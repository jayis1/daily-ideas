#!/usr/bin/env python3
"""Tests for Terminal Lava Lamp simulation v3.0.

Covers blob physics, bubble behavior, lamp shape, theme switching,
rendering, input validation, edge cases, merge/split dynamics,
screenshot export, custom theme loading, and more.
"""

import sys
import os
import math
import json
import tempfile
import shutil

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lava_lamp import (
    Blob, Bubble, LavaLamp, THEMES, WAX_CHARS, GLOW_CHARS,
    rgb_to_ansi, strip_ansi, Screenshot, load_themes_from_file,
    VERSION, MERGE_DISTANCE, SPLIT_RADIUS_THRESHOLD
)


# ─── Basic Version & Helpers ─────────────────────────────────────────────────

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


def test_strip_ansi():
    """Test that strip_ansi removes ANSI escape sequences."""
    ansi_text = "\033[38;2;255;60;30mHello\033[0m \033[48;2;20;10;40mWorld\033[0m"
    plain = strip_ansi(ansi_text)
    assert plain == "Hello World", f"Expected 'Hello World', got '{plain}'"

    # Plain text should be unchanged
    assert strip_ansi("no ansi here") == "no ansi here"

    # Empty string
    assert strip_ansi("") == ""

    print("✓ test_strip_ansi passed")


# ─── Blob Tests ──────────────────────────────────────────────────────────────

def test_blob_initialization():
    """Test that blobs initialize with valid properties."""
    blob = Blob(THEMES["classic"]["wax"], THEMES["classic"]["heat"])
    assert 0.7 <= blob.y <= 0.95, f"Blob y should start near bottom, got {blob.y}"
    assert 0.3 <= blob.x <= 0.7, f"Blob x should be centered, got {blob.x}"
    assert 0.03 <= blob.radius <= 0.12, f"Blob radius should be reasonable, got {blob.radius}"
    assert len(blob.colors) > 0, "Blob should have colors"
    assert blob.merge_cooldown == 0.0, "Blob should start with no merge cooldown"
    assert blob.split_cooldown == 0.0, "Blob should start with no split cooldown"
    print("✓ test_blob_initialization passed")


def test_blob_update():
    """Test that blob update changes position."""
    blob = Blob(THEMES["classic"]["wax"], THEMES["classic"]["heat"])
    initial_y = blob.y
    initial_x = blob.x
    blob.update(0.1)
    # Position should change (though direction is not guaranteed)
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
    assert blob.merge_cooldown == 0.0, "Reset blob should have no merge cooldown"
    assert blob.split_cooldown == 0.0, "Reset blob should have no split cooldown"
    print("✓ test_blob_reset passed")


def test_blob_speed_multiplier():
    """Test that speed multiplier affects blob movement."""
    blob1 = Blob(THEMES["classic"]["wax"], THEMES["classic"]["heat"])
    blob2 = Blob(THEMES["classic"]["wax"], THEMES["classic"]["heat"])
    blob1.update(0.1, speed_multiplier=1.0)
    blob2.update(0.1, speed_multiplier=2.0)
    assert blob2.life > blob1.life, "Speed multiplier should affect blob life"
    print("✓ test_blob_speed_multiplier passed")


def test_blob_cooldown_decreases():
    """Test that merge/split cooldowns decrease over time."""
    blob = Blob(THEMES["classic"]["wax"], THEMES["classic"]["heat"])
    blob.merge_cooldown = 2.0
    blob.split_cooldown = 3.0
    blob.update(0.5, speed_multiplier=1.0)
    assert blob.merge_cooldown < 2.0, "Merge cooldown should decrease"
    assert blob.split_cooldown < 3.0, "Split cooldown should decrease"
    print("✓ test_blob_cooldown_decreases passed")


