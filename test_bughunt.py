#!/usr/bin/env python3
"""
Bug hunt test suite — tests that verify each bug was found and fixed.

Run with: python3 test_bughunt.py
"""

import sys
import os

# Add project directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '2026-06-12-ascii-dungeon-generator'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '2026-06-12-rune-cipher'))

from dungeon_generator import (
    DungeonConfig, DungeonGenerator, validate_config,
    Room, WALL, FLOOR, CORRIDOR, STAIRS_UP, STAIRS_DOWN
)
from rune_cipher import (
    text_to_runes, runes_to_text, caesar_encrypt, caesar_decrypt,
    vigenere_encrypt, vigenere_decrypt, atbash_encrypt, rot13_encrypt,
    substitution_encrypt, substitution_decrypt, affine_encrypt, affine_decrypt,
    xor_encrypt, xor_decrypt, generate_keyword_key, random_substitution_key,
    frequency_score, bigram_score, combined_score, crack_caesar, crack_vigenere,
    crack_affine, analyze_frequency, format_analysis, AFFINE_VALID_A
)

passed = 0
failed = 0
errors = []

def run_test(name, func):
    global passed, failed, errors
    try:
        func()
        print(f"  ✓ {name}")
        passed += 1
    except AssertionError as e:
        print(f"  ✗ {name}: {e}")
        failed += 1
        errors.append((name, str(e)))
    except Exception as e:
        print(f"  ✗ {name}: EXCEPTION: {e}")
        failed += 1
        errors.append((name, str(e)))


# ── Dungeon Generator Bug Tests ────────────────────────────────────────────────

def test_bug1_small_room_no_crash():
    """Bug 1 (CRITICAL): min_room_size=2 caused ValueError in randint.
    After fix, generation should succeed without crash."""
    config = DungeonConfig(seed=42, min_room_size=2, max_room_size=3, 
                           width=40, height=20, min_rooms=3, max_rooms=5)
    gen = DungeonGenerator(config)
    gen.generate()  # Should not crash
    assert len(gen.rooms) >= 2, f"Expected >= 2 rooms, got {len(gen.rooms)}"

def test_bug1_small_room_entities_placed():
    """Bug 1: Even with small rooms, entities should still be placed in larger rooms."""
    config = DungeonConfig(seed=42, min_room_size=3, max_room_size=8,
                           width=60, height=30)
    gen = DungeonGenerator(config)
    gen.generate()
    # There should be monsters and treasures
    monsters = [e for e in gen.entities if e.kind == "monster"]
    treasures = [e for e in gen.entities if e.kind == "treasure"]
    assert len(monsters) > 0, "Expected at least one monster"
    assert len(treasures) > 0, "Expected at least one treasure"

def test_bug1_entities_on_walkable_tiles():
    """Bug 1 fix: All entities should be on walkable tiles (FLOOR or CORRIDOR)."""
    for seed in range(20):
        config = DungeonConfig(seed=seed, width=60, height=30)
        gen = DungeonGenerator(config)
        gen.generate()
        for e in gen.entities:
            tile = gen.grid[e.y][e.x]
            assert tile in (FLOOR, CORRIDOR), \
                f"Seed {seed}: {e.kind} '{e.description}' at ({e.x},{e.y}) on {tile}"

def test_bug2_invalid_theme_rejected():
    """Bug 2: validate_config should reject invalid themes."""
    errors = validate_config(DungeonConfig(theme="invalid"))
    assert len(errors) > 0, f"Expected error for invalid theme, got: {errors}"
    assert "theme" in errors[0].lower() or "Invalid" in errors[0], \
        f"Expected theme error, got: {errors[0]}"

def test_bug2_valid_themes_accepted():
    """Bug 2: validate_config should accept all valid themes."""
    for theme in ["standard", "crypt", "inferno", "forest", "aquatic"]:
        errors = validate_config(DungeonConfig(theme=theme))
        theme_errors = [e for e in errors if "theme" in e.lower() or "Invalid" in e]
        assert len(theme_errors) == 0, f"Theme '{theme}' should be valid, got: {theme_errors}"

def test_bug3_room_size_too_large():
    """Bug 3: validate_config should reject room sizes too large for the map."""
    errors = validate_config(DungeonConfig(width=10, height=10, max_room_size=15))
    assert len(errors) > 0, f"Expected error for oversized room, got: {errors}"

