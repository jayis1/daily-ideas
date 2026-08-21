#!/usr/bin/env python3
"""
Therma Weave — BLE Control Script
Control heating zones, monitor temperatures, and manage safety via Bluetooth LE.

Usage:
    python3 therma_weave_ble.py --mac AA:BB:CC:DD:EE:FF --zone 0 --target 40
    python3 therma_weave_ble.py --mac AA:BB:CC:DD:EE:FF --status
    python3 therma_weave_ble.py --mac AA:BB:CC:DD:EE:FF --shutdown

SPDX-License-Identifier: MIT
"""

import asyncio
import argparse
import struct
import sys

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("ERROR: bleak library not installed. Run: pip install bleak")
    sys.exit(1)

# BLE UUIDs
THERMA_SERVICE_UUID = "0000ffb0-0000-1000-8000-00805f9b34fb"
ENV_SERVICE_UUID = "0000181a-0000-1000-8000-00805f9b34fb"

# ThermaWeave Control Characteristics
CHAR_ZONE0_TARGET = "0000ffb1-0000-1000-8000-00805f9b34fb"
CHAR_ZONE1_TARGET = "0000ffb2-0000-1000-8000-00805f9b34fb"
CHAR_ZONE2_TARGET = "0000ffb3-0000-1000-8000-00805f9b34fb"
CHAR_ZONE3_TARGET = "0000ffb4-0000-1000-8000-00805f9b34fb"
CHAR_ZONE0_DUTY   = "0000ffb5-0000-1000-8000-00805f9b34fb"
CHAR_ZONE1_DUTY   = "0000ffb6-0000-1000-8000-00805f9b34fb"
CHAR_ZONE2_DUTY   = "0000ffb7-0000-1000-8000-00805f9b34fb"
CHAR_ZONE3_DUTY   = "0000ffb8-0000-1000-8000-00805f9b34fb"
CHAR_ZONE0_CURRENT= "0000ffb9-0000-1000-8000-00805f9b34fb"
CHAR_ZONE1_CURRENT= "0000ffba-0000-1000-8000-00805f9b34fb"
CHAR_ZONE2_CURRENT= "0000ffbb-0000-1000-8000-00805f9b34fb"
CHAR_ZONE3_CURRENT= "0000ffbc-0000-1000-8000-00805f9b34fb"
CHAR_ACTIVITY     = "0000ffbd-0000-1000-8000-00805f9b34fb"
CHAR_ENABLE       = "0000ffbe-0000-1000-8000-00805f9b34fb"
CHAR_SAFETY       = "0000ffbf-0000-1000-8000-00805f9b34fb"
CHAR_FAULT        = "0000ffc0-0000-1000-8000-00805f9b34fb"
CHAR_PID_KP       = "0000ffc1-0000-1000-8000-00805f9b34fb"
CHAR_PID_KI       = "0000ffc2-0000-1000-8000-00805f9b34fb"
CHAR_PID_KD       = "0000ffc3-0000-1000-8000-00805f9b34fb"
CHAR_DEVICE_INFO  = "0000ffff-0000-1000-8000-00805f9b34fb"

# Environmental Sensing Characteristics
CHAR_ZONE0_TEMP   = "00002a6e-0000-1000-8000-00805f9b34fb"
CHAR_AMBIENT_TEMP = "00002a1c-0000-1000-8000-00805f9b34fb"
CHAR_HUMIDITY     = "00002a6f-0000-1000-8000-00805f9b34fb"

ZONE_TARGET_CHARS = [CHAR_ZONE0_TARGET, CHAR_ZONE1_TARGET, CHAR_ZONE2_TARGET, CHAR_ZONE3_TARGET]
ZONE_DUTY_CHARS   = [CHAR_ZONE0_DUTY, CHAR_ZONE1_DUTY, CHAR_ZONE2_DUTY, CHAR_ZONE3_DUTY]
ZONE_CURRENT_CHARS= [CHAR_ZONE0_CURRENT, CHAR_ZONE1_CURRENT, CHAR_ZONE2_CURRENT, CHAR_ZONE3_CURRENT]

ACTIVITY_LABELS = {0: "STILL", 1: "WALKING", 2: "RUNNING", 3: "FALL"}

