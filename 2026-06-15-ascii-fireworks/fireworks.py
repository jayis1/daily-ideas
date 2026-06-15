#!/usr/bin/env python3
"""
🎆 Terminal ASCII Fireworks Simulator
A real-time fireworks display in your terminal with particle physics,
multiple explosion patterns, and choreographed shows.
"""

import curses
import random
import math
import time
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional


class FireworkType(Enum):
    PEONY = "peony"          # Classic spherical burst
    CHRYSANTHEMUM = "chrysanthemum"  # Long trailing sparks
    WILLOW = "willow"        # Drooping trails
    PALM = "palm"            # Few thick streams
    CROSSETTE = "crossette"  # Stars that split again
    RING = "ring"            # Circle shape
    HEART = "heart"          # Heart shape
    SPIRAL = "spiral"        # Spiral pattern


class TrailType(Enum):
    NONE = 0
    SHORT = 1
    MEDIUM = 2
    LONG = 3


# Color palette indices for curses
COLOR_MAP = {
    "red": 1,
    "orange": 2,
    "yellow": 3,
    "green": 4,
    "cyan": 5,
    "blue": 6,
    "magenta": 7,
    "white": 8,
    "pink": 9,
    "gold": 10,
    "silver": 11,
    "crimson": 12,
}

PALETTES = [
    ["red", "orange", "yellow"],           # Warm
    ["cyan", "blue", "white"],             # Cool
    ["magenta", "pink", "white"],          # Pink
    ["gold", "yellow", "white"],           # Golden
    ["green", "cyan", "white"],            # Emerald
    ["crimson", "red", "gold"],            # Fire
    ["silver", "white", "cyan"],            # Ice
    ["magenta", "blue", "cyan"],            # Nebula
    ["gold", "red", "orange"],             # Sunset
    ["pink", "magenta", "white"],          # Blossom
]

FIREWORK_CHARS = {
    "peony": ["*", "+", ".", "x"],
    "chrysanthemum": ["*", "~", "-", "·"],
    "willow": [".", ",", "·", "~"],
    "palm": ["|", "/", "\\", "*"],
    "crossette": ["x", "+", "*", "✦"],
    "ring": ["o", "O", "*", "+"],
    "heart": ["♥", "*", "+", "."],
    "spiral": [".", "*", "+", "x"],
}

ROCKET_CHARS = ["|", "!", "¡", "│"]
TRAIL_CHARS = [".", "·", ":", "░", "▒"]


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: str
    char: str
    life: float
    max_life: float
    trail: List[Tuple[float, float, str, float]] = field(default_factory=list)
    trail_type: TrailType = TrailType.SHORT
    gravity: float = 0.08
    drag: float = 0.985
    secondary: bool = False  # For secondary explosions (crossette)

    def update(self, dt: float = 1.0):
        # Record trail position
        if self.trail_type != TrailType.NONE:
            trail_len = {TrailType.SHORT: 3, TrailType.MEDIUM: 5, TrailType.LONG: 8}[self.trail_type]
            self.trail.append((self.x, self.y, self.char, self.life / self.max_life))
            if len(self.trail) > trail_len:
                self.trail = self.trail[-trail_len:]

        self.vy += self.gravity * dt
        self.vx *= self.drag ** dt
        self.vy *= self.drag ** dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    @property
    def alive(self) -> bool:
        return self.life > 0

    @property
    def alpha(self) -> float:
        return max(0.0, min(1.0, self.life / self.max_life))


@dataclass
class Rocket:
    x: float
    y: float
    vy: float
    target_y: float
    color: str
    char: str = "|"
    trail: List[Tuple[float, float]] = field(default_factory=list)
    fw_type: FireworkType = FireworkType.PEONY
    palette: List[str] = field(default_factory=lambda: PALETTES[0])

    def update(self, dt: float = 1.0):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail = self.trail[-6:]
        self.y += self.vy * dt
        self.vy *= 0.995

    @property
    def reached_target(self) -> bool:
        return self.y <= self.target_y


