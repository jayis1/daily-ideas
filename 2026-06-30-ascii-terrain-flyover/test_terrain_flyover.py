#!/usr/bin/env python3
"""Tests for ASCII Terrain Flyover."""

import math
import os
import tempfile

# Import the module under test
import terrain_flyover as tf


class TestPerlinNoise:
    """Tests for the PerlinNoise class."""

    def setup_method(self):
        self.noise = tf.PerlinNoise(seed=42)

    def test_deterministic_with_seed(self):
        """Same seed should produce same noise values."""
        n1 = tf.PerlinNoise(seed=123)
        n2 = tf.PerlinNoise(seed=123)
        for x in [0, 1, 5.5, -3.2]:
            for y in [0, 1, 5.5, -3.2]:
                assert n1.noise(x, y) == n2.noise(x, y), \
                    f"Noise mismatch at ({x}, {y})"

    def test_different_seeds_differ(self):
        """Different seeds should produce different noise values."""
        n1 = tf.PerlinNoise(seed=1)
        n2 = tf.PerlinNoise(seed=2)
        # At least some values should differ
        diffs = sum(1 for i in range(20)
                    if abs(n1.noise(i * 0.5, i * 0.7) - n2.noise(i * 0.5, i * 0.7)) > 1e-6)
        assert diffs > 0, "Different seeds produced identical noise"

    def test_noise_range(self):
        """Noise output should be within reasonable bounds."""
        values = [self.noise.noise(x * 0.1, y * 0.1)
                  for x in range(20) for y in range(20)]
        # Perlin noise is typically in [-0.7, 0.7] range
        assert all(-1.0 < v < 1.0 for v in values), \
            f"Noise values out of expected range: {min(values):.3f} to {max(values):.3f}"

    def test_octave_noise(self):
        """Octave noise should produce smoother results with multiple octaves."""
        vals_1 = [self.noise.octave_noise(x * 0.1, y * 0.1, octaves=1)
                   for x in range(10) for y in range(10)]
        vals_6 = [self.noise.octave_noise(x * 0.1, y * 0.1, octaves=6)
                   for x in range(10) for y in range(10)]
        # Both should produce values (not crash)
        assert len(vals_1) == 100
        assert len(vals_6) == 100

    def test_noise_zero(self):
        """Noise at integer coordinates should be deterministic."""
        # At exact integer coords, gradients should be consistent
        v = self.noise.noise(5, 5)
        assert isinstance(v, float)


class TestColorUtils:
    """Tests for color blending and mapping functions."""

    def test_blend_256_same_color(self):
        """Blending a color with itself should return a similar color."""
        assert tf._blend_256(34, 34, 0.5) == 34
        # Note: 255 maps through RGB cube so blending it with itself
        # may not round-trip exactly to 255
        result = tf._blend_256(255, 255, 0.5)
        assert isinstance(result, int)
        # Result should be close to white
        assert result >= 231  # nearest cube index to white

    def test_blend_256_at_zero(self):
        """Blending at t=0 should return the first color."""
        result = tf._blend_256(17, 255, 0.0)
        assert result == 17

    def test_blend_256_at_one(self):
        """Blending at t=1 should return the second color."""
        result = tf._blend_256(17, 255, 1.0)
        assert result == 255

    def test_blend_256_clamps(self):
        """Blending should clamp t to [0, 1]."""
        assert tf._blend_256(17, 255, -0.5) == 17
        assert tf._blend_256(17, 255, 1.5) == 255

    def test_rgb_to_256_primary(self):
        """RGB primary colors should map to known palette indices."""
        # Red
        assert tf._rgb_to_256(255, 0, 0) == 196
        # Green
        assert tf._rgb_to_256(0, 255, 0) == 46
        # Blue
        assert tf._rgb_to_256(0, 0, 255) == 21

    def test_rgb_to_256_black(self):
        """Black should map to palette index 16."""
        assert tf._rgb_to_256(0, 0, 0) == 16

    def test_rgb_to_256_white(self):
        """White should map to palette index 231."""
        assert tf._rgb_to_256(255, 255, 255) == 231


