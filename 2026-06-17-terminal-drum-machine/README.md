# 🥁 Terminal Drum Machine

A step-sequencer drum machine that runs entirely in your terminal. Synthesizes 8 different drum sounds from scratch using numpy waveforms — no external audio samples or libraries needed. Display animated sequencer grids, load preset beats, generate random patterns, add swing or humanize feel, control per-drum volume, mute/solo drums, undo changes, save/load patterns as JSON, and export to WAV or MIDI.

## Features

### Sound Engine
- **8 synthesized drum sounds** — Kick, Snare, Closed Hi-Hat, Open Hi-Hat, Clap, Tom, Rimshot, Cowbell
- **All-digital synthesis** — Sounds generated from sine waves, noise, and pitch envelopes (no samples)
- **Per-drum volume control** — Set each drum's volume from 0% to 200%
- **Mute/solo** — Toggle individual drums on/off, or solo a drum (mute all others)

### Sequencer
- **16-step sequencer** (also supports 8 and 32 steps via `--steps`)
- **Swing/groove** — Add shuffle feel from 0% (straight) to 75% (heavy swing). Swing redistributes timing between even/odd step pairs while preserving total loop duration.
- **Humanize mode** — Add organic timing jitter (±8ms) and velocity variation (±12%) for a more natural, less robotic feel. Toggle on/off in interactive mode or via `--humanize` CLI flag.
- **Metronome click track** — Optional quarter-note click for keeping time during playback
- **Pattern shift** — Rotate any drum's pattern left or right
- **Pattern invert** — Flip all steps on/off for a drum (empty becomes full, full becomes empty)
- **Pattern reverse** — Reverse the order of steps in a drum's pattern
- **Copy patterns** — Copy one drum's pattern to another drum
- **Fill generator** — Generate a random fill from a given step onward, with density that builds toward the end
- **Undo support** — Undo the last 50 pattern changes (toggle, clear, preset load, shift, invert, reverse, solo, mute, random, fill)

### Presets & Patterns
- **6 built-in presets** — Four-on-the-floor, Hip-hop, Breakbeat, Reggaeton, Bossa Nova, Drum & Bass
- **Random pattern generator** — Create beats with configurable density
- **Save/load patterns as JSON** — Full round-trip persistence including BPM, swing, volumes, mute state, and humanize settings
- **Adaptive step counts** — Presets automatically adapt to 8/16/32 step sequencers

### Export & Playback
- **WAV export** — Render loops to 44.1kHz 16-bit mono WAV files
- **MIDI export** — Export patterns as standard MIDI files (format 0) with GM percussion note mappings on channel 10
- **Audio playback** — Attempts system audio via aplay/paplay/play/afplay
- **Configurable loop count** — Export 1 or more loops per WAV file

### Interactive Mode
- **Full REPL** — Toggle steps, load presets, change BPM, set swing, adjust volumes, mute/solo drums, and more
- **Shorthand aliases** — `k`=Kick, `s`=Snare, `hhc`=HH-Closed, `hho`=HH-Open, `c`=Clap, `t`=Tom, `r`=Rim, `cb`=Cowbell

## Installation

Requires Python 3.8+ and numpy:

```bash
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

Opens an interactive session with full command access.

### Command-Line Mode

```bash
# Load a preset and show the grid
python3 drum_machine.py --preset hiphop

# Export a preset to WAV
python3 drum_machine.py --preset four-on-floor --export beat.wav

# Set BPM and export
python3 drum_machine.py --bpm 140 --preset dnb --export dnb_beat.wav

# Generate a random beat with specific density and export
python3 drum_machine.py --random --density 0.4 --export random_beat.wav

# Add swing feel
python3 drum_machine.py --preset breakbeat --swing 30 --export swing_beat.wav

# Add humanize for organic feel
python3 drum_machine.py --preset hiphop --humanize --export live_beat.wav

# Use a 32-step sequencer
python3 drum_machine.py --steps 32 --random --export long_pattern.wav

# Save a pattern to JSON
python3 drum_machine.py --preset bossa-nova --save pattern.json

