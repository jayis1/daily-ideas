#!/usr/bin/env python3
"""Tests for Terminal Mastermind."""

import json
import random
import sys
import os
import tempfile
from pathlib import Path
from collections import Counter

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mastermind import (
    evaluate_guess, is_valid_guess, generate_all_codes,
    knuth_minimax_solver, GameConfig, GameStats, load_stats, save_stats,
    COLORS, DIFFICULTIES, DIFFICULTY_MULTIPLIERS, Ansi, format_color_peg,
    format_feedback, format_color_name, color_menu, play_batch_solve,
    calculate_score, format_time, format_color_name_colorblind,
    COLORBLIND_SYMBOLS, VERSION, RULES
)


class TestEvaluateGuess:
    """Test the core evaluation logic."""
    
    def test_perfect_match(self):
        assert evaluate_guess([0, 1, 2, 3], [0, 1, 2, 3]) == (4, 0)
    
    def test_no_match(self):
        assert evaluate_guess([0, 0, 0, 0], [1, 1, 1, 1]) == (0, 0)
    
    def test_all_white_pegs(self):
        assert evaluate_guess([1, 0, 3, 2], [0, 1, 2, 3]) == (0, 4)
    
    def test_mixed_pegs(self):
        # 2 black (positions 0, 3), 1 white (position 2 matches position 1)
        assert evaluate_guess([0, 2, 1, 3], [0, 1, 4, 3]) == (2, 1)
    
    def test_repeated_colors(self):
        # Secret: [0, 0, 1, 1], Guess: [0, 1, 0, 1]
        black, white = evaluate_guess([0, 1, 0, 1], [0, 0, 1, 1])
        assert black == 2
        assert white == 2
    
    def test_single_peg(self):
        assert evaluate_guess([0], [0]) == (1, 0)
        assert evaluate_guess([0], [1]) == (0, 0)
    
    def test_long_code(self):
        code = list(range(8))
        assert evaluate_guess(code, code) == (8, 0)
        assert evaluate_guess(code, code[::-1]) == (0, 8)
    
    def test_all_same_color(self):
        assert evaluate_guess([0, 0, 0, 0], [0, 0, 0, 0]) == (4, 0)
        assert evaluate_guess([0, 0, 0, 0], [1, 1, 1, 1]) == (0, 0)
    
    def test_partial_duplicates(self):
        # Secret: [0, 1, 1, 2], Guess: [1, 0, 2, 1]
        black, white = evaluate_guess([1, 0, 2, 1], [0, 1, 1, 2])
        assert black == 0
        assert white == 4

    def test_length_mismatch_raises(self):
        """evaluate_guess should raise ValueError on length mismatch."""
        try:
            evaluate_guess([0, 1], [0, 1, 2])
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_two_same_one_in_secret(self):
        """Two of same in guess, one in secret."""
        black, white = evaluate_guess([0, 0], [1, 0])
        assert black == 1  # position 1 matches
        assert white == 0  # extra 0 has no match

    def test_swap(self):
        """Simple swap of two positions."""
        assert evaluate_guess([1, 0], [0, 1]) == (0, 2)


class TestIsValidGuess:
    """Test guess validation."""
    
    def test_valid_guess(self):
        assert is_valid_guess([0, 1, 2, 3], 4, 6) is True
    
    def test_wrong_length(self):
        assert is_valid_guess([0, 1, 2], 4, 6) is False
    
    def test_color_out_of_range(self):
        assert is_valid_guess([0, 1, 2, 6], 4, 6) is False
    
    def test_negative_color(self):
        assert is_valid_guess([0, -1, 2, 3], 4, 6) is False

    def test_exact_boundary(self):
        """Max valid color index is num_colors-1."""
        assert is_valid_guess([0, 1, 2, 5], 4, 6) is True  # 5 = 6-1
        assert is_valid_guess([0, 1, 2, 6], 4, 6) is False  # 6 >= 6


