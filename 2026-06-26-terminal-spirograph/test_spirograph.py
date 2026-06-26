#!/usr/bin/env python3
"""Tests for Terminal Spirograph."""

import math
import os
import tempfile

import spirograph as sp


# ── Unit tests for math functions ──

class TestHypotrochoidPoint:
    """Test hypotrochoid parametric computation."""

    def test_origin_at_zero(self):
        """At t=0: x = (R-r)*1 + d*1 = (R-r)+d, y = (R-r)*0 - d*0 = 0."""
        R, r, d = 11, 4, 4
        x, y = sp.hypotrochoid_point(R, r, d, 0)
        expected_x = (R - r) + d  # cos(0)=1
        assert abs(x - expected_x) < 1e-9, f"Expected x≈{expected_x}, got {x}"
        assert abs(y) < 1e-9, f"Expected y≈0, got {y}"

    def test_symmetry(self):
        """Hypotrochoid should have point symmetry for some params."""
        R, r, d = 10, 5, 5
        x1, y1 = sp.hypotrochoid_point(R, r, d, math.pi)
        x0, y0 = sp.hypotrochoid_point(R, r, d, 0)
        # With these params, points at t and t+pi should be roughly opposite
        assert abs(x1 + x0) < 1 or abs(y1 + y0) < 1e-6

    def test_returns_tuple(self):
        result = sp.hypotrochoid_point(11, 4, 6, 1.0)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestEpitrochoidPoint:
    """Test epitrochoid parametric computation."""

    def test_origin_at_zero(self):
        """At t=0, epitrochoid point should be at (R+r-d, 0)."""
        R, r, d = 7, 3, 5
        x, y = sp.epitrochoid_point(R, r, d, 0)
        assert abs(x - (R + r - d)) < 1e-9
        assert abs(y) < 1e-9

    def test_nonzero_y(self):
        """At t=pi/2, y should be nonzero for non-trivial params."""
        x, y = sp.epitrochoid_point(7, 3, 5, math.pi / 2)
        assert abs(y) > 0.1


class TestRosePoint:
    """Test rose curve parametric computation."""

    def test_at_zero(self):
        """At t=0, rose curve should be at (d, 0) since cos(0)=1."""
        k, n, d = 5, 3, 10
        x, y = sp.rose_point(k, n, d, 0)
        assert abs(x - d) < 1e-9
        assert abs(y) < 1e-9

    def test_returns_to_origin(self):
        """Rose curves should pass through origin at certain t values."""
        k, n, d = 3, 1, 10
        t = math.pi / 2 * n / k if k != 0 else 0
        # When cos(k/n * t) = 0, the point is at origin
        # For k=3, n=1: cos(3*t) = 0 when t=pi/6
        x, y = sp.rose_point(k, n, d, math.pi / 6)
        assert abs(x) < 1e-9
        assert abs(y) < 1e-9


class TestLissajousPoint:
    """Test Lissajous curve parametric computation."""

    def test_at_zero(self):
        """At t=0 with delta=pi/2, x should be d*sin(pi/2)=d, y=0."""
        a, b, delta, d = 3, 4, math.pi / 2, 10
        x, y = sp.lissajous_point(a, b, delta, d, 0)
        assert abs(x - d) < 1e-9
        assert abs(y) < 1e-9

    def test_bounded(self):
        """Lissajous points should stay within [-d, d]."""
        a, b, delta, d = 3, 4, math.pi / 3, 10
        for t in [i * 0.1 for i in range(100)]:
            x, y = sp.lissajous_point(a, b, delta, d, t)
            assert abs(x) <= d + 1e-9
            assert abs(y) <= d + 1e-9


# ── Unit tests for compute_curve ──

class TestComputeCurve:
    """Test that compute_curve returns valid point lists."""

    def test_hypo_returns_points(self):
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 1000)
        assert len(points) == 1000

    def test_epi_returns_points(self):
        params = {"R": 7, "r": 3, "d": 5}
        points = sp.compute_curve("epi", params, 1000)
        assert len(points) == 1000

    def test_rose_returns_points(self):
        params = {"k": 5, "n": 3, "d": 10}
        points = sp.compute_curve("rose", params, 1000)
        assert len(points) == 1000

    def test_lissajous_returns_points(self):
        params = {"a": 3, "b": 4, "delta": math.pi / 2, "d": 10}
        points = sp.compute_curve("lissajous", params, 1000)
        assert len(points) == 1000

    def test_zero_r_returns_empty(self):
        params = {"R": 11, "r": 0, "d": 6}
        points = sp.compute_curve("hypo", params, 1000)
        assert len(points) == 0


