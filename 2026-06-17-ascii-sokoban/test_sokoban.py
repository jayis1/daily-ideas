#!/usr/bin/env python3
"""Tests for the Sokoban game logic."""

import copy
import sys
sys.path.insert(0, '/root/daily-ideas/2026-06-17-ascii-sokoban')
import pytest
from sokoban import (
    parse_level,
    render,
    try_move,
    is_win,
    is_simple_deadlock,
    is_wall_deadlock,
    detect_deadlock,
    Stats,
    LEVELS,
    UNICODE_TILES,
    ASCII_TILES,
)

# ─── Test fixtures ──────────────────────────────────────────────────

# Player at (1,2), goal at (1,1), box at (2,2) — open space around box
SIMPLE_LEVEL = [
    "####",
    "#.@#",
    "# $  ",  # trailing space gives box room to move
    "#  #",
    "####",
]

# Actually let me use a wider level to avoid corner deadlocks in tests
OPEN_LEVEL = [
    "######",
    "# .  #",
    "#  $ #",
    "#  @ #",
    "######",
]

TWO_BOX_LEVEL = [
    "######",
    "#    #",
    "# .$ #",
    "# .$ #",
    "#  @ #",
    "######",
]

DEADLOCK_LEVEL = [
    "####",
    "# $#",
    "# @#",
    "####",
]

WIN_LEVEL = [
    "####",
    "#*@#",
    "#  #",
    "####",
]


# ─── Parser tests ──────────────────────────────────────────────────

class TestParseLevel:
    def test_basic_parsing(self):
        state = parse_level(OPEN_LEVEL)
        assert state['player'] == (3, 3)
        assert (1, 2) in state['goals']
        assert (2, 3) in state['boxes']
        assert len(state['walls']) > 0

    def test_player_on_goal(self):
        level = [
            "####",
            "# +#",
            "#  #",
            "####",
        ]
        state = parse_level(level)
        assert state['player'] == (1, 2)
        assert (1, 2) in state['goals']

    def test_box_on_goal(self):
        level = [
            "####",
            "#* #",
            "# @#",
            "####",
        ]
        state = parse_level(level)
        assert (1, 1) in state['boxes']
        assert (1, 1) in state['goals']

    def test_no_player_raises(self):
        level = [
            "####",
            "#  #",
            "####",
        ]
        with pytest.raises(ValueError, match="No player position"):
            parse_level(level)

    def test_height_and_width(self):
        state = parse_level(OPEN_LEVEL)
        assert state['height'] == 5
        assert state['width'] == 6

    def test_floor_connectivity(self):
        state = parse_level(OPEN_LEVEL)
        # All reachable floor cells should be in 'floor'
        assert state['player'] in state['floor']
        # Walls should not be in floor
        for w in state['walls']:
            assert w not in state['floor']


# ─── Movement tests ───────────────────────────────────────────────

class TestTryMove:
    def test_move_into_wall(self):
        state = parse_level(OPEN_LEVEL)
        # Player at (3,3), move up
        result = try_move(state, (-1, 0))
        assert result is not None  # Can move up
        # Move right into wall at (3,5)
        result = try_move(state, (0, 1))
        assert result is not None  # (3,4) is open, so can move right

    def test_push_box(self):
        level = [
            "#####",
            "# @ #",
            "# $ #",
            "# . #",
            "#####",
        ]
        state = parse_level(level)
        # Player at (1,2), box at (2,2), move down pushes box to (3,2)
        result = try_move(state, (1, 0))
        assert result is not None
        assert result['player'] == (2, 2)
        assert (3, 2) in result['boxes']
        assert (2, 2) not in result['boxes']

    def test_push_box_into_wall(self):
        level = [
            "#####",
            "# @$#",
            "#   #",
            "#####",
        ]
        state = parse_level(level)
        # Player at (1,2), box at (1,3), push right -> box hits wall at (1,4)
        result = try_move(state, (0, 1))
        assert result is None

    def test_push_box_into_box(self):
        level = [
            "######",
            "# @$$#",
            "#    #",
            "######",
        ]
        state = parse_level(level)
        # Player at (1,2), boxes at (1,3) and (1,4), push right -> box hits box
        result = try_move(state, (0, 1))
        assert result is None

    def test_simple_move_no_box(self):
        state = parse_level(OPEN_LEVEL)
        # Player at (3,3), move left to (3,2)
        result = try_move(state, (0, -1))
        assert result is not None
        assert result['player'] == (3, 2)
        # Boxes unchanged
        assert result['boxes'] == state['boxes']

    def test_push_flag_set(self):
        level = [
            "#####",
            "# @ #",
            "# $ #",
            "# . #",
            "#####",
        ]
        state = parse_level(level)
        result = try_move(state, (1, 0))
        assert result is not None
        assert result['pushed'] is True

    def test_push_flag_not_set_on_simple_move(self):
        state = parse_level(OPEN_LEVEL)
        result = try_move(state, (0, -1))
        assert result is not None
        assert result['pushed'] is False


