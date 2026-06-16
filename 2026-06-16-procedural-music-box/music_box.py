#!/usr/bin/env python3
"""
Procedural Music Box — Algorithmic melody generator and visualizer.

Generates unique melodies using music theory (scales, chords, rhythmic patterns),
renders them as an ASCII piano roll, and exports them as WAV audio files.

Usage:
    python3 music_box.py                    # Generate a random melody
    python3 music_box.py --seed 42          # Use a specific seed
    python3 music_box.py --scale dorian     # Choose a scale
    python3 music_box.py --bpm 140          # Set tempo
    python3 music_box.py --play             # Play audio after generating
    python3 music_box.py --output song.wav  # Save to specific file
    python3 music_box.py --bars 16         # Generate 16 bars
    python3 music_box.py --interactive      # Choose parameters interactively
"""

import argparse
import math
import random
import struct
import sys
import wave
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


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
    """Convert MIDI note number to frequency in Hz."""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))

def midi_to_name(midi_note: int) -> str:
    """Convert MIDI note number to note name with octave."""
    octave = (midi_note // 12) - 1
    note = NOTE_NAMES[midi_note % 12]
    return f"{note}{octave}"

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

    @property
    def end(self) -> float:
        return self.start + self.duration

    @property
    def freq(self) -> float:
        return midi_to_freq(self.midi)

    @property
    def name(self) -> str:
        return midi_to_name(self.midi)


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
        return self.total_beats * 60.0 / self.bpm


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
        """Generate a melody using stepwise motion with occasional leaps."""
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

            # Rest probability
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
        """Generate arpeggiated patterns from chord progressions."""
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

        # How many notes per chord (arpeggio speed)
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
                # Vary velocity
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

    def generate(self, bars: int = 8, style: str = "auto") -> Melody:
        """Generate a melody in the given style."""
        if style == "auto":
            style = self.rng.choice(["melodic", "melodic", "arpeggiated", "counterpoint", "drone"])

        if style == "melodic":
            return self.generate_melodic(bars)
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
    """Renders a Melody to audio samples."""

    def __init__(self, sample_rate: int = 44100, waveform: str = "piano"):
        self.sample_rate = sample_rate
        self.waveform = waveform

    def _osc(self, freq: float, t: float) -> float:
        """Basic oscillator."""
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

    def _envelope(self, note: Note, t: float, sr: int) -> float:
        """ADSR envelope."""
        beat_duration = 60.0 / 120  # Will be overridden by melody bpm
        note_dur_sec = note.duration * 60.0 / 120  # placeholder, fixed below
        attack = 0.01
        decay = 0.1
        sustain = 0.7
        release = 0.15
        note_time = t
        release_time = note_dur_sec

        if note_time < attack:
            return note_time / attack
        elif note_time < attack + decay:
            return 1.0 - (1.0 - sustain) * (note_time - attack) / decay
        elif note_time < release_time:
            return sustain
        elif note_time < release_time + release:
            return sustain * (1.0 - (note_time - release_time) / release)
        else:
            return 0.0

    def render(self, melody: Melody) -> List[float]:
        """Render a melody to audio samples."""
        total_seconds = melody.total_seconds + 1.0  # Extra for reverb tail
        total_samples = int(total_seconds * self.sample_rate)
        samples = [0.0] * total_samples

        beat_dur = 60.0 / melody.bpm

        for note in melody.notes:
            freq = note.freq
            start_sec = note.start * beat_dur
            dur_sec = note.duration * beat_dur
            amp = note.velocity / 127.0

            start_sample = int(start_sec * self.sample_rate)
            end_sample = int((start_sec + dur_sec + 0.2) * self.sample_rate)  # 0.2s release

            for i in range(start_sample, min(end_sample, total_samples)):
                t = i / self.sample_rate - start_sec
                note_time = i / self.sample_rate - start_sec

                # Envelope
                attack = 0.008
                decay_time = 0.15
                sustain_level = 0.6
                release_time = 0.15
                dur_actual = dur_sec

                if note_time < 0:
                    env = 0.0
                elif note_time < attack:
                    env = note_time / attack
                elif note_time < attack + decay_time:
                    env = 1.0 - (1.0 - sustain_level) * (note_time - attack) / decay_time
                elif note_time < dur_actual:
                    env = sustain_level
                elif note_time < dur_actual + release_time:
                    env = sustain_level * (1.0 - (note_time - dur_actual) / release_time)
                else:
                    env = 0.0

                osc_val = self._osc(freq, i / self.sample_rate)
                samples[i] += osc_val * env * amp * 0.3

        # Normalize
        max_val = max(abs(s) for s in samples) if samples else 1.0
        if max_val > 0:
            scale = 0.9 / max_val
            samples = [s * scale for s in samples]

        return samples

    def to_wav(self, melody: Melody, filename: str) -> None:
        """Export melody to WAV file."""
        samples = self.render(melody)

        with wave.open(filename, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)

            data = b''
            for s in samples:
                val = int(max(-32767, min(32767, s * 32767)))
                data += struct.pack('<h', val)
            wf.writeframes(data)

        return


# ─── ASCII Piano Roll Visualization ─────────────────────────────────────────

def render_piano_roll(melody: Melody, width: int = 80, height: int = 24) -> str:
    """Render a piano roll visualization as ASCII art."""
    if not melody.notes:
        return "No notes to display."

    # Determine note range
    min_midi = min(n.midi for n in melody.notes)
    max_midi = max(n.midi for n in melody.notes)
    range_size = max_midi - min_midi + 1

    # Use full semitone range
    note_range = list(range(min_midi - 1, max_midi + 2))
    if len(note_range) < 5:
        # Expand if too narrow
        center = (min_midi + max_midi) // 2
        note_range = list(range(center - 6, center + 7))

    total_beats = melody.total_beats

    # Create grid
    grid = {}
    for note in melody.notes:
        start_col = int(note.start / total_beats * (width - 8)) if total_beats > 0 else 0
        end_col = int(note.end / total_beats * (width - 8)) if total_beats > 0 else 0
        start_col = max(0, min(start_col, width - 9))
        end_col = max(start_col + 1, min(end_col, width - 8))

        for row_idx, midi in enumerate(note_range):
            if midi == note.midi:
                for col in range(start_col, end_col):
                    if col == start_col:
                        grid[(row_idx, col)] = '▐'
                    elif col == end_col - 1:
                        grid[(row_idx, col)] = '▌'
                    else:
                        grid[(row_idx, col)] = '█'

    # Build output
    lines = []
    lines.append(f"  Procedural Music Box — {melody.scale_type.value} scale on {midi_to_name(melody.root)}")
    lines.append(f"  BPM: {melody.bpm} | Beats: {melody.total_beats:.1f} | Notes: {len(melody.notes)}")
    lines.append("")

    # Time axis
    time_axis = "  " + " " * 6
    for i in range(width - 8):
        beat_mark = (i / (width - 8)) * total_beats
        if total_beats > 0 and int(beat_mark) % 4 == 0 and (i + 1) % max(1, (width - 8) // max(1, int(total_beats))) < 2:
            time_axis += '│'
        else:
            time_axis += ' '
    lines.append(time_axis)

    # Draw grid
    for row_idx, midi in enumerate(reversed(note_range)):
        label = midi_to_name(midi)
        if len(label) < 3:
            label = label.ljust(3)
        is_sharp = '#' in midi_to_name(midi)
        bg = '░' if is_sharp else ' '

        row = f"{label:>3s} │"
        for col in range(width - 8):
            cell = grid.get((row_idx if not reversed else list(reversed(note_range)).index(midi), col))
            if cell:
                row += cell
            else:
                row += bg
        row += '│'
        lines.append(row)

    lines.append(f"  {'─' * (width - 4)}")
    lines.append(f"  Time: 0{' ' * (width - 14)}{total_beats:.0f} beats")

    return '\n'.join(lines)


def render_piano_roll_simple(melody: Melody, width: int = 72, height: int = 20) -> str:
    """Simpler, cleaner piano roll visualization."""
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
    scale_notes = build_scale_notes(melody.root, melody.scale_type)
    degree_counts = defaultdict(int)
    for n in melody.notes:
        degree_counts[n.midi] += 1

    most_common = sorted(degree_counts.items(), key=lambda x: -x[1])[:5]

    lines = []
    lines.append("─── Melody Statistics ───")
    lines.append(f"  Total notes:      {len(melody.notes)}")
    lines.append(f"  Duration:         {melody.total_seconds:.1f}s ({melody.total_beats:.1f} beats)")
    lines.append(f"  Note range:       {midi_to_name(min(pitches))} — {midi_to_name(max(pitches))} ({max(pitches)-min(pitches)} semitones)")
    lines.append(f"  Average interval: {sum(intervals)/len(intervals):.1f} semitones" if intervals else "  Average interval: N/A")
    lines.append(f"  Avg velocity:     {sum(velocities)/len(velocities):.0f}")
    lines.append(f"  Most used notes:  {', '.join(f'{midi_to_name(n)}×{c}' for n, c in most_common)}")
    lines.append(f"  Duration types:   {', '.join(f'{d}×{durations.count(d)}' for d in sorted(set(durations))[:6])}")

    return '\n'.join(lines)


def render_ascii_notation(melody: Melody) -> str:
    """Render melody as a simplified text notation."""
    lines = []
    lines.append("─── Melody Notation ───")

    current_beat = 0.0
    measure_num = 0
    measure_str = ""

    for note in sorted(melody.notes, key=lambda n: n.start):
        # Add rests
        if note.start > current_beat:
            rest_beats = note.start - current_beat
            measure_str += f" r{rest_beats:.2g}"
            current_beat = note.start

        # Determine duration name
        if note.duration >= 4.0:
            dur_name = "w"  # whole
        elif note.duration >= 2.0:
            dur_name = "h"  # half
        elif note.duration >= 1.0:
            dur_name = "q"  # quarter
        elif note.duration >= 0.5:
            dur_name = "e"  # eighth
        else:
            dur_name = "s"  # sixteenth

        measure_str += f" {note.name}{dur_name}"
        current_beat = note.start + note.duration

        # New measure
        if current_beat >= (measure_num + 1) * 4.0:
            lines.append(f"  m{measure_num + 1:>3d}: {measure_str.strip()}")
            measure_str = ""
            measure_num += 1

    if measure_str.strip():
        lines.append(f"  m{measure_num + 1:>3d}: {measure_str.strip()}")

    return '\n'.join(lines)


# ─── Interactive Mode ────────────────────────────────────────────────────────

def interactive_mode() -> None:
    """Interactive CLI for choosing parameters."""
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
        bpm = max(60, min(200, bpm))
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
    synth = Synthesizer(waveform="piano")
    synth.to_wav(melody, filename)
    print(f"\n💾 Saved to: {filename}")


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
        """
    )

    parser.add_argument('--seed', type=int, default=None, help='Random seed for reproducibility')
    parser.add_argument('--root', type=str, default='C', help='Root note (C, D, E, etc.)')
    parser.add_argument('--scale', type=str, default='ionian',
                       choices=ScaleType.names(),
                       help='Scale/mode type')
    parser.add_argument('--bpm', type=int, default=120, help='Tempo in BPM (60-240)')
    parser.add_argument('--bars', type=int, default=8, help='Number of bars (4-32)')
    parser.add_argument('--style', type=str, default='auto',
                       choices=['melodic', 'arpeggiated', 'counterpoint', 'drone', 'auto'],
                       help='Composition style')
    parser.add_argument('--waveform', type=str, default='piano',
                       choices=['sine', 'square', 'sawtooth', 'triangle', 'piano', 'organ', 'bell'],
                       help='Synthesis waveform')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='Output WAV filename')
    parser.add_argument('--play', action='store_true', help='Play audio after generating')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--stats', action='store_true', default=True, help='Show statistics')
    parser.add_argument('--notation', action='store_true', default=True, help='Show notation')
    parser.add_argument('--no-piano-roll', action='store_true', help='Hide piano roll')

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
        return

    # Parse root note
    root_str = args.root.upper().strip()
    if root_str in NOTE_NAMES:
        root_midi = 60 + NOTE_NAMES.index(root_str)
    elif len(root_str) >= 2 and root_str[:-1] in NOTE_NAMES:
        # e.g., "C4" or "A3"
        note_part = root_str[:-1]
        octave = int(root_str[-1])
        root_midi = (octave + 1) * 12 + NOTE_NAMES.index(note_part)
    else:
        print(f"Unknown root note: {args.root}. Using C.")
        root_midi = 60

    scale_type = ScaleType(args.scale)

    # Use random seed or generate one
    seed = args.seed if args.seed is not None else random.randint(0, 999999)

    print(f"╔══════════════════════════════════════╗")
    print(f"║   ♫ Procedural Music Box ♫          ║")
    print(f"╚══════════════════════════════════════╝")
    print()
    print(f"  Root:  {midi_to_name(root_midi)}")
    print(f"  Scale: {scale_type.value}")
    print(f"  BPM:   {args.bpm}")
    print(f"  Bars:  {args.bars}")
    print(f"  Style: {args.style}")
    print(f"  Seed:  {seed}")
    print(f"  Sound: {args.waveform}")
    print()

    # Generate
    gen = MelodyGenerator(root=root_midi, scale_type=scale_type, bpm=args.bpm, seed=seed)
    melody = gen.generate(bars=args.bars, style=args.style)

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
    synth = Synthesizer(waveform=args.waveform)
    synth.to_wav(melody, filename)
    print(f"💾 Saved WAV to: {filename}")
    print(f"   Duration: {melody.total_seconds:.1f}s | Sample rate: {synth.sample_rate}Hz")

    # Play if requested
    if args.play:
        import subprocess
        try:
            subprocess.run(['aplay', filename], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                subprocess.run(['ffplay', '-nodisp', '-autoexit', filename],
                             check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("⚠ Could not play audio (no player found). The WAV file was saved.")


if __name__ == '__main__':
    main()