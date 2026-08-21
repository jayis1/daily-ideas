#!/usr/bin/env python3
"""
live_view.py — Real-time BLE dashboard for QCM Halo

Connects to the ESP32-C3 BLE module and displays live Δf and ΔD plots
in a matplotlib GUI. Also shows Sauerbrey mass and Voigt fit results.

Usage:
    python3 live_view.py

Requires: bleak, matplotlib, numpy
"""

import asyncio
import struct
import sys
from datetime import datetime

try:
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    from bleak import BleakClient
except ImportError:
    print("Install: pip install bleak matplotlib numpy")
    sys.exit(1)

# BLE UUIDs (Nordic UART-like service)
SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
TX_CHAR_UUID  = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Write
RX_CHAR_UUID  = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Notify

# Frame protocol
SYNC0 = 0xA5
SYNC1 = 0x5A

# Data storage
timestamps = []
delta_f_data = []
delta_d_data = []
sauerbrey_mass = []
max_points = 600  # 10 min at 1 Hz

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
fig.suptitle("QCM Halo — Live Dashboard", fontsize=14)

def crc8(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x07
            else:
                crc <<= 1
            crc &= 0xFF
    return crc

def parse_result(data):
    """Parse a 26-byte result packet (cmd 0x01)"""
    if len(data) < 26:
        return None
    channel, overtone_n = data[0], data[1]
    delta_f = struct.unpack_from('<f', data, 2)[0]
    dissipation = struct.unpack_from('<f', data, 6)[0]
    delta_d = struct.unpack_from('<f', data, 10)[0]
    temp = struct.unpack_from('<f', data, 14)[0]
    mass = struct.unpack_from('<f', data, 18)[0]
    ts = struct.unpack_from('<I', data, 22)[0]
    return {
        'channel': channel,
        'overtone': overtone_n,
        'delta_f': delta_f,
        'dissipation': dissipation,
        'delta_d': delta_d,
        'temp': temp,
        'mass': mass,
        'timestamp': ts,
    }

def parse_frame(data):
    """Extract frames from received BLE data"""
    results = []
    i = 0
    while i < len(data) - 4:
        if data[i] == SYNC0 and data[i+1] == SYNC1:
            cmd = data[i+2]
            plen = data[i+3]
            if i + 5 + plen <= len(data):
                payload = data[i+4:i+4+plen]
                expected_crc = crc8(data[i+2:i+4+plen])
                if data[i+4+plen] == expected_crc:
                    if cmd == 0x01:
                        r = parse_result(payload)
                        if r:
                            results.append(('result', r))
                    elif cmd == 0x04:
                        if len(payload) >= 8:
                            temp = struct.unpack_from('<f', payload, 0)[0]
                            vbat = struct.unpack_from('<f', payload, 4)[0]
                            results.append(('status', {'temp': temp, 'vbat': vbat}))
                    i += 5 + plen
                    continue
        i += 1
    return results

# BLE receive buffer
rx_buffer = bytearray()

def notification_handler(sender, data):
    global rx_buffer
    rx_buffer.extend(data)
    msgs = parse_frame(bytes(rx_buffer))
    for msg_type, msg_data in msgs:
        if msg_type == 'result':
            timestamps.append(datetime.now())
            delta_f_data.append(msg_data['delta_f'])
            delta_d_data.append(msg_data['delta_d'])
            sauerbrey_mass.append(msg_data['mass'])
            if len(timestamps) > max_points:
                timestamps.pop(0)
                delta_f_data.pop(0)
                delta_d_data.pop(0)
                sauerbrey_mass.pop(0)
            print(f"Δf={msg_data['delta_f']:.2f} Hz  ΔD={msg_data['delta_d']:.2e}  "
                  f"mass={msg_data['mass']:.1f} ng/cm²  T={msg_data['temp']:.1f}°C")

def send_command(client, cmd, payload=b''):
    frame = bytes([SYNC0, SYNC1, cmd, len(payload)]) + payload
    frame += bytes([crc8(frame[2:])])
    return client.write_gatt_char(TX_CHAR_UUID, frame, response=True)

async def run():
    print("Scanning for QCM Halo BLE device...")
    from bleak import BleakScanner
    devices = await BleakScanner.discover()
    qcm_device = None
    for d in devices:
        if "QCM" in (d.name or ""):
            qcm_device = d
            break

    if not qcm_device:
        print("QCM Halo not found. Make sure it's powered on and advertising.")
        return

    print(f"Found: {qcm_device.name} [{qcm_device.address}]")

    async with BleakClient(qcm_device) as client:
        print("Connected!")
        await client.start_notify(RX_CHAR_UUID, notification_handler)

        # Start measurement
        await send_command(client, 0x81, bytes([0, 1, 0]))  # ch=0, ov=1, no sweep

        # Keep connection alive
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            await send_command(client, 0x82)  # STOP
            await client.stop_notify(RX_CHAR_UUID)

def update_plot(frame):
    ax1.clear()
    ax2.clear()
    ax3.clear()

    if timestamps:
        ax1.plot(timestamps, delta_f_data, 'b-', linewidth=1)
        ax1.set_ylabel('Δf (Hz)')
        ax1.grid(True, alpha=0.3)

        ax2.plot(timestamps, delta_d_data, 'r-', linewidth=1)
        ax2.set_ylabel('ΔD')
        ax2.grid(True, alpha=0.3)

        ax3.plot(timestamps, sauerbrey_mass, 'g-', linewidth=1)
        ax3.set_ylabel('Mass (ng/cm²)')
        ax3.set_xlabel('Time')
        ax3.grid(True, alpha=0.3)

    fig.suptitle(f"QCM Halo — {len(timestamps)} points", fontsize=12)

def main():
    # Start BLE in background
    ble_thread = asyncio.ensure_future(run())

    # Run matplotlib in main thread
    ani = FuncAnimation(fig, update_plot, interval=1000, cache_frame_data=False)
    plt.show()

    # Clean up
    asyncio.get_event_loop().run_until_complete(asyncio.wait_for(ble_thread, timeout=1))

if __name__ == "__main__":
    main()