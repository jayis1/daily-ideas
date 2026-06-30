#!/usr/bin/env python3
"""Tests for Perfume Alchemist — procedural perfume generator."""

import json
import os
import random
import subprocess
import sys
import tempfile

# Add project directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from perfume_alchemist import (
    TOP_NOTES,
    HEART_NOTES,
    BASE_NOTES,
    FAMILIES,
    MOODS,
    SEASONS,
    Note,
    Perfume,
    generate_name,
    generate_perfume,
    generate_collection,
    compare_perfumes,
    search_notes,
    _dedupe_notes,
    HARMONY_PAIRS,
    CONCENTRATION_LONGEVITY,
    CONCENTRATION_SILLAGE,
)


# ─── Data Integrity Tests ────────────────────────────────────────────────────

def test_note_pools_are_populated():
    """Each note pool should have at least 10 entries for variety."""
    assert len(TOP_NOTES) >= 10, f"TOP_NOTES has only {len(TOP_NOTES)} entries"
    assert len(HEART_NOTES) >= 10, f"HEART_NOTES has only {len(HEART_NOTES)} entries"
    assert len(BASE_NOTES) >= 10, f"BASE_NOTES has only {len(BASE_NOTES)} entries"


def test_note_tuples_are_valid():
    """Every note tuple must have exactly 3 elements: (name, category, description)."""
    for pool_name, pool in [("TOP", TOP_NOTES), ("HEART", HEART_NOTES), ("BASE", BASE_NOTES)]:
        for entry in pool:
            assert len(entry) == 3, f"{pool_name} note {entry} has {len(entry)} fields, expected 3"
            assert isinstance(entry[0], str) and entry[0], f"{pool_name} note has empty name: {entry}"
            assert isinstance(entry[1], str) and entry[1], f"{pool_name} note has empty category: {entry}"
            assert isinstance(entry[2], str) and entry[2], f"{pool_name} note has empty description: {entry}"


def test_no_duplicate_note_names_within_pool():
    """Note names should be unique within each pool."""
    for pool_name, pool in [("TOP", TOP_NOTES), ("HEART", HEART_NOTES), ("BASE", BASE_NOTES)]:
        names = [entry[0] for entry in pool]
        duplicates = [n for n in names if names.count(n) > 1]
        assert not duplicates, f"{pool_name} has duplicate names: {set(duplicates)}"


def test_families_are_valid():
    """Families should be non-empty tuples of (name, description)."""
    assert len(FAMILIES) >= 5, "Need at least 5 families"
    for name, desc in FAMILIES:
        assert isinstance(name, str) and name, f"Family has empty name: {name}"
        assert isinstance(desc, str) and desc, f"Family {name} has empty description"


def test_moods_are_valid():
    """Moods should be unique, non-empty strings."""
    assert len(MOODS) >= 5, "Need at least 5 moods"
    assert len(set(MOODS)) == len(MOODS), "Moods should be unique"
    for m in MOODS:
        assert isinstance(m, str) and m, f"Mood is empty"


def test_seasons_are_valid():
    """Seasons should be unique, non-empty strings."""
    assert len(SEASONS) >= 4, "Need at least 4 seasons"
    assert len(set(SEASONS)) == len(SEASONS), "Seasons should be unique"


def test_concentration_mappings_are_valid():
    """Every concentration should have matching longevity and sillage options."""
    for conc in CONCENTRATION_LONGEVITY:
        assert conc in CONCENTRATION_SILLAGE, f"Missing sillage mapping for {conc}"
    for conc in CONCENTRATION_SILLAGE:
        assert conc in CONCENTRATION_LONGEVITY, f"Missing longevity mapping for {conc}"


# ─── Generation Tests ─────────────────────────────────────────────────────────

def test_generate_perfume_basic():
    """generate_perfume should return a valid Perfume object."""
    p = generate_perfume()
    assert isinstance(p, Perfume)
    assert p.name
    assert p.family
    assert p.mood in MOODS
    assert p.season in SEASONS
    assert p.origin
    assert p.concentration
    assert p.longevity
    assert p.sillage
    assert p.description
    assert len(p.top_notes) >= 2
    assert len(p.heart_notes) >= 2
    assert len(p.base_notes) >= 2


def test_generate_perfume_with_family():
    """Specifying a family should produce a perfume of that family."""
    p = generate_perfume(family="Chypre")
    assert p.family == "Chypre"


def test_generate_perfume_with_partial_family_match():
    """Partial family names should match (case-insensitive)."""
    p = generate_perfume(family="oriental")
    assert p.family == "Oriental / Amber"


def test_generate_perfume_with_mood():
    """Specifying a mood should produce a perfume with that mood."""
    p = generate_perfume(mood="serene")
    assert p.mood == "serene"


