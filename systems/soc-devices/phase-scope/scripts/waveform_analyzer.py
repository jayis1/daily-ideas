#!/usr/bin/env python3
"""
Phase Scope — Waveform Analyzer
Reads CSV log files from Phase Scope SD card and generates analysis plots.

Requirements:
    pip install numpy matplotlib pandas

Usage:
    python waveform_analyzer.py LOG_00001.CSV
    python waveform_analyzer.py --dir /path/to/logs/ --summary
    python waveform_analyzer.py --file LOG_00001.CSV --plot voltage
    python waveform_analyzer.py --file LOG_00001.CSV --plot harmonics
"""

import argparse
import sys
import os
import glob

try:
    import numpy as np
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import pandas as pd
except ImportError:
    print("Required packages: pip install numpy matplotlib pandas")
    sys.exit(1)


CSV_COLUMNS = [
    'timestamp', 'V1_rms', 'V2_rms', 'V3_rms',
    'I1_rms', 'I2_rms', 'I3_rms',
    'P1', 'P2', 'P3', 'Q1', 'Q2', 'Q3', 'S1', 'S2', 'S3',
    'PF1', 'PF2', 'PF3', 'freq',
    'THD1', 'THD2', 'THD3',
    'phase_VI1', 'phase_VI2', 'phase_VI3'
]


def load_csv(filepath):
    """Load a Phase Scope CSV log file."""
    df = pd.read_csv(filepath, names=CSV_COLUMNS)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['P_total'] = df['P1'] + df['P2'] + df['P3']
    df['Q_total'] = df['Q1'] + df['Q2'] + df['Q3']
    df['S_total'] = df['S1'] + df['S2'] + df['S3']
    df['PF_total'] = df['P_total'] / df['S_total']
    return df


def plot_voltage(df, title_suffix=""):
    """Plot voltage trends over time."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    for i, (label, color) in enumerate(zip(['L1', 'L2', 'L3'], ['#e74c3c', '#2ecc71', '#3498db'])):
        axes[i].plot(df['timestamp'], df[f'V{i+1}_rms'], color=color, linewidth=1)
        axes[i].set_ylabel(f'{label} Voltage (V)')
        axes[i].grid(True, alpha=0.3)
        axes[i].axhline(y=230, color='gray', linestyle='--', alpha=0.5, label='Nominal')
        axes[i].legend(loc='upper right')

    axes[2].set_xlabel('Time')
    fig.suptitle(f'Voltage Trends {title_suffix}')
    plt.tight_layout()
    return fig


def plot_current(df, title_suffix=""):
    """Plot current trends over time."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    for i, (label, color) in enumerate(zip(['L1', 'L2', 'L3'], ['#e74c3c', '#2ecc71', '#3498db'])):
        axes[i].plot(df['timestamp'], df[f'I{i+1}_rms'], color=color, linewidth=1)
        axes[i].set_ylabel(f'{label} Current (A)')
        axes[i].grid(True, alpha=0.3)

    axes[2].set_xlabel('Time')
    fig.suptitle(f'Current Trends {title_suffix}')
    plt.tight_layout()
    return fig


def plot_power(df, title_suffix=""):
    """Plot power and power factor trends."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Active power
    for i, (label, color) in enumerate(zip(['L1', 'L2', 'L3'], ['#e74c3c', '#2ecc71', '#3498db'])):
        axes[0, 0].plot(df['timestamp'], df[f'P{i+1}'], color=color, label=label, linewidth=1)
    axes[0, 0].set_ylabel('Active Power (W)')
    axes[0, 0].set_title('Active Power')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # Reactive power
    for i, (label, color) in enumerate(zip(['L1', 'L2', 'L3'], ['#e74c3c', '#2ecc71', '#3498db'])):
        axes[0, 1].plot(df['timestamp'], df[f'Q{i+1}'], color=color, label=label, linewidth=1)
    axes[0, 1].set_ylabel('Reactive Power (VAR)')
    axes[0, 1].set_title('Reactive Power')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # Power factor
    for i, (label, color) in enumerate(zip(['L1', 'L2', 'L3'], ['#e74c3c', '#2ecc71', '#3498db'])):
        axes[1, 0].plot(df['timestamp'], df[f'PF{i+1}'], color=color, label=label, linewidth=1)
    axes[1, 0].set_ylabel('Power Factor')
    axes[1, 0].set_title('Power Factor')
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].set_ylim(0, 1.05)

    # Frequency
    axes[1, 1].plot(df['timestamp'], df['freq'], color='#9b59b6', linewidth=1)
    axes[1, 1].axhline(y=50.0, color='gray', linestyle='--', alpha=0.5)
    axes[1, 1].set_ylabel('Frequency (Hz)')
    axes[1, 1].set_title('Mains Frequency')
    axes[1, 1].grid(True, alpha=0.3)

    for ax in axes.flat:
        ax.set_xlabel('Time')

    fig.suptitle(f'Power Analysis {title_suffix}')
    plt.tight_layout()
    return fig


def plot_harmonics(df, title_suffix=""):
    """Plot THD trends over time."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    for i, (label, color) in enumerate(zip(['L1', 'L2', 'L3'], ['#e74c3c', '#2ecc71', '#3498db'])):
        axes[i].plot(df['timestamp'], df[f'THD{i+1}'], color=color, linewidth=1)
        axes[i].set_ylabel(f'{label} THD (%)')
        axes[i].grid(True, alpha=0.3)
        axes[i].axhline(y=5.0, color='red', linestyle='--', alpha=0.5, label='5% limit')
        axes[i].legend()

    axes[2].set_xlabel('Time')
    fig.suptitle(f'Voltage THD Trends {title_suffix}')
    plt.tight_layout()
    return fig


