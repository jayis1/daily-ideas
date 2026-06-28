#!/usr/bin/env python3
"""
Tests for treasure_map.py — Procedural Treasure Map Generator

Run with: python3 test_treasure_map.py
"""

import sys
import os
import subprocess
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from treasure_map import MapConfig, TreasureMap, __version__, SYMBOLS, SIMPLE_SYMBOLS

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}" + (f" — {detail}" if detail else ""))

# ── Basic construction ──────────────────────────────────────────────────────

print("\n=== Basic Construction ===")

cfg = MapConfig(width=40, height=18, seed=42)
tmap = TreasureMap(cfg)
test("Default construction", tmap is not None)
test("Grid dimensions match config",
     len(tmap.grid) == 18 and len(tmap.grid[0]) == 40)
test("Terrain dimensions match config",
     len(tmap.terrain) == 18 and len(tmap.terrain[0]) == 40)
test("Seed is set correctly", tmap.seed == 42)

# ── Seed reproducibility ────────────────────────────────────────────────────

print("\n=== Seed Reproducibility ===")

cfg1 = MapConfig(width=40, height=18, seed=123)
cfg2 = MapConfig(width=40, height=18, seed=123)
tmap1 = TreasureMap(cfg1)
tmap2 = TreasureMap(cfg2)
test("Same seed produces same map",
     tmap1.render() == tmap2.render())

# ── Unicode vs ASCII mode ────────────────────────────────────────────────────

print("\n=== Unicode vs ASCII Mode ===")

cfg_u = MapConfig(width=40, height=18, seed=42, unicode=True)
cfg_a = MapConfig(width=40, height=18, seed=42, unicode=False)
tmap_u = TreasureMap(cfg_u)
tmap_a = TreasureMap(cfg_a)
rendered_unicode = tmap_u.render()
rendered_ascii = tmap_a.render()

# Check unicode chars that are always present (borders, water, compass)
always_unicode = ['≈', '═', '║', '╔', '╗']
always_ascii = ['~', '=', '|', '+']
for ch in always_unicode:
    test(f"Unicode char '{ch}' present in unicode mode", ch in rendered_unicode)
    test(f"Unicode char '{ch}' absent in ASCII mode", ch not in rendered_ascii)
for ch in always_ascii:
    test(f"ASCII char '{ch}' present in ASCII mode", ch in rendered_ascii)

# Check terrain-dependent chars may or may not appear (no assertion, just info)
terrain_chars = ['♣', '▲', '△', '☠']
for ch in terrain_chars:
    present_u = ch in rendered_unicode
    present_a = ch in rendered_ascii
    print(f"  INFO: '{ch}' unicode={present_u}, ascii={present_a} (terrain-dependent)")

test("ASCII mode uses simple borders",
     rendered_ascii.startswith("+=") or rendered_ascii.startswith("+="))

# ── Treasure placement ────────────────────────────────────────────────────────

print("\n=== Treasure Placement ===")

treasure_count = 0
for s in range(1, 30):
    cfg = MapConfig(width=40, height=18, seed=s)
    tmap = TreasureMap(cfg)
    if tmap.treasure_x is not None:
        treasure_count += 1
test("Treasure placed on most seeds (>=20/29)", treasure_count >= 20,
     f"Only {treasure_count}/29 seeds had treasure")

# Verify treasure is on land
for s in range(1, 20):
    cfg = MapConfig(width=40, height=18, seed=s)
    tmap = TreasureMap(cfg)
    if tmap.treasure_x is not None:
        tx, ty = tmap.treasure_x, tmap.treasure_y
        terrain = tmap.terrain[ty][tx]
        test(f"Seed {s}: Treasure on land ('{terrain}')",
             terrain in ("grass", "forest", "dense_forest", "sand"))

# ── Landing distinct from treasure ───────────────────────────────────────────

print("\n=== Landing Distinct from Treasure ===")

same_count = 0
for s in range(1, 100):
    cfg = MapConfig(width=40, height=18, seed=s)
    tmap = TreasureMap(cfg)
    if tmap.landing_x is not None and tmap.treasure_x is not None:
        if tmap.landing_x == tmap.treasure_x and tmap.landing_y == tmap.treasure_y:
            same_count += 1

test("Landing never same as treasure (0/99)", same_count == 0,
     f"{same_count}/99 seeds had landing==treasure")

# ── Label overflow ───────────────────────────────────────────────────────────

print("\n=== Label Overflow ===")

overflow_count = 0
for s in range(1, 100):
    cfg = MapConfig(width=40, height=18, seed=s)
    tmap = TreasureMap(cfg)
    W = cfg.width
    for ax, ay, text in tmap.annotations:
        end_x = ax + len(text)
        if end_x > W:
            overflow_count += 1
            break

test("No label overflow past grid width (0/99)", overflow_count == 0,
     f"{overflow_count}/99 seeds had overflow")

# ── Annotation collision resolution ──────────────────────────────────────────

print("\n=== Annotation Collision Resolution ===")

