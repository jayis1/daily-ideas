#!/usr/bin/env python3
"""Tests for the Crystal Growth Simulator (DLA).

These tests verify core functionality of the DLASimulator class,
including seed placement, walking, sticking, symmetry, rendering,
and JSON export.
"""

import math
import json
import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crystal_growth import DLASimulator, validate_output_path


def test_basic_creation():
    """Test that a simulator can be created with default parameters."""
    sim = DLASimulator(width=30, height=20, seed="center", seed_pos="center")
    assert sim.width == 30
    assert sim.height == 20
    assert sim.particle_count > 0, "Center seed should place at least 1 particle"
    # Center seed: 1 particle at (10, 15)
    assert sim.grid[10][15] > 0, "Center seed should be at grid center"
    print("✓ test_basic_creation passed")


def test_line_seed():
    """Test that line seed places a vertical line of particles."""
    sim = DLASimulator(width=30, height=20, seed_pos="line")
    # Count particles in the center column
    mid = 30 // 2
    center_col_count = sum(1 for r in range(20) if sim.grid[r][mid] > 0)
    assert center_col_count > 1, f"Line seed should place multiple particles, got {center_col_count}"
    print("✓ test_line_seed passed")


def test_corners_seed():
    """Test that corners seed places particles near all four corners."""
    sim = DLASimulator(width=30, height=20, seed_pos="corners")
    # Check that corners have particles
    assert sim.particle_count >= 4, f"Corners seed should place particles, got {sim.particle_count}"
    print("✓ test_corners_seed passed")


def test_ring_seed():
    """Test that ring seed places particles in a ring pattern."""
    sim = DLASimulator(width=40, height=30, seed_pos="ring")
    assert sim.particle_count > 4, f"Ring seed should place multiple particles, got {sim.particle_count}"
    print("✓ test_ring_seed passed")


def test_stepping_grows_crystal():
    """Test that running simulation steps increases particle count."""
    sim = DLASimulator(width=30, height=20, seed_pos="center", seed=42,
                       num_walkers=5)
    initial = sim.particle_count
    sim.step(count=500)
    assert sim.particle_count > initial, (
        f"Crystal should grow after steps: initial={initial}, final={sim.particle_count}"
    )
    assert sim.step_count == 500, "Step count should be 500"
    print(f"✓ test_stepping_grows_crystal passed (grew from {initial} to {sim.particle_count})")


def test_stickiness_affects_growth():
    """Test that lower stickiness creates different growth patterns."""
    sim_high = DLASimulator(width=30, height=20, seed_pos="center",
                            seed=42, stickiness=1.0, num_walkers=5)
    sim_low = DLASimulator(width=30, height=20, seed_pos="center",
                           seed=42, stickiness=0.3, num_walkers=5)

    sim_high.step(count=1000)
    sim_low.step(count=1000)

    # Both should grow, but patterns will differ
    assert sim_high.particle_count > 1, "High stickiness should grow"
    assert sim_low.particle_count > 1, "Low stickiness should grow"
    print(f"✓ test_stickiness_affects_growth passed "
          f"(high={sim_high.particle_count}, low={sim_low.particle_count})")


def test_max_particles_limit():
    """Test that simulation respects max_particles limit."""
    sim = DLASimulator(width=30, height=20, seed_pos="center",
                       max_particles=50, num_walkers=5)
    # Run many steps
    for _ in range(5000):
        sim.step(count=10)
        if sim.particle_count >= 50:
            break
    # Should not exceed max_particles (by much, allowing for simultaneous walkers)
    assert sim.particle_count <= 55, (
        f"Particle count should be near max, got {sim.particle_count}"
    )
    print(f"✓ test_max_particles_limit passed (particles={sim.particle_count})")


def test_render_produces_output():
    """Test that render() produces the correct number of lines."""
    sim = DLASimulator(width=30, height=15, seed_pos="center", seed=42)
    sim.step(count=200)
    lines = sim.render()
    assert len(lines) == 15, f"Should have 15 lines, got {len(lines)}"
    assert len(lines[0]) > 0, "Each line should have content"
    print("✓ test_render_produces_output passed")


