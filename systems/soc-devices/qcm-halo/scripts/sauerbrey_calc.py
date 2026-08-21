#!/usr/bin/env python3
"""
sauerbrey_calc.py — Sauerbrey mass/thickness calculator for QCM data

Standalone tool for quick mass and thickness calculations from
measured Δf values without needing the full QCM Halo device.

Usage:
    python3 sauerbrey_calc.py --df -15.3 --f0 5e6 --area 0.196
    python3 sauerbrey_calc.py --df -15.3 --f0 5e6 --rho_f 1.2
"""

import argparse
import math

RHO_Q = 2650.0      # kg/m³
MU_Q = 2.947e10     # Pa

def sauerbrey_mass(delta_f, f0, area_cm2):
    """Sauerbrey mass in ng/cm².
    Δm = -Δf * A * sqrt(ρq*μq) / (2*f0²)
    """
    sqrt_rq_muq = math.sqrt(RHO_Q * MU_Q)
    area_m2 = area_cm2 * 1e-4
    dm_kg = -delta_f * area_m2 * sqrt_rq_muq / (2 * f0**2)
    return dm_kg * 1e8  # kg/m² → ng/cm²

def sauerbrey_thickness(mass_ng_cm2, rho_f_g_cm3):
    """Thickness in nm from areal mass and film density."""
    return mass_ng_cm2 / (rho_f_g_cm3 * 100.0)

def kanazawa_delta_f(f0, rho_l, eta_l):
    """Kanazawa-Gordon Δf for a crystal in contact with a Newtonian liquid."""
    factor = math.sqrt(rho_l * eta_l / (math.pi * RHO_Q * MU_Q))
    return -(f0 ** 1.5) * factor

def main():
    parser = argparse.ArgumentParser(description='QCM Sauerbrey/Kanazawa calculator')
    parser.add_argument('--df', type=float, required=True, help='Frequency shift Δf (Hz)')
    parser.add_argument('--f0', type=float, default=5e6, help='Fundamental or overtone freq (Hz)')
    parser.add_argument('--area', type=float, default=0.196, help='Active area (cm²)')
    parser.add_argument('--rho_f', type=float, default=1.0, help='Film density (g/cm³)')
    parser.add_argument('--rho_l', type=float, help='Liquid density (kg/m³) for Kanazawa')
    parser.add_argument('--eta_l', type=float, help='Liquid viscosity (Pa·s) for Kanazawa')
    args = parser.parse_args()

    mass = sauerbrey_mass(args.df, args.f0, args.area)
    thickness = sauerbrey_thickness(mass, args.rho_f)

    print(f"── Sauerbrey Analysis ──")
    print(f"  Δf = {args.df:.3f} Hz at f = {args.f0/1e6:.1f} MHz")
    print(f"  Active area = {args.area:.3f} cm²")
    print(f"  Areal mass = {mass:.2f} ng/cm²")
    print(f"  Film density = {args.rho_f:.2f} g/cm³")
    print(f"  Thickness = {thickness:.3f} nm")
    print(f"  Sensitivity = {abs(args.df/mass):.2f} Hz/(ng/cm²)")

    if args.rho_l and args.eta_l:
        df_kan = kanazawa_delta_f(args.f0, args.rho_l, args.eta_l)
        print(f"\n── Kanazawa-Gordon (liquid) ──")
        print(f"  ρ_l = {args.rho_l:.1f} kg/m³, η_l = {args.eta_l:.4f} Pa·s")
        print(f"  Predicted Δf = {df_kan:.2f} Hz")

if __name__ == "__main__":
    main()