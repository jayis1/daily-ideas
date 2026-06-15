#!/usr/bin/env python3
"""
Boids Flocking Simulator — Terminal-based real-time simulation of Craig Reynolds' Boids algorithm.
Watch ASCII birds flock, evade predators, and navigate obstacles in your terminal!
"""

import curses
import random
import math
import time
import argparse
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class Vec2:
    """Simple 2D vector."""
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> "Vec2":
        return Vec2(self.x / scalar, self.y / scalar)

    def magnitude(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalized(self) -> "Vec2":
        m = self.magnitude()
        if m < 1e-8:
            return Vec2(0, 0)
        return Vec2(self.x / m, self.y / m)

    def limit(self, max_val: float) -> "Vec2":
        m = self.magnitude()
        if m > max_val:
            return self.normalized() * max_val
        return Vec2(self.x, self.y)

    def distance_to(self, other: "Vec2") -> float:
        return (self - other).magnitude()

    def copy(self) -> "Vec2":
        return Vec2(self.x, self.y)


@dataclass
class Boid:
    """A single boid (bird-oid) entity."""
    pos: Vec2
    vel: Vec2
    char: str = "o"
    color_pair: int = 1
    trail: List[Vec2] = field(default_factory=list)
    max_trail: int = 5

    def update(self, max_speed: float):
        self.vel = self.vel.limit(max_speed)
        self.trail.append(self.pos.copy())
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)
        self.pos = self.pos + self.vel


@dataclass
class Predator:
    """A predator that chases boids."""
    pos: Vec2
    vel: Vec2
    hunt_radius: float = 15.0

    def update(self, max_speed: float):
        self.vel = self.vel.limit(max_speed)
        self.pos = self.pos + self.vel


@dataclass
class Obstacle:
    """A circular obstacle that boids avoid."""
    pos: Vec2
    radius: float = 3.0


