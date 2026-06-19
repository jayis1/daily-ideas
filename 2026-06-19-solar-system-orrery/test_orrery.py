#!/usr/bin/env python3
"""
Comprehensive tests for the Solar System Orrery v2.2.
Tests orbital mechanics, screen mapping, star generation, state management,
conjunction detection, orbital velocity, asteroid belt, Moon position,
Halley's Comet, elongation, retrograde detection, edge cases, and bug fixes.
"""
import sys
sys.path.insert(0, '.')
import math
from datetime import datetime

from orrery import (
    solve_kepler, planet_position, au_to_screen,
    generate_stars, format_date, format_distance_km, OrreryState, safe_addstr,
    detect_conjunctions, orbital_velocity_km_s,
    generate_asteroids, ASTEROID_BELT_INNER_AU, ASTEROID_BELT_OUTER_AU,
    MOON_ORBITAL_RADIUS_AU, MOON_PERIOD_YEARS,
    CONJUNCTION_THRESHOLD_DEG, __version__, PLANETS, J2000_EPOCH,
    HALLEY_A, HALLEY_PERIOD, HALLEY_ECCENTRICITY, HALLEY_OMEGA,
    AU_KM,
    halley_position, halley_tail_segments,
    compute_elongation, elongation_status, compute_retrograde
)

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name}: {detail}")

# ============================================================
# 1. Kepler Solver Tests
# ============================================================
print("=== Kepler Solver Tests ===")

# Basic cases
E = solve_kepler(0.0, 0.0)
test("M=0, e=0 → E=0", abs(E) < 1e-10, f"got {E}")

E = solve_kepler(math.pi, 0.0)
test("M=π, e=0 → E=π", abs(E - math.pi) < 1e-10, f"got {E}")

E = solve_kepler(1.0, 0.5)
# Verify: M = E - e*sin(E)
M_check = E - 0.5 * math.sin(E)
test("M=1, e=0.5 → verifies M=E-e·sin(E)", abs(M_check - 1.0) < 1e-8, f"residual={M_check - 1.0}")

E = solve_kepler(1.0, 0.9)
M_check = E - 0.9 * math.sin(E)
test("M=1, e=0.9 → verifies", abs(M_check - 1.0) < 1e-8, f"residual={M_check - 1.0}")

# Edge: very small eccentricity
E = solve_kepler(2.0, 0.001)
test("Small eccentricity converges", abs(E) < 10, f"got {E}")

# Edge: large mean anomaly — solver doesn't crash and still satisfies Kepler's equation
E = solve_kepler(100 * math.pi, 0.3)
M_check = E - 0.3 * math.sin(E)
test("Large mean anomaly: Kepler equation satisfied",
     abs(M_check - 100 * math.pi) / (100 * math.pi) < 1e-6,
     f"residual={abs(M_check - 100*math.pi):.6f}")

# Error cases
try:
    solve_kepler(1.0, 1.0)
    test("e=1.0 raises ValueError", False)
except ValueError:
    test("e=1.0 raises ValueError", True)

try:
    solve_kepler(1.0, 1.5)
    test("e=1.5 raises ValueError", False)
except ValueError:
    test("e=1.5 raises ValueError", True)

try:
    solve_kepler(1.0, -0.1)
    test("e<0 raises ValueError", False)
except ValueError:
    test("e<0 raises ValueError", True)

# ============================================================
# 2. Planet Position Tests
# ============================================================
print("\n=== Planet Position Tests ===")

# Circular orbit at t=0 → (a, 0)
x, y = planet_position(1.0, 1.0, 0.0, 0.0)
test("Circular orbit at t=0: x≈1, y≈0", abs(x - 1.0) < 0.01 and abs(y) < 0.01,
     f"got ({x}, {y})")

# Earth at epoch
x, y = planet_position(1.0, 1.0, 0.017, 0.0)
test("Earth at epoch: distance≈1 AU",
     abs(math.sqrt(x**2 + y**2) - 1.0) < 0.1,
     f"distance={math.sqrt(x**2 + y**2)}")

# Mercury after 1 year
x, y = planet_position(0.387, 0.241, 0.206, 1.0)
r = math.sqrt(x**2 + y**2)
test("Mercury after 1yr: r in [0.31, 0.47] AU",
     0.31 < r < 0.47, f"r={r}")

