#!/usr/bin/env python3
"""
Pulse Hound — Interactive Hunt CLI
Control the Pulse Hound over BLE from a terminal: switch modes, trigger DF,
set sensitivity, log data to file.

Usage:
    python3 hunt.py [--device MAC] [--log FILE]
"""

import argparse
import struct
import asyncio
import sys
import time
import json

# BLE characteristic UUIDs
UUID_RSSI = "8e7f1a02-b000-1000-8000-00805f9b34fb"
UUID_SPECTRUM = "8e7f1a03-b000-1000-8000-00805f9b34fb"
UUID_BEARING = "8e7f1a04-b000-1000-8000-00805f9b34fb"
UUID_CLASS = "8e7f1a05-b000-1000-8000-00805f9b34fb"
UUID_MODE = "8e7f1a06-b000-1000-8000-00805f9b34fb"
UUID_BATTERY = "8e7f1a07-b000-1000-8000-00805f9b34fb"
UUID_LOG_CTRL = "8e7f1a08-b000-1000-8000-00805f9b34fb"

CLASS_NAMES = {
    0: "CW/Analog", 1: "WiFi/BLE", 2: "Cellular",
    3: "Radar/UWB", 4: "Thermal", 5: "Unknown",
}
MODE_NAMES = {0: "SWEEP", 1: "DF", 2: "MONITOR", 3: "POWER_SAVE"}


class PulseHoundHunt:
    def __init__(self, log_file=None):
        self.client = None
        self.current_rssi = -80.0
        self.peak_rssi = -80.0
        self.classification = "Unknown"
        self.bearing = 0.0
        self.battery_pct = 100
        self.mode = 0
        self.log_file = log_file
        self.log_fp = None
        self.running = True

    def notification_handler(self, sender, data):
        uuid = str(sender).lower()

        if UUID_RSSI in uuid:
            if len(data) >= 2:
                self.current_rssi = struct.unpack('<h', data[:2])[0] / 100.0
                if self.current_rssi > self.peak_rssi:
                    self.peak_rssi = self.current_rssi
                self._log_entry()

        elif UUID_BEARING in uuid:
            if len(data) >= 4:
                self.bearing = struct.unpack('<H', data[:2])[0] / 10.0
                peak = struct.unpack('<h', data[2:4])[0] / 100.0
                print(f"\n  >>> DF BEARING: {self.bearing:.1f}° (peak {peak:.1f} dBm) <<<\n")

        elif UUID_CLASS in uuid:
            if len(data) >= 1:
                self.classification = CLASS_NAMES.get(data[0], "Unknown")

        elif UUID_BATTERY in uuid:
            if len(data) >= 1:
                self.battery_pct = data[0]

    def _log_entry(self):
        if self.log_fp:
            entry = {
                "timestamp": time.time(),
                "rssi_dbm": self.current_rssi,
                "peak_dbm": self.peak_rssi,
                "class": self.classification,
                "bearing_deg": self.bearing,
                "battery_pct": self.battery_pct,
            }
            self.log_fp.write(json.dumps(entry) + "\n")
            self.log_fp.flush()

    def _display(self):
        """Print a compact status line (overwritten in place)."""
        bar_len = 30
        norm = max(0, min(1, (self.current_rssi + 80) / 85))
        bar = "█" * int(norm * bar_len) + "░" * (bar_len - int(norm * bar_len))
        sys.stdout.write(
            f"\r  RSSI: {self.current_rssi:+6.1f} dBm |{bar}| "
            f"PK: {self.peak_rssi:+6.1f} | {self.classification:10s} | "
            f"BAT: {self.battery_pct:3d}% | BRG: {self.bearing:5.1f}° "
        )
        sys.stdout.flush()

    async def set_mode(self, mode: int):
        """Write mode to the mode characteristic."""
        if self.client:
            await self.client.write_gatt_char(UUID_MODE, bytes([mode]))
            self.mode = mode
            print(f"\n  Mode set to: {MODE_NAMES.get(mode, '???')}")

    async def toggle_logging(self, enabled: bool):
        """Enable/disable SD card logging on the device."""
        if self.client:
            await self.client.write_gatt_char(UUID_LOG_CTRL, bytes([1 if enabled else 0]))

    async def run(self, device_addr):
        from bleak import BleakClient, BleakScanner

        # Scan if needed
        if device_addr is None:
            print("Scanning for 'Pulse Hound'...")
            devices = await BleakScanner.discover(timeout=10.0)
            for d in devices:
                if d.name and "Pulse Hound" in d.name:
                    device_addr = d.address
                    print(f"Found: {d.name} [{d.address}]")
                    break
            if device_addr is None:
                print("No Pulse Hound found.")
                return

        # Open log file
        if self.log_file:
            self.log_fp = open(self.log_file, "w")
            self.log_fp.write("# Pulse Hound hunt log\n")

        # Connect
        print(f"Connecting to {device_addr}...")
        self.client = BleakClient(device_addr)
        await self.client.connect()
        print(f"Connected: {self.client.is_connected}")

        # Subscribe to notifications
        for uuid in [UUID_RSSI, UUID_BEARING, UUID_CLASS, UUID_BATTERY]:
            await self.client.start_notify(uuid, self.notification_handler)

        print("\nPulse Hound Hunt CLI — Commands:")
        print("  [s] Sweep mode    [d] DF mode    [m] Monitor mode")
        print("  [p] Power save    [l] Toggle SD log    [q] Quit")
        print()

        # Start keyboard input task + display task
        loop = asyncio.get_event_loop()
        input_task = loop.create_task(self._keyboard_loop())
        display_task = loop.create_task(self._display_loop())

        try:
            await input_task
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            display_task.cancel()
            for uuid in [UUID_RSSI, UUID_BEARING, UUID_CLASS, UUID_BATTERY]:
                await self.client.stop_notify(uuid)
            await self.client.disconnect()
            if self.log_fp:
                self.log_fp.close()
            print("\nDisconnected. Good hunting!")

    async def _keyboard_loop(self):
        """Read keyboard input in a loop."""
        import termios, tty, select
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())
        try:
            while self.running:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    ch = sys.stdin.read(1)
                    if ch == 'q':
                        self.running = False
                        break
                    elif ch == 's':
                        await self.set_mode(0)
                    elif ch == 'd':
                        await self.set_mode(1)
                    elif ch == 'm':
                        await self.set_mode(2)
                    elif ch == 'p':
                        await self.set_mode(3)
                    elif ch == 'l':
                        await self.toggle_logging(True)
                        print("\n  SD logging: ON")
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    async def _display_loop(self):
        """Update the status display every 200 ms."""
        while self.running:
            self._display()
            await asyncio.sleep(0.2)


def main():
    parser = argparse.ArgumentParser(description="Pulse Hound Hunt CLI")
    parser.add_argument("--device", default=None, help="Device MAC address")
    parser.add_argument("--log", default=None, help="Log file (JSON lines)")
    args = parser.parse_args()

    hunter = PulseHoundHunt(log_file=args.log)
    asyncio.run(hunter.run(args.device))


if __name__ == "__main__":
    main()