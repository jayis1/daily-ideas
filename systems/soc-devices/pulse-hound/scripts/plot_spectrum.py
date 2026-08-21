#!/usr/bin/env python3
"""
Pulse Hound — Spectrum Plotter
Plot the live spectrum waterfall from the Pulse Hound BLE stream using matplotlib.

Usage:
    python3 plot_spectrum.py [--device MAC]

Displays a scrolling waterfall + RSSI line graph in real time.
"""

import argparse
import struct
import asyncio
import sys
import time
from collections import deque

import numpy as np

# BLE characteristic UUIDs
UUID_RSSI = "8e7f1a02-b000-1000-8000-00805f9b34fb"
UUID_SPECTRUM = "8e7f1a03-b000-1000-8000-00805f9b34fb"
UUID_BEARING = "8e7f1a04-b000-1000-8000-00805f9b34fb"
UUID_BATTERY = "8e7f1a07-b000-1000-8000-00805f9b34fb"

WATERFALL_ROWS = 64
WATERFALL_COLS = 64  # BLE spectrum row length (sent as 64 bytes)


class PulseHoundPlotter:
    """Real-time spectrum waterfall + RSSI line plotter."""

    def __init__(self):
        self.waterfall = np.zeros((WATERFALL_ROWS, WATERFALL_COLS), dtype=np.uint8)
        self.rssi_history = deque(maxlen=300)  # 30 s at 10 Hz
        self.time_history = deque(maxlen=300)
        self.current_rssi = -80.0
        self.battery_pct = 100
        self.bearing = 0.0

        # Matplotlib setup
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation

        self.fig, (self.ax_wf, self.ax_rssi) = plt.subplots(
            2, 1, figsize=(8, 6), gridspec_kw={"height_ratios": [2, 1]}
        )
        self.fig.suptitle("Pulse Hound — Live Spectrum", fontsize=14)

        # Waterfall subplot
        self.im_wf = self.ax_wf.imshow(
            self.waterfall, aspect="auto", cmap="inferno",
            vmin=0, vmax=255, interpolation="nearest"
        )
        self.ax_wf.set_title("Spectrum Waterfall")
        self.ax_wf.set_xlabel("Column")
        self.ax_wf.set_ylabel("Time (newest at top)")
        self.ax_wf.invert_yaxis()

        # RSSI line subplot
        self.line_rssi, = self.ax_rssi.plot([], [], "b-", linewidth=1)
        self.ax_rssi.set_title("RSSI (dBm)")
        self.ax_rssi.set_xlabel("Time (s)")
        self.ax_rssi.set_ylabel("RSSI (dBm)")
        self.ax_rssi.set_ylim(-85, 10)
        self.ax_rssi.grid(True, alpha=0.3)
        self.rssi_text = self.ax_rssi.text(
            0.02, 0.95, "", transform=self.ax_rssi.transAxes,
            fontsize=10, verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5)
        )

        self.ani = None
        self.client = None

    def notification_handler(self, sender, data):
        uuid = str(sender).lower()
        if UUID_SPECTRUM in uuid:
            # New waterfall row — shift down and insert at top
            row = np.frombuffer(data[:WATERFALL_COLS], dtype=np.uint8)
            if len(row) == WATERFALL_COLS:
                self.waterfall = np.roll(self.waterfall, 1, axis=0)
                self.waterfall[0] = row
        elif UUID_RSSI in uuid:
            if len(data) >= 2:
                val = struct.unpack('<h', data[:2])[0]
                self.current_rssi = val / 100.0
                self.rssi_history.append(self.current_rssi)
                self.time_history.append(time.time())
        elif UUID_BATTERY in uuid:
            if len(data) >= 1:
                self.battery_pct = data[0]
        elif UUID_BEARING in uuid:
            if len(data) >= 4:
                brg = struct.unpack('<H', data[:2])[0]
                self.bearing = brg / 10.0

    def update_plot(self, frame):
        """Animation callback — update the plot."""
        self.im_wf.set_array(self.waterfall)

        # Update RSSI line
        if len(self.rssi_history) > 1:
            t = list(self.time_history)
            t = [x - t[0] for x in t]  # relative time
            self.line_rssi.set_data(t, list(self.rssi_history))
            self.ax_rssi.set_xlim(0, max(t[-1], 1))

        self.rssi_text.set_text(
            f"RSSI: {self.current_rssi:.1f} dBm | BAT: {self.battery_pct}% | BRG: {self.bearing:.0f}°"
        )

        return [self.im_wf, self.line_rssi, self.rssi_text]

    async def run(self, device_addr):
        import matplotlib.pyplot as plt
        from bleak import BleakClient, BleakScanner

        # Scan if needed
        if device_addr is None:
            print("Scanning for 'Pulse Hound'...")
            devices = await BleakScanner.discover(timeout=10.0)
            for d in devices:
                if d.name and "Pulse Hound" in d.name:
                    device_addr = d.address
                    print(f"Found: {d.name} [{d.address}]")
                    break
            if device_addr is None:
                print("No Pulse Hound found.")
                return

        # Connect
        print(f"Connecting to {device_addr}...")
        self.client = BleakClient(device_addr)
        await self.client.connect()
        print(f"Connected: {self.client.is_connected}")

        # Subscribe to notifications
        for uuid in [UUID_RSSI, UUID_SPECTRUM, UUID_BEARING, UUID_BATTERY]:
            await self.client.start_notify(uuid, self.notification_handler)

        # Start animation
        import matplotlib.animation as animation
        self.ani = animation.FuncAnimation(
            self.fig, self.update_plot, interval=100, blit=False, cache_frame_data=False
        )

        plt.show()

        # Cleanup
        for uuid in [UUID_RSSI, UUID_SPECTRUM, UUID_BEARING, UUID_BATTERY]:
            await self.client.stop_notify(uuid)
        await self.client.disconnect()
        print("Disconnected.")


def main():
    parser = argparse.ArgumentParser(description="Pulse Hound Spectrum Plotter")
    parser.add_argument("--device", default=None, help="Device MAC address")
    args = parser.parse_args()

    plotter = PulseHoundPlotter()
    asyncio.run(plotter.run(args.device))


if __name__ == "__main__":
    main()