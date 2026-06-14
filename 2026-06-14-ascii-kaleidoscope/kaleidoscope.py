#!/usr/bin/env python3
"""
ASCII Kaleidoscope — Mesmerizing symmetric patterns in your terminal.

Generates real-time kaleidoscope patterns using Unicode block characters
and ANSI 256-color mode. Patterns are computed in a triangular wedge and
then mirrored across multiple axes of symmetry to create the kaleidoscope
effect.
"""

import sys
import os
import math
import time
import signal
import random
from collections import namedtuple

# ── ANSI helpers ──────────────────────────────────────────────────────────

ESC = "\033"
CSI = f"{ESC}["

def clear_screen():
    return f"{CSI}2J{CSI}H"

def hide_cursor():
    return f"{CSI}?25l"

def show_cursor():
    return f"{CSI}?25h"

def move_cursor(row, col):
    return f"{CSI}{row};{col}H"

def fg_color_256(n):
    return f"{CSI}38;5;{n}m"

def bg_color_256(n):
    return f"{CSI}48;5;{n}m"

RESET = f"{CSI}0m"

# ── Unicode block characters for pixel-like rendering ────────────────────

# Each block char has a "fill" ratio. We use these to simulate brightness.
BLOCK_CHARS = [
    " ",    # 0/8 fill
    "▁",    # 1/8
    "▂",    # 2/8
    "▃",    # 3/8
    "▄",    # 4/8
    "▅",    # 5/8
    "▆",    # 6/8
    "█",    # 7/8 full
]

# ── Color palette generation ─────────────────────────────────────────────

def generate_palette(hue_offset=0.0):
    """Generate a smooth 256-color ANSI palette cycling through hues."""
    colors = []
    for i in range(256):
        t = (i / 256.0) * 2 * math.pi + hue_offset
        # Map to ANSI 256-color cube (indices 16-231 are the 6x6x6 cube)
        r = int((math.sin(t) * 0.5 + 0.5) * 5)
        g = int((math.sin(t + 2.094) * 0.5 + 0.5) * 5)
        b = int((math.sin(t + 4.189) * 0.5 + 0.5) * 5)
        ansi = 16 + 36 * r + 6 * g + b
        colors.append(ansi)
    return colors

# ── Kaleidoscope engine ──────────────────────────────────────────────────

class Kaleidoscope:
    """
    Core kaleidoscope engine.

    The idea: compute a pattern in a single triangular wedge, then mirror
    it across N axes of symmetry to fill a circular viewport.
    """

    def __init__(self, segments=8, speed=1.0, pattern="spiral"):
        self.segments = segments  # Must be even for proper mirroring
        self.speed = speed
        self.pattern = pattern
        self.time = 0.0
        self.seed = random.randint(0, 999999)
        self.rng = random.Random(self.seed)
        self.palette_offset = 0.0

        # Pattern-specific params (randomized per session)
        self.freq1 = self.rng.uniform(2, 5)
        self.freq2 = self.rng.uniform(3, 7)
        self.freq3 = self.rng.uniform(1, 4)
        self.phase1 = self.rng.uniform(0, 2 * math.pi)
        self.phase2 = self.rng.uniform(0, 2 * math.pi)
        self.phase3 = self.rng.uniform(0, 2 * math.pi)
        self.morph_speed = self.rng.uniform(0.3, 1.2)

    def compute_pixel(self, r, theta, t):
        """Compute the color value for a point in polar coordinates."""
        s = self.speed

        if self.pattern == "spiral":
            val = math.sin(r * self.freq1 - theta * 3 + t * s)
            val += math.sin(r * self.freq2 + theta * 2 - t * s * 0.7)
            val += math.sin(r * self.freq3 * 0.5 + t * s * 0.3)

        elif self.pattern == "ripple":
            val = math.sin(r * self.freq1 * 2 + t * s)
            val += math.cos(r * self.freq2 * 1.5 - t * s * 0.5)
            val += math.sin(theta * self.freq3 + t * s * 0.8) * 0.5

        elif self.pattern == "crystal":
            # Creates crystal-like facets
            angle_mod = math.fmod(theta * self.freq1 + t * s * 0.2, math.pi / 3)
            val = math.sin(r * self.freq2 + angle_mod * 3)
            val += math.cos(r * 2 - t * s * 0.4) * 0.7
            val += math.sin(theta * self.freq3 + t * s * 0.6) * 0.4

        elif self.pattern == "flower":
            # Petal-like patterns
            petal = math.cos(theta * 6 + t * s * 0.3) * 0.5 + 0.5
            val = math.sin(r * self.freq1 * petal + t * s)
            val += math.cos(r * self.freq2 - t * s * 0.5) * 0.6
            val *= (petal + 0.3)

        elif self.pattern == "mandala":
            # Sacred geometry style
            ring = math.sin(r * self.freq1 * 2 + t * s * 0.3)
            spoke = math.cos(theta * self.freq2 * 2 + t * s * 0.2)
            pulse = math.sin(r * self.freq3 - t * s * 0.5)
            val = ring + spoke * 0.6 + pulse * 0.4

        elif self.pattern == "wave":
            # Ocean wave patterns
            wave1 = math.sin(r * self.freq1 + theta * 2 + t * s)
            wave2 = math.cos(r * self.freq2 - theta * 1.5 + t * s * 0.7)
            val = wave1 + wave2 + math.sin(theta * 3 + t * s * 0.4) * 0.3

        else:  # fallback
            val = math.sin(r * 3 + theta * 2 + t)

        # Normalize to 0..1
        val = (val + 3) / 6.0
        return max(0.0, min(1.0, val))

    def render_frame(self, width, height):
        """
        Render one frame of the kaleidoscope into a grid of (char, color_idx).

        Each cell is rendered as a half-block character (upper/lower), so
        each terminal row actually holds 2 pixel rows.
        """
        rows = height
        cols = width
        cx = cols / 2.0
        cy = rows / 2.0
        max_r = min(cx, cy) * 0.92  # Keep within circle
        t = self.time

        # We'll compute full pixel grid (2x rows for half-block chars)
        pixel_rows = rows * 2
        grid = [[0.0] * cols for _ in range(pixel_rows)]

        half_segments = self.segments // 2
        seg_angle = math.pi / half_segments

        palette = generate_palette(self.palette_offset)

        for py in range(pixel_rows):
            for px in range(cols):
                dx = (px - cx)
                dy = (py - cy)
                r = math.sqrt(dx * dx + dy * dy)

                if r > max_r or r < 0.5:
                    continue

                theta = math.atan2(dy, dx)
                if theta < 0:
                    theta += 2 * math.pi

                # Mirror: fold theta into first segment
                segment_idx = int(theta / seg_angle)
                theta_in_seg = theta - segment_idx * seg_angle

                # Every other segment is mirrored
                if segment_idx % 2 == 1:
                    theta_in_seg = seg_angle - theta_in_seg

                val = self.compute_pixel(r / max_r, theta_in_seg, t)
                grid[py][px] = val

        # Convert grid to (char, color) pairs for half-block rendering
        result = []
        for row in range(rows):
            row_data = []
            for col in range(cols):
                upper_val = grid[row * 2][col]
                lower_val = grid[row * 2 + 1][col]

                # Determine which block character to use based on upper/lower
                if upper_val > lower_val:
                    # Upper half block ▀ — foreground color = upper, bg = lower
                    char = "▀"
                    fg_idx = int(upper_val * 255)
                    bg_idx = int(lower_val * 255)
                else:
                    # Lower half block ▄ — foreground color = lower, bg = upper
                    char = "▄"
                    fg_idx = int(lower_val * 255)
                    bg_idx = int(upper_val * 255)

                fg_idx = max(0, min(255, fg_idx))
                bg_idx = max(0, min(255, bg_idx))

                fg = palette[fg_idx]
                bg = palette[bg_idx]

                row_data.append((char, fg, bg))
            result.append(row_data)

        self.time += 0.05 * self.speed
        self.palette_offset += 0.002 * self.speed
        return result