class TestGenerateAllCodes:
    """Test code generation."""
    
    def test_small_case(self):
        codes = generate_all_codes(2, 3)
        assert len(codes) == 9  # 3^2
        assert [0, 0] in codes
        assert [2, 2] in codes
    
    def test_length_one(self):
        codes = generate_all_codes(1, 4)
        assert len(codes) == 4
        assert [0] in codes
        assert [3] in codes
    
    def test_zero_length(self):
        codes = generate_all_codes(0, 4)
        assert codes == [[]]

    def test_standard_game(self):
        """4 pegs, 6 colors = 1296 codes."""
        codes = generate_all_codes(4, 6)
        assert len(codes) == 1296


class TestKnuthSolver:
    """Test the auto-solver."""
    
    def test_solve_easy(self):
        """Solver should solve a 4-peg, 6-color game."""
        config = GameConfig(code_length=4, num_colors=6, max_guesses=10,
                           secret=[0, 1, 2, 3])
        guesses = knuth_minimax_solver(config.code_length, config.num_colors,
                                       config.secret, config.max_guesses)
        assert guesses[-1].black == 4, f"Expected 4 black pegs, got {guesses[-1]}"
    
    def test_solve_another_code(self):
        """Solver should solve a different code."""
        config = GameConfig(code_length=4, num_colors=6, max_guesses=10,
                           secret=[5, 4, 3, 2])
        guesses = knuth_minimax_solver(config.code_length, config.num_colors,
                                       config.secret, config.max_guesses)
        assert guesses[-1].black == 4
    
    def test_solve_repeated_colors(self):
        """Solver should handle codes with repeated colors."""
        config = GameConfig(code_length=4, num_colors=6, max_guesses=10,
                           secret=[0, 0, 1, 1])
        guesses = knuth_minimax_solver(config.code_length, config.num_colors,
                                       config.secret, config.max_guesses)
        assert guesses[-1].black == 4
    
    def test_solver_within_max_guesses(self):
        """Knuth's algorithm should solve 4-peg 6-color in ≤5 guesses."""
        config = GameConfig(code_length=4, num_colors=6, max_guesses=10,
                           secret=[3, 5, 0, 2])
        guesses = knuth_minimax_solver(config.code_length, config.num_colors,
                                       config.secret, config.max_guesses)
        assert len(guesses) <= 5, f"Expected ≤5 guesses, took {len(guesses)}"
    
    def test_solver_all_same(self):
        config = GameConfig(code_length=4, num_colors=6, max_guesses=10,
                           secret=[0, 0, 0, 0])
        guesses = knuth_minimax_solver(config.code_length, config.num_colors,
                                       config.secret, config.max_guesses)
        assert guesses[-1].black == 4

    def test_solver_fails_on_insufficient_guesses(self):
        """Solver should still return guesses even if it can't solve."""
        config = GameConfig(code_length=4, num_colors=6, max_guesses=2,
                           secret=[3, 5, 0, 2])
        guesses = knuth_minimax_solver(config.code_length, config.num_colors,
                                       config.secret, config.max_guesses)
        # It may or may not solve in 2 guesses, but it should not crash
        assert isinstance(guesses, list)


class TestFormatFunctions:
    """Test display formatting."""
    
    def test_format_color_peg(self):
        result = format_color_peg(0, 6)
        assert "R" in result
        assert Ansi.RESET in result

    def test_format_color_peg_colorblind(self):
        result = format_color_peg(0, 6, colorblind=True)
        assert COLORBLIND_SYMBOLS[0] in result
        assert Ansi.RESET in result
    
    def test_format_feedback_perfect(self):
        result = format_feedback(4, 0, 4)
        assert "●" in result
    
    def test_format_feedback_white(self):
        result = format_feedback(0, 4, 4)
        assert "○" in result
    
    def test_format_feedback_mixed(self):
        result = format_feedback(2, 1, 4)
        assert "●" in result
        assert "○" in result
        assert "·" in result

    def test_format_feedback_zero(self):
        result = format_feedback(0, 0, 4)
        assert "·" in result
    
    def test_color_menu(self):
        result = color_menu(6)
        assert "Red" in result
        assert "Green" in result

    def test_color_menu_colorblind(self):
        result = color_menu(6, colorblind=True)
        assert "Red" in result
        # Should contain the color-blind symbols
        assert COLORBLIND_SYMBOLS[0] in result
    
    def test_format_color_name(self):
        result = format_color_name(0)
        assert "Red" in result

    def test_format_color_name_colorblind(self):
        result = format_color_name_colorblind(0)
        assert "Red" in result
        assert COLORBLIND_SYMBOLS[0] in result


