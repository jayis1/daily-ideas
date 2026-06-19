#!/usr/bin/env python3
"""
Solar System Orrery — An animated terminal-based orrery showing planets
orbiting the Sun with real orbital data, zoom, speed controls, and
a "go to date" feature.

Bug fixes from v1.0:
- generate_stars() no longer crashes on zero/negative-dimension terminals
- generate_stars() only regenerated on resize, not every frame
- Trail toggle now uses a proper show_trails boolean (press T to toggle on/off)
- Speed input now validates for positive values only
- planet_position() handles zero/negative period gracefully
- ASCII fallback for planet symbols when terminal lacks UTF-8 support
- Info panel lines are truncated to fit terminal width
- Controls bar truncated safely for narrow terminals
"""

import curses
import math
import time
from datetime import datetime, timedelta
import sys

# Orbital data: (name, semi_major_axis_AU, orbital_period_years, eccentricity, symbol)
# Symbols are ASCII-safe; Unicode symbols used as display names separately
PLANETS = [
    ("Mercury",  0.387,   0.241,  0.206, "Me"),
    ("Venus",    0.723,   0.615,  0.007, "Ve"),
    ("Earth",    1.000,   1.000,  0.017, "Ea"),
    ("Mars",     1.524,   1.881,  0.093, "Ma"),
    ("Jupiter",  5.203,  11.862,  0.049, "Ju"),
    ("Saturn",   9.537,  29.457,  0.054, "Sa"),
    ("Uranus",  19.191,  84.011,  0.047, "Ur"),
    ("Neptune", 30.069, 164.800,  0.009, "Ne"),
]

# Unicode display symbols — used with fallback to ASCII symbols above
PLANET_SYMBOLS_UNICODE = ["☿", "♀", "⊕", "♂", "♃", "♄", "♅", "♆"]

# Curses color mapping (planet_index -> curses color)
PLANET_COLORS = [
    curses.COLOR_WHITE,     # Mercury - gray
    curses.COLOR_YELLOW,    # Venus
    curses.COLOR_CYAN,      # Earth
    curses.COLOR_RED,       # Mars
    curses.COLOR_MAGENTA,   # Jupiter (brownish → magenta)
    curses.COLOR_GREEN,     # Saturn
    curses.COLOR_BLUE,      # Uranus
    curses.COLOR_RED,       # Neptune (deep blue → red for visibility)
]


def solve_kepler(M, e, tol=1e-8):
    """Solve Kepler's equation M = E - e*sin(E) for E using Newton's method.

    Args:
        M: Mean anomaly (radians)
        e: Eccentricity (must be 0 <= e < 1 for elliptical orbits)
        tol: Convergence tolerance

    Returns:
        Eccentric anomaly E (radians)

    Raises:
        ValueError: If e >= 1 (not an elliptical orbit)
    """
    if e >= 1.0:
        raise ValueError(f"Eccentricity {e} >= 1.0 is not valid for elliptical orbits")
    if e < 0:
        raise ValueError(f"Eccentricity {e} is negative")
    E = M
    for _ in range(100):
        denom = 1 - e * math.cos(E)
        if abs(denom) < 1e-15:
            break
        dE = (M - E + e * math.sin(E)) / denom
        E += dE
        if abs(dE) < tol:
            break
    return E


def planet_position(a, period, e, years_since_epoch):
    """Calculate (x, y) position in AU for a planet at a given time.

    Args:
        a: Semi-major axis in AU (must be > 0)
        period: Orbital period in years (must be > 0)
        e: Eccentricity (must be 0 <= e < 1)
        years_since_epoch: Time since J2000 epoch in years

    Returns:
        Tuple (x, y) in AU

    Raises:
        ValueError: If period <= 0 or a <= 0 or e >= 1
    """
    if period <= 0:
        raise ValueError(f"Orbital period must be > 0, got {period}")
    if a <= 0:
        raise ValueError(f"Semi-major axis must be > 0, got {a}")

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
    """Convert AU coordinates to screen coordinates.

    Uses power scaling to compress distances so both inner and outer
    planets are visible simultaneously.
    """
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


