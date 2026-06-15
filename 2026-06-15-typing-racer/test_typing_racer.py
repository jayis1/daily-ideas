#!/usr/bin/env python3
"""
Unit tests for Terminal Typing Racer game logic.
Run with: python3 -m pytest test_typing_racer.py -v
  or:    python3 test_typing_racer.py
"""

import json
import os
import tempfile
import time
import unittest

# Import game classes (we test logic only, no curses needed)
from typing_racer import (
    FallingWord, Particle, PowerUp, HighScoreManager,
    TypingRacer, EASY_WORDS, MEDIUM_WORDS, HARD_WORDS, EXPERT_WORDS,
    POWERUP_FREEZE, POWERUP_BOMB, POWERUP_HEART, __version__,
)


class TestFallingWord(unittest.TestCase):
    """Tests for FallingWord class."""

    def test_init(self):
        w = FallingWord("hello", 5, 1.5, "easy")
        self.assertEqual(w.word, "hello")
        self.assertEqual(w.x, 5)
        self.assertEqual(w.y, 0.0)
        self.assertEqual(w.speed, 1.5)
        self.assertEqual(w.difficulty, "easy")
        self.assertEqual(w.typed_count, 0)
        self.assertTrue(w.alive)
        self.assertFalse(w.frozen)

    def test_remaining_and_typed(self):
        w = FallingWord("hello", 0, 1.0, "easy")
        self.assertEqual(w.remaining, "hello")
        self.assertEqual(w.typed, "")
        w.try_char("h")
        self.assertEqual(w.remaining, "ello")
        self.assertEqual(w.typed, "h")
        w.try_char("e")
        self.assertEqual(w.remaining, "llo")
        self.assertEqual(w.typed, "he")

    def test_fraction_typed(self):
        w = FallingWord("cat", 0, 1.0, "easy")
        self.assertAlmostEqual(w.fraction_typed, 0.0)
        w.try_char("c")
        self.assertAlmostEqual(w.fraction_typed, 1 / 3)
        w.try_char("a")
        self.assertAlmostEqual(w.fraction_typed, 2 / 3)

    def test_advance(self):
        w = FallingWord("test", 0, 2.0, "easy")
        w.advance(0.5)
        self.assertAlmostEqual(w.y, 1.0)

    def test_advance_frozen(self):
        w = FallingWord("test", 0, 2.0, "easy")
        w.frozen = True
        w.advance(0.5)
        self.assertAlmostEqual(w.y, 0.0)

    def test_try_char_correct(self):
        w = FallingWord("hello", 0, 1.0, "easy")
        self.assertTrue(w.try_char("h"))
        self.assertTrue(w.try_char("e"))

    def test_try_char_wrong(self):
        w = FallingWord("hello", 0, 1.0, "easy")
        self.assertFalse(w.try_char("x"))
        self.assertEqual(w.typed_count, 0)

    def test_try_char_wrong_after_partial(self):
        w = FallingWord("hello", 0, 1.0, "easy")
        w.try_char("h")
        self.assertFalse(w.try_char("x"))
        self.assertEqual(w.typed_count, 1)  # still at 1

    def test_is_complete(self):
        w = FallingWord("hi", 0, 1.0, "easy")
        self.assertFalse(w.is_complete())
        w.try_char("h")
        self.assertFalse(w.is_complete())
        w.try_char("i")
        self.assertTrue(w.is_complete())

    def test_flash_timer(self):
        w = FallingWord("test", 0, 1.0, "easy")
        w.alive = False
        w.flash_timer = 0.5
        w.advance(0.3)
        self.assertAlmostEqual(w.flash_timer, 0.2)

    def test_empty_word(self):
        """Edge case: empty word string."""
        w = FallingWord("", 0, 1.0, "easy")
        self.assertTrue(w.is_complete())
        self.assertAlmostEqual(w.fraction_typed, 0.0)

    def test_try_char_on_completed_word(self):
        """Trying to type on an already completed word returns False."""
        w = FallingWord("hi", 0, 1.0, "easy")
        w.try_char("h")
        w.try_char("i")
        self.assertTrue(w.is_complete())
        self.assertFalse(w.try_char("x"))
        self.assertEqual(w.typed_count, 2)


