#!/usr/bin/env python3
"""
Procedural Cathedral Generator
Generates random ASCII art gothic cathedrals with spires, rose windows,
flying buttresses, arched doors, stained glass patterns, and optional
ANSI color, weather effects, and file output.

Usage:
    python3 cathedral.py                    # Random cathedral
    python3 cathedral.py --seed 42           # Reproducible
    python3 cathedral.py --color             # ANSI colored output
    python3 cathedral.py --weather rain      # Rain effect
    python3 cathedral.py --save output.txt   # Save to file
"""

import random
import sys
import math
import argparse
import json
import os

__version__ = "1.1.0"

# ── Character palettes ──────────────────────────────────────────────

S = {
    "wall": "█",
    "wall2": "▓",
    "wall3": "▒",
    "shadow": "░",
    "dot": "·",
    "dash": "─",
    "pipe": "│",
    "cross": "┼",
    "top": "╤",
    "tee_l": "├",
    "tee_r": "┤",
    "tee_d": "┬",
    "corner_tl": "╔",
    "corner_tr": "╗",
    "corner_bl": "╚",
    "corner_br": "╝",
}

GLASS = ["◆", "◇", "▪", "▫", "●", "○", "✦", "✧", "◈", "⬥", "⬦", "⬡"]
ROSE = ["✿", "❀", "✾", "❁", "✽"]

# ANSI color codes for --color mode
COLORS = {
    "wall":      "\033[37m",      # white/gray stone
    "wall2":     "\033[90m",      # dark gray
    "wall3":     "\033[90m",      # dark gray
    "shadow":    "\033[2;37m",    # dim gray
    "glass":     "\033[35m",      # magenta/purple glass
    "rose":      "\033[33m",      # gold rose window
    "roof":      "\033[31m",      # red-brown roof
    "spire":     "\033[36m",      # cyan spire
    "door":      "\033[33m",      # brown door
    "ground":    "\033[32m",      # green ground
    "star":      "\033[1;33m",    # bright yellow stars
    "moon":      "\033[1;36m",    # bright cyan moon
    "rain":      "\033[34m",      # blue rain
    "snow":      "\033[1;37m",    # bright white snow
    "fog":       "\033[2;37m",   # dim gray fog
    "clock":     "\033[1;33m",   # bright gold clock
    "cross":     "\033[1;37m",   # bright white cross
    "buttress":  "\033[90m",      # dark gray buttress
    "gargoyle":  "\033[90m",      # dark gray gargoyle
    "stringcourse": "\033[33m",  # gold stringcourse
    "reset":     "\033[0m",
}


# ── Canvas ──────────────────────────────────────────────────────────

class Canvas:
    """2D character canvas with optional color metadata per cell."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.g = [[" "] * w for _ in range(h)]
        # Color tags per cell (None = no color)
        self.colors = [[None] * w for _ in range(h)]

    def put(self, x, y, ch, color=None):
        """Place character at (x,y) with optional color tag."""
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch
            if color is not None:
                self.colors[y][x] = color

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.g[y][x]
        return ""

    def get_color(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.colors[y][x]
        return None

    def rect(self, x, y, w, h, ch, color=None):
        for dy in range(h):
            for dx in range(w):
                self.put(x + dx, y + dy, ch, color)

    def render(self, use_color=False):
        """Render canvas to string, optionally with ANSI color codes."""
        lines = []
        for y in range(self.h):
            row_chars = []
            if use_color:
                prev_color = None
                all_empty = True
                # Check if row has any content
                for x in range(self.w):
                    if self.g[y][x] != " ":
                        all_empty = False
                        break
                if all_empty:
                    continue
                for x in range(self.w):
                    ch = self.g[y][x]
                    col = self.colors[y][x]
                    if ch == " ":
                        # Only add space if we're between non-space chars
                        if prev_color is not None:
                            row_chars.append(" ")
                            prev_color = None  # spaces reset color tracking
                        continue
                    if col != prev_color:
                        if col is not None:
                            row_chars.append(COLORS.get(col, ""))
                        else:
                            row_chars.append(COLORS["reset"])
                        prev_color = col
                    row_chars.append(ch)
                # Reset color at end of line
                if prev_color is not None:
                    row_chars.append(COLORS["reset"])
            else:
                for x in range(self.w):
                    row_chars.append(self.g[y][x])
            lines.append("".join(row_chars).rstrip())
        # Trim trailing empty lines
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)


# ── Drawing primitives ──────────────────────────────────────────────

def line(canvas, x0, y0, x1, y1, ch, color=None):
    """Bresenham's line algorithm with optional color."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        canvas.put(x0, y0, ch, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def circle(canvas, cx, cy, r, ch, aspect=0.5, color=None):
    """Draw circle outline with character aspect ratio correction."""
    for a in range(360):
        rad = math.radians(a)
        x = int(round(cx + r * math.cos(rad) * aspect))
        y = int(round(cy + r * math.sin(rad)))
        canvas.put(x, y, ch, color)


