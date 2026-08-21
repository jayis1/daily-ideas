#!/usr/bin/env python3
"""
hall-puck / scripts / analyze_log.py
Post-measurement analysis of Hall Puck CSV log files.

Parses a CSV log, recomputes transport parameters from the raw
voltage/current data, and generates publication-quality plots.

Usage:
    python3 analyze_log.py HP_20260729_101530.csv
    python3 analyze_log.py HP_20260729_101530.csv --output result.png

Requires: numpy, matplotlib, scipy
    pip install numpy matplotlib scipy
"""

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import newton


@dataclass
class LogHeader:
    date: str = ""
    sample: str = ""
    thickness: float = 0.5  # mm
    temperature: float = 24.3  # C
    b_field: float = 0.482  # T
    current: float = 1.0  # mA


@dataclass
class LogResult:
    sheet_resistance: float = 0.0
    hall_coefficient: float = 0.0
    carrier_conc: float = 0.0
    mobility: float = 0.0
    resistivity: float = 0.0
    carrier_type: str = "unknown"


@dataclass
class LogPoint:
    step: int = 0
    config: str = ""
    current_ma: float = 0.0
    voltage_uv: float = 0.0
    b_field: float = 0.0
    note: str = ""


def parse_log(filename: str):
    header = LogHeader()
    result = LogResult()
    points: List[LogPoint] = []

    with open(filename, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith('#'):
                # Parse header comments
                line = ','.join(row)
                if 'Thickness:' in line:
                    m = re.search(r'Thickness:\s*([\d.]+)', line)
                    if m: header.thickness = float(m.group(1))
                elif 'Temperature:' in line:
                    m = re.search(r'Temperature:\s*([\d.]+)', line)
                    if m: header.temperature = float(m.group(1))
                elif 'B-field:' in line:
                    m = re.search(r'B-field:\s*([\d.]+)', line)
                    if m: header.b_field = float(m.group(1))
                elif 'Current:' in line:
                    m = re.search(r'Current:\s*([\d.]+)', line)
                    if m: header.current = float(m.group(1))
                elif 'Result:' in line:
                    m = re.search(r'Rs=([\d.]+)', line)
                    if m: result.sheet_resistance = float(m.group(1))
                    m = re.search(r'RH=([-\d.]+)', line)
                    if m: result.hall_coefficient = float(m.group(1))
                    m = re.search(r'n=([\d.eE+-]+)', line)
                    if m: result.carrier_conc = float(m.group(1))
                    m = re.search(r'mu=([\d.]+)', line)
                    if m: result.mobility = float(m.group(1))
                continue

            # Parse data rows
            if len(row) >= 5:
                try:
                    pt = LogPoint(
                        step=int(row[0]),
                        config=row[1].strip(),
                        current_ma=float(row[2]),
                        voltage_uv=float(row[3]),
                        b_field=float(row[4]),
                        note=row[5].strip() if len(row) > 5 else "",
                    )
                    points.append(pt)
                except (ValueError, IndexError):
                    pass

    return header, result, points


def vdp_solve_rs(ra: float, rb: float) -> float:
    """Solve the Van der Pauw equation for sheet resistance."""
    if ra <= 0 or rb <= 0:
        return 0.0

    def f(rs):
        x = -np.pi * ra / rs
        y = -np.pi * rb / rs
        x = np.clip(x, -50, 0)
        y = np.clip(y, -50, 0)
        return np.exp(x) + np.exp(y) - 1.0

    def fprime(rs):
        x = -np.pi * ra / rs
        y = -np.pi * rb / rs
        x = np.clip(x, -50, 0)
        y = np.clip(y, -50, 0)
        return (np.pi * ra / rs**2) * np.exp(x) + (np.pi * rb / rs**2) * np.exp(y)

    rs_init = (np.pi / np.log(2)) * (ra + rb) / 2
    try:
        rs = newton(f, rs_init, fprime=fprime, maxiter=100, tol=1e-10)
    except RuntimeError:
        rs = rs_init
    return rs


def compute_hall(v_bp_fwd, v_bp_rev, v_bm_fwd, v_bm_rev,
                 current_ma, b_field, thickness_mm):
    """Compute Hall coefficient from 4 voltage readings."""
    v_h = (v_bp_fwd - v_bp_rev - v_bm_fwd + v_bm_rev) / 4.0
    rh = (v_h * thickness_mm) / (current_ma * b_field * 1e4)  # cm³/C
    return v_h, rh


def analyze(header: LogHeader, points: List[LogPoint]):
    """Recompute transport parameters from raw data."""
    # Extract Van der Pauw measurements
    ra_fwd = next((p for p in points if 'Ra_fwd' in p.config), None)
    ra_rev = next((p for p in points if 'Ra_rev' in p.config), None)
    rb_fwd = next((p for p in points if 'Rb_fwd' in p.config), None)
    rb_rev = next((p for p in points if 'Rb_rev' in p.config), None)

    if not all([ra_fwd, ra_rev, rb_fwd, rb_rev]):
        print("Error: Missing Van der Pauw data points")
        return None

    current = abs(ra_fwd.current_ma)

    # R_A and R_B with current reversal
    ra = ((ra_fwd.voltage_uv - ra_rev.voltage_uv) / 2.0 * 1e-3) / current  # Ω
    rb = ((rb_fwd.voltage_uv - rb_rev.voltage_uv) / 2.0 * 1e-3) / current  # Ω

    # Sheet resistance
    rs = vdp_solve_rs(ra, rb)

    # Extract Hall measurements
    hbp_fwd = next((p for p in points if 'B+_fwd' in p.config), None)
    hbp_rev = next((p for p in points if 'B+_rev' in p.config), None)
    hbm_fwd = next((p for p in points if 'B-_fwd' in p.config), None)
    hbm_rev = next((p for p in points if 'B-_rev' in p.config), None)

    if not all([hbp_fwd, hbp_rev, hbm_fwd, hbm_rev]):
        print("Error: Missing Hall effect data points")
        return None

    b_field = abs(hbm_fwd.b_field) if hbm_fwd.b_field != 0 else header.b_field

    v_h, rh = compute_hall(
        hbp_fwd.voltage_uv, hbp_rev.voltage_uv,
        hbm_fwd.voltage_uv, hbm_rev.voltage_uv,
        current, b_field, header.thickness
    )

    e_charge = 1.602176634e-19
    conc = 1.0 / (abs(rh) * e_charge) if abs(rh) > 0 else 0
    mobility = abs(rh) / rs if rs > 0 else 0
    resistivity = rs * header.thickness * 0.1  # mm→cm
    carrier_type = "p-type" if rh > 0 else "n-type"

    return {
        'ra': ra, 'rb': rb, 'rs': rs,
        'v_h': v_h, 'rh': rh, 'conc': conc,
        'mobility': mobility, 'resistivity': resistivity,
        'carrier_type': carrier_type,
        'current': current, 'b_field': b_field,
    }


def plot_results(header, result, points, analysis, output_file):
    """Generate publication-quality plots."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Hall Puck — {header.sample or 'Semiconductor Sample'}", fontsize=14)

    # Plot 1: Raw voltage measurements
    ax1 = axes[0, 0]
    steps = [p.step for p in points]
    volts = [p.voltage_uv for p in points]
    colors = ['blue' if 'VDP' in p.config else 'red' if 'B+' in p.config else 'green'
              for p in points]
    ax1.bar(steps, volts, color=colors, alpha=0.7)
    ax1.set_xlabel('Measurement Step')
    ax1.set_ylabel('Voltage (µV)')
    ax1.set_title('Raw Voltage Measurements')
    ax1.axhline(y=0, color='k', linewidth=0.5)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Van der Pauw analysis
    ax2 = axes[0, 1]
    if analysis:
        ax2.text(0.1, 0.9, f"R_A = {analysis['ra']:.2f} Ω", transform=ax2.transAxes)
        ax2.text(0.1, 0.8, f"R_B = {analysis['rb']:.2f} Ω", transform=ax2.transAxes)
        ax2.text(0.1, 0.7, f"R_s = {analysis['rs']:.2f} Ω/□", transform=ax2.transAxes,
                 fontsize=12, fontweight='bold')
        ax2.text(0.1, 0.5, f"ρ = {analysis['resistivity']:.4f} Ω·cm", transform=ax2.transAxes)
    ax2.set_title('Van der Pauw Results')
    ax2.axis('off')

    # Plot 3: Hall voltage analysis
    ax3 = axes[1, 0]
    hall_pts = [p for p in points if 'HALL' in p.config]
    if hall_pts:
        labels = [p.config for p in hall_pts]
        volts = [p.voltage_uv for p in hall_pts]
        ax3.bar(range(len(labels)), volts, color=['red', 'red', 'green', 'green'],
                alpha=0.7)
        ax3.set_xticks(range(len(labels)))
        ax3.set_xticklabels(labels, rotation=45, ha='right')
        ax3.set_ylabel('Voltage (µV)')
        ax3.set_title('Hall Voltage Measurements (B+ vs B-)')
        ax3.axhline(y=0, color='k', linewidth=0.5)
        ax3.grid(True, alpha=0.3)

    # Plot 4: Final results summary
    ax4 = axes[1, 1]
    if analysis:
        results_text = (
            f"Carrier Type:       {analysis['carrier_type']}\n"
            f"Sheet Resistance:   {analysis['rs']:.2f} Ω/□\n"
            f"Hall Coefficient:   {analysis['rh']:.2f} cm³/C\n"
            f"Carrier Concentration: {analysis['conc']:.3e} cm⁻³\n"
            f"Mobility:           {analysis['mobility']:.1f} cm²/V·s\n"
            f"Resistivity:        {analysis['resistivity']:.4f} Ω·cm\n"
            f"\n"
            f"Temperature:        {header.temperature:.1f} °C\n"
            f"B-field:            {analysis['b_field']:.3f} T\n"
            f"Current:            {analysis['current']:.3f} mA\n"
            f"Thickness:          {header.thickness:.3f} mm\n"
        )
        ax4.text(0.05, 0.95, results_text, transform=ax4.transAxes,
                 fontsize=11, verticalalignment='top', fontfamily='monospace')
    ax4.set_title('Final Results')
    ax4.axis('off')

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description='Analyze Hall Puck CSV log')
    parser.add_argument('logfile', help='Path to CSV log file')
    parser.add_argument('--output', '-o', help='Output plot file (PNG)')
    args = parser.parse_args()

    header, result, points = parse_log(args.logfile)

    print(f"\n=== Hall Puck Log Analysis ===")
    print(f"File: {args.logfile}")
    print(f"Sample: {header.sample}")
    print(f"Thickness: {header.thickness} mm")
    print(f"Temperature: {header.temperature} °C")
    print(f"B-field: {header.b_field} T")
    print(f"Current: {header.current} mA")
    print(f"Data points: {len(points)}")

    analysis = analyze(header, points)
    if analysis:
        print(f"\n--- Computed Results ---")
        print(f"R_A = {analysis['ra']:.4f} Ω")
        print(f"R_B = {analysis['rb']:.4f} Ω")
        print(f"R_s = {analysis['rs']:.4f} Ω/□")
        print(f"V_H = {analysis['v_h']:.4f} µV")
        print(f"R_H = {analysis['rh']:.4f} cm³/C")
        print(f"n   = {analysis['conc']:.4e} cm⁻³")
        print(f"μ   = {analysis['mobility']:.2f} cm²/V·s")
        print(f"ρ   = {analysis['resistivity']:.6f} Ω·cm")
        print(f"Type: {analysis['carrier_type']}")

    plot_results(header, result, points, analysis, args.output)


if __name__ == "__main__":
    main()