import unittest

from metro_map_puzzler import Edge, Line, MetroMap, Station, build_metro, is_connected, pick_puzzle, render_map, shortest_route


class MetroMapPuzzlerTests(unittest.TestCase):
    def make_manual_map(self) -> MetroMap:
        stations = {
            "A": Station("A", "Alpha Market", 2, 2),
            "B": Station("B", "Beta Bridge", 8, 2),
            "C": Station("C", "Central Square", 14, 2),
            "D": Station("D", "Delta Yard", 14, 8),
            "E": Station("E", "Elm Point", 20, 8),
        }
        red = Line("red", "Red Line", "red", "#", ["A", "B", "C"])
        blue = Line("blue", "Blue Line", "blue", "=", ["C", "D", "E"])
        adjacency = {
            "A": [],
            "B": [],
            "C": [],
            "D": [],
            "E": [],
        }
        def add(a: str, b: str, line: str) -> None:
            adjacency[a].append(Edge(b, line))
            adjacency[b].append(Edge(a, line))
        add("A", "B", "red")
        add("B", "C", "red")
        add("C", "D", "blue")
        add("D", "E", "blue")
        return MetroMap(stations, [red, blue], adjacency, 24, 12)

    def test_generated_map_is_connected(self):
        metro = build_metro(seed=17, width=54, height=20, line_count=5)
        self.assertTrue(is_connected(metro))
        self.assertGreaterEqual(len(metro.lines), 5)
        self.assertGreater(len(metro.stations), 10)

    def test_shortest_route_prefers_fewest_transfers_after_stops(self):
        metro = self.make_manual_map()
        route = shortest_route(metro, "A", "E")
        self.assertEqual(route.stations, ["A", "B", "C", "D", "E"])
        self.assertEqual(route.lines, ["red", "blue"])
        self.assertEqual(route.stops, 4)
        self.assertEqual(route.transfers, 1)

    def test_render_contains_station_legend(self):
        metro = build_metro(seed=3, width=48, height=18, line_count=4)
        rendered = render_map(metro, color=False)
        self.assertIn("Station legend", rendered)
        self.assertIn("Lines", rendered)
        self.assertIn("●", rendered)

    def test_pick_puzzle_returns_valid_route(self):
        metro = build_metro(seed=99, width=54, height=20, line_count=5)
        puzzle = pick_puzzle(metro, seed=123, difficulty=3)
        self.assertNotEqual(puzzle.start, puzzle.goal)
        self.assertEqual(puzzle.route.stations[0], puzzle.start)
        self.assertEqual(puzzle.route.stations[-1], puzzle.goal)
        self.assertGreaterEqual(puzzle.route.stops, 1)


if __name__ == "__main__":
    unittest.main()
