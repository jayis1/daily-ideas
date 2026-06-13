# 🎵 Wave Synth — Terminal Audio Waveform Synthesizer

**Version 1.2.0** — A command-line tool for generating, visualizing, mixing, and exporting audio waveforms entirely from your terminal.

Generate sine, square, sawtooth, triangle, pulse, noise, harmonic, and chirp waveforms. Apply effects like tremolo, distortion, reverb, compressor, flanger, and more. Visualize as ASCII art or export as WAV files.

## Features

- **8 waveform types**: sine, square, sawtooth, triangle, pulse, noise, harmonic, chirp
- **17 audio effects**: tremolo, vibrato, lowpass, highpass, distortion, delay, fade-in/out, normalize, ADSR envelope, reverse, ring modulation, bitcrush, reverb, pitch shift, **compressor**, **flanger**
- **Pulse wave**: Variable duty cycle square wave (new in v1.2)
- **Dynamic compressor**: Threshold/ratio-based dynamics processing (new in v1.2)
- **Flanger**: Sweeping modulated delay with feedback (new in v1.2)
- **Melody transposition**: Shift melodies up/down by semitones (new in v1.2)
- **Musical note support**: Use note names like `A4`, `C#5`, `Eb3` — sharps and flats, case-insensitive
- **13 chord types**: maj, min, dim, aug, 7, maj7, min7, sus2, sus4, 5, **add9, 6, 9** (new in v1.2)
- **7 melody presets**: scale, happy_birthday, ode_to_joy, twinkle, pentatonic, **fur_elise**, **amazing_grace** (2 new in v1.2)
- **WAV import/export**: Load 8-bit or 16-bit WAV files, apply effects, re-export
- **ASCII visualization**: Waveform and frequency spectrum display in your terminal
- **Waveform info**: Duration, peak, RMS, DC offset, crest factor, estimated frequency
- **Interactive mode**: REPL for real-time waveform experimentation
- **Custom harmonics**: Define your own harmonic series for rich tones
- **Note & chord reference**: `--list-notes` and `--list-chords` flags for discoverability
- **`__all__` exports**: Clean public API for programmatic use
- **Comprehensive docstrings**: All functions fully documented with Args/Returns/Raises

## Installation

No external dependencies required — uses only Python standard library modules.

```bash
# Clone or download, then run directly:
python3 wave_synth.py sine A4 2
```

## Quick Start

```bash
# Generate 2 seconds of A4 (440 Hz) sine wave
python3 wave_synth.py sine A4 2

# Square wave at 220 Hz with tremolo effect
python3 wave_synth.py square 220 1 --effect tremolo

# Pulse wave with 25% duty cycle
python3 wave_synth.py pulse A4 2 --duty 0.25

# C major chord with sawtooth wave
python3 wave_synth.py chord C4 maj 2 --wave sawtooth

# A minor 7 arpeggio
python3 wave_synth.py arp A3 min7 3

# Fur Elise melody with triangle wave
python3 wave_synth.py melody fur_elise --wave triangle

# Frequency sweep (chirp) from 200 Hz to 2000 Hz
python3 wave_synth.py chirp 200 2000 3

# Sine wave with reverb and compressor, exported to WAV
python3 wave_synth.py sine A4 2 --effect reverb:0.4 --effect compressor:0.5:4 --export output.wav

# Sine wave with flanger effect
python3 wave_synth.py sine A4 2 --effect flanger:0.5:0.002:0.3

# 4-bit crushed sine
python3 wave_synth.py sine A4 2 --effect bitcrush:4

# Import a WAV, apply effects, re-export
python3 wave_synth.py --import-wav input.wav --effect lowpass:800 --export processed.wav

# Show frequency spectrum
python3 wave_synth.py sine A4 1 --spectrum

# Show detailed waveform info
python3 wave_synth.py sine A4 1 --info

# List all note names and frequencies
python3 wave_synth.py --list-notes

# List all chord types
python3 wave_synth.py --list-chords

# Interactive mode
python3 wave_synth.py --interactive
```

## Usage

```
python3 wave_synth.py <wave_type> <note/freq> <duration> [options]
```

### Positional Arguments

| Argument     | Description                                         |
|--------------|-----------------------------------------------------|
| `wave_type`  | sine, square, sawtooth, triangle, pulse, noise, harmonic, chirp, chord, arp, melody |
| `remaining`  | Note/frequency, chord type, duration (varies)      |

### Options

| Flag                     | Description                                        |
|--------------------------|----------------------------------------------------|
| `--interactive`, `-i`    | Start interactive mode                              |
| `--version`, `-V`        | Show version                                       |
| `--wave`, `-w`           | Wave type for chord/arp/melody (default: sine)     |
| `--amplitude`, `-a`      | Amplitude 0–1 (default: 0.8)                        |
| `--export`, `-e`         | Export to WAV file                                  |
| `--import-wav`           | Import WAV file and apply effects                   |
| `--effect`, `-f`         | Apply effect (can be used multiple times)           |
| `--adsr`                 | Apply ADSR envelope (e.g. `0.01,0.1,0.7,0.2`)       |
| `--chord-type`, `-c`     | Chord type for chord/arp (default: maj)             |
| `--harmonics`            | Custom harmonics (e.g. `"1,1 2,0.5 3,0.25"`)        |
| `--duty`                 | Duty cycle for pulse wave (0.0–1.0, default: 0.5)   |
| `--sweep-method`         | Chirp method: linear or exponential (default: linear) |
| `--spectrum`, `-s`       | Show frequency spectrum instead of waveform         |
| `--info`                 | Show waveform info (duration, peak, RMS, etc.)       |
| `--quiet`, `-q`          | Suppress visualization output                        |
| `--seed`                 | Random seed for noise generation                    |
| `--width`                | Visualization width (default: 72)                   |
| `--height`               | Visualization height (default: 16)                  |
| `--list-notes`           | List all note names and frequencies                 |
| `--list-chords`          | List all chord types and intervals                  |

