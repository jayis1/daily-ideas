#!/usr/bin/env python3
"""
Ping Caliper — read_ascan.py

Connect to a Ping Caliper over BLE, subscribe to the A-scan characteristic,
and plot a live A-scan (amplitude vs depth) with matplotlib.

Usage:
    python read_ascan.py --addr AA:BB:CC:DD:EE:FF
    python read_ascan.py --addr AA:BB:CC:DD:EE:FF --material "Steel (mild)" --velocity 5920

Requires: bleak, matplotlib, numpy
    pip install bleak matplotlib numpy
"""

import argparse
import asyncio
import struct
import sys
from collections import deque

import numpy as np

# BLE UUIDs (must match firmware/esp32c3/main/ble_ndt.c)
SVC_NDT      = "6e40fb10-b5a3-f393-e0a9-e50e24dcca9e"
CHR_ASCAN    = "6e40fb11-b5a3-f393-e0a9-e50e24dcca9e"   # actually A-scan
CHR_MEAS     = "6e40fb11-b5a3-f393-e0a9-e50e24dcca9e"
# (note: the firmware uses ...11fb... for measurement; here we subscribe to both)
CHR_MEASUREMENT = "6e40fb11-b5a3-f393-e0a9-e50e24dcca9e"
CHR_ASCAN_ACT    = "6e40fb12-b5a3-f393-e0a9-e50e24dcca9e"
CHR_STATUS       = "6e40fb13-b5a3-f393-e0a9-e50e24dcca9e"


def parse_ascan_chunk(data: bytes):
    """Parse an A-scan chunk notification (chunk_idx + total + count + 64 samples)."""
    if len(data) < 6:
        return None
    chunk_idx, total_chunks, count = struct.unpack_from("<HHH", data, 0)
    samples = np.frombuffer(data, dtype="<u2", count=64, offset=6)
    return chunk_idx, total_chunks, count, samples


class AscanBuffer:
    """Reassemble A-scan chunks into a full envelope."""
    def __init__(self, total_chunks, count):
        self.total = total_chunks
        self.count = count
        self.chunks = {}

    def add(self, chunk_idx, samples):
        self.chunks[chunk_idx] = samples

    def complete(self):
        return len(self.chunks) == self.total

    def assemble(self):
        env = np.concatenate([self.chunks[i] for i in range(self.total)])
        return env[:self.count]


async def run(addr: str, material: str, velocity: int, max_depth_mm: float):
    from bleak import BleakClient

    print(f"Connecting to {addr} ...")
    async with BleakClient(addr, timeout=15.0) as client:
        print(f"Connected. RSSI: {await client.get_rssi()}")
        print(f"Subscribing to A-scan + measurement ...")

        buffer = None
        latest_thickness = None

        def ascan_handler(sender, data: bytearray):
            nonlocal buffer
            parsed = parse_ascan_chunk(bytes(data))
            if parsed is None:
                return
            chunk_idx, total, count, samples = parsed
            if buffer is None or buffer.total != total:
                buffer = AscanBuffer(total, count)
            buffer.add(chunk_idx, samples)
            if buffer.complete():
                env = buffer.assemble()
                plot_ascan(env, velocity, max_depth_mm, latest_thickness)
                buffer = None

        def meas_handler(sender, data: bytearray):
            nonlocal latest_thickness
            if len(data) >= 8:
                thickness_mm, tof_ns = struct.unpack_from("<ff", data, 0)
                latest_thickness = thickness_mm
                print(f"\r  thickness = {thickness_mm:.3f} mm  (tof = {tof_ns:.0f} ns)",
                      end="", flush=True)

        await client.start_notify(CHR_ASCAN_ACT, ascan_handler)
        await client.start_notify(CHR_MEASUREMENT, meas_handler)

        print("\nLive A-scan streaming. Ctrl-C to stop.")
        try:
            while True:
                await asyncio.sleep(1.0)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await client.stop_notify(CHR_ASCAN_ACT)
            await client.stop_notify(CHR_MEASUREMENT)


def plot_ascan(env, velocity, max_depth_mm, thickness_mm):
    """Stub plot: in a real interactive session, use matplotlib FuncAnimation."""
    n = len(env)
    # Depth axis: d = (v * t) / 2 where t = i / sample_rate
    # sample_rate = 5 Msps → t = i * 200 ns → d_mm = v * i * 200e-9 / 2 * 1000
    sample_ns = 200.0   # 5 Msps
    depth_mm = np.arange(n) * (velocity * sample_ns * 1e-9 * 0.5 * 1000.0)
    peak_idx = int(np.argmax(env))
    peak_depth = depth_mm[peak_idx]
    print(f"\n  A-scan: {n} samples, peak at sample {peak_idx} "
          f"(depth {peak_depth:.2f} mm), amp {env[peak_idx]}/4095")
    if thickness_mm:
        print(f"  Reported thickness: {thickness_mm:.3f} mm")


def main():
    p = argparse.ArgumentParser(description="Ping Caliper BLE A-scan viewer")
    p.add_argument("--addr", required=True, help="BLE MAC address")
    p.add_argument("--material", default="Steel (mild)", help="Material name")
    p.add_argument("--velocity", type=int, default=5920, help="Wave velocity (m/s)")
    p.add_argument("--max-depth", type=float, default=50.0, help="Max depth (mm)")
    args = p.parse_args()
    try:
        asyncio.run(run(args.addr, args.material, args.velocity, args.max_depth))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()