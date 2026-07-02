# 🚂 ASCII Train Simulator

A terminal-based side-scrolling steam locomotive simulator. Drive your train through procedurally generated terrain, managing speed, coal, water, and steam pressure while stopping at stations, obeying signals, and delivering passengers.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Terminal-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Steam locomotive physics** — realistic throttle, brake, steam pressure, coal, and water management
- **Procedurally generated world** — every run produces unique terrain with hills, tunnels, bridges, water crossings, and stations
- **Named stations** — procedurally generated British-style station names (e.g., "Upperbridgeville", "Oldhampton")
- **Signal system** — green, yellow, and red signals that affect your score if violated
- **Passenger delivery** — pick up passengers at stations and deliver them to earn points
- **Smoke particle effects** — dynamic smoke from the locomotive that drifts in the wind
- **Wheel animation** — spinning wheels that speed matches the train's velocity
- **Whistle** — blow the horn with SPACE and see the animation
- **Derailment mechanic** — apply heavy brakes at high speed and you'll derail!
- **Score tracking** — earn points for distance, stations visited, and passengers delivered
- **Emergency brake** — hit B for immediate full braking

## How to Install

```bash
# No dependencies beyond Python's standard library!
# Just clone and run:
git clone <repo-url>
cd 2026-07-02-ascii-train-simulator
```

Requires Python 3.8+ with the `curses` module (included on most systems; on Windows, install `windows-curses`).

## How to Run

```bash
python3 train_simulator.py
```

## Controls

| Key | Action |
|-----|--------|
| `↑` / `W` | Increase throttle (0–8) |
| `↓` / `S` | Decrease throttle |
| `←` / `A` | Apply brakes (incremental) |
| `→` / `D` | Release brakes (incremental) |
| `C` | Stoke coal (+15%) |
| `F` | Fill water tank (at stations only, +25%) |
| `SPACE` | Sound whistle 🎶 |
| `B` | Emergency brake (full stop) |
| `R` | Restart (after derailment) |
| `Q` / `ESC` | Quit |

## How It Works

### Physics Model

- **Throttle** (0–8) controls how much steam drives the wheels
- **Steam pressure** builds when coal is burning and throttle is open; higher pressure = more force
- **Coal** is consumed proportionally to throttle level — press `C` to stoke more
- **Water** is consumed by steam production — refill at stations with `F`
- **Speed** is affected by throttle force, braking, friction, and terrain slope
- **Hills** slow you down going up and speed you up going down
- **Derailment** occurs if you brake hard (>50%) at high speed (>22 mph)

### Scoring

- **1 point** per 2 meters of distance traveled
- **10 points** per station visited
- **5 points** per passenger delivered
- **-50 points** for running a red signal

### World Generation

The world uses deterministic random generation based on position, so every run produces the same terrain for a given seed. You'll encounter:

- **Flat terrain** — smooth sailing
- **Hills** — affect your speed based on grade
- **Bridges** — over water crossings
- **Tunnels** — through mountains
- **Stations** — stop here to board passengers and refill water
- **Signals** — obey them or lose points!

## Usage Examples

```bash
# Run with default random seed
python3 train_simulator.py

# Run the test suite
python3 test_train.py
```

## Tips

1. Start with throttle 3–4 and gradually increase — full throttle burns coal fast
2. Watch your water gauge — running dry kills your steam pressure
3. Slow down for stations! You can only board passengers when nearly stopped
4. Don't slam on the brakes at high speed — you'll derail
5. Blow the whistle whenever you want (SPACE) — it's fun!
6. Refill water at stations with `F` — it's the only place you can