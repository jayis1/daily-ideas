#!/usr/bin/env python3
"""Edge case tests for Terminal Spirograph bug hunting."""
import math
import os
import sys
import tempfile
import spirograph as sp

# Test 1: r > R for hypotrochoid (invalid geometry - small circle larger than big circle)
print("Test 1: r > R for hypotrochoid")
params = {"R": 5, "r": 7, "d": 3}
points = sp.compute_curve("hypo", params, 1000)
print(f"  Points computed: {len(points)} (should work but produce odd results)")

# Test 2: Negative R
print("Test 2: Negative R")
params = {"R": -5, "r": 4, "d": 6}
points = sp.compute_curve("hypo", params, 1000)
print(f"  Points computed: {len(points)}")

# Test 3: Negative r
print("Test 3: Negative r")
params = {"R": 11, "r": -4, "d": 6}
try:
    points = sp.compute_curve("hypo", params, 1000)
    print(f"  Points computed: {len(points)}")
except Exception as e:
    print(f"  Exception: {e}")

# Test 4: Very large parameters
print("Test 4: Very large parameters")
params = {"R": 100000, "r": 1, "d": 1}
points = sp.compute_curve("hypo", params, 1000)
print(f"  Points computed: {len(points)}")

# Test 5: SVG export with path traversal
print("Test 5: SVG export - path traversal check")
with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
    safe_path = f.name
try:
    sp.export_svg([(1,2),(3,4)], "hypo", {"R":11,"r":4,"d":6}, safe_path)
    print(f"  SVG exported successfully")
finally:
    os.unlink(safe_path)

# Test 6: SVG export with special chars in label
print("Test 6: SVG export with special chars")
params = {"a": 3, "b": 4, "delta": math.pi/2, "d": 10}
points = sp.compute_curve("lissajous", params, 100)
with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
    filepath = f.name
try:
    sp.export_svg(points, "lissajous", params, filepath)
    with open(filepath) as f:
        content = f.read()
    # Check for XML injection - the delta value (math.pi/2) is a float, should be safe
    print(f"  SVG exported, content length: {len(content)}")
finally:
    os.unlink(filepath)

# Test 7: Rose curve with k=0
print("Test 7: Rose curve with k=0")
params = {"k": 0, "n": 3, "d": 10}
points = sp.compute_curve("rose", params, 1000)
print(f"  Points computed: {len(points)}")
# With k=0, cos(0) = 1, so r=d, all points would be at (d*cos(t), d*sin(t)) = circle
if points:
    x0, y0 = points[0]
    print(f"  First point: ({x0:.4f}, {y0:.4f}) - should be (10, 0)")

# Test 8: Rose curve with very large k/n ratio
print("Test 8: Rose curve with k=100, n=1")
params = {"k": 100, "n": 1, "d": 10}
points = sp.compute_curve("rose", params, 1000)
print(f"  Points computed: {len(points)}")

# Test 9: compute_curve with r=0 for epitrochoid
print("Test 9: Epitrochoid with r=0")
params = {"R": 11, "r": 0, "d": 6}
points = sp.compute_curve("epi", params, 1000)
print(f"  Points computed: {len(points)} (expected 0)")

# Test 10: Lissajous with a=0 (degenerate - vertical line)
print("Test 10: Lissajous with a=0")
params = {"a": 0, "b": 3, "delta": math.pi/2, "d": 10}
points = sp.compute_curve("lissajous", params, 100)
print(f"  Points computed: {len(points)}")

# Test 11: Render with single point
print("Test 11: Render with single point")
lines = sp.render_frame([(0, 0)], 40, 20)
print(f"  Lines: {len(lines)}, first line length: {len(lines[0])}")

# Test 12: Render with all points at same location
print("Test 12: Render with identical points")
lines = sp.render_frame([(5, 5)] * 100, 40, 20)
print(f"  Lines: {len(lines)}")

# Test 13: Very small width/height
print("Test 13: Very small dimensions")
params = {"R": 11, "r": 4, "d": 6}
points = sp.compute_curve("hypo", params, 100)
lines = sp.render_frame(points, 1, 1)
print(f"  Lines: {len(lines)}, line content: '{lines[0]}'")

# Test 14: generate_params with hypo - check r < R constraint
print("Test 14: generate_params hypo always has r < R")
for seed in range(100):
    params = sp.generate_params("hypo", seed=seed)
    if params["r"] >= params["R"]:
        print(f"  BUG: seed={seed}, r={params['r']} >= R={params['R']}")
        break
