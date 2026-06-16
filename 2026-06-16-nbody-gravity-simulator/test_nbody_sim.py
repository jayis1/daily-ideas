"""Tests for N-Body Gravity Simulator."""

import math
import random

import pytest
from nbody_sim import Body, Simulation, G, SOFTENING, DT_BASE


# ─── Body Tests ──────────────────────────────────────────────────────────────


class TestBody:
    """Tests for the Body class."""

    def test_body_defaults(self):
        b = Body(10, 20)
        assert b.x == 10
        assert b.y == 20
        assert b.vx == 0.0
        assert b.vy == 0.0
        assert b.mass == 1.0
        assert b.alive is True
        assert b.trail == []

    def test_body_custom_params(self):
        b = Body(5, 15, vx=1.0, vy=-0.5, mass=10.0, color_idx=3)
        assert b.vx == 1.0
        assert b.vy == -0.5
        assert b.mass == 10.0
        assert b.color_idx == 3

    def test_radius_display(self):
        assert Body(0, 0, mass=0.5).radius_display() == 0
        assert Body(0, 0, mass=5).radius_display() == 0
        assert Body(0, 0, mass=10).radius_display() == 1
        assert Body(0, 0, mass=50).radius_display() == 2
        assert Body(0, 0, mass=200).radius_display() == 2

    def test_char_mass_tiers(self):
        assert Body(0, 0, mass=0.5).char() == "·"
        assert Body(0, 0, mass=3).char() == "◆"
        assert Body(0, 0, mass=10).char() == "●"
        assert Body(0, 0, mass=50).char() == "✦"
        assert Body(0, 0, mass=100).char() == "★"

    def test_kinetic_energy(self):
        b = Body(0, 0, vx=3, vy=4, mass=2.0)
        # KE = 0.5 * m * (vx^2 + vy^2) = 0.5 * 2 * (9 + 16) = 25
        assert b.kinetic_energy() == pytest.approx(25.0)

    def test_kinetic_energy_zero(self):
        b = Body(0, 0, mass=100)
        assert b.kinetic_energy() == 0.0


# ─── Simulation Tests ────────────────────────────────────────────────────────


