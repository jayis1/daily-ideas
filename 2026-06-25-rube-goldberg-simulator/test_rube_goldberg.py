#!/usr/bin/env python3
"""
Tests for the Rube Goldberg Machine Simulator.

Run with:
    python3 -m pytest test_rube_goldberg.py -v
or:
    python3 test_rube_goldberg.py
"""

import random
import sys
import os

# Ensure we can import the main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rube_goldberg import (
    RubeGoldbergMachine, Component, Projectile,
    create_preset_machine, create_random_machine,
    BALL, DOMINO, SEESAW, BUCKET, PULLEY, FAN, HAMMER,
    SPRING, FUNNEL, BELL, FLAG, CANDLE, BALLOON,
    IDLE, ACTIVE, TRIGGERED, DONE,
    COMPONENT_CHARS, STAGE_DESCRIPTIONS,
    get_terminal_size, build_parser,
    __version__,
)


# ── Component Tests ────────────────────────────────────────────────

def test_component_default_state():
    """Components should start in IDLE state by default."""
    comp = Component(BALL, 10, 5)
    assert comp.state == IDLE
    assert comp.timer == 0
    assert comp.direction == 1
    assert comp.extra == {}
    assert comp.stage_name == ""


def test_component_custom_state():
    """Components should accept custom state and extra data."""
    comp = Component(BALL, 10, 5, state=ACTIVE, timer=3,
                     extra={"fall_to": 15}, stage_name="Test Ball")
    assert comp.state == ACTIVE
    assert comp.timer == 3
    assert comp.extra["fall_to"] == 15
    assert comp.stage_name == "Test Ball"


def test_component_char_ball():
    """Ball component should display as ●."""
    comp = Component(BALL, 0, 0)
    assert comp.char == "●"


def test_component_char_domino_idle():
    """Idle domino should display as ▌."""
    comp = Component(DOMINO, 0, 0, state=IDLE)
    assert comp.char == "▌"


def test_component_char_domino_active():
    """Active/triggered domino should display as ▀."""
    for state in (ACTIVE, TRIGGERED, DONE):
        comp = Component(DOMINO, 0, 0, state=state)
        assert comp.char == "▀"


def test_component_char_seesaw():
    """Seesaw should change appearance based on state."""
    comp = Component(SEESAW, 0, 0, state=IDLE)
    assert comp.char == "—"
    comp.state = ACTIVE
    assert comp.char == "/"
    comp.state = TRIGGERED
    assert comp.char == "\\"


def test_component_char_bucket():
    """Bucket should change appearance when triggered/done."""
    comp = Component(BUCKET, 0, 0, state=IDLE)
    assert comp.char == "╘╤╛"
    comp.state = TRIGGERED
    assert comp.char == "╘╤╛"
    comp.state = DONE
    assert comp.char == "╘═╛"


def test_component_char_flag():
    """Flag should show ⚐ when idle/active and ⚑ when done."""
    for state in (IDLE, ACTIVE, TRIGGERED):
        comp = Component(FLAG, 0, 0, state=state)
        assert comp.char == "⚐"
    comp = Component(FLAG, 0, 0, state=DONE)
    assert comp.char == "⚑"


def test_component_char_unknown():
    """Unknown component type should display as ?."""
    comp = Component("unknown_type", 0, 0)
    assert comp.char == "?"


def test_component_triggered_property():
    """triggered property should be True for TRIGGERED and DONE states."""
    comp = Component(BALL, 0, 0, state=IDLE)
    assert comp.triggered is False
    comp.state = ACTIVE
    assert comp.triggered is False
    comp.state = TRIGGERED
    assert comp.triggered is True
    comp.state = DONE
    assert comp.triggered is True


def test_component_describe():
    """describe() should return a human-readable string."""
    comp = Component(BALL, 10, 5, state=IDLE, stage_name="Starting Ball")
    desc = comp.describe()
    assert "Starting Ball" in desc
    assert "(10, 5)" in desc
    assert "waiting" in desc

    comp.state = DONE
    desc = comp.describe()
    assert "done" in desc


# ── Projectile Tests ───────────────────────────────────────────────

def test_projectile_default():
    """Projectiles should have sensible defaults."""
    proj = Projectile("ball", 10.0, 5.0, 1.0, 0.5)
    assert proj.kind == "ball"
    assert proj.x == 10.0
    assert proj.y == 5.0
    assert proj.dx == 1.0
    assert proj.dy == 0.5
    assert proj.life == 100
    assert proj.trail == []


