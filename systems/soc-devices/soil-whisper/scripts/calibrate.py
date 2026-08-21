#!/usr/bin/env python3
"""
Soil Whisper — Calibration Utility

Interactive command-line tool for calibrating Soil Whisper probes
via the serial console interface.

Usage:
    python calibrate.py --port /dev/ttyUSB0
    python calibrate.py --port COM3

Commands:
    - Follow the on-screen prompts to calibrate each sensor
"""

import serial
import time
import argparse
import sys


class SoilWhisperCalibrator:
    """Calibration utility for Soil Whisper device."""

    PROMPT = "SOIL> "

    def __init__(self, port: str, baud: int = 115200):
        self.ser = serial.Serial(port, baud, timeout=5)
        self.ser.reset_input_buffer()
        time.sleep(1)  # Wait for device to be ready

    def send_command(self, cmd: str) -> str:
        """Send a command and read the response."""
        self.ser.write((cmd + "\r\n").encode())
        time.sleep(0.5)
        response = self.ser.read(self.ser.in_waiting).decode("utf-8", errors="ignore")
        return response

    def calibrate_moisture(self, channel: int, reference: str):
        """Calibrate a moisture channel.

        Args:
            channel: 0, 1, or 2 (10cm, 20cm, 40cm)
            reference: "air" (dry) or "water" (wet)
        """
        print(f"\n--- Moisture Channel {channel} ({['10cm', '20cm', '40cm'][channel]}) ---")
        print(f"Place the probe in {reference} and press Enter to calibrate...")
        input()
        response = self.send_command(f"cal moisture {channel} {reference}")
        print(f"Device response: {response}")

    def calibrate_ph(self, buffer_value: float):
        """Calibrate pH sensor with a buffer solution.

        Args:
            buffer_value: pH value of the buffer (e.g., 4.0 or 7.0)
        """
        print(f"\n--- pH Calibration ---")
        print(f"Immerse the pH electrode in pH {buffer_value} buffer solution.")
        print("Wait 30 seconds for the reading to stabilize, then press Enter...")
        input()
        response = self.send_command(f"cal ph {buffer_value}")
        print(f"Device response: {response}")

    def calibrate_npk(self, ion: str, concentration: float):
        """Calibrate an NPK ion-selective electrode.

        Args:
            ion: "no3", "po4", or "k"
            concentration: Standard solution concentration in ppm
        """
        print(f"\n--- NPK Calibration ({ion.upper()}) ---")
        print(f"Immerse the {ion} electrode in {concentration} ppm standard solution.")
        print("Wait 60 seconds for the reading to stabilize, then press Enter...")
        input()
        response = self.send_command(f"cal npk {ion} {concentration}")
        print(f"Device response: {response}")

    def interactive_calibration(self):
        """Run the full interactive calibration sequence."""
        print("=" * 60)
        print("  Soil Whisper — Interactive Calibration")
        print("=" * 60)
        print()

        # Step 1: Moisture calibration
        print("STEP 1: Moisture Calibration")
        print("-" * 40)
        for ch in range(3):
            depth = ["10cm", "20cm", "40cm"][ch]
            print(f"\nChannel {ch} ({depth}):")
            self.calibrate_moisture(ch, "air")
            self.calibrate_moisture(ch, "water")

        # Step 2: pH calibration
        print("\n\nSTEP 2: pH Calibration")
        print("-" * 40)
        self.calibrate_ph(4.0)
        self.calibrate_ph(7.0)

        # Step 3: NPK calibration
        print("\n\nSTEP 3: NPK Calibration")
        print("-" * 40)
        self.calibrate_npk("no3", 100)
        self.calibrate_npk("po4", 50)
        self.calibrate_npk("k", 200)

        # Verify
        print("\n\nSTEP 4: Verification")
        print("-" * 40)
        print("Taking a sample to verify calibration...")
        response = self.send_command("sample now")
        print(f"Device response:\n{response}")

        print("\n✅ Calibration complete!")
        print("Calibration data has been saved to flash memory.")
        print("The device will use these calibration values for all future readings.")

    def close(self):
        self.ser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Soil Whisper Calibration Utility"
    )
    parser.add_argument("--port", required=True, help="Serial port (e.g., /dev/ttyUSB0 or COM3)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")

    args = parser.parse_args()

    try:
        cal = SoilWhisperCalibrator(args.port, args.baud)
        cal.interactive_calibration()
        cal.close()
    except serial.SerialException as e:
        print(f"Error: Could not open serial port {args.port}: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCalibration cancelled by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()