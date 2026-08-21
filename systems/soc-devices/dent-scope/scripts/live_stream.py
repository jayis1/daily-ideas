#!/usr/bin/env python3
"""
Dent Scope — Live BLE/Wi-Fi streaming and P–h curve plotter

Connects to Dent Scope via BLE (using bleak) or Wi-Fi (using websocket)
and plots the load–displacement curve in real time.

Usage:
  python3 live_stream.py --ble
  python3 live_stream.py --wifi 192.168.4.1

Requires: bleak, matplotlib (BLE mode) or websocket-client, matplotlib (Wi-Fi mode)

MIT License
"""
import argparse
import asyncio
import struct
import json
from collections import deque

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

# BLE UUIDs
SERVICE_UUID = "00008801-0000-1000-8000-00805f9b34fb"
DATA_UUID    = "00008802-0000-1000-8000-00805f9b34fb"
RESULT_UUID  = "00008803-0000-1000-8000-00805f9b34fb"
CMD_UUID     = "00008804-0000-1000-8000-00805f9b34fb"

class DentScopeData:
    def __init__(self):
        self.forces = deque(maxlen=10000)
        self.depths = deque(maxlen=10000)
        self.times = deque(maxlen=10000)

    def add_point(self, force_mN, depth_um, t_ms):
        self.forces.append(force_mN / 1000.0)  # mN → N
        self.depths.append(depth_um)
        self.times.append(t_ms)

def parse_data(data):
    """Parse 12-byte data point notification"""
    if len(data) < 12:
        return None
    force_mN, depth_um, t_ms = struct.unpack('<ffI', data[:12])
    return force_mN, depth_um, t_ms

async def ble_stream():
    from bleak import BleakClient
    ds_data = DentScopeData()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))
    fig.suptitle("Dent Scope — Live P–h Curve")

    line_ph, = ax1.plot([], [], 'b-', linewidth=1.5)
    ax1.set_xlabel('Depth h (µm)')
    ax1.set_ylabel('Force P (N)')
    ax1.set_title('Load–Displacement (P–h) Curve')
    ax1.grid(True)
    ax1.set_xlim(0, 50)
    ax1.set_ylim(0, 25)

    line_time, = ax2.plot([], [], 'r-', linewidth=1.0)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Force (N)')
    ax2.set_title('Force vs Time')
    ax2.grid(True)

    plt.ion()
    plt.show()

    def notification_handler(sender, data):
        point = parse_data(data)
        if point:
            force_mN, depth_um, t_ms = point
            ds_data.add_point(force_mN, depth_um, t_ms)
            # update plots
            line_ph.set_data(list(ds_data.depths), list(ds_data.forces))
            line_time.set_data([t / 1000.0 for t in ds_data.times], list(ds_data.forces))
            if ds_data.depths:
                ax1.set_xlim(0, max(ds_data.depths) * 1.1 + 0.1)
                ax1.set_ylim(0, max(ds_data.forces) * 1.1 + 0.1)
                ax2.set_xlim(0, max(ds_data.times) / 1000.0 * 1.1 + 0.1)
                ax2.set_ylim(0, max(ds_data.forces) * 1.1 + 0.1)
            plt.draw()
            plt.pause(0.001)

    # Scan and connect
    print("Scanning for Dent Scope...")
    from bleak import BleakScanner
    devices = await BleakScanner.discover(timeout=5.0)
    target = None
    for d in devices:
        if "DentScope" in (d.name or ""):
            target = d
            break
    if not target:
        print("Dent Scope not found. Make sure it's powered on and advertising.")
        return
    print(f"Found: {target.name} [{target.address}]")
    async with BleakClient(target.address) as client:
        print("Connected. Subscribing to data...")
        await client.start_notify(DATA_UUID, notification_handler)

        # Send START command
        print("Sending START command...")
        start_cmd = bytes([0xAA, 0x55, 0x10, 0x00, 0x00])
        # compute CRC
        crc = 0xFFFF
        for b in start_cmd:
            crc ^= b
            for _ in range(8):
                if crc & 1: crc = (crc >> 1) ^ 0xA001
                else: crc >>= 1
        start_cmd += struct.pack('<H', crc)
        await client.write_gatt_char(CMD_UUID, start_cmd)

        print("Streaming... Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            pass
        await client.stop_notify(DATA_UUID)
    plt.ioff()

def wifi_stream(ip):
    """Wi-Fi mode using websocket"""
    import websocket
    import threading
    import time

    ds_data = DentScopeData()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 8))
    fig.suptitle("Dent Scope — Live P–h Curve (Wi-Fi)")
    line_ph, = ax1.plot([], [], 'b-', linewidth=1.5)
    ax1.set_xlabel('Depth h (µm)')
    ax1.set_ylabel('Force P (N)')
    ax1.grid(True)
    line_time, = ax2.plot([], [], 'r-', linewidth=1.0)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Force (N)')
    ax2.grid(True)
    plt.ion()
    plt.show()

    def on_message(ws, message):
        try:
            d = json.loads(message)
            ds_data.add_point(d['force_mN'], d['depth_um'], d['t_ms'])
            line_ph.set_data(list(ds_data.depths), list(ds_data.forces))
            line_time.set_data([t / 1000.0 for t in ds_data.times], list(ds_data.forces))
            if ds_data.depths:
                ax1.set_xlim(0, max(ds_data.depths) * 1.1 + 0.1)
                ax1.set_ylim(0, max(ds_data.forces) * 1.1 + 0.1)
            plt.draw()
            plt.pause(0.001)
        except Exception as e:
            pass

    ws = websocket.WebSocketApp(f"ws://{ip}/ws",
                                 on_message=on_message)
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    try:
        while True:
            plt.pause(0.1)
    except KeyboardInterrupt:
        ws.close()

def main():
    parser = argparse.ArgumentParser(description='Dent Scope live stream')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--ble', action='store_true', help='Connect via BLE')
    group.add_argument('--wifi', metavar='IP', help='Connect via Wi-Fi (IP address)')
    args = parser.parse_args()

    if args.ble:
        asyncio.run(ble_stream())
    elif args.wifi:
        wifi_stream(args.wifi)

if __name__ == '__main__':
    main()