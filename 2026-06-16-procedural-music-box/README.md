# 🎵 Procedural Music Box

**Algorithmic melody generator, visualizer, and WAV exporter.**

Procedural Music Box generates unique melodies using music theory — scales, modes, chord progressions, and rhythmic patterns — then renders them as an ASCII piano roll and exports them as playable WAV audio files. Every run produces a different composition, or lock it in with a seed for reproducibility.

## Features

- **14 scales/modes** — Ionian (major), Dorian, Phrygian, Lydian, Mixolydian, Aeolian (minor), Locrian, Pentatonic (major & minor), Blues, Harmonic Minor, Melodic Minor, Whole Tone, and Chromatic
- **4 composition styles** — Melodic (stepwise motion), Arpeggiated (chord patterns), Counterpoint (two voices), and Drone (ambient)
- **7 waveforms** — Sine, Square, Sawtooth, Triangle, Piano, Organ, and Bell
- **ASCII piano roll** — Visualize the melody directly in your terminal with note positions, durations, and measure markers
- **Melody statistics** — Note range, average interval, velocity, most-used notes
- **Text notation** — Readable shorthand notation showing measure-by-measure note events
- **WAV export** — Save synthesized audio as a standard WAV file
- **Deterministic seeds** — Reproduce any generated melody exactly
- **Interactive mode** — Guided parameter selection with a terminal UI
- **Configurable** — Root note, scale, BPM, bar count, density, and style all adjustable via CLI flags

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

# Use a different synthesizer sound
python3 music_box.py --waveform bell
python3 music_box.py --waveform organ

# Save to a specific file
python3 music_box.py -o my_song.wav

# Interactive mode (choose everything step by step)
python3 music_box.py --interactive

# Play audio immediately after generating (requires aplay or ffplay)
python3 music_box.py --play
```

### Command-Line Options

| Flag | Default | Description |
|------|---------|-------------|
| `--seed` | Random | Random seed for reproducibility |
| `--root` | `C` | Root note (C, C#, D, D#, E, F, F#, G, G#, A, A#, B) |
| `--scale` | `ionian` | Scale/mode (see list below) |
| `--bpm` | `120` | Tempo in BPM (60–240) |
| `--bars` | `8` | Number of bars (4–32) |
| `--style` | `auto` | Composition style: melodic, arpeggiated, counterpoint, drone, auto |
| `--waveform` | `piano` | Sound: sine, square, sawtooth, triangle, piano, organ, bell |
| `--output`, `-o` | Auto-named | Output WAV filename |
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

Output includes an ASCII piano roll showing note positions, duration, and measure markers, followed by statistics and measure-by-measure notation.

### A Harmonic Minor Arpeggios with Bell Sound
```bash
python3 music_box.py --root A --scale harmonic_minor --bpm 160 --style arpeggiated --waveform bell --seed 99
```

### Ambient Drone in C Blues
```bash
python3 music_box.py --scale blues --bpm 100 --style drone --bars 8 --seed 7
```

### Whole Tone Counterpoint
```bash
python3 music_box.py --scale whole_tone --style counterpoint --bars 8 --seed 123
```

## How It Works

### Melody Generation

Each style uses a different algorithmic approach:

- **Melodic** — Stepwise motion with weighted interval choices: 50% scale steps, 25% small leaps, 15% large leaps, 10% dramatic jumps. Downbeats get accent velocities. Rest probability is controlled by a density parameter.

- **Arpeggiated** — Selects from common chord progressions (pop I-V-vi-iii, classic I-IV-V-V, jazzy I-iii-V-I, etc.) and arpeggiates through chord tones. Supports up, down, up-down, and random arpeggio patterns.

- **Counterpoint** — Generates a bass line using whole notes on chord tones, then creates a faster melodic voice above it with stepwise motion. The two voices create harmonic intervals.

- **Drone** — Sustains root, fifth, and octave drones for the entire duration, then layers a slow-moving melody on top with lots of held notes and small intervals.

### Audio Synthesis

The synthesizer renders each note using additive waveform synthesis with an ADSR envelope (attack, decay, sustain, release). Each waveform is built from fundamental + harmonics:

- **Piano** — Sine + harmonics at 2×, 3×, 4× with decreasing amplitude
- **Organ** — Strong harmonics (drawbar-style)
- **Bell** — Inharmonic partials (2.756×, 5.404× ratios)
- **Square/Saw/Triangle** — Classic waveforms

All samples are normalized to prevent clipping before WAV export.

### Piano Roll

The ASCII piano roll maps MIDI note numbers to rows and time to columns. Sharps are shown with a dotted background (`·`), naturals with spaces. Notes appear as `▸` (start) and `━` (continuation), with measure boundaries marked by `┆`.

## File Structure

```
2026-06-16-procedural-music-box/
├── music_box.py    # Complete implementation (single file)
└── README.md       # This file
```

## License

CC0 — use it however you like.