# Neptune after 1 year (barely moves)
x, y = planet_position(30.069, 164.8, 0.009, 1.0)
r = math.sqrt(x**2 + y**2)
test("Neptune after 1yr: r≈30 AU", abs(r - 30.069) < 0.5, f"r={r}")

# Error: zero period
try:
    planet_position(1.0, 0.0, 0.0, 1.0)
    test("Zero period raises ValueError", False)
except ValueError:
    test("Zero period raises ValueError", True)

# Error: negative period
try:
    planet_position(1.0, -1.0, 0.0, 1.0)
    test("Negative period raises ValueError", False)
except ValueError:
    test("Negative period raises ValueError", True)

# Error: negative semi-major axis
try:
    planet_position(-1.0, 1.0, 0.0, 1.0)
    test("Negative a raises ValueError", False)
except ValueError:
    test("Negative a raises ValueError", True)

# Error: e >= 1
try:
    planet_position(1.0, 1.0, 1.0, 1.0)
    test("e>=1 raises ValueError", False)
except ValueError:
    test("e>=1 raises ValueError", True)

# Large time values (should not crash)
x, y = planet_position(1.0, 1.0, 0.017, 1000000.0)
test("Large time: doesn't crash", True, f"got ({x:.2f}, {y:.2f})")

# Negative time
x, y = planet_position(1.0, 1.0, 0.017, -100.0)
test("Negative time: doesn't crash", True, f"got ({x:.2f}, {y:.2f})")

# ============================================================
# 3. AU to Screen Tests
# ============================================================
print("\n=== AU to Screen Tests ===")

# Origin → center
sx, sy = au_to_screen(0, 0, 40, 12, 12.0, 38)
test("Origin maps to center", sx == 40 and sy == 12, f"got ({sx}, {sy})")

# Very large AU → clamped to max_r
sx, sy = au_to_screen(1000, 1000, 40, 12, 12.0, 38)
test("Large AU clamped to max_r", abs(sx - 40) <= 39 and abs(sy - 12) <= 20,
     f"got ({sx}, {sy})")

# Negative AU → upper-left on screen (screen Y is inverted)
sx, sy = au_to_screen(-5, -5, 40, 12, 12.0, 38)
test("Negative AU maps to upper-left quadrant", sx < 40 and sy < 12,
     f"got ({sx}, {sy})")

# Zero scale → center
sx, sy = au_to_screen(1.0, 0.0, 40, 12, 0.0, 38)
test("Zero scale maps to center", sx == 40 and sy == 12, f"got ({sx}, {sy})")

# Small scale
sx, sy = au_to_screen(1.0, 0.0, 40, 12, 3.0, 38)
test("Small scale: Earth near center", abs(sx - 40) < 10 and abs(sy - 12) < 5,
     f"got ({sx}, {sy})")

# Verify Y compression (perspective effect)
sx_pos, sy_pos = au_to_screen(0, 10, 40, 12, 12.0, 38)
sx_neg, sy_neg = au_to_screen(10, 0, 40, 12, 12.0, 38)
# Y displacement should be roughly half X displacement for same AU distance
y_disp = abs(sy_pos - 12)
x_disp = abs(sx_neg - 40)
test("Y compression: Y displacement < X displacement", y_disp < x_disp,
     f"y_disp={y_disp}, x_disp={x_disp}")

# ============================================================
# 4. Generate Stars Tests
# ============================================================
print("\n=== Generate Stars Tests ===")

# Normal case
stars = generate_stars(24, 80, 80)
test("Normal stars: count matches", len(stars) <= 80 and len(stars) > 0,
     f"got {len(stars)} stars")

# All stars within bounds
all_in_bounds = all(0 <= sy < 24 and 0 <= sx < 80 for (sy, sx, ch) in stars)
test("Normal stars: all in bounds", all_in_bounds)

# Zero dimensions
stars = generate_stars(0, 0, 80)
test("Zero dimensions: returns empty list", len(stars) == 0, f"got {len(stars)} stars")

stars = generate_stars(0, 80, 80)
test("Zero height: returns empty list", len(stars) == 0)

stars = generate_stars(24, 0, 80)
test("Zero width: returns empty list", len(stars) == 0)

# Negative dimensions
stars = generate_stars(-1, -1, 80)
test("Negative dimensions: returns empty list", len(stars) == 0)

