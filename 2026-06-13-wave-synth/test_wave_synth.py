#!/usr/bin/env python3
"""Tests for Wave Synth — Terminal Audio Waveform Synthesizer."""

import math
import os
import sys
import tempfile
import unittest

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wave_synth import (
    generate_sine, generate_square, generate_sawtooth, generate_triangle,
    generate_noise, generate_harmonic, generate_chirp,
    resolve_freq, note_to_freq, NOTE_FREQS, SAMPLE_RATE,
    apply_adsr, apply_tremolo, apply_vibrato, apply_lowpass, apply_highpass,
    apply_distortion, apply_delay, apply_fade_in, apply_fade_out,
    apply_reverse, apply_ring_mod, apply_bitcrush, apply_reverb,
    apply_pitch_shift, normalize,
    mix_waves, generate_chord, generate_arpeggio, generate_melody,
    export_wav, import_wav, MELODY_PRESETS, CHORD_INTERVALS,
    visualize_ascii, visualize_spectrum_ascii, print_waveform_info,
    WAVE_GENERATORS, EFFECTS, __version__,
)


class TestWaveGeneration(unittest.TestCase):
    """Test basic waveform generators."""

    def test_sine_wave_length(self):
        """Sine wave should produce correct number of samples."""
        samples = generate_sine(440.0, 1.0)
        self.assertEqual(len(samples), SAMPLE_RATE)

    def test_sine_wave_amplitude(self):
        """Sine wave peak should match amplitude parameter."""
        samples = generate_sine(440.0, 1.0, amplitude=0.5)
        peak = max(abs(s) for s in samples)
        self.assertAlmostEqual(peak, 0.5, places=2)

    def test_sine_wave_range(self):
        """Sine wave values should be within [-amplitude, amplitude]."""
        samples = generate_sine(440.0, 1.0)
        for s in samples:
            self.assertGreaterEqual(s, -1.01)
            self.assertLessEqual(s, 1.01)

    def test_square_wave_values(self):
        """Square wave should only contain -1 and 1 values (approximately)."""
        samples = generate_square(440.0, 0.01)
        for s in samples:
            self.assertTrue(abs(abs(s) - 1.0) < 0.01 or abs(s) < 0.01,
                            f"Square wave value {s} not near ±1 or 0")

    def test_sawtooth_wave_range(self):
        """Sawtooth wave values should stay within [-1, 1]."""
        samples = generate_sawtooth(440.0, 0.1)
        for s in samples:
            self.assertGreaterEqual(s, -1.01)
            self.assertLessEqual(s, 1.01)

    def test_triangle_wave_range(self):
        """Triangle wave values should stay within [-1, 1]."""
        samples = generate_triangle(440.0, 0.1)
        for s in samples:
            self.assertGreaterEqual(s, -1.01)
            self.assertLessEqual(s, 1.01)

    def test_noise_wave_length(self):
        """Noise wave should produce correct number of samples."""
        samples = generate_noise(1.0)
        self.assertEqual(len(samples), SAMPLE_RATE)

    def test_noise_deterministic_with_seed(self):
        """Noise with same seed should produce identical output."""
        s1 = generate_noise(1.0, seed=42)
        s2 = generate_noise(1.0, seed=42)
        self.assertEqual(s1, s2)

    def test_harmonic_wave(self):
        """Harmonic wave with default overtones should produce samples."""
        samples = generate_harmonic(440.0, 1.0)
        self.assertEqual(len(samples), SAMPLE_RATE)
        # Should not be all zeros
        self.assertTrue(any(abs(s) > 0.01 for s in samples))

    def test_chirp_wave(self):
        """Chirp wave should produce samples and change frequency over time."""
        samples = generate_chirp(200.0, 2000.0, 1.0)
        self.assertEqual(len(samples), SAMPLE_RATE)
        # Should not be all zeros
        self.assertTrue(any(abs(s) > 0.01 for s in samples))

    def test_chirp_exponential(self):
        """Exponential chirp should produce samples."""
        samples = generate_chirp(200.0, 2000.0, 1.0, method='exponential')
        self.assertEqual(len(samples), SAMPLE_RATE)

    def test_invalid_frequency_raises(self):
        """Negative/zero frequency should raise ValueError."""
        with self.assertRaises(ValueError):
            generate_sine(-100.0, 1.0)
        with self.assertRaises(ValueError):
            generate_sine(0.0, 1.0)

    def test_invalid_duration_raises(self):
        """Negative/zero duration should raise ValueError."""
        with self.assertRaises(ValueError):
            generate_sine(440.0, -1.0)
        with self.assertRaises(ValueError):
            generate_sine(440.0, 0.0)


