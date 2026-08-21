#!/usr/bin/env python3
"""
Dent Scope — Offline Oliver–Pharr analysis and material identification

Reads a CSV log file from an indentation test and performs the full
Oliver–Pharr analysis: unloading curve fitting, contact stiffness,
hardness, reduced modulus, Young's modulus, work computation, and
material identification against the 30-material library.

Usage:
  python3 analyze_indentation.py indent_0001.csv

Requires: numpy, scipy, matplotlib

MIT License
"""
import argparse
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# 30-material library (same as firmware database.c)
MATERIALS = [
    {"name": "Al 6061-T6",       "HV": 107,  "E": 69,  "eta": 0.05},
    {"name": "Al 2024-T3",       "HV": 137,  "E": 73,  "eta": 0.04},
    {"name": "Al pure(annealed)","HV": 25,   "E": 69,  "eta": 0.10},
    {"name": "Cu (annealed)",    "HV": 47,   "E": 110, "eta": 0.08},
    {"name": "Cu (cold-worked)", "HV": 110,  "E": 120, "eta": 0.03},
    {"name": "Brass 360",        "HV": 160,  "E": 97,  "eta": 0.04},
    {"name": "Bronze",           "HV": 180,  "E": 110, "eta": 0.03},
    {"name": "Steel 1018",       "HV": 126,  "E": 200, "eta": 0.03},
    {"name": "Steel 1045",       "HV": 170,  "E": 200, "eta": 0.02},
    {"name": "Steel 4140",       "HV": 250,  "E": 200, "eta": 0.02},
    {"name": "Steel 304 SS",     "HV": 210,  "E": 193, "eta": 0.04},
    {"name": "Steel 316 SS",     "HV": 160,  "E": 193, "eta": 0.05},
    {"name": "Cast iron gray",   "HV": 200,  "E": 100, "eta": 0.02},
    {"name": "Cast iron duct",    "HV": 180,  "E": 170, "eta": 0.03},
    {"name": "Ti Gr2",           "HV": 145,  "E": 103, "eta": 0.05},
    {"name": "Ti Gr5 (6Al4V)",   "HV": 349,  "E": 114, "eta": 0.02},
    {"name": "Mg AZ31",          "HV": 60,   "E": 45,  "eta": 0.08},
    {"name": "Zn (die cast)",    "HV": 82,   "E": 108, "eta": 0.04},
    {"name": "Alumina 96%",      "HV": 1500, "E": 330, "eta": 0.40},
    {"name": "Zirconia Y-TZP",   "HV": 1300, "E": 210, "eta": 0.35},
    {"name": "Glass soda-lime",  "HV": 540,  "E": 70,  "eta": 0.45},
    {"name": "SiC",              "HV": 2800, "E": 410, "eta": 0.50},
    {"name": "Si3N4",            "HV": 2200, "E": 310, "eta": 0.45},
    {"name": "PMMA",             "HV": 20,   "E": 3.3, "eta": 0.70},
    {"name": "PE HDPE",          "HV": 6,    "E": 1.1, "eta": 0.85},
    {"name": "PC",               "HV": 14,   "E": 2.6, "eta": 0.65},
    {"name": "Nylon 66",         "HV": 30,   "E": 3.0, "eta": 0.70},
    {"name": "PTFE",             "HV": 5,    "E": 0.5, "eta": 0.90},
    {"name": "CFRP",             "HV": 60,   "E": 150, "eta": 0.50},
    {"name": "GFRP",             "HV": 35,   "E": 35,  "eta": 0.60},
    {"name": "TiN coating",      "HV": 2500, "E": 600, "eta": 0.55},
]

# Diamond indenter properties
E_DIAMOND = 1141.0  # GPa
NU_DIAMOND = 0.07

def load_csv(filename):
    """Load CSV log: t_ms,force_mN,depth_um,state"""
    data = np.genfromtxt(filename, delimiter=',', skip_header=1,
                          names=['t', 'force', 'depth', 'state'])
    return data

def find_phases(data):
    """Identify loading, hold, and unloading phases from state column"""
    loading = data[data['state'] == 2]
    holding = data[data['state'] == 3]
    unloading = data[data['state'] == 4]
    return loading, holding, unloading

