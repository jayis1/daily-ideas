#!/usr/bin/env python3
"""
Opti Rot — BLE companion script
Pocket Digital Polarimeter — measurement, identification, library management, and Drude ORD plotting.

Usage:
  python3 opti_rot.py --ble --measure                    # single measurement (589nm)
  python3 opti_rot.py --ble --identify                    # 3-wavelength identification
  python3 opti_rot.py --ble --zero                        # auto-zero
  python3 opti_rot.py --ble --monitor --output log.csv   # continuous monitoring
  python3 opti_rot.py --ble --library                     # list compound library
  python3 opti_rot.py --ble --add "Fructose" -92.4 -0.02  # add custom compound
  python3 opti_rot.py --ble --drude                       # real-time Drude ORD plot
  python3 opti_rot.py --wifi --measure                    # via Wi-Fi instead of BLE

Requires: bleak (for BLE), requests (for Wi-Fi), matplotlib (for plots)
  pip install bleak requests matplotlib
"""

import argparse
import asyncio
import struct
import sys
import csv
import json
from datetime import datetime

# BLE UUIDs
OPTI_ROT_SERVICE_UUID = "0000ff30-0000-1000-8000-00805f9b34fb"
CMD_CHAR_UUID    = "0000ff31-0000-1000-8000-00805f9b34fb"
RESULT_CHAR_UUID = "0000ff32-0000-1000-8000-00805f9b34fb"
STATUS_CHAR_UUID = "0000ff33-0000-1000-8000-00805f9b34fb"
LIBRARY_CHAR_UUID = "0000ff34-0000-1000-8000-00805f9b34fb"
CONFIG_CHAR_UUID  = "0000ff35-0000-1000-8000-00805f9b34fb"

# Wi-Fi default
WIFI_IP = "192.168.4.1"


def parse_single_result(data: bytes) -> dict:
    """Parse a single-wavelength result (49 bytes: type + 48 payload)."""
    if len(data) < 49:
        return {"error": "short result"}
    result_type = data[0]
    angle, rotation, concentration, confidence, wavelength, temp = struct.unpack_from('<6f', data, 1)
    compound = data[25:49].split(b'\x00')[0].decode('ascii', errors='replace')
    return {
        "type": "single" if result_type == 1 else f"unknown({result_type})",
        "angle": angle,
        "rotation": rotation,
        "concentration": concentration,
        "confidence": confidence,
        "wavelength": wavelength,
        "temperature": temp,
        "compound": compound,
        "timestamp": datetime.now().isoformat()
    }


def parse_multi_result(data: bytes) -> dict:
    """Parse a 3-wavelength result (62 bytes: type + 61 payload)."""
    if len(data) < 62:
        return {"error": "short multi result"}
    result_type = data[0]
    rot405, rot520, rot589, K, lambda0, residual = struct.unpack_from('<6f', data, 1)
    match_index = data[25]
    match_conf, match_dist = struct.unpack_from('<2f', data, 26)
    match_name = data[33:57].split(b'\x00')[0].decode('ascii', errors='replace')
    return {
        "type": "multi" if result_type == 2 else f"unknown({result_type})",
        "rotations": {"405nm": rot405, "520nm": rot520, "589nm": rot589},
        "drude": {"K": K, "lambda0": lambda0, "residual": residual},
        "match": {"index": match_index, "name": match_name,
                  "confidence": match_conf, "distance": match_dist},
        "timestamp": datetime.now().isoformat()
    }


def parse_library_entry(data: bytes) -> dict:
    """Parse a library entry (41 bytes)."""
    if len(data) < 41:
        return {"error": "short entry"}
    name = data[0:24].split(b'\x00')[0].decode('ascii', errors='replace')
    alpha, temp_coeff, K, lambda0 = struct.unpack_from('<4f', data, 24)
    is_custom = data[40]
    return {
        "name": name,
        "specific_rotation": alpha,
        "temp_coefficient": temp_coeff,
        "drude_K": K,
        "drude_lambda0": lambda0,
        "is_custom": bool(is_custom)
    }


# =================== BLE Backend ===================

