#!/usr/bin/env python3
"""
Soil Whisper — Data Logger & CSV Exporter

Reads Soil Whisper data via serial or from LoRaWAN MQTT broker
and logs to CSV files for analysis.

Usage:
    python data_logger.py --serial /dev/ttyUSB0 --output soil_data.csv
    python data_logger.py --mqtt --broker ttn.example.com --app myapp --device 0102030405060708
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Import decoder
sys.path.insert(0, str(Path(__file__).parent))
from soil_whisper_decoder import SoilData


class SoilDataLogger:
    """Logs Soil Whisper data to CSV."""

    CSV_HEADERS = [
        "timestamp", "moisture_10", "moisture_20", "moisture_40",
        "temp_10", "temp_20", "temp_40",
        "no3_ppm", "po4_ppm", "k_ppm",
        "ph", "humidity", "vbat",
        "flags_moisture_valid", "flags_temperature_valid",
        "flags_npk_valid", "flags_ph_valid", "flags_humidity_valid",
    ]

    def __init__(self, output_file: str):
        self.output_file = output_file
        self.file_exists = Path(output_file).exists()

        # Create file with headers if it doesn't exist
        if not self.file_exists:
            with open(output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(self.CSV_HEADERS)

    def log(self, data: SoilData):
        """Append a data point to the CSV file."""
        flags = data.flags_dict
        row = [
            datetime.utcnow().isoformat() + "Z",
            data.moisture_10, data.moisture_20, data.moisture_40,
            data.temp_10, data.temp_20, data.temp_40,
            data.no3, data.po4, data.k,
            data.ph, data.humidity, data.vbat,
            flags["moisture_valid"], flags["temperature_valid"],
            flags["npk_valid"], flags["ph_valid"], flags["humidity_valid"],
        ]

        with open(self.output_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        print(f"[{datetime.utcnow().isoformat()}Z] Logged: "
              f"M={data.moisture_10:.0f}/{data.moisture_20:.0f}/{data.moisture_40:.0f}% "
              f"T={data.temp_10:.1f}/{data.temp_20:.1f}/{data.temp_40:.1f}°C "
              f"NPK={data.no3:.0f}/{data.po4:.0f}/{data.k:.0f} "
              f"pH={data.ph:.1f} RH={data.humidity:.0f}% "
              f"VBat={data.vbat:.2f}V")

    def log_serial(self, port: str, baud: int = 115200):
        """Read data from serial port and log."""
        import serial

        ser = serial.Serial(port, baud, timeout=10)
        print(f"Connected to {port} at {baud} baud. Waiting for data...")

        buffer = b""
        while True:
            data = ser.read(ser.in_waiting or 1)
            if data:
                buffer += data
                # Look for PAYLOAD: marker
                while b"PAYLOAD:" in buffer:
                    start = buffer.index(b"PAYLOAD:") + len(b"PAYLOAD:")
                    end = buffer.find(b"\n", start)
                    if end == -1:
                        break
                    hex_str = buffer[start:end].strip().decode("ascii")
                    buffer = buffer[end + 1:]
                    try:
                        payload = bytes.fromhex(hex_str)
                        soil = SoilData.decode(payload)
                        self.log(soil)
                    except (ValueError, AssertionError) as e:
                        print(f"Decode error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Soil Whisper Data Logger"
    )
    parser.add_argument("--serial", help="Serial port for live data")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate")
    parser.add_argument("--output", default="soil_data.csv", help="Output CSV file")
    parser.add_argument("--mqtt", action="store_true", help="Use MQTT source")
    parser.add_argument("--broker", help="MQTT broker hostname")
    parser.add_argument("--app", help="TTN application ID")
    parser.add_argument("--device", help="Device EUI")

    args = parser.parse_args()

    logger = SoilDataLogger(args.output)

    if args.serial:
        try:
            logger.log_serial(args.serial, args.baud)
        except KeyboardInterrupt:
            print("\nLogging stopped.")
    elif args.mqtt:
        print("MQTT logging not yet implemented — use soil_whisper_decoder.py --mqtt instead")
        sys.exit(1)
    else:
        # Demo: generate some sample data
        print("No data source specified. Generating demo data...")
        import random
        for i in range(24):
            payload = bytes([
                0xF8,
                random.randint(1000, 5000) & 0xFF, (random.randint(1000, 5000) >> 8) & 0xFF,
                random.randint(800, 4000) & 0xFF, (random.randint(800, 4000) >> 8) & 0xFF,
                random.randint(600, 3000) & 0xFF, (random.randint(600, 3000) >> 8) & 0xFF,
                random.randint(4000, 6000) & 0xFF, (random.randint(4000, 6000) >> 8) & 0xFF,
                random.randint(3500, 5500) & 0xFF, (random.randint(3500, 5500) >> 8) & 0xFF,
                random.randint(3000, 5000) & 0xFF, (random.randint(3000, 5000) >> 8) & 0xFF,
                random.randint(100, 800) & 0xFF, (random.randint(100, 800) >> 8) & 0xFF,
                random.randint(3, 50),
                random.randint(500, 3000) & 0xFF, (random.randint(500, 3000) >> 8) & 0xFF,
                random.randint(50, 80),
                random.randint(100, 200),
                random.randint(150, 180),
            ])
            soil = SoilData.decode(payload)
            logger.log(soil)
            time.sleep(0.1)

        print(f"\nDemo data written to {args.output}")


if __name__ == "__main__":
    main()