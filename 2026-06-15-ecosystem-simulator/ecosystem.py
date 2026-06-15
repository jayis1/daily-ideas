#!/usr/bin/env python3
"""
ASCII Ecosystem Simulator
==========================
A terminal-based ecosystem simulation with multiple species,
population dynamics, food chains, seasons, and environmental events.
Watch plants, herbivores, and predators interact in real-time.
"""

import random
import time
import sys
import os
import curses
from enum import Enum
from collections import defaultdict


# ─── Configuration ───────────────────────────────────────────────────────────

WORLD_WIDTH = 80
WORLD_HEIGHT = 40
INITIAL_PLANTS = 60
INITIAL_HERBIVORES = 25
INITIAL_PREDATORS = 8
TICK_DELAY = 0.12

PLANT_SPREAD_CHANCE = 0.06
PLANT_MAX_AGE = 80
PLANT_NUTRITION = 20

HERBIVORE_MAX_ENERGY = 100
HERBIVORE_INITIAL_ENERGY = 60
HERBIVORE_MOVE_COST = 2
HERBIVORE_REPRODUCE_THRESHOLD = 65
HERBIVORE_REPRODUCE_COST = 30
HERBIVORE_VISION = 4
HERBIVORE_MAX_AGE = 120

PREDATOR_MAX_ENERGY = 120
PREDATOR_INITIAL_ENERGY = 80
PREDATOR_MOVE_COST = 3
PREDATOR_REPRODUCE_THRESHOLD = 80
PREDATOR_REPRODUCE_COST = 40
PREDATOR_VISION = 6
PREDATOR_HUNT_NUTRITION = 50
PREDATOR_MAX_AGE = 100

SEASON_LENGTH = 50  # ticks per season
DISASTER_CHANCE = 0.005  # per tick


class Season(Enum):
    SPRING = 0
    SUMMER = 1
    AUTUMN = 2
    WINTER = 3

    def next(self):
        return Season((self.value + 1) % 4)

    def emoji(self):
        return {Season.SPRING: "🌱", Season.SUMMER: "☀️",
                Season.AUTUMN: "🍂", Season.WINTER: "❄️"}[self]

    def label(self):
        return self.name.capitalize()


class EventType(Enum):
    DROUGHT = 0
    PLAGUE = 1
    BOUNTY = 2
    STORM = 3

    def label(self):
        return self.name.capitalize()

    def desc(self):
        return {
            EventType.DROUGHT: "Drought! Plants wither...",
            EventType.PLAGUE: "Plague! Creatures fall ill...",
            EventType.BOUNTY: "Bounty! Life flourishes!",
            EventType.STORM: "Storm! Chaos reigns!",
        }[self]


# ─── Entities ────────────────────────────────────────────────────────────────

class Entity:
    _id_counter = 0

    def __init__(self, x, y):
        Entity._id_counter += 1
        self.id = Entity._id_counter
        self.x = x
        self.y = y
        self.age = 0
        self.alive = True


class Plant(Entity):
    char = "♣"
    color_pair = 2  # green

    def __init__(self, x, y):
        super().__init__(x, y)
        self.nutrition = PLANT_NUTRITION
        self.maturity = 0  # grows over time

    def update(self, season):
        self.age += 1
        self.maturity = min(self.maturity + 1, 5)
        # Seasonal effects on aging
        if season == Season.WINTER:
            if random.random() < 0.03:
                self.alive = False
        elif season == Season.AUTUMN:
            if random.random() < 0.01:
                self.alive = False
        elif season == Season.SPRING:
            self.nutrition = min(self.nutrition + 2, PLANT_NUTRITION + 5)

        if self.age > PLANT_MAX_AGE:
            self.alive = False

    def try_spread(self, world):
        if self.maturity < 3:
            return None
        season_mod = {
            Season.SPRING: 2.0, Season.SUMMER: 1.2,
            Season.AUTUMN: 0.5, Season.WINTER: 0.1
        }
        chance = PLANT_SPREAD_CHANCE * season_mod.get(world.season, 1.0)
        if random.random() < chance:
            dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0),
                                     (1, 1), (-1, -1), (1, -1), (-1, 1)])
            nx = (self.x + dx) % WORLD_WIDTH
            ny = (self.y + dy) % WORLD_HEIGHT
            if not world.get_entity_at(nx, ny):
                return Plant(nx, ny)
        return None


