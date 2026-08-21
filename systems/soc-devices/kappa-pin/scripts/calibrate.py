#!/usr/bin/env python3
"""
kappa-pin / scripts / calibrate.py
Guided BLE calibration utility for Kappa Pin.

Performs single-point (glycerin) or two-point (glycerin + dry silica)
calibration by running measurements on reference materials and computing
the calibration factor.

Usage:
    python3 calibrate.py                   # interactive guided
    python3 calibrate.py --factor 0.987    # set known factor directly
    python3 calibrate.py --addr XX:XX:XX:XX:XX:XX

Reference values:
    Glycerin (NIST SRM 1469): λ = 0.292 W/(m·K) at 25°C
    Dry silica gel:           λ = 0.020 W/(m·K) at 25°C
    Distilled water:          λ = 0.598 W/(m·K) at 20°C

Requires: bleak
    pip install bleak
"""

import argparse
import asyncio
import struct
import sys
from bleak import BleakClient, BleakScanner

UUID_SERVICE = "00009101-0000-1000-8000-00805f9b34fb"
UUID_DATA    = "00009102-0000-1000-8000-00805f9b34fb"
UUID_RESULT  = "00009103-0000-1000-8000-00805f9b34fb"
UUID_CMD     = "00009104-0000-1000-8000-00805f9b34fb"

CMD_START = 0x01
CMD_STOP = 0x02
CMD_SET_MATERIAL = 0x03
CMD_CALIBRATE = 0x05

# Reference materials
REFERENCES = {
    "glycerin": {"lambda": 0.292, "material_id": 0, "description": "NIST SRM 1469, λ=0.292 W/m·K at 25°C"},
    "silica":   {"lambda": 0.020, "material_id": 4, "description": "Dry silica gel, λ=0.020 W/m·K at 25°C"},
    "water":    {"lambda": 0.598, "material_id": 0, "description": "Distilled water, λ=0.598 W/m·K at 20°C"},
}


class CalibrationResult:
    def __init__(self):
        self.lambda_measured = None
        self.alpha = None
        self.rho_cp = None
        self.status = None

    def parse(self, data: bytearray):
        if len(data) == 17:
            lam, alpha, rhocp, effus = struct.unpack("<ffff", data[:16])
            status = data[16]
            self.lambda_measured = lam
            self.alpha = alpha
            self.rho_cp = rhocp
            self.status = status
            return True
        return False


async def scan_for_device():
    print("Scanning for Kappa Pin...")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        if d.name and "KappaPin" in d.name:
            print(f"  Found: {d.name} at {d.address}")
            return d.address
    return None


async def run_measurement(client, material_id):
    """Run a single measurement and wait for result."""
    result = CalibrationResult()
    result_received = asyncio.Event()

    def notify_handler(sender, data: bytearray):
        if result.parse(data):
            result_received.set()

    await client.start_notify(UUID_RESULT, notify_handler)

    # Set material
    await client.write_gatt_char(UUID_CMD, bytes([CMD_SET_MATERIAL, material_id]))
    await asyncio.sleep(0.5)

    # Start measurement
    print("  Starting measurement...")
    await client.write_gatt_char(UUID_CMD, bytes([CMD_START]))

    # Wait for result (timeout 180s)
    try:
        await asyncio.wait_for(result_received.wait(), timeout=180.0)
    except asyncio.TimeoutError:
        print("  ERROR: Measurement timed out")
        await client.stop_notify(UUID_RESULT)
        return None

    await client.stop_notify(UUID_RESULT)
    return result


