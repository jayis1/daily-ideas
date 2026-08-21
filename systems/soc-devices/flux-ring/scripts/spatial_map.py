#!/usr/bin/env python3
"""
Flux Ring — spatial_map.py
Generate 2D/3D magnetic field spatial maps from BLE streaming data.

As the user walks around wearing the Flux Ring, this script collects
the 3-axis magnetic field samples (with timestamps) and builds a
spatial map. Hand position is estimated using the ring's accelerometer
data (dead reckoning) or optionally from the phone's IMU.

Usage:
    python3 spatial_map.py --mac AA:BB:CC:DD:EE:FF
    python3 spatial_map.py --mac AA:BB:CC:DD:EE:FF --output field_map
    python3 spatial_map.py --input field_data.csv --output field_map
"""

import argparse
import asyncio
import struct
import sys
import time
from collections import deque

try:
    import numpy as np
    HAS_NP = True
except ImportError:
    HAS_NP = False

try:
    from bleak import BleakClient, BleakScanner
    HAS_BLEAK = True
except ImportError:
    HAS_BLEAK = False

try:
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.cm import ScalarMappable
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# GATT UUIDs
CHAR_FIELD_X = "0000FFB1-0000-1000-8000-00805F9B34FB"

# Map data: list of (estimated_x, estimated_y, field_x, field_y, field_z, magnitude)
map_points = []
# Simple position tracking: accumulate steps from accelerometer
pos_x = 0.0
pos_y = 0.0
prev_ax = 0.0
prev_ay = 0.0
prev_time = 0.0


def estimate_position(ax, ay, az, dt):
    """
    Simple dead-reckoning position estimate from accelerometer.
    This is very approximate — for real mapping, use the phone's
    IMU + AR framework for position tracking.
    """
    global pos_x, pos_y, prev_ax, prev_ay

    # High-pass filter: remove gravity component (assume az ≈ 1g when still)
    ax_motion = ax * 0.1  # Scale down to avoid drift
    ay_motion = ay * 0.1

    # Integrate acceleration to get velocity, then position
    # Very simplified: treat acceleration as velocity * scaling factor
    vx = ax_motion * dt
    vy = ay_motion * dt

    pos_x += vx
    pos_y += vy

    # Apply heavy damping to prevent drift
    pos_x *= 0.995
    pos_y *= 0.995

    return pos_x, pos_y


def generate_heatmap(points, output_file):
    """Generate a 2D heat map of field magnitude."""
    if not HAS_MPL or not HAS_NP:
        print("Need matplotlib and numpy for heat map generation")
        return

    if len(points) < 5:
        print("Not enough points for heat map (need at least 5)")
        return

    data = np.array(points)
    x = data[:, 0]
    y = data[:, 1]
    mag = data[:, 5]  # magnitude column

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    # Create scatter plot colored by magnitude
    scatter = ax.scatter(x, y, c=mag, cmap='jet', s=20, alpha=0.7,
                         edgecolors='none')

    plt.colorbar(scatter, label='Field Magnitude (Gauss)')
    ax.set_xlabel('X position (m)')
    ax.set_ylabel('Y position (m)')
    ax.set_title('Flux Ring — Spatial Magnetic Field Map')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{output_file}.png", dpi=150)
    print(f"Heat map saved to {output_file}.png")
    plt.close()


def generate_vector_field(points, output_file):
    """Generate a 2D vector field plot."""
    if not HAS_MPL or not HAS_NP:
        print("Need matplotlib and numpy for vector field")
        return

    if len(points) < 5:
        print("Not enough points for vector field")
        return

    data = np.array(points)
    x = data[:, 0]
    y = data[:, 1]
    fx = data[:, 2]
    fy = data[:, 3]
    mag = data[:, 5]

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    # Normalize vectors for display
    mag_h = np.sqrt(fx**2 + fy**2)
    mag_h[mag_h == 0] = 1  # Avoid division by zero
    fx_norm = fx / mag_h
    fy_norm = fy / mag_h

    # Quiver plot
    q = ax.quiver(x, y, fx_norm, fy_norm, mag, cmap='jet', alpha=0.8,
                  scale=30, width=0.003)

    plt.colorbar(q, label='Field Magnitude (Gauss)')
    ax.set_xlabel('X position (m)')
    ax.set_ylabel('Y position (m)')
    ax.set_title('Flux Ring — Magnetic Vector Field')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{output_file}_vectors.png", dpi=150)
    print(f"Vector field saved to {output_file}_vectors.png")
    plt.close()


