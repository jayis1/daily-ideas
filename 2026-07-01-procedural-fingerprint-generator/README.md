# Procedural Fingerprint Generator

**Version 1.1.1**

Generate unique, realistic ASCII fingerprint patterns from a seed value. Each seed produces a deterministic, reproducible fingerprint with scientifically-inspired ridge patterns including loops, whorls, arches, tented arches, and double loops.

## How It Works

The generator uses an **orientation field model** — a technique inspired by real fingerprint analysis:

1. An **orientation field** computes the local ridge direction at every point, modeled after real fingerprint pattern classes (Henry classification system)
2. A **frequency field** determines local ridge spacing, with variations near the core
3. **Phase integration** accumulates these fields across the grid to produce a continuous phase map
4. A **cosine rendering** step converts the phase map into ridge/valley intensity values
5. An **elliptical mask** shapes the output to resemble a real finger pad impression
6. **Minutiae points** (endings, bifurcations, islands) are randomly placed and optionally marked

## Features

- **5 fingerprint pattern types**: Loop, Whorl, Arch, Tented Arch, Double Loop
- **Deterministic generation**: Same seed always produces the same fingerprint
- **Unique fingerprint IDs**: SHA-256 hash based on pattern + seed + minutiae positions
- **Minutiae visualization**: Mark ridge endings (◆), bifurcations (◇), and islands (○)
- **Side-by-side comparison**: View all pattern types simultaneously with `--compare`
- **ANSI color output**: Colorized rendering with `--color`
- **Batch generation**: Generate multiple fingerprints with `--batch N`
- **JSON output**: Machine-readable metadata with `--json`
- **File export**: Save fingerprint to a file with `--output` (ANSI codes are automatically stripped)
- **Adjustable density and contrast**: Fine-tune the visual output
- **Custom dimensions**: Control width and height of the output
- **Input validation**: Rejects invalid parameters with clear error messages
- **Responsive borders**: Border alignment is maintained even at narrow widths
- **Version flag**: `--version` support

## Installation

No external dependencies — uses only Python standard library:

```bash
# Just make it executable
chmod +x fingerprint.py
```

Requires Python 3.7+.

## Usage

```bash
# Generate a random loop fingerprint
python3 fingerprint.py

# Generate a specific pattern type
python3 fingerprint.py --pattern whorl
python3 fingerprint.py --pattern arch
python3 fingerprint.py --pattern tented_arch
python3 fingerprint.py --pattern double_loop

# Use a specific seed for reproducibility
python3 fingerprint.py --seed 12345

# Show minutiae points
python3 fingerprint.py --minutiae

# Enable color output
python3 fingerprint.py --color

# Compare all pattern types side by side
python3 fingerprint.py --compare

# Get just the fingerprint ID hash
python3 fingerprint.py --seed 42 --id-only

# Output metadata as JSON
python3 fingerprint.py --seed 42 --json

# Output JSON comparison of all patterns
python3 fingerprint.py --seed 42 --json --compare

# Adjust density and contrast
python3 fingerprint.py --density 0.8 --contrast 1.5

# Custom dimensions
python3 fingerprint.py --width 60 --height 70

# List available patterns
python3 fingerprint.py --list

# Show version
python3 fingerprint.py --version

# Batch generate 5 fingerprints
python3 fingerprint.py --batch 5 --seed 100

# Save fingerprint to a file (ANSI codes are stripped automatically)
python3 fingerprint.py --seed 42 --output fingerprint.txt

# Save colorized fingerprint to a file (ANSI codes are stripped)
python3 fingerprint.py --seed 42 --color --output fingerprint.txt

# Save fingerprint ID to a file
python3 fingerprint.py --seed 42 --id-only --output id.txt

# Save batch output to a file
python3 fingerprint.py --batch 3 --seed 100 --output batch.txt

# Save comparison to a file
python3 fingerprint.py --compare --output comparison.txt
```

## Examples

