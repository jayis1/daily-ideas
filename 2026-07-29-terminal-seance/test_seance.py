#!/usr/bin/env python3
"""Smoke tests for the Terminal Séance — verifies core logic without needing a TTY."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import ouija


def test_letter_positions():
    """All 26 letters and 10 digits should have valid on-board positions."""
    assert len(ouija.LETTER_POS) == 26 + 10  # 26 letters + 10 numbers
    for ch, (cx, cy) in ouija.LETTER_POS.items():
        assert 0 < cx < ouija.BOARD_WIDTH, f"{ch} col {cx} out of bounds"
        assert 0 < cy < ouija.BOARD_HEIGHT, f"{ch} row {cy} out of bounds"
    # Spot check
    assert "A" in ouija.LETTER_POS
    assert "Z" in ouija.LETTER_POS
    assert "0" in ouija.LETTER_POS
    print("✓ Letter positions valid")


def test_spirits_well_formed():
    """Every spirit should have the required keys and non-empty vocabulary."""
    required = {"name", "color", "desc", "style", "vocabulary", "farewell", "favor_yes"}
    for s in ouija.SPIRITS:
        assert required.issubset(s.keys()), f"Spirit missing keys: {s}"
        assert len(s["vocabulary"]) >= 5, f"{s['name']} has too few words"
        assert 0 <= s["favor_yes"] <= 1, f"{s['name']} favor_yes out of range"
        assert s["name"], "Spirit has empty name"
    print(f"✓ {len(ouija.SPIRITS)} spirits well-formed")


def test_response_generation():
    """generate_response should return a non-empty list of valid tokens."""
    for spirit in ouija.SPIRITS:
        for q in ["Will I be rich?", "Who are you?", "Is anyone there?", "Tell me a secret"]:
            tokens = ouija.generate_response(spirit, q)
            assert len(tokens) > 0, f"{spirit['name']} produced no tokens for '{q}'"
            for tok in tokens:
                assert tok[0] in ("LETTER", "SPECIAL"), f"Bad token type: {tok}"
                if tok[0] == "LETTER":
                    assert isinstance(tok[1], str) and len(tok[1]) == 1
                elif tok[0] == "SPECIAL":
                    assert tok[1] in ("YES", "NO", "GOODBYE"), f"Bad special: {tok[1]}"
    print("✓ Response generation produces valid tokens for all spirits")


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
    print("✓ Target positions valid for all letters and specials")


def test_easing():
    """ease_in_out should be 0 at start, 1 at end, and monotonic."""
    assert ouija.ease_in_out(0) == 0
    assert ouija.ease_in_out(1) == 1
    prev = 0
    for i in range(1, 101):
        t = i / 100
        val = ouija.ease_in_out(t)
        assert val >= prev, "Easing not monotonic"
        prev = val
    print("✓ Easing function is monotonic and bounded")


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
    print("✓ Board renders with all letters, numbers, YES/NO/GOODBYE")


def test_planchette_shape():
    """Planchette should have a visible shape with the peephole."""
    shape = ouija.render_planchette((30, 14), "\033[0m")
    chars = [s[2] for s in shape]
    assert "◉" in chars, "Planchette missing peephole"
    assert "V" in chars, "Planchette missing pointer"
    print("✓ Planchette shape includes peephole and pointer")


if __name__ == "__main__":
    test_letter_positions()
    test_spirits_well_formed()
    test_response_generation()
    test_target_positions()
    test_easing()
    test_board_render()
    test_planchette_shape()
    print()
    print("All tests passed! The spirits are cooperative. ✟")