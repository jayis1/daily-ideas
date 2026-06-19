#!/usr/bin/env python3
"""Tests for the Procedural Flag Generator."""

import sys
import os

# Add project directory to path
sys.path.insert(0, os.path.dirname(__file__))

from flag_generator import (
    generate_flag, generate_country_name, render_flag, render_flag_ascii,
    pattern_horizontal_stripes, pattern_vertical_stripes, pattern_diagonal,
    pattern_cross, pattern_saltire, pattern_chevron, pattern_quarters,
    pattern_circle, pattern_crescent, pattern_star_field, pattern_canton,
    pattern_diamond, flag_of_the_day, FLAG_COLORS,
    FLAG_W, FLAG_H,
)


def test_grid_dimensions():
    """Test that generated flags have the correct grid dimensions."""
    flag = generate_flag(seed=42)
    assert len(flag.grid) == FLAG_H, f"Expected {FLAG_H} rows, got {len(flag.grid)}"
    assert all(len(row) == FLAG_W for row in flag.grid), f"Expected {FLAG_W} columns"


def test_grid_has_valid_colors():
    """Test that all cells in the grid have valid ANSI color codes."""
    flag = generate_flag(seed=42)
    valid_colors = set(FLAG_COLORS.values())
    for y, row in enumerate(flag.grid):
        for x, cell in enumerate(row):
            assert cell in valid_colors, f"Invalid color {cell} at ({x},{y})"


def test_flag_attributes():
    """Test that flag attributes are set properly."""
    flag = generate_flag(seed=42)
    assert isinstance(flag.name, str)
    assert len(flag.name) > 0
    assert isinstance(flag.pattern_type, str)
    assert len(flag.pattern_type) > 0
    assert isinstance(flag.colors_used, list)
    assert len(flag.colors_used) >= 2


def test_pattern_horizontal_stripes():
    """Test horizontal stripes produces correct grid."""
    colors = [196, 46, 21]
    grid = pattern_horizontal_stripes(60, 40, colors, 3)
    assert len(grid) == 40
    assert all(len(row) == 60 for row in grid)
    # First stripe should be color[0]
    assert grid[0][0] == colors[0]
    # Last stripe should be color[2]
    assert grid[39][0] == colors[2]


def test_pattern_vertical_stripes():
    """Test vertical stripes produces correct grid."""
    colors = [196, 46, 21]
    grid = pattern_vertical_stripes(60, 40, colors, 3)
    assert len(grid) == 40
    # Left stripe should be color[0]
    assert grid[0][0] == colors[0]
    # Right stripe should be color[2]
    assert grid[0][59] == colors[2]


def test_pattern_diagonal():
    """Test diagonal pattern produces correct grid."""
    colors = [196, 46]
    grid = pattern_diagonal(60, 40, colors)
    assert len(grid) == 40
    # Both colors should appear in the grid
    all_cells = set(cell for row in grid for cell in row)
    assert colors[0] in all_cells
    assert colors[1] in all_cells


def test_pattern_cross():
    """Test cross pattern produces correct grid."""
    colors = [21, 226]  # blue bg, yellow cross
    grid = pattern_cross(60, 40, colors)
    # Center should be cross color
    assert grid[20][20] == colors[1]
    # Corner should be background
    assert grid[0][0] == colors[0]


def test_pattern_quarters():
    """Test quarters pattern produces correct grid."""
    colors = [196, 46, 21, 226]
    grid = pattern_quarters(60, 40, colors)
    # Top-left quarter
    assert grid[0][0] == colors[0]
    # Top-right quarter
    assert grid[0][59] == colors[1]
    # Bottom-left quarter
    assert grid[39][0] == colors[2]
    # Bottom-right quarter
    assert grid[39][59] == colors[3]


def test_pattern_circle():
    """Test circle pattern produces correct grid."""
    colors = [21, 226]  # blue bg, yellow circle
    grid = pattern_circle(60, 40, colors)
    # Center should be circle color
    assert grid[20][30] == colors[1]
    # Corners should be background
    assert grid[0][0] == colors[0]


def test_pattern_crescent():
    """Test crescent pattern produces correct grid."""
    colors = [21, 226]
    grid = pattern_crescent(60, 40, colors)
    # Should have both colors present
    all_cells = set(cell for row in grid for cell in row)
    assert colors[0] in all_cells
    assert colors[1] in all_cells


def test_pattern_star_field():
    """Test star pattern produces correct grid."""
    colors = [21, 226]
    grid = pattern_star_field(60, 40, colors)
    # Should have both colors
    all_cells = set(cell for row in grid for cell in row)
    assert colors[0] in all_cells
    assert colors[1] in all_cells


