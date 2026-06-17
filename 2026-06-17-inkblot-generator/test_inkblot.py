#!/usr/bin/env python3
"""
Tests for the Procedural Inkblot Generator.

Run with:
    python -m pytest test_inkblot.py -v
    # or
    python test_inkblot.py
"""

import math
import random
import subprocess
import sys
import os

# Ensure the module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inkblot


# ─── Braille rendering tests ─────────────────────────────────────────

class TestPixelsToBraille:
    """Test the Braille character encoding."""

    def test_empty_grid_produces_blank_chars(self):
        """An all-False grid should produce only the base Braille character (blank)."""
        grid = [[False] * 8 for _ in range(8)]
        lines = inkblot.pixels_to_braille(grid, 8, 8)
        # All characters should be the blank Braille character (U+2800)
        for line in lines:
            for ch in line:
                assert ch == "\u2800", f"Expected blank Braille, got {repr(ch)}"

    def test_full_grid_produces_full_braille(self):
        """An all-True grid should produce fully-dotted Braille characters (U+28FF)."""
        grid = [[True] * 8 for _ in range(8)]
        lines = inkblot.pixels_to_braille(grid, 8, 8)
        for line in lines:
            for ch in line:
                assert ch == "\u28FF", f"Expected full Braille U+28FF, got {repr(ch)}"

    def test_single_pixel_encoding(self):
        """Setting just the top-left pixel should activate only bit 0."""
        grid = [[False] * 2 for _ in range(4)]
        grid[0][0] = True  # top-left dot = bit 0
        lines = inkblot.pixels_to_braille(grid, 4, 2)
        assert len(lines) == 1
        assert len(lines[0]) == 1
        # U+2800 + bit 0 = U+2801
        assert lines[0] == "\u2801", f"Expected U+2801, got {repr(lines[0])}"

    def test_output_dimensions(self):
        """Verify that output line count and width are correct."""
        h, w = 20, 16
        grid = [[False] * w for _ in range(h)]
        lines = inkblot.pixels_to_braille(grid, h, w)
        # Expected Braille rows: ceil(h/4) = 5, cols: ceil(w/2) = 8
        assert len(lines) == 5, f"Expected 5 lines, got {len(lines)}"
        for line in lines:
            assert len(line) == 8, f"Expected 8 chars per line, got {len(line)}"

    def test_non_multiple_dimensions(self):
        """Grid dimensions not divisible by 2/4 should still work."""
        grid = [[False] * 7 for _ in range(11)]
        lines = inkblot.pixels_to_braille(grid, 11, 7)
        # ceil(11/4)=3 rows, ceil(7/2)=4 cols
        assert len(lines) == 3
        assert len(lines[0]) == 4


class TestColoredBraille:
    """Test colored Braille output."""

    def test_colored_wraps_with_ansi(self):
        """Colored output should contain ANSI escape codes."""
        grid = [[True] * 8 for _ in range(8)]
        lines = inkblot.pixels_to_braille_colored(grid, 8, 8, "\033[35m")
        for line in lines:
            assert line.startswith("\033[35m"), "Line should start with color code"
            assert "\033[0m" in line, "Line should contain reset code"

    def test_colored_preserves_content(self):
        """Colored output should have the same Braille characters, just wrapped in ANSI."""
        grid = [[True] * 8 for _ in range(8)]
        plain = inkblot.pixels_to_braille(grid, 8, 8)
        colored = inkblot.pixels_to_braille_colored(grid, 8, 8, "\033[35m")
        # Strip ANSI codes from colored and compare
        import re
        for p_line, c_line in zip(plain, colored):
            clean = re.sub(r'\033\[[0-9;]*m', '', c_line)
            assert clean == p_line, "Color-wrapped content should match plain content"


# ─── Noise function tests ────────────────────────────────────────────

