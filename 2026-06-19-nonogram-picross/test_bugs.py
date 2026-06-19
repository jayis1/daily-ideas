#!/usr/bin/env python3
"""Bug hunting tests for nonogram.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from nonogram import *

print("=" * 60)
print("BUG HUNT: Edge case tests")
print("=" * 60)

# Test 1: Size 3 (minimum)
g, rc, cc = generate_puzzle(3, 3, "easy", seed=1)
print(f"1. 3x3 easy: {len(g)}x{len(g[0])}")

# Test 2: Size 2 boundary
try:
    g, rc, cc = generate_puzzle(2, 2, "easy", seed=1)
    print(f"2. 2x2: {len(g)}x{len(g[0])}")
except Exception as e:
    print(f"2. 2x2 error: {type(e).__name__}: {e}")

# Test 3: check_solution dimension mismatch
try:
    result = check_solution([[1]], [[1, 0]])
    print(f"3. dim mismatch result: {result}")
except Exception as e:
    print(f"3. dim mismatch error: {type(e).__name__}: {e}")

# Test 4: compute_progress empty
result = compute_progress([], [])
print(f"4. empty progress: {result}")

# Test 5: compute_progress mismatched sizes
try:
    result = compute_progress([[-1]], [[1, 0]])
    print(f"5. mismatched progress: {result}")
except Exception as e:
    print(f"5. mismatched error: {type(e).__name__}: {e}")

# Test 6: 1x1 solve
sol = solve_nonogram([[1]], [[1]])
print(f"6. 1x1 solve: {sol}")

# Test 7: Infeasible
sol = solve_nonogram([[5]], [[0], [0]])
print(f"7. infeasible: {sol}")

# Test 8: all-zero grid
grid = [[0,0,0],[0,0,0],[0,0,0]]
rc, cc = compute_clues(grid)
sol = solve_nonogram(rc, cc)
print(f"8. all-zero: {sol}, match: {sol == grid}")

# Test 9: mistake counting
game = NonogramGame(size=5, difficulty="easy", seed=42)
found = False
for r in range(5):
    for c in range(5):
        if game.solution[r][c] == 0:
            game.cursor_r = r
            game.cursor_c = c
            found = True
            break
    if found:
        break
old = game.mistakes
game.toggle_fill()
print(f"9. mistakes: {game.mistakes} (was {old})")

# Test 10: Non-square puzzle
g, rc, cc = generate_puzzle(3, 7, "easy", seed=1)
print(f"10. 3x7: {len(g)}x{len(g[0])}")

# Test 11: Save/load roundtrip
game = NonogramGame(size=5, difficulty="easy", seed=42)
json_str = save_game_state(game)
restored = load_game_state(json_str)
print(f"11. save/load: rows={restored.rows}, cols={restored.cols}")

# Test 12: load_game_state with bad player_grid dimensions
try:
    bad_json = '{"rows": 5, "cols": 5, "difficulty": "easy", "row_clues": [[1],[1],[1],[1],[1]], "col_clues": [[1],[1],[1],[1],[1]], "player_grid": [[1]], "cursor_r": 0, "cursor_c": 0, "hints_used": 0, "mistakes": 0}'
    load_game_state(bad_json)
    print("12. BAD: no error on corrupt dimensions")
except Exception as e:
    print(f"12. corrupt data: {type(e).__name__}: {e}")

# Test 13: Export/import roundtrip
g, rc, cc = generate_puzzle(5, 5, "easy", seed=42)
json_str = export_puzzle(rc, cc, 5, 5)
irc, icc, rows, cols = import_puzzle(json_str)
print(f"13. roundtrip: rows={rows}, cols={cols}, match={rc==irc and cc==icc}")

# Test 14: verify_unique_solution
grid = [[1, 0, 1], [0, 1, 0], [1, 0, 1]]
rc, cc = compute_clues(grid)
result = verify_unique_solution(rc, cc)
print(f"14. unique diagonal: {result}")

# Test 15: toggle_fill toggling behavior
game = NonogramGame(size=5, difficulty="easy", seed=42)
r, c = 0, 0
game.cursor_r = r
game.cursor_c = c
old_val = game.player_grid[r][c]
game.toggle_fill()
print(f"15a. toggle_fill: {old_val} -> {game.player_grid[r][c]}")
game.toggle_fill()
print(f"15b. toggle_fill again: {game.player_grid[r][c]}")
game.toggle_fill()
print(f"15c. toggle_fill again: {game.player_grid[r][c]}")

# Test 16: toggle_mark behavior
game2 = NonogramGame(size=5, difficulty="easy", seed=42)
r, c = 0, 0
game2.cursor_r = r
game2.cursor_c = c
old_val = game2.player_grid[r][c]
game2.toggle_mark()
print(f"16a. toggle_mark: {old_val} -> {game2.player_grid[r][c]}")
game2.toggle_mark()
print(f"16b. toggle_mark again: {game2.player_grid[r][c]}")

# Test 17: Undo behavior
game3 = NonogramGame(size=5, difficulty="easy", seed=42)
r, c = 0, 0
game3.cursor_r = r
game3.cursor_c = c
old_val = game3.player_grid[r][c]
game3.toggle_fill()
print(f"17a. Before undo: {game3.player_grid[r][c]}")
game3.undo()
print(f"17b. After undo: {game3.player_grid[r][c]} (should be {old_val})")

# Test 18: clear_cell behavior
game4 = NonogramGame(size=5, difficulty="easy", seed=42)
game4.cursor_r = 0
game4.cursor_c = 0
game4.toggle_fill()
print(f"18a. After fill: {game4.player_grid[0][0]}")
game4.clear_cell()
print(f"18b. After clear: {game4.player_grid[0][0]} (should be -1)")

# Test 19: generate_line_possibilities with clue [0]
poss = generate_line_possibilities([0], 5)
print(f"19. clue [0] len 5: {poss}")

# Test 20: generate_line_possibilities with empty clue []
try:
    poss = generate_line_possibilities([], 5)
    print(f"20. empty clue: {poss}")
except Exception as e:
    print(f"20. empty clue error: {type(e).__name__}: {e}")

# Test 21: Non-square game initialization
game5 = NonogramGame(size=5, difficulty="easy", seed=42)
print(f"21. Game rows={game5.rows}, cols={game5.cols}")

# Test 22: _is_row_complete and _is_col_complete
game6 = NonogramGame(size=5, difficulty="easy", seed=42)
# Initially nothing should be complete
for r in range(game6.rows):
    assert not game6._is_row_complete(r), f"Row {r} should not be complete initially"
for c in range(game6.cols):
    assert not game6._is_col_complete(c), f"Col {c} should not be complete initially"
print("22. Initially no rows/cols complete: OK")

# After solving, all should be complete
game6.auto_solve()
for r in range(game6.rows):
    assert game6._is_row_complete(r), f"Row {r} should be complete after solve"
for c in range(game6.cols):
    assert game6._is_col_complete(c), f"Col {c} should be complete after solve"
print("22. After auto_solve, all rows/cols complete: OK")

# Test 23: compute_progress after auto_solve
progress = compute_progress(game6.player_grid, game6.solution)
print(f"23. Progress after auto_solve: {progress} (should be 1.0)")

# Test 24: count_solutions for non-unique puzzle
# A puzzle with clue [1] in a 1x2 grid has 2 solutions
row_clues = [[1]]
col_clues = [[1], [1]]
solutions = count_solutions(row_clues, col_clues, max_count=10)
print(f"24. count_solutions for 1x2 [1] / [[1],[1]]: {len(solutions)} solutions")

# Test 25: Check that NonogramGame handles non-square properly
# (The constructor sets self.rows = self.cols = size, so it's always square via CLI)
# But generate_puzzle supports non-square
g, rc, cc = generate_puzzle(5, 10, "easy", seed=42)
print(f"25. Non-square 5x10: {len(g)}x{len(g[0])}, solvable: {solve_nonogram(rc, cc) is not None}")

# Test 26: Verify toggle_fill mistake counting when filling a correct cell
game7 = NonogramGame(size=5, difficulty="easy", seed=42)
# Find a cell that should be 1 in the solution
for r in range(5):
    for c in range(5):
        if game7.solution[r][c] == 1:
            game7.cursor_r = r
            game7.cursor_c = c
            break
    else:
        continue
    break
old_mistakes = game7.mistakes
game7.toggle_fill()
print(f"26. Correct fill mistakes: {game7.mistakes} (was {old_mistakes}, should be same)")

# Test 27: Verify that generate_puzzle always produces solvable puzzles
import random
for seed in range(50):
    g, rc, cc = generate_puzzle(5, 5, "easy", seed=seed)
    sol = solve_nonogram(rc, cc)
    if sol is None:
        print(f"27. FAIL: seed={seed} produces unsolvable puzzle!")
        break
else:
    print("27. All 50 easy seeds produce solvable puzzles: OK")

# Test 28: Test undo stack limit
game8 = NonogramGame(size=5, difficulty="easy", seed=42)
for i in range(1100):
    game8.cursor_r = 0
    game8.cursor_c = 0
    game8._push_undo(0, 0, game8.player_grid[0][0])
print(f"28. Undo stack size after 1100 pushes: {len(game8.undo_stack)} (should be <= 1000)")

# Test 29: Test that auto_solve sets game_won
game9 = NonogramGame(size=5, difficulty="easy", seed=42)
game9.auto_solve()
print(f"29. game_won after auto_solve: {game9.game_won}")

# Test 30: Test compute_progress with partially filled grid
grid_partial = [[-1, -1], [-1, -1]]
solution = [[1, 0], [0, 1]]
progress = compute_progress(grid_partial, solution)
print(f"30. Progress of empty grid: {progress} (should be 0.0)")

print("\n" + "=" * 60)
print("BUG HUNT COMPLETE")
print("=" * 60)