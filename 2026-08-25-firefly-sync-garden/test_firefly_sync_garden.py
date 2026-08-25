from __future__ import annotations

import csv
import random
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import firefly_sync_garden as garden


class FireflySyncGardenTests(unittest.TestCase):
    def test_phase_order_is_one_for_perfect_sync(self):
        self.assertAlmostEqual(1.0, garden.phase_order([0.25, 0.25, 0.25]), places=6)

    def test_apply_flash_coupling_advances_nearby_neighbors(self):
        source = garden.Firefly(x=5.0, y=5.0, vx=0.0, vy=0.0, phase=0.0, period=30.0, flash_timer=2)
        neighbor = garden.Firefly(x=7.0, y=5.0, vx=0.0, vy=0.0, phase=0.4, period=30.0)
        distant = garden.Firefly(x=20.0, y=5.0, vx=0.0, vy=0.0, phase=0.4, period=30.0)
        state = garden.GardenState(width=24, height=12, fireflies=[source, neighbor, distant])

        garden.apply_flash_coupling(state, [0], coupling=0.5, radius=5.0)

        self.assertGreater(neighbor.phase, 0.4)
        self.assertAlmostEqual(0.4, distant.phase)

    def test_apply_flash_coupling_wraps_across_edges(self):
        source = garden.Firefly(x=0.2, y=5.0, vx=0.0, vy=0.0, phase=0.0, period=30.0, flash_timer=2)
        edge_neighbor = garden.Firefly(x=23.7, y=5.0, vx=0.0, vy=0.0, phase=0.3, period=30.0)
        state = garden.GardenState(width=24, height=12, fireflies=[source, edge_neighbor])

        garden.apply_flash_coupling(state, [0], coupling=0.4, radius=2.0)

        self.assertGreater(edge_neighbor.phase, 0.3)

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

    def test_run_analysis_collects_expected_rows(self):
        rng = random.Random(11)
        state = garden.create_state(width=30, height=12, count=10, rng=rng, speed=0.5)
        history, summary = garden.run_analysis(state, rng, garden.SimConfig(), steps=15)

        self.assertEqual(15, len(history))
        self.assertEqual(15, summary.steps)
        self.assertTrue(all(set(row) == {"frame", "flashes", "order", "synced_ratio", "mean_phase"} for row in history))
        self.assertGreaterEqual(summary.max_order, summary.final_order)
        self.assertGreaterEqual(summary.max_synced_ratio, summary.final_synced_ratio)

    def test_save_analysis_csv_writes_expected_columns(self):
        history = [
            {"frame": 1.0, "flashes": 2.0, "order": 0.5, "synced_ratio": 0.25, "mean_phase": 0.75},
            {"frame": 2.0, "flashes": 1.0, "order": 0.6, "synced_ratio": 0.30, "mean_phase": 0.10},
        ]
        with TemporaryDirectory() as tmpdir:
            destination = garden.save_analysis_csv(str(Path(tmpdir) / "metrics.csv"), history)
            with destination.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(["frame", "flashes", "order", "synced_ratio", "mean_phase"], list(rows[0].keys()))
        self.assertEqual("2.0", rows[0]["flashes"])
        self.assertEqual("0.10", f"{float(rows[1]['mean_phase']):.2f}")

    def test_resolve_options_applies_preset_and_overrides(self):
        parser = garden.build_parser()
        args = parser.parse_args(["--preset", "calm", "--count", "99", "--palette", "violet"])

        resolved = garden.resolve_options(args)

        self.assertEqual(99, resolved["count"])
        self.assertEqual("violet", resolved["palette"])
        self.assertEqual(garden.PRESETS["calm"]["speed"], resolved["speed"])


if __name__ == '__main__':
    unittest.main()
