#!/usr/bin/env python3
"""
calibrate.py — Ion Sprint calibration script

Sends a series of standard concentrations via BLE, records peak
areas, and computes response factors for the internal-standard
quantification method.

Usage:
    python3 calibrate.py --standards standards.json [--mac AA:BB:CC:DD:EE:FF]

standards.json format:
    [
        {"ion": "K+", "concentrations_mM": [0.1, 0.5, 1.0, 5.0], "areas": []},
        {"ion": "Na+", "concentrations_mM": [0.1, 0.5, 1.0, 5.0], "areas": []}
    ]

After running, this script fills in the "areas" field and computes
response factors relative to the internal standard (Ba2+).
"""

import argparse
import asyncio
import json
import struct
import numpy as np
from typing import Optional, List

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install bleak: pip install bleak")
    exit(1)

SERVICE_UUID = "0000fe21-0000-1000-8000-00805f9b34fb"
EPH_UUID     = "0000fe22-0000-1000-8000-00805f9b34fb"
RESULTS_UUID = "0000fe23-0000-1000-8000-00805f9b34fb"
COMMAND_UUID = "0000fe24-0000-1000-8000-00805f9b34fb"

CMD_START = 0x01
CMD_ABORT = 0x02
CMD_SET_HV = 0x03
CMD_SET_BGE = 0x04
CMD_SET_INJ = 0x05

PKT_START = 0xAA
PKT_RESULTS = 0x02


def crc8(data: bytes) -> int:
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


class Calibrator:
    def __init__(self, mac: Optional[str] = None):
        self.mac = mac
        self.latest_results = []
        self.run_complete = asyncio.Event()

    def on_notify(self, sender, data: bytes):
        if len(data) < 5 or data[0] != PKT_START:
            return
        pkt_type = data[1]
        pkt_len = (data[2] << 8) | data[3]
        payload = data[4:4 + pkt_len]
        if crc8(payload) != data[4 + pkt_len]:
            return
        if pkt_type == PKT_RESULTS:
            run_id = struct.unpack_from('<H', payload, 0)[0]
            count = payload[2]
            results = []
            offset = 3
            for _ in range(count):
                ion_id = payload[offset]
                ion_name = payload[offset+1:offset+13].decode('ascii',
                    errors='replace').strip('\x00')
                mt, area, conc = struct.unpack_from('<fff', payload, offset + 13)
                results.append({'ion': ion_name, 'mt': mt, 'area': area,
                               'conc': conc})
                offset += 25
            self.latest_results = results
            self.run_complete.set()

    async def find_device(self) -> Optional[str]:
        if self.mac:
            return self.mac
        print("Scanning for Ion Sprint...")
        devices = await BleakScanner.discover(timeout=10)
        for d in devices:
            if "Ion Sprint" in (d.name or ""):
                return d.address
        return None

    async def run_standard(self, client, hv_kv: float, bge: int,
                          inj_mode: int) -> List[dict]:
        """Run one standard and wait for results."""
        self.latest_results = []
        self.run_complete.clear()

        # Set parameters
        await client.write_gatt_char(COMMAND_UUID,
            bytes([CMD_SET_HV]) + struct.pack('<f', hv_kv))
        await client.write_gatt_char(COMMAND_UUID,
            bytes([CMD_SET_BGE, bge]))
        await client.write_gatt_char(COMMAND_UUID,
            bytes([CMD_SET_INJ, inj_mode]))

        # Start run
        await client.write_gatt_char(COMMAND_UUID, bytes([CMD_START]))

        # Wait for results (timeout 10 min)
        try:
            await asyncio.wait_for(self.run_complete.wait(), timeout=600)
        except asyncio.TimeoutError:
            print("  Run timed out!")
            return []

        return self.latest_results

    async def calibrate(self, standards_file: str, output_file: str,
                       hv_kv: float, bge: int, inj_mode: int):
        mac = await self.find_device()
        if mac is None:
            print("Ion Sprint not found!")
            return

        with open(standards_file) as f:
            standards = json.load(f)

        print(f"Connecting to {mac}...")
        async with BleakClient(mac) as client:
            await client.start_notify(RESULTS_UUID, self.on_notify)

            # Run each standard
            for std in standards:
                ion = std['ion']
                concs = std['concentrations_mM']
                areas = []
                print(f"\nCalibrating {ion} ({len(concs)} concentrations)...")
                for conc in concs:
                    print(f"  Running {conc} mM standard...")
                    print(f"  Prepare {conc} mM {ion} standard, press Enter when ready.")
                    # In automated mode, skip input:
                    # input()
                    results = await self.run_standard(client, hv_kv, bge, inj_mode)
                    # Find the peak for this ion
                    found = False
                    for r in results:
                        if r['ion'] == ion:
                            areas.append(r['area'])
                            found = True
                            break
                    if not found:
                        areas.append(0.0)
                        print(f"  WARNING: {ion} not detected!")

                std['areas'] = areas

                # Compute linear regression: area = slope * conc + intercept
                if len(concs) >= 2:
                    slope, intercept = np.polyfit(concs, areas, 1)
                    std['slope'] = float(slope)
                    std['intercept'] = float(intercept)
                    r_sq = float(np.corrcoef(concs, areas)[0, 1] ** 2)
                    std['r_squared'] = r_sq
                    print(f"  Slope: {slope:.4f}, R²: {r_sq:.4f}")

            await client.stop_notify(RESULTS_UUID)

        # Compute response factors relative to Ba2+ (internal standard)
        ba_slope = None
        for std in standards:
            if std['ion'] == 'Ba2+':
                ba_slope = std.get('slope', 0)
                break

        if ba_slope and ba_slope > 0:
            for std in standards:
                if std['ion'] != 'Ba2+' and 'slope' in std:
                    std['response_factor'] = std['slope'] / ba_slope
                    print(f"  {std['ion']}: RF = {std['response_factor']:.4f}")

        # Save results
        with open(output_file, 'w') as f:
            json.dump(standards, f, indent=2)
        print(f"\nCalibration saved to {output_file}")

        # Generate C code for response_factors[]
        print("\n--- Paste into quant.c response_factors[] ---")
        for std in standards:
            rf = std.get('response_factor', 1.0)
            print(f'    {rf:.4f}f,  /* {std["ion"]} */')


def main():
    parser = argparse.ArgumentParser(
        description='Ion Sprint calibration script')
    parser.add_argument('--standards', type=str, required=True,
                       help='JSON file with standard definitions')
    parser.add_argument('--output', type=str, default='calibration.json',
                       help='Output calibration file')
    parser.add_argument('--mac', type=str, default=None,
                       help='BLE MAC address')
    parser.add_argument('--hv', type=float, default=20.0,
                       help='HV voltage (kV)')
    parser.add_argument('--bge', type=int, default=0,
                       help='BGE recipe index')
    parser.add_argument('--inj', type=int, default=0,
                       help='Injection mode (0=EK, 1=HD)')
    args = parser.parse_args()

    cal = Calibrator(mac=args.mac)
    asyncio.run(cal.calibrate(args.standards, args.output,
                             args.hv, args.bge, args.inj))


if __name__ == '__main__':
    main()