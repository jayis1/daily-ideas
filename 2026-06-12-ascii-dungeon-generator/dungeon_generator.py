#!/usr/bin/env python3
"""
Procedural ASCII Dungeon Map Generator

Generates random dungeon maps with rooms, corridors, monsters,
treasures, traps, and exits. Supports multiple themes and
difficulty levels.
"""

import random
import math
import argparse
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ── Tile types ──────────────────────────────────────────────────────
WALL = 0
FLOOR = 1
CORRIDOR = 2
DOOR = 3
STAIRS_DOWN = 4
STAIRS_UP = 5
WATER = 6
PILLAR = 7

TILE_CHARS = {
    WALL: "█",
    FLOOR: "·",
    CORRIDOR: "·",
    DOOR: "+",
    STAIRS_DOWN: "▼",
    STAIRS_UP: "▲",
    WATER: "~",
    PILLAR: "○",
}

# ── Entity types ────────────────────────────────────────────────────
MONSTER_CHARS = {
    "crypt":    ["z", "s", "g", "W", "V", "Z"],
    "inferno":  ["i", "d", "f", "D", "I", "F"],
    "forest":   ["w", "k", "a", "S", "T", "A"],
    "aquatic":  ["m", "e", "p", "M", "E", "P"],
    "standard": ["r", "b", "o", "R", "B", "O"],
}

TREASURE_CHARS = ["*", "♦", "♦", "✦", "♥"]
TRAP_CHARS = ["^", "×", "!", "?"]

THEME_WALL = {
    "crypt":    "█",
    "inferno":  "▓",
    "forest":   "▒",
    "aquatic":  "░",
    "standard": "█",
}

THEME_FLOOR = {
    "crypt":    "·",
    "inferno":  "≈",
    "forest":   "░",
    "aquatic":  "~",
    "standard": "·",
}


@dataclass
class Room:
    x: int
    y: int
    w: int
    h: int
    room_id: int = 0

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    @property
    def area(self) -> int:
        return self.w * self.h


@dataclass
class Entity:
    x: int
    y: int
    char: str
    kind: str  # "monster", "treasure", "trap", "npc"
    description: str = ""
    hp: int = 0
    gold_value: int = 0


@dataclass
class DungeonConfig:
    width: int = 60
    height: int = 30
    min_rooms: int = 5
    max_rooms: int = 12
    min_room_size: int = 3
    max_room_size: int = 8
    corridor_width: int = 1
    theme: str = "standard"
    difficulty: int = 1  # 1-5
    seed: Optional[int] = None
    add_water: bool = True
    add_pillars: bool = True
    add_traps: bool = True
    add_doors: bool = True


