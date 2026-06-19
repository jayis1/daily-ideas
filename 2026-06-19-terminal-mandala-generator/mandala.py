#!/usr/bin/env python3
"""
Terminal Mandala Generator
===========================
Generates beautiful radial mandala patterns in the terminal using
Unicode block characters and ANSI 256-color palette.
"""

import random
import math
import sys
import argparse


# ANSI 256-color palette indices that look great for mandalas
WARM_PALETTE = [1, 9, 10, 11, 12, 13, 14, 15, 52, 53, 88, 89, 124, 125, 160, 161, 196, 197, 202, 203, 208, 209, 214, 215, 220, 221, 226, 227, 228, 229, 230, 231]
COOL_PALETTE = [4, 5, 6, 7, 12, 13, 14, 15, 17, 18, 19, 20, 21, 26, 27, 32, 33, 38, 39, 44, 45, 49, 50, 51, 56, 57, 62, 63, 68, 69, 74, 75, 80, 81, 86, 87, 99, 105, 111, 117, 123, 159]
EARTH_PALETTE = [1, 2, 3, 22, 23, 28, 29, 34, 35, 40, 41, 46, 47, 58, 59, 64, 65, 70, 71, 76, 77, 82, 83, 94, 95, 100, 101, 106, 107, 130, 131, 136, 137, 142, 143, 166, 172, 178, 184]
NEON_PALETTE = [2, 10, 11, 14, 15, 46, 47, 50, 51, 82, 83, 86, 87, 118, 119, 154, 155, 190, 191, 196, 197, 202, 208, 214, 220, 226, 231]
FIRE_PALETTE = [1, 9, 52, 88, 124, 160, 196, 202, 208, 214, 220, 226, 227, 228, 229, 230, 231, 15, 14, 11]

PALETTES = {
    'warm': WARM_PALETTE,
    'cool': COOL_PALETTE,
    'earth': EARTH_PALETTE,
    'neon': NEON_PALETTE,
    'fire': FIRE_PALETTE,
}

# Characters that look good in mandala patterns
BLOCK_CHARS = ['█', '▓', '▒', '░', '▄', '▀', '▐', '▌', '◆', '◇', '○', '●', '◎', '✦', '✧', '⬡', '⬢', '△', '▽', '⬟', '⬠']
DELICATE_CHARS = ['·', '•', '∘', '○', '◇', '✧', '✦', '⋆', '⊹', '°', '˙', '˚', '˜', '♦', '♣', '♠', '♥']
DOT_CHARS = ['·', '•', '∘', '°', '⋆', '✧']
RING_CHARS = ['○', '◎', '◑', '◒', '◐', '◔', '◕', '⬭', '⬬']

# Mandala element types
CIRCLE = 'circle'
RING = 'ring'
PETALS = 'petals'
DOTS = 'dots'
STAR = 'star'
WHEEL = 'wheel'
SPIRAL_ARMS = 'spiral'
DIAMONDS = 'diamonds'
FRACTAL_RING = 'fractal_ring'
WAVE_RING = 'wave_ring'

ELEMENT_TYPES = [CIRCLE, RING, PETALS, DOTS, STAR, WHEEL, SPIRAL_ARMS, DIAMONDS, FRACTAL_RING, WAVE_RING]


def ansi_fg(color_idx):
    """Return ANSI 256-color foreground escape."""
    return f'\033[38;5;{color_idx}m'


def ansi_bg(color_idx):
    """Return ANSI 256-color background escape."""
    return f'\033[48;5;{color_idx}m'


RESET = '\033[0m'
BG_BLACK = '\033[48;5;16m'


def pick_palette(name=None):
    """Pick a color palette by name or randomly."""
    if name and name in PALETTES:
        return PALETTES[name]
    return random.choice(list(PALETTES.values()))


def make_canvas(width, height):
    """Create a 2D canvas of spaces."""
    return [[' ' for _ in range(width)] for _ in range(height)]


def make_color_canvas(width, height):
    """Create a 2D canvas for color indices (None = no color)."""
    return [[None for _ in range(width)] for _ in range(height)]


