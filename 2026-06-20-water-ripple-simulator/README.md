# 🌊 Water Ripple Simulator

A real-time 2D wave equation simulator rendered in the terminal using Unicode block characters and 24-bit ANSI colors. Drop stones, watch waves propagate, interfere, and reflect off walls — all from the comfort of your terminal.

## What It Does

The simulator models the **discrete 2D wave equation** on a grid:

```
u(t+1) = (2·u(t) - u(t-1) + c²·∇²u(t)) · damping
```

Each frame, every cell computes a Laplacian from its four neighbours, propagating disturbances outward at speed `c`. The damping factor slowly attenuates waves, simulating energy loss. Walls act as **reflective boundaries**, causing waves to bounce back and creating beautiful interference patterns.

The result is rendered as a colour-coded heightmap using Unicode block characters (` ░▒▓█`) with five selectable colour palettes.

## Features

- **Realistic wave physics** — proper discrete wave equation with configurable speed and damping
- **Interactive drops** — press any letter key to drop a stone at a mapped grid position, or SPACE for random drops
- **Big drops (D)** — create large-amplitude disturbances
- **Rain mode (R)** — automatic random drops for ambient wave patterns
- **Wall placement (W)** — add obstacles that reflect waves, creating interference
- **Clear walls (C)** / **Clear water (X)** — reset simulation state
- **5 colour palettes** — Ocean, Lava, Toxic, Purple, Monochrome (keys 1–5)
- **Adjustable damping** — press `+`/`-` to tune wave persistence
- **HUD display** — shows drop count, palette, damping, rain mode, frame number

## How to Install

No external dependencies — uses only Python 3 standard library modules (`sys`, `time`, `random`, `math`, `select`, `tty`, `termios`).

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

Press `Q` or `Escape` to quit.

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Drop a stone at a random position |
| `D` | Drop a big stone |
| `R` | Toggle rain mode (auto-drops) |
| `W` | Add a random wall segment |
| `C` | Clear all walls |
| `X` | Reset water (clear simulation) |
| `+` / `-` | Increase / decrease damping |
| `1`–`5` | Switch colour palette |
| `Q` / `Esc` | Quit |

Any letter key (`A`–`Z`) drops a stone at a position mapped to that letter on the grid.

## How It Works

1. **Wave Equation**: Each cell's next value is computed from its current value, previous value, and the Laplacian (sum of 4 neighbours minus 4× self). This is the standard finite-difference scheme for the 2D wave equation.

2. **Damping**: A per-frame multiplicative damping factor (default 0.96) gradually reduces amplitude, simulating viscous energy loss. Lower damping = faster decay; higher = longer-lasting waves.

3. **Walls**: Marked cells are held at zero amplitude. Waves reflect off walls because the zero boundary condition acts like a fixed endpoint, inverting the wave on reflection.

4. **Rendering**: Wave height is mapped to 10 intensity levels (0–9), each assigned a color from the active palette. Unicode block characters provide visual density: ` ` (empty) through `█` (full block).

## Examples

```
# Start the simulator (drops one stone in the center automatically)
python3 ripple.py

# Run the self-test
python3 test_ripple.py
```

Try enabling rain mode (`R`) and adding some walls (`W`) for the most visually interesting interference patterns!

## License

MIT