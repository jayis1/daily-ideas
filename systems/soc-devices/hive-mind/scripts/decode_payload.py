#!/usr/bin/env python3
"""
Hive Mind — LoRaWAN Payload Decoder
Decodes the 21-byte binary payload from Hive Mind uplinks.

SPDX-License-Identifier: MIT
Copyright (c) 2026 jayis1

Usage:
    python3 decode_payload.py --hex "0BAC1A1C202082049600140001E0018C073E"
    python3 decode_payload.py --base64 "C6wYHCggggmAF..."
"""

import argparse
import struct
import sys
import json

ACOUSTIC_CLASSES = {
    0: "QUEENRIGHT",
    1: "QUEENLESS",
    2: "SWARMING",
    3: "FANNING",
    4: "PIPING",
    5: "ROBBING",
    6: "CLUSTERING",
    7: "DEAD",
}

def decode_temp(byte_val):
    """Decode temperature from byte: 0.5°C resolution, offset -20°C"""
    return round(byte_val * 0.5 - 20.0, 1)

def decode_voltage(byte_val):
    """Decode voltage from byte: 0.02V resolution"""
    return round(byte_val * 0.02, 2)

def decode_payload(data: bytes) -> dict:
    """Decode a 21-byte Hive Mind LoRaWAN payload."""
    if len(data) != 21:
        raise ValueError(f"Expected 21 bytes, got {len(data)}")

    idx = 0

    # Bytes 0-1: Hive weight (g), big-endian uint16
    weight_g = struct.unpack_from('>H', data, idx)[0]
    idx += 2

    # Bytes 2-4: Temperatures (floor, mid, crown)
    temp_floor = decode_temp(data[idx]); idx += 1
    temp_mid = decode_temp(data[idx]); idx += 1
    temp_crown = decode_temp(data[idx]); idx += 1

    # Byte 5: Ambient temperature
    ambient_t = decode_temp(data[idx]); idx += 1

    # Bytes 6-7: Ambient humidity (0.01%)
    ambient_h = round(struct.unpack_from('>H', data, idx)[0] / 100.0, 2)
    idx += 2

    # Bytes 8-9: Ambient pressure (0.1 hPa)
    ambient_p = round(struct.unpack_from('>H', data, idx)[0] / 10.0, 1)
    idx += 2

    # Byte 10: Acoustic class
    acoustic_class = ACOUSTIC_CLASSES.get(data[idx], "UNKNOWN")
    acoustic_class_id = data[idx]; idx += 1

    # Byte 11: Dominant frequency (×10 Hz)
    dominant_freq = data[idx] * 10; idx += 1

    # Bytes 12-13: Bee traffic in
    bee_in = struct.unpack_from('>H', data, idx)[0]; idx += 2

    # Bytes 14-15: Bee traffic out
    bee_out = struct.unpack_from('>H', data, idx)[0]; idx += 2

    # Byte 16: Battery voltage
    battery_v = decode_voltage(data[idx]); idx += 1

    # Byte 17: Solar voltage
    solar_v = decode_voltage(data[idx]); idx += 1

    # Bytes 18-19: Uptime hours
    uptime_h = struct.unpack_from('>H', data, idx)[0]; idx += 2

    # Byte 20: Health score (0-100)
    health_score = data[idx]; idx += 1

    return {
        "weight_g": weight_g,
        "weight_kg": round(weight_g / 1000.0, 2),
        "temp_floor_c": temp_floor,
        "temp_mid_c": temp_mid,
        "temp_crown_c": temp_crown,
        "ambient_t_c": ambient_t,
        "ambient_h_pct": ambient_h,
        "ambient_p_hpa": ambient_p,
        "acoustic_class": acoustic_class,
        "acoustic_class_id": acoustic_class_id,
        "dominant_freq_hz": dominant_freq,
        "bee_in": bee_in,
        "bee_out": bee_out,
        "activity_ratio": round(bee_in / bee_out, 2) if bee_out > 0 else None,
        "battery_v": battery_v,
        "solar_v": solar_v,
        "uptime_h": uptime_h,
        "health_score": health_score,
        "health_label": get_health_label(health_score),
    }

def get_health_label(score):
    if score >= 80: return "EXCELLENT"
    if score >= 60: return "GOOD"
    if score >= 40: return "FAIR"
    if score >= 20: return "POOR"
    return "CRITICAL"

def main():
    parser = argparse.ArgumentParser(description="Decode Hive Mind LoRaWAN payload")
    parser.add_argument("--hex", help="Hex-encoded payload string")
    parser.add_argument("--base64", help="Base64-encoded payload string")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    data = None

    if args.hex:
        hex_str = args.hex.replace(" ", "")
        data = bytes.fromhex(hex_str)
    elif args.base64:
        import base64
        data = base64.b64decode(args.base64)
    else:
        parser.print_help()
        sys.exit(1)

    result = decode_payload(data)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Hive Mind Payload Decoder")
        print(f"=========================")
        print(f"Weight:          {result['weight_kg']} kg ({result['weight_g']} g)")
        print(f"Temp floor:      {result['temp_floor_c']}°C")
        print(f"Temp mid:        {result['temp_mid_c']}°C")
        print(f"Temp crown:      {result['temp_crown_c']}°C")
        print(f"Ambient T:       {result['ambient_t_c']}°C")
        print(f"Ambient H:       {result['ambient_h_pct']}%")
        print(f"Ambient P:       {result['ambient_p_hpa']} hPa")
        print(f"Acoustic class:  {result['acoustic_class']} (id={result['acoustic_class_id']})")
        print(f"Dominant freq:   {result['dominant_freq_hz']} Hz")
        print(f"Bee traffic in:  {result['bee_in']}")
        print(f"Bee traffic out: {result['bee_out']}")
        if result['activity_ratio']:
            print(f"Activity ratio:  {result['activity_ratio']}")
        print(f"Battery:         {result['battery_v']} V")
        print(f"Solar:           {result['solar_v']} V")
        print(f"Uptime:          {result['uptime_h']} hours")
        print(f"Health score:    {result['health_score']}/100 ({result['health_label']})")

if __name__ == "__main__":
    main()