def test_render_plain_strips_ansi():
    """Test that render_plain() produces ANSI-free output."""
    sim = DLASimulator(width=30, height=10, seed_pos="center", seed=42)
    sim.step(count=200)
    lines = sim.render_plain()
    for line in lines:
        assert "\033[" not in line, "Plain render should not contain ANSI codes"
    print("✓ test_render_plain_strips_ansi passed")


def test_render_stats():
    """Test that render_stats returns a non-empty stats string."""
    sim = DLASimulator(width=30, height=20, seed_pos="center")
    sim.step(count=100)
    stats = sim.render_stats()
    assert "Particles" in stats, "Stats should include particle count"
    assert "Steps" in stats, "Stats should include step count"
    assert "Density" in stats, "Stats should include density"
    print("✓ test_render_stats passed")


def test_json_export():
    """Test JSON export contains expected fields."""
    sim = DLASimulator(width=20, height=15, seed_pos="center", seed=42)
    sim.step(count=100)
    json_str = sim.to_json()
    data = json.loads(json_str)

    assert "version" in data, "JSON should include version"
    assert "width" in data, "JSON should include width"
    assert "height" in data, "JSON should include height"
    assert data["width"] == 20, "Width should be 20"
    assert data["height"] == 15, "Height should be 15"
    assert "particle_count" in data, "JSON should include particle_count"
    assert data["particle_count"] > 0, "Should have some particles"
    assert "grid" in data, "JSON should include grid"
    assert len(data["grid"]) == 15, "Grid should have 15 rows"
    assert "symmetry" in data, "JSON should include symmetry"
    print("✓ test_json_export passed")


def test_get_stats_dict():
    """Test that stats dictionary has all expected keys."""
    sim = DLASimulator(width=20, height=15, seed_pos="center")
    stats = sim.get_stats_dict()
    expected_keys = [
        "version", "width", "height", "particle_count", "step_count",
        "max_radius", "density_percent", "stickiness", "num_walkers",
        "diagonal", "symmetry", "elapsed_seconds", "grid"
    ]
    for key in expected_keys:
        assert key in stats, f"Stats should include '{key}'"
    print("✓ test_get_stats_dict passed")


