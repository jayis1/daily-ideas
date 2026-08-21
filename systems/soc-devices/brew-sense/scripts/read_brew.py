#!/usr/bin/env python3
"""
Brew Sense BLE Reader

Connects to a Brew Sense device via Bluetooth Low Energy and
displays real-time fermentation data.
"""

import asyncio
import argparse
import sys
from datetime import datetime

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Please install bleak: pip install bleak")
    sys.exit(1)


# BLE Service and Characteristic UUIDs
BREWSENSE_SERVICE_UUID = "0000ffb0-0000-1000-8000-00805f9b34fb"
CHAR_GRAVITY  = "0000ffb1-0000-1000-8000-00805f9b34fb"
CHAR_TEMP     = "0000ffb2-0000-1000-8000-00805f9b34fb"
CHAR_CO2      = "0000ffb3-0000-1000-8000-00805f9b34fb"
CHAR_PH       = "0000ffb4-0000-1000-8000-00805f9b34fb"
CHAR_PRESSURE = "0000ffb5-0000-1000-8000-00805f9b34fb"
CHAR_STAGE    = "0000ffb6-0000-1000-8000-00805f9b34fb"
CHAR_ACTIVITY = "0000ffb7-0000-1000-8000-00805f9b34fb"
CHAR_BATTERY  = "0000ffb8-0000-1000-8000-00805f9b34fb"
CHAR_TREND    = "0000ffb9-0000-1000-8000-00805f9b34fb"
CHAR_INFO     = "0000ffba-0000-1000-8000-00805f9b34fb"

STAGE_NAMES = {
    0: "LAG",
    1: "ACTIVE",
    2: "PEAK",
    3: "SLOWING",
    4: "FINISHED",
    5: "STUCK",
}

TREND_ARROWS = {
    -2: "↓↓",
    -1: "↓",
    0: "→",
    1: "↑",
    2: "↑↑",
}


def parse_float32(data):
    """Parse little-endian float32 from BLE characteristic data."""
    if len(data) >= 4:
        import struct
        return struct.unpack("<f", data[:4])[0]
    return 0.0


def parse_uint16(data):
    """Parse little-endian uint16 from BLE characteristic data."""
    if len(data) >= 2:
        return int.from_bytes(data[:2], "little")
    return 0


def parse_uint8(data):
    """Parse uint8 from BLE characteristic data."""
    if len(data) >= 1:
        return data[0]
    return 0


def parse_int8(data):
    """Parse int8 from BLE characteristic data."""
    if len(data) >= 1:
        val = data[0]
        return val - 256 if val > 127 else val
    return 0


def parse_string(data):
    """Parse UTF-8 string from BLE characteristic data."""
    return data.decode("utf-8", errors="replace")


async def scan_devices(timeout=10):
    """Scan for Brew Sense devices."""
    print(f"Scanning for Brew Sense devices ({timeout}s)...")
    devices = await BleakScanner.discover(timeout=timeout)
    
    brew_devices = []
    for d in devices:
        if d.name and "BrewSense" in d.name:
            brew_devices.append(d)
            print(f"  Found: {d.name} ({d.address})")
    
    if not brew_devices:
        print("No Brew Sense devices found.")
        # Also show all devices in case name doesn't match
        print("\nAll BLE devices:")
        for d in devices:
            print(f"  {d.name or 'Unknown'} ({d.address})")
    
    return brew_devices


