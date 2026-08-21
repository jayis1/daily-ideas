#!/usr/bin/env python3
"""
Mycelium Node — Sensor Calibration Utility

Connects to Mycelium Node via serial port and performs sensor calibration:
  - SCD41 CO2 forced recalibration (expose to fresh air first)
  - SHT40 offset calibration (compare with reference thermometer/hygrometer)
  - DS18B20 offset calibration (ice water bath at 0°C)

Usage:
    python3 calibrate.py --port /dev/ttyUSB0 --co2 420
    python3 calibrate.py --port /dev/ttyUSB0 --temp-offset -0.3
    python3 calibrate.py --port /dev/ttyUSB0 --ice-bath

Requires: pyserial (pip install pyserial)
"""

import argparse
import sys
import time

try:
    import serial
except ImportError:
    print("Error: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)


class MyceliumCalibrator:
    """Serial interface for Mycelium Node calibration."""

    def __init__(self, port: str, baud: int = 115200, timeout: float = 5.0):
        self.ser = serial.Serial(port, baud, timeout=timeout)
        self.ser.flushInput()
        self.ser.flushOutput()
        time.sleep(1)  # Wait for device to be ready
        print(f"Connected to Mycelium Node on {port} @ {baud} baud")

    def send_command(self, cmd: str) -> str:
        """Send a command and read the response."""
        self.ser.write((cmd + '\n').encode('utf-8'))
        time.sleep(0.5)

        response = ''
        while self.ser.in_waiting > 0:
            chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='replace')
            response += chunk
            time.sleep(0.1)

        return response.strip()

    def get_status(self) -> dict:
        """Get current sensor status."""
        response = self.send_command('status')
        # Parse the status output
        result = {}
        for line in response.split('\n'):
            line = line.strip()
            if 'CHAMBER:' in line:
                parts = line.split()
                result['chamber_temp'] = float(parts[1].rstrip('°C'))
                result['chamber_rh'] = float(parts[3].rstrip('%'))
            elif 'CO2:' in line:
                parts = line.split()
                result['co2'] = int(parts[1].rstrip('ppm'))
            elif 'DEEP1:' in line:
                parts = line.split()
                result['deep_temp_1'] = float(parts[1].rstrip('°C'))
                result['deep_temp_2'] = float(parts[3].rstrip('°C'))
        return result

    def calibrate_co2(self, target_ppm: int):
        """
        Perform SCD41 forced recalibration.
        
        IMPORTANT: Before running this, expose the sensor to fresh outdoor air
        (≈420 ppm CO₂) for at least 10 minutes. The sensor must be in a stable
        environment with known CO₂ concentration.
        """
        print(f"\n{'='*60}")
        print("SCD41 CO₂ Forced Recalibration")
        print(f"{'='*60}")
        print(f"\nTarget CO₂ concentration: {target_ppm} ppm")
        print("\nBefore proceeding, ensure:")
        print("  1. Sensor has been in stable conditions for 10+ minutes")
        print("  2. If calibrating to outdoor air, sensor is outdoors")
        print("  3. No recent changes in ventilation or human presence")
        
        confirm = input("\nProceed with calibration? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Calibration cancelled.")
            return

        # Get current reading
        status = self.get_status()
        print(f"\nCurrent CO₂ reading: {status.get('co2', 'unknown')} ppm")
        
        # Send calibration command
        response = self.send_command(f'calibrate co2 {target_ppm}')
        print(f"\nDevice response: {response}")
        print("\n✓ CO₂ calibration complete!")
        print(f"  The SCD41 will use {target_ppm} ppm as the reference point.")
        print("  Allow 5 minutes for readings to stabilize.")

    def calibrate_ds18b20_ice_bath(self):
        """
        Calibrate DS18B20 temperature probes using ice water bath (0°C).
        
        Steps:
        1. Prepare an ice water bath with crushed ice and water
        2. Stir well and let sit for 5 minutes
        3. Insert both DS18B20 probes
        4. Wait 2 minutes for stabilization
        5. Record the offset from 0°C
        """
        print(f"\n{'='*60}")
        print("DS18B20 Ice Water Bath Calibration (0°C)")
        print(f"{'='*60}")
        print("\nSteps:")
        print("  1. Prepare a container with crushed ice and water")
        print("  2. Stir well and wait 5 minutes for temperature to stabilize at 0°C")
        print("  3. Insert both DS18B20 probes into the ice water")
        print("  4. Wait 2 minutes for probe readings to stabilize")

        input("\nPress Enter when probes are stabilized in ice water...")

        # Take multiple readings and average
        print("\nReading probes (taking 5 samples over 10 seconds)...")
        readings = []
        for i in range(5):
            time.sleep(2)
            status = self.get_status()
            t1 = status.get('deep_temp_1', 0)
            t2 = status.get('deep_temp_2', 0)
            readings.append((t1, t2))
            print(f"  Sample {i+1}: Deep1={t1:.2f}°C  Deep2={t2:.2f}°C")

        # Calculate averages
        avg_t1 = sum(r[0] for r in readings) / len(readings)
        avg_t2 = sum(r[1] for r in readings) / len(readings)

        # Calculate offsets (reading - 0°C = offset)
        offset_1 = avg_t1 - 0.0
        offset_2 = avg_t2 - 0.0

        print(f"\nResults:")
        print(f"  Probe 1 average: {avg_t1:.3f}°C  (offset: {offset_1:+.3f}°C)")
        print(f"  Probe 2 average: {avg_t2:.3f}°C  (offset: {offset_2:+.3f}°C)")
        print(f"\nNote: These offsets should be stored in NVS and applied to readings.")
        print(f"  In firmware, add DS18B20_OFFSET_1 = {offset_1:.3f}")
        print(f"  In firmware, add DS18B20_OFFSET_2 = {offset_2:.3f}")
        print(f"\n  Apply these offsets in main.c's ds18b20_read_all() function.")

    def calibrate_sht40(self):
        """
        Guide user through SHT40 calibration by comparing with a reference.
        """
        print(f"\n{'='*60}")
        print("SHT40 Temperature/Humidity Calibration")
        print(f"{'='*60}")
        print("\nThe SHT40 is factory-calibrated to ±0.1°C / ±1.8% RH.")
        print("If you have a calibrated reference thermometer/hygrometer,")
        print("you can apply a software offset.")
        print("\nNote: SHT40 offsets are applied in firmware, not in the sensor.")
        print("  This tool will display current readings for comparison.")

        while True:
            status = self.get_status()
            print(f"\n  Chamber:  T={status.get('chamber_temp', '?')}°C  RH={status.get('chamber_rh', '?')}%")
            print(f"  Substrate: T={status.get('substrate_temp', '?')}°C  RH={status.get('substrate_rh', '?')}%")
            print(f"\n  Enter reference temperature (°C) or 'q' to quit: ", end='')

            ref_temp_str = input().strip()
            if ref_temp_str.lower() == 'q':
                break

            try:
                ref_temp = float(ref_temp_str)
                offset = status.get('chamber_temp', ref_temp) - ref_temp
                print(f"  Offset: {offset:+.2f}°C")
                print(f"  Apply in firmware: SHT40_CHAMBER_TEMP_OFFSET = {offset:.2f}")
            except ValueError:
                print("  Invalid input.")

    def save_config(self):
        """Save current configuration to NVS."""
        response = self.send_command('save')
        print(f"Config saved: {response}")

    def close(self):
        """Close serial connection."""
        self.ser.close()
        print("Serial connection closed.")


