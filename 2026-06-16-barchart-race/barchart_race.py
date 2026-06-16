#!/usr/bin/env python3
"""
Barchart Race — Animated ASCII Bar Chart Race Visualizer

Generates animated bar chart races in the terminal. Watch values compete
and rankings shift over time with smooth ASCII animations.

Usage:
    python3 barchart_race.py              # built-in tech company revenue demo
    python3 barchart_race.py --sample      # choose from built-in datasets
    python3 barchart_race.py --data data.csv
    python3 barchart_race.py --speed 2     # animation speed (frames/sec)
    python3 barchart_race.py --top 5       # show only top N bars
    python3 barchart_race.py --export      # export frames as text
    python3 barchart_race.py --solve       # just output final ranking
    python3 barchart_race.py --percent     # percentage mode (share of total)
    python3 barchart_race.py --growth      # growth rate mode (change from first)
    python3 barchart_race.py --html        # export as animated HTML
    python3 barchart_race.py --compare 0 -1 # compare two periods side by side
"""

import argparse
import csv
import html
import io
import json
import math
import os
import random
import re
import sys
import time
from collections import defaultdict
from copy import deepcopy

VERSION = "2.0.0"

# ─── Built-in Datasets ────────────────────────────────────────────────

SAMPLE_DATASETS = {
    "tech-revenue": {
        "title": "Tech Company Revenue ($B)",
        "unit": "$B",
        "description": "Quarterly revenue for major tech companies",
        "data": {
            "Apple":      [65, 68, 72, 78, 83, 87, 94, 100, 108, 117, 125, 131, 139, 150],
            "Microsoft":  [45, 48, 52, 56, 61, 65, 70, 75,  80,  86,  92,  99, 106, 115],
            "Google":     [40, 43, 46, 50, 54, 58, 62, 67,  72,  78,  84,  90,  96, 103],
            "Amazon":     [35, 38, 42, 47, 52, 58, 64, 70,  77,  84,  92, 100, 110, 120],
            "Meta":       [28, 30, 33, 36, 39, 42, 45, 48,  52,  56,  60,  65,  70,  76],
            "Samsung":    [50, 52, 55, 58, 61, 64, 67, 70,  73,  76,  79,  82,  86,  90],
            "Netflix":    [10, 12, 14, 17, 20, 24, 28, 32,  36,  40,  44,  48,  52,  57],
            "Tesla":      [ 5,  7, 10, 14, 18, 24, 31, 38,  46,  54,  63,  72,  82,  96],
            "NVIDIA":     [ 8,  9, 10, 12, 16, 22, 30, 40,  52,  60,  72,  85,  100, 120],
            "Intel":      [20, 20, 19, 18, 19, 20, 21, 22,  23,  24,  25,  25,  26,  26],
        },
        "labels": ["Q1'21","Q2'21","Q3'21","Q4'21","Q1'22","Q2'22","Q3'22","Q4'22",
                    "Q1'23","Q2'23","Q3'23","Q4'23","Q1'24","Q2'24"]
    },

    "olympic-medals": {
        "title": "All-Time Olympic Medal Count",
        "unit": "medals",
        "description": "Cumulative Summer Olympic medals by country",
        "data": {
            "USA":       [2400, 2450, 2500, 2520, 2540, 2570, 2600, 2630, 2660, 2680, 2700, 2720, 2750, 2780],
            "USSR/RUS":  [1200, 1220, 1240, 1260, 1280, 1300, 1320, 1340, 1360, 1380, 1400, 1420, 1430, 1440],
            "Germany":   [ 800,  820,  840,  860,  880,  900,  920,  940,  960,  975,  990, 1005, 1020, 1035],
            "UK":        [ 700,  720,  740,  760,  780,  800,  820,  840,  860,  880,  900,  920,  940,  960],
            "France":    [ 650,  670,  690,  710,  730,  750,  770,  790,  810,  830,  850,  870,  890,  910],
            "China":     [ 200,  250,  310,  380,  460,  540,  620,  700,  780,  840,  900,  950, 1000, 1050],
            "Australia": [ 450,  460,  475,  490,  510,  530,  550,  570,  590,  610,  630,  650,  670,  690],
            "Japan":     [ 350,  370,  390,  410,  430,  450,  470,  490,  510,  540,  570,  600,  630,  660],
            "Italy":     [ 500,  510,  520,  535,  550,  565,  580,  595,  610,  625,  640,  655,  670,  685],
            "Hungary":   [ 400,  405,  410,  415,  420,  425,  430,  435,  440,  445,  450,  455,  460,  465],
        },
        "labels": ["1984","1988","1992","1996","2000","2004","2008","2012",
                    "2016","2020a","2020b","2020c","2024a","2024b"]
    },

    "programming-languages": {
        "title": "Programming Language Popularity (TIOBE Index)",
        "unit": "%",
        "description": "Estimated popularity over time",
        "data": {
            "Python":    [ 5,  6,  7,  8, 10, 12, 14, 16, 18, 20, 23, 26, 28, 30],
            "C":         [16, 15, 14, 13, 12, 12, 12, 12, 13, 13, 12, 11, 10,  9],
            "Java":      [20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10,  9,  8,  7],
            "C++":       [ 8,  8,  7,  7,  7,  7,  7,  7,  7,  7,  8,  8,  9, 10],
            "JavaScript":[ 4,  4,  5,  5,  6,  6,  7,  7,  7,  7,  7,  7,  6,  6],
            "Rust":      [ 0,  0,  0,  0,  1,  1,  1,  2,  2,  3,  3,  4,  5,  6],
            "Go":        [ 1,  2,  2,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3,  3],
            "Swift":     [ 0,  1,  2,  3,  3,  3,  3,  3,  3,  3,  3,  2,  2,  2],
            "TypeScript":[ 0,  0,  1,  1,  1,  2,  2,  2,  3,  3,  4,  4,  5,  5],
            "Kotlin":     [ 0,  0,  0,  0,  1,  1,  1,  2,  2,  2,  2,  2,  2,  2],
        },
        "labels": ["2011","2012","2013","2014","2015","2016","2017","2018",
                    "2019","2020","2021","2022","2023","2024"]
    },

    "world-population": {
        "title": "Country Population (Millions)",
        "unit": "M",
        "description": "Population growth of most populous countries",
        "data": {
            "China":     [1260, 1280, 1300, 1320, 1340, 1360, 1380, 1400, 1410, 1415, 1420, 1425, 1420, 1410],
            "India":     [1040, 1070, 1100, 1130, 1170, 1210, 1250, 1290, 1330, 1370, 1410, 1425, 1430, 1440],
            "USA":       [ 285,  288,  291,  295,  298,  302,  306,  310,  314,  318,  331,  333,  335,  337],
            "Indonesia": [ 215,  220,  225,  230,  237,  243,  250,  258,  265,  270,  274,  276,  278,  280],
            "Brazil":    [ 175,  180,  185,  190,  195,  200,  205,  209,  212,  214,  215,  216,  216,  217],
            "Nigeria":   [ 120,  130,  140,  150,  160,  175,  190,  205,  210,  218,  220,  225,  228,  232],
            "Bangladesh":[ 140,  145,  150,  155,  158,  161,  163,  166,  168,  170,  172,  173,  174,  175],
            "Russia":    [ 146,  145,  144,  144,  144,  144,  144,  145,  146,  146,  146,  146,  144,  144],
        },
        "labels": ["2000","2002","2004","2006","2008","2010","2012","2014",
                    "2016","2018","2020","2022","2024","2026"]
    },

    "crypto-marketcap": {
        "title": "Cryptocurrency Market Cap ($B)",
        "unit": "$B",
        "description": "Market cap of top cryptocurrencies",
        "data": {
            "Bitcoin":   [200, 350, 800, 120, 400, 700, 1100, 550, 900, 1300, 500, 800, 1400, 1900],
            "Ethereum":  [ 30,  70, 350,  40, 150, 300,  500, 200, 400,  600, 220, 350,  600,  800],
            "BNB":       [  2,   5,  30,   5,  30,  60,  100,  50,  60,   90,  50,  55,  100,  120],
            "XRP":       [ 10,  20,  80,  10,  30,  50,   80,  35,  40,   60,  30,  40,   80,  130],
            "Cardano":   [  0,   0,  30,   2,  10,  30,   70,  15,  15,   50,  15,  20,   30,   40],
            "Solana":    [  0,   0,   0,   0,   0,   2,   60,  10,  15,   50,   8,  15,   60,  100],
            "Dogecoin":  [  0,   0,   2,   0,   1,   5,   80,  15,  10,   30,   8,  10,   20,   30],
            "Polygon":  [  0,   0,   0,   0,   1,   2,   15,   5,   8,   15,   5,   8,   15,   20],
        },
        "labels": ["2017","2017Q2","2018","2019","2020","2020Q2","2021","2022",
                    "2022Q2","2023","2023Q2","2024Q1","2024Q2","2025"]
    },
}

