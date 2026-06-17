#!/usr/bin/env python3
"""
Procedural Heraldry Generator
Generates random medieval-style coats of arms following heraldic rules,
rendered as beautiful colored ASCII shields in the terminal.
"""

import random
import argparse
import sys
import math

# ─── Heraldic Tinctures ───────────────────────────────────────────────
# Colour names, ANSI codes, and metal names follow classic heraldry
TINCTURES = {
    # Metals
    "Or":      {"ansi": "\033[38;5;220m", "bg": "\033[48;5;220m", "class": "metal",   "char": "█"},
    "Argent":  {"ansi": "\033[38;5;255m", "bg": "\033[48;5;255m", "class": "metal",   "char": "█"},
    # Colours
    "Gules":   {"ansi": "\033[38;5;160m", "bg": "\033[48;5;160m", "class": "colour",  "char": "█"},
    "Azure":   {"ansi": "\033[38;5;027m", "bg": "\033[48;5;027m", "class": "colour",  "char": "█"},
    "Sable":   {"ansi": "\033[38;5;232m", "bg": "\033[48;5;232m", "class": "colour",  "char": "█"},
    "Vert":    {"ansi": "\033[38;5;028m", "bg": "\033[48;5;028m", "class": "colour",  "char": "█"},
    "Purpure": {"ansi": "\033[38;5;091m", "bg": "\033[48;5;091m", "class": "colour",  "char": "█"},
}

METALS = [t for t, v in TINCTURES.items() if v["class"] == "metal"]
COLOURS = [t for t, v in TINCTURES.items() if v["class"] == "colour"]
ALL_TINCTURES = list(TINCTURES.keys())

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"

# ─── Shield Shape ─────────────────────────────────────────────────────
# The shield is defined as a grid. Each cell is a boolean indicating
# whether it's inside the shield boundary.
SHIELD_W = 30
SHIELD_H = 28


def make_shield_mask():
    """Create a heater-style shield mask."""
    mask = [[False] * SHIELD_W for _ in range(SHIELD_H)]
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            cx = SHIELD_W / 2
            # Top portion: straight sides
            if y < 18:
                half_w = 13 - (y * 0.05 if y < 4 else 0)
                # Gentle taper at top
                if y < 4:
                    half_w = 11 + y * 0.5
                elif y < 6:
                    half_w = 13
                else:
                    half_w = 13
                if abs(x - cx) < half_w:
                    mask[y][x] = True
            else:
                # Bottom: pointed/rounded
                # Width narrows as we go down
                t = (y - 18) / (SHIELD_H - 18)  # 0..1
                half_w = 13 * (1 - t ** 1.5)
                if abs(x - cx) < half_w:
                    mask[y][x] = True
    return mask


# ─── Shield Divisions ─────────────────────────────────────────────────

def division_per_pale(field1, field2, mask):
    """Split vertically (left/right)."""
    result = [[None] * SHIELD_W for _ in range(SHIELD_H)]
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                result[y][x] = field1 if x < SHIELD_W // 2 else field2
    return result


def division_per_fess(field1, field2, mask):
    """Split horizontally (top/bottom)."""
    result = [[None] * SHIELD_W for _ in range(SHIELD_H)]
    mid = SHIELD_H // 2
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                result[y][x] = field1 if y < mid else field2
    return result


def division_per_bend(field1, field2, mask):
    """Diagonal split (top-left to bottom-right)."""
    result = [[None] * SHIELD_W for _ in range(SHIELD_H)]
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                result[y][x] = field1 if x > y * SHIELD_W / SHIELD_H else field2
    return result


def division_per_bend_sinister(field1, field2, mask):
    """Diagonal split (top-right to bottom-left)."""
    result = [[None] * SHIELD_W for _ in range(SHIELD_H)]
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                result[y][x] = field1 if x < SHIELD_W - y * SHIELD_W / SHIELD_H else field2
    return result


def division_per_saltire(field1, field2, mask):
    """X-shaped division."""
    result = [[None] * SHIELD_W for _ in range(SHIELD_H)]
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                on_d1 = abs(x - y * SHIELD_W / SHIELD_H) < 3
                on_d2 = abs(x - (SHIELD_W - y * SHIELD_W / SHIELD_H)) < 3
                result[y][x] = field2 if (on_d1 or on_d2) else field1
    return result


