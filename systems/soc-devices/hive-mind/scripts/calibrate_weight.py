#!/usr/bin/env python3
"""
Hive Mind — Weight Sensor Calibration Tool
Interactive tool for calibrating the HX711 load cell via USB serial.

SPDX-License-Identifier: MIT
Copyright (c) 2026 jayis1

Usage:
    python3 calibrate_weight.py --port /dev/ttyUSB0

Commands:
    tare       - Zero the scale (remove all weight first)
    calibrate  - Calibrate with a known weight
    read       - Read current weight
    monitor    - Continuous weight reading
    save       - Save calibration to device flash
"""

import argparse
import serial
import time
import sys

def send_command(ser, cmd: str) -> str:
    """Send a command to the Hive Mind console and return the response."""
    ser.write((cmd + "\n").encode())
    time.sleep(0.1)
    response = ""
    while ser.in_waiting:
        response += ser.read(ser.in_waiting).decode(errors='replace')
        time.sleep(0.05)
    return response.strip()

def interactive_calibration(ser):
    """Run an interactive calibration session."""
    print("=" * 50)
    print("Hive Mind Weight Sensor Calibration")
    print("=" * 50)
    print()

    # Step 1: Tare
    print("Step 1: TARE")
    print("Remove all weight from the scale.")
    input("Press Enter when ready...")
    response = send_command(ser, "weight tare")
    print(f"Device: {response}")

    # Step 2: Read raw value to verify
    response = send_command(ser, "weight raw")
    print(f"Raw value (should be near 0): {response}")

    # Step 3: Place known weight
    known_weight = float(input("Enter the known weight in grams (e.g., 10000 for 10 kg): "))
    print(f"Place the {known_weight}g weight on the scale now.")
    input("Press Enter when the weight is stable...")

    # Step 4: Calibrate
    response = send_command(ser, f"weight calibrate {int(known_weight)}")
    print(f"Device: {response}")

    # Step 5: Verify
    time.sleep(1)
    response = send_command(ser, "weight read")
    print(f"Current reading: {response}")

    # Step 6: Save
    save = input("Calibration looks good? Save to flash? (y/n): ")
    if save.lower() == 'y':
        response = send_command(ser, "save")
        print(f"Device: {response}")
        print("Calibration saved!")
    else:
        print("Calibration NOT saved. It will be lost on reboot.")

def monitor_weight(ser, interval=1.0):
    """Continuously read and display weight."""
    print("Monitoring weight (Ctrl+C to stop)...")
    print("-" * 40)
    try:
        while True:
            response = send_command(ser, "weight read")
            print(f"\r{response:<40}", end="", flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

def main():
    parser = argparse.ArgumentParser(description="Hive Mind weight calibration tool")
    parser.add_argument("--port", required=True, help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--monitor", action="store_true", help="Continuous weight monitoring")
    args = parser.parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1.0)
        print(f"Connected to {args.port} at {args.baud} baud")

        # Wait for device to be ready
        time.sleep(0.5)
        ser.reset_input_buffer()

        # Check connection
        response = send_command(ser, "version")
        if "Hive Mind" not in response:
            print(f"Warning: Unexpected response: {response}")
        else:
            print(f"Device: {response}")
            print()

        if args.monitor:
            monitor_weight(ser)
        else:
            interactive_calibration(ser)

        ser.close()
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()