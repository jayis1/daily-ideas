#!/usr/bin/env python3
"""
lumen_cast/scripts/lumen_cast_viewer.py

A companion desktop app for the Lumen Cast pocket goniophotometer.
Connects to the device via BLE (through the ESP32-C3 bridge) or
generates demo data for offline exploration.

Features:
  - Live polar plot of luminous intensity during scan
  - Photometric report: flux (lm), peak candela, beam angle, throw
  - Color uniformity: CCT/Duv on-axis vs edge, MacAdam steps
  - Isocandela contour plot
  - IES LM-63 (.IES) file generation and export
  - EULUMDAT (.LDT) file generation and export
  - Session history from CSV import

Usage:
  python3 lumen_cast_viewer.py --demo
  python3 lumen_cast_viewer.py --ble
  python3 lumen_cast_viewer.py --csv data.csv
  python3 lumen_cast_viewer.py --demo --export scan.ies
"""

import argparse
import math
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ─── Data structures ──────────────────────────────────────────────────────

@dataclass
class PhotoSample:
    azimuth_deg: float = 0.0
    elevation_deg: float = 90.0
    lux: float = 0.0
    candela: float = 0.0
    r: int = 0
    g: int = 0
    b: int = 0
    c: int = 0
    cct_k: float = 0.0
    duv: float = 0.0
    x: float = 0.0
    y: float = 0.0


@dataclass
class ScanConfig:
    scan_type: str = "Type C"
    az_steps: int = 24
    el_steps: int = 12
    az_start: float = 0.0
    az_end: float = 360.0
    el_start: float = 0.0
    el_end: float = 180.0
    step_deg: float = 15.0


@dataclass
class ScanBuffer:
    samples: List[PhotoSample] = field(default_factory=list)
    config: ScanConfig = field(default_factory=ScanConfig)
    timestamp: int = 0
    ambient_lux: float = 0.0
    cal_factor: float = 1.0


@dataclass
class PhotoResult:
    luminous_flux_lm: float = 0.0
    peak_candela: float = 0.0
    peak_az_deg: float = 0.0
    peak_el_deg: float = 90.0
    beam_angle_fwhm: float = 0.0
    field_angle_10pct: float = 0.0
    cbcp_candela: float = 0.0
    beam_uniformity: float = 0.0
    throw_m: float = 0.0
    cct_onaxis_k: float = 0.0
    duv_onaxis: float = 0.0
    cct_edge_k: float = 0.0
    duv_edge: float = 0.0
    delta_cct_k: float = 0.0
    macadam_steps_edge: float = 0.0
    timestamp: int = 0
    scan_id: int = 0
    valid: bool = False


# ─── Constants ────────────────────────────────────────────────────────────

SENSOR_RADIUS_M = 0.150
SENSOR_RADIUS_SQ = SENSOR_RADIUS_M ** 2
PI = math.pi


# ─── Demo data generation ─────────────────────────────────────────────────

