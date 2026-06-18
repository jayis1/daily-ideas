#!/usr/bin/env python3
"""Comprehensive test suite for voronoi.py v2.0.0 — verifies all features and bug fixes"""

import math
import random
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import voronoi as v

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}: {detail}")

def test_seed_generators():
    print("\n=== Seed Generators ===")
    for name, gen in v.SEED_TYPES.items():
        seeds = gen(10, 80, 48)
        check(f"{name}(10)", len(seeds) == 10, f"got {len(seeds)}")
        
        # All seeds within bounds (with some tolerance for jitter)
        in_bounds = all(-10 <= s[0] <= 90 and -10 <= s[1] <= 58 for s in seeds)
        check(f"{name}(10) in bounds", in_bounds)
        
        # Zero seeds
        seeds0 = gen(0, 80, 48)
        check(f"{name}(0)", len(seeds0) == 0, f"got {len(seeds0)}")
        
        # One seed
        seeds1 = gen(1, 80, 48)
        check(f"{name}(1)", len(seeds1) == 1, f"got {len(seeds1)}")

def test_hexagonal_seeds():
    """Test the new hexagonal seed pattern specifically."""
    print("\n=== Hexagonal Seed Pattern ===")
    # Basic generation
    seeds = v.seeds_hexagonal(20, 80, 48)
    check("hexagonal(20) count", len(seeds) == 20, f"got {len(seeds)}")
    
    # Zero seeds
    seeds0 = v.seeds_hexagonal(0, 80, 48)
    check("hexagonal(0)", len(seeds0) == 0)
    
    # One seed — should be centered
    seeds1 = v.seeds_hexagonal(1, 80, 48)
    check("hexagonal(1) count", len(seeds1) == 1)
    check("hexagonal(1) centered", abs(seeds1[0][0] - 40) < 1 and abs(seeds1[0][1] - 24) < 1,
          f"got ({seeds1[0][0]}, {seeds1[0][1]})")
    
    # Many seeds — should still produce valid output
    seeds_large = v.seeds_hexagonal(100, 160, 96)
    check("hexagonal(100) count", len(seeds_large) == 100)

def test_palette_generators():
    print("\n=== Palette Generators ===")
    for name, gen in v.PALETTES.items():
        colors = gen(15)
        check(f"{name}(15) count", len(colors) == 15)
        check(f"{name}(15) valid range", all(isinstance(c, int) and 0 <= c <= 255 for c in colors))
        
        colors0 = gen(0)
        check(f"{name}(0) count", len(colors0) == 0)

def test_aurora_palette():
    """Test the new aurora palette specifically."""
    print("\n=== Aurora Palette ===")
    colors = v.palette_aurora(10)
    check("aurora(10) count", len(colors) == 10)
    check("aurora(10) valid range", all(isinstance(c, int) and 0 <= c <= 255 for c in colors))
    
    # Aurora should produce varied colors (not all the same)
    check("aurora(10) varied", len(set(colors)) >= 3, f"only {len(set(colors))} unique colors")
    
    colors0 = v.palette_aurora(0)
    check("aurora(0) count", len(colors0) == 0)

def test_distance_metrics():
    print("\n=== Distance Metrics ===")
    for name, fn in v.DISTANCES.items():
        # Returns a number
        d = fn(0, 0, 3, 4)
        check(f"{name} returns number", isinstance(d, (int, float)))
        
        # Same point = 0 distance (or close for cosine at origin)
        d_same = fn(5, 5, 5, 5)
        if name == "cosine":
            check(f"{name}(same point)", d_same < 1e-9, f"got {d_same}")
        else:
            check(f"{name}(same point)", abs(d_same) < 1e-9, f"got {d_same}")
        
        # Symmetry
        d1 = fn(0, 0, 3, 4)
        d2 = fn(3, 4, 0, 0)
        check(f"{name} symmetric", abs(d1 - d2) < 1e-9, f"{d1} != {d2}")
        
        # Non-negative
        check(f"{name} non-negative", fn(10, 10, 0, 0) >= 0)

