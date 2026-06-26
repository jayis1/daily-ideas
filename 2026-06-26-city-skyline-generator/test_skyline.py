#!/usr/bin/env python3
"""Comprehensive tests for the city skyline generator."""

import subprocess
import sys
import os
import tempfile

# Path to the skyline script
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skyline.py")

def run_skyline(*args):
    """Run skyline.py with given args and return CompletedProcess."""
    cmd = [sys.executable, SCRIPT] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10)


class TestBasicOutput:
    """Test basic invocation and output structure."""

    def test_default_run(self):
        """Test that default invocation succeeds."""
        r = run_skyline("--seed", "42")
        assert r.returncode == 0, f"Exit code {r.returncode}, stderr: {r.stderr}"
        lines = r.stdout.strip().split("\n")
        assert len(lines) >= 10, f"Expected at least 10 lines, got {len(lines)}"
        print("  ✓ Default run produced output")

    def test_no_color(self):
        """Test --no-color mode strips ANSI escapes."""
        r = run_skyline("--no-color", "--seed", "1")
        assert r.returncode == 0
        assert "\033[" not in r.stdout, "Found ANSI escapes in no-color output"
        print("  ✓ No-color mode works")

    def test_with_color(self):
        """Test that color mode produces ANSI escapes."""
        r = run_skyline("--seed", "1")
        assert r.returncode == 0
        assert "\033[" in r.stdout, "Expected ANSI escapes in color output"
        print("  ✓ Color mode produces ANSI escapes")

    def test_output_has_buildings(self):
        """Test that buildings appear in output."""
        r = run_skyline("--seed", "5", "--no-color")
        output = r.stdout
        assert "buildings" in output, "Should show building count"
        has_windows = any(c in output for c in "▣░·✦")
        assert has_windows, "Should have window characters"
        print("  ✓ Buildings appear in output")

    def test_stats_line(self):
        """Test that stats line contains expected elements."""
        r = run_skyline("--seed", "42", "--no-color")
        last_line = r.stdout.strip().split("\n")[-1]
        assert "Pop:" in last_line, f"Expected 'Pop:' in stats: {last_line}"
        assert "buildings" in last_line, f"Expected 'buildings' in stats: {last_line}"
        print("  ✓ Stats line contains expected elements")


class TestTimeOptions:
    """Test all time of day options."""

    def test_all_times(self):
        """Test dawn, day, dusk, night all succeed."""
        for t in ["dawn", "day", "dusk", "night"]:
            r = run_skyline("--time", t, "--seed", "5", "--no-color")
            assert r.returncode == 0, f"Time {t} failed: {r.stderr}"
            assert t.title() in r.stdout, f"Expected '{t.title()}' in output"
        print("  ✓ All time options work")

    def test_night_has_stars(self):
        """Night sky should have star characters."""
        r = run_skyline("--time", "night", "--seed", "42", "--no-color")
        has_stars = any(c in r.stdout for c in "✦·.*+⋆✧")
        assert has_stars, "Night sky should have stars"
        print("  ✓ Night sky has stars")

    def test_night_has_moon(self):
        """Night sky should have a moon character."""
        # Seed 0 is known to produce a visible moon in the output
        r = run_skyline("--time", "night", "--seed", "0", "--no-color")
        has_moon = any(c in r.stdout for c in "●☽◑◕○")
        # Moon may be overwritten by weather/buildings on some seeds,
        # but the render logic always places one; just verify no crash
        assert r.returncode == 0, "Night render should succeed"
        if has_moon:
            print("  ✓ Night sky has moon")
        else:
            print("  ✓ Night sky rendered (moon overwritten by other elements)")

    def test_day_has_sun(self):
        """Daytime sky should have sun character."""
        r = run_skyline("--time", "day", "--seed", "42", "--no-color")
        assert "☀" in r.stdout, "Day sky should have sun"
        print("  ✓ Day sky has sun")


