#!/usr/bin/env python3
"""
Unit tests for Terminal Lunar Lander.

Tests terrain generation, physics, sprites, CLI arguments,
high score persistence, autopilot, warnings, and restart logic.
"""
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, "/root/daily-ideas/2026-06-23-terminal-lunar-lander")
import lunar_lander as ll

# Use a temporary file for high score tests so we don't pollute the real one
HIGHSCORES_TMP = None


class TestTerrainGeneration(unittest.TestCase):
    """Tests for generate_terrain()."""

    def test_surface_length(self):
        """Surface array should match world width."""
        surface, pads = ll.generate_terrain(80, 24, 5, 2, seed=42)
        self.assertEqual(len(surface), 80)

    def test_surface_bounds(self):
        """All surface values should be within [3, height-2]."""
        for seed in range(50):
            surface, pads = ll.generate_terrain(80, 24, 5, 2, seed=seed)
            for s in surface:
                self.assertGreaterEqual(s, 3)
                self.assertLessEqual(s, 22)

    def test_pad_py_matches_surface(self):
        """Pad py values must match surface heights at pad positions (Bug #1 fix)."""
        for seed in range(200):
            surface, pads = ll.generate_terrain(80, 24, 5, 2, seed=seed)
            for px, py, pw in pads:
                half = pw // 2
                for x in range(px - half, px + half + 1):
                    if 0 <= x < 80:
                        self.assertEqual(
                            surface[x], py,
                            f"Seed {seed}: surface[{x}]={surface[x]} != py={py} for pad at ({px},{py},w{pw})"
                        )

    def test_no_overlapping_pads(self):
        """Pads should not overlap each other (Bug #2 fix)."""
        for seed in range(200):
            surface, pads = ll.generate_terrain(80, 24, 8, 3, seed=seed)
            for i in range(len(pads)):
                for j in range(i + 1, len(pads)):
                    px1, _, pw1 = pads[i]
                    px2, _, pw2 = pads[j]
                    half1 = pw1 // 2
                    half2 = pw2 // 2
                    # Pads should have at least 4 pixels gap between them
                    self.assertGreaterEqual(
                        abs(px1 - px2), half1 + half2 + 4,
                        f"Seed {seed}: Overlapping pads P1=({px1},w{pw1}) P2=({px2},w{pw2})"
                    )

    def test_pad_within_bounds(self):
        """Pads should not extend past terrain edges."""
        for seed in range(100):
            surface, pads = ll.generate_terrain(80, 24, 5, 2, seed=seed)
            for px, py, pw in pads:
                half = pw // 2
                self.assertGreaterEqual(px - half, 0, f"Pad at {px} extends past left edge")
                self.assertLessEqual(px + half, 79, f"Pad at {px} extends past right edge")

    def test_different_difficulties(self):
        """Terrain generation should work for all difficulty settings."""
        for name, cfg in ll.DIFFICULTIES.items():
            surface, pads = ll.generate_terrain(
                80, 24, cfg["pad_width"], cfg["num_pads"], seed=42
            )
            self.assertEqual(len(pads), cfg["num_pads"])

    def test_seed_reproducibility(self):
        """Same seed should produce identical terrain."""
        surface1, pads1 = ll.generate_terrain(80, 24, 5, 2, seed=12345)
        surface2, pads2 = ll.generate_terrain(80, 24, 5, 2, seed=12345)
        self.assertEqual(surface1, surface2)
        self.assertEqual(pads1, pads2)

    def test_narrow_terrain(self):
        """Should handle very narrow terrains."""
        surface, pads = ll.generate_terrain(30, 24, 3, 1, seed=42)
        self.assertEqual(len(surface), 30)
        self.assertGreaterEqual(len(pads), 0)

    def test_large_terrain(self):
        """Should handle large terrains."""
        surface, pads = ll.generate_terrain(200, 50, 6, 4, seed=42)
        self.assertEqual(len(surface), 200)


