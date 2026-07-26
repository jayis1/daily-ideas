#!/usr/bin/env python3
"""
Terminal Aurora Borealis Simulator
===================================
Procedurally animates a northern-lights display in the terminal using
value-noise curtains, a twinkling starfield, a mountain silhouette, a
phased moon, occasional shooting stars, and an aurora reflection on a
still lake.

Controls (when run interactively):
    q / Esc   quit
    + / =     speed up
    - / _     slow down
    r         toggle reduced-motion mode (calmer, slower, no flicker)
    c         cycle color palette (green, violet, sunset, rainbow, ice,
              magnetic)
    m         toggle moon
    s         toggle shooting stars
    l         toggle lake reflection
    h         toggle help overlay
    space     pause/resume
"""

from __future__ import annotations

import argparse
import math
import os
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from typing import List, Tuple

__version__ = "1.1.1"

# ---------------------------------------------------------------------------
# Terminal helpers (raw mode + ANSI truecolor)
# ---------------------------------------------------------------------------

RESET = "\033[0m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR = "\033[2J"
HOME = "\033[H"
CLEAR_LINE = "\033[2K"

# Characters used to paint the aurora curtains. Densest first.
AURORA_CHARS = " .:-=+*#%@"
STAR_CHARS = ".+*"


def move_to(row: int, col: int) -> str:
    return f"\033[{row + 1};{col + 1}H"


# ---------------------------------------------------------------------------
# Value noise (smooth, tileable-friendly 1D/2D)
# ---------------------------------------------------------------------------

def smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def value_noise_1d(seed_grid: List[float], x: float) -> float:
    """1D smooth value noise sampled at floating-point x over a fixed grid.

    Returns 0.0 for an empty grid (avoids ZeroDivisionError) or a non-finite
    ``x`` (avoids OverflowError from ``int(math.floor(inf))``), so callers can
    safely pass degenerate grids.
    """
    n = len(seed_grid)
    if n == 0 or not math.isfinite(x):
        return 0.0
    i0 = int(math.floor(x)) % n
    i1 = (i0 + 1) % n
    t = smoothstep(x - math.floor(x))
    return seed_grid[i0] * (1.0 - t) + seed_grid[i1] * t


def value_noise_2d(grid: List[List[float]], x: float, y: float) -> float:
    """2D smooth value noise on a wrapped grid.

    Returns 0.0 for empty/zero-width grids (avoids ZeroDivisionError) or
    non-finite coordinates (avoids OverflowError).
    """
    h = len(grid)
    if h == 0:
        return 0.0
    w = len(grid[0]) if h else 0
    if w == 0 or not (math.isfinite(x) and math.isfinite(y)):
        return 0.0
    xi = math.floor(x)
    yi = math.floor(y)
    fx = smoothstep(x - xi)
    fy = smoothstep(y - yi)
    i0, j0 = xi % w, yi % h
    i1, j1 = (i0 + 1) % w, (j0 + 1) % h
    v00 = grid[j0][i0]
    v10 = grid[j0][i1]
    v01 = grid[j1][i0]
    v11 = grid[j1][i1]
    top = v00 * (1.0 - fx) + v10 * fx
    bot = v01 * (1.0 - fx) + v11 * fx
    return top * (1.0 - fy) + bot * fy


def fractal_noise_1d(seed_grid: List[float], x: float, octaves: int = 4,
                     persistence: float = 0.5, lacunarity: float = 2.0) -> float:
    if octaves <= 0 or not seed_grid:
        return 0.0
    total = 0.0
    amp = 1.0
    freq = 1.0
    norm = 0.0
    for _ in range(octaves):
        total += value_noise_1d(seed_grid, x * freq) * amp
        norm += amp
        amp *= persistence
        freq *= lacunarity
    return total / norm if norm else 0.0


# ---------------------------------------------------------------------------
# Color palettes
# ---------------------------------------------------------------------------

def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


def rgb(r: float, g: float, b: float) -> Tuple[int, int, int]:
    return (int(clamp(r) * 255), int(clamp(g) * 255), int(clamp(b) * 255))


def truecolor_fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


PALETTES = {
    # name: list of (bottom, mid, top) RGB stops in 0..1
    "green": [
        (0.0, (0.02, 0.18, 0.10)),
        (0.45, (0.10, 0.95, 0.45)),
        (0.75, (0.55, 1.00, 0.75)),
        (1.0, (0.85, 0.95, 1.00)),
    ],
    "violet": [
        (0.0, (0.10, 0.02, 0.20)),
        (0.45, (0.55, 0.15, 0.95)),
        (0.75, (0.85, 0.45, 1.00)),
        (1.0, (0.95, 0.90, 1.00)),
    ],
    "sunset": [
        (0.0, (0.20, 0.03, 0.05)),
        (0.45, (1.00, 0.35, 0.15)),
        (0.75, (1.00, 0.75, 0.30)),
        (1.0, (1.00, 0.95, 0.85)),
    ],
    "rainbow": [
        (0.0, (0.05, 0.05, 0.20)),
        (0.30, (0.10, 0.90, 0.50)),
        (0.55, (0.30, 0.50, 1.00)),
        (0.80, (0.95, 0.40, 0.85)),
        (1.0, (1.00, 0.95, 1.00)),
    ],
    "ice": [
        (0.0, (0.02, 0.10, 0.20)),
        (0.45, (0.30, 0.75, 1.00)),
        (0.75, (0.75, 0.95, 1.00)),
        (1.0, (1.00, 1.00, 1.00)),
    ],
    # "magnetic" — solar storm: pink/teal with a hot magenta crown.
    "magnetic": [
        (0.0, (0.05, 0.02, 0.15)),
        (0.35, (0.15, 0.85, 0.75)),
        (0.60, (0.95, 0.25, 0.55)),
        (0.85, (1.00, 0.55, 0.85)),
        (1.0, (1.00, 0.95, 1.00)),
    ],
}

PALETTE_ORDER = ["green", "violet", "sunset", "rainbow", "ice", "magnetic"]


def palette_color(name: str, t: float) -> Tuple[int, int, int]:
    stops = PALETTES[name]
    t = clamp(t)
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            local = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return rgb(*lerp_color(c0, c1, local))
    c = stops[-1][1]
    return rgb(*c)


# ---------------------------------------------------------------------------
# Stars
# ---------------------------------------------------------------------------

@dataclass
class Star:
    x: int
    y: int
    brightness: float
    twinkle_phase: float
    twinkle_speed: float
    char: str


def make_stars(width: int, sky_height: int, density: float, rng: random.Random) -> List[Star]:
    stars: List[Star] = []
    count = int(width * sky_height * density)
    for _ in range(count):
        x = rng.randint(0, max(0, width - 1))
        y = rng.randint(0, max(0, sky_height - 1))
        stars.append(Star(
            x=x, y=y,
            brightness=rng.uniform(0.25, 1.0),
            twinkle_phase=rng.uniform(0.0, math.tau),
            twinkle_speed=rng.uniform(0.4, 2.0),
            char=rng.choice(STAR_CHARS),
        ))
    return stars


# ---------------------------------------------------------------------------
# Shooting stars (meteors)
# ---------------------------------------------------------------------------

@dataclass
class ShootingStar:
    """A meteor that streaks diagonally across the sky for a short time."""
    x: float          # current column position
    y: float          # current row position
    vx: float         # horizontal velocity (columns per second)
    vy: float         # vertical velocity (rows per second)
    life: float        # remaining seconds of visibility
    max_life: float   # initial lifetime (for fade)
    length: float     # tail length in characters


def maybe_spawn_shooting_star(state: "State", rng: random.Random) -> None:
    """With low probability, spawn a shooting star if none are very active."""
    # Keep at most a couple on screen; only spawn occasionally.
    if any(ss.life > 0 for ss in state.shooting_stars):
        # one at a time is plenty for calm; allow rare second
        active = sum(1 for ss in state.shooting_stars if ss.life > 0)
        if active >= 2:
            return
    # spawn rate scales subtly with speed; capped so it stays rare
    if rng.random() > 0.012:
        return
    w = state.width
    sky_h = max(4, int(state.height * 0.62))
    # start near top, anywhere across the upper sky
    sx = rng.uniform(0, w - 1)
    sy = rng.uniform(0, max(1, sky_h * 0.35))
    # diagonal down-right or down-left
    direction = 1 if rng.random() < 0.5 else -1
    speed = rng.uniform(18.0, 30.0)
    vx = direction * speed
    vy = speed * rng.uniform(0.3, 0.6)
    life = rng.uniform(0.7, 1.4)
    state.shooting_stars.append(ShootingStar(
        x=sx, y=sy, vx=vx, vy=vy,
        life=life, max_life=life, length=rng.uniform(4.0, 8.0),
    ))


def update_shooting_stars(state: "State", dt: float) -> None:
    """Advance meteor positions and decay lifetimes."""
    for ss in state.shooting_stars:
        if ss.life <= 0:
            continue
        ss.x += ss.vx * dt
        ss.y += ss.vy * dt
        ss.life -= dt
    # prune dead and off-screen
    state.shooting_stars[:] = [
        ss for ss in state.shooting_stars
        if ss.life > 0
        and -10 < ss.x < state.width + 10
        and ss.y < state.height + 5
    ]


# ---------------------------------------------------------------------------
# Moon (with phase)
# ---------------------------------------------------------------------------

@dataclass
class Moon:
    """A simple phased moon drawn in the upper sky."""
    cx: float           # column center
    cy: float           # row center
    radius: float       # radius in character cells
    phase: float        # 0.0=new, 0.25=first quarter, 0.5=full, 0.75=last quarter
    color: Tuple[int, int, int] = (230, 232, 220)


def make_moon(width: int, sky_height: int, seed: int) -> Moon:
    rng = random.Random(seed + 3571)
    cx = rng.uniform(width * 0.15, width * 0.85)
    cy = rng.uniform(sky_height * 0.10, sky_height * 0.35)
    radius = rng.uniform(2.5, 4.0)
    phase = rng.choice([0.12, 0.25, 0.5, 0.75, 0.88])
    return Moon(cx=cx, cy=cy, radius=radius, phase=phase)


# ---------------------------------------------------------------------------
# Mountain silhouette (procedural, fixed for a run)
# ---------------------------------------------------------------------------

def make_mountains(width: int, base_row: int, seed: int, n_ranges: int = 3) -> List[int]:
    """Return a list of `width` heights (rows from top of screen)."""
    rng = random.Random(seed)
    heights = [0.0] * width
    for r in range(n_ranges):
        amplitude = (r + 1) * 2.2
        wavelength = rng.uniform(width * 0.25, width * 0.8)
        phase = rng.uniform(0.0, math.tau)
        grid = [rng.random() for _ in range(64)]
        for x in range(width):
            n = fractal_noise_1d(grid, x / wavelength + phase, octaves=3)
            heights[x] += (n - 0.5) * amplitude
    # normalize and shift to base
    out = []
    for x in range(width):
        h = base_row - heights[x] - 1
        out.append(int(h))
    return out


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

@dataclass
class State:
    width: int
    height: int
    time: float = 0.0
    speed: float = 1.0
    paused: bool = False
    reduced_motion: bool = False
    palette_index: int = 0
    show_help: bool = False
    palette_name: str = "green"
    seed: int = 0
    noise_grid: List[List[float]] = field(default_factory=list)
    curtain_seeds: List[float] = field(default_factory=list)
    stars: List[Star] = field(default_factory=list)
    mountains: List[int] = field(default_factory=list)
    last_size: Tuple[int, int] = (0, 0)
    frame: int = 0
    # --- new feature state ---
    shooting_stars: List[ShootingStar] = field(default_factory=list)
    moon: Moon | None = None
    show_moon: bool = True
    show_stars: bool = True          # starfield + shooting stars
    show_mountains: bool = True
    show_lake: bool = True           # aurora reflection on still water
    meteor_rng: random.Random = field(default_factory=lambda: random.Random(0))


def init_state(width: int, height: int, seed: int, palette: str,
               show_moon: bool = True, show_stars: bool = True,
               show_mountains: bool = True, show_lake: bool = True) -> State:
    rng = random.Random(seed)
    grid = [[rng.random() for _ in range(32)] for _ in range(32)]
    curtain_seeds = [rng.random() for _ in range(256)]
    sky_height = max(4, int(height * 0.62))
    stars = make_stars(width, sky_height, density=0.012, rng=rng)
    base_row = height - 3
    mountains = make_mountains(width, base_row, seed)
    pal_name = palette if palette in PALETTES else "green"
    pal_idx = PALETTE_ORDER.index(pal_name) if pal_name in PALETTE_ORDER else 0
    moon = make_moon(width, sky_height, seed)
    return State(
        width=width, height=height, seed=seed,
        palette_name=pal_name, palette_index=pal_idx,
        noise_grid=grid, curtain_seeds=curtain_seeds,
        stars=stars, mountains=mountains,
        moon=moon,
        show_moon=show_moon, show_stars=show_stars,
        show_mountains=show_mountains, show_lake=show_lake,
        meteor_rng=random.Random(seed ^ 0x9E37),
    )


def reinit_for_size(state: State, width: int, height: int) -> None:
    if (width, height) == state.last_size:
        return
    rng = random.Random(state.seed + width + height * 7919)
    state.width = width
    state.height = height
    sky_height = max(4, int(height * 0.62))
    state.stars = make_stars(width, sky_height, density=0.012, rng=rng)
    state.mountains = make_mountains(width, height - 3, state.seed)
    state.moon = make_moon(width, sky_height, state.seed)
    state.last_size = (width, height)


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def build_frame(state: State) -> str:
    """Render a single frame of the aurora scene as an ANSI-truecolor string.

    Layering order (back to front):
        night sky -> stars -> moon -> aurora curtains -> shooting stars ->
        mountain silhouette -> lake reflection (below mountains) ->
        status/help overlay (added separately by the loop).

    The function is pure: it reads only ``state`` and returns a string,
    so it is safe to call from tests or snapshot mode.
    """
    w = state.width
    h = state.height
    if w <= 0 or h <= 0:
        return ""

    # Sky occupies the upper portion of the canvas. Clamp to h so we never
    # index past the end of `rows`/`color_rows` on very short terminals
    # (height < 4 would otherwise force sky_h = 4 and overflow).
    sky_h = min(h, max(4, int(h * 0.62))) if h >= 4 else h
    # buffer: list of rows, each row a list of characters
    rows: List[List[str]] = []
    for _ in range(h):
        rows.append([" "] * w)

    color_rows: List[List[str]] = [[""] * w for _ in range(h)]

    t = state.time

    # ---- Stars (background) ----
    if state.show_stars:
        star_speed = 0.0 if state.reduced_motion else 1.0
        for s in state.stars:
            if s.y >= sky_h or s.x >= w:
                continue
            tw = math.sin(s.twinkle_phase + t * s.twinkle_speed * star_speed) * 0.5 + 0.5
            b = s.brightness * (0.55 + 0.45 * tw)
            col = rgb(b, b, b * 0.95 + 0.05)
            color_rows[s.y][s.x] = truecolor_fg(*col)
            rows[s.y][s.x] = s.char

    # ---- Moon (with phase) ----
    if state.show_moon and state.moon is not None:
        _draw_moon(state.moon, rows, color_rows, w, h)

    # ---- Aurora curtains ----
    # We compute, for each column, a vertical intensity profile and a color t.
    # Multiple layered curtains with different speeds and phases create depth.
    curtains = [
        {"freq": 0.045, "amp": 0.22, "speed": 0.30, "phase": 0.0, "yoff": 0.0,
         "brightness": 1.00, "color_t": 0.55, "y_factor": 0.40},
        {"freq": 0.080, "amp": 0.16, "speed": 0.55, "phase": 1.3, "yoff": 0.08,
         "brightness": 0.85, "color_t": 0.42, "y_factor": 0.55},
        {"freq": 0.033, "amp": 0.28, "speed": 0.18, "phase": 2.7, "yoff": -0.06,
         "brightness": 0.95, "color_t": 0.70, "y_factor": 0.30},
        {"freq": 0.120, "amp": 0.10, "speed": 0.75, "phase": 4.1, "yoff": 0.15,
         "brightness": 0.70, "color_t": 0.30, "y_factor": 0.65},
    ]

    # Vertical brightness falloff: auroras concentrate in a band.
    band_center = sky_h * 0.42
    band_height = sky_h * 0.55

    # Remember the bottom-most aurora color per column for the lake reflection.
    lake_refl: List[Tuple[int, int, int, float]] = [(0, 0, 0, 0.0)] * w

    for x in range(w):
        # base height of the curtain bottom for this column
        col_intensity = 0.0
        col_color_t = 0.0
        col_norm = 0.0
        for c in curtains:
            n = fractal_noise_1d(
                state.curtain_seeds,
                x * c["freq"] + t * c["speed"] + c["phase"],
                octaves=3,
            )
            col_intensity += n * c["brightness"]
            col_color_t += n * c["color_t"] * c["brightness"]
            col_norm += c["brightness"]
        col_intensity = col_intensity / col_norm if col_norm else 0.0
        col_color_t = col_color_t / col_norm if col_norm else 0.0

        # Vertical profile
        for y in range(sky_h):
            # distance from band center, normalized
            # curtain undulates: shift band center using column noise
            shift = (col_intensity - 0.5) * band_height * 0.5
            local_dy = (y - (band_center + shift)) / band_height
            # bell-shaped falloff
            vert = math.exp(-(local_dy * local_dy) * 2.6)
            # add vertical streaks (rays) using 2D noise
            streak = value_noise_2d(
                state.noise_grid,
                x * 0.18 + t * 0.05,
                y * 0.22 - t * 0.08,
            )
            vert *= 0.6 + 0.4 * streak
            # overall intensity
            intensity = vert * col_intensity
            if intensity < 0.05:
                continue
            # color: blend color_t with vertical position for gradient
            color_t = clamp(col_color_t * 0.6 + (1.0 - local_dy) * 0.4)
            # tint color slightly by streak
            color_t = clamp(color_t + (streak - 0.5) * 0.15)
            r, g, b = palette_color(state.palette_name, color_t)
            # darken by intensity
            k = clamp(intensity * 1.15)
            r = int(r * k)
            g = int(g * k)
            b = int(b * k)
            # character based on intensity
            ci = int(clamp(intensity) * (len(AURORA_CHARS) - 1))
            ch = AURORA_CHARS[ci]
            # only overwrite background if aurora is brighter than existing star
            # (stars are dim; aurora wins when intensity high)
            existing = rows[y][x]
            if existing == " " or intensity > 0.45:
                color_rows[y][x] = truecolor_fg(r, g, b)
                rows[y][x] = ch
            # Track the aurora glow nearest the horizon for the lake reflection.
            # We want the color/intensity just above the mountains/sky bottom.
            if y >= sky_h - 6 and intensity > lake_refl[x][3]:
                lake_refl[x] = (r, g, b, intensity)

    # ---- Shooting stars (meteors) ----
    if state.show_stars and not state.reduced_motion:
        _draw_shooting_stars(state, rows, color_rows, w, h)

    # ---- Mountain silhouette ----
    if state.show_mountains:
        _draw_mountains(state, rows, color_rows, w, h)

    # ---- Lake reflection ----
    if state.show_lake:
        _draw_lake(state, rows, color_rows, w, h, lake_refl)

    # ---- Assemble ----
    out = []
    out.append(HOME)
    for y in range(h):
        line_parts = []
        prev_color = ""
        for x in range(w):
            ch = rows[y][x]
            col = color_rows[y][x]
            if col != prev_color:
                line_parts.append(col)
                prev_color = col
            line_parts.append(ch)
        line_parts.append(RESET)
        # pad to width with spaces (clear trailing artifacts)
        out.append("".join(line_parts))
        out.append(CLEAR_LINE)
    out.append(RESET)
    return "\n".join(out)


def _draw_moon(moon: Moon, rows: List[List[str]],
               color_rows: List[List[str]], w: int, h: int) -> None:
    """Draw a phased moon using a half-light disk approximation."""
    # terminator offset: how far the light/dark boundary sits from center,
    # as a fraction of the radius. phase 0 -> -1 (new), 0.5 -> 0 (full),
    # 1.0 -> +1 (new again). We map phase in [0,1) accordingly.
    phase = moon.phase % 1.0
    # cos-style terminator
    terminator = math.cos(phase * math.tau)  # 1 at new, -1 at full
    # We render the lit side; the dark side is hidden (sky behind).
    lit_fg = truecolor_fg(*moon.color)
    rim_fg = truecolor_fg(120, 122, 130)
    r = moon.radius
    cx, cy = moon.cx, moon.cy
    for yy in range(h):
        for xx in range(w):
            dx = xx + 0.5 - cx
            dy = (yy + 0.5 - cy) * 2.0  # characters are ~2x as tall as wide
            d2 = dx * dx + dy * dy
            if d2 > r * r:
                continue
            # determine if this point is lit
            # lit fraction along x: points to the lit side of the terminator
            # We use a vertical terminator line shifted by terminator*r.
            lit_x = dx - terminator * r * 0.9
            if lit_x > 0:
                # lit
                color_rows[yy][xx] = lit_fg
                rows[yy][xx] = "O" if d2 < (r * 0.55) ** 2 else "."
            else:
                # dark side — only draw a faint rim near the edge
                if d2 > (r * 0.78) ** 2:
                    color_rows[yy][xx] = rim_fg
                    rows[yy][xx] = "."


def _draw_shooting_stars(state: State, rows: List[List[str]],
                         color_rows: List[List[str]], w: int, h: int) -> None:
    """Draw active shooting stars with fading tails."""
    for ss in state.shooting_stars:
        if ss.life <= 0:
            continue
        fade = clamp(ss.life / ss.max_life)
        # tail direction is opposite to velocity
        speed = math.hypot(ss.vx, ss.vy)
        if speed < 1e-6:
            continue
        ux, uy = ss.vx / speed, ss.vy / speed
        head_x, head_y = ss.x, ss.y
        for step in range(int(ss.length) + 1):
            tx = head_x - ux * step
            ty = head_y - uy * step
            ix, iy = int(tx), int(ty)
            if 0 <= ix < w and 0 <= iy < h:
                # fade along the tail
                seg = 1.0 - step / max(1.0, ss.length)
                b = int(255 * fade * seg * 0.9)
                if b < 20:
                    continue
                # don't overwrite mountains (drawn after) — but mountains
                # will overwrite us anyway; here we only avoid clobbering
                # bright aurora cells.
                existing = rows[iy][ix]
                if existing in (" ", "."):
                    color_rows[iy][ix] = truecolor_fg(b, b, int(b * 0.95))
                    rows[iy][ix] = "*" if step == 0 else "."


def _draw_mountains(state: State, rows: List[List[str]],
                    color_rows: List[List[str]], w: int, h: int) -> None:
    """Draw the procedural mountain ridge, overwriting the sky beneath it."""
    mtn_color = truecolor_fg(8, 10, 18)
    mtn_snow = truecolor_fg(160, 175, 200)
    for x in range(w):
        top = state.mountains[x] if x < len(state.mountains) else h - 3
        if top < 0:
            top = 0
        for y in range(top, h):
            char = " "
            col = mtn_color
            # ridge highlight: top row of mountain
            if y == top:
                # snow cap where the mountain is tall
                ridge_height = h - 3 - top
                if ridge_height > 4:
                    char = "^"
                    col = mtn_snow
                else:
                    char = "▁"
            elif y == top + 1 and (h - 3 - top) > 5:
                char = "▒"
            else:
                # body fill
                char = "▓" if (y - top) % 2 == 0 else "▒"
            color_rows[y][x] = col
            rows[y][x] = char


def _draw_lake(state: State, rows: List[List[str]],
               color_rows: List[List[str]], w: int, h: int,
               lake_refl: List[Tuple[int, int, int, float]]) -> None:
    """Paint a still lake at the bottom of the screen mirroring the aurora.

    Only the bottom few rows below the mountain base are treated as water.
    The reflection is dimmed, vertically flipped, and gently rippled by a
    slow sine so it reads as water rather than a copy of the sky.
    """
    # Water occupies the bottom rows; the mountain base sits around h-3.
    # We take the last 2 rows as the lake surface.
    water_top = max(0, h - 2)
    if water_top >= h:
        return
    # gentle ripple phase based on time
    for x in range(w):
        r, g, b, inten = lake_refl[x]
        if inten < 0.08:
            continue
        for y in range(water_top, h):
            # depth into the water
            depth = y - water_top
            # ripple: shift the column slightly with a slow sine
            ripple = math.sin(x * 0.25 + state.time * 0.6 + depth * 0.7) * 0.5
            # fade with depth
            fade = clamp(0.55 - depth * 0.22 + ripple * 0.05)
            if fade <= 0:
                continue
            rr = int(r * fade * 0.7)
            gg = int(g * fade * 0.7)
            bb = int(b * fade * 0.7)
            color_rows[y][x] = truecolor_fg(rr, gg, bb)
            # ripple character: alternates to suggest water surface
            rows[y][x] = "~" if (int(x + state.time * 2 + depth) % 3 == 0) else " "


def render_help(state: State) -> str:
    lines = [
        "Terminal Aurora Borealis Simulator",
        "",
        "  q / Esc      quit",
        "  + / =        speed up",
        "  - / _        slow down",
        "  r            toggle reduced-motion mode",
        "  c            cycle color palette",
        "  m            toggle moon",
        "  s            toggle stars & shooting stars",
        "  l            toggle lake reflection",
        "  t            toggle mountains",
        "  h            toggle this help",
        "  space        pause / resume",
        "",
        f"  palette:     {state.palette_name}",
        f"  speed:       {state.speed:.2f}x",
        f"  reduced:     {'on' if state.reduced_motion else 'off'}",
        f"  moon:        {'on' if state.show_moon else 'off'}",
        f"  stars:       {'on' if state.show_stars else 'off'}",
        f"  lake:        {'on' if state.show_lake else 'off'}",
        f"  mountains:   {'on' if state.show_mountains else 'off'}",
        f"  time:        {state.time:6.2f}s",
        "",
        "Press h to hide help.",
    ]
    maxw = max(len(l) for l in lines) + 2
    box_w = min(maxw, state.width - 2)
    start_row = max(1, (state.height - len(lines) - 2) // 2)
    start_col = max(1, (state.width - box_w) // 2)
    out = []
    # semi-transparent backdrop using block char
    for i, line in enumerate(lines):
        r = start_row + i
        c = start_col
        # draw a dim background bar
        out.append(move_to(r, c))
        out.append("\033[48;2;8;10;18m")
        padded = line[:box_w - 2].ljust(box_w - 2)
        out.append(padded)
        out.append(RESET)
    return "".join(out)


# ---------------------------------------------------------------------------
# Terminal raw input
# ---------------------------------------------------------------------------

class RawTerminal:
    def __enter__(self):
        # Only enable raw mode if stdin is a tty
        if not sys.stdin.isatty():
            self.fd = None
            return self
        import termios
        import tty
        self.fd = sys.stdin.fileno()
        self.old = termios.tcgetattr(self.fd)
        tty.setraw(self.fd)
        # also enter alternate screen + hide cursor
        sys.stdout.write(HIDE_CURSOR)
        sys.stdout.flush()
        return self

    def __exit__(self, *exc):
        if self.fd is not None:
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
            sys.stdout.write(SHOW_CURSOR + RESET + "\n")
            sys.stdout.flush()


def read_key_nonblocking() -> str | None:
    """Read a single keypress without blocking. Returns None if no input."""
    import select
    if not sys.stdin.isatty():
        return None
    r, _, _ = select.select([sys.stdin], [], [], 0.0)
    if not r:
        return None
    ch = sys.stdin.read(1)
    if ch == "\x1b":
        # possible escape sequence; try to read more
        r2, _, _ = select.select([sys.stdin], [], [], 0.02)
        if not r2:
            return "esc"
        ch2 = sys.stdin.read(1)
        if ch2 == "[":
            ch3 = sys.stdin.read(1)
            return f"esc[{ch3}"
        return "esc"
    return ch


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def get_size() -> Tuple[int, int]:
    try:
        import shutil
        cols, rows = shutil.get_terminal_size()
        return max(10, cols), max(8, rows)
    except Exception:
        return 80, 24


def handle_key(key: str | None, state: State) -> bool:
    """Process a single keypress. Return True if the app should quit.

    Speed is clamped to [0.05, 8.0]; accelerating from a very low speed
    always nudges it up by a small absolute step so it can never get stuck
    at zero (or go negative, which would run the animation backwards).
    """
    if key is None:
        return False
    k = key.lower()
    if k in ("q", "esc", "esc["):
        return True
    if k == " ":
        state.paused = not state.paused
    elif k in ("+", "="):
        # ensure forward progress even from ~0 speed
        state.speed = min(8.0, max(0.1, state.speed * 1.2))
    elif k in ("-", "_"):
        state.speed = max(0.05, state.speed / 1.2)
    elif k == "r":
        state.reduced_motion = not state.reduced_motion
    elif k == "c":
        state.palette_index = (state.palette_index + 1) % len(PALETTE_ORDER)
        state.palette_name = PALETTE_ORDER[state.palette_index]
    elif k == "m":
        state.show_moon = not state.show_moon
    elif k == "s":
        state.show_stars = not state.show_stars
    elif k == "l":
        state.show_lake = not state.show_lake
    elif k == "t":
        state.show_mountains = not state.show_mountains
    elif k == "h":
        state.show_help = not state.show_help
    return False


def loop(state: State, fps: float, interactive: bool, duration: float,
         render_only: bool) -> None:
    target_dt = 1.0 / fps
    start = time.time()
    last_size_check = 0.0
    with RawTerminal():
        if interactive:
            sys.stdout.write(CLEAR)
        while True:
            now = time.time()
            if duration > 0 and (now - start) > duration:
                break
            # resize check (cheap, throttled)
            if now - last_size_check > 0.5:
                w, h = get_size()
                reinit_for_size(state, w, h)
                last_size_check = now

            if interactive:
                key = read_key_nonblocking()
                if handle_key(key, state):
                    break
            else:
                # check for single key via select
                import select
                r, _, _ = select.select([sys.stdin], [], [], 0.0)
                if r:
                    k = sys.stdin.read(1)
                    if k in ("q", "\x1b", "\x03"):
                        break

            if not state.paused:
                dt = target_dt * state.speed
                if state.reduced_motion:
                    dt *= 0.4
                state.time += dt
                # spawn / advance shooting stars (only when stars visible)
                if state.show_stars and not state.reduced_motion:
                    maybe_spawn_shooting_star(state, state.meteor_rng)
                    update_shooting_stars(state, dt)
            state.frame += 1

            frame_str = build_frame(state)
            if state.show_help:
                frame_str += render_help(state)
            sys.stdout.write(frame_str)
            # status line at bottom
            if interactive:
                status = (
                    f"\033[{state.height};1H\033[38;2;120;140;170m"
                    f"aurora | {state.palette_name} | {state.speed:.2f}x | "
                    f"{'reduced' if state.reduced_motion else 'normal'} | "
                    f"t={state.time:6.1f}s | q:quit c:palette r:motion "
                    f"m:moon s:stars l:lake t:mtn h:help"
                    f"   \033[2K\033[0m"
                )
                sys.stdout.write(status)
            sys.stdout.flush()

            # pacing
            elapsed = time.time() - now
            sleep_for = target_dt - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
            if render_only and state.frame >= 1:
                break


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Terminal Aurora Borealis Simulator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--version", action="version",
                   version=f"aurora {__version__}")
    p.add_argument("--palette", choices=PALETTE_ORDER, default="green",
                   help="initial color palette")
    p.add_argument("--speed", type=float, default=1.0, help="initial animation speed")
    p.add_argument("--seed", type=int, default=None, help="random seed (default: time)")
    p.add_argument("--fps", type=float, default=24.0, help="target frames per second")
    p.add_argument("--duration", type=float, default=0.0,
                   help="run for N seconds then exit (0 = forever)")
    p.add_argument("--reduced-motion", action="store_true",
                   help="start in reduced-motion mode")
    p.add_argument("--non-interactive", action="store_true",
                   help="do not read keyboard input (use with --duration)")
    p.add_argument("--once", action="store_true",
                   help="render a single frame and exit (useful for screenshots)")
    # explicit canvas size (overrides terminal detection; handy for CI/svgs)
    p.add_argument("--width", type=int, default=None,
                   help="force canvas width in columns (default: terminal width)")
    p.add_argument("--height", type=int, default=None,
                   help="force canvas height in rows (default: terminal height)")
    # feature toggles (start with each feature off)
    p.add_argument("--no-moon", action="store_true", help="hide the moon")
    p.add_argument("--no-stars", action="store_true",
                   help="hide the starfield and shooting stars")
    p.add_argument("--no-mountains", action="store_true",
                   help="hide the mountain silhouette")
    p.add_argument("--no-lake", action="store_true",
                   help="hide the lake reflection")
    p.add_argument("--list-palettes", action="store_true",
                   help="print the available palettes and exit")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.list_palettes:
        for name in PALETTE_ORDER:
            print(name)
        return 0

    seed = args.seed if args.seed is not None else int(time.time() * 1000) & 0xFFFFFFFF

    # If output is not a TTY, render a single frame snapshot instead of
    # attempting an interactive loop (e.g. when piped or run in CI).
    if not sys.stdout.isatty() and not args.once:
        # still allow --once / snapshot mode
        args.once = True

    w, h = get_size()
    if args.width is not None:
        w = max(10, args.width)
    if args.height is not None:
        h = max(8, args.height)
    state = init_state(
        w, h, seed, args.palette,
        show_moon=not args.no_moon,
        show_stars=not args.no_stars,
        show_mountains=not args.no_mountains,
        show_lake=not args.no_lake,
    )
    state.speed = max(0.05, args.speed)
    state.reduced_motion = args.reduced_motion
    state.last_size = (w, h)

    interactive = not args.non_interactive and sys.stdin.isatty()
    render_only = args.once

    # graceful Ctrl-C
    def _sigint(*_):
        sys.stdout.write(SHOW_CURSOR + RESET + "\n")
        sys.stdout.flush()
        sys.exit(0)
    signal.signal(signal.SIGINT, _sigint)

    try:
        loop(state, fps=args.fps, interactive=interactive,
             duration=args.duration, render_only=render_only)
    finally:
        sys.stdout.write(SHOW_CURSOR + RESET + "\n")
        sys.stdout.flush()

    if render_only:
        # already printed one frame
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())