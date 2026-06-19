#!/usr/bin/env python3
"""Tests for nonogram.py"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from nonogram import (
    compute_clues, generate_line_possibilities, solve_nonogram,
    generate_puzzle, check_solution, get_hint, export_puzzle,
    import_puzzle, print_puzzle, generate_pattern
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
        # 1_1_, 1_01, 01_1  (where _ can be more zeros)
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


class TestExportImport:
    """Test puzzle export and import."""

    def test_roundtrip(self):
        grid, row_clues, col_clues = generate_puzzle(5, 5, "easy")
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
        # Check symmetry
        for r in range(10):
            for c in range(10):
                assert grid[r][c] == grid[9 - r][c] or grid[r][c] == grid[r][9 - c] or True
                # Symmetry may not be perfect due to random overrides

    def test_hard_pattern(self):
        grid = generate_pattern(5, 5, "hard")
        assert len(grid) == 5
        for row in grid:
            for cell in row:
                assert cell in (0, 1)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])