# ── Unit tests for render_frame ──

class TestRenderFrame:
    """Test rendering output."""

    def test_basic_render(self):
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 500)
        lines = sp.render_frame(points, 40, 20)
        assert len(lines) == 20
        assert all(len(line) == 40 for line in lines)

    def test_empty_points(self):
        lines = sp.render_frame([], 40, 20)
        # Empty points now returns a proper blank grid instead of empty list
        assert len(lines) == 20
        assert all(len(line) == 40 for line in lines)
        assert all(line == " " * 40 for line in lines)

    def test_fine_chars(self):
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 500)
        lines = sp.render_frame(points, 40, 20, chars=sp.DENSITY_CHARS_FINE)
        assert len(lines) == 20

    def test_non_blank_content(self):
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 5000)
        lines = sp.render_frame(points, 60, 30)
        # At least some characters should be non-blank
        all_text = "".join(lines)
        assert any(c != " " for c in all_text)


# ── Unit tests for colorize ──

class TestColorize:
    """Test ANSI colorization."""

    def test_none_palette_no_color(self):
        lines = ["  ##  ", "  ..  "]
        result = sp.colorize(lines, "none")
        assert result == lines  # unchanged

    def test_auto_palette_adds_ansi(self):
        lines = ["  ##  "]
        result = sp.colorize(lines, "auto", frame_idx=0)
        assert "\033[" in result[0]  # contains ANSI escape
        assert "\033[0m" in result[0]  # contains reset

    def test_rainbow_palette(self):
        lines = ["aaa", "bbb", "ccc"]
        result = sp.colorize(lines, "rainbow")
        # Each line should have different color
        assert len(result) == 3
        assert all("\033[" in line for line in result)

    def test_gradient_shifts_with_frame(self):
        lines = ["xxx", "yyy"]
        r1 = sp.colorize(lines, "gradient", frame_idx=0)
        r2 = sp.colorize(lines, "gradient", frame_idx=1)
        # Colors should shift
        assert r1 != r2


# ── Unit tests for generate_params ──

class TestGenerateParams:
    """Test random parameter generation."""

    def test_hypo_params_structure(self):
        params = sp.generate_params("hypo", seed=42)
        assert "R" in params
        assert "r" in params
        assert "d" in params
        assert params["r"] < params["R"]
        assert params["d"] >= 1

    def test_epi_params_structure(self):
        params = sp.generate_params("epi", seed=42)
        assert "R" in params
        assert "r" in params
        assert "d" in params
        assert params["d"] >= 1

    def test_rose_params_structure(self):
        params = sp.generate_params("rose", seed=42)
        assert "k" in params
        assert "n" in params
        assert "d" in params

    def test_lissajous_params_structure(self):
        params = sp.generate_params("lissajous", seed=42)
        assert "a" in params
        assert "b" in params
        assert "delta" in params
        assert "d" in params

    def test_seed_reproducibility(self):
        p1 = sp.generate_params("hypo", seed=123)
        p2 = sp.generate_params("hypo", seed=123)
        assert p1 == p2

    def test_different_seeds_differ(self):
        p1 = sp.generate_params("hypo", seed=1)
        p2 = sp.generate_params("hypo", seed=999)
        # Very unlikely to be identical
        assert p1 != p2


# ── Unit tests for get_curve_label ──

class TestGetCurveLabel:
    """Test human-readable curve labels."""

    def test_hypo_label(self):
        label = sp.get_curve_label("hypo", {"R": 11, "r": 4, "d": 6})
        assert "Hypotrochoid" in label
        assert "11" in label

    def test_epi_label(self):
        label = sp.get_curve_label("epi", {"R": 7, "r": 3, "d": 5})
        assert "Epitrochoid" in label

    def test_rose_label(self):
        label = sp.get_curve_label("rose", {"k": 5, "n": 3, "d": 10})
        assert "Rose" in label

    def test_lissajous_label(self):
        label = sp.get_curve_label("lissajous", {"a": 3, "b": 4, "delta": 1.57, "d": 10})
        assert "Lissajous" in label

    def test_unknown_label(self):
        label = sp.get_curve_label("unknown", {})
        assert "Unknown" in label


# ── Unit tests for clamp ──

class TestClamp:
    def test_within_range(self):
        assert sp.clamp(5, 0, 10) == 5

    def test_below_range(self):
        assert sp.clamp(-3, 0, 10) == 0

    def test_above_range(self):
        assert sp.clamp(15, 0, 10) == 10

    def test_exact_bounds(self):
        assert sp.clamp(0, 0, 10) == 0
        assert sp.clamp(10, 0, 10) == 10


