#!/usr/bin/env python3
"""
LOOM — Terminal Generative Art Weaver
Creates animated geometric tapestry patterns using Unicode block characters.
Patterns are generated from layered trigonometric functions and rendered
as a continuously evolving woven textile in your terminal.
"""

import os
import sys
import time
import math
import random
import argparse
from collections import namedtuple

# ─── Unicode block characters for weaving ───────────────────────────────
BLOCKS = {
    "full": "█",
    "dark": "▓",
    "medium": "▒",
    "light": "░",
    "top_half": "▀",
    "bottom_half": "▄",
    "left_half": "▌",
    "right_half": "▐",
    "quad_tl": "▘",
    "quad_tr": "▝",
    "quad_bl": "▖",
    "quad_br": "▗",
    "quad_full": "█",
    "dot": "·",
    "shade1": "░",
    "shade2": "▒",
    "shade3": "▓",
}

# Color palette threads for the loom
PALETTES = {
    "sunset": [(255, 80, 50), (255, 160, 40), (255, 220, 80), (180, 40, 80), (120, 20, 60)],
    "ocean": [(20, 80, 160), (40, 160, 200), (80, 220, 240), (10, 40, 100), (60, 200, 180)],
    "forest": [(30, 120, 40), (80, 200, 60), (160, 220, 80), (20, 80, 30), (100, 180, 100)],
    "neon": [(255, 0, 128), (0, 255, 128), (128, 0, 255), (255, 255, 0), (0, 200, 255)],
    "ember": [(255, 60, 0), (255, 120, 20), (200, 40, 0), (255, 200, 50), (120, 10, 0)],
    "aurora": [(80, 255, 180), (40, 120, 255), (200, 80, 255), (120, 255, 200), (60, 200, 160)],
    "monochrome": [(255, 255, 255), (200, 200, 200), (140, 140, 140), (80, 80, 80), (40, 40, 40)],
}

WEAVE_PATTERNS = ["plain", "twill", "satin", "herringbone", "basket", "diamond"]


def rgb_to_ansi(r, g, b):
    """Convert RGB to 24-bit ANSI escape code."""
    return f"\033[38;2;{int(r)};{int(g)};{int(b)}m"


def blend_color(c1, c2, t):
    """Linearly interpolate between two RGB colors."""
    return (
        c1[0] + (c2[0] - c1[0]) * t,
        c1[1] + (c2[1] - c1[1]) * t,
        c1[2] + (c2[2] - c1[2]) * t,
    )


def palette_color(palette, t):
    """Get a color from a palette at position t (0.0-1.0), with smooth interpolation."""
    t = t % 1.0
    n = len(palette)
    idx = t * n
    i = int(idx) % n
    j = (i + 1) % n
    frac = idx - int(idx)
    return blend_color(palette[i], palette[j], frac)


WeaveLayer = namedtuple("WeaveLayer", ["freq_x", "freq_y", "phase_x", "phase_y", "speed", "amplitude"])


def random_layer():
    """Generate a random weave layer."""
    return WeaveLayer(
        freq_x=random.uniform(0.02, 0.15),
        freq_y=random.uniform(0.02, 0.15),
        phase_x=random.uniform(0, math.pi * 2),
        phase_y=random.uniform(0, math.pi * 2),
        speed=random.uniform(0.3, 1.5),
        amplitude=random.uniform(0.3, 1.0),
    )


