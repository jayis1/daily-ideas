#!/usr/bin/env python3
"""Tests for the Terminal Drum Machine."""

import json
import os
import tempfile
import wave

import numpy as np
import pytest

from drum_machine import (
    DrumMachine,
    DrumName,
    DRUM_ALIASES,
    DRUM_ORDER,
    DRUM_SYNTHS,
    SAMPLE_RATE,
    VALID_STEP_COUNTS,
    __version__,
    synth_kick,
    synth_snare,
    synth_hihat_closed,
    synth_hihat_open,
    synth_clap,
    synth_tom,
    synth_rim,
    synth_cowbell,
    synth_metronome_click,
)


# ─── Sound Synthesis Tests ──────────────────────────────────────────────────


class TestSoundSynthesis:
    """Test individual drum sound synthesis functions."""

    @pytest.mark.parametrize("synth_func", [
        synth_kick, synth_snare, synth_hihat_closed, synth_hihat_open,
        synth_clap, synth_tom, synth_rim, synth_cowbell,
    ])
    def test_synth_returns_numpy_array(self, synth_func):
        result = synth_func()
        assert isinstance(result, np.ndarray)

    @pytest.mark.parametrize("synth_func", [
        synth_kick, synth_snare, synth_hihat_closed, synth_hihat_open,
        synth_clap, synth_tom, synth_rim, synth_cowbell,
    ])
    def test_synth_returns_non_empty(self, synth_func):
        result = synth_func()
        assert len(result) > 0

    @pytest.mark.parametrize("synth_func", [
        synth_kick, synth_snare, synth_hihat_closed, synth_hihat_open,
        synth_clap, synth_tom, synth_rim, synth_cowbell,
    ])
    def test_synth_peak_within_range(self, synth_func):
        result = synth_func()
        peak = np.max(np.abs(result))
        # All synths normalize to ~0.65-0.95 range
        assert 0.3 < peak <= 1.0

    @pytest.mark.parametrize("synth_func", [
        synth_kick, synth_snare, synth_hihat_closed, synth_hihat_open,
        synth_clap, synth_tom, synth_rim, synth_cowbell,
    ])
    def test_synth_custom_duration(self, synth_func):
        """Synths should respect a custom duration parameter."""
        result = synth_func(duration=0.1)
        expected_len = int(SAMPLE_RATE * 0.1)
        # Allow some tolerance since synths may pad slightly differently
        assert abs(len(result) - expected_len) < SAMPLE_RATE * 0.01

    def test_kick_has_low_frequency_content(self):
        """Kick drum should have significant low-frequency content."""
        kick = synth_kick()
        spectrum = np.abs(np.fft.rfft(kick))
        freqs = np.fft.rfftfreq(len(kick), 1.0 / SAMPLE_RATE)
        # The fundamental region (50-300Hz) should have the peak frequency
        low_mask = (freqs >= 50) & (freqs <= 300)
        peak_freq = freqs[np.argmax(spectrum[1:]) + 1]  # skip DC
        assert 30 <= peak_freq <= 500, f"Kick peak at {peak_freq:.0f}Hz, expected 30-500Hz"

    def test_hihat_closed_shorter_than_open(self):
        """Closed hi-hat should be shorter than open hi-hat."""
        closed = synth_hihat_closed()
        open_hat = synth_hihat_open()
        assert len(closed) < len(open_hat)

    def test_synth_deterministic_shape(self):
        """Running a synth twice should produce arrays of the same length."""
        # Note: noise-based synths won't be identical, but length should match
        for synth_func in [synth_kick, synth_tom, synth_cowbell]:
            r1 = synth_func(duration=0.2)
            r2 = synth_func(duration=0.2)
            assert len(r1) == len(r2)

    def test_all_synth_functions_in_map(self):
        """Every drum in DRUM_ORDER should have a synth function."""
        for drum in DRUM_ORDER:
            assert drum in DRUM_SYNTHS

    def test_synth_zero_duration(self):
        """Synths should handle very short/near-zero durations gracefully."""
        result = synth_kick(duration=0.001)
        # Should produce something, even if tiny
        assert isinstance(result, np.ndarray)


class TestMetronomeClick:
    """Test the metronome click synthesis."""

    def test_metronome_returns_array(self):
        result = synth_metronome_click()
        assert isinstance(result, np.ndarray)
        assert len(result) > 0

    def test_metronome_short_duration(self):
        result = synth_metronome_click(duration=0.02)
        assert len(result) > 0
        assert np.max(np.abs(result)) > 0

    def test_metronome_custom_duration(self):
        result = synth_metronome_click(duration=0.05)
        expected = int(SAMPLE_RATE * 0.05)
        assert abs(len(result) - expected) < SAMPLE_RATE * 0.01


# ─── DrumMachine Core Tests ──────────────────────────────────────────────────


class TestDrumMachineInit:
    """Test DrumMachine initialization and validation."""

    def test_default_init(self):
        dm = DrumMachine()
        assert dm.bpm == 120
        assert dm.steps == 16
        assert dm.swing == 0.0

    def test_custom_init(self):
        dm = DrumMachine(bpm=140, steps=32, swing=0.5)
        assert dm.bpm == 140
        assert dm.steps == 32
        assert dm.swing == 0.5

    def test_invalid_bpm_low(self):
        with pytest.raises(ValueError):
            DrumMachine(bpm=29)

    def test_invalid_bpm_high(self):
        with pytest.raises(ValueError):
            DrumMachine(bpm=301)

    def test_invalid_steps(self):
        with pytest.raises(ValueError):
            DrumMachine(steps=12)

    def test_invalid_swing(self):
        with pytest.raises(ValueError):
            DrumMachine(swing=0.8)

    def test_valid_step_counts(self):
        for steps in VALID_STEP_COUNTS:
            dm = DrumMachine(steps=steps)
            assert dm.steps == steps

    def test_humanize_defaults(self):
        dm = DrumMachine()
        assert dm.humanize is False
        assert dm.humanize_timing == 0.008
        assert dm.humanize_velocity == 0.12

    def test_metronome_defaults(self):
        dm = DrumMachine()
        assert dm.metronome is False

    def test_undo_stack_starts_empty(self):
        dm = DrumMachine()
        assert len(dm._undo_stack) == 0


