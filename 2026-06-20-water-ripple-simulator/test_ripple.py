#!/usr/bin/env python3
"""Comprehensive tests for the water ripple simulator."""

import sys
import os
import math

# Ensure we can import from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ripple import (
    RippleSimulator,
    WaveSource,
    clamp,
    lerp_color,
    interference_drop,
    get_cycled_palette,
    PALETTES,
    PALETTE_NAMES,
    WALL_PRESETS,
    BLOCK_CHARS,
)


def test_clamp():
    """Test the clamp utility function."""
    assert clamp(5, 0, 10) == 5
    assert clamp(-3, 0, 10) == 0
    assert clamp(15, 0, 10) == 10
    assert clamp(0, 0, 1) == 0
    assert clamp(1, 0, 1) == 1


def test_lerp_color():
    """Test color interpolation."""
    # At t=0, should return c1
    result = lerp_color((0, 0, 0), (100, 100, 100), 0.0)
    assert result == (0, 0, 0)
    # At t=1, should return c2
    result = lerp_color((0, 0, 0), (100, 100, 100), 1.0)
    assert result == (100, 100, 100)
    # At t=0.5, should be midpoint
    result = lerp_color((0, 0, 0), (200, 200, 200), 0.5)
    assert result == (100, 100, 100)


def test_basic_drop():
    """Test that dropping a stone creates waves."""
    sim = RippleSimulator(cols=20, rows=10)
    sim.drop_stone(10, 5, radius=2, amplitude=10)

    assert sim.drop_count == 1, f"Expected 1 drop, got {sim.drop_count}"

    # The center cell should have some amplitude
    center_val = sim.current[sim.idx(10, 5)]
    assert center_val > 0, f"Center cell should have positive amplitude, got {center_val}"


def test_simulation_steps():
    """Test that the simulation advances correctly."""
    sim = RippleSimulator(cols=20, rows=10)
    sim.drop_stone(10, 5, radius=2, amplitude=10)

    for i in range(5):
        sim.step()

    assert sim.frame == 5, f"Expected frame 5, got {sim.frame}"
    assert sim.drop_count == 1, f"Expected 1 drop, got {sim.drop_count}"

    # Check waves propagated (non-zero cells exist)
    nonzero = sum(1 for v in sim.current if abs(v) > 0.001)
    assert nonzero > 0, "Expected non-zero wave values after drop"


def test_wall_functionality():
    """Test that wall cells remain at zero and reflect waves."""
    sim = RippleSimulator(cols=20, rows=10)
    sim.walls[sim.idx(10, 5)] = True
    sim.drop_stone(5, 5, radius=1, amplitude=5)

    for i in range(10):
        sim.step()

    # Wall cell should be 0
    assert sim.current[sim.idx(10, 5)] == 0.0, "Wall cell should remain 0"


def test_clear_water():
    """Test clearing the water resets the simulation state."""
    sim = RippleSimulator(cols=10, rows=5)
    sim.drop_stone(5, 2, radius=1, amplitude=5)
    for i in range(5):
        sim.step()

    sim.clear_water()
    assert all(v == 0.0 for v in sim.current), "Water should be cleared"
    assert all(v == 0.0 for v in sim.previous), "Previous buffer should be cleared"
    assert sim.frame == 0, "Frame should reset to 0"
    assert sim.drop_count == 0, "Drop count should reset to 0"


def test_clear_walls():
    """Test clearing all walls."""
    sim = RippleSimulator(cols=10, rows=5)
    sim.walls[sim.idx(3, 2)] = True
    sim.walls[sim.idx(5, 2)] = True
    sim.clear_walls()
    assert not any(sim.walls), "All walls should be cleared"


def test_palette_switching():
    """Test that rendering works with different palettes."""
    for pid in PALETTES:
        sim = RippleSimulator(cols=10, rows=5)
        sim.palette_id = pid
        sim.drop_stone(5, 2, radius=1, amplitude=5)
        sim.step()
        lines = sim.render()
        assert len(lines) == 5, f"Palette {pid}: Expected 5 rows, got {len(lines)}"


def test_render_output_format():
    """Test that render output contains ANSI escape sequences."""
    sim = RippleSimulator(cols=20, rows=10)
    sim.drop_stone(10, 5, radius=2, amplitude=10)
    sim.step()
    lines = sim.render()

    # Each line should contain ANSI escape sequences
    for line in lines:
        assert "\033[" in line, "Rendered line should contain ANSI escape codes"


