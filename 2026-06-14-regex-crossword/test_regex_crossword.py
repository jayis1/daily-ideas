#!/usr/bin/env python3
"""Tests for the Regex Crossword Generator & Solver (v1.2.0)."""

import sys
import os
import re
import json
import random
import io
import contextlib

sys.path.insert(0, os.path.dirname(__file__))

from regex_crossword import (
    RegexCrossword, generate_smart_puzzle,
    solve_puzzle, solve_puzzle_bruteforce, validate_solution,
    count_solutions, print_puzzle_text, print_solution, 
    PUZZLES, CHARSET_MAP, format_duration, __version__,
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
            col_str = "".join(puzzle.solution[row][c] for row in range(puzzle.rows))
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


def test_solve_binary_blitz():
    """Test solving the binary_blitz puzzle."""
    puzzle = PUZZLES["binary_blitz"]
    solution = solve_puzzle(puzzle)
    assert solution is not None, "Should find a solution for binary_blitz puzzle"
    
    valid, errors = validate_solution(puzzle, solution)
    assert valid, f"Solution should be valid, got errors: {errors}"
    
    print("✓ test_solve_binary_blitz")


def test_alpha_chaos_validates():
    """Test that the alpha_chaos puzzle's built-in solution is valid."""
    puzzle = PUZZLES["alpha_chaos"]
    valid, errors = validate_solution(puzzle, puzzle.solution)
    assert valid, f"alpha_chaos solution should be valid: {errors}"
    
    print("✓ test_alpha_chaos_validates")


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
            col_str = "".join(puzzle.solution[row][c] for row in range(puzzle.rows))
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
            col_str = "".join(puzzle.solution[row][c] for row in range(puzzle.rows))
            assert re.fullmatch(puzzle.col_patterns[c], col_str), \
                f"Difficulty {diff}, col {c}: '{col_str}' doesn't match /{puzzle.col_patterns[c]}/"
    
    print("✓ test_generate_different_difficulties")


def test_generate_different_charsets():
    """Test generating puzzles with different charsets."""
    for charset_name in ["hex", "alpha", "digit", "alnum", "binary"]:
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
    
    # Wrong solution
    grid = [list(row) for row in puzzle.solution]
    grid[0][0] = "Z"
    valid, _ = validate_solution(puzzle, grid)
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
        col_str = "".join(puzzle.solution[row][c] for row in range(puzzle.rows))
        assert re.fullmatch(puzzle.col_patterns[c], col_str)
    
    print("✓ test_larger_puzzle")


def test_solver_partial_pruning():
    """Test that the solver uses row/column pruning correctly."""
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


# ─── New tests for v1.1.0 features ────────────────────────────────────

def test_version():
    """Test that __version__ is defined and follows semver."""
    assert __version__ is not None
    parts = __version__.split(".")
    assert len(parts) == 3, f"Version should be semver, got {__version__}"
    for part in parts:
        assert part.isdigit(), f"Version parts should be numeric, got {__version__}"
    print("✓ test_version")


def test_json_export():
    """Test JSON export for all puzzles."""
    for name, puzzle in PUZZLES.items():
        json_str = puzzle.to_json()
        data = json.loads(json_str)
        assert data["rows"] == puzzle.rows
        assert data["cols"] == puzzle.cols
        assert data["row_patterns"] == puzzle.row_patterns
        assert data["col_patterns"] == puzzle.col_patterns
        assert data["solution"] == puzzle.solution
        assert data["charset"] == puzzle.charset
        assert "version" in data
    print("✓ test_json_export")


def test_json_import():
    """Test JSON import roundtrip for all puzzles."""
    for name, puzzle in PUZZLES.items():
        json_str = puzzle.to_json()
        p2 = RegexCrossword.from_json(json_str)
        assert p2.rows == puzzle.rows
        assert p2.cols == puzzle.cols
        assert p2.row_patterns == puzzle.row_patterns
        assert p2.col_patterns == puzzle.col_patterns
        assert p2.solution == puzzle.solution
        assert p2.charset == puzzle.charset
    print("✓ test_json_import")


def test_json_import_missing_fields():
    """Test that JSON import raises ValueError for missing fields."""
    incomplete_json = json.dumps({"rows": 2, "cols": 2})  # missing patterns, solution
    try:
        RegexCrossword.from_json(incomplete_json)
        assert False, "Should have raised ValueError for missing fields"
    except ValueError as e:
        assert "Missing" in str(e)
    print("✓ test_json_import_missing_fields")


def test_json_import_invalid_json():
    """Test that JSON import raises error for malformed JSON."""
    try:
        RegexCrossword.from_json("{invalid json}")
        assert False, "Should have raised error for invalid JSON"
    except json.JSONDecodeError:
        pass  # Expected
    print("✓ test_json_import_invalid_json")


def test_to_dict():
    """Test the to_dict serialization method."""
    puzzle = PUZZLES["tutorial"]
    d = puzzle.to_dict()
    assert isinstance(d, dict)
    assert d["rows"] == 2
    assert d["cols"] == 2
    assert d["name"] == "tutorial"
    assert "version" in d
    print("✓ test_to_dict")


def test_from_dict():
    """Test the from_dict deserialization method."""
    puzzle = PUZZLES["easy"]
    d = puzzle.to_dict()
    p2 = RegexCrossword.from_dict(d)
    assert p2.rows == puzzle.rows
    assert p2.solution == puzzle.solution
    print("✓ test_from_dict")


def test_puzzle_name():
    """Test that puzzles have names."""
    for name, puzzle in PUZZLES.items():
        assert puzzle.name == name, f"Puzzle key '{name}' should match puzzle.name '{puzzle.name}'"
    print("✓ test_puzzle_name")


def test_count_solutions():
    """Test solution counting."""
    # The easy puzzle with literal patterns should have exactly 1 solution
    n = count_solutions(PUZZLES["easy"], limit=10)
    assert n == 1, f"Easy puzzle should have exactly 1 solution, got {n}"
    
    # Tutorial has loose patterns so may have multiple solutions
    n = count_solutions(PUZZLES["tutorial"], limit=100)
    assert n >= 1, "Tutorial puzzle should have at least 1 solution"
    
    # Binary blitz has a small charset, good for testing
    n = count_solutions(PUZZLES["binary_blitz"], limit=100)
    assert n >= 1, "Binary blitz should have at least 1 solution"
    print("✓ test_count_solutions")


def test_format_duration():
    """Test the format_duration utility function."""
    assert format_duration(0) == "0.0s"
    assert format_duration(1) == "1.0s"
    assert format_duration(59.9) == "59.9s"
    assert format_duration(60) == "1m 0s"
    assert format_duration(90) == "1m 30s"
    assert format_duration(3600) == "1h 0m 0s"
    assert format_duration(3661) == "1h 1m 1s"
    print("✓ test_format_duration")


def test_generate_validation():
    """Test that generate_smart_puzzle validates its arguments."""
    # Invalid rows
    try:
        generate_smart_puzzle(rows=1, cols=3)
        assert False, "Should raise ValueError for rows=1"
    except ValueError:
        pass
    
    # Invalid cols
    try:
        generate_smart_puzzle(rows=3, cols=1)
        assert False, "Should raise ValueError for cols=1"
    except ValueError:
        pass
    
    # Invalid difficulty
    try:
        generate_smart_puzzle(rows=3, cols=3, difficulty=4)
        assert False, "Should raise ValueError for difficulty=4"
    except ValueError:
        pass
    
    # Valid ranges
    puzzle = generate_smart_puzzle(rows=2, cols=2, difficulty=1)
    assert puzzle.rows == 2 and puzzle.cols == 2
    
    puzzle = generate_smart_puzzle(rows=8, cols=8, difficulty=3)
    assert puzzle.rows == 8 and puzzle.cols == 8
    
    print("✓ test_generate_validation")


def test_binary_charset():
    """Test generating and solving with the binary charset."""
    random.seed(42)
    puzzle = generate_smart_puzzle(rows=2, cols=2, difficulty=1, charset_name="binary")
    assert puzzle.charset == "01"
    
    solved = solve_puzzle(puzzle)
    assert solved is not None, "Should solve binary puzzle"
    
    # Verify all chars are 0 or 1
    for r in range(puzzle.rows):
        for c in range(puzzle.cols):
            assert solved[r][c] in "01", f"Binary puzzle char should be 0 or 1, got {solved[r][c]}"
    
    print("✓ test_binary_charset")


def test_check_row_with_invalid_regex():
    """Test that check_row handles invalid regex patterns gracefully."""
    puzzle = RegexCrossword(
        rows=1, cols=2,
        row_patterns=["[invalid"],  # Unclosed bracket
        col_patterns=["AB"],
        solution=[["A", "B"]],
        charset="AB",
    )
    grid = [["A", "B"]]
    result = puzzle.check_row(0, grid)
    assert result == False, "Invalid regex should return False, not crash"
    
    print("✓ test_check_row_with_invalid_regex")


def test_check_col_with_invalid_regex():
    """Test that check_col handles invalid regex patterns gracefully."""
    puzzle = RegexCrossword(
        rows=2, cols=1,
        row_patterns=["A", "B"],
        col_patterns=["[invalid"],  # Unclosed bracket
        solution=[["A"], ["B"]],
        charset="AB",
    )
    grid = [["A"], ["B"]]
    result = puzzle.check_col(0, grid)
    assert result == False, "Invalid regex should return False, not crash"
    
    print("✓ test_check_col_with_invalid_regex")


def test_validate_solution_invalid_pattern():
    """Test validate_solution with invalid regex patterns."""
    puzzle = RegexCrossword(
        rows=1, cols=1,
        row_patterns=["[invalid"],
        col_patterns=["A"],
        solution=[["A"]],
        charset="A",
    )
    valid, errors = validate_solution(puzzle, [["A"]])
    assert not valid, "Should report invalid pattern"
    assert any("invalid" in e.lower() or "Row" in e for e in errors)
    print("✓ test_validate_solution_invalid_pattern")


def test_cli_version():
    """Test the --version CLI flag."""
    import subprocess
    r = subprocess.run(["python3", "regex_crossword.py", "--version"],
                      capture_output=True, text=True,
                      cwd=os.path.dirname(__file__))
    assert "1.2.0" in (r.stdout + r.stderr), f"Version should be in output, got stdout={r.stdout} stderr={r.stderr}"
    print("✓ test_cli_version")


def test_cli_help():
    """Test the --help flag includes new options."""
    import subprocess
    r = subprocess.run(["python3", "regex_crossword.py", "--help"],
                      capture_output=True, text=True,
                      cwd=os.path.dirname(__file__))
    assert "--export" in r.stdout, "Help should mention --export"
    assert "--import" in r.stdout, "Help should mention --import"
    assert "--timer" in r.stdout, "Help should mention --timer"
    assert "--unique" in r.stdout, "Help should mention --unique"
    assert "--version" in r.stdout, "Help should mention --version"
    assert "binary" in r.stdout, "Help should mention binary charset"
    print("✓ test_cli_help")


def test_cli_list():
    """Test the --list flag includes new puzzles."""
    import subprocess
    r = subprocess.run(["python3", "regex_crossword.py", "--list"],
                      capture_output=True, text=True,
                      cwd=os.path.dirname(__file__))
    assert "binary_blitz" in r.stdout, "List should include binary_blitz"
    assert "alpha_chaos" in r.stdout, "List should include alpha_chaos"
    print("✓ test_cli_list")


def test_cli_export():
    """Test the --export flag produces valid JSON."""
    import subprocess
    r = subprocess.run(["python3", "regex_crossword.py", "--export", "tutorial"],
                      capture_output=True, text=True,
                      cwd=os.path.dirname(__file__))
    data = json.loads(r.stdout)
    assert data["rows"] == 2
    assert data["cols"] == 2
    assert data["name"] == "tutorial"
    print("✓ test_cli_export")


def test_cli_print_new_puzzles():
    """Test --print works for new puzzles."""
    import subprocess
    for name in ["binary_blitz", "alpha_chaos"]:
        r = subprocess.run(["python3", "regex_crossword.py", "--print", name],
                          capture_output=True, text=True,
                          cwd=os.path.dirname(__file__))
        assert r.returncode == 0, f"--print {name} should succeed"
        assert len(r.stdout) > 0, f"--print {name} should produce output"
    print("✓ test_cli_print_new_puzzles")


def test_cli_unknown_puzzle():
    """Test that unknown puzzle names produce an error message."""
    import subprocess
    r = subprocess.run(["python3", "regex_crossword.py", "--play", "nonexistent"],
                      capture_output=True, text=True,
                      cwd=os.path.dirname(__file__))
    assert "Unknown" in r.stdout or "Available" in r.stdout
    print("✓ test_cli_unknown_puzzle")


def test_solver_with_error_patterns():
    """Test that the solver handles invalid regex patterns without crashing."""
    puzzle = RegexCrossword(
        rows=2, cols=2,
        row_patterns=["AB", "[invalid"],
        col_patterns=["AC", "BD"],
        solution=[["A", "B"], ["C", "D"]],
        charset="ABCD",
    )
    # Should not crash, but may not find a solution
    result = solve_puzzle(puzzle)
    # We just verify it doesn't raise an exception
    print("✓ test_solver_with_error_patterns")


def test_new_predefined_puzzles_six_total():
    """Test that we have at least 6 predefined puzzles now."""
    assert len(PUZZLES) >= 6, f"Should have at least 6 puzzles, got {len(PUZZLES)}"
    assert "binary_blitz" in PUZZLES, "binary_blitz should exist"
    assert "alpha_chaos" in PUZZLES, "alpha_chaos should exist"
    print("✓ test_new_predefined_puzzles_six_total")


def test_binary_charset_in_charset_map():
    """Test that the binary charset is available in CHARSET_MAP."""
    assert "binary" in CHARSET_MAP, "binary should be in CHARSET_MAP"
    assert CHARSET_MAP["binary"] == "01", "binary charset should be '01'"
    print("✓ test_binary_charset_in_charset_map")


# ─── New tests for v1.2.0 bug fixes ──────────────────────────────────

def test_generate_small_charset_difficulty3():
    """Test that difficulty 3 with small charsets doesn't crash."""
    # Binary charset (2 unique chars) should work at difficulty 3
    random.seed(42)
    for _ in range(10):
        puzzle = generate_smart_puzzle(rows=2, cols=2, difficulty=3, charset_name="binary")
        assert puzzle.rows == 2 and puzzle.cols == 2
        # Verify solution is valid
        for r in range(puzzle.rows):
            row_str = "".join(puzzle.solution[r])
            assert re.fullmatch(puzzle.row_patterns[r], row_str), \
                f"Binary diff-3 row {r}: '{row_str}' doesn't match /{puzzle.row_patterns[r]}/"
    print("✓ test_generate_small_charset_difficulty3")


def test_generate_single_char_charset_raises():
    """Test that a 1-char charset raises ValueError for difficulty 3."""
    try:
        generate_smart_puzzle(rows=2, cols=2, difficulty=3, charset_name="A")
        assert False, "Should raise ValueError for 1-char charset at difficulty 3"
    except ValueError as e:
        assert "unique" in str(e).lower() or "character" in str(e).lower()
    print("✓ test_generate_single_char_charset_raises")


def test_generate_empty_charset_raises():
    """Test that an empty charset raises ValueError."""
    try:
        generate_smart_puzzle(rows=2, cols=2, difficulty=1, charset_name="")
        assert False, "Should raise ValueError for empty charset"
    except ValueError:
        pass  # Expected
    print("✓ test_generate_empty_charset_raises")


def test_negated_class_produces_valid_regex():
    """Test that negated class patterns produce valid regex for all built-in charsets."""
    for charset_name in ["alpha", "hex", "vowel", "digit", "alnum", "binary"]:
        random.seed(42)
        for _ in range(20):
            puzzle = generate_smart_puzzle(rows=2, cols=2, difficulty=3, charset_name=charset_name)
            # Verify all patterns are valid regex
            for rp in puzzle.row_patterns:
                try:
                    re.compile(rp)
                except re.error:
                    assert False, f"Invalid regex pattern /{rp}/ for charset {charset_name}"
            for cp in puzzle.col_patterns:
                try:
                    re.compile(cp)
                except re.error:
                    assert False, f"Invalid regex pattern /{cp}/ for charset {charset_name}"
    print("✓ test_negated_class_produces_valid_regex")


def test_variable_shadowing_fix_validate():
    """Test that validate_solution correctly validates columns (variable shadowing fix)."""
    # This test would fail with the old code that used `r` in both outer and inner loops
    puzzle = RegexCrossword(
        rows=3, cols=3,
        row_patterns=["ABC", "DEF", "GHI"],
        col_patterns=["ADG", "BEH", "CFI"],
        solution=[["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]],
        charset="ABCDEFGHI",
    )
    valid, errors = validate_solution(puzzle, puzzle.solution)
    assert valid, f"Correct solution should validate: {errors}"
    
    # Wrong solution should fail
    wrong = [["X", "Y", "Z"], ["X", "Y", "Z"], ["X", "Y", "Z"]]
    valid, errors = validate_solution(puzzle, wrong)
    assert not valid, "Wrong solution should not validate"
    print("✓ test_variable_shadowing_fix_validate")


def test_variable_shadowing_fix_bruteforce():
    """Test that bruteforce solver correctly validates columns."""
    puzzle = RegexCrossword(
        rows=3, cols=3,
        row_patterns=["ABC", "DEF", "GHI"],
        col_patterns=["ADG", "BEH", "CFI"],
        solution=[["A", "B", "C"], ["D", "E", "F"], ["G", "H", "I"]],
        charset="ABCDEFGHI",
    )
    result = solve_puzzle_bruteforce(puzzle)
    assert result == puzzle.solution, f"Bruteforce should find correct solution, got {result}"
    print("✓ test_variable_shadowing_fix_bruteforce")


def test_version_1_2_0():
    """Test that version is 1.2.0."""
    assert __version__ == "1.2.0", f"Version should be 1.2.0, got {__version__}"
    print("✓ test_version_1_2_0")


def main():
    import random
    
    tests = [
        # Original tests
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
        # New v1.1.0 tests
        test_version,
        test_json_export,
        test_json_import,
        test_json_import_missing_fields,
        test_json_import_invalid_json,
        test_to_dict,
        test_from_dict,
        test_puzzle_name,
        test_count_solutions,
        test_format_duration,
        test_generate_validation,
        test_binary_charset,
        test_check_row_with_invalid_regex,
        test_check_col_with_invalid_regex,
        test_validate_solution_invalid_pattern,
        test_cli_version,
        test_cli_help,
        test_cli_list,
        test_cli_export,
        test_cli_print_new_puzzles,
        test_cli_unknown_puzzle,
        test_solver_with_error_patterns,
        test_new_predefined_puzzles_six_total,
        test_binary_charset_in_charset_map,
        test_solve_binary_blitz,
        test_alpha_chaos_validates,
        # v1.2.0 bug fix tests
        test_generate_small_charset_difficulty3,
        test_generate_single_char_charset_raises,
        test_generate_empty_charset_raises,
        test_negated_class_produces_valid_regex,
        test_variable_shadowing_fix_validate,
        test_variable_shadowing_fix_bruteforce,
        test_version_1_2_0,
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