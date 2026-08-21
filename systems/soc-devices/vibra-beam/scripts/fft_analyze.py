#!/usr/bin/env python3
"""
fft_analyze.py — Offline FFT / spectrogram analysis of a Vibra Beam CSV.

Usage:
    python3 fft_analyze.py --input vibra.csv --fft 4096 --overlap 0.75
"""
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--fft", type=int, default=4096)
    ap.add_argument("--overlap", type=float, default=0.75)
    ap.add_argument("--rate", type=float, default=25000.0,
                    help="Sample rate (Hz) — infer from CSV time if present")
    args = ap.parse_args()

    df = pd.read_csv(args.input, names=["time_ms", "disp_nm", "vel_mms"])
    v = df["vel_mms"].to_numpy()
    t = df["time_ms"].to_numpy()
    if len(t) > 1:
        dt = np.mean(np.diff(t)) / 1000.0
        fs = 1.0 / dt
    else:
        fs = args.rate
    print(f"Loaded {len(v)} samples @ {fs:.1f} Hz")

    N = args.fft
    win = np.hanning(N)
    hop = int(N * (1 - args.overlap))
    n_frames = (len(v) - N) // hop + 1
    spec = np.zeros((n_frames, N // 2))
    for i in range(n_frames):
        seg = v[i*hop : i*hop + N] * win
        spec[i] = np.abs(np.fft.rfft(seg))[:N//2]

    freqs = np.fft.rfftfreq(N, 1/fs)[:N//2]
    times = np.arange(n_frames) * hop / fs

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
    ax1.plot(t / 1000.0, v, lw=0.5)
    ax1.set_xlabel("Time (s)"); ax1.set_ylabel("Velocity (mm/s)")
    ax1.set_title("Waveform")
    ax2.pcolormesh(times, freqs, spec.T, shading="auto", cmap="magma")
    ax2.set_xlabel("Time (s)"); ax2.set_ylabel("Frequency (Hz)")
    ax2.set_title("Spectrogram")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()