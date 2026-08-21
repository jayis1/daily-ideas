#!/usr/bin/env python3
"""
bh_plotter.py — companion app for the Ferro Weave B-H loop tracer.

Three modes:
  --ble   <device>   Live mode over BLE (needs `bleak`).
  --wifi  <host>     Live mode over Wi-Fi HTTP (/sweep.json) or TCP stream.
  --batch <glob>     Batch mode: read SD-card CSV dumps, plot each loop,
                     compute derived quantities, export PNG + summary CSV.

Batch mode has no third-party dependencies (stdlib + matplotlib only).
BLE mode requires `bleak`; Wi-Fi mode requires `requests`.

Examples:
  python3 bh_plotter.py --batch 'BH_*.csv'
  python3 bh_plotter.py --ble --device FerroWeave
  python3 bh_plotter.py --wifi --host 192.168.4.1
"""
import argparse
import csv
import glob
import json
import os
import re
import sys
import math
from pathlib import Path

MU0 = 1.2566370614e-6


def parse_csv(path: str):
    """Parse a Ferro Weave CSV dump → (geom, params, H[], B[])."""
    geom = {}
    params = {}
    result = {}
    H, B = [], []
    with open(path, newline="") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                # header comments
                m = re.match(r"#\s*(\w+)=(\S+)", line)
                if m:
                    params[m.group(1)] = m.group(2)
                continue
            if not line or line.startswith("index"):
                continue
            parts = line.split(",")
            if len(parts) >= 3:
                try:
                    H.append(float(parts[1]))
                    B.append(float(parts[2]))
                except ValueError:
                    pass
    # Parse the geometry line if present
    gline = params.get("N1")
    return params, H, B


def compute_loop(H, B):
    """Recompute B-H quantities in Python (cross-check the firmware)."""
    n = len(H)
    if n < 8:
        return None
    b_sat = max(abs(b) for b in B)
    h_peak = max(abs(h) for h in H)
    # loop area (shoelace)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += H[i] * B[j] - H[j] * B[i]
    area = abs(area) / 2.0
    # Hc (B=0 crossing with largest |H|)
    hc = 0.0
    for i in range(n):
        j = (i + 1) % n
        if (B[i] <= 0 and B[j] > 0) or (B[i] > 0 and B[j] <= 0):
            frac = -B[i] / (B[j] - B[i])
            h0 = H[i] + frac * (H[j] - H[i])
            if abs(h0) > abs(hc):
                hc = h0
    # Br (H=0 crossing)
    br = 0.0
    for i in range(n):
        j = (i + 1) % n
        if (H[i] <= 0 and H[j] > 0) or (H[i] > 0 and H[j] <= 0):
            frac = -H[i] / (H[j] - H[i])
            b0 = B[i] + frac * (B[j] - B[i])
            if abs(b0) > abs(br):
                br = b0
    mu_dc = (b_sat / h_peak / MU0) if h_peak > 1e-3 else 0.0
    sq = abs(br) / b_sat if b_sat > 1e-6 else 0.0
    return {
        "B_sat": b_sat, "H_c": hc, "B_r": br,
        "mu_dc": mu_dc, "loop_area": area, "squareness": sq,
    }


def plot_one(path, H, B, r, out_png):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot for", path)
        return
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(H, B, "-b", linewidth=0.8)
    ax.axhline(0, color="k", lw=0.4)
    ax.axvline(0, color="k", lw=0.4)
    ax.set_xlabel("H (A/m)")
    ax.set_ylabel("B (T)")
    ax.set_title(Path(path).stem)
    ax.grid(True, alpha=0.3)
    txt = (f"B_sat={r['B_sat']:.4f} T\\nH_c={r['H_c']:.2f} A/m\\n"
           f"B_r={r['B_r']:.4f} T\\nμ_dc={r['mu_dc']:.1f}\\n"
           f"sq={r['squareness']:.3f}")
    ax.text(0.02, 0.98, txt, transform=ax.transAxes,
            va="top", ha="left", fontsize=9,
            bbox=dict(boxstyle="round", fc="white", alpha=0.8))
    fig.tight_layout()
    fig.savefig(out_png, dpi=120)
    plt.close(fig)
    print(f"  → {out_png}")


def batch_mode(pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"No files matched: {pattern}")
        return 1
    print(f"Processing {len(files)} file(s)…")
    summary = []
    for path in files:
        params, H, B = parse_csv(path)
        if not H:
            print(f"  {path}: no data, skipping")
            continue
        r = compute_loop(H, B)
        if r is None:
            print(f"  {path}: too few samples, skipping")
            continue
        out_png = str(Path(path).with_suffix(".png"))
        plot_one(path, H, B, r, out_png)
        summary.append({"file": path, **r})
        print(f"  {path}: B_sat={r['B_sat']:.4f} T  H_c={r['H_c']:.2f} A/m  "
              f"B_r={r['B_r']:.4f} T  μ_dc={r['mu_dc']:.1f}  sq={r['squareness']:.3f}")
    # Write summary CSV
    if summary:
        sp = "bh_summary.csv"
        with open(sp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=summary[0].keys())
            w.writeheader()
            w.writerows(summary)
        print(f"\nSummary → {sp}")
    return 0


def ble_mode(device):
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError:
        print("BLE mode requires `bleak`:  pip install bleak")
        return 1
    import asyncio

    SWEEP_UUID = "8a7b3c2d-1e0f-4a1b-9c3d-2e1f0a1b2c3f"

    async def run():
        print(f"Scanning for {device}…")
        devs = await BleakScanner.discover()
        addr = None
        for d in devs:
            if device.lower() in (d.name or "").lower():
                addr = d.address
                break
        if not addr:
            print("Device not found.")
            return
        print(f"Connecting to {addr}…")
        async with BleakClient(addr) as client:
            print("Connected. Waiting for sweep notifications…")
            # ... subscribe to SWEEP_UUID, reassemble frames, plot live
            await client.start_notify(SWEEP_UUID, lambda _c, data: print(f"chunk: {len(data)} B"))
            while True:
                await asyncio.sleep(1)
    asyncio.run(run())
    return 0


def wifi_mode(host):
    try:
        import requests
    except ImportError:
        print("Wi-Fi mode requires `requests`:  pip install requests")
        return 1
    url = f"http://{host}/sweep.json"
    print(f"Fetching {url}…")
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    data = r.json()
    print(json.dumps(data, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--batch", metavar="GLOB", help="batch-process CSV dumps")
    g.add_argument("--ble",   action="store_true", help="live BLE mode")
    g.add_argument("--wifi",  action="store_true", help="live Wi-Fi mode")
    ap.add_argument("--device", default="FerroWeave", help="BLE device name")
    ap.add_argument("--host",   default="192.168.4.1", help="Wi-Fi host/IP")
    args = ap.parse_args()

    if args.batch:
        return batch_mode(args.batch)
    if args.ble:
        return ble_mode(args.device)
    if args.wifi:
        return wifi_mode(args.host)


if __name__ == "__main__":
    sys.exit(main() or 0)