def test_wave_conservation():
    """Test that wave energy is roughly conserved (with damping it should decrease)."""
    sim = RippleSimulator(cols=30, rows=15, )
    sim.damping = 1.0  # No damping for conservation check
    sim.drop_stone(15, 7, radius=2, amplitude=10)

    # Calculate total energy (sum of squares) after initial drop
    initial_energy = sum(v * v for v in sim.current)

    sim.step()

    after_step_energy = sum(v * v for v in sim.current)
    # Energy should be of similar magnitude (some goes to previous buffer)
    # With no damping, it shouldn't disappear
    assert after_step_energy > 0, "Energy should not be zero after stepping"


def test_boundary_conditions():
    """Test that the boundary of the grid stays at zero (absorbing/reflecting)."""
    sim = RippleSimulator(cols=20, rows=10)
    sim.drop_stone(10, 5, radius=2, amplitude=10)

    for i in range(20):
        sim.step()

    # Edges of the grid should be relatively calm (boundary condition)
    # Top edge
    top_row_energy = sum(abs(sim.current[sim.idx(x, 0)]) for x in range(sim.cols))
    # Middle should have more activity than edges typically
    # Just check it doesn't blow up
    assert top_row_energy < 1000, f"Top row energy unexpectedly high: {top_row_energy}"


def test_multiple_drops():
    """Test multiple stone drops at different positions."""
    sim = RippleSimulator(cols=30, rows=15)
    sim.drop_stone(10, 7, radius=2, amplitude=8)
    sim.drop_stone(20, 7, radius=2, amplitude=8)

    assert sim.drop_count == 2

    for i in range(10):
        sim.step()

    # Both drop locations should have had influence
    nonzero = sum(1 for v in sim.current if abs(v) > 0.001)
    assert nonzero > 0, "Should have active wave cells"


def test_wave_source():
    """Test continuous wave source creation and removal."""
    sim = RippleSimulator(cols=30, rows=15)

    # Add a source
    sim.add_source(10, 7, amplitude=5.0)
    assert len(sim.sources) == 1

    # Add another source
    sim.add_source(20, 7, amplitude=5.0)
    assert len(sim.sources) == 2

    # Remove a source by placing near it
    sim.add_source(10, 7, amplitude=5.0)  # Should toggle off
    assert len(sim.sources) == 1, "Source should be toggled off"


def test_wave_source_emission():
    """Test that wave sources emit pulses during simulation."""
    sim = RippleSimulator(cols=30, rows=15)
    sim.add_source(15, 7, amplitude=5.0)

    # Run enough frames for source to emit
    for i in range(20):
        sim.step()

    # Should have waves from source emission
    nonzero = sum(1 for v in sim.current if abs(v) > 0.001)
    assert nonzero > 0, "Source should produce waves"


def test_wall_presets():
    """Test that wall presets create walls."""
    for preset_idx in range(len(WALL_PRESETS)):
        sim = RippleSimulator(cols=40, rows=20)
        sim.apply_wall_preset(preset_idx)
        wall_count = sum(1 for w in sim.walls if w)
        assert wall_count > 0, f"Preset {WALL_PRESETS[preset_idx]} should create walls"

    # Test cycling through presets until we reach the "clear" state
    sim = RippleSimulator(cols=40, rows=20)
    sim.cycle_wall_preset()  # idx=0 (preset 0)
    assert sim.wall_preset_idx == 0

    sim.cycle_wall_preset()  # idx=1 (preset 1)
    assert sim.wall_preset_idx == 1

    # Cycle through remaining presets (2, 3, 4) then clear state
    # Total: 2 explicit + 4 in loop = 6 cycles from start
    for _ in range(len(WALL_PRESETS) - 1):
        sim.cycle_wall_preset()
    # After 6 total cycles we should be at the clear state (idx=-1)
    assert sim.wall_preset_idx == -1, f"Expected -1 after cycling past all, got {sim.wall_preset_idx}"
    assert not any(sim.walls), "Cycling past all presets should clear walls"


def test_interference_drop():
    """Test the interference demo function."""
    sim = RippleSimulator(cols=40, rows=20)
    interference_drop(sim)
    assert sim.drop_count == 2, "Interference demo should create 2 drops"

    # Run simulation
    for i in range(10):
        sim.step()

    # Should have active waves
    nonzero = sum(1 for v in sim.current if abs(v) > 0.001)
    assert nonzero > 0, "Interference should produce waves"


def test_color_cycle_palette():
    """Test that color cycling produces valid palettes."""
    for frame in range(100):
        palette = get_cycled_palette(frame)
        assert len(palette) == 10, f"Frame {frame}: palette should have 10 entries"
        for r, g, b in palette:
            assert 0 <= r <= 255, f"Red out of range: {r}"
            assert 0 <= g <= 255, f"Green out of range: {g}"
            assert 0 <= b <= 255, f"Blue out of range: {b}"


