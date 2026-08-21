#!/usr/bin/env python3
"""
taste_bead.py — BLE companion app for the Taste Bead pocket electronic tongue.

Connects to the Taste Bead device over BLE, receives impedance spectra and
classification results, manages the reference library, and provides a
real-time Nyquist plot viewer.

Usage:
    python3 taste_bead.py --ble --identify              # trigger identification
    python3 taste_bead.py --ble --learn "Tap Water"     # add a reference
    python3 taste_bead.py --ble --nyquist               # real-time Nyquist plots
    python3 taste_bead.py --ble --monitor --output milk_spoilage.csv  # track changes
    python3 taste_bead.py --ble --list-library          # show stored references
    python3 taste_bead.py --ble --delete 3              # delete entry #3
    python3 taste_bead.py --ble --clear-library         # erase all entries
    python3 taste_bead.py --ble --export-library lib.json  # export to file
    python3 taste_bead.py --ble --calibrate open        # run open calibration

Requires: bleak (for BLE), matplotlib (for visualization), numpy
    pip install bleak matplotlib numpy
"""

import argparse
import asyncio
import struct
import time
import csv
import json
import sys
import math
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List

# --- BLE UUIDs ---
SERVICE_UUID = "0000f00d-0000-1000-8000-00805f9b34fb"
CHAR_RESULT   = "0000f001-0000-1000-8000-00805f9b34fb"
CHAR_SPECTRUM = "0000f002-0000-1000-8000-00805f9b34fb"
CHAR_COMMAND  = "0000f003-0000-1000-8000-00805f9b34fb"
CHAR_LIBRARY  = "0000f004-0000-1000-8000-00805f9b34fb"
CHAR_STATUS   = "0000f005-0000-1000-8000-00805f9b34fb"

NUM_ELECTRODES = 5
NUM_FREQS = 20
NUM_FEATURES = 48
ELECTRODE_NAMES = ["Gold", "Platinum", "Ag/AgCl", "Glassy Carbon", "Copper"]

# --- Data structures ---

@dataclass
class ImpedancePoint:
    electrode: int
    freq_index: int
    z_mag: float       # Ω
    z_phase: float      # degrees

@dataclass
class Spectrum:
    """Full impedance spectrum: 5 electrodes × 20 frequencies."""
    points: List[ImpedancePoint] = field(default_factory=list)
    complete: bool = False

    def is_complete(self) -> bool:
        return len(self.points) == NUM_ELECTRODES * NUM_FREQS

    def get_nyquist_data(self, electrode: int):
        """Return (z_real, z_imag) for Nyquist plot of given electrode."""
        z_real = []
        z_imag = []
        for p in self.points:
            if p.electrode == electrode and not math.isnan(p.z_mag):
                rad = math.radians(p.z_phase)
                z_real.append(p.z_mag * math.cos(rad))
                z_imag.append(-p.z_mag * math.sin(rad))  # Nyquist: -Z''
        return z_real, z_imag

@dataclass
class Result:
    label: str = ""
    confidence: float = 0.0
    distance: float = 0.0
    timestamp: int = 0

@dataclass
class LibraryEntry:
    index: int = 0
    label: str = ""
    measurement_count: int = 0

# --- BLE communication ---