def test_bug4_generate_raises_on_failure():
    """Bug 4: generate() should raise RuntimeError instead of silently returning
    an invalid dungeon."""
    config = DungeonConfig(seed=9999, width=10, height=10, min_rooms=8, max_rooms=15)
    gen = DungeonGenerator(config)
    try:
        gen.generate()
        # If it succeeds, that's fine (unlikely with these params)
        assert len(gen.rooms) >= 2, "Should have at least 2 rooms"
    except RuntimeError:
        pass  # Expected: couldn't generate a valid dungeon

def test_bug4_normal_generation_works():
    """Bug 4 fix: Normal generation should still work."""
    config = DungeonConfig(seed=42)
    gen = DungeonGenerator(config)
    gen.generate()
    assert len(gen.rooms) >= 2, "Normal generation should produce rooms"

def test_bug5_connectivity_preserved():
    """All dungeons should be connected after generation."""
    for seed in range(10):
        config = DungeonConfig(seed=seed, width=50, height=25)
        gen = DungeonGenerator(config)
        gen.generate()
        assert gen._check_connectivity(), f"Seed {seed}: dungeon should be connected"


# ── Rune Cipher Bug Tests ──────────────────────────────────────────────────────

def test_bug_r3_crack_vigenere_short_text():
    """Bug R3: crack_vigenere should return '<too-short>' marker, not original
    ciphertext disguised as a decryption."""
    result = crack_vigenere("ab")
    assert len(result) > 0, "Should return at least one result"
    assert result[0][0] == "<too-short>", \
        f"Expected '<too-short>' marker, got '{result[0][0]}'"

def test_bug_r6_analyze_frequency_single_letter():
    """Bug R6: analyze_frequency should handle single-letter text without
    ZeroDivisionError in IoC calculation."""
    result = analyze_frequency("a")
    assert "index_of_coincidence" in result, "Should have IoC"
    assert result["index_of_coincidence"] == 0.0, \
        f"IoC for single letter should be 0.0, got {result['index_of_coincidence']}"

def test_bug_r6_analyze_frequency_two_same_letters():
    """Bug R6: IoC for 'aa' should be 1.0 (all letters same)."""
    result = analyze_frequency("aa")
    assert result["index_of_coincidence"] == 1.0, \
        f"IoC for 'aa' should be 1.0, got {result['index_of_coincidence']}"

def test_bug_r6_analyze_frequency_empty():
    """Bug R6: analyze_frequency should handle empty text gracefully."""
    result = analyze_frequency("")
    assert "error" in result, "Empty text should return error"

def test_bug_r6_analyze_frequency_no_letters():
    """Bug R6: analyze_frequency should handle text with no letters."""
    result = analyze_frequency("123!@#")
    assert "error" in result, "Non-letter text should return error"

def test_bug_r5_combined_score_punctuation():
    """Bug R5 fix: combined_score should match words with attached punctuation."""
    # Before fix: "mat." wouldn't match "mat" in common_words
    text_no_punct = "the cat sat on the mat"
    text_with_punct = "the cat sat on the mat."
    score_no_punct = combined_score(text_no_punct)
    score_with_punct = combined_score(text_with_punct)
    # Scores should be similar (within 30 points) since punctuation is stripped
    assert abs(score_no_punct - score_with_punct) < 30, \
        f"Punctuated text score ({score_with_punct:.1f}) should be close to non-punctuated ({score_no_punct:.1f})"

def test_caesar_crack_with_punctuation():
    """crack_caesar should work well with punctuated text."""
    plaintext = "the cat sat on the mat."
    ciphertext = caesar_encrypt(plaintext, 7)
    candidates = crack_caesar(ciphertext)
    # Best candidate should be close to original
    assert candidates[0][1].replace(".", "").replace(" ", "") == \
           plaintext.replace(".", "").replace(" ", ""), \
        f"Expected to crack '{plaintext}', got '{candidates[0][1]}'"

def test_xor_round_trip_unicode():
    """XOR round-trip should work with unicode characters."""
    for text in ["café", "naïve", "hello"]:
        enc = xor_encrypt(text, "key")
        dec = xor_decrypt(enc, "key")
        assert dec == text, f"XOR round-trip failed for '{text}'"

