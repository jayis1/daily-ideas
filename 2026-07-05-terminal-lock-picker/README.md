# 🔐 Terminal Lock Picker

An interactive terminal-based simulation of picking pin tumbler locks. Feel the tension, find the binding pins, lift them to the shear line, and experience the satisfying click when a pin sets!

## How It Works

The simulation models a realistic pin tumbler lock:

- **Pins** sit at the bottom of the lock chamber, held down by springs
- **Tension** applied to the plug causes specific pins to **bind** against the chamber wall
- **Bound pins** can be lifted to the **shear line** — when they reach the correct height, they **set** with a satisfying click (terminal bell!)
- Once **all pins are set** while tension is maintained (≥ 20%), the lock **opens**
- After a pin sets, the next binding pin appears automatically (binding updates each frame)

The challenge is finding the right amount of tension (too much and multiple pins bind; too little and nothing binds), then carefully lifting each bound pin to its shear line.

## Features

### Core Mechanics
- **Physics-based pin mechanics** — springs push pins back down, wobble adds realism, damping makes lifting feel tactile
- **Binding order** — pins bind in a random order based on manufacturing imperfections, just like real locks
- **Springback decay** — unset pins slowly fall back down under spring pressure
- **Overset protection** — non-bound pins lifted too high snap back down
- **Automatic binding updates** — binding recalculates each frame after pins are set, so the next binding pin appears naturally

### Gameplay
- **Adjustable difficulty** (Novice → Master) — tighter tolerances, stronger springs, more wobble
- **Adjustable pin count** (2–8 pins) — from simple 2-pin practice locks to challenging 8-pin models
- **Raking** — press `R` to rapidly scrub all pins (lower success rate but satisfying)
- **Pick durability** (Hard/Master) — your pick can wear and eventually break on harder locks, adding strategy. Both lifting and raking wear the pick at the same difficulty threshold (Hard and above)
- **Hint system** — press `H` to get a hint about which pin to work on next
- **Terminal bell feedback** — hear a beep when a pin clicks into place

### Progression & Stats
- **Session stats** — track locks picked, total time, current streak
- **Best time tracking** — persistent best times per pin count and difficulty, saved to `~/.lock_picker_stats.json`
- **Victory screen** — celebration animation with sparkles and frozen completion time
- **Lock profiles** — named lock configurations (Yale Standard, Kwikset Entry, Medeco High-Security, etc.)

### Interface
- **Visual pin chamber** — see each pin's height relative to the shear line in real time
- **Progress bar** — shows how many pins are set
- **Detailed pin info** — current height, shear line position, distance to set, spring tension
- **Pick health bar** — shown on Hard/Master difficulty when durability matters, with distinct visuals for healthy (▓), medium (▒), and critical (!) levels
- **Small terminal support** — handles terminals as small as 40×20 with a warning

### CLI & Demo
- **`--help`** and **`--version`** flags for quick reference
- **`--pins N`** and **`--difficulty N`** to start with specific settings
- **`--demo`** mode to watch the AI auto-pick a lock (non-interactive, no curses required)
- **`--speed`** to control demo animation speed
- **`--profile`** to use a named lock configuration (e.g., `--profile yale-standard`)
- **`--list-profiles`** to see all available profiles
- **`--verbose`** for detailed demo output

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
python3 lock_picker.py --profile medeco-high

# Watch the AI pick a lock
python3 lock_picker.py --demo

# Demo with custom speed (faster)
python3 lock_picker.py --demo --pins 3 --difficulty 1 --speed 0.01

# List available lock profiles
python3 lock_picker.py --list-profiles

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

### Strategy Tips

1. **Start with moderate tension** (~40-60%) — too little and no pins bind; too much and multiple pins bind making it harder
2. **Watch for BOUND pins** — only bound pins can be set
3. **Lift slowly** — reduce your lift amount (X key) for more precision on harder locks
4. **Watch the distance** — the status line shows how far you are from the shear line
5. **Pins set in order** — the binding order is random each lock. Set one, and the next one will bind
6. **Springs fight back** — unset pins slowly drift down. Keep lifting!
7. **Raking is luck-based** — works better on easier locks with fewer pins. On Hard+, raking can unset previously set pins!
8. **Use hints** — press H to highlight the best pin to work on next
9. **Watch pick health** — on Hard/Master, your pick can break. Both raking and lifting wear the pick. Don't rake too much!
10. **Best times are saved** — try to beat your personal record for each configuration

## Testing

Run the test suite (71 tests covering lock creation, physics, picking, raking, durability, hints, profiles, visual helpers, CLI args, and regression tests for fixed bugs):

