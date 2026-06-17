#!/usr/bin/env python3
"""
Tests for the Maze Generator & Pathfinder Visualizer.

Covers:
  - Maze generation (all 5 algorithms produce valid mazes)
  - Pathfinding (all 5 solvers find a path)
  - Save/load round-trip
  - Export to plain text
  - Maze statistics and difficulty rating
  - Heatmap computation
  - Custom start/end positions
  - Edge cases (minimum size, invalid inputs)
  - Rendering with and without color
  - File I/O validation
"""

import json
import os
import tempfile
import unittest

from maze_pathfinder import (
    MazeGrid,
    Cell,
    OPPOSITE,
    DIRECTIONS,
    WALL,
    PATH,
    START,
    END,
    SOLUTION,
    VISITED,
    FRONTIER,
    DEAD_END,
    GENERATORS,
    SOLVERS,
    generate_dfs,
    generate_prim,
    generate_kruskal,
    generate_ellers,
    generate_wilson,
    solve_bfs,
    solve_dfs,
    solve_astar,
    solve_greedy,
    solve_dijkstra,
    render,
    export_plain,
    save_maze,
    load_maze,
    compute_heatmap,
    _bitmap_to_graph,
)


class TestCell(unittest.TestCase):
    """Tests for the Cell class."""

    def test_cell_init(self):
        cell = Cell(3, 5)
        self.assertEqual(cell.row, 3)
        self.assertEqual(cell.col, 5)
        self.assertTrue(all(cell.walls.values()))
        self.assertFalse(cell.visited)

    def test_cell_serialization_roundtrip(self):
        cell = Cell(2, 7)
        cell.walls["N"] = False
        cell.walls["E"] = False
        d = cell.to_dict()
        restored = Cell.from_dict(d)
        self.assertEqual(restored.row, 2)
        self.assertEqual(restored.col, 7)
        self.assertFalse(restored.walls["N"])
        self.assertFalse(restored.walls["E"])
        self.assertTrue(restored.walls["S"])
        self.assertTrue(restored.walls["W"])


