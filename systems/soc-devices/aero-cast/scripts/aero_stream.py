#!/usr/bin/env python3
"""
aero_stream.py — Real-time BLE/Wi-Fi data receiver for the Aero Cast
pocket 3-axis ultrasonic anemometer.

Connects to the Aero Cast device, receives 20 Hz wind data, displays
a real-time wind rose and turbulence dashboard, and logs to CSV.

Usage:
    python3 aero_stream.py --ble --output wind_log.csv
    python3 aero_stream.py --tcp 192.168.1.100:8000 --output wind_log.csv
    python3 aero_stream.py --usb /dev/ttyACM0 --raw  # raw TOF for calibration

Requires: bleak (for BLE), matplotlib (for visualization), numpy
    pip install bleak matplotlib numpy
"""

import argparse
import asyncio
import struct
import time
import csv
import sys
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Iterator, Callable

# --- Data structures ---

@dataclass
class WindSample:
    """20 Hz wind data packet from the Aero Cast."""
    timestamp: int        # µs
    speed: float          # m/s
    direction: float      # degrees (meteorological)
    u: float             # east-west m/s
    v: float             # north-south m/s
    w: float             # vertical m/s
    t_sonic: float        # K
    bme_temp: float       # °C
    bme_press: float      # Pa
    bme_rh: float         # %RH

    @property
    def t_sonic_celsius(self) -> float:
        return self.t_sonic - 273.15

    def __str__(self):
        return (f"[{self.timestamp}] SPD={self.speed:5.2f} m/s "
                f"DIR={self.direction:5.1f}° "
                f"W={self.w:+.3f} "
                f"Ts={self.t_sonic_celsius:5.1f}°C")


@dataclass
class TurbulenceStats:
    """Turbulence statistics from averaging window."""
    u_mean: float
    v_mean: float
    w_mean: float
    sigma_u: float
    sigma_v: float
    sigma_w: float
    u_w_cov: float
    v_w_cov: float
    tke: float
    u_star: float
    turb_intensity: float
    elapsed_s: int

    def __str__(self):
        return (f"TKE={self.tke:.4f} u*={self.u_star:.4f} "
                f"σu={self.sigma_u:.3f} σw={self.sigma_w:.3f} "
                f"TI={self.turb_intensity:.3f} ({self.elapsed_s}s)")


@dataclass
class RawTOF:
    """Raw time-of-flight data for calibration."""
    path0_fwd: float  # µs
    path0_rev: float
    path1_fwd: float
    path1_rev: float
    path2_fwd: float
    path2_rev: float
    timestamp: int

    def expected_tof(self, c=343.0, L=0.0894):
        """Expected TOF in still air."""
        return L / c * 1e6  # µs

    def __str__(self):
        exp = self.expected_tof()
        return (f"[{self.timestamp}] "
                f"P0:{self.path0_fwd:.1f}/{self.path0_rev:.1f} "
                f"P1:{self.path1_fwd:.1f}/{self.path1_rev:.1f} "
                f"P2:{self.path2_fwd:.1f}/{self.path2_rev:.1f} µs "
                f"(expected ~{exp:.1f})")


# --- Packet parsing ---

WIND_PACKET_FORMAT = '<Ifffffff f f'  # timestamp, speed, dir, u, v, w, t_sonic, bme_temp, bme_press, bme_rh
WIND_PACKET_SIZE = struct.calcsize(WIND_PACKET_FORMAT)

TURB_PACKET_FORMAT = '<fffffffffff I'
TURB_PACKET_SIZE = struct.calcsize(TURB_PACKET_FORMAT)

RAW_PACKET_FORMAT = '<ffffffI'
RAW_PACKET_SIZE = struct.calcsize(RAW_PACKET_FORMAT)


def parse_wind_packet(payload: bytes) -> WindSample:
    if len(payload) < WIND_PACKET_SIZE:
        raise ValueError(f"Wind packet too short: {len(payload)} < {WIND_PACKET_SIZE}")
    fields = struct.unpack(WIND_PACKET_FORMAT, payload[:WIND_PACKET_SIZE])
    return WindSample(*fields)