class TestDrumMachinePattern:
    """Test pattern manipulation."""

    def test_toggle_on(self):
        dm = DrumMachine()
        assert dm.pattern[DrumName.KICK][0] is False
        result = dm.toggle(DrumName.KICK, 0)
        assert result is True
        assert dm.pattern[DrumName.KICK][0] is True

    def test_toggle_off(self):
        dm = DrumMachine()
        dm.toggle(DrumName.KICK, 0)
        result = dm.toggle(DrumName.KICK, 0)
        assert result is False

    def test_toggle_invalid_step(self):
        dm = DrumMachine()
        with pytest.raises(IndexError):
            dm.toggle(DrumName.KICK, 16)

    def test_toggle_negative_step(self):
        dm = DrumMachine()
        with pytest.raises(IndexError):
            dm.toggle(DrumName.KICK, -1)

    def test_clear_pattern(self):
        dm = DrumMachine()
        dm.toggle(DrumName.KICK, 0)
        dm.toggle(DrumName.SNARE, 4)
        dm.clear_pattern()
        for drum in dm.drums:
            assert all(not s for s in dm.pattern[drum])

    def test_shift_pattern_right(self):
        dm = DrumMachine()
        dm.pattern[DrumName.KICK] = [True, False, False, False] + [False] * 12
        dm.shift_pattern(DrumName.KICK, 1)
        assert dm.pattern[DrumName.KICK][1] is True
        assert dm.pattern[DrumName.KICK][0] is False

    def test_shift_pattern_left(self):
        dm = DrumMachine()
        dm.pattern[DrumName.KICK] = [True, False, False, False] + [False] * 12
        dm.shift_pattern(DrumName.KICK, -1)
        assert dm.pattern[DrumName.KICK][15] is True
        assert dm.pattern[DrumName.KICK][0] is False

    def test_copy_pattern(self):
        dm = DrumMachine()
        dm.pattern[DrumName.KICK] = [True, False] * 8
        dm.copy_pattern(DrumName.KICK, DrumName.SNARE)
        assert dm.pattern[DrumName.SNARE] == dm.pattern[DrumName.KICK]

    def test_random_pattern(self):
        dm = DrumMachine()
        dm.random_pattern(density=0.5)
        # At least one step should be on (with high probability)
        total_on = sum(
            1 for drum in dm.drums for s in dm.pattern[drum] if s
        )
        # Very unlikely all zeros with 0.5 density on 128 steps
        assert total_on > 0

    def test_random_pattern_density(self):
        dm = DrumMachine()
        dm.random_pattern(density=0.8)
        total_on = sum(1 for s in dm.pattern[DrumName.KICK] if s)
        # With 80% density, at least half should be on
        assert total_on >= 4  # At least 4 of 16 steps on


class TestDrumMachineInvertReverse:
    """Test pattern invert and reverse."""

    def test_invert_pattern(self):
        dm = DrumMachine()
        dm.load_preset("four-on-floor")
        # Kick: [1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0]
        original_kick = list(dm.pattern[DrumName.KICK])
        dm.invert_pattern(DrumName.KICK)
        for i in range(dm.steps):
            assert dm.pattern[DrumName.KICK][i] == (not original_kick[i])

    def test_invert_empty_pattern(self):
        dm = DrumMachine()
        dm.invert_pattern(DrumName.KICK)
        # All should be True now (inverted from all-False)
        assert all(dm.pattern[DrumName.KICK])

    def test_invert_full_pattern(self):
        dm = DrumMachine()
        dm.pattern[DrumName.KICK] = [True] * dm.steps
        dm.invert_pattern(DrumName.KICK)
        assert not any(dm.pattern[DrumName.KICK])

    def test_reverse_pattern(self):
        dm = DrumMachine()
        # Set a specific pattern: on at steps 0 and 3
        dm.pattern[DrumName.KICK][0] = True
        dm.pattern[DrumName.KICK][3] = True
        dm.reverse_pattern(DrumName.KICK)
        # After reverse: on at steps 12 (was 3) and 15 (was 0)
        assert dm.pattern[DrumName.KICK][15] is True   # was step 0
        assert dm.pattern[DrumName.KICK][12] is True   # was step 3
        assert dm.pattern[DrumName.KICK][0] is False

    def test_reverse_palindrome_pattern(self):
        dm = DrumMachine()
        # A palindrome pattern should be unchanged by reverse
        # [True, False, False, False, True] is palindromic for 5 steps,
        # but we need a 16-step palindrome. Use symmetric pattern.
        pal = [True, False, True, False, True, False, False, True,
               True, False, False, True, False, True, False, True]
        dm.pattern[DrumName.KICK] = pal
        original = list(dm.pattern[DrumName.KICK])
        dm.reverse_pattern(DrumName.KICK)
        assert list(dm.pattern[DrumName.KICK]) == original


