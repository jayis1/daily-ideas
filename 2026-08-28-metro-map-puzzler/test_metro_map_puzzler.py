import unittest
from pathlib import Path

from metro_map_puzzler import (
    Edge,
    Line,
    MetroMap,
    Station,
    build_metro,
    export_network,
    is_connected,
    network_stats,
    parse_station,
    pick_puzzle,
    render_map,
    shortest_route,
)


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

    def make_route_mode_map(self) -> MetroMap:
        stations = {
            "A": Station("A", "Alpha Market", 2, 2),
            "B": Station("B", "Bravo Bridge", 8, 2),
            "C": Station("C", "Central Square", 14, 2),
            "D": Station("D", "Delta Yard", 20, 2),
            "E": Station("E", "Elm Point", 26, 2),
            "F": Station("F", "Forest Gate", 8, 8),
            "G": Station("G", "Garden Loop", 14, 8),
        }
        red = Line("red", "Red Line", "red", "#", ["A", "B", "C", "D", "E"])
        green = Line("green", "Green Line", "green", "+", ["A", "F"])
        blue = Line("blue", "Blue Line", "blue", "=", ["F", "G"])
        yellow = Line("yellow", "Yellow Line", "yellow", "~", ["G", "E"])
        adjacency = {station_id: [] for station_id in stations}

        def add(a: str, b: str, line: str) -> None:
            adjacency[a].append(Edge(b, line))
            adjacency[b].append(Edge(a, line))

        add("A", "B", "red")
        add("B", "C", "red")
        add("C", "D", "red")
        add("D", "E", "red")
        add("A", "F", "green")
        add("F", "G", "blue")
        add("G", "E", "yellow")
        return MetroMap(stations, [red, green, blue, yellow], adjacency, 30, 12)

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

    def test_route_mode_can_prioritize_fewer_transfers(self):
        metro = self.make_route_mode_map()
        balanced = shortest_route(metro, "A", "E")
        transfer_friendly = shortest_route(metro, "A", "E", prioritize_transfers=True)
        self.assertEqual(balanced.stations, ["A", "F", "G", "E"])
        self.assertEqual((balanced.stops, balanced.transfers), (3, 2))
        self.assertEqual(transfer_friendly.stations, ["A", "B", "C", "D", "E"])
        self.assertEqual((transfer_friendly.stops, transfer_friendly.transfers), (4, 0))

    def test_route_mode_changes_choice_when_transfer_count_differs(self):
        metro = self.make_route_mode_map()
        balanced = shortest_route(metro, "B", "E")
        transfer_friendly = shortest_route(metro, "B", "E", prioritize_transfers=True)
        self.assertEqual(balanced.stations, ["B", "C", "D", "E"])
        self.assertEqual((balanced.stops, balanced.transfers), (3, 0))
        self.assertEqual(transfer_friendly.stations, ["B", "C", "D", "E"])
        self.assertEqual(balanced.transfers, 0)
        self.assertEqual(transfer_friendly.transfers, 0)

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

    def test_parse_station_suggests_similar_name(self):
        metro = self.make_manual_map()
        with self.assertRaises(SystemExit) as context:
            parse_station(metro, "Alpha Markit")
        self.assertIn("Did you mean", str(context.exception))

    def test_parse_station_rejects_empty_name(self):
        metro = self.make_manual_map()
        with self.assertRaises(SystemExit) as context:
            parse_station(metro, "   ")
        self.assertIn("cannot be empty", str(context.exception))

    def test_export_network_writes_json_with_stats(self):
        metro = build_metro(seed=7, width=48, height=18, line_count=4)
        target = Path("test_export_network.json")
        self.addCleanup(lambda: target.unlink(missing_ok=True))
        export_network(metro, target, seed=7)
        text = target.read_text(encoding="utf-8")
        stats = network_stats(metro)
        self.assertIn('"seed": 7', text)
        self.assertIn(stats["busiest_station"], text)

    def test_export_network_rejects_directory_destination(self):
        metro = build_metro(seed=7, width=48, height=18, line_count=4)
        with self.assertRaises(OSError) as context:
            export_network(metro, Path("."), seed=7)
        self.assertIn("directory", str(context.exception))

    def test_quiz_exits_cleanly_on_eof(self):
        metro = build_metro(seed=7, width=48, height=18, line_count=4)
        from unittest.mock import patch

        with patch("builtins.input", side_effect=EOFError), patch("sys.stdout.write"):
            result = __import__("metro_map_puzzler").quiz(metro, rounds=2, seed=7)
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
