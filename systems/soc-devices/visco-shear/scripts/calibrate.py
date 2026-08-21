#!/usr/bin/env python3
"""
visco-shear / scripts / calibrate.py
Guided calibration for Visco Shear pocket rheometer over BLE.

Usage:
    python3 calibrate.py                    # Single-point (silicone oil)
    python3 calibrate.py --two-point        # Two-point (water + glycerin)
    python3 calibrate.py --device <MAC>     # Specify BLE address

Requires: bleak (pip install bleak)
"""
import argparse
import asyncio
import struct
import sys
import time

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("ERROR: bleak not installed. Run: pip install bleak")
    sys.exit(1)

# BLE UUIDs
SERVICE_UUID      = "0000a101-0000-1000-8000-00805f9b34fb"
CHAR_TORQUE       = "0000a102-0000-1000-8000-00805f9b34fb"
CHAR_RESULT       = "0000a103-0000-1000-8000-00805f9b34fb"
CHAR_CMD          = "0000a104-0000-1000-8000-00805f9b34fb"
CHAR_INFO         = "0000a105-0000-1000-8000-00805f9b34fb"

# Reference fluids
SILICONE_OIL_100 = 96.0    # mPa·s at 25°C (NIST-traceable)
WATER_25C        = 0.890   # mPa·s at 25°C
GLYCERIN_25C     = 1412.0  # mPa·s at 25°C

calibration_factor = 1.0


def parse_result(data: bytes) -> dict:
    """Parse measurement result characteristic (32 bytes)."""
    if len(data) < 14:
        return {}
    model_id = data[0]
    r_squared = struct.unpack_from('<f', data, 1)[0]
    avg_visc = struct.unpack_from('<f', data, 5)[0]
    temp = struct.unpack_from('<f', data, 9)[0]
    n_points = data[13]
    params = struct.unpack_from('<4f', data, 14) if len(data) >= 30 else (0,0,0,0)

    model_names = ["Newtonian", "Power-Law", "Bingham", "Herschel-Bulkley",
                   "Casson", "Cross", "Carreau"]

    return {
        "model": model_names[model_id] if model_id < len(model_names) else f"Unknown({model_id})",
        "r_squared": r_squared,
        "avg_viscosity_mPa_s": avg_visc,
        "temperature_c": temp,
        "n_points": n_points,
        "params": params,
    }


async def find_device(name_filter="Visco"):
    """Scan for BLE devices matching the name filter."""
    print(f"Scanning for BLE devices matching '{name_filter}'...")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        if d.name and name_filter.lower() in d.name.lower():
            print(f"  Found: {d.name} ({d.address})")
            return d
    print("ERROR: No Visco Shear device found.")
    return None


async def send_command(client, cmd_byte, payload=b''):
    """Send a command to the device."""
    data = bytes([cmd_byte]) + payload
    await client.write_gatt_char(CHAR_CMD, data, response=True)


