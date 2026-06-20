#!/usr/bin/env python3
"""
Procedural Volcano Eruption Simulator
=======================================
A terminal-based ASCII simulation of a volcanic eruption featuring:
- Procedurally generated mountain terrain
- Erupting lava fountains with particles
- Flowing lava that cascades down the slopes
- Ash clouds and smoke plumes
- Earthquake tremors that shake the display
- Day/night cycle with glowing lava at night
- Real-time stats panel (seismic activity, eruption phase, etc.)

Controls:
  SPACE - Trigger eruption
  q     - Quit
  +/-   - Increase/decrease eruption intensity
  r     - Regenerate terrain
  d     - Toggle day/night
"""

import random
import math
import sys
import time
import shutil

# ─── Configuration ────────────────────────────────────────────────────────

ERUPTION_CHARS = ["▓", "▒", "░", "●", "◉", "✦", "✶", "✸", "⬤", "◆"]
LAVA_CHARS = ["▓", "▒", "░", "█", "▄", "▀"]
SMOKE_CHARS = ["░", "▒", "░", ".", "·", "~"]
ASH_CHARS = [".", "·", "•", "∘", "°"]
MOUNTAIN_CHARS = ["▓", "▒", "░", "█", "▄"]

# Color codes (ANSI 256-color)
LAVA_COLORS = [196, 202, 208, 214, 220, 166, 130]
SMOKE_COLORS = [240, 242, 244, 246, 248, 250, 252]
MOUNTAIN_COLORS = [239, 236, 233, 130, 131, 58]
SKY_NIGHT = 16
SKY_DAY = 195
CRATER_GLOW = [196, 202, 208, 214]
ERUPTION_COLORS = [196, 202, 208, 214, 220, 226, 227, 15]


def ansi(code, text=""):
    """Wrap text in ANSI 256-color code."""
    return f"\033[38;5;{code}m{text}"


def ansi_bg(code, text=""):
    """Wrap text in ANSI 256-color background code."""
    return f"\033[48;5;{code}m{text}"


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
BLINK = "\033[5m"


# ─── Particle System ────────────────────────────────────────────────────

class Particle:
    """A single particle (lava bomb, ash, smoke puff)."""
    __slots__ = ['x', 'y', 'vx', 'vy', 'life', 'max_life', 'char', 'color', 'ptype']

    def __init__(self, x, y, vx, vy, life, char, color, ptype):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.char = char
        self.color = color
        self.ptype = ptype


# ─── Volcano Simulator ───────────────────────────────────────────────────