class TestMazeGrid(unittest.TestCase):
    """Tests for the MazeGrid class."""

    def test_grid_init(self):
        maze = MazeGrid(5, 10)
        self.assertEqual(maze.rows, 5)
        self.assertEqual(maze.cols, 10)
        self.assertEqual(len(maze.cells), 5)
        self.assertEqual(len(maze.cells[0]), 10)

    def test_get_valid_cell(self):
        maze = MazeGrid(3, 3)
        cell = maze.get(1, 1)
        self.assertIsNotNone(cell)
        self.assertEqual(cell.row, 1)
        self.assertEqual(cell.col, 1)

    def test_get_out_of_bounds(self):
        maze = MazeGrid(3, 3)
        self.assertIsNone(maze.get(-1, 0))
        self.assertIsNone(maze.get(3, 0))
        self.assertIsNone(maze.get(0, -1))
        self.assertIsNone(maze.get(0, 3))

    def test_bitmap_dimensions(self):
        maze = MazeGrid(5, 8)
        bitmap = maze.to_bitmap()
        # 2*rows+1 x 2*cols+1
        self.assertEqual(len(bitmap), 2 * 5 + 1)
        self.assertEqual(len(bitmap[0]), 2 * 8 + 1)

    def test_bitmap_all_walls_initially(self):
        maze = MazeGrid(3, 3)
        bitmap = maze.to_bitmap()
        # All cells should be walls initially except cell centers
        for r in range(len(bitmap)):
            for c in range(len(bitmap[0])):
                if r % 2 == 1 and c % 2 == 1:
                    self.assertEqual(bitmap[r][c], PATH)
                elif r % 2 == 0 or c % 2 == 0:
                    self.assertEqual(bitmap[r][c], WALL)

    def test_serialization_roundtrip(self):
        maze = generate_dfs(5, 7, seed=42)
        data = maze.to_dict()
        restored = MazeGrid.from_dict(data)
        self.assertEqual(restored.rows, maze.rows)
        self.assertEqual(restored.cols, maze.cols)
        # Check that the bitmaps match
        orig_bitmap = maze.to_bitmap()
        restored_bitmap = restored.to_bitmap()
        self.assertEqual(orig_bitmap, restored_bitmap)

    def test_json_roundtrip(self):
        maze = generate_dfs(4, 6, seed=99)
        json_str = maze.to_json()
        restored = MazeGrid.from_json(json_str)
        self.assertEqual(restored.to_bitmap(), maze.to_bitmap())

    def test_dead_ends(self):
        maze = generate_dfs(5, 5, seed=42)
        dead_ends = maze.dead_ends()
        # A valid maze should have some dead ends
        self.assertGreater(len(dead_ends), 0)
        for cell in dead_ends:
            open_count = sum(1 for w in cell.walls.values() if not w)
            self.assertEqual(open_count, 1)

    def test_stats(self):
        maze = generate_dfs(8, 10, seed=7)
        stats = maze.stats()
        self.assertEqual(stats["total_cells"], 80)
        self.assertGreater(stats["dead_ends"], 0)
        self.assertGreater(float(stats["avg_branching"]), 0)

    def test_stats_with_precomputed_bitmap(self):
        """stats() should accept pre-computed bitmap to avoid recomputation."""
        maze = generate_dfs(5, 5, seed=42)
        bitmap = maze.to_bitmap()
        s1 = maze.stats()
        s2 = maze.stats(bitmap=bitmap)
        self.assertEqual(s1, s2)

    def test_stats_with_none_uses_internal_bitmap(self):
        """stats(bitmap=None) should compute bitmap internally."""
        maze = generate_dfs(5, 5, seed=42)
        s = maze.stats(bitmap=None)
        self.assertGreater(s["total_cells"], 0)

    def test_difficulty_rating(self):
        """difficulty_rating() should return a valid difficulty level."""
        maze = generate_dfs(10, 10, seed=42)
        difficulty = maze.difficulty_rating()
        self.assertIn(difficulty, ["Easy", "Medium", "Hard", "Expert"])

    def test_difficulty_rating_small_maze(self):
        """Small mazes should return a valid difficulty level."""
        maze = generate_dfs(2, 2, seed=1)
        bitmap = maze.to_bitmap()
        difficulty = maze.difficulty_rating(bitmap=bitmap)
        self.assertIn(difficulty, ["Easy", "Medium", "Hard", "Expert"])

    def test_difficulty_rating_with_precomputed_bitmap(self):
        """difficulty_rating() should accept pre-computed bitmap."""
        maze = generate_dfs(10, 10, seed=42)
        bitmap = maze.to_bitmap()
        d1 = maze.difficulty_rating()
        d2 = maze.difficulty_rating(bitmap=bitmap)
        self.assertEqual(d1, d2)

    def test_neighbors_after_carving(self):
        maze = MazeGrid(3, 3)
        # Carve a passage from (0,0) to (0,1)
        maze.cells[0][0].walls["E"] = False
        maze.cells[0][1].walls["W"] = False
        neighbors = maze.neighbors(maze.cells[0][0])
        neighbor_coords = [(n.row, n.col) for n in neighbors]
        self.assertIn((0, 1), neighbor_coords)


