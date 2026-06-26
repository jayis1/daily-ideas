# Terminal Spirograph

Generate beautiful hypotrochoid, epitrochoid, rose, and Lissajous curve patterns directly in your terminal using Unicode characters and ANSI colors.

## Features

- **4 curve families**: Hypotrochoid, Epitrochoid, Rose, and Lissajous
- **13 built-in presets**: `classic`, `starflower`, `daisy`, `vortex`, `sunburst`, `pinwheel`, `lotus`, `pentarose`, `heptarose`, `trefoil`, `bowtie`, `infinity`, `butterfly`
- **Animated drawing**: Watch curves being drawn progressively
- **Rainbow & gradient colors**: Multiple color palettes (`auto`, `rainbow`, `gradient`, `none`)
- **SVG export**: Export curves as high-quality vector SVG files
- **Continuous loop mode**: `--loop` for endless random spirographs
- **Seeded random generation**: `--seed N` for reproducible results
- **Fine & block character sets**: Choose rendering density
- **Input validation**: Clear error messages for invalid parameters
- **Security**: SVG export blocks writes to system directories

## Installation

No dependencies beyond Python 3.7+ and a standard library. Just clone and run:

```bash
git clone <repo-url>
cd terminal-spirograph
python3 spirograph.py --help
```

For running tests:

```bash
pip install pytest
pytest test_spirograph.py -v
```

## Usage

### Basic examples

```bash
# Show a hypotrochoid with default parameters
python3 spirograph.py --hypo --static

# Specify custom parameters
python3 spirograph.py --hypo --R 11 --r 4 --d 6 --static

# Random epitrochoid
python3 spirograph.py --epi --random

# Rose curve
python3 spirograph.py --rose --random

# Lissajous figure
python3 spirograph.py --lissajous --random
```

### Presets

```bash
# Use a named preset
python3 spirograph.py --preset classic --static

# List all presets
python3 spirograph.py --list-presets
```

### Animation

```bash
# Animated drawing (default when terminal is available)
python3 spirograph.py --preset starflower

# Static render (no animation)
python3 spirograph.py --preset daisy --static

# Custom animation speed
python3 spirograph.py --preset vortex --frames 60 --fps 30
```

### SVG export

```bash
# Export as SVG
python3 spirograph.py --preset classic --export-svg output.svg

# SVG export with custom dimensions
python3 spirograph.py --preset starflower --export-svg star.svg
```

### Reproducible generation

```bash
# Same seed always produces the same random curve
python3 spirograph.py --random --seed 42 --static
```

### Loop mode

```bash
# Continuously generate random spirographs (Ctrl+C to stop)
python3 spirograph.py --loop
```

### Color palettes

```bash
python3 spirograph.py --preset classic --palette rainbow --static
python3 spirograph.py --preset classic --palette gradient --static
python3 spirograph.py --preset classic --palette none --static
```

## All Command-Line Options

| Option | Description |
|--------|-------------|
| `--hypo` | Use hypotrochoid curve |
| `--epi` | Use epitrochoid curve |
| `--rose` | Use rose curve |
| `--lissajous` | Use Lissajous curve |
| `--random` | Generate random parameters |
| `--preset NAME` | Use a named preset |
| `--list-presets` | List all available presets and exit |
| `--R`, `--r`, `--d` | Outer radius, inner radius, pen distance (hypo/epi) |
| `--k`, `--n` | Numerator/denominator parameters (rose) |
| `--a`, `--b`, `--delta` | Frequencies and phase shift (lissajous) |
| `--width N` | Output width (default: terminal width) |
| `--height N` | Output height (default: terminal height - 4) |
| `--points N` | Number of curve points (default: 20000) |
| `--static` | Static render, no animation |
| `--frames N` | Animation frames (default: 40) |
| `--fps N` | Animation FPS (default: 15) |
| `--palette` | Color palette: `auto`, `rainbow`, `gradient`, `none` |
| `--chars` | Character set: `block` (default) or `fine` |
| `--gallery` | Show gallery of different curves |
| `--loop` | Continuous random spirographs |
| `--seed N` | Random seed for reproducible generation |
| `--export-svg FILE` | Export curve as SVG file |
| `--version` | Show version |

