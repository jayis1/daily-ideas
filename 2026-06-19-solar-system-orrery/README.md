# 🪐 Solar System Orrery v2.2

An animated terminal-based orrery that displays all eight planets orbiting the Sun using real orbital mechanics — now with Halley's Comet, elongation angles, retrograde detection, and perihelion/aphelion data.

## Features

### Core Mechanics
- **Real Orbital Mechanics** — Uses Kepler's equation solver (Newton's method) to compute true anomaly from mean anomaly, giving accurate elliptical orbits with proper eccentricity
- **All 8 Planets** — Mercury through Neptune with real semi-major axes, orbital periods, and eccentricities
- **Power-Compressed View** — Smart distance scaling (power 0.55) so inner and outer planets are all visible simultaneously
- **Starfield Background** — Randomly generated stars for atmosphere (regenerated only on terminal resize)

### Visualization
- **Earth's Moon** — A small dot orbiting Earth with the correct ~27.3-day period (toggle with `M`)
- **Asteroid Belt** — 60 animated asteroids between Mars and Jupiter following Kepler's third law (toggle with `A`)
- **Halley's Comet** — The famous comet with its highly eccentric orbit (e≈0.967), argument of perihelion rotation, and an animated tail that points away from the Sun and scales with distance (toggle with `C`)
- **Orbital Trails** — Toggle trail accumulation on/off with `T` to visualize orbit paths
- **Orbit Paths** — Dotted elliptical paths for all planets (toggle with `O`)
- **Planet Labels** — 3-letter labels next to each planet (toggle with `L`)
- **Perspective Effect** — Y-axis compression gives a subtle 3D perspective feel

### Information Panel
- **Selected Planet Info** — Shows semi-major axis, perihelion, aphelion, current distance from Sun, distance from Earth, orbital velocity (km/s), period, eccentricity, position in AU
- **Elongation Angle** — Shows the Sun-Earth-Planet angle with visibility status (Evening Star, Morning Star, Near Sun, Opposition)
- **Retrograde Motion** — Displays whether the selected planet is in prograde or retrograde motion
- **Conjunction Detection** — Automatically detects and alerts when two planets are within 5° of each other
- **Halley's Comet Info** — When visible, shows the comet's current distance from the Sun and velocity

### Controls
- **Time Control** — Speed up/slow down time, jump to any date, or pause
- **Zoom** — Zoom in/out to focus on inner planets or see the full system
- **Planet Selection** — Browse planet info with arrow keys
- **Jump to Today** — Press `H` to instantly jump to today's date
- **CLI Flags** — `--help`, `--version`, `--date`, `--speed`, `--no-trails`, `--no-moon`, `--asteroids`, `--comet`

### Robustness
- **Graceful Error Handling** — Handles small terminals, invalid inputs, and edge cases
- **Unicode Fallback** — Gracefully degrades to ASCII symbols on terminals without UTF-8 support
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

# Start with Halley's Comet visible
python3 orrery.py --comet

# Start with all features enabled
python3 orrery.py --speed 5 --asteroids --comet

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
| `C` | Toggle Halley's Comet |
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

**See Halley's Comet near perihelion:**
```
Press 'C' to enable the comet. Its highly eccentric orbit (e≈0.967) sweeps
from inside Mercury's orbit out past Neptune. The comet tail always points
away from the Sun and gets longer near perihelion.
```

**Check a planet's visibility from Earth:**
```
Press '←'/'→' to select a planet, then read the "Elongation" line in the
info panel. "Evening Star" means the planet is east of the Sun (visible after
sunset), "Morning Star" means west (visible before sunrise). "Near Sun"
means it's lost in the Sun's glare.
```

