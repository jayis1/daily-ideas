#!/usr/bin/env python3
"""
ASCII Kaleidoscope — Mesmerizing symmetric patterns in your terminal.

Generates real-time kaleidoscope patterns using Unicode block characters
and ANSI 256-color mode. Patterns are computed in a triangular wedge and
then mirrored across multiple axes of symmetry to create the kaleidoscope
effect.

Controls while running:
    q / Ctrl+C  — quit
    r           — randomize pattern
    space       — pause / resume
    +           — increase speed
    -           — decrease speed
    ]           — increase segments
    [           — decrease segments
"""

import sys
import os
import math
import time
import signal
import random
import argparse
from collections import namedtuple

__version__ = "1.1.0"

# ── ANSI helpers ──────────────────────────────────────────────────────────

ESC = "\033"
CSI = f"{ESC}["


def clear_screen():
    """Return ANSI sequence to clear screen and move cursor to (1,1)."""
    return f"{CSI}2J{CSI}H"


def hide_cursor():
    """Return ANSI sequence to hide the terminal cursor."""
    return f"{CSI}?25l"


def show_cursor():
    """Return ANSI sequence to show the terminal cursor."""
    return f"{CSI}?25h"


def move_cursor(row, col):
    """Return ANSI sequence to move cursor to (row, col)."""
    return f"{CSI}{row};{col}H"


def fg_color_256(n):
    """Return ANSI sequence to set 256-color foreground to index n."""
    return f"{CSI}38;5;{n}m"


def bg_color_256(n):
    """Return ANSI sequence to set 256-color background to index n."""
    return f"{CSI}48;5;{n}m"


RESET = f"{CSI}0m"

# ── Color palette generation ─────────────────────────────────────────────


def generate_palette(hue_offset=0.0):
    """
    Generate a smooth 256-entry palette cycling through the ANSI 216-color cube.

    Each entry maps a 0-255 intensity index to an ANSI color code (16-231).
    The hue cycles through the full spectrum using three phase-shifted sine
    waves, producing vivid, well-distributed colors.
    """
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


def generate_palette_enhanced(hue_offset=0.0, saturation=0.85):
    """
    Enhanced palette with adjustable saturation and smoother transitions.

    Includes some grayscale anchors for better contrast range.
    """
    colors = []
    for i in range(256):
        t = (i / 256.0) * 2 * math.pi + hue_offset
        # Core RGB with saturation control
        r_raw = math.sin(t) * 0.5 + 0.5
        g_raw = math.sin(t + 2.094) * 0.5 + 0.5
        b_raw = math.sin(t + 4.189) * 0.5 + 0.5
        # Mix with luminance for saturation control
        lum = 0.299 * r_raw + 0.587 * g_raw + 0.114 * b_raw
        r = r_raw * saturation + lum * (1 - saturation)
        g = g_raw * saturation + lum * (1 - saturation)
        b = b_raw * saturation + lum * (1 - saturation)
        # Map to 6x6x6 cube
        ri = min(5, max(0, int(r * 5.999)))
        gi = min(5, max(0, int(g * 5.999)))
        bi = min(5, max(0, int(b * 5.999)))
        ansi = 16 + 36 * ri + 6 * gi + bi
        colors.append(ansi)
    return colors


# ── Kaleidoscope engine ──────────────────────────────────────────────────


