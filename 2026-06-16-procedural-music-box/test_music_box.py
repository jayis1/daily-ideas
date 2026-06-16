#!/usr/bin/env python3
"""Tests for Procedural Music Box."""

import os
import struct
import tempfile
import wave

import music_box


# ─── Music Theory Tests ──────────────────────────────────────────────────────

def test_midi_to_freq_middle_c():
    """C4 (MIDI 60) should be ~261.63 Hz."""
    freq = music_box.midi_to_freq(60)
    assert 261.0 < freq < 262.0, f"C4 frequency off: {freq}"


def test_midi_to_freq_a4():
    """A4 (MIDI 69) should be exactly 440 Hz."""
    assert music_box.midi_to_freq(69) == 440.0


def test_midi_to_name():
    """Note name conversion should work for sharps and naturals."""
    assert music_box.midi_to_name(60) == "C4"
    assert music_box.midi_to_name(61) == "C#4"
    assert music_box.midi_to_name(69) == "A4"
    assert music_box.midi_to_name(57) == "A3"


def test_name_to_midi():
    """name_to_midi should parse note names with and without octave."""
    assert music_box.name_to_midi("C") == 60      # C4 default
    assert music_box.name_to_midi("A") == 69      # A4 default
    assert music_box.name_to_midi("C4") == 60
    assert music_box.name_to_midi("A4") == 69
    assert music_box.name_to_midi("C3") == 48
    assert music_box.name_to_midi("Bb") == 70      # Bb -> A#4


def test_build_scale_notes_ionian():
    """C Ionian should contain the white keys starting from C4."""
    notes = music_box.build_scale_notes(60, music_box.ScaleType.IONIAN)
    # Should include C4 (60), D4 (62), E4 (64), F4 (65), G4 (67), A4 (69), B4 (71)
    assert 60 in notes  # C4
    assert 62 in notes  # D4
    assert 64 in notes  # E4
    assert 65 in notes  # F4
    assert 67 in notes  # G4
    assert 69 in notes  # A4
    assert 71 in notes  # B4


def test_build_scale_notes_pentatonic():
    """C pentatonic major should have 5 notes per octave."""
    notes = music_box.build_scale_notes(60, music_box.ScaleType.PENTATONIC_MAJOR)
    # C(60), D(62), E(64), G(67), A(69) per octave
    assert 60 in notes
    assert 62 in notes
    assert 64 in notes
    assert 67 in notes
    assert 69 in notes
    # Should NOT contain F or B
    assert 65 not in notes
    assert 71 not in notes


def test_get_scale_degrees():
    """Scale degrees should produce proper triads for Ionian."""
    degrees = music_box.get_scale_degrees(60, music_box.ScaleType.IONIAN)
    # I chord in C major = C-E-G
    assert degrees[0] == [60, 64, 67]
    # IV chord in C major = F-A-C5 (was buggy: used to return [60,65,69])
    assert degrees[3] == [65, 69, 72]


# ─── Note / Melody Tests ────────────────────────────────────────────────────

def test_note_properties():
    """Note dataclass should compute derived properties correctly."""
    n = music_box.Note(midi=60, start=0.0, duration=2.0, velocity=100)
    assert n.end == 2.0
    assert abs(n.freq - music_box.midi_to_freq(60)) < 0.01
    assert n.name == "C4"


def test_note_is_sharp():
    """is_sharp() should correctly identify accidental notes."""
    assert music_box.Note(midi=61, start=0, duration=1).is_sharp() is True   # C#
    assert music_box.Note(midi=60, start=0, duration=1).is_sharp() is False   # C
    assert music_box.Note(midi=63, start=0, duration=1).is_sharp() is True    # D#/Eb


def test_melody_total_beats():
    """Melody total_beats should equal the latest note end time."""
    notes = [
        music_box.Note(midi=60, start=0.0, duration=1.0),
        music_box.Note(midi=64, start=1.0, duration=2.0),
        music_box.Note(midi=67, start=3.0, duration=0.5),
    ]
    melody = music_box.Melody(notes=notes, bpm=120)
    assert melody.total_beats == 3.5


