# 🪐 Solar System Orrery v2.1

An animated terminal-based orrery that displays all eight planets orbiting the Sun using real orbital mechanics. Watch Mercury race around while Neptune crawls — all in your terminal!

## Features

### Core Mechanics
- **Real Orbital Mechanics** — Uses Kepler's equation solver (Newton's method) to compute true anomaly from mean anomaly, giving accurate elliptical orbits with proper eccentricity
- **All 8 Planets** — Mercury through Neptune with real semi-major axes, orbital periods, and eccentricities
- **Power-Compressed View** — Smart distance scaling (power 0.55) so inner and outer planets are all visible simultaneously
- **Starfield Background** — Randomly generated stars for atmosphere (regenerated only on terminal resize)

### Visualization
- **Earth's Moon** — A small dot orbiting Earth with the correct ~27.3-day period (toggle with `M`)
- **Asteroid Belt** — 60 animated asteroids between Mars and Jupiter following Kepler's third law (toggle with `A`)
- **Orbital Trails** — Toggle trail accumulation on/off with `T` to visualize orbit paths
- **Orbit Paths** — Dotted elliptical paths for all planets (toggle with `O`)
- **Planet Labels** — 3-letter labels next to each planet (toggle with `L`)
- **Perspective Effect** — Y-axis compression gives a subtle 3D perspective feel

### Information & Alerts
- **Info Panel** — Shows selected planet's semi-major axis, current distance from Sun, orbital velocity (km/s), period, eccentricity, and live position
- **Conjunction Detection** — Automatically detects and alerts when two planets are within 5° of each other, displayed with prominent indicators
- **Orbital Velocity** — Real-time speed in km/s computed via the vis-viva equation

### Controls
- **Time Control** — Speed up/slow down time, jump to any date, or pause
- **Zoom** — Zoom in/out to focus on inner planets or see the full system
- **Planet Selection** — Browse planet info with arrow keys
- **Jump to Today** — Press `H` to instantly jump to today's date
- **CLI Flags** — `--help`, `--version`, `--date`, `--speed`, `--no-trails`, `--no-moon`, `--asteroids`

### Robustness
- **Graceful Error Handling** — Handles small terminals, invalid inputs, and edge cases
- **Unicode Fallback** — Gracefully degrades to ASCII symbols on terminals without UTF-8 support; handles wide character overflow at terminal edges
- **Frame Time Cap** — Prevents huge time jumps if the window is hidden/minimized
- **Bounds Checking** — All drawing operations are safely clamped to terminal dimensions
- **Speed Validation** — Simulation speed is clamped to valid range (0.01–3650 days/sec) on assignment
- **Case-Insensitive Keys** — All letter keys work with both uppercase and lowercase

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
# Start with default settings
python3 orrery.py

# Start at a specific date
python3 orrery.py --date 2030-07-04

# Start at 10x speed with asteroid belt visible
python3 orrery.py --speed 10 --asteroids

# Start with no trails and no Moon
python3 orrery.py --no-trails --no-moon

# Show version
python3 orrery.py --version

