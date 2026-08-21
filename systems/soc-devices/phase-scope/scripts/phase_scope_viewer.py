#!/usr/bin/env python3
"""
Phase Scope — Live Waveform Viewer
Connects to Phase Scope via BLE and displays real-time waveforms, phasors, and readings.

Requirements:
    pip install bleak numpy matplotlib

Usage:
    python phase_scope_viewer.py [--device BLE_ADDRESS] [--page phasor|waveform|harmonics|numeric]
"""

import argparse
import struct
import sys
import asyncio
import numpy as np
from collections import deque

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
except ImportError:
    print("matplotlib required: pip install matplotlib")
    sys.exit(1)

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("bleak required: pip install bleak")
    sys.exit(1)

# Nordic UART Service UUIDs
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

# Packet constants
START_BYTE_1 = 0xAA
START_BYTE_2 = 0x55
END_BYTE_1 = 0x0D
END_BYTE_2 = 0x0A
STATUS_PACKET_TYPE = 0x01
STATUS_PACKET_LEN = 64


class PhaseScopeData:
    """Holds the latest measurement data from Phase Scope."""

    def __init__(self):
        self.vrms = [0.0, 0.0, 0.0]
        self.irms = [0.0, 0.0, 0.0]
        self.p = [0.0, 0.0, 0.0]
        self.q = [0.0, 0.0, 0.0]
        self.s = [0.0, 0.0, 0.0]
        self.pf = [0.0, 0.0, 0.0]
        self.frequency = 0.0
        self.thd = [0.0, 0.0, 0.0]
        self.phase_vi = [0.0, 0.0, 0.0]
        self.flags = 0
        self.timestamp = 0

    def parse_status(self, data):
        """Parse a 64-byte status packet."""
        if len(data) < STATUS_PACKET_LEN:
            return False

        if data[0] != STATUS_PACKET_TYPE:
            return False

        for i in range(3):
            self.vrms[i] = struct.unpack_from('<h', data, 1 + i * 2)[0] / 10.0
            self.irms[i] = struct.unpack_from('<h', data, 7 + i * 2)[0] / 100.0
            self.p[i] = struct.unpack_from('<i', data, 13 + i * 4)[0]
            self.pf[i] = struct.unpack_from('<h', data, 25 + i * 2)[0] / 32767.0

        self.frequency = struct.unpack_from('<h', data, 31)[0] / 100.0
        self.timestamp = struct.unpack_from('<I', data, 33)[0]

        for i in range(3):
            self.thd[i] = struct.unpack_from('<h', data, 37 + i * 2)[0] / 100.0
            self.phase_vi[i] = struct.unpack_from('<h', data, 43 + i * 2)[0] / 100.0

        self.flags = struct.unpack_from('<H', data, 49)[0]
        return True

    def flag_str(self, bit, label):
        return label if (self.flags & (1 << bit)) else ""