class Herbivore(Entity):
    char = "◙"
    color_pair = 3  # cyan

    def __init__(self, x, y):
        super().__init__(x, y)
        self.energy = HERBIVORE_INITIAL_ENERGY
        self.direction = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])

    def update(self, world):
        self.age += 1
        self.energy -= HERBIVORE_MOVE_COST

        # Seasonal energy drain
        if world.season == Season.WINTER:
            self.energy -= 1
        if world.season == Season.SUMMER:
            self.energy += 0.5  # a bit of recovery in summer

        if self.energy <= 0 or self.age > HERBIVORE_MAX_AGE:
            self.alive = False
            return

        # Look for nearby plant
        target = self._find_plant(world)
        if target:
            self._move_toward(target.x, target.y)
            if abs(self.x - target.x) <= 1 and abs(self.y - target.y) <= 1:
                self.energy = min(self.energy + target.nutrition, HERBIVORE_MAX_ENERGY)
                target.alive = False
        else:
            # Random wandering
            if random.random() < 0.3:
                self.direction = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
            dx, dy = self.direction
            self.x = (self.x + dx) % WORLD_WIDTH
            self.y = (self.y + dy) % WORLD_HEIGHT

        # Flee from predators
        predator = self._find_predator(world)
        if predator:
            self._move_away(predator.x, predator.y)

    def _find_plant(self, world):
        best = None
        best_dist = float('inf')
        for p in world.plants:
            if not p.alive:
                continue
            dist = abs(p.x - self.x) + abs(p.y - self.y)
            if dist <= HERBIVORE_VISION and dist < best_dist:
                best = p
                best_dist = dist
        return best

    def _find_predator(self, world):
        for pr in world.predators:
            if not pr.alive:
                continue
            dist = abs(pr.x - self.x) + abs(pr.y - self.y)
            if dist <= 3:
                return pr
        return None

    def _move_toward(self, tx, ty):
        dx = 0 if tx == self.x else (1 if tx > self.x else -1)
        dy = 0 if ty == self.y else (1 if ty > self.y else -1)
        # Handle wrapping
        if abs(tx - self.x) > WORLD_WIDTH // 2:
            dx = -dx
        if abs(ty - self.y) > WORLD_HEIGHT // 2:
            dy = -dy
        self.x = (self.x + dx) % WORLD_WIDTH
        self.y = (self.y + dy) % WORLD_HEIGHT

    def _move_away(self, tx, ty):
        dx = 0 if tx == self.x else (-1 if tx > self.x else 1)
        dy = 0 if ty == self.y else (-1 if ty > self.y else 1)
        self.x = (self.x + dx) % WORLD_WIDTH
        self.y = (self.y + dy) % WORLD_HEIGHT

    def can_reproduce(self):
        return (self.alive and self.energy >= HERBIVORE_REPRODUCE_THRESHOLD
                and self.age > 10 and random.random() < 0.15)

    def reproduce(self):
        self.energy -= HERBIVORE_REPRODUCE_COST
        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
        nx = (self.x + dx) % WORLD_WIDTH
        ny = (self.y + dy) % WORLD_HEIGHT
        baby = Herbivore(nx, ny)
        baby.energy = 40
        return baby


