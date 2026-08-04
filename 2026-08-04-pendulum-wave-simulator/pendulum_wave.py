#!/usr/bin/env python3
"""
Terminal Pendulum Wave Simulator
=================================
A physics-based ASCII animation of the pendulum wave phenomenon.

A row of pendulums with carefully chosen lengths swings in unison.
Because each pendulum has a slightly different period, they create
mesmerizing traveling-wave patterns, then gradually drift into chaos,
and finally resynchronize — a beautiful demonstration of physics.

The pendulum lengths are chosen so that the longest pendulum completes
N oscillations in a chosen cycle time T, the next completes N+1, the
next N+2, and so on.  After time T all pendulums realign.

Controls (during animation):
    SPACE  — pause / resume
    R      — reduced-motion mode (no trail)
    T      — toggle trail
    +/-    — speed up / slow down
    1-4    — change visualization mode
    Q/Esc  — quit
"""

from __future__ import annotations

import argparse
import math
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from typing import List, Tuple

# ── Terminal helpers ──────────────────────────────────────────────────────────

ANSI = {
    "reset":   "\033[0m",
    "clear":   "\033[2J",
    "hide":    "\033[?25l",
    "show":    "\033[?25h",
    "home":    "\033[H",
    "bold":    "\033[1m",
}

# a pleasant colour palette for the bobs (indexed by pendulum number)
BOB_COLOURS = [
    (255,  0,  0), (255, 80,  0), (255,160,  0), (255,220,  0),
    (200,255,  0), (100,255, 60), (  0,255,160), (  0,220,220),
    (  0,160,255), (  0,100,255), ( 60,  0,255), (140,  0,255),
    (200,  0,255), (255,  0,200), (255,  0,140), (255,  0, 80),
]


def fg(rgb: Tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"\033[38;2;{r};{g};{b}m"


def dim(rgb: Tuple[int, int, int], factor: float = 0.4) -> Tuple[int, int, int]:
    return tuple(int(c * factor) for c in rgb)  # type: ignore


def term_size() -> Tuple[int, int]:
    try:
        import termios, fcntl, struct
        fd = sys.stdout.fileno()
        h, w = struct.unpack("HH", fcntl.ioctl(fd, termios.TIOCGWINSZ, b"\x00" * 8))
        return w, h
    except Exception:
        pass
    cols = os.environ.get("COLUMNS")
    rows = os.environ.get("LINES")
    return (int(cols) if cols else 80, int(rows) if rows else 24)


# ── Physics ───────────────────────────────────────────────────────────────────

G = 9.80665  # m/s²


@dataclass
class Pendulum:
    """A simple pendulum: small-angle approximation."""
    index: int
    length: float          # metres
    amplitude: float        # radians (max angle)
    n_swing: int            # target swings in cycle time T
    bob_char: str = "●"

    @property
    def period(self) -> float:
        return 2 * math.pi * math.sqrt(self.length / G)

    def angle(self, t: float) -> float:
        """Angular displacement at time *t* (radians)."""
        omega = 2 * math.pi / self.period
        return self.amplitude * math.cos(omega * t)

    def x(self, t: float) -> float:
        """Horizontal offset of the bob from rest (metres)."""
        return self.length * math.sin(self.angle(t))

    def y(self, t: float) -> float:
        """Vertical position of the bob below the pivot (metres, positive = down).

        At rest (angle=0) this equals *length*; when swinging the bob
        rises slightly:  y = L·cos(θ).
        """
        return self.length * math.cos(self.angle(t))


def build_pendulums(
    count: int,
    cycle_time: float,
    base_swings: int,
    max_length: float,
    amplitude_deg: float,
) -> List[Pendulum]:
    """
    Create *count* pendulums whose lengths are chosen so that the
    first completes *base_swings* full oscillations in the resync
    cycle time, the second completes base_swings+1, etc.

    The period of pendulum *i* is  T_i = cycle / (base_swings + i).
    From T = 2π√(L/g)  →  L = g(T/2π)².

    The longest pendulum (i=0) is forced to have length *max_length*,
    which in turn determines the true cycle time:
        cycle = base_swings × 2π × √(max_length / g)
    The user-supplied *cycle_time* is used only when *max_length* is
    zero or negative (i.e. "derive length from cycle").
    """
    amp = math.radians(amplitude_deg)

    if max_length > 0:
        # Derive the true cycle time from the desired longest length.
        period_0 = 2 * math.pi * math.sqrt(max_length / G)
        cycle = base_swings * period_0
    else:
        cycle = cycle_time

    pendulums: List[Pendulum] = []
    for i in range(count):
        n = base_swings + i
        period = cycle / n
        L = G * (period / (2 * math.pi)) ** 2
        pendulums.append(Pendulum(
            index=i,
            length=L,
            amplitude=amp,
            n_swing=n,
            bob_char="●",
        ))
    return pendulums


# ── Renderer ──────────────────────────────────────────────────────────────────

class Renderer:
    """
    Maps physical coordinates to the terminal grid and draws a frame.

    The scene shows a horizontal support bar at the top, the pendulum
    strings, and the bobs.  An optional trail shows the path of each
    bob, revealing the wave pattern.
    """

    # ── gradient characters for trail intensity ──
    TRAIL_CHARS = " .·:-=+*#%@"

    def __init__(self, width: int, height: int, pendulums: List[Pendulum],
                 max_x: float, max_y: float, mode: int = 1):
        self.w = width
        self.h = height
        self.pendulums = pendulums
        self.max_x = max_x
        self.max_y = max_y
        self.mode = mode
        self.trail_enabled = True
        # trail[i] is a list of (x, y) recent positions for pendulum i
        self.trails: List[List[Tuple[float, float]]] = [[] for _ in pendulums]
        self.trail_len = 40

    # coordinate transforms -------------------------------------------------
    def to_screen(self, px: float, py: float) -> Tuple[int, int]:
        """Physical (x metres, y metres-down) → terminal (col, row)."""
        col = int(self.w / 2 + px / self.max_x * (self.w / 2 - 2))
        row = int(2 + py / self.max_y * (self.h - 4))
        col = max(0, min(self.w - 1, col))
        row = max(0, min(self.h - 1, row))
        return col, row

    # main draw -------------------------------------------------------------
    def render(self, t: float) -> str:
        lines: List[List[str]] = []
        # blank grid (with colour reset per cell to be safe)
        for _ in range(self.h):
            lines.append([" "] * self.w)

        # ── support bar ──
        bar_row = 1
        for c in range(self.w):
            lines[bar_row][c] = "─"
        lines[bar_row][0] = "╭"
        lines[bar_row][self.w - 1] = "╮"
        # label
        label = f" t = {t:6.2f}s "
        for k, ch in enumerate(label):
            if 2 + k < self.w - 2:
                lines[bar_row][2 + k] = ch

        # ── compute bob positions ──
        positions: List[Tuple[float, float]] = []
        for p in self.pendulums:
            positions.append((p.x(t), p.y(t)))

        # ── update trails ──
        if self.trail_enabled:
            for i, (x, y) in enumerate(positions):
                self.trails[i].append((x, y))
                if len(self.trails[i]) > self.trail_len:
                    self.trails[i].pop(0)

        # ── draw trails ──
        if self.trail_enabled and self.mode in (1, 2):
            for i, trail in enumerate(self.trails):
                colour = BOB_COLOURS[i % len(BOB_COLOURS)]
                n = len(trail)
                for k, (tx, ty) in enumerate(trail):
                    if n <= 1:
                        break
                    intensity = k / (n - 1)  # 0 (oldest) → 1 (newest)
                    if intensity < 0.05:
                        continue
                    col, row = self.to_screen(tx, ty)
                    char_idx = int(intensity * (len(self.TRAIL_CHARS) - 1))
                    ch = self.TRAIL_CHARS[char_idx]
                    fade = 0.15 + 0.85 * intensity
                    r, g, b = dim(colour, fade)
                    if lines[row][col] == " " or self.mode == 2:
                        lines[row][col] = f"\033[38;2;{r};{g};{b}m{ch}\033[0m"

        # ── draw strings ──
        if self.mode in (1, 3):
            for i, p in enumerate(self.pendulums):
                bx, by = positions[i]
                col0 = self.w // 2
                row0 = bar_row
                col1, row1 = self.to_screen(bx, by)
                self._draw_line(lines, col0, row0, col1, row1, "│")

        # ── draw bobs ──
        for i, (bx, by) in enumerate(positions):
            col, row = self.to_screen(bx, by)
            colour = BOB_COLOURS[i % len(BOB_COLOURS)]
            ch = self.pendulums[i].bob_char
            lines[row][col] = f"{fg(colour)}{ch}{ANSI['reset']}"

        # ── draw pivot points ──
        if self.mode in (1, 3):
            lines[bar_row][self.w // 2] = "┬"

        # ── status line ──
        status_y = self.h - 1
        info = (f" pendulums={len(self.pendulums)}  "
                f"mode={self.mode}  trail={'on' if self.trail_enabled else 'off'}  "
                f"[SPACE]pause [T]trail [1-4]mode [+/-]speed [Q]quit")
        for k, ch in enumerate(info):
            if k < self.w:
                lines[status_y][k] = ch

        # ── assemble ──
        out = []
        for row in lines:
            out.append("".join(row))
        return "\n".join(out)

    def _draw_line(self, grid, x0, y0, x1, y1, ch="│"):
        """Bresenham-ish line, only draws vertical-ish strings."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        steps = max(dx, dy, 1)
        for s in range(steps + 1):
            t = s / steps
            cx = int(x0 + (x1 - x0) * t)
            cy = int(y0 + (y1 - y0) * t)
            if 0 <= cy < self.h and 0 <= cx < self.w:
                if grid[cy][cx] == " ":
                    grid[cy][cx] = ch


# ── Non-blocking input ───────────────────────────────────────────────────────

class NonBlockingInput:
    """Minimal raw-mode stdin reader for single-key input."""

    def __init__(self):
        self._fd = sys.stdin.fileno()
        self._old = None

    def __enter__(self):
        import termios
        self._old = termios.tcgetattr(self._fd)
        import tty
        tty.setraw(self._fd)
        # set non-blocking
        import fcntl as _fcntl
        flags = _fcntl.fcntl(self._fd, _fcntl.F_GETFL)
        _fcntl.fcntl(self._fd, _fcntl.F_SETFL, flags | os.O_NONBLOCK)
        return self

    def __exit__(self, *args):
        import termios
        if self._old is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)

    def read_key(self) -> str:
        try:
            data = sys.stdin.read(1)
            if data == "\x1b":
                # possible escape sequence
                try:
                    rest = sys.stdin.read(2)
                    data += rest
                except Exception:
                    pass
            return data
        except Exception:
            return ""


# ── Main loop ────────────────────────────────────────────────────────────────

def run_animation(pendulums: List[Pendulum], cycle_time: float,
                  max_x: float, max_y: float, fps: int = 30):
    import shutil
    w, h = shutil.get_terminal_size((80, 24))
    renderer = Renderer(w, h, pendulums, max_x, max_y, mode=1)

    sys.stdout.write(ANSI["clear"] + ANSI["hide"])
    sys.stdout.flush()

    paused = False
    speed = 1.0
    sim_t = 0.0
    last_wall = time.monotonic()
    dt_cap = 1.0 / fps

    try:
        with NonBlockingInput() as nbi:
            while True:
                now = time.monotonic()
                real_dt = now - last_wall
                last_wall = now
                if not paused:
                    sim_t += real_dt * speed

                # handle keys
                key = nbi.read_key()
                if key:
                    k = key.lower()
                    if k in ("q", "\x1b"):
                        break
                    elif key == " ":
                        paused = not paused
                    elif k == "t":
                        renderer.trail_enabled = not renderer.trail_enabled
                        if not renderer.trail_enabled:
                            renderer.trails = [[] for _ in pendulums]
                    elif k == "r":
                        renderer.trail_enabled = False
                        renderer.trails = [[] for _ in pendulums]
                    elif k in ("1", "2", "3", "4"):
                        renderer.mode = int(k)
                    elif key == "+" or key == "=":
                        speed = min(speed * 1.25, 8.0)
                    elif key == "-" or key == "_":
                        speed = max(speed / 1.25, 0.1)

                # resize check
                nw, nh = shutil.get_terminal_size((80, 24))
                if (nw, nh) != (renderer.w, renderer.h):
                    renderer.w, renderer.h = nw, nh
                    renderer.trails = [[] for _ in pendulums]
                    sys.stdout.write(ANSI["clear"])

                frame = renderer.render(sim_t)
                sys.stdout.write(ANSI["home"] + frame)
                sys.stdout.flush()

                elapsed = time.monotonic() - now
                sleep = dt_cap - elapsed
                if sleep > 0:
                    time.sleep(sleep)
    finally:
        sys.stdout.write(ANSI["show"] + ANSI["reset"] + "\n")
        sys.stdout.flush()


# ── Static / demo frame (no raw mode) ────────────────────────────────────────

def render_static(pendulums: List[Pendulum], t: float, width: int,
                  height: int, max_x: float, max_y: float, mode: int = 1) -> str:
    """Render a single frame without raw-mode input — for --frame and tests."""
    renderer = Renderer(width, height, pendulums, max_x, max_y, mode=mode)
    renderer.trail_enabled = False
    return renderer.render(t)


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Terminal Pendulum Wave Simulator — watch pendulums "
                    "create waves, chaos, and resynchronization.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python pendulum_wave.py                    # 16 pendulums, 60s cycle, animated
  python pendulum_wave.py -n 24 -T 90        # 24 pendulums, 90s cycle
  python pendulum_wave.py --frame 15.0       # render a single frame at t=15s
  python pendulum_wave.py --static --frames 8  # print 8 sampled frames
  python pendulum_wave.py --info             # print physics info and exit
""",
    )
    p.add_argument("-n", "--num", type=int, default=16,
                   help="number of pendulums (default 16)")
    p.add_argument("-T", "--cycle", type=float, default=60.0,
                   help="resynchronisation cycle time in seconds (default 60)")
    p.add_argument("-s", "--swings", type=int, default=51,
                   help="oscillations of the longest pendulum in one cycle "
                        "(default 51)")
    p.add_argument("-a", "--amplitude", type=float, default=12.0,
                   help="swing amplitude in degrees (default 12)")
    p.add_argument("-L", "--max-length", type=float, default=0.50,
                   help="length of the longest pendulum in metres (default 0.50)")
    p.add_argument("--fps", type=int, default=30, help="animation FPS (default 30)")
    p.add_argument("--frame", type=float, default=None,
                   help="render a single static frame at the given time and exit")
    p.add_argument("--static", action="store_true",
                   help="print a series of sampled frames (no animation)")
    p.add_argument("--frames", type=int, default=8,
                   help="number of frames for --static (default 8)")
    p.add_argument("--mode", type=int, default=1, choices=(1, 2, 3, 4),
                   help="visualization mode (1=all, 2=trail-only, "
                        "3=strings-only, 4=bobs-only)")
    p.add_argument("--info", action="store_true",
                   help="print physics details and exit (no rendering)")
    p.add_argument("--width", type=int, default=None, help="force terminal width")
    p.add_argument("--height", type=int, default=None, help="force terminal height")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if args.num < 2:
        print("error: need at least 2 pendulums", file=sys.stderr)
        return 1
    if args.cycle <= 0 or args.swings < 1:
        print("error: cycle time and swings must be positive", file=sys.stderr)
        return 1

    pendulums = build_pendulums(
        count=args.num,
        cycle_time=args.cycle,
        base_swings=args.swings,
        max_length=args.max_length,
        amplitude_deg=args.amplitude,
    )

    # physical extent for rendering
    max_length = max(p.length for p in pendulums)
    # horizontal: bob can swing out to L*sin(amp)
    max_x = max_length * math.sin(math.radians(args.amplitude))
    # vertical: bob hangs at L*cos(amp) at the extremes, L at rest
    # → total vertical extent is ~max_length (use full length)
    max_y_total = max_length * 1.05

    if args.info:
        # compute the true cycle time from the longest pendulum
        true_cycle = args.swings * pendulums[0].period
        print(f"Pendulum Wave — {args.num} pendulums")
        print(f"Longest pendulum: {pendulums[0].length*100:.2f} cm  "
              f"(period {pendulums[0].period:.4f} s)")
        print(f"Resync cycle: {true_cycle:.2f} s  "
              f"(longest swings {args.swings}×)")
        print(f"{'#':>3}  {'length(cm)':>10}  {'period(s)':>9}  {'swings':>7}")
        print("-" * 38)
        for p in pendulums:
            print(f"{p.index:>3}  {p.length*100:>10.2f}  {p.period:>9.4f}  "
                  f"{p.n_swing:>7}")
        print(f"\nAfter {true_cycle:.2f}s all pendulums realign.")
        return 0

    if args.frame is not None:
        w = args.width or 80
        h = args.height or 24
        print(render_static(pendulums, args.frame, w, h, max_x, max_y_total,
                            mode=args.mode))
        return 0

    if args.static:
        true_cycle = args.swings * pendulums[0].period
        w = args.width or 80
        h = args.height or 22
        step = true_cycle / args.frames
        for i in range(args.frames):
            t = i * step
            print(f"\n── t = {t:.2f}s {'─' * (w - 16)}")
            print(render_static(pendulums, t, w, h, max_x, max_y_total,
                                mode=args.mode))
        return 0

    # animated mode
    w = args.width or term_size()[0]
    h = args.height or term_size()[1]
    run_animation(pendulums, args.cycle, max_x, max_y_total, fps=args.fps)
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    sys.exit(main())