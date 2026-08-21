#!/usr/bin/env python3
"""
kappa-pin / scripts / analyze_log.py
Post-measurement analysis of Kappa Pin CSV log files.

Parses a CSV log, recomputes thermal conductivity/diffusivity from the
raw data, and generates publication-quality plots.

Usage:
    python3 analyze_log.py KP_20260727_143215.csv
    python3 analyze_log.py KP_20260727_143215.csv --output result.png

Requires: numpy, matplotlib, scipy
    pip install numpy matplotlib scipy
"""

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.stats import linregress


@dataclass
class LogHeader:
    date: str = ""
    probe: str = ""
    material: str = ""
    power: float = 0.0
    pulse: float = 0.0
    t0: float = 0.0


@dataclass
class LogResult:
    lambda_val: float = 0.0
    alpha: float = 0.0
    rho_cp: float = 0.0
    effusivity: float = 0.0
    r_squared: float = 0.0
    n_points: int = 0


@dataclass
class LogData:
    header: LogHeader = field(default_factory=LogHeader)
    result: Optional[LogResult] = None
    times: List[float] = field(default_factory=list)
    temps: List[float] = field(default_factory=list)
    dts: List[float] = field(default_factory=list)
    v_heaters: List[float] = field(default_factory=list)
    i_heaters: List[float] = field(default_factory=list)
    qs: List[float] = field(default_factory=list)


