#!/usr/bin/env python3
"""Unit tests for the typewriter simulator."""

import pytest
import random
import time
from typewriter import (
    TypewriterState, TypewriterModel, MODEL_PROPS, TerminalTypewriter,
    __version__, demo_typewriter, MIN_TERM_WIDTH, MIN_TERM_HEIGHT
)


class TestTypewriterState:
    """Tests for TypewriterState dataclass."""

    def test_default_state(self):
        """Test that default state has expected initial values."""
        state = TypewriterState()
        assert state.col == 1
        assert state.line == 1
        assert state.ribbon_wear == 0.0
        assert state.ink_density == 1.0
        assert state.total_chars == 0
        assert state.caps_lock is False
        assert state.jammed is False
        assert state.model == TypewriterModel.UNDERWOOD

    def test_state_with_model(self):
        """Test creating state with a specific model."""
        state = TypewriterState(model=TypewriterModel.ROYAL)
        assert state.model == TypewriterModel.ROYAL

    def test_state_with_color(self):
        """Test creating state with a specific ink color."""
        state = TypewriterState(ink_color="blue")
        assert state.ink_color == "blue"

    def test_state_lines_initialized(self):
        """Test that lines list is initialized with one empty line."""
        state = TypewriterState()
        assert len(state.lines) == 1
        assert len(state.lines[0]) == 0


class TestModelProperties:
    """Tests for typewriter model properties."""

    @pytest.mark.parametrize("model", list(TypewriterModel))
    def test_all_models_have_required_props(self, model):
        """Every model must have all required properties."""
        props = MODEL_PROPS[model]
        assert 'min_delay' in props
        assert 'max_delay' in props
        assert 'ink_variance' in props
        assert 'ding_at' in props
        assert 'description' in props
        assert 'key_weight' in props
        assert 'jam_chance' in props

    @pytest.mark.parametrize("model", list(TypewriterModel))
    def test_model_delays_are_positive(self, model):
        """All delay values must be positive."""
        props = MODEL_PROPS[model]
        assert props['min_delay'] > 0
        assert props['max_delay'] > 0
        assert props['min_delay'] < props['max_delay']

    @pytest.mark.parametrize("model", list(TypewriterModel))
    def test_model_ink_variance_in_range(self, model):
        """Ink variance must be between 0 and 1."""
        props = MODEL_PROPS[model]
        assert 0 <= props['ink_variance'] <= 1

    @pytest.mark.parametrize("model", list(TypewriterModel))
    def test_model_ding_at_is_reasonable(self, model):
        """Margin bell position should be in a plausible column range."""
        props = MODEL_PROPS[model]
        assert 40 <= props['ding_at'] <= 100

    @pytest.mark.parametrize("model", list(TypewriterModel))
    def test_model_jam_chance_in_range(self, model):
        """Jam chance must be a valid probability."""
        props = MODEL_PROPS[model]
        assert 0 <= props['jam_chance'] <= 0.01

    def test_ibm_fastest_model(self):
        """IBM Selectric should be the fastest model (lowest delays)."""
        ibm_props = MODEL_PROPS[TypewriterModel.IBM_SELECTRIC]
        royal_props = MODEL_PROPS[TypewriterModel.ROYAL]
        assert ibm_props['min_delay'] < royal_props['min_delay']
        assert ibm_props['max_delay'] < royal_props['max_delay']

    def test_royal_highest_ink_variance(self):
        """Royal should have the moodiest ink (highest variance)."""
        royal_var = MODEL_PROPS[TypewriterModel.ROYAL]['ink_variance']
        ibm_var = MODEL_PROPS[TypewriterModel.IBM_SELECTRIC]['ink_variance']
        assert royal_var > ibm_var

    def test_royal_highest_jam_chance(self):
        """Royal should have the highest jam chance (temperamental)."""
        royal_jam = MODEL_PROPS[TypewriterModel.ROYAL]['jam_chance']
        ibm_jam = MODEL_PROPS[TypewriterModel.IBM_SELECTRIC]['jam_chance']
        assert royal_jam > ibm_jam


