#!/usr/bin/env python3
"""
Brew Sense Calibration Tool

Performs air/water densitometer calibration and pH probe calibration
via serial connection to the Brew Sense device.
"""

import argparse
import serial
import time
import sys


def open_port(port, baudrate=115200, timeout=2):
    """Open serial port to Brew Sense device."""
    try:
        ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        print(f"Connected to Brew Sense on {port}")
        return ser
    except serial.SerialException as e:
        print(f"Error opening {port}: {e}")
        sys.exit(1)


def send_command(ser, command, wait=1.0):
    """Send a serial command and read the response."""
    ser.write((command + "\r\n").encode())
    time.sleep(wait)
    response = ser.read(ser.in_waiting).decode(errors="replace")
    return response.strip()


def calibrate_air(ser):
    """Perform air calibration for the densitometer."""
    print("\n=== DENSITOMETER AIR CALIBRATION ===")
    print("Hold the vibrating tube in AIR (not submerged in any liquid).")
    print("Make sure the tube is dry and at room temperature.")
    input("Press Enter when ready...")
    
    response = send_command(ser, "CALS,air", wait=3.0)
    print(f"Device response: {response}")
    
    # Parse response: CAL:AIR,f=4250.3
    if "CAL:AIR" in response:
        parts = response.split(",")
        if len(parts) >= 2:
            freq_str = parts[1].strip()
            print(f"✓ Air calibration successful! Resonant frequency: {freq_str} Hz")
            return True
    
    print("✗ Air calibration may have failed. Check device response.")
    return False


def calibrate_water(ser, temp=None):
    """Perform water calibration for the densitometer."""
    print("\n=== DENSITOMETER WATER CALIBRATION ===")
    print("Submerge the vibrating tube in DISTILLED WATER.")
    print("Ensure the water is at a known, stable temperature.")
    
    if temp is None:
        temp = float(input("Enter water temperature in °C (default 20.0): ") or "20.0")
    
    print(f"Water temperature: {temp}°C")
    input("Press Enter when the tube is submerged and settled (wait 30s)...")
    
    response = send_command(ser, "CALS,water", wait=3.0)
    print(f"Device response: {response}")
    
    if "CAL:WATER" in response:
        parts = response.split(",")
        if len(parts) >= 2:
            freq_str = parts[1].strip()
            print(f"✓ Water calibration successful! Resonant frequency: {freq_str} Hz")
            return True
    
    print("✗ Water calibration may have failed. Check device response.")
    return False


def calibrate_ph4(ser):
    """Calibrate pH probe with pH 4.0 buffer."""
    print("\n=== pH 4.0 BUFFER CALIBRATION ===")
    print("Place the pH probe in pH 4.0 buffer solution.")
    input("Press Enter when ready...")
    
    response = send_command(ser, "PH4", wait=2.0)
    print(f"Device response: {response}")
    
    if "PH:CAL4" in response and "OK" in response:
        print("✓ pH 4.0 calibration successful!")
        return True
    
    print("✗ pH 4.0 calibration may have failed.")
    return False


def calibrate_ph7(ser):
    """Calibrate pH probe with pH 7.0 buffer."""
    print("\n=== pH 7.0 BUFFER CALIBRATION ===")
    print("Rinse the pH probe and place it in pH 7.0 buffer solution.")
    input("Press Enter when ready...")
    
    response = send_command(ser, "PH7", wait=2.0)
    print(f"Device response: {response}")
    
    if "PH:CAL7" in response and "OK" in response:
        print("✓ pH 7.0 calibration successful!")
        return True
    
    print("✗ pH 7.0 calibration may have failed.")
    return False


def read_calibration(ser):
    """Read current calibration data from device."""
    print("\n=== CURRENT CALIBRATION DATA ===")
    response = send_command(ser, "CALR", wait=1.0)
    print(f"Device response: {response}")
    return response


