#!/usr/bin/env python3
"""
Solar System Orrery — An animated terminal-based orrery showing planets
orbiting the Sun with real orbital data, zoom, speed controls, conjunction
alerts, Earth's Moon, an asteroid belt, and a "go to date" feature.

Enhancements from v1.0:
- generate_stars() no longer crashes on zero/negative-dimension terminals
- generate_stars() only regenerated on resize, not every frame
- Trail toggle now uses a proper show_trails boolean
- Speed input validates for positive values only
- planet_position() handles zero/negative period gracefully
- ASCII fallback for planet symbols when terminal lacks UTF-8 support
- Info panel lines are truncated to fit terminal width
- Controls bar truncated safely for narrow terminals
- Frame time cap to prevent jumps on window hide/minimize
- draw_orbit() bounds checking

Enhancements from v2.0:
- Added --help and --version CLI flags
- Conjunction detection: alerts when two planets are within 5° of each other
- Earth's Moon displayed as a small dot orbiting Earth
- Asteroid belt visualization between Mars and Jupiter (toggle with A)
- Jump to today's date with H key
- Info panel shows live distance from Sun and orbital velocity
- Improved code documentation with type hints

Bug fixes from v2.1:
- Fixed speed label: was "days/frame", now correctly "days/sec"
- Fixed label rendering off-by-one: labels that exactly fit at terminal
  right edge were incorrectly skipped
- Fixed conjunction detection degenerate case: planets at origin (0,0) no
  longer cause false conjunctions with atan2(0,0)=0
- Fixed Unicode rendering: planet symbols and Sun character now check for
  wide character overflow at terminal right edge, falling back to ASCII
- Fixed key bindings: all letter keys now accept both uppercase and lowercase
  (previously only 'q/Q' worked with both cases)
- Fixed Moon overlap: Moon display radius minimum raised from 1 to 2 screen
  units to prevent overlapping with Earth on small terminals
- Speed property now validates and clamps values (0.01–3650) on assignment
- Removed unused height/width parameters from generate_asteroids()
- Added underscore key '_' as alias for '-' (slow down) for keyboard
  convenience
"""

import argparse
import curses
import math
import random
import time
from datetime import datetime, timedelta
import sys

__version__ = "2.1.0"

# J2000 epoch reference date
J2000_EPOCH = datetime(2000, 1, 1)

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

# Moon parameters: orbital radius in AU, period in years
MOON_ORBITAL_RADIUS_AU = 0.00257  # ~384,400 km
MOON_PERIOD_YEARS = 0.0748  # ~27.3 days

# Asteroid belt parameters
ASTEROID_BELT_INNER_AU = 2.1   # Inner edge (roughly Mars-Jupiter gap)
ASTEROID_BELT_OUTER_AU = 3.3   # Outer edge
ASTEROID_BELT_COUNT = 60        # Number of asteroid dots

# Conjunction detection threshold in degrees
CONJUNCTION_THRESHOLD_DEG = 5.0