def power_law(h, alpha, m, hf):
    """Oliver–Pharr unloading model: P = α(h − h_f)^m"""
    dh = h - hf
    dh = np.maximum(dh, 1e-6)
    return alpha * dh ** m

def oliver_pharr(loading, holding, unloading, tip='vickers', nu=0.30, ball_d=1000.0):
    """Perform full Oliver–Pharr analysis"""
    if len(loading) < 3 or len(unloading) < 5:
        return None

    # Peak values
    peak_idx = np.argmax(loading['force'])
    P_max = loading['force'][peak_idx]  # mN
    h_max = loading['depth'][peak_idx]   # µm

    # Find unloading start/end
    if len(unloading) < 5:
        return None

    # Use upper 30-98% of unloading curve for fit
    u_force = unloading['force']
    u_depth = unloading['depth']
    P_lo = P_max * 0.02
    P_hi = P_max * 0.98
    mask = (u_force >= P_lo) & (u_force <= P_hi)
    u_depth_fit = u_depth[mask]
    u_force_fit = u_force[mask]

    if len(u_depth_fit) < 3:
        return None

    # Initial guesses
    hf0 = u_depth[-1] * 0.5
    alpha0 = P_max / max((h_max - hf0), 1e-6) ** 1.5
    try:
        popt, _ = curve_fit(power_law, u_depth_fit, u_force_fit,
                           p0=[alpha0, 1.5, hf0],
                           bounds=([0, 1.0, 0], [1e12, 3.0, h_max]))
        alpha, m, hf = popt
    except Exception:
        return None

    # Contact stiffness S = dP/dh at h_max
    dh = h_max - hf
    if dh <= 0: dh = 1e-6
    S = alpha * m * dh ** (m - 1)  # mN/µm

    # Contact depth h_c = h_max - ε·P_max/S
    epsilon = 0.75 if tip in ('vickers', 'berkovich') else 1.0
    h_c = h_max - epsilon * P_max / S
    if h_c < 0: h_c = 1e-6

    # Contact area
    if tip == 'ball':
        A = np.pi * ball_d * h_c  # µm²
    else:
        A = 24.5 * h_c ** 2  # µm²

    # Hardness H = P_max / A (mN/µm² → MPa = ×1000)
    if A < 1e-6:
        return None
    H_MPa = P_max / A * 1000.0
    HV = H_MPa / 9.807  # kgf/mm²

    # Reduced modulus E_r = S / (2·β·√(A/π))
    beta = 1.012 if tip == 'vickers' else (1.034 if tip == 'berkovich' else 1.0)
    if A < 1e-6:
        return None
    Er_MPa = S / (2 * beta * np.sqrt(A / np.pi)) * 1000.0  # mN/µm² → MPa
    Er_GPa = Er_MPa / 1000.0

    # Young's modulus
    inv_E = (1 - nu**2) / Er_MPa - (1 - NU_DIAMOND**2) / (E_DIAMOND * 1000)
    E_GPa = (1 / inv_E) / 1000 if inv_E > 0 else 0

    # Work
    W_total = np.trapz(loading['force'], loading['depth'])  # nJ
    W_elastic = np.trapz(unloading['force'][::-1], unloading['depth'][::-1])
    eta = W_elastic / W_total if W_total > 0 else 0

    return {
        'P_max_mN': P_max,
        'h_max_um': h_max,
        'h_f_um': hf,
        'S_mN_um': S,
        'h_c_um': h_c,
        'A_um2': A,
        'H_MPa': H_MPa,
        'HV': HV,
        'E_r_GPa': Er_GPa,
        'E_GPa': E_GPa,
        'W_total_nJ': W_total,
        'W_elastic_nJ': W_elastic,
        'eta': eta,
        'alpha': alpha,
        'm': m,
    }

def knn_match(HV, E_GPa, eta, k=3):
    """k-NN material identification"""
    def norm_H(hv):
        return np.log(hv / 5 + 1) / np.log(3000 / 5 + 1)
    def norm_E(e):
        return np.log(e / 0.5 + 1) / np.log(600 / 0.5 + 1)

    q_h = norm_H(max(HV, 0.1))
    q_e = norm_E(max(E_GPa, 0.01))
    q_eta = max(0, min(1, eta))

    dists = []
    for mat in MATERIALS:
        d = (q_h - norm_H(mat['HV']))**2 + \
            (q_e - norm_E(mat['E']))**2 + \
            (q_eta - mat['eta'])**2
        dists.append((d, mat['name']))
    dists.sort()
    return dists[:k]