class TasteBeadBLE:
    def __init__(self):
        self.client = None
        self.spectrum = Spectrum()
        self.results: List[Result] = []
        self.library: List[LibraryEntry] = []
        self.status_msg = ""

    async def connect(self):
        try:
            from bleak import BleakClient, BleakScanner
        except ImportError:
            print("Error: bleak not installed. Run: pip install bleak")
            sys.exit(1)

        print("Scanning for Taste Bead...")
        devices = await BleakScanner.discover(timeout=10.0)

        target = None
        for d in devices:
            if "Taste Bead" in (d.name or ""):
                target = d
                break
            # Also try matching by service UUID
            if d.metadata.get("uuids"):
                for u in d.metadata["uuids"]:
                    if "f00d" in u.lower():
                        target = d
                        break

        if target is None:
            print("Taste Bead not found. Make sure it's powered on and in range.")
            sys.exit(1)

        print(f"Found: {target.name} ({target.address})")
        self.client = BleakClient(target.address)
        await self.client.connect()
        print("Connected!")

        # Subscribe to notifications
        await self.client.start_notify(CHAR_RESULT, self._on_result)
        await self.client.start_notify(CHAR_SPECTRUM, self._on_spectrum)
        await self.client.start_notify(CHAR_STATUS, self._on_status)
        await self.client.start_notify(CHAR_LIBRARY, self._on_library)

    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            print("Disconnected.")

    async def send_command(self, opcode: int, data: bytes = b''):
        if self.client and self.client.is_connected:
            payload = bytes([opcode]) + data
            await self.client.write_gatt_char(CHAR_COMMAND, payload)
            print(f"Sent command 0x{opcode:02X} ({len(data)} bytes data)")

    def _on_result(self, characteristic, data: bytearray):
        if len(data) < 41:
            return
        msg_type = data[0]
        if msg_type != 0x01:
            return
        label = data[1:33].decode('utf-8', errors='replace').rstrip('\x00')
        confidence = struct.unpack('<f', data[33:37])[0]
        distance = struct.unpack('<f', data[37:41])[0]
        timestamp = struct.unpack('<q', data[41:49])[0] if len(data) >= 49 else 0

        result = Result(label=label, confidence=confidence,
                        distance=distance, timestamp=timestamp)
        self.results.append(result)
        print(f"\n{'='*50}")
        print(f"  RESULT: {label}")
        print(f"  Confidence: {confidence:.1f}%")
        print(f"  Distance: {distance:.2f}")
        print(f"  Time: {datetime.fromtimestamp(timestamp/1e6).isoformat()}")
        print(f"{'='*50}\n")

    def _on_spectrum(self, characteristic, data: bytearray):
        if len(data) < 12:
            return
        msg_type = data[0]
        seq = data[1]
        electrode = data[2]
        freq_idx = data[3]
        z_mag = struct.unpack('<f', data[4:8])[0]
        z_phase = struct.unpack('<f', data[8:12])[0]

        point = ImpedancePoint(electrode=electrode, freq_index=freq_idx,
                                z_mag=z_mag, z_phase=z_phase)
        self.spectrum.points.append(point)

        if self.spectrum.is_complete():
            print(f"Spectrum complete: {len(self.spectrum.points)} points")
            self._print_spectrum_summary()

    def _print_spectrum_summary(self):
        print("\nImpedance Spectrum Summary:")
        print(f"{'Electrode':<15} {'Freq (Hz)':>10} {'|Z| (Ω)':>12} {'Phase (°)':>10}")
        print("-" * 50)
        for p in sorted(self.spectrum.points, key=lambda x: (x.electrode, x.freq_index)):
            if p.freq_index in (0, 5, 10, 15, 19):  # show every 5th freq
                name = ELECTRODE_NAMES[p.electrode]
                freq = [1, 10, 100, 1000, 100000][p.freq_index // 5]
                mag = p.z_mag if not math.isnan(p.z_mag) else float('nan')
                print(f"{name:<15} {freq:>10} {mag:>12.1f} {p.z_phase:>10.1f}")

    def _on_status(self, characteristic, data: bytearray):
        if len(data) < 2:
            return
        msg_type = data[0]
        self.status_msg = data[1:33].decode('utf-8', errors='replace').rstrip('\x00')
        print(f"Status: {self.status_msg}")

    def _on_library(self, characteristic, data: bytearray):
        if len(data) < 3:
            return
        idx = data[0]
        label = data[1:33].decode('utf-8', errors='replace').rstrip('\x00')
        count = struct.unpack('<H', data[33:35])[0] if len(data) >= 35 else 0
        entry = LibraryEntry(index=idx, label=label, measurement_count=count)
        self.library.append(entry)
        print(f"  [{idx}] {label} ({count} measurements)")

# --- Nyquist plot visualization ---

async def show_nyquist(device: TasteBeadBLE):
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("Error: matplotlib/numpy not installed. Run: pip install matplotlib numpy")
        return

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()
    fig.suptitle("Taste Bead — Real-time Nyquist Plots", fontsize=14)

    for e in range(NUM_ELECTRODES):
        axes[e].set_title(ELECTRODE_NAMES[e])
        axes[e].set_xlabel("Z' (Ω)")
        axes[e].set_ylabel("-Z'' (Ω)")
        axes[e].set_aspect('equal')
        axes[e].grid(True, alpha=0.3)

    axes[5].set_visible(False)  # hide extra subplot

    plt.ion()
    plt.show()

    print("Waiting for spectrum data... (Ctrl+C to stop)")
    try:
        while True:
            if device.spectrum.is_complete():
                for e in range(NUM_ELECTRODES):
                    z_real, z_imag = device.spectrum.get_nyquist_data(e)
                    axes[e].clear()
                    axes[e].set_title(ELECTRODE_NAMES[e])
                    axes[e].set_xlabel("Z' (Ω)")
                    axes[e].set_ylabel("-Z'' (Ω)")
                    axes[e].grid(True, alpha=0.3)
                    if z_real:
                        axes[e].scatter(z_real, z_imag, c='blue', s=20)
                        axes[e].plot(z_real, z_imag, 'b-', alpha=0.5)
                fig.canvas.draw_idle()
                fig.canvas.start_event_loop(0.1)
            await asyncio.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping Nyquist viewer...")
        plt.ioff()
        plt.close()

# --- Monitor mode (continuous logging) ---

async def monitor_mode(device: TasteBeadBLE, output_file: str, duration: int):
    print(f"Monitor mode: logging to {output_file} for {duration}s")
    await device.send_command(0x06)  # MONITOR_START

    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'label', 'confidence', 'distance'])

        start = time.time()
        try:
            while time.time() - start < duration:
                await asyncio.sleep(1)
                while device.results:
                    r = device.results.pop(0)
                    writer.writerow([r.timestamp, r.label, r.confidence, r.distance])
                    f.flush()
                    print(f"[{time.time()-start:.0f}s] {r.label} ({r.confidence:.1f}%)")
        finally:
            await device.send_command(0x07)  # MONITOR_STOP

    print(f"Monitor complete. {output_file} saved.")

