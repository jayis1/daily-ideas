# ASCII Stereogram Generator (SIRDS)

> Generate single-image random dot stereograms in the terminal using ASCII characters. Hidden 3D shapes pop out when you relax or cross your eyes.

## What Is a Stereogram?

A single-image random dot stereogram (SIRDS) is an image where a hidden 3D shape is encoded through horizontal offsets in an otherwise random texture. When you view the image with your eyes slightly misaligned — either by relaxing them (wall-eyed/parallel viewing) or crossing them (cross-eyed viewing) — the repeating patterns fuse and your brain reconstructs the depth, making a 3D shape appear to float above or sink below the surface.

This project recreates the classic "Magic Eye" effect using **ASCII characters** instead of pixels, so it works right in your terminal.

## Features

- **8 built-in depth patterns**: sphere, torus (donut), cone, pyramid, wave, steps (ziggurat), heart, and random blobs
- **Custom text mode**: render any short word as a 3D depth map using a built-in 5×5 bitmap font (`text:HI`, `text:HELLO`)
- **Adjustable dimensions**: control width and height via CLI arguments
- **Auto-tuned eye separation**: scales with output width for optimal viewing
- **No dependencies**: pure Python 3 standard library
- **Viewing instructions** printed inline so first-time users know how to see the effect

## How to Install

No installation needed — just a single Python file.

```bash
# Clone or copy the file
git clone https://github.com/<your-username>/daily-ideas.git
cd daily-ideas/2026-08-16-ascii-stereogram-generator
```

Requirements: **Python 3.7+** (uses only the standard library).

## How to Run

```bash
python3 stereogram.py [pattern] [width] [height]
```

### Arguments

| Argument  | Default  | Description |
|-----------|----------|-------------|
| `pattern` | `sphere` | One of: `sphere`, `torus`, `cone`, `pyramid`, `wave`, `steps`, `heart`, `random`, or `text:STRING` |
| `width`   | `72`     | Character width of the stereogram |
| `height`  | `24`     | Character height of the stereogram |

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

# Render "HELLO" in 3D
python3 stereogram.py text:HELLO

# Random blobs — practice seeing the effect
python3 stereogram.py random

# Bigger output for more depth detail
python3 stereogram.py sphere 100 30

# Smaller output for narrow terminals
python3 stereogram.py cone 50 16
```

## How to View the 3D Effect

1. **Position**: Hold the screen at a comfortable reading distance (or slightly closer).
2. **Relax your eyes**: Let your gaze go soft and unfocused — as if looking *through* the screen into the distance.
3. **Fuse the image**: You'll see the text rows double. Slowly let the doubled images overlap until the repeating patterns lock together.
4. **See the shape**: Once the patterns fuse, a 3D shape will appear to float above or sink below the background.

**Alternative (cross-eyed)**: Cross your eyes slightly until the doubled images merge. This is the opposite convergence direction from wall-eyed viewing — either one works, but wall-eyed is usually easier for most people.

**Tips**:
- Start with `sphere` or `cone` — they're the easiest shapes to see.
- A wider terminal window gives more depth range.
- It can take 10–30 seconds the first time. Once your eyes "click," subsequent viewing is instant.

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
- **Wave**: sum of sine functions
- **Steps**: quantized concentric squares
- **Heart**: implicit heart curve `(x² + y² − 1)³ − x²y³ ≤ 0`
- **Text**: 5×5 bitmap font rendered as depth=1 pixels

## File Structure

```
2026-08-16-ascii-stereogram-generator/
├── stereogram.py   # The complete generator (single file)
└── README.md       # This file
```

## Technical Notes

- The character aspect ratio (chars are ~2× taller than wide) is accounted for in all depth map calculations by doubling the y-offset.
- Eye separation auto-scales: `eye_sep = max(8, min(20, width // 6))` — wider images get more separation for stronger depth.
- The `depth_mul` parameter (default 0.33) controls how strongly depth shifts the pattern. Higher values create more dramatic 3D but can be harder to fuse.
- The 5×5 bitmap font supports A–Z, 0–9, space, and basic punctuation.

## License

Free to use, modify, and share. Created as a daily creative coding project.