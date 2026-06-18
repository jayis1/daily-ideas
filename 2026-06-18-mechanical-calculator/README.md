# ⚙ Curta Type II — Mechanical Calculator Simulator

A faithful terminal simulation of the Curta Type II mechanical calculator, the remarkable hand-cranked calculating machine invented by Curt Herzstark in a Buchenwald concentration camp and first produced in 1948.

![Python](https://img.shields.io/badge/python-3.11-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Description

This simulator recreates the experience of using a Curta mechanical calculator in your terminal. The Curta used a stepped drum mechanism with setting sliders, a carriage, result and counter dials, and a hand crank to perform addition, subtraction, multiplication, and division through pure mechanical operations — no electronics required.

The simulator features:

- **11-digit setting register** with visual sliders
- **8-digit revolution counter** (multiplier tracker)
- **15-digit result/accumulator dial**
- **Carriage position** (shifts by powers of 10, like a real Curta)
- **Animated gear mechanisms** with rotating crank visualization
- **Full interactive mode** for hands-on calculation
- **Batch mode** for scripted operations
- **Automated demo** showcasing all operations

## How It Works

A real Curta calculator works like this:

1. **Set** a number on the input sliders (0–9 per digit)
2. **Position** the carriage at a decimal place (0–8)
3. **Crank** the handle forward to add, or in reverse to subtract
4. Read the **result** on the accumulator dial and the **count** on the revolution counter

Multiplication is done by cranking multiple times at different carriage positions (e.g., to multiply by 456, crank 6 times at position 0, 5 times at position 1, and 4 times at position 2). Division uses repeated subtraction.

## Features

- 🎛️ **Setting Register** — 11 sliders (positions 0–10) for input
- 🔄 **Crank Forward** — adds the set value × 10^carriage to result
- 🔙 **Crank Reverse** — subtracts the set value × 10^carriage from result
- 🛷 **Carriage** — shifts decimal position (×1, ×10, ×100, ... ×10⁸)
- 📊 **Result Dial** — 15-digit accumulator
- 🔢 **Counter Dial** — 8-digit revolution counter
- ⚙️ **Animated Gears** — visible crank mechanism rotation
- 📜 **Operation Log** — tracks all operations performed
- 🎬 **Demo Mode** — automated walkthrough of addition, multiplication, and subtraction

## Installation

No external dependencies needed — uses only Python's standard library:

```bash
# Clone or download, then run directly
python3 mechanical_calculator.py
```

## How to Run

### Interactive Mode

```bash
python3 mechanical_calculator.py --interactive
```

Interactive commands:
| Command | Description |
|---------|-------------|
| `s <number>` | Set a number on the input sliders |
| `c [times]` | Crank forward (default: 1 time) |
| `r [times]` | Crank in reverse (default: 1 time) |
| `p <pos>` | Set carriage position (0–8) |
| `C` | Clear result & counter |
| `C all` | Clear everything |
| `+ <number>` | Quick add a number |
| `- <number>` | Quick subtract a number |
| `q` | Quit |

### Quick Calculations

```bash
# Addition
python3 mechanical_calculator.py --add 4287 3156
# → Result: 7443

# Subtraction
python3 mechanical_calculator.py --subtract 9000 3456
# → Result: 5544

# Multiplication (uses carriage-shifting algorithm)
python3 mechanical_calculator.py --multiply 123 456
# → Result: 56088

# Integer division
python3 mechanical_calculator.py --divide 17 5
# → Quotient: 3, Remainder: 2
```

### Demo Mode

```bash
# Watch an automated demonstration
python3 mechanical_calculator.py --demo

# Slow down animations (default speed: 1.0, higher = slower)
python3 mechanical_calculator.py --demo --speed 2.0
```

### Batch Mode

```bash
# Chain operations together
python3 mechanical_calculator.py --batch set:4287 add:4287 add:3156
# Available: set:N, add:N, sub:N, crank:N, reverse:N, position:N, clear, clear:all, clear:counter
```

## Usage Examples

### Manual Multiplication (like on a real Curta)

To compute 123 × 456:

1. Set number to 123: `s 123`
2. Set carriage to position 0: `p 0`
3. Crank 6 times (for the 6 in 456): `c 6`
4. Set carriage to position 1: `p 1`
5. Crank 5 times (for the 5 in 456): `c 5`
6. Set carriage to position 2: `p 2`
7. Crank 4 times (for the 4 in 456): `c 4`
8. Read result: **56088**

### Division via Repeated Subtraction

To compute 17 ÷ 5:

1. Set 17 and crank forward: `+ 17`
2. Set 5 and crank reverse until result < 5
3. Count how many times you cranked = quotient
4. Remaining result = remainder (2)

## The Real Curta

The Curta was invented by Curt Herzstark (1902–1988), an Austrian engineer who designed it while imprisoned in Buchenwald concentration camp during World War II. After liberation in 1945, he completed the design and began production in Liechtenstein in 1948. Approximately 140,000 Curta calculators were produced in two models (Type I and Type II) before being superseded by electronic calculators in the 1970s.

The Curta is a cylindrical device about the size of a pepper grinder, with a hand crank on top and setting sliders on the side. It is considered one of the finest mechanical calculators ever built and a masterpiece of precision engineering.

## Technical Details

- **Setting register**: 11 digits (Type II specification)
- **Counter register**: 8 digits
- **Result register**: 15 digits
- **Carriage positions**: 0–8 (multiplying by 10^position)
- **Carry propagation**: Automatic, just like the real machine
- **All computation uses integer arithmetic** — faithful to the mechanical original

## License

MIT