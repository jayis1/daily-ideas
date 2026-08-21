#!/usr/bin/env python3
"""
terra_pin_plot.py — Terra Pin soil health data processor and visualizer

Reads a CSV survey file produced by the Terra Pin firmware and produces:
  1. A Soil Health Index (SHI) time-series plot
  2. Individual parameter trend plots (flux, ORP, EC, moisture, temp)
  3. A correlation heatmap between parameters
  4. A summary statistics report

Usage:
    python3 terra_pin_plot.py TERRA_0001.csv --output soil_report.png
    python3 terra_pin_plot.py TERRA_0001.csv --trends --correlation

The CSV format (from the Terra Pin SD card):
    session,timestamp,co2_chamber,co2_ambient,flux_ppm_min,flux_mgC,
    orp_mv,ec_us,moisture_vwc,temp_c,shi,
    shi_resp,shi_redox,shi_ec,shi_moist,shi_temp
"""

import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None  # type: ignore

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    plt = None  # type: ignore


def load_csv(filepath):
    """Load Terra Pin CSV, skipping comment lines."""
    rows = []
    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            line = line.strip()
            if not line:
                continue
            parts = line.split(',')
            if len(parts) < 11:
                continue
            rows.append({
                'session':       int(parts[0]),
                'timestamp':     parts[1],
                'co2_chamber':   int(parts[2]),
                'co2_ambient':   int(parts[3]),
                'flux_ppm_min':  float(parts[4]),
                'flux_mgC':      float(parts[5]),
                'orp_mv':        int(parts[6]),
                'ec_us':         int(parts[7]),
                'moisture_vwc':  float(parts[8]),
                'temp_c':        float(parts[9]),
                'shi':           int(parts[10]),
            })
    return rows


def print_summary(rows):
    """Print summary statistics to stdout."""
    if not rows:
        print("No data rows found.")
        return

    n = len(rows)
    print(f"\n{'='*60}")
    print(f"  Terra Pin Soil Health Report")
    print(f"  Session: {rows[0]['session']}  |  Readings: {n}")
    print(f"{'='*60}\n")

    params = ['shi', 'flux_mgC', 'orp_mv', 'ec_us', 'moisture_vwc', 'temp_c']
    labels = {
        'shi':          'Soil Health Index',
        'flux_mgC':     'CO2 Flux (mg C/m²/h)',
        'orp_mv':       'Redox Potential (mV)',
        'ec_us':        'Conductivity (µS/cm)',
        'moisture_vwc': 'Moisture (VWC %)',
        'temp_c':       'Temperature (°C)',
    }

    for p in params:
        vals = [r[p] for r in rows]
        mean = sum(vals) / n
        mn = min(vals)
        mx = max(vals)
        stdev = (sum((v - mean) ** 2 for v in vals) / n) ** 0.5
        print(f"  {labels[p]:30s}  mean={mean:8.2f}  min={mn:8.2f}  "
              f"max={mx:8.2f}  std={stdev:7.2f}")

    # SHI distribution
    shi_vals = [r['shi'] for r in rows]
    healthy = sum(1 for s in shi_vals if s >= 70)
    moderate = sum(1 for s in shi_vals if 50 <= s < 70)
    poor = sum(1 for s in shi_vals if s < 50)
    print(f"\n  SHI Distribution:")
    print(f"    Healthy  (≥70): {healthy}/{n} ({100*healthy/n:.0f}%)")
    print(f"    Moderate (50-69): {moderate}/{n} ({100*moderate/n:.0f}%)")
    print(f"    Poor     (<50): {poor}/{n} ({100*poor/n:.0f}%)")
    print(f"\n{'='*60}\n")


