#!/usr/bin/env python3
"""
Thermo Trace — BLE companion app for the pocket DSC.

Connects to the Thermo Trace device via BLE (Nordic UART Service),
receives real-time DSC data, plots the heat-flow vs. temperature curve,
performs peak detection and library matching on PC, and exports data.

Usage:
    python thermo_trace_app.py [--device MAC] [--export CSV_PATH]

Requirements:
    pip install bleak matplotlib numpy

The app auto-discovers and connects to a device named "Thermo Trace".
"""

import argparse
import asyncio
import struct
import time
import csv
import json
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install bleak: pip install bleak")
    exit(1)

try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    import numpy as np
except ImportError:
    print("Install matplotlib numpy: pip install matplotlib numpy")
    exit(1)


# BLE Nordic UART Service UUIDs
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"   # notify (device→host)
NUS_RX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"   # write (host→device)

# Message types
MSG_DATA = 0x01
MSG_STATUS = 0x02
MSG_MATCH = 0x03
MSG_DONE = 0x04
MSG_CALIB = 0x05

SYNC1 = 0xAA
SYNC2 = 0x55


def crc8(data: bytes) -> int:
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


@dataclass
class DSCDataPoint:
    temperature: float
    heat_flow: float
    time_s: float
    setpoint: float


@dataclass
class DSCMatch:
    name: str
    confidence: float


