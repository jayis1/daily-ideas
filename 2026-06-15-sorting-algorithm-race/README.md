# 🏁 Sorting Algorithm Race v2.0

A real-time terminal visualization that pits multiple sorting algorithms against each other in a head-to-head race. Watch Bubble Sort struggle, Quick Sort fly, and Tim Sort hold steady — all competing simultaneously on the same shuffled dataset with live progress bars, comparison/swap counters, and mini histograms.

## What's New in v2.0

- **Tim Sort added** — the hybrid merge+insertion algorithm that powers Python's built-in `sorted()` and Java's `Arrays.sort()`
- **`--version` flag** — standard CLI version reporting
- **`--list` flag** — display all 11 algorithms with their complexity info (best/average/worst case, space, stability) in a formatted table
- **`--no-animation` flag** — skip the live animation and just print final results (great for scripts and CI)
- **`--detailed` flag** — show array accesses column in benchmark output
- **`--export csv|json`** — export benchmark results as machine-readable CSV or JSON to stdout
- **Better progress estimation** — uses a sortedness metric instead of crude step-counting for more accurate progress bars during the race
- **Early termination in Bubble Sort** — already-sorted arrays now finish in O(n) instead of O(n²)
- **Correctness verification** — after every race or benchmark, results are checked against Python's `sorted()` to catch bugs
- **Input validation** — `--size` must be ≥ 1, `--repeat` must be ≥ 1, `--export` requires `--benchmark`
- **More tests** — 55 tests covering new features, edge cases, CLI validation, and export formats
- **Better comments and docstrings** throughout

## Features

- **11 sorting algorithms**: Bubble, Selection, Insertion, Shell, Quick, Merge, Heap, Cocktail, Gnome, Radix, and Tim Sort
- **Animated race mode**: Watch algorithms compete in real time with progress bars and live stats
- **No-animation mode**: `--no-animation` for quiet, script-friendly results
- **Benchmark mode**: Run algorithms sequentially and compare performance in a clean table
- **Export results**: Output benchmark data as CSV or JSON for analysis
- **Mini histograms**: Each algorithm's current array state is visualized as an ASCII histogram during the race
- **Sortedness-based progress**: Progress bars use a sortedness metric for accurate estimation
- **Medal system**: 🥇🥈🥉 rankings for the top 3 finishers
- **Detailed stats**: Tracks comparisons, swaps, and array accesses for each algorithm
- **Algorithm info**: `--list` shows complexity table (best/average/worst case, space, stability)
- **Correctness check**: Verifies all sorted results against Python's reference `sorted()`
- **Reproducible**: Use `--seed` for consistent shuffles across runs
- **Configurable array size**: Test with small or large datasets

## Installation

No external dependencies needed — just Python 3.7+:

```bash
git clone <repo-url>
cd sorting-algorithm-race
```

## How to Run

### Race Mode (default)

Race the 5 default algorithms (Bubble, Insertion, Quick, Merge, Heap) on 200 elements:

```bash
python3 sort_race.py
```

Race specific algorithms:

```bash
python3 sort_race.py -a bubble selection insertion
```

Race ALL algorithms at once:

```bash
python3 sort_race.py --all
```

Adjust array size:

```bash
python3 sort_race.py -s 500
```

Use a fixed seed for reproducibility:

```bash
python3 sort_race.py --seed 42
```

Skip animation and just show final results:

```bash
python3 sort_race.py --no-animation
```

### Benchmark Mode

Get a clean comparison table without animation:

```bash
python3 sort_race.py --benchmark
```

Benchmark all algorithms on 1000 elements, averaged over 3 runs:

```bash
python3 sort_race.py --benchmark --all -s 1000 --repeat 3
```

Show array accesses in the benchmark table:

```bash
python3 sort_race.py --benchmark --all --detailed
```

### Export Benchmark Results

Export as JSON (to stdout):

```bash
python3 sort_race.py --benchmark --all -s 5000 --export json > results.json
```

Export as CSV (to stdout):

```bash
python3 sort_race.py --benchmark -a bubble quick merge -s 5000 --export csv > results.csv
```

