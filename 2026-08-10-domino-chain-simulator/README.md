# 🁫 Domino Chain Simulator

A terminal-based domino chain reaction simulator written in pure Python. Set up dominoes with varied heights and spacings, trigger any domino, and watch the cascade ripple across your screen in animated ASCII art.

## Description

This simulator models a row of dominoes as an interconnected physics system. Each domino has a height and spacing from its neighbors. When you push a domino, it begins to rotate under a simplified gravity model — the angular acceleration grows with `sin(angle)`, just like a real falling object pivoting about its base. When a falling domino leans past ~25°, it contacts its neighbor and transfers momentum with a probability that depends on the gap between them relative to the domino's height. Tight spacing and tall dominoes cascade reliably; wide gaps and short tiles may stall — exactly like real life.

The animation renders each domino as an ASCII block character (`█`) that rotates from vertical to horizontal as it falls, color-coded by state:

- **White** — standing, untouched
- **Cyan → Yellow** — falling (color shifts as the angle grows)
- **Red** — just landed
- **Gray** — settled and inert

A live HUD shows how many dominoes have fallen vs. total, the current frame count, and a progress bar.

## Features

### Physics & Simulation
- **Simplified rotational physics** — gravity-driven angular acceleration based on `sin(θ)`
- **Probabilistic momentum transfer** — gap-to-height ratio determines cascade reliability
- **Variable domino configurations** — random heights/spacings, uniform setups, or a hand-crafted demo chain
- **Bidirectional triggering** — push from the left (default), the right (`--reverse`), or any domino (`--trigger N`)
- **Reproducible runs** — `--seed` for deterministic randomness
- **Adjustable frame rate** — `--fps` controls animation speed
- **FALLEN linger** — dominoes briefly stay red before settling for better visual feedback

### Visualization
- **Color-coded states** — standing, falling, fallen, and settled dominoes are visually distinct
- **Live progress HUD** — domino count, frame counter, and progress bar
- **No-color mode** — `--no-color` disables all ANSI escape codes for accessibility or piping
- **Sound mode** — `--sound` emits a terminal bell each time a domino topples

### Scripting & CI
- **Headless mode** — `--no-anim` skips all rendering and just runs physics to completion
- **Statistics report** — `--stats` prints a post-run summary (total, fell, standing, frames)
- **Version flag** — `--version` prints the version and exits
- **Input validation** — invalid arguments (negative counts, bad fps, etc.) are caught with clear error messages

### Quality
- **Zero dependencies** — runs with just Python 3.10+ and a terminal
- **Comprehensive test suite** — 35 tests / 176 assertions, run with `python3 test_domino_chain.py`
- **Type hints** — full type annotations throughout

## Installation

No dependencies required — just Python 3.10 or newer.

```bash
# clone or download this folder, then:
cd 2026-08-10-domino-chain-simulator
```

That's it. No `pip install`, no virtual environment needed.

## How to Run

```bash
# Animated demo (20 hand-crafted dominoes, left trigger)
python3 domino_chain.py

# Run the test suite
python3 test_domino_chain.py
```

### Command-line options

| Flag | Description | Default |
|------|-------------|---------|
| `--random N` | Generate N dominoes with random heights (3–8) and spacings (1–4) | — |
| `--uniform [N]` | Generate N uniform dominoes (default 20) | — |
| `--height H` | Domino height for `--uniform` mode | 6 |
| `--spacing S` | Domino spacing for `--uniform` mode | 2 |
| `--reverse` | Push the chain from the right end | off |
| `--trigger IDX` | Trigger domino at index IDX (0-based) instead of an end | — |
| `--fps F` | Animation frames per second | 24 |
| `--seed S` | Random seed for reproducible runs | — |
| `--no-color` | Disable ANSI color codes | off |
| `--sound` | Emit terminal bell on each fall | off |
| `--no-anim` | Skip animation; run physics headless and exit | off |
| `--stats` | Print a statistics report after the simulation | off |
| `--version` | Print version and exit | — |
| `--help` | Show help and exit | — |

## Usage Examples

### Animated runs

```bash
# Default demo chain (20 hand-crafted dominoes, left trigger)
python3 domino_chain.py

# 30 random dominoes with a fixed seed
python3 domino_chain.py --random 30 --seed 99

# 25 uniform dominoes, height 5, spacing 1 (tight = guaranteed cascade)
python3 domino_chain.py --uniform 25 --height 5 --spacing 1

# Push 40 random dominoes from the right end, faster animation
python3 domino_chain.py --random 40 --reverse --fps 40 --seed 7

# Sparse dominoes — some chains will stall partway!
python3 domino_chain.py --uniform 20 --height 4 --spacing 4 --seed 3

# Trigger a domino in the middle of the chain
python3 domino_chain.py --uniform 10 --trigger 5

# Accessible / pipeable output without color codes
python3 domino_chain.py --no-color --random 15 --seed 1
```

### Headless / scripting

```bash
# Run without animation, just print stats
python3 domino_chain.py --no-anim --stats --random 30 --seed 42

# Sparse chain — see how many actually fall
python3 domino_chain.py --no-anim --stats --uniform 20 --height 3 --spacing 4 --seed 3

# Mid-chain trigger, headless
python3 domino_chain.py --no-anim --stats --uniform 10 --trigger 5

# Check version
python3 domino_chain.py --version
```

### Running tests

```bash
python3 test_domino_chain.py
```

Expected output:

```
Running 35 tests for domino_chain v1.1.0...

==================================================
  Passed: 176   Failed: 0
==================================================
```

## What It Does

1. **Setup phase** — dominoes are placed in a row. Each gets a height (visual length) and spacing (gap to the next one's base).

2. **Trigger** — the first (or last, with `--reverse`, or any index with `--trigger N`) domino is pushed over. It enters the `FALLING` state with an initial angular velocity. If the trigger index is out of range, a warning is printed and nothing is pushed.

3. **Physics simulation** — on each frame, every falling domino's angle increases based on a gravity-like acceleration. Once a domino leans past 25°, it checks whether it can reach its neighbor. The transfer probability is:

   ```
   P(transfer) = max(0.15, 1.0 - gap / (height × 1.2))
   ```

   Tall dominoes with small gaps almost always continue the chain. Short dominoes with large gaps may fail to knock over the next one, causing the cascade to stop.

4. **Settling** — once a domino reaches 90°, it snaps to horizontal (`FALLEN`, shown red), lingers briefly for visual feedback, then transitions to `SETTLED` (gray, inert).

5. **Completion** — when all dominoes are either settled or still standing (the chain stalled), the simulation prints a summary and exits. If `--stats` was passed, a detailed statistics report is printed.

## How It Works — Physics Notes

The angular acceleration uses the small-angle pendulum analog:

```
α = g · sin(θ) / h
```

where `g` is a scaled gravity constant, `θ` is the current lean angle, and `h` is the domino height. Taller dominoes accelerate more slowly (longer lever arm), creating visual variation in fall timing. An initial constant kick ensures the first domino starts moving immediately rather than sitting at equilibrium.

## Version

v1.1.0 — adds headless mode, stats report, arbitrary trigger index, no-color mode, sound option, input validation, FALLEN linger, `--version` flag, and a 35-test suite.

## License

MIT — do whatever you like.