# 🎯 Terminal Sonar Simulator

A submarine combat game played entirely in the terminal, where you navigate a fog-of-war ocean using sonar pings to detect, classify, and destroy hidden enemy vessels — while trying not to give away your own position.

## Description

You command a submarine in an ocean filled with enemy vessels. The ocean is cloaked in fog of war — you can only see what your sonar reveals. Fire active sonar pings to illuminate large areas, but beware: every ping also tells enemies where you are. Switch to passive sonar mode for stealth, but with dramatically reduced detection range. Manage your depth, conserve torpedoes, and hunt down all enemy ships before they find and sink you.

## Features

- **Fog of War** — The ocean is dark. You only see what your sonar reveals
- **Active & Passive Sonar** — Trade off between detection power and stealth
- **Depth System** — Dive deep for protection but lose visibility; rise to periscope depth for better intel
- **3 Enemy Types** — Destroyers (tough), Submarines (deadly), Patrol Boats (fast)
- **Enemy AI** — Enemies patrol, get alerted by your pings, chase you, and fire torpedoes back
- **Torpedo Combat** — Fire torpedoes at classified targets; manage your limited ammo
- **Procedural World** — Randomly generated island archipelagos each game
- **Minimap** — Toggle a strategic overview showing classified enemy positions
- **Particle Effects** — Explosions, torpedo trails, and sonar ring animations
- **Health & Ammo Management** — Slowly resupply torpedoes over time; heal at deep depth
- **Scoring** — Points for each kill, bonus for victory

## How to Install

Requires Python 3.6+ with standard library only (uses `curses`):

```bash
# No dependencies needed — just clone and run
git clone <repo-url>
cd 2026-07-03-terminal-sonar-simulator
```

On some Linux systems, you may need to install `curses`:
```bash
pip install windows-curses  # Windows only
# Linux/macOS: curses comes with Python by default
```

## How to Run

```bash
python3 sonar.py
```

Make sure your terminal is at least 80x28 characters for the best experience.

## Controls

| Key | Action |
|-----|--------|
| `W/A/S/D` or Arrow Keys | Move submarine |
| `SPACE` | Fire active sonar ping (reveals large area, alerts enemies) |
| `E` | Toggle active/passive sonar mode |
| `P` | Passive sonar listening burst (short range, stealthy) |
| `F` | Fire torpedo at nearest classified enemy |
| `Z` | Dive deeper (more protection, less visibility) |
| `X` | Rise shallower (less protection, more visibility) |
| `M` | Toggle minimap |
| `Q` | Quit |

## Strategy Tips

- **Active pings are loud** — enemies within range will detect you and start hunting
- **Use passive mode** to sneak around without revealing yourself, but your vision is limited
- **Depth matters** — at deep depth you take less torpedo damage, but you can barely see
- **Classify before firing** — you can only lock torpedoes onto classified (detected) targets
- **Watch your ammo** — torpedoes slowly resupply, but you only carry 8 at a time
- **Use islands as cover** — torpedoes and sonar can't pass through land

## How It Works

The game uses a curses-based terminal renderer with a scrolling viewport centered on your submarine. The ocean world (120×60 tiles) is procedurally generated with random island clusters. Enemy vessels have AI that switches between patrol mode and chase mode based on alert level. Sonar pings expand outward as animated rings, revealing any enemy they pass through. The fog of war system ensures you can only see tiles within your current detection radius or illuminated by recent pings.

## Game Objects

| Symbol | Object |
|--------|--------|
| `▲` | Your submarine |
| `D` | Enemy Destroyer (HP: 3) |
| `S` | Enemy Submarine (HP: 2) |
| `P` | Enemy Patrol Boat (HP: 1) |
| `█` | Island/land |
| `░` | Shallow water |
| `~` | Deep water |
| `○` | Sonar ping ring |
| `▸` | Friendly torpedo |
| `◃` | Enemy torpedo |

## License

MIT