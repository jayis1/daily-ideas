#!/usr/bin/env python3
"""Tests for Markov Chain Haiku Generator."""

import random
import sys
import os

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from markov_haiku import (
    count_syllables,
    syllable_count_phrase,
    MarkovChain,
    HaikuGenerator,
    DEFAULT_CORPUS,
)


# ─── Syllable counting tests ─────────────────────────────────────────────────

def test_syllable_basic():
    """Basic syllable count tests."""
    assert count_syllables("a") == 1
    assert count_syllables("the") == 1
    assert count_syllables("cat") == 1
    assert count_syllables("hello") == 2
    assert count_syllables("beautiful") == 4
    assert count_syllables("mountain") == 2
    assert count_syllables("water") == 2
    assert count_syllables("butterfly") == 4
    assert count_syllables("haiku") == 2


def test_syllable_single_vowel():
    """Single-vowel words."""
    assert count_syllables("i") == 1
    assert count_syllables("a") == 1
    assert count_syllables("o") == 1


def test_syllable_silent_e():
    """Words with silent e."""
    assert count_syllables("make") == 1
    assert count_syllables("time") == 1
    assert count_syllables("like") == 1


def test_syllable_exceptions():
    """Exception table words."""
    assert count_syllables("fire") == 1
    assert count_syllables("are") == 1
    assert count_syllables("some") == 1


def test_syllable_nature_words():
    """Nature/poetry words that are common in haikus."""
    assert count_syllables("cherry") == 2
    assert count_syllables("blossom") == 2
    assert count_syllables("petals") == 2
    assert count_syllables("morning") == 2
    assert count_syllables("evening") == 3
    assert count_syllables("moonlight") == 2
    assert count_syllables("sunlight") == 2
    assert count_syllables("starlight") == 2
    assert count_syllables("twilight") == 2


def test_syllable_ending_ed():
    """Words ending in -ed."""
    assert count_syllables("walked") == 1
    assert count_syllables("wanted") == 2
    assert count_syllables("started") == 2


def test_syllable_count_phrase():
    """Phrase-level syllable counting."""
    assert syllable_count_phrase("the cat") == 2
    assert syllable_count_phrase("cherry blossom") == 4
    assert syllable_count_phrase("mountain river") == 4


def test_syllable_empty():
    """Edge cases with empty input."""
    assert count_syllables("") == 0
    assert count_syllables("123") == 0
    assert syllable_count_phrase("") == 0


# ─── Markov Chain tests ────────────────────────────────────────────────────────

def test_markov_train_basic():
    """Basic training and generation."""
    chain = MarkovChain(order=1)
    chain.train("the cat sat on the mat the cat ate the rat")
    assert len(chain.chain) > 0
    assert chain.all_words


def test_markov_generate():
    """Generation produces words from training data."""
    chain = MarkovChain(order=1)
    chain.train("the cat sat on the mat the cat ate the rat")
    result = chain.generate(max_words=5)
    assert isinstance(result, list)
    assert all(isinstance(w, str) for w in result)
    assert len(result) > 0


def test_markov_generate_with_syllable_target():
    """Syllable-targeted generation."""
    chain = MarkovChain(order=2)
    chain.train(DEFAULT_CORPUS)
    
    for target in [5, 7]:
        result = chain.generate_with_syllable_target(target)
        if result:
            assert syllable_count_phrase(result) == target, \
                f"Expected {target} syllables, got {syllable_count_phrase(result)}: '{result}'"


def test_markov_construct_by_syllables():
    """Fallback syllable construction."""
    chain = MarkovChain(order=2)
    chain.train(DEFAULT_CORPUS)
    result = chain._construct_by_syllables(5)
    if result:
        assert syllable_count_phrase(result) == 5, \
            f"Expected 5 syllables, got {syllable_count_phrase(result)}: '{result}'"


# ─── Haiku Generator tests ────────────────────────────────────────────────────

def test_haiku_train_default():
    """Default corpus training."""
    gen = HaikuGenerator()
    gen.train_default()
    assert len(gen.chain.all_words) > 0


