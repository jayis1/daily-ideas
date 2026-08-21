#!/usr/bin/env python3
"""
read_results.py — Read and plot Phyto Pulse session data from SD card.

Reads RAW_xxxx.BIN (binary) and EVENTS_xxxx.CSV, plots the waveform
with detected events marked.

Usage:
    python3 read_results.py /path/to/RAW_0001.BIN /path/to/EVENTS_0001.CSV
"""

import struct
import sys
import csv
from pathlib import Path

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


def read_raw_file(filepath):
    """Read a Phyto Pulse raw binary file."""
    with open(filepath, 'rb') as f:
        # Read 16-byte header
        header = f.read(16)
        magic = header[:4]
        if magic != b'PHYT':
            raise ValueError(f"Bad magic: {magic}")
        version, = struct.unpack_from('<H', header, 4)
        sample_rate, = struct.unpack_from('<H', header, 6)
        ina_gain_x100, = struct.unpack_from('<H', header, 8)
        pga = header[10]
        start_ts, = struct.unpack_from('<I', header, 12)

        print(f"Version: {version}, Rate: {sample_rate} Hz, "
              f"INA gain: {ina_gain_x100/100:.0f}x, PGA: {pga}")

        # Read samples: 6 bytes each (2B voltage int16 + 4B timestamp uint32)
        samples = []
        timestamps = []
        while True:
            rec = f.read(6)
            if len(rec) < 6:
                break
            v_scaled, ts = struct.unpack('<hI', rec)
            v_mv = v_scaled / 100.0  # mV
            samples.append(v_mv)
            timestamps.append(ts / 1000.0)  # seconds

    return timestamps, samples, sample_rate


def read_events_csv(filepath):
    """Read the events CSV file."""
    events = []
    with open(filepath, 'r') as f:
        # Skip comment lines (SWP results)
        reader = csv.DictReader(f)
        for row in reader:
            try:
                events.append({
                    'timestamp_ms': float(row['timestamp_ms']),
                    'amp_mV': float(row['amp_mV']),
                    'duration_ms': float(row['duration_ms']),
                    'class': row['class'],
                    'confidence': float(row['confidence']),
                })
            except (ValueError, KeyError):
                continue
    return events


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 read_results.py <RAW_xxxx.BIN> [EVENTS_xxxx.CSV]")
        sys.exit(1)

    raw_path = sys.argv[1]
    csv_path = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Reading {raw_path}...")
    times, volts, rate = read_raw_file(raw_path)
    print(f"  {len(volts)} samples, {len(volts)/rate:.1f} s duration")

    events = []
    if csv_path and Path(csv_path).exists():
        print(f"Reading {csv_path}...")
        events = read_events_csv(csv_path)
        print(f"  {len(events)} events detected")
        ap_count = sum(1 for e in events if e['class'] == 'AP')
        vp_count = sum(1 for e in events if e['class'] == 'VP')
        art_count = sum(1 for e in events if e['class'] == 'ART')
        print(f"  AP: {ap_count}, VP: {vp_count}, Artifact: {art_count}")

    if HAS_MPL:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

        # Plot waveform
        ax1.plot(times, volts, linewidth=0.3, color='blue')
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Voltage (mV)')
        ax1.set_title('Phyto Pulse Recording')
        ax1.grid(True, alpha=0.3)

        # Mark events
        for ev in events:
            t = ev['timestamp_ms'] / 1000.0
            color = {'AP': 'red', 'VP': 'orange', 'ART': 'gray'}[ev['class']]
            ax1.axvline(t, color=color, alpha=0.5, linestyle='--')
            ax1.annotate(f"{ev['class']}\n{ev['amp_mV']:.1f}mV",
                        xy=(t, ev['amp_mV']), fontsize=7, color=color)

        # Plot event amplitude histogram
        if events:
            amps = [e['amp_mV'] for e in events]
            ax2.hist(amps, bins=30, color='green', alpha=0.7)
            ax2.set_xlabel('Amplitude (mV)')
            ax2.set_ylabel('Count')
            ax2.set_title('Event Amplitude Distribution')
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('phyto_pulse_session.png', dpi=150)
        print(f"Plot saved to phyto_pulse_session.png")
        plt.show()
    else:
        # Text summary only
        print("\n=== Session Summary ===")
        print(f"Duration: {len(volts)/rate:.1f} s")
        print(f"Mean: {sum(volts)/len(volts):.3f} mV")
        print(f"Min: {min(volts):.3f} mV, Max: {max(volts):.3f} mV")
        if events:
            print(f"Events: {len(events)} ({sum(1 for e in events if e['class']=='AP')} AP, "
                  f"{sum(1 for e in events if e['class']=='VP')} VP)")


if __name__ == '__main__':
    main()