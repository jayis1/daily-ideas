# 🏠 Terminal Lighthouse Keeper

A meditative ASCII resource management game where you keep a lighthouse burning through the night. Manage your fuel, maintain the lens, cool the engine, rescue ships in distress, and survive until dawn — all from your terminal.

## Description

The sun has set. You are the lighthouse keeper, responsible for guiding ships safely through the darkness. Storms roll in, the engine overheats, the lens cracks, and ships cry for help. Your job: keep the light burning until dawn — or until too many ships are lost.

This is a real-time terminal game built with `curses`. Watch the moon traverse the sky, see waves crash against the shore, and feel the tension as fuel runs low and a storm bears down on you.

## Features

- **Dynamic weather system** — Clear skies, rain, and storms that affect fuel consumption and lens health
- **Animated ASCII seascape** — Waves, moon, stars, and rain rendered in real-time with wind effects
- **Resource management** — Balance fuel, lens health, engine temperature, and beam intensity
- **Ship rescue** — Spot distressed ships (marked "SOS!⛵") and signal them to safety for bonus points
- **Efficiency mode** — Toggle eco mode with `E` to reduce fuel consumption by 40% (beam capped at 60%)
- **Random events** — Supply crates wash ashore, lens cracks appear, engines surge, seagulls visit
- **Three difficulty levels** — Easy, Medium (default), and Hard with different starting resources and storm frequency
- **Scoring system** — Points for ships saved, fuel remaining, lens health, engine condition, and difficulty multiplier
- **High scores** — Top 10 scores saved to `~/.lighthouse_scores.json`
- **Lose condition** — The game ends if you run out of fuel and lose 3+ ships
- **Full night cycle** — Survive from 6 PM to 6 AM with an accelerated clock
- **Pause** — Press `SPACE` to pause/resume the game

## How to Install

No external dependencies needed — just Python 3.6+ with the standard library (curses is included on most systems).

```bash
cd ~/daily-ideas/2026-07-08-terminal-lighthouse-keeper
```

**Note for Windows users:** You may need to install `windows-curses`:
```bash
pip install windows-curses
```

## How to Run

```bash
# Start with normal difficulty (default)
python3 lighthouse.py

# Start with easy difficulty (more fuel, fewer storms)
python3 lighthouse.py --difficulty easy

# Start with hard difficulty (less fuel, more storms)
python3 lighthouse.py --difficulty hard

# Show version
python3 lighthouse.py --version

# Show help
python3 lighthouse.py --help
```

## Controls

| Key | Action |
|-----|--------|
| `B` | Toggle the lighthouse beam on/off |
| `E` | Toggle efficiency (eco) mode — 40% less fuel, beam capped at 60% |
| `R` | Refuel (costs 5 minutes, restores 15–30% fuel) |
| `F` | Fix the lens (costs 3 minutes, restores 10–25% lens health) |
| `C` | Cool the engine (costs 2 minutes, reduces engine temp by 15–30°) |
| `S` | Signal a distressed ship to guide it to safety (+200 points) |
| `SPACE` | Pause / resume the game |
| `Q` | Quit the game |

When the game is over, press `R` to restart or `Q` to quit.

## Gameplay Tips

- **Keep fuel above 15%** — You'll get a warning, and if it hits 0, the light goes out!
- **Watch engine temperature** — If it hits 100°, the engine shuts down and the beam turns off
- **Lens health affects beam intensity** — A cracked lens means a dimmer beam
- **Turn off the beam strategically** — Saves fuel but risks losing ships
- **Use efficiency mode** — Toggle `E` to cut fuel consumption by 40% when things are calm
- **Rescue distress ships quickly** — They have a timer before they're lost
- **Storms increase fuel consumption** — Stock up on fuel before bad weather
- **Supply crates are rare blessings** — They restore both fuel and lens health
- **Don't let ships pile up** — If 3+ ships are lost while your light is out, the game ends

## What It Does

The game simulates a full night (6 PM to 6 AM) as a lighthouse keeper. Each game-minute ticks by in about one second of real time. You manage four interconnected resources:

1. **Fuel** — Depletes over time while the beam is on. Refuel with `R`.
2. **Lens health** — Degrades in storms. Repair with `F`.
3. **Engine temperature** — Rises while the beam is on. Cool it with `C`.
4. **Beam intensity** — Determined by fuel × lens health. Determines how well ships can see you.

Ships sail across the sea — some in distress (marked "SOS!⛵"). Signal them with `S` to rescue them. Your final score depends on ships saved, fuel remaining, lens health, and engine condition at dawn, multiplied by your difficulty level.

## Testing

```bash
python3 -m pytest test_game.py -v
```

The test suite includes 49 tests covering time advancement, dawn detection, resource bounds, event effects, rendering, difficulty settings, and lose/win conditions.

## Changelog

### v1.1.1 — Bug Fix Release

**Fixed:**
- **Critical: False dawn trigger in `_advance_time`** — Refueling, fixing the lens, or cooling the engine during evening hours (18:00–23:59) could incorrectly trigger the "Dawn has broken!" game-over, because the dawn check was missing the `hour < NIGHT_START` guard. Now only triggers between 6 AM and 6 PM.
- **Critical: Hour overflow past 24** — Both `tick()` and `_advance_time()` could increment the hour past 24 without wrapping, causing invalid time states. Hours now correctly wrap at midnight.
- **Storm intensity could go negative** — `storm_intensity` was only clamped at the upper bound (100) but could drift below 0. Now clamped to `[0, 100]`.
- **Beam intensity never reached 0** — When the beam was turned off, `beam_intensity *= 0.9` asymptotically approached 0 but never actually reached it. Now floors to 0 when below 0.1.
- **No lose condition** — The game could run indefinitely with 0 fuel and no beam. Now ends if you've been out of fuel for 300+ ticks AND have lost 3+ ships.
- **Redundant hour_display code** — The 12-hour time display computed `hour_display` twice; the first assignment was dead code. Cleaned up to use a clear if/elif/else structure.
- **Hardcoded test path** — `test_game.py` used an absolute path in `sys.path.insert`. Replaced with a relative path using `os.path.dirname`.
- **Test suite rewritten** — Replaced the minimal test script with a comprehensive pytest suite (49 tests) covering time logic, dawn detection, resource bounds, events, rendering, difficulty, and CLI arguments.

### v1.1.0 — Enhancement Release (previous)

- Added difficulty levels (easy/medium/hard)
- Added efficiency (eco) mode
- Added wind system affecting ship movement
- Added high score persistence
- Added pause functionality
- Added `--difficulty`, `--version`, `--help` CLI flags
- Added statistics tracking
- Various code quality improvements