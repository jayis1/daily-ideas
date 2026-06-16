# 🎵 Procedural Music Box

**Algorithmic melody generator, visualizer, MIDI exporter, and WAV exporter.**

Procedural Music Box generates unique melodies using music theory — scales, modes, chord progressions, and rhythmic patterns — then renders them as an ASCII piano roll and exports them as playable WAV audio and Standard MIDI files. Every run produces a different composition, or lock it in with a seed for reproducibility.

## Features

- **14 scales/modes** — Ionian (major), Dorian, Phrygian, Lydian, Mixolydian, Aeolian (minor), Locrian, Pentatonic (major & minor), Blues, Harmonic Minor, Melodic Minor, Whole Tone, and Chromatic
- **4 composition styles** — Melodic (stepwise motion), Arpeggiated (chord patterns), Counterpoint (two voices), and Drone (ambient)
- **7 waveforms** — Sine, Square, Sawtooth, Triangle, Piano, Organ, and Bell
- **Waveform-specific ADSR envelopes** — Each waveform type uses a tailored attack/decay/sustain/release profile (e.g., bells have long release, pianos have fast attack)
- **Note density control** — Adjust how many rests vs. notes the melodic generator produces (0.0–1.0)
- **Volume control** — Scale output audio volume from 0.1 to 2.0
- **MIDI export** — Save compositions as `.mid` files for use in any DAW or MIDI player
- **Multi-voice support** — Notes carry a `channel` field; counterpoint mode uses two voices; MIDI export preserves channels
- **Melody transpose** — Programmatically transpose any melody by semitones
- **ASCII piano roll** — Visualize the melody directly in your terminal with note positions, durations, and measure markers
- **Melody statistics** — Note range, average interval, velocity, most-used notes, duration breakdown, voice breakdown
- **Text notation** — Readable shorthand notation showing measure-by-measure note events with duration labels (w/h/q/e/s)
- **WAV export** — Save synthesized audio as a standard 16-bit mono WAV file
- **Deterministic seeds** — Reproduce any generated melody exactly
- **Interactive mode** — Guided parameter selection with a terminal UI
- **`--version` and `--help`** — Standard CLI flags
- **Flat/sharp note parsing** — Accepts `Bb`, `Eb`, `C#`, etc. as root notes, plus octave notation (`A3`, `C5`)
- **34 unit tests** — Comprehensive test coverage for theory, generation, synthesis, MIDI export, and visualization

## Installation

No external dependencies needed — uses only the Python standard library:

```bash
# Just run it directly
python3 music_box.py

# Or clone and run
cd daily-ideas/2026-06-16-procedural-music-box
python3 music_box.py
```

Requires Python 3.6+. No packages to install.

To run the test suite:

```bash
python3 -m pytest test_music_box.py -v
```

## Usage

### Quick Start

```bash
# Generate a random melody
python3 music_box.py

# Reproduce a specific melody with a seed
python3 music_box.py --seed 42

# Choose root, scale, and tempo
python3 music_box.py --root E --scale dorian --bpm 130

# Pick a composition style
python3 music_box.py --style arpeggiated
python3 music_box.py --style counterpoint
python3 music_box.py --style drone
python3 music_box.py --style melodic

# Adjust note density (fewer rests = higher density)
python3 music_box.py --density 0.9

# Use a different synthesizer sound
python3 music_box.py --waveform bell
python3 music_box.py --waveform organ

# Adjust output volume
python3 music_box.py --volume 1.5

# Save to a specific file
python3 music_box.py -o my_song.wav

# Export as MIDI alongside WAV
python3 music_box.py --midi-out song.mid

# Play audio immediately after generating (requires aplay, ffplay, or paplay)
python3 music_box.py --play

# Interactive mode (choose everything step by step)
python3 music_box.py --interactive

# Show version
python3 music_box.py --version
```

### Command-Line Options

