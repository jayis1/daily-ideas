#!/usr/bin/env python3
"""
Sap Watch — Zero-Flow Calibration Script

Connects to a Sap Watch device via the debug UART and runs the zero-flow
calibration procedure: collects predawn measurements, computes the offset,
and sends it to the device.

Usage:
    python calibration.py --port /dev/ttyUSB0 --samples 60
    python calibration.py --port /dev/ttyUSB0 --set-offset 0.003

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import re
import sys
import time

try:
    import serial
except ImportError:
    print("Install pyserial first: pip install pyserial", file=sys.stderr)
    sys.exit(1)


class Calibrator:
    def __init__(self, port: str, baud: int = 115200):
        self.ser = serial.Serial(port, baudrate=baud, timeout=5)

    def _send(self, line: str):
        self.ser.write((line + "\n").encode())
        self.ser.flush()

    def _read_until(self, pattern: str, timeout: float = 30.0) -> str:
        deadline = time.time() + timeout
        buf = ""
        while time.time() < deadline:
            if self.ser.in_waiting:
                buf += self.ser.read(self.ser.in_waiting).decode("utf-8", errors="replace")
                if re.search(pattern, buf):
                    return buf
            else:
                time.sleep(0.1)
        return buf

    def collect_measurements(self, n_samples: int):
        """Force n_samples measurements and extract V_h values."""
        print(f"Collecting {n_samples} predawn measurements...")
        print("Ensure this is run during predawn (02:00-05:00 local time)")
        print("when transpiration is zero.")
        print()

        v_h_values = []
        for i in range(n_samples):
            print(f"  [{i+1}/{n_samples}] Forcing measurement...", end=" ", flush=True)
            self._send("5")  # force measurement command
            output = self._read_until(r"V_h=([\d.\-]+) cm/s", timeout=35)
            match = re.search(r"V_h=([\d.\-]+) cm/s", output)
            if match:
                v_h = float(match.group(1))
                v_h_values.append(v_h)
                print(f"V_h = {v_h:.6f} cm/s")
            else:
                print("FAIL (no V_h in output)")
            time.sleep(1)

        if len(v_h_values) < n_samples // 2:
            print(f"\nERROR: Only got {len(v_h_values)} valid measurements "
                  f"(need at least {n_samples // 2})")
            return None

        avg = sum(v_h_values) / len(v_h_values)
        print(f"\nCollected {len(v_h_values)} measurements:")
        print(f"  Mean V_h: {avg:.6f} cm/s")
        print(f"  Min:  {min(v_h_values):.6f} cm/s")
        print(f"  Max:  {max(v_h_values):.6f} cm/s")
        print(f"  Std:  {(sum((v - avg) ** 2 for v in v_h_values) / len(v_h_values)) ** 0.5:.6f} cm/s")
        return avg

    def set_offset(self, offset: float):
        """Send the zero-flow offset to the device via serial."""
        print(f"Setting zero-flow offset to {offset:.6f} cm/s...")
        self._send(f"set_zero_offset {offset:.6f}")
        output = self._read_until(r"zero_flow_offset = ([\d.\-]+)", timeout=5)
        match = re.search(r"zero_flow_offset = ([\d.\-]+)", output)
        if match:
            stored = float(match.group(1))
            if abs(stored - offset) < 1e-6:
                print(f"PASS (offset stored: {stored:.6f})")
                return True
            else:
                print(f"FAIL (stored {stored}, expected {offset})")
                return False
        print("FAIL (no confirmation)")
        return False

    def close(self):
        self.ser.close()


def main():
    parser = argparse.ArgumentParser(description="Sap Watch zero-flow calibration")
    parser.add_argument("--port", required=True, help="Serial port")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--samples", type=int, default=60,
                        help="Number of measurements to collect (default: 60)")
    parser.add_argument("--set-offset", type=float,
                        help="Directly set the offset (skip collection)")
    args = parser.parse_args()

    cal = Calibrator(args.port, args.baud)

    if args.set_offset is not None:
        cal.set_offset(args.set_offset)
    else:
        offset = cal.collect_measurements(args.samples)
        if offset is not None:
            if abs(offset) > 0.05:
                print(f"\nWARNING: Offset {offset:.6f} is large (>0.05).")
                print("This may indicate poor probe installation.")
                print("Check needle spacing and depth before proceeding.")
            cal.set_offset(offset)

    cal.close()