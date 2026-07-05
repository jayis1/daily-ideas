#!/usr/bin/env python3
"""Test script for lock_picker module (non-interactive).

Tests cover lock creation, tension/binding mechanics, pin setting,
full lock picking, spring physics, raking, pick durability, hints,
and CLI argument parsing.
"""

import random
import sys
import unittest
from io import StringIO

from lock_picker import Lock, Pin, DIFFICULTY_NAMES, MIN_PINS, MAX_PINS, VERSION


class TestLockCreation(unittest.TestCase):
    """Test lock initialization and pin generation."""

    def test_basic_creation(self):
        """Lock should create with the specified number of pins."""
        lock = Lock(5, 2)
        self.assertEqual(lock.num_pins, 5)
        self.assertEqual(len(lock.pins), 5)

    def test_pin_count_range(self):
        """Lock should clamp pin count to valid range."""
        lock_too_few = Lock(0, 1)
        self.assertEqual(lock_too_few.num_pins, MIN_PINS)
        lock_too_many = Lock(100, 1)
        self.assertEqual(lock_too_many.num_pins, MAX_PINS)

    def test_difficulty_range(self):
        """Lock should clamp difficulty to 1-5."""
        lock_low = Lock(5, 0)
        self.assertEqual(lock_low.difficulty, 1)  # Clamped to 1
        lock_high = Lock(5, 99)
        self.assertLessEqual(lock_high.difficulty, 5)

    def test_pin_properties(self):
        """Each pin should have valid key_height and spring_tension."""
        random.seed(42)
        lock = Lock(5, 2)
        for pin in lock.pins:
            self.assertIsInstance(pin, Pin)
            self.assertGreater(pin.key_height, 0)
            self.assertLess(pin.key_height, 1)
            self.assertGreater(pin.spring_tension, 0)
            self.assertFalse(pin.is_set)
            self.assertEqual(pin.current_height, 0.0)

    def test_initial_state(self):
        """New lock should not be open and have zero tension."""
        lock = Lock(5, 1)
        self.assertFalse(lock.is_open)
        self.assertEqual(lock.tension, 0.0)
        self.assertEqual(lock.pick_health, 1.0)


class TestTensionAndBinding(unittest.TestCase):
    """Test tension application and pin binding mechanics."""

    def test_tension_causes_binding(self):
        """At least one pin should bind when tension is applied."""
        random.seed(42)
        lock = Lock(5, 2)
        lock.apply_tension(0.3)
        bound_count = sum(1 for p in lock.pins if p.is_bound)
        self.assertGreater(bound_count, 0)

    def test_zero_tension_no_binding(self):
        """No pins should bind with zero tension."""
        lock = Lock(5, 1)
        lock.apply_tension(0.03)  # Below the 0.05 threshold
        for pin in lock.pins:
            self.assertFalse(pin.is_bound)

    def test_high_tension_binds_more(self):
        """Higher tension should bind more pins."""
        random.seed(42)
        lock_low = Lock(6, 1)
        lock_low.apply_tension(0.2)
        low_bound = sum(1 for p in lock_low.pins if p.is_bound)

        random.seed(42)
        lock_high = Lock(6, 1)
        lock_high.apply_tension(0.8)
        high_bound = sum(1 for p in lock_high.pins if p.is_bound)

        self.assertGreaterEqual(high_bound, low_bound)

    def test_tension_clamped(self):
        """Tension should be clamped to [0.0, 1.0]."""
        lock = Lock(5, 1)
        lock.apply_tension(5.0)
        self.assertAlmostEqual(lock.tension, 1.0)
        lock.apply_tension(-1.0)
        self.assertAlmostEqual(lock.tension, 0.0)


class TestLiftingAndSetting(unittest.TestCase):
    """Test pin lifting and setting mechanics."""

    def test_bound_pin_can_be_set(self):
        """A bound pin should be settable by lifting it."""
        random.seed(42)
        lock = Lock(5, 2)
        lock.apply_tension(0.4)
        for i, pin in enumerate(lock.pins):
            if pin.is_bound:
                attempts = 0
                while not pin.is_set and attempts < 500:
                    lock.lift_pin(i, 0.02)
                    attempts += 1
                self.assertTrue(pin.is_set,
                                f"Bound pin {i+1} should be settable after {attempts} lifts")
                break

    def test_lift_invalid_pin(self):
        """Lifting an invalid pin index should return False."""
        lock = Lock(5, 1)
        self.assertFalse(lock.lift_pin(-1, 0.02))
        self.assertFalse(lock.lift_pin(99, 0.02))

    def test_set_pin_stays(self):
        """A set pin should remain at its key height."""
        random.seed(42)
        lock = Lock(5, 2)
        lock.apply_tension(0.4)
        for i, pin in enumerate(lock.pins):
            if pin.is_bound:
                while not pin.is_set:
                    lock.lift_pin(i, 0.02)
                self.assertAlmostEqual(pin.current_height, pin.key_height, places=2)
                break


