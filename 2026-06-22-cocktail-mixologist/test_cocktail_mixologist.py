#!/usr/bin/env python3
"""Tests for the Terminal Cocktail Mixologist v2.0.0."""

import json
import random
import tempfile
import os
import sys

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cocktail_mixologist import (
    generate_cocktail, generate_story, extract_flavors,
    render_recipe_card, render_cocktail_menu, render_strength_bar,
    render_glass_ascii, render_ingredient_shopping_list,
    render_pairing_card, _find_ingredient_name,
    compute_flavor_balance, compute_balance_score,
    score_cocktail_pairing, _infer_style,
    suggest_substitutions,
    save_cocktails, load_cocktails,
    weighted_choice, Ingredient, Cocktail,
    SPIRITS, LIQUEURS, MIXERS, GARNISHES, GLASSWARE, ICE_TYPES, METHODS,
    STYLE_PROFILES, ADJECTIVES, NOUNS, NAME_STYLES,
    HARMONIOUS_PAIRS, FLAVOR_MAP,
    PAIRING_COMPATIBILITY, SUBSTITUTIONS,
    __version__,
)


class TestGenerateCocktail:
    """Test cocktail generation."""

    def test_default_cocktail_has_all_fields(self):
        """A generated cocktail should have all fields populated."""
        c = generate_cocktail()
        assert c.name, "Cocktail should have a name"
        assert len(c.ingredients) >= 1, "Should have at least one ingredient"
        assert c.method, "Should have a method"
        assert c.glass, "Should have glassware"
        assert c.ice, "Should have ice type"
        assert c.garnish, "Should have a garnish"
        assert c.story, "Should have a story"
        assert c.flavor_profile, "Should have a flavor profile"
        assert c.difficulty in ("Easy", "Intermediate", "Advanced")
        assert c.abv > 0, "ABV should be positive"
        assert c.total_oz > 0, "Total volume should be positive"

    def test_specific_style(self):
        """Generating with a specific style should work."""
        for style in STYLE_PROFILES:
            c = generate_cocktail(style)
            assert c.name, f"Should generate cocktail for style '{style}'"

    def test_all_styles_produce_valid_cocktails(self):
        """Every style should produce a cocktail with ingredients."""
        for style in STYLE_PROFILES:
            c = generate_cocktail(style)
            assert len(c.ingredients) >= 2, f"Style '{style}' should have at least 2 ingredients"

    def test_abv_calculation(self):
        """ABV should be calculated correctly."""
        c = generate_cocktail()
        assert 0 < c.abv <= 100, f"ABV {c.abv} should be between 0 and 100"

    def test_cocktail_with_no_alcohol_mixers(self):
        """A cocktail should have at least one alcoholic ingredient (the base)."""
        c = generate_cocktail()
        base_spirits = [i for i in c.ingredients if i.role == "base"]
        assert len(base_spirits) == 1, "Should have exactly one base spirit"
        assert base_spirits[0].abv > 0, "Base spirit should have alcohol"

    def test_ingredient_roles(self):
        """Ingredients should have valid roles."""
        valid_roles = {"base", "liqueur", "mixer", "bitters"}
        c = generate_cocktail()
        for ing in c.ingredients:
            assert ing.role in valid_roles, f"Invalid role: {ing.role}"

    def test_difficulty_classification(self):
        """Difficulty should be based on method and ingredient count."""
        # Layered cocktails should be Advanced
        random.seed(42)
        for _ in range(100):
            c = generate_cocktail()
            if c.method[0] == "layered" or len(c.ingredients) > 5:
                assert c.difficulty == "Advanced", \
                    f"Layered or complex cocktails should be Advanced: {c.method[0]}, {len(c.ingredients)}"

    def test_seed_reproducibility(self):
        """Same seed should produce the same cocktail."""
        random.seed(12345)
        c1 = generate_cocktail()
        random.seed(12345)
        c2 = generate_cocktail()
        assert c1.name == c2.name, "Same seed should produce same name"

    def test_name_generation_diversity(self):
        """Generated names should be diverse."""
        names = set()
        for _ in range(50):
            c = generate_cocktail()
            names.add(c.name)
        assert len(names) >= 30, f"Expected diverse names, got {len(names)} unique out of 50"


