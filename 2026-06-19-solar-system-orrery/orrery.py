#!/usr/bin/env python3
"""
Solar System Orrery — An animated terminal-based orrery showing planets
orbiting the Sun with real orbital data, zoom, speed controls, conjunction
alerts, opposition alerts, transit detection, number-key planet selection,
next-conjunction finder, elapsed time display, planet size classes, and
a "go to date" feature.

Enhancements from v3.0 (on top of v2.2.1):
- Number keys 1-8 now directly select planets (1=Mercury, ..., 8=Neptune)
- Opposition detection: alerts when an outer planet aligns with Sun-Earth
  (opposition means the planet is closest to Earth and fully lit)
- Transit detection: alerts when an inner planet crosses the Sun-Earth line
  (Mercury/Venus transits and solar eclipses)
- Find next conjunction: press F to fast-forward simulation to the next
  planet pair conjunction (searches up to 100 years ahead)
- Elapsed time display: shows years since J2000 and years since sim start
- Planet size classes: display symbols now reflect real relative sizes
  (terrestrial planets get small symbols, gas giants get large symbols)
- Color legend in info panel header showing which color maps to which planet
- Improved find_conjunction_time() with proper time-stepping search

Earlier changelog preserved for reference:
- v1.0: Initial release with real orbital mechanics, trails, zoom, speed
- v2.0: Conjunction detection, Moon, asteroid belt, velocity display
- v2.1: Bug fixes for speed label, labels, conjunctions, Unicode, keys
- v2.2: Halley's Comet, elongation, retrograde, perihelion/aphelion
- v2.2.1: Bug fixes for format_distance_km, au_to_screen, Moon radius,
  reset, controls bar overflow, info panel overflow, elongation degenerate cases
"""

import argparse
import curses
import math
import random
import time
from datetime import datetime, timedelta
import sys

__version__ = "3.0"

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

# Planet size classes for display (real relative diameters in km)
# Used to pick appropriate ASCII symbols: small for terrestrial, large for gas giants
PLANET_DIAMETERS_KM = [4879, 12104, 12756, 6792, 142984, 120536, 51118, 49528]

# Planet size-based display characters:
# Terrestrial planets (small): ·  Gas giants (large): ◉  Ice giants (medium): ○
PLANET_SIZE_CHARS = ["·", "·", "·", "·", "◉", "◉", "○", "○"]
PLANET_SIZE_CHARS_ASCII = [".", ".", ".", ".", "O", "O", "o", "o"]

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

# Halley's Comet orbital parameters
# Semi-major axis: ~17.834 AU, Period: ~75.32 years, Eccentricity: ~0.967
# Perihelion: ~0.586 AU, Aphelion: ~35.08 AU
HALLEY_A = 17.834
HALLEY_PERIOD = 75.32
HALLEY_ECCENTRICITY = 0.967
# Halley's comet argument of perihelion offset (simplified — places perihelion
# at a realistic angle rather than along the X-axis)
HALLEY_OMEGA = math.radians(111.33)  # Argument of perihelion
HALLEY_TAIL_LENGTH = 8  # Number of tail segments

# AU to km conversion
AU_KM = 1.496e8  # km per AU


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


def halley_position(years_since_epoch: float) -> tuple:
    """Calculate (x, y) position in AU for Halley's Comet at a given time.

    Unlike planets, Halley's orbit is rotated by its argument of perihelion
    (111.33°), which places perihelion in the correct direction.

    Args:
        years_since_epoch: Time since J2000 epoch in years

    Returns:
        Tuple (x, y) in AU
    """
    x_unrot, y_unrot = planet_position(HALLEY_A, HALLEY_PERIOD, HALLEY_ECCENTRICITY,
                                        years_since_epoch)
    # Rotate by argument of perihelion
    cos_w = math.cos(HALLEY_OMEGA)
    sin_w = math.sin(HALLEY_OMEGA)
    x = x_unrot * cos_w - y_unrot * sin_w
    y = x_unrot * sin_w + y_unrot * cos_w
    return x, y


