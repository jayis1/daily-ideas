"""Tests for the Sorting Algorithm Race v2.0."""

import random
import json
import sys
import os
import subprocess
import pytest
from sort_race import (
    bubble_sort, selection_sort, insertion_sort, shell_sort,
    quick_sort, merge_sort, heap_sort, cocktail_sort, gnome_sort,
    radix_sort, tim_sort, SortStats, Algorithm, ALL_ALGORITHMS,
    ALGO_COMPLEXITY, run_race, run_benchmark, bar, mini_histogram,
    sortedness, list_algorithms, __version__,
)


@pytest.fixture
def random_arr():
    """Return a shuffled array of 1..100."""
    arr = list(range(1, 101))
    random.shuffle(arr)
    return arr


@pytest.fixture
def sorted_arr():
    return list(range(1, 101))


@pytest.fixture
def reverse_arr():
    return list(range(100, 0, -1))


@pytest.fixture
def stats():
    return SortStats()


# ─── Core sorting algorithm tests ────────────────────────────────────────────

def test_bubble_sort(random_arr, stats):
    bubble_sort(random_arr, stats)
    assert random_arr == list(range(1, 101))
    assert stats.done is True
    assert stats.comparisons > 0


def test_selection_sort(random_arr, stats):
    selection_sort(random_arr, stats)
    assert random_arr == list(range(1, 101))
    assert stats.done is True


def test_insertion_sort(random_arr, stats):
    insertion_sort(random_arr, stats)
    assert random_arr == list(range(1, 101))
    assert stats.done is True


def test_shell_sort(random_arr, stats):
    shell_sort(random_arr, stats)
    assert random_arr == list(range(1, 101))
    assert stats.done is True


def test_quick_sort(random_arr, stats):
    quick_sort(random_arr, stats)
    assert random_arr == list(range(1, 101))
    assert stats.done is True


def test_merge_sort(random_arr, stats):
    merge_sort(random_arr, stats)
    assert random_arr == list(range(1, 101))
    assert stats.done is True


def test_heap_sort(random_arr, stats):
    heap_sort(random_arr, stats)
    assert random_arr == list(range(1, 101))
    assert stats.done is True


def test_cocktail_sort(random_arr, stats):
    cocktail_sort(random_arr, stats)
    assert random_arr == list(range(1, 101))
    assert stats.done is True


def test_gnome_sort(random_arr, stats):
    gnome_sort(random_arr, stats)
    assert random_arr == list(range(1, 101))
    assert stats.done is True


def test_radix_sort(random_arr, stats):
    # Radix sort expects non-negative integers, so shift to 0-indexed
    arr = [x - 1 for x in random_arr]
    radix_sort(arr, stats)
    assert arr == list(range(100))
    assert stats.done is True


def test_tim_sort(random_arr, stats):
    """Tim Sort should correctly sort a random array."""
    tim_sort(random_arr, stats)
    assert random_arr == list(range(1, 101))
    assert stats.done is True


def test_tim_sort_large():
    """Tim Sort should correctly sort a larger array."""
    arr = list(range(1, 501))
    random.shuffle(arr)
    stats = SortStats()
    tim_sort(arr, stats)
    assert arr == list(range(1, 501))
    assert stats.done is True


def test_tim_sort_nearly_sorted():
    """Tim Sort should be efficient on nearly sorted data."""
    arr = list(range(1, 101))
    # Swap a few elements to make it nearly sorted
    arr[10], arr[20] = arr[20], arr[10]
    arr[50], arr[51] = arr[51], arr[50]
    stats = SortStats()
    tim_sort(arr, stats)
    assert arr == list(range(1, 101))
    assert stats.done is True


# ─── Edge case tests ────────────────────────────────────────────────────────

def test_empty_array(stats):
    for name, func in ALL_ALGORITHMS.values():
        arr = []
        func(arr, stats)
        assert arr == []


def test_single_element(stats):
    for name, func in ALL_ALGORITHMS.values():
        s = SortStats()
        arr = [42]
        func(arr, s)
        assert arr == [42]


def test_already_sorted(sorted_arr, stats):
    """Already sorted arrays should remain sorted."""
    for key, (name, func) in ALL_ALGORITHMS.items():
        if key == "radix":
            # Radix sort needs 0-indexed
            arr = [x - 1 for x in sorted_arr]
            s = SortStats()
            func(arr, s)
            assert arr == list(range(100))
        else:
            arr = list(sorted_arr)
            s = SortStats()
            func(arr, s)
            assert arr == sorted_arr


