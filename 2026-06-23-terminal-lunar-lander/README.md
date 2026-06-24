# 🌙 Terminal Lunar Lander

A classic physics-based lunar landing game rendered entirely in ASCII art. Pilot your lunar module safely to the surface by managing thrust, fuel, and descent angle across procedurally generated terrain — with real Moon gravity, wind systems, high scores, and an autopilot demo mode.

## Description

Terminal Lunar Lander recreates the iconic 1979 Atari game experience in your terminal. Navigate your lander through a realistic lunar descent with actual Moon gravity (1.625 m/s²), finite fuel reserves, and procedurally generated terrain complete with craters and designated landing pads.

Land softly on a highlighted pad with minimal speed and angle for maximum points — or crash spectacularly into the lunar surface. Your best scores are saved between sessions, and you can watch the autopilot show you how it's done in demo mode.

## Features

- **Realistic Physics** — Real lunar gravity (1.625 m/s²), thrust vectoring based on rotation angle, fuel consumption that directly impacts your descent options
- **Procedural Terrain** — Every game generates unique lunar terrain with midpoint displacement algorithm, random craters, and varied landing pad placement
- **Three Difficulty Levels**:
  - **CADET** — 120 fuel units, forgiving pads (8 wide), no wind
  - **PILOT** — 80 fuel units, smaller pads (5 wide), mild wind gusts
  - **COMMANDER** — 50 fuel units, tiny pad (4 wide), strong wind
- **Landing Assessment** — Detailed breakdown of speed, angle, pad proximity, and fuel efficiency with a final score
- **High Score System** — Top 10 scores per difficulty persisted to disk; best score shown on title screen
- **Restart After Landing** — Press R after landing or crashing to play again without restarting the program
- **Demo Mode / Autopilot** — Press D on the title screen (or use `--demo`) to watch an AI-controlled landing
- **In-Game Warnings** — Real-time alerts for "TOO FAST!", "HIGH DESCENT RATE!", "STEEP ANGLE!", "LOW FUEL!", and "NO FUEL!"
- **ASCII Art UI** — Title screen with lander illustration, in-game HUD with colored fuel bar, altitude gauge, speed indicator, and crash/landing animations
- **Visual Fuel Bar** — Color-coded on-screen fuel gauge (green → yellow → red) shows remaining fuel at a glance
- **Altitude Gauge** — Right-side altitude bar shows your height above terrain visually
- **Landing Pad Beacons** — Flashing ◈/◇ markers above each landing pad for better visibility
- **Speed Indicator** — HUD shows ● (safe), ◘ (caution), or ◆ (danger) next to your speed
- **Particle Effects** — Expanded thrust particles when firing engine, debris cloud on crash
- **Star Twinkling** — Background stars occasionally shift brightness
- **Wind System** — Sinusoidal wind gusts on harder difficulties that push your lander sideways
- **Score System** — Points based on fuel remaining, landing speed, angle precision, and whether you hit a pad, multiplied by difficulty
- **CLI Arguments** — `--help`, `--version`, `--easy`, `--medium`, `--hard`, and `--demo` flags
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

# Watch the autopilot land the module
python3 lunar_lander.py --demo

# Show version
python3 lunar_lander.py --version

# Show help
python3 lunar_lander.py --help
```

## Controls

| Key | Action |
|-----|--------|
| `←` / `A` | Rotate counter-clockwise |
| `→` / `D` | Rotate clockwise |
| `↑` / `W` | Fire main thruster |
| `R` | Restart (after landing or crash) |
| `Q` / `ESC` | Quit game |

## Usage Examples

```
$ python3 lunar_lander.py

  ╔═══════════════════════════════╗
  ║     L U N A R   L A N D E R  ║
  ║         ─────────────        ║
  ║     Terminal Edition v1.2.0  ║
  ╚═══════════════════════════════╝

       ▲
      /█\
     / █ \
    /  █  \
   /__███__\
    ║     ║
   ╱       ╲
  ▕  ▓▓▓▓▓▓  ▏
   ╲       ╱

Select Difficulty:
  [1] CADET   — Lots of fuel, forgiving pads
  [2] PILOT   — Moderate challenge
  [3] COMMANDER — Minimal fuel, tiny pads, wind
  [Q] Quit    [D] Demo mode
