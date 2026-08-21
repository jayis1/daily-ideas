#!/usr/bin/env python3
"""
Therma Weave — Data Logger
Logs zone temperatures, duty cycles, currents, and ambient data to CSV.

Usage:
    python3 data_logger.py --mac AA:BB:CC:DD:EE:FF --output log.csv
    python3 data_logger.py --mac AA:BB:CC:DD:EE:FF --interval 5 --duration 3600

SPDX-License-Identifier: MIT
"""

import asyncio
import argparse
import struct
import csv
import sys
import time
from datetime import datetime

try:
    from bleak import BleakClient
except ImportError:
    print("ERROR: bleak library not installed. Run: pip install bleak")
    sys.exit(1)

# BLE UUIDs
THERMA_SERVICE_UUID = "0000ffb0-0000-1000-8000-00805f9b34fb"
CHAR_ZONE0_TARGET = "0000ffb1-0000-1000-8000-00805f9b34fb"
CHAR_ZONE1_TARGET = "0000ffb2-0000-1000-8000-00805f9b34fb"
CHAR_ZONE2_TARGET = "0000ffb3-0000-1000-8000-00805f9b34fb"
CHAR_ZONE3_TARGET = "0000ffb4-0000-1000-8000-00805f9b34fb"
CHAR_ZONE0_DUTY   = "0000ffb5-0000-1000-8000-00805f9b34fb"
CHAR_ZONE1_DUTY   = "0000ffb6-0000-1000-8000-00805f9b34fb"
CHAR_ZONE2_DUTY   = "0000ffb7-0000-1000-8000-00805f9b34fb"
CHAR_ZONE3_DUTY   = "0000ffb8-0000-1000-8000-00805f9b34fb"
CHAR_ZONE0_CURRENT= "0000ffb9-0000-1000-8000-00805f9b34fb"
CHAR_ZONE1_CURRENT= "0000ffba-0000-1000-8000-00805f9b34fb"
CHAR_ZONE2_CURRENT= "0000ffbb-0000-1000-8000-00805f9b34fb"
CHAR_ZONE3_CURRENT= "0000ffbc-0000-1000-8000-00805f9b34fb"
CHAR_ACTIVITY     = "0000ffbd-0000-1000-8000-00805f9b34fb"
CHAR_FAULT        = "0000ffc0-0000-1000-8000-00805f9b34fb"

ZONE_TARGET_CHARS = [CHAR_ZONE0_TARGET, CHAR_ZONE1_TARGET, CHAR_ZONE2_TARGET, CHAR_ZONE3_TARGET]
ZONE_DUTY_CHARS   = [CHAR_ZONE0_DUTY, CHAR_ZONE1_DUTY, CHAR_ZONE2_DUTY, CHAR_ZONE3_DUTY]
ZONE_CURRENT_CHARS= [CHAR_ZONE0_CURRENT, CHAR_ZONE1_CURRENT, CHAR_ZONE2_CURRENT, CHAR_ZONE3_CURRENT]

ACTIVITY_LABELS = {0: "STILL", 1: "WALKING", 2: "RUNNING", 3: "FALL"}
FAULT_LABELS = {
    0x01: "OVERCURRENT", 0x02: "OVERTEMP", 0x04: "THERM_OPEN",
    0x08: "THERM_SHORT", 0x10: "LOW_BATT", 0x20: "WATCHDOG", 0x40: "COMM_ERR",
}


async def read_float(client, uuid: str) -> float:
    data = await client.read_gatt_char(uuid)
    return struct.unpack('<f', data)[0]


async def read_uint8(client, uuid: str) -> int:
    data = await client.read_gatt_char(uuid)
    return struct.unpack('<B', data)[0]


async def read_uint16(client, uuid: str) -> int:
    data = await client.read_gatt_char(uuid)
    return struct.unpack('<H', data)[0]


def decode_faults(fault_byte: int) -> str:
    if fault_byte == 0:
        return "NONE"
    faults = []
    for bit, name in FAULT_LABELS.items():
        if fault_byte & bit:
            faults.append(name)
    return "|".join(faults)


