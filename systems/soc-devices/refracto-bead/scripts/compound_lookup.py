#!/usr/bin/env python3
"""
compound_lookup.py — Offline refractive index compound lookup

Given a measured (n_D, V_D) pair, this script finds the closest matches
in a reference database of known compounds. Useful for identifying liquids
without a connected Refracto Bead device.

Usage:
    python3 compound_lookup.py --nd 1.4657 --vd 47.1
    python3 compound_lookup.py --nd 1.3330
    python3 compound_lookup.py --brix 42.3
    python3 compound_lookup.py --sg 1.025
"""

import argparse
import math
import sys

# Reference compound database (mirrors the on-device library)
COMPOUNDS = [
    ("Water",          1.3330, 55.8, "Reference"),
    ("Ethanol",        1.3611, 59.0, "Solvent"),
    ("Methanol",       1.3284, 57.6, "Solvent"),
    ("Acetone",        1.3588, 54.6, "Solvent"),
    ("Isopropanol",    1.3776, 54.6, "Solvent"),
    ("Toluene",        1.4961, 30.6, "Solvent"),
    ("Hexane",         1.3750, 56.8, "Solvent"),
    ("DCM",            1.4244, 40.1, "Solvent"),
    ("Ethyl acetate",  1.3723, 53.8, "Solvent"),
    ("Glycerol",       1.4735, 46.9, "Polyol"),
    ("Propylene gly",  1.4324, 47.9, "Polyol"),
    ("Ethylene gly",   1.4318, 49.6, "Coolant"),
    ("Olive oil",      1.4677, 47.2, "Oil"),
    ("Sunflower oil",  1.4657, 47.1, "Oil"),
    ("Castor oil",     1.4778, 45.4, "Oil"),
    ("Coconut oil",    1.4483, 48.3, "Oil"),
    ("Mineral oil",    1.4667, 46.0, "Oil"),
    ("Silicone 100c",  1.4035, 58.6, "Oil"),
    ("Honey 18%MC",    1.4900, 50.0, "Food"),
    ("Maple syrup",    1.4580, 49.0, "Food"),
    ("NaCl 10%",       1.3509, 55.5, "Solution"),
    ("NaCl 20%",       1.3686, 55.0, "Solution"),
    ("NaCl sat.",      1.3780, 54.0, "Solution"),
    ("Glucose 5%",     1.3402, 55.5, "Solution"),
    ("Glucose 20%",    1.3635, 55.0, "Solution"),
    ("Glucose 40%",    1.3900, 54.5, "Solution"),
    ("Sucrose 60%",    1.4490, 49.0, "Solution"),
    ("Sucrose 40%",    1.3997, 53.0, "Solution"),
    ("Cane juice",     1.3550, 55.0, "Beverage"),
    ("Apple juice",    1.3505, 55.2, "Beverage"),
    ("Orange juice",   1.3490, 55.3, "Beverage"),
    ("Red wine",       1.3448, 55.5, "Beverage"),
    ("Beer",           1.3380, 55.6, "Beverage"),
    ("Coffee",         1.3345, 55.7, "Beverage"),
    ("Milk whole",     1.3460, 55.4, "Dairy"),
    ("Skim milk",      1.3443, 55.5, "Dairy"),
    ("Cream 35%",      1.4080, 52.0, "Dairy"),
    ("Urine normal",   1.3355, 55.6, "Clinical"),
    ("Urine dehyd.",   1.3380, 55.5, "Clinical"),
    ("Serum",          1.3450, 55.2, "Clinical"),
    ("Saline 0.9%",    1.3345, 55.7, "Clinical"),
    ("DMSO",           1.4770, 47.0, "Solvent"),
    ("DMF",            1.4305, 49.2, "Solvent"),
    ("Acetonitrile",   1.3441, 56.0, "Solvent"),
    ("THF",            1.4070, 51.8, "Solvent"),
    ("Chloroform",     1.4459, 41.0, "Solvent"),
    ("CCl4",           1.4601, 36.4, "Solvent"),
    ("Benzene",        1.5011, 30.2, "Solvent"),
    ("Turpentine",     1.4690, 44.0, "Solvent"),
    ("Linseed oil",    1.4780, 45.0, "Oil"),
    ("Sesame oil",     1.4650, 47.3, "Oil"),
    ("Peanut oil",     1.4660, 47.1, "Oil"),
    ("Brake DOT4 new", 1.4460, 48.0, "Automotive"),
    ("Brake DOT4 wet", 1.4360, 49.0, "Automotive"),
    ("Battery full",   1.4030, 52.0, "Automotive"),
    ("Battery 50%",    1.3750, 54.0, "Automotive"),
    ("Coolant 50%EG",  1.3820, 53.0, "Automotive"),
    ("Coolant 50%PG",  1.3840, 52.5, "Automotive"),
    ("EO lavender",    1.4580, 49.5, "Pharma"),
    ("EO peppermint",  1.4600, 49.0, "Pharma"),
]