def parse_turb_packet(payload: bytes) -> TurbulenceStats:
    if len(payload) < TURB_PACKET_SIZE:
        raise ValueError(f"Turb packet too short: {len(payload)} < {TURB_PACKET_SIZE}")
    fields = struct.unpack(TURB_PACKET_FORMAT, payload[:TURB_PACKET_SIZE])
    return TurbulenceStats(*fields)


def parse_raw_packet(payload: bytes) -> RawTOF:
    if len(payload) < RAW_PACKET_SIZE:
        raise ValueError(f"Raw packet too short: {len(payload)} < {RAW_PACKET_SIZE}")
    fields = struct.unpack(RAW_PACKET_FORMAT, payload[:RAW_PACKET_SIZE])
    return RawTOF(*fields)


def crc8(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


# --- UART binary protocol parser ---

class UARTProtocol:
    """Parses the UART binary packet protocol from a serial stream."""

    ST_SYNC, ST_TYPE, ST_LEN, ST_PAYLOAD, ST_CRC = range(5)

    def __init__(self):
        self.state = self.ST_SYNC
        self.packet_type = 0
        self.payload_len = 0
        self.payload = bytearray()

    def feed(self, data: bytes) -> list:
        """Feed bytes and return list of (type, payload) tuples for complete packets."""
        packets = []
        for byte in data:
            if self.state == self.ST_SYNC:
                if byte == 0xAA:
                    self.state = self.ST_TYPE
            elif self.state == self.ST_TYPE:
                self.packet_type = byte
                self.state = self.ST_LEN
            elif self.state == self.ST_LEN:
                self.payload_len = byte
                self.payload = bytearray()
                if self.payload_len == 0:
                    self.state = self.ST_CRC
                else:
                    self.state = self.ST_PAYLOAD
            elif self.state == self.ST_PAYLOAD:
                self.payload.append(byte)
                if len(self.payload) >= self.payload_len:
                    self.state = self.ST_CRC
            elif self.state == self.ST_CRC:
                expected = crc8(bytes(self.payload))
                if byte == expected:
                    packets.append((self.packet_type, bytes(self.payload)))
                self.state = self.ST_SYNC
        return packets


# --- BLE connection (using bleak) ---

BLE_WIND_UUID = "0000aero-0000-1000-8000-00805f9b34fb"
BLE_CMD_UUID  = "0000aer1-0000-1000-8000-00805f9b34fb"
BLE_STATUS_UUID = "0000aer2-0000-1000-8000-00805f9b34fb"
BLE_RAW_UUID  = "0000aer3-0000-1000-8000-00805f9b34fb"


async def ble_stream(device_name: str = "aero-cast"):
    """Async generator yielding WindSample and TurbulenceStats from BLE."""
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError:
        print("Error: bleak not installed. Run: pip install bleak")
        return

    print(f"Scanning for '{device_name}'...")
    device = await BleakScanner.find_device_by_name(device_name)
    if not device:
        print(f"Device '{device_name}' not found")
        return

    print(f"Connecting to {device.name} [{device.address}]...")
    async with BleakClient(device) as client:
        print("Connected!")

        def wind_handler(sender, data):
            try:
                sample = parse_wind_packet(data)
                print(sample)
            except Exception as e:
                print(f"Parse error: {e}")

        def status_handler(sender, data):
            if len(data) == TURB_PACKET_SIZE:
                try:
                    stats = parse_turb_packet(data)
                    print(stats)
                except Exception as e:
                    print(f"Turb parse error: {e}")
            else:
                print(f"Status: {data.decode('utf-8', errors='replace')}")

        def raw_handler(sender, data):
            try:
                raw = parse_raw_packet(data)
                print(raw)
            except Exception as e:
                print(f"Raw parse error: {e}")

        await client.start_notify(BLE_WIND_UUID, wind_handler)
        await client.start_notify(BLE_STATUS_UUID, status_handler)

        print("Streaming... Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            await client.stop_notify(BLE_WIND_UUID)
            await client.stop_notify(BLE_STATUS_UUID)


# --- TCP connection (Wi-Fi) ---

def tcp_stream(host: str, port: int = 8000, output_file: str = None):
    """Connect via TCP and stream CSV data."""
    import socket

    print(f"Connecting to {host}:{port}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    print("Connected! Streaming CSV data...")

    csv_writer = None
    csv_file = None
    if output_file:
        csv_file = open(output_file, 'w', newline='')
        csv_writer = csv.writer(csv_file)

    buffer = ""
    try:
        while True:
            data = sock.recv(4096).decode('utf-8', errors='replace')
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                print(line.rstrip())
                if csv_writer:
                    csv_writer.writerow(line.split(','))
                    csv_file.flush()
    except KeyboardInterrupt:
        print("\nDisconnected.")
    finally:
        sock.close()
        if csv_file:
            csv_file.close()


# --- USB serial connection ---

def usb_stream(port: str, raw_mode: bool = False, baud: int = 115200):
    """Connect via USB serial and parse binary packets."""
    try:
        import serial
    except ImportError:
        print("Error: pyserial not installed. Run: pip install pyserial")
        return

    print(f"Opening {port} at {baud} baud...")
    ser = serial.Serial(port, baud, timeout=1)
    parser = UARTProtocol()

    try:
        while True:
            data = ser.read(256)
            if data:
                packets = parser.feed(data)
                for ptype, payload in packets:
                    if ptype == 0x01:
                        try:
                            sample = parse_wind_packet(payload)
                            print(sample)
                        except Exception as e:
                            print(f"Wind parse error: {e}")
                    elif ptype == 0x02:
                        if len(payload) == TURB_PACKET_SIZE:
                            try:
                                stats = parse_turb_packet(payload)
                                print(stats)
                            except Exception as e:
                                print(f"Turb parse error: {e}")
                        else:
                            print(f"Status: {payload.decode('utf-8', errors='replace')}")
                    elif ptype == 0x05:
                        try:
                            raw = parse_raw_packet(payload)
                            print(raw)
                        except Exception as e:
                            print(f"Raw parse error: {e}")
    except KeyboardInterrupt:
        print("\nDisconnected.")
    finally:
        ser.close()


# --- Real-time wind rose visualization ---

def visualize_stream(samples: list, max_display: int = 100):
    """Simple text-based wind rose display."""
    if not samples:
        return

    # Show latest
    latest = samples[-1]
    print(f"\r{'─'*60}", end='')
    print(f"\rSPD: {latest.speed:5.2f} m/s │ DIR: {latest.direction:5.1f}° │ "
          f"W: {latest.w:+.3f} │ Ts: {latest.t_sonic_celsius:5.1f}°C", end='')

    # Show mini histogram of directions
    if len(samples) >= 10:
        bins = [0] * 8  # 8 compass directions
        for s in samples[-max_display:]:
            idx = int(s.direction / 45) % 8
            bins[idx] += 1
        max_bin = max(bins) if bins else 1
        dirs = "N NE E SE S SW W NW"
        rose = ""
        for i, b in enumerate(bins):
            bar_len = int(b / max_bin * 10) if max_bin > 0 else 0
            rose += f"{dirs.split()[i]}:{'█'*bar_len} "
        print(f"\n{rose}")


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Aero Cast — real-time wind data receiver")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ble", action="store_true",
                       help="Connect via BLE")
    group.add_argument("--tcp", metavar="HOST:PORT",
                       help="Connect via Wi-Fi TCP (e.g., 192.168.1.100:8000)")
    group.add_argument("--usb", metavar="PORT",
                       help="Connect via USB serial (e.g., /dev/ttyACM0)")
    parser.add_argument("--device", default="aero-cast",
                       help="BLE device name (default: aero-cast)")
    parser.add_argument("--output", "-o", metavar="FILE",
                       help="Log to CSV file")
    parser.add_argument("--raw", action="store_true",
                       help="Show raw TOF data (calibration mode)")
    parser.add_argument("--baud", type=int, default=115200,
                       help="USB baud rate (default: 115200)")
    args = parser.parse_args()

    if args.ble:
        import asyncio
        asyncio.run(ble_stream(args.device))
    elif args.tcp:
        host, _, port = args.tcp.rpartition(':')
        tcp_stream(host, int(port) if port else 8000, args.output)
    elif args.usb:
        usb_stream(args.usb, args.raw, args.baud)

if __name__ == "__main__":
    main()