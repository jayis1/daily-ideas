#!/usr/bin/env python3
"""Tests for the Morse Wave Translator module.

Uses pytest-style assertions. Run with:
    pytest test_morse_wave.py -v
"""
import os
import sys
import tempfile

import morse_wave


# ─── Encoding / Decoding Tests ────────────────────────────────────────────────

class TestTextToMorse:
    """Tests for text_to_morse()."""

    def test_simple_word(self):
        assert morse_wave.text_to_morse("SOS") == "... --- ..."

    def test_multi_word(self):
        result = morse_wave.text_to_morse("HELLO WORLD")
        assert result == ".... . .-.. .-.. --- / .-- --- .-. .-.. -.."

    def test_case_insensitive(self):
        assert morse_wave.text_to_morse("hello") == morse_wave.text_to_morse("HELLO")

    def test_numbers(self):
        result = morse_wave.text_to_morse("123")
        assert result == ".---- ..--- ...--"

    def test_punctuation(self):
        result = morse_wave.text_to_morse("OK?")
        assert "?" in morse_wave.MORSE_ENCODE
        expected = morse_wave.MORSE_ENCODE["O"] + " " + \
                   morse_wave.MORSE_ENCODE["K"] + " " + \
                   morse_wave.MORSE_ENCODE["?"]
        assert result == expected

    def test_unknown_character(self):
        result = morse_wave.text_to_morse("A#B")
        # '#' is not in MORSE_ENCODE, should produce '?'
        assert "?" in result

    def test_empty_string(self):
        assert morse_wave.text_to_morse("") == ""

    def test_whitespace_only(self):
        assert morse_wave.text_to_morse("   ") == ""

    def test_single_character(self):
        assert morse_wave.text_to_morse("E") == "."

    def test_prosign_ar(self):
        result = morse_wave.text_to_morse("<AR>")
        assert result == morse_wave.PROSIGNS["<AR>"]

    def test_prosign_sk(self):
        result = morse_wave.text_to_morse("<SK>")
        assert result == morse_wave.PROSIGNS["<SK>"]


class TestMorseToText:
    """Tests for morse_to_text()."""

    def test_simple_word(self):
        assert morse_wave.morse_to_text("... --- ...") == "SOS"

    def test_multi_word(self):
        result = morse_wave.morse_to_text(".... . .-.. .-.. --- / .-- --- .-. .-.. -..")
        assert result == "HELLO WORLD"

    def test_empty_string(self):
        assert morse_wave.morse_to_text("") == ""

    def test_unknown_symbol(self):
        result = morse_wave.morse_to_text(".- ..---.- ..-")  # ..---.- is invalid
        assert "?" in result

    def test_whitespace_handling(self):
        assert morse_wave.morse_to_text("  ... --- ...  ") == "SOS"


class TestRoundtrip:
    """Test that encoding then decoding gives the original text."""

    def test_basic_roundtrip(self):
        text = "HELLO WORLD"
        morse = morse_wave.text_to_morse(text)
        decoded = morse_wave.morse_to_text(morse)
        assert decoded == text

    def test_alphanumeric_roundtrip(self):
        text = "ABC123XYZ789"
        morse = morse_wave.text_to_morse(text)
        decoded = morse_wave.morse_to_text(morse)
        assert decoded == text

    def test_punctuation_roundtrip(self):
        # Use characters that are in MORSE_ENCODE
        text = "HI. OK?"
        morse = morse_wave.text_to_morse(text)
        decoded = morse_wave.morse_to_text(morse)
        assert decoded == text.upper()

    def test_single_letter_roundtrip(self):
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            morse = morse_wave.text_to_morse(letter)
            decoded = morse_wave.morse_to_text(morse)
            assert decoded == letter, f"Roundtrip failed for '{letter}'"

    def test_single_digit_roundtrip(self):
        for digit in "0123456789":
            morse = morse_wave.text_to_morse(digit)
            decoded = morse_wave.morse_to_text(morse)
            assert decoded == digit, f"Roundtrip failed for '{digit}'"


# ─── Waveform Rendering Tests ────────────────────────────────────────────────

