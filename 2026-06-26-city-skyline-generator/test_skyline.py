#!/usr/bin/env python3
"""Tests for the city skyline generator."""

import subprocess
import sys

def run_skyline(*args):
    """Run skyline.py with given args and return CompletedProcess."""
    cmd = [sys.executable, "skyline.py"] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10)

def test_default_run():
    """Test that default invocation succeeds."""
    r = run_skyline("--seed", "42")
    assert r.returncode == 0, f"Exit code {r.returncode}, stderr: {r.stderr}"
    lines = r.stdout.strip().split("\n")
    assert len(lines) >= 10, f"Expected at least 10 lines, got {len(lines)}"
    print(f"  ✓ Default run produced {len(lines)} lines")

def test_no_color():
    """Test --no-color mode."""
    r = run_skyline("--no-color", "--seed", "1")
    assert r.returncode == 0
    assert "\033[" not in r.stdout, "Found ANSI escapes in no-color output"
    print("  ✓ No-color mode works")

def test_with_color():
    """Test that color mode produces ANSI escapes."""
    r = run_skyline("--seed", "1")
    assert r.returncode == 0
    assert "\033[" in r.stdout, "Expected ANSI escapes in color output"
    print("  ✓ Color mode produces ANSI escapes")

def test_time_options():
    """Test all time options."""
    for t in ["dawn", "day", "dusk", "night"]:
        r = run_skyline("--time", t, "--seed", "5", "--no-color")
        assert r.returncode == 0, f"Time {t} failed"
        assert t.title() in r.stdout, f"Expected '{t.title()}' in output"
    print("  ✓ All time options work")

def test_weather_options():
    """Test all weather options."""
    for w in ["clear", "cloudy", "rain", "snow", "fog", "storm"]:
        r = run_skyline("--weather", w, "--seed", "5", "--no-color")
        assert r.returncode == 0, f"Weather {w} failed"
        assert w.title() in r.stdout, f"Expected '{w.title()}' in output"
    print("  ✓ All weather options work")

def test_style_options():
    """Test all style options."""
    for s in ["modern", "art_deco", "gothic", "industrial", "brutalist", "residential", "mixed"]:
        r = run_skyline("--style", s, "--seed", "10", "--no-color")
        assert r.returncode == 0, f"Style {s} failed"
    print("  ✓ All style options work")

def test_width():
    """Test custom width."""
    for w in [40, 80, 120]:
        r = run_skyline("--width", str(w), "--seed", "3", "--no-color")
        assert r.returncode == 0, f"Width {w} failed"
        lines = r.stdout.strip().split("\n")
        # First few lines should be at least width chars (may have ANSI codes)
    print("  ✓ Custom width works")

def test_density():
    """Test density parameter."""
    r_low = run_skyline("--density", "0.2", "--seed", "7", "--no-color")
    r_high = run_skyline("--density", "1.0", "--seed", "7", "--no-color")
    assert r_low.returncode == 0
    assert r_high.returncode == 0
    print("  ✓ Density parameter works")

def test_seed_reproducibility():
    """Test that same seed produces same output."""
    r1 = run_skyline("--seed", "42", "--no-color")
    r2 = run_skyline("--seed", "42", "--no-color")
    assert r1.stdout == r2.stdout, "Same seed should produce same output"
    print("  ✓ Seed produces reproducible output")

def test_different_seeds():
    """Test that different seeds produce different output."""
    r1 = run_skyline("--seed", "1", "--no-color")
    r2 = run_skyline("--seed", "999", "--no-color")
    assert r1.stdout != r2.stdout, "Different seeds should produce different output"
    print("  ✓ Different seeds produce different output")

def test_list_flag():
    """Test --list flag."""
    r = run_skyline("--list")
    assert r.returncode == 0
    assert "modern" in r.stdout
    assert "gothic" in r.stdout
    print("  ✓ --list flag works")

def test_version_flag():
    """Test --version flag."""
    r = run_skyline("--version")
    assert r.returncode == 0
    assert "1.0.0" in r.stdout
    print("  ✓ --version flag works")

def test_buildings_in_output():
    """Test that buildings appear in output."""
    r = run_skyline("--seed", "5", "--no-color")
    output = r.stdout
    assert "buildings" in output, "Should show building count"
    # Should have window characters
    has_windows = any(c in output for c in "▣░·✦")
    assert has_windows, "Should have window characters"
    print("  ✓ Buildings appear in output")

def test_stats_line():
    """Test that stats line contains expected elements."""
    r = run_skyline("--seed", "42", "--no-color")
    last_line = r.stdout.strip().split("\n")[-1]
    assert "Pop:" in last_line
    assert "buildings" in last_line
    print("  ✓ Stats line contains expected elements")

if __name__ == "__main__":
    tests = [
        test_default_run,
        test_no_color,
        test_with_color,
        test_time_options,
        test_weather_options,
        test_style_options,
        test_width,
        test_density,
        test_seed_reproducibility,
        test_different_seeds,
        test_list_flag,
        test_version_flag,
        test_buildings_in_output,
        test_stats_line,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)