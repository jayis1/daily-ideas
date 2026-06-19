#!/usr/bin/env python3
"""Bug hunting tests for nonogram.py"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from nonogram import *
import nonogram as nm

print("=" * 60)
print("BUG HUNT: Detailed bug analysis")
print("=" * 60)

# Bug 1: check_solution with dimension mismatch raises IndexError instead of returning False
print("\nBug 1: check_solution dimension mismatch")
try:
    result = check_solution([[1]], [[1, 0]])
    print(f"  Result: {result}")
except IndexError as e:
    print(f"  IndexError: {e}")
    print("  BUG: should return False, not crash with IndexError")

# Bug 2: compute_progress with mismatched dimensions raises IndexError
print("\nBug 2: compute_progress dimension mismatch")
try:
    result = compute_progress([[-1]], [[1, 0]])
    print(f"  Result: {result}")
except IndexError as e:
    print(f"  IndexError: {e}")
    print("  BUG: should handle gracefully")

# Bug 3: load_game_state with wrong player_grid dimensions crashes with IndexError
print("\nBug 3: load_game_state corrupt data")
try:
    bad_json = '{"rows": 5, "cols": 5, "difficulty": "easy", "row_clues": [[1],[1],[1],[1],[1]], "col_clues": [[1],[1],[1],[1],[1]], "player_grid": [[1]], "cursor_r": 0, "cursor_c": 0, "hints_used": 0, "mistakes": 0}'
    load_game_state(bad_json)
    print("  No error (BAD)")
except IndexError as e:
    print(f"  IndexError: {e}")
    print("  BUG: should raise ValueError, not IndexError")

# Bug 4: generate_line_possibilities with empty clue []
print("\nBug 4: empty clue []")
poss = generate_line_possibilities([], 5)
print(f"  Empty clue: {poss}")
print(f"  Clue [0]: {generate_line_possibilities([0], 5)}")

# Bug 5: Non-unique puzzle detection
print("\nBug 5: Non-unique puzzle")
solutions = count_solutions([[1], [1]], [[1], [1]], max_count=10)
print(f"  2x2 [1],[1] / [1],[1]: {len(solutions)} solutions")
for s in solutions:
    print(f"    {s}")

# Bug 6: toggle_fill mistake counting - filling wrong cell then toggling back doesn't undo mistake count
print("\nBug 6: mistake count not decremented on undo")
game = NonogramGame(size=5, difficulty="easy", seed=42)
# Find an empty cell in solution
for r in range(5):
    for c in range(5):
        if game.solution[r][c] == 0:
            game.cursor_r = r
            game.cursor_c = c
            break
    else:
        continue
    break
print(f"  Mistakes before: {game.mistakes}")
game.toggle_fill()  # Wrong fill
print(f"  Mistakes after wrong fill: {game.mistakes}")
game.undo()  # Undo
print(f"  Mistakes after undo: {game.mistakes}")
print("  BUG: mistakes count should NOT be decremented by undo (this is actually fine - mistakes are permanent)")

# Bug 7: cursor_r/cursor_c not validated in NonogramGame
print("\nBug 7: cursor bounds")
game2 = NonogramGame(size=5, difficulty="easy", seed=42)
game2.move_cursor(0, 100)  # Should clamp
print(f"  cursor_c after move right 100: {game2.cursor_c} (should be 4)")
game2.move_cursor(-100, 0)  # Should clamp
print(f"  cursor_r after move up 100: {game2.cursor_r} (should be 0)")

# Bug 8: _is_row_complete and _is_col_complete use strict equality
# A row with X-marks (0) where solution has 0 is "complete" but may be confusing
print("\nBug 8: Row completion with X-marks")
game3 = NonogramGame(size=5, difficulty="easy", seed=42)
# Mark all empty cells with X (0)
for r in range(5):
    for c in range(5):
        if game3.solution[r][c] == 0:
            game3.player_grid[r][c] = 0
# Now check if rows with all X marks but no filled cells are "complete"
for r in range(5):
    has_filled = any(game3.solution[r][c] == 1 for c in range(5))
    if not has_filled:
        print(f"  Row {r} has no filled cells, complete: {game3._is_row_complete(r)}")

# Bug 9: Test print_puzzle with _NO_COLOR flag
print("\nBug 9: _NO_COLOR flag is not used in Style or print functions")
print(f"  _NO_COLOR = {nm._NO_COLOR}")
print("  The code uses Style constants but never checks _NO_COLOR in draw() or print_puzzle()")
print("  This means --no-color flag has NO EFFECT on output!")

# Bug 10: Test generate_puzzle with seed=None (non-deterministic fallback)
print("\nBug 10: generate_puzzle fallback behavior")
print("  If all 200 attempts fail uniqueness check, fallback generates without uniqueness check")
print("  This could produce a non-unique puzzle for easy/medium difficulty")

# Bug 11: The NonogramGame constructor only accepts size (always square)
print("\nBug 11: NonogramGame always creates square puzzles")
print("  NonogramGame.__init__ takes only 'size' param, sets rows=cols=size")
print("  This means you can't play rectangular puzzles interactively")

# Bug 12: Test that save_game_state captures elapsed time correctly
print("\nBug 12: save_game_state elapsed time")
game4 = NonogramGame(size=5, difficulty="easy", seed=42)
import time
time.sleep(0.1)
json_str = save_game_state(game4)
data = json.loads(json_str)
print(f"  Elapsed in save: {data.get('elapsed', 'MISSING')}")

# Bug 13: import_puzzle with negative rows
print("\nBug 13: import_puzzle with negative rows")
try:
    import_puzzle('{"rows": -1, "cols": 5, "row_clues": [], "col_clues": []}')
except ValueError as e:
    print(f"  Correctly raises ValueError: {e}")

# Bug 14: import_puzzle with row_clues as strings instead of lists
print("\nBug 14: import_puzzle with string clues")
try:
    import_puzzle('{"rows": 1, "cols": 1, "row_clues": [["a"]], "col_clues": [["a"]]}')
    sol = solve_nonogram([["a"]], [["a"]])
    print(f"  String clues: solvable? {sol}")
except Exception as e:
    print(f"  Error with string clues: {type(e).__name__}: {e}")

# Bug 15: NonogramGame with size=0 or negative
print("\nBug 15: NonogramGame with invalid size")
try:
    game5 = NonogramGame(size=0)
    print(f"  size=0: rows={game5.rows}, cols={game5.cols}")
except Exception as e:
    print(f"  size=0 error: {type(e).__name__}: {e}")

# Bug 16: Check if generate_puzzle handles difficulty strings correctly
print("\nBug 16: Invalid difficulty")
try:
    g, rc, cc = generate_puzzle(5, 5, "invalid_difficulty", seed=42)
    print(f"  Invalid difficulty generated grid: {len(g)}x{len(g[0])}")
    print("  BUG: should reject invalid difficulty")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

# Bug 17: Test compute_clues with empty grid (0 rows)
print("\nBug 17: compute_clues with empty grid")
try:
    rc, cc = compute_clues([])
    print(f"  Empty grid clues: rows={rc}, cols={cc}")
except Exception as e:
    print(f"  Empty grid error: {type(e).__name__}: {e}")

# Bug 18: Test that the --load flag works with the CLI
print("\nBug 18: CLI --load flag parsing")
# This is tested in test_nonogram.py already

# Bug 19: Test that print_puzzle doesn't crash with empty grid
print("\nBug 19: print_puzzle with 1x1")
try:
    print_puzzle([[1]], [[1]], 1, 1, grid=[[1]])
    print("  1x1 print: OK")
except Exception as e:
    print(f"  1x1 print error: {type(e).__name__}: {e}")

# Bug 20: Test that the game handles very large sizes gracefully
print("\nBug 20: Very large size (30)")
import signal
def handler(signum, frame):
    raise TimeoutError("Timeout")
try:
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(30)  # 30 second timeout
    g, rc, cc = generate_puzzle(25, 25, "hard", seed=1)
    sol = solve_nonogram(rc, cc, timeout=10)
    print(f"  25x25 hard: solvable={sol is not None}")
except TimeoutError:
    print("  25x25 hard: TIMEOUT")
finally:
    signal.alarm(0)

print("\n" + "=" * 60)
print("BUG HUNT COMPLETE")
print("=" * 60)