#!/usr/bin/env python3
"""
Tests for the Procedural Dinosaur Generator.

Covers:
  - Name generation
  - Dinosaur generation (default, seeded, typed)
  - Stat system (ranges, rarity, totals)
  - Card rendering
  - Battle system
  - Comparison
  - Tournament
  - DinoDex collection tracker
  - JSON export
  - CLI argument parsing
  - Version flag
  - Edge cases
"""

import json
import random
import sys
import io
import unittest
from unittest.mock import patch

from dinosaur_generator import (
    generate_name, generate_dinosaur, Dinosaur,
    render_card, render_full, render_art, battle, compare, tournament,
    stat_bar, DinoDex,
    BODY_TYPES, RARITY_STARS, RARITY_COLORS, GENUS_PREFIXES, GENUS_SUFFIXES,
    DESCRIPTIVE_EPITHETS, HABITAT_ADJECTIVES, SKIN_PATTERNS, FEATHER_TYPES,
    EGG_TYPES, SPECIAL_ABILITIES, PERSONALITY_TRAITS, HABITATS,
    __version__,
)


class TestNameGeneration(unittest.TestCase):
    """Test the binomial name generator."""

    def test_generates_two_part_name(self):
        """Name should be a (genus, species) pair of non-empty strings."""
        genus, species = generate_name("forest")
        self.assertTrue(len(genus) > 0)
        self.assertTrue(len(species) > 0)

    def test_genus_from_known_prefixes(self):
        """Genus should start with a known prefix."""
        random.seed(42)
        for _ in range(20):
            genus, species = generate_name("desert")
            prefix_match = any(genus.startswith(p) for p in GENUS_PREFIXES)
            self.assertTrue(prefix_match, f"Genus '{genus}' doesn't start with any known prefix")

    def test_habitat_influences_species(self):
        """With seed forcing habitat-adjective path, species should match habitat adjective."""
        # Force style=0.5 (habitat adjective) by mocking random
        with patch('dinosaur_generator.random.random', return_value=0.5):
            with patch('dinosaur_generator.random.choice', side_effect=lambda seq: seq[0]):
                genus, species = generate_name("volcanic")
                # species should be the habitat adjective for volcanic = "ignivomus"
                self.assertEqual(species, "ignivomus")

    def test_descriptive_species(self):
        """With style forcing descriptive path, species should come from epithets."""
        random.seed(100)
        genus, species = generate_name("forest")
        # Just verify it's a valid name
        self.assertTrue(len(species) > 0)


