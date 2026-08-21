#!/usr/bin/env python3
"""
analyze_log.py — Parse an Iono Pin session CSV and plot spectra + K0 reports.

Session CSV columns (one row per spectrum):
    time_ms, n_peaks, k0_0, amp_0, k0_1, amp_1, ..., k0_11, amp_11,
    compound, class, confidence, P_kPa, T_drift, T_amb

Usage:
    python analyze_log.py <session.csv> [--out report.png]
"""
import argparse
import csv
import sys
from pathlib import Path

import numpy as np

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Install matplotlib: pip install matplotlib")
    sys.exit(1)

CLASS_NAMES = {0: "NONE", 1: "EXPLOSIVE", 2: "DRUG", 3: "CWA",
               4: "TIC", 5: "VOC", 6: "REFERENCE"}
N_PEAKS = 12


def parse(path):
    rows = []
    with open(path, newline="") as f:
        rdr = csv.reader(f)
        for r in rdr:
            if not r or r[0].startswith("time"):
                continue
            try:
                time_ms = float(r[0]); n_peaks = int(r[1])
            except (ValueError, IndexError):
                continue
            k0s, amps = [], []
            off = 2
            for _ in range(N_PEAKS):
                k0 = float(r[off]); amp = float(r[off+1]); off += 2
                k0s.append(k0); amps.append(amp)
            compound = r[off]; cls = int(r[off+1]); conf = float(r[off+2])
            p = float(r[off+3]); td = float(r[off+4]); ta = float(r[off+5])
            rows.append({
                "time_ms": time_ms, "n_peaks": n_peaks,
                "k0s": k0s, "amps": amps, "compound": compound,
                "cls": cls, "conf": conf, "P": p, "T_drift": td, "T_amb": ta,
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--out", default="iono_report.png")
    args = ap.parse_args()

    rows = parse(args.csv)
    if not rows:
        print("No data rows found."); sys.exit(1)
    print(f"Parsed {len(rows)} spectra from {args.csv}")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))
    # K0 peaks over time (heatmap-like scatter)
    t = np.array([r["time_ms"]/1000.0 for r in rows])
    for i, r in enumerate(rows):
        for k, a in zip(r["k0s"][:r["n_peaks"]], r["amps"][:r["n_peaks"]]):
            ax1.scatter(r["time_ms"]/1000.0, k, s=a/200, c="steelblue", alpha=0.5)
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("K0 (cm²/V·s)")
    ax1.set_title("Detected peaks over session")
    ax1.grid(True, alpha=0.3)
    ax1.axhline(2.70, color="g", ls="--", alpha=0.5, label="RIP (2.70)")
    ax1.legend()

    # Classification confidence over time
    confs = [r["conf"] for r in rows]
    classes = [CLASS_NAMES.get(r["cls"], "?") for r in rows]
    ax2.plot(t, confs, "b.-")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Confidence")
    ax2.set_ylim(0, 1)
    ax2.set_title("Classification confidence")
    ax2.grid(True, alpha=0.3)
    # annotate the best hit
    best = max(rows, key=lambda r: r["conf"])
    ax2.text(0.02, 0.95, f"Best: {best['compound']} [{CLASS_NAMES.get(best['cls'],'?')}] "
             f"conf={best['conf']*100:.0f}% at t={best['time_ms']/1000:.1f}s",
             transform=ax2.transAxes, va="top", fontfamily="monospace",
             bbox=dict(boxstyle="round", fc="lightyellow"))

    plt.tight_layout()
    out = Path(args.out)
    plt.savefig(out, dpi=150)
    print(f"Report saved to {out}")

    # Summary table
    print("\n=== Session summary ===")
    print(f"Duration: {rows[-1]['time_ms']/1000:.1f} s")
    print(f"Spectra:  {len(rows)}")
    classes_seen = {}
    for r in rows:
        key = (r["compound"], classes[r["cls"]])
        classes_seen[key] = classes_seen.get(key, 0) + 1
    for (name, cls), cnt in sorted(classes_seen.items(), key=lambda x: -x[1]):
        print(f"  {name:24s} [{cls:10s}] x{cnt}")


if __name__ == "__main__":
    main()