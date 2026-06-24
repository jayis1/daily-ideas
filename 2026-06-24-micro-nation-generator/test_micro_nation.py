#!/usr/bin/env python3
"""
Unit tests for Procedural Micro-Nation Generator.

Tests nation generation, flag rendering, comparison display,
CLI arguments, seeded reproducibility, and edge cases.
"""

import json
import subprocess
import sys
import unittest

sys.path.insert(0, "/root/daily-ideas/2026-06-24-micro-nation-generator")
import micro_nation as mn


class TestMakeRng(unittest.TestCase):
    """Tests for the make_rng utility function."""

    def test_deterministic_with_same_seed(self):
        """Same seed should produce same RNG sequence."""
        rng1 = mn.make_rng("test-seed")
        rng2 = mn.make_rng("test-seed")
        self.assertEqual(rng1.random(), rng2.random())

    def test_different_seeds_differ(self):
        """Different seeds should produce different sequences."""
        rng1 = mn.make_rng("seed-a")
        rng2 = mn.make_rng("seed-b")
        # Very unlikely to be equal
        vals1 = [rng1.random() for _ in range(10)]
        vals2 = [rng2.random() for _ in range(10)]
        self.assertNotEqual(vals1, vals2)

    def test_none_seed_uses_time(self):
        """None seed should still create a valid RNG."""
        rng = mn.make_rng(None)
        self.assertIsNotNone(rng)
        val = rng.random()
        self.assertIsInstance(val, float)


class TestPick(unittest.TestCase):
    """Tests for the pick utility function."""

    def test_pick_single(self):
        """pick with n=1 should return a single item."""
        rng = mn.make_rng("test")
        result = mn.pick(rng, ["a", "b", "c"])
        self.assertIn(result, ["a", "b", "c"])

    def test_pick_multiple(self):
        """pick with n>1 should return a list of unique items."""
        rng = mn.make_rng("test")
        result = mn.pick(rng, ["a", "b", "c", "d", "e"], 3)
        self.assertEqual(len(result), 3)
        self.assertEqual(len(set(result)), 3)  # all unique

    def test_pick_more_than_list(self):
        """pick with n > list length should return at most len(list) items."""
        rng = mn.make_rng("test")
        result = mn.pick(rng, ["a", "b"], 5)
        self.assertEqual(len(result), 2)


class TestNationGenerator(unittest.TestCase):
    """Tests for NationGenerator."""

    def test_generate_single_nation(self):
        """Should generate a complete MicroNation."""
        gen = mn.NationGenerator(seed="test")
        nation = gen.generate()
        self.assertIsInstance(nation, mn.MicroNation)
        self.assertTrue(len(nation.name) > 0)
        self.assertTrue(len(nation.motto) > 0)
        self.assertTrue(len(nation.government) > 0)
        self.assertIsInstance(nation.population, int)
        self.assertGreater(nation.population, 0)

    def test_seeded_reproducibility(self):
        """Same seed override should produce identical nations."""
        gen1 = mn.NationGenerator(seed="repro-test")
        gen2 = mn.NationGenerator(seed="repro-test")
        n1 = gen1.generate(seed_override="same-seed")
        n2 = gen2.generate(seed_override="same-seed")
        self.assertEqual(n1.name, n2.name)
        self.assertEqual(n1.motto, n2.motto)
        self.assertEqual(n1.government, n2.government)
        self.assertEqual(n1.population, n2.population)

    def test_multiple_nations(self):
        """Should generate multiple nations."""
        gen = mn.NationGenerator(seed="multi")
        nations = [gen.generate(seed_override=f"n-{i}") for i in range(10)]
        self.assertEqual(len(nations), 10)
        # All should have different names (very likely with different seeds)
        names = [n.name for n in nations]
        self.assertGreater(len(set(names)), 1)

    def test_generated_nations_tracked(self):
        """Generated nations should be stored in generator.generated_nations."""
        gen = mn.NationGenerator(seed="track")
        gen.generate(seed_override="a")
        gen.generate(seed_override="b")
        self.assertEqual(len(gen.generated_nations), 2)

    def test_nation_has_all_fields(self):
        """Generated nation should have all expected fields."""
        gen = mn.NationGenerator(seed="fields")
        nation = gen.generate(seed_override="fields-test")
        # Check all fields are populated
        self.assertTrue(nation.name)
        self.assertTrue(nation.motto)
        self.assertTrue(nation.government)
        self.assertTrue(nation.gov_icon)
        self.assertIsInstance(nation.population, int)
        self.assertTrue(nation.terrain)
        self.assertIsInstance(nation.area_sq_km, float)
        self.assertGreater(nation.area_sq_km, 0)
        self.assertTrue(nation.capital)
        self.assertTrue(nation.currency)
        self.assertTrue(nation.national_animal)
        self.assertEqual(len(nation.exports), 3)
        self.assertEqual(len(nation.industries), 3)
        self.assertEqual(len(nation.cultural_events), 3)
        self.assertTrue(nation.personality)
        self.assertIsInstance(nation.founding_year, int)
        self.assertTrue(nation.leader_name)
        self.assertTrue(nation.national_holiday)
        self.assertTrue(nation.anthem_opening)

    def test_population_density(self):
        """Population density should be correctly calculated."""
        nation = mn.MicroNation(
            name="Test", motto="Test", government="Test", gov_icon="🏛️",
            population=10000, terrain="test", area_sq_km=100.0,
            capital="Test", currency="Test", national_animal="Test",
            exports=[], industries=[], cultural_events=[],
            personality="stoic", founding_year=2000,
            flag_pattern="cross", flag_colors=["red", "blue", "white"],
            emblem="star", seed="test"
        )
        self.assertAlmostEqual(nation.population_density, 100.0)

    def test_area_matches_terrain(self):
        """Area should be within the expected range for the terrain type."""
        gen = mn.NationGenerator(seed="area")
        for _ in range(50):
            nation = gen.generate()
            if nation.terrain in mn.TERRAIN_AREAS:
                lo, hi = mn.TERRAIN_AREAS[nation.terrain]
                self.assertGreaterEqual(nation.area_sq_km, lo,
                    f"Area {nation.area_sq_km} below minimum {lo} for {nation.terrain}")
                self.assertLessEqual(nation.area_sq_km, hi,
                    f"Area {nation.area_sq_km} above maximum {hi} for {nation.terrain}")


