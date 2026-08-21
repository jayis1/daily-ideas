#!/usr/bin/env python3
"""
calibrate.py — Refracto Bead 2-point calibration helper

This script guides the user through the 2-point calibration procedure
and computes the calibration coefficients (a, b, c) for each wavelength.

Usage:
    python3 calibrate.py --mac AA:BB:CC:DD:EE:FF
    python3 calibrate.py --offline  # Manual entry mode (no device needed)
"""

import argparse
import asyncio
import json
import struct
import sys
import math

try:
    from bleak import BleakClient
except ImportError:
    BLEAK_AVAILABLE = False
else:
    BLEAK_AVAILABLE = True

# Known reference liquids
REFERENCES = {
    "water": {"n_D": 1.3330, "name": "Distilled Water (n_D=1.3330)"},
    "oil_1.515": {"n_D": 1.5150, "name": "Cargille RI Standard Oil (n_D=1.5150)"},
    "oil_1.700": {"n_D": 1.7000, "name": "Cargille RI Standard Oil (n_D=1.7000)"},
}


def compute_coefficients_2pt(p1, n1, p2, n2):
    """Compute linear calibration coefficients from 2 points.

    n = a + b * p
    """
    b = (n2 - n1) / (p2 - p1)
    a = n1 - b * p1
    return {"a": a, "b": b, "c": 0.0}


def compute_coefficients_3pt(p1, n1, p2, n2, p3, n3):
    """Compute quadratic calibration coefficients from 3 points.

    n = a + b * p + c * p²
    """
    # Solve 3x3 system: [1 p1 p1²] [a]   [n1]
    #                   [1 p2 p2²] [b] = [n2]
    #                   [1 p3 p3²] [c]   [n3]
    denom = (p1 - p2) * (p1 - p3) * (p2 - p3)
    if abs(denom) < 1e-12:
        raise ValueError("Points are not distinct enough")

    a = (p2 * p3 * (p2 - p3) * n1 + p3 * p1 * (p3 - p1) * n2 + p1 * p2 * (p1 - p2) * n3) / denom
    b = (p2**2 - p3**2) * n1 / denom * -1 + (p3**2 - p1**2) * n2 / denom + (p1**2 - p2**2) * n3 / denom * -1

    # Use simpler Lagrange interpolation
    a = ((p2*p3*(p2-p3))*n1 + (p3*p1*(p3-p1))*n2 + (p1*p2*(p1-p2))*n3) / denom
    b = (-(p2**2-p3**2)*n1 + (p3**2-p1**2)*n2 - (p1**2-p2**2)*n3) / denom
    c = ((p2-p3)*n1 + (p3-p1)*n2 + (p1-p2)*n3) / denom

    return {"a": a, "b": b, "c": c}