class VolcanoSimulator:
    def __init__(self):
        self.width, self.height = self._get_terminal_size()
        self.width = max(self.width, 60)
        self.height = max(self.height, 20)
        self.frame = 0
        self.running = True

        # Eruption state
        self.eruption_phase = "dormant"  # dormant, building, erupting, subsiding
        self.eruption_intensity = 0.0    # 0.0 to 1.0
        self.target_intensity = 0.0
        self.seismic_activity = 0.0
        self.lava_volume = 0.0
        self.total_eruptions = 0
        self.auto_erupt_timer = random.randint(200, 600)

        # Day/night cycle
        self.is_day = True
        self.day_timer = 0
        self.day_cycle_length = 800  # frames per cycle

        # Terrain
        self.terrain = []  # height at each x column
        self.crater_x = self.width // 2
        self.crater_y = 0  # will be set by generate_terrain
        self.crater_width = 3

        # Particles
        self.particles = []
        self.lava_flows = {}  # (x, y) -> (char, color, age)

        # Shake
        self.shake_x = 0
        self.shake_y = 0
        self.shake_intensity = 0.0

        # Eruption history for stats
        self.eruption_log = []

        self.generate_terrain()

    def _get_terminal_size(self):
        try:
            w, h = shutil.get_terminal_size((80, 24))
            return w, h
        except Exception:
            return 80, 24

    def generate_terrain(self):
        """Procedurally generate volcano mountain terrain."""
        self.terrain = []
        cx = self.width // 2
        mountain_height = int(self.height * 0.55)
        base_y = self.height - 1

        # Generate base terrain with rolling hills
        for x in range(self.width):
            # Distance from center
            dist = abs(x - cx)
            # Volcano shape: steep cone with some noise
            if dist < self.width // 2 - 2:
                h = mountain_height * (1 - (dist / (self.width // 2)) ** 0.8)
                # Add some noise
                h += math.sin(x * 0.3) * 2 + math.sin(x * 0.7) * 1.5
                h = max(0, min(h, mountain_height))
            else:
                h = 0

            y_pos = base_y - int(h)
            self.terrain.append(y_pos)

        # Create crater (indent at top)
        crater_depth = 3
        for dx in range(-self.crater_width, self.crater_width + 1):
            x = cx + dx
            if 0 <= x < self.width:
                depth_factor = 1 - abs(dx) / (self.crater_width + 1)
                self.terrain[x] += int(crater_depth * depth_factor)

        self.crater_y = self.terrain[cx]
        self.lava_flows = {}
        self.particles = []

    def trigger_eruption(self, intensity=1.0):
        """Start an eruption."""
        self.eruption_phase = "building"
        self.target_intensity = intensity
        self.seismic_activity = min(1.0, intensity * 0.7)
        self.total_eruptions += 1
        self.eruption_log.append(self.frame)

    def update_eruption_state(self):
        """Update eruption phase and intensity."""
        if self.eruption_phase == "dormant":
            self.auto_erupt_timer -= 1
            if self.auto_erupt_timer <= 0:
                self.trigger_eruption(random.uniform(0.5, 1.0))
                self.auto_erupt_timer = random.randint(300, 800)
            self.eruption_intensity *= 0.95
            self.seismic_activity *= 0.98
            self.shake_intensity *= 0.9

        elif self.eruption_phase == "building":
            self.eruption_intensity += 0.02
            self.seismic_activity = min(1.0, self.seismic_activity + 0.01)
            self.shake_intensity = self.seismic_activity * 0.5
            if self.eruption_intensity >= self.target_intensity * 0.6:
                self.eruption_phase = "erupting"

        elif self.eruption_phase == "erupting":
            # Oscillate intensity
            self.eruption_intensity += random.uniform(-0.02, 0.03)
            self.eruption_intensity = max(0.3, min(1.0, self.eruption_intensity))
            self.seismic_activity = self.eruption_intensity * 0.6
            self.shake_intensity = self.eruption_intensity * 0.3
            self.lava_volume += self.eruption_intensity * 0.1

            # Chance to start subsiding
            if random.random() < 0.005:
                self.eruption_phase = "subsiding"

        elif self.eruption_phase == "subsiding":
            self.eruption_intensity *= 0.97
            self.seismic_activity *= 0.96
            self.shake_intensity *= 0.95
            if self.eruption_intensity < 0.05:
                self.eruption_phase = "dormant"
                self.eruption_intensity = 0.0
                self.shake_intensity = 0.0

        # Update shake
        if self.shake_intensity > 0.01:
            self.shake_x = random.randint(-int(self.shake_intensity * 3),
                                           int(self.shake_intensity * 3))
            self.shake_y = random.randint(-int(self.shake_intensity * 2),
                                           int(self.shake_intensity * 2))
        else:
            self.shake_x = 0
            self.shake_y = 0

    def spawn_particles(self):
        """Spawn eruption particles based on current state."""
        if self.eruption_phase == "dormant":
            # Gentle smoke from crater
            if random.random() < 0.3:
                px = self.crater_x + random.randint(-1, 1)
                py = self.crater_y
                self.particles.append(Particle(
                    px, py,
                    random.uniform(-0.3, 0.3),
                    random.uniform(-0.5, -0.2),
                    random.randint(20, 60),
                    random.choice(SMOKE_CHARS),
                    random.choice(SMOKE_COLORS),
                    "smoke"
                ))

        elif self.eruption_phase in ("building", "erupting", "subsiding"):
            intensity = self.eruption_intensity

            # Lava bombs
            if random.random() < intensity * 0.6:
                px = self.crater_x + random.randint(-2, 2)
                py = self.crater_y
                angle = random.uniform(-0.8, 0.8)  # slight horizontal spread
                speed = random.uniform(1.5, 4.0) * intensity
                self.particles.append(Particle(
                    px, py,
                    math.sin(angle) * speed * 0.5,
                    -speed,
                    random.randint(30, 80),
                    random.choice(ERUPTION_CHARS),
                    random.choice(ERUPTION_COLORS),
                    "lava"
                ))

            # Ash plume
            for _ in range(int(intensity * 3)):
                if random.random() < 0.7:
                    px = self.crater_x + random.randint(-3, 3)
                    py = self.crater_y - random.randint(0, 3)
                    self.particles.append(Particle(
                        px, py,
                        random.uniform(-0.5, 0.5),
                        random.uniform(-1.0, -0.3),
                        random.randint(40, 100),
                        random.choice(SMOKE_CHARS + ASH_CHARS),
                        random.choice(SMOKE_COLORS),
                        "ash"
                    ))

            # Sparks
            if random.random() < intensity * 0.4:
                px = self.crater_x + random.randint(-1, 1)
                py = self.crater_y
                self.particles.append(Particle(
                    px, py,
                    random.uniform(-2, 2),
                    random.uniform(-3, -1),
                    random.randint(5, 25),
                    random.choice(["✦", "✶", "✸", "*", "✧"]),
                    random.choice([220, 226, 227, 15, 196]),
                    "spark"
                ))

    def update_particles(self):
        """Update all particle positions and lifetimes."""
        alive = []
        for p in self.particles:
            p.life -= 1
            if p.life <= 0:
                continue

            # Gravity
            if p.ptype == "lava":
                p.vy += 0.12
                # Lava that lands on terrain becomes a lava flow
                new_y = int(p.y + p.vy)
                new_x = int(p.x + p.vx)
                if 0 <= new_x < self.width and new_y >= self.terrain[new_x]:
                    # Deposit lava
                    self.lava_flows[(new_x, new_y)] = (
                        random.choice(LAVA_CHARS),
                        random.choice(LAVA_COLORS),
                        self.frame
                    )
                    # Try to spread
                    for dx in [-1, 0, 1]:
                        spread_x = new_x + dx
                        if 0 <= spread_x < self.width:
                            spread_y = self.terrain[spread_x]
                            if (spread_x, spread_y) not in self.lava_flows:
                                if random.random() < 0.15 * self.eruption_intensity:
                                    self.lava_flows[(spread_x, spread_y)] = (
                                        random.choice(LAVA_CHARS),
                                        random.choice(LAVA_COLORS),
                                        self.frame
                                    )
                    continue  # Remove the particle, it's now a flow

            elif p.ptype == "spark":
                p.vy += 0.08

            elif p.ptype == "ash":
                p.vy += 0.01  # Slow drift up
                p.vx += random.uniform(-0.1, 0.1)  # Wind

            elif p.ptype == "smoke":
                p.vy -= 0.01  # Rise
                p.vx += random.uniform(-0.05, 0.05)

            p.x += p.vx
            p.y += p.vy

            # Remove if off screen
            if p.x < -5 or p.x > self.width + 5 or p.y < -5 or p.y > self.height + 5:
                continue

            alive.append(p)

        self.particles = alive

    def update_lava_flows(self):
        """Lava flows age and spread."""
        new_flows = {}
        for (x, y), (char, color, birth) in self.lava_flows.items():
            age = self.frame - birth
            # Lava slowly cools (darker colors over time)
            if age < 100:
                # Try to spread downhill
                if age % 3 == 0 and random.random() < 0.1:
                    for dx in [-1, 1]:
                        nx = x + dx
                        if 0 <= nx < self.width:
                            # Flow downward along terrain
                            ny = self.terrain[nx]
                            if ny >= y - 1 and (nx, ny) not in self.lava_flows:
                                new_flows[(nx, ny)] = (
                                    random.choice(LAVA_CHARS),
                                    color,  # Keep original color
                                    birth + random.randint(0, 10)
                                )
                new_flows[(x, y)] = (char, color, birth)

        # Limit total flows
        if len(new_flows) > 500:
            # Remove oldest
            sorted_flows = sorted(new_flows.items(), key=lambda i: i[1][2])
            new_flows = dict(sorted_flows[-500:])

        self.lava_flows = new_flows

    def update_day_night(self):
        """Toggle day/night cycle."""
        self.day_timer += 1
        if self.day_timer >= self.day_cycle_length:
            self.day_timer = 0
            self.is_day = not self.is_day

    def render(self):
        """Render the entire scene to a string."""
        # Create frame buffer
        buf = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        color_buf = [[0 for _ in range(self.width)] for _ in range(self.height)]
        bg_buf = [[None for _ in range(self.width)] for _ in range(self.height)]

        # Sky color
        sky_color = SKY_DAY if self.is_day else SKY_NIGHT
        # Transition factor
        transition = self.day_timer / self.day_cycle_length

        # Fill background
        for y in range(self.height):
            for x in range(self.width):
                bg_buf[y][x] = sky_color

        # Draw terrain (mountain)
        for x in range(self.width):
            terrain_y = self.terrain[x]
            # Mountain face
            for y in range(terrain_y, self.height):
                if y < 0 or y >= self.height:
                    continue
                depth = y - terrain_y
                if depth < 3:
                    buf[y][x] = random.choice(MOUNTAIN_CHARS[:2]) if self.frame % 5 == 0 else "▓"
                    color_buf[y][x] = 239 if self.is_day else 235
                else:
                    buf[y][x] = "░" if depth > 5 else "▒"
                    color_buf[y][x] = 236 if self.is_day else 233

        # Crater glow during eruption
        if self.eruption_intensity > 0.1:
            glow_range = int(2 + self.eruption_intensity * 3)
            for dx in range(-glow_range, glow_range + 1):
                x = self.crater_x + dx
                if 0 <= x < self.width:
                    y = self.terrain[x]
                    if 0 <= y < self.height:
                        dist = abs(dx)
                        if dist <= glow_range:
                            buf[y][x] = random.choice(ERUPTION_CHARS[:3])
                            brightness = 1 - (dist / (glow_range + 1))
                            if brightness > 0.5:
                                color_buf[y][x] = random.choice([196, 202, 208, 214])
                            else:
                                color_buf[y][x] = random.choice([166, 130, 58])

        # Draw lava flows
        for (x, y), (char, color, birth) in self.lava_flows.items():
            if 0 <= x < self.width and 0 <= y < self.height:
                age = self.frame - birth
                if age < 20:
                    buf[y][x] = random.choice(LAVA_CHARS[:2])
                    color_buf[y][x] = random.choice([196, 202])
                elif age < 60:
                    buf[y][x] = random.choice(LAVA_CHARS)
                    color_buf[y][x] = random.choice([208, 214, 220])
                else:
                    buf[y][x] = "▒"
                    color_buf[y][x] = random.choice([58, 130])

        # Draw particles
        for p in self.particles:
            px, py = int(p.x), int(p.y)
            if 0 <= px < self.width and 0 <= py < self.height:
                life_ratio = p.life / p.max_life
                buf[py][px] = p.char
                color_buf[py][px] = p.color
                # Add glow effect for lava at night
                if not self.is_day and p.ptype in ("lava", "spark"):
                    # Illuminate nearby pixels
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            nx, ny = px + dx, py + dy
                            if 0 <= nx < self.width and 0 <= ny < self.height:
                                if buf[ny][nx] == ' ':
                                    bg_buf[ny][nx] = random.choice([52, 88, 1])

        # Night stars
        if not self.is_day:
            random.seed(self.frame // 50)  # Stars twinkle slowly
            num_stars = self.width // 3
            for _ in range(num_stars):
                sx = random.randint(0, self.width - 1)
                # Only in sky (above terrain)
                if self.terrain[min(sx, self.width - 1)] > 2:
                    sy = random.randint(0, self.terrain[min(sx, self.width - 1)] - 2)
                    if 0 <= sy < self.height and buf[sy][sx] == ' ':
                        if random.random() < 0.3:
                            buf[sy][sx] = random.choice(["·", "•", "✦", "⋆"])
                            color_buf[sy][sx] = random.choice([254, 255, 229, 230])

        # Apply shake offset
        ox = self.shake_x
        oy = self.shake_y

        # Build output string
        lines = []
        for y in range(self.height):
            row = ""
            for x in range(self.width):
                # Apply shake offset
                rx = x - ox if ox >= 0 else x
                ry = y - oy if oy >= 0 else y

                src_x = max(0, min(x + ox, self.width - 1))
                src_y = max(0, min(y + oy, self.height - 1))

                ch = buf[y][x]
                fg = color_buf[y][x]
                bg = bg_buf[y][x]

                if ch != ' ':
                    row += ansi(fg, ch) + RESET
                elif bg is not None and bg != sky_color:
                    row += ansi_bg(bg, " ") + RESET
                else:
                    row += " "
            lines.append(row)

        return lines

    def render_stats(self):
        """Render stats panel at the bottom."""
        phase_colors = {
            "dormant": 34, "building": 226,
            "erupting": 196, "subsiding": 208
        }
        phase_labels = {
            "dormant": "💤 DORMANT", "building": "⚡ BUILDING",
            "erupting": "🌋 ERUPTING!", "subsiding": "📉 SUBSIDING"
        }

        phase = self.eruption_phase
        color = phase_colors.get(phase, 255)
        label = phase_labels.get(phase, phase.upper())

        # Seismic bar
        bar_len = 20
        filled = int(self.seismic_activity * bar_len)
        seismic_bar = "█" * filled + "░" * (bar_len - filled)

        # Intensity bar
        int_filled = int(self.eruption_intensity * bar_len)
        intensity_bar = "█" * int_filled + "░" * (bar_len - int_filled)

        # Eruption count
        stats = (
            f"{ansi(color, BOLD + label + RESET)} │ "
            f"Intensity: {ansi(202, intensity_bar)} {self.eruption_intensity:.0%} │ "
            f"Seismic: {ansi(196, seismic_bar)} │ "
            f"Particles: {len(self.particles):4d} │ "
            f"Lava flows: {len(self.lava_flows):3d} │ "
            f"Eruptions: {self.total_eruptions} │ "
            f"{'☀ DAY' if self.is_day else '🌙 NIGHT'} │ "
            f"[SPACE]Erupt [+/-]Intensity [r]Regen [d]Day/Night [q]uit"
        )
        return stats

    def step(self):
        """Advance one simulation step."""
        self.frame += 1
        self.update_day_night()
        self.update_eruption_state()
        self.spawn_particles()
        self.update_particles()
        self.update_lava_flows()

    def display(self):
        """Render and display the full frame."""
        lines = self.render()
        stats = self.render_stats()

        # Clear screen and render
        output = "\033[H"  # Move cursor to home
        output += "\n".join(lines)
        output += "\n" + "─" * min(self.width, 120) + "\n"
        output += stats + "\n"
        output += f"Frame: {self.frame:6d} │ Lava Volume: {self.lava_volume:.1f}m³ │ Auto-erupt in: {max(0, self.auto_erupt_timer):4d} frames"

        sys.stdout.write(output + RESET)
        sys.stdout.flush()


# ─── Non-blocking Input ──────────────────────────────────────────────────

def get_key_press():
    """Check for a key press without blocking. Returns key char or None."""
    import select
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1)
    return None


# ─── Main Loop ────────────────────────────────────────────────────────────

def main():
    sim = VolcanoSimulator()

    # Setup terminal
    print("\033[?25l")  # Hide cursor
    print("\033[2J")     # Clear screen

    # Enable non-blocking input
    import tty, termios
    old_settings = None
    try:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        tty.setcbreak(fd)
    except Exception:
        pass

    try:
        while sim.running:
            # Check for input
            try:
                key = get_key_press()
                if key == 'q':
                    sim.running = False
                elif key == ' ':
                    sim.trigger_eruption(random.uniform(0.6, 1.0))
                elif key == '+' or key == '=':
                    sim.target_intensity = min(1.0, sim.target_intensity + 0.1)
                    if sim.eruption_phase == "dormant":
                        sim.eruption_phase = "building"
                elif key == '-' or key == '_':
                    sim.target_intensity = max(0.0, sim.target_intensity - 0.1)
                elif key == 'r':
                    sim.generate_terrain()
                elif key == 'd':
                    sim.is_day = not sim.is_day
            except Exception:
                pass

            sim.step()
            sim.display()
            time.sleep(0.05)  # ~20 FPS

    finally:
        # Restore terminal
        print(RESET)
        print("\033[?25h")  # Show cursor
        if old_settings:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)
            except Exception:
                pass


if __name__ == "__main__":
    main()