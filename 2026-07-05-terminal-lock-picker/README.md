# 🔐 Terminal Lock Picker

An interactive terminal-based simulation of picking pin tumbler locks. Feel the tension, find the binding pins, lift them to the shear line, and experience the satisfying click when a pin sets!

## How It Works

The simulation models a realistic pin tumbler lock:

- **Pins** sit at the bottom of the lock chamber, held down by springs
- **Tension** applied to the plug causes specific pins to **bind** against the chamber wall
- **Bound pins** can be lifted to the **shear line** — when they reach the correct height, they **set** with a satisfying click
- Once **all pins are set** while tension is maintained, the lock **opens**

The challenge is finding the right amount of tension (too much and multiple pins bind; too little and nothing binds), then carefully lifting each bound pin to its shear line.

## Features

- **Physics-based pin mechanics** — springs push pins back down, wobble adds realism, damping makes lifting feel tactile
- **Binding order** — pins bind in a random order based on manufacturing imperfections, just like real locks
- **Adjustable difficulty** (Novice → Master) — tighter tolerances, stronger springs, more wobble
- **Adjustable pin count** (2–8 pins) — from simple 2-pin practice locks to challenging 8-pin models
- **Raking** — press `R` to rapidly scrub all pins with a rake tool (lower success rate but satisfying)
- **Visual pin chamber** — see each pin's height relative to the shear line in real time
- **Progress tracking** — bar shows how many pins are set
- **Springback decay** — unset pins slowly fall back down under spring pressure
- **Session stats** — track locks picked and total time

## How to Install

Requires Python 3.6+ with standard library (uses `curses`, which is included on Linux/macOS):

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

```bash
python3 lock_picker.py
```

## Usage

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

## What It Does

The game simulates the core mechanics of pin tumbler lock picking:

- **Pin generation**: Each lock generates random pin heights (the "key code") and random binding orders
- **Binding**: When you apply tension to the plug, the manufacturing tolerances cause specific pins to bind against the chamber wall. These are the pins you need to lift
- **Setting**: When you lift a bound pin to the correct height (the shear line), it clicks into place and stays set
- **Spring physics**: Unset pins slowly fall back toward the rest position under spring pressure
- **Opening**: When all pins are simultaneously at their shear line and tension is maintained, the plug rotates and the lock opens

## Testing

Run the non-interactive test suite:

```bash
python3 test_lock_picker.py
```

This verifies lock creation, tension/binding, pin setting, full lock picking, and spring mechanics.