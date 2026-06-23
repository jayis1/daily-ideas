#!/usr/bin/env python3
"""
Terminal Lunar Lander — A classic physics-based landing game in ASCII art.

Pilot your lunar module safely to the surface by managing thrust, fuel,
and descent angle. Features procedural terrain, realistic physics,
multiple difficulty levels, and detailed landing assessments.

Controls:
  ← / →  : Rotate lander
  ↑       : Main thrust
  q / ESC : Quit

Usage:
  python3 lunar_lander.py [OPTIONS]

Options:
  --help      Show this help message and exit
  --version   Show version and exit
  --easy      Start on CADET difficulty (skip title screen)
  --medium    Start on PILOT difficulty (skip title screen)
  --hard      Start on COMMANDER difficulty (skip title screen)
"""

import curses
import math
import random
import sys
import time

__version__ = "1.1.0"

# ─── Physics constants ───────────────────────────────────────────────

GRAVITY = 1.625        # m/s² (real lunar gravity)
MAX_THRUST = 4.5       # m/s² max acceleration from engine
FUEL_BURN_RATE = 0.8   # fuel units per second at full thrust
ROTATION_SPEED = 90.0  # degrees per second

# ─── Difficulty presets ───────────────────────────────────────────────

DIFFICULTIES = {
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


# ─── Terrain generation ──────────────────────────────────────────────

def generate_terrain(width, height, pad_width, num_pads, seed=None):
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

    def subdivide(start, end):
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
    surface = []
    for x in range(width):
        surface.append(max(3, min(height - 2, int(terrain[x]))))

    # Create landing pads with overlap checking
    pads = []
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


# ─── Lander sprite ───────────────────────────────────────────────────

def get_lander_sprite(angle_deg):
    """Return a list of (dx, dy, char) offsets for the lander at given angle."""
    # Simple directional indicator
    rad = math.radians(angle_deg)
    sprite = []
    # Center module
    sprite.append((0, 0, "▲"))
    # Body
    sprite.append((-1, 1, "/"))
    sprite.append((1, 1, "\\"))
    # Legs
    sprite.append((-2, 2, "/"))
    sprite.append((2, 2, "\\"))

    # Thrust flame indicator
    thrust_dir_x = math.sin(rad)
    thrust_dir_y = math.cos(rad)
    flame_x = int(round(-thrust_dir_x * 2))
    flame_y = int(round(thrust_dir_y * 2)) + 2
    sprite.append((flame_x, flame_y, "█"))

    return sprite


# ─── Main game ────────────────────────────────────────────────────────

class LunarLander:
    def __init__(self, stdscr, difficulty="medium"):
        self.stdscr = stdscr
        self.difficulty = difficulty
        self.config = DIFFICULTIES[difficulty]
        self._init_game()

    def _init_game(self):
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
        self.landing_result = None

        self.wind = 0.0

        self.score = 0
        self.altitude = 0.0
        self.time_elapsed = 0.0

        # Generate terrain
        seed = random.randint(0, 999999)
        self.surface, self.pads = generate_terrain(
            self.world_width, self.world_height,
            self.config["pad_width"], self.config["num_pads"], seed
        )

        # Stars
        self.stars = []
        for _ in range(60):
            sx = random.randint(0, self.world_width - 1)
            sy = random.randint(0, int(self.world_height * 0.5))
            brightness = random.choice(["·", "∙", "✦", "⋆", "+"])
            self.stars.append((sx, sy, brightness))

        self.last_time = time.time()

    def run(self):
        """Main game loop."""
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(33)  # ~30 FPS

        # Show title screen
        if not self._title_screen():
            return

        self.last_time = time.time()
        self._init_game()
        # Reset timer after init
        self.last_time = time.time()

        while self.alive and not self.landed:
            dt = self._get_dt()
            self._handle_input()
            self._update_physics(dt)
            self._render()

        # Final render
        self._render()
        self._show_result()

    def _get_dt(self):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        return min(dt, 0.1)  # Cap delta time

    def _handle_input(self):
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

        # Check held keys (for smoother control)
        # curses doesn't do key-hold well, so we rely on repeated key events

    def _update_physics(self, dt):
        if not self.alive or self.landed:
            return

        self.time_elapsed += dt

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

    def _check_landing(self, ix, ground_y):
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

    def _calc_score(self, speed, angle, on_pad):
        fuel_bonus = int(self.fuel / self.config["fuel"] * 100)
        speed_bonus = int((1 - speed / (self.config["landing_speed_max"] * 2)) * 100)
        angle_bonus = int((1 - angle / (self.config["landing_angle_max"] * 2)) * 100)
        pad_bonus = 200 if on_pad else 0
        diff_mult = {"easy": 1, "medium": 2, "hard": 3}[self.difficulty]
        self.score = int((fuel_bonus + speed_bonus + angle_bonus + pad_bonus) * diff_mult)

    def _render(self):
        self.stdscr.erase()

        # Draw stars
        for sx, sy, ch in self.stars:
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

        # Draw lander
        if self.alive or self.landed:
            sprite = get_lander_sprite(self.angle)
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
                for i in range(3):
                    px = lix + random.randint(-1, 1) + int(math.sin(rad) * 2)
                    py_pos = liy + 3 + random.randint(0, 2)
                    ch = random.choice(["░", "▒", "·", "*"])
                    if 0 <= py_pos < self.height and 0 <= px < self.width:
                        try:
                            self.stdscr.addch(py_pos, px, ch)
                        except curses.error:
                            pass

        # Crash animation
        if not self.alive:
            cx, cy = int(self.lx), int(self.ly)
            for _ in range(12):
                px = cx + random.randint(-4, 4)
                py = cy + random.randint(-3, 2)
                ch = random.choice(["*", "#", "░", "▒", "█", "✸"])
                if 0 <= py < self.height and 0 <= px < self.width:
                    try:
                        self.stdscr.addch(py, px, ch)
                    except curses.error:
                        pass

        # HUD
        self._draw_hud()

        self.stdscr.refresh()

    def _draw_hud(self):
        speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
        h_speed = abs(self.vx)
        v_speed = self.vy
        alt = max(0, self.altitude)

        # Left panel
        panel_x = 1
        panel_y = 1
        lines = [
            f"┌─ LUNAR LANDER ─────────┐",
            f"│ ALT:     {alt:8.1f} m     │",
            f"│ V-SPD:   {v_speed:8.2f} m/s   │",
            f"│ H-SPD:   {h_speed:8.2f} m/s   │",
            f"│ ANGLE:   {self.angle:8.1f} °     │",
            f"│ FUEL:    {self.fuel:8.1f}       │",
            f"│ SPEED:   {speed:8.2f} m/s   │",
            f"│ TIME:    {self.time_elapsed:8.1f} s     │",
        ]
        if self.config["wind"] > 0:
            wind_str = "→" if self.wind > 0 else "←" if self.wind < 0 else "·"
            lines.append(f"│ WIND:    {wind_str} {abs(self.wind):.2f}        │")
        lines.append(f"└────────────────────────┘")

        for i, line in enumerate(lines):
            try:
                self.stdscr.addstr(panel_y + i, panel_x, line)
            except curses.error:
                pass

        # Fuel bar — replace the numeric fuel line with a visual bar
        bar_y = panel_y + 5
        bar_x = panel_x + 12
        bar_len = 12
        fuel_pct = max(0.0, min(1.0, self.fuel / self.config["fuel"]))
        filled = int(bar_len * fuel_pct)
        bar = "█" * filled + "░" * (bar_len - filled)
        try:
            self.stdscr.addstr(bar_y, bar_x, bar)
        except curses.error:
            pass

        # Difficulty label at top right
        label = self.config["label"]
        diff_x = self.width - len(label) - 3
        try:
            self.stdscr.addstr(1, diff_x, f"[{label}]")
        except curses.error:
            pass

        # Controls hint at bottom
        controls = "←/→: Rotate  ↑/W: Thrust  Q: Quit"
        try:
            self.stdscr.addstr(self.height - 1, (self.width - len(controls)) // 2, controls)
        except curses.error:
            pass

    def _show_result(self):
        """Show landing/crash result screen."""
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
            self.stdscr.addstr(cy - 4, (self.width - len(title)) // 2, title, color_pair | curses.A_BOLD)
        except curses.error:
            pass

        try:
            self.stdscr.addstr(cy - 2, (self.width - len(subtitle)) // 2, subtitle)
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
                self.stdscr.addstr(cy + i, (self.width - len(line)) // 2, line)
            except curses.error:
                pass

        # Landing assessment
        max_speed = self.config["landing_speed_max"]
        max_angle = self.config["landing_angle_max"]
        assessment_lines = []
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

        prompt = "Press any key to exit..."
        try:
            self.stdscr.addstr(self.height - 3, (self.width - len(prompt)) // 2, prompt, curses.A_DIM)
        except curses.error:
            pass

        self.stdscr.refresh()
        self.stdscr.nodelay(False)
        self.stdscr.getch()

    def _title_screen(self):
        """Show title screen. Returns True to continue, False to quit."""
        self.stdscr.erase()

        title_lines = [
            "  ╔═══════════════════════════════╗",
            "  ║     L U N A R   L A N D E R  ║",
            "  ║         ─────────────        ║",
            "  ║     Terminal Edition          ║",
            "  ╚═══════════════════════════════╝",
        ]

        start_y = max(1, (self.height - 20) // 2)

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
                self.stdscr.addstr(start_y + 7 + i, (self.width - 19) // 2, line)
            except curses.error:
                pass

        # Difficulty selection
        diff_y = start_y + 18
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

        quit_line = "  [Q] Quit"
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
            elif key == ord("q") or key == 27:
                return False



def main(stdscr, difficulty=None):
    """Main game entry point (called by curses.wrapper).

    Args:
        stdscr: Curses standard screen.
        difficulty: Optional difficulty override ('easy', 'medium', 'hard').
    """
    # Initialize colors if available
    if curses.has_colors():
        curses.start_color()
        curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)

    try:
        game = LunarLander(stdscr, difficulty=difficulty or "medium")
        game.run()
    except ValueError as e:
        stdscr.erase()
        stdscr.addstr(0, 0, str(e))
        stdscr.refresh()
        stdscr.getch()


if __name__ == "__main__":
    # Parse command-line arguments
    cli_difficulty = None
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
        curses.wrapper(main, cli_difficulty)
    except curses.error as e:
        print(f"Terminal error: {e}", file=sys.stderr)
        print("Make sure your terminal supports curses and is at least 70x24.", file=sys.stderr)
        sys.exit(1)