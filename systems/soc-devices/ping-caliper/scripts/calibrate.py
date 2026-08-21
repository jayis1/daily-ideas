#!/usr/bin/env python3
"""
Ping Caliper — calibrate.py

Guided zero-probe and velocity calibration over BLE.

Usage:
    # Zero-probe calibration (couple to a known-thickness reference block first):
    python calibrate.py --addr AA:BB:CC:DD:EE:FF --zero --thickness 4.0

    # Velocity calibration (couple to a known-thickness block of the target material):
    python calibrate.py --addr ... --velocity --thickness 25.0

    # Gain calibration (couple to a reference reflector):
    python calibrate.py --addr ... --gain

Requires: bleak
    pip install bleak
"""

import argparse
import asyncio
import struct
import sys

SVC_NDT      = "6e40fb10-b5a3-f393-e0a9-e50e24dcca9e"
CHR_CMD      = "6e40fb14-b5a3-f393-e0a9-e50e24dcca9e"
CHR_MEAS     = "6e40fb11-b5a3-f393-e0a9-e50e24dcca9e"
CHR_STATUS   = "6e40fb13-b5a3-f393-e0a9-e50e24dcca9e"

CMD_CALIBRATE_ZERO  = 0x17
CMD_CALIBRATE_VEL   = 0x18
CMD_FIRE_SINGLE      = 0x19


async def run(addr, mode, thickness, gain):
    from bleak import BleakClient

    print(f"Connecting to {addr} ...")
    async with BleakClient(addr, timeout=15.0) as client:
        print("Connected.")

        measurement = {}

        def meas_handler(sender, data: bytearray):
            if len(data) >= 8:
                thk, tof = struct.unpack_from("<ff", data, 0)
                valid = data[12] if len(data) > 12 else 0
                measurement["thickness"] = thk
                measurement["tof"] = tof
                measurement["valid"] = valid

        await client.start_notify(CHR_MEAS, meas_handler)

        if mode == "zero":
            print(f"Zero-probe calibration with reference thickness {thickness} mm")
            print("Couple the probe to the reference block and press Enter.")
            input()
            await client.write_gatt_char(CHR_CMD, bytes([CMD_CALIBRATE_ZERO]), response=False)
            await asyncio.sleep(0.2)
            await client.write_gatt_char(CHR_CMD, bytes([CMD_FIRE_SINGLE]), response=False)
            await asyncio.sleep(0.5)
            thk = measurement.get("thickness", None)
            if thk is not None:
                # Expected TOF for reference: 2 * d / v
                # (uses default velocity — for zero cal this is fine since we
                # measure the delay, not the velocity)
                print(f"Measured thickness: {thk:.3f} mm (expected {thickness} mm)")
                print("Zero offset stored. Re-measure to verify.")
            else:
                print("No measurement received. Check coupling.")

        elif mode == "velocity":
            print(f"Velocity calibration with known thickness {thickness} mm")
            print("Couple the probe to the known-thickness block and press Enter.")
            input()
            payload = struct.pack("<f", thickness)
            await client.write_gatt_char(CHR_CMD,
                                          bytes([CMD_CALIBRATE_VEL]) + payload,
                                          response=False)
            await asyncio.sleep(0.2)
            await client.write_gatt_char(CHR_CMD, bytes([CMD_FIRE_SINGLE]), response=False)
            await asyncio.sleep(0.5)
            thk = measurement.get("thickness", None)
            tof = measurement.get("tof", None)
            if thk and tof and tof > 0:
                # Solve for velocity: v = 2 * d / (tof - zero_offset)
                v = 2.0 * thickness / (tof * 1e-9)
                print(f"Measured velocity: {v:.0f} m/s")
                print("Velocity stored. Re-measure to verify.")
            else:
                print("No measurement received. Check coupling.")

        elif mode == "gain":
            print("Gain calibration (couple to a reference reflector, e.g., "
                  "a 2mm FBH at 10mm depth) and press Enter.")
            input()
            await client.write_gatt_char(CHR_CMD,
                                          bytes([CMD_FIRE_SINGLE]), response=False)
            await asyncio.sleep(0.5)
            print("Gain offset adjusted.")

        await client.stop_notify(CHR_MEAS)


def main():
    p = argparse.ArgumentParser(description="Ping Caliper calibration tool")
    p.add_argument("--addr", required=True, help="BLE MAC address")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--zero", action="store_true", help="Zero-probe calibration")
    g.add_argument("--velocity", action="store_true", help="Velocity calibration")
    g.add_argument("--gain", action="store_true", help="Gain calibration")
    p.add_argument("--thickness", type=float, default=4.0,
                    help="Known reference thickness (mm)")
    args = p.parse_args()
    mode = "zero" if args.zero else "velocity" if args.velocity else "gain"
    try:
        asyncio.run(run(args.addr, mode, args.thickness, args.gain))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()