class FireworksShow:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        self.particles: List[Particle] = []
        self.rockets: List[Rocket] = []
        self.flash_cells: dict = {}  # (x, y) -> (char, color_idx, ttl)
        self.frame = 0
        self.show_mode = "auto"
        self.running = True
        self.show_speed = 1.0

        # Auto show state
        self.next_launch_frame = 5
        self.show_phase = 0
        self.phase_timer = 0

        # Statistics
        self.total_launched = 0
        self.total_particles = 0

        self._init_colors()

    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()

        color_defs = {
            "red": (curses.COLOR_RED, -1),
            "orange": (curses.COLOR_RED, -1),
            "yellow": (curses.COLOR_YELLOW, -1),
            "green": (curses.COLOR_GREEN, -1),
            "cyan": (curses.COLOR_CYAN, -1),
            "blue": (curses.COLOR_BLUE, -1),
            "magenta": (curses.COLOR_MAGENTA, -1),
            "white": (curses.COLOR_WHITE, -1),
            "pink": (curses.COLOR_MAGENTA, -1),
            "gold": (curses.COLOR_YELLOW, -1),
            "silver": (curses.COLOR_WHITE, -1),
            "crimson": (curses.COLOR_RED, -1),
        }

        for name, (fg, bg) in color_defs.items():
            idx = COLOR_MAP[name]
            curses.init_pair(idx, fg, bg)

    def _get_color_attr(self, color: str, alpha: float = 1.0) -> int:
        idx = COLOR_MAP.get(color, 8)
        return curses.color_pair(idx) | (curses.A_BOLD if alpha > 0.5 else curses.A_NORMAL)

    def launch_rocket(self, x: Optional[float] = None, fw_type: Optional[FireworkType] = None):
        if x is None:
            x = random.uniform(self.width * 0.15, self.width * 0.85)
        if fw_type is None:
            fw_type = random.choice(list(FireworkType))

        target_y = random.uniform(self.height * 0.1, self.height * 0.4)
        vy = random.uniform(-2.5, -1.8)
        palette = random.choice(PALETTES)
        color = random.choice(palette)

        rocket = Rocket(x=x, y=self.height - 1, vy=vy, target_y=target_y,
                        color=color, char=random.choice(ROCKET_CHARS),
                        fw_type=fw_type, palette=palette)
        self.rockets.append(rocket)
        self.total_launched += 1

    def explode(self, rocket: Rocket):
        fw_type = rocket.fw_type
        palette = rocket.palette
        cx, cy = rocket.x, rocket.y
        chars = FIREWORK_CHARS.get(fw_type.value, ["*", "+", ".", "x"])

        if fw_type == FireworkType.PEONY:
            self._burst_sphere(cx, cy, palette, chars, count=random.randint(40, 70),
                              speed=random.uniform(0.8, 1.5), trail=TrailType.SHORT)

        elif fw_type == FireworkType.CHRYSANTHEMUM:
            self._burst_sphere(cx, cy, palette, chars, count=random.randint(50, 80),
                              speed=random.uniform(1.2, 2.0), trail=TrailType.LONG)

        elif fw_type == FireworkType.WILLOW:
            self._burst_sphere(cx, cy, palette, chars, count=random.randint(30, 50),
                              speed=random.uniform(0.6, 1.2), trail=TrailType.LONG,
                              gravity=0.15, drag=0.97, life_mult=2.0)

        elif fw_type == FireworkType.PALM:
            self._burst_streams(cx, cy, palette, chars, streams=random.randint(5, 10),
                               speed=random.uniform(1.5, 2.5), trail=TrailType.LONG)

        elif fw_type == FireworkType.CROSSETTE:
            self._burst_sphere(cx, cy, palette, chars, count=random.randint(20, 30),
                              speed=random.uniform(1.0, 1.8), trail=TrailType.MEDIUM,
                              secondary=True)

        elif fw_type == FireworkType.RING:
            self._burst_ring(cx, cy, palette, chars, count=random.randint(30, 50),
                            radius=random.uniform(4, 8), trail=TrailType.SHORT)

        elif fw_type == FireworkType.HEART:
            self._burst_heart(cx, cy, palette, chars, count=60, trail=TrailType.SHORT)

        elif fw_type == FireworkType.SPIRAL:
            self._burst_spiral(cx, cy, palette, chars, count=random.randint(40, 60),
                              trail=TrailType.MEDIUM)

        # Flash effect at center
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                self.flash_cells[(int(cx) + dx, int(cy) + dy)] = (
                    random.choice(["✦", "✧", "*", "★"]),
                    COLOR_MAP.get(random.choice(palette), 8),
                    4
                )

    def _burst_sphere(self, cx, cy, palette, chars, count, speed, trail, gravity=0.08, drag=0.985, life_mult=1.0, secondary=False):
        for i in range(count):
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(speed * 0.3, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd * 0.6  # Squish vertically for terminal aspect ratio
            life = random.uniform(25, 45) * life_mult
            color = random.choice(palette)
            char = random.choice(chars)
            self.particles.append(Particle(
                x=cx + random.uniform(-0.5, 0.5),
                y=cy + random.uniform(-0.5, 0.5),
                vx=vx, vy=vy, color=color, char=char,
                life=life, max_life=life,
                trail_type=trail, gravity=gravity, drag=drag,
                secondary=secondary
            ))
            self.total_particles += 1

    def _burst_streams(self, cx, cy, palette, chars, streams, speed, trail):
        for i in range(streams):
            angle = (2 * math.pi * i / streams) + random.uniform(-0.1, 0.1)
            for j in range(random.randint(4, 8)):
                spd = speed * random.uniform(0.5, 1.0) * (1 - j * 0.08)
                vx = math.cos(angle) * spd
                vy = math.sin(angle) * spd * 0.6
                life = random.uniform(25, 45)
                color = random.choice(palette)
                char = random.choice(chars)
                self.particles.append(Particle(
                    x=cx, y=cy, vx=vx, vy=vy, color=color, char=char,
                    life=life, max_life=life, trail_type=trail
                ))
                self.total_particles += 1

    def _burst_ring(self, cx, cy, palette, chars, count, radius, trail):
        for i in range(count):
            angle = 2 * math.pi * i / count
            spd = radius * 0.06
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd * 0.6
            # Start at ring radius
            px = cx + math.cos(angle) * radius
            py = cy + math.sin(angle) * radius * 0.6
            life = random.uniform(20, 35)
            color = random.choice(palette)
            char = random.choice(chars)
            self.particles.append(Particle(
                x=px, y=py, vx=vx * 0.3, vy=vy * 0.3,
                color=color, char=char, life=life, max_life=life,
                trail_type=trail, gravity=0.04
            ))
            self.total_particles += 1

    def _burst_heart(self, cx, cy, palette, chars, count, trail):
        for i in range(count):
            t = 2 * math.pi * i / count
            # Heart parametric equation
            hx = 16 * math.sin(t) ** 3
            hy = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
            scale = 0.35
            px = cx + hx * scale
            py = cy + hy * scale * 0.7
            life = random.uniform(25, 40)
            color = random.choice(palette)
            char = random.choice(chars)
            self.particles.append(Particle(
                x=cx, y=cy,
                vx=(px - cx) * 0.08, vy=(py - cy) * 0.08,
                color=color, char=char, life=life, max_life=life,
                trail_type=trail, gravity=0.03
            ))
            self.total_particles += 1

    def _burst_spiral(self, cx, cy, palette, chars, count, trail):
        for i in range(count):
            t = i / count * 4 * math.pi
            r = (i / count) * 8
            vx = math.cos(t) * r * 0.08
            vy = math.sin(t) * r * 0.08 * 0.6
            # Add some initial outward velocity
            angle = math.atan2(vy, vx)
            spd = math.sqrt(vx**2 + vy**2) + 0.5
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            life = random.uniform(25, 45)
            color = random.choice(palette)
            char = random.choice(chars)
            self.particles.append(Particle(
                x=cx, y=cy, vx=vx, vy=vy,
                color=color, char=char, life=life, max_life=life,
                trail_type=trail, gravity=0.05, drag=0.99
            ))
            self.total_particles += 1

    def _secondary_explosion(self, particle: Particle):
        """Create a small secondary explosion (for crossette type)."""
        palette = PALETTES[0]  # Use a random palette
        actual_palette = random.choice(PALETTES)
        for _ in range(random.randint(6, 12)):
            angle = random.uniform(0, 2 * math.pi)
            spd = random.uniform(0.3, 0.8)
            life = random.uniform(10, 20)
            self.particles.append(Particle(
                x=particle.x, y=particle.y,
                vx=math.cos(angle) * spd,
                vy=math.sin(angle) * spd * 0.6,
                color=random.choice(actual_palette),
                char=random.choice(["+", "*", "·"]),
                life=life, max_life=life,
                trail_type=TrailType.NONE, gravity=0.06
            ))
            self.total_particles += 1

    def auto_show_tick(self):
        """Run choreographed auto show."""
        self.phase_timer += 1

        # Phase system for varied show
        if self.phase_timer > random.randint(80, 200):
            self.phase_timer = 0
            self.phase = (self.phase + 1) % 5

        if self.frame >= self.next_launch_frame:
            phase = self.phase

            if phase == 0:
                # Single random fireworks
                self.launch_rocket()
                self.next_launch_frame = self.frame + random.randint(15, 35)

            elif phase == 1:
                # Rapid fire
                self.launch_rocket()
                self.next_launch_frame = self.frame + random.randint(5, 12)

            elif phase == 2:
                # Grand finale - multiple simultaneous
                for _ in range(random.randint(2, 5)):
                    self.launch_rocket()
                self.next_launch_frame = self.frame + random.randint(20, 40)

            elif phase == 3:
                # Synchronized line
                x_base = random.uniform(self.width * 0.2, self.width * 0.5)
                for i in range(3):
                    self.launch_rocket(x=x_base + i * (self.width * 0.1),
                                       fw_type=random.choice([FireworkType.PEONY, FireworkType.CHRYSANTHEMUM]))
                self.next_launch_frame = self.frame + random.randint(30, 50)

            elif phase == 4:
                # Hearts and rings
                self.launch_rocket(fw_type=random.choice([FireworkType.HEART, FireworkType.RING]))
                self.next_launch_frame = self.frame + random.randint(20, 35)

    def update(self):
        self.frame += 1

        # Update rockets
        exploded = []
        for rocket in self.rockets:
            rocket.update()
            if rocket.reached_target:
                self.explode(rocket)
                exploded.append(rocket)
        for r in exploded:
            self.rockets.remove(r)

        # Update particles
        dead = []
        for p in self.particles:
            p.update()
            if not p.alive:
                # Check for secondary explosion (crossette)
                if p.secondary and p.alpha < 0.3:
                    self._secondary_explosion(p)
                dead.append(p)
        for p in dead:
            self.particles.remove(p)

        # Update flash cells
        dead_flashes = []
        for pos, (char, color, ttl) in self.flash_cells.items():
            if ttl <= 0:
                dead_flashes.append(pos)
            else:
                self.flash_cells[pos] = (char, color, ttl - 1)
        for pos in dead_flashes:
            del self.flash_cells[pos]

        # Auto show
        if self.show_mode == "auto":
            self.auto_show_tick()

    def render(self):
        self.stdscr.erase()

        # Draw particle trails and particles
        for p in self.particles:
            alpha = p.alpha
            if alpha < 0.05:
                continue

            # Draw trail
            for i, (tx, ty, tchar, talpha) in enumerate(p.trail):
                if talpha < 0.1:
                    continue
                ix, iy = int(tx), int(ty)
                if 0 <= ix < self.width and 0 <= iy < self.height:
                    trail_alpha = talpha * (i + 1) / len(p.trail) * 0.5
                    if trail_alpha > 0.15:
                        char = random.choice(TRAIL_CHARS) if random.random() < 0.3 else "·"
                        try:
                            self.stdscr.addch(iy, ix, char, self._get_color_attr(p.color, trail_alpha))
                        except curses.error:
                            pass

            # Draw particle
            ix, iy = int(p.x), int(p.y)
            if 0 <= ix < self.width and 0 <= iy < self.height:
                char = p.char if alpha > 0.3 else "."
                try:
                    self.stdscr.addch(iy, ix, char, self._get_color_attr(p.color, alpha))
                except curses.error:
                    pass

        # Draw rocket trails and rockets
        for rocket in self.rockets:
            # Trail
            for i, (tx, ty) in enumerate(rocket.trail):
                ix, iy = int(tx), int(ty)
                if 0 <= ix < self.width and 0 <= iy < self.height:
                    trail_char = TRAIL_CHARS[min(i, len(TRAIL_CHARS)-1)]
                    try:
                        self.stdscr.addch(iy, ix, trail_char, self._get_color_attr(rocket.color, 0.5))
                    except curses.error:
                        pass
            # Rocket head
            ix, iy = int(rocket.x), int(rocket.y)
            if 0 <= ix < self.width and 0 <= iy < self.height:
                try:
                    self.stdscr.addch(iy, ix, rocket.char, self._get_color_attr(rocket.color, 1.0) | curses.A_BOLD)
                except curses.error:
                    pass

        # Draw flash cells
        for (fx, fy), (char, color, ttl) in self.flash_cells.items():
            if 0 <= fx < self.width and 0 <= fy < self.height:
                alpha = ttl / 4.0
                try:
                    self.stdscr.addch(fy, fx, char, curses.color_pair(color) | curses.A_BOLD)
                except curses.error:
                    pass

        # Draw HUD
        hud = f" 🎆 Particles: {len(self.particles):4d} | Launched: {self.total_launched:3d} | [SPACE] Launch  [A] Auto  [Q] Quit "
        try:
            self.stdscr.addstr(0, 0, hud[:self.width-1], curses.color_pair(8) | curses.A_REVERSE)
        except curses.error:
            pass

        # Draw ground
        ground_y = self.height - 1
        ground_char = "▀"
        try:
            for x in range(self.width):
                self.stdscr.addch(ground_y, x, ground_char, curses.color_pair(2))
        except curses.error:
            pass

        self.stdscr.refresh()

    def handle_input(self):
        self.stdscr.nodelay(1)
        key = self.stdscr.getch()

        if key == ord('q') or key == ord('Q'):
            self.running = False
        elif key == ord(' '):
            self.launch_rocket()
        elif key == ord('a') or key == ord('A'):
            self.show_mode = "auto" if self.show_mode != "auto" else "manual"
        elif key == ord('1'):
            self.launch_rocket(fw_type=FireworkType.PEONY)
        elif key == ord('2'):
            self.launch_rocket(fw_type=FireworkType.CHRYSANTHEMUM)
        elif key == ord('3'):
            self.launch_rocket(fw_type=FireworkType.WILLOW)
        elif key == ord('4'):
            self.launch_rocket(fw_type=FireworkType.PALM)
        elif key == ord('5'):
            self.launch_rocket(fw_type=FireworkType.CROSSETTE)
        elif key == ord('6'):
            self.launch_rocket(fw_type=FireworkType.RING)
        elif key == ord('7'):
            self.launch_rocket(fw_type=FireworkType.HEART)
        elif key == ord('8'):
            self.launch_rocket(fw_type=FireworkType.SPIRAL)
        elif key == ord('f'):
            # Grand finale burst
            for _ in range(random.randint(5, 10)):
                self.launch_rocket()

    def run(self):
        curses.curs_set(0)
        self.stdscr.timeout(30)

        while self.running:
            self.handle_input()
            self.update()
            self.render()
            time.sleep(0.03)


def main(stdscr):
    show = FireworksShow(stdscr)
    show.run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        print("\n🎆 Thanks for watching the fireworks show!")