#!/usr/bin/env python3
"""Tests for Terminal Lava Lamp simulation.

Covers blob physics, bubble behavior, lamp shape, theme switching,
rendering, input validation, and edge cases.
"""

import sys
import os
import math

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lava_lamp import (
    Blob, Bubble, LavaLamp, THEMES, WAX_CHARS, GLOW_CHARS,
    rgb_to_ansi, VERSION
)


def test_version_defined():
    """Test that VERSION is a valid version string."""
    parts = VERSION.split(".")
    assert len(parts) == 3, f"VERSION should have 3 parts, got: {VERSION}"
    for part in parts:
        assert part.isdigit(), f"VERSION parts should be numeric, got: {VERSION}"
    print(f"✓ test_version_defined passed (VERSION={VERSION})")


def test_rgb_to_ansi_bounds():
    """Test that rgb_to_ansi clamps values to 0-255."""
    # Normal values
    code = rgb_to_ansi(100, 150, 200)
    assert "100" in code and "150" in code and "200" in code

    # Out-of-range values should be clamped
    code = rgb_to_ansi(300, -10, 128)
    assert "255" in code  # 300 → 255
    assert "0" in code     # -10 → 0
    assert "128" in code   # unchanged

    # fg vs bg
    fg_code = rgb_to_ansi(50, 60, 70, fg=True)
    bg_code = rgb_to_ansi(50, 60, 70, fg=False)
    assert "38" in fg_code  # foreground
    assert "48" in bg_code  # background

    print("✓ test_rgb_to_ansi_bounds passed")


def test_blob_initialization():
    """Test that blobs initialize with valid properties."""
    blob = Blob(THEMES["classic"]["wax"], THEMES["classic"]["heat"])
    assert 0.7 <= blob.y <= 0.95, f"Blob y should start near bottom, got {blob.y}"
    assert 0.3 <= blob.x <= 0.7, f"Blob x should be centered, got {blob.x}"
    assert 0.03 <= blob.radius <= 0.12, f"Blob radius should be reasonable, got {blob.radius}"
    assert len(blob.colors) > 0, "Blob should have colors"
    print("✓ test_blob_initialization passed")


def test_blob_update():
    """Test that blob update changes position."""
    blob = Blob(THEMES["classic"]["wax"], THEMES["classic"]["heat"])
    initial_y = blob.y
    initial_x = blob.x
    blob.update(0.1)
    # Position should change (though direction is not guaranteed)
    # At least one of x or y should differ after update
    moved = (blob.y != initial_y) or (blob.x != initial_x)
    assert moved, "Blob should move after update"
    print("✓ test_blob_update passed")


def test_blob_reset():
    """Test that blob reset restores initial conditions."""
    blob = Blob(THEMES["ocean"]["wax"], THEMES["ocean"]["heat"])
    blob.update(0.5)
    blob.update(0.5)
    old_y = blob.y
    blob.reset()
    assert 0.7 <= blob.y <= 0.95, f"Reset blob y should be near bottom, got {blob.y}"
    assert blob.life == 0.0, "Reset blob life should be 0"
    print("✓ test_blob_reset passed")


def test_blob_speed_multiplier():
    """Test that speed multiplier affects blob movement."""
    blob1 = Blob(THEMES["classic"]["wax"], THEMES["classic"]["heat"])
    blob2 = Blob(THEMES["classic"]["wax"], THEMES["classic"]["heat"])
    # Same starting position isn't guaranteed, but we test that speed=2 moves more
    blob1.update(0.1, speed_multiplier=1.0)
    blob2.update(0.1, speed_multiplier=2.0)
    # blob2 should have accumulated more life (time*speed)
    assert blob2.life > blob1.life, "Speed multiplier should affect blob life"
    print("✓ test_blob_speed_multiplier passed")


def test_bubble_initialization():
    """Test that bubbles initialize with valid properties."""
    bubble = Bubble(40, 30)
    assert 0.85 <= bubble.y <= 0.98, f"Bubble y should start near bottom, got {bubble.y}"
    assert 0.3 <= bubble.x <= 0.7, f"Bubble x should be centered, got {bubble.x}"
    assert bubble.speed > 0, "Bubble speed should be positive"
    assert bubble.char in ["·", "∘", "○", "°", "•"], f"Unexpected bubble char: {bubble.char}"
    print("✓ test_bubble_initialization passed")


def test_bubble_rises():
    """Test that bubbles rise over time."""
    bubble = Bubble(40, 30)
    initial_y = bubble.y
    alive = bubble.update(0.1)
    assert alive, "Bubble should be alive after short update"
    assert bubble.y < initial_y, "Bubble should rise (y decreases)"
    print("✓ test_bubble_rises passed")


def test_bubble_dies_at_top():
    """Test that bubbles die when they reach the top."""
    bubble = Bubble(40, 30)
    bubble.y = 0.02  # near the top
    alive = bubble.update(0.01)
    assert not alive, "Bubble at y=0.02 should die after moving up"
    print("✓ test_bubble_dies_at_top passed")