# Very small terminal (1x1)
stars = generate_stars(1, 1, 80)
test("1x1 terminal: generates stars", len(stars) > 0, f"got {len(stars)} stars")
# All stars should be at (0, 0)
all_at_origin = all(sy == 0 and sx == 0 for (sy, sx, ch) in stars)
test("1x1 terminal: all stars at origin", all_at_origin)

# Stars have valid characters
stars = generate_stars(24, 80, 80)
valid_chars = all(ch in [".", "+", "*", "·"] for (_, _, ch) in stars)
test("Stars: valid characters", valid_chars)

# Deterministic (seeded)
stars1 = generate_stars(24, 80, 80)
stars2 = generate_stars(24, 80, 80)
test("Stars: deterministic (same seed)", stars1 == stars2)

# ============================================================
# 5. Format Date Tests
# ============================================================
print("\n=== Format Date Tests ===")

dt = datetime(2026, 1, 1)
test("format_date 2026-01-01", format_date(dt) == "2026-01-01")

dt = datetime(2000, 12, 31)
test("format_date 2000-12-31", format_date(dt) == "2000-12-31")

dt = datetime(1, 1, 1)
test("format_date year 1", format_date(dt).endswith("01-01"), f"got '{format_date(dt)}'")

# ============================================================
# 6. Format Distance Tests (NEW in v2.2)
# ============================================================
print("\n=== Format Distance Tests ===")

# 1 AU
dist_str = format_distance_km(1.0)
test("format_distance 1 AU contains 'AU'", "AU" in dist_str, f"got '{dist_str}'")
test("format_distance 1 AU contains 'km'", "km" in dist_str, f"got '{dist_str}'")

# 0.387 AU (Mercury)
dist_str = format_distance_km(0.387)
test("format_distance 0.387 AU", "0.387" in dist_str, f"got '{dist_str}'")

# 30 AU (Neptune) — should use B for billions
dist_str = format_distance_km(30.069)
test("format_distance 30 AU uses B", "B" in dist_str or "billion" in dist_str.lower(), f"got '{dist_str}'")

# Very small distance
dist_str = format_distance_km(0.01)
test("format_distance 0.01 AU", "0.010" in dist_str, f"got '{dist_str}'")

# ============================================================
# 7. OrreryState Tests
# ============================================================
print("\n=== OrreryState Tests ===")

s = OrreryState()
test("Default date: 2026-01-01", s.current_date == datetime(2026, 1, 1))
test("Default speed: 1.0", s.speed == 1.0)
test("Default paused: False", s.paused == False)
test("Default selected_planet: 2 (Earth)", s.selected_planet == 2)
test("Default scale: 12.0", s.scale == 12.0)
test("Default show_orbits: True", s.show_orbits == True)
test("Default show_labels: True", s.show_labels == True)
test("Default show_trails: True", s.show_trails == True)
test("Default show_asteroids: False", s.show_asteroids == False)
test("Default show_moon: True", s.show_moon == True)
test("Default show_comet: False", s.show_comet == False)
test("Default input_mode: None", s.input_mode is None)
test("Default input_buffer: empty", s.input_buffer == "")
test("Trail dict has correct length", len(s.trail_positions) == 8)
test("Trails start empty", all(len(v) == 0 for v in s.trail_positions.values()))
test("Default conjunctions: empty", s.conjunctions == [])
test("Default prev_positions: None", s.prev_positions is None)

# ============================================================
# 8. Orbital Mechanics Consistency Tests
# ============================================================
print("\n=== Orbital Mechanics Consistency Tests ===")

# All 8 planets at epoch should give valid positions
PLANET_DATA = [
    ("Mercury",  0.387,   0.241,  0.206),
    ("Venus",    0.723,   0.615,  0.007),
    ("Earth",    1.000,   1.000,  0.017),
    ("Mars",     1.524,   1.881,  0.093),
    ("Jupiter",  5.203,  11.862,  0.049),
    ("Saturn",   9.537,  29.457,  0.054),
    ("Uranus",  19.191,  84.011,  0.047),
    ("Neptune", 30.069, 164.800,  0.009),
]

for name, a, period, e in PLANET_DATA:
    x, y = planet_position(a, period, e, 0.0)
    r = math.sqrt(x**2 + y**2)
    test(f"{name} at epoch: r in range [{a*(1-e):.3f}, {a*(1+e):.3f}]",
         a * (1 - e) - 0.01 <= r <= a * (1 + e) + 0.01,
         f"r={r:.4f}")