def plot_shi_timeseries(rows, output_path):
    """Plot SHI over time with color-coded zones."""
    if not HAS_MPL:
        print("matplotlib not available — skipping plots")
        return

    fig, ax = plt.subplots(figsize=(12, 5))
    x = range(len(rows))
    shi = [r['shi'] for r in rows]

    # Color zones
    ax.axhspan(70, 100, alpha=0.15, color='green', label='Healthy (≥70)')
    ax.axhspan(50, 70, alpha=0.15, color='yellow', label='Moderate (50-69)')
    ax.axhspan(0, 50, alpha=0.15, color='red', label='Poor (<50)')

    ax.plot(x, shi, 'k.-', linewidth=2, markersize=8, label='SHI')
    ax.fill_between(x, shi, alpha=0.2, color='blue')

    ax.set_xlabel('Reading #', fontsize=12)
    ax.set_ylabel('Soil Health Index (0–100)', fontsize=12)
    ax.set_title('Terra Pin — Soil Health Index Time Series', fontsize=14)
    ax.set_ylim(0, 100)
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    print(f"  SHI plot saved to {output_path}")
    plt.close(fig)


def plot_trends(rows, output_path):
    """Plot individual parameter trends in a 2×3 grid."""
    if not HAS_MPL:
        return

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    x = range(len(rows))

    plots = [
        ('flux_mgC', 'CO₂ Flux (mg C/m²/h)', 'tab:blue'),
        ('orp_mv', 'Redox (mV)', 'tab:orange'),
        ('ec_us', 'EC (µS/cm)', 'tab:green'),
        ('moisture_vwc', 'Moisture (VWC %)', 'tab:purple'),
        ('temp_c', 'Temperature (°C)', 'tab:red'),
        ('co2_chamber', 'Chamber CO₂ (ppm)', 'tab:brown'),
    ]

    for idx, (key, label, color) in enumerate(plots):
        ax = axes[idx // 3][idx % 3]
        vals = [r[key] for r in rows]
        ax.plot(x, vals, '.-', color=color, linewidth=1.5)
        ax.set_ylabel(label, fontsize=10)
    axes[1][2].set_xlabel('Reading #', fontsize=10)

    fig.suptitle('Terra Pin — Parameter Trends', fontsize=14)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    print(f"  Trends plot saved to {output_path}")
    plt.close(fig)


def plot_correlation(rows, output_path):
    """Plot correlation heatmap between parameters."""
    if not HAS_MPL or not HAS_NUMPY:
        print("numpy + matplotlib required for correlation plot")
        return

    params = ['shi', 'flux_mgC', 'orp_mv', 'ec_us', 'moisture_vwc', 'temp_c']
    labels = ['SHI', 'Flux', 'ORP', 'EC', 'Moist', 'Temp']

    data = np.array([[r[p] for r in rows] for p in params])
    corr = np.corrcoef(data)

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_yticklabels(labels, fontsize=11)

    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, f"{corr[i,j]:.2f}", ha='center', va='center',
                    fontsize=10, color='white' if abs(corr[i,j]) > 0.5 else 'black')

    fig.colorbar(im, ax=ax, label='Pearson r')
    ax.set_title('Terra Pin — Parameter Correlation Matrix', fontsize=14)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    print(f"  Correlation plot saved to {output_path}")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description='Terra Pin soil health data processor')
    parser.add_argument('csv_file', help='Path to Terra Pin CSV log file')
    parser.add_argument('--output', '-o', default='soil_shi.png',
                        help='Output SHI plot path (default: soil_shi.png)')
    parser.add_argument('--trends', action='store_true',
                        help='Also generate parameter trend plots')
    parser.add_argument('--correlation', action='store_true',
                        help='Also generate correlation heatmap')
    parser.add_argument('--trend-output', default='soil_trends.png',
                        help='Output trends plot path')
    parser.add_argument('--corr-output', default='soil_corr.png',
                        help='Output correlation plot path')
    args = parser.parse_args()

    filepath = Path(args.csv_file)
    if not filepath.exists():
        print(f"Error: {filepath} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {filepath}...")
    rows = load_csv(str(filepath))
    if not rows:
        print("No valid data rows found in CSV file.", file=sys.stderr)
        sys.exit(1)

    print_summary(rows)
    plot_shi_timeseries(rows, args.output)

    if args.trends:
        plot_trends(rows, args.trend_output)
    if args.correlation:
        plot_correlation(rows, args.corr_output)


if __name__ == '__main__':
    main()