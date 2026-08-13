#!/usr/bin/env python3
"""Tests for the Terminal Semaphore Flag Signaler."""

import sys
import os
import math

sys.path.insert(0, os.path.dirname(__file__))

from semaphore import (
    encode_text,
    SEMAPHORE,
    NUMERAL_MAP,
    POSITIONS,
    render_figure,
    render_diagram,
    angle_to_delta,
    make_canvas,
    set_pixel,
    draw_line,
)


def test_all_letters_encoded():
    """Every A-Z letter must have a semaphore mapping."""
    import string
    for letter in string.ascii_uppercase:
        assert letter in SEMAPHORE, f"Missing semaphore mapping for {letter}"
        left, right = SEMAPHORE[letter]
        assert 1 <= left <= 8, f"Invalid left position {left} for {letter}"
        assert 1 <= right <= 8, f"Invalid right position {right} for {letter}"
        assert left != right, f"Both arms same position for {letter}"
    print("✓ All 26 letters have valid semaphore mappings")


def test_positions_count():
    """There should be exactly 8 flag positions."""
    assert len(POSITIONS) == 8, f"Expected 8 positions, got {len(POSITIONS)}"
    for i in range(1, 9):
        assert i in POSITIONS, f"Missing position {i}"
    print("✓ 8 flag positions defined correctly")


def test_encode_basic_letters():
    """Test encoding simple letter sequences."""
    frames = encode_text("AB")
    assert len(frames) == 2
    assert frames[0][0] == 'A'
    assert frames[1][0] == 'B'
    # A = (1, 8), B = (1, 7)
    assert (frames[0][1], frames[0][2]) == SEMAPHORE['A']
    assert (frames[1][1], frames[1][2]) == SEMAPHORE['B']
    print("✓ Basic letter encoding works")


def test_encode_lowercase():
    """Lowercase letters should be converted to uppercase."""
    frames = encode_text("hello")
    assert len(frames) == 5
    for f in frames:
        assert f[0] in 'HELO'
    print("✓ Lowercase conversion works")


def test_encode_space():
    """Spaces should produce rest position (1, 1)."""
    frames = encode_text("A B")
    assert len(frames) == 3
    assert frames[1][0] == ' '
    assert (frames[1][1], frames[1][2]) == (1, 1)
    print("✓ Space encoding (rest) works")


def test_encode_digits():
    """Digits should trigger numeral mode with J preamble."""
    frames = encode_text("1")
    # Should be: [J-numerals, 1-as-A]
    assert len(frames) == 2
    assert frames[0][0] == '#'  # numeral marker
    assert (frames[0][1], frames[0][2]) == SEMAPHORE['J']
    # 1 maps to A in numeral mode
    assert (frames[1][1], frames[1][2]) == SEMAPHORE['A']
    print("✓ Digit encoding with numeral preamble works")


def test_encode_multi_digits():
    """Multiple digits should share one numeral preamble."""
    frames = encode_text("123")
    # Should be: [J, 1, 2, 3] = 4 frames, 1 preamble + 3 digits
    assert len(frames) == 4
    assert frames[0][0] == '#'
    assert frames[1][0] == '1'
    assert frames[2][0] == '2'
    assert frames[3][0] == '3'
    print("✓ Multi-digit encoding shares numeral preamble")


def test_encode_unknown_char():
    """Unknown characters should produce rest position."""
    frames = encode_text("@")
    assert len(frames) == 1
    char, left, right, label = frames[0]
    assert (left, right) == (1, 1)
    assert 'Unknown' in label
    print("✓ Unknown character handling works")


def test_render_figure_dimensions():
    """Rendered figure should have correct dimensions."""
    lines = render_figure(1, 8)
    assert isinstance(lines, list)
    assert len(lines) == 22  # CANVAS_H
    for line in lines:
        assert len(line) == 40  # CANVAS_W
    print("✓ Figure rendering dimensions correct")


def test_render_figure_has_content():
    """Rendered figure should contain the head character."""
    lines = render_figure(5, 5)  # both arms up
    content = ''.join(lines)
    assert '@' in content, "Head character '@' not found in render"
    assert '#' in content, "Flag character '#' not found in render"
    print("✓ Figure rendering contains head and flags")


