#!/usr/bin/env python3
"""
Terminal Tower Defense — A fully playable tower defense game in the terminal.

Place and upgrade towers to defend against waves of increasingly tough enemies
in this ASCII-art game powered by the curses library.

Controls:
  ←/→/↑/↓ or h/j/k/l : Move cursor
  1-7                  : Place tower (1=Arrow, 2=Cannon, 3=Ice, 4=Sniper, 5=Mortar, 6=Lightning, 7=Poison)
  Tab                  : Cycle tower selection
  u                    : Upgrade tower under cursor
  s                    : Sell tower under cursor (50% refund)
  SPACE                : Start next wave
  a                    : Toggle auto-wave mode
  f                    : Toggle fast-forward (2x speed)
  b                    : Use Bomb power-up (damages all enemies on screen)
  e                    : Use Freeze power-up (freezes all enemies for 3 seconds)
  d                    : Use Gold Rush power-up (2x gold for 5 seconds)
  p                    : Pause/unpause
  r                    : Restart (after game over)
  q / Esc              : Quit

Usage:
  python3 tower_defense.py [--help] [--version] [--difficulty easy|normal|hard]

Requirements: Python 3.7+ with curses (included on most Unix systems).
"""

import argparse
import curses
import json
import math
import os
import random
import sys
import time
from collections import deque
from enum import IntEnum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ─── Version ────────────────────────────────────────────────────────────────
VERSION = "2.3.0"

# ─── Grid & Display Constants ───────────────────────────────────────────────
MAP_W = 50
MAP_H = 20
SIDEBAR_W = 30
LOG_H = 4
HEADER_H = 1
MIN_TERM_W = MAP_W + SIDEBAR_W + 4
MIN_TERM_H = MAP_H + LOG_H + HEADER_H + 4

# ─── Interest and Power-up Constants ─────────────────────────────────────────
INTEREST_RATE = 0.05          # 5% gold interest between waves
INTEREST_MAX_GOLD = 500       # Cap interest at 500 gold earned
BOMB_DAMAGE = 80              # Bomb power-up: damage to all enemies
FREEZE_DURATION = 60          # Freeze power-up: frames enemies are frozen (3s at 20fps)
GOLD_RUSH_DURATION = 100      # Gold Rush power-up: frames of 2x gold (5s at 20fps)
POWER_UP_PER_WAVE = 1         # Number of power-up charges earned per wave cleared

# ─── High score file ────────────────────────────────────────────────────────
HIGHSCORE_FILE = Path(__file__).parent / "highscores.json"

# ─── Path waypoints (col, row) ──────────────────────────────────────────────
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

# ─── Difficulty settings ────────────────────────────────────────────────────
DIFFICULTY_SETTINGS = {
    "easy": {"gold": 300, "lives": 30, "hp_scale": 0.8, "reward_scale": 1.2},
    "normal": {"gold": 200, "lives": 20, "hp_scale": 1.0, "reward_scale": 1.0},
    "hard": {"gold": 150, "lives": 10, "hp_scale": 1.3, "reward_scale": 0.8},
}


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
    SWARM = 5
    STEALTH = 6


class TowerType(IntEnum):
    ARROW = 0
    CANNON = 1
    ICE = 2
    SNIPER = 3
    MORTAR = 4
    LIGHTNING = 5
    POISON = 6


# ─── Tower definitions ─────────────────────────────────────────────────────
TOWER_DATA: Dict[TowerType, dict] = {
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
        "chain": 0,
        "poison": 0,
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
        "chain": 0,
        "poison": 0,
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
        "chain": 0,
        "poison": 0,
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
        "chain": 0,
        "poison": 0,
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
        "chain": 0,
        "poison": 0,
        "upg_cost": 120,
        "upg_dmg": 20,
        "upg_range": 0,
    },
    TowerType.LIGHTNING: {
        "name": "Lightning",
        "char": "L",
        "color": curses.COLOR_BLUE,
        "cost": 130,
        "damage": 15,
        "range": 5,
        "fire_rate": 14,
        "splash": 0,
        "slow": 0,
        "chain": 3,       # chains to up to 3 nearby enemies
        "poison": 0,
        "upg_cost": 90,
        "upg_dmg": 8,
        "upg_range": 0,
    },
    TowerType.POISON: {
        "name": "Poison",
        "char": "P",
        "color": curses.COLOR_GREEN,
        "cost": 90,
        "damage": 3,
        "range": 4,
        "fire_rate": 10,
        "splash": 0,
        "slow": 0,
        "chain": 0,
        "poison": 3,      # 3 poison damage per tick for 5 ticks
        "upg_cost": 70,
        "upg_dmg": 1,
        "upg_range": 1,
    },
}

# ─── Enemy definitions ──────────────────────────────────────────────────────
ENEMY_DATA: Dict[EnemyType, dict] = {
    EnemyType.BASIC:   {"name": "Grunt",     "char": "g", "color": curses.COLOR_RED,     "hp": 30,  "speed": 0.08, "reward": 5,  "heal": 0, "stealth": False, "dodge": 0.0},
    EnemyType.FAST:    {"name": "Scout",     "char": "s", "color": curses.COLOR_YELLOW,  "hp": 18,  "speed": 0.16, "reward": 8,  "heal": 0, "stealth": False, "dodge": 0.0},
    EnemyType.TANK:    {"name": "Brute",     "char": "B", "color": curses.COLOR_MAGENTA, "hp": 100, "speed": 0.05, "reward": 15, "heal": 0, "stealth": False, "dodge": 0.0},
    EnemyType.HEALER:  {"name": "Medic",     "char": "H", "color": curses.COLOR_GREEN,   "hp": 25,  "speed": 0.07, "reward": 12, "heal": 2, "stealth": False, "dodge": 0.0},
    EnemyType.BOSS:    {"name": "Overlord",  "char": "X", "color": curses.COLOR_WHITE,   "hp": 300, "speed": 0.04, "reward": 50, "heal": 0, "stealth": False, "dodge": 0.0},
    EnemyType.SWARM:   {"name": "Swarm",     "char": "w", "color": curses.COLOR_CYAN,    "hp": 12,  "speed": 0.12, "reward": 3,  "heal": 0, "stealth": False, "dodge": 0.0},
    EnemyType.STEALTH: {"name": "Phantom",   "char": "?", "color": curses.COLOR_BLUE,    "hp": 22,  "speed": 0.10, "reward": 10, "heal": 0, "stealth": True,  "dodge": 0.30},
}


# ─── High score management ──────────────────────────────────────────────────
def load_highscores() -> List[dict]:
    """Load high scores from the JSON file. Returns empty list if file missing."""
    if HIGHSCORE_FILE.exists():
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_highscore(score: int, wave: int, difficulty: str, stats: Optional[dict] = None) -> None:
    """Append a new high score entry and save, keeping top 10."""
    scores = load_highscores()
    entry = {
        "score": score,
        "wave": wave,
        "difficulty": difficulty,
        "date": time.strftime("%Y-%m-%d %H:%M"),
    }
    if stats:
        entry["stats"] = stats
    scores.append(entry)
    # Sort by score descending, keep top 10
    scores.sort(key=lambda x: x["score"], reverse=True)
    scores = scores[:10]
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            json.dump(scores, f, indent=2)
    except OSError:
        pass  # Silently ignore write failures