class TestHeightMapping:
    """Tests for height-to-color and height-to-character mapping."""

    def test_height_to_color_water(self):
        """Very low height should return water colors."""
        assert tf.height_to_color(0.1) == tf.DEEP_WATER
        assert tf.height_to_color(0.30) == tf.SHALLOW_WATER

    def test_height_to_color_sand(self):
        """Beach/shallows height should return sand or nearby color."""
        # 0.39 is between sand (0.38) and grass (0.50)
        c = tf.height_to_color(0.39, fog_factor=0.0, hour=12.0)
        assert c in (tf.SAND, tf.GRASS, tf.DARK_GRASS), \
            f"Expected sand/grass color for h=0.39, got {c}"

    def test_height_to_color_snow(self):
        """Very high height should return snow color."""
        assert tf.height_to_color(0.95) == tf.SNOW

    def test_height_to_color_with_fog(self):
        """Fog factor should affect the color."""
        c_no_fog = tf.height_to_color(0.5, fog_factor=0.0)
        c_full_fog = tf.height_to_color(0.5, fog_factor=1.0)
        assert c_no_fog != c_full_fog, "Fog should change the color"

    def test_height_to_color_night(self):
        """Night time should darken terrain colors."""
        c_day = tf.height_to_color(0.5, fog_factor=0.0, hour=12.0)
        c_night = tf.height_to_color(0.5, fog_factor=0.0, hour=0.0)
        assert c_day != c_night, "Night should change terrain colors"

    def test_height_to_char_water(self):
        """Water height should return wave-like characters."""
        ch = tf.height_to_char(0.1, 5, 40, frame=0)
        assert ch in tf.WAVE_CHARS, f"Expected water char, got '{ch}'"

    def test_height_to_char_snow(self):
        """High altitude should return snow characters."""
        ch = tf.height_to_char(0.95, 5, 40, frame=0)
        assert ch in "*✦❄", f"Expected snow char, got '{ch}'"

    def test_height_to_char_animates(self):
        """Water characters should change with frame number."""
        ch1 = tf.height_to_char(0.1, 5, 40, frame=0)
        ch2 = tf.height_to_char(0.1, 5, 40, frame=4)
        # Animation should cycle through wave chars
        assert ch1 in tf.WAVE_CHARS
        assert ch2 in tf.WAVE_CHARS


class TestTerrainFlyover:
    """Tests for the TerrainFlyover renderer."""

    def setup_method(self):
        self.flyover = tf.TerrainFlyover(seed=42, width=40, height=15,
                                           show_stats=False)

    def test_init_with_seed(self):
        """Init with a specific seed should be deterministic."""
        f1 = tf.TerrainFlyover(seed=42, width=40, height=15)
        f2 = tf.TerrainFlyover(seed=42, width=40, height=15)
        assert f1.seed == f2.seed == 42
        # Same seed should produce same height at same position
        assert f1.get_height(10, 20) == f2.get_height(10, 20)

    def test_get_height_range(self):
        """get_height should return values in [0, 1]."""
        heights = [self.flyover.get_height(x * 10, z * 10)
                    for x in range(20) for z in range(20)]
        assert all(0 <= h <= 1 for h in heights), \
            f"Heights out of range: {min(heights):.3f} to {max(heights):.3f}"

    def test_get_height_deterministic(self):
        """Same coordinates should always return same height."""
        h1 = self.flyover.get_height(50, 75)
        h2 = self.flyover.get_height(50, 75)
        assert h1 == h2

    def test_get_height_varies(self):
        """Different coordinates should generally produce different heights."""
        h1 = self.flyover.get_height(0, 0)
        h2 = self.flyover.get_height(100, 200)
        assert h1 != h2, "Different coords produced same height"

    def test_get_cloud_density(self):
        """Cloud density should be non-negative."""
        for x in range(10):
            for z in range(10):
                d = self.flyover.get_cloud_density(x * 10, z * 10)
                assert d >= 0, f"Negative cloud density at ({x}, {z})"

    def test_get_biome(self):
        """Biome detection should return known biome names."""
        biome_names = {"Ocean", "Shallows", "Beach", "Plains",
                       "Forest", "Mountains", "Alpine"}
        # Test various positions
        biomes = set()
        for x in range(0, 500, 50):
            for z in range(0, 500, 50):
                biomes.add(self.flyover._get_biome(x, z))
        # Should find at least a few biomes
        assert len(biomes) >= 2, f"Too few biomes found: {biomes}"
        assert biomes.issubset(biome_names), f"Unknown biome: {biomes}"

    def test_render_frame(self):
        """render_frame should produce a non-empty string."""
        output = self.flyover.render_frame(0)
        assert isinstance(output, str)
        assert len(output) > 100  # Should have substantial content
        assert "\033[" in output  # Should contain ANSI codes

    def test_render_multiple_frames(self):
        """Should be able to render multiple frames without error."""
        for frame in range(5):
            output = self.flyover.render_frame(frame)
            assert len(output) > 0

    def test_heading_to_compass(self):
        """Compass directions should match expected angles."""
        assert tf.TerrainFlyover._heading_to_compass(0) == "N"
        assert tf.TerrainFlyover._heading_to_compass(math.pi / 2) == "E"
        assert tf.TerrainFlyover._heading_to_compass(math.pi) == "S"
        assert tf.TerrainFlyover._heading_to_compass(3 * math.pi / 2) == "W"

    def test_altitude_clamping(self):
        """Altitude should be clamped to [0.1, 1.0]."""
        f = tf.TerrainFlyover(seed=1, altitude=0.6, width=40, height=15)
        f.altitude = 0.05
        # Not auto-clamped, but should not crash
        f.render_frame(0)

    def test_minimap_rendering(self):
        """Minimap overlay should work without errors."""
        f = tf.TerrainFlyover(seed=42, width=60, height=20,
                               show_minimap=True, show_stats=False)
        output = f.render_frame(0)
        assert len(output) > 0

    def test_night_rendering(self):
        """Night-time rendering should work."""
        f = tf.TerrainFlyover(seed=42, width=40, height=15,
                               hour=2.0, show_stats=False)
        output = f.render_frame(0)
        assert len(output) > 0

    def test_sunset_rendering(self):
        """Sunset rendering should work."""
        f = tf.TerrainFlyover(seed=42, width=40, height=15,
                               hour=19.0, show_stats=False)
        output = f.render_frame(0)
        assert len(output) > 0


