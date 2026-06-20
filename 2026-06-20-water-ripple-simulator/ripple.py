#!/usr/bin/env python3
"""
Terminal Water Ripple Simulator
===============================
A real-time 2D wave equation simulator rendered in the terminal using Unicode
block characters. Drop stones, watch waves propagate, interfere, and reflect
off walls. Uses the discrete wave equation with damping.

Controls:
  - Click:  Press a letter key to drop a stone at that position
  - SPACE:  Drop a stone at a random position
  - R:      Rain mode (auto-drops)
  - D:      Drop a big stone
  - W:      Drop a wall/obstacle
  - C:      Clear all walls
  - X:      Clear water (reset simulation)
  - +/-:    Increase/decrease damping
  - 1-5:    Change color scheme
  - Q/Esc:  Quit
"""

import sys
import time
import random
import math

# ---------------------------------------------------------------------------
# Grid dimensions (character cells)
# ---------------------------------------------------------------------------
COLS = 72
ROWS = 28

# ---------------------------------------------------------------------------
# Wave equation parameters
# ---------------------------------------------------------------------------
SPEED = 0.45          # wave propagation speed (0 < c < 0.5 for stability)
DAMPING_DEFAULT = 0.96  # velocity damping per frame (0-1)
FPS = 20

# ---------------------------------------------------------------------------
# Color palettes: list of (r, g, b) tuples indexed by intensity 0..9
# ---------------------------------------------------------------------------
PALETTES = {
    1: [  # Ocean
        (0, 0, 30), (0, 5, 60), (0, 15, 100), (0, 30, 140),
        (0, 60, 170), (10, 100, 190), (40, 150, 210), (100, 200, 230),
        (180, 230, 245), (240, 250, 255),
    ],
    2: [  # Lava
        (20, 0, 0), (60, 0, 0), (110, 10, 0), (160, 30, 0),
        (210, 60, 0), (240, 100, 0), (255, 150, 20), (255, 200, 60),
        (255, 230, 120), (255, 255, 200),
    ],
    3: [  # Toxic
        (0, 15, 0), (0, 30, 5), (0, 50, 10), (0, 80, 15),
        (0, 120, 20), (20, 160, 30), (60, 200, 50), (120, 230, 80),
        (180, 245, 130), (230, 255, 200),
    ],
    4: [  # Purple
        (10, 0, 20), (25, 0, 50), (50, 5, 90), (80, 15, 130),
        (120, 30, 165), (155, 55, 195), (185, 90, 215), (210, 140, 230),
        (230, 195, 242), (248, 235, 255),
    ],
    5: [  # Monochrome
        (8, 8, 8), (20, 20, 20), (38, 38, 38), (60, 60, 60),
        (90, 90, 90), (120, 120, 120), (155, 155, 155), (195, 195, 195),
        (225, 225, 225), (255, 255, 255),
    ],
}

