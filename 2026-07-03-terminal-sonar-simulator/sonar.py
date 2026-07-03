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
  M                  - Toggle minimap
  Q                  - Quit
"""

import curses
import random
import math
import time
import sys
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ── Constants ──────────────────────────────────────────────────────────
WORLD_W = 120
WORLD_H = 60
VIEW_RADIUS = 12
PING_RADIUS = 18
PASSIVE_RADIUS = 6
TORPEDO_RANGE = 20
TORPEDO_SPEED = 2
SUB_SPEED = 1
ENEMY_SPEED = 1
MAX_TORPEDOES = 8
COOLDOWN_PING = 15      # frames between pings
COOLDOWN_TORPEDO = 10
DETECTION_THRESHOLD = 0.35  # probability enemy detects your ping per frame


class CellType(Enum):
    WATER = 0
    LAND = 1
    SHALLOWS = 2


class EnemyType(Enum):
    DESTROYER = "Destroyer"
    SUBMARINE = "Submarine"
    PATROL_BOAT = "Patrol Boat"


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


@dataclass
class Submarine:
    x: int = 60
    y: int = 30
    hp: int = 10
    max_hp: int = 10
    torpedoes: int = MAX_TORPEDOES
    ping_cooldown: int = 0
    torpedo_cooldown: int = 0
    depth: int = 0  # 0=periscope, 1=shallow, 2=deep
    score: int = 0
    pings_used: int = 0
    kills: int = 0


@dataclass
class Enemy:
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
    alert_level: float = 0.0       # 0-1, increases with pings
    move_timer: int = 0
    direction: int = 0              # angle in degrees


@dataclass
class Torpedo:
    x: float
    y: float
    dx: float
    dy: float
    friendly: bool
    dmg: int = 1
    age: int = 0


@dataclass
class SonarPing:
    x: int
    y: int
    radius: float
    max_radius: int
    age: int = 0
    active_ping: bool = True   # True=active (you sent it), False=passive listening


@dataclass
class Particle:
    x: float
    y: float
    dx: float
    dy: float
    life: int
    char: str


def generate_world(width: int, height: int) -> List[List[CellType]]:
    """Generate an ocean world with islands."""
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


def spawn_enemies(world: List[List[CellType]], count: int) -> List[Enemy]:
    """Spawn enemy vessels at random water locations."""
    enemies = []
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
            hp=cfg["hp"], speed=cfg["speed"],
            detect_range=cfg["detect_range"],
            symbol=cfg["symbol"], color=cfg["color"],
            torpedo_dmg=cfg["torpedo_dmg"],
            direction=random.randint(0, 359),
        )
        enemies.append(enemy)
        # Remove nearby cells to avoid clustering
        water_cells = [(wx, wy) for wx, wy in water_cells
                       if abs(wx - pos[0]) + abs(wy - pos[1]) > 8]

    return enemies


class SonarGame:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.sub = Submarine()
        self.world = generate_world(WORLD_W, WORLD_H)
        self.num_enemies = 10
        self.enemies = spawn_enemies(self.world, self.num_enemies)
        self.torpedoes: List[Torpedo] = []
        self.pings: List[SonarPing] = []
        self.particles: List[Particle] = []
        self.frame = 0
        self.show_minimap = True
        self.game_over = False
        self.victory = False
        self.messages: List[Tuple[str, int]] = []  # (text, expire_frame)
        self.sonar_mode = "active"  # "active" or "passive"
        self.detected_enemies: set = set()  # enemy ids currently visible
        self.last_ping_frame = -999
        self.depth_view_penalty = {0: 1.0, 1: 0.7, 2: 0.4}

        # Colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)       # sonar ring
        curses.init_pair(2, curses.COLOR_GREEN, -1)       # friendly
        curses.init_pair(3, curses.COLOR_RED, -1)         # enemy destroyer
        curses.init_pair(4, curses.COLOR_YELLOW, -1)      # land
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)     # enemy submarine
        curses.init_pair(6, curses.COLOR_BLUE, -1)        # water/shallows
        curses.init_pair(7, curses.COLOR_WHITE, -1)       # text
        curses.init_pair(8, curses.COLOR_RED, curses.COLOR_RED)  # damage flash
        curses.init_pair(9, 8, -1)                        # dark gray for deep water
        curses.init_pair(10, curses.COLOR_CYAN, curses.COLOR_BLACK)  # ping bg
        curses.init_pair(11, curses.COLOR_GREEN, curses.COLOR_BLACK) # HUD

        self.max_y, self.max_x = stdscr.getmaxyx()

    def add_message(self, text: str, duration: int = 120):
        self.messages.append((text, self.frame + duration))

    def dist(self, x1, y1, x2, y2):
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def in_bounds(self, x, y):
        return 0 <= x < WORLD_W and 0 <= y < WORLD_H

    def is_passable(self, x, y):
        if not self.in_bounds(x, y):
            return False
        return self.world[y][x] != CellType.LAND

    def handle_input(self, key):
        if self.game_over:
            if key in (ord('r'), ord('R')):
                self.__init__(self.stdscr)
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

        # Diagonal movement
        nx = self.sub.x + dx
        ny = self.sub.y + dy
        if self.is_passable(nx, ny):
            self.sub.x = nx
            self.sub.y = ny

        # Sonar ping
        if key == ord(' ') and self.sub.ping_cooldown <= 0:
            self.sub.ping_cooldown = COOLDOWN_PING
            self.pings.append(SonarPing(self.sub.x, self.sub.y, 0, PING_RADIUS, active_ping=True))
            self.sub.pings_used += 1
            self.last_ping_frame = self.frame
            self.add_message("⚡ ACTIVE SONAR PING!", 60)
            # Active pings alert enemies
            for e in self.enemies:
                d = self.dist(self.sub.x, self.sub.y, e.x, e.y)
                if d < PING_RADIUS + 5:
                    e.alert_level = min(1.0, e.alert_level + 0.5)
                    if d < e.detect_range:
                        e.detected_player = True

        # Toggle sonar mode
        if key == ord('e') or key == ord('E'):
            if self.sonar_mode == "active":
                self.sonar_mode = "passive"
                self.add_message("👂 Passive sonar mode (reduced range, stealthier)", 90)
            else:
                self.sonar_mode = "active"
                self.add_message("📡 Active sonar mode (full range, pings reveal you)", 90)

        # Passive sonar listening
        if key == ord('p') or key == ord('P'):
            if self.sonar_mode == "passive":
                self.pings.append(SonarPing(self.sub.x, self.sub.y, 0, PASSIVE_RADIUS, active_ping=False))
                self.add_message("👂 Passive listening...", 40)

        # Change depth
        if key == ord('z'):
            self.sub.depth = max(0, self.sub.depth - 1)
            depths = ["Periscope depth", "Shallow depth", "Deep depth"]
            self.add_message(f"⬇ Diving: {depths[self.sub.depth]}", 60)
        if key == ord('x'):
            self.sub.depth = min(2, self.sub.depth + 1)
            depths = ["Periscope depth", "Shallow depth", "Deep depth"]
            self.add_message(f"⬆ Rising: {depths[self.sub.depth]}", 60)

        # Fire torpedo
        if key == ord('f') or key == ord('F'):
            self.fire_torpedo()

        # Toggle minimap
        if key == ord('m') or key == ord('M'):
            self.show_minimap = not self.show_minimap

    def fire_torpedo(self):
        if self.sub.torpedo_cooldown > 0:
            self.add_message("Torpedo reloading...", 30)
            return
        if self.sub.torpedoes <= 0:
            self.add_message("⚠ No torpedoes remaining!", 60)
            return

        # Find nearest classified enemy
        target = None
        min_dist = float('inf')
        for e in self.enemies:
            if e.classified:
                d = self.dist(self.sub.x, self.sub.y, e.x, e.y)
                if d < min_dist and d <= TORPEDO_RANGE:
                    min_dist = d
                    target = e

        if target is None:
            self.add_message("⚠ No classified targets in range!", 60)
            return

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
        self.add_message(f"🐟 Torpedo fired! ({self.sub.torpedoes} remaining)", 60)

    def update_pings(self):
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
        for e in self.enemies[:]:
            if e.hp <= 0:
                self.enemies.remove(e)
                self.sub.score += {"Destroyer": 300, "Submarine": 500, "Patrol Boat": 150}[e.etype.value]
                self.sub.kills += 1
                self.add_message(f"💥 {e.etype.value} destroyed! (+{300 if e.etype == EnemyType.DESTROYER else 500 if e.etype == EnemyType.SUBMARINE else 150} pts)", 120)
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
                continue

            e.move_timer += 1

            # Alert decay
            e.alert_level = max(0, e.alert_level - 0.005)

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

            # Enemy fires at player if close and detected
            if e.detected_player:
                d = self.dist(e.x, e.y, self.sub.x, self.sub.y)
                if d < 8 and random.random() < 0.03:
                    # Enemy torpedo
                    dx = self.sub.x - e.x
                    dy = self.sub.y - e.y
                    mag = math.sqrt(dx * dx + dy * dy)
                    if mag > 0:
                        dx /= mag
                        dy /= mag
                    self.torpedoes.append(Torpedo(
                        e.x, e.y, dx * 1.5, dy * 1.5,
                        friendly=False, dmg=e.torpedo_dmg
                    ))
                    self.add_message(f"⚠ Incoming torpedo from {e.etype.value}!", 90)

    def update_torpedoes(self):
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
                        self.add_message(f"🎯 Hit on {e.etype.value}! (HP: {e.hp})", 60)
                        break
            else:
                # Enemy torpedo hitting player
                if self.dist(t.x, t.y, self.sub.x, self.sub.y) < 1.5:
                    # Depth affects damage
                    damage = t.dmg
                    if self.sub.depth == 2:
                        damage = max(1, damage - 1)
                    self.sub.hp -= damage
                    self.torpedoes.remove(t)
                    self.add_message(f"💥 Torpedo hit! -{damage} HP (Depth: {self.sub.depth})", 90)
                    if self.sub.hp <= 0:
                        self.game_over = True
                        self.add_message("☠ SUBMARINE DESTROYED! Press R to restart.", 9999)

    def update_particles(self):
        for p in self.particles[:]:
            p.x += p.dx
            p.y += p.dy
            p.dx *= 0.95
            p.dy *= 0.95
            p.life -= 1
            if p.life <= 0:
                self.particles.remove(p)

    def update(self):
        if self.game_over:
            return

        self.frame += 1

        # Cooldowns
        if self.sub.ping_cooldown > 0:
            self.sub.ping_cooldown -= 1
        if self.sub.torpedo_cooldown > 0:
            self.sub.torpedo_cooldown -= 1

        self.update_pings()
        self.update_enemies()
        self.update_torpedoes()
        self.update_particles()

        # Slow health regen at deep depth
        if self.sub.depth == 2 and self.frame % 60 == 0 and self.sub.hp < self.sub.max_hp:
            self.sub.hp = min(self.sub.max_hp, self.sub.hp + 1)

        # Ammo resupply (slow)
        if self.frame % 300 == 0 and self.sub.torpedoes < MAX_TORPEDOES:
            self.sub.torpedoes += 1
            self.add_message("📦 Torpedo resupplied!", 60)

        # Victory check
        if len(self.enemies) == 0:
            self.victory = True
            self.game_over = True
            self.sub.score += 1000
            self.add_message("🏆 ALL ENEMIES DESTROYED! VICTORY!", 9999)

        # Expire messages
        self.messages = [(t, exp) for t, exp in self.messages if exp > self.frame]

    def render(self):
        self.stdscr.clear()
        h, w = self.max_y, self.max_x

        # Camera centered on submarine
        cam_x = self.sub.x - w // 2
        cam_y = self.sub.y - h // 2

        view_r = VIEW_RADIUS * self.depth_view_penalty[self.sub.depth]

        # Render map
        for sy in range(h - 4):  # Leave 4 lines for HUD
            for sx in range(w):
                wx = cam_x + sx
                wy = cam_y + sy

                # Fog of war: only show what's in range or revealed by pings
                dist_to_sub = self.dist(wx, wy, self.sub.x, self.sub.y)

                in_view = dist_to_sub <= view_r
                in_ping = any(
                    abs(self.dist(wx, wy, p.x, p.y) - p.radius) < 2.0
                    for p in self.pings
                )

                if not in_view and not in_ping:
                    # Deep fog
                    if sy < h - 4 and sx < w:
                        try:
                            self.stdscr.addch(sy, sx, ' ', curses.color_pair(6))
                        except curses.error:
                            pass
                    continue

                if not self.in_bounds(wx, wy):
                    ch = ' '
                    color = curses.color_pair(6)
                else:
                    cell = self.world[wy][wx]
                    if cell == CellType.LAND:
                        # Land character based on distance from edge
                        is_edge = False
                        for ddy, ddx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            ny, nx = wy + ddy, wx + ddx
                            if self.in_bounds(nx, ny) and self.world[ny][nx] != CellType.LAND:
                                is_edge = True
                                break
                        ch = '▓' if is_edge else '█'
                        color = curses.color_pair(4)
                    elif cell == CellType.SHALLOWS:
                        ch = '░' if (wx + wy) % 3 == 0 else '·'
                        color = curses.color_pair(9)
                    else:
                        # Water with subtle animation
                        wave = (wx * 3 + wy * 7 + self.frame // 8) % 5
                        if dist_to_sub <= view_r * 0.5:
                            ch = ['~', '≈', '∼', '∽', '∼'][wave]
                        else:
                            ch = ['·', '˙', '·', '˙', '·'][wave]
                        # Deeper = darker
                        if self.sub.depth == 2:
                            color = curses.color_pair(9)
                        else:
                            color = curses.color_pair(6)

                # Ping highlight
                for p in self.pings:
                    if p.active_ping and abs(self.dist(wx, wy, p.x, p.y) - p.radius) < 1.2:
                        color = curses.color_pair(1)
                        ch = '○' if self.dist(wx, wy, p.x, p.y) < p.radius - 0.5 else '∘'
                        break

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

        # ── HUD ──────────────────────────────────────────────────────
        hud_y = h - 4
        depth_names = ["PERISCOPE", "SHALLOW", "DEEP"]
        depth_symbols = ["🔭", "🫧", "🌊"]

        # HP bar
        hp_pct = self.sub.hp / self.sub.max_hp
        hp_bar_len = 20
        hp_filled = int(hp_pct * hp_bar_len)
        hp_bar = '█' * hp_filled + '░' * (hp_bar_len - hp_filled)
        hp_color = curses.color_pair(2) if hp_pct > 0.5 else (curses.color_pair(4) if hp_pct > 0.25 else curses.color_pair(3))

        try:
            self.stdscr.addstr(hud_y, 0, f" HP: [{hp_bar}] {self.sub.hp}/{self.sub.max_hp}", hp_color)
        except curses.error:
            pass

        # Depth + mode
        try:
            self.stdscr.addstr(hud_y + 1, 0, f" Depth: {depth_names[self.sub.depth]}  Mode: {self.sonar_mode.upper()}  Torpedoes: {self.sub.torpedoes}/{MAX_TORPEDOES}", curses.color_pair(11))
        except curses.error:
            pass

        # Cooldowns
        ping_ready = "READY" if self.sub.ping_cooldown <= 0 else f"{self.sub.ping_cooldown}"
        torp_ready = "READY" if self.sub.torpedo_cooldown <= 0 else f"{self.sub.torpedo_cooldown}"
        try:
            self.stdscr.addstr(hud_y + 2, 0,
                f" Ping: {ping_ready}  Torpedo: {torp_ready}  Enemies: {len(self.enemies)}  Score: {self.sub.score}  Kills: {self.sub.kills}",
                curses.color_pair(7))
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
            self.stdscr.addstr(hud_y + 3, 0, " WASD:Move  SPACE:Ping  F:Fire  E:Mode  Z/X:Depth  M:Map  Q:Quit", curses.color_pair(9))
        except curses.error:
            pass

        # Minimap
        if self.show_minimap:
            mm_w, mm_h = 20, 10
            mm_x = w - mm_w - 2
            mm_y = 1
            try:
                # Border
                self.stdscr.addstr(mm_y - 1, mm_x - 1, '┌' + '─' * mm_w + '┐', curses.color_pair(1))
                for my in range(mm_h):
                    self.stdscr.addstr(mm_y + my, mm_x - 1, '│', curses.color_pair(1))
                    self.stdscr.addstr(mm_y + my, mm_x + mm_w, '│', curses.color_pair(1))
                self.stdscr.addstr(mm_y + mm_h, mm_x - 1, '└' + '─' * mm_w + '┘', curses.color_pair(1))
            except curses.error:
                pass

            for my in range(mm_h):
                for mx in range(mm_w):
                    wx = int(mx * WORLD_W / mm_w)
                    wy = int(my * WORLD_H / mm_h)
                    if self.in_bounds(wx, wy):
                        cell = self.world[wy][wx]
                        if cell == CellType.LAND:
                            ch, color = '█', curses.color_pair(4)
                        elif cell == CellType.SHALLOWS:
                            ch, color = '░', curses.color_pair(9)
                        else:
                            ch, color = '·', curses.color_pair(6)
                    else:
                        ch, color = ' ', curses.color_pair(6)

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

    def run(self):
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(80)

        self.add_message("⚓ SONAR SIMULATOR — Command your submarine!", 180)
        self.add_message("Use WASD to move, SPACE to ping, F to fire torpedoes", 180)
        self.add_message("Press E to toggle active/passive sonar mode", 180)

        while True:
            key = self.stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                break
            if key != -1:
                self.handle_input(key)

            self.update()
            self.render()

            if self.game_over and not self.victory:
                # Show game over screen
                h, w = self.max_y, self.max_x
                cy, cx = h // 2, w // 2
                try:
                    self.stdscr.addstr(cy - 2, cx - 12, "╔════════════════════╗", curses.color_pair(3) | curses.A_BOLD)
                    self.stdscr.addstr(cy - 1, cx - 12, "║   SUBMARINE LOST   ║", curses.color_pair(3) | curses.A_BOLD)
                    self.stdscr.addstr(cy, cx - 12,     f"║  Score: {self.sub.score:>9}  ║", curses.color_pair(4) | curses.A_BOLD)
                    self.stdscr.addstr(cy + 1, cx - 12, "║ Press R to restart ║", curses.color_pair(7))
                    self.stdscr.addstr(cy + 2, cx - 12, "╚════════════════════╝", curses.color_pair(3) | curses.A_BOLD)
                except curses.error:
                    pass
                self.stdscr.refresh()

                key = self.stdscr.getch()
                if key == ord('r') or key == ord('R'):
                    self.__init__(self.stdscr)
                elif key == ord('q') or key == ord('Q'):
                    break

            if self.victory:
                h, w = self.max_y, self.max_x
                cy, cx = h // 2, w // 2
                try:
                    self.stdscr.addstr(cy - 2, cx - 14, "╔════════════════════════╗", curses.color_pair(2) | curses.A_BOLD)
                    self.stdscr.addstr(cy - 1, cx - 14, "║    🏆 VICTORY! 🏆       ║", curses.color_pair(2) | curses.A_BOLD)
                    self.stdscr.addstr(cy, cx - 14,     f"║  Final Score: {self.sub.score:>8} ║", curses.color_pair(4) | curses.A_BOLD)
                    self.stdscr.addstr(cy + 1, cx - 14, "║ Press R to play again  ║", curses.color_pair(7))
                    self.stdscr.addstr(cy + 2, cx - 14, "╚════════════════════════╝", curses.color_pair(2) | curses.A_BOLD)
                except curses.error:
                    pass
                self.stdscr.refresh()

                key = self.stdscr.getch()
                if key == ord('r') or key == ord('R'):
                    self.__init__(self.stdscr)
                elif key == ord('q') or key == ord('Q'):
                    break


def main():
    try:
        stdscr = curses.initscr()
        game = SonarGame(stdscr)
        game.run()
    finally:
        curses.endwin()


if __name__ == "__main__":
    main()