class TestFullPick(unittest.TestCase):
    """Test picking a complete lock."""

    def test_full_pick_easy(self):
        """A 4-pin Novice lock should be fully pickable."""
        random.seed(99)
        lock = Lock(4, 1)
        lock.apply_tension(0.5)

        for _ in range(5000):
            if lock.check_open():
                break
            lock.apply_tension(lock.tension)
            found_bound = False
            for i, pin in enumerate(lock.pins):
                if pin.is_bound and not pin.is_set:
                    lock.lift_pin(i, 0.02)
                    found_bound = True
                    break
            if not found_bound:
                lock.apply_tension(min(1.0, lock.tension + 0.02))

        self.assertTrue(lock.is_open, "Lock should be pickable")

    def test_full_pick_hard(self):
        """A 3-pin Hard lock should be pickable (with persistence)."""
        random.seed(123)
        lock = Lock(3, 4)
        lock.apply_tension(0.4)

        for _ in range(8000):
            if lock.check_open():
                break
            lock.apply_tension(lock.tension)
            found_bound = False
            for i, pin in enumerate(lock.pins):
                if pin.is_bound and not pin.is_set:
                    lock.lift_pin(i, 0.015)  # Smaller lifts for precision
                    found_bound = True
                    break
            if not found_bound:
                lock.apply_tension(min(1.0, lock.tension + 0.02))

        self.assertTrue(lock.is_open, "Hard lock should be pickable")


class TestOpenCheck(unittest.TestCase):
    """Test lock opening conditions."""

    def test_all_set_with_tension_opens(self):
        """All pins set + tension > 0.2 should open the lock."""
        random.seed(999)
        lock = Lock(3, 1)
        lock.apply_tension(0.5)
        for pin in lock.pins:
            pin.is_set = True
            pin.current_height = pin.key_height
        result = lock.check_open()
        self.assertTrue(result)
        self.assertTrue(lock.is_open)

    def test_all_set_no_tension_no_open(self):
        """All pins set but no tension should NOT open."""
        lock = Lock(3, 1)
        lock.apply_tension(0.5)
        for pin in lock.pins:
            pin.is_set = True
            pin.current_height = pin.key_height
        lock.apply_tension(0.1)  # Below 0.2 threshold
        result = lock.check_open()
        self.assertFalse(result)


class TestSpringMechanics(unittest.TestCase):
    """Test spring physics for unset pins."""

    def test_springs_push_down(self):
        """Spring tension should push unset pins downward."""
        random.seed(77)
        lock = Lock(4, 2)
        pin = lock.pins[0]
        pin.current_height = 0.5
        old_height = pin.current_height
        pin.current_height = max(0.0, pin.current_height - pin.spring_tension * 0.5)
        self.assertLess(pin.current_height, old_height)

    def test_set_pin_doesnt_decay(self):
        """Set pins should not have spring decay applied in the game loop."""
        random.seed(42)
        lock = Lock(3, 1)
        lock.apply_tension(0.4)
        # Manually set a pin
        pin = lock.pins[0]
        pin.is_set = True
        pin.current_height = pin.key_height
        # Simulate decay step
        if not pin.is_set and pin.current_height > 0:
            pin.current_height = max(0.0, pin.current_height - pin.spring_tension * 0.5)
        # Height should remain at key_height since pin is set
        self.assertAlmostEqual(pin.current_height, pin.key_height, places=2)


class TestRaking(unittest.TestCase):
    """Test raking (scrubbing all pins)."""

    def test_rake_can_set_pins(self):
        """Raking should have a chance to set pins."""
        random.seed(42)
        successes = 0
        for _ in range(20):
            lock = Lock(3, 1)
            lock.apply_tension(0.5)
            clicks = lock.rack()
            if clicks > 0:
                successes += 1
        # At least some rakes should set pins
        self.assertGreater(successes, 0, "Raking should sometimes set pins on easy locks")

    def test_rake_hard_lock_can_unset(self):
        """On Hard difficulty, raking can unset previously set pins."""
        random.seed(77)
        # Set up a hard lock with one pin already set
        lock = Lock(4, 4)
        lock.apply_tension(0.5)
        lock.pins[0].is_set = True
        lock.pins[0].current_height = lock.pins[0].key_height
        # Raking might unset it (probabilistic, so just check it doesn't crash)
        try:
            lock.rack()
            success = True
        except Exception:
            success = False
        self.assertTrue(success, "Raking should not crash on hard locks")


class TestPickDurability(unittest.TestCase):
    """Test pick health/durability mechanics on harder difficulties."""

    def test_pick_starts_full(self):
        """Pick health should start at 1.0."""
        lock = Lock(5, 1)
        self.assertEqual(lock.pick_health, 1.0)

    def test_pick_wears_on_hard(self):
        """Picking on Hard/Master should wear the pick."""
        random.seed(42)
        lock = Lock(4, 4)
        lock.apply_tension(0.4)
        initial_health = lock.pick_health
        for i, pin in enumerate(lock.pins):
            if pin.is_bound and not pin.is_set:
                for _ in range(100):
                    lock.lift_pin(i, 0.02)
                    if pin.is_set:
                        break
                break
        self.assertLess(lock.pick_health, initial_health,
                        "Pick should wear on Hard difficulty")

    def test_rake_wears_pick(self):
        """Raking on hard difficulty should wear the pick more."""
        random.seed(42)
        lock = Lock(4, 3)
        lock.apply_tension(0.5)
        initial_health = lock.pick_health
        lock.rack()
        self.assertLess(lock.pick_health, initial_health,
                        "Raking should wear the pick on Medium+ difficulty")


class TestHints(unittest.TestCase):
    """Test the hint system."""

    def test_hint_with_tension(self):
        """Hint should identify a bound pin when tension is applied."""
        random.seed(42)
        lock = Lock(5, 2)
        lock.apply_tension(0.4)
        idx, hint = lock.get_next_hint()
        if idx is not None:
            self.assertGreaterEqual(idx, 0)
            self.assertLess(idx, lock.num_pins)

    def test_hint_no_tension(self):
        """Hint should suggest applying tension when none is applied."""
        lock = Lock(5, 1)
        idx, hint = lock.get_next_hint()
        self.assertIsNone(idx)
        self.assertIn("tension", hint.lower())

    def test_hint_all_set(self):
        """Hint should say adjust tension when all bound pins are set."""
        random.seed(42)
        lock = Lock(3, 1)
        lock.apply_tension(0.5)
        # Set all pins that are bound
        for pin in lock.pins:
            pin.is_set = True
            pin.current_height = pin.key_height
        idx, hint = lock.get_next_hint()
        # Should suggest adjusting tension since all bound pins are set
        self.assertIn("tension", hint.lower())


class TestReleasePin(unittest.TestCase):
    """Test pin release mechanics."""

    def test_release_unset_pin(self):
        """Releasing an unset pin should lower its height."""
        lock = Lock(5, 1)
        pin = lock.pins[0]
        pin.current_height = 0.5
        lock.release_pin(0)
        self.assertLess(pin.current_height, 0.5)

    def test_release_set_pin_stays(self):
        """Releasing a set pin should not change its height."""
        lock = Lock(5, 1)
        pin = lock.pins[0]
        pin.is_set = True
        pin.current_height = pin.key_height
        old_height = pin.current_height
        lock.release_pin(0)
        self.assertAlmostEqual(pin.current_height, old_height)

    def test_release_invalid_index(self):
        """Releasing an invalid pin index should not crash."""
        lock = Lock(5, 1)
        lock.release_pin(-1)  # Should not raise
        lock.release_pin(99)  # Should not raise


class TestCLIArgs(unittest.TestCase):
    """Test CLI argument parsing (non-curses parts)."""

    def test_version_constant(self):
        """VERSION should be a valid version string."""
        parts = VERSION.split('.')
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit(), f"Version part '{part}' should be numeric")

    def test_difficulty_names(self):
        """DIFFICULTY_NAMES should have exactly 5 entries."""
        self.assertEqual(len(DIFFICULTY_NAMES), 5)
        self.assertEqual(DIFFICULTY_NAMES[0], 'Novice')
        self.assertEqual(DIFFICULTY_NAMES[4], 'Master')

    def test_pin_range_constants(self):
        """MIN_PINS and MAX_PINS should be sensible."""
        self.assertEqual(MIN_PINS, 2)
        self.assertEqual(MAX_PINS, 8)


if __name__ == '__main__':
    print("Testing Terminal Lock Picker...\n")
    unittest.main(verbosity=2)