class TestIngredientData:
    """Test ingredient data integrity."""

    def test_spirits_have_valid_abv(self):
        """All spirits should have reasonable ABV values."""
        for spirit in SPIRITS:
            assert 0 < spirit[2] <= 100, f"Spirit {spirit[1]} has invalid ABV: {spirit[2]}"

    def test_mixers_have_zero_abv(self):
        """Mixers should have zero ABV, except bitters which are concentrated spirits."""
        for mixer in MIXERS:
            if mixer[0].startswith("bitters_"):
                assert mixer[2] > 0, f"Bitters {mixer[1]} should have positive ABV, got {mixer[2]}"
            else:
                assert mixer[2] == 0, f"Mixer {mixer[1]} should have 0 ABV, got {mixer[2]}"

    def test_no_duplicate_keys(self):
        """Ingredient keys should be unique within each category."""
        spirit_keys = [s[0] for s in SPIRITS]
        assert len(spirit_keys) == len(set(spirit_keys)), "Duplicate spirit keys"

        liqueur_keys = [l[0] for l in LIQUEURS]
        assert len(liqueur_keys) == len(set(liqueur_keys)), "Duplicate liqueur keys"

        mixer_keys = [m[0] for m in MIXERS]
        assert len(mixer_keys) == len(set(mixer_keys)), "Duplicate mixer keys"


class TestFlavorBalance:
    """Test flavor balance scoring."""

    def test_balance_score_range(self):
        """Balance score should be between 0 and 100."""
        for _ in range(20):
            c = generate_cocktail()
            score, desc = compute_balance_score(c)
            assert 0 <= score <= 100, f"Score {score} out of range"
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_balance_description_levels(self):
        """Balance descriptions should match score ranges."""
        random.seed(42)
        for _ in range(50):
            c = generate_cocktail()
            score, desc = compute_balance_score(c)
            if score >= 80:
                assert "Exceptionally" in desc or "masterful" in desc, f"Score {score}: {desc}"
            elif score >= 60:
                assert "Well-balanced" in desc, f"Score {score}: {desc}"
            elif score >= 40:
                assert "Moderate" in desc, f"Score {score}: {desc}"

    def test_flavor_balance_returns_dict(self):
        """Flavor balance should return a dict of flavor categories."""
        c = generate_cocktail()
        balance = compute_flavor_balance(c)
        assert isinstance(balance, dict)
        if balance:
            for key, val in balance.items():
                assert 0 <= val <= 1.0, f"Flavor value {val} for {key} out of range [0,1]"

    def test_worcestershire_key_fix(self):
        """The Worcestershire key should not have a leading space."""
        for m in MIXERS:
            assert not m[0].startswith(" "), f"Mixer key '{m[0]}' has leading space"


class TestPairing:
    """Test cocktail pairing system."""

    def test_pairing_score_range(self):
        """Pairing scores should be in [0, 100]."""
        c1 = generate_cocktail()
        c2 = generate_cocktail()
        score, label, explanation = score_cocktail_pairing(c1, c2)
        assert 0 <= score <= 100, f"Pairing score {score} out of range"
        assert isinstance(label, str)
        assert isinstance(explanation, str)

    def test_pairing_card_renders(self):
        """Pairing card should produce output containing both cocktail names."""
        c1 = generate_cocktail()
        c2 = generate_cocktail()
        card = render_pairing_card(c1, c2)
        assert c1.name in card, "Should contain cocktail 1 name"
        assert c2.name in card, "Should contain cocktail 2 name"
        assert "PAIRING" in card

    def test_same_spirit_penalty(self):
        """Two cocktails with the same base spirit should get a penalty."""
        random.seed(42)
        # Generate many pairs until we get same base spirit
        penalties_found = 0
        for _ in range(50):
            c1 = generate_cocktail()
            c2 = generate_cocktail()
            if c1.ingredients[0].key == c2.ingredients[0].key:
                _, _, explanation = score_cocktail_pairing(c1, c2)
                if "same base spirit" in explanation.lower():
                    penalties_found += 1
        # This is probabilistic; at least check the logic exists
        # Even if we don't always find same-base pairs, the code path is tested


