#!/usr/bin/env python3
"""
live_view.py — Vibra Beam live waveform + spectrum viewer
Connects via BLE (via bleak) or Wi-Fi (via the ESP32-C3's TCP socket)
and plots the incoming velocity stream + live FFT in real time.

Usage:
    python3 live_view.py --ble
    python3 live_view.py --wifi 192.168.4.1
"""
import argparse
import struct
import threading
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

SYNC = 0xAA

# ---- BLE ----
def ble_stream(on_sample):
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError:
        print("Install bleak: pip install bleak")
        return
    # The ESP32-C3 exposes a Nordic UART-like service.
    UART_RX = "6e400003-b5a3-f393-e0a9-e50e24dcca9b"
    async def run():
        devices = await BleakScanner.discover()
        target = next((d for d in devices if "Vibra" in (d.name or "")), None)
        if not target:
            print("Vibra Beam not found")
            return
        async with BleakClient(target) as client:
            buf = bytearray()
            def cb(_, data):
                buf.extend(data)
                while len(buf) >= 5:
                    if buf[0] != SYNC:
                        del buf[0]; continue
                    ln = (buf[2] << 8) | buf[3]
                    if len(buf) >= 5 + ln:
                        payload = bytes(buf[4:4+ln])
                        crc = buf[4+ln]
                        if crc ^ 0 == 0:  # placeholder CRC check
                            if buf[1] == 0x03:  # STREAM
                                t_ms, n = struct.unpack("<IH", payload[:6])
                                vels = struct.unpack(f"<{n}f", payload[6:6+4*n])
                                on_sample(np.array(vels))
                        del buf[:5+ln]
            await client.start_notify(UART_RX, cb)
            while True:
                await __import__('asyncio').sleep(0.1)
    import asyncio
    asyncio.run(run())

# ---- Wi-Fi ----
def wifi_stream(host, port=3333, on_sample=None):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    buf = bytearray()
    while True:
        data = s.recv(256)
        if not data: break
        buf.extend(data)
        while len(buf) >= 5:
            if buf[0] != SYNC:
                del buf[0]; continue
            ln = (buf[2] << 8) | buf[3]
            if len(buf) >= 5 + ln:
                payload = bytes(buf[4:4+ln])
                if buf[1] == 0x03:
                    t_ms, n = struct.unpack("<IH", payload[:6])
                    vels = struct.unpack(f"<{n}f", payload[6:6+4*n])
                    on_sample(np.array(vels))
                del buf[:5+ln]

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ble", action="store_true")
    ap.add_argument("--wifi", type=str, default=None)
    ap.add_argument("--port", type=int, default=3333)
    args = ap.parse_args()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
    line1, = ax1.plot([], [], lw=1)
    line2, = ax2.semilogy([], [], lw=1)
    ax1.set_title("Velocity (mm/s)")
    ax2.set_title("Spectrum")
    ax2.set_xlabel("Frequency (Hz)")
    state = {"vel": np.zeros(64), "spec": np.zeros(64)}

    def on_sample(v):
        state["vel"] = v
        state["spec"] = np.abs(np.fft.rfft(v))

    def update(frame):
        line1.set_data(np.arange(len(state["vel"])), state["vel"])
        ax1.relim(); ax1.autoscale_view()
        line2.set_data(np.arange(len(state["spec"])) * 25.0, state["spec"] + 1e-9)
        ax2.relim(); ax2.autoscale_view()
        return line1, line2

    if args.ble:
        threading.Thread(target=ble_stream, args=(on_sample,), daemon=True).start()
    elif args.wifi:
        threading.Thread(target=wifi_stream, args=(args.wifi, args.port, on_sample), daemon=True).start()
    else:
        print("Specify --ble or --wifi <ip>")

    ani = FuncAnimation(fig, update, interval=50, blit=True)
    plt.show()