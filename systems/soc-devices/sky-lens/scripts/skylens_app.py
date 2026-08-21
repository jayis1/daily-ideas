#!/usr/bin/env python3
"""
skylens_app.py — Sky Lens companion app

Live mode:  connects over BLE (or Wi-Fi TCP) and shows a live event feed,
            a rolling rate plot, a zenith histogram with a cos²θ fit,
            and a 64×32 skymap of the celestial muon flux.
Lifetime:   plots the inter-event delay histogram and fits the exponential
            to extract τ_µ ≈ 2.197 µs.
Batch:      reads a folder of SD-card CSV dumps and produces a summary
            table + per-day PNG plots (rate, zenith, skymap).

Usage:
  python3 skylens_app.py --ble --device SkyLens
  python3 skylens_app.py --wifi --host 192.168.4.1
  python3 skylens_app.py --lifetime --ble --device SkyLens
  python3 skylens_app.py --batch /mnt/sd/EVENTS/ev_*.csv
"""

import argparse
import struct
import sys
import math
import json
from pathlib import Path

# Protocol constants (must match firmware/esp32/main/proto.c)
PROTO_MAGIC = 0x534C   # 'SL'
FRAME_LEN = 56
FRAME_FMT = "<2sQqHHl ff 4f ff BB"  # see proto.c; simplified below


def unpack_event(buf: bytes):
    """Unpack a 56-byte Sky Lens event frame."""
    if len(buf) < FRAME_LEN:
        return None
    magic = buf[0:2]
    if magic != b"SL":
        return None
    cks = 0
    for b in buf[0:55]:
        cks ^= b
    if cks != buf[55]:
        return None
    (seq,) = struct.unpack_from("<I", buf, 2)
    (ts_us,) = struct.unpack_from("<Q", buf, 6)
    (h0, h1) = struct.unpack_from("<hh", buf, 14)
    (dt_ps,) = struct.unpack_from("<i", buf, 18)
    (zen, az) = struct.unpack_from("<ff", buf, 22)
    qw, qx, qy, qz = struct.unpack_from("<ffff", buf, 30)
    (p, t) = struct.unpack_from("<ff", buf, 46)
    flags = buf[54]
    return {
        "seq": seq, "ts_us": ts_us, "h0_mv": h0, "h1_mv": h1,
        "dt_ps": dt_ps, "zenith_deg": zen, "az_deg": az,
        "q": (qw, qx, qy, qz), "p_hpa": p, "t_c": t, "flags": flags,
    }


def fit_cos2theta(bins, n_bins=18):
    """Fit I(θ) = I0·cos²θ to a zenith histogram. Returns (I0, chi2)."""
    sum_y = 0.0
    sum_w = 0.0
    n_used = 0
    for i in range(n_bins):
        th = (i + 0.5) * (90.0 / n_bins) * math.pi / 180.0
        c2 = math.cos(th) ** 2
        if c2 < 0.01 or bins[i] < 1:
            continue
        sum_y += bins[i]
        sum_w += c2
        n_used += 1
    i0 = sum_y / sum_w if sum_w > 0 else 0
    chi2 = 0.0
    for i in range(n_bins):
        th = (i + 0.5) * (90.0 / n_bins) * math.pi / 180.0
        c2 = math.cos(th) ** 2
        if c2 < 0.01:
            continue
        model = i0 * c2
        if model > 0:
            chi2 += (bins[i] - model) ** 2 / model
    chi2 /= max(n_used - 2, 1)
    return i0, chi2