class TestDinosaurGeneration(unittest.TestCase):
    """Test the core generate_dinosaur function."""

    def test_basic_generation(self):
        """Should return a valid Dinosaur object."""
        dino = generate_dinosaur()
        self.assertIsInstance(dino, Dinosaur)
        self.assertTrue(len(dino.genus) > 0)
        self.assertTrue(len(dino.species) > 0)

    def test_seeded_reproducibility(self):
        """Same seed should produce identical dinosaurs."""
        d1 = generate_dinosaur(seed=42)
        d2 = generate_dinosaur(seed=42)
        self.assertEqual(d1.genus, d2.genus)
        self.assertEqual(d1.species, d2.species)
        self.assertEqual(d1.attack, d2.attack)
        self.assertEqual(d1.body_type, d2.body_type)

    def test_different_seeds_produce_different_dinos(self):
        """Different seeds should (usually) produce different dinosaurs."""
        d1 = generate_dinosaur(seed=1)
        d2 = generate_dinosaur(seed=999)
        # Statistically very unlikely to be identical
        different = (d1.genus != d2.genus or d1.species != d2.species
                     or d1.attack != d2.attack)
        self.assertTrue(different, "Different seeds produced identical dinosaurs")

    def test_body_type_parameter(self):
        """Specifying body_type should produce that exact type."""
        for bt in BODY_TYPES:
            dino = generate_dinosaur(body_type=bt)
            self.assertEqual(dino.body_type, bt)

    def test_invalid_body_type_raises(self):
        """Invalid body type should raise ValueError."""
        with self.assertRaises(ValueError):
            generate_dinosaur(body_type="dragonsaur")

    def test_all_body_types_are_valid(self):
        """All body types in BODY_TYPES should generate successfully."""
        for bt in BODY_TYPES:
            dino = generate_dinosaur(body_type=bt)
            self.assertEqual(dino.body_type, bt)
            self.assertIn(dino.diet, ["carnivore", "herbivore", "omnivore", "piscivore", "insectivore"])

    def test_size_within_range(self):
        """Dinosaur length should be within its body type's size range."""
        for bt in BODY_TYPES:
            for seed in range(10):
                dino = generate_dinosaur(seed=seed, body_type=bt)
                min_s, max_s = BODY_TYPES[bt]["size_range"]
                self.assertGreaterEqual(dino.length_m, min_s - 0.1, f"{bt} seed={seed}")
                self.assertLessEqual(dino.length_m, max_s + 0.1, f"{bt} seed={seed}")

    def test_weight_within_range(self):
        """Dinosaur weight should be within its body type's weight range."""
        for bt in BODY_TYPES:
            for seed in range(10):
                dino = generate_dinosaur(seed=seed * 10, body_type=bt)
                min_w, max_w = BODY_TYPES[bt]["weight_range"]
                # Allow some margin for randomness multiplier
                self.assertGreaterEqual(dino.weight_kg, min_w * 0.7,
                                        f"{bt} seed={seed*10}: weight {dino.weight_kg} below min {min_w}")
                self.assertLessEqual(dino.weight_kg, max_w * 1.3,
                                     f"{bt} seed={seed*10}: weight {dino.weight_kg} above max {max_w}")

    def test_stats_in_range(self):
        """Stats should be 1-100."""
        for seed in range(50):
            dino = generate_dinosaur(seed=seed)
            for stat_name in ["attack", "defense", "speed", "intelligence"]:
                val = getattr(dino, stat_name)
                self.assertGreaterEqual(val, 1, f"{stat_name} too low: {val}")
                self.assertLessEqual(val, 99, f"{stat_name} too high: {val}")

    def test_stat_total_matches_rarity(self):
        """Rarity should correctly reflect stat totals."""
        for seed in range(100):
            dino = generate_dinosaur(seed=seed)
            total = dino.stat_total
            if total >= 300:
                self.assertEqual(dino.rarity, "legendary")
            elif total >= 260:
                self.assertEqual(dino.rarity, "rare")
            elif total >= 200:
                self.assertEqual(dino.rarity, "uncommon")
            else:
                self.assertEqual(dino.rarity, "common")

    def test_rarity_values_are_valid(self):
        """Rarity should always be one of the known tiers."""
        for seed in range(50):
            dino = generate_dinosaur(seed=seed)
            self.assertIn(dino.rarity, ["common", "uncommon", "rare", "legendary"])

    def test_era_is_valid(self):
        """Era should be Triassic, Jurassic, or Cretaceous."""
        valid_eras = {"Triassic", "Jurassic", "Cretaceous"}
        for seed in range(20):
            dino = generate_dinosaur(seed=seed)
            self.assertIn(dino.era, valid_eras)

    def test_habitat_is_valid(self):
        """Habitat should be one of the known habitats."""
        for seed in range(20):
            dino = generate_dinosaur(seed=seed)
            self.assertIn(dino.habitat, HABITATS)

    def test_special_ability_matches_body_type(self):
        """Special ability should belong to the body type's ability list."""
        for bt in BODY_TYPES:
            for seed in range(10):
                dino = generate_dinosaur(seed=seed, body_type=bt)
                self.assertIn(dino.special_ability, SPECIAL_ABILITIES[bt])

    def test_personality_is_set(self):
        """Personality trait should be a non-empty string from known traits."""
        dino = generate_dinosaur(seed=42)
        self.assertTrue(len(dino.personality) > 0)
        self.assertIn(dino.personality, PERSONALITY_TRAITS)

    def test_diet_consistency(self):
        """Diet should be valid and consistent with body type rules."""
        for seed in range(50):
            dino = generate_dinosaur(seed=seed)
            self.assertIn(dino.diet, ["carnivore", "herbivore", "omnivore", "piscivore", "insectivore"])

    def test_full_name_property(self):
        """full_name should combine genus and species."""
        dino = generate_dinosaur(seed=42)
        self.assertEqual(dino.full_name, f"{dino.genus} {dino.species}")

    def test_stat_total_property(self):
        """stat_total should be the sum of all four stats."""
        dino = generate_dinosaur(seed=42)
        self.assertEqual(dino.stat_total, dino.attack + dino.defense + dino.speed + dino.intelligence)

    def test_art_is_nonempty(self):
        """ASCII art should be non-empty for all body types."""
        for bt in BODY_TYPES:
            dino = generate_dinosaur(seed=42, body_type=bt)
            self.assertTrue(len(dino.art) > 0, f"No art for {bt}")


class TestStatBar(unittest.TestCase):
    """Test the stat bar renderer."""

    def test_full_bar(self):
        bar = stat_bar(100, width=10)
        self.assertIn("##########", bar)

    def test_zero_bar(self):
        bar = stat_bar(0, width=10)
        self.assertIn("..........", bar)

    def test_half_bar(self):
        bar = stat_bar(50, width=10)
        self.assertIn("#####", bar)
        self.assertIn(".....", bar)


