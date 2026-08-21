#!/usr/bin/env python3
"""
live_view.py — Real-time EEM heatmap viewer for Fluor Cast

Connects via BLE to the Fluor Cast device and displays a live
excitation-emission matrix heatmap, spectrum view, and classification
results in a matplotlib GUI.

Usage:
    python3 live_view.py [--mac AA:BB:CC:DD:EE:FF]
    python3 live_view.py [--port /dev/ttyUSB0]
"""

import argparse
import struct
import time
import threading
import serial
import numpy as np

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from matplotlib.widgets import Button
except ImportError:
    print("Please install matplotlib: pip install matplotlib numpy pyserial")
    exit(1)


class FluorCastLiveView:
    """Real-time EEM viewer."""

    # Excitation wavelengths
    EX_WAVELENGTHS = [255, 280, 340, 365, 405, 440, 470, 525]

    def __init__(self, port: str = None, mac: str = None, baud: int = 921600):
        self.port = port
        self.mac = mac
        self.baud = baud
        self.eem_data = np.zeros((8, 256), dtype=np.uint16)
        self.connected = False
        self.running = False
        self.lock = threading.Lock()
        self.ser = None

    def connect_serial(self):
        """Connect via USB serial (ESP32-C3 USB CDC)."""
        self.ser = serial.Serial(self.port, self.baud, timeout=1.0)
        self.connected = True
        print(f"Connected via serial: {self.port}")

    def connect_ble(self):
        """Connect via BLE (requires bleak)."""
        try:
            from bleak import BleakClient, BleakScanner
        except ImportError:
            print("BLE requires bleak: pip install bleak")
            exit(1)

        print(f"Scanning for Fluor Cast device...")
        # In production: scan for device with specific service UUID
        # For now: use provided MAC address
        self.ser = None  # BLE uses different transport
        print(f"BLE connection to {self.mac} (stub — implement with bleak)")

    def poll_data(self):
        """Background thread: poll for EEM data."""
        while self.running:
            if self.ser and self.connected:
                # Read framed data from serial
                try:
                    if self.ser.in_waiting >= 7:
                        # Look for SOF
                        byte = self.ser.read(1)
                        if byte == b"\xAA":
                            length_bytes = self.ser.read(2)
                            length = int.from_bytes(length_bytes, "little")
                            cmd = self.ser.read(1)
                            payload = self.ser.read(length)
                            crc = self.ser.read(2)
                            eof = self.ser.read(1)

                            cmd_byte = cmd[0]
                            if cmd_byte == 0x01:  # EEM_DATA
                                with self.lock:
                                    # Parse EEM matrix from payload
                                    # Each chunk is 512 bytes of the 4096-byte matrix
                                    pass
                except Exception as e:
                    print(f"Read error: {e}")
            time.sleep(0.01)

    def start(self):
        """Start the live viewer."""
        if self.port:
            self.connect_serial()
        elif self.mac:
            self.connect_ble()
        else:
            print("Error: specify --port or --mac")
            return

        self.running = True
        poll_thread = threading.Thread(target=self.poll_data, daemon=True)
        poll_thread.start()

        # Set up matplotlib figure
        fig, axes = plt.subplots(2, 2, figsize=(14, 9))
        fig.suptitle("Fluor Cast — Live EEM Viewer", fontsize=14, fontweight="bold")

        # EEM heatmap (top, spanning full width)
        ax_eem = axes[0][0]
        ax_spectrum = axes[0][1]
        ax_result = axes[1][0]
        ax_status = axes[1][1]

        # EEM heatmap
        with self.lock:
            im = ax_eem.imshow(
                self.eem_data,
                aspect="auto",
                origin="lower",
                extent=[340, 755, 255, 525],
                cmap="jet",
                interpolation="nearest",
                norm=LogNorm(vmin=1, vmax=65535),
            )
        ax_eem.set_xlabel("Emission Wavelength (nm)")
        ax_eem.set_ylabel("Excitation Wavelength (nm)")
        ax_eem.set_title("Excitation-Emission Matrix")
        plt.colorbar(im, ax=ax_eem, label="Intensity (counts)")

        # Spectrum view
        spectrum_line, = ax_spectrum.plot([], [], "b-", linewidth=1)
        ax_spectrum.set_xlim(340, 755)
        ax_spectrum.set_ylim(0, 65535)
        ax_spectrum.set_xlabel("Emission Wavelength (nm)")
        ax_spectrum.set_ylabel("Intensity (counts)")
        ax_spectrum.set_title("Emission Spectrum (365 nm ex)")
        ax_spectrum.grid(True, alpha=0.3)

        # Result text
        result_text = ax_result.text(
            0.05, 0.95, "", transform=ax_result.transAxes,
            fontsize=12, verticalalignment="top", fontfamily="monospace"
        )
        ax_result.set_title("Classification Result")
        ax_result.axis("off")

        # Status
        status_text = ax_status.text(
            0.05, 0.95, "", transform=ax_status.transAxes,
            fontsize=10, verticalalignment="top", fontfamily="monospace"
        )
        ax_status.set_title("Device Status")
        ax_status.axis("off")

        # Animation update function
        def update(frame):
            with self.lock:
                # Update heatmap
                im.set_array(self.eem_data)
                im.set_norm(LogNorm(vmin=max(1, self.eem_data.min()),
                                     vmax=max(10, self.eem_data.max())))

                # Update spectrum (365 nm excitation row)
                spectrum = self.eem_data[3]  # 365nm = index 3
                wavelengths = np.linspace(340, 755, 256)
                spectrum_line.set_data(wavelengths, spectrum)

                # Auto-scale
                if spectrum.max() > 0:
                    ax_spectrum.set_ylim(0, min(65535, spectrum.max() * 1.2))

            return [im, spectrum_line, result_text, status_text]

        from matplotlib.animation import FuncAnimation
        anim = FuncAnimation(fig, update, interval=500, blit=False, cache_frame_data=False)

        plt.tight_layout()
        plt.show()

        self.running = False

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()


def main():
    parser = argparse.ArgumentParser(description="Fluor Cast Live EEM Viewer")
    parser.add_argument("--port", default=None, help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--mac", default=None, help="BLE MAC address")
    parser.add_argument("--baud", type=int, default=921600, help="Serial baud rate")
    args = parser.parse_args()

    viewer = FluorCastLiveView(port=args.port, mac=args.mac, baud=args.baud)

    try:
        viewer.start()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        viewer.stop()


if __name__ == "__main__":
    main()