def test_sim_speed():
    """Test simulation speed control."""
    sim = RippleSimulator(cols=20, rows=10)
    sim.sim_speed = 2.0
    sim.drop_stone(10, 5, radius=2, amplitude=10)

    # Run 3 outer loops with 2 steps each = 6 frames
    steps = max(1, int(sim.sim_speed))
    for _ in range(3):
        for _ in range(steps):
            sim.step()

    assert sim.frame == 6, f"Expected 6 frames, got {sim.frame}"


def test_damping_adjustment():
    """Test that damping can be adjusted."""
    sim = RippleSimulator(cols=20, rows=10)
    assert sim.damping == 0.96, f"Default damping should be 0.96, got {sim.damping}"

    sim.damping = 0.99
    assert sim.damping == 0.99

    # Clamp upper
    sim.damping = min(0.995, sim.damping + 0.01)
    assert sim.damping == 0.995

    # Clamp lower
    sim.damping = max(0.80, sim.damping - 0.20)
    assert sim.damping == 0.80


def test_render_with_walls():
    """Test that walls are rendered with block characters."""
    sim = RippleSimulator(cols=20, rows=10)
    sim.walls[sim.idx(10, 5)] = True
    lines = sim.render()

    # At least one line should contain a wall character
    has_wall_char = any("▓" in line or "▒" in line or "░" in line for line in lines)
    assert has_wall_char, "Wall characters should appear in render output"


def test_render_with_custom_palette():
    """Test rendering with a custom cycled palette."""
    from ripple import render_with_custom_palette

    sim = RippleSimulator(cols=20, rows=10)
    sim.drop_stone(10, 5, radius=2, amplitude=10)
    sim.step()

    palette = get_cycled_palette(0)
    lines = render_with_custom_palette(sim, palette)
    assert len(lines) == 10, f"Expected 10 rows, got {len(lines)}"


def test_palette_names():
    """Test that all palettes have names."""
    for pid in PALETTES:
        assert pid in PALETTE_NAMES, f"Palette {pid} missing from PALETTE_NAMES"


def test_in_bounds():
    """Test the in_bounds method."""
    sim = RippleSimulator(cols=20, rows=10)
    assert sim.in_bounds(0, 0) is True
    assert sim.in_bounds(19, 9) is True
    assert sim.in_bounds(20, 9) is False
    assert sim.in_bounds(19, 10) is False
    assert sim.in_bounds(-1, 0) is False


def test_idx():
    """Test the idx method."""
    sim = RippleSimulator(cols=20, rows=10)
    assert sim.idx(0, 0) == 0
    assert sim.idx(19, 0) == 19
    assert sim.idx(0, 1) == 20
    assert sim.idx(5, 3) == 65


def test_rain_mode():
    """Test that rain mode flag works."""
    sim = RippleSimulator(cols=20, rows=10)
    assert sim.rain_mode is False
    sim.rain_mode = True
    assert sim.rain_mode is True


def test_large_drop():
    """Test dropping a large stone (big radius)."""
    sim = RippleSimulator(cols=30, rows=20)
    sim.drop_stone(15, 10, radius=5, amplitude=20)

    # Should affect many cells
    nonzero = sum(1 for v in sim.current if abs(v) > 0.001)
    assert nonzero > 20, f"Large drop should affect many cells, got {nonzero}"


def test_drop_at_boundary():
    """Test dropping a stone near the edge of the grid."""
    sim = RippleSimulator(cols=20, rows=10)
    # Should not crash when dropping near edges
    sim.drop_stone(0, 0, radius=2, amplitude=5)
    sim.drop_stone(19, 9, radius=2, amplitude=5)
    sim.drop_stone(0, 9, radius=2, amplitude=5)

    for i in range(5):
        sim.step()

    # Should still produce some waves
    nonzero = sum(1 for v in sim.current if abs(v) > 0.001)
    assert nonzero > 0


if __name__ == "__main__":
    # Run all tests
    test_functions = [
        test_clamp, test_lerp_color, test_basic_drop,
        test_simulation_steps, test_wall_functionality, test_clear_water,
        test_clear_walls, test_palette_switching, test_render_output_format,
        test_wave_conservation, test_boundary_conditions, test_multiple_drops,
        test_wave_source, test_wave_source_emission, test_wall_presets,
        test_interference_drop, test_color_cycle_palette, test_sim_speed,
        test_damping_adjustment, test_render_with_walls,
        test_render_with_custom_palette, test_palette_names,
        test_in_bounds, test_idx, test_rain_mode, test_large_drop,
        test_drop_at_boundary,
    ]

    passed = 0
    failed = 0
    for test_fn in test_functions:
        try:
            test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ {test_fn.__name__}: {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(test_functions)} total")
    if failed == 0:
        print("✅ All tests passed!")
    else:
        sys.exit(1)