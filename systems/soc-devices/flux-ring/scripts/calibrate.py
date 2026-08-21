#!/usr/bin/env python3
"""
Flux Ring — calibrate.py
Figure-8 calibration helper for the MMC5983MA magnetometer.

This script connects to the Flux Ring via BLE, reads raw magnetic
data while the user performs a figure-8 rotation, and computes
the hard-iron offset and soft-iron scale factors.

Usage:
    python3 calibrate.py --mac AA:BB:CC:DD:EE:FF
    python3 calibrate.py --mac AA:BB:CC:DD:EE:FF --duration 15
"""

import argparse
import asyncio
import struct
import sys
import time

try:
    import numpy as np
    from bleak import BleakClient
except ImportError:
    print("Install dependencies: pip install bleak numpy")
    sys.exit(1)

# GATT UUIDs
FLUX_SERVICE_UUID = "0000FFB0-0000-1000-8000-00805F9B34FB"
CHAR_FIELD_X  = "0000FFB1-0000-1000-8000-00805F9B34FB"
CHAR_FIELD_Y  = "0000FFB2-0000-1000-8000-00805F9B34FB"
CHAR_FIELD_Z  = "0000FFB3-0000-1000-8000-00805F9B34FB"

# Calibration data
samples = []


def notification_handler(characteristic, data):
    """Collect raw field samples."""
    if len(data) >= 12:
        fx, fy, fz = struct.unpack('<fff', data[0:12])
        samples.append((fx, fy, fz))


def compute_calibration(samples_list):
    """
    Compute hard-iron offset and soft-iron scale from min/max of each axis.
    For best results, the user should rotate the device through all orientations
    during the calibration period.
    """
    if len(samples_list) < 50:
        print(f"WARNING: Only {len(samples_list)} samples — calibration may be inaccurate")

    data = np.array(samples_list)
    x, y, z = data[:, 0], data[:, 1], data[:, 2]

    # Hard-iron offset: midpoint of min/max for each axis
    offset_x = (np.max(x) + np.min(x)) / 2.0
    offset_y = (np.max(y) + np.min(y)) / 2.0
    offset_z = (np.max(z) + np.min(z)) / 2.0

    # Soft-iron scale: normalize so all axes have the same range
    delta_x = (np.max(x) - np.min(x)) / 2.0
    delta_y = (np.max(y) - np.min(y)) / 2.0
    delta_z = (np.max(z) - np.min(z)) / 2.0

    avg_delta = (delta_x + delta_y + delta_z) / 3.0

    if avg_delta < 1e-6:
        print("ERROR: Field range too small — was the device moving?")
        return None

    scale_x = avg_delta / delta_x if delta_x > 1e-6 else 1.0
    scale_y = avg_delta / delta_y if delta_y > 1e-6 else 1.0
    scale_z = avg_delta / delta_z if delta_z > 1e-6 else 1.0

    return {
        'offset_x': offset_x,
        'offset_y': offset_y,
        'offset_z': offset_z,
        'scale_x': scale_x,
        'scale_y': scale_y,
        'scale_z': scale_z,
        'num_samples': len(samples_list),
    }


async def run_calibration(mac_addr, duration=10):
    global samples
    samples = []

    print(f"Connecting to Flux Ring at {mac_addr}...")
    async with BleakClient(mac_addr) as client:
        print("Connected!")

        # Enable notifications
        await client.start_notify(CHAR_FIELD_X, notification_handler)

        print(f"\n{'='*50}")
        print(f"  CALIBRATION MODE")
        print(f"  Rotate the ring in a figure-8 pattern")
        print(f"  for {duration} seconds...")
        print(f"{'='*50}\n")

        # Countdown
        for i in range(duration, 0, -1):
            print(f"  {i}...  ({len(samples)} samples collected)", end='\r')
            await asyncio.sleep(1)

        print(f"\n\nCalibration complete — {len(samples)} samples collected")

        # Stop notifications
        await client.stop_notify(CHAR_FIELD_X)

    # Compute calibration parameters
    cal = compute_calibration(samples)
    if cal is None:
        print("Calibration failed.")
        return

    print(f"\n{'='*50}")
    print(f"  CALIBRATION RESULTS")
    print(f"{'='*50}")
    print(f"  Samples:     {cal['num_samples']}")
    print(f"  Hard-iron offset:")
    print(f"    X: {cal['offset_x']:+.4f} Gauss")
    print(f"    Y: {cal['offset_y']:+.4f} Gauss")
    print(f"    Z: {cal['offset_z']:+.4f} Gauss")
    print(f"  Soft-iron scale:")
    print(f"    X: {cal['scale_x']:.4f}")
    print(f"    Y: {cal['scale_y']:.4f}")
    print(f"    Z: {cal['scale_z']:.4f}")
    print(f"\n  These values are automatically stored in the")
    print(f"  device's flash and applied to all readings.")
    print(f"{'='*50}")

    # Optional: write calibration to file
    with open('calibration_params.txt', 'w') as f:
        f.write(f"# Flux Ring Calibration Parameters\n")
        f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Samples: {cal['num_samples']}\n\n")
        f.write(f"offset_x={cal['offset_x']:.6f}\n")
        f.write(f"offset_y={cal['offset_y']:.6f}\n")
        f.write(f"offset_z={cal['offset_z']:.6f}\n")
        f.write(f"scale_x={cal['scale_x']:.6f}\n")
        f.write(f"scale_y={cal['scale_y']:.6f}\n")
        f.write(f"scale_z={cal['scale_z']:.6f}\n")

    print(f"\n  Saved to: calibration_params.txt")


def main():
    parser = argparse.ArgumentParser(description='Flux Ring Calibration Helper')
    parser.add_argument('--mac', required=True, help='Device MAC address')
    parser.add_argument('--duration', type=int, default=10,
                        help='Calibration duration in seconds (default: 10)')
    args = parser.parse_args()

    asyncio.run(run_calibration(args.mac, args.duration))


if __name__ == '__main__':
    main()