#!/usr/bin/env python3
"""
Soil Whisper — LoRaWAN Payload Decoder & Dashboard

Decodes Soil Whisper uplink payloads and displays a formatted dashboard.
Can also connect to TTN/ChirpStack MQTT broker for live monitoring.

Usage:
    python soil_whisper_decoder.py --hex <hex_payload>
    python soil_whisper_decoder.py --mqtt --broker <host> --app <app_id> --device <dev_eui>
    python soil_whisper_decoder.py --serial <port>
"""

import argparse
import struct
import sys
import json
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class SoilData:
    """Parsed soil sensor data."""
    flags: int
    moisture_10: float    # % VWC at 10cm
    moisture_20: float    # % VWC at 20cm
    moisture_40: float    # % VWC at 40cm
    temp_10: float        # °C at 10cm
    temp_20: float        # °C at 20cm
    temp_40: float        # °C at 40cm
    no3: float            # ppm nitrate
    po4: float            # ppm phosphate
    k: float              # ppm potassium
    ph: float             # pH
    humidity: float       # %RH (above ground)
    vbat: float           # V (supercap voltage)

    @classmethod
    def decode(cls, data: bytes) -> "SoilData":
        """Decode 21-byte LoRaWAN payload."""
        if len(data) != 21:
            raise ValueError(f"Expected 21 bytes, got {len(data)}")

        flags = data[0]

        m10 = int.from_bytes(data[1:3], "little") * 0.01
        m20 = int.from_bytes(data[3:5], "little") * 0.01
        m40 = int.from_bytes(data[5:7], "little") * 0.01

        t10 = int.from_bytes(data[7:9], "little", signed=True) * 0.01 - 40.0
        t20 = int.from_bytes(data[9:11], "little", signed=True) * 0.01 - 40.0
        t40 = int.from_bytes(data[11:13], "little", signed=True) * 0.01 - 40.0

        no3 = int.from_bytes(data[13:15], "little") * 0.1
        po4 = data[15] * 2.0
        k   = int.from_bytes(data[16:18], "little") * 0.1

        ph  = data[18] * 0.1
        rh  = data[19] * 0.4
        vbat = data[20] * 0.02

        return cls(
            flags=flags,
            moisture_10=round(m10, 2),
            moisture_20=round(m20, 2),
            moisture_40=round(m40, 2),
            temp_10=round(t10, 2),
            temp_20=round(t20, 2),
            temp_40=round(t40, 2),
            no3=round(no3, 1),
            po4=round(po4, 1),
            k=round(k, 1),
            ph=round(ph, 1),
            humidity=round(rh, 1),
            vbat=round(vbat, 2),
        )

    @property
    def flags_dict(self) -> dict:
        return {
            "moisture_valid": bool(self.flags & 0x80),
            "temperature_valid": bool(self.flags & 0x40),
            "npk_valid": bool(self.flags & 0x20),
            "ph_valid": bool(self.flags & 0x10),
            "humidity_valid": bool(self.flags & 0x08),
        }


def dashboard(data: SoilData) -> str:
    """Render a formatted text dashboard."""
    lines = [
        "╔══════════════════════════════════════════════════════════╗",
        "║              SOIL WHISPER — Sensor Dashboard            ║",
        "╠══════════════════════════════════════════════════════════╣",
        "║                                                          ║",
        "║  🌡️  Temperature                                         ║",
        f"║    10 cm:  {data.temp_10:>6.1f} °C                                    ║",
        f"║    20 cm:  {data.temp_20:>6.1f} °C                                    ║",
        f"║    40 cm:  {data.temp_40:>6.1f} °C                                    ║",
        "║                                                          ║",
        "║  💧 Moisture (VWC)                                       ║",
        f"║    10 cm:  {data.moisture_10:>5.1f} %                                      ║",
        f"║    20 cm:  {data.moisture_20:>5.1f} %                                      ║",
        f"║    40 cm:  {data.moisture_40:>5.1f} %                                      ║",
        "║                                                          ║",
        "║  🧪 Nutrients                                            ║",
        f"║    Nitrate (NO₃⁻):   {data.no3:>6.1f} ppm                         ║",
        f"║    Phosphate (PO₄³⁻): {data.po4:>6.1f} ppm                         ║",
        f"║    Potassium (K⁺):   {data.k:>6.1f} ppm                         ║",
        "║                                                          ║",
        "║  ⚗️  pH & Humidity                                       ║",
        f"║    pH:             {data.ph:>4.1f}                                 ║",
        f"║    Humidity:       {data.humidity:>5.1f} %                               ║",
        "║                                                          ║",
        "║  🔋 Power                                                ║",
        f"║    Supercap:       {data.vbat:>4.2f} V                                 ║",
        f"║    Status:         {'🟢 OK' if data.vbat > 3.0 else '🟡 Low' if data.vbat > 2.5 else '🔴 Critical'}                                     ║",
        "║                                                          ║",
        "╚══════════════════════════════════════════════════════════╝",
    ]
    return "\n".join(lines)


