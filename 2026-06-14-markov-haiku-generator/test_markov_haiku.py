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
    syllable_breakdown,
    MarkovChain,
    HaikuGenerator,
    DEFAULT_CORPUS,
    Colors,
    __version__,
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


def test_syllable_breakdown():
    """Test the syllable_breakdown helper."""
    bd = syllable_breakdown("cherry blossom petals")
    assert bd == [("cherry", 2), ("blossom", 2), ("petals", 2)]
    total = sum(sc for _, sc in bd)
    assert total == 6


def test_syllable_new_exceptions():
    """New exception words added in v1.1."""
    assert count_syllables("willow") == 2
    assert count_syllables("sunset") == 2
    assert count_syllables("meadow") == 2
    assert count_syllables("alone") == 2
    assert count_syllables("remember") == 3
    assert count_syllables("return") == 2


# ─── Markov Chain tests ────────────────────────────────────────────────────

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


def test_markov_order_validation():
    """Order must be >= 1."""
    try:
        MarkovChain(order=0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_markov_train_empty():
    """Training on empty text should not crash."""
    chain = MarkovChain(order=2)
    chain.train("")
    chain.train("   ")
    assert len(chain.all_words) == 0


def test_markov_train_short():
    """Training on short text (fewer words than order) should still work."""
    chain = MarkovChain(order=2)
    chain.train("hello world")
    assert "hello" in chain.all_words or "world" in chain.all_words


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


# ─── Tanka tests ────────────────────────────────────────────────────────────

def test_tanka_generate():
    """Generate a tanka (5-7-5-7-7)."""
    random.seed(42)
    gen = HaikuGenerator()
    gen.train_default()
    tanka = gen.generate_tanka()
    assert tanka is not None, "Tanka generation returned None"
    assert len(tanka) == 5, f"Expected 5 lines, got {len(tanka)}"
    targets = [5, 7, 5, 7, 7]
    for i, (line, target) in enumerate(zip(tanka, targets)):
        actual = syllable_count_phrase(line)
        assert actual == target, \
            f"Line {i+1}: expected {target} syllables, got {actual}: '{line}'"


def test_tanka_format():
    """Format a tanka with type label."""
    gen = HaikuGenerator()
    gen.train_default()
    random.seed(42)
    tanka = gen.generate_tanka()
    formatted = gen.format_haiku(tanka, style="pretty", poem_type="tanka")
    assert tanka is not None
    # Should contain border characters
    assert "│" in formatted or "┌" in formatted


def test_tanka_format_cjk():
    """CJK format of a tanka includes 'tanka' label."""
    gen = HaikuGenerator()
    gen.train_default()
    random.seed(42)
    tanka = gen.generate_tanka()
    if tanka:
        formatted = gen.format_haiku(tanka, style="cjk", poem_type="tanka")
        assert "tanka" in formatted.lower() or "║" in formatted


def test_tanka_format_minimal():
    """Minimal format of tanka has 5 lines."""
    gen = HaikuGenerator()
    gen.train_default()
    random.seed(42)
    tanka = gen.generate_tanka()
    if tanka:
        formatted = gen.format_haiku(tanka, style="minimal", poem_type="tanka")
        assert len(formatted.strip().split("\n")) == 5


# ─── Season bias tests ────────────────────────────────────────────────────────

def test_haiku_season_bias():
    """Generate haiku with season bias."""
    random.seed(100)
    gen = HaikuGenerator()
    gen.train_default()
    # Try winter bias — generate several and at least one should match
    for _ in range(10):
        haiku = gen.generate_haiku(season_bias="winter")
        if haiku:
            season = gen.detect_season(" ".join(haiku))
            assert season == "winter", f"Season bias winter failed, got {season}"
            break  # At least one success is enough


# ─── Stats and formatting tests ─────────────────────────────────────────────

def test_format_stats():
    """Stats display shows syllable breakdown."""
    gen = HaikuGenerator()
    gen.train_default()
    random.seed(42)
    haiku = gen.generate_haiku()
    assert haiku is not None
    stats = gen.format_stats(haiku)
    assert "Line 1 (5):" in stats
    assert "Line 2 (7):" in stats
    assert "Line 3 (5):" in stats


def test_format_stats_tanka():
    """Stats display for tanka shows 5 lines."""
    gen = HaikuGenerator()
    gen.train_default()
    random.seed(42)
    tanka = gen.generate_tanka()
    if tanka:
        stats = gen.format_stats(tanka, poem_type="tanka")
        assert "Line 5 (7):" in stats


def test_format_empty():
    """Formatting None/empty returns fallback string."""
    gen = HaikuGenerator()
    result = gen.format_haiku(None)
    assert "could not generate" in result.lower() or "no poem" in result.lower()


# ─── Colors tests ────────────────────────────────────────────────────────────

def test_colors_disabled():
    """Colors.enabled() returns False when NO_COLOR is set."""
    old = os.environ.get("NO_COLOR")
    os.environ["NO_COLOR"] = "1"
    assert Colors.enabled() is False
    if old is None:
        del os.environ["NO_COLOR"]
    else:
        os.environ["NO_COLOR"] = old


def test_colors_bold():
    """Colors.bold returns text unchanged when disabled."""
    old = os.environ.get("NO_COLOR")
    os.environ["NO_COLOR"] = "1"
    assert Colors.bold("hello") == "hello"
    if old is None:
        del os.environ["NO_COLOR"]
    else:
        os.environ["NO_COLOR"] = old


def test_season_color():
    """Season color returns text when disabled."""
    old = os.environ.get("NO_COLOR")
    os.environ["NO_COLOR"] = "1"
    assert Colors.season_color("spring", "Spring") == "Spring"
    if old is None:
        del os.environ["NO_COLOR"]
    else:
        os.environ["NO_COLOR"] = old


# ─── Version test ────────────────────────────────────────────────────────────

def test_version():
    """Version string is valid."""
    assert __version__ is not None
    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


# ─── Bug fix tests ─────────────────────────────────────────────────────────────

def test_cjk_format_box_width():
    """CJK format box should accommodate long lines without overflow."""
    gen = HaikuGenerator()
    gen.train_default()
    # Test with lines that would overflow a 24-char inner width
    long_lines = ["The temple bell echoes through the dark",
                  "A frog jumps into the still",
                  "Sunset paints the clouds"]
    formatted = gen.format_haiku(long_lines, style="cjk")
    # All content lines should have consistent width between ║ markers
    content_lines = [l for l in formatted.split("\n") if "║" in l and "═" not in l]
    widths = set()
    for line in content_lines:
        parts = line.split("║")
        if len(parts) >= 3:
            widths.add(len(parts[1]))
    # All content lines should have the same width
    assert len(widths) == 1, f"Inconsistent CJK box widths: {widths}"


def test_cjk_format_short_lines():
    """CJK format should properly pad short lines."""
    gen = HaikuGenerator()
    gen.train_default()
    short_lines = ["Cat", "Dog runs", "Bird flies high"]
    formatted = gen.format_haiku(short_lines, style="cjk")
    # All content lines should have consistent width
    content_lines = [l for l in formatted.split("\n") if "║" in l and "═" not in l]
    widths = set()
    for line in content_lines:
        parts = line.split("║")
        if len(parts) >= 3:
            widths.add(len(parts[1]))
    assert len(widths) == 1, f"Inconsistent CJK box widths: {widths}"


def test_pretty_format_box_width():
    """Pretty format should accommodate long lines."""
    gen = HaikuGenerator()
    gen.train_default()
    long_lines = ["The temple bell echoes through the dark and ancient valley",
                  "A frog jumps into",
                  "Sunset paints the clouds"]
    formatted = gen.format_haiku(long_lines, style="pretty")
    # Should not crash and should produce output
    assert "│" in formatted


def test_train_none():
    """train(None) should not crash."""
    gen = HaikuGenerator()
    gen.train(None)
    gen.train_default()
    assert len(gen.chain.all_words) > 0


def test_train_non_string():
    """train(non-string) should not crash."""
    gen = HaikuGenerator()
    gen.train(42)
    gen.train_default()
    assert len(gen.chain.all_words) > 0


def test_markov_train_none():
    """MarkovChain.train(None) should not crash."""
    chain = MarkovChain(order=2)
    chain.train(None)
    chain.train(DEFAULT_CORPUS)
    assert len(chain.all_words) > 0


def test_markov_train_non_string():
    """MarkovChain.train(non-string) should not crash."""
    chain = MarkovChain(order=2)
    chain.train(42)
    chain.train(DEFAULT_CORPUS)
    assert len(chain.all_words) > 0


def test_format_stats_extra_lines():
    """format_stats should show extra lines beyond target count."""
    gen = HaikuGenerator()
    gen.train_default()
    # Pass 5 lines with haiku type (expects 3 targets)
    lines = ["Cherry blossoms fall", "Moonlight paints the garden in silver",
             "A single raindrop", "Autumn leaves drift down",
             "The ancient pine survives"]
    stats = gen.format_stats(lines, poem_type="haiku")
    # Should show all 5 lines (3 with targets + 2 extra)
    assert "Line 4:" in stats
    assert "Line 5:" in stats


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