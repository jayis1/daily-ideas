#!/usr/bin/env python3
"""Tests for the ASCII stereogram generator.

Run with:
    python3 test_stereogram.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stereogram  # noqa: E402


# --------------------------------------------------------------------------- #
# Depth-map generators                                                        #
# --------------------------------------------------------------------------- #

def test_depth_sphere_bounds():
    grid = stereogram.depth_sphere(72, 24)
    assert len(grid) == 24
    assert all(len(row) == 72 for row in grid)
    # Center pixel should be near max depth (closest to viewer).
    assert grid[12][36] > 0.9
    # All values in [0, 1].
    for row in grid:
        for v in row:
            assert 0.0 <= v <= 1.0


def test_depth_all_patterns_run():
    """Every non-text pattern should produce a correctly-sized grid in range."""
    for name, fn in stereogram.PATTERNS.items():
        grid = fn(40, 12)
        assert len(grid) == 12, f"{name}: wrong height"
        assert all(len(row) == 40 for row in grid), f"{name}: wrong width"
        for row in grid:
            for v in row:
                assert 0.0 <= v <= 1.0, f"{name}: value out of range"


def test_depth_text():
    grid = stereogram.depth_text("A", 20, 10)
    assert len(grid) == 10
    assert all(len(r) == 20 for r in grid)
    # At least one pixel should be 1.0 (the glyph A is not blank).
    assert any(v == 1.0 for row in grid for v in row)


def test_depth_text_empty():
    """An empty text string should yield an all-zero depth map (no crash)."""
    grid = stereogram.depth_text("", 20, 10)
    assert all(v == 0.0 for row in grid for v in row)


def test_depth_random_reproducible():
    """Same seed should yield identical random patterns."""
    import random
    r1 = random.Random(123)
    r2 = random.Random(123)
    a = stereogram.depth_random(40, 12, rng=r1)
    b = stereogram.depth_random(40, 12, rng=r2)
    assert a == b


def test_new_patterns_have_depth():
    """The newly added patterns should not be entirely empty."""
    for name in ("diamond", "spiral", "tunnel"):
        grid = stereogram.PATTERNS[name](50, 20)
        assert any(v > 0.0 for row in grid for v in row), \
            f"{name}: no depth produced"


# --------------------------------------------------------------------------- #
# Renderer                                                                    #
# --------------------------------------------------------------------------- #

def test_render_dimensions():
    depth = stereogram.depth_sphere(60, 20)
    out = stereogram.render_stereogram(depth, 60, 20)
    lines = out.split("\n")
    assert len(lines) == 20
    assert all(len(line) == 60 for line in lines)


def test_render_reproducible_with_seed():
    """Same seed -> identical stereogram."""
    import random
    depth = stereogram.depth_sphere(50, 10)
    r1 = random.Random(7)
    r2 = random.Random(7)
    a = stereogram.render_stereogram(depth, 50, 10, rng=r1)
    b = stereogram.render_stereogram(depth, 50, 10, rng=r2)
    assert a == b


def test_render_flat_is_random():
    """A flat (zero) depth map should still produce full-width rows of noise."""
    depth = stereogram._empty(30, 5)
    out = stereogram.render_stereogram(depth, 30, 5)
    lines = out.split("\n")
    assert len(lines) == 5
    for line in lines:
        assert len(line) == 30
        # No empty chars.
        assert all(c != "" for c in line)


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def test_invert_depth():
    grid = stereogram.depth_sphere(30, 10)
    inv = stereogram.invert_depth(grid, 30, 10)
    for y in range(10):
        for x in range(30):
            assert abs((grid[y][x] + inv[y][x]) - 1.0) < 1e-9


def test_render_depth_map_uses_ramp():
    depth = stereogram.depth_sphere(40, 12)
    out = stereogram.render_depth_map(depth, 40, 12)
    # Every output character (excluding row separators) should be a valid
    # ramp character.
    allowed = set(stereogram.RAMP)
    for line in out.split("\n"):
        for ch in line:
            assert ch in allowed, f"unexpected char {ch!r} in depth map"


def test_render_depth_map_negative_clamped():
    """Negative depth values must clamp to RAMP[0] (' '), not wrap around."""
    depth = [[-0.5] * 10 for _ in range(3)]
    out = stereogram.render_depth_map(depth, 10, 3)
    for line in out.split("\n"):
        assert line == " " * 10, f"negative depth should be all spaces, got {line!r}"


def test_alignment_guide_markers():
    guide = stereogram.alignment_guide(50, 14)
    assert len(guide) == 50
    # Exactly two '|' markers.
    assert guide.count("|") == 2
    # Markers separated by eye_sep.
    positions = [i for i, c in enumerate(guide) if c == "|"]
    assert positions[1] - positions[0] == 14


# --------------------------------------------------------------------------- #
# Dispatcher                                                                  #
# --------------------------------------------------------------------------- #

def test_make_depth_known_patterns():
    for name in stereogram.PATTERNS:
        grid = stereogram.make_depth(name, 30, 10)
        assert len(grid) == 10
    grid = stereogram.make_depth("text:HI", 30, 10)
    assert len(grid) == 10


def test_make_depth_unknown_raises():
    try:
        stereogram.make_depth("nonexistent", 30, 10)
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown pattern")


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #

def test_cli_default(capsys=None):
    """main() with no args should succeed and print a sphere stereogram."""
    rc = stereogram.main(["stereogram.py"])
    assert rc == 0


def test_cli_version_exits():
    """--version should exit with code 0 and print version string."""
    import subprocess
    proc = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "stereogram.py"),
         "--version"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert stereogram.__version__ in proc.stdout


def test_cli_help_exits():
    """--help should exit with code 0 and mention 'pattern'."""
    import subprocess
    proc = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "stereogram.py"),
         "--help"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert "pattern" in proc.stdout.lower()


def test_cli_bad_width():
    rc = stereogram.main(["stereogram.py", "sphere", "5", "10"])
    assert rc == 2


def test_cli_bad_pattern():
    rc = stereogram.main(["stereogram.py", "nonexistent"])
    assert rc == 1


def test_cli_list_patterns():
    rc = stereogram.main(["stereogram.py", "--list-patterns"])
    assert rc == 0


def test_cli_list_patterns_abbreviation():
    """Argparse prefix abbreviation --list should also list patterns."""
    import io
    from contextlib import redirect_stdout
    f = io.StringIO()
    with redirect_stdout(f):
        rc = stereogram.main(["stereogram.py", "--list"])
    assert rc == 0
    assert "Available patterns:" in f.getvalue()


def test_cli_show_depth():
    rc = stereogram.main(["stereogram.py", "sphere", "--show-depth",
                          "--no-banner"])
    assert rc == 0


def test_cli_invert_and_seed():
    rc = stereogram.main(["stereogram.py", "heart", "--invert", "--seed", "42",
                          "--no-banner"])
    assert rc == 0


def test_cli_save(tmp_path=None):
    import tempfile
    f = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
    f.close()
    rc = stereogram.main(["stereogram.py", "heart", "--save", f.name,
                          "--no-banner"])
    assert rc == 0
    assert os.path.getsize(f.name) > 0
    os.unlink(f.name)


def run_all():
    """Discover and run all test_* functions in this module."""
    fns = [obj for name, obj in sorted(globals().items())
           if name.startswith("test_") and callable(obj)]
    passed = 0
    failed = 0
    for fn in fns:
        try:
            # Some tests expect a capsys/tmp_path fixture-like arg; provide None.
            import inspect
            params = inspect.signature(fn).parameters
            args = []
            for pname in params:
                if pname == "capsys":
                    args.append(None)
                elif pname == "tmp_path":
                    args.append(None)
                else:
                    args.append(None)
            fn(*args)
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {fn.__name__}: {exc}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run_all())