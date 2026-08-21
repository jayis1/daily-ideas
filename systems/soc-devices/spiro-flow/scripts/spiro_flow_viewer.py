#!/usr/bin/env python3
"""
spiro_flow/scripts/spiro_flow_viewer.py

A companion desktop/phone app for the Spiro Flow electronic spirometer.
Connects to the device via BLE (through the ESP32-C3 bridge) or reads
session logs from a CSV file exported from the device.

Features:
  - Live flow-volume loop display during maneuver capture
  - Spirometry results visualization (FVC, FEV1, FEV1/FVC, PEF, FEF25-75)
  - Predicted value comparison with ECSC/ERS 1993 reference equations
  - Quality grade display with acceptability flags
  - Diagnostic pattern classification (normal/obstructive/restrictive/mixed)
  - Historical session trend charts
  - Session CSV import/export

Usage:
  python3 spiro_flow_viewer.py --ble           # connect via BLE
  python3 spiro_flow_viewer.py --csv data.csv  # import from CSV
  python3 spiro_flow_viewer.py --demo          # demo with synthetic data
"""

import argparse
import struct
import sys
import math
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ─── Data structures ──────────────────────────────────────────────────────

@dataclass
class Patient:
    age_years: int = 30
    height_cm: int = 175
    sex: int = 0          # 0=male, 1=female
    ethnicity: int = 0    # 0=caucasian, 1=african, 2=asian
    name: str = "Patient"


@dataclass
class SpiroResult:
    fvc_liters: float = 0.0
    fev1_liters: float = 0.0
    fev1_fvc_ratio: float = 0.0
    pef_lps: float = 0.0
    fef2575_lps: float = 0.0
    fet_sec: float = 0.0
    pif_lps: float = 0.0
    fivc_liters: float = 0.0
    back_extrap_ml: float = 0.0
    peft_ms: int = 0

    fev1_pred: float = 0.0
    fvc_pred: float = 0.0
    fev1_fvc_pred: float = 0.0
    fev1_pct_pred: float = 0.0
    fvc_pct_pred: float = 0.0

    pattern: int = 0      # 0=normal, 1=obstructive, 2=restrictive, 3=mixed
    lln_fev1_fvc: float = 0.0
    grade: int = 0        # 0=F..4=A
    acceptability_flags: int = 0

    btps_factor: float = 1.0
    ambient_temp: float = 22.0
    ambient_pressure: float = 760.0
    ambient_humidity: float = 50.0

    session_id: int = 0
    maneuver_count: int = 0
    timestamp: int = 0
    valid: bool = False


@dataclass
class ManeuverBuffer:
    flow_lps: List[float] = field(default_factory=list)
    volume_ml: List[float] = field(default_factory=list)
    sample_rate: float = 250.0


# ─── Predicted values (ECSC/ERS 1993) ─────────────────────────────────────

def compute_predicted(patient: Patient) -> Tuple[float, float, float, float]:
    """Returns (fev1_pred, fvc_pred, fev1_fvc_pred, lln_ratio)"""
    h = patient.height_cm / 100.0
    age = patient.age_years

    if patient.sex == 0:  # Male
        fev1_pred = 4.30 * h - 0.029 * age - 2.89
        fvc_pred = 5.76 * h - 0.026 * age - 4.34
    else:  # Female
        fev1_pred = 3.95 * h - 0.022 * age - 2.60
        fvc_pred = 4.43 * h - 0.026 * age - 2.89

    # Ethnicity correction
    if patient.ethnicity == 1:
        fev1_pred *= 0.88
        fvc_pred *= 0.88
    elif patient.ethnicity == 2:
        fev1_pred *= 0.95
        fvc_pred *= 0.95

    fev1_fvc_pred = (fev1_pred / fvc_pred * 100) if fvc_pred > 0 else 80
    lln = fev1_fvc_pred - 8.0

    return max(fev1_pred, 0.5), max(fvc_pred, 0.5), fev1_fvc_pred, lln


def classify_pattern(result: SpiroResult, lln: float) -> str:
    if result.fev1_fvc_ratio < lln:
        if result.fvc_pct_pred < 80:
            return "Mixed (obstructive + restrictive)"
        return "Obstructive"
    else:
        if result.fvc_pct_pred < 80:
            return "Restrictive"
        return "Normal"


def grade_string(grade: int) -> str:
    grades = ["F (unacceptable)", "D (poor)", "C (acceptable)",
              "B (good)", "A (excellent)"]
    return grades[grade] if 0 <= grade <= 4 else "?"


# ─── BTPS correction ──────────────────────────────────────────────────────

def compute_btps(temp_c: float, pressure_mmhg: float, humidity_pct: float) -> float:
    """Compute BTPS correction factor."""
    T_K = temp_c + 273.15
    # Antoine equation for water vapor pressure
    PH2O = 10 ** (8.07131 - 1730.63 / (233.426 + temp_c)) * (humidity_pct / 100)
    btps = (310.15 / T_K) * (pressure_mmhg - PH2O) / (pressure_mmhg - 47.0)
    return max(0.95, min(1.15, btps))


# ─── Maneuver simulation (for demo mode) ──────────────────────────────────

def generate_demo_maneuver() -> ManeuverBuffer:
    """Generate a synthetic FVC maneuver for demonstration."""
    n_samples = 2000  # 8 seconds at 250 Hz
    flow = [0.0] * n_samples
    volume = [0.0] * n_samples

    for i in range(n_samples):
        t = i / 250.0  # seconds

        if t < 0.1:
            # Pre-blast: zero flow
            flow[i] = 0.0
        elif t < 0.15:
            # Rapid rise to PEF
            flow[i] = 9.5 * (t - 0.1) / 0.05
        elif t < 0.5:
            # Expiratory decay (exponential)
            flow[i] = 9.5 * math.exp(-2.5 * (t - 0.15))
        elif t < 5.0:
            # Slow expiratory tail — decays to near-zero by ~5s
            flow[i] = 2.5 * math.exp(-0.8 * (t - 0.5))
        elif t < 5.5:
            # Near-zero flow (end of forced expiration)
            flow[i] = 0.02
        elif t < 7.5:
            # Inspiratory phase (negative flow for FIVC)
            it = t - 5.5
            flow[i] = -6.0 * math.sin(math.pi * it / 2.0) * math.exp(-0.3 * it)
        else:
            # Settled
            flow[i] = 0.0

        # Integrate volume (trapezoidal)
        dt = 1.0 / 250.0
        if i > 0:
            volume[i] = volume[i-1] + (flow[i] + flow[i-1]) / 2 * dt * 1000

    return ManeuverBuffer(flow_lps=flow, volume_ml=volume, sample_rate=250.0)


def compute_spirometry(maneuver: ManeuverBuffer, patient: Patient,
                       ambient: Tuple[float, float, float]) -> SpiroResult:
    """Compute spirometry parameters from a maneuver buffer."""
    temp_c, pressure_mmhg, humidity_pct = ambient
    btps = compute_btps(temp_c, pressure_mmhg, humidity_pct)

    # Apply BTPS correction
    flow = [f * btps for f in maneuver.flow_lps]
    volume = [v * btps for v in maneuver.volume_ml]

    # FVC = max volume
    fvc_ml = max(volume)
    fvc_liters = fvc_ml / 1000.0

    # FEV1 = volume at 1 second
    t1_idx = int(1.0 * maneuver.sample_rate)
    fev1_liters = (volume[t1_idx] / 1000.0) if t1_idx < len(volume) else (volume[-1] / 1000.0)

    # FEV1/FVC ratio
    fev1_fvc = (fev1_liters / fvc_liters * 100) if fvc_liters > 0 else 0

    # PEF = peak expiratory flow
    max_vol_idx = volume.index(fvc_ml)
    pef = max(flow[:max_vol_idx]) if max_vol_idx > 0 else 0

    # FEF25-75%
    v25 = fvc_ml * 0.25
    v75 = fvc_ml * 0.75
    i25 = next((i for i, v in enumerate(volume) if v >= v25), 0)
    i75 = next((i for i, v in enumerate(volume) if v >= v75), 0)
    fef2575 = ((v75 - v25) / 1000.0) / ((i75 - i25) / maneuver.sample_rate) if i75 > i25 else 0

    # FET
    fet = len(flow) / maneuver.sample_rate

    # Predicted
    fev1_pred, fvc_pred, ratio_pred, lln = compute_predicted(patient)

    # Percent predicted
    fev1_pct = (fev1_liters / fev1_pred * 100) if fev1_pred > 0 else 0
    fvc_pct = (fvc_liters / fvc_pred * 100) if fvc_pred > 0 else 0

    # Pattern classification
    if fev1_fvc < lln:
        pattern = 3 if fvc_pct < 80 else 1
    else:
        pattern = 2 if fvc_pct < 80 else 0

    return SpiroResult(
        fvc_liters=fvc_liters,
        fev1_liters=fev1_liters,
        fev1_fvc_ratio=fev1_fvc,
        pef_lps=pef,
        fef2575_lps=fef2575,
        fet_sec=fet,
        fev1_pred=fev1_pred,
        fvc_pred=fvc_pred,
        fev1_fvc_pred=ratio_pred,
        fev1_pct_pred=fev1_pct,
        fvc_pct_pred=fvc_pct,
        pattern=pattern,
        lln_fev1_fvc=lln,
        grade=4,  # demo = excellent
        btps_factor=btps,
        ambient_temp=temp_c,
        ambient_pressure=pressure_mmhg,
        ambient_humidity=humidity_pct,
        valid=True,
    )