def solve_kepler(M: float, e: float, tol: float = 1e-8) -> float:
    """Solve Kepler's equation M = E - e*sin(E) for E using Newton's method.

    Args:
        M: Mean anomaly (radians)
        e: Eccentricity (must be 0 <= e < 1 for elliptical orbits)
        tol: Convergence tolerance

    Returns:
        Eccentric anomaly E (radians)

    Raises:
        ValueError: If e >= 1 (not an elliptical orbit) or e < 0
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


def planet_position(a: float, period: float, e: float, years_since_epoch: float) -> tuple:
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


def orbital_velocity_km_s(a: float, period: float, r: float) -> float:
    """Calculate orbital velocity at a given distance from the Sun.

    Uses the vis-viva equation: v = sqrt(GM * (2/r - 1/a))
    where GM_sun ≈ 1.327e11 km³/s² and distances are converted from AU.

    Args:
        a: Semi-major axis in AU
        period: Orbital period in years (unused, kept for API consistency)
        r: Current distance from Sun in AU

    Returns:
        Velocity in km/s
    """
    GM_SUN = 1.32712440018e11  # km³/s²
    AU_KM = 1.496e8  # km per AU
    a_km = a * AU_KM
    r_km = r * AU_KM
    if r_km <= 0 or a_km <= 0:
        return 0.0
    v2 = GM_SUN * (2.0 / r_km - 1.0 / a_km)
    if v2 < 0:
        return 0.0
    return math.sqrt(v2)


def detect_conjunctions(planet_positions: list, threshold_deg: float = CONJUNCTION_THRESHOLD_DEG) -> list:
    """Detect conjunctions (close angular separations) between planets.

    Args:
        planet_positions: List of (x, y) tuples for each planet in AU
        threshold_deg: Angular threshold in degrees for conjunction detection

    Returns:
        List of (planet_i, planet_j, angular_separation_deg) tuples
    """
    conjunctions = []
    for i in range(len(planet_positions)):
        for j in range(i + 1, len(planet_positions)):
            x1, y1 = planet_positions[i]
            x2, y2 = planet_positions[j]
            # Skip if either planet is at the origin (degenerate case)
            if (x1 == 0 and y1 == 0) or (x2 == 0 and y2 == 0):
                continue
            # Angle of each planet from Sun (origin)
            angle1 = math.atan2(y1, x1)
            angle2 = math.atan2(y2, x2)
            # Angular separation (shortest arc)
            diff = abs(angle1 - angle2)
            if diff > math.pi:
                diff = 2 * math.pi - diff
            diff_deg = math.degrees(diff)
            if diff_deg < threshold_deg:
                conjunctions.append((i, j, diff_deg))
    return conjunctions


def au_to_screen(x_au: float, y_au: float, cx: int, cy: int, scale: float, max_r: int) -> tuple:
    """Convert AU coordinates to screen coordinates.

    Uses power scaling to compress distances so both inner and outer
    planets are visible simultaneously.

    Args:
        x_au, y_au: Position in AU
        cx, cy: Screen center coordinates
        scale: Scale factor
        max_r: Maximum screen radius

    Returns:
        Tuple (screen_x, screen_y) as integers
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


def draw_orbit(stdscr, a: float, e: float, cx: int, cy: int,
               scale: float, max_r: int, color_pair, height: int, width: int):
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


def generate_asteroids(seed: int = 12345) -> list:
    """Generate asteroid belt positions as (angle_fraction, radius_fraction, size_char).

    Each asteroid is stored as a fraction of its orbital position so it can be
    animated. The angle_fraction is [0, 1) representing position around the orbit,
    and radius_fraction is [0, 1) between inner and outer belt edge.

    Args:
        seed: Random seed for deterministic generation

    Returns:
        List of (angle_fraction, radius_fraction, angular_speed, char) tuples
    """
    rng = random.Random(seed)
    asteroids = []
    chars = [".", ","]
    for _ in range(ASTEROID_BELT_COUNT):
        angle_frac = rng.random()  # 0-1 around the orbit
        radius_frac = rng.random()  # 0-1 between inner and outer edge
        # Angular speed varies slightly (Kepler's third law approximation)
        radius_au = ASTEROID_BELT_INNER_AU + radius_frac * (ASTEROID_BELT_OUTER_AU - ASTEROID_BELT_INNER_AU)
        period_years = radius_au ** 1.5  # Kepler's third law: T² ∝ a³
        angular_speed = 1.0 / period_years  # revolutions per year
        char = rng.choice(chars)
        asteroids.append((angle_frac, radius_frac, angular_speed, char))
    return asteroids


