# 🎵 Wave Synth — Terminal Audio Waveform Synthesizer

Generate, visualize, mix, and export audio waveforms entirely from the command line. No GUI, no dependencies beyond Python's standard library — just pure terminal audio synthesis.

![Waveform visualization](https://img.shields.io/badge/platform-terminal-black?style=flat-square) ![Python 3.7+](https://img.shields.io/badge/python-3.7%2B-blue?style=flat-square) ![Zero dependencies](https://img.shields.io/badge/dependencies-zero-green?style=flat-square)

## Features

### Waveform Generation
- **7 waveform types**: sine, square, sawtooth, triangle, noise, harmonic (custom overtones), and chirp (frequency sweep)
- **Musical note support**: Use notes like `A4`, `C#5`, `Eb3` instead of raw Hz frequencies
- **Full chromatic scale**: All notes C0–C8 including sharps (`C#`) and flats (`Eb`)

### Effects (15 total)
- **Tremolo** — amplitude modulation (rate + depth)
- **Vibrato** — frequency modulation via delay modulation
- **Lowpass filter** — one-pole IIR low-pass (cutoff in Hz)
- **Highpass filter** — one-pole IIR high-pass (cutoff in Hz)
- **Distortion** — soft-clipping using tanh approximation (drive)
- **Delay/Echo** — with feedback control
- **Fade-in / Fade-out** — smooth volume ramps
- **Normalize** — peak normalization to target level
- **ADSR envelope** — Attack-Decay-Sustain-Release shaping
- **Reverse** — backwards playback
- **Ring modulation** — multiply with a carrier frequency
- **Bitcrush** — reduce bit depth for lo-fi crunch (1–16 bits)
- **Reverb** — multi-tap room simulation (decay control)
- **Pitch shift** — resample-based semitone shifting
- **Effect chaining** — stack multiple effects on a single waveform

### Visualization
- **ASCII art waveform display** with Unicode box-drawing characters and scale labels
- **Frequency spectrum** — approximate DFT bar chart with logarithmic frequency bins
- **Waveform info** — duration, sample count, peak amplitude, RMS, estimated frequency

### Music Theory
- **10 chord types**: maj, min, dim, aug, 7, maj7, min7, sus2, sus4, 5
- **Arpeggio generation** — play chord notes sequentially through any waveform
- **5 preset melodies**: C major scale, Happy Birthday, Ode to Joy, Twinkle Twinkle Little Star, pentatonic

### Audio I/O
- **WAV export** — 16-bit PCM mono WAV files
- **WAV import** — load 8-bit or 16-bit WAV files, apply effects, and re-export
- **Interactive mode** — full REPL-style synthesizer with command history

## Installation

No installation required — just download and run:

```bash
# Clone or download
git clone https://github.com/youruser/daily-ideas.git
cd daily-ideas/2026-06-13-wave-synth

# Make executable (optional)
chmod +x wave_synth.py
```

Requires Python 3.7+ (no external packages needed).

## Usage

### Basic Waveform Generation

```bash
# Generate a 2-second sine wave at A4 (440 Hz)
python3 wave_synth.py sine A4 2

# Use frequency in Hz directly
python3 wave_synth.py sine 440 2

# Square wave at 220 Hz
python3 wave_synth.py square 220 1

# Sawtooth wave at middle C
python3 wave_synth.py sawtooth C4 3

# Triangle wave
python3 wave_synth.py triangle E4 1.5

# White noise (1 second, first arg is duration)
python3 wave_synth.py noise 1

# Harmonic wave with custom overtones
python3 wave_synth.py harmonic C4 2 --harmonics "1,1 2,0.5 3,0.25 4,0.125"

# Frequency sweep (chirp) from 200 Hz to 2000 Hz
python3 wave_synth.py chirp 200 2000 3

# Exponential frequency sweep
python3 wave_synth.py chirp 100 5000 4 --sweep-method exponential
```

### Applying Effects

```bash
# Tremolo effect (rate=6Hz, depth=0.7)
python3 wave_synth.py sine A4 2 --effect tremolo:6:0.7

# Low-pass filter at 1000 Hz
python3 wave_synth.py sawtooth C4 2 --effect lowpass:1000

# High-pass filter at 200 Hz
python3 wave_synth.py square 100 3 --effect highpass:200

# Distortion (drive=3)
python3 wave_synth.py sine A4 1 --effect distortion:3

# Delay/echo (0.3s delay, 0.4 feedback)
python3 wave_synth.py sine A4 2 --effect delay:0.3:0.4

# Reverse playback
python3 wave_synth.py sine A4 2 --effect reverse

# Ring modulation (100 Hz carrier)
python3 wave_synth.py sine A4 2 --effect ringmod:100

# Bitcrush to 4-bit lo-fi
python3 wave_synth.py sine A4 2 --effect bitcrush:4

# Reverb (decay=0.4)
python3 wave_synth.py sine A4 2 --effect reverb:0.4

# Pitch shift up 5 semitones
python3 wave_synth.py sine A4 2 --effect pitchshift:5

# Chain multiple effects
python3 wave_synth.py sawtooth 220 2 --effect lowpass:2000 --effect distortion:2 --effect reverb:0.3

# Suppress visualization (useful for scripting)
python3 wave_synth.py sine A4 2 --effect normalize --quiet
```

### ADSR Envelope

```bash
# Apply envelope: Attack=0.05s, Decay=0.1s, Sustain=0.7, Release=0.3s
python3 wave_synth.py sine C4 2 --adsr 0.05,0.1,0.7,0.3
```

### Chords and Arpeggios

```bash
# C major chord (2 seconds)
python3 wave_synth.py chord C4 maj 2

# A minor 7th arpeggio (3 seconds, triangle wave)
python3 wave_synth.py arp A3 min7 3 --wave triangle

# D diminished chord
python3 wave_synth.py chord D4 dim 2 --wave sawtooth

# G7 chord with ADSR
python3 wave_synth.py chord G4 7 2 --wave sine --adsr 0.01,0.1,0.6,0.3
```

Available chord types: `maj`, `min`, `dim`, `aug`, `7`, `maj7`, `min7`, `sus2`, `sus4`, `5`

### Preset Melodies

```bash
# Twinkle Twinkle Little Star
python3 wave_synth.py melody twinkle

# C major scale
python3 wave_synth.py melody scale

# Happy Birthday
python3 wave_synth.py melody happy_birthday

# Ode to Joy (triangle wave)
python3 wave_synth.py melody ode_to_joy --wave triangle

# Pentatonic scale (sawtooth)
python3 wave_synth.py melody pentatonic --wave sawtooth
```

### Frequency Spectrum

```bash
# Show spectrum instead of waveform
python3 wave_synth.py --spectrum sine A4 1

# Spectrum of a complex waveform
python3 wave_synth.py --spectrum harmonic C4 2 --harmonics "1,1 2,0.5 3,0.3 5,0.2"
```

### Exporting and Importing WAV

```bash
# Export a waveform to a WAV file
python3 wave_synth.py sine A4 2 --export output.wav

# Chain effects and export
python3 wave_synth.py sawtooth 220 2 --effect lowpass:1000 --effect reverb:0.4 --export synth_sound.wav

# Export an arpeggio
python3 wave_synth.py arp C4 maj 3 --export arpeggio.wav

# Import a WAV file, apply effects, and re-export
python3 wave_synth.py --import-wav input.wav --effect reverb:0.3 --export processed.wav
```

### Waveform Info

```bash
# Show technical info about the waveform
python3 wave_synth.py sine A4 2 --info
```

Output:
```
  Name:       sine_A4_2
  Duration:   2.000s
  Samples:   88200
  Peak:       0.8000
  RMS:        0.5657
  Est. Freq:  439.8 Hz
```

### Version and Help

```bash
# Show version
python3 wave_synth.py --version

# Show full help with examples
python3 wave_synth.py --help
```

### Interactive Mode

```bash
python3 wave_synth.py --interactive
```

In interactive mode, you can:
- Generate waveforms: `gen sine A4 2`
- Generate chirps: `chirp 200 2000 3`
- Apply effects: `effect reverb:0.3`, `effect bitcrush:4`, `effect reverse`
- Apply ADSR: `adsr 0.01 0.1 0.7 0.2`
- Mix waveforms: `mix 0 1` (combines stored waves 0 and 1)
- Generate chords: `chord C4 maj 2`
- Generate arpeggios: `arp A3 min7 3`
- Play preset melodies: `melody twinkle`
- Import WAV: `import recording.wav`
- Visualize: `viz` or `spectrum`
- Show info: `info`
- Export: `export output.wav`
- List stored waves: `list`
- Quit: `quit`

## Supported Note Names

All notes from C0 through C8 are supported, including sharps and flats:
- `C4` = 261.63 Hz (middle C)
- `A4` = 440.00 Hz (concert A)
- `F#5` = 739.99 Hz (F sharp 5)
- `Eb3` = 155.56 Hz (E flat 3)
- `Bb4` = 466.16 Hz (B flat 4)

Or use raw frequencies: `440`, `261.63`, etc.

## How It Works

- **Wave generation**: Mathematical functions produce sample arrays at 44100 Hz sample rate
- **Chirp/sweep**: Linear and exponential frequency sweeps with proper phase integration
- **ASCII visualization**: Downsamples the waveform and maps amplitude values to Unicode box-drawing characters
- **Spectrum analysis**: Approximates a DFT across logarithmically-spaced frequency bins
- **WAV export**: Converts float samples to 16-bit PCM with proper WAV header structure
- **WAV import**: Reads 8-bit and 16-bit WAV files (mono and stereo, auto-mixdown)
- **Effects**: Tremolo (AM), vibrato (FM via delay modulation), one-pole IIR filters, tanh distortion, delay with feedback, bitcrushing, ring modulation, reverb, and resampling pitch shift
- **ADSR**: Classic synthesizer envelope with linear ramp segments

## Running Tests

```bash
python3 -m unittest test_wave_synth -v
```

The test suite covers waveform generation, note resolution, all effects, mixing, chord/arpeggio generation, melody presets, WAV I/O roundtrips, and visualization.

## License

MIT