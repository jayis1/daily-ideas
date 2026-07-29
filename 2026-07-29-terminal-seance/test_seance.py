#!/usr/bin/env python3
"""Tests for the Terminal Séance — verifies core logic without needing a TTY.

Run:    python3 test_seance.py
Exit:   0 on success, 1 on first failure.
"""

import os
import sys
import random

sys.path.insert(0, os.path.dirname(__file__))
import ouija

_failures = []


def _run(name, fn):
    try:
        fn()
    except AssertionError as e:
        print(f"  ✗ {name}: {e}")
        _failures.append(name)
        return False
    return True


# ---------------------------------------------------------------------------
# Original tests
# ---------------------------------------------------------------------------

def test_letter_positions():
    """All 26 letters and 10 digits should have valid on-board positions."""
    assert len(ouija.LETTER_POS) == 26 + 10  # 26 letters + 10 numbers
    for ch, (cx, cy) in ouija.LETTER_POS.items():
        assert 0 < cx < ouija.BOARD_WIDTH, f"{ch} col {cx} out of bounds"
        assert 0 < cy < ouija.BOARD_HEIGHT, f"{ch} row {cy} out of bounds"
    assert "A" in ouija.LETTER_POS
    assert "Z" in ouija.LETTER_POS
    assert "0" in ouija.LETTER_POS
    print("  ✓ Letter positions valid")


def test_spirits_well_formed():
    """Every spirit should have the required keys and non-empty vocabulary."""
    required = {"name", "color", "desc", "style", "vocabulary", "farewell", "favor_yes"}
    for s in ouija.SPIRITS:
        assert required.issubset(s.keys()), f"Spirit missing keys: {s}"
        assert len(s["vocabulary"]) >= 5, f"{s['name']} has too few words"
        assert 0 <= s["favor_yes"] <= 1, f"{s['name']} favor_yes out of range"
        assert s["name"], "Spirit has empty name"
    print(f"  ✓ {len(ouija.SPIRITS)} spirits well-formed")


def test_response_generation():
    """generate_response should return a non-empty list of valid tokens."""
    for spirit in ouija.SPIRITS:
        for q in ["Will I be rich?", "Who are you?", "Is anyone there?", "Tell me a secret", ""]:
            tokens = ouija.generate_response(spirit, q)
            assert len(tokens) > 0, f"{spirit['name']} produced no tokens for '{q}'"
            for tok in tokens:
                assert tok[0] in ("LETTER", "SPECIAL"), f"Bad token type: {tok}"
                if tok[0] == "LETTER":
                    assert isinstance(tok[1], str) and len(tok[1]) == 1
                elif tok[0] == "SPECIAL":
                    assert tok[1] in ("YES", "NO", "GOODBYE"), f"Bad special: {tok[1]}"
    print("  ✓ Response generation produces valid tokens for all spirits")


def test_target_positions():
    """get_target_position should return valid board coordinates for all token types."""
    for special in [("SPECIAL", "YES"), ("SPECIAL", "NO"), ("SPECIAL", "GOODBYE")]:
        pos = ouija.get_target_position(special)
        assert 0 < pos[0] < ouija.BOARD_WIDTH
        assert 0 < pos[1] < ouija.BOARD_HEIGHT
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        pos = ouija.get_target_position(("LETTER", ch))
        assert 0 < pos[0] < ouija.BOARD_WIDTH
        assert 0 < pos[1] < ouija.BOARD_HEIGHT
    # Space goes home
    pos = ouija.get_target_position(("LETTER", " "))
    assert pos == ouija.PLANCHETTE_HOME
    # Unknown token falls back to home (error handling)
    pos = ouija.get_target_position(("UNKNOWN", "??"))
    assert pos == ouija.PLANCHETTE_HOME
    print("  ✓ Target positions valid for all letters and specials")


def test_easing():
    """ease_in_out should be 0 at start, 1 at end, monotonic, and clamped."""
    assert ouija.ease_in_out(0) == 0
    assert ouija.ease_in_out(1) == 1
    prev = 0
    for i in range(1, 101):
        t = i / 100
        val = ouija.ease_in_out(t)
        assert val >= prev, "Easing not monotonic"
        prev = val
    # Clamp: out-of-range values should not explode
    assert ouija.ease_in_out(-0.5) == 0
    assert ouija.ease_in_out(1.5) == 1
    print("  ✓ Easing function is monotonic, bounded, and clamped")


def test_board_render():
    """render_board should produce a string containing all letters and special words."""
    board, planchette = ouija.render_board(ouija.SPIRITS[0]["color"],
                                           ouija.PLANCHETTE_HOME)
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
        assert ch in board, f"Letter {ch} not on board"
    assert "YES" in board
    assert "NO" in board
    assert "GOODBYE" in board
    assert isinstance(planchette, list) and len(planchette) > 0
    print("  ✓ Board renders with all letters, numbers, YES/NO/GOODBYE")


def test_planchette_shape():
    """Planchette should have a visible shape with the peephole."""
    shape = ouija.render_planchette((30, 14), "\033[0m")
    chars = [s[2] for s in shape]
    assert "◉" in chars, "Planchette missing peephole"
    assert "V" in chars, "Planchette missing pointer"
    print("  ✓ Planchette shape includes peephole and pointer")