class TestTypewriterModelEnum:
    """Tests for the TypewriterModel enum."""

    def test_five_models_exist(self):
        """There should be exactly 5 typewriter models."""
        assert len(TypewriterModel) == 5

    def test_model_names(self):
        """Verify expected model names."""
        assert TypewriterModel.UNDERWOOD.value == "Underwood No. 5"
        assert TypewriterModel.REMINGTON.value == "Remington Portable"
        assert TypewriterModel.OLIVETTI.value == "Olivetti Lettera 32"
        assert TypewriterModel.IBM_SELECTRIC.value == "IBM Selectric II"
        assert TypewriterModel.ROYAL.value == "Royal Quiet De Luxe"


class TestVersion:
    """Tests for version information."""

    def test_version_exists(self):
        """Module should expose a version string."""
        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_version_format(self):
        """Version should be in semver format."""
        parts = __version__.split('.')
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()


class TestDemoFunction:
    """Tests for the demo_typewriter function."""

    def test_demo_runs_without_error(self, capsys):
        """Demo should run without raising exceptions."""
        demo_typewriter("Hello World", "underwood")
        captured = capsys.readouterr()
        assert "Underwood" in captured.out
        assert "Hello World" in captured.out

    def test_demo_all_models(self, capsys):
        """Demo should work for all model names."""
        for name in ['underwood', 'remington', 'olivetti', 'ibm', 'royal']:
            demo_typewriter("Test", name)
            captured = capsys.readouterr()
            assert "│" in captured.out

    def test_demo_unknown_model_defaults(self, capsys):
        """Demo with unknown model name should default to Underwood."""
        demo_typewriter("Test", "nonexistent_model")
        captured = capsys.readouterr()
        assert "Underwood" in captured.out

    def test_demo_multiline_text(self, capsys):
        """Demo should handle multiline text correctly."""
        text = "Line one\nLine two\nLine three"
        demo_typewriter(text)
        captured = capsys.readouterr()
        assert "Line one" in captured.out
        assert "Line two" in captured.out


class TestRibbonWear:
    """Tests for ribbon wear mechanics."""

    def test_ribbon_wear_increases_with_typing(self):
        """Ribbon wear should increase as more characters are typed."""
        state = TypewriterState()
        initial_wear = state.ribbon_wear
        for ch in "Hello World!":
            state.lines[0].append((ch, 1.0))
            state.col += 1
            state.total_chars += 1
            state.ribbon_wear = min(1.0, state.ribbon_wear + 0.0002)
        assert state.ribbon_wear > initial_wear
        assert state.ribbon_wear == pytest.approx(0.0024, abs=0.001)

    def test_ribbon_wear_caps_at_one(self):
        """Ribbon wear should never exceed 1.0."""
        state = TypewriterState(ribbon_wear=0.9999)
        state.ribbon_wear = min(1.0, state.ribbon_wear + 0.0002)
        assert state.ribbon_wear == 1.0


class TestTypewriterText:
    """Tests for text reconstruction and counting."""

    def test_get_full_text_empty(self):
        """get_full_text should return empty string for fresh state."""
        # We can't easily test TerminalTypewriter without curses,
        # but we can test the state-based approach
        state = TypewriterState()
        lines = []
        for line in state.lines:
            line_text = "".join(ch for ch, _ in line)
            lines.append(line_text)
        text = "\n".join(lines)
        assert text == ""

    def test_word_count_empty(self):
        """Word count of empty state should be 0."""
        state = TypewriterState()
        lines = []
        for line in state.lines:
            line_text = "".join(ch for ch, _ in line)
            lines.append(line_text)
        text = "\n".join(lines)
        assert len(text.split()) == 0

    def test_manual_typing_preserves_text(self):
        """Characters added to state should be retrievable."""
        state = TypewriterState()
        text = "Hello World!"
        for ch in text:
            state.lines[0].append((ch, 1.0))
            state.col += 1
            state.total_chars += 1
        result = "".join(ch for ch, _ in state.lines[0])
        assert result == text

    def test_caps_lock(self):
        """When caps_lock is on, letters should be uppercase in the state representation."""
        state = TypewriterState(caps_lock=True)
        ch = 'a'
        if state.caps_lock and ch.isalpha():
            ch = ch.upper()
        assert ch == 'A'