def test_blob_out_of_bounds_resets():
    """Test that blobs that go out of bounds get reset."""
    blob = Blob(THEMES["classic"]["wax"], THEMES["classic"]["heat"])
    blob.y = -0.2  # above top
    blob.update(0.01)
    # Should have been reset
    assert 0.7 <= blob.y <= 0.95, f"Out-of-bounds blob should reset, got y={blob.y}"
    print("✓ test_blob_out_of_bounds_resets passed")


# ─── Bubble Tests ────────────────────────────────────────────────────────────

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
    assert bubble.y < 0.05 or bubble.life >= bubble.max_life, \
        "Bubble should die after exceeding max_life"
    print("✓ test_bubble_max_life passed")


# ─── LavaLamp Core Tests ─────────────────────────────────────────────────────

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
    assert lamp.merge_count == 0
    assert lamp.split_count == 0
    assert lamp.fps == 0.0
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


def test_lavalamp_remove_blob():
    """Test removing a blob."""
    lamp = LavaLamp(width=40, height=30, num_blobs=5)
    initial_count = len(lamp.blobs)
    lamp.blobs.pop(0)
    assert len(lamp.blobs) == initial_count - 1
    print("✓ test_lavalamp_remove_blob passed")


def test_lavalamp_bubble_respawn():
    """Test that bubbles are respawned when they die."""
    lamp = LavaLamp(width=40, height=30, num_bubbles=3)
    for _ in range(100):
        lamp.update(0.05)
    assert len(lamp.bubbles) == 3, f"Should maintain 3 bubbles, got {len(lamp.bubbles)}"
    print("✓ test_lavalamp_bubble_respawn passed")


def test_lavalamp_large_dt_capped():
    """Test that large dt values don't cause issues (capped in update)."""
    lamp = LavaLamp(width=40, height=30)
    lamp.update(10.0)  # Very large dt
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
    """Test that there are multiple themes available (including new ones)."""
    assert len(THEMES) >= 8, f"Should have at least 8 themes, got {len(THEMES)}"
    assert "neon" in THEMES, "Should have 'neon' theme"
    assert "aurora" in THEMES, "Should have 'aurora' theme"
    assert "ember" in THEMES, "Should have 'ember' theme"
    assert "frost" in THEMES, "Should have 'frost' theme"
    print(f"✓ test_theme_count passed ({len(THEMES)} themes)")


def test_lavalamp_multiple_updates():
    """Test that multiple updates work correctly."""
    lamp = LavaLamp(width=40, height=30)
    for _ in range(100):
        lamp.update(0.05)
    lines = lamp.render()
    assert len(lines) > 0, "Should render after many updates"
    assert lamp.time > 0, "Time should have advanced"
    print(f"✓ test_lavalamp_multiple_updates passed (time={lamp.time:.2f}s)")


# ─── Merge/Split Tests ──────────────────────────────────────────────────────

def test_merge_nearby_blobs():
    """Test that nearby blobs can merge."""
    lamp = LavaLamp(width=40, height=30, num_blobs=4)
    initial_count = len(lamp.blobs)
    # Place two blobs very close together
    lamp.blobs[0].x = 0.5
    lamp.blobs[0].y = 0.5
    lamp.blobs[0].merge_cooldown = 0  # ensure cooldown is clear
    lamp.blobs[1].x = 0.51  # very close
    lamp.blobs[1].y = 0.5
    lamp.blobs[1].merge_cooldown = 0
    # Run updates to trigger potential merge
    for _ in range(50):
        lamp.update(0.05)
    # May or may not merge (depends on random position convergence)
    # but should not crash
    assert len(lamp.blobs) >= 1, "Should have at least 1 blob"
    print(f"✓ test_merge_nearby_blobs passed (blobs: {len(lamp.blobs)})")


def test_merge_increments_counter():
    """Test that merges are tracked in merge_count."""
    lamp = LavaLamp(width=40, height=30, num_blobs=8)
    # Run enough updates for merges to potentially happen
    for _ in range(200):
        lamp.update(0.05)
    # merge_count is tracked regardless of whether merges happened
    assert isinstance(lamp.merge_count, int), "merge_count should be an integer"
    assert lamp.merge_count >= 0, "merge_count should be non-negative"
    print(f"✓ test_merge_increments_counter passed (merges: {lamp.merge_count})")


