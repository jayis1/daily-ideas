#!/usr/bin/env python3
"""
helio_app.py — Helio Tilt BLE companion app

A Python BLE client / plotter for the Helio Tilt pocket tracking
pyrheliometer and aerosol optical depth meter. Connects over BLE,
subscribes to the Measurement, Langley, and Status characteristics,
and plots live DNI, AOD, Ångström exponent, and PWV.

Usage:
    python3 helio_app.py [--mac AA:BB:CC:DD:EE:FF]

Requirements:
    pip install bleak numpy matplotlib

Press 's' to start tracking, 'l' for Langley calibration,
'a' to abort, 'q' to quit.
"""

import argparse
import asyncio
import struct
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

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
SERVICE_UUID    = "0000fe30-0000-1000-8000-00805f9b34fb"
MEAS_UUID       = "0000fe31-0000-1000-8000-00805f9b34fb"
LANGLEY_UUID    = "0000fe32-0000-1000-8000-00805f9b34fb"
COMMAND_UUID    = "0000fe33-0000-1000-8000-00805f9b34fb"
STATUS_UUID     = "0000fe34-0000-1000-8000-00805f9b34fb"
SETTINGS_UUID   = "0000fe35-0000-1000-8000-00805f9b34fb"
ERROR_UUID      = "0000fe36-0000-1000-8000-00805f9b34fb"

# Packet types
PKT_START   = 0xAA
PKT_MEAS    = 0x01
PKT_LANGLEY = 0x02
PKT_ERROR   = 0x03
PKT_STATUS  = 0x04

# Commands
CMD_START      = 0x01
CMD_STOP       = 0x02
CMD_LANGLEY    = 0x03
CMD_SET_PRES   = 0x04
CMD_SET_OZONE  = 0x05
CMD_MAG_CAL    = 0x06

# Wavelengths
WAVELENGTHS = [405, 440, 675, 870, 940, 1640]


@dataclass
class Measurement:
    sun_az: float = 0.0
    sun_el: float = 0.0
    zenith: float = 0.0
    air_mass: float = 0.0
    dni: List[float] = field(default_factory=lambda: [0.0]*6)
    aod: List[float] = field(default_factory=lambda: [0.0]*6)
    angstrom: float = 0.0
    pwv_cm: float = 0.0
    bat_v: float = 0.0
    timestamp: Optional[datetime] = None


@dataclass
class LangleyProgress:
    points: int = 0
    r2_870: float = 0.0
    v0_870: float = 0.0


@dataclass
class HelioState:
    latest_meas: Optional[Measurement] = None
    langley: Optional[LangleyProgress] = None
    status: str = "IDLE"
    error: Optional[str] = None
    measurements: List[Measurement] = field(default_factory=list)


state = HelioState()


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


def parse_measurement(payload: bytes) -> Measurement:
    """Parse measurement packet → Measurement."""
    m = Measurement()
    m.sun_az = struct.unpack_from('<f', payload, 0)[0]
    m.sun_el = struct.unpack_from('<f', payload, 4)[0]
    m.zenith = struct.unpack_from('<f', payload, 8)[0]
    m.air_mass = struct.unpack_from('<f', payload, 12)[0]
    m.dni = list(struct.unpack_from('<6f', payload, 16))
    m.aod = list(struct.unpack_from('<6f', payload, 40))
    m.angstrom = struct.unpack_from('<f', payload, 64)[0]
    m.pwv_cm = struct.unpack_from('<f', payload, 68)[0]
    m.bat_v = struct.unpack_from('<f', payload, 72)[0]
    m.timestamp = datetime.now()
    return m


def parse_langley(payload: bytes) -> LangleyProgress:
    """Parse Langley progress packet."""
    points = struct.unpack_from('<H', payload, 0)[0]
    r2 = struct.unpack_from('<f', payload, 2)[0]
    v0 = struct.unpack_from('<f', payload, 6)[0]
    return LangleyProgress(points=points, r2_870=r2, v0_870=v0)


def parse_status(payload: bytes) -> str:
    """Parse status packet → state string."""
    state_len = payload[0]
    return payload[1:1+state_len].decode('ascii', errors='replace')


def notification_handler(sender, data: bytearray):
    """Handle BLE notifications."""
    result = parse_packet(bytes(data))
    if result is None:
        return
    pkt_type, payload = result

    if pkt_type == PKT_MEAS:
        m = parse_measurement(payload)
        state.latest_meas = m
        state.measurements.append(m)
        if len(state.measurements) > 3600:
            state.measurements.pop(0)
    elif pkt_type == PKT_LANGLEY:
        state.langley = parse_langley(payload)
    elif pkt_type == PKT_STATUS:
        state.status = parse_status(payload)
    elif pkt_type == PKT_ERROR:
        state.error = payload.decode('ascii', errors='replace')
        print(f"Device error: {state.error}")


