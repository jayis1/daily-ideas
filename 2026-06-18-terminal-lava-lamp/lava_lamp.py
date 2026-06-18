#!/usr/bin/env python3
"""
Terminal Lava Lamp — A mesmerizing ASCII lava lamp simulation with ANSI colors.

Blobs of wax rise and fall inside a lamp-shaped container, rendered in the terminal
using colored characters and simple physics simulation.
"""

import sys
import time
import random
import math
import signal

# ── ANSI helpers ──────────────────────────────────────────────────────────

def esc(code):
    return f"\033[{code}m"

def clear_screen():
    sys.stdout.write("\033[2J\033[H")

def hide_cursor():
    sys.stdout.write("\033[?25l")

def show_cursor():
    sys.stdout.write("\033[?25h")

def move_cursor(row, col):
    sys.stdout.write(f"\033[{row};{col}H")

# ── Color palette ─────────────────────────────────────────────────────────

# Lava lamp color themes
THEMES = {
    "classic": {
        "bg": (20, 10, 40),       # dark purple background
        "lamp": (60, 40, 80),     # lamp body outline
        "wax": [                   # wax blob colors (red/orange/yellow)
            (255, 60, 30),
            (255, 120, 20),
            (255, 180, 40),
            (255, 220, 100),
            (255, 100, 50),
            (240, 80, 30),
        ],
        "glow": (80, 30, 15),     # glow behind wax
    },
    "ocean": {
        "bg": (5, 15, 40),
        "lamp": (20, 50, 90),
        "wax": [
            (30, 180, 255),
            (80, 220, 255),
            (150, 240, 255),
            (200, 255, 255),
            (60, 200, 240),
            (40, 160, 220),
        ],
        "glow": (10, 40, 80),
    },
    "toxic": {
        "bg": (10, 25, 10),
        "lamp": (30, 60, 30),
        "wax": [
            (50, 255, 30),
            (120, 255, 60),
            (180, 255, 100),
            (200, 255, 180),
            (80, 240, 40),
            (40, 200, 20),
        ],
        "glow": (15, 50, 15),
    },
    "sunset": {
        "bg": (30, 10, 20),
        "lamp": (70, 30, 50),
        "wax": [
            (255, 50, 100),
            (255, 100, 150),
            (255, 150, 200),
            (255, 200, 230),
            (255, 80, 130),
            (230, 40, 90),
        ],
        "glow": (60, 15, 35),
    },
}

# Characters for rendering
BG_CHARS = " .·:;░▒"
WAX_CHARS = "●◉⬤◆▲★◉⬤●◆▲★"
GLOW_CHARS = " .:;░"

def rgb_to_ansi(r, g, b, fg=True):
    """Convert RGB to 24-bit ANSI color code."""
    code = 38 if fg else 48
    return f"\033[{code};2;{int(r)};{int(g)};{int(b)}m"

# ── Blob class ────────────────────────────────────────────────────────────

