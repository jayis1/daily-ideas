#!/usr/bin/env python3
"""
Terminal Lunar Lander — A classic physics-based landing game in ASCII art.

Pilot your lunar module safely to the surface by managing thrust, fuel,
and descent angle. Features procedural terrain, realistic physics,
multiple difficulty levels, high scores, and detailed landing assessments.

Controls:
  ← / → / A / D : Rotate lander
  ↑ / W           : Main thrust
  R               : Restart (after landing or crash)
  Q / ESC         : Quit

Usage:
  python3 lunar_lander.py [OPTIONS]

Options:
  --help      Show this help message and exit
  --version   Show version and exit
  --easy      Start on CADET difficulty (skip title screen)
  --medium    Start on PILOT difficulty (skip title screen)
  --hard      Start on COMMANDER difficulty (skip title screen)
  --demo      Watch the autopilot land the module
"""

import curses
import json
import math
import os
import random
import sys
import time
from typing import Dict, List, Optional, Tuple

__version__ = "1.2.0"

# ─── High score file ─────────────────────────────────────────────────

HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".lunar_highscores.json")

# ─── Physics constants ───────────────────────────────────────────────

GRAVITY = 1.625        # m/s² (real lunar gravity)
MAX_THRUST = 4.5       # m/s² max acceleration from engine
FUEL_BURN_RATE = 0.8   # fuel units per second at full thrust
ROTATION_SPEED = 90.0  # degrees per second

# ─── Difficulty presets ───────────────────────────────────────────────

DIFFICULTIES: Dict[str, Dict] = {
    "easy": {
        "fuel": 120,
        "landing_speed_max": 4.0,
        "landing_angle_max": 15,
        "pad_width": 8,
        "num_pads": 3,
        "wind": 0,
        "label": "CADET",
    },
    "medium": {
        "fuel": 80,
        "landing_speed_max": 2.5,
        "landing_angle_max": 10,
        "pad_width": 5,
        "num_pads": 2,
        "wind": 0.3,
        "label": "PILOT",
    },
    "hard": {
        "fuel": 50,
        "landing_speed_max": 1.5,
        "landing_angle_max": 5,
        "pad_width": 4,
        "num_pads": 1,
        "wind": 0.8,
        "label": "COMMANDER",
    },
}

# ─── High score persistence ───────────────────────────────────────────

def load_highscores() -> Dict[str, List[Dict]]:
    """Load high scores from disk. Returns {difficulty: [{score, name, date}]}."""
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            data = json.load(f)
            # Validate structure
            if isinstance(data, dict):
                return data
    except (OSError, json.JSONDecodeError, ValueError):
        pass
    return {"easy": [], "medium": [], "hard": []}


def save_highscores(scores: Dict[str, List[Dict]]) -> None:
    """Save high scores to disk."""
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            json.dump(scores, f, indent=2)
    except OSError:
        pass  # Silently ignore if we can't save


def add_highscore(difficulty: str, score: int, result: str) -> Dict[str, List[Dict]]:
    """Add a score to the high score table and save. Returns updated scores."""
    scores = load_highscores()
    if difficulty not in scores:
        scores[difficulty] = []
    scores[difficulty].append({
        "score": score,
        "result": result,
        "date": time.strftime("%Y-%m-%d %H:%M"),
    })
    # Keep only top 10 per difficulty, sorted by score descending
    scores[difficulty].sort(key=lambda x: x["score"], reverse=True)
    scores[difficulty] = scores[difficulty][:10]
    save_highscores(scores)
    return scores


# ─── Terrain generation ──────────────────────────────────────────────

