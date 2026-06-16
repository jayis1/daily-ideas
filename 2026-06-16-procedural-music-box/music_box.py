#!/usr/bin/env python3
"""
Procedural Music Box — Algorithmic melody generator and visualizer.

Generates unique melodies using music theory (scales, chords, rhythmic patterns),
renders them as an ASCII piano roll, and exports them as WAV or MIDI audio files.
Every run produces a different composition, or lock it in with a seed for reproducibility.

Usage:
    python3 music_box.py                    # Generate a random melody
    python3 music_box.py --seed 42          # Use a specific seed
    python3 music_box.py --scale dorian     # Choose a scale
    python3 music_box.py --bpm 140          # Set tempo
    python3 music_box.py --play             # Play audio after generating
    python3 music_box.py --output song.wav  # Save to specific file
    python3 music_box.py --bars 16          # Generate 16 bars
    python3 music_box.py --interactive       # Choose parameters interactively
    python3 music_box.py --midi-out song.mid # Also export as MIDI
"""

import argparse
import math
import os
import random
import struct
import subprocess
import sys
import wave
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

__version__ = "1.1.0"

# ─── Music Theory ────────────────────────────────────────────────────────────

class ScaleType(Enum):
    IONIAN = "ionian"        # Major
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"
    AEOLIAN = "aeolian"      # Natural minor
    LOCRIAN = "locrian"
    PENTATONIC_MAJOR = "pentatonic_major"
    PENTATONIC_MINOR = "pentatonic_minor"
    BLUES = "blues"
    HARMONIC_MINOR = "harmonic_minor"
    MELODIC_MINOR = "melodic_minor"
    WHOLE_TONE = "whole_tone"
    CHROMATIC = "chromatic"

    @classmethod
    def names(cls):
        return [s.value for s in cls]


