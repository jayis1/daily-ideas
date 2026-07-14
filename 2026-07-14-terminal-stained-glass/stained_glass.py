#!/usr/bin/env python3
"""
Terminal Stained Glass Generator
Procedurally generates beautiful stained glass window patterns in the terminal
using colored Unicode characters with various architectural styles.
"""

__version__ = "1.1.0"

import random
import sys
import math
import argparse
from collections import deque

# ANSI color codes for rich terminal output
COLORS = {
    'deep_red':     '\033[38;5;124m',
    'crimson':      '\033[38;5;196m',
    'rose':         '\033[38;5;203m',
    'orange':       '\033[38;5;208m',
    'amber':        '\033[38;5;214m',
    'gold':         '\033[38;5;220m',
    'yellow':       '\033[38;5;226m',
    'lime':         '\033[38;5;118m',
    'green':        '\033[38;5;46m',
    'forest':       '\033[38;5;28m',
    'dark_green':   '\033[38;5;22m',
    'teal':         '\033[38;5;37m',
    'cyan':         '\033[38;5;51m',
    'sky_blue':     '\033[38;5;117m',
    'blue':         '\033[38;5;33m',
    'royal_blue':   '\033[38;5;20m',
    'navy':         '\033[38;5;17m',
    'indigo':       '\033[38;5;55m',
    'violet':       '\033[38;5;93m',
    'purple':       '\033[38;5;127m',
    'magenta':      '\033[38;5;199m',
    'pink':         '\033[38;5;213m',
    'white':        '\033[38;5;255m',
    'ivory':        '\033[38;5;230m',
    'gray':         '\033[38;5;244m',
    'dark_gray':    '\033[38;5;238m',
    'lead':         '\033[38;5;240m',
    'brown':        '\033[38;5;130m',
    'dark_brown':   '\033[38;5;88m',
}

BG_COLORS = {
    'black':      '\033[48;5;0m',
    'deep_blue':  '\033[48;5;17m',
    'dark_purple': '\033[48;5;55m',
}

RESET = '\033[0m'
BOLD = '\033[1m'

# Glass piece characters
GLASS_CHARS = {
    'full':    '█',
    'light':   '▓',
    'medium':  '▒',
    'sparse':  '░',
    'diamond': '◆',
    'circle':  '●',
    'star':    '★',
    'cross':   '✦',
    'flower':  '✿',
    'sun':     '✺',
    'heart':   '♥',
    'gem':     '◈',
    'dot':     '•',
    'wave':    '∿',
}

LEAD_CHARS = {
    'solid':  '│',
    'h_line': '─',
    'corner': '┼',
    'cross':  '╬',
    'tee_r':  '├',
    'tee_l':  '┤',
    'tee_d':  '┬',
    'tee_u':  '┴',
}

# Architectural style palettes
STYLES = {
    'gothic': {
        'name': 'Gothic Cathedral',
        'colors': ['deep_red', 'royal_blue', 'gold', 'forest', 'violet', 'crimson', 'ivory'],
        'accent': ['crimson', 'gold'],
        'bg': 'deep_blue',
        'shape': 'pointed_arch',
        'lead_color': 'dark_gray',
        'description': 'Tall pointed arches with deep jewel tones',
    },
    'romanesque': {
        'name': 'Romanesque',
        'colors': ['blue', 'teal', 'amber', 'orange', 'rose', 'green'],
        'accent': ['gold', 'orange'],
        'bg': 'dark_purple',
        'shape': 'round_arch',
        'lead_color': 'brown',
        'description': 'Rounded arches with warm Mediterranean tones',
    },
    'art_nouveau': {
        'name': 'Art Nouveau',
        'colors': ['lime', 'teal', 'violet', 'pink', 'gold', 'sky_blue', 'magenta'],
        'accent': ['gold', 'lime'],
        'bg': 'black',
        'shape': 'organic',
        'lead_color': 'dark_green',
        'description': 'Flowing organic shapes with pastel accents',
    },
    'art_deco': {
        'name': 'Art Deco',
        'colors': ['gold', 'navy', 'crimson', 'ivory', 'teal', 'amber'],
        'accent': ['gold', 'ivory'],
        'bg': 'black',
        'shape': 'geometric',
        'lead_color': 'dark_gray',
        'description': 'Bold geometric patterns with gold and jewel tones',
    },
    'byzantine': {
        'name': 'Byzantine',
        'colors': ['gold', 'royal_blue', 'crimson', 'purple', 'teal', 'ivory', 'deep_red'],
        'accent': ['gold', 'ivory'],
        'bg': 'deep_blue',
        'shape': 'mosaic',
        'lead_color': 'brown',
        'description': 'Rich gold and jewel tones in mosaic patterns',
    },
    'modern': {
        'name': 'Modern Minimalist',
        'colors': ['sky_blue', 'lime', 'yellow', 'pink', 'white', 'cyan'],
        'accent': ['white', 'yellow'],
        'bg': 'black',
        'shape': 'minimal',
        'lead_color': 'gray',
        'description': 'Clean lines with bright primary colors',
    },
}