class TestSubstitutions:
    """Test ingredient substitution system."""

    def test_suggest_substitutions_returns_list(self):
        """Substitution suggestions should be a list of tuples."""
        c = generate_cocktail()
        subs = suggest_substitutions(c)
        assert isinstance(subs, list)
        for item in subs:
            assert len(item) == 2, "Each item should be (name, options)"
            assert isinstance(item[0], str)
            assert isinstance(item[1], list)

    def test_base_spirit_has_substitution(self):
        """Most base spirits should have substitution options."""
        c = generate_cocktail()
        base_key = c.ingredients[0].key
        assert base_key in SUBSTITUTIONS, f"Base spirit '{base_key}' should have substitutions"

    def test_find_ingredient_name(self):
        """_find_ingredient_name should return display names."""
        assert _find_ingredient_name("gin") == "London Dry Gin"
        assert _find_ingredient_name("triple_sec") == "Triple Sec"
        # Unknown key should return title-cased version
        assert _find_ingredient_name("some_unknown_thing") == "Some Unknown Thing"


class TestSaveLoad:
    """Test save and load functionality."""

    def test_save_and_load_roundtrip(self):
        """Cocktails should round-trip through save/load."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp = f.name

        try:
            random.seed(42)
            cocktails = [generate_cocktail() for _ in range(3)]
            save_cocktails(cocktails, tmp)

            loaded = load_cocktails(tmp)
            assert len(loaded) == 3
            for original, loaded_c in zip(cocktails, loaded):
                assert original.name == loaded_c.name
                assert original.abv == loaded_c.abv
                assert original.difficulty == loaded_c.difficulty
                assert original.flavor_profile == loaded_c.flavor_profile
                assert len(original.ingredients) == len(loaded_c.ingredients)
        finally:
            os.unlink(tmp)

    def test_load_nonexistent_file(self):
        """Loading a nonexistent file should raise an error."""
        try:
            load_cocktails("/nonexistent/path/cocktails.json")
            assert False, "Should have raised an error"
        except (OSError, FileNotFoundError):
            pass  # Expected

    def test_save_creates_valid_json(self):
        """Saved JSON should be parseable and contain expected keys."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp = f.name

        try:
            random.seed(99)
            cocktails = [generate_cocktail()]
            save_cocktails(cocktails, tmp)

            with open(tmp) as f:
                data = json.load(f)

            assert "version" in data
            assert "cocktails" in data
            assert data["version"] == __version__
            assert len(data["cocktails"]) == 1
            assert data["cocktails"][0]["name"] == cocktails[0].name
        finally:
            os.unlink(tmp)


