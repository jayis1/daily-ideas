#!/usr/bin/env python3
"""
Procedural Volcano Eruption Simulator
=======================================
A terminal-based ASCII simulation of a volcanic eruption featuring:
- Procedurally generated mountain terrain
- Erupting lava fountains with particles
- Flowing lava that cascades down the slopes
- Ash clouds and smoke plumes
- Pyroclastic flows rushing down the mountainside
- Earthquake tremors that shake the display
- Day/night cycle with glowing lava at night
- Multiple eruption types (Hawaiian, Strombolian, Vulcanian, Plinian)
- VEI (Volcanic Explosivity Index) tracking
- Real-time stats panel (seismic activity, eruption phase, etc.)
- Screenshot save capability

Controls:
  SPACE - Trigger eruption
  q     - Quit
  +/-   - Increase/decrease eruption intensity
  r     - Regenerate terrain
  d     - Toggle day/night
  t     - Cycle eruption type
  s     - Save screenshot
  ?     - Show controls overlay

CLI Flags:
  --version           Show version and exit
  --help              Show help and exit
  --seed SEED         Set random seed for reproducible terrain
  --intensity FLOAT   Set initial eruption intensity (0.0-1.0)
  --type TYPE         Set eruption type (hawaiian, strombolian, vulcanian, plinian)
  --fps FPS           Set frames per second (default 20)
  --no-auto-erupt    Disable automatic eruptions
  --night             Start in night mode
  --width W           Override terminal width
  --height H          Override terminal height
"""

import argparse
import math
import os
import random
import shutil
import sys
import time
from datetime import datetime

__version__ = "2.1.0"

# ─── Configuration ────────────────────────────────────────────────────────

ERUPTION_CHARS = ["▓", "▒", "░", "●", "◉", "✦", "✶", "✸", "⬤", "◆"]
LAVA_CHARS = ["▓", "▒", "░", "█", "▄", "▀"]
SMOKE_CHARS = ["░", "▒", "░", ".", "·", "~"]
ASH_CHARS = [".", "·", "•", "∘", "°"]
MOUNTAIN_CHARS = ["▓", "▒", "░", "█", "▄"]
PYROCLASTIC_CHARS = ["█", "▓", "▒", "░", "●"]

# Color codes (ANSI 256-color)
LAVA_COLORS = [196, 202, 208, 214, 220, 166, 130]
SMOKE_COLORS = [240, 242, 244, 246, 248, 250, 252]
MOUNTAIN_COLORS = [239, 236, 233, 130, 131, 58]
SKY_NIGHT = 16
SKY_DAY = 195
CRATER_GLOW = [196, 202, 208, 214]
ERUPTION_COLORS = [196, 202, 208, 214, 220, 226, 227, 15]
PYROCLASTIC_COLORS = [196, 202, 208, 166, 130]

# Eruption type profiles: (name, intensity_mult, particle_rate, lava_rate, ash_rate, pyroclastic_chance)
ERUPTION_TYPES = {
    "hawaiian": {
        "label": "🌋 HAWAIIAN",
        "intensity_range": (0.3, 0.6),
        "particle_rate": 0.4,
        "ash_rate": 0.2,
        "lava_flow_rate": 0.4,
        "pyroclastic_chance": 0.0,
        "shake_mult": 0.5,
        "description": "Gentle lava fountains, fluid lava flows",
    },
    "strombolian": {
        "label": "💥 STROMBOLIAN",
        "intensity_range": (0.5, 0.8),
        "particle_rate": 0.6,
        "ash_rate": 0.4,
        "lava_flow_rate": 0.3,
        "pyroclastic_chance": 0.05,
        "shake_mult": 0.8,
        "description": "Moderate explosions, incandescent bombs",
    },
    "vulcanian": {
        "label": "💨 VULCANIAN",
        "intensity_range": (0.6, 0.9),
        "particle_rate": 0.5,
        "ash_rate": 0.7,
        "lava_flow_rate": 0.2,
        "pyroclastic_chance": 0.15,
        "shake_mult": 1.0,
        "description": "Violent ash eruptions, dense plumes",
    },
    "plinian": {
        "label": "☁️  PLINIAN",
        "intensity_range": (0.8, 1.0),
        "particle_rate": 0.8,
        "ash_rate": 0.9,
        "lava_flow_rate": 0.1,
        "pyroclastic_chance": 0.3,
        "shake_mult": 1.5,
        "description": "Catastrophic column, massive ash plume",
    },
}