def generate_demo_scan(scan_type: str = "Type C") -> ScanBuffer:
    """Generate a synthetic scan of a narrow-beam LED (38° beam, 850 lm)."""
    scan = ScanBuffer()
    scan.timestamp = int(time.time())
    scan.ambient_lux = 0.5
    scan.cal_factor = 1.02

    if scan_type == "Type A":
        scan.config = ScanConfig("Type A", 360, 1, 0, 360, 90, 90, 1.0)
        n_az, n_el = 360, 1
    elif scan_type == "Type C":
        scan.config = ScanConfig("Type C", 24, 12, 0, 360, 0, 180, 15.0)
        n_az, n_el = 24, 12
    elif scan_type == "Near-field":
        scan.config = ScanConfig("Near-field", 25, 25, -60, 60, 30, 150, 5.0)
        n_az, n_el = 25, 25
    else:
        scan.config = ScanConfig("Meridian", 1, 180, 0, 0, 0, 180, 1.0)
        n_az, n_el = 1, 180

    cfg = scan.config

    # Simulate a 38° FWHM Gaussian beam centered at (az=0, el=90)
    fwhm_deg = 38.0
    sigma = fwhm_deg / (2.0 * math.sqrt(2.0 * math.log(2.0)))

    # Calibrate peak so that spherical integration yields ~850 lm.
    # For a Gaussian beam: Φ ≈ 2π × I_peak × (1 - cos(3σ))
    # Empirically adjusted for grid resolution and Lambertian floor.
    peak_cd = 1700.0

    for el_idx in range(n_el):
        if n_el > 1:
            elevation = cfg.el_start + el_idx * (cfg.el_end - cfg.el_start) / (n_el - 1)
        else:
            elevation = 90.0

        for az_idx in range(n_az):
            if n_az > 1:
                azimuth = cfg.az_start + az_idx * (cfg.az_end - cfg.az_start) / n_az
            else:
                azimuth = 0.0

            # Angular distance from beam center (0, 90)
            d_az = min(abs(azimuth), 360 - abs(azimuth))
            d_el = abs(elevation - 90)
            angular_dist = math.sqrt(d_az**2 + d_el**2)

            # Gaussian beam profile
            I = peak_cd * math.exp(-0.5 * (angular_dist / sigma) ** 2)

            # Add some Lambertian floor (omnidirectional component)
            I += 5.0 * math.sin(elevation * PI / 180.0)

            # Convert to lux: E = I / r²
            lux = I / SENSOR_RADIUS_SQ

            # Simulate color: 3120K on-axis, slight blue shift at edge
            cct = 3120 + angular_dist * 1.7
            duv = 0.0021 + angular_dist * 0.00003

            # Simulate RGBC for this CCT (very approximate)
            c_val = max(1, int(I * 10))
            r_val = int(c_val * 0.45)
            g_val = int(c_val * 0.38)
            b_val = int(c_val * (0.15 + (cct - 2800) / 20000))

            sample = PhotoSample(
                azimuth_deg=azimuth, elevation_deg=elevation,
                lux=lux, candela=I,
                r=r_val, g=g_val, b=b_val, c=c_val,
                cct_k=cct, duv=duv,
                x=0.43, y=0.40
            )
            scan.samples.append(sample)

    scan.config.az_steps = n_az
    scan.config.el_steps = n_el
    return scan


# ─── Photometric computation ──────────────────────────────────────────────

def integrate_flux(scan: ScanBuffer) -> float:
    """Compute luminous flux by spherical integration: Φ = ∮ I dΩ"""
    cfg = scan.config
    if len(scan.samples) < 2:
        return 0.0

    if cfg.el_steps <= 1:
        # 1D azimuth: approximate with 4π × mean(I)
        mean_I = sum(s.candela for s in scan.samples) / len(scan.samples)
        return mean_I * 4.0 * PI

    dtheta = math.radians(cfg.el_end - cfg.el_start) / max(cfg.el_steps - 1, 1)
    dphi = math.radians(cfg.az_end - cfg.az_start) / max(cfg.az_steps, 1)

    flux = 0.0
    for s in scan.samples:
        theta = math.radians(s.elevation_deg)
        flux += s.candela * math.sin(theta) * dtheta * dphi
    return flux


def find_peak(scan: ScanBuffer) -> Tuple[float, float, float]:
    """Returns (peak_cd, az, el)"""
    peak = max(scan.samples, key=lambda s: s.candela)
    return peak.candela, peak.azimuth_deg, peak.elevation_deg