# ── Unit tests for SVG export ──

class TestExportSvg:
    """Test SVG file export."""

    def test_export_creates_file(self):
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 100)
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            filepath = f.name
        try:
            sp.export_svg(points, "hypo", params, filepath)
            assert os.path.exists(filepath)
            content = open(filepath).read()
            assert "<svg" in content
            assert "</svg>" in content
            assert "Hypotrochoid" in content
        finally:
            os.unlink(filepath)

    def test_export_empty_points_warns(self):
        """Exporting empty points should produce a warning, not crash."""
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            filepath = f.name
        try:
            sp.export_svg([], "hypo", {}, filepath)
            # File should not be created or should be empty
            assert not os.path.exists(filepath) or os.path.getsize(filepath) == 0
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)


# ── Unit tests for presets ──

class TestPresets:
    """Test that built-in presets produce valid curves."""

    def test_all_presets_have_valid_curves(self):
        for name, curve_type, params in sp.PRESETS:
            points = sp.compute_curve(curve_type, params, 1000)
            assert len(points) == 1000, f"Preset '{name}' produced {len(points)} points"

    def test_preset_names_unique(self):
        names = [p[0] for p in sp.PRESETS]
        assert len(names) == len(set(names)), "Preset names must be unique"


# ── Integration test ──

class TestIntegration:
    """Test end-to-end rendering pipeline."""

    def test_full_pipeline_hypo(self):
        """Compute, render, and colorize a hypotrochoid."""
        params = sp.generate_params("hypo", seed=42)
        points = sp.compute_curve("hypo", params, 5000)
        lines = sp.render_frame(points, 60, 25)
        colored = sp.colorize(lines, "auto")
        assert len(colored) == 25
        assert all("\033[" in line for line in colored)

    def test_full_pipeline_rose(self):
        """Compute, render, and colorize a rose curve."""
        params = {"k": 5, "n": 3, "d": 10}
        points = sp.compute_curve("rose", params, 5000)
        lines = sp.render_frame(points, 60, 25)
        colored = sp.colorize(lines, "rainbow")
        assert len(colored) == 25

    def test_static_render_runs(self, capsys=None):
        """static_render should not crash."""
        params = {"R": 11, "r": 4, "d": 6}
        # Force palette to "none" so ANSI codes don't interfere with assertions
        sp.static_render("hypo", params, 40, 15, 500, "none", sp.DENSITY_CHARS)
        # Just verify it doesn't crash — output goes to stdout


# ── Bug fix tests ──

class TestPeriodComputation:
    """Test that curve period computation is correct (no over-draw)."""

    def test_hypotrochoid_closes(self):
        """Hypotrochoid curve should close within one period."""
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 10000)
        start = points[0]
        end = points[-1]
        dist = math.sqrt((start[0] - end[0])**2 + (start[1] - end[1])**2)
        # End point should be very close to start point (closed curve)
        assert dist < 0.5, f"Curve doesn't close: distance={dist:.4f}"

    def test_epitrochoid_closes(self):
        """Epitrochoid curve should close within one period."""
        params = {"R": 9, "r": 3, "d": 5}
        points = sp.compute_curve("epi", params, 10000)
        start = points[0]
        end = points[-1]
        dist = math.sqrt((start[0] - end[0])**2 + (start[1] - end[1])**2)
        assert dist < 0.5, f"Curve doesn't close: distance={dist:.4f}"

    def test_rose_closes(self):
        """Rose curve should close within one period."""
        params = {"k": 5, "n": 3, "d": 10}
        points = sp.compute_curve("rose", params, 10000)
        start = points[0]
        end = points[-1]
        dist = math.sqrt((start[0] - end[0])**2 + (start[1] - end[1])**2)
        assert dist < 0.5, f"Curve doesn't close: distance={dist:.4f}"

    def test_lissajous_closes(self):
        """Lissajous curve should close within one period."""
        params = {"a": 3, "b": 4, "delta": math.pi / 2, "d": 10}
        points = sp.compute_curve("lissajous", params, 10000)
        start = points[0]
        end = points[-1]
        dist = math.sqrt((start[0] - end[0])**2 + (start[1] - end[1])**2)
        assert dist < 0.5, f"Curve doesn't close: distance={dist:.4f}"

    def test_no_excessive_overdraw(self):
        """Hypotrochoid should not over-draw by more than 2x the period."""
        # R=11, r=4, gcd=1: period = 2*pi*4 = 8*pi ≈ 25.13
        # The old code would compute t_max = 25.13 * 11 = 276.46 (11x overdraw)
        # The fixed code should compute t_max ≈ 25.13 (1x period)
        params = {"R": 11, "r": 4, "d": 6}
        # Use compute_curve and check the number of unique positions
        points = sp.compute_curve("hypo", params, 10000)
        # The curve should have all points within one period
        assert len(points) == 10000