def test_cosine_edge_cases():
    print("\n=== Cosine Distance Edge Cases ===")
    # Identical points at origin — should be 0 (fallback to Euclidean)
    d = v.dist_cosine(0, 0, 0, 0)
    check("cosine(0,0,0,0)=0", d < 1e-9, f"got {d}")
    
    # Same direction from origin
    d = v.dist_cosine(1, 1, 2, 2)
    check("cosine same direction", d < 1e-9, f"got {d}")
    
    # Opposite direction
    d = v.dist_cosine(1, 1, -1, -1)
    check("cosine opposite direction", d > 1.9, f"got {d}")
    
    # Origin to point (falls back to Euclidean)
    d = v.dist_cosine(0, 0, 5, 5)
    expected = math.sqrt(50)
    check("cosine origin fallback", abs(d - expected) < 1e-6, f"got {d}, expected {expected}")

def test_voronoi_computation():
    print("\n=== Voronoi Computation ===")
    seeds = [(10, 10), (30, 30)]
    grid = v.compute_voronoi(seeds, 40, 40, v.dist_euclidean)
    check("basic grid size", len(grid) == 40 and all(len(r) == 40 for r in grid))
    check("(0,0) closer to seed 0", grid[0][0] == 0)
    check("(39,39) closer to seed 1", grid[39][39] == 1)

def test_voronoi_info():
    """Test the new diagram statistics function."""
    print("\n=== Voronoi Info ===")
    seeds = [(10, 10), (30, 30)]
    grid = v.compute_voronoi(seeds, 40, 40, v.dist_euclidean)
    info = v.compute_voronoi_info(seeds, grid, 40, 40)
    
    check("info has cell_areas", "cell_areas" in info)
    check("info has total_pixels", info["total_pixels"] == 1600, f"got {info['total_pixels']}")
    check("info num_cells", info["num_cells"] == 2)
    check("info cell areas sum", sum(info["cell_areas"].values()) == 1600)
    
    # Empty grid
    info_empty = v.compute_voronoi_info([], [], 0, 0)
    check("info empty", info_empty["total_pixels"] == 0)

def test_empty_and_edge_cases():
    print("\n=== Empty & Edge Cases ===")
    # Empty seeds → empty grid
    grid = v.compute_voronoi([], 10, 10, v.dist_euclidean)
    check("empty seeds → empty grid", grid == [])
    
    grid, dist_grid = v.compute_voronoi_with_distance([], 10, 10, v.dist_euclidean)
    check("empty seeds → empty grid+dist", grid == [] and dist_grid == [])
    
    # Zero dimensions → empty grid
    grid = v.compute_voronoi([(5,5)], 0, 10, v.dist_euclidean)
    check("0-width → empty grid", grid == [])
    
    grid = v.compute_voronoi([(5,5)], 10, 0, v.dist_euclidean)
    check("0-height → empty grid", grid == [])
    
    # Single seed
    grid = v.compute_voronoi([(5,5)], 10, 10, v.dist_euclidean)
    check("single seed all cells = 0", all(c == 0 for r in grid for c in r))
    
    # 1x1 grid
    grid = v.compute_voronoi([(0,0)], 1, 1, v.dist_euclidean)
    check("1x1 grid", grid == [[0]])

def test_render_block():
    print("\n=== Render Block ===")
    seeds = [(10, 10), (30, 30)]
    colors = v.palette_rainbow(2)
    grid, dist_grid = v.compute_voronoi_with_distance(seeds, 40, 40, v.dist_euclidean)
    
    # Normal render
    lines = v.render_block(colors, grid, dist_grid, 40, 40, mode="filled", show_borders=False)
    check("filled render row count", len(lines) == 20)
    
    # Outline render
    lines = v.render_block(colors, grid, dist_grid, 40, 40, mode="outline", show_borders=True)
    check("outline render row count", len(lines) == 20)
    
    # Empty grid → empty result
    lines = v.render_block([], [], None, 10, 10, mode="filled", show_borders=False)
    check("empty grid render", lines == [])
    
    # No dist_grid with borders (should work, borders silently disabled)
    lines = v.render_block(colors, grid, None, 40, 40, mode="filled", show_borders=True)
    check("no dist_grid with borders", len(lines) == 20)
    
    # No dist_grid without borders (should work fine)
    lines = v.render_block(colors, grid, None, 40, 40, mode="filled", show_borders=False)
    check("no dist_grid without borders", len(lines) == 20)

