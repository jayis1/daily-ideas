#!/usr/bin/env python3
"""
Tremor Tile — LoRa Gateway Data Reader
Reads data from a LoRa gateway (MQTT) and displays structural health status.

Usage:
    python3 read_tremor.py --gateway 192.168.1.100 --topic "tremor/#"

Requires:
    pip install paho-mqtt
"""

import argparse
import json
import sys
from datetime import datetime

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt not installed. Run: pip install paho-mqtt")
    sys.exit(1)

# Packet type definitions
PKT_TYPES = {
    0x01: "HEARTBEAT",
    0x02: "SPECTRAL_SUMMARY",
    0x03: "ALERT",
    0x04: "RAW_DATA",
}

# Anomaly type definitions
ALERT_TYPES = {
    0x01: "NEW_PEAK",
    0x02: "PEAK_SHIFT",
    0x03: "BAND_ENERGY",
    0x04: "RMS_INCREASE",
    0x05: "KURTOSIS",
    0x06: "TAMPER",
    0x07: "TEMPERATURE",
}

# Frequency band names
BAND_NAMES = [
    "0.1-10Hz (very low)",
    "10-50Hz (low)",
    "50-200Hz (mid)",
    "200-500Hz (high)",
    "500-1500Hz (very high)",
]

# Severity colors for terminal
SEVERITY_COLORS = {
    1: "\033[92m",   # Green
    2: "\033[92m",   # Green
    3: "\033[93m",   # Yellow
    4: "\033[93m",   # Yellow
    5: "\033[91m",   # Red
    6: "\033[91m",   # Red
    7: "\033[91m",   # Red
    8: "\033[95m",   # Magenta
    9: "\033[95m",   # Magenta
    10: "\033[1;91m", # Bold Red
}
RESET_COLOR = "\033[0m"


def decode_heartbeat(data):
    """Decode a heartbeat packet (12 bytes)."""
    if len(data) < 5:
        return None
    device_id = (data[1] << 8) | data[2]
    battery_pct = data[3]
    status_flags = data[4]
    return {
        "type": "HEARTBEAT",
        "device_id": device_id,
        "battery_pct": battery_pct,
        "status_flags": f"0x{status_flags:02X}",
    }


def decode_spectral_summary(data):
    """Decode a spectral summary packet (48 bytes)."""
    if len(data) < 48:
        return None

    # Parse peak frequencies and amplitudes (5 peaks × 4 bytes each)
    peaks = []
    for i in range(5):
        freq_offset = 1 + i * 8
        amp_offset = freq_offset + 4

        # IEEE 754 float (big-endian)
        import struct
        freq = struct.unpack('>f', data[freq_offset:freq_offset+4])[0]
        amp = struct.unpack('>f', data[amp_offset:amp_offset+4])[0]
        if freq > 0:
            peaks.append({"freq_hz": round(freq, 1), "amplitude": round(amp, 6)})

    # Parse band energies (5 bands × 4 bytes each)
    band_offset = 1 + 5 * 8
    bands = []
    for i in range(5):
        energy = struct.unpack('>f', data[band_offset + i*4:band_offset + i*4 + 4])[0]
        bands.append({"name": BAND_NAMES[i], "energy": round(energy, 6)})

    # Parse RMS, crest factor, kurtosis
    rms_offset = band_offset + 5 * 4
    rms = struct.unpack('>f', data[rms_offset:rms_offset+4])[0]
    crest = struct.unpack('>f', data[rms_offset+4:rms_offset+8])[0]
    kurtosis = struct.unpack('>f', data[rms_offset+8:rms_offset+12])[0]

    return {
        "type": "SPECTRAL_SUMMARY",
        "peaks": peaks,
        "bands": bands,
        "rms_g": round(rms, 6),
        "crest_factor": round(crest, 3),
        "kurtosis": round(kurtosis, 3),
    }


