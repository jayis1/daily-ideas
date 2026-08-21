#!/usr/bin/env python3
"""
Pyro Balance — Offline TG/DTG analysis, kinetics, buoyancy correction.

Reads a CSV produced by Pyro Balance (SD card or BLE export), recomputes
the DTG curve, detects decomposition steps, and optionally:
  - subtracts an empty-crucible buoyancy blank
  - computes Kissinger / Ozawa activation energy from multiple runs

Usage:
    # Single run analysis
    python3 analyze_tga.py run.csv

    # With buoyancy blank subtraction
    python3 analyze_tga.py run.csv --blank blank.csv -o corrected.csv

    # Multi-rate kinetics (3 runs at 2/5/10 °C/min)
    python3 analyze_tga.py r2.csv r5.csv r10.csv --rates 2 5 10 --kinetics

Requirements: numpy, scipy, matplotlib (optional for plots)
    pip install numpy scipy matplotlib
"""
import argparse
import csv
import numpy as np
from dataclasses import dataclass, field
from typing import List


@dataclass
class TGRun:
    time_s: np.ndarray
    temp_c: np.ndarray
    mass_mg: np.ndarray
    mass_pct: np.ndarray
    dtg: np.ndarray = field(default_factory=lambda: np.array([]))

    @classmethod
    def from_csv(cls, path):
        t, T, m, pct, d = [], [], [], [], []
        with open(path, newline="") as f:
            for row in csv.reader(f):
                if not row or row[0].startswith("#"):
                    continue
                try:
                    t.append(float(row[0]))
                    T.append(float(row[1]))
                    m.append(float(row[2]))
                    pct.append(float(row[3]))
                    if len(row) > 4:
                        d.append(float(row[4]))
                    else:
                        d.append(0.0)
                except (ValueError, IndexError):
                    continue
        return cls(np.array(t), np.array(T), np.array(m),
                   np.array(pct), np.array(d))


def compute_dtg(run: TGRun, window: int = 7) -> np.ndarray:
    """Savitzky-Golay smoothed DTG (%/min)."""
    from scipy.signal import savgol_filter
    smoothed = savgol_filter(run.mass_pct, window_length=window, polyorder=2)
    dt = np.gradient(run.time_s) / 60.0  # minutes
    dtg = np.gradient(smoothed) / np.where(dt > 0, dt, 1e-9)
    return dtg


@dataclass
class Step:
    onset_c: float
    peak_c: float
    endset_c: float
    dmass_pct: float
    dtg_peak: float


def detect_steps(run: TGRun, k: float = 4.0, refractory_s: float = 30.0) -> List[Step]:
    dtg = run.dtg if run.dtg.any() else compute_dtg(run)
    abs_dtg = np.abs(dtg)
    mean = abs_dtg.mean()
    std = abs_dtg.std()
    thresh = mean + k * std
    steps = []
    i = 0
    n = len(run.temp_c)
    while i < n - 10:
        if abs_dtg[i] > thresh:
            pk = i
            j = i + 1
            while j < n - 1 and abs_dtg[j] > thresh * 0.3:
                if abs_dtg[j] > abs_dtg[pk]:
                    pk = j
                j += 1
            onset_i = max(0, pk - 5)
            while onset_i > 0 and abs_dtg[onset_i] > thresh * 0.1:
                onset_i -= 1
            endset_i = min(n - 1, j)
            while endset_i < n - 1 and abs_dtg[endset_i] > thresh * 0.1:
                endset_i += 1
            dmass = abs(run.mass_pct[onset_i] - run.mass_pct[endset_i])
            steps.append(Step(
                onset_c=run.temp_c[onset_i],
                peak_c=run.temp_c[pk],
                endset_c=run.temp_c[endset_i],
                dmass_pct=dmass,
                dtg_peak=dtg[pk],
            ))
            i = int(endset_i + refractory_s / max(np.gradient(run.time_s).mean(), 1e-9))
        else:
            i += 1
    return steps


def subtract_blank(run: TGRun, blank: TGRun) -> TGRun:
    """Subtract buoyancy blank (interpolated to run temps)."""
    from scipy.interpolate import interp1d
    interp = interp1d(blank.temp_c, blank.mass_pct, bounds_error=False, fill_value="extrapolate")
    blank_pct = interp(run.temp_c)
    corrected = run.mass_pct - (blank_pct - blank_pct[0])  # remove blank drift
    return TGRun(run.time_s, run.temp_c, run.mass_mg, corrected, run.dtg)


