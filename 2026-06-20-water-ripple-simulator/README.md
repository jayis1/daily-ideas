# 🌊 Water Ripple Simulator

A real-time 2D wave equation simulator rendered in the terminal using Unicode block characters and 24-bit ANSI colors. Drop stones, place wave sources, build walls, save/load state, and watch waves propagate, interfere, and reflect — all from your terminal.

## What It Does

The simulator models the **discrete 2D wave equation** on a grid:

```
u(t+1) = (2·u(t) - u(t-1) + c²·∇²u(t)) · damping
```

Each frame, every cell computes a Laplacian from its four neighbours, propagating disturbances outward at speed `c`. The damping factor slowly attenuates waves, simulating energy loss. Walls act as **reflective boundaries**, causing waves to bounce back and create interference patterns. Continuous wave sources emit periodic pulses, producing classic two-slit interference and standing wave patterns. An **absorbing boundary** mode reduces edge reflections for a more open-water feel.

## Features

### Physics & Simulation
- **Realistic wave physics** — proper discrete wave equation with configurable speed and damping
- **Per-instance wave speed** — each simulator stores its own speed, no shared global state
- **Reflective walls** — waves bounce off obstacles, creating interference patterns
- **Absorbing boundaries** — toggle with `B` to reduce reflections at grid edges
- **Continuous wave sources** — place persistent oscillating sources that emit pulses automatically
- **Double-slit interference** — built-in preset for the classic physics demonstration
- **Vortex pattern** — press `V` to drop 8 stones in a circular spiral for mesmerizing interference
- **Energy measurement** — press `E` to display total wave energy in the HUD
- **Adjustable damping** — press `+`/`-` to tune wave persistence in real time (clamped to 0.80–0.995)
- **Adjustable simulation speed** — press `[`/`]` to slow down or speed up the simulation
- **NaN/Inf protection** — wave values that become NaN or Inf are reset to 0.0 to prevent instability propagation
- **Extreme value clamping** — values exceeding ±1,000,000 are clamped to prevent exponential blowup

### Interactive Controls
- **Drop stones** — press `SPACE` for a random drop
- **Big drops** (`D`) — create large-amplitude disturbances
- **Interference demo** (`I`) — drop two symmetric stones for a classic interference pattern
- **Vortex demo** (`V`) — drop stones in a circular spiral pattern
- **Rain mode** (`R`) — automatic random drops for ambient wave patterns
- **Wall placement** (`W`) — add random wall segments that reflect waves
- **Preset wall patterns** (`P`) — cycle through rectangle, diamond, cross, circle, and double-slit presets
- **Wave sources** (`F`) — place/remove continuous oscillating wave sources
- **Color cycling** (`T`) — toggle animated color cycling mode
- **Boundary toggle** (`B`) — switch between reflective and absorbing edge boundaries
- **Energy display** (`E`) — show/hide total wave energy in the HUD
- **Save snapshot** (`S`) — save the current simulation state to a JSON file
- **Load snapshot** (`L`) — restore a previously saved simulation state
- **Reset** (`X`) — clear the simulation and start fresh

### Visuals
- **5 colour palettes** — Ocean, Lava, Toxic, Purple, Monochrome (keys `1`–`5`)
- **Color cycling mode** — smooth animated palette transitions
- **Wall rendering** — textured brick-pattern obstacle display
- **Source markers** — yellow indicators showing active wave sources
- **HUD display** — shows version, drop count, palette, damping, rain mode, sources, speed, wall preset, energy, boundary mode, and frame number

### Save & Load
- **Save state** (`S`) — writes the entire simulation (wave buffers, walls, sources, settings, UI flags) to `ripple_snapshot.json`
- **Load state** (`L`) — restores from `ripple_snapshot.json`, resuming exactly where you left off
- **CLI resume** (`--load FILE`) — start the simulator from a saved snapshot file
- **Portable format** — snapshots are human-readable JSON, easy to inspect or modify
- **Validation** — snapshot loading validates required fields, array lengths, and grid dimensions to prevent crashes from corrupted files
- **All state preserved** — boundary mode, show energy, color cycle, rain mode, sim speed, and palette are all saved and restored