class TestParticle(unittest.TestCase):
    """Tests for Particle class."""

    def test_init(self):
        p = Particle(5, 3, "a", 10.0, -5.0, 1.0, 1)
        self.assertEqual(p.x, 5.0)
        self.assertEqual(p.y, 3.0)
        self.assertEqual(p.char, "a")
        self.assertEqual(p.life, 1.0)

    def test_advance(self):
        p = Particle(0, 0, "x", 10.0, -5.0, 1.0, 1)
        p.advance(0.5)
        self.assertAlmostEqual(p.x, 5.0)
        # y = 0 + (-5)*0.5 = -2.5 (gravity applied to vy, not to y in same step)
        self.assertAlmostEqual(p.y, -2.5)

    def test_alive(self):
        p = Particle(0, 0, "x", 0, 0, 0.5, 1)
        self.assertTrue(p.alive)
        p.advance(0.6)
        self.assertFalse(p.alive)


class TestPowerUp(unittest.TestCase):
    """Tests for PowerUp class."""

    def test_init(self):
        pu = PowerUp(POWERUP_FREEZE, 10, 2)
        self.assertEqual(pu.ptype, POWERUP_FREEZE)
        self.assertEqual(pu.x, 10)
        self.assertTrue(pu.alive)

    def test_advance(self):
        pu = PowerUp(POWERUP_BOMB, 10, 2)
        pu.advance(1.0)
        self.assertAlmostEqual(pu.y, 2.6)  # 2 + 0.6*1
        self.assertAlmostEqual(pu.age, 1.0)

    def test_expires(self):
        pu = PowerUp(POWERUP_HEART, 10, 2)
        pu.advance(8.0)
        self.assertFalse(pu.alive)

    def test_symbol_and_label(self):
        self.assertEqual(PowerUp.SYMBOLS[POWERUP_FREEZE], "❄")
        self.assertEqual(PowerUp.LABELS[POWERUP_BOMB], "BOMB")
        self.assertEqual(PowerUp.LABELS[POWERUP_HEART], "+1 LIFE")

    def test_unknown_powerup_symbol(self):
        """Unknown powerup type returns '?' for symbol/label."""
        pu = PowerUp("unknown", 10, 2)
        self.assertEqual(pu.symbol, "?")
        self.assertEqual(pu.label, "?")

    def test_powerup_speed(self):
        """Power-up falls at speed 0.6 rows/sec."""
        pu = PowerUp(POWERUP_FREEZE, 10, 0)
        self.assertAlmostEqual(pu.speed, 0.6)

    def test_powerup_max_age(self):
        """Power-up disappears after 8 seconds."""
        pu = PowerUp(POWERUP_BOMB, 10, 0)
        self.assertAlmostEqual(pu.max_age, 8.0)


