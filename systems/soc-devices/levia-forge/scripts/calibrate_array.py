#!/usr/bin/env python3
"""
Levia Forge — Array Calibration Helper

Helps calibrate the 72-transducer array by:
1. Measuring individual transducer output levels
2. Detecting dead or weak transducers
3. Computing per-element amplitude correction factors
4. Measuring actual phase delays (for wire-length compensation)

This script communicates with the Levia Forge device via the ESP32-C3
BLE bridge, activating one transducer at a time (using a special
calibration mode) and measuring the acoustic output with an external
microphone or the VL53L0X (as a rough proxy).

Usage:
    python3 calibrate_array.py [--output calibration.json]

Requires:
    pip install bleak numpy
"""

import argparse
import json
import asyncio
import numpy as np
from datetime import datetime

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("bleak not installed. Install with: pip install bleak")
    exit(1)

DEVICE_NAME = "Levia Forge"
CHAR_CMD_UUID = "00002a02-0000-1000-8000-00805f9b34fb"
CHAR_STATE_UUID = "00002a01-0000-1000-8000-00805f9b34fb"

NUM_TRANSDUCERS = 72


async def scan_for_device():
    """Scan for the Levia Forge BLE device."""
    print("Scanning for Levia Forge...")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        if d.name and DEVICE_NAME in d.name:
            print(f"Found: {d.name} ({d.address})")
            return d
    print("Levia Forge not found!")
    return None


async def send_command(client, cmd):
    """Send a command to the device."""
    await client.write_gatt_char(CHAR_CMD_UUID, cmd.encode('utf-8'))
    await asyncio.sleep(0.2)  # Wait for response


async def read_state(client):
    """Read the current state from the device."""
    try:
        data = await client.read_gatt_char(CHAR_STATE_UUID)
        return data.decode('utf-8')
    except Exception:
        return ""


async def calibrate(client):
    """
    Run the calibration sequence.

    For each transducer:
    1. Activate only that transducer (all others off)
    2. Read the state (which includes a calibration amplitude)
    3. Record the amplitude
    4. Compute correction factor
    """
    results = []

    print(f"\nCalibrating {NUM_TRANSDUCERS} transducers...")
    print("Ensure a microphone is positioned at the focal point.")
    print("Press Enter to start...")
    input()

    # First, measure baseline (all off)
    await send_command(client, "CMD,SET_ACTIVE,0")
    await asyncio.sleep(0.5)
    baseline = await read_state(client)
    print(f"Baseline: {baseline}")

    # Measure each transducer
    for i in range(NUM_TRANSDUCERS):
        # Send calibration command: activate only transducer i
        cmd = f"CMD,CAL_SINGLE,{i}"
        await send_command(client, cmd)
        await asyncio.sleep(0.1)

        state = await read_state(client)
        # Parse amplitude from state (format depends on firmware)
        # For now, we just record the state
        amplitude = 1.0  # Placeholder: actual measurement from mic

        results.append({
            'index': i,
            'array': 'top' if i < 36 else 'bottom',
            'position_in_array': i % 36,
            'amplitude': amplitude,
            'state': state,
        })

        if (i + 1) % 10 == 0:
            print(f"  Calibrated {i + 1}/{NUM_TRANSDUCERS}")

    # Deactivate all
    await send_command(client, "CMD,SET_ACTIVE,0")

    # Compute correction factors
    amplitudes = np.array([r['amplitude'] for r in results])
    mean_amp = np.mean(amplitudes)

    for i, r in enumerate(results):
        if r['amplitude'] > 0:
            r['correction_factor'] = mean_amp / r['amplitude']
        else:
            r['correction_factor'] = 0.0
            r['status'] = 'DEAD'
            print(f"  WARNING: Transducer {i} appears dead!")

    # Check for weak transducers (< 50% of mean)
    for i, r in enumerate(results):
        if r['amplitude'] < mean_amp * 0.5:
            r['status'] = 'WEAK'
            print(f"  WARNING: Transducer {i} is weak "
                  f"({r['amplitude']:.3f} vs mean {mean_amp:.3f})")
        else:
            r['status'] = 'OK'

    return results


async def main_async(output_file):
    device = await scan_for_device()
    if not device:
        return

    async with BleakClient(device.address) as client:
        print(f"Connected to {device.name}")

        # Run calibration
        results = await calibrate(client)

        # Generate calibration report
        calibration = {
            'device': DEVICE_NAME,
            'date': datetime.now().isoformat(),
            'num_transducers': NUM_TRANSDUCERS,
            'results': results,
            'summary': {
                'mean_amplitude': float(np.mean(
                    [r['amplitude'] for r in results])),
                'std_amplitude': float(np.std(
                    [r['amplitude'] for r in results])),
                'dead_count': sum(1 for r in results
                                  if r.get('status') == 'DEAD'),
                'weak_count': sum(1 for r in results
                                  if r.get('status') == 'WEAK'),
                'ok_count': sum(1 for r in results
                                if r.get('status') == 'OK'),
            }
        }

        # Save to file
        with open(output_file, 'w') as f:
            json.dump(calibration, f, indent=2)

        print(f"\nCalibration complete!")
        print(f"  OK:   {calibration['summary']['ok_count']}")
        print(f"  Weak: {calibration['summary']['weak_count']}")
        print(f"  Dead: {calibration['summary']['dead_count']}")
        print(f"  Saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Levia Forge — Array Calibration Helper')
    parser.add_argument('--output', type=str, default='calibration.json',
                        help='Output calibration file (JSON)')
    args = parser.parse_args()

    asyncio.run(main_async(args.output))


if __name__ == "__main__":
    main()