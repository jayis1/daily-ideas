#!/usr/bin/env python3
"""
Sap Watch — Fleet Provisioning Script

Batch-provisions LoRaWAN credentials (AppEUI, AppKey, DevEUI) for a fleet
of Sap Watch nodes via their serial consoles. Generates unique DevEUIs
from a base address and writes them to each device.

Usage:
    python deploy_mesh.py --nodes node-list.csv --app-eui 70B3D57ED0000001 \\
        --app-key 2B7E151628AED2A6ABF7158809CF4F3C --base-dev-eui 70B3D57ED005A1B2
    python deploy_mesh.py --scan --ports /dev/ttyUSB0,/dev/ttyUSB1,/dev/ttyUSB2

Copyright (c) 2026 SoC Device Inventions. MIT License.
"""

import argparse
import csv
import random
import re
import sys
import time

try:
    import serial
except ImportError:
    print("Install pyserial first: pip install pyserial", file=sys.stderr)
    sys.exit(1)


def gen_dev_eui(base: str, index: int) -> str:
    """Generate a unique DevEUI from a base address + index offset."""
    base_int = int(base.replace(":", ""), 16)
    dev_eui_int = base_int + index
    return f"{dev_eui_int:016X}"


def format_eui(eui_hex: str) -> str:
    """Format hex EUI with colons: 70B3D57ED005A1B2 → 70:B3:D5:7E:D0:05:A1:B2"""
    return ":".join(eui_hex[i:i+2] for i in range(0, 16, 2))


def provision_node(port: str, app_eui: str, app_key: str, dev_eui: str,
                   baud: int = 115200) -> bool:
    """Provision one Sap Watch node via its serial console."""
    print(f"  Provisioning {port} → DevEUI {format_eui(dev_eui)}...", end=" ", flush=True)
    try:
        ser = serial.Serial(port, baudrate=baud, timeout=5)
    except serial.SerialException as e:
        print(f"FAIL (cannot open port: {e})")
        return False

    # Hold the PROG button equivalent: send a break or DTR toggle
    ser.dtr = False
    time.sleep(0.5)
    ser.dtr = True
    time.sleep(1)

    # Wait for provisioning menu
    buf = ""
    deadline = time.time() + 5
    while time.time() < deadline:
        if ser.in_waiting:
            buf += ser.read(ser.in_waiting).decode("utf-8", errors="replace")
        if "Provisioning" in buf:
            break
        time.sleep(0.1)

    if "Provisioning" not in buf:
        # Send a newline to trigger the menu
        ser.write(b"\n")
        time.sleep(1)
        buf += ser.read(ser.in_waiting).decode("utf-8", errors="replace")

    if "Provisioning" not in buf:
        print("FAIL (no provisioning menu)")
        ser.close()
        return False

    # Select option 1 (set credentials)
    ser.write(b"1\n")
    time.sleep(0.5)

    # Enter DevEUI
    ser.write(f"{format_eui(dev_eui)}\n".encode())
    time.sleep(0.5)

    # Enter AppEUI
    ser.write(f"{format_eui(app_eui)}\n".encode())
    time.sleep(0.5)

    # Enter AppKey
    ser.write(f"{format_eui(app_key)}\n".encode())
    time.sleep(1)

    # Read response
    response = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
    ser.close()

    if "saved" in response.lower() or "ok" in response.lower():
        print("PASS")
        return True
    elif "Provisioning" in response:
        # Might have looped back to menu — check if it accepted
        print("PASS (menu returned)")
        return True
    else:
        print(f"FAIL (response: {response.strip()[:80]})")
        return False


def scan_nodes(ports: list) -> list:
    """Scan serial ports for Sap Watch devices."""
    found = []
    for port in ports:
        try:
            ser = serial.Serial(port, baudrate=115200, timeout=2)
            ser.dtr = False
            time.sleep(0.3)
            ser.dtr = True
            time.sleep(2)
            buf = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
            ser.close()
            if "Sap Watch" in buf:
                found.append(port)
                print(f"  Found Sap Watch on {port}")
        except serial.SerialException:
            pass
    return found


def main():
    parser = argparse.ArgumentParser(description="Sap Watch fleet provisioning")
    parser.add_argument("--nodes", help="CSV file with node list (port,tree_id,sapwood_area)")
    parser.add_argument("--app-eui", required=True, help="LoRaWAN AppEUI (hex)")
    parser.add_argument("--app-key", required=True, help="LoRaWAN AppKey (hex)")
    parser.add_argument("--base-dev-eui", default="70B3D57ED005A1B2",
                        help="Base DevEUI (hex, incremented per node)")
    parser.add_argument("--scan", action="store_true", help="Scan ports for Sap Watch devices")
    parser.add_argument("--ports", help="Comma-separated serial ports to scan")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    if args.scan:
        if not args.ports:
            print("Error: --scan requires --ports", file=sys.stderr)
            sys.exit(1)
        ports = [p.strip() for p in args.ports.split(",")]
        print(f"Scanning {len(ports)} ports for Sap Watch devices...")
        found = scan_nodes(ports)
        print(f"\nFound {len(found)} Sap Watch device(s):")
        for p in found:
            print(f"  {p}")
        sys.exit(0)

    if not args.nodes:
        print("Error: --nodes CSV file required (or use --scan)", file=sys.stderr)
        sys.exit(1)

    # Read node list
    nodes = []
    with open(args.nodes) as f:
        reader = csv.DictReader(f)
        for row in reader:
            nodes.append(row)

    print(f"Provisioning {len(nodes)} Sap Watch nodes...")
    print(f"  AppEUI: {format_eui(args.app_eui)}")
    print(f"  AppKey: {format_eui(args.app_key)}")
    print()

    success = 0
    failed = 0
    for i, node in enumerate(nodes):
        port = node["port"]
        tree_id = node.get("tree_id", f"tree-{i+1}")
        dev_eui = gen_dev_eui(args.base_dev_eui, i + 1)
        print(f"[{i+1}/{len(nodes)}] {tree_id} ({port})")
        ok = provision_node(port, args.app_eui, args.app_key, dev_eui, args.baud)
        if ok:
            success += 1
            # Write back the DevEUI to the CSV
            node["dev_eui"] = dev_eui
        else:
            failed += 1
        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"Provisioning complete: {success} success, {failed} failed")
    print(f"{'='*50}")

    # Write updated CSV with DevEUIs
    if success > 0:
        out_path = args.nodes.replace(".csv", "_provisioned.csv")
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=nodes[0].keys())
            writer.writeheader()
            writer.writerows(nodes)
        print(f"Updated node list: {out_path}")


if __name__ == "__main__":
    main()