def plot_phase_angles(df, title_suffix=""):
    """Plot V-I phase angles over time."""
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

    for i, (label, color) in enumerate(zip(['L1', 'L2', 'L3'], ['#e74c3c', '#2ecc71', '#3498db'])):
        axes[i].plot(df['timestamp'], df[f'phase_VI{i+1}'], color=color, linewidth=1)
        axes[i].set_ylabel(f'{label} V-I Angle (°)')
        axes[i].grid(True, alpha=0.3)

    axes[2].set_xlabel('Time')
    fig.suptitle(f'Phase Angle Trends {title_suffix}')
    plt.tight_layout()
    return fig


def generate_summary(df, title_suffix=""):
    """Print a statistical summary of the log data."""
    print(f"\n{'='*60}")
    print(f"Phase Scope Log Analysis {title_suffix}")
    print(f"{'='*60}")
    print(f"Duration: {df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]}")
    print(f"Samples: {len(df)}")
    print(f"\n--- Voltage ---")
    for i, label in enumerate(['L1', 'L2', 'L3']):
        col = f'V{i+1}_rms'
        print(f"  {label}: mean={df[col].mean():.1f}V  min={df[col].min():.1f}V  max={df[col].max():.1f}V  "
              f"std={df[col].std():.2f}V")

    print(f"\n--- Current ---")
    for i, label in enumerate(['L1', 'L2', 'L3']):
        col = f'I{i+1}_rms'
        print(f"  {label}: mean={df[col].mean():.2f}A  min={df[col].min():.2f}A  max={df[col].max():.2f}A  "
              f"std={df[col].std():.3f}A")

    print(f"\n--- Power ---")
    print(f"  Total P: mean={df['P_total'].mean():.0f}W  min={df['P_total'].min():.0f}W  max={df['P_total'].max():.0f}W")
    print(f"  Total Q: mean={df['Q_total'].mean():.0f}VAR  min={df['Q_total'].min():.0f}VAR  max={df['Q_total'].max():.0f}VAR")
    print(f"  Total S: mean={df['S_total'].mean():.0f}VA")

    print(f"\n--- Power Factor ---")
    for i, label in enumerate(['L1', 'L2', 'L3']):
        col = f'PF{i+1}'
        print(f"  {label}: mean={df[col].mean():.3f}  min={df[col].min():.3f}  max={df[col].max():.3f}")

    print(f"\n--- Frequency ---")
    print(f"  Mean: {df['freq'].mean():.3f} Hz  Min: {df['freq'].min():.3f} Hz  Max: {df['freq'].max():.3f} Hz")

    print(f"\n--- THD ---")
    for i, label in enumerate(['L1', 'L2', 'L3']):
        col = f'THD{i+1}'
        print(f"  {label}: mean={df[col].mean():.2f}%  max={df[col].max():.2f}%")

    print(f"\n--- Voltage Imbalance ---")
    v_mean = (df['V1_rms'].mean() + df['V2_rms'].mean() + df['V3_rms'].mean()) / 3
    for i, label in enumerate(['L1', 'L2', 'L3']):
        col = f'V{i+1}_rms'
        deviation = abs(df[col].mean() - v_mean) / v_mean * 100
        print(f"  {label}: {deviation:.2f}% deviation from average")

    print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(description='Phase Scope Waveform Analyzer')
    parser.add_argument('files', nargs='*', help='CSV log files to analyze')
    parser.add_argument('--dir', '-d', help='Directory containing CSV log files')
    parser.add_argument('--plot', '-p',
                        choices=['voltage', 'current', 'power', 'harmonics', 'phase', 'all'],
                        default='all',
                        help='Type of plot to generate')
    parser.add_argument('--summary', '-s', action='store_true',
                        help='Print statistical summary')
    parser.add_argument('--output', '-o', help='Save plots to file instead of displaying')
    args = parser.parse_args()

    # Collect CSV files
    csv_files = list(args.files)
    if args.dir:
        csv_files.extend(glob.glob(os.path.join(args.dir, 'LOG_*.CSV')))
        csv_files.extend(glob.glob(os.path.join(args.dir, 'LOG_*.csv')))

    if not csv_files:
        print("No CSV files specified. Use --dir or pass filenames.")
        return

    for filepath in csv_files:
        print(f"Loading {filepath}...")
        df = load_csv(filepath)
        title_suffix = f"({os.path.basename(filepath)})"

        if args.summary:
            generate_summary(df, title_suffix)

        if args.plot in ('voltage', 'all'):
            fig = plot_voltage(df, title_suffix)
            if args.output:
                fig.savefig(f"{os.path.splitext(filepath)[0]}_voltage.png", dpi=150)

        if args.plot in ('current', 'all'):
            fig = plot_current(df, title_suffix)
            if args.output:
                fig.savefig(f"{os.path.splitext(filepath)[0]}_current.png", dpi=150)

        if args.plot in ('power', 'all'):
            fig = plot_power(df, title_suffix)
            if args.output:
                fig.savefig(f"{os.path.splitext(filepath)[0]}_power.png", dpi=150)

        if args.plot in ('harmonics', 'all'):
            fig = plot_harmonics(df, title_suffix)
            if args.output:
                fig.savefig(f"{os.path.splitext(filepath)[0]}_harmonics.png", dpi=150)

        if args.plot in ('phase', 'all'):
            fig = plot_phase_angles(df, title_suffix)
            if args.output:
                fig.savefig(f"{os.path.splitext(filepath)[0]}_phase.png", dpi=150)

    if not args.output:
        plt.show()


if __name__ == '__main__':
    main()