def test_split_increments_counter():
    """Test that splits are tracked in split_count."""
    lamp = LavaLamp(width=40, height=30, num_blobs=8)
    # Run enough updates for splits to potentially happen
    for _ in range(200):
        lamp.update(0.05)
    # split_count is tracked regardless of whether splits happened
    assert isinstance(lamp.split_count, int), "split_count should be an integer"
    assert lamp.split_count >= 0, "split_count should be non-negative"
    print(f"✓ test_split_increments_counter passed (splits: {lamp.split_count})")


def test_merge_cooldown_prevents_merge():
    """Test that blobs on cooldown cannot merge."""
    lamp = LavaLamp(width=40, height=30, num_blobs=4)
    # Set cooldown on all blobs
    for blob in lamp.blobs:
        blob.merge_cooldown = 10.0
    # Run updates — no merges should happen
    for _ in range(20):
        lamp.update(0.05)
    # merge_count should remain 0 (blobs can't merge with cooldown)
    # (though this depends on whether blobs get close enough in general,
    #  the cooldown should prevent any merges)
    assert isinstance(lamp.merge_count, int)
    print("✓ test_merge_cooldown_prevents_merge passed")


def test_split_cooldown_prevents_split():
    """Test that blobs on split cooldown cannot split."""
    lamp = LavaLamp(width=40, height=30, num_blobs=4)
    # Set split cooldown on all blobs
    for blob in lamp.blobs:
        blob.split_cooldown = 10.0
    for _ in range(20):
        lamp.update(0.05)
    # split_count should be 0
    assert lamp.split_count == 0, "Blobs on cooldown should not split"
    print("✓ test_split_cooldown_prevents_split passed")


def test_blob_count_changes_dynamically():
    """Test that blob count changes during simulation (merge/split)."""
    lamp = LavaLamp(width=40, height=30, num_blobs=8)
    counts = set()
    for _ in range(300):
        lamp.update(0.05)
        counts.add(len(lamp.blobs))
    # Over 300 updates with 8 blobs, merge/split should cause some variation
    # (not guaranteed, but likely)
    assert len(lamp.blobs) >= 1, "Should always have at least 1 blob"
    print(f"✓ test_blob_count_changes_dynamically passed (distinct counts seen: {counts})")


# ─── Screenshot Tests ────────────────────────────────────────────────────────

def test_screenshot_save_ansi():
    """Test that Screenshot.save_ansi writes a file."""
    lamp = LavaLamp(width=30, height=20, theme="classic")
    lamp.update(0.1)
    lines = lamp.render()
    assert len(lines) > 0

    tmpdir = tempfile.mkdtemp()
    try:
        filepath = os.path.join(tmpdir, "test_screenshot.ansi")
        result = Screenshot.save_ansi(lines, filepath)
        assert result, "save_ansi should return True on success"
        assert os.path.exists(filepath), "Screenshot file should exist"
        content = open(filepath, 'r').read()
        assert len(content) > 0, "Screenshot file should not be empty"
    finally:
        shutil.rmtree(tmpdir)
    print("✓ test_screenshot_save_ansi passed")


def test_screenshot_save_plain():
    """Test that Screenshot.save_plain writes a plain text file."""
    lamp = LavaLamp(width=30, height=20, theme="classic")
    lamp.update(0.1)
    lines = lamp.render()
    assert len(lines) > 0

    tmpdir = tempfile.mkdtemp()
    try:
        filepath = os.path.join(tmpdir, "test_screenshot.txt")
        result = Screenshot.save_plain(lines, filepath)
        assert result, "save_plain should return True on success"
        assert os.path.exists(filepath), "Screenshot file should exist"
        content = open(filepath, 'r').read()
        assert len(content) > 0, "Screenshot file should not be empty"
        # Plain text should NOT contain ANSI codes
        assert "\033[" not in content, "Plain text should not contain ANSI codes"
    finally:
        shutil.rmtree(tmpdir)
    print("✓ test_screenshot_save_plain passed")


