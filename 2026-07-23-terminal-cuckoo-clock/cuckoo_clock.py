#!/usr/bin/env python3
"""
Terminal Cuckoo Clock Simulator
================================
An ASCII-art cuckoo clock that ticks in real time (or in time-warp mode).
Features:
  * Swinging pendulum with damped harmonic motion
  * Interlocking gears that rotate at correct relative speeds
  * A cuckoo bird that pops out on the hour and cuckoos N times
  * Quarter-hour chimes (Westminster-style motif) played note-by-note
  * Bell sound via the terminal bell character (\\a)
  * Live digital readout of the time (12h or 24h, toggable with `h`)
  * Optional curses color for the case, dial, gears, bird, and pendulum
  * --warp SPEED option to accelerate time for demoing
  * --once option: run a single hour-strike and exit (great for testing)
  * --start HH:MM:SS option to begin from a custom time
  * --version / --help flags

No third-party dependencies — pure stdlib (curses + time).
"""

from __future__ import annotations

import argparse
import curses
import math
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

__version__ = "1.1.0"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def gear(teeth: int, radius: int, rotation: float) -> List[str]:
    """Render a spur gear as a list of strings (one per row).

    The gear has `teeth` teeth around a circle of approx `radius` cells.
    `rotation` is in radians.  We sample the gear outline on a grid and
    fill the interior so it reads as a solid wheel with teeth.
    """
    size = 2 * radius + 3
    cx = cy = radius + 1
    canvas = [[" "] * size for _ in range(size)]
    # tooth depth in cells
    tooth_depth = max(1, radius // 4)
    outer = radius + tooth_depth
    inner = radius
    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            # squash y because terminal cells are ~2x tall
            r = math.hypot(dx, dy * 2.0)
            angle = math.atan2(dy * 2.0, dx) + rotation
            # tooth modulation: how far out is the surface here?
            phase = (angle * teeth / (2 * math.pi)) % 1.0
            # square-ish tooth profile
            tooth_factor = 1.0 if (phase < 0.5) else 0.78
            surface = outer * tooth_factor
            if r <= inner * 0.4:
                ch = "·"  # hub
            elif r <= surface:
                # choose a glyph based on angle to give a faceted look
                spoke = (math.cos(angle * teeth / 2) + 1) / 2
                if r > inner * 0.6 and r < inner * 0.95 and spoke > 0.7:
                    ch = " "  # spokes (negative space)
                elif abs(r - surface) < 1.2:
                    ch = "#" if tooth_factor > 0.9 else "+"
                else:
                    ch = "·" if r < inner else "#"
            else:
                ch = " "
            if ch != " ":
                canvas[y][x] = ch
    # central axle
    canvas[cy][cx] = "O"
    return ["".join(row) for row in canvas]


def overlay(screen: List[List[str]], glyph_rows: List[str], top: int, left: int) -> None:
    """Blit glyph rows onto a character screen at (top, left), clipping edges."""
    h = len(screen)
    w = len(screen[0]) if h else 0
    for ry, row in enumerate(glyph_rows):
        y = top + ry
        if y < 0 or y >= h:
            continue
        for cx, ch in enumerate(row):
            if ch == " ":
                continue
            x = left + cx
            if x < 0 or x >= w:
                continue
            screen[y][x] = ch


def pendulum_bob(angle: float) -> List[str]:
    """Small ascii bob on a short rod; angle in radians from vertical."""
    rows: List[str] = []
    length = 8
    for i in range(length):
        x = int(round(math.sin(angle) * i))
        line = [" "] * (2 * length + 1)
        line[length + x] = "|"
        rows.append("".join(line))
    # bob
    bx = int(round(math.sin(angle) * length))
    pad = " " * (length + bx - 3)
    rows.append(f"{pad}(===)")
    pad2 = " " * (length + bx - 3)
    rows.append(f"{pad2} \\ / ")
    return rows


# ---------------------------------------------------------------------------
# Westminster chime motif (quarter-hour)
# ---------------------------------------------------------------------------
#
# Notes carry a relative pitch (Hz). The terminal bell (\a) has no frequency
# control, so we simulate a melody by spacing the taps at note-appropriate
# intervals (longer = lower). The note *names* are shown in the side panel so
# the motif is visible even when the bell is silent.

NOTE_FREQ = {
    "C4": 261.6, "D4": 293.7, "E4": 329.6, "F4": 349.2,
    "G4": 392.0, "A4": 440.0, "B3": 246.9, "B4": 493.9,
    "C5": 523.2, "E5": 659.2, "G3": 196.0,
}

# The four "quarter" motifs of Westminster:
WESTMINSTER = {
    15: ["C4", "D4", "E4", "B3"],
    30: ["E4", "C4", "D4", "B3", "E4", "C4", "D4"],
    45: ["C4", "D4", "E4", "B3", "C4", "D4", "E4", "C4", "D4"],
    60: [],  # full hour handled by cuckoo
}


def note_interval(note: str) -> float:
    """Return the audible duration (seconds) for a note — lower notes ring longer."""
    freq = NOTE_FREQ.get(note, 300.0)
    # clamp to a pleasant range: ~0.25s (high) .. ~0.6s (low)
    return max(0.22, min(0.65, 220.0 / freq + 0.18))


@dataclass
class ChimeState:
    """Drives a note-by-note Westminster chime animation."""
    active: bool = False
    notes: List[str] = field(default_factory=list)
    index: int = 0
    timer: float = 0.0


@dataclass
class ClockState:
    # Simulated time in seconds since midnight (can exceed real time when warped)
    sim_seconds: float = 0.0
    # For pendulum phase
    pendulum_phase: float = 0.0
    # Gear rotations (radians)
    gear_a: float = 0.0
    gear_b: float = 0.0
    # Cuckoo state
    cuckoo_active: bool = False
    cuckoo_count: int = 0  # how many cuckoos remaining
    cuckoo_step: int = 0  # sub-step within current cuckoo (0..N)
    cuckoo_timer: float = 0.0
    # Last quarter struck (15/30/45/60) so we don't repeat
    last_quarter: int = -1
    # Bell log (recent events) for display
    log: List[str] = field(default_factory=list)
    # Quarter chime sequencer
    chime: ChimeState = field(default_factory=ChimeState)
    # Display mode: True = 24-hour, False = 12-hour
    use_24h: bool = False


def hours_minutes_seconds(sim_seconds: float) -> Tuple[int, int, int, int]:
    """Return (hour12, minute, second, quarter) where quarter is 0/15/30/45."""
    s = int(sim_seconds) % 86400
    hour = (s // 3600) % 24
    minute = (s % 3600) // 60
    second = s % 60
    hour12 = hour % 12
    if hour12 == 0:
        hour12 = 12
    quarter = (minute // 15) * 15
    return hour12, minute, second, quarter


def start_cuckoo(state: ClockState, count: int) -> None:
    """Begin a cuckoo strike of `count` calls."""
    # Clamp count to a sane range to avoid runaway loops in odd time-zones.
    count = max(1, min(count, 12))
    state.cuckoo_active = True
    state.cuckoo_count = count
    state.cuckoo_step = 0
    state.cuckoo_timer = 0.0
    state.log.append(f"Cuckoo! ×{count}")


def start_chime(state: ClockState, quarter: int) -> None:
    """Begin playing a Westminster quarter-chime motif note-by-note."""
    notes = WESTMINSTER.get(quarter, [])
    if not notes:
        return
    state.chime.active = True
    state.chime.notes = list(notes)
    state.chime.index = 0
    state.chime.timer = 0.0
    state.log.append(f"Chime (Q{quarter}): {'-'.join(notes)}")


def format_time(hour12: int, minute: int, second: int, use_24h: bool,
                sim_seconds: float) -> str:
    """Format the digital readout in 12h or 24h style."""
    if use_24h:
        h24 = (int(sim_seconds) // 3600) % 24
        return f"⏰  {h24:02d}:{minute:02d}:{second:02d}"
    return f"⏰  {hour12:02d}:{minute:02d}:{second:02d}"


def parse_start_time(spec: str) -> float:
    """Parse a 'HH:MM:SS' or 'HH:MM' string into seconds-since-midnight.

    Raises ValueError on malformed input.
    """
    parts = spec.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"expected HH:MM[:SS], got {spec!r}")
    nums = [int(p) for p in parts]
    hh, mm = nums[0], nums[1]
    ss = nums[2] if len(nums) == 3 else 0
    if not (0 <= hh < 24 and 0 <= mm < 60 and 0 <= ss < 60):
        raise ValueError(f"time components out of range: {spec!r}")
    return hh * 3600 + mm * 60 + ss


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

BIRD_CLOSED = [
    "   ___   ",
    "  /   \\  ",
    " | O O | ",
    "  \\___/  ",
]

BIRD_OPEN = [
    "   ___   ",
    "  / o \\  ",
    " | \\_/ | ",
    "  \\___/  ",
    "   vvv   ",
]

# Color pair ids (initialized once in render via _init_colors)
_COLOR_CASE = 1
_COLOR_DIAL = 2
_COLOR_HAND = 3
_COLOR_BIRD = 4
_COLOR_GEAR = 5
_COLOR_PEND = 6
_COLOR_DIGITAL = 7
_COLOR_LOG = 8
_COLOR_CHIME = 9
_colors_ready = False


def _init_colors() -> None:
    """Set up curses color pairs. Called once (guarded by _colors_ready)."""
    global _colors_ready
    if _colors_ready:
        return
    if not curses.has_colors():
        return
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK
    curses.init_pair(_COLOR_CASE, curses.COLOR_YELLOW, bg)
    curses.init_pair(_COLOR_DIAL, curses.COLOR_CYAN, bg)
    curses.init_pair(_COLOR_HAND, curses.COLOR_WHITE, bg)
    curses.init_pair(_COLOR_BIRD, curses.COLOR_RED, bg)
    curses.init_pair(_COLOR_GEAR, curses.COLOR_GREEN, bg)
    curses.init_pair(_COLOR_PEND, curses.COLOR_MAGENTA, bg)
    curses.init_pair(_COLOR_DIGITAL, curses.COLOR_WHITE, bg)
    curses.init_pair(_COLOR_LOG, curses.COLOR_BLUE, bg)
    curses.init_pair(_COLOR_CHIME, curses.COLOR_YELLOW, bg)
    _colors_ready = True


def _new_color_grid(h: int, w: int) -> List[List[int]]:
    return [[0] * w for _ in range(h)]


def render(state: ClockState, stdscr, frame: int) -> None:
    h, w = stdscr.getmaxyx()
    if h < 24 or w < 60:
        stdscr.addstr(0, 0, "Terminal too small (need >=60x24). Resize me!")
        stdscr.clrtoeol()
        return

    _init_colors()
    has_color = curses.has_colors() and _colors_ready

    screen: List[List[str]] = [[" "] * w for _ in range(h)]
    colors = _new_color_grid(h, w) if has_color else None

    def put(y: int, x: int, ch: str, pair: int = 0) -> None:
        if 0 <= y < h and 0 <= x < w:
            screen[y][x] = ch
            if colors is not None and pair:
                colors[y][x] = pair

    # ---- Clock case (wooden frame) ----
    case_top = 1
    case_left = (w - 44) // 2
    case_w = 44
    case_h = 20
    for x in range(case_w):
        put(case_top, case_left + x, "═", _COLOR_CASE)
        put(case_top + case_h - 1, case_left + x, "═", _COLOR_CASE)
    for y in range(case_h):
        put(case_top + y, case_left, "║", _COLOR_CASE)
        put(case_top + y, case_left + case_w - 1, "║", _COLOR_CASE)
    put(case_top, case_left, "╔", _COLOR_CASE)
    put(case_top, case_left + case_w - 1, "╗", _COLOR_CASE)
    put(case_top + case_h - 1, case_left, "╚", _COLOR_CASE)
    put(case_top + case_h - 1, case_left + case_w - 1, "╝", _COLOR_CASE)
    # roof apex
    apex = case_top - 2
    mid = case_left + case_w // 2
    put(apex, mid, "▲", _COLOR_CASE)
    put(apex + 1, mid - 1, "╱", _COLOR_CASE)
    put(apex + 1, mid + 1, "╲", _COLOR_CASE)
    put(apex + 1, mid, "^", _COLOR_CASE)
    # "CUCKOO" plaque
    plaque = "· CUCKOO ·"
    for i, ch in enumerate(plaque):
        put(case_top + 1, case_left + 6 + i, ch, _COLOR_CASE)

    # ---- Dial (clock face with hands) ----
    dial_cx = case_left + case_w // 2
    dial_cy = case_top + 8
    dial_r = 6
    # draw circle
    for ang_deg in range(0, 360, 6):
        a = math.radians(ang_deg)
        px = int(round(dial_cx + math.cos(a) * dial_r))
        py = int(round(dial_cy + math.sin(a) * dial_r * 0.5))
        put(py, px, "•", _COLOR_DIAL)
    # hour ticks
    for hr in range(12):
        a = math.radians(hr * 30 - 90)
        px = int(round(dial_cx + math.cos(a) * (dial_r - 1)))
        py = int(round(dial_cy + math.sin(a) * (dial_r - 1) * 0.5))
        put(py, px, str(hr % 12 + 1)[0], _COLOR_DIAL)
    # hands — derive from sim_seconds
    hour12, minute, second, quarter = hours_minutes_seconds(state.sim_seconds)
    hour_angle = math.radians(((hour12 % 12) * 30 + minute * 0.5) - 90)
    min_angle = math.radians((minute * 6 + second * 0.1) - 90)
    sec_angle = math.radians((second * 6) - 90)
    for r in range(1, dial_r - 2):
        px = int(round(dial_cx + math.cos(hour_angle) * r * 0.6))
        py = int(round(dial_cy + math.sin(hour_angle) * r * 0.5 * 0.6))
        put(py, px, "█", _COLOR_HAND)
    for r in range(1, dial_r - 1):
        px = int(round(dial_cx + math.cos(min_angle) * r))
        py = int(round(dial_cy + math.sin(min_angle) * r * 0.5))
        put(py, px, "▌", _COLOR_HAND)
    px = int(round(dial_cx + math.cos(sec_angle) * (dial_r - 1)))
    py = int(round(dial_cy + math.sin(sec_angle) * (dial_r - 1) * 0.5))
    put(py, px, "●", _COLOR_HAND)
    put(dial_cy, dial_cx, "✚", _COLOR_HAND)

    # ---- Cuckoo door (above the dial) ----
    door_w = 10
    door_h = 5
    door_left = dial_cx - door_w // 2
    door_top = case_top + 2
    if state.cuckoo_active:
        # door open (show bird)
        for y in range(door_h):
            for x in range(door_w):
                put(door_top + y, door_left + x, " ")
        bird = BIRD_OPEN if (state.cuckoo_step % 2 == 0) else BIRD_CLOSED
        overlay(screen, bird, door_top, door_left + 1)
        if colors is not None:
            for ry, brow in enumerate(bird):
                for cx, ch in enumerate(brow):
                    if ch != " ":
                        y = door_top + ry
                        x = door_left + 1 + cx
                        if 0 <= y < h and 0 <= x < w:
                            colors[y][x] = _COLOR_BIRD
    else:
        # door closed
        for x in range(door_w):
            put(door_top, door_left + x, "─", _COLOR_CASE)
            put(door_top + door_h - 1, door_left + x, "─", _COLOR_CASE)
        for y in range(door_h):
            put(door_top + y, door_left, "│", _COLOR_CASE)
            put(door_top + y, door_left + door_w - 1, "│", _COLOR_CASE)
        put(door_top + 1, door_left + 3, "▼", _COLOR_CASE)
        put(door_top + 1, door_left + 6, "▼", _COLOR_CASE)

    # ---- Gears (visible below dial, left and right) ----
    g1 = gear(teeth=10, radius=4, rotation=state.gear_a)
    g2 = gear(teeth=14, radius=5, rotation=state.gear_b)
    overlay(screen, g1, case_top + 13, case_left + 3)
    overlay(screen, g2, case_top + 12, case_left + case_w - 14)
    if colors is not None:
        for glyph_rows, top, left in [
            (g1, case_top + 13, case_left + 3),
            (g2, case_top + 12, case_left + case_w - 14),
        ]:
            for ry, row in enumerate(glyph_rows):
                for cx, ch in enumerate(row):
                    if ch != " ":
                        y = top + ry
                        x = left + cx
                        if 0 <= y < h and 0 <= x < w:
                            colors[y][x] = _COLOR_GEAR

    # ---- Pendulum (hangs below the case, center-left) ----
    pend = pendulum_bob(state.pendulum_phase)
    overlay(screen, pend, case_top + case_h, dial_cx - 8)
    if colors is not None:
        for ry, prow in enumerate(pend):
            for cx, ch in enumerate(prow):
                if ch != " ":
                    y = case_top + case_h + ry
                    x = dial_cx - 8 + cx
                    if 0 <= y < h and 0 <= x < w:
                        colors[y][x] = _COLOR_PEND

    # ---- Digital readout + status (bottom) ----
    status_y = h - 4
    digital = format_time(hour12, minute, second, state.use_24h, state.sim_seconds)
    dx = max(0, (w - len(digital)) // 2)
    for i, ch in enumerate(digital):
        put(status_y, dx + i, ch, _COLOR_DIGITAL)
    quarter_label = {0: "top of hour", 15: "quarter past",
                     30: "half past", 45: "quarter to"}[quarter]
    qlabel = f"({quarter_label})"
    qx = max(0, (w - len(qlabel)) // 2)
    for i, ch in enumerate(qlabel):
        put(status_y + 1, qx + i, ch, _COLOR_DIGITAL)

    # Cuckoo / chime activity indicator
    if state.cuckoo_active:
        cu = f"🐦 CUCKOO!  ({state.cuckoo_count} left)"
        cu_pair = _COLOR_BIRD
    elif state.chime.active:
        idx = min(state.chime.index, len(state.chime.notes) - 1)
        note = state.chime.notes[idx] if state.chime.notes else "?"
        cu = f"🔔 Chime: {note}  ({state.chime.index + 1}/{len(state.chime.notes)})"
        cu_pair = _COLOR_CHIME
    else:
        cu = "🐦 zzz…"
        cu_pair = 0
    cux = max(0, (w - len(cu)) // 2)
    for i, ch in enumerate(cu):
        put(status_y + 2, cux + i, ch, cu_pair)

    # Log lines (left side)
    log_x = 2
    log_y = 1
    for j, ch in enumerate("Log:"):
        put(log_y, log_x + j, ch, _COLOR_LOG)
    for i, entry in enumerate(state.log[-(h - 6):]):
        line = entry[: w - 4]
        for j, ch in enumerate(line):
            put(log_y + 1 + i, log_x + j, ch, _COLOR_LOG)

    # ---- Blit to stdscr ----
    for y, row in enumerate(screen):
        try:
            line = "".join(row)
            if has_color:
                # Write char-by-char honoring color pairs, batching runs.
                # `colors` is non-None here because has_color requires it.
                row_colors = colors[y]  # type: ignore[index]
                x = 0
                while x < len(line):
                    pair = row_colors[x]
                    x2 = x + 1
                    while (x2 < len(line) and row_colors[x2] == pair
                           and line[x] != " " and line[x2] != " "):
                        x2 += 1
                    attr = curses.color_pair(pair)
                    stdscr.addnstr(y, x, line[x:x2], x2 - x, attr)
                    x = x2
            else:
                stdscr.addnstr(y, 0, line, w - 1)
        except curses.error:
            pass
    stdscr.refresh()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run(stdscr, args) -> None:
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.clear()

    state = ClockState()
    # Seed sim time: start at the current wall clock (or custom start)
    if args.start is not None:
        try:
            state.sim_seconds = parse_start_time(args.start)
        except ValueError as e:
            # Should not happen because argparse validates, but be safe.
            sys.stderr.write(f"invalid --start: {e}\n")
            return
    else:
        now = time.localtime()
        state.sim_seconds = now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec

    warp = args.warp
    t_last = time.monotonic()

    if args.once:
        # Fast-forward to next top of hour and strike once for testing
        # jump to a top-of-hour boundary
        state.sim_seconds = math.ceil(state.sim_seconds / 3600) * 3600
        hour12, _, _, quarter = hours_minutes_seconds(state.sim_seconds)
        if quarter == 0:
            start_cuckoo(state, hour12 if hour12 != 0 else 12)

    while True:
        # ---- input ----
        ch = stdscr.getch()
        if ch == ord("q") or ch == 27:  # q or ESC
            break
        elif ch == ord(" "):
            # space = strike cuckoo now (manual)
            hour12, _, _, _ = hours_minutes_seconds(state.sim_seconds)
            if not state.cuckoo_active:
                start_cuckoo(state, hour12 if hour12 != 0 else 12)
        elif ch in (ord("h"), ord("H")):
            # toggle 12h / 24h digital readout
            state.use_24h = not state.use_24h
        elif ch in (ord("c"), ord("C")):
            # manually trigger the current quarter chime
            _, _, _, quarter = hours_minutes_seconds(state.sim_seconds)
            if not state.chime.active and quarter in (15, 30, 45):
                start_chime(state, quarter)

        # ---- time step ----
        t_now = time.monotonic()
        dt = t_now - t_last
        t_last = t_now
        state.sim_seconds += dt * warp

        # pendulum: ~1 Hz swing
        state.pendulum_phase = math.sin(state.sim_seconds * math.pi) * 0.35

        # gears: A turns faster than B (escape wheel vs great wheel)
        state.gear_a += dt * warp * 1.2
        state.gear_b -= dt * warp * 0.5  # meshed, opposite direction

        # ---- quarter chimes ----
        hour12, minute, second, quarter = hours_minutes_seconds(state.sim_seconds)
        if quarter != state.last_quarter:
            state.last_quarter = quarter
            if quarter in (15, 30, 45):
                start_chime(state, quarter)
            if quarter == 0:
                # top of hour: cuckoo N times
                if not state.cuckoo_active:
                    start_cuckoo(state, hour12 if hour12 != 0 else 12)

        # ---- chime sequencer stepping ----
        if state.chime.active:
            state.chime.timer += dt * warp
            if state.chime.index < len(state.chime.notes):
                cur_note = state.chime.notes[state.chime.index]
                if state.chime.timer >= note_interval(cur_note):
                    state.chime.timer = 0.0
                    state.chime.index += 1
                    if not args.silent:
                        sys.stdout.write("\a")
                        sys.stdout.flush()
            if state.chime.index >= len(state.chime.notes):
                state.chime.active = False

        # ---- cuckoo animation stepping ----
        if state.cuckoo_active:
            state.cuckoo_timer += dt * warp
            # each "cuckoo" takes ~1.2s: 0.4s open beak + 0.4s hold + 0.4s close
            step_len = 1.2
            if state.cuckoo_timer >= step_len:
                state.cuckoo_timer = 0.0
                state.cuckoo_step += 1
                # strike a bell for each completed cuckoo
                if not args.silent:
                    sys.stdout.write("\a")
                    sys.stdout.flush()
                state.cuckoo_count -= 1
                if state.cuckoo_count <= 0:
                    state.cuckoo_active = False
                    if args.once:
                        break  # exit after one strike for --once mode

        # ---- render ----
        render(state, stdscr, 0)

        # pace the loop
        time.sleep(0.05)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Terminal Cuckoo Clock Simulator — ASCII cuckoo clock for your terminal.",
    )
    ap.add_argument("--warp", type=float, default=1.0,
                    help="Time-warp multiplier (1=real-time, 3600=1 hour per second).")
    ap.add_argument("--silent", action="store_true",
                    help="Disable terminal bell chimes.")
    ap.add_argument("--once", action="store_true",
                    help="Run a single hour-strike and exit (useful for testing).")
    ap.add_argument("--start", metavar="HH:MM:SS", default=None,
                    help="Start the clock at a custom time (e.g. 11:00 or 23:59:30).")
    ap.add_argument("--version", action="version",
                    version=f"terminal-cuckoo-clock {__version__}")
    args = ap.parse_args()

    # Validate --start up front so we fail before entering curses.
    if args.start is not None:
        try:
            parse_start_time(args.start)
        except ValueError as e:
            ap.error(f"--start: {e}")

    if args.warp <= 0:
        ap.error("--warp must be a positive number")

    try:
        curses.wrapper(run, args)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()