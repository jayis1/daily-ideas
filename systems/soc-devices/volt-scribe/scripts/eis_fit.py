#!/usr/bin/env python3
"""
eis_fit.py — Electrochemical Impedance Spectroscopy circuit fitting tool

Fits a Randles equivalent circuit (R_s + (C_dl ∥ (R_ct + Z_W))) to
measured EIS data using scipy.optimize.least_squares.

Usage:
    python3 eis_fit.py eis_data.csv
    python3 eis_fit.py --circuit randles eis_data.csv
    python3 eis_fit.py --simulate R_s=100 R_ct=2000 C_dl=20e-6

Requires: numpy, scipy, matplotlib
Install: pip install numpy scipy matplotlib
"""

import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares


def randles_impedance(params, freq):
    """
    Compute Randles equivalent circuit impedance.
    
    Circuit: R_s + (C_dl ∥ (R_ct + Z_W))
    where Z_W = σ_w * (1-j) / √(2ω)  (Warburg impedance)
    
    params = [R_s, R_ct, C_dl, alpha, sigma_w]
    """
    R_s, R_ct, C_dl, alpha, sigma_w = params
    omega = 2 * np.pi * freq

    # Constant Phase Element: Z_CPE = 1 / (C_dl * (jω)^α)
    # (jω)^α = ω^α * (cos(απ/2) + j*sin(απ/2))
    jw_alpha_re = omega**alpha * np.cos(alpha * np.pi / 2)
    jw_alpha_im = omega**alpha * np.sin(alpha * np.pi / 2)

    # Z_CPE = 1 / (C_dl * (jw_alpha_re + j*jw_alpha_im))
    denom_re = C_dl * jw_alpha_re
    denom_im = C_dl * jw_alpha_im
    denom_mag2 = denom_re**2 + denom_im**2
    denom_mag2 = np.maximum(denom_mag2, 1e-30)

    Z_cpe_re = denom_re / denom_mag2
    Z_cpe_im = -denom_im / denom_mag2

    # Warburg impedance: Z_W = σ_w * (1-j) / √(2ω)
    sqrt_2w = np.sqrt(2 * omega)
    sqrt_2w = np.maximum(sqrt_2w, 1e-10)
    Z_w_re = sigma_w / sqrt_2w
    Z_w_im = -sigma_w / sqrt_2w

    # Branch 2: R_ct + Z_W
    z2_re = R_ct + Z_w_re
    z2_im = Z_w_im

    # Parallel: Z_cpe ∥ (R_ct + Z_W)
    # 1/Z_par = 1/Z_cpe + 1/Z2
    z1_mag2 = Z_cpe_re**2 + Z_cpe_im**2
    z1_mag2 = np.maximum(z1_mag2, 1e-30)
    inv_z1_re = Z_cpe_re / z1_mag2
    inv_z1_im = -Z_cpe_im / z1_mag2

    z2_mag2 = z2_re**2 + z2_im**2
    z2_mag2 = np.maximum(z2_mag2, 1e-30)
    inv_z2_re = z2_re / z2_mag2
    inv_z2_im = -z2_im / z2_mag2

    inv_par_re = inv_z1_re + inv_z2_re
    inv_par_im = inv_z1_im + inv_z2_im

    inv_par_mag2 = inv_par_re**2 + inv_par_im**2
    inv_par_mag2 = np.maximum(inv_par_mag2, 1e-30)

    z_par_re = inv_par_re / inv_par_mag2
    z_par_im = -inv_par_im / inv_par_mag2

    # Total: Z = R_s + Z_parallel
    Z_re = R_s + z_par_re
    Z_im = z_par_im

    return Z_re, Z_im


def residuals(params, freq, Z_real_data, Z_imag_data):
    """Compute residuals for least-squares fitting."""
    Z_re, Z_im = randles_impedance(params, freq)
    # Weight real and imaginary equally
    resid_re = (Z_re - Z_real_data) / np.maximum(np.abs(Z_real_data), 1.0)
    resid_im = (Z_im - Z_imag_data) / np.maximum(np.abs(Z_imag_data), 1.0)
    return np.concatenate([resid_re, resid_im])


def fit_randles(freq, Z_real, Z_imag):
    """Fit Randles circuit to EIS data."""
    # Initial estimates from data
    R_s_est = np.min(Z_real)
    R_ct_est = np.max(Z_real) - R_s_est
    if R_ct_est < 1:
        R_ct_est = 1000.0

    # Find peak -Z_imag for C_dl estimate
    neg_Z_imag = -Z_imag
    peak_idx = np.argmax(neg_Z_imag)
    f_peak = freq[peak_idx]
    C_dl_est = 1.0 / (2 * np.pi * max(f_peak, 0.1) * max(R_ct_est, 1.0))
    if C_dl_est <= 0 or np.isnan(C_dl_est):
        C_dl_est = 1e-5

    # Bounds: R_s > 0, R_ct > 0, C_dl > 0, 0.5 < alpha < 1, sigma_w >= 0
    p0 = [R_s_est, R_ct_est, C_dl_est, 0.9, 0.0]
    bounds = ([0.1, 1.0, 1e-12, 0.5, 0.0],
              [1e6, 1e9, 1.0, 1.0, 1e6])

    result = least_squares(residuals, p0, args=(freq, Z_real, Z_imag),
                          bounds=bounds, method='trf', max_nfev=10000)

    return result.x, result.cost, result.success


