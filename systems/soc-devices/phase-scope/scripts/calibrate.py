#!/usr/bin/env python3
"""
Phase Scope — Calibration Tool
Connects to Phase Scope via BLE and performs voltage, current, and phase calibration.

Requirements:
    pip install bleak

Usage:
    python calibrate.py --device BLE_ADDRESS --mode voltage --reference 230.0
    python calibrate.py --device BLE_ADDRESS --mode current --reference 10.0
    python calibrate.py --device BLE_ADDRESS --mode phase --reference 1.0
    python calibrate.py --device BLE_ADDRESS --mode save
    python calibrate.py --device BLE_ADDRESS --mode reset
"""

import argparse
import struct
import sys
import asyncio

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("bleak required: pip install bleak")
    sys.exit(1)

# Nordic UART Service UUIDs
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

# Calibration commands
CAL_VOLTAGE = 0x00
CAL_CURRENT = 0x01
CAL_PHASE = 0x02
CAL_SAVE = 0x03
CAL_RESET = 0x04

# Packet framing
START_BYTES = bytes([0xAA, 0x55])
END_BYTES = bytes([0x0D, 0x0A])


async def scan_device():
    """Scan for Phase Scope BLE devices."""
    print("Scanning for Phase Scope devices...")
    devices = await BleakScanner.discover(timeout=10)

    phase_scopes = []
    for d in devices:
        if d.name and "PhaseScope" in d.name:
            phase_scopes.append(d)
            print(f"  Found: {d.name} ({d.address})")

    if not phase_scopes:
        print("No Phase Scope devices found.")
        return None

    if len(phase_scopes) == 1:
        return phase_scopes[0].address

    print("\nMultiple devices found. Specify --device ADDRESS.")
    return None


async def calibrate(address, mode, reference_value):
    """Perform calibration on Phase Scope."""

    if address is None:
        address = await scan_device()
        if address is None:
            return

    print(f"Connecting to {address}...")

    async with BleakClient(address) as client:
        print(f"Connected!")

        if mode == 'voltage':
            print(f"Starting voltage calibration with reference: {reference_value}V")
            cmd = bytes([0x40, CAL_VOLTAGE])
            await client.write_gatt_char(NUS_RX_CHAR_UUID, START_BYTES + cmd + END_BYTES)
            await asyncio.sleep(2)
            print("Apply the reference voltage to all three phase inputs.")
            print(f"Expected voltage: {reference_value}V")
            input("Press Enter when voltage is stable...")
            # Device measures and computes gain

        elif mode == 'current':
            print(f"Starting current calibration with reference: {reference_value}A")
            cmd = bytes([0x40, CAL_CURRENT])
            await client.write_gatt_char(NUS_RX_CHAR_UUID, START_BYTES + cmd + END_BYTES)
            await asyncio.sleep(2)
            print("Apply the reference current through all three CT clamps.")
            print(f"Expected current: {reference_value}A")
            input("Press Enter when current is stable...")

        elif mode == 'phase':
            print(f"Starting phase calibration with reference PF: {reference_value}")
            cmd = bytes([0x40, CAL_PHASE])
            await client.write_gatt_char(NUS_RX_CHAR_UUID, START_BYTES + cmd + END_BYTES)
            await asyncio.sleep(2)
            print("Apply a resistive load (PF ≈ 1.0) to all three phases.")
            input("Press Enter when load is stable...")

        elif mode == 'save':
            print("Saving calibration constants to flash...")
            cmd = bytes([0x40, CAL_SAVE])
            await client.write_gatt_char(NUS_RX_CHAR_UUID, START_BYTES + cmd + END_BYTES)
            await asyncio.sleep(1)
            print("Calibration saved!")

        elif mode == 'reset':
            print("Resetting calibration to factory defaults...")
            cmd = bytes([0x40, CAL_RESET])
            await client.write_gatt_char(NUS_RX_CHAR_UUID, START_BYTES + cmd + END_BYTES)
            await asyncio.sleep(1)
            print("Calibration reset to defaults!")

    print("Disconnected.")


def main():
    parser = argparse.ArgumentParser(description='Phase Scope Calibration Tool')
    parser.add_argument('--device', '-d', help='BLE device address')
    parser.add_argument('--mode', '-m',
                        choices=['voltage', 'current', 'phase', 'save', 'reset'],
                        required=True,
                        help='Calibration mode')
    parser.add_argument('--reference', '-r', type=float, default=0.0,
                        help='Reference value (voltage in V, current in A, or PF)')
    args = parser.parse_args()

    asyncio.run(calibrate(args.device, args.mode, args.reference))


if __name__ == '__main__':
    main()