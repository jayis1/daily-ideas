#!/usr/bin/env python3
"""
voigt_fit.py — Offline Voigt viscoelastic model fitting

Cross-check for the on-device Voigt fitting. Reads QCM Halo CSV logs
and fits the Voinova (1999) Voigt model to multi-overtone Δf/ΔD data.

Usage:
    python3 voigt_fit.py <csv_file> [--rho_f 1.0] [--rho_l 1000] [--eta_l 0.001]

Requires: numpy, scipy, matplotlib
"""

import sys
import argparse
import numpy as np
from scipy.optimize import least_squares

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

# Physical constants
RHO_Q = 2650.0      # kg/m³
MU_Q = 2.947e10     # Pa
PI = np.pi

def voigt_load_impedance(f, df_film, eta_f, mu_f, rho_f, rho_l, eta_l):
    """Compute complex load impedance for a Voigt layer on liquid."""
    omega = 2 * PI * f

    # Complex shear moduli
    G_f = mu_f + 1j * omega * eta_f
    G_l = 1j * omega * eta_l

    # Complex wave impedances
    xi_f = np.sqrt(rho_f * G_f)
    xi_l = np.sqrt(rho_l * G_l)

    # Complex wave number in film
    kf = np.sqrt(rho_f * 1j * omega / G_f)
    kf_df = kf * df_film

    cosh_kd = np.cosh(kf_df)
    sinh_kd = np.sinh(kf_df)

    # Load impedance
    num = xi_f * cosh_kd + xi_l * sinh_kd
    den = xi_l * cosh_kd + xi_f * sinh_kd

    return xi_l * num / den

def voigt_predict(params, f_n, f0, rho_q, mu_q, rho_l, eta_l, rho_f):
    """Predict Δf and ΔD for all overtones."""
    df_film, eta_f, mu_f = params
    n = f_n / f0  # overtone numbers
    tq = np.sqrt(mu_q / rho_q) / (2 * PI * f0)

    df_pred = np.zeros(len(f_n))
    dd_pred = np.zeros(len(f_n))

    for i, f in enumerate(f_n):
        xi = voigt_load_impedance(f, df_film, eta_f, mu_f, rho_f, rho_l, eta_l)
        df_pred[i] = -xi.imag * n[i] / (2 * PI * rho_q * tq)
        dd_pred[i] = -xi.real * n[i] / (PI * f0 * rho_q * tq)

    return df_pred, dd_pred

def residuals(params, f_n, df_meas, dd_meas, f0, rho_q, mu_q, rho_l, eta_l, rho_f):
    df_pred, dd_pred = voigt_predict(params, f_n, f0, rho_q, mu_q, rho_l, eta_l, rho_f)
    # Weight ΔD more heavily (smaller magnitude)
    return np.concatenate([df_pred - df_meas, (dd_pred - dd_meas) * 1e6])

def fit_voigt(f_n, df_meas, dd_meas, f0=5e6, rho_f=1000, rho_l=1000, eta_l=0.001):
    """Fit Voigt model and return parameters."""
    # Initial guess: thickness from Sauerbrey, water-like viscosity, soft gel modulus
    sauerbrey_mass = -df_meas[0] * 0.196e-7 * np.sqrt(RHO_Q * MU_Q) / (2 * f0**2) * 1e8
    d_init = max(sauerbrey_mass / (rho_f / 1000 * 100), 0.1) * 1e-9  # m

    p0 = [d_init, 0.001, 1e5]  # [d_f (m), eta_f (Pa·s), mu_f (Pa)]

    # Bounds: d_f > 0, eta_f > 1e-6, mu_f > 1e3
    lower = [1e-10, 1e-6, 1e3]
    upper = [1e-4, 100, 1e9]

    result = least_squares(
        residuals, p0, bounds=(lower, upper),
        args=(f_n, df_meas, dd_meas, f0, RHO_Q, MU_Q, rho_l, eta_l, rho_f),
        method='trf', max_nfev=1000
    )

    return {
        'thickness_nm': result.x[0] * 1e9,
        'viscosity_pa_s': result.x[1],
        'shear_mod_pa': result.x[2],
        'success': result.success,
        'cost': result.cost,
    }

