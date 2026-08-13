#!/usr/bin/env python3
"""Tests for the Terminal Semaphore Flag Signaler v2.0.0.

Covers encoding, decoding, rendering, CLI helpers, special signals,
color support, JSON export, and edge cases.
"""

import sys
import os
import math
import io
import string

sys.path.insert(0, os.path.dirname(__file__))

from semaphore import (
    # Encoding / decoding
    encode_text,
    decode_positions,
    decode_position_string,
    SEMAPHORE,
    SEMAPHORE_REVERSE,
    NUMERAL_MAP,
    NUMERAL_REVERSE,
    POSITIONS,
    POSITION_NAMES,
    SPECIAL_SIGNALS,
    REST,
    __version__,
    # Rendering
    render_figure,
    render_figure_colored,
    render_diagram,
    angle_to_delta,
    make_canvas,
    set_pixel,
    draw_line,
    _line_pixels,
    # Color
    colorize,
    COLORS,
    # CLI
    build_parser,
    export_frames,
)


# ---------------------------------------------------------------------------
# Encoding tests
# ---------------------------------------------------------------------------

def test_all_letters_encoded():
    """Every A-Z letter must have a semaphore mapping."""
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


def test_position_names():
    """Every position should have a human-readable name."""
    for i in range(1, 9):
        assert i in POSITION_NAMES, f"Missing name for position {i}"
        assert isinstance(POSITION_NAMES[i], str)
        assert len(POSITION_NAMES[i]) > 0
    print("✓ All positions have names")


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


def test_encode_empty_string():
    """Encoding an empty string should produce no frames."""
    frames = encode_text("")
    assert len(frames) == 0
    print("✓ Empty string encoding works")


def test_encode_punctuation():
    """Punctuation should be treated as unknown characters (rest)."""
    frames = encode_text("A!B")
    assert len(frames) == 3
    assert frames[1][0] == '!'
    assert (frames[1][1], frames[1][2]) == (1, 1)
    assert 'Unknown' in frames[1][3]
    print("✓ Punctuation handling works")


# ---------------------------------------------------------------------------
# Decoding tests
# ---------------------------------------------------------------------------

def test_decode_basic_letters():
    """Decode position pairs back to letters."""
    # A = (1,8), B = (1,7)
    result = decode_positions([(1, 8), (1, 7)])
    assert result == "AB", f"Expected 'AB', got '{result}'"
    print("✓ Basic letter decoding works")


def test_decode_reversed_order():
    """Decode should handle reversed position pairs (symmetric)."""
    # A = (1,8) — reversed should also decode to A
    result = decode_positions([(8, 1)])
    assert result == "A", f"Expected 'A', got '{result}'"
    print("✓ Reversed position order decoding works")


def test_decode_spaces():
    """Rest position should decode to space."""
    result = decode_positions([(1, 8), (1, 1), (1, 7)])
    assert result == "A B", f"Expected 'A B', got '{result}'"
    print("✓ Space decoding works")


def test_decode_digits():
    """Decode numeral preamble + digit letters."""
    # J = (2,6), then A = (1,8) for '1'
    result = decode_positions([(2, 6), (1, 8)])
    assert result == "1", f"Expected '1', got '{result}'"
    print("✓ Digit decoding works")


def test_decode_unknown_pair():
    """Unknown position pairs should produce '?'."""
    # (1, 1) is rest, so use a valid but unmapped pair.
    # All single-position pairs (like (3,3)) are not in the map.
    result = decode_positions([(3, 3)])
    assert '?' in result, f"Expected '?' in result, got '{result}'"
    print("✓ Unknown pair decoding produces '?'")


def test_decode_position_string_spaces():
    """Parse space-separated position string."""
    result = decode_position_string("1,8 1,7")
    assert result == "AB", f"Expected 'AB', got '{result}'"
    print("✓ Position string parsing (spaces) works")


def test_decode_position_string_semicolons():
    """Parse semicolon-separated position string."""
    result = decode_position_string("1,8;1,7")
    assert result == "AB", f"Expected 'AB', got '{result}'"
    print("✓ Position string parsing (semicolons) works")


def test_decode_position_string_dashes():
    """Parse dash-separated position pairs."""
    result = decode_position_string("1-8 1-7")
    assert result == "AB", f"Expected 'AB', got '{result}'"
    print("✓ Position string parsing (dashes) works")


def test_decode_sos():
    """Decode S-O-S positions."""
    # S=(4,8), O=(3,7)
    result = decode_position_string("4,8 3,7 4,8")
    assert result == "SOS", f"Expected 'SOS', got '{result}'"
    print("✓ SOS decoding works")


def test_roundtrip_encode_decode():
    """Encode text, then decode the positions — should get the text back."""
    text = "HELLO"
    frames = encode_text(text)
    positions = [(f[1], f[2]) for f in frames if f[0] != ' ' and f[0] != '#']
    # We filter out the numeral marker '#', so letters should round-trip
    decoded = decode_positions(positions)
    assert decoded == "HELLO", f"Expected 'HELLO', got '{decoded}'"
    print("✓ Round-trip encode→decode works")


