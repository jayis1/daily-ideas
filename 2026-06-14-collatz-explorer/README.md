# Collatz Explorer

**v1.1.0** — A terminal-based visualization tool for exploring the **Collatz Conjecture** — one of mathematics' most famous unsolved problems.

Given any positive integer `n`:
- If `n` is even → `n ÷ 2`
- If `n` is odd → `3n + 1`

The conjecture states that you will **always** eventually reach 1. No one has proven it yet.

## What's New

### v1.1.0 — Feature Release
- **New mode: Convergence** (`--converge`) — ASCII heat map showing stopping times across a range of numbers, revealing convergence patterns
- **New mode: Density** (`--density`) — 2D density map of Collatz stopping times
- **New mode: Stats** (`--mode stats`) — Detailed statistics for a single number: steps, peak, growth factor, odd/even operations, operation pattern
- **Memoized `collatz_steps()`** — LRU cache makes batch/range computations dramatically faster for repeated queries
- **`--export FILE`** — Save visualization output to a file instead of stdout
- **`--version` flag** — display version number
- **`--no-color` and `NO_COLOR` support** — disable ANSI colors for piped/scripted output
- **Interactive mode expanded** — modes 7 (Converge), 8 (Density), and `s` (Stats) added
- **Input validation** — negative numbers and zero now produce clear error messages
- **`collatz_stats()` API** — comprehensive statistics dictionary for programmatic use
- **47 tests** — full test suite covering core functions, renderers, CLI flags, and edge cases

## Features

**8 visualization modes + stats:**

| Mode | Description |
|------|-------------|
| **Sequence** | Step-by-step sequence with parity indicators (÷2 vs ×3+1) |
| **Path** | Compact dot-graph showing rises and falls of values |
| **Histogram** | Log-scale value distribution bar chart |
| **Tree** | Reverse Collatz tree — which numbers converge to a target? |
| **Batch** | Statistics and bar chart across a range of starting numbers |
| **Hailstone** | Value-over-time chart with directional markers (╱ rise, ╲ fall, ━ at 1) |
| **Converge** | Convergence speed heat map for a range of starting values |
| **Density** | 2D density map of stopping times across a range |
| **Stats** | Detailed statistics for a single number (steps, peak, growth factor, operation pattern) |

**Key stats displayed:**
- Steps to convergence
- Peak value reached
- Growth factor (peak relative to starting value)
- Odd/even operation ratio
- Operation pattern (÷/×) visualization
- Values above starting value
- Powers-of-2 fast paths and slow-convergence outliers (in batch mode)

## Installation

No dependencies needed — pure Python 3.6+ standard library:

```bash
git clone <repo-url>
cd collatz-explorer
chmod +x collatz_explorer.py
```

## Usage

### Interactive mode (default)

```bash
python3 collatz_explorer.py
```

Presents a menu to pick a visualization mode and enter numbers interactively. Choose from 8 visualization modes plus stats.

### Command-line mode

```bash
# Hailstone chart for n=27 (the famous 111-step sequence)
python3 collatz_explorer.py -n 27 --mode hailstone

# Step-by-step sequence for n=7
python3 collatz_explorer.py -n 7 --mode sequence

# Value distribution histogram
python3 collatz_explorer.py -n 27 --mode histogram

# Rise/fall path graph
python3 collatz_explorer.py -n 27 --mode path

# Detailed statistics for n=27
python3 collatz_explorer.py -n 27 --mode stats

# Batch statistics for range [1, 30]
python3 collatz_explorer.py --batch 1 30

# Convergence speed chart for range [1, 50]
python3 collatz_explorer.py --converge 1 50

# Density map for range [1, 100]
python3 collatz_explorer.py --density 1 100

# Reverse tree: which numbers reach 1 within 10 steps?
python3 collatz_explorer.py --tree 1 --depth 10

# Save output to a file
python3 collatz_explorer.py -n 27 --mode hailstone --export output.txt

# Disable colors (also supports NO_COLOR env var)
python3 collatz_explorer.py -n 27 --mode hailstone --no-color
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-n` | 27 | Starting number |
| `--mode` | hailstone | Visualization mode: sequence, path, histogram, tree, batch, hailstone, converge, density, stats |
| `--batch START END` | — | Range for batch statistics (clamped to 50) |
| `--tree TARGET` | — | Target for reverse tree |
| `--converge START END` | — | Range for convergence speed chart (clamped to 100) |
| `--density START END` | — | Range for density map (clamped to 100) |
| `--depth` | 8 | Tree depth |
| `--width` | 70 | Chart width in characters |
| `--height` | 22 | Chart height in characters |
| `--bins` | 15 | Histogram bins |
| `--no-color` | false | Disable ANSI colors |
| `--export FILE` | — | Save output to a file |
| `--version` | — | Show version number |