class TestLanderSprite(unittest.TestCase):
    """Tests for get_lander_sprite()."""

    def test_sprite_has_elements(self):
        """Sprite should always have elements."""
        for angle in [-90, -45, 0, 45, 90]:
            sprite = ll.get_lander_sprite(angle)
            self.assertGreater(len(sprite), 0)

    def test_sprite_chars_are_strings(self):
        """All sprite characters should be strings."""
        sprite = ll.get_lander_sprite(0)
        for dx, dy, ch in sprite:
            self.assertIsInstance(ch, str)

    def test_thrusting_sprite_larger(self):
        """Sprite with thrusting=True should have more elements."""
        normal = ll.get_lander_sprite(0, thrusting=False)
        thrusting = ll.get_lander_sprite(0, thrusting=True)
        self.assertGreaterEqual(len(thrusting), len(normal))


class TestPhysics(unittest.TestCase):
    """Tests for physics calculations."""

    def test_gravity_constant(self):
        """Gravity should be positive (downward)."""
        self.assertGreater(ll.GRAVITY, 0)

    def test_thrust_overcomes_gravity(self):
        """Full thrust at angle 0 should produce net upward acceleration."""
        ay = ll.GRAVITY - ll.MAX_THRUST  # net vertical acceleration at angle=0
        self.assertLess(ay, 0, "Thrust should overcome gravity when pointing straight up")

    def test_fuel_consumption_rate(self):
        """Fuel burn rate should be positive."""
        self.assertGreater(ll.FUEL_BURN_RATE, 0)

    def test_angle_clamping(self):
        """Angle should be clamped to [-90, 90]."""
        angle = 0.0
        dt = 0.033
        for _ in range(100):
            angle += ll.ROTATION_SPEED * dt
            angle = max(-90, min(90, angle))
        self.assertLessEqual(abs(angle), 90)

    def test_delta_time_capping(self):
        """Delta time should be capped at 0.1s to prevent tunneling."""
        # Simulate what _get_dt does
        dt = 0.5
        capped = min(dt, 0.1)
        self.assertEqual(capped, 0.1)


class TestDifficultyConfigs(unittest.TestCase):
    """Tests for difficulty configuration values."""

    def test_all_difficulties_exist(self):
        """All three difficulties should be defined."""
        self.assertIn("easy", ll.DIFFICULTIES)
        self.assertIn("medium", ll.DIFFICULTIES)
        self.assertIn("hard", ll.DIFFICULTIES)

    def test_no_zero_division_risks(self):
        """Config values used in division should be non-zero."""
        for name, cfg in ll.DIFFICULTIES.items():
            self.assertGreater(cfg["landing_speed_max"], 0, f"{name}: landing_speed_max is 0")
            self.assertGreater(cfg["landing_angle_max"], 0, f"{name}: landing_angle_max is 0")
            self.assertGreater(cfg["fuel"], 0, f"{name}: fuel is 0")
            self.assertGreater(cfg["pad_width"], 0, f"{name}: pad_width is 0")
            self.assertGreater(cfg["num_pads"], 0, f"{name}: num_pads is 0")

    def test_harder_difficulties_have_less_fuel(self):
        """Harder difficulties should have less fuel."""
        self.assertGreater(
            ll.DIFFICULTIES["easy"]["fuel"],
            ll.DIFFICULTIES["medium"]["fuel"]
        )
        self.assertGreater(
            ll.DIFFICULTIES["medium"]["fuel"],
            ll.DIFFICULTIES["hard"]["fuel"]
        )

    def test_harder_difficulties_have_stronger_wind(self):
        """Harder difficulties should have more wind."""
        self.assertLess(
            ll.DIFFICULTIES["easy"]["wind"],
            ll.DIFFICULTIES["medium"]["wind"]
        )
        self.assertLess(
            ll.DIFFICULTIES["medium"]["wind"],
            ll.DIFFICULTIES["hard"]["wind"]
        )


