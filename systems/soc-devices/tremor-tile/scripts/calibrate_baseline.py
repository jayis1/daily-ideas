#!/usr/bin/env python3
"""
Tremor Tile — Baseline Calibration Tool
Connects to the Tremor Tile via USB-C (CDC) and manages baseline learning.

Usage:
    python3 calibrate_baseline.py --port /dev/ttyACM0

Requires:
    pip install pyserial
"""

import argparse
import struct
import sys
import time

try:
    import serial
except ImportError:
    print("Error: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

# Commands sent to the device (over USB CDC)
CMD_GET_STATUS = 0x01
CMD_START_LEARNING = 0x02
CMD_STOP_LEARNING = 0x03
CMD_RESET_BASELINE = 0x04
CMD_SET_THRESHOLD = 0x05
CMD_GET_BASELINE = 0x06
CMD_GET_SPECTRUM = 0x07


def send_command(ser, cmd, data=b""):
    """Send a command and read response."""
    packet = bytes([0xAA, 0x55, cmd, len(data)]) + data
    ser.write(packet)
    ser.flush()
    time.sleep(0.1)

    # Read response
    header = ser.read(4)
    if len(header) < 4:
        print("Error: No response from device")
        return None

    if header[0] != 0xAA or header[1] != 0x55:
        print(f"Error: Invalid response header: {header.hex()}")
        return None

    resp_cmd = header[2]
    resp_len = header[3]
    resp_data = ser.read(resp_len) if resp_len > 0 else b""

    return {"cmd": resp_cmd, "data": resp_data}


def get_status(ser):
    """Get current device status."""
    resp = send_command(ser, CMD_GET_STATUS)
    if resp and len(resp["data"]) >= 8:
        data = resp["data"]
        mode = data[0]  # 0=sleep, 1=monitor, 2=active, 3=mapping
        battery_pct = data[1]
        learning = data[2]  # 0=monitoring, 1=learning
        anomaly_state = data[3]  # 0=normal, 1=alert
        samples = struct.unpack('<I', data[4:8])[0]

        modes = {0: "SLEEP", 1: "MONITOR", 2: "ACTIVE", 3: "MAPPING"}
        print(f"Device Status:")
        print(f"  Mode: {modes.get(mode, 'UNKNOWN')}")
        print(f"  Battery: {battery_pct}%")
        print(f"  Learning: {'YES' if learning else 'NO'}")
        print(f"  Anomaly: {'ALERT!' if anomaly_state else 'Normal'}")
        print(f"  Baseline samples: {samples}")
        return True
    return False


def start_learning(ser):
    """Start baseline learning period."""
    print("Starting baseline learning (24 hours recommended)...")
    resp = send_command(ser, CMD_START_LEARNING)
    if resp:
        print("Learning started. Device will learn the normal vibration signature.")
        print("Keep the device in its final mounting position during learning.")
        return True
    return False


def reset_baseline(ser):
    """Reset the baseline and restart learning."""
    confirm = input("Are you sure you want to reset the baseline? [y/N]: ")
    if confirm.lower() != 'y':
        print("Cancelled.")
        return

    print("Resetting baseline...")
    resp = send_command(ser, CMD_RESET_BASELINE)
    if resp:
        print("Baseline reset. Device will start learning again.")
        return True
    return False


def set_threshold(ser, sigma):
    """Set the anomaly detection threshold (sigma multiplier)."""
    data = struct.pack('<f', sigma)
    resp = send_command(ser, CMD_SET_THRESHOLD, data)
    if resp:
        print(f"Threshold set to {sigma:.1f}σ")
        return True
    return False


def get_spectrum(ser):
    """Get current spectral features."""
    resp = send_command(ser, CMD_GET_SPECTRUM)
    if resp and len(resp["data"]) >= 24:
        data = resp["data"]
        rms = struct.unpack('<f', data[0:4])[0]
        crest = struct.unpack('<f', data[4:8])[0]
        kurtosis = struct.unpack('<f', data[8:12])[0]

        print(f"Current Spectral Features:")
        print(f"  RMS vibration: {rms:.6f} g")
        print(f"  Crest factor: {crest:.3f}")
        print(f"  Kurtosis: {kurtosis:.3f}")

        # Parse peak frequencies
        if len(data) >= 24 + 5 * 8:
            print(f"  Peak frequencies:")
            for i in range(5):
                offset = 24 + i * 8
                freq = struct.unpack('<f', data[offset:offset+4])[0]
                amp = struct.unpack('<f', data[offset+4:offset+8])[0]
                if freq > 0:
                    print(f"    {freq:.1f} Hz (amplitude: {amp:.6f})")
        return True
    return False


def interactive_mode(ser):
    """Interactive command loop."""
    print("\n=== Tremor Tile Calibration Tool ===")
    print("Commands:")
    print("  s - Get status")
    print("  l - Start learning")
    print("  r - Reset baseline")
    print("  t - Set threshold")
    print("  p - Print current spectrum")
    print("  q - Quit")
    print()

    while True:
        try:
            cmd = input("> ").strip().lower()
            if cmd == 's':
                get_status(ser)
            elif cmd == 'l':
                start_learning(ser)
            elif cmd == 'r':
                reset_baseline(ser)
            elif cmd == 't':
                try:
                    sigma = float(input("Enter threshold (sigma, e.g. 5.0): "))
                    set_threshold(ser, sigma)
                except ValueError:
                    print("Invalid threshold value.")
            elif cmd == 'p':
                get_spectrum(ser)
            elif cmd == 'q':
                break
            else:
                print("Unknown command.")
        except KeyboardInterrupt:
            break

    print("Goodbye!")


def main():
    parser = argparse.ArgumentParser(description="Tremor Tile Baseline Calibration")
    parser.add_argument("--port", default="/dev/ttyACM0",
                       help="Serial port (default: /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200,
                       help="Baud rate (default: 115200)")
    args = parser.parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=2.0)
        print(f"Connected to {args.port} at {args.baud} baud")
        time.sleep(1)  # Wait for device to be ready

        interactive_mode(ser)

        ser.close()
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        print("Make sure the device is connected and the port is correct.")
        sys.exit(1)


if __name__ == "__main__":
    main()