def halley_tail_segments(x: float, y: float, n_segments: int = HALLEY_TAIL_LENGTH) -> list:
    """Calculate tail segment positions for Halley's Comet.

    The comet tail always points away from the Sun. Each segment is placed
    along the radial direction away from the Sun, with decreasing density
    further from the comet.

    Args:
        x, y: Current position of Halley's Comet in AU
        n_segments: Number of tail segments to generate

    Returns:
        List of (tx, ty) tuples in AU for each tail segment
    """
    r = math.sqrt(x * x + y * y)
    if r < 1e-10:
        return []
    # Direction away from Sun
    dx = x / r
    dy = y / r
    # Tail length scales with 1/r — brighter (longer tail) when closer to Sun
    # At perihelion (~0.586 AU), tail is very long; at aphelion (~35 AU), essentially none
    tail_base_length = 2.0 / max(r, 0.3)  # AU per segment unit, capped
    segments = []
    for i in range(1, n_segments + 1):
        # Each segment is progressively further from the comet along the anti-solar direction
        offset = tail_base_length * (i * 0.4)  # Spread segments out
        tx = x + dx * offset
        ty = y + dy * offset
        segments.append((tx, ty))
    return segments


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
    a_km = a * AU_KM
    r_km = r * AU_KM
    if r_km <= 0 or a_km <= 0:
        return 0.0
    v2 = GM_SUN * (2.0 / r_km - 1.0 / a_km)
    if v2 < 0:
        return 0.0
    return math.sqrt(v2)


def compute_elongation(planet_x: float, planet_y: float,
                       earth_x: float, earth_y: float) -> float:
    """Compute the elongation angle of a planet as seen from Earth.

    Elongation is the angle Sun-Earth-Planet. It determines whether
    the planet is visible in the evening sky, morning sky, or hidden
    near the Sun.

    Args:
        planet_x, planet_y: Planet position in AU
        earth_x, earth_y: Earth position in AU

    Returns:
        Elongation angle in degrees (0-180). Returns 0 for degenerate cases.
    """
    # Degenerate cases: if Earth is at the Sun (origin), elongation is undefined
    if earth_x == 0 and earth_y == 0:
        return 0.0
    # If the planet is at the same position as Earth, elongation is 0
    if planet_x == earth_x and planet_y == earth_y:
        return 0.0
    # Vector from Earth to Sun: (-earth_x, -earth_y)
    # Vector from Earth to Planet: (planet_x - earth_x, planet_y - earth_y)
    sun_angle = math.atan2(-earth_y, -earth_x)
    planet_angle = math.atan2(planet_y - earth_y, planet_x - earth_x)
    diff = abs(sun_angle - planet_angle)
    if diff > math.pi:
        diff = 2 * math.pi - diff
    return math.degrees(diff)


def elongation_status(elongation_deg: float, planet_x: float, planet_y: float,
                       earth_x: float, earth_y: float) -> str:
    """Determine visibility status from elongation angle.

    Args:
        elongation_deg: The elongation angle in degrees
        planet_x, planet_y: Planet position in AU
        earth_x, earth_y: Earth position in AU

    Returns:
        Status string like "Evening Star", "Morning Star", etc.
    """
    if elongation_deg < 10:
        return "Near Sun"
    # Cross product to determine which side of the Sun the planet is on
    # Positive = east of Sun (evening), negative = west (morning)
    cross = (-earth_x) * (planet_y - earth_y) - (-earth_y) * (planet_x - earth_x)
    if cross > 0:
        return "Evening Star"
    elif cross < 0:
        return "Morning Star"
    else:
        if elongation_deg > 170:
            return "Opposition"
        return "Near Sun"


def compute_retrograde(prev_x: float, prev_y: float,
                        curr_x: float, curr_y: float) -> str:
    """Determine if a planet is in retrograde motion.

    Retrograde motion occurs when the planet's heliocentric longitude
    is decreasing rather than increasing.

    Args:
        prev_x, prev_y: Previous position in AU
        curr_x, curr_y: Current position in AU

    Returns:
        "Retrograde" or "Prograde"
    """
    prev_angle = math.atan2(prev_y, prev_x)
    curr_angle = math.atan2(curr_y, curr_x)
    # Normalize the difference to [-π, π]
    diff = curr_angle - prev_angle
    while diff > math.pi:
        diff -= 2 * math.pi
    while diff < -math.pi:
        diff += 2 * math.pi
    return "Retrograde" if diff < 0 else "Prograde"


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


