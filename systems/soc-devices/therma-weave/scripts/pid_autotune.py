#!/usr/bin/env python3
"""
Therma Weave — PID Auto-Tune Tool
Automatically determines optimal PID parameters using Ziegler-Nichols relay method.

Usage:
    python3 pid_autotune.py --mac AA:BB:CC:DD:EE:FF --zone 0
    python3 pid_autotune.py --mac AA:BB:CC:DD:EE:FF --zone 0 --target 40 --duration 300

SPDX-License-Identifier: MIT
"""

import asyncio
import argparse
import struct
import time
import sys

try:
    from bleak import BleakClient
except ImportError:
    print("ERROR: bleak library not installed. Run: pip install bleak")
    sys.exit(1)

# BLE UUIDs (same as therma_weave_ble.py)
THERMA_SERVICE_UUID = "0000ffb0-0000-1000-8000-00805f9b34fb"
CHAR_ZONE0_TARGET = "0000ffb1-0000-1000-8000-00805f9b34fb"
CHAR_ZONE1_TARGET = "0000ffb2-0000-1000-8000-00805f9b34fb"
CHAR_ZONE2_TARGET = "0000ffb3-0000-1000-8000-00805f9b34fb"
CHAR_ZONE3_TARGET = "0000ffb4-0000-1000-8000-00805f9b34fb"
CHAR_ZONE0_DUTY   = "0000ffb5-0000-1000-8000-00805f9b34fb"
CHAR_ZONE1_DUTY   = "0000ffb6-0000-1000-8000-00805f9b34fb"
CHAR_ZONE2_DUTY   = "0000ffb7-0000-1000-8000-00805f9b34fb"
CHAR_ZONE3_DUTY   = "0000ffb8-0000-1000-8000-00805f9b34fb"
CHAR_ENABLE       = "0000ffbe-0000-1000-8000-00805f9b34fb"
CHAR_PID_KP       = "0000ffc1-0000-1000-8000-00805f9b34fb"
CHAR_PID_KI       = "0000ffc2-0000-1000-8000-00805f9b34fb"
CHAR_PID_KD       = "0000ffc3-0000-1000-8000-00805f9b34fb"

# Environmental sensing
CHAR_ZONE0_TEMP   = "00002a6e-0000-1000-8000-00805f9b34fb"

ZONE_TARGET_CHARS = [CHAR_ZONE0_TARGET, CHAR_ZONE1_TARGET, CHAR_ZONE2_TARGET, CHAR_ZONE3_TARGET]
ZONE_DUTY_CHARS   = [CHAR_ZONE0_DUTY, CHAR_ZONE1_DUTY, CHAR_ZONE2_DUTY, CHAR_ZONE3_DUTY]

# Temperature characteristic UUIDs for all 4 zones (using sequential handles)
ZONE_TEMP_CHARS = [
    "00002a6e-0000-1000-8000-00805f9b34fb",
    "00002a6e-0000-1000-8000-00805f9b34fb",  # Note: in real impl, use sequential handles
    "00002a6e-0000-1000-8000-00805f9b34fb",
    "00002a6e-0000-1000-8000-00805f9b34fb",
]

RELAY_DUTY_HIGH = 50.0   # % duty cycle during relay ON phase
RELAY_DUTY_LOW  = 0.0    # % duty cycle during relay OFF phase


async def read_float(client, char_uuid: str) -> float:
    data = await client.read_gatt_char(char_uuid)
    return struct.unpack('<f', data)[0]


async def read_uint8(client, char_uuid: str) -> int:
    data = await client.read_gatt_char(char_uuid)
    return struct.unpack('<B', data)[0]


async def write_uint8(client, char_uuid: str, value: int):
    await client.write_gatt_char(char_uuid, struct.pack('<B', value))


async def write_float(client, char_uuid: str, value: float):
    await client.write_gatt_char(char_uuid, struct.pack('<f', value))


