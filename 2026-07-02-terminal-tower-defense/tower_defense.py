#!/usr/bin/env python3
"""
Terminal Tower Defense — A fully playable tower defense game in the terminal.

Controls:
  ←/→ or h/l : Move cursor
  ↑/↓ or k/j : Scroll tower selection
  1-5         : Place tower (1=Arrow, 2=Cannon, 3=Ice, 4=Sniper, 5=Mortar)
  u           : Upgrade tower under cursor
  s           : Sell tower under cursor (50% refund)
  SPACE       : Start next wave
  p           : Pause/unpause
  q/Esc       : Quit

Requirements: Python 3.7+ with curses (included on most Unix systems)
"""

import curses
import random
import math
import time
from collections import deque
from enum import IntEnum

# ─── Grid & Display Constants ───────────────────────────────────────────────
MAP_W = 50
MAP_H = 20
SIDEBAR_W = 30
LOG_H = 4
HEADER_H = 1

# ─── Path waypoints (col, row) ─────────────────────────────────────────────
WAYPOINTS = [
    (0, 5),
    (10, 5),
    (10, 2),
    (20, 2),
    (20, 10),
    (30, 10),
    (30, 4),
    (40, 4),
    (40, 15),
    (49, 15),
]


# ─── Enums ──────────────────────────────────────────────────────────────────
class Tile(IntEnum):
    EMPTY = 0
    PATH = 1
    TOWER = 2


class EnemyType(IntEnum):
    BASIC = 0
    FAST = 1
    TANK = 2
    HEALER = 3
    BOSS = 4


class TowerType(IntEnum):
    ARROW = 0
    CANNON = 1
    ICE = 2
    SNIPER = 3
    MORTAR = 4


# ─── Tower definitions ─────────────────────────────────────────────────────
TOWER_DATA = {
    TowerType.ARROW: {
        "name": "Arrow",
        "char": "A",
        "color": curses.COLOR_GREEN,
        "cost": 50,
        "damage": 8,
        "range": 4,
        "fire_rate": 6,   # frames between shots
        "splash": 0,
        "slow": 0,
        "upg_cost": 40,
        "upg_dmg": 6,
        "upg_range": 1,
    },
    TowerType.CANNON: {
        "name": "Cannon",
        "char": "C",
        "color": curses.COLOR_RED,
        "cost": 100,
        "damage": 25,
        "range": 3,
        "fire_rate": 12,
        "splash": 1,
        "slow": 0,
        "upg_cost": 80,
        "upg_dmg": 15,
        "upg_range": 0,
    },
    TowerType.ICE: {
        "name": "Ice",
        "char": "I",
        "color": curses.COLOR_CYAN,
        "cost": 75,
        "damage": 4,
        "range": 4,
        "fire_rate": 8,
        "splash": 0,
        "slow": 0.5,       # 50% slow
        "upg_cost": 60,
        "upg_dmg": 2,
        "upg_range": 1,
    },
    TowerType.SNIPER: {
        "name": "Sniper",
        "char": "S",
        "color": curses.COLOR_YELLOW,
        "cost": 120,
        "damage": 50,
        "range": 8,
        "fire_rate": 20,
        "splash": 0,
        "slow": 0,
        "upg_cost": 100,
        "upg_dmg": 30,
        "upg_range": 1,
    },
    TowerType.MORTAR: {
        "name": "Mortar",
        "char": "M",
        "color": curses.COLOR_MAGENTA,
        "cost": 150,
        "damage": 40,
        "range": 5,
        "fire_rate": 18,
        "splash": 2,
        "slow": 0,
        "upg_cost": 120,
        "upg_dmg": 20,
        "upg_range": 0,
    },
}

