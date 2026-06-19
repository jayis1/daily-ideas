#!/usr/bin/env python3
"""
Solar System Orrery — An animated terminal-based orrery showing planets
orbiting the Sun with real orbital data, zoom, speed controls, and
a "go to date" feature.
"""

import curses
import math
import time
from datetime import datetime, timedelta
import sys

# Orbital data: (name, semi_major_axis_AU, orbital_period_years, eccentricity, color_pair, symbol)
# Color pairs are assigned at runtime
PLANETS = [
    ("Mercury",  0.387,   0.241,  0.206, None, "☿"),
    ("Venus",    0.723,   0.615,  0.007, None, "♀"),
    ("Earth",    1.000,   1.000,  0.017, None, "🜨"),
    ("Mars",     1.524,   1.881,  0.093, None, "♂"),
    ("Jupiter",  5.203,  11.862,  0.049, None, "♃"),
    ("Saturn",   9.537,  29.457,  0.054, None, "♄"),
    ("Uranus",  19.191,  84.011,  0.047, None, "♅"),
    ("Neptune", 30.069, 164.800,  0.009, None, "♆"),
]

# Curses color mapping (planet_index -> curses color)
PLANET_COLORS = [
    curses.COLOR_WHITE,     # Mercury - gray
    curses.COLOR_YELLOW,    # Venus
    curses.COLOR_CYAN,      # Earth
    curses.COLOR_RED,       # Mars
    curses.COLOR_MAGENTA,   # Jupiter (brownish → magenta)
    curses.COLOR_GREEN,     # Saturn
    curses.COLOR_BLUE,      # Uranus
    curses.COLOR_RED,       # Neptune (deep blue → use red for visibility)
]


def solve_kepler(M, e, tol=1e-8):
    """Solve Kepler's equation M = E - e*sin(E) for E using Newton's method."""
    E = M
    for _ in range(100):
        dE = (M - E + e * math.sin(E)) / (1 - e * math.cos(E))
        E += dE
        if abs(dE) < tol:
            break
    return E


def planet_position(a, period, e, years_since_epoch):
    """Calculate (x, y) position in AU for a planet at a given time."""
    # Mean anomaly
    M = 2 * math.pi * years_since_epoch / period
    M = M % (2 * math.pi)
    # Eccentric anomaly
    E = solve_kepler(M, e)
    # True anomaly
    nu = 2 * math.atan2(
        math.sqrt(1 + e) * math.sin(E / 2),
        math.sqrt(1 - e) * math.cos(E / 2),
    )
    # Distance from focus
    r = a * (1 - e * math.cos(E))
    x = r * math.cos(nu)
    y = r * math.sin(nu)
    return x, y


def au_to_screen(x_au, y_au, cx, cy, scale, max_r):
    """Convert AU coordinates to screen coordinates."""
    # Use sqrt scaling for outer planets to compress the view
    # but keep inner planets readable
    r_au = math.sqrt(x_au**2 + y_au**2)
    if r_au == 0:
        return cx, cy

    # Apply power scaling to compress distances
    r_scaled = (r_au ** 0.55) * scale
    if r_scaled > max_r:
        r_scaled = max_r

    angle = math.atan2(y_au, x_au)
    sx = cx + r_scaled * math.cos(angle)
    sy = cy + r_scaled * math.sin(angle) * 0.5  # Squish Y for perspective feel

    return int(sx), int(sy)


def draw_orbit(stdscr, a, e, cx, cy, scale, max_r, color_pair):
    """Draw the orbital path of a planet."""
    steps = 120
    points = []
    for i in range(steps + 1):
        angle = 2 * math.pi * i / steps
        r_au = a * (1 - e**2) / (1 + e * math.cos(angle))
        x_au = r_au * math.cos(angle)
        y_au = r_au * math.sin(angle)
        sx, sy = au_to_screen(x_au, y_au, cx, cy, scale, max_r)
        points.append((sx, sy))

    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        # Draw a line segment using characters
        dx = x2 - x1
        dy = y2 - y1
        steps_seg = max(abs(dx), abs(dy), 1)
        for s in range(steps_seg + 1):
            px = int(x1 + dx * s / steps_seg)
            py = int(y1 + dy * s / steps_seg)
            try:
                stdscr.addch(py, px, ord('.'), color_pair | curses.A_DIM)
            except curses.error:
                pass


def draw_starfield(stdscr, height, width, star_cache):
    """Draw background stars."""
    for (sy, sx, ch) in star_cache:
        try:
            stdscr.addch(sy, sx, ord(ch), curses.color_pair(0) | curses.A_DIM)
        except curses.error:
            pass