def division_quarterly(field1, field2, mask):
    """Quartered field."""
    result = [[None] * SHIELD_W for _ in range(SHIELD_H)]
    mid_x = SHIELD_W // 2
    mid_y = SHIELD_H // 2
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                top_left = y < mid_y and x < mid_x
                bot_right = y >= mid_y and x >= mid_x
                result[y][x] = field1 if (top_left or bot_right) else field2
    return result


def division_per_chevron(field1, field2, mask):
    """Chevron division."""
    result = [[None] * SHIELD_W for _ in range(SHIELD_H)]
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                cx = SHIELD_W / 2
                # Chevron line at y=SHIELD_H*0.6
                cy = SHIELD_H * 0.55
                # Point of chevron
                if y < cy:
                    result[y][x] = field1
                else:
                    # Two lines going from center-point outward
                    dx = abs(x - cx)
                    dy = y - cy
                    if dx < dy * 0.9 + 1:
                        result[y][x] = field1
                    else:
                        result[y][x] = field2
    return result


def division_gyronny(field1, field2, mask):
    """Gyronny (8-segment) division."""
    result = [[None] * SHIELD_W for _ in range(SHIELD_H)]
    cx = SHIELD_W / 2
    cy = SHIELD_H / 2
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                angle = math.atan2(y - cy, x - cx)
                segment = int((angle + math.pi) / (math.pi / 4)) % 8
                result[y][x] = field1 if segment % 2 == 0 else field2
    return result


DIVISIONS = {
    "Per Pale":           division_per_pale,
    "Per Fess":           division_per_fess,
    "Per Bend":           division_per_bend,
    "Per Bend Sinister":  division_per_bend_sinister,
    "Per Saltire":        division_per_saltire,
    "Quarterly":          division_quarterly,
    "Per Chevron":         division_per_chevron,
    "Gyronny":             division_gyronny,
}


# ─── Charges (symbols placed on the shield) ───────────────────────────

def _in_ellipse(x, y, cx, cy, rx, ry):
    """Check if point is inside an ellipse."""
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


def charge_cross(field, charge_tincture, mask):
    """Draw a cross charge."""
    result = [row[:] for row in field]
    cx, cy = SHIELD_W / 2, SHIELD_H / 2
    arm_w = 3
    arm_h = 10
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                in_vert = abs(x - cx) < arm_w and abs(y - cy) < arm_h
                in_horiz = abs(y - cy) < arm_w and abs(x - cx) < arm_h * 1.3
                if in_vert or in_horiz:
                    result[y][x] = charge_tincture
    return result


def charge_saltire(field, charge_tincture, mask):
    """Draw a saltire (X-shaped cross)."""
    result = [row[:] for row in field]
    cx, cy = SHIELD_W / 2, SHIELD_H / 2
    arm_w = 3
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                d1 = abs((x - cx) / (SHIELD_W / 2) - (y - cy) / (SHIELD_H / 2))
                d2 = abs((x - cx) / (SHIELD_W / 2) + (y - cy) / (SHIELD_H / 2))
                if d1 < 0.25 or d2 < 0.25:
                    result[y][x] = charge_tincture
    return result


def charge_roundel(field, charge_tincture, mask):
    """Draw a roundel (circle)."""
    result = [row[:] for row in field]
    cx, cy = SHIELD_W / 2, SHIELD_H * 0.45
    rx, ry = 8, 8
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x] and _in_ellipse(x, y, cx, cy, rx, ry):
                result[y][x] = charge_tincture
    return result


def charge_lozenge(field, charge_tincture, mask):
    """Draw a lozenge (diamond shape)."""
    result = [row[:] for row in field]
    cx, cy = SHIELD_W / 2, SHIELD_H * 0.45
    size = 10
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                dx = abs(x - cx) / (size * 1.2)
                dy = abs(y - cy) / size
                if dx + dy <= 1:
                    result[y][x] = charge_tincture
    return result