def render_canvas(canvas, color_canvas, bg_color=16):
    """Render canvas to string with ANSI colors."""
    lines = []
    bg_escape = ansi_bg(bg_color)
    prev_color = None
    for y in range(len(canvas)):
        line = bg_escape
        for x in range(len(canvas[y])):
            ch = canvas[y][x]
            color = color_canvas[y][x]
            if ch == ' ' and color is None:
                line += ' '
                prev_color = None
            elif color is not None:
                if color != prev_color:
                    line += ansi_fg(color)
                    prev_color = color
                line += ch
            else:
                line += ch
        line += RESET
        lines.append(line)
    return '\n'.join(lines)


class MandalaGenerator:
    """Generates mandala patterns on a canvas with radial symmetry."""

    def __init__(self, width=80, height=41, seed=None, palette_name=None):
        self.width = width
        self.height = height
        self.cx = width // 2
        self.cy = height // 2
        # Adjust for character aspect ratio (chars are ~2x tall as wide)
        self.aspect = 0.5
        if seed is not None:
            random.seed(seed)
        self.palette = pick_palette(palette_name)
        self.canvas = make_canvas(width, height)
        self.color_canvas = make_color_canvas(width, height)
        self.elements = []

    def _max_radius(self):
        """Maximum radius that fits on the canvas."""
        rx = self.cx - 1
        ry = self.cy - 1
        return min(rx, int(ry / self.aspect))

    def _plot(self, x, y, ch, color):
        """Plot a character at canvas coordinates."""
        ix, iy = int(round(x)), int(round(y))
        if 0 <= ix < self.width and 0 <= iy < self.height:
            self.canvas[iy][ix] = ch
            self.color_canvas[iy][ix] = color

    def _plot_polar(self, r, theta, ch, color):
        """Plot at polar coordinates from center, adjusted for aspect ratio."""
        x = self.cx + r * math.cos(theta)
        y = self.cy + r * math.sin(theta) * (1.0 / self.aspect)
        self._plot(x, y, ch, color)

    def _radial_draw(self, r, theta, ch, color, symmetry=None):
        """Draw at one angle and all rotational copies."""
        if symmetry is None:
            symmetry = random.choice([4, 6, 8, 10, 12, 16])
        for i in range(symmetry):
            angle = theta + (2 * math.pi * i) / symmetry
            self._plot_polar(r, angle, ch, color)

    def _pick_color(self):
        """Pick a random color from the palette."""
        return random.choice(self.palette)

    def _pick_char(self, char_set=None):
        """Pick a random character."""
        if char_set is None:
            char_set = BLOCK_CHARS + DELICATE_CHARS
        return random.choice(char_set)

    def add_center_dot(self):
        """Add a center dot to the mandala."""
        color = self._pick_color()
        self._plot(self.cx, self.cy, '◉', color)
        self.elements.append(('center_dot', 0))

    def add_circle(self, radius=None, ch=None, color=None, symmetry=None, filled=False):
        """Add a circle ring to the mandala."""
        max_r = self._max_radius()
        if radius is None:
            radius = random.randint(max_r // 4, max_r - 1)
        if ch is None:
            ch = random.choice(RING_CHARS + ['·', '•', '∘', '◦', '─'])
        if color is None:
            color = self._pick_color()
        if symmetry is None:
            symmetry = random.choice([4, 6, 8, 10, 12, 16, 20, 24, 32, 48])

        steps = max(32, int(2 * math.pi * radius / self.aspect))
        for i in range(steps):
            theta = 2 * math.pi * i / steps
            if filled:
                self._plot_polar(radius, theta, ch, color)
            else:
                if i % max(1, steps // symmetry) < max(1, steps // symmetry):
                    self._plot_polar(radius, theta, ch, color)
                    # Also draw mirror
                    self._plot_polar(radius, -theta, ch, color)

        self.elements.append(('circle', radius))

    def add_dotted_circle(self, radius=None, color=None, dots=None):
        """Add a dotted circle to the mandala."""
        max_r = self._max_radius()
        if radius is None:
            radius = random.randint(max_r // 4, max_r - 1)
        if color is None:
            color = self._pick_color()
        if dots is None:
            dots = random.choice([8, 12, 16, 20, 24, 32])

        ch = random.choice(DOT_CHARS + ['◆', '◇', '✦'])
        for i in range(dots):
            theta = 2 * math.pi * i / dots
            self._plot_polar(radius, theta, ch, color)

        self.elements.append(('dotted_circle', radius))

    def add_petals(self, radius=None, count=None, color=None, ch=None):
        """Add petal shapes radiating from center."""
        max_r = self._max_radius()
        if radius is None:
            radius = random.randint(max_r // 4, max_r - 2)
        if count is None:
            count = random.choice([4, 5, 6, 8, 10, 12, 16])
        if color is None:
            color = self._pick_color()
        if ch is None:
            ch = random.choice(['◆', '◇', '✦', '⬡', '⬢', '●', '◎', '♦'])

        inner_r = radius * random.uniform(0.2, 0.5)
        for i in range(count):
            base_theta = 2 * math.pi * i / count
            # Draw petal as series of points along a curve
            petal_len = random.randint(3, max(4, radius - int(inner_r)))
            for j in range(petal_len):
                t = j / petal_len
                r = inner_r + (radius - inner_r) * t
                # Slight curve to the petal
                spread = 0.15 * math.sin(t * math.pi)
                self._plot_polar(r, base_theta - spread, ch, color)
                self._plot_polar(r, base_theta + spread, ch, color)
                if t < 0.5:
                    self._plot_polar(r, base_theta, ch, color)

        self.elements.append(('petals', radius))

    def add_star(self, radius=None, points=None, color=None):
        """Add a star pattern."""
        max_r = self._max_radius()
        if radius is None:
            radius = random.randint(max_r // 4, max_r - 1)
        if points is None:
            points = random.choice([4, 5, 6, 8, 10, 12])
        if color is None:
            color = self._pick_color()

        ch = random.choice(['✦', '✧', '◆', '◇', '★', '☆'])
        inner_r = radius * random.uniform(0.3, 0.6)

        for i in range(points):
            theta_outer = 2 * math.pi * i / points
            theta_next = 2 * math.pi * (i + 1) / points
            theta_inner = (theta_outer + theta_next) / 2

            # Line from inner to outer
            steps = max(3, int(radius - inner_r))
            for s in range(steps):
                t = s / steps
                r = inner_r + (radius - inner_r) * t
                self._plot_polar(r, theta_outer * (1 - t) + theta_inner * t, ch, color)

            # Line from outer to next inner
            for s in range(steps):
                t = s / steps
                r = radius - (radius - inner_r) * t
                self._plot_polar(r, theta_outer * (1 - t) + theta_next * t, ch, color)

        self.elements.append(('star', radius))

    def add_spiral_arms(self, arms=None, radius=None, color=None, turns=None):
        """Add spiral arms emanating from center."""
        max_r = self._max_radius()
        if radius is None:
            radius = random.randint(max_r // 3, max_r - 1)
        if arms is None:
            arms = random.choice([3, 4, 5, 6, 8])
        if turns is None:
            turns = random.uniform(0.3, 1.0)
        if color is None:
            color = self._pick_color()

        ch = random.choice(['·', '•', '∘', '◆', '✦', '─'])

        for arm in range(arms):
            base_theta = 2 * math.pi * arm / arms
            steps = max(10, radius * 2)
            for s in range(steps):
                t = s / steps
                r = t * radius
                theta = base_theta + t * turns * 2 * math.pi
                self._plot_polar(r, theta, ch, color)

        self.elements.append(('spiral_arms', radius))

    def add_diamonds(self, radius=None, count=None, color=None):
        """Add diamond shapes in a ring."""
        max_r = self._max_radius()
        if radius is None:
            radius = random.randint(max_r // 4, max_r - 2)
        if count is None:
            count = random.choice([4, 6, 8, 10, 12])
        if color is None:
            color = self._pick_color()

        size = max(1, min(3, int(radius / count)))
        for i in range(count):
            theta = 2 * math.pi * i / count
            # Draw a small diamond at this position
            for dr in range(-size, size + 1):
                for dc in range(-size, size + 1):
                    if abs(dr) + abs(dc) <= size:
                        x = self.cx + radius * math.cos(theta) + dc
                        y = self.cy + radius * math.sin(theta) / self.aspect + dr
                        ch = '◆' if (abs(dr) + abs(dc)) == size else '◇'
                        self._plot(x, y, ch, color)

        self.elements.append(('diamonds', radius))

    def add_wave_ring(self, radius=None, color=None, waves=None):
        """Add a wavy ring pattern."""
        max_r = self._max_radius()
        if radius is None:
            radius = random.randint(max_r // 4, max_r - 2)
        if waves is None:
            waves = random.choice([4, 6, 8, 10, 12, 16])
        if color is None:
            color = self._pick_color()

        amplitude = random.uniform(1.0, 3.0)
        ch = random.choice(['~', '≈', '∿', '〰', '─', '━'])

        steps = max(48, radius * 3)
        for i in range(steps):
            theta = 2 * math.pi * i / steps
            r = radius + amplitude * math.sin(waves * theta)
            self._plot_polar(r, theta, ch, color)

        self.elements.append(('wave_ring', radius))

    def add_fractal_ring(self, radius=None, color=None, depth=None):
        """Add a fractal-style ring with sub-rings."""
        max_r = self._max_radius()
        if radius is None:
            radius = random.randint(max_r // 3, max_r - 2)
        if depth is None:
            depth = random.randint(2, 3)
        if color is None:
            color = self._pick_color()

        # Main ring
        self.add_dotted_circle(radius=radius, color=color,
                               dots=random.choice([6, 8, 10, 12]))

        # Sub-rings at each dot position (smaller)
        if depth > 1:
            sub_count = random.choice([4, 6, 8])
            sub_radius = max(2, int(radius * 0.2))
            for i in range(sub_count):
                theta = 2 * math.pi * i / sub_count
                sub_cx = self.cx + radius * math.cos(theta)
                sub_cy = self.cy + radius * math.sin(theta) / self.aspect
                # Draw small ring
                steps = max(8, sub_radius * 2)
                ch = random.choice(DOT_CHARS)
                for s in range(steps):
                    a = 2 * math.pi * s / steps
                    sx = sub_cx + sub_radius * math.cos(a)
                    sy = sub_cy + sub_radius * math.sin(a)
                    self._plot(sx, sy, ch, color)

        self.elements.append(('fractal_ring', radius))

    def add_wheel(self, radius=None, spokes=None, color=None, color2=None):
        """Add a wheel/spoke pattern."""
        max_r = self._max_radius()
        if radius is None:
            radius = random.randint(max_r // 4, max_r - 1)
        if spokes is None:
            spokes = random.choice([4, 6, 8, 10, 12, 16])
        if color is None:
            color = self._pick_color()
        if color2 is None:
            color2 = self._pick_color()

        ch = random.choice(['│', '─', '┃', '━', '|', '/', '\\'])

        for i in range(spokes):
            theta = 2 * math.pi * i / spokes
            steps = max(3, radius)
            for s in range(steps):
                t = s / steps
                r = t * radius
                spoke_ch = ch if s % 2 == 0 else '·'
                spoke_color = color if i % 2 == 0 else color2
                self._plot_polar(r, theta, spoke_ch, spoke_color)

        self.elements.append(('wheel', radius))

    def add_filled_ring(self, radius_outer=None, radius_inner=None, color=None, ch=None, density=0.4):
        """Add a partially filled ring between two radii."""
        max_r = self._max_radius()
        if radius_outer is None:
            radius_outer = random.randint(max_r // 3, max_r - 1)
        if radius_inner is None:
            radius_inner = random.randint(2, max(3, radius_outer - 3))
        if color is None:
            color = self._pick_color()
        if ch is None:
            ch = random.choice(['░', '▒', '▓', '·', '•'])

        for y in range(self.height):
            for x in range(self.width):
                dx = x - self.cx
                dy = (y - self.cy) * (1.0 / self.aspect)
                r = math.sqrt(dx * dx + dy * dy)
                if radius_inner <= r <= radius_outer:
                    if random.random() < density:
                        self.canvas[y][x] = ch
                        self.color_canvas[y][x] = color

        self.elements.append(('filled_ring', radius_outer))

    def add_ornamental_border(self, color=None):
        """Add an ornamental border around the mandala."""
        if color is None:
            color = self._pick_color()
        max_r = self._max_radius() - 1
        ch = random.choice(['✦', '◆', '◇', '●', '⬡', '❖', '✧'])

        # Outer circle
        self.add_dotted_circle(radius=max_r, color=color,
                               dots=random.choice([16, 20, 24, 32, 48]))
        # Second ring
        self.add_dotted_circle(radius=max_r - 2, color=color,
                               dots=random.choice([12, 16, 20, 24]))

        self.elements.append(('border', max_r))

    def generate_random(self, complexity=None):
        """Generate a random mandala with multiple layers."""
        if complexity is None:
            complexity = random.randint(3, 8)

        # Always start with center
        self.add_center_dot()

        max_r = self._max_radius()
        layers = []

        # Generate layer radii
        num_layers = complexity
        for i in range(num_layers):
            r = int(max_r * (i + 1) / (num_layers + 1))
            r = max(3, r)
            layers.append(r)

        # Shuffle element types
        element_pool = list(ELEMENT_TYPES)
        random.shuffle(element_pool)

        for i, radius in enumerate(layers):
            # Pick element type
            if i < len(element_pool):
                etype = element_pool[i]
            else:
                etype = random.choice(ELEMENT_TYPES)

            try:
                if etype == CIRCLE:
                    self.add_circle(radius=radius)
                elif etype == RING:
                    self.add_dotted_circle(radius=radius)
                elif etype == PETALS:
                    self.add_petals(radius=radius)
                elif etype == DOTS:
                    self.add_dotted_circle(radius=radius,
                                           dots=random.choice([8, 12, 16, 20, 24]))
                elif etype == STAR:
                    self.add_star(radius=radius)
                elif etype == WHEEL:
                    self.add_wheel(radius=radius)
                elif etype == SPIRAL_ARMS:
                    self.add_spiral_arms(radius=radius)
                elif etype == DIAMONDS:
                    self.add_diamonds(radius=radius)
                elif etype == FRACTAL_RING:
                    self.add_fractal_ring(radius=radius)
                elif etype == WAVE_RING:
                    self.add_wave_ring(radius=radius)
            except Exception:
                # Skip layers that fail
                pass

        # Add border
        if random.random() < 0.7:
            self.add_ornamental_border()

    def render(self, bg_color=16):
        """Render the mandala to a string."""
        return render_canvas(self.canvas, self.color_canvas, bg_color=bg_color)

    def render_no_color(self):
        """Render without ANSI colors."""
        lines = []
        for y in range(self.height):
            lines.append(''.join(self.canvas[y]))
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Terminal Mandala Generator - Create beautiful radial patterns in your terminal'
    )
    parser.add_argument('-w', '--width', type=int, default=None,
                        help='Canvas width (default: auto-detect terminal width)')
    parser.add_argument('-H', '--height', type=int, default=None,
                        help='Canvas height (default: auto-detect terminal height)')
    parser.add_argument('-s', '--seed', type=int, default=None,
                        help='Random seed for reproducible mandalas')
    parser.add_argument('-p', '--palette', choices=list(PALETTES.keys()), default=None,
                        help='Color palette: warm, cool, earth, neon, fire')
    parser.add_argument('-c', '--complexity', type=int, default=None,
                        help='Number of layers (3-8, default: random)')
    parser.add_argument('-b', '--bg', type=int, default=16,
                        help='Background color index (0-255, default: 16/black)')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable ANSI colors')
    parser.add_argument('--save', type=str, default=None,
                        help='Save output to file instead of printing')
    parser.add_argument('--batch', type=int, default=None,
                        help='Generate N different mandalas')
    args = parser.parse_args()

    # Determine canvas size
    width = args.width or 80
    height = args.height or 41

    if args.batch:
        for i in range(args.batch):
            seed = args.seed + i if args.seed is not None else random.randint(0, 999999)
            gen = MandalaGenerator(width=width, height=height, seed=seed,
                                   palette_name=args.palette)
            gen.generate_random(complexity=args.complexity)

            output = gen.render_no_color() if args.no_color else gen.render(bg_color=args.bg)

            if args.save:
                import os
                base, ext = os.path.splitext(args.save)
                filename = f"{base}_{i}{ext}" if ext else f"{base}_{i}.txt"
                with open(filename, 'w') as f:
                    f.write(output)
                print(f"Saved mandala {i+1} to {filename}")
            else:
                print(f"\n  === Mandala {i+1} (seed: {seed}) ===\n")
                print(output)
                print()
        return

    gen = MandalaGenerator(width=width, height=height, seed=args.seed,
                           palette_name=args.palette)
    gen.generate_random(complexity=args.complexity)

    if args.no_color:
        output = gen.render_no_color()
    else:
        output = gen.render(bg_color=args.bg)

    if args.save:
        with open(args.save, 'w') as f:
            f.write(output)
        print(f"Mandala saved to {args.save}")
    else:
        print()
        print(output)
        print()
        seed_used = args.seed if args.seed is not None else 'random'
        print(f"  (seed: {seed_used}, palette: {args.palette or 'random'})")
        print()


if __name__ == '__main__':
    main()