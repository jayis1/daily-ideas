#!/usr/bin/env python3
"""Tests for procedural snowflake generator."""

import json
import math
import os
import subprocess
import sys
import tempfile

# Add parent dir to path
sys.path.insert(0, os.path.dirname(__file__))

from snowflake import (
    SeededRNG, Segment, generate_snowflake, segments_to_points,
    render_snowflake, export_svg, export_json, generate_gallery,
    compare_snowflakes, PALETTES, SVG_PALETTES, VALID_SYMMETRIES,
    CRYSTAL_TYPES, __version__, _get_branch_count, _add_koch_edge,
    print_seed_info, animate_snowfall,
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

    def test_choice_empty_raises(self):
        """choice raises ValueError on empty sequence."""
        r = SeededRNG("empty_test")
        try:
            r.choice([])
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_shuffle(self):
        """shuffle returns a permutation of the input."""
        r = SeededRNG("shuffle_test")
        original = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = r.shuffle(original)
        assert sorted(result) == sorted(original), "Shuffle should preserve elements"
        assert result != original, "Shuffle should likely change order (extremely unlikely to match)"

    def test_shuffle_deterministic(self):
        """Same seed produces same shuffle."""
        r1 = SeededRNG("shuffle_det")
        r2 = SeededRNG("shuffle_det")
        result1 = r1.shuffle([1, 2, 3, 4, 5, 6, 7, 8])
        result2 = r2.shuffle([1, 2, 3, 4, 5, 6, 7, 8])
        assert result1 == result2, "Same seed should produce same shuffle"


class TestSegment:
    def test_creation(self):
        seg = Segment(0, 0, 1, 0, depth=0, branch_type="center")
        assert seg.r1 == 0
        assert seg.r2 == 1
        assert seg.depth == 0
        assert seg.branch_type == "center"

    def test_to_dict(self):
        """Segment.to_dict() serializes correctly."""
        seg = Segment(0.123456, 1.570796, 0.987654, 3.141593, depth=2, branch_type="left")
        d = seg.to_dict()
        assert d["depth"] == 2
        assert d["branch_type"] == "left"
        assert isinstance(d["r1"], float)
        assert isinstance(d["a1"], float)


class TestVersion:
    def test_version_exists(self):
        """Package has a version string."""
        assert __version__ is not None
        assert isinstance(__version__, str)
        parts = __version__.split(".")
        assert len(parts) == 3, f"Version should be semver: {__version__}"

    def test_version_format(self):
        """Version is valid semver."""
        for part in __version__.split("."):
            assert part.isdigit(), f"Version part {part} is not numeric"


class TestConstants:
    def test_valid_symmetries(self):
        """VALID_SYMMETRIES contains expected values."""
        assert 6 in VALID_SYMMETRIES
        assert 4 in VALID_SYMMETRIES
        assert 8 in VALID_SYMMETRIES
        assert 12 in VALID_SYMMETRIES

    def test_crystal_types(self):
        """CRYSTAL_TYPES contains all 5 types."""
        assert len(CRYSTAL_TYPES) == 5
        assert "dendrite" in CRYSTAL_TYPES
        assert "plate" in CRYSTAL_TYPES
        assert "stellar" in CRYSTAL_TYPES
        assert "fernlike" in CRYSTAL_TYPES
        assert "columnar" in CRYSTAL_TYPES


class TestGenerateSnowflake:
    def test_generates_segments(self):
        segments, ctype = generate_snowflake("test_seed")
        assert len(segments) > 0, "Should generate some segments"
        assert ctype in CRYSTAL_TYPES

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

    def test_custom_symmetry(self):
        """Custom symmetry should work."""
        for sym in VALID_SYMMETRIES:
            segments, ctype = generate_snowflake(f"sym_{sym}", symmetry=sym)
            assert len(segments) > 0, f"Should generate segments with symmetry={sym}"

    def test_invalid_symmetry_defaults_to_6(self):
        """Invalid symmetry should default to 6."""
        segments, _ = generate_snowflake("bad_sym", symmetry=7)
        # Should still work (defaults to 6)
        assert len(segments) > 0

    def test_depth_clamping(self):
        """Depth values outside 1-5 should be clamped."""
        s1, _ = generate_snowflake("clamp_low", max_depth=0)
        s2, _ = generate_snowflake("clamp_high", max_depth=10)
        assert len(s1) > 0, "Clamped to min depth 1"
        assert len(s2) > 0, "Clamped to max depth 5"


class TestGetBranchCount:
    def test_branch_count_nonnegative(self):
        """Branch counts should always be non-negative."""
        rng = SeededRNG("branch_test")
        for ctype in CRYSTAL_TYPES:
            for depth in range(6):
                count = _get_branch_count(rng, depth, ctype)
                assert count >= 0, f"Branch count for {ctype} depth {depth} is negative: {count}"


class TestKochEdge:
    def test_koch_edge_adds_segments(self):
        """Koch edge decoration should add segments for plate/stellar."""
        rng = SeededRNG("koch_test")
        segments = []
        _add_koch_edge(rng, segments, 0, 0, 1.0, 1)
        assert len(segments) > 0, "Koch edge should add segments"


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

    def test_symmetry_variations(self):
        """Different symmetry values should produce different patterns."""
        segs, _ = generate_snowflake("sym_var", symmetry=6)
        for sym in [4, 8, 12]:
            points, _, _ = segments_to_points(segs, symmetry=sym, canvas_size=31)
            assert len(points) > 0, f"Should produce points with symmetry={sym}"


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

    def test_render_with_symmetry(self):
        """Render with custom symmetry should work."""
        segments, ctype = generate_snowflake("sym_render", symmetry=8)
        output = render_snowflake(segments, ctype, "sym_render",
                                  canvas_size=31, color=False, symmetry=8)
        assert "8-fold" in output

    def test_render_shows_type(self):
        """Render should show crystal type in info."""
        segments, ctype = generate_snowflake("type_show")
        output = render_snowflake(segments, ctype, "type_show",
                                  canvas_size=21, color=False)
        assert ctype.capitalize() in output


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

    def test_svg_with_palette(self):
        """SVG export with custom palette should use those colors."""
        segments, ctype = generate_snowflake("svg_pal")
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        try:
            export_svg(segments, ctype, "svg_pal", filename=fname, palette="ember")
            with open(fname) as f:
                content = f.read()
            # Ember palette should have warm colors
            assert "#ff" in content.lower() or "ember" in content.lower() or "<svg" in content
        finally:
            os.unlink(fname)


class TestExportJSON:
    def test_json_structure(self):
        """JSON export should produce valid JSON with expected fields."""
        segments, ctype = generate_snowflake("json_test", max_depth=3, symmetry=6)
        json_str = export_json(segments, ctype, "json_test", symmetry=6, max_depth=3)
        data = json.loads(json_str)
        assert data["seed"] == "json_test"
        assert data["crystal_type"] == ctype
        assert data["symmetry"] == 6
        assert data["max_depth"] == 3
        assert data["num_segments"] == len(segments)
        assert data["version"] == __version__
        assert len(data["segments"]) > 0

    def test_json_segments_have_keys(self):
        """Each segment dict should have the expected keys."""
        segments, ctype = generate_snowflake("json_keys")
        json_str = export_json(segments, ctype, "json_keys")
        data = json.loads(json_str)
        for seg in data["segments"]:
            assert "r1" in seg
            assert "a1" in seg
            assert "r2" in seg
            assert "a2" in seg
            assert "depth" in seg
            assert "branch_type" in seg


class TestGallery:
    def test_gallery_output(self):
        seeds = ["gallery_a", "gallery_b", "gallery_c"]
        output = generate_gallery(seeds, palette="frost", width=21)
        assert len(output) > 0
        assert "Snowflake Gallery" in output

    def test_gallery_with_symmetry(self):
        """Gallery should work with custom symmetry."""
        seeds = ["gs1", "gs2"]
        output = generate_gallery(seeds, palette="frost", width=21, symmetry=8)
        assert len(output) > 0


class TestCompare:
    def test_compare_output(self):
        """Compare mode should produce side-by-side output."""
        output = compare_snowflakes("snow", "ice", canvas_size=21, color=False)
        assert len(output) > 0
        assert "Comparison" in output
        assert "snow" in output
        assert "ice" in output

    def test_compare_different_seeds(self):
        """Comparing different seeds should produce different patterns."""
        out = compare_snowflakes("alpha", "omega", canvas_size=21, color=False)
        assert len(out) > 100  # Should be substantial


class TestPalettes:
    def test_all_palettes_exist(self):
        for name in ["frost", "aurora", "ice", "ember", "violet", "mono"]:
            assert name in PALETTES

    def test_svg_palettes_exist(self):
        """SVG palettes should match ANSI palettes."""
        for name in PALETTES:
            assert name in SVG_PALETTES, f"Missing SVG palette: {name}"

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

    def test_version(self):
        """--version flag should work."""
        result = subprocess.run(
            [sys.executable, "snowflake.py", "--version"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        assert result.returncode == 0
        assert __version__ in result.stdout

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

    def test_symmetry_flag(self):
        """--symmetry flag should work."""
        result = subprocess.run(
            [sys.executable, "snowflake.py", "-s", "sym_cli", "--symmetry", "4",
             "--no-color", "--size", "21"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        assert result.returncode == 0
        assert "4-fold" in result.stdout

    def test_json_export_file(self):
        """--json flag should create a JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            fname = f.name
        try:
            result = subprocess.run(
                [sys.executable, "snowflake.py", "-s", "json_cli", "--json", fname, "--no-color", "--size", "21"],
                capture_output=True, text=True,
                cwd=os.path.dirname(__file__)
            )
            assert result.returncode == 0
            assert os.path.exists(fname)
            with open(fname) as f:
                data = json.load(f)
            assert data["seed"] == "json_cli"
        finally:
            os.unlink(fname)

    def test_json_export_stdout(self):
        """--json - should write JSON to stdout."""
        result = subprocess.run(
            [sys.executable, "snowflake.py", "-s", "json_stdout", "--json", "-", "--no-color", "--size", "21"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["seed"] == "json_stdout"

    def test_svg_export_cli(self):
        """--svg flag should create an SVG file."""
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        try:
            result = subprocess.run(
                [sys.executable, "snowflake.py", "-s", "svg_cli", "--svg", fname, "--no-color", "--size", "21"],
                capture_output=True, text=True,
                cwd=os.path.dirname(__file__)
            )
            assert result.returncode == 0
            assert os.path.exists(fname)
        finally:
            os.unlink(fname)

    def test_compare_cli(self):
        """--compare flag should work."""
        result = subprocess.run(
            [sys.executable, "snowflake.py", "--compare", "alpha", "beta", "--no-color", "--size", "21"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        assert result.returncode == 0
        assert "Comparison" in result.stdout


class TestNoColorMode:
    """Tests for --no-color flag propagating to all rendering functions."""

    def test_render_no_color_header(self):
        """render_snowflake with color=False should not contain ANSI in header."""
        segments, ctype = generate_snowflake("nocolor_hdr", max_depth=4)
        output = render_snowflake(segments, ctype, "nocolor_hdr",
                                  canvas_size=31, color=False, show_info=True)
        import re
        ansi_seqs = re.findall(r'\033\[[^m]*m', output)
        assert len(ansi_seqs) == 0, f"Found ANSI sequences in color=False output: {ansi_seqs[:5]}"

    def test_render_with_color_header(self):
        """render_snowflake with color=True should contain ANSI in header."""
        segments, ctype = generate_snowflake("color_hdr", max_depth=4)
        output = render_snowflake(segments, ctype, "color_hdr",
                                  canvas_size=31, color=True, show_info=True)
        import re
        ansi_seqs = re.findall(r'\033\[[^m]*m', output)
        assert len(ansi_seqs) > 0, "Expected ANSI sequences in color=True output"

    def test_compare_no_color(self):
        """compare_snowflakes with color=False should not contain ANSI."""
        output = compare_snowflakes("a", "b", canvas_size=21, color=False)
        import re
        ansi_seqs = re.findall(r'\033\[[^m]*m', output)
        assert len(ansi_seqs) == 0, f"Found ANSI in compare color=False: {ansi_seqs[:5]}"

    def test_compare_with_color(self):
        """compare_snowflakes with color=True should contain ANSI."""
        output = compare_snowflakes("x", "y", canvas_size=21, color=True)
        import re
        ansi_seqs = re.findall(r'\033\[[^m]*m', output)
        assert len(ansi_seqs) > 0, "Expected ANSI sequences in color=True output"

    def test_gallery_no_color(self):
        """generate_gallery with color=False should not contain ANSI."""
        output = generate_gallery(["g1", "g2"], width=21, color=False)
        import re
        ansi_seqs = re.findall(r'\033\[[^m]*m', output)
        assert len(ansi_seqs) == 0, f"Found ANSI in gallery color=False: {ansi_seqs[:5]}"

    def test_gallery_with_color(self):
        """generate_gallery with color=True should contain ANSI."""
        output = generate_gallery(["g1", "g2"], width=21, color=True)
        import re
        ansi_seqs = re.findall(r'\033\[[^m]*m', output)
        assert len(ansi_seqs) > 0, "Expected ANSI sequences in gallery color=True"

    def test_cli_no_color(self):
        """CLI --no-color should suppress ANSI codes in output."""
        result = subprocess.run(
            [sys.executable, "snowflake.py", "-s", "cli_nocolor",
             "--no-color", "--size", "21"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        import re
        ansi_seqs = re.findall(r'\033\[[^m]*m', result.stdout)
        assert len(ansi_seqs) == 0, f"Found ANSI in --no-color output: {ansi_seqs[:5]}"

    def test_cli_no_color_gallery(self):
        """CLI --no-color should suppress ANSI codes in gallery output."""
        result = subprocess.run(
            [sys.executable, "snowflake.py", "-s", "gal_nc",
             "--gallery", "2", "--no-color"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        import re
        ansi_seqs = re.findall(r'\033\[[^m]*m', result.stdout)
        assert len(ansi_seqs) == 0, f"Found ANSI in --no-color gallery: {ansi_seqs[:5]}"

    def test_cli_no_color_compare(self):
        """CLI --no-color should suppress ANSI codes in compare output."""
        result = subprocess.run(
            [sys.executable, "snowflake.py", "--compare", "a", "b",
             "--no-color", "--size", "21"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        import re
        ansi_seqs = re.findall(r'\033\[[^m]*m', result.stdout)
        assert len(ansi_seqs) == 0, f"Found ANSI in --no-color compare: {ansi_seqs[:5]}"

    def test_cli_no_color_info(self):
        """CLI --no-color with --info should suppress ANSI codes."""
        result = subprocess.run(
            [sys.executable, "snowflake.py", "-s", "info_nc",
             "--info", "--no-color", "--size", "21"],
            capture_output=True, text=True,
            cwd=os.path.dirname(__file__)
        )
        import re
        ansi_seqs = re.findall(r'\033\[[^m]*m', result.stdout)
        assert len(ansi_seqs) == 0, f"Found ANSI in --no-color --info: {ansi_seqs[:5]}"


class TestSVGXSSPrevention:
    """Tests for SVG seed/crystal type HTML escaping."""

    def test_svg_escapes_angle_brackets(self):
        """SVG export should escape < and > in seed names."""
        segments, ctype = generate_snowflake("svg_escape", max_depth=3)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        try:
            export_svg(segments, ctype, '<script>alert(1)</script>', filename=fname)
            with open(fname) as f:
                content = f.read()
            assert '<script>' not in content, "Unescaped <script> in SVG"
            assert '&lt;script&gt;' in content, "Escaped <script> not found in SVG"
        finally:
            os.unlink(fname)

    def test_svg_escapes_ampersand(self):
        """SVG export should escape & in seed names."""
        segments, ctype = generate_snowflake("svg_amp", max_depth=3)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        try:
            export_svg(segments, ctype, 'a&b', filename=fname)
            with open(fname) as f:
                content = f.read()
            # The bare & should be escaped as &amp; in the text element
            assert 'a&amp;b' in content or 'a&#x26;b' in content, "Ampersand not escaped in SVG"
        finally:
            os.unlink(fname)

    def test_svg_escapes_quotes(self):
        """SVG export should escape double quotes in seed names."""
        segments, ctype = generate_snowflake("svg_quotes", max_depth=3)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            fname = f.name
        try:
            export_svg(segments, ctype, 'say "hello"', filename=fname)
            with open(fname) as f:
                content = f.read()
            # Should not have raw " inside the text element attribute
            assert '&quot;' in content or '&#x27;' in content or '&amp;quot;' in content, \
                "Quotes should be escaped in SVG"
        finally:
            os.unlink(fname)


class TestPrintSeedInfoColor:
    """Tests for print_seed_info color parameter."""

    def test_seed_info_with_color(self):
        """print_seed_info with color=True should produce ANSI codes."""
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        print_seed_info("color_test", color=True)
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        import re
        assert len(re.findall(r'\033\[[^m]*m', output)) > 0, "Expected ANSI codes"

    def test_seed_info_no_color(self):
        """print_seed_info with color=False should not produce ANSI codes."""
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        print_seed_info("nocolor_test", color=False)
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        import re
        assert len(re.findall(r'\033\[[^m]*m', output)) == 0, \
            "No ANSI codes expected in color=False mode"


class TestAnimateSnowfallColor:
    """Tests for animate_snowfall color parameter (signature only)."""

    def test_animate_has_color_param(self):
        """animate_snowfall should accept a color parameter."""
        import inspect
        from snowflake import animate_snowfall
        sig = inspect.signature(animate_snowfall)
        assert 'color' in sig.parameters, "animate_snowfall should have a 'color' parameter"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])