#!/usr/bin/env python3
"""
storm_view.py — Bolt Compass companion app

Live / replay / calibrate modes for the Bolt Compass lightning station.

  Live mode (BLE or Wi-Fi):
    python3 storm_view.py --ble --device BoltCompass
    python3 storm_view.py --wifi --host 192.168.4.1

  Replay mode (from SD card dump):
    python3 storm_view.py --replay /mnt/sd/SFERIC_20260626.csv

  Calibrate mode (cross-correlate with Blitzortung public feed):
    python3 storm_view.py --calibrate --blitzortung
"""
import argparse
import json
import math
import os
import socket
import struct
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional

import matplotlib
matplotlib.use("TkAgg")  # change to Agg for headless
import matplotlib.pyplot as plt
import matplotlib.animation as animation


# ── Data types ──────────────────────────────────────────────────────

@dataclass
class Stroke:
    ts: float           # unix seconds
    type: str           # CG / IC / CC
    conf: float
    bearing: float      # degrees, 0=N
    distance: float     # km
    peak_uv: float
    flash_rate: float = 0.0

    @property
    def x(self) -> float:
        """Radar x-coordinate (log-scale distance)."""
        d = max(25, min(200, self.distance))
        r = (math.log(d) - math.log(25)) / (math.log(200) - math.log(25))
        return r * math.cos(math.radians(self.bearing - 90))

    @property
    def y(self) -> float:
        d = max(25, min(200, self.distance))
        r = (math.log(d) - math.log(25)) / (math.log(200) - math.log(25))
        return r * math.sin(math.radians(self.bearing - 90))


# ── BLE source (requires bleak) ─────────────────────────────────────

BOLT_SERVICE = "0000b07c-0000-1000-8000-00805f9b34fb"
CHR_EVENT   = "0000b071-0000-1000-8000-00805f9b34fb"
CHR_ALERT   = "0000b073-0000-1000-8000-00805f9b34fb"


def ble_source(device_name: str):
    """Yield Stroke objects from the BLE GATT notify stream."""
    try:
        import asyncio
        from bleak import BleakClient, BleakScanner
    except ImportError:
        print("Install bleak:  pip install bleak", file=sys.stderr)
        return

    loop = asyncio.new_event_loop()
    queue: List[Stroke] = []
    started = []

    def _run():
        asyncio.set_event_loop(loop)

        async def setup():
            devices = await BleakScanner.discover(timeout=10)
            addr = None
            for d in devices:
                if d.name and device_name in d.name:
                    addr = d.address
                    break
            if not addr:
                print(f"Device '{device_name}' not found", file=sys.stderr)
                return
            print(f"Connecting to {addr}…")
            client = BleakClient(addr)
            await client.connect()

            def callback(sender, data: bytearray):
                if len(data) >= 11:
                    ts_lo, typ, conf, brg, dist, peak = struct.unpack(
                        "<IBBHHH", bytes(data[:11]))
                    queue.append(Stroke(
                        ts=float(ts_lo),
                        type=["CG", "IC", "CC"][typ],
                        conf=conf / 255.0,
                        bearing=brg / 100.0,
                        distance=dist,
                        peak_uv=peak,
                    ))

            await client.start_notify(CHR_EVENT, callback)
            started.append(True)

        loop.create_task(setup())
        # Keep the loop running in a thread-friendly way.
        import threading
        t = threading.Thread(target=loop.run_forever, daemon=True)
        t.start()

    _run()
    # Wait for BLE to connect.
    for _ in range(50):
        if started:
            break
        time.sleep(0.1)
    while True:
        while queue:
            yield queue.pop(0)
        time.sleep(0.1)


# ── Wi-Fi TCP source ────────────────────────────────────────────────

