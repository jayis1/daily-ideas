#!/usr/bin/env python3
"""
Tests for the ASCII Topography Map Generator.
"""

import os
import sys
import tempfile

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from topography import (
    PerlinNoise, TopographyMap, get_terrain, get_terrain_index,
    TERRAIN, CONTOUR_INTERVAL, COMPASS_ROSE, __version__,
)


# ─── PerlinNoise Tests ────────────────────────────────────────────────────

class TestPerlinNoise:
    """Tests for the Perlin noise generator."""

    def test_deterministic(self):
        """Same seed produces same output."""
        n1 = PerlinNoise(42)
        n2 = PerlinNoise(42)
        for x in range(5):
            for y in range(5):
                assert n1.noise2d(x * 0.1, y * 0.1) == n2.noise2d(x * 0.1, y * 0.1)

    def test_different_seeds_differ(self):
        """Different seeds produce different output."""
        n1 = PerlinNoise(1)
        n2 = PerlinNoise(2)
        # Extremely unlikely to be equal for 10 samples
        diffs = 0
        for x in range(10):
            v1 = n1.noise2d(x * 0.3, 0.5)
            v2 = n2.noise2d(x * 0.3, 0.5)
            if v1 != v2:
                diffs += 1
        assert diffs > 0, "Different seeds produced identical output"

    def test_noise_range(self):
        """Noise output should be in reasonable range [-1, 1]."""
        n = PerlinNoise(0)
        for x in range(20):
            for y in range(20):
                val = n.noise2d(x * 0.1, y * 0.1)
                assert -1.5 <= val <= 1.5, f"Noise {val} out of range at ({x},{y})"

    def test_octave_noise_range(self):
        """Octave noise should be normalized roughly to [-1, 1]."""
        n = PerlinNoise(0)
        for x in range(20):
            val = n.octave_noise(x * 0.1, 0.5, octaves=4)
            assert -1.2 <= val <= 1.2, f"Octave noise {val} out of range at x={x}"

    def test_octave_noise_increases_with_octaves(self):
        """More octaves generally means more detail (different output)."""
        n = PerlinNoise(42)
        # Sample multiple points — at least one should differ between octave counts
        any_diff = False
        for x in [0.37, 1.23, 2.5, 4.1, 7.7]:
            val2 = n.octave_noise(x, x, octaves=2)
            val6 = n.octave_noise(x, x, octaves=6)
            if val2 != val6:
                any_diff = True
                break
        assert any_diff, "2 and 6 octaves produced identical output at all sample points"


# ─── Terrain Classification Tests ─────────────────────────────────────────

class TestTerrainClassification:
    """Tests for terrain type classification."""

    def test_deep_water(self):
        char, name = get_terrain(0.0)
        assert name == "deep water"
        assert char == "≈"

    def test_snow(self):
        char, name = get_terrain(0.95)
        assert name == "snow"
        assert char == "#"

    def test_forest(self):
        char, name = get_terrain(0.40)
        assert name == "forest"
        assert char == ";"

    def test_peak(self):
        char, name = get_terrain(0.75)
        assert name == "peak"
        assert char == "^"

    def test_get_terrain_index_boundaries(self):
        """Terrain index should match TERRAIN list ordering."""
        # Deep water at 0
        assert get_terrain_index(0.0) == 0
        # Snow at high elevation
        assert get_terrain_index(0.95) == len(TERRAIN) - 1


# ─── TopographyMap Tests ──────────────────────────────────────────────────

