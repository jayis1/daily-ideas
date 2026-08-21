#!/usr/bin/env python3
"""
Sonar Cast — bathy_plot.py
Plot a logged bathymetry CSV (from the microSD) as a depth-colored track on
an interactive leaflet.js map.  Saves an HTML file you can open in a browser.

Usage:
    python3 bathy_plot.py path/to/bathy_20260805.csv [--out map.html]

Requires: pandas, folium
    pip install pandas folium
"""
import argparse
import sys

try:
    import pandas as pd
    import folium
    from folium.plugins import MarkerCluster
except ImportError:
    print("Install: pip install pandas folium")
    sys.exit(1)


def main():
    p = argparse.ArgumentParser(description="Plot Sonar Cast bathymetry CSV on a map")
    p.add_argument("csv", help="Path to bathy_*.csv")
    p.add_argument("--out", default="sonar_cast_map.html", help="Output HTML file")
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    if "lat" not in df.columns or "lon" not in df.columns:
        print("CSV must have lat, lon, depth_m columns")
        sys.exit(1)

    df = df[(df["lat"] != 0) & (df["lon"] != 0) & (df["depth_m"] > 0)]

    if df.empty:
        print("No valid GPS+depth points in CSV.")
        sys.exit(1)

    print(f"Loaded {len(df)} soundings.  "
          f"Depth range: {df['depth_m'].min():.1f}–{df['depth_m'].max():.1f} m")

    cmap = folium.LinearColormap(
        colors=["#1a9850", "#a6d96a", "#ffffbf", "#fdae61", "#d73027"],
        vmin=df["depth_m"].min(), vmax=df["depth_m"].max(),
        caption="Depth (m)"
    )

    m = folium.Map(location=[df["lat"].mean(), df["lon"].mean()],
                   zoom_start=14, tiles="OpenStreetMap")

    # Track line
    folium.PolyLine(
        list(zip(df["lat"], df["lon"])),
        color="blue", weight=2, opacity=0.5
    ).add_to(m)

    # Depth-colored markers
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=4,
            fill=True, fill_color=cmap(row["depth_m"]),
            color=None, fill_opacity=0.8,
            popup=(f"Depth: {row['depth_m']:.2f} m<br>"
                   f"Bottom: {row.get('bottom_type','?')}<br>"
                   f"Fish: {row.get('fish_count',0)}<br>"
                   f"Temp: {row.get('temp_c','?')}°C<br>"
                   f"Time: {row.get('unix_ts','?')}")
        ).add_to(m)

    cmap.add_to(m)
    m.save(args.out)
    print(f"Saved map to {args.out} — open in a browser.")


if __name__ == "__main__":
    main()