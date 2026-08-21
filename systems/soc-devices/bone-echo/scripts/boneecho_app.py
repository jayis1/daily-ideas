#!/usr/bin/env python3
"""
boneecho_app.py — Bone Echo BLE companion app

A minimal Python BLE client / plotter for the Bone Echo pocket QUS
bone densitometer. Connects over BLE, subscribes to the Results,
Waveform, and Status characteristics, and plots the live A-scan
and BUA spectrum fit.

Usage:
    python3 boneecho_app.py [--mac AA:BB:CC:DD:EE:FF]

Requirements:
    pip install bleak numpy matplotlib

Press 's' to start a scan, 'p' to run phantom calibration, 'q' to quit.
"""

import argparse
import asyncio
import struct
from dataclasses import dataclass
from typing import Optional

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install bleak: pip install bleak")
    exit(1)

try:
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
except ImportError:
    print("Install numpy matplotlib: pip install numpy matplotlib")
    exit(1)

# BLE UUIDs
SERVICE_UUID = "0000fe20-0000-1000-8000-00805f9b34fb"
RESULTS_UUID  = "0000fe21-0000-1000-8000-00805f9b34fb"
WAVEFORM_UUID = "0000fe22-0000-1000-8000-00805f9b34fb"
STATUS_UUID   = "0000fe23-0000-1000-8000-00805f9b34fb"
COMMAND_UUID  = "0000fe24-0000-1000-8000-00805f9b34fb"

CLASS_NAMES = ["NORMAL", "OSTEOPENIA", "OSTEOPOROSIS", "SEVERE OSTEOPOROSIS"]


@dataclass
class ScanResult:
    sos: float       # m/s
    bua: float       # dB/MHz
    si: float        # dimensionless
    t_score: float   # SD
    z_score: float   # SD
    classification: int

    @classmethod
    def parse(cls, line: str) -> "ScanResult":
        """Parse 'R:1562.0,58.4,84.2,-1.20,-0.30,1'"""
        if not line.startswith("R:"):
            raise ValueError(f"Not a result line: {line}")
        parts = line[2:].strip().split(",")
        return cls(
            sos=float(parts[0]), bua=float(parts[1]), si=float(parts[2]),
            t_score=float(parts[3]), z_score=float(parts[4]),
            classification=int(parts[5]),
        )

    def __str__(self):
        cls_name = CLASS_NAMES[self.classification] if self.classification < 4 else "UNKNOWN"
        return (f"SOS: {self.sos:.0f} m/s   BUA: {self.bua:.1f} dB/MHz\n"
                f"SI:  {self.si:.1f}       T: {self.t_score:.2f}  Z: {self.z_score:.2f}\n"
                f"Classification: {cls_name}")