# ─── Enemy definitions ──────────────────────────────────────────────────────
ENEMY_DATA = {
    EnemyType.BASIC:  {"name": "Grunt",     "char": "g", "color": curses.COLOR_RED,    "hp": 30,  "speed": 0.08, "reward": 5,  "heal": 0},
    EnemyType.FAST:   {"name": "Scout",     "char": "s", "color": curses.COLOR_YELLOW,  "hp": 18,  "speed": 0.16, "reward": 8,  "heal": 0},
    EnemyType.TANK:   {"name": "Brute",     "char": "B", "color": curses.COLOR_MAGENTA, "hp": 100, "speed": 0.05, "reward": 15, "heal": 0},
    EnemyType.HEALER: {"name": "Medic",     "char": "H", "color": curses.COLOR_GREEN,   "hp": 25,  "speed": 0.07, "reward": 12, "heal": 2},
    EnemyType.BOSS:   {"name": "Overlord",  "char": "X", "color": curses.COLOR_WHITE,    "hp": 300, "speed": 0.04, "reward": 50, "heal": 0},
}


# ─── Build the path tiles ──────────────────────────────────────────────────
def build_path(waypoints):
    """Return a set of (col, row) tiles that form the path."""
    path_set = set()
    path_list = []
    for i in range(len(waypoints) - 1):
        c1, r1 = waypoints[i]
        c2, r2 = waypoints[i + 1]
        if c1 == c2:
            # vertical
            step = 1 if r2 > r1 else -1
            for r in range(r1, r2 + step, step):
                path_set.add((c1, r))
                path_list.append((c1, r))
        else:
            # horizontal
            step = 1 if c2 > c1 else -1
            for c in range(c1, c2 + step, step):
                path_set.add((c, r1))
                path_list.append((c, r1))
    # Remove duplicates while preserving order for enemy movement
    seen = set()
    ordered = []
    for p in path_list:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return path_set, ordered


# ─── Game objects ───────────────────────────────────────────────────────────
class Enemy:
    def __init__(self, etype, wave_num):
        data = ENEMY_DATA[etype]
        scale = 1 + wave_num * 0.15
        self.etype = etype
        self.name = data["name"]
        self.char = data["char"]
        self.color = data["color"]
        self.max_hp = int(data["hp"] * scale)
        self.hp = self.max_hp
        self.base_speed = data["speed"]
        self.speed = self.base_speed
        self.reward = data["reward"]
        self.heal = data["heal"]
        self.path_index = 0.0  # float position along ordered path
        self.alive = True
        self.reached_end = False
        self.slow_timer = 0

    def position(self, ordered_path):
        idx = int(self.path_index)
        frac = self.path_index - idx
        if idx >= len(ordered_path) - 1:
            return ordered_path[-1]
        c1, r1 = ordered_path[idx]
        c2, r2 = ordered_path[idx + 1]
        c = c1 + (c2 - c1) * frac
        r = r1 + (r2 - r1) * frac
        return (c, r)

    def grid_pos(self, ordered_path):
        c, r = self.position(ordered_path)
        return (int(round(c)), int(round(r)))

    def update(self, ordered_path):
        if self.slow_timer > 0:
            self.slow_timer -= 1
            self.speed = self.base_speed * 0.5
        else:
            self.speed = self.base_speed
        self.path_index += self.speed
        # Healer heals nearby enemies (handled externally)
        if self.path_index >= len(ordered_path) - 1:
            self.reached_end = True
            self.alive = False

    def take_damage(self, dmg):
        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def apply_slow(self, duration=15):
        self.slow_timer = max(self.slow_timer, duration)


class Projectile:
    def __init__(self, start, target, damage, splash=0, slow=0, color=curses.COLOR_WHITE):
        self.col, self.row = start
        self.target = target
        self.damage = damage
        self.splash = splash
        self.slow = slow
        self.color = color
        self.speed = 0.5
        self.alive = True

    def update(self):
        tc, tr = self.target
        dx = tc - self.col
        dy = tr - self.row
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < self.speed:
            self.col, self.row = tc, tr
            self.alive = False
            return True  # hit
        self.col += dx / dist * self.speed
        self.row += dy / dist * self.speed
        return False