def charge_escallop(field, charge_tincture, mask):
    """Draw a scallop shell (simplified)."""
    result = [row[:] for row in field]
    cx, cy = SHIELD_W / 2, SHIELD_H * 0.42
    # Main dome
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                if _in_ellipse(x, y, cx, cy, 9, 7):
                    # Cut out bottom half roughly
                    if y > cy + 2:
                        # Keep base
                        if y < cy + 5 and abs(x - cx) < 7:
                            result[y][x] = charge_tincture
                    else:
                        result[y][x] = charge_tincture
                # Stem/base
                if abs(x - cx) < 2 and cy + 2 < y < cy + 8:
                    result[y][x] = charge_tincture
    return result


def charge_star(field, charge_tincture, mask):
    """Draw a mullet (5-pointed star)."""
    result = [row[:] for row in field]
    cx, cy = SHIELD_W / 2, SHIELD_H * 0.43
    outer_r = 9
    inner_r = 4
    points = 5
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                dx = x - cx
                dy = y - cy
                dist = math.sqrt(dx * dx + dy * dy)
                angle = math.atan2(dy, dx)
                # Star radius at this angle
                a = ((angle % (2 * math.pi / points)) - math.pi / points)
                star_r = inner_r + (outer_r - inner_r) * max(0, 1 - abs(a) / (math.pi / points) * 2)
                # Smoother star
                star_r_smooth = outer_r * (inner_r / outer_r) ** (2 * abs(a) / (math.pi / points))
                if dist < star_r_smooth + 1:
                    result[y][x] = charge_tincture
    return result


def charge_fleur_de_lis(field, charge_tincture, mask):
    """Draw a simplified fleur-de-lis."""
    result = [row[:] for row in field]
    cx, cy = SHIELD_W / 2, SHIELD_H * 0.43
    # Center petal
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                dx = abs(x - cx)
                dy = y - cy
                # Center petal (tall narrow)
                if dy < 0 and dy > -10 and dx < 2.5 + max(0, (-dy - 5)) * 0.3:
                    result[y][x] = charge_tincture
                # Base
                if 0 <= dy < 3 and dx < 7:
                    result[y][x] = charge_tincture
                # Side petals
                if 0 < dy < 6:
                    # Left petal
                    if -9 < dx < -2 and abs(dy - 3) < 3:
                        if math.sqrt((x - cx + 5) ** 2 + (y - cy - 3) ** 2) < 3:
                            result[y][x] = charge_tincture
                    # Right petal
                    if 2 < dx < 9 and abs(dy - 3) < 3:
                        if math.sqrt((x - cx - 5) ** 2 + (y - cy - 3) ** 2) < 3:
                            result[y][x] = charge_tincture
                # Stem
                if 3 <= dy < 6 and dx < 1.5:
                    result[y][x] = charge_tincture
    return result


def charge_crescent(field, charge_tincture, mask):
    """Draw a crescent moon."""
    result = [row[:] for row in field]
    cx, cy = SHIELD_W / 2, SHIELD_H * 0.43
    rx, ry = 8, 8
    # Outer circle
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                in_outer = _in_ellipse(x, y, cx, cy, rx, ry)
                in_inner = _in_ellipse(x, y, cx + 4, cy, rx * 0.8, ry * 0.8)
                if in_outer and not in_inner:
                    result[y][x] = charge_tincture
    return result


def charge_bend(field, charge_tincture, mask):
    """Draw a bend (diagonal stripe)."""
    result = [row[:] for row in field]
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                # Diagonal from top-right to bottom-left
                pos = x / SHIELD_W + y / SHIELD_H
                if 0.35 < pos < 0.65:
                    result[y][x] = charge_tincture
    return result


def charge_chevron(field, charge_tincture, mask):
    """Draw a chevron."""
    result = [row[:] for row in field]
    cx, cy = SHIELD_W / 2, SHIELD_H * 0.55
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                dx = abs(x - cx)
                dy = y - cy
                # Two lines forming a V
                if abs(dx - max(0, -dy) * 0.9) < 2.5 and dy < 2:
                    result[y][x] = charge_tincture
    return result


def charge_pale(field, charge_tincture, mask):
    """Draw a pale (vertical stripe)."""
    result = [row[:] for row in field]
    cx = SHIELD_W / 2
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                if abs(x - cx) < 4:
                    result[y][x] = charge_tincture
    return result


