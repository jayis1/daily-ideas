#!/usr/bin/env python3
"""
experiment.py — Scripted experiment runner for QCM Halo binding kinetics

Automates a biomolecular binding kinetics experiment:
1. Establish baseline (buffer flow)
2. Inject analyte (association phase)
3. Switch back to buffer (dissociation phase)
4. Fit 1:1 Langmuir model to extract kon, koff, KD

Usage:
    python3 experiment.py --analyte "BSA 1uM" --baseline 60 --assoc 300 --dissoc 300

Requires: bleak, numpy, scipy
"""

import asyncio
import struct
import sys
import time
import argparse

try:
    import numpy as np
    from scipy.optimize import curve_fit
    from bleak import BleakClient, BleakScanner
except ImportError:
    print("Install: pip install bleak numpy scipy")
    sys.exit(1)

SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
TX_CHAR_UUID  = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
RX_CHAR_UUID  = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

SYNC0, SYNC1 = 0xA5, 0x5A

def crc8(data):
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) if (crc & 0x80) else (crc << 1)
            crc &= 0xFF
    return crc

def make_frame(cmd, payload=b''):
    frame = bytes([SYNC0, SYNC1, cmd, len(payload)]) + payload
    return frame + bytes([crc8(frame[2:])])

# Experiment data
time_data = []
delta_f_data = []
rx_buffer = bytearray()
start_time = 0

def notification_handler(sender, data):
    global rx_buffer
    rx_buffer.extend(data)
    i = 0
    while i < len(rx_buffer) - 4:
        if rx_buffer[i] == SYNC0 and rx_buffer[i+1] == SYNC1:
            cmd = rx_buffer[i+2]
            plen = rx_buffer[i+3]
            if i + 5 + plen <= len(rx_buffer):
                payload = rx_buffer[i+4:i+4+plen]
                if rx_buffer[i+4+plen] == crc8(rx_buffer[i+2:i+4+plen]):
                    if cmd == 0x01 and len(payload) >= 6:
                        df = struct.unpack_from('<f', payload, 2)[0]
                        t = time.time() - start_time
                        time_data.append(t)
                        delta_f_data.append(df)
                    i += 5 + plen
                    continue
        i += 1
    rx_buffer[:] = rx_buffer[i:]

def langmuir_association(t, Rmax, kon, koff, C):
    """1:1 Langmuir binding: R(t) = Rmax * C * kon / (C*kon + koff) * (1 - exp(-(C*kon+koff)*t))"""
    rate = C * kon + koff
    return Rmax * C * kon / rate * (1 - np.exp(-rate * t))

def langmuir_dissociation(t, R0, koff):
    """Dissociation: R(t) = R0 * exp(-koff * t)"""
    return R0 * np.exp(-koff * t)

def fit_kinetics(time_arr, df_arr, baseline_end, assoc_end):
    """Fit binding kinetics to Δf data."""
    # Baseline correction
    baseline = np.mean(df_arr[:baseline_end])
    df_corr = df_arr - baseline

    # Association phase
    t_assoc = time_arr[baseline_end:assoc_end] - time_arr[baseline_end]
    df_assoc = df_corr[baseline_end:assoc_end]

    # Dissociation phase
    t_dissoc = time_arr[assoc_end:] - time_arr[assoc_end]
    df_dissoc = df_corr[assoc_end:]

    results = {}

    # Fit dissociation first (simpler: single exponential)
    try:
        R0_init = df_dissoc[0] if len(df_dissoc) > 0 else 1.0
        popt, _ = curve_fit(langmuir_dissociation, t_dissoc, df_dissoc,
                           p0=[R0_init, 0.01], maxfev=10000)
        results['R0'] = popt[0]
        results['koff'] = abs(popt[1])
        print(f"  koff = {results['koff']:.4e} s⁻¹")
    except Exception as e:
        print(f"  Dissociation fit failed: {e}")
        results['koff'] = 0

    # Fit association (needs kon + koff)
    try:
        C = 1e-6  # 1 µM analyte concentration
        popt, _ = curve_fit(lambda t, Rmax, kon: langmuir_association(t, Rmax, kon, results.get('koff', 0.01), C),
                           t_assoc, df_assoc, p0=[abs(df_assoc[-1]), 1e3], maxfev=10000)
        results['Rmax'] = popt[0]
        results['kon'] = abs(popt[1])
        print(f"  kon  = {results['kon']:.4e} M⁻¹s⁻¹")
        print(f"  Rmax = {results['Rmax']:.2f} Hz")

        if results['koff'] > 0:
            results['KD'] = results['koff'] / results['kon']
            print(f"  KD   = {results['KD']:.4e} M")
    except Exception as e:
        print(f"  Association fit failed: {e}")

    return results