ERUPTION_TYPE_NAMES = list(ERUPTION_TYPES.keys())


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
    """A single particle (lava bomb, ash, smoke puff, pyroclastic)."""
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


# ─── Pyroclastic Flow ────────────────────────────────────────────────────

class PyroclasticFlow:
    """A pyroclastic flow that rushes down the mountain slope."""

    def __init__(self, start_x, start_y, direction, speed, width, life):
        self.x = float(start_x)
        self.y = float(start_y)
        self.direction = direction  # -1 = left, 1 = right
        self.speed = speed
        self.width = width  # how wide the flow front is
        self.life = life
        self.max_life = life
        self.cells = set()  # (x, y) cells occupied
        self.active = True

    def update(self, terrain, width, height):
        """Advance the pyroclastic flow downhill."""
        if not self.active:
            return

        self.life -= 1
        if self.life <= 0:
            self.active = False
            return

        # Move the head of the flow downhill and sideways
        self.x += self.direction * self.speed

        ix = int(self.x)
        if 0 <= ix < width:
            # Flow follows terrain downhill
            self.y = terrain[ix]
            # Expand width over time as it flows
            current_width = min(self.width + int(self.max_life - self.life) // 5,
                                8)
            for dy in range(current_width):
                if 0 <= self.y + dy < height:
                    self.cells.add((ix, self.y + dy))
            # Also mark cells slightly behind
            for dx in range(1, min(4, int(self.speed * 3))):
                bx = ix - dx * self.direction
                if 0 <= bx < width:
                    for dy in range(current_width - dx):
                        cy = terrain[bx]
                        if 0 <= cy + dy < height:
                            self.cells.add((bx, cy + dy))

        # Slowly die out
        if self.life < self.max_life * 0.3:
            # Start removing old cells
            self.cells = set(list(self.cells)[1:])


# ─── Volcano Simulator ───────────────────────────────────────────────────