def beam_angle(scan: ScanBuffer, fraction: float = 0.5) -> float:
    """Compute beam width at given fraction of peak (FWHM for 0.5)"""
    peak_cd, peak_az, peak_el = find_peak(scan)
    threshold = peak_cd * fraction
    if threshold < 0.01:
        return 0.0

    cfg = scan.config
    if cfg.el_steps <= 1:
        # 1D azimuth
        crossings = []
        for i in range(len(scan.samples) - 1):
            I0, I1 = scan.samples[i].candela, scan.samples[i+1].candela
            if (I0 < threshold <= I1) or (I0 >= threshold > I1):
                frac = (threshold - I0) / (I1 - I0 + 1e-9)
                angle = scan.samples[i].azimuth_deg + frac * (
                    scan.samples[i+1].azimuth_deg - scan.samples[i].azimuth_deg)
                crossings.append(angle)
        if len(crossings) >= 2:
            return crossings[-1] - crossings[0]
        return 360.0

    # 2D: elevation cut through peak azimuth
    # Filter samples near peak azimuth, sort by elevation
    plane = [s for s in scan.samples
             if min(abs(s.azimuth_deg - peak_az),
                    360 - abs(s.azimuth_deg - peak_az)) <= cfg.step_deg * 0.6]
    plane.sort(key=lambda s: s.elevation_deg)

    crossings = []
    for i in range(len(plane) - 1):
        I0, I1 = plane[i].candela, plane[i+1].candela
        if (I0 < threshold <= I1) or (I0 >= threshold > I1):
            frac = (threshold - I0) / (I1 - I0 + 1e-9)
            angle = plane[i].elevation_deg + frac * (
                plane[i+1].elevation_deg - plane[i].elevation_deg)
            crossings.append(angle)
    if len(crossings) >= 2:
        return crossings[-1] - crossings[0]
    return 180.0


def compute_results(scan: ScanBuffer) -> PhotoResult:
    """Full photometric analysis"""
    r = PhotoResult()
    if len(scan.samples) < 4:
        return r

    r.luminous_flux_lm = integrate_flux(scan)
    r.peak_candela, r.peak_az_deg, r.peak_el_deg = find_peak(scan)
    r.beam_angle_fwhm = beam_angle(scan, 0.5)
    r.field_angle_10pct = beam_angle(scan, 0.1)
    # CBCP: intensity at on-axis (closest to 0° azimuth, 90° elevation)
    onaxis_candidates = [s.candela for s in scan.samples
                         if abs(s.elevation_deg - 90) < 10
                         and min(abs(s.azimuth_deg), 360 - abs(s.azimuth_deg)) < 10]
    r.cbcp_candela = max(onaxis_candidates) if onaxis_candidates else 0

    # Beam uniformity
    threshold = r.peak_candela * 0.5
    in_beam = [s.candela for s in scan.samples if s.candela >= threshold]
    if in_beam:
        r.beam_uniformity = min(in_beam) / max(in_beam)

    # Throw (ANSI FL-1: distance to 0.25 lux)
    r.throw_m = math.sqrt(r.peak_candela / 0.25)

    # Color uniformity: find on-axis sample (closest to beam peak)
    onaxis = min(scan.samples,
                 key=lambda s: abs(s.elevation_deg - r.peak_el_deg) +
                               min(abs(s.azimuth_deg - r.peak_az_deg),
                                   360 - abs(s.azimuth_deg - r.peak_az_deg)))
    r.cct_onaxis_k = onaxis.cct_k
    r.duv_onaxis = onaxis.duv

    edge_samples = [s for s in scan.samples
                    if r.peak_candela * 0.45 < s.candela < r.peak_candela * 0.55]
    if edge_samples:
        r.cct_edge_k = sum(s.cct_k for s in edge_samples) / len(edge_samples)
        r.duv_edge = sum(s.duv for s in edge_samples) / len(edge_samples)
    else:
        r.cct_edge_k = r.cct_onaxis_k
        r.duv_edge = r.duv_onaxis

    r.delta_cct_k = abs(r.cct_edge_k - r.cct_onaxis_k)
    r.macadam_steps_edge = abs(r.duv_edge - r.duv_onaxis) / 0.001

    r.timestamp = scan.timestamp
    r.valid = True
    return r


# ─── IES LM-63 file generation ────────────────────────────────────────────

