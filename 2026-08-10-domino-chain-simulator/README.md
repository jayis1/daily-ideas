# 🁫 Domino Chain Simulator

A terminal-based domino chain reaction simulator written in pure Python. Set up dominoes with varied heights and spacings, trigger the first one, and watch the cascade ripple across your screen in animated ASCII art.

## Description

This simulator models a row of dominoes as an interconnected physics system. Each domino has a height and spacing from its neighbors. When you push the first domino, it begins to rotate under a simplified gravity model — the angular acceleration grows with `sin(angle)`, just like a real falling object pivoting about its base. When a falling domino leans past ~25°, it contacts its neighbor and transfers momentum with a probability that depends on the gap between them relative to the domino's height. Tight spacing and tall dominoes cascade reliably; wide gaps and short tiles may stall — exactly like real life.

The animation renders each domino as an ASCII block character (`█`) that rotates from vertical to horizontal as it falls, color-coded by state:

- **White** — standing, untouched
- **Cyan → Yellow** — falling (color shifts as the angle grows)
- **Red** — just landed
- **Gray** — settled and inert

A live HUD shows how many dominoes have fallen vs. total, the current frame count, and a progress bar.

## Features

- **Simplified rotational physics** — gravity-driven angular acceleration based on `sin(θ)`
- **Probabilistic momentum transfer** — gap-to-height ratio determines cascade reliability
- **Variable domino configurations** — random heights/spacings, uniform setups, or a hand-crafted demo chain
- **Bidirectional triggering** — push from the left (default) or the right (`--reverse`)
- **Reproducible runs** — `--seed` for deterministic randomness
- **Adjustable frame rate** — `--fps` controls animation speed
- **Color-coded states** — standing, falling, fallen, and settled dominoes are visually distinct
- **Live progress HUD** — domino count, frame counter, and progress bar
- **Zero dependencies** — runs with just Python 3.10+ and a terminal

## Installation

No dependencies required — just Python 3.10 or newer.

```bash
# clone or download this folder, then:
cd 2026-08-10-domino-chain-simulator
```

That's it. No `pip install`, no virtual environment needed.

## How to Run

```bash
python3 domino_chain.py
```

This launches the default demo chain: 20 dominoes with hand-tuned varied heights and spacings, triggered from the left.

### Command-line options

| Flag | Description | Default |
|------|-------------|---------|
| `--random N` | Generate N dominoes with random heights (3–8) and spacings (1–4) | — |
| `--uniform [N]` | Generate N uniform dominoes (default 20) | — |
| `--height H` | Domino height for `--uniform` mode | 6 |
| `--spacing S` | Domino spacing for `--uniform` mode | 2 |
| `--reverse` | Push the chain from the right end | off |
| `--fps F` | Animation frames per second | 24 |
| `--seed S` | Random seed for reproducible runs | — |

## Usage Examples

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
```

## What It Does

1. **Setup phase** — dominoes are placed in a row. Each gets a height (visual length) and spacing (gap to the next one's base).

2. **Trigger** — the first (or last, with `--reverse`) domino is pushed over. It enters the `FALLING` state with an initial angular velocity.

3. **Physics simulation** — on each frame, every falling domino's angle increases based on a gravity-like acceleration. Once a domino leans past 25°, it checks whether it can reach its neighbor. The transfer probability is:

   ```
   P(transfer) = max(0.15, 1.0 - gap / (height × 1.2))
   ```

   Tall dominoes with small gaps almost always continue the chain. Short dominoes with large gaps may fail to knock over the next one, causing the cascade to stop.

4. **Settling** — once a domino reaches 90°, it snaps to horizontal (`FALLEN`), then transitions to `SETTLED` (gray, inert).

5. **Completion** — when all dominoes are either settled or still standing (the chain stalled), the simulation prints a summary and exits.

## How It Works — Physics Notes

The angular acceleration uses the small-angle pendulum analog:

```
α = g · sin(θ) / h
```

where `g` is a scaled gravity constant, `θ` is the current lean angle, and `h` is the domino height. Taller dominoes accelerate more slowly (longer lever arm), creating visual variation in fall timing. An initial constant kick ensures the first domino starts moving immediately rather than sitting at equilibrium.

## License

MIT — do whatever you like.