class TestGenerateRelations(unittest.TestCase):
    """Tests for diplomatic relations generation."""

    def test_relations_generated(self):
        """Should generate relations between nations."""
        gen = mn.NationGenerator(seed="rel")
        n1 = gen.generate(seed_override="r1")
        n2 = gen.generate(seed_override="r2")
        gen.generate_relations()
        self.assertGreater(len(n1.relations), 0)
        self.assertGreater(len(n2.relations), 0)

    def test_relations_no_self(self):
        """A nation should not have relations with itself."""
        gen = mn.NationGenerator(seed="self")
        n1 = gen.generate(seed_override="s1")
        n2 = gen.generate(seed_override="s2")
        gen.generate_relations()
        for rel in n1.relations:
            self.assertNotEqual(rel["nation"], n1.name)

    def test_relations_structure(self):
        """Each relation should have the expected keys."""
        gen = mn.NationGenerator(seed="struct")
        gen.generate(seed_override="st1")
        gen.generate(seed_override="st2")
        gen.generate_relations()
        nation = gen.generated_nations[0]
        for rel in nation.relations:
            self.assertIn("nation", rel)
            self.assertIn("type", rel)
            self.assertIn("icon", rel)
            self.assertIn("strength", rel)
            self.assertIsInstance(rel["strength"], int)
            self.assertGreaterEqual(rel["strength"], 1)
            self.assertLessEqual(rel["strength"], 100)


class TestFlagRenderer(unittest.TestCase):
    """Tests for flag rendering."""

    def test_renders_all_patterns(self):
        """All flag patterns should render without errors."""
        rng = mn.make_rng("flag-test")
        renderer = mn.FlagRenderer(rng)
        for pattern in mn.FLAG_PATTERNS:
            lines = renderer.render(pattern=pattern, flag_colors=["red", "blue", "green"], emblem="star", use_color=False)
            self.assertEqual(len(lines), renderer.HEIGHT)
            for line in lines:
                self.assertTrue(len(line) > 0)

    def test_renders_all_emblems(self):
        """All emblems should render without errors."""
        rng = mn.make_rng("emblem-test")
        renderer = mn.FlagRenderer(rng)
        for emblem in ["star", "diamond", "circle", "crescent", "cross", "triangle"]:
            lines = renderer.render(pattern="horiz_tricolor", flag_colors=["red", "blue", "green"], emblem=emblem, use_color=False)
            self.assertEqual(len(lines), renderer.HEIGHT)

    def test_no_color_mode(self):
        """No-color mode should produce output without ANSI codes."""
        rng = mn.make_rng("nocolor-test")
        renderer = mn.FlagRenderer(rng)
        lines = renderer.render(use_color=False)
        for line in lines:
            self.assertNotIn("\033[", line)

    def test_color_mode(self):
        """Color mode should contain ANSI escape codes."""
        rng = mn.make_rng("color-test")
        renderer = mn.FlagRenderer(rng)
        lines = renderer.render(use_color=True)
        has_ansi = any("\033[" in line for line in lines)
        self.assertTrue(has_ansi)


