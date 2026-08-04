# 🕸️ Terminal Pendulum Wave Simulator

A physics-based ASCII animation of the **pendulum wave** — one of the most
mesmerizing demonstrations in classical mechanics. Pure Python, zero
dependencies, runs in any terminal.

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
                                                            ●●●
                                                               ●●
                                                                 ●●
                                                                   ●│
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
- **Interactive controls** — pause, speed up/down, toggle trail, switch modes,
  toggle colour
- **Monochrome mode** (`--no-color`) for accessibility or terminals without
  24-bit colour support
- **Pure-ASCII mode** (`--ascii`) for terminals that lack UTF-8 support
- **Snapshot mode** (`--snapshot`) — prints five key frames across one full
  cycle (start, ¼, ½, ¾, resync) for quick visualisation without animation
- **Energy reporting** — `--info` now includes the mechanical energy of each
  pendulum, and the `Pendulum.energy()` / `Pendulum.angular_velocity()`
  methods are available programmatically
- **Static frame mode** — render individual frames for screenshots or CI
- **Physics info mode** — print a table of lengths, periods, swing counts,
  and energy
- **Input validation** — bad parameters produce a clear error instead of a
  crash or silent garbage
- **Resizes automatically** when the terminal size changes
- **`--version` flag** for version checking
- **No external dependencies** — pure Python standard library (3.8+)

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

### Snapshot mode (new)

Prints five key moments of one full cycle — start, quarter, half,
three-quarter, and the final resync — each with a descriptive label.

```bash
python3 pendulum_wave.py --snapshot -n 10
python3 pendulum_wave.py --snapshot --no-color --ascii --width 70 --height 12
```

### Accessibility / restricted terminals

```bash
# Monochrome — no ANSI colour escapes at all
python3 pendulum_wave.py --no-color

# Pure ASCII — uses 'O' for bobs, '|' for strings, '+' for pivots
python3 pendulum_wave.py --ascii

# Both together (maximally portable)
python3 pendulum_wave.py --no-color --ascii
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

  #  length(cm)  period(s)   swings   energy(mJ)
--------------------------------------------------
  0       50.00     1.4187       51     107.5420
  1       48.10     1.3915       52     103.4455
  2       46.30     1.3652       53      99.5787
  ...
 15       38.66     1.2475       66      83.0197

After 72.36s all pendulums realign.
```

### Version

```bash
python3 pendulum_wave.py --version
# pendulum-wave 1.1.0
```

## Interactive Controls

| Key | Action |
|-----|--------|
| `SPACE` | Pause / resume |
| `T` | Toggle trail on/off |
| `C` | Toggle colour on/off |
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

### ASCII-only for a CI log or pipe

```bash
python3 pendulum_wave.py --snapshot --ascii --no-color -n 8 | head -40
```

## Running the Tests

```bash
python3 test_pendulum_wave.py
```

The test suite (23 tests, no external framework required) verifies:

- Correct pendulum count
- Periods and lengths decrease monotonically
- Period formula `T = 2π√(L/g)` is exact
- All pendulums resynchronize at the derived cycle time
- Quarter-cycle alignment of the longest pendulum
- Angle stays within amplitude bounds
- Half-period produces the opposite extreme
- Static rendering produces valid output in all four modes
- Monochrome rendering emits no colour escapes
- ASCII rendering uses `O` / `|` instead of `●` / `│`
- Energy is conserved (time-invariant) for the harmonic model
- Energy formula `E = ½ m g L A²` is exact
- Angular velocity is zero at the extremes and maximal at quarter period
- `--version` flag works
- Input validation rejects bad parameters
- Renderer survives zero-valued max dimensions
- Trails accumulate and are capped at `trail_len`

## How It Works

1. **Pendulum construction** — `build_pendulums()` computes lengths from the
   desired swing counts using `L = g(T/2π)²`, anchored to the longest pendulum.

2. **Physics** — each pendulum's angle at time *t* is
   `θ(t) = A·cos(ωt)` where `ω = 2π/T` (small-angle approximation). The
   angular velocity is `θ̇(t) = -Aω·sin(ωt)`, and the mechanical energy is
   `E = ½ m g L A²` (constant for the harmonic model).

3. **Rendering** — physical `(x, y)` coordinates are mapped to terminal
   `(col, row)`. Strings are drawn with Bresenham line interpolation. Trails
   are stored as a ring buffer of recent positions, rendered with a gradient
   of characters (` .·:-=+*#%@`, or ` .:-=+*#%X` in ASCII mode) and fading
   colours. A `--no-color` flag strips all ANSI colour escapes; `--ascii`
   swaps the Unicode glyph set for a pure-ASCII fallback.

4. **Input** — a minimal raw-mode reader sets stdin to non-blocking, allowing
   single-key input without blocking the animation loop.

## File Overview

| File | Description |
|------|-------------|
| `pendulum_wave.py` | Main simulator (physics, renderer, CLI, animation loop) |
| `test_pendulum_wave.py` | Test suite (run with `python3 test_pendulum_wave.py`) |

## License

MIT — do whatever you like.