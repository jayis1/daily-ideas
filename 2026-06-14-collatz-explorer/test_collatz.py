#!/usr/bin/env python3
"""Tests for the Collatz Conjecture Explorer (v1.1.0)."""

import sys
import os
import subprocess
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collatz_explorer import (
    collatz_sequence,
    collatz_steps,
    collatz_max,
    collatz_stats,
    reverse_collatz_tree,
    render_sequence,
    render_path,
    render_histogram,
    render_tree,
    render_batch,
    render_hailstone,
    render_converge,
    render_density,
    render_stats,
    color,
    __version__,
)

# ── Core Collatz tests ──────────────────────────────────────────────────────

def test_collatz_sequence_basic():
    """Test basic Collatz sequence generation."""
    assert collatz_sequence(1) == [1]
    assert collatz_sequence(2) == [2, 1]
    assert collatz_sequence(3) == [3, 10, 5, 16, 8, 4, 2, 1]
    assert collatz_sequence(4) == [4, 2, 1]
    assert collatz_sequence(6) == [6, 3, 10, 5, 16, 8, 4, 2, 1]
    print("✓ test_collatz_sequence_basic")


def test_collatz_sequence_famous():
    """Test the famous n=27 sequence (111 steps, peaks at 9232)."""
    seq = collatz_sequence(27)
    assert len(seq) == 112  # 111 steps + starting value
    assert max(seq) == 9232
    assert seq[-1] == 1
    print("✓ test_collatz_sequence_famous")


def test_collatz_sequence_invalid():
    """Test that invalid inputs raise ValueError."""
    try:
        collatz_sequence(0)
        assert False, "Should raise ValueError for n=0"
    except ValueError:
        pass
    try:
        collatz_sequence(-5)
        assert False, "Should raise ValueError for negative n"
    except ValueError:
        pass
    print("✓ test_collatz_sequence_invalid")


def test_collatz_steps():
    """Test the collatz_steps function with memoization."""
    assert collatz_steps(1) == 0
    assert collatz_steps(2) == 1
    assert collatz_steps(3) == 7
    assert collatz_steps(4) == 2
    assert collatz_steps(7) == 16
    assert collatz_steps(27) == 111
    print("✓ test_collatz_steps")


def test_collatz_steps_consistency():
    """Verify collatz_steps agrees with collatz_sequence length."""
    for n in range(1, 50):
        seq = collatz_sequence(n)
        steps = collatz_steps(n)
        assert steps == len(seq) - 1, f"n={n}: steps={steps} but seq len={len(seq)-1}"
    print("✓ test_collatz_steps_consistency")


def test_collatz_steps_invalid():
    """Test that collatz_steps raises ValueError for invalid input."""
    try:
        collatz_steps(0)
        assert False, "Should raise ValueError for n=0"
    except ValueError:
        pass
    print("✓ test_collatz_steps_invalid")


def test_collatz_max():
    """Test the collatz_max function."""
    assert collatz_max(1) == 1
    assert collatz_max(2) == 2
    assert collatz_max(3) == 16
    assert collatz_max(7) == 52
    assert collatz_max(27) == 9232
    print("✓ test_collatz_max")


def test_collatz_max_consistency():
    """Verify collatz_max agrees with max(collatz_sequence)."""
    for n in range(1, 30):
        seq = collatz_sequence(n)
        peak = collatz_max(n)
        assert peak == max(seq), f"n={n}: collatz_max={peak} but max(seq)={max(seq)}"
    print("✓ test_collatz_max_consistency")


def test_collatz_max_invalid():
    """Test that collatz_max raises ValueError for invalid input."""
    try:
        collatz_max(0)
        assert False, "Should raise ValueError for n=0"
    except ValueError:
        pass
    print("✓ test_collatz_max_invalid")


def test_collatz_stats():
    """Test the collatz_stats function."""
    stats = collatz_stats(27)
    assert stats["steps"] == 111
    assert stats["peak"] == 9232
    assert stats["growth_factor"] == 9232 / 27
    assert stats["odd_ops"] > 0
    assert stats["even_ops"] > 0
    assert stats["reaches_1"] is True
    print("✓ test_collatz_stats")


def test_collatz_stats_powers_of_2():
    """Test stats for powers of 2 (should have only even operations)."""
    stats = collatz_stats(8)
    assert stats["steps"] == 3  # 8 -> 4 -> 2 -> 1
    assert stats["odd_ops"] == 0
    assert stats["even_ops"] == 3
    assert stats["odd_even_ratio"] == float("inf")
    print("✓ test_collatz_stats_powers_of_2")


def test_collatz_stats_invalid():
    """Test that collatz_stats raises ValueError for invalid input."""
    try:
        collatz_stats(0)
        assert False, "Should raise ValueError"
    except ValueError:
        pass
    print("✓ test_collatz_stats_invalid")


# ── Reverse tree tests ────────────────────────────────────────────────────