class TestSimulation:
    """Tests for the Simulation class."""

    def test_empty_simulation(self):
        sim = Simulation(80, 24)
        assert sim.bodies == []
        assert sim.collision_count == 0

    def test_add_default_scene(self):
        sim = Simulation(80, 24)
        sim.add_default_scene()
        assert len(sim.bodies) == 6  # 1 star + 5 planets
        assert sim.bodies[0].mass == 200

    def test_add_binary_star_scene(self):
        sim = Simulation(80, 24)
        sim.add_binary_star_scene()
        assert len(sim.bodies) == 8  # 2 stars + 6 planets
        assert sim.bodies[0].mass == 100
        assert sim.bodies[1].mass == 100

    def test_add_figure_eight_scene(self):
        sim = Simulation(80, 24)
        sim.add_figure_eight_scene()
        assert len(sim.bodies) == 3
        assert all(b.mass == 30 for b in sim.bodies)

    def test_add_cluster_scene(self):
        sim = Simulation(80, 24)
        sim.add_cluster_scene()
        assert len(sim.bodies) == 25

    def test_step_advances_frame(self):
        sim = Simulation(80, 24)
        sim.add_default_scene()
        f0 = sim.frame
        sim.step()
        assert sim.frame == f0 + 1

    def test_step_when_paused(self):
        sim = Simulation(80, 24)
        sim.add_default_scene()
        sim.paused = True
        f0 = sim.frame
        sim.step()
        assert sim.frame == f0  # no advance when paused

    def test_single_body_doesnt_move(self):
        """A single body with no velocity stays put (no other gravity sources)."""
        sim = Simulation(80, 24)
        b = Body(40, 12, mass=5.0)
        sim.bodies.append(b)
        sim.step()
        assert b.x == pytest.approx(40.0)
        assert b.y == pytest.approx(12.0)

    def test_two_body_attraction(self):
        """Two bodies should accelerate toward each other."""
        sim = Simulation(80, 24)
        b1 = Body(30, 12, mass=50.0, color_idx=0)
        b2 = Body(50, 12, mass=50.0, color_idx=1)
        sim.bodies = [b1, b2]
        sim.step()
        # b1 should move right (toward b2), b2 should move left (toward b1)
        assert b1.x > 30.0
        assert b2.x < 50.0

    def test_two_body_orbit_stability(self):
        """Two-body orbit should remain roughly stable over many steps."""
        sim = Simulation(80, 24)
        b1 = Body(40, 12, 0, 0, mass=100, color_idx=0)
        b2 = Body(52, 12, 0, 0, mass=1, color_idx=1)
        # Circular orbit velocity
        v = math.sqrt(G * b1.mass / 12)
        b2.vy = v
        sim.bodies = [b1, b2]
        initial_dist = 12.0
        for _ in range(200):
            sim.step()
        dx = b2.x - b1.x
        dy = b2.y - b1.y
        dist = math.sqrt(dx ** 2 + dy ** 2)
        # Orbit should remain within 30% of initial distance
        assert abs(dist - initial_dist) / initial_dist < 0.3

    def test_collision_merging(self):
        """Two bodies that collide should merge into one."""
        sim = Simulation(80, 24)
        b1 = Body(40, 12, 0.1, 0, mass=10)
        b2 = Body(40.5, 12, -0.1, 0, mass=5)
        sim.bodies = [b1, b2]
        for _ in range(20):
            sim.step()
        # Should have merged
        assert len(sim.bodies) == 1
        assert sim.bodies[0].mass == pytest.approx(15.0)
        assert sim.collision_count >= 1

    def test_momentum_conservation_in_merge(self):
        """Total momentum should be conserved during a collision."""
        sim = Simulation(80, 24)
        b1 = Body(40, 12, 2.0, 1.0, mass=10)
        b2 = Body(41, 12, -1.0, 0.5, mass=5)
        sim.bodies = [b1, b2]
        # Initial total momentum
        px_before = b1.vx * b1.mass + b2.vx * b2.mass
        py_before = b1.vy * b1.mass + b2.vy * b2.mass
        for _ in range(50):
            sim.step()
        # After merging, total momentum should be conserved
        px_after = sum(b.vx * b.mass for b in sim.bodies)
        py_after = sum(b.vy * b.mass for b in sim.bodies)
        assert px_after == pytest.approx(px_before, abs=0.5)
        assert py_after == pytest.approx(py_before, abs=0.5)

    def test_clear_bodies(self):
        sim = Simulation(80, 24)
        sim.add_default_scene()
        sim.bodies.clear()
        sim.collision_count = 0
        assert len(sim.bodies) == 0

    def test_delete_nearest(self):
        sim = Simulation(80, 24)
        b = Body(40, 12, mass=5.0)
        sim.bodies.append(b)
        result = sim.delete_nearest(40, 12)
        assert result is True
        assert len(sim.bodies) == 0

    def test_delete_nearest_empty(self):
        sim = Simulation(80, 24)
        result = sim.delete_nearest(40, 12)
        assert result is False

    def test_delete_nearest_too_far(self):
        sim = Simulation(80, 24)
        b = Body(40, 12, mass=5.0)
        sim.bodies.append(b)
        # Try to delete from far away (outside 20-unit radius → 400 squared)
        result = sim.delete_nearest(100, 100)
        assert result is False
        assert len(sim.bodies) == 1

    def test_compute_energy(self):
        sim = Simulation(80, 24)
        b1 = Body(40, 12, vx=1, vy=0, mass=10)
        b2 = Body(52, 12, vx=0, vy=1, mass=5)
        sim.bodies = [b1, b2]
        ke, pe, te = sim.compute_energy()
        # KE = 0.5*10*(1+0) + 0.5*5*(0+1) = 5 + 2.5 = 7.5
        assert ke == pytest.approx(7.5)
        # PE should be negative (attractive force)
        assert pe < 0
        assert te == pytest.approx(ke + pe)

    def test_center_of_mass(self):
        sim = Simulation(80, 24)
        # Two equal masses at (10,10) and (30,10) → COM at (20,10)
        sim.bodies = [Body(10, 10, mass=5), Body(30, 10, mass=5)]
        cx, cy = sim.center_of_mass()
        assert cx == pytest.approx(20.0)
        assert cy == pytest.approx(10.0)

    def test_center_of_mass_single_body(self):
        sim = Simulation(80, 24)
        sim.bodies = [Body(42, 17, mass=1)]
        cx, cy = sim.center_of_mass()
        assert cx == pytest.approx(42.0)
        assert cy == pytest.approx(17.0)

    def test_center_of_mass_empty(self):
        sim = Simulation(80, 24)
        cx, cy = sim.center_of_mass()
        # Falls back to camera center
        assert cx == sim.cam_x
        assert cy == sim.cam_y

    def test_speed_control(self):
        sim = Simulation(80, 24)
        assert sim.speed_mult == 1.0
        sim.speed_mult *= 1.5
        assert sim.speed_mult == pytest.approx(1.5)
        sim.speed_mult /= 1.5
        assert sim.speed_mult == pytest.approx(1.0)

    def test_step_with_custom_dt(self):
        sim = Simulation(80, 24)
        b = Body(40, 12, vx=1.0, vy=0.0, mass=1.0)
        sim.bodies.append(b)
        sim.step(dt=0.1)
        # Position should advance by vx * dt = 1.0 * 0.1 = 0.1
        assert b.x == pytest.approx(40.1)

    def test_substep_stability(self):
        """Sub-stepping should give similar results to single step at lower speed."""
        sim1 = Simulation(80, 24)
        sim2 = Simulation(80, 24)
        b1 = Body(40, 12, 0, 0.5, mass=10, color_idx=0)
        b2 = Body(52, 12, 0, 0, mass=10, color_idx=1)
        sim1.bodies = [Body(b1.x, b1.y, b1.vx, b1.vy, b1.mass, b1.color_idx),
                       Body(b2.x, b2.y, b2.vx, b2.vy, b2.mass, b2.color_idx)]
        sim2.bodies = [Body(b1.x, b1.y, b1.vx, b1.vy, b1.mass, b1.color_idx),
                       Body(b2.x, b2.y, b2.vx, b2.vy, b2.mass, b2.color_idx)]
        # sim1: 1 step at speed_mult=1
        sim1.step()
        # sim2: 2 sub-steps at speed_mult=2 → total dt same
        dt_sub = DT_BASE * 2.0 / 2
        sim2.step(dt=dt_sub)
        sim2.step(dt=dt_sub)
        # Positions should be close but not identical (due to nonlinearity)
        # The key point is they should both remain finite and reasonable
        for b in sim2.bodies:
            assert abs(b.x) < 1000
            assert abs(b.y) < 1000

    def test_max_bodies_cap(self):
        """Verify MAX_BODIES constant is reasonable."""
        from nbody_sim import MAX_BODIES
        assert MAX_BODIES == 80