class VolcanoSimulator:
    """Main volcano eruption simulator class."""

    def __init__(self, seed=None, initial_intensity=None, eruption_type=None,
                 auto_erupt=True, start_night=False, width=None, height=None):
        self.width, self.height = self._get_terminal_size()
        if width:
            self.width = max(60, width)
        if height:
            self.height = max(20, height)
        self.width = max(self.width, 60)
        self.height = max(self.height, 20)
        self.frame = 0
        self.running = True
        self.seed = seed
        self.auto_erupt = auto_erupt

        if seed is not None:
            random.seed(seed)

        # Eruption state
        self.eruption_phase = "dormant"  # dormant, building, erupting, subsiding
        self.eruption_intensity = 0.0    # 0.0 to 1.0
        self.target_intensity = 0.0
        self.seismic_activity = 0.0
        self.lava_volume = 0.0
        self.total_eruptions = 0
        self.auto_erupt_timer = random.randint(200, 600)

        # Eruption type
        self.eruption_type = eruption_type or "strombolian"
        if self.eruption_type not in ERUPTION_TYPES:
            self.eruption_type = "strombolian"
        self.eruption_type_index = ERUPTION_TYPE_NAMES.index(self.eruption_type)

        # VEI (Volcanic Explosivity Index) tracking
        self.vei = 0  # 0-8 scale
        self.max_vei = 0
        self.vei_history = []  # list of (frame, vei) tuples

        # Day/night cycle
        self.is_day = not start_night
        self.day_timer = 0
        self.day_cycle_length = 800  # frames per cycle
        self.day_transition = 1.0 if self.is_day else 0.0  # smooth transition

        # Terrain
        self.terrain = []  # height at each x column
        self.crater_x = self.width // 2
        self.crater_y = 0  # will be set by generate_terrain
        self.crater_width = 3

        # Particles
        self.particles = []
        self.lava_flows = {}  # (x, y) -> (char, color, age)

        # Pyroclastic flows
        self.pyroclastic_flows = []

        # Shake
        self.shake_x = 0
        self.shake_y = 0
        self.shake_intensity = 0.0

        # Eruption history for stats
        self.eruption_log = []  # list of (frame, type, peak_intensity)

        # Screenshot data
        self.last_screenshot = None

        # Set initial intensity if provided
        if initial_intensity is not None and initial_intensity > 0:
            self.trigger_eruption(initial_intensity)

        self.generate_terrain()

    def _get_terminal_size(self):
        """Get terminal dimensions with fallback."""
        try:
            w, h = shutil.get_terminal_size((80, 24))
            return w, h
        except Exception:
            return 80, 24

    def generate_terrain(self):
        """Procedurally generate volcano mountain terrain."""
        if self.seed is not None:
            random.seed(self.seed + self.total_eruptions)

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
                # Add some noise for natural look
                h += math.sin(x * 0.3) * 2 + math.sin(x * 0.7) * 1.5
                h += random.uniform(-0.5, 0.5)
                h = max(0, min(h, mountain_height))
            else:
                h = 0

            y_pos = base_y - int(h)
            self.terrain.append(y_pos)

        # Smooth terrain to avoid jagged edges
        smoothed = self.terrain[:]
        for _ in range(2):
            for i in range(1, len(smoothed) - 1):
                smoothed[i] = (self.terrain[i - 1] + self.terrain[i] * 2 +
                               self.terrain[i + 1]) / 4
            self.terrain = [int(v) for v in smoothed]

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
        self.pyroclastic_flows = []

    def trigger_eruption(self, intensity=None):
        """Start an eruption with given or random intensity based on eruption type."""
        etype = ERUPTION_TYPES[self.eruption_type]
        if intensity is None:
            lo, hi = etype["intensity_range"]
            intensity = random.uniform(lo, hi)
        intensity = max(0.0, min(1.0, intensity))

        # Very low intensity (< 0.05) triggers a brief rumble then subsides
        if intensity < 0.05:
            self.eruption_phase = "subsiding"
            self.target_intensity = 0.0
            self.seismic_activity = min(1.0, intensity * 2)
            self.total_eruptions += 1
            self.eruption_log.append((self.frame, self.eruption_type, intensity))
            return

        self.eruption_phase = "building"
        self.target_intensity = intensity
        self.seismic_activity = min(1.0, intensity * 0.7)
        self.total_eruptions += 1
        self.eruption_log.append((self.frame, self.eruption_type, intensity))

        # Set initial VEI based on intensity and type
        if self.eruption_type == "hawaiian":
            self.vei = max(0, min(2, int(intensity * 2)))
        elif self.eruption_type == "strombolian":
            self.vei = max(1, min(4, int(intensity * 4)))
        elif self.eruption_type == "vulcanian":
            self.vei = max(2, min(5, int(intensity * 5)))
        elif self.eruption_type == "plinian":
            self.vei = max(3, min(8, int(intensity * 8)))
        else:
            self.vei = max(0, min(8, int(intensity * 5)))

        self.max_vei = max(self.max_vei, self.vei)

        # Chance to spawn a pyroclastic flow
        if random.random() < etype["pyroclastic_chance"] * intensity:
            direction = random.choice([-1, 1])
            speed = random.uniform(0.8, 2.0)
            width = random.randint(1, 3)
            life = random.randint(40, 80)
            self.pyroclastic_flows.append(PyroclasticFlow(
                self.crater_x, self.crater_y, direction, speed, width, life
            ))

    def cycle_eruption_type(self):
        """Cycle to the next eruption type."""
        self.eruption_type_index = (self.eruption_type_index + 1) % len(ERUPTION_TYPE_NAMES)
        self.eruption_type = ERUPTION_TYPE_NAMES[self.eruption_type_index]

    def update_eruption_state(self):
        """Update eruption phase and intensity."""
        etype = ERUPTION_TYPES[self.eruption_type]
        shake_mult = etype["shake_mult"]

        if self.eruption_phase == "dormant":
            if self.auto_erupt:
                self.auto_erupt_timer -= 1
                if self.auto_erupt_timer <= 0:
                    self.trigger_eruption()
                    self.auto_erupt_timer = random.randint(300, 800)
            self.eruption_intensity *= 0.95
            self.seismic_activity *= 0.98
            self.shake_intensity *= 0.9
            # Decay VEI during dormancy
            self.vei = max(0, self.vei - 0.02)

        elif self.eruption_phase == "building":
            self.eruption_intensity += 0.02
            self.seismic_activity = min(1.0, self.seismic_activity + 0.01)
            self.shake_intensity = self.seismic_activity * 0.5 * shake_mult
            # Transition to erupting when we reach at least 60% of target or a minimum of 0.05
            threshold = max(0.05, self.target_intensity * 0.6)
            if self.eruption_intensity >= threshold:
                self.eruption_phase = "erupting"

        elif self.eruption_phase == "erupting":
            # Oscillate intensity
            self.eruption_intensity += random.uniform(-0.02, 0.03)
            self.eruption_intensity = max(0.3, min(1.0, self.eruption_intensity))
            self.seismic_activity = self.eruption_intensity * 0.6
            self.shake_intensity = self.eruption_intensity * 0.3 * shake_mult
            self.lava_volume += self.eruption_intensity * 0.1

            # Update VEI dynamically
            self.vei = min(8, max(0, self.eruption_intensity * 8 * (
                1 if self.eruption_type == "hawaiian" else
                2 if self.eruption_type == "strombolian" else
                3 if self.eruption_type == "vulcanian" else 4
            )))
            self.max_vei = max(self.max_vei, self.vei)

            # Chance to spawn pyroclastic flow during eruption
            if random.random() < etype["pyroclastic_chance"] * 0.01 * self.eruption_intensity:
                direction = random.choice([-1, 1])
                self.pyroclastic_flows.append(PyroclasticFlow(
                    self.crater_x, self.crater_y, direction,
                    random.uniform(0.5, 1.5), random.randint(1, 2),
                    random.randint(30, 60)
                ))

            # Chance to start subsiding
            if random.random() < 0.005:
                self.eruption_phase = "subsiding"

        elif self.eruption_phase == "subsiding":
            self.eruption_intensity *= 0.97
            self.seismic_activity *= 0.96
            self.shake_intensity *= 0.95
            self.vei = max(0, self.vei - 0.1)
            if self.eruption_intensity < 0.05:
                self.eruption_phase = "dormant"
                self.eruption_intensity = 0.0
                self.shake_intensity = 0.0

        # Record VEI
        if self.frame % 10 == 0:
            self.vei_history.append((self.frame, int(self.vei)))
            # Keep only last 100 entries
            if len(self.vei_history) > 100:
                self.vei_history = self.vei_history[-100:]

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
        """Spawn eruption particles based on current state and eruption type."""
        etype = ERUPTION_TYPES[self.eruption_type]

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
            if random.random() < intensity * etype["particle_rate"]:
                px = self.crater_x + random.randint(-2, 2)
                py = self.crater_y
                angle = random.uniform(-0.8, 0.8)
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

            # Ash plume — rate varies by type
            ash_count = int(intensity * etype["ash_rate"] * 3)
            for _ in range(ash_count):
                if random.random() < 0.7:
                    px = self.crater_x + random.randint(-3, 3)
                    py = self.crater_y - random.randint(0, 3)
                    # Plinian eruptions have wider, taller ash columns
                    spread = 0.5 if self.eruption_type != "plinian" else 1.0
                    rise = -1.0 if self.eruption_type != "plinian" else -1.5
                    self.particles.append(Particle(
                        px, py,
                        random.uniform(-spread, spread),
                        random.uniform(rise, -0.3),
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
                    etype = ERUPTION_TYPES[self.eruption_type]
                    for dx in [-1, 0, 1]:
                        spread_x = new_x + dx
                        if 0 <= spread_x < self.width:
                            spread_y = self.terrain[spread_x]
                            if (spread_x, spread_y) not in self.lava_flows:
                                if random.random() < 0.15 * self.eruption_intensity * etype["lava_flow_rate"] * 3:
                                    self.lava_flows[(spread_x, spread_y)] = (
                                        random.choice(LAVA_CHARS),
                                        random.choice(LAVA_COLORS),
                                        self.frame
                                    )
                    continue  # Remove the particle, it's now a flow

            elif p.ptype == "spark":
                p.vy += 0.08

            elif p.ptype == "ash":
                p.vy += 0.01  # Slow drift up (negative vy)
                p.vx += random.uniform(-0.1, 0.1)  # Wind

            elif p.ptype == "smoke":
                p.vy -= 0.01  # Rise
                p.vx += random.uniform(-0.05, 0.05)

            p.x += p.vx
            p.y += p.vy

            # Remove if off screen
            if p.x < -5 or p.x > self.width + 5 or p.y < -10 or p.y > self.height + 5:
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
            sorted_flows = sorted(new_flows.items(), key=lambda item: item[1][2])
            new_flows = dict(sorted_flows[-500:])

        self.lava_flows = new_flows

    def update_pyroclastic_flows(self):
        """Update pyroclastic flows."""
        active_flows = []
        for pf in self.pyroclastic_flows:
            pf.update(self.terrain, self.width, self.height)
            if pf.active:
                active_flows.append(pf)
        self.pyroclastic_flows = active_flows

    def update_day_night(self):
        """Smooth day/night cycle transition."""
        self.day_timer += 1
        if self.day_timer >= self.day_cycle_length:
            self.day_timer = 0
            self.is_day = not self.is_day

        # Smooth transition
        if self.is_day:
            self.day_transition = min(1.0, self.day_transition + 0.005)
        else:
            self.day_transition = max(0.0, self.day_transition - 0.005)

    def render(self):
        """Render the entire scene to a string."""
        # Create frame buffer
        buf = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        color_buf = [[0 for _ in range(self.width)] for _ in range(self.height)]
        bg_buf = [[None for _ in range(self.width)] for _ in range(self.height)]

        # Sky color with smooth day/night blending
        # Interpolate between night (16) and day (195) based on day_transition
        sky_color = int(SKY_NIGHT + (SKY_DAY - SKY_NIGHT) * self.day_transition)

        # Fill background
        for y in range(self.height):
            for x in range(self.width):
                bg_buf[y][x] = sky_color

        # Draw terrain (mountain)
        # Use a deterministic seed for mountain chars so they don't flicker
        mt_rng = random.Random(self.seed if self.seed is not None else 42)
        for x in range(self.width):
            terrain_y = self.terrain[x]
            # Mountain face
            for y in range(terrain_y, self.height):
                if y < 0 or y >= self.height:
                    continue
                depth = y - terrain_y
                if depth < 3:
                    # Use deterministic char based on position so it doesn't flicker
                    char_idx = (x + y * 7) % len(MOUNTAIN_CHARS[:2])
                    buf[y][x] = MOUNTAIN_CHARS[:2][char_idx]
                    # Blend mountain colors with day/night
                    day_color = 239
                    night_color = 235
                    color_buf[y][x] = int(night_color + (day_color - night_color) * self.day_transition)
                else:
                    buf[y][x] = "░" if depth > 5 else "▒"
                    day_color = 236
                    night_color = 233
                    color_buf[y][x] = int(night_color + (day_color - night_color) * self.day_transition)

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

        # Draw pyroclastic flows
        for pf in self.pyroclastic_flows:
            life_ratio = pf.life / pf.max_life
            for (cx, cy) in pf.cells:
                if 0 <= cx < self.width and 0 <= cy < self.height:
                    buf[cy][cx] = random.choice(PYROCLASTIC_CHARS)
                    if life_ratio > 0.6:
                        color_buf[cy][cx] = random.choice([196, 202, 208])
                    elif life_ratio > 0.3:
                        color_buf[cy][cx] = random.choice(PYROCLASTIC_COLORS)
                    else:
                        color_buf[cy][cx] = random.choice([130, 58])

        # Draw particles
        for p in self.particles:
            px, py = int(p.x), int(p.y)
            if 0 <= px < self.width and 0 <= py < self.height:
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
            star_rng = random.Random(self.frame // 50)  # Stars twinkle slowly
            num_stars = self.width // 3
            for _ in range(num_stars):
                sx = star_rng.randint(0, self.width - 1)
                # Only in sky (above terrain)
                if self.terrain[min(sx, self.width - 1)] > 2:
                    sy = star_rng.randint(0, self.terrain[min(sx, self.width - 1)] - 2)
                    if 0 <= sy < self.height and buf[sy][sx] == ' ':
                        if star_rng.random() < 0.3:
                            buf[sy][sx] = star_rng.choice(["·", "•", "✦", "⋆"])
                            color_buf[sy][sx] = star_rng.choice([254, 255, 229, 230])

        # Apply earthquake shake offset to the buffer
        if self.shake_intensity > 0.01:
            sx = self.shake_x
            sy = self.shake_y
            if sx != 0 or sy != 0:
                # Shift buffer contents by shake offset
                new_buf = [[' ' for _ in range(self.width)] for _ in range(self.height)]
                new_color = [[0 for _ in range(self.width)] for _ in range(self.height)]
                new_bg = [[None for _ in range(self.width)] for _ in range(self.height)]
                for y in range(self.height):
                    for x in range(self.width):
                        # Source position (shifted opposite to shake)
                        src_y = y - sy
                        src_x = x - sx
                        if 0 <= src_y < self.height and 0 <= src_x < self.width:
                            new_buf[y][x] = buf[src_y][src_x]
                            new_color[y][x] = color_buf[src_y][src_x]
                            new_bg[y][x] = bg_buf[src_y][src_x]
                        else:
                            new_buf[y][x] = ' '
                            new_color[y][x] = 0
                            new_bg[y][x] = sky_color
                buf = new_buf
                color_buf = new_color
                bg_buf = new_bg

        # Build output string
        lines = []
        for y in range(self.height):
            row = ""
            for x in range(self.width):
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
        """Render stats panel at the bottom, adapting to terminal width."""
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

        # Adapt bar length to terminal width
        bar_len = max(8, min(20, self.width // 5))

        # Seismic bar
        filled = int(self.seismic_activity * bar_len)
        seismic_bar = "█" * filled + "░" * (bar_len - filled)

        # Intensity bar
        int_filled = int(self.eruption_intensity * bar_len)
        intensity_bar = "█" * int_filled + "░" * (bar_len - int_filled)

        # Eruption type info
        etype = ERUPTION_TYPES[self.eruption_type]
        etype_label = etype["label"]

        # VEI display
        vei_bar = "▓" * int(self.vei) + "░" * max(0, 8 - int(self.vei))

        # Stats line 1
        stats1 = (
            f"{ansi(color, BOLD + label + RESET)} │ "
            f"{etype_label} │ "
            f"VEI: {ansi(202, vei_bar)} {self.vei:.0f} │ "
            f"Intensity: {ansi(202, intensity_bar)} {self.eruption_intensity:.0%}"
        )

        # Stats line 2
        stats2 = (
            f"Seismic: {ansi(196, seismic_bar)} │ "
            f"Particles: {len(self.particles):4d} │ "
            f"Lava: {len(self.lava_flows):3d} │ "
            f"Eruptions: {self.total_eruptions} │ "
            f"{'☀ DAY' if self.is_day else '🌙 NIGHT'} │ "
            f"Max VEI: {self.max_vei:.0f}"
        )

        # Controls line — adapt to width
        full_controls = "[SPACE]Erupt [+/-]Intensity [t]Type [r]Regen [d]Day/Night [s]Screenshot [q]uit"
        short_controls = "[SPACE]Erupt [+/-]Int [t]Type [r]Regen [d]Night [s]Save [q]uit"
        if self.width < 70:
            stats3 = short_controls
        else:
            stats3 = full_controls

        return stats1, stats2, stats3

    def step(self):
        """Advance one simulation step."""
        self.frame += 1
        self.update_day_night()
        self.update_eruption_state()
        self.spawn_particles()
        self.update_particles()
        self.update_lava_flows()
        self.update_pyroclastic_flows()

    def display(self):
        """Render and display the full frame."""
        lines = self.render()
        stats1, stats2, stats3 = self.render_stats()

        # Move cursor home and clear to end of screen to remove stale content
        output = "\033[H\033[J"
        output += "\n".join(lines)
        separator = "─" * min(self.width, 120)
        output += "\n" + separator + "\n"
        output += stats1 + "\n"
        output += stats2 + "\n"
        output += separator + "\n"
        output += stats3 + "\n"
        output += f"Frame: {self.frame:6d} │ Lava Volume: {self.lava_volume:.1f}m³ │ " \
                  f"Auto-erupt: {'ON' if self.auto_erupt else 'OFF'} " \
                  f"({max(0, self.auto_erupt_timer):4d}f) │ " \
                  f"Pyroclastic: {len(self.pyroclastic_flows)}"

        sys.stdout.write(output + RESET)
        sys.stdout.flush()

    def save_screenshot(self):
        """Save current frame as a text file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"volcano_screenshot_{timestamp}.txt"
        lines = self.render()
        stats1, stats2, stats3 = self.render_stats()

        # Strip ANSI codes for plain text save
        import re
        def strip_ansi(text):
            return re.sub(r'\033\[[0-9;]*m', '', text)

        content = strip_ansi("\n".join(lines)) + "\n"
        content += "─" * 60 + "\n"
        content += strip_ansi(stats1) + "\n"
        content += strip_ansi(stats2) + "\n"
        content += f"Frame: {self.frame} | Eruptions: {self.total_eruptions} | " \
                   f"Type: {self.eruption_type} | VEI: {self.vei:.0f}\n"

        try:
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
            with open(filepath, "w") as f:
                f.write(content)
            self.last_screenshot = filepath
            return filepath
        except Exception as e:
            self.last_screenshot = None
            return f"Error: {e}"


# ─── Non-blocking Input ──────────────────────────────────────────────────

def get_key_press():
    """Check for a key press without blocking. Returns key char or None."""
    import select
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1)
    return None


# ─── Argument Parsing ─────────────────────────────────────────────────────

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="🌋 Procedural Volcano Eruption Simulator — terminal-based ASCII art",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Controls (while running):
  SPACE   Trigger a new eruption
  +/=     Increase eruption intensity
  -       Decrease eruption intensity
  t       Cycle eruption type (Hawaiian → Strombolian → Vulcanian → Plinian)
  r       Regenerate terrain (new mountain)
  d       Toggle day/night
  s       Save screenshot to text file
  q       Quit

Eruption Types:
  hawaiian    — Gentle lava fountains, fluid lava flows
  strombolian — Moderate explosions, incandescent bombs
  vulcanian   — Violent ash eruptions, dense plumes
  plinian     — Catastrophic column, massive ash plume
"""
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible terrain generation")
    parser.add_argument("--intensity", type=float, default=None,
                        help="Initial eruption intensity (0.0-1.0)")
    parser.add_argument("--type", dest="eruption_type", default=None,
                        choices=list(ERUPTION_TYPES.keys()),
                        help="Eruption type: hawaiian, strombolian, vulcanian, plinian")
    parser.add_argument("--fps", type=int, default=20,
                        help="Frames per second (default: 20)")
    parser.add_argument("--no-auto-erupt", action="store_true",
                        help="Disable automatic eruptions")
    parser.add_argument("--night", action="store_true",
                        help="Start in night mode")
    parser.add_argument("--width", type=int, default=None,
                        help="Override terminal width")
    parser.add_argument("--height", type=int, default=None,
                        help="Override terminal height")
    return parser.parse_args()


# ─── Main Loop ────────────────────────────────────────────────────────────

def main():
    """Entry point for the volcano eruption simulator."""
    args = parse_args()

    sim = VolcanoSimulator(
        seed=args.seed,
        initial_intensity=args.intensity,
        eruption_type=args.eruption_type,
        auto_erupt=not args.no_auto_erupt,
        start_night=args.night,
        width=args.width,
        height=args.height,
    )

    fps = max(1, min(60, args.fps))
    delay = 1.0 / fps

    # Setup terminal
    print("\033[?25l")  # Hide cursor
    print("\033[2J")     # Clear screen

    # Enable non-blocking input
    import tty
    import termios
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
                elif key == 't':
                    sim.cycle_eruption_type()
                elif key == 's':
                    path = sim.save_screenshot()
                    # Brief flash notification
                    if path:
                        print(f"\033[s\033[{sim.height + 4};0H" +
                              ansi(226, f"  📸 Screenshot saved: {path}") + RESET +
                              " " * 20)
                        sys.stdout.flush()
                elif key == '?':
                    pass  # Could show help overlay
            except Exception:
                pass

            sim.step()
            sim.display()
            time.sleep(delay)

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