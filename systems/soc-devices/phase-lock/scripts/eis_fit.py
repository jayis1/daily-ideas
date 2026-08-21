#!/usr/bin/env python3
"""
eis_fit.py — fit EIS (electrochemical impedance spectroscopy) data
from a Phase Lock frequency sweep to a Randles equivalent circuit.

The Randles circuit:   R_s + (R_ct ∥ C_dl) + W (Warburg)

     R_s ──┬── R_ct ──┬── W
           │          │
           └── C_dl ──┘

Impedance:  Z(ω) = R_s + R_ct/(1 + jωR_ctC_dl) + σ(1-j)/√ω

Reads a Phase Lock sweep CSV (SWP_NNNN.csv) and fits the parameters.

Usage:
    python eis_fit.py SWP_0001.csv
    python eis_fit.py SWP_0001.csv --plot
"""
import argparse
import numpy as np
from scipy.optimize import curve_fit

def parse_sweep_csv(path):
    """Parse a Phase Lock SWP_NNNN.csv → (f, R, theta) arrays."""
    f, R, theta = [], [], []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("f,"):
                continue
            parts = line.split(",")
            if len(parts) < 7:
                continue
            try:
                ff = float(parts[0])
                RR = float(parts[2])
                th = float(parts[3])
            except ValueError:
                continue
            f.append(ff); R.append(RR); theta.append(th)
    return np.array(f), np.array(R), np.array(theta)

def randles_z(f, Rs, Rct, Cdl, sigma):
    """Complex impedance of the Randles circuit."""
    w = 2 * np.pi * f
    Zw = sigma * (1 - 1j) / np.sqrt(w)   # Warburg
    Zct = Rct / (1 + 1j * w * Rct * Cdl)
    return Rs + Zct + Zw

def fit_randles(f, R, theta):
    """Fit |Z| and θ to the Randles model. Returns (Rs, Rct, Cdl, sigma)."""
    Z = R * np.exp(1j * theta)

    def residuals(params):
        Rs, Rct, Cdl, sigma = params
        Zfit = randles_z(f, Rs, Rct, Cdl, sigma)
        return np.concatenate([Zfit.real - Z.real, Zfit.imag - Z.imag])

    # Initial guesses
    p0 = [R[-1] * 0.1, R[np.argmin(R)] * 0.5, 1e-6, R[0] * 0.01]
    from scipy.optimize import least_squares
    result = least_squares(residuals, p0, bounds=([0, 0, 0, 0], [10, 10, 1, 10]))
    return result.x

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="SWP_NNNN.csv file path")
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    f, R, theta = parse_sweep_csv(args.csv)
    print(f"Parsed {len(f)} points: f = {f.min():.1f} – {f.max():.0f} Hz")

    Rs, Rct, Cdl, sigma = fit_randles(f, R, theta)
    print("\nRandles fit:")
    print(f"  R_s  (solution resistance)    = {Rs*1000:.1f} mΩ")
    print(f"  R_ct (charge-transfer resist) = {Rct*1000:.1f} mΩ")
    print(f"  C_dl (double-layer capacitance) = {Cdl*1e6:.2f} µF")
    print(f"  σ    (Warburg coefficient)     = {sigma*1000:.1f} mΩ·√Hz")

    if args.plot:
        import matplotlib.pyplot as plt
        Z = R * np.exp(1j * theta)
        Zfit = randles_z(f, Rs, Rct, Cdl, sigma)

        fig, (ax1, ax2) = plt.subplots(2, 1)
        ax1.semilogx(f, np.abs(Z), 'bo-', label='measured |Z|')
        ax1.semilogx(f, np.abs(Zfit), 'r--', label='fit |Z|')
        ax1.set_ylabel('|Z| (Ω)'); ax1.legend()

        ax2.semilogx(f, np.angle(Z, deg=True), 'bo-', label='measured θ')
        ax2.semilogx(f, np.angle(Zfit, deg=True), 'r--', label='fit θ')
        ax2.set_ylabel('θ (°)'); ax2.set_xlabel('f (Hz)'); ax2.legend()
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    main()