def generate_ies(scan: ScanBuffer, result: PhotoResult) -> str:
    """Generate IES LM-63-2002 photometric data file"""
    cfg = scan.config
    lines = []
    lines.append("IESNA:LM-63-2002")
    lines.append(f"[TEST] LUMEN_CAST_{scan.timestamp & 0xFFFF:04X}")
    lines.append("[MANUFAC] Unknown")
    lines.append(f"[TDATE] {scan.timestamp}")
    lines.append(f"[LUMCAT] LM_{scan.timestamp & 0xFFFF:04X}")
    lines.append("[LUMINAIRE] Lumen Cast Scan")
    lines.append("TILT=NONE")

    n_vert = cfg.az_steps
    n_horz = cfg.el_steps

    lines.append(f"1 {result.luminous_flux_lm:.1f} 1.0 {n_vert} {n_horz} 1 1 0 0 0 1.0 1.0 0")

    # Vertical angles (azimuth)
    vert = []
    for i in range(n_vert):
        angle = cfg.az_start + i * (cfg.az_end - cfg.az_start) / max(n_vert, 1)
        vert.append(f"{angle:.1f}")
    lines.append(" ".join(vert))

    # Horizontal angles (elevation)
    horz = []
    for j in range(n_horz):
        if n_horz > 1:
            angle = cfg.el_start + j * (cfg.el_end - cfg.el_start) / (n_horz - 1)
        else:
            angle = cfg.el_start
        horz.append(f"{angle:.1f}")
    lines.append(" ".join(horz))

    # Candela values
    for j in range(n_horz):
        row = []
        for i in range(n_vert):
            idx = j * n_vert + i
            if idx < len(scan.samples):
                row.append(f"{scan.samples[idx].candela:.1f}")
            else:
                row.append("0.0")
        lines.append(" ".join(row))

    return "\r\n".join(lines) + "\r\n"


# ─── EULUMDAT file generation ─────────────────────────────────────────────

def generate_ldt(scan: ScanBuffer, result: PhotoResult) -> str:
    """Generate EULUMDAT photometric data file (simplified)"""
    cfg = scan.config
    lines = []
    lines.append("0")  # manufacturer unknown
    lines.append("ITI - Lumen Cast")
    lines.append("Lumen Cast Scan")
    lines.append(f"LM_{scan.timestamp & 0xFFFF:04X}")
    lines.append("")  # file name
    lines.append("")  # date
    lines.append("")  # luminaire name (60 chars)
    lines.append("1")  # type
    lines.append("0")  # mounting type
    lines.append(f"{result.luminous_flux_lm:.1f}")  # total flux
    lines.append("1.0")  # conversion factor

    n_c = cfg.el_steps
    n_g = cfg.az_steps
    lines.append(str(n_c))  # number of C-planes
    lines.append(str(n_g))  # number of gamma angles per plane

    # ... (simplified — full EULUMDAT has many more fields)
    for j in range(n_c):
        for i in range(n_g):
            idx = j * n_g + i
            if idx < len(scan.samples):
                lines.append(f"{scan.samples[idx].candela:.2f}")
            else:
                lines.append("0.00")

    return "\r\n".join(lines) + "\r\n"


# ─── Text-based polar plot ────────────────────────────────────────────────

def text_polar_plot(scan: ScanBuffer, width: int = 60, height: int = 25) -> str:
    """Render an ASCII polar plot of the equatorial intensity distribution"""
    if not scan.samples:
        return "(no data)"

    grid = [[" "] * width for _ in range(height)]
    cx, cy = width // 2, height // 2
    max_r = min(cx, cy) - 1

    # Find equator samples (elevation near 90°)
    equator = [s for s in scan.samples if abs(s.elevation_deg - 90) < 20]
    if not equator:
        equator = scan.samples

    max_I = max(s.candela for s in equator) or 1.0

    # Draw grid circles
    for r_frac in [0.25, 0.5, 0.75, 1.0]:
        r = int(max_r * r_frac)
        for a in range(0, 360, 5):
            x = cx + int(r * math.cos(math.radians(a)))
            y = cy + int(r * math.sin(math.radians(a)) * 0.5)  # squash for terminal aspect
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = "·"

    # Draw axes
    for x in range(width):
        grid[cy][x] = "─" if grid[cy][x] == " " else grid[cy][x]
    for y in range(height):
        grid[y][cx] = "│" if grid[y][cx] == " " else grid[y][cx]

    # Plot intensity
    for s in equator:
        a = math.radians(s.azimuth_deg)
        rr = (s.candela / max_I) * max_r
        x = cx + int(rr * math.cos(a))
        y = cy + int(rr * math.sin(a) * 0.5)
        if 0 <= x < width and 0 <= y < height:
            grid[y][x] = "●"

    grid[cy][cx] = "+"

    return "\n".join("".join(row) for row in grid)