# ─── ANSI Colors ──────────────────────────────────────────────────────

COLORS = [
    "\033[91m",  # Red
    "\033[92m",  # Green
    "\033[93m",  # Yellow
    "\033[94m",  # Blue
    "\033[95m",  # Magenta
    "\033[96m",  # Cyan
    "\033[31m",  # Dark Red
    "\033[32m",  # Dark Green
    "\033[33m",  # Dark Yellow
    "\033[34m",  # Dark Blue
    "\033[35m",  # Dark Magenta
    "\033[36m",  # Dark Cyan
    "\033[97m",  # White
    "\033[90m",  # Gray
]
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# HTML color palette (hex) — same color philosophy as ANSI but web-friendly
HTML_COLORS = [
    "#e74c3c", "#2ecc71", "#f1c40f", "#3498db", "#9b59b6",
    "#1abc9c", "#e67e22", "#e84393", "#00cec9", "#6c5ce7",
    "#fd79a8", "#00b894", "#fdcb6e", "#74b9ff",
]

BAR_CHARS = ["█", "▓", "▒", "░"]  # full, dark, medium, light fill

# ─── Sparkline Characters ─────────────────────────────────────────────
# Low to high: minimum → maximum
SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"


# ─── Data Loading ──────────────────────────────────────────────────────

def load_csv(filepath):
    """Load data from CSV file.
    
    Expected format:
        label, name1, name2, name3, ...
        period1, val1, val2, val3, ...
        period2, val1, val2, val3, ...
    """
    with open(filepath, "r") as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if len(rows) < 2:
        raise ValueError("CSV must have a header row and at least one data row")
    
    header = rows[0]
    labels = []
    series = {name.strip(): [] for name in header[1:]}
    
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        labels.append(row[0].strip())
        for i, name in enumerate(header[1:]):
            key = name.strip()
            try:
                val = float(row[i + 1].strip())
            except (ValueError, IndexError):
                val = 0
            series[key].append(val)
    
    return {
        "title": os.path.splitext(os.path.basename(filepath))[0],
        "unit": "",
        "data": series,
        "labels": labels,
    }


def load_json(filepath):
    """Load data from JSON file.
    
    Expected format:
    {
        "title": "My Chart",
        "unit": "$",
        "data": {
            "Series A": [1, 2, 3, ...],
            "Series B": [4, 5, 6, ...]
        },
        "labels": ["Jan", "Feb", "Mar", ...]
    }
    """
    with open(filepath, "r") as f:
        data = json.load(f)
    
    if "data" not in data:
        raise ValueError("JSON must contain a 'data' key with series")
    
    # Validate all series have same length
    lengths = {len(v) for v in data["data"].values()}
    if len(lengths) > 1:
        raise ValueError(f"All series must have the same length, got: {lengths}")
    
    num_steps = lengths.pop() if lengths else 0
    if "labels" not in data:
        data["labels"] = [str(i + 1) for i in range(num_steps)]
    
    data.setdefault("title", "Bar Chart Race")
    data.setdefault("unit", "")
    
    return data