class TestFormatHelpers(unittest.TestCase):
    """Tests for formatting helper methods."""

    def test_format_population_millions(self):
        """Should format millions correctly."""
        gen = mn.NationGenerator(seed="fmt")
        self.assertEqual(gen.format_population(1_500_000), "1.5M")

    def test_format_population_thousands(self):
        """Should format thousands correctly."""
        gen = mn.NationGenerator(seed="fmt")
        self.assertEqual(gen.format_population(5_000), "5.0K")

    def test_format_population_small(self):
        """Should format small numbers as-is."""
        gen = mn.NationGenerator(seed="fmt")
        self.assertEqual(gen.format_population(999), "999")

    def test_format_area_large(self):
        """Should format large areas."""
        gen = mn.NationGenerator(seed="fmt")
        result = gen.format_area(2_500_000)
        self.assertIn("M", result)

    def test_format_area_thousands(self):
        """Should format thousand-level areas."""
        gen = mn.NationGenerator(seed="fmt")
        result = gen.format_area(5_000)
        self.assertIn("K", result)

    def test_format_area_small(self):
        """Should format small areas as-is."""
        gen = mn.NationGenerator(seed="fmt")
        result = gen.format_area(50.5)
        self.assertIn("50.5", result)


class TestDisplayNation(unittest.TestCase):
    """Tests for nation display formatting."""

    def test_display_contains_name(self):
        """Display should contain the nation name."""
        gen = mn.NationGenerator(seed="display")
        nation = gen.generate(seed_override="disp-test")
        text = gen.display_nation(nation, use_color=False)
        self.assertIn(nation.name.upper(), text)

    def test_display_compact(self):
        """Compact display should be a single line."""
        gen = mn.NationGenerator(seed="compact")
        nation = gen.generate(seed_override="comp-test")
        text = gen.display_nation(nation, use_color=False, compact=True)
        self.assertIn(nation.name, text)
        self.assertIn("|", text)
        # Compact should be one line
        self.assertEqual(len(text.split("\n")), 1)

    def test_display_full_has_sections(self):
        """Full display should have key sections."""
        gen = mn.NationGenerator(seed="full")
        nation = gen.generate(seed_override="full-test")
        text = gen.display_nation(nation, use_color=False)
        self.assertIn(nation.name.upper(), text)
        self.assertIn("Government", text)
        self.assertIn("Population", text)
        self.assertIn("Area", text)
        self.assertIn("Anthem", text)
        self.assertIn("Leader", text)

    def test_display_comparison(self):
        """Comparison display should show attributes side by side."""
        gen = mn.NationGenerator(seed="compare")
        n1 = gen.generate(seed_override="c1")
        n2 = gen.generate(seed_override="c2")
        text = gen.display_comparison([n1, n2], use_color=False)
        self.assertIn("COMPARISON", text)
        self.assertIn(n1.name, text)
        self.assertIn(n2.name, text)


class TestToJson(unittest.TestCase):
    """Tests for JSON serialization."""

    def test_to_dict_has_all_fields(self):
        """to_dict should include all nation fields."""
        gen = mn.NationGenerator(seed="json")
        nation = gen.generate(seed_override="json-test")
        d = gen.to_dict(nation)
        self.assertIn("name", d)
        self.assertIn("motto", d)
        self.assertIn("government", d)
        self.assertIn("population", d)
        self.assertIn("area_sq_km", d)
        self.assertIn("population_density", d)
        self.assertIn("terrain", d)
        self.assertIn("capital", d)
        self.assertIn("leader", d)
        self.assertIn("currency", d)
        self.assertIn("national_animal", d)
        self.assertIn("exports", d)
        self.assertIn("industries", d)
        self.assertIn("cultural_events", d)
        self.assertIn("personality", d)
        self.assertIn("founding_year", d)
        self.assertIn("national_holiday", d)
        self.assertIn("anthem_opening", d)
        self.assertIn("flag_pattern", d)
        self.assertIn("flag_colors", d)
        self.assertIn("emblem", d)
        self.assertIn("seed", d)

    def test_json_serializable(self):
        """to_dict output should be JSON serializable."""
        gen = mn.NationGenerator(seed="ser")
        nation = gen.generate(seed_override="ser-test")
        d = gen.to_dict(nation)
        result = json.dumps(d, ensure_ascii=False)
        self.assertIsInstance(result, str)
        self.assertIn(nation.name, result)