def draw_asteroid_belt(stdscr, asteroids: list, years_since_epoch: float,
                       cx: int, cy: int, scale: float, max_r: int,
                       height: int, width: int):
    """Draw the asteroid belt on screen.

    Args:
        stdscr: Curses window
        asteroids: List of asteroid tuples from generate_asteroids()
        years_since_epoch: Current simulation time
        cx, cy: Screen center
        scale, max_r: Scaling parameters
        height, width: Terminal dimensions
    """
    for angle_frac, radius_frac, angular_speed, char in asteroids:
        # Compute current angle based on time and speed
        current_angle = (angle_frac + angular_speed * years_since_epoch) * 2 * math.pi
        # Interpolate radius between inner and outer edge
        radius_au = ASTEROID_BELT_INNER_AU + radius_frac * (ASTEROID_BELT_OUTER_AU - ASTEROID_BELT_INNER_AU)
        x_au = radius_au * math.cos(current_angle)
        y_au = radius_au * math.sin(current_angle)
        sx, sy = au_to_screen(x_au, y_au, cx, cy, scale, max_r)
        if 0 <= sy < height and 0 <= sx < width:
            try:
                stdscr.addch(sy, sx, ord(char), curses.color_pair(0) | curses.A_DIM)
            except curses.error:
                pass


def draw_starfield(stdscr, height: int, width: int, star_cache: list):
    """Draw background stars.

    Args:
        stdscr: Curses window
        height: Terminal height
        width: Terminal width
        star_cache: List of (row, col, char) tuples from generate_stars()
    """
    for (sy, sx, ch) in star_cache:
        if 0 <= sy < height and 0 <= sx < width:
            try:
                stdscr.addch(sy, sx, ord(ch), curses.color_pair(0) | curses.A_DIM)
            except curses.error:
                pass