def test_reverse_sorted(reverse_arr, stats):
    """Reversely sorted arrays should be correctly sorted."""
    for key, (name, func) in ALL_ALGORITHMS.items():
        if key == "radix":
            arr = [x - 1 for x in reverse_arr]
            s = SortStats()
            func(arr, s)
            assert arr == list(range(100))
        else:
            arr = list(reverse_arr)
            s = SortStats()
            func(arr, s)
            assert arr == list(range(1, 101))


def test_two_elements(stats):
    """All algorithms should handle 2-element arrays."""
    for key, (name, func) in ALL_ALGORITHMS.items():
        s = SortStats()
        if key == "radix":
            arr = [5, 2]
            func(arr, s)
            assert arr == [2, 5]
        else:
            arr = [5, 2]
            func(arr, s)
            assert arr == [2, 5]
        s2 = SortStats()
        if key == "radix":
            arr2 = [2, 5]
            func(arr2, s2)
            assert arr2 == [2, 5]
        else:
            arr2 = [2, 5]
            func(arr2, s2)
            assert arr2 == [2, 5]


def test_duplicate_elements(stats):
    """All algorithms should handle arrays with duplicate values."""
    arr_template = [3, 1, 2, 1, 3, 2, 1, 2, 3]
    for key, (name, func) in ALL_ALGORITHMS.items():
        if key == "radix":
            arr = list(arr_template)
            s = SortStats()
            func(arr, s)
            assert arr == sorted(arr_template), f"{name} failed on duplicates"
        else:
            arr = list(arr_template)
            s = SortStats()
            func(arr, s)
            assert arr == sorted(arr_template), f"{name} failed on duplicates"


# ─── Stats tracking tests ───────────────────────────────────────────────────

def test_stats_tracking(random_arr, stats):
    """Bubble sort on 100 elements should produce known bounds of comparisons."""
    bubble_sort(random_arr, stats)
    # Bubble sort does at most n*(n-1)/2 comparisons = 4950
    # With early termination, it may do fewer
    assert stats.comparisons <= 4950
    assert stats.swaps > 0
    assert stats.array_accesses > 0


def test_bubble_sort_swaps_on_reverse(reverse_arr):
    """Bubble sort on reverse-sorted array should have maximum swaps."""
    s = SortStats()
    bubble_sort(reverse_arr, s)
    # On reverse-sorted 100 elements: n*(n-1)/2 swaps = 4950
    assert s.swaps == 4950


def test_bubble_sort_early_termination():
    """Bubble sort should terminate early on already-sorted data."""
    arr = list(range(100))
    s = SortStats()
    bubble_sort(arr, s)
    # With early termination, only 1 pass needed: n-1 comparisons = 99
    assert s.comparisons == 99
    assert s.swaps == 0


# ─── Utility function tests ──────────────────────────────────────────────────

def test_bar():
    assert bar(50, 100, width=10) == "█████░░░░░"
    assert bar(0, 100, width=10) == "░░░░░░░░░░"
    assert bar(100, 100, width=10) == "██████████"
    assert bar(150, 100, width=10) == "██████████"  # clamped


def test_bar_zero_max():
    """bar() should handle max_val=0 gracefully."""
    assert bar(5, 0, width=10) == "░░░░░░░░░░"


def test_mini_histogram():
    data = list(range(10))
    hist = mini_histogram(data, width=5, height=3)
    assert len(hist) == 3
    assert all(len(row) == 5 for row in hist)


def test_mini_histogram_empty():
    """mini_histogram on empty data should return blank rows."""
    hist = mini_histogram([], width=5, height=3)
    assert len(hist) == 3
    assert all(row == " " * 5 for row in hist)


def test_sortedness_perfectly_sorted():
    """sortedness() should return 1.0 for a sorted array."""
    assert sortedness([1, 2, 3, 4, 5]) == 1.0


def test_sortedness_fully_reversed():
    """sortedness() should return 0.0 for a fully reversed array."""
    assert sortedness([5, 4, 3, 2, 1]) == 0.0


def test_sortedness_empty():
    """sortedness() should return 1.0 for empty array."""
    assert sortedness([]) == 1.0


def test_sortedness_single():
    """sortedness() should return 1.0 for single-element array."""
    assert sortedness([42]) == 1.0


def test_sortedness_partial():
    """sortedness() should return 0.5 for half-sorted array."""
    # [1, 3, 2, 4]: pairs (1,3)=ok, (3,2)=no, (2,4)=ok -> 2/3 ≈ 0.667
    result = sortedness([1, 3, 2, 4])
    assert abs(result - 2/3) < 0.01