class Blob:
    """A wax blob in the lava lamp."""

    def __init__(self, lamp, theme_colors):
        self.lamp = lamp
        self.colors = theme_colors
        self.reset()

    def reset(self):
        self.y = random.uniform(0.7, 0.95)  # start near bottom
        self.x = random.uniform(0.3, 0.7)
        self.radius = random.uniform(0.04, 0.08)
        self.vy = 0.0
        self.phase = random.uniform(0, 2 * math.pi)
        self.color_idx = random.randint(0, len(self.colors) - 1)
        self.wobble_freq = random.uniform(1.5, 3.0)
        self.wobble_amp = random.uniform(0.01, 0.03)
        self.life = 0.0

    def update(self, dt, heat):
        """Update blob physics. heat is 0-1 representing lamp heat at this position."""
        self.life += dt

        # Buoyancy: hotter wax rises, cooler wax sinks
        # At bottom, heat is high → blob expands and rises
        # At top, heat is low → blob contracts and sinks
        target_vy = -0.15 + 0.3 * (1.0 - self.y)  # rises when low, sinks when high

        # Add some randomness
        target_vy += random.uniform(-0.02, 0.02)

        # Smooth velocity change
        self.vy += (target_vy - self.vy) * dt * 2.0
        self.y += self.vy * dt

        # Horizontal wobble
        self.x = 0.5 + self.wobble_amp * math.sin(self.life * self.wobble_freq + self.phase)
        # Add small random drift
        self.x += random.uniform(-0.005, 0.005)
        self.x = max(0.15, min(0.85, self.x))

        # Radius changes: expand when rising (hot), contract when sinking (cool)
        if self.vy < -0.02:  # rising
            self.radius = min(0.12, self.radius + dt * 0.02)
        elif self.vy > 0.02:  # sinking
            self.radius = max(0.03, self.radius - dt * 0.01)

        # Reset if out of bounds
        if self.y < -0.1 or self.y > 1.2:
            self.reset()

        # Color shifts slowly
        self.color_idx = (self.color_idx + random.uniform(-0.1, 0.1)) % len(self.colors)


# ── Lava Lamp ─────────────────────────────────────────────────────────────

