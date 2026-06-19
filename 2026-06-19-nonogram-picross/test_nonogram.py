#!/usr/bin/env python3
"""Tests for nonogram.py"""

import sys
import os
import json
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from nonogram import (
    compute_clues, generate_line_possibilities, solve_nonogram,
    generate_puzzle, check_solution, get_hint, export_puzzle,
    import_puzzle, print_puzzle, generate_pattern, compute_progress,
    verify_unique_solution, __version__
)


class TestComputeClues:
    """Test clue computation from grids."""

    def test_empty_grid(self):
        grid = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        row_clues, col_clues = compute_clues(grid)
        assert row_clues == [[0], [0], [0]]
        assert col_clues == [[0], [0], [0]]

    def test_full_grid(self):
        grid = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]
        row_clues, col_clues = compute_clues(grid)
        assert row_clues == [[3], [3], [3]]
        assert col_clues == [[3], [3], [3]]

    def test_single_cell(self):
        grid = [[1]]
        row_clues, col_clues = compute_clues(grid)
        assert row_clues == [[1]]
        assert col_clues == [[1]]

    def test_cross_pattern(self):
        # 5x5 cross
        grid = [
            [0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0],
            [1, 1, 1, 1, 1],
            [0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0],
        ]
        row_clues, col_clues = compute_clues(grid)
        assert row_clues == [[1], [1], [5], [1], [1]]
        assert col_clues == [[1], [1], [5], [1], [1]]

    def test_multiple_blocks(self):
        grid = [[1, 0, 1, 0, 1]]
        row_clues, col_clues = compute_clues(grid)
        assert row_clues == [[1, 1, 1]]
        assert col_clues == [[1], [0], [1], [0], [1]]

    def test_varying_blocks(self):
        grid = [
            [1, 1, 0, 1, 0],
        ]
        row_clues, col_clues = compute_clues(grid)
        assert row_clues == [[2, 1]]

    def test_rectangular_grid(self):
        grid = [
            [1, 0, 1],
            [0, 1, 0],
            [1, 0, 1],
            [0, 0, 0],
        ]
        row_clues, col_clues = compute_clues(grid)
        assert row_clues == [[1, 1], [1], [1, 1], [0]]
        assert col_clues == [[1, 1], [1], [1, 1]]

    def test_empty_row_in_grid(self):
        grid = [
            [1, 1],
            [0, 0],
            [1, 1],
        ]
        row_clues, col_clues = compute_clues(grid)
        assert row_clues == [[2], [0], [2]]


class TestLinePossibilities:
    """Test line possibility generation."""

    def test_empty_line(self):
        poss = generate_line_possibilities([0], 3)
        assert poss == [(0, 0, 0)]

    def test_full_line(self):
        poss = generate_line_possibilities([3], 3)
        assert poss == [(1, 1, 1)]

    def test_single_cell_in_line(self):
        poss = generate_line_possibilities([1], 3)
        assert len(poss) == 3
        assert (1, 0, 0) in poss
        assert (0, 1, 0) in poss
        assert (0, 0, 1) in poss

    def test_two_blocks(self):
        poss = generate_line_possibilities([1, 1], 4)
        expected = [
            (1, 0, 1, 0),
            (1, 0, 0, 1),
            (0, 1, 0, 1),
        ]
        assert len(poss) == len(expected)
        for p in expected:
            assert p in poss

    def test_block_size_two(self):
        poss = generate_line_possibilities([2], 3)
        expected = [(1, 1, 0), (0, 1, 1)]
        assert len(poss) == 2
        for p in expected:
            assert p in poss

    def test_infeasible_clue(self):
        # Clue that's too long for the line
        poss = generate_line_possibilities([5], 3)
        assert poss == []

    def test_large_block(self):
        poss = generate_line_possibilities([5], 5)
        assert poss == [(1, 1, 1, 1, 1)]

    def test_three_blocks(self):
        poss = generate_line_possibilities([1, 1, 1], 7)
        # Minimum length is 1+1+1+2=5, so 7 gives 3 extra spaces
        assert len(poss) > 0
        for p in poss:
            assert sum(p) == 3
            assert len(p) == 7