| Flag | Default | Description |
|------|---------|-------------|
| `--version` | — | Show version number and exit |
| `--seed` | Random | Random seed for reproducibility |
| `--root` | `C` | Root note (C, C#, D, D#, E, F, F#, G, G#, A, A#, B, flats like Bb/Eb, or with octave e.g. A3) |
| `--scale` | `ionian` | Scale/mode (see list below) |
| `--bpm` | `120` | Tempo in BPM (60–240) |
| `--bars` | `8` | Number of bars (4–32) |
| `--density` | `0.7` | Note density for melodic style (0.0–1.0) |
| `--style` | `auto` | Composition style: melodic, arpeggiated, counterpoint, drone, auto |
| `--waveform` | `piano` | Sound: sine, square, sawtooth, triangle, piano, organ, bell |
| `--volume` | `1.0` | Output volume (0.1–2.0) |
| `--output`, `-o` | Auto-named | Output WAV filename |
| `--midi-out` | Off | Also export as MIDI file (.mid) |
| `--play` | Off | Play audio after generating |
| `--no-piano-roll` | Off | Hide the piano roll visualization |
| `--interactive`, `-i` | Off | Launch interactive mode |

### Available Scales

`ionian` `dorian` `phrygian` `lydian` `mixolydian` `aeolian` `locrian` `pentatonic_major` `pentatonic_minor` `blues` `harmonic_minor` `melodic_minor` `whole_tone` `chromatic`

## Examples

### E Dorian at 130 BPM
```bash
python3 music_box.py --root E --scale dorian --bpm 130 --bars 12 --seed 42
```

### A Harmonic Minor Arpeggios with Bell Sound
```bash
python3 music_box.py --root A --scale harmonic_minor --bpm 160 --style arpeggiated --waveform bell --seed 99
```

### Ambient Drone in C Blues
```bash
python3 music_box.py --scale blues --bpm 100 --style drone --bars 8 --seed 7
```

### Whole Tone Counterpoint with MIDI Export
```bash
python3 music_box.py --scale whole_tone --style counterpoint --bars 8 --seed 123 --midi-out wholetone.mid
```

### Dense Melodic Line with Volume Boost
```bash
python3 music_box.py --density 0.95 --volume 1.5 --waveform organ --bars 16
```

## How It Works

### Melody Generation

Each style uses a different algorithmic approach:

- **Melodic** — Stepwise motion with weighted interval choices: 50% scale steps, 25% small leaps, 15% large leaps, 10% dramatic jumps. Downbeats get accent velocities. Rest probability is controlled by a density parameter (0.0 = sparse, 1.0 = dense).

- **Arpeggiated** — Selects from common chord progressions (pop I-V-vi-iii, classic I-IV-V-V, jazzy I-iii-V-I, etc.) and arpeggiates through chord tones. Supports up, down, up-down, and random arpeggio patterns.

- **Counterpoint** — Generates a bass line using whole notes on chord tones, then creates a faster melodic voice above it with stepwise motion. The two voices are tagged with separate MIDI channels for independent control.

- **Drone** — Sustains root, fifth, and octave drones for the entire duration, then layers a slow-moving melody on top with lots of held notes and small intervals.

### Audio Synthesis

The synthesizer renders each note using additive waveform synthesis with waveform-specific ADSR envelopes. Each waveform has its own attack, decay, sustain, and release timing:

| Waveform | Attack | Decay | Sustain | Release | Character |
|----------|--------|-------|---------|---------|-----------|
| Sine     | 10ms   | 100ms | 0.80    | 150ms   | Pure, clean |
| Square   | 5ms    | 50ms  | 0.70    | 100ms   | Retro, chiptune |
| Sawtooth | 5ms    | 80ms  | 0.60    | 120ms   | Bright, buzzy |
| Triangle | 10ms   | 100ms | 0.75    | 150ms   | Soft, mellow |
| Piano    | 8ms    | 150ms | 0.60    | 200ms   | Rich harmonics |
| Organ    | 20ms   | 50ms  | 0.85    | 100ms   | Sustained, drawbar |
| Bell     | 1ms    | 500ms | 0.30    | 800ms   | Inharmonic, long decay |

Each waveform is built from fundamental + harmonics:
- **Piano** — Sine + harmonics at 2×, 3×, 4× with decreasing amplitude
- **Organ** — Strong harmonics (drawbar-style)
- **Bell** — Inharmonic partials (2.756×, 5.404× ratios)

All samples are normalized to prevent clipping before WAV export.

### MIDI Export

MIDI files are written in Standard MIDI File Format 0, with 480 ticks per quarter note. Each note is encoded as a Note On/Note Off pair with proper delta-time encoding. Multi-channel notes (from counterpoint mode) are preserved in the output. Tempo is stored as a meta event.

### Piano Roll

The ASCII piano roll maps MIDI note numbers to rows and time to columns. Sharps are shown with a dotted background (`·`), naturals with spaces. Notes appear as `▸` (start) and `━` (continuation), with measure boundaries marked by `┆`.

## File Structure

```
2026-06-16-procedural-music-box/
├── music_box.py          # Complete implementation (single file)
├── test_music_box.py      # 34 unit tests
└── README.md              # This file
```

## Changelog

### v1.1.0
- Added `--version` flag
- Added `--volume` flag for output volume control (0.1–2.0)
- Added `--density` flag to control note density in melodic style
- Added `--midi-out` flag for Standard MIDI File export
- Added waveform-specific ADSR envelope presets (bell has long release, piano has fast attack, etc.)
- Added `Note.channel` field for multi-voice support; counterpoint now uses channel 0/1
- Added `Melody.voices()` method to group notes by channel
- Added `Melody.transpose()` method to shift melodies by semitones
- Added `Note.is_sharp()` helper method
- Added `name_to_midi()` parser supporting flats (Bb, Eb) and octave notation (A3, C5)
- Added 34 unit tests covering theory, generation, synthesis, MIDI export, and visualization
- Improved duration names in notation display (e.g., "whole", "half", "quarter" instead of raw numbers)
- Improved voice breakdown in statistics for multi-channel melodies
- Improved input validation (BPM clamped 60–240, bars 4–32, volume 0.1–2.0)
- Added `paplay` as fallback audio player
- Show file size and sample rate in WAV export output
- Removed dead code (`_envelope` method was never called; inlined envelope is now parameterized)
- Fixed piano roll reversed-index bug in the complex renderer

## License

CC0 — use it however you like.