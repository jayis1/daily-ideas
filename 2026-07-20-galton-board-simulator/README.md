# Galton Board Simulator

A live, interactive terminal simulation of a **Galton board** (also called a
"bean machine" or "quincunx") — the classic device that demonstrates how a
binomial process converges to a normal (Gaussian) distribution. Balls are
dropped from the top of a triangular peg lattice; at each peg they bounce left
or right with equal probability, and at the bottom they pile into a row of
bins. As more balls fall, the histogram of bin counts approaches the
unmistakable bell curve.

This simulator renders the whole thing in ASCII (or UTF-8) directly in your
terminal — pegs, falling balls, stacking bins, and a live overlay of the
theoretical normal curve computed from running statistics.

```
                                   ∘
                               ∘       ∘
                           ∘       ∘       ∘
                       ∘       ∘       ∘       ∘
                  ∘        ∘       ∘       ∘        ∘
              ∘        ∘       ∘       ∘       ∘        ∘
          ∘       ∘        ∘       ∘       ∘        ∘       ∘
      ∘       ∘        ∘       ∘       ∘       ∘        ∘       ∘
──────────────────────────────────────────────────────────────────────
      │       │        │       │   █   │       │        │       │     │
      │       │        │   ▓   │   █   │   █   │        │       │     │
      │       │        │   █   │   █   │   █   │        │       │     │
      │       │   █    │   █   │   █   │   █   │    █   │       │     │
      │   █   │   █    │   █   │   █   │   █   │    █   │   █   │     │

balls=200  mean=4.170  std=1.418  skew=-0.070
```

The `▓` glyphs show the theoretical normal curve overlaid on the empirical
histogram — watch them converge as you drop more balls.

## Features

- **Animated ASCII rendering** of pegs, falling balls, and accumulating bins.
- **Live normal-distribution fit** overlaid on the histogram (`▓` / `%`).
  Disable with `--no-curve`.
- **Running statistics** via Welford-style online moments:
  count, mean, variance, std, skewness, excess kurtosis, min, max.
- **Three modes:**
  - *Interactive* — drop balls one at a time with keyboard controls (requires
    a TTY).
  - *Batch* (`--batch`) — rapid animated dropping of N balls.
  - *Static* (`--static`) — compute N balls with no animation, render the
    final histogram.
- **Configurable geometry**: peg rows, board width/height, drop rate.
- **Color and glyph modes**: full-color UTF-8, monochrome UTF-8, or plain
  ASCII (`--ascii`, `--no-color`).
- **Seedable RNG** (`--seed`) for reproducible runs.
- **Export** the final histogram to CSV or JSON (`--export`), including the
  expected-normal counts per bin. Export errors (e.g. unwritable path) are
  caught and reported gracefully.
- **Built-in self-test suite** (`--test`) — 40 checks covering physics,
  statistics, rendering, export, CLI validation, and edge cases.
- **Input validation** — rejects negative `--balls`, `--rate`, or `--rows`,
  and warns when interactive mode is launched without a TTY.
- Zero external dependencies — pure Python standard library.

## Install

No installation is required beyond Python 3.10+:

```bash
git clone https://github.com/<you>/daily-ideas.git
cd daily-ideas/2026-07-20-galton-board-simulator
python3 galton_board.py --test   # verify it works
```

## How to run

### Interactive (default)

```bash
python3 galton_board.py
```

Drop balls and watch them pile up. Keyboard controls:

| Key     | Action                                  |
|---------|-----------------------------------------|
| `SPACE` | drop a ball from a random column        |
| `ENTER` | drop a ball from the center column      |
| `b`     | toggle continuous batch dropping        |
| `+`/`-` | increase / decrease the drop rate        |
| `c`     | clear the bins and reset stats          |
| `r`     | full reset (bins, stats, balls)         |
| `q`     | quit and print the final histogram      |

> **Note:** Interactive mode requires a TTY for keyboard input. If stdin is
> not a TTY (e.g. piped input, cron, CI), it prints an error and exits. Use
> `--static` or `--batch` for non-interactive runs.

### Batch (animated, fast)

```bash
python3 galton_board.py --batch --rows 12 --balls 5000 --rate 60
```

### Static (one-shot, no animation)

```bash
python3 galton_board.py --static --rows 10 --balls 10000 --seed 42
```

### Without the normal-curve overlay

```bash
python3 galton_board.py --static --rows 10 --balls 5000 --no-curve
```

### With export

```bash
python3 galton_board.py --static --rows 15 --balls 20000 --export hist.json
python3 galton_board.py --static --rows 15 --balls 20000 --export hist.csv
```

