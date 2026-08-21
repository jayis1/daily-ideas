#!/usr/bin/env python3
"""
wind_calc.py — compute winding geometry for a toroidal specimen.

Given a toroid's outer diameter, inner diameter, and height (in mm),
computes:
  - magnetic path length  l_e   (m)
  - cross-sectional area  A_core (m^2)
  - suggested primary/secondary turn counts for a target peak H field
    at a given peak current

Usage:
  python3 wind_calc.py --od 25.5 --id 14.0 --h 10.0 \
                       --ipeak 1.0 --hpeak 5000

This prints the geometry and a suggested N1/N2, which you then enter
into the Ferro Weave captive Wi-Fi portal or pass to bh_plotter.py.
"""
import argparse
import math


def toroid_geometry(od_mm: float, id_mm: float, h_mm: float):
    """Return (l_e_m, a_core_m2) for a toroid."""
    od = od_mm / 1000.0
    id_ = id_mm / 1000.0
    h = h_mm / 1000.0
    # magnetic path length (mean diameter)
    r_mean = (od / 2.0 + id_ / 2.0) / 2.0
    l_e = 2.0 * math.pi * r_mean
    # cross-sectional area (rectangular section)
    a_core = (od - id_) / 2.0 * h
    return l_e, a_core


def suggest_turns(l_e: float, i_peak: float, h_peak: float,
                  max_turns: int = 500):
    """Suggest N1 for H_peak = N1 * I_peak / l_e, capped at max_turns."""
    n1 = int(h_peak * l_e / i_peak)
    n1 = max(10, min(n1, max_turns))
    # N2: enough signal — rule of thumb N2 ≈ N1 (1:1) for a fair voltage
    n2 = n1
    return n1, n2


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--od",  type=float, required=True, help="outer diameter (mm)")
    ap.add_argument("--id",  type=float, required=True, help="inner diameter (mm)")
    ap.add_argument("--h",   type=float, required=True, help="height (mm)")
    ap.add_argument("--ipeak",  type=float, default=1.0, help="peak current (A)")
    ap.add_argument("--hpeak",  type=float, default=5000.0,
                    help="target peak H field (A/m)")
    ap.add_argument("--rho", type=float, default=4800.0,
                    help="material density (kg/m^3)")
    args = ap.parse_args()

    l_e, a_core = toroid_geometry(args.od, args.id, args.h)
    n1, n2 = suggest_turns(l_e, args.ipeak, args.hpeak)

    # A2 (secondary winding area) is slightly larger than A_core to
    # account for the winding clearance; assume 1 mm radial clearance.
    clearance = 0.001
    a2 = a_core + 2 * clearance * (args.h / 1000.0)

    print("Toroid geometry")
    print("─────────────────────────────────────")
    print(f"  OD = {args.od} mm,  ID = {args.id} mm,  H = {args.h} mm")
    print(f"  l_e     = {l_e*1000:.2f} mm   = {l_e:.4e} m")
    print(f"  A_core  = {a_core*1e6:.2f} mm²  = {a_core:.4e} m²")
    print(f"  A2      = {a2*1e6:.2f} mm²  = {a2:.4e} m²  (with 1 mm clearance)")
    print()
    print(f"Suggested turns for H_peak = {args.hpeak:.0f} A/m at I_peak = {args.ipeak} A:")
    print(f"  N1 = {n1}   (primary,  magnetizing)")
    print(f"  N2 = {n2}   (secondary, sense)")
    print()
    print("Enter these into Ferro Weave:")
    print(f"  GEOM {n1} {n2} {l_e:.4e} {a2:.4e} {a_core:.4e} {args.rho}")
    print()
    # Sanity: what H do we actually get at ipeak?
    h_actual = n1 * args.ipeak / l_e
    print(f"Actual H_peak with N1={n1}, I_peak={args.ipeak} A: {h_actual:.1f} A/m")


if __name__ == "__main__":
    main()