def generate_terrain(width: int, height: int, pad_width: int, num_pads: int,
                     seed: Optional[int] = None) -> Tuple[List[int], List[Tuple[int, int, int]]]:
    """Generate a lunar terrain surface with flat landing pads.

    Pads are guaranteed to:
    - Not overlap with each other
    - Have py values that exactly match the surface heights at the pad positions
    """
    if seed is not None:
        random.seed(seed)

    # Build base terrain using midpoint displacement
    terrain = [0.0] * width
    # Start with rough midpoint displacement
    terrain[0] = random.uniform(0.3, 0.5) * height
    terrain[width - 1] = random.uniform(0.3, 0.5) * height

    def subdivide(start: int, end: int) -> None:
        if end - start < 2:
            return
        mid = (start + end) // 2
        terrain[mid] = (terrain[start] + terrain[end]) / 2 + random.uniform(-height * 0.08, height * 0.08)
        subdivide(start, mid)
        subdivide(mid, end)

    subdivide(0, width - 1)

    # Add some craters
    for _ in range(random.randint(3, 8)):
        cx = random.randint(10, width - 10)
        crater_w = random.randint(5, 15)
        crater_d = random.uniform(1.5, 4.0)
        for x in range(max(0, cx - crater_w), min(width, cx + crater_w)):
            dist = abs(x - cx) / crater_w
            if dist < 1.0:
                terrain[x] += crater_d * (1 - dist * dist)

    # Convert to integer screen coordinates FIRST (before pad creation)
    # so that pad positions match actual surface values
    surface: List[int] = []
    for x in range(width):
        surface.append(max(3, min(height - 2, int(terrain[x]))))

    # Create landing pads with overlap checking
    pads: List[Tuple[int, int, int]] = []
    for _ in range(num_pads):
        px = random.randint(pad_width + 5, width - pad_width - 5)
        # Try multiple times to find a non-overlapping position
        for _attempt in range(50):
            px = random.randint(pad_width + 5, width - pad_width - 5)
            # Check overlap with existing pads
            overlaps = False
            for existing_px, _, existing_pw in pads:
                half_new = pad_width // 2
                half_existing = existing_pw // 2
                if abs(px - existing_px) < half_new + half_existing + 4:
                    overlaps = True
                    break
            if not overlaps:
                break

        # Flatten the pad area using the SURFACE (integer) values
        pad_y = surface[px]
        half = pad_width // 2
        for x in range(px - half, px + half + 1):
            if 0 <= x < width:
                surface[x] = pad_y
        pads.append((px, pad_y, pad_width))

    return surface, pads


# ─── Lander sprite ────────────────────────────────────────────────────

def get_lander_sprite(angle_deg: float, thrusting: bool = False) -> List[Tuple[int, int, str]]:
    """Return a list of (dx, dy, char) offsets for the lander at given angle.

    If thrusting, include an expanded flame effect.
    """
    rad = math.radians(angle_deg)
    sprite: List[Tuple[int, int, str]] = []
    # Center module
    sprite.append((0, 0, "▲"))
    # Body
    sprite.append((-1, 1, "/"))
    sprite.append((1, 1, "\\"))
    # Legs
    sprite.append((-2, 2, "/"))
    sprite.append((2, 2, "\\"))

    # Thrust flame indicator (larger when thrusting)
    thrust_dir_x = math.sin(rad)
    thrust_dir_y = math.cos(rad)
    flame_len = 3 if thrusting else 2
    flame_x = int(round(-thrust_dir_x * flame_len))
    flame_y = int(round(thrust_dir_y * flame_len)) + 2
    flame_char = "█" if thrusting else "▒"
    sprite.append((flame_x, flame_y, flame_char))

    # Add extra flame particles when thrusting
    if thrusting:
        sprite.append((flame_x + random.choice([-1, 0, 1]), flame_y + 1, random.choice(["░", "·"])))

    return sprite


# ─── Autopilot (demo mode) ────────────────────────────────────────────

class Autopilot:
    """Simple autopilot that lands the module on a pad.

    Strategy:
      1. Rotate toward the nearest landing pad.
      2. Apply lateral thrust to cancel horizontal velocity.
      3. Apply vertical thrust to maintain a target descent rate.
      4. As altitude decreases, slow descent and zero out horizontal speed.
    """

    def __init__(self, pads: List[Tuple[int, int, int]]) -> None:
        self.target_pad = min(pads, key=lambda p: p[0]) if pads else None

    def decide(self, lx: float, ly: float, vx: float, vy: float,
               angle: float, fuel: float, altitude: float) -> Tuple[bool, bool, bool]:
        """Return (thrusting, rotating_left, rotating_right) for the next frame.

        Uses a proportional control law:
          - Target x is the pad center.
          - Target descent rate decreases as altitude decreases.
          - Angle is steered to achieve desired lateral correction.
        """
        if self.target_pad is None or fuel <= 0:
            return False, False, False

        target_x = float(self.target_pad[0])
        target_y = float(self.target_pad[1])

        # Desired horizontal speed: proportional to distance from pad
        dx = target_x - lx
        # Wrap for horizontal torus
        if dx > 200:
            dx -= 400
        elif dx < -200:
            dx += 400
        desired_vx = max(-8.0, min(8.0, dx * 0.15))

        # Desired vertical speed: descend faster when high, slow down near ground
        desired_vy = min(3.0, max(0.5, altitude * 0.12))

        # Desired angle: to correct horizontal velocity
        desired_angle = max(-90, min(90, (desired_vx - vx) * 8.0))

        rot_left = angle > desired_angle + 2
        rot_right = angle < desired_angle - 2

        # Thrust when we need to slow descent or correct vertical speed
        desired_ay = GRAVITY - desired_vy_change(vy, desired_vy)
        # Need upward thrust if gravity > desired vertical acceleration
        net_vertical = GRAVITY - desired_vy * 0.05  # approximate needed correction
        should_thrust = vy > desired_vy or altitude < 15
        # Also thrust if going too fast laterally and need to brake
        if abs(vx) > 5 and altitude < 20:
            should_thrust = True

        return should_thrust, rot_left, rot_right


