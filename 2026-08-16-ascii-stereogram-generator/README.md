# ASCII Stereogram Generator (SIRDS)

> Generate single-image random dot stereograms in the terminal using ASCII characters. Hidden 3D shapes pop out when you relax or cross your eyes.

## What Is a Stereogram?

A single-image random dot stereogram (SIRDS) is an image where a hidden 3D shape is encoded through horizontal offsets in an otherwise random texture. When you view the image with your eyes slightly misaligned — either by relaxing them (wall-eyed/parallel viewing) or crossing them (cross-eyed viewing) — the repeating patterns fuse and your brain reconstructs the depth, making a 3D shape appear to float above or sink below the surface.

This project recreates the classic "Magic Eye" effect using **ASCII characters** instead of pixels, so it works right in your terminal.

## Features

- **11 built-in depth patterns**: sphere, torus (donut), cone, pyramid, diamond, wave, steps (ziggurat), heart, spiral, tunnel, and random blobs
- **Custom text mode**: render any short word as a 3D depth map using a built-in 5×5 bitmap font (`text:HI`, `text:HELLO`)
- **Proper CLI** with `argparse`: `--help`, `--version`, named flags, and a usage epilog
- **`--seed`** for fully reproducible stereograms (both pattern and texture)
- **`--depth-strength`** to tune the 3D effect from subtle to dramatic
- **`--invert`** to flip depth direction (great for cross-eyed viewers)
- **`--show-depth`** to preview the depth map as ASCII shading — see the shape without fusing
- **`--guide`** alignment markers that fuse into one dot when your eyes are correctly converged
- **`--no-banner`** for clean output suitable for piping or scripting
- **`--save FILE`** to write the rendered output to a file
- **`--list-patterns`** to enumerate all available patterns with descriptions
- **Adjustable dimensions**: control width and height via positional arguments
- **Auto-tuned eye separation**: scales with output width for optimal viewing
- **Input validation** with helpful error messages
- **No dependencies**: pure Python 3 standard library
- **Test suite**: 23 tests covering depth maps, the renderer, helpers, dispatcher, and CLI

## How to Install

No installation needed — just a single Python file.

```bash
# Clone or copy the project
git clone https://github.com/<your-username>/daily-ideas.git
cd daily-ideas/2026-08-16-ascii-stereogram-generator
```

Requirements: **Python 3.7+** (uses only the standard library).

## How to Run

```bash
python3 stereogram.py [pattern] [width] [height] [options]
```

### Arguments & Options

| Argument / Option        | Default  | Description |
|--------------------------|----------|-------------|
| `pattern`                | `sphere` | Depth pattern to render. One of the patterns below, or `text:STRING`. |
| `width`                  | `72`     | Character width of the stereogram (10–1000). |
| `height`                 | `24`     | Character height of the stereogram (3–500). |
| `--version`              | —        | Print version and exit. |
| `--help`                 | —        | Show help and exit. |
| `--seed SEED`            | none     | Random seed for reproducible `random` pattern and texture. |
| `--depth-strength MULT`  | `0.33`   | Depth multiplier in [0.0, 1.0]. Higher = more dramatic, harder to fuse. |
| `--invert`               | off      | Invert depth (pop-out ↔ sink-in). |
| `--no-banner`            | off      | Suppress banner and info header. |
| `--guide`                | off      | Print alignment guide markers above the stereogram. |
| `--show-depth`           | off      | Print depth map as ASCII shading instead of a stereogram. |
| `--save FILE`            | none     | Also write output to FILE. |
| `--list-patterns`        | off      | List all available patterns and exit. |

### Available Patterns

| Pattern     | Description |
|-------------|-------------|
| `sphere`    | A floating sphere (front hemisphere). Easiest to see. |
| `torus`     | A 3D donut. |
| `cone`      | A cone pointing toward you. |
| `pyramid`   | A square pyramid pointing toward you. |
| `diamond`   | A rotated square (diamond) using Manhattan distance. |
| `wave`      | A rippling sine wave field. |
| `steps`     | Concentric ziggurat steps. |
| `heart`     | A 3D heart via the implicit heart curve. |
| `spiral`    | An Archimedean spiral ramp — depth rises as you follow the arm. |
| `tunnel`    | A receding ringed vortex — concentric rings getting deeper toward center. |
| `random`    | Random blurry blobs — great for practicing the effect. |
| `text:STR`  | Render the word `STR` in 3D using a 5×5 bitmap font (A–Z, 0–9, space, `! ? . , - / :`). |

## Usage Examples