async def read_device(mac, continuous=False, interval=5):
    """Connect to a Brew Sense device and read data."""
    async with BleakClient(mac) as client:
        print(f"Connected to Brew Sense at {mac}")
        
        # Read device info
        try:
            info_data = await client.read_gatt_char(CHAR_INFO)
            device_info = parse_string(info_data)
            print(f"Device: {device_info}")
        except Exception:
            print("Could not read device info")
        
        if continuous:
            print("\nReading continuously (Ctrl+C to stop)...\n")
            print(f"{'Time':>8} | {'SG':>8} | {'Temp°C':>7} | {'CO2ppm':>7} | "
                  f"{'pH':>5} | {'hPa':>7} | {'Stage':>9} | {'Act':>4} | {'Trend':>5}")
            print("-" * 90)
            
            try:
                while True:
                    data = {}
                    
                    # Read all characteristics
                    try:
                        data["gravity"] = parse_float32(await client.read_gatt_char(CHAR_GRAVITY))
                    except Exception:
                        data["gravity"] = 0.0
                    
                    try:
                        data["temp"] = parse_float32(await client.read_gatt_char(CHAR_TEMP))
                    except Exception:
                        data["temp"] = 0.0
                    
                    try:
                        data["co2"] = parse_uint16(await client.read_gatt_char(CHAR_CO2))
                    except Exception:
                        data["co2"] = 0
                    
                    try:
                        data["ph"] = parse_float32(await client.read_gatt_char(CHAR_PH))
                    except Exception:
                        data["ph"] = 0.0
                    
                    try:
                        data["pressure"] = parse_float32(await client.read_gatt_char(CHAR_PRESSURE))
                    except Exception:
                        data["pressure"] = 0.0
                    
                    try:
                        data["stage"] = parse_uint8(await client.read_gatt_char(CHAR_STAGE))
                    except Exception:
                        data["stage"] = 0
                    
                    try:
                        data["activity"] = parse_uint8(await client.read_gatt_char(CHAR_ACTIVITY))
                    except Exception:
                        data["activity"] = 0
                    
                    try:
                        data["battery"] = parse_uint8(await client.read_gatt_char(CHAR_BATTERY))
                    except Exception:
                        data["battery"] = 0
                    
                    try:
                        data["trend"] = parse_int8(await client.read_gatt_char(CHAR_TREND))
                    except Exception:
                        data["trend"] = 0
                    
                    now = datetime.now().strftime("%H:%M:%S")
                    stage_name = STAGE_NAMES.get(data["stage"], "???")
                    trend_arrow = TREND_ARROWS.get(data["trend"], "?")
                    
                    print(f"{now:>8} | {data['gravity']:8.4f} | {data['temp']:7.1f} | "
                          f"{data['co2']:7d} | {data['ph']:5.2f} | {data['pressure']:7.1f} | "
                          f"{stage_name:>9} | {data['activity']:4d} | {trend_arrow:>5}")
                    
                    await asyncio.sleep(interval)
                    
            except KeyboardInterrupt:
                print("\nStopped.")
        
        else:
            # Single read
            print("\n=== Single Read ===")
            
            try:
                gravity = parse_float32(await client.read_gatt_char(CHAR_GRAVITY))
                print(f"Specific Gravity: {gravity:.4f}")
            except Exception as e:
                print(f"Gravity: Error ({e})")
            
            try:
                temp = parse_float32(await client.read_gatt_char(CHAR_TEMP))
                print(f"Temperature:      {temp:.1f}°C / {temp*9/5+32:.1f}°F")
            except Exception as e:
                print(f"Temperature:      Error ({e})")
            
            try:
                co2 = parse_uint16(await client.read_gatt_char(CHAR_CO2))
                print(f"CO₂:              {co2} ppm")
            except Exception as e:
                print(f"CO₂:              Error ({e})")
            
            try:
                ph = parse_float32(await client.read_gatt_char(CHAR_PH))
                print(f"pH:               {ph:.2f}")
            except Exception as e:
                print(f"pH:               Error ({e})")
            
            try:
                pressure = parse_float32(await client.read_gatt_char(CHAR_PRESSURE))
                print(f"Pressure:         {pressure:.1f} hPa")
            except Exception as e:
                print(f"Pressure:         Error ({e})")
            
            try:
                stage = parse_uint8(await client.read_gatt_char(CHAR_STAGE))
                stage_name = STAGE_NAMES.get(stage, "UNKNOWN")
                print(f"Stage:            {stage_name}")
            except Exception as e:
                print(f"Stage:            Error ({e})")
            
            try:
                activity = parse_uint8(await client.read_gatt_char(CHAR_ACTIVITY))
                print(f"Activity:         {activity}%")
            except Exception as e:
                print(f"Activity:         Error ({e})")
            
            try:
                battery = parse_uint8(await client.read_gatt_char(CHAR_BATTERY))
                print(f"Battery:          {battery}%")
            except Exception as e:
                print(f"Battery:         Error ({e})")
            
            try:
                trend = parse_int8(await client.read_gatt_char(CHAR_TREND))
                trend_name = TREND_ARROWS.get(trend, "?")
                print(f"Trend:            {trend_name}")
            except Exception as e:
                print(f"Trend:            Error ({e})")


def main():
    parser = argparse.ArgumentParser(description="Brew Sense BLE Reader")
    parser.add_argument("--mac", "-m", help="BLE MAC address of Brew Sense device")
    parser.add_argument("--scan", "-s", action="store_true", help="Scan for devices")
    parser.add_argument("--continuous", "-c", action="store_true",
                       help="Read continuously")
    parser.add_argument("--interval", "-i", type=int, default=5,
                       help="Read interval in seconds (default: 5)")
    parser.add_argument("--timeout", "-t", type=int, default=10,
                       help="Scan timeout in seconds (default: 10)")
    
    args = parser.parse_args()
    
    if args.scan:
        asyncio.run(scan_devices(args.timeout))
        return
    
    if not args.mac:
        print("Error: Please provide --mac address or use --scan to find devices")
        parser.print_help()
        sys.exit(1)
    
    try:
        asyncio.run(read_device(args.mac, args.continuous, args.interval))
    except KeyboardInterrupt:
        print("\nDisconnected.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()