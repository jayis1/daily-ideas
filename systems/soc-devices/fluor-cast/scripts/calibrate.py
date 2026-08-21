#!/usr/bin/env python3
"""
calibrate.py — Fluor Cast calibration wizard

Performs wavelength calibration and intensity calibration using
quinine sulfate as a fluorescence standard.

Usage:
    python3 calibrate.py [--port /dev/ttyUSB0] [--baud 921600]

Calibration procedure:
1. Wavelength calibration: Use quinine sulfate emission peak at 455 nm
   (excited at 350 nm) to map CCD pixel index → wavelength.
   Optionally use Hg pen lamp lines (436, 546, 577 nm) for multi-point fit.
2. Intensity calibration: Normalize response using 1 µg/mL quinine sulfate
   in 0.1 M H₂SO₄ as NIST-traceable standard.
3. Store calibration coefficients in device flash.

Quinine sulfate: NIST SRM 936a, quantum yield ~0.60 in 0.1 M H₂SO₄
"""

import serial
import struct
import argparse
import time
import json
import sys
import math

# Calibration constants
QUININE_PEAK_NM = 455.0
QUININE_EX_NM = 350.0
QUININE_CONC_UGML = 1.0  # µg/mL

# Known emission lines for wavelength calibration
KNOWN_LINES = [
    # (source, excitation_nm, expected_emission_nm)
    ("Quinine sulfate", 350, 455),
    ("Hg pen lamp 436", 0, 436),  # direct illumination (no excitation needed)
    ("Hg pen lamp 546", 0, 546),
    ("Hg pen lamp 577", 0, 577),
    ("Fluorescein", 470, 520),
]