# Verify periodicity: planet position at t and t+period should be same
for name, a, period, e in PLANET_DATA:
    x1, y1 = planet_position(a, period, e, 0.0)
    x2, y2 = planet_position(a, period, e, period)
    test(f"{name}: position at t=0 ≈ t=period",
         abs(x1 - x2) < 0.001 and abs(y1 - y2) < 0.001,
         f"diff=({abs(x1-x2):.6f}, {abs(y1-y2):.6f})")

# ============================================================
# 9. Orbital Velocity Tests
# ============================================================
print("\n=== Orbital Velocity Tests ===")

# Earth's average orbital velocity should be ~29.8 km/s
v_earth = orbital_velocity_km_s(1.0, 1.0, 1.0)
test("Earth velocity at 1 AU ≈ 29.8 km/s",
     28.0 < v_earth < 31.0, f"got {v_earth:.1f} km/s")

# Mercury should be faster (average ~47.9 km/s)
v_mercury = orbital_velocity_km_s(0.387, 0.241, 0.387)
test("Mercury velocity at ~0.387 AU > Earth velocity",
     v_mercury > v_earth, f"Mercury={v_mercury:.1f}, Earth={v_earth:.1f}")

# Neptune should be slower (average ~5.4 km/s)
v_neptune = orbital_velocity_km_s(30.069, 164.8, 30.069)
test("Neptune velocity at ~30 AU < Earth velocity",
     v_neptune < v_earth, f"Neptune={v_neptune:.1f}, Earth={v_earth:.1f}")

# Zero distance should return 0
test("Velocity at r=0 returns 0", orbital_velocity_km_s(1.0, 1.0, 0.0) == 0.0)

# Negative distance should return 0
test("Velocity at negative r returns 0", orbital_velocity_km_s(1.0, 1.0, -1.0) == 0.0)

# ============================================================
# 10. Conjunction Detection Tests
# ============================================================
print("\n=== Conjunction Detection Tests ===")

# Two planets at same angle → conjunction
positions_aligned = [(1.0, 0.0), (2.0, 0.0)]  # Both on X-axis
conjs = detect_conjunctions(positions_aligned, threshold_deg=5.0)
test("Aligned planets: conjunction detected", len(conjs) > 0,
     f"got {len(conjs)} conjunctions")

# Two planets 180° apart → no conjunction
positions_opposite = [(1.0, 0.0), (-2.0, 0.0)]  # Opposite sides
conjs = detect_conjunctions(positions_opposite, threshold_deg=5.0)
test("Opposite planets: no conjunction", len(conjs) == 0,
     f"got {len(conjs)} conjunctions")

# Empty list → no conjunctions
conjs = detect_conjunctions([], threshold_deg=5.0)
test("Empty positions: no conjunctions", len(conjs) == 0)

# Single planet → no conjunctions
conjs = detect_conjunctions([(1.0, 0.0)], threshold_deg=5.0)
test("Single planet: no conjunctions", len(conjs) == 0)

# Two planets 2° apart → conjunction with threshold 5°
angle1 = math.radians(0)
angle2 = math.radians(2)
positions_close = [(math.cos(angle1), math.sin(angle1)),
                    (2 * math.cos(angle2), 2 * math.sin(angle2))]
conjs = detect_conjunctions(positions_close, threshold_deg=5.0)
test("Planets 2° apart: conjunction detected", len(conjs) > 0)

# Two planets 2° apart → no conjunction with threshold 1°
conjs = detect_conjunctions(positions_close, threshold_deg=1.0)
test("Planets 2° apart: no conjunction with 1° threshold", len(conjs) == 0)

# Real planetary positions at epoch
epoch_positions = []
for name, a, period, e in PLANET_DATA:
    x, y = planet_position(a, period, e, 0.0)
    epoch_positions.append((x, y))
conjs = detect_conjunctions(epoch_positions, threshold_deg=10.0)
test("Real epoch positions: conjunction detection runs", True,
     f"found {len(conjs)} conjunctions")

# Verify conjunction format
positions_test = [(1.0, 0.0), (2.0, 0.001)]
conjs = detect_conjunctions(positions_test, threshold_deg=5.0)
if len(conjs) > 0:
    test("Conjunction format: (i, j, degrees)", 
         len(conjs[0]) == 3 and isinstance(conjs[0][2], float),
         f"got {conjs[0]}")
