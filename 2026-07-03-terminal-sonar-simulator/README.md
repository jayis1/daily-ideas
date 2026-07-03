# 🎯 Terminal Sonar Simulator

A submarine combat game played entirely in the terminal. Navigate a fog-of-war ocean using sonar pings to detect, classify, and destroy hidden enemy vessels — while trying not to give away your own position.

**Version 1.2.0**

## What's New

### v1.2.0 (Bug Fixes)
- **Fixed inverted depth controls** — Z now correctly dives deeper (depth increases) and X correctly rises shallower (depth decreases). Previously these were swapped, making Z rise and X dive!
- **Fixed passive sonar spam** — Passive listening burst (P key) now has a cooldown (half the active ping cooldown) and cannot be spammed infinitely.
- **Fixed passive mode feedback** — Pressing P in active sonar mode now shows "Switch to passive mode first (E)" instead of silently doing nothing.
- **Fixed camera centering** — The submarine now appears vertically centered in the viewport. Previously the camera offset used `h-4` instead of `h-6`, causing the sub to appear ~1 line off-center.
- **Added boundary feedback** — Pressing Z at max depth or X at min depth now shows informative messages instead of silently doing nothing.
- **Added 11 new tests** (49 total) covering depth control logic, passive sonar constraints, and camera centering.

### v1.1.0 (Feature Update)
- Difficulty levels, supply crates, bearing indicators, noise mechanics, long-range fire, time tracking, depth damage reduction, CLI flags, and 38 unit tests.

## Description

You command a submarine in an ocean filled with enemy vessels. The ocean is cloaked in fog of war — you can only see what your sonar reveals. Fire active sonar pings to illuminate large areas, but beware: every ping also tells enemies where you are. Switch to passive sonar mode for stealth, but with dramatically reduced detection range. Manage your depth, conserve torpedoes, and hunt down all enemy ships before they find and sink you.

## Features

- **Fog of War** — The ocean is dark. You only see what your sonar reveals.
- **Active & Passive Sonar** — Trade off between detection power and stealth.
- **Depth System** — Dive deep for protection and health regen but lose visibility; rise to periscope depth for better intel.
- **Noise Mechanic** — Movement and pinging generate noise that alerts nearby enemies. Deep diving reduces noise.
- **Bearing Indicators** — HUD shows compass arrows and distances to classified contacts.
- **3 Enemy Types** — Destroyers (tough, balanced), Submarines (deadly, long-range detection), Patrol Boats (fast, weak).
- **Enemy AI** — Enemies patrol, get alerted by your pings and noise, chase you, and fire torpedoes back.
- **Torpedo Combat** — Fire at nearest (`F`) or farthest (`G`) classified target; manage your limited ammo.
- **Supply Crates** — Pick up floating crates for torpedo refills and hull repairs.
- **Procedural World** — Randomly generated island archipelagos each game. Use `--seed` for reproducible maps.
- **Difficulty Levels** — Easy / Normal / Hard with tuned enemy stats, count, and player loadout.
- **Minimap** — Toggle a strategic overview showing classified enemy positions and supply crates.
- **Particle Effects** — Explosions, torpedo trails, and sonar ring animations.
- **Time Bonus** — Finishing quickly earns bonus score points.
- **Health & Ammo Management** — Slowly resupply torpedoes over time; heal at deep depth; pick up supply crates.
- **Scoring** — Points for each kill, time bonus for victory.

## How to Install

Requires Python 3.7+ with the standard library only (uses `curses`):

```bash
# Clone the repository
git clone <repo-url>
cd 2026-07-03-terminal-sonar-simulator

# No pip dependencies needed — just run it
```

On **Windows** you need to install the curses compatibility layer:
```bash
pip install windows-curses
```

On Linux and macOS, `curses` ships with Python by default.

## How to Run

```bash
# Default (normal difficulty, 10 enemies)
python3 sonar.py

# Easy mode
python3 sonar.py --difficulty easy

# Hard mode with 20 enemies
python3 sonar.py --difficulty hard --enemies 20

# Reproducible world seed
python3 sonar.py --seed 42

# Show help
python3 sonar.py --help

# Print version
python3 sonar.py --version
```

Make sure your terminal is at least **80×30 characters** for the best experience.

