# 🔐 Terminal Lock Picker

**v1.3.0** — An interactive terminal-based simulation of picking pin tumbler locks. Feel the tension, find the binding pins, lift them to the shear line, and experience the satisfying click when a pin sets!

## How It Works

The simulation models a realistic pin tumbler lock:

- **Pins** sit at the bottom of the lock chamber, held down by springs
- **Tension** applied to the plug causes specific pins to **bind** against the chamber wall
- **Bound pins** can be lifted to the **shear line** — when they reach the correct height, they **set** with a satisfying click (terminal bell!)
- Once **all pins are set** while tension is maintained (≥ 20%), the lock **opens**

The challenge is finding the right amount of tension (too much and multiple pins bind; too little and nothing binds), then carefully lifting each bound pin to its shear line.

## Features

### Core Mechanics
- **Physics-based pin mechanics** — springs push pins back down, wobble adds realism, damping makes lifting feel tactile
- **Binding order** — pins bind in a random order based on manufacturing imperfections, just like real locks
- **Springback decay** — unset pins slowly fall back down under spring pressure
- **Overset protection** — non-bound pins lifted too high snap back down

### Gameplay
- **Adjustable difficulty** (Novice → Master) — tighter tolerances, stronger springs, more wobble
- **Adjustable pin count** (2–8 pins) — from simple 2-pin practice locks to challenging 8-pin models
- **Raking** — press `R` to rapidly scrub all pins (lower success rate but satisfying)
- **Pick durability** (Hard/Master) — your pick can wear and eventually break on harder locks, adding strategy
- **Hint system** — press `H` to get a hint about which pin to work on next
- **Terminal bell feedback** — hear a beep when a pin clicks into place

### Lock Profiles
- **8 named lock profiles** — preset configurations modeled after real-world lock brands:
  - `practice-2pin` — 2-pin practice lock (Novice)
  - `kwikset-entry` — 4-pin budget lock (Novice)
  - `master-lock` — 4-pin padlock (Novice)
  - `yale-standard` — 5-pin residential lock (Novice)
  - `schlage-classic` — 5-pin mid-grade lock (Easy)
  - `medeco-high` — 6-pin high-security lock (Hard)
  - `abloy-protect` — 7-pin disc detainer (Master)
  - `challenge-8pin` — 8-pin monster (Master)
- Each profile includes flavor text that appears when you start a lock

### Progression & Stats
- **Session stats** — track locks picked, total time, lifts, and rakes
- **Win streaks** — consecutive locks picked without quitting
- **Pick break counter** — tracks how many picks you've broken
- **Best time tracking** — persistent best times per pin count and difficulty, saved to `~/.lock_picker_stats.json`
- **Victory screen** — celebration animation with sparkles and time display
- **Stats screen** — press `S` from the menu to see detailed session and all-time statistics

### Interface
- **Visual pin chamber** — see each pin's height relative to the shear line in real time
- **Progress bar** — shows how many pins are set
- **Detailed pin info** — current height, shear line position, distance to set, spring tension
- **Lift amount indicator** — shows your current lift granularity on screen
- **Pick health bar** — shown on Hard/Master difficulty when durability matters (with distinct visuals for healthy/medium/critical)
- **Small terminal support** — handles terminals as small as 40×20 with a warning

### CLI & Demo
- **`--help`** and **`--version`** flags for quick reference
- **`--pins N`** and **`--difficulty N`** to start with specific settings
- **`--profile <name>`** to use a named lock profile
- **`--list-profiles`** to show all available lock profiles
- **`--demo`** mode to watch the AI auto-pick a lock (non-interactive, no curses required)
- **`--verbose`** for detailed demo output
- **`--speed`** to control demo animation speed

## How to Install

Requires Python 3.6+ with standard library (uses `curses`, included on Linux/macOS):

```bash
# No external dependencies needed!
git clone https://github.com/yourusername/daily-ideas.git
cd daily-ideas/2026-07-05-terminal-lock-picker
```

On Windows, install `windows-curses`:
```bash
pip install windows-curses
```

## How to Run

### Interactive Mode (default)

```bash
python3 lock_picker.py
```

### With Options

```bash
# Start with 4 pins on Medium difficulty
python3 lock_picker.py --pins 4 --difficulty 3

# Use a named lock profile
python3 lock_picker.py --profile yale-standard

# List all available profiles
python3 lock_picker.py --list-profiles

# Watch the AI pick a lock
python3 lock_picker.py --demo

# Demo with detailed output
python3 lock_picker.py --demo --verbose

# Demo with custom speed (faster) and profile
python3 lock_picker.py --demo --profile challenge-8pin --speed 0.01

# Show version
python3 lock_picker.py --version

# Show help
python3 lock_picker.py --help
```

## Controls

### Menu Controls

| Key | Action |
|-----|--------|
| ← → | Change number of pins (2–8) |
| ↑ ↓ | Change difficulty (Novice–Master) |
| Enter | Start picking |
| S | View statistics |
| Q | Quit |

### Picking Controls

