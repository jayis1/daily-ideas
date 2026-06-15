#!/usr/bin/env python3
"""
ASCII Ecosystem Simulator
==========================
A terminal-based ecosystem simulation with multiple species,
population dynamics, food chains, seasons, water terrain,
and environmental events. Watch plants, herbivores, and predators
interact in real-time.

Usage:
    python3 ecosystem.py                  # Interactive mode (curses)
    python3 ecosystem.py --headless 200   # Run 200 ticks, output CSV
    python3 ecosystem.py --seed 42        # Reproducible simulation
    python3 ecosystem.py --help            # Show all options
"""

import argparse
import csv
import io
import random
import sys
import time
from collections import defaultdict
from enum import Enum

# ─── Configuration ───────────────────────────────────────────────────────────

VERSION = "1.1.0"

WORLD_WIDTH = 80
WORLD_HEIGHT = 40
WATER_RATIO = 0.05           # fraction of map that is water
INITIAL_PLANTS = 60
INITIAL_HERBIVORES = 25
INITIAL_PREDATORS = 8
TICK_DELAY = 0.12

PLANT_SPREAD_CHANCE = 0.06
PLANT_MAX_AGE = 80
PLANT_NUTRITION = 20
PLANT_POP_CAP = 300          # max plants before culling

HERBIVORE_MAX_ENERGY = 100
HERBIVORE_INITIAL_ENERGY = 60
HERBIVORE_MOVE_COST = 2
HERBIVORE_REPRODUCE_THRESHOLD = 65
HERBIVORE_REPRODUCE_COST = 30
HERBIVORE_VISION = 4
HERBIVORE_MAX_AGE = 120
HERBIVORE_POP_CAP = 150      # max herbivores before culling

PREDATOR_MAX_ENERGY = 120
PREDATOR_INITIAL_ENERGY = 80
PREDATOR_MOVE_COST = 3
PREDATOR_REPRODUCE_THRESHOLD = 80
PREDATOR_REPRODUCE_COST = 40
PREDATOR_VISION = 6
PREDATOR_HUNT_NUTRITION = 50
PREDATOR_MAX_AGE = 100
PREDATOR_POP_CAP = 60       # max predators before culling

SEASON_LENGTH = 50           # ticks per season
DISASTER_CHANCE = 0.005      # per tick


# ─── Enums ───────────────────────────────────────────────────────────────────

class Season(Enum):
    SPRING = 0
    SUMMER = 1
    AUTUMN = 2
    WINTER = 3

    def next(self):
        """Advance to the next season in the cycle."""
        return Season((self.value + 1) % 4)

    def emoji(self):
        """Return a Unicode emoji representing this season."""
        return {
            Season.SPRING: "🌱",
            Season.SUMMER: "☀️",
            Season.AUTUMN: "🍂",
            Season.WINTER: "❄️",
        }[self]

    def label(self):
        """Human-readable season name."""
        return self.name.capitalize()

    def plant_spread_modifier(self):
        """Multiplier for plant spread chance in this season."""
        return {
            Season.SPRING: 2.0,
            Season.SUMMER: 1.2,
            Season.AUTUMN: 0.5,
            Season.WINTER: 0.1,
        }[self]


class EventType(Enum):
    DROUGHT = 0
    PLAGUE = 1
    BOUNTY = 2
    STORM = 3
    FLOOD = 4  # NEW: floods create temporary water

    def label(self):
        return self.name.capitalize()

    def desc(self):
        """Return a human-readable description of the event."""
        return {
            EventType.DROUGHT: "Drought! Plants wither...",
            EventType.PLAGUE: "Plague! Creatures fall ill...",
            EventType.BOUNTY: "Bounty! Life flourishes!",
            EventType.STORM: "Storm! Chaos reigns!",
            EventType.FLOOD: "Flood! Water rises!",
        }[self]


# ─── Entities ────────────────────────────────────────────────────────────────

class Entity:
    """Base class for all entities in the simulation."""
    _id_counter = 0

    def __init__(self, x, y):
        Entity._id_counter += 1
        self.id = Entity._id_counter
        self.x = x
        self.y = y
        self.age = 0
        self.alive = True

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, pos=({self.x},{self.y}), age={self.age})"