class BoidSimulation:
    """Main simulation engine using Reynolds' Boids rules."""

    def __init__(self, width: int, height: int, num_boids: int = 50,
                 num_predators: int = 0, num_obstacles: int = 0):
        self.width = width
        self.height = height
        self.max_speed = 2.0
        self.max_force = 0.15

        # Rule weights
        self.separation_weight = 2.0
        self.alignment_weight = 1.0
        self.cohesion_weight = 1.0
        self.predator_flee_weight = 3.0
        self.obstacle_avoid_weight = 2.5

        # Perception radii
        self.separation_radius = 6.0
        self.alignment_radius = 15.0
        self.cohesion_radius = 20.0

        self.boids: List[Boid] = []
        self.predators: List[Predator] = []
        self.obstacles: List[Obstacle] = []

        self.paused = False
        self.show_trails = False
        self.show_debug = False
        self.show_vectors = False
        self.tick_count = 0
        self.eaten_count = 0

        # Boid display characters — vary for visual interest
        boid_chars = list(">v<^o·°○")

        # Color pairs for boids (will be mapped to curses colors)
        boid_colors = [1, 2, 3, 4]

        for i in range(num_boids):
            pos = Vec2(random.uniform(5, width - 5), random.uniform(5, height - 5))
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 1.5)
            vel = Vec2(math.cos(angle) * speed, math.sin(angle) * speed)
            char = random.choice(boid_chars)
            color = random.choice(boid_colors)
            self.boids.append(Boid(pos=pos, vel=vel, char=char, color_pair=color))

        for _ in range(num_predators):
            pos = Vec2(random.uniform(5, width - 5), random.uniform(5, height - 5))
            angle = random.uniform(0, 2 * math.pi)
            vel = Vec2(math.cos(angle) * 0.5, math.sin(angle) * 0.5)
            self.predators.append(Predator(pos=pos, vel=vel))

        for _ in range(num_obstacles):
            pos = Vec2(random.uniform(10, width - 10), random.uniform(5, height - 5))
            self.obstacles.append(Obstacle(pos=pos, radius=random.uniform(2, 4)))

    def _steer_towards(self, boid: Boid, target_vel: Vec2) -> Vec2:
        """Reynolds steering: desired velocity minus current velocity, limited."""
        desired = target_vel.normalized() * self.max_speed
        steer = desired - boid.vel
        return steer.limit(self.max_force)

    def separation(self, boid: Boid) -> Vec2:
        """Steer to avoid crowding nearby boids."""
        steer = Vec2(0, 0)
        count = 0
        for other in self.boids:
            if other is boid:
                continue
            d = boid.pos.distance_to(other.pos)
            if 0 < d < self.separation_radius:
                diff = boid.pos - other.pos
                diff = diff.normalized() / max(d, 0.1)  # Weight by inverse distance
                steer = steer + diff
                count += 1
        if count > 0:
            steer = steer / count
        return self._steer_towards(boid, steer)

    def alignment(self, boid: Boid) -> Vec2:
        """Steer towards average heading of nearby boids."""
        avg_vel = Vec2(0, 0)
        count = 0
        for other in self.boids:
            if other is boid:
                continue
            d = boid.pos.distance_to(other.pos)
            if 0 < d < self.alignment_radius:
                avg_vel = avg_vel + other.vel
                count += 1
        if count > 0:
            avg_vel = avg_vel / count
        return self._steer_towards(boid, avg_vel)

    def cohesion(self, boid: Boid) -> Vec2:
        """Steer towards average position of nearby boids."""
        center = Vec2(0, 0)
        count = 0
        for other in self.boids:
            if other is boid:
                continue
            d = boid.pos.distance_to(other.pos)
            if 0 < d < self.cohesion_radius:
                center = center + other.pos
                count += 1
        if count > 0:
            center = center / count
            desired = center - boid.pos
            return self._steer_towards(boid, desired)
        return Vec2(0, 0)

    def flee_predators(self, boid: Boid) -> Vec2:
        """Steer away from predators."""
        steer = Vec2(0, 0)
        count = 0
        for pred in self.predators:
            d = boid.pos.distance_to(pred.pos)
            if d < pred.hunt_radius:
                diff = boid.pos - pred.pos
                diff = diff.normalized() / max(d, 0.1)
                steer = steer + diff
                count += 1
        if count > 0:
            steer = steer / count
        return self._steer_towards(boid, steer)

    def avoid_obstacles(self, boid: Boid) -> Vec2:
        """Steer away from obstacles."""
        steer = Vec2(0, 0)
        for obs in self.obstacles:
            d = boid.pos.distance_to(obs.pos)
            avoid_dist = obs.radius + 5.0
            if d < avoid_dist:
                diff = boid.pos - obs.pos
                strength = 1.0 - (d / avoid_dist)
                diff = diff.normalized() * strength
                steer = steer + diff
        if steer.magnitude() > 0:
            return self._steer_towards(boid, steer)
        return Vec2(0, 0)

    def wrap_position(self, boid: Boid):
        """Wrap boid around screen edges."""
        if boid.pos.x < 0:
            boid.pos.x = self.width
            boid.trail.clear()
        elif boid.pos.x > self.width:
            boid.pos.x = 0
            boid.trail.clear()
        if boid.pos.y < 0:
            boid.pos.y = self.height
            boid.trail.clear()
        elif boid.pos.y > self.height:
            boid.pos.y = 0
            boid.trail.clear()

    def update_predators(self):
        """Predators chase the nearest boid."""
        predator_speed = self.max_speed * 0.7
        for pred in self.predators:
            if not self.boids:
                continue
            # Find nearest boid
            nearest = min(self.boids, key=lambda b: pred.pos.distance_to(b.pos))
            desired = nearest.pos - pred.pos
            steer = self._steer_towards_pred(pred, desired)
            pred.vel = (pred.vel + steer).limit(predator_speed)
            # Wrap predator
            pred.pos = pred.pos + pred.vel
            if pred.pos.x < 0: pred.pos.x = self.width
            elif pred.pos.x > self.width: pred.pos.x = 0
            if pred.pos.y < 0: pred.pos.y = self.height
            elif pred.pos.y > self.height: pred.pos.y = 0

        # Check if predator caught a boid
        for pred in self.predators:
            caught = []
            for boid in self.boids:
                if pred.pos.distance_to(boid.pos) < 1.5:
                    caught.append(boid)
            for boid in caught:
                self.boids.remove(boid)
                self.eaten_count += 1

    def _steer_towards_pred(self, pred: Predator, desired: Vec2) -> Vec2:
        desired = desired.normalized() * (self.max_speed * 0.7)
        steer = desired - pred.vel
        return steer.limit(self.max_force * 0.8)

    def update(self):
        """Update all boids with flocking rules."""
        if self.paused:
            return

        self.tick_count += 1

        # Calculate new velocities
        new_vels = []
        for boid in self.boids:
            sep = self.separation(boid) * self.separation_weight
            ali = self.alignment(boid) * self.alignment_weight
            coh = self.cohesion(boid) * self.cohesion_weight

            total = sep + ali + coh

            if self.predators:
                total = total + self.flee_predators(boid) * self.predator_flee_weight

            if self.obstacles:
                total = total + self.avoid_obstacles(boid) * self.obstacle_avoid_weight

            new_vels.append(boid.vel + total)

        # Apply new velocities
        for boid, new_vel in zip(self.boids, new_vels):
            boid.vel = new_vel
            boid.update(self.max_speed)
            self.wrap_position(boid)

        self.update_predators()

    def get_direction_char(self, boid: Boid) -> str:
        """Return a character based on movement direction."""
        if self.show_vectors:
            angle = math.atan2(boid.vel.y, boid.vel.x)
            # Map angle to direction chars
            dirs = "→↗↑↖←↙↓↘"
            idx = int((angle + math.pi) / (math.pi / 4)) % 8
            return dirs[idx]
        return boid.char

    def add_predator_at(self, x: int, y: int):
        """Add a predator at screen position."""
        pos = Vec2(float(x), float(y))
        angle = random.uniform(0, 2 * math.pi)
        vel = Vec2(math.cos(angle) * 0.5, math.sin(angle) * 0.5)
        self.predators.append(Predator(pos=pos, vel=vel))

    def add_obstacle_at(self, x: int, y: int):
        """Add an obstacle at screen position."""
        pos = Vec2(float(x), float(y))
        self.obstacles.append(Obstacle(pos=pos, radius=random.uniform(2, 3.5)))

    def add_boids_at(self, x: int, y: int, count: int = 10):
        """Add a group of boids at screen position."""
        for _ in range(count):
            pos = Vec2(float(x) + random.uniform(-3, 3),
                      float(y) + random.uniform(-3, 3))
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 1.5)
            vel = Vec2(math.cos(angle) * speed, math.sin(angle) * speed)
            char = random.choice(list(">v<^o·°○"))
            color = random.choice([1, 2, 3, 4])
            self.boids.append(Boid(pos=pos, vel=vel, char=char, color_pair=color))