def draw_orbit(stdscr, a, e, cx, cy, scale, max_r, color_pair, height, width):
    """Draw the orbital path of a planet.

    Args:
        stdscr: Curses window
        a, e: Orbital parameters
        cx, cy: Center coordinates
        scale, max_r: Scaling parameters
        color_pair: Curses color pair
        height, width: Terminal dimensions for bounds checking
    """
    steps = 120
    points = []
    for i in range(steps + 1):
        angle = 2 * math.pi * i / steps
        r_au = a * (1 - e**2) / (1 + e * math.cos(angle))
        x_au = r_au * math.cos(angle)
        y_au = r_au * math.sin(angle)
        sx, sy = au_to_screen(x_au, y_au, cx, cy, scale, max_r)
        # Skip points that are clearly off-screen
        if 0 <= sy < height and 0 <= sx < width:
            points.append((sx, sy))
        elif points:
            # We had on-screen points before going off-screen; keep the boundary point
            # to avoid gaps, but clamp to screen
            points.append((max(0, min(width - 1, sx)), max(0, min(height - 1, sy))))

    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        dx = x2 - x1
        dy = y2 - y1
        steps_seg = max(abs(dx), abs(dy), 1)
        for s in range(steps_seg + 1):
            px = int(x1 + dx * s / steps_seg)
            py = int(y1 + dy * s / steps_seg)
            if 0 <= py < height and 0 <= px < width:
                try:
                    stdscr.addch(py, px, ord('.'), color_pair | curses.A_DIM)
                except curses.error:
                    pass


def draw_starfield(stdscr, height, width, star_cache):
    """Draw background stars."""
    for (sy, sx, ch) in star_cache:
        if 0 <= sy < height and 0 <= sx < width:
            try:
                stdscr.addch(sy, sx, ord(ch), curses.color_pair(0) | curses.A_DIM)
            except curses.error:
                pass