class Plant(Entity):
    """A plant entity that grows, spreads, and provides nutrition to herbivores."""
    char = "♣"
    color_pair = 2  # green

    def __init__(self, x, y, maturity=0):
        super().__init__(x, y)
        self.nutrition = PLANT_NUTRITION
        self.maturity = maturity  # grows over time

    def update(self, season, rng=random):
        """Age the plant, apply seasonal effects, and check for death."""
        self.age += 1
        self.maturity = min(self.maturity + 1, 5)

        # Seasonal effects on aging
        if season == Season.WINTER:
            if rng.random() < 0.03:
                self.alive = False
        elif season == Season.AUTUMN:
            if rng.random() < 0.01:
                self.alive = False
        elif season == Season.SPRING:
            self.nutrition = min(self.nutrition + 2, PLANT_NUTRITION + 5)

        if self.age > PLANT_MAX_AGE:
            self.alive = False

    def try_spread(self, world, rng=random):
        """Attempt to spread to an adjacent cell. Returns a new Plant or None."""
        if self.maturity < 3:
            return None
        chance = PLANT_SPREAD_CHANCE * world.season.plant_spread_modifier()
        if rng.random() < chance:
            dx, dy = rng.choice(
                [(0, 1), (0, -1), (1, 0), (-1, 0),
                 (1, 1), (-1, -1), (1, -1), (-1, 1)]
            )
            nx = (self.x + dx) % world.width
            ny = (self.y + dy) % world.height
            if not world.is_water(nx, ny) and not world.get_entity_at(nx, ny):
                return Plant(nx, ny)
        return None


class Herbivore(Entity):
    """A herbivore entity that seeks plants, flees predators, and reproduces."""
    char = "◙"
    color_pair = 3  # cyan

    def __init__(self, x, y, energy=None):
        super().__init__(x, y)
        self.energy = energy if energy is not None else HERBIVORE_INITIAL_ENERGY
        self.direction = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])

    def update(self, world, rng=random):
        """Move, eat, flee, and check for death."""
        self.age += 1
        self.energy -= HERBIVORE_MOVE_COST

        # Seasonal energy drain
        if world.season == Season.WINTER:
            self.energy -= 1
        if world.season == Season.SUMMER:
            self.energy += 0.5  # slight recovery in summer

        if self.energy <= 0 or self.age > HERBIVORE_MAX_AGE:
            self.alive = False
            return

        # Flee from predators (higher priority than eating)
        predator = self._find_predator(world)
        if predator:
            self._move_away(predator.x, predator.y, world)
            return  # spent this tick fleeing

        # Seek nearby plant
        target = self._find_plant(world, rng)
        if target:
            self._move_toward(target.x, target.y, world)
            if abs(self.x - target.x) <= 1 and abs(self.y - target.y) <= 1:
                self.energy = min(
                    self.energy + target.nutrition, HERBIVORE_MAX_ENERGY
                )
                target.alive = False
        else:
            # Random wandering
            if rng.random() < 0.3:
                self.direction = rng.choice(
                    [(0, 1), (0, -1), (1, 0), (-1, 0)]
                )
            dx, dy = self.direction
            nx = (self.x + dx) % world.width
            ny = (self.y + dy) % world.height
            if not world.is_water(nx, ny):
                self.x = nx
                self.y = ny

        # Flee from predators after moving
        predator = self._find_predator(world)
        if predator:
            self._move_away(predator.x, predator.y, world)

    def _find_plant(self, world, rng=random):
        """Find the nearest visible plant within vision range."""
        best = None
        best_dist = float("inf")
        for p in world.plants:
            if not p.alive:
                continue
            dist = abs(p.x - self.x) + abs(p.y - self.y)
            if dist <= HERBIVORE_VISION and dist < best_dist:
                best = p
                best_dist = dist
        return best

    def _find_predator(self, world):
        """Find the nearest predator within flee range."""
        for pr in world.predators:
            if not pr.alive:
                continue
            dist = abs(pr.x - self.x) + abs(pr.y - self.y)
            if dist <= 3:
                return pr
        return None

    def _move_toward(self, tx, ty, world):
        """Move one step toward target, respecting world wrapping and water."""
        dx = 0 if tx == self.x else (1 if tx > self.x else -1)
        dy = 0 if ty == self.y else (1 if ty > self.y else -1)
        # Handle wrapping
        if abs(tx - self.x) > world.width // 2:
            dx = -dx
        if abs(ty - self.y) > world.height // 2:
            dy = -dy
        nx = (self.x + dx) % world.width
        ny = (self.y + dy) % world.height
        if not world.is_water(nx, ny):
            self.x = nx
            self.y = ny
        else:
            # Try just horizontal or vertical
            nx2 = (self.x + dx) % world.width
            ny2 = self.y
            if not world.is_water(nx2, ny2):
                self.x = nx2
            else:
                nx3 = self.x
                ny3 = (self.y + dy) % world.height
                if not world.is_water(nx3, ny3):
                    self.y = ny3

    def _move_away(self, tx, ty, world):
        """Move one step away from a threat, respecting water."""
        dx = 0 if tx == self.x else (-1 if tx > self.x else 1)
        dy = 0 if ty == self.y else (-1 if ty > self.y else 1)
        nx = (self.x + dx) % world.width
        ny = (self.y + dy) % world.height
        if not world.is_water(nx, ny):
            self.x = nx
            self.y = ny

    def can_reproduce(self, rng=random):
        """Check whether this herbivore can reproduce this tick."""
        return (
            self.alive
            and self.energy >= HERBIVORE_REPRODUCE_THRESHOLD
            and self.age > 10
            and rng.random() < 0.15
        )

    def reproduce(self, world, rng=random):
        """Create a baby herbivore in an adjacent cell."""
        self.energy -= HERBIVORE_REPRODUCE_COST
        dx, dy = rng.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
        nx = (self.x + dx) % world.width
        ny = (self.y + dy) % world.height
        baby = Herbivore(nx, ny, energy=40)
        return baby


