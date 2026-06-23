# 🌙 Terminal Lunar Lander

A classic physics-based lunar landing game rendered entirely in ASCII art. Pilot your lunar module safely to the surface by managing thrust, fuel, and descent angle across procedurally generated terrain.

## Description

Terminal Lunar Lander recreates the iconic 1979 Atari game experience in your terminal. Navigate your lander through a realistic lunar descent with actual Moon gravity (1.625 m/s²), finite fuel reserves, and procedurally generated terrain complete with craters and designated landing pads.

Land softly on a highlighted pad with minimal speed and angle for maximum points — or crash spectacularly into the lunar surface.

## Features

- **Realistic Physics** — Real lunar gravity (1.625 m/s²), thrust vectoring based on rotation angle, and fuel consumption that directly impacts your descent options
- **Procedural Terrain** — Every game generates unique lunar terrain with midpoint displacement algorithm, random craters, and varied landing pad placement
- **Three Difficulty Levels**:
  - **CADET** — 120 fuel units, forgiving pads (8 wide), no wind
  - **PILOT** — 80 fuel units, smaller pads (5 wide), mild wind gusts
  - **COMMANDER** — 50 fuel units, tiny pad (4 wide), strong wind
- **Landing Assessment** — Detailed breakdown of speed, angle, pad proximity, and fuel efficiency with a final score
- **ASCII Art UI** — Title screen with lander illustration, in-game HUD, particle thrust effects, and crash/landing animations
- **Visual Fuel Bar** — On-screen fuel gauge shows remaining fuel at a glance
- **Wind System** — Sinusoidal wind gusts on harder difficulties that push your lander sideways
- **Score System** — Points based on fuel remaining, landing speed, angle precision, and whether you hit a pad, multiplied by difficulty
- **CLI Arguments** — `--help`, `--version`, and `--easy`/`--medium`/`--hard` flags for quick start
- **Non-TTY Detection** — Helpful error message if run without an interactive terminal

## Installation

No external dependencies required — uses only Python's built-in `curses` library.

```bash
# Clone the repo
git clone <repo-url>
cd terminal-lunar-lander

# No pip install needed! Just run:
python3 lunar_lander.py
```

### Requirements

- Python 3.7+
- Terminal with curses support (Linux/macOS terminals, Windows Terminal with WSL)
- Minimum terminal size: 70 columns × 24 rows

## How to Run

```bash
# Interactive — shows title screen to pick difficulty
python3 lunar_lander.py

# Skip title screen and start on a specific difficulty
python3 lunar_lander.py --easy
python3 lunar_lander.py --medium
python3 lunar_lander.py --hard

# Show version
python3 lunar_lander.py --version

# Show help
python3 lunar_lunar_lander.py --help
```

## Controls

| Key | Action |
|-----|--------|
| `←` / `A` | Rotate counter-clockwise |
| `→` / `D` | Rotate clockwise |
| `↑` / `W` | Fire main thruster |
| `Q` / `ESC` | Quit game |

## Usage Examples

```
$ python3 lunar_lander.py

  ╔═══════════════════════════════╗
  ║     L U N A R   L A N D E R  ║
  ║         ─────────────        ║
  ║     Terminal Edition          ║
  ╚═══════════════════════════════╝

       ▲
      /█\
     / █ \
    /  █  \
   /__███___\
    ║     ║
   ╱       ╲
  ▕  ▓▓▓▓▓▓  ▏
   ╲       ╱

Select Difficulty:
  [1] CADET   — Lots of fuel, forgiving pads
  [2] PILOT   — Moderate challenge
  [3] COMMANDER — Minimal fuel, tiny pads, wind
  [Q] Quit
```

### In-Game HUD

```
┌─ LUNAR LANDER ─────────┐
│ ALT:       28.3 m      │
│ V-SPD:     -3.42 m/s   │
│ H-SPD:      0.12 m/s   │
│ ANGLE:      5.0  °     │
│ FUEL:    ████████░░░░   │
│ SPEED:      3.42 m/s   │
│ TIME:      12.4 s      │
│ WIND:    → 0.23         │
└────────────────────────┘
```

### Landing Results

- **PERFECT** — Landed on pad within speed and angle limits. Maximum score!
- **ROUGH** — On pad but slightly over limits. Partial score.
- **HARD** — Off-pad or significantly over limits, but survived.
- **CRASH** — Too fast, wrong angle, or not on terrain. 💥

## How It Works

1. **Terrain Generation**: Uses midpoint displacement with random perturbation, then overlays craters using quadratic falloff. Landing pads flatten and widen specified sections. Pads are guaranteed to never overlap and always have heights matching the terrain surface.

2. **Physics Engine**: Each frame integrates gravity, thrust (decomposed into x/y from rotation angle), and wind. Velocity and position update via Euler integration with delta-time capping at 0.1s to prevent tunneling.

3. **Collision Detection**: Checks if the lander's y-position crosses the terrain height at its x-position. Landing success is evaluated against difficulty-specific thresholds for speed, angle, and pad proximity.

4. **Rendering**: The curses library draws terrain character-by-character using Unicode block characters (`▀`, `▄`, `█`, `━`), with a sprite-based lander and random particle effects for thrust and crashes.

## Testing

```bash
# Run the test suite (23 tests)
python3 -m pytest test_lunar_lander.py -v

# Or with unittest
python3 -m unittest test_lunar_lander -v
```

## Changelog

### v1.1.0 — Bug Fix Release

**Fixed:**
- **Pad height mismatch** — Landing pad `py` values could differ from the actual terrain surface heights after integer conversion, causing invisible mismatches between displayed terrain and collision data. Pads are now created after integer conversion and always flatten the surface to match.
- **Overlapping pads** — Pads could randomly overlap each other, creating confusing terrain and unfair gameplay. Pads now enforce a minimum gap between each other.
- **Fuel bar not drawn** — The fuel bar was computed in `_draw_hud()` but never actually rendered on screen. The visual bar now appears next to the fuel value in the HUD.
- **Missing CLI arguments** — No `--help`, `--version`, or difficulty shortcut flags existed. Added `--help`/`-h`, `--version`/`-v`, `--easy`, `--medium`, `--hard`.
- **Non-TTY crash** — Running without an interactive terminal produced an unhelpful curses error. Now prints a clear error message and exits gracefully.
- **Fuel bar percentage clamping** — Fuel percentage could go negative when fuel was depleted, causing visual glitches. Now clamped to [0.0, 1.0].
- **Added `__version__`** — Module now exports `__version__` for version tracking.

## License

MIT