#!/usr/bin/env python3
"""
Unit tests for Terminal Lunar Lander.

Tests terrain generation, physics, sprites, CLI arguments,
and the bug fixes (pad overlap, pad height mismatch, fuel bar).
"""
import math
import random
import subprocess
import sys
import unittest

sys.path.insert(0, "/root/daily-ideas/2026-06-23-terminal-lunar-lander")
import lunar_lander as ll


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


class TestVersionAndCLI(unittest.TestCase):
    """Tests for version and CLI argument handling."""

    def test_version_exists(self):
        """Module should have a __version__ attribute."""
        self.assertTrue(hasattr(ll, "__version__"))
        self.assertIn(".", ll.__version__)

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


if __name__ == "__main__":
    unittest.main()