async def ble_scan():
    try:
        from bleak import BleakScanner
    except ImportError:
        print("Error: bleak not installed. Run: pip install bleak")
        return None
    print("Scanning for Opti Rot devices...")
    devices = await BleakScanner.discover(timeout=5.0)
    opti_devices = [d for d in devices if "OptiRot" in (d.name or "")]
    if not opti_devices:
        print("No Opti Rot devices found. Make sure the device is powered on.")
        return None
    if len(opti_devices) == 1:
        print(f"Found: {opti_devices[0].name} [{opti_devices[0].address}]")
        return opti_devices[0].address
    print("Multiple devices found:")
    for i, d in enumerate(opti_devices):
        print(f"  {i}: {d.name} [{d.address}]")
    choice = input("Select device (0): ").strip() or "0"
    return opti_devices[int(choice)].address


async def ble_connect_and_send(addr, cmd_byte, payload=b''):
    try:
        from bleak import BleakClient
    except ImportError:
        print("Error: bleak not installed.")
        return None
    async with BleakClient(addr, timeout=10.0) as client:
        result_data = []

        def notification_handler(sender, data):
            result_data.append(data)

        await client.start_notify(RESULT_CHAR_UUID, notification_handler)
        await client.start_notify(STATUS_CHAR_UUID, notification_handler)

        # Send command
        frame = bytes([cmd_byte, len(payload)]) + payload
        await client.write_gatt_char(CMD_CHAR_UUID, frame)

        # Wait for result
        await asyncio.sleep(20)  # max wait for 3-wavelength measurement

        await client.stop_notify(RESULT_CHAR_UUID)
        await client.stop_notify(STATUS_CHAR_UUID)

        return result_data


async def ble_measure():
    addr = await ble_scan()
    if not addr:
        return
    print("Triggering measurement (589nm)...")
    results = await ble_connect_and_send(addr, 0x01)
    if results:
        for r in results:
            result = parse_single_result(r)
            print(f"\n=== Measurement Result ===")
            print(f"Rotation:       {result.get('rotation', 0):+.4f}°")
            print(f"Concentration:  {result.get('concentration', 0):.3f} g/100mL")
            if result.get('compound'):
                print(f"Compound:       {result['compound']}")
                print(f"Confidence:     {result.get('confidence', 0):.1f}%")
            print(f"Wavelength:     {result.get('wavelength', 0):.0f} nm")
            print(f"Temperature:    {result.get('temperature', 0):.1f}°C")
            print(f"Timestamp:      {result.get('timestamp', '')}")


async def ble_identify():
    addr = await ble_scan()
    if not addr:
        return
    print("Triggering 3-wavelength identification...")
    results = await ble_connect_and_send(addr, 0x02, timeout=50)
    if results:
        for r in results:
            if r[0] == 2:
                result = parse_multi_result(r)
                print(f"\n=== Multi-Wavelength Identification ===")
                print(f"Rotation @ 405nm: {result['rotations']['405nm']:+.4f}°")
                print(f"Rotation @ 520nm: {result['rotations']['520nm']:+.4f}°")
                print(f"Rotation @ 589nm: {result['rotations']['589nm']:+.4f}°")
                print(f"\nDrude ORD Fit:")
                print(f"  K = {result['drude']['K']:.4e}")
                print(f"  λ₀ = {result['drude']['lambda0']:.1f} nm")
                print(f"  Residual = {result['drude']['residual']:.6f}")
                print(f"\nBest Match: {result['match']['name']}")
                print(f"  Confidence: {result['match']['confidence']:.1f}%")
                print(f"  Distance:  {result['match']['distance']:.4f}")

                # Try to plot
                try:
                    import matplotlib.pyplot as plt
                    import numpy as np
                    wavelengths = np.array([405, 520, 589])
                    rotations = np.array([result['rotations']['405nm'],
                                         result['rotations']['520nm'],
                                         result['rotations']['589nm']])
                    K = result['drude']['K']
                    l0 = result['drude']['lambda0']
                    lam_fine = np.linspace(380, 700, 300)
                    if K != 0 and l0 > 0:
                        pred = K / (lam_fine**2 - l0**2)
                        plt.figure(figsize=(8, 5))
                        plt.plot(lam_fine, pred, 'b-', label=f'Drude fit (K={K:.2e}, λ₀={l0:.0f}nm)')
                        plt.plot(wavelengths, rotations, 'ro', markersize=8, label='Measured')
                        plt.xlabel('Wavelength (nm)')
                        plt.ylabel('Optical Rotation (°)')
                        plt.title(f'Drude ORD — {result["match"]["name"]} ({result["match"]["confidence"]:.0f}%)')
                        plt.legend()
                        plt.grid(True, alpha=0.3)
                        plt.tight_layout()
                        plt.savefig('opti_rot_drude.png', dpi=150)
                        print(f"\nDrude plot saved: opti_rot_drude.png")
                except ImportError:
                    pass