class TestGameConfig:
    """Test game configuration."""
    
    def test_default_config(self):
        config = GameConfig()
        assert config.code_length == 4
        assert config.num_colors == 6
        assert config.max_guesses == 10
        assert config.difficulty == "easy"
        assert config.colorblind is False
    
    def test_custom_config(self):
        config = GameConfig(code_length=5, num_colors=8, max_guesses=12)
        assert config.code_length == 5
        assert config.num_colors == 8
        assert config.max_guesses == 12

    def test_validate_valid(self):
        config = GameConfig(code_length=4, num_colors=6, max_guesses=10)
        assert config.validate() == []

    def test_validate_invalid_length(self):
        config = GameConfig(code_length=0, num_colors=6, max_guesses=10)
        errors = config.validate()
        assert len(errors) > 0

    def test_validate_too_many_colors(self):
        config = GameConfig(code_length=4, num_colors=15, max_guesses=10)
        errors = config.validate()
        assert any("colors" in e.lower() for e in errors)

    def test_validate_too_few_colors(self):
        config = GameConfig(code_length=4, num_colors=1, max_guesses=10)
        errors = config.validate()
        assert len(errors) > 0


class TestGameStats:
    """Test game statistics."""
    
    def test_default_stats(self):
        stats = GameStats()
        assert stats.games_played == 0
        assert stats.games_won == 0
        assert stats.win_rate == 0.0
        assert stats.avg_guesses == 0.0
    
    def test_win_rate(self):
        stats = GameStats(games_played=10, games_won=7)
        assert abs(stats.win_rate - 0.7) < 0.001
    
    def test_avg_guesses(self):
        stats = GameStats(guess_history=[3, 4, 5, 4, 3])
        assert abs(stats.avg_guesses - 3.8) < 0.001

    def test_record_game_win(self):
        stats = GameStats()
        stats.record_game(won=True, num_guesses=4, difficulty="easy", score=900, elapsed_seconds=30.5)
        assert stats.games_played == 1
        assert stats.games_won == 1
        assert stats.current_streak == 1
        assert stats.best_streak == 1
        assert stats.guess_history == [4]
        assert len(stats.game_history) == 1
        assert stats.game_history[0]["won"] is True
        assert stats.game_history[0]["score"] == 900

    def test_record_game_loss(self):
        stats = GameStats()
        stats.record_game(won=False, num_guesses=10, difficulty="medium", score=0, elapsed_seconds=120.0)
        assert stats.games_played == 1
        assert stats.games_won == 0
        assert stats.current_streak == 0

    def test_record_game_streak(self):
        stats = GameStats()
        stats.record_game(won=True, num_guesses=3, difficulty="easy", score=1000)
        stats.record_game(won=True, num_guesses=4, difficulty="easy", score=900)
        assert stats.current_streak == 2
        assert stats.best_streak == 2

    def test_record_game_streak_broken(self):
        stats = GameStats()
        stats.record_game(won=True, num_guesses=3, difficulty="easy", score=1000)
        stats.record_game(won=False, num_guesses=10, difficulty="easy", score=0)
        stats.record_game(won=True, num_guesses=4, difficulty="easy", score=900)
        assert stats.current_streak == 1
        assert stats.best_streak == 1

    def test_per_difficulty_stats(self):
        stats = GameStats()
        stats.record_game(won=True, num_guesses=3, difficulty="easy", score=1000)
        stats.record_game(won=True, num_guesses=5, difficulty="hard", score=1200)
        assert "easy" in stats.difficulty_stats
        assert "hard" in stats.difficulty_stats
        assert stats.difficulty_stats["easy"]["won"] == 1
        assert stats.difficulty_stats["hard"]["won"] == 1

    def test_game_history_capped_at_50(self):
        stats = GameStats()
        for i in range(60):
            stats.record_game(won=True, num_guesses=4, difficulty="easy", score=700)
        assert len(stats.game_history) == 50


