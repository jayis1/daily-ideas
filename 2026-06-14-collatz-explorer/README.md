# Collatz Explorer

**v1.2.0** — A terminal-based visualization tool for exploring the **Collatz Conjecture** — one of mathematics' most famous unsolved problems.

Given any positive integer `n`:
- If `n` is even → `n ÷ 2`
- If `n` is odd → `3n + 1`

The conjecture states that you will **always** eventually reach 1. No one has proven it yet.

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

# Reverse tree from n=5 (which numbers reach 5?)
python3 collatz_explorer.py -n 5 --mode tree

# Batch statistics around n=5 (range [1, 15])
python3 collatz_explorer.py -n 5 --mode batch

# Batch statistics for range [1, 30]
python3 collatz_explorer.py --batch 1 30

# Convergence speed chart for range [1, 50]
python3 collatz_explorer.py --converge 1 50

# Density map for range [1, 100]
python3 collatz_explorer.py --density 1 100

# Reverse tree: which numbers reach 1 within 10 steps?
python3 collatz_explorer.py --tree 1 --depth 10

# Save output to a file (overwrites on each run)
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
| `--export FILE` | — | Save output to a file (overwrites existing) |
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

**Memoization**: The `collatz_steps()` function uses an iterative memoization approach — it walks the sequence step by step and checks a dictionary for already-computed stopping times. When a cached value is found, it back-fills all intermediate results. This avoids the `RecursionError` that a recursive approach would hit for large starting values.

## Running Tests

```bash
python3 test_collatz.py
```

The test suite (55 tests) covers:
- Core Collatz functions (sequence, steps, max, stats)
- Iterative memoization consistency (vs sequence length)
- Invalid input validation (0, negative numbers)
- Reverse tree construction
- All 8 visualization renderers
- Statistics renderer
- Color function
- CLI flags (`--version`, `--help`, `--export`, `--no-color`, `--converge`, `--density`)
- Convergence and density modes
- Edge cases (n=1, n=2, powers of 2, famous n=27)
- Version consistency
- **Bug regression tests**: no RecursionError for large n, `-n --mode tree/batch` produces output, `--export` overwrites, path label spacing, converge legend accuracy, density label deduplication

## Changelog

### v1.2.0 — Bug Fix Release
- **Fixed: `-n N --mode tree` silently produced no output** — tree and batch modes were not handled in the `-n` code path, so they were ignored. Both now work correctly with `-n`.
- **Fixed: `--export` appended instead of overwriting** — running export twice would concatenate outputs. Now the file is overwritten on each run.
- **Fixed: `collatz_steps()` could hit `RecursionError`** — the recursive `@lru_cache` implementation could overflow the call stack for large numbers with low system recursion limits. Replaced with iterative memoization that back-fills cached results.
- **Fixed: Path mode step label had no spacing** — `min(width-8, 0)` always evaluated to 0, producing labels like "Step 0Step 16" instead of "Step 0        Step 16". Changed to `max()`.
- **Fixed: Density map showed duplicate y-axis labels** — when step range was small relative to chart height, the same integer label appeared on many rows. Now duplicate labels are suppressed (only top/bottom/changed labels shown).
- **Fixed: Converge mode legend could show values above max** — for single-number ranges, the legend showed "5-6" when the max was 5. Legend values are now clamped to `max_steps`.

### v1.1.0 — Feature Release
- New modes: Convergence, Density, Stats
- Memoized `collatz_steps()`
- `--export FILE`, `--version`, `--no-color` / `NO_COLOR` support
- `collatz_stats()` API
- Input validation
- 47 tests

### v1.0.0 — Initial Release
- 6 visualization modes (Sequence, Path, Histogram, Tree, Batch, Hailstone)
- Interactive and CLI modes
- ANSI color support

## License

MIT