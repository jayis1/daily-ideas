#!/usr/bin/env python3
"""
Flux Ring — export_log.py
Export data from the Flux Ring's SPI flash log to CSV or VTK format.

Data can be retrieved via:
1. BLE (download log entries)
2. USB-C serial (UART console command)
3. Direct flash read (if connected via SWD)

Usage:
    python3 export_log.py --input log_data.bin --output field_data.csv
    python3 export_log.py --input log_data.bin --output field_map.vtk --format vtk
    python3 export_log.py --mac AA:BB:CC:DD:EE:FF --output field_data.csv
"""

import argparse
import struct
import sys

# Log format constants (must match firmware)
LOG_MAGIC = 0x46504C58  # "FLUX"
LOG_VERSION = 0x01
LOG_HEADER_SIZE = 32
LOG_SAMPLE_SIZE = 22


def parse_header(data):
    """Parse the 32-byte log header."""
    if len(data) < LOG_HEADER_SIZE:
        raise ValueError("Header too short")

    magic, version = struct.unpack('<IB', data[0:5])
    if magic != LOG_MAGIC:
        raise ValueError(f"Invalid magic: 0x{magic:08X} (expected 0x{LOG_MAGIC:08X})")
    if version != LOG_VERSION:
        raise ValueError(f"Unsupported version: {version}")

    sample_rate = struct.unpack('<B', data[5:6])[0]
    start_time = struct.unpack('<I', data[6:10])[0]

    # Calibration params (6 floats = 24 bytes at offset 8)
    cal = struct.unpack('<ffffff', data[8:32])

    return {
        'magic': magic,
        'version': version,
        'sample_rate': sample_rate,
        'start_time': start_time,
        'cal_offset_x': cal[0],
        'cal_offset_y': cal[1],
        'cal_offset_z': cal[2],
        'cal_scale_x': cal[3],
        'cal_scale_y': cal[4],
        'cal_scale_z': cal[5],
    }


def parse_samples(data, num_samples):
    """Parse sample records from binary data."""
    samples = []
    offset = LOG_HEADER_SIZE

    for i in range(num_samples):
        if offset + LOG_SAMPLE_SIZE > len(data):
            break

        ts, fx, fy, fz = struct.unpack('<Ifff', data[offset:offset + 16])
        ax, ay, az = struct.unpack('<hhh', data[offset + 16:offset + 22])

        # Convert accel from 0.001g units to g
        ax_g = ax / 1000.0
        ay_g = ay / 1000.0
        az_g = az / 1000.0

        # Compute magnitude
        magnitude = (fx**2 + fy**2 + fz**2) ** 0.5

        # Simple compass heading from horizontal components
        import math
        heading = math.degrees(math.atan2(fy, fx)) % 360

        samples.append({
            'timestamp_ms': ts,
            'field_x': fx,
            'field_y': fy,
            'field_z': fz,
            'magnitude': magnitude,
            'accel_x': ax_g,
            'accel_y': ay_g,
            'accel_z': az_g,
            'heading': heading,
        })

        offset += LOG_SAMPLE_SIZE

    return samples


def export_csv(samples, filename):
    """Export samples to CSV."""
    with open(filename, 'w') as f:
        f.write("timestamp_ms,field_x,field_y,field_z,magnitude,"
                "accel_x,accel_y,accel_z,heading\n")
        for s in samples:
            f.write(f"{s['timestamp_ms']},{s['field_x']:.4f},"
                    f"{s['field_y']:.4f},{s['field_z']:.4f},"
                    f"{s['magnitude']:.4f},{s['accel_x']:.4f},"
                    f"{s['accel_y']:.4f},{s['accel_z']:.4f},"
                    f"{s['heading']:.1f}\n")
    print(f"Exported {len(samples)} samples to {filename}")


def export_vtk(samples, filename):
    """Export samples as VTK legacy format for 3D visualization."""
    n = len(samples)
    with open(filename, 'w') as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("Flux Ring Magnetic Field Data\n")
        f.write("ASCII\n")
        f.write("DATASET POLYDATA\n")
        f.write(f"POINTS {n} float\n")

        # Points: use timestamp as X, magnitude as Z, evenly spaced Y
        for i, s in enumerate(samples):
            x = s['timestamp_ms'] / 1000.0  # Time as X
            y = 0.0
            z = s['magnitude']
            f.write(f"{x:.3f} {y:.3f} {z:.3f}\n")

        # Field vectors as point data
        f.write(f"\nPOINT_DATA {n}\n")
        f.write("VECTORS MagneticField float\n")
        for s in samples:
            f.write(f"{s['field_x']:.4f} {s['field_y']:.4f} {s['field_z']:.4f}\n")

        f.write("SCALARS Magnitude float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for s in samples:
            f.write(f"{s['magnitude']:.4f}\n")

    print(f"Exported {n} points to VTK: {filename}")


async def download_via_ble(mac, output_file, fmt='csv'):
    """Download log data from the device via BLE."""
    try:
        from bleak import BleakClient
    except ImportError:
        print("Install bleak: pip install bleak")
        return

    # This is a placeholder — actual implementation would use a
    # custom BLE characteristic for log download
    print(f"Connecting to {mac}...")
    async with BleakClient(mac) as client:
        print("Connected. Requesting log dump...")
        # In practice, the firmware would send log data over a
        # dedicated BLE characteristic or via USB-C CDC
        print("Log download via BLE not yet implemented in firmware.")
        print("Use USB-C serial console: 'log dump' command")


def main():
    parser = argparse.ArgumentParser(description='Flux Ring Log Exporter')
    parser.add_argument('--input', '-i', help='Binary log file to parse')
    parser.add_argument('--output', '-o', required=True, help='Output filename')
    parser.add_argument('--format', '-f', choices=['csv', 'vtk'], default='csv',
                        help='Output format (default: csv)')
    parser.add_argument('--mac', help='Download via BLE from device MAC')
    args = parser.parse_args()

    if args.mac:
        asyncio.run(download_via_ble(args.mac, args.output, args.format))
        return

    if not args.input:
        print("Provide --input (binary file) or --mac (BLE download)")
        return

    # Read binary file
    with open(args.input, 'rb') as f:
        data = f.read()

    # Parse header
    try:
        header = parse_header(data)
        print(f"Log header: version={header['version']}, "
              f"sample_rate={header['sample_rate']}, "
              f"start_time={header['start_time']}")
    except ValueError as e:
        print(f"Header parse error: {e}")
        print("Attempting raw sample parse...")

    # Calculate number of samples
    data_size = len(data) - LOG_HEADER_SIZE
    num_samples = data_size // LOG_SAMPLE_SIZE
    print(f"Data size: {data_size} bytes, {num_samples} samples")

    # Parse samples
    samples = parse_samples(data, num_samples)
    print(f"Parsed {len(samples)} samples")

    if len(samples) == 0:
        print("No samples to export.")
        return

    # Export
    if args.format == 'csv':
        export_csv(samples, args.output)
    elif args.format == 'vtk':
        export_vtk(samples, args.output)


if __name__ == '__main__':
    import asyncio
    main()