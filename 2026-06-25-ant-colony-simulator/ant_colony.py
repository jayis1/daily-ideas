#!/usr/bin/env python3
"""
Terminal Ant Colony Simulator
==============================
An emergent behavior simulation where ants forage for food, leave pheromone
trails, and collectively discover optimal paths — all rendered in the terminal
with colorful ASCII art.

Ants follow simple rules:
  1. Wander randomly when no pheromone is detected
  2. Follow the strongest pheromone trail nearby
  3. When food is found, pick it up and head home, depositing pheromone
  4. Pheromone evaporates over time (diffusion + decay)

The result: ants self-organize into efficient foraging highways!

Enhanced features:
  - Obstacle walls that ants must navigate around
  - Headless batch mode for running simulations without a terminal
  - Shortest-path efficiency tracking
  - Detailed statistics and progress tracking
  - Robust terminal resize handling
  - --version and --help flags
"""

import curses
import random
import math
import argparse
import sys
import json
from collections import defaultdict
from typing import List, Tuple, Optional

# ── Version ────────────────────────────────────────────────────────────────

__version__ = "1.1.1"

# ── Configuration ──────────────────────────────────────────────────────────

NUM_ANTS_DEFAULT = 60
NUM_FOOD_SOURCES = 5
FOOD_PER_SOURCE = 80
EVAPORATION_RATE = 0.995
DIFFUSION_RATE = 0.12
PHEROMONE_DEPOSIT = 40.0
ANT_SENSE_RADIUS = 3
ANT_CARRY_PHEROMONE_BOOST = 2.5
WANDER_STRENGTH = 0.35
FPS = 20
NUM_WALLS_DEFAULT = 3
WALL_LENGTH_RANGE = (5, 15)

# ── Colors ─────────────────────────────────────────────────────────────────

PAIR_EMPTY = 1
PAIR_PHEROMONE_LOW = 2
PAIR_PHEROMONE_MED = 3
PAIR_PHEROMONE_HIGH = 4
PAIR_ANT_SEARCH = 5
PAIR_ANT_CARRY = 6
PAIR_FOOD = 7
PAIR_NEST = 8
PAIR_WALL = 9
PAIR_INFO = 10
PAIR_PHEROMONE_VLOW = 11
PAIR_OBSTACLE = 12

# ── Direction Helpers ──────────────────────────────────────────────────────

DIRS_8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
DIRS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