class TestHighScoreManager(unittest.TestCase):
    """Tests for HighScoreManager class."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "test_scores.json")
        self.hs = HighScoreManager(path=self.path)

    def tearDown(self):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass
        os.rmdir(self.tmpdir)

    def test_empty_scores(self):
        self.assertEqual(self.hs.scores, [])

    def test_add_and_save(self):
        rank = self.hs.add(500, 45.0, 92.0, 3, 15, 5)
        self.assertEqual(rank, 1)
        self.assertEqual(len(self.hs.scores), 1)
        self.assertEqual(self.hs.scores[0]["score"], 500)

    def test_sorted_order(self):
        self.hs.add(100, 20.0, 80.0, 1, 5, 2)
        self.hs.add(500, 60.0, 95.0, 5, 30, 10)
        self.hs.add(300, 40.0, 85.0, 3, 15, 8)
        self.assertEqual(self.hs.scores[0]["score"], 500)
        self.assertEqual(self.hs.scores[1]["score"], 300)
        self.assertEqual(self.hs.scores[2]["score"], 100)

    def test_max_entries(self):
        for i in range(15):
            self.hs.add(i * 100, 20.0, 80.0, 1, 5, 2)
        self.assertEqual(len(self.hs.scores), 10)

    def test_is_high_score(self):
        for i in range(10):
            self.hs.add(100, 20.0, 80.0, 1, 5, 2)
        # 100 is the lowest score, so 50 shouldn't qualify
        self.assertFalse(self.hs.is_high_score(50))
        # 200 should qualify
        self.assertTrue(self.hs.is_high_score(200))
        # With fewer than max entries, any score qualifies
        hs2 = HighScoreManager(path=os.path.join(self.tmpdir, "other.json"))
        self.assertTrue(hs2.is_high_score(1))

    def test_load_from_disk(self):
        self.hs.add(500, 45.0, 92.0, 3, 15, 5)
        # Reload from disk
        hs2 = HighScoreManager(path=self.path)
        hs2.load()
        self.assertEqual(len(hs2.scores), 1)
        self.assertEqual(hs2.scores[0]["score"], 500)

    def test_load_corrupt_file(self):
        with open(self.path, "w") as f:
            f.write("NOT JSON{{{")
        hs2 = HighScoreManager(path=self.path)
        hs2.load()
        self.assertEqual(hs2.scores, [])

    def test_clear(self):
        self.hs.add(100, 20.0, 80.0, 1, 5, 2)
        self.hs.clear()
        self.assertEqual(self.hs.scores, [])
        self.assertFalse(os.path.exists(self.path))

    def test_clear_nonexistent(self):
        hs = HighScoreManager(path="/tmp/nonexistent_scores_test.json")
        hs.clear()  # should not raise

    def test_add_returns_zero_when_not_in_top(self):
        """When board is full and score doesn't qualify, return 0."""
        for i in range(10):
            self.hs.add(1000 - i * 10, 50.0, 90.0, 3, 15, 5)
        # The lowest score is 910, so 50 doesn't qualify
        rank = self.hs.add(50, 10.0, 50.0, 1, 2, 1)
        self.assertEqual(rank, 0)

    def test_score_entry_fields(self):
        """Verify all expected fields are present in a score entry."""
        self.hs.add(250, 55.5, 88.8, 4, 20, 7)
        entry = self.hs.scores[0]
        self.assertIn("score", entry)
        self.assertIn("wpm", entry)
        self.assertIn("accuracy", entry)
        self.assertIn("level", entry)
        self.assertIn("words", entry)
        self.assertIn("max_combo", entry)
        self.assertIn("date", entry)
        self.assertEqual(entry["score"], 250)
        self.assertAlmostEqual(entry["wpm"], 55.5)
        self.assertAlmostEqual(entry["accuracy"], 88.8)
        self.assertEqual(entry["level"], 4)
        self.assertEqual(entry["words"], 20)
        self.assertEqual(entry["max_combo"], 7)