class TestNoise:
    """Test procedural noise functions."""

    def test_hash2d_deterministic(self):
        """Same inputs should always produce the same output."""
        a = inkblot._hash2d(10, 20, 42)
        b = inkblot._hash2d(10, 20, 42)
        assert a == b, "Hash should be deterministic"

    def test_hash2d_range(self):
        """Hash values should be in [0, 1)."""
        for x in range(10):
            for y in range(10):
                for s in range(3):
                    val = inkblot._hash2d(x, y, s)
                    assert 0.0 <= val < 1.0, f"Hash {val} out of range"

    def test_hash2d_different_seeds(self):
        """Different seeds should produce different values."""
        a = inkblot._hash2d(5, 5, 0)
        b = inkblot._hash2d(5, 5, 1)
        assert a != b, "Different seeds should produce different hashes"

    def test_value_noise_range(self):
        """Value noise should return values in [0, 1] range."""
        for i in range(50):
            val = inkblot.value_noise(i * 0.3, i * 0.7, seed=0)
            assert 0.0 <= val <= 1.0, f"Noise value {val} out of [0,1]"

    def test_value_noise_deterministic(self):
        """Value noise should be deterministic with same inputs."""
        for seed in [0, 42, 999]:
            val1 = inkblot.value_noise(1.5, 2.5, seed)
            val2 = inkblot.value_noise(1.5, 2.5, seed)
            assert val1 == val2, f"Noise not deterministic for seed {seed}"

    def test_fbm_range(self):
        """fBm should return non-negative values (can exceed 1.0 due to octave summation)."""
        for i in range(30):
            val = inkblot.fbm(i * 0.5, i * 0.5, seed=10)
            assert val >= 0.0, f"fBm value {val} is negative"

    def test_smooth_interpolation(self):
        """Smoothstep should produce values in [0,1] for inputs in [0,1]."""
        for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
            s = inkblot._smooth(t)
            assert 0.0 <= s <= 1.0, f"Smoothstep({t}) = {s} out of range"


# ─── Generator tests ─────────────────────────────────────────────────

class TestGenerators:
    """Test inkblot generation functions."""

    def test_splash_produces_grid(self):
        """Splash generator should produce a grid of correct size."""
        rng = random.Random(42)
        grid = inkblot.generate_splash(40, 80, seed=42, rng=rng)
        assert len(grid) == 40, f"Expected height 40, got {len(grid)}"
        assert len(grid[0]) == 80, f"Expected width 80, got {len(grid[0])}"

    def test_radial_produces_grid(self):
        """Radial generator should produce a grid of correct size."""
        rng = random.Random(42)
        grid = inkblot.generate_radial(40, 80, seed=42, rng=rng)
        assert len(grid) == 40
        assert len(grid[0]) == 80

    def test_cellular_produces_grid(self):
        """Cellular generator should produce a grid of correct size."""
        rng = random.Random(42)
        grid = inkblot.generate_cellular(40, 80, seed=42, rng=rng)
        assert len(grid) == 40
        assert len(grid[0]) == 80

    def test_organic_produces_grid(self):
        """Organic generator should produce a grid of correct size."""
        rng = random.Random(42)
        grid = inkblot.generate_organic(40, 80, seed=42, rng=rng)
        assert len(grid) == 40
        assert len(grid[0]) == 80

    def test_mirror4_produces_grid(self):
        """Mirror4 generator should produce a grid of correct size."""
        rng = random.Random(42)
        grid = inkblot.generate_both_mirror(40, 80, seed=42, rng=rng)
        assert len(grid) == 40
        assert len(grid[0]) == 80

    def test_fractal_produces_grid(self):
        """Fractal generator should produce a grid of correct size."""
        rng = random.Random(42)
        grid = inkblot.generate_fractal(40, 80, seed=42, rng=rng)
        assert len(grid) == 40
        assert len(grid[0]) == 80

    def test_splash_horizontal_symmetry(self):
        """Splash-style blots should be horizontally symmetric."""
        rng = random.Random(42)
        grid = inkblot.generate_splash(40, 80, seed=42, rng=rng)
        mid = 40
        for y in range(40):
            for x in range(mid):
                left = grid[y][x]
                right = grid[y][80 - 1 - x]
                assert left == right, f"Asymmetry at ({y},{x}): left={left}, right={right}"

    def test_mirror4_fourfold_symmetry(self):
        """Mirror4 blots should have four-fold symmetry."""
        rng = random.Random(42)
        grid = inkblot.generate_both_mirror(40, 80, seed=42, rng=rng)
        half_h, half_w = 20, 40
        for y in range(half_h):
            for x in range(half_w):
                val = grid[y][x]
                assert grid[y][80 - 1 - x] == val, "Top-right mirror broken"
                assert grid[40 - 1 - y][x] == val, "Bottom-left mirror broken"
                assert grid[40 - 1 - y][80 - 1 - x] == val, "Bottom-right mirror broken"

    def test_all_styles_in_dict(self):
        """All generator functions should be in STYLES dict."""
        expected = {"splash", "radial", "cellular", "organic", "mirror4", "fractal"}
        assert set(inkblot.STYLES.keys()) == expected, f"Expected {expected}, got {set(inkblot.STYLES.keys())}"

    def test_density_affects_fill(self):
        """Higher density should produce more filled pixels."""
        rng_low = random.Random(99)
        grid_low = inkblot.generate_splash(40, 80, seed=99, rng=rng_low, density=0.2)
        fill_low = sum(sum(row) for row in grid_low)

        rng_high = random.Random(99)
        grid_high = inkblot.generate_splash(40, 80, seed=99, rng=rng_high, density=0.8)
        fill_high = sum(sum(row) for row in grid_high)

        assert fill_high > fill_low, f"Higher density should fill more pixels: low={fill_low}, high={fill_high}"


