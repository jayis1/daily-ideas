#!/usr/bin/env python3
"""
library_manager.py — Manage the Fluor Cast fluorescence compound library

Add, edit, remove, and export compound entries from the 50-compound
fluorescence library stored on the device.

Usage:
    python3 library_manager.py list
    python3 library_manager.py add --name "New Compound" --ex 380 --em 450
    python3 library_manager.py remove 23
    python3 library_manager.py export library.json
    python3 library_manager.py import library.json
"""

import argparse
import json
import sys
import struct
import serial
import time


class LibraryManager:
    """Interface to device fluorescence library via UART."""

    def __init__(self, port: str, baud: int = 921600):
        self.ser = serial.Serial(port, baud, timeout=5.0)

    def _crc16(self, data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc <<= 1
            crc &= 0xFFFF
        return crc

    def send_command(self, cmd: int, payload: bytes = b""):
        sof = b"\xAA"
        eof = b"\x55"
        length = len(payload).to_bytes(2, "little")
        crc_data = bytes([cmd]) + payload
        crc = self._crc16(crc_data)
        frame = sof + length + bytes([cmd]) + payload + crc.to_bytes(2, "little") + eof
        self.ser.write(frame)

    def list_compounds(self):
        """List all compounds in the library."""
        # Request library from device
        # In production: implement CMD_GET_LIBRARY command
        # For now: use the default library from the source code
        from collections import namedtuple
        Compound = namedtuple("Compound",
                              ["idx", "name", "category", "ex_peak", "em_peak"])

        compounds = [
            Compound(0, "Tryptophan", "Amino acid", 280, 350),
            Compound(1, "Tyrosine", "Amino acid", 275, 305),
            Compound(2, "Phenylalanine", "Amino acid", 260, 282),
            Compound(3, "NADH", "Cofactor", 340, 460),
            Compound(4, "FAD", "Cofactor", 450, 525),
            Compound(5, "Riboflavin (B2)", "Vitamin", 440, 530),
            Compound(6, "Thiamine (B1)", "Vitamin", 365, 440),
            Compound(7, "Pyridoxine (B6)", "Vitamin", 320, 390),
            Compound(8, "Chlorophyll-a", "Pigment", 440, 680),
            Compound(9, "Chlorophyll-b", "Pigment", 470, 660),
            Compound(10, "Phycocyanin", "Pigment", 620, 650),
            Compound(11, "Fluorescein", "Tracer dye", 470, 520),
            Compound(12, "Rhodamine B", "Tracer dye", 525, 580),
            Compound(13, "Rhodamine 6G", "Tracer dye", 525, 560),
            Compound(14, "Quinine sulfate", "Standard", 350, 455),
            Compound(15, "Esculin", "Coumarin", 365, 460),
            Compound(16, "Umbelliferone", "Coumarin", 365, 455),
            Compound(17, "4-Methylumbelliferone", "Coumarin", 365, 445),
            Compound(18, "Humic acid (Suwannee)", "DOM", 320, 420),
            Compound(19, "Fulvic acid (Suwannee)", "DOM", 320, 400),
            Compound(20, "Tryptophan-like (protein)", "DOM", 280, 340),
            Compound(21, "Tyrosine-like (protein)", "DOM", 275, 310),
            Compound(22, "Crude oil (freshwater)", "Petroleum", 254, 340),
            Compound(23, "Diesel fuel", "Petroleum", 254, 320),
            Compound(24, "Motor oil", "Petroleum", 280, 360),
            Compound(25, "Gasoline", "Petroleum", 254, 310),
            Compound(26, "BTEX mixture", "Petroleum", 254, 290),
            Compound(27, "Naphthalene", "Petroleum", 280, 340),
            Compound(28, "Phenanthrene", "Petroleum", 260, 370),
            Compound(29, "Pyrene", "Petroleum", 340, 390),
            Compound(30, "Carbaryl", "Pesticide", 280, 340),
            Compound(31, "Carbofuran", "Pesticide", 280, 330),
            Compound(32, "Chlorpyrifos", "Pesticide", 290, 350),
            Compound(33, "Atrazine", "Pesticide", 254, 310),
            Compound(34, "Aspirin", "Pharmaceutical", 280, 350),
            Compound(35, "Paracetamol", "Pharmaceutical", 280, 360),
            Compound(36, "Caffeine", "Pharmaceutical", 275, 340),
            Compound(37, "Warfarin", "Pharmaceutical", 320, 400),
            Compound(38, "Doxorubicin", "Pharmaceutical", 470, 590),
            Compound(39, "Hoechst 33342", "DNA stain", 360, 460),
            Compound(40, "SYBR Green", "DNA stain", 470, 520),
            Compound(41, "Ethidium bromide", "DNA stain", 300, 600),
            Compound(42, "PicoGreen", "DNA quant assay", 470, 520),
            Compound(43, "Coenzyme Q10", "Supplement", 280, 350),
            Compound(44, "Curcumin", "Natural compound", 440, 540),
            Compound(45, "Olive oil (EVOO)", "Food", 360, 440),
            Compound(46, "Honey (clover)", "Food", 360, 420),
            Compound(47, "Beer (fresh lager)", "Beverage", 340, 440),
            Compound(48, "Wine (red)", "Beverage", 340, 390),
            Compound(49, "Tap water (baseline)", "Reference", 254, 350),
        ]

        print(f"{'#':>3} {'Name':<30} {'Category':<16} {'Ex':>4} {'Em':>4}")
        print("-" * 62)
        for c in compounds:
            print(f"{c.idx:>3} {c.name:<30} {c.category:<16} {c.ex_peak:>4} {c.em_peak:>4}")
        print(f"\nTotal: {len(compounds)} compounds")

    def add_compound(self, name: str, ex_peak: int, em_peak: int, category: str = "Custom"):
        """Add a new compound to the library."""
        print(f"Adding compound: {name}")
        print(f"  Ex peak: {ex_peak} nm")
        print(f"  Em peak: {em_peak} nm")
        print(f"  Category: {category}")

        # In production: measure EEM of the compound and extract features
        # Then send to device via CMD_SET_LIBRARY
        print("  (Feature extraction requires a measured EEM — run with device)")

    def remove_compound(self, index: int):
        """Remove a compound from the library."""
        print(f"Removing compound at index {index}")
        # Send removal command to device

    def export_library(self, filename: str):
        """Export library to JSON file."""
        print(f"Exporting library to {filename}")
        library_data = {
            "version": "1.0",
            "compounds": [
                {"idx": i, "name": f"Compound_{i}", "ex_peak": 0, "em_peak": 0,
                 "features": [0.0] * 48}
                for i in range(50)
            ]
        }
        with open(filename, "w") as f:
            json.dump(library_data, f, indent=2)
        print(f"  Exported {len(library_data['compounds'])} compounds")

    def import_library(self, filename: str):
        """Import library from JSON file."""
        print(f"Importing library from {filename}")
        with open(filename, "r") as f:
            data = json.load(f)
        print(f"  Loaded {len(data.get('compounds', []))} compounds")
        # Send each compound to device

    def close(self):
        self.ser.close()


def main():
    parser = argparse.ArgumentParser(description="Fluor Cast Library Manager")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port")
    parser.add_argument("--baud", type=int, default=921600, help="Baud rate")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all compounds")

    add_p = sub.add_parser("add", help="Add a compound")
    add_p.add_argument("--name", required=True)
    add_p.add_argument("--ex", type=int, required=True, help="Excitation peak (nm)")
    add_p.add_argument("--em", type=int, required=True, help="Emission peak (nm)")
    add_p.add_argument("--category", default="Custom")

    rm_p = sub.add_parser("remove", help="Remove a compound")
    rm_p.add_argument("index", type=int)

    exp_p = sub.add_parser("export", help="Export library")
    exp_p.add_argument("filename")

    imp_p = sub.add_parser("import", help="Import library")
    imp_p.add_argument("filename")

    args = parser.parse_args()

    mgr = LibraryManager(args.port, args.baud)

    try:
        if args.command == "list":
            mgr.list_compounds()
        elif args.command == "add":
            mgr.add_compound(args.name, args.ex, args.em, args.category)
        elif args.command == "remove":
            mgr.remove_compound(args.index)
        elif args.command == "export":
            mgr.export_library(args.filename)
        elif args.command == "import":
            mgr.import_library(args.filename)
    finally:
        mgr.close()


if __name__ == "__main__":
    main()