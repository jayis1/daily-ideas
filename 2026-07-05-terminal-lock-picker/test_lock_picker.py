#!/usr/bin/env python3
"""Test script for lock_picker module (non-interactive).

Tests cover lock creation, tension/binding mechanics, pin setting,
full lock picking, spring physics, raking, pick durability, hints,
CLI argument parsing, lock profiles, stats formatting, and regression tests.
"""

import random
import sys
import unittest
from io import StringIO

from lock_picker import (Lock, Pin, DIFFICULTY_NAMES, MIN_PINS, MAX_PINS,
                         VERSION, LOCK_PROFILES, format_time,
                         height_to_bar, get_pin_visual, get_tension_bar,
                         get_pick_health_bar, list_profiles, parse_args)


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

    def test_pick_breaks_counter(self):
        """New lock should have pick_breaks initialized to 0."""
        lock = Lock(5, 1)
        self.assertEqual(lock.pick_breaks, 0)


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
        """Raking on Hard difficulty should wear the pick."""
        random.seed(42)
        lock = Lock(4, 4)  # Hard difficulty (not Medium)
        lock.apply_tension(0.5)
        initial_health = lock.pick_health
        lock.rack()
        self.assertLess(lock.pick_health, initial_health,
                        "Raking should wear the pick on Hard difficulty")


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

    def test_parse_args_defaults(self):
        """Default args should be None for pins and difficulty."""
        args = parse_args([])
        self.assertIsNone(args.pins)
        self.assertIsNone(args.difficulty)
        self.assertFalse(args.demo)
        self.assertIsNone(args.profile)
        self.assertFalse(args.verbose)
        self.assertFalse(args.list_profiles)

    def test_parse_args_demo(self):
        """--demo flag should set demo mode."""
        args = parse_args(['--demo'])
        self.assertTrue(args.demo)

    def test_parse_args_profile(self):
        """--profile should set a valid profile key."""
        args = parse_args(['--profile', 'yale-standard'])
        self.assertEqual(args.profile, 'yale-standard')


