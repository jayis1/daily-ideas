#!/usr/bin/env python3
"""
Thermo Trace — Calibration script.

Performs one-point (indium) or two-point (indium + tin) calibration of
the Thermo Trace pocket DSC. Connects via BLE, retrieves the scan data,
detects the reference standard's melting peak, computes correction
coefficients, and sends them to the device.

Usage:
    # One-point calibration with indium
    python calibrate.py --indium

    # Two-point calibration with indium + tin
    python calibrate.py --indium --tin

    # Specify device MAC
    python calibrate.py --indium --device AA:BB:CC:DD:EE:FF

Requirements:
    pip install bleak numpy
"""

import argparse
import asyncio
import struct
import time
import numpy as np

# Import the BLE infrastructure from the companion app
from thermo_trace_app import ThermoTraceDevice, NUS_RX_CHAR_UUID, crc8, SYNC1, SYNC2, MSG_CALIB

# Reference standard values
STANDARDS = {
    'indium': {
        'Tm': 156.6,   # °C
        'dH': 28.71,   # J/g
        'name': 'Indium',
    },
    'tin': {
        'Tm': 231.9,
        'dH': 60.22,
        'name': 'Tin',
    },
    'gallium': {
        'Tm': 29.8,
        'dH': 80.1,
        'name': 'Gallium',
    },
    'water': {
        'Tm': 0.0,
        'dH': 334.0,
        'name': 'Water (ice)',
    },
}


def detect_melting_peak(temps, heat_flows):
    """Detect the primary endothermic melting peak in DSC data."""
    if len(temps) < 20:
        return None, None, None

    temps = np.array(temps)
    heat_flows = np.array(heat_flows)

    # Baseline correction
    n = len(heat_flows)
    baseline = np.linspace(np.mean(heat_flows[:10]), np.mean(heat_flows[-10:]), n)
    corrected = heat_flows - baseline

    # Find the largest endothermic (positive) peak
    peak_idx = np.argmax(corrected)
    peak_height = corrected[peak_idx]
    peak_temp = temps[peak_idx]

    if peak_height < 0.1:
        return None, None, None

    # Find onset: where derivative first goes positive before peak
    onset_idx = peak_idx
    for i in range(peak_idx, 2, -1):
        if corrected[i] <= 0.05 * peak_height:
            onset_idx = i
            break

    # Find end: where derivative returns to baseline after peak
    end_idx = peak_idx
    for i in range(peak_idx, n - 2):
        if corrected[i] <= 0.05 * peak_height:
            end_idx = i
            break

    # Integrate for enthalpy (trapezoidal)
    # Assuming 5°C/min ramp: dt = dT / (rate/60)
    # We need actual time data for accurate integration
    # For now, approximate from temperature spacing
    dT = temps[1] - temps[0] if len(temps) > 1 else 1.0
    rate_per_s = 5.0 / 60.0  # 5°C/min = 0.0833°C/s
    dt_seconds = dT / rate_per_s if rate_per_s > 0 else 1.0

    area = np.trapz(corrected[onset_idx:end_idx], dx=dt_seconds)  # mW·s = mJ
    enthalpy = area * 0.001  # J (assuming 1g sample; will normalize later)

    return peak_temp, peak_height, enthalpy


def compute_correction(standards_measured):
    """
    Compute correction coefficients from measured vs. expected values.

    standards_measured: list of (T_measured, T_expected, dH_measured, dH_expected)

    Returns:
        temp_a, temp_b: T_corrected = a * T_measured + b
        flow_c, flow_d:  Φ_corrected = c * Φ_measured + d
    """
    if not standards_measured:
        raise ValueError("No standards measured")

    T_meas = np.array([s[0] for s in standards_measured])
    T_exp = np.array([s[1] for s in standards_measured])
    dH_meas = np.array([s[2] for s in standards_measured])
    dH_exp = np.array([s[3] for s in standards_measured])

    # Temperature: linear fit T_corrected = a * T_measured + b
    if len(standards_measured) >= 2:
        # Two-point linear fit
        coeffs = np.polyfit(T_meas, T_exp, 1)
        temp_a = float(coeffs[0])
        temp_b = float(coeffs[1])
    else:
        # One-point: assume slope = 1, adjust offset
        temp_a = 1.0
        temp_b = float(T_exp[0] - T_meas[0])

    # Heat flow: scale by ratio of expected/measured enthalpy
    if len(standards_measured) >= 2 and dH_meas[0] > 0 and dH_meas[1] > 0:
        # Two-point linear fit for heat flow
        flow_coeffs = np.polyfit(dH_meas, dH_exp, 1)
        flow_c = float(flow_coeffs[0])
        flow_d = float(flow_coeffs[1])
    elif dH_meas[0] > 0:
        # One-point: scale factor only
        flow_c = float(dH_exp[0] / dH_meas[0])
        flow_d = 0.0
    else:
        flow_c = 1.0
        flow_d = 0.0

    return temp_a, temp_b, flow_c, flow_d


async def send_calibration(device, t_measured, t_expected, correction):
    """Send calibration coefficients to the device via BLE."""
    # Build BLE_MSG_CALIB frame
    payload = struct.pack('<fff', t_measured, t_expected, correction)
    frame = bytes([SYNC1, SYNC2, MSG_CALIB, len(payload)]) + payload
    crc = crc8(bytes([MSG_CALIB, len(payload)]) + payload)
    frame += bytes([crc])

    await device.client.write_gatt_char(NUS_RX_CHAR_UUID, frame, response=True)
    print(f"  Sent calibration: T_meas={t_measured:.1f}, T_exp={t_expected:.1f}, "
          f"corr={correction:.4f}")


