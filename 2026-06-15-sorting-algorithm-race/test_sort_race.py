"""Tests for the Sorting Algorithm Race."""

import random
import pytest
from sort_race import (
    bubble_sort, selection_sort, insertion_sort, shell_sort,
    quick_sort, merge_sort, heap_sort, cocktail_sort, gnome_sort,
    radix_sort, SortStats, Algorithm, ALL_ALGORITHMS,
    run_benchmark, bar, mini_histogram,
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


def test_stats_tracking(random_arr, stats):
    """Bubble sort on 100 elements should produce known bounds of comparisons."""
    bubble_sort(random_arr, stats)
    # Bubble sort does n*(n-1)/2 comparisons = 4950
    assert stats.comparisons == 4950
    assert stats.swaps > 0
    assert stats.array_accesses > 0


def test_bubble_sort_swaps_on_reverse(reverse_arr):
    """Bubble sort on reverse-sorted array should have maximum swaps."""
    s = SortStats()
    bubble_sort(reverse_arr, s)
    # On reverse-sorted 100 elements: n*(n-1)/2 swaps = 4950
    assert s.swaps == 4950


def test_bar():
    assert bar(50, 100, width=10) == "█████░░░░░"
    assert bar(0, 100, width=10) == "░░░░░░░░░░"
    assert bar(100, 100, width=10) == "██████████"


def test_mini_histogram():
    data = list(range(10))
    hist = mini_histogram(data, width=5, height=3)
    assert len(hist) == 3
    assert all(len(row) == 5 for row in hist)


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


def test_all_algorithms_dict():
    """Verify ALL_ALGORITHMS dict has expected entries."""
    expected_keys = {"bubble", "selection", "insertion", "shell", "quick", "merge", "heap", "cocktail", "gnome", "radix"}
    assert set(ALL_ALGORITHMS.keys()) == expected_keys


def test_algorithm_dataclass():
    a = Algorithm(name="test", func=lambda x, s: None)
    assert a.name == "test"
    assert a.stats.comparisons == 0
    assert a.stats.done is False