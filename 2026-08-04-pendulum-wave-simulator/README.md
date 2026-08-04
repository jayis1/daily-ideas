# 🕸️ Terminal Pendulum Wave Simulator

A physics-based ASCII animation of the **pendulum wave** — one of the most
mesmerizing demonstrations in classical mechanics.

A row of pendulums, each with a carefully chosen length, swings from a common
pivot. Because each pendulum has a slightly different period, the bobs drift
in and out of phase, creating travelling waves, snake-like patterns, brief
chaos, and then a perfect resynchronization. Then the whole cycle repeats.

```
╭─ t =   0.00s ─────────────────────┬──────────────────────────────────╮
                                      ││
                                        ││
                                          ││
                                            ││
                                              ││
                                                ││
                                                 │││
                                                   │││
                                                     │││
                                                       │││
                                                         │││
                                                           ●││
                                                            ●●●│
                                                               ●●│
                                                                 ●●│
                                                                   ●││
                                                                    ● ●
```

## The Physics

Each pendulum *i* has a period `T_i = 2π√(L_i / g)`. The lengths are chosen
so that the longest pendulum completes exactly **N** full oscillations in the
resync cycle time, the next completes **N+1**, the next **N+2**, and so on.

The result: after the cycle time, every pendulum has completed a whole number
of swings and they all realign — a beautiful emergent pattern from simple
harmonic motion.

The simulator derives the true cycle time from the longest pendulum's length:

```
cycle = N × 2π × √(L_max / g)
```

so the physics is always exact, regardless of the parameters you choose.

## Features

- **Real-time ASCII animation** with 24-bit true-colour bobs
- **Trail rendering** — each bob leaves a fading trail that reveals the
  wave pattern (snake, travelling wave, chaos, resync)
- **Four visualization modes**:
  1. Strings + bobs + trail (default)
  2. Trail only — pure wave pattern
  3. Strings + bobs (no trail)
  4. Bobs only
- **Interactive controls** — pause, speed up/down, toggle trail, switch modes
- **Static frame mode** — render individual frames for screenshots or CI
- **Physics info mode** — print a table of lengths, periods, and swing counts
- **Resizes automatically** when the terminal size changes
- **No external dependencies** — pure Python standard library

## Installation

No dependencies required — just Python 3.8+.

```bash
git clone https://github.com/<user>/daily-ideas.git
cd daily-ideas/2026-08-04-pendulum-wave-simulator
```

## How to Run

### Animated (interactive)

```bash
python3 pendulum_wave.py
```

Default: 16 pendulums, longest = 50 cm, 51 swings per cycle (~72 s cycle).

### Custom parameters

```bash
# 24 pendulums, longest = 80 cm, 40 swings per cycle
python3 pendulum_wave.py -n 24 -L 0.80 -s 40

# Larger amplitude (20°) for more dramatic spread
python3 pendulum_wave.py -a 20

# Faster animation
python3 pendulum_wave.py --fps 60
```

### Single frame (for screenshots / non-interactive)

```bash
# Render the scene at t = 15 seconds
python3 pendulum_wave.py --frame 15.0 --width 80 --height 24
```

### Series of static frames

```bash
# Print 8 frames evenly spaced across one full cycle
python3 pendulum_wave.py --static --frames 8
```

### Physics info only

```bash
python3 pendulum_wave.py --info -n 16
```

Output:
```
Pendulum Wave — 16 pendulums
Longest pendulum: 50.00 cm  (period 1.4187 s)
Resync cycle: 72.36 s  (longest swings 51×)
  #  length(cm)  period(s)   swings
--------------------------------------
  0       50.00     1.4187       51
  1       48.10     1.3915       52
  2       46.30     1.3652       53
  ...
 15       38.66     1.2475       66

After 72.36s all pendulums realign.
```

## Interactive Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause / resume |
| `T` | Toggle trail on/off |
| `R` | Reduced-motion mode (disables trail) |
| `+` / `=` | Speed up (up to 8×) |
| `-` / `_` | Slow down (down to 0.1×) |
| `1`–`4` | Switch visualization mode |
| `Q` / `Esc` | Quit |

## Usage Examples

### Watch a 60-pendulum wave

```bash
python3 pendulum_wave.py -n 60 -L 1.0 -s 30 -a 8
```

With 60 pendulums you get a very dense, smooth wave. The 8° amplitude keeps
the bobs from overlapping too much.

### Trail-only mode (pure wave art)

```bash
python3 pendulum_wave.py -n 32 --mode 2
```

Mode 2 shows only the fading trails — the bobs themselves are hidden,
revealing the travelling-wave pattern as a flowing ribbon of colour.

### Screenshot a specific moment

```bash
python3 pendulum_wave.py --frame 36.18 --mode 1 --width 100 --height 30
```

## Running the Tests

```bash
python3 test_pendulum_wave.py
```

Tests verify:
- Correct pendulum count
- Periods and lengths decrease monotonically
- Period formula `T = 2π√(L/g)` is exact
- All pendulums resynchronize at the derived cycle time
- Angle stays within amplitude bounds
- Half-period produces the opposite extreme
- Static rendering produces valid output in all four modes

## How It Works

1. **Pendulum construction** — `build_pendulums()` computes lengths from the
   desired swing counts using `L = g(T/2π)²`, anchored to the longest pendulum.

2. **Physics** — each pendulum's angle at time *t* is
   `θ(t) = A·cos(ωt)` where `ω = 2π/T` (small-angle approximation).

3. **Rendering** — physical `(x, y)` coordinates are mapped to terminal
   `(col, row)`. Strings are drawn with Bresenham line interpolation. Trails
   are stored as a ring buffer of recent positions, rendered with a gradient
   of characters (` .·:-=+*#%@`) and fading colours.

4. **Input** — a minimal raw-mode reader sets stdin to non-blocking, allowing
   single-key input without blocking the animation loop.

## File Overview

| File | Description |
|------|-------------|
| `pendulum_wave.py` | Main simulator (physics, renderer, CLI, animation loop) |
| `test_pendulum_wave.py` | Test suite (run with `python3 test_pendulum_wave.py`) |

## License

MIT — do whatever you like.