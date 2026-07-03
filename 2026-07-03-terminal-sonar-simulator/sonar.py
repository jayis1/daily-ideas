#!/usr/bin/env python3
"""
Terminal Sonar Simulator
========================
Command a submarine and use sonar pings to detect hidden enemy vessels
in a fog-of-war ocean. Track, classify, and neutralize threats before
they find you!

Controls:
  Arrow keys / WASD  - Move submarine
  SPACE              - Fire active sonar ping (reveals area, but enemies can detect you)
  E                  - Passive sonar mode (listen without pinging, lower detection range)
  F                  - Fire torpedo at nearest classified target
  G                  - Fire torpedo at farthest classified target (long-range engage)
  P                  - Passive sonar listening burst
  Z                  - Dive deeper (more protection, less visibility)
  X                  - Rise shallower (less protection, more visibility)
  M                  - Toggle minimap
  Q                  - Quit

CLI Options:
  --help             Show usage information
  --version          Print version and exit
  --difficulty       Set difficulty: easy, normal, hard (default: normal)
  --seed             Set random seed for reproducible worlds
  --enemies          Set number of enemies (default: 10)
"""

import argparse
import curses
import random
import math
import time
import sys
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set

# ── Version ────────────────────────────────────────────────────────────
VERSION = "1.2.0"

# ── Constants ──────────────────────────────────────────────────────────
WORLD_W = 120
WORLD_H = 60
VIEW_RADIUS = 12
PING_RADIUS = 18
PASSIVE_RADIUS = 6
TORPEDO_RANGE = 20
TORPEDO_SPEED = 2
SUB_SPEED = 1
MAX_TORPEDOES = 8
COOLDOWN_PING = 15      # frames between pings
COOLDOWN_TORPEDO = 10
DETECTION_THRESHOLD = 0.35  # probability enemy detects your ping per frame

# ── Difficulty presets ────────────────────────────────────────────────
DIFFICULTY_PRESETS = {
    "easy": {
        "enemies": 6,
        "enemy_hp_mult": 0.7,
        "enemy_detect_mult": 0.6,
        "enemy_fire_chance": 0.015,
        "torpedo_count": 12,
        "ping_cooldown": 10,
        "description": "Fewer enemies, weaker foes, more torpedoes",
    },
    "normal": {
        "enemies": 10,
        "enemy_hp_mult": 1.0,
        "enemy_detect_mult": 1.0,
        "enemy_fire_chance": 0.03,
        "torpedo_count": 8,
        "ping_cooldown": 15,
        "description": "Standard challenge — the intended experience",
    },
    "hard": {
        "enemies": 15,
        "enemy_hp_mult": 1.3,
        "enemy_detect_mult": 1.4,
        "enemy_fire_chance": 0.05,
        "torpedo_count": 6,
        "ping_cooldown": 20,
        "description": "More enemies, sharper AI, fewer torpedoes",
    },
}

# ── Enums ──────────────────────────────────────────────────────────────

class CellType(Enum):
    WATER = 0
    LAND = 1
    SHALLOWS = 2


class EnemyType(Enum):
    DESTROYER = "Destroyer"
    SUBMARINE = "Submarine"
    PATROL_BOAT = "Patrol Boat"


# ── Enemy configuration ───────────────────────────────────────────────

ENEMY_CONFIGS = {
    EnemyType.DESTROYER: {
        "hp": 3, "speed": 1, "detect_range": 10, "symbol": "D",
        "color": 3, "torpedo_dmg": 2,
    },
    EnemyType.SUBMARINE: {
        "hp": 2, "speed": 1, "detect_range": 14, "symbol": "S",
        "color": 5, "torpedo_dmg": 3,
    },
    EnemyType.PATROL_BOAT: {
        "hp": 1, "speed": 2, "detect_range": 6, "symbol": "P",
        "color": 6, "torpedo_dmg": 1,
    },
}

# ── Data classes ───────────────────────────────────────────────────────

@dataclass
class Submarine:
    """Player-controlled submarine state."""
    x: int = 60
    y: int = 30
    hp: int = 10
    max_hp: int = 10
    torpedoes: int = MAX_TORPEDOES
    ping_cooldown: int = 0
    torpedo_cooldown: int = 0
    depth: int = 0          # 0=periscope, 1=shallow, 2=deep
    score: int = 0
    pings_used: int = 0
    kills: int = 0
    noise_level: float = 0.0  # accumulated noise from movement/pinging


@dataclass
class Enemy:
    """An enemy vessel on the map."""
    x: int
    y: int
    etype: EnemyType
    hp: int
    speed: int
    detect_range: int
    symbol: str
    color: int
    torpedo_dmg: int
    classified: bool = False       # identified via sonar
    detected_player: bool = False  # knows where player is
    alert_level: float = 0.0       # 0–1, increases with pings
    move_timer: int = 0
    direction: int = 0              # angle in degrees
    engine_noise_timer: int = 0     # frames until next engine noise pulse


@dataclass
class Torpedo:
    """A moving torpedo projectile."""
    x: float
    y: float
    dx: float
    dy: float
    friendly: bool
    dmg: int = 1
    age: int = 0


@dataclass
class SonarPing:
    """An expanding sonar ring on the map."""
    x: int
    y: int
    radius: float
    max_radius: int
    age: int = 0
    active_ping: bool = True   # True=active (you sent it), False=passive listening


@dataclass
class Particle:
    """A visual particle for explosions, trails, etc."""
    x: float
    y: float
    dx: float
    dy: float
    life: int
    char: str


