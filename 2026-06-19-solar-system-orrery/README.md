# 🪐 Solar System Orrery

A beautiful animated terminal-based orrery that displays all eight planets orbiting the Sun using real orbital mechanics. Watch Mercury race around while Neptune crawls — all in your terminal!

## Features

- **Real Orbital Mechanics**: Uses Kepler's equation solver (Newton's method) to compute true anomaly from mean anomaly, giving accurate elliptical orbits with proper eccentricity
- **All 8 Planets**: Mercury through Neptune with real semi-major axes, orbital periods, and eccentricities
- **Power-Compressed View**: Smart distance scaling (power 0.55) so inner and outer planets are all visible simultaneously
- **Trails**: Toggle orbital trails on/off with the T key — see where planets have been
- **Time Control**: Speed up or slow down time, jump to any date, or pause to study positions
- **Zoom**: Zoom in/out to focus on inner planets or see the full system
- **Planet Selection**: Browse planet info with arrow keys — see distance, period, eccentricity, and live position
- **Starfield Background**: Randomly generated stars for atmosphere (regenerated only on terminal resize)
- **Perspective Effect**: Y-axis compression gives a subtle 3D perspective feel
- **Robust Error Handling**: Gracefully handles small terminals, invalid inputs, and edge cases

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
| `T` | Toggle orbital trails on/off |
| `D` | Jump to a specific date (YYYY-MM-DD) |
| `S` | Set simulation speed manually (must be > 0) |
| `R` | Reset to default view, date, and trails |
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

**Toggle trails to see orbit paths:**
```
Press 'T' to enable trails and watch them accumulate as planets move.
Press 'T' again to clear trails and stop accumulation.
```

## How It Works

The orrery uses **Kepler's equation** (`M = E - e·sin(E)`) solved via Newton's method to convert mean anomaly to eccentric anomaly, then derives the true anomaly for accurate elliptical motion. The Y-axis is compressed by 0.5× to give a subtle 3D perspective effect. Distances are scaled with a power law (0.55) so that both Mercury (0.387 AU) and Neptune (30 AU) fit on screen while remaining visually distinguishable.

Orbital parameters are real values from J2000 epoch data.

## Architecture

- `solve_kepler(M, e)` — Solves Kepler's equation with Newton's method. Validates eccentricity (0 ≤ e < 1).
- `planet_position(a, period, e, years)` — Computes (x, y) in AU from orbital elements. Validates period > 0 and a > 0.
- `au_to_screen(x, y, cx, cy, scale, max_r)` — Maps AU coordinates to screen coordinates with power-law compression.
- `draw_orbit()` — Draws an orbital ellipse as a dotted path.
- `generate_stars()` — Creates a deterministic starfield (seeded). Returns empty list for degenerate terminal sizes.
- `OrreryState` — Tracks date, speed, selection, trail data, and UI toggles.
- `main()` — Curses event loop handling input, simulation, and rendering.

## Testing

```bash
python3 test_orrery.py
```

Runs 65 tests covering:
- Kepler solver (convergence, edge cases, invalid inputs)
- Planet position calculations (circular orbits, all 8 planets, invalid parameters)
- Screen coordinate mapping (origin, clamping, perspective compression)
- Star generation (bounds checking, degenerate sizes, determinism)
- State management (defaults, toggle behavior)
- Orbital mechanics consistency (perihelion/aphelion ranges, periodicity)

## Bug Fixes (from initial version)

1. **`generate_stars()` crashed on zero/negative terminal dimensions** — Now returns an empty list instead of raising `ValueError` from `randint(0, -1)`.
2. **Starfield regenerated every frame** — Stars are now only regenerated on terminal resize, not every frame. This also stopped resetting the global `random.seed(42)` 30 times per second.
3. **Trail toggle was broken** — Pressing T cleared trails but they immediately re-accumulated (no off state). Now T properly toggles trail accumulation on/off, and the info panel shows trail status.
4. **No speed validation** — The S key accepted any float including negative and zero values, causing time reversal or permanent freeze. Now only positive values are accepted.
5. **`planet_position()` crashed on zero period** — Division by zero when `period=0`. Now validates `period > 0` and `a > 0`.
6. **`solve_kepler()` accepted invalid eccentricities** — Values of e ≥ 1 (parabolic/hyperbolic orbits) would produce garbage or infinite loops. Now raises `ValueError`.
7. **Unicode planet symbols could crash on limited terminals** — Added fallback handling for `UnicodeEncodeError` so terminals without UTF-8 support gracefully degrade to ASCII symbols (Me, Ve, Ea, Ma, Ju, Sa, Ur, Ne).
8. **Info panel could overflow terminal width** — Added `safe_addstr()` helper that truncates strings to fit terminal dimensions and checks bounds before drawing.
9. **No frame time cap** — If the window was hidden/minimized, `dt_frame` could become huge on return, causing planets to jump. Now capped at 0.5 seconds.
10. **`draw_orbit()` could write outside terminal bounds** — Added bounds checking for each drawn character.
11. **Date input accepted invalid dates** — Added validation for reasonable date range (year 1–9999).