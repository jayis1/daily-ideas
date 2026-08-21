#!/usr/bin/env python3
"""
langley_analysis.py — Langley calibration regression analysis

Reads a Langley log CSV from the Helio Tilt SD card and performs
linear regression of ln(V) vs. air mass for each wavelength. Produces
V₀ calibration constants, total optical depth, and R² quality metrics.

Usage:
    python3 langley_analysis.py langley_20260713.csv

Outputs:
    - V₀ constants for each wavelength
    - Total optical depth (τ) per wavelength
    - R² quality metric per wavelength
    - Langley regression plot (ln(V) vs. m)
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

WAVELENGTHS = [405, 440, 675, 870, 940, 1640]


def load_langley_csv(filename):
    """Load Langley CSV from SD card.
    Format: date,time,air_mass,v_405,v_440,v_675,v_870,v_940,v_1640
    """
    data = []
    with open(filename, 'r') as f:
        header = f.readline()
        for line in f:
            parts = line.strip().split(',')
            if len(parts) < 9:
                continue
            date_str = parts[0]
            time_str = parts[1]
            air_mass = float(parts[2])
            voltages = [float(x) for x in parts[3:9]]
            data.append({
                'datetime': f"{date_str} {time_str}",
                'air_mass': air_mass,
                'voltages': voltages,
            })
    return data


def langley_regress(air_masses, voltages):
    """Perform linear regression: ln(V) = ln(V0) - tau * m.
    Returns: V0, tau, R2
    """
    m = np.array(air_masses)
    v = np.array(voltages)

    # Filter out zero/negative voltages
    mask = v > 0
    if np.sum(mask) < 5:
        return 0.0, 0.0, 0.0

    m = m[mask]
    ln_v = np.log(v[mask])

    # OLS regression
    n = len(m)
    sum_x = np.sum(m)
    sum_y = np.sum(ln_v)
    sum_xy = np.sum(m * ln_v)
    sum_x2 = np.sum(m * m)
    sum_y2 = np.sum(ln_v * ln_v)

    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-10:
        return 0.0, 0.0, 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = np.mean(ln_v) - slope * np.mean(m)

    V0 = np.exp(intercept)
    tau = -slope

    # R²
    denom_y = n * sum_y2 - sum_y * sum_y
    if abs(denom_y) < 1e-10:
        R2 = 0.0
    else:
        R2 = (n * sum_xy - sum_x * sum_y) ** 2 / (denom * denom_y)

    return V0, tau, R2


def analyze(filename):
    data = load_langley_csv(filename)
    if not data:
        print("No data found in file.")
        return

    print(f"Loaded {len(data)} Langley data points from {filename}")
    print(f"Time range: {data[0]['datetime']} to {data[-1]['datetime']}")
    print()

    air_masses = [d['air_mass'] for d in data]

    results = []
    for wl_idx, wl in enumerate(WAVELENGTHS):
        voltages = [d['voltages'][wl_idx] for d in data]
        V0, tau, R2 = langley_regress(air_masses, voltages)
        results.append((wl, V0, tau, R2))

        quality = "EXCELLENT" if R2 > 0.99 else \
                  "GOOD" if R2 > 0.95 else \
                  "MARGINAL" if R2 > 0.90 else "REJECT"
        print(f"  λ={wl:4d} nm: V₀={V0:.6f}  τ={tau:.4f}  "
              f"R²={R2:.6f}  [{quality}]")

    print()
    all_good = all(r[3] > 0.99 for r in results if r[1] > 0)
    if all_good:
        print("✓ Langley calibration accepted (R² > 0.99 for all wavelengths)")
        print()
        print("V₀ constants (paste into firmware v0_cal[]):")
        print("static float v0_cal[6] = {")
        for wl, V0, tau, R2 in results:
            print(f"    {V0:.6f}f,   /* {wl} nm, R²={R2:.4f} */")
        print("};")
    else:
        print("✗ Langley calibration rejected (R² < 0.99 for some wavelengths)")
        print("  Retry on a day with more stable atmospheric conditions.")

    # Plot
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle(f"Langley Regression — {filename}")

    for wl_idx, (wl, V0, tau, R2) in enumerate(results):
        ax = axes[wl_idx // 3][wl_idx % 3]
        voltages = [d['voltages'][wl_idx] for d in data]
        m_arr = np.array(air_masses)
        v_arr = np.array(voltages)
        mask = v_arr > 0
        if np.sum(mask) > 0:
            ax.scatter(m_arr[mask], np.log(v_arr[mask]),
                      c='blue', s=20, alpha=0.6)
            if V0 > 0:
                m_fit = np.linspace(min(m_arr[mask]), max(m_arr[mask]), 100)
                ln_v_fit = np.log(V0) - tau * m_fit
                ax.plot(m_fit, ln_v_fit, 'r--', linewidth=2)
        ax.set_title(f"λ={wl} nm | R²={R2:.4f}")
        ax.set_xlabel("Air mass m")
        ax.set_ylabel("ln(V)")
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output = filename.replace('.csv', '_plot.png')
    plt.savefig(output, dpi=150)
    print(f"\nPlot saved to {output}")


def main():
    parser = argparse.ArgumentParser(description="Langley calibration analysis")
    parser.add_argument('filename', help='Langley CSV file from SD card')
    args = parser.parse_args()
    analyze(args.filename)


if __name__ == "__main__":
    main()