#!/usr/bin/env python3
"""
Galton Board (Bean Machine / Quincunx) Simulator
=================================================

A live, interactive terminal simulation of a Galton board: balls are dropped
from the top, bounce left or right off a triangular grid of pegs, and pile up
at the bottom into a histogram that converges to a normal (Gaussian) bell curve.

Features
--------
* Animated ASCII rendering of the board, falling balls, pegs, and stacked bins.
* Real-time histogram with running normal-distribution fit overlay.
* Configurable rows of pegs, ball count, drop rate, and board dimensions.
* Live statistics: total balls, mean, variance, skewness, kurtosis.
* Multiple display modes: `animate`, `batch`, and `static` (one-shot render).
* Color and no-color modes; UTF-8 and ASCII fallback glyph sets.
* Seedable RNG for reproducibility; CSV / JSON export of the final histogram.
* Self-test suite baked in (`--test`).

Controls (animate mode)
-----------------------
  SPACE  drop a single ball from a random column
  ENTER  drop a ball from the center column
  b      toggle batch mode (rapid continuous dropping)
  + / -  increase / decrease drop rate
  c      clear the bins
  r      reset everything
  q      quit and print the final histogram

Usage
-----
  python3 galton_board.py                      # interactive animation, 12 rows
  python3 galton_board.py --rows 15 --balls 2000 --batch
  python3 galton_board.py --static --rows 10 --balls 5000 --export result.csv
  python3 galton_board.py --test
  python3 galton_board.py --version
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import random
import shutil
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

try:
    import termios
    import tty
    import select
    _POSIX = True
except Exception:  # pragma: no cover - non-posix fallback
    termios = None  # type: ignore[assignment]
    tty = None  # type: ignore[assignment]
    select = None  # type: ignore[assignment]
    _POSIX = False

__version__ = "1.0.1"

# ---------------------------------------------------------------------------
# Glyph sets
# ---------------------------------------------------------------------------

GLYPHS_UTF8 = {
    "ball": "●",
    "peg": "∘",
    "bin_wall": "│",
    "bin_floor": "─",
    "bar": "█",
    "bar_top": "▀",
    "grid_x": "·",
    "curve": "▓",
}

GLYPHS_ASCII = {
    "ball": "o",
    "peg": ".",
    "bin_wall": "|",
    "bin_floor": "-",
    "bar": "#",
    "bar_top": "^",
    "grid_x": ".",
    "curve": "%",
}

# ANSI color helpers ---------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"


def _color(text: str, code: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{code}{text}{RESET}"


# ---------------------------------------------------------------------------
# Statistics helpers (Welford-style running moments)
# ---------------------------------------------------------------------------

@dataclass
class RunningStats:
    n: int = 0
    mean: float = 0.0
    M2: float = 0.0
    M3: float = 0.0
    M4: float = 0.0
    min_val: float = math.inf
    max_val: float = -math.inf

    def add(self, x: float) -> None:
        self.n += 1
        n = self.n
        delta = x - self.mean
        delta_n = delta / n
        term1 = delta * delta_n * (n - 1)
        self.mean += delta_n
        self.M4 += (
            term1 * delta_n ** 2 * (n * n - 3 * n + 3)
            + 6 * delta_n ** 2 * self.M2
            - 4 * delta_n * self.M3
        )
        self.M3 += term1 * delta_n * (n - 2) - 3 * delta_n * self.M2
        self.M2 += term1
        if x < self.min_val:
            self.min_val = x
        if x > self.max_val:
            self.max_val = x

    @property
    def variance(self) -> float:
        return self.M2 / self.n if self.n > 0 else 0.0

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)

    @property
    def skewness(self) -> float:
        if self.n < 3 or self.M2 == 0:
            return 0.0
        n = self.n
        return (math.sqrt(n) * self.M3) / (self.M2 ** 1.5)

    @property
    def kurtosis(self) -> float:  # excess kurtosis
        if self.n < 4 or self.M2 == 0:
            return 0.0
        n = self.n
        return (n * self.M4) / (self.M2 * self.M2) - 3.0


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass
class Ball:
    col: float            # continuous column position (0 = far left peg)
    row: int              # current peg row (0 = top)
    x: float              # pixel x for rendering interpolation
    y: float              # pixel y for rendering interpolation
    target_x: float = 0.0
    target_y: float = 0.0
    done: bool = False
    bin_index: int = -1


@dataclass
class GaltonBoard:
    rows: int = 12
    bins: List[int] = field(default_factory=list)
    rng: random.Random = field(default_factory=lambda: random.Random())
    stats: RunningStats = field(default_factory=RunningStats)
    total_dropped: int = 0
    # configurable geometry
    width: int = 70
    height: int = 24

    def __post_init__(self) -> None:
        self.num_bins = self.rows + 1
        if not self.bins:
            self.bins = [0] * self.num_bins

    # physics ---------------------------------------------------------------

    def drop_ball(self, start_col: Optional[float] = None) -> Ball:
        """Create a ball at the top.  `start_col` in [0, rows]; defaults center."""
        if start_col is None:
            start_col = self.rows / 2.0
        # clamp
        start_col = max(0.0, min(float(self.rows), start_col))
        ball = Ball(
            col=start_col,
            row=0,
            x=self._col_to_x(start_col),
            y=0.0,
            target_x=self._col_to_x(start_col),
            target_y=0.0,
        )
        self.total_dropped += 1
        return ball

    def step_ball(self, ball: Ball) -> None:
        """Advance a ball one peg row.  At each row it goes left or right with
        p=0.5, perturbed around the nearest peg column."""
        if ball.done:
            return
        # decide direction
        col = ball.col
        # nearest peg column at this row
        # pegs at row r are at columns 0..r  (but we center them)
        # We treat `col` as a continuous position; rounding gives nearest peg.
        # At each step, the ball shifts left or right by 0.5.
        if self.rng.random() < 0.5:
            ball.col -= 0.5
        else:
            ball.col += 0.5
        # clamp within board
        ball.col = max(0.0, min(float(self.rows), ball.col))
        ball.row += 1
        ball.target_x = self._col_to_x(ball.col)
        ball.target_y = float(ball.row)
        if ball.row >= self.rows:
            # settle into a bin
            bin_index = int(round(ball.col))
            bin_index = max(0, min(self.num_bins - 1, bin_index))
            ball.bin_index = bin_index
            ball.done = True
            self.bins[bin_index] += 1
            self.stats.add(bin_index)

    # geometry helpers ------------------------------------------------------

    def _col_to_x(self, col: float) -> float:
        # map column [0, rows] to pixel x in [margin, width - margin]
        margin = 2
        usable = self.width - 2 * margin
        if self.rows <= 0:
            return margin
        return margin + (col / self.rows) * usable

    def pixel_y_of_row(self, row: int) -> int:
        peg_zone = self.height - self.num_bins - 2  # space for bins
        if self.rows <= 0:
            return 1
        # rows 0..rows-1 distributed in peg_zone
        if peg_zone <= 0:
            return row
        return 1 + int((row / max(1, self.rows)) * peg_zone)

    @property
    def bin_zone_top(self) -> int:
        return self.pixel_y_of_row(self.rows) + 1


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class BoardRenderer:
    def __init__(self, board: GaltonBoard, use_color: bool = True, utf8: bool = True):
        self.board = board
        self.use_color = use_color
        self.glyphs = GLYPHS_UTF8 if utf8 else GLYPHS_ASCII

    def render(self, balls: List[Ball], overlay_curve: bool = True) -> str:
        b = self.board
        w, h = b.width, b.height
        # build a canvas of characters
        canvas: List[List[str]] = [[" "] * w for _ in range(h)]

        # grid dots in peg zone
        for r in range(b.rows):
            y = b.pixel_y_of_row(r)
            if 0 <= y < h:
                for c in range(r + 1):
                    col = c  # peg column index 0..r
                    # peg x position: centered
                    px = self._peg_x(r, c)
                    if 0 <= px < w:
                        canvas[y][px] = self.glyphs["peg"]

        # balls
        for ball in balls:
            x = int(round(ball.x))
            y = int(round(ball.y))
            if 0 <= x < w and 0 <= y < h:
                canvas[y][x] = self._c(self.glyphs["ball"], YELLOW)

        # bins / histogram at bottom
        bin_top = b.bin_zone_top
        if bin_top < h:
            max_count = max(b.bins) if b.bins else 0
            bin_height = h - bin_top
            for i, count in enumerate(b.bins):
                bx = self._bin_x(i)
                if bx is None or bx >= w:
                    continue
                fill = 0
                if max_count > 0:
                    fill = int(round((count / max_count) * bin_height))
                for yy in range(bin_height):
                    cy = h - 1 - yy
                    if cy < bin_top:
                        break
                    if yy < fill:
                        canvas[cy][bx] = self._c(self.glyphs["bar"], GREEN)
                # bin floor label
                if 0 <= h - 1 < h:
                    pass

        # bin walls (drawn before curve so curve can fill between them)
        for i in range(b.num_bins + 1):
            bx = self._bin_wall_x(i)
            if bx is not None and 0 <= bx < w:
                for yy in range(bin_top, h):
                    if 0 <= yy < h:
                        canvas[yy][bx] = self._c(self.glyphs["bin_wall"], DIM)

        # bin floor
        if bin_top - 1 >= 0 and bin_top - 1 < h:
            for x in range(w):
                canvas[bin_top - 1][x] = self._c(self.glyphs["bin_floor"], DIM)

        # normal curve overlay (drawn last so it's visible on top of bars/walls)
        if overlay_curve and b.stats.n > 5 and b.stats.variance > 0:
            self._draw_curve(canvas, bin_top)

        lines = ["".join(row) for row in canvas]
        return "\n".join(lines)

    # -- curve overlay ------------------------------------------------------

    def _draw_curve(self, canvas, bin_top: int) -> None:
        b = self.board
        h = b.height
        max_count = max(b.bins) if b.bins else 1
        bin_height = h - bin_top
        if bin_height <= 0:
            return
        mu = b.stats.mean
        sigma = b.stats.std
        if sigma <= 0:
            return
        for i in range(b.num_bins):
            bx = self._bin_x(i)
            if bx is None or bx >= b.width:
                continue
            # expected count (un-normalized to max_count)
            z = (i - mu) / sigma
            pdf = math.exp(-0.5 * z * z) / (sigma * math.sqrt(2 * math.pi))
            # peak of pdf is at z=0 => 1/(sigma*sqrt(2pi))
            peak = 1.0 / (sigma * math.sqrt(2 * math.pi))
            ratio = pdf / peak if peak > 0 else 0
            fill = int(round(ratio * bin_height))
            for yy in range(fill):
                cy = h - 1 - yy
                if cy < bin_top:
                    break
                # Only fill empty cells; preserve bars, walls, and floor
                if canvas[cy][bx] == " ":
                    canvas[cy][bx] = self._c(self.glyphs["curve"], MAGENTA)

    # -- coordinate helpers --------------------------------------------------

    def _peg_x(self, row: int, col_index: int) -> int:
        b = self.board
        # pegs for row r: columns 0..r, but visually centered.
        # column position (in board col units) = col_index + (rows - row)/2 ? 
        # Actually our ball.col is in [0, rows]; peg at (row, c) sits at col = c.
        # But to make the triangle centered, the top peg row (0) has 1 peg at center.
        # We'll map: peg col_in_units = col_index + (rows - row) / 2
        col_units = col_index + (b.rows - row) / 2.0
        return int(round(b._col_to_x(col_units)))

    def _bin_x(self, i: int) -> Optional[int]:
        b = self.board
        # Bin i is centered at column position i (in board col units [0, rows]).
        # The bottom peg row is at row=rows with pegs at col 0..rows; bins sit
        # between them, so bin i's center is at col_units = i.
        return int(round(b._col_to_x(float(i))))

    def _bin_wall_x(self, i: int) -> Optional[int]:
        b = self.board
        if i < 0 or i > b.num_bins:
            return None
        col_units = i - 0.5
        return int(round(b._col_to_x(col_units)))

    def _c(self, text: str, code: str) -> str:
        return _color(text, code, self.use_color)


# ---------------------------------------------------------------------------
# Statistics line
# ---------------------------------------------------------------------------

def stats_line(board: GaltonBoard, use_color: bool = True) -> str:
    s = board.stats
    parts = [
        f"balls={s.n}",
        f"mean={s.mean:.3f}",
        f"std={s.std:.3f}",
        f"var={s.variance:.3f}",
        f"skew={s.skewness:.3f}",
        f"kurt={s.kurtosis:.3f}",
        f"min={int(s.min_val) if s.n else 0}",
        f"max={int(s.max_val) if s.n else 0}",
    ]
    line = "  ".join(parts)
    return _color(line, CYAN, use_color)


# ---------------------------------------------------------------------------
# Keyboard input (non-blocking) — POSIX
# ---------------------------------------------------------------------------

class _RawInput:
    def __enter__(self):
        if not _POSIX or not sys.stdin.isatty() or termios is None:
            self.fd = None
            return self
        self.fd = sys.stdin.fileno()
        self.old = termios.tcgetattr(self.fd)  # type: ignore[union-attr]
        try:
            tty.setcbreak(self.fd)  # type: ignore[union-attr]
        except Exception:
            self.fd = None
        return self

    def __exit__(self, *exc):
        if self.fd is not None and termios is not None:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)  # type: ignore[union-attr]
            except Exception:
                pass

    def get_key(self, timeout: float = 0.0) -> Optional[str]:
        if self.fd is None or select is None:
            return None
        r, _, _ = select.select([sys.stdin], [], [], timeout)  # type: ignore[union-attr]
        if not r:
            return None
        ch = sys.stdin.read(1)
        return ch


# ---------------------------------------------------------------------------
# Simulation driver
# ---------------------------------------------------------------------------

def run_batch(board: GaltonBoard, num_balls: int, renderer: BoardRenderer,
              rate: float = 30.0, frames: bool = True,
              overlay_curve: bool = True) -> None:
    """Drop balls in rapid succession with light animation."""
    balls: List[Ball] = []
    per_frame = max(1, int(rate * 0.05))
    dropped = 0
    term_clear = "\033[H\033[2J" if renderer.use_color else ""
    while dropped < num_balls or balls:
        # spawn
        spawn = min(per_frame, num_balls - dropped)
        for _ in range(spawn):
            balls.append(board.drop_ball())
            dropped += 1
        # advance all balls one step
        still: List[Ball] = []
        for ball in balls:
            board.step_ball(ball)
            if not ball.done:
                still.append(ball)
        balls = still
        if frames:
            sys.stdout.write(term_clear)
            sys.stdout.write(renderer.render(balls, overlay_curve=overlay_curve))
            sys.stdout.write("\n")
            sys.stdout.write(stats_line(board, renderer.use_color) + "\n")
            sys.stdout.write(f"dropped {dropped}/{num_balls}  active={len(balls)}\n")
            sys.stdout.flush()
            time.sleep(0.05)
    if frames:
        sys.stdout.write(term_clear)
        sys.stdout.write(renderer.render([], overlay_curve=overlay_curve))
        sys.stdout.write("\n")
        sys.stdout.write(stats_line(board, renderer.use_color) + "\n")
        sys.stdout.flush()


def run_static(board: GaltonBoard, num_balls: int, renderer: BoardRenderer,
               overlay_curve: bool = True) -> None:
    """Drop all balls with no animation; just compute then render final."""
    for _ in range(num_balls):
        ball = board.drop_ball()
        while not ball.done:
            board.step_ball(ball)
    renderer.board = board
    print(renderer.render([], overlay_curve=overlay_curve))
    print()
    print(stats_line(board, renderer.use_color))


def run_interactive(board: GaltonBoard, renderer: BoardRenderer,
                    rate: float = 5.0, auto_balls: int = 0,
                    overlay_curve: bool = True) -> None:
    """Interactive animated mode with keyboard controls."""
    balls: List[Ball] = []
    drop_rate = rate  # balls per second
    last_drop = 0.0
    batch_mode = auto_balls > 0
    remaining_auto = auto_balls
    term_clear = "\033[H\033[2J" if renderer.use_color else ""
    hide_cursor = "\033[?25l" if renderer.use_color else ""
    show_cursor = "\033[?25h" if renderer.use_color else ""

    with _RawInput() as inp:
        try:
            print(hide_cursor, end="")
            running = True
            while running:
                now = time.time()
                # handle input
                key = inp.get_key(timeout=0.02)
                if key is not None:
                    if key in ("q", "\x03"):
                        running = False
                    elif key == " ":
                        balls.append(board.drop_ball(
                            start_col=board.rng.uniform(0, board.rows)))
                    elif key in ("\r", "\n"):
                        balls.append(board.drop_ball())
                    elif key == "b":
                        batch_mode = not batch_mode
                    elif key in ("+", "="):
                        drop_rate = min(200, drop_rate + 1)
                    elif key == "-":
                        drop_rate = max(1, drop_rate - 1)
                    elif key == "c":
                        board.bins = [0] * board.num_bins
                        board.stats = RunningStats()
                        board.total_dropped = 0
                        balls.clear()
                    elif key == "r":
                        board.bins = [0] * board.num_bins
                        board.stats = RunningStats()
                        board.total_dropped = 0
                        balls.clear()
                        remaining_auto = 0
                        batch_mode = False

                # auto-drop in batch mode
                if batch_mode:
                    interval = 1.0 / drop_rate if drop_rate > 0 else 1.0
                    if now - last_drop >= interval:
                        if remaining_auto > 0:
                            balls.append(board.drop_ball(
                                start_col=board.rng.uniform(0, board.rows)))
                            remaining_auto -= 1
                            last_drop = now
                        elif auto_balls == 0:
                            balls.append(board.drop_ball(
                                start_col=board.rng.uniform(0, board.rows)))
                            last_drop = now

                # advance balls
                still: List[Ball] = []
                for ball in balls:
                    board.step_ball(ball)
                    if not ball.done:
                        still.append(ball)
                balls = still

                # render
                sys.stdout.write(term_clear)
                sys.stdout.write(renderer.render(balls, overlay_curve=overlay_curve))
                sys.stdout.write("\n")
                sys.stdout.write(stats_line(board, renderer.use_color) + "\n")
                ctrl = ("SPACE drop  ENTER center  b batch  +/- rate  "
                        "c clear  r reset  q quit")
                sys.stdout.write(_color(ctrl, DIM, renderer.use_color) + "\n")
                sys.stdout.write(
                    f"rate={drop_rate:.0f}/s  active={len(balls)}  "
                    f"batch={'ON' if batch_mode else 'OFF'}\n")
                sys.stdout.flush()
                time.sleep(0.03)

                # auto-exit if batch finished and no balls remain
                if batch_mode and auto_balls > 0 and remaining_auto == 0 and not balls:
                    running = False
        finally:
            print(show_cursor, end="")

    # final render
    sys.stdout.write(term_clear)
    sys.stdout.write(renderer.render([], overlay_curve=overlay_curve))
    sys.stdout.write("\n")
    print(stats_line(board, renderer.use_color))


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_csv(board: GaltonBoard, path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bin", "count", "expected_normal"])
        mu = board.stats.mean
        sigma = board.stats.std
        total = board.stats.n
        for i, count in enumerate(board.bins):
            expected = 0.0
            if sigma > 0 and total > 0:
                z = (i - mu) / sigma
                pdf = math.exp(-0.5 * z * z) / (sigma * math.sqrt(2 * math.pi))
                expected = pdf * total
            w.writerow([i, count, f"{expected:.3f}"])


def export_json(board: GaltonBoard, path: str) -> None:
    mu = board.stats.mean
    sigma = board.stats.std
    total = board.stats.n
    bins_out = []
    for i, count in enumerate(board.bins):
        expected = 0.0
        if sigma > 0 and total > 0:
            z = (i - mu) / sigma
            pdf = math.exp(-0.5 * z * z) / (sigma * math.sqrt(2 * math.pi))
            expected = pdf * total
        bins_out.append({"bin": i, "count": count,
                         "expected_normal": round(expected, 3)})
    data = {
        "rows": board.rows,
        "num_bins": board.num_bins,
        "total_dropped": board.total_dropped,
        "bins": bins_out,
        "stats": {
            "n": board.stats.n,
            "mean": round(board.stats.mean, 4),
            "std": round(board.stats.std, 4),
            "variance": round(board.stats.variance, 4),
            "skewness": round(board.stats.skewness, 4),
            "kurtosis": round(board.stats.kurtosis, 4),
            "min": int(board.stats.min_val) if board.stats.n else 0,
            "max": int(board.stats.max_val) if board.stats.n else 0,
        },
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _approx(a, b, tol=1e-6):
    return abs(a - b) <= tol


def run_tests() -> int:
    failures = 0
    tests = []

    def check(name, cond):
        nonlocal failures
        tests.append(name)
        if not cond:
            failures += 1
            print(f"  FAIL: {name}")
        else:
            print(f"  ok:   {name}")

    print("Running self-tests...")

    # 1. Bin count
    b = GaltonBoard(rows=10)
    check("num_bins == rows+1", b.num_bins == 11)

    # 2. Drop deterministic with seeded rng (all-left path)
    b = GaltonBoard(rows=5, rng=random.Random(0))
    ball = b.drop_ball()
    # force all-left by monkey-patching rng
    b.rng = random.Random(0)
    # We'll just verify a ball eventually settles
    steps = 0
    while not ball.done and steps < 100:
        b.step_ball(ball)
        steps += 1
    check("ball settles within steps", ball.done)
    check("bin_index in range", 0 <= ball.bin_index < b.num_bins)

    # 3. Bin index increments
    b2 = GaltonBoard(rows=4, rng=random.Random(42))
    before = sum(b2.bins)
    ball2 = b2.drop_ball()
    while not ball2.done:
        b2.step_ball(ball2)
    check("bin count increased by 1", sum(b2.bins) == before + 1)

    # 4. RunningStats basic
    rs = RunningStats()
    for x in [1, 2, 3, 4, 5]:
        rs.add(x)
    check("mean of 1..5 == 3.0", _approx(rs.mean, 3.0))
    check("variance of 1..5 == 2.0", _approx(rs.variance, 2.0))
    check("n == 5", rs.n == 5)

    # 5. RunningStats min/max
    check("min == 1", rs.min_val == 1)
    check("max == 5", rs.max_val == 5)

    # 6. col_to_x bounds
    b3 = GaltonBoard(rows=6, width=40)
    x0 = b3._col_to_x(0)
    x6 = b3._col_to_x(6)
    check("col 0 >= margin", x0 >= 2)
    check("col rows <= width - margin", x6 <= 38)

    # 7. Large drop converges near center (law of large numbers)
    b4 = GaltonBoard(rows=12, rng=random.Random(7))
    for _ in range(5000):
        ball4 = b4.drop_ball()
        while not ball4.done:
            b4.step_ball(ball4)
    check("mean near center (6 +/- 0.5)", abs(b4.stats.mean - 6.0) < 0.5)
    check("std near sqrt(rows/4) ~ 1.732", abs(b4.stats.std - math.sqrt(12 / 4)) < 0.3)

    # 8. Export CSV round-trip
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as tf:
        csv_path = tf.name
    export_csv(b4, csv_path)
    with open(csv_path) as f:
        reader = csv.reader(f)
        rows = list(reader)
    check("csv has header + bins rows", len(rows) == b4.num_bins + 1)
    check("csv header correct", rows[0] == ["bin", "count", "expected_normal"])
    os.unlink(csv_path)

    # 9. Export JSON structure
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tf:
        json_path = tf.name
    export_json(b4, json_path)
    with open(json_path) as f:
        data = json.load(f)
    check("json has bins array", isinstance(data.get("bins"), list))
    check("json bins length matches", len(data["bins"]) == b4.num_bins)
    check("json stats present", "stats" in data and "mean" in data["stats"])
    os.unlink(json_path)

    # 10. Renderer produces non-empty string
    b5 = GaltonBoard(rows=6, width=40, height=16)
    ball5 = b5.drop_ball()
    b5.step_ball(ball5)
    r = BoardRenderer(b5, use_color=False, utf8=False)
    out = r.render([ball5])
    check("render output non-empty", len(out) > 0)
    check("render has peg glyph", "." in out)

    # 11. Renderer with color includes ANSI codes
    r2 = BoardRenderer(b5, use_color=True, utf8=True)
    out2 = r2.render([ball5])
    check("color render contains escape", "\033[" in out2)

    # 12. skewness/kurtosis for symmetric distribution ~0
    check("skewness near 0", abs(b4.stats.skewness) < 0.3)
    # excess kurtosis for binomial ~ -1/(np) ... small-ish; just check finite
    check("kurtosis finite", math.isfinite(b4.stats.kurtosis))

    # 13. Drop clamps start_col
    b6 = GaltonBoard(rows=4)
    ball6 = b6.drop_ball(start_col=100)
    check("start_col clamped", ball6.col <= 4)
    ball6b = b6.drop_ball(start_col=-10)
    check("negative start_col clamped", ball6b.col >= 0)

    # 14. Zero-row board doesn't crash
    b7 = GaltonBoard(rows=0)
    ball7 = b7.drop_ball()
    while not ball7.done:
        b7.step_ball(ball7)
    check("zero-row board settles", ball7.done)
    check("zero-row has 1 bin", b7.num_bins == 1)

    # 15. Batch mode drops correct count
    b8 = GaltonBoard(rows=6, rng=random.Random(99))
    for _ in range(100):
        ball8 = b8.drop_ball()
        while not ball8.done:
            b8.step_ball(ball8)
    check("batch dropped 100", b8.stats.n == 100)

    # 16. --no-curve overlay actually disables the curve (regression for dead flag)
    b9 = GaltonBoard(rows=8, rng=random.Random(1), width=70, height=24)
    for _ in range(200):  # few balls so curve is visible above bars
        ball9 = b9.drop_ball()
        while not ball9.done:
            b9.step_ball(ball9)
    r9 = BoardRenderer(b9, use_color=False, utf8=False)
    with_curve = r9.render([], overlay_curve=True)
    without_curve = r9.render([], overlay_curve=False)
    check("overlay=True produces curve glyph", "%" in with_curve)
    check("overlay=False omits curve glyph", "%" not in without_curve)

    # 17. _bin_x returns integer (no no-op expression artifacts)
    bx0 = r9._bin_x(0)
    bx_mid = r9._bin_x(b9.num_bins // 2)
    check("_bin_x(0) is int", isinstance(bx0, int))
    check("_bin_x(mid) is int", isinstance(bx_mid, int))
    check("_bin_x(0) < _bin_x(mid)", (bx0 or 0) < (bx_mid or 0))

    # 18. CLI rejects negative --balls (regression for silent 1000 default)
    rc = main(["--static", "--balls", "-5", "--rows", "4", "--no-color", "--ascii"])
    check("negative --balls rejected", rc == 2)

    # 19. CLI rejects negative --rate
    rc2 = main(["--static", "--rate", "-1", "--rows", "4", "--no-color", "--ascii"])
    check("negative --rate rejected", rc2 == 2)

    # 20. CLI export to nonexistent directory gives error, not crash
    import tempfile
    bad_path = os.path.join(tempfile.gettempdir(), "nonexistent_dir_xyz", "out.csv")
    rc3 = main(["--static", "--rows", "4", "--balls", "10",
                "--no-color", "--ascii", "--export", bad_path])
    check("export to bad dir returns error code", rc3 == 1)

    # 21. CLI --version prints version
    import io as _io, contextlib
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc4 = main(["--version"])
    check("--version returns 0", rc4 == 0)
    check("--version prints version", __version__ in buf.getvalue())

    # 22. Non-tty interactive mode is rejected (no infinite loop)
    import io as _io2
    old_stdin = sys.stdin
    try:
        sys.stdin = _io2.StringIO("")  # not a tty
        rc5 = main(["--rows", "4"])
    finally:
        sys.stdin = old_stdin
    check("non-tty interactive rejected", rc5 == 2)

    # 23. --no-curve flag wired through CLI static mode
    buf2 = _io.StringIO()
    with contextlib.redirect_stdout(buf2):
        main(["--static", "--rows", "8", "--balls", "2000",
              "--no-color", "--ascii", "--no-curve", "--seed", "1"])
    check("--no-curve CLI omits curve glyph", "%" not in buf2.getvalue())

    print(f"\n{len(tests) - failures}/{len(tests)} passed.")
    if failures:
        print(f"{failures} FAILED")
    return failures


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _detect_utf8() -> bool:
    enc = (sys.stdout.encoding or "").lower()
    return "utf" in enc


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="galton_board",
        description="Terminal ASCII Galton Board (bean machine) simulator.",
    )
    parser.add_argument("--rows", type=int, default=12,
                        help="number of peg rows (default 12)")
    parser.add_argument("--balls", type=int, default=0,
                        help="number of balls to drop (interactive if 0)")
    parser.add_argument("--width", type=int, default=70,
                        help="board width in characters (min 20, default 70)")
    parser.add_argument("--height", type=int, default=24,
                        help="board height in characters (min 8, default 24)")
    parser.add_argument("--rate", type=float, default=8.0,
                        help="drop rate in balls/second (batch/interactive)")
    parser.add_argument("--seed", type=int, default=None,
                        help="random seed for reproducible runs")
    parser.add_argument("--batch", action="store_true",
                        help="animated batch mode (drops --balls quickly)")
    parser.add_argument("--static", action="store_true",
                        help="compute without animation, render final state")
    parser.add_argument("--no-color", action="store_true",
                        help="disable ANSI color output")
    parser.add_argument("--ascii", action="store_true",
                        help="use ASCII-only glyphs")
    parser.add_argument("--export", type=str, default=None,
                        help="export final histogram to CSV/JSON (by extension)")
    parser.add_argument("--no-curve", action="store_true",
                        help="disable normal-curve overlay")
    parser.add_argument("--test", action="store_true",
                        help="run self-tests and exit")
    parser.add_argument("--version", action="store_true",
                        help="print version and exit")
    args = parser.parse_args(argv)

    if args.version:
        print(f"galton_board {__version__}")
        return 0

    if args.test:
        return run_tests()

    # validation
    if args.rows < 0:
        print("error: --rows must be >= 0", file=sys.stderr)
        return 2
    if args.balls < 0:
        print("error: --balls must be >= 0", file=sys.stderr)
        return 2
    if args.rate < 0:
        print("error: --rate must be >= 0", file=sys.stderr)
        return 2
    if args.width < 20 or args.height < 8:
        print("error: --width >= 20 and --height >= 8 required",
              file=sys.stderr)
        return 2

    rng = random.Random(args.seed)
    board = GaltonBoard(rows=args.rows, rng=rng,
                        width=args.width, height=args.height)
    use_color = not args.no_color and sys.stdout.isatty()
    utf8 = not args.ascii and _detect_utf8()
    renderer = BoardRenderer(board, use_color=use_color, utf8=utf8)
    show_curve = not args.no_curve

    # decide mode
    if args.static:
        run_static(board, max(1, args.balls if args.balls > 0 else 1000),
                   renderer, overlay_curve=show_curve)
    elif args.batch or args.balls > 0:
        n = max(1, args.balls if args.balls > 0 else 1000)
        run_batch(board, n, renderer, rate=max(1.0, args.rate),
                  overlay_curve=show_curve)
    else:
        # Interactive mode requires a TTY for keyboard input.
        if not sys.stdin.isatty():
            print("error: interactive mode requires a TTY for keyboard input.\n"
                  "       Use --static or --batch with --balls N for non-interactive runs.",
                  file=sys.stderr)
            return 2
        run_interactive(board, renderer, rate=max(1.0, args.rate),
                        overlay_curve=show_curve)

    if args.export:
        try:
            if args.export.endswith(".json"):
                export_json(board, args.export)
            else:
                export_csv(board, args.export)
        except OSError as exc:
            print(f"error: could not write export file '{args.export}': {exc}",
                  file=sys.stderr)
            return 1
        print(f"exported histogram to {args.export}")

    return 0


if __name__ == "__main__":
    sys.exit(main())