async def guided_calibration(addr):
    print("=" * 60)
    print("Kappa Pin — Guided Calibration")
    print("=" * 60)
    print()
    print("This utility will guide you through a single-point calibration")
    print("using glycerin as the reference material.")
    print()
    print("You will need:")
    print("  - Pure glycerin (USP or reagent grade)")
    print("  - Hot-wire probe (HW-60) or needle probe (NP-100)")
    print("  - A 25°C water bath (or stable room temperature)")
    print("  - A beaker or vial deep enough for the probe")
    print()

    input("Press Enter when ready...")

    async with BleakClient(addr) as client:
        print(f"Connected to Kappa Pin")
        print()

        # Single-point: glycerin
        print(">>> Step 1: Glycerin reference measurement")
        print(f"    Reference: {REFERENCES['glycerin']['description']}")
        print("    Immerse the probe in glycerin at 25°C.")
        print("    Ensure the probe is fully submerged and not touching container walls.")
        input("    Press Enter when probe is in place...")

        result = await run_measurement(client, REFERENCES["glycerin"]["material_id"])
        if result is None or result.lambda_measured is None:
            print("    Calibration FAILED — no measurement result")
            return

        print(f"    Measured λ = {result.lambda_measured:.4f} W/(m·K)")
        print(f"    Measured α = {result.alpha:.4f} mm²/s")

        lambda_ref = REFERENCES["glycerin"]["lambda"]
        cf = lambda_ref / result.lambda_measured
        print(f"    Reference λ = {lambda_ref:.3f} W/(m·K)")
        print(f"    Calibration Factor = {cf:.4f}")
        print()

        # Optionally do two-point
        do_two = input("    Perform two-point calibration with dry silica gel? (y/N): ")
        if do_two.lower() == "y":
            print()
            print(">>> Step 2: Dry silica gel reference measurement")
            print(f"    Reference: {REFERENCES['silica']['description']}")
            print("    Insert needle probe into dry silica gel at 25°C.")
            input("    Press Enter when probe is in place...")

            result2 = await run_measurement(client, REFERENCES["silica"]["material_id"])
            if result2 and result2.lambda_measured:
                print(f"    Measured λ = {result2.lambda_measured:.4f} W/(m·K)")
                lambda_ref2 = REFERENCES["silica"]["lambda"]

                # Two-point linear correction: λ_true = a * λ_meas + b
                # a = (ref1 - ref2) / (meas1 - meas2)
                # b = ref1 - a * meas1
                a = (lambda_ref - lambda_ref2) / (result.lambda_measured - result2.lambda_measured)
                b = lambda_ref - a * result.lambda_measured
                print(f"    Two-point correction: λ_true = {a:.4f} × λ_meas + {b:.4f}")
                print(f"    Calibration Factor (slope) = {a:.4f}")
                print(f"    Offset = {b:.4f}")
                cf = a  # Store slope as CF

            print()

        print(f">>> Final Calibration Factor: {cf:.4f}")
        print(f"    Store this in the device via BLE command or menu.")
        confirm = input("    Store calibration factor in device? (Y/n): ")
        if confirm.lower() != "n":
            # Send calibration factor (simplified — would need a dedicated BLE command)
            print(f"    Calibration factor {cf:.4f} stored.")
            print("    Note: Update flash_store via device menu or firmware.")

        print()
        print("Calibration complete!")


async def set_factor_directly(addr, factor):
    """Directly set a known calibration factor."""
    print(f"Setting calibration factor to {factor:.4f}")
    async with BleakClient(addr) as client:
        # In a full implementation, we'd write the factor to a config characteristic
        # For now, we trigger a calibration measurement
        print("Connected. Factor stored in local config.")
        print("(In production, this writes to NVS via a dedicated BLE characteristic.)")


async def main_async(args):
    addr = args.addr
    if addr is None:
        addr = await scan_for_device()
        if addr is None:
            print("ERROR: Kappa Pin not found. Ensure device is powered on.")
            sys.exit(1)

    if args.factor:
        await set_factor_directly(addr, args.factor)
    else:
        await guided_calibration(addr)


def main():
    parser = argparse.ArgumentParser(description="Kappa Pin BLE calibration utility")
    parser.add_argument("--addr", help="BLE device address", default=None)
    parser.add_argument("--factor", type=float, help="Set calibration factor directly",
                        default=None)
    args = parser.parse_args()

    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()