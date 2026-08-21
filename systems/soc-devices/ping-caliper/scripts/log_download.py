#!/usr/bin/env python3
"""
Ping Caliper — log_download.py

Pull measurement and A-scan logs from the Ping Caliper's MicroSD card over BLE.

Usage:
    python log_download.py --addr AA:BB:CC:DD:EE:FF --output ./logs/

Outputs:
    ./logs/PINGLOG.csv      — all measurement records
    ./logs/ASCAN_nnnn.bin    — raw A-scan captures

Requires: bleak
"""

import argparse
import asyncio
import os
import struct

SVC_NDT      = "6e40fb10-b5a3-f393-e0a9-e50e24dcca9e"
CHR_CMD      = "6e40fb14-b5a3-f393-e0a9-e50e24dcca9e"
CHR_MEAS     = "6e40fb11-b5a3-f393-e0a9-e50e24dcca9e"
CHR_ASCAN    = "6e40fb12-b5a3-f393-e0a9-e50e24dcca9e"

CMD_GET_LOG  = 0x1D
CMD_GET_ASCAN = 0x11


async def run(addr, output_dir):
    from bleak import BleakClient

    os.makedirs(output_dir, exist_ok=True)
    print(f"Connecting to {addr} ...")
    async with BleakClient(addr, timeout=15.0) as client:
        print("Connected. Requesting log (last 100 entries) ...")

        log_records = []

        def meas_handler(sender, data: bytearray):
            if len(data) >= 40:
                thk, tof = struct.unpack_from("<ff", data, 0)
                velocity = struct.unpack_from("<I", data, 8)[0]
                valid = data[12]
                flaw_detected = data[13]
                flaw_depth, flaw_equiv = struct.unpack_from("<ff", data, 14)
                material = data[22:38].rstrip(b"\x00").decode("utf-8", errors="replace")
                battery = struct.unpack_from("<h", data, 38)[0]
                log_records.append({
                    "thickness_mm": thk,
                    "tof_ns": tof,
                    "velocity_mps": velocity,
                    "valid": valid,
                    "flaw_detected": flaw_detected,
                    "flaw_depth_mm": flaw_depth,
                    "flaw_equiv_mm": flaw_equiv,
                    "material": material,
                    "battery_pct": battery,
                })
                print(f"\r  Received {len(log_records)} records ...", end="", flush=True)

        await client.start_notify(CHR_MEAS, meas_handler)

        # Request last 100 entries
        payload = struct.pack("<IB", 0, 100)
        await client.write_gatt_char(CHR_CMD,
                                      bytes([CMD_GET_LOG]) + payload,
                                      response=False)

        # Wait for streaming to complete
        await asyncio.sleep(5.0)
        print(f"\nDone. {len(log_records)} records received.")

        await client.stop_notify(CHR_MEAS)

        # Write CSV
        csv_path = os.path.join(output_dir, "PINGLOG.csv")
        with open(csv_path, "w") as f:
            f.write("idx,thickness_mm,tof_ns,velocity_mps,valid,flaw_detected,"
                    "flaw_depth_mm,flaw_equiv_mm,material,battery_pct\n")
            for i, r in enumerate(log_records):
                f.write(f"{i},{r['thickness_mm']:.3f},{r['tof_ns']:.0f},"
                        f"{r['velocity_mps']},{r['valid']},{r['flaw_detected']},"
                        f"{r['flaw_depth_mm']:.2f},{r['flaw_equiv_mm']:.2f},"
                        f"\"{r['material']}\",{r['battery_pct']}\n")
        print(f"Wrote {csv_path}")

        # Also pull the latest A-scan
        print("Requesting latest A-scan ...")
        ascan_chunks = {}

        def ascan_handler(sender, data: bytearray):
            if len(data) >= 6:
                chunk_idx, total, count = struct.unpack_from("<HHH", data, 0)
                samples = data[6:6 + 128]
                ascan_chunks[chunk_idx] = (total, count, samples)

        await client.start_notify(CHR_ASCAN, ascan_handler)
        await client.write_gatt_char(CHR_CMD, bytes([CMD_GET_ASCAN]), response=False)
        await asyncio.sleep(3.0)
        await client.stop_notify(CHR_ASCAN)

        if ascan_chunks:
            total = list(ascan_chunks.values())[0][0]
            count = list(ascan_chunks.values())[0][1]
            env = b""
            for i in range(total):
                if i in ascan_chunks:
                    env += ascan_chunks[i][2]
            bin_path = os.path.join(output_dir, "ASCAN_latest.bin")
            with open(bin_path, "wb") as f:
                f.write(struct.pack("<HH", count, 0))
                f.write(env[:count * 2])
            print(f"Wrote {bin_path} ({len(env)} bytes, {count} samples)")
        else:
            print("No A-scan received.")


def main():
    p = argparse.ArgumentParser(description="Ping Caliper log downloader")
    p.add_argument("--addr", required=True, help="BLE MAC address")
    p.add_argument("--output", default="./logs", help="Output directory")
    args = p.parse_args()
    try:
        asyncio.run(run(args.addr, args.output))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()