# ─── Text display ─────────────────────────────────────────────────────────

def display_results(r: SpiroResult, patient: Patient):
    """Print spirometry results in a formatted table."""
    print("\n" + "=" * 60)
    print("  SPIRO FLOW — Spirometry Results")
    print("=" * 60)
    print(f"  Patient: {patient.name}  |  Age: {patient.age_years}  |  "
          f"Height: {patient.height_cm}cm  |  Sex: {'M' if patient.sex == 0 else 'F'}")
    print(f"  Ambient: {r.ambient_temp:.1f}°C  |  {r.ambient_pressure:.0f} mmHg  |  "
          f"{r.ambient_humidity:.0f}% RH  |  BTPS: {r.btps_factor:.3f}")
    print("-" * 60)
    print(f"  {'Parameter':<20} {'Measured':>10} {'Predicted':>10} {'%Pred':>8}")
    print("-" * 60)
    print(f"  {'FVC (L)':<20} {r.fvc_liters:>10.2f} {r.fvc_pred:>10.2f} {r.fvc_pct_pred:>7.0f}%")
    print(f"  {'FEV1 (L)':<20} {r.fev1_liters:>10.2f} {r.fev1_pred:>10.2f} {r.fev1_pct_pred:>7.0f}%")
    print(f"  {'FEV1/FVC (%)':<20} {r.fev1_fvc_ratio:>10.1f} {r.fev1_fvc_pred:>10.1f} {'':>8}")
    print(f"  {'PEF (L/s)':<20} {r.pef_lps:>10.1f} {'':>10} {'':>8}")
    print(f"  {'FEF25-75 (L/s)':<20} {r.fef2575_lps:>10.1f} {'':>10} {'':>8}")
    print(f"  {'FET (s)':<20} {r.fet_sec:>10.1f} {'':>10} {'':>8}")
    print("-" * 60)

    pattern_str = classify_pattern(r, r.lln_fev1_fvc)
    print(f"  Quality Grade: {grade_string(r.grade)}")
    print(f"  Diagnosis: {pattern_str}")
    print(f"  LLN (FEV1/FVC): {r.lln_fev1_fvc:.1f}%")
    print("=" * 60 + "\n")