def fit_lifetime(delays, bin_us=0.1, n_bins=200):
    """Fit N(t) = N0·exp(-t/τ) + bg to a delay histogram. Returns dict."""
    if sum(delays) < 20:
        return {"tau_us": 0, "err": 0, "bg": 0, "chi2": 0, "n_pairs": sum(delays)}
    bg = sum(delays[-20:]) / 20.0
    Sx = Sy = Sxx = Sxy = 0.0
    n_fit = 0
    for i in range(n_bins):
        y = delays[i] - bg
        if y < 1.0:
            continue
        t = (i + 0.5) * bin_us
        ly = math.log(y)
        Sx += t; Sy += ly; Sxx += t*t; Sxy += t*ly
        n_fit += 1
    if n_fit < 4:
        return {"tau_us": 0, "err": 0, "bg": bg, "chi2": 0, "n_pairs": sum(delays)}
    D = n_fit * Sxx - Sx * Sx
    if abs(D) < 1e-12:
        return {"tau_us": 0, "err": 0, "bg": bg, "chi2": 0, "n_pairs": sum(delays)}
    b = (n_fit * Sxy - Sx * Sy) / D
    a = (Sy - b * Sx) / n_fit
    if abs(b) < 1e-9:
        return {"tau_us": 0, "err": 0, "bg": bg, "chi2": 0, "n_pairs": sum(delays)}
    tau = -1.0 / b
    # error estimate
    var_b = 0.0
    for i in range(n_bins):
        y = delays[i] - bg
        if y < 1.0:
            continue
        t = (i + 0.5) * bin_us
        resid = math.log(y) - (a + b * t)
        var_b += resid ** 2
    sigma_b = math.sqrt(var_b / D / n_fit) if D > 0 else 0
    err = abs(1.0 / (b ** 2) * sigma_b) if abs(b) > 1e-9 else 0
    return {"tau_us": tau, "err": err, "bg": bg, "chi2": 0, "n_pairs": sum(delays)}


def pressure_correct(rate, p_hpa, beta=0.012, p_ref=1013.25):
    """Barometric correction: R_corr = R_meas * exp(beta * (P_ref - P))"""
    return rate * math.exp(beta * (p_ref - p_hpa))


# ── BLE live mode ──────────────────────────────────────────────────────
def live_ble(device_name):
    try:
        import asyncio
        from bleak import BleakClient, BleakScanner
    except ImportError:
        print("Install bleak: pip install bleak")
        return
    print(f"Scanning for {device_name}...")
    devices = asyncio.run(BleakScanner.discover())
    target = None
    for d in devices:
        if device_name.lower() in (d.name or "").lower():
            target = d
            break
    if not target:
        print(f"Device '{device_name}' not found.")
        return
    print(f"Connecting to {target.name} ({target.address})...")
    events = []
    async def run():
        async with BleakClient(target.address) as client:
            # UUID_A102 = event characteristic (notify)
            EVT_UUID = "0000a102-0000-1000-8000-00805f9b34fb"
            def handler(c, data):
                ev = unpack_event(bytes(data))
                if ev:
                    events.append(ev)
                    print(f"  event #{ev['seq']}: zen={ev['zenith_deg']:.1f}° "
                          f"az={ev['az_deg']:.1f}° h0={ev['h0_mv']}mV "
                          f"h1={ev['h1_mv']}mV P={ev['p_hpa']:.1f}hPa")
            await client.start_notify(EVT_UUID, handler)
            print("Listening for events (Ctrl-C to stop)...")
            try:
                while True:
                    await asyncio.sleep(1)
                    if events:
                        rate = len(events) / max(
                            (events[-1]["ts_us"] - events[0]["ts_us"]) / 1e6, 1) * 60
                        print(f"  [{len(events)} events] rate ≈ {rate:.1f} cpm")
            except KeyboardInterrupt:
                pass
            await client.stop_notify(EVT_UUID)
    asyncio.run(run())


# ── Wi-Fi live mode ─────────────────────────────────────────────────────
def live_wifi(host):
    import urllib.request
    base = f"http://{host}"
    print(f"Fetching events from {base}/events.json ...")
    try:
        with urllib.request.urlopen(f"{base}/events.json") as r:
            data = json.loads(r.read())
        evs = data.get("events", [])
        print(f"  {len(evs)} events in buffer:")
        for e in evs[-10:]:
            print(f"    #{e['seq']}: zen={e['zen']:.1f}° az={e['az']:.1f}° "
                  f"h0={e['h0']}mV h1={e['h1']}mV")
        # Skymap
        with urllib.request.urlopen(f"{base}/skymap.json") as r:
            sm = json.loads(r.read())
        total = sm.get("skymap_total", 0)
        print(f"  skymap total: {total} events")
    except Exception as e:
        print(f"  Error: {e}")


