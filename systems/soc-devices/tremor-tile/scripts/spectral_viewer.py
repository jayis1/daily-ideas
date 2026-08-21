#!/usr/bin/env python3
"""
Tremor Tile — Real-Time Spectral Viewer
Connects via USB-C and displays live FFT spectrum and vibration data.

Usage:
    python3 spectral_viewer.py --port /dev/ttyACM0

Requires:
    pip install pyserial numpy matplotlib
"""

import argparse
import struct
import sys
import time
import threading

try:
    import serial
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    from matplotlib.gridspec import GridSpec
except ImportError as e:
    print(f"Error: Missing dependency: {e}")
    print("Install with: pip install pyserial numpy matplotlib")
    sys.exit(1)

# Frequency bands
BAND_BOUNDARIES = [0.1, 10, 50, 200, 500, 1500]
BAND_COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
BAND_NAMES = ['0.1-10Hz', '10-50Hz', '50-200Hz', '200-500Hz', '500-1500Hz']

# Global data buffers
fft_magnitude = np.zeros(512)
peak_freqs = np.zeros(5)
band_energies = np.zeros(5)
rms_history = []
kurtosis_history = []
timestamp_history = []
data_lock = threading.Lock()
running = True

SAMPLE_RATE = 400  # Hz (must match device config)
FFT_SIZE = 1024
FREQ_RESOLUTION = SAMPLE_RATE / FFT_SIZE


def parse_serial_data(ser):
    """Read and parse data from serial port."""
    global fft_magnitude, peak_freqs, band_energies

    while running:
        try:
            # Read packet header: 0xAA, 0x55, type, length
            header = ser.read(4)
            if len(header) < 4:
                continue

            if header[0] != 0xAA or header[1] != 0x55:
                continue

            pkt_type = header[2]
            pkt_len = header[3]

            if pkt_len > 0:
                data = ser.read(pkt_len)
            else:
                data = b""

            with data_lock:
                if pkt_type == 0x10:  # FFT spectrum data
                    # 512 float values (magnitude spectrum)
                    if len(data) >= 512 * 4:
                        fft_magnitude = np.frombuffer(data[:512*4], dtype='<f4')
                        peak_freqs = np.frombuffer(data[512*4:512*4+5*8], dtype='<f4')
                        # Peak frequencies (5 floats) then amplitudes (5 floats)
                        # Then band energies (5 floats)
                        offset = 512*4 + 5*8
                        if len(data) >= offset + 5*4:
                            band_energies = np.frombuffer(
                                data[offset:offset+5*4], dtype='<f4')

                elif pkt_type == 0x11:  # Time series data (RMS, kurtosis)
                    if len(data) >= 8:
                        rms = struct.unpack('<f', data[0:4])[0]
                        kurt = struct.unpack('<f', data[4:8])[0]
                        now = time.time()
                        rms_history.append(rms)
                        kurtosis_history.append(kurt)
                        timestamp_history.append(now)

                        # Keep only last 1000 points
                        if len(rms_history) > 1000:
                            rms_history.pop(0)
                            kurtosis_history.pop(0)
                            timestamp_history.pop(0)

        except Exception as e:
            print(f"Serial error: {e}")
            time.sleep(0.1)


def create_figure():
    """Create the matplotlib figure with subplots."""
    fig = plt.figure(figsize=(14, 9))
    fig.suptitle('Tremor Tile — Live Spectral Viewer', fontsize=14, fontweight='bold')

    gs = GridSpec(3, 2, figure=fig, hspace=0.35, wspace=0.3)

    # Top: Full FFT spectrum
    ax_fft = fig.add_subplot(gs[0, :])

    # Middle left: Band energy bars
    ax_bands = fig.add_subplot(gs[1, 0])

    # Middle right: Peak frequency markers
    ax_peaks = fig.add_subplot(gs[1, 1])

    # Bottom left: RMS history
    ax_rms = fig.add_subplot(gs[2, 0])

    # Bottom right: Kurtosis history
    ax_kurt = fig.add_subplot(gs[2, 1])

    return fig, ax_fft, ax_bands, ax_peaks, ax_rms, ax_kurt