def generate_stars(height, width, count=80):
    """Generate random star positions."""
    import random
    random.seed(42)
    stars = []
    chars = [".", "+", "*", "·"]
    for _ in range(count):
        sy = random.randint(0, height - 1)
        sx = random.randint(0, width - 1)
        ch = random.choice(chars)
        stars.append((sy, sx, ch))
    return stars


def format_date(dt):
    return dt.strftime("%Y-%m-%d")


class OrreryState:
    def __init__(self):
        self.current_date = datetime(2026, 1, 1)
        self.speed = 1.0  # days per frame
        self.paused = False
        self.selected_planet = 2  # Earth by default
        self.scale = 12.0
        self.show_orbits = True
        self.show_labels = True
        self.input_mode = None  # None, 'date', 'speed'
        self.input_buffer = ""
        self.trail_positions = {i: [] for i in range(len(PLANETS))}
        self.max_trail = 200


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(33)  # ~30 fps

    # Setup colors
    curses.start_color()
    curses.use_default_colors()
    # Pair 1 = Sun (bright yellow)
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    # Pairs 2..9 = planets
    for i, cc in enumerate(PLANET_COLORS):
        curses.init_pair(i + 2, cc, -1)
    # Pair 10 = UI text
    curses.init_pair(10, curses.COLOR_WHITE, -1)
    # Pair 11 = dim text
    curses.init_pair(11, curses.COLOR_WHITE, -1)
    # Pair 12 = highlight
    curses.init_pair(12, curses.COLOR_BLACK, curses.COLOR_WHITE)

    for i in range(len(PLANETS)):
        PLANETS[i] = (
            PLANETS[i][0],
            PLANETS[i][1],
            PLANETS[i][2],
            PLANETS[i][3],
            curses.color_pair(i + 2),
            PLANETS[i][5],
        )

    state = OrreryState()
    height, width = stdscr.getmaxyx()

    star_cache = generate_stars(height, width)

    last_time = time.time()
    epoch = datetime(2000, 1, 1)  # J2000 epoch

    while True:
        current_time = time.time()
        dt_frame = current_time - last_time
        last_time = current_time

        # Handle input
        key = stdscr.getch()

        if state.input_mode == 'date':
            if key == 10 or key == 13:  # Enter
                try:
                    state.current_date = datetime.strptime(state.input_buffer, "%Y-%m-%d")
                except ValueError:
                    pass
                state.input_mode = None
                state.input_buffer = ""
            elif key == 27:  # Escape
                state.input_mode = None
                state.input_buffer = ""
            elif key == curses.KEY_BACKSPACE or key == 127:
                state.input_buffer = state.input_buffer[:-1]
            elif key >= 32 and key < 127:
                state.input_buffer += chr(key)
        elif state.input_mode == 'speed':
            if key == 10 or key == 13:
                try:
                    state.speed = float(state.input_buffer)
                except ValueError:
                    pass
                state.input_mode = None
                state.input_buffer = ""
            elif key == 27:
                state.input_mode = None
                state.input_buffer = ""
            elif key == curses.KEY_BACKSPACE or key == 127:
                state.input_buffer = state.input_buffer[:-1]
            elif key >= 32 and key < 127:
                state.input_buffer += chr(key)
        else:
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord(' '):
                state.paused = not state.paused
            elif key == ord('+') or key == ord('='):
                state.speed = min(state.speed * 1.5, 3650)
            elif key == ord('-'):
                state.speed = max(state.speed / 1.5, 0.01)
            elif key == ord('o'):
                state.show_orbits = not state.show_orbits
            elif key == ord('l'):
                state.show_labels = not state.show_labels
            elif key == ord('t'):
                # Toggle trails
                if state.trail_positions[0]:
                    state.trail_positions = {i: [] for i in range(len(PLANETS))}
                else:
                    pass  # trails will accumulate
            elif key == ord('d'):
                state.input_mode = 'date'
                state.input_buffer = ""
            elif key == ord('s'):
                state.input_mode = 'speed'
                state.input_buffer = ""
            elif key == curses.KEY_UP:
                state.scale = min(state.scale * 1.2, 80)
            elif key == curses.KEY_DOWN:
                state.scale = max(state.scale / 1.2, 3)
            elif key == curses.KEY_LEFT:
                state.selected_planet = (state.selected_planet - 1) % len(PLANETS)
            elif key == curses.KEY_RIGHT:
                state.selected_planet = (state.selected_planet + 1) % len(PLANETS)
            elif key == ord('r'):
                # Reset
                state.current_date = datetime(2026, 1, 1)
                state.speed = 1.0
                state.trail_positions = {i: [] for i in range(len(PLANETS))}

        # Update time
        if not state.paused:
            state.current_date += timedelta(days=state.speed * dt_frame * 30)
            # Keep trail
            years_since_epoch = (state.current_date - epoch).total_seconds() / (365.25 * 24 * 3600)
            for i, (name, a, period, e, cp, sym) in enumerate(PLANETS):
                x, y = planet_position(a, period, e, years_since_epoch)
                state.trail_positions[i].append((x, y))
                if len(state.trail_positions[i]) > state.max_trail:
                    state.trail_positions[i].pop(0)

        # Get dimensions (may have changed)
        height, width = stdscr.getmaxyx()
        stdscr.clear()

        cx = width // 2
        cy = height // 2

        # Regenerate stars on resize
        star_cache = generate_stars(height, width)
        draw_starfield(stdscr, height, width, star_cache)

        years_since_epoch = (state.current_date - epoch).total_seconds() / (365.25 * 24 * 3600)
        max_r = min(cx, cy) - 2

        # Draw orbits
        if state.show_orbits:
            for i, (name, a, period, e, cp, sym) in enumerate(PLANETS):
                draw_orbit(stdscr, a, e, cx, cy, state.scale, max_r, cp)

        # Draw Sun
        sun_ch = "☀"
        try:
            stdscr.addstr(cy, cx, sun_ch, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            stdscr.addch(cy, cx, ord('*'), curses.color_pair(1) | curses.A_BOLD)

        # Draw planets
        planet_info = []
        for i, (name, a, period, e, cp, sym) in enumerate(PLANETS):
            x, y = planet_position(a, period, e, years_since_epoch)
            sx, sy = au_to_screen(x, y, cx, cy, state.scale, max_r)
            planet_info.append((name, a, period, e, cp, sym, x, y, sx, sy))

            # Draw trail
            trail = state.trail_positions[i]
            if len(trail) > 1:
                for j, (tx, ty) in enumerate(trail):
                    tsx, tsy = au_to_screen(tx, ty, cx, cy, state.scale, max_r)
                    brightness = int(j / len(trail) * 8) + 1
                    trail_ch = "."
                    try:
                        stdscr.addch(tsy, tsx, ord(trail_ch), cp | curses.A_DIM)
                    except curses.error:
                        pass

            # Draw planet
            ch = sym
            try:
                stdscr.addstr(sy, sx, ch, cp | curses.A_BOLD)
            except curses.error:
                try:
                    stdscr.addch(sy, sx, ord(name[0]), cp | curses.A_BOLD)
                except curses.error:
                    pass

            # Label
            if state.show_labels and sy > 0 and sy < height - 1:
                label = name[:3]
                lx = sx + 2
                ly = sy
                if lx + len(label) < width:
                    try:
                        attr = cp
                        if i == state.selected_planet:
                            attr = cp | curses.A_REVERSE
                        stdscr.addstr(ly, lx, label, attr)
                    except curses.error:
                        pass

        # --- Info Panel ---
        panel_x = 1
        panel_y = 1

        sel = state.selected_planet
        sel_name, sel_a, sel_period, sel_e, sel_cp, sel_sym, sel_x, sel_y, _, _ = planet_info[sel]

        lines = [
            f"╔══ Solar System Orrery ══╗",
            f"  Date: {format_date(state.current_date)}",
            f"  Speed: {state.speed:.2f} days/frame",
            f"  {'PAUSED' if state.paused else 'RUNNING'}",
            f"╠════════════════════════╣",
            f"  Planet: {sel_name}",
            f"  Distance: {sel_a:.3f} AU",
            f"  Period: {sel_period:.3f} years",
            f"  Eccentricity: {sel_e:.3f}",
            f"  Position: ({sel_x:+.2f}, {sel_y:+.2f}) AU",
            f"╚════════════════════════╝",
        ]

        for idx, line in enumerate(lines):
            if panel_y + idx < height - 1:
                try:
                    stdscr.addstr(panel_y + idx, panel_x, line, curses.color_pair(10))
                except curses.error:
                    pass

        # --- Controls ---
        controls_y = height - 3
        controls = "SPACE:Pause  +/-:Speed  ↑↓:Zoom  ←→:Planet  O:Orbits  L:Labels  T:Trails  D:Date  S:SetSpeed  R:Reset  Q:Quit"
        if controls_y > 0:
            try:
                stdscr.addstr(controls_y, 1, controls[:width-2], curses.color_pair(10) | curses.A_DIM)
            except curses.error:
                pass

        # Input mode
        if state.input_mode == 'date':
            prompt = f"Go to date (YYYY-MM-DD): {state.input_buffer}_"
            try:
                stdscr.addstr(cy + max_r + 2, cx - len(prompt)//2, prompt, curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass
        elif state.input_mode == 'speed':
            prompt = f"Speed (days/frame): {state.input_buffer}_"
            try:
                stdscr.addstr(cy + max_r + 2, cx - len(prompt)//2, prompt, curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

        stdscr.refresh()

    curses.curs_set(1)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass