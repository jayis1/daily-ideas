# 🎯 Terminal Sonar Simulator

A submarine combat game played entirely in the terminal. Navigate a fog-of-war ocean using sonar pings to detect, classify, and destroy hidden enemy vessels — while trying not to give away your own position.

**Version 1.1.0** — Now with difficulty levels, supply crates, bearing indicators, noise mechanics, and CLI options.

## What's New in v1.1.0

- **Difficulty levels** — Choose `easy`, `normal`, or `hard` via `--difficulty`. Each adjusts enemy count, HP, detection range, fire rate, and torpedo loadout.
- **Supply crates** — Floating pickup crates scattered across the ocean grant torpedo refills (+2) or repair kits (+3 HP).
- **Noise mechanic** — Moving and pinging generates noise that enemies can detect. Deeper diving reduces your noise footprint. A noise bar in the HUD shows your current level.
- **Bearing indicators** — The HUD now shows directional arrows and distances to classified enemies (e.g. `→S14 ↑D8`).
- **Long-range fire** — Press `G` to fire a torpedo at the farthest classified target instead of the nearest.
- **Time tracking** — Elapsed game time is shown in the HUD; finishing quickly earns a time bonus on victory.
- **Depth damage reduction** — Taking hits at deeper depths now reduces damage by 25% (shallow) or 50% (deep), matching the HUD feedback.
- **CLI flags** — `--help`, `--version`, `--difficulty`, `--enemies`, and `--seed` for full control.
- **38 unit tests** — Comprehensive test suite covering world generation, enemy spawning, supply crates, data classes, difficulty presets, CLI parsing, and helper functions.

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
| `SPACE` | Fire active sonar ping (reveals large area, alerts enemies) |
| `E` | Toggle active/passive sonar mode |
| `P` | Passive sonar listening burst (short range, stealthy) |
| `F` | Fire torpedo at nearest classified enemy |
| `G` | Fire torpedo at farthest classified enemy (long-range engage) |
| `Z` | Dive deeper (more protection, less visibility, less noise) |
| `X` | Rise shallower (less protection, more visibility) |
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

## How It Works

The game uses a curses-based terminal renderer with a scrolling viewport centered on your submarine. The ocean world (120×60 tiles) is procedurally generated with random island clusters. Enemy vessels have AI that switches between patrol mode and chase mode based on alert level and noise detection. Sonar pings expand outward as animated rings, revealing any enemy they pass through. The fog of war system ensures you can only see tiles within your current detection radius or illuminated by recent pings. Supply crates spawn at game start and can be collected by moving over them.

## Running Tests

```bash
python3 test_sonar.py
```

38 tests covering world generation, enemy spawning, supply crates, data classes, difficulty presets, CLI parsing, helper functions, and config consistency.

## License

MIT