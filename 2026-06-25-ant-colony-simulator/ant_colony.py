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
"""

import curses
import random
import math
import time
import argparse
from collections import defaultdict

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

# ── Direction Helpers ──────────────────────────────────────────────────────

DIRS_8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
DIRS_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]


class Ant:
    """A single ant agent with simple behavioral rules."""

    __slots__ = ('x', 'y', 'carrying', 'direction', 'steps_since_drop', 'home_x', 'home_y')

    def __init__(self, x, y, home_x, home_y):
        self.x = x
        self.y = y
        self.home_x = home_x
        self.home_y = home_y
        self.carrying = False
        self.direction = random.choice(DIRS_8)
        self.steps_since_drop = 0

    def sense_pheromone(self, grid, height, width, sense_forward=True):
        """Sample pheromone in nearby cells, biased toward forward movement."""
        best_val = 0.0
        best_dir = None
        candidates = []

        for dx, dy in DIRS_8:
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < width and 0 <= ny < height:
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

    def choose_direction(self, grid, height, width):
        """Pick next direction based on state and pheromone sensing."""
        if self.carrying:
            # Head home — use pheromone trail if available, otherwise go toward nest
            best_dir, best_val, candidates = self.sense_pheromone(grid, height, width, sense_forward=True)

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
            best_dir, best_val, candidates = self.sense_pheromone(grid, height, width, sense_forward=True)

            if best_val > 1.0:
                # Strong pheromone — follow it with some randomness
                if random.random() < 0.85:
                    return best_dir
                else:
                    return random.choice(DIRS_8)
            else:
                # Weak/no pheromone — wander with forward momentum
                if random.random() < WANDER_STRENGTH:
                    # Continue roughly forward
                    return self.direction
                else:
                    return random.choice(DIRS_8)


class FoodSource:
    """A food source at a position with remaining quantity."""

    __slots__ = ('x', 'y', 'amount')

    def __init__(self, x, y, amount):
        self.x = x
        self.y = y
        self.amount = amount


class AntColonySimulation:
    """Main simulation engine."""

    def __init__(self, width, height, num_ants=NUM_ANTS_DEFAULT):
        self.width = width
        self.height = height
        self.num_ants = num_ants

        # Nest position (center-ish)
        self.nest_x = width // 2
        self.nest_y = height // 2

        # Pheromone grid (float)
        self.pheromone = [[0.0] * width for _ in range(height)]

        # Food grid (int — amount per cell)
        self.food_grid = [[0] * width for _ in range(height)]
        self.food_sources = []

        # Create ants
        self.ants = []
        for _ in range(num_ants):
            ax = self.nest_x + random.randint(-2, 2)
            ay = self.nest_y + random.randint(-2, 2)
            ax = max(0, min(width - 1, ax))
            ay = max(0, min(height - 1, ay))
            self.ants.append(Ant(ax, ay, self.nest_x, self.nest_y))

        # Statistics
        self.food_collected = 0
        self.total_food = 0
        self.tick = 0

        # Place initial pheromone around nest to guide early exploration
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                nx, ny = self.nest_x + dx, self.nest_y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist < 4:
                        self.pheromone[ny][nx] = 15.0 * (1.0 - dist / 4.0)

        # Place food sources
        self._place_food()

    def _place_food(self):
        """Place food sources around the map."""
        margin = 4
        for _ in range(NUM_FOOD_SOURCES):
            fx = self.nest_x
            fy = self.nest_y
            attempts = 0
            while attempts < 50:
                fx = random.randint(margin, self.width - margin - 1)
                fy = random.randint(margin, self.height - margin - 1)
                # Don't place too close to nest
                dist = math.sqrt((fx - self.nest_x)**2 + (fy - self.nest_y)**2)
                if dist > min(self.width, self.height) * 0.25:
                    break
                attempts += 1

            amount = FOOD_PER_SOURCE + random.randint(-20, 20)
            self.food_sources.append(FoodSource(fx, fy, amount))

            # Spread food in a small cluster
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    nx, ny = fx + dx, fy + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        cell_amount = max(1, amount // 9)
                        self.food_grid[ny][nx] += cell_amount

            self.total_food += amount

    def step(self):
        """Advance simulation by one tick."""
        self.tick += 1

        # Evaporate and diffuse pheromones
        self._evaporate_pheromones()

        # Update each ant
        for ant in self.ants:
            self._update_ant(ant)

        # Remove depleted food sources
        self.food_sources = [f for f in self.food_sources if f.amount > 0]

    def _evaporate_pheromones(self):
        """Apply evaporation and diffusion to pheromone grid."""
        new_grid = [[0.0] * self.width for _ in range(self.height)]

        for y in range(self.height):
            for x in range(self.width):
                val = self.pheromone[y][x]
                if val < 0.01:
                    new_grid[y][x] = 0.0
                    continue

                # Diffusion: spread to neighbors
                diffused = val * DIFFUSION_RATE
                kept = val * (1.0 - DIFFUSION_RATE) * EVAPORATION_RATE

                new_grid[y][x] += kept

                for dx, dy in DIRS_4:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        new_grid[ny][nx] += diffused / 4.0

        self.pheromone = new_grid

    def _update_ant(self, ant):
        """Update a single ant's state."""
        # Check if ant is at nest and carrying — drop food
        if ant.carrying:
            dist_to_nest = math.sqrt((ant.x - ant.home_x)**2 + (ant.y - ant.home_y)**2)
            if dist_to_nest < 2.0:
                ant.carrying = False
                self.food_collected += 1
                ant.steps_since_drop = 0

        # Check if ant is on food and not carrying — pick up food
        if not ant.carrying and self.food_grid[ant.y][ant.x] > 0:
            ant.carrying = True
            self.food_grid[ant.y][ant.x] -= 1
            ant.steps_since_drop = 0

        # Choose direction
        direction = ant.choose_direction(self.pheromone, self.height, self.width)

        # Add some randomness to movement
        if random.random() < 0.1:
            direction = random.choice(DIRS_8)

        ant.direction = direction

        # Move
        nx = ant.x + direction[0]
        ny = ant.y + direction[1]

        # Boundary — bounce
        if 0 <= nx < self.width and 0 <= ny < self.height:
            ant.x = nx
            ant.y = ny
        else:
            # Bounce back
            ant.direction = (-ant.direction[0], -ant.direction[1])

        # Deposit pheromone
        if ant.carrying:
            deposit = PHEROMONE_DEPOSIT * ANT_CARRY_PHEROMONE_BOOST
        else:
            deposit = PHEROMONE_DEPOSIT * 0.3

        # Pheromone fades the further from nest the ant has gone
        ant.steps_since_drop += 1
        fade = max(0.1, 1.0 / (1.0 + ant.steps_since_drop * 0.005))
        self.pheromone[ant.y][ant.x] += deposit * fade