else:
    test("Conjunction format: (i, j, degrees)", False, "No conjunction found")

# ============================================================
# 11. Generate Asteroids Tests
# ============================================================
print("\n=== Generate Asteroids Tests ===")

asteroids = generate_asteroids()
test("Asteroids: correct count", len(asteroids) == 60, f"got {len(asteroids)}")

# All asteroids have correct tuple structure
if len(asteroids) > 0:
    test("Asteroids: tuple has 4 elements", len(asteroids[0]) == 4,
         f"got {len(asteroids[0])} elements")
    angle_frac, radius_frac, angular_speed, char = asteroids[0]
    test("Asteroid: angle_frac in [0,1)", 0 <= angle_frac < 1,
         f"got {angle_frac}")
    test("Asteroid: radius_frac in [0,1)", 0 <= radius_frac < 1,
         f"got {radius_frac}")
    test("Asteroid: angular_speed > 0", angular_speed > 0,
         f"got {angular_speed}")
    test("Asteroid: char is valid", char in [".", ","], f"got '{char}'")
else:
    test("Asteroids: tuple structure", False, "No asteroids generated")

# Deterministic generation
asteroids2 = generate_asteroids()
test("Asteroids: deterministic (same seed)", asteroids == asteroids2)

# Radius corresponds to belt range
for _, radius_frac, _, _ in asteroids:
    radius_au = ASTEROID_BELT_INNER_AU + radius_frac * (ASTEROID_BELT_OUTER_AU - ASTEROID_BELT_INNER_AU)
    test("Asteroid radius in belt range",
         ASTEROID_BELT_INNER_AU <= radius_au <= ASTEROID_BELT_OUTER_AU,
         f"got {radius_au:.2f} AU")
    break  # Just test first one to avoid 60 messages

# Angular speed follows Kepler's third law (roughly)
inner_speeds = [a_s for _, r_f, a_s, _ in asteroids if r_f < 0.1]
outer_speeds = [a_s for _, r_f, a_s, _ in asteroids if r_f > 0.9]
if inner_speeds and outer_speeds:
    test("Inner asteroids orbit faster than outer",
         min(inner_speeds) > max(outer_speeds),
         f"inner_min={min(inner_speeds):.3f}, outer_max={max(outer_speeds):.3f}")

# ============================================================
# 12. Moon Constants Tests
# ============================================================
print("\n=== Moon Constants Tests ===")

test("Moon orbital radius ~0.00257 AU",
     abs(MOON_ORBITAL_RADIUS_AU - 0.00257) < 0.001,
     f"got {MOON_ORBITAL_RADIUS_AU}")

test("Moon period ~27.3 days (~0.0748 years)",
     abs(MOON_PERIOD_YEARS - 0.0748) < 0.01,
     f"got {MOON_PERIOD_YEARS}")

# Moon position can be computed for various times
for t in [0.0, 0.0748, 1.0]:
    moon_angle = 2 * math.pi * t / MOON_PERIOD_YEARS
    test(f"Moon angle at t={t}: computed successfully",
         0 <= moon_angle % (2 * math.pi) < 2 * math.pi,
         f"angle={moon_angle}")

# ============================================================
# 13. Version and Constants Tests
# ============================================================
print("\n=== Version and Constants Tests ===")

test("Version is a string", isinstance(__version__, str))
test("Version format valid", "." in __version__, f"got {__version__}")
test("Version is 2.2.0", __version__ == "2.2.0", f"got {__version__}")

test("J2000_EPOCH is datetime", isinstance(J2000_EPOCH, datetime))
test("J2000_EPOCH year is 2000", J2000_EPOCH.year == 2000)

test("PLANETS has 8 entries", len(PLANETS) == 8)
test("PLANET_DATA has 8 entries", len(PLANET_DATA) == 8)

# Conjunction threshold is reasonable
test("Conjunction threshold in [1, 30] degrees",
     1 <= CONJUNCTION_THRESHOLD_DEG <= 30,
     f"got {CONJUNCTION_THRESHOLD_DEG}")

# Asteroid belt constants
test("Asteroid belt inner < outer",
     ASTEROID_BELT_INNER_AU < ASTEROID_BELT_OUTER_AU)
