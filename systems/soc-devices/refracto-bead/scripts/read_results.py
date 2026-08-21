#!/usr/bin/env python3
"""
read_results.py — Read Refracto Bead measurement results via BLE and plot them.

Usage:
    python3 read_results.py --mac AA:BB:CC:DD:EE:FF --mode ri
    python3 read_results.py --mac AA:BB:CC:DD:EE:FF --mode brix --export result.json
    python3 read_results.py --mac AA:BB:CC:DD:EE:FF --watch
"""

import argparse
import asyncio
import json
import struct
import sys
from datetime import datetime

try:
    from bleak import BleakClient
except ImportError:
    print("Install bleak: pip install bleak")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("Install matplotlib + numpy: pip install matplotlib numpy")
    sys.exit(1)


# BLE UUIDs (16-bit, expanded to 128-bit standard UUID)
SERVICE_UUID     = "0000ffc0-0000-1000-8000-00805f9b34fb"
CHAR_COMMAND     = "0000ffc1-0000-1000-8000-00805f9b34fb"
CHAR_RI          = "0000ffc2-0000-1000-8000-00805f9b34fb"
CHAR_DERIVED     = "0000ffc3-0000-1000-8000-00805f9b34fb"
CHAR_COMPOUND    = "0000ffc4-0000-1000-8000-00805f9b34fb"
CHAR_WAVEFORM    = "0000ffc5-0000-1000-8000-00805f9b34fb"
CHAR_STATUS      = "0000ffc6-0000-1000-8000-00805f9b34fb"
CHAR_BATTERY     = "0000ffc7-0000-1000-8000-00805f9b34fb"
CHAR_LIBRARY     = "0000ffc8-0000-1000-8000-00805f9b34fb"


def parse_ri_result(data: bytes) -> dict:
    """Parse the 32-byte RI results characteristic."""
    n_D, n_F, n_C, abbe_vd, t_prism, dispersion = struct.unpack_from("<6f", data, 0)
    return {
        "n_D": round(n_D, 4),
        "n_F": round(n_F, 4),
        "n_C": round(n_C, 4),
        "abbe_vd": round(abbe_vd, 1),
        "t_prism": round(t_prism, 2),
        "dispersion": round(dispersion, 4),
    }


def parse_derived_result(data: bytes) -> dict:
    """Parse the 20-byte derived results characteristic."""
    brix, sg, abv, freeze_pt = struct.unpack_from("<4f", data, 0)
    compound_id = data[16]
    return {
        "brix": round(brix, 1),
        "specific_gravity": round(sg, 3),
        "abv": round(abv, 1),
        "freeze_point": round(freeze_pt, 1),
        "compound_id": compound_id,
    }


def parse_compound_match(data: bytes) -> dict:
    """Parse the 48-byte compound match characteristic."""
    name = data[0:16].rstrip(b'\x00').decode('ascii', errors='replace')
    n_D, abbe_vd, confidence = struct.unpack_from("<3f", data, 16)
    return {
        "compound_name": name,
        "library_n_D": round(n_D, 4),
        "library_abbe_vd": round(abbe_vd, 1),
        "confidence": round(confidence, 3),
    }


async def read_all_results(client: BleakClient) -> dict:
    """Read all result characteristics and combine into a single dict."""
    ri_data = await client.read_gatt_char(CHAR_RI)
    derived_data = await client.read_gatt_char(CHAR_DERIVED)
    compound_data = await client.read_gatt_char(CHAR_COMPOUND)

    results = {}
    results.update(parse_ri_result(ri_data))
    results.update(parse_derived_result(derived_data))
    results.update(parse_compound_match(compound_data))
    results["timestamp"] = datetime.now().isoformat()

    return results


async def read_battery(client: BleakClient) -> int:
    data = await client.read_gatt_char(CHAR_BATTERY)
    return data[0]


async def read_status(client: BleakClient) -> str:
    data = await client.read_gatt_char(CHAR_STATUS)
    status_names = {0: "idle", 1: "measuring", 2: "streaming", 3: "error"}
    return status_names.get(data[0], f"unknown({data[0]})")


async def trigger_measurement(client: BleakClient):
    """Send the measure command via BLE."""
    await client.write_gatt_char(CHAR_COMMAND, b'\x01', response=True)