async def ble_zero():
    addr = await ble_scan()
    if not addr:
        return
    print("Auto-zeroing (empty tube required)...")
    await ble_connect_and_send(addr, 0x03)
    print("Auto-zero complete.")


async def ble_monitor(output_file):
    addr = await ble_scan()
    if not addr:
        return
    print(f"Starting monitor mode (logging to {output_file})...")
    try:
        from bleak import BleakClient
    except ImportError:
        return

    f = open(output_file, 'w', newline='')
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'rotation', 'concentration', 'compound',
                      'confidence', 'temperature', 'wavelength'])

    async with BleakClient(addr, timeout=10.0) as client:
        def notification_handler(sender, data):
            result = parse_single_result(data)
            writer.writerow([
                result.get('timestamp', ''),
                result.get('rotation', 0),
                result.get('concentration', 0),
                result.get('compound', ''),
                result.get('confidence', 0),
                result.get('temperature', 0),
                result.get('wavelength', 0)
            ])
            f.flush()
            print(f"{result.get('timestamp','')}: rot={result.get('rotation',0):+.4f}° "
                  f"conc={result.get('concentration',0):.3f} "
                  f"compound={result.get('compound','')}")

        await client.start_notify(RESULT_CHAR_UUID, notification_handler)
        payload = struct.pack('<H', 10000)  # 10 second interval
        await client.write_gatt_char(CMD_CHAR_UUID, bytes([0x04, 2]) + payload)

        print("Monitoring... Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping monitor...")
            await client.write_gatt_char(CMD_CHAR_UUID, bytes([0x05, 0]))

    f.close()
    print(f"Data saved to {output_file}")


async def ble_library():
    addr = await ble_scan()
    if not addr:
        return
    print("Requesting library...")
    try:
        from bleak import BleakClient
    except ImportError:
        return

    async with BleakClient(addr, timeout=10.0) as client:
        entries = []

        def notification_handler(sender, data):
            entry = parse_library_entry(data)
            entries.append(entry)
            print(f"  {len(entries):3d}. {entry['name']:24s} [α]D={entry['specific_rotation']:+.1f} "
                  f"K={entry['drude_K']:.1e} λ₀={entry['drude_lambda0']:.0f}"
                  f" {'*' if entry['is_custom'] else ''}")

        await client.start_notify(LIBRARY_CHAR_UUID, notification_handler)
        await client.write_gatt_char(CMD_CHAR_UUID, bytes([0x07, 0]))
        await asyncio.sleep(5)
        await client.stop_notify(LIBRARY_CHAR_UUID)

    print(f"\n{len(entries)} compounds in library (* = custom)")


async def ble_add(name, alpha, temp_coeff):
    addr = await ble_scan()
    if not addr:
        return
    try:
        from bleak import BleakClient
    except ImportError:
        return

    payload = name.encode('ascii')[:24].ljust(24, b'\x00')
    payload += struct.pack('<4f', alpha, temp_coeff, 0.0, 200.0)  # K=0, λ₀=200 as defaults

    async with BleakClient(addr, timeout=10.0) as client:
        await client.write_gatt_char(CMD_CHAR_UUID, bytes([0x08, len(payload)]) + payload)
        print(f"Added compound: {name} [α]D={alpha} temp_coeff={temp_coeff}")
        await asyncio.sleep(2)


# =================== Wi-Fi Backend ===================

