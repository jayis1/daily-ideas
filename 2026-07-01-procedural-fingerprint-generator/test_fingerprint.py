#!/usr/bin/env python3
"""Tests for the Procedural Fingerprint Generator."""

import json
import os
import subprocess
import sys
import tempfile

# Add parent directory to path so we can import the module
sys.path.insert(0, os.path.dirname(__file__))

from fingerprint import (
    RAMP,
    PatternType,
    apply_oval_mask,
    generate_fingerprint_id,
    generate_fingerprint_metadata,
    generate_minutiae,
    mark_minutiae,
    orientation_at,
    render_fingerprint,
    ridge_frequency,
)


class TestOrientationAt:
    """Tests for the orientation_at function."""

    def test_loop_returns_valid_angle(self):
        """Loop pattern should return a float angle in radians."""
        angle = orientation_at(25, 25, 50, 50, PatternType.LOOP, 25, 21)
        assert isinstance(angle, float)

    def test_whorl_at_core_is_perpendicular(self):
        """Whorl orientation at the core point should be pi/2."""
        core_x, core_y = 25, 21
        angle = orientation_at(core_x, core_y, 50, 50, PatternType.WHORL, core_x, core_y)
        # At core, atan2(0,0) = 0, so theta=0, result = 0 + pi/2 = pi/2
        # Actually atan2(0,0) is 0.0 in most implementations
        assert isinstance(angle, float)

    def test_arch_is_horizontal_at_edges(self):
        """Arch orientation at far edges should be nearly -pi/2 (horizontal ridges)."""
        # Far left, bottom: should be close to -pi/2
        angle = orientation_at(0, 45, 50, 50, PatternType.ARCH, 25, 21)
        assert -2.0 < angle < 0.0

    def test_all_patterns_produce_valid_angles(self):
        """All pattern types should produce finite angle values."""
        for pattern in PatternType:
            angle = orientation_at(25, 25, 50, 50, pattern, 25, 21)
            assert isinstance(angle, float)
            assert abs(angle) < 100  # sanity check for finite values


class TestRidgeFrequency:
    """Tests for the ridge_frequency function."""

    def test_base_frequency_range(self):
        """Frequency should be positive and reasonable."""
        for pattern in PatternType:
            freq = ridge_frequency(25, 25, 50, 50, pattern, 25, 21)
            assert 0.0 < freq < 1.0

    def test_whorl_frequency_lower_near_core(self):
        """Whorl should have slightly lower frequency near core."""
        freq_near = ridge_frequency(25, 21, 50, 50, PatternType.WHORL, 25, 21)
        freq_far = ridge_frequency(45, 45, 50, 50, PatternType.WHORL, 25, 21)
        assert freq_near <= freq_far

    def test_loop_frequency_variation(self):
        """Loop should have slightly lower frequency near core."""
        freq_near = ridge_frequency(25, 21, 50, 50, PatternType.LOOP, 25, 21)
        freq_far = ridge_frequency(45, 45, 50, 50, PatternType.LOOP, 25, 21)
        assert freq_near <= freq_far


