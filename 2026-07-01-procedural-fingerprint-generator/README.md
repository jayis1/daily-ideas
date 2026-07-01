# Procedural Fingerprint Generator

Generate unique, realistic ASCII fingerprint patterns from a seed value. Each seed produces a deterministic, reproducible fingerprint with scientifically-inspired ridge patterns including loops, whorls, arches, tented arches, and double loops.

## How It Works

The generator uses an **orientation field model** — a technique inspired by real fingerprint analysis:

1. An **orientation field** computes the local ridge direction at every point, modeled after real fingerprint pattern classes (Henry classification system)
2. A **frequency field** determines local ridge spacing
3. **Phase integration** accumulates these fields across the grid to produce a continuous phase map
4. A **cosine rendering** step converts the phase map into ridge/valley intensity values
5. An **elliptical mask** shapes the output to resemble a real finger pad impression
6. **Minutiae points** (endings, bifurcations, islands) are randomly placed and optionally marked

## Features

- **5 fingerprint pattern types**: Loop, Whorl, Arch, Tented Arch, Double Loop
- **Deterministic generation**: Same seed always produces the same fingerprint
- **Unique fingerprint IDs**: SHA-256 hash based on pattern + seed + minutiae positions
- **Minutiae visualization**: Mark ridge endings (◆), bifurcations (◇), and islands (○)
- **Side-by-side comparison**: View all pattern types simultaneously
- **Adjustable density and contrast**: Fine-tune the visual output
- **Custom dimensions**: Control width and height of the output

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

# Compare all pattern types side by side
python3 fingerprint.py --compare

# Get just the fingerprint ID hash
python3 fingerprint.py --seed 42 --id-only

# Adjust density and contrast
python3 fingerprint.py --density 0.8 --contrast 1.5

# Custom dimensions
python3 fingerprint.py --width 60 --height 70

# List available patterns
python3 fingerprint.py --list
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
│                   .:.::... .         .:..- :            │
│       .::::.       .:.       .-=+**#****=              │
│      .-+=:=:...   ::: =   .. -=++#%@%%%#@#=            │
│      =*#*=+-.. ...  .:..:  .:-++#@@%%%#%@%@#+          │
│     *%@@%%%%@%#*=-:.      :..   -=+#%%%%#@%@%#@#%#+    │
│     +#@@@%%*%*=-:.   .:... .-+%%@%@@%@%%%@@@%%+        │
│     ...                                                      │
│ Minutiae: 10 points                                  │
└────────────────────────────────────────────────────┘
```

### Plain Whorl (seed: 42)
The whorl pattern produces characteristic concentric spiral ridges rotating around a central core point.

### Comparison View
Use `--compare` to see all five pattern types side by side.

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