def decode_alert(data):
    """Decode an alert packet (32 bytes)."""
    if len(data) < 11:
        return None
    device_id = (data[1] << 8) | data[2]
    alert_type = data[3]
    severity = data[4]
    affected_bands = (data[5] << 8) | data[6]

    # Parse timestamp
    import struct
    timestamp = struct.unpack('>I', data[7:11])[0]

    return {
        "type": "ALERT",
        "device_id": device_id,
        "alert_type": ALERT_TYPES.get(alert_type, f"UNKNOWN({alert_type})"),
        "severity": severity,
        "affected_bands": affected_bands,
        "timestamp": timestamp,
    }


def on_connect(client, userdata, flags, rc):
    """MQTT connection callback."""
    if rc == 0:
        print("Connected to gateway MQTT broker")
        client.subscribe(userdata['topic'])
        print(f"Subscribed to: {userdata['topic']}")
    else:
        print(f"Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """MQTT message callback."""
    try:
        data = msg.payload
        if len(data) < 1:
            return

        pkt_type = data[0]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if pkt_type == 0x01:  # HEARTBEAT
            decoded = decode_heartbeat(data)
            if decoded:
                print(f"[{timestamp}] ❤️  HEARTBEAT — Device {decoded['device_id']:04d} "
                      f" Battery: {decoded['battery_pct']}%  "
                      f"Status: {decoded['status_flags']}")

        elif pkt_type == 0x02:  # SPECTRAL_SUMMARY
            decoded = decode_spectral_summary(data)
            if decoded:
                print(f"[{timestamp}] 📊 SPECTRAL SUMMARY")
                print(f"  RMS: {decoded['rms_g']:.6f}g  "
                      f"Crest: {decoded['crest_factor']:.3f}  "
                      f"Kurtosis: {decoded['kurtosis']:.3f}")
                for peak in decoded['peaks']:
                    print(f"  Peak: {peak['freq_hz']:.1f} Hz  "
                          f"Amplitude: {peak['amplitude']:.6f}")
                for band in decoded['bands']:
                    if band['energy'] > 0:
                        print(f"  Band: {band['name']}  "
                              f"Energy: {band['energy']:.6f}")

        elif pkt_type == 0x03:  # ALERT
            decoded = decode_alert(data)
            if decoded:
                color = SEVERITY_COLORS.get(decoded['severity'], "")
                print(f"[{timestamp}] 🚨 ALERT — "
                      f"{color}SEVERITY {decoded['severity']}/10{RESET_COLOR}")
                print(f"  Type: {decoded['alert_type']}")
                print(f"  Device: {decoded['device_id']:04d}")
                print(f"  Affected bands: 0x{decoded['affected_bands']:04X}")

                # Decode affected bands
                for i in range(5):
                    if decoded['affected_bands'] & (1 << i):
                        print(f"    ⚠️  {BAND_NAMES[i]}")

        else:
            print(f"[{timestamp}] ❓ Unknown packet type: 0x{pkt_type:02X} "
                  f"({len(data)} bytes)")

    except Exception as e:
        print(f"Error decoding message: {e}")


def main():
    parser = argparse.ArgumentParser(description="Tremor Tile LoRa Gateway Reader")
    parser.add_argument("--gateway", default="192.168.1.100",
                       help="Gateway MQTT broker IP (default: 192.168.1.100)")
    parser.add_argument("--port", type=int, default=1883,
                       help="MQTT broker port (default: 1883)")
    parser.add_argument("--topic", default="tremor/#",
                       help="MQTT topic (default: tremor/#)")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    args = parser.parse_args()

    client = mqtt.Client(userdata={"topic": args.topic})

    if args.username:
        client.username_pw_set(args.username, args.password)

    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connecting to {args.gateway}:{args.port}...")
    try:
        client.connect(args.gateway, args.port, 60)
        print("Listening for Tremor Tile data... (Ctrl+C to exit)")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\nDisconnected.")
    except Exception as e:
        print(f"Connection error: {e}")


if __name__ == "__main__":
    main()