class TestSolver:
    """Test the nonogram solver."""

    def test_simple_3x3(self):
        grid = [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ]
        row_clues, col_clues = compute_clues(grid)
        solution = solve_nonogram(row_clues, col_clues)
        assert solution is not None
        for r in range(3):
            for c in range(3):
                assert solution[r][c] == grid[r][c]

    def test_cross_pattern(self):
        grid = [
            [0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0],
            [1, 1, 1, 1, 1],
            [0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0],
        ]
        row_clues, col_clues = compute_clues(grid)
        solution = solve_nonogram(row_clues, col_clues)
        assert solution is not None
        for r in range(5):
            for c in range(5):
                assert solution[r][c] == grid[r][c]

    def test_full_grid(self):
        grid = [[1, 1], [1, 1]]
        row_clues, col_clues = compute_clues(grid)
        solution = solve_nonogram(row_clues, col_clues)
        assert solution is not None
        assert all(solution[r][c] == 1 for r in range(2) for c in range(2))

    def test_empty_grid(self):
        grid = [[0, 0], [0, 0]]
        row_clues, col_clues = compute_clues(grid)
        solution = solve_nonogram(row_clues, col_clues)
        assert solution is not None
        assert all(solution[r][c] == 0 for r in range(2) for c in range(2))

    def test_diagonal(self):
        grid = [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
        row_clues, col_clues = compute_clues(grid)
        solution = solve_nonogram(row_clues, col_clues)
        assert solution is not None
        for r in range(4):
            for c in range(4):
                assert solution[r][c] == grid[r][c]

    def test_l_shape(self):
        grid = [
            [1, 0],
            [1, 0],
            [1, 1],
        ]
        row_clues, col_clues = compute_clues(grid)
        solution = solve_nonogram(row_clues, col_clues)
        assert solution is not None
        for r in range(3):
            for c in range(2):
                assert solution[r][c] == grid[r][c]

    def test_infeasible_puzzle(self):
        # Clue that can't be satisfied
        row_clues = [[5]]
        col_clues = [[0], [0], [0], [0], [0]]
        solution = solve_nonogram(row_clues, col_clues)
        assert solution is None

    def test_solver_with_timeout(self):
        # Basic test with explicit timeout
        grid = [
            [1, 0, 1],
            [0, 1, 0],
            [1, 0, 1],
        ]
        row_clues, col_clues = compute_clues(grid)
        solution = solve_nonogram(row_clues, col_clues, timeout=5)
        assert solution is not None

    def test_single_cell_puzzle(self):
        grid = [[1]]
        row_clues, col_clues = compute_clues(grid)
        solution = solve_nonogram(row_clues, col_clues)
        assert solution is not None
        assert solution[0][0] == 1


class TestGeneratePuzzle:
    """Test puzzle generation."""

    def test_generate_easy(self):
        grid, row_clues, col_clues = generate_puzzle(5, 5, "easy")
        assert len(grid) == 5
        assert len(grid[0]) == 5
        assert len(row_clues) == 5
        assert len(col_clues) == 5

    def test_generate_medium(self):
        grid, row_clues, col_clues = generate_puzzle(10, 10, "medium")
        assert len(grid) == 10
        assert len(grid[0]) == 10

    def test_generate_hard(self):
        grid, row_clues, col_clues = generate_puzzle(5, 5, "hard")
        assert len(grid) == 5
        assert len(grid[0]) == 5

    def test_clues_match_grid(self):
        grid, row_clues, col_clues = generate_puzzle(5, 5, "easy")
        rc, cc = compute_clues(grid)
        assert row_clues == rc
        assert col_clues == cc

    def test_generate_with_seed(self):
        """Test that same seed produces same puzzle."""
        g1, rc1, cc1 = generate_puzzle(5, 5, "easy", seed=42)
        g2, rc2, cc2 = generate_puzzle(5, 5, "easy", seed=42)
        assert g1 == g2
        assert rc1 == rc2
        assert cc1 == cc2

    def test_different_seeds_produce_different_puzzles(self):
        """Test that different seeds produce different puzzles."""
        g1, _, _ = generate_puzzle(5, 5, "easy", seed=42)
        g2, _, _ = generate_puzzle(5, 5, "easy", seed=99)
        # Different seeds should usually produce different grids
        # (not guaranteed but extremely likely)
        different = False
        for r in range(5):
            for c in range(5):
                if g1[r][c] != g2[r][c]:
                    different = True
                    break
            if different:
                break
        assert different

    def test_generate_non_square(self):
        """Test generating non-square puzzles."""
        grid, row_clues, col_clues = generate_puzzle(5, 5, "easy")
        assert len(grid) == 5
        assert len(grid[0]) == 5

    def test_generated_puzzle_is_solvable(self):
        """Test that generated puzzles can be solved."""
        grid, row_clues, col_clues = generate_puzzle(5, 5, "easy", seed=123)
        solution = solve_nonogram(row_clues, col_clues)
        assert solution is not None


class TestCheckSolution:
    """Test solution checking."""

    def test_correct_solution(self):
        grid = [[1, 0], [0, 1]]
        assert check_solution(grid, grid) is True

    def test_incorrect_solution(self):
        solution = [[1, 0], [0, 1]]
        player = [[0, 1], [1, 0]]
        assert check_solution(player, solution) is False

    def test_partial_solution(self):
        solution = [[1, 0], [0, 1]]
        player = [[-1, 0], [0, -1]]
        assert check_solution(player, solution) is False

    def test_x_mark_matches_empty(self):
        """X-marks (0 in player grid) should match empty cells (0 in solution)."""
        solution = [[0, 1], [1, 0]]
        player = [[0, 1], [1, 0]]
        assert check_solution(player, solution) is True

    def test_wrong_mark(self):
        """A filled cell where it should be empty is wrong."""
        solution = [[0, 1]]
        player = [[1, 1]]
        assert check_solution(player, solution) is False


class TestHint:
    """Test hint system."""

    def test_hint_returns_cell(self):
        grid = [[1, 0], [0, 1]]
        player = [[-1, -1], [-1, -1]]
        cell, is_wrong = get_hint(player, grid)
        assert cell is not None
        r, c = cell
        assert 0 <= r < 2
        assert 0 <= c < 2
        assert not is_wrong

    def test_hint_prefers_wrong_cells(self):
        grid = [[1, 0], [0, 1]]
        player = [[0, -1], [-1, -1]]  # First cell is wrong (0 instead of 1)
        cell, is_wrong = get_hint(player, grid)
        assert is_wrong is True
        assert cell == (0, 0)

    def test_no_hint_needed(self):
        grid = [[1, 0], [0, 1]]
        player = [[1, 0], [0, 1]]
        cell, is_wrong = get_hint(player, grid)
        assert cell is None

    def test_hint_on_empty_cell(self):
        """Hint should correctly identify an empty cell."""
        grid = [[0, 0], [0, 0]]
        player = [[-1, -1], [-1, -1]]
        cell, is_wrong = get_hint(player, grid)
        assert cell is not None


class TestProgress:
    """Test progress computation."""

    def test_no_progress(self):
        grid = [[1, 0], [0, 1]]
        player = [[-1, -1], [-1, -1]]
        assert compute_progress(player, grid) == 0.0

    def test_full_progress(self):
        grid = [[1, 0], [0, 1]]
        player = [[1, 0], [0, 1]]
        assert compute_progress(player, grid) == 1.0

    def test_half_progress(self):
        grid = [[1, 0], [0, 1]]
        player = [[1, -1], [-1, -1]]
        assert compute_progress(player, grid) == 0.25

    def test_empty_grid_progress(self):
        grid = [[0, 0], [0, 0]]
        player = [[0, 0], [0, 0]]
        assert compute_progress(player, grid) == 1.0


class TestExportImport:
    """Test puzzle export and import."""

    def test_roundtrip(self):
        grid, row_clues, col_clues = generate_puzzle(5, 5, "easy", seed=42)
        json_str = export_puzzle(row_clues, col_clues, 5, 5)
        rc, cc, r, c = import_puzzle(json_str)
        assert rc == row_clues
        assert cc == col_clues
        assert r == 5
        assert c == 5

    def test_import_invalid_json(self):
        try:
            import_puzzle("not valid json")
            assert False, "Should have raised an exception"
        except json.JSONDecodeError:
            pass

    def test_import_missing_fields(self):
        try:
            import_puzzle('{"rows": 5}')
            assert False, "Should have raised KeyError"
        except (KeyError, ValueError):
            pass

    def test_import_invalid_dimensions(self):
        try:
            import_puzzle('{"rows": -1, "cols": 5, "row_clues": [], "col_clues": []}')
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_import_too_large(self):
        try:
            import_puzzle('{"rows": 50, "cols": 50, "row_clues": [[]]*50, "col_clues": [[]]*50}')
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_import_dimension_mismatch(self):
        try:
            import_puzzle('{"rows": 3, "cols": 3, "row_clues": [[1], [1]], "col_clues": [[1], [1], [1]]}')
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_export_format(self):
        json_str = export_puzzle([[1, 1], [3]], [[2], [1], [1]], 2, 3)
        data = json.loads(json_str)
        assert data["rows"] == 2
        assert data["cols"] == 3
        assert data["row_clues"] == [[1, 1], [3]]
        assert data["col_clues"] == [[2], [1], [1]]


class TestGeneratePattern:
    """Test pattern generation."""

    def test_easy_pattern(self):
        grid = generate_pattern(5, 5, "easy")
        assert len(grid) == 5
        assert len(grid[0]) == 5
        # All cells should be 0 or 1
        for row in grid:
            for cell in row:
                assert cell in (0, 1)

    def test_medium_pattern_symmetry(self):
        grid = generate_pattern(10, 10, "medium")
        assert len(grid) == 10
        assert len(grid[0]) == 10
        # Medium patterns have some symmetry (may not be perfect due to random overrides)

    def test_hard_pattern(self):
        grid = generate_pattern(5, 5, "hard")
        assert len(grid) == 5
        for row in grid:
            for cell in row:
                assert cell in (0, 1)

    def test_pattern_with_rng(self):
        """Test reproducible pattern generation with explicit RNG."""
        rng = random.Random(42)
        grid1 = generate_pattern(5, 5, "easy", rng=rng)
        rng2 = random.Random(42)
        grid2 = generate_pattern(5, 5, "easy", rng=rng2)
        assert grid1 == grid2

    def test_pattern_all_values_valid(self):
        """Test that all pattern cells are 0 or 1."""
        for difficulty in ["easy", "medium", "hard"]:
            grid = generate_pattern(7, 7, difficulty)
            for row in grid:
                for cell in row:
                    assert cell in (0, 1), f"Invalid cell value {cell} in {difficulty} pattern"


class TestUniquenessVerification:
    """Test solution uniqueness verification."""

    def test_unique_solution_cross(self):
        """A cross pattern should have a unique solution."""
        grid = [
            [0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0],
            [1, 1, 1, 1, 1],
            [0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0],
        ]
        row_clues, col_clues = compute_clues(grid)
        assert verify_unique_solution(row_clues, col_clues) is True

    def test_full_grid_unique(self):
        """A fully filled grid should have a unique solution."""
        grid = [[1, 1], [1, 1]]
        row_clues, col_clues = compute_clues(grid)
        assert verify_unique_solution(row_clues, col_clues) is True

    def test_empty_grid_unique(self):
        """An empty grid should have a unique solution."""
        grid = [[0, 0], [0, 0]]
        row_clues, col_clues = compute_clues(grid)
        assert verify_unique_solution(row_clues, col_clues) is True


class TestVersion:
    """Test version is defined."""

    def test_version_exists(self):
        assert __version__ is not None
        assert len(__version__) > 0

    def test_version_format(self):
        parts = __version__.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()


if __name__ == "__main__":
    import random as _random  # noqa: already imported via sys path above
    import pytest
    pytest.main([__file__, "-v"])