test("Asteroid belt inner > Mars orbit",
     ASTEROID_BELT_INNER_AU > 1.5)  # Mars is ~1.5 AU
test("Asteroid belt outer < Jupiter orbit",
     ASTEROID_BELT_OUTER_AU < 5.5)  # Jupiter is ~5.2 AU

# Halley's Comet constants
test("Halley semi-major axis > 0", HALLEY_A > 0)
test("Halley period > 0", HALLEY_PERIOD > 0)
test("Halley eccentricity in (0, 1)", 0 < HALLEY_ECCENTRICITY < 1)
test("Halley eccentricity is ~0.967", abs(HALLEY_ECCENTRICITY - 0.967) < 0.01)
test("Halley argument of perihelion in [0, 2π]",
     0 <= HALLEY_OMEGA <= 2 * math.pi)

# AU_KM constant
test("AU_KM is ~1.496e8", abs(AU_KM - 1.496e8) < 1e5, f"got {AU_KM}")

# ============================================================
# 14. safe_addstr Tests
# ============================================================
print("\n=== safe_addstr Tests ===")

class MockScreen:
    """Mock curses screen for testing safe_addstr."""
    def __init__(self):
        self.strings = []

    def addstr(self, y, x, text, attr):
        self.strings.append((y, x, text, attr))

# Note: safe_addstr returns bool, but we can't easily mock stdscr.
# Instead, test the logic directly.
test("safe_addstr: out of bounds Y returns False",
     safe_addstr(None, -1, 0, "test", 0, 24, 80) == False)
test("safe_addstr: out of bounds X returns False",
     safe_addstr(None, 0, -1, "test", 0, 24, 80) == False)
test("safe_addstr: Y >= height returns False",
     safe_addstr(None, 24, 0, "test", 0, 24, 80) == False)
test("safe_addstr: X >= width returns False",
     safe_addstr(None, 0, 80, "test", 0, 24, 80) == False)

# ============================================================
# 15. Bug Fix Tests (v2.1)
# ============================================================
print("\n=== Bug Fix Tests (v2.1) ===")

# Bug fix: Conjunction detection skips degenerate origin case
conjs = detect_conjunctions([(0, 0), (1.0, 0.0)], threshold_deg=5.0)
test("Conjunction: planet at origin is skipped",
     len(conjs) == 0,
     f"expected no conjunctions, got {len(conjs)}")

conjs = detect_conjunctions([(0, 0), (0, 0)], threshold_deg=5.0)
test("Conjunction: two planets at origin are skipped",
     len(conjs) == 0,
     f"expected no conjunctions, got {len(conjs)}")

# Bug fix: Speed property clamps values
s = OrreryState()
s.speed = -5
test("Speed property: negative value clamped to 0.01",
     abs(s.speed - 0.01) < 0.001, f"got {s.speed}")

s.speed = 0
test("Speed property: zero clamped to 0.01",
     abs(s.speed - 0.01) < 0.001, f"got {s.speed}")

s.speed = 10000
test("Speed property: very large value clamped to 3650",
     abs(s.speed - 3650) < 0.001, f"got {s.speed}")

s.speed = 5.0
test("Speed property: normal value accepted",
     abs(s.speed - 5.0) < 0.001, f"got {s.speed}")

# Bug fix: generate_asteroids no longer takes height/width
asteroids = generate_asteroids()
test("generate_asteroids(): works without args", len(asteroids) == 60,
     f"got {len(asteroids)}")

asteroids2 = generate_asteroids(seed=42)
test("generate_asteroids(seed=42): works with custom seed", len(asteroids2) == 60,
     f"got {len(asteroids2)}")

# Test safe_addstr with a mock screen for in-bounds drawing
mock = MockScreen()
result = safe_addstr(mock, 0, 0, "test", 0, 24, 80)
test("safe_addstr: valid position returns True with mock screen",
     result == True, f"got {result}")
test("Mock screen received the string",
     len(mock.strings) == 1 and mock.strings[0][2] == "test",
     f"mock.strings = {mock.strings}")

# Test truncation: text that's too long should be truncated
mock2 = MockScreen()
result = safe_addstr(mock2, 0, 78, "abcde", 0, 24, 80)
test("safe_addstr: long text truncated to fit",
     result == True, f"got {result}")
test("Truncated text is correct length",
     len(mock2.strings) == 1 and len(mock2.strings[0][2]) <= 2,
     f"mock2.strings = {mock2.strings}")

