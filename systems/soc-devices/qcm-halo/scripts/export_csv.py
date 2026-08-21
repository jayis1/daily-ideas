#!/usr/bin/env python3
"""
export_csv.py — Export QCM Halo SD card logs to analysis-ready CSV

Reads the raw binary/CSV logs from the SD card and produces
clean, analysis-ready CSV files for spreadsheets or further processing.

Usage:
    python3 export_csv.py <input.csv> [--output output.csv]
    python3 export_csv.py <input.bin> [--binary] [--output output.csv]
"""

import csv
import sys
import argparse
import struct
from datetime import datetime

def export_csv_file(input_file, output_file):
    """Convert QCM Halo CSV log to a clean analysis CSV."""
    with open(input_file, 'r') as infile:
        lines = infile.readlines()

    rows = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            # Check for metadata
            if 'T=' in line:
                temp = line.split('T=')[1].split()[0] if 'T=' in line else ''
            continue

        parts = line.split(',')
        if len(parts) >= 10:
            # Single result CSV: timestamp,ch,ov_n,freq,delta_f,dissipation,delta_d,temp,mass,thickness
            try:
                rows.append({
                    'timestamp': parts[0],
                    'channel': parts[1],
                    'overtone': parts[2],
                    'frequency_hz': parts[3],
                    'delta_f_hz': parts[4],
                    'dissipation': parts[5],
                    'delta_d': parts[6],
                    'temperature_c': parts[7],
                    'sauerbrey_mass_ng_cm2': parts[8],
                    'sauerbrey_thickness_nm': parts[9],
                })
            except (IndexError, ValueError):
                continue

    if not rows:
        print("No valid data rows found!")
        return

    with open(output_file, 'w', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} rows to {output_file}")

def export_binary_file(input_file, output_file):
    """Convert QCM Halo binary log to CSV."""
    with open(input_file, 'rb') as f:
        data = f.read()

    rows = []
    offset = 0
    record_size = 26  # result packet size

    while offset + record_size <= len(data):
        # Parse 26-byte result record
        ch = data[offset]
        ov_n = data[offset + 1]
        delta_f = struct.unpack_from('<f', data, offset + 2)[0]
        dissipation = struct.unpack_from('<f', data, offset + 6)[0]
        delta_d = struct.unpack_from('<f', data, offset + 10)[0]
        temp = struct.unpack_from('<f', data, offset + 14)[0]
        mass = struct.unpack_from('<f', data, offset + 18)[0]
        ts = struct.unpack_from('<I', data, offset + 22)[0]

        rows.append({
            'timestamp_ms': ts,
            'channel': ch,
            'overtone': ov_n,
            'delta_f_hz': f'{delta_f:.3f}',
            'dissipation': f'{dissipation:.6e}',
            'delta_d': f'{delta_d:.6e}',
            'temperature_c': f'{temp:.2f}',
            'sauerbrey_mass_ng_cm2': f'{mass:.2f}',
        })
        offset += record_size

    if not rows:
        print("No valid records found in binary file!")
        return

    with open(output_file, 'w', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} records to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Export QCM Halo logs to CSV')
    parser.add_argument('input', help='Input file (CSV or binary)')
    parser.add_argument('--output', '-o', help='Output CSV file')
    parser.add_argument('--binary', '-b', action='store_true', help='Input is binary format')
    args = parser.parse_args()

    output = args.output or args.input.rsplit('.', 1)[0] + '_export.csv'

    if args.binary:
        export_binary_file(args.input, output)
    else:
        export_csv_file(args.input, output)

if __name__ == "__main__":
    main()