class Tower:
    def __init__(self, ttype, col, row):
        self.ttype = ttype
        data = TOWER_DATA[ttype]
        self.name = data["name"]
        self.char = data["char"]
        self.color = data["color"]
        self.col = col
        self.row = row
        self.level = 1
        self.damage = data["damage"]
        self.range = data["range"]
        self.fire_rate = data["fire_rate"]
        self.splash = data["splash"]
        self.slow = data["slow"]
        self.cooldown = 0
        self.total_cost = data["cost"]

    def upgrade_cost(self):
        if self.level >= 5:
            return None
        data = TOWER_DATA[self.ttype]
        return data["upg_cost"] * self.level

    def upgrade(self):
        if self.level >= 5:
            return
        data = TOWER_DATA[self.ttype]
        cost = self.upgrade_cost()
        self.level += 1
        self.damage += data["upg_dmg"]
        self.range += data["upg_range"]
        self.total_cost += cost

    def sell_value(self):
        return int(self.total_cost * 0.5)

    def find_target(self, enemies, ordered_path):
        """Find the furthest-along enemy in range."""
        best = None
        best_progress = -1
        for e in enemies:
            if not e.alive:
                continue
            ec, er = e.grid_pos(ordered_path)
            dist = abs(ec - self.col) + abs(er - self.row)
            if dist <= self.range:
                if e.path_index > best_progress:
                    best_progress = e.path_index
                    best = e
        return best

    def try_fire(self, enemies, ordered_path):
        if self.cooldown > 0:
            self.cooldown -= 1
            return None
        target = self.find_target(enemies, ordered_path)
        if target is None:
            return None
        self.cooldown = self.fire_rate
        tc, tr = target.position(ordered_path)
        return Projectile(
            (self.col, self.row), (tc, tr),
            self.damage, self.splash, self.slow, self.color
        )


# ─── Wave definitions ───────────────────────────────────────────────────────
def generate_wave(wave_num):
    """Generate a list of (EnemyType, spawn_delay) for a wave."""
    enemies = []
    count = 5 + wave_num * 2
    if wave_num % 5 == 0 and wave_num > 0:
        # Boss wave
        for i in range(count - 1):
            etype = random.choice([EnemyType.BASIC, EnemyType.FAST])
            enemies.append((etype, 12))
        enemies.append((EnemyType.BOSS, 20))
    else:
        pool = [EnemyType.BASIC]
        if wave_num >= 2:
            pool.append(EnemyType.FAST)
        if wave_num >= 4:
            pool.append(EnemyType.TANK)
        if wave_num >= 6:
            pool.append(EnemyType.HEALER)
        for i in range(count):
            etype = random.choice(pool)
            delay = 10 if etype != EnemyType.BOSS else 20
            enemies.append((etype, delay))
    return enemies