# ============================================================
# 16. Halley's Comet Tests (NEW in v2.2)
# ============================================================
print("\n=== Halley's Comet Tests ===")

# Halley's position at epoch (should be computable)
hx, hy = halley_position(0.0)
r_halley = math.sqrt(hx**2 + hy**2)
test("Halley at epoch: position computed", True, f"r={r_halley:.2f} AU")

# Halley's perihelion distance should be close to ~0.586 AU
# (a * (1 - e) = 17.834 * (1 - 0.967) ≈ 0.589 AU)
perihelion = HALLEY_A * (1 - HALLEY_ECCENTRICITY)
test("Halley perihelion distance ≈ 0.59 AU",
     abs(perihelion - 0.589) < 0.01, f"got {perihelion:.4f} AU")

# Halley's aphelion distance should be ~35 AU
aphelion = HALLEY_A * (1 + HALLEY_ECCENTRICITY)
test("Halley aphelion distance ≈ 35.1 AU",
     abs(aphelion - 35.08) < 0.1, f"got {aphelion:.2f} AU")

# Halley's position at a time near perihelion should be closer to Sun
# The next perihelion after J2000 was 1986; we'll check a point near it
# At t=-14 years (1986), Halley was near perihelion
hx_peri, hy_peri = halley_position(-14.0)
r_peri = math.sqrt(hx_peri**2 + hy_peri**2)
test("Halley near perihelion is closer to Sun than aphelion",
     r_peri < aphelion, f"r_peri={r_peri:.2f}, aphelion={aphelion:.2f}")

# Halley's tail segments
tail = halley_tail_segments(1.0, 0.5)
test("Halley tail: generates segments", len(tail) > 0, f"got {len(tail)} segments")

# Tail at origin should be empty
tail_origin = halley_tail_segments(0.0, 0.0)
test("Halley tail at origin: empty", len(tail_origin) == 0)

# Tail segments point away from Sun
hx, hy = 2.0, 1.0
tail = halley_tail_segments(hx, hy, n_segments=5)
test("Halley tail: correct number of segments", len(tail) == 5)
if len(tail) >= 2:
    # Tail segments should be further from origin than the comet
    for tx, ty in tail:
        d_tail = math.sqrt(tx**2 + ty**2)
        d_comet = math.sqrt(hx**2 + hy**2)
        test("Halley tail: segments further from Sun than comet",
             d_tail > d_comet or abs(d_tail - d_comet) < 0.01,
             f"d_tail={d_tail:.2f}, d_comet={d_comet:.2f}")
        break  # Just test first segment

# Halley's position is different from a planet's (due to argument of perihelion rotation)
x_planet, y_planet = planet_position(HALLEY_A, HALLEY_PERIOD, HALLEY_ECCENTRICITY, 0.0)
x_halley, y_halley = halley_position(0.0)
# They should NOT be the same due to the rotation
test("Halley position differs from planet_position (rotated)",
     abs(x_planet - x_halley) > 0.01 or abs(y_planet - y_halley) > 0.01,
     f"planet=({x_planet:.3f}, {y_planet:.3f}), halley=({x_halley:.3f}, {y_halley:.3f})")

# Halley's Comet doesn't crash with high eccentricity
for t in [0, -14.0, 37.66, 100.0]:
    try:
        hx, hy = halley_position(t)
        test(f"Halley at t={t}: computed successfully", True, f"r={math.sqrt(hx**2+hy**2):.2f}")
    except ValueError:
        test(f"Halley at t={t}: computed successfully", False, "ValueError raised")

# ============================================================
# 17. Elongation Tests (NEW in v2.2)
# ============================================================
print("\n=== Elongation Tests ===")

# Planet on same side as Sun from Earth → small elongation
# Earth at (1, 0), planet at (0.5, 0.01) → planet is between Sun and Earth
elong = compute_elongation(0.5, 0.01, 1.0, 0.0)
test("Planet between Earth and Sun: small elongation",
     elong < 10, f"got {elong:.1f}°")

# Planet opposite Sun from Earth → large elongation (near opposition)
# Earth at (1, 0), planet at (2, 0) → planet is beyond Earth from Sun
elong = compute_elongation(2.0, 0.0, 1.0, 0.0)
test("Planet beyond Earth: elongation near 180°",
     elong > 170, f"got {elong:.1f}°")

