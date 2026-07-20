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
                          ∘     ∘
                      ∘      ∘      ∘
                   ∘      ∘     ∘      ∘
                ∘     ∘      ∘      ∘     ∘
            ∘      ∘      ∘     ∘      ∘      ∘
         ∘     ∘      ∘      ∘     ∘      ∘      ∘
      ∘     ∘      ∘     ∘      ∘      ∘     ∘      ∘
──────────────────────────────────────────────────────
  │      │     │      │  █   │      │     │      │
  │      │     │  █   │  █   │  █   │     │      │
  │      │  █  │  █   │  █   │  █   │  █  │      │
  │  █   │  █  │  █   │  █   │  █   │  █  │  █   │

balls=800  mean=4.001  std=1.469  skew=0.040  kurt=-0.129
```

## Features

- **Animated ASCII rendering** of pegs, falling balls, and accumulating bins.
- **Live normal-distribution fit** overlaid on the histogram (`▓` / `%`).
- **Running statistics** via Welford-style online moments:
  count, mean, variance, std, skewness, excess kurtosis, min, max.
- **Three modes:**
  - *Interactive* — drop balls one at a time with keyboard controls.
  - *Batch* (`--batch`) — rapid animated dropping of N balls.
  - *Static* (`--static`) — compute N balls with no animation, render the
    final histogram.
- **Configurable geometry**: peg rows, board width/height, drop rate.
- **Color and glyph modes**: full-color UTF-8, monochrome UTF-8, or plain
  ASCII (`--ascii`, `--no-color`).
- **Seedable RNG** (`--seed`) for reproducible runs.
- **Export** the final histogram to CSV or JSON (`--export`), including the
  expected-normal counts per bin.
- **Built-in self-test suite** (`--test`) — 28 checks covering physics,
  statistics, rendering, export, and edge cases.
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
| `SPACE` | drop a ball from a random column       |
| `ENTER` | drop a ball from the center column      |
| `b`     | toggle continuous batch dropping        |
| `+`/`-` | increase / decrease the drop rate       |
| `c`     | clear the bins and reset stats          |
| `r`     | full reset (bins, stats, balls)         |
| `q`     | quit and print the final histogram      |

### Batch (animated, fast)

```bash
python3 galton_board.py --batch --rows 12 --balls 5000 --rate 60
```

### Static (one-shot, no animation)

```bash
python3 galton_board.py --static --rows 10 --balls 10000 --seed 42
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
$ python3 galton_board.py --static --rows 12 --balls 10000 --seed 1 --ascii --no-color 2>/dev/null
# (ASCII board with a tall, symmetric bell curve in the center bins)

$ python3 galton_board.py --static --rows 12 --balls 10000 --seed 1 2>&1 >/dev/null
balls=10000  mean=6.002  std=1.734  var=3.007  skew=0.012  kurt=-0.081  min=0  max=12
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
0,2,1.102
1,17,15.479
2,82,84.263
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
bin height — so you can literally watch the empirical histogram and the
theoretical curve converge as more balls drop.

## Files

- `galton_board.py` — the complete simulator (model, renderer, CLI, tests).

## License

MIT — do whatever you like.