class Loom:
    """A generative art loom that weaves animated patterns in the terminal."""

    def __init__(self, width=None, height=None, palette="sunset", pattern="twill",
                 layers=3, seed=None, fps=15):
        self.width = width or min(os.get_terminal_size().columns, 120)
        self.height = height or min(os.get_terminal_size().lines - 2, 50)
        self.palette_name = palette
        self.palette = PALETTES.get(palette, PALETTES["sunset"])
        self.pattern_name = pattern
        self.fps = fps
        self.frame_time = 1.0 / fps

        if seed is not None:
            random.seed(seed)

        self.layers = [random_layer() for _ in range(layers)]
        self.warp_threads = [random.uniform(0.01, 0.08) for _ in range(self.width)]
        self.weft_threads = [random.uniform(0.01, 0.08) for _ in range(self.height)]

        # Global phase offsets that slowly evolve
        self.global_phase = random.uniform(0, math.pi * 2)
        self.global_drift = random.uniform(0.1, 0.4)

    def compute_weave_value(self, x, y, t):
        """
        Compute the weave value at position (x, y) at time t.
        This is the core generative function — it layers multiple
        trigonometric functions to create complex interference patterns.
        """
        value = 0.0
        total_amplitude = 0.0

        for layer in self.layers:
            # Each layer contributes a sine wave with its own frequency, phase, and speed
            wave = math.sin(
                layer.freq_x * x + layer.phase_x + t * layer.speed
            ) * math.cos(
                layer.freq_y * y + layer.phase_y + t * layer.speed * 0.7
            )
            # Add cross terms for more complex patterns
            wave += 0.5 * math.sin(
                (layer.freq_x + layer.freq_y) * (x + y) * 0.5
                + self.global_phase + t * layer.speed * 0.3
            )
            value += wave * layer.amplitude
            total_amplitude += layer.amplitude

        if total_amplitude > 0:
            value /= total_amplitude

        # Apply warp/weft thread modulation (like real fabric)
        warp_mod = math.sin(self.warp_threads[x] * x + t * 0.2)
        weft_mod = math.sin(self.weft_threads[y] * y + t * 0.15)
        value = value * 0.8 + (warp_mod + weft_mod) * 0.1

        # Global drift creates slow evolution
        value += 0.1 * math.sin(self.global_drift * t + self.global_phase)

        return value  # Range roughly -1.5 to 1.5

    def value_to_char(self, value):
        """Map a weave value to a Unicode block character."""
        # Normalize to 0-1
        v = (value + 1.5) / 3.0
        v = max(0.0, min(1.0, v))

        if v < 0.15:
            return BLOCKS["light"]
        elif v < 0.3:
            return BLOCKS["quad_tl"]
        elif v < 0.45:
            return BLOCKS["shade2"]
        elif v < 0.55:
            return BLOCKS["medium"]
        elif v < 0.7:
            return BLOCKS["shade3"]
        elif v < 0.85:
            return BLOCKS["dark"]
        else:
            return BLOCKS["full"]

    def value_to_color_and_char(self, value, x, y, t):
        """Map a weave value to both a color and character based on pattern style."""
        # Color based on the value mapped to palette
        v = (value + 1.5) / 3.0
        v = max(0.0, min(1.0, v))
        color_t = (v + math.sin(x * 0.05 + t * 0.3) * 0.15 + math.cos(y * 0.04 + t * 0.2) * 0.15) % 1.0
        color = palette_color(self.palette, color_t)

        # Character based on pattern
        char = self._pattern_char(v, x, y, t)

        return color, char

    def _pattern_char(self, v, x, y, t):
        """Select character based on the weave pattern."""
        if self.pattern_name == "plain":
            return self._plain_char(v)
        elif self.pattern_name == "twill":
            return self._twill_char(v, x, y)
        elif self.pattern_name == "satin":
            return self._satin_char(v, x, y)
        elif self.pattern_name == "herringbone":
            return self._herringbone_char(v, x, y)
        elif self.pattern_name == "basket":
            return self._basket_char(v, x, y)
        elif self.pattern_name == "diamond":
            return self._diamond_char(v, x, y, t)
        else:
            return self._twill_char(v, x, y)

    def _plain_char(self, v):
        if v < 0.25:
            return BLOCKS["light"]
        elif v < 0.75:
            return BLOCKS["medium"]
        else:
            return BLOCKS["full"]

    def _twill_char(self, v, x, y):
        """Diagonal twill weave pattern."""
        diag = (x + y) % 8
        if diag < 2:
            if v < 0.3:
                return BLOCKS["light"]
            return BLOCKS["shade2"] if v < 0.6 else BLOCKS["dark"]
        elif diag < 5:
            if v > 0.7:
                return BLOCKS["full"]
            return BLOCKS["shade3"] if v > 0.4 else BLOCKS["medium"]
        else:
            if v < 0.35:
                return BLOCKS["dot"]
            return BLOCKS["shade1"] if v < 0.65 else BLOCKS["shade2"]

    def _satin_char(self, v, x, y):
        """Satin weave — scattered highlights."""
        highlight = ((x * 7 + y * 3) % 11) < 2
        if highlight:
            return BLOCKS["full"] if v > 0.3 else BLOCKS["shade3"]
        else:
            return BLOCKS["light"] if v < 0.6 else BLOCKS["shade2"]

    def _herringbone_char(self, v, x, y):
        """Herringbone — V-shaped pattern."""
        period = 16
        diag = (x + y) % period
        anti_diag = (x - y) % period
        v_pattern = (diag + anti_diag) % period
        if v_pattern < 4 or v_pattern > period - 4:
            return BLOCKS["full"] if v > 0.4 else BLOCKS["shade3"]
        return BLOCKS["light"] if v < 0.5 else BLOCKS["shade1"]

    def _basket_char(self, v, x, y):
        """Basket weave — alternating blocks."""
        bx = (x // 4) % 2
        by = (y // 2) % 2
        if bx == by:
            return BLOCKS["full"] if v > 0.3 else BLOCKS["shade3"]
        else:
            return BLOCKS["shade1"] if v < 0.5 else BLOCKS["medium"]

    def _diamond_char(self, v, x, y, t):
        """Diamond pattern with time-based rotation."""
        period = 12
        cx = (x % period) - period // 2
        cy = (y % period) - period // 2
        dist = abs(cx) + abs(cy)
        if dist < 3:
            return BLOCKS["full"] if v > 0.3 else BLOCKS["shade3"]
        elif dist < 5:
            return BLOCKS["medium"] if v > 0.4 else BLOCKS["shade2"]
        else:
            return BLOCKS["light"] if v < 0.5 else BLOCKS["dot"]

    def render_frame(self, t):
        """Render a single frame of the loom animation."""
        lines = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                value = self.compute_weave_value(x, y, t)
                color, char = self.value_to_color_and_char(value, x, y, t)
                row.append(f"{rgb_to_ansi(*color)}{char}")
            lines.append("".join(row))
        return lines

    def render_ascii_frame(self, t):
        """Render a frame using only ASCII characters (no colors)."""
        ascii_chars = " .:-=+*#%@█"
        lines = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                value = self.compute_weave_value(x, y, t)
                v = (value + 1.5) / 3.0
                v = max(0.0, min(1.0, v))
                idx = int(v * (len(ascii_chars) - 1))
                row.append(ascii_chars[idx])
            lines.append("".join(row))
        return lines

    def animate(self, duration=None, ascii_mode=False):
        """Run the loom animation in the terminal."""
        try:
            if not ascii_mode:
                # Check if terminal supports 24-bit color
                term = os.environ.get("TERM", "")
                colorterm = os.environ.get("COLORTERM", "")
                if "truecolor" not in colorterm.lower() and "256color" not in term.lower():
                    print("Note: Terminal may not support truecolor. Using ASCII mode.")
                    ascii_mode = True

            start_time = time.time()
            t = 0.0

            # Hide cursor
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

            while True:
                frame_start = time.time()

                if duration is not None and t > duration:
                    break

                if ascii_mode:
                    lines = self.render_ascii_frame(t)
                else:
                    lines = self.render_frame(t)

                # Move cursor to top-left and draw
                output = "\033[H" + "\n".join(lines)
                if not ascii_mode:
                    output += "\033[0m"  # Reset colors

                sys.stdout.write(output)
                sys.stdout.flush()

                # Advance time
                t += self.frame_time * 2  # Speed up animation slightly

                # Maintain frame rate
                elapsed = time.time() - frame_start
                if elapsed < self.frame_time:
                    time.sleep(self.frame_time - elapsed)

        except KeyboardInterrupt:
            pass
        finally:
            # Show cursor and reset colors
            sys.stdout.write("\033[?25h\033[0m")
            sys.stdout.write("\n")
            sys.stdout.flush()

    def snapshot(self, t=0.0, ascii_mode=False):
        """Render a single snapshot (for saving to file)."""
        if ascii_mode:
            return "\n".join(self.render_ascii_frame(t))
        else:
            lines = self.render_frame(t)
            return "\n".join(lines) + "\033[0m\n"

    def save_frames(self, filename="loom_output.txt", frames=10, interval=0.5, ascii_mode=False):
        """Save multiple frames to a text file."""
        with open(filename, "w") as f:
            for i in range(frames):
                t = i * interval
                f.write(f"--- Frame {i} (t={t:.1f}) ---\n")
                if ascii_mode:
                    f.write("\n".join(self.render_ascii_frame(t)))
                else:
                    # Strip ANSI for file output unless explicitly wanted
                    f.write("\n".join(self.render_ascii_frame(t)))
                f.write("\n\n")
        return filename


def main():
    parser = argparse.ArgumentParser(
        description="LOOM — Terminal Generative Art Weaver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  loom.py                          # Start animation with defaults
  loom.py --palette neon           # Neon color scheme
  loom.py --pattern diamond        # Diamond weave pattern
  loom.py --seed 42 --width 80     # Reproducible, custom size
  loom.py --ascii                   # ASCII-only mode (no colors)
  loom.py --snapshot > art.txt     # Save single frame
  loom.py --palette aurora --layers 5   # More complex weaving

Available palettes: sunset, ocean, forest, neon, ember, aurora, monochrome
Available patterns: plain, twill, satin, herringbone, basket, diamond
        """
    )

    parser.add_argument("-W", "--width", type=int, help="Terminal width (default: auto-detect)")
    parser.add_argument("-H", "--height", type=int, help="Terminal height (default: auto-detect)")
    parser.add_argument("-p", "--palette", default="sunset",
                        choices=list(PALETTES.keys()), help="Color palette (default: sunset)")
    parser.add_argument("--pattern", default="twill",
                        choices=WEAVE_PATTERNS, help="Weave pattern (default: twill)")
    parser.add_argument("-l", "--layers", type=int, default=3, help="Number of weave layers (default: 3)")
    parser.add_argument("-s", "--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--fps", type=int, default=15, help="Frames per second (default: 15)")
    parser.add_argument("--ascii", action="store_true", help="ASCII-only mode (no ANSI colors)")
    parser.add_argument("--snapshot", action="store_true", help="Output a single frame and exit")
    parser.add_argument("--duration", type=float, default=None, help="Animation duration in seconds")
    parser.add_argument("--save", type=str, default=None, help="Save frames to file instead of animating")
    parser.add_argument("--save-frames", type=int, default=10, help="Number of frames to save (default: 10)")

    args = parser.parse_args()

    loom = Loom(
        width=args.width,
        height=args.height,
        palette=args.palette,
        pattern=args.pattern,
        layers=args.layers,
        seed=args.seed,
        fps=args.fps,
    )

    if args.snapshot:
        print(loom.snapshot(t=2.0, ascii_mode=args.ascii))
    elif args.save:
        filename = loom.save_frames(args.save, frames=args.save_frames, ascii_mode=True)
        print(f"Saved {args.save_frames} frames to {filename}")
    else:
        # Clear screen before starting animation
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
        loom.animate(duration=args.duration, ascii_mode=args.ascii)


if __name__ == "__main__":
    main()