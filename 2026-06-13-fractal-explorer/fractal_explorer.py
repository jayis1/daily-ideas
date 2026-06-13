#!/usr/bin/env python3
"""
ASCII Fractal Explorer — Explore Mandelbrot and Julia sets in your terminal.

Zoom, pan, switch fractals, change color palettes, and save renders
to text files — all from the comfort of your keyboard.
"""

import argparse
import curses
import math
import os
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Color palette definitions (each maps iteration 0..max_iter to a char + color)
# ---------------------------------------------------------------------------

PALETTES = OrderedDict()

def _make_gradient(name: str, stops: List[Tuple[int, int, int]], chars: str = " .:-=+*#%@"):
    """Register a palette from RGB stops, interpolating across chars."""
    steps = len(chars)
    colors = []
    for i in range(steps):
        t = i / max(steps - 1, 1)
        seg = t * (len(stops) - 1)
        idx = min(int(seg), len(stops) - 2)
        frac = seg - idx
        r = int(stops[idx][0] + (stops[idx + 1][0] - stops[idx][0]) * frac)
        g = int(stops[idx][1] + (stops[idx + 1][1] - stops[idx][1]) * frac)
        b = int(stops[idx][2] + (stops[idx + 1][2] - stops[idx][2]) * frac)
        colors.append((chars[i], (r, g, b)))
    PALETTES[name] = colors

_make_gradient("fire",
    [(0,0,0),(128,0,0),(255,60,0),(255,165,0),(255,255,100),(255,255,255)])
_make_gradient("ocean",
    [(0,0,20),(0,20,80),(0,80,180),(40,180,255),(180,240,255),(255,255,255)])
_make_gradient("matrix",
    [(0,0,0),(0,40,0),(0,120,0),(0,200,0),(100,255,100),(220,255,220)])
_make_gradient("electric",
    [(0,0,30),(80,0,160),(160,0,255),(255,0,200),(255,100,255),(255,255,255)])
_make_gradient("earth",
    [(20,10,0),(60,40,0),(120,80,20),(60,140,40),(40,180,100),(200,255,200)])
_make_gradient("grayscale",
    [(0,0,0),(60,60,60),(120,120,120),(180,180,180),(220,220,220),(255,255,255)])


# ---------------------------------------------------------------------------
# Fractal math
# ---------------------------------------------------------------------------

def mandelbrot(cx: float, cy: float, max_iter: int, julia_c: complex = 0+0j,
               julia: bool = False) -> int:
    """Return escape iteration count for a point in the complex plane."""
    if julia:
        z = complex(cx, cy)
        c = julia_c
    else:
        z = 0 + 0j
        c = complex(cx, cy)
    for i in range(max_iter):
        if z.real * z.real + z.imag * z.imag > 4.0:
            return i
        z = z * z + c
    return max_iter


def smooth_color(iter_count: int, max_iter: int, cx: float, cy: float,
                 julia: bool, julia_c: complex) -> float:
    """Smooth iteration count for nicer gradients (using log2 escape)."""
    if iter_count >= max_iter:
        return float(max_iter)
    if julia:
        z = complex(cx, cy)
        c = julia_c
    else:
        z = 0 + 0j
        c = complex(cx, cy)
    for i in range(iter_count):
        z = z * z + c
    if z.real * z.real + z.imag * z.imag <= 0:
        return float(iter_count)
    log_zn = math.log(z.real * z.real + z.imag * z.imag) / 2.0
    nu = math.log(log_zn / math.log(2)) / math.log(2)
    return iter_count + 1 - nu


# ---------------------------------------------------------------------------
# Viewport state
# ---------------------------------------------------------------------------