class TestNoteResolution(unittest.TestCase):
    """Test note name to frequency resolution."""

    def test_a4_concert_pitch(self):
        """A4 should resolve to 440 Hz."""
        self.assertAlmostEqual(resolve_freq('A4'), 440.0, places=2)

    def test_middle_c(self):
        """C4 should resolve to ~261.63 Hz."""
        self.assertAlmostEqual(resolve_freq('C4'), 261.63, places=1)

    def test_sharp_note(self):
        """C#5 should resolve correctly."""
        self.assertAlmostEqual(resolve_freq('C#5'), 554.37, places=1)

    def test_flat_note(self):
        """Eb3 should resolve correctly (same as D#3)."""
        self.assertAlmostEqual(resolve_freq('Eb3'), resolve_freq('D#3'), places=2)

    def test_numeric_frequency(self):
        """Numeric strings should be parsed as Hz."""
        self.assertEqual(resolve_freq('440'), 440.0)
        self.assertEqual(resolve_freq('261.63'), 261.63)

    def test_unknown_note_raises(self):
        """Unknown note names should raise ValueError."""
        with self.assertRaises(ValueError):
            resolve_freq('Z99')


class TestEffects(unittest.TestCase):
    """Test audio effects."""

    def setUp(self):
        """Create a test sine wave."""
        self.samples = generate_sine(440.0, 0.5)

    def test_tremolo_length(self):
        """Tremolo should not change sample length."""
        result = apply_tremolo(self.samples, rate=5.0, depth=0.5)
        self.assertEqual(len(result), len(self.samples))

    def test_vibrato_length(self):
        """Vibrato should not change sample length."""
        result = apply_vibrato(self.samples, rate=5.0, depth=0.002)
        self.assertEqual(len(result), len(self.samples))

    def test_lowpass_preserves_length(self):
        """Lowpass filter should not change sample length."""
        result = apply_lowpass(self.samples, cutoff=1000.0)
        self.assertEqual(len(result), len(self.samples))

    def test_highpass_preserves_length(self):
        """Highpass filter should not change sample length."""
        result = apply_highpass(self.samples, cutoff=200.0)
        self.assertEqual(len(result), len(self.samples))

    def test_distortion_clips(self):
        """Distortion should limit peak values."""
        result = apply_distortion(self.samples, drive=5.0)
        peak = max(abs(s) for s in result)
        # tanh-based distortion should keep values < 1
        self.assertLess(peak, 1.01)

    def test_delay_length(self):
        """Delay should return trimmed samples at original length."""
        result = apply_delay(self.samples, delay_time=0.1, feedback=0.3)
        self.assertEqual(len(result), len(self.samples))

    def test_fade_in_starts_quiet(self):
        """Fade-in should start near zero."""
        result = apply_fade_in(self.samples, duration=0.1)
        self.assertAlmostEqual(result[0], 0.0, places=5)

    def test_fade_out_ends_quiet(self):
        """Fade-out should end near zero."""
        result = apply_fade_out(self.samples, duration=0.1)
        self.assertAlmostEqual(result[-1], 0.0, places=5)

    def test_normalize_peak(self):
        """Normalize should set peak to target."""
        result = normalize(self.samples, target_peak=0.9)
        peak = max(abs(s) for s in result)
        self.assertAlmostEqual(peak, 0.9, places=2)

    def test_reverse(self):
        """Reverse should reverse the waveform."""
        result = apply_reverse(self.samples)
        self.assertEqual(result, list(reversed(self.samples)))

    def test_ring_mod_length(self):
        """Ring modulation should not change sample length."""
        result = apply_ring_mod(self.samples, freq=100.0)
        self.assertEqual(len(result), len(self.samples))

    def test_bitcrush_quantizes(self):
        """Bitcrush with 1 bit should only produce -1, 0, or 1."""
        result = apply_bitcrush(self.samples, bits=1)
        for s in result:
            self.assertIn(round(s, 1), [-1.0, 0.0, 1.0])

    def test_reverb_length(self):
        """Reverb should not change sample length."""
        result = apply_reverb(self.samples, decay=0.3)
        self.assertEqual(len(result), len(self.samples))

    def test_pitch_shift_up(self):
        """Pitch shift up should produce shorter sample (higher pitch, less time)."""
        result = apply_pitch_shift(self.samples, semitones=12)
        self.assertLess(len(result), len(self.samples))

    def test_pitch_shift_zero(self):
        """Pitch shift of 0 semitones should return identical samples."""
        result = apply_pitch_shift(self.samples, semitones=0)
        self.assertEqual(len(result), len(self.samples))

    def test_adsr_length(self):
        """ADSR should not change sample length."""
        result = apply_adsr(self.samples, attack=0.01, decay=0.01, sustain=0.7, release=0.1)
        self.assertEqual(len(result), len(self.samples))

    def test_adsr_starts_quiet(self):
        """ADSR should start near zero (attack ramp)."""
        result = apply_adsr(self.samples, attack=0.1, decay=0.05, sustain=0.7, release=0.1)
        self.assertAlmostEqual(result[0], 0.0, places=2)