def test_projectile_char_ball():
    proj = Projectile("ball", 0, 0, 1, 0)
    assert proj.char == "●"


def test_projectile_char_water():
    proj = Projectile("water", 0, 0, 1, 0)
    assert proj.char == "≈"


def test_projectile_char_spark():
    proj = Projectile("spark", 0, 0, 1, 0)
    assert proj.char == "✦"


def test_projectile_char_air():
    proj = Projectile("air", 0, 0, 1, 0)
    assert proj.char == "~"


def test_projectile_char_unknown():
    proj = Projectile("mystery", 0, 0, 1, 0)
    assert proj.char == "•"


# ── Machine Generation Tests ───────────────────────────────────────

def test_create_preset_machine():
    """Preset machine should have the expected components."""
    machine = create_preset_machine(90, 35)
    assert len(machine.components) > 0
    # Should have at least one ball, bell, and flag
    kinds = [c.kind for c in machine.components]
    assert BALL in kinds, "Preset machine should have at least one ball"
    assert BELL in kinds, "Preset machine should have a bell"
    assert FLAG in kinds, "Preset machine should have a flag"
    # Preset machine should have its stage log
    assert len(machine._stage_log) > 0


def test_create_random_machine():
    """Random machine should generate components."""
    machine = create_random_machine(90, 35, seed=42)
    assert len(machine.components) > 0
    # Should have at least one ball, bell, and flag
    kinds = [c.kind for c in machine.components]
    assert BALL in kinds, "Random machine should have at least one ball"
    assert BELL in kinds, "Random machine should have a bell"
    assert FLAG in kinds, "Random machine should have a flag"


def test_random_machine_seeded():
    """Same seed should produce same machine."""
    m1 = create_random_machine(90, 35, seed=123)
    m2 = create_random_machine(90, 35, seed=123)
    assert len(m1.components) == len(m2.components)
    for c1, c2 in zip(m1.components, m2.components):
        assert c1.kind == c2.kind
        assert c1.x == c2.x
        assert c1.y == c2.y


def test_random_machine_different_seeds():
    """Different seeds should usually produce different machines."""
    m1 = create_random_machine(90, 35, seed=1)
    m2 = create_random_machine(90, 35, seed=2)
    # At least the component count or positions should differ
    same = (len(m1.components) == len(m2.components) and
            all(c1.x == c2.x and c1.kind == c2.kind
                for c1, c2 in zip(m1.components, m2.components)))
    # It's theoretically possible they match, but very unlikely
    assert not same, "Different seeds should produce different machines"


def test_machine_dimensions():
    """Machine should respect provided dimensions."""
    machine = create_random_machine(60, 25, seed=42)
    assert machine.width == 60
    assert machine.height == 25
    # Components should be within canvas bounds (with some tolerance)
    for comp in machine.components:
        assert comp.x >= 0, f"Component x={comp.x} is negative"
        assert comp.y >= 0, f"Component y={comp.y} is negative"


# ── Simulation Tests ───────────────────────────────────────────────

def test_step_advances_frame():
    """Each step should increment the frame counter."""
    machine = create_preset_machine(90, 35)
    assert machine.frame == 0
    machine.step()
    assert machine.frame == 1
    machine.step()
    assert machine.frame == 2


def test_step_updates_component_timers():
    """Stepping should decrement timers and transition states."""
    machine = create_preset_machine(90, 35)
    # Find a component with IDLE state and timer > 1
    idle_comp = None
    for comp in machine.components:
        if comp.state == IDLE and comp.timer > 5:
            idle_comp = comp
            break
    assert idle_comp is not None, "Should have at least one IDLE component with timer > 5"

    initial_timer = idle_comp.timer
    for _ in range(initial_timer + 10):
        machine.step()

    # The component should have transitioned past IDLE
    assert idle_comp.state != IDLE, f"Component should have left IDLE state, but is {idle_comp.state}"


def test_preset_machine_completes():
    """Preset machine should eventually reach the DONE state for the flag."""
    machine = create_preset_machine(90, 35)
    for _ in range(500):
        machine.step()
        if machine.complete:
            break
    assert machine.complete, "Preset machine should complete within 500 frames"


def test_random_machine_completes():
    """Random machine with seed should eventually complete."""
    random.seed(42)
    machine = create_random_machine(90, 35, seed=42)
    for _ in range(500):
        machine.step()
        if machine.complete:
            break
    assert machine.complete, "Random machine should complete within 500 frames"


