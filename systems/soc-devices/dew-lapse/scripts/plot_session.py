#!/usr/bin/env python3
"""plot_session.py — plot a Frost Point session CSV.

Produces a multi-panel plot of dew point, RH, mirror temperature, and
TEC current over time.

Usage:
    python3 plot_session.py session.csv --out plot.png
"""
import argparse
import csv
from datetime import datetime, timezone

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    raise SystemExit("Install matplotlib: pip install matplotlib")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv", help="session CSV path")
    p.add_argument("--out", default="session_plot.png", help="output image")
    args = p.parse_args()

    ts, dew, rh, ah, w, mirror, tec_i, phase = [], [], [], [], [], [], [], []
    with open(args.csv) as f:
        r = csv.DictReader(f)
        for row in r:
            ts.append(float(row["ts_ms"]) / 1000.0)
            dew.append(float(row["dew_c"]))
            rh.append(float(row["rh_pct"]))
            ah.append(float(row["ah_gm3"]))
            w.append(float(row["w_gkg"]))
            mirror.append(float(row["mirror_c"]))
            tec_i.append(float(row["tec_i"]))
            phase.append(int(row["phase"]))

    fig, axes = plt.subplots(4, 1, figsize=(10, 12), sharex=True)

    ax = axes[0]
    ax.plot(ts, dew, label="Dew/Frost Point", color="tab:blue")
    ax.plot(ts, mirror, label="Mirror Temp", color="tab:orange", alpha=0.7)
    ax.set_ylabel("Temperature (°C)")
    ax.legend(loc="upper right")
    ax.set_title("Frost Point Session")

    ax = axes[1]
    ax.plot(ts, rh, color="tab:green")
    ax.set_ylabel("RH (%)")

    ax = axes[2]
    ax.plot(ts, ah, color="tab:purple", label="AH (g/m³)")
    ax.plot(ts, w, color="tab:brown", label="w (g/kg)")
    ax.set_ylabel("AH / w")
    ax.legend(loc="upper right")

    ax = axes[3]
    ax.plot(ts, tec_i, color="tab:red")
    ax.set_ylabel("TEC Current (A)")
    ax.set_xlabel("Time (s)")

    # Mark frost regions
    for i, ph in enumerate(phase):
        if ph == 1:
            for a in axes:
                a.axvspan(ts[i] - 0.5, ts[i] + 0.5, alpha=0.05, color="cyan")

    fig.tight_layout()
    fig.savefig(args.out, dpi=120)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()