class Predator(Entity):
    """A predator entity that hunts herbivores, wanders, and reproduces."""
    char = "♦"
    color_pair = 4  # red

    def __init__(self, x, y, energy=None):
        super().__init__(x, y)
        self.energy = energy if energy is not None else PREDATOR_INITIAL_ENERGY
        self.direction = random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
        self.hunt_cooldown = 0

    def update(self, world, rng=random):
        """Hunt, move, and check for death."""
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
            self._move_toward(target.x, target.y, world)
            dist = abs(self.x - target.x) + abs(self.y - target.y)
            if dist <= 1 and self.hunt_cooldown == 0:
                self.energy = min(
                    self.energy + PREDATOR_HUNT_NUTRITION, PREDATOR_MAX_ENERGY
                )
                target.alive = False
                world.death_log.append(
                    f"Tick {world.tick}: Predator #{self.id} caught "
                    f"Herbivore #{target.id}"
                )
                self.hunt_cooldown = 3
        else:
            # Wander
            if rng.random() < 0.4:
                self.direction = rng.choice(
                    [(0, 1), (0, -1), (1, 0), (-1, 0)]
                )
            dx, dy = self.direction
            nx = (self.x + dx) % world.width
            ny = (self.y + dy) % world.height
            if not world.is_water(nx, ny):
                self.x = nx
                self.y = ny

    def _find_herbivore(self, world):
        """Find the nearest visible herbivore within vision range."""
        best = None
        best_dist = float("inf")
        for h in world.herbivores:
            if not h.alive:
                continue
            dist = abs(h.x - self.x) + abs(h.y - self.y)
            if dist <= PREDATOR_VISION and dist < best_dist:
                best = h
                best_dist = dist
        return best

    def _move_toward(self, tx, ty, world):
        """Move one step toward target, respecting wrapping and water."""
        dx = 0 if tx == self.x else (1 if tx > self.x else -1)
        dy = 0 if ty == self.y else (1 if ty > self.y else -1)
        if abs(tx - self.x) > world.width // 2:
            dx = -dx
        if abs(ty - self.y) > world.height // 2:
            dy = -dy
        nx = (self.x + dx) % world.width
        ny = (self.y + dy) % world.height
        if not world.is_water(nx, ny):
            self.x = nx
            self.y = ny
        else:
            # Try axes independently
            nx2 = (self.x + dx) % world.width
            if not world.is_water(nx2, self.y):
                self.x = nx2
            else:
                ny2 = (self.y + dy) % world.height
                if not world.is_water(self.x, ny2):
                    self.y = ny2

    def can_reproduce(self, rng=random):
        """Check whether this predator can reproduce this tick."""
        return (
            self.alive
            and self.energy >= PREDATOR_REPRODUCE_THRESHOLD
            and self.age > 15
            and rng.random() < 0.08
        )

    def reproduce(self, world, rng=random):
        """Create a baby predator in an adjacent cell."""
        self.energy -= PREDATOR_REPRODUCE_COST
        dx, dy = rng.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])
        nx = (self.x + dx) % world.width
        ny = (self.y + dy) % world.height
        baby = Predator(nx, ny, energy=50)
        return baby