def test_reverse_tree_basic():
    """Test basic reverse Collatz tree from 1."""
    layers = reverse_collatz_tree(1, 3)
    assert 0 in layers
    assert layers[0] == [1]
    # Step 1: 1*2=2, and (1-1)/3=0 which is not >1, so only 2
    assert 2 in layers[1]
    assert 2 in layers[1]
    print("✓ test_reverse_tree_basic")


def test_reverse_tree_depth():
    """Test tree with various depths."""
    layers = reverse_collatz_tree(1, 1)
    assert len(layers) >= 1
    layers = reverse_collatz_tree(1, 5)
    total = sum(len(v) for v in layers.values())
    assert total > 5  # Should have more than just the root
    print("✓ test_reverse_tree_depth")


def test_reverse_tree_invalid():
    """Test that invalid inputs raise ValueError."""
    try:
        reverse_collatz_tree(0, 5)
        assert False, "Should raise ValueError for target=0"
    except ValueError:
        pass
    try:
        reverse_collatz_tree(1, 0)
        assert False, "Should raise ValueError for depth=0"
    except ValueError:
        pass
    print("✓ test_reverse_tree_invalid")


# ── Rendering tests ──────────────────────────────────────────────────────

def test_render_sequence():
    """Test that sequence rendering produces output without crashing."""
    output = render_sequence(7)
    assert len(output) > 0
    assert "7" in output
    assert "Steps" in output or "steps" in output
    print("✓ test_render_sequence")


def test_render_sequence_truncation():
    """Test that long sequences are properly truncated."""
    # n=27 has 112 elements, truncation at 50 should show "more steps"
    output = render_sequence(27, max_display=20)
    assert "more steps" in output
    print("✓ test_render_sequence_truncation")


def test_render_path():
    """Test path rendering."""
    output = render_path(27)
    assert len(output) > 0
    assert "27" in output
    print("✓ test_render_path")


def test_render_path_short():
    """Test path rendering for very short sequences."""
    output = render_path(1)
    assert "Too short" in output
    print("✓ test_render_path_short")


def test_render_histogram():
    """Test histogram rendering."""
    output = render_histogram(27)
    assert len(output) > 0
    assert "Histogram" in output
    print("✓ test_render_histogram")


def test_render_histogram_short():
    """Test histogram for very short sequences."""
    output = render_histogram(2)
    assert "Too short" in output
    print("✓ test_render_histogram_short")


def test_render_tree():
    """Test tree rendering."""
    output = render_tree(1, 5)
    assert len(output) > 0
    assert "1" in output
    print("✓ test_render_tree")


def test_render_batch():
    """Test batch rendering."""
    output = render_batch(1, 10)
    assert len(output) > 0
    assert "Batch Statistics" in output
    assert "Average" in output
    print("✓ test_render_batch")


def test_render_batch_reversed_range():
    """Test batch with end < start (should auto-swap)."""
    output = render_batch(10, 1)
    assert "n ∈ [1, 10]" in output
    print("✓ test_render_batch_reversed_range")


def test_render_hailstone():
    """Test hailstone rendering."""
    output = render_hailstone(27)
    assert len(output) > 0
    assert "27" in output
    assert "Growth factor" in output
    print("✓ test_render_hailstone")


def test_render_hailstone_trivial():
    """Test hailstone for n=1 (trivial sequence)."""
    output = render_hailstone(1)
    assert "Trivial" in output
    print("✓ test_render_hailstone_trivial")


def test_render_converge():
    """Test convergence speed rendering."""
    output = render_converge(1, 20)
    assert len(output) > 0
    assert "Convergence" in output
    print("✓ test_render_converge")


def test_render_converge_reversed():
    """Test convergence with reversed range."""
    output = render_converge(20, 1)
    assert "[1, 20]" in output
    print("✓ test_render_converge_reversed")


def test_render_density():
    """Test density map rendering."""
    output = render_density(1, 20)
    assert len(output) > 0
    assert "Density" in output
    print("✓ test_render_density")


def test_render_density_reversed():
    """Test density with reversed range."""
    output = render_density(20, 1)
    assert "[1, 20]" in output
    print("✓ test_render_density_reversed")


def test_render_stats():
    """Test statistics rendering."""
    output = render_stats(27)
    assert len(output) > 0
    assert "Statistics" in output
    assert "111" in output  # steps
    assert "9,232" in output or "9232" in output  # peak
    print("✓ test_render_stats")


def test_render_stats_growth_factor():
    """Test that growth factor is shown in stats."""
    output = render_stats(7)
    assert "Growth factor" in output
    print("✓ test_render_stats_growth_factor")


# ── Color tests ──────────────────────────────────────────────────────────

def test_color_function():
    """Test the color function."""
    # When colors are disabled (which they are in test mode), just returns text
    result = color("red", "hello")
    assert "hello" in result
    print("✓ test_color_function")