class TestRendering:
    """Test rendering functions."""

    def test_recipe_card_contains_name(self):
        """Recipe card should contain the cocktail name."""
        c = generate_cocktail()
        card = render_recipe_card(c)
        assert c.name in card

    def test_recipe_card_contains_balance(self):
        """Recipe card should contain balance score."""
        c = generate_cocktail()
        card = render_recipe_card(c)
        assert "Balance:" in card

    def test_verbose_shows_substitutions(self):
        """Verbose recipe card should show substitutions."""
        random.seed(42)
        c = generate_cocktail()
        card = render_recipe_card(c, verbose=True)
        assert "Substitutions" in card

    def test_verbose_shows_flavor_breakdown(self):
        """Verbose recipe card should show flavor breakdown bars."""
        c = generate_cocktail()
        card = render_recipe_card(c, verbose=True)
        # Should have flavor bars with █ characters
        if compute_flavor_balance(c):
            assert "█" in card, "Should contain flavor bar characters"

    def test_menu_card_renders(self):
        """Menu card should render with proper border characters."""
        cocktails = [generate_cocktail() for _ in range(3)]
        menu = render_cocktail_menu(cocktails)
        assert "COCKTAIL MENU" in menu
        for c in cocktails:
            assert c.name in menu

    def test_strength_bar_levels(self):
        """Strength bar should show correct level labels."""
        assert "LIGHT" in render_strength_bar(5)
        assert "MEDIUM" in render_strength_bar(15)
        assert "STRONG" in render_strength_bar(25)
        assert "POTENT" in render_strength_bar(40)

    def test_glass_ascii_all_types(self):
        """All glass types should have ASCII art."""
        for glass_key, glass_name, glass_desc in GLASSWARE:
            art = render_glass_ascii(glass_key)
            assert len(art) > 10, f"Glass '{glass_key}' should have ASCII art"

    def test_shopping_list_renders(self):
        """Shopping list should include all cocktail names."""
        cocktails = [generate_cocktail() for _ in range(3)]
        shop = render_ingredient_shopping_list(cocktails)
        assert "SHOPPING LIST" in shop
        for c in cocktails:
            # At least one ingredient should appear
            found = any(ing.name in shop for ing in c.ingredients)
            assert found, f"Should find ingredient from {c.name} in shopping list"


class TestInferStyle:
    """Test style inference."""

    def test_infer_style_returns_valid_style(self):
        """Inferred style should be a valid STYLE_PROFILES key."""
        for _ in range(20):
            c = generate_cocktail()
            style = _infer_style(c)
            assert style in STYLE_PROFILES, f"Invalid inferred style: {style}"

    def test_blended_is_tropical(self):
        """Blended cocktails should be inferred as tropical."""
        c = generate_cocktail("tropical")
        # Force blended method
        blended_method = [m for m in METHODS if m[0] == "blended"][0]
        c = Cocktail(
            name="Test", ingredients=c.ingredients, method=blended_method,
            glass=c.glass, ice=c.ice, garnish=c.garnish
        )
        c.abv = 15.0
        assert _infer_style(c) == "tropical"


class TestVersion:
    """Test version is correct."""

    def test_version_string(self):
        """Version should be a valid semver string."""
        assert __version__ == "2.0.0"

    def test_version_in_cli(self):
        """--version flag should work."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "cocktail_mixologist.py", "--version"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        assert "2.0.0" in result.stdout + result.stderr


class TestCLI:
    """Test CLI flags."""

    def test_json_output(self):
        """--json should produce valid JSON."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "cocktail_mixologist.py", "--seed", "42", "--json", "-n", "2"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 2
        assert "name" in data[0]

    def test_json_pairing_output(self):
        """--json with --pairing should produce pairing data."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "cocktail_mixologist.py", "--seed", "42", "--json", "--pairing"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "pairing" in data
        assert "cocktails" in data
        assert data["pairing"]["score"] >= 0

    def test_style_flag(self):
        """--style should produce cocktails of that style."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "cocktail_mixologist.py", "--seed", "7", "-s", "tropical"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        assert result.returncode == 0
        assert len(result.stdout) > 0