class StainedGlassGenerator:
    def __init__(self, width=70, height=35, style='gothic', seed=None):
        self.width = width
        self.height = height
        self.style_name = style
        if style not in STYLES:
            valid = ', '.join(sorted(STYLES.keys()))
            raise ValueError(f"Unknown style '{style}'. Valid styles: {valid}")
        self.style = STYLES[style]
        self.grid = {}  # (x, y) -> {'color': str, 'char': str, 'is_lead': bool}
        # Fix: seed=0 was treated as falsy, generating random seed instead
        if seed is not None:
            self.seed = seed
        else:
            self.seed = random.randint(1, 999999)
        random.seed(self.seed)
        
    def _color(self, name):
        return COLORS.get(name, '')
    
    def _bg(self, name):
        return BG_COLORS.get(name, '')
    
    def _in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height
    
    def _set(self, x, y, color_name, char, is_lead=False):
        if self._in_bounds(x, y):
            self.grid[(x, y)] = {
                'color': color_name,
                'char': char,
                'is_lead': is_lead,
            }
    
    def _get(self, x, y):
        return self.grid.get((x, y), None)
    
    def _fill_bg(self):
        """Fill the entire grid with background."""
        bg = self.style['bg']
        for y in range(self.height):
            for x in range(self.width):
                self._set(x, y, bg, ' ')
    
    def _draw_arch_gothic(self, cx, top_y, width, height):
        """Draw a pointed gothic arch outline."""
        lead = self.style['lead_color']
        hw = width // 2
        
        # Left side
        for dy in range(height):
            y = top_y + dy
            t = dy / max(height - 1, 1)
            # Curve inward as we go up
            x_off = int(hw * (1 - t ** 0.5))
            self._set(cx - x_off, y, lead, '│', is_lead=True)
            self._set(cx + x_off, y, lead, '│', is_lead=True)
        
        # Point at top
        for i in range(hw // 2):
            y = top_y - i
            x_off = max(0, hw // 2 - i)
            self._set(cx - x_off, y, lead, '/', is_lead=True)
            self._set(cx + x_off, y, lead, '\\', is_lead=True)
        
        # Apex
        self._set(cx, top_y - hw // 2, lead, '^', is_lead=True)
        
        # Bottom horizontal
        for x in range(cx - hw, cx + hw + 1):
            self._set(x, top_y + height - 1, lead, '─', is_lead=True)
    
    def _draw_arch_round(self, cx, top_y, width, height):
        """Draw a round Romanesque arch outline."""
        lead = self.style['lead_color']
        hw = width // 2
        
        # Sides
        for dy in range(height):
            y = top_y + dy
            self._set(cx - hw, y, lead, '│', is_lead=True)
            self._set(cx + hw, y, lead, '│', is_lead=True)
        
        # Rounded top
        for i in range(hw + 1):
            angle = math.pi * i / hw
            x = cx + int(hw * math.cos(angle))
            y = top_y - int(hw * 0.6 * math.sin(angle))
            self._set(x, y, lead, '─', is_lead=True)
            if i > 0 and i < hw:
                self._set(x, y - 1, lead, '·', is_lead=True)
        
        # Bottom
        for x in range(cx - hw, cx + hw + 1):
            self._set(x, top_y + height - 1, lead, '─', is_lead=True)
    
    def _draw_frame(self):
        """Draw the window frame based on style."""
        lead = self.style['lead_color']
        shape = self.style['shape']
        
        if shape == 'pointed_arch':
            self._draw_arch_gothic(self.width // 2, 3, self.width - 4, self.height - 4)
        elif shape == 'round_arch':
            self._draw_arch_round(self.width // 2, 3, self.width - 4, self.height - 4)
        else:
            # Simple rectangular frame for other styles
            for x in range(2, self.width - 2):
                self._set(x, 2, lead, '─', is_lead=True)
                self._set(x, self.height - 3, lead, '─', is_lead=True)
            for y in range(2, self.height - 2):
                self._set(2, y, lead, '│', is_lead=True)
                self._set(self.width - 3, y, lead, '│', is_lead=True)
    
    def _flood_fill_regions(self):
        """Flood fill to find connected regions of empty space."""
        visited = set()
        regions = []
        
        for y in range(self.height):
            for x in range(self.width):
                if (x, y) not in visited:
                    cell = self._get(x, y)
                    if cell and cell['is_lead']:
                        visited.add((x, y))
                        continue
                    
                    # Flood fill
                    region = []
                    queue = deque([(x, y)])
                    while queue:
                        cx, cy = queue.popleft()
                        if (cx, cy) in visited:
                            continue
                        if not self._in_bounds(cx, cy):
                            continue
                        visited.add((cx, cy))
                        
                        cell = self._get(cx, cy)
                        if cell and cell['is_lead']:
                            continue
                        
                        region.append((cx, cy))
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            nx, ny = cx + dx, cy + dy
                            if (nx, ny) not in visited and self._in_bounds(nx, ny):
                                queue.append((nx, ny))
                    
                    if len(region) > 0:
                        regions.append(region)
        
        return regions
    
    def _draw_leaded_pattern_inside_frame(self):
        """Draw decorative lead lines inside the window."""
        lead = self.style['lead_color']
        shape = self.style['shape']
        cx = self.width // 2
        cy = self.height // 2
        
        if shape == 'pointed_arch':
            # Gothic: vertical center line and horizontal dividers
            for y in range(4, self.height - 4):
                self._set(cx, y, lead, '│', is_lead=True)
            
            # Horizontal bands
            for div_y in [self.height // 3, 2 * self.height // 3]:
                for x in range(4, self.width - 4):
                    cell = self._get(x, div_y)
                    if not (cell is not None and cell['is_lead']):
                        self._set(x, div_y, lead, '─', is_lead=True)
            
            # Cross intersections
            self._set(cx, self.height // 3, lead, '┼', is_lead=True)
            self._set(cx, 2 * self.height // 3, lead, '┼', is_lead=True)
            
            # Circular medallion in center
            r = min(self.width, self.height) // 6
            for angle_deg in range(360):
                angle = math.radians(angle_deg)
                for ri in range(r, r + 1):
                    px = int(cx + ri * math.cos(angle))
                    py = int(cy + ri * math.sin(angle) * 0.6)
                    if self._in_bounds(px, py):
                        self._set(px, py, lead, '·', is_lead=True)
            
            # Diamond in top section
            dr = min(self.width // 8, 6)
            top_cy = (4 + self.height // 3) // 2
            for i in range(dr):
                self._set(cx + i, top_cy - i, lead, '/', is_lead=True)
                self._set(cx - i, top_cy - i, lead, '\\', is_lead=True)
                self._set(cx + i, top_cy + i, lead, '\\', is_lead=True)
                self._set(cx - i, top_cy + i, lead, '/', is_lead=True)
                        
        elif shape == 'round_arch':
            # Romanesque: concentric arches
            for offset in [8, 14]:
                self._draw_arch_round(cx, 3 + offset // 3, self.width - offset * 2, self.height - offset)
                
        elif shape == 'organic':
            # Art Nouveau: flowing curves
            for y in range(4, self.height - 4):
                wave_x = cx + int(6 * math.sin(y * 0.3))
                self._set(wave_x, y, lead, '│', is_lead=True)
                self._set(wave_x - 4, y, lead, '│', is_lead=True)
                self._set(wave_x + 4, y, lead, '│', is_lead=True)
            
            # Circular elements
            for cr in [5, 8]:
                for angle_deg in range(0, 360, 3):
                    angle = math.radians(angle_deg)
                    px = int(cx + cr * math.cos(angle))
                    py = int(cy + cr * math.sin(angle) * 0.7)
                    if self._in_bounds(px, py) and 3 < px < self.width - 3 and 2 < py < self.height - 3:
                        self._set(px, py, lead, '·', is_lead=True)
                        
        elif shape == 'geometric':
            # Art Deco: chevrons and geometric patterns
            for row in range(4, self.height - 3, 4):
                for x in range(4, self.width - 3):
                    offset = (row // 4) % 2 * 4
                    if abs((x + offset) % 8 - 4) < 1:
                        self._set(x, row, lead, '─', is_lead=True)
            
            # Diamond pattern
            for i in range(0, self.width, 8):
                for j in range(min(i, self.height), 0, -1):
                    x = i - j
                    y = 4 + j
                    if self._in_bounds(x, y) and 3 < x < self.width - 3 and 2 < y < self.height - 3:
                        self._set(x, y, lead, '\\', is_lead=True)
                        
        elif shape == 'mosaic':
            # Byzantine: grid of small squares
            for y in range(4, self.height - 3, 3):
                for x in range(3, self.width - 3):
                    self._set(x, y, lead, '─', is_lead=True)
            for x in range(3, self.width - 3, 4):
                for y in range(3, self.height - 3):
                    self._set(x, y, lead, '│', is_lead=True)
            
            # Central medallion
            r = min(self.width, self.height) // 5
            for angle_deg in range(360):
                angle = math.radians(angle_deg)
                for ri in range(r, r + 2):
                    px = int(cx + ri * math.cos(angle))
                    py = int(cy + ri * math.sin(angle) * 0.6)
                    if self._in_bounds(px, py):
                        self._set(px, py, lead, '·', is_lead=True)
                        
        elif shape == 'minimal':
            # Modern: clean horizontal bands
            for i, frac in enumerate([0.25, 0.5, 0.75]):
                y = int(3 + (self.height - 6) * frac)
                for x in range(3, self.width - 3):
                    self._set(x, y, lead, '─', is_lead=True)
            # One vertical
            for y in range(3, self.height - 3):
                self._set(cx, y, lead, '│', is_lead=True)
    
    def _color_regions(self, regions):
        """Color each region with a glass color."""
        palette = self.style['colors']
        accent = self.style['accent']
        
        # Sort regions by size - larger ones get main colors, smaller get accents
        regions.sort(key=len, reverse=True)
        
        for i, region in enumerate(regions):
            # Calculate region center
            avg_x = sum(p[0] for p in region) / len(region)
            avg_y = sum(p[1] for p in region) / len(region)
            
            # Pick color with some spatial coherence
            color_idx = (int(avg_x + avg_y * 0.5) + i) % len(palette)
            color_name = palette[color_idx]
            
            # Occasionally use accent color for small regions
            if len(region) < 15 and random.random() < 0.4:
                color_name = random.choice(accent)
            
            # Pick glass character
            char_type = random.choice(list(GLASS_CHARS.keys()))
            char = GLASS_CHARS[char_type]
            
            # Apply color and character to all cells in region
            for (x, y) in region:
                # Vary the character slightly within a region for texture
                local_char = char
                if random.random() < 0.2:
                    alt_type = random.choice(list(GLASS_CHARS.keys()))
                    local_char = GLASS_CHARS[alt_type]
                
                self._set(x, y, color_name, local_char)
    
    def _add_border(self):
        """Add an ornamental border around the window."""
        lead = self.style['lead_color']
        
        # Top border
        for x in range(self.width):
            self._set(x, 0, lead, '═', is_lead=True)
            self._set(x, 1, lead, '─', is_lead=True)
        
        # Bottom border
        for x in range(self.width):
            self._set(x, self.height - 2, lead, '─', is_lead=True)
            self._set(x, self.height - 1, lead, '═', is_lead=True)
        
        # Side borders
        for y in range(self.height):
            self._set(0, y, lead, '║', is_lead=True)
            self._set(1, y, lead, '│', is_lead=True)
            self._set(self.width - 2, y, lead, '│', is_lead=True)
            self._set(self.width - 1, y, lead, '║', is_lead=True)
        
        # Corners
        self._set(0, 0, lead, '╔', is_lead=True)
        self._set(self.width - 1, 0, lead, '╗', is_lead=True)
        self._set(0, self.height - 1, lead, '╚', is_lead=True)
        self._set(self.width - 1, self.height - 1, lead, '╝', is_lead=True)
    
    def generate(self):
        """Generate the complete stained glass window."""
        self._fill_bg()
        self._draw_frame()
        self._draw_leaded_pattern_inside_frame()
        regions = self._flood_fill_regions()
        self._color_regions(regions)
        self._add_border()
        return self
    
    def render(self):
        """Render the stained glass window to a string."""
        lines = []
        for y in range(self.height):
            line = ''
            prev_color = None
            for x in range(self.width):
                cell = self._get(x, y)
                if cell is None:
                    line += ' '
                    prev_color = None
                elif cell['is_lead']:
                    # Lead lines - use lead color
                    color_code = self._color(cell['color'])
                    if color_code != prev_color:
                        line += color_code
                        prev_color = color_code
                    line += cell['char']
                else:
                    # Glass pieces
                    color_code = self._color(cell['color'])
                    if color_code != prev_color:
                        line += color_code
                        prev_color = color_code
                    line += cell['char']
            line += RESET
            lines.append(line)
        
        return '\n'.join(lines)


def print_header(style_info, seed):
    """Print a decorative header with style info."""
    name = style_info['name']
    desc = style_info['description']
    
    header = f"""
{BOLD}{COLORS['gold']}╔══════════════════════════════════════════════════════════════╗
║  {COLORS['ivory']}✦ Terminal Stained Glass Generator ✦{COLORS['gold']}                              ║
╚══════════════════════════════════════════════════════════════╝{RESET}

{BOLD}{COLORS['gold']}  Style: {COLORS['ivory']}{name}{RESET}
{BOLD}{COLORS['gold']}  Seed:  {COLORS['ivory']}{seed}{RESET}
{BOLD}{COLORS['gold']}  {desc}{RESET}

"""
    print(header)


def print_legend(style_info):
    """Print a color legend."""
    palette = style_info['colors']
    legend = f"\n{BOLD}{COLORS['gold']}  Palette:{RESET} "
    for color_name in palette:
        legend += f"{COLORS[color_name]}██{RESET}"
    print(legend)


def list_styles():
    """Print available styles."""
    print(f"\n{BOLD}{COLORS['gold']}Available Styles:{RESET}\n")
    for key, style in STYLES.items():
        print(f"  {BOLD}{COLORS['ivory']}{key:15s}{RESET} - {style['description']}")
        palette_str = "    Colors: "
        for c in style['colors'][:6]:
            palette_str += f"{COLORS[c]}██{RESET}"
        print(palette_str)
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Terminal Stained Glass Generator - Create beautiful stained glass windows in your terminal!'
    )
    parser.add_argument('-s', '--style', choices=list(STYLES.keys()), default=None,
                        help='Architectural style for the stained glass')
    parser.add_argument('-w', '--width', type=int, default=None,
                        help='Window width in characters (default: auto)')
    parser.add_argument('-H', '--height', type=int, default=None,
                        help='Window height in characters (default: auto)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility')
    parser.add_argument('--list-styles', action='store_true',
                        help='List available architectural styles')
    parser.add_argument('-n', '--count', type=int, default=1,
                        help='Number of windows to generate')
    parser.add_argument('--version', action='version', version=f'stained_glass.py {__version__}',
                        help='Show version and exit')
    
    args = parser.parse_args()
    
    if args.list_styles:
        list_styles()
        return
    
    # Auto-detect terminal size
    try:
        import shutil
        term_size = shutil.get_terminal_size()
        default_width = min(70, term_size.columns - 2)
        default_height = min(35, term_size.lines - 8)
    except OSError:
        default_width = 70
        default_height = 35
    
    width = args.width if args.width is not None else default_width
    height = args.height if args.height is not None else default_height
    
    # Ensure minimum dimensions
    width = max(30, width)
    height = max(15, height)
    
    styles = list(STYLES.keys())
    chosen_style = args.style or random.choice(styles)
    # Fix: seed=0 was treated as falsy with 'or', now uses 'is not None'
    seed = args.seed if args.seed is not None else random.randint(1, 999999)
    
    for i in range(args.count):
        if i > 0:
            print('\n' + '─' * width + '\n')
            seed = seed + 1  # Increment seed for variety
        
        style_info = STYLES[chosen_style]
        print_header(style_info, seed)
        
        gen = StainedGlassGenerator(width=width, height=height, style=chosen_style, seed=seed)
        gen.generate()
        
        window = gen.render()
        print(window)
        
        # Print legend
        legend = f"\n{BOLD}{COLORS['gold']}  Palette:{RESET} "
        for color_name in style_info['colors']:
            legend += f"{COLORS[color_name]}██{RESET}"
        print(legend)
        
        print(f"\n{COLORS['gray']}  Style: {chosen_style} | Seed: {seed} | Dimensions: {width}x{height}{RESET}")
        print(f"{COLORS['gray']}  Regenerate: python stained_glass.py -s {chosen_style} --seed {seed}{RESET}\n")


if __name__ == '__main__':
    main()