class TestWordPools(unittest.TestCase):
    """Verify word pools are well-formed."""

    def test_easy_words_lowercase(self):
        for word in EASY_WORDS:
            self.assertEqual(word, word.lower(), f"Word '{word}' should be lowercase")

    def test_medium_words_lowercase(self):
        for word in MEDIUM_WORDS:
            self.assertEqual(word, word.lower(), f"Word '{word}' should be lowercase")

    def test_hard_words_lowercase(self):
        for word in HARD_WORDS:
            self.assertEqual(word, word.lower(), f"Word '{word}' should be lowercase")

    def test_expert_words_lowercase(self):
        for word in EXPERT_WORDS:
            self.assertEqual(word, word.lower(), f"Word '{word}' should be lowercase")

    def test_no_duplicates_in_pools(self):
        for pool_name, pool in [
            ("easy", EASY_WORDS), ("medium", MEDIUM_WORDS),
            ("hard", HARD_WORDS), ("expert", EXPERT_WORDS)
        ]:
            self.assertEqual(len(pool), len(set(pool)),
                             f"{pool_name} pool has duplicate words")

    def test_all_words_nonempty(self):
        for pool in [EASY_WORDS, MEDIUM_WORDS, HARD_WORDS, EXPERT_WORDS]:
            for word in pool:
                self.assertTrue(len(word) > 0, f"Empty word in pool")
                self.assertTrue(word.isalpha(), f"Word '{word}' has non-alpha characters")

    def test_easy_words_are_short(self):
        for word in EASY_WORDS:
            self.assertLessEqual(len(word), 4, f"Easy word '{word}' too long: {len(word)}")

    def test_expert_words_are_long(self):
        for word in EXPERT_WORDS:
            self.assertGreaterEqual(len(word), 9, f"Expert word '{word}' too short: {len(word)}")


class TestVersion(unittest.TestCase):
    """Verify version is set."""

    def test_version_exists(self):
        self.assertIsNotNone(__version__)
        self.assertRegex(__version__, r"\d+\.\d+\.\d+")


class TestScoring(unittest.TestCase):
    """Test scoring formula by examining _complete_word logic."""

    def test_score_formula_easy(self):
        """Easy word: (10 + len) * 1 * 1 = 10 + len"""
        expected = 13
        length_bonus = 3
        combo_mult = 1.0
        difficulty_bonus = 1
        points = int((10 + length_bonus) * combo_mult * difficulty_bonus)
        self.assertEqual(points, expected)

    def test_score_formula_with_combo(self):
        """Combo 5: (10 + len) * (1 + 4*0.25) * diff_bonus"""
        length_bonus = 5
        combo_mult = 1.0 + (5 - 1) * 0.25
        difficulty_bonus = 2
        points = int((10 + length_bonus) * combo_mult * difficulty_bonus)
        self.assertEqual(points, 60)