# ── Version test ──────────────────────────────────────────────────────────

def test_version():
    """Test that version is set and follows semver."""
    assert __version__ is not None
    parts = __version__.split(".")
    assert len(parts) == 3, f"Version should be semver, got {__version__}"
    assert parts[0] == "1"
    assert parts[1] == "1"
    assert parts[2] == "0"
    print("✓ test_version")


# ── CLI tests ──────────────────────────────────────────────────────────

def test_cli_version():
    """Test the --version flag."""
    result = subprocess.run(
        [sys.executable, "collatz_explorer.py", "--version"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    assert "1.1.0" in (result.stdout + result.stderr), f"Version should be in output"
    print("✓ test_cli_version")


def test_cli_help():
    """Test the --help flag includes new options."""
    result = subprocess.run(
        [sys.executable, "collatz_explorer.py", "--help"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    output = result.stdout
    assert "--version" in output
    assert "--export" in output
    assert "converge" in output
    assert "density" in output
    assert "stats" in output
    print("✓ test_cli_help")


def test_cli_hailstone():
    """Test hailstone mode from CLI."""
    result = subprocess.run(
        [sys.executable, "collatz_explorer.py", "-n", "7", "--mode", "hailstone", "--no-color"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    assert result.returncode == 0
    assert "7" in result.stdout
    print("✓ test_cli_hailstone")


def test_cli_sequence():
    """Test sequence mode from CLI."""
    result = subprocess.run(
        [sys.executable, "collatz_explorer.py", "-n", "3", "--mode", "sequence", "--no-color"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    assert result.returncode == 0
    assert "3" in result.stdout
    print("✓ test_cli_sequence")


def test_cli_stats():
    """Test stats mode from CLI."""
    result = subprocess.run(
        [sys.executable, "collatz_explorer.py", "-n", "27", "--mode", "stats", "--no-color"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    assert result.returncode == 0
    assert "Statistics" in result.stdout
    print("✓ test_cli_stats")


def test_cli_export():
    """Test --export flag saves output to a file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        tmpfile = f.name
    try:
        result = subprocess.run(
            [sys.executable, "collatz_explorer.py", "-n", "7", "--mode", "sequence", "--no-color", "--export", tmpfile],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        assert result.returncode == 0
        with open(tmpfile) as f:
            content = f.read()
        assert "7" in content
    finally:
        os.unlink(tmpfile)
    print("✓ test_cli_export")


def test_cli_converge():
    """Test converge mode from CLI."""
    result = subprocess.run(
        [sys.executable, "collatz_explorer.py", "--converge", "1", "20", "--no-color"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    assert result.returncode == 0
    assert "Convergence" in result.stdout
    print("✓ test_cli_converge")


def test_cli_density():
    """Test density mode from CLI."""
    result = subprocess.run(
        [sys.executable, "collatz_explorer.py", "--density", "1", "20", "--no-color"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    assert result.returncode == 0
    assert "Density" in result.stdout
    print("✓ test_cli_density")


def test_cli_invalid_n():
    """Test that invalid n values produce an error."""
    result = subprocess.run(
        [sys.executable, "collatz_explorer.py", "-n", "0", "--mode", "hailstone"],
        capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    assert result.returncode != 0
    print("✓ test_cli_invalid_n")


# ── Edge case tests ────────────────────────────────────────────────────

def test_sequence_n_1():
    """Test that n=1 produces a trivial sequence."""
    seq = collatz_sequence(1)
    assert seq == [1]
    assert collatz_steps(1) == 0
    assert collatz_max(1) == 1
    print("✓ test_sequence_n_1")


def test_sequence_n_2():
    """Test that n=2 produces the simplest non-trivial sequence."""
    seq = collatz_sequence(2)
    assert seq == [2, 1]
    print("✓ test_sequence_n_2")


def test_render_stats_n_1():
    """Test stats rendering for n=1."""
    output = render_stats(1)
    assert "1" in output
    assert "0" in output  # 0 steps
    print("✓ test_render_stats_n_1")


def test_memoized_steps_large_n():
    """Test that memoized steps works for larger numbers."""
    # n=871: known to have 178 steps
    steps = collatz_steps(871)
    assert steps == 178
    print("✓ test_memoized_steps_large_n")


# ── Run all tests ──────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [obj for name, obj in sorted(globals().items())
             if name.startswith("test_") and callable(obj)]

    passed = 0
    failed = 0
    errors = []

    for test in tests:
        name = test.__name__
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
            errors.append((name, str(e)))
        except Exception as e:
            print(f"  ✗ {name}: ERROR: {e}")
            failed += 1
            errors.append((name, f"ERROR: {e}"))

    print(f"\n  Results: {passed} passed, {failed} failed out of {len(tests)} tests")

    if errors:
        print("\n  Failed tests:")
        for name, err in errors:
            print(f"    - {name}: {err}")

    sys.exit(0 if failed == 0 else 1)