# ─── Benchmark mode tests ────────────────────────────────────────────────────

def test_benchmark_mode():
    """Test that benchmark mode runs and returns results."""
    results = run_benchmark(["bubble", "insertion"], size=50, seed=42, repeat=1)
    assert len(results) == 2
    # Results should be sorted by time
    assert results[0]["time"] <= results[1]["time"]
    for r in results:
        assert "name" in r
        assert "time" in r
        assert "comparisons" in r
        assert "swaps" in r


def test_benchmark_reproducible():
    """Same seed should give same results."""
    r1 = run_benchmark(["bubble"], size=50, seed=123, repeat=1)
    r2 = run_benchmark(["bubble"], size=50, seed=123, repeat=1)
    assert r1[0]["comparisons"] == r2[0]["comparisons"]


def test_benchmark_with_tim_sort():
    """Tim Sort should work in benchmark mode."""
    results = run_benchmark(["tim", "merge", "quick"], size=100, seed=42, repeat=1)
    assert len(results) == 3
    for r in results:
        assert r["time"] > 0


def test_benchmark_export_json():
    """Benchmark JSON export should produce valid JSON."""
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        run_benchmark(["bubble", "insertion"], size=50, seed=42, repeat=1, export_format="json")
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    data = json.loads(output)
    assert "benchmark" in data
    assert "results" in data
    assert data["benchmark"]["size"] == 50
    assert len(data["results"]) == 2


def test_benchmark_export_csv():
    """Benchmark CSV export should produce valid CSV."""
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        run_benchmark(["bubble", "insertion"], size=50, seed=42, repeat=1, export_format="csv")
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout
    lines = output.strip().split("\n")
    assert len(lines) >= 3  # header + 2 data rows
    assert "rank" in lines[0]
    assert "name" in lines[0]


# ─── Algorithm registry tests ───────────────────────────────────────────────

def test_all_algorithms_dict():
    """Verify ALL_ALGORITHMS dict has expected entries including tim."""
    expected_keys = {"bubble", "selection", "insertion", "shell", "quick", "merge",
                     "heap", "cocktail", "gnome", "radix", "tim"}
    assert set(ALL_ALGORITHMS.keys()) == expected_keys


def test_algo_complexity_dict():
    """ALGO_COMPLEXITY should have an entry for every algorithm."""
    assert set(ALGO_COMPLEXITY.keys()) == set(ALL_ALGORITHMS.keys())


def test_algo_complexity_fields():
    """Each complexity entry should have 5 fields: best, avg, worst, space, stable."""
    for key, (best, avg, worst, space, stable) in ALGO_COMPLEXITY.items():
        assert isinstance(best, str), f"{key}: best should be str"
        assert isinstance(avg, str), f"{key}: avg should be str"
        assert isinstance(worst, str), f"{key}: worst should be str"
        assert isinstance(space, str), f"{key}: space should be str"
        assert isinstance(stable, bool), f"{key}: stable should be bool"


def test_algorithm_dataclass():
    a = Algorithm(name="test", func=lambda x, s: None)
    assert a.name == "test"
    assert a.stats.comparisons == 0
    assert a.stats.done is False


# ─── Version tests ──────────────────────────────────────────────────────────

def test_version_is_string():
    assert isinstance(__version__, str)


def test_version_format():
    """Version should be in semver format."""
    parts = __version__.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


# ─── CLI tests ───────────────────────────────────────────────────────────────

SCRIPT = os.path.join(os.path.dirname(__file__), "sort_race.py")


def test_cli_version():
    """--version flag should work."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--version"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert __version__ in result.stdout


def test_cli_help():
    """--help flag should work."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--help"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Sorting Algorithm Race" in result.stdout


def test_cli_list():
    """--list flag should show algorithm table and exit."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--list"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Bubble Sort" in result.stdout
    assert "Tim Sort" in result.stdout
    assert "Stable" in result.stdout


def test_cli_invalid_size():
    """--size 0 should be rejected."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--size", "0", "-a", "bubble", "--benchmark"],
        capture_output=True, text=True
    )
    assert result.returncode != 0


def test_cli_negative_size():
    """Negative --size should be rejected."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--size", "-5", "-a", "bubble", "--benchmark"],
        capture_output=True, text=True
    )
    assert result.returncode != 0


def test_cli_invalid_repeat():
    """--repeat 0 should be rejected."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--benchmark", "--repeat", "0", "-a", "bubble"],
        capture_output=True, text=True
    )
    assert result.returncode != 0