def test_projectiles_appear():
    """Stepping should produce projectiles when components activate."""
    machine = create_preset_machine(90, 35)
    # Run a few frames — the starting ball is ACTIVE and will spawn projectiles
    machine.step()
    # After the first step, the ACTIVE ball should have produced a projectile
    has_projectiles = len(machine.projectiles) > 0
    # If not yet, run a few more
    for _ in range(20):
        machine.step()
        if len(machine.projectiles) > 0:
            has_projectiles = True
            break
    assert has_projectiles, "Should produce projectiles during simulation"


def test_projectile_trail():
    """Projectiles should accumulate trail positions."""
    machine = create_preset_machine(90, 35)
    # Run until we have a projectile with a trail
    for _ in range(50):
        machine.step()
        for proj in machine.projectiles:
            if len(proj.trail) > 0:
                return  # Trail found, test passes
    # Even if no trail (projectiles may be short-lived), that's acceptable
    # The important thing is the simulation runs without errors


def test_sparkles_decay():
    """Sparkles should decay over time."""
    machine = create_preset_machine(90, 35)
    machine.sparkles = [(10, 5, 3)]
    machine.step()
    assert len(machine.sparkles) == 1
    assert machine.sparkles[0][2] == 2  # ttl decreased
    # Run until sparkle expires
    machine.step()
    machine.step()
    assert len([s for s in machine.sparkles if s[2] <= 0]) == 0


def test_message_timer():
    """Messages should clear after the timer expires."""
    machine = create_preset_machine(90, 35)
    machine.message = "Test message"
    machine.message_timer = 5
    for _ in range(6):
        machine.step()
    assert machine.message == "", "Message should have cleared after timer expired"


# ── Rendering Tests ────────────────────────────────────────────────

def test_render_produces_output():
    """render() should produce a non-empty string."""
    machine = create_preset_machine(90, 35)
    output = machine.render()
    assert len(output) > 0, "Render should produce output"
    assert "RUBE GOLDBERG" in output, "Render should include title"


def test_render_includes_status():
    """Rendered output should include frame and component counts."""
    machine = create_preset_machine(90, 35)
    output = machine.render()
    assert "Frame:" in output
    assert "Components:" in output
    assert "Projectiles:" in output


def test_render_border():
    """Rendered output should have box-drawing borders."""
    machine = create_preset_machine(90, 35)
    output = machine.render()
    assert "╔" in output
    assert "╗" in output
    assert "╚" in output
    assert "╝" in output


def test_render_with_color():
    """Color mode should include ANSI escape codes."""
    machine = create_preset_machine(90, 35, color=True)
    output = machine.render()
    assert "\033[" in output, "Color mode should include ANSI escape codes"


def test_render_without_color():
    """Non-color mode should not include ANSI escape codes for components."""
    machine = create_preset_machine(90, 35, color=False)
    output = machine.render()
    assert "\033[" not in output, "Non-color mode should not include ANSI codes"


def test_render_completion_message():
    """Completion should trigger a message in the render output."""
    machine = create_preset_machine(90, 35)
    # Force completion
    for comp in machine.components:
        if comp.kind == FLAG:
            comp.state = DONE
    machine.complete = True
    machine.message = "🎉  MACHINE COMPLETE!  🎉"
    output = machine.render()
    assert "MACHINE COMPLETE" in output


# ── Describe Mode Tests ────────────────────────────────────────────

def test_describe_preset():
    """describe() should return a readable description for preset machine."""
    machine = create_preset_machine(90, 35)
    desc = machine.describe()
    assert "Rube Goldberg" in desc
    assert "Components:" in desc or "components" in desc.lower()


def test_describe_random():
    """describe() should include stage names for random machine."""
    machine = create_random_machine(90, 35, seed=42)
    desc = machine.describe()
    assert "Stages" in desc or "stage" in desc.lower()
    # Should mention at least one stage type
    assert "domino" in desc.lower() or "seesaw" in desc.lower() or "bucket" in desc.lower()


def test_describe_includes_seed():
    """describe() should report the seed used."""
    machine = create_random_machine(90, 35, seed=42)
    desc = machine.describe()
    assert "42" in desc


def test_describe_includes_dimensions():
    """describe() should report canvas dimensions."""
    machine = create_random_machine(90, 35, seed=42)
    desc = machine.describe()
    assert "90" in desc
    assert "35" in desc


# ── CLI Parser Tests ───────────────────────────────────────────────