# ─── Interpretation tests ────────────────────────────────────────────

class TestInterpretation:
    """Test psychological interpretation generation."""

    def test_interpretation_structure(self):
        """Interpretation should contain three sections."""
        rng = random.Random(42)
        interp = inkblot.generate_interpretation(42, rng)
        assert "You see" in interp, "Should contain 'You see'"
        assert "This suggests" in interp, "Should contain 'This suggests'"
        # The advice line should not be empty
        lines = [l for l in interp.strip().split("\n") if l.strip()]
        assert len(lines) >= 3, f"Expected at least 3 lines, got {len(lines)}"

    def test_interpretation_deterministic(self):
        """Same seed should produce the same interpretation."""
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        i1 = inkblot.generate_interpretation(42, rng1)
        i2 = inkblot.generate_interpretation(42, rng2)
        assert i1 == i2, "Interpretation should be deterministic with same seed"

    def test_interpretations_dict_has_keys(self):
        """INTERPRETATIONS dict should have all required categories."""
        for key in ["emotions", "objects", "advice"]:
            assert key in inkblot.INTERPRETATIONS, f"Missing key: {key}"
            assert len(inkblot.INTERPRETATIONS[key]) > 0, f"Empty list for key: {key}"


# ─── Statistics tests ────────────────────────────────────────────────

class TestStats:
    """Test inkblot statistics computation."""

    def test_stats_structure(self):
        """Stats should contain expected keys."""
        grid = [[True] * 8 for _ in range(8)]
        stats = inkblot.compute_stats(grid, 8, 8)
        assert "fill_ratio" in stats
        assert "pixel_count" in stats
        assert "total_pixels" in stats
        assert "symmetry_score" in stats

    def test_full_grid_stats(self):
        """A fully filled grid should have 100% fill ratio."""
        grid = [[True] * 10 for _ in range(10)]
        stats = inkblot.compute_stats(grid, 10, 10)
        assert stats["fill_ratio"] == 1.0
        assert stats["pixel_count"] == 100
        assert stats["total_pixels"] == 100

    def test_empty_grid_stats(self):
        """An empty grid should have 0% fill ratio."""
        grid = [[False] * 10 for _ in range(10)]
        stats = inkblot.compute_stats(grid, 10, 10)
        assert stats["fill_ratio"] == 0.0
        assert stats["pixel_count"] == 0

    def test_symmetric_grid_symmetry_score(self):
        """A perfectly symmetric grid should have symmetry_score near 1.0."""
        rng = random.Random(42)
        grid = inkblot.generate_splash(40, 80, seed=42, rng=rng)
        stats = inkblot.compute_stats(grid, 40, 80)
        # Splash is horizontally mirrored, so should be very symmetric
        assert stats["symmetry_score"] >= 0.95, f"Expected high symmetry, got {stats['symmetry_score']:.3f}"


# ─── Inversion tests ─────────────────────────────────────────────────