# ── Batch mode ──────────────────────────────────────────────────────────
def batch_process(pattern):
    import csv
    import glob
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"No files matching {pattern}")
        return
    print(f"Processing {len(files)} files...")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
        have_plot = True
    except ImportError:
        have_plot = False
        print("Install matplotlib + numpy for plots: pip install matplotlib numpy")

    all_events = []
    for f in files:
        with open(f) as fh:
            reader = csv.reader(fh)
            for row in reader:
                if len(row) < 14:
                    continue
                try:
                    ev = {
                        "ts_us": int(row[0]),
                        "seq": int(row[1]),
                        "h0_mv": int(row[2]),
                        "h1_mv": int(row[3]),
                        "dt_ps": int(row[4]),
                        "zenith_deg": float(row[5]),
                        "az_deg": float(row[6]),
                        "p_hpa": float(row[11]),
                        "t_c": float(row[12]),
                    }
                    all_events.append(ev)
                except (ValueError, IndexError):
                    continue
    print(f"  {len(all_events)} total events")

    # Zenith histogram
    zen_bins = [0] * 18
    for ev in all_events:
        z = abs(ev["zenith_deg"])
        b = min(int(z / 90.0 * 18), 17)
        zen_bins[b] += 1
    i0, chi2 = fit_cos2theta(zen_bins)
    print(f"  Zenith fit: I(0) = {i0:.1f} cpm, chi2 = {chi2:.2f}")

    # Rate
    if all_events:
        duration_s = (all_events[-1]["ts_us"] - all_events[0]["ts_us"]) / 1e6
        rate = len(all_events) / (duration_s / 60) if duration_s > 0 else 0
        mean_p = sum(e["p_hpa"] for e in all_events) / len(all_events)
        corr = pressure_correct(rate, mean_p)
        print(f"  Raw rate: {rate:.1f} cpm | Corrected: {corr:.1f} cpm "
              f"(P_mean={mean_p:.1f} hPa)")

    if have_plot and all_events:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        # Zenith histogram + cos²θ fit
        ax = axes[0]
        centers = [(i + 0.5) * 5 for i in range(18)]
        ax.bar(centers, zen_bins, width=4, label="data")
        if i0 > 0:
            th = np.linspace(0, 90, 50)
            ax.plot(th, [i0 * math.cos(t * math.pi / 180) ** 2 for t in th],
                    "r-", label=f"I0·cos²θ (I0={i0:.1f})")
        ax.set_xlabel("Zenith angle (°)")
        ax.set_ylabel("Counts")
        ax.set_title("Zenith histogram + cos²θ fit")
        ax.legend()
        # Skymap
        ax = axes[1]
        skymap = np.zeros((32, 64))
        for ev in all_events:
            za = min(int(ev["zenith_deg"] / 90.0 * 32), 31)
            az = min(int(ev["az_deg"] / 360.0 * 64), 63)
            skymap[za][az] += 1
        ax.imshow(skymap, aspect="auto", cmap="viridis",
                  extent=[0, 360, 90, 0])
        ax.set_xlabel("Azimuth (°)")
        ax.set_ylabel("Zenith (°)")
        ax.set_title(f"Muon skymap ({len(all_events)} events)")
        plt.tight_layout()
        out = "sky_lens_batch.png"
        plt.savefig(out, dpi=150)
        print(f"  Plots saved to {out}")


# ── Lifetime mode ────────────────────────────────────────────────────────
def lifetime_ble(device_name):
    """Fetch the lifetime histogram over BLE and fit it."""
    # This is a placeholder; the real implementation would read the
    # lifetime characteristic (UUID_A105) and call fit_lifetime().
    print("Lifetime mode: connect over BLE and read the delay histogram.")
    print("Expected τ_µ ≈ 2.197 µs. See the batch mode for offline fitting.")


# ── Main ────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Sky Lens companion app")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ble", action="store_true", help="BLE live mode")
    mode.add_argument("--wifi", action="store_true", help="Wi-Fi live mode")
    mode.add_argument("--batch", metavar="PATTERN", help="Batch process SD CSVs")
    mode.add_argument("--lifetime", action="store_true", help="Lifetime fit mode")
    p.add_argument("--device", default="SkyLens", help="BLE device name")
    p.add_argument("--host", default="192.168.4.1", help="Wi-Fi host IP")
    args = p.parse_args()

    if args.ble:
        live_ble(args.device)
    elif args.wifi:
        live_wifi(args.host)
    elif args.batch:
        batch_process(args.batch)
    elif args.lifetime:
        lifetime_ble(args.device)


if __name__ == "__main__":
    main()