def plot_curve(loading, holding, unloading, result):
    """Plot P–h curve with annotations"""
    fig, ax = plt.subplots(figsize=(8, 6))

    ax.plot(loading['depth'], loading['force'] / 1000, 'b-', linewidth=1.5, label='Loading')
    if len(holding) > 0:
        ax.plot(holding['depth'], holding['force'] / 1000, 'g--', linewidth=1, label='Hold')
    if len(unloading) > 0:
        ax.plot(unloading['depth'], unloading['force'] / 1000, 'r-', linewidth=1.5, label='Unloading')

    # annotations
    P_max_N = result['P_max_mN'] / 1000
    ax.axhline(y=P_max_N, color='gray', linestyle=':', alpha=0.5)
    ax.annotate(f"P_max = {P_max_N:.2f} N\nh_max = {result['h_max_um']:.1f} µm",
               xy=(result['h_max_um'], P_max_N),
               xytext=(result['h_max_um'] + 5, P_max_N - 2),
               arrowprops=dict(arrowstyle='->', color='gray'),
               fontsize=9)

    ax.set_xlabel('Depth h (µm)', fontsize=12)
    ax.set_ylabel('Force P (N)', fontsize=12)
    ax.set_title(f"Dent Scope — P–h Curve\n"
                f"HV={result['HV']:.1f}  E={result['E_GPa']:.1f} GPa  η={result['eta']:.2f}",
                fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('ph_curve.png', dpi=150)
    print(f"Plot saved: ph_curve.png")

def main():
    parser = argparse.ArgumentParser(description='Dent Scope offline analysis')
    parser.add_argument('csv_file', help='CSV log file from indentation test')
    parser.add_argument('--tip', default='vickers', choices=['vickers', 'berkovich', 'ball'])
    parser.add_argument('--nu', type=float, default=0.30, help="Sample Poisson's ratio")
    parser.add_argument('--no-plot', action='store_true')
    args = parser.parse_args()

    data = load_csv(args.csv_file)
    loading, holding, unloading = find_phases(data)

    print(f"Points: {len(loading)} loading, {len(holding)} hold, {len(unloading)} unloading")

    result = oliver_pharr(loading, holding, unloading,
                          tip=args.tip, nu=args.nu)
    if result is None:
        print("ERROR: insufficient data for Oliver–Pharr analysis")
        return

    print("\n=== Oliver–Pharr Results ===")
    print(f"  P_max      = {result['P_max_mN']:.1f} mN ({result['P_max_mN']/1000:.2f} N)")
    print(f"  h_max      = {result['h_max_um']:.2f} µm")
    print(f"  h_f        = {result['h_f_um']:.2f} µm (residual)")
    print(f"  S          = {result['S_mN_um']:.1f} mN/µm (contact stiffness)")
    print(f"  h_c        = {result['h_c_um']:.2f} µm (contact depth)")
    print(f"  A          = {result['A_um2']:.1f} µm² (contact area)")
    print(f"  H          = {result['H_MPa']:.0f} MPa = {result['HV']:.1f} HV")
    print(f"  E_r        = {result['E_r_GPa']:.1f} GPa (reduced modulus)")
    print(f"  E          = {result['E_GPa']:.1f} GPa (Young's modulus)")
    print(f"  W_total    = {result['W_total_nJ']:.1f} nJ")
    print(f"  W_elastic  = {result['W_elastic_nJ']:.1f} nJ")
    print(f"  η (elastic ratio) = {result['eta']:.3f}")
    print(f"  Unloading fit: α={result['alpha']:.4e}  m={result['m']:.2f}")

    matches = knn_match(result['HV'], result['E_GPa'], result['eta'])
    print("\n=== Material Identification (k-NN, k=3) ===")
    for i, (dist, name) in enumerate(matches):
        print(f"  {i+1}. {name:25s}  (dist={dist:.4f})")

    if not args.no_plot:
        plot_curve(loading, holding, unloading, result)

if __name__ == '__main__':
    main()