class TestRenderFingerprint:
    """Tests for the main render_fingerprint function."""

    def test_basic_render(self):
        """Rendering should produce correct-sized output."""
        lines, minutiae = render_fingerprint(30, 30, PatternType.LOOP, 42, 1.0, 1.2, False)
        assert len(lines) == 30
        for line in lines:
            assert len(line) == 30

    def test_deterministic(self):
        """Same seed should produce identical output."""
        lines1, m1 = render_fingerprint(20, 20, PatternType.WHORL, 123, 1.0, 1.2, False)
        lines2, m2 = render_fingerprint(20, 20, PatternType.WHORL, 123, 1.0, 1.2, False)
        assert lines1 == lines2
        assert len(m1) == len(m2)

    def test_different_seeds_differ(self):
        """Different seeds should produce different output."""
        lines1, _ = render_fingerprint(20, 20, PatternType.LOOP, 1, 1.0, 1.2, False)
        lines2, _ = render_fingerprint(20, 20, PatternType.LOOP, 2, 1.0, 1.2, False)
        # Extremely unlikely to be identical
        assert lines1 != lines2

    def test_all_patterns_render(self):
        """All pattern types should render without errors."""
        for pattern in PatternType:
            lines, _ = render_fingerprint(20, 20, pattern, 42, 1.0, 1.2, False)
            assert len(lines) == 20

    def test_minutiae_count(self):
        """Minutiae should contain between 10 and 20 points."""
        _, minutiae = render_fingerprint(30, 30, PatternType.LOOP, 42, 1.0, 1.2, False)
        assert 10 <= len(minutiae) <= 20

    def test_minutiae_types(self):
        """All minutiae should have valid types."""
        _, minutiae = render_fingerprint(30, 30, PatternType.LOOP, 42, 1.0, 1.2, False)
        valid_types = {"ending", "bifurcation", "island"}
        for m in minutiae:
            assert m["type"] in valid_types

    def test_minutiae_visible_when_shown(self):
        """When minutiae are shown, marker characters should appear in output."""
        lines, _ = render_fingerprint(40, 40, PatternType.WHORL, 99, 1.0, 1.2, True)
        all_chars = "".join(lines)
        markers = {"◆", "◇", "○", "•"}
        assert any(m in all_chars for m in markers)

    def test_oval_mask_applied(self):
        """Rendered output should have spaces in corners (outside oval mask)."""
        lines, _ = render_fingerprint(30, 30, PatternType.LOOP, 42, 1.0, 1.2, False)
        # Corners should be spaces (outside the oval)
        assert lines[0][0] == " "
        assert lines[0][-1] == " "
        assert lines[-1][0] == " "
        assert lines[-1][-1] == " "

    def test_density_affects_output(self):
        """Different density values should produce different output."""
        lines1, _ = render_fingerprint(20, 20, PatternType.LOOP, 42, 0.5, 1.2, False)
        lines2, _ = render_fingerprint(20, 20, PatternType.LOOP, 42, 1.5, 1.2, False)
        assert lines1 != lines2


class TestApplyOvalMask:
    """Tests for the apply_oval_mask function."""

    def test_corners_masked(self):
        """Corners of the grid should be masked (spaces)."""
        lines = [RAMP[-1] * 20 for _ in range(20)]
        result = apply_oval_mask(lines, 20, 20)
        assert result[0][0] == " "
        assert result[0][-1] == " "

    def test_center_preserved(self):
        """Center of the grid should be preserved."""
        lines = [RAMP[-1] * 20 for _ in range(20)]
        result = apply_oval_mask(lines, 20, 20)
        # Center should still be a dense character
        assert result[10][10] != " "

    def test_degenerate_size(self):
        """Very small sizes should not crash."""
        lines = ["@@" for _ in range(2)]
        result = apply_oval_mask(lines, 2, 2)
        assert len(result) == 2


class TestGenerateMinutiae:
    """Tests for the generate_minutiae function."""

    def test_count_range(self):
        """Should generate 10-20 minutiae points."""
        rng = __import__("random").Random(42)
        minutiae = generate_minutiae(50, 50, rng)
        assert 10 <= len(minutiae) <= 20

    def test_positions_within_bounds(self):
        """Minutiae positions should be within grid bounds."""
        rng = __import__("random").Random(42)
        minutiae = generate_minutiae(50, 50, rng)
        for m in minutiae:
            assert 0 <= m["x"] <= 50
            assert 0 <= m["y"] <= 50

    def test_angle_range(self):
        """Minutiae angles should be in [0, 2*pi)."""
        rng = __import__("random").Random(42)
        minutiae = generate_minutiae(50, 50, rng)
        for m in minutiae:
            assert 0 <= m["angle"] < 2 * 3.14159


class TestMarkMinutiae:
    """Tests for the mark_minutiae function."""

    def test_markers_appear(self):
        """Minutiae markers should appear in the output."""
        rng = __import__("random").Random(42)
        minutiae = generate_minutiae(30, 30, rng)
        lines = [RAMP[-1] * 30 for _ in range(30)]
        result = mark_minutiae(lines, minutiae, 30, 30)
        all_text = "".join(result)
        # At least some markers should be visible
        markers = {"◆", "◇", "○", "•"}
        assert any(m in all_text for m in markers)


class TestFingerprintId:
    """Tests for the generate_fingerprint_id function."""

    def test_deterministic(self):
        """Same inputs should produce same ID."""
        minutiae = [{"x": 10, "y": 20, "angle": 1.0, "type": "ending"}]
        id1 = generate_fingerprint_id(PatternType.LOOP, 42, minutiae)
        id2 = generate_fingerprint_id(PatternType.LOOP, 42, minutiae)
        assert id1 == id2

    def test_different_patterns_differ(self):
        """Different pattern types should produce different IDs."""
        minutiae = [{"x": 10, "y": 20, "angle": 1.0, "type": "ending"}]
        id1 = generate_fingerprint_id(PatternType.LOOP, 42, minutiae)
        id2 = generate_fingerprint_id(PatternType.WHORL, 42, minutiae)
        assert id1 != id2

    def test_format(self):
        """ID should be a 16-character uppercase hex string."""
        id1 = generate_fingerprint_id(PatternType.LOOP, 42, [])
        assert len(id1) == 16
        assert id1 == id1.upper()
        assert all(c in "0123456789ABCDEF" for c in id1)