# Intervals as semitone offsets from root
SCALE_INTERVALS = {
    ScaleType.IONIAN:             [0, 2, 4, 5, 7, 9, 11],
    ScaleType.DORIAN:             [0, 2, 3, 5, 7, 9, 10],
    ScaleType.PHRYGIAN:           [0, 1, 3, 5, 7, 8, 10],
    ScaleType.LYDIAN:             [0, 2, 4, 6, 7, 9, 11],
    ScaleType.MIXOLYDIAN:         [0, 2, 4, 5, 7, 9, 10],
    ScaleType.AEOLIAN:            [0, 2, 3, 5, 7, 8, 10],
    ScaleType.LOCRIAN:            [0, 1, 3, 5, 6, 8, 10],
    ScaleType.PENTATONIC_MAJOR:   [0, 2, 4, 7, 9],
    ScaleType.PENTATONIC_MINOR:   [0, 3, 5, 7, 10],
    ScaleType.BLUES:              [0, 3, 5, 6, 7, 10],
    ScaleType.HARMONIC_MINOR:     [0, 2, 3, 5, 7, 8, 11],
    ScaleType.MELODIC_MINOR:      [0, 2, 3, 5, 7, 9, 11],
    ScaleType.WHOLE_TONE:         [0, 2, 4, 6, 8, 10],
    ScaleType.CHROMATIC:          list(range(12)),
}

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def midi_to_freq(midi_note: int) -> float:
    """Convert MIDI note number to frequency in Hz (A440 tuning)."""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def midi_to_name(midi_note: int) -> str:
    """Convert MIDI note number to note name with octave (e.g., C4, A#5)."""
    octave = (midi_note // 12) - 1
    note = NOTE_NAMES[midi_note % 12]
    return f"{note}{octave}"


def name_to_midi(name: str) -> int:
    """Convert a note name like 'C', 'C#4', 'B3' to a MIDI note number.

    If no octave is given, defaults to octave 4 (MIDI 60 for C).
    Supports both '#' and 'b' for accidentals (e.g., 'Bb' -> A#).
    """
    name = name.strip()

    # Handle flats by converting to sharps
    flat_map = {'Db': 'C#', 'Eb': 'D#', 'Fb': 'E', 'Gb': 'F#',
                'Ab': 'G#', 'Bb': 'A#', 'Cb': 'B'}
    if name in flat_map:
        name = flat_map[name]
    elif len(name) >= 2 and name[:2] in flat_map:
        name = flat_map[name[:2]] + name[2:]

    # Parse octave
    if name and name[-1].isdigit():
        octave = int(name[-1])
        note_part = name[:-1]
    else:
        octave = 4
        note_part = name

    if note_part in NOTE_NAMES:
        return (octave + 1) * 12 + NOTE_NAMES.index(note_part)
    raise ValueError(f"Unknown note name: {name!r}")


def build_scale_notes(root: int, scale_type: ScaleType) -> List[int]:
    """Build a list of MIDI notes spanning ~3 octaves for the given scale."""
    intervals = SCALE_INTERVALS[scale_type]
    notes = []
    for octave_offset in range(-1, 3):  # 4 octaves of range
        for interval in intervals:
            note = root + octave_offset * 12 + interval
            if 36 <= note <= 96:  # C2 to C7
                notes.append(note)
    return sorted(set(notes))


def get_scale_degrees(root: int, scale_type: ScaleType) -> List[List[int]]:
    """Return chords for each scale degree (triads built on 3rds)."""
    intervals = SCALE_INTERVALS[scale_type]
    n = len(intervals)
    chords = []
    for deg in range(n):
        third = intervals[(deg + 2) % n]
        fifth = intervals[(deg + 4) % n]
        root_note = root + intervals[deg]
        chord = sorted([root_note, root + third, root + fifth])
        chords.append(chord)
    return chords


# ─── Note / Melody Data Structures ──────────────────────────────────────────

@dataclass
class Note:
    midi: int           # MIDI note number
    start: float        # Start time in beats
    duration: float     # Duration in beats
    velocity: int = 80  # Velocity 0-127
    channel: int = 0    # MIDI channel (for multi-voice)

    @property
    def end(self) -> float:
        return self.start + self.duration

    @property
    def freq(self) -> float:
        return midi_to_freq(self.midi)

    @property
    def name(self) -> str:
        return midi_to_name(self.midi)

    def is_sharp(self) -> bool:
        """Return True if this note is a sharp/flat."""
        return self.midi % 12 in {1, 3, 6, 8, 10}


@dataclass
class Melody:
    notes: List[Note] = field(default_factory=list)
    bpm: int = 120
    root: int = 60       # Middle C
    scale_type: ScaleType = ScaleType.IONIAN

    @property
    def total_beats(self) -> float:
        if not self.notes:
            return 0.0
        return max(n.end for n in self.notes)

    @property
    def total_seconds(self) -> float:
        return self.total_beats * 60.0 / max(1, self.bpm)

    def voices(self) -> dict:
        """Group notes by channel into separate voices."""
        voices = defaultdict(list)
        for n in self.notes:
            voices[n.channel].append(n)
        return dict(voices)

    def transpose(self, semitones: int) -> 'Melody':
        """Return a new Melody transposed by the given number of semitones."""
        new_notes = [
            Note(midi=n.midi + semitones, start=n.start, duration=n.duration,
                 velocity=n.velocity, channel=n.channel)
            for n in self.notes
        ]
        return Melody(notes=new_notes, bpm=self.bpm,
                      root=self.root + semitones, scale_type=self.scale_type)


# ─── Melody Generation Algorithms ───────────────────────────────────────────

class MelodyGenerator:
    """Generates melodies using various algorithmic composition techniques."""

    def __init__(self, root: int = 60, scale_type: ScaleType = ScaleType.IONIAN,
                 bpm: int = 120, seed: Optional[int] = None):
        self.root = root
        self.scale_type = scale_type
        self.bpm = bpm
        self.rng = random.Random(seed)
        self.scale_notes = build_scale_notes(root, scale_type)

    def _note_in_scale(self, midi: int) -> bool:
        return midi in self.scale_notes

    def _nearest_scale_note(self, midi: int, direction: int = 0) -> int:
        """Find nearest note in scale. direction: -1=down, 0=nearest, 1=up."""
        if midi in self.scale_notes:
            return midi
        if direction <= 0:
            below = [n for n in self.scale_notes if n <= midi]
            if below:
                return max(below)
        if direction >= 0:
            above = [n for n in self.scale_notes if n >= midi]
            if above:
                return min(above)
        # Fallback: middle of scale
        return self.scale_notes[len(self.scale_notes) // 2]

    def _scale_index(self, midi: int) -> int:
        """Get index of note in scale, or nearest."""
        if midi in self.scale_notes:
            return self.scale_notes.index(midi)
        nearest = self._nearest_scale_note(midi)
        return self.scale_notes.index(nearest)

    def _step(self, current_idx: int, step: int) -> int:
        """Step up or down in the scale by given number of scale degrees."""
        new_idx = current_idx + step
        new_idx = max(0, min(len(self.scale_notes) - 1, new_idx))
        return new_idx

    def generate_melodic(self, bars: int = 8, density: float = 0.7) -> Melody:
        """Generate a melody using stepwise motion with occasional leaps.

        Args:
            bars: Number of bars (4/4 time).
            density: Note density 0.0–1.0 (higher = fewer rests).
        """
        melody = Melody(bpm=self.bpm, root=self.root, scale_type=self.scale_type)
        current_idx = len(self.scale_notes) // 2  # Start in middle of range
        beat = 0.0
        total_beats = bars * 4  # 4/4 time

        # Rhythm patterns (in beats)
        rhythm_pool = [0.25, 0.5, 0.5, 1.0, 1.0, 1.0, 2.0]

        while beat < total_beats:
            remaining = total_beats - beat

            # Choose duration
            if remaining < 0.25:
                break
            max_dur = min(remaining, 4.0)
            if beat % 4 < 0.01:  # On a downbeat — tend longer
                dur_options = [d for d in rhythm_pool if d <= max_dur and d >= 0.5]
            else:
                dur_options = [d for d in rhythm_pool if d <= max_dur]

            if not dur_options:
                break

            # Rest probability (inversely related to density)
            if self.rng.random() > density:
                rest_dur = self.rng.choice([0.25, 0.5, 1.0])
                rest_dur = min(rest_dur, remaining)
                beat += rest_dur
                continue

            duration = self.rng.choice(dur_options)

            # Determine melodic interval
            r = self.rng.random()
            if r < 0.50:  # Stepwise
                step = self.rng.choice([-1, 1]) * self.rng.choice([1, 1, 2])
            elif r < 0.75:  # Small leap
                step = self.rng.choice([-1, 1]) * self.rng.choice([2, 3, 4])
            elif r < 0.90:  # Large leap
                step = self.rng.choice([-1, 1]) * self.rng.choice([4, 5, 6, 7])
            else:  # Big jump (exciting!)
                step = self.rng.choice([-1, 1]) * self.rng.choice([7, 8, 10, 12])

            current_idx = self._step(current_idx, step)

            # Velocity variation
            vel = 60 + int(self.rng.gauss(0, 15))
            vel = max(30, min(127, vel))
            # Accent downbeats
            if beat % 4 < 0.01:
                vel = min(127, vel + 20)

            note = Note(
                midi=self.scale_notes[current_idx],
                start=round(beat * 4) / 4,  # Quantize to 16th notes
                duration=duration,
                velocity=vel,
            )
            melody.notes.append(note)
            beat += duration

        return melody

    def generate_arpeggiated(self, bars: int = 8, pattern: str = "up") -> Melody:
        """Generate arpeggiated patterns from chord progressions.

        Args:
            bars: Number of bars (4/4 time).
            pattern: Arpeggio pattern — 'up', 'down', 'up_down', 'random'.
        """
        melody = Melody(bpm=self.bpm, root=self.root, scale_type=self.scale_type)
        degrees = get_scale_degrees(self.root, self.scale_type)

        # Common progressions
        progressions = {
            "pop":      [0, 5, 6, 3],   # I-V-vi-iii
            "classic":  [0, 3, 4, 4],   # I-IV-V-V
            "jazzy":    [0, 2, 5, 0],   # I-iii-V-I
            "sad":      [5, 3, 0, 4],   # vi-IV-I-V
            "folk":     [0, 3, 0, 4],   # I-IV-I-V
        }
        prog_key = self.rng.choice(list(progressions.keys()))
        progression = progressions[prog_key]

        # How many notes per beat (arpeggio speed)
        notes_per_beat = self.rng.choice([2, 3, 4])  # 8th, triplet, 16th
        note_dur = 4.0 / notes_per_beat

        beat = 0.0
        total_beats = bars * 4

        # Arpeggio patterns
        arp_patterns = {
            "up":        lambda c: c,
            "down":      lambda c: list(reversed(c)),
            "up_down":   lambda c: c + list(reversed(c[1:-1])),
            "random":    lambda c: self.rng.sample(c, len(c)),
        }

        for bar in range(bars):
            chord_deg = progression[bar % len(progression)]
            chord_notes = degrees[chord_deg % len(degrees)]
            # Extend chord across octaves
            extended = []
            for oct_shift in [0, 12]:
                for cn in chord_notes:
                    extended.append(cn + oct_shift)
            extended = sorted(set([n for n in extended if 36 <= n <= 96]))

            if pattern == "random":
                chosen_pattern = self.rng.choice(list(arp_patterns.keys()))
            else:
                chosen_pattern = pattern

            arp_order = arp_patterns[chosen_pattern](extended)

            beat_in_bar = 0.0
            note_idx = 0
            while beat_in_bar < 4.0:
                if beat >= total_beats:
                    break
                midi = arp_order[note_idx % len(arp_order)]
                # Vary velocity: accent on beat
                beat_in_bar_int = int(beat_in_bar * notes_per_beat)
                vel = 70 + (15 if beat_in_bar_int % notes_per_beat == 0 else 0)
                vel = max(40, min(127, vel + int(self.rng.gauss(0, 8))))

                note = Note(
                    midi=midi,
                    start=beat,
                    duration=note_dur * 0.9,  # Slight staccato
                    velocity=vel,
                )
                melody.notes.append(note)
                beat_in_bar += note_dur
                beat += note_dur
                note_idx += 1

        return melody

    def generate_counterpoint(self, bars: int = 8) -> Melody:
        """Generate two voices in simple counterpoint and merge them."""
        melody = Melody(bpm=self.bpm, root=self.root, scale_type=self.scale_type)

        # Generate a bass line (slow)
        bass_root = self.root - 24  # Two octaves down
        if bass_root < 36:
            bass_root = self.root - 12
        bass_scale = build_scale_notes(bass_root, self.scale_type)
        degrees = get_scale_degrees(bass_root, self.scale_type)

        progression = [0, 3, 4, 0]  # I-IV-V-I

        beat = 0.0
        for bar in range(bars):
            # Bass: whole notes
            chord_deg = progression[bar % len(progression)]
            bass_note = bass_scale[min(chord_deg, len(bass_scale) - 1)]
            melody.notes.append(Note(
                midi=bass_note,
                start=beat,
                duration=4.0,
                velocity=70,
                channel=1,  # Voice 2 channel
            ))

            # Melody: faster notes over the bass
            melody_idx = len(self.scale_notes) // 2
            sub_beat = beat
            for _ in range(self.rng.choice([4, 6, 8])):
                step = self.rng.choice([-2, -1, 1, 1, 2])
                melody_idx = self._step(melody_idx, step)
                melody.notes.append(Note(
                    midi=self.scale_notes[melody_idx],
                    start=sub_beat,
                    duration=1.0 if self.rng.random() < 0.3 else 0.5,
                    velocity=self.rng.randint(60, 100),
                    channel=0,  # Voice 1 channel
                ))
                sub_beat += 0.5

            beat += 4.0

        return melody

    def generate_drone(self, bars: int = 8) -> Melody:
        """Generate a drone-based piece with slowly evolving melody."""
        melody = Melody(bpm=self.bpm, root=self.root, scale_type=self.scale_type)

        # Drone on root (2 octaves)
        melody.notes.append(Note(midi=self.root, start=0.0, duration=bars * 4.0, velocity=50))
        melody.notes.append(Note(midi=self.root - 12, start=0.0, duration=bars * 4.0, velocity=50))

        # Fifth drone
        fifth = self._nearest_scale_note(self.root + 7)
        if fifth != self.root:
            melody.notes.append(Note(midi=fifth, start=0.0, duration=bars * 4.0, velocity=40))

        # Slow melody
        current_idx = len(self.scale_notes) // 2
        beat = 0.0
        while beat < bars * 4.0:
            step = self.rng.choice([-1, 0, 0, 1])  # Lots of held notes
            current_idx = self._step(current_idx, step)
            dur = self.rng.choice([1.0, 2.0, 2.0, 3.0, 4.0])
            melody.notes.append(Note(
                midi=self.scale_notes[current_idx],
                start=beat,
                duration=min(dur, bars * 4.0 - beat),
                velocity=self.rng.randint(50, 90),
            ))
            beat += dur

        return melody

    def generate(self, bars: int = 8, style: str = "auto",
                 density: float = 0.7) -> Melody:
        """Generate a melody in the given style.

        Args:
            bars: Number of bars (4/4 time).
            style: Composition style — 'melodic', 'arpeggiated',
                   'counterpoint', 'drone', or 'auto'.
            density: Note density for melodic style (0.0–1.0).
        """
        if style == "auto":
            style = self.rng.choice(["melodic", "melodic", "arpeggiated",
                                      "counterpoint", "drone"])

        if style == "melodic":
            return self.generate_melodic(bars, density=density)
        elif style == "arpeggiated":
            return self.generate_arpeggiated(bars)
        elif style == "counterpoint":
            return self.generate_counterpoint(bars)
        elif style == "drone":
            return self.generate_drone(bars)
        else:
            return self.generate_melodic(bars)


# ─── Audio Synthesis ─────────────────────────────────────────────────────────

class Synthesizer:
    """Renders a Melody to audio samples using additive waveform synthesis."""

    # ADSR envelope presets per waveform type
    ENVELOPE_PRESETS = {
        "sine":     {"attack": 0.01,  "decay": 0.1,  "sustain": 0.8, "release": 0.15},
        "square":   {"attack": 0.005, "decay": 0.05, "sustain": 0.7, "release": 0.1},
        "sawtooth": {"attack": 0.005, "decay": 0.08, "sustain": 0.6, "release": 0.12},
        "triangle": {"attack": 0.01,  "decay": 0.1,  "sustain": 0.75,"release": 0.15},
        "piano":    {"attack": 0.008, "decay": 0.15, "sustain": 0.6, "release": 0.2},
        "organ":    {"attack": 0.02,  "decay": 0.05, "sustain": 0.85,"release": 0.1},
        "bell":     {"attack": 0.001, "decay": 0.5,  "sustain": 0.3, "release": 0.8},
    }

    def __init__(self, sample_rate: int = 44100, waveform: str = "piano",
                 volume: float = 1.0):
        self.sample_rate = sample_rate
        self.waveform = waveform
        self.volume = max(0.0, min(2.0, volume))

    def _osc(self, freq: float, t: float) -> float:
        """Basic oscillator generating waveform samples."""
        if freq <= 0:
            return 0.0
        if self.waveform == "sine":
            return math.sin(2 * math.pi * freq * t)
        elif self.waveform == "square":
            return 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        elif self.waveform == "sawtooth":
            return 2.0 * ((freq * t) % 1.0) - 1.0
        elif self.waveform == "triangle":
            phase = (freq * t) % 1.0
            return 4.0 * abs(phase - 0.5) - 1.0
        elif self.waveform == "piano":
            # Simple piano: sine + harmonics with fast decay
            val = math.sin(2 * math.pi * freq * t)
            val += 0.5 * math.sin(2 * math.pi * freq * 2 * t)
            val += 0.25 * math.sin(2 * math.pi * freq * 3 * t)
            val += 0.125 * math.sin(2 * math.pi * freq * 4 * t)
            return val / 1.875
        elif self.waveform == "organ":
            val = math.sin(2 * math.pi * freq * t)
            val += 0.8 * math.sin(2 * math.pi * freq * 2 * t)
            val += 0.6 * math.sin(2 * math.pi * freq * 3 * t)
            val += 0.4 * math.sin(2 * math.pi * freq * 4 * t)
            return val / 2.8
        elif self.waveform == "bell":
            val = math.sin(2 * math.pi * freq * t)
            val += 0.7 * math.sin(2 * math.pi * freq * 2.756 * t)
            val += 0.5 * math.sin(2 * math.pi * freq * 5.404 * t)
            return val / 2.2
        else:
            return math.sin(2 * math.pi * freq * t)

    def _get_envelope(self, waveform: str) -> dict:
        """Return ADSR envelope parameters for the given waveform."""
        return self.ENVELOPE_PRESETS.get(waveform, self.ENVELOPE_PRESETS["piano"])

    def render(self, melody: Melody) -> List[float]:
        """Render a melody to audio samples.

        Returns a list of floating-point sample values in the range [-1, 1].
        """
        if not melody.notes:
            return [0.0]

        total_seconds = melody.total_seconds + 1.0  # Extra for release tail
        total_samples = int(total_seconds * self.sample_rate)
        samples = [0.0] * total_samples

        beat_dur = 60.0 / max(1, melody.bpm)
        env_params = self._get_envelope(self.waveform)

        for note in melody.notes:
            freq = note.freq
            if freq <= 0:
                continue
            start_sec = note.start * beat_dur
            dur_sec = note.duration * beat_dur
            amp = (note.velocity / 127.0) * self.volume

            attack = env_params["attack"]
            decay_time = env_params["decay"]
            sustain_level = env_params["sustain"]
            release_time = env_params["release"]

            start_sample = int(start_sec * self.sample_rate)
            end_sample = int((start_sec + dur_sec + release_time) * self.sample_rate)

            for i in range(start_sample, min(end_sample, total_samples)):
                note_time = i / self.sample_rate - start_sec

                if note_time < 0:
                    env = 0.0
                elif note_time < attack:
                    env = note_time / attack if attack > 0 else 1.0
                elif note_time < attack + decay_time:
                    env = 1.0 - (1.0 - sustain_level) * (note_time - attack) / decay_time if decay_time > 0 else sustain_level
                elif note_time < dur_sec:
                    env = sustain_level
                elif note_time < dur_sec + release_time:
                    env = sustain_level * (1.0 - (note_time - dur_sec) / release_time) if release_time > 0 else 0.0
                else:
                    env = 0.0

                osc_val = self._osc(freq, i / self.sample_rate)
                samples[i] += osc_val * env * amp * 0.3

        # Normalize to prevent clipping
        max_val = max(abs(s) for s in samples) if samples else 1.0
        if max_val > 0:
            scale = 0.9 / max_val
            samples = [s * scale for s in samples]

        return samples

    def to_wav(self, melody: Melody, filename: str) -> None:
        """Export melody to WAV file."""
        samples = self.render(melody)

        with wave.open(filename, 'w') as wf:
            wf.setnchannels(1)          # Mono
            wf.setsampwidth(2)           # 16-bit
            wf.setframerate(self.sample_rate)

            data = b''
            for s in samples:
                val = int(max(-32767, min(32767, s * 32767)))
                data += struct.pack('<h', val)
            wf.writeframes(data)


# ─── MIDI Export ──────────────────────────────────────────────────────────────

def export_midi(melody: Melody, filename: str) -> None:
    """Export melody as a Standard MIDI File (Format 0).

    Uses only the Python standard library — builds the binary MIDI file
    byte-by-byte following the SMF spec.

    Args:
        melody: The Melody object to export.
        filename: Path to write the .mid file.
    """
    def _varlen(value: int) -> bytes:
        """Encode a variable-length quantity (MIDI standard)."""
        result = []
        result.append(value & 0x7F)
        value >>= 7
        while value > 0:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.reverse()
        return bytes(result)

    def _to_midi_ticks(beats: float, bpm: int) -> int:
        """Convert beats to MIDI ticks (assuming 480 ticks per quarter note)."""
        return int(beats * 480)

    ticks_per_quarter = 480
    bpm = melody.bpm

    # Build track data
    track_data = bytearray()

    # Tempo meta event (microseconds per quarter note)
    us_per_beat = 60_000_000 // bpm
    track_data += b'\x00'  # delta time 0
    track_data += b'\xFF\x51\x03'  # tempo meta event
    track_data += bytes([(us_per_beat >> 16) & 0xFF, (us_per_beat >> 8) & 0xFF,
                         us_per_beat & 0xFF])

    # Program change — acoustic grand piano (channel 0)
    track_data += b'\x00'  # delta time 0
    track_data += bytes([0xC0, 0x00])

    # Sort notes by start time
    sorted_notes = sorted(melody.notes, key=lambda n: (n.start, n.midi))

    # Build event list: (tick, type, data)
    events = []
    for note in sorted_notes:
        start_tick = _to_midi_ticks(note.start, bpm)
        end_tick = _to_midi_ticks(note.end, bpm)
        channel = note.channel & 0x0F  # Clamp to 0-15
        vel = max(0, min(127, note.velocity))

        # Note On
        events.append((start_tick, 0x90 | channel, note.midi, vel))
        # Note Off
        events.append((end_tick, 0x80 | channel, note.midi, 0))

    # Sort events by tick (note-offs before note-ons at same tick)
    events.sort(key=lambda e: (e[0], 0 if e[1] & 0xF0 == 0x80 else 1))

    # Write events with delta times
    prev_tick = 0
    for tick, status, note_num, vel in events:
        delta = tick - prev_tick
        track_data += _varlen(delta)
        track_data += bytes([status, note_num & 0x7F, vel & 0x7F])
        prev_tick = tick

    # End of track meta event
    track_data += b'\x00\xFF\x2F\x00'

    # Build complete MIDI file
    midi_file = bytearray()

    # Header chunk: MThd
    midi_file += b'MThd'
    midi_file += struct.pack('>I', 6)        # Header length
    midi_file += struct.pack('>H', 0)         # Format 0
    midi_file += struct.pack('>H', 1)         # 1 track
    midi_file += struct.pack('>H', ticks_per_quarter)

    # Track chunk: MTrk
    midi_file += b'MTrk'
    midi_file += struct.pack('>I', len(track_data))
    midi_file += track_data

    with open(filename, 'wb') as f:
        f.write(midi_file)


# ─── ASCII Piano Roll Visualization ─────────────────────────────────────────

def render_piano_roll_simple(melody: Melody, width: int = 72, height: int = 20) -> str:
    """Render a clean, bordered piano roll visualization as ASCII art.

    Args:
        melody: The melody to visualize.
        width: Character width of the display.
        height: Maximum row height.
    """
    if not melody.notes:
        return "No notes to display."

    min_midi = min(n.midi for n in melody.notes)
    max_midi = max(n.midi for n in melody.notes)

    # Ensure reasonable range
    if max_midi - min_midi < 10:
        center = (min_midi + max_midi) // 2
        min_midi = center - 5
        max_midi = center + 5

    total_beats = melody.total_beats
    if total_beats == 0:
        return "Empty melody."

    note_range_size = max_midi - min_midi + 1
    usable_width = width - 10  # Space for note labels and borders
    usable_height = min(height - 4, note_range_size)

    lines = []
    scale_name = f"{midi_to_name(melody.root)} {melody.scale_type.value}"
    lines.append(f"╔{'═' * (width - 2)}╗")
    title = f"♫ {scale_name} | {melody.bpm} BPM | {len(melody.notes)} notes".center(width - 2)
    lines.append(f"║{title}║")
    lines.append(f"╠{'═' * (width - 2)}╣")

    # Map note range to rows
    step = max(1, note_range_size // usable_height)
    display_notes = list(range(max_midi, min_midi - 1, -step))

    for midi in display_notes:
        label = midi_to_name(midi).ljust(4)
        is_sharp = '#' in midi_to_name(midi)
        bg = '·' if is_sharp else ' '

        row = label + '│'
        for beat_step in range(usable_width):
            beat_pos = (beat_step / usable_width) * total_beats

            # Check if any note covers this position
            has_note = False
            is_start = False
            for n in melody.notes:
                if n.midi == midi and n.start <= beat_pos < n.end:
                    has_note = True
                    if abs(n.start - beat_pos) < total_beats / usable_width:
                        is_start = True
                    break

            if has_note:
                if is_start:
                    row += '▸'
                else:
                    row += '━'
            else:
                # Beat markers
                beat_in_measure = beat_pos % 4
                if abs(beat_in_measure) < total_beats / usable_width:
                    row += '┆'
                else:
                    row += bg

        row += '│'
        lines.append(f"║{row.ljust(width - 2)}║")

    lines.append(f"╚{'═' * (width - 2)}╝")

    # Note info
    lines.append("")
    lines.append("Note range: " + ", ".join([
        f"{midi_to_name(n.midi)}" for n in sorted(melody.notes, key=lambda n: n.midi)[:3]
    ]) + " ... " + ", ".join([
        f"{midi_to_name(n.midi)}" for n in sorted(melody.notes, key=lambda n: n.midi)[-3:]
    ]))

    return '\n'.join(lines)


def render_melody_stats(melody: Melody) -> str:
    """Print statistics about the generated melody."""
    if not melody.notes:
        return "Empty melody."

    pitches = [n.midi for n in melody.notes]
    durations = [n.duration for n in melody.notes]
    velocities = [n.velocity for n in melody.notes]
    intervals = [abs(pitches[i+1] - pitches[i]) for i in range(len(pitches)-1)]

    # Count scale degrees used
    degree_counts = defaultdict(int)
    for n in melody.notes:
        degree_counts[n.midi] += 1

    most_common = sorted(degree_counts.items(), key=lambda x: -x[1])[:5]

    # Duration names
    dur_names = {4.0: "whole", 2.0: "half", 1.0: "quarter",
                 0.5: "eighth", 0.25: "16th", 0.75: "dotted-eighth",
                 1.5: "dotted-quarter", 3.0: "dotted-half"}

    lines = []
    lines.append("─── Melody Statistics ───")
    lines.append(f"  Total notes:      {len(melody.notes)}")
    lines.append(f"  Duration:         {melody.total_seconds:.1f}s ({melody.total_beats:.1f} beats)")
    lines.append(f"  Note range:       {midi_to_name(min(pitches))} — {midi_to_name(max(pitches))} ({max(pitches)-min(pitches)} semitones)")
    lines.append(f"  Average interval: {sum(intervals)/len(intervals):.1f} semitones" if intervals else "  Average interval: N/A")
    lines.append(f"  Avg velocity:     {sum(velocities)/len(velocities):.0f}")
    lines.append(f"  Most used notes:  {', '.join(f'{midi_to_name(n)}×{c}' for n, c in most_common)}")
    lines.append(f"  Duration types:   {', '.join(f'{dur_names.get(d, str(d))}×{durations.count(d)}' for d in sorted(set(durations))[:6])}")

    # Voice breakdown
    voices = melody.voices()
    if len(voices) > 1:
        lines.append(f"  Voices:           {len(voices)}")
        for ch, notes in sorted(voices.items()):
            lines.append(f"    Ch{ch}: {len(notes)} notes, range {midi_to_name(min(n.midi for n in notes))}–{midi_to_name(max(n.midi for n in notes))}")

    return '\n'.join(lines)


def render_ascii_notation(melody: Melody) -> str:
    """Render melody as a simplified text notation (measure-by-measure)."""
    lines = []
    lines.append("─── Melody Notation ───")

    current_beat = 0.0
    measure_num = 0
    measure_str = ""

    # Duration name mapping
    dur_map = {4.0: "w", 2.0: "h", 1.0: "q", 0.5: "e", 0.25: "s"}

    for note in sorted(melody.notes, key=lambda n: (n.start, n.midi)):
        # Add rests
        if note.start > current_beat + 0.001:
            rest_beats = note.start - current_beat
            # Find closest duration name
            closest = min(dur_map.keys(), key=lambda d: abs(d - rest_beats))
            if abs(closest - rest_beats) < 0.01:
                measure_str += f" r{dur_map[closest]}"
            else:
                measure_str += f" r{rest_beats:.2g}"
            current_beat = note.start

        # Determine duration name
        dur_name = dur_map.get(note.duration, f"{note.duration:.2g}")

        measure_str += f" {note.name}{dur_name}"
        current_beat = note.start + note.duration

        # New measure
        if current_beat >= (measure_num + 1) * 4.0:
            lines.append(f"  m{measure_num + 1:>3d}: {measure_str.strip()}")
            measure_str = ""
            measure_num = int(current_beat // 4)

    if measure_str.strip():
        lines.append(f"  m{measure_num + 1:>3d}: {measure_str.strip()}")

    return '\n'.join(lines)


# ─── Interactive Mode ────────────────────────────────────────────────────────

def interactive_mode() -> None:
    """Interactive CLI for choosing parameters step by step."""
    print("╔══════════════════════════════════════╗")
    print("║   ♫ Procedural Music Box ♫          ║")
    print("╚══════════════════════════════════════╝")
    print()

    # Root note
    print("Choose a root note:")
    print("  " + "  ".join(f"{i}: {n}" for i, n in enumerate(NOTE_NAMES)))
    root_choice = input("Root note [C=0, default=0]: ").strip()
    try:
        root_idx = int(root_choice) if root_choice else 0
        root_idx = max(0, min(11, root_idx))
    except ValueError:
        root_idx = 0
    root = 60 + root_idx  # C4 = 60

    # Scale
    print("\nChoose a scale:")
    for i, st in enumerate(ScaleType):
        print(f"  {i:>2d}: {st.value}")
    scale_choice = input(f"Scale [0-{len(ScaleType)-1}, default=0]: ").strip()
    try:
        scale_idx = int(scale_choice) if scale_choice else 0
        scale_idx = max(0, min(len(ScaleType) - 1, scale_idx))
    except ValueError:
        scale_idx = 0
    scale_type = list(ScaleType)[scale_idx]

    # BPM
    bpm_choice = input("\nBPM [60-200, default=120]: ").strip()
    try:
        bpm = int(bpm_choice) if bpm_choice else 120
        bpm = max(60, min(240, bpm))
    except ValueError:
        bpm = 120

    # Style
    print("\nComposition style:")
    print("  0: melodic (stepwise melodies)")
    print("  1: arpeggiated (chord patterns)")
    print("  2: counterpoint (two voices)")
    print("  3: drone (ambient)")
    print("  4: random (surprise me!)")
    style_choice = input("Style [0-4, default=4]: ").strip()
    styles = ["melodic", "arpeggiated", "counterpoint", "drone", "auto"]
    try:
        style_idx = int(style_choice) if style_choice else 4
        style_idx = max(0, min(4, style_idx))
    except ValueError:
        style_idx = 4
    style = styles[style_idx]

    # Waveform
    print("\nSynthesis sound:")
    waveforms = ["sine", "square", "sawtooth", "triangle", "piano", "organ", "bell"]
    for i, wf in enumerate(waveforms):
        print(f"  {i}: {wf}")
    wf_choice = input(f"Sound [0-{len(waveforms)-1}, default=4]: ").strip()
    try:
        wf_idx = int(wf_choice) if wf_choice else 4
        wf_idx = max(0, min(len(waveforms) - 1, wf_idx))
    except ValueError:
        wf_idx = 4
    waveform = waveforms[wf_idx]

    # Bars
    bars_choice = input("\nBars [4-32, default=8]: ").strip()
    try:
        bars = int(bars_choice) if bars_choice else 8
        bars = max(4, min(32, bars))
    except ValueError:
        bars = 8

    # Generate
    seed = random.randint(0, 999999)
    print(f"\n🎵 Generating {bars}-bar {scale_type.value} melody in {midi_to_name(root)}...")
    print(f"   Seed: {seed}")

    gen = MelodyGenerator(root=root, scale_type=scale_type, bpm=bpm, seed=seed)
    melody = gen.generate(bars=bars, style=style)

    # Display
    print("\n" + render_piano_roll_simple(melody))
    print()
    print(render_melody_stats(melody))
    print()
    print(render_ascii_notation(melody))

    # Save
    filename = f"melody_{midi_to_name(root)}_{scale_type.value}_{seed}.wav"
    synth = Synthesizer(waveform=waveform)
    synth.to_wav(melody, filename)
    print(f"\n💾 Saved to: {filename}")

    # Offer MIDI export
    midi_choice = input("\nExport as MIDI too? [y/N]: ").strip().lower()
    if midi_choice.startswith('y'):
        midi_filename = filename.replace('.wav', '.mid')
        export_midi(melody, midi_filename)
        print(f"🎹 Saved MIDI to: {midi_filename}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Procedural Music Box — Generate algorithmic melodies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 music_box.py                        # Random melody
  python3 music_box.py --seed 42               # Reproducible
  python3 music_box.py --root D --scale dorian # D Dorian mode
  python3 music_box.py --bpm 140 --style arp   # Fast arpeggios
  python3 music_box.py --interactive            # Choose everything
  python3 music_box.py --waveform bell         # Bell sound
  python3 music_box.py --midi-out song.mid     # Also export MIDI
        """
    )
    parser.add_argument('--version', action='version',
                       version=f'Procedural Music Box v{__version__}')
    parser.add_argument('--seed', type=int, default=None,
                       help='Random seed for reproducibility')
    parser.add_argument('--root', type=str, default='C',
                       help='Root note (C, C#, D, D#, E, F, F#, G, G#, A, A#, B) or with octave (e.g. A3)')
    parser.add_argument('--scale', type=str, default='ionian',
                       choices=ScaleType.names(),
                       help='Scale/mode type')
    parser.add_argument('--bpm', type=int, default=120,
                       help='Tempo in BPM (60-240)')
    parser.add_argument('--bars', type=int, default=8,
                       help='Number of bars (4-32)')
    parser.add_argument('--density', type=float, default=0.7,
                       help='Note density for melodic style (0.0-1.0)')
    parser.add_argument('--style', type=str, default='auto',
                       choices=['melodic', 'arpeggiated', 'counterpoint', 'drone', 'auto'],
                       help='Composition style')
    parser.add_argument('--waveform', type=str, default='piano',
                       choices=['sine', 'square', 'sawtooth', 'triangle', 'piano', 'organ', 'bell'],
                       help='Synthesis waveform')
    parser.add_argument('--volume', type=float, default=1.0,
                       help='Output volume (0.0-2.0, default 1.0)')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='Output WAV filename')
    parser.add_argument('--midi-out', type=str, default=None,
                       help='Also export as MIDI file (.mid)')
    parser.add_argument('--play', action='store_true',
                       help='Play audio after generating')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode')
    parser.add_argument('--stats', action='store_true', default=True,
                       help='Show statistics')
    parser.add_argument('--notation', action='store_true', default=True,
                       help='Show notation')
    parser.add_argument('--no-piano-roll', action='store_true',
                       help='Hide the piano roll visualization')

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
        return

    # Parse root note
    root_str = args.root.upper().strip()
    try:
        root_midi = name_to_midi(root_str)
    except ValueError:
        # Fall back to simple lookup
        if root_str in NOTE_NAMES:
            root_midi = 60 + NOTE_NAMES.index(root_str)
        else:
            print(f"Unknown root note: {args.root}. Using C.")
            root_midi = 60

    # Clamp BPM and bars
    bpm = max(60, min(240, args.bpm))
    bars = max(4, min(32, args.bars))
    density = max(0.1, min(1.0, args.density))
    volume = max(0.1, min(2.0, args.volume))

    scale_type = ScaleType(args.scale)

    # Use random seed or generate one
    seed = args.seed if args.seed is not None else random.randint(0, 999999)

    print(f"╔══════════════════════════════════════╗")
    print(f"║   ♫ Procedural Music Box v{__version__}    ║")
    print(f"╚══════════════════════════════════════╝")
    print()
    print(f"  Root:  {midi_to_name(root_midi)}")
    print(f"  Scale: {scale_type.value}")
    print(f"  BPM:   {bpm}")
    print(f"  Bars:  {bars}")
    print(f"  Style: {args.style}")
    print(f"  Seed:  {seed}")
    print(f"  Sound: {args.waveform}")
    print(f"  Volume: {volume:.1f}")
    print()

    # Generate
    gen = MelodyGenerator(root=root_midi, scale_type=scale_type, bpm=bpm, seed=seed)
    melody = gen.generate(bars=bars, style=args.style, density=density)

    # Display
    if not args.no_piano_roll:
        print(render_piano_roll_simple(melody))
        print()

    if args.stats:
        print(render_melody_stats(melody))
        print()

    if args.notation:
        print(render_ascii_notation(melody))
        print()

    # Save WAV
    filename = args.output or f"melody_{midi_to_name(root_midi)}_{scale_type.value}_{seed}.wav"
    synth = Synthesizer(waveform=args.waveform, volume=volume)
    synth.to_wav(melody, filename)
    file_size = os.path.getsize(filename)
    print(f"💾 Saved WAV to: {filename} ({file_size / 1024:.0f} KB)")
    print(f"   Duration: {melody.total_seconds:.1f}s | Sample rate: {synth.sample_rate}Hz")

    # Save MIDI if requested
    if args.midi_out:
        midi_filename = args.midi_out
        export_midi(melody, midi_filename)
        midi_size = os.path.getsize(midi_filename)
        print(f"🎹 Saved MIDI to: {midi_filename} ({midi_size} bytes)")

    # Play if requested
    if args.play:
        try:
            subprocess.run(['aplay', filename], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(['ffplay', '-nodisp', '-autoexit', filename],
                             check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                try:
                    subprocess.run(['paplay', filename], check=True, capture_output=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print("⚠ Could not play audio (no player found). "
                          "The WAV file was saved.")


if __name__ == '__main__':
    main()