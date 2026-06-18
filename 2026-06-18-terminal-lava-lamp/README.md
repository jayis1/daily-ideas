# 🫧 Terminal Lava Lamp

A mesmerizing ASCII lava lamp simulation that runs in your terminal, featuring colored wax blobs that rise and fall inside a lamp-shaped container using simple physics. Rendered with 24-bit ANSI colors and Unicode characters for a retro-yet-vibrant look.

![Terminal Lava Lamp](https://img.shields.io/badge/terminal-lava%20lamp-purple)

## Features

- **Realistic blob physics** — Wax blobs expand when heated (rising) and contract when cooled (sinking), with smooth velocity transitions and horizontal wobble
- **4 color themes** — Classic (red/orange), Ocean (blue/cyan), Toxic (green), and Sunset (pink/red)
- **Live theme switching** — Press 1-4 to swap themes while running
- **Adaptive sizing** — Automatically fits your terminal window
- **24-bit color** — Uses true-color ANSI codes for smooth gradient rendering
- **Glow effects** — Soft halos around wax blobs fade into the background
- **Lamp-shaped container** — The wax is contained within a rendered lamp outline with cap and base

## How to Install

Requires Python 3.6+ (no external dependencies — uses only the standard library):

```bash
git clone <repo-url>
cd 2026-06-18-terminal-lava-lamp
```

Or just copy `lava_lamp.py` — it's a single self-contained file.

## How to Run

```bash
python3 lava_lamp.py           # Classic theme (default)
python3 lava_lamp.py ocean     # Ocean theme
python3 lava_lamp.py toxic     # Toxic theme
python3 lava_lamp.py sunset    # Sunset theme
python3 lava_lamp.py --help    # Show help
```

**Requires a terminal that supports 24-bit (true-color) ANSI codes** — most modern terminals (iTerm2, Windows Terminal, kitty, Alacritty, GNOME Terminal) support this.

## Controls

| Key | Action |
|-----|--------|
| `1` | Switch to Classic theme (red/orange) |
| `2` | Switch to Ocean theme (blue/cyan) |
| `3` | Switch to Toxic theme (green) |
| `4` | Switch to Sunset theme (pink) |
| `q` | Quit |
| `Ctrl+C` | Quit |

## How It Works

1. **Blob physics**: Each blob has position, velocity, and radius. Buoyancy drives blobs upward at the bottom and downward at the top, creating the classic rise-and-fall cycle. Blobs expand when rising (heated wax) and contract when sinking (cooled wax).

2. **Rendering**: For each pixel inside the lamp, the renderer calculates the combined "density" from all nearby blobs using smooth distance falloff. High-density areas get vivid wax colors and solid Unicode characters; medium areas get a soft glow; and empty areas show the dark interior.

3. **Lamp shape**: The container is defined by a parametric width function — narrow at the top cap, widening through the body, and narrowing again at the base — giving the classic lava lamp silhouette.

4. **Color blending**: All colors are computed as RGB blends using 24-bit ANSI escape codes, producing smooth gradients without the banding typical of 256-color mode.

## Usage Examples

```
$ python3 lava_lamp.py classic
  ✦ CLASSIC LAVA LAMP ✦

         ▄▄▄▄▄▄▄▄▄▄▄
      │  ░░░████████░░░  │
      │  ░░██████████░░  │
      │     ░░████░░     │
      │        ░░        │
      │  ░░░████████░░░  │
      │  ██████████████  │
      │  ██████████████  │
         ▀▀▀▀▀▀▀▀▀▀▀

  [1-4] themes  [q]uit
```

Run it full-screen in your terminal for the full experience — the colors and movement are quite hypnotic!