# ─── Main report ──────────────────────────────────────────────────────────

def print_report(scan: ScanBuffer, result: PhotoResult):
    print("\n" + "=" * 65)
    print("  LUMEN CAST — Photometric Report")
    print(f"  Scan: {scan.config.scan_type}  |  "
          f"Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(scan.timestamp))}")
    print(f"  Radius: {SENSOR_RADIUS_M*1000:.0f}mm  |  "
          f"Grid: {scan.config.az_steps} az × {scan.config.el_steps} el")
    print("-" * 65)
    print(f"  LUMINOUS FLUX:       {result.luminous_flux_lm:7.1f} lm")
    print(f"  PEAK CANDela:        {result.peak_candela:7.0f} cd  "
          f"@ (θ={result.peak_el_deg:.0f}°, φ={result.peak_az_deg:.0f}°)")
    print(f"  BEAM ANGLE (FWHM):   {result.beam_angle_fwhm:7.1f}°")
    print(f"  FIELD ANGLE (10%):   {result.field_angle_10pct:7.1f}°")
    print(f"  CBCP (on-axis):      {result.cbcp_candela:7.0f} cd")
    print(f"  BEAM UNIFORMITY:     {result.beam_uniformity:7.2f}")
    print(f"  THROW (0.25 lux):    {result.throw_m:7.1f} m")
    print("-" * 65)
    print(f"  COLOR (on-axis):     {result.cct_onaxis_k:4.0f} K  "
          f"Duv: {result.duv_onaxis:+.4f}")
    print(f"  COLOR (beam edge):   {result.cct_edge_k:4.0f} K  "
          f"Duv: {result.duv_edge:+.4f}")
    print(f"  ΔCCT across beam:    {result.delta_cct_k:7.0f} K")
    print(f"  MacAdam steps:       {result.macadam_steps_edge:7.1f}")
    print("-" * 65)
    print("\n  Polar plot (equatorial):")
    print(text_polar_plot(scan))
    print("=" * 65)


# ─── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lumen Cast viewer")
    parser.add_argument("--demo", action="store_true",
                        help="Generate demo scan data")
    parser.add_argument("--ble", action="store_true",
                        help="Connect via BLE")
    parser.add_argument("--csv", type=str, help="Import from CSV")
    parser.add_argument("--scan-type", type=str, default="Type C",
                        choices=["Type A", "Type C", "Meridian", "Near-field"])
    parser.add_argument("--export", type=str,
                        help="Export IES file to path")
    args = parser.parse_args()

    if args.ble:
        print("BLE connection not yet implemented in this demo script.")
        print("Use --demo for offline exploration.")
        sys.exit(1)

    if args.csv:
        print(f"CSV import from {args.csv} not yet implemented.")
        sys.exit(1)

    if args.demo or not (args.ble or args.csv):
        scan = generate_demo_scan(args.scan_type)
        result = compute_results(scan)
        print_report(scan, result)

        if args.export:
            ies = generate_ies(scan, result)
            with open(args.export, "w") as f:
                f.write(ies)
            print(f"\n  .IES file exported: {args.export} ({len(ies)} bytes)")

            ldt_path = args.export.replace(".ies", ".ldt")
            ldt = generate_ldt(scan, result)
            with open(ldt_path, "w") as f:
                f.write(ldt)
            print(f"  .LDT file exported: {ldt_path} ({len(ldt)} bytes)")


if __name__ == "__main__":
    main()