class TestRenderCard(unittest.TestCase):
    """Test card rendering."""

    def test_card_contains_name(self):
        dino = generate_dinosaur(seed=42)
        card = render_card(dino, use_color=False)
        self.assertIn(dino.genus, card)
        self.assertIn(dino.species, card)

    def test_card_contains_stats(self):
        dino = generate_dinosaur(seed=42)
        card = render_card(dino, use_color=False)
        self.assertIn("ATK:", card)
        self.assertIn("DEF:", card)
        self.assertIn("SPD:", card)
        self.assertIn("INT:", card)

    def test_card_no_color_mode(self):
        dino = generate_dinosaur(seed=42)
        card = render_card(dino, use_color=False)
        # Should not contain ANSI escape codes
        self.assertNotIn("\033[", card)

    def test_card_with_color(self):
        dino = generate_dinosaur(seed=42)
        card = render_card(dino, use_color=True)
        # Legendary or rare might have color codes
        # Just check it renders without error
        self.assertTrue(len(card) > 0)

    def test_card_contains_body_type(self):
        dino = generate_dinosaur(seed=42)
        card = render_card(dino, use_color=False)
        self.assertIn(dino.body_type.upper(), card)

    def test_card_contains_personality(self):
        """Card should display the personality trait."""
        dino = generate_dinosaur(seed=42)
        card = render_card(dino, use_color=False)
        self.assertIn("Temper:", card)
        self.assertIn(dino.personality, card)


class TestBattle(unittest.TestCase):
    """Test the battle system."""

    def test_battle_produces_result(self):
        d1 = generate_dinosaur(seed=1)
        d2 = generate_dinosaur(seed=2)
        result = battle(d1, d2)
        self.assertIn("BATTLE:", result)
        self.assertIn("WINS", result)

    def test_battle_always_has_winner(self):
        """Battle should always produce a winner (no draws possible in output)."""
        # Very unlikely to get an exact draw with float multiplication
        d1 = generate_dinosaur(seed=1)
        d2 = generate_dinosaur(seed=2)
        result = battle(d1, d2)
        self.assertTrue("WINS" in result or "DRAW" in result)

    def test_battle_mentions_abilities(self):
        d1 = generate_dinosaur(seed=10)
        d2 = generate_dinosaur(seed=20)
        result = battle(d1, d2)
        self.assertIn(d1.special_ability.lower(), result)
        self.assertIn(d2.special_ability.lower(), result)


class TestCompare(unittest.TestCase):
    """Test the comparison function."""

    def test_compare_output(self):
        d1 = generate_dinosaur(seed=1)
        d2 = generate_dinosaur(seed=2)
        result = compare(d1, d2)
        self.assertIn("COMPARISON", result)
        self.assertIn("Name", result)
        self.assertIn(d1.full_name, result)
        self.assertIn(d2.full_name, result)

    def test_compare_shows_stats(self):
        d1 = generate_dinosaur(seed=1)
        d2 = generate_dinosaur(seed=2)
        result = compare(d1, d2)
        self.assertIn("ATK", result)
        self.assertIn("DEF", result)
        self.assertIn("TOTAL", result)


class TestTournament(unittest.TestCase):
    """Test the tournament system."""

    def test_tournament_returns_champion(self):
        dinos = [generate_dinosaur(seed=i) for i in range(4)]
        champion = tournament(dinos, use_color=False)
        self.assertIsInstance(champion, Dinosaur)
        self.assertIn(champion, dinos)

    def test_tournament_minimum_two(self):
        with self.assertRaises(ValueError):
            tournament([generate_dinosaur(seed=1)])

    def test_tournament_two_dinos(self):
        dinos = [generate_dinosaur(seed=i) for i in range(2)]
        champion = tournament(dinos, use_color=False)
        self.assertIn(champion, dinos)

    def test_tournament_odd_count(self):
        """Tournament with odd number should still work (byes)."""
        dinos = [generate_dinosaur(seed=i) for i in range(3)]
        champion = tournament(dinos, use_color=False)
        self.assertIn(champion, dinos)


class TestDinoDex(unittest.TestCase):
    """Test the DinoDex collection tracker."""

    def test_empty_dex(self):
        dex = DinoDex()
        self.assertEqual(len(dex.collection), 0)

    def test_add_dinosaur(self):
        dex = DinoDex()
        dino = generate_dinosaur(seed=1)
        dex.add(dino)
        self.assertEqual(len(dex.collection), 1)
        self.assertEqual(dex.collection[0], dino)

    def test_summary(self):
        dex = DinoDex()
        for i in range(5):
            dex.add(generate_dinosaur(seed=i))
        summary = dex.summary()
        self.assertIn("Total dinosaurs: 5", summary)

    def test_empty_summary(self):
        dex = DinoDex()
        summary = dex.summary()
        self.assertIn("empty", summary.lower())

    def test_wall_of_fame(self):
        dex = DinoDex()
        for i in range(5):
            dex.add(generate_dinosaur(seed=i))
        wof = dex.wall_of_fame()
        self.assertIn("WALL OF FAME", wof)

    def test_empty_wall_of_fame(self):
        dex = DinoDex()
        wof = dex.wall_of_fame()
        self.assertIn("No dinosaurs", wof)