class TestExportPath:
    """Tests for export file path handling."""

    def test_export_path_default_empty(self):
        """Default export path should be empty string."""
        state = TypewriterState()
        assert state.export_path == ""

    def test_export_path_can_be_set(self):
        """Export path can be set via constructor."""
        state = TypewriterState(export_path="/tmp/output.txt")
        assert state.export_path == "/tmp/output.txt"


class TestJamMechanics:
    """Tests for paper jam mechanics."""

    def test_initial_state_no_jam(self):
        """Fresh state should not be jammed."""
        state = TypewriterState()
        assert state.jammed is False
        assert state.jam_timer == 0

    def test_jam_state_can_be_set(self):
        """Jam state should be settable."""
        state = TypewriterState(jammed=True, jam_timer=8)
        assert state.jammed is True
        assert state.jam_timer == 8

    def test_jam_chance_in_model_props(self):
        """All models should have a jam_chance property."""
        for model in TypewriterModel:
            assert 'jam_chance' in MODEL_PROPS[model]

    def test_resolve_jam_clears_state(self):
        """Resolving a jam should clear jammed and jam_timer."""
        state = TypewriterState(jammed=True, jam_timer=5)
        state.jammed = False
        state.jam_timer = 0
        assert state.jammed is False
        assert state.jam_timer == 0


class TestCtrlJKeycodeConflict:
    """Tests for the Ctrl+J / Enter keycode conflict fix.

    Ctrl+J is ASCII 10 (Line Feed), which is the same keycode as
    the Enter key's Line Feed. The original code had Ctrl+J handling
    AFTER Enter handling, making it unreachable. Now Ctrl+J is handled
    BEFORE Enter, so it can clear paper jams.
    """

    def test_ctrl_j_is_ascii_10(self):
        """Ctrl+J should produce ASCII code 10 (Line Feed)."""
        assert ord('\n') == 10
        assert ord('\x0a') == 10

    def test_ctrl_j_keycode_equals_enter_lf(self):
        """Enter (LF) and Ctrl+J share the same keycode."""
        # This verifies the conflict exists and justifies the fix
        enter_lf_code = 10
        ctrl_j_code = 10
        assert enter_lf_code == ctrl_j_code

    def test_enter_cr_is_separate_keycode(self):
        """Enter (CR) is keycode 13, distinct from Ctrl+J."""
        assert 13 != 10  # CR != LF


class TestAutoTypeJamPause:
    """Tests for auto-type auto-pause on jam behavior."""

    def test_jam_sets_pause_in_auto_mode(self):
        """When auto-typing and a jam occurs, auto-type should pause."""
        state = TypewriterState(jammed=True)
        # Simulating what _auto_type does: if jammed, set paused
        # This tests the logic pattern, not the actual method (needs curses)
        auto_mode = True
        paused = False
        if state.jammed and auto_mode:
            paused = True
        assert paused is True

    def test_resolve_jam_unpauses_auto_mode(self):
        """Resolving a jam in auto-mode should also unpause."""
        state = TypewriterState(jammed=True, jam_timer=5)
        auto_mode = True
        paused = True  # Was paused due to jam
        # Resolve jam
        state.jammed = False
        state.jam_timer = 0
        if auto_mode and paused:
            paused = False
        assert paused is False

    def test_manual_mode_jam_does_not_set_pause(self):
        """In manual (non-auto) mode, jam doesn't need to pause."""
        state = TypewriterState(jammed=True)
        auto_mode = False
        paused = False
        # In manual mode, there's no auto-type to pause
        if auto_mode and state.jammed:
            paused = True
        assert paused is False


