# 🥁 Terminal Drum Machine

A feature-rich, Python-based drum machine that runs entirely in your terminal. Synthesize 8 drum sounds, build patterns with a step sequencer, apply swing and humanize, export to WAV or MIDI, and more — all with zero external audio dependencies beyond NumPy.

## Features

- **8 synthesized drum sounds** — kick, snare, hi-hat (closed/open), clap, tom, rimshot, cowbell — generated with pure NumPy, no samples needed
- **16-step sequencer** with support for 8 or 32 steps as well
- **Interactive mode** — real-time pattern editing with a terminal UI
- **6 built-in presets** — four-on-floor, hiphop, breakbeat, reggaeton, bossa nova, drum-and-bass
- **Swing timing** — adjustable swing feel (0.0–0.75)
- **Humanize mode** — adds realistic timing jitter and velocity variation
- **Metronome click track** — optional quarter-note click during playback
- **Pattern operations** — invert, reverse, shift, copy, random, fill generator, solo/unsolo
- **Undo support** — undo up to 50 pattern changes
- **Save/Load JSON** — persist and restore patterns with BPM, swing, humanize, and mute state
- **WAV export** — render patterns to `.wav` audio files
- **MIDI export** — export patterns as standard MIDI format 0 files (GM percussion channel 10)
- **CLI interface** — `--export`, `--export-midi`, `--save`, `--list-presets`, `--version`, and more

## Installation

```bash
# Requires Python 3.10+ and NumPy
pip install numpy

# Clone or download this repository
cd 2026-06-17-terminal-drum-machine
```

## Quick Start

```bash
# Launch interactive mode (default)
python3 drum_machine.py

# Play with a preset and humanize
python3 drum_machine.py --preset hiphop --humanize

# Export to WAV
python3 drum_machine.py --preset four-on-floor --export output.wav

# Export to MIDI
python3 drum_machine.py --preset dnb --export-midi output.mid

# Save a pattern to JSON
python3 drum_machine.py --preset bossanova --save pattern.json
```

## Interactive Commands

| Command | Description |
|---------|-------------|
| `toggle <drum> <step>` | Toggle a step on/off (e.g. `toggle kick 0`) |
| `clear <drum>` | Clear all steps for a drum |
| `preset <name>` | Load a preset pattern |
| `presets` | List available presets |
| `bpm <value>` | Set tempo (30–300) |
| `swing <value>` | Set swing (0.0–0.75) |
| `humanize [on\|off]` | Toggle humanize mode |
| `metronome` | Toggle metronome click |
| `invert <drum>` | Invert all steps (ON↔OFF) |
| `reverse <drum>` | Reverse step order |
| `shift <drum> <steps>` | Shift pattern left (neg) or right (pos) |
| `solo <drum>` | Mute all drums except one |
| `unsolo` | Unmute all drums |
| `mute <drum>` | Toggle mute on a drum |
| `volume <drum> <val>` | Set drum volume (0.0–2.0) |
| `random [density]` | Randomize pattern (0.0–1.0 density) |
| `fill [step] [density]` | Generate building fill |
| `copy <src> <dst>` | Copy pattern between drums |
| `save <file.json>` | Save pattern to JSON |
| `load <file.json>` | Load pattern from JSON |
| `export <file.wav>` | Export to WAV audio |
| `exportmidi <file.mid>` | Export to MIDI |
| `undo` | Undo last pattern change |
| `play` | Play the pattern |
| `grid` | Display current pattern |
| `quit` / `exit` / `q` | Exit |

> **Note:** Filenames with spaces are supported in `save`, `load`, `export`, and `exportmidi` commands.

## Drum Aliases

| Full Name | Short Alias |
|-----------|-------------|
| kick | k |
| snare | s |
| hihat_closed | hc |
| hihat_open | ho |
| clap | c |
| tom | t |
| rim | r |
| cowbell | cb |

## Running Tests

```bash
python3 -m pytest test_drum_machine.py -v
```

168 tests covering all features, edge cases, and bug regressions.

## Bug Fixes (v1.4.0)

This release fixes 5 bugs found in v1.3.0:

1. **Hi-hat synthesis crash with very short durations** — `synth_hihat_closed` and `synth_hihat_open` could crash with `ValueError` when `duration` was shorter than the convolution kernel. Now the number of samples is automatically clamped to be at least as long as the kernel.

2. **JSON load accepted out-of-range BPM** — Loading a JSON file with `bpm` outside 30–300 (e.g., 0, -50, or 999) would silently corrupt the machine state, leading to crashes in rendering (division by zero) or MIDI export. BPM values from JSON are now clamped to the 30–300 range and coerced to `int`.

3. **JSON load accepted out-of-range swing** — Loading a JSON file with `swing` outside 0.0–0.75 (e.g., 1.5 or -0.5) would cause negative step durations, producing invalid audio. Swing values from JSON are now clamped to 0.0–0.75.

4. **MIDI export crash with invalid BPM** — `render_to_midi` would crash with `OverflowError` if BPM was 0 or negative (from `tempo.to_bytes(3, 'big')`). Now raises `ValueError` with a clear message instead.

5. **Interactive mode filenames with spaces** — Commands like `load my pattern.json` would only capture `my` as the filename. All file-related commands (`save`, `load`, `export`, `exportmidi`) now correctly join remaining arguments to support filenames with spaces.

Additional defensive improvements:
- `step_duration()` now returns a minimum of 1ms and gracefully handles BPM ≤ 0 (falls back to 120 BPM timing) instead of crashing with `ZeroDivisionError`
- All synth functions have zero-duration guards that return a tiny silent array

## Changelog

### v1.4.0 (2026-06-17)
- Fixed hi-hat crash with very short durations
- Fixed JSON load accepting out-of-range BPM and swing values
- Fixed MIDI export crash with invalid BPM
- Fixed interactive mode filename parsing for paths with spaces
- Added defensive guards in `step_duration()` for BPM ≤ 0 and extreme swing
- Added 17 regression tests (168 total)

### v1.3.0 (2026-06-17)
- Added pattern invert, reverse, solo/unsolo, fill generator
- Added humanize mode, metronome click track
- Added undo support (50 levels)
- Added MIDI export
- Added --help and --version flags

### v1.0.0
- Initial release with 8 drum sounds, 16-step sequencer, WAV export, presets, swing, save/load