class TestCLI(unittest.TestCase):
    """Tests for command-line interface."""

    def test_help_flag(self):
        """--help should exit with 0."""
        result = subprocess.run(
            [sys.executable, "micro_nation.py", "--help"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-24-micro-nation-generator"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Micro-Nation", result.stdout)

    def test_version_flag(self):
        """--version should exit with 0 and print version."""
        result = subprocess.run(
            [sys.executable, "micro_nation.py", "--version"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-24-micro-nation-generator"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(mn.__version__, result.stdout)

    def test_json_output(self):
        """--json should produce valid JSON."""
        result = subprocess.run(
            [sys.executable, "micro_nation.py", "-n", "2", "--json", "--seed", "clitest"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-24-micro-nation-generator"
        )
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        self.assertIn("name", data[0])

    def test_compact_output(self):
        """--compact should produce one-line-per-nation output."""
        result = subprocess.run(
            [sys.executable, "micro_nation.py", "-n", "3", "--compact", "--seed", "compacttest"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-24-micro-nation-generator"
        )
        self.assertEqual(result.returncode, 0)
        lines = [l for l in result.stdout.strip().split("\n") if l.strip() and not l.startswith("🌱")]
        # Should have at least 3 nation lines
        self.assertGreaterEqual(len(lines), 3)

    def test_default_run(self):
        """Default run should produce output."""
        result = subprocess.run(
            [sys.executable, "micro_nation.py", "--seed", "defaulttest"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-24-micro-nation-generator"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Generated 5", result.stdout)

    def test_single_nation(self):
        """-n 1 should produce a single nation."""
        result = subprocess.run(
            [sys.executable, "micro_nation.py", "-n", "1", "--seed", "onetest"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-24-micro-nation-generator"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Generated 1", result.stdout)

    def test_list_governments(self):
        """--list-governments should list available governments."""
        result = subprocess.run(
            [sys.executable, "micro_nation.py", "--list-governments"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-24-micro-nation-generator"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Constitutional Monarchy", result.stdout)

    def test_no_color(self):
        """--no-color should produce output without ANSI codes."""
        result = subprocess.run(
            [sys.executable, "micro_nation.py", "-n", "1", "--no-color", "--seed", "nocolortest"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-24-micro-nation-generator"
        )
        self.assertEqual(result.returncode, 0)
        # No ANSI escape sequences in output (except reset which shouldn't appear in no-color mode)
        self.assertNotIn("\033[31m", result.stdout)

    def test_version_attribute(self):
        """Module should have a __version__ attribute."""
        self.assertTrue(hasattr(mn, "__version__"))
        self.assertIn(".", mn.__version__)


class TestLeaderGeneration(unittest.TestCase):
    """Tests for leader name generation."""

    def test_leader_name_format(self):
        """Leader names should include a title, first name, and epithet."""
        gen = mn.NationGenerator(seed="leader")
        nation = gen.generate(seed_override="leader-test")
        # Leader name should have at least 3 parts: Title FirstName Epithet
        parts = nation.leader_name.split()
        self.assertGreaterEqual(len(parts), 3)

    def test_leader_title_matches_government(self):
        """Leader title should be appropriate for the government type."""
        gen = mn.NationGenerator(seed="title")
        for _ in range(20):
            nation = gen.generate()
            if nation.government in mn.LEADER_TITLES:
                titles = mn.LEADER_TITLES[nation.government]
                self.assertIn(nation.leader_title, titles,
                    f"Leader title '{nation.leader_title}' doesn't match government '{nation.government}'")


class TestAnthemGeneration(unittest.TestCase):
    """Tests for national anthem generation."""

    def test_anthem_matches_personality(self):
        """Anthem opening should match the nation's personality."""
        gen = mn.NationGenerator(seed="anthem")
        for _ in range(30):
            nation = gen.generate()
            self.assertIn(nation.anthem_opening, mn.ANTHEM_OPENINGS.get(nation.personality, []),
                f"Anthem '{nation.anthem_opening}' doesn't match personality '{nation.personality}'")


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and error handling."""

    def test_empty_relations_list(self):
        """Nation with no relations should display correctly."""
        gen = mn.NationGenerator(seed="norel")
        nation = gen.generate(seed_override="norel-test")
        text = gen.display_nation(nation, use_color=False)
        # Should not crash, and should not contain "Diplomatic Relations"
        self.assertNotIn("Diplomatic Relations", text)

    def test_comparison_with_single_nation(self):
        """Comparison with one nation should still work."""
        gen = mn.NationGenerator(seed="single-comp")
        nation = gen.generate(seed_override="sc-test")
        text = gen.display_comparison([nation], use_color=False)
        self.assertIn(nation.name, text)

    def test_comparison_empty(self):
        """Comparison with no nations should handle gracefully."""
        gen = mn.NationGenerator(seed="empty-comp")
        text = gen.display_comparison([], use_color=False)
        self.assertIn("No nations", text)


if __name__ == "__main__":
    unittest.main()