def test_reverse_map_completeness():
    """SEMAPHORE_REVERSE should contain entries for all letters (both orderings)."""
    for letter in string.ascii_uppercase:
        left, right = SEMAPHORE[letter]
        assert (left, right) in SEMAPHORE_REVERSE
        assert (right, left) in SEMAPHORE_REVERSE
        assert SEMAPHORE_REVERSE[(left, right)] == letter
        assert SEMAPHORE_REVERSE[(right, left)] == letter
    print("✓ Reverse semaphore map is complete and symmetric")


def test_numeral_reverse():
    """NUMERAL_REVERSE should map letters back to digits."""
    for digit, letter in NUMERAL_MAP.items():
        assert NUMERAL_REVERSE[letter] == digit
    print("✓ Numeral reverse map works")


# ---------------------------------------------------------------------------
# Special signals tests
# ---------------------------------------------------------------------------

def test_special_signals_defined():
    """Special signals should be defined with valid positions."""
    expected = {'REST', 'ATTENTION', 'ERROR', 'CORRECT', 'NUMERALS', 'LETTERS'}
    assert set(SPECIAL_SIGNALS.keys()) == expected, \
        f"Missing special signals. Got: {set(SPECIAL_SIGNALS.keys())}"
    for name, (l, r) in SPECIAL_SIGNALS.items():
        assert 1 <= l <= 8 and 1 <= r <= 8, f"Invalid positions for {name}: ({l}, {r})"
    print("✓ Special signals defined correctly")


def test_rest_is_both_down():
    """REST should be (1, 1) — both arms down."""
    assert SPECIAL_SIGNALS['REST'] == (1, 1)
    assert REST == (1, 1)
    print("✓ REST signal is (1, 1)")


# ---------------------------------------------------------------------------
# Rendering tests
# ---------------------------------------------------------------------------

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


def test_render_figure_colored_dimensions():
    """Colored figure should still produce 22 lines."""
    lines = render_figure_colored(1, 8)
    assert isinstance(lines, list)
    assert len(lines) == 22
    print("✓ Colored figure rendering dimensions correct")


def test_render_figure_colored_has_ansi():
    """Colored figure should contain ANSI escape codes."""
    lines = render_figure_colored(1, 8)
    content = ''.join(lines)
    assert '\033[' in content, "No ANSI escape codes found in colored render"
    print("✓ Colored figure contains ANSI codes")


def test_render_diagram():
    """Diagram should be a non-empty list of strings."""
    diag = render_diagram(1, 8)
    assert isinstance(diag, list)
    assert len(diag) > 0
    assert all(isinstance(line, str) for line in diag)
    print("✓ Diagram rendering works")


def test_render_diagram_shows_active():
    """Diagram should mention active positions in the label line."""
    diag = render_diagram(4, 8)
    joined = '\n'.join(diag)
    assert '4' in joined and '8' in joined, "Active positions not shown in diagram"
    # Should also include position names
    assert 'up-right' in joined or 'down-left' in joined, \
        "Position names not shown in diagram"
    print("✓ Diagram shows active positions with names")


# ---------------------------------------------------------------------------
# Angle / canvas tests
# ---------------------------------------------------------------------------

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


def test_line_pixels():
    """Test the _line_pixels helper returns correct pixel list."""
    pixels = _line_pixels(10, 10, 15, 10)
    assert len(pixels) == 6
    assert pixels[0] == (10, 10)
    assert pixels[-1] == (15, 10)
    print("✓ Line pixels helper works")


# ---------------------------------------------------------------------------
# Color tests
# ---------------------------------------------------------------------------

def test_colorize_enabled():
    """colorize should wrap text with ANSI codes when enabled."""
    result = colorize("hello", "red", enabled=True)
    assert '\033[31m' in result
    assert '\033[0m' in result
    assert 'hello' in result
    print("✓ colorize works when enabled")


def test_colorize_disabled():
    """colorize should return plain text when disabled."""
    result = colorize("hello", "red", enabled=False)
    assert result == "hello"
    print("✓ colorize returns plain text when disabled")


def test_colorize_unknown_color():
    """colorize should return plain text for unknown colors."""
    result = colorize("hello", "nonexistent", enabled=True)
    assert result == "hello"
    print("✓ colorize handles unknown colors gracefully")