def test_generate_perfume_with_season():
    """Specifying a season should produce a perfume with that season."""
    p = generate_perfume(season="high summer")
    assert p.season == "high summer"


def test_generate_perfume_all_params():
    """All parameters together should work."""
    p = generate_perfume(family="Floral", mood="sensual", season="monsoon dusk")
    assert p.family == "Floral"
    assert p.mood == "sensual"
    assert p.season == "monsoon dusk"


def test_generate_perfume_no_duplicate_notes():
    """No note name should appear more than once across the entire perfume."""
    p = generate_perfume()
    all_names = (
        [n.name for n in p.top_notes]
        + [n.name for n in p.heart_notes]
        + [n.name for n in p.base_notes]
    )
    assert len(all_names) == len(set(all_names)), f"Duplicate notes found: {all_names}"


def test_concentration_longevity_consistency():
    """Concentration should be consistent with longevity ranges."""
    for _ in range(20):  # Sample multiple times due to randomness
        p = generate_perfume()
        conc = p.concentration
        longevity = p.longevity
        assert longevity in CONCENTRATION_LONGEVITY[conc], (
            f"Inconsistent: {conc} with longevity {longevity}"
        )


def test_concentration_sillage_consistency():
    """Concentration should be consistent with sillage options."""
    for _ in range(20):
        p = generate_perfume()
        conc = p.concentration
        sillage = p.sillage
        assert sillage in CONCENTRATION_SILLAGE[conc], (
            f"Inconsistent: {conc} with sillage {sillage}"
        )


# ─── Name Generation Tests ────────────────────────────────────────────────────

def test_generate_name_returns_string():
    """generate_name should return a non-empty string."""
    name = generate_name()
    assert isinstance(name, str)
    assert len(name) > 0


def test_generate_name_variety():
    """Running generate_name many times should produce variety."""
    random.seed(42)
    names = {generate_name() for _ in range(50)}
    assert len(names) > 5, "Name generation is not varied enough"


# ─── Collection Tests ─────────────────────────────────────────────────────────

def test_generate_collection_size():
    """generate_collection should return the requested number of perfumes."""
    coll = generate_collection(3)
    assert len(coll) == 3
    for p in coll:
        assert isinstance(p, Perfume)


def test_generate_collection_varied_families():
    """Collection perfumes should have varied families."""
    coll = generate_collection(5)
    families = {p.family for p in coll}
    assert len(families) >= 3, f"Expected at least 3 different families, got {families}"


# ─── Report & Display Tests ───────────────────────────────────────────────────

def test_full_report_is_nonempty():
    """full_report should produce a non-empty string with key sections."""
    p = generate_perfume()
    report = p.full_report()
    assert isinstance(report, str)
    assert len(report) > 100
    assert "Note Pyramid" in report
    assert "Scent Profile" in report
    assert "Tasting Notes" in report
    assert "Impressions" in report
    assert "Harmony" in report


def test_note_pyramid_format():
    """Note pyramid should contain all note names and section headers."""
    p = generate_perfume()
    pyramid = p.note_pyramid()
    assert "TOP" in pyramid
    assert "HEART" in pyramid
    assert "BASE" in pyramid
    for note in p.top_notes:
        assert note.name in pyramid
    for note in p.heart_notes:
        assert note.name in pyramid
    for note in p.base_notes:
        assert note.name in pyramid


def test_scent_profile_bar():
    """Scent profile should contain percentages and bars."""
    p = generate_perfume()
    profile = p.scent_profile_bar()
    assert "%" in profile
    assert "█" in profile


def test_harmony_score_format():
    """Harmony score should be a formatted string with rating and percentage."""
    p = generate_perfume()
    score = p.harmony_score()
    assert "%" in score
    # Should contain one of the rating labels
    assert any(label in score for label in ["Harmonious", "Balanced", "Distinctive", "Contrarian"])


# ─── Comparison Tests ──────────────────────────────────────────────────────────

def test_compare_perfumes():
    """compare_perfumes should produce a formatted comparison string."""
    p1 = generate_perfume()
    p2 = generate_perfume()
    result = compare_perfumes(p1, p2)
    assert "FRAGRANCE DUEL" in result
    assert p1.name in result
    assert p2.name in result
    assert "Top Notes" in result
    assert "Heart Notes" in result
    assert "Base Notes" in result


# ─── Search Tests ─────────────────────────────────────────────────────────────

def test_search_notes_by_name():
    """Searching for 'oud' should find the oud note."""
    result = search_notes("oud")
    assert "oud" in result
    assert "Heart" in result  # oud is a heart note