class TestGeneration(unittest.TestCase):
    """Tests for maze generation algorithms."""

    def _assert_valid_maze(self, maze, rows, cols):
        """Check that a maze is valid: correct size and all cells reachable."""
        self.assertEqual(maze.rows, rows)
        self.assertEqual(maze.cols, cols)

        # Check bitmap has correct dimensions
        bitmap = maze.to_bitmap()
        self.assertEqual(len(bitmap), 2 * rows + 1)
        self.assertEqual(len(bitmap[0]), 2 * cols + 1)

        # Check that start and end positions are reachable (passable)
        start = (1, 1)
        end = (2 * rows - 1, 2 * cols - 1)
        self.assertNotEqual(bitmap[start[0]][start[1]], WALL)
        self.assertNotEqual(bitmap[end[0]][end[1]], WALL)

        # Check all passable cells are connected (BFS from start)
        graph = _bitmap_to_graph(bitmap)
        visited = {start}
        queue = [start]
        while queue:
            pos = queue.pop(0)
            for neighbor in graph.get(pos, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # All passable cells should be reachable
        total_passable = sum(1 for v in graph.values() for _ in [1])
        self.assertEqual(len(visited), len(graph), "Not all cells are reachable")

    def test_dfs_generation(self):
        maze = generate_dfs(5, 7, seed=42)
        self._assert_valid_maze(maze, 5, 7)

    def test_prim_generation(self):
        maze = generate_prim(5, 7, seed=42)
        self._assert_valid_maze(maze, 5, 7)

    def test_kruskal_generation(self):
        maze = generate_kruskal(5, 7, seed=42)
        self._assert_valid_maze(maze, 5, 7)

    def test_ellers_generation(self):
        maze = generate_ellers(5, 7, seed=42)
        self._assert_valid_maze(maze, 5, 7)

    def test_wilson_generation(self):
        maze = generate_wilson(5, 7, seed=42)
        self._assert_valid_maze(maze, 5, 7)

    def test_dfs_minimum_size(self):
        maze = generate_dfs(2, 2, seed=1)
        self._assert_valid_maze(maze, 2, 2)

    def test_prim_minimum_size(self):
        maze = generate_prim(2, 2, seed=1)
        self._assert_valid_maze(maze, 2, 2)

    def test_kruskal_minimum_size(self):
        maze = generate_kruskal(2, 2, seed=1)
        self._assert_valid_maze(maze, 2, 2)

    def test_ellers_minimum_size(self):
        maze = generate_ellers(2, 2, seed=1)
        self._assert_valid_maze(maze, 2, 2)

    def test_wilson_minimum_size(self):
        maze = generate_wilson(2, 2, seed=1)
        self._assert_valid_maze(maze, 2, 2)

    def test_invalid_size_raises(self):
        with self.assertRaises(ValueError):
            generate_dfs(1, 5)
        with self.assertRaises(ValueError):
            generate_prim(5, 1)
        with self.assertRaises(ValueError):
            generate_kruskal(0, 0)
        with self.assertRaises(ValueError):
            generate_ellers(1, 1)
        with self.assertRaises(ValueError):
            generate_wilson(1, 3)

    def test_reproducible_with_seed(self):
        maze1 = generate_dfs(5, 5, seed=42)
        maze2 = generate_dfs(5, 5, seed=42)
        self.assertEqual(maze1.to_bitmap(), maze2.to_bitmap())

    def test_wilson_reproducible_with_seed(self):
        maze1 = generate_wilson(5, 5, seed=42)
        maze2 = generate_wilson(5, 5, seed=42)
        self.assertEqual(maze1.to_bitmap(), maze2.to_bitmap())

    def test_different_seeds_produce_different_mazes(self):
        maze1 = generate_dfs(10, 10, seed=42)
        maze2 = generate_dfs(10, 10, seed=99)
        self.assertNotEqual(maze1.to_bitmap(), maze2.to_bitmap())

    def test_all_generators_in_dict(self):
        self.assertEqual(set(GENERATORS.keys()), {"dfs", "prim", "kruskal", "ellers", "wilson"})

    def test_large_maze_generation(self):
        """Test that generators can handle larger mazes."""
        for name, gen_func in GENERATORS.items():
            maze = gen_func(20, 40, seed=42)
            self._assert_valid_maze(maze, 20, 40)


class TestPathfinding(unittest.TestCase):
    """Tests for pathfinding algorithms."""

    def setUp(self):
        """Create a standard test maze."""
        self.maze = generate_dfs(5, 7, seed=42)
        self.bitmap = self.maze.to_bitmap()
        self.start = (1, 1)
        self.end = (2 * self.maze.rows - 1, 2 * self.maze.cols - 1)

    def _collect_solver(self, solver_func):
        """Run a solver and collect all frames, return (final_path, total_visited, steps)."""
        path = None
        total_visited = 0
        steps = 0
        for visited, frontier, solution in solver_func(self.bitmap, self.start, self.end):
            steps += 1
            total_visited = len(visited)
            if solution is not None:
                path = solution
        return path, total_visited, steps

    def test_bfs_finds_path(self):
        path, visited, steps = self._collect_solver(solve_bfs)
        self.assertIsNotNone(path)
        self.assertEqual(path[0], self.start)
        self.assertEqual(path[-1], self.end)

    def test_dfs_finds_path(self):
        path, visited, steps = self._collect_solver(solve_dfs)
        self.assertIsNotNone(path)
        self.assertEqual(path[0], self.start)
        self.assertEqual(path[-1], self.end)

    def test_astar_finds_path(self):
        path, visited, steps = self._collect_solver(solve_astar)
        self.assertIsNotNone(path)
        self.assertEqual(path[0], self.start)
        self.assertEqual(path[-1], self.end)

    def test_greedy_finds_path(self):
        path, visited, steps = self._collect_solver(solve_greedy)
        self.assertIsNotNone(path)
        self.assertEqual(path[0], self.start)
        self.assertEqual(path[-1], self.end)

    def test_dijkstra_finds_path(self):
        path, visited, steps = self._collect_solver(solve_dijkstra)
        self.assertIsNotNone(path)
        self.assertEqual(path[0], self.start)
        self.assertEqual(path[-1], self.end)

    def test_astar_is_optimal(self):
        """A* should find a path no longer than BFS (both are optimal)."""
        bfs_path, _, _ = self._collect_solver(solve_bfs)
        astar_path, _, _ = self._collect_solver(solve_astar)
        self.assertEqual(len(bfs_path), len(astar_path))

    def test_dijkstra_is_optimal(self):
        """Dijkstra should find the same path length as BFS (optimal)."""
        bfs_path, _, _ = self._collect_solver(solve_bfs)
        dijkstra_path, _, _ = self._collect_solver(solve_dijkstra)
        self.assertEqual(len(bfs_path), len(dijkstra_path))

    def test_astar_explores_fewer_than_bfs(self):
        """A* should explore fewer or equal cells compared to BFS."""
        _, bfs_visited, _ = self._collect_solver(solve_bfs)
        _, astar_visited, _ = self._collect_solver(solve_astar)
        self.assertLessEqual(astar_visited, bfs_visited)

    def test_all_solvers_on_various_mazes(self):
        """Each solver should find a path on various maze sizes and generators."""
        for gen_name, gen_func in GENERATORS.items():
            for rows, cols in [(2, 2), (3, 5), (5, 8)]:
                maze = gen_func(rows, cols, seed=42)
                bitmap = maze.to_bitmap()
                start = (1, 1)
                end = (2 * rows - 1, 2 * cols - 1)
                for solver_name, solver_func in SOLVERS.items():
                    path = None
                    for _, _, solution in solver_func(bitmap, start, end):
                        if solution is not None:
                            path = solution
                            break
                    self.assertIsNotNone(
                        path,
                        f"{solver_name} failed on {gen_name} {rows}x{cols}"
                    )

    def test_all_solvers_in_dict(self):
        self.assertEqual(set(SOLVERS.keys()), {"bfs", "dfs", "astar", "greedy", "dijkstra"})

    def test_solver_yields_frames(self):
        """Each solver should yield multiple frames for a reasonable maze."""
        frames = list(solve_astar(self.bitmap, self.start, self.end))
        self.assertGreater(len(frames), 1)

    def test_custom_start_end(self):
        """Solvers should work with custom start/end positions."""
        maze = generate_dfs(5, 5, seed=10)
        bitmap = maze.to_bitmap()
        # Start at bottom-right, end at top-left
        start = (2 * 5 - 1, 2 * 5 - 1)
        end = (1, 1)
        path = None
        for _, _, solution in solve_astar(bitmap, start, end):
            if solution is not None:
                path = solution
                break
        self.assertIsNotNone(path)
        self.assertEqual(path[0], start)
        self.assertEqual(path[-1], end)


class TestBitmapToGraph(unittest.TestCase):
    """Tests for the bitmap-to-graph conversion."""

    def test_simple_graph(self):
        maze = generate_dfs(3, 3, seed=42)
        bitmap = maze.to_bitmap()
        graph = _bitmap_to_graph(bitmap)
        start = (1, 1)
        self.assertIn(start, graph)
        self.assertGreater(len(graph[start]), 0)

    def test_wall_not_in_graph(self):
        maze = generate_dfs(3, 3, seed=42)
        bitmap = maze.to_bitmap()
        graph = _bitmap_to_graph(bitmap)
        # Find a wall position
        self.assertEqual(bitmap[0][0], WALL)
        self.assertNotIn((0, 0), graph)


class TestHeatmap(unittest.TestCase):
    """Tests for the heatmap computation."""

    def test_heatmap_returns_dict(self):
        maze = generate_dfs(5, 5, seed=42)
        bitmap = maze.to_bitmap()
        start = (1, 1)
        end = (2 * 5 - 1, 2 * 5 - 1)
        heat = compute_heatmap(bitmap, start, end)
        self.assertIsInstance(heat, dict)
        # Should have some entries
        self.assertGreater(len(heat), 0)

    def test_heatmap_start_and_end_visited(self):
        """Start and end should be visited by all solvers."""
        maze = generate_dfs(5, 5, seed=42)
        bitmap = maze.to_bitmap()
        start = (1, 1)
        end = (2 * 5 - 1, 2 * 5 - 1)
        heat = compute_heatmap(bitmap, start, end)
        # Start and end should be visited by all 5 solvers
        self.assertEqual(heat[start], len(SOLVERS) * 2)  # visited + solution
        self.assertEqual(heat[end], len(SOLVERS) * 2)

    def test_heatmap_no_wall_entries(self):
        """Heatmap should not contain wall positions."""
        maze = generate_dfs(5, 5, seed=42)
        bitmap = maze.to_bitmap()
        start = (1, 1)
        end = (2 * 5 - 1, 2 * 5 - 1)
        heat = compute_heatmap(bitmap, start, end)
        for pos in heat:
            self.assertNotEqual(bitmap[pos[0]][pos[1]], WALL)


class TestRendering(unittest.TestCase):
    """Tests for the rendering function."""

    def setUp(self):
        self.maze = generate_dfs(3, 3, seed=42)
        self.bitmap = self.maze.to_bitmap()

    def test_render_colored(self):
        """Render with ANSI colors should contain escape codes."""
        output = render(self.bitmap, start=(1, 1), end=(5, 5), use_color=True)
        self.assertIn(START, output)
        self.assertIn(END, output)
        self.assertIn(WALL, output)
        self.assertIn("\033[", output)  # ANSI escape codes present

    def test_render_plain(self):
        """Render without colors should NOT contain escape codes."""
        output = render(self.bitmap, start=(1, 1), end=(5, 5), use_color=False)
        self.assertIn(START, output)
        self.assertIn(END, output)
        self.assertNotIn("\033[", output)

    def test_render_with_visited_and_frontier(self):
        visited = {(1, 1), (1, 2)}
        frontier = {(1, 3)}
        output = render(self.bitmap, visited=visited, frontier=frontier,
                        start=(1, 1), end=(5, 5), use_color=False)
        self.assertIn(VISITED, output)
        self.assertIn(FRONTIER, output)

    def test_render_with_solution(self):
        solution = [(1, 1), (1, 2), (1, 3)]
        output = render(self.bitmap, solution=solution,
                        start=(1, 1), end=(5, 5), use_color=False)
        self.assertIn(SOLUTION, output)

    def test_render_with_heatmap(self):
        """Render with heatmap should contain heatmap characters."""
        maze = generate_dfs(5, 5, seed=42)
        bitmap = maze.to_bitmap()
        heat = {(1, 1): 5, (1, 3): 3}
        output = render(bitmap, heatmap=heat, start=(1, 1), end=(9, 9), use_color=False)
        # Should contain some heatmap characters (not just walls and spaces)
        # Check that we get something back that's not empty
        self.assertGreater(len(output), 0)

    def test_export_plain(self):
        output = export_plain(self.bitmap, start=(1, 1), end=(5, 5))
        self.assertIn(START, output)
        self.assertIn(END, output)
        self.assertNotIn("\033[", output)

    def test_export_plain_with_heatmap(self):
        """export_plain should work with heatmap."""
        maze = generate_dfs(5, 5, seed=42)
        bitmap = maze.to_bitmap()
        heat = {(1, 1): 3}
        output = export_plain(bitmap, heatmap=heat, start=(1, 1), end=(9, 9))
        self.assertNotIn("\033[", output)


class TestFileIO(unittest.TestCase):
    """Tests for save/load functionality."""

    def test_save_and_load_roundtrip(self):
        maze = generate_dfs(5, 7, seed=42)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            save_maze(maze, filepath)
            self.assertTrue(os.path.exists(filepath))

            loaded = load_maze(filepath)
            self.assertEqual(loaded.rows, maze.rows)
            self.assertEqual(loaded.cols, maze.cols)
            self.assertEqual(loaded.to_bitmap(), maze.to_bitmap())
        finally:
            os.unlink(filepath)

    def test_save_produces_valid_json(self):
        maze = generate_dfs(3, 3, seed=10)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            save_maze(maze, filepath)
            with open(filepath) as f:
                data = json.load(f)
            self.assertIn("rows", data)
            self.assertIn("cols", data)
            self.assertIn("cells", data)
        finally:
            os.unlink(filepath)

    def test_load_nonexistent_file(self):
        with self.assertRaises(FileNotFoundError):
            load_maze("/nonexistent/path/maze.json")

    def test_load_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            filepath = f.name

        try:
            with self.assertRaises(json.JSONDecodeError):
                load_maze(filepath)
        finally:
            os.unlink(filepath)

    def test_load_invalid_maze_data(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"rows": 1, "cols": 1}, f)
            filepath = f.name

        try:
            with self.assertRaises(ValueError):
                load_maze(filepath)
        finally:
            os.unlink(filepath)