### List Algorithms

View all available algorithms with their complexity info:

```bash
python3 sort_race.py --list
```

Output:

```
════════════════════════════════════════════════════════════════════════════════
  📋  Available Sorting Algorithms  📋
════════════════════════════════════════════════════════════════════════════════

  Key          Name               Best           Average        Worst          Space      Stable
  ──────────────────────────────────────────────────────────────────────────────────
  bubble       Bubble Sort        O(n)           O(n²)          O(n²)          O(1)       ✓
  selection    Selection Sort     O(n²)          O(n²)          O(n²)          O(1)       ✗
  insertion    Insertion Sort     O(n)           O(n²)          O(n²)          O(1)       ✓
  shell        Shell Sort        O(n log n)     O(n^1.25)     O(n²)          O(1)       ✗
  quick        Quick Sort        O(n log n)     O(n log n)     O(n²)          O(log n)   ✗
  merge        Merge Sort        O(n log n)     O(n log n)     O(n log n)     O(n)       ✓
  heap         Heap Sort         O(n log n)     O(n log n)     O(n log n)     O(1)       ✗
  cocktail     Cocktail Sort     O(n)           O(n²)          O(n²)          O(1)       ✓
  gnome        Gnome Sort        O(n)           O(n²)          O(n²)          O(1)       ✓
  radix        Radix Sort        O(nk)          O(nk)          O(nk)          O(n+k)     ✓
  tim          Tim Sort          O(n)           O(n log n)     O(n log n)     O(n)       ✓
```

### Version

```bash
python3 sort_race.py --version
```

## Usage Examples

### Example: Racing 3 algorithms on 300 elements

```bash
python3 sort_race.py -a bubble quick merge -s 300
```

This launches an animated terminal display showing:
- Each algorithm's name and color
- A progress bar (based on sortedness) or completion status with medal
- Real-time comparison, swap, and array access counts
- A live ASCII histogram of the current state of each algorithm's array
- Correctness verification after all algorithms finish

### Example: Benchmark output

```bash
$ python3 sort_race.py --benchmark --all -s 5000
```

```
════════════════════════════════════════════════════════════════════════════
  🏁  SORTING BENCHMARK — 5000 elements, 1 run(s)  🏁
════════════════════════════════════════════════════════════════════════════

  Rank  Algorithm          Time        Comps        Swaps
  ────────────────────────────────────────────────────────────────────────────
  🥇1   Radix Sort         0.0145s       0            50000
  🥈2   Quick Sort         0.0231s     62034           14228
  🥉3   Tim Sort           0.0312s     55000           12000
     4   Shell Sort         0.0372s     87043           42217
     5   Merge Sort         0.0418s     57047           12689
     6   Heap Sort          0.0523s    115630           26750
     7   Insertion Sort     0.8941s   6266758        3133378
     8   Cocktail Sort      1.1023s   6266758        3133378
     9   Selection Sort     1.2345s   12497500         4990
    10   Bubble Sort        1.4567s   6266758        3133378
    11   Gnome Sort         2.0134s   6266758        3133378

  Times are averages over 1 run(s).
  Use --detailed to show array accesses column.
```

### Example: JSON export

```bash
$ python3 sort_race.py --benchmark -a bubble quick --export json -s 100
```

```json
{
  "benchmark": {
    "size": 100,
    "repeat": 1,
    "seed": null
  },
  "results": [
    {"key": "quick", "name": "Quick Sort", "time": 0.0003, "comparisons": 620, "swaps": 150, "accesses": 1800},
    {"key": "bubble", "name": "Bubble Sort", "time": 0.0012, "comparisons": 4950, "swaps": 2500, "accesses": 14900}
  ]
}
```

## How It Works

Each sorting algorithm runs in its own thread on an identical copy of the shuffled array. The main thread polls their progress at ~8 FPS, displaying:

1. **Status indicators**: Progress bars (based on a sortedness metric) for running algorithms, medals (🥇🥈🥉) for finished ones
2. **Statistics**: Live counters for comparisons, swaps, and array accesses — updated by each algorithm during execution
3. **Mini histograms**: ASCII block histograms showing the current state of each array, so you can *see* the sort progressing (bubble sort's "bubble" moving right, quick sort's partitions forming, etc.)
4. **Correctness verification**: After all algorithms finish, each result is compared against Python's `sorted()` to ensure correctness