def print_results(results: dict):
    """Pretty-print measurement results."""
    print("\n" + "=" * 50)
    print("  REFRACTO BEAD — Measurement Results")
    print("=" * 50)
    print(f"  Refractive Index (n_D):  {results['n_D']:.4f}")
    print(f"  Abbe Number (V_D):       {results['abbe_vd']:.1f}")
    print(f"  Dispersion (n_F - n_C):  {results['dispersion']:.4f}")
    print(f"  Prism Temperature:       {results['t_prism']:.1f} °C")
    print("-" * 50)
    print(f"  Brix:           {results['brix']:.1f} °Bx")
    print(f"  Specific Grav:  {results['specific_gravity']:.3f}")
    print(f"  %ABV:           {results['abv']:.1f} %")
    print(f"  Freeze Point:   {results['freeze_point']:.1f} °C")
    print("-" * 50)
    print(f"  Compound:       {results['compound_name']}")
    print(f"  Confidence:     {results['confidence']*100:.0f}%")
    print("=" * 50 + "\n")


def plot_results(results: dict):
    """Create a summary visualization."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # RI gauge
    ax = axes[0]
    ax.barh(["n_D"], [results["n_D"]], color="#3498db", height=0.5)
    ax.set_xlim(1.3, 1.7)
    ax.set_xlabel("Refractive Index")
    ax.set_title("RI Measurement")
    ax.axvline(results["n_D"], color="#e74c3c", linestyle="--", alpha=0.5)

    # Dispersion
    ax = axes[1]
    wavelengths = [470, 525, 589, 655]
    n_values = [results["n_F"], results["n_D"], results["n_D"], results["n_C"]]
    # Approximate: we only have n_F, n_C, n_D — plot the 3 we know
    wl_plot = [470, 589, 655]
    n_plot = [results["n_F"], results["n_D"], results["n_C"]]
    ax.plot(wl_plot, n_plot, "o-", color="#2ecc71", markersize=8)
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Refractive Index")
    ax.set_title(f"Dispersion (V_D={results['abbe_vd']:.1f})")

    # Compound match
    ax = axes[2]
    ax.axis("off")
    conf = results["confidence"] * 100
    color = "#2ecc71" if conf > 85 else "#f39c12" if conf > 50 else "#e74c3c"
    ax.text(0.5, 0.7, results["compound_name"], ha="center", va="center",
            fontsize=16, fontweight="bold", transform=ax.transAxes)
    ax.text(0.5, 0.4, f"{conf:.0f}% confidence", ha="center", va="center",
            fontsize=14, color=color, transform=ax.transAxes)
    ax.text(0.5, 0.2, f"n_D={results['n_D']:.4f}  V_D={results['abbe_vd']:.1f}",
            ha="center", va="center", fontsize=10, transform=ax.transAxes)
    ax.set_title("Compound Identification")

    plt.tight_layout()
    plt.show()


async def main(args):
    if not args.mac:
        print("Error: --mac is required for BLE connection")
        sys.exit(1)

    async with BleakClient(args.mac) as client:
        print(f"Connected to {args.mac}")
        battery = await read_battery(client)
        status = await read_status(client)
        print(f"Battery: {battery}%, Status: {status}")

        if args.watch:
            print("\nWatching for new measurements (Ctrl+C to stop)...")
            results_history = []

            def notification_handler(sender, data):
                if sender == CHAR_RI:
                    print("\n[New measurement received]")
                    asyncio.create_task(handle_notification(client, results_history))

            await client.start_notify(CHAR_RI, notification_handler)
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nStopped watching.")
                await client.stop_notify(CHAR_RI)
                if results_history:
                    print(f"\nCollected {len(results_history)} measurements")
                    for r in results_history:
                        print_results(r)
            return

        if args.measure:
            print("Triggering measurement...")
            await trigger_measurement(client)
            await asyncio.sleep(5)  # Wait for measurement to complete

        results = await read_all_results(client)
        print_results(results)

        if args.plot:
            plot_results(results)

        if args.export:
            with open(args.export, "w") as f:
                json.dump(results, f, indent=2)
            print(f"Results exported to {args.export}")


async def handle_notification(client, history):
    """Handle a notification by reading full results."""
    results = await read_all_results(client)
    print_results(results)
    history.append(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refracto Bead BLE Results Reader")
    parser.add_argument("--mac", help="Device MAC address")
    parser.add_argument("--mode", default="all",
                        choices=["ri", "brix", "sg", "cool", "alc", "all"],
                        help="Display mode")
    parser.add_argument("--measure", action="store_true",
                        help="Trigger a measurement before reading")
    parser.add_argument("--watch", action="store_true",
                        help="Watch for new measurement notifications")
    parser.add_argument("--plot", action="store_true",
                        help="Plot results with matplotlib")
    parser.add_argument("--export", help="Export results to JSON file")
    args = parser.parse_args()
    asyncio.run(main(args))