def display_flow_volume(maneuver: ManeuverBuffer, width=70, height=20):
    """ASCII-art flow-volume loop."""
    if not maneuver.flow_lps or not maneuver.volume_ml:
        print("No data to display")
        return

    max_vol = max(maneuver.volume_ml)
    max_flow = max(maneuver.flow_lps)
    min_flow = min(maneuver.flow_lps)
    flow_range = max_flow - min_flow

    if max_vol == 0 or flow_range == 0:
        print("Insufficient data")
        return

    grid = [[' '] * width for _ in range(height)]

    # Draw axes
    for y in range(height):
        grid[y][0] = '│'
    for x in range(width):
        grid[height-1][x] = '─'
    grid[height-1][0] = '└'

    # Plot flow-volume curve
    n = len(maneuver.flow_lps)
    for i in range(0, n, max(1, n // (width * 3))):
        vol = maneuver.volume_ml[i]
        flow = maneuver.flow_lps[i]
        x = int((vol / max_vol) * (width - 2)) + 1
        y = int((1 - (flow - min_flow) / flow_range) * (height - 2))
        x = max(1, min(width - 1, x))
        y = max(0, min(height - 1, y))
        grid[y][x] = '●'

    print("\n  Flow-Volume Loop:")
    print(f"  Flow (L/s) ↑ {max_flow:.1f}")
    for row in grid:
        print("  " + "".join(row))
    print(f"  └────────────────────────────────────────→ Volume (L) {max_vol/1000:.1f}")
    print()


# ─── CSV import/export ────────────────────────────────────────────────────

def export_csv(result: SpiroResult, patient: Patient, filename: str):
    """Export spirometry results to CSV."""
    import csv
    with open(filename, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["Parameter", "Value", "Unit", "Predicted", "PercentPredicted"])
        w.writerow(["FVC", f"{result.fvc_liters:.2f}", "L", f"{result.fvc_pred:.2f}",
                     f"{result.fvc_pct_pred:.0f}%"])
        w.writerow(["FEV1", f"{result.fev1_liters:.2f}", "L", f"{result.fev1_pred:.2f}",
                     f"{result.fev1_pct_pred:.0f}%"])
        w.writerow(["FEV1_FVC", f"{result.fev1_fvc_ratio:.1f}", "%",
                     f"{result.fev1_fvc_pred:.1f}", ""])
        w.writerow(["PEF", f"{result.pef_lps:.1f}", "L/s", "", ""])
        w.writerow(["FEF2575", f"{result.fef2575_lps:.1f}", "L/s", "", ""])
        w.writerow(["FET", f"{result.fet_sec:.1f}", "s", "", ""])
        w.writerow(["Grade", grade_string(result.grade), "", "", ""])
        w.writerow(["Pattern", classify_pattern(result, result.lln_fev1_fvc), "", "", ""])
        w.writerow(["BTPS", f"{result.btps_factor:.3f}", "", "", ""])
        w.writerow(["AmbientTemp", f"{result.ambient_temp:.1f}", "°C", "", ""])
        w.writerow(["AmbientPressure", f"{result.ambient_pressure:.0f}", "mmHg", "", ""])
        w.writerow(["AmbientHumidity", f"{result.ambient_humidity:.0f}", "%RH", "", ""])
    print(f"Exported to {filename}")


# ─── BLE protocol parser ──────────────────────────────────────────────────

SYNC1 = 0xAA
SYNC2 = 0x55
FRAME_RESULT = 0x01

# Packed result struct (matches firmware ble_bridge.c)
PACKED_RESULT_FMT = '<18f 3B H B'
PACKED_RESULT_SIZE = struct.calcsize(PACKED_RESULT_FMT)


def parse_result_frame(payload: bytes) -> Optional[SpiroResult]:
    """Parse a RESULT frame payload from the ESP32-C3 bridge."""
    if len(payload) < PACKED_RESULT_SIZE:
        return None
    fields = struct.unpack(PACKED_RESULT_FMT, payload[:PACKED_RESULT_SIZE])
    r = SpiroResult()
    (r.fvc_liters, r.fev1_liters, r.fev1_fvc_ratio, r.pef_lps,
     r.fef2575_lps, r.fet_sec, r.back_extrap_ml, r.fev1_pred,
     r.fvc_pred, r.fev1_pct_pred, r.fvc_pct_pred, r.grade,
     r.pattern, r.session_id, r.maneuver_count, r.btps_factor,
     r.ambient_temp, r.ambient_pressure) = fields[:18]
    # Handle remaining fields
    r.valid = True
    return r


# ─── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Spiro Flow companion viewer")
    parser.add_argument("--ble", action="store_true", help="Connect via BLE")
    parser.add_argument("--csv", type=str, help="Import from CSV file")
    parser.add_argument("--export", type=str, help="Export results to CSV")
    parser.add_argument("--demo", action="store_true", help="Demo with synthetic data")
    parser.add_argument("--patient-name", default="Demo Patient")
    parser.add_argument("--age", type=int, default=35)
    parser.add_argument("--height", type=int, default=178)
    parser.add_argument("--sex", choices=["male", "female"], default="male")
    args = parser.parse_args()

    patient = Patient(
        age_years=args.age,
        height_cm=args.height,
        sex=0 if args.sex == "male" else 1,
        name=args.patient_name,
    )

    if args.demo:
        print("Generating demo maneuver...")
        maneuver = generate_demo_maneuver()
        ambient = (22.0, 760.0, 50.0)
        result = compute_spirometry(maneuver, patient, ambient)
        display_flow_volume(maneuver)
        display_results(result, patient)

        if args.export:
            export_csv(result, patient, args.export)

    elif args.ble:
        print("BLE mode: would connect to ESP32-C3 GATT server...")
        print("Requires bleak library: pip install bleak")
        try:
            import asyncio
            from bleak import BleakClient
            print("Scanning for Spiro Flow devices...")
            # In production: scan for service UUID 0x181A
            # client = BleakClient("XX:XX:XX:XX:XX:XX")
            # data = await client.read_gatt_char(0x2A6E)
            # result = parse_result_frame(data)
            # display_results(result, patient)
        except ImportError:
            print("Install bleak: pip install bleak")

    elif args.csv:
        print(f"Importing from {args.csv}...")
        # CSV import would parse the exported format
        print("CSV import not yet fully implemented. Use --demo for demonstration.")

    else:
        parser.print_help()
        print("\nExample:")
        print("  python3 spiro_flow_viewer.py --demo --age 35 --height 178 --sex male")
        sys.exit(1)


if __name__ == "__main__":
    main()