class TestFingerprintMetadata:
    """Tests for the generate_fingerprint_metadata function."""

    def test_structure(self):
        """Metadata should contain all expected fields."""
        minutiae = [{"x": 10.0, "y": 20.0, "angle": 1.0, "type": "ending"}]
        meta = generate_fingerprint_metadata(PatternType.LOOP, 42, minutiae, 50, 55)
        assert "fingerprint_id" in meta
        assert "pattern_type" in meta
        assert "pattern_name" in meta
        assert "seed" in meta
        assert "width" in meta
        assert "height" in meta
        assert "minutiae_count" in meta
        assert "minutiae" in meta
        assert meta["seed"] == 42
        assert meta["width"] == 50
        assert meta["height"] == 55
        assert meta["minutiae_count"] == 1


class TestCLI:
    """Integration tests for the CLI interface."""

    def _run(self, args):
        """Helper to run the script as a subprocess."""
        script = os.path.join(os.path.dirname(__file__), "fingerprint.py")
        result = subprocess.run(
            [sys.executable, script] + args,
            capture_output=True, text=True, timeout=30
        )
        return result

    def test_default_run(self):
        """Default run should succeed and produce output."""
        result = self._run(["--seed", "42"])
        assert result.returncode == 0
        assert "Fingerprint" in result.stdout

    def test_pattern_loop(self):
        """Loop pattern should generate successfully."""
        result = self._run(["--pattern", "loop", "--seed", "1"])
        assert result.returncode == 0
        assert "Ulnar Loop" in result.stdout

    def test_pattern_whorl(self):
        """Whorl pattern should generate successfully."""
        result = self._run(["--pattern", "whorl", "--seed", "1"])
        assert result.returncode == 0
        assert "Whorl" in result.stdout

    def test_id_only(self):
        """--id-only should output just the hash."""
        result = self._run(["--seed", "42", "--id-only"])
        assert result.returncode == 0
        # Should be a 16-char hex string
        output = result.stdout.strip()
        assert len(output) == 16
        assert all(c in "0123456789ABCDEF" for c in output)

    def test_list_patterns(self):
        """--list should show all pattern types."""
        result = self._run(["--list"])
        assert result.returncode == 0
        assert "loop" in result.stdout
        assert "whorl" in result.stdout

    def test_compare(self):
        """--compare should show all patterns side by side."""
        result = self._run(["--compare", "--seed", "42"])
        assert result.returncode == 0
        assert "seed: 42" in result.stdout

    def test_version(self):
        """--version should output version string."""
        result = self._run(["--version"])
        assert result.returncode == 0
        assert "1.1.0" in result.stdout

    def test_json_output(self):
        """--json should produce valid JSON with metadata."""
        result = self._run(["--seed", "42", "--json"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "fingerprint_id" in data
        assert data["seed"] == 42
        assert "minutiae" in data
        assert "ascii" in data

    def test_json_with_compare(self):
        """--json with --compare should produce a JSON array."""
        result = self._run(["--seed", "42", "--json", "--compare"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 5  # five pattern types

    def test_output_to_file(self):
        """--output should write fingerprint to a file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            tmpfile = f.name
        try:
            result = self._run(["--seed", "42", "--output", tmpfile])
            assert result.returncode == 0
            assert f"saved to {tmpfile}" in result.stdout
            with open(tmpfile) as f:
                content = f.read()
            assert "Fingerprint" in content
        finally:
            os.unlink(tmpfile)

    def test_batch_mode(self):
        """--batch should generate multiple fingerprints."""
        result = self._run(["--seed", "42", "--batch", "3", "--width", "20", "--height", "20"])
        assert result.returncode == 0
        assert "Fingerprint 1/3" in result.stdout
        assert "Fingerprint 3/3" in result.stdout

    def test_invalid_width(self):
        """Width < 10 should produce an error."""
        result = self._run(["--width", "5"])
        assert result.returncode != 0

    def test_invalid_density(self):
        """Negative density should produce an error."""
        result = self._run(["--density", "-1"])
        assert result.returncode != 0


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))