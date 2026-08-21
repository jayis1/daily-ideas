#!/usr/bin/env python3
"""
Gossamer Spin — live_monitor.py
BLE-connected live electrospinning process monitor.

Connects to the Gossamer Spin device over BLE, receives process data frames,
and displays a live matplotlib dashboard showing:
  - HV voltage (kV) with target line
  - Jet current (nA) with state classification
  - Flow rate and drum RPM
  - Temperature and humidity
  - Rolling 60-second time series charts

Usage:
    python3 live_monitor.py [--addr BLE_MAC]

Requires: bleak, matplotlib, numpy
    pip install bleak matplotlib numpy
"""
import asyncio
import struct
import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
from bleak import BleakClient

# BLE UUIDs (must match firmware/esp32c3/main.c)
SERVICE_UUID = "00009501-1212-efde-1523-785feabcd123"
PROCESS_UUID = "00009502-1212-efde-1523-785feabcd123"
COMMAND_UUID = "00009503-1212-efde-1523-785feabcd123"

JET_STATE_NAMES = ["IDLE", "STABLE", "INTERRUPTED", "UNSTABLE", "DRIPPING"]
JET_STATE_COLORS = ["#888888", "#22cc22", "#ff8800", "#ff4444", "#ff00ff"]

# History buffers (60 seconds at 10 Hz = 600 points)
HISTORY = 600
hist_time = deque(maxlen=HISTORY)
hist_hv = deque(maxlen=HISTORY)
hist_current = deque(maxlen=HISTORY)
hist_temp = deque(maxlen=HISTORY)
hist_rh = deque(maxlen=HISTORY)

latest = {
    "hv": 0, "current": 0, "flow": 0, "rpm": 0,
    "temp": 0, "rh": 0, "jet_state": 0, "sigma": 0,
    "elapsed": 0,
}
t_counter = 0


def parse_process(data: bytes):
    """Parse a type 0x01 process data frame payload (33 bytes)."""
    if len(data) < 33:
        return
    hv, current, flow, rpm, temp, rh = struct.unpack_from("<6f", data, 0)
    jet_state = data[24]
    sigma = struct.unpack_from("<f", data, 25)[0]
    elapsed = struct.unpack_from("<I", data, 29)[0]

    global t_counter
    t_counter += 0.1  # 10 Hz

    latest.update({
        "hv": hv, "current": current, "flow": flow, "rpm": rpm,
        "temp": temp, "rh": rh, "jet_state": jet_state,
        "sigma": sigma, "elapsed": elapsed,
    })
    hist_time.append(t_counter)
    hist_hv.append(hv)
    hist_current.append(current)
    hist_temp.append(temp)
    hist_rh.append(rh)


def notification_handler(sender, data: bytearray):
    """BLE notification callback — parse process frames."""
    if len(data) >= 6 and data[0] == 0xAA and data[1] == 0x55:
        body_len = data[2] | (data[3] << 8)
        if body_len >= 33 and data[4] == 0x01:
            parse_process(bytes(data[5:]))


async def ble_loop(addr: str):
    """Connect to device and subscribe to process notifications."""
    async with BleakClient(addr) as client:
        print(f"Connected to {addr}")
        await client.start_notify(PROCESS_UUID, notification_handler)
        while True:
            await asyncio.sleep(1)


def update_plot(frame, axes):
    """Matplotlib animation update — refresh all charts."""
    ax_hv, ax_i, ax_env, ax_info = axes

    for ax in axes:
        ax.clear()

    # HV voltage chart
    if hist_time:
        ax_hv.plot(list(hist_time), list(hist_hv), 'b-', linewidth=1.5)
        ax_hv.set_ylabel("HV (kV)")
        ax_hv.set_title("High Voltage", fontsize=11)
        ax_hv.grid(True, alpha=0.3)
        ax_hv.set_ylim(0, 35)

    # Jet current chart (color-coded by state)
    if hist_time:
        color = JET_STATE_COLORS[latest["jet_state"] if latest["jet_state"] < 5 else 0]
        ax_i.plot(list(hist_time), list(hist_current), color=color, linewidth=1.5)
        ax_i.axhline(y=20, color='orange', linestyle='--', alpha=0.5, label='Interrupt threshold')
        ax_i.axhline(y=800, color='red', linestyle='--', alpha=0.5, label='Drip threshold')
        ax_i.set_ylabel("Jet Current (nA)")
        state_name = JET_STATE_NAMES[latest["jet_state"] if latest["jet_state"] < 5 else 0]
        ax_i.set_title(f"Jet Current — {state_name}", fontsize=11, color=color)
        ax_i.grid(True, alpha=0.3)
        ax_i.legend(fontsize=7, loc='upper left')

    # Environment chart
    if hist_time:
        ax_env.plot(list(hist_time), list(hist_temp), 'r-', linewidth=1, label='Temp (°C)')
        ax_env2 = ax_env.twinx()
        ax_env2.plot(list(hist_time), list(hist_rh), 'g-', linewidth=1, label='RH (%)')
        ax_env.set_ylabel("Temp (°C)", color='r', fontsize=9)
        ax_env2.set_ylabel("RH (%)", color='g', fontsize=9)
        ax_env.set_title("Chamber Environment", fontsize=11)
        ax_env.grid(True, alpha=0.3)

    # Info panel
    ax_info.axis('off')
    state_name = JET_STATE_NAMES[latest["jet_state"] if latest["jet_state"] < 5 else 0]
    info = (
        f"HV:      {latest['hv']:5.1f} kV\n"
        f"Current: {latest['current']:5.0f} nA\n"
        f"σ:       {latest['sigma']:5.0f} nA\n"
        f"State:   {state_name}\n"
        f"Flow:    {latest['flow']:5.2f} mL/h\n"
        f"Drum:    {latest['rpm']:5.0f} RPM\n"
        f"Temp:    {latest['temp']:5.1f} °C\n"
        f"RH:      {latest['rh']:5.1f} %\n"
        f"Elapsed: {latest['elapsed']} s"
    )
    color = JET_STATE_COLORS[latest["jet_state"] if latest["jet_state"] < 5 else 0]
    ax_info.text(0.05, 0.95, info, transform=ax_info.transAxes,
                 fontsize=11, verticalalignment='top', family='monospace',
                 color=color)


def main():
    parser = argparse.ArgumentParser(description="Gossamer Spin live monitor")
    parser.add_argument("--addr", required=True, help="BLE MAC address")
    args = parser.parse_args()

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    axes_flat = [axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]]
    fig.suptitle("Gossamer Spin — Live Process Monitor", fontsize=14)

    ani = FuncAnimation(fig, update_plot, fargs=(axes_flat,),
                        interval=200, cache_frame_data=False)

    ble_thread = threading.Thread(
        target=lambda: asyncio.run(ble_loop(args.addr)), daemon=True)
    ble_thread.start()

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    import threading
    main()