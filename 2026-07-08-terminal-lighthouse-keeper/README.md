# 🏠 Terminal Lighthouse Keeper

A meditative ASCII resource management game where you keep a lighthouse burning through the night. Manage your fuel, maintain the lens, cool the engine, and rescue ships in distress — all from your terminal.

## Description

The sun has set. You are the lighthouse keeper, responsible for guiding ships safely through the darkness. Storms roll in, the engine overheats, the lens cracks, and ships cry for help. Your job: keep the light burning until dawn.

This is a real-time terminal game built with `curses`. Watch the moon traverse the sky, see waves crash against the shore, and feel the tension as fuel runs low and a storm bears down on you.

## Features

- **Dynamic weather system** — Clear skies, rain, and storms that affect fuel consumption and lens health
- **Animated ASCII seascape** — Waves, moon phases, stars, and rain rendered in real-time
- **Resource management** — Balance fuel, lens health, engine temperature, and beam intensity
- **Ship rescue** — Spot distressed ships and signal them to safety for bonus points
- **Random events** — Supply crates wash ashore, lens cracks appear, engines surge
- **Scoring system** — Points for ships saved, fuel remaining, lens health, and engine management
- **Full night cycle** — Survive from 6 PM to 6 AM with an accelerated clock

## How to Install

No external dependencies needed — just Python 3.6+ with the standard library (curses is included on most systems).

```bash
# Clone or copy the project
cd ~/daily-ideas/2026-07-08-terminal-lighthouse-keeper
```

**Note for macOS users:** You may need to install a curses wrapper:
```bash
pip install windows-curses  # Windows
# macOS and Linux should work out of the box
```

## How to Run

```bash
python3 lighthouse.py
```

## Controls

| Key | Action |
|-----|--------|
| `B` | Toggle the lighthouse beam on/off |
| `R` | Refuel (costs 5 minutes of game time, restores 15-30% fuel) |
| `F` | Fix the lens (costs 3 minutes, restores 10-25% lens health) |
| `C` | Cool the engine (costs 2 minutes, reduces engine temp by 15-30°) |
| `S` | Signal a distressed ship to guide it to safety (+200 points) |
| `Q` | Quit the game |

## Gameplay Tips

- **Keep fuel above 15%** — You'll get a warning, and if it hits 0, the light goes out!
- **Watch engine temperature** — If it hits 100°, the engine shuts down and the beam turns off
- **Lens health affects beam intensity** — A cracked lens means a dimmer beam
- **Turn off the beam strategically** — Saves fuel but risks losing ships
- **Rescue distress ships quickly** — They have a timer before they're lost
- **Storms increase fuel consumption** — Stock up on fuel before bad weather
- **Supply crates are rare blessings** — They restore both fuel and lens health

## What It Does

The game simulates a full night (6 PM to 6 AM) as a lighthouse keeper. Each game-minute ticks by in about one second of real time. You manage four interconnected resources:

1. **Fuel** — Depletes over time while the beam is on. Refuel with `R`.
2. **Lens health** — Degrades in storms. Repair with `F`.
3. **Engine temperature** — Rises while the beam is on. Cool it with `C`.
4. **Beam intensity** — Determined by fuel × lens health. Determines how well ships can see you.

Ships sail across the sea — some in distress (marked "SOS!⛵"). Signal them with `S` to rescue them. Your final score depends on ships saved, fuel remaining, lens health, and engine condition at dawn.

Survive the night, keep the light burning, and guide them home. 🏠