class LavaLamp:
    """The main lava lamp simulation."""

    def __init__(self, width=40, height=30, theme="classic"):
        self.width = width
        self.height = height
        self.theme_name = theme
        self.theme = THEMES[theme]
        self.blobs = []
        self.time = 0.0

        # Create initial blobs
        for _ in range(8):
            blob = Blob(self, self.theme["wax"])
            self.blobs.append(blob)

        # Pre-compute lamp shape
        self._compute_shape()

    def _compute_shape(self):
        """Compute the lamp shape as a function of row (0=top, 1=bottom)."""
        # The lamp shape: narrow top cap, widens to a bowl, narrows at bottom
        # Returns width multiplier (0-1) for a given y position
        self.shape_points = []
        for i in range(self.height + 4):  # extra rows for cap and base
            y = i / (self.height + 3)
            w = self._shape_width(y)
            self.shape_points.append(w)

    def _shape_width(self, y):
        """Return relative width (0-1) of the lamp at position y (0=top, 1=bottom)."""
        # Cap (top): y=0..0.08
        if y < 0.05:
            return 0.15 + 0.2 * (y / 0.05)
        # Neck transition: y=0.05..0.15
        elif y < 0.15:
            t = (y - 0.05) / 0.1
            return 0.35 + 0.4 * t
        # Main body: y=0.15..0.75 (widest)
        elif y < 0.75:
            t = (y - 0.15) / 0.6
            # Gentle curve
            return 0.75 + 0.15 * math.sin(t * math.pi)
        # Lower body narrowing: y=0.75..0.88
        elif y < 0.88:
            t = (y - 0.75) / 0.13
            return 0.75 - 0.35 * t
        # Base: y=0.88..1.0
        else:
            t = (y - 0.88) / 0.12
            return 0.4 + 0.1 * t

    def _y_to_row(self, y):
        """Convert normalized y (0=top, 1=bottom) to screen row."""
        # Reserve top 2 rows for cap, bottom 2 for base
        return int(2 + y * (self.height - 1))

    def _row_to_y(self, row):
        """Convert screen row to normalized y."""
        return (row - 2) / (self.height - 1)

    def update(self, dt):
        self.time += dt
        for blob in self.blobs:
            blob.update(dt, 1.0 - blob.y)  # heat is stronger at bottom

    def render(self):
        """Render the lava lamp to a string buffer."""
        lines = []

        bg = self.theme["bg"]
        lamp_c = self.theme["lamp"]
        glow_c = self.theme["glow"]

        for row in range(self.height):
            y = self._row_to_y(row)
            lamp_w = self._shape_width(y)

            # Compute center and edges
            center = self.width // 2
            half_w = int(lamp_w * self.width / 2)
            left = center - half_w
            right = center + half_w

            line = ""
            for col in range(self.width):
                # Check if inside lamp
                if left <= col <= right:
                    # Compute blob influence at this pixel
                    bx = (col - left) / max(1, right - left)  # 0..1 within lamp
                    by = y

                    # Compute combined blob density
                    density = 0.0
                    blob_colors_r, blob_colors_g, blob_colors_b = 0.0, 0.0, 0.0
                    glow = 0.0

                    for blob in self.blobs:
                        # Map blob position to screen coordinates
                        blob_screen_x = blob.x  # 0..1 across lamp width
                        blob_screen_y = blob.y  # 0=top, 1=bottom

                        # Distance from blob center
                        dx = bx - blob_screen_x
                        dy = by - blob_screen_y
                        dist = math.sqrt(dx * dx * 4 + dy * dy)  # squish horizontally

                        # Blob influence (smooth falloff)
                        r = blob.radius
                        if dist < r * 3:
                            # Core of blob
                            core = max(0, 1.0 - dist / r)
                            core = core * core  # sharpen
                            density += core
                            c = blob.colors[int(blob.color_idx) % len(blob.colors)]
                            blob_colors_r += c[0] * core
                            blob_colors_g += c[1] * core
                            blob_colors_b += c[2] * core

                            # Glow around blob
                            glow += max(0, 1.0 - dist / (r * 3)) * 0.5

                    # Near edges: darken slightly
                    edge_dist = min(bx - 0, 1 - bx)
                    edge_fade = min(1.0, edge_dist * 8)

                    if density > 0.05:
                        # Wax color
                        fr = min(255, blob_colors_r / density)
                        fg_c = min(255, blob_colors_g / density)
                        fb = min(255, blob_colors_b / density)

                        # Blend with background based on density
                        alpha = min(1.0, density)
                        alpha *= edge_fade

                        # Blend
                        r = int(bg[0] * (1 - alpha) + fr * alpha)
                        g = int(bg[1] * (1 - alpha) + fg_c * alpha)
                        b = int(bg[2] * (1 - alpha) + fb * alpha)

                        # Pick character based on density
                        idx = min(len(WAX_CHARS) - 1, int(density * len(WAX_CHARS)))
                        ch = WAX_CHARS[idx]

                        line += rgb_to_ansi(r, g, b) + rgb_to_ansi(r, g, b, fg=False) + ch + esc(0)
                    elif glow > 0.05:
                        # Glow around wax
                        alpha = min(1.0, glow) * edge_fade
                        r = int(bg[0] * (1 - alpha) + glow_c[0] * alpha)
                        g = int(bg[1] * (1 - alpha) + glow_c[1] * alpha)
                        b = int(bg[2] * (1 - alpha) + glow_c[2] * alpha)

                        idx = min(len(GLOW_CHARS) - 1, int(glow * len(GLOW_CHARS)))
                        ch = GLOW_CHARS[idx]

                        line += rgb_to_ansi(r, g, b) + rgb_to_ansi(r, g, b, fg=False) + ch + esc(0)
                    else:
                        # Inside lamp, no blob
                        # Slight color variation for depth
                        depth = 0.5 + 0.5 * math.sin((bx - 0.5) * math.pi)
                        r = int(bg[0] * (1 - depth * 0.3) + lamp_c[0] * depth * 0.3)
                        g = int(bg[1] * (1 - depth * 0.3) + lamp_c[1] * depth * 0.3)
                        b = int(bg[2] * (1 - depth * 0.3) + lamp_c[2] * depth * 0.3)

                        line += rgb_to_ansi(r, g, b) + " " + esc(0)
                elif col == left - 1 or col == right + 1:
                    # Lamp outline
                    line += rgb_to_ansi(lamp_c[0] + 60, lamp_c[1] + 40, lamp_c[2] + 60) + "│" + esc(0)
                else:
                    # Outside lamp — dark background
                    line += rgb_to_ansi(bg[0], bg[1], bg[2]) + " " + esc(0)

            lines.append(line)

        # Add base
        base_line = ""
        center = self.width // 2
        for col in range(self.width):
            if abs(col - center) < 8:
                base_line += rgb_to_ansi(lamp_c[0] + 40, lamp_c[1] + 20, lamp_c[2] + 40) + "▀" + esc(0)
            elif abs(col - center) < 10:
                base_line += rgb_to_ansi(lamp_c[0] + 20, lamp_c[1] + 10, lamp_c[2] + 20) + "▀" + esc(0)
            else:
                base_line += rgb_to_ansi(bg[0], bg[1], bg[2]) + " " + esc(0)
        lines.append(base_line)

        # Add cap
        cap_line = ""
        for col in range(self.width):
            if abs(col - center) < 4:
                cap_line += rgb_to_ansi(lamp_c[0] + 60, lamp_c[1] + 40, lamp_c[2] + 60) + "▄" + esc(0)
            elif abs(col - center) < 6:
                cap_line += rgb_to_ansi(lamp_c[0] + 30, lamp_c[1] + 20, lamp_c[2] + 30) + "▄" + esc(0)
            else:
                cap_line += rgb_to_ansi(bg[0], bg[1], bg[2]) + " " + esc(0)

        # Insert cap at top
        lines.insert(0, cap_line)

        # Title
        title = f"✦ {self.theme_name.upper()} LAVA LAMP ✦"
        title_line = rgb_to_ansi(180, 180, 200) + title.center(self.width) + esc(0)

        return "\n".join([title_line, ""] + lines)


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    theme = "classic"
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in THEMES:
            theme = arg
        elif arg in ("-h", "--help"):
            print("Usage: lava_lamp.py [THEME]")
            print(f"Themes: {', '.join(THEMES.keys())}")
            print("\nControls:")
            print("  Ctrl+C — Quit")
            print("  1-4    — Switch theme (classic, ocean, toxic, sunset)")
            sys.exit(0)
        else:
            print(f"Unknown theme '{arg}'. Available: {', '.join(THEMES.keys())}")
            sys.exit(1)

    # Detect terminal size
    try:
        cols, rows = os.get_terminal_size()
    except:
        cols, rows = 44, 34

    width = max(30, min(60, cols - 4))
    height = max(20, min(40, rows - 6))

    lamp = LavaLamp(width=width, height=height, theme=theme)

    clear_screen()
    hide_cursor()

    running = True

    def handle_sigint(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_sigint)

    last_time = time.time()
    fps_target = 15
    frame_time = 1.0 / fps_target

    try:
        while running:
            now = time.time()
            dt = now - last_time
            last_time = now

            # Update simulation
            lamp.update(min(dt, 0.1))

            # Render
            output = lamp.render()
            move_cursor(1, 1)
            sys.stdout.write(output)
            sys.stdout.write("\n" + rgb_to_ansi(120, 120, 140) + "  [1-4] themes  [q]uit".ljust(width) + esc(0))
            sys.stdout.flush()

            # Check for keypress (non-blocking)
            import select
            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1)
                if key == 'q':
                    break
                elif key == '1':
                    lamp = LavaLamp(width=width, height=height, theme="classic")
                elif key == '2':
                    lamp = LavaLamp(width=width, height=height, theme="ocean")
                elif key == '3':
                    lamp = LavaLamp(width=width, height=height, theme="toxic")
                elif key == '4':
                    lamp = LavaLamp(width=width, height=height, theme="sunset")

            # Frame rate limiting
            elapsed = time.time() - now
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)

    except Exception as e:
        pass
    finally:
        show_cursor()
        move_cursor(height + 5, 1)
        print(rgb_to_ansi(180, 180, 200) + "✦ Lava lamp powered off ✦" + esc(0))


import os

if __name__ == "__main__":
    main()