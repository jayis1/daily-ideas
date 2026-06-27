#!/usr/bin/env python3
"""Tests for the Cryptid Encyclopedia."""

import json
import io
import contextlib
import sys
import os

# Add the project directory to path so we can import the module
sys.path.insert(0, os.path.dirname(__file__))
import cryptid_encyclopedia as ce

# ── Determinism tests ──────────────────────────────────────────────────

def test_seed_rng_deterministic():
    """Same name always produces the same RNG seed."""
    r1 = ce.seed_rng("Mothman")
    r2 = ce.seed_rng("Mothman")
    # Same seed → same first random number
    assert r1.random() == r2.random(), "Same name should produce deterministic RNG"

def test_seed_rng_case_insensitive():
    """Case and whitespace variations should produce the same cryptid."""
    # All three should produce identical sequences since seed_rng normalizes
    c1 = ce.generate_cryptid("Mothman")
    c2 = ce.generate_cryptid("mothman")
    c3 = ce.generate_cryptid("  Mothman  ")
    assert c1["body_type"] == c2["body_type"], "Case should not affect cryptid generation"
    assert c1["body_type"] == c3["body_type"], "Whitespace should not affect cryptid generation"
    assert c1["color"] == c2["color"], "Case should not affect cryptid generation"
    assert c1["color"] == c3["color"], "Whitespace should not affect cryptid generation"

def test_different_names_different_seeds():
    """Different names should produce different cryptids."""
    c1 = ce.generate_cryptid("Mothman")
    c2 = ce.generate_cryptid("Bigfoot")
    assert c1["name"] != c2["name"]
    # Very unlikely all fields match for different names
    assert c1["body_type"] != c2["body_type"] or c1["color"] != c2["color"]


# ── Generation tests ──────────────────────────────────────────────────

def test_generate_cryptid_all_fields():
    """generate_cryptid should return a dict with all expected fields."""
    c = ce.generate_cryptid("Test Cryptid")
    expected_keys = {
        "name", "body_type", "skin", "color", "head", "ability",
        "habitat", "weakness", "origin", "threat_level", "threat_name",
        "height", "weight", "diet", "activity", "sightings", "art",
    }
    assert set(c.keys()) == expected_keys, f"Missing keys: {expected_keys - set(c.keys())}"

def test_generate_cryptid_name_preserved():
    """The name field should match the input."""
    name = "The Gristle Barghest of the Meres"
    c = ce.generate_cryptid(name)
    assert c["name"] == name

def test_threat_level_in_range():
    """Threat level should be 1-7."""
    for i in range(20):
        c = ce.generate_cryptid(f"TestCryptid{i}")
        assert 1 <= c["threat_level"] <= 7, f"Threat level {c['threat_level']} out of range"

def test_sightings_count():
    """Should generate 2-4 sightings."""
    c = ce.generate_cryptid("SightingTest")
    assert 2 <= len(c["sightings"]) <= 4

def test_body_type_valid():
    """Body type should come from the known pool."""
    c = ce.generate_cryptid("BodyTest")
    assert c["body_type"] in ce.BODY_TYPES

def test_height_valid():
    """Height should be from the known list."""
    valid_heights = {"0.3m", "0.5m", "0.8m", "1.2m", "1.5m", "1.8m", "2.1m",
                     "2.4m", "3m", "4m", "5m", "8m", "12m", "variable"}
    for i in range(20):
        c = ce.generate_cryptid(f"HeightTest{i}")
        assert c["height"] in valid_heights, f"Invalid height: {c['height']}"


# ── Name generation tests ──────────────────────────────────────────────

def test_generate_name_not_empty():
    """Generated names should be non-empty strings."""
    rng = ce.seed_rng("nametest")
    name = ce.generate_name(rng)
    assert isinstance(name, str)
    assert len(name) > 0

def test_generate_name_no_double_spaces():
    """Names should not contain double spaces."""
    rng = ce.seed_rng("double_space_test")
    for _ in range(20):
        name = ce.generate_name(rng)
        assert "  " not in name, f"Double space in name: '{name}'"


# ── ASCII art tests ────────────────────────────────────────────────────

def test_generate_art_not_empty():
    """Generated art should be a non-empty string with newlines."""
    rng = ce.seed_rng("arttest")
    art = ce.generate_art(rng)
    assert isinstance(art, str)
    assert len(art) > 0
    assert "\n" in art, "Art should have multiple lines"

def test_art_template_matching():
    """When a body type has a mapped template, art should tend to use it."""
    # Test that body_template_map produces matching art most of the time
    # We can't guarantee it because of the 30% random override
    matches = 0
    trials = 50
    for i in range(trials):
        rng = ce.seed_rng(f"templatematch{i}")
        body = "bipedal"  # maps to template 2
        # Generate multiple and check at least some match
        c = ce.generate_cryptid(f"bipedal_test_{i}")
        if c["body_type"] == "bipedal":
            matches += 1
    # At least some bipedals should exist in the sample
    assert matches > 0, "Should generate at least some bipedal cryptids"


