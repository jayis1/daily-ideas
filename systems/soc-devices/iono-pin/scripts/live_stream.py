#!/usr/bin/env python3
"""
live_stream.py — Live Iono Pin IMS spectrum viewer over BLE.

Connects to the Iono Pin ESP32-C3 bridge over BLE, subscribes to the IMS
characteristic (0x2BE0), parses the binary frames, and plots the live
mobility spectrum (drift-time axis) + classification verdict using matplotlib.

Requirements:
    pip install bleak matplotlib numpy

Usage:
    python live_stream.py [--mac AA:BB:CC:DD:EE:FF]

If --mac is omitted, scans for devices advertising service 0x18A0.
"""
import argparse
import struct
import asyncio
from datetime import datetime

import numpy as np

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install bleak: pip install bleak")
    raise SystemExit(1)

try:
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
except ImportError:
    print("Install matplotlib: pip install matplotlib")
    raise SystemExit(1)

IMS_SERVICE_UUID = "000018a0-0000-1000-8000-00805f9b34fb"
IMS_CHAR_UUID    = "00002be0-0000-1000-8000-00805f9b34fb"
IMS_SAMPLES     = 140
T_START_MS      = 0.5
T_END_MS        = 3.5
DRIFT_LEN_CM    = 8.5
DRIFT_V         = 2125.0

CLASS_NAMES = {0: "NONE", 1: "EXPLOSIVE", 2: "DRUG", 3: "CWA",
               4: "TIC", 5: "VOC", 6: "REFERENCE"}


def parse_frame(data: bytes):
    """Parse a type-0x01 spectrum+verdict payload."""
    if len(data) < 13:
        return None
    off = 0
    pressure, t_drift, t_amb = struct.unpack_from("<fff", data, off); off += 12
    n_peaks = data[off]; off += 1
    k0s = []
    for _ in range(n_peaks):
        k0 = struct.unpack_from("<f", data, off)[0]; off += 4
        k0s.append(k0)
    amps = []
    for _ in range(n_peaks):
        amp = struct.unpack_from("<h", data, off)[0]; off += 2
        amps.append(amp)
    name_len = data[off]; off += 1
    name = data[off:off+name_len].decode("ascii", "replace"); off += name_len
    cls = data[off]; off += 1
    conf = struct.unpack_from("<f", data, off)[0]; off += 4
    # remaining bytes are the 140-sample averaged spectrum (high bytes)
    spec_hi = list(data[off:off+IMS_SAMPLES])
    spec = np.array(spec_hi[:IMS_SAMPLES], dtype=float) * 256.0
    return {
        "pressure": pressure, "t_drift": t_drift, "t_amb": t_amb,
        "k0s": k0s, "amps": amps, "name": name, "cls": cls, "conf": conf,
        "spectrum": spec,
    }


def k0_axis(p_kpa, t_c):
    """Build a K0 axis corresponding to the drift-time samples."""
    t_ms = np.linspace(T_START_MS, T_END_MS, IMS_SAMPLES)
    p_torr = p_kpa * 7.50062
    t_kelvin = t_c + 273.15
    k0 = (DRIFT_LEN_CM**2) / (DRIFT_V * t_ms * 1e-3) * (p_torr/760.0) * (273.0/t_kelvin)
    return k0


async def find_device(mac=None):
    if mac:
        return mac
    print("Scanning for Iono Pin (service 0x18A0)...")
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices:
        for s in d.metadata.get("uuids", []):
            if s.lower() == IMS_SERVICE_UUID:
                print(f"Found: {d.name} [{d.address}]")
                return d.address
    print("No Iono Pin found. Specify --mac.")
    raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser(description="Iono Pin live IMS viewer")
    ap.add_argument("--mac", default=None, help="BLE MAC address")
    args = ap.parse_args()

    loop = asyncio.new_event_loop()
    mac = loop.run_until_complete(find_device(args.mac))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), gridspec_kw={"height_ratios": [3, 1]})
    fig.suptitle("Iono Pin — Live Ion Mobility Spectrum")

    line_spec, = ax1.plot([], [], "b-", lw=1)
    ax1.set_xlabel("Drift time (ms)")
    ax1.set_ylabel("Signal (counts)")
    ax1.set_xlim(T_START_MS, T_END_MS)
    ax1.grid(True, alpha=0.3)
    verdict_txt = ax1.text(0.02, 0.95, "", transform=ax1.transAxes, va="top",
                            fontsize=12, fontfamily="monospace",
                            bbox=dict(boxstyle="round", fc="lightyellow", alpha=0.8))

    line_k0, = ax2.plot([], [], "r.-", lw=1)
    ax2.set_xlabel("Reduced mobility K0 (cm²/V·s)")
    ax2.set_ylabel("Amplitude")
    ax2.set_xlim(0.8, 3.0)
    ax2.grid(True, alpha=0.3)

    latest = {"frame": None}

    async def run():
        async with BleakClient(mac) as client:
            print(f"Connected to {mac}")
            def handler(sender, data: bytearray):
                # data is the characteristic notification payload = the frame payload
                f = parse_frame(bytes(data))
                if f:
                    latest["frame"] = f
            await client.start_notify(IMS_CHAR_UUID, handler)
            while plt.fignum_exists(fig.number):
                await asyncio.sleep(0.05)
            await client.stop_notify(IMS_CHAR_UUID)

    def update(frame_idx):
        f = latest["frame"]
        if f is None:
            return line_spec, verdict_txt, line_k0
        t_ms = np.linspace(T_START_MS, T_END_MS, IMS_SAMPLES)
        line_spec.set_data(t_ms, f["spectrum"])
        ax1.set_ylim(f["spectrum"].min()*1.1 - 1, f["spectrum"].max()*1.1 + 1)
        cls_name = CLASS_NAMES.get(f["cls"], "?")
        verdict = (f"{f['name']}  [{cls_name}]\n"
                   f"conf={f['conf']*100:.0f}%  P={f['pressure']:.0f}kPa  "
                   f"T={f['t_drift']:.1f}C\n"
                   f"peaks K0: {[f'{k:.2f}' for k in f['k0s']]}")
        verdict_txt.set_text(verdict)
        if f["k0s"]:
            line_k0.set_data(f["k0s"], f["amps"])
            ax2.set_ylim(0, max(f["amps"]) * 1.2 + 1)
        return line_spec, verdict_txt, line_k0

    ani = FuncAnimation(fig, update, interval=100, blit=False, cache_frame_data=False)

    # Run asyncio + matplotlib together
    import threading
    t = threading.Thread(target=lambda: loop.run_until_complete(run()), daemon=True)
    t.start()
    plt.show()


if __name__ == "__main__":
    main()