@dataclass
class SupplyCrate:
    """A floating supply crate the player can pick up."""
    x: int
    y: int
    kind: str   # "torpedo" or "repair"
    age: int = 0


# ── World generation ───────────────────────────────────────────────────

def generate_world(width: int, height: int, seed: Optional[int] = None) -> List[List[CellType]]:
    """Generate an ocean world with islands.

    Args:
        width:  World width in cells.
        height: World height in cells.
        seed:   Optional random seed for reproducibility.

    Returns:
        A 2-D grid of CellType values.
    """
    if seed is not None:
        random.seed(seed)

    grid = [[CellType.WATER for _ in range(width)] for _ in range(height)]

    # Generate island clusters using random walk + expansion
    num_islands = random.randint(6, 12)
    for _ in range(num_islands):
        cx = random.randint(10, width - 10)
        cy = random.randint(5, height - 5)
        size = random.randint(3, 8)
        # Walk to create irregular shapes
        for _ in range(size * 4):
            wx = cx + random.randint(-size, size)
            wy = cy + random.randint(-size, size)
            if 0 <= wx < width and 0 <= wy < height:
                grid[wy][wx] = CellType.LAND
        # Add shallows around the island
        for y in range(max(0, cy - size - 2), min(height, cy + size + 3)):
            for x in range(max(0, cx - size - 2), min(width, cx + size + 3)):
                if grid[y][x] == CellType.WATER:
                    # Check if adjacent to land
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            ny, nx = y + dy, x + dx
                            if 0 <= nx < width and 0 <= ny < height:
                                if grid[ny][nx] == CellType.LAND:
                                    if random.random() < 0.6:
                                        grid[y][x] = CellType.SHALLOWS
                                    break

    # Ensure starting area is clear
    for y in range(28, 33):
        for x in range(57, 64):
            grid[y][x] = CellType.WATER

    return grid


def spawn_enemies(world: List[List[CellType]], count: int,
                  hp_mult: float = 1.0, detect_mult: float = 1.0) -> List[Enemy]:
    """Spawn enemy vessels at random water locations, away from the player start.

    Args:
        world:        The world grid.
        count:        Number of enemies to spawn.
        hp_mult:      Multiplier applied to enemy HP (for difficulty scaling).
        detect_mult:  Multiplier applied to enemy detection range.

    Returns:
        List of Enemy instances.
    """
    enemies: List[Enemy] = []
    height = len(world)
    width = len(world[0])

    water_cells = []
    for y in range(height):
        for x in range(width):
            if world[y][x] == CellType.WATER and abs(x - 60) + abs(y - 30) > 15:
                water_cells.append((x, y))

    for _ in range(count):
        if not water_cells:
            break
        pos = random.choice(water_cells)
        etype = random.choice(list(EnemyType))
        cfg = ENEMY_CONFIGS[etype]
        enemy = Enemy(
            x=pos[0], y=pos[1], etype=etype,
            hp=max(1, round(cfg["hp"] * hp_mult)),
            speed=cfg["speed"],
            detect_range=max(3, round(cfg["detect_range"] * detect_mult)),
            symbol=cfg["symbol"], color=cfg["color"],
            torpedo_dmg=cfg["torpedo_dmg"],
            direction=random.randint(0, 359),
        )
        enemies.append(enemy)
        # Remove nearby cells to avoid clustering
        water_cells = [(wx, wy) for wx, wy in water_cells
                       if abs(wx - pos[0]) + abs(wy - pos[1]) > 8]

    return enemies


def spawn_supply_crates(world: List[List[CellType]], count: int = 4) -> List[SupplyCrate]:
    """Spawn supply crates at random water locations.

    Args:
        world:  The world grid.
        count:  Number of crates to create.

    Returns:
        List of SupplyCrate instances.
    """
    height = len(world)
    width = len(world[0])
    crates: List[SupplyCrate] = []

    water_cells = []
    for y in range(height):
        for x in range(width):
            if world[y][x] == CellType.WATER and abs(x - 60) + abs(y - 30) > 10:
                water_cells.append((x, y))

    for _ in range(count):
        if not water_cells:
            break
        pos = random.choice(water_cells)
        kind = random.choice(["torpedo", "torpedo", "repair"])  # 2:1 torpedo bias
        crates.append(SupplyCrate(x=pos[0], y=pos[1], kind=kind))
        # Spread them out
        water_cells = [(wx, wy) for wx, wy in water_cells
                       if abs(wx - pos[0]) + abs(wy - pos[1]) > 12]

    return crates


# ── Main game class ───────────────────────────────────────────────────

