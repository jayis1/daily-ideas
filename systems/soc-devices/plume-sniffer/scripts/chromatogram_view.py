#!/usr/bin/env python3
"""chromatogram_view.py — Offline chromatogram viewer for Plume Sniffer SD logs.

Loads a RUN_NNNN.csv file from the SD card and displays the chromatogram
with automatic peak detection and compound labeling.

Usage:
    python3 chromatogram_view.py RUN_0001.csv
    python3 chromatogram_view.py RUN_0001.csv --meta RUN_0001_meta.txt
"""

import argparse
import csv
import sys
import re
from dataclasses import dataclass

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Install matplotlib:  pip install matplotlib")
    sys.exit(1)
import numpy as np


@dataclass
class Peak:
    retention_s: float
    retention_index: float
    name: str
    conc_ppm: float
    area: float
    height: float


def load_csv(path):
    """Load a Plume Sniffer RUN_NNNN.csv file."""
    header = {}
    times = []
    raw = []
    baseline = []
    corrected = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                m = re.match(r"#\s*(\S+):\s*(.+)", line)
                if m:
                    header[m.group(1)] = m.group(2).strip()
            elif line.startswith("time_s"):
                continue
            elif line:
                parts = line.split(",")
                if len(parts) >= 4:
                    times.append(float(parts[0]))
                    raw.append(float(parts[1]))
                    baseline.append(float(parts[2]))
                    corrected.append(float(parts[3]))

    return header, np.array(times), np.array(corrected)


def load_meta(path):
    """Load a RUN_NNNN_meta.txt file and return list of Peak objects."""
    peaks = []
    with open(path) as f:
        in_table = False
        for line in f:
            line = line.strip()
            if line.startswith("tR_s"):
                in_table = True
                continue
            if in_table and line:
                parts = re.split(r"\s+", line)
                if len(parts) >= 6:
                    peaks.append(Peak(
                        retention_s=float(parts[0]),
                        retention_index=float(parts[1]),
                        name=parts[2],
                        conc_ppm=float(parts[3]),
                        area=float(parts[4]),
                        height=float(parts[5]),
                    ))
    return peaks


def detect_peaks(signal, times, noise_sigma=5.0, min_height=25.0):
    """Simple peak detection — for offline viewing only."""
    if len(signal) < 5:
        return []
    deriv = np.gradient(signal, times)
    threshold = 3.0 * noise_sigma * 50  # per-sample
    peaks = []
    i = 1
    while i < len(signal) - 1:
        if deriv[i] > threshold:
            start = i
            while i < len(signal) - 1 and deriv[i] > -threshold:
                i += 1
            apex = start + int(np.argmax(signal[start:i+1]))
            height = signal[apex]
            if height > min_height:
                peaks.append((times[apex], height))
        i += 1
    return peaks


def main():
    ap = argparse.ArgumentParser(description="Plume Sniffer chromatogram viewer")
    ap.add_argument("csv", help="RUN_NNNN.csv file path")
    ap.add_argument("--meta", help="RUN_NNNN_meta.txt file path")
    ap.add_argument("--save", help="Save plot to PNG file")
    args = ap.parse_args()

    header, times, corrected = load_csv(args.csv)
    print(f"Loaded {len(times)} samples")
    print(f"  Method: {header.get('Method', '?')}")
    print(f"  Sample volume: {header.get('Sample volume', '?')}")
    print(f"  Duration: {times[-1]:.1f}s")

    peaks = []
    if args.meta:
        peaks = load_meta(args.meta)
        print(f"\nPeak table ({len(peaks)} peaks):")
        print(f"  {'tR (s)':>8}  {'RI':>5}  {'Compound':16s}  {'ppm':>8}")
        for p in peaks:
            print(f"  {p.retention_s:8.1f}  {p.retention_index:5.0f}  "
                  f"{p.name:16s}  {p.conc_ppm:8.0f}")
    else:
        detected = detect_peaks(corrected, times)
        print(f"\nDetected {len(detected)} peaks (offline, approximate):")
        for tR, h in detected:
            print(f"  tR={tR:.1f}s  height={h:.0f}µV")

    # Plot
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(times, corrected, linewidth=0.5, color='blue', label='TCD (corrected)')
    ax.axhline(0, color='gray', linewidth=0.3)

    if args.meta and peaks:
        for p in peaks:
            # Find the y-value at the peak's retention time
            idx = int(np.argmin(np.abs(times - p.retention_s)))
            y = corrected[idx] if idx < len(corrected) else 0
            ax.annotate(f"{p.name}\n{p.conc_ppm:.0f}ppm",
                       (p.retention_s, y),
                       textcoords="offset points", xytext=(0, 10),
                       fontsize=7, ha='center',
                       arrowprops=dict(arrowstyle='->', lw=0.5))
            ax.plot(p.retention_s, y, 'ro', markersize=3)

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("TCD Signal (µV, baseline-corrected)")
    ax.set_title(f"Plume Sniffer — {header.get('Method', '?')} — "
                 f"{header.get('Sample volume', '?')}")
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    if args.save:
        plt.savefig(args.save, dpi=150)
        print(f"Saved plot to {args.save}")
    else:
        plt.show()


if __name__ == "__main__":
    main()