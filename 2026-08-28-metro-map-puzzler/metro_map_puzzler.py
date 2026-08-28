#!/usr/bin/env python3
"""Metro Map Puzzler.

Generate a tiny fictional subway network, render it as ASCII, and challenge the
player to find efficient journeys across the map.
"""

from __future__ import annotations

import argparse
import collections
import difflib
import heapq
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

VERSION = "1.0.0"
RESET = "\033[0m"
ANSI_COLORS = {
    "red": "\033[38;5;203m",
    "blue": "\033[38;5;39m",
    "green": "\033[38;5;42m",
    "yellow": "\033[38;5;220m",
    "magenta": "\033[38;5;207m",
    "cyan": "\033[38;5;51m",
    "orange": "\033[38;5;208m",
    "white": "\033[38;5;255m",
}
LINE_STYLES = [
    ("Crimson", "red", "#"),
    ("Azure", "blue", "="),
    ("Emerald", "green", "+"),
    ("Sun", "yellow", "~"),
    ("Violet", "magenta", "*"),
    ("Tide", "cyan", "%"),
    ("Amber", "orange", ";"),
]
ADJECTIVES = [
    "North", "South", "East", "West", "Old", "New", "Upper", "Lower", "Grand", "Silver",
    "Golden", "River", "Cinder", "Echo", "Marble", "Copper", "Moon", "Harbor", "Signal", "Maple",
]
NOUNS = [
    "Market", "Bridge", "Square", "Heights", "Wharf", "Garden", "Junction", "Library", "Arcade", "Yard",
    "Terrace", "Quarter", "Gate", "Spire", "Loop", "Museum", "Observatory", "Point", "Commons", "Depot",
]


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    x: int
    y: int


@dataclass(frozen=True)
class Edge:
    target: str
    line: str


@dataclass
class Line:
    id: str
    name: str
    color: str
    glyph: str
    stations: list[str]


@dataclass
class MetroMap:
    stations: dict[str, Station]
    lines: list[Line]
    adjacency: dict[str, list[Edge]]
    width: int
    height: int


@dataclass(order=True)
class SearchState:
    priority: tuple[int, int, str]
    stops: int = field(compare=False)
    transfers: int = field(compare=False)
    station_id: str = field(compare=False)
    line_id: str | None = field(compare=False)


@dataclass
class Route:
    stations: list[str]
    lines: list[str]
    stops: int
    transfers: int

    def station_names(self, metro: MetroMap) -> list[str]:
        return [metro.stations[station_id].name for station_id in self.stations]

    def line_names(self, metro: MetroMap) -> list[str]:
        line_lookup = {line.id: line.name for line in metro.lines}
        return [line_lookup[line_id] for line_id in self.lines]


@dataclass(frozen=True)
class SearchWeights:
    """Priority weights used when selecting a route.

    The search still tracks both stops and transfers, but the priority tuple lets
    the CLI choose whether to optimize primarily for shortest journeys or fewest
    line changes.
    """

    prioritize_transfers: bool = False

    def priority(self, stops: int, transfers: int, station_id: str) -> tuple[int, int, str]:
        if self.prioritize_transfers:
            return (transfers, stops, station_id)
        return (stops, transfers, station_id)


@dataclass
class Puzzle:
    start: str
    goal: str
    question: str
    route: Route
    difficulty: int


class GenerationError(RuntimeError):
    pass


def slugify_name(name: str) -> str:
    return name.lower().replace(" ", "-")


def station_code(index: int) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    code = ""
    number = index
    while True:
        code = letters[number % 26] + code
        number = number // 26 - 1
        if number < 0:
            return code


def make_station_name(rng: random.Random, used: set[str]) -> str:
    for _ in range(500):
        name = f"{rng.choice(ADJECTIVES)} {rng.choice(NOUNS)}"
        if name not in used:
            used.add(name)
            return name
    raise GenerationError("could not create a unique station name")