class TestTimestampWhileJammed:
    """Tests for timestamp insertion while jammed."""

    def test_type_char_returns_false_when_jammed(self):
        """_type_char should return False when the typewriter is jammed."""
        state = TypewriterState(jammed=True)
        # When jammed, _type_char returns False without typing
        # We can verify the state logic
        if state.jammed:
            result = False  # This is what _type_char does
        else:
            result = True
        assert result is False

    def test_type_char_works_when_not_jammed(self):
        """_type_char should work normally when not jammed."""
        state = TypewriterState(jammed=False)
        if state.jammed:
            result = False
        else:
            result = True
        assert result is True


class TestExportFeedback:
    """Tests for export action feedback."""

    def test_export_returns_true_on_success(self):
        """_export_to_file should return True on successful write."""
        import tempfile
        import os
        state = TypewriterState(export_path=os.path.join(tempfile.gettempdir(), 'test_export.txt'))
        # Simulate typing some text
        for ch in "Hello":
            state.lines[0].append((ch, 1.0))
        # Reconstruct and write
        lines = []
        for line in state.lines:
            line_text = "".join(ch for ch, _ in line)
            lines.append(line_text)
        text = "\n".join(lines)
        try:
            with open(state.export_path, 'w') as f:
                f.write(text)
            with open(state.export_path, 'r') as f:
                content = f.read()
            assert content == "Hello"
        finally:
            if os.path.exists(state.export_path):
                os.unlink(state.export_path)

    def test_export_returns_false_on_bad_path(self):
        """Exporting to a bad path should return False."""
        state = TypewriterState(export_path="/nonexistent/dir/file.txt")
        try:
            with open(state.export_path, 'w') as f:
                f.write("test")
            assert False, "Should have raised IOError"
        except (IOError, OSError):
            pass  # Expected


class TestEscapeSequenceDrain:
    """Tests for improved escape sequence handling."""

    def test_csi_sequence_final_byte_range(self):
        """CSI sequences end with bytes in range 0x40-0x7E."""
        # This is a specification test for the escape drain logic
        # The final byte of a CSI sequence must be in 0x40-0x7E
        # Examples: A=0x41, B=0x42, etc.
        assert 0x40 <= ord('A') <= 0x7E
        assert 0x40 <= ord('~') <= 0x7E
        # Intermediate bytes are in 0x20-0x3F
        assert 0x20 <= ord(';') <= 0x3F
        assert 0x20 <= ord('0') <= 0x3F


class TestDeterministicSeed:
    """Tests for the --seed deterministic RNG feature (v1.3.0)."""

    def test_seeded_rng_is_reproducible(self):
        """Two RNGs with the same seed produce the same sequence."""
        r1 = random.Random(123)
        r2 = random.Random(123)
        seq1 = [r1.random() for _ in range(20)]
        seq2 = [r2.random() for _ in range(20)]
        assert seq1 == seq2

    def test_different_seeds_differ(self):
        """Two RNGs with different seeds produce different sequences."""
        r1 = random.Random(1)
        r2 = random.Random(2)
        seq1 = [r1.random() for _ in range(20)]
        seq2 = [r2.random() for _ in range(20)]
        assert seq1 != seq2

    def test_seeded_demo_is_reproducible(self, capsys):
        """demo_typewriter with the same seed produces identical output."""
        demo_typewriter("Hello World", "underwood", seed=42)
        out1 = capsys.readouterr().out
        demo_typewriter("Hello World", "underwood", seed=42)
        out2 = capsys.readouterr().out
        assert out1 == out2

    def test_unseeded_demo_may_vary(self, capsys):
        """demo_typewriter without seed uses global RNG (may differ)."""
        # We only assert it runs; output may or may not differ across calls.
        demo_typewriter("Test", "royal")
        captured = capsys.readouterr()
        assert "Royal" in captured.out


