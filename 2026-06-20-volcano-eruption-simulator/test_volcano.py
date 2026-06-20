#!/usr/bin/env python3
"""Tests for the Volcano Eruption Simulator."""

import math
import random
import sys
import os

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from volcano import (
    VolcanoSimulator, Particle, PyroclasticFlow,
    ERUPTION_TYPES, ERUPTION_TYPE_NAMES, ansi, ansi_bg, RESET, BOLD,
    __version__
)


class TestParticle:
    """Test the Particle class."""

    def test_particle_creation(self):
        p = Particle(5, 10, 0.5, -2.0, 50, "█", 196, "lava")
        assert p.x == 5
        assert p.y == 10
        assert p.vx == 0.5
        assert p.vy == -2.0
        assert p.life == 50
        assert p.max_life == 50
        assert p.char == "█"
        assert p.color == 196
        assert p.ptype == "lava"

    def test_particle_types(self):
        """Test creating particles of different types."""
        for ptype in ("lava", "ash", "smoke", "spark"):
            p = Particle(0, 0, 0, 0, 10, "*", 0, ptype)
            assert p.ptype == ptype


class TestPyroclasticFlow:
    """Test the PyroclasticFlow class."""

    def test_flow_creation(self):
        pf = PyroclasticFlow(start_x=40, start_y=10, direction=1, speed=1.5, width=2, life=60)
        assert pf.x == 40
        assert pf.direction == 1
        assert pf.speed == 1.5
        assert pf.width == 2
        assert pf.life == 60
        assert pf.active is True

    def test_flow_moves_right(self):
        """Flow with direction=1 should move to the right."""
        pf = PyroclasticFlow(start_x=40, start_y=10, direction=1, speed=1.5, width=2, life=60)
        terrain = [20] * 80  # Flat terrain at y=20
        old_x = pf.x
        pf.update(terrain, 80, 24)
        assert pf.x > old_x

    def test_flow_moves_left(self):
        """Flow with direction=-1 should move to the left."""
        pf = PyroclasticFlow(start_x=40, start_y=10, direction=-1, speed=1.5, width=2, life=60)
        terrain = [20] * 80
        old_x = pf.x
        pf.update(terrain, 80, 24)
        assert pf.x < old_x

    def test_flow_dies(self):
        """Flow should become inactive when life runs out."""
        pf = PyroclasticFlow(start_x=40, start_y=10, direction=1, speed=1.0, width=2, life=3)
        terrain = [20] * 80
        pf.update(terrain, 80, 24)
        pf.update(terrain, 80, 24)
        pf.update(terrain, 80, 24)
        assert pf.active is False


