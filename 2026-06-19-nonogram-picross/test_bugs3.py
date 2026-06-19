#!/usr/bin/env python3
"""Additional bug hunting tests"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from nonogram import *
import nonogram as nm

# Bug 15: NonogramGame with size=0 or negative
print("Bug 15: NonogramGame with size=0...")
try:
    game = NonogramGame(size=0)
    print(f"  size=0: rows={game.rows}, cols={game.cols}")
except ZeroDivisionError as e:
    print(f"  size=0: ZeroDivisionError - {e}")
    print("  BUG: should validate size in constructor")

# Bug 16: Invalid difficulty in generate_puzzle
print("\nBug 16: Invalid difficulty...")
try:
    g, rc, cc = generate_puzzle(5, 5, "invalid", seed=42)
    print(f"  Invalid difficulty generated: {len(g)}x{len(g[0])}")
    print("  BUG: should reject invalid difficulty")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

# Bug 3 detailed: load_game_state with wrong player_grid dimensions
print("\nBug 3: load_game_state dimension validation...")
bad_json = '{"rows": 5, "cols": 5, "difficulty": "easy", "row_clues": [[1],[1],[1],[1],[1]], "col_clues": [[1],[1],[1],[1],[1]], "player_grid": [[1]], "cursor_r": 0, "cursor_c": 0, "hints_used": 0, "mistakes": 0}'
try:
    game = load_game_state(bad_json)
    print(f"  player_grid[0][0] = {game.player_grid[0][0]}")
    print(f"  player_grid rows: {len(game.player_grid)}")
    print("  BUG: load_game_state accepted malformed player_grid")
except IndexError as e:
    print(f"  IndexError on access: {e}")
    print("  BUG: load_game_state should validate player_grid dimensions")
except ValueError as e:
    print(f"  ValueError: {e}")

# Bug 17: NonogramGame with size=1
print("\nBug 17: NonogramGame with size=1...")
try:
    game = NonogramGame(size=1)
    print(f"  size=1: rows={game.rows}, cols={game.cols}")
except ZeroDivisionError as e:
    print(f"  size=1: ZeroDivisionError - {e}")
except Exception as e:
    print(f"  size=1: {type(e).__name__}: {e}")

# Bug 18: check_solution with None values
print("\nBug 18: check_solution edge cases...")
# Test with a player_grid that has a cell set to None
try:
    result = check_solution([[None]], [[1]])
    print(f"  check_solution with None: {result}")
except Exception as e:
    print(f"  check_solution with None: {type(e).__name__}: {e}")

# Bug 19: get_hint randomness (uses module random, not seeded)
print("\nBug 19: get_hint uses random.choice (module-level random)")
import random
random.seed(42)
grid = [[-1, -1], [-1, -1]]
solution = [[1, 0], [0, 1]]
hint1, wrong1 = get_hint(grid, solution)
print(f"  Hint 1: {hint1}, wrong: {wrong1}")

# Bug 20: Test that the game properly handles --solve with --puzzle
print("\nBug 20: Test CLI --solve --puzzle")
puzzle_json = '{"rows": 5, "cols": 5, "row_clues": [[3],[5],[5],[5],[3]], "col_clues": [[3],[5],[5],[5],[3]]}'
import_and_solve(puzzle_json, solve=True)
print("  --solve --puzzle: OK")

# Bug 21: Test that generate_and_display works
print("\nBug 21: generate_and_display")
generate_and_display(5, "easy", seed=42)

# Bug 22: Test NonogramGame with size=2
print("\nBug 22: NonogramGame with size=2...")
try:
    game = NonogramGame(size=2)
    print(f"  size=2: rows={game.rows}, cols={game.cols}")
except Exception as e:
    print(f"  size=2: {type(e).__name__}: {e}")

# Bug 23: Test compute_clues with empty grid
print("\nBug 23: compute_clues with empty grid...")
try:
    rc, cc = compute_clues([])
    print(f"  Empty grid: row_clues={rc}, col_clues={cc}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

# Bug 24: Test solve_nonogram with empty clues
print("\nBug 24: solve_nonogram with empty clues...")
try:
    sol = solve_nonogram([], [])
    print(f"  Empty clues solution: {sol}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

# Bug 25: Test generate_pattern with empty grid
print("\nBug 25: generate_pattern with 0x0...")
try:
    pattern = generate_pattern(0, 0, "easy")
    print(f"  0x0 pattern: {pattern}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

# Bug 26: Test verify_unique_solution with empty clues
print("\nBug 26: verify_unique_solution with empty...")
try:
    result = verify_unique_solution([], [])
    print(f"  Empty verify_unique: {result}")
except Exception as e:
    print(f"  Error: {type(e).__name__}: {e}")

# Bug 27: Test toggle_fill when cell is already filled correctly
print("\nBug 27: toggle_fill on already-correct cell...")
game = NonogramGame(size=5, difficulty="easy", seed=42)
for r in range(5):
    for c in range(5):
        if game.solution[r][c] == 1:
            game.cursor_r = r
            game.cursor_c = c
            break
    else:
        continue
    break
game.toggle_fill()  # Fill correctly
old_mistakes = game.mistakes
game.toggle_fill()  # Toggle off
print(f"  Mistakes after toggling off: {game.mistakes} (was {old_mistakes})")
print(f"  Cell value after toggling off: {game.player_grid[r][c]} (should be -1)")

# Bug 28: Test the _is_row_complete with partially filled rows
print("\nBug 28: _is_row_complete with partial fill...")
game2 = NonogramGame(size=5, difficulty="easy", seed=42)
# Fill only some cells correctly
for c in range(game2.cols):
    if game2.solution[0][c] == 1:
        game2.player_grid[0][c] = 1
print(f"  Row 0 complete (partial fill): {game2._is_row_complete(0)}")

print("\nAll additional bug tests completed.")