async def wait_for_result(client, timeout=120) -> dict:
    """Wait for a measurement result notification."""
    result = {}
    done = asyncio.Event()

    def notification_handler(sender, data):
        nonlocal result
        # Parse based on characteristic UUID
        if hasattr(sender, 'uuid') and 'a103' in str(sender.uuid).lower():
            result = parse_result(data)
            done.set()
        elif 'a103' in str(sender).lower():
            result = parse_result(data)
            done.set()

    await client.start_notify(CHAR_RESULT, notification_handler)
    try:
        await asyncio.wait_for(done.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        print("ERROR: Timed out waiting for measurement result.")
    await client.stop_notify(CHAR_RESULT)
    return result


async def single_point_calibration(client, reference_eta, reference_name):
    """Run a single-point calibration measurement."""
    print(f"\n=== Single-Point Calibration: {reference_name} ===")
    print(f"Expected viscosity: {reference_eta} mPa·s at 25°C")
    print()
    print("Instructions:")
    print("  1. Install CC-13 spindle")
    print("  2. Add 2.0 mL of reference fluid to the sample cup")
    print("  3. Set temperature to 25°C and wait for equilibrium")
    print("  4. Press ENTER to start measurement...")
    input()

    # Send start command (single-speed mode)
    await send_command(client, 0x03, bytes([4]))  # Set mode = SINGLE_SPEED
    await asyncio.sleep(0.5)
    await send_command(client, 0x05, struct.pack('<f', 25.0))  # Set temp = 25°C
    await asyncio.sleep(0.5)
    await send_command(client, 0x01)  # Start measurement

    print("Measurement in progress... (waiting for result)")
    result = await wait_for_result(client, timeout=120)

    if not result or result.get("avg_viscosity_mPa_s", 0) == 0:
        print("ERROR: No valid measurement result received.")
        return None

    measured_eta = result["avg_viscosity_mPa_s"]
    print(f"\nMeasured viscosity: {measured_eta:.2f} mPa·s")
    print(f"Expected viscosity: {reference_eta:.2f} mPa·s")
    print(f"Model: {result['model']}, R² = {result['r_squared']:.5f}")

    cf = reference_eta / measured_eta
    print(f"\nCalibration factor: CF = {reference_eta:.2f} / {measured_eta:.2f} = {cf:.5f}")

    print("\nTo apply this calibration factor:")
    print(f"  Write CF={cf:.5f} to the device via BLE command 0x06")
    print(f"  Or update firmware: torque_set_calibration({cf:.5f}f);")

    return cf


async def two_point_calibration(client):
    """Run a two-point calibration (water + glycerin)."""
    print("\n=== Two-Point Calibration ===")

    # Low-viscosity point: water
    cf1 = await single_point_calibration(client, WATER_25C, "Water (η=0.890 mPa·s)")
    if cf1 is None:
        return

    # High-viscosity point: glycerin
    cf2 = await single_point_calibration(client, GLYCERIN_25C, "Glycerin (η=1412 mPa·s)")
    if cf2 is None:
        return

    # Fit: η_corrected = a × η_measured + b
    # water: 0.890 = a × (0.890/cf1) + b  →  0.890 = cf1 × (0.890/cf1) + b ... simplified
    # For simplicity: a = (GLYCERIN - WATER) / (GLYCERIN/cf2 - WATER/cf1)
    # b = WATER - a × (WATER/cf1)
    m1 = WATER_25C / cf1
    m2 = GLYCERIN_25C / cf2
    a = (GLYCERIN_25C - WATER_25C) / (m2 - m1) if (m2 - m1) != 0 else 1.0
    b = WATER_25C - a * m1

    print(f"\n=== Two-Point Calibration Result ===")
    print(f"  η_corrected = {a:.5f} × η_measured + {b:.5f}")
    print(f"  Water:  measured={m1:.3f} → corrected={a*m1+b:.3f} (expected {WATER_25C})")
    print(f"  Glycer: measured={m2:.3f} → corrected={a*m2+b:.3f} (expected {GLYCERIN_25C})")


async def main():
    parser = argparse.ArgumentParser(description="Visco Shear BLE calibration tool")
    parser.add_argument("--two-point", action="store_true", help="Two-point calibration (water + glycerin)")
    parser.add_argument("--device", type=str, default=None, help="BLE MAC address")
    parser.add_argument("--reference", type=float, default=SILICONE_OIL_100,
                        help="Reference viscosity in mPa·s (default: silicone oil 100cSt = 96)")
    parser.add_argument("--name", type=str, default="silicone oil 100cSt",
                        help="Reference fluid name")
    args = parser.parse_args()

    # Find device
    if args.device:
        address = args.device
        print(f"Connecting to {address}...")
    else:
        device = await find_device()
        if device is None:
            sys.exit(1)
        address = device.address

    async with BleakClient(address, timeout=30.0) as client:
        print(f"Connected to Visco Shear at {address}")

        # Read device info
        info = await client.read_gatt_char(CHAR_INFO)
        if info:
            version = info[:24].split(b'\x00')[0].decode('ascii', errors='replace')
            spindle = info[24] if len(info) > 24 else 0
            temp = struct.unpack_from('<f', info, 25)[0] if len(info) >= 29 else 0
            print(f"  Firmware: {version}")
            print(f"  Spindle: {['CC-13','CP-25','VN-16','TB-3'][spindle] if spindle < 4 else '?'}")
            print(f"  Temperature: {temp:.1f} °C")

        if args.two_point:
            await two_point_calibration(client)
        else:
            await single_point_calibration(client, args.reference, args.name)

        print("\nCalibration complete!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)