else:
    print(f"  All 100 seeds produce r < R")

# Test 15: Check t_max computation for hypotrochoid period
print("Test 15: Hypotrochoid period computation")
# For R=11, r=4: gcd=1, period = 2*pi*4/1 = 8*pi
# t_max = max(8*pi, 2*pi) * max(11, 1) = 8*pi * 11 = 88*pi
# This draws 11 loops which is correct for gcd=1
R, r = 11, 4
g = math.gcd(R, r)
period = 2 * math.pi * r / g
t_max = max(period, 2 * math.pi) * max(R // g, 1)
print(f"  R={R}, r={r}, gcd={g}, period={period:.4f}, t_max={t_max:.4f}")
print(f"  Expected: period = {2*math.pi*4:.4f}, t_max = {2*math.pi*4*11:.4f}")

# Test 16: Epitrochoid with R=9, r=3: gcd=3, period = 2*pi*3/3 = 2*pi
# t_max = max(2*pi, 2*pi) * max(3, 1) = 2*pi * 3 = 6*pi
R, r = 9, 3
g = math.gcd(R, r)
period = 2 * math.pi * r / g
t_max = max(period, 2 * math.pi) * max(R // g, 1)
print(f"  R={R}, r={r}, gcd={g}, period={period:.4f}, t_max={t_max:.4f}")

# Test 17: Preset daisy R=15, r=7: gcd=1, period=2*pi*7
# t_max = max(14*pi, 2*pi) * 15 = 14*pi*15 = 210*pi
# This is 15 * 2*pi*7 which draws 15 loops - should be correct
R, r = 15, 7
g = math.gcd(R, r)
period = 2 * math.pi * r / g
t_max = max(period, 2 * math.pi) * max(R // g, 1)
print(f"  R={R}, r={r}, gcd={g}, period={period:.4f}, t_max={t_max:.4f}")

# Test 18: Check if the period formula is actually correct for hypotrochoid
# A hypotrochoid closes when (R-r)/r * t is a multiple of 2*pi AND t is a multiple of 2*pi
# This means t must be lcm(2*pi, 2*pi*r/(R-r)) = 2*pi*r/gcd(r, R-r) = 2*pi*R/gcd(R,r)/1
# Wait, that's not right. Let me reconsider.
# Actually, for the hypotrochoid to close, we need:
# (R-r)/r * t = 2*pi*k for some integer k, AND the curve closes when t = 2*pi*n
# where n = r/gcd(R-r, r)
# The period is 2*pi * lcm(1, r/gcd(R,r)) / (R-r)/r
# Actually: the curve closes when t = 2*pi*r/gcd(R,r) is the angular range
# No: it closes at t = 2*pi * (r / gcd(R, r))
# Wait, that's what's in the code. Let me verify.
# The correct period for a hypotrochoid is 2*pi * r / gcd(R, r)
# For R=11, r=4, gcd=1: period = 2*pi*4 = 8*pi ✓
# For R=15, r=7, gcd=1: period = 2*pi*7 = 14*pi ✓
# The t_max = period * R/gcd(R,r) which gives the full curve
# For R=11, r=4: t_max = 8*pi * 11 = 88*pi — this draws 11 full rotations around
# But the curve should close at period = 8*pi, not 88*pi!
# The t_max = period * R/gcd is WRONG - it over-draws by a factor of R/gcd
print("\nTest 18: Period over-draw check")
print("  The code computes t_max = period * R/gcd, which for R=11,r=4 gives 88*pi")
print("  But the curve closes at t=8*pi (one period), so this draws 11x too many loops!")
print("  This wastes computation but doesn't produce wrong output.")

# Test 19: Check generate_params for lissajous when a=0 or b=0
print("\nTest 19: Generate params lissajous seed check")
p = sp.generate_params("lissajous", seed=42)
print(f"  a={p['a']}, b={p['b']}")
# Both a and b can be 0 since the range is 1-9, so this is fine

# Test 20: SVG export with path traversal - check if file path is sanitized
print("\nTest 20: Path security check")
# The export_svg function uses open(filepath, "w") directly without sanitization
# This allows path traversal like --export-svg ../../../etc/cron.d/malicious
print("  BUG: export_svg does not sanitize file paths - path traversal possible")

print("\nAll edge case tests complete.")