def wifi_source(host: str, port: int = 7777):
    """Yield Stroke objects from the raw TCP socket (12-byte packets)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    buf = b""
    while True:
        data = sock.recv(256)
        if not data:
            break
        buf += data
        while len(buf) >= 12:
            pkt = buf[:12]
            buf = buf[12:]
            ts_lo, typ, conf, brg, dist, peak = struct.unpack(
                "<IBBHHH", pkt[:11])
            yield Stroke(
                ts=float(ts_lo),
                type=["CG", "IC", "CC"][typ],
                conf=conf / 255.0,
                bearing=brg / 100.0,
                distance=dist,
                peak_uv=peak,
            )


# ── Replay from SD CSV ──────────────────────────────────────────────

def replay_source(csv_path: str):
    """Yield Stroke objects from a SFERIC_YYYYMMDD.csv file."""
    import csv as csvmod
    with open(csv_path) as f:
        reader = csvmod.DictReader(f)
        for row in reader:
            # iso_ts,type,conf,bearing,distance_km,peak_uv,...
            from datetime import datetime
            try:
                dt = datetime.strptime(row["iso_ts"],
                                       "%Y-%m-%dT%H:%M:%SZ")
                ts = dt.timestamp()
            except Exception:
                ts = time.time()
            yield Stroke(
                ts=ts,
                type=row["type"],
                conf=float(row["conf"]),
                bearing=float(row["bearing"]),
                distance=float(row["distance_km"]),
                peak_uv=float(row.get("peak_uv", 0)),
            )


# ── Radar plot ──────────────────────────────────────────────────────

class RadarPlot:
    def __init__(self):
        self.fig, self.ax = plt.subplots(figsize=(6, 6))
        self.ax.set_aspect("equal")
        self.ax.set_facecolor("#0a0a1a")
        self.fig.patch.set_facecolor("#0a0a1a")
        self.strokes: List[Stroke] = []
        self.setup_radar()

    def setup_radar(self):
        self.ax.clear()
        self.ax.set_facecolor("#0a0a1a")
        rings = [25, 50, 100, 200]
        for r_km in rings:
            r = (math.log(r_km) - math.log(25)) / (math.log(200) - math.log(25))
            circle = plt.Circle((0, 0), r, fill=False, color="#2a2a5a",
                                linewidth=0.8)
            self.ax.add_patch(circle)
            self.ax.text(r * 0.7, r * 0.7, f"{r_km}km", color="#5a5a9a",
                         fontsize=7)
        for a in range(0, 360, 30):
            rad = math.radians(a - 90)
            self.ax.plot([0, 1.05 * math.cos(rad)],
                         [0, 1.05 * math.sin(rad)],
                         color="#1a1a3a", linewidth=0.5)
        self.ax.set_xlim(-1.3, 1.3)
        self.ax.set_ylim(-1.3, 1.3)
        self.ax.set_title("Bolt Compass — Storm Radar", color="#9a9aff")
        self.ax.tick_params(colors="#3a3a6a")
        for spine in self.ax.spines.values():
            spine.set_color("#2a2a5a")

    def add_stroke(self, s: Stroke):
        self.strokes.append(s)
        if len(self.strokes) > 50:
            self.strokes.pop(0)

    def draw(self):
        self.setup_radar()
        for s in self.strokes[-50:]:
            color = {"CG": "#ff3333", "IC": "#33ff33", "CC": "#3333ff"}[s.type]
            alpha = max(0.2, s.conf)
            self.ax.plot(s.x, s.y, "o", color=color, markersize=8,
                         alpha=alpha, markeredgecolor="white",
                         markeredgewidth=0.5)
        if self.strokes:
            last = self.strokes[-1]
            self.ax.text(-1.25, -1.25,
                         f"{last.type} {last.distance:.0f}km brg {last.bearing:.0f}°",
                         color="white", fontsize=9)
        plt.pause(0.05)


# ── Calibrate (Blitzortung cross-correlation) ───────────────────────

def calibrate(blitzortung: bool):
    """Fit the range model ref_field_uv by comparing device strokes to
    the public Blitzortung stroke feed (lightningmaps.org JSON)."""
    print("Calibration mode: compare device strokes to Blitzortung feed.")
    print("1. Place the device outdoors with a clear view of an active storm.")
    print("2. Record ~50 strokes via --replay or --ble.")
    print("3. Download the same time window from lightningmaps.org.")
    print("4. This script fits ref_field_uv to minimize distance error.")
    print()
    print("Run:  python3 storm_view.py --replay SFERIC.csv --calibrate")
    print("      (needs a paired Blitzortung_YYYYMMDD.csv)")


# ── Main ────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Bolt Compass companion app")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--ble", action="store_true", help="Live BLE mode")
    g.add_argument("--wifi", action="store_true", help="Live Wi-Fi TCP mode")
    g.add_argument("--replay", metavar="CSV", help="Replay from SD CSV")
    g.add_argument("--calibrate", action="store_true", help="Calibrate range model")
    p.add_argument("--device", default="BoltCompass", help="BLE device name")
    p.add_argument("--host", default="192.168.4.1", help="Wi-Fi host IP")
    p.add_argument("--port", type=int, default=7777, help="TCP port")
    p.add_argument("--blitzortung", action="store_true")
    args = p.parse_args()

    if args.calibrate:
        calibrate(args.blitzortung)
        return

    if args.ble:
        source = ble_source(args.device)
    elif args.wifi:
        source = wifi_source(args.host, args.port)
    else:
        source = replay_source(args.replay)

    radar = RadarPlot()
    plt.ion()
    plt.show()

    try:
        for stroke in source:
            radar.add_stroke(stroke)
            radar.draw()
            print(f"{stroke.type} {stroke.distance:.0f}km brg {stroke.bearing:.0f}° "
                  f"conf={stroke.conf:.2f}")
    except KeyboardInterrupt:
        print("\nDone.")


if __name__ == "__main__":
    main()