### Effect Parameters

Effects can be specified with parameters using colons:

```
--effect tremolo:5:0.5          Tremolo (rate Hz, depth 0-1)
--effect vibrato:5:0.002        Vibrato (rate Hz, depth seconds)
--effect lowpass:1000            Low-pass filter (cutoff Hz)
--effect highpass:1000           High-pass filter (cutoff Hz)
--effect distortion:3            Distortion (drive 0+)
--effect delay:0.3:0.4          Delay (time seconds, feedback 0-1)
--effect fadein:0.05            Fade in (duration seconds)
--effect fadeout:0.05           Fade out (duration seconds)
--effect normalize               Normalize to peak 0.95
--effect reverse                 Reverse waveform
--effect ringmod:100             Ring modulation (carrier Hz)
--effect bitcrush:4             Bit crush (1–16 bits)
--effect reverb:0.3              Reverb (decay 0-1)
--effect pitchshift:5            Pitch shift (semitones)
--effect compressor:0.5:4       Compressor (threshold 0-1, ratio 1+)
--effect flanger:0.5:0.002:0.3  Flanger (rate Hz, depth s, feedback 0-1)
```

### Note Names

Supports standard scientific pitch notation:
- Sharps: `C#4`, `A#3`, `F#5`
- Flats: `Eb3`, `Bb4`, `Ab5`
- Case-insensitive: `eb3`, `bb4`, `c#5` all work
- Numeric frequencies: `440`, `261.63`

### Chord Types

`maj`, `min`, `dim`, `aug`, `7`, `maj7`, `min7`, `sus2`, `sus4`, `5`, `add9`, `6`, `9`

### Melody Presets

`scale`, `happy_birthday`, `ode_to_joy`, `twinkle`, `pentatonic`, `fur_elise`, `amazing_grace`

### Pulse Wave Duty Cycle

The `pulse` wave type generates a rectangular wave with configurable duty cycle:
- `--duty 0.5` → standard square wave (default)
- `--duty 0.25` → narrow pulse, buzzy sound
- `--duty 0.1` → very narrow click-like pulse

## Interactive Mode

Run `python3 wave_synth.py --interactive` for a REPL:

```
wave> gen sine A4 2
wave> effect tremolo:5:0.5
wave> effect reverb:0.3
wave> effect compressor:0.5:4
wave> effect flanger:0.5:0.002:0.3
wave> viz
wave> export output.wav
wave> quit
```

Interactive mode also supports:
- `pulse <freq> <duration> [duty]` — Generate pulse waves
- `transpose <semitones>` — Transpose the last melody by semitones
- `info` — Show detailed waveform statistics

## Programmatic Use

```python
from wave_synth import generate_sine, apply_reverb, apply_compressor, export_wav

# Generate a sine wave
samples = generate_sine(440.0, 2.0, amplitude=0.8)

# Apply effects chain
samples = apply_compressor(samples, threshold=0.5, ratio=4.0)
samples = apply_reverb(samples, decay=0.3)

# Export to WAV
export_wav(samples, 'output.wav')
```

All public functions are exported via `__all__`.

## What's New

### v1.2.0 — Feature Release

**New features:**
- **Pulse wave generator** (`generate_pulse`) — variable duty cycle rectangular wave
- **Compressor effect** (`apply_compressor`) — dynamics processing with threshold, ratio, attack, and release
- **Flanger effect** (`apply_flanger`) — classic sweeping modulated delay
- **Melody transposition** (`transpose_melody`) — shift melodies up/down by semitones
- **`--list-notes` and `--list-chords` CLI flags** — reference tables for all notes and chords
- **`--duty` flag** for pulse wave duty cycle control
- **3 new chord types**: `add9`, `6`, `9`
- **2 new melody presets**: `fur_elise`, `amazing_grace`
- **`_generate_wave_for_type()` helper** — unified wave generation for chords/arps/melodies
- **`EFFECT_DESCRIPTIONS` dict** — human-readable descriptions for all effects
- **`__all__` exports** — clean public API
- **Enhanced `print_waveform_info()`** — now shows DC offset, crest factor, and sample rate
- **Comprehensive docstrings** on all public functions with Args/Returns/Raises
- **`export_wav()` validates empty input** — raises `ValueError` on empty samples
- **Empty sample handling** added to tremolo, vibrato, delay, ring_mod, reverb, flanger, fade_in, fade_out, bitcrush, and compressor

**Tests:**
- 113 tests (up from 80), including new test classes for pulse wave, compressor, flanger, transpose, edge cases, and effect registry completeness

### v1.1.1 — Bug Fix Release

- Fixed `note_to_freq` corrupted B notes
- Fixed `resolve_freq` failed on lowercase flat notes
- Fixed `generate_chord`/`generate_arpeggio`/`generate_melody` crashed with harmonic/chirp wave types
- Fixed `lowpass`/`highpass` crashed on empty samples
- Fixed `pitch_shift` returned `[0.0]` on empty input
- Fixed `distortion` with `drive=0` raised `ValueError`
- Fixed `mix_waves` with all-zero weights caused `ZeroDivisionError`
- Fixed `visualize_ascii` scale labels shifting row indices

### v1.1.0 — Feature Release

- Added chirp/sweep waveform, 5 effects (reverse, ring mod, bitcrush, reverb, pitch shift), WAV import, `--version`/`-V`, `--quiet`/`-q`, interactive mode enhancements

### v1.0.0 — Initial Release

- Basic waveform generation, effects, visualization, WAV export

## License

MIT