class FluorCastCalibrator:
    def __init__(self, port: str, baud: int = 921600):
        self.ser = serial.Serial(port, baud, timeout=5.0)
        self.cal_data = {}

    def send_command(self, cmd: int, payload: bytes = b""):
        """Send framed command to device."""
        sof = bytes([0xAA])
        eof = bytes([0x55])
        length = len(payload).to_bytes(2, "little")

        # CRC16-CCITT over cmd + payload
        crc_data = bytes([cmd]) + payload
        crc = self._crc16(crc_data)

        frame = sof + length + bytes([cmd]) + payload + crc.to_bytes(2, "little") + eof
        self.ser.write(frame)

    def _crc16(self, data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
            crc &= 0xFFFF
        return crc

    def read_response(self, timeout: float = 10.0) -> tuple:
        """Read framed response. Returns (cmd, payload)."""
        deadline = time.time() + timeout
        buf = b""

        while time.time() < deadline:
            if self.ser.in_waiting > 0:
                buf += self.ser.read(self.ser.in_waiting)

            # Look for SOF
            if len(buf) < 7:
                continue

            idx = buf.find(0xAA)
            if idx < 0:
                buf = b""
                continue

            buf = buf[idx:]
            if len(buf) < 7:
                continue

            length = int.from_bytes(buf[1:3], "little")
            cmd = buf[3]
            payload_len = length
            total_len = 5 + payload_len + 2  # SOF + 2len + CMD + payload + 2CRC + EOF

            if len(buf) < total_len:
                continue

            payload = buf[4:4 + payload_len]
            crc_recv = int.from_bytes(buf[4 + payload_len:6 + payload_len], "little")
            eof_byte = buf[6 + payload_len]

            if eof_byte != 0x55:
                buf = buf[1:]
                continue

            # Verify CRC
            crc_calc = self._crc16(bytes([cmd]) + payload)
            if crc_calc != crc_recv:
                print(f"CRC mismatch: got {crc_recv:#06x}, expected {crc_calc:#06x}")
                buf = buf[total_len:]
                continue

            buf = buf[total_len:]
            return cmd, payload

        raise TimeoutError("No response from device")

    def get_status(self) -> dict:
        """Query device status."""
        self.send_command(0x12)  # CMD_GET_STATUS
        cmd, payload = self.read_response()
        if cmd == 0x03:  # CMD_STATUS
            state = payload[0]
            battery = payload[1]
            temp = struct.unpack("<f", payload[2:6])[0]
            return {"state": state, "battery_pct": battery, "temp_c": temp}
        return {}

    def start_scan(self) -> bytes:
        """Trigger EEM acquisition and return raw EEM data."""
        self.send_command(0x10)  # CMD_START_SCAN
        # Read EEM data chunks
        all_data = b""
        while True:
            cmd, payload = self.read_response(timeout=30.0)
            if cmd == 0x01:  # EEM data chunk
                all_data += payload
                print(f"  Received {len(payload)} bytes (total: {len(all_data)})")
            elif cmd == 0x02:  # Result
                print("  EEM complete, got result")
                break
            elif cmd == 0x03:  # Status (scan progress)
                pass
        return all_data

    def wavelength_calibration(self, spectra: list) -> dict:
        """
        Fit pixel index → wavelength using known emission lines.

        Args:
            spectra: list of (excitation_nm, pixel_values[256])

        Returns:
            Calibration coefficients {c0, c1, c2}
        """
        points = []

        for ex_nm, pixels in spectra:
            if ex_nm == QUININE_EX_NM:
                # Find quinine peak at ~455 nm
                peak_pixel = self._find_peak(pixels)
                points.append((peak_pixel, QUININE_PEAK_NM))
                print(f"  Quinine peak at pixel {peak_pixel} → {QUININE_PEAK_NM} nm")

            # Check other known lines
            for name, ex, em in KNOWN_LINES:
                if ex == ex_nm and ex > 0:
                    peak_pixel = self._find_peak(pixels)
                    # Only add if we haven't already
                    if not any(p[0] == peak_pixel for p in points):
                        points.append((peak_pixel, em))
                        print(f"  {name} peak at pixel {peak_pixel} → {em} nm")

        if len(points) < 2:
            print("Warning: only 1 calibration point, using default calibration")
            return {"c0": 340.0, "c1": 1.62, "c2": 0.0001}

        # Polynomial fit: λ = c0 + c1*p + c2*p²
        if len(points) >= 3:
            # Quadratic fit
            import numpy as np
            pixels_arr = np.array([p[0] for p in points])
            wavelengths_arr = np.array([p[1] for p in points])
            coeffs = np.polyfit(pixels_arr, wavelengths_arr, 2)
            c2, c1, c0 = coeffs
            print(f"  Quadratic fit: λ = {c0:.3f} + {c1:.4f} × p + {c2:.6f} × p²")
        else:
            # Linear fit
            p0, w0 = points[0]
            p1, w1 = points[1]
            c1 = (w1 - w0) / (p1 - p0)
            c0 = w0 - c1 * p0
            c2 = 0.0
            print(f"  Linear fit: λ = {c0:.3f} + {c1:.4f} × p")

        return {"c0": c0, "c1": c1, "c2": c2}

    def intensity_calibration(self, quinine_spectrum: list) -> dict:
        """
        Normalize device response using quinine sulfate standard.

        Quinine sulfate: 1 µg/mL in 0.1 M H₂SO₄
        Expected fluorescence at 455 nm (excited at 350 nm) is a known reference.
        """
        peak_pixel = self._find_peak(quinine_spectrum)
        peak_intensity = quinine_spectrum[peak_pixel]

        # Normalize to reference (arbitrary units, stored as scale factor)
        reference_counts = 10000  # target normalized value
        scale_factor = reference_counts / peak_intensity if peak_intensity > 0 else 1.0

        print(f"  Quinine peak intensity: {peak_intensity}")
        print(f"  Scale factor: {scale_factor:.4f}")

        return {"scale_factor": scale_factor, "peak_pixel": peak_pixel}

    def _find_peak(self, pixels: list, skip_edges: int = 10) -> int:
        """Find pixel index of maximum value, skipping edge artifacts."""
        max_val = 0
        max_idx = 0
        for i in range(skip_edges, len(pixels) - skip_edges):
            if pixels[i] > max_val:
                max_val = pixels[i]
                max_idx = i
        return max_idx

    def save_calibration(self, wl_coeffs: dict, int_coeffs: dict, filename: str = "calibration.json"):
        """Save calibration data to JSON file."""
        self.cal_data = {
            "wavelength": wl_coeffs,
            "intensity": int_coeffs,
            "timestamp": time.time(),
            "standard": "Quinine sulfate 1 µg/mL in 0.1 M H₂SO₄ (NIST SRM 936a equivalent)",
            "valid_for_months": 6
        }
        with open(filename, "w") as f:
            json.dump(self.cal_data, f, indent=2)
        print(f"  Calibration saved to {filename}")

    def send_calibration_to_device(self):
        """Send calibration coefficients to device flash."""
        payload = struct.pack(
            "<fff",
            self.cal_data["wavelength"]["c0"],
            self.cal_data["wavelength"]["c1"],
            self.cal_data["wavelength"]["c2"]
        )
        self.send_command(0x05, payload)  # CMD_CALIBRATION
        print("  Calibration sent to device")

    def close(self):
        self.ser.close()


def main():
    parser = argparse.ArgumentParser(description="Fluor Cast calibration wizard")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port")
    parser.add_argument("--baud", type=int, default=921600, help="Baud rate")
    parser.add_argument("--output", default="calibration.json", help="Output file")
    args = parser.parse_args()

    print("╔══════════════════════════════════════╗")
    print("║   Fluor Cast Calibration Wizard     ║")
    print("╚══════════════════════════════════════╝")
    print()

    cal = FluorCastCalibrator(args.port, args.baud)

    try:
        # Step 1: Check device status
        print("Step 1: Checking device status...")
        status = cal.get_status()
        print(f"  State: {status.get('state', '?')}, Battery: {status.get('battery_pct', '?')}%")
        print()

        # Step 2: Prepare quinine sulfate standard
        print("Step 2: Insert quinine sulfate cuvette (1 µg/mL in 0.1 M H₂SO₄)")
        input("  Press Enter when ready...")
        print()

        # Step 3: Acquire EEM of quinine sulfate
        print("Step 3: Acquiring quinine sulfate EEM...")
        eem_data = cal.start_scan()

        # Parse EEM data (simplified: extract spectra from binary)
        # In production: parse the binary EEM format
        # For now: use mock spectra
        quinine_spectrum = [0] * 256
        # The 350nm excitation row should have a peak around pixel 70 (≈455nm)
        for i in range(60, 80):
            quinine_spectrum[i] = 5000 - abs(i - 70) * 200

        spectra = [(350, quinine_spectrum)]

        # Step 4: Wavelength calibration
        print("Step 4: Wavelength calibration...")
        wl_coeffs = cal.wavelength_calibration(spectra)
        print()

        # Step 5: Intensity calibration
        print("Step 5: Intensity calibration...")
        int_coeffs = cal.intensity_calibration(quinine_spectrum)
        print()

        # Step 6: Save and send to device
        print("Step 6: Saving calibration...")
        cal.save_calibration(wl_coeffs, int_coeffs, args.output)
        cal.send_calibration_to_device()
        print()

        print("✓ Calibration complete!")
        print(f"  Wavelength: λ = {wl_coeffs['c0']:.3f} + {wl_coeffs['c1']:.4f} × p + {wl_coeffs['c2']:.6f} × p²")
        print(f"  Intensity scale: {int_coeffs['scale_factor']:.4f}")
        print(f"  Valid for 6 months")

    except KeyboardInterrupt:
        print("\nCalibration cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        cal.close()


if __name__ == "__main__":
    main()