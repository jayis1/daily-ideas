#!/usr/bin/env python3
"""Tests for the Regex Crossword Generator & Solver."""

import sys
import os
import re
import random

sys.path.insert(0, os.path.dirname(__file__))

from regex_crossword import (
    RegexCrossword, generate_smart_puzzle,
    solve_puzzle, solve_puzzle_bruteforce, validate_solution,
    print_puzzle_text, print_solution, PUZZLES, CHARSET_MAP
)


def test_basic_puzzle_creation():
    """Test creating a basic puzzle."""
    puzzle = RegexCrossword(
        rows=2, cols=2,
        row_patterns=["AB", "CD"],
        col_patterns=["AC", "BD"],
        solution=[["A", "B"], ["C", "D"]],
        charset="ABCD",
    )
    assert puzzle.rows == 2
    assert puzzle.cols == 2
    assert len(puzzle.row_patterns) == 2
    assert len(puzzle.col_patterns) == 2
    print("✓ test_basic_puzzle_creation")


def test_check_row_col():
    """Test row and column checking."""
    puzzle = RegexCrossword(
        rows=2, cols=2,
        row_patterns=["AB", "CD"],
        col_patterns=["AC", "BD"],
        solution=[["A", "B"], ["C", "D"]],
        charset="ABCD",
    )
    
    # Complete valid grid
    grid = [["A", "B"], ["C", "D"]]
    assert puzzle.check_row(0, grid) == True
    assert puzzle.check_row(1, grid) == True
    assert puzzle.check_col(0, grid) == True
    assert puzzle.check_col(1, grid) == True
    
    # Invalid grid
    grid_bad = [["D", "C"], ["B", "A"]]
    assert puzzle.check_row(0, grid_bad) == False
    
    # Incomplete grid
    grid_partial = [["A", None], ["C", "D"]]
    assert puzzle.check_row(0, grid_partial) is None  # incomplete
    assert puzzle.check_row(1, grid_partial) == True
    assert puzzle.check_col(1, grid_partial) is None  # incomplete
    
    print("✓ test_check_row_col")


def test_is_solved():
    """Test is_solved method."""
    puzzle = RegexCrossword(
        rows=2, cols=2,
        row_patterns=["AB", "CD"],
        col_patterns=["AC", "BD"],
        solution=[["A", "B"], ["C", "D"]],
        charset="ABCD",
    )
    
    # Solved grid
    grid = [["A", "B"], ["C", "D"]]
    assert puzzle.is_solved(grid) == True
    
    # Wrong solution
    grid_bad = [["A", "A"], ["A", "A"]]
    assert puzzle.is_solved(grid_bad) == False
    
    # Incomplete
    grid_partial = [["A", "B"], ["C", None]]
    assert puzzle.is_solved(grid_partial) == False
    
    print("✓ test_is_solved")


def test_predefined_puzzles_valid():
    """Test that all predefined puzzles have valid solutions."""
    for name, puzzle in PUZZLES.items():
        # Check row patterns
        for r in range(puzzle.rows):
            row_str = "".join(puzzle.solution[r])
            assert re.fullmatch(puzzle.row_patterns[r], row_str), \
                f"Puzzle '{name}': Row {r} solution '{row_str}' doesn't match /{puzzle.row_patterns[r]}/"
        
        # Check column patterns
        for c in range(puzzle.cols):
            col_str = "".join(puzzle.solution[r][c] for r in range(puzzle.rows))
            assert re.fullmatch(puzzle.col_patterns[c], col_str), \
                f"Puzzle '{name}': Col {c} solution '{col_str}' doesn't match /{puzzle.col_patterns[c]}/"
    
    print("✓ test_predefined_puzzles_valid")


def test_solve_tutorial():
    """Test solving the tutorial puzzle."""
    puzzle = PUZZLES["tutorial"]
    solution = solve_puzzle(puzzle)
    assert solution is not None, "Should find a solution for tutorial puzzle"
    
    valid, errors = validate_solution(puzzle, solution)
    assert valid, f"Solution should be valid, got errors: {errors}"
    
    print("✓ test_solve_tutorial")


def test_solve_easy():
    """Test solving the easy puzzle."""
    puzzle = PUZZLES["easy"]
    solution = solve_puzzle(puzzle)
    assert solution is not None, "Should find a solution for easy puzzle"
    
    valid, errors = validate_solution(puzzle, solution)
    assert valid, f"Solution should be valid, got errors: {errors}"
    
    print("✓ test_solve_easy")


