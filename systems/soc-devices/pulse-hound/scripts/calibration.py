#!/usr/bin/env python3
"""
Pulse Hound — AD8318 RSSI Calibration Tool
Connect to the Pulse Hound over USB-serial, run calibration procedures.

Usage:
    python3 calibration.py --port /dev/ttyACM0 --noise-floor
    python3 calibration.py --port /dev/ttyACM0 --calibrate --freq 2400 --power -30
    python3 calibration.py --port /dev/ttyACM0 --multipoint --points "-60,-50,-40,-30,-20,-10"
    python3 calibration.py --port /dev/ttyACM0 --read
"""

import argparse
import serial
import time
import struct
import sys
import json


class PulseHoundCal:
    def __init__(self, port, baud=115200):
        self.ser = serial.Serial(port, baud, timeout=2.0)
        time.sleep(1)  # wait for boot
        self._flush()

    def _flush(self):
        while self.ser.in_waiting:
            self.ser.read(self.ser.in_waiting)

    def _send(self, cmd):
        self._flush()
        self.ser.write((cmd + "\n").encode())
        time.sleep(0.1)

    def _readline(self):
        line = b""
        while True:
            ch = self.ser.read(1)
            if ch == b"" or ch == b"\n":
                break
            line += ch
        return line.decode(errors="replace")

    def _read_response(self, timeout=5.0):
        lines = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.ser.in_waiting:
                line = self._readline()
                if line:
                    lines.append(line)
                    if "OK" in line or "ERROR" in line or "done" in line.lower():
                        break
            else:
                time.sleep(0.05)
        return lines

    def read_calibration(self):
        """Read current calibration values from the device."""
        self._send("cal read")
        lines = self._read_response()
        for line in lines:
            print(line)
        return lines

    def noise_floor(self):
        """Measure noise floor with no antenna / terminated input."""
        print("Measuring noise floor (10 seconds, no signal)...")
        self._send("cal noise_floor")
        lines = self._read_response(timeout=15)
        for line in lines:
            print(line)
        print("Noise floor measurement complete.")

    def calibrate_single(self, freq_mhz, power_dbm):
        """Single-point calibration with known signal."""
        print(f"Calibrating at {freq_mhz} MHz, {power_dbm} dBm...")
        cmd = f"cal set {freq_mhz} {power_dbm}"
        self._send(cmd)
        lines = self._read_response(timeout=10)
        for line in lines:
            print(line)
        print("Single-point calibration complete.")

    def calibrate_multipoint(self, power_points):
        """Multi-point calibration with linear regression."""
        print(f"Multi-point calibration at power levels: {power_points}")
        # The device reads VOUT at each power level (signal generator must be set manually)
        results = []
        for p in power_points:
            print(f"\n  Set signal generator to {p} dBm, then press Enter...")
            input()
            self._send(f"cal sample {p}")
            lines = self._read_response(timeout=5)
            for line in lines:
                print(f"    {line}")
                if "VOUT" in line:
                    try:
                        vout = float(line.split("=")[1].strip().replace("V", ""))
                        results.append((p, vout))
                    except (ValueError, IndexError):
                        pass

        if len(results) >= 2:
            # Linear regression: power = (VOUT - intercept) / slope
            import numpy as np
            powers = np.array([r[0] for r in results])
            vouts = np.array([r[1] for r in results])
            # VOUT = intercept + slope * power  →  slope = dVOUT/dpower
            coeffs = np.polyfit(powers, vouts, 1)
            slope = coeffs[0] * 1000  # mV/dB
            intercept = coeffs[1]    # V

            print(f"\n  Linear fit: slope={slope:.1f} mV/dB, intercept={intercept:.3f} V")
            print(f"  R² = {np.corrcoef(powers, vouts)[0,1]**2:.4f}")

            self._send(f"cal store {slope:.2f} {intercept:.4f}")
            lines = self._read_response(timeout=5)
            for line in lines:
                print(f"    {line}")
            print("Multi-point calibration stored to NVS.")

    def temp_sweep(self):
        """Monitor RSSI over temperature for temp coefficient calculation."""
        print("Temperature sweep (60 seconds)...")
        self._send("cal temp_sweep")
        lines = self._read_response(timeout=70)
        for line in lines:
            print(line)
        print("Temperature sweep complete.")


def main():
    parser = argparse.ArgumentParser(description="Pulse Hound AD8318 Calibration")
    parser.add_argument("--port", required=True, help="Serial port (e.g., /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--noise-floor", action="store_true", help="Measure noise floor")
    parser.add_argument("--calibrate", action="store_true", help="Single-point calibration")
    parser.add_argument("--freq", type=float, default=2400, help="Calibration frequency (MHz)")
    parser.add_argument("--power", type=float, default=-30, help="Calibration power (dBm)")
    parser.add_argument("--multipoint", action="store_true", help="Multi-point calibration")
    parser.add_argument("--points", default="-60,-50,-40,-30,-20,-10",
                        help="Comma-separated power levels for multipoint")
    parser.add_argument("--temp-sweep", action="store_true", help="Temperature coefficient sweep")
    parser.add_argument("--read", action="store_true", help="Read current calibration")
    args = parser.parse_args()

    try:
        cal = PulseHoundCal(args.port, args.baud)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)

    if args.read:
        cal.read_calibration()
    elif args.noise_floor:
        cal.noise_floor()
    elif args.calibrate:
        cal.calibrate_single(args.freq, args.power)
    elif args.multipoint:
        points = [float(p) for p in args.points.split(",")]
        cal.calibrate_multipoint(points)
    elif args.temp_sweep:
        cal.temp_sweep()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()