def manhattan_path(ax: int, ay: int, bx: int, by: int) -> list[tuple[int, int]]:
    path: list[tuple[int, int]] = [(ax, ay)]
    x, y = ax, ay
    step_x = 1 if bx > x else -1
    while x != bx:
        x += step_x
        path.append((x, y))
    step_y = 1 if by > y else -1
    while y != by:
        y += step_y
        path.append((x, y))
    return path


def add_edge(adjacency: dict[str, list[Edge]], a: str, b: str, line_id: str) -> None:
    adjacency.setdefault(a, []).append(Edge(b, line_id))
    adjacency.setdefault(b, []).append(Edge(a, line_id))


def station_line_membership(metro: MetroMap) -> dict[str, list[str]]:
    membership: dict[str, list[str]] = collections.defaultdict(list)
    for line in metro.lines:
        for station_id in line.stations:
            membership[station_id].append(line.id)
    return dict(membership)


def generate_line_path(
    rng: random.Random,
    width: int,
    height: int,
    target_len: int,
    occupied: dict[tuple[int, int], str],
    shared_station_ids: list[str],
    station_lookup: dict[str, Station],
    used_names: set[str],
    start_index: int,
    require_shared_start: bool,
) -> tuple[list[Station], int]:
    attempts = 0
    next_index = start_index
    while attempts < 250:
        attempts += 1
        stations: list[Station] = []
        local_occupied: dict[tuple[int, int], str] = {}
        if shared_station_ids and (require_shared_start or rng.random() < 0.8):
            shared_id = rng.choice(shared_station_ids)
            stations.append(station_lookup[shared_id])
        else:
            if require_shared_start:
                continue
            x = rng.randint(2, width - 3)
            y = rng.randint(2, height - 3)
            if (x, y) in occupied:
                continue
            station = Station(station_code(next_index), make_station_name(rng, used_names), x, y)
            stations.append(station)
            next_index += 1
        while len(stations) < target_len:
            current = stations[-1]
            direction = rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            distance = rng.randint(3, 6)
            nx = current.x + direction[0] * distance
            ny = current.y + direction[1] * distance
            nx = max(2, min(width - 3, nx))
            ny = max(2, min(height - 3, ny))
            if (nx, ny) == (current.x, current.y):
                continue
            candidate_path = manhattan_path(current.x, current.y, nx, ny)
            if any(pos in local_occupied for pos in candidate_path[1:]):
                continue
            reuse_existing = (nx, ny) in occupied and rng.random() < 0.35
            if reuse_existing:
                station = station_lookup[occupied[(nx, ny)]]
                if station.id in [s.id for s in stations]:
                    continue
            elif (nx, ny) in occupied:
                continue
            else:
                station = Station(station_code(next_index), make_station_name(rng, used_names), nx, ny)
                next_index += 1
            stations.append(station)
            for pos in candidate_path:
                local_occupied[pos] = station.id
        unique_ids = {station.id for station in stations}
        if len(stations) >= max(5, target_len - 1) and len(unique_ids) == len(stations):
            return stations, next_index
    raise GenerationError("could not generate a valid line path")


def build_metro(seed: int, width: int, height: int, line_count: int) -> MetroMap:
    rng = random.Random(seed)
    occupied: dict[tuple[int, int], str] = {}
    stations: dict[str, Station] = {}
    adjacency: dict[str, list[Edge]] = collections.defaultdict(list)
    lines: list[Line] = []
    used_names: set[str] = set()
    next_index = 0
    for line_number in range(line_count):
        line_name, color, glyph = LINE_STYLES[line_number % len(LINE_STYLES)]
        existing_shared = list(stations)
        target_len = rng.randint(5, 8)
        line_stations, next_index = generate_line_path(
            rng,
            width,
            height,
            target_len,
            occupied,
            existing_shared,
            stations,
            used_names,
            next_index,
            require_shared_start=line_number > 0,
        )
        line_id = slugify_name(line_name)
        for station in line_stations:
            stations.setdefault(station.id, station)
        for left, right in zip(line_stations, line_stations[1:]):
            for pos in manhattan_path(left.x, left.y, right.x, right.y):
                occupied.setdefault(pos, left.id)
            add_edge(adjacency, left.id, right.id, line_id)
        lines.append(Line(line_id, f"{line_name} Line", color, glyph, [station.id for station in line_stations]))
    metro = MetroMap(stations=stations, lines=lines, adjacency=dict(adjacency), width=width, height=height)
    if not is_connected(metro):
        raise GenerationError("generated metro is unexpectedly disconnected")
    return metro