class Kaleidoscope:
    """
    Core kaleidoscope engine.

    The idea: compute a pattern in a single triangular wedge, then mirror
    it across N axes of symmetry to fill a circular viewport. This produces
    the characteristic kaleidoscopic reflection effect.

    Attributes:
        segments: Number of symmetry segments (must be even).
        speed: Animation speed multiplier.
        pattern: Name of the active pattern mode.
        time: Current animation time value.
        seed: Random seed for reproducible sessions.
    """

    PATTERNS = ["spiral", "ripple", "crystal", "flower", "mandala", "wave", "plasma", "vortex"]

    def __init__(self, segments=8, speed=1.0, pattern="spiral", seed=None):
        """
        Initialize the kaleidoscope engine.

        Args:
            segments: Number of symmetry segments (will be forced even, min 4).
            speed: Animation speed multiplier (0.2 - 5.0).
            pattern: Pattern mode name (must be in PATTERNS).
            seed: Optional random seed for reproducible parameters.
        """
        # Ensure segments is even and >= 4
        self.segments = max(4, segments)
        if self.segments % 2 != 0:
            self.segments += 1

        self.speed = max(0.2, min(5.0, speed))
        self.pattern = pattern if pattern in self.PATTERNS else "spiral"
        self.time = 0.0
        self.seed = seed if seed is not None else random.randint(0, 999999)
        self.rng = random.Random(self.seed)
        self.palette_offset = 0.0
        self.frame_count = 0
        self.fps = 0.0

        # Pattern-specific parameters (randomized per session for variety)
        self.freq1 = self.rng.uniform(2, 5)
        self.freq2 = self.rng.uniform(3, 7)
        self.freq3 = self.rng.uniform(1, 4)
        self.phase1 = self.rng.uniform(0, 2 * math.pi)
        self.phase2 = self.rng.uniform(0, 2 * math.pi)
        self.phase3 = self.rng.uniform(0, 2 * math.pi)
        self.morph_speed = self.rng.uniform(0.3, 1.2)

    def compute_pixel(self, r, theta, t):
        """
        Compute the intensity value (0.0 - 1.0) for a point in polar coordinates.

        The function combines multiple sinusoidal waves with different frequencies
        and phases, producing complex interference patterns. The exact combination
        depends on the selected pattern mode.

        Args:
            r: Normalized radial distance (0.0 at center, 1.0 at edge).
            theta: Angle within the current wedge (0 to seg_angle).
            t: Current animation time value.

        Returns:
            Float in [0.0, 1.0] representing the pixel intensity.
        """
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
            # Creates crystal-like facets with sharp angular geometry
            angle_mod = math.fmod(theta * self.freq1 + t * s * 0.2, math.pi / 3)
            val = math.sin(r * self.freq2 + angle_mod * 3)
            val += math.cos(r * 2 - t * s * 0.4) * 0.7
            val += math.sin(theta * self.freq3 + t * s * 0.6) * 0.4

        elif self.pattern == "flower":
            # Organic petal-like patterns that bloom and shift
            petal = math.cos(theta * 6 + t * s * 0.3) * 0.5 + 0.5
            val = math.sin(r * self.freq1 * petal + t * s)
            val += math.cos(r * self.freq2 - t * s * 0.5) * 0.6
            val *= (petal + 0.3)

        elif self.pattern == "mandala":
            # Sacred geometry style with concentric rings and spokes
            ring = math.sin(r * self.freq1 * 2 + t * s * 0.3)
            spoke = math.cos(theta * self.freq2 * 2 + t * s * 0.2)
            pulse = math.sin(r * self.freq3 - t * s * 0.5)
            val = ring + spoke * 0.6 + pulse * 0.4

        elif self.pattern == "wave":
            # Ocean wave interference patterns
            wave1 = math.sin(r * self.freq1 + theta * 2 + t * s)
            wave2 = math.cos(r * self.freq2 - theta * 1.5 + t * s * 0.7)
            val = wave1 + wave2 + math.sin(theta * 3 + t * s * 0.4) * 0.3

        elif self.pattern == "plasma":
            # Classic plasma effect with color cycling
            v1 = math.sin(r * self.freq1 + t * s * 0.6)
            v2 = math.sin(theta * self.freq2 * 1.3 + t * s * 0.4)
            v3 = math.sin((r + theta) * self.freq3 + t * s * 0.5)
            # Add a rotating component for extra visual complexity
            v4 = math.sin(math.sqrt(r * self.freq1) * 3 + t * s * 0.8)
            val = v1 + v2 + v3 * 0.7 + v4 * 0.5

        elif self.pattern == "vortex":
            # Spinning vortex with depth illusion
            # Spiral arms that rotate and twist
            spin = theta + r * 4 + t * s * 1.2
            val = math.sin(spin * self.freq1 * 0.8)
            val += math.cos(r * self.freq2 * 2 - spin * 0.5 + self.phase1) * 0.8
            # Pulsing center for depth
            val += math.sin(r * self.freq3 * 3 + t * s * 0.6) * r * 0.6
            # Twist modulation
            val += math.cos(theta * 4 + r * 6 + t * s * 0.3) * 0.3

        else:
            # Fallback pattern
            val = math.sin(r * 3 + theta * 2 + t)

        # Normalize to 0..1 range (values typically range from -3 to +3)
        val = (val + 3) / 6.0
        return max(0.0, min(1.0, val))

    def render_frame(self, width, height):
        """
        Render one frame of the kaleidoscope into a grid of (char, fg, bg) tuples.

        Each terminal cell is rendered using a half-block character (▀ or ▄),
        giving 2 vertical sub-pixels per row. This doubles the effective
        vertical resolution for smoother visuals.

        Args:
            width: Number of terminal columns.
            height: Number of terminal rows.

        Returns:
            List of rows, each containing a list of (char, fg_color, bg_color) tuples.
        """
        # Guard against degenerate sizes
        if width < 2 or height < 2:
            return [[]]

        rows = height
        cols = width
        cx = cols / 2.0
        cy = rows  # Center vertically (in sub-pixel coords, rows*2 pixels high)
        max_r = min(cx, rows) * 0.92

        t = self.time

        # Full pixel grid (2x rows for half-block rendering)
        pixel_rows = rows * 2
        pixel_cols = cols
        grid = [[0.0] * pixel_cols for _ in range(pixel_rows)]

        half_segments = self.segments // 2
        seg_angle = math.pi / half_segments if half_segments > 0 else math.pi

        palette = generate_palette_enhanced(self.palette_offset)

        # Background color for outside the circle (dark blue-black)
        bg_dark = 16  # ANSI color 16 = #000000 in the 216 cube

        for py in range(pixel_rows):
            for px in range(pixel_cols):
                dx = px - cx + 0.5
                dy = py - cy + 0.5
                r = math.sqrt(dx * dx + dy * dy)

                if r > max_r or r < 0.5:
                    grid[py][px] = -1.0  # Sentinel: outside circle
                    continue

                theta = math.atan2(dy, dx)
                if theta < 0:
                    theta += 2 * math.pi

                # Mirror: fold theta into first segment
                segment_idx = int(theta / seg_angle)
                theta_in_seg = theta - segment_idx * seg_angle

                # Every other segment is mirrored for kaleidoscope effect
                if segment_idx % 2 == 1:
                    theta_in_seg = seg_angle - theta_in_seg

                val = self.compute_pixel(r / max_r, theta_in_seg, t)
                grid[py][px] = val

        # Convert pixel grid to (char, fg_color, bg_color) for half-block rendering
        result = []
        for row in range(rows):
            row_data = []
            for col in range(pixel_cols):
                upper_val = grid[row * 2][col]
                lower_val = grid[row * 2 + 1][col]

                # Handle outside-circle pixels
                if upper_val < 0 and lower_val < 0:
                    # Both sub-pixels outside circle: show as dark background
                    row_data.append((" ", bg_dark, 0))  # space with dark bg
                    continue

                # If one sub-pixel is outside, clamp it to near-zero
                if upper_val < 0:
                    upper_val = 0.02
                if lower_val < 0:
                    lower_val = 0.02

                # Use half-block chars for sub-pixel color depth
                if upper_val >= lower_val:
                    char = "▀"
                    fg_idx = int(upper_val * 255)
                    bg_idx = int(lower_val * 255)
                else:
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
        self.frame_count += 1
        return result