class TestRenderWaveform:
    """Tests for render_waveform()."""

    def test_produces_output(self):
        morse = morse_wave.text_to_morse("SOS")
        result = morse_wave.render_waveform(morse)
        assert len(result) > 0

    def test_empty_morse(self):
        result = morse_wave.render_waveform("")
        assert result == ""

    def test_amplitude_1(self):
        morse = morse_wave.text_to_morse("E")
        result = morse_wave.render_waveform(morse, amplitude=1)
        lines = result.strip().split("\n")
        # With amplitude=1, we expect 3 rows (2*1+1)
        assert len(lines) <= 3

    def test_amplitude_2(self):
        morse = morse_wave.text_to_morse("E")
        result = morse_wave.render_waveform(morse, amplitude=2)
        lines = result.strip().split("\n")
        # With amplitude=2, we expect up to 5 rows (2*2+1)
        assert len(lines) <= 5

    def test_contains_wave_characters(self):
        morse = morse_wave.text_to_morse("SOS")
        result = morse_wave.render_waveform(morse)
        # Should contain at least some drawing characters
        assert any(ch in result for ch in "╱╲─")


class TestRenderCompactWaveform:
    """Tests for render_compact_waveform()."""

    def test_produces_output(self):
        morse = morse_wave.text_to_morse("SOS")
        result = morse_wave.render_compact_waveform(morse)
        assert len(result) > 0

    def test_empty_morse(self):
        result = morse_wave.render_compact_waveform("")
        assert result == ""

    def test_contains_block_chars(self):
        morse = morse_wave.text_to_morse("SOS")
        result = morse_wave.render_compact_waveform(morse)
        # Should contain Unicode block characters
        assert any(ch in result for ch in " ░▒▓█")

    def test_contains_morse_annotation(self):
        morse = morse_wave.text_to_morse("SOS")
        result = morse_wave.render_compact_waveform(morse)
        # Should contain the dot/dash annotation
        assert "." in result or "-" in result

    def test_width_wrapping(self):
        morse = morse_wave.text_to_morse("HELLO WORLD THIS IS A LONG MESSAGE")
        result = morse_wave.render_compact_waveform(morse, width=40)
        # Long message should wrap across multiple lines
        lines = result.split("\n")
        assert len(lines) >= 2


# ─── Statistics Tests ─────────────────────────────────────────────────────────

class TestComputeStats:
    """Tests for compute_stats()."""

    def test_basic_stats(self):
        morse = morse_wave.text_to_morse("SOS")
        # S="..." (3 dots), O="---" (3 dashes), S="..." (3 dots)
        stats = morse_wave.compute_stats(morse)
        assert stats["dots"] == 6    # 3 from first S + 3 from second S
        assert stats["dashes"] == 3  # 3 from O
        assert stats["characters"] == 3  # S, O, S
        assert stats["words"] == 1

    def test_multi_word_stats(self):
        morse = morse_wave.text_to_morse("HI THERE")
        stats = morse_wave.compute_stats(morse)
        assert stats["words"] == 2
        assert stats["word_gaps"] == 1

    def test_timing_calculation(self):
        morse = morse_wave.text_to_morse("E")  # single dot
        stats = morse_wave.compute_stats(morse, wpm=15.0)
        # 1 unit at 15 WPM = 80ms
        assert stats["unit_ms"] == 80.0
        assert stats["dot_time_ms"] == 80.0

    def test_wpm_affects_timing(self):
        morse = morse_wave.text_to_morse("E")
        stats_15 = morse_wave.compute_stats(morse, wpm=15.0)
        stats_30 = morse_wave.compute_stats(morse, wpm=30.0)
        # At 30 WPM, timing should be half of 15 WPM
        assert stats_30["unit_ms"] == stats_15["unit_ms"] / 2


class TestFormatStats:
    """Tests for format_stats()."""

    def test_format_no_color(self):
        morse = morse_wave.text_to_morse("SOS")
        stats = morse_wave.compute_stats(morse)
        result = morse_wave.format_stats(stats, use_color=False)
        assert "SOS" not in result  # stats show counts, not the text
        assert "3" in result  # dot/dash count
        assert "1" in result  # word count

    def test_format_contains_key_fields(self):
        morse = morse_wave.text_to_morse("HELLO")
        stats = morse_wave.compute_stats(morse)
        result = morse_wave.format_stats(stats)
        assert "Characters" in result
        assert "Words" in result
        assert "Dots" in result
        assert "Dashes" in result
        assert "Total time" in result


# ─── Sine Wave Helper Tests ───────────────────────────────────────────────────