def build_metro_with_retries(seed: int, width: int, height: int, line_count: int, retries: int = 8) -> MetroMap:
    """Generate a metro map, retrying with adjacent seeds if needed.

    The generator is usually stable, but retries make the CLI more robust when a
    particular seed leads to an awkward layout.
    """

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return build_metro(seed + attempt, width, height, line_count)
        except GenerationError as error:
            last_error = error
    raise GenerationError(f"could not generate metro after {retries} attempts: {last_error}")


def is_connected(metro: MetroMap) -> bool:
    if not metro.stations:
        return True
    start = next(iter(metro.stations))
    queue = collections.deque([start])
    seen = {start}
    while queue:
        station_id = queue.popleft()
        for edge in metro.adjacency.get(station_id, []):
            if edge.target not in seen:
                seen.add(edge.target)
                queue.append(edge.target)
    return len(seen) == len(metro.stations)


def shortest_route(metro: MetroMap, start: str, goal: str, *, prioritize_transfers: bool = False) -> Route:
    weights = SearchWeights(prioritize_transfers=prioritize_transfers)
    heap: list[SearchState] = [SearchState(weights.priority(0, 0, start), 0, 0, start, None)]
    best: dict[tuple[str, str | None], tuple[int, int, str]] = {(start, None): weights.priority(0, 0, start)}
    metrics: dict[tuple[str, str | None], tuple[int, int]] = {(start, None): (0, 0)}
    previous: dict[tuple[str, str | None], tuple[tuple[str, str | None] | None, str | None]] = {(start, None): (None, None)}
    goal_state: tuple[str, str | None] | None = None
    while heap:
        state = heapq.heappop(heap)
        key = (state.station_id, state.line_id)
        if best.get(key) != weights.priority(state.stops, state.transfers, state.station_id):
            continue
        if state.station_id == goal:
            goal_state = key
            break
        for edge in metro.adjacency.get(state.station_id, []):
            next_stops = state.stops + 1
            extra_transfer = 0 if state.line_id in (None, edge.line) else 1
            next_transfers = state.transfers + extra_transfer
            next_key = (edge.target, edge.line)
            cost = weights.priority(next_stops, next_transfers, edge.target)
            if cost < best.get(next_key, (10**9, 10**9, "~")):
                best[next_key] = cost
                metrics[next_key] = (next_stops, next_transfers)
                previous[next_key] = (key, edge.line)
                heapq.heappush(
                    heap,
                    SearchState(
                        weights.priority(next_stops, next_transfers, edge.target),
                        next_stops,
                        next_transfers,
                        edge.target,
                        edge.line,
                    ),
                )
    if goal_state is None:
        raise ValueError(f"no route from {start} to {goal}")
    station_path: list[str] = []
    line_path: list[str] = []
    cursor: tuple[str, str | None] | None = goal_state
    while cursor is not None:
        station_path.append(cursor[0])
        prev_info = previous[cursor]
        if prev_info[1] is not None:
            line_path.append(prev_info[1])
        cursor = prev_info[0]
    station_path.reverse()
    line_path.reverse()
    normalized_lines: list[str] = []
    for line_id in line_path:
        if not normalized_lines or normalized_lines[-1] != line_id:
            normalized_lines.append(line_id)
    stops, transfers = metrics[goal_state]
    return Route(stations=station_path, lines=normalized_lines, stops=stops, transfers=transfers)


