# Terminal Aurora Borealis Simulator

A self-contained Python program that paints a procedurally-animated aurora
borealis across your terminal — drifting curtains of light, a twinkling
starfield, and a snow-capped mountain silhouette below. No external
dependencies, no assets — everything is generated from value noise and
mathematics at runtime.

![aurora screenshot — green palette](./screenshot.svg)

## Features

- **Procedural curtains** — four layered value-noise curtains with different
  frequencies, speeds, and phases produce organic, ever-changing ribbons of
  light. A 2D noise field adds vertical "ray" streaks that flicker through the
  bands.
- **Five color palettes** — `green` (classic northern lights), `violet`
  (magnetic purple), `sunset` (warm corona), `rainbow` (full spectral), and
  `ice` (cool blue-white). Cycle between them live with `c`.
- **Twinkling starfield** — dozens of stars with per-star brightness and
  twinkle phase sit behind the aurora.
- **Mountain silhouette** — a procedurally generated ridge with snow caps on
  the taller peaks sits in the foreground.
- **Truecolor rendering** — 24-bit ANSI escape codes drive the colors; the
  character ramp ` .:-=+*#%@` controls density, so the image reads even on
  terminals without truecolor support.
- **Reduced-motion mode** (`r`) — slows the animation and disables star
  twinkle for a calmer, accessibility-friendly view.
- **Resize-aware** — detects terminal resize and regenerates the starfield
  and mountains to fit.
- **Snapshot mode** (`--once`) — renders a single frame and exits, perfect for
  screenshots, piping, or CI smoke tests.
- **No dependencies** — runs on the Python 3.10+ standard library alone.

## Install

No installation step is required. Just clone the repo and run the script:

```bash
git clone <this-repo>
cd 2026-07-26-terminal-aurora-simulator
python3 aurora.py
```

Requires Python 3.10+ (uses `match`-free `str | None` type hints, so 3.10 is
the practical floor). Works best in a terminal that supports 24-bit
truecolor (most modern terminals: GNOME Terminal, Kitty, WezTerm, iTerm2,
Alacritty, Windows Terminal).

## How to run

```bash
# default interactive animation
python3 aurora.py

# pick a starting palette
python3 aurora.py --palette violet

# seed it for a reproducible scene
python3 aurora.py --seed 1337 --palette rainbow

# render a single frame (great for screenshots / piping to a file)
python3 aurora.py --once --seed 42 --palette green

# run for 10 seconds then exit (non-interactive, for cron / demos)
python3 aurora.py --duration 10 --non-interactive

# start in reduced-motion mode
python3 aurora.py --reduced-motion

# custom animation speed
python3 aurora.py --speed 2.0
```

### CLI flags

| Flag                | Default | Description                                      |
|---------------------|---------|--------------------------------------------------|
| `--palette`         | green   | Initial palette: green, violet, sunset, rainbow, ice |
| `--speed`           | 1.0     | Initial animation speed multiplier               |
| `--seed`            | time    | Random seed for reproducible scenes             |
| `--fps`             | 24      | Target frames per second                         |
| `--duration`        | 0       | Run for N seconds then exit (0 = forever)        |
| `--reduced-motion`  | off     | Start in reduced-motion mode                     |
| `--non-interactive` | off     | Do not read keyboard input                       |
| `--once`            | off     | Render a single frame and exit                   |

## Controls (interactive mode)

| Key        | Action                          |
|------------|---------------------------------|
| `q` / Esc  | Quit                            |
| `+` / `=`  | Speed up                        |
| `-` / `_`  | Slow down                       |
| `r`        | Toggle reduced-motion mode      |
| `c`        | Cycle to next color palette     |
| `h`        | Toggle the help overlay         |
| `space`    | Pause / resume                  |
| Ctrl-C    | Quit                            |

## Usage examples

Capture a still frame to a text file (ANSI codes included):

```bash
python3 aurora.py --once --seed 42 --palette violet > frame.txt
less -R frame.txt   # -R lets less render the colors
```

Run a 30-second non-interactive demo on a projector:

```bash
python3 aurora.py --duration 30 --non-interactive --palette rainbow --speed 1.3
```

Run the smoke test to verify the renderer:

```bash
python3 test_smoke.py
```

## How it works

1. **Value noise.** A fixed-size grid of random values is sampled with
   smoothstep interpolation to produce 1D and 2D value noise. Fractal noise
   (a sum of octaves with decreasing amplitude) gives the curtains their
   natural-looking variation.
2. **Curtains.** For each screen column, four layered noise functions — each
   with its own frequency, speed, phase, brightness, and color contribution
   — are summed into a column intensity and a color coordinate `t`.
3. **Vertical profile.** A Gaussian falloff centered on a band in the upper
   sky, shifted by the column intensity, concentrates the light into a
   ribbon. A 2D noise field multiplies through as "ray" streaks.
4. **Color.** The column's `t` value is blended with the vertical position and
   the streak noise, then looked up in the active palette's gradient stops
   to produce a 24-bit RGB color. Intensity darkens the color and selects the
   character from the ramp.
5. **Stars.** A scatter of stars with per-star brightness and twinkle phase
   is rendered first; the aurora overwrites them where it is bright.
6. **Mountains.** A sum of sine-like noise ridges produces a silhouette; tall
   peaks get snow caps.
7. **Compositing.** Each row is emitted as a run of characters, only switching
   the ANSI color escape when the color actually changes, keeping the output
   stream compact.

## Files

- `aurora.py` — the simulator (single file, stdlib only).
- `test_smoke.py` — a small smoke test that exercises every palette, the
  resize path, and the key handler.

## License

MIT — do whatever you like.