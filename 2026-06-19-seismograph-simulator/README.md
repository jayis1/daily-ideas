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
- **Richter Scale Bar** — Visual magnitude indicator with classification (Minor/Moderate/Strong/Major)
- **Station Map** — Top-down view showing epicenter and station positions (shown at start)
- **Historical Earthquakes** — Simulate famous events like the 2011 Tohoku M9.0 or 2004 Indian Ocean M9.1
- **Configurable** — Set magnitude, depth, speed, duration, and number of stations
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

### Full options
```
python3 seismograph.py -m 7.5 -d 30 --lat 35.6 --lon 139.7 --speed 2 --duration 90
```

## Command-Line Options

| Flag | Default | Description |
|------|---------|-------------|
| `-m`, `--magnitude` | Random | Earthquake magnitude (1.0–10.0) |
| `-d`, `--depth` | 10 | Depth in km |
| `--lat` | 35.6 | Epicenter latitude |
| `--lon` | 139.7 | Epicenter longitude |
| `--duration` | 60 | Simulation duration in seconds |
| `--speed` | 1.0 | Playback speed multiplier |
| `--historical` | — | Simulate a random famous earthquake |
| `--interactive` | — | Choose from a list of historical events |
| `--list` | — | List historical earthquakes and exit |
| `--no-map` | — | Skip the station map display |
| `--stations` | 10 | Number of monitoring stations (3–10) |

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

## Example Output

```
  ════════════════════════════════════════════════════════════════════
    🌍 SEISMOGRAPH SIMULATOR  │  Live Seismic Monitoring
  ════════════════════════════════════════════════════════════════════
  Epicenter: (35.6°, 139.7°)  Magnitude: M7.0  Depth: 10 km  Time: 29.9s
  Richter Scale  █████████████████████░░░░░░░░░ M7.0 (Major)

  ────────────────────────────────────────────────────────────────────
    Real-Time Seismograms
  ────────────────────────────────────────────────────────────────────
  Alpha Ridge   45km │     ████████████░░████████                     │ Surface
  Delta Creek   80km │        █░░░░░███░░█░█░░█░███░█████████░░░░█    │ Surface
  Bravo Peak  120km │                                       █         │ P-wave
  Juliet Dock 150km │                 █░░░█░█████████░██░██              │ S-wave
  ────────────────────────────────────────────────────────────────────

  Wave Phase Guide
    P-wave     High freq, low amp           ● ACTIVE
    S-wave     Medium freq, med amp         ● ACTIVE
    Surface    Low freq, high amp           ● ACTIVE
```

## License

MIT