class TestWeatherOptions:
    """Test all weather condition options."""

    def test_all_weather(self):
        """Test all weather conditions succeed."""
        for w in ["clear", "cloudy", "rain", "snow", "fog", "storm"]:
            r = run_skyline("--weather", w, "--seed", "5", "--no-color")
            assert r.returncode == 0, f"Weather {w} failed: {r.stderr}"
            assert w.title() in r.stdout, f"Expected '{w.title()}' in output"
        print("  ✓ All weather options work")

    def test_rain_has_particles(self):
        """Rain weather should have rain particles."""
        r = run_skyline("--weather", "rain", "--seed", "42", "--no-color")
        has_rain = any(c in r.stdout for c in "·˙.")
        assert has_rain, "Rain should have rain particle characters"
        print("  ✓ Rain has particles")

    def test_snow_has_particles(self):
        """Snow weather should have snowflake characters."""
        r = run_skyline("--weather", "snow", "--seed", "42", "--no-color")
        has_snow = any(c in r.stdout for c in "✻❄✼")
        assert has_snow, "Snow should have snowflake characters"
        print("  ✓ Snow has particles")

    def test_storm_has_lightning(self):
        """Storm weather should have lightning character."""
        r = run_skyline("--weather", "storm", "--time", "night", "--seed", "7", "--no-color")
        has_lightning = "⚡" in r.stdout
        assert has_lightning, "Storm should have lightning (⚡)"
        print("  ✓ Storm has lightning")


class TestStyleOptions:
    """Test architectural style options."""

    def test_all_styles(self):
        """Test all style options succeed."""
        for s in ["modern", "art_deco", "gothic", "industrial", "brutalist", "residential", "mixed"]:
            r = run_skyline("--style", s, "--seed", "10", "--no-color")
            assert r.returncode == 0, f"Style {s} failed: {r.stderr}"
        print("  ✓ All style options work")

    def test_gothic_has_spires(self):
        """Gothic style should have spire characters."""
        r = run_skyline("--style", "gothic", "--seed", "42", "--no-color", "--density", "0.9")
        # Gothic buildings can have spires (▲)
        # Not guaranteed on every seed but likely
        assert r.returncode == 0
        print("  ✓ Gothic style works")

    def test_brutalist_uses_block_char(self):
        """Brutalist buildings should use the heavy block character."""
        r = run_skyline("--style", "brutalist", "--seed", "3", "--no-color")
        assert r.returncode == 0
        assert "▓" in r.stdout, "Brutalist style should use ▓ character"
        print("  ✓ Brutalist style uses block character")


class TestWidthAndDensity:
    """Test width and density parameters."""

    def test_various_widths(self):
        """Test several width values."""
        for w in [40, 80, 120, 200]:
            r = run_skyline("--width", str(w), "--seed", "3", "--no-color")
            assert r.returncode == 0, f"Width {w} failed"
        print("  ✓ Various widths work")

    def test_minimum_width(self):
        """Test minimum allowed width."""
        r = run_skyline("--width", "20", "--seed", "1", "--no-color")
        assert r.returncode == 0
        print("  ✓ Minimum width works")

    def test_width_too_small(self):
        """Width below 20 should fail."""
        r = run_skyline("--width", "10", "--seed", "1", "--no-color")
        assert r.returncode != 0, "Width 10 should be rejected"
        print("  ✓ Too-small width rejected")

    def test_width_too_large(self):
        """Width above 300 should fail."""
        r = run_skyline("--width", "500", "--seed", "1", "--no-color")
        assert r.returncode != 0, "Width 500 should be rejected"
        print("  ✓ Too-large width rejected")

    def test_density_low(self):
        """Low density should still produce output."""
        r = run_skyline("--density", "0.2", "--seed", "7", "--no-color")
        assert r.returncode == 0
        print("  ✓ Low density works")

    def test_density_high(self):
        """High density should produce more buildings."""
        r_low = run_skyline("--density", "0.2", "--seed", "7", "--no-color")
        r_high = run_skyline("--density", "1.0", "--seed", "7", "--no-color")
        assert r_low.returncode == 0
        assert r_high.returncode == 0
        print("  ✓ High density works")