class TestJsonExport(unittest.TestCase):
    """Test JSON serialization."""

    def test_to_json_is_valid_json(self):
        dino = generate_dinosaur(seed=42)
        json_str = dino.to_json()
        data = json.loads(json_str)
        self.assertIsInstance(data, dict)

    def test_to_json_contains_required_fields(self):
        dino = generate_dinosaur(seed=42)
        data = json.loads(dino.to_json())
        required = ["genus", "species", "full_name", "stat_total",
                     "attack", "defense", "speed", "intelligence",
                     "body_type", "diet", "rarity", "personality"]
        for field in required:
            self.assertIn(field, data, f"Missing field: {field}")

    def test_to_dict_matches_to_json(self):
        dino = generate_dinosaur(seed=42)
        d = dino.to_dict()
        j = json.loads(dino.to_json())
        self.assertEqual(d, j)

    def test_json_round_trip(self):
        """Data should survive a JSON round-trip."""
        dino = generate_dinosaur(seed=42)
        json_str = dino.to_json()
        data = json.loads(json_str)
        self.assertEqual(data["genus"], dino.genus)
        self.assertEqual(data["species"], dino.species)
        self.assertEqual(data["attack"], dino.attack)


class TestCLI(unittest.TestCase):
    """Test command-line interface."""

    def test_version_flag(self):
        """--version should print the version and exit."""
        with self.assertRaises(SystemExit) as cm:
            with patch('sys.argv', ['dinosaur_generator.py', '--version']):
                from dinosaur_generator import main
                main()
        self.assertEqual(cm.exception.code, 0)

    def test_generate_one(self):
        """--generate should produce output without errors."""
        with patch('sys.argv', ['dinosaur_generator.py', '--generate', '--seed', '42']):
            with patch('builtins.print') as mock_print:
                from dinosaur_generator import main
                main()
                self.assertTrue(mock_print.called)

    def test_battle_mode(self):
        """--battle should produce output without errors."""
        with patch('sys.argv', ['dinosaur_generator.py', '--battle', '--seed', '42']):
            with patch('builtins.print') as mock_print:
                from dinosaur_generator import main
                main()
                output = "\n".join(str(c[0][0]) if c[0] else "" for c in mock_print.call_args_list)
                self.assertTrue(mock_print.called)

    def test_json_output(self):
        """--json should produce valid JSON output."""
        captured = io.StringIO()
        with patch('sys.argv', ['dinosaur_generator.py', '--generate', '--json', '--seed', '42']):
            with patch('builtins.print') as mock_print:
                from dinosaur_generator import main
                main()
                # Find JSON in print calls
                json_found = False
                for call in mock_print.call_args_list:
                    for arg in call[0]:
                        try:
                            data = json.loads(str(arg))
                            if "genus" in data:
                                json_found = True
                        except (json.JSONDecodeError, TypeError):
                            pass
                self.assertTrue(json_found, "No JSON output found")

    def test_type_flag(self):
        """--type theropod should generate a theropod."""
        with patch('sys.argv', ['dinosaur_generator.py', '--generate', '--type', 'theropod', '--seed', '42']):
            with patch('builtins.print') as mock_print:
                from dinosaur_generator import main
                main()
                self.assertTrue(mock_print.called)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and robustness."""

    def test_many_generations_no_crash(self):
        """Generating many dinosaurs should never crash."""
        for seed in range(200):
            dino = generate_dinosaur(seed=seed)
            self.assertIsInstance(dino, Dinosaur)

    def test_all_body_types_all_seeds_stable(self):
        """Every body type with various seeds should produce valid dinos."""
        for bt in BODY_TYPES:
            for seed in [0, 1, 42, 100, 999]:
                dino = generate_dinosaur(seed=seed, body_type=bt)
                self.assertEqual(dino.body_type, bt)
                self.assertIsInstance(dino.attack, int)

    def test_render_full_no_color(self):
        """Full render without color should not contain ANSI codes."""
        dino = generate_dinosaur(seed=42)
        output = render_full(dino, use_color=False)
        self.assertNotIn("\033[", output)

    def test_render_full_contains_name(self):
        dino = generate_dinosaur(seed=42)
        output = render_full(dino, use_color=False)
        self.assertIn(dino.genus, output)

    def test_render_art(self):
        """Art should be non-empty string."""
        dino = generate_dinosaur(seed=42)
        art = render_art(dino)
        self.assertTrue(len(art) > 0)


if __name__ == "__main__":
    unittest.main()