# 🪐 Solar System Orrery

A beautiful animated terminal-based orrery that displays all eight planets orbiting the Sun using real orbital mechanics. Watch Mercury race around while Neptune crawls — all in your terminal!

## Features

- **Real Orbital Mechanics**: Uses Kepler's equation solver to compute true anomaly from mean anomaly, giving accurate elliptical orbits with proper eccentricity
- **All 8 Planets**: Mercury through Neptune with real semi-major axes, orbital periods, and eccentricities
- **Power-Compressed View**: Smart distance scaling (power 0.55) so inner and outer planets are all visible simultaneously
- **Trails**: Toggle orbital trails to see where planets have been
- **Time Control**: Speed up or slow down time, jump to any date, or pause to study positions
- **Zoom**: Zoom in/out to focus on inner planets or see the full system
- **Planet Selection**: Browse planet info with arrow keys — see distance, period, eccentricity, and live position
- **Starfield Background**: Randomly generated stars for atmosphere
- **Perspective Effect**: Y-axis compression gives a slight 3D perspective feel

## How to Install

```bash
# No external dependencies needed — uses only Python standard library (curses)
# Just clone and run!
git clone <repo-url>
cd solar-system-orrery
```

Requires Python 3.6+ with curses support (included on most Linux/macOS systems).

## How to Run

```bash
python3 orrery.py
```

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause / Resume |
| `+` / `=` | Speed up time |
| `-` | Slow down time |
| `↑` / `↓` | Zoom in / out |
| `←` / `→` | Select previous / next planet |
| `O` | Toggle orbit paths |
| `L` | Toggle planet labels |
| `T` | Toggle trails |
| `D` | Jump to a specific date (YYYY-MM-DD) |
| `S` | Set simulation speed manually |
| `R` | Reset to default view and date |
| `Q` | Quit |

## Usage Examples

**Watch a year go by fast:**
```
Press '+' several times to speed up, then watch the inner planets zip around
```

**Jump to a specific date:**
```
Press 'D', type "2030-07-04", press Enter to see planetary positions on July 4th, 2030
```

**Focus on inner planets:**
```
Press '↑' to zoom in, then watch Mercury, Venus, Earth, and Mars in detail
```

**Study a single planet's orbit:**
```
Press '←'/'→' to select a planet, then read its orbital data in the info panel
```

## How It Works

The orrery uses **Kepler's equation** (`M = E - e·sin(E)`) solved via Newton's method to convert mean anomaly to eccentric anomaly, then derives the true anomaly for accurate elliptical motion. The Y-axis is compressed by 0.5× to give a subtle 3D perspective effect. Distances are scaled with a power law (0.55) so that both Mercury (0.387 AU) and Neptune (30 AU) fit on screen while remaining visually distinguishable.

Orbital parameters are real values from J2000 epoch data.