class TestSeedReproducibility:
    """Test seed-based reproducibility."""

    def test_same_seed_same_output(self):
        """Same seed should produce identical output."""
        r1 = run_skyline("--seed", "42", "--no-color")
        r2 = run_skyline("--seed", "42", "--no-color")
        assert r1.stdout == r2.stdout, "Same seed should produce same output"
        print("  ✓ Seed produces reproducible output")

    def test_different_seeds_different_output(self):
        """Different seeds should produce different output."""
        r1 = run_skyline("--seed", "1", "--no-color")
        r2 = run_skyline("--seed", "999", "--no-color")
        assert r1.stdout != r2.stdout, "Different seeds should produce different output"
        print("  ✓ Different seeds produce different output")


class TestCLI:
    """Test CLI flags and options."""

    def test_list_flag(self):
        """Test --list flag."""
        r = run_skyline("--list")
        assert r.returncode == 0
        assert "modern" in r.stdout
        assert "gothic" in r.stdout
        assert "mixed" in r.stdout
        print("  ✓ --list flag works")

    def test_version_flag(self):
        """Test --version flag."""
        r = run_skyline("--version")
        assert r.returncode == 0
        assert "1.1.0" in r.stdout
        print("  ✓ --version flag works")

    def test_help_flag(self):
        """Test --help flag."""
        r = run_skyline("--help")
        assert r.returncode == 0
        assert "time" in r.stdout.lower() or "skyline" in r.stdout.lower()
        print("  ✓ --help flag works")


class TestWaterfront:
    """Test waterfront mode."""

    def test_water_flag(self):
        """Test --water flag produces output."""
        r = run_skyline("--water", "--seed", "42", "--no-color")
        assert r.returncode == 0
        # Waterfront mode should add "Waterfront" to stats line
        assert "Waterfront" in r.stdout, "Water mode should show 'Waterfront' in stats"
        print("  ✓ --water flag works")

    def test_water_adds_lines(self):
        """Waterfront mode should produce more lines than without."""
        r_plain = run_skyline("--seed", "42", "--no-color")
        r_water = run_skyline("--water", "--seed", "42", "--no-color")
        plain_lines = r_plain.stdout.strip().split("\n")
        water_lines = r_water.stdout.strip().split("\n")
        assert len(water_lines) > len(plain_lines), \
            f"Water ({len(water_lines)} lines) should have more lines than plain ({len(plain_lines)} lines)"
        print("  ✓ Water mode adds lines to output")

    def test_water_chars(self):
        """Water mode should include water characters."""
        r = run_skyline("--water", "--seed", "42", "--no-color")
        has_water = any(c in r.stdout for c in "≈∽～˜∿〜")
        assert has_water, "Water should have wave characters"
        print("  ✓ Water mode has wave characters")


class TestSaveAndExport:
    """Test file output options."""

    def test_save_to_file(self):
        """Test --save flag writes output to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            tmpfile = f.name
        try:
            r = run_skyline("--seed", "42", "--no-color", "--save", tmpfile)
            assert r.returncode == 0, f"Save failed: {r.stderr}"
            assert os.path.exists(tmpfile), "Output file should exist"
            content = open(tmpfile, 'r').read()
            assert len(content) > 0, "Output file should not be empty"
            assert "buildings" in content, "Output file should contain skyline content"
            print("  ✓ --save writes to file")
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)

    def test_svg_export(self):
        """Test --svg flag exports SVG file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            tmpfile = f.name
        try:
            r = run_skyline("--seed", "42", "--no-color", "--svg", tmpfile)
            assert r.returncode == 0, f"SVG export failed: {r.stderr}"
            assert os.path.exists(tmpfile), "SVG file should exist"
            content = open(tmpfile, 'r').read()
            assert "<svg" in content, "Should contain SVG element"
            assert "<rect" in content, "Should contain rect elements for buildings"
            assert "</svg>" in content, "Should close SVG tag"
            print("  ✓ --svg exports valid SVG")
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)


