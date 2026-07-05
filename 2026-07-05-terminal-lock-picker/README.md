# 🔐 Terminal Lock Picker

An interactive terminal-based simulation of picking pin tumbler locks. Feel the tension, find the binding pins, lift them to the shear line, and experience the satisfying click when a pin sets!

## How It Works

The simulation models a realistic pin tumbler lock:

- **Pins** sit at the bottom of the lock chamber, held down by springs
- **Tension** applied to the plug causes specific pins to **bind** against the chamber wall
- **Bound pins** can be lifted to the **shear line** — when they reach the correct height, they **set** with a satisfying click (terminal bell!)
- Once **all pins are set** while tension is maintained, the lock **opens**

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
- **Pick health bar** — shown on Hard/Master difficulty when durability matters
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
7. **Raking is luck-based** — works better on easier locks with fewer pins
8. **Use hints** — press H to highlight the best pin to work on next
9. **Watch pick health** — on Hard/Master, your pick can break. Don't rake too much!
10. **Best times are saved** — try to beat your personal record for each configuration

## Testing

Run the test suite (32 tests covering lock creation, physics, picking, raking, durability, hints, and CLI args):

```bash
python3 -m pytest test_lock_picker.py -v
```

Or with unittest:

```bash
python3 test_lock_picker.py
```

## What It Does

The game simulates the core mechanics of pin tumbler lock picking:

- **Pin generation**: Each lock generates random pin heights (the "key code") and random binding orders
- **Binding**: When you apply tension to the plug, manufacturing tolerances cause specific pins to bind against the chamber wall
- **Setting**: When you lift a bound pin to the correct height (the shear line), it clicks into place and stays set
- **Spring physics**: Unset pins slowly fall back toward rest under spring pressure
- **Pick durability**: On Hard and Master difficulty, picks wear with use and can break, forcing a new lock
- **Hint system**: Analyzes current lock state and suggests which pin to work on next
- **Opening**: When all pins are simultaneously at their shear line and tension is maintained, the plug rotates and the lock opens
- **Persistent stats**: Best times and totals are saved across sessions to `~/.lock_picker_stats.json`