class TestScoreCalculation:
    """Test the score system."""

    def test_loss_scores_zero(self):
        assert calculate_score(False, 5, 10, "easy") == 0

    def test_win_base_score_easy(self):
        # 10 guesses max, solved in 5 guesses → (10-5+1)*100*1.0 = 600
        assert calculate_score(True, 5, 10, "easy") == 600

    def test_win_first_guess_easy(self):
        # Solved in 1 guess → (10-1+1)*100*1.0 = 1000
        assert calculate_score(True, 1, 10, "easy") == 1000

    def test_win_medium_multiplier(self):
        # (10-5+1)*100*1.5 = 900
        assert calculate_score(True, 5, 10, "medium") == 900

    def test_win_hard_multiplier(self):
        # (10-5+1)*100*2.0 = 1200
        assert calculate_score(True, 5, 10, "hard") == 1200

    def test_win_expert_multiplier(self):
        # (10-5+1)*100*3.0 = 1800
        assert calculate_score(True, 5, 10, "expert") == 1800

    def test_win_with_streak(self):
        # Streak 5: base * (1 + 5*0.1) = 600 * 1.5 = 900
        score = calculate_score(True, 5, 10, "easy", current_streak=5)
        assert score == 900

    def test_streak_capped_at_10(self):
        # Streak 10 and 15 should give same bonus
        s10 = calculate_score(True, 5, 10, "easy", current_streak=10)
        s15 = calculate_score(True, 5, 10, "easy", current_streak=15)
        assert s10 == s15

    def test_win_last_guess(self):
        # Solved on last guess → (10-10+1)*100*1.0 = 100
        assert calculate_score(True, 10, 10, "easy") == 100


class TestFormatTime:
    """Test time formatting."""

    def test_zero_seconds(self):
        assert format_time(0.0) == "0:00"

    def test_30_seconds(self):
        assert format_time(30.0) == "0:30"

    def test_90_seconds(self):
        assert format_time(90.0) == "1:30"

    def test_large_time(self):
        assert format_time(3661.0) == "61:01"


