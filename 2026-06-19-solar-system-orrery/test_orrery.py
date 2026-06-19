#!/usr/bin/env python3
"""
Comprehensive tests for the Solar System Orrery.
Tests orbital mechanics, screen mapping, star generation, state management,
edge cases, and bug fixes.
"""
import sys
sys.path.insert(0, '.')
import math
from datetime import datetime

from orrery import (
    solve_kepler, planet_position, au_to_screen,
    generate_stars, format_date, OrreryState, safe_addstr
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
# 6. OrreryState Tests
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
test("Default input_mode: None", s.input_mode is None)
test("Default input_buffer: empty", s.input_buffer == "")
test("Trail dict has correct length", len(s.trail_positions) == 8)
test("Trails start empty", all(len(v) == 0 for v in s.trail_positions.values()))

# ============================================================
# 7. Orbital Mechanics Consistency Tests
# ============================================================
print("\n=== Orbital Mechanics Consistency Tests ===")

# All 8 planets at epoch should give valid positions
PLANETS = [
    ("Mercury",  0.387,   0.241,  0.206),
    ("Venus",    0.723,   0.615,  0.007),
    ("Earth",    1.000,   1.000,  0.017),
    ("Mars",     1.524,   1.881,  0.093),
    ("Jupiter",  5.203,  11.862,  0.049),
    ("Saturn",   9.537,  29.457,  0.054),
    ("Uranus",  19.191,  84.011,  0.047),
    ("Neptune", 30.069, 164.800,  0.009),
]

for name, a, period, e in PLANETS:
    x, y = planet_position(a, period, e, 0.0)
    r = math.sqrt(x**2 + y**2)
    test(f"{name} at epoch: r in range [{a*(1-e):.3f}, {a*(1+e):.3f}]",
         a * (1 - e) - 0.01 <= r <= a * (1 + e) + 0.01,
         f"r={r:.4f}")

# Verify periodicity: planet position at t and t+period should be same
for name, a, period, e in PLANETS:
    x1, y1 = planet_position(a, period, e, 0.0)
    x2, y2 = planet_position(a, period, e, period)
    test(f"{name}: position at t=0 ≈ t=period",
         abs(x1 - x2) < 0.001 and abs(y1 - y2) < 0.001,
         f"diff=({abs(x1-x2):.6f}, {abs(y1-y2):.6f})")

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