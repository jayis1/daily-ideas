#!/usr/bin/env python3
"""
Lode Sweep — survey_map.py
Plot a logged survey CSV as a GPS-tagged target map.

Reads a survey CSV from the SD card and plots detections on a leaflet.js
map (saved as an interactive HTML file) with class-colored markers and
depth labels.

Usage:
    python3 survey_map.py survey_20260807.csv [--output map.html]

Requires: pandas, folium, matplotlib
    pip install pandas folium matplotlib
"""
import argparse
import pandas as pd
import folium
from folium import Popup

CLASS_NAMES = ["Iron", "Foil", "Nickel", "Pull-Tab",
               "Zinc", "Gold", "Copper", "Silver"]
CLASS_COLORS = ["gray", "lightgray", "green", "blue",
                "orange", "red", "silver", "gold"]
CLASS_ICONS = ["trash", "trash", "star", "remove",
               "star", "star", "star", "star"]


def main():
    parser = argparse.ArgumentParser(description="Lode Sweep survey map")
    parser.add_argument("csv_file", help="Survey CSV file path")
    parser.add_argument("--output", "-o", default="survey_map.html",
                        help="Output HTML file")
    args = parser.parse_args()

    df = pd.read_csv(args.csv_file)

    # Filter out rows without GPS fix
    df = df[(df["lat"] != 0) & (df["lon"] != 0)]
    if len(df) == 0:
        print("No GPS-tagged detections found in CSV.")
        return

    # Center map on mean of detections
    center = [df["lat"].mean(), df["lon"].mean()]
    m = folium.Map(location=center, zoom_start=18, tiles="OpenStreetMap")

    # Add markers for each detection
    for _, row in df.iterrows():
        cls_name = row["target_class"]
        cls_idx = CLASS_NAMES.index(cls_name) if cls_name in CLASS_NAMES else -1
        color = CLASS_COLORS[cls_idx] if cls_idx >= 0 else "purple"
        icon = CLASS_ICONS[cls_idx] if cls_idx >= 0 else "info-sign"

        popup_text = (
            f"<b>{cls_name}</b><br>"
            f"Depth: {row['depth_cm']:.0f} cm<br>"
            f"Confidence: {row['confidence']*100:.0f}%<br>"
            f"Signal: {row['signal']:.3f}<br>"
            f"Time: {row['unix_ts']}"
        )
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=Popup(popup_text, max_width=200),
            icon=folium.Icon(color=color, icon=icon, prefix="glyphicon"),
        ).add_to(m)

    # Add a heatmap-like path connecting detections in order
    coords = list(zip(df["lat"], df["lon"]))
    if len(coords) > 1:
        folium.PolyLine(coords, color="blue", weight=2, opacity=0.5,
                        tooltip="Survey path").add_to(m)

    # Summary
    print(f"Loaded {len(df)} detections from {args.csv_file}")
    print("\nDetections by class:")
    print(df["target_class"].value_counts().to_string())
    print(f"\nMean depth: {df['depth_cm'].mean():.1f} cm")
    print(f"Max depth:  {df['depth_cm'].max():.1f} cm")

    m.save(args.output)
    print(f"\nSaved interactive map to {args.output}")
    print(f"Open in a browser: file://$(pwd)/{args.output}")


if __name__ == "__main__":
    main()