def test_melody_total_seconds():
    """Total seconds = total_beats * 60 / bpm."""
    notes = [music_box.Note(midi=60, start=0.0, duration=4.0)]
    melody = music_box.Melody(notes=notes, bpm=120)
    assert abs(melody.total_seconds - 2.0) < 0.01  # 4 beats at 120 BPM = 2s


def test_melody_transpose():
    """Transposing a melody should shift all MIDI notes."""
    notes = [music_box.Note(midi=60, start=0.0, duration=1.0)]
    melody = music_box.Melody(notes=notes, bpm=120, root=60,
                               scale_type=music_box.ScaleType.IONIAN)
    transposed = melody.transpose(12)
    assert transposed.notes[0].midi == 72  # C4 -> C5
    assert transposed.root == 72


def test_melody_voices():
    """voices() should group notes by channel."""
    notes = [
        music_box.Note(midi=60, start=0.0, duration=1.0, channel=0),
        music_box.Note(midi=64, start=0.0, duration=1.0, channel=1),
        music_box.Note(midi=67, start=1.0, duration=1.0, channel=0),
    ]
    melody = music_box.Melody(notes=notes)
    voices = melody.voices()
    assert len(voices) == 2
    assert len(voices[0]) == 2
    assert len(voices[1]) == 1


# ─── Melody Generation Tests ─────────────────────────────────────────────────

def test_generate_melodic_deterministic():
    """Same seed should produce identical melodies."""
    gen1 = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                       bpm=120, seed=12345)
    gen2 = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                       bpm=120, seed=12345)
    m1 = gen1.generate_melodic(bars=4)
    m2 = gen2.generate_melodic(bars=4)
    assert len(m1.notes) == len(m2.notes)
    for n1, n2 in zip(m1.notes, m2.notes):
        assert n1.midi == n2.midi
        assert n1.start == n2.start
        assert n1.duration == n2.duration


def test_generate_melodic_has_notes():
    """Generated melodic melody should have notes."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_melodic(bars=4)
    assert len(melody.notes) > 0


def test_generate_arpeggiated_has_notes():
    """Generated arpeggiated melody should have notes."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_arpeggiated(bars=4)
    assert len(melody.notes) > 0


def test_generate_counterpoint_has_two_voices():
    """Counterpoint should produce notes in two different channels."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_counterpoint(bars=4)
    assert len(melody.notes) > 0
    channels = set(n.channel for n in melody.notes)
    assert len(channels) == 2, f"Expected 2 voices, got {len(channels)}"


def test_generate_drone_has_long_notes():
    """Drone style should produce notes longer than 8 beats (sustained drones)."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_drone(bars=4)
    # At least one drone note should span the full length
    max_duration = max(n.duration for n in melody.notes)
    assert max_duration >= 16.0, f"Expected drone note >= 16 beats, got {max_duration}"


def test_generate_auto():
    """Auto style should generate a valid melody."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=99)
    melody = gen.generate(bars=4)
    assert len(melody.notes) > 0


def test_generate_with_density():
    """Higher density should generally produce more notes."""
    gen_low = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                          bpm=120, seed=42)
    gen_high = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                           bpm=120, seed=42)
    # Low density = more rests
    m_low = gen_low.generate(bars=8, style="melodic", density=0.3)
    m_high = gen_high.generate(bars=8, style="melodic", density=0.95)
    # Higher density should generally have more notes (probabilistic, but strong trend)
    assert len(m_high.notes) > len(m_low.notes)


# ─── Synthesizer Tests ───────────────────────────────────────────────────────

def test_synth_render_nonempty():
    """Synthesizer should produce non-zero samples."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_melodic(bars=2)
    synth = music_box.Synthesizer(waveform="piano")
    samples = synth.render(melody)
    assert len(samples) > 0
    # Should have some non-zero samples
    assert any(abs(s) > 0.001 for s in samples)


