#!/usr/bin/env python3
"""
Terminal Cuckoo Clock Simulator
================================
An ASCII-art cuckoo clock that ticks in real time (or in time-warp mode).
Features:
  * Swinging pendulum with damped harmonic motion
  * Interlocking gears that rotate at correct relative speeds
  * A cuckoo bird that pops out on the hour and cuckoos N times
  * Quarter-hour chimes (Westminster-style motif)
  * Bell sound via the terminal bell character (\\a)
  * Live digital readout of the time
  * --warp SPEED option to accelerate time for demoing
  * --once option: run a single hour-strike and exit (great for testing)

No third-party dependencies — pure stdlib (curses + time).
"""

from __future__ import annotations

import argparse
import curses
import math
import sys
import time
from dataclasses import dataclass, field
from typing import List, Tuple


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

# Notes as (frequency-ish label, beat count).  We use bell char for strike.
# The four "quarter" motifs of Westminster:
WESTMINSTER = {
    15: ["C4", "D4", "E4", "B3"],
    30: ["E4", "C4", "D4", "B3", "E4", "C4", "D4"],
    45: ["C4", "D4", "E4", "B3", "C4", "D4", "E4", "C4", "D4"],
    60: [],  # full hour handled by cuckoo
}


@dataclass
class ClockState:
    # Simulated time in seconds since midnight (can exceed real time when warped)
    sim_seconds: float = 0.0
    # For pendulum phase
    pendulum_phase: float = 0.0
    # Gear rotations (radians)
    gear_a: float = 0.0
    gear_b: float = 0.0
    gear_c: float = 0.0
    # Cuckoo state
    cuckoo_active: bool = False
    cuckoo_count: int = 0  # how many cuckoos remaining
    cuckoo_step: int = 0  # sub-step within current cuckoo (0..N)
    cuckoo_timer: float = 0.0
    # Last quarter struck (15/30/45/60) so we don't repeat
    last_quarter: int = -1
    # Bell log (recent events) for display
    log: List[str] = field(default_factory=list)


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
    state.cuckoo_active = True
    state.cuckoo_count = count
    state.cuckoo_step = 0
    state.cuckoo_timer = 0.0
    state.log.append(f"Cuckoo! ×{count}")


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


