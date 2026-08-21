#!/usr/bin/env python3
"""
Brewfather Sync Tool

Publishes Brew Sense data to the Brewfather custom stream API.
Reads from MQTT and forwards to Brewfather's HTTP endpoint.
"""

import argparse
import json
import time
import sys
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Please install paho-mqtt: pip install paho-mqtt")

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")


BREWFATHER_API_URL = "https://log.brewfather.app/stream"


class BrewfatherSync:
    def __init__(self, device_id, mqtt_broker, mqtt_port, brewfather_key,
                 mqtt_user=None, mqtt_pass=None):
        self.device_id = device_id
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.brewfather_key = brewfather_key
        self.mqtt_user = mqtt_user
        self.mqtt_pass = mqtt_pass
        
        self.current = {
            "gravity": 0.0,
            "temperature": 0.0,
            "co2": 0,
            "ph": 0.0,
            "pressure": 0.0,
            "stage": "UNKNOWN",
            "activity": 0,
            "trend": 0,
        }
        
        self.last_push = 0
        self.push_interval = 900  # Push every 15 minutes
        self.client = None
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to MQTT broker: {self.mqtt_broker}")
            topic = f"brewsense/{self.device_id}/#"
            client.subscribe(topic)
            print(f"Subscribed to: {topic}")
        else:
            print(f"MQTT connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8", errors="replace")
        
        parts = topic.split("/")
        if len(parts) >= 3:
            metric = parts[2]
            
            if metric == "status":
                try:
                    data = json.loads(payload)
                    for key in self.current:
                        if key in data:
                            self.current[key] = data[key]
                except json.JSONDecodeError:
                    pass
            elif metric in self.current:
                try:
                    if metric == "co2":
                        self.current[metric] = int(float(payload))
                    elif metric == "activity":
                        self.current[metric] = int(float(payload))
                    elif metric == "trend":
                        self.current[metric] = int(float(payload))
                    elif metric == "stage":
                        self.current[metric] = payload.strip()
                    else:
                        self.current[metric] = float(payload)
                except ValueError:
                    pass
    
    def push_to_brewfather(self):
        """Push current data to Brewfather custom stream."""
        url = f"{BREWFATHER_API_URL}?id={self.brewfather_key}"
        
        # Brewfather custom stream format
        payload = {
            "name": f"BrewSense-{self.device_id}",
            "gravity": self.current["gravity"],
            "gravity_unit": "SG",
            "temp": self.current["temperature"],
            "temp_unit": "C",
            "comment": f"Stage: {self.current['stage']}, Activity: {self.current['activity']}%, "
                       f"CO2: {self.current['co2']}ppm, pH: {self.current['ph']:.2f}",
            "ph": self.current["ph"],
            "aux_pressure": self.current["pressure"],
        }
        
        # Remove fields with zero values (Brewfather ignores them)
        payload = {k: v for k, v in payload.items() if v != 0.0 and v != 0}
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                      f"Pushed to Brewfather: SG={self.current['gravity']:.4f}, "
                      f"T={self.current['temperature']:.1f}°C")
                return True
            else:
                print(f"Brewfather error: {response.status_code} {response.text}")
                return False
        except requests.RequestException as e:
            print(f"Push failed: {e}")
            return False
    
    def run(self):
        """Main sync loop."""
        self.client = mqtt.Client(client_id=f"brewsense-sync-{self.device_id}")
        
        if self.mqtt_user and self.mqtt_pass:
            self.client.username_pw_set(self.mqtt_user, self.mqtt_pass)
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        try:
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"Failed to connect to MQTT: {e}")
            sys.exit(1)
        
        print(f"Brewfather Sync running for {self.device_id}")
        print(f"Push interval: {self.push_interval}s")
        print(f"Brewfather key: {self.brewfather_key[:8]}...")
        
        try:
            while True:
                now = time.time()
                if now - self.last_push >= self.push_interval:
                    if self.current["gravity"] > 0:
                        self.push_to_brewfather()
                        self.last_push = now
                    else:
                        print("Waiting for valid data...")
                time.sleep(10)
        except KeyboardInterrupt:
            print("\nSync stopped.")
            self.client.loop_stop()
            self.client.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Brew Sense → Brewfather Sync")
    parser.add_argument("--device-id", "-d", default="brewsense-001",
                       help="Device ID (default: brewsense-001)")
    parser.add_argument("--mqtt", "-m", default="localhost",
                       help="MQTT broker (default: localhost)")
    parser.add_argument("--mqtt-port", type=int, default=1883,
                       help="MQTT port (default: 1883)")
    parser.add_argument("--mqtt-user", help="MQTT username")
    parser.add_argument("--mqtt-pass", help="MQTT password")
    parser.add_argument("--brewfather-key", "-k", required=True,
                       help="Brewfather custom stream key")
    parser.add_argument("--interval", "-i", type=int, default=900,
                       help="Push interval in seconds (default: 900)")
    
    args = parser.parse_args()
    
    sync = BrewfatherSync(
        device_id=args.device_id,
        mqtt_broker=args.mqtt,
        mqtt_port=args.mqtt_port,
        brewfather_key=args.brewfather_key,
        mqtt_user=args.mqtt_user,
        mqtt_pass=args.mqtt_pass,
    )
    sync.push_interval = args.interval
    
    sync.run()


if __name__ == "__main__":
    main()