# ─── Main Game ──────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.gold = 200
        self.lives = 20
        self.score = 0
        self.wave_num = 0
        self.wave_active = False
        self.wave_enemies = []    # remaining (type, delay) to spawn
        self.spawn_timer = 0
        self.enemies = []
        self.towers = []
        self.projectiles = []
        self.tower_grid = {}      # (col, row) -> Tower
        self.path_set, self.ordered_path = build_path(WAYPOINTS)
        self.grid = [[Tile.EMPTY for _ in range(MAP_W)] for _ in range(MAP_H)]
        for c, r in self.path_set:
            self.grid[r][c] = Tile.PATH
        self.cursor_col = 10
        self.cursor_row = 10
        self.selected_tower = 0
        self.log = deque(maxlen=50)
        self.log.append("Welcome to Terminal Tower Defense!")
        self.log.append("Place towers to defend against waves of enemies.")
        self.log.append("Press SPACE to start wave 1. Press q to quit.")
        self.paused = False
        self.game_over = False
        self.frame = 0

    def add_log(self, msg):
        self.log.append(msg)

    def place_tower(self, ttype):
        c, r = self.cursor_col, self.cursor_row
        if r < 0 or r >= MAP_H or c < 0 or c >= MAP_W:
            return
        if self.grid[r][c] != Tile.EMPTY:
            self.add_log("Can't place there!")
            return
        data = TOWER_DATA[ttype]
        if self.gold < data["cost"]:
            self.add_log(f"Not enough gold! Need {data['cost']}, have {self.gold}")
            return
        tower = Tower(ttype, c, r)
        self.towers.append(tower)
        self.tower_grid[(c, r)] = tower
        self.grid[r][c] = Tile.TOWER
        self.gold -= data["cost"]
        self.add_log(f"Placed {data['name']} tower at ({c},{r}) for {data['cost']}g")

    def upgrade_tower(self):
        c, r = self.cursor_col, self.cursor_row
        tower = self.tower_grid.get((c, r))
        if tower is None:
            self.add_log("No tower at cursor.")
            return
        cost = tower.upgrade_cost()
        if cost is None:
            self.add_log("Tower already max level!")
            return
        if self.gold < cost:
            self.add_log(f"Not enough gold! Need {cost}, have {self.gold}")
            return
        self.gold -= cost
        tower.upgrade()
        self.add_log(f"Upgraded {tower.name} to Lv{tower.level} for {cost}g")

    def sell_tower(self):
        c, r = self.cursor_col, self.cursor_row
        tower = self.tower_grid.get((c, r))
        if tower is None:
            self.add_log("No tower at cursor.")
            return
        value = tower.sell_value()
        self.gold += value
        self.towers.remove(tower)
        del self.tower_grid[(c, r)]
        self.grid[r][c] = Tile.EMPTY
        self.add_log(f"Sold {tower.name} tower for {value}g")

    def start_wave(self):
        if self.wave_active:
            self.add_log("Wave already in progress!")
            return
        self.wave_num += 1
        self.wave_active = True
        self.wave_enemies = generate_wave(self.wave_num)
        self.spawn_timer = 0
        self.add_log(f"=== Wave {self.wave_num} starts! ===")

    def update(self):
        if self.paused or self.game_over:
            return
        self.frame += 1

        # Spawn enemies
        if self.wave_enemies:
            self.spawn_timer -= 1
            if self.spawn_timer <= 0:
                etype, delay = self.wave_enemies.pop(0)
                self.enemies.append(Enemy(etype, self.wave_num))
                self.spawn_timer = delay

        # Update enemies
        for e in self.enemies:
            if e.alive:
                e.update(self.ordered_path)
                if e.reached_end:
                    self.lives -= 1
                    self.add_log(f"{e.name} reached the end! ({self.lives} lives left)")
                    if self.lives <= 0:
                        self.game_over = True
                        self.add_log("GAME OVER! All lives lost.")

        # Healer enemies heal nearby
        for e in self.enemies:
            if e.alive and e.etype == EnemyType.HEALER and e.heal > 0:
                ec, er = e.grid_pos(self.ordered_path)
                for other in self.enemies:
                    if other.alive and other is not e:
                        oc, orow = other.grid_pos(self.ordered_path)
                        if abs(oc - ec) + abs(orow - er) <= 2:
                            other.hp = min(other.max_hp, other.hp + e.heal)

        # Remove dead/reached enemies
        for e in list(self.enemies):
            if not e.alive:
                if not e.reached_end:
                    self.gold += e.reward
                    self.score += e.reward * 2
                self.enemies.remove(e)

        # Check wave complete
        if self.wave_active and not self.wave_enemies and not self.enemies:
            self.wave_active = False
            bonus = 25 + self.wave_num * 10
            self.gold += bonus
            self.add_log(f"Wave {self.wave_num} cleared! Bonus: {bonus}g")

        # Towers fire
        for tower in self.towers:
            proj = tower.try_fire(self.enemies, self.ordered_path)
            if proj:
                self.projectiles.append(proj)

        # Update projectiles
        for p in list(self.projectiles):
            hit = p.update()
            if hit:
                # Damage target(s)
                if p.splash > 0:
                    for e in self.enemies:
                        if e.alive:
                            ec, er = e.position(self.ordered_path)
                            dist = math.sqrt((ec - p.col) ** 2 + (er - p.row) ** 2)
                            if dist <= p.splash:
                                e.take_damage(p.damage)
                else:
                    # Hit nearest alive enemy to impact point
                    best = None
                    best_dist = float('inf')
                    for e in self.enemies:
                        if e.alive:
                            ec, er = e.position(self.ordered_path)
                            dist = math.sqrt((ec - p.col) ** 2 + (er - p.row) ** 2)
                            if dist < best_dist:
                                best_dist = dist
                                best = e
                    if best and best_dist < 1.5:
                        best.take_damage(p.damage)
                        if p.slow > 0:
                            best.apply_slow()
            if not p.alive:
                self.projectiles.remove(p)