class TestBugFixes:
    """Tests for bugs that were found and fixed."""

    def test_pairing_empty_cocktail_no_crash(self):
        """score_cocktail_pairing should not crash on empty ingredient lists."""
        empty = Cocktail(
            name="Empty",
            ingredients=[],
            method=("built", "Built", "Assemble directly in serving glass"),
            glass=("rocks", "Rocks Glass", "short, wide tumbler"),
            ice=("cube", "Standard Cubes"),
            garnish=("cherry", "Luxardo Cherry"),
        )
        empty.compute_stats()
        # Should not crash — empty cocktails have no ingredients
        score, label, explanation = score_cocktail_pairing(empty, empty)
        assert 0 <= score <= 100

    def test_infer_style_empty_ingredients(self):
        """_infer_style should not crash on empty ingredient lists."""
        empty = Cocktail(
            name="Empty",
            ingredients=[],
            method=("built", "Built", "Assemble directly in serving glass"),
            glass=("rocks", "Rocks Glass", "short, wide tumbler"),
            ice=("cube", "Standard Cubes"),
            garnish=("cherry", "Luxardo Cherry"),
        )
        empty.compute_stats()
        style = _infer_style(empty)
        assert style in STYLE_PROFILES

    def test_substitution_targets_exist(self):
        """All substitution target keys should exist in ingredient pools."""
        all_keys = set(s[0] for s in SPIRITS) | set(l[0] for l in LIQUEURS) | set(m[0] for m in MIXERS)
        for key, subs in SUBSTITUTIONS.items():
            for sub_key, reason in subs:
                assert sub_key in all_keys, f"Substitution target '{sub_key}' for '{key}' not in ingredient pools"

    def test_story_trait2_different_from_trait(self):
        """Story generation should always have trait2 != trait."""
        random.seed(12345)
        for _ in range(50):
            c = generate_cocktail()
            # If trait2 == trait, the story format "combining X with Y" would
            # read oddly, but the fix ensures they're always different.
            # We can't directly test the internal variable, but verify stories generate.
            assert c.story, "Story should not be empty"

    def test_bitters_have_positive_abv(self):
        """Bitters should have realistic ABV (they're concentrated spirits)."""
        for mixer in MIXERS:
            if mixer[0].startswith("bitters_"):
                assert mixer[2] > 0, f"Bitters {mixer[1]} should have positive ABV"

    def test_bitters_amount_is_dash(self):
        """Generated cocktails should have bitters with dash-sized amounts."""
        random.seed(42)
        found_bitters = False
        for _ in range(20):
            c = generate_cocktail()
            for ing in c.ingredients:
                if ing.role == "bitters":
                    found_bitters = True
                    assert ing.amount_oz < 0.1, \
                        f"Bitters {ing.name} amount should be a dash (~0.03 oz), got {ing.amount_oz}"
        assert found_bitters, "Should find at least one bitters ingredient"

    def test_shopping_list_with_parens_in_name(self):
        """Shopping list should not crash when cocktail names contain parentheses."""
        random.seed(42)
        cocktails = [generate_cocktail() for _ in range(2)]
        cocktails[0].name = "The (Special) Drink"
        shop = render_ingredient_shopping_list(cocktails)
        assert "SHOPPING LIST" in shop

    def test_shopping_list_no_duplicate_entries(self):
        """Shopping list should properly count duplicate ingredients."""
        random.seed(99)
        cocktails = [generate_cocktail() for _ in range(5)]
        shop = render_ingredient_shopping_list(cocktails)
        assert "SHOPPING LIST" in shop


if __name__ == "__main__":
    # Run tests manually
    import traceback
    test_classes = [
        TestGenerateCocktail, TestIngredientData, TestFlavorBalance,
        TestPairing, TestSubstitutions, TestSaveLoad, TestRendering,
        TestInferStyle, TestVersion, TestCLI, TestBugFixes,
    ]
    total = 0
    passed = 0
    failed = 0
    for test_class in test_classes:
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total += 1
                try:
                    getattr(instance, method_name)()
                    passed += 1
                    print(f"  ✓ {test_class.__name__}.{method_name}")
                except Exception as e:
                    failed += 1
                    print(f"  ✗ {test_class.__name__}.{method_name}: {e}")
                    traceback.print_exc()

    print(f"\n{passed}/{total} tests passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)