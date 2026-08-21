#!/usr/bin/env python3
"""
hall-puck / scripts / live_stream.py
Live BLE client for Hall Puck — displays real-time measurement data.

Connects to the Hall Puck BLE peripheral, subscribes to the data stream
and result characteristics, and displays live voltage readings plus
the final measurement result.

Usage:
    python3 live_stream.py

Requires: bleak, rich
    pip install bleak rich
"""

import asyncio
import struct
import sys
from collections import deque
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout
from bleak import BleakClient, BleakScanner

# BLE UUIDs (match firmware)
UUID_SERVICE = "00009201-0000-1000-8000-00805f9b34fb"
UUID_DATA    = "00009202-0000-1000-8000-00805f9b34fb"
UUID_RESULT  = "00009203-0000-1000-8000-00805f9b34fb"
UUID_CMD     = "00009204-0000-1000-8000-00805f9b34fb"
UUID_INFO    = "00009205-0000-1000-8000-00805f9b34fb"

# Command codes
CMD_START    = 0x01
CMD_STOP     = 0x02
CMD_SET_CUR  = 0x03
CMD_SET_THK  = 0x04
CMD_SET_MODE = 0x05
CMD_CALIB    = 0x06
CMD_GET_INFO = 0x07

# Config names
CONFIG_NAMES = [
    "VDP_Ra_fwd", "VDP_Ra_rev", "VDP_Rb_fwd", "VDP_Rb_rev",
    "HALL_B+_fwd", "HALL_B+_rev", "HALL_B-_fwd", "HALL_B-_rev",
    "Check_1", "Check_2", "Check_3", "Check_4",
    "Short_Zero", "Off",
]

console = Console()


class HallPuckStream:
    def __init__(self):
        self.points = deque(maxlen=100)
        self.result = None
        self.connected = False

    def parse_data(self, data: bytes):
        """Parse a data point notification (20 bytes)."""
        if len(data) < 18:
            return
        config = data[0]
        idx = data[1]
        voltage_uv, current_ma, b_field, temp = struct.unpack('<ffff', data[2:18])
        config_name = CONFIG_NAMES[config] if config < len(CONFIG_NAMES) else f"Cfg{config}"
        self.points.append({
            'idx': idx,
            'config': config_name,
            'voltage_uv': voltage_uv,
            'current_ma': current_ma,
            'b_field': b_field,
            'temp': temp,
        })

    def parse_result(self, data: bytes):
        """Parse the result notification (28 bytes)."""
        if len(data) < 28:
            return
        rs, rh, conc, mob, rho = struct.unpack('<fffff', data[0:20])
        carrier_type = data[20]
        status = data[21]
        temp_x100 = struct.unpack('<h', data[22:24])[0]
        b_field = struct.unpack('<f', data[24:28])[0]

        type_str = {0: "Unknown", 1: "n-type", 2: "p-type"}.get(carrier_type, "?")
        status_str = {0: "OK", 1: "Error", 2: "Warning"}.get(status, "?")

        self.result = {
            'sheet_resistance': rs,
            'hall_coefficient': rh,
            'carrier_conc': conc,
            'mobility': mob,
            'resistivity': rho,
            'carrier_type': type_str,
            'status': status_str,
            'temperature': temp_x100 / 100.0,
            'b_field': b_field,
        }

    def render(self) -> Panel:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="points"),
            Layout(name="result", size=12),
        )

        # Header
        header = Table(show_header=False, box=None)
        header.add_row("Hall Puck — Live Monitor",
                       f"{'Connected' if self.connected else 'Disconnected'}")
        layout["header"].update(Panel(header, title="Status"))

        # Points table
        pts_table = Table(show_header=True, header_style="bold cyan")
        pts_table.add_column("Step", width=6)
        pts_table.add_column("Config", width=16)
        pts_table.add_column("I (mA)", width=10)
        pts_table.add_column("V (µV)", width=12)
        pts_table.add_column("B (T)", width=8)
        pts_table.add_column("T (°C)", width=8)

        for p in list(self.points)[-10:]:
            pts_table.add_row(
                str(p['idx']),
                p['config'],
                f"{p['current_ma']:.3f}",
                f"{p['voltage_uv']:.2f}",
                f"{p['b_field']:.4f}",
                f"{p['temp']:.1f}",
            )
        layout["points"].update(Panel(pts_table, title="Live Data Points"))

        # Result
        if self.result:
            r = self.result
            res_table = Table(show_header=False, header_style="bold")
            res_table.add_column("Parameter", style="cyan")
            res_table.add_column("Value", style="white")
            res_table.add_row("Carrier Type", r['carrier_type'])
            res_table.add_row("Sheet Resistance", f"{r['sheet_resistance']:.2f} Ω/□")
            res_table.add_row("Hall Coefficient", f"{r['hall_coefficient']:.2f} cm³/C")
            res_table.add_row("Carrier Concentration", f"{r['carrier_conc']:.3e} cm⁻³")
            res_table.add_row("Mobility", f"{r['mobility']:.1f} cm²/V·s")
            res_table.add_row("Resistivity", f"{r['resistivity']:.4f} Ω·cm")
            res_table.add_row("Temperature", f"{r['temperature']:.1f} °C")
            res_table.add_row("B-field", f"{r['b_field']:.3f} T")
            res_table.add_row("Status", r['status'])
            layout["result"].update(Panel(res_table, title="Measurement Result"))
        else:
            layout["result"].update(Panel("Waiting for result...", title="Result"))

        return Panel(layout, title="Hall Puck")


async def main():
    console.print("[bold cyan]Scanning for Hall Puck...[/]")

    devices = await BleakScanner.discover(timeout=10)
    target = None
    for d in devices:
        if d.name and "HallPuck" in d.name:
            target = d
            break

    if not target:
        console.print("[red]Hall Puck not found![/]")
        console.print("Make sure the device is powered on and advertising.")
        sys.exit(1)

    console.print(f"[green]Found: {target.name} ({target.address})[/]")

    stream = HallPuckStream()
    stream.connected = True

    async with BleakClient(target) as client:
        # Subscribe to notifications
        await client.start_notify(UUID_DATA, lambda _, d: stream.parse_data(d))
        await client.start_notify(UUID_RESULT, lambda _, d: stream.parse_result(d))

        console.print("[green]Connected. Press Enter to start measurement.[/]")
        console.print("[dim]Commands: ENTER=start, q=quit, c=calibrate[/]")

        with Live(stream.render(), refresh_per_second=4, console=console) as live:
            while True:
                live.update(stream.render())
                await asyncio.sleep(0.25)

                # Non-blocking input check (simplified)
                # In production: use asyncio with stdin reader
                try:
                    await asyncio.wait_for(asyncio.sleep(0.1), timeout=0.1)
                except asyncio.TimeoutError:
                    pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Disconnected.[/]")