# 🥁 Terminal Drum Machine

A feature-rich, Python-based drum machine that runs entirely in your terminal. Synthesize 8 drum sounds, build patterns with a step sequencer, add accents and flams for expression, apply swing and humanize, export to WAV or MIDI, and more — all with zero external audio dependencies beyond NumPy.

## Features

### Sound Engine
- **8 synthesized drum sounds** — kick, snare, hi-hat (closed/open), clap, tom, rimshot, cowbell — generated with pure NumPy, no samples needed
- **Accent patterns** — boost volume on any step for dynamic emphasis (1.3× default, configurable)
- **Flam hits** — add grace notes 30ms before the main hit on any drum/step for snare rushes and rhythmic texture

### Sequencer
- **8/16/32-step sequencer** — change step count on the fly with the `steps` command
- **9 built-in presets** — four-on-floor, hiphop, breakbeat, reggaeton, bossa nova, drum-and-bass, **trap**, **jazz**, **garage house**
- **Swing timing** — adjustable swing feel (0.0–0.75)
- **Humanize mode** — adds realistic timing jitter and velocity variation
- **Metronome click track** — optional quarter-note click during playback

### Pattern Operations
- **Invert, reverse, shift, copy** — full pattern manipulation toolkit
- **Random & fill generators** — create patterns with adjustable density
- **Solo/unsolo** — isolate any drum or unmute all
- **Undo support** — undo up to 50 pattern changes (including accents, flams, and step count changes)

### Display
- **ASCII grid** — visual step sequencer with `█` for hits, `·` for rests, `^` for accents, `~` for flams
- **Pattern info** — `info` command shows BPM, step count, swing, density stats, accent/flam counts

### Import/Export
- **Save/Load JSON** — persist and restore patterns with BPM, swing, humanize, mute state, accents, and flams
- **WAV export** — render patterns to `.wav` audio files
- **MIDI export** — export patterns as standard MIDI format 0 files (GM percussion channel 10)

### CLI Interface
- `--export`, `--export-midi`, `--save`, `--list-presets`, `--version`, and more

## Installation

```bash
# Requires Python 3.10+ and NumPy
pip install numpy

# Clone or download this repository
cd 2026-06-17-terminal-drum-machine
```

## Quick Start

```bash
# Interactive mode — the main way to use it
python3 drum_machine.py

# Or use CLI flags for quick actions
python3 drum_machine.py --preset hiphop --bpm 90 --play
python3 drum_machine.py --preset trap --export trap_beat.wav
python3 drum_machine.py --list-presets
```

## Interactive Commands

Once inside interactive mode, use these commands:

| Command | Description |
|---|---|
| `<drum> <step>` | Toggle a step (e.g. `kick 1`, `snare 5`) |
| `preset <name>` | Load a preset pattern |
| `presets` | List available presets |
| `bpm <n>` | Set BPM (30–300) |
| `steps <8\|16\|32>` | Change step count |
| `swing <0-75>` | Set swing percentage |
| `volume <drum> <0-200>` | Set drum volume percentage |
| `mute <drum>` | Toggle mute on a drum |
| `solo <drum>` | Solo a drum (mute all others) |
| `unsolo` | Unmute all drums |
| `shift <drum> <n>` | Rotate pattern by n steps |
| `invert <drum>` | Invert pattern (on↔off) |
| `reverse <drum>` | Reverse pattern order |
| `copy <src> <dst>` | Copy pattern between drums |
| `fill [start_step]` | Generate fill from step onward |
| `accent <step>` | Toggle accent on a step (1-indexed) |
| `clearaccents` | Clear all accents |
| `flam <drum> <step>` | Toggle flam on a drum/step |
| `clearflams` | Clear all flams |
| `humanize [on\|off]` | Toggle humanize (timing/velocity) |
| `metronome` | Toggle click track |
| `clear` | Clear pattern |
| `random [density]` | Random pattern (0.0–1.0 density) |
| `density` | Show pattern density per drum |
| `info` | Show pattern stats & details |
| `undo` | Undo last change |
| `save <file>` | Save pattern to JSON |
| `load <file>` | Load pattern from JSON |
| `play` | Play pattern (audio) |
| `export <file>` | Export to WAV |
| `exportmidi <file>` | Export to MIDI |
| `grid` | Redraw the grid |
| `quit` | Exit |

## Drum Aliases

Use short names for drums in commands:

| Alias | Drum |
|---|---|
| `k` | Kick |
| `s` | Snare |
| `hhc` | HH Closed |
| `hho` | HH Open |
| `c` | Clap |
| `t` | Tom |
| `r` | Rim |
| `cb` | Cowbell |

## Presets

| Name | Style | Description |
|---|---|---|
| `four-on-floor` | House/Pop | Classic four-on-the-floor kick pattern |
| `hiphop` | Hip-Hop | Boom-bap hip-hop beat |
| `breakbeat` | Breakbeat | Broken beat pattern |
| `reggaeton` | Reggaeton | Dembow rhythm |
| `bossa-nova` | Bossa Nova | Brazilian bossa nova |
| `drum-and-bass` | DnB | Fast DnB pattern |
| `trap` | Trap | Trap with rapid hi-hats and 808 kick |
| `jazz` | Jazz | Swing jazz with ride and rim |
| `garage` | Garage House | 2-step garage house |

## Accent & Flam Details

### Accents
Accents boost the volume of all hits on a given step by a multiplier (default 1.3×). Use `accent <step>` to toggle. Accented steps show `^` in the grid.

```
🥁 > accent 1
Accent on step 1: ON (x1.3)
🥁 > accent 1
Accent on step 1: OFF
```

### Flams
Flams add a quiet grace note 30ms before the main hit on a specific drum/step. The grace note plays at 60% volume. Use `flam <drum> <step>` to toggle. Flammed steps show `~` in the grid.

```
🥁 > flam snare 5
Flam on Snare step 5: ON
🥁 > flam k 1
Flam on Kick step 1: ON
```

## JSON Format

Saved patterns include accents and flams:

```json
{
  "bpm": 120,
  "steps": 16,
  "swing": 0.0,
  "pattern": {"Kick": [1,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0], ...},
  "accents": [1.3, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, ...],
  "flams": {"Kick": [0,0,0,0,...], "Snare": [0,0,0,0,1,...], ...},
  "volumes": {"Kick": 1.0, ...},
  "muted": {"Kick": false, ...}
}
```

Old JSON files without `accents` or `flams` keys load without errors — they default to no accents and no flams.

## Running Tests

```bash
python3 -m pytest test_drum_machine.py -v
```

The test suite includes 205 tests covering all features: sound synthesis, pattern manipulation, presets, accents, flams, step changes, undo, save/load, MIDI export, and more.

## License

MIT