# Load and re-export a saved pattern
python3 drum_machine.py --load pattern.json --export loaded.wav

# Export as MIDI
python3 drum_machine.py --preset four-on-floor --export-midi beat.mid

# List available presets
python3 drum_machine.py --list-presets

# Show version
python3 drum_machine.py --version
```

### All CLI Options

| Flag | Description |
|------|-------------|
| `--version` | Show version number |
| `--bpm N` | Set tempo (30–300, default: 120) |
| `--steps {8,16,32}` | Number of sequencer steps (default: 16) |
| `--preset NAME` | Load a preset pattern |
| `--export FILE.wav` | Export to WAV file |
| `--export-midi FILE.mid` | Export as MIDI file |
| `--loops N` | Number of loops for WAV export (default: 2) |
| `--random` | Generate a random pattern |
| `--density 0.0-1.0` | Fill density for random (default: 0.3) |
| `--swing 0-75` | Swing percentage (default: 0 = straight) |
| `--humanize` | Add timing jitter and velocity variation |
| `--play` | Attempt audio playback |
| `--list-presets` | Show available presets |
| `--save FILE.json` | Save pattern to JSON |
| `--load FILE.json` | Load pattern from JSON |
| `-i, --interactive` | Start interactive mode |

## Interactive Commands

Once in interactive mode, type commands at the `🥁 >` prompt:

| Command | Description |
|---------|-------------|
| `<drum> <step>` | Toggle a step (e.g. `kick 1`, `snare 5`) |
| `preset <name>` | Load a preset |
| `presets` | List available presets |
| `bpm <n>` | Change tempo (30–300; invalid values are rejected) |
| `swing <0-75>` | Set swing percentage |
| `volume <drum> <0-200>` | Set drum volume (percentage) |
| `mute <drum>` | Toggle mute on a drum |
| `solo <drum>` | Solo a drum (mute all others) |
| `unsolo` | Unmute all drums |
| `shift <drum> <n>` | Rotate pattern by n steps (+right/-left) |
| `invert <drum>` | Invert pattern (ON↔OFF) |
| `reverse <drum>` | Reverse pattern order |
| `copy <src> <dst>` | Copy pattern between drums |
| `fill [step] [density]` | Generate random fill from step onward |
| `humanize [on\|off]` | Toggle humanize mode |
| `metronome` | Toggle click track on quarter notes |
| `clear` | Clear all steps |
| `random [density]` | Generate random pattern (0.05–0.95) |
| `density` | Show pattern density per drum |
| `undo` | Undo last pattern change |
| `save <file>` | Save pattern to JSON |
| `load <file>` | Load pattern from JSON |
| `play` | Play current pattern |
| `export <file>` | Export to WAV |
| `exportmidi <file>` | Export as MIDI |
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
- **Metronome** — Short 1000Hz sine beep with very fast decay, for click track

All sounds are mixed per-step with automatic peak normalization and exported as standard 44.1kHz 16-bit mono WAV.

### Humanize Mode

When humanize is enabled, each note gets:
- **Timing jitter**: ±8ms random offset (configurable via `humanize_timing`)
- **Velocity variation**: ±12% random amplitude change (configurable via `humanize_velocity`)

This creates subtle, natural-sounding variations that make programmed beats feel less robotic.

### Swing Timing

At BPM=120, each 16th-note step is 125ms (60/120/4 seconds), giving a full 16-step bar of exactly 2 seconds.

With swing enabled, even-indexed steps (0, 2, 4...) are lengthened and odd-indexed steps (1, 3, 5...) are shortened. Each pair of steps still sums to `2 × base_duration`, so the total loop duration is always preserved regardless of swing setting.

### MIDI Export

MIDI export maps each drum to a General MIDI percussion note on channel 10:
- Kick → 36 (Bass Drum 1)
- Snare → 38 (Acoustic Snare)
- HH-Closed → 42 (Closed Hi-Hat)
- HH-Open → 46 (Open Hi-Hat)
- Clap → 39 (Hand Clap)
- Tom → 47 (Low-Mid Tom)
- Rim → 37 (Side Stick)
- Cowbell → 56 (Cowbell)

Velocity is derived from per-drum volume (0–200% maps to 1–127).

### JSON Pattern Format

Saved patterns include BPM, steps, swing, humanize settings, pattern data, volumes, and mute state:

```json
{
  "version": "1.3.0",
  "bpm": 140,
  "steps": 16,
  "swing": 0.3,
  "humanize": true,
  "humanize_timing": 0.008,
  "humanize_velocity": 0.12,
  "pattern": { "Kick": [1,0,0,0,...], ... },
  "volumes": { "Kick": 1.0, "Snare": 0.8, ... },
  "muted": { "Cowbell": true, ... }
}
```

## Example Output

```
──────────────┼───────────────────────────────────────────────┼─
Drum Machine  │  1┼ 2┼ 3┼ 4┼ 5┼ 6┼ 7┼ 8┼ 9┼10┼11┼12┼13┼14┼15┼16 │
──────────────┼───────────────────────────────────────────────┼─
         Kick  │ ● · · · ● · · · ● · · · ● · · · │
        Snare  │ · · · · ● · · · · · · · ● · · · │
         HH-C  │ ● · ● · ● · ● · ● · ● · ● · ● · │
         HH-O  │ · · · · · · · · · · · · · · · · │
         Clap  │ · · · · · · · · · · · · · · · · │
          Tom  │ · · · · · · · · · · · · · · · · │
          Rim  │ · · · · · · · · · · · · · · · · │
          Cow  │ · · · · · · · · · · · · · · · · │
