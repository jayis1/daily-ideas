#!/usr/bin/env python3
"""
gravi_dot_plot.py — Gravi Dot survey data processor and anomaly map plotter

Reads a CSV survey file produced by the Gravi Dot firmware and produces:
  1. A residual gravity anomaly contour map (matplotlib)
  2. A profile plot along the survey path
  3. A summary statistics report

Usage:
    python3 gravi_dot_plot.py survey_001.csv --rho 2670 --output map.png
    python3 gravi_dot_plot.py survey_001.csv --rho 2670 --contour --profile

The CSV format (from the Gravi Dot SD card):
    #,type,lat,lon,alt,time,g_z,g_x,g_y,temp,press,tilt_x,tilt_y,rms,g_corr,residual

Corrections already applied on-device:
    tilt, temperature, pressure, drift, earth-tide, latitude, free-air, Bouguer

This script does additional post-processing:
    - Regional-residual separation (optional high-pass filter)
    - Interpolation onto a regular grid for contouring
    - Quality flagging (high vibration, poor GPS, large tilt)
"""

import argparse
import csv
import sys
import math
from pathlib import Path

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None  # type: ignore

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from scipy.interpolate import griddata
    HAS_PLOT = True
except ImportError:
    HAS_PLOT = False


def load_survey(csv_path: str):
    """Load Gravi Dot CSV survey file."""
    stations = []
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                st = {
                    "num":       int(row["#"]),
                    "type":      row["type"],
                    "lat":       float(row["lat"]),
                    "lon":       float(row["lon"]),
                    "alt":       float(row["alt"]),
                    "time":      int(row["time"]),
                    "g_z":       float(row["g_z"]),
                    "g_corr":    float(row["g_corr"]),
                    "residual":  float(row["residual"]),
                    "rms":       float(row["rms"]),
                    "tilt_x":    float(row["tilt_x"]),
                    "tilt_y":    float(row["tilt_y"]),
                }
                stations.append(st)
            except (KeyError, ValueError) as e:
                print(f"  WARN: skipping bad row: {e}", file=sys.stderr)
    return stations


def compute_distances(stations):
    """Compute along-track distance for profile plot (metres)."""
    if not stations:
        return []
    lats = [s["lat"] for s in stations]
    lons = [s["lon"] for s in stations]
    # Haversine distance between consecutive stations
    dists = [0.0]
    for i in range(1, len(lats)):
        dlat = math.radians(lats[i] - lats[i-1])
        dlon = math.radians(lons[i] - lons[i-1])
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lats[i-1])) * \
            math.cos(math.radians(lats[i])) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        dists.append(dists[-1] + 6371000 * c)
    return dists


def quality_flags(stations, vib_thresh=2.0, tilt_thresh=0.2):
    """Flag stations with quality issues."""
    flags = []
    for s in stations:
        issues = []
        if s["rms"] > vib_thresh:
            issues.append(f"HIGH_VIB({s['rms']:.2f})")
        if abs(s["tilt_x"]) > tilt_thresh or abs(s["tilt_y"]) > tilt_thresh:
            issues.append(f"TILT({s['tilt_x']:.3f},{s['tilt_y']:.3f})")
        if s["lat"] == 0 and s["lon"] == 0:
            issues.append("NO_GPS")
        flags.append(issues)
    return flags