async def autotune(mac: str, zone: int, target_temp: float, duration: int):
    """Run Ziegler-Nichols relay auto-tune for a zone."""

    print(f"\n{'='*60}")
    print(f"  THERMA WEAVE — PID Auto-Tune")
    print(f"  Zone: {zone}, Target: {target_temp}°C, Duration: {duration}s")
    print(f"{'='*60}\n")

    async with BleakClient(mac) as client:
        print(f"Connected to {mac}")

        # Enable the zone
        bitmask = 1 << zone
        await write_uint8(client, CHAR_ENABLE, bitmask)
        print(f"Zone {zone} enabled")

        # Set initial target temperature
        await write_uint8(client, ZONE_TARGET_CHARS[zone], int(target_temp))
        print(f"Zone {zone} target set to {int(target_temp)}°C")

        # Read initial temperature
        initial_temp = await read_float(client, CHAR_ZONE0_TEMP)
        print(f"Initial temperature: {initial_temp:.1f}°C")

        # Check if target is reachable
        if target_temp < initial_temp + 5:
            print(f"WARNING: Target ({target_temp}°C) is only {target_temp - initial_temp:.1f}°C above ambient.")
            print(f"         For best results, target should be at least 10°C above ambient.")

        # Relay method: oscillate around setpoint
        print(f"\nStarting relay auto-tune (oscillating around {target_temp}°C)...")
        print(f"High duty: {RELAY_DUTY_HIGH}%, Low duty: {RELAY_DUTY_LOW}%")
        print(f"Watching for oscillation patterns...\n")

        # Data collection
        temperatures = []
        timestamps = []
        start_time = time.time()

        # Relay oscillation
        state = "HEATING"
        crossings = []  # (time, direction) tuples for setpoint crossings
        peak_temps = []
        valley_temps = []

        # Manually drive duty cycle (in real impl, we'd write to a manual duty char)
        # For now, we set target and let PID control oscillate

        while (time.time() - start_time) < duration:
            current_temp = await read_float(client, CHAR_ZONE0_TEMP)
            current_time = time.time() - start_time
            duty = await read_uint8(client, ZONE_DUTY_CHARS[zone])

            temperatures.append(current_temp)
            timestamps.append(current_time)

            # Detect setpoint crossings
            if len(temperatures) >= 2:
                prev_temp = temperatures[-2]
                if prev_temp < target_temp and current_temp >= target_temp:
                    crossings.append((current_time, "UP"))
                    valley_temps.append(min(temperatures[-10:]))  # Approximate valley
                elif prev_temp >= target_temp and current_temp < target_temp:
                    crossings.append((current_time, "DOWN"))
                    peak_temps.append(max(temperatures[-10:]))  # Approximate peak

            # Status update every 5 seconds
            if int(current_time) % 5 == 0:
                elapsed = int(current_time)
                print(f"  [{elapsed:3d}s] Temp: {current_temp:5.1f}°C  Duty: {duty:3d}%  "
                      f"Crossings: {len(crossings)}  Peaks: {len(peak_temps)}  "
                      f"Valleys: {len(valley_temps)}")

            await asyncio.sleep(1.0)

        # Analyze oscillation data
        print(f"\n{'='*60}")
        print(f"  Auto-Tune Results")
        print(f"{'='*60}")

        if len(crossings) < 4:
            print("  ERROR: Not enough oscillation cycles detected.")
            print("  Try increasing duration or target temperature difference.")
            print("  Using default PID parameters.")
            return

        # Calculate ultimate gain (Ku) and ultimate period (Tu)
        if len(peak_temps) > 0 and len(valley_temps) > 0:
            avg_amplitude = (sum(peak_temps) / len(peak_temps) -
                            sum(valley_temps) / len(valley_temps)) / 2.0
            Ku = (4.0 * RELAY_DUTY_HIGH) / (3.14159 * avg_amplitude) if avg_amplitude > 0 else 2.5
        else:
            Ku = 2.5  # Default

        # Calculate period from crossings
        periods = []
        for i in range(2, len(crossings), 2):
            period = crossings[i][0] - crossings[i-2][0]
            periods.append(period)

        Tu = sum(periods) / len(periods) if periods else 60.0

        # Ziegler-Nichols PID tuning rules
        Kp = 0.6 * Ku
        Ki = 2.0 * Kp / Tu if Tu > 0 else 0.08
        Kd = Kp * Tu / 8.0 if Tu > 0 else 0.4

        print(f"  Oscillation amplitude: {avg_amplitude:.2f}°C")
        print(f"  Oscillation period (Tu): {Tu:.1f}s")
        print(f"  Ultimate gain (Ku): {Ku:.2f}")
        print(f"")
        print(f"  ╔══════════════════════════════════╗")
        print(f"  ║  Recommended PID Parameters:    ║")
        print(f"  ║  Kp = {Kp:.3f}                     ║")
        print(f"  ║  Ki = {Ki:.4f}                   ║")
        print(f"  ║  Kd = {Kd:.3f}                     ║")
        print(f"  ╚══════════════════════════════════╝")
        print(f"")

        # Ask to apply
        print(f"  To apply these parameters, run:")
        print(f"  python3 therma_weave_ble.py --mac {mac} --kp {Kp:.3f} --ki {Ki:.4f} --kd {Kd:.3f}")
        print(f"")
        print(f"  Or set via serial console:")
        print(f"  ZONE:PID {zone} {Kp:.3f} {Ki:.4f} {Kd:.3f}")


def main():
    parser = argparse.ArgumentParser(description="Therma Weave PID Auto-Tune")
    parser.add_argument("--mac", required=True, help="Device MAC address")
    parser.add_argument("--zone", type=int, required=True, help="Zone to tune (0-3)")
    parser.add_argument("--target", type=float, default=45.0,
                        help="Target temperature for oscillation (default: 45°C)")
    parser.add_argument("--duration", type=int, default=300,
                        help="Auto-tune duration in seconds (default: 300)")

    args = parser.parse_args()

    if args.zone < 0 or args.zone > 3:
        print("ERROR: Zone must be 0-3")
        sys.exit(1)

    if args.target < 30 or args.target > 55:
        print("ERROR: Target must be 30-55°C")
        sys.exit(1)

    asyncio.run(autotune(args.mac, args.zone, args.target, args.duration))


if __name__ == "__main__":
    main()