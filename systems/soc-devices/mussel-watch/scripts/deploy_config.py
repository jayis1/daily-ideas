#!/usr/bin/env python3
"""
Mussel Watch — Deployment Configuration Tool

Connects to a Mussel Watch device over BLE, reads the current configuration,
and allows setting parameters (deployment ID, sample interval, thresholds,
and triggering calibration) from the command line.

Usage:
    python3 deploy_config.py --scan
    python3 deploy_config.py --addr <BLE_MAC> --read
    python3 deploy_config.py --addr <BLE_MAC> --set-deployment-id 0x05
    python3 deploy_config.py --addr <BLE_MAC> --set-sample-interval 30
    python3 deploy_config.py --addr <BLE_MAC> --set-uplink-interval 1800
    python3 deploy_config.py --addr <BLE_MAC> --cal-closed 0
    python3 deploy_config.py --addr <BLE_MAC> --cal-open 0
    python3 deploy_config.py --addr <BLE_MAC> --watch

Requires: bleak (async BLE library)
    pip install bleak
"""

import sys
import argparse
import asyncio
import struct

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Error: bleak is required. Install with: pip install bleak")
    sys.exit(1)


# Mussel Watch BLE service and characteristic UUIDs
# Base UUID: 000019xx-0000-1000-8000-00805f9b34fb
SERVICE_UUID = "00001900-0000-1000-8000-00805f9b34fb"

CHAR_UUIDS = {
    "deployment_id":     "00001901-0000-1000-8000-00805f9b34fb",
    "sample_interval":   "00001902-0000-1000-8000-00805f9b34fb",
    "uplink_interval":   "00001903-0000-1000-8000-00805f9b34fb",
    "gape_threshold":    "00001904-0000-1000-8000-00805f9b34fb",
    "closure_duration":  "00001905-0000-1000-8000-00805f9b34fb",
    "cal_closed":        "00001906-0000-1000-8000-00805f9b34fb",
    "cal_open":          "00001907-0000-1000-8000-00805f9b34fb",
    "gape_live":         "00001908-0000-1000-8000-00805f9b34fb",
    "wq_live":           "00001909-0000-1000-8000-00805f9b34fb",
    "alert_flags":       "0000190a-0000-1000-8000-00805f9b34fb",
    "fw_version":        "0000190b-0000-1000-8000-00805f9b34fb",
}


ALERT_NAMES = {
    0: "Normal", 1: "Closure event", 2: "Sustained closure",
    3: "Rhythm deviation", 4: "Multi-mussel event",
    5: "Temperature anomaly", 6: "DO anomaly", 7: "Low battery",
}


async def scan_devices():
    """Scan for BLE devices and find Mussel Watch nodes."""
    print("Scanning for BLE devices (10 seconds)...")
    devices = await BleakScanner.discover(timeout=10.0)

    mussel_devices = []
    for d in devices:
        if "Mussel" in (d.name or ""):
            mussel_devices.append(d)
            print(f"  🦪 {d.name} — {d.address} (RSSI: {d.rssi} dBm)")

    if not mussel_devices:
        print("  No Mussel Watch devices found.")
        print("  Make sure the device is powered on and in advertising mode.")
    else:
        print(f"\nFound {len(mussel_devices)} Mussel Watch device(s).")
        print("Use --addr <MAC> to connect.")

    return mussel_devices


async def read_config(addr):
    """Read and display the current configuration from a Mussel Watch device."""
    async with BleakClient(addr, timeout=15.0) as client:
        print(f"Connected to {addr}")
        print("=" * 50)
        print("  MUSSEL WATCH — CURRENT CONFIGURATION")
        print("=" * 50)

        # Deployment ID
        data = await client.read_gatt_char(CHAR_UUIDS["deployment_id"])
        print(f"  Deployment ID    : 0x{data[0]:02X}")

        # Sample interval
        data = await client.read_gatt_char(CHAR_UUIDS["sample_interval"])
        interval = struct.unpack("<H", data)[0]
        print(f"  Sample interval  : {interval} s")

        # Uplink interval
        data = await client.read_gatt_char(CHAR_UUIDS["uplink_interval"])
        interval = struct.unpack("<H", data)[0]
        print(f"  Uplink interval  : {interval} s ({interval/60:.0f} min)")

        # Gape threshold
        data = await client.read_gatt_char(CHAR_UUIDS["gape_threshold"])
        threshold = struct.unpack("<f", data)[0]
        print(f"  Gape threshold   : {threshold:.2f}°")

        # Closure duration
        data = await client.read_gatt_char(CHAR_UUIDS["closure_duration"])
        dur = struct.unpack("<H", data)[0]
        print(f"  Closure alert    : {dur} s ({dur/60:.0f} min)")

        # Firmware version
        data = await client.read_gatt_char(CHAR_UUIDS["fw_version"])
        fw = data.decode("ascii", errors="replace").rstrip("\x00")
        print(f"  Firmware version : {fw}")

        # Live gape angles
        data = await client.read_gatt_char(CHAR_UUIDS["gape_live"])
        gapes = struct.unpack("<4f", data)
        print(f"  Live gape angles :")
        for i, g in enumerate(gapes):
            if g < -100:
                print(f"    Mussel {chr(65+i)}     : (unused)")
            else:
                status = "OPEN" if g > 2.0 else "CLOSED"
                print(f"    Mussel {chr(65+i)}     : {g:.2f}° [{status}]")

        # Live water quality
        data = await client.read_gatt_char(CHAR_UUIDS["wq_live"])
        temp, do_mgl, depth, batt = struct.unpack("<4f", data)
        print(f"  Water temp       : {temp:.2f} °C")
        print(f"  Dissolved O₂     : {do_mgl:.2f} mg/L")
        print(f"  Depth            : {depth:.2f} m")
        print(f"  Battery          : {batt:.2f} V")

        # Alert flags
        data = await client.read_gatt_char(CHAR_UUIDS["alert_flags"])
        alert = struct.unpack("<H", data)[0]
        print(f"  Current alert    : {alert} ({ALERT_NAMES.get(alert, 'Unknown')})")
        print("=" * 50)


