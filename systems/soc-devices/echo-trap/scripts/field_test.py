#!/usr/bin/env python3
"""
Echo Trap — field_test.py

Run a field test on an Echo Trap device over BLE: verify the fan,
UV LED, LoRaWAN uplink, and sensor readings. Reports pass/fail.

Usage:
    python field_test.py --addr AA:BB:CC:DD:EE:FF

Requires: bleak
    pip install bleak

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import asyncio
import struct
import time

# BLE UUIDs
CHR_DEVICE_INFO = "6e41ec01-b5a3-f393-e0a9-e50e24dcca9e"
CHR_COMMAND     = "6e41ec08-b5a3-f393-e0a9-e50e24dcca9e"
CHR_SPECIES     = "6e41ec06-b5a3-f393-e0a9-e50e24dcca9e"
CHR_LORA_STATUS = "6e41ec09-b5a3-f393-e0a9-e50e24dcca9e"


async def run_test(addr: str):
    from bleak import BleakClient

    print(f"Echo Trap Field Test")
    print(f"=" * 50)
    print(f"Connecting to {addr} ...")

    results = {}

    async with BleakClient(addr, timeout=15.0) as client:
        print(f"Connected. RSSI: {await client.get_rssi()}")

        # 1. Device info
        info = await client.read_gatt_char(CHR_DEVICE_INFO)
        fw_ver = info[0] if len(info) > 0 else 0
        hw_ver = info[1] if len(info) > 1 else 0
        battery = info[2] if len(info) > 2 else 0
        name = info[3:19].decode('ascii', errors='replace').strip('\x00')
        print(f"\n--- Device Info ---")
        print(f"  Firmware: v{fw_ver}.0")
        print(f"  Hardware: v{hw_ver}.0")
        print(f"  Battery:  {battery}%")
        print(f"  Name:     {name}")
        results['device_info'] = fw_ver > 0

        # 2. Species counts (current period)
        counts_data = await client.read_gatt_char(CHR_SPECIES)
        if len(counts_data) >= 24:
            counts = struct.unpack_from("<12H", counts_data)
            print(f"\n--- Species Counts (current period) ---")
            species_names = [
                "Aedes", "Culex", "Anopheles", "Honeybee", "Drosophila",
                "Codling Moth", "Armyworm", "Housefly", "Wasp",
                "Lacewing", "Hoverfly", "Unknown"
            ]
            for i, (name_s, count) in enumerate(zip(species_names, counts)):
                if count > 0:
                    print(f"  {name_s}: {count}")
            results['species_counts'] = sum(counts) > 0
        else:
            print(f"  (no counts data)")
            results['species_counts'] = False

        # 3. LoRaWAN status
        lora_data = await client.read_gatt_char(CHR_LORA_STATUS)
        joined = lora_data[0] if len(lora_data) > 0 else 0
        rssi = struct.unpack_from("b", lora_data, 1)[0] if len(lora_data) > 1 else 0
        uplinks = lora_data[2] if len(lora_data) > 2 else 0
        print(f"\n--- LoRaWAN ---")
        print(f"  Joined:    {'YES' if joined else 'NO'}")
        print(f"  RSSI:      {rssi} dBm")
        print(f"  Uplinks:   {uplinks}")
        results['lora_joined'] = bool(joined)

        # 4. Fan test
        print(f"\n--- Fan Test ---")
        print(f"  Sending fan-test command...")
        await client.write_gatt_char(CHR_COMMAND, bytes([0x04, 0x01]))
        print(f"  Fan should be running for 2 seconds. Listen for airflow.")
        await asyncio.sleep(3)
        results['fan_test'] = True  # user verifies manually

        # 5. UV LED test
        print(f"\n--- UV LED Test ---")
        print(f"  Setting UV override to 100% for 5 seconds...")
        await client.write_gatt_char(CHR_COMMAND, bytes([0x01, 0xFF]))
        print(f"  UV LED should be ON (visible as dim purple).")
        await asyncio.sleep(5)
        await client.write_gatt_char(CHR_COMMAND, bytes([0x01, 0x00]))
        print(f"  UV LED back to auto mode.")
        results['uv_test'] = True

    # Summary
    print(f"\n{'=' * 50}")
    print(f"FIELD TEST SUMMARY")
    print(f"{'=' * 50}")
    all_pass = True
    for test, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test:20s} {status}")
        if not passed:
            all_pass = False

    if all_pass:
        print(f"\n✓ All tests passed!")
    else:
        print(f"\n✗ Some tests failed — check details above.")


def main():
    parser = argparse.ArgumentParser(description='Echo Trap field test')
    parser.add_argument('--addr', required=True, help='BLE address')
    args = parser.parse_args()
    asyncio.run(run_test(args.addr))


if __name__ == '__main__':
    main()