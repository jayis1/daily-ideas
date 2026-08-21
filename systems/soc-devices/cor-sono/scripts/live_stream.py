#!/usr/bin/env python3
"""
Cor Sono — live_stream.py
Connects to Cor Sono via BLE, displays live waveform + classification results.

Usage:
    python3 live_stream.py [--mac AA:BB:CC:DD:EE:FF]

Requires: bleak, matplotlib
"""
import argparse
import asyncio
import struct
from collections import deque

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install: pip install bleak matplotlib")
    raise

SVC_UUID = "00009201-1212-efde-1523-785feabcd123"
CHR_AUDIO = "00009202-1212-efde-1523-785feabcd123"
CHR_RESULT = "00009203-1212-efde-1523-785feabcd123"
CHR_CMD = "00009204-1212-efde-1523-785feabcd123"

CLASS_NAMES = [
    "Normal", "S3 gallop", "S4 gallop", "Sys murmur",
    "Dia murmur", "Crackles", "Wheeze", "Pleural rub"
]

audio_buf = deque(maxlen=4000)
results = {"hr": 0, "class": "---", "conf": 0}


def on_audio(sender, data):
    """80 samples × 2 ch × int16 = 320 bytes"""
    n = len(data) // 4
    for i in range(n):
        ch0, ch1 = struct.unpack_from("<hh", data, i * 4)
        audio_buf.append(ch0)


def on_result(sender, data):
    """class_u8, confidence_u8, hr_u16_le"""
    global results
    if len(data) >= 4:
        cls_id, conf, hr_lo, hr_hi = struct.unpack("<BBH", data[:4])
        hr = hr_lo | (hr_hi << 8)
        results = {
            "hr": hr,
            "class": CLASS_NAMES[cls_id] if cls_id < 8 else "Unknown",
            "conf": conf,
        }


async def main(mac):
    print("Scanning for Cor Sono...")
    if mac is None:
        devices = await BleakScanner.discover(timeout=10)
        for d in devices:
            if "Cor Sono" in (d.name or ""):
                mac = d.address
                break
        if mac is None:
            print("Cor Sono not found. Pass MAC address explicitly.")
            return

    print(f"Connecting to {mac}...")
    async with BleakClient(mac) as client:
        print(f"Connected: {client.is_connected}")
        await client.start_notify(CHR_AUDIO, on_audio)
        await client.start_notify(CHR_RESULT, on_result)
        print("Streaming. Press Ctrl+C to stop.")

        try:
            import matplotlib.pyplot as plt
            import matplotlib.animation as animation

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
            line, = ax1.plot([], [], "g-", lw=0.5)
            text = ax2.text(0.1, 0.5, "", fontsize=20, family="monospace")
            ax1.set_title("Cor Sono — Live PCG Waveform")
            ax1.set_xlabel("Samples")
            ax1.set_ylabel("Amplitude")
            ax1.set_xlim(0, 4000)
            ax1.set_ylim(-32768, 32768)
            ax2.axis("off")
            ax2.set_title("Classification Result")

            def update(frame):
                if audio_buf:
                    line.set_data(range(len(audio_buf)), list(audio_buf))
                text.set_text(
                    f"  HR: {results['hr']} BPM\n"
                    f"  Class: {results['class']}\n"
                    f"  Confidence: {results['conf']}%"
                )
                return line, text

            ani = animation.FuncAnimation(fig, update, interval=100, blit=False)
            plt.show()
        except ImportError:
            print("matplotlib not available; text-only mode")
            while True:
                await asyncio.sleep(1)
                print(f"HR={results['hr']} Class={results['class']} Conf={results['conf']}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mac", default=None, help="BLE MAC address")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.mac))
    except KeyboardInterrupt:
        print("\nStopped.")