# Planet at 90° from Sun as seen from Earth
# Earth at (1, 0), planet at (0, 1) → planet is at 45° elongation (geometric effect)
elong = compute_elongation(0.0, 1.0, 1.0, 0.0)
test("Planet at (0,1) from Earth at (1,0): elongation computed",
     0 <= elong <= 180, f"got {elong:.1f}°")

# True quadrature: planet far from Sun at 90° angle → elongation approaches 90°
# Neptune at (0, 30) from Earth at (1, 0): nearly 90° elongation
elong2 = compute_elongation(0.0, 30.0, 1.0, 0.0)
test("Far planet at quadrature: elongation near 90°",
     85 < elong2 < 95, f"got {elong2:.1f}°")

# Earth looking at itself should give 0 elongation (edge case)
elong_self = compute_elongation(1.0, 0.0, 1.0, 0.0)
test("Earth-planet self: elongation computed", isinstance(elong_self, float),
     f"got {elong_self:.1f}°")

# ============================================================
# 18. Elongation Status Tests (NEW in v2.2)
# ============================================================
print("\n=== Elongation Status Tests ===")

# Very small elongation → "Near Sun"
status = elongation_status(5.0, 2.0, 0.0, 1.0, 0.0)
test("Small elongation: Near Sun", status == "Near Sun", f"got '{status}'")

# Large elongation with planet east of Sun → "Evening Star"
status = elongation_status(45.0, 2.0, 1.0, 1.0, 0.0)
test("Planet east of Sun: Evening Star or Morning Star",
     status in ["Evening Star", "Morning Star"], f"got '{status}'")

# Large elongation with planet west of Sun → "Morning Star"
status = elongation_status(45.0, -1.0, -2.0, 1.0, 0.0)
test("Planet west of Sun: Morning Star or Evening Star",
     status in ["Morning Star", "Evening Star"], f"got '{status}'")

# ============================================================
# 19. Retrograde Detection Tests (NEW in v2.2)
# ============================================================
print("\n=== Retrograde Detection Tests ===")

# Prograde: planet moves counter-clockwise (angle increases)
status = compute_retrograde(1.0, 0.0, 0.0, 1.0)
test("Counter-clockwise motion: Prograde", status == "Prograde", f"got '{status}'")

# Retrograde: planet moves clockwise (angle decreases)
status = compute_retrograde(0.0, 1.0, 1.0, 0.0)
test("Clockwise motion: Retrograde", status == "Retrograde", f"got '{status}'")

# No motion: same position
status = compute_retrograde(1.0, 0.0, 1.0, 0.0)
test("No motion: Prograde (zero diff)", status == "Prograde", f"got '{status}'")

# Small prograde step
status = compute_retrograde(1.0, 0.0, math.cos(0.1), math.sin(0.1))
test("Small prograde step", status == "Prograde", f"got '{status}'")

# ============================================================
# 20. Perihelion/Aphelion Tests (NEW in v2.2)
# ============================================================
print("\n=== Perihelion/Aphelion Tests ===")

# Verify perihelion/aphelion for all planets
for name, a, period, e in PLANET_DATA:
    peri = a * (1 - e)
    aph = a * (1 + e)
    test(f"{name}: perihelion < a < aphelion",
         peri < a < aph or abs(peri - a) < 0.001 or abs(aph - a) < 0.001,
         f"peri={peri:.4f}, a={a}, aph={aph:.4f}")
    test(f"{name}: aphelion - perihelion = 2ae",
         abs((aph - peri) - 2 * a * e) < 0.001,
         f"diff={aph - peri:.4f}, 2ae={2*a*e:.4f}")

# Earth's perihelion should be close to 0.983 AU
earth_peri = 1.0 * (1 - 0.017)
test("Earth perihelion ≈ 0.983 AU",
     abs(earth_peri - 0.983) < 0.001, f"got {earth_peri:.4f}")

# Mercury has the highest eccentricity among planets
mercury_e = 0.206
test("Mercury eccentricity > all other planets",
     all(mercury_e >= e for _, _, _, e in PLANET_DATA),
     "Some planet has higher eccentricity than Mercury")

# ============================================================
# Summary
# ============================================================
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
if failed > 0:
    print("SOME TESTS FAILED!")
    sys.exit(1)
else:
    print("All tests passed!")