def test_solve_medium():
    """Test solving the medium puzzle."""
    puzzle = PUZZLES["medium"]
    solution = solve_puzzle(puzzle)
    assert solution is not None, "Should find a solution for medium puzzle"
    
    valid, errors = validate_solution(puzzle, solution)
    assert valid, f"Solution should be valid, got errors: {errors}"
    
    print("✓ test_solve_medium")


def test_solve_vowel_vortex():
    """Test solving the vowel vortex puzzle."""
    puzzle = PUZZLES["vowel_vortex"]
    solution = solve_puzzle(puzzle)
    assert solution is not None, "Should find a solution for vowel vortex puzzle"
    
    valid, errors = validate_solution(puzzle, solution)
    assert valid, f"Solution should be valid, got errors: {errors}"
    
    print("✓ test_solve_vowel_vortex")


def test_generate_puzzle():
    """Test generating random puzzles."""
    for seed in range(5):
        random.seed(seed)
        puzzle = generate_smart_puzzle(rows=3, cols=3, difficulty=1, charset_name="hex")
        assert puzzle.rows == 3
        assert puzzle.cols == 3
        assert len(puzzle.solution) == 3
        assert len(puzzle.solution[0]) == 3
        
        # Verify solution is valid
        for r in range(puzzle.rows):
            row_str = "".join(puzzle.solution[r])
            assert re.fullmatch(puzzle.row_patterns[r], row_str), \
                f"Generated puzzle row {r}: '{row_str}' doesn't match /{puzzle.row_patterns[r]}/"
        
        for c in range(puzzle.cols):
            col_str = "".join(puzzle.solution[r][c] for r in range(puzzle.rows))
            assert re.fullmatch(puzzle.col_patterns[c], col_str), \
                f"Generated puzzle col {c}: '{col_str}' doesn't match /{puzzle.col_patterns[c]}/"
    
    print("✓ test_generate_puzzle")


def test_generate_different_difficulties():
    """Test generating puzzles at different difficulty levels."""
    for diff in [1, 2, 3]:
        random.seed(42 + diff)
        puzzle = generate_smart_puzzle(rows=3, cols=3, difficulty=diff, charset_name="hex")
        assert puzzle.rows == 3
        assert puzzle.cols == 3
        
        # Verify solution
        for r in range(puzzle.rows):
            row_str = "".join(puzzle.solution[r])
            assert re.fullmatch(puzzle.row_patterns[r], row_str), \
                f"Difficulty {diff}, row {r}: '{row_str}' doesn't match /{puzzle.row_patterns[r]}/"
        
        for c in range(puzzle.cols):
            col_str = "".join(puzzle.solution[r][c] for r in range(puzzle.rows))
            assert re.fullmatch(puzzle.col_patterns[c], col_str), \
                f"Difficulty {diff}, col {c}: '{col_str}' doesn't match /{puzzle.col_patterns[c]}/"
    
    print("✓ test_generate_different_difficulties")


def test_generate_different_charsets():
    """Test generating puzzles with different charsets."""
    for charset_name in ["hex", "alpha", "digit", "alnum"]:
        random.seed(hash(charset_name))
        puzzle = generate_smart_puzzle(rows=2, cols=2, difficulty=1, charset_name=charset_name)
        charset = CHARSET_MAP[charset_name]
        
        # Verify all solution chars are in charset
        for r in range(puzzle.rows):
            for c in range(puzzle.cols):
                assert puzzle.solution[r][c] in charset, \
                    f"Charset {charset_name}: solution char '{puzzle.solution[r][c]}' not in charset"
    
    print("✓ test_generate_different_charsets")


def test_validate_solution():
    """Test the validate_solution function."""
    puzzle = PUZZLES["tutorial"]
    
    # Correct solution
    grid = [list(row) for row in puzzle.solution]
    valid, errors = validate_solution(puzzle, grid)
    assert valid, f"Correct solution should validate: {errors}"
    
    # Wrong solution - should still validate if it matches constraints
    # (might match or not depending on the constraints)
    grid = [list(row) for row in puzzle.solution]
    grid[0][0] = "Z"  # Probably wrong
    valid, _ = validate_solution(puzzle, grid)
    # This should be invalid for tutorial puzzle since row pattern is "A."
    assert not valid, "Invalid solution should not validate"
    
    print("✓ test_validate_solution")


