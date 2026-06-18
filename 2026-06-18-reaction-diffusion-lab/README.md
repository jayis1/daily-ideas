# 🔬 ASCII Reaction-Diffusion Lab

A terminal-based simulator for the **Gray-Scott reaction-diffusion model** — the mathematical system that produces stunning organic patterns like coral growth, cell mitosis, spots, stripes, mazes, and more. All rendered in real-time ASCII art directly in your terminal.

![Reaction-diffusion patterns](https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/Gray-Scott.PNG/600px-Gray-Scott.PNG)

## What Is Reaction-Diffusion?

The Gray-Scott model simulates two virtual chemicals (U and V) that react with each other and diffuse across a 2D surface:

```
dU/dt = Du·∇²U - U·V² + F·(1 - U)
dV/dt = Dv·∇²V + U·V² - (F + k)·V
```

By tweaking the **feed rate** (F) and **kill rate** (k), you get wildly different emergent patterns — from branching coral to pulsating blobs to labyrinthine mazes. This tool lets you explore all of them interactively.

## Features

- **15 built-in presets** — coral, mitosis, spots, stripes, maze, waves, ripples, fingers, solitons, pulsing, bubbles, worms, chaos, flowers, web
- **Real-time interactive mode** — watch patterns evolve live in your terminal
- **Snapshot mode** — render a single frame after N steps (great for scripts/pipes)
- **5 ASCII ramp styles** — standard, blocks (░▒▓█), dots, simple, dense
- **8 color schemes** — fire, ocean, forest, plasma, aurora, heat, ice, mono
- **Interactive controls** — seed new patterns, change presets, tweak parameters live
- **Toroidal boundary** — patterns wrap around edges seamlessly

## Installation

No external dependencies needed — pure Python 3.6+:

```bash
# Clone or download
git clone <repo-url>
cd 2026-06-18-reaction-diffusion-lab

# Make executable (optional)
chmod +x reaction_diffusion.py
```

## Quick Start

```bash
# Interactive mode with default (coral) preset
python3 reaction_diffusion.py

# Start with mitosis pattern
python3 reaction_diffusion.py --preset mitosis

# Ocean-colored spots
python3 reaction_diffusion.py --preset spots --color ocean

# Use Unicode block characters for denser display
python3 reaction_diffusion.py --preset maze --ramp blocks

# Custom grid size
python3 reaction_diffusion.py --width 120 --height 50

# Non-interactive: render a snapshot after 1000 steps
python3 reaction_diffusion.py --snapshot --steps 1000 --preset coral
```

## Interactive Controls

| Key | Action |
|-----|--------|
| `SPACE` | Seed new pattern at center |
| `R` | Seed random patterns across the grid |
| `C` | Clear and restart simulation |
| `P` | Pause / resume |
| `+` / `-` | Speed up / slow down (iterations per frame) |
| `1`-`9`, `0` | Switch between presets |
| `S` | Cycle through color schemes |
| `D` | Cycle through ASCII ramp styles |
| `F` / `B` | Increase / decrease feed rate |
| `K` / `L` | Decrease / increase kill rate |
| `H` / `?` | Show help |
| `Q` / `Esc` | Quit |

## Presets

| # | Preset | F | k | Description |
|---|--------|-----|------|-------------|
| 1 | coral | 0.0545 | 0.062 | Branching coral growth |
| 2 | mitosis | 0.028 | 0.062 | Cell-like splitting patterns |
| 3 | spots | 0.030 | 0.062 | Stable spot formation |
| 4 | stripes | 0.040 | 0.060 | Worm-like stripe patterns |
| 5 | maze | 0.029 | 0.057 | Labyrinthine maze structures |
| 6 | waves | 0.014 | 0.045 | Oscillating wave patterns |
| 7 | ripples | 0.018 | 0.051 | Expanding ripple rings |
| 8 | fingers | 0.050 | 0.064 | Finger-like protrusions |
| 9 | solitons | 0.030 | 0.057 | Isolated moving spots |
| 0 | pulsing | 0.025 | 0.050 | Pulsating organic clusters |

## Advanced Usage

### Custom Parameters

Fine-tune the reaction parameters to discover your own patterns:

```bash
# Custom F and k values — explore the parameter space!
python3 reaction_diffusion.py --preset custom --feed 0.035 --kill 0.065

# Adjust diffusion rates
python3 reaction_diffusion.py --preset custom --feed 0.04 --kill 0.06 --du 0.20 --dv 0.06
```

### Snapshot Mode for Scripting

```bash
# Generate a snapshot and save to file
python3 reaction_diffusion.py --snapshot --steps 2000 --preset mitosis > output.txt

# Quick preset exploration
for preset in coral mitosis spots stripes maze; do
    echo "=== $preset ==="
    python3 reaction_diffusion.py --snapshot --steps 800 --preset $preset --mono
    echo
done
```

## The Science Behind It

The Gray-Scott model is a two-variable reaction-diffusion system:

- **U** (the substrate) is continuously fed into the system at rate **F**
- **V** (the activator) is continuously removed at rate **k**
- V consumes U in an autocatalytic reaction: U + 2V → 3V
- Both chemicals diffuse across the surface, U faster than V (Du > Dv)

The interplay between reaction and diffusion creates **Turing patterns** — the same mechanism believed to create patterns on animal coats, tropical fish, and seashells. Alan Turing first described this principle in his 1952 paper "The Chemical Basis of Morphogenesis."

The parameter space (F, k) contains distinct regions that produce qualitatively different pattern classes. Small changes in F or k can push the system from stable spots to branching coral to chaotic mixing — making it an endlessly fascinating system to explore.

## Performance Tips

- Smaller grids (e.g., `--width 60 --height 30`) update faster
- Use `--iters 1` for precise control or `--iters 8` for fast evolution
- The simulation uses a simple explicit Euler method; for larger grids, consider reducing the step count per frame
- Snapshot mode with `--mono` is fastest for batch generation

## License

MIT License — explore, modify, and share freely!