class PhaseScopeViewer:
    """Real-time Phase Scope display."""

    def __init__(self, page='numeric'):
        self.data = PhaseScopeData()
        self.page = page
        self.pkt_buffer = bytearray()
        self.history_vrms = [deque(maxlen=200), deque(maxlen=200), deque(maxlen=200)]
        self.history_irms = [deque(maxlen=200), deque(maxlen=200), deque(maxlen=200)]
        self.connected = False

    def notification_handler(self, sender, data):
        """Handle incoming BLE data."""
        self.pkt_buffer.extend(data)

        # Look for complete packets
        while len(self.pkt_buffer) >= 4:
            # Find start bytes
            try:
                start = self.pkt_buffer.index(START_BYTE_1)
                if start + 1 < len(self.pkt_buffer) and self.pkt_buffer[start + 1] == START_BYTE_2:
                    # Find end bytes
                    end = None
                    for i in range(start + 2, len(self.pkt_buffer) - 1):
                        if self.pkt_buffer[i] == END_BYTE_1 and self.pkt_buffer[i + 1] == END_BYTE_2:
                            end = i + 2
                            break

                    if end is not None:
                        payload = bytes(self.pkt_buffer[start + 2:end - 2])
                        self.pkt_buffer = self.pkt_buffer[end:]
                        self.data.parse_status(payload)
                        return
                    else:
                        break
                else:
                    self.pkt_buffer = self.pkt_buffer[start + 1:]
            except ValueError:
                self.pkt_buffer.clear()
                return

    async def scan_and_connect(self, address=None):
        """Find and connect to Phase Scope."""
        if address:
            client = BleakClient(address)
        else:
            print("Scanning for Phase Scope devices...")
            devices = await BleakScanner.discover(timeout=10)
            phase_scope = None
            for d in devices:
                if d.name and "PhaseScope" in d.name:
                    phase_scope = d
                    print(f"Found: {d.name} ({d.address})")
                    break

            if phase_scope is None:
                print("No Phase Scope found!")
                return None

            client = BleakClient(phase_scope.address)

        await client.connect()
        self.connected = True
        print(f"Connected to {client.address}")

        await client.start_notify(NUS_TX_CHAR_UUID, self.notification_handler)
        return client

    def create_figure(self):
        """Create the matplotlib figure based on selected page."""
        self.fig = plt.figure(figsize=(12, 8))
        self.fig.suptitle('Phase Scope — 3-Phase Power Quality Analyzer',
                          fontsize=14, fontweight='bold')

        if self.page == 'phasor':
            self.ax1 = self.fig.add_subplot(111, polar=True)
            self.ax1.set_title('Phasor Diagram')
        elif self.page == 'waveform':
            self.ax1 = self.fig.add_subplot(311)
            self.ax2 = self.fig.add_subplot(312)
            self.ax3 = self.fig.add_subplot(313)
        elif self.page == 'harmonics':
            self.ax1 = self.fig.add_subplot(111)
        else:  # numeric
            self.ax1 = self.fig.add_subplot(111)
            self.ax1.axis('off')

        return self.fig

    def update_numeric(self, frame):
        """Update numeric readout display."""
        self.ax1.clear()
        self.ax1.axis('off')

        d = self.data
        lines = [
            f"{'─' * 40}",
            f"  L1: {d.vrms[0]:7.1f} V   {d.irms[0]:6.2f} A   PF {d.pf[0]:.3f}",
            f"  L2: {d.vrms[1]:7.1f} V   {d.irms[1]:6.2f} A   PF {d.pf[1]:.3f}",
            f"  L3: {d.vrms[2]:7.1f} V   {d.irms[2]:6.2f} A   PF {d.pf[2]:.3f}",
            f"{'─' * 40}",
            f"  Frequency: {d.frequency:.2f} Hz",
            f"  Total P: {sum(d.p):.0f} W",
            f"  Total Q: {sum(d.q):.0f} VAR",
            f"  Total S: {sum(d.s):.0f} VA",
            f"{'─' * 40}",
            f"  THD L1: {d.thd[0]:.1f}%   L2: {d.thd[1]:.1f}%   L3: {d.thd[2]:.1f}%",
            f"  Phase V-I  L1: {d.phase_vi[0]:.1f}°  L2: {d.phase_vi[1]:.1f}°  L3: {d.phase_vi[2]:.1f}°",
            f"{'─' * 40}",
            f"  Flags: {d.flag_str(0, 'OV1 ')}{d.flag_str(3, 'UV1 ')}"
                    f"{d.flag_str(8, 'BAT ')}{d.flag_str(9, 'LOG ')}"
                    f"{d.flag_str(10, 'BLE ')}",
        ]

        self.ax1.text(0.05, 0.95, '\n'.join(lines),
                      transform=self.ax1.transAxes,
                      fontsize=11, fontfamily='monospace',
                      verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        return []

    def update_phasor(self, frame):
        """Update phasor diagram display."""
        self.ax1.clear()
        d = self.data
        colors = ['#e74c3c', '#2ecc71', '#3498db']
        labels = ['L1', 'L2', 'L3']

        for i in range(3):
            angle = np.radians(d.phase_vi[i] + i * 120)
            magnitude = d.vrms[i] / 400.0  # Normalize to unit circle
            if magnitude > 1.0:
                magnitude = 1.0

            self.ax1.plot([0, angle], [0, magnitude], color=colors[i],
                         linewidth=2, label=f'{labels[i]}: {d.vrms[i]:.0f}V')

        self.ax1.set_title('Voltage Phasors', pad=20)
        self.ax1.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        return []

    def update_harmonics(self, frame):
        """Update harmonic bar chart display."""
        self.ax1.clear()
        d = self.data

        harmonics = np.zeros(50)
        harmonics[0] = d.vrms[0]  # Fundamental approximation
        for i in range(1, min(16, 50)):
            # Approximate harmonic magnitudes from THD
            if i < len(d.thd):
                harmonics[i] = d.vrms[i % 3] * d.thd[i % 3] / 100.0 / i

        x = np.arange(16)
        self.ax1.bar(x, harmonics[:16], color='#3498db', alpha=0.7)
        self.ax1.set_xlabel('Harmonic Order')
        self.ax1.set_ylabel('Magnitude (V)')
        self.ax1.set_title(f'Voltage Harmonics — THD: L1={d.thd[0]:.1f}% L2={d.thd[1]:.1f}% L3={d.thd[2]:.1f}%')
        self.ax1.set_xticks(x)
        self.ax1.set_xticklabels([str(i+1) for i in range(16)])
        return []

    async def run(self, address=None):
        """Main run loop."""
        client = await self.scan_and_connect(address)
        if client is None:
            return

        try:
            fig = self.create_figure()

            if self.page == 'numeric':
                ani = animation.FuncAnimation(fig, self.update_numeric, interval=500, blit=False)
            elif self.page == 'phasor':
                ani = animation.FuncAnimation(fig, self.update_phasor, interval=1000, blit=False)
            elif self.page == 'harmonics':
                ani = animation.FuncAnimation(fig, self.update_harmonics, interval=1000, blit=False)
            else:
                ani = animation.FuncAnimation(fig, self.update_numeric, interval=500, blit=False)

            plt.show()

        finally:
            await client.stop_notify(NUS_TX_CHAR_UUID)
            await client.disconnect()
            self.connected = False


def main():
    parser = argparse.ArgumentParser(description='Phase Scope Live Viewer')
    parser.add_argument('--device', '-d', help='BLE device address')
    parser.add_argument('--page', '-p',
                        choices=['phasor', 'waveform', 'harmonics', 'numeric'],
                        default='numeric',
                        help='Display page (default: numeric)')
    args = parser.parse_args()

    viewer = PhaseScopeViewer(page=args.page)

    try:
        asyncio.run(viewer.run(address=args.device))
    except KeyboardInterrupt:
        print("\nDisconnected.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    main()