### CLI Options
- **`--cols N`** — set grid width, minimum 3 (default: 72)
- **`--rows N`** — set grid height, minimum 3 (default: 28)
- **`--fps N`** — target frames per second, minimum 1 (default: 20)
- **`--palette N`** — initial colour palette 1–5 (default: 1)
- **`--speed C`** — wave propagation speed, clamped to 0.01–0.49 (default: 0.45)
- **`--damping D`** — wave damping factor, clamped to 0.0–1.0 (default: 0.96)
- **`--rain`** — start with rain mode enabled
- **`--absorbing`** — use absorbing boundary conditions (reduces edge reflections)
- **`--load FILE`** — load a snapshot from a JSON file to resume a previous session
- **`--energy`** — display total wave energy in the HUD
- **`--version`** — show version number (1.4.0)
- **`--help`** — show usage information

## How to Install

No external dependencies — uses only Python 3 standard library modules (`sys`, `time`, `random`, `math`, `argparse`, `select`, `tty`, `termios`, `json`, `os`).

```bash
# No installation needed, just run it
python3 ripple.py
```

> **Note:** For the best experience, run in a terminal that supports 24-bit ANSI color (most modern terminals do: iTerm2, Windows Terminal, Kitty, Alacritty, etc.).

## How to Run

```bash
cd ~/daily-ideas/2026-06-20-water-ripple-simulator
python3 ripple.py
```

### Run with Options

```bash
# Start with a wider grid and rain mode
python3 ripple.py --cols 100 --rows 35 --rain

# Start with the Lava palette and absorbing boundaries
python3 ripple.py --palette 2 --absorbing

# Slower wave speed for more dramatic visuals, with energy display
python3 ripple.py --speed 0.3 --damping 0.98 --energy

# Small grid for slower terminals
python3 ripple.py --cols 40 --rows 15

# Resume from a saved snapshot
python3 ripple.py --load ripple_snapshot.json
```

### Run Tests

```bash
python3 test_ripple.py
```

Press `Q` or `Escape` to quit the simulator.

## Controls

| Key | Action |
|-----|--------|
| `SPACE` | Drop a stone at a random position |
| `D` | Drop a big stone |
| `F` | Place/remove a continuous wave source |
| `I` | Interference demo (two symmetric drops) |
| `V` | Vortex demo (circular spiral of drops) |
| `R` | Toggle rain mode (auto-drops) |
| `P` | Cycle preset wall patterns |
| `T` | Toggle color-cycling mode |
| `W` | Add a random wall segment |
| `C` | Clear all walls |
| `X` | Reset water (clear simulation) |
| `E` | Toggle energy display in HUD |
| `B` | Toggle boundary mode (reflective / absorbing) |
| `S` | Save snapshot to JSON |
| `L` | Load snapshot from JSON |
| `+` / `-` | Increase / decrease damping |
| `[` / `]` | Decrease / increase simulation speed |
| `1`–`5` | Switch colour palette |
| `Q` / `Esc` | Quit |

## How It Works

1. **Wave Equation**: Each cell's next value is computed from its current value, previous value, and the Laplacian (sum of 4 neighbours minus 4× self). This is the standard finite-difference scheme for the 2D wave equation.

2. **Damping**: A per-frame multiplicative damping factor (default 0.96) gradually reduces amplitude, simulating viscous energy loss. Lower damping = faster decay; higher = longer-lasting waves. The damping property is now **clamped to [0.0, 1.0]** to prevent instability from values outside this range.

3. **Boundaries**: In **reflective** mode (default), boundary cells are held at zero, causing waves to bounce back. In **absorbing** mode, boundary cells use a first-order approximation that absorbs outgoing waves, reducing edge reflections.

4. **Walls**: Marked cells are held at zero amplitude. Waves reflect off walls because the zero boundary condition acts like a fixed endpoint, inverting the wave on reflection.

5. **Wave Sources**: Continuous sources emit a small drop every few frames, creating persistent oscillation patterns. Toggle them with `F`.

6. **Vortex**: The `V` key drops 8 stones in a circular arrangement, producing a striking spiral interference pattern.

7. **Energy**: Total energy (sum of squared amplitudes) can be displayed in the HUD with `E`, letting you observe wave decay and interference in real time.

8. **Snapshots**: Press `S` to save the full simulation state to `ripple_snapshot.json`. Press `L` to load it back. You can also start with `--load FILE` to resume from a saved state. **All UI state is preserved** — boundary mode, energy display, color cycling, rain mode, sim speed, and palette.

9. **Stability**: NaN and Inf values in the wave buffer are reset to 0.0 during each step to prevent cascading instability. Extreme values beyond ±1,000,000 are clamped to prevent exponential blowup even with unusual parameter settings.

10. **Rendering**: Wave height is mapped to 10 intensity levels (0–9), each assigned a color from the active palette. Unicode block characters provide visual density: ` ` (empty) through `█` (full block). NaN and Inf values are safely handled and rendered as mid-intensity.