def test_haiku_generate():
    """Generate a haiku."""
    random.seed(42)
    gen = HaikuGenerator()
    gen.train_default()
    haiku = gen.generate_haiku()
    assert haiku is not None, "Haiku generation returned None"
    assert len(haiku) == 3, f"Expected 3 lines, got {len(haiku)}"
    assert syllable_count_phrase(haiku[0]) == 5, \
        f"Line 1: expected 5 syllables, got {syllable_count_phrase(haiku[0])}: '{haiku[0]}'"
    assert syllable_count_phrase(haiku[1]) == 7, \
        f"Line 2: expected 7 syllables, got {syllable_count_phrase(haiku[1])}: '{haiku[1]}'"
    assert syllable_count_phrase(haiku[2]) == 5, \
        f"Line 3: expected 5 syllables, got {syllable_count_phrase(haiku[2])}: '{haiku[2]}'"


def test_haiku_format_pretty():
    """Pretty formatting."""
    gen = HaikuGenerator()
    gen.train_default()
    haiku = gen.generate_haiku()
    formatted = gen.format_haiku(haiku, style="pretty")
    assert "│" in formatted or "┌" in formatted


def test_haiku_format_minimal():
    """Minimal formatting."""
    gen = HaikuGenerator()
    gen.train_default()
    haiku = gen.generate_haiku()
    formatted = gen.format_haiku(haiku, style="minimal")
    lines = formatted.strip().split("\n")
    assert len(lines) == 3


def test_haiku_format_cjk():
    """CJK-style formatting."""
    gen = HaikuGenerator()
    gen.train_default()
    haiku = gen.generate_haiku()
    formatted = gen.format_haiku(haiku, style="cjk")
    assert "║" in formatted


def test_haiku_detect_season():
    """Season detection."""
    gen = HaikuGenerator()
    gen.train_default()
    
    spring = gen.detect_season("cherry blossom petals fall morning rain")
    assert spring == "spring"
    
    winter = gen.detect_season("snow frost ice cold moonlight night")
    assert winter == "winter"
    
    summer = gen.detect_season("sun cicada golden pond warm")
    assert summer == "summer"
    
    autumn = gen.detect_season("autumn leaf crimson moon mist")
    assert autumn == "autumn"


def test_haiku_generate_multiple():
    """Generate multiple haikus."""
    random.seed(123)
    gen = HaikuGenerator()
    gen.train_default()
    results = gen.generate_and_format(count=3, style="minimal")
    assert len(results) == 3


def test_haiku_custom_training():
    """Train on custom text and generate."""
    random.seed(999)
    gen = HaikuGenerator()
    custom_text = """
    The robot walks through the neon city streets
    Digital rain falls on the glass tower
    Circuit boards glow in the midnight darkness
    The android dreams of electric butterflies
    Code flows like water through the silicon valley
    The server hums its quiet song
    Binary stars shine in the data sky
    The hacker types into the glowing screen
    Electric pulses race through copper veins
    The network stretches across the sleeping world
    """
    gen.train(custom_text)
    haiku = gen.generate_haiku()
    assert haiku is not None
    assert len(haiku) == 3
    assert syllable_count_phrase(haiku[0]) == 5
    assert syllable_count_phrase(haiku[1]) == 7
    assert syllable_count_phrase(haiku[2]) == 5


def test_haiku_reproducible_with_seed():
    """Same seed produces same haiku."""
    gen1 = HaikuGenerator()
    gen1.train_default()
    random.seed(77)
    h1 = gen1.generate_haiku()

    gen2 = HaikuGenerator()
    gen2.train_default()
    random.seed(77)
    h2 = gen2.generate_haiku()

    assert h1 == h2, "Same seed should produce same haiku"


# ─── Run all tests ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [obj for name, obj in sorted(globals().items())
             if name.startswith("test_") and callable(obj)]
    
    passed = 0
    failed = 0
    errors = []
    
    for test in tests:
        name = test.__name__
        try:
            test()
            print(f"  ✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
            errors.append((name, str(e)))
        except Exception as e:
            print(f"  ✗ {name}: ERROR: {e}")
            failed += 1
            errors.append((name, f"ERROR: {e}"))
    
    print(f"\n  Results: {passed} passed, {failed} failed")
    
    if errors:
        print("\n  Failed tests:")
        for name, err in errors:
            print(f"    - {name}: {err}")
    
    sys.exit(0 if failed == 0 else 1)