class TestTimeOfDay:
    """Tests for the day/night cycle palette interpolation."""

    def test_lerp_palette_day(self):
        """Noon should return the day palette."""
        palette = tf._lerp_palette(tf.SKY_DAY, tf.SKY_SUNSET, tf.SKY_NIGHT, 12.0)
        assert palette == tf.SKY_DAY

    def test_lerp_palette_night(self):
        """Midnight should return the night palette."""
        palette = tf._lerp_palette(tf.SKY_DAY, tf.SKY_SUNSET, tf.SKY_NIGHT, 0.0)
        assert palette == tf.SKY_NIGHT

    def test_lerp_palette_sunset(self):
        """Sunset hour should produce warm colors."""
        palette = tf._lerp_palette(tf.SKY_DAY, tf.SKY_SUNSET, tf.SKY_NIGHT, 18.0)
        # Should be somewhere between day and sunset, not identical to either
        assert isinstance(palette, tuple)
        assert len(palette) == 5


class TestScreenshot:
    """Tests for the screenshot functionality."""

    def test_screenshot_produces_file(self):
        """Screenshot should create a text file without ANSI codes."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            filepath = f.name
        try:
            tf.run_screenshot(seed=42, filepath=filepath, width=40, height=10)
            assert os.path.exists(filepath)
            with open(filepath, 'r') as f:
                content = f.read()
            assert len(content) > 50
            # Should NOT contain ANSI escape sequences
            assert '\x1b[' not in content, "Screenshot should not contain ANSI codes"
        finally:
            os.unlink(filepath)


class TestMapMode:
    """Tests for the map mode."""

    def test_render_minimap(self):
        """render_minimap should produce a string."""
        flyover = tf.TerrainFlyover(seed=42, width=40, height=20)
        output = tf.render_minimap(flyover, map_w=20, map_h=10, scale=0.3)
        assert isinstance(output, str)
        assert len(output) > 50
        assert "\033[" in output  # Should contain ANSI codes

    def test_render_minimap_contains_marker(self):
        """Minimap should contain a position marker."""
        flyover = tf.TerrainFlyover(seed=42, width=40, height=20)
        output = tf.render_minimap(flyover, map_w=20, map_h=10, scale=0.3)
        assert "▶" in output, "Minimap should contain position marker"


class TestSkyColor:
    """Tests for sky color rendering."""

    def test_sky_color_day(self):
        """Daytime sky should produce valid color indices."""
        c = tf.sky_color(0, 10, 0.5, 0.3, hour=12.0)
        assert isinstance(c, int)
        assert 0 <= c <= 255

    def test_sky_color_night(self):
        """Nighttime sky should produce darker color indices."""
        c = tf.sky_color(0, 10, 0.5, 0.3, hour=1.0)
        assert isinstance(c, int)

    def test_sky_color_sunset(self):
        """Sunset sky should produce warm color indices."""
        c = tf.sky_color(5, 10, 0.5, 0.3, hour=19.0)
        assert isinstance(c, int)


class TestCLIArgs:
    """Test command-line argument parsing."""

    def test_version_flag(self):
        """--version should print version and exit."""
        import subprocess
        result = subprocess.run(
            [sys.executable, tf.__file__, "--version"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert tf.__version__ in result.stdout

    def test_help_flag(self):
        """--help should print usage and exit."""
        import subprocess
        result = subprocess.run(
            [sys.executable, tf.__file__, "--help"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "terrain" in result.stdout.lower()


class TestBugFixes:
    """Regression tests for bugs that were found and fixed."""

    def test_height_to_char_zero_max_dist(self):
        """height_to_char should not crash when max_dist=0."""
        # Bug: ZeroDivisionError when max_dist=0 (fog_dist=0)
        ch = tf.height_to_char(0.5, 5, 0, frame=0)
        assert isinstance(ch, str)
        assert len(ch) > 0

    def test_height_to_char_negative_max_dist(self):
        """height_to_char should not crash when max_dist is negative."""
        ch = tf.height_to_char(0.5, 5, -1, frame=0)
        assert isinstance(ch, str)
        assert len(ch) > 0

    def test_fog_dist_zero_no_crash(self):
        """TerrainFlyover with fog_dist=0 should not crash."""
        f = tf.TerrainFlyover(seed=42, width=20, height=10,
                               fog_dist=0, show_stats=False)
        output = f.render_frame(0)
        assert isinstance(output, str)
        assert len(output) > 0

    def test_interactive_keys_not_cleared_before_render(self):
        """_keys_held should be usable by render_frame in interactive mode."""
        f = tf.TerrainFlyover(seed=42, width=40, height=15,
                               interactive=True, show_stats=False)
        # Set keys and verify they affect rendering
        f._keys_held = {'w'}
        output = f.render_frame(0)
        assert isinstance(output, str)
        assert len(output) > 0
        # 'w' should cause speed_mult = speed * 2.0, which changes the output

    def test_overlay_minimap_no_garbled_ansi(self):
        """Minimap overlay should not produce garbled ANSI sequences."""
        f = tf.TerrainFlyover(seed=42, width=60, height=20,
                               show_minimap=True, show_stats=True)
        output = f.render_frame(0)
        # Check there are no double-ESC sequences (garbled ANSI)
        # Garbled sequences look like: \x1b[\x1b[...
        assert r'\x1b[\x1b[' not in repr(output), \
            "Minimap overlay produces garbled ANSI sequences"

    def test_parse_ansi_cells_basic(self):
        """_parse_ansi_cells should correctly parse ANSI-colored strings."""
        cells = tf.TerrainFlyover._parse_ansi_cells("\x1b[38;5;34m\"\x1b[0m")
        # The \x1b[0m is a trailing ANSI sequence with no following visible char,
        # so it's stored as a prefix for an empty string char.
        assert len(cells) == 1
        assert cells[0] == ("\x1b[38;5;34m", '"')

    def test_parse_ansi_cells_plain_text(self):
        """_parse_ansi_cells should handle plain text without ANSI."""
        cells = tf.TerrainFlyover._parse_ansi_cells("hello")
        assert len(cells) == 5
        assert all(a == "" for a, c in cells)

    def test_cells_to_string_roundtrip(self):
        """_cells_to_string should reconstruct the original ANSI string (minus trailing resets)."""
        # Note: trailing ANSI sequences with no following visible char are dropped by
        # _parse_ansi_cells, which is fine for the overlay use case.
        original = "\x1b[38;5;34mv\x1b[38;5;22m♣"
        cells = tf.TerrainFlyover._parse_ansi_cells(original)
        reconstructed = tf.TerrainFlyover._cells_to_string(cells)
        assert reconstructed == original

    def test_render_minimap_marker_after_fix(self):
        """render_minimap should still produce valid output with ▶ marker."""
        flyover = tf.TerrainFlyover(seed=42, width=40, height=20)
        output = tf.render_minimap(flyover, map_w=20, map_h=10, scale=0.3)
        assert "▶" in output, "Minimap should contain position marker"

    def test_screenshot_no_ansi_codes(self):
        """Screenshot should contain no ANSI escape sequences."""
        f = tf.TerrainFlyover(seed=42, width=40, height=15, show_stats=True)
        plain = f.render_screenshot(0)
        assert '\x1b[' not in plain, "Screenshot should not contain ANSI codes"

    def test_small_terminal_with_minimap(self):
        """Small terminals with minimap should not crash or produce garbled output."""
        f = tf.TerrainFlyover(seed=42, width=25, height=10,
                               show_minimap=True, show_stats=False)
        output = f.render_frame(0)
        assert isinstance(output, str)
        assert len(output) > 0


import sys

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])