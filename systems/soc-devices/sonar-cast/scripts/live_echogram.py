#!/usr/bin/env python3
"""
Sonar Cast — live_echogram.py
Connects to Sonar Cast via BLE, displays a live scrolling water-column echogram
plus depth, bottom type, and fish marks.

Usage:
    python3 live_echogram.py [--mac AA:BB:CC:DD:EE:FF]

Requires: bleak, matplotlib, numpy
    pip install bleak matplotlib numpy
"""
import argparse
import asyncio
import struct
from collections import deque

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install: pip install bleak matplotlib numpy")
    raise

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

SVC_UUID   = "00009301-1212-efde-1523-785feabcd123"
CHR_ECHO   = "00009302-1212-efde-1523-785feabcd123"
CHR_CMD    = "00009303-1212-efde-1523-785feabcd123"

BOTTOM_NAMES = ["hard", "soft", "weedy", "unknown"]
HISTORY = 120   # number of pings to show in the waterfall
BINS    = 128

waterfall = deque(maxlen=HISTORY)
info = {"depth": 0, "bottom": "---", "fish": 0, "temp": 0}


def parse_result(data: bytes):
    """Parse a type=0x01 result frame (payload only, sync+len+crc stripped)."""
    if len(data) < 27 or data[0] != 0x01:
        return
    depth, depth_p, btype, bconf, fcount = struct.unpack_from("<ffBfB", data, 1)
    off = 15
    fish_depths = []
    for _ in range(fcount):
        fd, fl, ts = struct.unpack_from("<fff", data, off)
        fish_depths.append((fd, fl))
        off += 12
    temp, ss, tilt = struct.unpack_from("<fff", data, off)
    off += 12
    echo = list(data[off:off + 128])
    info["depth"] = depth
    info["bottom"] = BOTTOM_NAMES[btype if btype < 4 else 3]
    info["fish"] = fcount
    info["temp"] = temp
    waterfall.append(echo)


def on_echo(sender, data: bytearray):
    if len(data) >= 4 and data[0] == 0xAA and data[1] == 0x55:
        plen = data[2] | (data[3] << 8)
        payload = bytes(data[4:4 + plen])
        parse_result(payload)


async def run(mac):
    fig, (ax_e, ax_i) = plt.subplots(1, 2, gridspec_kw={"width_ratios": [3, 1]})
    fig.canvas.manager.set_window_title("Sonar Cast — Live Echogram")

    print(f"Scanning for Sonar Cast{' ('+mac+')' if mac else ''}...")
    if mac:
        client = BleakClient(mac)
    else:
        dev = await BleakScanner.find_device_by_name("SonarCast")
        if not dev:
            print("No Sonar Cast found. Pass --mac.")
            return
        client = BleakClient(dev)

    await client.connect()
    await client.start_notify(CHR_ECHO, on_echo)
    print("Connected. Listening for echogram frames... (Ctrl+C to stop)")

    import matplotlib.animation as animation

    def update(_):
        if not waterfall:
            return
        arr = np.array(waterfall).T  # shape (128, n_pings)
        ax_e.clear()
        ax_e.imshow(arr, aspect="auto", cmap="inferno",
                    vmin=0, vmax=255, origin="upper",
                    extent=[0, arr.shape[1], BINS, 0])
        ax_e.set_xlabel("Ping #")
        ax_e.set_ylabel("Range bin (0=surface → 128=deep)")
        ax_e.set_title(f"Depth: {info['depth']:.1f} m  |  Bottom: {info['bottom']}"
                       f"  |  Fish: {info['fish']}  |  T: {info['temp']:.1f}°C")

        ax_i.clear()
        ax_i.axis("off")
        ax_i.text(0.05, 0.9, f"Depth\n  {info['depth']:.2f} m", fontsize=14)
        ax_i.text(0.05, 0.7, f"Bottom\n  {info['bottom']}", fontsize=14)
        ax_i.text(0.05, 0.5, f"Fish\n  {info['fish']}", fontsize=14)
        ax_i.text(0.05, 0.3, f"Temp\n  {info['temp']:.1f} °C", fontsize=14)

    ani = animation.FuncAnimation(fig, update, interval=200, cache_frame_data=False)
    plt.show(block=True)

    try:
        while client.is_connected:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await client.stop_notify(CHR_ECHO)
        await client.disconnect()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mac", default=None, help="Sonar Cast BLE MAC address")
    args = p.parse_args()
    asyncio.run(run(args.mac))