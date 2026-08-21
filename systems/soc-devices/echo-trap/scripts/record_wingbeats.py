#!/usr/bin/env python3
"""
Echo Trap — record_wingbeats.py

Connect to an Echo Trap over BLE, subscribe to the Audio Stream
characteristic, and save raw I²S audio to disk for dataset collection.

Usage:
    python record_wingbeats.py --addr AA:BB:CC:DD:EE:FF \
        --output dataset/ --species aedes --duration 60

Requires: bleak, numpy
    pip install bleak numpy

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import asyncio
import os
import struct
import time
from pathlib import Path

import numpy as np

# BLE UUIDs (must match firmware)
SVC_ECHO_TRAP   = "6e41ec00-b5a3-f393-e0a9-e50e24dcca9e"
CHR_DEVICE_INFO = "6e41ec01-b5a3-f393-e0a9-e50e24dcca9e"
CHR_COMMAND     = "6e41ec08-b5a3-f393-e0a9-e50e24dcca9e"
CHR_AUDIO_STREAM = "6e41ec07-b5a3-f393-e0a9-e50e24dcca9e"

SAMPLE_RATE = 16000
CHANNELS = 2


async def record(addr: str, output_dir: str, species: str, duration: int):
    from bleak import BleakClient

    output_path = Path(output_dir) / species
    output_path.mkdir(parents=True, exist_ok=True)

    # Find next file number
    existing = list(output_path.glob(f"{species}_*.npy"))
    file_num = len(existing) + 1
    out_file = output_path / f"{species}_{file_num:03d}.npy"

    print(f"Connecting to {addr} ...")
    async with BleakClient(addr, timeout=15.0) as client:
        print(f"Connected. RSSI: {await client.get_rssi()}")

        # Read device info
        info = await client.read_gatt_char(CHR_DEVICE_INFO)
        fw_ver = info[0] if len(info) > 0 else 0
        print(f"Device firmware: {fw_ver}")

        # Audio buffer
        frames = []
        total_samples = 0
        target_samples = SAMPLE_RATE * duration * CHANNELS

        def audio_handler(sender, data: bytearray):
            nonlocal total_samples
            if len(data) < 4:
                return
            frame_idx, count = struct.unpack_from("<HH", data, 0)
            samples = np.frombuffer(data, dtype="<i2", count=count, offset=4)
            frames.append(samples.copy())
            total_samples += len(samples)

        # Subscribe to audio stream
        await client.start_notify(CHR_AUDIO_STREAM, audio_handler)

        # Send "start stream" command
        await client.write_gatt_char(CHR_COMMAND, bytes([0x10, 0x01]))
        print(f"Recording {duration}s of audio → {out_file}")

        # Wait for the specified duration
        start = time.time()
        while time.time() - start < duration:
            elapsed = time.time() - start
            print(f"\r  Recording: {elapsed:.0f}/{duration}s "
                  f"({total_samples} samples)", end="", flush=True)
            await asyncio.sleep(0.5)

        # Send "stop stream" command
        await client.write_gatt_char(CHR_COMMAND, bytes([0x11, 0x01]))
        await client.stop_notify(CHR_AUDIO_STREAM)

    # Concatenate and save
    if frames:
        all_samples = np.concatenate(frames)
        # Reshape to (N, 2) — interleaved stereo
        n_complete = len(all_samples) // 2 * 2
        audio_stereo = all_samples[:n_complete].reshape(-1, 2)
        np.save(out_file, audio_stereo)
        print(f"\nSaved {len(audio_stereo)} frames to {out_file}")
    else:
        print("\nNo audio received!")


def main():
    parser = argparse.ArgumentParser(description='Record wingbeats from Echo Trap')
    parser.add_argument('--addr', required=True, help='BLE address')
    parser.add_argument('--output', default='dataset/', help='Output directory')
    parser.add_argument('--species', required=True, help='Species name')
    parser.add_argument('--duration', type=int, default=60,
                        help='Recording duration in seconds')
    args = parser.parse_args()

    asyncio.run(record(args.addr, args.output, args.species, args.duration))


if __name__ == '__main__':
    main()