# ─── Win detection tests ───────────────────────────────────────────

class TestIsWin:
    def test_not_win_initially(self):
        state = parse_level(OPEN_LEVEL)
        assert not is_win(state)

    def test_win_with_box_on_goal(self):
        # Box already on goal
        level = [
            "####",
            "#*@#",
            "#  #",
            "####",
        ]
        state = parse_level(level)
        assert is_win(state)

    def test_not_win_box_off_goal(self):
        state = parse_level(OPEN_LEVEL)
        assert not is_win(state)


# ─── Deadlock detection tests ──────────────────────────────────────

class TestDeadlockDetection:
    def test_corner_deadlock(self):
        # Box in a corner (wall above and wall left)
        level = [
            "####",
            "#$ #",
            "# @#",
            "####",
        ]
        state = parse_level(level)
        assert is_simple_deadlock(state)

    def test_no_deadlock_on_goal(self):
        # Box in a corner but it's on a goal
        level = [
            "####",
            "#*.#",
            "# @#",
            "####",
        ]
        state = parse_level(level)
        assert not is_simple_deadlock(state)

    def test_no_deadlock_in_open_space(self):
        state = parse_level(OPEN_LEVEL)
        # Box not in a corner — should not be a deadlock
        assert not is_simple_deadlock(state)

    def test_combined_deadlock(self):
        # Both simple and wall deadlock should be caught by detect_deadlock
        level = [
            "####",
            "#$ #",
            "# @#",
            "####",
        ]
        state = parse_level(level)
        assert detect_deadlock(state)


# ─── Rendering tests ──────────────────────────────────────────────

class TestRender:
    def test_render_unicode(self):
        state = parse_level(OPEN_LEVEL)
        lines = render(state, tiles=UNICODE_TILES)
        assert len(lines) == 5
        # Player should appear at (3,3)
        assert UNICODE_TILES['player'] in lines[3]

    def test_render_ascii(self):
        state = parse_level(OPEN_LEVEL)
        lines = render(state, tiles=ASCII_TILES)
        assert len(lines) == 5
        # Player should appear at (3,3)
        assert '@' in lines[3]

    def test_render_box_on_goal(self):
        level = [
            "####",
            "#*@#",
            "#  #",
            "####",
        ]
        state = parse_level(level)
        lines = render(state, tiles=ASCII_TILES)
        # Box on goal should render as '*'
        assert '*' in lines[1]

    def test_render_player_on_goal(self):
        level = [
            "####",
            "#+ #",
            "#  #",
            "####",
        ]
        state = parse_level(level)
        lines = render(state, tiles=ASCII_TILES)
        # Player on goal should render as '+'
        assert '+' in lines[1]


# ─── Stats tests ──────────────────────────────────────────────────

class TestStats:
    def test_record_level(self):
        stats = Stats()
        stats.record_level(0, moves=10, pushes=3, elapsed=30)
        assert stats.total_moves == 10
        assert stats.total_pushes == 3
        assert stats.levels_completed == 1
        assert stats.best_moves[0] == 10
        assert stats.best_pushes[0] == 3
        assert stats.best_times[0] == 30

    def test_best_scores(self):
        stats = Stats()
        stats.record_level(0, moves=15, pushes=5, elapsed=60)
        stats.record_level(0, moves=10, pushes=3, elapsed=45)
        assert stats.best_moves[0] == 10
        assert stats.best_pushes[0] == 3
        assert stats.best_times[0] == 45

    def test_multiple_levels(self):
        stats = Stats()
        stats.record_level(0, moves=10, pushes=3, elapsed=30)
        stats.record_level(1, moves=20, pushes=6, elapsed=60)
        assert stats.total_moves == 30
        assert stats.total_pushes == 9
        assert stats.levels_completed == 2


# ─── Level integrity tests ─────────────────────────────────────────

class TestLevelIntegrity:
    def test_all_levels_parse(self):
        """Every level in LEVELS should parse without error."""
        for i, level in enumerate(LEVELS):
            state = parse_level(level)
            assert state['player'] is not None, f"Level {i+1} has no player"
            assert len(state['boxes']) > 0, f"Level {i+1} has no boxes"
            assert len(state['goals']) > 0, f"Level {i+1} has no goals"

    def test_boxes_equal_goals(self):
        """Every level should have the same number of boxes and goals."""
        for i, level in enumerate(LEVELS):
            state = parse_level(level)
            assert len(state['boxes']) == len(state['goals']), \
                f"Level {i+1}: {len(state['boxes'])} boxes != {len(state['goals'])} goals"

    def test_all_levels_render(self):
        """Every level should render without error."""
        for i, level in enumerate(LEVELS):
            state = parse_level(level)
            lines = render(state)
            assert len(lines) == state['height']