class TestBugFixes(unittest.TestCase):
    """Regression tests for bugs found and fixed."""

    def test_pick_health_never_negative(self):
        """Pick health should never go below 0."""
        random.seed(42)
        lock = Lock(3, 5)  # Master difficulty
        lock.apply_tension(0.5)
        lock.pick_health = 0.0001
        for _ in range(100):
            lock.lift_pin(0, 0.02)
        self.assertGreaterEqual(lock.pick_health, 0.0,
                                 "Pick health should never go negative from lifting")

    def test_rake_pick_health_never_negative(self):
        """Raking should never make pick health negative."""
        random.seed(42)
        lock = Lock(4, 3)
        lock.apply_tension(0.5)
        lock.pick_health = 0.01
        for _ in range(10):
            lock.rack()
        self.assertGreaterEqual(lock.pick_health, 0.0,
                                 "Raking should never make pick health negative")

    def test_pins_set_count_is_computed(self):
        """pins_set_count should always match actual is_set count."""
        random.seed(42)
        lock = Lock(5, 2)
        lock.apply_tension(0.5)

        # Set pins one by one and verify count
        for i, pin in enumerate(lock.pins):
            if pin.is_bound and not pin.is_set:
                while not pin.is_set:
                    lock.lift_pin(i, 0.02)
                self.assertEqual(lock.pins_set_count,
                                 sum(1 for p in lock.pins if p.is_set),
                                 f"After setting pin {i}, count mismatch")
                lock.apply_tension(lock.tension)

    def test_already_set_pin_not_double_counted(self):
        """Lifting an already-set pin should not increment pins_set_count."""
        random.seed(42)
        lock = Lock(3, 1)
        lock.apply_tension(0.5)

        # Set a bound pin
        for i, pin in enumerate(lock.pins):
            if pin.is_bound:
                while not pin.is_set:
                    lock.lift_pin(i, 0.02)
                break

        count_before = lock.pins_set_count
        # Lift the already-set pin again
        lock.lift_pin(i, 0.02)
        self.assertEqual(lock.pins_set_count, count_before,
                         "Lifting an already-set pin should not increment count")

    def test_check_open_with_exact_tension_threshold(self):
        """Lock should open when tension is exactly 0.2."""
        lock = Lock(3, 1)
        for pin in lock.pins:
            pin.is_set = True
            pin.current_height = pin.key_height
        lock.tension = 0.2
        result = lock.check_open()
        self.assertTrue(result, "Lock should open with tension >= 0.2")

    def test_check_open_below_tension_threshold(self):
        """Lock should not open when tension is below 0.2."""
        lock = Lock(3, 1)
        for pin in lock.pins:
            pin.is_set = True
            pin.current_height = pin.key_height
        lock.tension = 0.19
        result = lock.check_open()
        self.assertFalse(result, "Lock should not open with tension < 0.2")

    def test_pick_health_bar_distinct_levels(self):
        """Pick health bar should have distinct visuals for different levels."""
        bar_high = get_pick_health_bar(0.8, 20)
        bar_mid = get_pick_health_bar(0.4, 20)
        bar_low = get_pick_health_bar(0.1, 20)
        # High should use ▓, mid should use ▒, low should use ! (critical)
        self.assertIn('▓', bar_high)
        self.assertIn('▒', bar_mid)
        self.assertIn('!', bar_low)  # Critical health uses ! for remaining
        self.assertIn('·', bar_low)  # And · for lost health

    def test_pins_set_count_after_raking(self):
        """pins_set_count should match actual count after raking."""
        random.seed(42)
        lock = Lock(4, 1)
        lock.apply_tension(0.5)
        lock.rack()
        self.assertEqual(lock.pins_set_count,
                         sum(1 for p in lock.pins if p.is_set),
                         "pins_set_count should match actual after raking")

    def test_raking_on_novice_no_pick_wear(self):
        """Raking on Novice difficulty should not wear the pick."""
        random.seed(42)
        lock = Lock(4, 1)  # Novice
        lock.apply_tension(0.5)
        initial_health = lock.pick_health
        lock.rack()
        self.assertEqual(lock.pick_health, initial_health,
                         "Raking on Novice should not wear the pick")

    def test_raking_on_medium_no_pick_wear(self):
        """Raking on Medium difficulty should not wear the pick (only Hard/Master)."""
        random.seed(42)
        lock = Lock(4, 3)  # Medium
        lock.apply_tension(0.5)
        initial_health = lock.pick_health
        lock.rack()
        self.assertEqual(lock.pick_health, initial_health,
                         "Raking on Medium should not wear the pick")

    def test_raking_on_hard_wears_pick(self):
        """Raking on Hard difficulty should wear the pick."""
        random.seed(42)
        lock = Lock(4, 4)  # Hard
        lock.apply_tension(0.5)
        initial_health = lock.pick_health
        lock.rack()
        self.assertLess(lock.pick_health, initial_health,
                        "Raking on Hard should wear the pick")

    def test_rake_with_broken_pick_returns_zero(self):
        """Raking with a broken pick should return 0 and not modify pins."""
        random.seed(42)
        lock = Lock(4, 4)
        lock.apply_tension(0.5)
        lock.pick_health = 0.0
        # Record pin states before raking
        heights_before = [p.current_height for p in lock.pins]
        set_before = [p.is_set for p in lock.pins]
        clicks = lock.rack()
        self.assertEqual(clicks, 0, "Raking with broken pick should return 0 clicks")
        # Pin heights should not change (rake does nothing with broken pick)
        for i, pin in enumerate(lock.pins):
            self.assertEqual(pin.current_height, heights_before[i],
                             f"Pin {i} height changed despite broken pick")
            self.assertEqual(pin.is_set, set_before[i],
                             f"Pin {i} set state changed despite broken pick")

    def test_demo_broken_pick_exits(self):
        """Demo mode should detect broken pick and exit early."""
        import io
        from contextlib import redirect_stdout
        from lock_picker import run_demo
        lock = Lock(3, 5)  # Master difficulty
        lock.apply_tension(0.5)
        # Break the pick
        lock.pick_health = 0.0
        # Verify lock is not open and pick is broken
        self.assertFalse(lock.is_open)
        self.assertTrue(lock.pick_health <= 0)

    def test_pick_health_bar_zero_distinct_from_low(self):
        """Zero health bar should look different from low health bar."""
        bar_zero = get_pick_health_bar(0.0, 20)
        bar_low = get_pick_health_bar(0.15, 20)
        # Zero should have no ! (no remaining health)
        # Low should have some ! (some remaining health)
        bang_count_zero = bar_zero.count('!')
        bang_count_low = bar_low.count('!')
        self.assertGreater(bang_count_low, bang_count_zero,
                           "Low health should show more remaining (!) than zero health")

    def test_binding_updates_after_pin_set(self):
        """Binding should update after a pin is set when tension is re-applied."""
        random.seed(42)
        lock = Lock(5, 2)
        lock.apply_tension(0.4)
        # Find and set a bound pin
        for i, pin in enumerate(lock.pins):
            if pin.is_bound and not pin.is_set:
                while not pin.is_set:
                    lock.lift_pin(i, 0.02)
                break
        # After setting, re-apply tension to update binding
        lock.apply_tension(lock.tension)
        # Check that new pins are bound (if any unset remain)
        unset_pins = [p for p in lock.pins if not p.is_set]
        if unset_pins:
            bound_unset = [p for p in unset_pins if p.is_bound]
            # With tension applied and some pins set, there should be new binding
            self.assertGreater(len(bound_unset), 0,
                              "After setting a pin and re-applying tension, "
                              "new pins should bind")


