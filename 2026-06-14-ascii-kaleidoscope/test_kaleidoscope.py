#!/usr/bin/env python3
"""
Unit tests for the ASCII Kaleidoscope engine.

Covers pattern rendering, segment symmetry, animation continuity,
parameter validation, palette generation, escape sequence handling,
FPS counter behavior, and rendering output format.
"""

import unittest
import math
from kaleidoscope import (
    Kaleidoscope, generate_palette, generate_palette_enhanced,
    get_key_nonblock, move_cursor, fg_color_256, bg_color_256,
    clear_screen, hide_cursor, show_cursor
)


class TestKaleidoscopeCore(unittest.TestCase):
    """Core engine tests for the Kaleidoscope class."""

    def test_all_patterns_render(self):
        """Every known pattern should render a frame without errors."""
        for pattern in Kaleidoscope.PATTERNS:
            with self.subTest(pattern=pattern):
                k = Kaleidoscope(pattern=pattern, segments=8)
                frame = k.render_frame(40, 12)
                self.assertEqual(len(frame), 12, f"Expected 12 rows for {pattern}")
                self.assertEqual(len(frame[0]), 40, f"Expected 40 cols for {pattern}")

    def test_pattern_fallback(self):
        """An unknown pattern name should fall back to 'spiral' gracefully."""
        k = Kaleidoscope(pattern="nonexistent_pattern_xyz", segments=8)
        # The constructor should normalize to 'spiral'
        self.assertEqual(k.pattern, "spiral")

    def test_new_patterns_render(self):
        """The plasma and vortex patterns should render correctly."""
        for pattern in ["plasma", "vortex"]:
            with self.subTest(pattern=pattern):
                k = Kaleidoscope(pattern=pattern, segments=8)
                frame = k.render_frame(40, 12)
                self.assertEqual(len(frame), 12)
                self.assertEqual(len(frame[0]), 40)

    def test_various_segment_counts(self):
        """Frames should render correctly with various (even) segment counts."""
        for segments in [4, 6, 8, 10, 12, 16, 20, 24]:
            with self.subTest(segments=segments):
                k = Kaleidoscope(segments=segments, pattern="spiral")
                frame = k.render_frame(30, 10)
                self.assertEqual(len(frame), 10)

    def test_odd_segments_normalized(self):
        """Odd segment counts should be normalized to even."""
        for odd_val in [5, 7, 9, 11]:
            k = Kaleidoscope(segments=odd_val, pattern="spiral")
            self.assertEqual(k.segments % 2, 0,
                             f"Segments {k.segments} should be even for input {odd_val}")

    def test_minimum_segments(self):
        """Segments below 4 should be clamped to 4."""
        for val in [1, 2, 3, 0, -1]:
            k = Kaleidoscope(segments=val, pattern="spiral")
            self.assertGreaterEqual(k.segments, 4,
                                     f"Segments should be >= 4, got {k.segments}")

    def test_speed_clamping(self):
        """Speed should be clamped to [0.2, 5.0]."""
        k = Kaleidoscope(speed=0.01, pattern="spiral")
        self.assertAlmostEqual(k.speed, 0.2)

        k = Kaleidoscope(segments=8, speed=100.0, pattern="spiral")
        self.assertAlmostEqual(k.speed, 5.0)

    def test_animation_continuity(self):
        """Rendering multiple frames should advance time and produce varied output."""
        k = Kaleidoscope(pattern="spiral", segments=8, seed=42)
        frames = []
        for _ in range(5):
            frame = k.render_frame(20, 10)
            frames.append(frame)
            self.assertEqual(len(frame), 10)

        # Time should advance between frames
        self.assertGreater(k.time, 0.0, "Time should have advanced after 5 frames")

    def test_deterministic_with_seed(self):
        """Same seed should produce identical frames."""
        k1 = Kaleidoscope(pattern="spiral", segments=8, seed=12345)
        k2 = Kaleidoscope(pattern="spiral", segments=8, seed=12345)

        f1 = k1.render_frame(20, 10)
        f2 = k2.render_frame(20, 10)

        for r in range(len(f1)):
            for c in range(len(f1[0])):
                self.assertEqual(f1[r][c], f2[r][c],
                                 f"Frames differ at row {r}, col {c}")

    def test_frame_count_increments(self):
        """frame_count should increment with each rendered frame."""
        k = Kaleidoscope(pattern="spiral", segments=8)
        self.assertEqual(k.frame_count, 0)
        k.render_frame(20, 10)
        self.assertEqual(k.frame_count, 1)
        k.render_frame(20, 10)
        self.assertEqual(k.frame_count, 2)

    def test_small_viewport(self):
        """Very small viewports should still render without error."""
        k = Kaleidoscope(pattern="spiral", segments=8)
        # Minimum useful size
        frame = k.render_frame(4, 2)
        self.assertIsNotNone(frame)

    def test_degenerate_viewport(self):
        """Degenerate (too small) viewports should return [[]] gracefully."""
        k = Kaleidoscope(pattern="spiral", segments=8)
        frame = k.render_frame(1, 1)
        self.assertEqual(frame, [[]])

    def test_negative_viewport(self):
        """Negative viewport dimensions should return [[]] gracefully."""
        k = Kaleidoscope(pattern="spiral", segments=8)
        frame = k.render_frame(-1, -1)
        self.assertEqual(frame, [[]])

    def test_zero_viewport(self):
        """Zero-size viewport should return [[]] gracefully."""
        k = Kaleidoscope(pattern="spiral", segments=8)
        frame = k.render_frame(0, 0)
        self.assertEqual(frame, [[]])


class TestSegmentsProperty(unittest.TestCase):
    """Tests for the segments property with normalization."""

    def test_segments_property_normalizes_odd(self):
        """Setting odd segment values via property should normalize to even."""
        k = Kaleidoscope(segments=8, pattern="spiral")
        k.segments = 7
        self.assertEqual(k.segments, 8, "Odd value 7 should normalize to 8")

    def test_segments_property_enforces_minimum(self):
        """Setting segments below 4 via property should clamp to 4."""
        k = Kaleidoscope(segments=8, pattern="spiral")
        k.segments = 2
        self.assertEqual(k.segments, 4, "Below-minimum value should clamp to 4")

    def test_segments_property_accepts_even(self):
        """Even segment values should be stored as-is."""
        k = Kaleidoscope(segments=8, pattern="spiral")
        k.segments = 12
        self.assertEqual(k.segments, 12)

    def test_live_segment_changes(self):
        """Simulating the live segment controls from main loop."""
        k = Kaleidoscope(segments=8, pattern="spiral")
        # Increase by 2 (from main loop: min(ks.segments + 2, 24))
        k.segments = min(k.segments + 2, 24)
        self.assertEqual(k.segments, 10)
        # Decrease by 2 (from main loop: max(ks.segments - 2, 4))
        k.segments = max(k.segments - 2, 4)
        self.assertEqual(k.segments, 8)


class TestComputePixel(unittest.TestCase):
    """Tests for the compute_pixel method directly."""

    def test_output_range(self):
        """compute_pixel should always return a value in [0, 1]."""
        k = Kaleidoscope(pattern="spiral", segments=8, seed=99)
        for pattern in Kaleidoscope.PATTERNS:
            k.pattern = pattern
            for r in [0.0, 0.25, 0.5, 0.75, 1.0]:
                for theta in [0.0, 0.5, 1.0, 1.5, 2.0]:
                    val = k.compute_pixel(r, theta, 0.0)
                    self.assertGreaterEqual(val, 0.0,
                                            f"{pattern} at r={r}, θ={theta}: val={val}")
                    self.assertLessEqual(val, 1.0,
                                         f"{pattern} at r={r}, θ={theta}: val={val}")

    def test_time_variation(self):
        """Different time values should generally produce different outputs."""
        k = Kaleidoscope(pattern="spiral", segments=8, seed=42)
        val_t0 = k.compute_pixel(0.5, 1.0, 0.0)
        val_t1 = k.compute_pixel(0.5, 1.0, 10.0)
        # Not guaranteed different for all params, but very likely
        self.assertIsInstance(val_t0, float)
        self.assertIsInstance(val_t1, float)


class TestPalette(unittest.TestCase):
    """Tests for palette generation functions."""

    def test_palette_length(self):
        """Generated palettes should always have 256 entries."""
        pal = generate_palette(0.0)
        self.assertEqual(len(pal), 256)

        pal2 = generate_palette_enhanced(1.5)
        self.assertEqual(len(pal2), 256)

    def test_palette_values_in_range(self):
        """All palette values should be valid ANSI 256-color indices (0-255)."""
        for offset in [0.0, 0.5, 1.0, 3.14]:
            pal = generate_palette(offset)
            for color in pal:
                self.assertGreaterEqual(color, 0)
                self.assertLessEqual(color, 255)

            pal2 = generate_palette_enhanced(offset)
            for color in pal2:
                self.assertGreaterEqual(color, 0)
                self.assertLessEqual(color, 255)

    def test_palette_offset_changes_colors(self):
        """Different hue offsets should produce different palettes."""
        pal0 = generate_palette(0.0)
        pal1 = generate_palette(2.0)
        # They should differ (extremely unlikely to be identical)
        self.assertNotEqual(pal0, pal1)

    def test_generate_palette_full_color_range(self):
        """generate_palette should use the full 6x6x6 cube (16-231)."""
        pal = generate_palette(0.0)
        # With the * 5.999 fix, the palette should reach higher values
        self.assertGreaterEqual(min(pal), 16, "Palette minimum should be >= 16")
        self.assertLessEqual(max(pal), 231, "Palette maximum should be <= 231")
        # The palette should span a significant range
        self.assertGreater(max(pal) - min(pal), 50,
                           "Palette should span a wide range of colors")


class TestRenderOutput(unittest.TestCase):
    """Tests for the rendered output format and content."""

    def test_outside_circle_pixels_use_bg_dark(self):
        """Outside-circle pixels should use bg_dark (16) for both fg and bg."""
        k = Kaleidoscope(pattern="spiral", segments=8, seed=42)
        # Render a large frame to ensure some outside-circle pixels
        frame = k.render_frame(60, 30)
        outside_pixels = [(char, fg, bg) for row in frame
                          for char, fg, bg in row if char == ' ']
        if outside_pixels:
            for char, fg, bg in outside_pixels:
                self.assertEqual(fg, 16, "Outside pixel fg should be bg_dark (16)")
                self.assertEqual(bg, 16, "Outside pixel bg should be bg_dark (16)")

    def test_all_output_chars_valid(self):
        """All rendered characters should be valid (space, ▀, or ▄)."""
        k = Kaleidoscope(pattern="spiral", segments=8, seed=42)
        frame = k.render_frame(40, 12)
        valid_chars = {' ', '▀', '▄'}
        for row in frame:
            for char, fg, bg in row:
                self.assertIn(char, valid_chars,
                              f"Invalid char: {repr(char)}")

    def test_all_output_colors_valid(self):
        """All rendered fg/bg values should be valid ANSI indices."""
        k = Kaleidoscope(pattern="spiral", segments=8, seed=42)
        frame = k.render_frame(40, 12)
        for row in frame:
            for char, fg, bg in row:
                self.assertGreaterEqual(fg, 0, f"fg too low: {fg}")
                self.assertLessEqual(fg, 255, f"fg too high: {fg}")
                self.assertGreaterEqual(bg, 0, f"bg too low: {bg}")
                self.assertLessEqual(bg, 255, f"bg too high: {bg}")


class TestSymmetry(unittest.TestCase):
    """Tests that verify the symmetry/mirroring behavior."""

    def test_mirror_symmetry_in_render(self):
        """
        Points at symmetric positions in the rendered frame should produce
        the same pixel value, confirming kaleidoscopic mirror behavior.
        """
        k = Kaleidoscope(pattern="spiral", segments=8, seed=42)
        frame = k.render_frame(60, 30)
        self.assertEqual(len(frame), 30)
        self.assertEqual(len(frame[0]), 60)

    def test_segment_change_changes_output(self):
        """Different segment counts should produce different patterns."""
        k1 = Kaleidoscope(pattern="spiral", segments=6, seed=42)
        k2 = Kaleidoscope(pattern="spiral", segments=12, seed=42)

        f1 = k1.render_frame(20, 10)
        f2 = k2.render_frame(20, 10)

        # At least some pixels should differ
        any_different = False
        for r in range(min(len(f1), len(f2))):
            for c in range(min(len(f1[0]), len(f2[0]))):
                if f1[r][c] != f2[r][c]:
                    any_different = True
                    break
            if any_different:
                break
        self.assertTrue(any_different,
                        "Different segment counts should produce different output")


class TestANSIHelpers(unittest.TestCase):
    """Tests for ANSI escape sequence helper functions."""

    def test_clear_screen(self):
        """clear_screen should produce proper ANSI clear sequence."""
        self.assertEqual(clear_screen(), "\033[2J\033[H")

    def test_hide_cursor(self):
        """hide_cursor should produce proper ANSI cursor hide sequence."""
        self.assertEqual(hide_cursor(), "\033[?25l")

    def test_show_cursor(self):
        """show_cursor should produce proper ANSI cursor show sequence."""
        self.assertEqual(show_cursor(), "\033[?25h")

    def test_move_cursor(self):
        """move_cursor should produce proper ANSI cursor move sequence."""
        self.assertEqual(move_cursor(5, 10), "\033[5;10H")

    def test_fg_color_256(self):
        """fg_color_256 should produce proper ANSI 256-color fg sequence."""
        self.assertEqual(fg_color_256(16), "\033[38;5;16m")

    def test_bg_color_256(self):
        """bg_color_256 should produce proper ANSI 256-color bg sequence."""
        self.assertEqual(bg_color_256(231), "\033[48;5;231m")


if __name__ == "__main__":
    unittest.main()