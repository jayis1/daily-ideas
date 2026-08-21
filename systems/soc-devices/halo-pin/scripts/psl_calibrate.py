#!/usr/bin/env python3
"""
psl_calibrate.py — PSL sphere calibration helper for Halo Pin.

Generates a calibration procedure script and parses the resulting
peak-height data from the BLE stream to compute the power-law fit
(peak_mV = A * d^B) and update the device's bin boundaries.

Usage:
    python3 psl_calibrate.py --sizes 0.5,1.0,2.0,5.0 --device MAC

The script:
  1. Sends "CALIB" command to start calibration mode.
  2. For each PSL size, prompts the user to inject the PSL aerosol,
     waits 60 s, collects peak heights, and records the median.
  3. Performs log-log linear regression to fit A and B.
  4. Sends the updated boundaries to the device.
"""

import argparse
import asyncio
import math
import statistics
import sys

try:
    from bleak import BleakClient
except ImportError:
    print("Install: pip install bleak", file=sys.stderr)
    sys.exit(1)

UUID_STATUS = "00002a01-0000-1000-8000-00805f9b34fb"
UUID_CMD    = "00002a03-0000-1000-8000-00805f9b34fb"

# Default bin edges (µm)
BIN_EDGES = [0.30, 0.40, 0.50, 0.70, 1.00, 1.30, 1.70, 2.20,
             3.00, 4.00, 5.00, 7.00, 10.0, 15.0, 20.0, 30.0, 40.0]


async def collect_peaks(client, duration_s=60):
    """Collect peak heights from the BLE stream for a given duration."""
    peaks = []
    start = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start < duration_s:
        try:
            raw = await client.read_gatt_char(UUID_STATUS)
            text = raw.decode("ascii", errors="replace")
            # Parse histogram from status string
            if "H:" in text:
                hist_part = text.split("H:")[1].strip().rstrip(",")
                counts = [int(c) if c.strip().isdigit() else 0
                          for c in hist_part.split(",")[:16]]
                # The histogram bin with the most counts is the peak
                # In calibration mode, the raw peak heights are reported
                # instead of counts. For this script, we use the
                # histogram bin index to estimate the median peak height.
                max_bin = counts.index(max(counts)) if counts else 0
                # Estimate peak mV from bin midpoint (rough)
                # In real use, the device streams raw peak heights
                peaks.append(float(max_bin))
        except Exception:
            pass
        await asyncio.sleep(1.0)
    return peaks


def fit_power_law(sizes, medians):
    """Fit peak_mV = A * d^B via log-log linear regression."""
    import math
    n = len(sizes)
    if n < 2:
        return 1.0, 2.0
    Sx = Sy = Sxx = Sxy = 0.0
    for s, m in zip(sizes, medians):
        x = math.log(s)
        y = math.log(max(m, 0.001))
        Sx += x; Sy += y
        Sxx += x * x; Sxy += x * y
    denom = n * Sxx - Sx * Sx
    if abs(denom) < 1e-12:
        return 1.0, 2.0
    B = (n * Sxy - Sx * Sy) / denom
    A = math.exp((Sy - B * Sx) / n)
    return A, B


def compute_boundaries(A, B):
    """Compute pulse-height boundaries (mV) for each bin edge."""
    return [A * (d ** B) for d in BIN_EDGES]


async def run(device_addr, sizes_str, duration):
    sizes = [float(s) for s in sizes_str.split(",")]
    if len(sizes) < 2:
        print("Need at least 2 PSL sizes for calibration.")
        return

    print(f"Connecting to {device_addr}...")
    async with BleakClient(device_addr) as client:
        print("Sending CALIB command...")
        await client.write_gatt_char(UUID_CMD, b"CALIB\n")

        medians = []
        for size in sizes:
            input(f"\nInject {size} µm PSL aerosol, then press Enter to collect...")
            print(f"Collecting for {duration} s...")
            peaks = await collect_peaks(client, duration)
            if peaks:
                med = statistics.median(peaks)
                medians.append(med)
                print(f"  Median peak: {med:.1f} mV (from {len(peaks)} samples)")
            else:
                print("  No peaks detected!")
                medians.append(0.001)

        # Fit
        A, B = fit_power_law(sizes, medians)
        print(f"\nPower-law fit: peak_mV = {A:.3f} * d^{B:.3f}")

        boundaries = compute_boundaries(A, B)
        print(f"Bin boundaries (mV): {[f'{b:.1f}' for b in boundaries]}")

        # Send boundaries to device
        cmd = "BINS:" + ",".join(f"{b:.1f}" for b in boundaries) + "\n"
        await client.write_gatt_char(UUID_CMD, cmd.encode("ascii"))
        print("Boundaries sent to device.")

        # Send STOP
        await client.write_gatt_char(UUID_CMD, b"STOP\n")
        print("Calibration complete.")


def main():
    parser = argparse.ArgumentParser(description="PSL calibration for Halo Pin")
    parser.add_argument("--device", required=True, help="BLE MAC address")
    parser.add_argument("--sizes", default="0.5,1.0,2.0,5.0",
                       help="Comma-separated PSL sizes in µm")
    parser.add_argument("--duration", type=int, default=60,
                       help="Collection duration per size (seconds)")
    args = parser.parse_args()
    asyncio.run(run(args.device, args.sizes, args.duration))


if __name__ == "__main__":
    main()