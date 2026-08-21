#!/usr/bin/env python3
"""
skymap_proj.py — Sky Lens skymap projection helper

Converts an attitude quaternion plus a reconstructed zenith angle θ into
a (azimuth, zenith) skymap cell, and renders a 64×32 cell skymap to PNG.

Usage:
  python3 skymap_proj.py --render skymap.json --out skymap.png
  python3 skymap_proj.py --project --qw 0.9 --qx 0.1 --qy 0.1 --qz 0.4 --zen 30
"""

import argparse
import json
import math
import sys


def quat_to_yaw(qw, qx, qy, qz):
    """Extract yaw (azimuth) from a quaternion."""
    yaw = math.atan2(2 * (qw * qz + qx * qy),
                     1 - 2 * (qy * qy + qz * qz))
    deg = math.degrees(yaw)
    if deg < 0:
        deg += 360
    return deg


def project_to_cell(qw, qx, qy, qz, zenith_deg, az_cells=64, zen_cells=32):
    """Project a track + attitude onto a skymap cell."""
    az_deg = quat_to_yaw(qw, qx, qy, qz)
    za = min(int(zenith_deg / 90.0 * zen_cells), zen_cells - 1)
    az = min(int(az_deg / 360.0 * az_cells), az_cells - 1)
    return az, za


def render_skymap(skymap_data, total, outfile):
    """Render a 64×32 skymap to a PNG file."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("Install matplotlib + numpy: pip install matplotlib numpy")
        return
    grid = np.zeros((32, 64))
    for za in range(32):
        for az in range(64):
            grid[za][az] = skymap_data.get(str(za * 64 + az), 0)
    fig, ax = plt.subplots(figsize=(10, 5))
    im = ax.imshow(grid, aspect="auto", cmap="viridis",
                   extent=[0, 360, 90, 0])
    ax.set_xlabel("Azimuth (°)")
    ax.set_ylabel("Zenith (°)")
    ax.set_title(f"Muon skymap ({total} events)")
    plt.colorbar(im, ax=ax, label="Counts")
    plt.tight_layout()
    plt.savefig(outfile, dpi=150)
    print(f"Skymap saved to {outfile}")


def main():
    p = argparse.ArgumentParser(description="Sky Lens skymap projection")
    p.add_argument("--render", metavar="JSON", help="Render a skymap JSON to PNG")
    p.add_argument("--out", default="skymap.png", help="Output PNG filename")
    p.add_argument("--project", action="store_true", help="Project a single event")
    p.add_argument("--qw", type=float, default=1.0)
    p.add_argument("--qx", type=float, default=0.0)
    p.add_argument("--qy", type=float, default=0.0)
    p.add_argument("--qz", type=float, default=0.0)
    p.add_argument("--zen", type=float, default=0.0, help="Zenith angle (°)")
    args = p.parse_args()

    if args.render:
        with open(args.render) as f:
            data = json.load(f)
        skymap_data = data.get("cells", {})
        total = data.get("total", 0)
        render_skymap(skymap_data, total, args.out)
    elif args.project:
        az, za = project_to_cell(args.qw, args.qx, args.qy, args.qz, args.zen)
        print(f"Skymap cell: az={az}, zen={za}")
    else:
        p.print_help()


if __name__ == "__main__":
    main()