def export_csv(points, output_file):
    """Export map points to CSV."""
    with open(f"{output_file}.csv", 'w') as f:
        f.write("pos_x,pos_y,field_x,field_y,field_z,magnitude\n")
        for p in points:
            f.write(f"{p[0]:.4f},{p[1]:.4f},{p[2]:.4f},"
                    f"{p[3]:.4f},{p[4]:.4f},{p[5]:.4f}\n")
    print(f"Point data saved to {output_file}.csv")


def export_vtk(points, output_file):
    """Export map points as VTK for ParaView/VisIt."""
    n = len(points)
    with open(f"{output_file}.vtk", 'w') as f:
        f.write("# vtk DataFile Version 3.0\n")
        f.write("Flux Ring Spatial Magnetic Field Map\n")
        f.write("ASCII\n")
        f.write("DATASET POLYDATA\n")
        f.write(f"POINTS {n} float\n")
        for p in points:
            f.write(f"{p[0]:.4f} {p[1]:.4f} 0.0\n")

        f.write(f"\nPOINT_DATA {n}\n")
        f.write("VECTORS MagneticField float\n")
        for p in points:
            f.write(f"{p[2]:.4f} {p[3]:.4f} {p[4]:.4f}\n")

        f.write("SCALARS Magnitude float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for p in points:
            f.write(f"{p[5]:.4f}\n")

    print(f"VTK file saved to {output_file}.vtk")


async def stream_and_map(mac, output_file='field_map', duration=60):
    """Connect to Flux Ring via BLE and build a spatial map in real-time."""
    global map_points

    sample_count = 0

    def notification_handler(characteristic, data):
        nonlocal sample_count
        if len(data) == 24:
            ts, fx, fy, fz = struct.unpack('<Ifff', data[0:16])
            ax, ay, az = struct.unpack('<hhh', data[16:22])

            ax_g = ax / 1000.0
            ay_g = ay / 1000.0

            # Estimate position
            dt = 0.01  # Assume 100Hz
            px, py = estimate_position(ax_g, ay_g, az / 1000.0, dt)

            magnitude = (fx**2 + fy**2 + fz**2) ** 0.5
            map_points.append((px, py, fx, fy, fz, magnitude))
            sample_count += 1

    print(f"Connecting to Flux Ring at {mac}...")
    async with BleakClient(mac) as client:
        print("Connected! Starting spatial mapping...")
        print(f"Walk around your space for {duration} seconds.")
        print("The app will track your position and build a field map.\n")

        await client.start_notify(CHAR_FIELD_X, notification_handler)

        for remaining in range(duration, 0, -1):
            print(f"\r  Mapping: {remaining}s remaining | "
                  f"{len(map_points)} points collected", end='', flush=True)
            await asyncio.sleep(1)

        await client.stop_notify(CHAR_FIELD_X)

    print(f"\n\nMapping complete — {len(map_points)} points collected")

    # Generate outputs
    if len(map_points) > 0:
        export_csv(map_points, output_file)
        export_vtk(map_points, output_file)
        if HAS_MPL:
            generate_heatmap(map_points, output_file)
            generate_vector_field(map_points, output_file)


def process_csv(input_file, output_file='field_map'):
    """Process a previously saved CSV file."""
    points = []
    with open(input_file, 'r') as f:
        header = f.readline()  # Skip header
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 6:
                try:
                    p = [float(x) for x in parts[:6]]
                    points.append(tuple(p))
                except ValueError:
                    continue

    print(f"Loaded {len(points)} points from {input_file}")

    if len(points) > 0:
        export_vtk(points, output_file)
        if HAS_MPL:
            generate_heatmap(points, output_file)
            generate_vector_field(points, output_file)


def main():
    parser = argparse.ArgumentParser(description='Flux Ring Spatial Mapper')
    parser.add_argument('--mac', help='Device MAC address for live mapping')
    parser.add_argument('--input', '-i', help='Input CSV file (pre-recorded)')
    parser.add_argument('--output', '-o', default='field_map',
                        help='Output base name (default: field_map)')
    parser.add_argument('--duration', type=int, default=60,
                        help='Mapping duration in seconds (default: 60)')
    args = parser.parse_args()

    if args.input:
        process_csv(args.input, args.output)
    elif args.mac:
        if not HAS_BLEAK:
            print("Install bleak: pip install bleak")
            return
        asyncio.run(stream_and_map(args.mac, args.output, args.duration))
    else:
        print("Provide --mac (live) or --input (CSV file). See --help.")


if __name__ == '__main__':
    main()