#!/usr/bin/env python3
"""
calibrate.py — Calibration helper for Phyto Pulse

Performs:
1. Electrode offset measurement (differential DC offset between electrodes)
2. Noise floor measurement (short the inputs, measure RMS noise)
3. Gain verification (apply known test signal, verify gain)

Connects via Wi-Fi WebSocket to the live device.

Usage:
    python3 calibrate.py [--ip 192.168.4.1] [--mode noise|offset|gain]

Requirements:
    pip install websocket-client numpy
"""

import argparse
import json
import time
import threading
from collections import deque
import sys

try:
    import websocket
    HAS_WS = True
except ImportError:
    HAS_WS = False

try:
    import numpy as np
    HAS_NP = True
except ImportError:
    HAS_NP = False


class CalibrationStream:
    def __init__(self, ip='192.168.4.1'):
        self.ip = ip
        self.ws = None
        self.connected = False
        self.samples = deque(maxlen=10000)
        self.lock = threading.Lock()

    def connect(self):
        url = f"ws://{self.ip}/ws"
        try:
            self.ws = websocket.WebSocketApp(
                url,
                on_message=self.on_message,
                on_open=self.on_open,
                on_error=self.on_error,
                on_close=self.on_close,
            )
            self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.thread.start()
            time.sleep(2)
            return self.connected
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def on_open(self, ws):
        self.connected = True

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            if data.get('type') == 'sample' or data.get('t') == 's':
                v = data.get('v', 0)
                with self.lock:
                    self.samples.append(v)
        except json.JSONDecodeError:
            pass

    def on_error(self, ws, error):
        self.connected = False

    def on_close(self, ws, *args):
        self.connected = False

    def get_samples(self):
        with self.lock:
            return list(self.samples)


def measure_noise(stream, duration_s=10):
    """Measure noise floor: short both electrode inputs to a common reference.
    Collects samples and computes RMS + peak-to-peak."""
    print(f"\n=== Noise Floor Measurement ({duration_s}s) ===")
    print("Short both BNC inputs to GND (or connect both electrodes to same point).")
    print("Press Enter when ready...")
    input()

    print(f"Collecting {duration_s}s of samples...")
    start_len = len(stream.get_samples())
    time.sleep(duration_s)
    samples = stream.get_samples()[start_len:]

    if not samples:
        print("No samples received!")
        return

    if HAS_NP:
        arr = np.array(samples)
        rms = np.sqrt(np.mean(arr**2))
        pp = np.max(arr) - np.min(arr)
        mean = np.mean(arr)
        std = np.std(arr)
    else:
        rms = (sum(s**2 for s in samples) / len(samples)) ** 0.5
        pp = max(samples) - min(samples)
        mean = sum(samples) / len(samples)
        std = (sum((s - mean)**2 for s in samples) / len(samples)) ** 0.5

    print(f"\nResults:")
    print(f"  Samples:    {len(samples)}")
    print(f"  Mean:       {mean:.4f} mV")
    print(f"  RMS:        {rms:.4f} mV")
    print(f"  Std (σ):    {std:.4f} mV")
    print(f"  Peak-peak:  {pp:.4f} mV")
    print(f"\n  Minimum detectable signal (3σ): {3*std:.4f} mV")
    print(f"  Threshold (μ + 5σ):              {mean + 5*std:.4f} mV")

    if rms < 0.005:
        print("  ✓ PASS: noise < 5 µVrms (excellent)")
    elif rms < 0.020:
        print("  ✓ GOOD: noise < 20 µVrms")
    elif rms < 0.100:
        print("  ⚠ FAIR: noise 20-100 µVrms (check electrode contact)")
    else:
        print("  ✗ POOR: noise > 100 µVrms (check shielding, electrode gel)")


def measure_offset(stream, duration_s=5):
    """Measure electrode DC offset: place both electrodes in same KCl bath."""
    print(f"\n=== Electrode Offset Measurement ({duration_s}s) ===")
    print("Place both electrodes in the same 0.1 M KCl bath (or on same plant region).")
    print("Press Enter when ready...")
    input()

    print(f"Collecting {duration_s}s of samples...")
    start_len = len(stream.get_samples())
    time.sleep(duration_s)
    samples = stream.get_samples()[start_len:]

    if not samples:
        print("No samples received!")
        return

    if HAS_NP:
        arr = np.array(samples)
        mean = np.mean(arr)
        drift = np.max(arr) - np.min(arr)
    else:
        mean = sum(samples) / len(samples)
        drift = max(samples) - min(samples)

    print(f"\nResults:")
    print(f"  Mean offset:  {mean:.3f} mV")
    print(f"  Drift (pp):   {drift:.3f} mV")

    if abs(mean) < 5:
        print("  ✓ PASS: offset < 5 mV (electrodes well-matched)")
    elif abs(mean) < 20:
        print("  ⚠ FAIR: offset 5-20 mV (electrodes need conditioning)")
    else:
        print("  ✗ POOR: offset > 20 mV (re-condition Ag/AgCl pellets)")
    print(f"  Drift {'✓' if drift < 2 else '⚠'}: {'< 2 mV (stable)' if drift < 2 else f'{drift:.1f} mV (wait longer for stabilization)'}")


def verify_gain(stream, duration_s=5):
    """Verify gain: apply a known test signal and check the measured amplitude."""
    print(f"\n=== Gain Verification ({duration_s}s) ===")
    print("Apply a known signal to the electrode inputs:")
    print("  e.g., 10 mV from a signal generator, or touch a 1.5V battery briefly")
    print("Enter the expected signal amplitude (mV):")
    try:
        expected = float(input("  Expected amplitude (mV): "))
    except ValueError:
        print("Invalid input.")
        return

    print(f"Collecting {duration_s}s...")
    start_len = len(stream.get_samples())
    time.sleep(duration_s)
    samples = stream.get_samples()[start_len:]

    if not samples:
        print("No samples received!")
        return

    if HAS_NP:
        arr = np.array(samples)
        peak = np.max(np.abs(arr))
    else:
        peak = max(abs(s) for s in samples)

    ratio = peak / expected if expected > 0 else 0
    print(f"\nResults:")
    print(f"  Expected:    {expected:.2f} mV")
    print(f"  Measured:    {peak:.2f} mV")
    print(f"  Ratio:       {ratio:.3f}")

    if 0.9 <= ratio <= 1.1:
        print("  ✓ PASS: gain within ±10%")
    elif 0.8 <= ratio <= 1.2:
        print("  ⚠ FAIR: gain within ±20%")
    else:
        print("  ✗ FAIL: gain error > 20% — check INA333 gain setting")


def main():
    parser = argparse.ArgumentParser(description='Phyto Pulse calibration')
    parser.add_argument('--ip', default='192.168.4.1')
    parser.add_argument('--mode', choices=['noise', 'offset', 'gain', 'all'],
                        default='all')
    args = parser.parse_args()

    if not HAS_WS:
        print("websocket-client not installed. Install with: pip install websocket-client")
        sys.exit(1)

    print("Phyto Pulse Calibration Tool")
    print(f"Connecting to {args.ip}...")

    stream = CalibrationStream(args.ip)
    if not stream.connect():
        print("Failed to connect. Connect to PhytoPulse-XXXX Wi-Fi AP first.")
        sys.exit(1)

    print("Connected! Start a recording on the device before calibrating.\n")

    if args.mode in ('noise', 'all'):
        measure_noise(stream)
    if args.mode in ('offset', 'all'):
        measure_offset(stream)
    if args.mode in ('gain', 'all'):
        verify_gain(stream)

    print("\nCalibration complete.")


if __name__ == '__main__':
    main()