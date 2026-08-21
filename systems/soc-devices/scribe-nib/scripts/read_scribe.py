#!/usr/bin/env python3
"""
read_scribe.py — Read recognized text from Scribe Nib over BLE

Connects to the custom GATT service (0xFFB0) and displays
recognized characters in real-time.

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import asyncio
import sys

# BLE UUIDs
SCRIBE_SERVICE_UUID = "0000ffb0-0000-1000-8000-00805f9b34fb"
CHAR_TEXT_UUID      = "0000ffb1-0000-1000-8000-00805f9b34fb"
CHAR_LAST_CHAR_UUID = "0000ffb2-0000-1000-8000-00805f9b34fb"
CHAR_CONFIDENCE_UUID = "0000ffb3-0000-1000-8000-00805f9b34fb"
CHAR_PROFILE_UUID   = "0000ffb5-0000-1000-8000-00805f9b34fb"
CHAR_MODE_UUID      = "0000ffb6-0000-1000-8000-00805f9b34fb"
CHAR_BATTERY_UUID   = "0000ffb7-0000-1000-8000-00805f9b34fb"

CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


async def read_scribe(mac_address, verbose=False):
    """Connect to Scribe Nib and read recognized text."""
    try:
        from bleak import BleakClient
    except ImportError:
        print("Error: bleak is required. Install with: pip install bleak")
        sys.exit(1)

    recognized_text = ""

    def notification_handler(characteristic, data):
        nonlocal recognized_text
        if characteristic.uuid.endswith("ffb1"):  # Text characteristic
            text = data.decode('utf-8', errors='replace')
            recognized_text += text
            print(f"\r[Text] {recognized_text}", end='', flush=True)
        elif characteristic.uuid.endswith("ffb2"):  # Last char
            char_id = int.from_bytes(data, 'big')
            if 0 <= char_id < 62:
                char = CHARSET[char_id]
            else:
                char = '?'
            if verbose:
                print(f"\n[Last Char] {char} (id={char_id})", flush=True)
        elif characteristic.uuid.endswith("ffb3"):  # Confidence
            import struct
            confidence = struct.unpack('<f', data)[0]
            if verbose:
                print(f"\n[Confidence] {confidence:.2f}", flush=True)

    print(f"Connecting to ScribeNib at {mac_address}...")

    async with BleakClient(mac_address) as client:
        print(f"Connected! RSSI: {await get_rssi(client)}")

        # Subscribe to notifications
        for uuid in [CHAR_TEXT_UUID, CHAR_LAST_CHAR_UUID, CHAR_CONFIDENCE_UUID]:
            try:
                await client.start_notify(uuid, notification_handler)
                print(f"Subscribed to {uuid}")
            except Exception as e:
                print(f"Could not subscribe to {uuid}: {e}")

        # Read static characteristics
        try:
            profile_data = await client.read_gatt_char(CHAR_PROFILE_UUID)
            print(f"Active profile: {int.from_bytes(profile_data, 'big')}")
        except:
            pass

        try:
            mode_data = await client.read_gatt_char(CHAR_MODE_UUID)
            modes = ["AUTO", "LETTERS", "NUMBERS"]
            mode = int.from_bytes(mode_data, 'big')
            print(f"Recognition mode: {modes[mode] if mode < 3 else 'UNKNOWN'}")
        except:
            pass

        try:
            battery_data = await client.read_gatt_char(CHAR_BATTERY_UUID)
            print(f"Battery: {int.from_bytes(battery_data, 'big')}%")
        except:
            pass

        print("\n--- Listening for recognized characters (Ctrl+C to stop) ---\n")

        try:
            while True:
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            print(f"\n\nFinal text: {recognized_text}")
            print(f"Characters: {len(recognized_text)}")


async def get_rssi(client):
    """Attempt to read RSSI (not always available)."""
    try:
        # bleak doesn't expose RSSI directly in all backends
        return "N/A"
    except:
        return "N/A"


def main():
    parser = argparse.ArgumentParser(description="Read Scribe Nib BLE output")
    parser.add_argument("--mac", required=True, help="Device MAC address (AA:BB:CC:DD:EE:FF)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    asyncio.run(read_scribe(args.mac, verbose=args.verbose))


if __name__ == "__main__":
    main()