```bash
python3 -m pytest test_lock_picker.py -v
```

Or with unittest:

```bash
python3 test_lock_picker.py
```

## Changelog

### v1.3.1 — Bug Fix Release

**Fixed bugs:**
- **Raking pick wear threshold inconsistency** — `rack()` wore the pick at difficulty ≥ 3 (Medium+) while `lift_pin()` only wore at difficulty ≥ 4 (Hard+). Now both consistently wear only at Hard and Master difficulty. Updated the existing `test_rake_wears_pick` test to use difficulty 4 (Hard).
- **`get_pick_health_bar()` critical health bar was indistinguishable from zero** — When health dropped below 20%, both the filled and unfilled portions used `·`, making it impossible to tell remaining health from a completely broken pick. Critical health now uses `!` for remaining health and `·` for lost health.
- **`rack()` didn't check for broken pick** — Unlike `lift_pin()` which returns `False` when the pick is broken, `rack()` would still modify pin heights even with `pick_health ≤ 0`. Now `rack()` returns 0 and doesn't modify pins when the pick is broken.
- **Demo mode could infinite-loop with broken pick** — On Hard/Master difficulty, the pick can break during the demo, causing `lift_pin()` to always return `False`. The demo would spin for all 800 rounds doing nothing. Now the demo detects a broken pick and exits early with a warning message.
- **Binding didn't update after pins were set in game** — After setting a pin, the next binding pin wouldn't appear until the player pressed A/Z to change tension. The game now re-applies tension each frame (matching the demo's behavior), so binding updates automatically after each pin is set.
- **Victory screen time kept ticking** — The elapsed time on the victory screen was recalculated from `time.time() - start_time` every frame, causing the displayed time to keep increasing. Now the completion time is frozen when the lock opens.
- **`main()` error handling** — If `curses.wrapper` raised a non-KeyboardInterrupt exception (e.g., terminal resize during play), `result` would be `None` and the message would misleadingly say "interrupted". Added a broader `except Exception` handler and clearer messaging.

**Added tests:**
- `test_raking_on_medium_no_pick_wear` — verifies Medium raking doesn't wear the pick
- `test_raking_on_hard_wears_pick` — verifies Hard raking does wear the pick
- `test_rake_with_broken_pick_returns_zero` — verifies broken pick raking returns 0 clicks and doesn't modify pins
- `test_demo_broken_pick_exits` — verifies demo can detect broken pick state
- `test_pick_health_bar_zero_distinct_from_low` — verifies 0% and 10% health bars look different
- `test_binding_updates_after_pin_set` — verifies binding recalculates when tension is re-applied after setting a pin

**Total test count: 71** (up from 65)

### v1.3.0 — Feature Release (Profiles, Stats Screen, Streaks)

- Added lock profiles system (Yale Standard, Kwikset Entry, Schlage Classic, Master Lock, Medeco High-Security, Abloy Protect, 2-Pin Practice, 8-Pin Challenge)
- Added `--profile` CLI flag to use named lock configurations
- Added `--list-profiles` flag to show available profiles
- Added `--verbose` flag for detailed demo output
- Added stats screen (press S on victory screen)
- Added session tracking: current streak, total lifts, total rakes, picks broken
- Added `format_time()` helper for better time display
- Added `Lock.reset()` method and `Lock.difficulty_name` / `Lock.progress_pct` properties
- Expanded test suite from 41 to 65 tests

### v1.2.0 — Bug Fix Release

- Fixed `pins_set_count` desync
- Fixed `pick_health` going negative
- Fixed `check_open()` tension threshold (≥0.2 instead of >0.2)
- Fixed `get_pick_health_bar()` identical branches
- Fixed `get_pin_visual()` unreachable code
- Fixed demo mode progress counting
- Fixed falsy CLI arg defaults
- Fixed `result` variable undefined on error
- Fixed raking unset logic

### v1.1.0 — Feature Release

- Added CLI arguments (`--help`, `--version`, `--pins`, `--difficulty`)
- Added demo mode (`--demo`, `--speed`)
- Added hint system (press H during gameplay)
- Added pick durability mechanic (Hard/Master difficulty)
- Added terminal bell feedback on pin set
- Added persistent best times saved to `~/.lock_picker_stats.json`
- Added small terminal handling
- Added raking can unset pins on Hard+ difficulty
- Expanded test suite from 6 to 32 tests

### v1.0.0 — Initial Release

- Core lock picking simulation with pin tumbler mechanics
- Interactive curses-based UI with visual pin chamber
- Adjustable pin count (2–8) and difficulty (Novice–Master)
- Raking mechanic
- Session statistics tracking