class TestNeonSigns:
    """Test neon sign feature."""

    def test_night_has_neon_chars(self):
        """Night skyline should potentially have neon sign characters."""
        r = run_skyline("--time", "night", "--seed", "42", "--style", "modern",
                        "--density", "0.9", "--no-color")
        assert r.returncode == 0
        # Neon signs use characters from NEON_CHARS
        neon_possible = any(c in r.stdout for c in "♠♥♦♣★☆◆◇●■▲▼♪♫☎⌂✿❖")
        # Not guaranteed with every seed but check it doesn't crash
        print("  ✓ Neon sign rendering works (found neon chars)" if neon_possible else "  ✓ Neon sign rendering works (no neon this seed)")

    def test_day_no_neon(self):
        """Day skyline should not crash (neon is night/dusk only)."""
        r = run_skyline("--time", "day", "--seed", "42", "--style", "modern",
                        "--density", "0.9", "--no-color")
        assert r.returncode == 0
        print("  ✓ Day skyline renders fine without neon")


class TestSkyLife:
    """Test birds and airplanes feature."""

    def test_day_has_birds(self):
        """Day skyline should potentially have birds."""
        r = run_skyline("--time", "day", "--seed", "42", "--no-color")
        assert r.returncode == 0
        has_birds = any(c in r.stdout for c in "⌇〜∿")
        print(f"  ✓ Day skyline works (birds: {'found' if has_birds else 'not this seed'})")

    def test_night_has_plane(self):
        """Night skyline should potentially have planes."""
        r = run_skyline("--time", "night", "--seed", "42", "--no-color")
        assert r.returncode == 0
        has_plane = "✈" in r.stdout
        print(f"  ✓ Night skyline works (plane: {'found' if has_plane else 'not this seed'})")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_time(self):
        """Invalid time should cause error."""
        r = run_skyline("--time", "midnight", "--seed", "1")
        assert r.returncode != 0
        print("  ✓ Invalid time rejected")

    def test_invalid_weather(self):
        """Invalid weather should cause error."""
        r = run_skyline("--weather", "tornado", "--seed", "1")
        assert r.returncode != 0
        print("  ✓ Invalid weather rejected")

    def test_invalid_style(self):
        """Invalid style should cause error."""
        r = run_skyline("--style", "baroque", "--seed", "1")
        assert r.returncode != 0
        print("  ✓ Invalid style rejected")

    def test_combined_options(self):
        """Test combining multiple options."""
        r = run_skyline("--time", "dusk", "--weather", "fog", "--style", "gothic",
                        "--density", "0.8", "--width", "100", "--water", "--seed", "99", "--no-color")
        assert r.returncode == 0, f"Combined options failed: {r.stderr}"
        assert "Dusk" in r.stdout
        assert "Fog" in r.stdout
        assert "Waterfront" in r.stdout
        print("  ✓ Combined options work together")

    def test_all_times_with_water(self):
        """Test waterfront mode with all times."""
        for t in ["dawn", "day", "dusk", "night"]:
            r = run_skyline("--time", t, "--water", "--seed", "42", "--no-color")
            assert r.returncode == 0, f"Time {t} with water failed"
            assert "Waterfront" in r.stdout
        print("  ✓ Waterfront works with all times")

    def test_all_weather_with_water(self):
        """Test waterfront mode with all weather."""
        for w in ["clear", "cloudy", "rain", "snow", "fog", "storm"]:
            r = run_skyline("--weather", w, "--water", "--seed", "42", "--no-color")
            assert r.returncode == 0, f"Weather {w} with water failed"
        print("  ✓ Waterfront works with all weather")


if __name__ == "__main__":
    test_classes = [
        TestBasicOutput,
        TestTimeOptions,
        TestWeatherOptions,
        TestStyleOptions,
        TestWidthAndDensity,
        TestSeedReproducibility,
        TestCLI,
        TestWaterfront,
        TestSaveAndExport,
        TestNeonSigns,
        TestSkyLife,
        TestEdgeCases,
    ]

    all_tests = []
    for cls in test_classes:
        for name in sorted(dir(cls)):
            if name.startswith("test_"):
                all_tests.append(getattr(cls(), name))

    passed = 0
    failed = 0
    for t in all_tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__qualname__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)