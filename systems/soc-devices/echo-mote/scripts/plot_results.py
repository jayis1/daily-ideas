#!/usr/bin/env python3
"""
plot_results.py — Read Echo Mote measurement results via BLE and plot them.

Usage:
    python3 plot_results.py --mac AA:BB:CC:DD:EE:FF --mode rt60
    python3 plot_results.py --mac AA:BB:CC:DD:EE:FF --mode freq --export freq.csv
    python3 plot_results.py --compare room1.json room2.json
"""

import argparse
import asyncio
import json
import struct
import sys

try:
    from bleak import BleakClient
except ImportError:
    print("Install bleak: pip install bleak")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Install matplotlib + numpy: pip install matplotlib numpy")
    sys.exit(1)


# BLE UUIDs
SERVICE_UUID = "0000ffb0-0000-1000-8000-00805f9b34fb"
CHAR_RT60     = "0000ffb2-0000-1000-8000-00805f9b34fb"
CHAR_FREQ     = "0000ffb3-0000-1000-8000-00805f9b34fb"
CHAR_MODES    = "0000ffb4-0000-1000-8000-00805f9b34fb"
CHAR_CLARITY  = "0000ffb5-0000-1000-8000-00805f9b34fb"
CHAR_NC       = "0000ffb6-0000-1000-8000-00805f9b34fb"
CHAR_STATUS   = "0000ffb7-0000-1000-8000-00805f9b34fb"
CHAR_BATTERY  = "0000ffb8-0000-1000-8000-00805f9b34fb"

OCTAVE_CENTERS = [125, 250, 500, 1000, 2000, 4000]
THIRD_OCT_CENTERS = [
    20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160,
    200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
    2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000
]


async def read_rt60(client):
    """Read RT60 results from BLE characteristic."""
    data = await client.read_gatt_char(CHAR_RT60)
    rt60_values = struct.unpack("<6f", data)
    return rt60_values


async def read_clarity(client):
    """Read clarity indices from BLE characteristic."""
    data = await client.read_gatt_char(CHAR_CLARITY)
    c50 = struct.unpack("<6b", data[:6])
    c80 = struct.unpack("<6b", data[6:12])
    return c50, c80


async def read_modes(client):
    """Read room modes from BLE characteristic."""
    data = await client.read_gatt_char(CHAR_MODES)
    modes = []
    for i in range(0, min(len(data), 32), 4):
        if i + 3 < len(data):
            freq = struct.unpack_from("<H", data, i)[0]
            decay_type = struct.unpack_from("<H", data, i + 2)[0]
            decay_raw = decay_type >> 4
            mode_type = decay_type & 0x0F
            modes.append({
                "freq": freq,
                "decay": decay_raw * 0.01,
                "type": ["axial", "tangential", "oblique"][mode_type] if mode_type < 3 else "unknown"
            })
    return modes


async def read_battery(client):
    """Read battery level."""
    data = await client.read_gatt_char(CHAR_BATTERY)
    return data[0]


async def read_status(client):
    """Read device status."""
    data = await client.read_gatt_char(CHAR_STATUS)
    status_names = {0: "idle", 1: "measuring", 2: "streaming", 3: "error"}
    return status_names.get(data[0], f"unknown({data[0]})")