def update_plots(frame):
    """Update all plots with current data."""
    with data_lock:
        # FFT spectrum
        freqs = np.arange(len(fft_magnitude)) * FREQ_RESOLUTION
        ax_fft.clear()
        ax_fft.semilogy(freqs[:len(fft_magnitude)], fft_magnitude[:len(freqs)],
                       color='#1f77b4', linewidth=0.8)
        ax_fft.set_xlabel('Frequency (Hz)')
        ax_fft.set_ylabel('Magnitude (g/√Hz)')
        ax_fft.set_title('Vibration Spectrum')
        ax_fft.set_xlim(0, SAMPLE_RATE / 2)
        ax_fft.grid(True, alpha=0.3)

        # Band energy bars
        ax_bands.clear()
        bars = ax_bands.barh(BAND_NAMES, band_energies, color=BAND_COLORS)
        ax_bands.set_xlabel('Energy (g²·Hz)')
        ax_bands.set_title('Band Energy')
        ax_bands.grid(True, alpha=0.3, axis='x')

        # Peak frequencies
        ax_peaks.clear()
        if len(peak_freqs) > 0:
            valid_peaks = peak_freqs[peak_freqs > 0]
            if len(valid_peaks) > 0:
                ax_peaks.stem(valid_peaks, np.ones(len(valid_peaks)),
                            linefmt='r-', markerfmt='ro', basefmt='k-')
        ax_peaks.set_xlabel('Frequency (Hz)')
        ax_peaks.set_title('Peak Frequencies')
        ax_peaks.set_xlim(0, SAMPLE_RATE / 2)
        ax_peaks.set_ylim(0, 2)
        ax_peaks.grid(True, alpha=0.3)

        # RMS history
        if len(rms_history) > 1:
            ax_rms.clear()
            times = np.array(timestamp_history) - timestamp_history[0]
            ax_rms.plot(times, rms_history, color='#2ca02c', linewidth=1)
            ax_rms.set_xlabel('Time (s)')
            ax_rms.set_ylabel('RMS (g)')
            ax_rms.set_title('RMS Vibration History')
            ax_rms.grid(True, alpha=0.3)

        # Kurtosis history
        if len(kurtosis_history) > 1:
            ax_kurt.clear()
            times = np.array(timestamp_history) - timestamp_history[0]
            ax_kurt.plot(times, kurtosis_history, color='#d62728', linewidth=1)
            ax_kurt.axhline(y=3.0, color='orange', linestyle='--', alpha=0.5,
                          label='Normal (3.0)')
            ax_kurt.set_xlabel('Time (s)')
            ax_kurt.set_ylabel('Kurtosis')
            ax_kurt.set_title('Kurtosis History')
            ax_kurt.legend(fontsize=8)
            ax_kurt.grid(True, alpha=0.3)


def main():
    parser = argparse.ArgumentParser(description="Tremor Tile Spectral Viewer")
    parser.add_argument("--port", default="/dev/ttyACM0",
                       help="Serial port (default: /dev/ttyACM0)")
    parser.add_argument("--baud", type=int, default=115200,
                       help="Baud rate (default: 115200)")
    parser.add_argument("--refresh", type=int, default=100,
                       help="Plot refresh interval in ms (default: 100)")
    args = parser.parse_args()

    # Open serial port
    try:
        ser = serial.Serial(args.port, args.baud, timeout=1.0)
        print(f"Connected to {args.port} at {args.baud} baud")
        time.sleep(1)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        sys.exit(1)

    # Start serial reader thread
    reader_thread = threading.Thread(target=parse_serial_data, args=(ser,),
                                     daemon=True)
    reader_thread.start()

    # Create figure
    fig, ax_fft, ax_bands, ax_peaks, ax_rms, ax_kurt = create_figure()

    # Start animation
    ani = animation.FuncAnimation(fig, update_plots, interval=args.refresh,
                                   cache_frame_data=False)

    try:
        plt.show()
    except KeyboardInterrupt:
        pass

    global running
    running = False
    ser.close()
    print("Disconnected.")


if __name__ == "__main__":
    main()