### Ulnar Loop (seed: 42)
```
┌──────── Fingerprint: Ulnar Loop (seed: 42) ────────┐
│                      +*****++*                       │
│                   **+#%#%%#%#+#*=                     │
│                =+*%##%@%*%@@%#*++=-:                  │
│               .:+*#**+####*#+===:=-.                  │
│             . :+**#=*=#+=*+:=--:-.:-                  │
│              :-=+=-==-==--:=:... ....                  │
│              ::---:===--::. ....   .                   │
│            .  .::::-:-.-...     .  .   .               │
│ Minutiae: 10 points                                 │
└────────────────────────────────────────────────────┘
```

### JSON Output
```bash
$ python3 fingerprint.py --seed 42 --json
{
  "fingerprint_id": "2818839C6E44B290",
  "pattern_type": "loop",
  "pattern_name": "Ulnar Loop",
  "seed": 42,
  "width": 50,
  "height": 55,
  "minutiae_count": 10,
  "minutiae": [
    {"x": 18.4, "y": 15.2, "angle": 3.7568, "type": "bifurcation"},
    ...
  ],
  "ascii": "..."
}
```

## Pattern Types

| Pattern | Description |
|---------|-------------|
| `loop` | Ulnar Loop — ridges enter from one side, curve around the core, and exit the same side |
| `whorl` | Plain Whorl — concentric spiral ridges around a central core |
| `arch` | Plain Arch — ridges enter from one side, rise in the middle, and exit the other side |
| `tented_arch` | Tented Arch — like an arch but with a sharp, pointed peak |
| `double_loop` | Double Loop Whorl — two loop cores with ridges spiraling between them |

## Fingerprint IDs

Each generated fingerprint has a unique 16-character hex ID derived from SHA-256 hashing of the seed, pattern type, and minutiae positions. This mimics how real fingerprint identification systems work:

```bash
$ python3 fingerprint.py --seed 42 --pattern loop --id-only
2818839C6E44B290

$ python3 fingerprint.py --seed 42 --pattern whorl --id-only
820215DDFBDDB146
```

## Algorithm Details

The orientation field for each pattern type is based on simplified mathematical models of real fingerprint ridge flows:

- **Loop**: `θ(x,y) = π/2 + strength × sin(2φ)` where φ is the angle from the core
- **Whorl**: `θ(x,y) = φ + π/2` (pure rotation around core)
- **Arch**: `θ(x,y) = -π/2 + bump(x) × h(y)` with Gaussian bump
- **Tented Arch**: Sharper Gaussian spike than arch
- **Double Loop**: Weighted blend of two loop orientation fields around dual cores

Phase integration accumulates the orientation and frequency gradients from the top-left corner, averaging contributions from the left and above neighbors for numerical stability. Gaussian noise is added to the rendered output for realism.

## Testing

```bash
# Run the test suite
python3 -m pytest test_fingerprint.py -v
```

The test suite includes 54 tests covering orientation computation, rendering, minutiae generation, fingerprint IDs, CLI argument handling, JSON output, file export, batch mode, input validation, border alignment, ANSI stripping for file output, and all new bug fixes.

## Changelog

### v1.1.1 — Bug Fix Release

- **Fixed**: Border alignment for narrow widths — title, info, and legend lines could overflow the border when the width was less than ~34 characters. Now all lines are properly truncated/padded to fit.
- **Fixed**: `--color --output` wrote ANSI escape codes to the file. ANSI codes are now automatically stripped when writing to a file.
- **Fixed**: `--batch --output` didn't write batch output to the file — it only printed to stdout. Now batch output is properly written to the specified file.
- **Fixed**: `--compare --output` didn't write comparison output to the file. Now comparison output is properly written to the specified file.
- **Fixed**: `--id-only --output` didn't write the fingerprint ID to the file. Now the ID is written to the specified file.
- **Fixed**: Error messages for density and contrast validation said "between 0 and X" but rejected 0. Messages now correctly say "greater than 0 and at most X".
- **Added**: `_pad_line()` helper function for safe text padding/truncation within borders.
- **Added**: `generate_comparison()` and `generate_batch()` now return strings instead of printing directly, enabling proper file output handling.
- **Added**: 7 new tests covering border alignment, ANSI stripping, file output for batch/compare/id-only modes, and error message content.