class TestInversion:
    """Test grid inversion."""

    def test_inversion_flips_pixels(self):
        """Inversion should flip all pixels."""
        grid = [[True, False], [False, True]]
        inverted = inkblot.invert_grid(grid, 2, 2)
        assert inverted == [[False, True], [True, False]]

    def test_double_inversion_restores(self):
        """Inverting twice should restore the original."""
        original = [[True, False, True], [False, True, False]]
        once = inkblot.invert_grid(original, 2, 3)
        twice = inkblot.invert_grid(once, 2, 3)
        assert twice == original, "Double inversion should restore original"


# ─── CLI tests ────────────────────────────────────────────────────────

class TestCLI:
    """Test command-line interface."""

    def _run(self, args, timeout=10):
        """Helper to run inkblot.py with given arguments."""
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inkblot.py")
        result = subprocess.run(
            [sys.executable, script] + args,
            capture_output=True, text=True, timeout=timeout
        )
        return result

    def test_basic_run(self):
        """Basic run should succeed and produce output."""
        result = self._run(["--seed", "42", "--no-interpret"])
        assert result.returncode == 0, f"Exit code {result.returncode}: {result.stderr}"
        assert "RORSCHACH INKBLOT" in result.stdout
        assert "seed=42" in result.stdout

    def test_version_flag(self):
        """--version should print version and exit."""
        result = self._run(["--version"])
        assert result.returncode == 0
        assert "inkblot" in result.stdout.lower() or inkblot.VERSION in result.stdout

    def test_list_styles(self):
        """--list-styles should list all available styles."""
        result = self._run(["--list-styles"])
        assert result.returncode == 0
        for style in inkblot.STYLES:
            assert style in result.stdout, f"Style '{style}' not listed"

    def test_style_option(self):
        """Each style should produce output without errors."""
        for style in inkblot.STYLES:
            result = self._run(["--seed", "1", "--style", style, "--no-interpret"])
            assert result.returncode == 0, f"Style '{style}' failed: {result.stderr}"
            assert f"style={style}" in result.stdout, f"Style '{style}' not in output"

    def test_invert_flag(self):
        """--invert should add 'inverted' to metadata."""
        result = self._run(["--seed", "42", "--invert", "--no-interpret"])
        assert result.returncode == 0
        assert "inverted" in result.stdout

    def test_color_flag(self):
        """--color should work and produce output."""
        result = self._run(["--seed", "42", "--color", "magenta", "--no-interpret"])
        assert result.returncode == 0
        assert "color=magenta" in result.stdout

    def test_density_flag(self):
        """--density should accept valid values."""
        result = self._run(["--seed", "42", "--density", "0.7", "--no-interpret"])
        assert result.returncode == 0
        assert "density=0.70" in result.stdout

    def test_gallery_mode(self):
        """--gallery should produce a gallery view."""
        result = self._run(["--seed", "42", "--gallery", "--no-interpret"])
        assert result.returncode == 0
        assert "INKBLOT GALLERY" in result.stdout

    def test_stats_flag(self):
        """--stats should show statistics."""
        result = self._run(["--seed", "42", "--stats", "--no-interpret"])
        assert result.returncode == 0
        assert "fill=" in result.stdout
        assert "symmetry=" in result.stdout

    def test_save_to_file(self):
        """--save should write output to a file."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            tmpfile = f.name
        try:
            result = self._run(["--seed", "42", "--save", tmpfile, "--no-interpret"])
            assert result.returncode == 0
            assert os.path.exists(tmpfile), "Save file was not created"
            with open(tmpfile, "r", encoding="utf-8") as f:
                content = f.read()
            assert "RORSCHACH INKBLOT" in content
            # Saved file should not contain ANSI escape codes
            assert "\033[" not in content, "Saved file should not contain ANSI codes"
        finally:
            os.unlink(tmpfile)

    def test_small_width(self):
        """Small width should work."""
        result = self._run(["--seed", "42", "--width", "20", "--no-interpret"])
        assert result.returncode == 0
        assert "seed=42" in result.stdout

    def test_invalid_width(self):
        """Invalid width should produce an error."""
        result = self._run(["--width", "5", "--no-interpret"])
        assert result.returncode != 0

    def test_invalid_density(self):
        """Invalid density should produce an error."""
        result = self._run(["--density", "1.5", "--no-interpret"])
        assert result.returncode != 0


# ─── Run all tests if executed directly ──────────────────────────────

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))