### Interesting starting numbers

- `n = 27` — the classic example: 111 steps, peaks at 9,232
- `n = 871` — peaks at 190,996 over 178 steps
- `n = 6171` — 261 steps to reach 1
- `n = 77031` — peaks at 1,185,280 over 350 steps

## Example Output

### Stats mode (n=27)

```
  Collatz Statistics for n = 27

  Starting value:     27
  Steps to reach 1:   111
  Peak value:         9,232
  Growth factor:      341.9×
  Odd operations:     41
  Even operations:    70
  Even/Odd ratio:    1.71:1

  Values above start: 102 / 112 (91.1%)
  Times at 1:         1 (always 1 at end)

  Operation pattern:  × ÷ × ÷ ÷ × ÷ × ÷ × ÷ ÷ × ÷ ÷ × ÷ × ÷ ÷ × ÷ × ÷ ...
  (÷ = even/halve, × = odd/triple+1)
```

### Hailstone chart (n=27)

```
  Hailstone Chart for n = 27  (steps: 111, peak: 9,232)

      9,232 │                                                ▲
             │                                          ╱
             │                                               ╱
             │                                         ╱
             │                                                 ╱
             │                        ╱             ╱    ╱  ╱
             │                          ╱          ╱  ╱    ╱     ╱
             │                               ╱  ╱ ╱ ╱  ╱    ╱     ╱  ╱ ╱
             │         ╱       ╱  ╱  ╱ ╱  ╱                       ╱ ╱
           1 │╲╱╱╱╱╱╱ ╱╱╱╱╱╱╱ ╱╱ ╱╱    ╱ ╱╱ ╱╱ ╱                    ╱╱╱╱╲╱╱╱╱╲╲╲╲━
             └──────────────────────────────────────────────────────────────────────
              Step 0                                                        Step 111

  Odd operations (3n+1): 41   Even operations (n÷2): 70   Ratio: 1.71:1
  Growth factor: peak 9,232 is 341.9× starting value
```

## How It Works

The Collatz sequence (also called the "hailstone sequence" because values rise and fall unpredictably) is generated by repeatedly applying the rule `n/2` (even) or `3n+1` (odd). The reverse tree is built via BFS: from any value, the two possible predecessors are `2n` (always valid) and `(n-1)/3` (valid only when it produces an odd integer > 1).

**Memoization**: The `collatz_steps()` function uses LRU caching to dramatically speed up repeated queries, especially useful for batch, convergence, and density modes that compute stopping times for many numbers.

## Running Tests

```bash
python3 test_collatz.py
```

The test suite (47 tests) covers:
- Core Collatz functions (sequence, steps, max, stats)
- Memoized steps consistency
- Invalid input validation (0, negative numbers)
- Reverse tree construction
- All 8 visualization renderers
- Statistics renderer
- Color function
- CLI flags (`--version`, `--help`, `--export`, `--no-color`)
- Convergence and density modes
- Edge cases (n=1, n=2, powers of 2, famous n=27)
- Version consistency

## License

MIT