#!/usr/bin/env python3
"""
kappa-pin / scripts / live_stream.py
Live BLE client for Kappa Pin — plots ΔT vs time and ln(t) regression in real time.

Usage:
    python3 live_stream.py

Connects to the Kappa Pin BLE peripheral, subscribes to the data stream
characteristic, and plots the live temperature rise curve with the
ln(t) regression fit overlaid.

Requires: bleak, matplotlib, numpy
    pip install bleak matplotlib numpy
"""

import asyncio
import struct
import sys
import time
from collections import deque

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from bleak import BleakClient, BleakScanner

# BLE UUIDs (match firmware)
UUID_SERVICE = "00009101-0000-1000-8000-00805f9b34fb"
UUID_DATA    = "00009102-0000-1000-8000-00805f9b34fb"
UUID_RESULT  = "00009103-0000-1000-8000-00805f9b34fb"
UUID_CMD     = "00009104-0000-1000-8000-00805f9b34fb"

# Command codes
CMD_START = 0x01
CMD_STOP = 0x02
CMD_SET_MATERIAL = 0x03

MATERIALS = ["Liquid", "Wet Soil", "Dry Soil", "Polymer",
             "Insulation", "Metal Powder", "Custom"]


class KappaPinStream:
    def __init__(self):
        self.times = deque(maxlen=7200)
        self.dts = deque(maxlen=7200)
        self.qs = deque(maxlen=7200)
        self.result = None
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 8))
        self.fig.suptitle("Kappa Pin — Live Thermal Conductivity Measurement")

    def notification_handler(self, sender, data: bytearray):
        if len(data) == 6:
            # Data sample: ts_u16 + dt_s16 + q_s16
            ts_raw, dt_raw, q_raw = struct.unpack("<Hhh", data)
            t_s = ts_raw / 100.0
            dt_mk = dt_raw / 4.0
            q_mw = q_raw
            self.times.append(t_s)
            self.dts.append(dt_mk)
            self.qs.append(q_mw)
        elif len(data) == 17:
            # Result: 4 floats + 1 byte
            lam, alpha, rhocp, effus = struct.unpack("<ffff", data[:16])
            status = data[16]
            self.result = {
                "lambda": lam,
                "alpha": alpha,
                "rho_cp": rhocp,
                "effusivity": effus,
                "status": status,
            }
            print(f"\n=== RESULT ===")
            print(f"  λ  = {lam:.4f} W/(m·K)")
            print(f"  α  = {alpha:.4f} mm²/s")
            print(f"  ρcₚ = {rhocp:.4e} J/(m³·K)")
            print(f"  e  = {effus:.1f} J/(m²·K·s^0.5)")
            print(f"  status = {status}")

    def update_plot(self, frame):
        self.ax1.clear()
        self.ax2.clear()

        if len(self.times) < 2:
            self.ax1.set_title("Waiting for data...")
            return

        t = np.array(self.times)
        dt = np.array(self.dts) / 1000.0  # mK → °C
        q = np.array(self.qs) / 1000.0    # mW → W

        # Plot 1: ΔT vs time
        self.ax1.plot(t, dt, "b-", linewidth=1.5, label="ΔT")
        self.ax1.set_xlabel("Time (s)")
        self.ax1.set_ylabel("ΔT (°C)")
        self.ax1.set_title("Temperature Rise vs Time")
        self.ax1.legend()
        self.ax1.grid(True, alpha=0.3)

        # Mark heating phase (Q > 0)
        heating = q > 0.01
        if np.any(heating):
            t_heat = t[heating]
            if len(t_heat) > 0:
                self.ax1.axvspan(t_heat[0], t_heat[-1], alpha=0.1, color="red",
                                 label="heating")

        # Plot 2: ΔT vs ln(t) — linear regression
        valid = (t > 0.5) & heating  # exclude t=0 and cooling phase
        if np.sum(valid) > 10:
            ln_t = np.log(t[valid])
            dt_valid = dt[valid]
            self.ax2.plot(ln_t, dt_valid, "b.", markersize=2, label="data")

            # Linear fit
            coeffs = np.polyfit(ln_t, dt_valid, 1)
            fit_line = np.polyval(coeffs, ln_t)
            self.ax2.plot(ln_t, fit_line, "r-", linewidth=2,
                          label=f"fit: slope={coeffs[0]:.4f} K/ln(s)")

            # Compute λ if we know Q (average from data)
            avg_q = np.mean(q[valid]) if np.any(valid) else 0
            active_len = 0.080  # NP-100 default
            Q_per_m = avg_q / active_len
            if coeffs[0] != 0:
                lam = Q_per_m / (4 * np.pi * coeffs[0])
                self.ax2.text(0.05, 0.95, f"λ = {lam:.4f} W/(m·K)\n"
                              f"Q = {avg_q:.3f} W\n"
                              f"R² = {np.corrcoef(ln_t, dt_valid)[0,1]**2:.5f}",
                              transform=self.ax2.transAxes, fontsize=10,
                              verticalalignment="top",
                              bbox=dict(boxstyle="round", facecolor="wheat"))

        self.ax2.set_xlabel("ln(t)")
        self.ax2.set_ylabel("ΔT (°C)")
        self.ax2.set_title("Linear Regression: ΔT vs ln(t)")
        self.ax2.legend()
        self.ax2.grid(True, alpha=0.3)

        # Show result if available
        if self.result:
            self.fig.suptitle(
                f"Kappa Pin — λ={self.result['lambda']:.4f} W/(m·K), "
                f"α={self.result['alpha']:.3f} mm²/s",
                fontsize=12
            )

        plt.tight_layout()

    async def run(self, device_addr=None):
        # Scan for Kappa Pin if no address provided
        if device_addr is None:
            print("Scanning for Kappa Pin...")
            devices = await BleakScanner.discover(timeout=10.0)
            for d in devices:
                if d.name and "KappaPin" in d.name:
                    device_addr = d.address
                    print(f"Found: {d.name} ({d.address})")
                    break
            if device_addr is None:
                print("Kappa Pin not found. Ensure device is powered on and BLE is advertising.")
                return

        print(f"Connecting to {device_addr}...")
        async with BleakClient(device_addr) as client:
            print("Connected!")
            print("Commands: [s]tart, [x]stop, [m]aterial, [q]uit")

            await client.start_notify(UUID_DATA, self.notification_handler)
            await client.start_notify(UUID_RESULT, self.notification_handler)

            # Start animation
            ani = FuncAnimation(self.fig, self.update_plot, interval=200,
                                cache_frame_data=False)

            # Interactive commands
            loop = asyncio.get_event_loop()
            def input_thread():
                while True:
                    cmd = input().strip().lower()
                    if cmd == "s":
                        asyncio.run_coroutine_threadsafe(
                            client.write_gatt_char(UUID_CMD, bytes([CMD_START])),
                            loop)
                        print("→ Start command sent")
                    elif cmd == "x":
                        asyncio.run_coroutine_threadsafe(
                            client.write_gatt_char(UUID_CMD, bytes([CMD_STOP])),
                            loop)
                        print("→ Stop command sent")
                    elif cmd == "m":
                        print("Materials: " + ", ".join(
                            f"{i}:{m}" for i, m in enumerate(MATERIALS)))
                        try:
                            idx = int(input("Material ID: "))
                            asyncio.run_coroutine_threadsafe(
                                client.write_gatt_char(UUID_CMD,
                                    bytes([CMD_SET_MATERIAL, idx])),
                                loop)
                            print(f"→ Material set to {MATERIALS[idx]}")
                        except (ValueError, IndexError):
                            print("Invalid material ID")
                    elif cmd == "q":
                        print("Quitting...")
                        loop.call_soon_threadsafe(loop.stop)
                        break

            import threading
            t = threading.Thread(target=input_thread, daemon=True)
            t.start()

            plt.show()

            await client.stop_notify(UUID_DATA)
            await client.stop_notify(UUID_RESULT)


def main():
    addr = sys.argv[1] if len(sys.argv) > 1 else None
    stream = KappaPinStream()
    try:
        asyncio.run(stream.run(addr))
    except KeyboardInterrupt:
        print("\nDisconnected.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()