def wifi_measure():
    import requests
    print("Triggering measurement via Wi-Fi...")
    r = requests.post(f"http://{WIFI_IP}/api/measure", timeout=30)
    result = r.json()
    print(f"\n=== Measurement Result ===")
    print(f"Rotation:       {result.get('rotation', 0):+.4f}°")
    print(f"Concentration:  {result.get('concentration', 0):.3f} g/100mL")
    if result.get('compound'):
        print(f"Compound:       {result['compound']}")
        print(f"Confidence:     {result.get('confidence', 0):.1f}%")
    print(f"Temperature:    {result.get('temperature', 0):.1f}°C")


def wifi_identify():
    import requests
    print("Triggering 3-wavelength identification via Wi-Fi...")
    r = requests.post(f"http://{WIFI_IP}/api/identify", timeout=60)
    result = r.json()
    print(f"\n=== Multi-Wavelength Identification ===")
    for wl in ['405', '520', '589']:
        print(f"Rotation @ {wl}nm: {result['rotations'][wl]:+.4f}°")
    print(f"\nDrude: K={result['drude']['K']:.4e}, λ₀={result['drude']['lambda0']:.1f}nm")
    print(f"Match: {result['match']['name']} ({result['match']['confidence']:.1f}%)")


def wifi_library():
    import requests
    r = requests.get(f"http://{WIFI_IP}/api/library", timeout=10)
    entries = r.json()
    for i, e in enumerate(entries):
        print(f"  {i+1:3d}. {e['name']:24s} [α]D={e['specific_rotation']:+.1f}")


def wifi_add(name, alpha, temp_coeff):
    import requests
    r = requests.post(f"http://{WIFI_IP}/api/library/add", json={
        'name': name, 'alpha': alpha, 'tc': temp_coeff
    }, timeout=10)
    print(f"Added: {r.json()}")


def wifi_zero():
    import requests
    r = requests.post(f"http://{WIFI_IP}/api/zero", timeout=15)
    print("Auto-zero complete.")


# =================== Main ===================

def main():
    parser = argparse.ArgumentParser(
        description="Opti Rot — Pocket Digital Polarimeter companion script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--ble', action='store_true', help="Use BLE connection")
    group.add_argument('--wifi', action='store_true', help="Use Wi-Fi connection")

    parser.add_argument('--measure', action='store_true', help="Single measurement (589nm)")
    parser.add_argument('--identify', action='store_true', help="3-wavelength identification")
    parser.add_argument('--zero', action='store_true', help="Auto-zero (empty tube)")
    parser.add_argument('--monitor', action='store_true', help="Continuous monitoring")
    parser.add_argument('--library', action='store_true', help="List compound library")
    parser.add_argument('--add', nargs=3, metavar=('NAME', 'ALPHA', 'TEMP_COEFF'),
                        help="Add custom compound")
    parser.add_argument('--output', default='opti_rot_log.csv', help="Output file for monitor")
    parser.add_argument('--drude', action='store_true', help="Real-time Drude ORD plot")
    parser.add_argument('--ip', default=WIFI_IP, help="Wi-Fi IP (default 192.168.4.1)")

    args = parser.parse_args()

    global WIFI_IP
    WIFI_IP = args.ip

    if args.wifi:
        if args.measure:
            wifi_measure()
        elif args.identify:
            wifi_identify()
        elif args.zero:
            wifi_zero()
        elif args.library:
            wifi_library()
        elif args.add:
            wifi_add(args.add[0], float(args.add[1]), float(args.add[2]))
        else:
            print("Specify an action: --measure, --identify, --zero, --library, --add")
    elif args.ble:
        if args.measure:
            asyncio.run(ble_measure())
        elif args.identify:
            asyncio.run(ble_identify())
        elif args.zero:
            asyncio.run(ble_zero())
        elif args.monitor:
            asyncio.run(ble_monitor(args.output))
        elif args.library:
            asyncio.run(ble_library())
        elif args.add:
            asyncio.run(ble_add(args.add[0], float(args.add[1]), float(args.add[2])))
        else:
            print("Specify an action: --measure, --identify, --zero, --monitor, --library, --add")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()