def test_colors_defined():
    """All expected colors should be in the COLORS dict."""
    expected = ['reset', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white', 'bold']
    for c in expected:
        assert c in COLORS, f"Missing color: {c}"
    print("✓ All expected colors defined")


# ---------------------------------------------------------------------------
# CLI / parser tests
# ---------------------------------------------------------------------------

def test_version_flag():
    """The --version flag should be present and return the version string."""
    parser = build_parser()
    # Simulate --version
    old_stderr, old_stdout = sys.stderr, sys.stdout
    try:
        sys.stdout = io.StringIO()
        try:
            parser.parse_args(['--version'])
            assert False, "Should have exited"
        except SystemExit as e:
            assert e.code == 0
        output = sys.stdout.getvalue()
        assert __version__ in output
    finally:
        sys.stderr, sys.stdout = old_stderr, old_stdout
    print("✓ --version flag works")


def test_parser_default_args():
    """Parser should set sensible defaults."""
    parser = build_parser()
    args = parser.parse_args(["HELLO"])
    assert args.text == ["HELLO"]
    assert args.delay == 1.2
    assert args.loop is False
    assert args.color is False
    assert args.encode is False
    assert args.json is False
    assert args.chart is False
    assert args.special is False
    assert args.export is None
    assert args.decode is None
    print("✓ Parser defaults are correct")


def test_parser_color_flag():
    """Parser should parse --color flag."""
    parser = build_parser()
    args = parser.parse_args(["TEST", "--color"])
    assert args.color is True
    print("✓ --color flag parsed correctly")


def test_parser_json_flag():
    """Parser should parse --json flag."""
    parser = build_parser()
    args = parser.parse_args(["TEST", "--json"])
    assert args.json is True
    print("✓ --json flag parsed correctly")


def test_parser_decode_flag():
    """Parser should parse --decode flag with a value."""
    parser = build_parser()
    args = parser.parse_args(["--decode", "1,8 1,7"])
    assert args.decode == "1,8 1,7"
    print("✓ --decode flag parsed correctly")


def test_parser_export_flag():
    """Parser should parse --export flag with a filepath."""
    parser = build_parser()
    args = parser.parse_args(["TEST", "--export", "output.txt"])
    assert args.export == "output.txt"
    print("✓ --export flag parsed correctly")


def test_parser_special_flag():
    """Parser should parse --special flag."""
    parser = build_parser()
    args = parser.parse_args(["--special"])
    assert args.special is True
    print("✓ --special flag parsed correctly")


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------

def test_export_frames(tmp_path="/tmp"):
    """Test that export_frames writes a file with correct content."""
    filepath = os.path.join(tmp_path, "_semaphore_test_export.txt")
    # Clean up if exists
    if os.path.exists(filepath):
        os.remove(filepath)

    export_frames("SOS", filepath, show_diagram=False)

    assert os.path.exists(filepath), "Export file was not created"
    with open(filepath, 'r') as f:
        content = f.read()

    assert "Semaphore Signal Export" in content
    assert "SOS" in content
    assert "Frame" in content
    assert "Letter 'S'" in content

    # Clean up
    os.remove(filepath)
    print("✓ Export frames writes valid file")


def test_export_frames_with_diagram(tmp_path="/tmp"):
    """Test that export_frames includes diagrams when requested."""
    filepath = os.path.join(tmp_path, "_semaphore_test_export2.txt")
    if os.path.exists(filepath):
        os.remove(filepath)

    export_frames("AB", filepath, show_diagram=True)

    with open(filepath, 'r') as f:
        content = f.read()

    assert "Active positions" in content

    os.remove(filepath)
    print("✓ Export frames with diagram works")


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

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


def test_version_string():
    """Version should be a non-empty string."""
    assert isinstance(__version__, str)
    assert len(__version__) > 0
    # Should look like a semver
    parts = __version__.split('.')
    assert len(parts) >= 2, f"Version doesn't look like semver: {__version__}"
    print("✓ Version string is valid")


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("  Semaphore Signaler — Test Suite (v2.0.0)")
    print("=" * 50 + "\n")

    tests = [
        # Encoding
        test_all_letters_encoded,
        test_positions_count,
        test_position_names,
        test_encode_basic_letters,
        test_encode_lowercase,
        test_encode_space,
        test_encode_digits,
        test_encode_multi_digits,
        test_encode_unknown_char,
        test_encode_empty_string,
        test_encode_punctuation,
        # Decoding
        test_decode_basic_letters,
        test_decode_reversed_order,
        test_decode_spaces,
        test_decode_digits,
        test_decode_unknown_pair,
        test_decode_position_string_spaces,
        test_decode_position_string_semicolons,
        test_decode_position_string_dashes,
        test_decode_sos,
        test_roundtrip_encode_decode,
        test_reverse_map_completeness,
        test_numeral_reverse,
        # Special signals
        test_special_signals_defined,
        test_rest_is_both_down,
        # Rendering
        test_render_figure_dimensions,
        test_render_figure_has_content,
        test_render_figure_different_positions,
        test_render_figure_colored_dimensions,
        test_render_figure_colored_has_ansi,
        test_render_diagram,
        test_render_diagram_shows_active,
        # Angle / canvas
        test_angle_to_delta_right,
        test_angle_to_delta_up,
        test_angle_to_delta_down,
        test_angle_to_delta_left,
        test_canvas_operations,
        test_draw_line,
        test_draw_line_diagonal,
        test_line_pixels,
        # Color
        test_colorize_enabled,
        test_colorize_disabled,
        test_colorize_unknown_color,
        test_colors_defined,
        # CLI / parser
        test_version_flag,
        test_parser_default_args,
        test_parser_color_flag,
        test_parser_json_flag,
        test_parser_decode_flag,
        test_parser_export_flag,
        test_parser_special_flag,
        # Export
        test_export_frames,
        test_export_frames_with_diagram,
        # Integration
        test_numeral_map,
        test_sos_encoding,
        test_all_positions_unique_angles,
        test_version_string,
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