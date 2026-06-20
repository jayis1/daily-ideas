#!/usr/bin/env python3
"""
Procedural Cathedral Generator
Generates random ASCII art gothic cathedrals with spires, rose windows,
flying buttresses, arched doors, and stained glass patterns.
"""

import random
import sys
import math
import argparse


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


# ── Canvas ──────────────────────────────────────────────────────────

class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.g = [[" "] * w for _ in range(h)]

    def put(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = ch

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.g[y][x]
        return ""

    def rect(self, x, y, w, h, ch):
        for dy in range(h):
            for dx in range(w):
                self.put(x + dx, y + dy, ch)

    def render(self):
        lines = []
        for row in self.g:
            lines.append("".join(row).rstrip())
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)


# ── Drawing primitives ──────────────────────────────────────────────

def line(canvas, x0, y0, x1, y1, ch):
    """Bresenham's line."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        canvas.put(x0, y0, ch)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def circle(canvas, cx, cy, r, ch, aspect=0.5):
    """Draw circle outline with character aspect ratio correction."""
    for a in range(360):
        rad = math.radians(a)
        x = int(round(cx + r * math.cos(rad) * aspect))
        y = int(round(cy + r * math.sin(rad)))
        canvas.put(x, y, ch)


def filled_circle(canvas, cx, cy, r, fill_ch, border_ch=None, aspect=0.5):
    """Draw filled circle."""
    for y_off in range(-r, r + 1):
        for x_off in range(-2 * r, 2 * r + 1):
            dist = math.sqrt((x_off / (2 * aspect)) ** 2 + y_off ** 2)
            if dist < r:
                canvas.put(cx + x_off, cy + y_off, fill_ch)
            if border_ch and abs(dist - r) < 1.0:
                canvas.put(cx + x_off, cy + y_off, border_ch)


# ── Cathedral components ───────────────────────────────────────────

def draw_pointed_arch(canvas, cx, y_top, width, height, ch, fill=" "):
    """Draw a gothic pointed arch. cx is center, y_top is the apex."""
    half = width // 2
    # Draw the arch outline from top down
    for dy in range(height):
        t = dy / max(height - 1, 1)
        # Pointed arch shape: narrow at top, widening rapidly then slowly
        hw = int(half * (0.1 + 0.9 * (t ** 0.5)))
        y = y_top + dy
        canvas.put(cx - hw, y, ch)
        canvas.put(cx + hw, y, ch)
        # Fill interior
        if fill and dy > 0 and dy < height - 1:
            for dx in range(1, hw):
                canvas.put(cx - hw + dx, y, fill)
                canvas.put(cx + hw - dx, y, fill)


def draw_spire(canvas, cx, base_y, height, ch=S["wall2"]):
    """Draw a spire with cross on top."""
    # Cross
    canvas.put(cx, base_y - height - 2, "✝")
    canvas.put(cx, base_y - height - 1, "│")

    # Tapered spire
    for dy in range(height):
        y = base_y - height + dy
        t = dy / max(height - 1, 1)
        half_w = max(1, int(3 * t + 0.5))
        for dx in range(-half_w, half_w + 1):
            if abs(dx) == half_w:
                canvas.put(cx + dx, y, ch)
            elif dx == 0:
                canvas.put(cx + dx, y, S["pipe"])
            else:
                canvas.put(cx + dx, y, S["wall3"])


def draw_rose_window(canvas, cx, cy, radius):
    """Draw an ornate rose window with petal pattern."""
    # Outer ring
    circle(canvas, cx, cy, radius, S["wall"], aspect=0.5)
    # Inner ring
    if radius > 3:
        circle(canvas, cx, cy, radius - 2, S["wall2"], aspect=0.5)

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
                canvas.put(cx + x_off, cy + y_off, ch)

    # Radial spokes
    for spoke in range(6):
        angle = spoke * math.pi / 3
        for r in range(2, radius):
            px = int(round(cx + r * math.cos(angle) * 0.5))
            py = int(round(cy + r * math.sin(angle)))
            canvas.put(px, py, S["wall2"])

    # Center
    canvas.put(cx, cy, random.choice(ROSE))


def draw_glass_window(canvas, cx, y_top, width, height):
    """Draw a tall stained glass window with pointed arch."""
    half = width // 2
    # Arch outline
    for dy in range(height):
        t = dy / max(height - 1, 1)
        hw = int(half * (0.12 + 0.88 * (t ** 0.5)))
        y = y_top + dy
        canvas.put(cx - hw, y, S["wall"])
        canvas.put(cx + hw, y, S["wall"])
        # Glass fill
        if 0 < dy < height - 1:
            for dx in range(1, hw):
                section = int(math.atan2(1, dx / max(dy, 1)) * 3) % len(GLASS)
                canvas.put(cx - hw + dx, y, GLASS[(dx + dy) % len(GLASS)])
                canvas.put(cx + hw - dx, y, GLASS[(dx + dy + 3) % len(GLASS)])
    # Keystone at top
    canvas.put(cx, y_top, "◇")


def draw_door(canvas, cx, y_top, width, height):
    """Draw a gothic arched door."""
    half = width // 2
    # Arch
    for dy in range(height):
        t = dy / max(height - 1, 1)
        hw = int(half * (0.12 + 0.88 * (t ** 0.5)))
        y = y_top + dy
        canvas.put(cx - hw, y, S["wall"])
        canvas.put(cx + hw, y, S["wall"])
        if 0 < dy < height - 1:
            for dx in range(1, hw):
                canvas.put(cx - hw + dx, y, S["shadow"])
                canvas.put(cx + hw - dx, y, S["shadow"])
    # Door panels
    panel_y_start = y_top + height // 3
    for y in range(panel_y_start, y_top + height - 1):
        if y < canvas.h:
            canvas.put(cx, y, S["pipe"])
    # Handle
    canvas.put(cx + 1, y_top + height - 3, "⬤")
    canvas.put(cx - 1, y_top + height - 3, "⬤")


def draw_buttress(canvas, x, y_attach, y_ground, direction):
    """Draw a flying buttress. direction: -1=left, 1=right."""
    span = random.randint(5, 8)
    pier_x = x + direction * span
    height = y_ground - y_attach

    # Outer pier
    for y in range(y_attach, y_ground + 1):
        canvas.put(pier_x, y, S["wall"])
        canvas.put(pier_x + 1, y, S["wall"])

    # Pinnacle
    canvas.put(pier_x, y_attach - 2, "▴")
    canvas.put(pier_x + 1, y_attach - 2, "▴")
    for y in range(y_attach - 1, y_attach):
        canvas.put(pier_x, y, S["wall2"])
        canvas.put(pier_x + 1, y, S["wall2"])

    # Flying arch
    for i in range(span + 1):
        t = i / span
        arch_y = int(y_attach - 4 * t * (1 - t) * min(3, span // 3))
        wall_y = y_attach + int(height * (1 - t) * 0.3)
        actual_y = min(wall_y, y_attach + height // 4) + arch_y
        if actual_y < y_ground:
            canvas.put(x + direction * i, actual_y, S["wall2"])
            canvas.put(x + direction * i, actual_y + 1, S["wall2"])


def draw_gargoyle(canvas, x, y, direction):
    """Draw a small gargoyle."""
    if direction > 0:
        art = [" ▄▀█ ", "▀██▀ ", " ╧╧  "]
    else:
        art = [" █▀▄ ", " ▀██▀", "  ╧╧ "]
    for dy, row in enumerate(art):
        for dx, ch in enumerate(row):
            if ch != " ":
                canvas.put(x + dx, y + dy, ch)


# ── Main generation ─────────────────────────────────────────────────

def generate_cathedral(seed=None, width=100, height=50):
    """Generate a full procedural gothic cathedral."""
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
    door_width = random.choice([6, 8])
    has_double_door = random.choice([True, False, False])

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
    canvas.rect(0, ground_y, width, 3, "▀")

    # Foundation steps
    for step in range(3):
        sw = body_width + 8 + step * 4
        sx = cx - sw // 2
        canvas.rect(sx, ground_y - step, sw, 1, S["wall2"])

    # ── Main body walls ──────────────────────────────────────────────
    # Left wall
    canvas.rect(body_left, body_top, 2, body_height, S["wall"])
    # Right wall
    canvas.rect(body_right - 2, body_top, 2, body_height, S["wall"])
    # Top cap
    canvas.rect(body_left, body_top, body_width, 1, S["wall"])

    # Wall texture - horizontal courses
    for y in range(body_top + 4, ground_y, 3):
        canvas.put(body_left, y, S["tee_l"])
        canvas.put(body_right - 1, y, S["tee_r"])
        for x in range(body_left + 2, body_right - 1, 5):
            if canvas.get(x, y) == S["wall"]:
                canvas.put(x, y, S["cross"])

    # ── Roof ────────────────────────────────────────────────────────
    roof_h = random.randint(8, 14)
    roof_peak = body_top - roof_h

    line(canvas, body_left + 1, body_top, cx, roof_peak, S["wall2"])
    line(canvas, body_right - 2, body_top, cx, roof_peak, S["wall2"])

    # Fill roof
    for y in range(roof_peak, body_top + 1):
        t = (y - roof_peak) / max(body_top - roof_peak, 1)
        lx = int(cx + (body_left + 1 - cx) * t)
        rx = int(cx + (body_right - 2 - cx) * t)
        for x in range(lx, rx + 1):
            if canvas.get(x, y) == " ":
                canvas.put(x, y, S["shadow"])
        # Ridge
        canvas.put(cx, y, S["wall2"])

    # ── Towers ───────────────────────────────────────────────────────
    # Left tower
    lt_x = body_left - tower_w + 2
    lt_top = ground_y - tower_h
    canvas.rect(lt_x, lt_top, tower_w, tower_h, S["wall"])
    # Tower window
    draw_glass_window(canvas, lt_x + tower_w // 2, lt_top + 3, 4, 8)
    # Tower spire
    spire_h = random.randint(8, 14)
    draw_spire(canvas, lt_x + tower_w // 2, lt_top, spire_h, S["wall2"])
    # Tower cap line
    canvas.rect(lt_x, lt_top, tower_w, 1, S["wall"])
    # Tower courses
    for y in range(lt_top + 3, ground_y, 4):
        canvas.put(lt_x, y, S["tee_l"])
        canvas.put(lt_x + tower_w - 1, y, S["tee_r"])

    # Right tower
    rt_x = body_right - 2
    rt_top = ground_y - tower_h
    canvas.rect(rt_x, rt_top, tower_w, tower_h, S["wall"])
    draw_glass_window(canvas, rt_x + tower_w // 2, rt_top + 3, 4, 8)
    draw_spire(canvas, rt_x + tower_w // 2, rt_top, spire_h, S["wall2"])
    canvas.rect(rt_x, rt_top, tower_w, 1, S["wall"])
    for y in range(rt_top + 3, ground_y, 4):
        canvas.put(rt_x, y, S["tee_l"])
        canvas.put(rt_x + tower_w - 1, y, S["tee_r"])

    # ── Central spire ────────────────────────────────────────────────
    if has_central_spire:
        draw_spire(canvas, cx, roof_peak, random.randint(10, 16), S["wall2"])

    # ── Rose window ──────────────────────────────────────────────────
    if has_rose:
        rose_y = body_top + 5
        draw_rose_window(canvas, cx, rose_y, random.randint(5, 7))

    # ── Side windows ─────────────────────────────────────────────────
    win_h = random.randint(7, 10)
    win_w = random.choice([4, 6])
    win_y = body_top + 3

    # Calculate window positions on left and right halves
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
            canvas.rect(x0 + pos, body_top - 1, mw, 2, S["wall"])
            pos += mw + 2

    # ── Decorative horizontal stringcourse ───────────────────────────
    band_y = body_top + 2 + win_h + 2
    if band_y < ground_y - 4:
        for x in range(body_left + 2, body_right - 1):
            if canvas.get(x, band_y) == " ":
                canvas.put(x, band_y, S["dash"])

    # ── Cross at roof peak ──────────────────────────────────────────
    if not has_central_spire:
        canvas.put(cx, roof_peak - 1, "✝")

    return canvas


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
            canvas.put(sx, sy, random.choice(["✦", "✧", "·", "⋆", "✶", "✷"]))

    # Ground texture
    for x in range(w):
        for y in range(ground_y, h):
            if canvas.get(x, y) == "▀" and random.random() < 0.2:
                canvas.put(x, y, random.choice(["░", "▒", "▓"]))

    return canvas


# ── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🏛️ Procedural Cathedral Generator — generate unique ASCII gothic cathedrals"
    )
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--width", type=int, default=100, help="Canvas width (default: 100)")
    parser.add_argument("--height", type=int, default=50, help="Canvas height (default: 50)")
    parser.add_argument("--no-atmosphere", action="store_true",
                        help="Skip stars and ground texture")
    parser.add_argument("--multi", type=int, default=1,
                        help="Generate multiple cathedrals (default: 1)")
    args = parser.parse_args()

    seed = args.seed if args.seed is not None else random.randint(0, 999999)

    for i in range(args.multi):
        s = seed + i if args.seed is not None else random.randint(0, 999999)

        canvas = generate_cathedral(seed=s, width=args.width, height=args.height)
        if not args.no_atmosphere:
            canvas = add_atmosphere(canvas)

        output = canvas.render()

        print(f"╔════════════════════════════════════════════════════════════════╗")
        print(f"║  🏛️  Procedural Cathedral Generator  —  Seed: {s:<6}          ║")
        print(f"║  Size: {args.width}x{args.height}  |  Re-run with --seed {s} to reproduce  ║")
        print(f"╚════════════════════════════════════════════════════════════════╝")
        print()
        print(output)
        print()

        if args.multi > 1:
            print(f"{'─' * args.width}")
            print()


if __name__ == "__main__":
    main()