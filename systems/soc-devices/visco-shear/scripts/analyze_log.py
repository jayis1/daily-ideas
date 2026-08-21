#!/usr/bin/env python3
"""
visco-shear / scripts / analyze_log.py
Analyze a Visco Shear CSV log file: plot flow curve, fit models, compute G′/G″.

Usage:
    python3 analyze_log.py VS_20260731_101530.csv
    python3 analyze_log.py VS_20260731_101530.csv --plot flow_curve.png
    python3 analyze_log.py VS_20260731_101530.csv --models  # Fit all models

Requires: numpy, matplotlib, scipy (pip install numpy matplotlib scipy)
"""
import argparse
import csv
import sys
import re
import numpy as np

try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

try:
    from scipy.optimize import curve_fit
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ── Rheological models ──────────────────────────────────────────

def newtonian(gd, eta):
    return eta * gd

def power_law(gd, K, n):
    return K * gd**n

def bingham(gd, tau_b, eta_p):
    return np.maximum(tau_b + eta_p * gd, 0)

def herschel_bulkley(gd, tau_hb, K, n):
    return tau_hb + K * gd**n

def casson(gd, tau_c, eta_c):
    sq = np.sqrt(np.maximum(tau_c, 0)) + np.sqrt(eta_c * gd)
    return sq**2

def cross_model(gd, eta0, eta_inf, lam, m):
    return eta_inf + (eta0 - eta_inf) / (1 + (lam * gd)**m)

def carreau_model(gd, eta0, eta_inf, lam, n):
    return eta_inf + (eta0 - eta_inf) / (1 + (lam * gd)**2)**(n/2)

MODELS = {
    "Newtonian":        (newtonian, 1, ["eta"]),
    "Power-Law":        (power_law, 2, ["K", "n"]),
    "Bingham":          (bingham, 2, ["tau_B", "eta_p"]),
    "Herschel-Bulkley": (herschel_bulkley, 3, ["tau_HB", "K", "n"]),
    "Casson":           (casson, 2, ["tau_C", "eta_C"]),
    "Cross":            (cross_model, 4, ["eta_0", "eta_inf", "lambda", "m"]),
    "Carreau":          (carreau_model, 4, ["eta_0", "eta_inf", "lambda", "n"]),
}


