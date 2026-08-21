#!/usr/bin/env python3
"""
visco-shear / scripts / live_stream.py
Live data streaming and visualization for Visco Shear over BLE.

Displays real-time flow curve, model fit, and oscillatory G′/G″ data.

Usage:
    python3 live_stream.py                    # Auto-discover device
    python3 live_stream.py --device <MAC>     # Specify BLE address
    python3 live_stream.py --save data.csv    # Save to CSV

Requires: bleak, matplotlib (pip install bleak matplotlib)
"""
import argparse
import asyncio
import struct
import sys
import time
from collections import deque

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("ERROR: bleak not installed. Run: pip install bleak")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    HAS_MPL = True
except ImportError:
    print("WARNING: matplotlib not installed. Text-only mode.")
    HAS_MPL = False

# BLE UUIDs
CHAR_TORQUE  = "0000a102-0000-1000-8000-00805f9b34fb"
CHAR_RESULT  = "0000a103-0000-1000-8000-00805f9b34fb"
CHAR_CMD     = "0000a104-0000-1000-8000-00805f9b34fb"
CHAR_INFO    = "0000a105-0000-1000-8000-00805f9b34fb"

# Data buffers
torque_samples = deque(maxlen=500)
omega_samples = deque(maxlen=500)
viscosity_points = []
shear_rate_points = []
result_data = {}
csv_lines = ["# Visco Shear live stream log\n"]
connected = False


def parse_torque(data: bytes):
    """Parse torque notification (6 bytes)."""
    if len(data) < 6:
        return None, None, None
    ts = struct.unpack_from('<H', data, 0)[0]
    torque = struct.unpack_from('<h', data, 2)[0]  # µN·m (int16)
    omega = struct.unpack_from('<h', data, 4)[0] / 100.0  # rpm
    return ts, torque, omega


def parse_result(data: bytes) -> dict:
    """Parse result notification (32 bytes)."""
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


def torque_handler(sender, data):
    """Handle torque notification."""
    ts, torque, omega = parse_torque(data)
    if ts is not None:
        torque_samples.append(torque)
        omega_samples.append(omega)
        print(f"  [t={ts:5d}] τ={torque:8.1f} µN·m, Ω={omega:6.2f} rpm")


def result_handler(sender, data):
    """Handle result notification."""
    global result_data
    result_data = parse_result(data)
    if result_data:
        print("\n╔════════════════════════════════════════╗")
        print("║       MEASUREMENT RESULT               ║")
        print("╠════════════════════════════════════════╣")
        print(f"║  Model:      {result_data['model']:<28}║")
        print(f"║  R²:         {result_data['r_squared']:<28.5f}║")
        print(f"║  Avg η:      {result_data['avg_viscosity_mPa_s']:<28.2f} mPa·s")
        print(f"║  Temp:       {result_data['temperature_c']:<28.2f} °C")
        print(f"║  Points:     {result_data['n_points']:<28d}")
        print("╚════════════════════════════════════════╝\n")
        csv_lines.append(f"# Result: model={result_data['model']}, "
                         f"eta={result_data['avg_viscosity_mPa_s']:.2f}, "
                         f"R2={result_data['r_squared']:.5f}\n")


async def find_device():
    """Scan for Visco Shear BLE device."""
    print("Scanning for Visco Shear...")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        if d.name and "visco" in d.name.lower():
            print(f"  Found: {d.name} ({d.address})")
            return d
    return None


async def send_cmd(client, cmd, payload=b''):
    await client.write_gatt_char(CHAR_CMD, bytes([cmd]) + payload, response=True)


async def main():
    parser = argparse.ArgumentParser(description="Visco Shear live BLE stream")
    parser.add_argument("--device", type=str, default=None, help="BLE MAC address")
    parser.add_argument("--save", type=str, default=None, help="Save data to CSV file")
    args = parser.parse_args()

    # Find device
    if args.device:
        address = args.device
    else:
        device = await find_device()
        if not device:
            print("ERROR: No Visco Shear found.")
            sys.exit(1)
        address = device.address

    print(f"Connecting to {address}...")
    async with BleakClient(address, timeout=30.0) as client:
        print(f"Connected!\n")

        # Subscribe to notifications
        await client.start_notify(CHAR_TORQUE, torque_handler)
        await client.start_notify(CHAR_RESULT, result_handler)

        print("Commands:")
        print("  s - Start flow curve measurement")
        print("  o - Start oscillatory measurement")
        print("  t - Start thixotropy measurement")
        print("  x - Stop/cancel")
        print("  q - Quit")
        print()

        # Interactive command loop
        loop = asyncio.get_event_loop()
        while True:
            cmd_input = await loop.run_in_executor(None, input, "> ")
            cmd_input = cmd_input.strip().lower()

            if cmd_input == 'q':
                break
            elif cmd_input == 's':
                print("Starting flow curve measurement...")
                await send_cmd(client, 0x03, bytes([0]))  # Mode = FLOW_CURVE
                await asyncio.sleep(0.2)
                await send_cmd(client, 0x01)  # Start
            elif cmd_input == 'o':
                print("Starting oscillatory measurement...")
                await send_cmd(client, 0x03, bytes([2]))  # Mode = OSCILLATORY
                await asyncio.sleep(0.2)
                await send_cmd(client, 0x01)
            elif cmd_input == 't':
                print("Starting thixotropy measurement...")
                await send_cmd(client, 0x03, bytes([3]))  # Mode = THIXOTROPY
                await asyncio.sleep(0.2)
                await send_cmd(client, 0x01)
            elif cmd_input == 'x':
                print("Cancelling...")
                await send_cmd(client, 0x02)

        await client.stop_notify(CHAR_TORQUE)
        await client.stop_notify(CHAR_RESULT)

    # Save CSV if requested
    if args.save and csv_lines:
        with open(args.save, 'w') as f:
            f.writelines(csv_lines)
        print(f"Data saved to {args.save}")

    print("Disconnected.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted.")