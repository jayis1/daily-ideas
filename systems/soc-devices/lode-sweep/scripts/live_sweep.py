#!/usr/bin/env python3
"""
Lode Sweep — live_sweep.py
BLE-connected live target identification display.

Connects to the Lode Sweep device over BLE, receives target result frames,
and displays a live matplotlib view showing:
  - Current target class (color-coded)
  - Depth estimate
  - Signal strength bar
  - 16-gate decay curve
  - Rolling detection history

Usage:
    python3 live_sweep.py [--addr BLE_MAC]

Requires: bleak, matplotlib, numpy
    pip install bleak matplotlib numpy
"""
import asyncio
import struct
import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from bleak import BleakClient

# BLE UUIDs (must match firmware/esp32c3/main.c)
SERVICE_UUID = "00009401-1212-efde-1523-785feabcd123"
RESULT_UUID  = "00009402-1212-efde-1523-785feabcd123"
COMMAND_UUID = "00009403-1212-efde-1523-785feabcd123"

CLASS_NAMES = ["Iron", "Foil", "Nickel", "Pull-Tab",
               "Zinc", "Gold", "Copper", "Silver"]
CLASS_COLORS = ["#444444", "#888888", "#22dd22", "#44aaff",
                "#ffaa22", "#ff6622", "#cccccc", "#ffdd00"]
GATE_DELAY = np.array([
    10.0, 12.5, 15.6, 19.5, 24.4, 30.5, 38.1, 47.7,
    59.6, 74.5, 93.1, 116.4, 145.5, 181.9, 227.4, 284.2
])

# Latest result (updated by BLE callback)
latest = {
    "class": 0, "confidence": 0, "depth": 0, "signal": 0,
    "tilt": 0, "decay": np.zeros(16),
    "lat": 0, "lon": 0, "ts": 0,
}


def parse_result(data: bytes):
    """Parse a type 0x01 result frame payload (after sync+len+type)."""
    if len(data) < 94:
        return
    cls = data[0]
    conf, depth, signal, tilt = struct.unpack_from("<ffff", data, 1)
    decay = np.array(struct.unpack_from("<16f", data, 17))
    lat, lon, hdop = struct.unpack_from("<fff", data, 81)
    ts = struct.unpack_from("<I", data, 93)[0]
    latest.update({
        "class": cls, "confidence": conf, "depth": depth,
        "signal": signal, "tilt": tilt, "decay": decay,
        "lat": lat, "lon": lon, "ts": ts,
    })


def notification_handler(sender, data: bytearray):
    """BLE notification callback — parse result frames."""
    # Look for sync bytes 0xAA 0x55
    if len(data) >= 6 and data[0] == 0xAA and data[1] == 0x55:
        body_len = data[2] | (data[3] << 8)
        if body_len >= 2 and data[4] == 0x01:
            parse_result(bytes(data[5:]))


async def ble_loop(addr: str):
    """Connect to device and subscribe to result notifications."""
    async with BleakClient(addr) as client:
        print(f"Connected to {addr}")
        await client.start_notify(RESULT_UUID, notification_handler)
        # Keep connection alive
        while True:
            await asyncio.sleep(1)


def update_plot(frame, ax_lines, ax_info):
    """Matplotlib animation update — refresh display from latest data."""
    ax_lines.clear()
    ax_info.clear()

    cls = latest["class"]
    name = CLASS_NAMES[cls] if cls < 8 else "?"
    color = CLASS_COLORS[cls] if cls < 8 else "#000000"

    # Decay curve
    ax_lines.plot(GATE_DELAY, latest["decay"], color=color, linewidth=2)
    ax_lines.set_xlim(0, 300)
    ax_lines.set_ylim(-0.1, 1.1)
    ax_lines.set_xlabel("Delay (µs)")
    ax_lines.set_ylabel("Normalized signal")
    ax_lines.set_title(f"Decay Curve — {name}", color=color, fontsize=14)
    ax_lines.grid(True, alpha=0.3)

    # Info panel
    ax_info.axis("off")
    info_text = (
        f"Target:  {name}\n"
        f"Conf:    {latest['confidence']*100:.0f}%\n"
        f"Depth:   {latest['depth']:.0f} cm\n"
        f"Signal:  {latest['signal']:.3f}\n"
        f"Tilt:    {latest['tilt']:.0f}°\n"
        f"GPS:     {latest['lat']:.5f}, {latest['lon']:.5f}\n"
    )
    ax_info.text(0.1, 0.9, info_text, transform=ax_info.transAxes,
                 fontsize=14, verticalalignment="top", family="monospace",
                 color=color)
    # Signal strength bar
    bar_y = 0.2
    bar_w = min(latest["signal"] * 10, 1.0)
    ax_info.add_patch(plt.Rectangle((0.1, bar_y), bar_w, 0.05,
                     transform=ax_info.transAxes, color=color, alpha=0.7))
    ax_info.add_patch(plt.Rectangle((0.1, bar_y), 1.0, 0.05,
                     transform=ax_info.transAxes, fill=False,
                     edgecolor="gray"))


def main():
    parser = argparse.ArgumentParser(description="Lode Sweep live display")
    parser.add_argument("--addr", required=True, help="BLE MAC address")
    args = parser.parse_args()

    fig, (ax_lines, ax_info) = plt.subplots(1, 2, figsize=(12, 5),
                                            gridspec_kw={"width_ratios": [3, 1]})
    fig.suptitle("Lode Sweep — Live Target Identification", fontsize=16)

    ani = FuncAnimation(fig, update_plot, fargs=(ax_lines, ax_info),
                        interval=100, cache_frame_data=False)

    # Start BLE loop in background
    import threading
    ble_thread = threading.Thread(
        target=lambda: asyncio.run(ble_loop(args.addr)), daemon=True)
    ble_thread.start()

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()