class TestMixing(unittest.TestCase):
    """Test waveform mixing."""

    def test_mix_two_sines(self):
        """Mixing two waves should produce output at the max length."""
        s1 = generate_sine(440.0, 1.0)
        s2 = generate_sine(880.0, 1.0)
        result = mix_waves([s1, s2])
        self.assertEqual(len(result), len(s1))

    def test_mix_with_weights(self):
        """Mixing with unequal weights should weight properly."""
        s1 = generate_sine(440.0, 0.1)
        s2 = [0.0] * len(s1)  # Silent
        # With weights [1.0, 0.0], normalized to [1.0, 0.0], result = s1*1.0 + 0*0.0
        result = mix_waves([s1, s2], [1.0, 0.0])
        for i in range(len(result)):
            self.assertAlmostEqual(result[i], s1[i], places=5)


class TestChordsAndArpeggios(unittest.TestCase):
    """Test chord and arpeggio generation."""

    def test_chord_length(self):
        """Chord should produce samples of correct duration."""
        samples = generate_chord(440.0, 'maj', 2.0)
        self.assertAlmostEqual(len(samples), 2.0 * SAMPLE_RATE, delta=1)

    def test_arpeggio_length(self):
        """Arpeggio should produce samples of correct duration."""
        samples = generate_arpeggio(440.0, 'maj', 2.0)
        self.assertEqual(len(samples), 2.0 * SAMPLE_RATE)

    def test_all_chord_types(self):
        """All chord types should generate without errors."""
        for chord_type in CHORD_INTERVALS:
            samples = generate_chord(440.0, chord_type, 1.0)
            self.assertGreater(len(samples), 0)


class TestMelody(unittest.TestCase):
    """Test melody generation."""

    def test_all_presets_work(self):
        """All melody presets should generate without errors."""
        for name, notes in MELODY_PRESETS.items():
            samples = generate_melody(notes)
            self.assertGreater(len(samples), 0)

    def test_melody_with_rests(self):
        """Melodies with rests should produce silence for rest notes."""
        notes = [('C4', 0.1), ('R', 0.1)]
        samples = generate_melody(notes)
        self.assertGreater(len(samples), 0)