def main():
    parser = argparse.ArgumentParser(
        description='Mycelium Node Calibration Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Calibrate CO2 sensor (outdoor air ≈ 420 ppm)
  python3 calibrate.py --port /dev/ttyUSB0 --co2 420

  # Calibrate DS18B20 probes in ice water bath
  python3 calibrate.py --port /dev/ttyUSB0 --ice-bath

  # Compare SHT40 readings with reference instrument
  python3 calibrate.py --port /dev/ttyUSB0 --sht40
        """
    )
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    parser.add_argument('--co2', type=int, help='Calibrate SCD41 CO2 to target ppm')
    parser.add_argument('--ice-bath', action='store_true', help='DS18B20 ice water bath calibration')
    parser.add_argument('--sht40', action='store_true', help='SHT40 comparison calibration')
    parser.add_argument('--save', action='store_true', help='Save config to NVS after calibration')

    args = parser.parse_args()

    if not any([args.co2, args.ice_bath, args.sht40, args.save]):
        parser.print_help()
        sys.exit(1)

    cal = MyceliumCalibrator(port=args.port, baud=args.baud)

    try:
        if args.co2:
            cal.calibrate_co2(args.co2)
        if args.ice_bath:
            cal.calibrate_ds18b20_ice_bath()
        if args.sht40:
            cal.calibrate_sht40()
        if args.save:
            cal.save_config()
    finally:
        cal.close()


if __name__ == '__main__':
    main()