def parse_csv(filename):
    """Parse a Visco Shear CSV log file."""
    metadata = {}
    flow_data = []
    osc_data = []
    thixo_data = {}

    section = None

    with open(filename, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            first = row[0].strip()

            # Parse comments (metadata)
            if first.startswith('#'):
                line = ' '.join(row).strip()
                if 'Spindle:' in line:
                    metadata['spindle'] = line.split('Spindle:')[1].strip()
                elif 'Mode:' in line:
                    metadata['mode'] = line.split('Mode:')[1].strip()
                elif 'Temperature:' in line:
                    metadata['temperature'] = line.split('Temperature:')[1].strip()
                elif 'Best model:' in line:
                    metadata['best_model'] = line.split('Best model:')[1].strip()
                elif 'Oscillatory:' in line:
                    section = 'osc'
                elif 'Thixotropy:' in line:
                    thixo = line.split('Thixotropy:')[1].strip()
                    if 'hysteresis_area' in thixo:
                        for part in thixo.split(','):
                            k, v = part.strip().split('=')
                            thixo_data[k.strip()] = float(v)
                elif 'END' in line:
                    section = None
                elif 'Columns:' in line:
                    pass  # Header
                continue

            # Parse data rows
            if section == 'osc':
                try:
                    freq = float(row[0])
                    Gp = float(row[1])
                    Gd = float(row[2])
                    tan_d = float(row[3])
                    eta_c = float(row[4])
                    osc_data.append((freq, Gp, Gd, tan_d, eta_c))
                except (ValueError, IndexError):
                    pass
            elif first.isdigit() and len(row) >= 5:
                try:
                    step = int(row[0])
                    omega = float(row[1])
                    shear_rate = float(row[2])
                    torque = float(row[3])
                    viscosity = float(row[4])
                    flow_data.append((step, omega, shear_rate, torque, viscosity))
                except (ValueError, IndexError):
                    pass

    return metadata, flow_data, osc_data, thixo_data


def fit_models(shear_rate, stress):
    """Fit all rheological models and return results sorted by AIC."""
    results = []

    for name, (func, nparam, param_names) in MODELS.items():
        try:
            # Initial guesses
            if name == "Newtonian":
                p0 = [np.mean(stress / shear_rate)]
            elif name == "Power-Law":
                p0 = [1.0, 1.0]
            elif name == "Bingham":
                p0 = [np.min(stress), np.mean(np.diff(stress) / np.diff(shear_rate))]
            elif name == "Herschel-Bulkley":
                p0 = [np.min(stress) * 0.5, 1.0, 0.8]
            elif name == "Casson":
                p0 = [np.min(stress), 0.01]
            elif name == "Cross":
                p0 = [np.max(stress/shear_rate), np.min(stress/shear_rate), 0.1, 0.8]
            elif name == "Carreau":
                p0 = [np.max(stress/shear_rate), np.min(stress/shear_rate), 0.1, 0.8]

            popt, pcov = curve_fit(func, shear_rate, stress, p0=p0, maxfev=5000)

            # Compute R²
            residual = stress - func(shear_rate, *popt)
            ss_res = np.sum(residual**2)
            ss_tot = np.sum((stress - np.mean(stress))**2)
            r_sq = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            # AIC
            n = len(stress)
            aic = n * np.log(ss_res / n + 1e-15) + 2 * nparam

            results.append({
                "name": name,
                "params": dict(zip(param_names, popt)),
                "r_squared": r_sq,
                "aic": aic,
            })
        except Exception as e:
            results.append({
                "name": name,
                "params": {},
                "r_squared": -1,
                "aic": 1e15,
                "error": str(e),
            })

    results.sort(key=lambda x: x["aic"])
    return results


def main():
    parser = argparse.ArgumentParser(description="Analyze Visco Shear CSV log")
    parser.add_argument("filename", help="CSV log file path")
    parser.add_argument("--plot", type=str, default=None, help="Save plot to file")
    parser.add_argument("--models", action="store_true", help="Fit all rheological models")
    args = parser.parse_args()

    print(f"Analyzing: {args.filename}\n")

    metadata, flow_data, osc_data, thixo_data = parse_csv(args.filename)

    # Print metadata
    print("=== Metadata ===")
    for k, v in metadata.items():
        print(f"  {k}: {v}")

    # Flow curve
    if flow_data:
        print(f"\n=== Flow Curve ({len(flow_data)} points) ===")
        steps = [d[0] for d in flow_data]
        omegas = [d[1] for d in flow_data]
        shear_rates = [d[2] for d in flow_data]
        torques = [d[3] for d in flow_data]
        viscosities = [d[4] for d in flow_data]

        print(f"  {'Step':>4} {'RPM':>8} {'γ̇ (1/s)':>10} {'τ (µN·m)':>10} {'η (mPa·s)':>12}")
        for s, o, sr, t, v in flow_data:
            print(f"  {s:4d} {o:8.3f} {sr:10.4f} {t:10.2f} {v:12.2f}")

        # Compute stress (Pa) from torque (µN·m)
        # This requires spindle geometry; approximate with CC-13 factor
        stress_Pa = np.array(torques) * 1e-6 / 1.887e-6  # Approx CC-13 factor
        shear_rate_arr = np.array(shear_rates)

        if args.models and HAS_SCIPY:
            print("\n=== Model Fitting ===")
            fits = fit_models(shear_rate_arr, stress_Pa)
            for fit in fits[:3]:  # Top 3
                print(f"  {fit['name']:>20s}: R²={fit['r_squared']:.5f}, AIC={fit['aic']:.2f}")
                for pn, pv in fit['params'].items():
                    print(f"    {pn} = {pv:.6f}")
                if 'error' in fit:
                    print(f"    ERROR: {fit['error']}")

        # Plot
        if HAS_MPL and args.plot:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

            # Flow curve: τ vs γ̇
            ax1.loglog(shear_rate_arr, stress_Pa, 'bo-', label='Measured')
            ax1.set_xlabel('Shear rate γ̇ (1/s)')
            ax1.set_ylabel('Shear stress τ (Pa)')
            ax1.set_title('Flow Curve')
            ax1.legend()
            ax1.grid(True, which='both', alpha=0.3)

            # Viscosity vs shear rate
            ax2.loglog(shear_rate_arr, np.array(viscosities), 'rs-', label='Viscosity')
            ax2.set_xlabel('Shear rate γ̇ (1/s)')
            ax2.set_ylabel('Viscosity η (mPa·s)')
            ax2.set_title('Viscosity vs Shear Rate')
            ax2.legend()
            ax2.grid(True, which='both', alpha=0.3)

            # Oscillatory subplot if available
            if osc_data:
                fig2, (ax3, ax4) = plt.subplots(1, 2, figsize=(14, 6))
                freqs = [d[0] for d in osc_data]
                Gp = [d[1] for d in osc_data]
                Gd = [d[2] for d in osc_data]
                tan_d = [d[3] for d in osc_data]

                ax3.loglog(freqs, Gp, 'bo-', label="G' (storage)")
                ax3.loglog(freqs, Gd, 'rs-', label="G'' (loss)")
                ax3.set_xlabel('Frequency (Hz)')
                ax3.set_ylabel('Modulus (Pa)')
                ax3.set_title('Storage & Loss Moduli')
                ax3.legend()
                ax3.grid(True, which='both', alpha=0.3)

                ax4.semilogx(freqs, tan_d, 'g^-', label='tan δ')
                ax4.axhline(y=1.0, color='k', linestyle='--', alpha=0.5, label='Gel point (tanδ=1)')
                ax4.set_xlabel('Frequency (Hz)')
                ax4.set_ylabel('tan δ')
                ax4.set_title('Loss Tangent')
                ax4.legend()
                ax4.grid(True, which='both', alpha=0.3)

                fig2.tight_layout()
                fig2.savefig(args.plot.replace('.png', '_osc.png'), dpi=150)
                print(f"\nOscillatory plot saved to {args.plot.replace('.png', '_osc.png')}")

            fig.tight_layout()
            fig.savefig(args.plot, dpi=150)
            print(f"\nFlow curve plot saved to {args.plot}")

    # Oscillatory data
    if osc_data:
        print(f"\n=== Oscillatory Data ({len(osc_data)} frequencies) ===")
        gp_label = "G' (Pa)"
        gd_label = "G'' (Pa)"
        print(f"  {'Freq (Hz)':>10} {gp_label:>10} {gd_label:>10} {'tan δ':>10} {'|η*| (Pa·s)':>12}")
        for f, Gp, Gd, td, ec in osc_data:
            print(f"  {f:10.3f} {Gp:10.2f} {Gd:10.2f} {td:10.4f} {ec:12.2f}")

    # Thixotropy
    if thixo_data:
        print(f"\n=== Thixotropy ===")
        for k, v in thixo_data.items():
            print(f"  {k}: {v:.2f}")

    print("\nDone.")


if __name__ == "__main__":
    main()