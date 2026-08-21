#!/usr/bin/env python3
"""
Echo Trap — dashboard.py

Decode Echo Trap LoRaWAN uplinks from a TTN/Chirpstack HTTP integration
(or from a file of raw hex payloads) and plot species counts over time.

Usage:
    # From a TTN webhook (runs a local HTTP server):
    python dashboard.py --webhook --port 8080

    # From a file of hex payloads (one per line):
    python dashboard.py --file uplinks.txt

    # From a live MQTT subscription:
    python dashboard.py --mqtt --broker thethings.network.com \
        --app-id myapp --dev-id echotrap-01

Requires: matplotlib, numpy
    pip install matplotlib numpy

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import struct
import sys
from datetime import datetime
from collections import defaultdict

import numpy as np

SPECIES_NAMES = [
    "Aedes", "Culex", "Anopheles", "Honeybee", "Drosophila",
    "Codling Moth", "Armyworm", "Housefly", "Wasp",
    "Lacewing", "Hoverfly", "Unknown",
]


def decode_summary(payload: bytes):
    """Decode a summary uplink payload (20 bytes)."""
    if len(payload) < 20:
        return None
    ptype = payload[0]
    if ptype != 0x01:
        return None
    return {
        'type': 'summary',
        'battery': payload[1],
        'temperature_c': payload[2] - 40,
        'humidity_pct': payload[3],
        'target_captures': struct.unpack_from(">H", payload, 4)[0],
        'beneficial_sighted': struct.unpack_from(">H", payload, 6)[0],
        'species_counts': [payload[8 + i] for i in range(12)],
    }


def decode_detection(payload: bytes):
    """Decode a detection uplink payload (8 bytes)."""
    if len(payload) < 8:
        return None
    ptype = payload[0]
    if ptype != 0x02:
        return None
    return {
        'type': 'detection',
        'species_id': payload[1],
        'timestamp_s': struct.unpack_from(">I", payload, 2)[0],
        'temperature_c': payload[6] - 40,
        'humidity_pct': payload[7],
    }


def decode_payload(hex_str: str):
    """Decode a hex payload string."""
    try:
        payload = bytes.fromhex(hex_str.strip())
    except ValueError:
        return None
    if len(payload) == 0:
        return None
    if payload[0] == 0x01:
        return decode_summary(payload)
    elif payload[0] == 0x02:
        return decode_detection(payload)
    return None


def plot_dashboard(summaries, detections):
    """Plot the species count dashboard."""
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    # 1. Species counts over time (stacked bar)
    if summaries:
        times = [s['time'] for s in summaries]
        counts = np.array([s['species_counts'] for s in summaries])

        # Stack only non-zero species
        non_zero = counts.sum(axis=0) > 0
        labels = [SPECIES_NAMES[i] for i in range(12) if non_zero[i]]
        data = counts[:, non_zero]

        axes[0].stackplot(range(len(times)), data.T, labels=labels, alpha=0.8)
        axes[0].set_ylabel('Insect Count')
        axes[0].set_title('Species Counts per Reporting Period')
        axes[0].legend(loc='upper left', fontsize=7, ncol=3)
        axes[0].set_xticks(range(len(times)))
        axes[0].set_xticklabels([t.strftime('%H:%M') for t in times],
                                 rotation=45, fontsize=7)

    # 2. Target captures + beneficial sightings
    if summaries:
        times = [s['time'] for s in summaries]
        targets = [s['target_captures'] for s in summaries]
        beneficials = [s['beneficial_sighted'] for s in summaries]
        axes[1].plot(range(len(times)), targets, 'r-o', label='Target pests', markersize=3)
        axes[1].plot(range(len(times)), beneficials, 'g-s', label='Beneficials', markersize=3)
        axes[1].set_ylabel('Count')
        axes[1].set_title('Target Captures vs Beneficial Sightings')
        axes[1].legend()

    # 3. Environmental data
    if summaries:
        times = [s['time'] for s in summaries]
        temps = [s['temperature_c'] for s in summaries]
        humids = [s['humidity_pct'] for s in summaries]
        bats = [s['battery'] for s in summaries]

        ax3 = axes[2]
        ax3.plot(range(len(times)), temps, 'b-o', label='Temp (°C)', markersize=3)
        ax3.set_ylabel('Temperature (°C)', color='b')
        ax3.tick_params(axis='y', labelcolor='b')

        ax3b = ax3.twinx()
        ax3b.plot(range(len(times)), humids, 'c-s', label='RH (%)', markersize=3)
        ax3b.set_ylabel('Humidity (%)', color='c')
        ax3b.tick_params(axis='y', labelcolor='c')

        ax3.set_title('Environmental Conditions')
        ax3.legend(loc='upper left')
        ax3b.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig('echo_trap_dashboard.png', dpi=150)
    print("Dashboard saved to echo_trap_dashboard.png")
    plt.show()


def run_webhook_server(port: int):
    """Run a local HTTP server to receive TTN/Chirpstack webhooks."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json

    summaries = []
    detections = []

    class WebhookHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)
            try:
                data = json.loads(body)
                # TTN v3 webhook format
                uplink = data.get('uplink_message', {})
                payload_hex = uplink.get('frm_payload', '')
                if payload_hex:
                    import base64
                    payload = base64.b64decode(payload_hex)
                    decoded = decode_payload(payload.hex())
                    if decoded:
                        decoded['time'] = datetime.now()
                        if decoded['type'] == 'summary':
                            summaries.append(decoded)
                            print(f"[{decoded['time']}] Summary: "
                                  f"bat={decoded['battery']}% "
                                  f"T={decoded['temperature_c']}°C "
                                  f"targets={decoded['target_captures']}")
                        else:
                            detections.append(decoded)
                            species = SPECIES_NAMES[decoded['species_id']]
                            print(f"[{decoded['time']}] Detection: {species}")
            except Exception as e:
                print(f"Error: {e}")
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass  # suppress default logging

    server = HTTPServer(('', port), WebhookHandler)
    print(f"Webhook server listening on port {port}")
    print(f"Configure your TTN/Chirpstack webhook to POST to http://your-ip:{port}/")
    print("Press Ctrl+C to stop and show dashboard.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nGenerating dashboard...")
        plot_dashboard(summaries, detections)


