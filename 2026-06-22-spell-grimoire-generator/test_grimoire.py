#!/usr/bin/env python3
"""Tests for the Spell Grimoire Generator."""

import json
import subprocess
import sys
import os

# Add the project directory to path
sys.path.insert(0, os.path.dirname(__file__))

from grimoire import (
    generate_spell, generate_grimoire, generate_spell_list,
    render_grimoire_page, render_plaintext_page, strip_ansi,
    ordinal, choose_rarity, SPELL_LEVELS, SCHOOLS, RARITIES,
    generate_incantation, generate_sigil, generate_spell_diagram,
    __version__,
)


class TestGenerateSpell:
    """Test spell generation."""

    def test_default_spell_has_all_fields(self):
        spell = generate_spell()
        assert spell.name, "Spell should have a name"
        assert spell.school in SCHOOLS, f"School '{spell.school}' should be valid"
        assert 0 <= spell.level <= 9, f"Level {spell.level} should be 0-9"
        assert spell.casting_time, "Should have casting time"
        assert spell.rng, "Should have range"
        assert spell.duration, "Should have duration"
        assert spell.description, "Should have description"
        assert spell.incantation, "Should have incantation"
        assert spell.backstory, "Should have backstory"
        assert spell.rarity in RARITIES, f"Rarity '{spell.rarity}' should be valid"
        assert len(spell.sigil) > 0, "Should have sigil lines"
        assert len(spell.diagram) > 0, "Should have diagram lines"

    def test_specific_school(self):
        spell = generate_spell(school="Necromancy")
        assert spell.school == "Necromancy"

    def test_specific_level(self):
        spell = generate_spell(level=5)
        assert spell.level == 5

    def test_specific_rarity(self):
        spell = generate_spell(rarity="Legendary")
        assert spell.rarity == "Legendary"

    def test_all_schools(self):
        """Every school should produce a valid spell."""
        for school in SCHOOLS:
            spell = generate_spell(school=school, level=3)
            assert spell.school == school
            assert spell.level == 3

    def test_all_levels(self):
        """Every level 0-9 should produce a valid spell."""
        for level in range(10):
            spell = generate_spell(level=level)
            assert spell.level == level

    def test_higher_levels_for_mid_levels(self):
        """Spells at levels 1-8 should have higher_levels text."""
        spell = generate_spell(level=5)
        assert spell.higher_levels, "Mid-level spells should have higher_levels text"
        assert "higher" in spell.higher_levels.lower()

    def test_cantrip_has_no_higher_levels(self):
        """Cantrips (level 0) should not have higher_levels text."""
        spell = generate_spell(level=0)
        assert spell.higher_levels == ""

    def test_ninth_level_has_no_higher_levels(self):
        """9th-level spells should not have higher_levels text."""
        spell = generate_spell(level=9)
        assert spell.higher_levels == ""

    def test_higher_levels_uses_correct_ordinal(self):
        """Check that the ordinal helper works correctly."""
        assert ordinal(1) == "1st"
        assert ordinal(2) == "2nd"
        assert ordinal(3) == "3rd"
        assert ordinal(4) == "4th"
        assert ordinal(11) == "11th"
        assert ordinal(12) == "12th"
        assert ordinal(13) == "13th"
        assert ordinal(21) == "21st"
        assert ordinal(22) == "22nd"
        assert ordinal(23) == "23rd"

    def test_name_uniqueness(self):
        """Generated spell names should be unique across multiple calls."""
        names = set()
        for _ in range(50):
            spell = generate_spell()
            # Names should not collide — though this is probabilistic,
            # with 50 spells and large word pools, collisions are very rare
            names.add(spell.name)
        # Allow a small number of collisions but not many
        assert len(names) >= 40, f"Too many name collisions: {50 - len(names)}"


class TestRarity:
    """Test rarity system."""

    def test_choose_rarity_returns_valid(self):
        for _ in range(50):
            r = choose_rarity()
            assert r in RARITIES

    def test_choose_rarity_with_level(self):
        for level in range(10):
            r = choose_rarity(level=level)
            assert r in RARITIES

    def test_legendary_rarity_high_level(self):
        """Legendary rarity should bias toward high levels."""
        # The bias is probabilistic; just check that most Legendary spells
        # tend to be mid-to-high level (3+) rather than cantrips
        high_level_count = 0
        for _ in range(30):
            spell = generate_spell(rarity="Legendary")
            if spell.level >= 3:
                high_level_count += 1
        # At least some should be mid-to-high level due to re-roll bias
        assert high_level_count >= 5, f"Expected some Legendary spells to be high level, got {high_level_count}/30"


class TestRendering:
    """Test rendering functions."""

    def test_render_page_contains_spell_name(self):
        spell = generate_spell(school="Evocation", level=3)
        page = render_grimoire_page(spell, color=False)
        assert spell.name in page, "Rendered page should contain spell name"

    def test_render_page_contains_school(self):
        spell = generate_spell(school="Necromancy")
        page = render_grimoire_page(spell, color=False)
        assert "Necromancy" in page

    def test_render_page_contains_rarity(self):
        spell = generate_spell(rarity="Rare")
        page = render_grimoire_page(spell, color=False)
        assert "[Rare]" in page

    def test_render_page_no_ansi_in_plaintext(self):
        spell = generate_spell()
        page = render_plaintext_page(spell)
        # Should not contain ANSI escape sequences
        assert "\033[" not in page, "Plaintext page should not contain ANSI codes"

    def test_strip_ansi(self):
        text = "\033[38;5;196mHello\033[0m World"
        assert strip_ansi(text) == "Hello World"

    def test_render_grimoire_multiple_spells(self):
        output = generate_grimoire(num_spells=3, color=False)
        # The header uses spaced-out text "G R I M O I R E"
        assert "GRIMOIRE" in output or "G R I M O I R E" in output
        # Should contain 3 spell pages (each has a bottom border)
        assert output.count("╚") >= 3

    def test_render_spell_list(self):
        output = generate_spell_list(num_spells=5, color=False)
        assert "Level" in output
        assert "School" in output
        assert "Spell Name" in output