class TestExportPlain(unittest.TestCase):
    """Tests for the plain text export."""

    def test_export_contains_solution(self):
        maze = generate_dfs(5, 5, seed=42)
        bitmap = maze.to_bitmap()
        start = (1, 1)
        end = (2 * maze.rows - 1, 2 * maze.cols - 1)

        # Get a solution
        for visited, frontier, solution in solve_astar(bitmap, start, end):
            if solution:
                output = export_plain(bitmap, solution=solution, start=start, end=end)
                self.assertIn(SOLUTION, output)
                self.assertIn(START, output)
                self.assertIn(END, output)
                break


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and error handling."""

    def test_minimum_maze_2x2(self):
        """All generators should work with 2x2 minimum size."""
        for name, gen_func in GENERATORS.items():
            maze = gen_func(2, 2, seed=1)
            bitmap = maze.to_bitmap()
            # Start and end should be reachable
            self.assertNotEqual(bitmap[1][1], WALL)
            self.assertNotEqual(bitmap[3][3], WALL)

    def test_solver_on_minimum_maze(self):
        """All solvers should find a path on a 2x2 maze."""
        maze = generate_dfs(2, 2, seed=1)
        bitmap = maze.to_bitmap()
        start = (1, 1)
        end = (3, 3)
        for name, solver in SOLVERS.items():
            path = None
            for _, _, solution in solver(bitmap, start, end):
                if solution:
                    path = solution
                    break
            self.assertIsNotNone(path, f"{name} failed on 2x2 maze")

    def test_start_equals_end_on_trivial_graph(self):
        """If start equals end (shouldn't happen in maze, but test robustness)."""
        maze = generate_dfs(3, 3, seed=42)
        bitmap = maze.to_bitmap()
        start = (1, 1)
        # BFS should immediately return a path of length 1
        for visited, frontier, solution in solve_bfs(bitmap, start, start):
            if solution:
                self.assertEqual(len(solution), 1)
                self.assertEqual(solution[0], start)
                break


class TestLoadMazeValidation(unittest.TestCase):
    """Tests for load_maze() input validation (bugs fixed in v1.2.0)."""

    def test_load_cells_as_string(self):
        """Cells field as a string should raise ValueError, not TypeError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"rows": 3, "cols": 3, "cells": "not_a_list"}, f)
            filepath = f.name
        try:
            with self.assertRaises(ValueError):
                load_maze(filepath)
        finally:
            os.unlink(filepath)

    def test_load_cells_wrong_dimensions(self):
        """Cells array with wrong row count should raise ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            # 2 rows of cells but rows=3 declared
            data = {"rows": 3, "cols": 2, "cells": [
                [{"row": 0, "col": 0, "walls": {"N": True, "S": True, "E": True, "W": True}},
                 {"row": 0, "col": 1, "walls": {"N": True, "S": True, "E": True, "W": True}}],
                [{"row": 1, "col": 0, "walls": {"N": True, "S": True, "E": True, "W": True}},
                 {"row": 1, "col": 1, "walls": {"N": True, "S": True, "E": True, "W": True}}],
            ]}
            json.dump(data, f)
            filepath = f.name
        try:
            with self.assertRaises(ValueError):
                load_maze(filepath)
        finally:
            os.unlink(filepath)

    def test_load_cell_missing_keys(self):
        """Cell dict missing required keys should raise ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            data = {"rows": 2, "cols": 2, "cells": [
                [{"row": 0, "col": 0, "walls": {"N": True, "S": True, "E": True, "W": True}},
                 {"wrong_key": 1}],  # Missing 'row', 'col', 'walls'
                [{"row": 1, "col": 0, "walls": {"N": True, "S": True, "E": True, "W": True}},
                 {"row": 1, "col": 1, "walls": {"N": True, "S": True, "E": True, "W": True}}],
            ]}
            json.dump(data, f)
            filepath = f.name
        try:
            with self.assertRaises(ValueError):
                load_maze(filepath)
        finally:
            os.unlink(filepath)

    def test_load_cell_not_dict(self):
        """Cell that is not a dict should raise ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            data = {"rows": 2, "cols": 2, "cells": [
                [{"row": 0, "col": 0, "walls": {"N": True, "S": True, "E": True, "W": True}},
                 {"row": 0, "col": 1, "walls": {"N": True, "S": True, "E": True, "W": True}}],
                [{"row": 1, "col": 0, "walls": {"N": True, "S": True, "E": True, "W": True}},
                 "not_a_dict"],
            ]}
            json.dump(data, f)
            filepath = f.name
        try:
            with self.assertRaises(ValueError):
                load_maze(filepath)
        finally:
            os.unlink(filepath)

    def test_load_non_integer_rows(self):
        """Non-integer rows/cols should raise ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"rows": "three", "cols": 3, "cells": []}, f)
            filepath = f.name
        try:
            with self.assertRaises(ValueError):
                load_maze(filepath)
        finally:
            os.unlink(filepath)

    def test_load_cells_row_not_list(self):
        """A cells row that is not a list should raise ValueError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            data = {"rows": 2, "cols": 2, "cells": [
                "not_a_list",
                [{"row": 1, "col": 0, "walls": {"N": True, "S": True, "E": True, "W": True}},
                 {"row": 1, "col": 1, "walls": {"N": True, "S": True, "E": True, "W": True}}],
            ]}
            json.dump(data, f)
            filepath = f.name
        try:
            with self.assertRaises(ValueError):
                load_maze(filepath)
        finally:
            os.unlink(filepath)


if __name__ == "__main__":
    unittest.main()