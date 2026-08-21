#!/usr/bin/env python3
"""
Mussel Watch — Gape Data Visualizer

Reads the CSV log file from the SD card and plots the gape-angle time series
for all mussels, along with water temperature and dissolved oxygen.

Usage:
    python3 visualize_gape.py <logfile.csv> [--output plot.png]

If no output file is specified, the plot is displayed interactively.
"""

import sys
import argparse
import csv
from datetime import datetime, timedelta

try:
    import matplotlib
    matplotlib.use("Agg")  # non-interactive default; overridden if no --output
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
except ImportError:
    print("Error: matplotlib is required. Install with: pip install matplotlib")
    sys.exit(1)


def parse_log(path):
    """Parse the Mussel Watch CSV log file.
    Returns a dict of lists keyed by column name."""
    data = {
        "timestamp": [],
        "gape_a": [], "gape_b": [], "gape_c": [], "gape_d": [],
        "temp_c": [], "do_mgl": [], "depth_m": [],
        "battery_v": [], "alert": []
    }

    with open(path, "r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            if len(row) < 10:
                continue

            try:
                ts = int(row[0])
                data["timestamp"].append(ts)
                data["gape_a"].append(float(row[1]) if row[1] != "NaN" else None)
                data["gape_b"].append(float(row[2]) if row[2] != "NaN" else None)
                data["gape_c"].append(float(row[3]) if row[3] != "NaN" else None)
                data["gape_d"].append(float(row[4]) if row[4] != "NaN" else None)
                data["temp_c"].append(float(row[5]))
                data["do_mgl"].append(float(row[6]))
                data["depth_m"].append(float(row[7]))
                data["battery_v"].append(float(row[8]))
                data["alert"].append(int(row[9]))
            except (ValueError, IndexError):
                continue

    return data


def plot_data(data, output):
    """Create a multi-panel plot of gape angles and water quality."""
    timestamps = [datetime.fromtimestamp(ts) for ts in data["timestamp"]]

    fig, axes = plt.subplots(4, 1, figsize=(14, 12), sharex=True)
    fig.suptitle("Mussel Watch — Deployment Data", fontsize=14, fontweight="bold")

    # Panel 1: Gape angles
    ax = axes[0]
    colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12"]
    labels = ["Mussel A", "Mussel B", "Mussel C", "Mussel D"]
    gape_keys = ["gape_a", "gape_b", "gape_c", "gape_d"]

    for i, (key, label, color) in enumerate(zip(gape_keys, labels, colors)):
        values = data[key]
        # Only plot non-None values
        ts_valid = [t for t, v in zip(timestamps, values) if v is not None]
        val_valid = [v for v in values if v is not None]
        if val_valid:
            ax.plot(ts_valid, val_valid, color=color, label=label, linewidth=1.2)
            ax.axhline(y=2.0, color="gray", linestyle="--", alpha=0.3, linewidth=0.8)

    ax.set_ylabel("Gape Angle (°)")
    ax.set_ylim(-0.5, 16)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Bivalve Valve Gape Angle")
    ax.grid(True, alpha=0.3)

    # Panel 2: Water temperature
    ax = axes[1]
    ax.plot(timestamps, data["temp_c"], color="#e67e22", linewidth=1.2)
    ax.set_ylabel("Temperature (°C)")
    ax.set_title("Water Temperature (DS18B20)")
    ax.grid(True, alpha=0.3)

    # Panel 3: Dissolved oxygen
    ax = axes[2]
    ax.plot(timestamps, data["do_mgl"], color="#2980b9", linewidth=1.2)
    ax.axhline(y=4.0, color="red", linestyle="--", alpha=0.5, linewidth=0.8,
              label="Hypoxia threshold (4 mg/L)")
    ax.set_ylabel("Dissolved O₂ (mg/L)")
    ax.set_title("Dissolved Oxygen (Atlas DO)")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    # Panel 4: Alert events
    ax = axes[3]
    alert_colors = {1: "#f39c12", 2: "#e74c3c", 3: "#9b59b6",
                    4: "#c0392b", 5: "#e67e22", 6: "#2980b9", 7: "#7f8c8d"}
    alert_names = {1: "Closure", 2: "Sustained", 3: "Rhythm", 4: "Multi-mussel",
                   5: "Temp", 6: "DO", 7: "Low batt"}

    for code, color in alert_colors.items():
        ts_alert = [t for t, a in zip(timestamps, data["alert"]) if a == code]
        if ts_alert:
            ax.scatter(ts_alert, [code] * len(ts_alert), color=color,
                      s=50, zorder=5, label=alert_names.get(code, f"Code {code}"))

    ax.set_ylabel("Alert Code")
    ax.set_yticks(range(0, 8))
    ax.set_title("Alert Events")
    ax.legend(loc="upper right", fontsize=7)
    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    plt.xticks(rotation=45)
    plt.tight_layout()

    if output:
        plt.savefig(output, dpi=150)
        print(f"Plot saved to {output}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Visualize Mussel Watch gape data")
    parser.add_argument("logfile", help="Path to the CSV log file from the SD card")
    parser.add_argument("--output", "-o", default=None,
                       help="Output PNG file (if not specified, display interactively)")
    args = parser.parse_args()

    if not args.output:
        matplotlib.use("TkAgg")  # interactive

    data = parse_log(args.logfile)
    if not data["timestamp"]:
        print("Error: no valid data found in log file")
        sys.exit(1)

    print(f"Loaded {len(data['timestamp'])} data points")
    print(f"  Time range: {datetime.fromtimestamp(data['timestamp'][0])} "
          f"→ {datetime.fromtimestamp(data['timestamp'][-1])}")
    print(f"  Alerts: {sum(1 for a in data['alert'] if a > 0)} events")

    plot_data(data, args.output)


if __name__ == "__main__":
    main()