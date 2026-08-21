#!/usr/bin/env python3
"""
Spectra Charm — Companion Script: Spectrum Viewer & Analysis

Usage:
    python3 spectra_viewer.py [--port /dev/ttyUSB0] [--ble] [--wifi 192.168.4.1]

Reads spectrum data from the Spectra Charm device (via serial, BLE, or WiFi)
and displays it in an interactive matplotlib plot.

Requirements:
    pip install matplotlib numpy requests pyserial

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import struct
import sys
import time
import numpy as np

try:
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Button
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# Constants
WAVELENGTH_START = 340.0  # nm
WAVELENGTH_END = 700.0    # nm
SPECTRUM_POINTS = 128

# UART protocol constants
SYNC1 = 0xA5
SYNC2 = 0x5A
CMD_SCAN_REQUEST = 0x01
CMD_SCAN_RESULT = 0x81


def wavelength_array():
    """Generate wavelength axis for spectrum."""
    return np.linspace(WAVELENGTH_START, WAVELENGTH_END, SPECTRUM_POINTS)


def read_spectrum_wifi(host):
    """Read spectrum from WiFi REST API."""
    if not HAS_REQUESTS:
        print("ERROR: 'requests' package required for WiFi mode. pip install requests")
        return None

    # Trigger scan
    try:
        r = requests.post(f"http://{host}/api/v1/scan", json={"type": 2}, timeout=30)
        print(f"Scan triggered: {r.json()}")
    except Exception as e:
        print(f"Error triggering scan: {e}")
        return None

    # Wait for scan to complete
    time.sleep(4)

    # Fetch spectrum
    try:
        r = requests.get(f"http://{host}/api/v1/spectrum", timeout=10)
        data = r.json()
        absorbance = np.array(data["absorbance"])
        return absorbance
    except Exception as e:
        print(f"Error reading spectrum: {e}")
        return None


def read_match_wifi(host):
    """Read compound match from WiFi REST API."""
    if not HAS_REQUESTS:
        return None

    try:
        r = requests.get(f"http://{host}/api/v1/match", timeout=10)
        return r.json()
    except Exception:
        return None


def crc8(data):
    """Calculate CRC-8 over byte array."""
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def build_scan_request(scan_type=2, gain=9, integration=29):
    """Build UART scan request packet."""
    pkt = bytearray()
    pkt.append(SYNC1)
    pkt.append(SYNC2)
    pkt.append(0x00)  # len high
    pkt.append(0x03)  # len low
    pkt.append(CMD_SCAN_REQUEST)
    pkt.append(scan_type)
    pkt.append(gain)
    pkt.append((integration >> 8) & 0xFF)
    pkt.append(integration & 0xFF)
    crc = crc8(pkt[4:])
    pkt.append(crc)
    return bytes(pkt)


def parse_scan_result(data):
    """Parse SCAN_RESULT packet from STM32."""
    if len(data) < 5:
        return None

    if data[0] != SYNC1 or data[1] != SYNC2:
        return None

    payload_len = (data[2] << 8) | data[3]
    cmd = data[4]

    if cmd != CMD_SCAN_RESULT:
        return None

    # Parse payload
    idx = 5
    status = data[idx]; idx += 1
    scan_number = (data[idx] << 8) | data[idx + 1]; idx += 2
    num_peaks = data[idx]; idx += 1

    # Parse peaks
    peaks = []
    for _ in range(min(num_peaks, 16)):
        wl = struct.unpack_from('<f', data, idx)[0]; idx += 4
        ab = struct.unpack_from('<f', data, idx)[0]; idx += 4
        peaks.append((wl, ab))

    # Parse match
    compound_id = data[idx]; idx += 1
    confidence = struct.unpack_from('<f', data, idx)[0]; idx += 4
    concentration = struct.unpack_from('<f', data, idx)[0]; idx += 4
    name = data[idx:idx+32].split(b'\x00')[0].decode('utf-8', errors='replace')

    return {
        'status': status,
        'scan_number': scan_number,
        'num_peaks': num_peaks,
        'peaks': peaks,
        'compound_id': compound_id,
        'confidence': confidence,
        'concentration': concentration,
        'name': name,
    }


def read_spectrum_serial(port, baud=115200):
    """Read spectrum from UART serial connection."""
    if not HAS_SERIAL:
        print("ERROR: 'pyserial' package required for serial mode. pip install pyserial")
        return None, None

    try:
        ser = serial.Serial(port, baud, timeout=5)
    except Exception as e:
        print(f"Error opening serial port: {e}")
        return None, None

    # Send scan request
    pkt = build_scan_request(scan_type=2)
    ser.write(pkt)
    print("Scan request sent via UART")

    # Wait for response
    time.sleep(4)

    # Read response
    data = ser.read(2048)
    ser.close()

    if len(data) < 10:
        print("Insufficient data received")
        return None, None

    result = parse_scan_result(data)
    if result is None:
        print("Failed to parse scan result")
        return None, None

    # Reconstruct spectrum from peaks (approximate)
    # In real implementation, the full 128-point spectrum is included
    wavelengths = wavelength_array()
    absorbance = np.zeros(SPECTRUM_POINTS)

    for wl, ab in result['peaks']:
        idx = int((wl - WAVELENGTH_START) / (WAVELENGTH_END - WAVELENGTH_START) * (SPECTRUM_POINTS - 1))
        if 0 <= idx < SPECTRUM_POINTS:
            absorbance[idx] = ab

    return absorbance, result


def plot_spectrum(absorbance, match_info=None, title="Spectra Charm — Absorbance Spectrum"):
    """Plot spectrum with matplotlib."""
    if not HAS_MATPLOTLIB:
        print("ERROR: 'matplotlib' required for plotting. pip install matplotlib")
        print(f"Absorbance data: {absorbance}")
        return

    wavelengths = wavelength_array()

    fig, ax = plt.subplots(1, 1, figsize=(10, 5))
    ax.plot(wavelengths, absorbance, 'b-', linewidth=1.5, label='Absorbance')
    ax.fill_between(wavelengths, absorbance, alpha=0.15, color='blue')

    ax.set_xlabel('Wavelength (nm)')
    ax.set_ylabel('Absorbance (AU)')
    ax.set_title(title)
    ax.set_xlim(WAVELENGTH_START, WAVELENGTH_END)
    ax.set_ylim(0, max(absorbance.max() * 1.1, 0.1))
    ax.grid(True, alpha=0.3)

    # Add visible wavelength color bands
    color_bands = [
        (380, 440, '#8B00FF', 0.05),  # Violet
        (440, 490, '#0000FF', 0.05),  # Blue
        (490, 510, '#00FF00', 0.05),  # Cyan/Green
        (510, 580, '#FFFF00', 0.05),  # Yellow
        (580, 620, '#FF7F00', 0.05),  # Orange
        (620, 700, '#FF0000', 0.05),  # Red
    ]
    for wl_lo, wl_hi, color, alpha in color_bands:
        ax.axvspan(wl_lo, wl_hi, alpha=alpha, color=color)

    # Show match info
    if match_info:
        compound = match_info.get('name', match_info.get('compound', 'Unknown'))
        confidence = match_info.get('confidence', 0)
        concentration = match_info.get('concentration_mol_L', match_info.get('concentration', 0))

        info_text = f"Match: {compound}\nConfidence: {confidence:.1%}\nConcentration: {concentration:.4e} M"
        ax.text(0.98, 0.98, info_text, transform=ax.transAxes,
                fontsize=9, verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.show()


def export_csv(absorbance, filename="spectrum.csv"):
    """Export spectrum to CSV file."""
    wavelengths = wavelength_array()
    with open(filename, 'w') as f:
        f.write("wavelength_nm,absorbance_AU\n")
        for wl, ab in zip(wavelengths, absorbance):
            f.write(f"{wl:.1f},{ab:.6f}\n")
    print(f"Spectrum exported to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Spectra Charm Spectrum Viewer")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port")
    parser.add_argument("--ble", action="store_true", help="Use BLE connection")
    parser.add_argument("--wifi", default=None, help="WiFi AP IP address")
    parser.add_argument("--export", default=None, help="Export to CSV file")
    parser.add_argument("--no-plot", action="store_true", help="Don't show plot")
    args = parser.parse_args()

    absorbance = None
    match_info = None

    if args.wifi:
        print(f"Connecting via WiFi to {args.wifi}...")
        absorbance = read_spectrum_wifi(args.wifi)
        match_info = read_match_wifi(args.wifi)
    elif args.ble:
        print("BLE mode not yet implemented. Use --wifi or --port.")
        sys.exit(1)
    else:
        print(f"Connecting via serial to {args.port}...")
        absorbance, match_info = read_spectrum_serial(args.port)

    if absorbance is None:
        print("Failed to read spectrum")
        sys.exit(1)

    print(f"Spectrum read: {len(absorbance)} points")
    print(f"Peak absorbance: {absorbance.max():.4f} AU at {wavelength_array()[np.argmax(absorbance)]:.0f} nm")

    if match_info:
        print(f"Compound match: {match_info}")

    if args.export:
        export_csv(absorbance, args.export)

    if not args.no_plot:
        plot_spectrum(absorbance, match_info)


if __name__ == "__main__":
    main()