def filled_circle(canvas, cx, cy, r, fill_ch, border_ch=None, aspect=0.5, fill_color=None, border_color=None):
    """Draw filled circle with optional border and colors."""
    for y_off in range(-r, r + 1):
        for x_off in range(-2 * r, 2 * r + 1):
            dist = math.sqrt((x_off / (2 * aspect)) ** 2 + y_off ** 2)
            if dist < r:
                canvas.put(cx + x_off, cy + y_off, fill_ch, fill_color)
            if border_ch and abs(dist - r) < 1.0:
                canvas.put(cx + x_off, cy + y_off, border_ch, border_color)


# ── Cathedral components ───────────────────────────────────────────

def draw_pointed_arch(canvas, cx, y_top, width, height, ch, fill=" ", color=None, fill_color=None):
    """Draw a gothic pointed arch. cx is center, y_top is the apex."""
    half = width // 2
    for dy in range(height):
        t = dy / max(height - 1, 1)
        # Pointed arch shape: narrow at top, widening rapidly then slowly
        hw = int(half * (0.1 + 0.9 * (t ** 0.5)))
        y = y_top + dy
        canvas.put(cx - hw, y, ch, color)
        canvas.put(cx + hw, y, ch, color)
        if fill and dy > 0 and dy < height - 1:
            for dx in range(1, hw):
                canvas.put(cx - hw + dx, y, fill, fill_color)
                canvas.put(cx + hw - dx, y, fill, fill_color)


def draw_spire(canvas, cx, base_y, height, ch=S["wall2"], color="spire"):
    """Draw a spire with cross on top."""
    # Cross
    canvas.put(cx, base_y - height - 2, "✝", "cross")
    canvas.put(cx, base_y - height - 1, "│", "cross")

    # Tapered spire
    for dy in range(height):
        y = base_y - height + dy
        t = dy / max(height - 1, 1)
        half_w = max(1, int(3 * t + 0.5))
        for dx in range(-half_w, half_w + 1):
            if abs(dx) == half_w:
                canvas.put(cx + dx, y, ch, color)
            elif dx == 0:
                canvas.put(cx + dx, y, S["pipe"], color)
            else:
                canvas.put(cx + dx, y, S["wall3"], color)


def draw_rose_window(canvas, cx, cy, radius):
    """Draw an ornate rose window with petal pattern and radial spokes."""
    # Outer ring
    circle(canvas, cx, cy, radius, S["wall"], aspect=0.5, color="rose")
    # Inner ring
    if radius > 3:
        circle(canvas, cx, cy, radius - 2, S["wall2"], aspect=0.5, color="rose")

    # Fill glass petals
    for y_off in range(-radius, radius + 1):
        for x_off in range(-2 * radius, 2 * radius + 1):
            dist = math.sqrt((x_off) ** 2 + (4 * y_off ** 2))
            norm_dist = dist / (2 * radius)
            if norm_dist < 0.85 and norm_dist > 0.1:
                angle = math.atan2(y_off * 2, x_off)
                petal = int((angle + math.pi) / (math.pi / 3)) % 6
                ring = int(norm_dist * 4)
                ch = GLASS[(petal + ring) % len(GLASS)]
                canvas.put(cx + x_off, cy + y_off, ch, "glass")

    # Radial spokes
    for spoke in range(6):
        angle = spoke * math.pi / 3
        for r in range(2, radius):
            px = int(round(cx + r * math.cos(angle) * 0.5))
            py = int(round(cy + r * math.sin(angle)))
            canvas.put(px, py, S["wall2"], "rose")

    # Center
    canvas.put(cx, cy, random.choice(ROSE), "rose")