## Controls

| Key | Action |
|-----|--------|
| `W/A/S/D` or Arrow Keys | Move submarine |
| `SPACE` | Fire active sonar ping (reveals large area, alerts enemies, costs cooldown) |
| `E` | Toggle active/passive sonar mode |
| `P` | Passive sonar listening burst (short range, stealthy, has cooldown) |
| `F` | Fire torpedo at nearest classified enemy |
| `G` | Fire torpedo at farthest classified enemy (long-range engage) |
| `Z` | Dive deeper (more protection, less visibility, less noise) |
| `X` | Rise shallower (less protection, more visibility, more noise) |
| `M` | Toggle minimap |
| `Q` | Quit |
| `R` | Restart (after game over or victory) |

## Game Objects

| Symbol | Object |
|--------|--------|
| `▲` | Your submarine |
| `D` | Enemy Destroyer (HP: 3) |
| `S` | Enemy Submarine (HP: 2) |
| `P` | Enemy Patrol Boat (HP: 1) |
| `█` / `▓` | Island / land |
| `░` | Shallow water |
| `~` | Deep water |
| `○` / `∘` | Sonar ping ring |
| `▸` | Friendly torpedo |
| `◃` | Enemy torpedo |
| `T` | Torpedo supply crate |
| `+` | Repair kit crate |

## Depth System

| Depth Level | Visibility | Damage Reduction | Noise | Health Regen |
|-------------|-----------|-------------------|-------|-------------|
| Periscope (0) | 100% | 0% | High | None |
| Shallow (1) | 70% | 25% | Medium | None |
| Deep (2) | 40% | 50% | Low | +1 HP/min |

- Press **Z** to dive deeper (more protection, less visibility).
- Press **X** to rise shallower (more visibility, less protection).
- Active pings generate 0.4 noise regardless of depth.
- Movement noise decreases with depth (0.15 → 0.08 → 0.03 per step).

## Difficulty Levels

| Setting | Enemies | Torpedoes | Enemy HP | Enemy Detection | Fire Rate | Ping Cooldown |
|---------|---------|-----------|----------|-----------------|-----------|---------------|
| Easy | 6 | 12 | ×0.7 | ×0.6 | 1.5% | 10 frames |
| Normal | 10 | 8 | ×1.0 | ×1.0 | 3.0% | 15 frames |
| Hard | 15 | 6 | ×1.3 | ×1.4 | 5.0% | 20 frames |

## Strategy Tips

- **Active pings are loud** — enemies within range will detect you and start hunting.
- **Use passive mode** to sneak around without revealing yourself, but your vision is limited.
- **Depth matters** — at deep depth you take less torpedo damage and generate less noise, but you can barely see.
- **Classify before firing** — you can only lock torpedoes onto classified (detected) targets.
- **Watch your ammo** — torpedoes slowly resupply, and supply crates give +2 torpedoes.
- **Use islands as cover** — torpedoes and sonar can't pass through land.
- **Watch the noise bar** — high noise alerts nearby enemies even without pinging.
- **Pick up crates** — look for `T` and `+` on the map and minimap for crucial resupply.

## Running Tests

```bash
python3 test_sonar.py
```

49 tests covering world generation, enemy spawning, supply crates, data classes, difficulty presets, CLI parsing, helper functions, config consistency, depth controls, passive sonar constraints, and camera centering.

## Changelog

### v1.2.0
- **Fixed**: Z/X depth controls were inverted — Z now correctly dives deeper and X correctly rises shallower
- **Fixed**: Passive listening burst (P key) had no cooldown, allowing infinite passive pings — now costs half the active ping cooldown
- **Fixed**: Pressing P in active sonar mode silently did nothing — now shows "Switch to passive mode first (E)"
- **Fixed**: Camera vertical centering was off by ~1 line (used `h-4` instead of `h-6` to match viewport height)
- **Added**: Boundary messages when trying to dive at max depth or rise at periscope depth
- **Added**: 11 new tests for depth controls, passive sonar constraints, and camera centering (49 total)

### v1.1.0
- Added difficulty levels, supply crates, noise mechanic, bearing indicators, long-range fire, time tracking, depth damage reduction, CLI flags, and 38 unit tests

### v1.0.0
- Initial release

## License

MIT