class Ant:
    """A single ant agent with simple behavioral rules.

    Attributes:
        x: Current x position on the grid.
        y: Current y position on the grid.
        carrying: Whether the ant is carrying food.
        direction: Current movement direction as (dx, dy).
        steps_since_drop: Steps since last food pickup/dropoff (for pheromone fading).
        home_x: Nest x coordinate.
        home_y: Nest y coordinate.
        steps_carrying: Total steps spent carrying food (efficiency metric).
        food_delivered: Number of food units this ant has delivered.
    """

    __slots__ = ('x', 'y', 'carrying', 'direction', 'steps_since_drop',
                 'home_x', 'home_y', 'steps_carrying', 'food_delivered')

    def __init__(self, x: int, y: int, home_x: int, home_y: int):
        self.x = x
        self.y = y
        self.home_x = home_x
        self.home_y = home_y
        self.carrying = False
        self.direction = random.choice(DIRS_8)
        self.steps_since_drop = 0
        self.steps_carrying = 0
        self.food_delivered = 0

    def sense_pheromone(self, grid: List[List[float]], height: int, width: int,
                        sense_forward: bool = True, walls: Optional[set] = None):
        """Sample pheromone in nearby cells, biased toward forward movement.

        Args:
            grid: The pheromone grid.
            height: Grid height.
            width: Grid width.
            sense_forward: If True, bias toward current heading.
            walls: Set of (x, y) wall positions to avoid.

        Returns:
            Tuple of (best_direction, best_value, all_candidates).
        """
        best_val = 0.0
        best_dir = None
        candidates = []

        for dx, dy in DIRS_8:
            nx, ny = self.x + dx, self.y + dy
            # Skip out-of-bounds or wall cells
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if walls and (nx, ny) in walls:
                continue

            val = grid[ny][nx]
            # Bias: forward directions get a bonus
            if sense_forward:
                fwd = (dx * self.direction[0] + dy * self.direction[1])
                val *= (1.0 + fwd * 0.5)
            candidates.append((dx, dy, val, nx, ny))
            if val > best_val:
                best_val = val
                best_dir = (dx, dy)

        return best_dir, best_val, candidates

    def choose_direction(self, grid: List[List[float]], height: int, width: int,
                         walls: Optional[set] = None):
        """Pick next direction based on state and pheromone sensing.

        Args:
            grid: The pheromone grid.
            height: Grid height.
            width: Grid width.
            walls: Set of (x, y) wall positions to avoid.

        Returns:
            A (dx, dy) direction tuple.
        """
        if self.carrying:
            # Head home — use pheromone trail if available, otherwise go toward nest
            best_dir, best_val, candidates = self.sense_pheromone(
                grid, height, width, sense_forward=True, walls=walls)

            # Also consider direct path home
            dx_home = self.home_x - self.x
            dy_home = self.home_y - self.y
            dist_home = math.sqrt(dx_home**2 + dy_home**2) + 1e-6
            dx_home /= dist_home
            dy_home /= dist_home

            # Score candidates by home direction + pheromone
            best_score = -1
            best_move = None
            for ddx, ddy, pval, nx, ny in candidates:
                home_dot = ddx * dx_home + ddy * dy_home
                score = home_dot * 2.0 + (pval / (PHEROMONE_DEPOSIT + 1)) * 3.0
                if score > best_score:
                    best_score = score
                    best_move = (ddx, ddy)

            if best_move:
                return best_move
            return self.direction
        else:
            # Searching for food — follow pheromone trails
            best_dir, best_val, candidates = self.sense_pheromone(
                grid, height, width, sense_forward=True, walls=walls)

            if best_val > 1.0 and best_dir is not None:
                # Strong pheromone — follow it with some randomness
                if random.random() < 0.85:
                    return best_dir
                else:
                    # Random walk, but avoid walls
                    return _random_valid_direction(self, walls, width, height)
            else:
                # Weak/no pheromone — wander with forward momentum
                if random.random() < WANDER_STRENGTH:
                    # Check if current direction is valid (no wall ahead)
                    nx = self.x + self.direction[0]
                    ny = self.y + self.direction[1]
                    if (0 <= nx < width and 0 <= ny < height and
                            (not walls or (nx, ny) not in walls)):
                        return self.direction
                    else:
                        return _random_valid_direction(self, walls, width, height)
                else:
                    return _random_valid_direction(self, walls, width, height)


def _random_valid_direction(ant: Ant, walls: Optional[set], width: int, height: int):
    """Return a random direction that doesn't immediately hit a wall or boundary.

    Falls back to a random DIRS_8 direction if all directions are blocked.
    """
    shuffled = list(DIRS_8)
    random.shuffle(shuffled)
    for dx, dy in shuffled:
        nx, ny = ant.x + dx, ant.y + dy
        if (0 <= nx < width and 0 <= ny < height and
                (not walls or (nx, ny) not in walls)):
            return (dx, dy)
    # Completely surrounded — return current direction as fallback
    return ant.direction


class FoodSource:
    """A food source at a position with remaining quantity.

    Attributes:
        x: X coordinate of the food source center.
        y: Y coordinate of the food source center.
        amount: Remaining food units at this source.
        initial_amount: Starting food units (for statistics).
    """

    __slots__ = ('x', 'y', 'amount', 'initial_amount')

    def __init__(self, x: int, y: int, amount: int):
        self.x = x
        self.y = y
        self.amount = amount
        self.initial_amount = amount