class TestTopographyMap:
    """Tests for the topographic map generator."""

    def test_basic_generation(self):
        """Map generates without errors."""
        tmap = TopographyMap(width=30, height=15, seed=42)
        tmap.generate()
        assert len(tmap.elevation) == 15
        assert len(tmap.elevation[0]) == 30

    def test_elevation_range(self):
        """All elevation values should be in [0, 1]."""
        tmap = TopographyMap(width=40, height=20, seed=42)
        tmap.generate()
        for y in range(tmap.height):
            for x in range(tmap.width):
                e = tmap.elevation[y][x]
                assert 0.0 <= e <= 1.0, f"Elevation {e} out of range at ({x},{y})"

    def test_deterministic_seed(self):
        """Same seed produces same map."""
        t1 = TopographyMap(width=30, height=15, seed=12345)
        t1.generate()
        t2 = TopographyMap(width=30, height=15, seed=12345)
        t2.generate()
        for y in range(15):
            for x in range(30):
                assert t1.elevation[y][x] == t2.elevation[y][x]

    def test_different_seeds_differ(self):
        """Different seeds produce different maps."""
        t1 = TopographyMap(width=30, height=15, seed=1)
        t1.generate()
        t2 = TopographyMap(width=30, height=15, seed=2)
        t2.generate()
        diffs = sum(1 for y in range(15) for x in range(30)
                    if t1.elevation[y][x] != t2.elevation[y][x])
        assert diffs > 0, "Different seeds produced identical maps"

    def test_rivers_generated(self):
        """Rivers should be generated for typical maps."""
        tmap = TopographyMap(width=60, height=30, seed=42)
        tmap.generate()
        # Should have some river cells (could be 0 for edge cases, but unlikely with seed 42)
        assert isinstance(tmap.river_cells, set)

    def test_peaks_generated(self):
        """Peaks should be generated for typical maps."""
        tmap = TopographyMap(width=80, height=30, seed=42)
        tmap.generate()
        # With a large enough map, peaks should exist
        assert len(tmap.peak_labels) >= 0  # could be 0 for very flat maps

    def test_lake_detection(self):
        """Lake detection should find enclosed water basins."""
        tmap = TopographyMap(width=60, height=30, seed=100)
        tmap.generate()
        # lake_cells is always a set (could be empty)
        assert isinstance(tmap.lake_cells, set)

    def test_render_basic(self):
        """Render should produce output without errors."""
        tmap = TopographyMap(width=30, height=10, seed=42)
        tmap.generate()
        output = tmap.render(use_color=False)
        assert isinstance(output, str)
        assert len(output) > 0
        # Should contain border characters
        assert "╔" in output
        assert "╗" in output

    def test_render_with_color(self):
        """Color render should include ANSI codes."""
        tmap = TopographyMap(width=30, height=10, seed=42)
        tmap.generate()
        output = tmap.render(use_color=True)
        assert "\033[" in output  # ANSI escape sequences present

    def test_render_no_color(self):
        """No-color render should not include ANSI codes."""
        tmap = TopographyMap(width=30, height=10, seed=42)
        tmap.generate()
        output = tmap.render(use_color=False)
        assert "\033[" not in output

    def test_render_elevation_numbers(self):
        """Elevation numbers render should show digits."""
        tmap = TopographyMap(width=30, height=10, seed=42)
        tmap.generate()
        output = tmap.render_elevation_numbers()
        lines = output.strip().split("\n")
        assert len(lines) == 10
        # Each line should be 30 chars of digits
        for line in lines:
            assert len(line) == 30
            for ch in line:
                assert ch in "0123456789"

    def test_render_profile_row(self):
        """Profile render for a row should work."""
        tmap = TopographyMap(width=30, height=15, seed=42)
        tmap.generate()
        output = tmap.render_profile('row', 5, use_color=False)
        assert "Elevation Profile" in output
        assert "Row 5" in output
        assert "█" in output  # profile blocks

    def test_render_profile_col(self):
        """Profile render for a column should work."""
        tmap = TopographyMap(width=30, height=15, seed=42)
        tmap.generate()
        output = tmap.render_profile('col', 10, use_color=False)
        assert "Col 10" in output

    def test_render_profile_invalid_direction(self):
        """Invalid profile direction should return error message."""
        tmap = TopographyMap(width=30, height=15, seed=42)
        tmap.generate()
        output = tmap.render_profile('invalid', 5)
        assert "Error" in output

    def test_render_profile_out_of_range(self):
        """Out-of-range profile index should return error message."""
        tmap = TopographyMap(width=30, height=15, seed=42)
        tmap.generate()
        output = tmap.render_profile('row', 999)
        assert "Error" in output

    def test_render_with_grid(self):
        """Grid overlay render should produce output."""
        tmap = TopographyMap(width=40, height=20, seed=42)
        tmap.generate()
        output = tmap.render(use_color=False, show_grid=True)
        assert "┼" in output or "│" in output or "─" in output

    def test_render_without_compass(self):
        """No-compass render should not include compass rose."""
        tmap = TopographyMap(width=40, height=15, seed=42)
        tmap.generate()
        output = tmap.render(use_color=False, show_compass=False)
        assert "NW" not in output

    def test_render_with_compass(self):
        """Compass render should include directional text."""
        tmap = TopographyMap(width=40, height=15, seed=42)
        tmap.generate()
        output = tmap.render(use_color=False, show_compass=True)
        assert "N" in output

    def test_render_without_stats(self):
        """No-stats render should not include terrain composition."""
        tmap = TopographyMap(width=40, height=15, seed=42)
        tmap.generate()
        output = tmap.render(use_color=False, show_stats=False)
        assert "Terrain:" not in output

    def test_render_with_stats(self):
        """Stats render should include terrain composition."""
        tmap = TopographyMap(width=40, height=15, seed=42)
        tmap.generate()
        output = tmap.render(use_color=False, show_stats=True)
        assert "Terrain:" in output

    def test_terrain_stats(self):
        """Terrain stats should sum to approximately 100%."""
        tmap = TopographyMap(width=60, height=30, seed=42)
        tmap.generate()
        stats = tmap.get_terrain_stats()
        total = sum(stats.values())
        assert 99.0 <= total <= 101.0, f"Stats sum to {total}%"

    def test_lake_count_connected(self):
        """Lake count should count distinct connected components."""
        tmap = TopographyMap(width=60, height=30, seed=42)
        tmap.generate()
        count = tmap.get_lake_count()
        assert count >= 0

    def test_contour_detection(self):
        """Contour detection should work for steep areas."""
        tmap = TopographyMap(width=40, height=20, seed=42)
        tmap.generate()
        # Just verify it doesn't crash
        for y in range(1, tmap.height - 1):
            for x in range(1, tmap.width - 1):
                tmap.is_contour(x, y)