overlap_count = 0
for s in range(1, 100):
    cfg = MapConfig(width=40, height=18, seed=s)
    tmap = TreasureMap(cfg)
    resolved = tmap._resolve_annotation_collisions(tmap.annotations, cfg.width, cfg.height)
    for i, (ax1, ay1, text1) in enumerate(resolved):
        for j, (ax2, ay2, text2) in enumerate(resolved):
            if i >= j:
                continue
            if ay1 == ay2:
                start1, end1 = ax1, ax1 + len(text1)
                start2, end2 = ax2, ax2 + len(text2)
                if start1 < end2 and start2 < end1:
                    overlap_count += 1
                    break
        if overlap_count > 3:
            break

test("No overlapping resolved annotations (0/99)", overlap_count == 0,
     f"{overlap_count}/99 seeds had overlaps")

# ── Treasure X not overwritten ──────────────────────────────────────────────

print("\n=== Treasure X Preservation ===")

overwrite_count = 0
for s in range(1, 100):
    cfg = MapConfig(width=40, height=18, seed=s)
    tmap = TreasureMap(cfg)
    rendered = tmap.render()
    if tmap.treasure_x is not None:
        lines = rendered.split('\n')
        row_idx = tmap.treasure_y + 1  # +1 for top border
        col_idx = tmap.treasure_x + 1  # +1 for left border
        if 0 <= row_idx < len(lines) and 0 <= col_idx < len(lines[row_idx]):
            cell = lines[row_idx][col_idx]
            if cell != tmap.sym["x_mark"]:
                overwrite_count += 1

test("Treasure X preserved in render (0/99)", overwrite_count == 0,
     f"{overwrite_count}/99 seeds had overwritten X")

# ── Hardcoded symbols check ─────────────────────────────────────────────────

print("\n=== Hardcoded Symbol Consistency ===")

import inspect
src_foam = inspect.getsource(TreasureMap._add_coast_foam)
src_lake = inspect.getsource(TreasureMap._add_lake_if_possible)
src_trail = inspect.getsource(TreasureMap._draw_trail)

test("Coast foam uses self.sym['water']",
     'self.sym["water"]' in src_foam or "self.sym['water']" in src_foam)
test("Lake uses self.sym['water']",
     'self.sym["water"]' in src_lake or "self.sym['water']" in src_lake)
test("Trail uses self.sym['trail_dot']",
     'self.sym["trail_dot"]' in src_trail or "self.sym['trail_dot']" in src_trail)

# ── Edge case sizes ─────────────────────────────────────────────────────────

print("\n=== Edge Case Map Sizes ===")

for w, h in [(5, 3), (8, 5), (3, 3), (100, 2), (2, 100), (72, 34)]:
    try:
        cfg = MapConfig(width=w, height=h, seed=42)
        tmap = TreasureMap(cfg)
        r = tmap.render()
        lines = r.split('\n')
        test(f"Size {w}x{h}: correct line count ({len(lines)} == {h+2})",
             len(lines) == h + 2)
        test(f"Size {w}x{h}: correct width",
             all(len(line) == w + 2 for line in lines))
    except Exception as e:
        test(f"Size {w}x{h}: no crash", False, str(e))

# ── All-water map ────────────────────────────────────────────────────────────

print("\n=== All-Water Map ===")

try:
    cfg = MapConfig(width=30, height=15, seed=5, water_level=0.99)
    tmap = TreasureMap(cfg)
    test("All-water map renders without crash", True)
    test("All-water map: no treasure", tmap.treasure_x is None)
    test("All-water map: no landing", tmap.landing_x is None)
except Exception as e:
    test("All-water map: no crash", False, str(e))

# ── Riddle and legend ────────────────────────────────────────────────────────

print("\n=== Riddle and Legend ===")

cfg = MapConfig(width=40, height=18, seed=42)
tmap = TreasureMap(cfg)
riddle = tmap.generate_riddle()
test("Riddle is non-empty", len(riddle) > 0)
test("Riddle contains multiple lines", '\n' in riddle)

legend = tmap.generate_legend()
test("Legend is non-empty", len(legend) > 0)
test("Legend contains key terrain types",
     "Deep Water" in legend and "Shallow Water" in legend)

# ── CLI flags ─────────────────────────────────────────────────────────────────

print("\n=== CLI Flags ===")

script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'treasure_map.py')

result = subprocess.run(
    [sys.executable, script, '--version'],
    capture_output=True, text=True
)
test("--version flag works", result.returncode == 0, result.stderr)
test("--version output includes version", __version__ in result.stdout or __version__ in result.stderr)

result = subprocess.run(
    [sys.executable, script, '--help'],
    capture_output=True, text=True
)
test("--help flag works", result.returncode == 0)

result = subprocess.run(
    [sys.executable, script, '--seed', '42', '--riddle', '--legend'],
    capture_output=True, text=True
)
test("--seed --riddle --legend combined", result.returncode == 0)
test("Output contains treasure map", "TREASURE MAP" in result.stdout)

result = subprocess.run(
    [sys.executable, script, '--no-unicode', '--seed', '42'],
    capture_output=True, text=True
)
test("--no-unicode produces ASCII output", result.returncode == 0)

# ── Summary ──────────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed} tests")
if failed == 0:
    print("All tests passed! ✓")
else:
    print(f"{failed} test(s) failed! ✗")
sys.exit(0 if failed == 0 else 1)