def parse_csv(filename):
    """Parse overtone sweep CSV from QCM Halo."""
    f_n = []
    df = []
    dd = []
    temp = 25.0

    with open(filename) as f:
        for line in f:
            line = line.strip()
            if line.startswith('#'):
                if 'T=' in line:
                    temp = float(line.split('T=')[1].split()[0])
                continue
            parts = line.split(',')
            if len(parts) >= 4 and parts[0] in ('1st','3rd','5th','7th','9th','11th'):
                n = int(parts[0].replace('th','').replace('st',''))
                f = float(parts[1])
                df_val = float(parts[2])
                dd_val = float(parts[3])
                f_n.append(f)
                df.append(df_val)
                dd.append(dd_val)

    return np.array(f_n), np.array(df), np.array(dd), temp

def main():
    parser = argparse.ArgumentParser(description='Voigt model fitting for QCM Halo')
    parser.add_argument('csv_file', help='Overtone sweep CSV file')
    parser.add_argument('--rho_f', type=float, default=1000, help='Film density (kg/m³)')
    parser.add_argument('--rho_l', type=float, default=1000, help='Liquid density (kg/m³)')
    parser.add_argument('--eta_l', type=float, default=0.001, help='Liquid viscosity (Pa·s)')
    parser.add_argument('--f0', type=float, default=5e6, help='Fundamental frequency (Hz)')
    args = parser.parse_args()

    f_n, df, dd, temp = parse_csv(args.csv_file)

    print(f"Loaded {len(f_n)} overtones at T={temp:.1f}°C")
    print(f"  Overtone  Δf (Hz)    ΔD")
    for i, f in enumerate(f_n):
        n = int(round(f / args.f0))
        print(f"  {n:2d}        {df[i]:+.2f}    {dd[i]:.3e}")

    print(f"\nFitting Voigt model (ρ_f={args.rho_f}, ρ_l={args.rho_l}, η_l={args.eta_l})...")
    result = fit_voigt(f_n, df, dd, args.f0, args.rho_f, args.rho_l, args.eta_l)

    print(f"\n── Voigt Fit Results ──")
    print(f"  Thickness:  {result['thickness_nm']:.2f} nm")
    print(f"  Viscosity:  {result['viscosity_pa_s']:.3e} Pa·s")
    print(f"  Shear mod:  {result['shear_mod_pa']:.3e} Pa")
    print(f"  Converged:  {'YES' if result['success'] else 'NO'}")
    print(f"  Cost:       {result['cost']:.6e}")

    if plt:
        # Plot measured vs predicted
        df_pred, dd_pred = voigt_predict(
            [result['thickness_nm']*1e-9, result['viscosity_pa_s'], result['shear_mod_pa']],
            f_n, args.f0, RHO_Q, MU_Q, args.rho_l, args.eta_l, args.rho_f
        )

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
        n = f_n / args.f0
        ax1.plot(n, df, 'bo', label='Measured')
        ax1.plot(n, df_pred, 'b--', label='Voigt fit')
        ax1.set_xlabel('Overtone number')
        ax1.set_ylabel('Δf (Hz)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        ax2.plot(n, dd, 'ro', label='Measured')
        ax2.plot(n, dd_pred, 'r--', label='Voigt fit')
        ax2.set_xlabel('Overtone number')
        ax2.set_ylabel('ΔD')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        fig.suptitle(f"Voigt Fit: d={result['thickness_nm']:.1f}nm, "
                     f"η={result['viscosity_pa_s']:.1e}Pa·s, "
                     f"μ={result['shear_mod_pa']:.1e}Pa")
        plt.tight_layout()
        plt.savefig(args.csv_file.replace('.csv', '_voigt.png'), dpi=150)
        print(f"\nPlot saved: {args.csv_file.replace('.csv', '_voigt.png')}")
        plt.show()

if __name__ == "__main__":
    main()