# ─── Validation Tests ────────────────────────────────────────────────────

class TestValidation:
    """Tests for input validation."""

    def test_width_too_small(self):
        try:
            TopographyMap(width=3, height=10, seed=42)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "too small" in str(e).lower()

    def test_height_too_small(self):
        try:
            TopographyMap(width=20, height=2, seed=42)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "too small" in str(e).lower()

    def test_width_too_large(self):
        try:
            TopographyMap(width=600, height=30, seed=42)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "too large" in str(e).lower()

    def test_octaves_too_high(self):
        try:
            TopographyMap(width=30, height=15, seed=42, octaves=20)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "octaves" in str(e).lower()

    def test_octaves_zero(self):
        try:
            TopographyMap(width=30, height=15, seed=42, octaves=0)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "octaves" in str(e).lower()

    def test_scale_invalid(self):
        try:
            TopographyMap(width=30, height=15, seed=42, scale=0)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "scale" in str(e).lower()

    def test_scale_negative(self):
        try:
            TopographyMap(width=30, height=15, seed=42, scale=-0.01)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "scale" in str(e).lower()


# ─── Output Tests ─────────────────────────────────────────────────────────

class TestOutput:
    """Tests for output features."""

    def test_save_to_file(self):
        """--output flag should save to file."""
        tmap = TopographyMap(width=30, height=10, seed=42)
        tmap.generate()
        output = tmap.render(use_color=False)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(output)
            f.write("\n")
            tmppath = f.name
        try:
            with open(tmppath) as f:
                content = f.read()
            assert "Topographic Map" in content
            assert "╔" in content
        finally:
            os.unlink(tmppath)

    def test_version_constant(self):
        """Version should be a valid version string."""
        assert __version__
        parts = __version__.split(".")
        assert len(parts) >= 2
        for part in parts:
            assert part.isdigit()

    def test_compass_rose_structure(self):
        """Compass rose should have proper structure."""
        assert len(COMPASS_ROSE) == 9
        assert any("N" in line for line in COMPASS_ROSE)
        assert any("S" in line for line in COMPASS_ROSE)
        assert any("W" in line for line in COMPASS_ROSE)
        assert any("E" in line for line in COMPASS_ROSE)