def assess_soil_health(data: SoilData) -> dict:
    """Provide basic soil health assessment based on readings."""
    assessment = {
        "moisture": {},
        "nutrients": {},
        "ph": {},
        "overall": "unknown",
    }

    # Moisture assessment (general ranges for most crops)
    avg_moisture = (data.moisture_10 + data.moisture_20 + data.moisture_40) / 3
    if avg_moisture < 20:
        assessment["moisture"]["status"] = "dry"
        assessment["moisture"]["recommendation"] = "Irrigation recommended"
    elif avg_moisture < 40:
        assessment["moisture"]["status"] = "optimal"
        assessment["moisture"]["recommendation"] = "Moisture level is good"
    elif avg_moisture < 60:
        assessment["moisture"]["status"] = "moist"
        assessment["moisture"]["recommendation"] = "No irrigation needed"
    else:
        assessment["moisture"]["status"] = "waterlogged"
        assessment["moisture"]["recommendation"] = "Drainage may be needed"

    # NPK assessment
    assessment["nutrients"]["nitrogen"] = "sufficient" if data.no3 > 20 else "low" if data.no3 < 10 else "moderate"
    assessment["nutrients"]["phosphorus"] = "sufficient" if data.po4 > 15 else "low" if data.po4 < 5 else "moderate"
    assessment["nutrients"]["potassium"] = "sufficient" if data.k > 100 else "low" if data.k < 50 else "moderate"

    # pH assessment
    if 6.0 <= data.ph <= 7.5:
        assessment["ph"]["status"] = "optimal"
        assessment["ph"]["recommendation"] = "pH is in ideal range for most crops"
    elif 5.5 <= data.ph < 6.0:
        assessment["ph"]["status"] = "slightly_acidic"
        assessment["ph"]["recommendation"] = "Consider lime application"
    elif data.ph < 5.5:
        assessment["ph"]["status"] = "acidic"
        assessment["ph"]["recommendation"] = "Lime application recommended"
    elif 7.5 < data.ph <= 8.0:
        assessment["ph"]["status"] = "slightly_alkaline"
        assessment["ph"]["recommendation"] = "Monitor for nutrient lockout"
    else:
        assessment["ph"]["status"] = "alkaline"
        assessment["ph"]["recommendation"] = "Sulfur amendment may be needed"

    # Overall
    issues = 0
    if assessment["moisture"]["status"] in ("dry", "waterlogged"):
        issues += 1
    if any(v == "low" for v in assessment["nutrients"].values()):
        issues += 1
    if assessment["ph"]["status"] not in ("optimal", "slightly_acidic", "slightly_alkaline"):
        issues += 1

    if issues == 0:
        assessment["overall"] = "healthy"
    elif issues == 1:
        assessment["overall"] = "attention_needed"
    else:
        assessment["overall"] = "intervention_required"

    return assessment


def main():
    parser = argparse.ArgumentParser(description="Soil Whisper LoRaWAN Payload Decoder")
    parser.add_argument("--hex", help="Hex-encoded payload string (e.g., 'F8560D340BAD...')")
    parser.add_argument("--base64", help="Base64-encoded payload")
    parser.add_argument("--mqtt", action="store_true", help="Connect to MQTT broker for live data")
    parser.add_argument("--serial", help="Serial port for live data (e.g., /dev/ttyUSB0)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--assess", action="store_true", help="Include soil health assessment")
    parser.add_argument("--broker", default="eu1.cloud.thethings.network", help="MQTT broker")
    parser.add_argument("--app", help="TTN application ID")
    parser.add_argument("--device", help="Device EUI")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate")

    args = parser.parse_args()

    # Decode from hex or base64
    if args.hex:
        payload = bytes.fromhex(args.hex)
        data = SoilData.decode(payload)
    elif args.base64:
        import base64
        payload = base64.b64decode(args.base64)
        data = SoilData.decode(payload)
    elif args.serial:
        # Live serial mode
        import serial
        ser = serial.Serial(args.serial, args.baud, timeout=1)
        print(f"Connected to {args.serial} at {args.baud} baud")
        print("Waiting for Soil Whisper data...")
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("PAYLOAD:"):
                hex_str = line.split(":")[1].strip()
                payload = bytes.fromhex(hex_str)
                data = SoilData.decode(payload)
                if args.json:
                    print(json.dumps(asdict(data), indent=2))
                else:
                    print(dashboard(data))
                    if args.assess:
                        assessment = assess_soil_health(data)
                        print(json.dumps(assessment, indent=2))
        return
    elif args.mqtt:
        # MQTT mode
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            print("Error: paho-mqtt not installed. Run: pip install paho-mqtt")
            sys.exit(1)

        def on_connect(client, userdata, flags, rc):
            topic = f"v3/{args.app}@{args.tenant}/devices/{args.device}/up"
            client.subscribe(topic)
            print(f"Subscribed to {topic}")

        def on_message(client, userdata, msg):
            try:
                j = json.loads(msg.payload)
                payload = bytes.fromhex(j["uplink_message"]["f_port"])
                # Actually, TTN provides frm_payload in base64
                import base64
                payload = base64.b64decode(j["uplink_message"]["frm_payload"])
                data = SoilData.decode(payload)
                if args.json:
                    print(json.dumps(asdict(data), indent=2))
                else:
                    print(dashboard(data))
            except Exception as e:
                print(f"Error decoding: {e}")

        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(args.broker, 1883, 60)
        print(f"Connecting to MQTT broker at {args.broker}...")
        client.loop_forever()
        return
    else:
        # Demo mode with example data
        example = bytes([
            0xF8,       # flags
            0x56, 0x0D,  # moisture 10cm
            0x34, 0x0B,  # moisture 20cm
            0xAD, 0x08,  # moisture 40cm
            0xE8, 0x13,  # temp 10cm
            0xC4, 0x10,  # temp 20cm
            0x9C, 0x0E,  # temp 40cm
            0xC4, 0x01,  # NO3
            0x06,        # PO4
            0xB1, 0x07,  # K
            0x40,        # pH
            0x9B,        # RH
            0xAA,        # VBat
        ])
        data = SoilData.decode(example)

    if args.json:
        output = asdict(data)
        if args.assess:
            output["assessment"] = assess_soil_health(data)
        print(json.dumps(output, indent=2))
    else:
        print(dashboard(data))
        if args.assess:
            assessment = assess_soil_health(data)
            print("\n--- Soil Health Assessment ---")
            print(json.dumps(assessment, indent=2))


if __name__ == "__main__":
    main()