# ─── World ────────────────────────────────────────────────────────────────────

class World:
    """
    The simulation world containing all entities, terrain, and state.

    Parameters
    ----------
    width : int
        Width of the world grid.
    height : int
        Height of the world grid.
    initial_plants : int
        Number of plants to spawn at start.
    initial_herbivores : int
        Number of herbivores to spawn at start.
    initial_predators : int
        Number of predators to spawn at start.
    seed : int or None
        Random seed for reproducibility.
    water_ratio : float
        Fraction of cells that are water (impassable).
    """

    def __init__(
        self,
        width=WORLD_WIDTH,
        height=WORLD_HEIGHT,
        initial_plants=INITIAL_PLANTS,
        initial_herbivores=INITIAL_HERBIVORES,
        initial_predators=INITIAL_PREDATORS,
        seed=None,
        water_ratio=WATER_RATIO,
    ):
        self.rng = random.Random(seed)
        self.width = width
        self.height = height
        self.tick = 0
        self.season = Season.SPRING
        self.season_tick = 0
        self.plants = []
        self.herbivores = []
        self.predators = []
        self.events = []
        self.death_log = []  # NEW: track notable deaths
        self.history = {"plants": [], "herbivores": [], "predators": []}
        self.paused = False
        self.speed = 1

        # Generate water terrain
        self.water = set()
        num_water = int(width * height * water_ratio)
        attempts = 0
        while len(self.water) < num_water and attempts < num_water * 10:
            wx = self.rng.randint(0, width - 1)
            wy = self.rng.randint(0, height - 1)
            self.water.add((wx, wy))
            attempts += 1

        # Spawn initial entities on land
        for _ in range(initial_plants):
            x, y = self._random_land()
            p = Plant(x, y)
            p.maturity = self.rng.randint(1, 5)
            p.age = self.rng.randint(0, 30)
            self.plants.append(p)

        for _ in range(initial_herbivores):
            x, y = self._random_land()
            self.herbivores.append(Herbivore(x, y))

        for _ in range(initial_predators):
            x, y = self._random_land()
            self.predators.append(Predator(x, y))

    def _random_land(self):
        """Return a random (x, y) position that is not water."""
        while True:
            x = self.rng.randint(0, self.width - 1)
            y = self.rng.randint(0, self.height - 1)
            if (x, y) not in self.water:
                return x, y

    def is_water(self, x, y):
        """Check whether a cell is water."""
        return (x, y) in self.water

    def get_entity_at(self, x, y):
        """Find the topmost entity at a given grid position (plants < herbivores < predators)."""
        for pr in self.predators:
            if pr.alive and pr.x == x and pr.y == y:
                return pr
        for h in self.herbivores:
            if h.alive and h.x == x and h.y == y:
                return h
        for p in self.plants:
            if p.alive and p.x == x and p.y == y:
                return p
        return None

    def update(self):
        """Advance the simulation by one tick."""
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
        if self.rng.random() < DISASTER_CHANCE:
            self._trigger_event()

        # Update plants
        new_plants = []
        for p in self.plants:
            if p.alive:
                p.update(self.season, self.rng)
                baby = p.try_spread(self, self.rng)
                if baby:
                    new_plants.append(baby)
        self.plants = [p for p in self.plants if p.alive] + new_plants

        # Cap plants to prevent runaway
        if len(self.plants) > PLANT_POP_CAP:
            self.rng.shuffle(self.plants)
            for p in self.plants[PLANT_POP_CAP:]:
                p.alive = False
            self.plants = self.plants[:PLANT_POP_CAP]

        # Update herbivores
        new_herbivores = []
        for h in self.herbivores:
            if h.alive:
                h.update(self, self.rng)
                if h.can_reproduce(self.rng):
                    baby = h.reproduce(self, self.rng)
                    new_herbivores.append(baby)
        self.herbivores = [h for h in self.herbivores if h.alive] + new_herbivores

        # Cap herbivores
        if len(self.herbivores) > HERBIVORE_POP_CAP:
            self.rng.shuffle(self.herbivores)
            for h in self.herbivores[HERBIVORE_POP_CAP:]:
                h.alive = False
            self.herbivores = self.herbivores[:HERBIVORE_POP_CAP]

        # Update predators
        new_predators = []
        for pr in self.predators:
            if pr.alive:
                pr.update(self, self.rng)
                if pr.can_reproduce(self.rng):
                    baby = pr.reproduce(self, self.rng)
                    new_predators.append(baby)
        self.predators = [pr for pr in self.predators if pr.alive] + new_predators

        # Cap predators
        if len(self.predators) > PREDATOR_POP_CAP:
            self.rng.shuffle(self.predators)
            for pr in self.predators[PREDATOR_POP_CAP:]:
                pr.alive = False
            self.predators = self.predators[:PREDATOR_POP_CAP]

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

        # Keep death log short
        if len(self.death_log) > 10:
            self.death_log = self.death_log[-10:]

        # Ecosystem stabilization: respawn if species go extinct
        if len(self.plants) < 5 and self.tick % 10 == 0:
            for _ in range(10):
                x, y = self._random_land()
                self.plants.append(Plant(x, y))

        if (
            len(self.herbivores) == 0
            and self.tick % 20 == 0
            and len(self.plants) > 10
        ):
            for _ in range(3):
                x, y = self._random_land()
                h = Herbivore(x, y, energy=HERBIVORE_MAX_ENERGY)
                self.herbivores.append(h)
            self.events.append("Herbivores migrated into the area!")

        if (
            len(self.predators) == 0
            and len(self.herbivores) > 5
            and self.tick % 30 == 0
        ):
            for _ in range(2):
                x, y = self._random_land()
                pr = Predator(x, y, energy=PREDATOR_MAX_ENERGY)
                self.predators.append(pr)
            self.events.append("Predators migrated into the area!")

    def _trigger_event(self):
        """Trigger a random environmental event."""
        event = self.rng.choice(list(EventType))
        self.events.append(event.desc())

        if event == EventType.DROUGHT:
            # Kill 30% of plants
            n = min(len(self.plants), max(1, len(self.plants) // 3))
            for p in self.rng.sample(self.plants, n):
                p.alive = False
        elif event == EventType.PLAGUE:
            # Kill 20% of herbivores and predators
            if self.herbivores:
                n = max(1, len(self.herbivores) // 5)
                for h in self.rng.sample(
                    self.herbivores, min(len(self.herbivores), n)
                ):
                    h.alive = False
            if self.predators:
                n = max(1, len(self.predators) // 5)
                for pr in self.rng.sample(
                    self.predators, min(len(self.predators), n)
                ):
                    pr.alive = False
        elif event == EventType.BOUNTY:
            # Spawn new plants on land
            for _ in range(30):
                x, y = self._random_land()
                p = Plant(x, y, maturity=5)
                self.plants.append(p)
        elif event == EventType.STORM:
            # Scatter all creatures randomly
            for h in self.herbivores:
                h.x, h.y = self._random_land()
            for pr in self.predators:
                pr.x, pr.y = self._random_land()
        elif event == EventType.FLOOD:
            # Add temporary water cells and scatter creatures
            for _ in range(5):
                wx = self.rng.randint(0, self.width - 1)
                wy = self.rng.randint(0, self.height - 1)
                self.water.add((wx, wy))
            # Remove some water cells to keep it balanced
            if len(self.water) > int(self.width * self.height * WATER_RATIO) + 20:
                for _ in range(5):
                    if self.water:
                        self.water.discard(self.rng.choice(list(self.water)))

    def get_grid(self):
        """Build a character grid and color grid of the world for rendering."""
        grid = [
            [" " for _ in range(self.width)] for _ in range(self.height)
        ]
        grid_colors = [
            [0 for _ in range(self.width)] for _ in range(self.height)
        ]

        # Draw water
        for wx, wy in self.water:
            if 0 <= wy < self.height and 0 <= wx < self.width:
                grid[wy][wx] = "~"
                grid_colors[wy][wx] = 6  # blue for water

        # Draw plants
        for p in self.plants:
            if p.alive and 0 <= p.y < self.height and 0 <= p.x < self.width:
                chars = {0: "·", 1: "·", 2: "∘", 3: "♣", 4: "♣", 5: "♠"}
                grid[p.y][p.x] = chars.get(p.maturity, "♣")
                grid_colors[p.y][p.x] = 2  # green

        # Draw herbivores (on top of plants)
        for h in self.herbivores:
            if h.alive and 0 <= h.y < self.height and 0 <= h.x < self.width:
                grid[h.y][h.x] = "◙"
                grid_colors[h.y][h.x] = 3  # cyan

        # Draw predators (on top of everything)
        for pr in self.predators:
            if pr.alive and 0 <= pr.y < self.height and 0 <= pr.x < self.width:
                grid[pr.y][pr.x] = "♦"
                grid_colors[pr.y][pr.x] = 4  # red

        return grid, grid_colors

    def avg_energy(self, species):
        """Return the average energy of a species list, or 0 if empty."""
        alive = [e for e in species if e.alive]
        if not alive:
            return 0.0
        return sum(e.energy for e in alive) / len(alive)


# ─── Headless Mode ───────────────────────────────────────────────────────────

def run_headless(world, ticks, output_format="csv"):
    """
    Run the simulation without curses and output population data.

    Parameters
    ----------
    world : World
        The simulation world to run.
    ticks : int
        Number of ticks to simulate.
    output_format : str
        'csv' or 'json' for output format.

    Returns
    -------
    str
        The formatted output string.
    """
    records = []
    for t in range(1, ticks + 1):
        world.update()
        record = {
            "tick": world.tick,
            "season": world.season.label(),
            "plants": len(world.plants),
            "herbivores": len(world.herbivores),
            "predators": len(world.predators),
            "avg_herb_energy": round(world.avg_energy(world.herbivores), 1),
            "avg_pred_energy": round(world.avg_energy(world.predators), 1),
            "events": "; ".join(world.events) if world.events else "",
        }
        records.append(record)

    if output_format == "json":
        import json
        return json.dumps(records, indent=2)
    else:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
        return buf.getvalue()


# ─── Curses Renderer ─────────────────────────────────────────────────────────

def draw_population_graph(stdscr, history, start_y, start_x, width, height):
    """Draw an ASCII population graph in the curses window."""
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
    try:
        stdscr.addch(start_y, start_x, "┌")
        stdscr.addch(start_y + height - 1, start_x, "└")
        for y in range(start_y + 1, start_y + height - 1):
            stdscr.addch(y, start_x, "│")
        for x in range(start_x + 1, start_x + graph_width + 1):
            stdscr.addch(start_y + height - 1, x, "─")
            stdscr.addch(start_y, x, "─")
        stdscr.addch(start_y + height - 1, start_x + graph_width + 1, "┘")
        stdscr.addch(start_y, start_x + graph_width + 1, "┐")
    except curses.error:
        pass

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
                    stdscr.addch(y, x, "█", curses.color_pair(color))
                except curses.error:
                    pass


def main(stdscr, world):
    """Main curses interactive loop."""
    import curses

    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()

    # Define color pairs
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)    # default
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)     # plants
    curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)     # herbivores
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)      # predators
    curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # events
    curses.init_pair(6, curses.COLOR_BLUE, curses.COLOR_BLACK)     # water/season
    curses.init_pair(7, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # title
    curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLUE)     # header

    # Follow mode state
    follow_entity = None
    follow_type = None  # 'herbivore' or 'predator'

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()

        # Handle input
        key = stdscr.getch()
        if key == ord("q") or key == ord("Q"):
            break
        elif key == ord(" "):
            world.paused = not world.paused
        elif key == ord("+") or key == ord("="):
            world.speed = max(1, world.speed - 1)
        elif key == ord("-"):
            world.speed = min(5, world.speed + 1)
        elif key == ord("r") or key == ord("R"):
            world = World(
                width=world.width, height=world.height, seed=None,
                water_ratio=WATER_RATIO,
            )
            follow_entity = None
            follow_type = None
        elif key == ord("p"):
            # Spawn plants on land
            for _ in range(10):
                x, y = world._random_land()
                world.plants.append(Plant(x, y))
        elif key == ord("h"):
            x, y = world._random_land()
            world.herbivores.append(Herbivore(x, y))
        elif key == ord("d"):
            x, y = world._random_land()
            world.predators.append(Predator(x, y))
        elif key == ord("f"):
            # Toggle follow mode: cycle through herbivore -> predator -> off
            if follow_type is None:
                follow_type = "herbivore"
            elif follow_type == "herbivore":
                follow_type = "predator"
            else:
                follow_type = None
                follow_entity = None
            # Pick an entity to follow
            if follow_type == "herbivore" and world.herbivores:
                follow_entity = world.rng.choice(world.herbivores)
            elif follow_type == "predator" and world.predators:
                follow_entity = world.rng.choice(world.predators)
            else:
                follow_entity = None
                follow_type = None
        elif key == ord("e"):
            # Trigger a random event
            world._trigger_event()

        # Validate follow entity still alive
        if follow_entity and not follow_entity.alive:
            follow_entity = None
            follow_type = None

        # ─── Header ───
        header = f" 🌍 ECOSYSTEM SIMULATOR v{VERSION} "
        stdscr.addstr(
            0, 0, header.ljust(max_x), curses.color_pair(8) | curses.A_BOLD
        )

        # ─── Stats bar ───
        stats_y = 1
        n_plants = len(world.plants)
        n_herbs = len(world.herbivores)
        n_preds = len(world.predators)
        total = n_plants + n_herbs + n_preds

        avg_herb_e = world.avg_energy(world.herbivores)
        avg_pred_e = world.avg_energy(world.predators)

        season_bar = "▓" * world.season_tick + "░" * (
            SEASON_LENGTH - world.season_tick
        )

        stats = (
            f" Tick:{world.tick:>5} │ "
            f"{world.season.label():>7} [{season_bar}] │ "
            f"♣{n_plants:>3} ◙{n_herbs:>3}(E{avg_herb_e:.0f}) "
            f"♦{n_preds:>3}(E{avg_pred_e:.0f}) │ "
            f"Total:{total:>3} "
            f"Speed:{world.speed}x"
        )
        try:
            stdscr.addstr(stats_y, 0, stats[:max_x], curses.color_pair(1))
        except curses.error:
            pass

        # ─── Events bar ───
        events_y = 2
        if world.events:
            evt_text = f" ⚡ {world.events[-1]}"
            try:
                stdscr.addstr(
                    events_y, 0, evt_text[:max_x], curses.color_pair(5)
                )
            except curses.error:
                pass

        # ─── World grid ───
        grid, grid_colors = world.get_grid()
        grid_start_y = 3

        # Compute visible area, centered on follow entity if active
        view_offset_x = 0
        view_offset_y = 0
        visible_width = min(world.width, max_x - 1)
        visible_height = min(world.height, max_y - grid_start_y - 14)

        if follow_entity and follow_entity.alive:
            # Center view on followed entity
            cx = follow_entity.x - visible_width // 2
            cy = follow_entity.y - visible_height // 2
            view_offset_x = max(0, min(cx, world.width - visible_width))
            view_offset_y = max(0, min(cy, world.height - visible_height))

        for y in range(visible_height):
            for x in range(visible_width):
                wx = x + view_offset_x
                wy = y + view_offset_y
                if wx < world.width and wy < world.height:
                    ch = grid[wy][wx]
                    color = grid_colors[wy][wx]
                else:
                    ch = " "
                    color = 0
                # Highlight followed entity
                if (
                    follow_entity
                    and follow_entity.alive
                    and wx == follow_entity.x
                    and wy == follow_entity.y
                ):
                    try:
                        stdscr.addch(
                            grid_start_y + y,
                            x,
                            ch,
                            curses.color_pair(color) | curses.A_REVERSE,
                        )
                    except curses.error:
                        pass
                else:
                    try:
                        stdscr.addch(
                            grid_start_y + y, x, ch, curses.color_pair(color)
                        )
                    except curses.error:
                        pass

        # ─── Follow info ───
        info_y = grid_start_y + visible_height + 1
        if follow_entity and follow_entity.alive:
            e = follow_entity
            info = (
                f" Following {e.__class__.__name__} #{e.id}: "
                f"pos=({e.x},{e.y}) age={e.age} energy={e.energy:.0f}"
            )
            try:
                stdscr.addstr(
                    info_y, 0, info[:max_x], curses.color_pair(5) | curses.A_BOLD
                )
            except curses.error:
                pass
            info_y += 1

        # ─── Population graph ───
        graph_y = info_y
        graph_x = 1
        graph_w = min(60, max_x - 2)
        graph_h = min(8, max_y - graph_y - 4)

        if graph_h >= 3 and graph_w >= 10:
            try:
                stdscr.addstr(
                    graph_y,
                    0,
                    " Population Dynamics:",
                    curses.color_pair(7) | curses.A_BOLD,
                )
            except curses.error:
                pass
            draw_population_graph(
                stdscr, world.history, graph_y + 1, graph_x, graph_w, graph_h
            )

        # ─── Legend / Controls ───
        ctrl_y = max(graph_y + graph_h + 2, max_y - 3)
        legend = (
            f" ♣=Plant ◙=Herbivore ♦=Predator ~=Water │ "
            f"[SPACE]=Pause [+/-]=Speed [p/h/d]=Spawn "
            f"[f]=Follow [e]=Event [R]=Reset [Q]=Quit"
        )
        try:
            stdscr.addstr(ctrl_y, 0, legend[:max_x], curses.color_pair(1))
        except curses.error:
            pass

        # Water count
        water_info = f" Water cells: {len(world.water)}"
        try:
            stdscr.addstr(ctrl_y + 1, 0, water_info[:max_x], curses.color_pair(6))
        except curses.error:
            pass

        # Paused indicator
        if world.paused:
            pause_text = " ⏸ PAUSED "
            px = max_x // 2 - len(pause_text) // 2
            py = max_y // 2
            try:
                stdscr.addstr(
                    py, px, pause_text, curses.color_pair(5) | curses.A_BOLD
                )
            except curses.error:
                pass

        stdscr.refresh()

        # Update simulation
        world.update()

        # Delay
        delay = TICK_DELAY * world.speed
        time.sleep(delay)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="ecosystem",
        description=(
            "ASCII Ecosystem Simulator — watch plants, herbivores, and "
            "predators interact in real-time through a terminal interface."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s                      # Interactive mode (curses)\n"
            "  %(prog)s --headless 200       # Run 200 ticks, output CSV\n"
            "  %(prog)s --headless 500 --format json  # Output as JSON\n"
            "  %(prog)s --seed 42             # Reproducible simulation\n"
            "  %(prog)s --width 100 --height 50  # Custom world size\n"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    parser.add_argument(
        "--headless",
        type=int,
        metavar="TICKS",
        default=None,
        help="Run in headless mode for TICKS ticks and output population data",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format for headless mode (default: csv)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible simulations",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=WORLD_WIDTH,
        help=f"World width in cells (default: {WORLD_WIDTH})",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=WORLD_HEIGHT,
        help=f"World height in cells (default: {WORLD_HEIGHT})",
    )
    parser.add_argument(
        "--plants",
        type=int,
        default=INITIAL_PLANTS,
        help=f"Initial number of plants (default: {INITIAL_PLANTS})",
    )
    parser.add_argument(
        "--herbivores",
        type=int,
        default=INITIAL_HERBIVORES,
        help=f"Initial number of herbivores (default: {INITIAL_HERBIVORES})",
    )
    parser.add_argument(
        "--predators",
        type=int,
        default=INITIAL_PREDATORS,
        help=f"Initial number of predators (default: {INITIAL_PREDATORS})",
    )
    parser.add_argument(
        "--water",
        type=float,
        default=WATER_RATIO,
        help=f"Fraction of map that is water (default: {WATER_RATIO})",
    )
    parser.add_argument(
        "--speed",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5],
        help="Initial simulation speed 1-5 (default: 1)",
    )
    return parser.parse_args(argv)


def run_from_args(args):
    """Create a World from parsed CLI arguments."""
    world = World(
        width=args.width,
        height=args.height,
        initial_plants=args.plants,
        initial_herbivores=args.herbivores,
        initial_predators=args.predators,
        seed=args.seed,
        water_ratio=args.water,
    )
    world.speed = args.speed
    return world


if __name__ == "__main__":
    args = parse_args()
    world = run_from_args(args)

    if args.headless:
        output = run_headless(world, args.headless, args.format)
        print(output)
    else:
        try:
            import curses
            curses.wrapper(main, world)
        except KeyboardInterrupt:
            print("\nEcosystem simulation ended.")