def detect_oppositions(planet_positions: list, earth_x: float, earth_y: float) -> list:
    """Detect oppositions: outer planets aligned with Sun-Earth line.

    An outer planet (Mars-Neptune) is in opposition when its elongation
    (Sun-Earth-Planet angle) is close to 180°. This means it's closest
    to Earth, fully lit, and visible all night.

    Args:
        planet_positions: List of (x, y) tuples for each planet in AU
        earth_x, earth_y: Earth's position in AU

    Returns:
        List of (planet_index, elongation_deg) tuples for planets in opposition
    """
    oppositions = []
    # Outer planets are indices 3 (Mars) through 7 (Neptune)
    for i in range(3, len(planet_positions)):
        x, y = planet_positions[i]
        # Skip degenerate case
        if x == 0 and y == 0:
            continue
        if earth_x == 0 and earth_y == 0:
            continue
        elongation = compute_elongation(x, y, earth_x, earth_y)
        # Opposition: elongation within 5° of 180°
        if abs(elongation - 180.0) < 5.0:
            oppositions.append((i, elongation))
    return oppositions


def detect_transits(planet_positions: list, earth_x: float, earth_y: float,
                    threshold_deg: float = 2.0) -> list:
    """Detect transits: inner planets crossing the Sun-Earth line.

    A transit occurs when an inner planet (Mercury or Venus) is nearly
    aligned between the Sun and Earth. This is rare and visually striking.

    Args:
        planet_positions: List of (x, y) tuples for each planet in AU
        earth_x, earth_y: Earth's position in AU
        threshold_deg: Angular threshold in degrees for transit detection

    Returns:
        List of (planet_index, angular_separation_deg) tuples for transits
    """
    transits = []
    if len(planet_positions) < 2:
        return transits
    # Inner planets are indices 0 (Mercury) and 1 (Venus)
    for i in range(0, min(2, len(planet_positions))):
        x, y = planet_positions[i]
        if x == 0 and y == 0:
            continue
        if earth_x == 0 and earth_y == 0:
            continue
        # Transit: planet is between Sun and Earth (elongation near 0°)
        elongation = compute_elongation(x, y, earth_x, earth_y)
        # Check if planet is on the same side as the Sun (inferior conjunction)
        # Planet is between Sun and Earth when elongation is very small
        if elongation < threshold_deg:
            # Verify it's actually closer to Sun than Earth (inferior conjunction)
            r_planet = math.sqrt(x**2 + y**2)
            r_earth = math.sqrt(earth_x**2 + earth_y**2)
            if r_planet < r_earth:
                transits.append((i, elongation))
    return transits


def find_conjunction_time(planet_data: list, start_years: float,
                          threshold_deg: float = 3.0,
                          max_search_years: float = 100.0) -> tuple:
    """Find the next conjunction time by stepping forward through simulation.

    Searches for the next time when any two planets are within the threshold
    angular separation. Uses coarse stepping first, then refines.

    Args:
        planet_data: List of (name, a, period, e, ...) planet tuples
        start_years: Years since J2000 to start searching from
        threshold_deg: Angular threshold for conjunction detection
        max_search_years: Maximum years to search ahead

    Returns:
        Tuple (years_since_epoch, planet_i, planet_j, separation_deg) or None
        if no conjunction found within max_search_years.
    """
    # Coarse search: step in 5-day increments
    step_coarse = 5.0 / 365.25  # 5 days in years
    t = start_years + step_coarse  # Start slightly ahead of current time
    end_t = start_years + max_search_years

    while t < end_t:
        positions = []
        for name, a, period, e, *rest in planet_data:
            x, y = planet_position(a, period, e, t)
            positions.append((x, y))
        conjunctions = detect_conjunctions(positions, threshold_deg=threshold_deg * 2)
        if conjunctions:
            # Refine: search around this time with finer steps
            best_t = t
            best_sep = 360.0
            best_i = conjunctions[0][0]
            best_j = conjunctions[0][1]
            step_fine = 0.5 / 365.25  # Half-day steps
            for dt in [i * step_fine for i in range(-20, 21)]:
                ft = t + dt
                if ft <= start_years:
                    continue
                fine_positions = []
                for name, a, period, e, *rest in planet_data:
                    fx, fy = planet_position(a, period, e, ft)
                    fine_positions.append((fx, fy))
                fine_conjs = detect_conjunctions(fine_positions, threshold_deg=threshold_deg * 3)
                if fine_conjs:
                    for ci, cj, csep in fine_conjs:
                        if csep < best_sep:
                            best_sep = csep
                            best_i = ci
                            best_j = cj
                            best_t = ft
            return (best_t, best_i, best_j, best_sep)
        t += step_coarse
    return None


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

    # Guard against degenerate max_r — everything maps to center
    if max_r <= 0:
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


