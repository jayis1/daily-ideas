# 🏁 Sorting Algorithm Race

A real-time terminal visualization that pits multiple sorting algorithms against each other in a head-to-head race. Watch Bubble Sort struggle, Quick Sort fly, and Merge Sort hold steady — all competing simultaneously on the same shuffled dataset with live progress bars, comparison/swap counters, and mini histograms.

## Features

- **10 sorting algorithms**: Bubble, Selection, Insertion, Shell, Quick, Merge, Heap, Cocktail, Gnome, and Radix Sort
- **Animated race mode**: Watch algorithms compete in real time with progress bars and live stats
- **Benchmark mode**: Run algorithms sequentially and compare performance in a clean table
- **Mini histograms**: Each algorithm's current array state is visualized as an ASCII histogram during the race
- **Medal system**: 🥇🥈🥉 rankings for the top 3 finishers
- **Detailed stats**: Tracks comparisons, swaps, and array accesses for each algorithm
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

### Benchmark Mode

Get a clean comparison table without animation:

```bash
python3 sort_race.py --benchmark
```

Benchmark all algorithms on 1000 elements, averaged over 3 runs:

```bash
python3 sort_race.py --benchmark --all -s 1000 --repeat 3
```

## Usage Examples

### Example: Racing 3 algorithms on 300 elements

```bash
python3 sort_race.py -a bubble quick merge -s 300
```

This launches an animated terminal display showing:
- Each algorithm's name and color
- A progress bar or completion status with medal
- Real-time comparison, swap, and array access counts
- A live ASCII histogram of the current state of each algorithm's array

### Example: Benchmark output

```bash
$ python3 sort_race.py --benchmark --all -s 5000

════════════════════════════════════════════════════════════════════════════
  🏁  SORTING BENCHMARK — 5000 elements, 1 run(s)  🏁
════════════════════════════════════════════════════════════════════════════

  Rank  Algorithm          Time        Comps        Swaps     Accesses
  ────────────────────────────────────────────────────────────────────────────
  🥇1   Radix Sort         0.0145s       0            50000        70000
  🥈2   Quick Sort         0.0231s     62034           14228       166466
  🥉3   Shell Sort         0.0372s     87043           42217       213349
     4   Merge Sort         0.0418s     57047           12689       142094
     5   Heap Sort          0.0523s    115630           26750       286880
     6   Insertion Sort     0.8941s   6266758        3133378      18800194
     7   Cocktail Sort      1.1023s   6266758        3133378      18800194
     8   Selection Sort     1.2345s   12497500         4990       24997498
     9   Bubble Sort        1.4567s   6266758        3133378      18800194
    10   Gnome Sort         2.0134s   6266758        3133378      18800194

  Times are averages over 1 run(s).
```

## How It Works

Each sorting algorithm runs in its own thread on an identical copy of the shuffled array. The main thread polls their progress at ~8 FPS, displaying:

1. **Status indicators**: Progress bars for running algorithms, medals (🥇🥈🥉) for finished ones
2. **Statistics**: Live counters for comparisons, swaps, and array accesses — updated by each algorithm during execution
3. **Mini histograms**: ASCII block histograms showing the current state of each array, so you can *see* the sort progressing (bubble sort's "bubble" moving right, quick sort's partitions forming, etc.)

When all algorithms finish, a final leaderboard displays ranked results with precise timing.

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

## Running Tests

```bash
python3 -m pytest test_sort_race.py -v
```