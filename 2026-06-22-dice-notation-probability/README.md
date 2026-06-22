# 🎲 Dice Notation Roller & Probability Analyzer

A command-line tool that parses standard and advanced dice notation, rolls dice, computes exact probability distributions, and renders beautiful ASCII histograms. Perfect for TTRPG players, game designers, and probability nerds.

## Features

- **Full dice notation parser** — supports standard notation and advanced modifiers:
  - `NdS` — roll N S-sided dice, sum them (e.g., `2d6`, `3d8`)
  - `NdS+M` / `NdS-M` — add/subtract a modifier (e.g., `2d6+3`, `1d20-2`)
  - `NdSkhK` — keep highest K dice (e.g., `4d6kh3` for D&D stat rolling)
  - `NdSklK` — keep lowest K dice (e.g., `2d20kl1` for disadvantage)
  - `NdSdhK` — drop highest K dice (e.g., `4d6dh1`)
  - `NdSdlK` — drop lowest K dice (e.g., `3d6dl1`)
  - `NdS>R`, `NdS>=R`, `NdS<R`, `NdS<=R` — count successes (e.g., `10d6>=5`)
- **Exact probability distributions** — computes exact probabilities for up to 8 dice using exhaustive enumeration
- **Monte Carlo simulation** — approximate distributions for large dice pools
- **ASCII histogram visualization** — beautiful bar charts in your terminal
- **Statistics** — mean, stddev, median, mode, min, max, percentiles
- **Head-to-head comparison** — compare two notations and see win probabilities
- **JSON output** — export distributions as JSON for scripting
- **Reproducible results** — seed support for deterministic rolling
- **58 comprehensive tests** — full test suite included

## Installation

No external dependencies — uses only Python's standard library:

```bash
# Just make it executable
chmod +x dice_prob.py

# Or run directly
python3 dice_prob.py
```

## Usage

### Roll dice

```bash
# Roll 2d6
python3 dice_prob.py 2d6

# Roll 4d6, keep highest 3 (D&D stat rolling)
python3 dice_prob.py 4d6kh3

# Roll with a modifier
python3 dice_prob.py 2d6+3

# Roll multiple times
python3 dice_prob.py 2d6 --roll 10

# Use a seed for reproducible results
python3 dice_prob.py 2d6 --seed 42
```

### Probability distributions

```bash
# Show exact probability distribution for 2d6
python3 dice_prob.py 2d6 --dist

# Show distribution for 4d6 keep highest 3
python3 dice_prob.py 4d6kh3 --dist

# Count successes distribution (10 dice, success on 5+)
python3 dice_prob.py 10d6>=5 --dist

# Use Monte Carlo for large dice pools
python3 dice_prob.py 10d6 --dist --mc

# Customize Monte Carlo trials
python3 dice_prob.py 10d6 --dist --mc --mc-trials 50000
```

### Statistics

```bash
# Show statistics (mean, stddev, median, etc.)
python3 dice_prob.py 2d6 --stats

# Show both distribution and statistics
python3 dice_prob.py 4d6kh3 --dist --stats
```

### Compare notations

```bash
# Compare 2d6 vs 1d12 — who rolls higher?
python3 dice_prob.py 2d6 1d12 --compare

# Compare with more Monte Carlo trials
python3 dice_prob.py 3d6 2d10 --compare --mc-trials 100000
```

### JSON export

```bash
# Export distribution as JSON
python3 dice_prob.py 2d6 --dist --json

# Export with statistics
python3 dice_prob.py 2d6 --dist --stats --json
```

### Custom histogram width

```bash
# Wider histogram
python3 dice_prob.py 2d6 --dist --width 80

# Narrower histogram
python3 dice_prob.py 2d6 --dist --width 30
```

## Example Output

### Rolling 4d6 keep highest 3

```
🎲 4d6kh3
═════════

  Dice: [6, 1, 1, 6]
  Kept: [6, 1, 6]  Dropped: [1]

  ══► Result: 13 ◄══
```

### Distribution of 2d6

```
🎲 2d6
══════

Exact Distribution:
  2 │████████                                              2.78%
  3 │█████████████████                                    5.56%
  4 │█████████████████████████                            8.33%
  5 │█████████████████████████████████                   11.11%
  6 │██████████████████████████████████████████          13.89%
  7 │██████████████████████████████████████████████████  16.67%
  8 │██████████████████████████████████████████          13.89%
  9 │█████████████████████████████████                   11.11%
 10 │█████████████████████████████                         8.33%
 11 │█████████████████                                     5.56%
 12 │████████                                              2.78%
```

### Comparison

```
Notation                 Mean   StdDev   Min   Max  Median
──────────────────────────────────────────────────────────
2d6                      7.00     2.41     2    12       7
1d12                     6.50     3.45     1    12       7

Head-to-head (100,000 trials):
  2d6 wins: 43.8%
  1d12 wins: 43.0%
  Ties:    13.2%
```

## Supported Notation Reference

| Notation | Meaning | Example |
|----------|---------|---------|
| `NdS` | Roll N dice with S sides, sum | `2d6` → 2–12 |
| `NdS+M` | Roll and add M | `2d6+3` → 5–15 |
| `NdS-M` | Roll and subtract M | `1d20-2` → -1–18 |
| `NdSkhK` | Keep highest K dice | `4d6kh3` → 3–18 |
| `NdSklK` | Keep lowest K dice | `2d20kl1` → 1–20 |
| `NdSdhK` | Drop highest K dice | `4d6dh1` → 3–18 |
| `NdSdlK` | Drop lowest K dice | `3d6dl1` → 2–12 |
| `NdS>R` | Count dice > R | `10d6>4` → 0–10 |
| `NdS>=R` | Count dice ≥ R | `10d6>=5` → 0–10 |
| `NdS<R` | Count dice < R | `10d6<3` → 0–10 |
| `NdS<=R` | Count dice ≤ R | `10d6<=2` → 0–10 |

## How It Works

- **Exact distributions** are computed by enumerating all possible outcomes (feasible for ≤8 dice). For `2d6`, this means all 36 combinations of two dice.
- **Monte Carlo** uses random sampling (default 100,000 trials) for distributions that are too large to enumerate exactly.
- **Statistics** are computed directly from the probability distribution for exact results, or from the Monte Carlo sample for approximate results.
- **Keep/drop** modes use sorting and selection to identify which dice contribute to the result.
- **Success count** modes count how many dice meet the threshold condition.

## Testing

```bash
python3 test_dice_prob.py
```

Runs 58 tests covering parsing, rolling, distributions, statistics, histogram output, and CLI integration.