def plot_rt60(rt60_values, title="RT60 Results"):
    """Plot RT60 bar chart."""
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#2ecc71" if v < 0.6 else "#f39c12" if v < 1.0 else "#e74c3c"
              for v in rt60_values]
    bars = ax.bar(range(6), rt60_values, color=colors, edgecolor="black", linewidth=0.5)
    ax.set_xticks(range(6))
    ax.set_xticklabels([f"{f} Hz" for f in OCTAVE_CENTERS])
    ax.set_ylabel("RT60 (seconds)")
    ax.set_title(title)
    ax.axhline(y=0.6, color="green", linestyle="--", alpha=0.5, label="Optimal (≤0.6s)")
    ax.axhline(y=1.0, color="orange", linestyle="--", alpha=0.5, label="Acceptable (≤1.0s)")
    ax.legend()
    for bar, val in zip(bars, rt60_values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{val:.2f}s", ha="center", va="bottom", fontsize=9)
    plt.tight_layout()
    plt.show()


def plot_clarity(c50, c80):
    """Plot C50 and C80 bar charts."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    colors50 = ["#2ecc71" if v > 0 else "#e74c3c" for v in c50]
    ax1.bar(range(6), c50, color=colors50, edgecolor="black", linewidth=0.5)
    ax1.set_xticks(range(6))
    ax1.set_xticklabels([f"{f} Hz" for f in OCTAVE_CENTERS])
    ax1.set_ylabel("C50 (dB)")
    ax1.set_title("C50 — Speech Clarity")
    ax1.axhline(y=0, color="black", linestyle="-", alpha=0.3)

    colors80 = ["#2ecc71" if v > 0 else "#e74c3c" for v in c80]
    ax2.bar(range(6), c80, color=colors80, edgecolor="black", linewidth=0.5)
    ax2.set_xticks(range(6))
    ax2.set_xticklabels([f"{f} Hz" for f in OCTAVE_CENTERS])
    ax2.set_ylabel("C80 (dB)")
    ax2.set_title("C80 — Music Clarity")
    ax2.axhline(y=0, color="black", linestyle="-", alpha=0.3)

    plt.tight_layout()
    plt.show()


def plot_modes(modes):
    """Plot room modes as frequency-domain markers."""
    fig, ax = plt.subplots(figsize=(10, 4))
    if not modes:
        ax.text(0.5, 0.5, "No room modes detected", ha="center", va="center",
                transform=ax.transAxes)
    else:
        for m in modes:
            color = {"axial": "#e74c3c", "tangential": "#f39c12",
                     "oblique": "#3498db"}.get(m["type"], "#95a5a6")
            ax.axvline(x=m["freq"], color=color, linewidth=2, alpha=0.7)
            ax.text(m["freq"], 0.5 + modes.index(m) * 0.1,
                    f"{m['freq']:.0f} Hz\n{m['type']}", ha="center", fontsize=8)

        ax.legend(handles=[
            plt.Line2D([0], [0], color="#e74c3c", linewidth=2, label="Axial"),
            plt.Line2D([0], [0], color="#f39c12", linewidth=2, label="Tangential"),
            plt.Line2D([0], [0], color="#3498db", linewidth=2, label="Oblique"),
        ])

    ax.set_xlabel("Frequency (Hz)")
    ax.set_xlim(20, 300)
    ax.set_title("Room Modes")
    plt.tight_layout()
    plt.show()


def compare_rooms(room1_data, room2_data):
    """Compare RT60 between two rooms."""
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(6)
    width = 0.35
    ax.bar(x - width / 2, room1_data["rt60"], width, label="Room 1", color="#3498db")
    ax.bar(x + width / 2, room2_data["rt60"], width, label="Room 2", color="#e74c3c")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{f} Hz" for f in OCTAVE_CENTERS])
    ax.set_ylabel("RT60 (seconds)")
    ax.set_title("RT60 Comparison")
    ax.legend()
    plt.tight_layout()
    plt.show()


async def main(args):
    if args.compare:
        with open(args.compare[0]) as f:
            room1 = json.load(f)
        with open(args.compare[1]) as f:
            room2 = json.load(f)
        compare_rooms(room1, room2)
        return

    if not args.mac:
        print("Error: --mac is required for BLE connection")
        sys.exit(1)

    async with BleakClient(args.mac) as client:
        print(f"Connected to {args.mac}")
        battery = await read_battery(client)
        status = await read_status(client)
        print(f"Battery: {battery}%, Status: {status}")

        if args.mode == "rt60":
            rt60 = await read_rt60(client)
            print(f"RT60: {rt60}")
            plot_rt60(rt60)
            if args.export:
                with open(args.export, "w") as f:
                    json.dump({"rt60": list(rt60)}, f, indent=2)

        elif args.mode == "clarity":
            c50, c80 = await read_clarity(client)
            print(f"C50: {c50}, C80: {c80}")
            plot_clarity(c50, c80)

        elif args.mode == "modes":
            modes = await read_modes(client)
            print(f"Room modes: {modes}")
            plot_modes(modes)

        else:
            print(f"Mode '{args.mode}' — reading all available data")
            rt60 = await read_rt60(client)
            c50, c80 = await read_clarity(client)
            modes = await read_modes(client)
            results = {
                "rt60": list(rt60),
                "c50": list(c50),
                "c80": list(c80),
                "room_modes": modes,
                "battery": battery,
            }
            print(json.dumps(results, indent=2))
            if args.export:
                with open(args.export, "w") as f:
                    json.dump(results, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Echo Mote BLE Results Reader")
    parser.add_argument("--mac", help="Device MAC address")
    parser.add_argument("--mode", default="all",
                        choices=["rt60", "freq", "modes", "clarity", "noise", "all"],
                        help="Measurement mode to read")
    parser.add_argument("--export", help="Export results to file (CSV/JSON)")
    parser.add_argument("--compare", nargs=2, metavar=("ROOM1", "ROOM2"),
                        help="Compare two room result JSON files")
    args = parser.parse_args()
    asyncio.run(main(args))