def test_render_gradient():
    """Test the new gradient rendering mode."""
    print("\n=== Render Gradient ===")
    seeds = [(10, 10), (30, 30)]
    colors = v.palette_rainbow(2)
    grid, dist_grid = v.compute_voronoi_with_distance(seeds, 40, 40, v.dist_euclidean)
    
    # Gradient render with borders
    lines = v.render_gradient_block(colors, grid, dist_grid, 40, 40,
                                      show_borders=True, show_seeds=False, seeds=seeds)
    check("gradient render row count", len(lines) == 20)
    
    # Gradient render without borders
    lines = v.render_gradient_block(colors, grid, dist_grid, 40, 40,
                                      show_borders=False, show_seeds=False, seeds=seeds)
    check("gradient no borders", len(lines) == 20)
    
    # Empty grid → empty result
    lines = v.render_gradient_block([], [], None, 10, 10,
                                      show_borders=False, show_seeds=False, seeds=[])
    check("gradient empty grid", lines == [])

def test_render_small_sizes():
    print("\n=== Small Render Sizes ===")
    seeds = [(1, 1)]
    colors = v.palette_rainbow(1)
    for w, h in [(1, 1), (2, 2), (1, 10), (10, 1)]:
        grid, dist_grid = v.compute_voronoi_with_distance(seeds, w, h, v.dist_euclidean)
        lines = v.render_block(colors, grid, dist_grid, w, h, mode="filled", show_borders=False)
        expected = (h + 1) // 2
        check(f"{w}x{h} render", len(lines) == expected, f"got {len(lines)}, expected {expected}")

def test_color_utilities():
    """Test color conversion and manipulation utilities."""
    print("\n=== Color Utilities ===")
    # _ansi_to_rgb round-trip for color cube
    for idx in [16, 17, 100, 200, 231]:
        r, g, b = v._ansi_to_rgb(idx)
        back = v._rgb_to_256(r, g, b)
        check(f"ansi_to_rgb({idx}) round-trip", back == idx,
              f"got {back} (rgb=({r},{g},{b}))")
    
    # _darken_color should produce a valid ANSI index
    for idx in [196, 46, 21]:
        dark = v._darken_color(idx, 0.5)
        check(f"darken({idx}, 0.5) valid", isinstance(dark, int) and 0 <= dark <= 255,
              f"got {dark}")
    
    # _lighten_color should produce a valid ANSI index
    for idx in [196, 46, 21]:
        light = v._lighten_color(idx, 0.5)
        check(f"lighten({idx}, 0.5) valid", isinstance(light, int) and 0 <= light <= 255,
              f"got {light}")
    
    # Darkening then lightening should roughly recover
    original = 196  # bright red
    dark = v._darken_color(original, 0.5)
    light_back = v._lighten_color(dark, 0.6)
    check("darken→lighten reasonable", isinstance(light_back, int))

def test_svg_export():
    """Test the SVG export functionality."""
    print("\n=== SVG Export ===")
    import tempfile
    
    seeds = [(10, 10), (30, 30)]
    colors = v.palette_rainbow(2)
    grid, dist_grid = v.compute_voronoi_with_distance(seeds, 20, 20, v.dist_euclidean)
    
    # Export to temp file
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w") as f:
        tmp_path = f.name
    
    try:
        result = v.export_svg(seeds, grid, colors, 20, 20, tmp_path,
                              palette_name="rainbow", dist_name="euclidean",
                              seed_type="random")
        check("svg export success", result)
        
        # Read and verify SVG content
        with open(tmp_path, 'r') as f:
            svg_content = f.read()
        
        check("svg has header", '<?xml' in svg_content)
        check("svg has <svg>", '<svg' in svg_content)
        check("svg has circles", '<circle' in svg_content)
        check("svg has title", '<title>' in svg_content)
        check("svg has desc", '<desc>' in svg_content)
        check("svg has closing tag", '</svg>' in svg_content)
        check("svg has paths", '<path' in svg_content)
    finally:
        os.unlink(tmp_path)
    
    # Export with empty grid should handle gracefully
    result_empty = v.export_svg([], [], [], 10, 10, "/dev/null")
    check("svg export empty grid", result_empty is False or result_empty is True)  # should not crash

