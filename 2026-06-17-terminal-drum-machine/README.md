# 🥁 Terminal Drum Machine

A step-sequencer drum machine that runs entirely in your terminal. Synthesizes 8 different drum sounds from scratch using numpy waveforms — no external audio samples or libraries needed. Display animated sequencer grids, load preset beats, generate random patterns, and export to WAV.

## Features

- **8 synthesized drum sounds** — Kick, Snare, Closed Hi-Hat, Open Hi-Hat, Clap, Tom, Rimshot, Cowbell
- **All-digital synthesis** — Sounds generated from sine waves, noise, and pitch envelopes (no samples)
- **16-step sequencer** — Visual grid display with step highlighting
- **6 built-in presets** — Four-on-the-floor, Hip-hop, Breakbeat, Reggaeton, Bossa Nova, Drum & Bass
- **Random pattern generator** — Create unexpected beats with one command
- **WAV export** — Render loops to 44.1kHz 16-bit WAV files
- **Interactive mode** — Toggle steps, change BPM, load presets in real-time
- **Configurable BPM** — 30–300 BPM range

## Installation

Requires Python 3.8+ and numpy:

```bash
# Install numpy
pip install numpy

# Or on Debian/Ubuntu:
sudo apt-get install python3-numpy
```

No other dependencies needed!

## How to Run

### Interactive Mode (default)

```bash
python3 drum_machine.py
```

Opens an interactive session where you can toggle steps, load presets, change BPM, and more.

### Command-Line Mode

```bash
# Load a preset and show the grid
python3 drum_machine.py --preset hiphop

# Export a preset to WAV
python3 drum_machine.py --preset four-on-floor --export beat.wav

# Set BPM and export
python3 drum_machine.py --bpm 140 --preset dnb --export dnb_beat.wav

# Generate a random beat and export it
python3 drum_machine.py --random --export random_beat.wav

# List available presets
python3 drum_machine.py --list-presets

# Force interactive mode
python3 drum_machine.py -i
```

### All Options

| Flag | Description |
|------|-------------|
| `--bpm N` | Set tempo (default: 120) |
| `--preset NAME` | Load a preset pattern |
| `--export FILE.wav` | Export to WAV file |
| `--loops N` | Number of loops for export (default: 2) |
| `--random` | Generate a random pattern |
| `--play` | Attempt audio playback |
| `--list-presets` | Show available presets |
| `-i, --interactive` | Start interactive mode |

## Interactive Commands

Once in interactive mode, type commands at the `🥁 >` prompt:

| Command | Description |
|---------|-------------|
| `kick 1` | Toggle Kick on step 1 |
| `snare 5` | Toggle Snare on step 5 |
| `hhc 3` | Toggle Closed Hi-Hat on step 3 (shorthand) |
| `preset hiphop` | Load a preset |
| `presets` | List available presets |
| `bpm 140` | Change tempo |
| `clear` | Clear all steps |
| `random` | Generate random pattern |
| `export beat.wav` | Export to WAV |
| `play` | Play current pattern |
| `grid` | Redraw the grid |
| `quit` | Exit |

Shorthand aliases: `k`=Kick, `s`=Snare, `hhc`=HH-Closed, `hho`=HH-Open, `c`=Clap, `t`=Tom, `r`=Rim, `cb`=Cowbell

## Available Presets

| Preset | Description |
|--------|-------------|
| `four-on-floor` | Classic 4/4 dance beat — kick on every quarter note |
| `hiphop` | Boom-bap hip-hop groove with syncopated kick |
| `breakbeat` | Amen-inspired breakbeat pattern |
| `reggaeton` | Dembow rhythm with rimshot accent |
| `bossa-nova` | Brazilian bossa nova feel with cowbell |
| `dnb` | Fast drum and bass with open hi-hat tail |

## How It Works

### Sound Synthesis

Each drum sound is synthesized from first principles:

- **Kick** — Pitch-swept sine wave (150Hz→40Hz exponential sweep) with fast exponential decay and a transient click
- **Snare** — Layered sine tones (200Hz + 350Hz) mixed with white noise, shaped by a fast decay envelope and smoothed with a moving-average bandpass
- **Closed Hi-Hat** — High-pass filtered noise burst with very fast decay (50/s)
- **Open Hi-Hat** — Similar to closed but with slower decay (12/s)
- **Clap** — Layered noise bursts with micro-offsets for the layered-hand effect
- **Tom** — Mid-frequency swept sine (200Hz→100Hz) with medium decay
- **Rimshot** — Short 800Hz tone mixed with noise, extremely fast decay
- **Cowbell** — Two detuned square waves (560Hz + 845Hz) for that classic metallic timbre

All sounds are mixed per-step with automatic peak normalization and exported as standard 44.1kHz 16-bit mono WAV.

### Step Duration

At BPM=120, each 16th-note step is 125ms (60/120/4 seconds), giving a full 16-step bar of exactly 2 seconds.

## Example Output

```
───────────────┼───────────────────────────────────────────────┼─
Drum Machine  │  1┼ 2┼ 3┼ 4┼ 5┼ 6┼ 7┼ 8┼ 9┼10┼11┼12┼13┼14┼15┼16 │
───────────────┼───────────────────────────────────────────────┼─
         Kick │ ● · · · ● · · · ● · · · ● · · · │
        Snare │ · · · · ● · · · · · · · ● · · · │
         HH-C │ ● · ● · ● · ● · ● · ● · ● · ● · │
         HH-O │ · · · · · · · · · · · · · · · · │
         Clap │ · · · · · · · · · · · · · · · · │
          Tom │ · · · · · · · · · · · · · · · · │
          Rim │ · · · · · · · · · · · · · · · · │
          Cow │ · · · · · · · · · · · · · · · · │
───────────────┼───────────────────────────────────────────────┼─
  BPM: 120  Steps: 16
```

## License

MIT