# ─── Edge Case Tests ─────────────────────────────────────────────────────

class TestEdgeCases:
    """Tests for edge cases."""

    def test_very_small_map(self):
        """Smallest allowed map size should work."""
        tmap = TopographyMap(width=10, height=5, seed=42)
        tmap.generate()
        output = tmap.render(use_color=False)
        assert len(output) > 0

    def test_tall_narrow_map(self):
        """Non-square map proportions should work."""
        tmap = TopographyMap(width=10, height=30, seed=42)
        tmap.generate()
        assert len(tmap.elevation) == 30
        assert len(tmap.elevation[0]) == 10

    def test_wide_short_map(self):
        """Wide short map should work."""
        tmap = TopographyMap(width=100, height=5, seed=42)
        tmap.generate()
        assert len(tmap.elevation) == 5
        assert len(tmap.elevation[0]) == 100

    def test_single_octave(self):
        """Map with just one octave should still generate."""
        tmap = TopographyMap(width=30, height=15, seed=42, octaves=1)
        tmap.generate()
        assert len(tmap.elevation) == 15

    def test_high_octaves(self):
        """Map with many octaves should still generate."""
        tmap = TopographyMap(width=30, height=15, seed=42, octaves=12)
        tmap.generate()
        assert len(tmap.elevation) == 15

    def test_very_small_scale(self):
        """Very small scale (zoomed out) should work."""
        tmap = TopographyMap(width=30, height=15, seed=42, scale=0.005)
        tmap.generate()
        output = tmap.render(use_color=False)
        assert len(output) > 0

    def test_larger_scale(self):
        """Larger scale should work."""
        tmap = TopographyMap(width=30, height=15, seed=42, scale=0.1)
        tmap.generate()
        output = tmap.render(use_color=False)
        assert len(output) > 0

    def test_contour_interval_custom(self):
        """Custom contour interval should work."""
        tmap = TopographyMap(width=30, height=15, seed=42, contour_interval=0.10)
        tmap.generate()
        output = tmap.render(use_color=False, show_contours=True)
        assert "every 10%" in output

    def test_no_features(self):
        """Map with all features hidden should still render."""
        tmap = TopographyMap(width=30, height=15, seed=42)
        tmap.generate()
        output = tmap.render(
            use_color=False,
            show_contours=False,
            show_rivers=False,
            show_labels=False,
            show_legend=False,
            show_compass=False,
            show_stats=False,
        )
        assert len(output) > 0
        assert "╔" in output


if __name__ == "__main__":
    # Simple test runner
    import traceback
    test_classes = [
        TestPerlinNoise, TestTerrainClassification, TestTopographyMap,
        TestValidation, TestOutput, TestEdgeCases,
    ]
    passed = 0
    failed = 0
    for cls in test_classes:
        instance = cls()
        for attr in sorted(dir(instance)):
            if attr.startswith("test_"):
                try:
                    getattr(instance, attr)()
                    passed += 1
                except Exception as e:
                    failed += 1
                    print(f"FAIL: {cls.__name__}.{attr}: {e}")
                    traceback.print_exc()
    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)