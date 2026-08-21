#!/usr/bin/env python3
"""
calibrate.py — Collect a blank (drift-gas only) calibration for Iono Pin.

Reads a series of spectra over BLE while the device runs in calibration mode
(drift gas only, no sample), locates the Reactant Ion Peak (RIP, expected at
K0 ≈ 2.70), and computes a K0 offset correction that can be applied to the
firmware library or stored in flash.

Usage:
    python calibrate.py [--mac AA:BB:CC:DD:EE:FF] [--n 50]
"""
import argparse
import asyncio
import statistics
import struct
import sys

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install bleak: pip install bleak"); sys.exit(1)

IMS_SERVICE_UUID = "000018a0-0000-1000-8000-00805f9b34fb"
IMS_CHAR_UUID    = "00002be0-0000-1000-8000-00805f9b34fb"
IMS_SAMPLES     = 140
T_START_MS      = 0.5
T_END_MS        = 3.5
DRIFT_LEN_CM    = 8.5
DRIFT_V         = 2125.0
EXPECTED_RIP_K0 = 2.70


def parse_frame(data: bytes):
    if len(data) < 13:
        return None
    off = 0
    pressure, t_drift, t_amb = struct.unpack_from("<fff", data, off); off += 12
    n_peaks = data[off]; off += 1
    k0s = []
    for _ in range(n_peaks):
        k0 = struct.unpack_from("<f", data, off)[0]; off += 4
        k0s.append(k0)
    return {"pressure": pressure, "t_drift": t_drift, "k0s": k0s}


async def find_device(mac=None):
    if mac: return mac
    print("Scanning for Iono Pin...")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        for s in d.metadata.get("uuids", []):
            if s.lower() == IMS_SERVICE_UUID:
                return d.address
    print("Not found."); sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mac", default=None)
    ap.add_argument("--n", type=int, default=50, help="number of spectra to average")
    args = ap.parse_args()

    loop = asyncio.new_event_loop()
    mac = loop.run_until_complete(find_device(args.mac))

    rip_k0s = []

    async def run():
        async with BleakClient(mac) as client:
            print(f"Connected. Collecting {args.n} blank spectra...")
            def handler(sender, data):
                f = parse_frame(bytes(data))
                if not f: return
                # find peak closest to expected RIP
                if not f["k0s"]: return
                closest = min(f["k0s"], key=lambda k: abs(k - EXPECTED_RIP_K0))
                if abs(closest - EXPECTED_RIP_K0) < 0.3:
                    rip_k0s.append(closest)
                    if len(rip_k0s) % 10 == 0:
                        print(f"  {len(rip_k0s)}/{args.n}  RIP K0={closest:.3f}")
            await client.start_notify(IMS_CHAR_UUID, handler)
            while len(rip_k0s) < args.n:
                await asyncio.sleep(0.1)
            await client.stop_notify(IMS_CHAR_UUID)

    loop.run_until_complete(run())

    if len(rip_k0s) < 5:
        print("Not enough RIP peaks detected. Check drift gas flow and ionizer.")
        sys.exit(1)

    mean_k0 = statistics.mean(rip_k0s)
    stdev = statistics.stdev(rip_k0s)
    offset = EXPECTED_RIP_K0 - mean_k0

    print("\n=== Calibration result ===")
    print(f"RIP K0 measured:  {mean_k0:.4f} cm²/V·s (σ={stdev:.4f})")
    print(f"Expected RIP K0:  {EXPECTED_RIP_K0:.4f}")
    print(f"K0 offset:        {offset:+.4f}  (apply to library entries)")
    print()
    print("To apply, add this offset to every K0 in firmware/main/library.c,")
    print("or store it in flash and apply at classify() time.")
    print()
    print("If |offset| > 0.05, check:")
    print("  - drift tube length (should be 8.5 cm)")
    print("  - drift voltage (should be 2125 V)")
    print("  - BME280 pressure/temperature readings")


if __name__ == "__main__":
    main()