11. **Speed**: Wave propagation speed is stored per-instance (not as a global), so multiple simulators can have different speeds. The CLI `--speed` flag clamps values to 0.01–0.49 to maintain CFL stability.

## Examples

```bash
# Start the simulator (drops one stone in the center automatically)
python3 ripple.py

# Double-slit interference demo
python3 ripple.py --palette 2
# Then press P until "Wall: double_slit" appears, then press I

# Ambient rain with color cycling and energy display
python3 ripple.py --rain --palette 3 --energy
# Then press T for color cycling

# Absorbing boundaries for an open-water feel
python3 ripple.py --absorbing

# Save a cool pattern, then resume it later
python3 ripple.py
# ... make some waves, press S to save ...
python3 ripple.py --load ripple_snapshot.json

# Run the test suite
python3 test_ripple.py
```

Try enabling rain mode (`R`), adding wave sources (`F`), pressing `V` for vortex patterns, and cycling wall presets (`P`) for the most visually interesting patterns!

## Changelog

### v1.4.0 — Bug Fixes & Robustness
- **Fixed: Damping not clamped on assignment** — `sim.damping = 1.5` previously caused exponential wave amplification and simulation blowup. Damping is now a property that clamps values to [0.0, 1.0].
- **Fixed: NaN/Inf propagation in wave simulation** — NaN and Inf values in the wave buffer previously propagated through the entire grid, eventually crashing the render. Now reset to 0.0 during each step.
- **Fixed: Extreme value blowup** — Wave values exceeding ±1,000,000 are now clamped to prevent exponential blowup from damping > 1.0 or numerical instability.
- **Fixed: Snapshot missing fields** — `save_snapshot` was missing `show_energy`, `color_cycle`, and `rain_mode`. These are now saved and restored properly.
- **Fixed: Load snapshot state loss** — The `L` key handler in the main loop was not transferring `boundary_mode`, `show_energy`, `color_cycle`, `rain_mode`, `sim_speed`, or `palette_id` from the loaded state. All fields are now properly transferred.
- **Fixed: Empty palette infinite loop** — `render_with_custom_palette([])` caused an infinite loop due to the `while len(palette) < 10` doubling strategy failing on empty lists. Empty palettes now fall back to the Ocean palette.
- **Fixed: Snapshot validation** — `load_snapshot` now validates required fields, checks array lengths match `cols × rows`, and rejects grids smaller than 3×3. Corrupted snapshots now raise `ValueError` instead of causing `IndexError` later.
- **Added: 14 new tests** — covering all bug fixes plus comprehensive snapshot round-trip validation. Total: 70 tests passing.

### v1.3.0 — New Features & Improvements
- **Absorbing boundary mode**: Press `B` to toggle between reflective and absorbing boundaries. Absorbing mode reduces edge reflections for a more natural open-water feel. CLI flag: `--absorbing`.
- **Vortex demo**: Press `V` to drop 8 stones in a circular spiral, creating mesmerizing interference patterns.
- **Energy display**: Press `E` to toggle total wave energy in the HUD. CLI flag: `--energy`.
- **Snapshot save/load**: Press `S` to save simulation state to JSON, `L` to load it back. Resume from CLI with `--load FILE`.
- **WaveSource serialization**: `WaveSource` objects now have `to_dict()`/`from_dict()` for full snapshot support.
- **Boundary mode constants**: `BOUNDARY_REFLECTIVE` and `BOUNDARY_ABSORBING` constants for clarity.
- **Improved comments**: Better docstrings on `apply_wall_preset()`, `drop_stone()`, `step()`, `total_energy()`, and the main loop.
- **Added 22 new tests**: vortex drop, total energy, energy decay, absorbing boundaries, boundary toggle, snapshot save/load, WaveSource serialization, CLI parser flags, version validation, and more.

### v1.2.0 — Bug Fixes
- Fixed NaN/Inf crash in `render()` and `render_with_custom_palette()`.
- Fixed short palette crash in `render_with_custom_palette()`.
- Fixed negative/zero grid dimensions raising `ValueError`.
- Fixed invalid CLI parameter validation.
- Fixed global `SPEED` mutability — now per-instance.
- Added damping validation in constructor.
- Added 7 new tests for edge cases.

### v1.0.0 — Initial Release
- Real-time 2D wave equation simulation in the terminal.
- 5 colour palettes with color cycling.
- Wall obstacles with 5 preset patterns.
- Continuous wave sources.
- Rain mode, interference demo.
- Adjustable damping and simulation speed.

## License

MIT