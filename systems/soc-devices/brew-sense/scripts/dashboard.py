#!/usr/bin/env python3
"""
Brew Sense MQTT Dashboard

Subscribes to Brew Sense MQTT topics and displays a real-time
fermentation monitoring dashboard in the terminal.
"""

import argparse
import sys
import json
import time
from datetime import datetime
from collections import deque

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Please install paho-mqtt: pip install paho-mqtt")
    sys.exit(1)


# Stage names and colors
STAGE_NAMES = {
    "LAG": "⚪ LAG",
    "ACTIVE": "🟢 ACTIVE",
    "PEAK": "🟡 PEAK",
    "SLOWING": "🟠 SLOWING",
    "FINISHED": "🔵 FINISHED",
    "STUCK": "🔴 STUCK",
}

STAGE_COLORS = {
    "LAG": "\033[94m",      # Blue
    "ACTIVE": "\033[92m",   # Green
    "PEAK": "\033[93m",     # Yellow
    "SLOWING": "\033[33m",  # Orange
    "FINISHED": "\033[96m", # Cyan
    "STUCK": "\033[91m",    # Red
}

RESET = "\033[0m"
BOLD = "\033[1m"


class BrewDashboard:
    def __init__(self, device_id, broker, port, username=None, password=None):
        self.device_id = device_id
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password
        
        # Data storage
        self.gravity_history = deque(maxlen=48)
        self.temp_history = deque(maxlen=48)
        self.co2_history = deque(maxlen=48)
        self.ph_history = deque(maxlen=48)
        
        self.current = {
            "gravity": 0.0,
            "temperature": 0.0,
            "co2": 0,
            "ph": 0.0,
            "pressure": 0.0,
            "stage": "UNKNOWN",
            "activity": 0,
            "trend": 0,
            "battery_pct": 0,
        }
        
        self.last_update = None
        self.client = None
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to MQTT broker at {self.broker}:{self.port}")
            # Subscribe to all topics
            topic = f"brewsense/{self.device_id}/#"
            client.subscribe(topic)
            print(f"Subscribed to: {topic}")
        else:
            print(f"Connection failed with code: {rc}")
    
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8", errors="replace")
        
        # Extract metric from topic
        # Format: brewsense/{device_id}/{metric}
        parts = topic.split("/")
        if len(parts) >= 3:
            metric = parts[2]
            
            if metric == "status":
                # JSON payload with all fields
                try:
                    data = json.loads(payload)
                    for key, value in data.items():
                        if key in self.current:
                            self.current[key] = value
                    self.last_update = datetime.now()
                except json.JSONDecodeError:
                    pass
            elif metric == "gravity":
                self.current["gravity"] = float(payload)
                self.gravity_history.append(float(payload))
                self.last_update = datetime.now()
            elif metric == "temperature":
                self.current["temperature"] = float(payload)
                self.temp_history.append(float(payload))
                self.last_update = datetime.now()
            elif metric == "co2":
                self.current["co2"] = int(payload)
                self.co2_history.append(int(payload))
                self.last_update = datetime.now()
            elif metric == "ph":
                self.current["ph"] = float(payload)
                self.ph_history.append(float(payload))
                self.last_update = datetime.now()
            elif metric == "pressure":
                self.current["pressure"] = float(payload)
                self.last_update = datetime.now()
            elif metric == "stage":
                self.current["stage"] = payload.strip()
                self.last_update = datetime.now()
            elif metric == "activity":
                self.current["activity"] = int(float(payload))
                self.last_update = datetime.now()
            elif metric == "trend":
                self.current["trend"] = int(payload)
                self.last_update = datetime.now()
    
    def connect(self):
        self.client = mqtt.Client(client_id=f"brewsense-dashboard-{self.device_id}")
        
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"Failed to connect: {e}")
            sys.exit(1)
    
    def render(self):
        """Render the dashboard to terminal."""
        # Clear screen
        print("\033[2J\033[H", end="")
        
        # Header
        print(f"{BOLD}{'='*60}{RESET}")
        print(f"{BOLD}  🍺 BREW SENSE DASHBOARD — {self.device_id}{RESET}")
        print(f"{BOLD}{'='*60}{RESET}")
        
        if self.last_update:
            print(f"  Last update: {self.last_update.strftime('%H:%M:%S')}")
        else:
            print(f"  Waiting for data...")
        
        print()
        
        # Main readings
        stage = self.current["stage"]
        stage_display = STAGE_NAMES.get(stage, f"❓ {stage}")
        stage_color = STAGE_COLORS.get(stage, "")
        
        print(f"  {BOLD}Specific Gravity:{RESET}  {self.current['gravity']:.4f}")
        print(f"  {BOLD}Temperature:{RESET}       {self.current['temperature']:.1f}°C / "
              f"{self.current['temperature']*9/5+32:.1f}°F")
        print(f"  {BOLD}CO₂:{RESET}              {self.current['co2']} ppm")
        print(f"  {BOLD}pH:{RESET}               {self.current['ph']:.2f}")
        print(f"  {BOLD}Pressure:{RESET}         {self.current['pressure']:.1f} hPa")
        print(f"  {BOLD}Stage:{RESET}            {stage_color}{stage_display}{RESET}")
        print(f"  {BOLD}Activity:{RESET}         {self.current['activity']}%")
        print(f"  {BOLD}Trend:{RESET}            {self.current['trend']}")
        print(f"  {BOLD}Battery:{RESET}          {self.current['battery_pct']}%")
        
        # Gravity mini-graph
        if len(self.gravity_history) > 1:
            print()
            print(f"  {BOLD}Gravity Trend (last {len(self.gravity_history)} readings):{RESET}")
            self._render_graph(self.gravity_history, "SG")
        
        print()
        print(f"{'='*60}")
        print("  Press Ctrl+C to exit")
    
    def _render_graph(self, data, label, width=50, height=10):
        """Render a simple ASCII graph."""
        if len(data) < 2:
            return
        
        values = list(data)
        min_val = min(values)
        max_val = max(values)
        val_range = max_val - min_val
        if val_range < 0.001:
            val_range = 0.001
        
        # Build graph
        rows = []
        for y in range(height, -1, -1):
            row = ""
            threshold = min_val + (y / height) * val_range
            for x, v in enumerate(values):
                x_pos = int(x * width / len(values))
                if x_pos < width:
                    scaled = (v - min_val) / val_range
                    if abs(scaled - y / height) < 1.0 / height:
                        row += "█"
                    else:
                        row += " "
            rows.append(row)
        
        # Print graph with scale
        for i, row in enumerate(rows):
            val = min_val + ((height - i) / height) * val_range
            if i % 2 == 0:
                print(f"  {val:.4f} |{row}|")
            else:
                print(f"         |{row}|")
        
        print(f"          {'─' * width}")
        print(f"          {min_val:.4f}{' ' * (width - 12)}{max_val:.4f}")
    
    def run(self):
        """Run the dashboard with periodic refresh."""
        self.connect()
        print("Connecting to MQTT broker...")
        time.sleep(2)
        
        try:
            while True:
                self.render()
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nDashboard stopped.")
            self.client.loop_stop()
            self.client.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Brew Sense MQTT Dashboard")
    parser.add_argument("--device-id", "-d", default="brewsense-001",
                       help="Device ID (default: brewsense-001)")
    parser.add_argument("--mqtt", "-m", default="localhost",
                       help="MQTT broker address (default: localhost)")
    parser.add_argument("--port", "-p", type=int, default=1883,
                       help="MQTT broker port (default: 1883)")
    parser.add_argument("--username", "-u", help="MQTT username")
    parser.add_argument("--password", "-P", help="MQTT password")
    
    args = parser.parse_args()
    
    dashboard = BrewDashboard(
        device_id=args.device_id,
        broker=args.mqtt,
        port=args.port,
        username=args.username,
        password=args.password,
    )
    
    dashboard.run()


if __name__ == "__main__":
    main()