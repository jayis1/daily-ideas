#!/usr/bin/env python3
"""
Ping Caliper — material_db.py

View and edit the on-device material velocity database over BLE.

Usage:
    python material_db.py --addr AA:BB:CC:DD:EE:FF --list
    python material_db.py --addr ... --add "Inconel 718" --velocity 5790 --shear 3100 --density 8.19
    python material_db.py --addr ... --set-default 7

Requires: bleak
"""

import argparse
import asyncio
import struct

SVC_NDT      = "6e40fb10-b5a3-f393-e0a9-e50e24dcca9e"
CHR_CMD      = "6e40fb14-b5a3-f393-e0a9-e50e24dcca9e"
CHR_MATERIAL = "6e40fb16-b5a3-f393-e0a9-e50e24dcca9e"

CMD_LIST_MATERIALS = 0x1C
CMD_SET_MATERIAL   = 0x14

# Built-in material table (must match firmware/materials.c)
BUILTIN = [
    ("Steel (mild)",         5920),
    ("Steel (stainless 304)", 5660),
    ("Steel (stainless 316)", 5740),
    ("Steel (carbon 1020)",   5890),
    ("Steel (tool, hardened)", 5900),
    ("Steel (cast)",          4600),
    ("Aluminum (6061)",      6320),
    ("Aluminum (2024)",      6370),
    ("Aluminum (7075)",      6300),
    ("Aluminum (cast A356)", 6710),
    ("Copper",                4760),
    ("Brass (naval)",         4430),
    ("Bronze (phosphor)",     4400),
    ("Titanium (grade 5)",    6100),
    ("Titanium (grade 2)",    6070),
    ("Nickel",                5480),
    ("Monel 400",             5350),
    ("Inconel 625",           5820),
    ("Tungsten",              5180),
    ("Zinc",                  4170),
    ("Lead",                  2160),
    ("Tin",                   3320),
    ("Silver",                3650),
    ("Gold",                  3240),
    ("Magnesium (AZ31B)",     5770),
    ("Beryllium copper",      4700),
    ("Zirconium",             4650),
    ("Cast iron (grey)",      4600),
    ("Cast iron (ductile)",   5600),
    ("Ductile iron",          5600),
    ("Glass (soda-lime)",     5640),
    ("Glass (borosilicate)",  5640),
    ("Glass (fused silica)",  5970),
    ("Acrylic (PMMA)",        2730),
    ("Polycarbonate",         2300),
    ("Nylon 6/6",             2620),
    ("PVC",                   2390),
    ("PTFE (Teflon)",         1350),
    ("HDPE",                  2430),
    ("ABS",                   2240),
    ("Delrin (POM)",          2440),
    ("Carbon fiber laminate", 3200),
    ("Glass fiber laminate",  2750),
    ("Concrete",              4250),
    ("Granite",               5950),
    ("Marble",                6150),
    ("Ceramic (alumina)",    10000),
    ("Ceramic (zirconia)",    7000),
    ("Silicon",               8430),
    ("Water (20C)",           1480),
    ("Ice",                   3980),
    ("Wood (oak, //grain)",    3940),
    ("Wood (pine, //grain)",   5070),
    ("Rubber (neoprene)",      1600),
    ("Rubber (silicone)",       980),
    ("Epoxy resin",            2650),
    ("Aluminum oxide",         9900),
    ("Invar 36",              4590),
    ("Hastelloy C276",        5840),
    ("Stellite",               4500),
    ("Tungsten carbide",       6650),
    ("Beryllium",              12890),
    ("Uranium",                3370),
    ("Diamond",               17500),
]


async def run(addr, action, name, velocity, shear, density, default_idx):
    from bleak import BleakClient

    print(f"Connecting to {addr} ...")
    async with BleakClient(addr, timeout=15.0) as client:
        print("Connected.")

        if action == "list":
            print("\nBuilt-in materials (from firmware):")
            for i, (mname, vel) in enumerate(BUILTIN):
                marker = " *" if i == default_idx else ""
                print(f"  [{i:2d}] {mname:<28s} {vel:5d} m/s{marker}")
            print(f"\n  * = current default (index {default_idx})")
            # Also request the live list from the device
            await client.write_gatt_char(CHR_CMD, bytes([CMD_LIST_MATERIALS]),
                                           response=False)

        elif action == "add":
            if not name or velocity < 500 or velocity > 12000:
                print("Error: provide --name and --velocity (500-12000 m/s)")
                return
            # Pack: index(1, 0xFF=append) + name(23) + velocity(4) + shear(4) + density(4)
            payload = bytes([0xFF])
            name_bytes = name.encode("utf-8")[:23].ljust(23, b"\x00")
            payload += name_bytes
            payload += struct.pack("<I", velocity)
            payload += struct.pack("<I", shear)
            payload += struct.pack("<f", density)
            await client.write_gatt_char(CHR_CMD,
                                          bytes([CMD_SET_MATERIAL]) + payload,
                                          response=False)
            print(f"Added material '{name}' (v={velocity} m/s) to the device.")

        elif action == "set-default":
            if default_idx is None or default_idx >= len(BUILTIN):
                print("Error: invalid index")
                return
            payload = bytes([default_idx])
            payload += BUILTIN[default_idx][0].encode("utf-8")[:23].ljust(23, b"\x00")
            await client.write_gatt_char(CHR_MATERIAL, payload, response=True)
            print(f"Default material set to [{default_idx}] {BUILTIN[default_idx][0]}")


def main():
    p = argparse.ArgumentParser(description="Ping Caliper material database tool")
    p.add_argument("--addr", required=True, help="BLE MAC address")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="List all materials")
    g.add_argument("--add", action="store_true", help="Add a custom material")
    g.add_argument("--set-default", action="store_true", help="Set default material")
    p.add_argument("--name", help="Material name (for --add)")
    p.add_argument("--velocity", type=int, help="Longitudinal velocity (m/s)")
    p.add_argument("--shear", type=int, default=0, help="Shear velocity (m/s)")
    p.add_argument("--density", type=float, default=1.0, help="Density (g/cm³)")
    p.add_argument("--index", type=int, help="Material index (for --set-default)")
    args = p.parse_args()
    action = "list" if args.list else "add" if args.add else "set-default"
    try:
        asyncio.run(run(args.addr, action, args.name, args.velocity or 0,
                          args.shear, args.density, args.index))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()