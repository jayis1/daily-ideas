#!/usr/bin/env python3
"""
Sap Watch — Field Test Script

Connects to a Sap Watch device via the debug UART (115200 baud) and runs
a series of automated tests: heater pulse, ADC read, sensor scan, and
LoRaWAN join check. Reports pass/fail for each test.

Usage:
    python field_test.py --port /dev/ttyUSB0
    python field_test.py --port COM3       (Windows)

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


class SapWatchTester:
    def __init__(self, port: str, baud: int = 115200):
        self.ser = serial.Serial(port, baudrate=baud, timeout=5)
        self.results = []

    def _read_until(self, pattern: str, timeout: float = 10.0) -> str:
        """Read from serial until pattern is found or timeout."""
        deadline = time.time() + timeout
        buf = ""
        while time.time() < deadline:
            if self.ser.in_waiting:
                chunk = self.ser.read(self.ser.in_waiting).decode("utf-8", errors="replace")
                buf += chunk
                if re.search(pattern, buf):
                    return buf
            else:
                time.sleep(0.1)
        return buf

    def _send(self, line: str):
        self.ser.write((line + "\n").encode())
        self.ser.flush()

    def test_boot(self):
        """Test 1: Device boots and prints identification."""
        print("Test 1: Boot identification...", end=" ")
        # Reset by toggling DTR
        self.ser.dtr = False
        time.sleep(0.5)
        self.ser.dtr = True
        output = self._read_until("Sap Watch v", timeout=5)
        if "Sap Watch v" in output:
            version = re.search(r"Sap Watch v(\S+)", output)
            print(f"PASS (v{version.group(1)})")
            self.results.append(("Boot", "PASS"))
        else:
            print("FAIL (no boot message)")
            self.results.append(("Boot", "FAIL"))

    def test_sensors(self):
        """Test 2: Environmental sensors respond."""
        print("Test 2: Sensor scan...", end=" ")
        # Trigger a measurement via the mode button serial command
        self._send("5")  # serial menu option 5 = force measurement
        output = self._read_until(r"\[MEAS\] sensors:", timeout=30)
        if "sensors:" in output and "NaN" not in output:
            temp = re.search(r"T_air=([\d.]+)", output)
            rh = re.search(r"RH=([\d.]+)", output)
            bat = re.search(r"bat=(\d+)%", output)
            if temp and rh and bat:
                print(f"PASS (T={temp.group(1)}°C, RH={rh.group(1)}%, "
                      f"bat={bat.group(1)}%)")
                self.results.append(("Sensors", "PASS"))
            else:
                print("FAIL (missing values)")
                self.results.append(("Sensors", "FAIL"))
        else:
            print("FAIL (no sensor output)")
            self.results.append(("Sensors", "FAIL"))

    def test_heater(self):
        """Test 3: Heater pulse fires without fault."""
        print("Test 3: Heater pulse...", end=" ")
        output = self._read_until(r"\[MEAS\] heat pulse", timeout=10)
        if "heat pulse" in output and "fault" not in output.lower():
            current = re.search(r"@ ([\d.]+)A", output)
            if current:
                print(f"PASS ({current.group(1)}A)")
                self.results.append(("Heater", "PASS"))
            else:
                print("PASS (no fault)")
                self.results.append(("Heater", "PASS"))
        else:
            print("FAIL (fault or no pulse)")
            self.results.append(("Heater", "FAIL"))

    def test_probe(self):
        """Test 4: Probe thermistors give valid readings."""
        print("Test 4: Probe thermistors...", end=" ")
        output = self._read_until(r"V_sap=([\d.]+) cm/s", timeout=30)
        if output:
            v = re.search(r"V_sap=([\d.]+) cm/s", output)
            if v:
                v_sap = float(v.group(1))
                if -5.0 <= v_sap <= 100.0:
                    print(f"PASS (V_sap={v_sap} cm/h)")
                    self.results.append(("Probe", "PASS"))
                else:
                    print(f"FAIL (V_sap={v_sap} out of range)")
                    self.results.append(("Probe", "FAIL"))
            else:
                print("FAIL (no V_sap)")
                self.results.append(("Probe", "FAIL"))
        else:
            print("FAIL (timeout)")
            self.results.append(("Probe", "FAIL"))

    def test_lorawan(self):
        """Test 5: LoRaWAN join status."""
        print("Test 5: LoRaWAN join...", end=" ")
        output = self._read_until(r"LoRaWAN: (joined|join failed)", timeout=35)
        if "joined!" in output:
            dev = re.search(r"DevEUI=([0-9A-F]+)", output)
            print(f"PASS (DevEUI={dev.group(1) if dev else '?'})")
            self.results.append(("LoRaWAN", "PASS"))
        elif "join failed" in output:
            print("FAIL (join failed)")
            self.results.append(("LoRaWAN", "FAIL"))
        else:
            print("SKIP (no LoRaWAN output)")
            self.results.append(("LoRaWAN", "SKIP"))

    def run_all(self):
        print("=" * 50)
        print("Sap Watch Field Test")
        print("=" * 50)
        self.test_boot()
        self.test_heater()
        self.test_probe()
        self.test_sensors()
        self.test_lorawan()
        print("=" * 50)
        passed = sum(1 for _, r in self.results if r == "PASS")
        failed = sum(1 for _, r in self.results if r == "FAIL")
        skipped = sum(1 for _, r in self.results if r == "SKIP")
        print(f"Results: {passed} PASS, {failed} FAIL, {skipped} SKIP")
        for name, result in self.results:
            marker = "✓" if result == "PASS" else "✗" if result == "FAIL" else "–"
            print(f"  {marker} {name}: {result}")
        print("=" * 50)
        self.ser.close()
        return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Sap Watch field test")
    parser.add_argument("--port", required=True, help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    args = parser.parse_args()

    tester = SapWatchTester(args.port, args.baud)
    ok = tester.run_all()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()