def test_cli_validation():
    print("\n=== CLI Input Validation ===")
    base = [sys.executable, 'voronoi.py', '--width', '20', '--height', '10', '--seed', '42']
    cwd = os.path.dirname(os.path.abspath(__file__))
    
    # --seeds 0 should be rejected
    result = subprocess.run(base + ['--seeds', '0'], capture_output=True, text=True, timeout=10, cwd=cwd)
    check("--seeds 0 rejected", result.returncode != 0, f"exit code {result.returncode}")
    
    # --seeds -1 should be rejected
    result = subprocess.run(base + ['--seeds', '-1'], capture_output=True, text=True, timeout=10, cwd=cwd)
    check("--seeds -1 rejected", result.returncode != 0, f"exit code {result.returncode}")
    
    # --delay 0 should be rejected
    result = subprocess.run(base + ['--seeds', '5', '--delay', '0'], capture_output=True, text=True, timeout=10, cwd=cwd)
    check("--delay 0 rejected", result.returncode != 0, f"exit code {result.returncode}")
    
    # --delay -1 should be rejected
    result = subprocess.run(base + ['--seeds', '5', '--delay', '-0.1'], capture_output=True, text=True, timeout=10, cwd=cwd)
    check("--delay -0.1 rejected", result.returncode != 0, f"exit code {result.returncode}")
    
    # Normal usage should work
    result = subprocess.run(base + ['--seeds', '5'], capture_output=True, text=True, timeout=10, cwd=cwd)
    check("normal usage works", result.returncode == 0, f"exit code {result.returncode}")

def test_cli_combinations():
    print("\n=== CLI Combinations ===")
    base = [sys.executable, 'voronoi.py', '--seeds', '5', '--width', '20', '--height', '10', '--seed', '42']
    cwd = os.path.dirname(os.path.abspath(__file__))
    
    for dist in v.DISTANCES:
        result = subprocess.run(base + ['--distance', dist], capture_output=True, text=True, timeout=30, cwd=cwd)
        check(f"distance={dist}", result.returncode == 0, f"exit {result.returncode}")
    
    for pal in v.PALETTES:
        result = subprocess.run(base + ['--palette', pal], capture_output=True, text=True, timeout=30, cwd=cwd)
        check(f"palette={pal}", result.returncode == 0, f"exit {result.returncode}")
    
    for st in v.SEED_TYPES:
        result = subprocess.run(base + ['--seed-type', st], capture_output=True, text=True, timeout=30, cwd=cwd)
        check(f"seed-type={st}", result.returncode == 0, f"exit {result.returncode}")
    
    # Outline mode
    result = subprocess.run(base + ['--mode', 'outline'], capture_output=True, text=True, timeout=30, cwd=cwd)
    check("mode=outline", result.returncode == 0)
    
    # Gradient mode (new!)
    result = subprocess.run(base + ['--mode', 'gradient'], capture_output=True, text=True, timeout=30, cwd=cwd)
    check("mode=gradient", result.returncode == 0)
    
    # Borders
    result = subprocess.run(base + ['--borders'], capture_output=True, text=True, timeout=30, cwd=cwd)
    check("--borders", result.returncode == 0)
    
    # Seeds visible
    result = subprocess.run(base + ['--seeds-visible'], capture_output=True, text=True, timeout=30, cwd=cwd)
    check("--seeds-visible", result.returncode == 0)
    
    # Outline + borders
    result = subprocess.run(base + ['--mode', 'outline', '--borders'], capture_output=True, text=True, timeout=30, cwd=cwd)
    check("outline+borders", result.returncode == 0)
    
    # Gradient + borders (new combo!)
    result = subprocess.run(base + ['--mode', 'gradient', '--borders'], capture_output=True, text=True, timeout=30, cwd=cwd)
    check("gradient+borders", result.returncode == 0)
    
    # Hexagonal seed type (new!)
    result = subprocess.run(base + ['--seed-type', 'hexagonal'], capture_output=True, text=True, timeout=30, cwd=cwd)
    check("seed-type=hexagonal", result.returncode == 0)
    
    # Aurora palette (new!)
    result = subprocess.run(base + ['--palette', 'aurora'], capture_output=True, text=True, timeout=30, cwd=cwd)
    check("palette=aurora", result.returncode == 0)
    
    # --version
    result = subprocess.run([sys.executable, 'voronoi.py', '--version'], capture_output=True, text=True, timeout=10, cwd=cwd)
    check("--version", result.returncode == 0 and "2.0.0" in result.stdout, f"got '{result.stdout.strip()}'")
    
    # --help should work
    result = subprocess.run([sys.executable, 'voronoi.py', '--help'], capture_output=True, text=True, timeout=10, cwd=cwd)
    check("--help", result.returncode == 0)
    check("--help mentions gradient", "gradient" in result.stdout)
    check("--help mentions aurora", "aurora" in result.stdout)
    check("--help mentions hexagonal", "hexagonal" in result.stdout)
    check("--help mentions export", "export" in result.stdout.lower())
    check("--help mentions info", "info" in result.stdout.lower())