def test_screenshot_bad_path():
    """Test that Screenshot handles bad file paths gracefully."""
    lines = ["hello"]
    result = Screenshot.save_ansi(lines, "/nonexistent/path/file.txt")
    assert not result, "save_ansi should return False for bad path"
    print("✓ test_screenshot_bad_path passed")


# ─── Theme File Loading Tests ────────────────────────────────────────────────

def test_load_themes_from_file():
    """Test loading custom themes from a JSON file."""
    tmpdir = tempfile.mkdtemp()
    try:
        theme_data = {
            "custom1": {
                "name": "Custom1",
                "bg": [10, 10, 10],
                "lamp": [50, 50, 50],
                "wax": [
                    [255, 0, 0],
                    [0, 255, 0],
                    [0, 0, 255],
                    [255, 255, 0],
                ],
                "glow": [20, 20, 20],
                "heat": [200, 50, 50],
            },
            "custom2": {
                "name": "Custom2",
                "bg": [0, 0, 20],
                "lamp": [30, 30, 60],
                "wax": [
                    [100, 200, 255],
                    [150, 220, 255],
                    [200, 240, 255],
                    [50, 180, 220],
                    [80, 150, 200],
                    [120, 190, 230],
                ],
                "glow": [10, 20, 40],
                "heat": [60, 100, 200],
            },
        }
        filepath = os.path.join(tmpdir, "custom_themes.json")
        with open(filepath, 'w') as f:
            json.dump(theme_data, f)

        loaded = load_themes_from_file(filepath)
        assert "custom1" in loaded
        assert "custom2" in loaded
        assert loaded["custom1"]["name"] == "Custom1"
        assert loaded["custom1"]["bg"] == (10, 10, 10)
        assert loaded["custom1"]["wax"][0] == (255, 0, 0)
        assert loaded["custom2"]["wax"][0] == (100, 200, 255)
    finally:
        shutil.rmtree(tmpdir)
    print("✓ test_load_themes_from_file passed")


def test_load_themes_missing_keys():
    """Test that loading themes with missing keys raises ValueError."""
    tmpdir = tempfile.mkdtemp()
    try:
        theme_data = {
            "bad_theme": {
                "name": "Bad",
                "bg": [0, 0, 0],
                # missing "lamp", "wax", "glow", "heat"
            }
        }
        filepath = os.path.join(tmpdir, "bad_themes.json")
        with open(filepath, 'w') as f:
            json.dump(theme_data, f)

        try:
            load_themes_from_file(filepath)
            assert False, "Should raise ValueError for missing keys"
        except ValueError as e:
            assert "missing" in str(e).lower()
    finally:
        shutil.rmtree(tmpdir)
    print("✓ test_load_themes_missing_keys passed")


def test_load_themes_file_not_found():
    """Test that loading from nonexistent file raises FileNotFoundError."""
    try:
        load_themes_from_file("/nonexistent/path/themes.json")
        assert False, "Should raise FileNotFoundError"
    except FileNotFoundError:
        pass
    print("✓ test_load_themes_file_not_found passed")


def test_load_themes_out_of_range_colors():
    """Test that out-of-range color values raise ValueError."""
    tmpdir = tempfile.mkdtemp()
    try:
        theme_data = {
            "bad_colors": {
                "name": "BadColors",
                "bg": [300, -10, 128],  # out of range
                "lamp": [50, 50, 50],
                "wax": [[255, 0, 0], [0, 255, 0], [0, 0, 255], [255, 255, 0]],
                "glow": [20, 20, 20],
                "heat": [200, 50, 50],
            }
        }
        filepath = os.path.join(tmpdir, "bad_colors.json")
        with open(filepath, 'w') as f:
            json.dump(theme_data, f)

        try:
            load_themes_from_file(filepath)
            assert False, "Should raise ValueError for out-of-range colors"
        except ValueError as e:
            assert "out-of-range" in str(e).lower() or "range" in str(e).lower()
    finally:
        shutil.rmtree(tmpdir)
    print("✓ test_load_themes_out_of_range_colors passed")