# ── Pattern names ────────────────────────────────────────────────────────

PATTERNS = ["spiral", "ripple", "crystal", "flower", "mandala", "wave"]

# ── Main loop ────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ASCII Kaleidoscope")
    parser.add_argument("-s", "--segments", type=int, default=8,
                        help="Number of symmetry segments (default: 8)")
    parser.add_argument("-p", "--pattern", type=str, default=None,
                        choices=PATTERNS,
                        help="Pattern type (default: random)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Animation speed multiplier (default: 1.0)")
    args = parser.parse_args()

    segments = max(4, args.segments)
    if segments % 2 != 0:
        segments += 1

    pattern = args.pattern or random.choice(PATTERNS)

    # Get terminal size
    try:
        cols = os.get_terminal_size().columns
        rows = os.get_terminal_size().lines
    except OSError:
        cols, rows = 80, 24

    # Leave room for info line
    rows -= 2
    cols = min(cols, 120)
    rows = min(rows, 50)

    ks = Kaleidoscope(segments=segments, speed=args.speed, pattern=pattern)

    running = True
    paused = False

    def handle_sigint(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_sigint)

    buffer = clear_screen() + hide_cursor()

    # Render info
    info = f"  ✦ ASCII Kaleidoscope — pattern: {pattern} | segments: {segments} | speed: {args.speed:.1f}x | [q]uit [r]andom [space]pause [+/-]speed"

    try:
        sys.stdout.write(buffer)
        sys.stdout.flush()

        frame_count = 0

        while running:
            if not paused:
                frame = ks.render_frame(cols, rows)

                output = []
                output.append(move_cursor(1, 1))

                for row_idx, row in enumerate(frame):
                    line = ""
                    prev_fg = -1
                    prev_bg = -1
                    for char, fg, bg in row:
                        if fg != prev_fg or bg != prev_bg:
                            line += fg_color_256(fg) + bg_color_256(bg) + char
                            prev_fg = fg
                            prev_bg = bg
                        else:
                            line += char
                    line += RESET
                    output.append(line)

                output.append(move_cursor(rows + 2, 1) + RESET + info)
                sys.stdout.write("\n".join(output) + "\n")
                sys.stdout.flush()
                frame_count += 1

            # Check for keypresses (non-blocking)
            import select
            if select.select([sys.stdin], [], [], 0.02)[0]:
                key = sys.stdin.read(1)
                if key == 'q' or key == '\x03':
                    running = False
                elif key == ' ':
                    paused = not paused
                elif key == 'r':
                    pattern = random.choice(PATTERNS)
                    ks = Kaleidoscope(segments=segments, speed=args.speed, pattern=pattern)
                    info = f"  ✦ ASCII Kaleidoscope — pattern: {pattern} | segments: {segments} | speed: {args.speed:.1f}x | [q]uit [r]andom [space]pause [+/-]speed"
                elif key == '+':
                    ks.speed = min(ks.speed + 0.2, 5.0)
                elif key == '-':
                    ks.speed = max(ks.speed - 0.2, 0.2)
            else:
                if paused:
                    time.sleep(0.05)

    finally:
        sys.stdout.write(show_cursor() + move_cursor(rows + 3, 1) + RESET + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()