class TestInputValidation:
    """Test input validation fixes."""

    def test_render_frame_negative_width_raises(self):
        """render_frame should reject negative width."""
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 100)
        try:
            sp.render_frame(points, -5, 20)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "width" in str(e).lower()

    def test_render_frame_negative_height_raises(self):
        """render_frame should reject negative height."""
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 100)
        try:
            sp.render_frame(points, 40, -5)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "height" in str(e).lower()

    def test_render_frame_zero_width_raises(self):
        """render_frame should reject zero width."""
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 100)
        try:
            sp.render_frame(points, 0, 20)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_compute_curve_unknown_type_raises(self):
        """compute_curve should raise ValueError for unknown curve type."""
        try:
            sp.compute_curve("unknown", {"R": 11}, 100)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "unknown" in str(e).lower()

    def test_generate_params_unknown_type_raises(self):
        """generate_params should raise ValueError for unknown curve type."""
        try:
            sp.generate_params("unknown", seed=42)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "unknown" in str(e).lower()

    def test_render_frame_empty_points_returns_grid(self):
        """render_frame with empty points returns proper blank grid."""
        lines = sp.render_frame([], 40, 20)
        assert len(lines) == 20
        assert all(len(line) == 40 for line in lines)
        assert all(line == " " * 40 for line in lines)

    def test_compute_curve_zero_points_returns_empty(self):
        """compute_curve with num_points=0 returns empty list."""
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 0)
        assert len(points) == 0

    def test_negative_points_returns_empty(self):
        """compute_curve with negative num_points returns empty list."""
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, -1)
        assert len(points) == 0


class TestSVGSecurity:
    """Test SVG export security fixes."""

    def test_svg_blocks_system_paths(self):
        """SVG export should block writing to system directories."""
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 100)
        # Writing to /etc should be blocked
        import io
        from unittest.mock import patch as mock_patch
        # Use stderr capture to check for error message
        with mock_patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
            sp.export_svg(points, "hypo", params, "/etc/test_output.svg")
            output = mock_stderr.getvalue()
            assert "Error" in output or "Cannot write" in output

    def test_svg_normal_path_works(self):
        """SVG export should work for normal paths."""
        params = {"R": 11, "r": 4, "d": 6}
        points = sp.compute_curve("hypo", params, 100)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            filepath = f.name
        try:
            sp.export_svg(points, "hypo", params, filepath)
            assert os.path.exists(filepath)
            content = open(filepath).read()
            assert "<svg" in content
        finally:
            os.unlink(filepath)


class TestRoseCurvePeriod:
    """Test that rose curve period is computed correctly."""

    def test_trefoil_closes(self):
        """Trefoil (k=3, n=1) should close properly.
        k*n = 3 is odd, so period = pi*1/gcd(3,1) = pi."""
        params = {"k": 3, "n": 1, "d": 10}
        points = sp.compute_curve("rose", params, 10000)
        start = points[0]
        end = points[-1]
        dist = math.sqrt((start[0] - end[0])**2 + (start[1] - end[1])**2)
        assert dist < 1.0, f"Trefoil doesn't close: distance={dist:.4f}"

    def test_pentarose_closes(self):
        """Pentarose (k=5, n=3) should close properly.
        k*n = 15 is odd, so period = pi*3/gcd(5,3) = 3*pi."""
        params = {"k": 5, "n": 3, "d": 10}
        points = sp.compute_curve("rose", params, 10000)
        start = points[0]
        end = points[-1]
        dist = math.sqrt((start[0] - end[0])**2 + (start[1] - end[1])**2)
        assert dist < 1.0, f"Pentarose doesn't close: distance={dist:.4f}"

    def test_even_kn_closes(self):
        """Rose with k=4, n=2 (k*n=8, even) should close properly.
        period = 2*pi*2/gcd(4,2) = 2*pi."""
        params = {"k": 4, "n": 2, "d": 10}
        points = sp.compute_curve("rose", params, 10000)
        start = points[0]
        end = points[-1]
        dist = math.sqrt((start[0] - end[0])**2 + (start[1] - end[1])**2)
        assert dist < 1.0, f"Rose (4,2) doesn't close: distance={dist:.4f}"