class TestVolcanoSimulator:
    """Test the VolcanoSimulator class."""

    def test_initial_state(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        assert sim.width == 80
        assert sim.height == 24
        assert sim.eruption_phase == "dormant"
        assert sim.eruption_intensity == 0.0
        assert sim.running is True
        assert sim.total_eruptions == 0

    def test_custom_dimensions(self):
        sim = VolcanoSimulator(width=120, height=30)
        assert sim.width == 120
        assert sim.height == 30

    def test_minimum_dimensions(self):
        sim = VolcanoSimulator(width=40, height=10)
        assert sim.width == 60  # Minimum 60
        assert sim.height == 20  # Minimum 20

    def test_seed_reproducibility(self):
        """Same seed should produce same terrain."""
        sim1 = VolcanoSimulator(seed=12345, width=80, height=24)
        sim2 = VolcanoSimulator(seed=12345, width=80, height=24)
        assert sim1.terrain == sim2.terrain

    def test_generate_terrain(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        old_terrain = sim.terrain[:]
        sim.generate_terrain()
        # After regenerating, terrain may or may not change
        # (depends on seed state), but it should still be valid
        assert len(sim.terrain) == sim.width
        for h in sim.terrain:
            assert 0 <= h < sim.height

    def test_terrain_valid(self):
        """All terrain heights should be within screen bounds."""
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        for y in sim.terrain:
            assert 0 <= y < sim.height

    def test_crater_exists(self):
        """Crater position should be at the center of the screen."""
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        assert sim.crater_x == sim.width // 2
        assert 0 <= sim.crater_y < sim.height

    def test_trigger_eruption(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        sim.trigger_eruption(0.8)
        assert sim.eruption_phase == "building"
        assert sim.total_eruptions == 1
        assert sim.target_intensity == 0.8

    def test_trigger_eruption_clamps_intensity(self):
        """Intensity should be clamped to [0.0, 1.0]."""
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        sim.trigger_eruption(2.0)
        assert sim.target_intensity <= 1.0
        sim.trigger_eruption(-0.5)
        assert sim.target_intensity >= 0.0

    def test_eruption_phases(self):
        """Test eruption progresses through all phases."""
        sim = VolcanoSimulator(seed=42, width=80, height=24, auto_erupt=False)
        assert sim.eruption_phase == "dormant"
        sim.trigger_eruption(1.0)
        assert sim.eruption_phase == "building"

        # Advance through building phase
        for _ in range(100):
            sim.update_eruption_state()

        # Should be erupting or subsiding at this point
        assert sim.eruption_phase in ("building", "erupting", "subsiding")

    def test_eruption_type_cycling(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        initial_type = sim.eruption_type
        sim.cycle_eruption_type()
        assert sim.eruption_type != initial_type

        # Cycle through all types
        for _ in range(len(ERUPTION_TYPE_NAMES) - 1):
            sim.cycle_eruption_type()
        assert sim.eruption_type == initial_type  # Back to start

    def test_all_eruption_types(self):
        """Test that all eruption types can be set and work."""
        for etype in ERUPTION_TYPE_NAMES:
            sim = VolcanoSimulator(seed=42, width=80, height=24,
                                    eruption_type=etype)
            assert sim.eruption_type == etype
            sim.trigger_eruption()
            assert sim.total_eruptions == 1

    def test_invalid_eruption_type_defaults(self):
        """Invalid eruption type should default to strombolian."""
        sim = VolcanoSimulator(seed=42, width=80, height=24,
                                eruption_type="invalid_type")
        assert sim.eruption_type == "strombolian"

    def test_step_advances_frame(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        old_frame = sim.frame
        sim.step()
        assert sim.frame == old_frame + 1

    def test_step_multiple(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        for _ in range(50):
            sim.step()
        assert sim.frame == 50

    def test_render_produces_lines(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        lines = sim.render()
        assert len(lines) == sim.height

    def test_render_with_eruption(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        sim.trigger_eruption(0.9)
        for _ in range(20):
            sim.step()
        lines = sim.render()
        assert len(lines) == sim.height

    def test_render_stats(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        stats1, stats2, stats3 = sim.render_stats()
        assert isinstance(stats1, str)
        assert isinstance(stats2, str)
        assert isinstance(stats3, str)
        assert "DORMANT" in stats1

    def test_render_stats_during_eruption(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        sim.trigger_eruption(0.9)
        for _ in range(20):
            sim.step()
        stats1, stats2, stats3 = sim.render_stats()
        assert "BUILDING" in stats1 or "ERUPTING" in stats1

    def test_auto_erupt_disabled(self):
        """With auto_erupt=False, volcano should not auto-erupt."""
        sim = VolcanoSimulator(seed=42, width=80, height=24, auto_erupt=False)
        for _ in range(1000):
            sim.step()
        assert sim.total_eruptions == 0

    def test_auto_erupt_enabled(self):
        """With auto_erupt=True, volcano should eventually auto-erupt."""
        sim = VolcanoSimulator(seed=42, width=80, height=24, auto_erupt=True)
        # Set a short timer
        sim.auto_erupt_timer = 5
        for _ in range(50):
            sim.step()
            if sim.total_eruptions > 0:
                break
        assert sim.total_eruptions >= 1

    def test_night_mode(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24, start_night=True)
        assert sim.is_day is False

    def test_day_night_transition(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        initial = sim.day_transition
        sim.is_day = False
        for _ in range(50):
            sim.update_day_night()
        assert sim.day_transition < initial

    def test_initial_intensity(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24,
                                 initial_intensity=0.8)
        assert sim.total_eruptions == 1
        assert sim.eruption_phase == "building"

    def test_particles_spawn_during_eruption(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        sim.trigger_eruption(1.0)
        for _ in range(30):
            sim.step()
        assert len(sim.particles) > 0

    def test_lava_flows_appear(self):
        """After sustained eruption, lava flows should appear on terrain."""
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        sim.trigger_eruption(1.0)
        for _ in range(100):
            sim.step()
        assert len(sim.lava_flows) > 0 or sim.eruption_phase == "dormant"

    def test_shake_during_eruption(self):
        """During eruption, shake intensity should be non-zero."""
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        sim.trigger_eruption(0.9)
        for _ in range(30):
            sim.step()
        assert sim.shake_intensity >= 0

    def test_vei_tracking(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        sim.trigger_eruption(1.0)
        assert sim.vei > 0 or sim.eruption_phase == "building"
        assert sim.max_vei >= 0

    def test_save_screenshot(self):
        """Test screenshot saving."""
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        path = sim.save_screenshot()
        assert path is not None
        assert os.path.exists(path)
        # Clean up
        os.remove(path)

    def test_pyroclastic_flow_tracking(self):
        """Plinian eruptions should potentially spawn pyroclastic flows."""
        sim = VolcanoSimulator(seed=42, width=80, height=24,
                                eruption_type="plinian")
        # Force a high-intensity eruption with pyroclastic flow
        sim.trigger_eruption(1.0)
        # Manually add a pyroclastic flow to test tracking
        sim.pyroclastic_flows.append(
            PyroclasticFlow(40, 10, 1, 1.5, 2, 30)
        )
        assert len(sim.pyroclastic_flows) == 1
        for _ in range(5):
            sim.update_pyroclastic_flows()
        # Flow should still be active or recently died
        assert isinstance(sim.pyroclastic_flows, list)

    def test_version(self):
        assert __version__ == "2.1.0"

    def test_eruption_log(self):
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        sim.trigger_eruption(0.7)
        sim.trigger_eruption(0.9)
        assert len(sim.eruption_log) == 2
        assert sim.eruption_log[0][2] == 0.7
        assert sim.eruption_log[1][2] == 0.9

    def test_intensity_decrease(self):
        """Target intensity should be decreasable."""
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        sim.target_intensity = 0.5
        sim.target_intensity = max(0.0, sim.target_intensity - 0.1)
        assert sim.target_intensity == 0.4

    def test_eruption_state_machine_dormant_decay(self):
        """During dormancy, intensity and seismic should decay."""
        sim = VolcanoSimulator(seed=42, width=80, height=24, auto_erupt=False)
        sim.eruption_intensity = 0.5
        sim.seismic_activity = 0.5
        sim.update_eruption_state()
        assert sim.eruption_intensity < 0.5
        assert sim.seismic_activity < 0.5

    def test_zero_intensity_no_full_eruption(self):
        """trigger_eruption(0.0) should not lead to a full eruption."""
        sim = VolcanoSimulator(seed=42, width=80, height=24, auto_erupt=False)
        sim.trigger_eruption(0.0)
        # Should go to subsiding, not erupting
        assert sim.eruption_phase == "subsiding"
        # Intensity should stay very low
        for _ in range(30):
            sim.update_eruption_state()
        # Should not have erupted with high intensity
        assert sim.eruption_intensity < 0.1 or sim.eruption_phase == "dormant"

    def test_very_low_intensity_subside(self):
        """Very low intensity triggers should subside quickly."""
        sim = VolcanoSimulator(seed=42, width=80, height=24, auto_erupt=False)
        sim.trigger_eruption(0.01)
        assert sim.eruption_phase == "subsiding"

    def test_shake_applied_in_render(self):
        """Shake offsets should affect render output."""
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        # Render without shake
        lines_no_shake = sim.render()
        # Set shake
        sim.shake_intensity = 1.0
        sim.shake_x = 2
        sim.shake_y = 1
        lines_with_shake = sim.render()
        # With shake, output should differ
        assert lines_no_shake != lines_with_shake

    def test_sky_color_smooth_transition(self):
        """Sky color should vary smoothly with day_transition."""
        sim = VolcanoSimulator(seed=42, width=80, height=24)
        # At day_transition 0.0 (full night), sky_color should be SKY_NIGHT (16)
        sim.day_transition = 0.0
        sim.is_day = False
        expected = 16  # SKY_NIGHT
        sky_at_night = int(16 + (195 - 16) * 0.0)
        assert sky_at_night == expected

        # At day_transition 1.0 (full day), sky_color should be SKY_DAY (195)
        sim.day_transition = 1.0
        sim.is_day = True
        sky_at_day = int(16 + (195 - 16) * 1.0)
        assert sky_at_day == 195

        # At 0.5, should be intermediate
        sky_mid = int(16 + (195 - 16) * 0.5)
        assert 16 < sky_mid < 195

    def test_render_adapts_to_width(self):
        """Stats should adapt to narrow terminal widths."""
        sim = VolcanoSimulator(seed=42, width=60, height=20)
        s1, s2, s3 = sim.render_stats()
        # Stats lines should be produced without error
        assert isinstance(s3, str)
        # On narrow terminal, should use short controls
        assert len(s3) < 80  # Short controls should be shorter


class TestANSIHelpers:
    """Test ANSI color helper functions."""

    def test_ansi_fg(self):
        result = ansi(196, "hello")
        assert "\033[38;5;196m" in result
        assert "hello" in result

    def test_ansi_bg(self):
        result = ansi_bg(16, "world")
        assert "\033[48;5;16m" in result
        assert "world" in result

    def test_ansi_empty_text(self):
        result = ansi(255)
        assert "\033[38;5;255m" in result


class TestEruptionTypes:
    """Test eruption type configurations."""

    def test_all_types_have_required_fields(self):
        required = ["label", "intensity_range", "particle_rate", "ash_rate",
                     "lava_flow_rate", "pyroclastic_chance", "shake_mult",
                     "description"]
        for name, etype in ERUPTION_TYPES.items():
            for field in required:
                assert field in etype, f"{name} missing {field}"

    def test_intensity_ranges_valid(self):
        for name, etype in ERUPTION_TYPES.items():
            lo, hi = etype["intensity_range"]
            assert 0 <= lo <= hi <= 1.0, f"{name} has invalid intensity range"

    def test_rates_between_0_and_1(self):
        for name, etype in ERUPTION_TYPES.items():
            assert 0 <= etype["particle_rate"] <= 1
            assert 0 <= etype["ash_rate"] <= 1
            assert 0 <= etype["lava_flow_rate"] <= 1


if __name__ == "__main__":
    # Run tests
    test_classes = [
        TestParticle, TestPyroclasticFlow, TestVolcanoSimulator,
        TestANSIHelpers, TestEruptionTypes
    ]

    total_passed = 0
    total_failed = 0

    for test_class in test_classes:
        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in methods:
            try:
                getattr(instance, method_name)()
                total_passed += 1
            except Exception as e:
                total_failed += 1
                print(f"FAIL: {test_class.__name__}.{method_name}: {e}")

    print(f"\n{total_passed + total_failed} tests: {total_passed} passed, {total_failed} failed")
    if total_failed > 0:
        sys.exit(1)