# 🎵 Wave Synth — Terminal Audio Waveform Synthesizer

**Version 1.1.1** — A command-line tool for generating, visualizing, mixing, and exporting audio waveforms entirely from your terminal.

Generate sine, square, sawtooth, triangle, noise, harmonic, and chirp waveforms. Apply effects like tremolo, distortion, reverb, and more. Visualize as ASCII art or export as WAV files.

## Features

- **7 waveform types**: sine, square, sawtooth, triangle, noise, harmonic, chirp
- **15 audio effects**: tremolo, vibrato, lowpass, highpass, distortion, delay, fade-in/out, normalize, ADSR envelope, reverse, ring modulation, bitcrush, reverb, pitch shift
- **Musical note support**: Use note names like `A4`, `C#5`, `Eb3` — sharps and flats, case-insensitive
- **Chord & arpeggio generation**: 10 chord types (maj, min, dim, aug, 7, maj7, min7, sus2, sus4, 5)
- **Melody presets**: scale, happy_birthday, ode_to_joy, twinkle, pentatonic
- **WAV import/export**: Load 8-bit or 16-bit WAV files, apply effects, re-export
- **ASCII visualization**: Waveform and spectrum display in your terminal
- **Interactive mode**: REPL for real-time waveform experimentation
- **Custom harmonics**: Define your own harmonic series for rich tones

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

# C major chord with sawtooth wave
python3 wave_synth.py chord C4 maj 2 --wave sawtooth

# A minor 7 arpeggio
python3 wave_synth.py arp A3 min7 3

# Twinkle Twinkle melody with triangle wave
python3 wave_synth.py melody twinkle --wave triangle

# Frequency sweep (chirp) from 200 Hz to 2000 Hz
python3 wave_synth.py chirp 200 2000 3

# Sine wave with reverb, exported to WAV
python3 wave_synth.py sine A4 2 --effect reverb:0.4 --export output.wav

# 4-bit crushed sine
python3 wave_synth.py sine A4 2 --effect bitcrush:4

# Import a WAV, apply effects, re-export
python3 wave_synth.py --import-wav input.wav --effect lowpass:800 --export processed.wav

# Show frequency spectrum
python3 wave_synth.py sine A4 1 --spectrum

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
| `wave_type`  | sine, square, sawtooth, triangle, noise, harmonic, chirp, chord, arp, melody |
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
| `--sweep-method`         | Chirp method: linear or exponential (default: linear) |
| `--spectrum`, `-s`       | Show frequency spectrum instead of waveform         |
| `--info`                 | Show waveform info (duration, peak, RMS, etc.)       |
| `--quiet`, `-q`          | Suppress visualization output                        |
| `--seed`                 | Random seed for noise generation                    |
| `--width`                | Visualization width (default: 72)                   |
| `--height`               | Visualization height (default: 16)                  |

### Effect Parameters

Effects can be specified with parameters using colons:

```
--effect tremolo:5:0.5       Tremolo (rate, depth)
--effect vibrato:5:0.002    Vibrato (rate, depth)
--effect lowpass:1000       Low-pass filter (cutoff Hz)
--effect highpass:1000      High-pass filter (cutoff Hz)
--effect distortion:3       Distortion (drive, 0+)
--effect delay:0.3:0.4       Delay (time, feedback)
--effect fadein:0.05         Fade in (duration)
--effect fadeout:0.05        Fade out (duration)
--effect normalize           Normalize to peak 0.95
--effect reverse              Reverse waveform
--effect ringmod:100          Ring modulation (carrier Hz)
--effect bitcrush:4           Bit crush (1–16 bits)
--effect reverb:0.3           Reverb (decay 0–1)
--effect pitchshift:5         Pitch shift (semitones)
```

### Note Names

Supports standard scientific pitch notation:
- Sharps: `C#4`, `A#3`, `F#5`
- Flats: `Eb3`, `Bb4`, `Ab5`
- Case-insensitive: `eb3`, `bb4`, `c#5` all work
- Numeric frequencies: `440`, `261.63`

### Chord Types

`maj`, `min`, `dim`, `aug`, `7`, `maj7`, `min7`, `sus2`, `sus4`, `5`

### Melody Presets

`scale`, `happy_birthday`, `ode_to_joy`, `twinkle`, `pentatonic`

## Interactive Mode

Run `python3 wave_synth.py --interactive` for a REPL:

```
wave> gen sine A4 2
wave> effect tremolo:5:0.5
wave> effect reverb:0.3
wave> viz
wave> export output.wav
wave> quit
```

## Changelog

### v1.1.1 — Bug Fix Release

**Fixed:**
- **`note_to_freq` corrupted B notes** — `.upper().replace('B','b')` turned `B4` into `b4` (not in dictionary) and `Bb4` into `bb4` (wrong frequency). Rewrote to delegate to `resolve_freq` for correct lookup.
- **`resolve_freq` failed on lowercase flat notes** — `eb3`, `bb4`, `ab4` etc. crashed because `.upper()` produced `EB3` (not in dict). Added proper `_normalize_note_name()` function that preserves flat indicators.
- **`generate_chord`/`generate_arpeggio`/`generate_melody` crashed with harmonic wave type** — `sample_rate` (int) was being passed as the `harmonics` parameter. Fixed to use `sample_rate` as a keyword argument.
- **`generate_chord`/`generate_arpeggio`/`generate_melody` crashed with chirp wave type** — `WAVE_GENERATORS['chirp']` is `None`, causing `TypeError`. Fixed with explicit handling that uses `generate_chirp()` directly.
- **`lowpass`/`highpass` crashed on empty samples** — `IndexError` from accessing `samples[0]` on empty list. Added early return for empty input.
- **`pitch_shift` returned `[0.0]` on empty input** instead of `[]`. Fixed to return empty list.
- **`distortion` with `drive=0` raised `ValueError`** — changed to be a no-op (returns copy of samples). Negative drive still raises error.
- **`mix_waves` with all-zero weights** caused `ZeroDivisionError`. Added guard to return silence.
- **`visualize_ascii` scale labels inserted as extra rows** — scale labels (`+1.0`, `0.0`, `-1.0`) were `insert()`ed into the lines list, shifting row indices and producing a malformed display (wrong number of rows). Changed to overlay labels on existing rows instead.

**Added:**
- 15 new regression tests covering all fixed bugs
- Version bumped to 1.1.1

### v1.1.0 — Feature Release

- Added chirp/sweep waveform, 5 new effects (reverse, ring mod, bitcrush, reverb, pitch shift), WAV import, `--version`/`-V` flag, `--quiet`/`-q` flag, interactive mode enhancements
- Fixed flat note resolution, improved distortion, better error handling

### v1.0.0 — Initial Release

- Basic waveform generation, effects, visualization, WAV export

## License

MIT