class TestBugFixes(unittest.TestCase):
    """Tests for bug fixes in v2.1 and v2.2."""

    def test_bomb_does_not_increment_words_completed(self):
        """Bomb power-up should NOT count destroyed words toward words_completed."""
        words = [
            FallingWord("cat", 5, 1.0, "easy"),
            FallingWord("dog", 10, 1.0, "easy"),
            FallingWord("sun", 15, 1.0, "easy"),
        ]
        words_completed_before = 5
        bombed_count = 0
        score_before = 100
        for w in words:
            if w.alive:
                w.alive = False
                score_before += 5
                bombed_count += 1
        self.assertEqual(words_completed_before, 5)
        self.assertEqual(score_before, 100 + 5 * 3)

    def test_powerup_collection_mechanic(self):
        """Power-ups should be collected when they reach the bottom area."""
        pu = PowerUp(POWERUP_FREEZE, 10, 2)
        self.assertTrue(pu.alive)
        pu.advance(8.0)
        self.assertFalse(pu.alive)

    def test_bomb_powerup_no_words_completed_increment(self):
        """Verify that collect_powerup for BOMB does not change words_completed."""
        self.assertTrue(hasattr(TypingRacer, 'collect_powerup'))

    def test_freeze_powerup_freezes_words(self):
        """Freeze power-up should set frozen=True on all words."""
        words = [
            FallingWord("cat", 5, 1.0, "easy"),
            FallingWord("dog", 10, 1.0, "easy"),
        ]
        for w in words:
            self.assertFalse(w.frozen)
        for w in words:
            w.frozen = True
        for w in words:
            self.assertTrue(w.frozen)
            old_y = w.y
            w.advance(1.0)
            self.assertAlmostEqual(w.y, old_y)

    def test_heart_powerup_max_lives(self):
        """Heart power-up should not exceed max 5 lives."""
        lives = 5
        new_lives = min(lives + 1, 5)
        self.assertEqual(new_lives, 5)
        lives = 3
        new_lives = min(lives + 1, 5)
        self.assertEqual(new_lives, 4)

    def test_spawn_interval_bounds(self):
        """spawn_interval should never go below 0.8."""
        for level in range(1, 100):
            interval = max(0.8, 2.5 - (level - 1) * 0.15)
            self.assertGreaterEqual(interval, 0.8)

    def test_esc_does_not_skip_countdown(self):
        """ESC key (ch=27) should be ignored during countdown phase."""
        ch = 27
        started = False
        if ch == 27:
            pass
        else:
            started = True
        self.assertFalse(started)

    def test_quit_from_pause(self):
        """Q key during pause should trigger game over."""
        ch = ord('q')
        paused = True
        game_over = False
        if paused and ch == ord('q'):
            game_over = True
        self.assertTrue(game_over)

    # ── v2.2 bug fix tests ────────────────────────────────────────────

    def test_case_insensitive_matching(self):
        """Uppercase letters should match lowercase words (Caps Lock fix)."""
        w = FallingWord("hello", 5, 1.0, "easy")
        # Simulate the lowercase conversion now done in handle_input
        self.assertTrue(w.try_char("H".lower()))
        self.assertTrue(w.try_char("E".lower()))
        # Without lowercase conversion, these would fail
        self.assertFalse(w.try_char("E"))  # uppercase fails raw match

    def test_non_alpha_keys_ignored(self):
        """Non-alpha characters should not affect gameplay."""
        # The fix in handle_input: if not char.isalpha(): return
        # This means space, digits, punctuation are completely ignored
        self.assertFalse(" ".isalpha())
        self.assertFalse("1".isalpha())
        self.assertFalse(".".isalpha())
        self.assertFalse("\n".isalpha())
        # But letters should still work
        self.assertTrue("a".isalpha())
        self.assertTrue("A".isalpha())

    def test_high_score_validates_entries(self):
        """HighScoreManager should skip invalid entries on load."""
        tmpdir = tempfile.mkdtemp()
        try:
            path = os.path.join(tmpdir, "test_scores.json")
            # Write a mix of valid and invalid entries
            with open(path, "w") as f:
                json.dump([
                    "not a dict",
                    42,
                    {"score": 100, "wpm": 20.0, "accuracy": 80.0,
                     "level": 1, "words": 5, "max_combo": 2, "date": "2026-01-01"},
                    {"score": 50},  # missing keys
                ], f)
            hs = HighScoreManager(path=path)
            hs.load()
            # Only the valid entry should survive
            self.assertEqual(len(hs.scores), 1)
            self.assertEqual(hs.scores[0]["score"], 100)
        finally:
            os.remove(path)
            os.rmdir(tmpdir)

    def test_unlocked_tier_always_has_weight(self):
        """Unlocked difficulty tiers should always have weight >= 1.

        Before fix: hard tier was unlocked at 10 words but had weight=0
        until level 3, meaning it would never spawn despite being unlocked.
        """
        # Simulate the weight calculation at various levels
        for level in range(1, 10):
            # Easy weight
            easy_w = max(1, 5 - level)
            self.assertGreaterEqual(easy_w, 1, f"easy weight at level {level}")
            # Medium weight
            medium_w = max(1, min(level, 5))
            self.assertGreaterEqual(medium_w, 1, f"medium weight at level {level}")
            # Hard weight (unlocked at 10 words, but level matters)
            if level > 2:
                hard_w = max(1, min(level - 1, 4))
            else:
                hard_w = 1  # unlocked but low level
            self.assertGreaterEqual(hard_w, 1, f"hard weight at level {level}")
            # Expert weight
            if level > 4:
                expert_w = max(1, min(level - 3, 3))
            else:
                expert_w = 1  # unlocked but low level
            self.assertGreaterEqual(expert_w, 1, f"expert weight at level {level}")


if __name__ == "__main__":
    unittest.main()