class DungeonGenerator:
    def __init__(self, config: DungeonConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self.grid: List[List[int]] = []
        self.rooms: List[Room] = []
        self.entities: List[Entity] = []
        self.room_id_counter = 0

    def _init_grid(self):
        self.grid = [[WALL for _ in range(self.config.width)]
                     for _ in range(self.config.height)]

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.config.width and 0 <= y < self.config.height

    def _carve_room(self, room: Room):
        for dy in range(room.h):
            for dx in range(room.w):
                nx, ny = room.x + dx, room.y + dy
                if self._in_bounds(nx, ny):
                    self.grid[ny][nx] = FLOOR

    def _rooms_overlap(self, room: Room, margin: int = 1) -> bool:
        for other in self.rooms:
            if (room.x - margin < other.x + other.w and
                room.x + room.w + margin > other.x and
                room.y - margin < other.y + other.h and
                room.h + room.y + margin > other.y):
                return True
        return False

    def _carve_corridor(self, x1: int, y1: int, x2: int, y2: int):
        x, y = x1, y1
        # L-shaped corridors: pick horizontal or vertical first
        if self.rng.random() < 0.5:
            # Horizontal first, then vertical
            while x != x2:
                if self._in_bounds(x, y) and self.grid[y][x] == WALL:
                    self.grid[y][x] = CORRIDOR
                x += 1 if x2 > x else -1
            while y != y2:
                if self._in_bounds(x, y) and self.grid[y][x] == WALL:
                    self.grid[y][x] = CORRIDOR
                y += 1 if y2 > y else -1
        else:
            # Vertical first, then horizontal
            while y != y2:
                if self._in_bounds(x, y) and self.grid[y][x] == WALL:
                    self.grid[y][x] = CORRIDOR
                y += 1 if y2 > y else -1
            while x != x2:
                if self._in_bounds(x, y) and self.grid[y][x] == WALL:
                    self.grid[y][x] = CORRIDOR
                x += 1 if x2 > x else -1
        if self._in_bounds(x2, y2) and self.grid[y2][x2] == WALL:
            self.grid[y2][x2] = CORRIDOR

    def _add_doors(self):
        """Place doors at room/corridor transitions."""
        if not self.config.add_doors:
            return
        for room in self.rooms:
            # Check each wall cell for door positions
            door_candidates = []
            for dy in range(room.h):
                for dx in range(room.w):
                    rx, ry = room.x + dx, room.y + dy
                    # Only check border cells
                    if dy == 0 or dy == room.h - 1 or dx == 0 or dx == room.w - 1:
                        # Check if adjacent to corridor
                        for nx, ny in [(rx-1,ry),(rx+1,ry),(rx,ry-1),(rx,ry+1)]:
                            if self._in_bounds(nx, ny) and self.grid[ny][nx] == CORRIDOR:
                                if self.grid[ry][rx] == FLOOR:
                                    door_candidates.append((rx, ry))
            # Place doors at some candidates
            for cx, cy in door_candidates:
                if self.rng.random() < 0.4:
                    self.grid[cy][cx] = DOOR

    def _add_water_features(self):
        """Add water puddles in some rooms."""
        if not self.config.add_water:
            return
        for i, room in enumerate(self.rooms):
            # Skip first and last room (stairs rooms) to keep them clear
            if i == 0 or i == len(self.rooms) - 1:
                continue
            if self.rng.random() < 0.3:
                cx, cy = room.center
                puddle_size = self.rng.randint(1, min(room.w, room.h) // 2)
                for dy in range(-puddle_size, puddle_size + 1):
                    for dx in range(-puddle_size, puddle_size + 1):
                        nx, ny = cx + dx, cy + dy
                        if (self._in_bounds(nx, ny) and
                            self.grid[ny][nx] == FLOOR and
                            dx*dx + dy*dy <= puddle_size*puddle_size):
                            if self.rng.random() < 0.7:
                                self.grid[ny][nx] = WATER

    def _add_pillars(self):
        """Add decorative pillars in large rooms."""
        if not self.config.add_pillars:
            return
        for room in self.rooms:
            if room.w >= 5 and room.h >= 5:
                # Add pillars in a pattern
                step_x = max(2, room.w // 3)
                step_y = max(2, room.h // 3)
                for dy in range(step_y, room.h - 1, step_y):
                    for dx in range(step_x, room.w - 1, step_x):
                        px, py = room.x + dx, room.y + dy
                        if (self._in_bounds(px, py) and
                            self.grid[py][px] == FLOOR and
                            self.rng.random() < 0.6):
                            self.grid[py][px] = PILLAR

    def _add_monsters(self):
        """Populate rooms with monsters based on theme and difficulty."""
        monsters = MONSTER_CHARS.get(self.config.theme, MONSTER_CHARS["standard"])
        num_monsters = self.rng.randint(
            len(self.rooms),
            len(self.rooms) * self.config.difficulty
        )
        monster_names = {
            "crypt":    {"z": "Zombie", "s": "Skeleton", "g": "Ghost",
                        "W": "Wraith", "V": "Vampire", "Z": "Lich"},
            "inferno":  {"i": "Imp", "d": "Demon", "f": "Fire Elemental",
                        "D": "Devil", "I": "Infernal", "F": "Fire Lord"},
            "forest":   {"w": "Wolf", "k": "Kobold", "a": "Arachnid",
                        "S": "Spider Queen", "T": "Treant", "A": "Arch-druid"},
            "aquatic":  {"m": "Murloc", "e": "Eel", "p": "Piranha",
                        "M": "Merfolk", "E": "Electric Eel", "P": "Kraken"},
            "standard": {"r": "Rat", "b": "Bat", "o": "Orc",
                        "R": "Rock Golem", "B": "Bear", "O": "Ogre"},
        }
        names = monster_names.get(self.config.theme, monster_names["standard"])

        for _ in range(num_monsters):
            room = self.rng.choice(self.rooms)
            mx = self.rng.randint(room.x + 1, room.x + room.w - 2)
            my = self.rng.randint(room.y + 1, room.y + room.h - 2)
            # Pick monster tier based on difficulty
            tier = min(self.rng.randint(0, self.config.difficulty), len(monsters) - 1)
            char = monsters[tier]
            name = names.get(char, "Monster")
            hp = (tier + 1) * self.rng.randint(3, 8)
            if self.grid[my][mx] in (FLOOR, CORRIDOR):
                self.entities.append(Entity(
                    x=mx, y=my, char=char, kind="monster",
                    description=name, hp=hp
                ))

    def _add_treasures(self):
        """Scatter treasure in rooms."""
        num_treasures = self.rng.randint(1, max(1, len(self.rooms) // 2))
        treasure_names = {
            "*": "Gold coins",
            "♦": "Gem",
            "✦": "Magic scroll",
            "♥": "Potion",
        }
        for _ in range(num_treasures):
            room = self.rng.choice(self.rooms)
            tx = self.rng.randint(room.x + 1, room.x + room.w - 2)
            ty = self.rng.randint(room.y + 1, room.y + room.h - 2)
            char = self.rng.choice(TREASURE_CHARS)
            gold = self.rng.randint(10, 100) * self.config.difficulty
            name = treasure_names.get(char, "Treasure")
            if self.grid[ty][tx] in (FLOOR, CORRIDOR):
                self.entities.append(Entity(
                    x=tx, y=ty, char=char, kind="treasure",
                    description=name, gold_value=gold
                ))

    def _add_traps(self):
        """Place traps on corridor tiles."""
        if not self.config.add_traps:
            return
        trap_names = {
            "^": "Spike trap",
            "×": "Poison gas",
            "!": "Pit trap",
            "?": "Illusion",
        }
        trap_chance = 0.05 * self.config.difficulty
        for y in range(self.config.height):
            for x in range(self.config.width):
                if self.grid[y][x] == CORRIDOR and self.rng.random() < trap_chance:
                    char = self.rng.choice(TRAP_CHARS)
                    name = trap_names.get(char, "Trap")
                    self.entities.append(Entity(
                        x=x, y=y, char=char, kind="trap",
                        description=name
                    ))

    def _add_stairs(self):
        """Place stairs up and stairs down in different rooms."""
        if len(self.rooms) < 2:
            return
        # Stairs up in the first room — find a FLOOR tile near center
        room_up = self.rooms[0]
        placed = False
        candidates = []
        for dy in range(room_up.h):
            for dx in range(room_up.w):
                cx, cy = room_up.x + dx, room_up.y + dy
                if self.grid[cy][cx] == FLOOR:
                    dist = abs(cx - room_up.center[0]) + abs(cy - room_up.center[1])
                    candidates.append((dist, cx, cy))
        candidates.sort()
        for _, sx, sy in candidates:
            # Check no entity already here
            if not any(e.x == sx and e.y == sy for e in self.entities):
                self.grid[sy][sx] = STAIRS_UP
                placed = True
                break

        # Stairs down in the last room — find a FLOOR tile near center
        room_down = self.rooms[-1]
        candidates = []
        for dy in range(room_down.h):
            for dx in range(room_down.w):
                cx, cy = room_down.x + dx, room_down.y + dy
                if self.grid[cy][cx] == FLOOR:
                    dist = abs(cx - room_down.center[0]) + abs(cy - room_down.center[1])
                    candidates.append((dist, cx, cy))
        candidates.sort()
        for _, sx, sy in candidates:
            if not any(e.x == sx and e.y == sy for e in self.entities):
                self.grid[sy][sx] = STAIRS_DOWN
                break

    def generate(self) -> 'DungeonGenerator':
        self._init_grid()

        # Generate rooms
        max_attempts = 200
        target_rooms = self.rng.randint(self.config.min_rooms, self.config.max_rooms)
        while len(self.rooms) < target_rooms and max_attempts > 0:
            max_attempts -= 1
            w = self.rng.randint(self.config.min_room_size, self.config.max_room_size)
            h = self.rng.randint(self.config.min_room_size, self.config.max_room_size)
            x = self.rng.randint(1, self.config.width - w - 1)
            y = self.rng.randint(1, self.config.height - h - 1)
            room = Room(x, y, w, h, room_id=self.room_id_counter)
            if not self._rooms_overlap(room, margin=2):
                self._carve_room(room)
                self.rooms.append(room)
                self.room_id_counter += 1

        # Connect rooms with corridors (MST-like with extra connections)
        if len(self.rooms) >= 2:
            # Sort rooms by distance from center to create connected layout
            connected = [0]
            unconnected = list(range(1, len(self.rooms)))

            while unconnected:
                best_dist = float('inf')
                best_pair = (connected[0], unconnected[0])
                for ci in connected:
                    for ui in unconnected:
                        r1 = self.rooms[ci]
                        r2 = self.rooms[ui]
                        dist = math.hypot(r1.center[0] - r2.center[0],
                                         r1.center[1] - r2.center[1])
                        if dist < best_dist:
                            best_dist = dist
                            best_pair = (ci, ui)
                ci, ui = best_pair
                self._carve_corridor(
                    self.rooms[ci].center[0], self.rooms[ci].center[1],
                    self.rooms[ui].center[0], self.rooms[ui].center[1]
                )
                connected.append(ui)
                unconnected.remove(ui)

            # Add a few extra corridors for loops
            for _ in range(self.rng.randint(1, max(1, len(self.rooms) // 3))):
                i = self.rng.randint(0, len(self.rooms) - 1)
                j = self.rng.randint(0, len(self.rooms) - 1)
                if i != j:
                    self._carve_corridor(
                        self.rooms[i].center[0], self.rooms[i].center[1],
                        self.rooms[j].center[0], self.rooms[j].center[1]
                    )

        # Add features
        self._add_water_features()
        self._add_pillars()
        self._add_doors()
        self._add_stairs()
        self._add_monsters()
        self._add_treasures()
        self._add_traps()

        return self

    def render(self) -> str:
        """Render the dungeon as an ASCII string."""
        theme = self.config.theme
        wall_char = THEME_WALL.get(theme, "█")
        floor_char = THEME_FLOOR.get(theme, "·")

        # Build entity lookup by position
        entity_map = {}
        for e in self.entities:
            entity_map[(e.x, e.y)] = e

        lines = []
        for y in range(self.config.height):
            row = []
            for x in range(self.config.width):
                if (x, y) in entity_map:
                    row.append(entity_map[(x, y)].char)
                else:
                    tile = self.grid[y][x]
                    if tile == WALL:
                        row.append(wall_char)
                    elif tile in (FLOOR, CORRIDOR):
                        row.append(floor_char)
                    else:
                        row.append(TILE_CHARS.get(tile, "?"))
            lines.append("".join(row))
        return "\n".join(lines)

    def render_legend(self) -> str:
        theme = self.config.theme
        wall_char = THEME_WALL.get(theme, "█")
        floor_char = THEME_FLOOR.get(theme, "·")
        lines = [
            f"{'═' * 40}",
            f"  DUNGEON MAP — Theme: {theme.upper()}, Difficulty: {'★' * self.config.difficulty}",
            f"{'═' * 40}",
            f"",
            f"  LEGEND:",
            f"  {wall_char}  Wall",
            f"  {floor_char}  Floor / Corridor",
            f"  +  Door",
            f"  ▼  Stairs Down",
            f"  ▲  Stairs Up (Entrance)",
            f"  ~  Water",
            f"  ○  Pillar",
            f"",
        ]

        # Group entities by kind
        monsters = [e for e in self.entities if e.kind == "monster"]
        treasures = [e for e in self.entities if e.kind == "treasure"]
        traps = [e for e in self.entities if e.kind == "trap"]

        if monsters:
            lines.append(f"  MONSTERS ({len(monsters)}):")
            seen = {}
            for m in monsters:
                if m.char not in seen:
                    seen[m.char] = m.description
            for char, name in seen.items():
                count = sum(1 for m in monsters if m.char == char)
                lines.append(f"    {char}  {name} (×{count})")
            lines.append("")

        if treasures:
            lines.append(f"  TREASURES ({len(treasures)}):")
            for t in treasures:
                lines.append(f"    {t.char}  {t.description} ({t.gold_value}gp)")
            lines.append("")

        if traps:
            lines.append(f"  TRAPS ({len(traps)}):")
            seen = {}
            for t in traps:
                if t.char not in seen:
                    seen[t.char] = t.description
            for char, name in seen.items():
                count = sum(1 for t in traps if t.char == char)
                lines.append(f"    {char}  {name} (×{count})")
            lines.append("")

        lines.append(f"  ROOMS: {len(self.rooms)}")
        lines.append(f"  DIMENSIONS: {self.config.width}×{self.config.height}")
        if self.config.seed is not None:
            lines.append(f"  SEED: {self.config.seed}")
        lines.append(f"{'═' * 40}")
        return "\n".join(lines)

    def render_stats(self) -> str:
        """Render summary statistics."""
        total_floor = sum(1 for y in range(self.config.height)
                         for x in range(self.config.width)
                         if self.grid[y][x] in (FLOOR, CORRIDOR))
        total_area = self.config.width * self.config.height
        density = total_floor / total_area * 100
        monsters = [e for e in self.entities if e.kind == "monster"]
        avg_hp = sum(m.hp for m in monsters) / max(1, len(monsters))
        total_gold = sum(t.gold_value for t in self.entities if t.kind == "treasure")

        return (
            f"  Floor density: {density:.1f}%\n"
            f"  Avg monster HP: {avg_hp:.0f}\n"
            f"  Total gold value: {total_gold}gp\n"
            f"  Traps: {sum(1 for e in self.entities if e.kind == 'trap')}\n"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Procedural ASCII Dungeon Map Generator"
    )
    parser.add_argument(
        "-W", "--width", type=int, default=60,
        help="Dungeon width (default: 60)"
    )
    parser.add_argument(
        "-H", "--height", type=int, default=30,
        help="Dungeon height (default: 30)"
    )
    parser.add_argument(
        "-r", "--rooms", type=int, default=8,
        help="Max number of rooms (default: 8)"
    )
    parser.add_argument(
        "-t", "--theme",
        choices=["standard", "crypt", "inferno", "forest", "aquatic"],
        default="standard",
        help="Dungeon theme (default: standard)"
    )
    parser.add_argument(
        "-d", "--difficulty", type=int, default=1,
        help="Difficulty 1-5 (default: 1)"
    )
    parser.add_argument(
        "-s", "--seed", type=int, default=None,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--no-water", action="store_true",
        help="Disable water features"
    )
    parser.add_argument(
        "--no-pillars", action="store_true",
        help="Disable pillars"
    )
    parser.add_argument(
        "--no-traps", action="store_true",
        help="Disable traps"
    )
    parser.add_argument(
        "--no-doors", action="store_true",
        help="Disable doors"
    )
    parser.add_argument(
        "--legend", action="store_true",
        help="Show legend and entity listing"
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Show dungeon statistics"
    )

    args = parser.parse_args()

    config = DungeonConfig(
        width=args.width,
        height=args.height,
        max_rooms=args.rooms,
        theme=args.theme,
        difficulty=max(1, min(5, args.difficulty)),
        seed=args.seed,
        add_water=not args.no_water,
        add_pillars=not args.no_pillars,
        add_traps=not args.no_traps,
        add_doors=not args.no_doors,
    )

    generator = DungeonGenerator(config)
    generator.generate()

    print()
    print(generator.render())
    print()

    if args.legend:
        print(generator.render_legend())
        print()

    if args.stats:
        print(generator.render_stats())
        print()


if __name__ == "__main__":
    main()