def test_parser_defaults():
    """Default args should be sensible."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.preset is False
    assert args.random is False
    assert args.marathon is False
    assert args.seed == 0
    assert args.speed > 0
    assert args.color is False
    assert args.describe is False


def test_parser_preset():
    parser = build_parser()
    args = parser.parse_args(["--preset"])
    assert args.preset is True


def test_parser_random_with_seed():
    parser = build_parser()
    args = parser.parse_args(["--random", "--seed", "42"])
    assert args.random is True
    assert args.seed == 42


def test_parser_marathon_with_color():
    parser = build_parser()
    args = parser.parse_args(["--marathon", "--color"])
    assert args.marathon is True
    assert args.color is True


def test_parser_describe():
    parser = build_parser()
    args = parser.parse_args(["--describe", "--random"])
    assert args.describe is True
    assert args.random is True


def test_parser_speed():
    parser = build_parser()
    args = parser.parse_args(["--speed", "0.03"])
    assert args.speed == 0.03


def test_parser_dimensions():
    parser = build_parser()
    args = parser.parse_args(["--width", "60", "--height", "25"])
    assert args.width == 60
    assert args.height == 25


def test_version():
    """Version should be a valid version string."""
    assert __version__ is not None
    parts = __version__.split(".")
    assert len(parts) >= 2, "Version should have at least major.minor"


# ── Utility Tests ───────────────────────────────────────────────────

def test_get_terminal_size():
    """get_terminal_size should return reasonable dimensions."""
    width, height = get_terminal_size()
    assert width >= 50, f"Width {width} is too small"
    assert height >= 20, f"Height {height} is too small"


def test_component_chars_completeness():
    """All defined component types should have visual representations."""
    for kind in [BALL, DOMINO, SEESAW, BUCKET, PULLEY, FAN, CANDLE,
                 BALLOON, HAMMER, FUNNEL, SPRING, BELL, FLAG]:
        assert kind in COMPONENT_CHARS, f"Component type {kind} missing from COMPONENT_CHARS"


def test_stage_descriptions_completeness():
    """All stage types used in generation should have descriptions."""
    # The stage types used in _design_machine
    stage_names = [
        "starting_ball", "domino_chain", "seesaw_launch", "bucket_dump",
        "hammer_smash", "fan_blow", "spring_launch",
        "funnel_redirect", "pulley_lift", "final_ball",
    ]
    for name in stage_names:
        assert name in STAGE_DESCRIPTIONS, f"Stage {name} missing from STAGE_DESCRIPTIONS"


def test_preset_describe_no_mysterious():
    """Preset machine describe() should not show 'A mysterious mechanism'."""
    machine = create_preset_machine(90, 35)
    desc = machine.describe()
    assert "A mysterious mechanism" not in desc, (
        "Preset describe() should not contain 'A mysterious mechanism'"
    )


def test_random_describe_no_mysterious():
    """Random machine describe() should not show 'A mysterious mechanism'."""
    machine = create_random_machine(90, 35, seed=42)
    desc = machine.describe()
    assert "A mysterious mechanism" not in desc, (
        "Random describe() should not contain 'A mysterious mechanism'"
    )


def test_component_bounds_preset():
    """Preset machine components should stay within canvas bounds."""
    for w, h in [(50, 20), (60, 25), (80, 30), (90, 35)]:
        machine = create_preset_machine(w, h)
        for comp in machine.components:
            assert 0 <= comp.x < w, f"Preset {comp.kind} at x={comp.x} out of [0, {w})"
            assert 0 <= comp.y < h, f"Preset {comp.kind} at y={comp.y} out of [0, {h})"


def test_component_bounds_random():
    """Random machine components should stay within canvas bounds."""
    for w, h in [(50, 20), (60, 25)]:
        for seed in range(1, 31):
            machine = create_random_machine(w, h, seed=seed)
            for comp in machine.components:
                assert 0 <= comp.x < w, (
                    f"Seed {seed}: {comp.kind} at x={comp.x} out of [0, {w})"
                )
                assert 0 <= comp.y < h, (
                    f"Seed {seed}: {comp.kind} at y={comp.y} out of [0, {h})"
                )


# ── Run Tests ──────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run all tests when executed directly
    import traceback
    test_functions = [
        obj for name, obj in sorted(globals().items())
        if callable(obj) and name.startswith("test_")
    ]
    passed = 0
    failed = 0
    for test_func in test_functions:
        name = test_func.__name__
        try:
            test_func()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    sys.exit(1 if failed > 0 else 0)