async def log_data(mac: str, output_file: str, interval: float, duration: float):
    """Log data to CSV file."""

    fieldnames = [
        'timestamp', 'elapsed_s',
        'z0_target', 'z0_temp', 'z0_duty', 'z0_current',
        'z1_target', 'z1_temp', 'z1_duty', 'z1_current',
        'z2_target', 'z2_temp', 'z2_duty', 'z2_current',
        'z3_target', 'z3_temp', 'z3_duty', 'z3_current',
        'activity', 'faults'
    ]

    async with BleakClient(mac) as client:
        print(f"Connected to Therma Weave at {mac}")
        print(f"Logging to {output_file} every {interval}s for {duration}s")
        print(f"Press Ctrl+C to stop early.\n")

        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            start_time = time.time()
            row_count = 0

            try:
                while True:
                    elapsed = time.time() - start_time
                    if duration > 0 and elapsed >= duration:
                        break

                    # Read all zone data
                    row = {
                        'timestamp': datetime.now().isoformat(),
                        'elapsed_s': f'{elapsed:.1f}',
                    }

                    # Read targets, duty cycles, and currents for each zone
                    for z in range(4):
                        try:
                            row[f'z{z}_target'] = await read_uint8(client, ZONE_TARGET_CHARS[z])
                            row[f'z{z}_duty'] = await read_uint8(client, ZONE_DUTY_CHARS[z])
                            row[f'z{z}_current'] = await read_uint16(client, ZONE_CURRENT_CHARS[z])
                            # Temperature is in env service - use float
                            row[f'z{z}_temp'] = '0.0'  # Placeholder
                        except Exception as e:
                            row[f'z{z}_target'] = 'ERR'
                            row[f'z{z}_duty'] = 'ERR'
                            row[f'z{z}_current'] = 'ERR'
                            row[f'z{z}_temp'] = 'ERR'

                    # Activity level
                    try:
                        activity = await read_uint8(client, CHAR_ACTIVITY)
                        row['activity'] = ACTIVITY_LABELS.get(activity, f'UNKNOWN({activity})')
                    except Exception:
                        row['activity'] = 'ERR'

                    # Faults
                    try:
                        faults = await read_uint8(client, CHAR_FAULT)
                        row['faults'] = decode_faults(faults)
                    except Exception:
                        row['faults'] = 'ERR'

                    writer.writerow(row)
                    row_count += 1

                    # Print status line
                    temps = [row.get(f'z{z}_temp', '?') for z in range(4)]
                    duties = [row.get(f'z{z}_duty', '?') for z in range(4)]
                    print(f"[{elapsed:7.1f}s] "
                          f"Z0:{str(temps[0]):>6s}°C/{str(duties[0]):>3s}%  "
                          f"Z1:{str(temps[1]):>6s}°C/{str(duties[1]):>3s}%  "
                          f"Z2:{str(temps[2]):>6s}°C/{str(duties[2]):>3s}%  "
                          f"Z3:{str(temps[3]):>6s}°C/{str(duties[3]):>3s}%  "
                          f"Act:{row['activity']}  Faults:{row['faults']}")

                    await asyncio.sleep(interval)

            except KeyboardInterrupt:
                print(f"\nLogging stopped by user.")

            print(f"\nLogged {row_count} rows to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Therma Weave Data Logger")
    parser.add_argument("--mac", required=True, help="Device MAC address")
    parser.add_argument("--output", default="therma_weave_log.csv",
                        help="Output CSV file (default: therma_weave_log.csv)")
    parser.add_argument("--interval", type=float, default=2.0,
                        help="Logging interval in seconds (default: 2)")
    parser.add_argument("--duration", type=float, default=0,
                        help="Logging duration in seconds (0=infinite, default: 0)")

    args = parser.parse_args()
    asyncio.run(log_data(args.mac, args.output, args.interval, args.duration))


if __name__ == "__main__":
    main()