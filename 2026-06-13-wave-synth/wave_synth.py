#!/usr/bin/env python3
"""
Wave Synth — Terminal Audio Waveform Synthesizer

Generate, visualize, mix, and export audio waveforms entirely from the command line.
Supports sine, square, sawtooth, triangle, noise, and harmonic waveforms with
real-time ASCII visualization, envelope shaping, filters, and WAV export.
"""

import argparse
import math
import struct
import wave
import random
import sys
import copy
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ─── Constants ───────────────────────────────────────────────────────────────

SAMPLE_RATE = 44100
MAX_AMPLITUDE = 32767  # 16-bit signed
TERMINAL_WIDTH = 72
TERMINAL_HEIGHT = 16

NOTE_FREQS = {
    'C0': 16.35, 'C#0': 17.32, 'Db0': 17.32, 'D0': 18.35, 'D#0': 19.42,
    'Eb0': 19.42, 'E0': 20.60, 'F0': 21.83, 'F#0': 23.12, 'Gb0': 23.12,
    'G0': 24.50, 'G#0': 25.96, 'Ab0': 25.96, 'A0': 27.50, 'A#0': 29.14,
    'Bb0': 29.14, 'B0': 30.87,
    'C1': 32.70, 'C#1': 34.65, 'D1': 36.71, 'D#1': 38.89, 'E1': 41.20,
    'F1': 43.65, 'F#1': 46.25, 'G1': 49.00, 'G#1': 51.91, 'A1': 55.00,
    'A#1': 58.27, 'B1': 61.74,
    'C2': 65.41, 'C#2': 69.30, 'D2': 73.42, 'D#2': 77.78, 'E2': 82.41,
    'F2': 87.31, 'F#2': 92.50, 'G2': 98.00, 'G#2': 103.83, 'A2': 110.00,
    'A#2': 116.54, 'B2': 123.47,
    'C3': 130.81, 'C#3': 138.59, 'D3': 146.83, 'D#3': 155.56, 'E3': 164.81,
    'F3': 174.61, 'F#3': 185.00, 'G3': 196.00, 'G#3': 207.65, 'A3': 220.00,
    'A#3': 233.08, 'B3': 246.94,
    'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13, 'E4': 329.63,
    'F4': 349.23, 'F#4': 369.99, 'G4': 392.00, 'G#4': 415.30, 'A4': 440.00,
    'A#4': 466.16, 'B4': 493.88,
    'C5': 523.25, 'C#5': 554.37, 'D5': 587.33, 'D#5': 622.25, 'E5': 659.25,
    'F5': 698.46, 'F#5': 739.99, 'G5': 783.99, 'G#5': 830.61, 'A5': 880.00,
    'A#5': 932.33, 'B5': 987.77,
    'C6': 1046.50, 'C#6': 1108.73, 'D6': 1174.66, 'D#6': 1244.51, 'E6': 1318.51,
    'F6': 1396.91, 'F#6': 1479.98, 'G6': 1567.98, 'G#6': 1661.22, 'A6': 1760.00,
    'A#6': 1864.92, 'B6': 1975.53,
    'C7': 2093.00, 'C#7': 2217.46, 'D7': 2349.32, 'D#7': 2489.02, 'E7': 2637.02,
    'F7': 2793.83, 'F#7': 2959.96, 'G7': 3135.96, 'G#7': 3322.44, 'A7': 3520.00,
    'A#7': 3729.81, 'B7': 3951.07,
    'C8': 4186.01,
}


# ─── Waveform Generation ────────────────────────────────────────────────────