## Error Handling

The program validates inputs and provides clear error messages:

- **Negative dimensions**: `--width` and `--height` must be ≥ 1
- **Zero/negative parameters**: R must be positive; r, d cannot be negative
- **r ≥ R warning**: For hypotrochoids, warns when r ≥ R (small circle can't roll inside)
- **Zero division**: Blocks r=0, n=0, and both a/b=0
- **Degenerate curves**: Warns when Lissajous a=0 or b=0 (produces a line)
- **Invalid dimensions**: `--frames`, `--fps`, and `--points` must be ≥ 1
- **SVG security**: Blocks writes to system directories (`/etc`, `/usr`, etc.)
- **Unknown curve types**: `compute_curve()` and `generate_params()` raise `ValueError` for unknown types
- **Override warnings**: Warns when `--random` overrides explicit parameter values

## Presets

| Preset | Curve Type | Parameters |
|--------|-----------|------------|
| classic | Hypotrochoid | R=11, r=4, d=6 |
| starflower | Hypotrochoid | R=21, r=8, d=5 |
| daisy | Hypotrochoid | R=15, r=7, d=9 |
| vortex | Hypotrochoid | R=19, r=6, d=12 |
| sunburst | Hypotrochoid | R=9, r=4, d=7 |
| pinwheel | Hypotrochoid | R=7, r=3, d=5 |
| lotus | Hypotrochoid | R=11, r=5, d=9 |
| pentarose | Rose | k=5, n=3 |
| heptarose | Rose | k=7, n=4 |
| trefoil | Rose | k=3, n=1 |
| bowtie | Lissajous | a=1, b=2 |
| infinity | Lissajous | a=1, b=2, δ=π/2 |
| butterfly | Lissajous | a=3, b=4, δ=π/4 |

## Running Tests

```bash
pytest test_spirograph.py -v
```

The test suite includes 62 tests covering:
- Parametric math (hypotrochoid, epitrochoid, rose, Lissajous)
- Curve computation and period correctness
- Rendering and colorization
- Input validation (negative dimensions, zero parameters, unknown types)
- SVG export security (path traversal blocked)
- Rose curve period computation (odd/even k·n)
- Preset validity
- End-to-end integration

## Changelog

### v1.2.0 — Bug fixes
- **Fixed period over-draw**: Hypotrochoid and epitrochoid curves were being drawn R/gcd(R,r) times too many. Now correctly compute the single full period (2π·r/gcd(R,r))
- **Fixed rose curve period**: Was using approximate formula `2π·max(n,2)`. Now uses exact period: `π·n/gcd(k,n)` for odd k·n, `2π·n/gcd(k,n)` for even k·n
- **Fixed Lissajous period**: Was using `2π·max(a,b,2)`. Now uses `2π·lcm(a,b)` for more accurate closure
- **Fixed SVG path traversal**: `--export-svg` now blocks writes to system directories (/etc, /usr, /bin, etc.) to prevent directory traversal attacks
- **Fixed render_frame with negative/zero dimensions**: Now raises `ValueError` instead of producing garbage output
- **Fixed render_frame with empty points**: Now returns a proper blank grid instead of empty list
- **Added input validation**: Negative R/r/d, zero dimensions, zero frames/fps all produce clear error messages
- **Added warning for r ≥ R in hypotrochoid**: Warns that the curve may not be meaningful
- **Added warning for degenerate Lissajous**: Warns when a=0 or b=0
- **Added warning for --random override**: Informs user when --random ignores explicit parameters
- **Fixed division by zero**: animate_curve now validates frames ≥ 1 and fps ≥ 1
- **Fixed unknown curve types**: compute_curve and generate_params now raise ValueError instead of silently returning empty results