def charge_fess(field, charge_tincture, mask):
    """Draw a fess (horizontal stripe)."""
    result = [row[:] for row in field]
    cy = SHIELD_H / 2
    for y in range(SHIELD_H):
        for x in range(SHIELD_W):
            if mask[y][x]:
                if abs(y - cy) < 3.5:
                    result[y][x] = charge_tincture
    return result


CHARGES = {
    "Cross":         charge_cross,
    "Saltire":       charge_saltire,
    "Roundel":       charge_roundel,
    "Lozenge":       charge_lozenge,
    "Star":          charge_star,
    "Crescent":      charge_crescent,
    "Fleur-de-lis":  charge_fleur_de_lis,
    "Escallop":      charge_escallop,
    "Bend":          charge_bend,
    "Chevron":       charge_chevron,
    "Pale":          charge_pale,
    "Fess":          charge_fess,
}

# ─── Ordinaries (large simple geometric shapes) ───────────────────────
# Some charges above are ordinaries — we just reuse them

ORDINARIES = ["Pale", "Fess", "Bend", "Chevron", "Cross", "Saltire"]

# ─── Blazon generation ────────────────────────────────────────────────

def violates_rule_of_tincture(field_tincture, charge_tincture):
    """Check if placing charge_tincture on field_tincture violates the rule of tincture."""
    f_class = TINCTURES[field_tincture]["class"]
    c_class = TINCTURES[charge_tincture]["class"]
    # Rule: colour should not be on colour, metal should not be on metal
    return f_class == c_class


def compliant_tincture(for_class):
    """Get a random tincture of the opposite class."""
    if for_class == "metal":
        return random.choice(COLOURS)
    else:
        return random.choice(METALS)


def generate_blazon():
    """Generate a random heraldic blazon and its visual components."""
    # Decide on complexity
    complexity = random.choices(["simple", "medium", "complex"], weights=[3, 5, 2])[0]

    # Pick a division
    if complexity == "simple" or (complexity == "medium" and random.random() < 0.4):
        division_name = None  # Solid field
    else:
        division_name = random.choice(list(DIVISIONS.keys()))

    # Pick tinctures
    if division_name:
        # Two field tinctures — must follow rule of tincture
        field1 = random.choice(ALL_TINCTURES)
        opposite_class = "colour" if TINCTURES[field1]["class"] == "metal" else "metal"
        field2 = random.choice([t for t in ALL_TINCTURES if TINCTURES[t]["class"] == opposite_class])
    else:
        field1 = random.choice(ALL_TINCTURES)
        field2 = None

    # Pick charge
    charge_name = random.choice(list(CHARGES.keys()))

    # Pick charge tincture (must contrast with field)
    if division_name:
        # Must contrast with both fields
        candidates = [t for t in ALL_TINCTURES
                      if not violates_rule_of_tincture(field1, t)
                      and not violates_rule_of_tincture(field2, t)]
        if candidates:
            charge_tincture = random.choice(candidates)
        else:
            # Fallback: just contrast with primary field
            charge_tincture = compliant_tincture(TINCTURES[field1]["class"])
    else:
        candidates = [t for t in ALL_TINCTURES
                      if not violates_rule_of_tincture(field1, t)]
        if candidates:
            charge_tincture = random.choice(candidates)
        else:
            charge_tincture = compliant_tincture(TINCTURES[field1]["class"])

    # Build blazon text
    blazon_parts = []
    if division_name:
        blazon_parts.append(f"{division_name} {field1} and {field2}")
    else:
        blazon_parts.append(field1)

    blazon_parts.append(f"charged with a {charge_name} {charge_tincture}")

    blazon = ", ".join(blazon_parts)

    return {
        "division": division_name,
        "field1": field1,
        "field2": field2,
        "charge": charge_name,
        "charge_tincture": charge_tincture,
        "blazon": blazon,
    }


def render_shield(spec, mask):
    """Render a shield from a blazon spec into a grid of tincture names."""
    # Start with division
    if spec["division"]:
        render_fn = DIVISIONS[spec["division"]]
        field = render_fn(spec["field1"], spec["field2"], mask)
    else:
        field = [[spec["field1"]] * SHIELD_W for _ in range(SHIELD_H)]

    # Apply charge
    charge_fn = CHARGES[spec["charge"]]
    field = charge_fn(field, spec["charge_tincture"], mask)

    return field