def simulate_eis(params, freq_range=(1, 100000), points_per_decade=10):
    """Simulate EIS data for given Randles parameters."""
    freq = np.logspace(np.log10(freq_range[0]), np.log10(freq_range[1]),
                       points_per_decade * 6)
    Z_re, Z_im = randles_impedance(params, freq)
    return freq, Z_re, Z_im


def load_eis_csv(filename):
    """Load EIS data from CSV file."""
    freq, z_real, z_imag = [], [], []
    with open(filename, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            try:
                freq.append(float(row[0]))
                z_real.append(float(row[1]))
                z_imag.append(float(row[2]))
            except (ValueError, IndexError):
                continue
    return np.array(freq), np.array(z_real), np.array(z_imag)


def plot_eis(freq, Z_real, Z_imag, params=None, title="EIS"):
    """Plot Nyquist and Bode diagrams."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available. Install with: pip install matplotlib")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Nyquist
    ax1.plot(Z_real, -Z_imag, "ro", markersize=3, label="Data")

    if params is not None:
        freq_fine = np.logspace(np.log10(freq[0]), np.log10(freq[-1]), 200)
        Z_re_fit, Z_im_fit = randles_impedance(params, freq_fine)
        ax1.plot(Z_re_fit, -Z_im_fit, "b-", linewidth=1, label="Fit")

    ax1.set_xlabel("Z' (Ω)")
    ax1.set_ylabel("-Z'' (Ω)")
    ax1.set_title("Nyquist Plot")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect("equal")

    # Bode
    magnitude = np.sqrt(Z_real**2 + Z_imag**2)
    phase = np.degrees(np.arctan2(Z_imag, Z_real))

    ax2.semilogx(freq, magnitude, "ro", markersize=3, label="|Z|")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("|Z| (Ω)", color="r")
    ax2.tick_params(axis="y", labelcolor="r")
    ax2.grid(True, alpha=0.3)

    ax2b = ax2.twinx()
    ax2b.semilogx(freq, phase, "bs", markersize=3, label="Phase")
    ax2b.set_ylabel("Phase (°)", color="b")
    ax2b.tick_params(axis="y", labelcolor="b")
    ax2.set_title("Bode Plot")

    if params is not None:
        fig.suptitle(f"Randles Fit: R_s={params[0]:.0f}Ω, R_ct={params[1]:.0f}Ω, "
                     f"C_dl={params[2]*1e6:.2f}µF, α={params[3]:.2f}")

    plt.tight_layout()
    plt.savefig("eis_fit.png", dpi=150)
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="EIS Circuit Fitting Tool")
    parser.add_argument("file", nargs="?", help="EIS CSV file")
    parser.add_argument("--simulate", action="store_true",
                       help="Simulate EIS data instead of fitting")
    parser.add_argument("--plot", action="store_true", default=True,
                       help="Plot results (default: True)")
    parser.add_argument("--R_s", type=float, default=100,
                       help="Solution resistance (Ω) for simulation")
    parser.add_argument("--R_ct", type=float, default=2000,
                       help="Charge transfer resistance (Ω) for simulation")
    parser.add_argument("--C_dl", type=float, default=20e-6,
                       help="Double layer capacitance (F) for simulation")
    parser.add_argument("--alpha", type=float, default=0.9,
                       help="CPE exponent (0-1) for simulation")
    parser.add_argument("--sigma_w", type=float, default=0,
                       help="Warburg coefficient (Ω/√Hz) for simulation")

    args = parser.parse_args()

    if args.simulate:
        print(f"Simulating Randles circuit:")
        print(f"  R_s   = {args.R_s:.0f} Ω")
        print(f"  R_ct  = {args.R_ct:.0f} Ω")
        print(f"  C_dl  = {args.C_dl*1e6:.2f} µF")
        print(f"  α     = {args.alpha:.2f}")
        print(f"  σ_w   = {args.sigma_w:.1f} Ω/√Hz")

        freq, Z_real, Z_imag = simulate_eis(
            [args.R_s, args.R_ct, args.C_dl, args.alpha, args.sigma_w]
        )
        plot_eis(freq, Z_real, Z_imag,
                params=[args.R_s, args.R_ct, args.C_dl, args.alpha, args.sigma_w],
                title="Simulated EIS")
        return

    if args.file is None:
        parser.print_help()
        return

    # Load and fit
    freq, Z_real, Z_imag = load_eis_csv(args.file)
    print(f"Loaded {len(freq)} data points from {args.file}")

    params, cost, success = fit_randles(freq, Z_real, Z_imag)
    R_s, R_ct, C_dl, alpha, sigma_w = params

    print(f"\nFitted Randles Circuit Parameters:")
    print(f"  R_s   = {R_s:.1f} Ω")
    print(f"  R_ct  = {R_ct:.1f} Ω")
    print(f"  C_dl  = {C_dl*1e6:.3f} µF")
    print(f"  α     = {alpha:.3f}")
    print(f"  σ_w   = {sigma_w:.1f} Ω/√Hz")
    print(f"  Cost  = {cost:.6f}")
    print(f"  Success: {success}")

    if args.plot:
        plot_eis(freq, Z_real, Z_imag, params=params, title=args.file)


if __name__ == "__main__":
    main()