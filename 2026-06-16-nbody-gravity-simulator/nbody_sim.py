#!/usr/bin/env python3
"""
N-Body Gravity Simulator — Terminal-based gravitational N-body simulation.

Bodies interact via Newtonian gravity. Watch orbits, collisions, slingshots,
and chaotic dynamics unfold in your terminal with colored trails.

Controls:
  Left Click   — Spawn a body (drag to set velocity)
  Right Click  — Spawn a massive "star" body
  1/2/3        — Load preset scenes (solar system / binary star / figure-8)
  SPACE        — Pause / Resume
  T            — Toggle trails
  G            — Toggle grid
  F            — Toggle center-of-mass tracking
  D            — Delete nearest body to last mouse position
  +/-          — Speed up / Slow down simulation
  R            — Reset to default scene
  C            — Clear all bodies
  H            — Toggle help overlay
  Q / ESC      — Quit
"""

import argparse
import math
import random
import sys
import time

try:
    import curses
except ImportError:
    print("curses is required. Install it or use a terminal that supports it.")
    sys.exit(1)


# ─── Version ─────────────────────────────────────────────────────────────────

__version__ = "1.1.0"

# ─── Constants ───────────────────────────────────────────────────────────────

G = 1.0                # Gravitational constant (simulation units)
SOFTENING = 0.5        # Softening parameter to avoid singularities
DT_BASE = 0.05         # Base timestep per frame
MAX_TRAIL = 120        # Max trail points per body
MAX_BODIES = 80         # Performance cap
COLLISION_DIST = 0.8    # Base merge distance

# ─── Color palette (curses color pairs) ──────────────────────────────────────

BODY_COLORS = [
    (196, "red"),
    (202, "orange"),
    (226, "yellow"),
    (46,  "green"),
    (51,  "cyan"),
    (33,  "blue"),
    (201, "magenta"),
    (213, "pink"),
    (255, "white"),
    (248, "gray"),
]

# ─── Body ────────────────────────────────────────────────────────────────────


