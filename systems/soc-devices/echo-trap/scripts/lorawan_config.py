#!/usr/bin/env python3
"""
Echo Trap — lorawan_config.py

Provision LoRaWAN credentials (AppEUI, AppKey, DevEUI) on an Echo Trap
over BLE. The device saves them to NVS and attempts an OTAA join.

Usage:
    python lorawan_config.py --addr AA:BB:CC:DD:EE:FF \
        --appeui 0000000000000001 \
        --appkey 00112233445566778899AABBCCDDEEFF \
        --deveui 0000000000000001

Requires: bleak
    pip install bleak

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import asyncio
import struct

# BLE UUIDs
CHR_APP_EUI  = "6e41ec02-b5a3-f393-e0a9-e50e24dcca9e"
CHR_APP_KEY  = "6e41ec03-b5a3-f393-e0a9-e50e24dcca9e"
CHR_DEV_EUI  = "6e41ec04-b5a3-f393-e0a9-e50e24dcca9e"
CHR_SAVE     = "6e41ec05-b5a3-f393-e0a9-e50e24dcca9e"
CHR_LORA_STATUS = "6e41ec09-b5a3-f393-e0a9-e50e24dcca9e"


def parse_hex(s: str, length: int) -> bytes:
    """Parse a hex string to bytes (big-endian)."""
    s = s.replace(":", "").replace("-", "").replace(" ", "")
    if len(s) != length * 2:
        raise ValueError(f"Expected {length} bytes ({length*2} hex chars), got {len(s)//2}")
    return bytes.fromhex(s)


async def provision(addr: str, app_eui: str, app_key: str, dev_eui: str):
    from bleak import BleakClient

    app_eui_b = parse_hex(app_eui, 8)
    app_key_b = parse_hex(app_key, 16)
    dev_eui_b = parse_hex(dev_eui, 8)

    print(f"Connecting to {addr} ...")
    async with BleakClient(addr, timeout=15.0) as client:
        print("Connected. Writing LoRaWAN credentials...")

        # Write credentials (big-endian as per LoRaWAN spec)
        await client.write_gatt_char(CHR_APP_EUI, app_eui_b[::-1])  # LE for BLE
        await client.write_gatt_char(CHR_APP_KEY, app_key_b[::-1])
        await client.write_gatt_char(CHR_DEV_EUI, dev_eui_b[::-1])

        # Trigger save + OTAA join
        await client.write_gatt_char(CHR_SAVE, bytes([0x01]))
        print("Credentials saved. Waiting for OTAA join...")

        # Poll join status for up to 30 seconds
        for i in range(30):
            await asyncio.sleep(1)
            status = await client.read_gatt_char(CHR_LORA_STATUS)
            joined = status[0] if len(status) > 0 else 0
            rssi = struct.unpack_from("b", status, 1)[0] if len(status) > 1 else 0
            uplinks = status[2] if len(status) > 2 else 0
            print(f"\r  Join status: {joined} (RSSI={rssi}, uplinks={uplinks})",
                  end="", flush=True)
            if joined:
                print("\n✓ LoRaWAN joined successfully!")
                return

        print("\n✗ OTAA join timed out. Check your gateway and network server.")


def main():
    parser = argparse.ArgumentParser(description='Provision Echo Trap LoRaWAN keys')
    parser.add_argument('--addr', required=True, help='BLE address')
    parser.add_argument('--appeui', required=True, help='AppEUI (16 hex chars)')
    parser.add_argument('--appkey', required=True, help='AppKey (32 hex chars)')
    parser.add_argument('--deveui', required=True, help='DevEUI (16 hex chars)')
    args = parser.parse_args()

    asyncio.run(provision(args.addr, args.appeui, args.appkey, args.deveui))


if __name__ == '__main__':
    main()