def field_to_ascii(field, mask):
    """Convert tincture grid to colored ASCII art."""
    lines = []
    # Shield border top
    lines.append("        " + TINCTURES["Sable"]["ansi"] + "▄" * (SHIELD_W) + RESET)

    for y in range(SHIELD_H):
        row = ""
        # Find leftmost and rightmost shield pixels
        left = right = None
        for x in range(SHIELD_W):
            if mask[y][x]:
                if left is None:
                    left = x
                right = x

        if left is None:
            continue

        # Left border
        border_left = TINCTURES["Sable"]["ansi"] + "█" + RESET

        line = "        " + border_left

        for x in range(left, right + 1):
            if mask[y][x]:
                tincture = field[y][x]
                if tincture and tincture in TINCTURES:
                    # Choose character based on tincture for texture
                    ch = "█"
                    line += TINCTURES[tincture]["ansi"] + ch + RESET
                else:
                    line += " "
            else:
                line += " "

        # Right border
        line += TINCTURES["Sable"]["ansi"] + "█" + RESET
        lines.append(line)

    # Shield border bottom
    lines.append("        " + TINCTURES["Sable"]["ansi"] + "▀" * (SHIELD_W) + RESET)

    return "\n".join(lines)


def render_banner(blazon, shield_ascii):
    """Render the complete display with banner and blazon."""
    # Decorative banner
    width = 46
    top = "╔" + "═" * (width) + "╗"
    title_line = "║" + BOLD + " COAT OF ARMS ".center(width) + RESET + "║"
    divider = "╟" + "─" * (width) + "╢"

    # Word-wrap blazon
    blazon_text = f'"{blazon["blazon"]}"'
    blazon_lines = []
    max_len = width - 4
    words = blazon_text.split()
    current = ""
    for w in words:
        if len(current) + len(w) + 1 > max_len:
            blazon_lines.append(current)
            current = w
        else:
            current = (current + " " + w).strip()
    if current:
        blazon_lines.append(current)

    blazon_display = []
    for line in blazon_lines:
        blazon_display.append("║ " + ITALIC + line.ljust(max_len) + RESET + " ║")

    bottom = "╚" + "═" * (width) + "╝"

    # Helmet/crest decoration
    crest = BOLD + TINCTURES["Argent"]["ansi"] + """
                                   ╱▔▔▔╲
                                  ╱  ╱╲   ╲
                                 ╱  ╱  ╲   ╲
                                ╱  ╱    ╲   ╲
                               ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔
                                   ║║║║
                                   ║║║║""" + RESET

    # Mantling
    mantling_color = blazon["field1"]
    mantling_color2 = blazon["field2"] if blazon["field2"] else random.choice([t for t in ALL_TINCTURES if t != mantling_color])
    mc1 = TINCTURES[mantling_color]["ansi"]
    mc2 = TINCTURES[mantling_color2]["ansi"]
    mantling = (
        mc1 + "  ╱╲    ╱╲    ╱╲    ╱╲    ╱╲    ╱╲" + RESET + "\n"
        + mc2 + " ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲" + RESET + "\n"
        + mc1 + "╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲" + RESET
    )

    # Motto
    mottos = [
        "In Hoc Signo Vinces",
        "Nemo Me Impune Lacessit",
        "Per Aspera Ad Astra",
        "Virtus Et Honor",
        "Fortis Cadere Cedere Non Potest",
        "Dum Spiro Spero",
        "Aquila Non Capit Muscas",
        "Audax Et Fidelis",
        "Semper Fidelis",
        "Fortiter Et Recte",
        "Carpe Diem",
        "Aut Viam Inveniam Aut Faciam",
    ]
    motto = random.choice(mottos)

    motto_line = BOLD + DIM + f"  « {motto} »".center(width) + RESET

    output = "\n".join([
        "",
        top,
        title_line,
        divider,
        "",
    ])

    for line in blazon_display:
        output += line + "\n"

    output += "\n" + divider + "\n\n"

    # Shield
    output += shield_ascii + "\n\n"

    # Mantling
    output += "     " + mantling + "\n\n"

    # Motto
    motto_banner = "╭" + "─" * (width) + "╮"
    motto_text = "│" + f" « {motto} » ".center(width) + "│"
    motto_bottom = "╰" + "─" * (width) + "╯"
    output += motto_banner + "\n" + motto_text + "\n" + motto_bottom + "\n"

    output += "\n" + bottom + "\n"

    return output