# ─── Build the path tiles ──────────────────────────────────────────────────
def build_path(waypoints: List[Tuple[int, int]]) -> Tuple[Set[Tuple[int, int]], List[Tuple[int, int]]]:
    """Return a set of (col, row) tiles forming the path, and an ordered list for movement."""
    path_set: Set[Tuple[int, int]] = set()
    path_list: List[Tuple[int, int]] = []
    for i in range(len(waypoints) - 1):
        c1, r1 = waypoints[i]
        c2, r2 = waypoints[i + 1]
        if c1 == c2:
            # vertical segment
            step = 1 if r2 > r1 else -1
            for r in range(r1, r2 + step, step):
                path_set.add((c1, r))
                path_list.append((c1, r))
        else:
            # horizontal segment
            step = 1 if c2 > c1 else -1
            for c in range(c1, c2 + step, step):
                path_set.add((c, r1))
                path_list.append((c, r1))
    # Remove duplicates while preserving order for enemy movement
    seen: Set[Tuple[int, int]] = set()
    ordered: List[Tuple[int, int]] = []
    for p in path_list:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return path_set, ordered


# ─── Game objects ───────────────────────────────────────────────────────────
class Enemy:
    """An enemy unit that follows the path toward the exit."""

    def __init__(self, etype: EnemyType, wave_num: int, difficulty: str = "normal"):
        data = ENEMY_DATA[etype]
        diff = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS["normal"])
        hp_scale = (1 + wave_num * 0.15) * diff["hp_scale"]
        reward = int(data["reward"] * diff["reward_scale"])

        self.etype = etype
        self.name = data["name"]
        self.char = data["char"]
        self.color = data["color"]
        self.max_hp = int(data["hp"] * hp_scale)
        self.hp = self.max_hp
        self.base_speed = data["speed"]
        self.speed = self.base_speed
        self.reward = reward
        self.heal = data["heal"]
        self.stealth = data.get("stealth", False)
        self.dodge = data.get("dodge", 0.0)
        self.path_index = 0.0  # float position along ordered path
        self.alive = True
        self.reached_end = False
        self.slow_timer = 0
        self.hit_flash = 0  # frames to show hit indicator
        self.killed_by: Optional[Tower] = None  # which tower killed this enemy
        self.poison_timer = 0   # frames of poison remaining
        self.poison_dmg = 0     # poison damage per tick
        self.visible = True      # for stealth enemies: visibility state
        self.phase_timer = 0     # stealth phase timer

    def __repr__(self) -> str:
        return f"Enemy({self.name}, hp={self.hp}/{self.max_hp}, pos_idx={self.path_index:.1f})"

    def position(self, ordered_path: List[Tuple[int, int]]) -> Tuple[float, float]:
        """Interpolated (col, row) position along the path."""
        idx = int(self.path_index)
        frac = self.path_index - idx
        if idx >= len(ordered_path) - 1:
            return ordered_path[-1]
        c1, r1 = ordered_path[idx]
        c2, r2 = ordered_path[idx + 1]
        c = c1 + (c2 - c1) * frac
        r = r1 + (r2 - r1) * frac
        return (c, r)

    def grid_pos(self, ordered_path: List[Tuple[int, int]]) -> Tuple[int, int]:
        """Nearest integer grid position."""
        c, r = self.position(ordered_path)
        return (int(round(c)), int(round(r)))

    def update(self, ordered_path: List[Tuple[int, int]], frozen: bool = False) -> None:
        """Advance enemy along the path. If frozen, do not move."""
        if frozen:
            # Frozen enemies don't move and timers are paused (except hit flash)
            if self.hit_flash > 0:
                self.hit_flash -= 1
            return

        if self.slow_timer > 0:
            self.slow_timer -= 1
            self.speed = self.base_speed * 0.5
        else:
            self.speed = self.base_speed
        if self.hit_flash > 0:
            self.hit_flash -= 1

        # Poison damage
        if self.poison_timer > 0:
            self.poison_timer -= 1
            self.hp -= self.poison_dmg
            if self.hp <= 0:
                self.hp = 0
                self.alive = False
                # Dead enemy stops moving — no further path advancement
                return

        # Stealth phasing: cycle between visible and invisible
        if self.stealth:
            self.phase_timer += 1
            # Visible for 40 frames, invisible for 25 frames
            cycle = self.phase_timer % 65
            self.visible = cycle < 40

        self.path_index += self.speed
        if self.path_index >= len(ordered_path) - 1:
            self.reached_end = True
            self.alive = False

    def take_damage(self, dmg: int, source: Optional["Tower"] = None) -> bool:
        """Apply damage. Returns True if damage was actually dealt (not dodged).
        Marks enemy as dead if HP reaches zero."""
        # Dodge check for stealth enemies
        if self.dodge > 0 and random.random() < self.dodge:
            return False  # attack was dodged

        self.hp -= dmg
        self.hit_flash = 3
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            if source is not None and self.killed_by is None:
                self.killed_by = source
        return True

    def apply_slow(self, duration: int = 15) -> None:
        """Slow the enemy for a number of frames. Only extends, never shortens."""
        self.slow_timer = max(self.slow_timer, duration)

    def apply_poison(self, dmg_per_tick: int, duration: int = 5) -> None:
        """Apply poison damage over time. Reapplying refreshes the duration and damage."""
        self.poison_timer = max(self.poison_timer, duration)
        self.poison_dmg = max(self.poison_dmg, dmg_per_tick)


