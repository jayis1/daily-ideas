# 🎆 Terminal ASCII Fireworks Simulator

A real-time fireworks display in your terminal with particle physics, multiple explosion patterns, and choreographed shows. Watch rockets launch, explode into dazzling patterns, and cascade with trails — all rendered in colorful ASCII.

## Features

- **8 Firework Types**: Peony, Chrysanthemum, Willow, Palm, Crossette (secondary explosions!), Ring, Heart, and Spiral
- **Particle Physics**: Gravity, drag, and trails create realistic cascading effects
- **Choreographed Auto Show**: 5-phase auto show with varied patterns — single shots, rapid fire, grand finales, synchronized lines, and themed shapes
- **Interactive Mode**: Launch specific firework types with number keys, trigger grand finales with `f`
- **10 Color Palettes**: Warm, Cool, Pink, Golden, Emerald, Fire, Ice, Nebula, Sunset, Blossom
- **Flash Effects**: Bright flash at explosion center
- **Trail Rendering**: Particles leave fading trails for visual persistence
- **Live HUD**: Shows particle count and total fireworks launched

## How to Install

```bash
# No external dependencies needed — uses only Python standard library (curses)
cd ~/daily-ideas/2026-06-15-ascii-fireworks
```

Requires Python 3.7+ with `curses` (included on most Unix systems). On some Linux distros:
```bash
sudo apt-get install python3-curses  # only if missing
```

## How to Run

```bash
python3 fireworks.py
```

> **Note**: Must be run in a real terminal (not an IDE output pane). Works best in a terminal with color support.

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Launch a random firework |
| `A` | Toggle auto/manual show mode |
| `1` | Launch Peony |
| `2` | Launch Chrysanthemum |
| `3` | Launch Willow |
| `4` | Launch Palm |
| `5` | Launch Crossette |
| `6` | Launch Ring |
| `7` | Launch Heart |
| `8` | Launch Spiral |
| `F` | Grand finale — burst of 5-10 simultaneous rockets |
| `Q` | Quit |

## Usage Examples

```bash
# Start the auto show (default mode)
python3 fireworks.py

# The show starts automatically with choreographed phases
# Press SPACE to manually launch extra fireworks
# Press F for a grand finale burst
# Press A to switch to manual mode (no auto-launches)
```

## How It Works

- **Rockets** launch from the bottom of the terminal and ascend toward a target height
- On reaching the target, they **explode** into particles based on their type
- Each **particle** follows realistic physics: gravity pulls it down, drag slows it, and trails record its path
- **Crossette** fireworks create secondary mini-explosions when their particles fade
- **Heart** and **Ring** types use parametric equations to shape the explosion
- **Spiral** types add angular momentum for a swirling effect
- The auto show cycles through 5 phases with varying cadence and firework selections