FAULT_LABELS = {
    0x01: "OVERCURRENT",
    0x02: "OVERTEMP",
    0x04: "THERMISTOR_OPEN",
    0x08: "THERMISTOR_SHORT",
    0x10: "LOW_BATTERY",
    0x20: "WATCHDOG",
    0x40: "COMM_ERROR",
}


class ThermaWeaveClient:
    """BLE client for Therma Weave heated textile controller."""

    def __init__(self, mac_address: str):
        self.mac = mac_address
        self.client = BleakClient(mac_address)

    async def connect(self):
        await self.client.connect()
        print(f"Connected to Therma Weave at {self.mac}")

    async def disconnect(self):
        await self.client.disconnect()
        print("Disconnected")

    async def read_float(self, char_uuid: str) -> float:
        data = await self.client.read_gatt_char(char_uuid)
        return struct.unpack('<f', data)[0]

    async def write_uint8(self, char_uuid: str, value: int):
        await self.client.write_gatt_char(char_uuid, struct.pack('<B', value))

    async def write_uint16(self, char_uuid: str, value: int):
        await self.client.write_gatt_char(char_uuid, struct.pack('<H', value))

    async def read_uint8(self, char_uuid: str) -> int:
        data = await self.client.read_gatt_char(char_uuid)
        return struct.unpack('<B', data)[0]

    async def read_uint16(self, char_uuid: str) -> int:
        data = await self.client.read_gatt_char(char_uuid)
        return struct.unpack('<H', data)[0]

    async def set_target_temp(self, zone: int, temp: float):
        """Set target temperature for a zone (30-55°C)."""
        if zone < 0 or zone > 3:
            raise ValueError(f"Zone must be 0-3, got {zone}")
        if temp < 30 or temp > 55:
            raise ValueError(f"Target must be 30-55°C, got {temp}")
        await self.write_uint8(ZONE_TARGET_CHARS[zone], int(temp))
        print(f"Zone {zone}: target temperature set to {int(temp)}°C")

    async def enable_zones(self, bitmask: int):
        """Enable zones by bitmask (bit0=Z0, bit1=Z1, bit2=Z2, bit3=Z3)."""
        await self.write_uint8(CHAR_ENABLE, bitmask)
        enabled = []
        for z in range(4):
            if bitmask & (1 << z):
                enabled.append(f"Z{z}")
        print(f"Enabled zones: {', '.join(enabled)}")

    async def emergency_shutdown(self):
        """Emergency shutdown all heaters."""
        await self.write_uint8(CHAR_SAFETY, 0x01)
        print("⚠️  EMERGENCY SHUTDOWN — all heaters disabled")

    async def reset_faults(self):
        """Reset all fault flags."""
        await self.write_uint8(CHAR_SAFETY, 0x02)
        print("All faults reset")

    async def read_zone_temps(self) -> list:
        """Read temperature from all zones."""
        temps = []
        for z in range(4):
            try:
                temp = await self.read_float(CHAR_ZONE0_TEMP) if z == 0 else 0.0
                # Read each zone's temp characteristic
                temps.append(temp)
            except Exception:
                temps.append(float('nan'))
        return temps

    async def read_zone_duties(self) -> list:
        """Read duty cycle from all zones."""
        duties = []
        for z in range(4):
            try:
                duty = await self.read_uint8(ZONE_DUTY_CHARS[z])
                duties.append(duty)
            except Exception:
                duties.append(0)
        return duties

    async def read_zone_currents(self) -> list:
        """Read current from all zones (mA)."""
        currents = []
        for z in range(4):
            try:
                current = await self.read_uint16(ZONE_CURRENT_CHARS[z])
                currents.append(current)
            except Exception:
                currents.append(0)
        return currents

    async def read_fault_status(self) -> int:
        """Read fault status bitmap."""
        return await self.read_uint8(CHAR_FAULT)

    async def read_activity(self) -> int:
        """Read activity level."""
        return await self.read_uint8(CHAR_ACTIVITY)

    async def print_status(self):
        """Print full device status."""
        print("\n╔══════════════════════════════════════════╗")
        print("║     THERMA WEAVE — Device Status        ║")
        print("╠══════════════════════════════════════════╣")

        # Zone status
        duties = await self.read_zone_duties()
        currents = await self.read_zone_currents()
        targets = []
        for z in range(4):
            try:
                t = await self.read_uint8(ZONE_TARGET_CHARS[z])
                targets.append(t)
            except Exception:
                targets.append(0)

        print("║ Zone │ Target │ Duty │ Current          ║")
        print("║──────┼────────┼──────┼──────────         ║")
        for z in range(4):
            print(f"║  Z{z}  │ {targets[z]:2d}°C  │ {duties[z]:3d}% │ {currents[z]:4d} mA         ║")

        # Fault status
        faults = await self.read_fault_status()
        if faults:
            fault_names = []
            for bit, name in FAULT_LABELS.items():
                if faults & bit:
                    fault_names.append(name)
            print(f"║ ⚠️  FAULTS: {', '.join(fault_names)}")
        else:
            print("║ ✓  No faults")

        # Activity
        activity = await self.read_activity()
        act_label = ACTIVITY_LABELS.get(activity, "UNKNOWN")
        print(f"║ Activity: {act_label}")

        print("╚══════════════════════════════════════════╝\n")

    async def set_pid(self, kp: float, ki: float, kd: float):
        """Set PID parameters for all zones."""
        await self.client.write_gatt_char(CHAR_PID_KP, struct.pack('<f', kp))
        await self.client.write_gatt_char(CHAR_PID_KI, struct.pack('<f', ki))
        await self.client.write_gatt_char(CHAR_PID_KD, struct.pack('<f', kd))
        print(f"PID parameters set: Kp={kp}, Ki={ki}, Kd={kd}")