class Predator(Entity):
    char = "♦"
    color_pair = 4  # red

    def __init__(self, x, y):
        super().__init__(x, y)
        self.energy = PREDATOR_INITIAL_ENERGY
        self.direction = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
        self.hunt_cooldown = 0

    def update(self, world):
        self.age += 1
        self.energy -= PREDATOR_MOVE_COST
        self.hunt_cooldown = max(0, self.hunt_cooldown - 1)

        if world.season == Season.WINTER:
            self.energy -= 1

        if self.energy <= 0 or self.age > PREDATOR_MAX_AGE:
            self.alive = False
            return

        # Hunt for herbivores
        target = self._find_herbivore(world)
        if target:
            self._move_toward(target.x, target.y)
            dist = abs(self.x - target.x) + abs(self.y - target.y)
            if dist <= 1 and self.hunt_cooldown == 0:
                self.energy = min(self.energy + PREDATOR_HUNT_NUTRITION, PREDATOR_MAX_ENERGY)
                target.alive = False
                self.hunt_cooldown = 3
        else:
            # Wander
            if random.random() < 0.4:
                self.direction = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
            dx, dy = self.direction
            self.x = (self.x + dx) % WORLD_WIDTH
            self.y = (self.y + dy) % WORLD_HEIGHT

    def _find_herbivore(self, world):
        best = None
        best_dist = float('inf')
        for h in world.herbivores:
            if not h.alive:
                continue
            dist = abs(h.x - self.x) + abs(h.y - self.y)
            if dist <= PREDATOR_VISION and dist < best_dist:
                best = h
                best_dist = dist
        return best

    def _move_toward(self, tx, ty):
        dx = 0 if tx == self.x else (1 if tx > self.x else -1)
        dy = 0 if ty == self.y else (1 if ty > self.y else -1)
        if abs(tx - self.x) > WORLD_WIDTH // 2:
            dx = -dx
        if abs(ty - self.y) > WORLD_HEIGHT // 2:
            dy = -dy
        self.x = (self.x + dx) % WORLD_WIDTH
        self.y = (self.y + dy) % WORLD_HEIGHT

    def can_reproduce(self):
        return (self.alive and self.energy >= PREDATOR_REPRODUCE_THRESHOLD
                and self.age > 15 and random.random() < 0.08)

    def reproduce(self):
        self.energy -= PREDATOR_REPRODUCE_COST
        dx, dy = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
        nx = (self.x + dx) % WORLD_WIDTH
        ny = (self.y + dy) % WORLD_HEIGHT
        baby = Predator(nx, ny)
        baby.energy = 50
        return baby


# ─── World ────────────────────────────────────────────────────────────────────