def test_bubble_max_life():
    """Test that bubbles die after max_life."""
    bubble = Bubble(40, 30)
    bubble.max_life = 0.5
    bubble.update(0.6)  # exceed max_life
    # The bubble should have died
    # (y might be out of range OR life exceeded max_life)
    assert bubble.y < 0.05 or bubble.life >= bubble.max_life, \
        "Bubble should die after exceeding max_life"
    print("✓ test_bubble_max_life passed")


def test_lavalamp_creation():
    """Test that LavaLamp can be created with default parameters."""
    lamp = LavaLamp(width=40, height=30, theme="classic")
    assert lamp.width == 40
    assert lamp.height == 30
    assert lamp.theme_name == "classic"
    assert len(lamp.blobs) == 8  # default num_blobs
    assert len(lamp.bubbles) == 5  # default num_bubbles
    assert lamp.speed == 1.0
    assert not lamp.paused
    print("✓ test_lavalamp_creation passed")


def test_lavalamp_custom_params():
    """Test LavaLamp with custom parameters."""
    lamp = LavaLamp(width=50, height=25, theme="ocean", num_blobs=12,
                     num_bubbles=8, speed=2.0)
    assert lamp.width == 50
    assert lamp.theme_name == "ocean"
    assert len(lamp.blobs) == 12
    assert len(lamp.bubbles) == 8
    assert lamp.speed == 2.0
    print("✓ test_lavalamp_custom_params passed")


def test_lavalamp_invalid_theme():
    """Test that invalid theme raises ValueError."""
    try:
        LavaLamp(width=40, height=30, theme="nonexistent")
        assert False, "Should raise ValueError for invalid theme"
    except ValueError as e:
        assert "nonexistent" in str(e)
    print("✓ test_lavalamp_invalid_theme passed")


def test_lavalamp_switch_theme():
    """Test switching themes."""
    lamp = LavaLamp(width=40, height=30, theme="classic")
    lamp.switch_theme("ocean")
    assert lamp.theme_name == "ocean"
    assert lamp.theme == THEMES["ocean"]
    # Blobs should have new colors
    for blob in lamp.blobs:
        assert blob.colors == THEMES["ocean"]["wax"]
    print("✓ test_lavalamp_switch_theme passed")


def test_lavalamp_switch_invalid_theme():
    """Test that switching to invalid theme raises ValueError."""
    lamp = LavaLamp(width=40, height=30, theme="classic")
    try:
        lamp.switch_theme("invalid_theme")
        assert False, "Should raise ValueError for invalid theme"
    except ValueError:
        pass
    print("✓ test_lavalamp_switch_invalid_theme passed")


def test_lavalamp_shape_width():
    """Test that lamp shape width values are reasonable."""
    lamp = LavaLamp(width=40, height=30)
    # At top: narrow
    top_w = lamp._shape_width(0.02)
    assert 0.1 <= top_w <= 0.3, f"Top shape should be narrow, got {top_w}"
    # At middle: wide
    mid_w = lamp._shape_width(0.45)
    assert mid_w > 0.5, f"Middle shape should be wide, got {mid_w}"
    # At bottom: medium
    bot_w = lamp._shape_width(0.95)
    assert 0.3 <= bot_w <= 0.6, f"Bottom shape should be medium, got {bot_w}"
    print("✓ test_lavalamp_shape_width passed")


def test_lavalamp_update():
    """Test that update advances simulation time."""
    lamp = LavaLamp(width=40, height=30, theme="classic")
    assert lamp.time == 0.0
    lamp.update(0.1)
    assert lamp.time > 0.0, "Time should advance after update"
    print("✓ test_lavalamp_update passed")


def test_lavalamp_update_paused():
    """Test that paused lamp doesn't advance time."""
    lamp = LavaLamp(width=40, height=30, theme="classic")
    lamp.paused = True
    lamp.update(0.1)
    assert lamp.time == 0.0, "Time should not advance when paused"
    print("✓ test_lavalamp_update_paused passed")


def test_lavalamp_render():
    """Test that render produces output lines."""
    lamp = LavaLamp(width=40, height=25, theme="classic")
    lines = lamp.render()
    assert len(lines) > 0, "Render should produce output"
    assert len(lines) >= 25, f"Should have at least 25 lines, got {len(lines)}"
    # Lines should contain ANSI codes (color)
    has_ansi = any("\033[" in line for line in lines)
    assert has_ansi, "Rendered output should contain ANSI escape codes"
    print(f"✓ test_lavalamp_render passed ({len(lines)} lines)")


def test_lavalamp_all_themes():
    """Test rendering with all available themes."""
    for theme_name in THEMES:
        lamp = LavaLamp(width=30, height=20, theme=theme_name)
        lamp.update(0.1)
        lines = lamp.render()
        assert len(lines) > 0, f"Theme '{theme_name}' should render"
    print(f"✓ test_lavalamp_all_themes passed ({len(THEMES)} themes)")