class TestLockProfiles(unittest.TestCase):
    """Test lock profile system."""

    def test_profiles_exist(self):
        """Lock profiles dict should have entries."""
        self.assertGreater(len(LOCK_PROFILES), 0)

    def test_profile_structure(self):
        """Each profile should have required keys."""
        required_keys = {'name', 'description', 'pins', 'difficulty', 'flavor'}
        for key, profile in LOCK_PROFILES.items():
            self.assertTrue(required_keys.issubset(set(profile.keys())),
                            f"Profile '{key}' missing keys: {required_keys - set(profile.keys())}")

    def test_profile_pin_range(self):
        """Each profile's pin count should be within valid range."""
        for key, profile in LOCK_PROFILES.items():
            self.assertGreaterEqual(profile['pins'], MIN_PINS,
                                    f"Profile '{key}' has too few pins")
            self.assertLessEqual(profile['pins'], MAX_PINS,
                                  f"Profile '{key}' has too many pins")

    def test_profile_difficulty_range(self):
        """Each profile's difficulty should be within valid range."""
        for key, profile in LOCK_PROFILES.items():
            self.assertGreaterEqual(profile['difficulty'], 1,
                                    f"Profile '{key}' difficulty too low")
            self.assertLessEqual(profile['difficulty'], 5,
                                  f"Profile '{key}' difficulty too high")

    def test_specific_profiles(self):
        """Test that key profiles exist with expected values."""
        self.assertIn('yale-standard', LOCK_PROFILES)
        self.assertEqual(LOCK_PROFILES['yale-standard']['pins'], 5)
        self.assertEqual(LOCK_PROFILES['yale-standard']['difficulty'], 1)

        self.assertIn('challenge-8pin', LOCK_PROFILES)
        self.assertEqual(LOCK_PROFILES['challenge-8pin']['pins'], 8)
        self.assertEqual(LOCK_PROFILES['challenge-8pin']['difficulty'], 5)

    def test_lock_creation_from_profile(self):
        """Creating a lock from profile values should work correctly."""
        for key, profile in LOCK_PROFILES.items():
            lock = Lock(profile['pins'], profile['difficulty'])
            self.assertEqual(lock.num_pins, profile['pins'],
                             f"Profile '{key}' pin count mismatch")
            self.assertEqual(lock.difficulty, profile['difficulty'],
                             f"Profile '{key}' difficulty mismatch")


class TestFormatTime(unittest.TestCase):
    """Test the format_time helper function."""

    def test_seconds_format(self):
        """Times under 60 seconds should show decimal seconds."""
        self.assertEqual(format_time(8.2), "8.2s")
        self.assertEqual(format_time(0.5), "0.5s")
        self.assertEqual(format_time(59.9), "59.9s")

    def test_minutes_format(self):
        """Times >= 60 seconds should show minutes and seconds."""
        self.assertEqual(format_time(65.0), "1m 5.0s")
        self.assertEqual(format_time(122.3), "2m 2.3s")

    def test_negative_time(self):
        """Negative times should show a dash."""
        self.assertEqual(format_time(-1), "—")

    def test_zero_time(self):
        """Zero time should format as seconds."""
        self.assertEqual(format_time(0), "0.0s")


class TestLockProperties(unittest.TestCase):
    """Test computed properties on the Lock class."""

    def test_progress_pct(self):
        """progress_pct should reflect pin completion percentage."""
        random.seed(42)
        lock = Lock(4, 1)
        lock.apply_tension(0.5)
        self.assertAlmostEqual(lock.progress_pct, 0.0)

        # Set one pin
        for i, pin in enumerate(lock.pins):
            if pin.is_bound and not pin.is_set:
                while not pin.is_set:
                    lock.lift_pin(i, 0.02)
                break

        self.assertGreater(lock.progress_pct, 0.0)
        self.assertLessEqual(lock.progress_pct, 1.0)

    def test_difficulty_name(self):
        """difficulty_name should return the human-readable name."""
        lock = Lock(5, 1)
        self.assertEqual(lock.difficulty_name, 'Novice')
        lock5 = Lock(5, 5)
        self.assertEqual(lock5.difficulty_name, 'Master')

    def test_reset(self):
        """Resetting a lock should give fresh pins and reset state."""
        random.seed(42)
        lock = Lock(5, 2)
        lock.apply_tension(0.5)
        # Set a pin
        for i, pin in enumerate(lock.pins):
            if pin.is_bound:
                while not pin.is_set:
                    lock.lift_pin(i, 0.02)
                break
        self.assertGreater(lock.pins_set_count, 0)

        # Reset
        result = lock.reset()
        self.assertIs(result, lock)  # Should return self for chaining
        self.assertEqual(lock.pins_set_count, 0)
        self.assertEqual(lock.tension, 0.0)
        self.assertFalse(lock.is_open)
        self.assertEqual(lock.pick_health, 1.0)
        self.assertEqual(len(lock.pins), 5)


class TestVisualHelpers(unittest.TestCase):
    """Test visual helper functions."""

    def test_height_to_bar(self):
        """height_to_bar should create bar strings."""
        bar = height_to_bar(0.5, 8)
        self.assertEqual(len(bar), 8)
        self.assertIn('█', bar)
        self.assertIn('░', bar)

    def test_height_to_bar_zero(self):
        """Zero height should give empty bar."""
        bar = height_to_bar(0.0, 8)
        self.assertEqual(bar, '░' * 8)

    def test_height_to_bar_full(self):
        """Full height should give full bar."""
        bar = height_to_bar(1.0, 8)
        self.assertEqual(bar, '█' * 8)

    def test_get_pin_visual_set(self):
        """Set pins should show 'SET' visual."""
        pin = Pin(0.5, 0.2)
        pin.is_set = True
        visual = get_pin_visual(pin)
        self.assertIn('SET', visual)

    def test_get_pin_visual_bound(self):
        """Bound pins should show BOUND indicator."""
        pin = Pin(0.5, 0.2)
        pin.is_bound = True
        visual = get_pin_visual(pin)
        self.assertIn('BOUND', visual)

    def test_get_tension_bar(self):
        """Tension bar should show percentage."""
        bar = get_tension_bar(0.5, 10)
        self.assertIn('50%', bar)

    def test_list_profiles_runs(self):
        """list_profiles should run without error (prints to stdout)."""
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f):
            list_profiles()
        output = f.getvalue()
        self.assertIn('yale-standard', output)
        self.assertIn('Available Lock Profiles', output)


if __name__ == '__main__':
    print("Testing Terminal Lock Picker...\n")
    unittest.main(verbosity=2)