class Projectile:
    """A visual projectile traveling from tower to target position."""

    def __init__(self, start: Tuple[int, int], target: Tuple[float, float],
                 damage: int, splash: int = 0, slow: float = 0,
                 chain: int = 0, poison: int = 0, color: int = curses.COLOR_WHITE,
                 source_tower: Optional["Tower"] = None):
        self.col, self.row = start
        self.target = target
        self.damage = damage
        self.splash = splash
        self.slow = slow
        self.chain = chain
        self.poison = poison
        self.color = color
        self.source_tower = source_tower  # Track which tower fired this projectile
        self.speed = 0.5
        self.alive = True

    def update(self) -> bool:
        """Move toward target. Returns True if the projectile hit."""
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
    """A defensive tower placed on the grid."""

    def __init__(self, ttype: TowerType, col: int, row: int):
        self.ttype = ttype
        data = TOWER_DATA[ttype]
        self.name: str = data["name"]
        self.char: str = data["char"]
        self.color: int = data["color"]
        self.col = col
        self.row = row
        self.level = 1
        self.damage: int = data["damage"]
        self.range: int = data["range"]
        self.fire_rate: int = data["fire_rate"]
        self.splash: int = data["splash"]
        self.slow: float = data["slow"]
        self.chain: int = data["chain"]
        self.poison: int = data.get("poison", 0)
        self.cooldown = 0
        self.total_cost: int = data["cost"]
        self.kills = 0  # track kills per tower

    def __repr__(self) -> str:
        return f"Tower({self.name} Lv{self.level} at ({self.col},{self.row}), kills={self.kills})"

    def upgrade_cost(self) -> Optional[int]:
        """Return cost to upgrade, or None if max level."""
        if self.level >= 5:
            return None
        data = TOWER_DATA[self.ttype]
        return data["upg_cost"] * self.level

    def upgrade(self) -> None:
        """Upgrade this tower one level."""
        if self.level >= 5:
            return
        data = TOWER_DATA[self.ttype]
        cost = self.upgrade_cost()
        assert cost is not None  # guaranteed by the level check above
        self.level += 1
        self.damage += data["upg_dmg"]
        self.range += data["upg_range"]
        self.total_cost += cost
        # Chain count increases with level for Lightning
        if self.ttype == TowerType.LIGHTNING:
            self.chain = TOWER_DATA[TowerType.LIGHTNING]["chain"] + (self.level - 1)
        # Poison damage increases with level for Poison
        if self.ttype == TowerType.POISON:
            self.poison = TOWER_DATA[TowerType.POISON]["poison"] + (self.level - 1)

    def sell_value(self) -> int:
        """50% refund of total invested gold."""
        return int(self.total_cost * 0.5)

    def find_target(self, enemies: List[Enemy], ordered_path: List[Tuple[int, int]]) -> Optional[Enemy]:
        """Find the furthest-along enemy in range (prioritizes enemies closest to exit)."""
        best: Optional[Enemy] = None
        best_progress = -1.0
        for e in enemies:
            if not e.alive:
                continue
            # Stealth enemies that are invisible can't be targeted directly
            # (but can be hit by splash/chain)
            if e.stealth and not e.visible:
                continue
            ec, er = e.grid_pos(ordered_path)
            dist = abs(ec - self.col) + abs(er - self.row)
            if dist <= self.range:
                if e.path_index > best_progress:
                    best_progress = e.path_index
                    best = e
        return best

    def try_fire(self, enemies: List[Enemy], ordered_path: List[Tuple[int, int]]) -> Optional[Projectile]:
        """Fire a projectile if the cooldown has expired and a target exists."""
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
            self.damage, self.splash, self.slow, self.chain, self.poison, self.color,
            source_tower=self
        )