def test_render_figure_different_positions():
    """Different positions should produce different renders."""
    render_a = render_figure(1, 8)  # A
    render_b = render_figure(1, 7)  # B
    assert render_a != render_b, "Different positions produced identical renders"
    print("✓ Different positions produce different renders")


def test_render_diagram():
    """Diagram should be a non-empty list of strings."""
    diag = render_diagram(1, 8)
    assert isinstance(diag, list)
    assert len(diag) > 0
    assert all(isinstance(line, str) for line in diag)
    print("✓ Diagram rendering works")


def test_angle_to_delta_right():
    """0 degrees should point right (positive dx, zero dy)."""
    dx, dy = angle_to_delta(0, length=5)
    assert dx == 5
    assert dy == 0
    print("✓ Angle 0° -> right")


def test_angle_to_delta_up():
    """90 degrees should point up (zero dx, negative dy on screen)."""
    dx, dy = angle_to_delta(90, length=5)
    assert dx == 0
    assert dy == -5
    print("✓ Angle 90° -> up")


def test_angle_to_delta_down():
    """-90 degrees should point down (zero dx, positive dy on screen)."""
    dx, dy = angle_to_delta(-90, length=5)
    assert dx == 0
    assert dy == 5
    print("✓ Angle -90° -> down")


def test_angle_to_delta_left():
    """180 degrees should point left (negative dx, zero dy)."""
    dx, dy = angle_to_delta(180, length=5)
    assert dx == -5
    assert dy == 0
    print("✓ Angle 180° -> left")


def test_canvas_operations():
    """Test basic canvas operations."""
    canvas = make_canvas()
    assert len(canvas) == 22
    assert len(canvas[0]) == 40

    set_pixel(canvas, 5, 3, 'X')
    assert canvas[3][5] == 'X'

    # Out of bounds should not crash
    set_pixel(canvas, -1, -1, 'Y')
    set_pixel(canvas, 100, 100, 'Y')
    print("✓ Canvas operations work")


def test_draw_line():
    """Test line drawing produces expected pixels."""
    canvas = make_canvas()
    draw_line(canvas, 10, 10, 15, 10, '*')
    for x in range(10, 16):
        assert canvas[10][x] == '*'
    print("✓ Line drawing works")


def test_draw_line_diagonal():
    """Test diagonal line drawing."""
    canvas = make_canvas()
    draw_line(canvas, 10, 10, 15, 15, '+')
    for i in range(6):
        assert canvas[10 + i][10 + i] == '+'
    print("✓ Diagonal line drawing works")


def test_numeral_map():
    """Numeral map should cover all digits 0-9."""
    for d in '0123456789':
        assert d in NUMERAL_MAP
        assert NUMERAL_MAP[d] in SEMAPHORE
    print("✓ Numeral map covers all digits")


def test_sos_encoding():
    """SOS should encode to 3 frames (S, O, S)."""
    frames = encode_text("SOS")
    assert len(frames) == 3
    assert frames[0][0] == 'S'
    assert frames[1][0] == 'O'
    assert frames[2][0] == 'S'
    print("✓ SOS encoding works")


def test_all_positions_unique_angles():
    """All 8 positions should have distinct angles."""
    angles = list(POSITIONS.values())
    assert len(set(angles)) == 8, "Duplicate angles in positions"
    print("✓ All 8 positions have unique angles")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("  Semaphore Signaler — Test Suite")
    print("=" * 50 + "\n")

    tests = [
        test_all_letters_encoded,
        test_positions_count,
        test_encode_basic_letters,
        test_encode_lowercase,
        test_encode_space,
        test_encode_digits,
        test_encode_multi_digits,
        test_encode_unknown_char,
        test_render_figure_dimensions,
        test_render_figure_has_content,
        test_render_figure_different_positions,
        test_render_diagram,
        test_angle_to_delta_right,
        test_angle_to_delta_up,
        test_angle_to_delta_down,
        test_angle_to_delta_left,
        test_canvas_operations,
        test_draw_line,
        test_draw_line_diagonal,
        test_numeral_map,
        test_sos_encoding,
        test_all_positions_unique_angles,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {test.__name__}: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"{'=' * 50}\n")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(run_all_tests())