def validate_data(dataset):
    """Validate and normalize a dataset."""
    data = dataset["data"]
    if not data:
        raise ValueError("Dataset has no data series")
    
    # Ensure all series have same length
    series_names = list(data.keys())
    length = len(data[series_names[0]])
    for name in series_names:
        if len(data[name]) != length:
            raise ValueError(f"Series '{name}' has length {len(data[name])}, expected {length}")
    
    if "labels" not in dataset or not dataset["labels"]:
        dataset["labels"] = [str(i + 1) for i in range(length)]
    elif len(dataset["labels"]) != length:
        # Pad or truncate labels
        while len(dataset["labels"]) < length:
            dataset["labels"].append(str(len(dataset["labels"]) + 1))
        dataset["labels"] = dataset["labels"][:length]
    
    dataset.setdefault("title", "Bar Chart Race")
    dataset.setdefault("unit", "")
    
    return dataset


def interpolate_data(dataset, steps_per_period=5):
    """Create smooth interpolation between data points for animation."""
    data = dataset["data"]
    labels = dataset["labels"]
    series_names = list(data.keys())
    num_periods = len(data[series_names[0]])
    
    if num_periods < 2:
        return dataset
    
    # Create interpolated data
    interp_data = {}
    interp_labels = []
    
    for name in series_names:
        interp_data[name] = []
    
    for i in range(num_periods - 1):
        for j in range(steps_per_period):
            t = j / steps_per_period
            for name in series_names:
                start_val = data[name][i]
                end_val = data[name][i + 1]
                # Smooth easing (ease-in-out)
                t_smooth = t * t * (3 - 2 * t)
                interp_val = start_val + (end_val - start_val) * t_smooth
                interp_data[name].append(interp_val)
        interp_labels.append(labels[i])
    
    # Add final frame
    for name in series_names:
        interp_data[name].append(data[name][-1])
    interp_labels.append(labels[-1])
    
    result = deepcopy(dataset)
    result["data"] = interp_data
    result["labels"] = interp_labels
    return result


# ─── Data Transformations ─────────────────────────────────────────────

def transform_percentage(dataset):
    """Transform data to show each series as a percentage of total per period.
    
    This is useful for market share, vote share, etc. where you want to
    see relative proportions rather than absolute values.
    """
    data = dataset["data"]
    series_names = list(data.keys())
    num_periods = len(data[series_names[0]])
    
    pct_data = {}
    for name in series_names:
        pct_data[name] = []
    
    for i in range(num_periods):
        total = sum(abs(data[n][i]) for n in series_names)
        total = max(total, 1e-10)  # Avoid division by zero
        for name in series_names:
            pct_data[name].append(round((data[name][i] / total) * 100, 2))
    
    result = deepcopy(dataset)
    result["data"] = pct_data
    result["unit"] = "%"
    result["title"] = dataset.get("title", "") + " — Share %"
    return result


def transform_growth(dataset):
    """Transform data to show growth from first period (index = 0).
    
    Each value becomes (current - first) / |first| * 100, giving the
    percentage change from the starting point. If the first value is 0,
    shows absolute change instead.
    """
    data = dataset["data"]
    series_names = list(data.keys())
    
    growth_data = {}
    for name in series_names:
        first_val = data[name][0]
        growth_vals = []
        for v in data[name]:
            if abs(first_val) > 1e-10:
                growth_vals.append(round(((v - first_val) / abs(first_val)) * 100, 2))
            else:
                # If starting value is 0, just show absolute change
                growth_vals.append(round(v - first_val, 2))
        growth_data[name] = growth_vals
    
    result = deepcopy(dataset)
    result["data"] = growth_data
    result["unit"] = "%"
    result["title"] = dataset.get("title", "") + " — Growth %"
    return result


# ─── Sparkline ─────────────────────────────────────────────────────────