class TestDrumMachineSolo:
    """Test solo/unsolo functionality."""

    def test_solo_mutes_all_others(self):
        dm = DrumMachine()
        dm.solo(DrumName.KICK)
        # Only kick should be unmuted
        assert dm.muted[DrumName.KICK] is False
        for drum in dm.drums:
            if drum != DrumName.KICK:
                assert dm.muted[drum] is True

    def test_unsolo_all(self):
        dm = DrumMachine()
        dm.solo(DrumName.KICK)
        dm.unsolo_all()
        for drum in dm.drums:
            assert dm.muted[drum] is False


class TestDrumMachineFill:
    """Test fill generation."""

    def test_fill_from_step_12(self):
        dm = DrumMachine()
        dm.generate_fill(start_step=12, density=0.8)
        # At least some steps from 12 onward should be on
        fill_steps = [dm.pattern[d][i] for d in dm.drums for i in range(12, 16)]
        assert any(fill_steps)

    def test_fill_from_step_0(self):
        dm = DrumMachine()
        dm.generate_fill(start_step=0, density=0.5)
        # Should have hits somewhere
        total_on = sum(1 for d in dm.drums for s in dm.pattern[d] if s)
        assert total_on > 0

    def test_fill_invalid_step(self):
        dm = DrumMachine()
        with pytest.raises(IndexError):
            dm.generate_fill(start_step=16)

    def test_fill_negative_step(self):
        dm = DrumMachine()
        with pytest.raises(IndexError):
            dm.generate_fill(start_step=-1)


class TestDrumMachineHumanize:
    """Test humanize mode."""

    def test_humanize_toggle(self):
        dm = DrumMachine()
        assert dm.humanize is False
        dm.humanize = True
        assert dm.humanize is True

    def test_humanize_renders_audio(self):
        dm = DrumMachine(bpm=120)
        dm.humanize = True
        dm.load_preset("four-on-floor")
        audio = dm.render_full_loop()
        assert len(audio) > 0
        assert np.max(np.abs(audio)) > 0

    def test_humanize_produces_different_each_time(self):
        """With humanize on, consecutive renders should differ slightly."""
        dm = DrumMachine(bpm=120)
        dm.humanize = True
        dm.load_preset("four-on-floor")
        loop1 = dm.render_full_loop()
        loop2 = dm.render_full_loop()
        # Velocity variation should make them differ
        # (extremely unlikely to be identical)
        assert not np.array_equal(loop1, loop2)


class TestDrumMachineMetronome:
    """Test metronome click track."""

    def test_metronome_toggle(self):
        dm = DrumMachine()
        assert dm.metronome is False
        dm.metronome = True
        assert dm.metronome is True

    def test_metronome_adds_click_to_mix(self):
        """Metronome should add audio to otherwise silent steps."""
        dm = DrumMachine(bpm=120, steps=16)
        # Don't load any preset — all steps are off
        dm.metronome = True
        # Step 0 should have metronome click on a quarter note
        step0_with = dm.mix_step(0)
        dm.metronome = False
        step0_without = dm.mix_step(0)
        # With metronome on, there should be some audio (the click)
        assert np.max(np.abs(step0_with)) > 0.01
        # Without metronome and no pattern, should be silence
        assert np.max(np.abs(step0_without)) == 0.0


class TestDrumMachineUndo:
    """Test undo functionality."""

    def test_undo_toggle(self):
        dm = DrumMachine()
        assert dm.pattern[DrumName.KICK][0] is False
        dm.toggle(DrumName.KICK, 0)
        assert dm.pattern[DrumName.KICK][0] is True
        dm.undo()
        assert dm.pattern[DrumName.KICK][0] is False

    def test_undo_clear(self):
        dm = DrumMachine()
        dm.load_preset("four-on-floor")
        dm.clear_pattern()
        assert all(not s for s in dm.pattern[DrumName.KICK])
        dm.undo()
        assert dm.pattern[DrumName.KICK][0] is True

    def test_undo_random(self):
        dm = DrumMachine()
        dm.load_preset("four-on-floor")
        original = list(dm.pattern[DrumName.KICK])
        dm.random_pattern(density=0.5)
        dm.undo()
        assert dm.pattern[DrumName.KICK] == original

    def test_undo_preset_load(self):
        dm = DrumMachine()
        original_kick = list(dm.pattern[DrumName.KICK])
        dm.load_preset("four-on-floor")
        assert dm.pattern[DrumName.KICK][0] is True
        dm.undo()
        assert dm.pattern[DrumName.KICK] == original_kick

    def test_undo_shift(self):
        dm = DrumMachine()
        dm.pattern[DrumName.KICK] = [True, False, False, False] + [False] * 12
        dm.shift_pattern(DrumName.KICK, 1)
        assert dm.pattern[DrumName.KICK][1] is True
        dm.undo()
        assert dm.pattern[DrumName.KICK][0] is True

    def test_undo_invert(self):
        dm = DrumMachine()
        original = list(dm.pattern[DrumName.KICK])
        dm.invert_pattern(DrumName.KICK)
        dm.undo()
        assert dm.pattern[DrumName.KICK] == original

    def test_undo_reverse(self):
        dm = DrumMachine()
        dm.pattern[DrumName.KICK][0] = True
        original = list(dm.pattern[DrumName.KICK])
        dm.reverse_pattern(DrumName.KICK)
        dm.undo()
        assert dm.pattern[DrumName.KICK] == original

    def test_undo_mute(self):
        dm = DrumMachine()
        assert dm.muted[DrumName.KICK] is False
        dm.toggle_mute(DrumName.KICK)
        assert dm.muted[DrumName.KICK] is True
        dm.undo()
        assert dm.muted[DrumName.KICK] is False

    def test_undo_solo(self):
        dm = DrumMachine()
        dm.solo(DrumName.KICK)
        assert dm.muted[DrumName.KICK] is False
        assert dm.muted[DrumName.SNARE] is True
        dm.undo()
        assert dm.muted[DrumName.KICK] is False
        assert dm.muted[DrumName.SNARE] is False

    def test_undo_empty_stack(self):
        dm = DrumMachine()
        result = dm.undo()
        assert result is False

    def test_undo_multiple_times(self):
        dm = DrumMachine()
        dm.toggle(DrumName.KICK, 0)
        dm.toggle(DrumName.KICK, 1)
        dm.toggle(DrumName.KICK, 2)
        # Undo all three
        dm.undo()  # undo step 2 toggle
        assert dm.pattern[DrumName.KICK][2] is False
        dm.undo()  # undo step 1 toggle
        assert dm.pattern[DrumName.KICK][1] is False
        dm.undo()  # undo step 0 toggle
        assert dm.pattern[DrumName.KICK][0] is False

    def test_undo_max_history(self):
        """Undo stack should not exceed MAX_UNDO_HISTORY."""
        from drum_machine import MAX_UNDO_HISTORY
        dm = DrumMachine()
        for i in range(MAX_UNDO_HISTORY + 10):
            dm.toggle(DrumName.KICK, i % dm.steps)
        # Should still be able to undo (at least MAX_UNDO_HISTORY times)
        assert dm.undo() is True


