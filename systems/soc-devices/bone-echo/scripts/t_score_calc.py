#!/usr/bin/env python3
"""
t_score_calc.py — Bone Echo T-score / Z-score calculator

A standalone Python utility that computes the Stiffness Index,
T-score, and Z-score from measured SOS and BUA, using the same
normative database as the firmware.

Usage:
    python3 t_score_calc.py --sos 1562 --bua 58.4 --age 55 --sex F --eth caucasian
    python3 t_score_calc.py --sos 1500 --bua 40 --age 70 --sex F --eth asian --fracture

This is useful for:
  - Verifying the firmware's on-device computation
  - Re-computing scores from logged CSV data
  - Exploring what-if scenarios (how SOS/BUA map to T-score)
"""

import argparse
import sys

# Normative database: [ethnicity][sex][age_group] = (mean_si, sd_si)
NORM_DB = {
    "caucasian": {
        "M": [(95, 14), (93, 14), (91, 15), (88, 15), (84, 16), (80, 16), (75, 17)],
        "F": [(89, 12), (87, 12), (84, 13), (78, 14), (70, 15), (62, 16), (55, 17)],
    },
    "asian": {
        "M": [(93, 13), (91, 13), (89, 14), (86, 14), (82, 15), (78, 15), (73, 16)],
        "F": [(87, 11), (85, 11), (82, 12), (76, 13), (68, 14), (60, 15), (53, 16)],
    },
    "african": {
        "M": [(99, 13), (97, 13), (95, 14), (92, 14), (88, 15), (84, 15), (79, 16)],
        "F": [(93, 11), (91, 11), (88, 12), (82, 13), (74, 14), (66, 15), (59, 16)],
    },
    "hispanic": {
        "M": [(94, 14), (92, 14), (90, 15), (87, 15), (83, 16), (79, 16), (74, 17)],
        "F": [(88, 12), (86, 12), (83, 13), (77, 14), (69, 15), (61, 16), (54, 17)],
    },
}

AGE_GROUPS = [(20, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 200)]


def age_group_index(age: int) -> int:
    for i, (lo, hi) in enumerate(AGE_GROUPS):
        if lo <= age < hi:
            return i
    return 6  # 80+


def stiffness_index(bua: float, sos: float) -> float:
    """SI = 0.67 * BUA + 0.28 * SOS - 420 (Langton 1996)"""
    return 0.67 * bua + 0.28 * sos - 420.0


def t_score(si: float, sex: str, ethnicity: str) -> float:
    """T-score compares to young-adult (20-29) reference."""
    ref = NORM_DB[ethnicity][sex][0]
    return (si - ref[0]) / ref[1]


def z_score(si: float, age: int, sex: str, ethnicity: str) -> float:
    """Z-score compares to age-matched peers."""
    ag = age_group_index(age)
    ref = NORM_DB[ethnicity][sex][ag]
    return (si - ref[0]) / ref[1]


def classify(t: float, fracture: bool = False) -> str:
    if t >= -1.0:
        return "Normal (T ≥ -1.0)"
    elif t > -2.5:
        return "Osteopenia (-2.5 < T < -1.0)"
    elif fracture:
        return "Severe Osteoporosis (T ≤ -2.5 with fracture)"
    else:
        return "Osteoporosis (T ≤ -2.5)"


def recommend(t: float, fracture: bool = False) -> str:
    if t >= -1.0:
        return "Normal — repeat screening in 2 years"
    elif t > -2.5:
        return "Osteopenia — DEXA confirmation recommended"
    elif fracture:
        return "Severe osteoporosis — urgent physician consult"
    else:
        return "Osteoporosis — physician consult; DEXA confirmation"


def main():
    parser = argparse.ArgumentParser(description="Bone Echo T-score calculator")
    parser.add_argument("--sos", type=float, required=True, help="Speed of sound (m/s)")
    parser.add_argument("--bua", type=float, required=True, help="BUA (dB/MHz)")
    parser.add_argument("--age", type=int, required=True, help="Patient age (years)")
    parser.add_argument("--sex", choices=["M", "F"], required=True, help="Sex (M/F)")
    parser.add_argument("--eth", choices=["caucasian", "asian", "african", "hispanic"],
                        required=True, help="Ethnicity")
    parser.add_argument("--fracture", action="store_true", help="Prior fragility fracture")
    args = parser.parse_args()

    si = stiffness_index(args.bua, args.sos)
    t = t_score(si, args.sex, args.eth)
    z = z_score(si, args.age, args.sex, args.eth)
    cls = classify(t, args.fracture)
    rec = recommend(t, args.fracture)

    print("=== Bone Echo QUS Report ===")
    print(f"  SOS:        {args.sos:.1f} m/s")
    print(f"  BUA:        {args.bua:.1f} dB/MHz")
    print(f"  SI:         {si:.1f}")
    print(f"  T-score:    {t:.2f}")
    print(f"  Z-score:    {z:.2f}")
    print(f"  Class:      {cls}")
    print(f"  Recommend:  {rec}")

    # Age-matched reference
    ag = age_group_index(args.age)
    ref_age = NORM_DB[args.eth][args.sex][ag]
    ref_young = NORM_DB[args.eth][args.sex][0]
    print(f"\n  Reference (young-adult {args.eth} {args.sex}): mean={ref_young[0]}, sd={ref_young[1]}")
    print(f"  Reference (age {AGE_GROUPS[ag][0]}-{AGE_GROUPS[ag][1]} {args.eth} {args.sex}): "
          f"mean={ref_age[0]}, sd={ref_age[1]}")

    if args.eth not in ["caucasian"]:
        print(f"\n  Note: {args.eth} reference values are less validated than Caucasian.")


if __name__ == "__main__":
    main()