def generate_multiple(n, seed=None):
    """Generate n random coats of arms."""
    if seed is not None:
        random.seed(seed)

    mask = make_shield_mask()
    results = []

    for i in range(n):
        spec = generate_blazon()
        field = render_shield(spec, mask)
        ascii_art = field_to_ascii(field, mask)
        full = render_banner(spec, ascii_art)
        results.append((spec, full))

    return results


# ─── Historical Coats of Arms ────────────────────────────────────────
HISTORICAL = {
    "england": {
        "division": None,
        "field1": "Gules",
        "field2": None,
        "charge": "Cross",
        "charge_tincture": "Argent",
        "blazon": "Gules charged with a Cross Argent",
    },
    "france": {
        "division": None,
        "field1": "Azure",
        "field2": None,
        "charge": "Fleur-de-lis",
        "charge_tincture": "Or",
        "blazon": "Azure charged with a Fleur-de-lis Or",
    },
    "scotland": {
        "division": None,
        "field1": "Or",
        "field2": None,
        "charge": "Saltire",
        "charge_tincture": "Azure",
        "blazon": "Or charged with a Saltire Azure",
    },
    "switzerland": {
        "division": None,
        "field1": "Gules",
        "field2": None,
        "charge": "Cross",
        "charge_tincture": "Argent",
        "blazon": "Gules charged with a Cross Argent",
    },
}

HISTORICAL_NAMES = {
    "england": "Kingdom of England",
    "france": "Kingdom of France",
    "switzerland": "Swiss Confederacy",
    "scotland": "Kingdom of Scotland",
}


def main():
    parser = argparse.ArgumentParser(
        description="Procedural Heraldry Generator — Create random medieval coats of arms"
    )
    parser.add_argument("-n", "--number", type=int, default=1,
                        help="Number of coats of arms to generate (default: 1)")
    parser.add_argument("-s", "--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--historical", type=str, default=None,
                        choices=list(HISTORICAL.keys()),
                        help="Display a specific historical coat of arms")
    parser.add_argument("--list-historical", action="store_true",
                        help="List available historical coats of arms")
    parser.add_argument("--blazon-only", action="store_true",
                        help="Only output the blazon text, no art")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output")
    parser.add_argument("--plain", action="store_true",
                        help="Use plain ASCII characters instead of Unicode")

    args = parser.parse_args()

    if args.no_color:
        for key in TINCTURES:
            TINCTURES[key]["ansi"] = ""
            TINCTURES[key]["bg"] = ""
        global RESET, BOLD, DIM, ITALIC
        RESET = ""
        BOLD = ""
        DIM = ""
        ITALIC = ""

    mask = make_shield_mask()

    if args.list_historical:
        print("Available historical coats of arms:")
        for key, name in HISTORICAL_NAMES.items():
            blazon = HISTORICAL[key]["blazon"]
            print(f"  {key:15s} — {name}: {blazon}")
        return

    if args.historical:
        spec = HISTORICAL[args.historical]
        name = HISTORICAL_NAMES[args.historical]
        if args.blazon_only:
            print(f"{name}: {spec['blazon']}")
            return
        field = render_shield(spec, mask)
        ascii_art = field_to_ascii(field, mask)
        full = render_banner(spec, ascii_art)
        print(f"\n  {BOLD}Historical:{RESET} {name}\n")
        print(full)
        return

    if args.seed is not None:
        random.seed(args.seed)

    for i in range(args.number):
        spec = generate_blazon()
        if args.blazon_only:
            print(f"#{i+1}: {spec['blazon']}")
            continue

        field = render_shield(spec, mask)
        ascii_art = field_to_ascii(field, mask)
        full = render_banner(spec, ascii_art)

        if args.number > 1:
            print(f"\n{'═' * 50}")
            print(f"  Coat of Arms #{i+1}")
            print(f"{'═' * 50}")

        print(full)


if __name__ == "__main__":
    main()