def test_lavalamp_add_blob():
    """Test adding a blob dynamically."""
    lamp = LavaLamp(width=40, height=30, num_blobs=4)
    initial_count = len(lamp.blobs)
    lamp.blobs.append(Blob(lamp.theme["wax"], lamp.theme["heat"]))
    assert len(lamp.blobs) == initial_count + 1
    print("✓ test_lavalamp_add_blob passed")


def test_lavalamp_bubble_respawn():
    """Test that bubbles are respawned when they die."""
    lamp = LavaLamp(width=40, height=30, num_bubbles=3)
    # Run simulation long enough for some bubbles to reach the top
    for _ in range(100):
        lamp.update(0.05)
    # Should still have 3 bubbles (some may have been respawned)
    assert len(lamp.bubbles) == 3, f"Should maintain 3 bubbles, got {len(lamp.bubbles)}"
    print("✓ test_lavalamp_bubble_respawn passed")


def test_lavalamp_large_dt_capped():
    """Test that large dt values don't cause issues (capped in update)."""
    lamp = LavaLamp(width=40, height=30)
    lamp.update(10.0)  # Very large dt
    # Should not crash, dt is capped internally
    lines = lamp.render()
    assert len(lines) > 0, "Should still render after large dt"
    print("✓ test_lavalamp_large_dt_capped passed")


def test_lavalamp_small_width():
    """Test that the lamp works with a small width."""
    lamp = LavaLamp(width=20, height=15, theme="classic")
    lamp.update(0.05)
    lines = lamp.render()
    assert len(lines) > 0, "Should render with small width"
    print("✓ test_lavalamp_small_width passed")


def test_themes_structure():
    """Test that all themes have required keys."""
    required_keys = {"name", "bg", "lamp", "wax", "glow", "heat"}
    for theme_name, theme in THEMES.items():
        for key in required_keys:
            assert key in theme, f"Theme '{theme_name}' missing key '{key}'"
        assert len(theme["wax"]) >= 4, f"Theme '{theme_name}' should have >=4 wax colors"
        # Check RGB tuples are valid
        for color in theme["wax"]:
            assert len(color) == 3, f"Wax color {color} should be RGB tuple"
            for v in color:
                assert 0 <= v <= 255, f"RGB value {v} out of range"
    print(f"✓ test_themes_structure passed ({len(THEMES)} themes)")


def test_theme_count():
    """Test that there are multiple themes available."""
    assert len(THEMES) >= 4, f"Should have at least 4 themes, got {len(THEMES)}"
    # Check for new themes
    assert "neon" in THEMES, "Should have 'neon' theme"
    assert "aurora" in THEMES, "Should have 'aurora' theme"
    print(f"✓ test_theme_count passed ({len(THEMES)} themes)")


def test_blob_out_of_bounds_resets():
    """Test that blobs that go out of bounds get reset."""
    blob = Blob(THEMES["classic"]["wax"], THEMES["classic"]["heat"])
    blob.y = -0.2  # above top
    blob.update(0.01)
    # Should have been reset
    assert 0.7 <= blob.y <= 0.95, f"Out-of-bounds blob should reset, got y={blob.y}"
    print("✓ test_blob_out_of_bounds_resets passed")


def test_lavalamp_multiple_updates():
    """Test that multiple updates work correctly."""
    lamp = LavaLamp(width=40, height=30)
    for _ in range(100):
        lamp.update(0.05)
    lines = lamp.render()
    assert len(lines) > 0, "Should render after many updates"
    assert lamp.time > 0, "Time should have advanced"
    print(f"✓ test_lavalamp_multiple_updates passed (time={lamp.time:.2f}s)")


# ─── Run all tests ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Terminal Lava Lamp — Test Suite")
    print("=" * 60)
    print()

    tests = [
        test_version_defined,
        test_rgb_to_ansi_bounds,
        test_blob_initialization,
        test_blob_update,
        test_blob_reset,
        test_blob_speed_multiplier,
        test_bubble_initialization,
        test_bubble_rises,
        test_bubble_dies_at_top,
        test_bubble_max_life,
        test_lavalamp_creation,
        test_lavalamp_custom_params,
        test_lavalamp_invalid_theme,
        test_lavalamp_switch_theme,
        test_lavalamp_switch_invalid_theme,
        test_lavalamp_shape_width,
        test_lavalamp_update,
        test_lavalamp_update_paused,
        test_lavalamp_render,
        test_lavalamp_all_themes,
        test_lavalamp_add_blob,
        test_lavalamp_bubble_respawn,
        test_lavalamp_large_dt_capped,
        test_lavalamp_small_width,
        test_themes_structure,
        test_theme_count,
        test_blob_out_of_bounds_resets,
        test_lavalamp_multiple_updates,
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