def draw_glass_window(canvas, cx, y_top, width, height):
    """Draw a tall stained glass window with pointed arch."""
    half = width // 2
    # Arch outline
    for dy in range(height):
        t = dy / max(height - 1, 1)
        hw = int(half * (0.12 + 0.88 * (t ** 0.5)))
        y = y_top + dy
        canvas.put(cx - hw, y, S["wall"], "wall")
        canvas.put(cx + hw, y, S["wall"], "wall")
        # Glass fill
        if 0 < dy < height - 1:
            for dx in range(1, hw):
                canvas.put(cx - hw + dx, y, GLASS[(dx + dy) % len(GLASS)], "glass")
                canvas.put(cx + hw - dx, y, GLASS[(dx + dy + 3) % len(GLASS)], "glass")
    # Keystone at top
    canvas.put(cx, y_top, "◇", "glass")


def draw_door(canvas, cx, y_top, width, height):
    """Draw a gothic arched door."""
    half = width // 2
    # Arch
    for dy in range(height):
        t = dy / max(height - 1, 1)
        hw = int(half * (0.12 + 0.88 * (t ** 0.5)))
        y = y_top + dy
        canvas.put(cx - hw, y, S["wall"], "door")
        canvas.put(cx + hw, y, S["wall"], "door")
        if 0 < dy < height - 1:
            for dx in range(1, hw):
                canvas.put(cx - hw + dx, y, S["shadow"], "door")
                canvas.put(cx + hw - dx, y, S["shadow"], "door")
    # Door panels — vertical center line
    panel_y_start = y_top + height // 3
    for y in range(panel_y_start, y_top + height - 1):
        if y < canvas.h:
            canvas.put(cx, y, S["pipe"], "door")
    # Door handles
    canvas.put(cx + 1, y_top + height - 3, "⬤", "door")
    canvas.put(cx - 1, y_top + height - 3, "⬤", "door")