class SonarGame:
    """Core game logic and rendering for Terminal Sonar Simulator."""

    def __init__(self, stdscr, difficulty: str = "normal", num_enemies: int = 10,
                 seed: Optional[int] = None):
        """Initialise a new game.

        Args:
            stdscr:       The curses window.
            difficulty:   One of 'easy', 'normal', 'hard'.
            num_enemies:  Override number of enemies (takes precedence over difficulty).
            seed:         Random seed for world generation.
        """
        self.stdscr = stdscr

        # Apply difficulty preset
        preset = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS["normal"])
        self.difficulty = difficulty
        self.enemy_fire_chance = preset["enemy_fire_chance"]
        self.ping_cooldown_max = preset["ping_cooldown"]

        # Generate world (seed only used for world gen, then re-randomise)
        self.rng = random.Random()
        if seed is not None:
            random.seed(seed)
        self.world = generate_world(WORLD_W, WORLD_H)
        self.rng_state = random.getstate()

        actual_enemies = num_enemies if num_enemies != 10 else preset["enemies"]
        max_torp = preset["torpedo_count"]

        self.num_enemies = actual_enemies
        self.enemies = spawn_enemies(
            self.world, actual_enemies,
            hp_mult=preset["enemy_hp_mult"],
            detect_mult=preset["enemy_detect_mult"],
        )
        self.supply_crates: List[SupplyCrate] = spawn_supply_crates(self.world)
        self.torpedoes: List[Torpedo] = []
        self.pings: List[SonarPing] = []
        self.particles: List[Particle] = []
        self.sub = Submarine(torpedoes=max_torp, max_hp=10)
        self.max_torpedoes = max_torp
        self.frame = 0
        self.start_time = time.time()
        self.show_minimap = True
        self.game_over = False
        self.victory = False
        self.messages: List[Tuple[str, int]] = []  # (text, expire_frame)
        self.sonar_mode = "active"  # "active" or "passive"
        self.detected_enemies: Set[int] = set()
        self.last_ping_frame = -999
        self.depth_view_penalty = {0: 1.0, 1: 0.7, 2: 0.4}
        self.depth_damage_reduction = {0: 0.0, 1: 0.25, 2: 0.5}
        self.bearing_arrows: List[Tuple[str, str, int]] = []  # (arrow_char, label, color)

        # Initialise colours
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)           # sonar ring
        curses.init_pair(2, curses.COLOR_GREEN, -1)           # friendly
        curses.init_pair(3, curses.COLOR_RED, -1)             # enemy destroyer
        curses.init_pair(4, curses.COLOR_YELLOW, -1)          # land / warnings
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)         # enemy submarine
        curses.init_pair(6, curses.COLOR_BLUE, -1)            # water / shallows
        curses.init_pair(7, curses.COLOR_WHITE, -1)           # text
        curses.init_pair(8, curses.COLOR_RED, curses.COLOR_RED)       # damage flash
        curses.init_pair(9, 8, -1)                            # dark gray
        curses.init_pair(10, curses.COLOR_CYAN, curses.COLOR_BLACK)   # ping bg
        curses.init_pair(11, curses.COLOR_GREEN, curses.COLOR_BLACK)  # HUD
        curses.init_pair(12, curses.COLOR_WHITE, curses.COLOR_BLUE)    # supply crate
        curses.init_pair(13, curses.COLOR_RED, curses.COLOR_WHITE)     # enemy bearing

        self.max_y, self.max_x = stdscr.getmaxyx()

    # ── Helpers ────────────────────────────────────────────────────────

    def add_message(self, text: str, duration: int = 120):
        """Add a HUD message with an expiry frame."""
        self.messages.append((text, self.frame + duration))

    @staticmethod
    def dist(x1, y1, x2, y2) -> float:
        """Euclidean distance between two points."""
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    @staticmethod
    def in_bounds(x, y) -> bool:
        """Check whether (x, y) is inside the world grid."""
        return 0 <= x < WORLD_W and 0 <= y < WORLD_H

    def is_passable(self, x, y) -> bool:
        """Check whether a cell can be moved into (water or shallows)."""
        if not self.in_bounds(x, y):
            return False
        return self.world[y][x] != CellType.LAND

    @staticmethod
    def bearing_arrow(from_x, from_y, to_x, to_y) -> str:
        """Return a Unicode arrow character indicating direction from→to."""
        angle = math.atan2(to_y - from_y, to_x - from_x)
        # 8-direction arrows
        arrows = ['→', '↘', '↓', '↙', '←', '↖', '↑', '↗']
        idx = round(angle / (math.pi / 4)) % 8
        return arrows[idx]

    # ── Input handling ─────────────────────────────────────────────────

    def handle_input(self, key):
        """Process a single keypress from the player."""
        if self.game_over:
            if key in (ord('r'), ord('R')):
                self.__init__(self.stdscr, difficulty=self.difficulty,
                              num_enemies=self.num_enemies)
            return

        dx, dy = 0, 0
        if key in (curses.KEY_UP, ord('w'), ord('W')):
            dy = -1
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            dy = 1
        elif key in (curses.KEY_LEFT, ord('a'), ord('A')):
            dx = -1
        elif key in (curses.KEY_RIGHT, ord('d'), ord('D')):
            dx = 1

        # Movement generates noise at periscope depth
        if dx != 0 or dy != 0:
            noise = {0: 0.15, 1: 0.08, 2: 0.03}[self.sub.depth]
            self.sub.noise_level = min(1.0, self.sub.noise_level + noise)

        nx = self.sub.x + dx
        ny = self.sub.y + dy
        if self.is_passable(nx, ny):
            self.sub.x = nx
            self.sub.y = ny

        # Sonar ping (SPACE)
        if key == ord(' ') and self.sub.ping_cooldown <= 0:
            self.sub.ping_cooldown = self.ping_cooldown_max
            self.pings.append(SonarPing(self.sub.x, self.sub.y, 0, PING_RADIUS, active_ping=True))
            self.sub.pings_used += 1
            self.last_ping_frame = self.frame
            self.sub.noise_level = min(1.0, self.sub.noise_level + 0.4)
            self.add_message("⚡ ACTIVE SONAR PING!", 60)
            # Active pings alert enemies
            for e in self.enemies:
                d = self.dist(self.sub.x, self.sub.y, e.x, e.y)
                if d < PING_RADIUS + 5:
                    e.alert_level = min(1.0, e.alert_level + 0.5)
                    if d < e.detect_range:
                        e.detected_player = True

        # Toggle sonar mode (E)
        if key in (ord('e'), ord('E')):
            if self.sonar_mode == "active":
                self.sonar_mode = "passive"
                self.add_message("👂 Passive sonar mode (reduced range, stealthier)", 90)
            else:
                self.sonar_mode = "active"
                self.add_message("📡 Active sonar mode (full range, pings reveal you)", 90)

        # Passive listening burst (P)
        if key in (ord('p'), ord('P')):
            if self.sonar_mode == "passive":
                if self.sub.ping_cooldown <= 0:
                    self.pings.append(SonarPing(self.sub.x, self.sub.y, 0, PASSIVE_RADIUS, active_ping=False))
                    self.sub.ping_cooldown = self.ping_cooldown_max // 2  # passive costs half cooldown
                    self.add_message("👂 Passive listening...", 40)
                else:
                    self.add_message("Sonar recharging...", 30)
            else:
                self.add_message("Switch to passive mode first (E)", 60)

        # Change depth (Z = dive deeper, X = rise shallower)
        if key == ord('z'):
            if self.sub.depth < 2:
                self.sub.depth += 1
                depths = ["Periscope depth", "Shallow depth", "Deep depth"]
                self.add_message(f"⬇ Diving: {depths[self.sub.depth]}", 60)
            else:
                self.add_message("Already at maximum depth", 40)
        if key == ord('x'):
            if self.sub.depth > 0:
                self.sub.depth -= 1
                depths = ["Periscope depth", "Shallow depth", "Deep depth"]
                self.add_message(f"⬆ Rising: {depths[self.sub.depth]}", 60)
            else:
                self.add_message("Already at periscope depth", 40)

        # Fire torpedo at nearest (F)
        if key in (ord('f'), ord('F')):
            self.fire_torpedo(target_select="nearest")

        # Fire torpedo at farthest classified target (G — long-range)
        if key in (ord('g'), ord('G')):
            self.fire_torpedo(target_select="farthest")

        # Toggle minimap (M)
        if key in (ord('m'), ord('M')):
            self.show_minimap = not self.show_minimap

    def fire_torpedo(self, target_select: str = "nearest"):
        """Launch a torpedo at a classified enemy.

        Args:
            target_select: 'nearest' or 'farthest' classified target in range.
        """
        if self.sub.torpedo_cooldown > 0:
            self.add_message("Torpedo reloading...", 30)
            return
        if self.sub.torpedoes <= 0:
            self.add_message("⚠ No torpedoes remaining!", 60)
            return

        # Find target based on selection mode
        candidates = [
            (e, self.dist(self.sub.x, self.sub.y, e.x, e.y))
            for e in self.enemies if e.classified
        ]
        candidates_in_range = [(e, d) for e, d in candidates if d <= TORPEDO_RANGE]

        if not candidates_in_range:
            self.add_message("⚠ No classified targets in range!", 60)
            return

        if target_select == "farthest":
            target, _ = max(candidates_in_range, key=lambda ed: ed[1])
        else:
            target, _ = min(candidates_in_range, key=lambda ed: ed[1])

        dx = target.x - self.sub.x
        dy = target.y - self.sub.y
        mag = math.sqrt(dx * dx + dy * dy)
        if mag == 0:
            return
        dx /= mag
        dy /= mag

        self.torpedoes.append(Torpedo(
            x=self.sub.x, y=self.sub.y,
            dx=dx * TORPEDO_SPEED, dy=dy * TORPEDO_SPEED,
            friendly=True, dmg=2
        ))
        self.sub.torpedoes -= 1
        self.sub.torpedo_cooldown = COOLDOWN_TORPEDO
        self.sub.noise_level = min(1.0, self.sub.noise_level + 0.2)
        mode_label = "long-range" if target_select == "farthest" else ""
        self.add_message(
            f"🐟 Torpedo fired{(' (' + mode_label + ')') if mode_label else ''}! "
            f"({self.sub.torpedoes} remaining)", 60
        )

    # ── Update loop ────────────────────────────────────────────────────

    def update_pings(self):
        """Expand sonar pings and detect enemies they reveal."""
        self.detected_enemies.clear()
        for ping in self.pings[:]:
            ping.radius += 0.8
            ping.age += 1
            if ping.radius > ping.max_radius:
                self.pings.remove(ping)
                continue

            # Check which enemies the ping reveals
            for e in self.enemies:
                d = self.dist(ping.x, ping.y, e.x, e.y)
                if abs(d - ping.radius) < 1.5:
                    e.classified = True
                    self.detected_enemies.add(id(e))

        # Also detect by proximity (sub's own sensors)
        view_r = VIEW_RADIUS * self.depth_view_penalty[self.sub.depth]
        if self.sonar_mode == "passive":
            view_r = min(view_r, PASSIVE_RADIUS)

        for e in self.enemies:
            d = self.dist(self.sub.x, self.sub.y, e.x, e.y)
            if d <= view_r:
                e.classified = True
                self.detected_enemies.add(id(e))

    def update_enemies(self):
        """Move enemies, manage AI, and handle enemy torpedo firing."""
        for e in self.enemies[:]:
            if e.hp <= 0:
                score_map = {
                    EnemyType.DESTROYER: 300,
                    EnemyType.SUBMARINE: 500,
                    EnemyType.PATROL_BOAT: 150,
                }
                pts = score_map[e.etype]
                self.sub.score += pts
                self.sub.kills += 1
                self.add_message(f"💥 {e.etype.value} destroyed! (+{pts} pts)", 120)
                # Explosion particles
                for _ in range(15):
                    angle = random.uniform(0, math.pi * 2)
                    speed = random.uniform(0.3, 1.5)
                    self.particles.append(Particle(
                        e.x, e.y,
                        math.cos(angle) * speed, math.sin(angle) * speed,
                        random.randint(10, 25),
                        random.choice(["*", "●", "✦", "◆"])
                    ))
                self.enemies.remove(e)
                continue

            e.move_timer += 1

            # Alert decay
            e.alert_level = max(0, e.alert_level - 0.005)

            # Engine noise timer (passive sonar can detect this)
            e.engine_noise_timer = max(0, e.engine_noise_timer - 1)

            if e.detected_player and e.alert_level > 0.3:
                # Chase the player
                dx = self.sub.x - e.x
                dy = self.sub.y - e.y
                mag = math.sqrt(dx * dx + dy * dy)
                if mag > 0:
                    dx /= mag
                    dy /= mag
                # Occasionally randomize direction slightly
                if random.random() < 0.1:
                    angle = random.uniform(-0.5, 0.5)
                    cos_a, sin_a = math.cos(angle), math.sin(angle)
                    dx, dy = dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a
            else:
                # Patrol randomly
                if e.move_timer % 20 == 0:
                    e.direction = random.randint(0, 359)
                dx = math.cos(math.radians(e.direction))
                dy = math.sin(math.radians(e.direction))

            if e.move_timer % max(1, (3 - e.speed)) == 0:
                nx = e.x + round(dx)
                ny = e.y + round(dy)
                if self.is_passable(nx, ny):
                    e.x = nx
                    e.y = ny
                else:
                    e.direction = random.randint(0, 359)

            # Emit engine noise pulses periodically (for passive detection)
            if e.engine_noise_timer == 0:
                e.engine_noise_timer = random.randint(15, 40)

            # Player noise can alert nearby enemies
            if self.sub.noise_level > 0.3:
                d = self.dist(e.x, e.y, self.sub.x, self.sub.y)
                noise_range = 8 * self.sub.noise_level
                if d < noise_range:
                    e.alert_level = min(1.0, e.alert_level + 0.02)
                    if d < e.detect_range * 0.7:
                        e.detected_player = True

            # Enemy fires at player if close and detected
            if e.detected_player:
                d = self.dist(e.x, e.y, self.sub.x, self.sub.y)
                if d < 8 and random.random() < self.enemy_fire_chance:
                    # Enemy torpedo
                    fdx = self.sub.x - e.x
                    fdy = self.sub.y - e.y
                    fmag = math.sqrt(fdx * fdx + fdy * fdy)
                    if fmag > 0:
                        fdx /= fmag
                        fdy /= fmag
                    self.torpedoes.append(Torpedo(
                        e.x, e.y, fdx * 1.5, fdy * 1.5,
                        friendly=False, dmg=e.torpedo_dmg
                    ))
                    self.add_message(f"⚠ Incoming torpedo from {e.etype.value}!", 90)

    def update_torpedoes(self):
        """Move all torpedoes and check for collisions."""
        for t in self.torpedoes[:]:
            t.x += t.dx
            t.y += t.dy
            t.age += 1

            # Trail particle
            if t.age % 2 == 0:
                self.particles.append(Particle(
                    t.x, t.y, 0, 0, 8,
                    "·" if t.friendly else "∘"
                ))

            # Out of bounds or too old
            if not self.in_bounds(int(t.x), int(t.y)) or t.age > 60:
                self.torpedoes.remove(t)
                continue

            # Hit land
            ix, iy = int(t.x), int(t.y)
            if self.world[iy][ix] == CellType.LAND:
                self.torpedoes.remove(t)
                continue

            # Check collisions
            if t.friendly:
                for e in self.enemies:
                    if self.dist(t.x, t.y, e.x, e.y) < 1.5:
                        e.hp -= t.dmg
                        self.torpedoes.remove(t)
                        # Hit particles
                        for _ in range(8):
                            angle = random.uniform(0, math.pi * 2)
                            speed = random.uniform(0.5, 1.0)
                            self.particles.append(Particle(
                                t.x, t.y,
                                math.cos(angle) * speed, math.sin(angle) * speed,
                                random.randint(8, 15), "◆"
                            ))
                        self.add_message(f"🎯 Hit on {e.etype.value}! (HP: {max(0, e.hp)})", 60)
                        break
            else:
                # Enemy torpedo hitting player
                if self.dist(t.x, t.y, self.sub.x, self.sub.y) < 1.5:
                    # Depth affects damage
                    damage = t.dmg
                    reduction = self.depth_damage_reduction[self.sub.depth]
                    damage = max(1, round(damage * (1 - reduction)))
                    self.sub.hp -= damage
                    self.torpedoes.remove(t)
                    depth_label = ["periscope", "shallow", "deep"][self.sub.depth]
                    self.add_message(
                        f"💥 Torpedo hit! -{damage} HP (depth: {depth_label})", 90
                    )
                    if self.sub.hp <= 0:
                        self.game_over = True
                        self.add_message("☠ SUBMARINE DESTROYED! Press R to restart.", 9999)

    def update_supply_crates(self):
        """Check if the player picks up any supply crate."""
        for crate in self.supply_crates[:]:
            crate.age += 1
            if self.dist(self.sub.x, self.sub.y, crate.x, crate.y) < 1.5:
                if crate.kind == "torpedo":
                    self.sub.torpedoes = min(self.max_torpedoes, self.sub.torpedoes + 2)
                    self.add_message("📦 Picked up torpedo supply! (+2)", 90)
                elif crate.kind == "repair":
                    heal = min(3, self.sub.max_hp - self.sub.hp)
                    self.sub.hp += heal
                    self.add_message(f"🔧 Repair kit! (+{heal} HP)", 90)
                self.supply_crates.remove(crate)

    def update_particles(self):
        """Advance all visual particles by one frame."""
        for p in self.particles[:]:
            p.x += p.dx
            p.y += p.dy
            p.dx *= 0.95
            p.dy *= 0.95
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def update_bearing_indicators(self):
        """Compute bearing arrows toward classified enemies for the HUD."""
        self.bearing_arrows.clear()
        for e in self.enemies:
            if e.classified:
                d = self.dist(self.sub.x, self.sub.y, e.x, e.y)
                arrow = self.bearing_arrow(self.sub.x, self.sub.y, e.x, e.y)
                label = f"{e.symbol}{int(d)}"
                self.bearing_arrows.append((arrow, label, e.color))

    def update(self):
        """Advance the simulation by one frame."""
        if self.game_over:
            return

        self.frame += 1

        # Cooldowns
        if self.sub.ping_cooldown > 0:
            self.sub.ping_cooldown -= 1
        if self.sub.torpedo_cooldown > 0:
            self.sub.torpedo_cooldown -= 1

        # Noise decay
        self.sub.noise_level = max(0, self.sub.noise_level - 0.01)

        self.update_pings()
        self.update_enemies()
        self.update_torpedoes()
        self.update_supply_crates()
        self.update_particles()
        self.update_bearing_indicators()

        # Slow health regen at deep depth
        if self.sub.depth == 2 and self.frame % 60 == 0 and self.sub.hp < self.sub.max_hp:
            self.sub.hp = min(self.sub.max_hp, self.sub.hp + 1)
            self.add_message("💚 Deep-depth repair (+1 HP)", 40)

        # Ammo resupply (slow)
        if self.frame % 300 == 0 and self.sub.torpedoes < self.max_torpedoes:
            self.sub.torpedoes += 1
            self.add_message("📦 Torpedo resupplied!", 60)

        # Victory check
        if len(self.enemies) == 0:
            self.victory = True
            self.game_over = True
            self.sub.score += 1000
            elapsed = int(time.time() - self.start_time)
            time_bonus = max(0, 600 - elapsed)  # bonus for finishing under 10 min
            self.sub.score += time_bonus
            self.add_message(f"🏆 ALL ENEMIES DESTROYED! VICTORY! (Time bonus: +{time_bonus})", 9999)

        # Expire messages
        self.messages = [(t, exp) for t, exp in self.messages if exp > self.frame]

    # ── Rendering ──────────────────────────────────────────────────────

    def render(self):
        """Draw the entire game frame to the terminal."""
        self.stdscr.clear()
        h, w = self.max_y, self.max_x

        # Camera centred on submarine
        cam_x = self.sub.x - w // 2
        cam_y = self.sub.y - (h - 6) // 2

        view_r = VIEW_RADIUS * self.depth_view_penalty[self.sub.depth]

        # ── Render map ─────────────────────────────────────────────────
        for sy in range(h - 6):  # Leave 6 lines for HUD (was 4)
            for sx in range(w):
                wx = cam_x + sx
                wy = cam_y + sy

                dist_to_sub = self.dist(wx, wy, self.sub.x, self.sub.y)
                in_view = dist_to_sub <= view_r
                in_ping = any(
                    abs(self.dist(wx, wy, p.x, p.y) - p.radius) < 2.0
                    for p in self.pings
                )

                if not in_view and not in_ping:
                    try:
                        self.stdscr.addch(sy, sx, ' ', curses.color_pair(6))
                    except curses.error:
                        pass
                    continue

                ch = ' '
                color = curses.color_pair(6)

                if not self.in_bounds(wx, wy):
                    ch = ' '
                    color = curses.color_pair(6)
                else:
                    cell = self.world[wy][wx]
                    if cell == CellType.LAND:
                        is_edge = any(
                            self.in_bounds(wx + ddx, wy + ddy)
                            and self.world[wy + ddy][wx + ddx] != CellType.LAND
                            for ddy, ddx in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                        )
                        ch = '▓' if is_edge else '█'
                        color = curses.color_pair(4)
                    elif cell == CellType.SHALLOWS:
                        ch = '░' if (wx + wy) % 3 == 0 else '·'
                        color = curses.color_pair(9)
                    else:
                        wave = (wx * 3 + wy * 7 + self.frame // 8) % 5
                        if dist_to_sub <= view_r * 0.5:
                            ch = ['~', '≈', '∼', '∽', '∼'][wave]
                        else:
                            ch = ['·', '˙', '·', '˙', '·'][wave]
                        color = curses.color_pair(9) if self.sub.depth == 2 else curses.color_pair(6)

                # Ping highlight
                for p in self.pings:
                    if p.active_ping and abs(self.dist(wx, wy, p.x, p.y) - p.radius) < 1.2:
                        color = curses.color_pair(1)
                        ch = '○' if self.dist(wx, wy, p.x, p.y) < p.radius - 0.5 else '∘'
                        break

                # Supply crates
                for crate in self.supply_crates:
                    if crate.x == wx and crate.y == wy:
                        ch = '📦' if crate.kind == "torpedo" else '🔧'
                        # Fallback to simple chars since emoji may not render in curses
                        ch = 'T' if crate.kind == "torpedo" else '+'
                        color = curses.color_pair(12) | curses.A_BOLD

                # Enemies
                for e in self.enemies:
                    if e.x == wx and e.y == wy:
                        if id(e) in self.detected_enemies or e.classified:
                            ch = e.symbol
                            color = curses.color_pair(e.color) | curses.A_BOLD

                # Torpedoes
                for t in self.torpedoes:
                    if abs(t.x - wx) < 1 and abs(t.y - wy) < 1:
                        ch = '▸' if t.friendly else '◃'
                        color = curses.color_pair(2) if t.friendly else curses.color_pair(3)

                # Particles
                for p in self.particles:
                    if abs(p.x - wx) < 1 and abs(p.y - wy) < 1:
                        ch = p.char
                        color = curses.color_pair(3)

                # Player submarine
                if wx == self.sub.x and wy == self.sub.y:
                    ch = '▲'
                    color = curses.color_pair(2) | curses.A_BOLD

                try:
                    self.stdscr.addch(sy, sx, ch, color)
                except curses.error:
                    pass

        # ── HUD ────────────────────────────────────────────────────────
        hud_y = h - 6
        depth_names = ["PERISCOPE", "SHALLOW", "DEEP"]

        # Elapsed time
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        time_str = f"{mins:02d}:{secs:02d}"

        # HP bar
        hp_pct = self.sub.hp / self.sub.max_hp
        hp_bar_len = 16
        hp_filled = int(hp_pct * hp_bar_len)
        hp_bar = '█' * hp_filled + '░' * (hp_bar_len - hp_filled)
        hp_color = (curses.color_pair(2) if hp_pct > 0.5
                    else curses.color_pair(4) if hp_pct > 0.25
                    else curses.color_pair(3))

        try:
            self.stdscr.addstr(hud_y, 0,
                f" HP:[{hp_bar}] {self.sub.hp}/{self.sub.max_hp}  "
                f"Time: {time_str}", hp_color)
        except curses.error:
            pass

        # Depth + mode + noise
        noise_pct = int(self.sub.noise_level * 100)
        noise_bar_len = 8
        noise_filled = int(self.sub.noise_level * noise_bar_len)
        noise_bar = '▓' * noise_filled + '░' * (noise_bar_len - noise_filled)
        try:
            self.stdscr.addstr(hud_y + 1, 0,
                f" Depth:{depth_names[self.sub.depth]}  Mode:{self.sonar_mode.upper():>6}  "
                f"Torps:{self.sub.torpedoes}/{self.max_torpedoes}  "
                f"Noise:[{noise_bar}]", curses.color_pair(11))
        except curses.error:
            pass

        # Cooldowns + stats
        ping_ready = "READY" if self.sub.ping_cooldown <= 0 else f"{self.sub.ping_cooldown}"
        torp_ready = "READY" if self.sub.torpedo_cooldown <= 0 else f"{self.sub.torpedo_cooldown}"
        try:
            self.stdscr.addstr(hud_y + 2, 0,
                f" Ping:{ping_ready:>5}  Torp:{torp_ready:>5}  "
                f"Enemies:{len(self.enemies)}  Score:{self.sub.score}  "
                f"Kills:{self.sub.kills}/{self.num_enemies}",
                curses.color_pair(7))
        except curses.error:
            pass

        # Bearing indicators (directions to classified enemies)
        if self.bearing_arrows:
            bearing_str = " ".join(
                f"{arrow}{label}" for arrow, label, _ in self.bearing_arrows[:6]
            )
            try:
                self.stdscr.addstr(hud_y + 3, 0,
                    f" Contacts: {bearing_str}", curses.color_pair(1))
            except curses.error:
                pass
        else:
            try:
                self.stdscr.addstr(hud_y + 3, 0,
                    " Contacts: None classified", curses.color_pair(9))
            except curses.error:
                pass

        # Messages
        msg_y = hud_y - 1
        for text, _ in reversed(self.messages[-3:]):
            try:
                self.stdscr.addstr(msg_y, 0, f" {text}"[:w], curses.color_pair(4))
            except curses.error:
                pass
            msg_y -= 1

        # Controls hint
        try:
            self.stdscr.addstr(hud_y + 4, 0,
                " WASD:Move  SPACE:Ping  F:Fire  G:LongFire  E:Mode  "
                "Z/X:Depth  P:Listen  M:Map  Q:Quit", curses.color_pair(9))
        except curses.error:
            pass

        # Difficulty indicator
        try:
            self.stdscr.addstr(hud_y + 5, 0,
                f" Difficulty: {self.difficulty.upper()}", curses.color_pair(9))
        except curses.error:
            pass

        # ── Minimap ────────────────────────────────────────────────────
        if self.show_minimap:
            mm_w, mm_h = 20, 10
            mm_x = w - mm_w - 2
            mm_y = 1
            try:
                self.stdscr.addstr(mm_y - 1, mm_x - 1, '┌' + '─' * mm_w + '┐', curses.color_pair(1))
                for my in range(mm_h):
                    self.stdscr.addstr(mm_y + my, mm_x - 1, '│', curses.color_pair(1))
                    self.stdscr.addstr(mm_y + my, mm_x + mm_w, '│', curses.color_pair(1))
                self.stdscr.addstr(mm_y + mm_h, mm_x - 1, '└' + '─' * mm_w + '┘', curses.color_pair(1))
            except curses.error:
                pass

            for my in range(mm_h):
                for mx in range(mm_w):
                    wx_mm = int(mx * WORLD_W / mm_w)
                    wy_mm = int(my * WORLD_H / mm_h)
                    ch, color = '·', curses.color_pair(6)
                    if self.in_bounds(wx_mm, wy_mm):
                        cell = self.world[wy_mm][wx_mm]
                        if cell == CellType.LAND:
                            ch, color = '█', curses.color_pair(4)
                        elif cell == CellType.SHALLOWS:
                            ch, color = '░', curses.color_pair(9)
                        else:
                            ch, color = '·', curses.color_pair(6)

                    # Supply crates on minimap
                    for crate in self.supply_crates:
                        cmx = int(crate.x * mm_w / WORLD_W)
                        cmy = int(crate.y * mm_h / WORLD_H)
                        if mx == cmx and my == cmy:
                            ch, color = '+', curses.color_pair(4) | curses.A_BOLD

                    # Player on minimap
                    pmx = int(self.sub.x * mm_w / WORLD_W)
                    pmy = int(self.sub.y * mm_h / WORLD_H)
                    if mx == pmx and my == pmy:
                        ch, color = '▲', curses.color_pair(2) | curses.A_BOLD

                    # Enemies on minimap
                    for e in self.enemies:
                        if e.classified:
                            emx = int(e.x * mm_w / WORLD_W)
                            emy = int(e.y * mm_h / WORLD_H)
                            if mx == emx and my == emy:
                                ch, color = e.symbol, curses.color_pair(e.color)

                    try:
                        self.stdscr.addch(mm_y + my, mm_x + mx, ch, color)
                    except curses.error:
                        pass

        self.stdscr.refresh()

    # ── Main loop ──────────────────────────────────────────────────────

    def run(self):
        """Main game loop — handles input, updates, and rendering."""
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(80)

        self.add_message("⚓ SONAR SIMULATOR — Command your submarine!", 180)
        self.add_message("WASD: move | SPACE: ping | F/G: fire | E: mode | Z/X: depth", 180)
        self.add_message(f"Difficulty: {self.difficulty.upper()} | Enemies: {self.num_enemies}", 180)

        while True:
            key = self.stdscr.getch()
            if key in (ord('q'), ord('Q')):
                break
            if key != -1:
                self.handle_input(key)

            self.update()
            self.render()

            if self.game_over and not self.victory:
                self._show_game_over_screen()
            elif self.victory:
                self._show_victory_screen()

    def _show_game_over_screen(self):
        """Display the defeat screen and wait for restart/quit."""
        h, w = self.max_y, self.max_x
        cy, cx = h // 2, w // 2
        try:
            self.stdscr.addstr(cy - 2, cx - 14, "╔══════════════════════════╗", curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(cy - 1, cx - 14, "║    SUBMARINE LOST         ║", curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(cy, cx - 14,     f"║  Score: {self.sub.score:>10}      ║", curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(cy + 1, cx - 14, "║ Press R to restart         ║", curses.color_pair(7))
            self.stdscr.addstr(cy + 2, cx - 14, "║ Press Q to quit            ║", curses.color_pair(7))
            self.stdscr.addstr(cy + 3, cx - 14, "╚══════════════════════════╝", curses.color_pair(3) | curses.A_BOLD)
        except curses.error:
            pass
        self.stdscr.refresh()

        key = self.stdscr.getch()
        if key in (ord('r'), ord('R')):
            self.__init__(self.stdscr, difficulty=self.difficulty,
                          num_enemies=self.num_enemies)
        elif key in (ord('q'), ord('Q')):
            raise SystemExit(0)

    def _show_victory_screen(self):
        """Display the victory screen and wait for restart/quit."""
        h, w = self.max_y, self.max_x
        cy, cx = h // 2, w // 2
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        try:
            self.stdscr.addstr(cy - 2, cx - 14, "╔══════════════════════════╗", curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(cy - 1, cx - 14, "║     🏆 VICTORY! 🏆        ║", curses.color_pair(2) | curses.A_BOLD)
            self.stdscr.addstr(cy, cx - 14,     f"║  Score: {self.sub.score:>10}      ║", curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(cy + 1, cx - 14, f"║  Time:  {mins:>3}:{secs:02d}            ║", curses.color_pair(7))
            self.stdscr.addstr(cy + 2, cx - 14, "║ Press R to play again      ║", curses.color_pair(7))
            self.stdscr.addstr(cy + 3, cx - 14, "╚══════════════════════════╝", curses.color_pair(2) | curses.A_BOLD)
        except curses.error:
            pass
        self.stdscr.refresh()

        key = self.stdscr.getch()
        if key in (ord('r'), ord('R')):
            self.__init__(self.stdscr, difficulty=self.difficulty,
                          num_enemies=self.num_enemies)
        elif key in (ord('q'), ord('Q')):
            raise SystemExit(0)


# ── CLI entry point ───────────────────────────────────────────────────

def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="sonar",
        description="Terminal Sonar Simulator — command a submarine in a fog-of-war ocean!",
        epilog="Use WASD to move, SPACE to ping sonar, F to fire torpedoes.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {VERSION}",
        help="Print version and exit",
    )
    parser.add_argument(
        "--difficulty", choices=["easy", "normal", "hard"], default="normal",
        help="Set game difficulty (default: normal)",
    )
    parser.add_argument(
        "--enemies", type=int, default=None,
        help="Override number of enemies (default: set by difficulty)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducible world generation",
    )
    return parser.parse_args(argv)


def main():
    """Entry point — parse args and launch the game."""
    args = parse_args()
    num_enemies = args.enemies if args.enemies is not None else DIFFICULTY_PRESETS[args.difficulty]["enemies"]

    try:
        stdscr = curses.initscr()
        game = SonarGame(stdscr, difficulty=args.difficulty,
                         num_enemies=num_enemies, seed=args.seed)
        game.run()
    finally:
        curses.endwin()


if __name__ == "__main__":
    main()