# Unicode block characters ordered by visual density
BLOCK_CHARS = " ░▒▓█"


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class RippleSimulator:
    """2D wave equation simulation with terminal rendering."""

    def __init__(self, cols=COLS, rows=ROWS):
        self.cols = cols
        self.rows = rows
        n = cols * rows

        # Two buffers for the wave equation (current and previous)
        self.current = [0.0] * n
        self.previous = [0.0] * n

        # Walls / obstacles
        self.walls = [False] * n

        self.damping = DAMPING_DEFAULT
        self.palette_id = 1
        self.rain_mode = False
        self.rain_timer = 0
        self.frame = 0
        self.drop_count = 0
        self.wall_mode = False
        self.wall_start = None

    # ------------------------------------------------------------------
    # Wave simulation
    # ------------------------------------------------------------------

    def idx(self, x, y):
        return y * self.cols + x

    def in_bounds(self, x, y):
        return 0 <= x < self.cols and 0 <= y < self.rows

    def drop_stone(self, cx, cy, radius=2, amplitude=8.0):
        """Create a circular disturbance centred at (cx, cy)."""
        r2 = radius * radius
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = cx + dx, cy + dy
                if not self.in_bounds(nx, ny):
                    continue
                i = self.idx(nx, ny)
                if self.walls[i]:
                    continue
                dist2 = dx * dx + dy * dy
                if dist2 <= r2:
                    falloff = 1.0 - dist2 / (r2 + 1)
                    self.current[i] += amplitude * falloff
        self.drop_count += 1

    def step(self):
        """Advance the simulation by one time step using the discrete wave equation."""
        c2 = SPEED * SPEED
        damping = self.damping
        cols = self.cols
        cur = self.current
        prev = self.previous
        walls = self.walls
        rows = self.rows

        next_buf = [0.0] * (cols * rows)

        for y in range(1, rows - 1):
            row_off = y * cols
            for x in range(1, cols - 1):
                i = row_off + x
                if walls[i]:
                    # Reflect: wall cells stay 0 but neighbours bounce
                    next_buf[i] = 0.0
                    continue

                laplacian = (
                    cur[i - 1] + cur[i + 1] +
                    cur[i - cols] + cur[i + cols] -
                    4.0 * cur[i]
                )
                next_buf[i] = (2.0 * cur[i] - prev[i] + c2 * laplacian) * damping

        self.previous = cur
        self.current = next_buf
        self.frame += 1

    def clear_water(self):
        n = self.cols * self.rows
        self.current = [0.0] * n
        self.previous = [0.0] * n
        self.frame = 0
        self.drop_count = 0

    def clear_walls(self):
        self.walls = [False] * (self.cols * self.rows)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self):
        """Return a list of strings (one per row) with ANSI-coloured block characters."""
        palette = PALETTES[self.palette_id]
        lines = []
        cur = self.current
        walls = self.walls
        cols = self.cols

        # Build a quick mapping of intensity -> color string
        # Intensity is 0..9
        colors = []
        for i in range(10):
            r, g, b = palette[i]
            colors.append(f"\033[38;2;{r};{g};{b}m")

        reset = "\033[0m"
        wall_color = "\033[38;2;180;140;100m"

        for y in range(self.rows):
            row_off = y * cols
            line_parts = []
            x = 0
            while x < cols:
                i = row_off + x
                if walls[i]:
                    # Render wall with a brick-like pattern
                    if (x + y) % 3 == 0:
                        line_parts.append(f"{wall_color}▓{reset}")
                    elif (x + y) % 3 == 1:
                        line_parts.append(f"{wall_color}▒{reset}")
                    else:
                        line_parts.append(f"{wall_color}░{reset}")
                    x += 1
                else:
                    val = cur[i]
                    # Map wave height to intensity 0..9
                    # Clamp to reasonable range
                    intensity = clamp(int((val + 4.0) / 8.0 * 9), 0, 9)
                    ch = BLOCK_CHARS[intensity // 2] if intensity < 9 else BLOCK_CHARS[min(intensity // 2, 4)]
                    # Better mapping: use half-block chars for mid range
                    if intensity <= 1:
                        ch = " "
                    elif intensity <= 3:
                        ch = "░"
                    elif intensity <= 5:
                        ch = "▒"
                    elif intensity <= 7:
                        ch = "▓"
                    else:
                        ch = "█"
                    line_parts.append(f"{colors[intensity]}{ch}")
                    x += 1
            lines.append("".join(line_parts))

        return lines


def main():
    # Check if terminal supports ANSI
    sim = RippleSimulator()

    # Hide cursor
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    CLEAR = "\033[2J\033[H"

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()

    # Set up terminal for raw input
    old_settings = None
    try:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setraw(fd)
    except (ImportError, termios.error):
        pass  # Not a real terminal (e.g., piped)

    def restore():
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()
        if old_settings is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass

    # Initial splash: drop a stone in the center
    sim.drop_stone(sim.cols // 2, sim.rows // 2, radius=3, amplitude=10.0)

    try:
        while True:
            # --- Input ---
            ch = None
            try:
                import select
                if select.select([sys.stdin], [], [], 0)[0]:
                    ch = sys.stdin.read(1)
                    if ch == '\x1b':  # ESC sequence
                        ch2 = sys.stdin.read(1) if select.select([sys.stdin], [], [], 0.01)[0] else ''
                        if ch2 == '[':
                            ch3 = sys.stdin.read(1) if select.select([sys.stdin], [], [], 0.01)[0] else ''
                            # Arrow keys etc — ignore for now
                            ch = None
                        elif ch2 == '':
                            ch = 'q'  # bare ESC
                        else:
                            ch = None
            except Exception:
                pass

            if ch in ('q', 'Q', '\x1b'):
                break
            elif ch == ' ':
                x = random.randint(2, sim.cols - 3)
                y = random.randint(2, sim.rows - 3)
                sim.drop_stone(x, y, radius=random.randint(1, 3), amplitude=random.uniform(5, 12))
            elif ch == 'd' or ch == 'D':
                x = random.randint(4, sim.cols - 5)
                y = random.randint(4, sim.rows - 5)
                sim.drop_stone(x, y, radius=5, amplitude=15.0)
            elif ch == 'r' or ch == 'R':
                sim.rain_mode = not sim.rain_mode
            elif ch == 'w' or ch == 'W':
                # Toggle a wall at a random position
                wx = random.randint(3, sim.cols - 4)
                wy = random.randint(3, sim.rows - 4)
                # Make a small wall segment
                if random.random() < 0.5:
                    for dx in range(-2, 3):
                        if sim.in_bounds(wx + dx, wy):
                            sim.walls[sim.idx(wx + dx, wy)] = True
                else:
                    for dy in range(-2, 3):
                        if sim.in_bounds(wx, wy + dy):
                            sim.walls[sim.idx(wx, wy + dy)] = True
            elif ch == 'c' or ch == 'C':
                sim.clear_walls()
            elif ch == 'x' or ch == 'X':
                sim.clear_water()
            elif ch == '+' or ch == '=':
                sim.damping = min(0.995, sim.damping + 0.01)
            elif ch == '-' or ch == '_':
                sim.damping = max(0.80, sim.damping - 0.01)
            elif ch in '12345':
                sim.palette_id = int(ch)
            elif ch and ch.isalpha():
                # Map letter to position on grid
                alpha_idx = ord(ch.upper()) - ord('A')
                total_cells = sim.cols * sim.rows
                # Spread letters across the grid
                target = int(alpha_idx / 26.0 * total_cells * 0.8 + total_cells * 0.1)
                target = clamp(target, 0, total_cells - 1)
                y = target // sim.cols
                x = target % sim.cols
                if sim.in_bounds(x, y):
                    sim.drop_stone(x, y, radius=random.randint(2, 4), amplitude=random.uniform(8, 14))

            # --- Rain mode ---
            if sim.rain_mode:
                sim.rain_timer += 1
                if sim.rain_timer % 4 == 0:
                    x = random.randint(2, sim.cols - 3)
                    y = random.randint(2, sim.rows - 3)
                    sim.drop_stone(x, y, radius=random.randint(1, 2), amplitude=random.uniform(3, 8))

            # --- Simulate ---
            sim.step()

            # --- Render ---
            lines = sim.render()
            palette_names = {1: "Ocean", 2: "Lava", 3: "Toxic", 4: "Purple", 5: "Mono"}
            hud = (
                f"  🌊 Water Ripple Simulator  │  "
                f"Drops: {sim.drop_count}  │  "
                f"Palette: {palette_names[sim.palette_id]}  │  "
                f"Damping: {sim.damping:.2f}  │  "
                f"Rain: {'ON' if sim.rain_mode else 'OFF'}  │  "
                f"Frame: {sim.frame}"
            )
            controls = (
                "  [SPACE] drop  [D] big drop  [R] rain  [W] wall  "
                "[C] clear walls  [X] reset  [+/-] damping  [1-5] palette  [Q] quit"
            )

            output = CLEAR
            output += "\033[38;2;100;180;220m" + hud + "\033[0m\n"
            for line in lines:
                output += line + "\n"
            output += "\033[38;2;140;140;140m" + controls + "\033[0m"

            sys.stdout.write(output)
            sys.stdout.flush()

            time.sleep(1.0 / FPS)

    except KeyboardInterrupt:
        pass
    finally:
        restore()
        sys.stdout.write(CLEAR + "Thanks for making waves! 🌊\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()