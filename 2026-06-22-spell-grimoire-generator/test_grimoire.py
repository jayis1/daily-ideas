#!/usr/bin/env python3
"""Tests for the Spell Grimoire Generator v3.0.0."""

import json
import random
import subprocess
import sys
import os
import tempfile

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from grimoire import (
    generate_spell, generate_grimoire, generate_spell_list,
    render_grimoire_page, render_plaintext_page, render_side_by_side,
    strip_ansi, ordinal, choose_rarity, SPELL_LEVELS, SCHOOLS, RARITIES,
    generate_incantation, generate_sigil, generate_spell_diagram,
    wrap_text, pluralize, calculate_mana_cost, generate_tags,
    find_synergies, render_synergies, save_spells, load_spells,
    MANA_COSTS, MANA_MULTIPLIERS, TAG_POOLS, SYNERGY_PAIRS,
    format_duration_phrase, format_duration_phrase_cap, format_hp_phrase,
    _reset_generated_names,
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
        assert len(spell.tags) > 0, "Should have tags"
        assert isinstance(spell.mana_cost, int), "Mana cost should be an integer"
        assert spell.mana_cost >= 0, "Mana cost should be non-negative"

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
            names.add(spell.name)
        # Allow a small number of collisions but not many
        assert len(names) >= 40, f"Too many name collisions: {50 - len(names)}"

    def test_grammar_singular_count(self):
        """Descriptions with count=1 should use singular nouns."""
        random.seed(42)
        for _ in range(200):
            spell = generate_spell()
            desc = spell.description
            assert "1 undead servants" not in desc, f"Singular bug: {desc}"
            assert "1 creatures become" not in desc, f"Singular bug: {desc}"
            assert "1 allies" not in desc, f"Singular bug: {desc}"
            assert "1 hidden objects" not in desc, f"Singular bug: {desc}"
            assert "1 days" not in desc, f"Singular bug: {desc}"
            assert "1 yes/no questions" not in desc, f"Singular bug: {desc}"

    def test_tags_are_generated(self):
        """Every spell should have tags."""
        spell = generate_spell()
        assert len(spell.tags) >= 1, "Spell should have at least one tag"
        assert spell.school.lower() in spell.tags, "Tags should include school"

    def test_mana_cost_is_non_negative(self):
        """Mana cost should always be non-negative."""
        for level in range(10):
            for school in SCHOOLS:
                cost = calculate_mana_cost(level, school, "Common", "1 action", "Instantaneous")
                assert cost >= 0, f"Mana cost should be >= 0: level={level}, school={school}"

    def test_mana_cost_increases_with_level(self):
        """Higher level spells should generally cost more mana."""
        costs = []
        for level in range(10):
            costs.append(calculate_mana_cost(level, "Evocation", "Common", "1 action", "Instantaneous"))
        # Generally increasing (allowing for some rounding effects)
        assert costs[0] <= costs[5] <= costs[9], f"Mana costs should increase with level: {costs}"


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
        high_level_count = 0
        for _ in range(30):
            spell = generate_spell(rarity="Legendary")
            if spell.level >= 3:
                high_level_count += 1
        assert high_level_count >= 5, f"Expected some Legendary spells to be high level, got {high_level_count}/30"


class TestManaCost:
    """Test mana cost calculation."""

    def test_cantrip_mana_cost_is_low(self):
        """Cantrips should have very low mana cost (0 base + modifiers)."""
        cost = calculate_mana_cost(0, "Evocation", "Common", "1 action", "Instantaneous")
        # Base is 0, but "1 action" (quick cast) adds 3, so total is 3
        assert cost <= 5

    def test_school_multiplier_affects_cost(self):
        """Schools with higher multipliers should cost more."""
        cost_conj = calculate_mana_cost(5, "Conjuration", "Common", "1 action", "Instantaneous")
        cost_div = calculate_mana_cost(5, "Divination", "Common", "1 action", "Instantaneous")
        assert cost_conj > cost_div, "Conjuration (1.15x) should cost more than Divination (0.85x)"

    def test_rarity_modifies_cost(self):
        """Higher rarity should add to mana cost."""
        cost_common = calculate_mana_cost(5, "Evocation", "Common", "1 action", "Instantaneous")
        cost_legendary = calculate_mana_cost(5, "Evocation", "Legendary", "1 action", "Instantaneous")
        assert cost_legendary > cost_common

    def test_quick_cast_adds_cost(self):
        """Quick casting times should add to mana cost."""
        cost_action = calculate_mana_cost(3, "Evocation", "Common", "1 action", "Instantaneous")
        cost_ritual = calculate_mana_cost(3, "Evocation", "Common", "1 hour", "Instantaneous")
        assert cost_action > cost_ritual

    def test_long_duration_adds_cost(self):
        """Long durations should add to mana cost."""
        cost_instant = calculate_mana_cost(3, "Evocation", "Common", "1 action", "Instantaneous")
        cost_long = calculate_mana_cost(3, "Evocation", "Common", "1 action", "Until dispelled")
        assert cost_long > cost_instant


class TestTags:
    """Test tag generation."""

    def test_tags_include_school(self):
        """Tags should always include the school."""
        for school in SCHOOLS:
            tags = generate_tags(school, 3)
            assert school.lower() in tags

    def test_cantrip_tag(self):
        """Level 0 spells should get the cantrip tag."""
        tags = generate_tags("Evocation", 0)
        assert "cantrip" in tags

    def test_epic_tag(self):
        """Level 7+ spells should get the epic tag."""
        tags = generate_tags("Evocation", 8)
        assert "epic" in tags

    def test_rarity_tag(self):
        """Non-Common rarity should add a tag."""
        tags = generate_tags("Evocation", 3, rarity="Legendary")
        assert "legendary" in tags

    def test_common_no_rarity_tag(self):
        """Common rarity should not add a rarity tag."""
        tags = generate_tags("Evocation", 3, rarity="Common")
        assert "common" not in tags


class TestSynergies:
    """Test spell synergy detection."""

    def test_find_synergies_evocation_abjuration(self):
        """Evocation + Abjuration should be a synergy pair."""
        s1 = generate_spell(school="Evocation", level=5)
        s2 = generate_spell(school="Abjuration", level=3)
        synergies = find_synergies([s1, s2])
        assert len(synergies) > 0

    def test_no_synergies_same_school(self):
        """Two spells of the same school typically don't have a specific synergy."""
        s1 = generate_spell(school="Evocation", level=3)
        s2 = generate_spell(school="Evocation", level=5)
        synergies = find_synergies([s1, s2])
        # Same school pair is not in SYNERGY_PAIRS (keys are different schools)
        assert len(synergies) == 0

    def test_synergies_description(self):
        """Synergy descriptions should be non-empty strings."""
        s1 = generate_spell(school="Evocation", level=5)
        s2 = generate_spell(school="Abjuration", level=3)
        synergies = find_synergies([s1, s2])
        for _, _, desc in synergies:
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_render_synergies_no_synergies(self):
        """Rendering with no synergies should report that fact."""
        s1 = generate_spell(school="Evocation", level=3)
        s2 = generate_spell(school="Evocation", level=5)
        result = render_synergies([s1, s2])
        assert "No synergies" in result


class TestSaveLoad:
    """Test save and load functionality."""

    def test_save_and_load_spells(self):
        """Spells should round-trip through save/load."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp = f.name

        try:
            spells = [generate_spell() for _ in range(3)]
            save_spells(spells, tmp)

            loaded = load_spells(tmp)
            assert len(loaded) == 3
            for original, loaded_spell in zip(spells, loaded):
                assert original.name == loaded_spell.name
                assert original.school == loaded_spell.school
                assert original.level == loaded_spell.level
                assert original.mana_cost == loaded_spell.mana_cost
                assert original.tags == loaded_spell.tags
        finally:
            os.unlink(tmp)

    def test_save_load_preserves_tags(self):
        """Tags should be preserved through save/load."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp = f.name

        try:
            spell = generate_spell()
            save_spells([spell], tmp)
            loaded = load_spells(tmp)
            assert loaded[0].tags == spell.tags
        finally:
            os.unlink(tmp)

    def test_load_nonexistent_file(self):
        """Loading a nonexistent file should raise an error."""
        try:
            load_spells("/nonexistent/path/spells.json")
            assert False, "Should have raised an error"
        except (OSError, FileNotFoundError):
            pass  # Expected


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

    def test_render_page_contains_mana_cost(self):
        """Mana cost should appear in rendered pages."""
        spell = generate_spell(level=5)
        page = render_grimoire_page(spell, color=False)
        assert "Mana" in page
        assert str(spell.mana_cost) in page

    def test_render_page_contains_tags(self):
        """Tags should appear in rendered pages."""
        spell = generate_spell(school="Evocation", level=3)
        page = render_grimoire_page(spell, color=False)
        # At least the school should appear as a tag
        assert "evocation" in page.lower()

    def test_render_page_no_ansi_in_plaintext(self):
        spell = generate_spell()
        page = render_plaintext_page(spell)
        assert "\033[" not in page, "Plaintext page should not contain ANSI codes"

    def test_strip_ansi(self):
        text = "\033[38;5;196mHello\033[0m World"
        assert strip_ansi(text) == "Hello World"

    def test_render_grimoire_multiple_spells(self):
        output = generate_grimoire(num_spells=3, color=False)
        assert "GRIMOIRE" in output or "G R I M O I R E" in output
        assert output.count("╚") >= 3

    def test_render_spell_list(self):
        output = generate_spell_list(num_spells=5, color=False)
        assert "Level" in output
        assert "School" in output
        assert "Mana" in output

    def test_box_alignment_plaintext(self):
        """All lines with ║ should be exactly 64 chars wide in plaintext."""
        random.seed(42)
        for _ in range(20):
            spell = generate_spell()
            page = render_plaintext_page(spell)
            for line in page.split('\n'):
                if '║' in line:
                    assert len(line) == 64, f"Line width {len(line)} != 64: {line}"

    def test_box_alignment_colored(self):
        """All lines with ║ should be exactly 64 chars wide (visible) when colored."""
        random.seed(42)
        for _ in range(10):
            spell = generate_spell()
            page = render_grimoire_page(spell, color=True)
            clean = strip_ansi(page)
            for line in clean.split('\n'):
                if '║' in line:
                    assert len(line) == 64, f"Line width {len(line)} != 64: {line}"

    def test_grimoire_header_alignment(self):
        """Grimoire header lines should be 64 chars wide."""
        output = generate_grimoire(num_spells=1, color=False)
        for line in output.split('\n'):
            if '║' in line:
                assert len(line) == 64, f"Header line width {len(line)} != 64: {line}"

    def test_higher_levels_wrapping(self):
        """'At Higher Levels' text should not overflow the box."""
        random.seed(42)
        for level in range(1, 9):
            spell = generate_spell(level=level)
            page = render_plaintext_page(spell)
            for line in page.split('\n'):
                if '║' in line:
                    assert len(line) == 64, f"HL overflow at level {level}: {line}"


class TestSideBySide:
    """Test side-by-side comparison rendering."""

    def test_side_by_side_produces_output(self):
        """Side-by-side rendering should produce output."""
        s1 = generate_spell(school="Evocation", level=3)
        s2 = generate_spell(school="Necromancy", level=5)
        result = render_side_by_side(s1, s2, color=False)
        assert len(result) > 0
        assert s1.name in result
        assert s2.name in result

    def test_side_by_side_has_separator(self):
        """Side-by-side output should have a separator between spells."""
        s1 = generate_spell(school="Evocation", level=3)
        s2 = generate_spell(school="Necromancy", level=5)
        result = render_side_by_side(s1, s2, color=False)
        assert "│" in result


class TestMarkdownExport:
    """Test Markdown export functionality."""

    def test_markdown_has_headers(self):
        """Markdown output should have proper headers."""
        spell = generate_spell(school="Evocation", level=3)
        md = spell.to_markdown()
        assert f"# {spell.name}" in md
        assert "## Description" in md

    def test_markdown_has_metadata(self):
        """Markdown output should contain metadata."""
        spell = generate_spell(school="Necromancy", level=5)
        md = spell.to_markdown()
        assert "Casting Time" in md
        assert "Range" in md
        assert "Duration" in md
        assert "Mana Cost" in md

    def test_markdown_has_tags(self):
        """Markdown output should include tags section."""
        spell = generate_spell(school="Evocation", level=3)
        md = spell.to_markdown()
        assert "## Tags" in md
        assert spell.school.lower() in md.lower()

    def test_markdown_has_incantation(self):
        """Markdown output should include incantation."""
        spell = generate_spell()
        md = spell.to_markdown()
        assert "## Incantation" in md

    def test_markdown_has_lore(self):
        """Markdown output should include lore section."""
        spell = generate_spell()
        md = spell.to_markdown()
        assert "## Lore" in md


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
        random.seed(12345)
        state_before = random.getstate()
        generate_spell_diagram("Necromancy", 3)
        state_after = random.getstate()
        assert state_after == state_before


class TestIncantation:
    """Test incantation generation."""

    def test_incantation_format(self):
        for school in SCHOOLS:
            inc = generate_incantation(school)
            assert inc.startswith('"'), f"Incantation should start with quote: {inc}"
            assert inc.endswith('"'), f"Incantation should end with quote: {inc}"


class TestPluralize:
    """Test the pluralize helper."""

    def test_singular(self):
        assert pluralize(1, "undead servant", "undead servants") == "1 undead servant"
        assert pluralize(1, "ally", "allies") == "1 ally"
        assert pluralize(1, "creature", "creatures") == "1 creature"
        assert pluralize(1, "hidden object", "hidden objects") == "1 hidden object"
        assert pluralize(1, "day", "days") == "1 day"

    def test_plural(self):
        assert pluralize(2, "undead servant", "undead servants") == "2 undead servants"
        assert pluralize(3, "ally", "allies") == "3 allies"
        assert pluralize(5, "creature", "creatures") == "5 creatures"


class TestWrapText:
    """Test the wrap_text function."""

    def test_basic_wrap(self):
        result = wrap_text("hello world", width=5)
        assert result == ["hello", "world"]

    def test_first_line_width(self):
        """wrap_text with first_line_width should wrap the first line shorter."""
        text = "When cast using a spell slot of 4th level or higher, the number increases"
        result = wrap_text(text, width=56, first_line_width=38)
        assert len(result[0]) <= 38, f"First line too long: {len(result[0])} > 38"
        for line in result[1:]:
            assert len(line) <= 56, f"Subsequent line too long: {line}"


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
        assert "tags" in d
        assert "mana_cost" in d
        assert isinstance(d["sigil"], list)
        assert isinstance(d["tags"], list)

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
        parsed = json.loads(j)
        assert len(parsed["sigil"]) > 0

    def test_json_has_tags_and_mana(self):
        """JSON export should include tags and mana_cost."""
        spell = generate_spell()
        d = spell.to_dict()
        assert isinstance(d["tags"], list)
        assert isinstance(d["mana_cost"], int)


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

    def test_markdown_output(self):
        """Markdown flag should produce Markdown output."""
        result = subprocess.run(
            [sys.executable, "grimoire.py", "--markdown", "--seed", "42"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        assert result.returncode == 0
        assert "## Description" in result.stdout

    def test_markdown_file_output(self):
        """Markdown output should work with file output."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            tmpfile = f.name
        try:
            result = subprocess.run(
                [sys.executable, "grimoire.py", "--markdown", "--seed", "42", "-o", tmpfile],
                capture_output=True, text=True, cwd=os.path.dirname(__file__),
            )
            assert result.returncode == 0
            with open(tmpfile) as f:
                content = f.read()
            assert "## Description" in content
        finally:
            os.unlink(tmpfile)

    def test_synergies_flag(self):
        """--synergies flag should produce output."""
        result = subprocess.run(
            [sys.executable, "grimoire.py", "--synergies", "5", "--seed", "42", "--no-color"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        assert result.returncode == 0
        # Should contain "Synergies" header
        assert "Synerg" in result.stdout or "spell" in result.stdout.lower()

    def test_compare_flag(self):
        """--compare flag should produce side-by-side output."""
        result = subprocess.run(
            [sys.executable, "grimoire.py", "--compare", "--seed", "42", "--no-color"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        assert result.returncode == 0
        assert len(result.stdout) > 100  # Should produce substantial output

    def test_json_has_new_fields(self):
        """JSON output should include tags and mana_cost."""
        result = subprocess.run(
            [sys.executable, "grimoire.py", "--json", "--seed", "1"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        data = json.loads(result.stdout)
        assert "tags" in data[0]
        assert "mana_cost" in data[0]
        assert isinstance(data[0]["tags"], list)
        assert isinstance(data[0]["mana_cost"], int)


class TestEdgeCases:
    """Test edge cases."""

    def test_cantrip_mana_cost_is_low(self):
        """Cantrips should have very low mana cost (base 0 + small modifiers)."""
        for school in SCHOOLS:
            cost = calculate_mana_cost(0, school, "Common", "1 hour", "Instantaneous")
            # Base is 0, no quick cast penalty (1 hour), no long duration
            assert cost == 0, f"Cantrip base mana cost should be 0 for {school}, got {cost}"

    def test_save_load_roundtrip_all_fields(self):
        """All fields including tags and mana_cost should survive save/load."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp = f.name
        try:
            spell = generate_spell(school="Evocation", level=5, rarity="Rare")
            save_spells([spell], tmp)
            loaded = load_spells(tmp)
            assert loaded[0].name == spell.name
            assert loaded[0].tags == spell.tags
            assert loaded[0].mana_cost == spell.mana_cost
            assert loaded[0].higher_levels == spell.higher_levels
        finally:
            os.unlink(tmp)


class TestDurationPhrase:
    """Test duration phrase formatting."""

    def test_instantaneous_is_empty(self):
        """Instantaneous duration should produce no phrase."""
        assert format_duration_phrase("Instantaneous") == ""

    def test_until_dispelled(self):
        """'Until dispelled' should produce 'until dispelled'."""
        result = format_duration_phrase("Until dispelled")
        assert result == " until dispelled"

    def test_until_the_next_dawn(self):
        """'Until the next dawn' should produce 'until the next dawn'."""
        result = format_duration_phrase("Until the next dawn")
        assert result == " until the next dawn"

    def test_regular_duration(self):
        """Regular durations should produce 'for X' phrases."""
        assert format_duration_phrase("1 minute") == " for 1 minute"
        assert format_duration_phrase("10 minutes") == " for 10 minutes"
        assert format_duration_phrase("1 hour") == " for 1 hour"
        assert format_duration_phrase("24 hours") == " for 24 hours"
        assert format_duration_phrase("1 round") == " for 1 round"

    def test_concentration_duration(self):
        """Concentration durations should produce 'for up to X' phrases."""
        result = format_duration_phrase("Concentration, up to 1 minute")
        assert result == " for up to 1 minute"
        result = format_duration_phrase("Concentration, up to 10 minutes")
        assert result == " for up to 10 minutes"
        result = format_duration_phrase("Concentration, up to 1 hour")
        assert result == " for up to 1 hour"

    def test_duration_phrase_cap(self):
        """Capitalized version should start with uppercase."""
        assert format_duration_phrase_cap("1 minute") == " For 1 minute"
        assert format_duration_phrase_cap("Instantaneous") == ""

    def test_hp_phrase_singular(self):
        """Singular count should produce 'with X HP'."""
        assert format_hp_phrase(1, 25) == " with 25 HP"

    def test_hp_phrase_plural(self):
        """Plural count should produce ', each with X HP'."""
        assert format_hp_phrase(3, 25) == ", each with 25 HP"


class TestDescriptionGrammar:
    """Test that generated descriptions have correct grammar."""

    def test_no_for_instantaneous(self):
        """Descriptions should never contain 'for Instantaneous'."""
        random.seed(42)
        for _ in range(200):
            spell = generate_spell()
            assert "for Instantaneous" not in spell.description, \
                f"'for Instantaneous' found: {spell.description}"

    def test_no_singular_each_with(self):
        """Singular undead servant should not have 'each with'."""
        random.seed(42)
        for _ in range(200):
            spell = generate_spell(school="Necromancy")
            if "1 undead servant" in spell.description:
                assert ", each with" not in spell.description, \
                    f"Singular 'each with' found: {spell.description}"

    def test_no_for_until(self):
        """Descriptions should not have 'for Until' (capitalized)."""
        random.seed(42)
        for _ in range(200):
            spell = generate_spell()
            assert "for Until" not in spell.description, \
                f"'for Until' found: {spell.description}"


class TestSeedDeterminism:
    """Test that --seed produces deterministic output."""

    def test_seed_reset_produces_same_names(self):
        """Same seed should produce same spell names after reset."""
        _reset_generated_names()
        random.seed(777)
        names1 = [generate_spell().name for _ in range(10)]
        _reset_generated_names()
        random.seed(777)
        names2 = [generate_spell().name for _ in range(10)]
        assert names1 == names2, "Same seed should produce same names after reset"


class TestGrimoireSave:
    """Test that --grimoire with --save works correctly."""

    def test_grimoire_save_flag(self):
        """--grimoire --save should save spells to a JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp = f.name
        try:
            result = subprocess.run(
                [sys.executable, "grimoire.py", "--grimoire", "--no-color",
                 "--seed", "42", "--save", tmp],
                capture_output=True, text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )
            assert result.returncode == 0, f"Exit code {result.returncode}: {result.stderr}"
            assert f"Saved 5 spells to {tmp}" in result.stdout, \
                f"Expected save message in output: {result.stdout}"
            # Verify file contents
            with open(tmp) as f:
                data = json.load(f)
            assert len(data) == 5, f"Expected 5 spells, got {len(data)}"
            assert all("name" in s for s in data), "Each spell should have a name"
        finally:
            os.unlink(tmp)

    def test_list_save_flag(self):
        """--list --save should save spells to a JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp = f.name
        try:
            result = subprocess.run(
                [sys.executable, "grimoire.py", "--list", "3", "--no-color",
                 "--seed", "42", "--save", tmp],
                capture_output=True, text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )
            assert result.returncode == 0, f"Exit code {result.returncode}: {result.stderr}"
            assert f"Saved 3 spells to {tmp}" in result.stdout
            with open(tmp) as f:
                data = json.load(f)
            assert len(data) == 3
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    # Simple test runner
    import traceback
    test_classes = [
        TestGenerateSpell, TestRarity, TestManaCost, TestTags,
        TestSynergies, TestSaveLoad, TestRendering, TestSideBySide,
        TestMarkdownExport, TestSigil, TestDiagram, TestIncantation,
        TestPluralize, TestWrapText, TestJsonExport, TestCLI,
        TestEdgeCases, TestDurationPhrase, TestDescriptionGrammar,
        TestSeedDeterminism, TestGrimoireSave,
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