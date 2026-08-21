#!/usr/bin/env python3
"""
Sap Watch — LoRaWAN Uplink Decoder

Decodes port-1 (periodic report) and port-2 (anomaly alert) uplink payloads
into human-readable JSON.

Usage:
    python decode_uplink.py --port 1 --hex 0802 04E2 07D0 0A28 1770 4E20 00DC 53 13 012C 01
    python decode_uplink.py --port 1 --base64 AUIETuQKKBd3ATBC
    python decode_uplink.py --port 2 --hex 01 0802 0032 0802 28

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import json
import struct
import sys
import base64
from datetime import datetime, timezone


def decode_port1(data: bytes) -> dict:
    """Decode a port-1 periodic report (19 bytes)."""
    if len(data) < 19:
        raise ValueError(f"Port 1 payload must be 19 bytes, got {len(data)}")

    off = 0
    sap_flux_raw = struct.unpack(">h", data[off:off+2])[0]; off += 2
    daily_trans_raw = struct.unpack(">H", data[off:off+2])[0]; off += 2
    sapwood_temp_raw = struct.unpack(">h", data[off:off+2])[0]; off += 2
    air_temp_raw = struct.unpack(">h", data[off:off+2])[0]; off += 2
    humidity_raw = struct.unpack(">H", data[off:off+2])[0]; off += 2
    light_raw = struct.unpack(">H", data[off:off+2])[0]; off += 2
    vpd_raw = struct.unpack(">H", data[off:off+2])[0]; off += 2
    battery_pct = data[off]; off += 1
    probe_health = data[off]; off += 1
    meas_count = struct.unpack(">H", data[off:off+2])[0]; off += 2
    flags = data[off]; off += 1

    health_bits = {
        "heater_ok":      bool(probe_health & 0x01),
        "adc_ok":         bool(probe_health & 0x02),
        "therm1_ok":      bool(probe_health & 0x04),
        "therm2_ok":      bool(probe_health & 0x08),
        "zero_cal_valid": bool(probe_health & 0x10),
    }
    flag_bits = {
        "drought_stress": bool(flags & 0x01),
        "heater_fault":   bool(flags & 0x02),
        "low_battery":    bool(flags & 0x04),
    }

    return {
        "port": 1,
        "type": "periodic_report",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sap_flux_velocity_cmh":   sap_flux_raw / 100.0,
        "daily_transpiration_L":  daily_trans_raw / 100.0,
        "sapwood_temp_c":          sapwood_temp_raw / 100.0,
        "air_temp_c":              air_temp_raw / 100.0,
        "humidity_pct":            humidity_raw / 100.0,
        "light_lux":               light_raw,
        "vpd_kpa":                 vpd_raw / 100.0,
        "battery_pct":             battery_pct,
        "probe_health":            health_bits,
        "measurement_count":       meas_count,
        "flags":                   flag_bits,
    }


def decode_port2(data: bytes) -> dict:
    """Decode a port-2 anomaly alert (8 bytes)."""
    if len(data) < 8:
        raise ValueError(f"Port 2 payload must be 8 bytes, got {len(data)}")

    alert_types = {
        1: "DROUGHT_STRESS",
        2: "HEATER_FAULT",
        3: "PROBE_DISCONNECT",
        4: "LOW_BATTERY",
    }
    off = 0
    alert_type = data[off]; off += 1
    sap_flux = struct.unpack(">h", data[off:off+2])[0] / 100.0; off += 2
    predawn = struct.unpack(">h", data[off:off+2])[0] / 100.0; off += 2
    midday = struct.unpack(">h", data[off:off+2])[0] / 100.0; off += 2
    ratio_pct = data[off]; off += 1

    return {
        "port": 2,
        "type": "anomaly_alert",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "alert_type": alert_types.get(alert_type, f"UNKNOWN({alert_type})"),
        "sap_flux_velocity_cmh": sap_flux,
        "predawn_flux_cmh":      predawn,
        "midday_flux_cmh":       midday,
        "midday_to_predawn_ratio_pct": ratio_pct,
    }


def main():
    parser = argparse.ArgumentParser(description="Sap Watch LoRaWAN uplink decoder")
    parser.add_argument("--port", type=int, choices=[1, 2], required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hex", nargs="+", help="Hex bytes (space-separated)")
    group.add_argument("--base64", help="Base64-encoded payload")
    args = parser.parse_args()

    if args.hex:
        data = bytes(int(h, 16) for h in args.hex)
    else:
        data = base64.b64decode(args.base64)

    if args.port == 1:
        result = decode_port1(data)
    else:
        result = decode_port2(data)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()