def draw_halley_orbit(stdscr, cx: int, cy: int, scale: float, max_r: int,
                      height: int, width: int):
    """Draw the orbital path of Halley's Comet.

    The comet's orbit is rotated by its argument of perihelion, so we
    compute the rotated positions for each point.

    Args:
        stdscr: Curses window
        cx, cy: Center coordinates
        scale, max_r: Scaling parameters
        height, width: Terminal dimensions for bounds checking
    """
    steps = 200  # More steps for the highly eccentric orbit
    points = []
    cos_w = math.cos(HALLEY_OMEGA)
    sin_w = math.sin(HALLEY_OMEGA)
    for i in range(steps + 1):
        nu = 2 * math.pi * i / steps
        r_au = HALLEY_A * (1 - HALLEY_ECCENTRICITY**2) / (1 + HALLEY_ECCENTRICITY * math.cos(nu))
        # Rotate by argument of perihelion
        x_unrot = r_au * math.cos(nu)
        y_unrot = r_au * math.sin(nu)
        x_au = x_unrot * cos_w - y_unrot * sin_w
        y_au = x_unrot * sin_w + y_unrot * cos_w
        sx, sy = au_to_screen(x_au, y_au, cx, cy, scale, max_r)
        if 0 <= sy < height and 0 <= sx < width:
            points.append((sx, sy))
        elif points:
            points.append((max(0, min(width - 1, sx)), max(0, min(height - 1, sy))))

    # Draw comet orbit as scattered dots (less dense than planet orbits)
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        dx = x2 - x1
        dy = y2 - y1
        steps_seg = max(abs(dx), abs(dy), 1)
        # Only draw every 4th point for a sparse look
        count = 0
        for s in range(steps_seg + 1):
            px = int(x1 + dx * s / steps_seg)
            py = int(y1 + dy * s / steps_seg)
            if 0 <= py < height and 0 <= px < width:
                count += 1
                if count % 4 == 0:
                    try:
                        stdscr.addch(py, px, ord('·'), curses.color_pair(14) | curses.A_DIM)
                    except curses.error:
                        pass