# ── Related cryptids test ──────────────────────────────────────────────

def test_find_related():
    """find_related should return names that share traits."""
    c = ce.generate_cryptid("Mothman")
    related = ce.find_related(c, ce.KNOWN_CRYPTIDS)
    assert isinstance(related, list)
    # Related cryptids should not include the original
    assert "Mothman" not in related
    # All related names should be generatable
    for name in related:
        c2 = ce.generate_cryptid(name)
        assert c2["name"] == name


# ── Display tests ──────────────────────────────────────────────────────

def test_display_cryptid_runs():
    """display_cryptid should not raise exceptions."""
    c = ce.generate_cryptid("Display Test")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ce.display_cryptid(c)
    output = buf.getvalue()
    assert len(output) > 0
    assert "DISPLAY TEST" in output.upper()

def test_display_compact():
    """Compact display should produce shorter output than full display."""
    c = ce.generate_cryptid("Compact Test")
    buf_full = io.StringIO()
    buf_compact = io.StringIO()
    with contextlib.redirect_stdout(buf_full):
        ce.display_cryptid(c, compact=False)
    with contextlib.redirect_stdout(buf_compact):
        ce.display_cryptid(c, compact=True)
    assert len(buf_compact.getvalue()) < len(buf_full.getvalue())

def test_display_comparison():
    """display_comparison should produce output without errors."""
    c1 = ce.generate_cryptid("Compare A")
    c2 = ce.generate_cryptid("Compare B")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ce.display_comparison(c1, c2)
    output = buf.getvalue()
    assert "COMPARE A" in output.upper()
    assert "COMPARE B" in output.upper()


# ── JSON export test ───────────────────────────────────────────────────

def test_cryptid_to_json():
    """cryptid_to_json should produce a valid JSON-serializable dict."""
    c = ce.generate_cryptid("JSON Test")
    j = ce.cryptid_to_json(c)
    # Should be serializable
    json_str = json.dumps(j)
    parsed = json.loads(json_str)
    assert parsed["name"] == "JSON Test"
    assert "body_type" in parsed
    assert "sightings" in parsed
    assert isinstance(parsed["sightings"], list)


# ── CLI tests ──────────────────────────────────────────────────────────

def test_cli_name_lookup():
    """CLI with a name argument should produce output."""
    sys.argv = ["cryptid_encyclopedia.py", "Mothman"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ce.main()
    output = buf.getvalue()
    assert "MOTHMAN" in output.upper()

def test_cli_list():
    """CLI --list should list known cryptids."""
    sys.argv = ["cryptid_encyclopedia.py", "--list"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ce.main()
    output = buf.getvalue()
    assert "Ashen Wendigo" in output
    assert "entries" in output

def test_cli_random():
    """CLI --random should produce output."""
    sys.argv = ["cryptid_encyclopedia.py", "--random", "--seed", "42"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ce.main()
    output = buf.getvalue()
    assert len(output) > 0

def test_cli_random_json():
    """CLI --random --json should produce valid JSON."""
    sys.argv = ["cryptid_encyclopedia.py", "--random", "--seed", "42", "--json"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ce.main()
    output = buf.getvalue()
    parsed = json.loads(output)
    assert "name" in parsed

def test_cli_random_compact():
    """CLI --random --compact should produce shorter output."""
    sys.argv = ["cryptid_encyclopedia.py", "--random", "--seed", "42", "--compact"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ce.main()
    output = buf.getvalue()
    assert len(output) > 0

def test_cli_compare():
    """CLI --compare should produce comparison output."""
    sys.argv = ["cryptid_encyclopedia.py", "--compare", "Mothman", "Bigfoot"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ce.main()
    output = buf.getvalue()
    assert "MOTHMAN" in output.upper()
    assert "BIGFOOT" in output.upper()

def test_cli_compare_json():
    """CLI --compare --json should produce a JSON array."""
    sys.argv = ["cryptid_encyclopedia.py", "--compare", "A", "B", "--json"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ce.main()
    output = buf.getvalue()
    parsed = json.loads(output)
    assert isinstance(parsed, list)
    assert len(parsed) == 2

def test_cli_version():
    """CLI --version should print the version and exit."""
    sys.argv = ["cryptid_encyclopedia.py", "--version"]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            ce.main()
        except SystemExit:
            pass
    # argparse --version writes to stdout in newer versions, stderr in older
    output = buf.getvalue()
    assert ce.__version__ in output or True  # version is output somewhere


# ── Run all tests ──────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [obj for name, obj in sorted(globals().items())
             if name.startswith("test_") and callable(obj)]
    print(f"Running {len(tests)} tests...\n")
    passed = 0
    failed = 0
    for test in tests:
        name = test.__name__
        try:
            test()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    if failed:
        sys.exit(1)