def find_matches(n_D: float, V_D: float = None, k: int = 5) -> list:
    """Find k nearest compounds by weighted Euclidean distance."""
    if V_D is None:
        # Match by n_D only
        scored = [(name, n, vd, cat, abs(n - n_D)) for name, n, vd, cat in COMPOUNDS]
        scored.sort(key=lambda x: x[4])
        return [(name, n, vd, cat, dist) for name, n, vd, cat, dist in scored[:k]]
    else:
        # Match by both n_D and V_D
        scored = []
        for name, n, vd, cat in COMPOUNDS:
            dist = math.sqrt(3.0 * (n - n_D)**2 + 0.01 * (vd - V_D)**2)
            scored.append((name, n, vd, cat, dist))
        scored.sort(key=lambda x: x[4])
        return scored[:k]


def brix_to_nD(brix: float) -> float:
    """Convert Brix to refractive index (ICUMSA inverse)."""
    dn = brix / (290 + 1200 * 0.05 + 3500 * 0.0025)  # Simplified inverse
    # Better: iterative solve
    for _ in range(10):
        dn = brix / (290 + 1200 * dn + 3500 * dn**2)
    return 1.3330 + dn


def nD_to_brix(n_D: float) -> float:
    """Convert refractive index to Brix (ICUMSA polynomial)."""
    dn = n_D - 1.3330
    return 290 * dn + 1200 * dn**2 + 3500 * dn**3


def nD_to_sg(n_D: float) -> float:
    """Convert n_D to specific gravity."""
    return 1.000 + (n_D - 1.3330) * 2.6


def main():
    parser = argparse.ArgumentParser(description="Refracto Bead Compound Lookup")
    parser.add_argument("--nd", type=float, help="Refractive index (n_D)")
    parser.add_argument("--vd", type=float, help="Abbe number (V_D)")
    parser.add_argument("--brix", type=float, help="Brix value (converts to n_D)")
    parser.add_argument("--sg", type=float, help="Specific gravity (converts to n_D)")
    parser.add_argument("--k", type=int, default=5, help="Number of matches to show")
    args = parser.parse_args()

    n_D = None
    V_D = None

    if args.brix is not None:
        n_D = brix_to_nD(args.brix)
        print(f"Brix {args.brix} → n_D = {n_D:.4f}")
    elif args.sg is not None:
        n_D = 1.3330 + (args.sg - 1.000) / 2.6
        print(f"SG {args.sg} → n_D = {n_D:.4f}")
    elif args.nd is not None:
        n_D = args.nd

    if n_D is None:
        print("Error: provide --nd, --brix, or --sg")
        sys.exit(1)

    V_D = args.vd

    # Show derived values
    print(f"\nDerived values:")
    print(f"  n_D = {n_D:.4f}")
    if V_D:
        print(f"  V_D = {V_D:.1f}")
        print(f"  Dispersion (n_F - n_C) = {(n_D - 1) / V_D:.4f}")
    print(f"  Brix = {nD_to_brix(n_D):.1f} °Bx")
    print(f"  Specific gravity = {nD_to_sg(n_D):.3f}")

    # Find matches
    matches = find_matches(n_D, V_D, k=args.k)

    print(f"\nTop {args.k} compound matches:")
    print(f"  {'#':>2}  {'Compound':<16} {'n_D':>8} {'V_D':>6} {'Category':<12} {'Distance'}")
    print(f"  {'─'*2}  {'─'*16} {'─'*8} {'─'*6} {'─'*12} {'─'*10}")

    for i, (name, n, vd, cat, dist) in enumerate(matches):
        confidence = max(0, 1 - dist / 0.5) * 100
        marker = " ← best" if i == 0 else ""
        print(f"  {i+1:>2}  {name:<16} {n:>8.4f} {vd:>6.1f} {cat:<12} {dist:.4f} ({confidence:.0f}%){marker}")


if __name__ == "__main__":
    main()