──────────────┼───────────────────────────────────────────────┼─
  BPM: 120  Steps: 16  Humanize: ON
```

## Running Tests

```bash
python3 -m pytest test_drum_machine.py -v
```

151 tests covering sound synthesis, pattern manipulation, presets, volume/mute, solo, swing timing, invert/reverse, fill generation, humanize, metronome, undo, WAV export, MIDI export, JSON save/load (including type validation), display, and regression tests for fixed bugs.

## Changelog

### v1.3.0 — New Features & Enhancements
- **Added pattern invert**: `invert <drum>` flips all steps ON↔OFF for a drum
- **Added pattern reverse**: `reverse <drum>` reverses the step order
- **Added solo/unsolo**: `solo <drum>` mutes all drums except one; `unsolo` unmutes all
- **Added fill generator**: `fill [start_step] [density]` creates a building fill toward the end of the pattern
- **Added humanize mode**: `--humanize` flag and `humanize [on|off]` command add timing jitter (±8ms) and velocity variation (±12%) for organic feel. Settings persist in JSON saves.
- **Added metronome click track**: `metronome` command toggles quarter-note clicks during playback
- **Added undo support**: `undo` command reverts the last pattern change (up to 50 levels). Tracks toggle, clear, preset load, shift, invert, reverse, solo, mute, random, and fill operations.
- **Added MIDI export**: `--export-midi FILE.mid` and `exportmidi <file>` command export patterns as standard MIDI files with GM percussion note mappings
- **Added `--export-midi` CLI flag** for MIDI file export
- **Added metronome click synthesis**: `synth_metronome_click()` produces a short 1000Hz beep
- **Improved code comments** throughout all synthesis functions and core methods
- **Improved interactive help display**: expanded to show all new commands

### v1.2.0 — Bug Fixes
- **Fixed swing timing bug**: Step 0 was not receiving swing adjustment, causing total loop duration to shrink when swing was applied
- **Fixed incorrect comment**: The `step_duration` docstring incorrectly described even-indexed steps
- **Fixed JSON load type safety**: `load_pattern_json` now validates that `bpm`, `swing`, `steps`, `volumes`, and `muted` values are the correct numeric types before assignment
- **Fixed JSON load pattern validation**: Pattern values that are not lists now default to all-False instead of causing a crash
- **Fixed interactive BPM validation**: The `bpm` command now rejects invalid values (outside 30–300 range) instead of printing an error but still clamping
- **Added `render_to_wav` loops validation**: `render_to_wav` now raises `ValueError` if `loops < 1`
- Added 8 regression tests covering all fixed bugs

## License

MIT