**Watch for retrograde motion:**
```
Speed up time and select Mars or Jupiter. The "Motion" line in the info
panel switches between "Prograde" and "Retrograde" — retrograde motion
occurs when Earth overtakes an outer planet.
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

**Study perihelion and aphelion distances:**
```
Select a planet and check the "Perihelion" and "Aphelion" lines in the info
panel. Mercury's orbit is most extreme: perihelion at 0.307 AU, aphelion
at 0.467 AU (eccentricity 0.206).
```

## How It Works

### Orbital Mechanics

The orrery uses **Kepler's equation** (`M = E - e·sin(E)`) solved via Newton's method to convert mean anomaly to eccentric anomaly, then derives the true anomaly for accurate elliptical motion. The Y-axis is compressed by 0.5× to give a subtle 3D perspective effect. Distances are scaled with a power law (0.55) so that both Mercury (0.387 AU) and Neptune (30 AU) fit on screen while remaining visually distinguishable.

### Orbital Velocity

The info panel displays real-time orbital velocity computed using the **vis-viva equation**: `v = √(GM·(2/r - 1/a))`, where GM☉ = 1.327×10¹¹ km³/s². This gives physically accurate velocities — Earth ~29.8 km/s, Mercury ~47.9 km/s, Neptune ~5.4 km/s.

### Halley's Comet

Halley's Comet uses real orbital parameters: semi-major axis 17.834 AU, eccentricity 0.967, period 75.32 years, and argument of perihelion 111.33°. The orbit is rotated by this angle, placing perihelion in the correct direction. The comet tail is computed by placing segments radially away from the Sun, with the tail length inversely proportional to distance (longer when closer to the Sun, matching real comet behavior).

### Elongation

Elongation is the angle Sun-Earth-Planet, computed using `atan2`. It determines whether an inner planet is visible as an "Evening Star" (east of Sun) or "Morning Star" (west of Sun). The cross product of the Sun-Earth and Planet-Earth vectors determines east vs. west.

### Retrograde Detection

The heliocentric longitude (`atan2(y, x)`) is tracked frame-to-frame for each planet. When it decreases, the planet is in retrograde — an apparent backward motion caused by Earth overtaking it in orbit.

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
- `halley_position(years)` — Computes Halley's Comet position with rotated orbit (argument of perihelion).
- `halley_tail_segments(x, y)` — Calculates anti-solar tail positions scaled by distance from Sun.
- `orbital_velocity_km_s(a, period, r)` — Computes orbital velocity at distance r via vis-viva equation.
- `compute_elongation(planet, earth)` — Calculates Sun-Earth-Planet angle for visibility.
- `elongation_status(angle, planet, earth)` — Determines Evening Star / Morning Star / Near Sun status.
- `compute_retrograde(prev, curr)` — Detects prograde vs. retrograde motion from position change.
- `format_distance_km(au)` — Formats AU distances with human-readable km units.
- `detect_conjunctions(positions, threshold)` — Finds planet pairs within a given angular threshold.
- `au_to_screen(x, y, cx, cy, scale, max_r)` — Maps AU coordinates to screen coordinates with power-law compression.
- `draw_orbit()` — Draws an orbital ellipse as a dotted path.
- `draw_halley_orbit()` — Draws Halley's comet orbit as sparse dots.
- `generate_asteroids(seed)` — Creates deterministic asteroid belt with Kepler-correct speeds.
- `generate_stars()` — Creates a deterministic starfield. Returns empty list for degenerate terminal sizes.
- `OrreryState` — Tracks date, speed (validated via property), selection, trail data, toggles, conjunction alerts, and previous positions for retrograde detection.
- `main()` — Curses event loop handling input, simulation, and rendering.
- `parse_args()` — CLI argument parser with --help, --version, --date, --speed, --no-trails, --no-moon, --asteroids, --comet.

## Testing

```bash
python3 test_orrery.py
```

Runs 179 tests covering:
- Kepler solver (convergence, edge cases, invalid inputs, large mean anomaly)
- Planet position calculations (circular orbits, all 8 planets, invalid parameters)
- Screen coordinate mapping (origin, clamping, perspective compression)
- Star generation (bounds checking, degenerate sizes, determinism)
- Date formatting
- Distance formatting (human-readable km units)
- State management (defaults, toggle behavior, speed property validation)
- Orbital mechanics consistency (perihelion/aphelion ranges, periodicity)
- Orbital velocity (vis-viva equation, edge cases, relative ordering)
- Conjunction detection (aligned, opposite, close, far, empty, format, degenerate origin)
- Asteroid belt generation (count, structure, Kepler's law, determinism)
- Moon constants (radius, period, angle computation)
- Halley's Comet (position, tail segments, rotation, perihelion/aphelion)
- Elongation calculation (near Sun, opposition, quadrature, self-reference)
- Elongation status (Evening Star, Morning Star, Near Sun)
- Retrograde detection (prograde, retrograde, no motion)
- Perihelion/aphelion (all planets, validation)
- Version and constants validation
- safe_addstr bounds checking and text truncation
- Bug fix regression tests (speed clamping, conjunction origin, generate_asteroids API)

## What's New in v2.2

### Halley's Comet
- Press `C` to toggle Halley's Comet with its real orbital parameters (a=17.834 AU, e=0.967, P=75.32 yr)
- The orbit is rotated by the argument of perihelion (111.33°) for accurate positioning
- An animated tail points away from the Sun and grows longer near perihelion
- The comet orbit is drawn as sparse dots to distinguish it from planet orbits
- Comet info (distance, velocity) appears in the info panel when enabled
- Use `--comet` CLI flag to start with the comet visible

### Elongation & Visibility
- The info panel now shows the elongation angle (Sun-Earth-Planet) for the selected planet
- Visibility status indicates whether the planet is an "Evening Star", "Morning Star", "Near Sun", or at "Opposition"
- Helps you understand when planets are actually visible in the sky

### Retrograde Motion
- The info panel shows "Prograde" or "Retrograde" for each planet based on heliocentric longitude change
- Watch Mars switch to retrograde when Earth overtakes it!

### Perihelion & Aphelion
- The info panel now shows perihelion and aphelion distances for the selected planet
- See how Mercury's orbit varies between 0.307 AU and 0.467 AU

### Distance from Earth
- The info panel shows the current distance from Earth to the selected planet (Distance⊕)
- Watch this value change as planets orbit at different speeds

### Other Improvements
- `prev_positions` tracking for retrograde detection
- `format_distance_km()` helper for human-readable distance strings
- Comet cyan color pair (pair 14)
- Comet toggle `C` key and `--comet` CLI flag

## Bug Fixes (v2.1)

1. **Speed label was incorrect** — Displayed "days/frame" but the actual unit is "days/sec". Fixed.
2. **Label rendering off-by-one** — Labels that exactly fit at the terminal right edge were incorrectly skipped.
3. **Conjunction detection false positive at origin** — Planets at (0, 0) no longer cause false conjunctions.
4. **Unicode rendering overflow** — Planet symbols now fall back to ASCII near the right edge.
5. **Key bindings case sensitivity** — All letter keys now accept both uppercase and lowercase.
6. **Moon overlap on small terminals** — Moon display radius minimum raised to 2 screen units.
7. **Speed property not validated on assignment** — Now clamps to [0.01, 3650].
8. **`generate_asteroids()` had unused parameters** — Removed for a cleaner API.