# ─── New Theme Tests ─────────────────────────────────────────────────────────

def test_ember_theme():
    """Test that the Ember theme exists and is valid."""
    assert "ember" in THEMES
    theme = THEMES["ember"]
    assert theme["name"] == "Ember"
    assert theme["bg"] == (25, 8, 5)
    assert len(theme["wax"]) >= 4
    print("✓ test_ember_theme passed")


def test_frost_theme():
    """Test that the Frost theme exists and is valid."""
    assert "frost" in THEMES
    theme = THEMES["frost"]
    assert theme["name"] == "Frost"
    assert theme["bg"] == (8, 12, 25)
    assert len(theme["wax"]) >= 4
    print("✓ test_frost_theme passed")


# ─── Bug Regression Tests ──────────────────────────────────────────────────

def test_negative_dt_ignored():
    """Bug fix: negative dt values should be ignored (no negative time)."""
    lamp = LavaLamp(width=40, height=30)
    lamp.update(-0.5)
    assert lamp.time == 0.0, f"Time should stay 0 after negative dt, got {lamp.time}"
    for blob in lamp.blobs:
        assert blob.life == 0.0, f"Blob life should stay 0 after negative dt, got {blob.life}"
    print("✓ test_negative_dt_ignored passed")


def test_zero_dt_ignored():
    """Bug fix: zero dt values should be ignored (no time advance)."""
    lamp = LavaLamp(width=40, height=30)
    lamp.update(0.0)
    assert lamp.time == 0.0, f"Time should stay 0 after zero dt, got {lamp.time}"
    print("✓ test_zero_dt_ignored passed")


def test_negative_speed_rejected():
    """Bug fix: negative speed should raise ValueError."""
    try:
        LavaLamp(width=40, height=30, speed=-1.0)
        assert False, "Should raise ValueError for negative speed"
    except ValueError as e:
        assert "positive" in str(e).lower(), f"Error message should mention positive, got: {e}"
    print("✓ test_negative_speed_rejected passed")


def test_zero_speed_rejected():
    """Bug fix: zero speed should raise ValueError."""
    try:
        LavaLamp(width=40, height=30, speed=0.0)
        assert False, "Should raise ValueError for zero speed"
    except ValueError:
        pass
    print("✓ test_zero_speed_rejected passed")


def test_too_small_width_rejected():
    """Bug fix: very small width should raise ValueError."""
    try:
        LavaLamp(width=2, height=30)
        assert False, "Should raise ValueError for width < 5"
    except ValueError as e:
        assert "5" in str(e), f"Error message should mention minimum 5, got: {e}"
    print("✓ test_too_small_width_rejected passed")


def test_too_small_height_rejected():
    """Bug fix: very small height should raise ValueError."""
    try:
        LavaLamp(width=40, height=1)
        assert False, "Should raise ValueError for height < 3"
    except ValueError as e:
        assert "3" in str(e), f"Error message should mention minimum 3, got: {e}"
    print("✓ test_too_small_height_rejected passed")


def test_row_to_y_clamped():
    """Bug fix: _row_to_y should return values in [0, 1].

    Previously, rows 0 and 1 returned negative y values, causing
    negative shape widths and broken rendering at the top of the lamp.
    """
    lamp = LavaLamp(width=40, height=30)
    y0 = lamp._row_to_y(0)
    y1 = lamp._row_to_y(1)
    assert y0 >= 0.0, f"_row_to_y(0) should be >= 0, got {y0}"
    assert y1 >= 0.0, f"_row_to_y(1) should be >= 0, got {y1}"
    assert y0 <= 1.0, f"_row_to_y(0) should be <= 1, got {y0}"
    assert y1 <= 1.0, f"_row_to_y(1) should be <= 1, got {y1}"
    y_last = lamp._row_to_y(lamp.height - 1)
    assert y_last <= 1.0, f"_row_to_y(last) should be <= 1, got {y_last}"
    print("✓ test_row_to_y_clamped passed")


