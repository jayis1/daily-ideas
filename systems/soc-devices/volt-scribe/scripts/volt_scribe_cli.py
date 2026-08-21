#!/usr/bin/env python3
"""
volt_scribe_cli.py — Python CLI for Volt Scribe BLE control & plotting

Requires: bleak, matplotlib, numpy
Install: pip install bleak matplotlib numpy

Usage:
    python3 volt_scribe_cli.py --port /dev/ttyUSB0          # USB serial
    python3 volt_scribe_cli.py --ble AA:BB:CC:DD:EE:FF     # BLE
    python3 volt_scribe_cli.py --plot cv cv_data.csv          # Plot saved data
"""

import argparse
import struct
import asyncio
import sys
import csv
import math
from pathlib import Path

# BLE UART Service UUIDs (Nordic UART Protocol)
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

# Frame protocol
FRAME_HEADER = bytes([0xAA, 0x55])
TYPE_DATA_POINT = 0x01
TYPE_EIS_POINT = 0x02
TYPE_STATUS = 0x03
TYPE_PEAK = 0x04
TYPE_RANDLES = 0x05
TYPE_EXP_START = 0x06
TYPE_EXP_END = 0x07


def crc8(data: bytes) -> int:
    """CRC-8-CCITT"""
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def parse_frame(data: bytes) -> dict:
    """Parse a binary frame from Volt Scribe."""
    if len(data) < 4:
        return None
    if data[0] != 0xAA or data[1] != 0x55:
        return None

    msg_type = data[2]
    length = data[3]
    payload = data[4:4 + length]
    expected_crc = data[4 + length] if len(data) > 4 + length else None

    if expected_crc is not None and crc8(payload) != expected_crc:
        print(f"CRC error: expected {expected_crc:02X}, got {crc8(payload):02X}")
        return None

    result = {"type": msg_type}

    if msg_type == TYPE_DATA_POINT and length == 8:
        e, i = struct.unpack("<ff", payload)
        result["E"] = e
        result["I"] = i
    elif msg_type == TYPE_EIS_POINT and length == 12:
        zr, zi, freq = struct.unpack("<fff", payload)
        result["Z_real"] = zr
        result["Z_imag"] = zi
        result["freq"] = freq
    elif msg_type == TYPE_PEAK and length == 9:
        e, i_val = struct.unpack("<ff", payload[:8])
        pk_type = payload[8]
        result["E"] = e
        result["I"] = i_val
        result["peak_type"] = "anodic" if pk_type == 0 else "cathodic"
    elif msg_type == TYPE_RANDLES and length == 16:
        rs, rct, cdl, alpha = struct.unpack("<ffff", payload)
        result["R_s"] = rs
        result["R_ct"] = rct
        result["C_dl"] = cdl
        result["alpha"] = alpha
    elif msg_type == TYPE_EXP_START and length == 5:
        technique = payload[0]
        n_points = struct.unpack("<I", payload[1:5])[0]
        result["technique"] = technique
        result["n_points"] = n_points
    elif msg_type == TYPE_EXP_END and length == 1:
        result["status"] = payload[0]

    return result


def try_import_matplotlib():
    """Try to import matplotlib, return None if unavailable."""
    try:
        import matplotlib.pyplot as plt
        return plt
    except ImportError:
        print("matplotlib not available. Install with: pip install matplotlib")
        return None


def try_import_numpy():
    """Try to import numpy, return None if unavailable."""
    try:
        import numpy as np
        return np
    except ImportError:
        print("numpy not available. Install with: pip install numpy")
        return None