async def run_experiment(args):
    global start_time

    print("Scanning for QCM Halo...")
    devices = await BleakScanner.discover()
    target = None
    for d in devices:
        if "QCM" in (d.name or ""):
            target = d
            break

    if not target:
        print("QCM Halo not found!")
        return

    print(f"Found: {target.name}")
    print(f"Experiment: {args.analyte}")
    print(f"  Baseline:  {args.baseline}s")
    print(f"  Association: {args.assoc}s")
    print(f"  Dissociation: {args.dissoc}s")

    async with BleakClient(target) as client:
        await client.start_notify(RX_CHAR_UUID, notification_handler)

        # Set temperature
        temp_bytes = struct.pack('<f', args.temp)
        await client.write_gatt_char(TX_CHAR_UUID,
            make_frame(0x85, temp_bytes), response=True)
        await asyncio.sleep(5)

        # Set pump rate
        rate_bytes = struct.pack('<f', args.pump_rate)
        await client.write_gatt_char(TX_CHAR_UUID,
            make_frame(0x86, rate_bytes), response=True)

        # Set valve to buffer (position 0)
        await client.write_gatt_char(TX_CHAR_UUID,
            make_frame(0x87, bytes([0])), response=True)

        # Start streaming
        dur_bytes = struct.pack('<I', args.baseline + args.assoc + args.dissoc)
        await client.write_gatt_char(TX_CHAR_UUID,
            make_frame(0x89, dur_bytes), response=True)

        start_time = time.time()

        # Phase 1: Baseline
        print(f"\n[{0:.0f}s] Baseline phase (buffer)...")
        await asyncio.sleep(args.baseline)
        baseline_end = len(time_data)

        # Phase 2: Association — switch to analyte valve (position 1)
        print(f"[{args.baseline:.0f}s] Association phase ({args.analyte})...")
        await client.write_gatt_char(TX_CHAR_UUID,
            make_frame(0x87, bytes([1])), response=True)
        await asyncio.sleep(args.assoc)
        assoc_end = len(time_data)

        # Phase 3: Dissociation — switch back to buffer
        print(f"[{args.baseline + args.assoc:.0f}s] Dissociation phase (buffer)...")
        await client.write_gatt_char(TX_CHAR_UUID,
            make_frame(0x87, bytes([0])), response=True)
        await asyncio.sleep(args.dissoc)

        # Stop
        await client.write_gatt_char(TX_CHAR_UUID, make_frame(0x82), response=True)
        await client.stop_notify(RX_CHAR_UUID)

    print(f"\n=== Experiment Complete ({len(time_data)} points) ===")

    # Fit kinetics
    if len(time_data) > 10:
        print("\n=== Binding Kinetics Analysis ===")
        t_arr = np.array(time_data)
        df_arr = np.array(delta_f_data)
        results = fit_kinetics(t_arr, df_arr, baseline_end, assoc_end)

        # Save data
        filename = f"experiment_{int(time.time())}.csv"
        with open(filename, 'w') as f:
            f.write(f"# Experiment: {args.analyte}\n")
            f.write(f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("time_s,delta_f_Hz\n")
            for t, d in zip(time_data, delta_f_data):
                f.write(f"{t:.2f},{d:.3f}\n")
        print(f"\nData saved: {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='QCM Halo binding kinetics experiment')
    parser.add_argument('--analyte', default='Sample', help='Analyte name')
    parser.add_argument('--baseline', type=int, default=60, help='Baseline duration (s)')
    parser.add_argument('--assoc', type=int, default=300, help='Association duration (s)')
    parser.add_argument('--dissoc', type=int, default=300, help='Dissociation duration (s)')
    parser.add_argument('--temp', type=float, default=25.0, help='Temperature (°C)')
    parser.add_argument('--pump_rate', type=float, default=2.0, help='Flow rate (mL/min)')
    args = parser.parse_args()

    asyncio.run(run_experiment(args))