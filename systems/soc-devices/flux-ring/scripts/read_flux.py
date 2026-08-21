#!/usr/bin/env python3
"""
Flux Ring — read_flux.py
BLE reader for Flux Ring magnetic field data.
Live-plots 3-axis field + magnitude using matplotlib.

Usage:
    python3 read_flux.py --mac AA:BB:CC:DD:EE:FF
    python3 read_flux.py --mac AA:BB:CC:DD:EE:FF --stream  # mapping mode
"""

import argparse
import asyncio
import struct
import sys
import time
from collections import deque

try:
    import bleak
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install bleak: pip install bleak")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("Install matplotlib for live plot: pip install matplotlib")

# GATT UUIDs
FLUX_SERVICE_UUID = "0000FFB0-0000-1000-8000-00805F9B34FB"
CHAR_FIELD_X  = "0000FFB1-0000-1000-8000-00805F9B34FB"
CHAR_FIELD_Y  = "0000FFB2-0000-1000-8000-00805F9B34FB"
CHAR_FIELD_Z  = "0000FFB3-0000-1000-8000-00805F9B34FB"
CHAR_MAGNITUDE = "0000FFB4-0000-1000-8000-00805F9B34FB"
CHAR_HEADING   = "0000FFB5-0000-1000-8000-00805F9B34FB"
CHAR_POLE      = "0000FFB6-0000-1000-8000-00805F9B34FB"
CHAR_SAMPLE_RATE = "0000FFB7-0000-1000-8000-00805F9B34FB"
CHAR_MODE      = "0000FFB8-0000-1000-8000-00805F9B34FB"
CHAR_BATTERY   = "0000FFB9-0000-1000-8000-00805F9B34FB"
CHAR_DEVICE_INFO = "0000FFBA-0000-1000-8000-00805F9B34FB"

# Data buffers for plotting
HISTORY_LEN = 500
timestamps = deque(maxlen=HISTORY_LEN)
field_x_data = deque(maxlen=HISTORY_LEN)
field_y_data = deque(maxlen=HISTORY_LEN)
field_z_data = deque(maxlen=HISTORY_LEN)
magnitude_data = deque(maxlen=HISTORY_LEN)

# Stream state
stream_mode = False
stream_file = None


def field_to_color(magnitude):
    """Map field magnitude to RGB color matching the LED."""
    if magnitude < 0.5:
        return '#001EFF'   # Soft blue
    elif magnitude < 1.0:
        return '#00C8FF'   # Cyan
    elif magnitude < 3.0:
        return '#00FF50'   # Green
    elif magnitude < 10.0:
        return '#FFFF00'   # Yellow
    elif magnitude < 50.0:
        return '#FF8C00'   # Orange
    else:
        return '#FF1400'   # Red


def pole_name(pole_val):
    names = {0: 'None', 1: 'N', 2: 'S'}
    return names.get(pole_val, '?')


async def read_characteristics(client):
    """Read all GATT characteristics once."""
    print("\n=== Flux Ring Status ===")

    try:
        fx = struct.unpack('<f', await client.read_gatt_char(CHAR_FIELD_X))[0]
        fy = struct.unpack('<f', await client.read_gatt_char(CHAR_FIELD_Y))[0]
        fz = struct.unpack('<f', await client.read_gatt_char(CHAR_FIELD_Z))[0]
        mag = struct.unpack('<f', await client.read_gatt_char(CHAR_MAGNITUDE))[0]
        heading = struct.unpack('<H', await client.read_gatt_char(CHAR_HEADING))[0]
        pole = (await client.read_gatt_char(CHAR_POLE))[0]
        sample_rate = (await client.read_gatt_char(CHAR_SAMPLE_RATE))[0]
        mode = (await client.read_gatt_char(CHAR_MODE))[0]
        battery = (await client.read_gatt_char(CHAR_BATTERY))[0]
        info = (await client.read_gatt_char(CHAR_DEVICE_INFO)).decode('utf-8', errors='replace')
    except Exception as e:
        print(f"Error reading characteristics: {e}")
        return

    mode_names = {0: 'Monitor', 1: 'Explore', 2: 'Mapping', 3: 'Compass'}
    rate_names = {0: '10Hz', 1: '100Hz', 2: '200Hz'}

    print(f"  Device:      {info}")
    print(f"  Mode:        {mode_names.get(mode, '?')} ({mode})")
    print(f"  Sample Rate:  {rate_names.get(sample_rate, '?')}")
    print(f"  Battery:     {battery}%")
    print(f"  Field X:     {fx:+.3f} Gauss")
    print(f"  Field Y:     {fy:+.3f} Gauss")
    print(f"  Field Z:     {fz:+.3f} Gauss")
    print(f"  Magnitude:   {mag:.3f} Gauss")
    print(f"  Heading:     {heading}°")
    print(f"  Pole:        {pole_name(pole)}")
    print()