@dataclass
class Viewport:
    center_x: float = -0.5
    center_y: float = 0.0
    zoom: float = 1.5        # half-width of the view in complex coords
    max_iter: int = 100
    palette_name: str = "fire"
    julia: bool = False
    julia_cx: float = -0.7
    julia_cy: float = 0.27015
    smooth: bool = True
    ascii_mode: bool = True   # True = chars, False = half-blocks
    needs_redraw: bool = True

    @property
    def julia_c(self) -> complex:
        return complex(self.julia_cx, self.julia_cy)

    @property
    def aspect(self) -> float:
        # approximate terminal character aspect ratio
        return 0.5  # chars are ~2x tall as wide


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class Renderer:
    def __init__(self, stdscr: curses.window, vp: Viewport):
        self.stdscr = stdscr
        self.vp = vp
        self.palette = PALETTES[vp.palette_name]
        self._color_pairs: dict = {}
        self._next_pair = 1
        self._init_colors()

    def _init_colors(self):
        """Pre-register color pairs for the current palette."""
        self._color_pairs = {}
        self._next_pair = 1
        self.palette = PALETTES[self.vp.palette_name]
        for ch, (r, g, b) in self.palette:
            idx = self._next_pair
            try:
                curses.init_color(idx + 7, r * 1000 // 255, g * 1000 // 255, b * 1000 // 255)
            except curses.error:
                pass  # terminal doesn't support custom colors
            try:
                curses.init_pair(idx, idx + 7, curses.COLOR_BLACK)
            except curses.error:
                curses.init_pair(idx, curses.COLOR_WHITE, curses.COLOR_BLACK)
            self._color_pairs[(ch, (r, g, b))] = idx
            self._next_pair += 1

    def _get_color_pair(self, r: int, g: int, b: int) -> int:
        """Find the closest registered color for an RGB value."""
        best = None
        best_dist = float('inf')
        for ch, (cr, cg, cb) in self.palette:
            d = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
            if d < best_dist:
                best_dist = d
                best = (ch, (cr, cg, cb))
        if best and best in self._color_pairs:
            return self._color_pairs[best]
        return 0

    def render(self):
        """Render the fractal into the terminal."""
        vp = self.vp
        h, w = self.stdscr.getmaxyx()
        # leave room for status bar
        draw_h = max(h - 2, 1)
        draw_w = w

        aspect = vp.aspect
        x_min = vp.center_x - vp.zoom
        x_max = vp.center_x + vp.zoom
        y_range = vp.zoom * draw_h / draw_w / aspect
        y_min = vp.center_y - y_range
        y_max = vp.center_y + y_range

        dx = (x_max - x_min) / draw_w
        dy = (y_max - y_min) / draw_h

        palette = self.palette
        n_colors = len(palette)

        try:
            self.stdscr.erase()
        except curses.error:
            return

        for row in range(draw_h):
            cy = y_min + row * dy
            line_buf = []
            for col in range(draw_w):
                cx = x_min + col * dx
                if vp.smooth:
                    raw = smooth_color(0, vp.max_iter, cx, cy,
                                       vp.julia, vp.julia_c)
                    # compute actual iteration for smooth mapping
                    it = mandelbrot(cx, cy, vp.max_iter, vp.julia_c, vp.julia)
                    if it >= vp.max_iter:
                        # inside the set
                        ch, (r, g, b) = palette[0]
                    else:
                        raw = smooth_color(it, vp.max_iter, cx, cy,
                                           vp.julia, vp.julia_c)
                        t = raw / vp.max_iter
                        idx = int(t * (n_colors - 1))
                        idx = max(0, min(idx, n_colors - 1))
                        ch, (r, g, b) = palette[idx]
                else:
                    it = mandelbrot(cx, cy, vp.max_iter, vp.julia_c, vp.julia)
                    if it >= vp.max_iter:
                        ch, (r, g, b) = palette[0]
                    else:
                        t = it / vp.max_iter
                        idx = int(t * (n_colors - 1))
                        idx = max(0, min(idx, n_colors - 1))
                        ch, (r, g, b) = palette[idx]

                pair = self._color_pairs.get((ch, (r, g, b)), 0)
                try:
                    self.stdscr.addch(row, col, ord(ch), curses.color_pair(pair))
                except curses.error:
                    pass

        # Status bar
        fractal_name = "Julia" if vp.julia else "Mandelbrot"
        status = (f" {fractal_name} | Center: ({vp.center_x:.6f}, {vp.center_y:.6f}) "
                  f"| Zoom: {1/vp.zoom:.1f}x | Iter: {vp.max_iter} "
                  f"| Palette: {vp.palette_name} | Smooth: {'on' if vp.smooth else 'off'}")
        if vp.julia:
            status += f" | Julia c: {vp.julia_cx:.4f}+{vp.julia_cy:.4f}i"

        try:
            self.stdscr.addstr(draw_h, 0, status[:w - 1], curses.A_REVERSE)
        except curses.error:
            pass
        help_line = " Arrows:Pan  +/-:Zoom  M:Mode  P:Palette  I:Iter  S:Smooth  Q:Quit  R:Reset  H:Help"
        try:
            self.stdscr.addstr(draw_h + 1, 0, help_line[:w - 1],
                                curses.A_DIM)
        except curses.error:
            pass

        self.stdscr.refresh()
        vp.needs_redraw = False


# ---------------------------------------------------------------------------
# Non-curses batch renderer (for --export mode)
# ---------------------------------------------------------------------------

def render_to_text(vp: Viewport, width: int = 120, height: int = 60) -> str:
    """Render fractal to plain text (ANSI color codes)."""
    palette = PALETTES[vp.palette_name]
    n_colors = len(palette)
    aspect = vp.aspect

    x_min = vp.center_x - vp.zoom
    x_max = vp.center_x + vp.zoom
    y_range = vp.zoom * height / width / aspect
    y_min = vp.center_y - y_range
    y_max = vp.center_y + y_range

    dx = (x_max - x_min) / width
    dy = (y_max - y_min) / height

    # ANSI color codes
    def ansi_color(r, g, b):
        return f"\033[38;2;{r};{g};{b}m"

    RESET = "\033[0m"
    lines = []
    for row in range(height):
        cy = y_min + row * dy
        buf = ""
        for col in range(width):
            cx = x_min + col * dx
            it = mandelbrot(cx, cy, vp.max_iter, vp.julia_c, vp.julia)
            if it >= vp.max_iter:
                ch, (r, g, b) = palette[0]
            else:
                if vp.smooth:
                    raw = smooth_color(it, vp.max_iter, cx, cy,
                                       vp.julia, vp.julia_c)
                    t = raw / vp.max_iter
                else:
                    t = it / vp.max_iter
                idx = int(t * (n_colors - 1))
                idx = max(0, min(idx, n_colors - 1))
                ch, (r, g, b) = palette[idx]
            buf += f"{ansi_color(r, g, b)}{ch}"
        lines.append(buf + RESET)

    # Legend
    fractal_name = "Julia" if vp.julia else "Mandelbrot"
    lines.append(f"\n{fractal_name} set | Center: ({vp.center_x:.6f}, {vp.center_y:.6f})"
                 f" | Zoom: {1/vp.zoom:.1f}x | Iter: {vp.max_iter}"
                 f" | Palette: {vp.palette_name}")
    return "\n".join(lines)


def render_to_plain_text(vp: Viewport, width: int = 120, height: int = 60) -> str:
    """Render fractal to plain ASCII (no color codes)."""
    chars = " .:-=+*#%@"
    n = len(chars)

    aspect = vp.aspect
    x_min = vp.center_x - vp.zoom
    x_max = vp.center_x + vp.zoom
    y_range = vp.zoom * height / width / aspect
    y_min = vp.center_y - y_range
    y_max = vp.center_y + y_range
    dx = (x_max - x_min) / width
    dy = (y_max - y_min) / height

    lines = []
    for row in range(height):
        cy = y_min + row * dy
        buf = ""
        for col in range(width):
            cx = x_min + col * dx
            it = mandelbrot(cx, cy, vp.max_iter, vp.julia_c, vp.julia)
            if it >= vp.max_iter:
                buf += chars[0]
            else:
                t = it / vp.max_iter
                idx = int(t * (n - 1))
                idx = max(0, min(idx, n - 1))
                buf += chars[idx]
        lines.append(buf)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Interactive mode (curses)
# ---------------------------------------------------------------------------

def interactive_main(stdscr: curses.window, vp: Viewport):
    """Main interactive loop with curses."""
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)

    # Try to enable 256 colors
    try:
        curses.start_color()
        curses.use_default_colors()
    except Exception:
        pass

    renderer = Renderer(stdscr, vp)
    vp.needs_redraw = True

    # Help overlay
    showing_help = False
    help_text = [
        "╔══════════════════════════════════════════╗",
        "║        ASCII Fractal Explorer            ║",
        "╠══════════════════════════════════════════╣",
        "║  Arrow Keys    Pan around                ║",
        "║  + / -         Zoom in / out             ║",
        "║  M             Toggle Mandelbrot/Julia    ║",
        "║  P             Cycle color palette        ║",
        "║  I / Shift+I   Increase / Decrease iter  ║",
        "║  S             Toggle smooth coloring     ║",
        "║  R             Reset view                 ║",
        "║  E             Export to file              ║",
        "║  H             Toggle this help            ║",
        "║  Q / Esc       Quit                       ║",
        "╠══════════════════════════════════════════╣",
        "║  In Julia mode:                          ║",
        "║  J             Cycle Julia presets         ║",
        "║  Shift+Arrows  Adjust Julia c parameter   ║",
        "╚══════════════════════════════════════════╝",
    ]

    julia_presets = [
        (-0.7, 0.27015),
        (-0.8, 0.156),
        (0.285, 0.01),
        (-0.4, 0.6),
        (0.45, 0.1428),
        (-0.70176, -0.3842),
        (-0.835, -0.2321),
        (-0.1, 0.651),
    ]
    julia_preset_idx = 0

    PAN_STEP_SMALL = 0.05
    ZOOM_FACTOR = 1.5

    while True:
        if vp.needs_redraw and not showing_help:
            renderer.render()

        try:
            key = stdscr.getch()
        except Exception:
            key = -1

        if key == -1:
            continue

        # Quit
        if key in (ord('q'), ord('Q'), 27):  # 27 = ESC
            if showing_help:
                showing_help = False
                vp.needs_redraw = True
                continue
            break

        # Help
        if key in (ord('h'), ord('H')):
            showing_help = not showing_help
            if showing_help:
                stdscr.erase()
                h, w = stdscr.getmaxyx()
                start_row = max(0, (h - len(help_text)) // 2)
                for i, line in enumerate(help_text):
                    col = max(0, (w - len(line)) // 2)
                    try:
                        stdscr.addstr(start_row + i, col, line,
                                      curses.A_BOLD)
                    except curses.error:
                        pass
                stdscr.refresh()
            else:
                vp.needs_redraw = True
            continue

        if showing_help:
            continue

        # Movement
        if key == curses.KEY_UP or key == ord('w') or key == ord('W'):
            vp.center_y -= vp.zoom * PAN_STEP_SMALL
            vp.needs_redraw = True
        elif key == curses.KEY_DOWN or key == ord('s') or key == ord('S'):
            # Avoid conflict with smooth toggle — use shift check
            if key == ord('S'):
                vp.smooth = not vp.smooth
                vp.needs_redraw = True
            else:
                vp.center_y += vp.zoom * PAN_STEP_SMALL
                vp.needs_redraw = True
        elif key == curses.KEY_LEFT or key == ord('a') or key == ord('A'):
            vp.center_x -= vp.zoom * PAN_STEP_SMALL
            vp.needs_redraw = True
        elif key == curses.KEY_RIGHT or key == ord('d') or key == ord('D'):
            vp.center_x += vp.zoom * PAN_STEP_SMALL
            vp.needs_redraw = True

        # Smooth toggle
        elif key == ord('f') or key == ord('F'):
            vp.smooth = not vp.smooth
            vp.needs_redraw = True

        # Zoom
        elif key in (ord('+'), ord('=')):
            vp.zoom /= ZOOM_FACTOR
            vp.max_iter = max(50, int(50 + 30 * math.log10(1 / vp.zoom + 1)))
            vp.needs_redraw = True
        elif key in (ord('-'), ord('_')):
            vp.zoom *= ZOOM_FACTOR
            vp.max_iter = max(50, int(50 + 30 * math.log10(1 / vp.zoom + 1)))
            vp.needs_redraw = True

        # Mode toggle
        elif key == ord('m') or key == ord('M'):
            vp.julia = not vp.julia
            vp.needs_redraw = True

        # Palette cycle
        elif key == ord('p') or key == ord('P'):
            names = list(PALETTES.keys())
            idx = names.index(vp.palette_name)
            vp.palette_name = names[(idx + 1) % len(names)]
            renderer = Renderer(stdscr, vp)
            vp.needs_redraw = True

        # Iterations
        elif key == ord('i'):
            vp.max_iter = min(5000, vp.max_iter + 50)
            vp.needs_redraw = True
        elif key == ord('I'):
            vp.max_iter = max(20, vp.max_iter - 50)
            vp.needs_redraw = True

        # Reset
        elif key == ord('r') or key == ord('R'):
            vp.center_x = -0.5 if not vp.julia else 0.0
            vp.center_y = 0.0
            vp.zoom = 1.5
            vp.max_iter = 100
            vp.needs_redraw = True

        # Julia presets
        elif key == ord('j') or key == ord('J'):
            julia_preset_idx = (julia_preset_idx + 1) % len(julia_presets)
            vp.julia_cx, vp.julia_cy = julia_presets[julia_preset_idx]
            vp.julia = True
            vp.needs_redraw = True

        # Export
        elif key == ord('e') or key == ord('E'):
            fname = os.path.expanduser("~/fractal_export.txt")
            output = render_to_text(vp)
            with open(fname, "w") as f:
                f.write(output)
            # Flash message
            h, w = stdscr.getmaxyx()
            msg = f" Exported to {fname} "
            try:
                stdscr.addstr(h // 2, max(0, (w - len(msg)) // 2), msg,
                              curses.A_REVERSE | curses.A_BOLD)
                stdscr.refresh()
                time.sleep(1.5)
            except curses.error:
                pass
            vp.needs_redraw = True

        # Shift+Arrows for Julia c parameter (using curses escape sequences)
        elif key == 0x102:  # shift up
            vp.julia_cy += 0.01
            vp.needs_redraw = True
        elif key == 0x103:  # shift down
            vp.julia_cy -= 0.01
            vp.needs_redraw = True
        elif key == 0x104:  # shift left
            vp.julia_cx -= 0.01
            vp.needs_redraw = True
        elif key == 0x105:  # shift right
            vp.julia_cx += 0.01
            vp.needs_redraw = True


# ---------------------------------------------------------------------------
# CLI interface
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ASCII Fractal Explorer — Explore Mandelbrot and Julia sets in your terminal.")
    parser.add_argument("--julia", action="store_true",
                        help="Start in Julia set mode")
    parser.add_argument("--julia-c", type=str, default=None,
                        help="Julia c parameter as 'real,imag' (e.g. '-0.7,0.27015')")
    parser.add_argument("--center", type=str, default=None,
                        help="Center as 'x,y' (e.g. '-0.5,0')")
    parser.add_argument("--zoom", type=float, default=None,
                        help="Initial zoom level (half-width in complex coords)")
    parser.add_argument("--iter", type=int, default=None,
                        help="Maximum iterations")
    parser.add_argument("--palette", type=str, default=None,
                        choices=list(PALETTES.keys()),
                        help="Color palette name")
    parser.add_argument("--smooth", action="store_true", default=True,
                        help="Enable smooth coloring (default)")
    parser.add_argument("--no-smooth", action="store_true",
                        help="Disable smooth coloring")
    parser.add_argument("--export", type=str, default=None,
                        help="Export to file and exit (non-interactive)")
    parser.add_argument("--width", type=int, default=120,
                        help="Width for export mode (default: 120)")
    parser.add_argument("--height", type=int, default=60,
                        help="Height for export mode (default: 60)")
    parser.add_argument("--plain", action="store_true",
                        help="Plain text export (no ANSI colors)")
    parser.add_argument("--no-curses", action="store_true",
                        help="Print fractal to terminal directly (no curses)")

    args = parser.parse_args()

    vp = Viewport()

    if args.julia:
        vp.julia = True
    if args.julia_c:
        parts = args.julia_c.split(",")
        vp.julia_cx = float(parts[0])
        vp.julia_cy = float(parts[1])
        vp.julia = True
    if args.center:
        parts = args.center.split(",")
        vp.center_x = float(parts[0])
        vp.center_y = float(parts[1])
    if args.zoom is not None:
        vp.zoom = args.zoom
    if args.iter is not None:
        vp.max_iter = args.iter
    if args.palette:
        vp.palette_name = args.palette
    if args.no_smooth:
        vp.smooth = False

    # Non-interactive export
    if args.export:
        if args.plain:
            output = render_to_plain_text(vp, args.width, args.height)
        else:
            output = render_to_text(vp, args.width, args.height)
        with open(args.export, "w") as f:
            f.write(output)
        print(f"Fractal exported to {args.export}")
        return

    # Direct terminal print (no curses)
    if args.no_curses:
        try:
            h, w = os.get_terminal_size()
        except OSError:
            w, h = args.width, args.height
        if args.plain:
            output = render_to_plain_text(vp, w, h - 2)
        else:
            output = render_to_text(vp, w, h - 2)
        print(output)
        return

    # Interactive curses mode
    curses.wrapper(interactive_main, vp)


if __name__ == "__main__":
    main()