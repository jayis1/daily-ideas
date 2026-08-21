#!/usr/bin/env python3
"""
modal_fit.py — Resonance + damping extraction from a Vibra Beam velocity spectrum.

Finds the dominant resonance peak in [fmin, fmax], fits a single-DOF
second-order system |H(f)| = A / sqrt((1-(f/fn)^2)^2 + (2*zeta*f/fn)^2),
and reports fn, Q = 1/(2*zeta), damping ratio zeta, and -3dB bandwidth.

Usage:
    python3 modal_fit.py --input vibra.csv --fmin 10 --fmax 5000
"""
import argparse
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

def sdoj(f, fn, zeta, A):
    r = (f / fn) ** 2
    return A / np.sqrt((1 - r) ** 2 + (2 * zeta * r) ** 2)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--fmin", type=float, default=1.0)
    ap.add_argument("--fmax", type=float, default=100000.0)
    ap.add_argument("--rate", type=float, default=25000.0)
    args = ap.parse_args()

    df = pd.read_csv(args.input, names=["time_ms", "disp_nm", "vel_mms"])
    v = df["vel_mms"].to_numpy()
    t = df["time_ms"].to_numpy()
    if len(t) > 1:
        fs = 1.0 / (np.mean(np.diff(t)) / 1000.0)
    else:
        fs = args.rate
    N = len(v)
    freqs = np.fft.rfftfreq(N, 1/fs)
    mag = np.abs(np.fft.rfft(v * np.hanning(N)))

    mask = (freqs >= args.fmin) & (freqs <= args.fmax)
    f = freqs[mask]
    m = mag[mask]
    peak_idx = np.argmax(m)
    fn0 = f[peak_idx]
    A0 = m[peak_idx]
    try:
        popt, _ = curve_fit(sdoj, f, m, p0=[fn0, 0.05, A0], maxfev=10000)
        fn, zeta, A = popt
        Q = 1.0 / (2.0 * zeta) if zeta > 0 else float("inf")
        bw = fn / Q if Q > 0 else 0.0
        print(f"Resonance fn = {fn:.2f} Hz")
        print(f"Damping ratio zeta = {zeta:.4f}")
        print(f"Quality factor Q = {Q:.1f}")
        print(f"-3dB bandwidth = {bw:.2f} Hz")
        print(f"Peak amplitude = {A:.2f} mm/s")
        plt.semilogy(f, m, label="measured")
        plt.semilogy(f, sdoj(f, *popt), "--", label="fit")
        plt.xlabel("Frequency (Hz)"); plt.ylabel("|V| (mm/s)")
        plt.legend(); plt.title(f"Modal fit: fn={fn:.1f} Hz, Q={Q:.1f}")
        plt.show()
    except Exception as e:
        print(f"Fit failed: {e}")

if __name__ == "__main__":
    main()