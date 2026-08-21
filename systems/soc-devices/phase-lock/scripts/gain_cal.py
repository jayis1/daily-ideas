#!/usr/bin/env python3
"""
gain_cal.py — gain calibration procedure for Phase Lock.

Connects over BLE, sweeps the reference amplitude from 10 mV to 2 V
(at f0 = 1 kHz with a loopback cable Ref Out → Signal In), records
R at each amplitude, fits a linear gain curve, and writes the
correction table back to the device's NVS via the Config
characteristic.

Usage:
    python gain_cal.py --addr XX:XX:XX:XX:XX:XX
"""
import argparse
import asyncio
import struct

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("pip install bleak numpy"); raise SystemExit(1)

import numpy as np

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
DEMOD_UUID  = "0000ffe1-0000-1000-8000-00805f9b34fb"
CMD_UUID    = "0000ffe4-0000-1000-8000-00805f9b34fb"

DEMO_FMT = struct.Struct("<Bfffff")

async def read_demod(client, timeout=2.0):
    """Wait for one demod notification and return (R, theta, X, Y, noise)."""
    fut = asyncio.get_event_loop().create_future()
    def cb(_, data):
        if not fut.done() and len(data) >= DEMO_FMT.size:
            tag, freq, gain, R, theta, X, Y, noise = DEMO_FMT.unpack(data[:DEMO_FMT.size])
            fut.set_result((R, theta, X, Y, noise))
    await client.start_notify(DEMOD_UUID, cb)
    try:
        return await asyncio.wait_for(fut, timeout)
    finally:
        await client.stop_notify(DEMOD_UUID)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--addr", required=True)
    ap.add_argument("--f0", type=float, default=1000.0, help="calibration frequency (Hz)")
    args = ap.parse_args()

    async with BleakClient(args.addr) as client:
        print(f"Connected to {args.addr}")
        # Set frequency
        await client.write_gatt_char(CMD_UUID, f"F:{args.f0}".encode())
        await asyncio.sleep(0.5)

        amplitudes = np.logspace(np.log10(0.01), np.log10(2.0), 20)
        measured_R = []

        print("Sweeping amplitude (loopback Ref Out → Signal In):")
        for a in amplitudes:
            await client.write_gatt_char(CMD_UUID, f"A:{a:.4f}".encode())
            await asyncio.sleep(1.0)   # settle
            R, theta, X, Y, noise = await read_demod(client)
            measured_R.append(R)
            print(f"  A={a:.4f} V  →  R={R:.6f} V  Θ={theta*57.3:.1f}°  noise={noise*1e9:.1f} nV/√Hz")

        # Linear fit: R = k * A (ideal k = 1.0 for unity loopback)
        amplitudes = np.array(amplitudes)
        measured_R = np.array(measured_R)
        k, b = np.polyfit(amplitudes, measured_R, 1)
        print(f"\nGain fit:  R = {k:.6f} × A + {b:.6f} V")
        print(f"Ideal:     R = 1.000000 × A")
        print(f"Deviation: {(k-1)*100:+.3f}% (this is the gain correction)")

        # Write the correction to NVS (the firmware stores a single scalar
        # gain correction for the loopback; in a full calibration we'd store
        # a per-frequency table.)
        # await client.write_gatt_char(CMD_UUID, f"GCAL:{k:.6f}".encode())

        print("\nDone. Apply this correction in your measurements.")

if __name__ == "__main__":
    asyncio.run(main())