def test_search_notes_by_category():
    """Searching for 'citrus' should find citrus category notes."""
    result = search_notes("citrus")
    assert "citrus" in result.lower()
    # Should find at least bergamot, lemon zest, grapefruit, petitgrain, yuzu
    assert "bergamot" in result.lower() or "lemon zest" in result.lower()


def test_search_notes_no_results():
    """Searching for nonsense should return a helpful message."""
    result = search_notes("xyznonexistent123")
    assert "No notes found" in result


# ─── Dedupe Tests ─────────────────────────────────────────────────────────────

def test_dedupe_notes_removes_duplicates():
    """_dedupe_notes should remove duplicate note names."""
    # Create two notes with the same name
    notes = [Note("bergamot", "citrus", "test"), Note("bergamot", "citrus", "test")]
    seen = set()
    result = _dedupe_notes(notes, TOP_NOTES, seen)
    names = [n.name for n in result]
    assert len(names) == len(set(names)), f"Duplicates found: {names}"


# ─── Serialization Tests ──────────────────────────────────────────────────────

def test_to_dict_is_serializable():
    """Perfume.to_dict should produce a JSON-serializable dictionary."""
    p = generate_perfume()
    d = p.to_dict()
    # Should be serializable to JSON without errors
    json_str = json.dumps(d, ensure_ascii=False)
    assert len(json_str) > 100
    parsed = json.loads(json_str)
    assert parsed["name"] == p.name
    assert parsed["family"] == p.family
    assert len(parsed["top_notes"]) == len(p.top_notes)


def test_note_to_dict():
    """Note.to_dict should produce a valid dictionary."""
    n = Note("bergamot", "citrus", "bright citrus")
    d = n.to_dict()
    assert d == {"name": "bergamot", "category": "citrus", "description": "bright citrus"}


# ─── CLI Tests ─────────────────────────────────────────────────────────────────

def test_cli_version():
    """--version flag should print version and exit."""
    result = subprocess.run(
        [sys.executable, "perfume_alchemist.py", "--version"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__),
    )
    assert result.returncode == 0
    assert "1.1.0" in result.stdout or "1.1.0" in result.stderr


def test_cli_help():
    """--help flag should print help text and exit."""
    result = subprocess.run(
        [sys.executable, "perfume_alchemist.py", "--help"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__),
    )
    assert result.returncode == 0
    assert "Perfume Alchemist" in result.stdout
    assert "--generate" in result.stdout
    assert "--family" in result.stdout
    assert "--mood" in result.stdout
    assert "--version" in result.stdout


def test_cli_generate_single():
    """--generate should produce perfume output."""
    result = subprocess.run(
        [sys.executable, "perfume_alchemist.py", "--generate", "--seed", "123"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__),
    )
    assert result.returncode == 0
    assert "✦" in result.stdout
    assert "Note Pyramid" in result.stdout


def test_cli_list_families():
    """--list-families should list all families."""
    result = subprocess.run(
        [sys.executable, "perfume_alchemist.py", "--list-families"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__),
    )
    assert result.returncode == 0
    assert "Chypre" in result.stdout
    assert "Floral" in result.stdout


def test_cli_search():
    """--search should find matching notes."""
    result = subprocess.run(
        [sys.executable, "perfume_alchemist.py", "--search", "oud"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__),
    )
    assert result.returncode == 0
    assert "oud" in result.stdout


def test_cli_export_json():
    """--export should write valid JSON to a file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        tmpfile = f.name
    try:
        result = subprocess.run(
            [sys.executable, "perfume_alchemist.py", "--generate", "--seed", "7", "--export", tmpfile],
            capture_output=True, text=True, cwd=os.path.dirname(__file__),
        )
        assert result.returncode == 0
        with open(tmpfile, "r") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"]
        assert "top_notes" in data[0]
    finally:
        os.unlink(tmpfile)


def test_cli_season_flag():
    """--season should set the perfume's season."""
    result = subprocess.run(
        [sys.executable, "perfume_alchemist.py", "--generate", "--season", "high summer", "--seed", "5"],
        capture_output=True, text=True, cwd=os.path.dirname(__file__),
    )
    assert result.returncode == 0
    assert "High summer" in result.stdout


if __name__ == "__main__":
    # Run all tests with verbose output
    import traceback
    test_funcs = [obj for name, obj in sorted(globals().items())
                  if name.startswith("test_") and callable(obj)]
    passed = 0
    failed = 0
    for func in test_funcs:
        try:
            func()
            print(f"  ✓ {func.__name__}")
            passed += 1
        except Exception:
            print(f"  ✗ {func.__name__}")
            traceback.print_exc()
            failed += 1
    print(f"\n  {passed} passed, {failed} failed out of {len(test_funcs)} tests")
    sys.exit(1 if failed else 0)