# ─── Renderer ───────────────────────────────────────────────────────────────
class Renderer:
    def __init__(self, stdscr, game):
        self.stdscr = stdscr
        self.game = game
        self.colors_initialized = False

    def init_colors(self):
        if self.colors_initialized:
            return
        curses.start_color()
        curses.use_default_colors()
        # Pair 1-7: standard colors
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_BLUE, -1)
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)
        curses.init_pair(6, curses.COLOR_CYAN, -1)
        curses.init_pair(7, curses.COLOR_WHITE, -1)
        # Pair 8: path color (brown/dark yellow)
        curses.init_pair(8, 136, -1)  # dark yellow/brown
        # Pair 9: cursor highlight
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_WHITE)
        # Pair 10-14: tower colors
        curses.init_pair(10, curses.COLOR_GREEN, -1)    # Arrow
        curses.init_pair(11, curses.COLOR_RED, -1)      # Cannon
        curses.init_pair(12, curses.COLOR_CYAN, -1)     # Ice
        curses.init_pair(13, curses.COLOR_YELLOW, -1)    # Sniper
        curses.init_pair(14, curses.COLOR_MAGENTA, -1)   # Mortar
        # Pair 15-19: enemy colors
        curses.init_pair(15, curses.COLOR_RED, -1)      # Basic
        curses.init_pair(16, curses.COLOR_YELLOW, -1)   # Fast
        curses.init_pair(17, curses.COLOR_MAGENTA, -1)   # Tank
        curses.init_pair(18, curses.COLOR_GREEN, -1)    # Healer
        curses.init_pair(19, curses.COLOR_WHITE, -1)    # Boss
        # Pair 20: HP bar color
        curses.init_pair(20, curses.COLOR_GREEN, curses.COLOR_RED)
        # Pair 21: dim text
        curses.init_pair(21, 240, -1)
        # Pair 22: gold color
        curses.init_pair(22, 220, -1)
        self.colors_initialized = True

    def color_pair_for_enemy(self, e):
        mapping = {
            EnemyType.BASIC: 15,
            EnemyType.FAST: 16,
            EnemyType.TANK: 17,
            EnemyType.HEALER: 18,
            EnemyType.BOSS: 19,
        }
        return mapping.get(e.etype, 1)

    def color_pair_for_tower(self, t):
        mapping = {
            TowerType.ARROW: 10,
            TowerType.CANNON: 11,
            TowerType.ICE: 12,
            TowerType.SNIPER: 13,
            TowerType.MORTAR: 14,
        }
        return mapping.get(t.ttype, 1)

    def draw(self):
        g = self.game
        stdscr = self.stdscr
        stdscr.clear()

        # ── Header ──
        header = f" ⚔ TOWER DEFENSE ⚔  Wave: {g.wave_num}  Gold: {g.gold}  Lives: {g.lives}  Score: {g.score}  "
        if g.paused:
            header += " [PAUSED]"
        if g.game_over:
            header += " [GAME OVER]"
        stdscr.addstr(0, 0, header, curses.A_BOLD)

        # ── Map ──
        # Build a display grid
        display = [[('·', 21) for _ in range(MAP_W)] for _ in range(MAP_H)]

        # Path tiles
        for r in range(MAP_H):
            for c in range(MAP_W):
                if g.grid[r][c] == Tile.PATH:
                    display[r][c] = ('█', 8)

        # Towers
        for t in g.towers:
            display[t.row][t.col] = (t.char, self.color_pair_for_tower(t))

        # Projectiles
        for p in g.projectiles:
            pc, pr = int(round(p.col)), int(round(p.row))
            if 0 <= pr < MAP_H and 0 <= pc < MAP_W:
                display[pr][pc] = ('•', 7)

        # Cursor range indicator
        ct = g.tower_grid.get((g.cursor_col, g.cursor_row))
        selected_type = TowerType(g.selected_tower)
        sel_data = TOWER_DATA[selected_type]
        range_val = ct.range if ct else sel_data["range"]
        for dr in range(-range_val, range_val + 1):
            for dc in range(-range_val, range_val + 1):
                rr, cc = g.cursor_row + dr, g.cursor_col + dc
                if 0 <= rr < MAP_H and 0 <= cc < MAP_W:
                    if abs(dr) + abs(dc) <= range_val:
                        if display[rr][cc][0] == '·':
                            display[rr][cc] = ('░', 21)

        # Enemies (draw on top)
        for e in g.enemies:
            if e.alive:
                ec, er = e.grid_pos(g.ordered_path)
                if 0 <= er < MAP_H and 0 <= ec < MAP_W:
                    display[er][ec] = (e.char, self.color_pair_for_enemy(e))

        # Draw the grid
        offset_y = 1
        for r in range(MAP_H):
            for c in range(MAP_W):
                ch, cpair = display[r][c]
                # Highlight cursor
                if c == g.cursor_col and r == g.cursor_row:
                    stdscr.addstr(offset_y + r, c, ch, curses.color_pair(cpair) | curses.A_REVERSE)
                else:
                    try:
                        stdscr.addstr(offset_y + r, c, ch, curses.color_pair(cpair))
                    except curses.error:
                        pass

        # ── HP bars under enemies (on a separate line below map) ──
        # We'll draw enemy info in sidebar instead

        # ── Sidebar ──
        sx = MAP_W + 2
        sy = 1

        # Selected tower info
        tower_types = list(TowerType)
        stdscr.addstr(sy, sx, "── TOWERS ──", curses.A_BOLD)
        for i, tt in enumerate(TowerType):
            data = TOWER_DATA[tt]
            marker = "►" if i == g.selected_tower else " "
            line = f"{marker}{i+1} {data['char']} {data['name']:7s} {data['cost']:3d}g"
            cpair = self.color_pair_for_tower_type(tt)
            if i == g.selected_tower:
                stdscr.addstr(sy + 1 + i, sx, line, curses.color_pair(cpair) | curses.A_BOLD)
            else:
                stdscr.addstr(sy + 1 + i, sx, line, curses.color_pair(cpair))

        # Tower details
        dy = sy + 7
        ct = g.tower_grid.get((g.cursor_col, g.cursor_row))
        if ct:
            stdscr.addstr(dy, sx, "── TOWER INFO ──", curses.A_BOLD)
            stdscr.addstr(dy+1, sx, f"{ct.name} Lv{ct.level}")
            stdscr.addstr(dy+2, sx, f"DMG: {ct.damage}  RNG: {ct.range}")
            uc = ct.upgrade_cost()
            if uc:
                stdscr.addstr(dy+3, sx, f"Upgrade: {uc}g [u]")
            else:
                stdscr.addstr(dy+3, sx, "MAX LEVEL")
            stdscr.addstr(dy+4, sx, f"Sell: {ct.sell_value()}g [s]")
        else:
            sel_data = TOWER_DATA[selected_type]
            stdscr.addstr(dy, sx, f"── {sel_data['name'].upper()} TOWER ──", curses.A_BOLD)
            stdscr.addstr(dy+1, sx, f"Cost: {sel_data['cost']}g")
            stdscr.addstr(dy+2, sx, f"DMG: {sel_data['damage']}  RNG: {sel_data['range']}")
            stdscr.addstr(dy+3, sx, f"Rate: {sel_data['fire_rate']}")
            if sel_data['splash'] > 0:
                stdscr.addstr(dy+4, sx, f"Splash: {sel_data['splash']}")
            if sel_data['slow'] > 0:
                stdscr.addstr(dy+4, sx, f"Slow: {int(sel_data['slow']*100)}%")

        # Controls
        cy = dy + 6
        stdscr.addstr(cy, sx, "── CONTROLS ──", curses.A_BOLD)
        controls = [
            "←→↑↓  Move cursor",
            "1-5    Place tower",
            "u      Upgrade",
            "s      Sell tower",
            "SPACE  Start wave",
            "p      Pause",
            "q/Esc  Quit",
        ]
        for i, line in enumerate(controls):
            stdscr.addstr(cy + 1 + i, sx, line)

        # ── Log ──
        log_y = MAP_H + 2
        stdscr.addstr(log_y, 0, "─" * (MAP_W + SIDEBAR_W + 2))
        logs = list(g.log)[-LOG_H:]
        for i, msg in enumerate(logs):
            if i < LOG_H:
                stdscr.addstr(log_y + 1 + i, 0, msg[:MAP_W + SIDEBAR_W + 2])

        # ── Enemy HP indicators on map ──
        # Draw small HP bars above enemies where possible
        for e in g.enemies:
            if e.alive:
                ec, er = e.grid_pos(g.ordered_path)
                # Draw HP fraction as a small bar at the bottom of the log area
                pass  # We'll show in sidebar instead

        # ── Enemy list in sidebar ──
        ey = cy + 1 + len(controls) + 1
        if g.enemies:
            stdscr.addstr(ey, sx, f"── ENEMIES ({len(g.enemies)}) ──", curses.A_BOLD)
            for i, e in enumerate(g.enemies[:4]):
                hp_pct = e.hp / e.max_hp
                bar_len = 10
                filled = int(hp_pct * bar_len)
                bar = '█' * filled + '░' * (bar_len - filled)
                line = f"{e.char} {bar} {e.hp}/{e.max_hp}"
                cpair = self.color_pair_for_enemy(e)
                stdscr.addstr(ey + 1 + i, sx, line, curses.color_pair(cpair))
            if len(g.enemies) > 4:
                stdscr.addstr(ey + 5, sx, f"  ...+{len(g.enemies)-4} more")

        stdscr.refresh()

    def color_pair_for_tower_type(self, tt):
        mapping = {
            TowerType.ARROW: 10,
            TowerType.CANNON: 11,
            TowerType.ICE: 12,
            TowerType.SNIPER: 13,
            TowerType.MORTAR: 14,
        }
        return mapping.get(tt, 1)


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)  # 50ms refresh = 20fps

    game = Game()
    renderer = Renderer(stdscr, game)
    renderer.init_colors()

    while True:
        # Input
        key = stdscr.getch()
        if key != -1:
            if key in (ord('q'), 27):  # q or Esc
                break
            elif key == ord('p'):
                game.paused = not game.paused
            elif key == ord(' '):
                game.start_wave()
            elif key in (curses.KEY_LEFT, ord('h')):
                game.cursor_col = max(0, game.cursor_col - 1)
            elif key in (curses.KEY_RIGHT, ord('l')):
                game.cursor_col = min(MAP_W - 1, game.cursor_col + 1)
            elif key in (curses.KEY_UP, ord('k')):
                game.cursor_row = max(0, game.cursor_row - 1)
            elif key in (curses.KEY_DOWN, ord('j')):
                game.cursor_row = min(MAP_H - 1, game.cursor_row + 1)
            elif key == ord('1'):
                game.place_tower(TowerType.ARROW)
            elif key == ord('2'):
                game.place_tower(TowerType.CANNON)
            elif key == ord('3'):
                game.place_tower(TowerType.ICE)
            elif key == ord('4'):
                game.place_tower(TowerType.SNIPER)
            elif key == ord('5'):
                game.place_tower(TowerType.MORTAR)
            elif key == ord('u'):
                game.upgrade_tower()
            elif key == ord('s'):
                game.sell_tower()
            elif key == ord('\t'):
                game.selected_tower = (game.selected_tower + 1) % 5

        # Update
        game.update()

        # Draw
        renderer.draw()

    # End screen
    stdscr.clear()
    end_msg = f"Game Over! Final Score: {game.score} | Waves Survived: {game.wave_num}"
    stdscr.addstr(curses.LINES // 2, max(0, (curses.COLS - len(end_msg)) // 2), end_msg, curses.A_BOLD)
    stdscr.addstr(curses.LINES // 2 + 1, max(0, (curses.COLS - 20) // 2), "Press any key to exit")
    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main)