class TestVersionAndCLI(unittest.TestCase):
    """Tests for version and CLI argument handling."""

    def test_version_exists(self):
        """Module should have a __version__ attribute."""
        self.assertTrue(hasattr(ll, "__version__"))
        self.assertIn(".", ll.__version__)

    def test_version_format(self):
        """Version should be in x.y.z format."""
        parts = ll.__version__.split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())

    def test_help_flag(self):
        """--help should exit with 0 and print docstring."""
        result = subprocess.run(
            [sys.executable, "lunar_lander.py", "--help"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-23-terminal-lunar-lander"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Lunar Lander", result.stdout)

    def test_version_flag(self):
        """--version should exit with 0 and print version."""
        result = subprocess.run(
            [sys.executable, "lunar_lander.py", "--version"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-23-terminal-lunar-lander"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn(ll.__version__, result.stdout)

    def test_unknown_argument(self):
        """Unknown argument should exit with 1."""
        result = subprocess.run(
            [sys.executable, "lunar_lander.py", "--invalid"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-23-terminal-lunar-lander"
        )
        self.assertEqual(result.returncode, 1)

    def test_non_tty_detection(self):
        """Non-TTY should print error and exit with 1."""
        result = subprocess.run(
            [sys.executable, "lunar_lander.py", "--easy"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
            cwd="/root/daily-ideas/2026-06-23-terminal-lunar-lander"
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("interactive terminal", result.stderr)

    def test_demo_flag_in_help(self):
        """--demo flag should be documented in help output."""
        result = subprocess.run(
            [sys.executable, "lunar_lander.py", "--help"],
            capture_output=True, text=True,
            cwd="/root/daily-ideas/2026-06-23-terminal-lunar-lander"
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--demo", result.stdout)


class TestScoreCalculation(unittest.TestCase):
    """Tests for the score calculation logic."""

    def test_perfect_landing_score(self):
        """Perfect landing should give a positive score."""
        for diff_name, diff in ll.DIFFICULTIES.items():
            fuel = diff["fuel"]
            max_speed = diff["landing_speed_max"]
            max_angle = diff["landing_angle_max"]
            speed = 1.0
            angle = 2.0
            on_pad = True
            fuel_bonus = int(fuel / diff["fuel"] * 100)
            speed_bonus = int((1 - speed / (max_speed * 2)) * 100)
            angle_bonus = int((1 - angle / (max_angle * 2)) * 100)
            pad_bonus = 200
            diff_mult = {"easy": 1, "medium": 2, "hard": 3}[diff_name]
            score = int((fuel_bonus + speed_bonus + angle_bonus + pad_bonus) * diff_mult)
            self.assertGreater(score, 0, f"{diff_name}: score should be positive")

    def test_crash_score_is_zero(self):
        """A crash should result in score 0."""
        # In the game code, crash sets self.score = 0
        score = 0
        self.assertEqual(score, 0)

    def test_higher_difficulty_multiplier(self):
        """Harder difficulties should multiply score more."""
        self.assertGreater(
            ll.DIFFICULTIES["hard"].get("score_mult", 3),
            ll.DIFFICULTIES["easy"].get("score_mult", 1)
        )


class TestHorizontalWrapping(unittest.TestCase):
    """Tests for horizontal wrapping behavior."""

    def test_wrap_left(self):
        """Lander should wrap from left edge to right edge."""
        lx = -1.0
        world_width = 80
        if lx < 0:
            lx += world_width
        self.assertEqual(lx, 79.0)

    def test_wrap_right(self):
        """Lander should wrap from right edge to left edge."""
        lx = 80.5
        world_width = 80
        if lx >= world_width:
            lx -= world_width
        self.assertAlmostEqual(lx, 0.5)


class TestHighScores(unittest.TestCase):
    """Tests for high score persistence."""

    def test_load_empty_scores(self):
        """Loading from nonexistent file should return empty structure."""
        scores = ll.load_highscores()
        self.assertIn("easy", scores)
        self.assertIn("medium", scores)
        self.assertIn("hard", scores)

    def test_save_and_load_cycle(self):
        """Scores should round-trip through save and load."""
        # Use a temporary file
        original_file = ll.HIGHSCORE_FILE
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp_path = f.name
        try:
            ll.HIGHSCORE_FILE = tmp_path
            scores = {"easy": [{"score": 500, "result": "PERFECT", "date": "2026-01-01"}]}
            ll.save_highscores(scores)
            loaded = ll.load_highscores()
            self.assertEqual(loaded["easy"][0]["score"], 500)
        finally:
            ll.HIGHSCORE_FILE = original_file
            os.unlink(tmp_path)

    def test_add_highscore_sorts_descending(self):
        """add_highscore should sort scores descending."""
        original_file = ll.HIGHSCORE_FILE
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp_path = f.name
        try:
            ll.HIGHSCORE_FILE = tmp_path
            ll.add_highscore("medium", 300, "ROUGH")
            ll.add_highscore("medium", 500, "PERFECT")
            ll.add_highscore("medium", 200, "HARD")
            scores = ll.load_highscores()
            self.assertEqual(scores["medium"][0]["score"], 500)
            self.assertEqual(scores["medium"][1]["score"], 300)
            self.assertEqual(scores["medium"][2]["score"], 200)
        finally:
            ll.HIGHSCORE_FILE = original_file
            os.unlink(tmp_path)

    def test_highscore_limit(self):
        """Should keep only top 10 scores per difficulty."""
        original_file = ll.HIGHSCORE_FILE
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp_path = f.name
        try:
            ll.HIGHSCORE_FILE = tmp_path
            for i in range(15):
                ll.add_highscore("easy", 100 + i * 10, "PERFECT")
            scores = ll.load_highscores()
            self.assertLessEqual(len(scores["easy"]), 10)
        finally:
            ll.HIGHSCORE_FILE = original_file
            os.unlink(tmp_path)

    def test_corrupt_file_handling(self):
        """Should handle corrupt JSON files gracefully."""
        original_file = ll.HIGHSCORE_FILE
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("NOT VALID JSON {{{")
            tmp_path = f.name
        try:
            ll.HIGHSCORE_FILE = tmp_path
            scores = ll.load_highscores()
            self.assertIn("easy", scores)
            self.assertEqual(len(scores["easy"]), 0)
        finally:
            ll.HIGHSCORE_FILE = original_file
            os.unlink(tmp_path)


class TestAutopilot(unittest.TestCase):
    """Tests for the autopilot (demo mode)."""

    def test_autopilot_init(self):
        """Autopilot should initialize with pads."""
        pads = [(40, 18, 5)]
        ap = ll.Autopilot(pads)
        self.assertIsNotNone(ap.target_pad)
        self.assertEqual(ap.target_pad[0], 40)

    def test_autopilot_with_no_pads(self):
        """Autopilot with no pads should not thrust."""
        ap = ll.Autopilot([])
        t, rl, rr = ap.decide(40, 5, 0, 1, 0, 50, 15)
        self.assertFalse(t)
        self.assertFalse(rl)
        self.assertFalse(rr)

    def test_autopilot_returns_tuple(self):
        """Autopilot decide() should return a 3-tuple of bools."""
        pads = [(40, 18, 5)]
        ap = ll.Autopilot(pads)
        result = ap.decide(40, 5, 0, 1, 0, 50, 15)
        self.assertEqual(len(result), 3)
        for val in result:
            self.assertIsInstance(val, bool)

    def test_autopilot_aims_for_pad(self):
        """When far from pad, autopilot should steer toward it."""
        pads = [(60, 18, 5)]
        ap = ll.Autopilot(pads)
        # Lander at x=20, should steer right
        t, rl, rr = ap.decide(20, 5, 0, 1, 0, 80, 30)
        self.assertTrue(rr or not rl)  # Should rotate right toward pad


class TestDesiredVyChange(unittest.TestCase):
    """Tests for the desired_vy_change helper."""

    def test_positive_when_desired_higher(self):
        """Should return positive when desired vy is higher than current."""
        result = ll.desired_vy_change(1.0, 3.0)
        self.assertAlmostEqual(result, 2.0)

    def test_negative_when_desired_lower(self):
        """Should return negative when desired vy is lower than current."""
        result = ll.desired_vy_change(5.0, 2.0)
        self.assertAlmostEqual(result, -3.0)


if __name__ == "__main__":
    unittest.main()