def draw_buttress(canvas, x, y_attach, y_ground, direction):
    """Draw a flying buttress. direction: -1=left, 1=right."""
    span = random.randint(5, 8)
    pier_x = x + direction * span
    height = y_ground - y_attach

    # Outer pier
    for y in range(y_attach, y_ground + 1):
        canvas.put(pier_x, y, S["wall"], "buttress")
        canvas.put(pier_x + 1, y, S["wall"], "buttress")

    # Pinnacle
    canvas.put(pier_x, y_attach - 2, "▴", "buttress")
    canvas.put(pier_x + 1, y_attach - 2, "▴", "buttress")
    for y in range(y_attach - 1, y_attach):
        canvas.put(pier_x, y, S["wall2"], "buttress")
        canvas.put(pier_x + 1, y, S["wall2"], "buttress")

    # Flying arch
    for i in range(span + 1):
        t = i / span
        arch_y = int(y_attach - 4 * t * (1 - t) * min(3, span // 3))
        wall_y = y_attach + int(height * (1 - t) * 0.3)
        actual_y = min(wall_y, y_attach + height // 4) + arch_y
        if actual_y < y_ground:
            canvas.put(x + direction * i, actual_y, S["wall2"], "buttress")
            canvas.put(x + direction * i, actual_y + 1, S["wall2"], "buttress")


def draw_gargoyle(canvas, x, y, direction):
    """Draw a small gargoyle facing left or right."""
    if direction > 0:
        art = [" ▄▀█ ", "▀██▀ ", " ╧╧  "]
    else:
        art = [" █▀▄ ", " ▀██▀", "  ╧╧ "]
    for dy, row in enumerate(art):
        for dx, ch in enumerate(row):
            if ch != " ":
                canvas.put(x + dx, y + dy, ch, "gargoyle")


def draw_clock_face(canvas, cx, cy, radius=3):
    """Draw a circular clock face on a tower with hour markers and hands."""
    # Outer circle
    circle(canvas, cx, cy, radius, S["wall"], aspect=0.5, color="clock")
    # Inner fill
    for y_off in range(-radius, radius + 1):
        for x_off in range(-2 * radius, 2 * radius + 1):
            dist = math.sqrt((x_off / 1.0) ** 2 + (4 * y_off ** 2))
            norm = dist / (2 * radius)
            if norm < 0.7:
                canvas.put(cx + x_off, cy + y_off, S["shadow"], "clock")
    # Hour markers (12 positions)
    for h in range(12):
        angle = math.radians(h * 30 - 90)
        hx = int(round(cx + (radius - 1) * math.cos(angle) * 0.5))
        hy = int(round(cy + (radius - 1) * math.sin(angle)))
        canvas.put(hx, hy, "·", "clock")
    # Hands — show a random time
    hour_angle = math.radians(random.randint(0, 11) * 30 - 90)
    minute_angle = math.radians(random.randint(0, 11) * 30 - 90)
    # Hour hand (short)
    hx = int(round(cx + (radius - 2) * math.cos(hour_angle) * 0.5))
    hy = int(round(cy + (radius - 2) * math.sin(hour_angle)))
    line(canvas, cx, cy, hx, hy, S["pipe"], "clock")
    # Minute hand (long)
    mx = int(round(cx + (radius - 1) * math.cos(minute_angle) * 0.5))
    my = int(round(cy + (radius - 1) * math.sin(minute_angle)))
    line(canvas, cx, cy, mx, my, S["dash"], "clock")
    # Center dot
    canvas.put(cx, cy, "◈", "clock")


# ── Weather effects ──────────────────────────────────────────────────

def add_rain(canvas, seed=None):
    """Add rain streaks to the scene."""
    if seed is not None:
        random.seed(seed)
    w, h = canvas.h, canvas.w  # We use standard w,h below
    w, h = canvas.w, canvas.h
    num_drops = random.randint(40, 80)
    for _ in range(num_drops):
        sx = random.randint(0, w - 1)
        sy = random.randint(0, h - 1)
        length = random.randint(2, 5)
        # Rain falls at a slight angle
        for dy in range(length):
            rx = sx + dy // 3  # slight angle
            ry = sy + dy
            if canvas.get(rx, ry) == " ":
                canvas.put(rx, ry, random.choice(["│", "╎", "┆"]), "rain")
    return canvas


def add_snow(canvas, seed=None):
    """Add snowflakes to the scene."""
    if seed is not None:
        random.seed(seed)
    w, h = canvas.w, canvas.h
    ground_y = h - 3
    # Falling snowflakes
    for _ in range(random.randint(30, 60)):
        sx = random.randint(0, w - 1)
        sy = random.randint(0, h - 2)
        if canvas.get(sx, sy) == " ":
            canvas.put(sx, sy, random.choice(["❅", "❆", "·", "✻", "✼"]), "snow")
    # Snow accumulation on flat surfaces (ground line gets snow)
    for x in range(w):
        if canvas.get(x, ground_y - 1) == " ":
            if random.random() < 0.4:
                canvas.put(x, ground_y - 1, "▀", "snow")
    return canvas


def add_fog(canvas, seed=None):
    """Add fog/mist layers at the base of the cathedral."""
    if seed is not None:
        random.seed(seed)
    w, h = canvas.w, canvas.h
    ground_y = h - 3
    # Fog layers
    for y in range(ground_y - 5, ground_y):
        for x in range(w):
            if canvas.get(x, y) == " " and random.random() < 0.35:
                canvas.put(x, y, random.choice(["░", "▒", "≈", "~"]), "fog")
    return canvas


def add_moon(canvas, seed=None):
    """Add a crescent moon to the upper corner of the scene."""
    if seed is not None:
        random.seed(seed)
    w, h = canvas.w, canvas.h
    # Place moon in upper corner
    side = random.choice([-1, 1])
    if side == -1:
        mx = random.randint(3, w // 4)
    else:
        mx = random.randint(3 * w // 4, w - 4)
    my = random.randint(1, h // 6)

    # Simple crescent moon
    r = 3
    for y_off in range(-r, r + 1):
        for x_off in range(-r, r + 1):
            dist = math.sqrt(x_off ** 2 + y_off ** 2)
            if dist < r and dist > r - 1.2:
                canvas.put(mx + x_off, my + y_off, "●", "moon")
            elif dist < r - 0.5:
                # Check if this point is on the "lit" side (crescent effect)
                offset_dist = math.sqrt((x_off + 1) ** 2 + y_off ** 2)
                if offset_dist >= r - 0.5:
                    canvas.put(mx + x_off, my + y_off, "·", "moon")
    return canvas


# ── Main generation ─────────────────────────────────────────────────

def generate_cathedral(seed=None, width=100, height=50):
    """Generate a full procedural gothic cathedral.

    Returns:
        tuple: (canvas, metadata_dict) where metadata includes seed, dimensions,
               and feature flags for programmatic use.
    """
    if seed is not None:
        random.seed(seed)

    canvas = Canvas(width, height)

    # ── Randomized parameters ────────────────────────────────────────
    num_windows = random.randint(3, 5)
    has_rose = random.choice([True, True, True, False])
    has_central_spire = random.choice([True, True, False])
    has_buttresses = random.choice([True, True, False])
    has_gargoyles = random.choice([True, False])
    has_battlements = random.choice([True, False, False])
    has_clock = random.choice([True, True, False])
    door_width = random.choice([6, 8])
    has_double_door = random.choice([True, False, False])

    # Collect metadata
    metadata = {
        "seed": seed,
        "width": width,
        "height": height,
        "features": {
            "rose_window": has_rose,
            "central_spire": has_central_spire,
            "flying_buttresses": has_buttresses,
            "gargoyles": has_gargoyles,
            "battlements": has_battlements,
            "clock": has_clock,
            "double_door": has_double_door,
            "num_side_windows": num_windows,
            "door_width": door_width,
        }
    }

    # ── Layout ───────────────────────────────────────────────────────
    cx = width // 2
    ground_y = height - 3

    body_width = min(width - 20, random.randint(60, 76))
    body_left = cx - body_width // 2
    body_right = body_left + body_width
    body_height = random.randint(14, 20)
    body_top = ground_y - body_height

    tower_w = random.randint(10, 14)
    tower_h = random.randint(22, min(35, height - 8))

    # ── Ground ──────────────────────────────────────────────────────
    canvas.rect(0, ground_y, width, 3, "▀", "ground")

    # Foundation steps
    for step in range(3):
        sw = body_width + 8 + step * 4
        sx = cx - sw // 2
        canvas.rect(sx, ground_y - step, sw, 1, S["wall2"], "wall")

    # ── Main body walls ──────────────────────────────────────────────
    canvas.rect(body_left, body_top, 2, body_height, S["wall"], "wall")
    canvas.rect(body_right - 2, body_top, 2, body_height, S["wall"], "wall")
    canvas.rect(body_left, body_top, body_width, 1, S["wall"], "wall")

    # Wall texture — horizontal courses
    for y in range(body_top + 4, ground_y, 3):
        canvas.put(body_left, y, S["tee_l"], "wall")
        canvas.put(body_right - 1, y, S["tee_r"], "wall")
        for x in range(body_left + 2, body_right - 1, 5):
            if canvas.get(x, y) == S["wall"]:
                canvas.put(x, y, S["cross"], "wall")

    # ── Roof ────────────────────────────────────────────────────────
    roof_h = random.randint(8, 14)
    roof_peak = body_top - roof_h

    line(canvas, body_left + 1, body_top, cx, roof_peak, S["wall2"], "roof")
    line(canvas, body_right - 2, body_top, cx, roof_peak, S["wall2"], "roof")

    # Fill roof
    for y in range(roof_peak, body_top + 1):
        t = (y - roof_peak) / max(body_top - roof_peak, 1)
        lx = int(cx + (body_left + 1 - cx) * t)
        rx = int(cx + (body_right - 2 - cx) * t)
        for x in range(lx, rx + 1):
            if canvas.get(x, y) == " ":
                canvas.put(x, y, S["shadow"], "roof")
        canvas.put(cx, y, S["wall2"], "roof")

    # ── Towers ───────────────────────────────────────────────────────
    # Left tower
    lt_x = body_left - tower_w + 2
    lt_top = ground_y - tower_h
    canvas.rect(lt_x, lt_top, tower_w, tower_h, S["wall"], "wall")
    draw_glass_window(canvas, lt_x + tower_w // 2, lt_top + 3, 4, 8)
    spire_h = random.randint(8, 14)
    draw_spire(canvas, lt_x + tower_w // 2, lt_top, spire_h)
    canvas.rect(lt_x, lt_top, tower_w, 1, S["wall"], "wall")
    # Tower courses
    for y in range(lt_top + 3, ground_y, 4):
        canvas.put(lt_x, y, S["tee_l"], "wall")
        canvas.put(lt_x + tower_w - 1, y, S["tee_r"], "wall")
    # Clock face on left tower (optional)
    if has_clock:
        clock_y = lt_top + tower_h // 2
        draw_clock_face(canvas, lt_x + tower_w // 2, clock_y, radius=min(3, tower_w // 4))

    # Right tower
    rt_x = body_right - 2
    rt_top = ground_y - tower_h
    canvas.rect(rt_x, rt_top, tower_w, tower_h, S["wall"], "wall")
    draw_glass_window(canvas, rt_x + tower_w // 2, rt_top + 3, 4, 8)
    draw_spire(canvas, rt_x + tower_w // 2, rt_top, spire_h)
    canvas.rect(rt_x, rt_top, tower_w, 1, S["wall"], "wall")
    for y in range(rt_top + 3, ground_y, 4):
        canvas.put(rt_x, y, S["tee_l"], "wall")
        canvas.put(rt_x + tower_w - 1, y, S["tee_r"], "wall")

    # ── Central spire ────────────────────────────────────────────────
    if has_central_spire:
        draw_spire(canvas, cx, roof_peak, random.randint(10, 16))

    # ── Rose window ──────────────────────────────────────────────────
    if has_rose:
        rose_y = body_top + 5
        draw_rose_window(canvas, cx, rose_y, random.randint(5, 7))

    # ── Side windows ─────────────────────────────────────────────────
    win_h = random.randint(7, 10)
    win_w = random.choice([4, 6])
    win_y = body_top + 3

    left_zone_start = body_left + 4
    left_zone_end = cx - door_width // 2 - 3
    right_zone_start = cx + door_width // 2 + 3
    right_zone_end = body_right - 4

    def place_windows(canvas, zone_start, zone_end, win_y, win_h, win_w, n):
        if zone_end <= zone_start or n <= 0:
            return
        spacing = (zone_end - zone_start) // (n + 1)
        for i in range(n):
            wx = zone_start + spacing * (i + 1)
            draw_glass_window(canvas, wx, win_y, win_w, win_h)

    left_n = min(num_windows, max(1, (left_zone_end - left_zone_start) // (win_w + 5)))
    right_n = min(num_windows, max(1, (right_zone_end - right_zone_start) // (win_w + 5)))

    place_windows(canvas, left_zone_start, left_zone_end, win_y, win_h, win_w, left_n)
    place_windows(canvas, right_zone_start, right_zone_end, win_y, win_h, win_w, right_n)

    # ── Door ─────────────────────────────────────────────────────────
    door_h = min(10, body_height - 5)
    door_y = ground_y - door_h - 1
    if has_double_door:
        draw_door(canvas, cx - door_width // 2 - 1, door_y, door_width, door_h)
        draw_door(canvas, cx + door_width // 2 + 1, door_y, door_width, door_h)
    else:
        draw_door(canvas, cx, door_y, door_width, door_h)

    # ── Flying buttresses ────────────────────────────────────────────
    if has_buttresses:
        n_butt = random.randint(2, 3)
        for i in range(n_butt):
            y_att = body_top + 6 + i * 5
            draw_buttress(canvas, body_left - 1, y_att, ground_y - 1, -1)
            draw_buttress(canvas, body_right + 1, y_att, ground_y - 1, 1)

    # ── Gargoyles ────────────────────────────────────────────────────
    if has_gargoyles:
        draw_gargoyle(canvas, body_left - 5, body_top + 2, -1)
        draw_gargoyle(canvas, body_right + 1, body_top + 2, 1)

    # ── Battlements ──────────────────────────────────────────────────
    if has_battlements:
        pos = 0
        x0 = body_left + 2
        end = body_right - 2
        while pos < end - x0:
            mw = min(2, end - x0 - pos)
            canvas.rect(x0 + pos, body_top - 1, mw, 2, S["wall"], "wall")
            pos += mw + 2

    # ── Decorative horizontal stringcourse ───────────────────────────
    band_y = body_top + 2 + win_h + 2
    if band_y < ground_y - 4:
        for x in range(body_left + 2, body_right - 1):
            if canvas.get(x, band_y) == " ":
                canvas.put(x, band_y, S["dash"], "stringcourse")

    # ── Cross at roof peak (if no central spire) ─────────────────────
    if not has_central_spire:
        canvas.put(cx, roof_peak - 1, "✝", "cross")

    return canvas, metadata


def add_atmosphere(canvas, seed=None):
    """Add stars, ground texture, and atmospheric details."""
    if seed is not None:
        random.seed(seed)

    w, h = canvas.w, canvas.h
    ground_y = h - 3

    # Stars
    for _ in range(random.randint(20, 40)):
        sx = random.randint(0, w - 1)
        sy = random.randint(0, h // 3)
        if canvas.get(sx, sy) == " ":
            canvas.put(sx, sy, random.choice(["✦", "✧", "·", "⋆", "✶", "✷"]), "star")

    # Ground texture
    for x in range(w):
        for y in range(ground_y, h):
            if canvas.get(x, y) == "▀" and random.random() < 0.2:
                canvas.put(x, y, random.choice(["░", "▒", "▓"]), "ground")

    # Crescent moon (random chance)
    if random.choice([True, True, False]):
        add_moon(canvas)

    return canvas


# ── Main ────────────────────────────────────────────────────────────

def validate_dimensions(width, height):
    """Validate canvas dimensions, raising SystemExit on invalid values."""
    if width < 40:
        print(f"Error: width must be at least 40 (got {width})", file=sys.stderr)
        sys.exit(1)
    if height < 25:
        print(f"Error: height must be at least 25 (got {height})", file=sys.stderr)
        sys.exit(1)
    if width > 300:
        print(f"Error: width must be at most 300 (got {width})", file=sys.stderr)
        sys.exit(1)
    if height > 150:
        print(f"Error: height must be at most 150 (got {height})", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="🏛️ Procedural Cathedral Generator — generate unique ASCII gothic cathedrals"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility (default: random)")
    parser.add_argument("--width", type=int, default=100,
                        help="Canvas width in characters (default: 100)")
    parser.add_argument("--height", type=int, default=50,
                        help="Canvas height in characters (default: 50)")
    parser.add_argument("--no-atmosphere", action="store_true",
                        help="Skip stars, moon, and ground texture")
    parser.add_argument("--color", action="store_true",
                        help="Enable ANSI color output")
    parser.add_argument("--weather", choices=["rain", "snow", "fog"],
                        default=None, help="Add weather effect: rain, snow, or fog")
    parser.add_argument("--save", type=str, default=None, metavar="FILE",
                        help="Save output to a file instead of stdout")
    parser.add_argument("--json", action="store_true",
                        help="Output cathedral metadata as JSON")
    parser.add_argument("--multi", type=int, default=1,
                        help="Generate N cathedrals with sequential seeds (default: 1)")
    args = parser.parse_args()

    validate_dimensions(args.width, args.height)

    seed = args.seed if args.seed is not None else random.randint(0, 999999)

    all_metadata = []

    for i in range(args.multi):
        s = seed + i if args.seed is not None else random.randint(0, 999999)

        canvas, metadata = generate_cathedral(seed=s, width=args.width, height=args.height)

        if not args.no_atmosphere:
            add_atmosphere(canvas, seed=s + 10000)

        # Weather effects
        if args.weather == "rain":
            add_rain(canvas, seed=s + 20000)
        elif args.weather == "snow":
            add_snow(canvas, seed=s + 30000)
        elif args.weather == "fog":
            add_fog(canvas, seed=s + 40000)

        metadata["seed"] = s
        metadata["weather"] = args.weather
        all_metadata.append(metadata)

        output = canvas.render(use_color=args.color and sys.stdout.isatty())

        # Build header bar
        header = (
            f"╔{'═' * 62}╗\n"
            f"║  🏛️  Procedural Cathedral Generator  —  Seed: {s:<6}          ║\n"
            f"║  Size: {args.width}x{args.height}  |  Re-run with --seed {s} to reproduce  ║\n"
            f"╚{'═' * 62}╝"
        )

        # Output destination
        if args.save:
            with open(args.save, "a", encoding="utf-8") as f:
                f.write(header + "\n\n")
                f.write(output + "\n\n")
                if args.multi > 1:
                    f.write(f"{'─' * args.width}\n\n")
            print(f"Saved cathedral (seed {s}) to {args.save}")
        else:
            print(header)
            print()
            print(output)
            print()

            if args.multi > 1:
                print(f"{'─' * args.width}")
                print()

    # JSON metadata output
    if args.json:
        if len(all_metadata) == 1:
            print(json.dumps(all_metadata[0], indent=2))
        else:
            print(json.dumps(all_metadata, indent=2))


if __name__ == "__main__":
    main()