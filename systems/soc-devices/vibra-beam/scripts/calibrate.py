#!/usr/bin/env python3
"""
calibrate.py — Vibra Beam fringe / velocity scale calibration utility.

Two modes:
  1. Fringe: point at a static target, verify the I/Q Lissajous is a clean
     circle, and measure the DC offset + radius for baseline subtraction.
  2. Velocity: drive a target at a known frequency and displacement
     (e.g., a speaker at f Hz, x um peak), and verify the measured
     velocity equals 2*pi*f*x mm/s.

Usage:
    python3 calibrate.py --mode fringe --input vibra.iq
    python3 calibrate.py --mode velocity --input vibra.csv --freq 1000 --disp 1.0
"""
import argparse
import numpy as np
import pandas as pd

def read_iq(path):
    """Parse the binary I/Q log format."""
    with open(path, "rb") as f:
        data = f.read()
    samples = []
    i = 0
    while i + 8 <= len(data):
        t_ms = int.from_bytes(data[i:i+4], "little"); i += 4
        n    = int.from_bytes(data[i:i+4], "little"); i += 4
        for _ in range(n):
            if i + 4 > len(data): break
            iv = int.from_bytes(data[i:i+2],   "little", signed=True); i += 2
            qv = int.from_bytes(data[i:i+2],   "little", signed=True); i += 2
            samples.append((t_ms, iv, qv))
    return np.array(samples)

def fringe_mode(path):
    arr = read_iq(path)
    if len(arr) == 0:
        print("No I/Q samples in file"); return
    I = arr[:, 1].astype(float)
    Q = arr[:, 2].astype(float)
    dc_i = np.mean(I); dc_q = np.mean(Q)
    radius = np.mean(np.sqrt((I - dc_i)**2 + (Q - dc_q)**2))
    print(f"DC offset: I={dc_i:.1f}, Q={dc_q:.1f}")
    print(f"Mean fringe radius: {radius:.1f} LSB")
    print(f"Eccentricity: {np.std(np.sqrt((I-dc_i)**2+(Q-dc_q)**2)):.1f} LSB")
    print("If radius > 200 LSB and eccentricity < 20 LSB, the interferometer is well aligned.")

def velocity_mode(path, freq_hz, disp_um):
    df = pd.read_csv(path, names=["time_ms", "disp_nm", "vel_mms"])
    v = df["vel_mms"].to_numpy()
    expected = 2 * np.pi * freq_hz * disp_um * 1e-3  # mm/s
    measured = np.max(np.abs(v))
    print(f"Expected peak velocity: {expected:.3f} mm/s")
    print(f"Measured peak velocity: {measured:.3f} mm/s")
    print(f"Scale factor: {expected / (measured + 1e-9):.4f}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["fringe", "velocity"], required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--freq", type=float, default=1000.0)
    ap.add_argument("--disp", type=float, default=1.0, help="Target displacement (um peak)")
    args = ap.parse_args()
    if args.mode == "fringe":
        fringe_mode(args.input)
    else:
        velocity_mode(args.input, args.freq, args.disp)