# ---------------------------------------------------------------------------
# New tests (v1.1.0)
# ---------------------------------------------------------------------------

def test_no_color_mode():
    """--no-color should strip all ANSI escape codes from board output."""
    ouija.set_no_color(True)
    try:
        board, _ = ouija.render_board(ouija.SPIRITS[0]["color"], ouija.PLANCHETTE_HOME)
        assert "\033[" not in board, "ANSI codes leaked into no-color output"
    finally:
        ouija.set_no_color(False)
    print("  ✓ --no-color strips ANSI codes correctly")


def test_spirit_lookup():
    """pick_spirit should find spirits by name and reject invalid names."""
    s = ouija.pick_spirit(name="The Jester")
    assert s["name"] == "The Jester"
    # Case-insensitive
    s = ouija.pick_spirit(name="the jester")
    assert s["name"] == "The Jester"
    # Invalid name raises ValueError
    try:
        ouija.pick_spirit(name="Ghosty McGhostface")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    # Exclude works
    for _ in range(20):
        s = ouija.pick_spirit(exclude="The Whisperer")
        assert s["name"] != "The Whisperer"
    print("  ✓ Spirit lookup by name works (case-insensitive, validation, exclusion)")


def test_tokens_to_string():
    """tokens_to_string should render a readable message."""
    tokens = [("LETTER", "H"), ("LETTER", "I"), ("LETTER", " "), ("SPECIAL", "YES")]
    assert ouija.tokens_to_string(tokens) == "HI [YES]"
    # Empty
    assert ouija.tokens_to_string([]) == ""
    print("  ✓ tokens_to_string renders readable messages")


def test_session_log():
    """SessionLog should append entries and write to a temp file."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        path = f.name
    try:
        log = ouija.SessionLog(path)
        log.add("The Whisperer", "Is anyone there?", "YES")
        log.add("Captain Aldous", "Where are you?", "THE SEA")
        assert len(log.entries) == 2
        content = open(path, encoding="utf-8").read()
        assert "Terminal Séance" in content
        assert "The Whisperer" in content
        assert "Is anyone there?" in content
        assert "THE SEA" in content
        assert "Session had 2 exchange(s)" in log.summary()
    finally:
        os.unlink(path)
    print("  ✓ SessionLog writes Markdown transcript correctly")


def test_yn_word_set():
    """YN_WORDS should contain common question-starting words."""
    assert "will" in ouija.YN_WORDS
    assert "is" in ouija.YN_WORDS
    assert "the" not in ouija.YN_WORDS
    assert isinstance(ouija.YN_WORDS, frozenset)
    print("  ✓ YN_WORDS set is well-formed")


def test_version():
    """Version string should be a valid semver."""
    v = ouija.__version__
    parts = v.split(".")
    assert len(parts) == 3, f"Version should be semver: {v}"
    for p in parts:
        assert p.isdigit(), f"Version part not numeric: {p}"
    print(f"  ✓ Version {v} is valid semver")


def test_demo_runs():
    """run_demo should not crash and should exercise every spirit."""
    import io
    import contextlib
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        ouija.run_demo(type("Args", (), {"fast": True, "no_color": False})())
    out = captured.getvalue()
    for spirit in ouija.SPIRITS:
        assert spirit["name"] in out, f"Spirit {spirit['name']} missing from demo output"
    print("  ✓ Demo mode runs without errors and covers all spirits")


def test_seeded_reproducibility():
    """Same seed should produce identical responses."""
    random.seed(42)
    r1 = ouija.generate_response(ouija.SPIRITS[0], "Will I be rich?")
    random.seed(42)
    r2 = ouija.generate_response(ouija.SPIRITS[0], "Will I be rich?")
    assert r1 == r2, "Seeded responses should be identical"
    print("  ✓ Seeded random produces reproducible responses")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_TESTS = [
    ("letter_positions", test_letter_positions),
    ("spirits_well_formed", test_spirits_well_formed),
    ("response_generation", test_response_generation),
    ("target_positions", test_target_positions),
    ("easing", test_easing),
    ("board_render", test_board_render),
    ("planchette_shape", test_planchette_shape),
    ("no_color_mode", test_no_color_mode),
    ("spirit_lookup", test_spirit_lookup),
    ("tokens_to_string", test_tokens_to_string),
    ("session_log", test_session_log),
    ("yn_word_set", test_yn_word_set),
    ("version", test_version),
    ("demo_runs", test_demo_runs),
    ("seeded_reproducibility", test_seeded_reproducibility),
]


if __name__ == "__main__":
    print()
    print("  Terminal Séance — Test Suite")
    print(f"  ({len(ALL_TESTS)} tests)\n")
    passed = 0
    for name, fn in ALL_TESTS:
        if _run(name, fn):
            passed += 1
    print()
    if _failures:
        print(f"  ✗ {len(_failures)} test(s) failed: {', '.join(_failures)}")
        sys.exit(1)
    print(f"  ✓ All {passed} tests passed! The spirits are cooperative. ✟")
    sys.exit(0)