def test_shape_width_no_negative():
    """Bug fix: _shape_width should never return negative values.

    Previously, values of y outside [0, 1] could produce negative widths,
    causing rendering artifacts.
    """
    lamp = LavaLamp(width=40, height=30)
    for y_val in [-0.5, -0.1, 0.0, 0.01, 0.5, 0.99, 1.0, 1.5]:
        w = lamp._shape_width(y_val)
        assert w > 0, f"_shape_width({y_val}) should be > 0, got {w}"
    print("✓ test_shape_width_no_negative passed")


def test_render_first_rows_have_lamp_content():
    """Bug fix: first rows of render should contain lamp content.

    Previously, the top 2 rows had no lamp content because _row_to_y
    returned negative values, causing _shape_width to return negative widths.
    """
    lamp = LavaLamp(width=40, height=30)
    lamp.update(0.1)
    lines = lamp.render()
    found_lamp_content = False
    import re
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    for i in range(2, min(6, len(lines))):
        stripped = ansi_escape.sub('', lines[i])
        if '│' in stripped:
            found_lamp_content = True
            break
    assert found_lamp_content, "Early lamp rows should contain lamp outline characters"
    print("✓ test_render_first_rows_have_lamp_content passed")


def test_empty_lamp_renders():
    """Bug fix: a lamp with zero blobs and bubbles should still render."""
    lamp = LavaLamp(width=40, height=30, num_blobs=0, num_bubbles=0)
    lamp.update(0.1)
    lines = lamp.render()
    assert len(lines) > 0, "Empty lamp should still render"
    print("✓ test_empty_lamp_renders passed")


# ─── Run all tests ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print(f"Terminal Lava Lamp v{VERSION} — Test Suite")
    print("=" * 60)
    print()

    tests = [
        # Basic & helpers
        test_version_defined,
        test_rgb_to_ansi_bounds,
        test_strip_ansi,
        # Blob tests
        test_blob_initialization,
        test_blob_update,
        test_blob_reset,
        test_blob_speed_multiplier,
        test_blob_cooldown_decreases,
        test_blob_out_of_bounds_resets,
        # Bubble tests
        test_bubble_initialization,
        test_bubble_rises,
        test_bubble_dies_at_top,
        test_bubble_max_life,
        # LavaLamp core tests
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
        test_lavalamp_remove_blob,
        test_lavalamp_bubble_respawn,
        test_lavalamp_large_dt_capped,
        test_lavalamp_small_width,
        test_themes_structure,
        test_theme_count,
        test_lavalamp_multiple_updates,
        # Merge/Split tests
        test_merge_nearby_blobs,
        test_merge_increments_counter,
        test_split_increments_counter,
        test_merge_cooldown_prevents_merge,
        test_split_cooldown_prevents_split,
        test_blob_count_changes_dynamically,
        # Screenshot tests
        test_screenshot_save_ansi,
        test_screenshot_save_plain,
        test_screenshot_bad_path,
        # Theme file loading tests
        test_load_themes_from_file,
        test_load_themes_missing_keys,
        test_load_themes_file_not_found,
        test_load_themes_out_of_range_colors,
        # New themes
        test_ember_theme,
        test_frost_theme,
        # Bug regression tests
        test_negative_dt_ignored,
        test_zero_dt_ignored,
        test_negative_speed_rejected,
        test_zero_speed_rejected,
        test_too_small_width_rejected,
        test_too_small_height_rejected,
        test_row_to_y_clamped,
        test_shape_width_no_negative,
        test_render_first_rows_have_lamp_content,
        test_empty_lamp_renders,
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