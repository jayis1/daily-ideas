# 🌊 Water Ripple Simulator

A real-time 2D wave equation simulator rendered in the terminal using Unicode block characters and 24-bit ANSI colors. Drop stones, place wave sources, build wall obstacles, and watch waves propagate, interfere, and reflect — all from the comfort of your terminal.

## What It Does

The simulator models the **discrete 2D wave equation** on a grid:

```
u(t+1) = (2·u(t) - u(t-1) + c²·∇²u(t)) · damping
```

Each frame, every cell computes a Laplacian from its four neighbours, propagating disturbances outward at speed `c`. The damping factor slowly attenuates waves, simulating energy loss. Walls act as **reflective boundaries**, causing waves to bounce back and create interference patterns. Continuous wave sources emit periodic pulses, producing classic two-slit interference and standing wave patterns.

## Features

### Physics & Simulation
- **Realistic wave physics** — proper discrete wave equation with configurable speed and damping
- **Reflective walls** — waves bounce off obstacles, creating interference patterns
- **Continuous wave sources** — place persistent oscillating sources that emit pulses automatically
- **Double-slit interference** — built-in preset for the classic physics demonstration
- **Adjustable damping** — press `+`/`-` to tune wave persistence in real time
- **Adjustable simulation speed** — press `[`/`]` to slow down or speed up the simulation

### Interactive Controls
- **Drop stones** — press `SPACE` for a random drop, or any letter key (`A`–`Z`) for a grid-mapped position
- **Big drops** (`D`) — create large-amplitude disturbances
- **Interference demo** (`I`) — drop two symmetric stones for a classic interference pattern
- **Rain mode** (`R`) — automatic random drops for ambient wave patterns
- **Wall placement** (`W`) — add random wall segments that reflect waves
- **Preset wall patterns** (`P`) — cycle through rectangle, diamond, cross, circle, and double-slit presets
- **Wave sources** (`F`) — place/remove continuous oscillating wave sources
- **Color cycling** (`T`) — toggle animated color cycling mode

### Visuals
- **5 colour palettes** — Ocean, Lava, Toxic, Purple, Monochrome (keys `1`–`5`)
- **Color cycling mode** — smooth animated palette transitions
- **Wall rendering** — textured brick-pattern obstacle display
- **Source markers** — yellow indicators showing active wave sources
- **HUD display** — shows drop count, palette, damping, rain mode, sources, speed, wall preset, frame number

### CLI Options
- **`--cols N`** — set grid width (default: 72)
- **`--rows N`** — set grid height (default: 28)
- **`--fps N`** — target frames per second (default: 20)
- **`--palette N`** — initial colour palette 1–5 (default: 1)
- **`--speed C`** — wave propagation speed (default: 0.45)
- **`--damping D`** — wave damping factor (default: 0.96)
- **`--rain`** — start with rain mode enabled
- **`--version`** — show version number
- **`--help`** — show usage information

## How to Install

No external dependencies — uses only Python 3 standard library modules (`sys`, `time`, `random`, `math`, `argparse`, `select`, `tty`, `termios`).

```bash
# No installation needed, just run it
python3 ripple.py
```

> **Note:** For the best experience, run in a terminal that supports 24-bit ANSI color (most modern terminals do: iTerm2, Windows Terminal, Kitty, Alacritty, etc.).

## How to Run

```bash
cd ~/daily-ideas/2026-06-20-water-ripple-simulator
python3 ripple.py
```

### Run with Options

```bash
# Start with a wider grid and rain mode
python3 ripple.py --cols 100 --rows 35 --rain

# Start with the Lava palette
python3 ripple.py --palette 2

# Slower wave speed for more dramatic visuals
python3 ripple.py --speed 0.3 --damping 0.98
```

### Run Tests

```bash
python3 test_ripple.py
```

Press `Q` or `Escape` to quit.

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Drop a stone at a random position |
| `D` | Drop a big stone |
| `F` | Place/remove a continuous wave source |
| `I` | Interference demo (two symmetric drops) |
| `R` | Toggle rain mode (auto-drops) |
| `P` | Cycle preset wall patterns |
| `T` | Toggle color-cycling mode |
| `W` | Add a random wall segment |
| `C` | Clear all walls |
| `X` | Reset water (clear simulation) |
| `+` / `-` | Increase / decrease damping |
| `[` / `]` | Decrease / increase simulation speed |
| `1`–`5` | Switch colour palette |
| `Q` / `Esc` | Quit |

Any letter key (`A`–`Z`) drops a stone at a position mapped to that letter on the grid.

## How It Works

1. **Wave Equation**: Each cell's next value is computed from its current value, previous value, and the Laplacian (sum of 4 neighbours minus 4× self). This is the standard finite-difference scheme for the 2D wave equation.

2. **Damping**: A per-frame multiplicative damping factor (default 0.96) gradually reduces amplitude, simulating viscous energy loss. Lower damping = faster decay; higher = longer-lasting waves.

3. **Walls**: Marked cells are held at zero amplitude. Waves reflect off walls because the zero boundary condition acts like a fixed endpoint, inverting the wave on reflection.

4. **Wave Sources**: Continuous sources emit a small drop every few frames, creating persistent oscillation patterns. Toggle them with `F`.

5. **Rendering**: Wave height is mapped to 10 intensity levels (0–9), each assigned a color from the active palette. Unicode block characters provide visual density: ` ` (empty) through `█` (full block).

## Examples

```bash
# Start the simulator (drops one stone in the center automatically)
python3 ripple.py

# Double-slit interference demo
python3 ripple.py --palette 2
# Then press P until "Wall: double_slit" appears, then press I

# Ambient rain with color cycling
python3 ripple.py --rain --palette 3
# Then press T for color cycling

# Run the test suite
python3 test_ripple.py
```

Try enabling rain mode (`R`), adding wave sources (`F`), and cycling wall presets (`P`) for the most visually interesting patterns!

## License

MIT