def test_xor_round_trip_special_chars():
    """XOR round-trip should work with special characters."""
    for text in ["hello!@#world", "spaces and tabs\there", "newline\nhere"]:
        enc = xor_encrypt(text, "key")
        dec = xor_decrypt(enc, "key")
        assert dec == text, f"XOR round-trip failed for: {repr(text)}"

def test_all_cipher_round_trips():
    """All ciphers should round-trip correctly."""
    plaintext = "hello world"
    
    # Caesar
    for key in [0, 1, 13, 25]:
        assert caesar_decrypt(caesar_encrypt(plaintext, key), key) == plaintext
    
    # Vigenère
    for key in ["a", "abc", "secret"]:
        assert vigenere_decrypt(vigenere_encrypt(plaintext, key), key) == plaintext
    
    # Atbash (self-inverse)
    assert atbash_encrypt(atbash_encrypt(plaintext)) == plaintext
    
    # ROT13 (self-inverse)
    assert rot13_encrypt(rot13_encrypt(plaintext)) == plaintext
    
    # Substitution
    key = random_substitution_key()
    assert substitution_decrypt(substitution_encrypt(plaintext, key), key) == plaintext
    
    # Affine
    for a in AFFINE_VALID_A[:3]:
        for b in [0, 5, 13]:
            assert affine_decrypt(affine_encrypt(plaintext, a, b), a, b) == plaintext

def test_rune_round_trip():
    """Text → runes → text should be identity."""
    for text in ["hello world", "the quick brown fox", "abcdefghijklmnopqrstuvwxyz"]:
        assert runes_to_text(text_to_runes(text)) == text

def test_dungeon_reproducibility():
    """Same seed should produce identical dungeons."""
    for seed in [1, 42, 100]:
        gen1 = DungeonGenerator(DungeonConfig(seed=seed))
        gen1.generate()
        map1 = gen1.render()
        
        gen2 = DungeonGenerator(DungeonConfig(seed=seed))
        gen2.generate()
        map2 = gen2.render()
        
        assert map1 == map2, f"Seed {seed}: same seed should produce same map"


# ── Run all tests ───────────────────────────────────────────────────────────────

print("=" * 60)
print("BUG HUNT TEST SUITE")
print("=" * 60)

print("\n── Dungeon Generator Bug Tests ──")
run_test("Bug 1: Small rooms don't crash", test_bug1_small_room_no_crash)
run_test("Bug 1: Entities placed in normal rooms", test_bug1_small_room_entities_placed)
run_test("Bug 1: All entities on walkable tiles", test_bug1_entities_on_walkable_tiles)
run_test("Bug 2: Invalid theme rejected", test_bug2_invalid_theme_rejected)
run_test("Bug 2: Valid themes accepted", test_bug2_valid_themes_accepted)
run_test("Bug 3: Oversized rooms rejected", test_bug3_room_size_too_large)
run_test("Bug 4: Generate raises RuntimeError on failure", test_bug4_generate_raises_on_failure)
run_test("Bug 4: Normal generation works", test_bug4_normal_generation_works)
run_test("Bug 5: Connectivity preserved", test_bug5_connectivity_preserved)

print("\n── Rune Cipher Bug Tests ──")
run_test("Bug R3: crack_vigenere short text marker", test_bug_r3_crack_vigenere_short_text)
run_test("Bug R6: analyze_frequency single letter", test_bug_r6_analyze_frequency_single_letter)
run_test("Bug R6: analyze_frequency two same letters", test_bug_r6_analyze_frequency_two_same_letters)
run_test("Bug R6: analyze_frequency empty", test_bug_r6_analyze_frequency_empty)
run_test("Bug R6: analyze_frequency no letters", test_bug_r6_analyze_frequency_no_letters)
run_test("Bug R5: combined_score handles punctuation", test_bug_r5_combined_score_punctuation)
run_test("Caesar crack with punctuation", test_caesar_crack_with_punctuation)
run_test("XOR round-trip unicode", test_xor_round_trip_unicode)
run_test("XOR round-trip special chars", test_xor_round_trip_special_chars)
run_test("All cipher round-trips", test_all_cipher_round_trips)
run_test("Rune round-trip", test_rune_round_trip)
run_test("Dungeon reproducibility", test_dungeon_reproducibility)

print(f"\n{'═' * 60}")
print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")

if errors:
    print(f"\n  Failed tests:")
    for name, err in errors:
        print(f"    - {name}: {err}")

sys.exit(0 if failed == 0 else 1)