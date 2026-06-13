# 🎵 Wave Synth — Terminal Audio Waveform Synthesizer

Generate, visualize, mix, and export audio waveforms entirely from the command line. No GUI, no dependencies beyond Python's standard library — just pure terminal audio synthesis.

![Waveform visualization](https://img.shields.io/badge/platform-terminal-black?style=flat-square)

## Features

- **6 waveform types**: sine, square, sawtooth, triangle, noise, and harmonic (with custom overtones)
- **ASCII art visualization**: Real-time waveform rendering in your terminal with scale labels
- **Frequency spectrum display**: Approximate DFT-based spectrum analysis as ASCII bar charts
- **9 audio effects**: tremolo, vibrato, lowpass filter, highpass filter, distortion, delay/echo, fade-in, fade-out, normalize
- **ADSR envelopes**: Attack-Decay-Sustain-Release envelope shaping
- **Chord generation**: 10 chord types (maj, min, dim, aug, 7, maj7, min7, sus2, sus4, 5)
- **Arpeggio generation**: Play chord notes sequentially through any waveform
- **5 preset melodies**: C major scale, Happy Birthday, Ode to Joy, Twinkle Twinkle Little Star, pentatonic
- **Note name support**: Use musical notes like `A4`, `C#5`, `Eb3` instead of raw frequencies
- **WAV export**: Save waveforms as standard 16-bit PCM WAV files
- **Interactive mode**: Full REPL-style synthesizer with command history
- **Waveform mixing**: Combine multiple waveforms with custom weights
- **Zero dependencies**: Pure Python, standard library only

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

# Chain multiple effects
python3 wave_synth.py sawtooth 220 2 --effect lowpass:2000 --effect distortion:2 --effect tremolo:5:0.5
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

### Exporting to WAV

```bash
# Export a waveform to a WAV file
python3 wave_synth.py sine A4 2 --export output.wav

# Chain effects and export
python3 wave_synth.py sawtooth 220 2 --effect lowpass:1000 --effect tremolo:5:0.6 --export synth_sound.wav

# Export an arpeggio
python3 wave_synth.py arp C4 maj 3 --export arpeggio.wav
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

### Interactive Mode

```bash
python3 wave_synth.py --interactive
```

In interactive mode, you can:
- Generate waveforms: `gen sine A4 2`
- Apply effects: `effect tremolo`, `effect lowpass:1000`
- Apply ADSR: `adsr 0.01 0.1 0.7 0.2`
- Mix waveforms: `mix 0 1` (combines stored waves 0 and 1)
- Generate chords: `chord C4 maj 2`
- Generate arpeggios: `arp A3 min7 3`
- Play preset melodies: `melody twinkle`
- Visualize: `viz` or `spectrum`
- Show info: `info`
- Export: `export output.wav`
- List stored waves: `list`
- Quit: `quit`

## Supported Note Names

All notes from C0 through C8 are supported, including sharps and flats:
- `C4` = 261.63 Hz (middle C)
- `A4` = 440.00 Hz (concert A)
- `F#5` = 739.99 Hz
- `Eb3` = 155.56 Hz

Or use raw frequencies: `440`, `261.63`, etc.

## How It Works

- **Wave generation**: Mathematical functions produce sample arrays at 44100 Hz sample rate
- **ASCII visualization**: Downsamples the waveform and maps amplitude values to Unicode box-drawing characters
- **Spectrum analysis**: Approximates a DFT across logarithmically-spaced frequency bins
- **WAV export**: Converts float samples to 16-bit PCM with proper WAV header structure
- **Effects**: Tremolo (AM), vibrato (FM via delay modulation), one-pole IIR filters, soft-clipping distortion, delay with feedback
- **ADSR**: Classic synthesizer envelope with linear ramp segments

## Example Output

A 440 Hz sine wave visualized in the terminal:

```
┌────────────────────────────────────────────────────────────────────────┐
│ +1.0                                                                   │
│ ⌐        ⌐        ⌐        ⌐        ⌐        ⌐        ⌐        ⌐       │
│ │    ⌐   │    ⌐   │    ⌐   │    ⌐   │    ⌐   │    ⌐   │    ⌐   │    ⌐  │
│ │   ⌐│   │   ⌐│   │   ⌐│   │   ⌐│   │   ⌐│   │   ⌐│   │   ⌐│   │   ⌐│  │
│ │╮  ││   │╮  ││   │╮  ││   │╮  ││   │╮  ││   │╮  ││   │╮  ││   │╮  ││  │
│⌐││  ││  ⌐││  ││  ⌐││  ││  ⌐││  ││  ⌐││  ││  ⌐││  ││  ⌐││  ││  ⌐││  ││  │
│  0.0 ─────────────────────────────────────────────────────────────── │
│   ││  ¬│   ││  ¬│   ││  ¬│   ││  ¬│   ││  ¬│   ││  ¬│   ││  ¬│   ││  ¬││
│   │╯   │   │╯   │   │╯   │   │╯   │   │╯   │   │╯   │   │╯   │   │╯   ││
│        ¬        ¬        ¬        ¬        ¬        ¬        ¬        ¬│
│ -1.0                                                                   │
└────────────────────────────────────────────────────────────────────────┘
```

## License

MIT