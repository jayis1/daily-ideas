#!/usr/bin/env python3
"""
Cor Sono — analyze_log.py
Parse Cor Sono CSV + WAV logs, generate summary plots.

Usage:
    python3 analyze_log.py CS_20260803_101530.csv

Produces:
    - Heart rate trend plot
    - Classification distribution pie chart
    - WAV spectrogram
"""
import sys
import csv
import os
import struct
import wave
from collections import Counter
from datetime import datetime

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Install: pip install matplotlib numpy")
    sys.exit(1)


def parse_csv(path):
    """Parse Cor Sono CSV classification log."""
    times, classes, confs = [], [], []
    hr = None
    mode = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("# Mode:"):
                mode = line.split(":", 1)[1].strip()
            elif line.startswith("# Summary:"):
                parts = line.split("HR=")[1].split(",")
                hr = int(parts[0])
            elif line.startswith("#") or not line:
                continue
            else:
                parts = line.split(",")
                if len(parts) >= 4:
                    t = float(parts[0])
                    cls_id = int(parts[1])
                    cls_name = parts[2]
                    conf = int(parts[3])
                    times.append(t)
                    classes.append(cls_name)
                    confs.append(conf)
    return {"mode": mode, "hr": hr, "times": times, "classes": classes, "confs": confs}


def plot_wav_spectrogram(wav_path, ax):
    """Plot spectrogram of the contact mic channel."""
    if not os.path.exists(wav_path):
        ax.text(0.5, 0.5, "WAV not found", ha="center", va="center")
        return
    with wave.open(wav_path, "rb") as wf:
        n_ch = wf.getnchannels()
        sr = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    samples = np.frombuffer(raw, dtype=np.int16)
    if n_ch == 2:
        samples = samples[::2]  # contact channel only

    ax.specgram(samples, Fs=sr, NFFT=256, noverlap=128, cmap="viridis")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Frequency (Hz)")
    ax.set_title("PCG Spectrogram (Contact Mic)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_log.py <CS_xxxxx.csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    data = parse_csv(csv_path)

    print(f"=== Cor Sono Log Analysis ===")
    print(f"File: {csv_path}")
    print(f"Mode: {data['mode']}")
    print(f"Duration: {data['times'][-1]:.1f} s" if data["times"] else "No data")
    print(f"Mean HR: {data['hr']} BPM" if data["hr"] else "HR: N/A")
    print(f"Samples: {len(data['classes'])}")

    if data["classes"]:
        dist = Counter(data["classes"])
        print("\nClassification distribution:")
        for cls, count in dist.most_common():
            pct = 100 * count / len(data["classes"])
            print(f"  {cls:20s}: {count:3d} ({pct:5.1f}%)")

    # Plot
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle(f"Cor Sono Log — {os.path.basename(csv_path)}", fontsize=14)

    # HR / confidence trend
    if data["times"]:
        ax = axes[0, 0]
        ax.plot(data["times"], data["confs"], "b-o", ms=3)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Confidence (%)")
        ax.set_title("Classification Confidence Trend")
        ax.set_ylim(0, 100)
        ax.axhline(60, color="r", ls="--", label="Threshold")
        ax.legend()

    # Pie chart
    if data["classes"]:
        ax = axes[0, 1]
        dist = Counter(data["classes"])
        ax.pie(dist.values(), labels=dist.keys(), autopct="%1.1f%%")
        ax.set_title("Class Distribution")

    # Spectrogram
    wav_path = csv_path.replace(".csv", ".wav")
    plot_wav_spectrogram(wav_path, axes[1, 0])

    # Confidence histogram
    if data["confs"]:
        ax = axes[1, 1]
        ax.hist(data["confs"], bins=20, color="green", edgecolor="black")
        ax.set_xlabel("Confidence (%)")
        ax.set_ylabel("Count")
        ax.set_title("Confidence Histogram")

    plt.tight_layout()
    out = csv_path.replace(".csv", "_analysis.png")
    plt.savefig(out, dpi=150)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()