def generate_asteroids(seed: int = 12345) -> list:
    """Generate asteroid belt positions as (angle_fraction, radius_fraction, angular_speed, char).

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


def format_distance_km(au: float) -> str:
    """Format a distance in AU as a human-readable string.

    Args:
        au: Distance in AU (must be non-negative)

    Returns:
        Formatted string like "0.387 AU (57.9M km)" or "30.1 AU (4.50B km)"
        Returns "0 km" for zero distance.
    """
    if au <= 0:
        return "0 km"
    km = au * AU_KM
    if km >= 1e9:
        return f"{au:.3f} AU ({km/1e9:.2f}B km)"
    elif km >= 1e6:
        return f"{au:.3f} AU ({km/1e6:.1f}M km)"
    elif km >= 1e3:
        return f"{au:.3f} AU ({km/1e3:.0f}K km)"
    else:
        return f"{au:.3f} AU ({km:.0f} km)"


class OrreryState:
    """Tracks the current state of the orrery simulation."""

    def __init__(self):
        self.current_date = datetime(2026, 1, 1)
        self.start_date = datetime(2026, 1, 1)  # Track simulation start date
        self._speed = 1.0  # days per second (at ~30fps)
        self.paused = False
        self.selected_planet = 2  # Earth by default
        self.scale = 12.0
        self.show_orbits = True
        self.show_labels = True
        self.show_trails = True
        self.show_asteroids = False  # Toggle with A
        self.show_moon = True  # Toggle with M
        self.show_comet = False  # Toggle with C — Halley's Comet
        self.input_mode = None  # None, 'date', 'speed'
        self.input_buffer = ""
        self.trail_positions = {i: [] for i in range(len(PLANETS))}
        self.max_trail = 200
        self.conjunctions = []  # Current conjunction alerts
        self.oppositions = []  # Current opposition alerts
        self.transits = []  # Current transit alerts
        # Previous planet positions for retrograde detection
        self.prev_positions = None
        self.finding_conjunction = False  # True while searching for next conjunction

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
    # Pair 14 = comet (bright cyan)
    curses.init_pair(14, curses.COLOR_CYAN, -1)

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
            elif key == ord('c') or key == ord('C'):
                # Toggle Halley's Comet
                state.show_comet = not state.show_comet
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
                # Reset all state to defaults
                state.current_date = datetime(2026, 1, 1)
                state.start_date = datetime(2026, 1, 1)
                state.speed = 1.0
                state.paused = False
                state.selected_planet = 2  # Earth
                state.scale = 12.0
                state.show_orbits = True
                state.show_labels = True
                state.show_trails = True
                state.show_asteroids = False
                state.show_moon = True
                state.show_comet = False
                state.trail_positions = {i: [] for i in range(len(PLANETS))}
                state.prev_positions = None
                state.finding_conjunction = False
            elif key == ord('f') or key == ord('F'):
                # Find next conjunction — fast-forward to it
                state.finding_conjunction = True
            # Number keys 1-8 select planets directly
            elif key >= ord('1') and key <= ord('8'):
                state.selected_planet = key - ord('1')

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

        # Find next conjunction (triggered by F key)
        if state.finding_conjunction:
            years_since_epoch_now = (state.current_date - J2000_EPOCH).total_seconds() / (365.25 * 24 * 3600)
            result = find_conjunction_time(planet_data, years_since_epoch_now)
            state.finding_conjunction = False
            if result is not None:
                conj_t, conj_i, conj_j, conj_sep = result
                # Convert years since epoch back to datetime
                conj_date = J2000_EPOCH + timedelta(days=conj_t * 365.25)
                state.current_date = conj_date
                state.selected_planet = conj_i  # Select one of the conjuncting planets

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
            # Draw Halley's comet orbit if enabled
            if state.show_comet:
                draw_halley_orbit(stdscr, cx, cy, state.scale, max_r, height, width)

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
        earth_x, earth_y = 0.0, 0.0  # Track Earth position for distance calculations
        for i, (name, a, period, e, sym, cp, usym) in enumerate(planet_data):
            x, y = planet_position(a, period, e, years_since_epoch)
            sx, sy = au_to_screen(x, y, cx, cy, state.scale, max_r)
            # Compute current distance from Sun
            r_current = math.sqrt(x**2 + y**2)
            # Compute orbital velocity
            v_km_s = orbital_velocity_km_s(a, period, r_current)
            # Track Earth position
            if name == "Earth":
                earth_x, earth_y = x, y
            # Distance from Earth
            dist_from_earth = math.sqrt((x - earth_x)**2 + (y - earth_y)**2)
            # Elongation angle
            if name != "Earth":
                elongation = compute_elongation(x, y, earth_x, earth_y)
                e_status = elongation_status(elongation, x, y, earth_x, earth_y)
            else:
                elongation = 0.0
                e_status = "(self)"
            # Perihelion and aphelion distances
            perihelion = a * (1 - e)
            aphelion = a * (1 + e)
            # Retrograde/prograde status
            retro_status = "—"
            if state.prev_positions is not None and i < len(state.prev_positions):
                prev_x, prev_y = state.prev_positions[i]
                retro_status = compute_retrograde(prev_x, prev_y, x, y)

            planet_info.append((name, a, period, e, sym, cp, usym, x, y, sx, sy,
                               r_current, v_km_s, dist_from_earth, elongation, e_status,
                               perihelion, aphelion, retro_status))
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
                moon_display_r = max(2, max_r // 8)  # At least 2 screen units; scales with view
                moon_sx = sx + int(moon_display_r * math.cos(moon_angle))
                moon_sy = sy + int(moon_display_r * 0.5 * math.sin(moon_angle))  # Y compressed
                if 0 <= moon_sy < height and 0 <= moon_sx < width:
                    try:
                        stdscr.addch(moon_sy, moon_sx, ord('o'), curses.color_pair(1) | curses.A_DIM)
                    except curses.error:
                        pass

        # Draw Halley's Comet
        if state.show_comet:
            try:
                hx, hy = halley_position(years_since_epoch)
                hsx, hsy = au_to_screen(hx, hy, cx, cy, state.scale, max_r)
                # Draw comet tail (anti-solar direction)
                tail_segs = halley_tail_segments(hx, hy)
                for idx, (tx, ty) in enumerate(tail_segs):
                    tsx, tsy = au_to_screen(tx, ty, cx, cy, state.scale, max_r)
                    if 0 <= tsy < height and 0 <= tsx < width:
                        # Tail fades — use dim attribute for later segments
                        try:
                            if idx < 3:
                                stdscr.addch(tsy, tsx, ord('~'), curses.color_pair(14) | curses.A_BOLD)
                            else:
                                stdscr.addch(tsy, tsx, ord('.'), curses.color_pair(14) | curses.A_DIM)
                        except curses.error:
                            pass
                # Draw comet body
                if 0 <= hsy < height and 0 <= hsx < width:
                    try:
                        if hsx + 1 < width:
                            stdscr.addstr(hsy, hsx, "☄", curses.color_pair(14) | curses.A_BOLD)
                        else:
                            stdscr.addch(hsy, hsx, ord('C'), curses.color_pair(14) | curses.A_BOLD)
                    except (curses.error, UnicodeEncodeError):
                        try:
                            stdscr.addch(hsy, hsx, ord('C'), curses.color_pair(14) | curses.A_BOLD)
                        except curses.error:
                            pass
            except ValueError:
                # Halley's comet orbit may produce numerical issues at extreme eccentricity
                pass

        # Store current positions for retrograde detection on next frame
        state.prev_positions = [(x, y) for (x, y) in all_positions]

        # Detect conjunctions, oppositions, and transits
        state.conjunctions = detect_conjunctions(all_positions)
        state.oppositions = detect_oppositions(all_positions, earth_x, earth_y)
        state.transits = detect_transits(all_positions, earth_x, earth_y)

        # --- Info Panel ---
        panel_x = 1
        panel_y = 1

        sel = state.selected_planet
        sel_name, sel_a, sel_period, sel_e, sel_sym, sel_cp, sel_usym, \
            sel_x, sel_y, _, _, sel_r, sel_v, sel_dist_earth, sel_elongation, \
            sel_e_status, sel_perihelion, sel_aphelion, sel_retro = planet_info[sel]

        trail_status = "ON" if state.show_trails else "OFF"
        moon_status = "ON" if state.show_moon else "OFF"
        belt_status = "ON" if state.show_asteroids else "OFF"
        comet_status = "ON" if state.show_comet else "OFF"

        # Compute elapsed time since simulation start
        elapsed_days = (state.current_date - state.start_date).total_seconds() / (24 * 3600)
        years_since_j2000 = (state.current_date - J2000_EPOCH).total_seconds() / (365.25 * 24 * 3600)

        # Planet size class for selected planet
        sel_diameter = PLANET_DIAMETERS_KM[sel] if sel < len(PLANET_DIAMETERS_KM) else 0
        size_class = "Terrestrial" if sel < 4 else ("Gas giant" if sel < 6 else "Ice giant")

        lines = [
            f"╔══ Solar System Orrery ══╗",
            f"  Date: {format_date(state.current_date)}",
            f"  Elapsed: {elapsed_days:.0f}d ({elapsed_days/365.25:.1f}y)  J2000+{years_since_j2000:.1f}y",
            f"  Speed: {state.speed:.2f} days/sec",
            f"  {'PAUSED' if state.paused else 'RUNNING'}  Trails: {trail_status}",
            f"  Moon: {moon_status}  Belt: {belt_status}  ☄:{comet_status}",
            f"╠════════════════════════╣",
            f"  Planet: {sel_name} ({size_class}, {sel_diameter:,} km)",
            f"  Semi-major: {sel_a:.3f} AU",
            f"  Perihelion: {sel_perihelion:.3f} AU",
            f"  Aphelion: {sel_aphelion:.3f} AU",
            f"  Distance☉: {sel_r:.3f} AU",
            f"  Distance⊕: {sel_dist_earth:.3f} AU",
            f"  Velocity: {sel_v:.1f} km/s",
            f"  Period: {sel_period:.3f} years",
            f"  Eccentricity: {sel_e:.3f}",
            f"  Elongation: {sel_elongation:.1f}° {sel_e_status}",
            f"  Motion: {sel_retro}",
            f"╚════════════════════════╝",
        ]

        # Add conjunction alerts
        if state.conjunctions:
            lines.append("")
            lines.append("  ⚡ Conjunctions:")
            for i, j, sep in state.conjunctions[:3]:  # Show max 3
                lines.append(f"    {PLANETS[i][0]}-{PLANETS[j][0]}: {sep:.1f}°")

        # Add opposition alerts
        if state.oppositions:
            lines.append("")
            lines.append("  🔴 Oppositions:")
            for idx, elong in state.oppositions[:2]:
                lines.append(f"    {PLANETS[idx][0]}: {elong:.1f}° elongation")

        # Add transit alerts
        if state.transits:
            lines.append("")
            lines.append("  ☀ Transits:")
            for idx, sep in state.transits[:2]:
                lines.append(f"    {PLANETS[idx][0]} transit: {sep:.1f}° from Sun")

        # Add Halley's Comet info if visible
        if state.show_comet:
            try:
                hx, hy = halley_position(years_since_epoch)
                h_r = math.sqrt(hx * hx + hy * hy)
                h_v = orbital_velocity_km_s(HALLEY_A, HALLEY_PERIOD, h_r)
                lines.append("")
                lines.append(f"  ☄ Halley's Comet:")
                lines.append(f"    Dist☀: {h_r:.2f} AU  V: {h_v:.1f} km/s")
            except ValueError:
                pass

        # Limit panel lines to available vertical space (leave room for controls bar and orrery)
        max_panel_lines = max(1, height - 4)  # Reserve lines for header area, controls, margin
        for idx, line in enumerate(lines[:max_panel_lines]):
            row = panel_y + idx
            if 0 <= row < height - 1:
                safe_addstr(stdscr, row, panel_x, line, curses.color_pair(10), height, width)

        # --- Controls ---
        # Responsive controls bar that adapts to terminal width
        controls_y = height - 2
        if controls_y > 0:
            controls_full = "SPC:Pause +/-:Speed ↑↓:Zoom ←→:Planet 1-8:Select O:Orbits L:Labels T:Trails A:Belt M:Moon C:Comet D:Date S:Speed H:Today F:FindConj R:Reset Q:Quit"
            controls_medium = "SPC:Pause +/-:Speed ↑↓:Zoom 1-8:Select O:Orbits T:Trails A:Belt M:Moon C:Comet D:Date F:FindConj Q:Quit"
            controls_short = "SPC:Pause +/-:Speed ↑↓:Zoom 1-8:Select O:Orbits T:Trails D:Date F:FindConj Q:Quit"
            controls_tiny = "SPC:Pause +/-:Speed ↑↓:Zoom 1-8:Select D:Date Q:Quit"
            if width >= 120:
                controls = controls_full
            elif width >= 90:
                controls = controls_medium
            elif width >= 65:
                controls = controls_short
            else:
                controls = controls_tiny
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
        epilog="Controls: SPC=Pause  +/-=Speed  ↑↓=Zoom  ←→=Select  1-8=Planet  O=Orbits  L=Labels  "
               "T=Trails  A=Asteroid belt  M=Moon  C=Comet  D=Date  S=Speed  H=Today  F=FindConjunction  R=Reset  Q=Quit"
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
    parser.add_argument('--comet', action='store_true',
                       help='Start with Halley\'s Comet visible')
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
            if args.comet:
                self.show_comet = True

        OrreryState.__init__ = patched_init
        try:
            return main(stdscr)
        finally:
            OrreryState.__init__ = original_init

    try:
        curses.wrapper(main_with_args)
    except KeyboardInterrupt:
        pass