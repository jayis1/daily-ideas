#!/usr/bin/env python3
"""
ionsprint_app.py — Ion Sprint BLE companion app

A Python BLE client / plotter for the Ion Sprint pocket capillary
electrophoresis instrument. Connects over BLE, subscribes to the
Electropherogram, Results, and Status characteristics, and plots
the live electropherogram + peak table.

Usage:
    python3 ionsprint_app.py [--mac AA:BB:CC:DD:EE:FF]

Requirements:
    pip install bleak numpy matplotlib

Press 's' to start a run, 'a' to abort, 'q' to quit.
"""

import argparse
import asyncio
import struct
from dataclasses import dataclass, field
from typing import Optional, List

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
SERVICE_UUID    = "0000fe21-0000-1000-8000-00805f9b34fb"
EPH_UUID        = "0000fe22-0000-1000-8000-00805f9b34fb"
RESULTS_UUID    = "0000fe23-0000-1000-8000-00805f9b34fb"
COMMAND_UUID    = "0000fe24-0000-1000-8000-00805f9b34fb"
STATUS_UUID     = "0000fe25-0000-1000-8000-00805f9b34fb"
SETTINGS_UUID   = "0000fe26-0000-1000-8000-00805f9b34fb"
ERROR_UUID      = "0000fe27-0000-1000-8000-00805f9b34fb"

# Packet types
PKT_START   = 0xAA
PKT_EPH     = 0x01
PKT_RESULTS = 0x02
PKT_ERROR   = 0x03
PKT_STATUS  = 0x04

# Commands
CMD_START    = 0x01
CMD_ABORT    = 0x02
CMD_SET_HV   = 0x03
CMD_SET_BGE  = 0x04
CMD_SET_INJ  = 0x05
CMD_CALIB    = 0x06
CMD_FLUSH    = 0x07


@dataclass
class IonResult:
    ion_id: int
    ion_name: str
    migration_time: float
    area: float
    concentration_mM: float


@dataclass
class IonSprintState:
    eph_data: List[float] = field(default_factory=list)
    hv_kv: float = 0.0
    current_ua: float = 0.0
    results: List[IonResult] = field(default_factory=list)
    status: str = "IDLE"
    error: Optional[str] = None
    run_id: int = 0


