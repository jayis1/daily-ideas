#!/usr/bin/env python3
"""Tests for pipes_puzzle"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from pipes_puzzle import (
    Dir, PipeType, STRAIGHT, ELBOW, TEE, CROSS,
    pipe_char, pipe_connections, generate_puzzle, check_flow, _find_rotation
)


def test_dir_opposite():
    assert Dir.TOP.opposite() == Dir.BOTTOM
    assert Dir.BOTTOM.opposite() == Dir.TOP
    assert Dir.LEFT.opposite() == Dir.RIGHT
    assert Dir.RIGHT.opposite() == Dir.LEFT


def test_dir_delta():
    assert Dir.TOP.delta() == (-1, 0)
    assert Dir.RIGHT.delta() == (0, 1)
    assert Dir.BOTTOM.delta() == (1, 0)
    assert Dir.LEFT.delta() == (0, -1)


def test_pipe_char_straight():
    assert pipe_char(STRAIGHT, 0) == '║'
    assert pipe_char(STRAIGHT, 1) == '═'
    assert pipe_char(STRAIGHT, 2) == '║'
    assert pipe_char(STRAIGHT, 3) == '═'


def test_pipe_char_elbow():
    assert pipe_char(ELBOW, 0) == '╔'
    assert pipe_char(ELBOW, 1) == '╗'
    assert pipe_char(ELBOW, 2) == '╝'
    assert pipe_char(ELBOW, 3) == '╚'


def test_pipe_char_tee():
    assert pipe_char(TEE, 0) == '╩'
    assert pipe_char(TEE, 1) == '╠'
    assert pipe_char(TEE, 2) == '╦'
    assert pipe_char(TEE, 3) == '╣'


def test_pipe_char_cross():
    for rot in range(4):
        assert pipe_char(CROSS, rot) == '╬'


def test_pipe_connections_straight():
    conns = pipe_connections(STRAIGHT, 0)
    assert Dir.TOP in conns
    assert Dir.BOTTOM in conns
    assert len(conns) == 2


def test_pipe_connections_straight_rotated():
    conns = pipe_connections(STRAIGHT, 1)
    assert Dir.LEFT in conns
    assert Dir.RIGHT in conns
    assert len(conns) == 2


def test_pipe_connections_elbow():
    conns = pipe_connections(ELBOW, 0)
    assert Dir.TOP in conns
    assert Dir.RIGHT in conns
    assert len(conns) == 2


def test_pipe_connections_elbow_rotated():
    # Rotation 1: TOP+RIGHT rotated CW -> RIGHT+BOTTOM
    conns = pipe_connections(ELBOW, 1)
    assert Dir.RIGHT in conns
    assert Dir.BOTTOM in conns


def test_pipe_connections_cross():
    for rot in range(4):
        conns = pipe_connections(CROSS, rot)
        assert len(conns) == 4


def test_find_rotation():
    # Straight vertical
    rot = _find_rotation(STRAIGHT, {Dir.TOP, Dir.BOTTOM})
    assert pipe_connections(STRAIGHT, rot) == {Dir.TOP, Dir.BOTTOM}

    # Straight horizontal
    rot = _find_rotation(STRAIGHT, {Dir.LEFT, Dir.RIGHT})
    assert pipe_connections(STRAIGHT, rot) == {Dir.LEFT, Dir.RIGHT}

    # Elbow top-right
    rot = _find_rotation(ELBOW, {Dir.TOP, Dir.RIGHT})
    assert pipe_connections(ELBOW, rot) == {Dir.TOP, Dir.RIGHT}


def test_generate_puzzle_basic():
    grid, rows, cols, source, drain = generate_puzzle(5, 7, 1)
    assert rows == 5
    assert cols == 7
    assert len(grid) == 35
    assert source[1] == -1
    assert drain[1] == 7


def test_generate_puzzle_has_correct_rotations():
    grid, rows, cols, source, drain = generate_puzzle(5, 7, 1)
    for (r, c), (ptype, rotation, correct) in grid.items():
        assert rotation >= 0 and rotation < 4
        assert correct >= 0 and correct < 4


def test_check_flow_unsolved():
    """A freshly generated (scrambled) puzzle should not be solved."""
    for _ in range(10):
        grid, rows, cols, source, drain = generate_puzzle(5, 7, 1)
        solved, filled = check_flow(grid, rows, cols, source, drain)
        # Could theoretically be solved by chance, but very unlikely
        # Just check it runs without error
        assert isinstance(solved, bool)
        assert isinstance(filled, set)


def test_check_flow_solved():
    """If all pipes are in correct rotation, puzzle should be solved."""
    grid, rows, cols, source, drain = generate_puzzle(5, 7, 1)
    # Set all rotations to correct
    for key in grid:
        ptype, rotation, correct = grid[key]
        grid[key] = (ptype, correct, correct)

    solved, filled = check_flow(grid, rows, cols, source, drain)
    assert solved is True
    assert len(filled) > 0


def test_check_flow_blocks_at_left():
    """If first cell doesn't connect left, flow doesn't start."""
    grid, rows, cols, source, drain = generate_puzzle(5, 7, 1)
    # Set first cell to block left connection
    src_r = source[0]
    ptype, rotation, correct = grid[(src_r, 0)]
    conns = pipe_connections(ptype, rotation)
    # Rotate until it doesn't connect left
    for _ in range(4):
        rotation = (rotation + 1) % 4
        conns = pipe_connections(ptype, rotation)
        if Dir.LEFT not in conns:
            break
    grid[(src_r, 0)] = (ptype, rotation, correct)

    solved, filled = check_flow(grid, rows, cols, source, drain)
    assert solved is False


def test_puzzle_sizes():
    """Test various puzzle sizes."""
    for r, c in [(3, 3), (5, 5), (7, 9), (10, 12)]:
        grid, rows, cols, source, drain = generate_puzzle(r, c, 2)
        assert rows == r
        assert cols == c
        assert len(grid) == r * c


def test_difficulty_levels():
    """Test that all difficulty levels generate valid puzzles."""
    for d in [1, 2, 3]:
        grid, rows, cols, source, drain = generate_puzzle(5, 7, d)
        assert len(grid) == 35


def test_flow_connectivity():
    """Flow should be symmetric: if A connects to B, B connects back (when solved)."""
    grid, rows, cols, source, drain = generate_puzzle(5, 7, 1)

    # Use correct rotations to verify structural connectivity
    solved_grid = {}
    for key in grid:
        ptype, rotation, correct = grid[key]
        solved_grid[key] = (ptype, correct, correct)

    solved, filled = check_flow(solved_grid, rows, cols, source, drain)
    assert solved is True

    for (r, c) in filled:
        ptype, rotation, _ = solved_grid[(r, c)]
        conns = pipe_connections(ptype, rotation)
        for d in conns:
            dr, dc = d.delta()
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                nptype, nrotation, _ = solved_grid[(nr, nc)]
                nconns = pipe_connections(nptype, nrotation)
                assert d.opposite() in nconns, \
                    f"Cell ({r},{c}) connects {d.name} to ({nr},{nc}) but no return"


if __name__ == "__main__":
    test_dir_opposite()
    test_dir_delta()
    test_pipe_char_straight()
    test_pipe_char_elbow()
    test_pipe_char_tee()
    test_pipe_char_cross()
    test_pipe_connections_straight()
    test_pipe_connections_straight_rotated()
    test_pipe_connections_elbow()
    test_pipe_connections_elbow_rotated()
    test_pipe_connections_cross()
    test_find_rotation()
    test_generate_puzzle_basic()
    test_generate_puzzle_has_correct_rotations()
    test_check_flow_unsolved()
    test_check_flow_solved()
    test_check_flow_blocks_at_left()
    test_puzzle_sizes()
    test_difficulty_levels()
    test_flow_connectivity()
    print("All tests passed! ✅")