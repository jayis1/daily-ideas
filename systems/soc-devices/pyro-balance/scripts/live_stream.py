#!/usr/bin/env python3
"""
Pyro Balance — Live BLE streamer & CSV exporter.
Connects to the Pyro-Balance BLE peripheral, subscribes to the data
characteristic (0x2A01), and plots the live TG/DTG curve. Saves the
run to CSV when the run completes.

Requirements: bleak, matplotlib
    pip install bleak matplotlib

Usage:
    python3 live_stream.py [--save out.csv] [--mac AA:BB:CC:DD:EE:FF]
"""
import argparse
import asyncio
import struct
import csv
import time
from datetime import datetime

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install bleak:  pip install bleak")
    raise

SERVICE_UUID = "00001801-0000-1000-8000-00805f9b34fb"
DATA_UUID     = "00002a01-0000-1000-8000-00805f9b34fb"
CMD_UUID      = "00002a02-0000-1000-8000-00805f9b34fb"

HEADER = 0xAA

def parse_frame(buf: bytes):
    """Parse a Pyro Balance frame. Returns (cmd, payload) or None."""
    if len(buf) < 5 or buf[0] != HEADER:
        return None
    plen = buf[1] | (buf[2] << 8)
    cmd = buf[3]
    if len(buf) < 5 + plen:
        return None
    payload = buf[4:4+plen]
    crc = buf[4+plen]
    calc = 0
    for b in buf[:4+plen]:
        calc ^= b
    if crc != calc:
        return None
    return cmd, payload

def parse_data(payload: bytes):
    """0x01 data point: t_ms(u32) temp(f32) mass_mg(f32) mass_pct(f32) dtg(f32)"""
    if len(payload) < 20:
        return None
    t_ms, temp, mass_mg, mass_pct, dtg = struct.unpack("<Iffff", payload[:20])
    return t_ms / 1000.0, temp, mass_mg, mass_pct, dtg


class PyroBalancePlotter:
    def __init__(self, save_path):
        self.save_path = save_path
        self.points = []
        self.done = False
        try:
            import matplotlib.pyplot as plt
            from matplotlib.animation import FuncAnimation
            self.plt = plt
            self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6))
            self.ax1.set_title("TG curve (mass % vs T)")
            self.ax1.set_xlabel("Temperature (°C)")
            self.ax1.set_ylabel("Mass (%)")
            self.ax1.set_xlim(0, 650)
            self.ax1.set_ylim(0, 105)
            self.ax2.set_title("DTG curve (mass %/min vs T)")
            self.ax2.set_xlabel("Temperature (°C)")
            self.ax2.set_ylabel("DTG (%/min)")
            self.ax2.set_xlim(0, 650)
            self.tg_line, = self.ax1.plot([], [], "b-")
            self.dtg_line, = self.ax2.plot([], [], "r-")
            self.use_mpl = True
        except ImportError:
            print("matplotlib not available; CSV-only mode")
            self.use_mpl = False

    def add_point(self, t_s, temp, mass_mg, mass_pct, dtg):
        self.points.append((t_s, temp, mass_mg, mass_pct, dtg))
        if self.use_mpl and len(self.points) % 5 == 0:
            temps = [p[1] for p in self.points]
            pct   = [p[3] for p in self.points]
            d     = [p[4] for p in self.points]
            self.tg_line.set_data(temps, pct)
            self.dtg_line.set_data(temps, d)
            self.fig.canvas.draw_idle()

    def save(self):
        if not self.save_path:
            return
        with open(self.save_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time_s", "temp_c", "mass_mg", "mass_pct", "dtg_pct_per_min"])
            for p in self.points:
                w.writerow([f"{p[0]:.3f}", f"{p[1]:.3f}", f"{p[2]:.3f}",
                            f"{p[3]:.3f}", f"{p[4]:.4f}"])
        print(f"Saved {len(self.points)} points to {self.save_path}")


async def run(mac, save_path):
    print("Scanning for Pyro-Balance...")
    if mac:
        device = await BleakScanner.find_device_by_address(mac, timeout=15)
    else:
        devices = await BleakScanner.discover(timeout=15)
        device = next((d for d in devices if "Pyro-Balance" in (d.name or "")), None)
    if not device:
        print("Pyro-Balance not found. Provide --mac AA:BB:CC:DD:EE:FF")
        return

    plotter = PyroBalancePlotter(save_path)
    print(f"Connecting to {device.name} ({device.address})...")

    buf = bytearray()
    def notify(sender, data: bytearray):
        buf.extend(data)
        # try to parse frames from buffer
        while len(buf) >= 5:
            result = parse_frame(bytes(buf))
            if result is None:
                buf.clear()
                break
            cmd, payload = result
            fr_len = 5 + len(payload)
            if cmd == 0x01:
                pt = parse_data(payload)
                if pt:
                    plotter.add_point(*pt)
                    print(f"  T={pt[1]:.1f}°C  mass={pt[3]:.2f}%  DTG={pt[4]:.3f}")
            elif cmd == 0x04:
                print("Run complete. Result received.")
                plotter.done = True
            elif cmd == 0x03:
                print(f"[log] {payload.decode('utf-8', errors='replace')}")
            del buf[:fr_len]

    async with BleakClient(device) as client:
        await client.start_notify(DATA_UUID, notify)
        print("Streaming. Ctrl-C to stop.")
        try:
            while not plotter.done:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        await client.stop_notify(DATA_UUID)

    plotter.save()
    if plotter.use_mpl:
        plotter.plt.show()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", default=f"tga_{datetime.now():%Y%m%d_%H%M%S}.csv")
    ap.add_argument("--mac", default=None)
    args = ap.parse_args()
    asyncio.run(run(args.mac, args.save))