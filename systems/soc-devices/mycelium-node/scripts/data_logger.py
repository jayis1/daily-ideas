#!/usr/bin/env python3
"""
Mycelium Node — MQTT Data Logger

Subscribes to Mycelium Node sensor data and logs to CSV files.
Supports multiple nodes on the same MQTT broker.

Usage:
    python3 data_logger.py --broker mqtt.local --device mycelium-a1b2c3

Requires: paho-mqtt (pip install paho-mqtt)
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt not installed. Run: pip install paho-mqtt")
    sys.exit(1)


class MyceliumDataLogger:
    """Logs Mycelium Node sensor data to CSV files."""

    def __init__(self, broker: str, port: int, device_id: str, output_dir: str):
        self.broker = broker
        self.port = port
        self.device_id = device_id
        self.output_dir = output_dir
        self.csv_file = None
        self.csv_writer = None

        # MQTT topics
        self.topic_sensors = f"mycelium/node/{device_id}/sensors"
        self.topic_status = f"mycelium/node/{device_id}/status"

        # CSV columns
        self.columns = [
            'timestamp', 'phase',
            'chamber_temp_c', 'chamber_rh_pct', 'co2_ppm', 'light_lux',
            'substrate_temp_c', 'substrate_rh_pct', 'deep_temp_1_c', 'deep_temp_2_c',
            'humidifier_pct', 'heater_pct', 'fan_pct', 'light_pct',
            'lipo_v', 'usb_v', 'rail_12v'
        ]

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Open CSV file
        date_str = datetime.now().strftime('%Y%m%d')
        filename = os.path.join(output_dir, f"mycelium_{device_id}_{date_str}.csv")
        self.csv_file = open(filename, 'a', newline='')
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=self.columns)

        # Write header if file is new
        if self.csv_file.tell() == 0:
            self.csv_writer.writeheader()
            self.csv_file.flush()

        print(f"Logging to: {filename}")

        # Setup MQTT client
        self.client = mqtt.Client(client_id=f"logger_{device_id}")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to MQTT broker at {self.broker}:{self.port}")
            client.subscribe(self.topic_sensors)
            client.subscribe(self.topic_status)
            print(f"Subscribed to: {self.topic_sensors}")
            print(f"Subscribed to: {self.topic_status}")
        else:
            print(f"Connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode('utf-8'))
        except json.JSONDecodeError:
            print(f"Invalid JSON on {msg.topic}")
            return

        if msg.topic == self.topic_sensors:
            self._log_sensor_data(data)
        elif msg.topic == self.topic_status:
            self._log_status_data(data)

    def _log_sensor_data(self, data: dict):
        """Log sensor reading to CSV."""
        row = {
            'timestamp': datetime.fromtimestamp(data['ts']).isoformat(),
            'phase': data.get('phase', ''),
            'chamber_temp_c': data['chamber']['temp_c'],
            'chamber_rh_pct': data['chamber']['rh_pct'],
            'co2_ppm': data['chamber']['co2_ppm'],
            'light_lux': data['chamber']['light_lux'],
            'substrate_temp_c': data['substrate']['temp_c'],
            'substrate_rh_pct': data['substrate']['rh_pct'],
            'deep_temp_1_c': data['substrate'].get('deep_temp_1_c', ''),
            'deep_temp_2_c': data['substrate'].get('deep_temp_2_c', ''),
            'humidifier_pct': data['actuators']['humidifier_pct'],
            'heater_pct': data['actuators']['heater_pct'],
            'fan_pct': data['actuators']['fan_pct'],
            'light_pct': data['actuators']['light_pct'],
            'lipo_v': data['power']['lipo_v'],
            'usb_v': data['power']['usb_v'],
            'rail_12v': data['power']['rail_12v'],
        }

        self.csv_writer.writerow(row)
        self.csv_file.flush()

        # Print summary
        print(f"[{row['timestamp']}] {data['phase']:12s} | "
              f"T={data['chamber']['temp_c']:5.1f}°C | "
              f"RH={data['chamber']['rh_pct']:5.1f}% | "
              f"CO₂={data['chamber']['co2_ppm']:4d}ppm | "
              f"Hum={data['actuators']['humidifier_pct']:3.0f}% | "
              f"Fan={data['actuators']['fan_pct']:3.0f}%")

    def _log_status_data(self, data: dict):
        """Log status (less frequent, PID info)."""
        print(f"[STATUS] uptime={data['uptime_s']}s | "
              f"phase={data['phase']} day={data['phase_day']} | "
              f"PID: H={data['pid']['humidity']['output']:.1f}% "
              f"T={data['pid']['temperature']['output']:.1f}% "
              f"CO₂={data['pid']['co2']['output']:.1f}% | "
              f"errors={data['errors']}")

    def run(self):
        """Connect and run the MQTT loop."""
        print(f"Connecting to {self.broker}:{self.port}...")
        self.client.connect(self.broker, self.port, 60)

        try:
            self.client.loop_forever()
        except KeyboardInterrupt:
            print("\nDisconnecting...")
            self.client.disconnect()
            self.csv_file.close()
            print("Logger stopped.")


def main():
    parser = argparse.ArgumentParser(description='Mycelium Node MQTT Data Logger')
    parser.add_argument('--broker', default='mqtt.local', help='MQTT broker address')
    parser.add_argument('--port', type=int, default=1883, help='MQTT broker port')
    parser.add_argument('--device', default='mycelium-a1b2c3', help='Device ID')
    parser.add_argument('--output', default='./data', help='Output directory for CSV files')
    args = parser.parse_args()

    logger = MyceliumDataLogger(
        broker=args.broker,
        port=args.port,
        device_id=args.device,
        output_dir=args.output
    )
    logger.run()


if __name__ == '__main__':
    main()