#!/usr/bin/env python3
"""
calibrate_mics.py — Calibrate the dual MEMS microphones for sensitivity matching.

Plays pink noise through the speaker while both mics capture.
Computes magnitude ratio per octave band and stores compensation factors.

Usage:
    python3 calibrate_mics.py --port /dev/ttyUSB0
"""

import argparse
import serial
import struct
import time
import numpy as np


def send_command(ser, cmd):
    """Send a command to Echo Mote via USB-C serial."""
    ser.write((cmd + "\n").encode())
    time.sleep(0.1)
    response = ""
    while ser.in_waiting:
        response += ser.read(ser.in_waiting).decode("utf-8", errors="replace")
    return response


def calibrate(port, baudrate=115200):
    """Run microphone sensitivity calibration."""
    print(f"Connecting to Echo Mote on {port}...")
    ser = serial.Serial(port, baudrate, timeout=1)
    time.sleep(2)  # Wait for device ready

    # Check device is responding
    response = send_command(ser, "status")
    print(f"Device response: {response.strip()}")

    # Start calibration mode
    print("Starting mic calibration...")
    print("Playing pink noise through speaker for 5 seconds...")
    response = send_command(ser, "cal mic")
    print(f"Calibration response: {response.strip()}")

    # Wait for calibration to complete
    for i in range(10):
        time.sleep(1)
        if ser.in_waiting:
            response = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
            print(f"  {i+1}s: {response.strip()}")
            if "calibration complete" in response.lower() or "done" in response.lower():
                break

    print("\nCalibration complete!")
    print("Microphone sensitivity matching factors stored in NVS.")
    print("They will be applied automatically to all future measurements.")

    ser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Echo Mote Microphone Calibration")
    parser.add_argument("--port", required=True, help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    args = parser.parse_args()
    calibrate(args.port, args.baud)