def offline_calibration():
    """Manual calibration without a connected device."""
    print("\n" + "=" * 60)
    print("  Refracto Bead — Offline Calibration Calculator")
    print("=" * 60)

    print("\nThis tool computes calibration coefficients from known")
    print("edge pixel positions and reference RI values.")
    print()

    # 2-point or 3-point?
    print("Calibration modes:")
    print("  1. 2-point (linear) — water + 1 standard")
    print("  2. 3-point (quadratic) — water + 2 standards")
    choice = input("\nSelect mode [1/2]: ").strip()

    if choice == "1":
        print("\n--- 2-Point Linear Calibration ---")
        print("\nReference 1: Distilled Water (n_D = 1.3330)")
        p1 = float(input("  Edge pixel position for water: "))

        print("\nReference 2: RI Standard Oil")
        print("  Options:")
        for key, ref in REFERENCES.items():
            if key != "water":
                print(f"    {key}: {ref['name']}")
        ref2_key = input("  Select reference [oil_1.515/oil_1.700]: ").strip()
        ref2 = REFERENCES.get(ref2_key, REFERENCES["oil_1.515"])
        p2 = float(input(f"  Edge pixel position for {ref2_key}: "))

        coeffs = compute_coefficients_2pt(p1, 1.3330, p2, ref2["n_D"])

        print(f"\n--- Calibration Coefficients ---")
        print(f"  a = {coeffs['a']:.6f}")
        print(f"  b = {coeffs['b']:.8f}")
        print(f"  c = {coeffs['c']:.6f}")

        # Verify
        n_check1 = coeffs["a"] + coeffs["b"] * p1
        n_check2 = coeffs["a"] + coeffs["b"] * p2
        print(f"\n  Verification:")
        print(f"    Water:   p={p1} → n={n_check1:.4f} (expected 1.3330)")
        print(f"    Oil:     p={p2} → n={n_check2:.4f} (expected {ref2['n_D']:.4f})")

    elif choice == "2":
        print("\n--- 3-Point Quadratic Calibration ---")
        p1 = float(input("  Water (n_D=1.3330) edge pixel: "))
        p2 = float(input("  Oil 1.515 (n_D=1.5150) edge pixel: "))
        p3 = float(input("  Oil 1.700 (n_D=1.7000) edge pixel: "))

        coeffs = compute_coefficients_3pt(p1, 1.3330, p2, 1.5150, p3, 1.7000)

        print(f"\n--- Calibration Coefficients ---")
        print(f"  a = {coeffs['a']:.6f}")
        print(f"  b = {coeffs['b']:.8f}")
        print(f"  c = {coeffs['c']:.12f}")

    # Save
    save = input("\nSave to calibration.json? [y/n]: ").strip().lower()
    if save == "y":
        with open("calibration.json", "w") as f:
            json.dump({
                "mode": "2-point" if choice == "1" else "3-point",
                "coefficients": coeffs,
                "references": [p1, p2] if choice == "1" else [p1, p2, p3],
            }, f, indent=2)
        print("Saved to calibration.json")


async def ble_calibration(mac):
    """Calibration with a connected device via BLE."""
    if not BLEAK_AVAILABLE:
        print("Install bleak: pip install bleak")
        return

    CHAR_COMMAND = "0000ffc1-0000-1000-8000-00805f9b34fb"
    CHAR_RI = "0000ffc2-0000-1000-8000-00805f9b34fb"
    CHAR_WAVEFORM = "0000ffc5-0000-1000-8000-00805f9b34fb"

    print(f"\nConnecting to {mac}...")
    async with BleakClient(mac) as client:
        print("Connected!")

        print("\n--- Calibration Procedure ---")
        print("You will need:")
        print("  1. Distilled water (n_D = 1.3330)")
        print("  2. RI standard oil (n_D = 1.5150)")
        print()

        input("Press Enter when water is on the prism...")
        print("Triggering water measurement...")
        await client.write_gatt_char(CHAR_COMMAND, b'\x02', response=True)  # Cal water
        await asyncio.sleep(4)

        ri_data = await client.read_gatt_char(CHAR_RI)
        n_D_water = struct.unpack_from("<f", ri_data, 0)[0]
        print(f"  Water n_D = {n_D_water:.4f}")

        # Read raw waveform for edge position
        wf_data = await client.read_gatt_char(CHAR_WAVEFORM)
        print(f"  Captured {len(wf_data)}-pixel waveform")

        input("\nClean prism, apply RI standard oil, press Enter...")
        print("Triggering oil measurement...")
        await client.write_gatt_char(CHAR_COMMAND, b'\x03', response=True)  # Cal oil
        await asyncio.sleep(4)

        ri_data = await client.read_gatt_char(CHAR_RI)
        n_D_oil = struct.unpack_from("<f", ri_data, 0)[0]
        print(f"  Oil n_D = {n_D_oil:.4f}")

        print("\n✓ Calibration complete! Coefficients stored in device flash.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refracto Bead Calibration Helper")
    parser.add_argument("--mac", help="Device MAC address for BLE calibration")
    parser.add_argument("--offline", action="store_true",
                        help="Offline coefficient calculator (no device needed)")
    args = parser.parse_args()

    if args.offline or not args.mac:
        offline_calibration()
    else:
        asyncio.run(ble_calibration(args.mac))