async def scan_for_devices():
    """Scan for Therma Weave BLE devices."""
    print("Scanning for Therma Weave devices...")
    devices = await BleakScanner.discover(timeout=10.0)
    found = []
    for device in devices:
        if device.name and "Therma" in device.name:
            found.append(device)
            print(f"  Found: {device.name} at {device.address}")
    if not found:
        print("  No Therma Weave devices found.")
    return found


async def main():
    parser = argparse.ArgumentParser(description="Therma Weave BLE Control")
    parser.add_argument("--mac", required=False, help="Device MAC address")
    parser.add_argument("--scan", action="store_true", help="Scan for devices")
    parser.add_argument("--zone", type=int, help="Zone number (0-3)")
    parser.add_argument("--target", type=float, help="Target temperature (30-55°C)")
    parser.add_argument("--enable", type=int, help="Zone enable bitmask (0-15)")
    parser.add_argument("--disable", action="store_true", help="Disable all zones")
    parser.add_argument("--shutdown", action="store_true", help="Emergency shutdown")
    parser.add_argument("--reset-faults", action="store_true", help="Reset all faults")
    parser.add_argument("--status", action="store_true", help="Print device status")
    parser.add_argument("--kp", type=float, help="PID proportional gain")
    parser.add_argument("--ki", type=float, help="PID integral gain")
    parser.add_argument("--kd", type=float, help="PID derivative gain")

    args = parser.parse_args()

    if args.scan:
        await scan_for_devices()
        return

    if not args.mac:
        print("ERROR: --mac is required (use --scan to find devices)")
        parser.print_help()
        return

    tw = ThermaWeaveClient(args.mac)
    await tw.connect()

    try:
        if args.status:
            await tw.print_status()

        if args.target is not None and args.zone is not None:
            await tw.set_target_temp(args.zone, args.target)

        if args.enable is not None:
            await tw.enable_zones(args.enable)

        if args.disable:
            await tw.enable_zones(0x00)

        if args.shutdown:
            await tw.emergency_shutdown()

        if args.reset_faults:
            await tw.reset_faults()

        if args.kp is not None and args.ki is not None and args.kd is not None:
            await tw.set_pid(args.kp, args.ki, args.kd)

        # If no specific action, print status
        if not any([args.target, args.enable is not None, args.disable,
                     args.shutdown, args.reset_faults, args.kp is not None]):
            await tw.print_status()

    finally:
        await tw.disconnect()


if __name__ == "__main__":
    asyncio.run(main())