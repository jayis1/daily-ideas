#!/usr/bin/env python3
"""
stern_volmer.py — Stern-Volmer quenching analysis tool

Analyzes fluorescence quenching data to determine:
  - Stern-Volmer quenching constant (Ksv)
  - Bimolecular quenching rate (kq = Ksv / τ0)
  - Quencher concentration from measured fluorescence
  - Static vs. dynamic quenching (via temperature dependence)

Stern-Volmer equation: F0/F = 1 + Ksv × [Q]

Usage:
    python3 stern_volmer.py --input quench_data.csv
    python3 stern_volmer.py --F0 10000 --Ksv 200 --Q 0.005
"""

import argparse
import math
import json
import sys

try:
    import numpy as np
except ImportError:
    np = None


def fit_stern_volmer(concentrations: list, F_values: list, F0: float = None):
    """
    Fit Stern-Volmer equation: F0/F = 1 + Ksv × [Q]

    Args:
        concentrations: List of quencher concentrations [Q] (M)
        F_values: List of fluorescence intensities at each [Q]
        F0: Fluorescence at [Q]=0 (auto-determined if None)

    Returns:
        dict with Ksv, R², kq (if τ0 provided)
    """
    if F0 is None:
        # Use the first data point (lowest concentration) as F0
        F0 = F_values[0]

    # Compute F0/F for each data point
    sv_ratios = []
    for F in F_values:
        if F > 0:
            sv_ratios.append(F0 / F)
        else:
            sv_ratios.append(float("inf"))

    # Linear fit: y = 1 + Ksv × x
    # y = F0/F, x = [Q]
    x = np.array(concentrations) if np else concentrations
    y = np.array(sv_ratios) if np else sv_ratios

    if np:
        # Linear regression via least squares
        n = len(x)
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_x2 = np.sum(x * x)

        Ksv = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        intercept = (sum_y - Ksv * sum_x) / n

        # R²
        y_pred = Ksv * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    else:
        # Simple linear fit without numpy
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)

        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            Ksv = 0
        else:
            Ksv = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - Ksv * sum_x) / n
        r2 = 0  # simplified

    return {
        "F0": F0,
        "Ksv": Ksv,
        "intercept": intercept,
        "R2": r2,
        "n_points": len(concentrations),
    }


def estimate_quencher_concentration(F: float, F0: float, Ksv: float) -> float:
    """Estimate quencher concentration from measured fluorescence.
    [Q] = (F0/F - 1) / Ksv
    """
    if F <= 0 or Ksv == 0:
        return -1
    return (F0 / F - 1) / Ksv


def compute_kq(Ksv: float, tau0_ns: float) -> float:
    """Compute bimolecular quenching rate constant.
    kq = Ksv / τ0
    """
    tau0_s = tau0_ns * 1e-9
    return Ksv / tau0_s


def analyze_dynamic_vs_static(Ksv_temp1: float, Ksv_temp2: float,
                             temp1: float, temp2: float) -> dict:
    """
    Determine if quenching is dynamic or static.

    Dynamic quenching: Ksv increases with temperature (more diffusion)
    Static quenching: Ksv decreases with temperature (complex destabilizes)
    """
    if Ksv_temp2 > Ksv_temp1 and temp2 > temp1:
        mechanism = "dynamic"
    elif Ksv_temp2 < Ksv_temp1 and temp2 > temp1:
        mechanism = "static"
    else:
        mechanism = "mixed/unclear"

    return {
        "Ksv_T1": Ksv_temp1,
        "Ksv_T2": Ksv_temp2,
        "T1": temp1,
        "T2": temp2,
        "mechanism": mechanism,
        "note": f"Ksv {'increases' if Ksv_temp2 > Ksv_temp1 else 'decreases'} with temperature"
    }


def main():
    parser = argparse.ArgumentParser(description="Stern-Volmer quenching analysis")
    parser.add_argument("--input", help="CSV file: [Q] (M), F (intensity)")
    parser.add_argument("--F0", type=float, help="F0 (unquenched fluorescence)")
    parser.add_argument("--Ksv", type=float, help="Stern-Volmer constant (M⁻¹)")
    parser.add_argument("--Q", type=float, help="Quencher concentration (M)")
    parser.add_argument("--tau0", type=float, default=None,
                       help="Fluorescence lifetime without quencher (ns)")
    parser.add_argument("--temp1", type=float, default=None, help="Temperature 1 (°C)")
    parser.add_argument("--temp2", type=float, default=None, help="Temperature 2 (°C)")
    parser.add_argument("--Ksv2", type=float, default=None, help="Ksv at temperature 2")
    args = parser.parse_args()

    if args.input:
        # Load CSV data
        print(f"Loading quenching data from {args.input}")
        concentrations = []
        F_values = []

        import csv
        with open(args.input) as f:
            reader = csv.reader(f)
            for row in reader:
                if row[0].startswith("#") or not row[0]:
                    continue
                concentrations.append(float(row[0]))
                F_values.append(float(row[1]))

        print(f"\n{'[Q] (M)':>12} {'F':>10} {'F0/F':>10}")
        print("-" * 36)

        F0 = args.F0 if args.F0 else max(F_values)
        for q, fval in zip(concentrations, F_values):
            ratio = F0 / fval if fval > 0 else float("inf")
            print(f"{q:>12.6f} {fval:>10.1f} {ratio:>10.4f}")

        result = fit_stern_volmer(concentrations, F_values, F0)
        print(f"\nStern-Volmer Analysis Results:")
        print(f"  F0 = {result['F0']:.1f}")
        print(f"  Ksv = {result['Ksv']:.2f} M⁻¹")
        print(f"  intercept = {result['intercept']:.4f} (expected: 1.0)")
        print(f"  R² = {result['R2']:.6f}")
        print(f"  N points = {result['n_points']}")

        if args.tau0:
            kq = compute_kq(result["Ksv"], args.tau0)
            print(f"\n  τ₀ = {args.tau0} ns")
            print(f"  kq = Ksv / τ₀ = {kq:.2e} M⁻¹s⁻¹")

            # Diffusion limit check (~1e10 M⁻¹s⁻¹ in water)
            if kq > 1e10:
                print(f"  → kq exceeds diffusion limit (≈10¹⁰ M⁻¹s⁻¹), check for static component")
            else:
                print(f"  → kq within diffusion limit (dynamic quenching)")

    elif args.F0 and args.Ksv and args.Q:
        # Single-point: estimate concentration or compute F
        F = args.F0 / (1 + args.Ksv * args.Q)
        print(f"Stern-Volmer Prediction:")
        print(f"  F0 = {args.F0:.1f}")
        print(f"  Ksv = {args.Ksv:.2f} M⁻¹")
        print(f"  [Q] = {args.Q:.6f} M")
        print(f"  Predicted F = F0 / (1 + Ksv×[Q]) = {F:.1f}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()