# Show help
python3 orrery.py --help
```

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause / Resume |
| `+` / `=` | Speed up time |
| `-` / `_` | Slow down time |
| `↑` / `↓` | Zoom in / out |
| `←` / `→` | Select previous / next planet |
| `O` | Toggle orbit paths |
| `L` | Toggle planet labels |
| `T` | Toggle orbital trails on/off |
| `A` | Toggle asteroid belt |
| `M` | Toggle Earth's Moon |
| `D` | Jump to a specific date (YYYY-MM-DD) |
| `S` | Set simulation speed manually (must be > 0) |
| `H` | Jump to today's date |
| `R` | Reset to default view, date, and trails |
| `Q` | Quit |

All letter keys work with both uppercase and lowercase.

## Usage Examples

**Watch a year go by fast:**
```
Press '+' several times to speed up, then watch the inner planets zip around
```

**Jump to a specific date:**
```
Press 'D', type "2030-07-04", press Enter to see planetary positions on July 4th, 2030
```

**Jump to today:**
```
Press 'H' to instantly set the simulation date to today
```

**Focus on inner planets:**
```
Press '↑' to zoom in, then watch Mercury, Venus, Earth, and Mars in detail
```

**Enable the asteroid belt:**
```
Press 'A' to toggle the asteroid belt on/off. 60 asteroids orbit between
Mars and Jupiter following Kepler's third law — inner ones move faster.
```

**Watch for conjunctions:**
```
Speed up time and watch for ⚡ conjunction alerts that appear when two
planets are within 5° of each other as seen from the Sun.
```

**Study a single planet's orbit:**
```
Press '←'/'→' to select a planet, then read its orbital data in the info panel
— including live distance from Sun and orbital velocity in km/s.
```

**Toggle trails to see orbit paths:**
```
Press 'T' to enable trails and watch them accumulate as planets move.
Press 'T' again to clear trails and stop accumulation.
```

**Start from command line:**
```
python3 orrery.py --date 2024-04-08 --speed 5 --asteroids
```

## How It Works

### Orbital Mechanics

The orrery uses **Kepler's equation** (`M = E - e·sin(E)`) solved via Newton's method to convert mean anomaly to eccentric anomaly, then derives the true anomaly for accurate elliptical motion. The Y-axis is compressed by 0.5× to give a subtle 3D perspective effect. Distances are scaled with a power law (0.55) so that both Mercury (0.387 AU) and Neptune (30 AU) fit on screen while remaining visually distinguishable.

### Orbital Velocity

The info panel displays real-time orbital velocity computed using the **vis-viva equation**: `v = √(GM·(2/r - 1/a))`, where GM☉ = 1.327×10¹¹ km³/s². This gives physically accurate velocities — Earth ~29.8 km/s, Mercury ~47.9 km/s, Neptune ~5.4 km/s.

### Conjunction Detection

Every frame, the angular positions of all planet pairs are compared. When two planets are within 5° of each other (as seen from the Sun), a conjunction alert is displayed with the exact angular separation. Planets at the origin (degenerate case) are skipped to avoid false positives.

### Asteroid Belt

60 asteroids are generated deterministically between 2.1–3.3 AU (the main asteroid belt). Each asteroid's orbital period follows Kepler's third law (`T = a^1.5`), so inner asteroids orbit faster — just like real ones.

### Earth's Moon

A small dot orbits Earth with the Moon's real 27.3-day period. The display radius is exaggerated for visibility (real scale would be invisible). The Moon is offset from Earth by at least 2 screen units to prevent overlap on small terminals.

### Speed Units

The simulation speed is displayed in "days/sec" — at speed 1.0, approximately 1 day of simulation time passes per real second at 30fps. The actual formula is `elapsed_days = speed × dt_frame × 30`.

## Architecture

- `solve_kepler(M, e)` — Solves Kepler's equation with Newton's method. Validates eccentricity (0 ≤ e < 1).
- `planet_position(a, period, e, years)` — Computes (x, y) in AU from orbital elements. Validates period > 0 and a > 0.
- `orbital_velocity_km_s(a, period, r)` — Computes orbital velocity at distance r via vis-viva equation.
- `detect_conjunctions(positions, threshold)` — Finds planet pairs within a given angular threshold. Skips degenerate origin positions.
- `au_to_screen(x, y, cx, cy, scale, max_r)` — Maps AU coordinates to screen coordinates with power-law compression.
- `draw_orbit()` — Draws an orbital ellipse as a dotted path.
- `generate_asteroids(seed)` — Creates deterministic asteroid belt with Kepler-correct speeds.
- `draw_asteroid_belt()` — Renders animated asteroids on screen.
- `generate_stars()` — Creates a deterministic starfield (seeded). Returns empty list for degenerate terminal sizes.
- `OrreryState` — Tracks date, speed (validated via property), selection, trail data, toggles, and conjunction alerts.
- `main()` — Curses event loop handling input, simulation, and rendering.
- `parse_args()` — CLI argument parser with --help, --version, --date, --speed, --no-trails, --no-moon, --asteroids.

## Testing

```bash
python3 test_orrery.py
```

Runs 123 tests covering:
- Kepler solver (convergence, edge cases, invalid inputs, large mean anomaly)
- Planet position calculations (circular orbits, all 8 planets, invalid parameters)
- Screen coordinate mapping (origin, clamping, perspective compression)
- Star generation (bounds checking, degenerate sizes, determinism)
- State management (defaults, toggle behavior, speed property validation)
- Orbital mechanics consistency (perihelion/aphelion ranges, periodicity)
- Orbital velocity (vis-viva equation, edge cases, relative ordering)
- Conjunction detection (aligned, opposite, close, far, empty, format, degenerate origin)
- Asteroid belt generation (count, structure, Kepler's law, determinism)
- Moon constants (radius, period, angle computation)
- Version and constants validation
- safe_addstr bounds checking and text truncation
- Bug fix regression tests (speed clamping, conjunction origin, generate_asteroids API)

## Bug Fixes (v2.1)

1. **Speed label was incorrect** — Displayed "days/frame" but the actual unit is "days/sec" (at ~30fps, speed=1.0 gives ~1 day/sec). Fixed to display "days/sec" throughout (info panel, speed input prompt, and CLI help text).

2. **Label rendering off-by-one** — Labels that exactly fit at the terminal right edge were incorrectly skipped (`< width` should have been `<= width`). A 3-character label at column `width-3` would now render correctly.

3. **Conjunction detection false positive at origin** — A planet at position (0, 0) would have `atan2(0, 0) = 0`, causing false conjunctions with planets on the X-axis. Now skips degenerate origin positions.

4. **Unicode rendering overflow** — Planet symbols (☿♀⊕♂♃♄♅♆) and the Sun character (☀) may be wide (2-column) characters on some terminals. Added bounds checks that fall back to ASCII symbols when too close to the right edge, and handle `UnicodeEncodeError` in addition to `curses.error`.

5. **Key bindings case sensitivity** — Only 'q/Q' accepted both cases; all other letter keys (o, l, t, a, m, d, s, h, r) only worked with lowercase. Now all keys accept both uppercase and lowercase. Also added `_` as an alias for `-` (slow down).

6. **Moon overlap on small terminals** — Moon display radius minimum was 1 screen unit, which could overlap with Earth. Raised to 2 screen units.

7. **Speed property not validated on assignment** — `OrreryState.speed` could be set to negative values directly, causing time to run backwards. Now implemented as a property that clamps values to the range [0.01, 3650].

8. **`generate_asteroids()` had unused parameters** — The function took `height` and `width` parameters but never used them. Removed these unused parameters for a cleaner API.

## Bug Fixes (from v1.0 → v2.0)

1. **`generate_stars()` crashed on zero/negative terminal dimensions** — Now returns an empty list instead of raising `ValueError`.
2. **Starfield regenerated every frame** — Stars are now only regenerated on terminal resize.
3. **Trail toggle was broken** — Now T properly toggles trail accumulation on/off.
4. **No speed validation** — The S key now only accepts positive values.
5. **`planet_position()` crashed on zero period** — Now validates `period > 0` and `a > 0`.
6. **`solve_kepler()` accepted invalid eccentricities** — Now raises `ValueError` for e ≥ 1 or e < 0.
7. **Unicode planet symbols could crash on limited terminals** — Added fallback handling.
8. **Info panel could overflow terminal width** — Added `safe_addstr()` helper that truncates safely.
9. **No frame time cap** — dt_frame now capped at 0.5 seconds.
10. **`draw_orbit()` could write outside terminal bounds** — Added bounds checking.
11. **Date input accepted invalid dates** — Added validation for year 1–9999.

## What's New in v2.0

- **CLI flags**: `--help`, `--version`, `--date`, `--speed`, `--no-trails`, `--no-moon`, `--asteroids`
- **Conjunction detection**: Alerts when planets are within 5° of each other
- **Earth's Moon**: Animated Moon orbiting Earth (toggle with `M`)
- **Asteroid belt**: 60 animated asteroids between Mars and Jupiter (toggle with `A`)
- **Orbital velocity**: Live km/s readout in info panel via vis-viva equation
- **Current distance**: Shows actual distance from Sun (varies with eccentricity)
- **Jump to today**: Press `H` to set the date to now