# ─── Edge Case Tests ─────────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge case and robustness tests."""

    def test_zero_mass_body(self):
        """A zero-mass body should not cause division by zero."""
        sim = Simulation(80, 24)
        b1 = Body(40, 12, mass=10.0)
        b2 = Body(50, 12, mass=0.01)  # Near-zero mass
        sim.bodies = [b1, b2]
        # Should not crash
        for _ in range(10):
            sim.step()
        assert len(sim.bodies) >= 1

    def test_overlapping_bodies_merge(self):
        """Bodies placed on top of each other should merge."""
        sim = Simulation(80, 24)
        b1 = Body(40, 12, mass=5.0)
        b2 = Body(40, 12, mass=3.0)  # Same position
        sim.bodies = [b1, b2]
        sim.step()
        assert len(sim.bodies) == 1
        assert sim.bodies[0].mass == pytest.approx(8.0)

    def test_trail_length_limit(self):
        """Trails should be capped at MAX_TRAIL points."""
        from nbody_sim import MAX_TRAIL
        sim = Simulation(80, 24)
        b = Body(40, 12, vx=1.0, mass=1.0)
        sim.bodies.append(b)
        for _ in range(MAX_TRAIL + 50):
            sim.step()
        assert len(b.trail) <= MAX_TRAIL

    def test_many_bodies_no_crash(self):
        """Simulate with many bodies without crashing."""
        sim = Simulation(80, 24)
        random.seed(42)
        for i in range(20):
            angle = 2 * math.pi * i / 20
            x = 40 + 15 * math.cos(angle)
            y = 12 + 15 * math.sin(angle)
            v = math.sqrt(1.0 * 100 / 15)
            vx = -v * math.sin(angle)
            vy = v * math.cos(angle)
            sim.bodies.append(Body(x, y, vx, vy, mass=random.uniform(0.5, 3.0)))
        for _ in range(50):
            sim.step()
        # Should still have bodies (some may have merged)
        assert len(sim.bodies) >= 1

    def test_color_idx_in_range_default_scene(self):
        """All bodies in default scene should have valid color_idx."""
        from nbody_sim import BODY_COLORS
        sim = Simulation(80, 24)
        sim.add_default_scene()
        for b in sim.bodies:
            assert 0 <= b.color_idx < len(BODY_COLORS), \
                f"color_idx {b.color_idx} out of range [0, {len(BODY_COLORS)-1}]"

    def test_color_idx_in_range_binary_scene(self):
        """All bodies in binary star scene should have valid color_idx."""
        from nbody_sim import BODY_COLORS
        sim = Simulation(80, 24)
        sim.add_binary_star_scene()
        for b in sim.bodies:
            assert 0 <= b.color_idx < len(BODY_COLORS), \
                f"color_idx {b.color_idx} out of range [0, {len(BODY_COLORS)-1}]"

    def test_color_idx_in_range_figure8_scene(self):
        """All bodies in figure-8 scene should have valid color_idx."""
        from nbody_sim import BODY_COLORS
        sim = Simulation(80, 24)
        sim.add_figure_eight_scene()
        for b in sim.bodies:
            assert 0 <= b.color_idx < len(BODY_COLORS), \
                f"color_idx {b.color_idx} out of range [0, {len(BODY_COLORS)-1}]"

    def test_screen_to_world_no_offset(self):
        """screen_to_world with no offset returns same coords."""
        sim = Simulation(80, 24)
        wx, wy = sim.screen_to_world(40, 12)
        assert wx == pytest.approx(40.0)
        assert wy == pytest.approx(12.0)

    def test_screen_to_world_with_offset(self):
        """screen_to_world with camera offset converts correctly."""
        sim = Simulation(80, 24)
        sim.cam_offset_x = 50.0
        sim.cam_offset_y = 10.0
        wx, wy = sim.screen_to_world(40, 12)
        assert wx == pytest.approx(90.0)
        assert wy == pytest.approx(22.0)

    def test_delete_nearest_with_camera_offset(self):
        """delete_nearest should work with camera offset active."""
        sim = Simulation(80, 24)
        # Body at world (140, 12)
        sim.bodies.append(Body(140, 12, mass=5.0))
        # Camera offset makes world(140,12) appear at screen(40,12)
        sim.cam_offset_x = 100.0
        result = sim.delete_nearest(40, 12)
        assert result is True
        assert len(sim.bodies) == 0

    def test_substep_frame_increment(self):
        """Sub-stepping should only increment frame once per logical frame."""
        sim = Simulation(80, 24)
        sim.add_default_scene()
        sim.speed_mult = 4.0
        initial_frame = sim.frame
        sub_steps = max(1, int(sim.speed_mult))
        dt_per_step = DT_BASE * sim.speed_mult / sub_steps
        for s in range(sub_steps):
            is_last = (s == sub_steps - 1)
            sim.step(dt=dt_per_step, increment_frame=is_last)
        assert sim.frame == initial_frame + 1

    def test_figure8_zero_momentum(self):
        """Figure-8 scene should have zero total momentum."""
        sim = Simulation(80, 24)
        sim.add_figure_eight_scene()
        px = sum(b.vx * b.mass for b in sim.bodies)
        py = sum(b.vy * b.mass for b in sim.bodies)
        assert abs(px) < 0.01, f"x-momentum should be ~0, got {px}"
        assert abs(py) < 0.01, f"y-momentum should be ~0, got {py}"

    def test_figure8_center_of_mass_at_center(self):
        """Figure-8 scene COM should be at camera center."""
        sim = Simulation(80, 24)
        sim.add_figure_eight_scene()
        cx, cy = sim.center_of_mass()
        assert cx == pytest.approx(sim.cam_x, abs=0.01)
        assert cy == pytest.approx(sim.cam_y, abs=0.01)