class TestSigil:
    """Test sigil generation."""

    def test_sigil_deterministic(self):
        """Same school+level should produce the same sigil."""
        s1 = generate_sigil("Evocation", 5)
        s2 = generate_sigil("Evocation", 5)
        assert s1 == s2, "Same school+level should produce identical sigils"

    def test_sigil_different_schools(self):
        """Different schools should produce different sigils."""
        s1 = generate_sigil("Evocation", 3)
        s2 = generate_sigil("Necromancy", 3)
        assert s1 != s2, "Different schools should produce different sigils"

    def test_sigil_preserves_random_state(self):
        """Generating a sigil should not affect the global random state."""
        import random
        random.seed(12345)
        state_before = random.getstate()
        generate_sigil("Evocation", 3)
        state_after = random.getstate()
        assert state_before == state_after, "Sigil generation should not alter random state"


class TestDiagram:
    """Test diagram generation."""

    def test_diagram_deterministic(self):
        d1 = generate_spell_diagram("Evocation", 5)
        d2 = generate_spell_diagram("Evocation", 5)
        assert d1 == d2

    def test_diagram_preserves_random_state(self):
        import random
        random.seed(12345)
        state_before = random.getstate()
        generate_spell_diagram("Necromancy", 3)
        state_after = random.getstate()
        assert state_before == state_after


class TestIncantation:
    """Test incantation generation."""

    def test_incantation_format(self):
        for school in SCHOOLS:
            inc = generate_incantation(school)
            assert inc.startswith('"'), f"Incantation should start with quote: {inc}"
            assert inc.endswith('"'), f"Incantation should end with quote: {inc}"


class TestJsonExport:
    """Test JSON export functionality."""

    def test_spell_to_dict(self):
        spell = generate_spell()
        d = spell.to_dict()
        assert isinstance(d, dict)
        assert "name" in d
        assert "school" in d
        assert "rarity" in d
        assert "sigil" in d
        assert isinstance(d["sigil"], list)

    def test_spell_to_json(self):
        spell = generate_spell()
        j = spell.to_json()
        parsed = json.loads(j)
        assert parsed["name"] == spell.name
        assert parsed["school"] == spell.school

    def test_json_is_valid_unicode(self):
        """JSON output should handle Unicode characters (sigils, runes)."""
        spell = generate_spell(school="Necromancy", level=5)
        j = spell.to_json()
        # Should be parseable JSON
        parsed = json.loads(j)
        assert len(parsed["sigil"]) > 0


class TestCLI:
    """Test command-line interface."""

    def test_help_flag(self):
        result = subprocess.run(
            [sys.executable, "grimoire.py", "--help"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        assert result.returncode == 0
        assert "Procedural Spell Grimoire Generator" in result.stdout

    def test_version_flag(self):
        result = subprocess.run(
            [sys.executable, "grimoire.py", "--version"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        assert result.returncode == 0
        assert __version__ in result.stdout.strip()

    def test_seed_produces_deterministic_output(self):
        result1 = subprocess.run(
            [sys.executable, "grimoire.py", "--no-color", "--seed", "42"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        result2 = subprocess.run(
            [sys.executable, "grimoire.py", "--no-color", "--seed", "42"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        assert result1.stdout == result2.stdout, "Same seed should produce identical output"

    def test_school_flag(self):
        result = subprocess.run(
            [sys.executable, "grimoire.py", "--no-color", "--seed", "99", "-s", "Necromancy"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        assert "Necromancy" in result.stdout

    def test_json_output(self):
        result = subprocess.run(
            [sys.executable, "grimoire.py", "--json", "--seed", "1"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) == 1
        assert "name" in data[0]

    def test_json_count_output(self):
        result = subprocess.run(
            [sys.executable, "grimoire.py", "--json", "--count", "5", "--seed", "1"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 5

    def test_file_output(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            tmpfile = f.name
        try:
            result = subprocess.run(
                [sys.executable, "grimoire.py", "--no-color", "--seed", "42", "-o", tmpfile],
                capture_output=True, text=True, cwd=os.path.dirname(__file__),
            )
            assert result.returncode == 0
            assert f"Grimoire written to {tmpfile}" in result.stdout
            with open(tmpfile) as f:
                content = f.read()
            assert "\033[" not in content, "File output should not contain ANSI codes"
            assert len(content) > 100, "File should contain substantial content"
        finally:
            os.unlink(tmpfile)

    def test_rarity_flag(self):
        result = subprocess.run(
            [sys.executable, "grimoire.py", "--no-color", "--seed", "7", "--rarity", "Legendary"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        assert "[Legendary]" in result.stdout


if __name__ == "__main__":
    # Simple test runner
    import traceback
    test_classes = [
        TestGenerateSpell, TestRarity, TestRendering,
        TestSigil, TestDiagram, TestIncantation,
        TestJsonExport, TestCLI,
    ]
    passed = 0
    failed = 0
    for cls in test_classes:
        instance = cls()
        for attr in dir(instance):
            if attr.startswith("test_"):
                try:
                    getattr(instance, attr)()
                    passed += 1
                except Exception as e:
                    failed += 1
                    print(f"FAIL: {cls.__name__}.{attr}: {e}")
                    traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed out of {passed + failed} tests")
    sys.exit(0 if failed == 0 else 1)