def test_cli_info_and_export():
    """Test --info and --export CLI flags."""
    print("\n=== CLI Info & Export ===")
    import tempfile
    base = [sys.executable, 'voronoi.py', '--seeds', '5', '--width', '20', '--height', '10', '--seed', '42']
    cwd = os.path.dirname(os.path.abspath(__file__))
    
    # --info should work
    result = subprocess.run(base + ['--info'], capture_output=True, text=True, timeout=30, cwd=cwd)
    check("--info works", result.returncode == 0, f"exit {result.returncode}")
    check("--info output has stats", "Statistics" in result.stdout or "cell" in result.stdout.lower(),
          "missing statistics in output")
    
    # --export should work
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        tmp_svg = f.name
    
    try:
        result = subprocess.run(base + ['--export', tmp_svg], capture_output=True, text=True, timeout=30, cwd=cwd)
        check("--export works", result.returncode == 0, f"exit {result.returncode}")
        check("--export creates file", os.path.exists(tmp_svg) and os.path.getsize(tmp_svg) > 0,
              "SVG file missing or empty")
        check("--export mentions file", "Exported SVG" in result.stdout,
              f"missing export message, got: {result.stdout[-200:]}")
    finally:
        if os.path.exists(tmp_svg):
            os.unlink(tmp_svg)

def test_color_math():
    print("\n=== Color Math ===")
    # Pure colors
    r, g, b = v._hsv_to_rgb(0, 1.0, 1.0)
    check("pure red", (r, g, b) == (255, 0, 0), f"got ({r},{g},{b})")
    
    r, g, b = v._hsv_to_rgb(120, 1.0, 1.0)
    check("pure green", (r, g, b) == (0, 255, 0), f"got ({r},{g},{b})")
    
    r, g, b = v._hsv_to_rgb(240, 1.0, 1.0)
    check("pure blue", (r, g, b) == (0, 0, 255), f"got ({r},{g},{b})")
    
    # h=360 should equal h=0
    r1, g1, b1 = v._hsv_to_rgb(0, 1.0, 1.0)
    r2, g2, b2 = v._hsv_to_rgb(360, 1.0, 1.0)
    check("h=360 == h=0", (r1,g1,b1) == (r2,g2,b2))
    
    # Negative h should wrap
    r1, g1, b1 = v._hsv_to_rgb(-30, 1.0, 1.0)
    r2, g2, b2 = v._hsv_to_rgb(330, 1.0, 1.0)
    check("h=-30 == h=330", (r1,g1,b1) == (r2,g2,b2))
    
    # s=0 should be gray
    r, g, b = v._hsv_to_rgb(180, 0.0, 0.5)
    check("s=0 is gray", r == g == b, f"got ({r},{g},{b})")
    
    # v=0 should be black
    r, g, b = v._hsv_to_rgb(180, 1.0, 0.0)
    check("v=0 is black", (r, g, b) == (0, 0, 0), f"got ({r},{g},{b})")
    
    # Black maps to ANSI 16
    idx = v._rgb_to_256(0, 0, 0)
    check("black → ANSI 16", idx == 16, f"got {idx}")

def test_seed_markers():
    print("\n=== Seed Markers ===")
    seeds = [(10, 10), (30, 30)]
    colors = v.palette_rainbow(2)
    markers = v.render_seed_markers(seeds, 40, 40, colors)
    check("normal markers", len(markers) == 2)
    
    # Out of bounds markers should be filtered
    seeds_out = [(-5, -5), (100, 100)]
    markers_out = v.render_seed_markers(seeds_out, 40, 40, colors)
    check("out-of-bounds markers filtered", len(markers_out) == 0, f"got {len(markers_out)}")

# Run all tests
print("=" * 60)
print(f"VORONOI v{v.__version__} — Feature Verification Tests")
print("=" * 60)

test_seed_generators()
test_hexagonal_seeds()
test_palette_generators()
test_aurora_palette()
test_distance_metrics()
test_cosine_edge_cases()
test_voronoi_computation()
test_voronoi_info()
test_empty_and_edge_cases()
test_render_block()
test_render_gradient()
test_render_small_sizes()
test_color_utilities()
test_svg_export()
test_cli_validation()
test_cli_combinations()
test_cli_info_and_export()
test_color_math()
test_seed_markers()

print("\n" + "=" * 60)
print(f"Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
if FAIL > 0:
    print("FAILURES DETECTED!")
    sys.exit(1)
else:
    print("All tests passed!")
print("=" * 60)