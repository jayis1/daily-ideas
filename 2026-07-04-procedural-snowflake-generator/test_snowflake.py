#!/usr/bin/env python3
"""Tests for procedural snowflake generator."""

import math
import os
import subprocess
import sys
import tempfile

# Add parent dir to path
sys.path.insert(0, os.path.dirname(__file__))

from snowflake import (
    SeededRNG, Segment, generate_snowflake, segments_to_points,
    render_snowflake, export_svg, generate_gallery, PALETTES
)


class TestSeededRNG:
    def test_deterministic(self):
        """Same seed produces same sequence."""
        r1 = SeededRNG("test")
        r2 = SeededRNG("test")
        vals1 = [r1.random() for _ in range(20)]
        vals2 = [r2.random() for _ in range(20)]
        assert vals1 == vals2, "Same seed should produce same random values"

    def test_different_seeds(self):
        """Different seeds produce different sequences."""
        r1 = SeededRNG("alpha")
        r2 = SeededRNG("beta")
        vals1 = [r1.random() for _ in range(20)]
        vals2 = [r2.random() for _ in range(20)]
        assert vals1 != vals2, "Different seeds should produce different values"

    def test_randint_range(self):
        """randint returns values in range."""
        r = SeededRNG("range_test")
        for _ in range(100):
            val = r.randint(3, 7)
            assert 3 <= val <= 7, f"randint out of range: {val}"

    def test_uniform_range(self):
        """uniform returns values in range."""
        r = SeededRNG("uniform_test")
        for _ in range(100):
            val = r.uniform(0.5, 1.5)
            assert 0.5 <= val <= 1.5, f"uniform out of range: {val}"

    def test_choice(self):
        """choice returns elements from the sequence."""
        r = SeededRNG("choice_test")
        seq = [1, 2, 3, 4, 5]
        for _ in range(20):
            val = r.choice(seq)
            assert val in seq, f"choice returned value not in sequence: {val}"


class TestSegment:
    def test_creation(self):
        seg = Segment(0, 0, 1, 0, depth=0, branch_type="center")
        assert seg.r1 == 0
        assert seg.r2 == 1
        assert seg.depth == 0
        assert seg.branch_type == "center"


class TestGenerateSnowflake:
    def test_generates_segments(self):
        segments, ctype = generate_snowflake("test_seed")
        assert len(segments) > 0, "Should generate some segments"
        assert ctype in ["dendrite", "plate", "stellar", "fernlike", "columnar"]

    def test_different_seeds_different_results(self):
        s1, c1 = generate_snowflake("seed_a")
        s2, c2 = generate_snowflake("seed_b")
        # At least the count should differ (very likely)
        assert len(s1) != len(s2) or c1 != c2, "Different seeds should likely produce different results"

    def test_deterministic(self):
        s1, c1 = generate_snowflake("deterministic")
        s2, c2 = generate_snowflake("deterministic")
        assert c1 == c2
        assert len(s1) == len(s2)

    def test_crystal_types(self):
        """All crystal types should be generatable."""
        types_seen = set()
        for i in range(50):
            _, ctype = generate_snowflake(f"type_test_{i}")
            types_seen.add(ctype)
        # Should hit most types in 50 tries
        assert len(types_seen) >= 3, f"Expected at least 3 crystal types, got {types_seen}"

    def test_max_depth_controls_complexity(self):
        s1, _ = generate_snowflake("depth_test", max_depth=1)
        s2, _ = generate_snowflake("depth_test", max_depth=4)
        assert len(s2) >= len(s1), "Higher depth should produce at least as many segments"


class TestSegmentsToPoints:
    def test_produces_points(self):
        segments, _ = generate_snowflake("render_test")
        points, cx, cy = segments_to_points(segments, canvas_size=31)
        assert len(points) > 0, "Should produce some rendered points"
        assert cx == 15, "Center x should be canvas_size // 2"
        assert cy == 15

    def test_center_in_points(self):
        segments, _ = generate_snowflake("center_test")
        points, cx, cy = segments_to_points(segments, canvas_size=31)
        assert (cx, cy) in points, "Center point should be in output"


class TestRenderSnowflake:
    def test_renders_without_crash(self):
        segments, ctype = generate_snowflake("render_crash")
        output = render_snowflake(segments, ctype, "render_crash",
                                  canvas_size=31, color=False)
        assert len(output) > 0
        assert "◆" in output

    def test_render_with_color(self):
        segments, ctype = generate_snowflake("color_test")
        output = render_snowflake(segments, ctype, "color_test",
                                  canvas_size=31, color=True)
        # Should contain ANSI codes
        assert "\033[" in output

    def test_render_no_info(self):
        segments, ctype = generate_snowflake("noinfo")
        output = render_snowflake(segments, ctype, "noinfo",
                                  canvas_size=31, color=False, show_info=False)
        # Should not contain the header
        assert "Procedural Snowflake" not in output


class TestExportSVG:
    def test_creates_file(self):
        segments, ctype = generate_snowflake("svg_test")
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        try:
            result = export_svg(segments, ctype, "svg_test", filename=fname)
            assert result == fname
            assert os.path.exists(fname)
            with open(fname) as f:
                content = f.read()
            assert "<svg" in content
            assert "</svg>" in content
            assert "svg_test" in content
        finally:
            os.unlink(fname)


class TestGallery:
    def test_gallery_output(self):
        seeds = ["gallery_a", "gallery_b", "gallery_c"]
        output = generate_gallery(seeds, palette="frost", width=21)
        assert len(output) > 0
        assert "Snowflake Gallery" in output


class TestPalettes:
    def test_all_palettes_exist(self):
        for name in ["frost", "aurora", "ice", "ember", "violet", "mono"]:
            assert name in PALETTES

    def test_palette_colors(self):
        for name, colors in PALETTES.items():
            assert len(colors) > 0
            for c in colors:
                assert c.startswith("\033[")


class TestCLI:
    def test_help(self):
        result = subprocess.run(
            [sys.executable, "snowflake.py", "--help"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        assert result.returncode == 0
        assert "snowflake" in result.stdout.lower() or "seed" in result.stdout.lower()

    def test_seed_output(self):
        result = subprocess.run(
            [sys.executable, "snowflake.py", "-s", "cli_test", "--no-color", "--size", "21"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        assert result.returncode == 0
        assert "cli_test" in result.stdout
        assert "◆" in result.stdout

    def test_gallery_cli(self):
        result = subprocess.run(
            [sys.executable, "snowflake.py", "-s", "gal", "--gallery", "2", "--no-color"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        assert result.returncode == 0
        assert "Gallery" in result.stdout

    def test_info_flag(self):
        result = subprocess.run(
            [sys.executable, "snowflake.py", "-s", "info_test", "--info", "--no-color", "--size", "21"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        assert result.returncode == 0
        assert "Crystal Report" in result.stdout
        assert "info_test" in result.stdout


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])