class TestMakeSineWave:
    """Tests for _make_sine_wave()."""

    def test_width_zero(self):
        result = morse_wave._make_sine_wave(0)
        assert result == []

    def test_positive_width(self):
        result = morse_wave._make_sine_wave(10)
        assert len(result) == 5  # 2*2+1 rows
        for row in result:
            assert len(row) == 10

    def test_custom_amplitude(self):
        result = morse_wave._make_sine_wave(5, amplitude=1)
        assert len(result) == 3  # 2*1+1 rows


# ─── File I/O Tests ───────────────────────────────────────────────────────────

class TestFileIO:
    """Tests for file input/output helpers."""

    def test_read_input_from_text_args(self):
        result = morse_wave._read_input(["HELLO", "WORLD"])
        assert result == "HELLO WORLD"

    def test_read_input_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("TEST INPUT")
            f.flush()
            path = f.name
        try:
            result = morse_wave._read_input([], file_path=path)
            assert result == "TEST INPUT"
        finally:
            os.unlink(path)

    def test_read_input_file_not_found(self):
        # Should exit with error
        try:
            morse_wave._read_input([], file_path="/nonexistent/file.txt")
            assert False, "Should have raised SystemExit"
        except SystemExit:
            pass

    def test_write_output_to_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            path = f.name
        try:
            morse_wave._write_output("Hello output", output_path=path)
            with open(path, "r") as f:
                content = f.read()
            assert "Hello output" in content
        finally:
            os.unlink(path)


# ─── Color Support Tests ──────────────────────────────────────────────────────

class TestColors:
    """Tests for the Colors utility class."""

    def test_no_color_env_var(self):
        old = os.environ.get("NO_COLOR")
        os.environ["NO_COLOR"] = "1"
        try:
            assert morse_wave.Colors.supports_color() is False
        finally:
            if old is None:
                del os.environ["NO_COLOR"]
            else:
                os.environ["NO_COLOR"] = old


# ─── Prosign Tests ────────────────────────────────────────────────────────────

class TestProsigns:
    """Tests for prosign support."""

    def test_prosign_encode(self):
        for name, code in morse_wave.PROSIGNS.items():
            morse = morse_wave.text_to_morse(name)
            assert morse == code, f"Prosign {name} encoded incorrectly"

    def test_prosign_decode_unique(self):
        """Test roundtrip for prosigns whose Morse codes don't overlap
        with standard character encodings."""
        # Some prosigns share Morse sequences with punctuation (e.g., <AR> = "+")
        # Only test prosigns with unique codes
        standard_codes = set(morse_wave.MORSE_ENCODE.values())
        for name, code in morse_wave.PROSIGNS.items():
            if code not in standard_codes:
                decoded = morse_wave.morse_to_text(code)
                assert decoded == name, f"Prosign {name} decoded as {decoded}"

    def test_prosign_in_text(self):
        """Test that prosigns can be embedded in regular text."""
        text = "CQ <SK>"
        morse = morse_wave.text_to_morse(text)
        # CQ should be encoded, and <SK> prosign should appear
        assert morse_wave.PROSIGNS["<SK>"] in morse


# ─── Edge Case Tests ──────────────────────────────────────────────────────────

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_single_space(self):
        result = morse_wave.text_to_morse(" ")
        assert result == ""

    def test_multiple_spaces(self):
        result = morse_wave.text_to_morse("A  B")
        # Multiple spaces should still produce valid morse
        morse = morse_wave.text_to_morse("A B")
        assert "A" in result or ".-" in result

    def test_unicode_text(self):
        # Characters not in the Morse table should produce '?'
        result = morse_wave.text_to_morse("ñ")
        assert "?" in result

    def test_very_long_text(self):
        # Should not crash on long input
        text = "PARIS " * 100
        morse = morse_wave.text_to_morse(text)
        decoded = morse_wave.morse_to_text(morse)
        assert decoded == text.upper().strip()

    def test_waveform_with_all_dots(self):
        morse = morse_wave.text_to_morse("EISH")  # all dots
        result = morse_wave.render_waveform(morse)
        assert len(result) > 0

    def test_waveform_with_all_dashes(self):
        morse = morse_wave.text_to_morse("TM0")  # all dashes
        result = morse_wave.render_waveform(morse)
        assert len(result) > 0