def test_cli_export_without_benchmark():
    """--export without --benchmark should be rejected."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--export", "json", "-a", "bubble"],
        capture_output=True, text=True
    )
    assert result.returncode != 0


def test_cli_benchmark_runs():
    """Benchmark mode should run and produce output."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--benchmark", "-a", "bubble", "insertion",
         "--size", "50", "--seed", "42"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Bubble Sort" in result.stdout
    assert "Insertion Sort" in result.stdout


def test_cli_benchmark_json_export():
    """Benchmark with --export json should produce valid JSON."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--benchmark", "-a", "bubble",
         "--size", "50", "--seed", "42", "--export", "json"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "results" in data


def test_cli_benchmark_csv_export():
    """Benchmark with --export csv should produce valid CSV."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--benchmark", "-a", "bubble", "insertion",
         "--size", "50", "--seed", "42", "--export", "csv"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    lines = result.stdout.strip().split("\n")
    assert len(lines) >= 3


def test_cli_no_animation():
    """--no-animation mode should produce results without live animation."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "-a", "bubble", "insertion",
         "--size", "50", "--seed", "42", "--no-animation"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Bubble Sort" in result.stdout


def test_cli_detailed_benchmark():
    """--detailed flag should add Accesses column to benchmark output."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--benchmark", "-a", "bubble",
         "--size", "50", "--seed", "42", "--detailed"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "Accesses" in result.stdout


def test_cli_detailed_without_benchmark():
    """--detailed without --benchmark should be rejected."""
    result = subprocess.run(
        [sys.executable, SCRIPT, "--detailed", "-a", "bubble"],
        capture_output=True, text=True
    )
    assert result.returncode != 0


# ─── Bug fix regression tests ──────────────────────────────────────────────────

def test_radix_sort_rejects_negatives():
    """Radix sort should raise ValueError on arrays with negative numbers."""
    s = SortStats()
    with pytest.raises(ValueError, match="non-negative"):
        radix_sort([-5, 3, -1, 10, 7], s)


def test_radix_sort_accepts_zero():
    """Radix sort should handle zero correctly."""
    s = SortStats()
    arr = [0, 5, 3, 10, 1]
    radix_sort(arr, s)
    assert arr == [0, 1, 3, 5, 10]
    assert s.done is True


def test_quick_sort_sorted_large():
    """Quick sort should handle sorted arrays without RecursionError.

    Previously used recursive Lomuto partition which hit Python's recursion
    limit on sorted arrays. Now uses iterative approach with median-of-three.
    """
    s = SortStats()
    arr = list(range(2000))
    quick_sort(arr, s)
    assert arr == list(range(2000))
    assert s.done is True


def test_quick_sort_reverse_sorted_large():
    """Quick sort should handle reverse-sorted arrays without RecursionError."""
    s = SortStats()
    arr = list(range(2000, 0, -1))
    quick_sort(arr, s)
    assert arr == list(range(1, 2001))
    assert s.done is True


def test_quick_sort_deduplicates():
    """Quick sort with median-of-three should correctly sort arrays with duplicates."""
    s = SortStats()
    arr = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
    quick_sort(arr, s)
    assert arr == sorted([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5])
    assert s.done is True


def test_quick_sort_small_arrays():
    """Quick sort with median-of-three should handle edge cases: empty, single, two elements."""
    s1 = SortStats()
    arr1 = []
    quick_sort(arr1, s1)
    assert arr1 == []
    assert s1.done is True

    s2 = SortStats()
    arr2 = [42]
    quick_sort(arr2, s2)
    assert arr2 == [42]
    assert s2.done is True

    s3 = SortStats()
    arr3 = [5, 2]
    quick_sort(arr3, s3)
    assert arr3 == [2, 5]
    assert s3.done is True

    s4 = SortStats()
    arr4 = [2, 5]
    quick_sort(arr4, s4)
    assert arr4 == [2, 5]
    assert s4.done is True


def test_race_no_animation_all_correct():
    """Race mode with --no-animation should produce correct results for all algorithms."""
    results = run_race(list(ALL_ALGORITHMS.keys()), size=100, seed=42, no_animation=True)
    sorted_ref = sorted(list(range(1, 101)))
    for algo, arr in results:
        assert arr == sorted_ref, f"{algo.name} produced incorrect output in race mode"