async def notification_handler(characteristic, data):
    """Handle BLE notifications (streaming mode)."""
    global stream_file

    if len(data) == 24:
        # Stream packet: [ts(4)] [fx(4)] [fy(4)] [fz(4)] [ax(2)] [ay(2)] [az(2)] [heading(2)]
        ts, fx, fy, fz = struct.unpack('<Ifff', data[0:16])
        ax, ay, az = struct.unpack('<hhh', data[16:22])
        heading = struct.unpack('<H', data[22:24])[0]

        now = time.time()
        timestamps.append(now)
        field_x_data.append(fx)
        field_y_data.append(fy)
        field_z_data.append(fz)
        magnitude_data.append((fx**2 + fy**2 + fz**2)**0.5)

        if stream_file:
            stream_file.write(f"{ts},{fx:.4f},{fy:.4f},{fz:.4f},"
                             f"{ax},{ay},{az},{heading}\n")

    elif len(data) == 4:
        # Single characteristic notification
        val = struct.unpack('<f', data)[0]
        now = time.time()
        timestamps.append(now)
        magnitude_data.append(val)


async def run(mac_addr, stream=False, output_file=None, no_plot=False):
    global stream_mode, stream_file

    stream_mode = stream

    if output_file:
        stream_file = open(output_file, 'w')
        stream_file.write("timestamp_ms,field_x,field_y,field_z,accel_x,accel_y,accel_z,heading\n")

    print(f"Scanning for Flux Ring at {mac_addr}...")

    async with BleakClient(mac_addr) as client:
        print(f"Connected to {mac_addr}")

        # Read initial state
        await read_characteristics(client)

        if stream or not no_plot:
            # Enable notifications
            await client.start_notify(CHAR_FIELD_X, notification_handler)
            print("Notifications enabled — streaming field data...")

        # If in live plot mode
        if HAS_MPL and not no_plot:
            fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
            fig.suptitle('Flux Ring — Live Magnetic Field Data', fontsize=14)

            lines_x, = axes[0].plot([], [], 'r-', label='X', linewidth=0.8)
            lines_y, = axes[1].plot([], [], 'g-', label='Y', linewidth=0.8)
            lines_z, = axes[2].plot([], [], 'b-', label='Z', linewidth=0.8)
            lines_mag, = axes[3].plot([], [], 'k-', label='|B|', linewidth=1.2)

            for i, (ax, lbl) in enumerate(zip(axes, ['X (Gauss)', 'Y (Gauss)',
                                                       'Z (Gauss)', '|B| (Gauss)'])):
                ax.set_ylabel(lbl)
                ax.legend(loc='upper right')
                ax.grid(True, alpha=0.3)
            axes[3].set_xlabel('Time (s)')

            def animate(frame):
                if len(timestamps) > 1:
                    t = list(timestamps)
                    t0 = t[0]
                    t_rel = [x - t0 for x in t]

                    lines_x.set_data(t_rel, list(field_x_data))
                    lines_y.set_data(t_rel, list(field_y_data))
                    lines_z.set_data(t_rel, list(field_z_data))
                    lines_mag.set_data(t_rel, list(magnitude_data))

                    for ax in axes:
                        ax.relim()
                        ax.autoscale_view()

                return lines_x, lines_y, lines_z, lines_mag

            ani = animation.FuncAnimation(fig, animate, interval=50, blit=True)
            plt.show()
        else:
            # Console-only mode
            print("Press Ctrl+C to stop...")
            try:
                while True:
                    await asyncio.sleep(1)
                    if len(magnitude_data) > 0:
                        print(f"\r  |B| = {magnitude_data[-1]:.3f} Gauss  "
                              f"X={field_x_data[-1]:+.3f}  "
                              f"Y={field_y_data[-1]:+.3f}  "
                              f"Z={field_z_data[-1]:+.3f}", end='', flush=True)
            except KeyboardInterrupt:
                print("\nStopped.")

        if stream or not no_plot:
            await client.stop_notify(CHAR_FIELD_X)

    if stream_file:
        stream_file.close()
        print(f"\nData saved to {output_file}")


async def scan():
    """Scan for Flux Ring devices."""
    print("Scanning for Flux Ring devices...")
    devices = await BleakScanner.discover(timeout=10)
    found = False
    for d in devices:
        if 'Flux' in (d.name or ''):
            print(f"  {d.address}  {d.name}  RSSI={d.rssi}")
            found = True
    if not found:
        print("No Flux Ring devices found. Make sure the ring is powered on and advertising.")
        print("Tip: The device advertises as 'Flux Ring' via BLE.")


def main():
    parser = argparse.ArgumentParser(description='Flux Ring BLE Reader')
    parser.add_argument('--mac', help='Device MAC address')
    parser.add_argument('--scan', action='store_true', help='Scan for devices')
    parser.add_argument('--stream', action='store_true', help='Enable streaming mode')
    parser.add_argument('--output', '-o', help='Save stream data to CSV file')
    parser.add_argument('--no-plot', action='store_true', help='Console only, no plot')
    args = parser.parse_args()

    if args.scan:
        asyncio.run(scan())
    elif args.mac:
        asyncio.run(run(args.mac, stream=args.stream,
                        output_file=args.output, no_plot=args.no_plot))
    else:
        print("Provide --mac or --scan. Use --help for options.")


if __name__ == '__main__':
    main()