#!/usr/bin/env python3
"""
Sap Watch — Transpiration Plotter

Connects to a Chirpstack/TTN HTTP integration, fetches Sap Watch uplinks,
and plots daily transpiration curves, sap-flux velocity, and drought-stress
flags over time using matplotlib.

Usage:
    python plot_transpiration.py --ttn-region eu1 --app-id sap-watch \\
        --device-id dev-001 --days 7 --api-key YOUR_API_KEY

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("Install 'requests' first: pip install requests", file=sys.stderr)
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Install 'matplotlib' first: pip install matplotlib", file=sys.stderr)
    sys.exit(1)


def decode_uplink(f_port: int, payload_b64: str) -> Optional[dict]:
    """Decode a Sap Watch uplink payload (base64)."""
    import base64
    import struct

    raw = base64.b64decode(payload_b64)

    if f_port == 1 and len(raw) >= 19:
        off = 0
        sap_flux = struct.unpack(">h", raw[off:off+2])[0] / 100.0; off += 2
        daily_t = struct.unpack(">H", raw[off:off+2])[0] / 100.0; off += 2
        sapwood_t = struct.unpack(">h", raw[off:off+2])[0] / 100.0; off += 2
        air_t = struct.unpack(">h", raw[off:off+2])[0] / 100.0; off += 2
        rh = struct.unpack(">H", raw[off:off+2])[0] / 100.0; off += 2
        lux = struct.unpack(">H", raw[off:off+2])[0]; off += 2
        vpd = struct.unpack(">H", raw[off:off+2])[0] / 100.0; off += 2
        bat = raw[off]; off += 1
        health = raw[off]; off += 1
        count = struct.unpack(">H", raw[off:off+2])[0]; off += 2
        flags = raw[off]; off += 1
        return {
            "sap_flux": sap_flux,
            "daily_trans": daily_t,
            "sapwood_temp": sapwood_t,
            "air_temp": air_t,
            "humidity": rh,
            "light": lux,
            "vpd": vpd,
            "battery": bat,
            "drought_stress": bool(flags & 0x01),
        }
    elif f_port == 2:
        # Alert — return alert_type
        if len(raw) >= 1:
            return {"alert_type": raw[0]}
    return None


def fetch_ttn_uplinks(region: str, app_id: str, device_id: str,
                       api_key: str, days: int):
    """Fetch uplinks from The Things Network (TTN) v3 API."""
    base = f"https://{region}.cloud.thethings.network/api/v3"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    url = f"{base}/applications/{app_id}/devices/{device_id}/data"
    params = {"limit": 1000, "start": start.isoformat()}

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    uplinks = []
    for entry in resp.json().get("uplinks", []):
        decoded = decode_uplink(entry["f_port"], entry["uplink_message"]["frm_payload"])
        if decoded:
            decoded["timestamp"] = entry["received_at"]
            uplinks.append(decoded)
    return uplinks


def fetch_csv_uplinks(csv_path: str):
    """Fetch uplinks from a CSV file (columns: timestamp, f_port, payload_b64)."""
    import csv
    uplinks = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            decoded = decode_uplink(int(row["f_port"]), row["payload_b64"])
            if decoded:
                decoded["timestamp"] = row["timestamp"]
                uplinks.append(decoded)
    return uplinks


def plot_data(uplinks: list, device_id: str):
    """Plot sap flow, transpiration, and stress flags."""
    times = [u["timestamp"] for u in uplinks if "sap_flux" in u and isinstance(u["sap_flux"], (int, float))]
    flux = [u["sap_flux"] for u in uplinks if "sap_flux" in u and isinstance(u["sap_flux"], (int, float))]
    daily = [u["daily_trans"] for u in uplinks if "daily_trans" in u and isinstance(u["daily_trans"], (int, float))]
    stress_flags = [u for u in uplinks if u.get("drought_stress") or u.get("alert_type") == 1]

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(f"Sap Watch — {device_id}", fontsize=14)

    ax1.plot(times, flux, "g-o", markersize=3, linewidth=0.8)
    ax1.set_ylabel("Sap Flux Velocity (cm/h)")
    ax1.set_title("Real-time Sap Flow")
    ax1.grid(True, alpha=0.3)

    ax2.plot(times, daily, "b-o", markersize=3, linewidth=0.8)
    ax2.set_ylabel("Daily Transpiration (L)")
    ax2.set_title("Cumulative Daily Water Use")
    ax2.grid(True, alpha=0.3)

    # Drought stress markers
    for sf in stress_flags:
        ts = sf["timestamp"]
        ax3.axvline(x=ts, color="r", linewidth=2, alpha=0.5)
    ax3.set_ylabel("Drought Stress Events")
    ax3.set_title("Anomaly Alerts (red lines)")
    ax3.grid(True, alpha=0.3)

    plt.xlabel("Time")
    plt.tight_layout()
    output = f"sap_watch_{device_id}.png"
    plt.savefig(output, dpi=150)
    print(f"Plot saved to {output}")


def main():
    parser = argparse.ArgumentParser(description="Sap Watch transpiration plotter")
    parser.add_argument("--device-id", required=True, help="Device ID")
    parser.add_argument("--days", type=int, default=7, help="Days of data to fetch")
    parser.add_argument("--ttn-region", default="eu1", help="TTN region (eu1, nam1, etc.)")
    parser.add_argument("--app-id", default="sap-watch", help="TTN application ID")
    parser.add_argument("--api-key", help="TTN API key")
    parser.add_argument("--csv", help="Alternative: read uplinks from CSV file")
    args = parser.parse_args()

    if args.csv:
        uplinks = fetch_csv_uplinks(args.csv)
    elif args.api_key:
        uplinks = fetch_ttn_uplinks(args.ttn_region, args.app_id,
                                     args.device_id, args.api_key, args.days)
    else:
        print("Either --api-key (TTN) or --csv (local file) required", file=sys.stderr)
        sys.exit(1)

    if not uplinks:
        print("No uplinks found", file=sys.stderr)
        sys.exit(1)

    print(f"Fetched {len(uplinks)} uplinks")
    plot_data(uplinks, args.device_id)


if __name__ == "__main__":
    main()