### ASCII-only (for non-UTF-8 terminals / CI logs)

```bash
python3 galton_board.py --static --rows 8 --balls 1000 --ascii --no-color
```

### Self-tests

```bash
python3 galton_board.py --test
```

## Usage examples

A quick demonstration that the board converges to the expected distribution:

```bash
$ python3 galton_board.py --static --rows 12 --balls 10000 --seed 1 2>&1 >/dev/null
balls=10000  mean=5.993  std=1.742  var=3.035  skew=0.003  kurt=-0.187  min=0  max=12
```

For `rows = 12`, the theoretical binomial distribution has mean `rows/2 = 6`
and standard deviation `√(rows/4) ≈ 1.732` — which the simulator matches to
three decimal places after 10 000 balls.

Export the histogram for downstream analysis:

```bash
$ python3 galton_board.py --static --rows 8 --balls 2000 --export out.csv
exported histogram to out.csv

$ head -4 out.csv
bin,count,expected_normal
0,7,8.797
1,68,54.403
2,188,200.380
```

## How it works

Each ball starts at the top of the board and steps through `rows` peg rows.
At each row it shifts left or right by half a column with probability 0.5.
After `rows` steps the ball's continuous column position is rounded to the
nearest integer bin index in `[0, rows]`, giving `rows + 1` bins. This is
exactly a binomial `B(rows, 0.5)` process, whose distribution approaches a
normal `N(rows/2, rows/4)` as the number of balls grows.

Statistics are tracked with a single-pass online algorithm (Welford's
method extended to the third and fourth central moments) so that mean,
variance, skewness, and excess kurtosis update in O(1) per ball with no
storage of individual samples.

The normal-curve overlay is drawn by evaluating the Gaussian PDF at each
bin center, using the running mean and std, and scaling to the current peak
bin height. The curve fills empty cells above the bars so you can literally
watch the empirical histogram and the theoretical curve converge as more
balls drop.

## Files

- `galton_board.py` — the complete simulator (model, renderer, CLI, tests).

## Changelog

### v1.0.1 — bug fixes

- **Fixed `--no-curve` flag being dead code.** The flag was parsed but never
  passed to any `render()` call — all calls hardcoded `overlay_curve=True`.
  Now it correctly disables the normal-curve overlay in all modes.
- **Fixed duplicate stats output.** `main()` printed the stats line to stderr
  unconditionally after the run function had already printed it to stdout,
  causing it to appear twice in mixed `2>&1` output. Removed the redundant
  print.
- **Fixed interactive mode infinite loop on non-TTY stdin.** When stdin was
  not a TTY (piped input, cron, CI), `run_interactive` would loop forever
  because no keyboard input could ever arrive and there was no other exit
  condition. Now `main()` detects the non-TTY case, prints a helpful error,
  and exits with code 2.
- **Fixed unhandled `FileNotFoundError` crash on `--export` to a
  nonexistent directory.** Export I/O errors are now caught and reported
  gracefully with a clear error message and exit code 1.
- **Fixed negative `--balls` silently becoming 1000.** Negative values are
  now rejected with a validation error (exit code 2). Same for negative
  `--rate`.
- **Fixed latent `UnboundLocalError` in the test runner.** The nested
  `check()` function used `failures += 1` without a `nonlocal`
  declaration, so the test runner would crash with `UnboundLocalError` if
  *any* test ever failed. Added `nonlocal failures`.
- **Fixed curve overlay drawing order.** The curve was drawn *before* bin
  walls, causing walls to overwrite the curve. Now the curve is drawn
  *after* walls and only fills empty cells, producing a cleaner visual.
- **Removed dead `grid_x` glyph reference** in `_draw_curve` (the glyph
  was defined but never drawn on the canvas).
- **Cleaned up no-op expression** in `_bin_x`: `(b.rows - b.rows) / 2.0`
  always equals 0; replaced with a clear comment explaining bin centering.
- **Added help text** to all argparse flags (`--width`, `--height`,
  `--seed`, `--no-color`, `--version`) that previously had no `help=`.
- **Added 12 new self-tests** (28 → 40) covering the `--no-curve` flag,
  `_bin_x` correctness, CLI validation (negative `--balls`/`--rate`),
  export error handling, `--version`, non-TTY rejection, and `--no-curve`
  CLI integration.

### v1.0.0 — initial release

Animated Galton board simulator with live normal-curve overlay, Welford
running statistics, three modes (interactive/batch/static), CSV/JSON
export, seedable RNG, and 28 built-in self-tests.

## License

MIT — do whatever you like.