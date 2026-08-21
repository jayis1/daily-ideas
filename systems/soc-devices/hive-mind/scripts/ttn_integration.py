#!/usr/bin/env python3
"""
Hive Mind — TTN Payload Integration
Decodes Hive Mind uplinks from The Things Network V3 MQTT broker
and stores them in InfluxDB for Grafana visualization.

SPDX-License-Identifier: MIT
Copyright (c) 2026 jayis1

Usage:
    python3 ttn_integration.py --host localhost --db hivemind

Requires: paho-mqtt, influxdb, decode_payload module
    pip install paho-mqtt influxdb
"""

import argparse
import json
import sys
import base64
from datetime import datetime

# Import the decoder from the same directory
from decode_payload import decode_payload

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt not installed. Run: pip install paho-mqtt")
    sys.exit(1)

try:
    from influxdb import InfluxDBClient
except ImportError:
    print("Error: influxdb not installed. Run: pip install influxdb")
    sys.exit(1)

# Configuration
TTN_MQTT_HOST = "eu1.cloud.thethings.network"
TTN_MQTT_PORT = 1883
TTN_APP_ID = "hive-mind"  # Replace with your TTN application ID
TTN_API_KEY = ""  # Replace with your TTN API key

INFLUX_HOST = "localhost"
INFLUX_PORT = 8086
INFLUX_DB = "hivemind"


def on_connect(client, userdata, flags, rc):
    """Called when connected to MQTT broker."""
    if rc == 0:
        print(f"Connected to MQTT broker at {TTN_MQTT_HOST}")
        topic = f"v3/{TTN_APP_ID}@ttn/devices/#/up"
        client.subscribe(topic)
        print(f"Subscribed to: {topic}")
    else:
        print(f"MQTT connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Called when a message is received from TTN."""
    try:
        payload = json.loads(msg.payload.decode())

        # Extract device ID and uplink data
        device_id = payload.get("end_device_ids", {}).get("device_id", "unknown")
        uplink = payload.get("uplink_message", {})
        frm_payload = uplink.get("frm_payload", "")

        if not frm_payload:
            print(f"No payload from {device_id}")
            return

        # Decode base64 payload
        raw_data = base64.b64decode(frm_payload)

        # Decode using our decoder
        decoded = decode_payload(raw_data)

        # Add metadata
        decoded["device_id"] = device_id
        decoded["timestamp"] = datetime.utcnow().isoformat()

        # Write to InfluxDB
        write_to_influx(decoded)

        print(f"[{decoded['timestamp']}] {device_id}: "
              f"Weight={decoded['weight_kg']}kg, "
              f"Health={decoded['health_score']}/100, "
              f"Class={decoded['acoustic_class']}")

    except Exception as e:
        print(f"Error processing message: {e}")


def write_to_influx(data: dict):
    """Write decoded data point to InfluxDB."""
    point = {
        "measurement": "hive_mind",
        "tags": {
            "device": data["device_id"],
        },
        "fields": {
            "weight_g": data["weight_g"],
            "weight_kg": data["weight_kg"],
            "temp_floor_c": data["temp_floor_c"],
            "temp_mid_c": data["temp_mid_c"],
            "temp_crown_c": data["temp_crown_c"],
            "ambient_t_c": data["ambient_t_c"],
            "ambient_h_pct": data["ambient_h_pct"],
            "ambient_p_hpa": data["ambient_p_hpa"],
            "acoustic_class_id": data["acoustic_class_id"],
            "dominant_freq_hz": data["dominant_freq_hz"],
            "bee_in": data["bee_in"],
            "bee_out": data["bee_out"],
            "battery_v": data["battery_v"],
            "solar_v": data["solar_v"],
            "uptime_h": data["uptime_h"],
            "health_score": data["health_score"],
        },
    }

    influx_client.write_points([point])


def main():
    global TTN_APP_ID, TTN_API_KEY, INFLUX_HOST, INFLUX_PORT, INFLUX_DB
    global influx_client

    parser = argparse.ArgumentParser(description="Hive Mind TTN integration")
    parser.add_argument("--app-id", default=TTN_APP_ID, help="TTN application ID")
    parser.add_argument("--api-key", default=TTN_API_KEY, help="TTN API key")
    parser.add_argument("--influx-host", default=INFLUX_HOST, help="InfluxDB host")
    parser.add_argument("--influx-port", type=int, default=INFLUX_PORT, help="InfluxDB port")
    parser.add_argument("--influx-db", default=INFLUX_DB, help="InfluxDB database name")
    args = parser.parse_args()

    TTN_APP_ID = args.app_id
    TTN_API_KEY = args.api_key

    # Connect to InfluxDB
    influx_client = InfluxDBClient(
        host=args.influx_host,
        port=args.influx_port,
        database=args.influx_db
    )

    # Create database if it doesn't exist
    influx_client.create_database(args.influx_db)
    print(f"Connected to InfluxDB at {args.influx_host}:{args.influx_port}/{args.influx_db}")

    # Connect to TTN MQTT broker
    client = mqtt.Client(client_id="hive-mind-integration")
    client.username_pw_set(args.app_id, args.api_key)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connecting to TTN MQTT at {TTN_MQTT_HOST}:{TTN_MQTT_PORT}...")
    client.connect(TTN_MQTT_HOST, TTN_MQTT_PORT, 60)

    # Loop forever
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nDisconnecting...")
        client.disconnect()
        influx_client.close()


if __name__ == "__main__":
    main()