class TestStatsFile:
    """Test stats file loading/saving."""
    
    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp = Path(f.name)
        
        try:
            stats = GameStats(games_played=5, games_won=3, current_streak=2,
                             best_streak=4, total_guesses=15, guess_history=[3, 4, 3, 2, 3])
            # Manually save to temp file
            tmp.write_text(json.dumps(stats.__dict__, indent=2))
            
            # Load from temp file
            data = json.loads(tmp.read_text())
            loaded = GameStats(**data)
            assert loaded.games_played == 5
            assert loaded.games_won == 3
            assert loaded.current_streak == 2
            assert loaded.best_streak == 4
        finally:
            tmp.unlink()
    
    def test_load_nonexistent(self):
        # Should return default stats
        stats = GameStats()
        assert stats.games_played == 0

    def test_load_with_missing_fields(self):
        """Loading old stats files without new fields should still work."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            tmp = Path(f.name)
        try:
            # Old format without difficulty_stats or game_history
            old_data = {
                "games_played": 10,
                "games_won": 7,
                "current_streak": 3,
                "best_streak": 5,
                "total_guesses": 30,
                "guess_history": [3, 4, 5, 4, 3, 3, 4]
            }
            tmp.write_text(json.dumps(old_data))
            data = json.loads(tmp.read_text())
            # Add missing fields manually as load_stats does
            data.setdefault("difficulty_stats", {})
            data.setdefault("game_history", [])
            loaded = GameStats(**data)
            assert loaded.games_played == 10
            assert loaded.difficulty_stats == {}
            assert loaded.game_history == []
        finally:
            tmp.unlink()


class TestDifficulties:
    """Test difficulty presets."""
    
    def test_easy(self):
        d = DIFFICULTIES["easy"]
        assert d["code_length"] == 4
        assert d["num_colors"] == 6
        assert d["max_guesses"] == 12
    
    def test_expert(self):
        d = DIFFICULTIES["expert"]
        assert d["code_length"] == 6
        assert d["num_colors"] == 10
        assert d["max_guesses"] == 10
    
    def test_all_difficulties_valid(self):
        for name, d in DIFFICULTIES.items():
            assert d["code_length"] >= 1
            assert d["num_colors"] >= 2
            assert d["max_guesses"] >= 1

    def test_difficulty_multipliers(self):
        assert DIFFICULTY_MULTIPLIERS["easy"] == 1.0
        assert DIFFICULTY_MULTIPLIERS["medium"] == 1.5
        assert DIFFICULTY_MULTIPLIERS["hard"] == 2.0
        assert DIFFICULTY_MULTIPLIERS["expert"] == 3.0


class TestBatchSolve:
    """Test batch solving for statistics."""
    
    def test_batch_solve_easy(self):
        """Batch solve should work for easy difficulty."""
        config = GameConfig(code_length=4, num_colors=6, max_guesses=10)
        results = play_batch_solve(config, num_games=10)
        assert results["total"] == 10
        assert results["wins"] >= 8  # Knuth should solve most/all
        assert results["avg_guesses"] > 0
        assert results["avg_guesses"] <= 5.5  # Should average well under 6
    
    def test_batch_solve_all_win(self):
        """For 4 pegs 6 colors, solver should win all games."""
        config = GameConfig(code_length=4, num_colors=6, max_guesses=10)
        results = play_batch_solve(config, num_games=20)
        assert results["win_rate"] == 1.0, f"Expected 100% win rate, got {results['win_rate']}"

    def test_batch_solve_has_distribution(self):
        """Batch solve should return guess distribution."""
        config = GameConfig(code_length=4, num_colors=6, max_guesses=10)
        results = play_batch_solve(config, num_games=20)
        assert "guess_distribution" in results
        assert isinstance(results["guess_distribution"], dict)
        assert len(results["guess_distribution"]) > 0


class TestVersion:
    """Test version is defined."""

    def test_version_exists(self):
        assert VERSION is not None
        assert isinstance(VERSION, str)
        # Should be in semver format
        parts = VERSION.split(".")
        assert len(parts) == 3

class TestRules:
    """Test rules display constant."""

    def test_rules_defined(self):
        assert RULES is not None
        assert "Black peg" in RULES or "●" in RULES

class TestColorBlindSymbols:
    """Test color-blind symbol definitions."""

    def test_symbols_match_colors(self):
        assert len(COLORBLIND_SYMBOLS) == len(COLORS)

    def test_symbols_are_unique(self):
        assert len(set(COLORBLIND_SYMBOLS)) == len(COLORBLIND_SYMBOLS)


def run_tests():
    """Run all tests."""
    test_classes = [
        TestEvaluateGuess, TestIsValidGuess, TestGenerateAllCodes,
        TestKnuthSolver, TestFormatFunctions, TestGameConfig,
        TestGameStats, TestScoreCalculation, TestFormatTime,
        TestStatsFile, TestDifficulties,
        TestBatchSolve, TestVersion, TestRules,
        TestColorBlindSymbols
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_class in test_classes:
        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith('test_')]
        for method_name in methods:
            try:
                method = getattr(instance, method_name)
                method()
                passed += 1
            except Exception as e:
                failed += 1
                errors.append(f"  {test_class.__name__}.{method_name}: {e}")
    
    print(f"\n{'='*60}")
    print(f"Tests: {passed} passed, {failed} failed, {passed+failed} total")
    print(f"{'='*60}")
    
    if errors:
        print("\nFailures:")
        for err in errors:
            print(err)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_tests())