def crc8(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def parse_packet(data: bytes) -> Optional[tuple]:
    """Parse a BLE notification into (type, payload) or None."""
    if len(data) < 5 or data[0] != PKT_START:
        return None
    pkt_type = data[1]
    pkt_len = (data[2] << 8) | data[3]
    payload = data[4:4 + pkt_len]
    crc = data[4 + pkt_len] if len(data) > 4 + pkt_len else 0
    if crc8(payload) != crc:
        print(f"CRC mismatch: got {crc}, expected {crc8(payload)}")
        return None
    return (pkt_type, payload)


def parse_eph(payload: bytes) -> tuple:
    """Parse electropherogram chunk → (hv_kv, current_ua, samples)"""
    hv_kv, current_ua = struct.unpack_from('<ff', payload, 0)
    count = struct.unpack_from('<H', payload, 8)[0]
    samples = struct.unpack_from(f'<{count}f', payload, 10)
    return hv_kv, current_ua, list(samples)


def parse_results(payload: bytes) -> tuple:
    """Parse results packet → (run_id, [IonResult])"""
    run_id = struct.unpack_from('<H', payload, 0)[0]
    count = payload[2]
    results = []
    offset = 3
    for _ in range(count):
        ion_id = payload[offset]
        ion_name = payload[offset+1:offset+13].decode('ascii', errors='replace').strip('\x00')
        mt, area, conc = struct.unpack_from('<fff', payload, offset + 13)
        results.append(IonResult(ion_id, ion_name, mt, area, conc))
        offset += 25
    return run_id, results


def parse_error(payload: bytes) -> str:
    """Parse error packet → message string"""
    msg_len = payload[0]
    msg = payload[1:1+msg_len].decode('ascii', errors='replace')
    return msg


class IonSprintApp:
    def __init__(self, mac: Optional[str] = None):
        self.mac = mac
        self.state = IonSprintState()
        self.client: Optional[BleakClient] = None
        self.fig, (self.ax_eph, self.ax_peaks) = plt.subplots(2, 1,
            figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]})
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)

    def on_key(self, event):
        if event.key == 's':
            asyncio.get_event_loop().create_task(self.send_command(CMD_START))
        elif event.key == 'a':
            asyncio.get_event_loop().create_task(self.send_command(CMD_ABORT))
        elif event.key == 'f':
            asyncio.get_event_loop().create_task(self.send_command(CMD_FLUSH))
        elif event.key == 'q':
            plt.close(self.fig)

    async def send_command(self, cmd: int, param: bytes = b''):
        if self.client and self.client.is_connected:
            payload = bytes([cmd]) + param
            await self.client.write_gatt_char(COMMAND_UUID, payload)

    def on_eph(self, sender, data: bytes):
        parsed = parse_packet(data)
        if parsed is None:
            return
        pkt_type, payload = parsed
        if pkt_type == PKT_EPH:
            hv, curr, samples = parse_eph(payload)
            self.state.hv_kv = hv
            self.state.current_ua = curr
            self.state.eph_data.extend(samples)
        elif pkt_type == PKT_RESULTS:
            run_id, results = parse_results(payload)
            self.state.run_id = run_id
            self.state.results = results
            print(f"\n=== Run {run_id} Results ===")
            for r in results:
                print(f"  {r.ion_name:12s}  t={r.migration_time:6.1f}s  "
                      f"conc={r.concentration_mM:6.3f} mM")
        elif pkt_type == PKT_ERROR:
            self.state.error = parse_error(payload)
            print(f"ERROR: {self.state.error}")

    def update_plot(self, frame):
        self.ax_eph.clear()
        if self.state.eph_data:
            t = np.arange(len(self.state.eph_data)) / 100.0  # 100 Hz
            self.ax_eph.plot(t, self.state.eph_data, 'b-', linewidth=0.5)
            self.ax_eph.set_xlabel('Time (s)')
            self.ax_eph.set_ylabel('C4D Signal')
            self.ax_eph.set_title(f'Ion Sprint — Run {self.state.run_id} — '
                                f'HV={self.state.hv_kv:.1f} kV  '
                                f'I={self.state.current_ua:.1f} µA')

        self.ax_peaks.clear()
        if self.state.results:
            names = [r.ion_name for r in self.state.results]
            concs = [r.concentration_mM for r in self.state.results]
            self.ax_peaks.bar(range(len(names)), concs)
            self.ax_peaks.set_xticks(range(len(names)))
            self.ax_peaks.set_xticklabels(names, rotation=45, ha='right')
            self.ax_peaks.set_ylabel('Concentration (mM)')
            self.ax_peaks.set_title('Peak Table')

        self.fig.tight_layout()

    async def run(self):
        # Scan for device
        if self.mac is None:
            print("Scanning for Ion Sprint...")
            devices = await BleakScanner.discover(timeout=10)
            for d in devices:
                if "Ion Sprint" in (d.name or ""):
                    self.mac = d.address
                    break
            if self.mac is None:
                print("Ion Sprint not found. Specify --mac.")
                return

        print(f"Connecting to {self.mac}...")
        async with BleakClient(self.mac) as client:
            self.client = client
            await client.start_notify(EPH_UUID, self.on_eph)
            await client.start_notify(RESULTS_UUID, self.on_eph)
            await client.start_notify(ERROR_UUID, self.on_eph)
            print("Connected! Press 's' to start, 'a' to abort, 'q' to quit.")

            ani = FuncAnimation(self.fig, self.update_plot, interval=100,
                               cache_frame_data=False)
            plt.show()

            await client.stop_notify(EPH_UUID)
            await client.stop_notify(RESULTS_UUID)
            await client.stop_notify(ERROR_UUID)


def main():
    parser = argparse.ArgumentParser(description='Ion Sprint BLE companion app')
    parser.add_argument('--mac', type=str, default=None,
                       help='BLE MAC address')
    args = parser.parse_args()

    app = IonSprintApp(mac=args.mac)
    asyncio.run(app.run())


if __name__ == '__main__':
    main()