def plot_cv(filename: str):
    """Plot a cyclic voltammogram from CSV file."""
    plt = try_import_matplotlib()
    if plt is None:
        return

    E_vals, I_vals = [], []
    with open(filename, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].startswith("#"):
                print(row[0])
                continue
            try:
                E_vals.append(float(row[0]))
                I_vals.append(float(row[1]) * 1e6)  # Convert to µA
            except (ValueError, IndexError):
                continue

    if not E_vals:
        print("No data found in file.")
        return

    plt.figure(figsize=(8, 6))
    plt.plot(E_vals, I_vals, "b-", linewidth=1)
    plt.xlabel("Potential (V)")
    plt.ylabel("Current (µA)")
    plt.title("Cyclic Voltammogram")
    plt.grid(True, alpha=0.3)
    plt.axhline(y=0, color="k", linewidth=0.5)
    plt.axvline(x=0, color="k", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(filename.replace(".csv", "_cv.png"), dpi=150)
    plt.show()
    print(f"Plot saved to {filename.replace('.csv', '_cv.png')}")


def plot_eis(filename: str):
    """Plot Nyquist and Bode plots from EIS CSV file."""
    plt = try_import_matplotlib()
    np = try_import_numpy()
    if plt is None or np is None:
        return

    z_real_vals, z_imag_vals, freq_vals = [], [], []
    with open(filename, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].startswith("#"):
                print(row[0])
                continue
            try:
                freq_vals.append(float(row[0]))
                z_real_vals.append(float(row[1]))
                z_imag_vals.append(-float(row[2]))  # Convention: -Z_imag up
            except (ValueError, IndexError):
                continue

    if not freq_vals:
        print("No data found in file.")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Nyquist plot
    ax1.plot(z_real_vals, z_imag_vals, "ro-", markersize=4, linewidth=1)
    ax1.set_xlabel("Z' (Ω)")
    ax1.set_ylabel("-Z'' (Ω)")
    ax1.set_title("Nyquist Plot")
    ax1.grid(True, alpha=0.3)
    ax1.set_aspect("equal")

    # Bode plot
    magnitude = [math.sqrt(zr**2 + zi**2) for zr, zi in
                 zip(z_real_vals, [z * (-1) for z in z_imag_vals])]
    phase = [math.degrees(math.atan2(zi, zr)) for zr, zi in
             zip(z_real_vals, z_imag_vals)]

    ax2.semilogx(freq_vals, magnitude, "b-", label="|Z|")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("|Z| (Ω)", color="b")
    ax2.tick_params(axis="y", labelcolor="b")

    ax2b = ax2.twinx()
    ax2b.semilogx(freq_vals, phase, "r-", label="Phase")
    ax2b.set_ylabel("Phase (°)", color="r")
    ax2b.tick_params(axis="y", labelcolor="r")
    ax2.set_title("Bode Plot")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(filename.replace(".csv", "_eis.png"), dpi=150)
    plt.show()
    print(f"Plot saved to {filename.replace('.csv', '_eis.png')}")


def plot_it(filename: str):
    """Plot amperometric i-t curve from CSV file."""
    plt = try_import_matplotlib()
    if plt is None:
        return

    t_vals, I_vals = [], []
    with open(filename, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].startswith("#"):
                continue
            try:
                t_vals.append(float(row[0]))
                I_vals.append(float(row[1]) * 1e6)  # µA
            except (ValueError, IndexError):
                continue

    if not t_vals:
        print("No data found in file.")
        return

    plt.figure(figsize=(10, 5))
    plt.plot(t_vals, I_vals, "g-", linewidth=1)
    plt.xlabel("Time (s)")
    plt.ylabel("Current (µA)")
    plt.title("Amperometric i-t Curve")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(filename.replace(".csv", "_it.png"), dpi=150)
    plt.show()
    print(f"Plot saved to {filename.replace('.csv', '_it.png')}")


class SerialConnection:
    """Serial (USB CDC) connection to Volt Scribe."""

    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None

    def connect(self):
        import serial
        self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
        print(f"Connected to {self.port} @ {self.baudrate}")

    def send_command(self, cmd: str):
        self.serial.write((cmd + "\r\n").encode())
        response = self.serial.readline().decode().strip()
        return response

    def close(self):
        if self.serial:
            self.serial.close()


class BLEConnection:
    """BLE UART connection to Volt Scribe via ESP32-C3."""

    def __init__(self, address: str):
        self.address = address
        self.client = None

    async def connect_async(self):
        from bleak import BleakClient
        self.client = BleakClient(self.address)
        await self.client.connect()
        print(f"Connected to {self.address}")

        # Enable notifications
        await self.client.start_notify(NUS_TX_CHAR_UUID, self._notification_handler)

    def _notification_handler(self, sender, data: bytearray):
        frame = parse_frame(bytes(data))
        if frame:
            self._handle_frame(frame)

    def _handle_frame(self, frame: dict):
        if frame["type"] == TYPE_DATA_POINT:
            print(f"  E={frame['E']:.4f}V  I={frame['I']*1e6:.2f}µA")
        elif frame["type"] == TYPE_EIS_POINT:
            print(f"  Z'={frame['Z_real']:.0f}Ω  Z''={frame['Z_imag']:.0f}Ω  f={frame['freq']:.0f}Hz")
        elif frame["type"] == TYPE_PEAK:
            print(f"  ★ Peak: E={frame['E']:.3f}V  I={frame['I']*1e6:.2f}µA  ({frame['peak_type']})")
        elif frame["type"] == TYPE_RANDLES:
            print(f"  R_s={frame['R_s']:.0f}Ω  R_ct={frame['R_ct']:.0f}Ω  "
                  f"C_dl={frame['C_dl']*1e6:.2f}µF  α={frame['alpha']:.2f}")
        elif frame["type"] == TYPE_EXP_END:
            print("Experiment complete.")

    async def send_command_async(self, cmd: str):
        if self.client:
            await self.client.write_gatt_char(
                NUS_RX_CHAR_UUID, (cmd + "\r\n").encode()
            )

    async def disconnect_async(self):
        if self.client:
            await self.client.disconnect()


def interactive_mode(conn):
    """Run interactive CLI mode."""
    print("Volt Scribe CLI — type 'help' for commands, 'quit' to exit")
    while True:
        try:
            cmd = input("VS> ").strip()
        except EOFError:
            break
        if not cmd:
            continue
        if cmd.lower() == "quit":
            break
        if cmd.lower() == "plot":
            filename = input("CSV file: ").strip()
            mode = input("Type (cv/eis/it): ").strip().lower()
            if mode == "cv":
                plot_cv(filename)
            elif mode == "eis":
                plot_eis(filename)
            elif mode == "it":
                plot_it(filename)
            continue

        response = conn.send_command(cmd)
        print(response)


def main():
    parser = argparse.ArgumentParser(description="Volt Scribe CLI")
    parser.add_argument("--port", help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--ble", help="BLE device address (e.g., AA:BB:CC:DD:EE:FF)")
    parser.add_argument("--plot", nargs=2, metavar=("TYPE", "FILE"),
                        help="Plot saved data: cv/eis/it <file.csv>")

    args = parser.parse_args()

    if args.plot:
        plot_type, filename = args.plot
        if plot_type == "cv":
            plot_cv(filename)
        elif plot_type == "eis":
            plot_eis(filename)
        elif plot_type == "it":
            plot_it(filename)
        else:
            print(f"Unknown plot type: {plot_type}. Use cv, eis, or it.")
        return

    if args.port:
        conn = SerialConnection(args.port)
        conn.connect()
        interactive_mode(conn)
        conn.close()
    elif args.ble:
        print("BLE mode requires asyncio — use: python3 -m asyncio")
        print("Then: await ble.connect_async()")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()