def make_command(cmd: int, payload: bytes = b'') -> bytes:
    """Build a command packet."""
    data = bytes([PKT_START, cmd, 0, len(payload)]) + payload
    data += bytes([crc8(payload)])
    return data


async def run(mac: str):
    print(f"Scanning for Helio Tilt...")

    if mac is None:
        devices = await BleakScanner.discover(timeout=10.0)
        helio = None
        for d in devices:
            if SERVICE_UUID in (d.metadata or {}).get('uuids', []):
                helio = d
                break
        if helio is None:
            print("Helio Tilt not found. Specify MAC with --mac")
            return
        mac = helio.address

    print(f"Connecting to {mac}...")
    async with BleakClient(mac) as client:
        print(f"Connected. Subscribing to characteristics...")

        await client.start_notify(MEAS_UUID, notification_handler)
        await client.start_notify(LANGLEY_UUID, notification_handler)
        await client.start_notify(STATUS_UUID, notification_handler)
        await client.start_notify(ERROR_UUID, notification_handler)

        print("Connected! Press 's' to start, 'l' for Langley, 'q' to quit.")

        # Set up matplotlib live plot
        plt.ion()
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle("Helio Tilt — Live Solar Radiometry")

        ax_dni = axes[0, 0]
        ax_aod = axes[0, 1]
        ax_ang = axes[1, 0]
        ax_pwv = axes[1, 1]

        ax_dni.set_title("DNI (W/m²)")
        ax_dni.set_ylim(0, 1400)
        ax_aod.set_title("AOD at 6 wavelengths")
        ax_ang.set_title("Ångström Exponent")
        ax_pwv.set_title("Precipitable Water Vapor (cm)")

        try:
            while True:
                await asyncio.sleep(0.1)

                # Update plots
                if state.latest_meas:
                    m = state.latest_meas

                    # DNI bar chart
                    ax_dni.clear()
                    ax_dni.bar(range(6), m.dni, tick_label=WAVELENGTHS)
                    ax_dni.set_title(f"DNI (W/m²) — DNI870={m.dni[3]:.0f}")
                    ax_dni.set_ylim(0, 1400)

                    # AOD bar chart
                    ax_aod.clear()
                    ax_aod.bar(range(6), m.aod, tick_label=WAVELENGTHS)
                    ax_aod.set_title(f"AOD — AOD870={m.aod[3]:.3f}")
                    ax_aod.set_ylim(0, 1.0)

                    # Angstrom
                    ax_ang.clear()
                    ax_ang.text(0.1, 0.5, f"α = {m.angstrom:.2f}",
                               transform=ax_ang.transAxes, fontsize=24)
                    ax_ang.set_title("Ångström Exponent")

                    # PWV
                    ax_pwv.clear()
                    ax_pwv.text(0.1, 0.5, f"PWV = {m.pwv_cm:.2f} cm",
                               transform=ax_pwv.transAxes, fontsize=24)
                    ax_pwv.set_title("Precipitable Water Vapor")

                    fig.suptitle(
                        f"Helio Tilt | Status: {state.status} | "
                        f"Sun: Az={m.sun_az:.0f}° El={m.sun_el:.0f}° | "
                        f"Bat: {m.bat_v:.2f}V"
                    )

                    fig.canvas.draw()
                    fig.canvas.flush_events()

        except KeyboardInterrupt:
            print("\nDisconnecting...")

        await client.stop_notify(MEAS_UUID)
        await client.stop_notify(LANGLEY_UUID)
        await client.stop_notify(STATUS_UUID)
        await client.stop_notify(ERROR_UUID)

    # Save data
    if state.measurements:
        filename = f"helio_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, 'w') as f:
            f.write("timestamp,sun_az,sun_el,zenith,air_mass,"
                    "dni_405,dni_440,dni_675,dni_870,dni_940,dni_1640,"
                    "aod_405,aod_440,aod_675,aod_870,aod_940,aod_1640,"
                    "angstrom,pwv_cm,bat_v\n")
            for m in state.measurements:
                f.write(f"{m.timestamp.isoformat()},"
                       f"{m.sun_az},{m.sun_el},{m.zenith},{m.air_mass},"
                       f"{','.join(str(d) for d in m.dni)},"
                       f"{','.join(str(a) for a in m.aod)},"
                       f"{m.angstrom},{m.pwv_cm},{m.bat_v}\n")
        print(f"Data saved to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Helio Tilt BLE companion")
    parser.add_argument("--mac", default=None, help="Device MAC address")
    args = parser.parse_args()

    asyncio.run(run(args.mac))


if __name__ == "__main__":
    main()