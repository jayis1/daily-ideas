#!/usr/bin/env python3
"""
Sorting Algorithm Race — Watch sorting algorithms compete in real time!

A terminal visualization that runs multiple sorting algorithms simultaneously
on the same shuffled data and shows animated progress bars, comparison/swap
counters, and a live leaderboard.
"""

import argparse
import random
import sys
import time
import threading
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Callable, List, Optional

# ─── ANSI helpers ──────────────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

CLEAR_SCREEN = "\033[2J\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

ALGO_COLORS = [CYAN, GREEN, YELLOW, MAGENTA, BLUE, RED, WHITE]


def bar(value: int, max_val: int, width: int = 30) -> str:
    """Return an ASCII progress bar."""
    filled = int(width * value / max_val) if max_val > 0 else 0
    return "█" * filled + "░" * (width - filled)


def mini_histogram(data: List[int], width: int = 40, height: int = 5) -> List[str]:
    """Return a small ASCII histogram of the data, as a list of rows (top to bottom)."""
    if not data:
        return [" " * width] * height

    n = len(data)
    # Bucket data into `width` bins
    bins = [0] * width
    bin_size = max(1, n // width)
    for i in range(width):
        start = i * bin_size
        end = min(start + bin_size, n)
        if start >= n:
            break
        bins[i] = int(sum(data[start:end]) / (end - start)) if end > start else 0

    max_bin = max(bins) if bins else 1
    if max_bin == 0:
        max_bin = 1

    rows = []
    for level in range(height, 0, -1):
        threshold = level / height
        row = ""
        for b in bins:
            frac = b / max_bin
            if frac >= threshold:
                row += "█"
            elif frac >= threshold - 0.5 / height:
                row += "▒"
            else:
                row += " "
        rows.append(row)
    return rows


# ─── Sorting algorithm implementations with step counting ───────────────────

@dataclass
class SortStats:
    comparisons: int = 0
    swaps: int = 0
    array_accesses: int = 0
    done: bool = False
    finish_order: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    snapshot: List[int] = field(default_factory=list)
    steps: int = 0


@dataclass
class Algorithm:
    name: str
    func: Callable
    color: str = ""
    stats: SortStats = field(default_factory=SortStats)


def bubble_sort(arr: List[int], stats: SortStats):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            stats.comparisons += 1
            stats.array_accesses += 2
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                stats.swaps += 1
                stats.array_accesses += 2
            stats.steps += 1
            # snapshot every 50 steps for animation
            if stats.steps % 50 == 0:
                stats.snapshot = list(arr)
        # snapshot at end of each pass
        stats.snapshot = list(arr)
    stats.done = True


def selection_sort(arr: List[int], stats: SortStats):
    n = len(arr)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            stats.comparisons += 1
            stats.array_accesses += 2
            if arr[j] < arr[min_idx]:
                min_idx = j
            stats.steps += 1
            if stats.steps % 50 == 0:
                stats.snapshot = list(arr)
        if min_idx != i:
            arr[i], arr[min_idx] = arr[min_idx], arr[i]
            stats.swaps += 1
            stats.array_accesses += 2
        stats.snapshot = list(arr)
    stats.done = True


def insertion_sort(arr: List[int], stats: SortStats):
    n = len(arr)
    for i in range(1, n):
        key = arr[i]
        stats.array_accesses += 1
        j = i - 1
        while j >= 0:
            stats.comparisons += 1
            stats.array_accesses += 1
            if arr[j] > key:
                arr[j + 1] = arr[j]
                stats.swaps += 1
                stats.array_accesses += 2
                j -= 1
            else:
                break
            stats.steps += 1
            if stats.steps % 50 == 0:
                stats.snapshot = list(arr)
        arr[j + 1] = key
        stats.array_accesses += 1
        stats.snapshot = list(arr)
    stats.done = True


def shell_sort(arr: List[int], stats: SortStats):
    n = len(arr)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            temp = arr[i]
            stats.array_accesses += 1
            j = i
            while j >= gap:
                stats.comparisons += 1
                stats.array_accesses += 1
                if arr[j - gap] > temp:
                    arr[j] = arr[j - gap]
                    stats.swaps += 1
                    stats.array_accesses += 2
                    j -= gap
                else:
                    break
                stats.steps += 1
                if stats.steps % 50 == 0:
                    stats.snapshot = list(arr)
            arr[j] = temp
            stats.array_accesses += 1
        gap //= 2
    stats.done = True


def quick_sort(arr: List[int], stats: SortStats):
    def _qs(a, lo, hi):
        if lo < hi:
            p = _partition(a, lo, hi)
            _qs(a, lo, p - 1)
            _qs(a, p + 1, hi)

    def _partition(a, lo, hi):
        pivot = a[hi]
        stats.array_accesses += 1
        i = lo - 1
        for j in range(lo, hi):
            stats.comparisons += 1
            stats.array_accesses += 1
            if a[j] <= pivot:
                i += 1
                a[i], a[j] = a[j], a[i]
                stats.swaps += 1
                stats.array_accesses += 2
            stats.steps += 1
            if stats.steps % 50 == 0:
                stats.snapshot = list(arr)
        a[i + 1], a[hi] = a[hi], a[i + 1]
        stats.swaps += 1
        stats.array_accesses += 2
        stats.snapshot = list(arr)
        return i + 1

    _qs(arr, 0, len(arr) - 1)
    stats.done = True


def merge_sort(arr: List[int], stats: SortStats):
    def _ms(a, l, r):
        if l < r:
            m = (l + r) // 2
            _ms(a, l, m)
            _ms(a, m + 1, r)
            _merge(a, l, m, r)

    def _merge(a, l, m, r):
        left = a[l:m + 1]
        right = a[m + 1:r + 1]
        stats.array_accesses += (m + 1 - l) + (r - m)
        i = j = 0
        k = l
        while i < len(left) and j < len(right):
            stats.comparisons += 1
            stats.array_accesses += 2
            if left[i] <= right[j]:
                a[k] = left[i]
                i += 1
            else:
                a[k] = right[j]
                j += 1
                stats.swaps += 1
            stats.array_accesses += 1
            k += 1
            stats.steps += 1
            if stats.steps % 50 == 0:
                stats.snapshot = list(arr)
        while i < len(left):
            a[k] = left[i]
            stats.array_accesses += 1
            i += 1
            k += 1
        while j < len(right):
            a[k] = right[j]
            stats.array_accesses += 1
            j += 1
            k += 1
        stats.snapshot = list(arr)

    _ms(arr, 0, len(arr) - 1)
    stats.done = True


def heap_sort(arr: List[int], stats: SortStats):
    n = len(arr)

    def heapify(a, n, i):
        largest = i
        left = 2 * i + 1
        right = 2 * i + 2
        if left < n:
            stats.comparisons += 1
            stats.array_accesses += 2
            if a[left] > a[largest]:
                largest = left
        if right < n:
            stats.comparisons += 1
            stats.array_accesses += 2
            if a[right] > a[largest]:
                largest = right
        if largest != i:
            a[i], a[largest] = a[largest], a[i]
            stats.swaps += 1
            stats.array_accesses += 2
            stats.steps += 1
            if stats.steps % 50 == 0:
                stats.snapshot = list(arr)
            heapify(a, n, largest)

    for i in range(n // 2 - 1, -1, -1):
        heapify(arr, n, i)
    for i in range(n - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]
        stats.swaps += 1
        stats.array_accesses += 2
        stats.snapshot = list(arr)
        heapify(arr, i, 0)
    stats.done = True


def cocktail_sort(arr: List[int], stats: SortStats):
    n = len(arr)
    swapped = True
    start = 0
    end = n - 1
    while swapped:
        swapped = False
        for i in range(start, end):
            stats.comparisons += 1
            stats.array_accesses += 2
            if arr[i] > arr[i + 1]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                stats.swaps += 1
                stats.array_accesses += 2
                swapped = True
            stats.steps += 1
            if stats.steps % 50 == 0:
                stats.snapshot = list(arr)
        if not swapped:
            break
        end -= 1
        swapped = False
        for i in range(end - 1, start - 1, -1):
            stats.comparisons += 1
            stats.array_accesses += 2
            if arr[i] > arr[i + 1]:
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                stats.swaps += 1
                stats.array_accesses += 2
                swapped = True
            stats.steps += 1
            if stats.steps % 50 == 0:
                stats.snapshot = list(arr)
        start += 1
    stats.done = True


def gnome_sort(arr: List[int], stats: SortStats):
    n = len(arr)
    if n <= 1:
        stats.done = True
        return
    i = 1
    while i < n:
        stats.comparisons += 1
        stats.array_accesses += 2
        if arr[i] >= arr[i - 1]:
            i += 1
        else:
            arr[i], arr[i - 1] = arr[i - 1], arr[i]
            stats.swaps += 1
            stats.array_accesses += 2
            if i > 1:
                i -= 1
        stats.steps += 1
        if stats.steps % 50 == 0:
            stats.snapshot = list(arr)
    stats.done = True


def radix_sort(arr: List[int], stats: SortStats):
    if not arr:
        stats.done = True
        return
    max_val = max(arr)
    exp = 1
    n = len(arr)
    while max_val // exp > 0:
        output = [0] * n
        count = [0] * 10
        for i in range(n):
            idx = (arr[i] // exp) % 10
            count[idx] += 1
            stats.array_accesses += 1
        for i in range(1, 10):
            count[i] += count[i - 1]
        for i in range(n - 1, -1, -1):
            idx = (arr[i] // exp) % 10
            output[count[idx] - 1] = arr[i]
            count[idx] -= 1
            stats.array_accesses += 2
            stats.swaps += 1
        for i in range(n):
            arr[i] = output[i]
            stats.array_accesses += 1
        stats.steps += 1
        stats.snapshot = list(arr)
        exp *= 10
    stats.done = True


# ─── Algorithm registry ─────────────────────────────────────────────────────

ALL_ALGORITHMS = {
    "bubble":    ("Bubble Sort",    bubble_sort),
    "selection": ("Selection Sort",  selection_sort),
    "insertion": ("Insertion Sort",  insertion_sort),
    "shell":     ("Shell Sort",      shell_sort),
    "quick":     ("Quick Sort",      quick_sort),
    "merge":     ("Merge Sort",      merge_sort),
    "heap":      ("Heap Sort",       heap_sort),
    "cocktail":  ("Cocktail Sort",    cocktail_sort),
    "gnome":     ("Gnome Sort",      gnome_sort),
    "radix":     ("Radix Sort",      radix_sort),
}

DEFAULT_SET = ["bubble", "insertion", "quick", "merge", "heap"]


# ─── Race engine ─────────────────────────────────────────────────────────────

def run_race(algo_keys: List[str], size: int = 200, seed: Optional[int] = None):
    """Run a sorting race with the given algorithms and return results."""

    if seed is not None:
        random.seed(seed)
    base_data = list(range(1, size + 1))
    random.shuffle(base_data)

    algorithms = []
    for idx, key in enumerate(algo_keys):
        name, func = ALL_ALGORITHMS[key]
        color = ALGO_COLORS[idx % len(ALGO_COLORS)]
        data_copy = deepcopy(base_data)
        stats = SortStats()
        algo = Algorithm(name=name, func=func, color=color, stats=stats)
        algorithms.append((algo, data_copy))

    # Launch each sort in a thread
    finish_counter = [0]
    lock = threading.Lock()
    threads = []

    def sort_wrapper(algo: Algorithm, arr: List[int]):
        algo.stats.start_time = time.monotonic()
        algo.func(arr, algo.stats)
        algo.stats.end_time = time.monotonic()
        with lock:
            finish_counter[0] += 1
            algo.stats.finish_order = finish_counter[0]

    for algo, arr in algorithms:
        t = threading.Thread(target=sort_wrapper, args=(algo, arr))
        t.daemon = True
        threads.append(t)

    # Animation loop
    print(HIDE_CURSOR, end="", flush=True)
    try:
        start = time.monotonic()
        all_done = False
        while not all_done:
            elapsed = time.monotonic() - start
            all_done = all(a.stats.done for a, _ in algorithms)

            # Build display
            lines = []
            lines.append(f"{BOLD}{'═' * 70}{RESET}")
            lines.append(f"{BOLD}  🏁  SORTING ALGORITHM RACE  🏁{RESET}")
            lines.append(f"{BOLD}{'═' * 70}{RESET}")
            lines.append(f"  Array size: {size}  |  Elapsed: {elapsed:.2f}s")
            lines.append("")

            for algo, arr in algorithms:
                s = algo.stats
                c = algo.color
                status = ""
                if s.done:
                    medal = ["🥇", "🥈", "🥉"][s.finish_order - 1] if s.finish_order <= 3 else f"#{s.finish_order}"
                    dur = s.end_time - s.start_time
                    status = f"{GREEN}✓ Done {medal} ({dur:.4f}s){RESET}"
                else:
                    progress = min(1.0, s.steps / max(1, size * size // 4))
                    pb = bar(int(progress * 100), 100, width=20)
                    status = f"{DIM}⏳ Running {pb}{RESET}"

                lines.append(f"  {c}{BOLD}{algo.name:16s}{RESET}  {status}")
                lines.append(
                    f"    Comparisons: {s.comparisons:>8d}  |  "
                    f"Swaps: {s.swaps:>8d}  |  "
                    f"Accesses: {s.array_accesses:>8d}"
                )

                # Mini histogram
                snapshot = s.snapshot if s.snapshot else arr
                hist = mini_histogram(snapshot, width=50, height=3)
                for row in hist:
                    lines.append(f"    {c}{row}{RESET}")
                lines.append("")

            if all_done:
                lines.append(f"{BOLD}{'═' * 70}{RESET}")
                lines.append(f"{BOLD}  🏆  FINAL RESULTS  🏆{RESET}")
                lines.append(f"{BOLD}{'═' * 70}{RESET}")
                results = sorted(algorithms, key=lambda x: x[0].stats.finish_order)
                for rank, (algo, _) in enumerate(results, 1):
                    s = algo.stats
                    c = algo.color
                    dur = s.end_time - s.start_time
                    medal = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"#{rank}"
                    lines.append(
                        f"  {medal} {c}{BOLD}{algo.name:16s}{RESET}  "
                        f"Time: {dur:.4f}s  |  "
                        f"Comparisons: {s.comparisons:,}  |  "
                        f"Swaps: {s.swaps:,}"
                    )
                lines.append("")

            # Render
            output = CLEAR_SCREEN + "\n".join(lines)
            print(output, end="", flush=True)

            if not all_done:
                time.sleep(0.12)

        # Wait for threads
        for t in threads:
            t.join(timeout=5)

    finally:
        print(SHOW_CURSOR, end="", flush=True)

    return algorithms


# ─── Benchmark mode (no animation) ──────────────────────────────────────────

def run_benchmark(algo_keys: List[str], size: int = 1000, seed: Optional[int] = None, repeat: int = 1):
    """Run algorithms sequentially and print a comparison table."""
    if seed is not None:
        random.seed(seed)
    base_data = list(range(1, size + 1))
    random.shuffle(base_data)

    results = []
    for key in algo_keys:
        name, func = ALL_ALGORITHMS[key]
        total_time = 0.0
        total_comps = 0
        total_swaps = 0
        total_accesses = 0

        for _ in range(repeat):
            data_copy = deepcopy(base_data)
            stats = SortStats()
            start = time.monotonic()
            func(data_copy, stats)
            elapsed = time.monotonic() - start
            total_time += elapsed
            total_comps += stats.comparisons
            total_swaps += stats.swaps
            total_accesses += stats.array_accesses

        results.append({
            "key": key,
            "name": name,
            "time": total_time / repeat,
            "comparisons": total_comps // repeat,
            "swaps": total_swaps // repeat,
            "accesses": total_accesses // repeat,
        })

    # Sort by time
    results.sort(key=lambda r: r["time"])

    print(f"\n{BOLD}{'═' * 72}{RESET}")
    print(f"{BOLD}  🏁  SORTING BENCHMARK — {size} elements, {repeat} run(s)  🏁{RESET}")
    print(f"{BOLD}{'═' * 72}{RESET}\n")

    header = f"  {'Rank':<5} {'Algorithm':<18} {'Time':>10} {'Comps':>12} {'Swaps':>12} {'Accesses':>12}"
    print(f"{BOLD}{header}{RESET}")
    print(f"  {'─' * 68}")

    for rank, r in enumerate(results, 1):
        medal = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else "  "
        print(
            f"  {medal}{rank:<3} {r['name']:<18} "
            f"{r['time']:>10.4f}s "
            f"{r['comparisons']:>12,} "
            f"{r['swaps']:>12,} "
            f"{r['accesses']:>12,}"
        )

    print(f"\n  {DIM}Times are averages over {repeat} run(s).{RESET}\n")

    return results


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🏁 Sorting Algorithm Race — watch algorithms compete in real time!"
    )
    parser.add_argument(
        "-a", "--algorithms",
        nargs="+",
        default=DEFAULT_SET,
        choices=list(ALL_ALGORITHMS.keys()),
        help=f"Which algorithms to race. Choices: {', '.join(ALL_ALGORITHMS.keys())}. Default: %(default)s",
    )
    parser.add_argument(
        "-s", "--size",
        type=int,
        default=200,
        help="Size of the array to sort (default: 200)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run in benchmark mode (no animation, sequential, prints table)",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of repetitions in benchmark mode (default: 1)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Race all available algorithms",
    )

    args = parser.parse_args()

    if args.all:
        args.algorithms = list(ALL_ALGORITHMS.keys())

    if args.benchmark:
        run_benchmark(args.algorithms, size=args.size, seed=args.seed, repeat=args.repeat)
    else:
        run_race(args.algorithms, size=args.size, seed=args.seed)


if __name__ == "__main__":
    main()