#!/usr/bin/env python3
"""
Terminal Lava Lamp — A mesmerizing ASCII lava lamp simulation with ANSI colors.

Blobs of wax rise and fall inside a lamp-shaped container, rendered in the terminal
using colored characters and simple physics simulation. Features multiple color themes,
interactive controls, bubble particles, heat glow effects, blob merging/splitting,
screenshot export, and smooth animation.

Usage:
    python3 lava_lamp.py [OPTIONS]
    python3 lava_lamp.py classic
    python3 lava_lamp.py --theme ocean --speed 1.5
    python3 lava_lamp.py --help
"""

import sys
import os
import time
import random
import math
import signal
import argparse
import json
import select
import tty
import termios
from typing import List, Tuple, Optional, Dict, Any

# ── Version ────────────────────────────────────────────────────────────────

VERSION = "3.0.0"

# ── ANSI helpers ──────────────────────────────────────────────────────────

def esc(code):
    """Return an ANSI escape sequence for the given code."""
    return f"\033[{code}m"

def clear_screen():
    """Clear the terminal screen and move cursor to top-left."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def move_cursor(row, col):
    """Move the terminal cursor to (row, col)."""
    sys.stdout.write(f"\033[{row};{col}H")
    sys.stdout.flush()

def hide_cursor():
    """Hide the terminal cursor for cleaner animation."""
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def show_cursor():
    """Show the terminal cursor (restore after hiding)."""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()

def rgb_to_ansi(r, g, b, fg=True):
    """Convert RGB values (0-255) to a 24-bit ANSI color escape code.

    Values are clamped to 0-255 to prevent out-of-range errors.

    Args:
        r: Red component (0-255, clamped).
        g: Green component (0-255, clamped).
        b: Blue component (0-255, clamped).
        fg: If True, produce foreground color; else background color.

    Returns:
        ANSI escape string like \\033[38;2;R;G;Bm or \\033[48;2;R;G;Bm.
    """
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    code = 38 if fg else 48
    return f"\033[{code};2;{r};{g};{b}m"

def strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from a string.

    Args:
        text: String potentially containing ANSI escape codes.

    Returns:
        Plain text with all ANSI sequences removed.
    """
    import re
    return re.sub(r'\033\[[0-9;]*m', '', text)

# ── Color palette ─────────────────────────────────────────────────────────

# Lava lamp color themes
THEMES: Dict[str, Dict[str, Any]] = {
    "classic": {
        "name": "Classic",
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
        "heat": (255, 80, 20),     # heat source glow color
    },
    "ocean": {
        "name": "Ocean",
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
        "heat": (40, 120, 200),
    },
    "toxic": {
        "name": "Toxic",
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
        "heat": (40, 200, 40),
    },
    "sunset": {
        "name": "Sunset",
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
        "heat": (255, 60, 80),
    },
    "neon": {
        "name": "Neon",
        "bg": (5, 5, 15),
        "lamp": (30, 10, 50),
        "wax": [
            (255, 0, 255),
            (0, 255, 255),
            (255, 255, 0),
            (0, 255, 128),
            (255, 128, 0),
            (128, 0, 255),
        ],
        "glow": (40, 10, 50),
        "heat": (200, 0, 200),
    },
    "aurora": {
        "name": "Aurora",
        "bg": (5, 10, 20),
        "lamp": (15, 35, 55),
        "wax": [
            (50, 200, 100),
            (100, 255, 150),
            (150, 200, 255),
            (200, 100, 255),
            (50, 255, 180),
            (100, 150, 255),
        ],
        "glow": (15, 40, 60),
        "heat": (40, 180, 120),
    },
    "ember": {
        "name": "Ember",
        "bg": (25, 8, 5),
        "lamp": (70, 30, 20),
        "wax": [
            (255, 40, 10),
            (255, 80, 0),
            (255, 140, 20),
            (255, 200, 60),
            (200, 30, 0),
            (180, 50, 10),
        ],
        "glow": (50, 15, 5),
        "heat": (255, 60, 10),
    },
    "frost": {
        "name": "Frost",
        "bg": (8, 12, 25),
        "lamp": (30, 50, 70),
        "wax": [
            (180, 220, 255),
            (220, 240, 255),
            (150, 200, 255),
            (255, 255, 255),
            (100, 170, 240),
            (140, 190, 250),
        ],
        "glow": (15, 25, 50),
        "heat": (80, 150, 220),
    },
}

# Characters for rendering
BG_CHARS = " .·:;░▒"
WAX_CHARS = "●◉⬤◆▲★◉⬤●◆▲★"
GLOW_CHARS = " .:;░"

# ── Merge/Split constants ─────────────────────────────────────────────────

MERGE_DISTANCE = 0.08       # Blobs closer than this may merge
SPLIT_RADIUS_THRESHOLD = 0.10  # Blobs larger than this may split
MERGE_COOLDOWN = 2.0       # Seconds after merge before another merge
SPLIT_COOLDOWN = 3.0       # Seconds after split before another split

# ── Bubble class ──────────────────────────────────────────────────────────

class Bubble:
    """A small rising bubble particle for visual flair."""

    def __init__(self, lamp_width: int, lamp_height: int):
        """Create a bubble with random position near the base of the lamp.

        Args:
            lamp_width: Terminal character width (for reference).
            lamp_height: Terminal row height (for reference).
        """
        self.y = random.uniform(0.85, 0.98)  # start near bottom
        self.x = random.uniform(0.3, 0.7)
        self.speed = random.uniform(0.05, 0.15)
        self.wobble_freq = random.uniform(2.0, 5.0)
        self.wobble_amp = random.uniform(0.005, 0.02)
        self.phase = random.uniform(0, 2 * math.pi)
        self.life = 0.0
        self.max_life = random.uniform(3.0, 8.0)  # seconds before popping
        self.char = random.choice(["·", "∘", "○", "°", "•"])

    def update(self, dt: float) -> bool:
        """Move the bubble upward with wobble.

        Args:
            dt: Time delta in seconds.

        Returns:
            True if the bubble is still alive, False if it should be removed.
        """
        self.life += dt
        self.y -= self.speed * dt  # rise
        self.x += self.wobble_amp * math.sin(self.life * self.wobble_freq + self.phase)
        self.x = max(0.2, min(0.8, self.x))
        return self.y > 0.05 and self.life < self.max_life

# ── Blob class ────────────────────────────────────────────────────────────

class Blob:
    """A wax blob in the lava lamp with physics simulation.

    Blobs expand when heated (rising) and contract when cooled (sinking).
    They can merge with nearby blobs and large blobs can spontaneously split.
    """

    def __init__(self, theme_colors: List[Tuple[int, int, int]],
                 heat_color: Tuple[int, int, int]):
        """Initialize a blob with the given theme colors and heat color.

        Args:
            theme_colors: List of (r, g, b) tuples for wax colors.
            heat_color: (r, g, b) tuple for heat source color.
        """
        self.colors = theme_colors
        self.heat_color = heat_color
        self.merge_cooldown = 0.0   # Seconds until this blob can merge again
        self.split_cooldown = 0.0   # Seconds until this blob can split again
        self.reset()

    def reset(self):
        """Reset the blob to a random position near the bottom of the lamp."""
        self.y = random.uniform(0.7, 0.95)  # start near bottom
        self.x = random.uniform(0.3, 0.7)
        self.radius = random.uniform(0.04, 0.08)
        self.vy = 0.0
        self.phase = random.uniform(0, 2 * math.pi)
        self.color_idx = random.randint(0, len(self.colors) - 1)
        self.wobble_freq = random.uniform(1.5, 3.0)
        self.wobble_amp = random.uniform(0.01, 0.03)
        self.life = 0.0
        self.base_radius = self.radius  # remember initial size
        self.merge_cooldown = 0.0
        self.split_cooldown = 0.0

    def update(self, dt: float, speed_multiplier: float = 1.0):
        """Update blob physics.

        Heat is stronger at the bottom, causing wax to expand and rise.
        At the top, wax cools, contracts, and sinks.

        Args:
            dt: Time delta in seconds.
            speed_multiplier: Animation speed factor (1.0 = normal).
        """
        effective_dt = dt * speed_multiplier
        self.life += effective_dt

        # Reduce cooldowns
        self.merge_cooldown = max(0, self.merge_cooldown - effective_dt)
        self.split_cooldown = max(0, self.split_cooldown - effective_dt)

        # Buoyancy: hotter wax rises, cooler wax sinks
        # At bottom, heat is high → blob expands and rises
        # At top, heat is low → blob contracts and sinks
        target_vy = -0.15 + 0.3 * (1.0 - self.y)  # rises when low, sinks when high

        # Add some randomness for organic feel
        target_vy += random.uniform(-0.02, 0.02)

        # Smooth velocity change (inertia)
        self.vy += (target_vy - self.vy) * effective_dt * 2.0
        self.y += self.vy * effective_dt

        # Horizontal wobble
        self.x = 0.5 + self.wobble_amp * math.sin(self.life * self.wobble_freq + self.phase)
        # Small random drift for natural motion
        self.x += random.uniform(-0.003, 0.003)
        self.x = max(0.15, min(0.85, self.x))

        # Radius changes: expand when rising (hot), contract when sinking (cool)
        if self.vy < -0.02:  # rising
            self.radius = min(0.12, self.radius + effective_dt * 0.02)
        elif self.vy > 0.02:  # sinking
            self.radius = max(0.03, self.radius - effective_dt * 0.01)

        # Gentle pulsation for visual liveliness
        pulse = 0.005 * math.sin(self.life * 2.5)
        self.radius = max(0.03, min(0.12, self.radius + pulse))

        # Reset if out of bounds
        if self.y < -0.1 or self.y > 1.2:
            self.reset()

        # Color shifts slowly over time
        self.color_idx = (self.color_idx + random.uniform(-0.1, 0.1)) % len(self.colors)

# ── Screenshot ────────────────────────────────────────────────────────────

class Screenshot:
    """Handles saving screenshots of the lava lamp to files."""

    @staticmethod
    def save_ansi(lines: List[str], filepath: str) -> bool:
        """Save rendered lines with ANSI codes to a file.

        Args:
            lines: List of ANSI-colored strings from render().
            filepath: Path to save the screenshot.

        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines) + "\n")
            return True
        except (OSError, IOError) as e:
            print(f"Error saving screenshot: {e}", file=sys.stderr)
            return False

    @staticmethod
    def save_plain(lines: List[str], filepath: str) -> bool:
        """Save rendered lines as plain text (ANSI stripped) to a file.

        Args:
            lines: List of ANSI-colored strings from render().
            filepath: Path to save the plain text screenshot.

        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(strip_ansi(line) + "\n")
            return True
        except (OSError, IOError) as e:
            print(f"Error saving plain screenshot: {e}", file=sys.stderr)
            return False

# ── Theme loader ──────────────────────────────────────────────────────────

def load_themes_from_file(filepath: str) -> Dict[str, Dict[str, Any]]:
    """Load additional color themes from a JSON file.

    The JSON file should contain a dictionary mapping theme names to theme
    definitions. Each theme must have: name, bg, lamp, wax (list of 6 colors),
    glow, and heat. Colors are [r, g, b] arrays.

    Args:
        filepath: Path to the JSON theme file.

    Returns:
        Dictionary of theme definitions that can be merged into THEMES.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If a theme definition is missing required keys or has
                    invalid color values.
    """
    required_keys = {"name", "bg", "lamp", "wax", "glow", "heat"}

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    themes = {}
    for theme_name, theme_def in data.items():
        # Validate required keys
        missing = required_keys - set(theme_def.keys())
        if missing:
            raise ValueError(f"Theme '{theme_name}' missing keys: {missing}")

        # Convert color arrays to tuples
        def to_tuple(color):
            if isinstance(color, (list, tuple)) and len(color) == 3:
                t = tuple(int(c) for c in color)
                for v in t:
                    if not (0 <= v <= 255):
                        raise ValueError(
                            f"Theme '{theme_name}' has out-of-range color value: {t}")
                return t
            raise ValueError(f"Theme '{theme_name}' has invalid color: {color}")

        themes[theme_name] = {
            "name": str(theme_def["name"]),
            "bg": to_tuple(theme_def["bg"]),
            "lamp": to_tuple(theme_def["lamp"]),
            "wax": [to_tuple(c) for c in theme_def["wax"]],
            "glow": to_tuple(theme_def["glow"]),
            "heat": to_tuple(theme_def["heat"]),
        }

        # Validate wax has enough colors
        if len(themes[theme_name]["wax"]) < 4:
            raise ValueError(f"Theme '{theme_name}' needs at least 4 wax colors")

    return themes

# ── Lava Lamp ─────────────────────────────────────────────────────────────

class LavaLamp:
    """The main lava lamp simulation engine.

    Manages blobs, bubbles, and rendering. The lamp shape is defined by a
    parametric width function that creates the classic lava lamp silhouette.
    Blobs can merge when close together and large blobs can split apart,
    creating dynamic, organic-looking motion.

    Attributes:
        width: Terminal character width for rendering.
        height: Terminal row height for rendering.
        theme_name: Name of the current color theme.
        blobs: List of Blob objects.
        bubbles: List of Bubble objects.
        time: Total elapsed simulation time.
        paused: Whether the simulation is paused.
        speed: Animation speed multiplier.
        fps: Measured frames per second (updated each frame).
        merge_count: Total number of merges that have occurred.
        split_count: Total number of splits that have occurred.
    """

    def __init__(self, width: int = 40, height: int = 30, theme: str = "classic",
                 num_blobs: int = 8, num_bubbles: int = 5, speed: float = 1.0):
        """Initialize the lava lamp.

        Args:
            width: Rendering width in terminal characters.
            height: Rendering height in terminal rows.
            theme: Theme name (key in THEMES dict).
            num_blobs: Number of wax blobs to simulate.
            num_bubbles: Number of rising bubbles.
            speed: Animation speed multiplier (0.5 = slow, 2.0 = fast).

        Raises:
            ValueError: If theme is not found in THEMES.
        """
        if theme not in THEMES:
            raise ValueError(
                f"Unknown theme '{theme}'. Available: {', '.join(THEMES.keys())}")
        self.width = width
        self.height = height
        self.theme_name = theme
        self.theme = THEMES[theme]
        self.time = 0.0
        self.paused = False
        self.speed = speed
        self.fps = 0.0
        self.merge_count = 0
        self.split_count = 0

        # Create initial blobs
        self.blobs: List[Blob] = []
        for _ in range(num_blobs):
            self.blobs.append(Blob(self.theme["wax"], self.theme["heat"]))

        # Create rising bubbles
        self.bubbles: List[Bubble] = []
        for _ in range(num_bubbles):
            self.bubbles.append(Bubble(width, height))

        # Pre-compute lamp shape
        self._compute_shape()

    def switch_theme(self, theme_name: str):
        """Switch to a new color theme.

        Args:
            theme_name: Name of the theme to switch to.

        Raises:
            ValueError: If theme is not found.
        """
        if theme_name not in THEMES:
            raise ValueError(
                f"Unknown theme '{theme_name}'. Available: {', '.join(THEMES.keys())}")
        self.theme_name = theme_name
        self.theme = THEMES[theme_name]
        # Update blob colors
        for blob in self.blobs:
            blob.colors = self.theme["wax"]
            blob.heat_color = self.theme["heat"]
            blob.color_idx = random.randint(0, len(blob.colors) - 1)

    def _compute_shape(self):
        """Pre-compute lamp shape widths for each row."""
        self.shape_points = []
        for i in range(self.height + 4):  # extra rows for cap and base
            y = i / (self.height + 3)
            w = self._shape_width(y)
            self.shape_points.append(w)

    def _shape_width(self, y: float) -> float:
        """Return relative width (0-1) of the lamp at position y (0=top, 1=bottom).

        The shape creates a classic lava lamp silhouette with a narrow cap,
        a wide body that tapers, and a solid base. Values of y outside [0, 1]
        are clamped to avoid negative widths.

        Args:
            y: Vertical position (0=top, 1=bottom).

        Returns:
            Relative width between 0 and 1.
        """
        y = max(0.0, min(1.0, y))  # clamp to valid range
        # Cap (top): y=0..0.05
        if y < 0.05:
            return 0.15 + 0.2 * (y / 0.05)
        # Neck transition: y=0.05..0.15
        elif y < 0.15:
            t = (y - 0.05) / 0.1
            return 0.35 + 0.4 * t
        # Main body: y=0.15..0.75 (widest)
        elif y < 0.75:
            t = (y - 0.15) / 0.6
            # Gentle curve with a bulge
            return 0.75 + 0.15 * math.sin(t * math.pi)
        # Lower body narrowing: y=0.75..0.88
        elif y < 0.88:
            t = (y - 0.75) / 0.13
            return 0.75 - 0.35 * t
        # Base: y=0.88..1.0
        else:
            t = (y - 0.88) / 0.12
            return 0.4 + 0.1 * t

    def _y_to_row(self, y: float) -> int:
        """Convert normalized y (0=top, 1=bottom) to screen row."""
        return int(2 + y * (self.height - 1))

    def _row_to_y(self, row: int) -> float:
        """Convert screen row to normalized y (0=top, 1=bottom).

        Clamped to [0, 1] to avoid negative y values that would cause
        negative shape widths and broken rendering at the top of the lamp.
        """
        y = (row - 2) / max(1, self.height - 1)
        return max(0.0, min(1.0, y))

    def _try_merge_blobs(self):
        """Attempt to merge nearby blobs into larger ones.

        When two blobs are within MERGE_DISTANCE of each other and neither is
        on merge cooldown, they combine: the larger absorbs the smaller, gaining
        its area (radius increases), and the smaller is removed.

        This creates the satisfying "blobs joining together" effect seen in
        real lava lamps.
        """
        if len(self.blobs) < 2:
            return

        merged = set()
        new_blobs = []

        for i in range(len(self.blobs)):
            if i in merged:
                continue
            for j in range(i + 1, len(self.blobs)):
                if j in merged:
                    continue
                bi = self.blobs[i]
                bj = self.blobs[j]

                # Skip if on cooldown
                if bi.merge_cooldown > 0 or bj.merge_cooldown > 0:
                    continue

                dx = bi.x - bj.x
                dy = bi.y - bj.y
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < MERGE_DISTANCE:
                    # Merge: keep the larger blob, absorb the smaller
                    if bi.radius >= bj.radius:
                        # bi absorbs bj
                        # Conserve area: π*r1² + π*r2² = π*r_new²
                        new_r = math.sqrt(bi.radius ** 2 + bj.radius ** 2)
                        bi.radius = min(0.12, new_r)
                        bi.base_radius = bi.radius
                        bi.merge_cooldown = MERGE_COOLDOWN
                        bi.vy = (bi.vy + bj.vy) / 2  # average velocity
                        merged.add(j)
                    else:
                        # bj absorbs bi
                        new_r = math.sqrt(bi.radius ** 2 + bj.radius ** 2)
                        bj.radius = min(0.12, new_r)
                        bj.base_radius = bj.radius
                        bj.merge_cooldown = MERGE_COOLDOWN
                        bj.vy = (bi.vy + bj.vy) / 2
                        merged.add(i)
                        break  # bi is gone, stop checking for it

        self.blobs = [b for idx, b in enumerate(self.blobs) if idx not in merged]
        self.merge_count += len(merged)

    def _try_split_blobs(self):
        """Attempt to split large blobs into two smaller ones.

        When a blob's radius exceeds SPLIT_RADIUS_THRESHOLD and it's not on
        split cooldown, it may spontaneously split into two blobs with smaller
        radii, simulating a large wax mass breaking apart.
        """
        new_blobs = []
        to_remove = set()

        for i, blob in enumerate(self.blobs):
            if blob.split_cooldown > 0:
                continue
            if blob.radius < SPLIT_RADIUS_THRESHOLD:
                continue
            # Random chance to split (makes it feel organic, not deterministic)
            if random.random() > 0.005:
                continue

            # Split: conserve area → each new blob has radius r/sqrt(2)
            new_r = blob.radius / math.sqrt(2)
            new_r = max(0.03, min(0.08, new_r))  # clamp

            # Create two daughter blobs
            b1 = Blob(self.theme["wax"], self.theme["heat"])
            b1.x = blob.x - 0.03
            b1.y = blob.y
            b1.radius = new_r
            b1.base_radius = new_r
            b1.vy = blob.vy - 0.02  # one goes slightly up
            b1.merge_cooldown = MERGE_COOLDOWN  # don't immediately re-merge
            b1.split_cooldown = SPLIT_COOLDOWN
            b1.life = blob.life
            b1.color_idx = blob.color_idx

            b2 = Blob(self.theme["wax"], self.theme["heat"])
            b2.x = blob.x + 0.03
            b2.y = blob.y
            b2.radius = new_r
            b2.base_radius = new_r
            b2.vy = blob.vy + 0.02  # one goes slightly down
            b2.merge_cooldown = MERGE_COOLDOWN
            b2.split_cooldown = SPLIT_COOLDOWN
            b2.life = blob.life
            b2.color_idx = (blob.color_idx + 1) % len(self.theme["wax"])

            new_blobs.extend([b1, b2])
            to_remove.add(i)

        # Remove split blobs and add new ones
        self.blobs = [b for idx, b in enumerate(self.blobs) if idx not in to_remove]
        self.blobs.extend(new_blobs)
        self.split_count += len(to_remove)

    def update(self, dt: float):
        """Advance the simulation by dt seconds.

        Updates all blob and bubble physics, then attempts merges and splits.
        Negative or zero dt values are safely ignored.

        Args:
            dt: Time delta in seconds. Negative values are clamped to 0.
        """
        if self.paused:
            return

        if dt <= 0:
            return  # Ignore zero or negative time deltas

        effective_dt = min(dt, 0.1)  # cap to prevent large jumps
        self.time += effective_dt

        for blob in self.blobs:
            blob.update(effective_dt, self.speed)

        # Update bubbles and respawn dead ones
        for i, bubble in enumerate(self.bubbles):
            if not bubble.update(effective_dt * self.speed):
                self.bubbles[i] = Bubble(self.width, self.height)

        # Try merge and split (dynamic blob count)
        self._try_merge_blobs()
        self._try_split_blobs()

    def render(self) -> List[str]:
        """Render the lava lamp to a list of ANSI-colored strings.

        Returns a list of strings, one per row, containing the full rendered
        lamp with background, blobs, glow effects, bubbles, outline, and
        a status bar with theme info.
        """
        lines = []

        bg = self.theme["bg"]
        lamp_c = self.theme["lamp"]
        glow_c = self.theme["glow"]
        heat_c = self.theme["heat"]

        for row in range(self.height):
            y = self._row_to_y(row)
            lamp_w = self._shape_width(y)

            # Compute center and edges
            center = self.width // 2
            half_w = int(lamp_w * self.width / 2)
            left = center - half_w
            right = center + half_w

            line_parts = []  # Use list for faster string building
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

                        # Distance from blob center (squish horizontally for oval shape)
                        dx = bx - blob_screen_x
                        dy = by - blob_screen_y
                        dist = math.sqrt(dx * dx * 4 + dy * dy)

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

                    # Check bubble influence at this pixel
                    bubble_density = 0.0
                    for bubble in self.bubbles:
                        bub_dx = bx - bubble.x
                        bub_dy = by - bubble.y
                        bub_dist = math.sqrt(bub_dx * bub_dx * 4 + bub_dy * bub_dy)
                        if bub_dist < 0.06:
                            bub_core = max(0, 1.0 - bub_dist / 0.06)
                            bubble_density += bub_core

                    # Near edges: darken slightly for depth effect
                    edge_dist = min(bx - 0, 1 - bx)
                    edge_fade = min(1.0, edge_dist * 8)

                    # Heat source glow at bottom
                    heat_intensity = max(0, (y - 0.8) / 0.2) * 0.3  # glow in bottom 20%
                    # Add subtle pulsing to heat
                    heat_intensity *= (0.8 + 0.2 * math.sin(self.time * 3.0))

                    if density > 0.05:
                        # Wax color
                        fr = min(255, blob_colors_r / density)
                        fg_c = min(255, blob_colors_g / density)
                        fb = min(255, blob_colors_b / density)

                        # Blend with background based on density
                        alpha = min(1.0, density)
                        alpha *= edge_fade

                        # Add heat glow tint near bottom
                        if heat_intensity > 0:
                            fr = min(255, fr + heat_c[0] * heat_intensity)
                            fg_c = min(255, fg_c + heat_c[1] * heat_intensity * 0.5)
                            fb = min(255, fb + heat_c[2] * heat_intensity * 0.3)

                        # Blend wax color with background
                        r_val = int(bg[0] * (1 - alpha) + fr * alpha)
                        g_val = int(bg[1] * (1 - alpha) + fg_c * alpha)
                        b_val = int(bg[2] * (1 - alpha) + fb * alpha)

                        # Pick character based on density
                        idx = min(len(WAX_CHARS) - 1, int(density * len(WAX_CHARS)))
                        ch = WAX_CHARS[idx]

                        line_parts.append(
                            rgb_to_ansi(r_val, g_val, b_val) +
                            rgb_to_ansi(r_val, g_val, b_val, fg=False) + ch + esc(0))

                    elif bubble_density > 0.3:
                        # Bubble rendering — small bright highlight
                        b_alpha = min(1.0, bubble_density) * edge_fade
                        br = int(min(255, bg[0] * (1 - b_alpha) + 220 * b_alpha))
                        bg_c = int(min(255, bg[1] * (1 - b_alpha) + 230 * b_alpha))
                        bb = int(min(255, bg[2] * (1 - b_alpha) + 240 * b_alpha))
                        bub_char = random.choice(["·", "∘", "°"]) if bubble_density > 0.6 else "·"
                        line_parts.append(rgb_to_ansi(br, bg_c, bb) + bub_char + esc(0))

                    elif glow > 0.05:
                        # Glow around wax
                        alpha = min(1.0, glow) * edge_fade
                        r_val = int(bg[0] * (1 - alpha) + glow_c[0] * alpha)
                        g_val = int(bg[1] * (1 - alpha) + glow_c[1] * alpha)
                        b_val = int(bg[2] * (1 - alpha) + glow_c[2] * alpha)

                        # Add heat tint
                        if heat_intensity > 0:
                            r_val = int(min(255, r_val + heat_c[0] * heat_intensity * 0.4))
                            g_val = int(min(255, g_val + heat_c[1] * heat_intensity * 0.2))

                        idx = min(len(GLOW_CHARS) - 1, int(glow * len(GLOW_CHARS)))
                        ch = GLOW_CHARS[idx]

                        line_parts.append(
                            rgb_to_ansi(r_val, g_val, b_val) +
                            rgb_to_ansi(r_val, g_val, b_val, fg=False) + ch + esc(0))

                    elif heat_intensity > 0.05:
                        # Bottom heat glow (no blob or glow here, just heat)
                        r_val = int(min(255, bg[0] * (1 - heat_intensity) + heat_c[0] * heat_intensity))
                        g_val = int(min(255, bg[1] * (1 - heat_intensity) + heat_c[1] * heat_intensity * 0.5))
                        b_val = int(min(255, bg[2] * (1 - heat_intensity) + heat_c[2] * heat_intensity * 0.3))
                        line_parts.append(
                            rgb_to_ansi(r_val, g_val, b_val) +
                            rgb_to_ansi(r_val, g_val, b_val, fg=False) + "░" + esc(0))

                    else:
                        # Inside lamp, no blob — subtle depth shading
                        depth = 0.5 + 0.5 * math.sin((bx - 0.5) * math.pi)
                        r_val = int(bg[0] * (1 - depth * 0.3) + lamp_c[0] * depth * 0.3)
                        g_val = int(bg[1] * (1 - depth * 0.3) + lamp_c[1] * depth * 0.3)
                        b_val = int(bg[2] * (1 - depth * 0.3) + lamp_c[2] * depth * 0.3)

                        line_parts.append(rgb_to_ansi(r_val, g_val, b_val) + " " + esc(0))

                elif col == left - 1 or col == right + 1:
                    # Lamp outline
                    outline_r = min(255, lamp_c[0] + 60)
                    outline_g = min(255, lamp_c[1] + 40)
                    outline_b = min(255, lamp_c[2] + 60)
                    line_parts.append(rgb_to_ansi(outline_r, outline_g, outline_b) + "│" + esc(0))
                else:
                    # Outside lamp — dark background
                    line_parts.append(rgb_to_ansi(bg[0], bg[1], bg[2]) + " " + esc(0))

            lines.append("".join(line_parts))

        # Base with heat indicator
        base_parts = []
        center = self.width // 2
        heat_pulse = 0.7 + 0.3 * math.sin(self.time * 2.0)
        for col in range(self.width):
            dist = abs(col - center)
            if dist < 8:
                # Heat glow at base center
                intensity = max(0, (8 - dist) / 8) * heat_pulse
                br = int(min(255, lamp_c[0] + 40 + heat_c[0] * intensity * 0.3))
                bg_c = int(min(255, lamp_c[1] + 20 + heat_c[1] * intensity * 0.2))
                bb = int(min(255, lamp_c[2] + 40 + heat_c[2] * intensity * 0.15))
                base_parts.append(rgb_to_ansi(br, bg_c, bb) + "▀" + esc(0))
            elif dist < 10:
                base_parts.append(rgb_to_ansi(
                    min(255, lamp_c[0] + 20),
                    min(255, lamp_c[1] + 10),
                    min(255, lamp_c[2] + 20)
                ) + "▀" + esc(0))
            else:
                base_parts.append(rgb_to_ansi(bg[0], bg[1], bg[2]) + " " + esc(0))
        lines.append("".join(base_parts))

        # Cap
        cap_parts = []
        for col in range(self.width):
            if abs(col - center) < 4:
                cap_parts.append(rgb_to_ansi(
                    min(255, lamp_c[0] + 60),
                    min(255, lamp_c[1] + 40),
                    min(255, lamp_c[2] + 60)
                ) + "▄" + esc(0))
            elif abs(col - center) < 6:
                cap_parts.append(rgb_to_ansi(
                    min(255, lamp_c[0] + 30),
                    min(255, lamp_c[1] + 20),
                    min(255, lamp_c[2] + 30)
                ) + "▄" + esc(0))
            else:
                cap_parts.append(rgb_to_ansi(bg[0], bg[1], bg[2]) + " " + esc(0))

        # Insert cap at top
        lines.insert(0, "".join(cap_parts))

        # Title
        status = "PAUSED" if self.paused else ""
        title = f"✦ {self.theme['name'].upper()} LAVA LAMP ✦"
        if status:
            title += f"  [{status}]"
        title_line = rgb_to_ansi(180, 180, 200) + title.center(self.width) + esc(0)

        return [title_line, ""] + lines


# ── Main ──────────────────────────────────────────────────────────────────

def parse_args():
    """Parse command-line arguments.

    Returns:
        Parsed argparse.Namespace object with all options.
    """
    parser = argparse.ArgumentParser(
        description="Terminal Lava Lamp — A mesmerizing ASCII lava lamp simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Themes: classic, ocean, toxic, sunset, neon, aurora, ember, frost

Controls while running:
  1-8      Switch theme
  +/=      Increase speed
  -/_      Decrease speed
  p        Pause / Resume
  b        Add a blob
  d        Remove a blob
  r        Reset (new blobs)
  s        Save screenshot
  q/Ctrl+C Quit

Examples:
  python3 lava_lamp.py                  # Classic theme, default size
  python3 lava_lamp.py --theme ocean    # Ocean theme
  python3 lava_lamp.py --speed 2        # Double speed
  python3 lava_lamp.py --blobs 12       # More blobs for denser look
  python3 lava_lamp.py --theme-file my_themes.json
"""
    )
    parser.add_argument("theme", nargs="?", default="classic",
                        choices=list(THEMES.keys()),
                        help="Color theme (default: classic)")
    parser.add_argument("--theme", dest="theme_flag", choices=list(THEMES.keys()),
                        help="Color theme (alternative to positional arg)")
    parser.add_argument("--theme-file", dest="theme_file", default=None,
                        help="Load additional themes from a JSON file")
    parser.add_argument("-W", "--width", type=int, default=None,
                        help="Terminal width (default: auto-detect)")
    parser.add_argument("-H", "--height", type=int, default=None,
                        help="Terminal height (default: auto-detect)")
    parser.add_argument("--blobs", type=int, default=8,
                        help="Number of wax blobs (default: 8, min: 1)")
    parser.add_argument("--bubbles", type=int, default=5,
                        help="Number of rising bubbles (default: 5)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Animation speed multiplier (default: 1.0)")
    parser.add_argument("--fps", type=int, default=15,
                        help="Target frames per second (default: 15)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    # Merge positional and flag theme
    if args.theme_flag:
        args.theme = args.theme_flag

    # Validate ranges
    if args.blobs < 1:
        parser.error(f"Need at least 1 blob, got {args.blobs}")
    if args.bubbles < 0:
        parser.error(f"Bubbles must be non-negative, got {args.bubbles}")
    if args.speed <= 0:
        parser.error(f"Speed must be positive, got {args.speed}")
    if not (1 <= args.fps <= 60):
        parser.error(f"FPS must be between 1 and 60, got {args.fps}")

    # Load custom themes if provided
    if args.theme_file:
        try:
            custom_themes = load_themes_from_file(args.theme_file)
            THEMES.update(custom_themes)
            # Update theme choices for argparse (for future validation)
            print(f"Loaded {len(custom_themes)} custom theme(s): "
                  f"{', '.join(custom_themes.keys())}")
            # If the selected theme is one of the new ones, it's valid now
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
            parser.error(f"Error loading theme file: {e}")

    # Validate theme exists (after potentially loading custom themes)
    if args.theme not in THEMES:
        parser.error(f"Unknown theme '{args.theme}'. Available: {', '.join(THEMES.keys())}")

    return args


def main():
    """Run the lava lamp simulation."""
    args = parse_args()

    # Detect terminal size
    try:
        cols, rows = os.get_terminal_size()
    except OSError:
        cols, rows = 44, 34

    width = args.width if args.width else max(30, min(60, cols - 4))
    height = args.height if args.height else max(20, min(40, rows - 6))

    # Clamp to reasonable values
    width = max(20, min(120, width))
    height = max(15, min(60, height))

    lamp = LavaLamp(
        width=width, height=height,
        theme=args.theme,
        num_blobs=args.blobs,
        num_bubbles=args.bubbles,
        speed=args.speed,
    )

    clear_screen()
    hide_cursor()

    # Set terminal to cbreak mode for single-character key input
    old_term_settings = None
    try:
        old_term_settings = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
    except (termios.error, OSError, AttributeError):
        # Not a real terminal (e.g., piped input) — skip terminal mode setup
        pass

    running = True

    def handle_sigint(sig, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_sigint)

    last_time = time.time()
    fps_target = args.fps
    frame_time = 1.0 / fps_target
    theme_keys = list(THEMES.keys())
    frame_count = 0
    fps_update_time = last_time

    # Screenshot counter for unique filenames
    screenshot_count = 0

    try:
        while running:
            now = time.time()
            dt = now - last_time
            last_time = now

            # FPS tracking (update every 0.5s for smooth display)
            frame_count += 1
            if now - fps_update_time >= 0.5:
                lamp.fps = frame_count / max(0.001, now - fps_update_time)
                frame_count = 0
                fps_update_time = now

            # Update simulation
            lamp.update(dt)

            # Render
            output_lines = lamp.render()
            move_cursor(1, 1)
            for line in output_lines:
                sys.stdout.write(line + "\n")

            # Status bar with FPS, time, blob count, and controls
            elapsed = int(lamp.time)
            mins, secs = divmod(elapsed, 60)
            speed_display = f"{lamp.speed:.2f}x"
            status_parts = [
                f"Speed:{speed_display}",
                f"Blobs:{len(lamp.blobs)}",
                f"Time:{mins}:{secs:02d}",
                f"FPS:{lamp.fps:.0f}",
            ]
            if lamp.merge_count > 0:
                status_parts.append(f"Merges:{lamp.merge_count}")
            if lamp.split_count > 0:
                status_parts.append(f"Splits:{lamp.split_count}")
            status_line = "  ".join(status_parts)
            controls = "│ [1-8]themes [+/-]speed [p]ause [b]add [d]el [r]eset [s]ave [q]uit"
            sys.stdout.write(
                rgb_to_ansi(120, 120, 140) +
                status_line.ljust(width) + "\n" +
                rgb_to_ansi(100, 100, 120) +
                controls.ljust(width) + esc(0) + "\n")
            sys.stdout.flush()

            # Check for keypress (non-blocking)
            try:
                import select as _select
                if _select.select([sys.stdin], [], [], 0)[0]:
                    key = sys.stdin.read(1)
                    if key in ('q', 'Q'):
                        break
                    elif key in '12345678':
                        idx = int(key) - 1
                        if idx < len(theme_keys):
                            try:
                                lamp.switch_theme(theme_keys[idx])
                            except ValueError:
                                pass
                    elif key in ('+', '='):
                        lamp.speed = min(5.0, lamp.speed + 0.25)
                    elif key in ('-', '_'):
                        lamp.speed = max(0.25, lamp.speed - 0.25)
                    elif key in ('p', 'P'):
                        lamp.paused = not lamp.paused
                    elif key in ('b', 'B'):
                        lamp.blobs.append(Blob(lamp.theme["wax"], lamp.theme["heat"]))
                    elif key in ('d', 'D'):
                        # Remove a random blob (if any exist)
                        if len(lamp.blobs) > 1:
                            idx = random.randint(0, len(lamp.blobs) - 1)
                            lamp.blobs.pop(idx)
                    elif key in ('r', 'R'):
                        # Reset all blobs
                        lamp.blobs = [Blob(lamp.theme["wax"], lamp.theme["heat"])
                                      for _ in range(args.blobs)]
                        lamp.bubbles = [Bubble(width, height) for _ in range(args.bubbles)]
                        lamp.time = 0.0
                        lamp.merge_count = 0
                        lamp.split_count = 0
                    elif key in ('s', 'S'):
                        # Save screenshot
                        screenshot_count += 1
                        filename = f"lava_lamp_screenshot_{screenshot_count}.txt"
                        plain_filename = f"lava_lamp_screenshot_{screenshot_count}_plain.txt"
                        Screenshot.save_ansi(output_lines, filename)
                        Screenshot.save_plain(output_lines, plain_filename)
            except (ImportError, OSError, ValueError):
                pass

            # Frame rate limiting
            elapsed_frame = time.time() - now
            if elapsed_frame < frame_time:
                time.sleep(frame_time - elapsed_frame)

    except Exception as e:
        # Log error but don't crash silently — print traceback to stderr
        import traceback
        traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
    finally:
        # Restore terminal settings
        if old_term_settings is not None:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_term_settings)
            except (termios.error, OSError):
                pass
        show_cursor()
        move_cursor(height + 8, 1)
        print(rgb_to_ansi(180, 180, 200) + "✦ Lava lamp powered off ✦" + esc(0))


if __name__ == "__main__":
    main()