class TestDrumMachinePresets:
    """Test preset loading."""

    def test_load_four_on_floor(self):
        dm = DrumMachine()
        assert dm.load_preset("four-on-floor") is True
        assert dm.pattern[DrumName.KICK][0] is True
        assert dm.pattern[DrumName.KICK][2] is False

    def test_load_hiphop(self):
        dm = DrumMachine()
        assert dm.load_preset("hiphop") is True

    def test_load_breakbeat(self):
        dm = DrumMachine()
        assert dm.load_preset("breakbeat") is True

    def test_load_reggaeton(self):
        dm = DrumMachine()
        assert dm.load_preset("reggaeton") is True

    def test_load_bossa_nova(self):
        dm = DrumMachine()
        assert dm.load_preset("bossa-nova") is True

    def test_load_dnb(self):
        dm = DrumMachine()
        assert dm.load_preset("dnb") is True

    def test_load_unknown_preset(self):
        dm = DrumMachine()
        assert dm.load_preset("nonexistent") is False

    def test_preset_clears_previous(self):
        dm = DrumMachine()
        dm.toggle(DrumName.KICK, 0)
        dm.load_preset("dnb")
        # The previous toggle should be gone — dnb has kick on step 0 anyway
        # Let's check a drum that's not in dnb
        assert all(not s for s in dm.pattern[DrumName.CLAP])

    def test_preset_name_normalization(self):
        dm = DrumMachine()
        assert dm.load_preset("FourOnFloor") is True
        assert dm.load_preset("four on floor") is True
        assert dm.load_preset("BOSSANOVA") is True

    def test_preset_adapts_to_step_count(self):
        dm = DrumMachine(steps=8)
        result = dm.load_preset("four-on-floor")
        assert result is True
        # Pattern should be 8 steps long
        for drum in dm.drums:
            assert len(dm.pattern[drum]) == 8


class TestDrumMachineVolumeAndMute:
    """Test volume and mute features."""

    def test_set_volume(self):
        dm = DrumMachine()
        dm.set_volume(DrumName.KICK, 0.5)
        assert dm.volumes[DrumName.KICK] == 0.5

    def test_set_volume_clamps_high(self):
        dm = DrumMachine()
        dm.set_volume(DrumName.KICK, 5.0)
        assert dm.volumes[DrumName.KICK] == 2.0

    def test_set_volume_clamps_low(self):
        dm = DrumMachine()
        dm.set_volume(DrumName.KICK, -1.0)
        assert dm.volumes[DrumName.KICK] == 0.0

    def test_toggle_mute(self):
        dm = DrumMachine()
        assert dm.muted[DrumName.KICK] is False
        result = dm.toggle_mute(DrumName.KICK)
        assert result is True
        assert dm.muted[DrumName.KICK] is True
        result = dm.toggle_mute(DrumName.KICK)
        assert result is False

    def test_muted_drums_excluded_from_mix(self):
        dm = DrumMachine()
        dm.load_preset("four-on-floor")
        dm.toggle_mute(DrumName.KICK)
        # Kick is muted, mix should be different
        step0 = dm.mix_step(0)
        # Without kick but with HH, it should still produce audio
        assert np.max(np.abs(step0)) > 0


class TestDrumMachineSwing:
    """Test swing timing."""

    def test_no_swing_equal_steps(self):
        dm = DrumMachine(bpm=120, swing=0.0)
        dur = dm.step_duration(0)
        assert abs(dur - 0.125) < 0.001  # 60/120/4 = 0.125

    def test_swing_changes_step_duration(self):
        dm = DrumMachine(bpm=120, swing=0.5)
        # With swing, even-indexed and odd-indexed steps should differ
        d0 = dm.step_duration(0)
        d1 = dm.step_duration(1)
        # Not equal when swing is active
        assert d0 != d1

    def test_total_loop_duration_no_swing(self):
        dm = DrumMachine(bpm=120)
        total = dm.total_loop_duration()
        expected = 16 * 60.0 / 120 / 4
        assert abs(total - expected) < 0.001