def parse_log(filename: str) -> LogData:
    """Parse a Kappa Pin CSV log file."""
    data = LogData()

    with open(filename, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue

            line = ",".join(row).strip()

            # Parse header comments
            if line.startswith("#"):
                m = re.match(r"#\s*Date:\s*(.+)", line)
                if m: data.header.date = m.group(1)

                m = re.match(r"#\s*Probe:\s*(\d+)", line)
                if m: data.header.probe = m.group(1)

                m = re.match(r"#\s*Material:\s*(\d+)", line)
                if m: data.header.material = m.group(1)

                m = re.match(r"#\s*Power:\s*([\d.]+)\s*W", line)
                if m: data.header.power = float(m.group(1))

                m = re.match(r"#\s*Pulse:\s*([\d.]+)\s*s", line)
                if m: data.header.pulse = float(m.group(1))

                m = re.match(r"#\s*T0:\s*([\d.]+)\s*C", line)
                if m: data.header.t0 = float(m.group(1))

                # Parse result
                m = re.match(r"#\s*lambda=([\d.]+)\s*W/m\.K", line)
                if m:
                    if data.result is None:
                        data.result = LogResult()
                    data.result.lambda_val = float(m.group(1))

                m = re.match(r"#\s*alpha=([\d.]+)\s*mm2/s", line)
                if m:
                    if data.result is None:
                        data.result = LogResult()
                    data.result.alpha = float(m.group(1))

                m = re.match(r"#\s*rhoCp=([\d.e+-]+)\s*J/m3\.K", line)
                if m:
                    if data.result is None:
                        data.result = LogResult()
                    data.result.rho_cp = float(m.group(1))

                m = re.match(r"#\s*effusivity=([\d.]+)", line)
                if m:
                    if data.result is None:
                        data.result = LogResult()
                    data.result.effusivity = float(m.group(1))

                m = re.match(r"#\s*R2=([\d.]+)", line)
                if m:
                    if data.result is None:
                        data.result = LogResult()
                    data.result.r_squared = float(m.group(1))

                continue

            # Skip column header line
            if line.startswith("t_s"):
                continue

            # Parse data row
            try:
                parts = [p.strip() for p in row if p.strip()]
                if len(parts) >= 6:
                    data.times.append(float(parts[0]))
                    data.temps.append(float(parts[1]))
                    data.dts.append(float(parts[2]))
                    data.v_heaters.append(float(parts[3]))
                    data.i_heaters.append(float(parts[4]))
                    data.qs.append(float(parts[5]))
            except (ValueError, IndexError):
                pass

    return data


def reanalyze(data: LogData):
    """Recompute thermal conductivity from raw data."""
    t = np.array(data.times)
    dt = np.array(data.dts) / 1000.0  # mK → °C
    q = np.array(data.qs)

    # Identify heating phase
    heating = q > 0.01
    cooling = ~heating

    # Average power during heating
    avg_q = np.mean(q[heating]) if np.any(heating) else 0
    active_len = 0.080  # NP-100 default
    Q_per_m = avg_q / active_len

    print(f"Heating phase: {np.sum(heating)} samples ({np.sum(heating) * 100 / len(t):.1f}%)")
    print(f"Average power: {avg_q:.4f} W")
    print(f"Q per meter:   {Q_per_m:.4f} W/m")

    # Find optimal regression window
    t_heat = t[heating]
    dt_heat = dt[heating]

    # Skip early transient (first 20% of heating)
    n_heat = len(t_heat)
    min_start = max(5, n_heat // 5)
    max_end = n_heat * 9 // 10

    best_r2 = -1
    best_slope = 0
    best_intercept = 0
    best_start = 0
    best_end = 0

    for start in range(min_start, n_heat // 2):
        for end in range(start + 10, min(max_end, n_heat)):
            if t_heat[end] <= 0 or t_heat[start] <= 0:
                continue
            ln_t = np.log(t_heat[start:end+1])
            dt_seg = dt_heat[start:end+1]
            if len(ln_t) < 5:
                continue
            slope, intercept, r_value, _, _ = linregress(ln_t, dt_seg)
            r2 = r_value ** 2
            if r2 > best_r2 and r2 > 0.999:
                best_r2 = r2
                best_slope = slope
                best_intercept = intercept
                best_start = start
                best_end = end

    if best_r2 < 0:
        # Fallback
        ln_t = np.log(t_heat[min_start:max_end])
        dt_seg = dt_heat[min_start:max_end]
        slope, intercept, r_value, _, _ = linregress(ln_t, dt_seg)
        best_slope = slope
        best_intercept = intercept
        best_r2 = r_value ** 2
        best_start = min_start
        best_end = max_end - 1

    # Thermal conductivity
    pi = np.pi
    lambda_val = Q_per_m / (4 * pi * best_slope) if best_slope != 0 else 0

    print(f"\nRegression window: samples {best_start}–{best_end} "
          f"(t = {t_heat[best_start]:.2f}–{t_heat[best_end]:.2f} s)")
    print(f"Slope m = {best_slope:.6f} K/ln(s)")
    print(f"R² = {best_r2:.6f}")
    print(f"\nλ = Q / (4π·m) = {Q_per_m:.4f} / (4π × {best_slope:.6f})")
    print(f"λ = {lambda_val:.4f} W/(m·K)")

    # Fit diffusivity
    def model(t, lam, alpha):
        r = 0.0006  # probe radius
        gamma = 0.5772156649
        return (Q_per_m / (4 * pi * lam)) * (np.log(4 * alpha * t / r**2) - gamma)

    try:
        popt, _ = curve_fit(model, t_heat[best_start:best_end+1],
                            dt_heat[best_start:best_end+1],
                           p0=[lambda_val, 5e-7],
                           bounds=([0.001, 1e-9], [20, 5e-6]))
        lam_fit, alpha_fit = popt
        alpha_mm2 = alpha_fit * 1e6
        rho_cp = lam_fit / (alpha_fit)
        effus = np.sqrt(lam_fit * rho_cp)

        print(f"\nLevenberg-Marquardt fit:")
        print(f"  λ (fitted) = {lam_fit:.4f} W/(m·K)")
        print(f"  α = {alpha_mm2:.4f} mm²/s")
        print(f"  ρcₚ = {rho_cp:.4e} J/(m³·K)")
        print(f"  e = {effus:.1f} J/(m²·K·s^0.5)")
    except Exception as e:
        print(f"Diffusivity fit failed: {e}")
        lam_fit = lambda_val
        alpha_mm2 = 0
        rho_cp = 0
        effus = 0

    return {
        "lambda": lambda_val,
        "lambda_fit": lam_fit,
        "alpha": alpha_mm2,
        "rho_cp": rho_cp,
        "effusivity": effus,
        "slope": best_slope,
        "intercept": best_intercept,
        "r_squared": best_r2,
        "fit_start": best_start,
        "fit_end": best_end,
        "Q_per_m": Q_per_m,
        "avg_q": avg_q,
    }


def plot_results(data: LogData, analysis: dict, output: str = None):
    """Generate analysis plots."""
    t = np.array(data.times)
    dt = np.array(data.dts) / 1000.0
    q = np.array(data.qs)
    heating = q > 0.01
    t_heat = t[heating]
    dt_heat = dt[heating]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Kappa Pin Analysis — {data.header.date}", fontsize=14)

    # Plot 1: ΔT vs time
    ax = axes[0, 0]
    ax.plot(t, dt, "b-", linewidth=1.5)
    if np.any(heating):
        ax.axvspan(t_heat[0], t_heat[-1], alpha=0.1, color="red", label="Heating")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("ΔT (°C)")
    ax.set_title("Temperature Rise vs Time")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: ΔT vs ln(t) with fit
    ax = axes[0, 1]
    valid = t_heat > 0
    ln_t = np.log(t_heat[valid])
    ax.plot(ln_t, dt_heat[valid], "b.", markersize=3, label="Data")

    # Fit line
    fs = analysis["fit_start"]
    fe = analysis["fit_end"]
    if fe > fs and fe < len(t_heat):
        ln_t_fit = np.log(t_heat[fs:fe+1])
        fit_line = analysis["slope"] * ln_t_fit + analysis["intercept"]
        ax.plot(ln_t_fit, fit_line, "r-", linewidth=2,
                label=f"Fit: m={analysis['slope']:.4f}, R²={analysis['r_squared']:.5f}")
        ax.axvspan(ln_t_fit[0], ln_t_fit[-1], alpha=0.1, color="green", label="Fit window")

    ax.set_xlabel("ln(t)")
    ax.set_ylabel("ΔT (°C)")
    ax.set_title("Linear Regression: ΔT vs ln(t)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Heater power vs time
    ax = axes[1, 0]
    ax.plot(t, q, "g-", linewidth=1.5)
    ax.axhline(analysis["avg_q"], color="r", linestyle="--",
               label=f"Avg Q = {analysis['avg_q']:.3f} W")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Power (W)")
    ax.set_title("Heater Power vs Time")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 4: Summary text
    ax = axes[1, 1]
    ax.axis("off")
    summary = (
        f"MEASUREMENT SUMMARY\n"
        f"{'='*40}\n"
        f"Date:        {data.header.date}\n"
        f"Probe:       {data.header.probe}\n"
        f"Material:    {data.header.material}\n"
        f"T₀:          {data.header.t0:.4f} °C\n"
        f"Pulse:       {data.header.pulse:.1f} s\n"
        f"Power:       {analysis['avg_q']:.4f} W\n"
        f"Q/L:         {analysis['Q_per_m']:.4f} W/m\n"
        f"\n"
        f"RESULTS\n"
        f"{'='*40}\n"
        f"λ (slope):   {analysis['lambda']:.4f} W/(m·K)\n"
        f"λ (fit):     {analysis['lambda_fit']:.4f} W/(m·K)\n"
        f"α:           {analysis['alpha']:.4f} mm²/s\n"
        f"ρcₚ:         {analysis['rho_cp']:.4e} J/(m³·K)\n"
        f"Effusivity:  {analysis['effusivity']:.1f} J/(m²·K·s^0.5)\n"
        f"R²:          {analysis['r_squared']:.6f}\n"
        f"Slope:       {analysis['slope']:.6f} K/ln(s)\n"
    )

    # Compare with logged result if available
    if data.result:
        summary += (
            f"\n"
            f"DEVICE RESULT (from log)\n"
            f"{'='*40}\n"
            f"λ:           {data.result.lambda_val:.4f} W/(m·K)\n"
            f"α:           {data.result.alpha:.4f} mm²/s\n"
            f"R²:          {data.result.r_squared:.6f}\n"
        )

    ax.text(0.05, 0.95, summary, transform=ax.transAxes, fontsize=10,
            verticalalignment="top", fontfamily="monospace",
            bbox=dict(boxstyle="round", facecolor="lightyellow"))

    plt.tight_layout()

    if output:
        fig.savefig(output, dpi=150, bbox_inches="tight")
        print(f"\nPlot saved to: {output}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Analyze Kappa Pin CSV log files")
    parser.add_argument("logfile", help="Path to CSV log file")
    parser.add_argument("-o", "--output", help="Output image file (PNG/PDF)",
                        default=None)
    args = parser.parse_args()

    print(f"Parsing {args.logfile}...")
    data = parse_log(args.logfile)

    print(f"  {len(data.times)} samples loaded")
    print(f"  Date: {data.header.date}")
    print(f"  Power: {data.header.power} W, Pulse: {data.header.pulse} s")
    print()

    print("Reanalyzing measurement...")
    analysis = reanalyze(data)

    print()
    plot_results(data, analysis, args.output)


if __name__ == "__main__":
    main()