#!/usr/bin/env python3
"""
Gossamer Spin — sim_fiber.py
Simulate electrospinning fiber diameter vs process parameters.

Uses a simplified empirical model based on the Taylor cone and jet
thinning physics to estimate fiber diameter as a function of:
  - Voltage (kV)
  - Flow rate (mL/h)
  - Needle-collector distance (cm)
  - Polymer concentration (%)
  - Humidity (% RH)
  - Drum speed (RPM)

The model is based on the following relationships from electrospinning
literature (Taylor 1964, Reneker 2007, Thompson 2007):

  Fiber diameter d ≈ k × (Q / V)^a × (c/c*)^b × (1 / (1 + RH/100))^c

where:
  Q = flow rate, V = voltage, c = concentration, c* = overlap conc.
  k, a, b, c are empirical constants (fitted to PVA/PAN/PLLA data)

Usage:
    python3 sim_fiber.py [--voltage 20] [--flow 1.0] [--dist 15]
                         [--conc 10] [--rh 35] [--rpm 800]
    python3 sim_fiber.py --sweep voltage 5 30 50
"""
import argparse
import numpy as np
import matplotlib.pyplot as plt

# Empirical constants (fitted to literature data for PVA ~10% in water)
K = 45.0       # prefactor (nm)
ALPHA = 0.42   # flow rate exponent
BETA = 2.8     # concentration exponent
GAMMA = 0.15   # voltage exponent
DELTA = 0.35   # humidity thinning exponent
RH_REF = 30.0  # reference humidity (%)
DIST_EXP = 0.3 # distance exponent


def fiber_diameter(voltage_kv, flow_mlh, dist_cm, conc_pct, rh_pct, rpm=800):
    """Estimate nanofiber diameter (nm) from process parameters."""
    # Base diameter from flow/voltage ratio (higher flow = thicker, higher V = thinner)
    d = K * (flow_mlh ** ALPHA) * (voltage_kv ** (-GAMMA))

    # Concentration effect (stronger: higher conc → much thicker)
    c_star = 5.0  # overlap concentration for PVA (~5%)
    d *= ((conc_pct / c_star) ** BETA)

    # Distance effect (longer distance = more stretching = thinner)
    d *= (15.0 / dist_cm) ** DIST_EXP

    # Humidity effect (higher RH = slower evaporation = thicker, beaded)
    d *= (1.0 + (rh_pct - RH_REF) / 100.0) ** DELTA

    # Drum speed effect on alignment (not diameter, but we note it)
    # Higher RPM → more aligned, slightly thinner due to mechanical drawing
    if rpm > 1500:
        d *= 0.92  # 8% thinning at high RPM (aligned)

    return d


def simulate_run(voltage, flow, dist, conc, rh, rpm, duration_min=30):
    """Simulate a full run, showing fiber diameter over time."""
    t = np.linspace(0, duration_min, duration_min * 10)

    # Add process variability (±2% in voltage, ±5% in flow, ±3% RH)
    np.random.seed(42)
    v_noise = voltage * (1 + 0.02 * np.random.randn(len(t)))
    f_noise = flow * (1 + 0.05 * np.random.randn(len(t)))
    rh_drift = rh + 2 * np.sin(t * 0.1) + np.random.randn(len(t)) * 0.5

    diameters = np.array([
        fiber_diameter(v, f, dist, conc, r, rpm)
        for v, f, r in zip(v_noise, f_noise, rh_drift)
    ])

    return t, diameters


def main():
    parser = argparse.ArgumentParser(description="Gossamer Spin fiber simulator")
    parser.add_argument("--voltage", type=float, default=20.0, help="Voltage (kV)")
    parser.add_argument("--flow", type=float, default=1.0, help="Flow rate (mL/h)")
    parser.add_argument("--dist", type=float, default=15.0, help="Needle-collector distance (cm)")
    parser.add_argument("--conc", type=float, default=10.0, help="Polymer concentration (%)")
    parser.add_argument("--rh", type=float, default=35.0, help="Relative humidity (%)")
    parser.add_argument("--rpm", type=float, default=800, help="Drum speed (RPM)")
    parser.add_argument("--duration", type=int, default=30, help="Run duration (min)")
    parser.add_argument("--sweep", nargs='+', help="Sweep a parameter: name start stop steps")
    args = parser.parse_args()

    if args.sweep:
        param = args.sweep[0]
        start, stop, steps = float(args.sweep[1]), float(args.sweep[2]), int(args.sweep[3])
        values = np.linspace(start, stop, steps)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        # Sweep: fiber diameter vs parameter
        # Map CLI short names to function kwargs
        param_map = {
            'voltage': 'voltage_kv', 'flow': 'flow_mlh', 'dist': 'dist_cm',
            'conc': 'conc_pct', 'rh': 'rh_pct', 'rpm': 'rpm',
        }
        kw_name = param_map.get(param, param)
        diameters = []
        for val in values:
            kw = dict(voltage_kv=args.voltage, flow_mlh=args.flow, dist_cm=args.dist,
                      conc_pct=args.conc, rh_pct=args.rh, rpm=args.rpm)
            kw[kw_name] = val
            diameters.append(fiber_diameter(**kw))

        ax1.plot(values, diameters, 'b-', linewidth=2)
        ax1.set_xlabel(f"{param}")
        ax1.set_ylabel("Fiber Diameter (nm)")
        ax1.set_title(f"Fiber Diameter vs {param}", fontsize=12)
        ax1.grid(True, alpha=0.3)

        # Also show a histogram of fiber diameters (with process noise)
        t, d = simulate_run(args.voltage, args.flow, args.dist, args.conc,
                            args.rh, args.rpm, args.duration)
        ax2.hist(d, bins=50, color='green', alpha=0.7, edgecolor='black')
        ax2.axvline(x=np.mean(d), color='red', linestyle='--', linewidth=2,
                    label=f'Mean: {np.mean(d):.0f} nm')
        ax2.set_xlabel("Fiber Diameter (nm)")
        ax2.set_ylabel("Count")
        ax2.set_title(f"Diameter Distribution ({args.duration} min run)", fontsize=12)
        ax2.legend()

        print(f"Mean diameter: {np.mean(d):.0f} nm ± {np.std(d):.0f} nm")
        print(f"  Min: {np.min(d):.0f} nm  Max: {np.max(d):.0f} nm")

    else:
        d = fiber_diameter(args.voltage, args.flow, args.dist, args.conc,
                           args.rh, args.rpm)
        print(f"Estimated fiber diameter: {d:.0f} nm")
        print(f"  Voltage:     {args.voltage} kV")
        print(f"  Flow:        {args.flow} mL/h")
        print(f"  Distance:    {args.dist} cm")
        print(f"  Concentration: {args.conc}%")
        print(f"  Humidity:    {args.rh}% RH")
        print(f"  Drum RPM:    {args.rpm}")

        # Simulate a run
        t, diams = simulate_run(args.voltage, args.flow, args.dist, args.conc,
                                args.rh, args.rpm, args.duration)
        print(f"\nSimulated {args.duration}-min run:")
        print(f"  Mean: {np.mean(diams):.0f} nm  Std: {np.std(diams):.0f} nm")

        plt.figure(figsize=(10, 5))
        plt.plot(t, diams, 'b-', linewidth=0.5, alpha=0.7)
        plt.axhline(y=np.mean(diams), color='r', linestyle='--', label=f'Mean: {np.mean(diams):.0f} nm')
        plt.xlabel("Time (min)")
        plt.ylabel("Fiber Diameter (nm)")
        plt.title("Simulated Fiber Diameter Over Run", fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()