def desired_vy_change(current_vy: float, desired_vy: float) -> float:
    """Helper: how much we want vy to change."""
    return desired_vy - current_vy


# ─── Main game ────────────────────────────────────────────────────────

class LunarLander:
    def __init__(self, stdscr, difficulty: str = "medium", demo: bool = False):
        self.stdscr = stdscr
        self.difficulty = difficulty
        self.config = DIFFICULTIES[difficulty]
        self.demo = demo
        self._init_game()

    def _init_game(self) -> None:
        self.height, self.width = self.stdscr.getmaxyx()
        if self.height < 24 or self.width < 70:
            raise ValueError("Terminal too small. Need at least 70x24.")

        self.world_width = self.width
        self.world_height = self.height

        # Lander state — position in world coords (0,0 = top-left)
        self.lx = self.world_width / 2.0
        self.ly = 3.0
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0  # degrees, 0 = straight up

        self.fuel = self.config["fuel"]
        self.thrusting = False
        self.rotating_left = False
        self.rotating_right = False
        self.alive = True
        self.landed = False
        self.landing_result: Optional[str] = None

        self.wind = 0.0

        self.score = 0
        self.altitude = 0.0
        self.time_elapsed = 0.0
        self.frame_count = 0

        # Warnings state
        self.warning_text = ""
        self.warning_timer = 0.0

        # Generate terrain
        seed = random.randint(0, 999999)
        self.surface, self.pads = generate_terrain(
            self.world_width, self.world_height,
            self.config["pad_width"], self.config["num_pads"], seed
        )

        # Stars
        self.stars: List[Tuple[int, int, str]] = []
        for _ in range(60):
            sx = random.randint(0, self.world_width - 1)
            sy = random.randint(0, int(self.world_height * 0.5))
            brightness = random.choice(["·", "∙", "✦", "⋆", "+"])
            self.stars.append((sx, sy, brightness))

        # Autopilot for demo mode
        self.autopilot = Autopilot(self.pads) if self.demo else None

        self.last_time = time.time()

    def run(self) -> bool:
        """Main game loop. Returns True to signal restart, False to quit."""
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(33)  # ~30 FPS

        # Show title screen (skip in demo mode)
        if not self.demo:
            if not self._title_screen():
                return False

        self.last_time = time.time()
        self._init_game()
        # Reset timer after init
        self.last_time = time.time()

        while self.alive and not self.landed:
            dt = self._get_dt()
            self._handle_input()
            self._update_physics(dt)
            self._update_warnings(dt)
            self._render()

        # Final render
        self._render()
        return self._show_result()

    def _get_dt(self) -> float:
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        return min(dt, 0.1)  # Cap delta time

    def _handle_input(self) -> None:
        if self.demo:
            # Autopilot controls
            if self.autopilot:
                t, rl, rr = self.autopilot.decide(
                    self.lx, self.ly, self.vx, self.vy,
                    self.angle, self.fuel, self.altitude
                )
                self.thrusting = t
                self.rotating_left = rl
                self.rotating_right = rr
            return

        self.thrusting = False
        self.rotating_left = False
        self.rotating_right = False

        key = self.stdscr.getch()
        if key in (ord("q"), 27):  # q or ESC
            self.alive = False
            return

        # Keep reading buffered keys
        while key != -1:
            if key == curses.KEY_UP or key == ord("w"):
                self.thrusting = True
            elif key == curses.KEY_LEFT or key == ord("a"):
                self.rotating_left = True
            elif key == curses.KEY_RIGHT or key == ord("d"):
                self.rotating_right = True
            elif key == ord("q") or key == 27:
                self.alive = False
                return
            key = self.stdscr.getch()

    def _update_warnings(self, dt: float) -> None:
        """Update in-game warning messages based on flight parameters."""
        speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
        max_speed = self.config["landing_speed_max"]
        max_angle = self.config["landing_angle_max"]

        # Clear old warning after timer expires
        if self.warning_timer > 0:
            self.warning_timer -= dt
            return

        # Generate new warnings
        if self.altitude < 20 and speed > max_speed * 1.5:
            self.warning_text = "⚠ TOO FAST! SLOW DOWN!"
            self.warning_timer = 0.8
        elif self.altitude < 10 and self.vy > max_speed:
            self.warning_text = "⚠ HIGH DESCENT RATE!"
            self.warning_timer = 0.8
        elif abs(self.angle) > max_angle and self.altitude < 30:
            self.warning_text = "⚠ STEEP ANGLE!"
            self.warning_timer = 0.8
        elif self.fuel <= 0:
            self.warning_text = "⚠ NO FUEL!"
            self.warning_timer = 1.0
        elif self.fuel < self.config["fuel"] * 0.2 and self.fuel > 0:
            self.warning_text = "⚠ LOW FUEL!"
            self.warning_timer = 1.5
        else:
            self.warning_text = ""

    def _update_physics(self, dt: float) -> None:
        if not self.alive or self.landed:
            return

        self.time_elapsed += dt
        self.frame_count += 1

        # Rotation
        if self.rotating_left:
            self.angle -= ROTATION_SPEED * dt
        if self.rotating_right:
            self.angle += ROTATION_SPEED * dt
        # Clamp angle
        self.angle = max(-90, min(90, self.angle))

        # Thrust
        ax, ay = 0.0, GRAVITY  # gravity pulls down (positive y)
        if self.thrusting and self.fuel > 0:
            rad = math.radians(self.angle)
            ax -= MAX_THRUST * math.sin(rad)
            ay -= MAX_THRUST * math.cos(rad)
            self.fuel -= FUEL_BURN_RATE * dt
            self.fuel = max(0, self.fuel)

        # Wind
        if self.config["wind"] > 0:
            self.wind = math.sin(self.time_elapsed * 0.5) * self.config["wind"]
            ax += self.wind

        # Integrate
        self.vx += ax * dt
        self.vy += ay * dt
        self.lx += self.vx * dt
        self.ly += self.vy * dt

        # Horizontal wrapping
        if self.lx < 0:
            self.lx += self.world_width
        elif self.lx >= self.world_width:
            self.lx -= self.world_width

        # Ceiling bounce
        if self.ly < 0:
            self.ly = 0
            self.vy = abs(self.vy) * 0.3

        # Ground collision check
        ix = int(self.lx) % self.world_width
        ground_y = self.surface[ix]
        self.altitude = ground_y - self.ly

        if self.ly >= ground_y - 1:
            self.ly = ground_y - 1
            self._check_landing(ix, ground_y)

    def _check_landing(self, ix: int, ground_y: int) -> None:
        """Check if the landing was successful."""
        speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
        angle = abs(self.angle)

        # Check if on a landing pad
        on_pad = False
        for px, py, pw in self.pads:
            if abs(ix - px) <= pw // 2:
                on_pad = True
                break

        max_speed = self.config["landing_speed_max"]
        max_angle = self.config["landing_angle_max"]

        if on_pad and speed <= max_speed and angle <= max_angle:
            # Perfect landing!
            self.landed = True
            self.landing_result = "PERFECT"
            self._calc_score(speed, angle, on_pad)
        elif on_pad and speed <= max_speed * 1.5:
            self.landed = True
            self.landing_result = "ROUGH"
            self._calc_score(speed, angle, on_pad)
        elif speed <= max_speed * 2 and angle <= max_angle * 2:
            self.landed = True
            self.landing_result = "HARD"
            self._calc_score(speed, angle, on_pad)
        else:
            # Crash!
            self.alive = False
            self.landing_result = "CRASH"
            self.score = 0

    def _calc_score(self, speed: float, angle: float, on_pad: bool) -> None:
        """Calculate the final score based on landing quality."""
        fuel_pct = self.fuel / self.config["fuel"] if self.config["fuel"] > 0 else 0
        fuel_bonus = int(fuel_pct * 100)
        speed_pct = 1 - speed / (self.config["landing_speed_max"] * 2) if self.config["landing_speed_max"] > 0 else 0
        speed_bonus = int(max(0, speed_pct) * 100)
        angle_pct = 1 - angle / (self.config["landing_angle_max"] * 2) if self.config["landing_angle_max"] > 0 else 0
        angle_bonus = int(max(0, angle_pct) * 100)
        pad_bonus = 200 if on_pad else 0
        diff_mult = {"easy": 1, "medium": 2, "hard": 3}[self.difficulty]
        self.score = int((fuel_bonus + speed_bonus + angle_bonus + pad_bonus) * diff_mult)

    def _render(self) -> None:
        self.stdscr.erase()

        # Draw stars
        for sx, sy, ch in self.stars:
            # Twinkle effect: some stars randomly change brightness
            if self.frame_count % 120 < 3 and random.random() < 0.1:
                ch = random.choice(["·", "✦"])
            if 0 <= sy < self.height and 0 <= sx < self.width:
                try:
                    self.stdscr.addch(sy, sx, ch)
                except curses.error:
                    pass

        # Draw terrain
        for x in range(min(self.world_width, self.width)):
            ground_y = self.surface[x]
            # Check if this x is on a landing pad
            is_pad = False
            for px, py, pw in self.pads:
                if abs(x - px) <= pw // 2:
                    is_pad = True
                    break

            for y in range(max(0, ground_y), min(self.height, ground_y + 6)):
                if y < self.height and x < self.width:
                    if y == ground_y:
                        ch = "━" if is_pad else "▀"
                    elif y == ground_y + 1:
                        ch = "▄" if not is_pad else "│"
                    else:
                        ch = "█" if not is_pad else " "
                    try:
                        self.stdscr.addch(y, x, ch)
                    except curses.error:
                        pass

        # Draw landing pad markers
        for px, py, pw in self.pads:
            for dx in range(-pw // 2, pw // 2 + 1):
                x = px + dx
                if 0 <= x < self.width and py < self.height:
                    try:
                        self.stdscr.addch(py, x, "━")
                    except curses.error:
                        pass
            # Draw pad beacon markers (flashing lights above pad)
            beacon_char = "◈" if self.frame_count % 30 < 15 else "◇"
            for bx_off in [-(pw // 2), pw // 2]:
                bx = px + bx_off
                by = py - 1
                if 0 <= bx < self.width and 0 <= by < self.height:
                    try:
                        self.stdscr.addch(by, bx, beacon_char)
                    except curses.error:
                        pass

        # Draw lander
        if self.alive or self.landed:
            sprite = get_lander_sprite(self.angle, self.thrusting and self.fuel > 0)
            liy = int(self.ly)
            lix = int(self.lx)
            for dx, dy, ch in sprite:
                y = liy + dy
                x = (lix + dx) % self.world_width
                if 0 <= y < self.height and 0 <= x < self.width:
                    try:
                        self.stdscr.addch(y, x, ch)
                    except curses.error:
                        pass

            # Draw thrust particles
            if self.thrusting and self.fuel > 0:
                rad = math.radians(self.angle)
                for _ in range(5):
                    px = lix + random.randint(-1, 1) + int(math.sin(rad) * 2)
                    py_pos = liy + 3 + random.randint(0, 3)
                    ch = random.choice(["░", "▒", "·", "*", "✧"])
                    if 0 <= py_pos < self.height and 0 <= px < self.width:
                        try:
                            self.stdscr.addch(py_pos, px, ch)
                        except curses.error:
                            pass

        # Crash animation
        if not self.alive:
            cx, cy = int(self.lx), int(self.ly)
            # Expanding debris cloud
            radius = min(8, 3 + self.frame_count % 20)
            for _ in range(15):
                px = cx + random.randint(-radius, radius)
                py = cy + random.randint(-radius, max(0, radius - 2))
                ch = random.choice(["*", "#", "░", "▒", "█", "✸", "✦", "◆"])
                if 0 <= py < self.height and 0 <= px < self.width:
                    try:
                        self.stdscr.addch(py, px, ch)
                    except curses.error:
                        pass

        # Warnings overlay
        if self.warning_text:
            wx = max(0, (self.width - len(self.warning_text)) // 2)
            wy = max(0, self.height // 4)
            try:
                self.stdscr.addstr(wy, wx, self.warning_text, curses.A_BOLD | curses.color_pair(1) if curses.has_colors() else curses.A_BOLD)
            except curses.error:
                pass

        # HUD
        self._draw_hud()

        self.stdscr.refresh()

    def _draw_hud(self) -> None:
        speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
        h_speed = abs(self.vx)
        v_speed = self.vy
        alt = max(0, self.altitude)

        # Left panel
        panel_x = 1
        panel_y = 1

        # Speed color coding
        max_spd = self.config["landing_speed_max"]
        speed_indicator = "●" if speed <= max_spd else ("◘" if speed <= max_spd * 1.5 else "◆")

        lines = [
            f"┌─ LUNAR LANDER ─────────┐",
            f"│ ALT:     {alt:8.1f} m     │",
            f"│ V-SPD:   {v_speed:8.2f} m/s   │",
            f"│ H-SPD:   {h_speed:8.2f} m/s   │",
            f"│ ANGLE:   {self.angle:8.1f} °     │",
            f"│ FUEL:    {self.fuel:8.1f}       │",
            f"│ SPEED:   {speed:8.2f} m/s {speed_indicator} │",
            f"│ TIME:    {self.time_elapsed:8.1f} s     │",
        ]
        if self.config["wind"] > 0:
            wind_str = "→" if self.wind > 0 else "←" if self.wind < 0 else "·"
            lines.append(f"│ WIND:    {wind_str} {abs(self.wind):.2f}        │")
        if self.demo:
            lines.append(f"│ [DEMO MODE]            │")
        lines.append(f"└────────────────────────┘")

        for i, line in enumerate(lines):
            try:
                self.stdscr.addstr(panel_y + i, panel_x, line)
            except curses.error:
                pass

        # Fuel bar
        bar_y = panel_y + 5
        bar_x = panel_x + 12
        bar_len = 12
        fuel_pct = max(0.0, min(1.0, self.fuel / self.config["fuel"]))
        filled = int(bar_len * fuel_pct)
        bar = "█" * filled + "░" * (bar_len - filled)
        # Color the fuel bar: green > yellow > red
        try:
            if fuel_pct > 0.5:
                color = curses.color_pair(2) if curses.has_colors() else 0  # green
            elif fuel_pct > 0.2:
                color = curses.color_pair(3) if curses.has_colors() else 0  # yellow
            else:
                color = curses.color_pair(1) if curses.has_colors() else 0  # red
            self.stdscr.addstr(bar_y, bar_x, bar, color | curses.A_BOLD)
        except curses.error:
            pass

        # Altitude bar on right side
        bar_max_h = min(15, self.height - 4)
        if bar_max_h > 3:
            alt_pct = max(0.0, min(1.0, self.altitude / (self.height * 0.7))) if self.altitude > 0 else 0
            alt_filled = int(bar_max_h * alt_pct)
            alt_x = self.width - 3
            try:
                self.stdscr.addstr(1, alt_x, "AL")
                self.stdscr.addstr(2, alt_x, "──")
                for i in range(bar_max_h):
                    ch = "█" if i < alt_filled else "░"
                    self.stdscr.addch(3 + bar_max_h - 1 - i, alt_x, ch)
                self.stdscr.addstr(3 + bar_max_h, alt_x, "──")
            except curses.error:
                pass

        # Difficulty label at top right
        label = self.config["label"]
        diff_x = self.width - len(label) - 8
        try:
            self.stdscr.addstr(1, diff_x, f"[{label}]")
        except curses.error:
            pass

        # Controls hint at bottom
        controls = "←/→: Rotate  ↑/W: Thrust  Q: Quit" + ("  [DEMO]" if self.demo else "")
        try:
            self.stdscr.addstr(self.height - 1, (self.width - len(controls)) // 2, controls)
        except curses.error:
            pass

    def _show_result(self) -> bool:
        """Show landing/crash result screen. Returns True to restart, False to quit."""
        # Save high score
        if self.landing_result and self.landing_result != "CRASH":
            add_highscore(self.difficulty, self.score, self.landing_result)

        self.stdscr.erase()

        if self.landing_result == "CRASH":
            title = "💥 CRASH! 💥"
            subtitle = "Your lunar module was destroyed."
            color_pair = curses.color_pair(1) if curses.has_colors() else 0
        elif self.landing_result == "PERFECT":
            title = "🌟 PERFECT LANDING! 🌟"
            subtitle = "Eagle has landed!"
            color_pair = curses.color_pair(2) if curses.has_colors() else 0
        elif self.landing_result == "ROUGH":
            title = "⚠ ROUGH LANDING ⚠"
            subtitle = "You made it, but barely."
            color_pair = curses.color_pair(3) if curses.has_colors() else 0
        else:
            title = "HARD LANDING"
            subtitle = "Not pretty, but you survived."
            color_pair = curses.color_pair(3) if curses.has_colors() else 0

        # Center the result
        cy = self.height // 2

        # Title
        try:
            self.stdscr.addstr(cy - 5, (self.width - len(title)) // 2, title, color_pair | curses.A_BOLD)
        except curses.error:
            pass

        try:
            self.stdscr.addstr(cy - 3, (self.width - len(subtitle)) // 2, subtitle)
        except curses.error:
            pass

        # Stats
        speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
        stats = [
            f"Descent Speed: {speed:.2f} m/s",
            f"Landing Angle: {abs(self.angle):.1f}°",
            f"Fuel Remaining: {self.fuel:.1f}",
            f"Time: {self.time_elapsed:.1f}s",
            f"",
            f"Score: {self.score}",
        ]

        for i, line in enumerate(stats):
            try:
                self.stdscr.addstr(cy - 1 + i, (self.width - len(line)) // 2, line)
            except curses.error:
                pass

        # Landing assessment
        max_speed = self.config["landing_speed_max"]
        max_angle = self.config["landing_angle_max"]
        assessment_lines: List[str] = []
        if self.landing_result != "CRASH":
            if speed <= max_speed:
                assessment_lines.append("✓ Speed within limits")
            else:
                assessment_lines.append("✗ Speed exceeded limits")

            if abs(self.angle) <= max_angle:
                assessment_lines.append("✓ Angle within limits")
            else:
                assessment_lines.append("✗ Angle exceeded limits")

            on_pad = any(abs(int(self.lx) - px) <= pw // 2 for px, py, pw in self.pads)
            assessment_lines.append("✓ On landing pad" if on_pad else "✗ Missed landing pad")

        for i, line in enumerate(assessment_lines):
            try:
                self.stdscr.addstr(cy + len(stats) + i + 1, (self.width - len(line)) // 2, line)
            except curses.error:
                pass

        # Show top 3 high scores for this difficulty
        highscores = load_highscores()
        if self.difficulty in highscores and highscores[self.difficulty]:
            hs_y = cy + len(stats) + len(assessment_lines) + 3
            try:
                self.stdscr.addstr(hs_y, (self.width - 20) // 2, "── Top Scores ──", curses.A_BOLD)
                for j, entry in enumerate(highscores[self.difficulty][:3]):
                    hs_line = f"{j+1}. {entry['score']:>5} pts  {entry['result']}"
                    self.stdscr.addstr(hs_y + 1 + j, (self.width - len(hs_line)) // 2, hs_line)
            except curses.error:
                pass

        prompt = "Press R to restart · Any other key to quit"
        try:
            self.stdscr.addstr(self.height - 3, (self.width - len(prompt)) // 2, prompt, curses.A_DIM)
        except curses.error:
            pass

        self.stdscr.refresh()
        self.stdscr.nodelay(False)
        key = self.stdscr.getch()

        # R or r to restart
        return key in (ord("r"), ord("R"))

    def _title_screen(self) -> bool:
        """Show title screen. Returns True to continue, False to quit."""
        self.stdscr.erase()

        title_lines = [
            "  ╔═══════════════════════════════╗",
            "  ║     L U N A R   L A N D E R  ║",
            "  ║         ─────────────        ║",
            "  ║     Terminal Edition v" + __version__ + "  ║",
            "  ╚═══════════════════════════════╝",
        ]

        start_y = max(1, (self.height - 22) // 2)

        for i, line in enumerate(title_lines):
            try:
                self.stdscr.addstr(start_y + i, (self.width - len(line)) // 2, line, curses.A_BOLD)
            except curses.error:
                pass

        # ASCII art lander
        lander_art = [
            "       ▲",
            "      /█\\",
            "     / █ \\",
            "    /  █  \\",
            "   /__███__\\",
            "    ║     ║",
            "   ╱       ╲",
            "  ▕  ▓▓▓▓▓▓  ▏",
            "   ╲       ╱",
        ]

        for i, line in enumerate(lander_art):
            try:
                self.stdscr.addstr(start_y + 6 + i, (self.width - 19) // 2, line)
            except curses.error:
                pass

        # Difficulty selection
        diff_y = start_y + 17
        prompt = "Select Difficulty:"
        try:
            self.stdscr.addstr(diff_y, (self.width - len(prompt)) // 2, prompt)
        except curses.error:
            pass

        options = [
            ("1", "easy", "CADET   — Lots of fuel, forgiving pads"),
            ("2", "medium", "PILOT   — Moderate challenge"),
            ("3", "hard", "COMMANDER — Minimal fuel, tiny pads, wind"),
        ]

        for i, (key, diff, desc) in enumerate(options):
            line = f"  [{key}] {desc}"
            try:
                self.stdscr.addstr(diff_y + 2 + i, (self.width - len(line)) // 2, line)
            except curses.error:
                pass

        # Show best scores next to each difficulty
        highscores = load_highscores()
        for i, (_, diff, _) in enumerate(options):
            if diff in highscores and highscores[diff]:
                best = highscores[diff][0]["score"]
                best_line = f"  Best: {best} pts"
                try:
                    self.stdscr.addstr(diff_y + 2 + i, self.width - len(best_line) - 3, best_line, curses.A_DIM)
                except curses.error:
                    pass

        quit_line = "  [Q] Quit    [D] Demo mode"
        try:
            self.stdscr.addstr(diff_y + 6, (self.width - len(quit_line)) // 2, quit_line, curses.A_DIM)
        except curses.error:
            pass

        controls = "Controls: ←/→ Rotate  ↑/W Thrust  Q Quit"
        try:
            self.stdscr.addstr(self.height - 2, (self.width - len(controls)) // 2, controls, curses.A_DIM)
        except curses.error:
            pass

        self.stdscr.refresh()

        # Wait for key
        self.stdscr.nodelay(False)
        while True:
            key = self.stdscr.getch()
            if key == ord("1"):
                self.difficulty = "easy"
                self.config = DIFFICULTIES["easy"]
                return True
            elif key == ord("2"):
                self.difficulty = "medium"
                self.config = DIFFICULTIES["medium"]
                return True
            elif key == ord("3"):
                self.difficulty = "hard"
                self.config = DIFFICULTIES["hard"]
                return True
            elif key == ord("d") or key == ord("D"):
                self.demo = True
                self.difficulty = "medium"
                self.config = DIFFICULTIES["medium"]
                return True
            elif key == ord("q") or key == 27:
                return False


def main(stdscr, difficulty: Optional[str] = None, demo: bool = False) -> None:
    """Main game entry point (called by curses.wrapper).

    Args:
        stdscr: Curses standard screen.
        difficulty: Optional difficulty override ('easy', 'medium', 'hard').
        demo: Whether to run in demo/autopilot mode.
    """
    # Initialize colors if available
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)

    while True:
        try:
            game = LunarLander(stdscr, difficulty=difficulty or "medium", demo=demo)
            restart = game.run()
            if not restart:
                break
            # Reset for restart
            difficulty = None  # Go back to title screen on restart
            demo = False
        except ValueError as e:
            stdscr.erase()
            stdscr.addstr(0, 0, str(e))
            stdscr.refresh()
            stdscr.getch()
            break


if __name__ == "__main__":
    # Parse command-line arguments
    cli_difficulty: Optional[str] = None
    cli_demo = False
    for arg in sys.argv[1:]:
        if arg == "--help" or arg == "-h":
            print(__doc__)
            sys.exit(0)
        elif arg == "--version" or arg == "-v":
            print(f"terminal-lunar-lander {__version__}")
            sys.exit(0)
        elif arg == "--easy":
            cli_difficulty = "easy"
        elif arg == "--medium":
            cli_difficulty = "medium"
        elif arg == "--hard":
            cli_difficulty = "hard"
        elif arg == "--demo":
            cli_demo = True
        else:
            print(f"Unknown argument: {arg}", file=sys.stderr)
            print("Use --help for usage information.", file=sys.stderr)
            sys.exit(1)

    # Check if running in a terminal (non-TTY fallback)
    if not sys.stdin.isatty():
        print("Error: This game requires an interactive terminal (TTY).", file=sys.stderr)
        print("Run it in a terminal, not via piped input.", file=sys.stderr)
        sys.exit(1)

    try:
        curses.wrapper(main, cli_difficulty, cli_demo)
    except curses.error as e:
        print(f"Terminal error: {e}", file=sys.stderr)
        print("Make sure your terminal supports curses and is at least 70x24.", file=sys.stderr)
        sys.exit(1)