def pick_puzzle(metro: MetroMap, seed: int, difficulty: int = 2) -> Puzzle:
    rng = random.Random(seed)
    station_ids = list(metro.stations)
    candidates: list[Puzzle] = []
    for _ in range(120):
        start, goal = rng.sample(station_ids, 2)
        route = shortest_route(metro, start, goal)
        score = route.stops + route.transfers * 2 + max(0, len(route.lines) - 1)
        if score >= 4 + difficulty * 2:
            question = (
                f"How do you travel from {metro.stations[start].name} to {metro.stations[goal].name} "
                f"with the fewest stops?"
            )
            candidates.append(Puzzle(start, goal, question, route, score))
    if not candidates:
        start, goal = station_ids[0], station_ids[-1]
        route = shortest_route(metro, start, goal)
        return Puzzle(start, goal, f"Travel from {metro.stations[start].name} to {metro.stations[goal].name}.", route, route.stops)
    return max(candidates, key=lambda puzzle: (puzzle.difficulty, puzzle.route.transfers, puzzle.route.stops))


def route_summary(route: Route, metro: MetroMap) -> str:
    names = route.station_names(metro)
    line_lookup = {line.id: line.name for line in metro.lines}
    segments: list[str] = []
    current_line: str | None = None
    start_name = names[0]
    for left, right in zip(route.stations, route.stations[1:]):
        line_id = next(edge.line for edge in metro.adjacency[left] if edge.target == right)
        if current_line != line_id:
            if current_line is None:
                segments.append(f"Start on {line_lookup[line_id]} at {metro.stations[left].name}")
            else:
                segments.append(f"Transfer to {line_lookup[line_id]} at {metro.stations[left].name}")
            current_line = line_id
    segments.append(f"Arrive at {names[-1]}")
    joined = " → ".join(names)
    return (
        f"{joined}\n"
        f"Stops: {route.stops} | Transfers: {route.transfers}\n"
        + "\n".join(segments)
    )


def network_stats(metro: MetroMap) -> dict[str, str | int]:
    memberships = station_line_membership(metro)
    interchanges = [station_id for station_id, lines in memberships.items() if len(lines) > 1]
    busiest_station_id = max(memberships, key=lambda station_id: (len(memberships[station_id]), metro.stations[station_id].name))
    longest_line = max(metro.lines, key=lambda line: len(line.stations))
    return {
        "stations": len(metro.stations),
        "lines": len(metro.lines),
        "interchanges": len(interchanges),
        "busiest_station": metro.stations[busiest_station_id].name,
        "busiest_station_lines": len(memberships[busiest_station_id]),
        "longest_line": longest_line.name,
        "longest_line_stations": len(longest_line.stations),
    }


def describe_network(metro: MetroMap) -> str:
    stats = network_stats(metro)
    return (
        "Network summary\n"
        "---------------\n"
        f"Stations: {stats['stations']}\n"
        f"Lines: {stats['lines']}\n"
        f"Interchanges: {stats['interchanges']}\n"
        f"Busiest interchange: {stats['busiest_station']} ({stats['busiest_station_lines']} lines)\n"
        f"Longest line: {stats['longest_line']} ({stats['longest_line_stations']} stations)\n"
    )


def station_listing(metro: MetroMap) -> str:
    memberships = station_line_membership(metro)
    line_names = {line.id: line.name for line in metro.lines}
    lines = ["Stations", "--------"]
    for station in sorted(metro.stations.values(), key=lambda item: item.name):
        served_by = ", ".join(line_names[line_id] for line_id in memberships.get(station.id, []))
        lines.append(f"{station.name:<24} ({station.x:>2},{station.y:>2})  {served_by}")
    return "\n".join(lines) + "\n"