# ─── Wave definitions ───────────────────────────────────────────────────────
def generate_wave(wave_num: int) -> List[Tuple[EnemyType, int]]:
    """Generate a list of (EnemyType, spawn_delay) for a wave.

    Waves get progressively harder:
      - More enemies per wave
      - Tougher enemy types unlock over time
      - Every 5th wave is a boss wave
      - Swarm enemies appear from wave 3+
      - Stealth enemies appear from wave 7+
    """
    enemies: List[Tuple[EnemyType, int]] = []
    count = 5 + wave_num * 2

    if wave_num % 5 == 0 and wave_num > 0:
        # Boss wave: mix of regulars plus a boss
        for _ in range(count - 1):
            etype = random.choice([EnemyType.BASIC, EnemyType.FAST, EnemyType.SWARM])
            enemies.append((etype, 10))
        enemies.append((EnemyType.BOSS, 20))
    else:
        pool = [EnemyType.BASIC]
        if wave_num >= 2:
            pool.append(EnemyType.FAST)
        if wave_num >= 3:
            pool.append(EnemyType.SWARM)
        if wave_num >= 4:
            pool.append(EnemyType.TANK)
        if wave_num >= 6:
            pool.append(EnemyType.HEALER)
        if wave_num >= 7:
            pool.append(EnemyType.STEALTH)
        # Higher waves add more swarm packs
        swarm_count = max(0, (wave_num - 3) // 2)
        for _ in range(count - swarm_count):
            etype = random.choice(pool)
            delay = 10 if etype != EnemyType.BOSS else 20
            enemies.append((etype, delay))
        # Swarm packs: groups of 3-5 with short delays
        pack_size = min(3 + wave_num // 4, 5)
        for _ in range(swarm_count):
            for j in range(pack_size):
                enemies.append((EnemyType.SWARM, 4 if j == 0 else 4))
    return enemies


def describe_wave(wave_num: int) -> str:
    """Return a short description of what's in a wave for the wave preview."""
    if wave_num <= 0:
        return "Press SPACE to start wave 1"
    wave = generate_wave(wave_num)
    counts: Dict[EnemyType, int] = {}
    for etype, _ in wave:
        counts[etype] = counts.get(etype, 0) + 1
    parts = []
    # Show in a sensible order
    order = [EnemyType.BASIC, EnemyType.FAST, EnemyType.SWARM, EnemyType.TANK,
             EnemyType.HEALER, EnemyType.STEALTH, EnemyType.BOSS]
    for etype in order:
        if etype in counts:
            name = ENEMY_DATA[etype]["name"]
            n = counts[etype]
            parts.append(f"{n}x{name}")
    return " | ".join(parts) if parts else "Empty wave"


# ─── Main Game ──────────────────────────────────────────────────────────────
class Game:
    """Core game state and logic for Terminal Tower Defense."""

    def __init__(self, difficulty: str = "normal"):
        diff = DIFFICULTY_SETTINGS.get(difficulty, DIFFICULTY_SETTINGS["normal"])
        self.difficulty = difficulty
        self.gold = diff["gold"]
        self.lives = diff["lives"]
        self.score = 0
        self.wave_num = 0
        self.wave_active = False
        self.wave_enemies: List[Tuple[EnemyType, int]] = []
        self.spawn_timer = 0
        self.enemies: List[Enemy] = []
        self.towers: List[Tower] = []
        self.projectiles: List[Projectile] = []
        self.tower_grid: Dict[Tuple[int, int], Tower] = {}
        self.path_set, self.ordered_path = build_path(WAYPOINTS)
        self.grid = [[Tile.EMPTY for _ in range(MAP_W)] for _ in range(MAP_H)]
        for c, r in self.path_set:
            self.grid[r][c] = Tile.PATH
        self.cursor_col = 10
        self.cursor_row = 10
        self.selected_tower = 0
        self.log: deque = deque(maxlen=50)
        self.log.append("Welcome to Terminal Tower Defense v2.3!")
        self.log.append("Place towers to defend against waves of enemies.")
        self.log.append("Press SPACE to start wave 1. Press q to quit.")
        self.log.append("Press 'a' for auto-wave, 'f' for fast-forward.")
        self.paused = False
        self.game_over = False
        self.auto_wave = False
        self.fast_forward = False
        self.frame = 0
        self.total_kills = 0
        # Power-ups
        self.bomb_charges = 0
        self.freeze_charges = 0
        self.gold_rush_charges = 0
        self.freeze_timer = 0        # frames remaining for freeze effect
        self.gold_rush_timer = 0     # frames remaining for gold rush
        # Statistics tracking
        self.towers_placed = 0
        self.towers_upgraded = 0
        self.towers_sold = 0
        self.total_gold_earned = 0
        self.interest_earned = 0

    def add_log(self, msg: str) -> None:
        """Add a message to the in-game event log."""
        self.log.append(msg)

    def place_tower(self, ttype: TowerType) -> None:
        """Attempt to place a tower at the cursor position."""
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
        self.towers_placed += 1
        self.add_log(f"Placed {data['name']} tower at ({c},{r}) for {data['cost']}g")

    def upgrade_tower(self) -> None:
        """Attempt to upgrade the tower under the cursor."""
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
        self.towers_upgraded += 1
        self.add_log(f"Upgraded {tower.name} to Lv{tower.level} for {cost}g")

    def sell_tower(self) -> None:
        """Sell the tower under the cursor for 50% of total invested gold."""
        c, r = self.cursor_col, self.cursor_row
        tower = self.tower_grid.get((c, r))
        if tower is None:
            self.add_log("No tower at cursor.")
            return
        value = tower.sell_value()
        self.gold += value
        # Note: sell refund is NOT counted in total_gold_earned
        # (it's a refund of previously spent gold, not new income)
        self.towers.remove(tower)
        del self.tower_grid[(c, r)]
        self.grid[r][c] = Tile.EMPTY
        self.towers_sold += 1
        self.add_log(f"Sold {tower.name} tower for {value}g")

    def use_bomb(self) -> None:
        """Use a Bomb power-up: deal damage to all enemies on the map."""
        if self.bomb_charges <= 0:
            self.add_log("No bombs available!")
            return
        if not self.enemies:
            self.add_log("No enemies to bomb!")
            return
        self.bomb_charges -= 1
        hit_count = 0
        for e in self.enemies:
            if e.alive:
                # Bomb doesn't trigger dodge for stealth (it's AoE)
                e.hp -= BOMB_DAMAGE
                e.hit_flash = 3
                if e.hp <= 0:
                    e.hp = 0
                    e.alive = False
                hit_count += 1
        self.add_log(f"💥 BOMB! Hit {hit_count} enemies for {BOMB_DAMAGE} damage!")

    def use_freeze(self) -> None:
        """Use a Freeze power-up: freeze all enemies for a duration."""
        if self.freeze_charges <= 0:
            self.add_log("No freeze charges available!")
            return
        self.freeze_charges -= 1
        self.freeze_timer = FREEZE_DURATION
        self.add_log(f"❄ FREEZE! All enemies frozen for {FREEZE_DURATION // 20}s!")

    def use_gold_rush(self) -> None:
        """Use a Gold Rush power-up: double gold for a duration."""
        if self.gold_rush_charges <= 0:
            self.add_log("No gold rush charges available!")
            return
        self.gold_rush_charges -= 1
        self.gold_rush_timer = GOLD_RUSH_DURATION
        self.add_log(f"💰 GOLD RUSH! Double gold for {GOLD_RUSH_DURATION // 20}s!")

    def start_wave(self) -> None:
        """Begin the next wave of enemies."""
        if self.game_over:
            self.add_log("Game is over! Press 'r' to restart.")
            return
        if self.wave_active:
            self.add_log("Wave already in progress!")
            return
        self.wave_num += 1
        self.wave_active = True
        self.wave_enemies = generate_wave(self.wave_num)
        self.spawn_timer = 0
        self.add_log(f"=== Wave {self.wave_num} starts! ===")

    def _apply_projectile_hit(self, proj: Projectile) -> None:
        """Apply damage/effects from a projectile that has reached its target."""
        source = proj.source_tower  # May be None for older projectiles
        if proj.chain > 0:
            # Lightning: hits primary target, then chains to nearby enemies
            hit_enemies: List[Enemy] = []
            # Find primary target (nearest alive enemy to impact point)
            primary = None
            best_dist = float('inf')
            for e in self.enemies:
                if e.alive:
                    ec, er = e.position(self.ordered_path)
                    dist = math.sqrt((ec - proj.col) ** 2 + (er - proj.row) ** 2)
                    if dist < best_dist:
                        best_dist = dist
                        primary = e
            if primary and best_dist < 2.0:
                primary.take_damage(proj.damage, source)
                hit_enemies.append(primary)
                # Chain to nearby enemies
                chain_remaining = proj.chain
                chain_range = 3.0
                last_ec, last_er = primary.position(self.ordered_path)
                while chain_remaining > 0:
                    next_enemy = None
                    next_dist = float('inf')
                    for e in self.enemies:
                        if e.alive and e not in hit_enemies:
                            ec, er = e.position(self.ordered_path)
                            dist = math.sqrt((ec - last_ec) ** 2 + (er - last_er) ** 2)
                            if dist <= chain_range and dist < next_dist:
                                next_dist = dist
                                next_enemy = e
                    if next_enemy:
                        chain_damage = int(proj.damage * 0.7)  # 70% damage per chain
                        next_enemy.take_damage(chain_damage, source)
                        hit_enemies.append(next_enemy)
                        last_ec, last_er = next_enemy.position(self.ordered_path)
                        chain_remaining -= 1
                    else:
                        break
                # Kill counting is handled in update() — don't double-count here
        elif proj.splash > 0:
            # Splash damage: full to primary, reduced to others in radius
            for e in self.enemies:
                if e.alive:
                    ec, er = e.position(self.ordered_path)
                    dist = math.sqrt((ec - proj.col) ** 2 + (er - proj.row) ** 2)
                    if dist <= proj.splash:
                        # Damage falls off with distance from center
                        falloff = max(0.5, 1.0 - dist / (proj.splash + 1))
                        damage = int(proj.damage * falloff)
                        e.take_damage(max(1, damage), source)
                        if proj.slow > 0:
                            e.apply_slow()
                        if proj.poison > 0:
                            e.apply_poison(proj.poison)
        else:
            # Single target: hit nearest alive enemy to impact point
            best = None
            best_dist = float('inf')
            for e in self.enemies:
                if e.alive:
                    ec, er = e.position(self.ordered_path)
                    dist = math.sqrt((ec - proj.col) ** 2 + (er - proj.row) ** 2)
                    if dist < best_dist:
                        best_dist = dist
                        best = e
            if best and best_dist < 1.5:
                hit = best.take_damage(proj.damage, source)
                if hit:  # only apply effects if damage wasn't dodged
                    if proj.slow > 0:
                        best.apply_slow()
                    if proj.poison > 0:
                        best.apply_poison(proj.poison)

    def update(self) -> None:
        """Advance game state by one frame."""
        if self.paused or self.game_over:
            return
        self.frame += 1

        # Check power-up states BEFORE decrementing timers
        # (so the last frame of a power-up still has its effect active)
        is_frozen = self.freeze_timer > 0
        gold_rush_active = self.gold_rush_timer > 0

        # Decrement power-up timers AFTER checking their state
        if self.freeze_timer > 0:
            self.freeze_timer -= 1
        if self.gold_rush_timer > 0:
            self.gold_rush_timer -= 1

        # Spawn enemies
        if self.wave_enemies:
            self.spawn_timer -= 1
            if self.spawn_timer <= 0:
                etype, delay = self.wave_enemies.pop(0)
                self.enemies.append(Enemy(etype, self.wave_num, self.difficulty))
                self.spawn_timer = delay

        # Update enemies
        for e in self.enemies:
            if e.alive:
                e.update(self.ordered_path, frozen=is_frozen)
                if e.reached_end:
                    self.lives -= 1
                    self.add_log(f"{e.name} reached the end! ({max(0, self.lives)} lives left)")
                    if self.lives <= 0 and not self.game_over:
                        self.game_over = True
                        self.add_log("GAME OVER! All lives lost.")
                        stats = self.get_stats()
                        save_highscore(self.score, self.wave_num, self.difficulty, stats)

        # Healer enemies heal nearby allies
        for e in self.enemies:
            if e.alive and e.etype == EnemyType.HEALER and e.heal > 0:
                ec, er = e.grid_pos(self.ordered_path)
                for other in self.enemies:
                    if other.alive and other is not e:
                        oc, orow = other.grid_pos(self.ordered_path)
                        if abs(oc - ec) + abs(orow - er) <= 2:
                            other.hp = min(other.max_hp, other.hp + e.heal)

        # Remove dead/reached enemies and award gold
        surviving: List[Enemy] = []
        for e in self.enemies:
            if not e.alive:
                if not e.reached_end:
                    # Gold rush: double reward (using state from before timer decrement)
                    reward = e.reward * (2 if gold_rush_active else 1)
                    self.gold += reward
                    self.total_gold_earned += reward
                    self.score += e.reward * 2
                    self.total_kills += 1
                    # Track which tower got the kill
                    if e.killed_by is not None:
                        e.killed_by.kills += 1
            else:
                surviving.append(e)
        self.enemies = surviving

        # Check wave complete
        if self.wave_active and not self.wave_enemies and not self.enemies:
            self.wave_active = False
            # Wave clear bonus
            bonus = 25 + self.wave_num * 10
            self.gold += bonus
            self.total_gold_earned += bonus
            self.add_log(f"Wave {self.wave_num} cleared! Bonus: {bonus}g")
            # Interest on unspent gold
            interest = int(self.gold * INTEREST_RATE)
            if interest > 0:
                interest = min(interest, INTEREST_MAX_GOLD)
                self.gold += interest
                self.total_gold_earned += interest
                self.interest_earned += interest
                self.add_log(f"Interest earned: {interest}g ({int(INTEREST_RATE * 100)}%)")
            # Award power-up charges
            self.bomb_charges += POWER_UP_PER_WAVE
            self.freeze_charges += POWER_UP_PER_WAVE
            self.gold_rush_charges += POWER_UP_PER_WAVE
            self.add_log(f"+1 Bomb, +1 Freeze, +1 Gold Rush charge!")
            # Auto-wave: start next wave after short delay
            if self.auto_wave:
                self.start_wave()

        # Towers fire
        for tower in self.towers:
            proj = tower.try_fire(self.enemies, self.ordered_path)
            if proj:
                self.projectiles.append(proj)

        # Update projectiles and apply hits
        for p in list(self.projectiles):
            hit = p.update()
            if hit:
                self._apply_projectile_hit(p)
            if not p.alive:
                self.projectiles.remove(p)

    def get_stats(self) -> dict:
        """Return a dictionary of game statistics."""
        return {
            "total_kills": self.total_kills,
            "towers_placed": self.towers_placed,
            "towers_upgraded": self.towers_upgraded,
            "towers_sold": self.towers_sold,
            "total_gold_earned": self.total_gold_earned,
            "interest_earned": self.interest_earned,
        }


# ─── Renderer ───────────────────────────────────────────────────────────────
class Renderer:
    """Handles all curses-based rendering for the game."""

    def __init__(self, stdscr, game: Game):
        self.stdscr = stdscr
        self.game = game
        self.colors_initialized = False

    def init_colors(self) -> None:
        """Initialize curses color pairs. Safe to call multiple times."""
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
        curses.init_pair(8, 136, -1)
        # Pair 9: cursor highlight
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_WHITE)
        # Pair 10-16: tower colors
        curses.init_pair(10, curses.COLOR_GREEN, -1)     # Arrow
        curses.init_pair(11, curses.COLOR_RED, -1)        # Cannon
        curses.init_pair(12, curses.COLOR_CYAN, -1)       # Ice
        curses.init_pair(13, curses.COLOR_YELLOW, -1)     # Sniper
        curses.init_pair(14, curses.COLOR_MAGENTA, -1)    # Mortar
        curses.init_pair(15, curses.COLOR_BLUE, -1)       # Lightning
        curses.init_pair(16, curses.COLOR_GREEN, -1)       # Poison (bright green)
        # Pair 20-26: enemy colors
        curses.init_pair(20, curses.COLOR_RED, -1)       # Basic
        curses.init_pair(21, curses.COLOR_YELLOW, -1)    # Fast
        curses.init_pair(22, curses.COLOR_MAGENTA, -1)    # Tank
        curses.init_pair(23, curses.COLOR_GREEN, -1)      # Healer
        curses.init_pair(24, curses.COLOR_WHITE, -1)      # Boss
        curses.init_pair(25, curses.COLOR_CYAN, -1)      # Swarm
        curses.init_pair(26, curses.COLOR_BLUE, -1)       # Stealth
        # Pair 30: HP bar (green on red)
        curses.init_pair(30, curses.COLOR_GREEN, curses.COLOR_RED)
        # Pair 31: dim text
        curses.init_pair(31, 240, -1)
        # Pair 32: gold color
        curses.init_pair(32, 220, -1)
        # Pair 33: hit flash (bright white)
        curses.init_pair(33, curses.COLOR_WHITE, curses.COLOR_RED)
        # Pair 34: freeze indicator (bright cyan on blue)
        curses.init_pair(34, curses.COLOR_CYAN, curses.COLOR_BLUE)
        # Pair 35: gold rush indicator (bright yellow on black)
        curses.init_pair(35, curses.COLOR_YELLOW, -1)
        # Pair 36: stealth enemy dim (dark blue)
        curses.init_pair(36, 54, -1)
        self.colors_initialized = True

    def color_pair_for_enemy(self, e: Enemy) -> int:
        mapping = {
            EnemyType.BASIC: 20,
            EnemyType.FAST: 21,
            EnemyType.TANK: 22,
            EnemyType.HEALER: 23,
            EnemyType.BOSS: 24,
            EnemyType.SWARM: 25,
            EnemyType.STEALTH: 26,
        }
        return mapping.get(e.etype, 1)

    def color_pair_for_tower(self, t: Tower) -> int:
        mapping = {
            TowerType.ARROW: 10,
            TowerType.CANNON: 11,
            TowerType.ICE: 12,
            TowerType.SNIPER: 13,
            TowerType.MORTAR: 14,
            TowerType.LIGHTNING: 15,
            TowerType.POISON: 16,
        }
        return mapping.get(t.ttype, 1)

    def color_pair_for_tower_type(self, tt: TowerType) -> int:
        mapping = {
            TowerType.ARROW: 10,
            TowerType.CANNON: 11,
            TowerType.ICE: 12,
            TowerType.SNIPER: 13,
            TowerType.MORTAR: 14,
            TowerType.LIGHTNING: 15,
            TowerType.POISON: 16,
        }
        return mapping.get(tt, 1)

    def draw(self) -> None:
        """Render the complete game frame."""
        g = self.game
        stdscr = self.stdscr
        stdscr.clear()

        # ── Header ──
        header = (f" ⚔ TOWER DEFENSE ⚔  Wave: {g.wave_num}  "
                  f"Gold: {g.gold}  Lives: {max(0, g.lives)}  Score: {g.score}  "
                  f"Kills: {g.total_kills}")
        if g.paused:
            header += " [PAUSED]"
        if g.game_over:
            header += " [GAME OVER]"
        if g.auto_wave:
            header += " [AUTO]"
        if g.fast_forward:
            header += " [FFx2]"
        if g.freeze_timer > 0:
            header += " [FROZEN]"
        if g.gold_rush_timer > 0:
            header += " [GOLDx2]"
        try:
            stdscr.addstr(0, 0, header[:curses.COLS], curses.A_BOLD)
        except curses.error:
            pass

        # ── Map ──
        display = [[('·', 31) for _ in range(MAP_W)] for _ in range(MAP_H)]

        # Path tiles
        for r in range(MAP_H):
            for c in range(MAP_W):
                if g.grid[r][c] == Tile.PATH:
                    display[r][c] = ('█', 8)

        # Towers (show level indicator)
        for t in g.towers:
            level_char = t.char if t.level == 1 else str(min(t.level, 9))
            display[t.row][t.col] = (level_char, self.color_pair_for_tower(t))

        # Projectiles
        for p in g.projectiles:
            pc, pr = int(round(p.col)), int(round(p.row))
            if 0 <= pr < MAP_H and 0 <= pc < MAP_W:
                if p.chain > 0:
                    proj_char = '~'  # lightning
                elif p.poison > 0:
                    proj_char = 'p'  # poison
                elif p.splash > 1:
                    proj_char = '*'  # mortar
                elif p.splash > 0:
                    proj_char = 'o'  # cannon
                else:
                    proj_char = '·'  # single target
                display[pr][pc] = (proj_char, 7)

        # Cursor range indicator
        ct = g.tower_grid.get((g.cursor_col, g.cursor_row))
        selected_type = TowerType(g.selected_tower)
        sel_data = TOWER_DATA.get(selected_type, TOWER_DATA[TowerType.ARROW])
        range_val = ct.range if ct else sel_data["range"]
        for dr in range(-range_val, range_val + 1):
            for dc in range(-range_val, range_val + 1):
                rr, cc = g.cursor_row + dr, g.cursor_col + dc
                if 0 <= rr < MAP_H and 0 <= cc < MAP_W:
                    if abs(dr) + abs(dc) <= range_val:
                        if display[rr][cc][0] == '·':
                            display[rr][cc] = ('░', 31)

        # Enemies (draw on top of everything)
        for e in g.enemies:
            if e.alive:
                # Stealth enemies are invisible part of the time
                if e.stealth and not e.visible:
                    # Don't render invisible stealth enemies
                    continue
                ec, er = e.grid_pos(g.ordered_path)
                if 0 <= er < MAP_H and 0 <= ec < MAP_W:
                    char = e.char
                    cpair = self.color_pair_for_enemy(e)
                    # Poison indicator
                    if e.poison_timer > 0:
                        char = 'p'
                        cpair = 16  # poison green
                    # Hit flash: briefly show '!' when hit
                    elif e.hit_flash > 0:
                        char = '!'
                        cpair = 7  # bright white
                    # Freeze indicator
                    if g.freeze_timer > 0 and e.alive:
                        cpair = 34  # frozen colors
                    display[er][ec] = (char, cpair)

        # Draw the grid
        offset_y = 1
        for r in range(MAP_H):
            for c in range(MAP_W):
                ch, cpair = display[r][c]
                if c == g.cursor_col and r == g.cursor_row:
                    try:
                        stdscr.addstr(offset_y + r, c, ch, curses.color_pair(cpair) | curses.A_REVERSE)
                    except curses.error:
                        pass
                else:
                    try:
                        stdscr.addstr(offset_y + r, c, ch, curses.color_pair(cpair))
                    except curses.error:
                        pass

        # ── Sidebar ──
        sx = MAP_W + 2
        sy = 1

        # Tower selection list (7 towers now)
        stdscr.addstr(sy, sx, "── TOWERS ──", curses.A_BOLD)
        for i, tt in enumerate(TowerType):
            data = TOWER_DATA[tt]
            marker = "►" if i == g.selected_tower else " "
            line = f"{marker}{i+1} {data['char']} {data['name']:9s} {data['cost']:3d}g"
            cpair = self.color_pair_for_tower_type(tt)
            if i == g.selected_tower:
                try:
                    stdscr.addstr(sy + 1 + i, sx, line, curses.color_pair(cpair) | curses.A_BOLD)
                except curses.error:
                    pass
            else:
                try:
                    stdscr.addstr(sy + 1 + i, sx, line, curses.color_pair(cpair))
                except curses.error:
                    pass

        # Tower details
        dy = sy + 1 + len(TowerType) + 1
        ct = g.tower_grid.get((g.cursor_col, g.cursor_row))
        if ct:
            stdscr.addstr(dy, sx, "── TOWER INFO ──", curses.A_BOLD)
            stdscr.addstr(dy + 1, sx, f"{ct.name} Lv{ct.level}")
            stdscr.addstr(dy + 2, sx, f"DMG: {ct.damage}  RNG: {ct.range}")
            stdscr.addstr(dy + 3, sx, f"Kills: {ct.kills}")
            uc = ct.upgrade_cost()
            if uc:
                stdscr.addstr(dy + 4, sx, f"Upgrade: {uc}g [u]")
            else:
                stdscr.addstr(dy + 4, sx, "MAX LEVEL")
            stdscr.addstr(dy + 5, sx, f"Sell: {ct.sell_value()}g [s]")
        else:
            sel_data = TOWER_DATA[selected_type]
            stdscr.addstr(dy, sx, f"── {sel_data['name'].upper()} TOWER ──", curses.A_BOLD)
            stdscr.addstr(dy + 1, sx, f"Cost: {sel_data['cost']}g")
            stdscr.addstr(dy + 2, sx, f"DMG: {sel_data['damage']}  RNG: {sel_data['range']}")
            stdscr.addstr(dy + 3, sx, f"Rate: {sel_data['fire_rate']}")
            if sel_data['splash'] > 0:
                stdscr.addstr(dy + 4, sx, f"Splash: {sel_data['splash']}")
            elif sel_data['slow'] > 0:
                stdscr.addstr(dy + 4, sx, f"Slow: {int(sel_data['slow'] * 100)}%")
            elif sel_data['chain'] > 0:
                stdscr.addstr(dy + 4, sx, f"Chain: {sel_data['chain']} targets")
            elif sel_data.get('poison', 0) > 0:
                stdscr.addstr(dy + 4, sx, f"Poison: {sel_data['poison']} dmg/tick")

        # Power-ups
        py = dy + 7
        stdscr.addstr(py, sx, "── POWER-UPS ──", curses.A_BOLD)
        stdscr.addstr(py + 1, sx, f"b Bomb: {g.bomb_charges}")
        stdscr.addstr(py + 2, sx, f"e Freeze: {g.freeze_charges}")
        stdscr.addstr(py + 3, sx, f"d GoldRush: {g.gold_rush_charges}")
        if g.freeze_timer > 0:
            stdscr.addstr(py + 1, sx + 16, f"[{g.freeze_timer // 20 + 1}s]", curses.color_pair(6) | curses.A_BOLD)
        if g.gold_rush_timer > 0:
            stdscr.addstr(py + 3, sx + 16, f"[{g.gold_rush_timer // 20 + 1}s]", curses.color_pair(3) | curses.A_BOLD)

        # Wave preview (show next wave composition)
        wy = py + 5
        if not g.wave_active and g.wave_num == 0:
            stdscr.addstr(wy, sx, "── NEXT WAVE ──", curses.A_BOLD)
            stdscr.addstr(wy + 1, sx, "Press SPACE to start!", curses.color_pair(3))
        elif not g.wave_active:
            preview = describe_wave(g.wave_num + 1)
            stdscr.addstr(wy, sx, "── NEXT WAVE ──", curses.A_BOLD)
            # Truncate if too long for sidebar
            if len(preview) > SIDEBAR_W - 2:
                preview = preview[:SIDEBAR_W - 5] + "..."
            stdscr.addstr(wy + 1, sx, preview[:SIDEBAR_W - 2])

        # Controls
        cy = wy + 3
        stdscr.addstr(cy, sx, "── CONTROLS ──", curses.A_BOLD)
        controls = [
            "←→↑↓  Move cursor",
            "1-7    Place tower",
            "u      Upgrade",
            "s      Sell tower",
            "SPACE  Start wave",
            "a      Auto-wave",
            "f      Fast-forward",
            "b/e/d  Power-ups",
            "p      Pause",
            "q/Esc  Quit",
        ]
        for i, line in enumerate(controls):
            try:
                stdscr.addstr(cy + 1 + i, sx, line)
            except curses.error:
                pass

        # ── Enemy list in sidebar ──
        ey = cy + 1 + len(controls) + 1
        if g.enemies:
            try:
                stdscr.addstr(ey, sx, f"── ENEMIES ({len(g.enemies)}) ──", curses.A_BOLD)
                for i, e in enumerate(g.enemies[:3]):
                    hp_pct = e.hp / e.max_hp if e.max_hp > 0 else 0
                    bar_len = 8
                    filled = int(hp_pct * bar_len)
                    bar = '█' * filled + '░' * (bar_len - filled)
                    status = ""
                    if e.poison_timer > 0:
                        status = " psn"
                    if g.freeze_timer > 0 and e.alive:
                        status += " frz"
                    line = f"{e.char}{bar}{e.hp}/{e.max_hp}{status}"
                    cpair = self.color_pair_for_enemy(e)
                    stdscr.addstr(ey + 1 + i, sx, line[:SIDEBAR_W - 2], curses.color_pair(cpair))
                if len(g.enemies) > 3:
                    stdscr.addstr(ey + 4, sx, f"  ...+{len(g.enemies) - 3} more")
            except curses.error:
                pass

        # ── Log ──
        log_y = MAP_H + 2
        try:
            stdscr.addstr(log_y, 0, "─" * (MAP_W + SIDEBAR_W + 2))
        except curses.error:
            pass
        logs = list(g.log)[-LOG_H:]
        for i, msg in enumerate(logs):
            if i < LOG_H:
                try:
                    stdscr.addstr(log_y + 1 + i, 0, msg[:MAP_W + SIDEBAR_W + 2])
                except curses.error:
                    pass

        stdscr.refresh()


# ─── Difficulty Selection Screen ────────────────────────────────────────────
def select_difficulty(stdscr) -> str:
    """Show a difficulty selection screen and return the chosen difficulty."""
    curses.curs_set(0)
    difficulties = ["easy", "normal", "hard"]
    selected = 1  # default: normal
    colors = [curses.color_pair(2), curses.color_pair(3) | curses.A_BOLD, curses.color_pair(1)]

    while True:
        stdscr.clear()
        title = "⚔ TERMINAL TOWER DEFENSE ⚔"
        subtitle = "Select Difficulty"
        stdscr.addstr(curses.LINES // 2 - 4,
                      max(0, (curses.COLS - len(title)) // 2), title, curses.A_BOLD)
        stdscr.addstr(curses.LINES // 2 - 2,
                      max(0, (curses.COLS - len(subtitle)) // 2), subtitle)

        descs = [
            ("Easy",   "300g start | 30 lives | 0.8x enemy HP | 1.2x rewards"),
            ("Normal", "200g start | 20 lives | 1.0x enemy HP | 1.0x rewards"),
            ("Hard",   "150g start | 10 lives | 1.3x enemy HP | 0.8x rewards"),
        ]
        for i, (name, desc) in enumerate(descs):
            marker = "  ► " if i == selected else "    "
            line = f"{marker}{name}: {desc}"
            y = curses.LINES // 2 + i
            if i == selected:
                stdscr.addstr(y, max(0, (curses.COLS - len(line)) // 2), line,
                              curses.A_BOLD | colors[i])
            else:
                stdscr.addstr(y, max(0, (curses.COLS - len(line)) // 2), line)

        stdscr.addstr(curses.LINES // 2 + 5,
                      max(0, (curses.COLS - 30) // 2),
                      "↑↓ to select, ENTER to confirm")

        stdscr.refresh()
        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')):
            selected = (selected - 1) % 3
        elif key in (curses.KEY_DOWN, ord('j')):
            selected = (selected + 1) % 3
        elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER):
            return difficulties[selected]


# ─── High Scores Screen ────────────────────────────────────────────────────
def show_highscores(stdscr) -> None:
    """Display the high scores screen after game over."""
    stdscr.clear()
    title = "HIGH SCORES"
    stdscr.addstr(1, max(0, (curses.COLS - len(title)) // 2), title, curses.A_BOLD)

    scores = load_highscores()
    if not scores:
        stdscr.addstr(3, max(0, (curses.COLS - 20) // 2), "No scores yet!")
    else:
        header = f"{'#':<4}{'Score':<8}{'Wave':<6}{'Difficulty':<12}{'Date':<18}"
        stdscr.addstr(3, max(0, (curses.COLS - len(header)) // 2), header, curses.A_UNDERLINE)
        for i, entry in enumerate(scores[:10]):
            line = (f"{i+1:<4}{entry.get('score', 0):<8}"
                    f"{entry.get('wave', 0):<6}"
                    f"{entry.get('difficulty', '?'):<12}"
                    f"{entry.get('date', ''):<18}")
            stdscr.addstr(4 + i, max(0, (curses.COLS - len(line)) // 2), line)

    stdscr.addstr(curses.LINES - 2,
                  max(0, (curses.COLS - 26) // 2),
                  "Press any key to continue")
    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()


# ─── Main Loop ──────────────────────────────────────────────────────────────
# Module-level difficulty (set by CLI before launching curses)
_selected_difficulty = "normal"


def main(stdscr):
    """Entry point for the game, wrapped by curses."""
    # Use the globally selected difficulty, or let user choose in-game
    difficulty = _selected_difficulty

    # Terminal size check
    if curses.COLS < MIN_TERM_W or curses.LINES < MIN_TERM_H:
        stdscr.clear()
        msg = (f"Terminal too small! Need at least {MIN_TERM_W}x{MIN_TERM_H}, "
               f"got {curses.COLS}x{curses.LINES}")
        stdscr.addstr(0, 0, msg)
        stdscr.addstr(1, 0, "Press any key to exit.")
        stdscr.refresh()
        stdscr.nodelay(False)
        stdscr.getch()
        return

    # Difficulty selection — skip menu if pre-selected via CLI
    if _selected_difficulty in DIFFICULTY_SETTINGS:
        difficulty = _selected_difficulty
    else:
        difficulty = select_difficulty(stdscr)

    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(50)  # 50ms refresh = 20fps

    game = Game(difficulty)
    renderer = Renderer(stdscr, game)
    renderer.init_colors()

    while True:
        # ── Input ──
        key = stdscr.getch()
        if key != -1:
            if key in (ord('q'), 27):  # q or Esc
                break
            elif key == ord('p'):
                game.paused = not game.paused
            elif key == ord(' '):
                game.start_wave()
            elif key == ord('a'):
                game.auto_wave = not game.auto_wave
                game.add_log(f"Auto-wave {'ON' if game.auto_wave else 'OFF'}")
                if game.auto_wave and not game.wave_active:
                    game.start_wave()
            elif key == ord('f'):
                game.fast_forward = not game.fast_forward
                game.add_log(f"Fast-forward {'ON' if game.fast_forward else 'OFF'}")
                stdscr.timeout(25 if game.fast_forward else 50)
            elif key == ord('b'):
                game.use_bomb()
            elif key == ord('e'):
                game.use_freeze()
            elif key == ord('d'):
                game.use_gold_rush()
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
            elif key == ord('6'):
                game.place_tower(TowerType.LIGHTNING)
            elif key == ord('7'):
                game.place_tower(TowerType.POISON)
            elif key == ord('u'):
                game.upgrade_tower()
            elif key == ord('s'):
                game.sell_tower()
            elif key == ord('\t'):
                game.selected_tower = (game.selected_tower + 1) % len(TowerType)

        # ── Update ──
        game.update()

        # ── Draw ──
        renderer.draw()

        # ── Game over ──
        if game.game_over:
            stdscr.nodelay(False)
            stdscr.timeout(-1)
            # Show game over screen with stats
            stdscr.clear()
            stats = game.get_stats()
            end_msgs = [
                "╔══════════════════════════════════════╗",
                "║          GAME OVER                   ║",
                f"║  Final Score: {game.score:<24}║",
                f"║  Waves Survived: {game.wave_num:<19}║",
                f"║  Total Kills: {game.total_kills:<22}║",
                f"║  Difficulty: {game.difficulty:<23}║",
                f"║  Towers Placed: {stats['towers_placed']:<20}║",
                f"║  Towers Upgraded: {stats['towers_upgraded']:<18}║",
                f"║  Gold Earned: {stats['total_gold_earned']:<21}║",
                f"║  Interest Earned: {stats['interest_earned']:<18}║",
                "╚══════════════════════════════════════╝",
                "",
                "  [r] Restart   [h] High Scores   [q] Quit",
            ]
            for i, line in enumerate(end_msgs):
                try:
                    stdscr.addstr(curses.LINES // 2 - 6 + i,
                                  max(0, (curses.COLS - len(line)) // 2), line,
                                  curses.A_BOLD if i < 11 else curses.A_NORMAL)
                except curses.error:
                    pass
            stdscr.refresh()

            while True:
                choice = stdscr.getch()
                if choice == ord('r'):
                    # Restart game
                    game = Game(difficulty)
                    renderer = Renderer(stdscr, game)
                    renderer.init_colors()
                    stdscr.nodelay(True)
                    stdscr.timeout(50 if not game.fast_forward else 25)
                    break
                elif choice == ord('h'):
                    show_highscores(stdscr)
                    # Return to game over screen loop
                    continue
                elif choice in (ord('q'), 27):
                    return
            continue  # go back to main loop

    # End screen (normal quit)
    stdscr.clear()
    end_msg = f"Thanks for playing! Score: {game.score} | Waves: {game.wave_num}"
    stdscr.addstr(curses.LINES // 2,
                  max(0, (curses.COLS - len(end_msg)) // 2), end_msg, curses.A_BOLD)
    stdscr.addstr(curses.LINES // 2 + 1,
                  max(0, (curses.COLS - 20) // 2), "Press any key to exit")
    stdscr.refresh()
    stdscr.nodelay(False)
    stdscr.getch()


# ─── CLI Entry Point ────────────────────────────────────────────────────────
def cli_main():
    """Parse command-line arguments and launch the game."""
    parser = argparse.ArgumentParser(
        description="Terminal Tower Defense — a fully playable tower defense game in your terminal.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 tower_defense.py                  Play on normal difficulty
  python3 tower_defense.py --difficulty hard Play on hard difficulty
  python3 tower_defense.py --version         Show version and exit

Power-ups (earned by clearing waves):
  b   Bomb — Deal 80 damage to all enemies on screen
  e   Freeze — Freeze all enemies for 3 seconds
  d   Gold Rush — Double gold rewards for 5 seconds
        """,
    )
    parser.add_argument(
        "--version", action="version", version=f"Terminal Tower Defense v{VERSION}",
        help="Show the version number and exit.",
    )
    parser.add_argument(
        "--difficulty", choices=["easy", "normal", "hard"], default=None,
        help="Pre-select difficulty (skip the menu).",
    )
    args = parser.parse_args()

    # If difficulty is pre-selected, pass it through; otherwise the menu will show
    if args.difficulty:
        global _selected_difficulty
        _selected_difficulty = args.difficulty

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    cli_main()