def generate_stars(height: int, width: int, count: int = 80) -> list:
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

    rng = random.Random(42)
    # Reduce star count for very small terminals to avoid clutter
    actual_count = min(count, max(1, (height * width) // 10))
    stars = []
    chars = [".", "+", "*", "·"]
    for _ in range(actual_count):
        sy = rng.randint(0, height - 1)
        sx = rng.randint(0, width - 1)
        ch = rng.choice(chars)
        stars.append((sy, sx, ch))
    return stars


def format_date(dt: datetime) -> str:
    """Format a datetime as YYYY-MM-DD."""
    return dt.strftime("%Y-%m-%d")


class OrreryState:
    """Tracks the current state of the orrery simulation."""

    def __init__(self):
        self.current_date = datetime(2026, 1, 1)
        self._speed = 1.0  # days per second (at ~30fps)
        self.paused = False
        self.selected_planet = 2  # Earth by default
        self.scale = 12.0
        self.show_orbits = True
        self.show_labels = True
        self.show_trails = True
        self.show_asteroids = False  # New: asteroid belt toggle
        self.show_moon = True  # New: show Earth's Moon
        self.input_mode = None  # None, 'date', 'speed'
        self.input_buffer = ""
        self.trail_positions = {i: [] for i in range(len(PLANETS))}
        self.max_trail = 200
        self.conjunctions = []  # Current conjunction alerts

    @property
    def speed(self):
        """Get the current simulation speed in days/second."""
        return self._speed

    @speed.setter
    def speed(self, value):
        """Set the simulation speed, clamping to valid range."""
        self._speed = max(0.01, min(value, 3650))


def safe_addstr(stdscr, y: int, x: int, text: str, attr, height: int, width: int) -> bool:
    """Safely add a string to the screen, respecting terminal bounds.

    Args:
        stdscr: Curses window
        y, x: Row and column to start drawing at
        text: String to draw
        attr: Curses attribute (color, bold, etc.)
        height, width: Terminal dimensions

    Returns:
        True if the string was drawn, False if out of bounds
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
    """Main curses event loop for the orrery."""
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
    # Pair 13 = conjunction alert (bright red)
    curses.init_pair(13, curses.COLOR_RED, -1)

    # Build runtime planet data with color pairs assigned
    planet_data = []
    for i, (name, a, period, e, sym) in enumerate(PLANETS):
        cp = curses.color_pair(i + 2)
        unicode_sym = PLANET_SYMBOLS_UNICODE[i] if i < len(PLANET_SYMBOLS_UNICODE) else sym
        planet_data.append((name, a, period, e, sym, cp, unicode_sym))

    state = OrreryState()
    height, width = stdscr.getmaxyx()

    # Generate stars only once initially, and on resize
    star_cache = generate_stars(height, width)
    last_height, last_width = height, width

    # Generate asteroid belt (deterministic)
    asteroids = generate_asteroids()

    last_time = time.time()

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
            elif key == ord('-') or key == ord('_'):
                state.speed = max(state.speed / 1.5, 0.01)
            elif key == ord('o') or key == ord('O'):
                state.show_orbits = not state.show_orbits
            elif key == ord('l') or key == ord('L'):
                state.show_labels = not state.show_labels
            elif key == ord('t') or key == ord('T'):
                # Toggle trail accumulation — clear trails when turning off
                if state.show_trails:
                    state.show_trails = False
                    state.trail_positions = {i: [] for i in range(len(PLANETS))}
                else:
                    state.show_trails = True
            elif key == ord('a') or key == ord('A'):
                # Toggle asteroid belt
                state.show_asteroids = not state.show_asteroids
            elif key == ord('m') or key == ord('M'):
                # Toggle Moon
                state.show_moon = not state.show_moon
            elif key == ord('d') or key == ord('D'):
                state.input_mode = 'date'
                state.input_buffer = ""
            elif key == ord('s') or key == ord('S'):
                state.input_mode = 'speed'
                state.input_buffer = ""
            elif key == ord('h') or key == ord('H'):
                # Jump to today's date
                state.current_date = datetime.now()
            elif key == curses.KEY_UP:
                state.scale = min(state.scale * 1.2, 80)
            elif key == curses.KEY_DOWN:
                state.scale = max(state.scale / 1.2, 3)
            elif key == curses.KEY_LEFT:
                state.selected_planet = (state.selected_planet - 1) % len(planet_data)
            elif key == curses.KEY_RIGHT:
                state.selected_planet = (state.selected_planet + 1) % len(planet_data)
            elif key == ord('r') or key == ord('R'):
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
                years_since_epoch = (state.current_date - J2000_EPOCH).total_seconds() / (365.25 * 24 * 3600)
                for i, (name, a, period, e, sym, cp, usym) in enumerate(planet_data):
                    x, y = planet_position(a, period, e, years_since_epoch)
                    state.trail_positions[i].append((x, y))
                    if len(state.trail_positions[i]) > state.max_trail:
                        state.trail_positions[i].pop(0)

        # Get dimensions (may have changed)
        height, width = stdscr.getmaxyx()

        # Only regenerate stars on resize
        if height != last_height or width != last_width:
            star_cache = generate_stars(height, width)
            last_height, last_width = height, width

        stdscr.clear()

        cx = width // 2
        cy = height // 2

        draw_starfield(stdscr, height, width, star_cache)

        years_since_epoch = (state.current_date - J2000_EPOCH).total_seconds() / (365.25 * 24 * 3600)
        max_r = min(cx, cy) - 2

        # Draw orbits
        if state.show_orbits and max_r > 0:
            for i, (name, a, period, e, sym, cp, usym) in enumerate(planet_data):
                draw_orbit(stdscr, a, e, cx, cy, state.scale, max_r, cp, height, width)

        # Draw asteroid belt
        if state.show_asteroids and max_r > 0:
            draw_asteroid_belt(stdscr, asteroids, years_since_epoch, cx, cy,
                             state.scale, max_r, height, width)

        # Draw Sun
        if 0 <= cy < height and 0 <= cx < width:
            sun_str = "☀"
            # Sun symbol may be a wide character; ensure room for it
            try:
                if cx + 1 < width:  # Room for wide char
                    stdscr.addstr(cy, cx, sun_str, curses.color_pair(1) | curses.A_BOLD)
                else:
                    # At the right edge, use ASCII fallback
                    stdscr.addch(cy, cx, ord('*'), curses.color_pair(1) | curses.A_BOLD)
            except (curses.error, UnicodeEncodeError):
                try:
                    stdscr.addch(cy, cx, ord('*'), curses.color_pair(1) | curses.A_BOLD)
                except curses.error:
                    pass

        # Draw planets
        planet_info = []
        all_positions = []
        for i, (name, a, period, e, sym, cp, usym) in enumerate(planet_data):
            x, y = planet_position(a, period, e, years_since_epoch)
            sx, sy = au_to_screen(x, y, cx, cy, state.scale, max_r)
            # Compute current distance from Sun
            r_current = math.sqrt(x**2 + y**2)
            # Compute orbital velocity
            v_km_s = orbital_velocity_km_s(a, period, r_current)
            planet_info.append((name, a, period, e, sym, cp, usym, x, y, sx, sy, r_current, v_km_s))
            all_positions.append((x, y))

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
            # Unicode symbols may be wide (2 columns) — ensure we have room
            if 0 <= sy < height and 0 <= sx < width:
                # Try Unicode symbol first; if it's wide, we need sx+1 < width
                try:
                    # Attempt to write the Unicode symbol
                    if sx + 1 < width:  # Ensure room for wide char + label offset
                        stdscr.addstr(sy, sx, usym, cp | curses.A_BOLD)
                    else:
                        # At the right edge, fall back to ASCII (always 1 column)
                        stdscr.addstr(sy, sx, sym, cp | curses.A_BOLD)
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
                if lx + len(label) <= width:
                    try:
                        stdscr.addstr(ly, lx, label, attr)
                    except curses.error:
                        pass

            # Draw Earth's Moon
            if state.show_moon and name == "Earth":
                moon_angle = 2 * math.pi * years_since_epoch / MOON_PERIOD_YEARS
                # Moon position relative to Earth, scaled up for visibility
                # We use a larger display radius (not real scale) so it's visible
                moon_display_r = max(2, max_r // 25)  # At least 2 screen units from Earth to avoid overlap
                moon_sx = sx + int(moon_display_r * math.cos(moon_angle))
                moon_sy = sy + int(moon_display_r * 0.5 * math.sin(moon_angle))  # Y compressed
                if 0 <= moon_sy < height and 0 <= moon_sx < width:
                    try:
                        stdscr.addch(moon_sy, moon_sx, ord('o'), curses.color_pair(1) | curses.A_DIM)
                    except curses.error:
                        pass

        # Detect conjunctions
        state.conjunctions = detect_conjunctions(all_positions)

        # --- Info Panel ---
        panel_x = 1
        panel_y = 1

        sel = state.selected_planet
        sel_name, sel_a, sel_period, sel_e, sel_sym, sel_cp, sel_usym, \
            sel_x, sel_y, _, _, sel_r, sel_v = planet_info[sel]

        trail_status = "ON" if state.show_trails else "OFF"
        moon_status = "ON" if state.show_moon else "OFF"
        belt_status = "ON" if state.show_asteroids else "OFF"

        lines = [
            f"╔══ Solar System Orrery ══╗",
            f"  Date: {format_date(state.current_date)}",
            f"  Speed: {state.speed:.2f} days/sec",
            f"  {'PAUSED' if state.paused else 'RUNNING'}  Trails: {trail_status}",
            f"  Moon: {moon_status}  Belt: {belt_status}",
            f"╠════════════════════════╣",
            f"  Planet: {sel_name}",
            f"  Semi-major: {sel_a:.3f} AU",
            f"  Distance: {sel_r:.3f} AU",
            f"  Velocity: {sel_v:.1f} km/s",
            f"  Period: {sel_period:.3f} years",
            f"  Eccentricity: {sel_e:.3f}",
            f"  Position: ({sel_x:+.2f}, {sel_y:+.2f}) AU",
            f"╚════════════════════════╝",
        ]

        # Add conjunction alerts
        if state.conjunctions:
            lines.append("")
            lines.append("  ⚡ Conjunctions:")
            for i, j, sep in state.conjunctions[:3]:  # Show max 3
                lines.append(f"    {PLANETS[i][0]}-{PLANETS[j][0]}: {sep:.1f}°")

        for idx, line in enumerate(lines):
            row = panel_y + idx
            if 0 <= row < height - 1:
                safe_addstr(stdscr, row, panel_x, line, curses.color_pair(10), height, width)

        # --- Controls ---
        controls_y = height - 2
        controls = "SPC:Pause +/-:Speed ↑↓:Zoom ←→:Planet O:Orbits L:Labels T:Trails A:Belt M:Moon D:Date S:Speed H:Today R:Reset Q:Quit"
        if controls_y > 0:
            safe_addstr(stdscr, controls_y, 1, controls, curses.color_pair(10) | curses.A_DIM, height, width)

        # Input mode
        if state.input_mode == 'date':
            prompt = f"Go to date (YYYY-MM-DD): {state.input_buffer}_"
            prompt_y = min(cy + max_r + 2, height - 3)
            safe_addstr(stdscr, prompt_y, max(0, cx - len(prompt) // 2), prompt, curses.color_pair(1) | curses.A_BOLD, height, width)
        elif state.input_mode == 'speed':
            prompt = f"Speed (days/sec, >0): {state.input_buffer}_"
            prompt_y = min(cy + max_r + 2, height - 3)
            safe_addstr(stdscr, prompt_y, max(0, cx - len(prompt) // 2), prompt, curses.color_pair(1) | curses.A_BOLD, height, width)

        # Conjunction alert at bottom
        if state.conjunctions and not state.input_mode:
            for ci, (i, j, sep) in enumerate(state.conjunctions[:2]):
                alert = f"⚡ {PLANETS[i][0]}-{PLANETS[j][0]} conjunction ({sep:.1f}°)"
                alert_y = height - 4 - ci
                if alert_y > 0:
                    safe_addstr(stdscr, alert_y, max(1, cx - len(alert) // 2),
                              alert, curses.color_pair(13) | curses.A_BOLD, height, width)

        stdscr.refresh()

    curses.curs_set(1)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Solar System Orrery — An animated terminal-based orrery with real orbital mechanics",
        epilog="Controls: SPC=Pause  +/-=Speed  ↑↓=Zoom  ←→=Select  O=Orbits  L=Labels  "
               "T=Trails  A=Asteroid belt  M=Moon  D=Date  S=Speed  H=Today  R=Reset  Q=Quit"
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--date', '-d', type=str, default=None,
                       help='Start date in YYYY-MM-DD format (default: 2026-01-01)')
    parser.add_argument('--speed', '-s', type=float, default=None,
                       help='Initial speed in days/sec (default: 1.0)')
    parser.add_argument('--no-trails', action='store_true',
                       help='Start with trails disabled')
    parser.add_argument('--no-moon', action='store_true',
                       help='Start with Moon hidden')
    parser.add_argument('--asteroids', action='store_true',
                       help='Start with asteroid belt visible')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Apply CLI arguments by modifying default state before entering curses
    # We create a custom wrapper that sets up state from args
    def main_with_args(stdscr):
        """Wrapper that applies CLI args before entering the main loop."""
        # We need to hook into the state initialization
        # The simplest approach: patch OrreryState defaults
        original_init = OrreryState.__init__

        def patched_init(self):
            original_init(self)
            if args.date:
                try:
                    self.current_date = datetime.strptime(args.date, "%Y-%m-%d")
                except ValueError:
                    print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD.", file=sys.stderr)
                    sys.exit(1)
            if args.speed is not None:
                if args.speed <= 0:
                    print("Error: Speed must be positive.", file=sys.stderr)
                    sys.exit(1)
                self.speed = min(args.speed, 3650)
            if args.no_trails:
                self.show_trails = False
            if args.no_moon:
                self.show_moon = False
            if args.asteroids:
                self.show_asteroids = True

        OrreryState.__init__ = patched_init
        try:
            return main(stdscr)
        finally:
            OrreryState.__init__ = original_init

    try:
        curses.wrapper(main_with_args)
    except KeyboardInterrupt:
        pass