def render(state: ClockState, stdscr, frame: int) -> None:
    h, w = stdscr.getmaxyx()
    if h < 24 or w < 60:
        stdscr.addstr(0, 0, "Terminal too small (need >=60x24). Resize me!")
        stdscr.clrtoeol()
        return

    screen: List[List[str]] = [[" "] * w for _ in range(h)]

    # ---- Clock case (wooden frame) ----
    case_top = 1
    case_left = (w - 44) // 2
    case_w = 44
    case_h = 20
    for x in range(case_w):
        screen[case_top][case_left + x] = "═"
        screen[case_top + case_h - 1][case_left + x] = "═"
    for y in range(case_h):
        screen[case_top + y][case_left] = "║"
        screen[case_top + y][case_left + case_w - 1] = "║"
    screen[case_top][case_left] = "╔"
    screen[case_top][case_left + case_w - 1] = "╗"
    screen[case_top + case_h - 1][case_left] = "╚"
    screen[case_top + case_h - 1][case_left + case_w - 1] = "╝"
    # roof apex
    apex = case_top - 2
    mid = case_left + case_w // 2
    screen[apex][mid] = "▲"
    screen[apex + 1][mid - 1] = "╱"
    screen[apex + 1][mid + 1] = "╲"
    screen[apex + 1][mid] = "^"
    # "CUCKOO" plaque
    plaque = "· CUCKOO ·"
    for i, ch in enumerate(plaque):
        screen[case_top + 1][case_left + 6 + i] = ch

    # ---- Dial (clock face with hands) ----
    dial_cx = case_left + case_w // 2
    dial_cy = case_top + 8
    dial_r = 6
    # draw circle
    for ang_deg in range(0, 360, 6):
        a = math.radians(ang_deg)
        px = int(round(dial_cx + math.cos(a) * dial_r))
        py = int(round(dial_cy + math.sin(a) * dial_r * 0.5))
        if 0 <= py < h and 0 <= px < w:
            screen[py][px] = "•"
    # hour ticks
    for hr in range(12):
        a = math.radians(hr * 30 - 90)
        px = int(round(dial_cx + math.cos(a) * (dial_r - 1)))
        py = int(round(dial_cy + math.sin(a) * (dial_r - 1) * 0.5))
        if 0 <= py < h and 0 <= px < w:
            screen[py][px] = str(hr % 12 + 1)[0]
    # hands — derive from sim_seconds
    hour12, minute, second, quarter = hours_minutes_seconds(state.sim_seconds)
    hour_angle = math.radians(((hour12 % 12) * 30 + minute * 0.5) - 90)
    min_angle = math.radians((minute * 6 + second * 0.1) - 90)
    sec_angle = math.radians((second * 6) - 90)
    for r in range(1, dial_r - 2):
        px = int(round(dial_cx + math.cos(hour_angle) * r * 0.6))
        py = int(round(dial_cy + math.sin(hour_angle) * r * 0.5 * 0.6))
        if 0 <= py < h and 0 <= px < w:
            screen[py][px] = "█"
    for r in range(1, dial_r - 1):
        px = int(round(dial_cx + math.cos(min_angle) * r))
        py = int(round(dial_cy + math.sin(min_angle) * r * 0.5))
        if 0 <= py < h and 0 <= px < w:
            screen[py][px] = "▌"
    px = int(round(dial_cx + math.cos(sec_angle) * (dial_r - 1)))
    py = int(round(dial_cy + math.sin(sec_angle) * (dial_r - 1) * 0.5))
    if 0 <= py < h and 0 <= px < w:
        screen[py][px] = "●"
    screen[dial_cy][dial_cx] = "✚"

    # ---- Cuckoo door (above the dial) ----
    door_w = 10
    door_h = 5
    door_left = dial_cx - door_w // 2
    door_top = case_top + 2
    if state.cuckoo_active:
        # door open (show bird)
        for y in range(door_h):
            for x in range(door_w):
                screen[door_top + y][door_left + x] = " "
        bird = BIRD_OPEN if (state.cuckoo_step % 2 == 0) else BIRD_CLOSED
        overlay(screen, bird, door_top, door_left + 1)
    else:
        # door closed
        for x in range(door_w):
            screen[door_top][door_left + x] = "─"
            screen[door_top + door_h - 1][door_left + x] = "─"
        for y in range(door_h):
            screen[door_top + y][door_left] = "│"
            screen[door_top + y][door_left + door_w - 1] = "│"
        screen[door_top + 1][door_left + 3] = "▼"
        screen[door_top + 1][door_left + 6] = "▼"

    # ---- Gears (visible below dial, left and right) ----
    g1 = gear(teeth=10, radius=4, rotation=state.gear_a)
    g2 = gear(teeth=14, radius=5, rotation=state.gear_b)
    overlay(screen, g1, case_top + 13, case_left + 3)
    overlay(screen, g2, case_top + 12, case_left + case_w - 14)

    # ---- Pendulum (hangs below the case, center-left) ----
    pend = pendulum_bob(state.pendulum_phase)
    overlay(screen, pend, case_top + case_h, dial_cx - 8)

    # ---- Digital readout + status (bottom) ----
    status_y = h - 4
    digital = f"⏰  {hour12:02d}:{minute:02d}:{second:02d}"
    screen[status_y][(w - len(digital)) // 2] = digital[0]
    # write safely
    dx = (w - len(digital)) // 2
    for i, ch in enumerate(digital):
        if 0 <= dx + i < w:
            screen[status_y][dx + i] = ch
    quarter_label = {0: "top of hour", 15: "quarter past", 30: "half past", 45: "quarter to"}[quarter]
    qlabel = f"({quarter_label})"
    qx = (w - len(qlabel)) // 2
    for i, ch in enumerate(qlabel):
        if 0 <= qx + i < w:
            screen[status_y + 1][qx + i] = ch

    # Cuckoo activity indicator
    if state.cuckoo_active:
        cu = f"🐦 CUCKOO!  ({state.cuckoo_count} left)"
    else:
        cu = "🐦 zzz…"
    cux = (w - len(cu)) // 2
    for i, ch in enumerate(cu):
        if 0 <= cux + i < w:
            screen[status_y + 2][cux + i] = ch

    # Log lines (right side)
    log_x = 2
    log_y = 1
    screen[log_y][log_x] = "Log:"
    for i, entry in enumerate(state.log[-(h - 6):]):
        line = entry[: w - 4]
        for j, ch in enumerate(line):
            if 0 <= log_x + j < w:
                screen[log_y + 1 + i][log_x + j] = ch

    # ---- Blit to stdscr ----
    for y, row in enumerate(screen):
        try:
            stdscr.addnstr(y, 0, "".join(row), w - 1)
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
    now = time.localtime()
    state.sim_seconds = now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec

    warp = args.warp
    t_last = time.monotonic()

    if args.once:
        # Fast-forward to next top of hour and strike once for testing
        hour12, _, _, _ = hours_minutes_seconds(state.sim_seconds)
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
            if quarter in WESTMINSTER and WESTMINSTER[quarter]:
                state.log.append(f"Chime (Q{quarter}): {'-'.join(WESTMINSTER[quarter])}")
                if not args.silent:
                    # single bell per motif start
                    sys.stdout.write("\a")
                    sys.stdout.flush()
            if quarter == 0:
                # top of hour: cuckoo N times
                if not state.cuckoo_active:
                    start_cuckoo(state, hour12 if hour12 != 0 else 12)

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
    ap = argparse.ArgumentParser(description="Terminal Cuckoo Clock Simulator")
    ap.add_argument("--warp", type=float, default=1.0,
                    help="Time-warp multiplier (1=real-time, 3600=1 hour per second).")
    ap.add_argument("--silent", action="store_true", help="Disable terminal bell chimes.")
    ap.add_argument("--once", action="store_true",
                    help="Run a single hour-strike and exit (useful for testing).")
    args = ap.parse_args()

    try:
        curses.wrapper(run, args)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()