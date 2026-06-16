#!/usr/bin/env python3
"""
N-Body Gravity Simulator — Terminal-based gravitational N-body simulation.

Bodies interact via Newtonian gravity. Watch orbits, collisions, slingshots,
and chaotic dynamics unfold in your terminal with colored trails.

Controls:
  Left Click   — Spawn a body (drag to set velocity)
  Right Click  — Spawn a massive "star" body
  SPACE        — Pause / Resume
  T            — Toggle trails
  G            — Toggle grid
  +/-          — Speed up / Slow down simulation
  R            — Reset to default scene
  C            — Clear all bodies
  H            — Toggle help overlay
  Q / ESC      — Quit
"""

import sys
import math
import random
import time

try:
    import curses
except ImportError:
    print("curses is required. Install it or use a terminal that supports it.")
    sys.exit(1)


# ─── Constants ───────────────────────────────────────────────────────────────

G = 1.0                # Gravitational constant (simulation units)
SOFTENING = 0.5         # Softening parameter to avoid singularities
DT_BASE = 0.05          # Base timestep
MAX_TRAIL = 120         # Max trail points per body
MAX_BODIES = 80         # Performance cap
COLLISION_DIST = 0.8    # Merge distance


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
    __slots__ = ("x", "y", "vx", "vy", "mass", "color_idx", "trail", "alive")

    def __init__(self, x, y, vx=0.0, vy=0.0, mass=1.0, color_idx=None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.mass = mass
        self.color_idx = color_idx if color_idx is not None else random.randint(0, len(BODY_COLORS) - 1)
        self.trail = []
        self.alive = True

    def radius_display(self):
        """Visual radius based on mass (for rendering)."""
        if self.mass >= 50:
            return 2
        if self.mass >= 10:
            return 1
        return 0  # single character

    def char(self):
        if self.mass >= 100:
            return "★"
        if self.mass >= 50:
            return "✦"
        if self.mass >= 10:
            return "●"
        if self.mass >= 3:
            return "◆"
        return "·"


# ─── Simulation ──────────────────────────────────────────────────────────────

class Simulation:
    def __init__(self, width, height):
        self.bodies: list[Body] = []
        self.width = width
        self.height = height
        self.paused = False
        self.show_trails = True
        self.show_grid = False
        self.show_help = False
        self.speed_mult = 1.0
        self.total_mass_initial = 0
        self.collision_count = 0
        self.frame = 0
        # Camera offset (world coords mapped to screen center)
        self.cam_x = width / 2.0
        self.cam_y = height / 2.0
        # Drag state for spawning
        self.dragging = False
        self.drag_start = None  # (wx, wy) in world coords
        self.drag_is_star = False

    def add_default_scene(self):
        """Create a simple solar-system-like scene."""
        cx, cy = self.cam_x, self.cam_y
        # Central star
        star = Body(cx, cy, 0, 0, mass=200, color_idx=2)
        self.bodies.append(star)
        # Planets
        planets = [
            (12, 0.8, 46),   # dist, mass, color_idx
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
            # Tangential direction (perpendicular to radius, random CW/CCW)
            direction = 1 if random.random() > 0.3 else -1
            vx = -direction * v_orb * math.sin(angle)
            vy = direction * v_orb * math.cos(angle)
            b = Body(px, py, vx, vy, mass=mass, color_idx=cidx)
            self.bodies.append(b)

        self.total_mass_initial = sum(b.mass for b in self.bodies)

    def step(self):
        if self.paused:
            return
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
        self.frame += 1


# ─── Renderer ────────────────────────────────────────────────────────────────

class Renderer:
    def __init__(self, stdscr, sim: Simulation):
        self.stdscr = stdscr
        self.sim = sim
        self.init_colors()

    def init_colors(self):
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

    def world_to_screen(self, wx, wy):
        h = self.sim.height
        w = self.sim.width
        sx = int(round(wx))
        sy = int(round(wy))
        return sx, sy

    def clamp(self, sx, sy):
        sy = max(0, min(self.sim.height - 1, sy))
        sx = max(0, max(0, min(self.sim.width - 1, sx)))
        return sx, sy

    def draw(self, drag_info=None):
        stdscr = self.stdscr
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        self.sim.height = h
        self.sim.width = w

        # Grid
        if self.sim.show_grid:
            for y in range(0, h, 5):
                for x in range(0, w, 10):
                    try:
                        stdscr.addch(y, x, ord("."), curses.color_pair(11))
                    except curses.error:
                        pass

        # Trails
        if self.sim.show_trails:
            for body in self.sim.bodies:
                trail = body.trail
                tlen = len(trail)
                if tlen < 2:
                    continue
                cpair = curses.color_pair(body.color_idx + 1)
                # Draw every Nth point to save perf
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

        # Bodies
        for body in self.sim.bodies:
            sx, sy = self.world_to_screen(body.x, body.y)
            sx, sy = self.clamp(sx, sy)
            cpair = curses.color_pair(body.color_idx + 1)
            ch = body.char()
            try:
                # Encode character
                bch = ch.encode("utf-8", errors="replace")
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

        # Drag arrow (velocity preview)
        if drag_info is not None:
            sx, sy, ex, ey, is_star = drag_info
            cpair = curses.color_pair(14) if is_star else curses.color_pair(15)
            # Draw line from start to end
            self._draw_line(sx, sy, ex, ey, ord("→"), cpair)
            try:
                stdscr.addstr(sy, sx, "✦" if is_star else "●", cpair | curses.A_BOLD)
            except curses.error:
                pass

        # HUD
        self._draw_hud()

        # Help overlay
        if self.sim.show_help:
            self._draw_help()

        stdscr.refresh()

    def _draw_line(self, x0, y0, x1, y1, ch, cpair):
        """Bresenham line."""
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

    def _draw_hud(self):
        stdscr = self.stdscr
        h, w = stdscr.getmaxyx()
        sim = self.sim
        total_mass = sum(b.mass for b in sim.bodies)
        # Top-left info
        lines = [
            f" Bodies: {len(sim.bodies)}  Mass: {total_mass:.1f}  Collisions: {sim.collision_count}  Speed: {sim.speed_mult:.1f}x  Frame: {sim.frame}",
            f" {'PAUSED' if sim.paused else 'RUNNING'}  |  SPACE=pause  T=trails  G=grid  H=help  Click=spawn  R=reset  Q=quit",
        ]
        for i, line in enumerate(lines):
            if i < h - 1:
                try:
                    stdscr.addstr(i, 0, line, curses.color_pair(12))
                except curses.error:
                    pass

    def _draw_help(self):
        stdscr = self.stdscr
        h, w = stdscr.getmaxyx()
        help_text = [
            "╔══════════════════════════════════════╗",
            "║     N-BODY GRAVITY SIMULATOR        ║",
            "╠══════════════════════════════════════╣",
            "║  Left Click   Spawn body (drag→vel) ║",
            "║  Right Click  Spawn massive star     ║",
            "║  SPACE        Pause / Resume         ║",
            "║  T            Toggle trails          ║",
            "║  G            Toggle grid            ║",
            "║  + / -        Speed up / down        ║",
            "║  R            Reset scene            ║",
            "║  C            Clear all bodies        ║",
            "║  H            Toggle this help        ║",
            "║  Q / ESC      Quit                   ║",
            "╠══════════════════════════════════════╣",
            "║  Bodies attract via Newtonian        ║",
            "║  gravity. Drag to set velocity.      ║",
            "║  Colliding bodies merge!             ║",
            "╚══════════════════════════════════════╝",
        ]
        top = max(3, (h - len(help_text)) // 2)
        left = max(0, (w - len(help_text[0])) // 2)
        for i, line in enumerate(help_text):
            if top + i < h - 1:
                try:
                    stdscr.addstr(top + i, left, line, curses.color_pair(13) | curses.A_BOLD)
                except curses.error:
                    pass


# ─── Main loop ──────────────────────────────────────────────────────────────

def main(stdscr):
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

    drag_start_screen = None
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

        elif key == ord("r"):
            sim.bodies.clear()
            sim.collision_count = 0
            sim.frame = 0
            sim.add_default_scene()

        elif key == ord("c"):
            sim.bodies.clear()
            sim.collision_count = 0

        elif key == ord("+") or key == ord("="):
            sim.speed_mult = min(sim.speed_mult * 1.5, 20.0)

        elif key == ord("-") or key == ord("_"):
            sim.speed_mult = max(sim.speed_mult / 1.5, 0.1)

        elif key == curses.KEY_MOUSE:
            try:
                _, mx, my, _, bstate = curses.getmouse()
            except Exception:
                mx, my, bstate = 0, 0, 0

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
        sub_steps = max(1, int(sim.speed_mult))
        for _ in range(sub_steps):
            sim.step()

        # ── Render ────────────────────────────────────────────────────────
        renderer.draw(drag_info=drag_info)

        # Frame timing — target ~30 FPS
        time.sleep(0.033)

    curses.endwin()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass