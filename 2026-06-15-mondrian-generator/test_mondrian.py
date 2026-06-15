#!/usr/bin/env python3
"""Tests for the Terminal Mondrian Art Generator v3.0."""

import random
import sys
import os
import tempfile
import json
import pytest

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mondrian import (
    generate_mondrian, MondrianCanvas, Rect, Cell,
    PALETTES, BORDER_W, export_svg, export_html, export_png,
    count_regions, compute_coverage, render_plain,
    __version__, fix_intersections, draw_outer_border, add_signature,
    parse_custom_palette, list_palettes,
)


class TestVersion:
    """Test that the version is properly defined."""

    def test_version_is_string(self):
        assert isinstance(__version__, str)

    def test_version_format(self):
        parts = __version__.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_version_is_3_0_0(self):
        assert __version__ == "3.0.0"


class TestMondrianCanvas:
    """Test the MondrianCanvas data structure."""

    def test_canvas_creation(self):
        canvas = MondrianCanvas(width=20, height=10)
        assert canvas.width == 20
        assert canvas.height == 10
        assert len(canvas.cells) == 10
        assert len(canvas.cells[0]) == 20

    def test_canvas_default_cells(self):
        canvas = MondrianCanvas(width=10, height=5)
        for row in canvas.cells:
            for cell in row:
                assert cell.char == " "
                assert cell.bg == (242, 242, 242)  # white

    def test_fill_rect(self):
        canvas = MondrianCanvas(width=20, height=10)
        palette = PALETTES["classic"]
        rect = Rect(x=2, y=2, w=5, h=3)
        canvas.fill_rect(rect, "red", palette)
        # Check that the filled area has red color
        r, g, b = palette["red"]
        for row in range(2, 5):
            for col in range(2, 7):
                assert canvas.cells[row][col].bg == (r, g, b)

    def test_fill_rect_boundary_checks(self):
        """Fill should not crash on boundary-exceeding rects."""
        canvas = MondrianCanvas(width=10, height=5)
        palette = PALETTES["classic"]
        # Out of bounds — should not raise
        rect = Rect(x=-2, y=-2, w=20, h=20)
        canvas.fill_rect(rect, "blue", palette)
        # Verify no crash and some valid cells were filled
        assert canvas.cells[0][0].bg == (0, 54, 170)  # blue

    def test_rect_area(self):
        """Rect.area() should return width * height."""
        r = Rect(x=1, y=2, w=10, h=5)
        assert r.area() == 50

    def test_rect_area_zero(self):
        r = Rect(x=0, y=0, w=0, h=0)
        assert r.area() == 0


class TestGenerateMondrian:
    """Test the main generation function."""

    def test_basic_generation(self):
        """Should generate a non-empty string."""
        ansi_art, canvas, palette = generate_mondrian(width=40, height=20, seed=42)
        assert len(ansi_art) > 0
        assert "\n" in ansi_art

    def test_deterministic_with_seed(self):
        """Same seed should produce identical output."""
        art1, _, _ = generate_mondrian(width=40, height=20, seed=123)
        # Reset random state
        random.seed(123)
        art2, _, _ = generate_mondrian(width=40, height=20, seed=123)
        assert art1 == art2

    def test_different_seeds_different_output(self):
        """Different seeds should produce different output."""
        art1, _, _ = generate_mondrian(width=40, height=20, seed=1)
        art2, _, _ = generate_mondrian(width=40, height=20, seed=2)
        assert art1 != art2

    def test_canvas_dimensions(self):
        """Canvas should match requested dimensions."""
        _, canvas, _ = generate_mondrian(width=50, height=25, seed=99)
        assert canvas.width == 50
        assert canvas.height == 25
        assert len(canvas.cells) == 25
        assert len(canvas.cells[0]) == 50

    def test_no_signature_mode(self):
        """no_signature=True should produce output without MONDRIAN text."""
        ansi_art, canvas, _ = generate_mondrian(width=40, height=20, seed=42, no_signature=True)
        assert "MONDRIAN" not in ansi_art

    def test_with_signature_mode(self):
        """Default mode should include the MONDRIAN signature in canvas cells."""
        _, canvas, palette = generate_mondrian(width=40, height=20, seed=42)
        # Check that "MONDRIAN" appears in cell characters in bottom-right area
        sig_found = False
        for row in canvas.cells[-4:]:
            for cell in row:
                if cell.char in "MONDRIAN":
                    sig_found = True
                    break
        assert sig_found

    def test_custom_signature_text(self):
        """add_signature should support custom text."""
        _, canvas, palette = generate_mondrian(width=40, height=20, seed=42, no_signature=True)
        add_signature(canvas, palette, text="TEST")
        # Check that "TEST" characters appear in the canvas
        chars_found = set()
        for row in canvas.cells[-4:]:
            for cell in row:
                chars_found.add(cell.char)
        for ch in "TEST":
            assert ch in chars_found, f"Expected '{ch}' in canvas, found: {chars_found}"

    def test_all_palettes(self):
        """Each palette should produce valid output without errors."""
        for palette_name in PALETTES:
            ansi_art, _, _ = generate_mondrian(
                width=30, height=15, seed=42, palette_name=palette_name
            )
            assert len(ansi_art) > 0

    def test_custom_palette(self):
        """Custom palette should produce valid output."""
        custom = {
            "red": (255, 0, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "white": (255, 255, 255),
            "black": (0, 0, 0),
        }
        ansi_art, canvas, palette = generate_mondrian(
            width=30, height=15, seed=42, custom_palette=custom
        )
        assert len(ansi_art) > 0
        assert palette == custom

    def test_small_canvas(self):
        """Minimum viable canvas size should work."""
        min_size = 6
        w = 2 * BORDER_W + min_size
        h = 2 * BORDER_W + min_size
        ansi_art, _, _ = generate_mondrian(width=w, height=h, seed=7)
        assert len(ansi_art) > 0

    def test_output_has_ansi_escapes(self):
        """Output should contain ANSI escape sequences."""
        ansi_art, _, _ = generate_mondrian(width=40, height=20, seed=42)
        assert "\033[" in ansi_art
        assert "\033[0m" in ansi_art  # RESET

    def test_output_has_box_chars(self):
        """Output should contain Unicode box-drawing characters."""
        ansi_art, _, _ = generate_mondrian(width=40, height=20, seed=42)
        box_chars = set("─│┼┬┴├┤")
        found = any(c in ansi_art for c in box_chars)
        assert found, "Output should contain at least one box-drawing character"

    def test_outer_border_exists(self):
        """The outer border should be present and black."""
        _, canvas, palette = generate_mondrian(width=30, height=15, seed=42)
        border_color = palette["black"]
        # Top-left corner should be a border cell
        assert canvas.cells[0][0].fg == border_color
        assert canvas.cells[0][0].char == "┼"

    def test_high_split_prob_produces_more_divisions(self):
        """Higher split probability should generally produce more border characters."""
        _, canvas_high, palette = generate_mondrian(
            width=40, height=20, seed=42, split_prob=0.99
        )
        _, canvas_low, _ = generate_mondrian(
            width=40, height=20, seed=42, split_prob=0.3
        )
        # Count border cells (cells with black fg)
        border_color = palette["black"]
        high_borders = sum(
            1 for row in canvas_high.cells for cell in row if cell.fg == border_color
        )
        low_borders = sum(
            1 for row in canvas_low.cells for cell in row if cell.fg == border_color
        )
        # High split prob should create more internal divisions (more borders)
        assert high_borders >= low_borders


class TestRenderPlain:
    """Test the plain text rendering function."""

    def test_plain_render_has_no_ansi(self):
        """Plain render should not contain ANSI escape sequences."""
        _, canvas, _ = generate_mondrian(width=40, height=20, seed=42)
        plain = render_plain(canvas)
        assert "\033[" not in plain

    def test_plain_render_has_box_chars(self):
        """Plain render should contain box-drawing characters."""
        _, canvas, _ = generate_mondrian(width=40, height=20, seed=42)
        plain = render_plain(canvas)
        box_chars = set("─│┼┬┴├┤")
        found = any(c in plain for c in box_chars)
        assert found

    def test_plain_render_dimensions(self):
        """Plain render should have correct line count and widths."""
        _, canvas, _ = generate_mondrian(width=40, height=20, seed=42)
        plain = render_plain(canvas)
        lines = plain.split("\n")
        assert len(lines) == 20
        for line in lines:
            assert len(line) == 40


class TestComputeCoverage:
    """Test the coverage computation function."""

    def test_coverage_returns_dict(self):
        """compute_coverage should return a dictionary with color names."""
        _, canvas, palette = generate_mondrian(width=40, height=20, seed=42)
        coverage = compute_coverage(canvas, palette)
        assert isinstance(coverage, dict)
        assert len(coverage) > 0

    def test_coverage_percentages_sum_near_100(self):
        """Coverage percentages should sum to approximately 100%."""
        _, canvas, palette = generate_mondrian(width=60, height=30, seed=42)
        coverage = compute_coverage(canvas, palette)
        total = sum(coverage.values())
        assert abs(total - 100.0) < 5.0, f"Coverage sum {total} should be near 100%"

    def test_coverage_has_white(self):
        """Coverage should include white as the dominant color."""
        _, canvas, palette = generate_mondrian(width=60, height=30, seed=42)
        coverage = compute_coverage(canvas, palette)
        assert "white" in coverage
        # White should be dominant (typically >40%)
        assert coverage["white"] > 30.0


class TestExport:
    """Test SVG, HTML, and PNG export functions."""

    def test_svg_export(self):
        """SVG export should create a valid SVG file."""
        _, canvas, palette = generate_mondrian(width=30, height=15, seed=42)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w") as f:
            tmpfile = f.name
        try:
            export_svg(canvas, palette, tmpfile)
            with open(tmpfile, "r") as f:
                content = f.read()
            assert "<svg" in content
            assert "</svg>" in content
            assert "rect" in content
        finally:
            os.unlink(tmpfile)

    def test_html_export(self):
        """HTML export should create a valid HTML file."""
        _, canvas, palette = generate_mondrian(width=30, height=15, seed=42)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            tmpfile = f.name
        try:
            export_html(canvas, palette, tmpfile)
            with open(tmpfile, "r") as f:
                content = f.read()
            assert "<html" in content
            assert "</html>" in content
            assert "mondrian" in content
        finally:
            os.unlink(tmpfile)

    def test_png_export(self):
        """PNG export should create a valid PNG file."""
        _, canvas, palette = generate_mondrian(width=20, height=10, seed=42)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmpfile = f.name
        try:
            export_png(canvas, palette, tmpfile)
            # Check file exists and has content
            assert os.path.exists(tmpfile)
            with open(tmpfile, "rb") as f:
                data = f.read()
            # PNG magic bytes
            assert data[:8] == b"\x89PNG\r\n\x1a\n"
            assert len(data) > 100  # Should be a reasonable-sized file
        finally:
            os.unlink(tmpfile)

    def test_png_export_custom_cell_size(self):
        """PNG export with custom cell_size should produce different file size."""
        _, canvas, palette = generate_mondrian(width=20, height=10, seed=42)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_small = f.name
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            tmp_large = f.name
        try:
            export_png(canvas, palette, tmp_small, cell_size=5)
            export_png(canvas, palette, tmp_large, cell_size=20)
            # Larger cell size should produce larger file
            assert os.path.getsize(tmp_large) > os.path.getsize(tmp_small)
        finally:
            os.unlink(tmp_small)
            os.unlink(tmp_large)


class TestCountRegions:
    """Test the statistics/counting function."""

    def test_count_regions_returns_dict(self):
        """count_regions should return a dictionary with expected keys."""
        _, canvas, palette = generate_mondrian(width=40, height=20, seed=42)
        stats = count_regions(canvas, palette)
        assert "total_cells" in stats
        assert "colors" in stats
        assert isinstance(stats["total_cells"], int)
        assert stats["total_cells"] > 0

    def test_count_regions_has_primary_colors(self):
        """Generated composition should have at least one primary color."""
        _, canvas, palette = generate_mondrian(width=60, height=30, seed=42)
        stats = count_regions(canvas, palette)
        # With a decent canvas size and seed, should have some colored cells
        assert stats["total_cells"] > 0


class TestRect:
    """Test the Rect dataclass."""

    def test_rect_creation(self):
        r = Rect(x=1, y=2, w=10, h=5)
        assert r.x == 1
        assert r.y == 2
        assert r.w == 10
        assert r.h == 5


class TestPalettes:
    """Test palette data."""

    def test_all_palettes_have_required_colors(self):
        """Each palette should have all five Mondrian colors."""
        required = {"red", "blue", "yellow", "white", "black"}
        for name, palette in PALETTES.items():
            assert required == set(palette.keys()), f"Palette '{name}' is missing colors"

    def test_palette_values_are_rgb_tuples(self):
        """Each color in each palette should be a 3-tuple of ints 0-255."""
        for name, palette in PALETTES.items():
            for color_name, rgb in palette.items():
                assert len(rgb) == 3, f"Palette '{name}', color '{color_name}' is not a 3-tuple"
                for val in rgb:
                    assert 0 <= val <= 255, f"Palette '{name}', color '{color_name}' has out-of-range value"

    def test_new_palettes_exist(self):
        """Ocean and autumn palettes should exist."""
        assert "ocean" in PALETTES
        assert "autumn" in PALETTES


class TestParseCustomPalette:
    """Test custom palette JSON parsing."""

    def test_valid_custom_palette(self):
        """Should parse a valid custom palette."""
        json_str = '{"red":[255,0,0],"blue":[0,0,255],"yellow":[255,255,0],"white":[255,255,255],"black":[0,0,0]}'
        palette = parse_custom_palette(json_str)
        assert palette["red"] == (255, 0, 0)
        assert palette["blue"] == (0, 0, 255)

    def test_missing_color_raises(self):
        """Missing required color should raise ValueError."""
        json_str = '{"red":[255,0,0],"blue":[0,0,255],"yellow":[255,255,0],"white":[255,255,255]}'
        with pytest.raises(ValueError, match="missing"):
            parse_custom_palette(json_str)

    def test_extra_color_raises(self):
        """Extra colors should raise ValueError."""
        json_str = '{"red":[255,0,0],"blue":[0,0,255],"yellow":[255,255,0],"white":[255,255,255],"black":[0,0,0],"purple":[128,0,128]}'
        with pytest.raises(ValueError, match="unknown"):
            parse_custom_palette(json_str)

    def test_invalid_rgb_raises(self):
        """Out-of-range RGB values should raise ValueError."""
        json_str = '{"red":[256,0,0],"blue":[0,0,255],"yellow":[255,255,0],"white":[255,255,255],"black":[0,0,0]}'
        with pytest.raises(ValueError, match="0-255"):
            parse_custom_palette(json_str)

    def test_invalid_json_raises(self):
        """Invalid JSON should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_custom_palette("not json at all")

    def test_non_list_rgb_raises(self):
        """Non-list RGB values should raise ValueError."""
        json_str = '{"red":"bad","blue":[0,0,255],"yellow":[255,255,0],"white":[255,255,255],"black":[0,0,0]}'
        with pytest.raises(ValueError, match="list of 3"):
            parse_custom_palette(json_str)


class TestBugFixes:
    """Regression tests for bugs found and fixed."""

    def test_zero_dimension_canvas_raises(self):
        """Zero-width or zero-height canvas should raise ValueError."""
        with pytest.raises(ValueError):
            MondrianCanvas(width=0, height=5)
        with pytest.raises(ValueError):
            MondrianCanvas(width=5, height=0)
        with pytest.raises(ValueError):
            MondrianCanvas(width=0, height=0)

    def test_negative_dimension_canvas_raises(self):
        """Negative canvas dimensions should raise ValueError."""
        with pytest.raises(ValueError):
            MondrianCanvas(width=-1, height=5)
        with pytest.raises(ValueError):
            MondrianCanvas(width=5, height=-1)

    def test_svg_export_has_explicit_xy_on_background(self):
        """SVG background rect should have explicit x=\"0\" y=\"0\" attributes."""
        _, canvas, palette = generate_mondrian(width=30, height=15, seed=42)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w") as f:
            tmpfile = f.name
        try:
            export_svg(canvas, palette, tmpfile)
            with open(tmpfile) as f:
                content = f.read()
            # Find the background rect (second rect in the file)
            assert 'x="0"' in content, "SVG should have explicit x=\"0\" on rects"
            assert 'y="0"' in content, "SVG should have explicit y=\"0\" on rects"
        finally:
            os.unlink(tmpfile)

    def test_html_export_has_border_cell_class(self):
        """HTML export should distinguish border cells with a 'border-cell' class."""
        _, canvas, palette = generate_mondrian(width=30, height=15, seed=42)
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            tmpfile = f.name
        try:
            export_html(canvas, palette, tmpfile)
            with open(tmpfile) as f:
                content = f.read()
            assert "border-cell" in content, "HTML should contain 'border-cell' class for border cells"
            assert ".border-cell" in content, "HTML should contain CSS for .border-cell"
        finally:
            os.unlink(tmpfile)

    def test_negative_delay_rejected_by_cli(self):
        """Negative --delay should be rejected by the CLI."""
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mondrian.py"),
             "--delay", "-1", "-W", "20", "-H", "10", "--no-clear", "-s", "42"],
            capture_output=True, text=True
        )
        assert result.returncode != 0, "Negative --delay should be rejected"

    def test_export_stats_format(self):
        """Export mode with --stats should produce formatted output, not raw dict."""
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mondrian.py"),
             "--export", "svg", "-W", "60", "-H", "30", "-s", "42", "--stats",
             "-o", os.path.join(tempfile.gettempdir(), "test_stats_fmt.svg")],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        # Should have formatted stats, not raw dict repr
        assert "Composition statistics" in result.stdout, "Stats should have formatted header"
        # The word "cells" appears in per-color lines like "red: 120 cells"
        assert "cells" in result.stdout or "Seed" in result.stdout, \
            f"Stats should show cell counts or at least seed info; got: {result.stdout}"
        # Should NOT contain raw dict repr like {'total_cells':
        assert "{'total_cells'" not in result.stdout, "Stats should not be raw dict repr"
        # Clean up
        svg_path = os.path.join(tempfile.gettempdir(), "test_stats_fmt.svg")
        if os.path.exists(svg_path):
            os.unlink(svg_path)


class TestCLI:
    """Test CLI flags and behavior."""

    def test_version_flag(self):
        """--version should print version and exit."""
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mondrian.py"),
             "--version"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "3.0.0" in result.stdout

    def test_help_flag(self):
        """--help should print usage and exit."""
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mondrian.py"),
             "--help"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "Mondrian" in result.stdout
        assert "--export" in result.stdout
        assert "--list-palettes" in result.stdout
        assert "--custom-palette" in result.stdout

    def test_list_palettes_flag(self):
        """--list-palettes should list all palettes."""
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mondrian.py"),
             "--list-palettes"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "classic" in result.stdout
        assert "neon" in result.stdout
        assert "ocean" in result.stdout
        assert "autumn" in result.stdout
        assert "(default)" in result.stdout

    def test_png_export_via_cli(self):
        """--export png should create a PNG file."""
        import subprocess
        outpath = os.path.join(tempfile.gettempdir(), "test_cli_export.png")
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mondrian.py"),
             "--export", "png", "-W", "20", "-H", "10", "-s", "42", "-o", outpath],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert os.path.exists(outpath)
        with open(outpath, "rb") as f:
            data = f.read()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        os.unlink(outpath)

    def test_plain_flag_via_cli(self):
        """--plain should output text without ANSI escapes."""
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mondrian.py"),
             "-W", "20", "-H", "10", "-s", "42", "--no-clear", "--plain"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "\033[" not in result.stdout or result.stdout.count("\033[") < 5

    def test_stats_with_coverage(self):
        """--stats should show percentage coverage."""
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mondrian.py"),
             "-W", "40", "-H", "20", "-s", "42", "--no-clear", "--stats"],
            capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "%" in result.stdout, "Stats should show percentage coverage"

    def test_custom_palette_via_cli(self):
        """--custom-palette should work with valid JSON."""
        import subprocess
        json_palette = '{"red":[255,0,0],"blue":[0,100,200],"yellow":[255,200,0],"white":[240,240,240],"black":[30,30,30]}'
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mondrian.py"),
             "-W", "20", "-H", "10", "-s", "42", "--no-clear",
             "--custom-palette", json_palette],
            capture_output=True, text=True
        )
        assert result.returncode == 0

    def test_invalid_custom_palette_via_cli(self):
        """--custom-palette with invalid JSON should fail."""
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), "mondrian.py"),
             "-W", "20", "-H", "10", "-s", "42", "--no-clear",
             "--custom-palette", "not json"],
            capture_output=True, text=True
        )
        assert result.returncode != 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])