@dataclass
class ThermoTraceDevice:
    """Represents a connected Thermo Trace device."""
    client: Optional[BleakClient] = None
    data_points: list = field(default_factory=list)
    matches: list = field(default_factory=list)
    scan_done: bool = False
    status: dict = field(default_factory=dict)

    # RX buffer for frame assembly
    _rx_buffer: bytearray = field(default_factory=bytearray)
    _on_data_callbacks: list = field(default_factory=list)

    def on_data(self, callback: Callable):
        """Register a callback for data points."""
        self._on_data_callbacks.append(callback)

    def _parse_frame(self, frame: bytes):
        """Parse a complete BLE frame."""
        if len(frame) < 5:
            return
        msg_type = frame[2]
        payload_len = frame[3]
        payload = frame[4:4 + payload_len]
        crc_received = frame[4 + payload_len] if len(frame) > 4 + payload_len else 0

        # Verify CRC
        crc_data = bytes([msg_type, payload_len]) + payload
        if crc8(crc_data) != crc_received:
            print(f"CRC mismatch: expected {crc8(crc_data)}, got {crc_received}")
            return

        if msg_type == MSG_DATA and len(payload) >= 16:
            temp, heat_flow, time_s, setpoint = struct.unpack_from('<ffff', payload, 0)
            point = DSCDataPoint(temp, heat_flow, time_s, setpoint)
            self.data_points.append(point)
            for cb in self._on_data_callbacks:
                cb(point)

        elif msg_type == MSG_STATUS and len(payload) >= 16:
            temp, setpoint, heat_flow, ramp_rate = struct.unpack_from('<ffff', payload, 0)
            battery = payload[14] if len(payload) > 14 else 0
            state = payload[15] if len(payload) > 15 else 0
            self.status = {
                'temperature': temp,
                'setpoint': setpoint,
                'heat_flow': heat_flow,
                'ramp_rate': ramp_rate,
                'battery': battery,
                'state': state,
            }

        elif msg_type == MSG_MATCH and len(payload) >= 4:
            name_len = payload[0]
            name = payload[1:1 + name_len].decode('ascii', errors='replace')
            confidence = struct.unpack_from('<f', payload, 24)[0] if len(payload) >= 28 else 0.0
            self.matches.append(DSCMatch(name, confidence))
            print(f"  MATCH: {name} ({confidence:.1%})")

        elif msg_type == MSG_DONE:
            self.scan_done = True
            print("  Scan complete!")

        elif msg_type == MSG_CALIB and len(payload) >= 12:
            t_measured, t_expected, correction = struct.unpack_from('<fff', payload, 0)
            print(f"  CALIBRATION: measured={t_measured:.1f}°C, "
                  f"expected={t_expected:.1f}°C, correction={correction:.4f}")

    def _notification_handler(self, sender, data: bytearray):
        """Handle incoming BLE notifications (NUS TX characteristic)."""
        self._rx_buffer.extend(data)

        # Extract complete frames from buffer
        while len(self._rx_buffer) >= 6:  # minimum frame size
            # Find sync bytes
            if self._rx_buffer[0] != SYNC1 or self._rx_buffer[1] != SYNC2:
                self._rx_buffer.pop(0)
                continue

            if len(self._rx_buffer) < 5:
                break

            msg_type = self._rx_buffer[2]
            payload_len = self._rx_buffer[3]
            frame_len = 5 + payload_len + 1  # sync(2) + type(1) + len(1) + payload + crc(1)

            if len(self._rx_buffer) < frame_len:
                break  # wait for more data

            frame = bytes(self._rx_buffer[:frame_len])
            self._rx_buffer = self._rx_buffer[frame_len:]
            self._parse_frame(frame)

    async def connect(self, mac: Optional[str] = None):
        """Scan for and connect to a Thermo Trace device."""
        print("Scanning for Thermo Trace device...")
        devices = await BleakScanner.discover(timeout=10.0)

        target = None
        for dev in devices:
            if dev.name and "Thermo Trace" in dev.name:
                target = dev
                break
            if mac and dev.address == mac:
                target = dev
                break

        if not target:
            raise ConnectionError("Thermo Trace device not found. Is it powered on?")

        print(f"Connecting to {target.name} ({target.address})...")
        self.client = BleakClient(target.address)
        await self.client.connect()
        print("Connected!")

        await self.client.start_notify(NUS_TX_CHAR_UUID, self._notification_handler)

    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            print("Disconnected.")

    def export_csv(self, path: str):
        """Export scan data to CSV."""
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['time_s', 'temperature_C', 'heat_flow_mW', 'setpoint_C'])
            for pt in self.data_points:
                writer.writerow([f'{pt.time_s:.2f}', f'{pt.temperature:.2f}',
                                 f'{pt.heat_flow:.3f}', f'{pt.setpoint:.2f}'])
        print(f"Exported {len(self.data_points)} data points to {path}")

    def export_json(self, path: str):
        """Export scan data + matches to JSON."""
        data = {
            'device': 'Thermo Trace',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': [
                {'time_s': pt.time_s, 'temperature_C': pt.temperature,
                 'heat_flow_mW': pt.heat_flow, 'setpoint_C': pt.setpoint}
                for pt in self.data_points
            ],
            'matches': [
                {'name': m.name, 'confidence': m.confidence}
                for m in self.matches
            ],
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Exported to {path}")

    def plot_curve(self):
        """Plot the DSC heat-flow vs. temperature curve."""
        if not self.data_points:
            print("No data to plot.")
            return

        temps = [pt.temperature for pt in self.data_points]
        heat_flows = [pt.heat_flow for pt in self.data_points]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(temps, heat_flows, 'b-', linewidth=0.8)
        ax.set_xlabel('Temperature (°C)')
        ax.set_ylabel('Heat Flow (mW)')
        ax.set_title('Thermo Trace — DSC Scan')
        ax.axhline(y=0, color='k', linewidth=0.3)
        ax.grid(True, alpha=0.3)

        # Annotate matches
        if self.matches:
            match_text = "Matches:\n" + "\n".join(
                f"  {m.name} ({m.confidence:.0%})" for m in self.matches[:3])
            ax.text(0.02, 0.02, match_text, transform=ax.transAxes,
                    fontsize=9, verticalalignment='bottom',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        plt.show()

    def analyze_peaks(self):
        """Perform PC-side peak detection (more sophisticated than on-device)."""
        if len(self.data_points) < 10:
            print("Not enough data for analysis.")
            return

        temps = np.array([pt.temperature for pt in self.data_points])
        heat_flows = np.array([pt.heat_flow for pt in self.data_points])

        # Baseline correction (linear interpolation between first/last 10 pts)
        n = len(heat_flows)
        baseline_start = np.mean(heat_flows[:10])
        baseline_end = np.mean(heat_flows[-10:])
        baseline = np.linspace(baseline_start, baseline_end, n)
        corrected = heat_flows - baseline

        # Peak detection (simple: local maxima above threshold)
        threshold = 0.5 * np.max(np.abs(corrected))
        peaks = []
        for i in range(2, n - 2):
            if corrected[i] > threshold and \
               corrected[i] >= corrected[i - 1] and \
               corrected[i] >= corrected[i + 1]:
                peaks.append((temps[i], corrected[i], 'endothermic'))
            elif corrected[i] < -threshold and \
                 corrected[i] <= corrected[i - 1] and \
                 corrected[i] <= corrected[i + 1]:
                peaks.append((temps[i], corrected[i], 'exothermic'))

        print(f"\nPeak Analysis ({len(peaks)} peaks detected):")
        for i, (t, h, ptype) in enumerate(peaks):
            print(f"  Peak {i + 1}: T={t:.1f}°C, ΔΦ={h:.2f}mW ({ptype})")

        return peaks


async def main():
    parser = argparse.ArgumentParser(description='Thermo Trace BLE companion app')
    parser.add_argument('--device', '-d', type=str, default=None,
                        help='Device MAC address (auto-discover if omitted)')
    parser.add_argument('--export', '-e', type=str, default='thermo_trace_scan.csv',
                        help='CSV export path')
    parser.add_argument('--json', '-j', type=str, default=None,
                        help='JSON export path')
    parser.add_argument('--timeout', '-t', type=int, default=3600,
                        help='Max wait time in seconds')
    parser.add_argument('--no-plot', action='store_true',
                        help='Skip plotting')
    args = parser.parse_args()

    device = ThermoTraceDevice()

    def on_data(pt: DSCDataPoint):
        if len(device.data_points) % 50 == 0:
            print(f"  T={pt.temperature:.1f}°C  Φ={pt.heat_flow:.2f}mW  "
                  f"t={pt.time_s:.0f}s  SP={pt.setpoint:.1f}°C")

    device.on_data(on_data)

    await device.connect(args.device)

    print("\nWaiting for DSC data... (press Ctrl+C to stop)\n")

    try:
        start = time.time()
        while not device.scan_done and time.time() - start < args.timeout:
            await asyncio.sleep(0.5)
            if device.data_points:
                # Print periodic status
                pass
    except KeyboardInterrupt:
        print("\nStopped by user.")

    # Export data
    device.export_csv(args.export)
    if args.json:
        device.export_json(args.json)

    # Analyze peaks
    device.analyze_peaks()

    # Print matches
    if device.matches:
        print("\nMaterial Matches:")
        for m in device.matches:
            print(f"  {m.name}: {m.confidence:.1%}")

    # Plot
    if not args.no_plot and device.data_points:
        device.plot_curve()

    await device.disconnect()


if __name__ == '__main__':
    asyncio.run(main())