The sortedness metric measures what fraction of adjacent pairs are in order (0.0 = fully reversed, 1.0 = fully sorted), providing a more accurate progress bar than crude step counting.

## Algorithm Details

| Algorithm | Best Case | Average Case | Worst Case | Space | Stable |
|-----------|-----------|-------------|------------|-------|--------|
| Bubble Sort | O(n) | O(n²) | O(n²) | O(1) | Yes |
| Selection Sort | O(n²) | O(n²) | O(n²) | O(1) | No |
| Insertion Sort | O(n) | O(n²) | O(n²) | O(1) | Yes |
| Shell Sort | O(n log n) | O(n^1.25) | O(n²) | O(1) | No |
| Quick Sort | O(n log n) | O(n log n) | O(n²) | O(log n) | No |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes |
| Heap Sort | O(n log n) | O(n log n) | O(n log n) | O(1) | No |
| Cocktail Sort | O(n) | O(n²) | O(n²) | O(1) | Yes |
| Gnome Sort | O(n) | O(n²) | O(n²) | O(1) | Yes |
| Radix Sort | O(nk) | O(nk) | O(nk) | O(n+k) | Yes |
| Tim Sort | O(n) | O(n log n) | O(n log n) | O(n) | Yes |

## All CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `-a` / `--algorithms` | bubble, insertion, quick, merge, heap | Which algorithms to race |
| `-s` / `--size` | 200 | Size of the array to sort (≥ 1) |
| `--seed` | random | Random seed for reproducibility |
| `--benchmark` | off | Run in benchmark mode (sequential, prints table) |
| `--repeat` | 1 | Number of repetitions in benchmark mode (≥ 1) |
| `--all` | off | Race all available algorithms |
| `--no-animation` | off | Skip live animation, just show final results |
| `--detailed` | off | Show array accesses column in benchmark mode |
| `--export` | — | Export format: `csv` or `json` (benchmark mode only) |
| `--list` | off | List all algorithms with complexity info and exit |
| `--version` | — | Show version number |
| `--help` | — | Show help message |

## Running Tests

```bash
python3 -m pytest test_sort_race.py -v
```

The test suite includes 55 tests covering:
- All 11 sorting algorithms on random, sorted, reversed, empty, and single-element arrays
- Duplicate element handling
- Two-element edge cases
- Stats tracking (comparisons, swaps, accesses)
- Early termination optimization in Bubble Sort
- Utility functions (bar, mini_histogram, sortedness)
- Benchmark mode with JSON and CSV export
- Algorithm registry and complexity metadata
- CLI flags: `--version`, `--help`, `--list`, `--no-animation`, `--detailed`, `--export`
- Input validation (invalid size, invalid repeat, export without benchmark)

## As a Python Library

```python
from sort_race import (
    run_race, run_benchmark, ALL_ALGORITHMS, ALGO_COMPLEXITY,
    sortedness, bar, mini_histogram,
)

# Race mode (returns list of (Algorithm, data) tuples)
results = run_race(["bubble", "quick", "merge", "tim"], size=200, seed=42)

# Benchmark mode (returns list of result dicts sorted by time)
bench = run_benchmark(["quick", "merge", "tim"], size=1000, seed=42, repeat=3)
for r in bench:
    print(f"{r['name']}: {r['time']:.4f}s, {r['comparisons']} comparisons")

# Export benchmark as JSON or CSV
run_benchmark(["bubble", "quick"], size=500, export_format="json")
run_benchmark(["bubble", "quick"], size=500, export_format="csv")

# Check sortedness of an array
progress = sortedness(my_array)  # 0.0 to 1.0

# List available algorithms
for key, (name, func) in ALL_ALGORITHMS.items():
    best, avg, worst, space, stable = ALGO_COMPLEXITY[key]
    print(f"{name}: {avg} avg, stable={stable}")
```

## License

MIT