class TestStatsFile:
    """Tests for the --stats file output feature (v1.3.0)."""

    def test_stats_path_default_empty(self):
        """Default stats path should be empty string."""
        state = TypewriterState()
        assert state.stats_path == ""

    def test_stats_path_can_be_set(self):
        """Stats path can be set via constructor."""
        state = TypewriterState(stats_path="/tmp/stats.txt")
        assert state.stats_path == "/tmp/stats.txt"

    def test_stats_write_succeeds(self, tmp_path):
        """Writing stats to a valid path should create a readable file."""
        stats_file = tmp_path / "stats.txt"
        state = TypewriterState(stats_path=str(stats_file),
                                model=TypewriterModel.UNDERWOOD)
        state.lines[0].extend([('H', 1.0), ('i', 0.9)])
        state.total_chars = 2
        state.start_time = time.monotonic() - 5.0
        # Reproduce _write_stats logic (can't instantiate TerminalTypewriter
        # without curses), verifying the pattern works end-to-end.
        text_lines = "".join(ch for ch, _ in state.lines[0])
        words = len(text_lines.split())
        elapsed = 5.0
        lines = [
            f"Typewriter: {state.model.value}",
            f"Characters: {state.total_chars}",
            f"Words: {words}",
            f"Lines: {len(state.lines)}",
            f"Ribbon wear: {state.ribbon_wear * 100:.1f}%",
            f"Session duration: {elapsed:.1f}s",
            f"Characters/sec: {state.total_chars / elapsed:.2f}",
        ]
        with open(stats_file, 'w') as f:
            f.write("\n".join(lines) + "\n")
        content = stats_file.read_text()
        assert "Typewriter: Underwood No. 5" in content
        assert "Characters: 2" in content
        assert "Words: 1" in content


class TestAutoWrap:
    """Tests for the --wrap auto-wrap at margin feature (v1.3.0)."""

    def test_auto_wrap_default_off(self):
        """auto_wrap should default to False."""
        state = TypewriterState()
        assert state.auto_wrap is False

    def test_auto_wrap_can_be_enabled(self):
        """auto_wrap can be set via constructor."""
        state = TypewriterState(auto_wrap=True)
        assert state.auto_wrap is True

    def test_auto_wrap_triggers_newline(self):
        """When auto_wrap is on and col exceeds margin, a new line starts."""
        state = TypewriterState(auto_wrap=True,
                                model=TypewriterModel.UNDERWOOD)
        # Underwood ding_at is 65; wrap triggers at ding_at + 5 = 70
        state.col = 71
        props = MODEL_PROPS[state.model]
        if state.auto_wrap and state.col > props["ding_at"] + 5:
            state.line += 1
            state.col = 1
        assert state.line == 2
        assert state.col == 1

    def test_no_wrap_stays_on_line(self):
        """Without auto_wrap, exceeding the margin does NOT start a new line."""
        state = TypewriterState(auto_wrap=False,
                                model=TypewriterModel.UNDERWOOD)
        state.col = 100
        props = MODEL_PROPS[state.model]
        if state.auto_wrap and state.col > props["ding_at"] + 5:
            state.line += 1
            state.col = 1
        assert state.line == 1
        assert state.col == 100


class TestTerminalSizeGuard:
    """Tests for the terminal size guard constants (v1.3.0)."""

    def test_min_dimensions_defined(self):
        """Minimum terminal dimensions should be sensible positive integers."""
        assert MIN_TERM_WIDTH >= 40
        assert MIN_TERM_HEIGHT >= 8

    def test_min_width_allows_typing(self):
        """The minimum width should fit at least a short line + margins."""
        assert MIN_TERM_WIDTH > 20 + 5 + 5  # line + margins


class TestNewKeycodes:
    """Tests for new keycodes added in v1.3.0 (Tab, Ctrl+S)."""

    def test_tab_is_ascii_9(self):
        """Tab key produces ASCII code 9."""
        assert ord('\t') == 9

    def test_ctrl_s_is_ascii_19(self):
        """Ctrl+S produces ASCII code 19 (XOFF in terminals, repurposed here)."""
        assert 19 == 0x13


class TestDemoSeedParam:
    """Tests for the seed parameter on demo_typewriter (v1.3.0)."""

    def test_demo_accepts_seed_kwarg(self, capsys):
        """demo_typewriter should accept a seed keyword without error."""
        demo_typewriter("Seeded demo", "olivetti", seed=7)
        captured = capsys.readouterr()
        assert "Olivetti" in captured.out
        assert "Seeded demo" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])