class AntColonySimulation:
    """Main simulation engine for the ant colony foraging model.

    Manages the pheromone grid, food grid, wall obstacles, and all ant agents.
    Provides step-by-step simulation advancement and statistics tracking.

    Args:
        width: Width of the simulation grid.
        height: Height of the simulation grid.
        num_ants: Number of ant agents to create.
        num_walls: Number of random wall obstacles to place.
        evaporation_rate: Pheromone evaporation multiplier per tick (0-1).
        diffusion_rate: Fraction of pheromone that diffuses to neighbors per tick.
        pheromone_deposit: Base pheromone deposit per ant step.
        seed: Optional random seed for reproducibility.
    """

    def __init__(self, width: int, height: int, num_ants: int = NUM_ANTS_DEFAULT,
                 num_walls: int = NUM_WALLS_DEFAULT,
                 evaporation_rate: float = EVAPORATION_RATE,
                 diffusion_rate: float = DIFFUSION_RATE,
                 pheromone_deposit: float = PHEROMONE_DEPOSIT,
                 seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

        if width < 20 or height < 10:
            raise ValueError(f"Grid too small: {width}x{height}. Minimum is 20x10.")
        if num_ants < 1:
            raise ValueError(f"Need at least 1 ant, got {num_ants}.")
        if not (0.0 < evaporation_rate <= 1.0):
            raise ValueError(f"Evaporation rate must be between 0 and 1, got {evaporation_rate}.")
        if not (0.0 <= diffusion_rate <= 1.0):
            raise ValueError(f"Diffusion rate must be between 0 and 1, got {diffusion_rate}.")

        self.width = width
        self.height = height
        self.num_ants = num_ants
        self.evaporation_rate = evaporation_rate
        self.diffusion_rate = diffusion_rate
        self.pheromone_deposit = pheromone_deposit

        # Nest position (center-ish)
        self.nest_x = width // 2
        self.nest_y = height // 2

        # Pheromone grid (float)
        self.pheromone: List[List[float]] = [[0.0] * width for _ in range(height)]

        # Food grid (int — amount per cell)
        self.food_grid: List[List[int]] = [[0] * width for _ in range(height)]
        self.food_sources: List[FoodSource] = []

        # Wall obstacles (set of (x, y) positions)
        self.walls: set = set()
        self._place_walls(num_walls)

        # Create ants (avoiding walls)
        self.ants: List[Ant] = []
        for _ in range(num_ants):
            ax, ay = self._random_position_near(self.nest_x, self.nest_y, radius=2)
            self.ants.append(Ant(ax, ay, self.nest_x, self.nest_y))

        # Statistics
        self.food_collected = 0
        self.total_food = 0
        self.tick = 0
        self.peak_pheromone = 0.0
        self.food_delivery_times: List[int] = []  # Tick numbers when food was delivered
        self.wall_count = num_walls

        # Place initial pheromone around nest to guide early exploration
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                nx, ny = self.nest_x + dx, self.nest_y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    if (nx, ny) not in self.walls:
                        dist = math.sqrt(dx**2 + dy**2)
                        if dist < 4:
                            self.pheromone[ny][nx] = 15.0 * (1.0 - dist / 4.0)

        # Place food sources (avoiding walls and nest)
        self._place_food()

    def _random_position_near(self, cx: int, cy: int, radius: int = 2) -> Tuple[int, int]:
        """Find a random valid position near (cx, cy) that isn't a wall."""
        for _ in range(100):
            ax = cx + random.randint(-radius, radius)
            ay = cy + random.randint(-radius, radius)
            ax = max(0, min(self.width - 1, ax))
            ay = max(0, min(self.height - 1, ay))
            if (ax, ay) not in self.walls:
                return ax, ay
        # Fallback: just use center clamped
        return max(0, min(self.width - 1, cx)), max(0, min(self.height - 1, cy))

    def _place_walls(self, num_walls: int):
        """Place random wall obstacles as line segments on the grid.

        Walls are horizontal or vertical line segments that ants cannot pass
        through, forcing them to find paths around obstacles.
        """
        if num_walls <= 0:
            return

        for _ in range(num_walls):
            # Ensure grid is large enough for wall placement with margins
            wall_margin = min(5, self.width // 4, self.height // 4)
            if wall_margin < 1 or self.width - wall_margin - 1 <= wall_margin or self.height - wall_margin - 1 <= wall_margin:
                continue  # Grid too small for walls; skip

            # Choose random starting position away from nest
            wx, wy = self.width // 2 + wall_margin, self.height // 2  # safe default
            for _ in range(50):
                wx = random.randint(wall_margin, self.width - wall_margin - 1)
                wy = random.randint(wall_margin, self.height - wall_margin - 1)
                dist = math.sqrt((wx - self.nest_x)**2 + (wy - self.nest_y)**2)
                if dist > min(self.width, self.height) * 0.15:
                    break

            # Choose horizontal or vertical
            if random.random() < 0.5:
                # Horizontal wall
                length = random.randint(*WALL_LENGTH_RANGE)
                for dx in range(length):
                    cell_x = wx + dx
                    if 0 <= cell_x < self.width and 0 <= wy < self.height:
                        # Don't place wall on nest
                        if abs(cell_x - self.nest_x) > 1 or abs(wy - self.nest_y) > 1:
                            self.walls.add((cell_x, wy))
            else:
                # Vertical wall
                length = random.randint(*WALL_LENGTH_RANGE)
                for dy in range(length):
                    cell_y = wy + dy
                    if 0 <= wx < self.width and 0 <= cell_y < self.height:
                        if abs(wx - self.nest_x) > 1 or abs(cell_y - self.nest_y) > 1:
                            self.walls.add((wx, cell_y))

    def _place_food(self):
        """Place food sources around the map, avoiding walls and nest."""
        margin = 4
        for _ in range(NUM_FOOD_SOURCES):
            fx, fy = self.nest_x, self.nest_y
            attempts = 0
            while attempts < 50:
                fx = random.randint(margin, self.width - margin - 1)
                fy = random.randint(margin, self.height - margin - 1)
                # Don't place too close to nest
                dist = math.sqrt((fx - self.nest_x)**2 + (fy - self.nest_y)**2)
                if dist > min(self.width, self.height) * 0.25:
                    # Check that the center cell is not a wall
                    if (fx, fy) not in self.walls:
                        break
                attempts += 1

            amount = FOOD_PER_SOURCE + random.randint(-20, 20)
            self.food_sources.append(FoodSource(fx, fy, amount))

            # Spread food in a small cluster (avoiding walls and nest)
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = fx + dx, fy + dy
                    if (0 <= nx < self.width and 0 <= ny < self.height
                            and (nx, ny) not in self.walls
                            and (abs(nx - self.nest_x) > 1 or abs(ny - self.nest_y) > 1)):
                        cell_amount = max(1, amount // 9)
                        self.food_grid[ny][nx] += cell_amount

            self.total_food += amount

    def _decrement_food_source(self, x: int, y: int):
        """Decrement the amount of the nearest food source when food is picked up.

        Finds the food source closest to (x, y) and decrements its amount by 1.
        This keeps food_source.amount in sync with food_grid.
        """
        if not self.food_sources:
            return
        # Find the closest food source to this position
        closest = min(self.food_sources,
                     key=lambda f: (f.x - x) ** 2 + (f.y - y) ** 2)
        if closest.amount > 0:
            closest.amount -= 1

    def step(self):
        """Advance simulation by one tick.

        Evaporates pheromones, then updates all ant positions and states.
        Removes depleted food sources and updates statistics.
        """
        self.tick += 1

        # Evaporate and diffuse pheromones
        self._evaporate_pheromones()

        # Update each ant
        for ant in self.ants:
            self._update_ant(ant)

        # Remove depleted food sources
        self.food_sources = [f for f in self.food_sources if f.amount > 0]

        # Track peak pheromone level
        if self.pheromone:
            current_max = max(max(row) for row in self.pheromone)
            self.peak_pheromone = max(self.peak_pheromone, current_max)

    def _evaporate_pheromones(self):
        """Apply evaporation and diffusion to pheromone grid.

        Each cell's pheromone value is:
        1. Reduced by evaporation rate
        2. A fraction diffuses to 4-connected neighbors
        """
        new_grid = [[0.0] * self.width for _ in range(self.height)]

        # Pheromone cap to prevent runaway growth
        max_pheromone = PHEROMONE_DEPOSIT * ANT_CARRY_PHEROMONE_BOOST * 20.0

        for y in range(self.height):
            for x in range(self.width):
                # Wall cells never have pheromone
                if (x, y) in self.walls:
                    new_grid[y][x] = 0.0
                    continue

                val = self.pheromone[y][x]
                if val < 0.01:
                    new_grid[y][x] = 0.0
                    continue

                # Diffusion: spread to neighbors
                diffused = val * self.diffusion_rate
                kept = val * (1.0 - self.diffusion_rate) * self.evaporation_rate

                # Cap kept pheromone
                kept = min(kept, max_pheromone)
                new_grid[y][x] += kept

                for dx, dy in DIRS_4:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        # Do not diffuse into wall cells
                        if (nx, ny) not in self.walls:
                            new_grid[ny][nx] += diffused / 4.0

        self.pheromone = new_grid

    def _update_ant(self, ant: Ant):
        """Update a single ant's state for one tick.

        Handles food pickup, food delivery at nest, movement, and
        pheromone deposition.
        """
        # Check if ant is at nest and carrying — drop food
        if ant.carrying:
            dist_to_nest = math.sqrt((ant.x - ant.home_x)**2 + (ant.y - ant.home_y)**2)
            if dist_to_nest < 2.0:
                ant.carrying = False
                self.food_collected += 1
                ant.steps_since_drop = 0
                ant.food_delivered += 1
                self.food_delivery_times.append(self.tick)

            # Check if ant is on food and not carrying — pick up food
        # Skip pickup on nest cell to prevent immediate re-pickup after delivery
        on_nest = (abs(ant.x - ant.home_x) <= 1 and abs(ant.y - ant.home_y) <= 1)
        if not ant.carrying and self.food_grid[ant.y][ant.x] > 0 and not on_nest:
            ant.carrying = True
            self.food_grid[ant.y][ant.x] -= 1
            ant.steps_since_drop = 0
            # Decrement the nearest food source's amount
            self._decrement_food_source(ant.x, ant.y)

        # Choose direction
        direction = ant.choose_direction(
            self.pheromone, self.height, self.width, walls=self.walls)

        # Add some randomness to movement
        if random.random() < 0.1:
            direction = _random_valid_direction(
                ant, self.walls, self.width, self.height)

        ant.direction = direction

        # Move
        nx = ant.x + direction[0]
        ny = ant.y + direction[1]

        # Check if new position is valid (in-bounds and not a wall)
        if (0 <= nx < self.width and 0 <= ny < self.height
                and (nx, ny) not in self.walls):
            ant.x = nx
            ant.y = ny
        else:
            # Bounce: reverse direction
            ant.direction = (-ant.direction[0], -ant.direction[1])

        # Deposit pheromone
        if ant.carrying:
            deposit = self.pheromone_deposit * ANT_CARRY_PHEROMONE_BOOST
            ant.steps_carrying += 1
        else:
            deposit = self.pheromone_deposit * 0.3

        # Pheromone fades the further from nest the ant has gone
        ant.steps_since_drop += 1
        fade = max(0.1, 1.0 / (1.0 + ant.steps_since_drop * 0.005))
        max_pheromone = PHEROMONE_DEPOSIT * ANT_CARRY_PHEROMONE_BOOST * 20.0
        self.pheromone[ant.y][ant.x] = min(
            self.pheromone[ant.y][ant.x] + deposit * fade, max_pheromone)

    def get_stats(self) -> dict:
        """Return a dictionary of current simulation statistics."""
        carrying_count = sum(1 for a in self.ants if a.carrying)
        max_pheromone = max(max(row) for row in self.pheromone) if self.pheromone else 0
        total_steps = self.tick * self.num_ants
        efficiency = (self.food_collected / max(1, total_steps)) * 1000
        avg_delivery_time = (
            sum(self.food_delivery_times) / len(self.food_delivery_times)
            if self.food_delivery_times else 0
        )
        best_forager = max(self.ants, key=lambda a: a.food_delivered) if self.ants else None

        return {
            'tick': self.tick,
            'ants': len(self.ants),
            'food_collected': self.food_collected,
            'total_food': self.total_food,
            'carrying': carrying_count,
            'max_pheromone': max_pheromone,
            'peak_pheromone': self.peak_pheromone,
            'efficiency': efficiency,
            'sources_remaining': len(self.food_sources),
            'avg_delivery_ticks': avg_delivery_time,
            'best_forager_deliveries': best_forager.food_delivered if best_forager else 0,
            'walls': len(self.walls),
            'all_collected': self.food_collected >= self.total_food,
        }


def get_pheromone_char(val: float) -> Tuple[str, int]:
    """Return (char, color_pair) for a pheromone level.

    Args:
        val: Pheromone intensity value.

    Returns:
        Tuple of (display character, curses color pair index).
    """
    if val < 0.5:
        return (' ', 0)
    elif val < 2:
        return ('·', PAIR_PHEROMONE_VLOW)
    elif val < 8:
        return ('∘', PAIR_PHEROMONE_LOW)
    elif val < 30:
        return ('○', PAIR_PHEROMONE_MED)
    elif val < 80:
        return ('◎', PAIR_PHEROMONE_MED)
    else:
        return ('◉', PAIR_PHEROMONE_HIGH)


def run_headless(num_ants: int = NUM_ANTS_DEFAULT, max_ticks: int = 1000,
                 num_walls: int = NUM_WALLS_DEFAULT, evaporation: float = EVAPORATION_RATE,
                 seed: Optional[int] = None, json_output: bool = False):
    """Run the simulation in headless (batch) mode without a terminal UI.

    Args:
        num_ants: Number of ants in the simulation.
        max_ticks: Maximum number of ticks to simulate.
        num_walls: Number of wall obstacles.
        evaporation: Pheromone evaporation rate.
        seed: Random seed for reproducibility.
        json_output: If True, output results as JSON.
    """
    # Use a fixed grid size for headless mode
    sim = AntColonySimulation(
        80, 24, num_ants=num_ants, num_walls=num_walls,
        evaporation_rate=evaporation, seed=seed)

    for _ in range(max_ticks):
        sim.step()
        if sim.food_collected >= sim.total_food:
            break

    stats = sim.get_stats()
    stats['completed'] = sim.food_collected >= sim.total_food

    if json_output:
        print(json.dumps(stats, indent=2))
    else:
        print(f"=== Ant Colony Simulation Results ===")
        print(f"  Ticks simulated:  {stats['tick']}")
        print(f"  Food collected:    {stats['food_collected']}/{stats['total_food']}")
        print(f"  Sources remaining: {stats['sources_remaining']}")
        print(f"  Peak pheromone:    {stats['peak_pheromone']:.1f}")
        print(f"  Avg delivery time: {stats['avg_delivery_ticks']:.0f} ticks")
        print(f"  Best forager:      {stats['best_forager_deliveries']} deliveries")
        print(f"  Efficiency:        {stats['efficiency']:.3f}")
        print(f"  Completed:         {'Yes 🎉' if stats['completed'] else 'No (ran out of ticks)'}")

    return stats


def main(stdscr, args=None):
    """Main curses-based simulation loop with interactive controls.

    Args:
        stdscr: curses window object (provided by curses.wrapper).
        args: Pre-parsed argparse namespace. If None, defaults are used.
    """
    if args is None:
        # Use defaults if called without argparse (e.g., from tests)
        import argparse
        args = argparse.Namespace(
            ants=NUM_ANTS_DEFAULT, fps=FPS, evaporation=EVAPORATION_RATE,
            walls=NUM_WALLS_DEFAULT, no_walls=False, headless=False,
            ticks=1000, seed=None, json=False)

    num_walls = 0 if args.no_walls else args.walls

    # Curses setup
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(int(1000 / args.fps))

    # Initialize colors
    curses.init_pair(PAIR_EMPTY, curses.COLOR_WHITE, 236)          # dark gray bg
    curses.init_pair(PAIR_PHEROMONE_VLOW, 242, 236)               # dim
    curses.init_pair(PAIR_PHEROMONE_LOW, 58, 236)                 # dark green
    curses.init_pair(PAIR_PHEROMONE_MED, 82, 236)                  # bright green
    curses.init_pair(PAIR_PHEROMONE_HIGH, 226, 236)                # yellow
    curses.init_pair(PAIR_ANT_SEARCH, 249, 236)                    # light gray
    curses.init_pair(PAIR_ANT_CARRY, 214, 236)                    # orange
    curses.init_pair(PAIR_FOOD, 196, 236)                          # red
    curses.init_pair(PAIR_NEST, 33, 236)                           # blue
    curses.init_pair(PAIR_WALL, 240, 236)                         # gray
    curses.init_pair(PAIR_INFO, 252, 235)                         # light text

    max_y, max_x = stdscr.getmaxyx()
    # Reserve 4 lines for info panel at bottom
    sim_height = max(10, max_y - 4)
    sim_width = max(20, max_x)

    sim = AntColonySimulation(
        sim_width, sim_height, num_ants=args.ants, num_walls=num_walls,
        evaporation_rate=args.evaporation, seed=args.seed)

    paused = False
    speed_mult = 1
    show_legend = False

    while True:
        key = stdscr.getch()
        if key == ord('q') or key == 27:  # q or ESC
            break
        elif key == ord(' '):
            paused = not paused
        elif key == ord('+') or key == ord('='):
            speed_mult = min(speed_mult + 1, 10)
        elif key == ord('-'):
            speed_mult = max(speed_mult - 1, 1)
        elif key == ord('r'):
            sim = AntColonySimulation(
                sim_width, sim_height, num_ants=args.ants, num_walls=num_walls,
                evaporation_rate=args.evaporation, seed=args.seed)
        elif key == ord('l'):
            show_legend = not show_legend

        # Handle terminal resize
        new_max_y, new_max_x = stdscr.getmaxyx()
        if new_max_y != max_y or new_max_x != max_x:
            max_y, max_x = new_max_y, new_max_x
            sim_height = max(10, max_y - 4)
            sim_width = max(20, max_x)
            # Note: simulation grid stays the same size; we just render what fits

        if not paused:
            for _ in range(speed_mult):
                sim.step()

        # ── Render ─────────────────────────────────────────────────────
        # Build display buffer
        display = [[(' ', 0)] * sim.width for _ in range(sim.height)]

        # Draw pheromone layer
        for y in range(sim.height):
            for x in range(sim.width):
                pval = sim.pheromone[y][x]
                if pval > 0.3:
                    ch, cpair = get_pheromone_char(pval)
                    display[y][x] = (ch, cpair)

        # Draw walls
        for wx, wy in sim.walls:
            if 0 <= wy < sim.height and 0 <= wx < sim.width:
                display[wy][wx] = ('▓', PAIR_WALL)

        # Draw food
        for y in range(sim.height):
            for x in range(sim.width):
                if sim.food_grid[y][x] > 0:
                    fval = sim.food_grid[y][x]
                    if fval > 15:
                        ch = '█'
                    elif fval > 5:
                        ch = '▓'
                    else:
                        ch = '▒'
                    display[y][x] = (ch, PAIR_FOOD)

        # Draw nest
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = sim.nest_x + dx, sim.nest_y + dy
                if 0 <= nx < sim.width and 0 <= ny < sim.height:
                    if dx == 0 and dy == 0:
                        display[ny][nx] = ('⌂', PAIR_NEST)
                    else:
                        display[ny][nx] = ('░', PAIR_NEST)

        # Draw ants
        for ant in sim.ants:
            if 0 <= ant.x < sim.width and 0 <= ant.y < sim.height:
                if ant.carrying:
                    display[ant.y][ant.x] = ('●', PAIR_ANT_CARRY)
                else:
                    display[ant.y][ant.x] = ('·', PAIR_ANT_SEARCH)

        # ── Write to screen ────────────────────────────────────────────
        stdscr.erase()

        # Determine visible area based on terminal size
        render_height = min(sim.height, max_y - 4)
        render_width = min(sim.width, max_x)

        # Render simulation area using color runs for speed
        for y in range(render_height):
            x = 0
            while x < render_width:
                ch, cpair = display[y][x]
                if cpair == 0:
                    cpair = PAIR_EMPTY
                # Collect a run of same-color characters
                run = ch
                x2 = x + 1
                while x2 < render_width:
                    ch2, cp2 = display[y][x2]
                    if cp2 == 0:
                        cp2 = PAIR_EMPTY
                    if cp2 != cpair:
                        break
                    run += ch2
                    x2 += 1
                try:
                    stdscr.addstr(y, x, run, curses.color_pair(cpair))
                except curses.error:
                    pass
                x = x2

        # ── Info panel ─────────────────────────────────────────────────
        info_y = render_height
        stats = sim.get_stats()

        info_lines = [
            f"🐜 Ants: {stats['ants']} | 🍬 Food: {stats['food_collected']}/{stats['total_food']} | "
            f"🚶 Carrying: {stats['carrying']} | 📊 Max Ph: {stats['max_pheromone']:.1f} | "
            f"⚡ Eff: {stats['efficiency']:.3f} | ⏱ Tick: {stats['tick']}",
            f"[SPACE] Pause{'  (PAUSED)' if paused else ''} | [+/-] Speed: {speed_mult}x | "
            f"[R] Reset | [L] Legend | [Q] Quit"
            f"{'  | Walls: ' + str(stats['walls']) + ' cells' if stats['walls'] > 0 else ''}",
            f"Sources left: {stats['sources_remaining']} | "
            f"Avg delivery: {stats['avg_delivery_ticks']:.0f} ticks | "
            f"{'All food collected! 🎉' if stats['all_collected'] else 'Ants are foraging...'}",
        ]

        for i, line in enumerate(info_lines):
            if info_y + i < max_y:
                try:
                    stdscr.addstr(info_y + i, 0, line, curses.color_pair(PAIR_INFO))
                except curses.error:
                    pass

        # ── Legend overlay ─────────────────────────────────────────────
        if show_legend:
            legend_lines = [
                "┌─── Legend ──────────────────┐",
                "│ ·  Searching ant (gray)     │",
                "│ ●  Carrying ant (orange)     │",
                "│ ▓▒ Food source (red)         │",
                "│ ⌂  Nest center (blue)        │",
                "│ ▓  Wall obstacle (gray)      │",
                "│ ·∘○◎◉  Pheromone intensity   │",
                "└─────────────────────────────┘",
            ]
            for i, line in enumerate(legend_lines):
                if 1 + i < render_height:
                    try:
                        stdscr.addstr(1 + i, 2, line, curses.color_pair(PAIR_INFO))
                    except curses.error:
                        pass

        stdscr.refresh()


if __name__ == '__main__':
    # Parse args before launching curses so --version and --help work
    # without requiring a terminal
    import sys
    parser = argparse.ArgumentParser(
        description='Terminal Ant Colony Simulator — watch emergent foraging behavior!',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s                      Run with defaults
  %(prog)s --ants 120           More ants for denser trails
  %(prog)s --walls 5            Add obstacle walls
  %(prog)s --fps 30             Faster animation
  %(prog)s --headless --ticks 2000 --seed 42   Batch mode for benchmarking
  %(prog)s --version            Show version
""")
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('-a', '--ants', type=int, default=NUM_ANTS_DEFAULT,
                        help=f'Number of ants (default: {NUM_ANTS_DEFAULT})')
    parser.add_argument('-f', '--fps', type=int, default=FPS,
                        help=f'Target FPS (default: {FPS})')
    parser.add_argument('--evaporation', type=float, default=EVAPORATION_RATE,
                        help=f'Pheromone evaporation rate (default: {EVAPORATION_RATE})')
    parser.add_argument('-w', '--walls', type=int, default=NUM_WALLS_DEFAULT,
                        help=f'Number of wall obstacles (default: {NUM_WALLS_DEFAULT})')
    parser.add_argument('--no-walls', action='store_true',
                        help='Disable wall obstacles entirely')
    parser.add_argument('--headless', action='store_true',
                        help='Run without terminal UI (batch mode)')
    parser.add_argument('--ticks', type=int, default=1000,
                        help='Max ticks for headless mode (default: 1000)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility')
    parser.add_argument('--json', action='store_true',
                        help='Output JSON in headless mode')
    args = parser.parse_args()

    num_walls = 0 if args.no_walls else args.walls

    if args.headless:
        run_headless(
            num_ants=args.ants, max_ticks=args.ticks, num_walls=num_walls,
            evaporation=args.evaporation, seed=args.seed, json_output=args.json)
    else:
        curses.wrapper(lambda stdscr: main(stdscr, args))