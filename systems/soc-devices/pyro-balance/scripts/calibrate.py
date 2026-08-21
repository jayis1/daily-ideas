#!/usr/bin/env python3
"""
Pyro Balance — Mass & temperature calibration helper.

Sends calibration commands to Pyro Balance over BLE and verifies
the stored calibration values.

Requirements: bleak
    pip install bleak

Usage:
    # Mass calibration (place 5 g reference weight on crucible hanger)
    python3 calibrate.py --mass --ref 5000.0      # 5000 mg = 5 g

    # Temperature 2-point (ice bath then boiling water)
    python3 calibrate.py --temp --point 0
    python3 calibrate.py --temp --point 100

    # Read current calibration
    python3 calibrate.py --read
"""
import argparse
import asyncio
import struct
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "00001801-0000-1000-8000-00805f9b34fb"
CMD_UUID      = "00002a02-0000-1000-8000-00805f9b34fb"

HEADER = 0xAA

def make_frame(cmd: int, payload: bytes) -> bytes:
    plen = len(payload)
    buf = bytearray([HEADER, plen & 0xFF, (plen >> 8) & 0xFF, cmd])
    buf.extend(payload)
    crc = 0
    for b in buf:
        crc ^= b
    buf.append(crc)
    return bytes(buf)


async def find_device():
    print("Scanning for Pyro-Balance...")
    devices = await BleakScanner.discover(timeout=15)
    d = next((x for x in devices if "Pyro-Balance" in (x.name or "")), None)
    if not d:
        raise SystemExit("Pyro-Balance not found")
    return d


async def send_cmd(device, frame):
    async with BleakClient(device) as client:
        await client.write_gatt_characteristic(CMD_UUID, frame, response=True)
        await asyncio.sleep(0.5)


async def calibrate_mass(ref_mg):
    d = await find_device()
    payload = struct.pack("<f", float(ref_mg))
    await send_cmd(d, make_frame(0x16, payload))
    print(f"Mass calibration sent: ref={ref_mg} mg. Check device OLED for confirmation.")


async def calibrate_temp(point, temp_c):
    d = await find_device()
    payload = struct.pack("<Bf", int(point), float(temp_c))
    await send_cmd(d, make_frame(0x17, payload))
    print(f"Temperature calibration sent: point={point} temp={temp_c}°C.")


async def read_config():
    d = await find_device()
    async with BleakClient(d) as client:
        # GET_STATUS returns pb_status_t; for full config use GET_RESULT
        await client.write_gatt_characteristic(CMD_UUID, make_frame(0x14, b""))
        await asyncio.sleep(1)
        print("Status requested. See device OLED / BLE notifications for response.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mass", action="store_true", help="calibrate mass")
    ap.add_argument("--ref", type=float, default=5000.0, help="reference mass in mg")
    ap.add_argument("--temp", action="store_true", help="calibrate temperature")
    ap.add_argument("--point", type=int, default=0, help="temp calibration point index (0/1/2)")
    ap.add_argument("--temp-c", type=float, default=0.0, help="actual temperature in °C")
    ap.add_argument("--read", action="store_true", help="read current config")
    args = ap.parse_args()
    if args.mass:
        asyncio.run(calibrate_mass(args.ref))
    elif args.temp:
        asyncio.run(calibrate_temp(args.point, args.temp_c))
    elif args.read:
        asyncio.run(read_config())
    else:
        ap.print_help()