def get_pheromone_char(val):
    """Return (char, color_pair) for a pheromone level."""
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


def main(stdscr):
    parser = argparse.ArgumentParser(description='Terminal Ant Colony Simulator')
    parser.add_argument('-a', '--ants', type=int, default=NUM_ANTS_DEFAULT,
                        help=f'Number of ants (default: {NUM_ANTS_DEFAULT})')
    parser.add_argument('-f', '--fps', type=int, default=FPS,
                        help=f'Target FPS (default: {FPS})')
    parser.add_argument('--evaporation', type=float, default=EVAPORATION_RATE,
                        help=f'Pheromone evaporation rate (default: {EVAPORATION_RATE})')
    args = parser.parse_args()

    # Curses setup
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(int(1000 / args.fps))

    # Colors
    curses.init_pair(PAIR_EMPTY, curses.COLOR_WHITE, 236)          # dark gray bg
    curses.init_pair(PAIR_PHEROMONE_VLOW, 242, 236)                 # dim
    curses.init_pair(PAIR_PHEROMONE_LOW, 58, 236)                   # dark green
    curses.init_pair(PAIR_PHEROMONE_MED, 82, 236)                  # bright green
    curses.init_pair(PAIR_PHEROMONE_HIGH, 226, 236)                 # yellow
    curses.init_pair(PAIR_ANT_SEARCH, 249, 236)                     # light gray
    curses.init_pair(PAIR_ANT_CARRY, 214, 236)                      # orange
    curses.init_pair(PAIR_FOOD, 196, 236)                            # red
    curses.init_pair(PAIR_NEST, 33, 236)                             # blue
    curses.init_pair(PAIR_WALL, 240, 236)                           # gray
    curses.init_pair(PAIR_INFO, 252, 235)                            # light text

    max_y, max_x = stdscr.getmaxyx()
    # Reserve 3 lines for info panel at bottom
    sim_height = max(10, max_y - 3)
    sim_width = max(20, max_x)

    sim = AntColonySimulation(sim_width, sim_height, num_ants=args.ants)

    paused = False
    speed_mult = 1

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
            sim = AntColonySimulation(sim_width, sim_height, num_ants=args.ants)

        if not paused:
            for _ in range(speed_mult):
                sim.step()

        # ── Render ─────────────────────────────────────────────────────
        # Build display buffer
        display = [[(' ', 0)] * sim_width for _ in range(sim_height)]

        # Draw pheromone layer
        for y in range(sim_height):
            for x in range(sim_width):
                pval = sim.pheromone[y][x]
                if pval > 0.3:
                    ch, cpair = get_pheromone_char(pval)
                    display[y][x] = (ch, cpair)

        # Draw food
        for y in range(sim_height):
            for x in range(sim_width):
                if sim.food_grid[y][x] > 0:
                    fval = sim.food_grid[y][x]
                    if fval > 15:
                        ch, cpair = '█', PAIR_FOOD
                    elif fval > 5:
                        ch, cpair = '▓', PAIR_FOOD
                    else:
                        ch, cpair = '▒', PAIR_FOOD
                    display[y][x] = (ch, cpair)

        # Draw nest
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = sim.nest_x + dx, sim.nest_y + dy
                if 0 <= nx < sim_width and 0 <= ny < sim_height:
                    if dx == 0 and dy == 0:
                        display[ny][nx] = ('⌂', PAIR_NEST)
                    else:
                        display[ny][nx] = ('░', PAIR_NEST)

        # Draw ants
        for ant in sim.ants:
            if 0 <= ant.x < sim_width and 0 <= ant.y < sim_height:
                if ant.carrying:
                    display[ant.y][ant.x] = ('●', PAIR_ANT_CARRY)
                else:
                    display[ant.y][ant.x] = ('·', PAIR_ANT_SEARCH)

        # ── Write to screen ────────────────────────────────────────────
        stdscr.erase()

        # Render simulation area using color runs for speed
        for y in range(sim_height):
            x = 0
            while x < sim_width:
                ch, cpair = display[y][x]
                if cpair == 0:
                    cpair = PAIR_EMPTY
                # Collect a run of same-color characters
                run = ch
                x2 = x + 1
                while x2 < sim_width:
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
        info_y = sim_height
        carrying_count = sum(1 for a in sim.ants if a.carrying)
        max_pheromone = max(max(row) for row in sim.pheromone) if sim.pheromone else 0

        # Compute path efficiency: food_collected / total_steps
        total_steps = sim.tick * sim.num_ants
        efficiency = (sim.food_collected / max(1, total_steps)) * 1000

        info_lines = [
            f"🐜 Ants: {len(sim.ants)} | 🍬 Food: {sim.food_collected}/{sim.total_food} | "
            f"🚶 Carrying: {carrying_count} | 📊 Max Pheromone: {max_pheromone:.1f} | "
            f"⚡ Efficiency: {efficiency:.3f} | ⏱ Tick: {sim.tick}",
            f"[SPACE] Pause{'  (PAUSED)' if paused else ''} | [+/-] Speed: {speed_mult}x | "
            f"[R] Reset | [Q] Quit",
            f"Food sources remaining: {len(sim.food_sources)} | "
            f"{'All food collected! 🎉' if sim.food_collected >= sim.total_food else 'Ants are foraging...'}",
        ]

        for i, line in enumerate(info_lines):
            try:
                stdscr.addstr(info_y + i, 0, line, curses.color_pair(PAIR_INFO))
            except curses.error:
                pass

        stdscr.refresh()


if __name__ == '__main__':
    curses.wrapper(main)