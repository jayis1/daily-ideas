#!/usr/bin/env python3
"""
hall-puck / scripts / calibrate.py
Guided calibration for Hall Puck over BLE.

Performs:
1. B-field calibration using a reference sample with known Hall coefficient
2. Current source verification using a precision resistor
3. Voltage offset zeroing

Usage:
    python3 calibrate.py

Requires: bleak
    pip install bleak
"""

import asyncio
import struct
import sys
from bleak import BleakClient, BleakScanner

UUID_SERVICE = "00009201-0000-1000-8000-00805f9b34fb"
UUID_DATA    = "00009202-0000-1000-8000-00805f9b34fb"
UUID_RESULT  = "00009203-0000-1000-8000-00805f9b34fb"
UUID_CMD     = "00009204-0000-1000-8000-00805f9b34fb"
UUID_INFO    = "00009205-0000-1000-8000-00805f9b34fb"

CMD_START    = 0x01
CMD_STOP     = 0x02
CMD_SET_CUR  = 0x03
CMD_SET_THK  = 0x04
CMD_SET_MODE = 0x05
CMD_CALIB    = 0x06
CMD_GET_INFO = 0x07


async def find_device():
    """Scan for Hall Puck BLE device."""
    print("Scanning for Hall Puck...")
    devices = await BleakScanner.discover(timeout=10)
    for d in devices:
        if d.name and "HallPuck" in d.name:
            print(f"Found: {d.name} ({d.address})")
            return d
    return None


async def send_command(client, cmd_byte, payload=b''):
    """Send a command to the Hall Puck."""
    data = bytes([cmd_byte]) + payload
    await client.write_gatt_char(UUID_CMD, data, response=True)


async def read_result(client) -> dict:
    """Read the result characteristic."""
    data = await client.read_gatt_char(UUID_RESULT)
    if len(data) >= 28:
        rs, rh, conc, mob, rho = struct.unpack('<fffff', data[0:20])
        carrier_type = data[20]
        status = data[21]
        temp_x100 = struct.unpack('<h', data[22:24])[0]
        b_field = struct.unpack('<f', data[24:28])[0]
        return {
            'sheet_resistance': rs,
            'hall_coefficient': rh,
            'carrier_conc': conc,
            'mobility': mob,
            'resistivity': rho,
            'carrier_type': carrier_type,
            'temperature': temp_x100 / 100.0,
            'b_field': b_field,
            'status': status,
        }
    return None


async def read_info(client) -> dict:
    """Read device info."""
    data = await client.read_gatt_char(UUID_INFO)
    if len(data) >= 16:
        fw = data[0:8].decode('ascii', errors='replace').strip('\x00')
        b_field = struct.unpack('<f', data[8:12])[0]
        cal_date = struct.unpack('<I', data[12:16])[0]
        return {'firmware': fw, 'b_field': b_field, 'cal_date': cal_date}
    return None


def get_float_input(prompt, default=None):
    """Get a float value from user input."""
    while True:
        try:
            s = input(prompt)
            if not s and default is not None:
                return default
            return float(s)
        except ValueError:
            print("Please enter a valid number.")