async def set_deployment_id(addr, value):
    async with BleakClient(addr, timeout=15.0) as client:
        await client.write_gatt_char(CHAR_UUIDS["deployment_id"], bytes([value]))
        print(f"Deployment ID set to 0x{value:02X}")


async def set_sample_interval(addr, seconds):
    async with BleakClient(addr, timeout=15.0) as client:
        data = struct.pack("<H", seconds)
        await client.write_gatt_char(CHAR_UUIDS["sample_interval"], data)
        print(f"Sample interval set to {seconds} s")


async def set_uplink_interval(addr, seconds):
    async with BleakClient(addr, timeout=15.0) as client:
        data = struct.pack("<H", seconds)
        await client.write_gatt_char(CHAR_UUIDS["uplink_interval"], data)
        print(f"Uplink interval set to {seconds} s ({seconds/60:.0f} min)")


async def calibrate_closed(addr, channel):
    async with BleakClient(addr, timeout=15.0) as client:
        await client.write_gatt_char(CHAR_UUIDS["cal_closed"], bytes([channel]))
        print(f"Calibration (closed) triggered for channel {channel}")
        print("  Make sure the mussel is held closed!")


async def calibrate_open(addr, channel):
    async with BleakClient(addr, timeout=15.0) as client:
        await client.write_gatt_char(CHAR_UUIDS["cal_open"], bytes([channel]))
        print(f"Calibration (open) triggered for channel {channel}")
        print("  Make sure the mussel is naturally wide open!")


async def watch_live(addr):
    """Continuously read and display live gape + water quality data."""
    print(f"Watching live data from {addr} (Ctrl+C to stop)...\n")
    async with BleakClient(addr, timeout=15.0) as client:
        try:
            while True:
                # Read live gape
                data = await client.read_gatt_char(CHAR_UUIDS["gape_live"])
                gapes = struct.unpack("<4f", data)

                # Read live WQ
                wq = await client.read_gatt_char(CHAR_UUIDS["wq_live"])
                temp, do_mgl, depth, batt = struct.unpack("<4f", wq)

                # Read alert
                alert_data = await client.read_gatt_char(CHAR_UUIDS["alert_flags"])
                alert = struct.unpack("<H", alert_data)[0]

                # Display
                gape_str = "  ".join(
                    f"M{chr(65+i)}: {g:5.2f}°" if g >= 0 else f"M{chr(65+i)}: ---"
                    for i, g in enumerate(gapes)
                )
                print(f"\r  {gape_str}  |  T:{temp:.1f}°C  DO:{do_mgl:.1f}mg/L  "
                      f"D:{depth:.2f}m  Batt:{batt:.1f}V  Alert:{alert}  ",
                      end="", flush=True)
                await asyncio.sleep(0.5)

        except KeyboardInterrupt:
            print("\n\nStopped.")


def main():
    parser = argparse.ArgumentParser(description="Mussel Watch BLE configuration tool")
    parser.add_argument("--scan", action="store_true", help="Scan for Mussel Watch devices")
    parser.add_argument("--addr", help="BLE MAC address of the device")
    parser.add_argument("--read", action="store_true", help="Read current configuration")
    parser.add_argument("--set-deployment-id", type=lambda x: int(x, 0),
                       help="Set deployment ID (hex or decimal)")
    parser.add_argument("--set-sample-interval", type=int, help="Set sample interval (seconds)")
    parser.add_argument("--set-uplink-interval", type=int, help="Set uplink interval (seconds)")
    parser.add_argument("--cal-closed", type=int, metavar="CHANNEL", help="Trigger closed calibration")
    parser.add_argument("--cal-open", type=int, metavar="CHANNEL", help="Trigger open calibration")
    parser.add_argument("--watch", action="store_true", help="Watch live data continuously")
    args = parser.parse_args()

    if args.scan:
        asyncio.run(scan_devices())
        return

    if not args.addr:
        print("Error: --addr is required (or use --scan to find devices)")
        sys.exit(1)

    if args.read:
        asyncio.run(read_config(args.addr))
    elif args.set_deployment_id is not None:
        asyncio.run(set_deployment_id(args.addr, args.set_deployment_id))
    elif args.set_sample_interval:
        asyncio.run(set_sample_interval(args.addr, args.set_sample_interval))
    elif args.set_uplink_interval:
        asyncio.run(set_uplink_interval(args.addr, args.set_uplink_interval))
    elif args.cal_closed is not None:
        asyncio.run(calibrate_closed(args.addr, args.cal_closed))
    elif args.cal_open is not None:
        asyncio.run(calibrate_open(args.addr, args.cal_open))
    elif args.watch:
        asyncio.run(watch_live(args.addr))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()