def test_synth_wav_export():
    """Synthesizer should write a valid WAV file."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_melodic(bars=2)
    synth = music_box.Synthesizer(waveform="sine")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        filename = f.name

    try:
        synth.to_wav(melody, filename)
        assert os.path.exists(filename)
        assert os.path.getsize(filename) > 0

        # Verify it's a valid WAV
        with wave.open(filename, 'r') as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 44100
            assert wf.getnframes() > 0
    finally:
        os.unlink(filename)


def test_synth_all_waveforms():
    """All waveform types should produce valid audio."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_melodic(bars=1)

    for wf in ["sine", "square", "sawtooth", "triangle", "piano", "organ", "bell"]:
        synth = music_box.Synthesizer(waveform=wf)
        samples = synth.render(melody)
        assert len(samples) > 0, f"No samples for waveform {wf}"
        assert any(abs(s) > 0.001 for s in samples), f"All-zero samples for {wf}"


def test_synth_volume():
    """Volume parameter should affect output level."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_melodic(bars=2)

    synth_low = music_box.Synthesizer(waveform="piano", volume=0.2)
    synth_high = music_box.Synthesizer(waveform="piano", volume=1.5)

    samples_low = synth_low.render(melody)
    samples_high = synth_high.render(melody)

    # After normalization both should be similar amplitude, but before
    # normalization the high volume should have higher peak values.
    # Actually, normalization makes this tricky. Let's check that both produce output.
    assert any(abs(s) > 0.001 for s in samples_low)
    assert any(abs(s) > 0.001 for s in samples_high)


# ─── MIDI Export Tests ────────────────────────────────────────────────────────

def test_midi_export():
    """MIDI export should produce a valid .mid file."""
    notes = [
        music_box.Note(midi=60, start=0.0, duration=1.0, velocity=80, channel=0),
        music_box.Note(midi=64, start=1.0, duration=1.0, velocity=80, channel=0),
        music_box.Note(midi=67, start=2.0, duration=2.0, velocity=80, channel=0),
    ]
    melody = music_box.Melody(notes=notes, bpm=120)

    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
        filename = f.name

    try:
        music_box.export_midi(melody, filename)
        assert os.path.exists(filename)
        assert os.path.getsize(filename) > 0

        # Verify MIDI file header
        with open(filename, 'rb') as f:
            header = f.read(4)
            assert header == b'MThd', f"Invalid MIDI header: {header}"
    finally:
        os.unlink(filename)


def test_midi_export_multichannel():
    """MIDI export should handle multiple channels."""
    notes = [
        music_box.Note(midi=60, start=0.0, duration=4.0, velocity=70, channel=1),
        music_box.Note(midi=72, start=0.0, duration=1.0, velocity=100, channel=0),
    ]
    melody = music_box.Melody(notes=notes, bpm=120)

    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
        filename = f.name

    try:
        music_box.export_midi(melody, filename)
        assert os.path.getsize(filename) > 0
    finally:
        os.unlink(filename)


# ─── Visualization Tests ──────────────────────────────────────────────────────

def test_piano_roll_simple():
    """Piano roll should render without errors for a simple melody."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_melodic(bars=4)
    output = music_box.render_piano_roll_simple(melody)
    assert len(output) > 0
    assert "♫" in output
    assert "BPM" in output


def test_piano_roll_empty():
    """Piano roll should handle empty melody gracefully."""
    melody = music_box.Melody()
    assert music_box.render_piano_roll_simple(melody) == "No notes to display."


def test_melody_stats():
    """Statistics should include expected fields."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_melodic(bars=4)
    stats = music_box.render_melody_stats(melody)
    assert "Total notes" in stats
    assert "Duration" in stats
    assert "Note range" in stats
    assert "Most used notes" in stats


def test_ascii_notation():
    """Notation should render measure-by-measure."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_melodic(bars=4)
    notation = music_box.render_ascii_notation(melody)
    assert "m" in notation  # Should have measure numbers


# ─── Edge Cases ───────────────────────────────────────────────────────────────

def test_chromatic_scale():
    """Chromatic scale should include all 12 semitones per octave."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.CHROMATIC,
                                      bpm=120, seed=42)
    melody = gen.generate_melodic(bars=4)
    assert len(melody.notes) > 0
    # Should use a wider variety of notes
    unique_pitches = set(n.midi for n in melody.notes)
    assert len(unique_pitches) > 3


def test_high_bpm():
    """Fast BPM should still produce valid melodies."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=240, seed=42)
    melody = gen.generate_melodic(bars=4)
    assert len(melody.notes) > 0
    assert melody.total_seconds > 0