def run_simulation(stdscr, num_boids=50, num_predators=0, num_obstacles=0):
    """Main simulation loop with curses rendering."""
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(33)  # ~30 FPS

    # Initialize colors
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)      # Predator
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_RED)       # Obstacle
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)    # UI text
    curses.init_pair(8, curses.COLOR_BLUE, curses.COLOR_BLACK)     # Trail
    curses.init_pair(9, curses.COLOR_RED, curses.COLOR_BLACK)      # Debug

    height, width = stdscr.getmaxyx()
    sim = BoidSimulation(width, height, num_boids, num_predators, num_obstacles)

    running = True
    fps_times = []
    fps = 0.0

    while running:
        t0 = time.time()

        # Handle input
        key = stdscr.getch()
        if key == ord('q') or key == ord('Q'):
            running = False
        elif key == ord(' '):
            sim.paused = not sim.paused
        elif key == ord('t'):
            sim.show_trails = not sim.show_trails
        elif key == ord('d'):
            sim.show_debug = not sim.show_debug
        elif key == ord('v'):
            sim.show_vectors = not sim.show_vectors
        elif key == ord('+') or key == ord('='):
            # Increase separation
            sim.separation_weight = min(sim.separation_weight + 0.5, 10.0)
        elif key == ord('-'):
            sim.separation_weight = max(sim.separation_weight - 0.5, 0.0)
        elif key == ord('p'):
            # Add predator at random position
            sim.add_predator_at(random.randint(5, width-5), random.randint(5, height-5))
        elif key == ord('o'):
            # Add obstacle at random position
            sim.add_obstacle_at(random.randint(10, width-10), random.randint(5, height-5))
        elif key == ord('b'):
            # Add boids at random position
            sim.add_boids_at(random.randint(5, width-5), random.randint(5, height-5))
        elif key == ord('r'):
            # Reset
            sim = BoidSimulation(width, height, num_boids, num_predators, num_obstacles)
        elif key == ord('1'):
            # Preset: tight flocking
            sim.separation_weight = 1.0
            sim.alignment_weight = 2.0
            sim.cohesion_weight = 2.0
        elif key == ord('2'):
            # Preset: loose swarm
            sim.separation_weight = 3.0
            sim.alignment_weight = 0.5
            sim.cohesion_weight = 0.5
        elif key == ord('3'):
            # Preset: balanced (default)
            sim.separation_weight = 2.0
            sim.alignment_weight = 1.0
            sim.cohesion_weight = 1.0
        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, _ = curses.getmouse()
                if my < height - 1:
                    sim.add_predator_at(mx, my)
            except curses.error:
                pass
        elif key == curses.KEY_RESIZE:
            height, width = stdscr.getmaxyx()
            sim.width = width
            sim.height = height
            stdscr.clear()

        # Handle mouse clicks for adding predators
        try:
            curses.mousemask(curses.ALL_MOUSE_EVENTS)
        except:
            pass

        # Update simulation
        sim.update()

        # Render
        stdscr.erase()

        # Draw obstacles
        for obs in sim.obstacles:
            ox, oy = int(obs.pos.x), int(obs.pos.y)
            r = int(obs.radius)
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        px, py = ox + dx, oy + dy
                        if 0 <= px < width and 0 <= py < height:
                            try:
                                stdscr.addch(py, px, '#', curses.color_pair(6))
                            except curses.error:
                                pass

        # Draw trails
        if sim.show_trails:
            for boid in sim.boids:
                for i, trail_pos in enumerate(boid.trail):
                    tx, ty = int(trail_pos.x), int(trail_pos.y)
                    if 0 <= tx < width and 0 <= ty < height:
                        trail_chars = "·:;"
                        tc = trail_chars[min(i, len(trail_chars)-1)]
                        try:
                            stdscr.addch(ty, tx, tc, curses.color_pair(8) | curses.A_DIM)
                        except curses.error:
                            pass

        # Draw boids
        for boid in sim.boids:
            bx, by = int(boid.pos.x), int(boid.pos.y)
            if 0 <= bx < width and 0 <= by < height:
                char = sim.get_direction_char(boid)
                try:
                    stdscr.addch(by, bx, char, curses.color_pair(boid.color_pair))
                except curses.error:
                    pass

        # Draw predators
        for pred in sim.predators:
            px, py = int(pred.pos.x), int(pred.pos.y)
            if 0 <= px < width and 0 <= py < height:
                try:
                    stdscr.addch(py, px, 'X', curses.color_pair(5) | curses.A_BOLD)
                except curses.error:
                    pass

        # Draw HUD
        hud_line = height - 1
        status = f" Boids:{len(sim.boids)} Predators:{len(sim.predators)} Obstacles:{len(sim.obstacles)}"
        status += f" Sep:{sim.separation_weight:.1f} Ali:{sim.alignment_weight:.1f} Coh:{sim.cohesion_weight:.1f}"
        if sim.paused:
            status += " [PAUSED]"
        status += f" FPS:{fps:.0f}"
        try:
            stdscr.addstr(hud_line, 0, status[:width-1], curses.color_pair(7) | curses.A_REVERSE)
        except curses.error:
            pass

        # Draw debug info
        if sim.show_debug and sim.boids:
            b = sim.boids[0]
            debug = f"Pos:({b.pos.x:.1f},{b.pos.y:.1f}) Vel:({b.vel.x:.2f},{b.vel.y:.2f}) Tick:{sim.tick_count}"
            try:
                stdscr.addstr(0, 0, debug[:width-1], curses.color_pair(9))
            except curses.error:
                pass

        # Controls help (top right)
        help_text = "[Space]Pause [T]rails [D]ebug [V]ectors [P]redator [O]bstacle [B]oids [+/-]Sep [1-3]Presets [R]eset [Q]uit"
        try:
            stdscr.addstr(0, max(0, width - len(help_text) - 1), help_text[:width-1], curses.color_pair(7) | curses.A_DIM)
        except curses.error:
            pass

        stdscr.refresh()

        # FPS calculation
        t1 = time.time()
        fps_times.append(t1 - t0)
        if len(fps_times) > 30:
            fps_times.pop(0)
        avg_frame = sum(fps_times) / len(fps_times) if fps_times else 0.033
        fps = 1.0 / max(avg_frame, 0.001)

    return sim.eaten_count


def main():
    parser = argparse.ArgumentParser(
        description="Boids Flocking Simulator — Watch emergent flocking behavior in your terminal!"
    )
    parser.add_argument("-n", "--boids", type=int, default=50,
                       help="Number of boids (default: 50)")
    parser.add_argument("-p", "--predators", type=int, default=0,
                       help="Number of predators (default: 0)")
    parser.add_argument("-o", "--obstacles", type=int, default=0,
                       help="Number of obstacles (default: 0)")
    args = parser.parse_args()

    try:
        eaten = curses.wrapper(run_simulation, args.boids, args.predators, args.obstacles)
        print(f"\n🐦 Boids simulation ended. {eaten} boid(s) were eaten by predators.")
    except KeyboardInterrupt:
        print("\n🐦 Boids simulation interrupted.")


if __name__ == "__main__":
    main()