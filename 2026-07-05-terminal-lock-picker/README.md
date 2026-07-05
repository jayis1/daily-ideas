# 🔐 Terminal Lock Picker

An interactive terminal-based simulation of picking pin tumbler locks. Feel the tension, find the binding pins, lift them to the shear line, and experience the satisfying click when a pin sets!

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

### Progression & Stats
- **Session stats** — track locks picked and total time
- **Best time tracking** — persistent best times per pin count and difficulty, saved to `~/.lock_picker_stats.json`
- **Victory screen** — celebration animation with sparkles and time display

### Interface
- **Visual pin chamber** — see each pin's height relative to the shear line in real time
- **Progress bar** — shows how many pins are set
- **Detailed pin info** — current height, shear line position, distance to set, spring tension
- **Pick health bar** — shown on Hard/Master difficulty when durability matters (with distinct visuals for healthy/medium/critical)
- **Small terminal support** — handles terminals as small as 40×20 with a warning

### CLI & Demo
- **`--help`** and **`--version`** flags for quick reference
- **`--pins N`** and **`--difficulty N`** to start with specific settings
- **`--demo`** mode to watch the AI auto-pick a lock (non-interactive, no curses required)
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

# Watch the AI pick a lock
python3 lock_picker.py --demo

# Demo with custom speed (faster)
python3 lock_picker.py --demo --pins 3 --difficulty 1 --speed 0.01

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
9. **Watch pick health** — on Hard/Master, your pick can break. Don't rake too much!
10. **Best times are saved** — try to beat your personal record for each configuration

## Testing

Run the test suite (41 tests covering lock creation, physics, picking, raking, durability, hints, CLI args, and regression tests for fixed bugs):

```bash
python3 -m pytest test_lock_picker.py -v
```

Or with unittest:

```bash
python3 test_lock_picker.py
```

## Changelog

### v1.2.0 — Bug Fix Release

**Fixed bugs:**
- **`pins_set_count` desync** — The counter could be double-incremented when lifting an already-set pin, and could go negative after raking. Replaced the manual counter with a computed property derived from actual `is_set` flags, eliminating all desync issues.
- **`pick_health` going negative** — Pick health could drop below 0 from both lifting and raking on Hard/Master difficulty. Added `max(0.0, ...)` clamping to both code paths.
- **`check_open()` tension threshold** — Changed from `> 0.2` to `>= 0.2` so the lock opens at exactly 20% tension, matching the displayed tension percentage.
- **`get_pick_health_bar()` identical branches** — The medium health (0.2–0.5) and low health (<0.2) branches produced identical output (both used `▒`). Low health now uses `·` for a distinct critical visual.
- **`get_pin_visual()` unreachable code** — Removed dead `elif pin.is_set` branch that could never execute (the `if pin.is_set` above it always returns first).
- **Demo mode progress counting** — The `no_progress_count` was incremented even on successful pin clicks, causing unnecessary raking attempts every 30 rounds even when making progress. Now only increments when no pin clicks in a round.
- **Falsy CLI arg defaults** — `--difficulty 1` was treated as unspecified because `1` is falsy. Changed to `is not None` checks for both `--pins` and `--difficulty`.
- **`result` variable undefined on error** — In `main()`, if `curses.wrapper` raised a non-KeyboardInterrupt exception, `result` was referenced before assignment. Added proper initialization and `is not None` check.
- **Raking unset logic** — Moved the "raking can unset pins" logic from inside the pin iteration loop to a separate pass, fixing a bug where the `elif pin.is_set` check could match pins that were just set in the same rake pass.

**Added tests:**
- 9 new regression tests in `TestBugFixes` class covering all fixed bugs
- Total test count: 41 (up from 32)

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