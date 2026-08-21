#!/usr/bin/env python3
"""
Pulse Hound — BLE Decoder
Decode RSSI + spectrum + bearing data from the Pulse Hound BLE GATT stream.

Usage:
    python3 decode_ble.py [--device MAC]

If no device address is given, scans for "Pulse Hound" and connects to the first one found.
"""

import argparse
import struct
import asyncio
import json
import sys

# BLE characteristic UUIDs
UUID_RSSI      = "8e7f1a02-b000-1000-8000-00805f9b34fb"
UUID_SPECTRUM  = "8e7f1a03-b000-1000-8000-00805f9b34fb"
UUID_BEARING   = "8e7f1a04-b000-1000-8000-00805f9b34fb"
UUID_CLASS     = "8e7f1a05-b000-1000-8000-00805f9b34fb"
UUID_MODE      = "8e7f1a06-b000-1000-8000-00805f9b34fb"
UUID_BATTERY   = "8e7f1a07-b000-1000-8000-00805f9b34fb"
UUID_LOG_CTRL  = "8e7f1a08-b000-1000-8000-00805f9b34fb"

CLASS_NAMES = {
    0: "CW/Analog",
    1: "WiFi/BLE",
    2: "Cellular",
    3: "Radar/UWB",
    4: "Thermal",
    5: "Unknown",
}

MODE_NAMES = {
    0: "SWEEP",
    1: "DF",
    2: "MONITOR",
    3: "POWER_SAVE",
}


def decode_rssi(data: bytes) -> float:
    """Decode RSSI from int16 dBm*100 (little-endian)."""
    if len(data) < 2:
        return -999.0
    val = struct.unpack('<h', data[:2])[0]
    return val / 100.0


def decode_bearing(data: bytes):
    """Decode bearing (uint16 deg*10) + peak RSSI (int16 dBm*100)."""
    if len(data) < 4:
        return 0.0, -999.0
    bearing = struct.unpack('<H', data[:2])[0] / 10.0
    peak = struct.unpack('<h', data[2:4])[0] / 100.0
    return bearing, peak


def decode_classification(data: bytes) -> str:
    if len(data) < 1:
        return "Unknown"
    return CLASS_NAMES.get(data[0], f"Unknown({data[0]})")


def decode_battery(data: bytes) -> int:
    if len(data) < 1:
        return 0
    return data[0]


def spectrum_to_ascii(row_data: bytes, width: int = 48) -> str:
    """Convert a 64-byte spectrum row to a compact ASCII bar representation."""
    chars = " .:-=+*#%@"
    result = []
    for i in range(min(width, len(row_data))):
        intensity = row_data[i]
        idx = min(int(intensity / 256 * len(chars)), len(chars) - 1)
        result.append(chars[idx])
    return "".join(result)


async def scan_and_connect(bleak_client, device_addr=None):
    """Scan for Pulse Hound devices and connect."""
    from bleak import BleakScanner, BleakClient

    if device_addr is None:
        print("Scanning for 'Pulse Hound'...")
        devices = await BleakScanner.discover(timeout=10.0)
        target = None
        for d in devices:
            if d.name and "Pulse Hound" in d.name:
                target = d
                print(f"Found: {d.name} [{d.address}] RSSI={d.rssi} dBm")
                break
        if target is None:
            print("No Pulse Hound device found.")
            return None
        device_addr = target.address

    print(f"Connecting to {device_addr}...")
    client = BleakClient(device_addr)
    await client.connect()
    print(f"Connected: {client.is_connected}")
    return client


def notification_handler(sender, data):
    """Handle incoming BLE notifications."""
    uuid = str(sender).lower()

    if UUID_RSSI in uuid:
        rssi = decode_rssi(data)
        print(f"[RSSI] {rssi:.2f} dBm")
    elif UUID_SPECTRUM in uuid:
        ascii_row = spectrum_to_ascii(data)
        print(f"[SPECT] |{ascii_row}|")
    elif UUID_BEARING in uuid:
        bearing, peak = decode_bearing(data)
        print(f"[BEAR] {bearing:.1f}° peak={peak:.2f} dBm")
    elif UUID_CLASS in uuid:
        cls = decode_classification(data)
        print(f"[CLASS] {cls}")
    elif UUID_BATTERY in uuid:
        pct = decode_battery(data)
        print(f"[BAT] {pct}%")


async def main():
    parser = argparse.ArgumentParser(description="Pulse Hound BLE Decoder")
    parser.add_argument("--device", default=None, help="Device MAC address")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    args = parser.parse_args()

    try:
        from bleak import BleakClient
    except ImportError:
        print("Error: 'bleak' package not installed. Install with:")
        print("  pip install bleak")
        sys.exit(1)

    client = await scan_and_connect(None, args.device)
    if client is None:
        sys.exit(1)

    # Subscribe to all characteristics
    for uuid in [UUID_RSSI, UUID_SPECTRUM, UUID_BEARING, UUID_CLASS, UUID_BATTERY]:
        await client.start_notify(uuid, notification_handler)
        print(f"Subscribed to {uuid}")

    print("\n--- Streaming (Ctrl+C to stop) ---\n")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        for uuid in [UUID_RSSI, UUID_SPECTRUM, UUID_BEARING, UUID_CLASS, UUID_BATTERY]:
            await client.stop_notify(uuid)
        await client.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    asyncio.run(main())