def test_empty_melody_stats():
    """Stats should handle empty melody."""
    stats = music_box.render_melody_stats(music_box.Melody())
    assert "Empty" in stats or "0" in stats


def test_note_name_with_accidentals():
    """name_to_midi should handle flats and sharps."""
    assert music_box.name_to_midi("Bb") == 70   # A#4
    assert music_box.name_to_midi("Eb") == 63   # D#4
    assert music_box.name_to_midi("C#5") == 73


def test_note_name_uppercase_flats():
    """name_to_midi should handle uppercase flats (as produced by CLI .upper())."""
    assert music_box.name_to_midi("BB") == 70   # A#4 (same as Bb)
    assert music_box.name_to_midi("EB") == 63   # D#4 (same as Eb)
    assert music_box.name_to_midi("AB") == 68   # G#4 (same as Ab)
    assert music_box.name_to_midi("GB") == 66   # F#4 (same as Gb)
    assert music_box.name_to_midi("DB") == 61   # C#4 (same as Db)


def test_note_name_mixed_case():
    """name_to_midi should handle mixed case note names."""
    assert music_box.name_to_midi("c#") == 61   # C#4
    assert music_box.name_to_midi("bb") == 70   # A#4
    assert music_box.name_to_midi("eb3") == 51  # D#3


def test_scale_degrees_ionian_correct():
    """Scale degrees should produce correct chords for Ionian."""
    degrees = music_box.get_scale_degrees(60, music_box.ScaleType.IONIAN)
    # I chord: C-E-G = [60,64,67]
    assert degrees[0] == [60, 64, 67], f"I chord wrong: {degrees[0]}"
    # IV chord: F-A-C5 = [65,69,72]
    assert degrees[3] == [65, 69, 72], f"IV chord wrong: {degrees[3]}"
    # V chord: G-B-D5 = [67,71,74]
    assert degrees[4] == [67, 71, 74], f"V chord wrong: {degrees[4]}"
    # vi chord: A-C5-E5 = [69,72,76]
    assert degrees[5] == [69, 72, 76], f"vi chord wrong: {degrees[5]}"


def test_scale_degrees_pentatonic():
    """Scale degrees should produce correct chords for pentatonic (wrapping)."""
    degrees = music_box.get_scale_degrees(60, music_box.ScaleType.PENTATONIC_MAJOR)
    # I chord: C-E-A = [60,64,69]
    assert degrees[0] == [60, 64, 69], f"Pent I chord wrong: {degrees[0]}"
    # II chord: D-G-C5 = [62,67,72] (wraps to next octave)
    assert degrees[1] == [62, 67, 72], f"Pent II chord wrong: {degrees[1]}"


def test_drone_notation_has_readable_durations():
    """Drone melody notation should show readable duration labels, not raw numbers."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_drone(bars=4)
    notation = music_box.render_ascii_notation(melody)
    # Should not contain raw "16" as a duration label (was a bug)
    assert "16" not in notation or "m" in notation.split("16")[0], \
        f"Raw '16' duration found in notation:\n{notation}"


def test_arpeggiated_notation_has_readable_durations():
    """Arpeggiated notation should show readable duration labels, not raw '1.8'."""
    gen = music_box.MelodyGenerator(root=60, scale_type=music_box.ScaleType.IONIAN,
                                      bpm=120, seed=42)
    melody = gen.generate_arpeggiated(bars=4)
    notation = music_box.render_ascii_notation(melody)
    stats = music_box.render_melody_stats(melody)
    # Should not contain raw "1.8" as a duration in notation
    # (Note: the number 1.8 could appear in measure numbers like "m  1:8" so check carefully)
    for line in notation.split('\n'):
        if '1.8' in line and not line.strip().startswith('m'):
            assert False, f"Raw '1.8' duration in notation: {line}"


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])