async def run_calibration(args):
    """Run the calibration procedure."""
    device = ThermoTraceDevice()
    await device.connect(args.device)

    print("\n=== Thermo Trace Calibration ===\n")

    standards_measured = []

    for std_name in ['indium', 'tin']:
        if std_name == 'indium' and not args.indium:
            continue
        if std_name == 'tin' and not args.tin:
            continue

        std = STANDARDS[std_name]
        print(f"\n--- {std['name']} Calibration ---")
        print(f"  Expected: Tm = {std['Tm']:.1f}°C, ΔH = {std['dH']:.2f} J/g")
        print(f"  Please load {std_name} sample ({args.mass} mg) and run a scan.")
        print(f"  Waiting for scan data... (timeout: {args.timeout}s)")

        # Clear previous data
        device.data_points = []
        device.scan_done = False

        # Wait for scan to complete
        start = time.time()
        while not device.scan_done and time.time() - start < args.timeout:
            await asyncio.sleep(0.5)
            if device.data_points and len(device.data_points) % 100 == 0:
                print(f"  Received {len(device.data_points)} data points...")

        if not device.data_points:
            print("  ERROR: No data received!")
            continue

        print(f"  Received {len(device.data_points)} data points.")

        # Detect melting peak
        temps = [pt.temperature for pt in device.data_points]
        heat_flows = [pt.heat_flow for pt in device.data_points]
        peak_temp, peak_height, enthalpy = detect_melting_peak(temps, heat_flows)

        if peak_temp is None:
            print(f"  ERROR: No melting peak detected for {std_name}!")
            continue

        # Normalize enthalpy by sample mass
        enthalpy_per_g = enthalpy / (args.mass / 1000.0) if args.mass > 0 else 0

        print(f"  Measured: Tm = {peak_temp:.1f}°C, ΔH ≈ {enthalpy_per_g:.2f} J/g")
        print(f"  Error: ΔT = {peak_temp - std['Tm']:.1f}°C, "
              f"ΔH error = {enthalpy_per_g - std['dH']:.2f} J/g")

        standards_measured.append((
            peak_temp, std['Tm'],
            enthalpy_per_g, std['dH']
        ))

    if not standards_measured:
        print("\nNo standards measured successfully. Cannot calibrate.")
        await device.disconnect()
        return

    # Compute correction coefficients
    print("\n--- Computing Correction Coefficients ---")
    temp_a, temp_b, flow_c, flow_d = compute_correction(standards_measured)

    print(f"\n  Temperature correction: T_corr = {temp_a:.4f} × T_meas + {temp_b:.4f}")
    print(f"  Heat flow correction:    Φ_corr = {flow_c:.4f} × Φ_meas + {flow_d:.4f}")

    # Verify: apply correction to measured values
    print("\n  Verification:")
    for T_meas, T_exp, dH_meas, dH_exp in standards_measured:
        T_corr = temp_a * T_meas + temp_b
        dH_corr = flow_c * dH_meas + flow_d
        print(f"    Tm: {T_meas:.1f} → {T_corr:.1f}°C (expected {T_exp:.1f}°C, "
              f"error {T_corr - T_exp:.2f}°C)")
        print(f"    ΔH: {dH_meas:.1f} → {dH_corr:.1f} J/g (expected {dH_exp:.1f} J/g, "
              f"error {dH_corr - dH_exp:.2f} J/g)")

    # Send to device
    if not args.dry_run:
        print("\n  Sending coefficients to device...")
        await send_calibration(device, temp_a, temp_b, flow_c)
        print("  Calibration complete! Coefficients stored in device flash.")
    else:
        print("\n  [DRY RUN] Skipping device write.")

    # Save to file
    with open('calibration_coeffs.txt', 'w') as f:
        f.write(f"# Thermo Trace Calibration Coefficients\n")
        f.write(f"# Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Standards: {', '.join(s[1] for s in standards_measured)}\n")
        f.write(f"temp_a = {temp_a}\n")
        f.write(f"temp_b = {temp_b}\n")
        f.write(f"flow_c = {flow_c}\n")
        f.write(f"flow_d = {flow_d}\n")
    print("  Saved to calibration_coeffs.txt")

    await device.disconnect()


def main():
    parser = argparse.ArgumentParser(description='Thermo Trace calibration')
    parser.add_argument('--indium', action='store_true',
                        help='Calibrate with indium standard (Tm=156.6°C)')
    parser.add_argument('--tin', action='store_true',
                        help='Calibrate with tin standard (Tm=231.9°C)')
    parser.add_argument('--device', '-d', type=str, default=None,
                        help='Device MAC address')
    parser.add_argument('--mass', '-m', type=float, default=5.0,
                        help='Sample mass in mg (default: 5.0)')
    parser.add_argument('--timeout', '-t', type=int, default=3600,
                        help='Scan timeout in seconds (default: 3600)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Compute coefficients without sending to device')
    args = parser.parse_args()

    if not args.indium and not args.tin:
        print("Error: specify at least one standard (--indium and/or --tin)")
        return

    asyncio.run(run_calibration(args))


if __name__ == '__main__':
    main()