def test_bruteforce_solve():
    """Test the brute force solver on a small puzzle."""
    puzzle = RegexCrossword(
        rows=2, cols=2,
        row_patterns=["[A-C][1-3]", "[D-F][4-6]"],
        col_patterns=["[A-Z][A-Z]", "\\d\\d"],
        solution=[["A", "1"], ["D", "4"]],
        charset="ABCDEF123456",
    )
    
    result = solve_puzzle_bruteforce(puzzle, "ABCDEF123456")
    assert result is not None, "Should find a solution via brute force"
    
    valid, errors = validate_solution(puzzle, result)
    assert valid, f"Brute force solution should be valid: {errors}"
    
    print("✓ test_bruteforce_solve")


def test_solver_handles_constrained():
    """Test solver with a very constrained puzzle - unique solution."""
    puzzle = RegexCrossword(
        rows=2, cols=2,
        row_patterns=["AB", "CD"],
        col_patterns=["AC", "BD"],
        solution=[["A", "B"], ["C", "D"]],
        charset="ABCD",
    )
    
    result = solve_puzzle(puzzle)
    assert result is not None, "Should find solution for constrained puzzle"
    assert result == [["A", "B"], ["C", "D"]], "Should find the unique solution"
    
    print("✓ test_solver_handles_constrained")


def test_print_puzzle_no_errors():
    """Test that print_puzzle_text doesn't crash."""
    import io
    import contextlib
    
    for name, puzzle in PUZZLES.items():
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            print_puzzle_text(puzzle)
        output = f.getvalue()
        assert len(output) > 0, f"Puzzle '{name}' should produce output"
        assert "Column" in output or "C" in output, f"Output should mention columns"
    
    print("✓ test_print_puzzle_no_errors")


def test_print_solution_no_errors():
    """Test that print_solution doesn't crash."""
    import io
    import contextlib
    
    for name, puzzle in PUZZLES.items():
        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            print_solution(puzzle)
        output = f.getvalue()
        assert len(output) > 0, f"Puzzle '{name}' should produce solution output"
    
    print("✓ test_print_solution_no_errors")


def test_generate_and_solve():
    """Test generating and then solving a puzzle."""
    random.seed(123)
    puzzle = generate_smart_puzzle(rows=3, cols=3, difficulty=1, charset_name="hex")
    
    solved = solve_puzzle(puzzle)
    assert solved is not None, "Should find a solution for generated puzzle"
    
    valid, errors = validate_solution(puzzle, solved)
    assert valid, f"Solver's solution should be valid: {errors}"
    
    print("✓ test_generate_and_solve")


def test_larger_puzzle():
    """Test with a larger 4x4 puzzle."""
    random.seed(999)
    puzzle = generate_smart_puzzle(rows=4, cols=4, difficulty=1, charset_name="hex")
    assert puzzle.rows == 4
    assert puzzle.cols == 4
    
    # Verify the solution
    for r in range(puzzle.rows):
        row_str = "".join(puzzle.solution[r])
        assert re.fullmatch(puzzle.row_patterns[r], row_str)
    
    for c in range(puzzle.cols):
        col_str = "".join(puzzle.solution[r][c] for r in range(puzzle.rows))
        assert re.fullmatch(puzzle.col_patterns[c], col_str)
    
    print("✓ test_larger_puzzle")


def test_solver_partial_pruning():
    """Test that the solver uses partial row/column pruning correctly."""
    # A puzzle where partial matching helps prune the search space
    puzzle = RegexCrossword(
        rows=3, cols=3,
        row_patterns=["ABC", "DEF", "GHI"],
        col_patterns=["ADG", "BEH", "CFI"],
        solution=[["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]],
        charset="ABCDEFGHI",
    )
    
    result = solve_puzzle(puzzle)
    assert result is not None, "Should find solution"
    assert result == puzzle.solution, "Should find the unique solution"
    
    print("✓ test_solver_partial_pruning")


def main():
    import random
    
    tests = [
        test_basic_puzzle_creation,
        test_check_row_col,
        test_is_solved,
        test_predefined_puzzles_valid,
        test_solve_tutorial,
        test_solve_easy,
        test_solve_medium,
        test_solve_vowel_vortex,
        test_generate_puzzle,
        test_generate_different_difficulties,
        test_generate_different_charsets,
        test_validate_solution,
        test_bruteforce_solve,
        test_solver_handles_constrained,
        test_print_puzzle_no_errors,
        test_print_solution_no_errors,
        test_generate_and_solve,
        test_larger_puzzle,
        test_solver_partial_pruning,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())