def generate_sine(freq: float, duration: float, amplitude: float = 1.0,
                  sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a sine wave."""
    n_samples = int(duration * sample_rate)
    return [amplitude * math.sin(2 * math.pi * freq * i / sample_rate)
            for i in range(n_samples)]


def generate_square(freq: float, duration: float, amplitude: float = 1.0,
                    sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a square wave."""
    n_samples = int(duration * sample_rate)
    return [amplitude * (1.0 if math.sin(2 * math.pi * freq * i / sample_rate) >= 0 else -1.0)
            for i in range(n_samples)]


def generate_sawtooth(freq: float, duration: float, amplitude: float = 1.0,
                     sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a sawtooth wave."""
    n_samples = int(duration * sample_rate)
    return [amplitude * (2.0 * ((freq * i / sample_rate) % 1.0) - 1.0)
            for i in range(n_samples)]


def generate_triangle(freq: float, duration: float, amplitude: float = 1.0,
                     sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a triangle wave."""
    n_samples = int(duration * sample_rate)
    result = []
    for i in range(n_samples):
        phase = (freq * i / sample_rate) % 1.0
        if phase < 0.5:
            result.append(amplitude * (4.0 * phase - 1.0))
        else:
            result.append(amplitude * (3.0 - 4.0 * phase))
    return result


def generate_noise(duration: float, amplitude: float = 1.0,
                  sample_rate: int = SAMPLE_RATE,
                  seed: Optional[int] = None) -> List[float]:
    """Generate white noise."""
    if seed is not None:
        random.seed(seed)
    n_samples = int(duration * sample_rate)
    return [amplitude * (random.random() * 2.0 - 1.0) for _ in range(n_samples)]


def generate_harmonic(freq: float, duration: float, amplitude: float = 1.0,
                      harmonics: Optional[List[Tuple[int, float]]] = None,
                      sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a wave with harmonic overtones. harmonics is a list of (harmonic_number, relative_amplitude)."""
    if harmonics is None:
        harmonics = [(1, 1.0), (2, 0.5), (3, 0.25), (4, 0.125)]
    n_samples = int(duration * sample_rate)
    result = [0.0] * n_samples
    total_amp = sum(a for _, a in harmonics)
    for h_num, h_amp in harmonics:
        h_freq = freq * h_num
        if h_freq > sample_rate / 2:
            continue  # Skip above Nyquist
        for i in range(n_samples):
            result[i] += (amplitude * h_amp / total_amp) * math.sin(2 * math.pi * h_freq * i / sample_rate)
    return result


WAVE_GENERATORS = {
    'sine': generate_sine,
    'square': generate_square,
    'sawtooth': generate_sawtooth,
    'triangle': generate_triangle,
    'noise': lambda f, d, a, sr=SAMPLE_RATE: generate_noise(d, a, sr),
    'harmonic': generate_harmonic,
}


def resolve_freq(note_or_freq: str) -> float:
    """Resolve a note name (e.g. 'A4') or frequency string to a float."""
    note = note_or_freq.strip().upper()
    if note in NOTE_FREQS:
        return NOTE_FREQS[note]
    try:
        return float(note_or_freq)
    except ValueError:
        raise ValueError(f"Unknown note or frequency: {note_or_freq!r}. "
                         f"Examples: 'A4', 'C#5', '440', '261.63'")


# ─── Envelope ────────────────────────────────────────────────────────────────

def apply_adsr(samples: List[float], attack: float = 0.01, decay: float = 0.01,
               sustain: float = 0.7, release: float = 0.1,
               sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply an ADSR envelope to samples."""
    n = len(samples)
    result = [0.0] * n

    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)
    release_samples = int(release * sample_rate)
    sustain_start = attack_samples + decay_samples
    sustain_end = n - release_samples

    if sustain_end < sustain_start:
        sustain_end = sustain_start

    for i in range(n):
        if i < attack_samples and attack_samples > 0:
            # Attack: ramp from 0 to 1
            env = i / attack_samples
        elif i < sustain_start and decay_samples > 0:
            # Decay: ramp from 1 to sustain level
            env = 1.0 - (1.0 - sustain) * (i - attack_samples) / decay_samples
        elif i < sustain_end:
            # Sustain: hold at sustain level
            env = sustain
        elif release_samples > 0 and i < n:
            # Release: ramp from sustain to 0
            remaining = n - i
            env = sustain * remaining / release_samples if remaining < release_samples else sustain
        else:
            env = 0.0
        result[i] = samples[i] * max(0.0, min(1.0, env))

    return result


# ─── Effects ─────────────────────────────────────────────────────────────────

def apply_tremolo(samples: List[float], rate: float = 5.0, depth: float = 0.5,
                  sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply tremolo (amplitude modulation)."""
    result = []
    for i, s in enumerate(samples):
        mod = 1.0 - depth * (0.5 + 0.5 * math.sin(2 * math.pi * rate * i / sample_rate))
        result.append(s * mod)
    return result


def apply_vibrato(samples: List[float], rate: float = 5.0, depth: float = 0.002,
                  sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply vibrato (frequency modulation via delay modulation)."""
    n = len(samples)
    max_delay = int(depth * sample_rate)
    # Pad with zeros at the beginning for delay
    padded = [0.0] * max_delay + samples
    result = []
    for i in range(n):
        delay = int(max_delay * math.sin(2 * math.pi * rate * i / sample_rate))
        idx = i + max_delay + delay
        idx = max(0, min(len(padded) - 1, idx))
        result.append(padded[idx])
    return result


def apply_lowpass(samples: List[float], cutoff: float = 1000.0,
                  sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a simple one-pole low-pass filter."""
    rc = 1.0 / (2.0 * math.pi * cutoff)
    dt = 1.0 / sample_rate
    alpha = dt / (rc + dt)
    result = [0.0] * len(samples)
    result[0] = samples[0]
    for i in range(1, len(samples)):
        result[i] = result[i - 1] + alpha * (samples[i] - result[i - 1])
    return result


def apply_highpass(samples: List[float], cutoff: float = 1000.0,
                   sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a simple one-pole high-pass filter."""
    rc = 1.0 / (2.0 * math.pi * cutoff)
    dt = 1.0 / sample_rate
    alpha = rc / (rc + dt)
    result = [0.0] * len(samples)
    result[0] = samples[0]
    for i in range(1, len(samples)):
        result[i] = alpha * (result[i - 1] + samples[i] - samples[i - 1])
    return result


def apply_distortion(samples: List[float], drive: float = 2.0) -> List[float]:
    """Apply distortion (soft clipping)."""
    result = []
    for s in samples:
        driven = s * drive
        # Soft clip using tanh-like curve
        if abs(driven) > 1.0:
            clipped = math.copysign(1.0, driven)
        else:
            clipped = driven
        result.append(clipped)
    return result


def apply_delay(samples: List[float], delay_time: float = 0.3, feedback: float = 0.4,
                mix: float = 0.5, sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a delay/echo effect."""
    n = len(samples)
    delay_samples = int(delay_time * sample_rate)
    result = [0.0] * (n + delay_samples * 3)  # Extra room for echoes

    # Mix in original
    for i in range(n):
        result[i] += samples[i] * (1.0 - mix)

    # Add delayed signals
    echo = copy.deepcopy(samples)
    fb = feedback
    while fb > 0.01:
        for i in range(len(echo)):
            idx = i + delay_samples
            if idx < len(result):
                result[idx] += echo[i] * fb * mix
        delay_samples_actual = delay_samples
        delay_samples += delay_samples_actual
        fb *= feedback

    # Trim and normalize length
    return result[:n]


def apply_fade_in(samples: List[float], duration: float = 0.05,
                 sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a fade-in."""
    n = min(int(duration * sample_rate), len(samples))
    result = list(samples)
    for i in range(n):
        result[i] *= i / n
    return result


def apply_fade_out(samples: List[float], duration: float = 0.05,
                  sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Apply a fade-out."""
    n = min(int(duration * sample_rate), len(samples))
    result = list(samples)
    for i in range(n):
        result[len(result) - 1 - i] *= i / n
    return result


def normalize(samples: List[float], target_peak: float = 0.95) -> List[float]:
    """Normalize samples to a target peak amplitude."""
    peak = max(abs(s) for s in samples) if samples else 0
    if peak == 0:
        return samples
    scale = target_peak / peak
    return [s * scale for s in samples]


EFFECTS = {
    'tremolo': apply_tremolo,
    'vibrato': apply_vibrato,
    'lowpass': apply_lowpass,
    'highpass': apply_highpass,
    'distortion': apply_distortion,
    'delay': apply_delay,
    'fadein': apply_fade_in,
    'fadeout': apply_fade_out,
    'normalize': normalize,
    'adsr': apply_adsr,
}


# ─── Mixing ──────────────────────────────────────────────────────────────────

def mix_waves(waves: List[List[float]], weights: Optional[List[float]] = None) -> List[float]:
    """Mix multiple wave arrays. Weights default to equal."""
    if not waves:
        return []
    max_len = max(len(w) for w in waves)
    if weights is None:
        weights = [1.0 / len(waves)] * len(waves)
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    result = [0.0] * max_len
    for wave, weight in zip(waves, weights):
        for i in range(len(wave)):
            result[i] += wave[i] * weight
    return result


# ─── ASCII Visualization ─────────────────────────────────────────────────────

def visualize_ascii(samples: List[float], width: int = TERMINAL_WIDTH,
                   height: int = TERMINAL_HEIGHT) -> str:
    """Render an ASCII art waveform visualization."""
    if not samples:
        return "(empty waveform)"

    # Downsample to width points
    step = max(1, len(samples) // width)
    points = []
    for i in range(0, min(len(samples), width * step), step):
        points.append(samples[i])
    if not points:
        points = [0.0]

    # Create canvas
    canvas = [[' '] * len(points) for _ in range(height)]

    for col, val in enumerate(points):
        # Map val from [-1, 1] to row [0, height-1]
        normalized = (val + 1.0) / 2.0  # [0, 1]
        normalized = max(0.0, min(1.0, normalized))
        row = int((1.0 - normalized) * (height - 1))

        # Draw the waveform line
        # Fill from center to the point
        center_row = height // 2
        min_row = min(row, center_row)
        max_row = max(row, center_row)

        for r in range(min_row, max_row + 1):
            canvas[r][col] = '│'

        if 0 <= row < height:
            if val >= 0:
                canvas[row][col] = '╮' if col > 0 and canvas[row][col-1] == '│' else '⌐'
            else:
                canvas[row][col] = '╯' if col > 0 and canvas[row][col-1] == '│' else '¬'

    # Add center line
    for col in range(len(points)):
        center_row = height // 2
        if canvas[center_row][col] == ' ':
            canvas[center_row][col] = '─'

    # Build frame
    top_line = '┌' + '─' * len(points) + '┐'
    bottom_line = '└' + '─' * len(points) + '┘'
    lines = [top_line]
    for row in canvas:
        lines.append('│' + ''.join(row) + '│')
    lines.append(bottom_line)

    # Add scale labels
    lines.insert(1, f'│ +1.0 {" " * (len(points) - 6)}│')
    lines.insert(height // 2 + 2, f'│  0.0 {" " * (len(points) - 6)}│')
    lines.insert(-1, f'│ -1.0 {" " * (len(points) - 6)}│')

    return '\n'.join(lines)


def visualize_spectrum_ascii(samples: List[float], width: int = TERMINAL_WIDTH,
                            height: int = 10) -> str:
    """Render a simple ASCII frequency spectrum approximation using zero-crossing analysis."""
    if len(samples) < 2:
        return "(not enough samples for spectrum)"

    # Simple DFT approximation for a few frequency bins
    n = len(samples)
    # Pick logarithmically spaced frequency bins
    bins = []
    min_freq = 20
    max_freq = SAMPLE_RATE / 2
    num_bins = width

    for i in range(num_bins):
        freq = min_freq * (max_freq / min_freq) ** (i / num_bins)
        bins.append(freq)

    # Compute magnitude for each bin
    magnitudes = []
    for freq in bins:
        real_part = 0.0
        imag_part = 0.0
        for j in range(n):
            angle = 2 * math.pi * freq * j / SAMPLE_RATE
            real_part += samples[j] * math.cos(angle)
            imag_part -= samples[j] * math.sin(angle)
        mag = math.sqrt(real_part ** 2 + imag_part ** 2) / n
        magnitudes.append(mag)

    # Normalize
    max_mag = max(magnitudes) if magnitudes else 1.0
    if max_mag == 0:
        max_mag = 1.0
    magnitudes = [m / max_mag for m in magnitudes]

    # Build bar chart
    lines = []
    lines.append(f'  {"─" * width}')
    for row in range(height, 0, -1):
        threshold = row / height
        bar_line = ''
        for m in magnitudes:
            if m >= threshold:
                bar_line += '█'
            elif m >= threshold - 0.15:
                bar_line += '▓'
            elif m >= threshold - 0.3:
                bar_line += '░'
            else:
                bar_line += ' '
        lines.append(f'  │{bar_line}│')
    lines.append(f'  {"─" * width}')
    lines.append(f'  20Hz{" " * (width - 14)}{int(max_freq/1000)}kHz')

    return '\n'.join(lines)


def print_waveform_info(samples: List[float], name: str = "Waveform",
                       sample_rate: int = SAMPLE_RATE) -> str:
    """Print summary info about a waveform."""
    if not samples:
        return f"{name}: (empty)"
    duration = len(samples) / sample_rate
    peak = max(abs(s) for s in samples)
    rms = math.sqrt(sum(s * s for s in samples) / len(samples))
    zero_crossings = sum(1 for i in range(1, len(samples)) if samples[i] * samples[i-1] < 0)
    est_freq = zero_crossings / (2 * duration) if duration > 0 else 0

    info = [
        f"  Name:       {name}",
        f"  Duration:   {duration:.3f}s",
        f"  Samples:   {len(samples)}",
        f"  Peak:       {peak:.4f}",
        f"  RMS:        {rms:.4f}",
        f"  Est. Freq:  {est_freq:.1f} Hz",
    ]
    return '\n'.join(info)


# ─── WAV Export ──────────────────────────────────────────────────────────────

def export_wav(samples: List[float], filename: str,
               sample_rate: int = SAMPLE_RATE) -> None:
    """Export samples as a 16-bit mono WAV file."""
    # Normalize to prevent clipping
    peak = max(abs(s) for s in samples) if samples else 0
    if peak > 1.0:
        samples = [s / peak for s in samples]

    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)

        data = b''
        for s in samples:
            val = int(s * MAX_AMPLITUDE)
            val = max(-MAX_AMPLITUDE, min(MAX_AMPLITUDE, val))
            data += struct.pack('<h', val)

        wf.writeframes(data)

    # Print file size
    import os
    size = os.path.getsize(filename)
    print(f"  Exported: {filename} ({size:,} bytes, {len(samples)/sample_rate:.2f}s)")


# ─── Chord / Arpeggio Generation ────────────────────────────────────────────

CHORD_INTERVALS = {
    'maj': [0, 4, 7],
    'min': [0, 3, 7],
    'dim': [0, 3, 6],
    'aug': [0, 4, 8],
    '7': [0, 4, 7, 10],
    'maj7': [0, 4, 7, 11],
    'min7': [0, 3, 7, 10],
    'sus2': [0, 2, 7],
    'sus4': [0, 5, 7],
    '5': [0, 7],
}

NOTE_ORDER = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def note_to_freq(note_name: str) -> float:
    """Convert a note name like 'C4' to frequency."""
    note = note_name.strip()
    # Parse note letter and octave
    if len(note) < 2:
        return float(note)
    
    letter = note[0].upper()
    accidental = ''
    octave_str = ''
    
    i = 1
    while i < len(note) and note[i] in '#b':
        accidental += note[i]
        i += 1
    octave_str = note[i:]
    
    if not octave_str:
        # Try as a frequency
        try:
            return float(note)
        except ValueError:
            octave_str = '4'
    
    # Build the note key
    key = letter + accidental + octave_str
    key_upper = key.upper().replace('B', 'b')
    
    if key_upper in NOTE_FREQS:
        return NOTE_FREQS[key_upper]
    
    # Manual calculation
    try:
        semitone = NOTE_ORDER.index(letter + accidental.replace('b', '').replace('#', '#') if accidental else '')
        octave = int(octave_str)
        midi = (octave + 1) * 12 + semitone
        return 440.0 * (2.0 ** ((midi - 69) / 12.0))
    except (ValueError, IndexError):
        return float(note)


def generate_chord(root_freq: float, chord_type: str, duration: float,
                   wave_type: str = 'sine', amplitude: float = 1.0,
                   sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a chord by mixing multiple notes."""
    intervals = CHORD_INTERVALS.get(chord_type, CHORD_INTERVALS['maj'])
    waves = []
    for interval in intervals:
        freq = root_freq * (2.0 ** (interval / 12.0))
        gen = WAVE_GENERATORS.get(wave_type, generate_sine)
        if wave_type == 'noise':
            w = generate_noise(duration, amplitude / len(intervals), sample_rate)
        else:
            w = gen(freq, duration, amplitude / len(intervals), sample_rate)
        waves.append(w)
    return mix_waves(waves)


def generate_arpeggio(root_freq: float, chord_type: str, duration: float,
                     wave_type: str = 'sine', amplitude: float = 1.0,
                     sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate an arpeggio — each note played sequentially."""
    intervals = CHORD_INTERVALS.get(chord_type, CHORD_INTERVALS['maj'])
    note_duration = duration / len(intervals)
    result = []
    for interval in intervals:
        freq = root_freq * (2.0 ** (interval / 12.0))
        gen = WAVE_GENERATORS.get(wave_type, generate_sine)
        if wave_type == 'noise':
            w = generate_noise(note_duration, amplitude, sample_rate)
        else:
            w = gen(freq, note_duration, amplitude, sample_rate)
        result.extend(w)
    return result


# ─── Melody from Notes ──────────────────────────────────────────────────────

def generate_melody(notes: List[Tuple[str, float]], wave_type: str = 'sine',
                    amplitude: float = 0.8, sample_rate: int = SAMPLE_RATE) -> List[float]:
    """Generate a melody from a list of (note, duration) tuples.
    Notes can be note names like 'C4', 'A#3', rests use 'R' or 'rest'.
    Duration is in seconds.
    """
    result = []
    gen = WAVE_GENERATORS.get(wave_type, generate_sine)
    for note, dur in notes:
        if note.upper() in ('R', 'REST', ''):
            result.extend([0.0] * int(dur * sample_rate))
        else:
            freq = resolve_freq(note)
            if wave_type == 'noise':
                w = generate_noise(dur, amplitude, sample_rate)
            else:
                w = gen(freq, dur, amplitude, sample_rate)
            result.extend(w)
    return result


# ─── Preset Melodies ────────────────────────────────────────────────────────

MELODY_PRESETS = {
    'scale': [('C4', 0.3), ('D4', 0.3), ('E4', 0.3), ('F4', 0.3),
              ('G4', 0.3), ('A4', 0.3), ('B4', 0.3), ('C5', 0.5)],
    'happy_birthday': [('C4', 0.25), ('C4', 0.25), ('D4', 0.5), ('C4', 0.5),
                       ('F4', 0.5), ('E4', 1.0), ('R', 0.25),
                       ('C4', 0.25), ('C4', 0.25), ('D4', 0.5), ('C4', 0.5),
                       ('G4', 0.5), ('F4', 1.0)],
    'ode_to_joy': [('E4', 0.4), ('E4', 0.4), ('F4', 0.4), ('G4', 0.4),
                   ('G4', 0.4), ('F4', 0.4), ('E4', 0.4), ('D4', 0.4),
                   ('C4', 0.4), ('C4', 0.4), ('D4', 0.4), ('E4', 0.4),
                   ('E4', 0.6), ('D4', 0.2), ('D4', 0.8)],
    'twinkle': [('C4', 0.4), ('C4', 0.4), ('G4', 0.4), ('G4', 0.4),
                ('A4', 0.4), ('A4', 0.4), ('G4', 0.8),
                ('F4', 0.4), ('F4', 0.4), ('E4', 0.4), ('E4', 0.4),
                ('D4', 0.4), ('D4', 0.4), ('C4', 0.8)],
    'pentatonic': [('C4', 0.25), ('D4', 0.25), ('E4', 0.25), ('G4', 0.25),
                   ('A4', 0.25), ('C5', 0.25), ('A4', 0.25), ('G4', 0.25),
                   ('E4', 0.25), ('D4', 0.25), ('C4', 0.5)],
}


# ─── Interactive Mode ────────────────────────────────────────────────────────

def interactive_mode():
    """Run an interactive wave synthesizer session."""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              🎵  WAVE SYNTH — Interactive Mode  🎵          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Commands:")
    print("  gen <wave> <freq/note> <duration>  — Generate waveform")
    print("  effect <name> [params]             — Apply effect to current wave")
    print("  adsr <a> <d> <s> <r>               — Apply ADSR envelope")
    print("  mix <idx1> <idx2> [w1] [w2]        — Mix two stored waves")
    print("  chord <root> <type> <duration>     — Generate chord")
    print("  arp <root> <type> <duration>        — Generate arpeggio")
    print("  melody <preset>                     — Generate preset melody")
    print("  viz                                 — Visualize current waveform")
    print("  spectrum                            — Show frequency spectrum")
    print("  info                                — Show waveform info")
    print("  export <filename>                  — Export as WAV")
    print("  play                                — Show current waveform")
    print("  list                                — List stored waveforms")
    print("  help                                 — Show this help")
    print("  quit                                 — Exit")
    print()
    print(f"  Wave types: sine, square, sawtooth, triangle, noise, harmonic")
    print(f"  Effects: tremolo, vibrato, lowpass, highpass, distortion, delay, fadein, fadeout, normalize, adsr")
    print(f"  Chord types: {', '.join(CHORD_INTERVALS.keys())}")
    print(f"  Melody presets: {', '.join(MELODY_PRESETS.keys())}")
    print()

    current = None
    waves = []  # List of (name, samples) tuples

    while True:
        try:
            cmd = input("wave> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not cmd:
            continue

        parts = cmd.split()
        action = parts[0].lower()

        try:
            if action == 'quit' or action == 'exit':
                print("Bye!")
                break

            elif action == 'help':
                print("See the command list above, or use 'gen sine A4 2' to get started!")

            elif action == 'gen':
                if len(parts) < 4:
                    print("Usage: gen <wave_type> <freq_or_note> <duration>")
                    continue
                wave_type = parts[1].lower()
                freq = resolve_freq(parts[2])
                duration = float(parts[3])
                if wave_type not in WAVE_GENERATORS:
                    print(f"Unknown wave type: {wave_type}. Available: {', '.join(WAVE_GENERATORS.keys())}")
                    continue
                gen = WAVE_GENERATORS[wave_type]
                if wave_type == 'noise':
                    samples = generate_noise(duration, 1.0, SAMPLE_RATE)
                else:
                    samples = gen(freq, duration, 1.0, SAMPLE_RATE)
                name = f"{wave_type}_{parts[2]}_{duration}s"
                current = samples
                waves.append((name, samples))
                print(f"  Generated {name} ({len(samples)} samples)")

            elif action == 'effect':
                if current is None:
                    print("No current waveform. Use 'gen' first.")
                    continue
                if len(parts) < 2:
                    print(f"Available effects: {', '.join(EFFECTS.keys())}")
                    continue
                effect_name = parts[1].lower()
                if effect_name not in EFFECTS and effect_name != 'adsr':
                    print(f"Unknown effect: {effect_name}")
                    continue

                if effect_name == 'tremolo':
                    rate = float(parts[2]) if len(parts) > 2 else 5.0
                    depth = float(parts[3]) if len(parts) > 3 else 0.5
                    current = apply_tremolo(current, rate, depth)
                    print(f"  Applied tremolo (rate={rate}, depth={depth})")
                elif effect_name == 'vibrato':
                    rate = float(parts[2]) if len(parts) > 2 else 5.0
                    depth = float(parts[3]) if len(parts) > 3 else 0.002
                    current = apply_vibrato(current, rate, depth)
                    print(f"  Applied vibrato (rate={rate}, depth={depth})")
                elif effect_name == 'lowpass':
                    cutoff = float(parts[2]) if len(parts) > 2 else 1000.0
                    current = apply_lowpass(current, cutoff)
                    print(f"  Applied lowpass (cutoff={cutoff}Hz)")
                elif effect_name == 'highpass':
                    cutoff = float(parts[2]) if len(parts) > 2 else 1000.0
                    current = apply_highpass(current, cutoff)
                    print(f"  Applied highpass (cutoff={cutoff}Hz)")
                elif effect_name == 'distortion':
                    drive = float(parts[2]) if len(parts) > 2 else 2.0
                    current = apply_distortion(current, drive)
                    print(f"  Applied distortion (drive={drive})")
                elif effect_name == 'delay':
                    delay_time = float(parts[2]) if len(parts) > 2 else 0.3
                    feedback = float(parts[3]) if len(parts) > 3 else 0.4
                    current = apply_delay(current, delay_time, feedback)
                    print(f"  Applied delay (time={delay_time}s, feedback={feedback})")
                elif effect_name == 'fadein':
                    dur = float(parts[2]) if len(parts) > 2 else 0.05
                    current = apply_fade_in(current, dur)
                    print(f"  Applied fade-in ({dur}s)")
                elif effect_name == 'fadeout':
                    dur = float(parts[2]) if len(parts) > 2 else 0.05
                    current = apply_fade_out(current, dur)
                    print(f"  Applied fade-out ({dur}s)")
                elif effect_name == 'normalize':
                    current = normalize(current)
                    print("  Normalized waveform")
                elif effect_name == 'adsr':
                    a = float(parts[2]) if len(parts) > 2 else 0.01
                    d = float(parts[3]) if len(parts) > 3 else 0.01
                    s = float(parts[4]) if len(parts) > 4 else 0.7
                    r = float(parts[5]) if len(parts) > 5 else 0.1
                    current = apply_adsr(current, a, d, s, r)
                    print(f"  Applied ADSR (A={a}, D={d}, S={s}, R={r})")

                waves.append((f"effect_{effect_name}", current))

            elif action == 'mix':
                if len(parts) < 3:
                    print("Usage: mix <idx1> <idx2> [weight1] [weight2]")
                    continue
                idx1 = int(parts[1])
                idx2 = int(parts[2])
                w1 = float(parts[3]) if len(parts) > 3 else 1.0
                w2 = float(parts[4]) if len(parts) > 4 else 1.0
                if idx1 >= len(waves) or idx2 >= len(waves):
                    print(f"Index out of range. Available: 0-{len(waves)-1}")
                    continue
                current = mix_waves([waves[idx1][1], waves[idx2][1]], [w1, w2])
                name = f"mix_{idx1}_{idx2}"
                waves.append((name, current))
                print(f"  Mixed waves {idx1} and {idx2} (weights: {w1}, {w2})")

            elif action == 'chord':
                if len(parts) < 4:
                    print("Usage: chord <root_note> <type> <duration> [wave]")
                    continue
                root = resolve_freq(parts[1])
                chord_type = parts[2].lower()
                duration = float(parts[3])
                wave_type = parts[4].lower() if len(parts) > 4 else 'sine'
                current = generate_chord(root, chord_type, duration, wave_type)
                name = f"chord_{parts[1]}_{chord_type}"
                waves.append((name, current))
                print(f"  Generated {name} ({len(current)} samples)")

            elif action == 'arp':
                if len(parts) < 4:
                    print("Usage: arp <root_note> <type> <duration> [wave]")
                    continue
                root = resolve_freq(parts[1])
                chord_type = parts[2].lower()
                duration = float(parts[3])
                wave_type = parts[4].lower() if len(parts) > 4 else 'sine'
                current = generate_arpeggio(root, chord_type, duration, wave_type)
                name = f"arp_{parts[1]}_{chord_type}"
                waves.append((name, current))
                print(f"  Generated {name} ({len(current)} samples)")

            elif action == 'melody':
                if len(parts) < 2:
                    print(f"Available presets: {', '.join(MELODY_PRESETS.keys())}")
                    continue
                preset = parts[1].lower()
                if preset not in MELODY_PRESETS:
                    print(f"Unknown preset: {preset}")
                    continue
                wave_type = parts[2].lower() if len(parts) > 2 else 'sine'
                notes = MELODY_PRESETS[preset]
                current = generate_melody(notes, wave_type)
                name = f"melody_{preset}"
                waves.append((name, current))
                print(f"  Generated {name} ({len(current)} samples)")

            elif action == 'viz' or action == 'visualize':
                if current is None:
                    print("No current waveform.")
                    continue
                print(visualize_ascii(current))

            elif action == 'spectrum':
                if current is None:
                    print("No current waveform.")
                    continue
                print(visualize_spectrum_ascii(current))

            elif action == 'info':
                if current is None:
                    print("No current waveform.")
                    continue
                name = waves[-1][0] if waves else "unknown"
                print(print_waveform_info(current, name))

            elif action == 'export':
                if current is None:
                    print("No current waveform to export.")
                    continue
                filename = parts[1] if len(parts) > 1 else "output.wav"
                if not filename.endswith('.wav'):
                    filename += '.wav'
                export_wav(current, filename)

            elif action == 'play':
                if current is None:
                    print("No current waveform.")
                    continue
                name = waves[-1][0] if waves else "unknown"
                print(f"Current: {name} ({len(current)} samples)")
                print(visualize_ascii(current))

            elif action == 'list':
                if not waves:
                    print("No waveforms stored yet.")
                    continue
                for i, (name, s) in enumerate(waves):
                    dur = len(s) / SAMPLE_RATE
                    marker = " ◀" if s is current else ""
                    print(f"  [{i}] {name} ({dur:.2f}s){marker}")

            else:
                print(f"Unknown command: {action}. Type 'help' for commands.")

        except Exception as e:
            print(f"Error: {e}")


# ─── CLI Mode ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Wave Synth — Terminal Audio Waveform Synthesizer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s sine A4 2                          Generate 2s sine at A4 (440Hz)
  %(prog)s square 220 1 --effect tremolo       Square wave with tremolo
  %(prog)s triangle C4 3 --export output.wav   Export triangle wave to WAV
  %(prog)s harmonic E4 2 --harmonics 1,1 2,0.5 3,0.25  Custom harmonics
  %(prog)s chord C4 maj 2 --wave sawtooth     C major chord (sawtooth)
  %(prog)s arp A3 min7 3                       A minor 7 arpeggio
  %(prog)s melody twinkle --wave triangle      Twinkle Twinkle melody
  %(prog)s --interactive                       Start interactive mode
  %(prog)s --spectrum sine A4 1               Show frequency spectrum
        """)

    parser.add_argument('wave_type', nargs='?', choices=list(WAVE_GENERATORS.keys()) + ['chord', 'arp', 'melody'],
                        help='Type of waveform to generate')
    parser.add_argument('remaining', nargs='*', help='Note, chord-type, and/or duration (varies by wave type)')

    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Start interactive mode')
    parser.add_argument('--wave', '-w', default='sine',
                        choices=list(WAVE_GENERATORS.keys()),
                        help='Wave type for chord/arp/melody (default: sine)')
    parser.add_argument('--amplitude', '-a', type=float, default=0.8,
                        help='Amplitude 0-1 (default: 0.8)')
    parser.add_argument('--export', '-e', metavar='FILE',
                        help='Export to WAV file')
    parser.add_argument('--effect', '-f', action='append',
                        help='Apply effect (e.g. tremolo, lowpass:1000, distortion:3)')
    parser.add_argument('--adsr', metavar='A,D,S,R',
                        help='Apply ADSR envelope (e.g. 0.01,0.1,0.7,0.2)')
    parser.add_argument('--chord-type', '-c', default='maj',
                        choices=list(CHORD_INTERVALS.keys()),
                        help='Chord type (for chord/arp commands)')
    parser.add_argument('--harmonics', metavar='N,A ...',
                        help='Custom harmonics for harmonic wave (e.g. "1,1 2,0.5 3,0.25")')
    parser.add_argument('--spectrum', '-s', action='store_true',
                        help='Show frequency spectrum instead of waveform')
    parser.add_argument('--info', action='store_true',
                        help='Show waveform info')
    parser.add_argument('--seed', type=int,
                        help='Random seed for noise generation')
    parser.add_argument('--width', type=int, default=TERMINAL_WIDTH,
                        help='Visualization width')
    parser.add_argument('--height', type=int, default=TERMINAL_HEIGHT,
                        help='Visualization height')

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
        return

    if not args.wave_type:
        parser.print_help()
        return

    # Parse positional args based on wave type
    remaining = args.remaining or []

    # Parse effect parameters
    effects_to_apply = []
    if args.effect:
        for eff_str in args.effect:
            parts = eff_str.split(':')
            name = parts[0].lower()
            params = [float(p) for p in parts[1:]] if len(parts) > 1 else []
            effects_to_apply.append((name, params))

    # Parse ADSR
    adsr_params = None
    if args.adsr:
        parts = args.adsr.split(',')
        if len(parts) == 4:
            adsr_params = tuple(float(p) for p in parts)
        else:
            print("ADSR format: A,D,S,R (e.g. 0.01,0.1,0.7,0.2)")
            return

    # Generate waveform
    samples = None

    if args.wave_type in ('chord', 'arp'):
        # chord C4 maj 2 | chord C4 2 (uses --chord-type)
        # arp A3 min7 3 | arp A3 3 (uses --chord-type)
        note = remaining[0] if len(remaining) >= 1 else None
        if not note:
            print(f"{args.wave_type} requires note and duration. Usage: {args.wave_type} <note> [chord_type] <duration>")
            return
        # Check if second arg is a chord type or duration
        if len(remaining) == 3:
            chord_type = remaining[1]
            duration = float(remaining[2])
        elif len(remaining) == 2:
            # Second arg could be chord_type or duration
            try:
                duration = float(remaining[1])
                chord_type = args.chord_type
            except ValueError:
                chord_type = remaining[1]
                print(f"{args.wave_type} requires a duration. Usage: {args.wave_type} <note> [chord_type] <duration>")
                return
        else:
            print(f"{args.wave_type} requires note and duration. Usage: {args.wave_type} <note> [chord_type] <duration>")
            return
        freq = resolve_freq(note)
        if args.wave_type == 'chord':
            samples = generate_chord(freq, chord_type, duration, args.wave, args.amplitude)
        else:
            samples = generate_arpeggio(freq, chord_type, duration, args.wave, args.amplitude)

    elif args.wave_type == 'melody':
        preset = remaining[0] if remaining else None
        if preset and preset.lower() in MELODY_PRESETS:
            samples = generate_melody(MELODY_PRESETS[preset.lower()], args.wave, args.amplitude)
        else:
            print(f"Melody presets: {', '.join(MELODY_PRESETS.keys())}")
            return

    else:
        # Standard wave: sine A4 2 | noise 1 | harmonic C4 2
        if len(remaining) < 1:
            print("Generation requires note/frequency. For noise, provide duration.")
            return
        note = remaining[0]
        if len(remaining) >= 2:
            duration = float(remaining[1])
        else:
            # For noise, first arg is duration
            if args.wave_type == 'noise':
                duration = float(note)
                note = None
            else:
                print("Generation requires note/frequency and duration")
                return

        if args.wave_type == 'noise':
            samples = generate_noise(duration, args.amplitude, SAMPLE_RATE, args.seed)
        else:
            freq = resolve_freq(note)
            gen = WAVE_GENERATORS[args.wave_type]
            if args.wave_type == 'harmonic':
                harmonics = None
                if args.harmonics:
                    harmonics = []
                    for h_str in args.harmonics.split():
                        n, a = h_str.split(',')
                        harmonics.append((int(n), float(a)))
                samples = generate_harmonic(freq, duration, args.amplitude, harmonics)
            else:
                samples = gen(freq, duration, args.amplitude)

    # Apply ADSR
    if adsr_params:
        samples = apply_adsr(samples, *adsr_params)

    # Apply effects
    for eff_name, params in effects_to_apply:
        if eff_name in EFFECTS:
            func = EFFECTS[eff_name]
            try:
                samples = func(samples, *params)
            except TypeError:
                samples = func(samples)
            print(f"  Applied: {eff_name}")
        else:
            print(f"  Unknown effect: {eff_name}")

    # Normalize before export
    if args.export:
        samples = normalize(samples, 0.95)

    # Output
    label = args.wave_type
    if remaining:
        label += '_' + '_'.join(str(r) for r in remaining)
    if args.info:
        print(print_waveform_info(samples, label))
        print()

    if args.spectrum:
        print(visualize_spectrum_ascii(samples, args.width, args.height))
    else:
        print(visualize_ascii(samples, args.width, args.height))

    if args.export:
        export_wav(samples, args.export)


if __name__ == '__main__':
    main()