def generate_stars(height, width, count=80):
    """Generate random star positions.

    Handles edge cases gracefully: if terminal is too small, generates
    fewer stars to avoid over-drawing. Returns an empty list for
    degenerate (zero/negative) dimensions.

    Args:
        height: Terminal height in rows
        width: Terminal width in columns
        count: Desired number of stars (reduced for small terminals)

    Returns:
        List of (row, col, char) tuples
    """
    if height <= 0 or width <= 0:
        return []

    import random
    random.seed(42)
    # Reduce star count for very small terminals to avoid clutter
    actual_count = min(count, max(1, (height * width) // 10))
    stars = []
    chars = [".", "+", "*", "·"]
    for _ in range(actual_count):
        sy = random.randint(0, height - 1)
        sx = random.randint(0, width - 1)
        ch = random.choice(chars)
        stars.append((sy, sx, ch))
    return stars


def format_date(dt):
    """Format a datetime as YYYY-MM-DD."""
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
        self.show_trails = True  # BUG FIX: proper trail toggle
        self.input_mode = None  # None, 'date', 'speed'
        self.input_buffer = ""
        self.trail_positions = {i: [] for i in range(len(PLANETS))}
        self.max_trail = 200


def safe_addstr(stdscr, y, x, text, attr, height, width):
    """Safely add a string to the screen, respecting terminal bounds.

    Returns True if the string was drawn, False if it was out of bounds.
    """
    if y < 0 or y >= height or x < 0 or x >= width:
        return False
    # Truncate text to fit within terminal width
    max_len = width - x
    if max_len <= 0:
        return False
    text = text[:max_len]
    try:
        stdscr.addstr(y, x, text, attr)
        return True
    except curses.error:
        return False


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
    # Pair 11 = dim text (same as 10 but used conceptually)
    curses.init_pair(11, curses.COLOR_WHITE, -1)
    # Pair 12 = highlight
    curses.init_pair(12, curses.COLOR_BLACK, curses.COLOR_WHITE)

    # Build runtime planet data with color pairs assigned
    planet_data = []
    for i, (name, a, period, e, sym) in enumerate(PLANETS):
        cp = curses.color_pair(i + 2)
        unicode_sym = PLANET_SYMBOLS_UNICODE[i] if i < len(PLANET_SYMBOLS_UNICODE) else sym
        planet_data.append((name, a, period, e, sym, cp, unicode_sym))

    state = OrreryState()
    height, width = stdscr.getmaxyx()

    # BUG FIX: Generate stars only once initially, and on resize
    star_cache = generate_stars(height, width)
    last_height, last_width = height, width

    last_time = time.time()
    epoch = datetime(2000, 1, 1)  # J2000 epoch

    while True:
        current_time = time.time()
        dt_frame = current_time - last_time
        last_time = current_time

        # Cap dt_frame to avoid huge jumps if window was hidden
        dt_frame = min(dt_frame, 0.5)

        # Handle input
        key = stdscr.getch()

        if state.input_mode == 'date':
            if key == 10 or key == 13:  # Enter
                try:
                    new_date = datetime.strptime(state.input_buffer, "%Y-%m-%d")
                    # Validate date is reasonable (year 1-9999)
                    if new_date.year < 1 or new_date.year > 9999:
                        pass  # Invalid date range, ignore
                    else:
                        state.current_date = new_date
                except ValueError:
                    pass  # Invalid format, ignore
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
                    new_speed = float(state.input_buffer)
                    # BUG FIX: validate speed is positive
                    if new_speed > 0:
                        state.speed = min(new_speed, 3650)
                except ValueError:
                    pass  # Invalid number, ignore
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
                # BUG FIX: proper toggle — clear trails and toggle accumulation
                if state.show_trails:
                    # Trails were on, turn them off and clear
                    state.show_trails = False
                    state.trail_positions = {i: [] for i in range(len(PLANETS))}
                else:
                    # Trails were off, turn them on (will accumulate)
                    state.show_trails = True
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
                state.selected_planet = (state.selected_planet - 1) % len(planet_data)
            elif key == curses.KEY_RIGHT:
                state.selected_planet = (state.selected_planet + 1) % len(planet_data)
            elif key == ord('r'):
                # Reset
                state.current_date = datetime(2026, 1, 1)
                state.speed = 1.0
                state.trail_positions = {i: [] for i in range(len(PLANETS))}
                state.show_trails = True

        # Update time
        if not state.paused:
            state.current_date += timedelta(days=state.speed * dt_frame * 30)
            # Keep trail (only if trails are enabled)
            if state.show_trails:
                years_since_epoch = (state.current_date - epoch).total_seconds() / (365.25 * 24 * 3600)
                for i, (name, a, period, e, sym, cp, usym) in enumerate(planet_data):
                    x, y = planet_position(a, period, e, years_since_epoch)
                    state.trail_positions[i].append((x, y))
                    if len(state.trail_positions[i]) > state.max_trail:
                        state.trail_positions[i].pop(0)

        # Get dimensions (may have changed)
        height, width = stdscr.getmaxyx()

        # BUG FIX: Only regenerate stars on resize
        if height != last_height or width != last_width:
            star_cache = generate_stars(height, width)
            last_height, last_width = height, width

        stdscr.clear()

        cx = width // 2
        cy = height // 2

        draw_starfield(stdscr, height, width, star_cache)

        years_since_epoch = (state.current_date - epoch).total_seconds() / (365.25 * 24 * 3600)
        max_r = min(cx, cy) - 2

        # Draw orbits
        if state.show_orbits and max_r > 0:
            for i, (name, a, period, e, sym, cp, usym) in enumerate(planet_data):
                draw_orbit(stdscr, a, e, cx, cy, state.scale, max_r, cp, height, width)

        # Draw Sun
        if 0 <= cy < height and 0 <= cx < width:
            sun_str = "☀"
            try:
                stdscr.addstr(cy, cx, sun_str, curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                try:
                    stdscr.addch(cy, cx, ord('*'), curses.color_pair(1) | curses.A_BOLD)
                except curses.error:
                    pass

        # Draw planets
        planet_info = []
        for i, (name, a, period, e, sym, cp, usym) in enumerate(planet_data):
            x, y = planet_position(a, period, e, years_since_epoch)
            sx, sy = au_to_screen(x, y, cx, cy, state.scale, max_r)
            planet_info.append((name, a, period, e, sym, cp, usym, x, y, sx, sy))

            # Draw trail
            if state.show_trails:
                trail = state.trail_positions[i]
                if len(trail) > 1:
                    for j, (tx, ty) in enumerate(trail):
                        tsx, tsy = au_to_screen(tx, ty, cx, cy, state.scale, max_r)
                        if 0 <= tsy < height and 0 <= tsx < width:
                            try:
                                stdscr.addch(tsy, tsx, ord('.'), cp | curses.A_DIM)
                            except curses.error:
                                pass

            # Draw planet symbol (try Unicode first, fall back to ASCII)
            if 0 <= sy < height and 0 <= sx < width:
                try:
                    stdscr.addstr(sy, sx, usym, cp | curses.A_BOLD)
                except (curses.error, UnicodeEncodeError):
                    try:
                        stdscr.addstr(sy, sx, sym, cp | curses.A_BOLD)
                    except curses.error:
                        pass

            # Label
            if state.show_labels and 0 < sy < height - 1:
                label = name[:3]
                lx = sx + 2
                ly = sy
                attr = cp
                if i == state.selected_planet:
                    attr = cp | curses.A_REVERSE
                if lx + len(label) < width:
                    try:
                        stdscr.addstr(ly, lx, label, attr)
                    except curses.error:
                        pass

        # --- Info Panel ---
        panel_x = 1
        panel_y = 1

        sel = state.selected_planet
        sel_name, sel_a, sel_period, sel_e, sel_sym, sel_cp, sel_usym, sel_x, sel_y, _, _ = planet_info[sel]

        trail_status = "ON" if state.show_trails else "OFF"
        lines = [
            f"╔══ Solar System Orrery ══╗",
            f"  Date: {format_date(state.current_date)}",
            f"  Speed: {state.speed:.2f} days/frame",
            f"  {'PAUSED' if state.paused else 'RUNNING'}  Trails: {trail_status}",
            f"╠════════════════════════╣",
            f"  Planet: {sel_name}",
            f"  Distance: {sel_a:.3f} AU",
            f"  Period: {sel_period:.3f} years",
            f"  Eccentricity: {sel_e:.3f}",
            f"  Position: ({sel_x:+.2f}, {sel_y:+.2f}) AU",
            f"╚════════════════════════╝",
        ]

        for idx, line in enumerate(lines):
            row = panel_y + idx
            if 0 <= row < height - 1:
                safe_addstr(stdscr, row, panel_x, line, curses.color_pair(10), height, width)

        # --- Controls ---
        controls_y = height - 2
        controls = "SPC:Pause +/-:Speed ↑↓:Zoom ←→:Planet O:Orbits L:Labels T:Trails D:Date S:SetSpeed R:Reset Q:Quit"
        if controls_y > 0:
            safe_addstr(stdscr, controls_y, 1, controls, curses.color_pair(10) | curses.A_DIM, height, width)

        # Input mode
        if state.input_mode == 'date':
            prompt = f"Go to date (YYYY-MM-DD): {state.input_buffer}_"
            prompt_y = min(cy + max_r + 2, height - 3)
            safe_addstr(stdscr, prompt_y, max(0, cx - len(prompt) // 2), prompt, curses.color_pair(1) | curses.A_BOLD, height, width)
        elif state.input_mode == 'speed':
            prompt = f"Speed (days/frame, >0): {state.input_buffer}_"
            prompt_y = min(cy + max_r + 2, height - 3)
            safe_addstr(stdscr, prompt_y, max(0, cx - len(prompt) // 2), prompt, curses.color_pair(1) | curses.A_BOLD, height, width)

        stdscr.refresh()

    curses.curs_set(1)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass