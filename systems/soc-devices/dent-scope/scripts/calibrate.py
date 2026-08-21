#!/usr/bin/env python3
"""
Dent Scope — Calibration helper script

Connects to Dent Scope via USB serial (STM32 debug port) or BLE to
perform force and depth calibration.

Usage:
  python3 calibrate.py --port /dev/ttyUSB0 --force-zero
  python3 calibrate.py --port /dev/ttyUSB0 --force-scale 49.1
  python3 calibrate.py --port /dev/ttyUSB0 --depth-point 0
  python3 calibrate.py --port /dev/ttyUSB0 --depth-point 50
  python3 calibrate.py --port /dev/ttyUSB0 --depth-point 100
  python3 calibrate.py --port /dev/ttyUSB0 --depth-commit

MIT License
"""
import argparse
import serial
import struct
import time
import json
import numpy as np

def send_cmd(ser, cmd_type, payload=b''):
    """Send a frame: AA 55 type len_lo len_hi payload crc16"""
    frame = bytes([0xAA, 0x55, cmd_type, len(payload) & 0xFF, (len(payload) >> 8) & 0xFF]) + payload
    crc = crc16(frame)
    frame += struct.pack('<H', crc)
    ser.write(frame)
    time.sleep(0.1)
    resp = ser.read(256)
    return resp

def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def read_raw_force(ser, n=32):
    """Read n HX711 raw values from device and return average"""
    resp = send_cmd(ser, 0x20, struct.pack('<H', n))  # cmd 0x20: read raw
    if len(resp) >= 6:
        plen = resp[3] | (resp[4] << 8)
        if plen >= 4:
            val = struct.unpack('<i', resp[5:9])[0]
            return val
    return 0

def read_raw_cap(ser, n=32):
    """Read n AD7746 raw capacitance values"""
    resp = send_cmd(ser, 0x21, struct.pack('<H', n))
    if len(resp) >= 6:
        plen = resp[3] | (resp[4] << 8)
        if plen >= 4:
            val = struct.unpack('<f', resp[5:9])[0]
            return val
    return 0.0

def main():
    parser = argparse.ArgumentParser(description='Dent Scope calibration')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--force-zero', action='store_true', help='Tare force (set HX711 offset)')
    parser.add_argument('--force-scale', type=float, help='Set HX711 scale with known weight (mN)')
    parser.add_argument('--depth-point', type=float, help='Collect depth calibration point (µm)')
    parser.add_argument('--depth-commit', action='store_true', help='Commit depth calibration to flash')
    parser.add_argument('--depth-show', action='store_true', help='Show collected depth points')
    args = parser.parse_args()

    ser = serial.Serial(args.port, args.baud, timeout=1.0)
    time.sleep(0.5)

    depth_points_file = '/tmp/dent_scope_depth_cal.json'

    if args.force_zero:
        raw = read_raw_force(ser, 32)
        print(f"Force zero: raw offset = {raw}")
        send_cmd(ser, 0x22, struct.pack('<i', raw))  # cmd 0x22: set offset
        print("Force offset saved.")

    elif args.force_scale:
        # Read raw at zero, then with weight
        raw_zero = read_raw_force(ser, 16)
        print(f"Raw at zero: {raw_zero}")
        input(f"Apply {args.force_scale} mN load, then press Enter...")
        raw_loaded = read_raw_force(ser, 16)
        print(f"Raw with load: {raw_loaded}")
        delta = raw_loaded - raw_zero
        if delta != 0:
            scale = args.force_scale / delta
            print(f"Scale: {scale:.8f} mN/count")
            send_cmd(ser, 0x23, struct.pack('<f', scale))  # cmd 0x23: set scale
            print("Force scale saved.")
        else:
            print("ERROR: no change in raw value")

    elif args.depth_point is not None:
        pf = read_raw_cap(ser, 32)
        print(f"AD7746 capacitance: {pf:.6f} pF at depth {args.depth_point} µm")
        # load existing points
        try:
            with open(depth_points_file) as f:
                points = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            points = []
        points.append({'depth_um': args.depth_point, 'cap_pf': pf})
        with open(depth_points_file, 'w') as f:
            json.dump(points, f, indent=2)
        print(f"Point saved ({len(points)} total)")

    elif args.depth_show:
        try:
            with open(depth_points_file) as f:
                points = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            points = []
        print(f"Collected {len(points)} depth calibration points:")
        for p in points:
            print(f"  depth={p['depth_um']:.1f} µm  cap={p['cap_pf']:.6f} pF")
        if len(points) >= 3:
            depths = np.array([p['depth_um'] for p in points])
            caps = np.array([p['cap_pf'] for p in points])
            # quadratic fit: depth = offset + scale*cap + quad*cap²
            coeffs = np.polyfit(caps, depths, 2)
            quad, scale, offset = coeffs
            print(f"\nQuadratic fit: depth = {offset:.4f} + {scale:.4f}×cap + {quad:.6f}×cap²")
            print(f"  offset = {offset:.6f}")
            print(f"  scale  = {scale:.6f}")
            print(f"  quad   = {quad:.8f}")

    elif args.depth_commit:
        try:
            with open(depth_points_file) as f:
                points = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            points = []
        if len(points) < 3:
            print("ERROR: need at least 3 calibration points")
            return
        depths = np.array([p['depth_um'] for p in points])
        caps = np.array([p['cap_pf'] for p in points])
        coeffs = np.polyfit(caps, depths, 2)
        quad, scale, offset = coeffs
        print(f"Committing: offset={offset:.6f} scale={scale:.6f} quad={quad:.8f}")
        payload = struct.pack('<fff', offset, scale, quad)
        send_cmd(ser, 0x24, payload)  # cmd 0x24: set depth cal
        print("Depth calibration committed to flash.")

    else:
        # Live monitor mode
        print("Live monitor (Ctrl+C to stop):")
        try:
            while True:
                raw_f = read_raw_force(ser, 1)
                raw_c = read_raw_cap(ser, 1)
                print(f"Force raw: {raw_f:8d}  Cap: {raw_c:.6f} pF")
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nDone.")

    ser.close()

if __name__ == '__main__':
    main()