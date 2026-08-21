#!/usr/bin/env python3
"""
sferic_gen.py — synthetic sferic waveform generator for Bolt Compass

Generates synthetic CG (cloud-to-ground) and IC (intra-cloud) sferic
waveforms as they would be received by the crossed-loop VLF antennas,
applies the Earth-ionosphere waveguide propagation model, and writes
them to a binary file for offline classifier testing / training.

Usage:
    python3 sferic_gen.py --n 1000 --out sferics.bin
    python3 sferic_gen.py --n 50 --type CG --dist 100 --bearing 45 --plot
"""
import argparse
import math
import struct
import random
import sys
from pathlib import Path

ADC_RATE = 8000          # samples per second
WIN = 400                # 50 ms window
K_LOOP = 4.096           # loop units per µV/m
ALPHA_DAY = 0.00075      # mode-1 TM attenuation, AVG ground, day (per km)
E_REF = 1000.0           # reference peak field at 100 km (µV/m)


def sferic_envelope(t_us: float, stroke_type: str) -> float:
    """Received sferic envelope (after ionospheric dispersion)."""
    if t_us < 0:
        return 0.0
    if stroke_type == "CG":
        rise = math.exp(-t_us / 200.0)    # ~200 us rise
        tail = math.exp(-t_us / 8000.0)   # ~8 ms slow tail
        return rise * 0.7 + tail * 0.3
    elif stroke_type == "IC":
        return math.exp(-t_us / 1000.0) * (1.0 - math.exp(-t_us / 400.0)) * 3.0
    else:  # CC
        return math.exp(-t_us / 2000.0) * (1.0 - math.exp(-t_us / 800.0)) * 2.0


def propagate(amp_uv: float, dist_km: float) -> float:
    """Apply Earth-ionosphere waveguide attenuation."""
    return amp_uv * math.exp(-ALPHA_DAY * dist_km) * math.sqrt(100.0 / dist_km)


def generate_sferic(bearing_deg: float, dist_km: float, stroke_type: str,
                    noise_std: float = 80.0):
    """Return (ns[WIN], ew[WIN], e[WIN]) as lists of int16."""
    e_peak = propagate(E_REF, dist_km)
    amp = e_peak * K_LOOP
    if amp > 28000:
        amp = 28000.0

    br = math.radians(bearing_deg)
    ns_gain = math.cos(br)
    ew_gain = math.sin(br)

    peak_idx = 160
    ns, ew, e = [], [], []
    for i in range(WIN):
        t = (i - peak_idx) * (1e6 / ADC_RATE)
        env = sferic_envelope(t, stroke_type)
        n = amp * ns_gain * env + random.gauss(0, noise_std)
        w = amp * ew_gain * env + random.gauss(0, noise_std)
        if stroke_type == "CG":
            es = amp * 0.5 * math.exp(-t / 5000.0) * (1 if t > 0 else -1)
        else:
            es = amp * 0.15 * math.exp(-t / 3000.0) * (1 if t > 0 else -1) * 0.3
        es += random.gauss(0, noise_std * 0.3)
        ns.append(int(max(-32768, min(32767, n))))
        ew.append(int(max(-32768, min(32767, w))))
        e.append(int(max(-32768, min(32767, es))))
    return ns, ew, e


TYPE_MAP = {"CG": 0, "IC": 1, "CC": 2}


def main():
    p = argparse.ArgumentParser(description="Synthetic sferic generator")
    p.add_argument("--n", type=int, default=100, help="number of sferics")
    p.add_argument("--out", default="sferics.bin", help="output binary file")
    p.add_argument("--type", choices=["CG", "IC", "CC", "mixed"],
                   default="mixed")
    p.add_argument("--dist", type=float, nargs=2, default=[10, 300],
                   metavar=("MIN", "MAX"), help="distance range km")
    p.add_argument("--bearing", type=float, nargs=2, default=[0, 360],
                   metavar=("MIN", "MAX"), help="bearing range deg")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--plot", action="store_true", help="plot first sferic")
    args = p.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    types = ["CG", "IC", "CC"] if args.type == "mixed" else [args.type]
    path = Path(args.out)
    with path.open("wb") as f:
        for i in range(args.n):
            t = random.choice(types) if args.type == "mixed" else args.type
            brg = random.uniform(*args.bearing)
            dist = random.uniform(*args.dist)
            ns, ew, e = generate_sferic(brg, dist, t)
            # Header: type(1) + bearing(2) + dist(2) + 3*WIN*2 bytes
            f.write(struct.pack("<BHH", TYPE_MAP[t],
                                int(brg * 100), int(dist)))
            f.write(struct.pack(f"<{WIN}h", *ns))
            f.write(struct.pack(f"<{WIN}h", *ew))
            f.write(struct.pack(f"<{WIN}h", *e))

    print(f"Wrote {args.n} sferics to {path} "
          f"({path.stat().st_size} bytes)")

    if args.plot:
        import matplotlib.pyplot as plt
        t = types[0] if args.type != "mixed" else "CG"
        ns, ew, e = generate_sferic(45, 100, t)
        ts = [i * (1e6 / ADC_RATE) for i in range(WIN)]
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8))
        ax1.plot(ts, ns, label="N-S loop")
        ax1.set_ylabel("amplitude")
        ax1.set_title(f"Synthetic {t} sferic @ 45° 100 km")
        ax1.legend()
        ax2.plot(ts, ew, label="E-W loop", color="orange")
        ax2.set_ylabel("amplitude")
        ax2.legend()
        ax3.plot(ts, e, label="slow-E", color="green")
        ax3.set_ylabel("amplitude")
        ax3.set_xlabel("time (µs)")
        ax3.legend()
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()