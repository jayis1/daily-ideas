#!/usr/bin/env python3
"""alkane_cal.py — Plume Sniffer n-alkane calibration tool.

Connects to a Plume Sniffer device over BLE, runs a guided n-alkane
calibration procedure, and uploads the retention-time anchors to the
device's NVS via the Control characteristic.

Usage:
    python3 alkane_cal.py [--device MAC] [--anchors FILE]

If --anchors is given, loads pre-recorded retention times from a JSON
file instead of interactive entry. The JSON format is:
    {"C5": 30.0, "C6": 48.0, "C7": 72.0, ... "C16": 705.0}
"""

import argparse
import json
import sys
import struct

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install bleak:  pip install bleak")
    sys.exit(1)

UUID_CTRL   = "00001841-0000-1000-8000-00805f9b34fb"
UUID_CHROM  = "00001842-0000-1000-8000-00805f9b34fb"
UUID_RESULT = "00001843-0000-1000-8000-00805f9b34fb"

ALKANES = ["C5", "C6", "C7", "C8", "C9", "C10",
           "C11", "C12", "C13", "C14", "C15", "C16"]
ALKANE_RI = [500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600]


async def find_device():
    print("Scanning for Plume Sniffer...")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        if "Plume" in (d.name or ""):
            print(f"Found: {d.name} ({d.address})")
            return d.address
    print("Plume Sniffer not found.")
    return None


def get_anchors_interactive():
    print("\n=== n-Alkane Calibration ===")
    print("Run a GC with an n-alkane mix (C5–C16 headspace) and enter")
    print("the retention time (seconds) for each alkane peak.")
    print("Press Enter to skip an alkane you didn't see.\n")
    anchors = {}
    for alk, ri in zip(ALKANES, ALKANE_RI):
        while True:
            val = input(f"  {alk} (RI={ri}): tR [s] = ").strip()
            if val == "":
                break
            try:
                t = float(val)
                anchors[alk] = t
                break
            except ValueError:
                print("  Enter a number or press Enter to skip.")
    return anchors


def anchors_to_floats(anchors):
    """Convert dict to ordered float list (missing → 0.0 placeholder)."""
    result = []
    for alk in ALKANES:
        result.append(anchors.get(alk, 0.0))
    return result


def build_anchor_packet(floats):
    """Pack 12 floats (48 bytes) + a 1-byte command prefix (0x10 = set anchors)."""
    return bytes([0x10]) + struct.pack("<12f", *floats)


async def upload_anchors(address, floats):
    async with BleakClient(address, timeout=15.0) as client:
        pkt = build_anchor_packet(floats)
        await client.write_gatt_char(UUID_CTRL, pkt, response=True)
        print(f"Uploaded {len(floats)} anchors to device NVS.")


def main():
    ap = argparse.ArgumentParser(description="Plume Sniffer n-alkane calibration")
    ap.add_argument("--device", help="BLE MAC address")
    ap.add_argument("--anchors", help="JSON file with pre-recorded anchors")
    ap.add_argument("--save", help="Save anchors to JSON file")
    args = ap.parse_args()

    import asyncio

    if args.anchors:
        with open(args.anchors) as f:
            anchors = json.load(f)
        print(f"Loaded anchors from {args.anchors}: {anchors}")
    else:
        anchors = get_anchors_interactive()

    if not anchors:
        print("No anchors entered. Nothing to upload.")
        return

    if args.save:
        with open(args.save, "w") as f:
            json.dump(anchors, f, indent=2)
        print(f"Saved anchors to {args.save}")

    floats = anchors_to_floats(anchors)
    print(f"\nAnchor float array: {floats}")

    address = args.device
    if not address:
        address = asyncio.run(find_device())
    if not address:
        print("Cannot upload — no device found.")
        return

    asyncio.run(upload_anchors(address, floats))
    print("Calibration complete.")


if __name__ == "__main__":
    main()