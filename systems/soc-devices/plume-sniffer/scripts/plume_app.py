#!/usr/bin/env python3
"""plume_app.py — Minimal BLE client + live chromatogram plotter for Plume Sniffer.

Subscribes to the chromatogram and results characteristics, plots the
live chromatogram, and prints the peak table after the run completes.

Usage:
    python3 plume_app.py [--device MAC]

Requirements:
    pip install bleak matplotlib
"""

import argparse
import struct
import sys
import time
from collections import deque

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install bleak:  pip install bleak")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
except ImportError:
    print("Install matplotlib:  pip install matplotlib")
    sys.exit(1)

UUID_CTRL   = "00001841-0000-1000-8000-00805f9b34fb"
UUID_CHROM  = "00001842-0000-1000-8000-00805f9b34fb"
UUID_RESULT = "00001843-0000-1000-8000-00805f9b34fb"

# Library (must match firmware/library.c) — name by index
LIBRARY = [
    "Freon-134a", "Formaldehyde", "Methanol", "Propane", "Acetaldehyde",
    "Butane", "Diethyl ether", "Trimethylamine", "Pentane", "Acetone",
    "Isoprene", "Ethanol", "Isopropanol", "1-Propanol", "Ethyl acetate",
    "Acetic acid", "Dichloromethane", "Chloroform", "Hexane", "MEK",
    "Cyclohexane", "Benzene", "1-Butanol", "Heptane", "Pyridine",
    "Toluene", "Dimethyl disulfide", "Ethylbenzene", "m-Xylene", "o-Xylene",
    "Styrene", "Hexanal", "Butyric acid", "Nonane", "alpha-Pinene",
    "1-Octen-3-ol", "Decane", "Limonene", "Nonanal", "Naphthalene",
]


async def find_device():
    print("Scanning for Plume Sniffer...")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        if "Plume" in (d.name or ""):
            print(f"Found: {d.name} ({d.address})")
            return d.address
    return None


class PlumePlotter:
    def __init__(self):
        self.trace = deque(maxlen=6000)  # 2 min at 50 Hz
        self.peaks = []
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 6))
        self.fig.suptitle("Plume Sniffer — Live Chromatogram")

    def on_chromatogram(self, sender, data: bytearray):
        """Parse 20-float notification and append to trace."""
        n = len(data) // 4
        floats = struct.unpack(f"<{n}f", data[:n*4])
        self.trace.extend(floats)

    def on_results(self, sender, data: bytearray):
        """Parse a 16-byte peak result notification."""
        if len(data) < 14:
            return
        tR, RI, conc = struct.unpack("<3f", data[:12])
        idx = struct.unpack("<h", data[12:14])[0]
        name = LIBRARY[idx] if 0 <= idx < len(LIBRARY) else "unknown"
        self.peaks.append((tR, RI, name, conc))
        print(f"  Peak: tR={tR:.1f}s  RI={RI:.0f}  {name}  {conc:.0f} ppm")

    def update_plot(self, frame):
        self.ax1.clear()
        self.ax1.set_title("TCD Signal (µV)")
        self.ax1.set_xlabel("Sample #")
        self.ax1.set_ylabel("µV (corrected)")
        if self.trace:
            self.ax1.plot(list(self.trace), linewidth=0.5, color='blue')
            self.ax1.axhline(0, color='gray', linewidth=0.3)

        self.ax2.clear()
        self.ax2.set_title("Peak Table")
        self.ax2.axis('off')
        if self.peaks:
            lines = ["tR (s)   RI     Compound          Conc (ppm)"]
            lines.append("-" * 48)
            for tR, RI, name, conc in self.peaks:
                lines.append(f"{tR:7.1f}  {RI:5.0f}  {name:16s}  {conc:8.0f}")
            self.ax2.text(0.05, 0.95, "\n".join(lines),
                         transform=self.ax2.transAxes,
                         fontsize=9, verticalalignment='top',
                         fontfamily='monospace')

    def show(self):
        ani = animation.FuncAnimation(self.fig, self.update_plot,
                                      interval=200, cache_frame_data=False)
        plt.tight_layout()
        plt.show()


async def run_client(address):
    plotter = PlumePlotter()
    async with BleakClient(address, timeout=15.0) as client:
        print(f"Connected to {address}")
        await client.start_notify(UUID_CHROM, plotter.on_chromatogram)
        await client.start_notify(UUID_RESULT, plotter.on_results)
        print("Subscribed to chromatogram + results notifications.")
        print("Press RUN on the device (or send 0x01 to control char).")
        print("Close the plot window to exit.\n")

        plotter.show()

        await client.stop_notify(UUID_CHROM)
        await client.stop_notify(UUID_RESULT)


def main():
    ap = argparse.ArgumentParser(description="Plume Sniffer BLE client + plotter")
    ap.add_argument("--device", help="BLE MAC address")
    args = ap.parse_args()

    import asyncio

    address = args.device
    if not address:
        address = asyncio.run(find_device())
    if not address:
        print("Plume Sniffer not found.")
        return

    asyncio.run(run_client(address))


if __name__ == "__main__":
    main()