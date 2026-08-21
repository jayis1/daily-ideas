#!/usr/bin/env python3
"""
halo_pin_app.py — BLE companion app for Halo Pin optical particle counter.

Connects to the ESP32-C3 BLE bridge on the Halo Pin device,
subscribes to the status GATT characteristic, and displays:
  - PM1, PM2.5, PM10 mass concentration (µg/m³)
  - 16-bin particle histogram (bar chart)
  - Flow rate (L/min), temperature, humidity, pressure
  - Battery voltage
  - Live time-series plot of PM2.5

Usage:
    python3 halo_pin_app.py [--device MAC] [--log FILE.csv]

Requires: bleak (pip install bleak), matplotlib (pip install matplotlib)
"""

import argparse
import asyncio
import struct
import sys
import time
from collections import deque

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install: pip install bleak", file=sys.stderr)
    sys.exit(1)

# GATT characteristic UUIDs (matching ESP32-C3 firmware)
UUID_STATUS = "00002a01-0000-1000-8000-00805f9b34fb"  # status + PM values
UUID_HIST   = "00002a02-0000-1000-8000-00805f9b34fb"  # 16-bin histogram
UUID_CMD    = "00002a03-0000-1000-8000-00805f9b34fb"  # command write

# Size bin edges (µm) — must match firmware calibration.c
BIN_EDGES = [0.30, 0.40, 0.50, 0.70, 1.00, 1.30, 1.70, 2.20,
             3.00, 4.00, 5.00, 7.00, 10.0, 15.0, 20.0, 30.0, 40.0]
BIN_MIDPOINTS = [(BIN_EDGES[i] + BIN_EDGES[i+1]) / 2 for i in range(16)]


class HaloPinData:
    """Parsed data from the Halo Pin status characteristic."""
    def __init__(self):
        self.pm1 = 0.0
        self.pm25 = 0.0
        self.pm10 = 0.0
        self.flow = 0.0
        self.battery = 0.0
        self.state = 0
        self.counts = [0] * 16
        self.timestamp = time.time()

    def parse_status(self, data: bytes):
        """Parse the S:<state>,B:<batt>,F:<flow>,1:<pm1>,25:<pm25>,10:<pm10>,H:<hist> string."""
        text = data.decode("ascii", errors="replace").strip()
        # Expected: S:1,B:3.85,F:1.02,1:2.3,25:8.1,10:12.5,H:0,0,5,12,...
        parts = {}
        for token in text.split(","):
            if ":" in token:
                key, val = token.split(":", 1)
                parts[key.strip()] = val.strip()
        self.state = int(parts.get("S", 0))
        self.battery = float(parts.get("B", 0))
        self.flow = float(parts.get("F", 0))
        self.pm1 = float(parts.get("1", 0))
        self.pm25 = float(parts.get("25", 0))
        self.pm10 = float(parts.get("10", 0))
        if "H" in parts:
            counts = parts["H"].rstrip(",").split(",")
            self.counts = [int(c) if c.strip().isdigit() else 0 for c in counts[:16]]
        self.timestamp = time.time()

    def number_concentration(self):
        """Compute number concentration (#/L) per bin from counts and flow."""
        if self.flow < 0.01:
            return [0.0] * 16
        vol_l = self.flow / 60.0  # L/s (assume 1 s interval)
        return [c / vol_l if vol_l > 0 else 0 for c in self.counts]

    def mass_concentration_estimate(self):
        """Independent mass estimate from histogram (for cross-check)."""
        import math
        rho = 1.65e-3  # g/cm³ → µg/µm³ factor
        total = 0.0
        for i, d in enumerate(BIN_MIDPOINTS):
            n_per_l = self.counts[i] / (self.flow / 60.0) if self.flow > 0 else 0
            vol_cm3 = (math.pi / 6.0) * (d / 1e4) ** 3
            mass_ug = 1.65 * vol_cm3 * 1e6
            total += n_per_l * mass_ug * 1000  # #/L → #/m³
        return total


def print_table(data: HaloPinData):
    """Print a simple text table to the terminal."""
    print(f"\n{'='*50}")
    print(f"  HALO PIN  |  {time.strftime('%H:%M:%S', time.localtime(data.timestamp))}")
    print(f"{'='*50}")
    print(f"  State:     {['IDLE','SAMPLING','CALIB'][data.state] if data.state < 3 else '?'}")
    print(f"  Battery:   {data.battery:.2f} V")
    print(f"  Flow:      {data.flow:.2f} L/min")
    print(f"  PM1:       {data.pm1:6.1f} µg/m³")
    print(f"  PM2.5:     {data.pm25:6.1f} µg/m³  {'⚠' if data.pm25 > 25 else '✓'}")
    print(f"  PM10:      {data.pm10:6.1f} µg/m³  {'⚠' if data.pm10 > 50 else '✓'}")
    print(f"  {'─'*46}")
    print(f"  Histogram (counts per 1 s):")
    max_c = max(data.counts) if data.counts else 1
    for i, c in enumerate(data.counts):
        bar = "█" * int(c / max_c * 30) if max_c > 0 else ""
        print(f"  {BIN_EDGES[i]:5.2f}-{BIN_EDGES[i+1]:5.2f}µm  {c:5d}  {bar}")
    print(f"{'='*50}")


async def run(device_addr: str, log_file: str, duration: float):
    """Connect, subscribe, and display data."""
    print(f"Scanning for Halo Pin...")
    if not device_addr:
        devices = await BleakScanner.discover(timeout=10.0)
        halo = [d for d in devices if "HaloPin" in (d.name or "")]
        if not halo:
            print("Halo Pin not found. Provide --device MAC.")
            for d in devices:
                print(f"  {d.address}  {d.name}")
            return
        device_addr = halo[0].address
        print(f"Found Halo Pin at {device_addr}")

    print(f"Connecting to {device_addr}...")
    async with BleakClient(device_addr) as client:
        print("Connected!")
        data = HaloPinData()
        log_fp = open(log_file, "a") if log_file else None
        if log_fp:
            log_fp.write("# timestamp,pm1,pm25,pm10,flow,battery,"
                         + ",".join(f"bin_{BIN_EDGES[i]:.2f}" for i in range(16))
                         + "\n")

        start = time.time()
        while time.time() - start < duration:
            try:
                raw = await client.read_gatt_char(UUID_STATUS)
                data.parse_status(raw)
                print_table(data)
                if log_fp:
                    log_fp.write(f"{data.timestamp:.1f},{data.pm1:.1f},"
                                 f"{data.pm25:.1f},{data.pm10:.1f},"
                                 f"{data.flow:.2f},{data.battery:.2f},"
                                 + ",".join(str(c) for c in data.counts)
                                 + "\n")
                    log_fp.flush()
            except Exception as e:
                print(f"Read error: {e}", file=sys.stderr)
            await asyncio.sleep(1.0)

        if log_fp:
            log_fp.close()
        print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Halo Pin BLE companion app")
    parser.add_argument("--device", default="", help="BLE MAC address")
    parser.add_argument("--log", default="", help="Log CSV file")
    parser.add_argument("--duration", type=float, default=3600,
                       help="Run duration in seconds (default 3600)")
    args = parser.parse_args()
    asyncio.run(run(args.device, args.log, args.duration))


if __name__ == "__main__":
    main()