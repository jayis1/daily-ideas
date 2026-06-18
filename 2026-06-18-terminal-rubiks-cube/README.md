# 🎲 Terminal Rubik's Cube

A fully interactive 3×3 Rubik's Cube simulator rendered entirely in the terminal with ANSI colors. Supports all 18 standard moves, scramble, undo, solve detection, and multiple rendering modes.

## Features

- **Full 3×3 Cube Simulation** — All 18 standard moves (U, D, L, R, F, B + primes + doubles)
- **3 Rendering Modes** — Net view, compact cross view, and isometric 3D perspective
- **Interactive Mode** — Real-time keyboard controls for hands-on cubing
- **Scramble** — Random scrambles of configurable length
- **Undo** — Full move history with step-by-step undo
- **Solve Detection** — Automatically detects when the cube is solved
- **Progress Tracking** — Corner/edge counters show how close you are to solving
- **Algorithm Application** — Apply standard notation algorithms (e.g., `R U R' U'`)
- **Self-Tests** — 66 built-in tests verify cube logic correctness

## Installation

No external dependencies required — uses only Python 3 standard library:

```bash
# Make executable (optional)
chmod +x rubiks.py

# Or just run directly
python3 rubiks.py
```

## Usage

### Interactive Mode (default)
```bash
python3 rubiks.py
```

Keyboard controls in interactive mode:
| Key | Action | Key | Action |
|-----|--------|-----|--------|
| `u` | U move (prime) | `U` (shift+u) | U move |
| `d` | D move (prime) | `D` | D move |
| `l` | L move (prime) | `L` | L move |
| `r` | R move (prime) | `R` | R move |
| `f` | F move (prime) | `F` | F move |
| `b` | B move (prime) | `B` | B move |
| `s` | Scramble | `z` | Undo last move |
| `x` | Reset to solved | `v` | Toggle view mode |
| `q` | Quit | `?` | Show help |

> Lowercase = prime (counter-clockwise), Uppercase = clockwise. Press `2` after a move for a double turn.

### Command-Line Options

```bash
# Scramble with 25 random moves and show result
python3 rubiks.py --scramble 25

# Scramble and enter interactive mode
python3 rubiks.py --scramble 20 --interactive

# Apply an algorithm and show before/after
python3 rubiks.py --algo "R U R' U'"

# Apply specific moves
python3 rubiks.py --moves "R U2 F'"

# Use compact rendering mode
python3 rubiks.py --view compact

# Check solve status
python3 rubiks.py --scramble 10 --solve-check

# Show statistics
python3 rubiks.py --scramble 15 --stats

# Run self-tests (66 tests)
python3 rubiks.py --test
```

### Rendering Modes

| Mode | Flag | Description |
|------|------|-------------|
| Net | `--view net` | Cross/net unfolded view (default) |
| Compact | `--view compact` | Side-by-side faces with separators |
| 3D | `--view 3d` | Isometric perspective showing Top, Front, Right |

## Examples

### Apply the Sexy Move algorithm
```bash
python3 rubiks.py --algo "R U R' U'"
```

### Scramble and show compact view
```bash
python3 rubiks.py --scramble 20 --view compact
```

### Run the comprehensive test suite
```bash
python3 rubiks.py --test
```

Output:
```
Running Terminal Rubik's Cube self-tests...

  ✅ Cube initializes to solved state
  ✅ All U face cells are W
  ✅ All F face cells are G
  ✅ After R, cube is not solved
  ✅ After undo of R, cube is solved
  ...
  ✅ (R U R' U') × 6 = identity
  ✅ Scramble produces 20 moves
  ✅ Undoing scramble restores solved state
  ...

Results: 66 passed, 0 failed
```

## How It Works

The cube is represented as 6 faces (U, D, F, B, R, L), each a 3×3 grid of color characters. When a move is applied:

1. The face itself rotates 90° (clockwise or counter-clockwise)
2. The adjacent edge rows/columns cycle between neighboring faces
3. All face permutations follow standard Rubik's Cube notation

The implementation correctly handles:
- **Face rotation** — In-place 90° CW/CCW matrix rotation
- **Edge cycling** — Correct row/column swaps between adjacent faces
- **Inverse moves** — U' undoes U, U2 is self-inverse
- **Group properties** — 4× any single move returns to solved state

## Color Mapping

| Face | Color | ANSI |
|------|-------|------|
| U (Up) | White (W) | White background |
| D (Down) | Yellow (Y) | Yellow background |
| F (Front) | Green (G) | Green background |
| B (Back) | Blue (B) | Blue background |
| R (Right) | Orange (O) | Red background |
| L (Left) | Red (R) | Magenta background |

## License

MIT