```bash
# Default: a floating sphere
python3 stereogram.py

# A 3D donut/torus
python3 stereogram.py torus

# A 3D heart
python3 stereogram.py heart

# Render the word "HI" in 3D
python3 stereogram.py text:HI

# Render "HELLO" in 3D, bigger
python3 stereogram.py text:HELLO 100 24

# Random blobs — practice seeing the effect
python3 stereogram.py random

# Reproducible random pattern
python3 stereogram.py random 80 28 --seed 42

# Bigger output for more depth detail
python3 stereogram.py sphere 100 30

# Smaller output for narrow terminals
python3 stereogram.py cone 50 16

# More dramatic 3D (can be harder to fuse)
python3 stereogram.py heart --depth-strength 0.45

# Invert depth (cone sinks away instead of popping out)
python3 stereogram.py cone --invert

# Preview the shape without fusing — prints a shaded depth map
python3 stereogram.py spiral --show-depth

# Alignment guide markers help you lock in the right convergence
python3 stereogram.py sphere --guide

# Save output to a file
python3 stereogram.py heart --save heart.txt

# Clean output with no banner (good for piping)
python3 stereogram.py diamond --no-banner

# List all patterns
python3 stereogram.py --list-patterns

# Version
python3 stereogram.py --version
```

## How to View the 3D Effect

1. **Position**: Hold the screen at a comfortable reading distance (or slightly closer).
2. **Relax your eyes**: Let your gaze go soft and unfocused — as if looking *through* the screen into the distance.
3. **Fuse the image**: You'll see the text rows double. Slowly let the doubled images overlap until the repeating patterns lock together.
4. **See the shape**: Once the patterns fuse, a 3D shape will appear to float above or sink below the background.

**Alternative (cross-eyed)**: Cross your eyes slightly until the doubled images merge. This is the opposite convergence direction from wall-eyed viewing — either one works, but wall-eyed is usually easier for most people. If cross-eyed viewing works better for you, try `--invert` so the depth reads correctly.

**Using `--guide`**: The guide prints two `|` markers separated by the eye-separation distance. When you've converged correctly, the two markers will fuse into a single dot — at that point the stereogram below should pop out instantly.

**Tips**:
- Start with `sphere` or `cone` — they're the easiest shapes to see.
- A wider terminal window gives more depth range.
- It can take 10–30 seconds the first time. Once your eyes "click," subsequent viewing is instant.
- If you can't see the effect, try `--show-depth` first to confirm what the shape looks like, then go back to the stereogram.

## How It Works

The renderer works row-by-row:

1. Each row is initialized with random characters from a noise pool (`. , : ; ~ = + * o # % @`).
2. For each pixel with non-zero depth `d ∈ [0, 1]`, the algorithm computes a **pixel separation**:

   ```
   separation = eye_separation − d × eye_separation × depth_mul
   ```

   Closer objects (higher `d`) produce a *smaller* separation, which makes the fused image pop *toward* the viewer.
3. The character at position `x` is copied from position `x − separation`, ensuring both eyes see the same symbol at the two matching positions. This is the core of the SIRDS algorithm.
4. Background pixels (depth = 0) keep their random characters, creating the camouflaging noise.

The depth maps are generated mathematically:
- **Sphere**: front hemisphere via `z = √(1 − (x/r)² − (y/r)²)`
- **Torus**: depth from the minor circle of a torus ring
- **Cone**: linear falloff from center
- **Pyramid**: Chebyshev distance from center
- **Diamond**: Manhattan distance from center (rotated square)
- **Wave**: sum of sine functions
- **Steps**: quantized concentric squares
- **Heart**: implicit heart curve `(x² + y² − 1)³ − x²y³ ≤ 0`
- **Spiral**: Archimedean spiral — depth rises along the unwound arm
- **Tunnel**: concentric rings with sawtooth depth that recedes toward center
- **Text**: 5×5 bitmap font rendered as depth=1 pixels

## Testing

The project includes a self-contained test suite (no external test framework required):

```bash
python3 test_stereogram.py
```

This runs 23 tests covering depth-map generators (bounds, ranges, reproducibility, new patterns), the renderer (dimensions, flat maps, seeded reproducibility), helpers (`invert_depth`, `render_depth_map`, `alignment_guide`), the pattern dispatcher, and the CLI (default run, `--version`, `--help`, bad width, bad pattern, `--list-patterns`, `--show-depth`, `--invert`, `--seed`, `--save`).

## File Structure

```
2026-08-16-ascii-stereogram-generator/
├── stereogram.py        # The complete generator (single file)
├── test_stereogram.py   # Test suite (23 tests, no dependencies)
└── README.md            # This file
```

## Technical Notes

- The character aspect ratio (chars are ~2× taller than wide) is accounted for in all depth map calculations by doubling the y-offset.
- Eye separation auto-scales: `eye_sep = max(8, min(20, width // 6))` — wider images get more separation for stronger depth.
- The `depth_mul` / `--depth-strength` parameter (default 0.33) controls how strongly depth shifts the pattern. Higher values create more dramatic 3D but can be harder to fuse. Range is [0.0, 1.0].
- `--seed` makes both the `random` depth pattern and the stereogram texture fully reproducible by passing a `random.Random` instance through the pipeline.
- `--invert` applies `1 − d` to the depth map, flipping which surfaces pop out vs. sink in.
- The 5×5 bitmap font supports A–Z, 0–9, space, and the punctuation `! ? . , - / :`.
- Input validation guards width (10–1000), height (3–500), and depth-strength (0.0–1.0) ranges, returning exit code 2 on bad input.
- Exit codes: `0` = success, `1` = runtime error (bad pattern, write failure), `2` = invalid arguments.

## License

Free to use, modify, and share. Created as a daily creative coding project.