class World:
    def __init__(self):
        self.tick = 0
        self.season = Season.SPRING
        self.season_tick = 0
        self.plants = []
        self.herbivores = []
        self.predators = []
        self.events = []  # recent events for display
        self.history = {"plants": [], "herbivores": [], "predators": []}
        self.paused = False
        self.speed = 1

        # Spawn initial entities
        for _ in range(INITIAL_PLANTS):
            x = random.randint(0, WORLD_WIDTH - 1)
            y = random.randint(0, WORLD_HEIGHT - 1)
            p = Plant(x, y)
            p.maturity = random.randint(1, 5)
            p.age = random.randint(0, 30)
            self.plants.append(p)

        for _ in range(INITIAL_HERBIVORES):
            x = random.randint(0, WORLD_WIDTH - 1)
            y = random.randint(0, WORLD_HEIGHT - 1)
            self.herbivores.append(Herbivore(x, y))

        for _ in range(INITIAL_PREDATORS):
            x = random.randint(0, WORLD_WIDTH - 1)
            y = random.randint(0, WORLD_HEIGHT - 1)
            self.predators.append(Predator(x, y))

    def get_entity_at(self, x, y):
        for p in self.plants:
            if p.alive and p.x == x and p.y == y:
                return p
        for h in self.herbivores:
            if h.alive and h.x == x and h.y == y:
                return h
        for pr in self.predators:
            if pr.alive and pr.x == x and pr.y == y:
                return pr
        return None

    def update(self):
        if self.paused:
            return

        self.tick += 1
        self.season_tick += 1

        # Season change
        if self.season_tick >= SEASON_LENGTH:
            self.season_tick = 0
            self.season = self.season.next()
            self.events.append(f"Season changed to {self.season.label()}")

        # Random environmental events
        if random.random() < DISASTER_CHANCE:
            self._trigger_event()

        # Update plants
        new_plants = []
        for p in self.plants:
            if p.alive:
                p.update(self.season)
                baby = p.try_spread(self)
                if baby:
                    new_plants.append(baby)
        self.plants = [p for p in self.plants if p.alive] + new_plants

        # Cap plants to prevent runaway
        if len(self.plants) > 300:
            random.shuffle(self.plants)
            for p in self.plants[300:]:
                p.alive = False
            self.plants = self.plants[:300]

        # Update herbivores
        new_herbivores = []
        for h in self.herbivores:
            if h.alive:
                h.update(self)
                if h.can_reproduce():
                    baby = h.reproduce()
                    new_herbivores.append(baby)
        self.herbivores = [h for h in self.herbivores if h.alive] + new_herbivores

        # Update predators
        new_predators = []
        for pr in self.predators:
            if pr.alive:
                pr.update(self)
                if pr.can_reproduce():
                    baby = pr.reproduce()
                    new_predators.append(baby)
        self.predators = [pr for pr in self.predators if pr.alive] + new_predators

        # Record history every 5 ticks
        if self.tick % 5 == 0:
            self.history["plants"].append(len(self.plants))
            self.history["herbivores"].append(len(self.herbivores))
            self.history["predators"].append(len(self.predators))
            # Keep last 100 data points
            for key in self.history:
                if len(self.history[key]) > 100:
                    self.history[key] = self.history[key][-100:]

        # Keep events list short
        if len(self.events) > 5:
            self.events = self.events[-5:]

        # Ecosystem stabilization: respawn if species go extinct
        if len(self.plants) < 5 and self.tick % 10 == 0:
            for _ in range(10):
                x = random.randint(0, WORLD_WIDTH - 1)
                y = random.randint(0, WORLD_HEIGHT - 1)
                self.plants.append(Plant(x, y))

        # Auto-reintroduce herbivores if they go extinct (simulates migration)
        if len(self.herbivores) == 0 and self.tick % 20 == 0 and len(self.plants) > 10:
            for _ in range(3):
                x = random.randint(0, WORLD_WIDTH - 1)
                y = random.randint(0, WORLD_HEIGHT - 1)
                h = Herbivore(x, y)
                h.energy = HERBIVORE_MAX_ENERGY
                self.herbivores.append(h)
            self.events.append("Herbivores migrated into the area!")

        # Auto-reintroduce predators if herbivores exist but predators are extinct
        if len(self.predators) == 0 and len(self.herbivores) > 5 and self.tick % 30 == 0:
            for _ in range(2):
                x = random.randint(0, WORLD_WIDTH - 1)
                y = random.randint(0, WORLD_HEIGHT - 1)
                pr = Predator(x, y)
                pr.energy = PREDATOR_MAX_ENERGY
                self.predators.append(pr)
            self.events.append("Predators migrated into the area!")

    def _trigger_event(self):
        event = random.choice(list(EventType))
        self.events.append(event.desc())

        if event == EventType.DROUGHT:
            # Kill 30% of plants
            for p in random.sample(self.plants, min(len(self.plants), len(self.plants) // 3)):
                p.alive = False
        elif event == EventType.PLAGUE:
            # Kill 20% of herbivores and predators
            if self.herbivores:
                for h in random.sample(self.herbivores, min(len(self.herbivores), len(self.herbivores) // 5)):
                    h.alive = False
            if self.predators:
                for pr in random.sample(self.predators, min(len(self.predators), len(self.predators) // 5)):
                    pr.alive = False
        elif event == EventType.BOUNTY:
            # Spawn new plants
            for _ in range(30):
                x = random.randint(0, WORLD_WIDTH - 1)
                y = random.randint(0, WORLD_HEIGHT - 1)
                p = Plant(x, y)
                p.maturity = 5
                self.plants.append(p)
        elif event == EventType.STORM:
            # Scatter all creatures randomly
            for h in self.herbivores:
                h.x = random.randint(0, WORLD_WIDTH - 1)
                h.y = random.randint(0, WORLD_HEIGHT - 1)
            for pr in self.predators:
                pr.x = random.randint(0, WORLD_WIDTH - 1)
                pr.y = random.randint(0, WORLD_HEIGHT - 1)

    def get_grid(self):
        """Build a character grid of the world."""
        grid = [[' ' for _ in range(WORLD_WIDTH)] for _ in range(WORLD_HEIGHT)]
        grid_colors = [[0 for _ in range(WORLD_WIDTH)] for _ in range(WORLD_HEIGHT)]

        for p in self.plants:
            if p.alive:
                # Plant appearance based on maturity
                chars = {0: '·', 1: '·', 2: '∘', 3: '♣', 4: '♣', 5: '♠'}
                grid[p.y][p.x] = chars.get(p.maturity, '♣')
                grid_colors[p.y][p.x] = 2

        for h in self.herbivores:
            if h.alive:
                grid[h.y][h.x] = '◙'
                grid_colors[h.y][h.x] = 3

        for pr in self.predators:
            if pr.alive:
                grid[pr.y][pr.x] = '♦'
                grid_colors[pr.y][pr.x] = 4

        return grid, grid_colors


# ─── Curses Renderer ─────────────────────────────────────────────────────────

def draw_population_graph(stdscr, history, start_y, start_x, width, height):
    """Draw an ASCII population graph."""
    if not history["plants"] and not history["herbivores"] and not history["predators"]:
        return

    all_vals = history["plants"] + history["herbivores"] + history["predators"]
    if not all_vals:
        return

    max_val = max(max(all_vals), 1)
    data_len = len(history["plants"])
    graph_height = height - 2
    graph_width = min(width - 2, data_len)

    if graph_height < 1 or graph_width < 1:
        return

    # Draw axes
    stdscr.addch(start_y, start_x, '┌')
    stdscr.addch(start_y + height - 1, start_x, '└')
    for y in range(start_y + 1, start_y + height - 1):
        stdscr.addch(y, start_x, '│')
    for x in range(start_x + 1, start_x + graph_width + 1):
        stdscr.addch(start_y + height - 1, x, '─')
        stdscr.addch(start_y, x, '─')
    stdscr.addch(start_y + height - 1, start_x + graph_width + 1, '┘')
    stdscr.addch(start_y, start_x + graph_width + 1, '┐')

    # Plot each series
    series = [
        ("plants", 2),
        ("herbivores", 3),
        ("predators", 4),
    ]

    for key, color in series:
        data = history[key][-graph_width:]
        for i, val in enumerate(data):
            x = start_x + 1 + i
            if x > start_x + graph_width:
                break
            y_norm = int((val / max_val) * graph_height)
            y = start_y + height - 2 - y_norm
            if start_y + 1 <= y <= start_y + height - 2:
                try:
                    stdscr.addch(y, x, '█', curses.color_pair(color))
                except curses.error:
                    pass


def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()

    # Define color pairs
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)   # default
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)    # plants
    curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)     # herbivores
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)      # predators
    curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # events
    curses.init_pair(6, curses.COLOR_BLUE, curses.COLOR_BLACK)     # season
    curses.init_pair(7, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # title
    curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLUE)     # header

    world = World()

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()

        # Handle input
        key = stdscr.getch()
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord(' '):
            world.paused = not world.paused
        elif key == ord('+') or key == ord('='):
            world.speed = max(1, world.speed - 1)
        elif key == ord('-'):
            world.speed = min(5, world.speed + 1)
        elif key == ord('r') or key == ord('R'):
            world = World()
        elif key == ord('p'):
            # Spawn plants
            for _ in range(10):
                x = random.randint(0, WORLD_WIDTH - 1)
                y = random.randint(0, WORLD_HEIGHT - 1)
                world.plants.append(Plant(x, y))
        elif key == ord('h'):
            # Spawn herbivore at random position
            world.herbivores.append(Herbivore(
                random.randint(0, WORLD_WIDTH - 1),
                random.randint(0, WORLD_HEIGHT - 1)))
        elif key == ord('d'):
            # Spawn predator at random position
            world.predators.append(Predator(
                random.randint(0, WORLD_WIDTH - 1),
                random.randint(0, WORLD_HEIGHT - 1)))

        # ─── Header ───
        header = f" 🌍 ECOSYSTEM SIMULATOR "
        stdscr.addstr(0, 0, header.ljust(max_x), curses.color_pair(8) | curses.A_BOLD)

        # ─── Stats bar ───
        stats_y = 1
        n_plants = len(world.plants)
        n_herbs = len(world.herbivores)
        n_preds = len(world.predators)
        total = n_plants + n_herbs + n_preds

        season_bar = "▓" * world.season_tick + "░" * (SEASON_LENGTH - world.season_tick)

        stats = (
            f" Tick: {world.tick:>5}  │  "
            f"Season: {world.season.label():>7} [{season_bar}]  │  "
            f"Plants: {n_plants:>3}  │  "
            f"Herbivores: {n_herbs:>3}  │  "
            f"Predators: {n_preds:>3}  │  "
            f"Total: {total:>3} "
        )
        stdscr.addstr(stats_y, 0, stats[:max_x], curses.color_pair(1))

        # ─── Events bar ───
        events_y = 2
        if world.events:
            evt_text = f" ⚡ {world.events[-1]}"
            stdscr.addstr(events_y, 0, evt_text[:max_x], curses.color_pair(5))

        # ─── World grid ───
        grid, grid_colors = world.get_grid()
        grid_start_y = 3

        for y in range(min(WORLD_HEIGHT, max_y - grid_start_y - 12)):
            for x in range(min(WORLD_WIDTH, max_x - 1)):
                ch = grid[y][x] if x < WORLD_WIDTH else ' '
                color = grid_colors[y][x] if x < WORLD_WIDTH else 0
                try:
                    stdscr.addch(grid_start_y + y, x, ch, curses.color_pair(color))
                except curses.error:
                    pass

        # ─── Population graph ───
        graph_y = grid_start_y + min(WORLD_HEIGHT, max_y - grid_start_y - 12) + 1
        graph_x = 1
        graph_w = min(60, max_x - 2)
        graph_h = min(8, max_y - graph_y - 4)

        if graph_h >= 3 and graph_w >= 10:
            stdscr.addstr(graph_y, 0, " Population Dynamics:", curses.color_pair(7) | curses.A_BOLD)
            draw_population_graph(stdscr, world.history,
                                  graph_y + 1, graph_x, graph_w, graph_h)

        # ─── Legend / Controls ───
        ctrl_y = max(graph_y + graph_h + 2, max_y - 4)
        legend = (
            f" ♣=Plant  ◙=Herbivore  ♦=Predator  │  "
            f"[SPACE]=Pause  [+/-]=Speed  [p/h/d]=Spawn  [R]=Reset  [Q]=Quit"
        )
        try:
            stdscr.addstr(ctrl_y, 0, legend[:max_x], curses.color_pair(1))
        except curses.error:
            pass

        # Paused indicator
        if world.paused:
            pause_text = " ⏸ PAUSED "
            px = max_x // 2 - len(pause_text) // 2
            py = max_y // 2
            try:
                stdscr.addstr(py, px, pause_text, curses.color_pair(5) | curses.A_BOLD)
            except curses.error:
                pass

        stdscr.refresh()

        # Update simulation
        world.update()

        # Delay
        delay = TICK_DELAY * world.speed
        time.sleep(delay)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\nEcosystem simulation ended.")