# --- Main ---

async def main():
    parser = argparse.ArgumentParser(description="Taste Bead BLE companion")
    parser.add_argument('--ble', action='store_true', help="Use BLE connection")
    parser.add_argument('--identify', action='store_true', help="Trigger identification")
    parser.add_argument('--learn', type=str, help="Learn a new reference with given label")
    parser.add_argument('--nyquist', action='store_true', help="Show real-time Nyquist plots")
    parser.add_argument('--monitor', action='store_true', help="Continuous monitoring")
    parser.add_argument('--output', type=str, help="Output CSV file for monitor mode")
    parser.add_argument('--duration', type=int, default=3600, help="Monitor duration (seconds)")
    parser.add_argument('--list-library', action='store_true', help="List stored references")
    parser.add_argument('--delete', type=int, help="Delete library entry by index")
    parser.add_argument('--clear-library', action='store_true', help="Clear entire library")
    parser.add_argument('--export-library', type=str, help="Export library to JSON file")
    parser.add_argument('--calibrate', type=str, choices=['open', 'short', 'kcl'],
                        help="Run calibration step")
    args = parser.parse_args()

    if not args.ble:
        parser.print_help()
        sys.exit(0)

    device = TasteBeadBLE()
    await device.connect()

    try:
        if args.identify:
            print("Triggering identification sweep...")
            await device.send_command(0x01)
            print("Waiting for result... (sweep takes ~12 seconds)")
            await asyncio.sleep(30)

        elif args.learn:
            label = args.learn[:31]  # max 32 chars including null
            print(f"Learning reference: '{label}'")
            label_bytes = label.encode('utf-8').ljust(32, b'\x00')
            await device.send_command(0x02, label_bytes)
            print("Waiting for capture... (dip probe and press ID button)")
            await asyncio.sleep(30)

        elif args.nyquist:
            await show_nyquist(device)

        elif args.monitor:
            output = args.output or f"taste_bead_monitor_{int(time.time())}.csv"
            await monitor_mode(device, output, args.duration)

        elif args.list_library:
            print("Requesting library...")
            await device.send_command(0x04)
            await asyncio.sleep(5)
            if not device.library:
                print("Library is empty.")
            else:
                print(f"\nLibrary ({len(device.library)} entries):")
                for entry in device.library:
                    print(f"  [{entry.index}] {entry.label} ({entry.measurement_count} measurements)")

        elif args.delete is not None:
            print(f"Deleting entry #{args.delete}...")
            await device.send_command(0x03, bytes([args.delete]))
            await asyncio.sleep(2)

        elif args.clear_library:
            print("Clearing entire library...")
            # Send delete for each entry
            await device.send_command(0x04)
            await asyncio.sleep(3)
            for entry in device.library:
                await device.send_command(0x03, bytes([entry.index]))
                await asyncio.sleep(0.5)
            print("Library cleared.")

        elif args.export_library:
            print("Requesting library for export...")
            await device.send_command(0x04)
            await asyncio.sleep(5)
            with open(args.export_library, 'w') as f:
                json.dump([{'index': e.index, 'label': e.label,
                           'measurements': e.measurement_count}
                          for e in device.library], f, indent=2)
            print(f"Exported {len(device.library)} entries to {args.export_library}")

        elif args.calibrate:
            steps = {'open': 0, 'short': 1, 'kcl': 2}
            step = steps[args.calibrate]
            print(f"Running {args.calibrate} calibration (step {step})...")
            await device.send_command(0x05, bytes([step]))
            await asyncio.sleep(20)
            print("Calibration step complete.")

        else:
            print("Listening for results... (Ctrl+C to stop)")
            while True:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await device.disconnect()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExited.")