# ── Terminal input handling ───────────────────────────────────────────────


def get_key_nonblock(timeout=0.02):
    """
    Read a single keypress from stdin without blocking.

    Args:
        timeout: Seconds to wait for input (default 0.02).

    Returns:
        Character string if a key was pressed, or None if no input available.
    """
    import select
    if select.select([sys.stdin], [], [], timeout)[0]:
        return sys.stdin.read(1)
    return None


def set_terminal_raw():
    """Set terminal to raw mode for non-blocking key input."""
    import tty
    import termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    return old_settings


def restore_terminal(old_settings):
    """Restore terminal to original settings."""
    import termios
    fd = sys.stdin.fileno()
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# ── Main loop ────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="ASCII Kaleidoscope — Mesmerizing symmetric patterns in your terminal.",
        epilog="While running: q=quit  r=random pattern  space=pause  +/-=speed  [/]=segments"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-s", "--segments", type=int, default=8,
        help="Number of symmetry segments, must be even, min 4 (default: 8)"
    )
    parser.add_argument(
        "-p", "--pattern", type=str, default=None,
        choices=Kaleidoscope.PATTERNS,
        help="Pattern type (default: random)"
    )
    parser.add_argument(
        "--speed", type=float, default=1.0,
        help="Animation speed multiplier, 0.2-5.0 (default: 1.0)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducible patterns"
    )
    parser.add_argument(
        "--no-info", action="store_true",
        help="Hide the info bar at the bottom for cleaner display"
    )
    args = parser.parse_args()

    pattern = args.pattern or random.choice(Kaleidoscope.PATTERNS)

    # Get terminal size
    try:
        term_size = os.get_terminal_size()
        cols = term_size.columns
        rows = term_size.lines
    except OSError:
        cols, rows = 80, 24

    # Reserve space for info bar unless --no-info
    info_rows = 0 if args.no_info else 2
    rows = max(4, rows - info_rows)
    cols = min(cols, 160)
    rows = min(rows, 60)

    ks = Kaleidoscope(
        segments=args.segments,
        speed=args.speed,
        pattern=pattern,
        seed=args.seed,
    )

    running = True
    paused = False
    show_info = not args.no_info

    # Signal handler for Ctrl+C
    def handle_sigint(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_sigint)

    # Set up terminal for non-blocking input
    old_term_settings = None
    try:
        old_term_settings = set_terminal_raw()

        sys.stdout.write(clear_screen() + hide_cursor())
        sys.stdout.flush()

        # FPS tracking
        last_fps_time = time.time()
        fps_frame_count = 0

        while running:
            frame_start = time.time()

            if not paused:
                frame = ks.render_frame(cols, rows)

                # Build output buffer
                output_parts = [move_cursor(1, 1)]

                for row_idx, row in enumerate(frame):
                    line_parts = []
                    prev_fg = -1
                    prev_bg = -1
                    for char, fg, bg in row:
                        if fg != prev_fg or bg != prev_bg:
                            line_parts.append(fg_color_256(fg))
                            line_parts.append(bg_color_256(bg))
                            line_parts.append(char)
                            prev_fg = fg
                            prev_bg = bg
                        else:
                            line_parts.append(char)
                    line_parts.append(RESET)
                    output_parts.append("".join(line_parts))

                # Info bar
                if show_info:
                    fps_str = f"{ks.fps:.0f}" if ks.fps > 0 else "—"
                    info_text = (
                        f"  ✦ Kaleidoscope │ {pattern} │ "
                        f"segments: {ks.segments} │ speed: {ks.speed:.1f}x │ "
                        f"fps: {fps_str} │ "
                        f"[q]uit [r]andom [space]pause [+/-]speed [/]segments"
                    )
                    output_parts.append(move_cursor(rows + 2, 1) + RESET + info_text)

                sys.stdout.write("\n".join(output_parts) + "\n")
                sys.stdout.flush()

            # FPS calculation
            fps_frame_count += 1
            now = time.time()
            elapsed = now - last_fps_time
            if elapsed >= 1.0:
                ks.fps = fps_frame_count / elapsed
                fps_frame_count = 0
                last_fps_time = now

            # Handle keypresses
            key = get_key_nonblock(timeout=0.02)
            if key == 'q' or key == '\x03':
                running = False
            elif key == ' ':
                paused = not paused
            elif key == 'r':
                pattern = random.choice(Kaleidoscope.PATTERNS)
                ks = Kaleidoscope(
                    segments=ks.segments, speed=ks.speed,
                    pattern=pattern, seed=None
                )
            elif key == '+' or key == '=':
                ks.speed = min(ks.speed + 0.2, 5.0)
            elif key == '-' or key == '_':
                ks.speed = max(ks.speed - 0.2, 0.2)
            elif key == ']':
                ks.segments = min(ks.segments + 2, 24)
            elif key == '[':
                ks.segments = max(ks.segments - 2, 4)

    finally:
        # Always restore terminal state
        if old_term_settings is not None:
            try:
                restore_terminal(old_term_settings)
            except Exception:
                pass
        sys.stdout.write(show_cursor() + move_cursor(rows + info_rows + 1, 1) + RESET + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()