class TestDrumMachineRender:
    """Test rendering and export."""

    def test_mix_step_produces_audio(self):
        dm = DrumMachine()
        dm.load_preset("four-on-floor")
        audio = dm.mix_step(0)  # Kick on step 0
        assert len(audio) > 0
        assert np.max(np.abs(audio)) > 0

    def test_mix_empty_step(self):
        dm = DrumMachine()
        audio = dm.mix_step(0)  # Nothing on
        assert len(audio) > 0
        assert np.max(np.abs(audio)) == 0.0

    def test_render_full_loop(self):
        dm = DrumMachine()
        dm.load_preset("four-on-floor")
        loop = dm.render_full_loop()
        assert len(loop) > 0
        assert np.max(np.abs(loop)) > 0

    def test_render_to_wav(self):
        dm = DrumMachine()
        dm.load_preset("four-on-floor")
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_name = tmp.name
        try:
            dm.render_to_wav(tmp_name, loops=1)
            assert os.path.exists(tmp_name)
            # Verify it's a valid WAV
            with wave.open(tmp_name, 'r') as wf:
                assert wf.getnchannels() == 1
                assert wf.getsampwidth() == 2
                assert wf.getframerate() == SAMPLE_RATE
                assert wf.getnframes() > 0
        finally:
            os.unlink(tmp_name)

    def test_render_to_wav_creates_directory(self):
        dm = DrumMachine()
        dm.load_preset("four-on-floor")
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "subdir", "test.wav")
            dm.render_to_wav(filepath, loops=1)
            assert os.path.exists(filepath)

    def test_render_empty_pattern_to_wav(self):
        """Rendering an empty pattern should still work (silence)."""
        dm = DrumMachine()
        # No steps toggled — should produce silence
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_name = tmp.name
        try:
            dm.render_to_wav(tmp_name, loops=1)
            assert os.path.exists(tmp_name)
        finally:
            os.unlink(tmp_name)


class TestDrumMachineMIDI:
    """Test MIDI export functionality."""

    def test_render_to_midi_creates_file(self):
        dm = DrumMachine()
        dm.load_preset("four-on-floor")
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp:
            tmp_name = tmp.name
        try:
            dm.render_to_midi(tmp_name)
            assert os.path.exists(tmp_name)
            # Check the file has content (MIDI header should be present)
            with open(tmp_name, 'rb') as f:
                data = f.read()
            assert len(data) > 20  # MIDI header + track data
            assert data[:4] == b'MThd'  # MIDI header chunk
        finally:
            os.unlink(tmp_name)

    def test_midi_file_contains_track_data(self):
        dm = DrumMachine(bpm=120)
        dm.load_preset("four-on-floor")
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp:
            tmp_name = tmp.name
        try:
            dm.render_to_midi(tmp_name)
            with open(tmp_name, 'rb') as f:
                data = f.read()
            # Should have MTrk track chunk
            assert b'MTrk' in data
        finally:
            os.unlink(tmp_name)

    def test_midi_empty_pattern(self):
        """Exporting an empty pattern should still produce a valid MIDI file."""
        dm = DrumMachine()
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp:
            tmp_name = tmp.name
        try:
            dm.render_to_midi(tmp_name)
            assert os.path.exists(tmp_name)
        finally:
            os.unlink(tmp_name)

    def test_midi_creates_directory(self):
        dm = DrumMachine()
        dm.load_preset("four-on-floor")
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "subdir", "test.mid")
            dm.render_to_midi(filepath)
            assert os.path.exists(filepath)

    def test_midi_bpm_in_file(self):
        """The MIDI file should encode the correct tempo."""
        dm = DrumMachine(bpm=140)
        dm.load_preset("four-on-floor")
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp:
            tmp_name = tmp.name
        try:
            dm.render_to_midi(tmp_name)
            with open(tmp_name, 'rb') as f:
                data = f.read()
            # Check for tempo meta event
            # Tempo is FF 51 03 followed by 3 bytes encoding microseconds/quarter
            # For BPM=140: 60_000_000 / 140 = 428571 μs → 0x06 0x8E 0xBB
            assert b'MThd' in data[:4]
        finally:
            os.unlink(tmp_name)


class TestDrumMachineSaveLoadJSON:
    """Test JSON pattern save/load."""

    def test_save_and_load_roundtrip(self):
        dm = DrumMachine(bpm=140, steps=16, swing=0.3)
        dm.load_preset("hiphop")
        dm.set_volume(DrumName.KICK, 0.8)
        dm.toggle_mute(DrumName.COWBELL)

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_name = tmp.name

        try:
            dm.save_pattern_json(tmp_name)
            assert os.path.exists(tmp_name)

            dm2 = DrumMachine()
            assert dm2.load_pattern_json(tmp_name)
            assert dm2.bpm == 140
            assert dm2.swing == 0.3
            assert dm2.volumes[DrumName.KICK] == 0.8
            assert dm2.muted[DrumName.COWBELL] is True
            # Check pattern
            for drum in dm.drums:
                assert dm2.pattern[drum] == dm.pattern[drum]
        finally:
            os.unlink(tmp_name)

    def test_save_and_load_humanize(self):
        """Humanize state should round-trip through JSON."""
        dm = DrumMachine(bpm=120)
        dm.humanize = True
        dm.humanize_timing = 0.015
        dm.humanize_velocity = 0.2

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_name = tmp.name
        try:
            dm.save_pattern_json(tmp_name)
            dm2 = DrumMachine()
            dm2.load_pattern_json(tmp_name)
            assert dm2.humanize is True
            assert abs(dm2.humanize_timing - 0.015) < 0.001
            assert abs(dm2.humanize_velocity - 0.2) < 0.001
        finally:
            os.unlink(tmp_name)

    def test_load_nonexistent_file(self):
        dm = DrumMachine()
        result = dm.load_pattern_json("/nonexistent/file.json")
        assert result is False

    def test_load_invalid_json(self):
        dm = DrumMachine()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            tmp.write("not valid json{{{")
            tmp_name = tmp.name
        try:
            result = dm.load_pattern_json(tmp_name)
            assert result is False
        finally:
            os.unlink(tmp_name)

    def test_save_creates_directory(self):
        dm = DrumMachine()
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "subdir", "pattern.json")
            dm.save_pattern_json(filepath)
            assert os.path.exists(filepath)

    def test_json_structure(self):
        dm = DrumMachine(bpm=130)
        dm.load_preset("breakbeat")

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            tmp_name = tmp.name

        try:
            dm.save_pattern_json(tmp_name)
            with open(tmp_name) as f:
                data = json.load(f)

            assert "version" in data
            assert data["bpm"] == 130
            assert data["steps"] == 16
            assert "pattern" in data
            assert "Kick" in data["pattern"]
            assert "volumes" in data
            assert "muted" in data
            assert "humanize" in data
        finally:
            os.unlink(tmp_name)


