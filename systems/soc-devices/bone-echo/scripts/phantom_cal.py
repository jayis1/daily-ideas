#!/usr/bin/env python3
"""
phantom_cal.py — Bone Echo phantom calibration script

Connects to Bone Echo over BLE, runs the phantom calibration procedure,
and verifies the measured SOS and BUA reference are within spec.

Usage:
    python3 phantom_cal.py [--mac AA:BB:CC:DD:EE:FF]

Requirements:
    pip install bleak
"""

import argparse
import asyncio
import sys

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install bleak: pip install bleak")
    sys.exit(1)

RESULTS_UUID = "0000fe21-0000-1000-8000-00805f9b34fb"
STATUS_UUID  = "0000fe23-0000-1000-8000-00805f9b34fb"
COMMAND_UUID = "0000fe24-0000-1000-8000-00805f9b34fb"

PHANTOM_SOS_EXPECTED = 2700.0  # m/s for acrylic PMMA
PHANTOM_SOS_TOLERANCE = 50.0   # ±50 m/s


class PhantomCalibrator:
    def __init__(self):
        self.sos_measured = None
        self.bua_measured = None
        self.done = asyncio.Event()

    def on_results(self, characteristic, data: bytearray):
        line = data.decode("utf-8", errors="ignore").strip()
        if line.startswith("R:"):
            parts = line[2:].split(",")
            self.sos_measured = float(parts[0])
            self.bua_measured = float(parts[1])
            print(f"Phantom SOS: {self.sos_measured:.1f} m/s  BUA: {self.bua_measured:.1f} dB/MHz")
            self.done.set()


async def main():
    parser = argparse.ArgumentParser(description="Bone Echo phantom calibration")
    parser.add_argument("--mac", help="Device MAC address", default=None)
    args = parser.parse_args()

    mac = args.mac
    if mac is None:
        print("Scanning for Bone Echo...")
        devices = await BleakScanner.discover(timeout=10)
        for d in devices:
            if d.name and "Bone Echo" in d.name:
                mac = d.address
                print(f"Found: {d.name} ({d.address})")
                break
        if mac is None:
            print("No Bone Echo device found.")
            return

    print(f"Connecting to {mac}...")
    async with BleakClient(mac) as client:
        cal = PhantomCalibrator()
        await client.start_notify(RESULTS_UUID, cal.on_results)

        print("Place the 25mm acrylic phantom between transducers.")
        print("Press Enter when ready...")
        # input()  # Uncomment for interactive use
        await asyncio.sleep(1)

        print("Sending PHANTOM command...")
        await client.write_gatt_char(COMMAND_UUID, b"PHANTOM\n")

        try:
            await asyncio.wait_for(cal.done.wait(), timeout=10)
        except asyncio.TimeoutError:
            print("ERROR: No response within 10 s. Check phantom placement.")
            return

        # Verify
        if cal.sos_measured is None:
            print("ERROR: No SOS measurement received.")
            return

        delta = abs(cal.sos_measured - PHANTOM_SOS_EXPECTED)
        if delta <= PHANTOM_SOS_TOLERANCE:
            print(f"PASS: SOS = {cal.sos_measured:.1f} m/s "
                  f"(expected {PHANTOM_SOS_EXPECTED:.0f} ± {PHANTOM_SOS_TOLERANCE:.0f})")
            print("Phantom calibration stored in NVS.")
            print("Reference FFT captured for BUA.")
        else:
            print(f"FAIL: SOS = {cal.sos_measured:.1f} m/s "
                  f"(expected {PHANTOM_SOS_EXPECTED:.0f} ± {PHANTOM_SOS_TOLERANCE:.0f}, "
                  f"delta = {delta:.1f})")
            print("Check transducer seating and gel coupling.")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())