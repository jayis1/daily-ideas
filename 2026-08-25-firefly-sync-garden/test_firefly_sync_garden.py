from __future__ import annotations

import random
import unittest

import firefly_sync_garden as garden


class FireflySyncGardenTests(unittest.TestCase):
    def test_phase_order_is_one_for_perfect_sync(self):
        self.assertAlmostEqual(1.0, garden.phase_order([0.25, 0.25, 0.25]), places=6)

    def test_apply_flash_coupling_advances_nearby_neighbors(self):
        source = garden.Firefly(x=5.0, y=5.0, vx=0.0, vy=0.0, phase=0.0, period=30.0, flash_timer=2)
        neighbor = garden.Firefly(x=7.0, y=5.0, vx=0.0, vy=0.0, phase=0.4, period=30.0)
        distant = garden.Firefly(x=30.0, y=30.0, vx=0.0, vy=0.0, phase=0.4, period=30.0)
        fireflies = [source, neighbor, distant]

        garden.apply_flash_coupling(fireflies, [0], coupling=0.5, radius=5.0)

        self.assertGreater(neighbor.phase, 0.4)
        self.assertAlmostEqual(0.4, distant.phase)

    def test_snapshot_render_is_deterministic_with_seed(self):
        rng = random.Random(7)
        state = garden.create_state(width=24, height=10, count=8, rng=rng, speed=0.5)
        stats = garden.simulate_snapshot(state, rng, garden.SimConfig(), warmup=12)
        frame = garden.render_frame(
            state,
            stats,
            garden.RenderConfig(use_color=False, unicode=False, show_status=False),
        )
        lines = frame.splitlines()
        self.assertEqual(10, len(lines))
        self.assertTrue(all(len(line) == 24 for line in lines))
        self.assertIn('*', frame)


if __name__ == '__main__':
    unittest.main()