```

### In-Game HUD

```
┌─ LUNAR LANDER ─────────┐     AL
│ ALT:       28.3 m      │     ──
│ V-SPD:     -3.42 m/s   │     ██
│ H-SPD:      0.12 m/s   │     ██
│ ANGLE:      5.0  °     │     ░░
│ FUEL:    ████████░░░░   │     ░░
│ SPEED:      3.42 m/s ● │     ░░
│ TIME:      12.4 s      │     ──
│ WIND:    → 0.23        │
└────────────────────────┘
```

The fuel bar changes color: **green** (above 50%), **yellow** (20-50%), **red** (below 20%). The altitude gauge on the right shows your height above terrain as a vertical bar. The speed indicator shows ● (safe), ◘ (caution), or ◆ (danger) based on landing speed thresholds.

### Landing Results

- **PERFECT** — Landed on pad within speed and angle limits. Maximum score!
- **ROUGH** — On pad but slightly over limits. Partial score.
- **HARD** — Off-pad or significantly over limits, but survived.
- **CRASH** — Too fast, wrong angle, or not on terrain. 💥

After any result, the top 3 high scores for your difficulty are displayed. Press **R** to play again or any other key to quit.

## How It Works

1. **Terrain Generation**: Uses midpoint displacement with random perturbation, then overlays craters using quadratic falloff. Landing pads flatten and widen specified sections. Pads are guaranteed to never overlap and always have heights matching the terrain surface.

2. **Physics Engine**: Each frame integrates gravity, thrust (decomposed into x/y from rotation angle), and wind. Velocity and position update via Euler integration with delta-time capping at 0.1s to prevent tunneling.

3. **Collision Detection**: Checks if the lander's y-position crosses the terrain height at its x-position. Landing success is evaluated against difficulty-specific thresholds for speed, angle, and pad proximity.

4. **Autopilot (Demo Mode)**: A proportional controller steers toward the nearest landing pad, adjusting rotation and thrust to cancel horizontal velocity and maintain a safe descent rate. It's not perfect — watch it sometimes crash for fun!

5. **High Scores**: Stored in `.lunar_highscores.json` next to the script. Top 10 per difficulty, sorted descending. Best scores appear on the title screen next to each difficulty option.

6. **Rendering**: The curses library draws terrain character-by-character using Unicode block characters (`▀`, `▄`, `█`, `━`), with a sprite-based lander, flashing pad beacons, and random particle effects for thrust and crashes.

## Testing

```bash
# Run the full test suite (44 tests)
python3 -m pytest test_lunar_lander.py -v

# Or with unittest
python3 -m unittest test_lunar_lander -v
```

Tests cover terrain generation (surface bounds, pad alignment, overlap prevention, reproducibility), physics constants, difficulty configs, CLI argument parsing, score calculation, horizontal wrapping, high score persistence (save/load, sorting, limits, corruption handling), and autopilot behavior.

## Changelog

### v1.2.0 — Feature Release

**Added:**
- **High score system** — Top 10 scores per difficulty saved to `.lunar_highscores.json`; best score shown on title screen
- **Restart after landing** — Press R on the result screen to play again without quitting
- **Demo/autopilot mode** — Press D on title screen or use `--demo` flag to watch AI land the module
- **In-game warnings** — Real-time alerts for high speed, steep angle, low fuel, and no fuel
- **Altitude gauge** — Vertical bar on the right side of the HUD
- **Landing pad beacons** — Flashing ◈/◇ markers above each pad
- **Speed indicator** — ●/◘/◆ symbol next to speed value based on landing thresholds
- **Colored fuel bar** — Green → yellow → red as fuel decreases
- **Expanded thrust particles** — More particles when thrusting, debris cloud on crash
- **Star twinkling** — Background stars randomly shift brightness
- **Version in title** — Title screen shows current version
- **Type hints** — Added throughout the codebase for better documentation

**Improved:**
- Score calculation now clamps fuel and speed percentages to [0, ∞) to prevent negative bonuses
- Thrusting sprite is now more distinct (larger flame, extra particles)
- Better error handling in rendering (replaced bare `except` with `except curses.error`)
- Code documentation expanded with docstrings on all new functions

### v1.1.0 — Bug Fix Release

**Fixed:**
- **Pad height mismatch** — Landing pad `py` values could differ from actual terrain heights
- **Overlapping pads** — Pads could randomly overlap; now enforce minimum gap
- **Fuel bar not drawn** — Computed but never rendered; now visible with color coding
- **Missing CLI arguments** — Added `--help`/`-h`, `--version`/`-v`, `--easy`, `--medium`, `--hard`
- **Non-TTY crash** — Now prints clear error and exits gracefully
- **Fuel bar percentage clamping** — Could go negative; now clamped to [0.0, 1.0]
- **Added `__version__`** — Module exports version for tracking

## License

MIT