def export_network(metro: MetroMap, destination: Path, seed: int) -> None:
    if destination.exists() and destination.is_dir():
        raise OSError(f"export path is a directory: {destination}")
    payload = {
        "seed": seed,
        "width": metro.width,
        "height": metro.height,
        "stations": [
            {"id": station.id, "name": station.name, "x": station.x, "y": station.y}
            for station in sorted(metro.stations.values(), key=lambda item: item.id)
        ],
        "lines": [
            {
                "id": line.id,
                "name": line.name,
                "color": line.color,
                "glyph": line.glyph,
                "stations": line.stations,
            }
            for line in metro.lines
        ],
        "stats": network_stats(metro),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def render_map(metro: MetroMap, *, color: bool = True, legend: bool = True) -> str:
    grid = [[" " for _ in range(metro.width)] for _ in range(metro.height)]
    line_lookup = {line.id: line for line in metro.lines}
    for line in metro.lines:
        for left_id, right_id in zip(line.stations, line.stations[1:]):
            left = metro.stations[left_id]
            right = metro.stations[right_id]
            for x, y in manhattan_path(left.x, left.y, right.x, right.y)[1:-1]:
                grid[y][x] = line.glyph
    for station in metro.stations.values():
        grid[station.y][station.x] = "●"
    rendered_rows = ["".join(row).rstrip() for row in grid]
    if color:
        colored_rows = []
        for y, row in enumerate(grid):
            pieces: list[str] = []
            for x, cell in enumerate(row):
                if cell == " ":
                    pieces.append(" ")
                    continue
                station_here = next((s for s in metro.stations.values() if s.x == x and s.y == y), None)
                if station_here is not None:
                    pieces.append(ANSI_COLORS["white"] + "●" + RESET)
                    continue
                applied = False
                for line in metro.lines:
                    if cell == line.glyph:
                        pieces.append(ANSI_COLORS[line.color] + cell + RESET)
                        applied = True
                        break
                if not applied:
                    pieces.append(cell)
            colored_rows.append("".join(pieces).rstrip())
        rendered_rows = colored_rows
    output = ["Metro map", "=" * 9, *rendered_rows, ""]
    if legend:
        memberships = station_line_membership(metro)
        line_names = {line.id: line.name for line in metro.lines}
        output.append("Station legend")
        output.append("-" * 14)
        for station in sorted(metro.stations.values(), key=lambda item: (item.y, item.x, item.name)):
            lines = ", ".join(line_names[line_id] for line_id in memberships.get(station.id, []))
            output.append(f"{station.name:<24} ({station.x:>2},{station.y:>2})  {lines}")
        output.append("")
        output.append("Lines")
        output.append("-" * 5)
        for line in metro.lines:
            output.append(f"{line.glyph} {line.name}: " + " → ".join(metro.stations[station_id].name for station_id in line.stations))
    return "\n".join(output).rstrip() + "\n"


def quiz(metro: MetroMap, rounds: int, seed: int) -> int:
    print(render_map(metro, color=sys.stdout.isatty()))
    print("Trip quiz")
    print("=========")
    print("Answer with station names separated by commas, or type 'hint', 'show', or 'quit'.")
    score = 0
    for round_index in range(rounds):
        puzzle = pick_puzzle(metro, seed + round_index * 101, difficulty=2 + round_index)
        print()
        print(f"Round {round_index + 1}/{rounds}")
        print(puzzle.question)
        try:
            answer = input("> ").strip()
        except EOFError:
            print("Input closed. Ending quiz early.")
            break
        if answer.lower() == "quit":
            break
        if answer.lower() in {"hint", "show"}:
            print(route_summary(puzzle.route, metro))
            continue
        guessed = [part.strip().lower() for part in answer.split(",") if part.strip()]
        truth = [name.lower() for name in puzzle.route.station_names(metro)]
        if guessed == truth:
            score += 1
            print("Correct. Perfect route.")
        elif guessed and guessed[0] == truth[0] and guessed[-1] == truth[-1]:
            print("Close, but not optimal.")
            print(route_summary(puzzle.route, metro))
        else:
            print("Not quite.")
            print(route_summary(puzzle.route, metro))
    print()
    print(f"Final score: {score}/{rounds}")
    return 0


def write_snapshot(metro: MetroMap, seed: int, color: bool) -> str:
    puzzle = pick_puzzle(metro, seed + 404, difficulty=3)
    return (
        render_map(metro, color=color)
        + "\n"
        + describe_network(metro)
        + "\nPuzzle\n------\n"
        + puzzle.question
        + "\n\nBest route\n----------\n"
        + route_summary(puzzle.route, metro)
        + "\n"
    )


def parse_station(metro: MetroMap, query: str) -> str:
    query_norm = query.strip().lower()
    if not query_norm:
        raise SystemExit("station name cannot be empty")
    exact = [station.id for station in metro.stations.values() if station.name.lower() == query_norm]
    if exact:
        return exact[0]
    partial = [station.id for station in metro.stations.values() if query_norm in station.name.lower()]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        names = [station.name for station in metro.stations.values()]
        suggestions = difflib.get_close_matches(query, names, n=3, cutoff=0.45)
        if suggestions:
            raise SystemExit(f"unknown station: {query}. Did you mean: {', '.join(suggestions)}?")
        raise SystemExit(f"unknown station: {query}")
    names = ", ".join(metro.stations[station_id].name for station_id in partial[:8])
    raise SystemExit(f"station name is ambiguous: {query} -> {names}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and solve tiny ASCII metro-route puzzles.")
    parser.add_argument("--seed", type=int, default=42, help="random seed for reproducible maps")
    parser.add_argument("--width", type=int, default=54, help="map width in characters")
    parser.add_argument("--height", type=int, default=20, help="map height in characters")
    parser.add_argument("--lines", type=int, default=5, help="number of metro lines to generate")
    parser.add_argument("--snapshot", action="store_true", help="print a generated map, puzzle, and answer")
    parser.add_argument("--quiz", type=int, metavar="ROUNDS", help="play an interactive route quiz")
    parser.add_argument("--solve", nargs=2, metavar=("FROM", "TO"), help="solve a route between two station names")
    parser.add_argument(
        "--route-mode",
        choices=("balanced", "transfers"),
        default="balanced",
        help="optimize for fewest stops first (balanced) or fewest transfers first",
    )
    parser.add_argument("--list-stations", action="store_true", help="print the generated station list")
    parser.add_argument("--stats", action="store_true", help="print a compact network summary")
    parser.add_argument("--export", type=Path, metavar="PATH", help="export the generated metro network as JSON")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    return parser


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if args.width < 24 or args.height < 12:
        parser.error("width/height are too small; use at least 24x12")
    if not 2 <= args.lines <= len(LINE_STYLES):
        parser.error(f"--lines must be between 2 and {len(LINE_STYLES)}")
    if args.quiz is not None and args.quiz < 1:
        parser.error("--quiz must be at least 1")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"Metro Map Puzzler {VERSION}")
        return 0
    validate_args(args, parser)
    try:
        metro = build_metro_with_retries(args.seed, args.width, args.height, args.lines)
    except GenerationError as error:
        parser.exit(1, f"error: {error}\n")
    use_color = (not args.no_color) and sys.stdout.isatty()
    if args.export:
        try:
            export_network(metro, args.export, args.seed)
        except OSError as error:
            parser.exit(1, f"error: could not export network: {error}\n")
    if args.solve:
        start = parse_station(metro, args.solve[0])
        goal = parse_station(metro, args.solve[1])
        route = shortest_route(metro, start, goal, prioritize_transfers=args.route_mode == "transfers")
        print(render_map(metro, color=use_color))
        print(describe_network(metro))
        print("Solved route")
        print("------------")
        print(route_summary(route, metro))
        return 0
    if args.list_stations:
        print(render_map(metro, color=use_color, legend=False))
        print(station_listing(metro))
        if args.stats:
            print(describe_network(metro))
        return 0
    if args.stats:
        print(describe_network(metro))
        return 0
    if args.quiz is not None:
        return quiz(metro, args.quiz, args.seed)
    print(write_snapshot(metro, args.seed, use_color))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