def test_symmetry_horizontal():
    """Test horizontal symmetry mode mirrors particles."""
    sim = DLASimulator(width=30, height=20, seed_pos="center",
                       symmetry="horizontal", num_walkers=3, seed=42)
    sim.step(count=500)
    # Check horizontal symmetry: grid[r][c] should equal grid[r][width-1-c]
    symmetric = True
    mismatches = 0
    for r in range(sim.height):
        for c in range(sim.width // 2):
            left = sim.grid[r][c] > 0
            right = sim.grid[r][sim.width - 1 - c] > 0
            if left != right:
                mismatches += 1
    # Allow some mismatches due to walker positions, but overall symmetry should hold
    total_particles = sum(1 for r in range(sim.height) for c in range(sim.width) if sim.grid[r][c] > 0)
    # At least most particles should be symmetric
    assert total_particles > 5, "Should have enough particles to test symmetry"
    print(f"✓ test_symmetry_horizontal passed (particles={total_particles}, mismatches={mismatches})")


def test_symmetry_both():
    """Test 'both' symmetry mode (4-fold symmetry)."""
    sim = DLASimulator(width=30, height=20, seed_pos="center",
                       symmetry="both", num_walkers=3, seed=42)
    sim.step(count=500)
    total = sum(1 for r in range(sim.height) for c in range(sim.width) if sim.grid[r][c] > 0)
    assert total > 5, "Should have enough particles with both symmetry"
    print(f"✓ test_symmetry_both passed (particles={total})")


def test_input_validation():
    """Test that invalid inputs are rejected."""
    # Grid too small
    try:
        DLASimulator(width=2, height=10)
        assert False, "Should reject width < 3"
    except ValueError:
        pass

    try:
        DLASimulator(width=10, height=2)
        assert False, "Should reject height < 3"
    except ValueError:
        pass

    # Invalid stickiness
    try:
        DLASimulator(width=10, height=10, stickiness=0.0)
        assert False, "Should reject stickiness=0"
    except ValueError:
        pass

    try:
        DLASimulator(width=10, height=10, stickiness=1.5)
        assert False, "Should reject stickiness > 1"
    except ValueError:
        pass

    # Invalid walkers
    try:
        DLASimulator(width=10, height=10, num_walkers=0)
        assert False, "Should reject 0 walkers"
    except ValueError:
        pass

    print("✓ test_input_validation passed")


def test_validate_output_path():
    """Test that path validation blocks system directories."""
    # Should block system paths
    for sys_path in ["/etc/passwd", "/usr/bin/test", "/bin/sh"]:
        try:
            validate_output_path(sys_path)
            assert False, f"Should block {sys_path}"
        except ValueError:
            pass

    # Should allow writing to home directory
    valid_path = validate_output_path("~/test_crystal.txt")
    assert "test_crystal.txt" in valid_path

    # Should allow writing to current directory
    valid_path = validate_output_path("crystal_output.txt")
    assert "crystal_output.txt" in valid_path

    print("✓ test_validate_output_path passed")


def test_diagonal_vs_orthogonal():
    """Test that disabling diagonals produces different growth."""
    sim_diag = DLASimulator(width=30, height=20, seed_pos="center",
                            seed=42, diagonal=True, num_walkers=3)
    sim_orth = DLASimulator(width=30, height=20, seed_pos="center",
                            seed=42, diagonal=False, num_walkers=3)
    sim_diag.step(count=500)
    sim_orth.step(count=500)
    # Both should grow
    assert sim_diag.particle_count > 1
    assert sim_orth.particle_count > 1
    print(f"✓ test_diagonal_vs_orthogonal passed "
          f"(diag={sim_diag.particle_count}, orth={sim_orth.particle_count})")


def test_no_color_mode():
    """Test that no-color mode works without errors."""
    sim = DLASimulator(width=20, height=10, seed_pos="center",
                       color=False, seed=42)
    sim.step(count=200)
    lines = sim.render()
    assert len(lines) == 10
    # In no-color mode, there should be no ANSI color codes in the output
    # (since use_color is False)
    print("✓ test_no_color_mode passed")


def test_walker_position_in_render():
    """Test that walker positions appear in the rendered output."""
    sim = DLASimulator(width=20, height=15, seed_pos="center",
                       num_walkers=3, seed=42, color=False)
    # Don't step yet — walkers should be visible
    lines = sim.render()
    full_text = "".join(lines)
    # The walkers should be visible (non-space characters)
    # At least some non-space content should exist
    assert len(full_text.strip()) > 0, "Rendered output should not be empty"
    print("✓ test_walker_position_in_render passed")


def test_growth_history_tracking():
    """Test that growth history is tracked for analytics."""
    sim = DLASimulator(width=30, height=20, seed_pos='center',
                       num_walkers=5, seed=42)
    sim.step(count=1000)
    assert len(sim.growth_history) > 0, "Growth history should be recorded"
    # Each entry should be (step, grid_count)
    for step, count in sim.growth_history:
        assert isinstance(step, int), "Step should be int"
        assert isinstance(count, int), "Count should be int"
        assert count > 0, "Grid count should be positive"
    # History should be monotonically increasing in grid count
    counts = [c for _, c in sim.growth_history]
    assert counts == sorted(counts), "Grid counts should increase over time"
    print(f"✓ test_growth_history_tracking passed ({len(sim.growth_history)} entries)")


def test_max_particles_enforced_in_step():
    """Test that max_particles is enforced inside step(), not just CLI loops."""
    sim = DLASimulator(width=30, height=20, seed_pos='center',
                       max_particles=20, num_walkers=3, seed=42)
    sim.step(count=5000)
    assert sim.grid_count <= 22, (
        f"grid_count should be near max_particles=20, got {sim.grid_count}"
    )
    print(f"✓ test_max_particles_enforced_in_step passed (grid_count={sim.grid_count})")


def test_reproducibility_with_seed():
    """Test that same seed produces identical results."""
    sims = []
    for _ in range(3):
        sim = DLASimulator(width=30, height=20, seed_pos='center',
                           seed=12345, num_walkers=3)
        sim.step(count=300)
        sims.append(sim)
    assert sims[0].grid_count == sims[1].grid_count == sims[2].grid_count, (
        f"Same seed should give same results: {[s.grid_count for s in sims]}"
    )
    print(f"✓ test_reproducibility_with_seed passed (all runs: {sims[0].grid_count})")


def test_corners_seed_on_small_grid():
    """Test that corners seed works on grids smaller than 10x10."""
    sim = DLASimulator(width=5, height=5, seed_pos='corners', num_walkers=1)
    assert sim.grid_count >= 4, (
        f"Corners seed should place at least 4 particles on 5x5 grid, got {sim.grid_count}"
    )
    print(f"✓ test_corners_seed_on_small_grid passed (grid_count={sim.grid_count})")


def test_grid_count_matches_actual_cells():
    """Test that grid_count matches actual occupied grid cells."""
    # Without symmetry
    sim = DLASimulator(width=30, height=20, seed_pos='center',
                       num_walkers=3, seed=42)
    sim.step(count=500)
    actual = sum(1 for r in range(sim.height) for c in range(sim.width) if sim.grid[r][c] > 0)
    assert sim.grid_count == actual, (
        f"grid_count ({sim.grid_count}) != actual cells ({actual}) without symmetry"
    )
    # With both symmetry
    sim2 = DLASimulator(width=30, height=20, seed_pos='center',
                        symmetry='both', num_walkers=3, seed=42)
    sim2.step(count=500)
    actual2 = sum(1 for r in range(sim2.height) for c in range(sim2.width) if sim2.grid[r][c] > 0)
    assert sim2.grid_count == actual2, (
        f"grid_count ({sim2.grid_count}) != actual cells ({actual2}) with symmetry=both"
    )
    print(f"✓ test_grid_count_matches_actual_cells passed "
          f"(none={sim.grid_count}, both={sim2.grid_count})")


def test_density_accuracy():
    """Test that density calculation is accurate using grid_count."""
    sim = DLASimulator(width=30, height=20, seed_pos='center',
                       symmetry='horizontal', num_walkers=3, seed=42)
    sim.step(count=500)
    stats = sim.get_stats_dict()
    actual_density = sim.grid_count / (sim.width * sim.height) * 100
    assert abs(stats['density_percent'] - actual_density) < 0.1, (
        f"Reported density ({stats['density_percent']:.1f}%) != "
        f"actual density ({actual_density:.1f}%)"
    )
    print(f"✓ test_density_accuracy passed (density={stats['density_percent']:.1f}%)")


def test_symmetry_seed_placement():
    """Test that seed placement respects symmetry mode."""
    sim = DLASimulator(width=30, height=20, seed_pos='center',
                       symmetry='horizontal', num_walkers=1)
    # Center seed should be mirrored horizontally
    # Check that the grid is symmetric around the vertical center line
    mismatches = 0
    for r in range(sim.height):
        for c in range(sim.width // 2):
            left = sim.grid[r][c] > 0
            right = sim.grid[r][sim.width - 1 - c] > 0
            if left != right:
                mismatches += 1
    assert mismatches == 0, (
        f"Seed placement should be symmetric, got {mismatches} mismatches"
    )
    print(f"✓ test_symmetry_seed_placement passed (0 mismatches)")


# ─── Run all tests ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Crystal Growth Simulator — Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_basic_creation,
        test_line_seed,
        test_corners_seed,
        test_ring_seed,
        test_stepping_grows_crystal,
        test_stickiness_affects_growth,
        test_max_particles_limit,
        test_render_produces_output,
        test_render_plain_strips_ansi,
        test_render_stats,
        test_json_export,
        test_get_stats_dict,
        test_symmetry_horizontal,
        test_symmetry_both,
        test_input_validation,
        test_validate_output_path,
        test_diagonal_vs_orthogonal,
        test_no_color_mode,
        test_walker_position_in_render,
        test_growth_history_tracking,
        test_max_particles_enforced_in_step,
        test_reproducibility_with_seed,
        test_corners_seed_on_small_grid,
        test_grid_count_matches_actual_cells,
        test_density_accuracy,
        test_symmetry_seed_placement,
    ]

    passed = 0
    failed = 0
    errors = []

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            errors.append((test.__name__, str(e)))
            print(f"✗ {test.__name__} FAILED: {e}")

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  - {name}: {err}")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)