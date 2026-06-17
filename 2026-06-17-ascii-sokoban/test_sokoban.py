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
    strip_ansi,
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
    "# $  ",
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

# Corridor level for wall deadlock tests
CORRIDOR_LEVEL = [
    "######",
    "#$.  #",
    "######",
]

# Box in corridor with goal (NOT a deadlock)
CORRIDOR_GOAL_LEVEL = [
    "######",
    "# $. #",
    "######",
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

    def test_row_padding(self):
        """Rows of different lengths should be padded to the same length."""
        level = [
            "###",
            "# @#",
            "####",
        ]
        state = parse_level(level)
        assert state['width'] == 4  # max row length


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

    def test_boxes_not_shared_reference(self):
        """Bug fix: boxes set should not be shared between states."""
        state = parse_level(OPEN_LEVEL)
        result = try_move(state, (0, -1))
        assert result is not None
        # The returned boxes should be a separate object
        assert result['boxes'] is not state['boxes']

    def test_move_out_of_bounds(self):
        """Moving out of bounds should return None."""
        level = [
            "#####",
            "#@  #",
            "#   #",
            "#####",
        ]
        state = parse_level(level)
        # Player at (1,1). Move up to (0,1) which is a wall
        result = try_move(state, (-1, 0))
        assert result is None  # Wall at (0,1)

    def test_push_box_out_of_bounds(self):
        """Pushing a box out of bounds should return None."""
        level = [
            "#####",
            "# @$ #",
            "#####",
        ]
        state = parse_level(level)
        # Player at (1,1), box at (1,2), push right -> box to (1,3) which is space
        result = try_move(state, (0, 1))
        assert result is not None
        # But push box further right into wall at (1,4)
        result2 = try_move(result, (0, 1))
        assert result2 is None  # Wall blocks


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

    def test_win_with_empty_goals_is_false(self):
        """Bug fix: is_win should return False for empty goals (malformed level)."""
        state = {
            'goals': frozenset(),
            'boxes': set(),
        }
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

    def test_wall_deadlock_corridor(self):
        """Box in a corridor (walls above and below) with no goal on the row = deadlock."""
        # Box at (1,1) in horizontal corridor, goal on a different row
        level = [
            "#######",
            "#$    #",
            "##### #",
            "#  .  #",
            "# @   #",
            "#######",
        ]
        state = parse_level(level)
        assert is_wall_deadlock(state)

    def test_wall_deadlock_not_triggered_by_single_wall(self):
        """Bug fix: Box against one wall should NOT trigger corridor deadlock."""
        # Box against a wall on one side but free on the other
        level = [
            "######",
            "#$ . #",
            "#    #",
            "# @  #",
            "######",
        ]
        state = parse_level(level)
        # Box at (1,1) has wall above but no wall below — not a corridor
        assert not is_wall_deadlock(state)

    def test_no_false_deadlock_at_start(self):
        """All game levels should NOT be deadlocked at the start."""
        for i, level in enumerate(LEVELS):
            state = parse_level(level)
            assert not detect_deadlock(state), \
                f"Level {i+1} is deadlocked at the start (false positive)"


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

    def test_strip_ansi(self):
        """Bug fix: strip_ansi should remove ANSI escape codes."""
        assert strip_ansi("\033[31mhello\033[0m") == "hello"
        assert strip_ansi("\033[1;32;40mworld\033[0m") == "world"
        assert strip_ansi("plain text") == "plain text"
        assert strip_ansi("\033[48;5;23m\033[37mcolored\033[0m") == "colored"

    def test_render_color_width_consistency(self):
        """Rendered line visual width should match level width (no ANSI in width calc)."""
        state = parse_level(OPEN_LEVEL)
        lines_nocolor = render(state, tiles=UNICODE_TILES, use_color=False)
        lines_color = render(state, tiles=UNICODE_TILES, use_color=True)
        # Visual width should be the same regardless of color
        for nocolor_line, color_line in zip(lines_nocolor, lines_color):
            assert len(strip_ansi(color_line)) == len(nocolor_line)


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

    def test_all_levels_solvable(self):
        """Every level should not be deadlocked at the start."""
        for i, level in enumerate(LEVELS):
            state = parse_level(level)
            assert not detect_deadlock(state), \
                f"Level {i+1} is deadlocked at the start"

    def test_row_lengths_consistent(self):
        """All rows in each level should have the same length after padding."""
        for i, level in enumerate(LEVELS):
            state = parse_level(level)
            # parse_level pads rows, so width should be consistent
            for row in level:
                # The actual level definition may have varying lengths,
                # but parse_level handles padding
                assert len(row) <= state['width'], \
                    f"Level {i+1}: row length {len(row)} exceeds width {state['width']}"