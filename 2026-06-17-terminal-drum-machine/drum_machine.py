#!/usr/bin/env python3
"""
Terminal Drum Machine — A step-sequencer drum machine that runs in your terminal.
Synthesizes drum sounds from scratch using numpy, displays an animated sequencer
grid, and exports patterns as WAV or MIDI files. No external audio libraries needed!

Features:
  - 8 synthesized drum sounds (Kick, Snare, HH-Closed, HH-Open, Clap, Tom, Rim, Cowbell)
  - 16-step sequencer with configurable step count (8/16/32)
  - 6 built-in presets + random pattern generator
  - Shuffle/swing for groove feel
  - Humanize mode for organic timing/velocity variation
  - Per-drum volume control
  - Mute/solo per drum
  - Pattern save/load (JSON)
  - Pattern shift/rotate, invert, reverse
  - Copy drum patterns
  - Fill generator for last N steps
  - Undo support for pattern changes
  - WAV export at 44.1kHz 16-bit mono
  - MIDI export (basic, single-track)
  - Interactive REPL mode
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import struct
import sys
import wave
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np

__version__ = "1.3.0"

# ─── Constants ────────────────────────────────────────────────────────────────

SAMPLE_RATE = 44100
VALID_STEP_COUNTS = (8, 16, 32)

# Maximum number of undo states to keep in memory
MAX_UNDO_HISTORY = 50

# ─── Sound Synthesis ─────────────────────────────────────────────────────────


def synth_kick(duration: float = 0.4) -> np.ndarray:
    """Synthesize a kick drum — pitch-swept sine wave with fast decay.

    Uses an exponential frequency sweep from 150Hz down to 40Hz to create
    the characteristic thump, plus a short noise burst for attack transient.
    """
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0)
    t = np.linspace(0, duration, n, endpoint=False)

    # Pitch sweep from 150Hz down to 40Hz (exponential decay)
    freq = 150 * np.exp(-t * 12) + 40
    phase = np.cumsum(freq) / SAMPLE_RATE * 2 * np.pi
    signal = np.sin(phase) * 0.9

    # Add a tiny click at the start for attack transient
    click_len = int(0.005 * SAMPLE_RATE)
    if click_len > 0 and click_len < n:
        signal[:click_len] += np.random.randn(click_len) * 0.3

    # Envelope: fast exponential decay
    env = np.exp(-t * 8)
    signal *= env
    peak = np.max(np.abs(signal))
    return signal / (peak + 1e-10) * 0.95


def synth_snare(duration: float = 0.3) -> np.ndarray:
    """Synthesize a snare drum — tone + noise mixture with bandpass filtering.

    Layers sine tones at 200Hz and 350Hz with white noise, then applies
    a moving-average bandpass filter for a snappy, focused sound.
    """
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0)
    t = np.linspace(0, duration, n, endpoint=False)

    # Tone component: two harmonics
    tone = np.sin(2 * np.pi * 200 * t) + 0.5 * np.sin(2 * np.pi * 350 * t)

    # Noise component
    noise = np.random.randn(n)

    # Mix tone and noise
    signal = 0.4 * tone + 0.6 * noise

    # Envelope: fast exponential decay
    env = np.exp(-t * 15)
    signal *= env

    # Bandpass-ish filter using moving average
    kernel_size = 20
    kernel = np.ones(kernel_size) / kernel_size
    signal = np.convolve(signal, kernel, mode='same')

    peak = np.max(np.abs(signal))
    return signal / (peak + 1e-10) * 0.9


def synth_hihat_closed(duration: float = 0.08) -> np.ndarray:
    """Synthesize a closed hi-hat — high-pass filtered noise burst.

    Very fast decay (50/s) gives the tight, staccato character of a closed hat.
    """
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0)
    t = np.linspace(0, duration, n, endpoint=False)

    signal = np.random.randn(n)

    # High-pass by subtracting low frequencies
    low = np.convolve(signal, np.ones(30) / 30, mode='same')
    signal = signal - low * 0.8

    # Fast decay envelope
    env = np.exp(-t * 50)
    signal *= env

    peak = np.max(np.abs(signal))
    return signal / (peak + 1e-10) * 0.7


def synth_hihat_open(duration: float = 0.3) -> np.ndarray:
    """Synthesize an open hi-hat — longer noise burst with slower decay.

    Similar to closed hat but with much slower decay (12/s) for that
    sustained sizzle.
    """
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0)
    t = np.linspace(0, duration, n, endpoint=False)

    signal = np.random.randn(n)
    low = np.convolve(signal, np.ones(30) / 30, mode='same')
    signal = signal - low * 0.8

    env = np.exp(-t * 12)
    signal *= env

    peak = np.max(np.abs(signal))
    return signal / (peak + 1e-10) * 0.7


def synth_clap(duration: float = 0.15) -> np.ndarray:
    """Synthesize a clap — layered noise bursts for a multi-hand effect.

    Multiple short bursts at micro-offsets simulate the sound of several
    hands clapping in near-unison.
    """
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0)
    t = np.linspace(0, duration, n, endpoint=False)

    signal = np.random.randn(n)

    # Create multiple small bursts for layered-hand effect
    for offset in [0, 0.01, 0.02, 0.025]:
        idx = int(offset * SAMPLE_RATE)
        burst_len = int(0.005 * SAMPLE_RATE)
        if idx < n:
            end = min(idx + burst_len, n)
            signal[idx:end] *= 1.5

    env = np.exp(-t * 20)
    signal *= env

    peak = np.max(np.abs(signal))
    return signal / (peak + 1e-10) * 0.85


def synth_tom(duration: float = 0.25) -> np.ndarray:
    """Synthesize a tom — mid-frequency swept sine.

    Sweeps from 200Hz down to 100Hz with medium decay, producing a
    satisfying mid-pitched drum tone.
    """
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0)
    t = np.linspace(0, duration, n, endpoint=False)

    freq = 200 * np.exp(-t * 6) + 100
    phase = np.cumsum(freq) / SAMPLE_RATE * 2 * np.pi
    signal = np.sin(phase)

    env = np.exp(-t * 10)
    signal *= env

    peak = np.max(np.abs(signal))
    return signal / (peak + 1e-10) * 0.9


def synth_rim(duration: float = 0.05) -> np.ndarray:
    """Synthesize a rimshot — short click of tone + noise.

    Very fast decay (60/s) gives the sharp, clicky character of a rimshot.
    """
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0)
    t = np.linspace(0, duration, n, endpoint=False)

    signal = np.random.randn(n) * 0.5 + np.sin(2 * np.pi * 800 * t) * 0.5
    env = np.exp(-t * 60)
    signal *= env

    peak = np.max(np.abs(signal))
    return signal / (peak + 1e-10) * 0.7


def synth_cowbell(duration: float = 0.2) -> np.ndarray:
    """Synthesize a cowbell — two detuned square-ish waves.

    Sums two square waves at 560Hz and 845Hz for the classic metallic
    "more cowbell" timbre.
    """
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0)
    t = np.linspace(0, duration, n, endpoint=False)

    # Two detuned frequencies for metallic timbre
    sig1 = np.sign(np.sin(2 * np.pi * 560 * t))
    sig2 = np.sign(np.sin(2 * np.pi * 845 * t))
    signal = 0.5 * sig1 + 0.5 * sig2

    env = np.exp(-t * 8)
    signal *= env

    peak = np.max(np.abs(signal))
    return signal / (peak + 1e-10) * 0.65


def synth_metronome_click(duration: float = 0.05) -> np.ndarray:
    """Synthesize a metronome click — short high-pitched sine beep.

    Used as an optional click track to keep time during playback.
    """
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0)
    t = np.linspace(0, duration, n, endpoint=False)

    # High-pitched sine at 1000Hz with fast decay
    signal = np.sin(2 * np.pi * 1000 * t) * 0.6
    env = np.exp(-t * 80)
    signal *= env

    peak = np.max(np.abs(signal))
    if peak < 1e-10:
        return signal
    return signal / peak * 0.5


# ─── Drum Machine ─────────────────────────────────────────────────────────────


class DrumName(Enum):
    """Drum instrument names used in the sequencer."""
    KICK = "Kick"
    SNARE = "Snare"
    HH_CLOSED = "HH-C"
    HH_OPEN = "HH-O"
    CLAP = "Clap"
    TOM = "Tom"
    RIM = "Rim"
    COWBELL = "Cow"


DRUM_SYNTHS: Dict[DrumName, callable] = {
    DrumName.KICK: synth_kick,
    DrumName.SNARE: synth_snare,
    DrumName.HH_CLOSED: synth_hihat_closed,
    DrumName.HH_OPEN: synth_hihat_open,
    DrumName.CLAP: synth_clap,
    DrumName.TOM: synth_tom,
    DrumName.RIM: synth_rim,
    DrumName.COWBELL: synth_cowbell,
}

DRUM_ORDER: List[DrumName] = [
    DrumName.KICK,
    DrumName.SNARE,
    DrumName.HH_CLOSED,
    DrumName.HH_OPEN,
    DrumName.CLAP,
    DrumName.TOM,
    DrumName.RIM,
    DrumName.COWBELL,
]

# Shorthand aliases for interactive use
DRUM_ALIASES: Dict[str, DrumName] = {
    "kick": DrumName.KICK, "k": DrumName.KICK,
    "snare": DrumName.SNARE, "s": DrumName.SNARE,
    "hh-closed": DrumName.HH_CLOSED, "hhc": DrumName.HH_CLOSED,
    "hh-open": DrumName.HH_OPEN, "hho": DrumName.HH_OPEN,
    "clap": DrumName.CLAP, "c": DrumName.CLAP,
    "tom": DrumName.TOM, "t": DrumName.TOM,
    "rim": DrumName.RIM, "r": DrumName.RIM,
    "cowbell": DrumName.COWBELL, "cb": DrumName.COWBELL,
}


class DrumMachine:
    """Terminal-based step sequencer drum machine with sound synthesis.

    Supports pattern editing, presets, swing, humanize, undo, fill generation,
    WAV/MIDI export, and more.
    """

    def __init__(self, bpm: int = 120, steps: int = 16, swing: float = 0.0):
        if bpm < 30 or bpm > 300:
            raise ValueError(f"BPM must be between 30 and 300, got {bpm}")
        if steps not in VALID_STEP_COUNTS:
            raise ValueError(f"Steps must be one of {VALID_STEP_COUNTS}, got {steps}")
        if not 0.0 <= swing <= 0.75:
            raise ValueError(f"Swing must be between 0.0 and 0.75, got {swing}")

        self.bpm: int = bpm
        self.steps: int = steps
        self.swing: float = swing  # 0.0 = straight, 0.5 = medium swing, 0.75 = max
        self.drums: List[DrumName] = list(DRUM_ORDER)
        self.pattern: Dict[DrumName, List[bool]] = {
            drum: [False] * steps for drum in self.drums
        }
        self.volumes: Dict[DrumName, float] = {drum: 1.0 for drum in self.drums}
        self.muted: Dict[DrumName, bool] = {drum: False for drum in self.drums}
        self.synths: Dict[DrumName, callable] = dict(DRUM_SYNTHS)

        # Humanize settings: timing jitter in seconds, velocity variation as fraction
        self.humanize: bool = False
        self.humanize_timing: float = 0.008   # ±8ms jitter
        self.humanize_velocity: float = 0.12  # ±12% velocity variation

        # Metronome: click track on quarter-note steps
        self.metronome: bool = False

        # Undo history: stores snapshots of (pattern, volumes, muted, bpm, swing)
        self._undo_stack: List[tuple] = []

    # ─── Undo Support ────────────────────────────────────────────────────

    def _snapshot(self) -> tuple:
        """Capture current state for undo."""
        pattern_copy = {d: list(v) for d, v in self.pattern.items()}
        volumes_copy = dict(self.volumes)
        muted_copy = dict(self.muted)
        return (pattern_copy, volumes_copy, muted_copy, self.bpm, self.swing)

    def _push_undo(self) -> None:
        """Push current state onto the undo stack."""
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > MAX_UNDO_HISTORY:
            self._undo_stack.pop(0)

    def undo(self) -> bool:
        """Restore the most recent undo state. Returns True if undone."""
        if not self._undo_stack:
            return False
        pattern_copy, volumes_copy, muted_copy, bpm, swing = self._undo_stack.pop()
        self.pattern = pattern_copy
        self.volumes = volumes_copy
        self.muted = muted_copy
        self.bpm = bpm
        self.swing = swing
        return True

    # ─── Pattern Manipulation ─────────────────────────────────────────────

    def load_preset(self, name: str) -> bool:
        """Load a preset pattern by name. Returns True if found."""
        presets = self._get_presets()

        name_lower = name.lower().replace("-", "").replace(" ", "")
        for key, pattern in presets.items():
            if key.replace("-", "").replace(" ", "") == name_lower:
                self._push_undo()
                # Clear current pattern first
                for drum in self.drums:
                    self.pattern[drum] = [False] * self.steps
                # Load preset, adapting to current step count
                for drum, steps in pattern.items():
                    adapted = self._adapt_pattern(steps, self.steps)
                    self.pattern[drum] = adapted
                return True
        return False

    def _adapt_pattern(self, source: List[int], target_steps: int) -> List[bool]:
        """Adapt a pattern list to a different step count via tiling/truncation."""
        source_bools = [bool(s) for s in source]
        if len(source_bools) == target_steps:
            return source_bools
        # Tile or truncate
        result = []
        for i in range(target_steps):
            result.append(source_bools[i % len(source_bools)])
        return result

    def toggle(self, drum: DrumName, step: int) -> bool:
        """Toggle a step on/off. Returns new state."""
        if step < 0 or step >= self.steps:
            raise IndexError(f"Step must be 0-{self.steps - 1}, got {step}")
        self._push_undo()
        self.pattern[drum][step] = not self.pattern[drum][step]
        return self.pattern[drum][step]

    def set_volume(self, drum: DrumName, volume: float) -> None:
        """Set per-drum volume (0.0 to 2.0)."""
        self.volumes[drum] = max(0.0, min(2.0, volume))

    def toggle_mute(self, drum: DrumName) -> bool:
        """Toggle mute on/off for a drum. Returns new mute state."""
        self._push_undo()
        self.muted[drum] = not self.muted[drum]
        return self.muted[drum]

    def solo(self, drum: DrumName) -> None:
        """Solo a drum: mute all drums except the specified one."""
        self._push_undo()
        for d in self.drums:
            self.muted[d] = (d != drum)

    def unsolo_all(self) -> None:
        """Unmute all drums (clear any solo state)."""
        self._push_undo()
        for d in self.drums:
            self.muted[d] = False

    def shift_pattern(self, drum: DrumName, amount: int) -> None:
        """Rotate a drum's pattern left (negative) or right (positive)."""
        self._push_undo()
        p = self.pattern[drum]
        if amount == 0:
            return
        amount = amount % self.steps
        self.pattern[drum] = p[-amount:] + p[:-amount] if amount else p

    def invert_pattern(self, drum: DrumName) -> None:
        """Invert a drum's pattern: ON becomes OFF and vice versa."""
        self._push_undo()
        self.pattern[drum] = [not s for s in self.pattern[drum]]

    def reverse_pattern(self, drum: DrumName) -> None:
        """Reverse a drum's pattern: first step becomes last, etc."""
        self._push_undo()
        self.pattern[drum] = list(reversed(self.pattern[drum]))

    def copy_pattern(self, src: DrumName, dst: DrumName) -> None:
        """Copy one drum's pattern to another."""
        self._push_undo()
        self.pattern[dst] = list(self.pattern[src])

    def clear_pattern(self) -> None:
        """Clear all steps."""
        self._push_undo()
        for drum in self.drums:
            self.pattern[drum] = [False] * self.steps

    def random_pattern(self, density: float = 0.3) -> None:
        """Generate a random pattern with given overall density (0.0-1.0)."""
        self._push_undo()
        import random
        for drum in self.drums:
            if drum == DrumName.KICK:
                d = max(0.1, density - 0.1)
            elif drum in (DrumName.HH_CLOSED,):
                d = min(0.7, density + 0.15)
            elif drum in (DrumName.HH_OPEN, DrumName.CLAP, DrumName.COWBELL):
                d = max(0.05, density * 0.4)
            else:
                d = density
            self.pattern[drum] = [random.random() < d for _ in range(self.steps)]

    def generate_fill(self, start_step: int = 0, density: float = 0.7) -> None:
        """Generate a random fill starting from start_step to end of pattern.

        A fill adds hits on all drums in the specified range, creating a
        buildup or transition feel. Only affects steps from start_step onward.
        """
        import random
        if start_step < 0 or start_step >= self.steps:
            raise IndexError(f"start_step must be 0-{self.steps - 1}, got {start_step}")
        self._push_undo()
        for drum in self.drums:
            for i in range(start_step, self.steps):
                # Increase probability toward the end for a building feel
                progress = (i - start_step) / max(1, self.steps - 1 - start_step)
                prob = density * (0.5 + 0.5 * progress)
                if random.random() < prob:
                    self.pattern[drum][i] = True

    # ─── Timing ────────────────────────────────────────────────────────────

    def step_duration(self, step: int = 0) -> float:
        """Duration of one step in seconds, accounting for swing.

        Swing redistributes timing within each pair of steps:
        even-indexed steps (0, 2, 4...) get longer, odd-indexed steps
        (1, 3, 5...) get shorter. Total loop duration is preserved.
        A swing of 0.0 is straight timing, 0.67 is a classic swing feel.
        """
        base = 60.0 / self.bpm / 4
        if self.swing > 0:
            if step % 2 == 0:
                # Even-indexed steps (0, 2, 4...) get longer
                return base * (1.0 + self.swing)
            else:
                # Odd-indexed steps (1, 3, 5...) get shorter
                return base * (1.0 - self.swing)
        return base

    def total_loop_duration(self) -> float:
        """Total duration of one full loop in seconds."""
        if self.swing == 0.0:
            return self.steps * 60.0 / self.bpm / 4
        return sum(self.step_duration(s) for s in range(self.steps))

    # ─── Audio Rendering ───────────────────────────────────────────────────

    def mix_step(self, step: int) -> np.ndarray:
        """Mix all active (un-muted) sounds for a given step.

        Applies humanize timing jitter and velocity variation if enabled.
        Optionally includes a metronome click on quarter-note steps.
        """
        duration = self.step_duration(step)
        n = int(SAMPLE_RATE * duration)
        if n <= 0:
            n = 1
        mixed = np.zeros(n)

        for drum in self.drums:
            if self.pattern[drum][step] and not self.muted[drum]:
                sound = self.synths[drum](duration=min(duration, 0.5))
                # Apply per-drum volume
                vol = self.volumes[drum]

                # Apply humanize velocity variation if enabled
                if self.humanize:
                    import random
                    vel_factor = 1.0 + random.uniform(-self.humanize_velocity,
                                                       self.humanize_velocity)
                    vel_factor = max(0.2, min(1.5, vel_factor))
                    vol *= vel_factor

                sound = sound * vol
                # Trim or pad to match step length
                if len(sound) > n:
                    sound = sound[:n]
                elif len(sound) < n:
                    sound = np.pad(sound, (0, n - len(sound)))
                mixed += sound

        # Metronome click on quarter-note steps (every 4th step in 16-step mode)
        if self.metronome:
            # Quarter notes: steps 0, 4, 8, 12 for 16-step; 0, 2, 4, 6 for 8-step
            quarter_interval = self.steps // 4
            if quarter_interval > 0 and step % quarter_interval == 0:
                click = synth_metronome_click(duration=min(duration, 0.05))
                if len(click) > n:
                    click = click[:n]
                elif len(click) < n:
                    click = np.pad(click, (0, n - len(click)))
                mixed += click

        # Normalize if clipping
        peak = np.max(np.abs(mixed))
        if peak > 0.95:
            mixed = mixed / peak * 0.95
        return mixed

    def render_full_loop(self) -> np.ndarray:
        """Render the full pattern as a numpy array."""
        return np.concatenate([self.mix_step(s) for s in range(self.steps)])

    def render_to_wav(self, filename: str, loops: int = 2) -> str:
        """Render pattern to a WAV file. Returns the filename.

        Args:
            filename: Output WAV file path.
            loops: Number of times to loop the pattern (must be >= 1).

        Raises:
            ValueError: If loops < 1 or the pattern renders empty audio.
        """
        if loops < 1:
            raise ValueError(f"Loops must be at least 1, got {loops}")

        loop = self.render_full_loop()
        if len(loop) == 0:
            raise ValueError("Cannot render empty loop — pattern may be empty")

        full = np.tile(loop, loops)

        # Add a tiny fade-out at the very end to prevent clicks
        fade_len = min(int(0.01 * SAMPLE_RATE), len(full))
        if fade_len > 0:
            full[-fade_len:] *= np.linspace(1, 0, fade_len)

        # Convert to 16-bit PCM
        full = np.clip(full, -1.0, 1.0)
        pcm = (full * 32767).astype(np.int16)

        # Ensure parent directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with wave.open(filename, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm.tobytes())

        return filename

    def render_to_midi(self, filename: str) -> str:
        """Export the pattern as a basic single-track MIDI file (format 0).

        Each drum is mapped to a GM percussion note number (channel 10).
        Velocity is derived from per-drum volume (0-200% maps to 0-127).

        Args:
            filename: Output .mid file path.

        Returns:
            The filename written.
        """
        # General MIDI percussion note mappings (channel 10 = 0x09)
        DRUM_MIDI_NOTE = {
            DrumName.KICK: 36,       # Bass Drum 1
            DrumName.SNARE: 38,      # Acoustic Snare
            DrumName.HH_CLOSED: 42,  # Closed Hi-Hat
            DrumName.HH_OPEN: 46,    # Open Hi-Hat
            DrumName.CLAP: 39,       # Hand Clap
            DrumName.TOM: 47,        # Low-Mid Tom
            DrumName.RIM: 37,        # Side Stick
            DrumName.COWBELL: 56,    # Cowbell
        }

        ticks_per_quarter = 480
        step_ticks = ticks_per_quarter // 4  # 16th note resolution

        events: List[tuple] = []  # (absolute_tick, note, velocity)

        for step_idx in range(self.steps):
            tick = step_idx * step_ticks
            for drum in self.drums:
                if self.pattern[drum][step_idx] and not self.muted[drum]:
                    vel = int(min(1.0, self.volumes[drum]) * 127)
                    vel = max(1, min(127, vel))
                    events.append((tick, DRUM_MIDI_NOTE[drum], vel))

        # Sort events by tick
        events.sort(key=lambda e: e[0])

        # Build MIDI file bytes
        def varlen(value: int) -> bytes:
            """Encode a value as a MIDI variable-length quantity."""
            result = []
            result.append(value & 0x7F)
            value >>= 7
            while value > 0:
                result.append((value & 0x7F) | 0x80)
                value >>= 7
            result.reverse()
            return bytes(result)

        # Build the track data
        track_data = bytearray()

        # Tempo meta event: microseconds per quarter note
        tempo = int(60_000_000 / self.bpm)
        track_data += b'\x00'  # delta time = 0
        track_data += b'\xFF\x51\x03'  # tempo meta event
        track_data += tempo.to_bytes(3, 'big')

        prev_tick = 0
        for tick, note, vel in events:
            delta = tick - prev_tick
            prev_tick = tick
            track_data += varlen(delta)
            # Note On on channel 10 (0x9F = note on, channel 10 = 0x09)
            track_data += bytes([0x99, note & 0x7F, vel])
            # Note Off after a short duration (1/32nd note)
            track_data += varlen(step_ticks // 2)
            track_data += bytes([0x89, note & 0x7F, 0])

        # End of track meta event
        track_data += b'\x00\xFF\x2F\x00'

        # MIDI file header (format 0, 1 track)
        header = b'MThd'
        header += (6).to_bytes(4, 'big')     # header length
        header += (0).to_bytes(2, 'big')      # format 0
        header += (1).to_bytes(2, 'big')      # 1 track
        header += ticks_per_quarter.to_bytes(2, 'big')

        # Track chunk
        track_chunk = b'MTrk'
        track_chunk += len(track_data).to_bytes(4, 'big')
        track_chunk += bytes(track_data)

        midi_bytes = header + track_chunk

        # Ensure parent directory exists
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(filename, 'wb') as f:
            f.write(midi_bytes)

        return filename

    # ─── Save / Load ───────────────────────────────────────────────────────

    def save_pattern_json(self, filename: str) -> None:
        """Save the current pattern, volumes, BPM, swing, and humanize state to JSON."""
        data = {
            "version": __version__,
            "bpm": self.bpm,
            "steps": self.steps,
            "swing": self.swing,
            "humanize": self.humanize,
            "humanize_timing": self.humanize_timing,
            "humanize_velocity": self.humanize_velocity,
            "pattern": {
                drum.value: [int(s) for s in self.pattern[drum]]
                for drum in self.drums
            },
            "volumes": {
                drum.value: self.volumes[drum]
                for drum in self.drums
            },
            "muted": {
                drum.value: self.muted[drum]
                for drum in self.drums
            },
        }
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    def load_pattern_json(self, filename: str) -> bool:
        """Load a pattern from a JSON file. Returns True on success.

        Validates types for all loaded values to prevent crashes from
        malformed JSON data.
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
            print(f"Error loading pattern: {e}")
            return False

        self._push_undo()

        # Validate and coerce types
        bpm_val = data.get("bpm", self.bpm)
        if isinstance(bpm_val, (int, float)):
            self.bpm = int(bpm_val)

        swing_val = data.get("swing", 0.0)
        if isinstance(swing_val, (int, float)):
            self.swing = float(swing_val)

        loaded_steps = data.get("steps", self.steps)
        if isinstance(loaded_steps, int) and loaded_steps in VALID_STEP_COUNTS:
            self.steps = loaded_steps

        # Load humanize settings if present
        humanize_val = data.get("humanize", False)
        if isinstance(humanize_val, bool):
            self.humanize = humanize_val
        timing_val = data.get("humanize_timing", 0.008)
        if isinstance(timing_val, (int, float)):
            self.humanize_timing = float(timing_val)
        velocity_val = data.get("humanize_velocity", 0.12)
        if isinstance(velocity_val, (int, float)):
            self.humanize_velocity = float(velocity_val)

        for drum in self.drums:
            if drum.value in data.get("pattern", {}):
                src = data["pattern"][drum.value]
                if isinstance(src, list):
                    self.pattern[drum] = self._adapt_pattern(src, self.steps)
                else:
                    self.pattern[drum] = [False] * self.steps
            else:
                self.pattern[drum] = [False] * self.steps

        for drum in self.drums:
            if drum.value in data.get("volumes", {}):
                vol = data["volumes"][drum.value]
                if isinstance(vol, (int, float)):
                    self.volumes[drum] = float(vol)

        for drum in self.drums:
            if drum.value in data.get("muted", {}):
                m = data["muted"][drum.value]
                if isinstance(m, (bool, int)):
                    self.muted[drum] = bool(m)

        return True

    # ─── Display ───────────────────────────────────────────────────────────

    def display_grid(self, highlight_step: Optional[int] = None) -> str:
        """Return a string representation of the sequencer grid."""
        lines: List[str] = []

        # Build header with step numbers
        header = "Drum Machine  │ "
        header += "┼".join(f"{i + 1:2}" for i in range(self.steps))
        header += " │"

        # Separator line
        inner_width = self.steps * 3 - 1
        sep = "─" * 14 + "┼" + "─" * inner_width + "┼─"
        lines.append(sep)
        lines.append(header)
        lines.append(sep)

        # Drum rows
        for drum in self.drums:
            mute_marker = "🔇" if self.muted[drum] else "  "
            row = f"{drum.value:>13}{mute_marker}│ "
            for i in range(self.steps):
                if self.pattern[drum][i]:
                    if highlight_step is not None and i == highlight_step:
                        marker = "◉ "
                    else:
                        marker = "● "
                else:
                    if highlight_step is not None and i == highlight_step:
                        marker = "◦ "
                    else:
                        marker = "· "
                row += marker
            row += "│"
            lines.append(row)

        lines.append(sep)

        # Status line
        status_parts = [f"BPM: {self.bpm}", f"Steps: {self.steps}"]
        if self.swing > 0:
            status_parts.append(f"Swing: {self.swing:.0%}")
        if self.humanize:
            status_parts.append("Humanize: ON")
        if self.metronome:
            status_parts.append("Metro: ON")
        if highlight_step is not None:
            status_parts.append(f"Step: {highlight_step + 1}")
        lines.append("  " + "  ".join(status_parts))

        return "\n".join(lines)

    def display_presets(self) -> str:
        """Show available presets as a formatted string."""
        presets = [
            ("four-on-floor", "Classic 4/4 dance beat — kick on every quarter note"),
            ("hiphop", "Boom-bap hip-hop groove with syncopated kick"),
            ("breakbeat", "Amen-inspired breakbeat pattern"),
            ("reggaeton", "Dembow rhythm with rimshot accent"),
            ("bossa-nova", "Brazilian bossa nova feel with cowbell"),
            ("dnb", "Fast drum and bass with open hi-hat tail"),
        ]
        lines = ["Available Presets:", ""]
        for name, desc in presets:
            lines.append(f"  {name:<20} — {desc}")
        return "\n".join(lines)

    def pattern_density(self) -> Dict[str, float]:
        """Return fill density per drum (fraction of steps that are ON)."""
        result = {}
        for drum in self.drums:
            on = sum(1 for s in self.pattern[drum] if s)
            result[drum.value] = on / self.steps if self.steps > 0 else 0.0
        return result

    @staticmethod
    def _get_presets() -> dict:
        """Return the preset dictionary."""
        return {
            "four-on-floor": {
                DrumName.KICK:     [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
                DrumName.SNARE:    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                DrumName.HH_CLOSED:[1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
            },
            "hiphop": {
                DrumName.KICK:     [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                DrumName.SNARE:   [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1],
                DrumName.HH_CLOSED:[1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 0, 1, 0],
            },
            "breakbeat": {
                DrumName.KICK:     [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                DrumName.SNARE:   [0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0],
                DrumName.HH_CLOSED:[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                DrumName.HH_OPEN: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
            },
            "reggaeton": {
                DrumName.KICK:     [1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0],
                DrumName.SNARE:   [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                DrumName.HH_CLOSED:[1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                DrumName.RIM:     [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
            },
            "bossa-nova": {
                DrumName.KICK:     [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                DrumName.RIM:     [0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 1],
                DrumName.HH_CLOSED:[1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                DrumName.COWBELL: [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0],
            },
            "dnb": {
                DrumName.KICK:     [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
                DrumName.SNARE:   [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0],
                DrumName.HH_CLOSED:[1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                DrumName.HH_OPEN: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            },
        }


def try_play_audio(audio_data: np.ndarray) -> bool:
    """Try to play audio using available system tools. Returns True if played."""
    import subprocess
    import tempfile

    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp_name = tmp.name
    tmp.close()

    try:
        samples = np.clip(audio_data, -1.0, 1.0)
        pcm = (samples * 32767).astype(np.int16)
        with wave.open(tmp_name, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm.tobytes())

        for player in ['aplay', 'paplay', 'play', 'afplay']:
            for search_path in ['/usr/bin', '/usr/local/bin', '/bin']:
                candidate = os.path.join(search_path, player)
                if os.path.isfile(candidate):
                    try:
                        subprocess.run(
                            [candidate, tmp_name],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=30,
                        )
                        return True
                    except (subprocess.TimeoutExpired, OSError):
                        continue
        return False
    finally:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass


def interactive_mode(machine: DrumMachine) -> None:
    """Run the drum machine in interactive REPL mode."""
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║            🥁  TERMINAL DRUM MACHINE  🥁                  ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print("║  <drum> <step>       — Toggle a step  (e.g. kick 1)      ║")
    print("║  preset <name>       — Load a preset                      ║")
    print("║  presets             — List presets                        ║")
    print("║  bpm <n>             — Set BPM (30-300)                   ║")
    print("║  swing <0-75>        — Set swing %  (0=straight)         ║")
    print("║  volume <drum> <0-200> — Set drum volume %              ║")
    print("║  mute <drum>         — Toggle mute on a drum            ║")
    print("║  solo <drum>         — Solo a drum (mute all others)     ║")
    print("║  unsolo              — Unmute all drums                   ║")
    print("║  shift <drum> <n>    — Rotate pattern by n steps         ║")
    print("║  invert <drum>       — Invert pattern (on↔off)          ║")
    print("║  reverse <drum>       — Reverse pattern order             ║")
    print("║  copy <src> <dst>    — Copy pattern between drums        ║")
    print("║  fill [start_step]   — Generate fill from step onward     ║")
    print("║  humanize [on|off]   — Toggle humanize (timing/velocity)  ║")
    print("║  metronome           — Toggle click track on quarter notes║")
    print("║  clear               — Clear pattern                      ║")
    print("║  random [density]    — Random pattern (0.0-1.0)           ║")
    print("║  density             — Show pattern density per drum       ║")
    print("║  undo                — Undo last change                  ║")
    print("║  save <file>         — Save pattern to JSON               ║")
    print("║  load <file>         — Load pattern from JSON              ║")
    print("║  play                — Play pattern (audio)               ║")
    print("║  export <file>       — Export to WAV                      ║")
    print("║  exportmidi <file>   — Export to MIDI                     ║")
    print("║  grid                — Redraw the grid                    ║")
    print("║  quit                — Exit                               ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    print(machine.display_grid())
    print()

    while True:
        try:
            cmd = input("🥁 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not cmd:
            continue

        parts = cmd.lower().split()

        if parts[0] in ("quit", "exit", "q"):
            print("Bye!")
            break

        elif parts[0] == "grid":
            print(machine.display_grid())
            print()

        elif parts[0] == "presets":
            print(machine.display_presets())
            print()

        elif parts[0] == "preset":
            if len(parts) < 2:
                print("Usage: preset <name>")
                continue
            name = parts[1]
            if machine.load_preset(name):
                print(f"Loaded preset: {name}")
                print(machine.display_grid())
            else:
                print(f"Unknown preset: {name}. Type 'presets' to see available presets.")
            print()

        elif parts[0] == "bpm":
            if len(parts) < 2:
                print(f"Current BPM: {machine.bpm}")
                continue
            try:
                new_bpm = int(parts[1])
                if new_bpm < 30 or new_bpm > 300:
                    print("BPM must be between 30 and 300")
                    continue
                machine._push_undo()
                machine.bpm = new_bpm
                print(f"BPM set to {machine.bpm}")
            except ValueError:
                print("Invalid BPM value")
            print()

        elif parts[0] == "swing":
            if len(parts) < 2:
                print(f"Current swing: {machine.swing:.0%}")
                continue
            try:
                swing_pct = float(parts[1])
                machine._push_undo()
                machine.swing = max(0.0, min(0.75, swing_pct / 100.0))
                print(f"Swing set to {machine.swing:.0%}")
            except (ValueError, IndexError):
                print("Usage: swing <0-75>  (percentage)")
            print()

        elif parts[0] == "volume":
            if len(parts) < 3:
                print("Usage: volume <drum> <0-200>  (percentage, 100=normal)")
                continue
            drum_name = parts[1]
            if drum_name not in DRUM_ALIASES:
                drum_names = sorted(set(d.value for d in DRUM_ALIASES.values()))
                print(f"Unknown drum: {drum_name}. Use one of: {', '.join(drum_names)}")
                continue
            try:
                vol_pct = float(parts[2])
                drum = DRUM_ALIASES[drum_name]
                machine.set_volume(drum, vol_pct / 100.0)
                print(f"{drum.value} volume set to {vol_pct:.0f}%")
            except (ValueError, IndexError):
                print("Volume must be a number (0-200)")
            print()

        elif parts[0] == "mute":
            if len(parts) < 2:
                print("Usage: mute <drum>")
                continue
            drum_name = parts[1]
            if drum_name not in DRUM_ALIASES:
                print(f"Unknown drum: {drum_name}")
                continue
            drum = DRUM_ALIASES[drum_name]
            new_mute = machine.toggle_mute(drum)
            state = "MUTED 🔇" if new_mute else "UNMUTED"
            print(f"{drum.value} is now {state}")
            print(machine.display_grid())
            print()

        elif parts[0] == "solo":
            if len(parts) < 2:
                print("Usage: solo <drum>")
                continue
            drum_name = parts[1]
            if drum_name not in DRUM_ALIASES:
                print(f"Unknown drum: {drum_name}")
                continue
            drum = DRUM_ALIASES[drum_name]
            machine.solo(drum)
            print(f"Solo: {drum.value} — all other drums muted")
            print(machine.display_grid())
            print()

        elif parts[0] == "unsolo":
            machine.unsolo_all()
            print("All drums unmuted")
            print(machine.display_grid())
            print()

        elif parts[0] == "shift":
            if len(parts) < 3:
                print("Usage: shift <drum> <amount>  (positive=right, negative=left)")
                continue
            drum_name = parts[1]
            if drum_name not in DRUM_ALIASES:
                print(f"Unknown drum: {drum_name}")
                continue
            try:
                amount = int(parts[2])
                drum = DRUM_ALIASES[drum_name]
                machine.shift_pattern(drum, amount)
                direction = "right" if amount > 0 else "left"
                print(f"Shifted {drum.value} {direction} by {abs(amount)} step(s)")
                print(machine.display_grid())
            except ValueError:
                print("Amount must be an integer")
            print()

        elif parts[0] == "invert":
            if len(parts) < 2:
                print("Usage: invert <drum>")
                continue
            drum_name = parts[1]
            if drum_name not in DRUM_ALIASES:
                print(f"Unknown drum: {drum_name}")
                continue
            drum = DRUM_ALIASES[drum_name]
            machine.invert_pattern(drum)
            print(f"Inverted {drum.value} pattern")
            print(machine.display_grid())
            print()

        elif parts[0] == "reverse":
            if len(parts) < 2:
                print("Usage: reverse <drum>")
                continue
            drum_name = parts[1]
            if drum_name not in DRUM_ALIASES:
                print(f"Unknown drum: {drum_name}")
                continue
            drum = DRUM_ALIASES[drum_name]
            machine.reverse_pattern(drum)
            print(f"Reversed {drum.value} pattern")
            print(machine.display_grid())
            print()

        elif parts[0] == "copy":
            if len(parts) < 3:
                print("Usage: copy <source_drum> <dest_drum>")
                continue
            src_name, dst_name = parts[1], parts[2]
            if src_name not in DRUM_ALIASES or dst_name not in DRUM_ALIASES:
                print(f"Unknown drum name. Use aliases: k, s, hhc, hho, c, t, r, cb")
                continue
            src = DRUM_ALIASES[src_name]
            dst = DRUM_ALIASES[dst_name]
            machine.copy_pattern(src, dst)
            print(f"Copied {src.value} → {dst.value}")
            print(machine.display_grid())
            print()

        elif parts[0] == "fill":
            start_step = max(0, machine.steps - 4)  # default: last 4 steps
            density = 0.7
            if len(parts) > 1:
                try:
                    # User specifies 1-indexed step number
                    start_step = int(parts[1]) - 1
                    if start_step < 0 or start_step >= machine.steps:
                        print(f"Step must be between 1 and {machine.steps}")
                        continue
                except ValueError:
                    print("Fill start step must be a number")
                    continue
            if len(parts) > 2:
                try:
                    density = float(parts[2])
                    density = max(0.1, min(1.0, density))
                except ValueError:
                    print("Density must be a number")
            try:
                machine.generate_fill(start_step=start_step, density=density)
                print(f"Fill generated from step {start_step + 1} (density ~{density:.0%})")
                print(machine.display_grid())
            except IndexError as e:
                print(f"Error: {e}")
            print()

        elif parts[0] == "humanize":
            if len(parts) > 1:
                if parts[1] in ("on", "yes", "true", "1"):
                    machine.humanize = True
                elif parts[1] in ("off", "no", "false", "0"):
                    machine.humanize = False
                else:
                    print("Usage: humanize [on|off]")
                    continue
            else:
                machine.humanize = not machine.humanize
            state = "ON 🎭" if machine.humanize else "OFF"
            print(f"Humanize: {state}")
            if machine.humanize:
                print(f"  Timing jitter: ±{machine.humanize_timing*1000:.1f}ms")
                print(f"  Velocity variation: ±{machine.humanize_velocity:.0%}")
            print()

        elif parts[0] == "metronome":
            machine.metronome = not machine.metronome
            state = "ON 🔔" if machine.metronome else "OFF"
            print(f"Metronome: {state}")
            print()

        elif parts[0] == "clear":
            machine.clear_pattern()
            print("Pattern cleared.")
            print(machine.display_grid())
            print()

        elif parts[0] == "random":
            density = 0.3
            if len(parts) > 1:
                try:
                    density = float(parts[1])
                    density = max(0.05, min(0.95, density))
                except ValueError:
                    print("Density must be a number between 0.05 and 0.95")
                    continue
            machine.random_pattern(density=density)
            print(f"Random pattern generated (density ~{density:.0%})!")
            print(machine.display_grid())
            print()

        elif parts[0] == "density":
            densities = machine.pattern_density()
            print("Pattern density per drum:")
            for drum in machine.drums:
                d = densities[drum.value]
                bar = "█" * int(d * 20) + "░" * (20 - int(d * 20))
                mute_str = " (muted)" if machine.muted[drum] else ""
                vol_str = f" vol:{machine.volumes[drum]:.0%}" if machine.volumes[drum] != 1.0 else ""
                print(f"  {drum.value:>8} {bar} {d:5.1%}{mute_str}{vol_str}")
            print()

        elif parts[0] == "undo":
            if machine.undo():
                print("↩ Undo successful")
                print(machine.display_grid())
            else:
                print("Nothing to undo")
            print()

        elif parts[0] == "save":
            if len(parts) < 2:
                print("Usage: save <file.json>")
                continue
            filename = parts[1]
            if not filename.endswith('.json'):
                filename += '.json'
            try:
                machine.save_pattern_json(filename)
                print(f"Pattern saved to {filename}")
            except OSError as e:
                print(f"Error saving: {e}")
            print()

        elif parts[0] == "load":
            if len(parts) < 2:
                print("Usage: load <file.json>")
                continue
            filename = parts[1]
            if not os.path.exists(filename):
                print(f"File not found: {filename}")
                continue
            if machine.load_pattern_json(filename):
                print(f"Pattern loaded from {filename}")
                print(machine.display_grid())
            print()

        elif parts[0] == "play":
            print("Playing pattern...")
            loop = machine.render_full_loop()
            played = try_play_audio(loop)
            if not played:
                outfile = "/tmp/drum_machine_output.wav"
                machine.render_to_wav(outfile)
                print(f"Audio playback not available. Saved to {outfile}")
            print()

        elif parts[0] == "export":
            if len(parts) < 2:
                print("Usage: export <filename.wav>")
                continue
            filename = parts[1]
            if not filename.endswith('.wav'):
                filename += '.wav'
            try:
                machine.render_to_wav(filename)
                print(f"Exported to {filename}")
            except (OSError, ValueError) as e:
                print(f"Error exporting: {e}")
            print()

        elif parts[0] == "exportmidi":
            if len(parts) < 2:
                print("Usage: exportmidi <filename.mid>")
                continue
            filename = parts[1]
            if not filename.endswith('.mid'):
                filename += '.mid'
            try:
                machine.render_to_midi(filename)
                print(f"Exported MIDI to {filename}")
            except (OSError, ValueError) as e:
                print(f"Error exporting MIDI: {e}")
            print()

        elif parts[0] in DRUM_ALIASES:
            drum = DRUM_ALIASES[parts[0]]
            if len(parts) < 2:
                print(f"Usage: {parts[0]} <step_number> (1-{machine.steps})")
                continue
            try:
                step = int(parts[1]) - 1
                if step < 0 or step >= machine.steps:
                    print(f"Step must be between 1 and {machine.steps}")
                    continue
                new_state = machine.toggle(drum, step)
                state = "ON" if new_state else "OFF"
                print(f"{drum.value} step {step + 1}: {state}")
                print(machine.display_grid(highlight_step=step))
            except ValueError:
                print("Invalid step number")
            print()

        else:
            print(f"Unknown command: {parts[0]}")
            print("Type 'quit' to exit.")


def main() -> None:
    """Entry point for the drum machine CLI."""
    parser = argparse.ArgumentParser(
        description="Terminal Drum Machine — Step sequencer that synthesizes drum sounds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 drum_machine.py                          # Interactive mode
  python3 drum_machine.py --preset hiphop           # Load preset and show grid
  python3 drum_machine.py --export beat.wav         # Export to WAV
  python3 drum_machine.py --bpm 140 --preset dnb --export dnb.wav
  python3 drum_machine.py --random --export rand.wav
  python3 drum_machine.py --random --density 0.4   # Random with specific density
  python3 drum_machine.py --swing 30               # 30% swing feel
  python3 drum_machine.py --steps 32               # 32-step sequencer
  python3 drum_machine.py --humanize               # Add human feel
  python3 drum_machine.py --preset breakbeat --humanize --export live.wav
  python3 drum_machine.py --export-midi beat.mid   # Export as MIDI
        """
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--bpm", type=int, default=120, help="Beats per minute (default: 120)")
    parser.add_argument("--steps", type=int, default=16, choices=VALID_STEP_COUNTS,
                        help="Number of steps (default: 16)")
    parser.add_argument("--preset", type=str, help="Load a preset pattern")
    parser.add_argument("--export", type=str, metavar="FILE.wav", help="Export to WAV file")
    parser.add_argument("--export-midi", type=str, metavar="FILE.mid",
                        help="Export as MIDI file")
    parser.add_argument("--loops", type=int, default=2, help="Number of loops for WAV export (default: 2)")
    parser.add_argument("--random", action="store_true", help="Generate random pattern")
    parser.add_argument("--density", type=float, default=0.3, help="Density for random (0.0-1.0, default: 0.3)")
    parser.add_argument("--swing", type=int, default=0, help="Swing percentage (0-75, default: 0)")
    parser.add_argument("--humanize", action="store_true",
                        help="Add human-like timing and velocity variation")
    parser.add_argument("--play", action="store_true", help="Play the pattern (if audio available)")
    parser.add_argument("--list-presets", action="store_true", help="List available presets")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--save", type=str, metavar="FILE.json", help="Save pattern to JSON")
    parser.add_argument("--load", type=str, metavar="FILE.json", help="Load pattern from JSON")

    args = parser.parse_args()

    try:
        machine = DrumMachine(bpm=args.bpm, steps=args.steps, swing=args.swing / 100.0)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if args.humanize:
        machine.humanize = True

    if args.list_presets:
        print(machine.display_presets())
        return

    if args.load:
        if not machine.load_pattern_json(args.load):
            sys.exit(1)

    if args.preset:
        if not machine.load_preset(args.preset):
            print(f"Unknown preset: {args.preset}")
            print(machine.display_presets())
            sys.exit(1)

    if args.random:
        machine.random_pattern(density=args.density)

    # Show the grid
    print()
    print(machine.display_grid())
    print()

    if args.export:
        try:
            machine.render_to_wav(args.export, loops=args.loops)
            print(f"✓ Exported {args.loops} loop(s) to: {args.export}")
            print(f"  BPM: {machine.bpm}, Steps: {machine.steps}, Swing: {machine.swing:.0%}")
            if machine.humanize:
                print(f"  Humanize: ON (±{machine.humanize_timing*1000:.1f}ms timing, ±{machine.humanize_velocity:.0%} velocity)")
        except (OSError, ValueError) as e:
            print(f"Error exporting: {e}")
            sys.exit(1)

    if args.export_midi:
        try:
            machine.render_to_midi(args.export_midi)
            print(f"✓ Exported MIDI to: {args.export_midi}")
            print(f"  BPM: {machine.bpm}, Steps: {machine.steps}")
        except (OSError, ValueError) as e:
            print(f"Error exporting MIDI: {e}")
            sys.exit(1)

    if args.save:
        try:
            machine.save_pattern_json(args.save)
            print(f"✓ Pattern saved to: {args.save}")
        except OSError as e:
            print(f"Error saving: {e}")
            sys.exit(1)

    if args.play:
        print("Playing pattern...")
        loop = machine.render_full_loop()
        played = try_play_audio(loop)
        if not played:
            print("(Audio playback not available on this system)")

    if args.interactive or (not args.export and not args.play and not args.list_presets
                            and not args.save and not args.export_midi):
        interactive_mode(machine)


if __name__ == "__main__":
    main()