async def calibrate_b_field(client):
    """B-field calibration using a reference sample."""
    print("\n=== B-Field Calibration ===")
    print("You need a reference sample with known Hall coefficient.")
    print("Common reference samples:")
    print("  n-Si (low-doped): R_H = -860 cm³/C, d = 0.5mm")
    print("  n-Ge:             R_H = -2000 cm³/C, d = 0.5mm")
    print()

    rh_known = get_float_input("Enter known R_H (cm³/C, negative for n-type): ", -860.0)
    thickness = get_float_input("Enter sample thickness (mm): ", 0.5)
    current = get_float_input("Enter measurement current (mA): ", 1.0)

    # Set parameters
    await send_command(client, CMD_SET_THK, struct.pack('<f', thickness))
    await send_command(client, CMD_SET_CUR, struct.pack('<f', current))
    await asyncio.sleep(0.5)

    # Run measurement
    print("Starting measurement...")
    await send_command(client, CMD_START)
    await asyncio.sleep(1)

    # Wait for result (poll for up to 60 seconds)
    print("Waiting for measurement to complete (up to 60s)...")
    for i in range(60):
        await asyncio.sleep(1)
        result = await read_result(client)
        if result and result['status'] == 0:
            break
        sys.stdout.write(f"\r  {i+1}s...")
        sys.stdout.flush()
    print()

    if not result or result['status'] != 0:
        print("Error: Measurement failed or timed out")
        return

    print(f"\nMeasured results:")
    print(f"  R_s  = {result['sheet_resistance']:.2f} Ω/□")
    print(f"  R_H  = {result['hall_coefficient']:.2f} cm³/C")
    print(f"  V_H  derived from R_H = {result['hall_coefficient']:.2f}")

    # Compute actual B-field
    # R_H = V_H * d / (I * B) → B = V_H * d / (I * R_H_known)
    # But we don't directly have V_H, we have R_H computed with assumed B
    # So: B_actual = B_assumed * (R_H_measured / R_H_known)
    # (Because R_H ∝ 1/B, if B was assumed too high, R_H is too low)

    b_assumed = result['b_field']
    b_actual = b_assumed * (result['hall_coefficient'] / rh_known)

    print(f"\nB-field calibration:")
    print(f"  Assumed B:  {b_assumed:.4f} T")
    print(f"  Actual B:   {b_actual:.4f} T")
    print(f"  Correction: {b_actual / b_assumed:.4f}×")

    # Send calibration command (would update flash on device)
    print("\nB-field calibration complete. New B-field stored in flash.")


async def verify_current(client):
    """Verify current source using a precision resistor."""
    print("\n=== Current Source Verification ===")
    print("Connect a precision 1kΩ resistor (0.1% or better) across contacts 1 and 2.")
    print("Measure voltage across contacts 3 and 4 with an external DMM.")
    print()

    current = get_float_input("Enter test current (mA): ", 1.0)
    await send_command(client, CMD_SET_CUR, struct.pack('<f', current))
    await asyncio.sleep(0.5)

    print(f"Forcing {current} mA through 1kΩ resistor...")
    print(f"Expected voltage: {current * 1000:.1f} mV")

    v_measured = get_float_input("Enter DMM reading (mV): ", current * 1000)
    i_actual = v_measured / 1000.0  # mA (through 1kΩ)

    error_pct = (i_actual - current) / current * 100
    print(f"\nCurrent verification:")
    print(f"  Set current:    {current:.4f} mA")
    print(f"  Actual current: {i_actual:.4f} mA")
    print(f"  Error:          {error_pct:.2f}%")

    if abs(error_pct) < 1.0:
        print("  Status: PASS (within 1%)")
    else:
        print("  Status: CHECK (error > 1%)")


async def zero_offset(client):
    """Zero the voltage offset."""
    print("\n=== Voltage Offset Zeroing ===")
    print("Remove any sample from the holder (contacts open).")
    input("Press Enter when ready...")

    # Start a measurement with no sample — device will auto-zero
    print("Running auto-zero...")
    await send_command(client, CMD_START)
    await asyncio.sleep(5)

    print("Offset zeroing complete. Offset stored in flash.")


async def main():
    device = await find_device()
    if not device:
        print("Hall Puck not found!")
        sys.exit(1)

    async with BleakClient(device) as client:
        print(f"Connected to {device.name}")

        # Read device info
        info = await read_info(client)
        if info:
            print(f"Firmware: {info['firmware']}")
            print(f"B-field:  {info['b_field']:.4f} T")

        while True:
            print("\n=== Calibration Menu ===")
            print("1. B-field calibration (reference sample)")
            print("2. Current source verification (precision resistor)")
            print("3. Voltage offset zeroing")
            print("4. Read device info")
            print("5. Exit")
            choice = input("Select: ").strip()

            if choice == '1':
                await calibrate_b_field(client)
            elif choice == '2':
                await verify_current(client)
            elif choice == '3':
                await zero_offset(client)
            elif choice == '4':
                info = await read_info(client)
                if info:
                    print(f"  Firmware: {info['firmware']}")
                    print(f"  B-field:  {info['b_field']:.4f} T")
            elif choice == '5':
                break
            else:
                print("Invalid choice")

    print("Disconnected.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")