class Body:
    """A single gravitational body with position, velocity, mass, and trail."""

    __slots__ = ("x", "y", "vx", "vy", "mass", "color_idx", "trail", "alive")

    def __init__(self, x: float, y: float, vx: float = 0.0, vy: float = 0.0,
                 mass: float = 1.0, color_idx: int | None = None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.mass = mass
        self.color_idx = color_idx if color_idx is not None else random.randint(0, len(BODY_COLORS) - 1)
        self.trail: list[tuple[float, float]] = []
        self.alive = True

    def radius_display(self) -> int:
        """Visual radius based on mass (for rendering)."""
        if self.mass >= 50:
            return 2
        if self.mass >= 10:
            return 1
        return 0

    def char(self) -> str:
        """Unicode character representing body mass tier."""
        if self.mass >= 100:
            return "★"
        if self.mass >= 50:
            return "✦"
        if self.mass >= 10:
            return "●"
        if self.mass >= 3:
            return "◆"
        return "·"

    def kinetic_energy(self) -> float:
        """KE = 0.5 * m * v^2"""
        return 0.5 * self.mass * (self.vx ** 2 + self.vy ** 2)


# ─── Simulation ──────────────────────────────────────────────────────────────


class Simulation:
    """Core N-body gravitational simulation engine."""

    def __init__(self, width: int, height: int):
        self.bodies: list[Body] = []
        self.width = width
        self.height = height
        self.paused = False
        self.show_trails = True
        self.show_grid = False
        self.show_help = False
        self.show_energy = True
        self.follow_com = False  # Follow center of mass
        self.speed_mult = 1.0
        self.total_mass_initial = 0.0
        self.collision_count = 0
        self.frame = 0
        # Camera offset (world coords mapped to screen center)
        self.cam_x = width / 2.0
        self.cam_y = height / 2.0
        # Camera offset for center-of-mass tracking
        self.cam_offset_x = 0.0
        self.cam_offset_y = 0.0
        # Drag state for spawning
        self.dragging = False
        self.drag_start: tuple[int, int] | None = None
        self.drag_is_star = False
        # Last mouse position (for delete-nearest)
        self.last_mouse_x = 0
        self.last_mouse_y = 0

    def add_default_scene(self) -> None:
        """Create a simple solar-system-like scene."""
        cx, cy = self.cam_x, self.cam_y
        # Central star
        star = Body(cx, cy, 0, 0, mass=200, color_idx=2)
        self.bodies.append(star)
        # Planets at various distances
        planets = [
            (12, 0.8, 46),   # (distance, mass, color_idx)
            (20, 1.5, 33),
            (30, 2.0, 201),
            (42, 0.6, 51),
            (55, 3.0, 196),
        ]
        for dist, mass, cidx in planets:
            angle = random.uniform(0, 2 * math.pi)
            px = cx + dist * math.cos(angle)
            py = cy + dist * math.sin(angle)
            # Circular orbit velocity: v = sqrt(G*M/r)
            v_orb = math.sqrt(G * star.mass / dist)
            # Tangential direction (perpendicular to radius)
            direction = 1 if random.random() > 0.3 else -1
            vx = -direction * v_orb * math.sin(angle)
            vy = direction * v_orb * math.cos(angle)
            b = Body(px, py, vx, vy, mass=mass, color_idx=cidx)
            self.bodies.append(b)

        self.total_mass_initial = sum(b.mass for b in self.bodies)

    def add_binary_star_scene(self) -> None:
        """Create a binary star system with orbiting planets."""
        cx, cy = self.cam_x, self.cam_y
        sep = 15  # Separation between stars
        # Two stars orbiting each other
        mass_star = 100.0
        v_orb = math.sqrt(G * mass_star / (2 * sep)) * 0.7
        star1 = Body(cx - sep / 2, cy, 0, -v_orb, mass=mass_star, color_idx=196)
        star2 = Body(cx + sep / 2, cy, 0, v_orb, mass=mass_star, color_idx=226)
        self.bodies.extend([star1, star2])
        # A few small planets
        for _ in range(6):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(25, 45)
            px = cx + dist * math.cos(angle)
            py = cy + dist * math.sin(angle)
            v = math.sqrt(G * 200 / dist) * random.uniform(0.8, 1.2)
            vx = -v * math.sin(angle)
            vy = v * math.cos(angle)
            self.bodies.append(Body(px, py, vx, vy, mass=random.uniform(0.5, 3.0)))

        self.total_mass_initial = sum(b.mass for b in self.bodies)

    def add_figure_eight_scene(self) -> None:
        """Create the famous figure-8 three-body solution.

        Uses the initial conditions discovered by Chenciner & Montgomery (2000).
        Positions and velocities are scaled for our simulation units.
        """
        cx, cy = self.cam_x, self.cam_y
        scale = 15.0  # Spatial scale
        mass = 30.0    # Mass of each body

        # Figure-8 initial conditions (normalized)
        # Body 1 at top-right, Body 2 at top-left, Body 3 at bottom
        x1 = 0.97000436 * scale + cx
        y1 = -0.24308753 * scale + cy
        x2 = -x1 + 2 * cx  # Mirror of body 1
        y2 = -y1 + 2 * cy
        x3 = cx
        y3 = cy

        # Velocities (body 3 gets double velocity, others have negative of half)
        v_scale = 2.5
        vx3 = -0.93240737 * v_scale
        vy3 = -0.86473146 * v_scale
        vx1 = -vx3 / 2
        vy1 = -vy3 / 2
        vx2 = -vx3 / 2
        vy2 = -vy3 / 2

        b1 = Body(x1, y1, vx1, vy1, mass=mass, color_idx=46)
        b2 = Body(x2, y2, vx2, vy2, mass=mass, color_idx=51)
        b3 = Body(x3, y3, vx3, vy3, mass=mass, color_idx=196)
        self.bodies.extend([b1, b2, b3])
        self.total_mass_initial = sum(b.mass for b in self.bodies)

    def add_cluster_scene(self) -> None:
        """Create a random cluster of bodies — chaotic gravitational collapse."""
        cx, cy = self.cam_x, self.cam_y
        n = min(25, MAX_BODIES)
        for i in range(n):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(2, 20)
            px = cx + dist * math.cos(angle)
            py = cy + dist * math.sin(angle)
            vx = random.uniform(-0.3, 0.3)
            vy = random.uniform(-0.3, 0.3)
            mass = random.choice([0.5, 1.0, 1.5, 2.0, 5.0])
            self.bodies.append(Body(px, py, vx, vy, mass=mass))
        self.total_mass_initial = sum(b.mass for b in self.bodies)

    def compute_energy(self) -> tuple[float, float, float]:
        """Compute kinetic, potential, and total energy of the system."""
        ke = sum(b.kinetic_energy() for b in self.bodies)
        pe = 0.0
        n = len(self.bodies)
        for i in range(n):
            bi = self.bodies[i]
            for j in range(i + 1, n):
                bj = self.bodies[j]
                dx = bj.x - bi.x
                dy = bj.y - bi.y
                dist = math.sqrt(dx * dx + dy * dy + SOFTENING * SOFTENING)
                pe -= G * bi.mass * bj.mass / dist
        return ke, pe, ke + pe

    def center_of_mass(self) -> tuple[float, float]:
        """Compute the center of mass of all bodies."""
        if not self.bodies:
            return self.cam_x, self.cam_y
        total_mass = sum(b.mass for b in self.bodies)
        if total_mass == 0:
            return self.cam_x, self.cam_y
        cx = sum(b.x * b.mass for b in self.bodies) / total_mass
        cy = sum(b.y * b.mass for b in self.bodies) / total_mass
        return cx, cy

    def delete_nearest(self, sx: int, sy: int) -> bool:
        """Delete the body nearest to screen coordinates (sx, sy).

        Returns True if a body was deleted, False otherwise.
        """
        if not self.bodies:
            return False
        best_body = None
        best_dist = float("inf")
        for b in self.bodies:
            dx = b.x - sx
            dy = b.y - sy
            d = dx * dx + dy * dy
            if d < best_dist:
                best_dist = d
                best_body = b
        if best_body is not None and best_dist < 400:  # Within ~20 units
            best_body.alive = False
            self.bodies = [b for b in self.bodies if b.alive]
            return True
        return False

    def step(self, dt: float | None = None) -> None:
        """Advance simulation by one timestep.

        Args:
            dt: Timestep to use. If None, uses DT_BASE * speed_mult.
        """
        if self.paused:
            return

        if dt is None:
            dt = DT_BASE * self.speed_mult

        bodies = self.bodies
        n = len(bodies)
        if n == 0:
            return

        # Compute accelerations (O(n^2))
        ax = [0.0] * n
        ay = [0.0] * n
        for i in range(n):
            bi = bodies[i]
            if not bi.alive:
                continue
            for j in range(i + 1, n):
                bj = bodies[j]
                if not bj.alive:
                    continue
                dx = bj.x - bi.x
                dy = bj.y - bi.y
                dist_sq = dx * dx + dy * dy + SOFTENING * SOFTENING
                dist = math.sqrt(dist_sq)
                force = G * bi.mass * bj.mass / dist_sq
                fx = force * dx / dist
                fy = force * dy / dist
                ax[i] += fx / bi.mass
                ay[i] += fy / bi.mass
                ax[j] -= fx / bj.mass
                ay[j] -= fy / bj.mass

        # Update velocities and positions (symplectic Euler)
        for i in range(n):
            bi = bodies[i]
            if not bi.alive:
                continue
            bi.vx += ax[i] * dt
            bi.vy += ay[i] * dt
            bi.x += bi.vx * dt
            bi.y += bi.vy * dt
            # Record trail
            bi.trail.append((bi.x, bi.y))
            if len(bi.trail) > MAX_TRAIL:
                bi.trail.pop(0)

        # Collision detection & merging
        for i in range(n):
            bi = bodies[i]
            if not bi.alive:
                continue
            for j in range(i + 1, n):
                bj = bodies[j]
                if not bj.alive:
                    continue
                # Re-check bi.alive in case it was consumed in a prior merge this frame
                if not bi.alive:
                    break
                dx = bj.x - bi.x
                dy = bj.y - bi.y
                dist = math.sqrt(dx * dx + dy * dy)
                merge_r = COLLISION_DIST * (1 + 0.1 * (bi.radius_display() + bj.radius_display()))
                if dist < merge_r:
                    # Merge into the heavier body
                    if bi.mass >= bj.mass:
                        survivor, consumed = bi, bj
                    else:
                        survivor, consumed = bj, bi
                    total = survivor.mass + consumed.mass
                    # Conservation of momentum
                    survivor.vx = (survivor.vx * survivor.mass + consumed.vx * consumed.mass) / total
                    survivor.vy = (survivor.vy * survivor.mass + consumed.vy * consumed.mass) / total
                    # Center-of-mass position
                    survivor.x = (survivor.x * survivor.mass + consumed.x * consumed.mass) / total
                    survivor.y = (survivor.y * survivor.mass + consumed.y * consumed.mass) / total
                    survivor.mass = total
                    consumed.alive = False
                    self.collision_count += 1

        # Remove dead bodies
        self.bodies = [b for b in self.bodies if b.alive]

        # Update camera offset for center-of-mass tracking
        if self.follow_com and self.bodies:
            com_x, com_y = self.center_of_mass()
            self.cam_offset_x = com_x - self.width / 2.0
            self.cam_offset_y = com_y - self.height / 2.0
        else:
            self.cam_offset_x = 0.0
            self.cam_offset_y = 0.0

        self.frame += 1


# ─── Renderer ────────────────────────────────────────────────────────────────


class Renderer:
    """Handles all curses-based rendering for the simulation."""

    def __init__(self, stdscr, sim: Simulation):
        self.stdscr = stdscr
        self.sim = sim
        self.init_colors()

    def init_colors(self) -> None:
        """Initialize curses color pairs."""
        curses.start_color()
        curses.use_default_colors()
        # Pair 1-10: body colors
        for i, (cnum, _) in enumerate(BODY_COLORS):
            curses.init_pair(i + 1, cnum, -1)
        # Pair 11: grid
        curses.init_pair(11, 240, -1)
        # Pair 12: UI text
        curses.init_pair(12, 248, -1)
        # Pair 13: help text
        curses.init_pair(13, 252, -1)
        # Pair 14: drag arrow
        curses.init_pair(14, 226, -1)
        # Pair 15: velocity preview
        curses.init_pair(15, 46, -1)
        # Pair 16: energy bar
        curses.init_pair(16, 214, -1)
        # Pair 17: center-of-mass marker
        curses.init_pair(17, 244, -1)

    def world_to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        """Convert world coordinates to screen coordinates, applying camera offset."""
        ox = self.sim.cam_offset_x
        oy = self.sim.cam_offset_y
        sx = int(round(wx - ox))
        sy = int(round(wy - oy))
        return sx, sy

    def clamp(self, sx: int, sy: int) -> tuple[int, int]:
        """Clamp screen coordinates to stay within the terminal."""
        sy = max(0, min(self.sim.height - 1, sy))
        sx = max(0, min(self.sim.width - 1, sx))
        return sx, sy

    def draw(self, drag_info: tuple | None = None) -> None:
        """Render the full simulation frame."""
        stdscr = self.stdscr
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        self.sim.height = h
        self.sim.width = w

        # Grid
        if self.sim.show_grid:
            self._draw_grid(h, w)

        # Center-of-mass marker
        if self.sim.follow_com and self.sim.bodies:
            com_x, com_y = self.sim.center_of_mass()
            sx, sy = self.world_to_screen(com_x, com_y)
            sx, sy = self.clamp(sx, sy)
            try:
                stdscr.addch(sy, sx, ord("+"), curses.color_pair(17))
            except curses.error:
                pass

        # Trails
        if self.sim.show_trails:
            self._draw_trails()

        # Bodies
        self._draw_bodies()

        # Drag arrow (velocity preview)
        if drag_info is not None:
            self._draw_drag_arrow(drag_info)

        # HUD
        self._draw_hud()

        # Energy display
        if self.sim.show_energy:
            self._draw_energy()

        # Help overlay
        if self.sim.show_help:
            self._draw_help()

        stdscr.refresh()

    def _draw_grid(self, h: int, w: int) -> None:
        """Draw a background grid."""
        stdscr = self.stdscr
        for y in range(0, h, 5):
            for x in range(0, w, 10):
                try:
                    stdscr.addch(y, x, ord("."), curses.color_pair(11))
                except curses.error:
                    pass

    def _draw_trails(self) -> None:
        """Draw fading trails for all bodies."""
        stdscr = self.stdscr
        for body in self.sim.bodies:
            trail = body.trail
            tlen = len(trail)
            if tlen < 2:
                continue
            cpair = curses.color_pair(body.color_idx + 1)
            # Draw every Nth point for performance
            step = max(1, tlen // 60)
            for k in range(0, tlen, step):
                tx, ty = trail[k]
                sx, sy = self.world_to_screen(tx, ty)
                sx, sy = self.clamp(sx, sy)
                # Fade: earlier points dimmer
                fade = k / tlen
                if fade < 0.3:
                    ch = ord("·")
                elif fade < 0.7:
                    ch = ord("∙")
                else:
                    ch = ord("°")
                try:
                    stdscr.addch(sy, sx, ch, cpair)
                except curses.error:
                    pass

    def _draw_bodies(self) -> None:
        """Draw all bodies with glow effects for massive ones."""
        stdscr = self.stdscr
        for body in self.sim.bodies:
            sx, sy = self.world_to_screen(body.x, body.y)
            sx, sy = self.clamp(sx, sy)
            cpair = curses.color_pair(body.color_idx + 1)
            ch = body.char()
            try:
                stdscr.addstr(sy, sx, ch, cpair | curses.A_BOLD)
            except curses.error:
                pass
            # Glow for large bodies
            if body.mass >= 50:
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    gx, gy = sx + dx, sy + dy
                    gx, gy = self.clamp(gx, gy)
                    try:
                        stdscr.addch(gy, gx, ord("░"), cpair)
                    except curses.error:
                        pass

    def _draw_drag_arrow(self, drag_info: tuple) -> None:
        """Draw velocity preview arrow while dragging."""
        stdscr = self.stdscr
        sx, sy, ex, ey, is_star = drag_info
        cpair = curses.color_pair(14) if is_star else curses.color_pair(15)
        self._draw_line(sx, sy, ex, ey, ord("→"), cpair)
        try:
            stdscr.addstr(sy, sx, "✦" if is_star else "●", cpair | curses.A_BOLD)
        except curses.error:
            pass

    def _draw_energy(self) -> None:
        """Display energy statistics on the bottom-right."""
        stdscr = self.stdscr
        h, w = stdscr.getmaxyx()
        ke, pe, te = self.sim.compute_energy()
        lines = [
            f"KE:{ke:>8.1f}",
            f"PE:{pe:>8.1f}",
            f"TE:{te:>8.1f}",
        ]
        for i, line in enumerate(lines):
            row = h - 1 - (len(lines) - 1 - i)
            if row > 2 and row < h:
                col = max(0, w - len(line) - 2)
                try:
                    stdscr.addstr(row, col, line, curses.color_pair(16))
                except curses.error:
                    pass

    def _draw_line(self, x0: int, y0: int, x1: int, y1: int,
                   ch: int, cpair: int) -> None:
        """Draw a line using Bresenham's algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            cx, cy = self.clamp(x0, y0)
            try:
                self.stdscr.addch(cy, cx, ch, cpair)
            except curses.error:
                pass
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def _draw_hud(self) -> None:
        """Draw the heads-up display at the top of the screen."""
        stdscr = self.stdscr
        h, w = stdscr.getmaxyx()
        sim = self.sim
        total_mass = sum(b.mass for b in sim.bodies)
        com_str = " [COM]" if sim.follow_com else ""
        status = "PAUSED" if sim.paused else "RUNNING"
        lines = [
            f" Bodies:{len(sim.bodies)} Mass:{total_mass:.1f} "
            f"Collisions:{sim.collision_count} Speed:{sim.speed_mult:.1f}x "
            f"Frame:{sim.frame}{com_str}",
            f" {status} | SPACE=pause T=trails G=grid F=follow "
            f"D=delete H=help Click=spawn R=reset 1/2/3=presets Q=quit",
        ]
        for i, line in enumerate(lines):
            if i < h - 1:
                try:
                    stdscr.addstr(i, 0, line[:w], curses.color_pair(12))
                except curses.error:
                    pass

    def _draw_help(self) -> None:
        """Draw the help overlay in the center of the screen."""
        stdscr = self.stdscr
        h, w = stdscr.getmaxyx()
        help_text = [
            "╔══════════════════════════════════════════╗",
            "║      N-BODY GRAVITY SIMULATOR  v1.1      ║",
            "╠══════════════════════════════════════════╣",
            "║  Left Click   Spawn body (drag→vel)      ║",
            "║  Right Click  Spawn massive star          ║",
            "║  1            Solar system scene          ║",
            "║  2            Binary star scene           ║",
            "║  3            Figure-8 three-body         ║",
            "║  SPACE        Pause / Resume             ║",
            "║  T            Toggle trails               ║",
            "║  G            Toggle grid                 ║",
            "║  F            Follow center of mass       ║",
            "║  D            Delete nearest body         ║",
            "║  E            Toggle energy display       ║",
            "║  + / -        Speed up / down             ║",
            "║  R            Reset scene                 ║",
            "║  C            Clear all bodies             ║",
            "║  H            Toggle this help             ║",
            "║  Q / ESC      Quit                        ║",
            "╠══════════════════════════════════════════╣",
            "║  Newtonian gravity · Colliding bodies    ║",
            "║  merge with momentum conservation.        ║",
            "║  Drag to set initial velocity.            ║",
            "╚══════════════════════════════════════════╝",
        ]
        top = max(3, (h - len(help_text)) // 2)
        left = max(0, (w - len(help_text[0])) // 2)
        for i, line in enumerate(help_text):
            if top + i < h - 1:
                try:
                    stdscr.addstr(top + i, left, line[:w], curses.color_pair(13) | curses.A_BOLD)
                except curses.error:
                    pass


# ─── Main loop ────────────────────────────────────────────────────────────────


def main(stdscr) -> None:
    """Main application entry point wrapped by curses."""
    curses.curs_set(0)       # Hide cursor
    stdscr.nodelay(True)     # Non-blocking input
    stdscr.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
    curses.noecho()

    h, w = stdscr.getmaxyx()
    sim = Simulation(w, h)
    sim.add_default_scene()
    renderer = Renderer(stdscr, sim)

    # Enable mouse wheel if terminal supports it
    try:
        curses.mouseinterval(0)
    except Exception:
        pass

    drag_start_screen: tuple[int, int] | None = None
    drag_is_star = False
    running = True

    while running:
        # ── Input ────────────────────────────────────────────────────────
        try:
            key = stdscr.getch()
        except Exception:
            key = -1

        drag_info = None

        if key == ord("q") or key == 27:  # Q or ESC
            running = False
            continue

        elif key == ord(" "):
            sim.paused = not sim.paused

        elif key == ord("t"):
            sim.show_trails = not sim.show_trails

        elif key == ord("g"):
            sim.show_grid = not sim.show_grid

        elif key == ord("h"):
            sim.show_help = not sim.show_help

        elif key == ord("e"):
            sim.show_energy = not sim.show_energy

        elif key == ord("f"):
            sim.follow_com = not sim.follow_com
            if not sim.follow_com:
                sim.cam_offset_x = 0.0
                sim.cam_offset_y = 0.0

        elif key == ord("d"):
            sim.delete_nearest(sim.last_mouse_x, sim.last_mouse_y)

        elif key == ord("r"):
            sim.bodies.clear()
            sim.collision_count = 0
            sim.frame = 0
            sim.follow_com = False
            sim.cam_offset_x = 0.0
            sim.cam_offset_y = 0.0
            sim.add_default_scene()

        elif key == ord("c"):
            sim.bodies.clear()
            sim.collision_count = 0

        elif key == ord("+") or key == ord("="):
            sim.speed_mult = min(sim.speed_mult * 1.5, 20.0)

        elif key == ord("-") or key == ord("_"):
            sim.speed_mult = max(sim.speed_mult / 1.5, 0.1)

        # Preset scenes
        elif key == ord("1"):
            sim.bodies.clear()
            sim.collision_count = 0
            sim.follow_com = False
            sim.cam_offset_x = 0.0
            sim.cam_offset_y = 0.0
            sim.add_default_scene()

        elif key == ord("2"):
            sim.bodies.clear()
            sim.collision_count = 0
            sim.follow_com = False
            sim.cam_offset_x = 0.0
            sim.cam_offset_y = 0.0
            sim.add_binary_star_scene()

        elif key == ord("3"):
            sim.bodies.clear()
            sim.collision_count = 0
            sim.follow_com = False
            sim.cam_offset_x = 0.0
            sim.cam_offset_y = 0.0
            sim.add_figure_eight_scene()

        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
            except Exception:
                mx, my, bstate = 0, 0, 0

            sim.last_mouse_x = mx
            sim.last_mouse_y = my

            if bstate & curses.BUTTON1_PRESSED:
                drag_start_screen = (mx, my)
                drag_is_star = False

            elif bstate & curses.BUTTON3_PRESSED:
                drag_start_screen = (mx, my)
                drag_is_star = True

            elif bstate & curses.BUTTON1_RELEASED or bstate & curses.BUTTON3_RELEASED:
                if drag_start_screen is not None and len(sim.bodies) < MAX_BODIES:
                    sx0, sy0 = drag_start_screen
                    dx = (mx - sx0) * 0.15
                    dy = (my - sy0) * 0.15
                    mass = 200.0 if drag_is_star else random.uniform(0.5, 5.0)
                    cidx = 2 if drag_is_star else random.randint(0, len(BODY_COLORS) - 1)
                    body = Body(sx0, sy0, dx, dy, mass=mass, color_idx=cidx)
                    sim.bodies.append(body)
                drag_start_screen = None
                drag_is_star = False

        # Draw drag preview
        if drag_start_screen is not None:
            try:
                _, mx, my, _, _ = curses.getmouse()
            except Exception:
                mx, my = drag_start_screen
            drag_info = (*drag_start_screen, mx, my, drag_is_star)

        # ── Update ────────────────────────────────────────────────────────
        # Multiple sub-steps for stability at high speed
        # Total simulation time per frame = DT_BASE * speed_mult
        # Split into sub_steps for numerical stability
        sub_steps = max(1, int(sim.speed_mult))
        dt_per_step = DT_BASE * sim.speed_mult / sub_steps
        for _ in range(sub_steps):
            sim.step(dt=dt_per_step)

        # ── Render ────────────────────────────────────────────────────────
        renderer.draw(drag_info=drag_info)

        # Frame timing — target ~30 FPS
        time.sleep(0.033)

    curses.endwin()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="nbody_sim",
        description="N-Body Gravity Simulator — Terminal-based gravitational N-body simulation",
        epilog="Controls: SPACE=pause, T=trails, G=grid, F=follow COM, "
               "D=delete, 1/2/3=presets, R=reset, C=clear, H=help, Q=quit"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--scene", choices=["solar", "binary", "figure8", "cluster"],
        default="solar",
        help="Starting scene preset (default: solar)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    # Select starting scene
    scene_map = {
        "solar": "default",
        "binary": "binary",
        "figure8": "figure8",
        "cluster": "cluster",
    }

    def main_with_args(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        curses.noecho()

        h, w = stdscr.getmaxyx()
        sim = Simulation(w, h)

        # Load selected scene
        scene_name = scene_map.get(args.scene, "default")
        if scene_name == "binary":
            sim.add_binary_star_scene()
        elif scene_name == "figure8":
            sim.add_figure_eight_scene()
        elif scene_name == "cluster":
            sim.add_cluster_scene()
        else:
            sim.add_default_scene()

        renderer = Renderer(stdscr, sim)

        try:
            curses.mouseinterval(0)
        except Exception:
            pass

        drag_start_screen = None
        drag_is_star = False
        running = True

        while running:
            try:
                key = stdscr.getch()
            except Exception:
                key = -1

            drag_info = None

            if key == ord("q") or key == 27:
                running = False
                continue

            elif key == ord(" "):
                sim.paused = not sim.paused

            elif key == ord("t"):
                sim.show_trails = not sim.show_trails

            elif key == ord("g"):
                sim.show_grid = not sim.show_grid

            elif key == ord("h"):
                sim.show_help = not sim.show_help

            elif key == ord("e"):
                sim.show_energy = not sim.show_energy

            elif key == ord("f"):
                sim.follow_com = not sim.follow_com
                if not sim.follow_com:
                    sim.cam_offset_x = 0.0
                    sim.cam_offset_y = 0.0

            elif key == ord("d"):
                sim.delete_nearest(sim.last_mouse_x, sim.last_mouse_y)

            elif key == ord("r"):
                sim.bodies.clear()
                sim.collision_count = 0
                sim.frame = 0
                sim.follow_com = False
                sim.cam_offset_x = 0.0
                sim.cam_offset_y = 0.0
                sim.add_default_scene()

            elif key == ord("c"):
                sim.bodies.clear()
                sim.collision_count = 0

            elif key == ord("+") or key == ord("="):
                sim.speed_mult = min(sim.speed_mult * 1.5, 20.0)

            elif key == ord("-") or key == ord("_"):
                sim.speed_mult = max(sim.speed_mult / 1.5, 0.1)

            elif key == ord("1"):
                sim.bodies.clear()
                sim.collision_count = 0
                sim.follow_com = False
                sim.cam_offset_x = 0.0
                sim.cam_offset_y = 0.0
                sim.add_default_scene()

            elif key == ord("2"):
                sim.bodies.clear()
                sim.collision_count = 0
                sim.follow_com = False
                sim.cam_offset_x = 0.0
                sim.cam_offset_y = 0.0
                sim.add_binary_star_scene()

            elif key == ord("3"):
                sim.bodies.clear()
                sim.collision_count = 0
                sim.follow_com = False
                sim.cam_offset_x = 0.0
                sim.cam_offset_y = 0.0
                sim.add_figure_eight_scene()

            elif key == curses.KEY_MOUSE:
                try:
                    _, mx, my, _, bstate = curses.getmouse()
                except Exception:
                    mx, my, bstate = 0, 0, 0

                sim.last_mouse_x = mx
                sim.last_mouse_y = my

                if bstate & curses.BUTTON1_PRESSED:
                    drag_start_screen = (mx, my)
                    drag_is_star = False

                elif bstate & curses.BUTTON3_PRESSED:
                    drag_start_screen = (mx, my)
                    drag_is_star = True

                elif bstate & curses.BUTTON1_RELEASED or bstate & curses.BUTTON3_RELEASED:
                    if drag_start_screen is not None and len(sim.bodies) < MAX_BODIES:
                        sx0, sy0 = drag_start_screen
                        dx = (mx - sx0) * 0.15
                        dy = (my - sy0) * 0.15
                        mass = 200.0 if drag_is_star else random.uniform(0.5, 5.0)
                        cidx = 2 if drag_is_star else random.randint(0, len(BODY_COLORS) - 1)
                        body = Body(sx0, sy0, dx, dy, mass=mass, color_idx=cidx)
                        sim.bodies.append(body)
                    drag_start_screen = None
                    drag_is_star = False

            # Draw drag preview
            if drag_start_screen is not None:
                try:
                    _, mx, my, _, _ = curses.getmouse()
                except Exception:
                    mx, my = drag_start_screen
                drag_info = (*drag_start_screen, mx, my, drag_is_star)

            # Update with sub-stepping for stability
            sub_steps = max(1, int(sim.speed_mult))
            dt_per_step = DT_BASE * sim.speed_mult / sub_steps
            for _ in range(sub_steps):
                sim.step(dt=dt_per_step)

            renderer.draw(drag_info=drag_info)
            time.sleep(0.033)

        curses.endwin()

    try:
        curses.wrapper(main_with_args)
    except KeyboardInterrupt:
        pass