def erase_calibration(ser):
    """Erase all calibration data (factory reset)."""
    print("\n=== ERASE CALIBRATION ===")
    print("WARNING: This will erase ALL calibration data!")
    confirm = input("Type 'YES' to confirm: ")
    if confirm != "YES":
        print("Cancelled.")
        return
    
    response = send_command(ser, "CALZ", wait=1.0)
    print(f"Device response: {response}")
    
    if "ERASED" in response:
        print("✓ Calibration data erased successfully.")
    else:
        print("✗ Erase may have failed.")


def read_sensors(ser):
    """Read current sensor values."""
    print("\n=== CURRENT SENSOR READINGS ===")
    response = send_command(ser, "READ", wait=2.0)
    print(f"Device response: {response}")
    return response


def main():
    parser = argparse.ArgumentParser(description="Brew Sense Calibration Tool")
    parser.add_argument("--port", "-p", default="/dev/ttyUSB0",
                       help="Serial port (default: /dev/ttyUSB0)")
    parser.add_argument("--baudrate", "-b", type=int, default=115200,
                       help="Baud rate (default: 115200)")
    parser.add_argument("--air", action="store_true",
                       help="Perform air calibration")
    parser.add_argument("--water", action="store_true",
                       help="Perform water calibration")
    parser.add_argument("--temp", type=float, default=20.0,
                       help="Water temperature for calibration (default: 20.0°C)")
    parser.add_argument("--ph4", action="store_true",
                       help="Calibrate pH at 4.0")
    parser.add_argument("--ph7", action="store_true",
                       help="Calibrate pH at 7.0")
    parser.add_argument("--read", action="store_true",
                       help="Read current calibration data")
    parser.add_argument("--erase", action="store_true",
                       help="Erase all calibration data")
    parser.add_argument("--all", action="store_true",
                       help="Run full calibration sequence (air + water + pH4 + pH7)")
    parser.add_argument("--sensors", action="store_true",
                       help="Read current sensor values")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Interactive mode")
    
    args = parser.parse_args()
    
    ser = open_port(args.port, args.baudrate)
    
    # Wait for device to be ready
    time.sleep(0.5)
    
    # Clear any pending data
    ser.reset_input_buffer()
    
    # Check device is responding
    response = send_command(ser, "INFO", wait=1.0)
    print(f"Device: {response}")
    
    success = True
    
    if args.all:
        print("\n" + "="*50)
        print("  BREW SENSE FULL CALIBRATION")
        print("="*50)
        success &= calibrate_air(ser)
        success &= calibrate_water(ser, args.temp)
        success &= calibrate_ph4(ser)
        success &= calibrate_ph7(ser)
        if success:
            print("\n✓ All calibrations completed successfully!")
            read_calibration(ser)
        else:
            print("\n✗ Some calibrations failed. Please retry.")
    
    if args.air:
        success &= calibrate_air(ser)
    
    if args.water:
        success &= calibrate_water(ser, args.temp)
    
    if args.ph4:
        success &= calibrate_ph4(ser)
    
    if args.ph7:
        success &= calibrate_ph7(ser)
    
    if args.read:
        read_calibration(ser)
    
    if args.erase:
        erase_calibration(ser)
    
    if args.sensors:
        read_sensors(ser)
    
    if args.interactive:
        print("\n=== INTERACTIVE MODE ===")
        print("Commands: air, water, ph4, ph7, read, erase, sensors, help, quit")
        while True:
            try:
                cmd = input("\n> ").strip().lower()
                if cmd == "quit" or cmd == "exit":
                    break
                elif cmd == "air":
                    calibrate_air(ser)
                elif cmd == "water":
                    calibrate_water(ser)
                elif cmd == "ph4":
                    calibrate_ph4(ser)
                elif cmd == "ph7":
                    calibrate_ph7(ser)
                elif cmd == "read":
                    read_calibration(ser)
                elif cmd == "erase":
                    erase_calibration(ser)
                elif cmd == "sensors":
                    read_sensors(ser)
                elif cmd == "help":
                    print("Commands: air, water, ph4, ph7, read, erase, sensors, help, quit")
                else:
                    # Send raw command
                    response = send_command(ser, cmd)
                    print(response)
            except KeyboardInterrupt:
                break
    
    ser.close()
    print("\nDone.")


if __name__ == "__main__":
    main()