class TestWavIO(unittest.TestCase):
    """Test WAV import and export."""

    def test_export_and_import_roundtrip(self):
        """Exporting and importing a WAV file should preserve sample count and values."""
        original = generate_sine(440.0, 0.5)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            filename = f.name
        try:
            export_wav(original, filename)
            imported, sr = import_wav(filename)
            self.assertEqual(sr, SAMPLE_RATE)
            # Allow some quantization error (16-bit)
            self.assertEqual(len(imported), len(original))
            for orig, imp in zip(original, imported):
                self.assertAlmostEqual(orig, imp, places=3)
        finally:
            os.unlink(filename)

    def test_export_creates_file(self):
        """Export should create a non-empty WAV file."""
        original = generate_sine(440.0, 1.0)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            filename = f.name
        try:
            export_wav(original, filename)
            self.assertGreater(os.path.getsize(filename), 0)
        finally:
            os.unlink(filename)

    def test_import_nonexistent_raises(self):
        """Importing a nonexistent file should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            import_wav('/nonexistent/file.wav')


class TestVisualization(unittest.TestCase):
    """Test ASCII visualization functions."""

    def test_visualize_ascii(self):
        """ASCII visualization should produce a non-empty string."""
        samples = generate_sine(440.0, 1.0)
        result = visualize_ascii(samples)
        self.assertIn('│', result)
        self.assertIn('─', result)

    def test_visualize_empty(self):
        """Visualizing empty samples should return a message."""
        result = visualize_ascii([])
        self.assertIn('empty', result)

    def test_spectrum_ascii(self):
        """Spectrum visualization should produce a non-empty string."""
        samples = generate_sine(440.0, 1.0)
        result = visualize_spectrum_ascii(samples)
        self.assertIn('│', result)

    def test_spectrum_too_short(self):
        """Spectrum with too few samples should return a message."""
        result = visualize_spectrum_ascii([0.5])
        self.assertIn('not enough', result)

    def test_waveform_info(self):
        """Waveform info should contain expected fields."""
        samples = generate_sine(440.0, 1.0)
        info = print_waveform_info(samples, "test")
        self.assertIn('Name:', info)
        self.assertIn('Duration:', info)
        self.assertIn('Peak:', info)
        self.assertIn('RMS:', info)

    def test_waveform_info_empty(self):
        """Waveform info for empty samples should indicate empty."""
        info = print_waveform_info([], "test")
        self.assertIn('empty', info)


class TestVersion(unittest.TestCase):
    """Test version is defined."""

    def test_version_exists(self):
        """Module should have a version string."""
        self.assertIsNotNone(__version__)
        self.assertRegex(__version__, r'\d+\.\d+\.\d+')


class TestBugFixes(unittest.TestCase):
    """Tests for bugs found and fixed during bug hunting."""

    def test_resolve_freq_lowercase_flats(self):
        """Lowercase flat notes should resolve correctly (eb3 -> Eb3)."""
        self.assertAlmostEqual(resolve_freq('eb3'), 155.56, places=1)
        self.assertAlmostEqual(resolve_freq('bb4'), 466.16, places=1)
        self.assertAlmostEqual(resolve_freq('ab4'), 415.30, places=1)
        self.assertAlmostEqual(resolve_freq('gb5'), 739.99, places=1)

    def test_note_to_freq_B_notes(self):
        """B notes should not be corrupted by case normalization."""
        self.assertAlmostEqual(note_to_freq('B4'), 493.88, places=1)
        self.assertAlmostEqual(note_to_freq('B3'), 246.94, places=1)
        self.assertAlmostEqual(note_to_freq('Bb4'), 466.16, places=1)

    def test_note_to_freq_lowercase_flats(self):
        """note_to_freq should handle lowercase flats correctly."""
        self.assertAlmostEqual(note_to_freq('eb3'), 155.56, places=1)
        self.assertAlmostEqual(note_to_freq('bb4'), 466.16, places=1)

    def test_generate_chord_harmonic(self):
        """Generating a chord with harmonic wave type should not crash."""
        samples = generate_chord(440.0, 'maj', 0.5, wave_type='harmonic')
        self.assertGreater(len(samples), 0)

    def test_generate_chord_chirp(self):
        """Generating a chord with chirp wave type should not crash (uses sine fallback)."""
        samples = generate_chord(440.0, 'maj', 0.5, wave_type='chirp')
        self.assertGreater(len(samples), 0)

    def test_generate_arpeggio_harmonic(self):
        """Generating an arpeggio with harmonic wave type should not crash."""
        samples = generate_arpeggio(440.0, 'maj', 0.5, wave_type='harmonic')
        self.assertGreater(len(samples), 0)

    def test_generate_melody_harmonic(self):
        """Generating a melody with harmonic wave type should not crash."""
        notes = [('C4', 0.2), ('E4', 0.2)]
        samples = generate_melody(notes, wave_type='harmonic')
        self.assertGreater(len(samples), 0)

    def test_lowpass_empty_samples(self):
        """Lowpass filter on empty samples should return empty list."""
        result = apply_lowpass([], cutoff=1000.0)
        self.assertEqual(result, [])

    def test_highpass_empty_samples(self):
        """Highpass filter on empty samples should return empty list."""
        result = apply_highpass([], cutoff=1000.0)
        self.assertEqual(result, [])

    def test_pitch_shift_empty_samples(self):
        """Pitch shift on empty samples should return empty list."""
        result = apply_pitch_shift([], semitones=5)
        self.assertEqual(result, [])

    def test_distortion_zero_drive(self):
        """Distortion with drive=0 should return a copy of the samples (no-op)."""
        samples = generate_sine(440.0, 0.1)
        result = apply_distortion(samples, drive=0)
        self.assertEqual(len(result), len(samples))
        for orig, res in zip(samples, result):
            self.assertAlmostEqual(orig, res, places=5)

    def test_distortion_negative_drive_raises(self):
        """Distortion with negative drive should raise ValueError."""
        with self.assertRaises(ValueError):
            apply_distortion([0.5], drive=-1.0)

    def test_mix_waves_zero_weights(self):
        """Mixing with all-zero weights should produce silence."""
        s1 = generate_sine(440.0, 0.1)
        s2 = generate_sine(880.0, 0.1)
        result = mix_waves([s1, s2], [0.0, 0.0])
        self.assertEqual(len(result), len(s1))
        for s in result:
            self.assertAlmostEqual(s, 0.0, places=5)

    def test_visualize_ascii_scale_labels(self):
        """Visualization should have correct number of data rows (not extra from labels)."""
        samples = generate_sine(440.0, 0.5)
        viz = visualize_ascii(samples, width=40, height=10)
        lines = viz.split('\n')
        # Should have top border + height data rows + bottom border = height+2 lines
        # (labels are now overlaid on existing rows, not inserted as new rows)
        self.assertEqual(len(lines), 10 + 2)  # height + top + bottom

    def test_chirp_same_freq(self):
        """Chirp with same start/end frequency should produce valid sine wave."""
        samples = generate_chirp(440, 440, 0.5)
        self.assertEqual(len(samples), int(0.5 * SAMPLE_RATE))
        self.assertTrue(any(abs(s) > 0.01 for s in samples))


if __name__ == '__main__':
    unittest.main()
    unittest.main()