def kissinger_E(betas, Tps_K):
    """Kissinger activation energy (J/mol)."""
    import numpy as np
    x = 1.0 / np.array(Tps_K)
    y = np.log(np.array(betas) / np.array(Tps_K)**2)
    slope, _ = np.polyfit(x, y, 1)
    R = 8.314
    return -slope * R


def ozawa_E(betas, Tps_K):
    """Ozawa–Flynn–Wall activation energy (J/mol)."""
    x = 1.0 / np.array(Tps_K)
    y = np.log(np.array(betas))
    slope, _ = np.polyfit(x, y, 1)
    R = 8.314
    return -slope * R / 1.052


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="CSV file(s)")
    ap.add_argument("--rates", nargs="+", type=float, help="heating rates °C/min (for kinetics)")
    ap.add_argument("--kinetics", action="store_true", help="compute activation energy")
    ap.add_argument("--blank", help="blank CSV for buoyancy correction")
    ap.add_argument("-o", "--output", help="write corrected CSV")
    ap.add_argument("--plot", action="store_true", help="show plots")
    args = ap.parse_args()

    runs = [TGRun.from_csv(r) for r in args.runs]

    if args.blank:
        blank = TGRun.from_csv(args.blank)
        runs[0] = subtract_blank(runs[0], blank)
        print("Applied buoyancy blank correction.")

    # recompute DTG
    for run in runs:
        run.dtg = compute_dtg(run)

    # single-run analysis
    run = runs[0]
    steps = detect_steps(run)
    print(f"\n=== TG Analysis: {args.runs[0]} ===")
    print(f"Initial mass: {run.mass_mg[0]:.3f} mg")
    print(f"Final mass:   {run.mass_mg[-1]:.3f} mg")
    print(f"Residual:     {run.mass_pct[-1]:.2f} %")
    print(f"Steps detected: {len(steps)}")
    for i, s in enumerate(steps):
        print(f"  Step {i}: onset={s.onset_c:.1f}°C  peak={s.peak_c:.1f}°C  "
              f"endset={s.endset_c:.1f}°C  Δm={s.dmass_pct:.2f}%  DTG_peak={s.dtg_peak:.3f}%/min")

    if args.output:
        with open(args.output, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time_s", "temp_c", "mass_mg", "mass_pct", "dtg_pct_per_min"])
            for i in range(len(run.time_s)):
                w.writerow([f"{run.time_s[i]:.3f}", f"{run.temp_c[i]:.3f}",
                            f"{run.mass_mg[i]:.3f}", f"{run.mass_pct[i]:.3f}",
                            f"{run.dtg[i]:.4f}"])
        print(f"Corrected CSV written to {args.output}")

    # kinetics
    if args.kinetics and len(runs) >= 3 and args.rates:
        if len(args.rates) != len(runs):
            print("Warning: number of rates != number of runs; skipping kinetics.")
        else:
            Tps = []
            for r in runs:
                st = detect_steps(r)
                if st:
                    Tps.append(st[0].peak_c + 273.15)
                else:
                    Tps.append(np.nan)
            if all(np.isfinite(Tps)):
                Ek = kissinger_E(args.rates, Tps)
                Eo = ozawa_E(args.rates, Tps)
                print(f"\n=== Kinetics (step 0) ===")
                print(f"  Kissinger E_a = {Ek/1000:.1f} kJ/mol")
                print(f"  Ozawa E_a     = {Eo/1000:.1f} kJ/mol")
                print(f"  Average       = {(Ek+Eo)/2/1000:.1f} kJ/mol")

    if args.plot:
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
        ax1.plot(run.temp_c, run.mass_pct, "b-")
        ax1.set_xlabel("Temperature (°C)")
        ax1.set_ylabel("Mass (%)")
        ax1.set_title("TG curve")
        ax2.plot(run.temp_c, run.dtg, "r-")
        ax2.set_xlabel("Temperature (°C)")
        ax2.set_ylabel("DTG (%/min)")
        ax2.set_title("DTG curve")
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    main()