| Key | Action |
|-----|--------|
| ← → | Select a pin |
| ↑ | Lift selected pin |
| ↓ | Release selected pin (let it fall slightly) |
| A | Increase plug tension |
| Z | Decrease plug tension |
| S | Increase lift amount per press |
| X | Decrease lift amount per press |
| R | Rake (scrub all pins randomly) |
| H | Show a hint (highlights the best pin to work on) |
| N | Start a new lock |
| Q | Return to menu |

### Victory Screen Controls

| Key | Action |
|-----|--------|
| Enter | Start a new lock |
| S | View statistics |
| M | Return to menu |
| Q | Return to menu |

### Strategy Tips

1. **Start with moderate tension** (~40-60%) — too little and no pins bind; too much and multiple pins bind making it harder
2. **Watch for BOUND pins** — only bound pins can be set
3. **Lift slowly** — reduce your lift amount (X key) for more precision on harder locks
4. **Watch the distance** — the status line shows how far you are from the shear line
5. **Pins set in order** — the binding order is random each lock. Set one, and the next one will bind
6. **Springs fight back** — unset pins slowly drift down. Keep lifting!
7. **Raking is luck-based** — works better on easier locks with fewer pins. On Hard+, raking can unset previously set pins!
8. **Use hints** — press H to highlight the best pin to work on next
9. **Watch pick health** — on Hard/Master, your pick can break. Don't rake too much!
10. **Best times are saved** — try to beat your personal record for each configuration
11. **Try lock profiles** — use `--profile` to simulate real-world lock brands with appropriate difficulty

## Testing

Run the test suite (65 tests covering lock creation, physics, picking, raking, durability, hints, CLI args, profiles, visual helpers, and regression tests):

```bash
python3 -m pytest test_lock_picker.py -v
```

Or with unittest:

```bash
python3 test_lock_picker.py
```

## What's New

### v1.3.0 — Profile & Stats Update

**New features:**
- **Lock profiles system** — 8 named presets simulating real-world lock brands (Yale, Kwikset, Schlage, Master Lock, Medeco, Abloy, etc.) with appropriate pin counts and difficulties
- **`--profile` flag** — start a game with a specific lock profile
- **`--list-profiles` flag** — list all available lock profiles from the command line
- **`--verbose` flag** — detailed output in demo mode showing lock configuration
- **Stats screen** — press S from the menu to view session and all-time statistics including best times, total picks, pick breaks, and win streaks
- **Win streak tracking** — consecutive locks picked is tracked and persisted
- **Pick break counter** — tracks how many picks have broken across sessions
- **Lift/rake counters** — session and all-time tracking of total lifts and rakes
- **`Lock.progress_pct`** — computed property for completion percentage
- **`Lock.difficulty_name`** — computed property for human-readable difficulty name
- **`Lock.reset()`** — method to reset a lock with a fresh random configuration (returns self for chaining)
- **`format_time()`** — helper to format seconds into human-readable time strings (e.g., "1m 23.4s")
- **Flavor text** — lock profiles display thematic flavor text when starting a new lock

**Improvements:**
- Demo mode now shows lock configuration details (key heights, spring tensions, binding orders)
- Demo mode tracks and displays total lifts and rakes used
- `parse_args()` now accepts an optional `args` parameter for testability
- Victory screen shows current win streak
- Victory screen offers Stats option (press S)
- Menu screen shows current win streak
- Menu screen shows profile name when a profile is active
- Lift amount now displayed on the picking screen

### v1.2.0 — Bug Fix Release

**Fixed bugs:**
- **`pins_set_count` desync** — The counter could be double-incremented when lifting an already-set pin, and could go negative after raking. Replaced the manual counter with a computed property derived from actual `is_set` flags, eliminating all desync issues.
- **`pick_health` going negative** — Pick health could drop below 0 from both lifting and raking on Hard/Master difficulty. Added `max(0.0, ...)` clamping to both code paths.
- **`check_open()` tension threshold** — Changed from `> 0.2` to `>= 0.2` so the lock opens at exactly 20% tension.
- **`get_pick_health_bar()` identical branches** — Low health now uses `·` for a distinct critical visual.
- **Demo mode progress counting** — `no_progress_count` now only increments when no pin clicks in a round.
- **Falsy CLI arg defaults** — Changed to `is not None` checks for `--pins` and `--difficulty`.
- **`result` variable undefined on error** — Added proper initialization and `is not None` check in `main()`.
- **Raking unset logic** — Moved to a separate pass, fixing a bug where `elif pin.is_set` could match pins just set in the same rake pass.

### v1.1.0 — Feature Release

- Added CLI arguments (`--help`, `--version`, `--pins`, `--difficulty`)
- Added demo mode (`--demo`, `--speed`)
- Added hint system (press H during gameplay)
- Added pick durability mechanic (Hard/Master difficulty)
- Added terminal bell feedback on pin set
- Added persistent best times saved to `~/.lock_picker_stats.json`
- Added small terminal handling
- Added raking can unset pins on Hard+ difficulty

### v1.0.0 — Initial Release

- Core lock picking simulation with pin tumbler mechanics
- Interactive curses-based UI with visual pin chamber
- Adjustable pin count (2–8) and difficulty (Novice–Master)
- Raking mechanic
- Session statistics tracking