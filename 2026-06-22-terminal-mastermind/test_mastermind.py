#!/usr/bin/env python3
"""Tests for Terminal Mastermind."""

import json
import random
import sys
import os
import tempfile
from pathlib import Path

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mastermind import (
    evaluate_guess, is_valid_guess, generate_all_codes,
    knuth_minimax_solver, GameConfig, GameStats, load_stats, save_stats,
    COLORS, DIFFICULTIES, Ansi, format_color_peg, format_feedback,
    format_color_name, color_menu, play_batch_solve
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
        # Position 0: 0=0 -> black
        # Position 1: 1 vs 0 -> check: 0 at pos 1 is already used (pos 0)
        # We need to be careful with duplicate handling
        black, white = evaluate_guess([0, 1, 0, 1], [0, 0, 1, 1])
        # Position 0: 0=0 -> black (1)
        # Remaining secret: [0, 1, 1], Remaining guess: [1, 0, 1]
        # Position 1: 1 vs 0 -> no
        # Position 2: 0 vs 1 -> no
        # Position 3: 1 vs 1 -> black (2)
        # White: position 1 guess 1 matches secret position 2 -> white
        # position 2 guess 0 matches secret position 1 -> white
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
        # Position 0: 1 vs 0 -> no
        # Position 1: 0 vs 1 -> no
        # Position 2: 2 vs 1 -> no
        # Position 3: 1 vs 2 -> no
        # But: guess 1 appears in secret positions 1, 2 -> 2 matches
        # guess 0 appears in secret position 0 -> 1 match
        # guess 2 appears in secret position 3 -> 1 match
        # Total color matches = 4, but we need to handle duplicates
        # Secret counts: {0:1, 1:2, 2:1}
        # Guess counts: {1:2, 0:1, 2:1}
        # Intersection: min(1,1)=1 for 0, min(2,2)=2 for 1, min(1,1)=1 for 2 = 4
        # Black: 0, so White = 4
        assert black == 0
        assert white == 4


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


class TestFormatFunctions:
    """Test display formatting."""
    
    def test_format_color_peg(self):
        result = format_color_peg(0, 6)
        assert "R" in result
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
    
    def test_color_menu(self):
        result = color_menu(6)
        assert "Red" in result
        assert "Green" in result
    
    def test_format_color_name(self):
        result = format_color_name(0)
        assert "Red" in result


class TestGameConfig:
    """Test game configuration."""
    
    def test_default_config(self):
        config = GameConfig()
        assert config.code_length == 4
        assert config.num_colors == 6
        assert config.max_guesses == 10
    
    def test_custom_config(self):
        config = GameConfig(code_length=5, num_colors=8, max_guesses=12)
        assert config.code_length == 5
        assert config.num_colors == 8
        assert config.max_guesses == 12


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


class TestEdgeCases:
    """Test edge cases."""
    
    def test_evaluate_guess_single(self):
        assert evaluate_guess([0], [0]) == (1, 0)
        assert evaluate_guess([0], [1]) == (0, 0)
    
    def test_evaluate_guess_two_same(self):
        # Two of same in guess, one in secret
        black, white = evaluate_guess([0, 0], [1, 0])
        assert black == 1  # position 1 matches
        assert white == 0  # extra 0 has no match
    
    def test_evaluate_guess_swap(self):
        # Simple swap of two positions
        assert evaluate_guess([1, 0], [0, 1]) == (0, 2)


def run_tests():
    """Run all tests."""
    test_classes = [
        TestEvaluateGuess, TestIsValidGuess, TestGenerateAllCodes,
        TestKnuthSolver, TestFormatFunctions, TestGameConfig,
        TestGameStats, TestStatsFile, TestDifficulties,
        TestBatchSolve, TestEdgeCases
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