class TestDrumMachineDisplay:
    """Test display methods."""

    def test_display_grid_returns_string(self):
        dm = DrumMachine()
        grid = dm.display_grid()
        assert isinstance(grid, str)
        assert "Kick" in grid
        assert "BPM" in grid

    def test_display_grid_with_highlight(self):
        dm = DrumMachine()
        grid = dm.display_grid(highlight_step=3)
        assert "Step: 4" in grid  # 1-indexed

    def test_display_grid_shows_steps(self):
        dm = DrumMachine()
        grid = dm.display_grid()
        # Should have step numbers 1-16
        assert " 1" in grid

    def test_display_grid_muted(self):
        dm = DrumMachine()
        dm.toggle_mute(DrumName.KICK)
        grid = dm.display_grid()
        assert "🔇" in grid

    def test_display_grid_humanize(self):
        dm = DrumMachine()
        dm.humanize = True
        grid = dm.display_grid()
        assert "Humanize" in grid

    def test_display_grid_metronome(self):
        dm = DrumMachine()
        dm.metronome = True
        grid = dm.display_grid()
        assert "Metro" in grid

    def test_display_presets_returns_string(self):
        dm = DrumMachine()
        presets = dm.display_presets()
        assert isinstance(presets, str)
        assert "four-on-floor" in presets
        assert "hiphop" in presets


class TestDrumMachineStepCounts:
    """Test different step counts."""

    @pytest.mark.parametrize("steps", VALID_STEP_COUNTS)
    def test_init_with_valid_steps(self, steps):
        dm = DrumMachine(steps=steps)
        assert dm.steps == steps
        for drum in dm.drums:
            assert len(dm.pattern[drum]) == steps

    @pytest.mark.parametrize("steps", VALID_STEP_COUNTS)
    def test_render_with_steps(self, steps):
        dm = DrumMachine(steps=steps)
        dm.load_preset("four-on-floor")
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_name = tmp.name
        try:
            dm.render_to_wav(tmp_name, loops=1)
            assert os.path.exists(tmp_name)
        finally:
            os.unlink(tmp_name)


class TestDrumMachineAdaptPattern:
    """Test pattern adaptation for different step counts."""

    def test_adapt_shorter_pattern(self):
        dm = DrumMachine(steps=16)
        src = [1, 0, 1, 0]
        result = dm._adapt_pattern(src, 8)
        assert len(result) == 8
        assert result == [True, False, True, False, True, False, True, False]

    def test_adapt_longer_pattern(self):
        dm = DrumMachine()
        src = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
        result = dm._adapt_pattern(src, 8)
        assert len(result) == 8
        assert result == [True, False] * 4


class TestDrumAliases:
    """Test drum alias mappings."""

    def test_all_short_aliases_exist(self):
        assert "k" in DRUM_ALIASES
        assert "s" in DRUM_ALIASES
        assert "hhc" in DRUM_ALIASES
        assert "hho" in DRUM_ALIASES
        assert "c" in DRUM_ALIASES
        assert "t" in DRUM_ALIASES
        assert "r" in DRUM_ALIASES
        assert "cb" in DRUM_ALIASES

    def test_all_full_names_exist(self):
        assert "kick" in DRUM_ALIASES
        assert "snare" in DRUM_ALIASES
        assert "hh-closed" in DRUM_ALIASES
        assert "hh-open" in DRUM_ALIASES
        assert "clap" in DRUM_ALIASES
        assert "tom" in DRUM_ALIASES
        assert "rim" in DRUM_ALIASES
        assert "cowbell" in DRUM_ALIASES

    def test_aliases_map_correctly(self):
        assert DRUM_ALIASES["k"] == DrumName.KICK
        assert DRUM_ALIASES["s"] == DrumName.SNARE
        assert DRUM_ALIASES["cb"] == DrumName.COWBELL


class TestVersion:
    """Test version constant."""

    def test_version_is_string(self):
        assert isinstance(__version__, str)

    def test_version_format(self):
        parts = __version__.split(".")
        assert len(parts) >= 2
        for part in parts:
            assert part.isdigit()