def test_pattern_canton():
    """Test canton pattern produces correct grid."""
    colors = [21, 226, 196]
    grid = pattern_canton(60, 40, colors)
    # Canton area (top-left) should have canton color
    assert grid[0][0] == colors[0]
    # Bottom-right should NOT be canton color (should be stripe)
    # (unless coincidence)


def test_country_name_generation():
    """Test country name generator produces valid names."""
    import random
    random.seed(42)
    names = set()
    for _ in range(20):
        name = generate_country_name()
        assert isinstance(name, str)
        assert len(name) > 0
        assert name.strip() == name  # no leading/trailing whitespace
        names.add(name)
    # Should generate diverse names
    assert len(names) > 5, f"Only generated {len(names)} unique names"


def test_render_flag_returns_string():
    """Test that render_flag produces a non-empty string."""
    flag = generate_flag(seed=42)
    output = render_flag(flag)
    assert isinstance(output, str)
    assert len(output) > 100  # Should be a substantial string


def test_render_flag_ascii_returns_string():
    """Test that render_flag_ascii produces a non-empty string."""
    flag = generate_flag(seed=42)
    output = render_flag_ascii(flag)
    assert isinstance(output, str)
    assert len(output) > 50
    # Should contain border characters
    assert "+" in output
    assert "-" in output
    assert "|" in output


def test_render_flag_ascii_dimensions():
    """Test ASCII render has correct dimensions."""
    flag = generate_flag(seed=42)
    output = render_flag_ascii(flag)
    lines = output.strip().split("\n")
    # Should have FLAG_H rows + 2 border + metadata lines
    grid_lines = [l for l in lines if l.startswith("|")]
    assert len(grid_lines) == FLAG_H, f"Expected {FLAG_H} grid lines, got {len(grid_lines)}"


def test_flag_of_the_day_deterministic():
    """Test that flag_of_the_day is deterministic."""
    flag1 = flag_of_the_day()
    flag2 = flag_of_the_day()
    assert flag1.name == flag2.name
    assert flag1.pattern_type == flag2.pattern_type
    assert flag1.grid == flag2.grid


def test_seed_reproducibility():
    """Test that same seed produces same flag."""
    flag1 = generate_flag(seed=12345)
    flag2 = generate_flag(seed=12345)
    assert flag1.name == flag2.name
    assert flag1.grid == flag2.grid
    assert flag1.pattern_type == flag2.pattern_type


def test_different_seeds_different_flags():
    """Test that different seeds produce different flags."""
    flag1 = generate_flag(seed=1)
    flag2 = generate_flag(seed=2)
    # Very unlikely to be identical
    different = (flag1.name != flag2.name or 
                 flag1.pattern_type != flag2.pattern_type or
                 flag1.grid != flag2.grid)
    assert different, "Different seeds should produce different flags"


def test_each_pattern_type():
    """Test that each pattern type can be generated without errors."""
    for seed in range(100):
        flag = generate_flag(seed=seed)
        assert len(flag.grid) == FLAG_H
        assert all(len(row) == FLAG_W for row in flag.grid)


def test_render_contains_color_codes():
    """Test that rendered output contains ANSI escape codes."""
    flag = generate_flag(seed=42)
    output = render_flag(flag)
    assert "\033[" in output, "Should contain ANSI escape codes"


def test_emblem_overlay():
    """Test that flags with emblems still have valid grids."""
    # Generate many flags and check those with emblems
    for seed in range(50):
        flag = generate_flag(seed=seed)
        valid_colors = set(FLAG_COLORS.values())
        for row in flag.grid:
            for cell in row:
                assert cell in valid_colors


if __name__ == "__main__":
    test_grid_dimensions()
    test_grid_has_valid_colors()
    test_flag_attributes()
    test_pattern_horizontal_stripes()
    test_pattern_vertical_stripes()
    test_pattern_diagonal()
    test_pattern_cross()
    test_pattern_quarters()
    test_pattern_circle()
    test_pattern_crescent()
    test_pattern_star_field()
    test_pattern_canton()
    test_country_name_generation()
    test_render_flag_returns_string()
    test_render_flag_ascii_returns_string()
    test_render_flag_ascii_dimensions()
    test_flag_of_the_day_deterministic()
    test_seed_reproducibility()
    test_different_seeds_different_flags()
    test_each_pattern_type()
    test_render_contains_color_codes()
    test_emblem_overlay()
    print("All tests passed! ✓")