def sparkline(values, width=12):
    """Render a unicode sparkline from a list of numeric values.
    
    Returns a string of box-drawing characters representing the values.
    Characters range from ▁ (minimum) to █ (maximum).
    """
    if not values:
        return ""
    
    vmin = min(values)
    vmax = max(values)
    vrange = vmax - vmin
    
    # If all values are the same, show a mid-height line
    if vrange < 1e-10:
        return SPARKLINE_CHARS[len(SPARKLINE_CHARS) // 2] * min(len(values), width)
    
    chars = []
    for v in values[:width]:
        normalized = (v - vmin) / vrange
        idx = int(normalized * (len(SPARKLINE_CHARS) - 1))
        idx = max(0, min(idx, len(SPARKLINE_CHARS) - 1))
        chars.append(SPARKLINE_CHARS[idx])
    
    return "".join(chars)


# ─── Rendering ─────────────────────────────────────────────────────────

def get_terminal_width():
    """Get terminal width, default to 80."""
    try:
        return os.get_terminal_size().columns
    except (OSError, AttributeError):
        return 80


def get_terminal_height():
    """Get terminal height, default to 24."""
    try:
        return os.get_terminal_size().lines
    except (OSError, AttributeError):
        return 24


def format_value(val, unit=""):
    """Format a value for display."""
    if abs(val) >= 1000:
        return f"{val:,.0f}{unit}"
    elif abs(val) >= 1:
        return f"{val:.1f}{unit}"
    else:
        return f"{val:.2f}{unit}"


def render_frame(dataset, frame_idx, top_n=None, bar_width=None, color=True):
    """Render a single frame of the bar chart race as a string."""
    data = dataset["data"]
    title = dataset.get("title", "Bar Chart Race")
    unit = dataset.get("unit", "")
    labels = dataset.get("labels", [])
    
    series_names = list(data.keys())
    
    if not series_names:
        return "No data to display"
    
    num_frames = len(data[series_names[0]])
    frame_idx = max(0, min(frame_idx, num_frames - 1))
    
    # Get current values
    current_values = {name: data[name][frame_idx] for name in series_names}
    
    # Sort by value descending
    ranked = sorted(current_values.items(), key=lambda x: x[1], reverse=True)
    
    if top_n:
        ranked = ranked[:top_n]
    
    # Determine bar width
    if bar_width is None:
        term_width = get_terminal_width()
        max_name_len = max(len(name) for name, _ in ranked) if ranked else 10
        max_val_len = max(len(format_value(val, unit)) for _, val in ranked) if ranked else 6
        # Leave room for rank, name, value, some padding
        bar_width = max(10, term_width - max_name_len - max_val_len - 10)
    
    max_val = max(abs(val) for _, val in ranked) if ranked else 1
    if max_val == 0:
        max_val = 1
    
    # Build the frame
    lines = []
    
    # Title and period label
    label_text = labels[frame_idx] if frame_idx < len(labels) else str(frame_idx + 1)
    
    # Header
    header = f"{BOLD}{title}{RESET}" if color else title
    lines.append(header)
    lines.append(f"{'─' * 60}")
    
    period_line = f"  Period: {BOLD}{label_text}{RESET}" if color else f"  Period: {label_text}"
    lines.append(period_line)
    lines.append("")
    
    for rank, (name, val) in enumerate(ranked, 1):
        # Calculate bar length
        bar_len = int((abs(val) / max_val) * bar_width)
        bar_len = max(0, min(bar_len, bar_width))
        
        # Choose color — color by name (consistent per series across frames)
        name_idx = list(dataset["data"].keys()).index(name) if name in dataset["data"] else rank - 1
        color_idx = name_idx % len(COLORS)
        c = COLORS[color_idx] if color else ""
        r = RESET if color else ""
        
        # Choose bar character
        bar_char = BAR_CHARS[0]
        
        # Build bar
        bar = c + bar_char * bar_len + r
        
        # Format value
        val_str = format_value(val, unit)
        
        # Rank with medal emoji for top 3
        if rank == 1:
            rank_str = "🥇" if color else "#1"
        elif rank == 2:
            rank_str = "🥈" if color else "#2"
        elif rank == 3:
            rank_str = "🥉" if color else "#3"
        else:
            rank_str = f"#{rank}"
        
        # Right-align name padding
        max_name_len = max(len(n) for n, _ in ranked) if ranked else 10
        padded_name = name.rjust(max_name_len)
        
        if color:
            line = f" {rank_str} {c}{BOLD}{padded_name}{r} {bar} {val_str}"
        else:
            line = f" {rank_str} {padded_name} {bar} {val_str}"
        
        lines.append(line)
    
    # Footer with progress
    progress = frame_idx / max(num_frames - 1, 1)
    bar_total = 40
    filled = int(progress * bar_total)
    progress_bar = f"[{'█' * filled}{'░' * (bar_total - filled)}]"
    footer = f"\n{progress_bar} {frame_idx + 1}/{num_frames}"
    lines.append(footer)
    
    return "\n".join(lines)


def render_minimal_frame(dataset, frame_idx, top_n=5, width=50, color=True):
    """Render a compact frame suitable for smaller displays."""
    data = dataset["data"]
    title = dataset.get("title", "")
    unit = dataset.get("unit", "")
    labels = dataset.get("labels", [])
    
    series_names = list(data.keys())
    num_frames = len(data[series_names[0]])
    frame_idx = max(0, min(frame_idx, num_frames - 1))
    
    current_values = {name: data[name][frame_idx] for name in series_names}
    ranked = sorted(current_values.items(), key=lambda x: x[1], reverse=True)
    
    if top_n:
        ranked = ranked[:top_n]
    
    max_val = max(abs(val) for _, val in ranked) if ranked else 1
    if max_val == 0:
        max_val = 1
    
    lines = []
    
    label_text = labels[frame_idx] if frame_idx < len(labels) else ""
    header = f"{BOLD}{title}{RESET} — {label_text}" if color else f"{title} — {label_text}"
    lines.append(header)
    
    for rank, (name, val) in enumerate(ranked, 1):
        bar_len = int((abs(val) / max_val) * width)
        bar_len = max(0, min(bar_len, width))
        # Color by name for consistency
        name_idx = list(dataset["data"].keys()).index(name) if name in dataset["data"] else rank - 1
        color_idx = name_idx % len(COLORS)
        c = COLORS[color_idx] if color else ""
        r = RESET if color else ""
        bar = c + "█" * bar_len + r
        val_str = format_value(val, unit)
        line = f" {rank:2d}. {name:<12s} {bar} {val_str}"
        lines.append(line)
    
    return "\n".join(lines)


# ─── Comparison View ──────────────────────────────────────────────────

def render_comparison(dataset, period_a, period_b, top_n=None, color=True):
    """Render a side-by-side comparison of two time periods.
    
    Args:
        dataset: The dataset to compare.
        period_a: Index of the first period (or -1 for last).
        period_b: Index of the second period (or -1 for last).
        top_n: Number of top entries to show.
        color: Whether to use ANSI colors.
    
    Returns:
        String with the comparison output.
    """
    data = dataset["data"]
    title = dataset.get("title", "Bar Chart Race")
    unit = dataset.get("unit", "")
    labels = dataset.get("labels", [])
    series_names = list(data.keys())
    num_periods = len(data[series_names[0]])

    # Normalize negative indices
    if period_a < 0:
        period_a = num_periods + period_a
    if period_b < 0:
        period_b = num_periods + period_b

    period_a = max(0, min(period_a, num_periods - 1))
    period_b = max(0, min(period_b, num_periods - 1))

    label_a = labels[period_a] if period_a < len(labels) else str(period_a + 1)
    label_b = labels[period_b] if period_b < len(labels) else str(period_b + 1)

    vals_a = {name: data[name][period_a] for name in series_names}
    vals_b = {name: data[name][period_b] for name in series_names}

    # Sort by period B values descending
    ranked = sorted(vals_b.items(), key=lambda x: x[1], reverse=True)
    if top_n:
        ranked = ranked[:top_n]

    max_val = max(max(abs(vals_a[n]), abs(vals_b[n])) for n, _ in ranked) if ranked else 1
    if max_val == 0:
        max_val = 1

    bar_width = 20

    lines = []
    header = f"{BOLD}=== {title} ==={RESET}" if color else f"=== {title} ==="
    lines.append(header)
    lines.append(f"  Comparing: {BOLD}{label_a}{RESET} vs {BOLD}{label_b}{RESET}" if color else f"  Comparing: {label_a} vs {label_b}")
    lines.append("")

    for rank, (name, val_b) in enumerate(ranked, 1):
        val_a = vals_a[name]
        change = val_b - val_a

        # Color by name
        name_idx = list(data.keys()).index(name) if name in data else rank - 1
        color_idx = name_idx % len(COLORS)
        c = COLORS[color_idx] if color else ""
        r = RESET if color else ""

        bar_len_a = int((abs(val_a) / max_val) * bar_width)
        bar_len_b = int((abs(val_b) / max_val) * bar_width)

        # Change indicator
        if change > 0:
            change_str = f"↑+{format_value(change, unit)}"
        elif change < 0:
            change_str = f"↓{format_value(change, unit)}"
        else:
            change_str = f"  {format_value(0, unit)}"

        # Rank with medal
        if rank == 1:
            rank_str = "🥇" if color else "#1"
        elif rank == 2:
            rank_str = "🥈" if color else "#2"
        elif rank == 3:
            rank_str = "🥉" if color else "#3"
        else:
            rank_str = f"#{rank}"

        line = f" {rank_str} {c}{BOLD}{name:<15s}{r} "
        line += f"{c}{'█' * bar_len_a}{r} → {c}{'█' * bar_len_b}{r}  "
        line += change_str
        lines.append(line)

    # Summary
    lines.append("")
    lines.append(f"  {'Series':<15s} {'From':>10s} {'To':>10s} {'Change':>10s} {'%':>8s}")
    lines.append(f"  {'─' * 15} {'─' * 10} {'─' * 10} {'─' * 10} {'─' * 8}")

    for name, _ in ranked:
        val_a = vals_a[name]
        val_b = vals_b[name]
        change = val_b - val_a
        if abs(val_a) > 1e-10:
            pct = ((val_b - val_a) / abs(val_a)) * 100
            pct_str = f"{pct:+.1f}%"
        else:
            pct_str = "N/A"
        change_str = format_value(change, unit)
        from_str = format_value(val_a, unit)
        to_str = format_value(val_b, unit)
        lines.append(f"  {name:<15s} {from_str:>10s} {to_str:>10s} {change_str:>10s} {pct_str:>8s}")

    return "\n".join(lines)


# ─── Ticker View ──────────────────────────────────────────────────────

def render_ticker(dataset, frame_idx, width=None):
    """Render a compact one-line ticker summary for the current period.
    
    Shows the top entries as: Rank Name Value │ ...
    Useful for embedding in status bars or piped output.
    """
    data = dataset["data"]
    title = dataset.get("title", "")
    unit = dataset.get("unit", "")
    labels = dataset.get("labels", [])

    series_names = list(data.keys())
    num_frames = len(data[series_names[0]])
    frame_idx = max(0, min(frame_idx, num_frames - 1))

    current_values = {name: data[name][frame_idx] for name in series_names}
    ranked = sorted(current_values.items(), key=lambda x: x[1], reverse=True)[:5]

    label_text = labels[frame_idx] if frame_idx < len(labels) else str(frame_idx + 1)

    if width is None:
        width = get_terminal_width()

    parts = [f"{BOLD}{label_text}{RESET}"]
    for rank, (name, val) in enumerate(ranked, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
        parts.append(f"{medal}{name} {format_value(val, unit)}")

    line = " │ ".join(parts)

    # Truncate if too wide
    # Strip ANSI for width calculation
    visible_len = len(re.sub(r'\033\[[0-9;]*m', '', line))
    if visible_len > width:
        line = line[:width]  # rough truncation

    return line


# ─── HTML Export ──────────────────────────────────────────────────────

def export_html(dataset, output_file, top_n=None, speed=1.0):
    """Export the bar chart race as an animated HTML file using CSS animations.
    
    Creates a self-contained HTML file with CSS-driven bar animations that can
    be opened in any browser. No JavaScript dependencies required.
    """
    dataset = validate_data(dataset)
    data = dataset["data"]
    title = dataset.get("title", "Bar Chart Race")
    unit = dataset.get("unit", "")
    labels = dataset.get("labels", [])
    series_names = list(data.keys())
    num_periods = len(data[series_names[0]])

    if top_n is None:
        top_n = len(series_names)

    # Build ranked lists per period
    period_data = []
    for i in range(num_periods):
        vals = {name: data[name][i] for name in series_names}
        ranked = sorted(vals.items(), key=lambda x: x[1], reverse=True)[:top_n]
        period_data.append(ranked)

    # Compute max value across entire dataset for consistent bar scaling
    max_val = max(abs(data[n][i]) for n in series_names for i in range(num_periods))
    if max_val == 0:
        max_val = 1

    interval_ms = int(1000 / speed) if speed > 0 else 2000

    # Generate HTML
    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>""" + html.escape(title) + """ — Bar Chart Race</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #1a1a2e; color: #eee; padding: 20px; max-width: 900px; margin: 0 auto;
  }
  h1 { text-align: center; margin-bottom: 5px; font-size: 1.5em; }
  .period-label { text-align: center; font-size: 1.2em; color: #aaa; margin-bottom: 15px; }
  .bar-row {
    display: flex; align-items: center; margin: 4px 0; height: 28px;
  }
  .bar-rank { width: 30px; text-align: right; margin-right: 8px; font-weight: bold; }
  .bar-name { width: 140px; font-weight: bold; text-align: right; margin-right: 8px; }
  .bar-track { flex: 1; position: relative; height: 24px; background: #2a2a4a; border-radius: 3px; }
  .bar-fill {
    height: 100%; border-radius: 3px; transition: width """ + str(interval_ms) + """ms ease-in-out;
    display: flex; align-items: center; justify-content: flex-end; padding-right: 5px;
    font-size: 0.8em; color: #fff; min-width: 30px;
  }
  .bar-value { margin-left: 8px; width: 70px; font-family: monospace; }
  .controls { text-align: center; margin: 20px 0; }
  .controls button {
    background: #4a4a7a; color: #fff; border: none; padding: 8px 16px; margin: 0 4px;
    border-radius: 4px; cursor: pointer; font-size: 1em;
  }
  .controls button:hover { background: #6a6a9a; }
  .progress-bar { width: 100%; height: 4px; background: #2a2a4a; border-radius: 2px; margin: 10px 0; }
  .progress-fill { height: 100%; background: #667eea; border-radius: 2px; transition: width 0.3s; }
</style>
</head>
<body>
<h1>""" + html.escape(title) + """</h1>
<div class="period-label" id="period-label"></div>
<div class="progress-bar"><div class="progress-fill" id="progress"></div></div>
<div id="bars"></div>
<div class="controls">
  <button onclick="prevFrame()">◀ Prev</button>
  <button id="playBtn" onclick="togglePlay()">⏸ Pause</button>
  <button onclick="nextFrame()">Next ▶</button>
  <button onclick="resetAnim()">↺ Reset</button>
</div>
<script>
const data = """)

    # Build JS data
    js_series = {}
    for name in series_names:
        js_series[name] = data[name]
    js_data = {
        "series": js_series,
        "labels": labels,
        "colors": {name: HTML_COLORS[i % len(HTML_COLORS)] for i, name in enumerate(series_names)},
        "unit": unit,
        "maxVal": max_val,
        "topN": top_n,
    }
    html_parts.append(json.dumps(js_data, indent=2))
    html_parts.append(""";
const interval = """ + str(interval_ms) + """;
let currentFrame = 0;
let playing = true;
let timerId = null;

function renderFrame(idx) {
  const labels = data.labels;
  const series = data.series;
  const names = Object.keys(series);
  const numFrames = series[names[0]].length;
  idx = Math.max(0, Math.min(idx, numFrames - 1));
  currentFrame = idx;

  document.getElementById('period-label').textContent = labels[idx] || '';
  document.getElementById('progress').style.width = ((idx / (numFrames - 1)) * 100) + '%';

  let vals = names.map(n => ({name: n, val: series[n][idx]}));
  vals.sort((a, b) => b.val - a.val);
  vals = vals.slice(0, data.topN);

  const barsDiv = document.getElementById('bars');
  barsDiv.innerHTML = '';
  vals.forEach((item, rank) => {
    const row = document.createElement('div');
    row.className = 'bar-row';
    const pct = Math.max(1, (Math.abs(item.val) / data.maxVal) * 100);
    const color = data.colors[item.name] || '#667eea';
    const medals = ['🥇', '🥈', '🥉'];
    const rankStr = rank < 3 ? medals[rank] : '#' + (rank + 1);
    row.innerHTML = `
      <div class="bar-rank">${rankStr}</div>
      <div class="bar-name" style="color:${color}">${item.name}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${color}">${item.val >= 1000 ? item.val.toLocaleString() : item.val.toFixed(1)}${data.unit}</div></div>
    `;
    barsDiv.appendChild(row);
  });
}

function nextFrame() {
  const names = Object.keys(data.series);
  const numFrames = data.series[names[0]].length;
  currentFrame = (currentFrame + 1) % numFrames;
  renderFrame(currentFrame);
}

function prevFrame() {
  const names = Object.keys(data.series);
  const numFrames = data.series[names[0]].length;
  currentFrame = (currentFrame - 1 + numFrames) % numFrames;
  renderFrame(currentFrame);
}

function togglePlay() {
  playing = !playing;
  document.getElementById('playBtn').textContent = playing ? '⏸ Pause' : '▶ Play';
  if (playing) startTimer();
  else stopTimer();
}

function resetAnim() {
  currentFrame = 0;
  renderFrame(0);
}

function startTimer() {
  stopTimer();
  timerId = setInterval(nextFrame, interval);
}

function stopTimer() {
  if (timerId) { clearInterval(timerId); timerId = null; }
}

renderFrame(0);
startTimer();
</script>
</body>
</html>""")

    html_content = "\n".join(html_parts)
    with open(output_file, "w") as f:
        f.write(html_content)

    print(f"Exported HTML bar chart race to {output_file}")
    return output_file


# ─── Animation ─────────────────────────────────────────────────────────

def clear_screen():
    """Clear terminal screen."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def animate(dataset, speed=2.0, top_n=None, loop=True, color=True, minimal=False):
    """Run the bar chart race animation."""
    dataset = validate_data(dataset)
    dataset = interpolate_data(dataset, steps_per_period=5)
    
    series_names = list(dataset["data"].keys())
    num_frames = len(dataset["data"][series_names[0]])
    
    if top_n is None:
        top_n = len(series_names)
    
    frame_delay = 1.0 / speed
    
    try:
        while True:
            for i in range(num_frames):
                if minimal:
                    frame = render_minimal_frame(dataset, i, top_n=top_n, color=color)
                else:
                    frame = render_frame(dataset, i, top_n=top_n, color=color)
                
                clear_screen()
                print(frame)
                time.sleep(frame_delay)
            
            if not loop:
                break
            
            # Pause at end before looping
            time.sleep(2.0)
    
    except KeyboardInterrupt:
        print(f"\n\n{DIM}Animation stopped.{RESET}")
        return


# ─── Export ────────────────────────────────────────────────────────────

def export_frames(dataset, output_dir, top_n=None, num_steps=100):
    """Export animation frames as individual text files."""
    dataset = validate_data(dataset)
    dataset = interpolate_data(dataset, steps_per_period=5)
    
    series_names = list(dataset["data"].keys())
    num_frames = len(dataset["data"][series_names[0]])
    
    if top_n is None:
        top_n = len(series_names)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Sample frames for export
    if num_frames <= num_steps:
        frame_indices = list(range(num_frames))
    else:
        frame_indices = [int(i * (num_frames - 1) / (num_steps - 1)) for i in range(num_steps)]
    
    for idx, frame_idx in enumerate(frame_indices):
        frame = render_frame(dataset, frame_idx, top_n=top_n, color=False)
        filepath = os.path.join(output_dir, f"frame_{idx:04d}.txt")
        with open(filepath, "w") as f:
            f.write(frame)
    
    print(f"Exported {len(frame_indices)} frames to {output_dir}/")
    return len(frame_indices)


def export_ascii_movie(dataset, output_file, top_n=None, fps=10):
    """Export as a single text file with all frames separated by form feeds."""
    dataset = validate_data(dataset)
    dataset = interpolate_data(dataset, steps_per_period=5)
    
    series_names = list(dataset["data"].keys())
    num_frames = len(dataset["data"][series_names[0]])
    
    if top_n is None:
        top_n = len(series_names)
    
    frames = []
    for i in range(num_frames):
        frame = render_frame(dataset, i, top_n=top_n, color=False)
        frames.append(frame)
    
    with open(output_file, "w") as f:
        f.write("\f".join(frames))
    
    print(f"Exported {num_frames} frames to {output_file}")
    return num_frames


def print_final_ranking(dataset, top_n=None):
    """Print the final ranking without animation."""
    dataset = validate_data(dataset)
    
    series_names = list(dataset["data"].keys())
    data = dataset["data"]
    title = dataset.get("title", "Bar Chart Race")
    unit = dataset.get("unit", "")
    
    if top_n is None:
        top_n = len(series_names)
    
    # Get final values
    final_values = {name: data[name][-1] for name in series_names}
    ranked = sorted(final_values.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    print(f"\n{BOLD}=== Final Ranking: {title} ==={RESET}\n")
    
    medals = ["🥇", "🥈", "🥉"]
    
    max_val = max(abs(val) for _, val in ranked) if ranked else 1
    if max_val == 0:
        max_val = 1
    
    for rank, (name, val) in enumerate(ranked, 1):
        medal = medals[rank - 1] if rank <= 3 else "  "
        bar_len = int((abs(val) / max_val) * 30)
        color_idx = (list(data.keys()).index(name) if name in data else rank - 1) % len(COLORS)
        c = COLORS[color_idx]
        bar = c + "█" * bar_len + RESET
        val_str = format_value(val, unit)
        print(f" {medal} {rank:2d}. {BOLD}{name}{RESET}  {bar} {val_str}")
    
    print()
    
    # Also show biggest movers
    if len(data[series_names[0]]) > 1:
        changes = {}
        for name in series_names:
            start = data[name][0]
            end = data[name][-1]
            changes[name] = end - start
        
        biggest_gainer = max(changes.items(), key=lambda x: x[1])
        biggest_loser = min(changes.items(), key=lambda x: x[1])
        
        print(f" {BOLD}Biggest gainer:{RESET} {biggest_gainer[0]} ({format_value(biggest_gainer[1], unit)} change)")
        print(f" {BOLD}Biggest loser:{RESET}  {biggest_loser[0]} ({format_value(biggest_loser[1], unit)} change)")
        
        # Rank changes
        start_ranking = sorted(
            [(name, data[name][0]) for name in series_names],
            key=lambda x: x[1], reverse=True
        )
        end_ranking = sorted(
            [(name, data[name][-1]) for name in series_names],
            key=lambda x: x[1], reverse=True
        )
        
        start_ranks = {name: i + 1 for i, (name, _) in enumerate(start_ranking)}
        end_ranks = {name: i + 1 for i, (name, _) in enumerate(end_ranking)}
        
        movers = []
        for name in series_names:
            rank_change = start_ranks[name] - end_ranks[name]
            if rank_change != 0:
                movers.append((name, rank_change))
        
        if movers:
            movers.sort(key=lambda x: abs(x[1]), reverse=True)
            print(f"\n {BOLD}Rank changes:{RESET}")
            for name, change in movers[:5]:
                arrow = "↑" if change > 0 else "↓"
                print(f"   {name}: {arrow}{abs(change)} (#{start_ranks[name]} → #{end_ranks[name]})")


def generate_random_data(num_series=8, num_periods=15, seed=None):
    """Generate random race data for testing/demo."""
    if seed is not None:
        random.seed(seed)
    
    names = [
        "Alpha", "Beta", "Gamma", "Delta", "Epsilon",
        "Zeta", "Eta", "Theta", "Iota", "Kappa",
        "Lambda", "Mu", "Nu", "Xi", "Omicron"
    ]
    
    data = {}
    for i in range(min(num_series, len(names))):
        name = names[i]
        values = [random.uniform(10, 100)]
        for j in range(1, num_periods):
            # Random walk with drift
            drift = random.uniform(-5, 8)  # slight positive bias
            noise = random.gauss(0, 10)
            new_val = max(1, values[-1] + drift + noise)
            values.append(round(new_val, 1))
        data[name] = values
    
    labels = [f"Period {i+1}" for i in range(num_periods)]
    
    return {
        "title": "Random Race",
        "unit": "pts",
        "data": data,
        "labels": labels,
    }


# ─── Stats ────────────────────────────────────────────────────────────

def compute_stats(dataset):
    """Compute and display statistics about the dataset."""
    dataset = validate_data(dataset)
    
    data = dataset["data"]
    title = dataset.get("title", "")
    unit = dataset.get("unit", "")
    series_names = list(data.keys())
    num_periods = len(data[series_names[0]])
    
    print(f"\n{BOLD}=== Statistics: {title} ==={RESET}\n")
    print(f"  Series count:    {len(series_names)}")
    print(f"  Time periods:    {num_periods}")
    
    # Per-series stats with sparklines
    print(f"\n  {'Series':<15s} {'Min':>8s} {'Max':>8s} {'Mean':>8s} {'Growth':>8s} {'Trend':>12s}")
    print(f"  {'─'*15} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*12}")
    
    for name in series_names:
        vals = data[name]
        min_v = min(vals)
        max_v = max(vals)
        mean_v = sum(vals) / len(vals)
        growth = vals[-1] - vals[0]
        trend = sparkline(vals, width=min(12, num_periods))
        print(f"  {name:<15s} {min_v:>8.1f} {max_v:>8.1f} {mean_v:>8.1f} {growth:>+8.1f} {trend:>12s}")
    
    # Growth ranking
    print(f"\n  {BOLD}Growth Ranking:{RESET}")
    growths = [(name, data[name][-1] - data[name][0]) for name in series_names]
    growths.sort(key=lambda x: x[1], reverse=True)
    for i, (name, growth) in enumerate(growths[:5]):
        pct_growth = ((data[name][-1] - data[name][0]) / abs(data[name][0]) * 100) if abs(data[name][0]) > 1e-10 else float('inf')
        pct_str = f" ({pct_growth:+.1f}%)" if pct_growth != float('inf') else ""
        medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f"  "
        print(f"    {medal} {name}: {format_value(growth, unit)}{pct_str}")
    
    # Correlation between series (simplified)
    print(f"\n  Most competitive pairs (high correlation):")
    
    pairs = []
    for i, n1 in enumerate(series_names):
        for n2 in series_names[i+1:]:
            v1 = data[n1]
            v2 = data[n2]
            # Simple correlation
            mean1 = sum(v1) / len(v1)
            mean2 = sum(v2) / len(v2)
            cov = sum((a - mean1) * (b - mean2) for a, b in zip(v1, v2)) / len(v1)
            std1 = (sum((a - mean1)**2 for a in v1) / len(v1)) ** 0.5
            std2 = (sum((b - mean2)**2 for b in v2) / len(v2)) ** 0.5
            if std1 > 0 and std2 > 0:
                corr = cov / (std1 * std2)
                pairs.append((n1, n2, corr))
    
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    for n1, n2, corr in pairs[:5]:
        print(f"    {n1} ↔ {n2}: {corr:+.3f}")


# ─── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Barchart Race — Animated ASCII Bar Chart Race Visualizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              Run default demo (tech-revenue)
  %(prog)s --sample olympic-medals      Run Olympic medals dataset
  %(prog)s --data my_data.csv           Load custom CSV data
  %(prog)s --data my_data.json          Load custom JSON data
  %(prog)s --random                     Generate random race
  %(prog)s --top 5                       Show only top 5 bars
  %(prog)s --speed 4                     Faster animation
  %(prog)s --no-loop                    Don't loop animation
  %(prog)s --no-color                   Disable colors
  %(prog)s --percent                    Show values as percentage of total
  %(prog)s --growth                     Show growth from first period
  %(prog)s --compare 0 -1               Compare first vs last period
  %(prog)s --ticker                     Show compact one-line summary
  %(prog)s --html output.html           Export as animated HTML
  %(prog)s --export frames/              Export frames to directory
  %(prog)s --stats                       Show dataset statistics
  %(prog)s --solve                       Show final ranking
  %(prog)s --list                        List available datasets
        """
    )
    
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--data", "-d", help="Path to CSV or JSON data file")
    parser.add_argument("--sample", "-s", choices=list(SAMPLE_DATASETS.keys()),
                        help="Choose a built-in sample dataset")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List available sample datasets")
    parser.add_argument("--random", "-r", action="store_true",
                        help="Generate random race data")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for --random")
    parser.add_argument("--speed", "-sp", type=float, default=2.0,
                        help="Animation speed in frames/sec (default: 2.0)")
    parser.add_argument("--top", "-n", type=int, default=None,
                        help="Show only top N bars")
    parser.add_argument("--no-loop", action="store_true",
                        help="Don't loop the animation")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output")
    parser.add_argument("--minimal", "-m", action="store_true",
                        help="Use compact display mode")
    parser.add_argument("--percent", "-p", action="store_true",
                        help="Show values as percentage of total (market share mode)")
    parser.add_argument("--growth", "-g", action="store_true",
                        help="Show growth from first period instead of absolute values")
    parser.add_argument("--compare", "-c", nargs=2, type=int, metavar=("PERIOD_A", "PERIOD_B"),
                        help="Compare two periods side by side (e.g. --compare 0 -1)")
    parser.add_argument("--ticker", "-t", action="store_true",
                        help="Show compact one-line ticker for each period")
    parser.add_argument("--html", metavar="FILE",
                        help="Export as animated HTML file")
    parser.add_argument("--export", "-e", metavar="DIR",
                        help="Export frames to directory (no animation)")
    parser.add_argument("--export-movie", metavar="FILE",
                        help="Export as single text file with all frames")
    parser.add_argument("--stats", action="store_true",
                        help="Show statistics about the dataset")
    parser.add_argument("--solve", action="store_true",
                        help="Show final ranking without animation")
    
    args = parser.parse_args()
    
    color = not args.no_color
    
    # List datasets
    if args.list:
        print(f"\n{BOLD}Available sample datasets:{RESET}\n")
        for key, ds in SAMPLE_DATASETS.items():
            num_series = len(ds["data"])
            num_periods = len(ds["data"][list(ds["data"].keys())[0]])
            print(f"  {key:<25s} — {ds['title']}")
            print(f"  {'':25s}   {ds['description']}")
            print(f"  {'':25s}   {num_series} series × {num_periods} periods")
            print()
        return
    
    # Load dataset
    dataset = None
    
    if args.data:
        filepath = args.data
        if filepath.endswith(".json"):
            dataset = load_json(filepath)
        elif filepath.endswith(".csv"):
            dataset = load_csv(filepath)
        else:
            # Try JSON first, then CSV
            try:
                dataset = load_json(filepath)
            except (json.JSONDecodeError, ValueError):
                dataset = load_csv(filepath)
    elif args.random:
        dataset = generate_random_data(seed=args.seed)
    elif args.sample:
        dataset = deepcopy(SAMPLE_DATASETS[args.sample])
    else:
        # Default: tech-revenue
        dataset = deepcopy(SAMPLE_DATASETS["tech-revenue"])
    
    dataset = validate_data(dataset)
    
    # Apply transforms
    if args.percent:
        dataset = transform_percentage(dataset)
    elif args.growth:
        dataset = transform_growth(dataset)
    
    # Handle stats
    if args.stats:
        compute_stats(dataset)
        return
    
    # Handle compare
    if args.compare:
        print(render_comparison(dataset, args.compare[0], args.compare[1], top_n=args.top, color=color))
        return
    
    # Handle ticker
    if args.ticker:
        dataset_interp = interpolate_data(dataset, steps_per_period=3)
        series_names = list(dataset_interp["data"].keys())
        num_frames = len(dataset_interp["data"][series_names[0]])
        frame_delay = 1.0 / args.speed
        try:
            for i in range(num_frames):
                line = render_ticker(dataset_interp, i)
                # Move cursor to beginning of line and clear it
                sys.stdout.write(f"\r\033[K{line}")
                sys.stdout.flush()
                time.sleep(frame_delay)
            sys.stdout.write("\n")
        except KeyboardInterrupt:
            sys.stdout.write("\n")
        return
    
    # Handle solve (final ranking)
    if args.solve:
        print_final_ranking(dataset, top_n=args.top)
        return
    
    # Handle HTML export
    if args.html:
        export_html(dataset, args.html, top_n=args.top, speed=args.speed)
        return
    
    # Handle export
    if args.export:
        export_frames(dataset, args.export, top_n=args.top)
        return
    
    if args.export_movie:
        export_ascii_movie(dataset, args.export_movie, top_n=args.top)
        return
    
    # Animate
    animate(
        dataset,
        speed=args.speed,
        top_n=args.top,
        loop=not args.no_loop,
        color=color,
        minimal=args.minimal,
    )


if __name__ == "__main__":
    main()