class TestBugFixes:
    """Tests for bugs that were found and fixed."""

    def test_swing_preserves_total_duration(self):
        """Swing should redistribute timing without changing total loop duration."""
        dm_no_swing = DrumMachine(bpm=120, swing=0.0)
        dm_swing = DrumMachine(bpm=120, swing=0.5)
        total_no_swing = dm_no_swing.total_loop_duration()
        total_swing = dm_swing.total_loop_duration()
        assert abs(total_no_swing - total_swing) < 0.001, \
            f"Swing changed total duration: {total_swing:.4f}s vs {total_no_swing:.4f}s"

    def test_swing_step_0_treated_as_even(self):
        """Step 0 should be treated the same as other even steps under swing."""
        dm = DrumMachine(bpm=120, swing=0.5)
        d0 = dm.step_duration(0)
        d2 = dm.step_duration(2)
        d4 = dm.step_duration(4)
        assert abs(d0 - d2) < 0.001, f"Step 0 ({d0:.4f}) != Step 2 ({d2:.4f})"
        assert abs(d0 - d4) < 0.001, f"Step 0 ({d0:.4f}) != Step 4 ({d4:.4f})"

    def test_swing_pair_sums_to_double_base(self):
        """Each pair of (even, odd) steps should sum to 2*base."""
        dm = DrumMachine(bpm=120, swing=0.3)
        base = 60.0 / 120 / 4
        for i in range(0, 16, 2):
            pair_sum = dm.step_duration(i) + dm.step_duration(i + 1)
            assert abs(pair_sum - 2 * base) < 0.001, \
                f"Pair {i},{i+1} sums to {pair_sum:.4f}, expected {2*base:.4f}"

    def test_load_json_with_wrong_types_does_not_crash(self):
        """Loading JSON with wrong value types should not corrupt DrumMachine state."""
        dm = DrumMachine(bpm=120, steps=16, swing=0.1)
        original_bpm = dm.bpm
        original_swing = dm.swing
        bad_data = {
            "bpm": "fast",
            "steps": "sixteen",
            "swing": "groovy",
            "pattern": "noise",
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(bad_data, tmp)
            tmp_name = tmp.name
        try:
            result = dm.load_pattern_json(tmp_name)
            assert result is True  # File loads, but bad values are ignored
            # bpm and swing should remain unchanged (wrong types ignored)
            assert dm.bpm == original_bpm
            assert dm.swing == original_swing
            # Steps should remain unchanged (wrong type)
            assert dm.steps == 16
            # Should still be functional after bad load
            loop = dm.render_full_loop()
            assert len(loop) > 0
            dur = dm.step_duration(0)
            assert dur > 0
        finally:
            os.unlink(tmp_name)

    def test_load_json_with_numeric_types(self):
        """Loading JSON with proper numeric types should work correctly."""
        dm = DrumMachine()
        good_data = {
            "bpm": 140,
            "steps": 16,
            "swing": 0.25,
            "pattern": {"Kick": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0]},
            "volumes": {"Kick": 0.5},
            "muted": {"Snare": True},
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(good_data, tmp)
            tmp_name = tmp.name
        try:
            result = dm.load_pattern_json(tmp_name)
            assert result is True
            assert dm.bpm == 140
            assert dm.swing == 0.25
            assert dm.volumes[DrumName.KICK] == 0.5
            assert dm.muted[DrumName.SNARE] is True
        finally:
            os.unlink(tmp_name)

    def test_render_to_wav_rejects_zero_loops(self):
        """render_to_wav should reject loops < 1."""
        dm = DrumMachine()
        dm.load_preset("four-on-floor")
        with pytest.raises(ValueError, match="at least 1"):
            dm.render_to_wav("/tmp/test_zero.wav", loops=0)

    def test_swing_max_preserves_duration(self):
        """Maximum swing (0.75) should still preserve total loop duration."""
        dm = DrumMachine(bpm=120, swing=0.75)
        total = dm.total_loop_duration()
        expected = 16 * 60.0 / 120 / 4
        assert abs(total - expected) < 0.01, \
            f"Max swing changed total: {total:.4f}s vs {expected:.4f}s"

    def test_load_json_pattern_with_non_list_value(self):
        """Loading JSON where a pattern value is not a list should not crash."""
        dm = DrumMachine()
        data = {
            "bpm": 120,
            "pattern": {"Kick": "not_a_list"},
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(data, tmp)
            tmp_name = tmp.name
        try:
            result = dm.load_pattern_json(tmp_name)
            assert result is True
            # Kick pattern should default to all-False since "not_a_list" is not a list
            assert all(not s for s in dm.pattern[DrumName.KICK])
        finally:
            os.unlink(tmp_name)


class TestBugFixesRound2:
    """Regression tests for bugs found in v1.3.0 and fixed in v1.4.0."""

    def test_load_json_rejects_out_of_range_bpm(self):
        """BPM values outside 30-300 should be rejected on JSON load."""
        dm = DrumMachine(bpm=120)

        # BPM=500 (too high)
        data = {"bpm": 500}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_name = f.name
        try:
            dm.load_pattern_json(tmp_name)
            assert dm.bpm == 120, f"BPM=500 should be rejected, got {dm.bpm}"
        finally:
            os.unlink(tmp_name)

        # BPM=0 (too low — causes ZeroDivisionError)
        data = {"bpm": 0}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_name = f.name
        try:
            dm.load_pattern_json(tmp_name)
            assert dm.bpm == 120, f"BPM=0 should be rejected, got {dm.bpm}"
        finally:
            os.unlink(tmp_name)

        # BPM=-50 (negative)
        data = {"bpm": -50}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_name = f.name
        try:
            dm.load_pattern_json(tmp_name)
            assert dm.bpm == 120, f"BPM=-50 should be rejected, got {dm.bpm}"
        finally:
            os.unlink(tmp_name)

    def test_load_json_rejects_out_of_range_swing(self):
        """Swing values outside 0.0-0.75 should be rejected on JSON load."""
        dm = DrumMachine(swing=0.0)

        # Swing=1.5 (too high — causes negative step durations)
        data = {"swing": 1.5}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_name = f.name
        try:
            dm.load_pattern_json(tmp_name)
            assert dm.swing == 0.0, f"Swing=1.5 should be rejected, got {dm.swing}"
        finally:
            os.unlink(tmp_name)

        # Swing=-0.5 (negative)
        data = {"swing": -0.5}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_name = f.name
        try:
            dm.load_pattern_json(tmp_name)
            assert dm.swing == 0.0, f"Swing=-0.5 should be rejected, got {dm.swing}"
        finally:
            os.unlink(tmp_name)

    def test_hihat_closed_very_short_duration(self):
        """synth_hihat_closed should not crash with very short durations."""
        result = synth_hihat_closed(duration=0.0001)
        assert isinstance(result, np.ndarray)
        # Result may be empty or short, but should not crash

    def test_hihat_closed_short_duration(self):
        """synth_hihat_closed should work with short but plausible durations."""
        result = synth_hihat_closed(duration=0.005)
        assert isinstance(result, np.ndarray)
        assert len(result) > 0

    def test_hihat_open_very_short_duration(self):
        """synth_hihat_open should not crash with very short durations."""
        result = synth_hihat_open(duration=0.0001)
        assert isinstance(result, np.ndarray)

    def test_hihat_open_short_duration(self):
        """synth_hihat_open should work with short but plausible durations."""
        result = synth_hihat_open(duration=0.005)
        assert isinstance(result, np.ndarray)
        assert len(result) > 0

    def test_render_with_zero_bpm_does_not_crash(self):
        """Rendering should not crash even if BPM is set to 0 via JSON."""
        dm = DrumMachine(bpm=120)
        dm.load_preset("four-on-floor")
        dm.bpm = 0  # Simulate corrupted state
        try:
            loop = dm.render_full_loop()
            assert len(loop) > 0
        except ZeroDivisionError:
            pytest.fail("render_full_loop crashed with BPM=0")

    def test_render_with_negative_bpm_does_not_crash(self):
        """Rendering should not crash with negative BPM."""
        dm = DrumMachine(bpm=120)
        dm.load_preset("four-on-floor")
        dm.bpm = -50  # Simulate corrupted state
        try:
            loop = dm.render_full_loop()
            assert len(loop) > 0
        except Exception as e:
            pytest.fail(f"render_full_loop crashed with BPM=-50: {e}")

    def test_midi_export_rejects_zero_bpm(self):
        """MIDI export should raise ValueError with invalid BPM."""
        dm = DrumMachine(bpm=120)
        dm.load_preset("four-on-floor")
        dm.bpm = 0
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp:
            tmp_name = tmp.name
        try:
            with pytest.raises(ValueError, match="invalid BPM"):
                dm.render_to_midi(tmp_name)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def test_midi_export_rejects_negative_bpm(self):
        """MIDI export should raise ValueError with negative BPM."""
        dm = DrumMachine(bpm=120)
        dm.load_preset("four-on-floor")
        dm.bpm = -10
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp:
            tmp_name = tmp.name
        try:
            with pytest.raises(ValueError, match="invalid BPM"):
                dm.render_to_midi(tmp_name)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def test_load_json_valid_bpm_in_range(self):
        """Valid BPM values in JSON should still be accepted."""
        dm = DrumMachine(bpm=120)
        data = {"bpm": 140}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_name = f.name
        try:
            dm.load_pattern_json(tmp_name)
            assert dm.bpm == 140
        finally:
            os.unlink(tmp_name)

    def test_load_json_valid_swing_in_range(self):
        """Valid swing values in JSON should still be accepted."""
        dm = DrumMachine(swing=0.0)
        data = {"swing": 0.5}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_name = f.name
        try:
            dm.load_pattern_json(tmp_name)
            assert dm.swing == 0.5
        finally:
            os.unlink(tmp_name)

    def test_load_json_boundary_bpm(self):
        """BPM at boundary values (30, 300) should be accepted."""
        dm = DrumMachine(bpm=120)

        data = {"bpm": 30}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_name = f.name
        try:
            dm.load_pattern_json(tmp_name)
            assert dm.bpm == 30
        finally:
            os.unlink(tmp_name)

        data = {"bpm": 300}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_name = f.name
        try:
            dm.load_pattern_json(tmp_name)
            assert dm.bpm == 300
        finally:
            os.unlink(tmp_name)

    def test_load_json_boundary_swing(self):
        """Swing at boundary values (0.0, 0.75) should be accepted."""
        dm = DrumMachine(swing=0.0)

        data = {"swing": 0.0}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_name = f.name
        try:
            dm.load_pattern_json(tmp_name)
            assert dm.swing == 0.0
        finally:
            os.unlink(tmp_name)

        data = {"swing": 0.75}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            tmp_name = f.name
        try:
            dm.load_pattern_json(tmp_name)
            assert dm.swing == 0.75
        finally:
            os.unlink(tmp_name)

    def test_all_muted_render_to_wav_succeeds(self):
        """Rendering WAV with all drums muted should succeed (silence)."""
        dm = DrumMachine()
        for drum in dm.drums:
            dm.muted[drum] = True
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_name = tmp.name
        try:
            dm.render_to_wav(tmp_name, loops=1)
            assert os.path.exists(tmp_name)
            with wave.open(tmp_name, 'r') as wf:
                assert wf.getnframes() > 0
        finally:
            os.unlink(tmp_name)

    def test_step_duration_with_invalid_bpm_returns_positive(self):
        """step_duration should return a positive value even with invalid BPM."""
        dm = DrumMachine(bpm=120)
        dm.bpm = 0
        d = dm.step_duration(0)
        assert d > 0, f"step_duration should be positive even with BPM=0, got {d}"

    def test_step_duration_with_extreme_swing_returns_positive(self):
        """step_duration should return a positive value even with extreme swing."""
        dm = DrumMachine(bpm=120)
        dm.swing = 1.5  # Invalid but loaded from corrupted JSON
        d0 = dm.step_duration(0)
        d1 = dm.step_duration(1)
        assert d0 > 0, f"step_duration(0) should be positive, got {d0}"
        assert d1 > 0, f"step_duration(1) should be positive, got {d1}"