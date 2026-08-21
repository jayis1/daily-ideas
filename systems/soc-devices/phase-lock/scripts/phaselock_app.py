#!/usr/bin/env python3
"""
phaselock_app.py — minimal BLE client / plotter for Phase Lock.

Connects to the Phase Lock device over BLE, subscribes to the Demod
Data (0xFFE1) and Sweep Data (0xFFE2) characteristics, and plots the
live R/Theta/X/Y time-trace or the swept Bode plot (magnitude + phase).

Requires: bleak, matplotlib

Usage:
    python phaselock_app.py                  # auto-scan + connect
    python phaselock_app.py --addr XX:XX:XX:XX:XX:XX
    python phaselock_app.py --sweep           # start a frequency sweep on connect
"""
import argparse
import asyncio
import struct
from collections import deque

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install: pip install bleak matplotlib")
    raise SystemExit(1)

import matplotlib.pyplot as plt

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
DEMOD_UUID   = "0000ffe1-0000-1000-8000-00805f9b34fb"
SWEEP_UUID   = "0000ffe2-0000-1000-8000-00805f9b34fb"
CMD_UUID    = "0000ffe4-0000-1000-8000-00805f9b34fb"

DEMO_FMT = struct.Struct("<Bffff f f")   # tag, freq, gain, R, theta, X, Y, noise
SWEEP_FMT = struct.Struct("<Bff f f f f I")  # tag, f, a, R, theta, X, Y, noise, ts

class PhaseLockPlotter:
    def __init__(self):
        self.t = deque(maxlen=1000)
        self.R = deque(maxlen=1000)
        self.theta = deque(maxlen=1000)
        self.noise = deque(maxlen=1000)
        self.swp_f = []
        self.swp_R = []
        self.swp_theta = []
        self.mode = "demod"

    def handle_demod(self, _, data):
        if len(data) < DEMO_FMT.size:
            return
        tag, freq, gain, R, theta, X, Y, noise = DEMO_FMT.unpack(data[:DEMO_FMT.size])
        self.t.append(len(self.t))
        self.R.append(R)
        self.theta.append(theta * 57.2958)
        self.noise.append(noise * 1e9)

    def handle_sweep(self, _, data):
        if len(data) < SWEEP_FMT.size:
            return
        tag, f, a, R, theta, X, Y, noise, ts = SWEEP_FMT.unpack(data[:SWEEP_FMT.size])
        self.swp_f.append(f)
        self.swp_R.append(R)
        self.swp_theta.append(theta * 57.2958)
        self.mode = "sweep"

    def plot(self):
        plt.ion()
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
        while True:
            ax1.clear(); ax2.clear()
            if self.mode == "demod" and self.t:
                ax1.plot(self.t, self.R, 'b-', label='R (V)')
                ax1.set_ylabel('R (V)')
                ax2.plot(self.t, self.theta, 'r-', label='Theta (deg)')
                ax2.set_ylabel('Theta (deg)')
                ax2.set_xlabel('sample')
            elif self.mode == "sweep" and self.swp_f:
                ax1.semilogx(self.swp_f, self.swp_R, 'b-o', label='|Z| (V)')
                ax1.set_ylabel('|Z| (V)')
                ax2.semilogx(self.swp_f, self.swp_theta, 'r-o', label='Phase (deg)')
                ax2.set_ylabel('Phase (deg)')
                ax2.set_xlabel('frequency (Hz)')
            ax1.legend(); ax2.legend()
            fig.canvas.draw()
            fig.canvas.flush_events()
            plt.pause(0.1)

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--addr", help="BLE MAC address")
    ap.add_argument("--sweep", action="store_true", help="start a freq sweep on connect")
    args = ap.parse_args()

    plotter = PhaseLockPlotter()

    addr = args.addr
    if not addr:
        print("Scanning for Phase Lock...")
        devices = await BleakScanner.discover(timeout=10)
        for d in devices:
            if "Phase" in (d.name or ""):
                addr = d.address
                print(f"Found: {d.name} @ {addr}")
                break
        if not addr:
            print("Phase Lock not found. Pass --addr manually.")
            return

    async with BleakClient(addr) as client:
        print(f"Connected to {addr}")
        await client.start_notify(DEMOD_UUID, plotter.handle_demod)
        await client.start_notify(SWEEP_UUID, plotter.handle_sweep)

        if args.sweep:
            print("Starting frequency sweep...")
            await client.write_gatt_char(CMD_UUID, b"SWP")

        plotter.plot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass