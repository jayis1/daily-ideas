#!/usr/bin/env python3
"""
export_eem.py — Export Fluor Cast SD card logs to standard formats

Converts binary EEM logs from the Fluor Cast SD card to:
  - CSV matrix format (for Excel, R, MATLAB)
  - MATLAB .mat format (for ParafacView, drEEM toolbox)
  - JSON format (for web apps, custom analysis)
  - EEM heatmap PNG images

Usage:
    python3 export_eem.py input_dir/ output_dir/
    python3 export_eem.py --format mat input_dir/ output_dir/
    python3 export_eem.py --format json --plot input.bin output/
"""

import argparse
import struct
import os
import sys
import json
import math
import csv

# EEM format constants (must match firmware)
EEM_ROWS = 8
EEM_COLS = 256
FEATURE_COUNT = 48
EX_WAVELENGTHS = [255, 280, 340, 365, 405, 440, 470, 525]

# Wavelength calibration (must match device calibration)
WL_C0 = 340.0
WL_C1 = 1.62
WL_C2 = 0.0001

MAGIC = b"FCEM"  # Fluor Cast EEM binary format magic


def pixel_to_wavelength(pixel: int) -> float:
    """Convert CCD pixel index to emission wavelength."""
    p = float(pixel)
    return WL_C0 + WL_C1 * p + WL_C2 * p * p


def parse_binary_eem(filepath: str) -> dict:
    """
    Parse binary EEM file.

    Format:
      [magic:4][timestamp:4][temp:4f][duration:4u]
      [matrix: 8×256 × 2u = 4096 bytes]
      [mask:   8×256 × 1u = 2048 bytes]
      [features: 48×4f = 192 bytes]
    """
    with open(filepath, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError(f"Invalid magic: {magic}")

        timestamp = struct.unpack("<I", f.read(4))[0]
        temp_c = struct.unpack("<f", f.read(4))[0]
        duration_ms = struct.unpack("<I", f.read(4))[0]

        # EEM matrix
        matrix = []
        for w in range(EEM_ROWS):
            row = []
            for p in range(EEM_COLS):
                val = struct.unpack("<H", f.read(2))[0]
                row.append(val)
            matrix.append(row)

        # Mask
        mask = []
        for w in range(EEM_ROWS):
            row = []
            for p in range(EEM_COLS):
                m = f.read(1)[0]
                row.append(m)
            mask.append(row)

        # Features
        features = []
        for i in range(FEATURE_COUNT):
            features.append(struct.unpack("<f", f.read(4))[0])

    return {
        "timestamp": timestamp,
        "temp_c": temp_c,
        "duration_ms": duration_ms,
        "matrix": matrix,
        "mask": mask,
        "features": features,
    }


def export_csv(eem: dict, filepath: str):
    """Export EEM as CSV matrix (rows=excitation, cols=emission pixels)."""
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)

        # Header with metadata
        writer.writerow([f"# Fluor Cast EEM Export"])
        writer.writerow([f"# Timestamp: {eem['timestamp']}"])
        writer.writerow([f"# Temperature: {eem['temp_c']:.1f} C"])
        writer.writerow([f"# Duration: {eem['duration_ms']} ms"])
        writer.writerow([f"# Excitation wavelengths (nm): {EX_WAVELENGTHS}"])
        writer.writerow([])

        # Emission wavelength header row
        header = ["Ex\\Em (nm)"]
        for p in range(EEM_COLS):
            header.append(f"{pixel_to_wavelength(p):.1f}")
        writer.writerow(header)

        # EEM matrix rows
        for w in range(EEM_ROWS):
            row = [f"Ex_{EX_WAVELENGTHS[w]}"]
            for p in range(EEM_COLS):
                val = eem["matrix"][w][p]
                if eem["mask"][w][p] == 0:
                    row.append("")  # masked (scatter)
                else:
                    row.append(val)
            writer.writerow(row)

        # Features
        writer.writerow([])
        writer.writerow(["# Features"])
        for i, feat in enumerate(eem["features"]):
            writer.writerow([f"feature_{i}", f"{feat:.6f}"])


def export_matlab(eem: dict, filepath: str):
    """Export EEM as MATLAB .mat file (compatible with drEEM/ParafacView)."""
    try:
        from scipy.io import savemat
    except ImportError:
        # Fallback: export as Octave text format
        print("scipy not available, exporting as Octave text format")
        with open(filepath, "w") as f:
            f.write("% Fluor Cast EEM data (Octave format)\n")
            f.write(f"% Timestamp: {eem['timestamp']}\n")
            f.write(f"% Temperature: {eem['temp_c']:.1f}\n\n")

            f.write("EX = [")
            f.write(" ".join(str(w) for w in EX_WAVELENGTHS))
            f.write("];\n")

            # Emission wavelengths
            f.write("EM = [")
            f.write(" ".join(f"{pixel_to_wavelength(p):.1f}" for p in range(EEM_COLS)))
            f.write("];\n")

            # EEM matrix
            f.write("EEM = [\n")
            for w in range(EEM_ROWS):
                row = eem["matrix"][w]
                f.write(" ".join(str(v) for v in row))
                f.write("\n")
            f.write("];\n")

            # Mask
            f.write("mask = [\n")
            for w in range(EEM_ROWS):
                f.write(" ".join(str(m) for m in eem["mask"][w]))
                f.write("\n")
            f.write("];\n")

            # Features
            f.write("features = [")
            f.write(" ".join(str(f) for f in eem["features"]))
            f.write("];\n")
        return

    # scipy available
    import numpy as np
    data = {
        "EX": np.array(EX_WAVELENGTHS, dtype=np.float64),
        "EM": np.array([pixel_to_wavelength(p) for p in range(EEM_COLS)], dtype=np.float64),
        "EEM": np.array(eem["matrix"], dtype=np.float64),
        "mask": np.array(eem["mask"], dtype=np.uint8),
        "features": np.array(eem["features"], dtype=np.float64),
        "timestamp": eem["timestamp"],
        "temp_c": eem["temp_c"],
        "duration_ms": eem["duration_ms"],
    }
    savemat(filepath, data, oned_as="column")


def export_json(eem: dict, filepath: str):
    """Export EEM as JSON."""
    # Build emission wavelength axis
    emission_wl = [pixel_to_wavelength(p) for p in range(EEM_COLS)]

    data = {
        "format": "fluor-cast-eem",
        "version": "1.0",
        "timestamp": eem["timestamp"],
        "temperature_c": eem["temp_c"],
        "duration_ms": eem["duration_ms"],
        "excitation_wavelengths_nm": EX_WAVELENGTHS,
        "emission_wavelengths_nm": emission_wl,
        "matrix": eem["matrix"],
        "mask": eem["mask"],
        "features": eem["features"],
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def plot_eem(eem: dict, filepath: str):
    """Generate EEM heatmap PNG."""
    try:
        import numpy as np
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import LogNorm
    except ImportError:
        print("matplotlib/numpy required for plotting")
        return

    matrix = np.array(eem["matrix"], dtype=np.float64)
    matrix[matrix == 0] = 0.1  # avoid log(0)

    fig, ax = plt.subplots(figsize=(10, 6))

    im = ax.imshow(
        matrix,
        aspect="auto",
        origin="lower",
        extent=[340, 755, 250, 525],
        cmap="jet",
        interpolation="nearest",
        norm=LogNorm(vmin=1, vmax=matrix.max()),
    )

    ax.set_xlabel("Emission Wavelength (nm)", fontsize=12)
    ax.set_ylabel("Excitation Wavelength (nm)", fontsize=12)
    ax.set_title(f"Fluor Cast EEM — {eem['temp_c']:.1f}°C, {eem['duration_ms']}ms", fontsize=14)

    plt.colorbar(im, ax=ax, label="Intensity (counts)")
    plt.tight_layout()
    plt.savefig(filepath, dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Export Fluor Cast EEM logs")
    parser.add_argument("input", help="Input file or directory")
    parser.add_argument("output", help="Output file or directory")
    parser.add_argument("--format", default="csv",
                       choices=["csv", "mat", "json", "all"],
                       help="Output format")
    parser.add_argument("--plot", action="store_true", help="Also generate PNG plot")
    args = parser.parse_args()

    if os.path.isdir(args.input):
        # Batch export all .bin files in directory
        os.makedirs(args.output, exist_ok=True)
        files = [f for f in os.listdir(args.input) if f.endswith(".bin")]
        print(f"Found {len(files)} EEM files")

        for fname in sorted(files):
            inpath = os.path.join(args.input, fname)
            base = os.path.splitext(fname)[0]
            print(f"  Exporting {fname}...")

            try:
                eem = parse_binary_eem(inpath)

                if args.format in ("csv", "all"):
                    export_csv(eem, os.path.join(args.output, f"{base}.csv"))
                if args.format in ("mat", "all"):
                    export_matlab(eem, os.path.join(args.output, f"{base}.mat"))
                if args.format in ("json", "all"):
                    export_json(eem, os.path.join(args.output, f"{base}.json"))
                if args.plot:
                    plot_eem(eem, os.path.join(args.output, f"{base}.png"))

            except Exception as e:
                print(f"  Error: {e}")

    else:
        # Single file
        eem = parse_binary_eem(args.input)
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

        if args.format in ("csv", "all"):
            export_csv(eem, args.output + ".csv")
        if args.format in ("mat", "all"):
            export_matlab(eem, args.output + ".mat")
        if args.format in ("json", "all"):
            export_json(eem, args.output + ".json")
        if args.plot:
            plot_eem(eem, args.output + ".png")

    print("Export complete.")


if __name__ == "__main__":
    main()