def regional_residual(residuals, window=5):
    """Simple moving-average regional separation.
    residual = observed - regional_trend
    Returns (regional, residual_detrended)
    """
    n = len(residuals)
    if n < window:
        return [0.0]*n, list(residuals)
    if HAS_NUMPY:
        regional = np.convolve(residuals, np.ones(window)/window, mode="same")
        for i in range(window//2):
            regional[i] = np.mean(residuals[:i+window//2+1])
            regional[-i-1] = np.mean(residuals[-(i+window//2+1):])
        detrended = np.array(residuals) - regional
        return regional, detrended
    else:
        # Pure-Python fallback
        regional = []
        for i in range(n):
            lo = max(0, i - window//2)
            hi = min(n, i + window//2 + 1)
            regional.append(sum(residuals[lo:hi]) / (hi - lo))
        detrended = [r - g for r, g in zip(residuals, regional)]
        return regional, detrended


def plot_contour(stations, output_path, rho=2670):
    """Produce a 2D contour map of gravity anomalies."""
    if not HAS_PLOT:
        print("  matplotlib/scipy not available — skipping contour plot")
        return

    lats = np.array([s["lat"] for s in stations])
    lons = np.array([s["lon"] for s in stations])
    res  = np.array([s["residual"] for s in stations]) * 1000.0  # → μGal

    # Convert lat/lon to local metres (approximate UTM)
    lat0 = lats.mean()
    lon0 = lons.mean()
    x = (lons - lon0) * 111320 * math.cos(math.radians(lat0))
    y = (lats - lat0) * 110574

    # Grid for interpolation
    if len(stations) < 4:
        print("  Not enough stations for contour map (need ≥4)")
        return

    xi = np.linspace(x.min(), x.max(), 100)
    yi = np.linspace(y.min(), y.max(), 100)
    xi, yi = np.meshgrid(xi, yi)
    zi = griddata((x, y), res, (xi, yi), method="cubic")

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    # Custom colormap: blue (low gravity) → white → red (high gravity)
    cmap = LinearSegmentedColormap.from_list("gravity",
        ["#2166AC", "#67A9CF", "#D1E5F0", "#FFFFFF", "#FDDBC7", "#EF8A62", "#B2182B"])

    levels = np.linspace(np.nanmin(zi), np.nanmax(zi), 20)
    cs = ax.contourf(xi, yi, zi, levels=levels, cmap=cmap, extend="both")
    ax.scatter(x, y, c="black", s=30, zorder=5, edgecolors="white", linewidths=0.5)

    # Annotate station numbers
    for i, s in enumerate(stations):
        ax.annotate(str(s["num"]), (x[i], y[i]), fontsize=6,
                    textcoords="offset points", xytext=(4, 4))

    plt.colorbar(cs, ax=ax, label="Residual gravity anomaly (μGal)")
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    ax.set_title(f"Gravi Dot Survey — Residual Gravity Anomaly\n"
                 f"({len(stations)} stations, ρ={rho} kg/m³)")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"  Contour map saved: {output_path}")


def plot_profile(stations, output_path):
    """Produce a 1D profile plot along the survey path."""
    if not HAS_PLOT:
        print("  matplotlib not available — skipping profile plot")
        return

    dists = compute_distances(stations)
    res = np.array([s["residual"] for s in stations]) * 1000.0  # → μGal
    regional, detrended = regional_residual(res.tolist())

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), sharex=True)

    ax1.plot(dists, res, "ko-", markersize=4, label="Residual (observed)")
    ax1.plot(dists, regional, "b--", linewidth=1, label="Regional trend")
    ax1.set_ylabel("Gravity anomaly (μGal)")
    ax1.set_title("Gravi Dot — Gravity Profile")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.axhline(0, color="gray", linewidth=0.5)

    ax2.plot(dists, detrended, "r.-", markersize=4, label="Detrended residual")
    ax2.fill_between(dists, detrended, 0, where=(detrended < 0),
                     color="blue", alpha=0.3, label="low (possible void)")
    ax2.fill_between(dists, detrended, 0, where=(detrended >= 0),
                     color="red", alpha=0.3, label="high (dense body)")
    ax2.set_xlabel("Along-track distance (m)")
    ax2.set_ylabel("Detrended anomaly (μGal)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.axhline(0, color="gray", linewidth=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    print(f"  Profile plot saved: {output_path}")


def print_summary(stations, flags):
    """Print survey summary statistics."""
    res = [s["residual"] * 1000.0 for s in stations]  # μGal
    res_min = min(res)
    res_max = max(res)
    res_mean = sum(res) / len(res)
    res_std = (sum((r - res_mean)**2 for r in res) / len(res)) ** 0.5
    print(f"\n{'='*60}")
    print(f"  GRAVI DOT SURVEY SUMMARY")
    print(f"{'='*60}")
    print(f"  Stations:      {len(stations)}")
    print(f"  Base stations: {sum(1 for s in stations if s['type'] == 'BASE')}")
    print(f"  Survey span:   {stations[0]['lat']:.6f}, {stations[0]['lon']:.6f}"
          f" → {stations[-1]['lat']:.6f}, {stations[-1]['lon']:.6f}")
    print(f"  Elevation:     {min(s['alt'] for s in stations):.1f}"
          f" – {max(s['alt'] for s in stations):.1f} m")
    print(f"  Residual (μGal):")
    print(f"    min:    {res_min:.1f}")
    print(f"    max:    {res_max:.1f}")
    print(f"    mean:   {res_mean:.1f}")
    print(f"    std:    {res_std:.1f}")
    print(f"    range:  {res_max - res_min:.1f}")

    n_flagged = sum(1 for f in flags if f)
    if n_flagged:
        print(f"\n  ⚠ {n_flagged} station(s) with quality issues:")
        for i, (s, f) in enumerate(zip(stations, flags)):
            if f:
                print(f"    #{s['num']}: {', '.join(f)}")

    # Interpretation hints
    print(f"\n  Interpretation hints:")
    if res_min < -50:
        print(f"    → Strong gravity low ({res_min:.0f} μGal) — possible subsurface void/cave")
    if res_max > 50:
        print(f"    → Strong gravity high ({res_max:.0f} μGal) — possible dense body/ore")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Gravi Dot survey data processor and anomaly map plotter")
    parser.add_argument("csv", help="Survey CSV file from Gravi Dot SD card")
    parser.add_argument("--rho", type=float, default=2670,
                        help="Bouguer crustal density (kg/m³, default 2670)")
    parser.add_argument("--output", "-o", default="gravi_dot_map.png",
                        help="Output contour map filename")
    parser.add_argument("--profile", "-p", action="store_true",
                        help="Also produce a profile plot")
    parser.add_argument("--contour", "-c", action="store_true",
                        help="Produce a contour map (default if matplotlib available)")
    parser.add_argument("--summary", "-s", action="store_true",
                        help="Print survey summary statistics")
    args = parser.parse_args()

    if not Path(args.csv).exists():
        print(f"Error: {args.csv} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Loading survey: {args.csv}")
    stations = load_survey(args.csv)
    print(f"  Loaded {len(stations)} stations")

    if not stations:
        print("Error: no valid stations found", file=sys.stderr)
        sys.exit(1)

    flags = quality_flags(stations)

    if args.summary or not (args.contour or args.profile):
        print_summary(stations, flags)

    if args.contour or (not args.summary and not args.profile):
        plot_contour(stations, args.output, args.rho)

    if args.profile:
        prof_path = args.output.replace(".png", "_profile.png")
        plot_profile(stations, prof_path)


if __name__ == "__main__":
    main()