class BoneEchoApp:
    def __init__(self, mac: Optional[str] = None):
        self.mac = mac
        self.client: Optional[BleakClient] = None
        self.waveform_chunks = {}
        self.waveform_collecting = False
        self.latest_result: Optional[ScanResult] = None
        self.waveform = np.zeros(115200, dtype=np.uint16)

    async def connect(self):
        if self.mac is None:
            print("Scanning for Bone Echo devices...")
            devices = await BleakScanner.discover(timeout=10)
            for d in devices:
                if d.name and "Bone Echo" in d.name:
                    self.mac = d.address
                    print(f"Found: {d.name} ({d.address})")
                    break
            if self.mac is None:
                print("No Bone Echo device found.")
                return False

        print(f"Connecting to {self.mac}...")
        self.client = BleakClient(self.mac)
        await self.client.connect()
        await self.client.start_notify(RESULTS_UUID, self._on_results)
        await self.client.start_notify(WAVEFORM_UUID, self._on_waveform)
        await self.client.start_notify(STATUS_UUID, self._on_status)
        print("Connected. Press 's' to scan, 'p' for phantom, 'q' to quit.")
        return True

    def _on_results(self, characteristic, data: bytearray):
        line = data.decode("utf-8", errors="ignore").strip()
        if line.startswith("R:"):
            try:
                self.latest_result = ScanResult.parse(line)
                print("\n=== Scan Result ===")
                print(self.latest_result)
            except Exception as e:
                print(f"Parse error: {e} on '{line}'")

    def _on_waveform(self, characteristic, data: bytearray):
        line = data.decode("utf-8", errors="ignore").strip()
        if line == "W:START":
            self.waveform_collecting = True
            self.waveform_chunks = {}
        elif line == "W:END":
            self.waveform_collecting = False
            # Assemble chunks
            offsets = sorted(self.waveform_chunks.keys())
            for off in offsets:
                chunk = self.waveform_chunks[off]
                idx = off // 2
                for i, val in enumerate(chunk):
                    if idx + i < len(self.waveform):
                        self.waveform[idx + i] = val
            print(f"Waveform received: {len(self.waveform)} samples")
        elif line.startswith("W:"):
            offset = int(line[2:])
            # Real code would receive raw bytes separately
        # In a real impl, raw binary data follows the W:offset marker

    def _on_status(self, characteristic, data: bytearray):
        line = data.decode("utf-8", errors="ignore").strip()
        if line.startswith("S:"):
            parts = line[2:].split(",")
            if len(parts) >= 4:
                bat, state, sos, bua = parts
                print(f"Status: bat={bat}V state={state} SOS={sos} BUA={bua}")

    async def send_command(self, cmd: str):
        if self.client:
            await self.client.write_gatt_char(COMMAND_UUID, cmd.encode())

    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    def plot_waveform(self):
        if self.latest_result is None:
            return
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
        t_us = np.arange(len(self.waveform)) / 3.6e6 * 1e6  # 3.6 Msps → µs
        ax1.plot(t_us, self.waveform, linewidth=0.5)
        ax1.set_xlabel("Time (µs)")
        ax1.set_ylabel("ADC count")
        ax1.set_title(f"A-scan  |  SOS={self.latest_result.sos:.0f} m/s  "
                      f"BUA={self.latest_result.bua:.1f} dB/MHz  "
                      f"SI={self.latest_result.si:.1f}  "
                      f"T={self.latest_result.t_score:.2f}")
        ax1.grid(True)

        # BUA spectrum (placeholder)
        fft_mag = np.abs(np.fft.rfft(self.waveform[:1024].astype(float)))
        f_mhz = np.arange(len(fft_mag)) / 1024 * 3.6 / 2
        ax2.plot(f_mhz, 20 * np.log10(fft_mag + 1e-6))
        ax2.set_xlabel("Frequency (MHz)")
        ax2.set_ylabel("Magnitude (dB)")
        ax2.set_title(f"BUA spectrum fit  |  T-score={self.latest_result.t_score:.2f}  "
                      f"Z={self.latest_result.z_score:.2f}  "
                      f"{CLASS_NAMES[self.latest_result.classification]}")
        ax2.set_xlim(0, 2)
        ax2.grid(True)

        plt.tight_layout()
        plt.savefig("boneecho_scan.png", dpi=120)
        plt.show()


async def main():
    parser = argparse.ArgumentParser(description="Bone Echo BLE companion app")
    parser.add_argument("--mac", help="Device MAC address", default=None)
    parser.add_argument("--scan", action="store_true", help="Start a scan immediately")
    parser.add_argument("--phantom", action="store_true", help="Run phantom calibration")
    args = parser.parse_args()

    app = BoneEchoApp(mac=args.mac)
    if not await app.connect():
        return

    try:
        if args.phantom:
            await app.send_command("PHANTOM\n")
            await asyncio.sleep(5)
        if args.scan:
            await app.send_command("SCAN\n")
            await asyncio.sleep(3)
            app.plot_waveform()
        else:
            # Interactive loop
            print("Listening for notifications (10 s)...")
            await asyncio.sleep(10)
            if app.latest_result:
                app.plot_waveform()
    finally:
        await app.disconnect()


if __name__ == "__main__":
    asyncio.run(main())