def run_from_file(filename: str):
    """Decode uplinks from a file (one hex payload per line)."""
    summaries = []
    detections = []
    with open(filename) as f:
        for i, line in enumerate(f):
            decoded = decode_payload(line)
            if decoded:
                decoded['time'] = datetime.now()  # placeholder
                if decoded['type'] == 'summary':
                    summaries.append(decoded)
                    print(f"Summary: bat={decoded['battery']}% "
                          f"targets={decoded['target_captures']} "
                          f"counts={decoded['species_counts']}")
                else:
                    detections.append(decoded)
                    species = SPECIES_NAMES[decoded['species_id']]
                    print(f"Detection: {species}")
    if summaries or detections:
        plot_dashboard(summaries, detections)
    else:
        print("No valid uplinks found in file.")


def main():
    parser = argparse.ArgumentParser(description='Echo Trap LoRaWAN dashboard')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--webhook', action='store_true', help='Run webhook server')
    group.add_argument('--file', help='Decode uplinks from a file')
    group.add_argument('--mqtt', action='store_true', help='Subscribe via MQTT')
    parser.add_argument('--port', type=int, default=8080, help='Webhook port')
    parser.add_argument('--broker', help='MQTT broker')
    parser.add_argument('--app-id', help='TTN app ID')
    parser.add_argument('--dev-id', help='TTN device ID')
    args = parser.parse_args()

    if args.webhook:
        run_webhook_server(args.port)
    elif args.file:
        run_from_file(args.file)
    elif args.mqtt:
        print("MQTT mode not yet implemented — use --webhook or --file")


if __name__ == '__main__':
    main()