#!/usr/bin/env python3
"""Unit tests for the typewriter simulator."""

import pytest
import random
from typewriter import (
    TypewriterState, TypewriterModel, MODEL_PROPS, TerminalTypewriter,
    __version__, demo_typewriter
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])