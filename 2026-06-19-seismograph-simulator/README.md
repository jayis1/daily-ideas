# 🌍 Terminal Seismograph Simulator

A real-time terminal-based seismograph simulator that visualizes earthquake seismic waves propagating through a network of monitoring stations. Watch P-waves, S-waves, and surface waves arrive at different stations based on their distance from the epicenter — just like real seismologists do.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![No Dependencies](https://img.shields.io/badge/Dependencies-None-brightgreen.svg)

## Features

- **Realistic Wave Propagation** — P-waves (fast, low amplitude), S-waves (medium), and surface waves (slow, high amplitude) arrive at different times based on distance
- **10 Seismic Stations** — Each at different distances and azimuths from the epicenter
- **Live Waveform Display** — Animated seismogram traces for all stations with phase-colored fills
- **Travel Time Calculations** — Real-time arrival status with ETA countdowns for each wave type at each station
- **Richter Scale Bar** — Visual magnitude indicator with classification (Minor/Moderate/Strong/Major/Great)
- **Station Map** — Top-down view showing epicenter and station positions (shown at start)
- **Travel-Time Curve Plot** — ASCII chart showing P, S, and surface wave travel-time curves with station markers
- **Historical Earthquakes** — Simulate famous events like the 2011 Tohoku M9.0 or 2004 Indian Ocean M9.1
- **Configurable** — Set magnitude, depth, speed, duration, and number of stations
- **Input Validation** — Invalid inputs (speed ≤ 0, negative depth, etc.) are gracefully handled with sensible defaults
- **Zero Dependencies** — Pure Python 3, no external packages required

## How It Works

The simulator uses simplified but physically-grounded models:

- **P-waves** travel at ~6.5 km/s through the upper mantle (high frequency, lower amplitude)
- **S-waves** travel at ~3.7 km/s (medium frequency, medium amplitude)
- **Surface waves** travel at ~3.0 km/s (low frequency, highest amplitude, longest duration)
- Wave amplitude decays exponentially with time since arrival
- Amplitude scales with magnitude (logarithmic, per the Richter scale)
- Closer stations receive stronger signals (inverse distance scaling)
- Background microseismic noise is simulated with Gaussian random noise

## Installation

No installation needed beyond Python 3.8+:

```bash
# Just download and run
git clone <repo-url>
cd seismograph-simulator
python3 seismograph.py
```

## Usage

### Basic — Random earthquake
```bash
python3 seismograph.py
```

### Specify magnitude and depth
```bash
python3 seismograph.py -m 7.5 -d 30
```

### Simulate a historical earthquake
```bash
python3 seismograph.py --historical
```

### Choose from a list of famous earthquakes
```bash
python3 seismograph.py --interactive
```

### List available historical events
```bash
python3 seismograph.py --list
```

### Speed up the simulation
```bash
python3 seismograph.py -m 6.0 --speed 5     # 5x realtime
python3 seismograph.py -m 8.0 --speed 10    # 10x realtime
```

### Custom duration and fewer stations
```bash
python3 seismograph.py -m 5.5 --duration 120 --stations 5
```

### Show version
```bash
python3 seismograph.py --version
```

### Full options
```
python3 seismograph.py -m 7.5 -d 30 --lat 35.6 --lon 139.7 --speed 2 --duration 90
```

## Command-Line Options

| Flag | Default | Description |
|------|---------|-------------|
| `-m`, `--magnitude` | Random | Earthquake magnitude (1.0–10.0) |
| `-d`, `--depth` | 10 | Depth in km (must be ≥ 0) |
| `--lat` | 35.6 | Epicenter latitude |
| `--lon` | 139.7 | Epicenter longitude |
| `--duration` | 60 | Simulation duration in seconds (must be > 0) |
| `--speed` | 1.0 | Playback speed multiplier (must be > 0) |
| `--historical` | — | Simulate a random famous earthquake |
| `--interactive` | — | Choose from a list of historical events |
| `--list` | — | List historical earthquakes and exit |
| `--no-map` | — | Skip the station map display |
| `--stations` | 10 | Number of monitoring stations (3–10) |
| `--version` | — | Show version and exit |

## What You'll See

When you run the simulator, you'll see:

1. **Header** — Epicenter coordinates, magnitude, depth, and elapsed time
2. **Richter Scale Bar** — Color-coded magnitude indicator
3. **Seismogram Traces** — 10 station waveforms scrolling in real-time
   - Green fill = P-wave phase
   - Yellow fill = S-wave phase
   - Cyan fill = Surface wave phase
   - Dim traces = pre-event (noise only)
4. **Wave Phase Guide** — Which wave types are currently active
5. **Arrival Times** — Per-station P/S/Surface wave arrival status with ETAs
6. **Station Map** — Top-down view showing epicenter (★) and stations (▲)

Press **Ctrl+C** to stop the simulation at any time.

## Historical Earthquakes Included

| # | Mag | Event |
|---|-----|-------|
| 1 | 9.1 | 2004 Indian Ocean Tsunami |
| 2 | 9.0 | 2011 Tohoku (Fukushima) |
| 3 | 8.8 | 2010 Chile (Maule) |
| 4 | 7.9 | 2008 Sichuan, China |
| 5 | 7.0 | 2010 Haiti |
| 6 | 6.9 | 1989 Loma Prieta, CA |
| 7 | 6.7 | 1994 Northridge, CA |
| 8 | 6.4 | 2021 Crete |
| 9 | 5.5 | Hypothetical London |
| 10 | 4.5 | Small Bay Area |

## Richter Scale Classification

| Magnitude | Classification | Color |
|-----------|---------------|-------|
| < 3.0 | Minor | Green |
| 3.0–4.9 | Moderate | Yellow |
| 5.0–6.9 | Strong | Red |
| 7.0–7.9 | Major | Red (bold) |
| ≥ 8.0 | Great | Magenta (bold) |

## Testing

Run the test suite:

```bash
python3 -m pytest test_seismograph.py -v
```

The test suite includes 51 tests covering:
- Magnitude-to-amplitude conversion (including edge cases and minimum clamping)
- Wave arrival time calculations (zero distance, depth handling, ordering)
- Wave generation (before/after arrival, decay, noise)
- Compute waveform (integration test)
- Drawing functions (Richter scale, map, travel-time curve, phase diagram)
- Zero-distance station in travel-time curve (division-by-zero fix)
- Empty station lists
- CLI argument parsing (--version, --list, magnitude/depth/speed validation)
- Data structure integrity

## Changelog

### v1.1.0 — Bug Fix Release

**Critical Fixes:**
- **Fixed ZeroDivisionError in `draw_travel_time_curve`** when all stations have zero distance — now falls back to a default distance
- **Fixed crash with `--speed 0`** — previously caused `ZeroDivisionError` in `time.sleep(dt/speed)`; now validates and falls back to 1.0x with an error message
- **Fixed crash with `--speed < 0`** — previously caused `ValueError: sleep length must be non-negative`; now validates and falls back to 1.0x with an error message

**Improvements:**
- **Added `--version` flag** — shows version `1.1.0`
- **Added Richter scale "Great" classification** — M8.0+ now labeled "Great" (was incorrectly labeled "Major"); M7.0–7.9 remains "Major"
- **Added minimum amplitude clamping** — Very small magnitudes (M1–M2) now produce visible waveforms instead of being lost in noise
- **Added depth validation** — Negative depth values are clamped to 0
- **Added duration validation** — Non-positive durations fall back to 60s with a warning
- **Added docstring to `surface_wave_arrival_time`** — Clarifies that the `depth_km` parameter is accepted for API consistency but not used in the calculation
- **Added comprehensive test suite** — 51 unit tests covering all core functions, edge cases, and CLI argument parsing

## License

MIT