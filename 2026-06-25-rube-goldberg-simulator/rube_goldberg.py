#!/usr/bin/env python3
"""
Rube Goldberg Machine Simulator
================================
A terminal-based ASCII animation of absurdly complex chain-reaction machines.
Watch as balls, dominoes, seesaws, buckets, pulleys, and more interact in
a hilariously over-engineered contraption to accomplish a trivial task.

Usage:
    python3 rube_goldberg.py                  # Interactive menu
    python3 rube_goldberg.py --preset         # Run preset machine
    python3 rube_goldberg.py --random         # Run random machine
    python3 rube_goldberg.py --marathon       # Run 3 random machines
    python3 rube_goldberg.py --seed 42        # Use specific random seed
    python3 rube_goldberg.py --speed 0.03     # Faster animation
    python3 rube_goldberg.py --describe       # Print machine description, no animation
    python3 rube_goldberg.py --version        # Show version
    python3 rube_goldberg.py --help           # Show help
"""

import argparse
import random
import time
import sys
import shutil
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ── Version ────────────────────────────────────────────────────────
__version__ = "1.1.0"

# ── Display constants ──────────────────────────────────────────────
FRAME_DELAY = 0.06  # seconds between frames
MAX_FRAMES = 400    # safety limit per machine

# ── ANSI color codes ──────────────────────────────────────────────
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_BLUE = "\033[34m"
ANSI_MAGENTA = "\033[35m"
ANSI_CYAN = "\033[36m"
ANSI_WHITE = "\033[37m"

# Component type identifiers
BALL = "ball"
DOMINO = "domino"
SEESAW = "seesaw"
BUCKET = "bucket"
PULLEY = "pulley"
FAN = "fan"
CANDLE = "candle"
BALLOON = "balloon"
HAMMER = "hammer"
FUNNEL = "funnel"
SPRING = "spring"
BELL = "bell"
FLAG = "flag"
DOMINO_CHAIN = "domino_chain"

# ── Visual representations ─────────────────────────────────────────
COMPONENT_CHARS = {
    BALL:       "●",
    DOMINO:     "▌",
    SEESAW:     "—",
    BUCKET:     "╘╤╛",
    PULLEY:     "⊙",
    FAN:        "✦",
    CANDLE:     "¥",
    BALLOON:    "○",
    HAMMER:     "⌐",
    FUNNEL:     "▽",
    SPRING:     "⌇",
    BELL:       "♫",
    FLAG:       "⚑",
}

# ── Component color map (for --color mode) ────────────────────────
COMPONENT_COLORS = {
    BALL:    ANSI_CYAN,
    DOMINO:  ANSI_YELLOW,
    SEESAW:  ANSI_GREEN,
    BUCKET:  ANSI_BLUE,
    PULLEY:  ANSI_MAGENTA,
    FAN:     ANSI_WHITE,
    CANDLE:  ANSI_RED,
    BALLOON: ANSI_RED,
    HAMMER:  ANSI_YELLOW,
    FUNNEL:  ANSI_GREEN,
    SPRING:  ANSI_CYAN,
    BELL:    ANSI_YELLOW,
    FLAG:    ANSI_GREEN,
}

# ── Stage descriptions (for --describe mode) ───────────────────────
STAGE_DESCRIPTIONS = {
    "domino_chain":    "A row of dominoes falls in sequence, each knocking into the next",
    "seesaw_launch":   "A seesaw tips and flings a ball upward to the next contraption",
    "bucket_dump":     "A bucket tips over, spilling its contents onto the next stage",
    "hammer_smash":    "A hammer swings down with great force, triggering a spring below",
    "fan_blow":        "A fan blows a gust of air, pushing a ball along a rail",
    "spring_launch":   "A spring compresses and launches a ball skyward",
    "funnel_redirect": "A funnel catches a ball and redirects it downward",
    "pulley_lift":     "A pulley system lifts a ball up to a higher track",
}

# ── State tracking ─────────────────────────────────────────────────
IDLE = "idle"
ACTIVE = "active"
TRIGGERED = "triggered"
DONE = "done"


@dataclass
class Component:
    """A single mechanical component in the Rube Goldberg machine.

    Attributes:
        kind: The component type (ball, domino, seesaw, etc.)
        x: Horizontal position on the canvas
        y: Vertical position on the canvas
        state: Current state (idle/active/triggered/done)
        timer: Frames remaining until next state transition
        direction: 1 for right, -1 for left
        extra: Additional properties (e.g., fall_to target y coordinate)
        stage_name: Optional name of the stage this component belongs to
    """
    kind: str
    x: int
    y: int
    state: str = IDLE
    timer: int = 0
    direction: int = 1
    extra: dict = field(default_factory=dict)
    stage_name: str = ""

    @property
    def char(self):
        """Return the display character for this component based on its kind and state."""
        if self.kind == BUCKET and self.state == TRIGGERED:
            return "╘╤╛"
        if self.kind == BUCKET and self.state == DONE:
            return "╘═╛"
        if self.kind == SEESAW:
            if self.state == IDLE:
                return "—"
            elif self.state == ACTIVE:
                return "/"
            else:
                return "\\"
        if self.kind == HAMMER and self.state == TRIGGERED:
            return "⌐"
        if self.kind == DOMINO:
            if self.state == IDLE:
                return "▌"
            return "▀"
        if self.kind == FLAG and self.state == DONE:
            return "⚑"
        if self.kind == FLAG:
            return "⚐"
        return COMPONENT_CHARS.get(self.kind, "?")

    @property
    def triggered(self):
        """Whether this component has been triggered or is done."""
        return self.state in (TRIGGERED, DONE)

    def describe(self) -> str:
        """Return a human-readable description of this component."""
        label = self.stage_name or self.kind.replace("_", " ").title()
        state_label = {
            IDLE: "waiting",
            ACTIVE: "activating",
            TRIGGERED: "triggered",
            DONE: "done",
        }.get(self.state, self.state)
        return f"{label} at ({self.x}, {self.y}) [{state_label}]"


@dataclass
class Projectile:
    """A moving object (ball, water, air, spark) that travels between components.

    Attributes:
        kind: Projectile type (ball/water/spark/air)
        x: Current horizontal position (float for smooth motion)
        y: Current vertical position (float for smooth motion)
        dx: Horizontal velocity per frame
        dy: Vertical velocity per frame
        life: Frames remaining before the projectile disappears
        trail: List of recent (x, y) positions for drawing trails
    """
    kind: str
    x: float
    y: float
    dx: float
    dy: float
    life: int = 100
    trail: list = field(default_factory=list)

    @property
    def char(self):
        """Return the display character for this projectile type."""
        if self.kind == "ball":
            return "●"
        if self.kind == "water":
            return "≈"
        if self.kind == "spark":
            return "✦"
        if self.kind == "air":
            return "~"
        return "•"


class RubeGoldbergMachine:
    """Manages and simulates a complete Rube Goldberg machine.

    The machine consists of components placed on a 2D canvas. Each component
    has a timer that counts down; when it reaches zero, the component activates
    and may spawn projectiles. The simulation advances frame by frame until
    the flag component reaches the DONE state.

    Attributes:
        width: Canvas width in characters
        height: Canvas height in characters
        components: List of mechanical components
        projectiles: List of moving objects
        frame: Current simulation frame number
        complete: Whether the machine has finished running
        color: Whether to use ANSI color codes in rendering
        seed: Random seed used for reproducibility (0 = not set)
    """

    def __init__(self, width=90, height=35, color=False, seed=0):
        self.width = width
        self.height = height
        self.components: List[Component] = []
        self.projectiles: List[Projectile] = []
        self.frame = 0
        self.complete = False
        self.message = ""
        self.message_timer = 0
        self.sparkles: List[Tuple[int, int, int]] = []  # x, y, ttl
        self.color = color
        self.seed = seed
        self._stage_log: List[str] = []  # tracks which stages were used

    # ── Machine generation ─────────────────────────────────────────

    def generate_machine(self):
        """Generate a random Rube Goldberg machine layout.

        Uses the instance's seed if set for reproducible results.
        The machine consists of 4-6 randomly selected stages, plus
        a start ball and a finale (bell + flag).
        """
        if self.seed:
            random.seed(self.seed)

        self.components.clear()
        self.projectiles.clear()
        self._stage_log.clear()

        machine_parts = self._design_machine()
        for part in machine_parts:
            self.components.append(part)

        # Sort by x for visual flow (left to right generally)
        self.components.sort(key=lambda c: (c.y, c.x))

    def _design_machine(self) -> List[Component]:
        """Design a complete multi-stage machine.

        Returns a list of Component objects arranged in a cascading
        layout from top-left to bottom-right.
        """
        parts = []
        y_levels = [4, 8, 12, 16, 20, 24]
        num_stages = random.randint(4, 6)

        # Start with a ball at the top-left
        start_x = 4
        start_y = y_levels[0]
        parts.append(Component(BALL, start_x, start_y, state=ACTIVE, timer=1,
                               extra={"fall_to": y_levels[1]},
                               stage_name="Starting Ball"))

        current_x = start_x
        current_y = y_levels[0]

        stage_types = [
            ("domino_chain",    self._stage_domino_chain),
            ("seesaw_launch",   self._stage_seesaw_launch),
            ("bucket_dump",     self._stage_bucket_dump),
            ("hammer_smash",    self._stage_hammer_smash),
            ("fan_blow",        self._stage_fan_blow),
            ("spring_launch",   self._stage_spring_launch),
            ("funnel_redirect", self._stage_funnel_redirect),
            ("pulley_lift",     self._stage_pulley_lift),
        ]

        random.shuffle(stage_types)
        stage_funcs = stage_types[:num_stages]

        for i, (stage_name, stage_func) in enumerate(stage_funcs):
            self._stage_log.append(stage_name)
            next_y = y_levels[min(i + 1, len(y_levels) - 1)]
            new_parts, current_x, current_y = stage_func(
                current_x, current_y, next_y
            )
            # Tag components with their stage name
            for part in new_parts:
                if not part.stage_name:
                    part.stage_name = stage_name.replace("_", " ").title()
            parts.extend(new_parts)

        # End with a bell + flag
        parts.append(Component(BELL, current_x + 3, current_y,
                                state=IDLE, timer=random.randint(8, 15),
                                stage_name="Grand Finale Bell"))
        parts.append(Component(FLAG, current_x + 6, current_y - 1,
                                state=IDLE, timer=random.randint(3, 6),
                                stage_name="Victory Flag"))

        return parts

    def _stage_domino_chain(self, x, y, next_y) -> Tuple[List[Component], int, int]:
        """A row of dominoes that fall in sequence."""
        parts = []
        num = random.randint(4, 7)
        end_x = x + num * 3
        for i in range(num):
            dx = x + i * 3
            delay = i * 3 + 2
            parts.append(Component(DOMINO, dx, y, state=IDLE, timer=delay))
        # Ball at end launches to next level
        parts.append(Component(BALL, end_x + 2, y, state=IDLE,
                               timer=num * 3 + 4,
                               extra={"fall_to": next_y}))
        return parts, end_x + 2, y

    def _stage_seesaw_launch(self, x, y, next_y) -> Tuple[List[Component], int, int]:
        """A seesaw that flings a ball upward."""
        parts = []
        sx = x + 6
        parts.append(Component(SEESAW, sx, y, state=IDLE, timer=3))
        parts.append(Component(BALL, sx + 8, y - 3, state=IDLE, timer=7,
                               extra={"fall_to": next_y}))
        return parts, sx + 8, y - 3

    def _stage_bucket_dump(self, x, y, next_y) -> Tuple[List[Component], int, int]:
        """A bucket that tips over and spills a ball."""
        parts = []
        bx = x + 5
        parts.append(Component(BUCKET, bx, y, state=IDLE, timer=4))
        parts.append(Component(BALL, bx + 5, next_y, state=IDLE, timer=10,
                               extra={"fall_to": next_y}))
        return parts, bx + 5, next_y

    def _stage_hammer_smash(self, x, y, next_y) -> Tuple[List[Component], int, int]:
        """A hammer that whacks something, sending a ball flying."""
        parts = []
        hx = x + 5
        parts.append(Component(HAMMER, hx, y - 1, state=IDLE, timer=4))
        parts.append(Component(SPRING, hx + 3, y, state=IDLE, timer=7))
        parts.append(Component(BALL, hx + 6, y, state=IDLE, timer=10,
                               extra={"fall_to": next_y}))
        return parts, hx + 6, y

    def _stage_fan_blow(self, x, y, next_y) -> Tuple[List[Component], int, int]:
        """A fan that blows a ball sideways."""
        parts = []
        fx = x + 4
        parts.append(Component(FAN, fx, y, state=IDLE, timer=3))
        parts.append(Component(BALL, fx + 8, y, state=IDLE, timer=8,
                               extra={"fall_to": next_y}))
        return parts, fx + 8, y

    def _stage_spring_launch(self, x, y, next_y) -> Tuple[List[Component], int, int]:
        """A spring that bounces a ball up."""
        parts = []
        sx = x + 4
        parts.append(Component(SPRING, sx, y, state=IDLE, timer=3))
        parts.append(Component(BALL, sx + 3, y, state=IDLE, timer=6,
                               extra={"fall_to": next_y}))
        return parts, sx + 3, y

    def _stage_funnel_redirect(self, x, y, next_y) -> Tuple[List[Component], int, int]:
        """A funnel that redirects a ball."""
        parts = []
        fx = x + 5
        parts.append(Component(FUNNEL, fx, y, state=IDLE, timer=4))
        parts.append(Component(BALL, fx + 3, y + 2, state=IDLE, timer=8,
                               extra={"fall_to": next_y}))
        return parts, fx + 3, y + 2

    def _stage_pulley_lift(self, x, y, next_y) -> Tuple[List[Component], int, int]:
        """A pulley that lifts a ball."""
        parts = []
        px = x + 6
        parts.append(Component(PULLEY, px, y - 2, state=IDLE, timer=3))
        parts.append(Component(BALL, px + 4, next_y, state=IDLE, timer=8,
                               extra={"fall_to": next_y}))
        return parts, px + 4, next_y

    # ── Simulation ─────────────────────────────────────────────────

    def step(self):
        """Advance one frame of simulation.

        Updates component timers and state transitions, moves projectiles
        with gravity physics, decays sparkle effects, and checks for
        machine completion (flag reaching DONE state).
        """
        self.frame += 1

        # Update component timers
        for comp in self.components:
            if comp.state == IDLE:
                comp.timer -= 1
                if comp.timer <= 0:
                    comp.state = ACTIVE
                    comp.timer = random.randint(3, 8)
                    self._activate_component(comp)
            elif comp.state == ACTIVE:
                comp.timer -= 1
                if comp.timer <= 0:
                    comp.state = TRIGGERED
                    comp.timer = random.randint(5, 12)
            elif comp.state == TRIGGERED:
                comp.timer -= 1
                if comp.timer <= 0:
                    comp.state = DONE

        # Update projectiles
        new_projectiles = []
        for proj in self.projectiles:
            proj.trail.append((proj.x, proj.y))
            if len(proj.trail) > 6:
                proj.trail.pop(0)
            proj.x += proj.dx
            proj.y += proj.dy
            proj.dy += 0.15  # gravity
            proj.life -= 1
            # Add sparkle at position
            if self.frame % 2 == 0:
                self.sparkles.append((int(proj.x), int(proj.y), 4))
            if proj.life > 0 and 0 <= proj.x < self.width and 0 <= proj.y < self.height:
                new_projectiles.append(proj)

        self.projectiles = new_projectiles

        # Update sparkles
        self.sparkles = [(x, y, ttl - 1) for x, y, ttl in self.sparkles if ttl > 1]

        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer <= 0:
                self.message = ""

        # Check for completion
        flags = [c for c in self.components if c.kind == FLAG]
        if flags and all(f.state == DONE for f in flags):
            self.complete = True
            self.message = "🎉  MACHINE COMPLETE!  🎉"
            self.message_timer = 30

    def _activate_component(self, comp):
        """Handle component activation effects.

        When a component transitions to ACTIVE state, it may spawn
        projectiles (balls, water, air) and sparkles for visual effect.
        """
        if comp.kind == BALL:
            target_y = comp.extra.get("fall_to", comp.y + 5)
            dy = 0.3 if target_y > comp.y else -0.3
            dx = random.uniform(0.5, 1.5)
            self.projectiles.append(Projectile("ball", comp.x, comp.y, dx, dy, life=40))

        elif comp.kind == DOMINO:
            # Domino falls and creates a small spark
            self.sparkles.append((comp.x + 1, comp.y, 6))

        elif comp.kind == SEESAW:
            self.projectiles.append(
                Projectile("ball", comp.x + 3, comp.y - 2, 1.2, -1.0, life=25))

        elif comp.kind == BUCKET:
            # Bucket tips - spill water drops
            for i in range(3):
                self.projectiles.append(
                    Projectile("water", comp.x + 2 + i, comp.y,
                               random.uniform(0.3, 0.8), random.uniform(0.2, 0.6), life=20))

        elif comp.kind == HAMMER:
            self.sparkles.append((comp.x + 2, comp.y + 1, 8))

        elif comp.kind == FAN:
            for i in range(5):
                self.projectiles.append(
                    Projectile("air", comp.x + 2 + i, comp.y + random.uniform(-0.5, 0.5),
                               random.uniform(0.5, 1.5), random.uniform(-0.3, 0.3), life=15))

        elif comp.kind == SPRING:
            self.projectiles.append(
                Projectile("ball", comp.x + 1, comp.y - 1, 0.8, -1.5, life=30))

        elif comp.kind == FUNNEL:
            self.projectiles.append(
                Projectile("ball", comp.x + 2, comp.y + 1, 0.5, 0.8, life=20))

        elif comp.kind == PULLEY:
            self.projectiles.append(
                Projectile("ball", comp.x + 2, comp.y, 1.0, -0.5, life=25))

        elif comp.kind == BELL:
            self.message = "🔔 DING!"
            self.message_timer = 10
            for _ in range(8):
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(1, 3)
                self.sparkles.append((
                    int(comp.x + math.cos(angle) * dist),
                    int(comp.y + math.sin(angle) * dist),
                    8
                ))

        elif comp.kind == FLAG:
            self.message = "⚑ Task accomplished!"
            self.message_timer = 20

    # ── Machine description ────────────────────────────────────────

    def describe(self) -> str:
        """Return a human-readable description of the machine's stages.

        Lists each stage type and a brief explanation of what it does.
        Useful for understanding what a randomly generated machine will do
        before watching the animation.
        """
        lines = []
        lines.append("⚙️  Rube Goldberg Machine — Stage Description")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Canvas size: {self.width} × {self.height}")
        lines.append(f"Total components: {len(self.components)}")
        lines.append(f"Seed: {self.seed or 'random'}")
        lines.append("")

        if self._stage_log:
            lines.append("Stages (in order):")
            lines.append("-" * 40)
            for i, stage_name in enumerate(self._stage_log, 1):
                desc = STAGE_DESCRIPTIONS.get(stage_name, "A mysterious mechanism")
                lines.append(f"  {i}. {stage_name.replace('_', ' ').title()}")
                lines.append(f"     {desc}")
                lines.append("")
        else:
            # Preset machine — describe components directly
            lines.append("Components (in order):")
            lines.append("-" * 40)
            for i, comp in enumerate(self.components, 1):
                lines.append(f"  {i}. {comp.describe()}")
            lines.append("")

        # Count component types
        type_counts = {}
        for comp in self.components:
            type_counts[comp.kind] = type_counts.get(comp.kind, 0) + 1
        lines.append("Component summary:")
        for kind, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {kind}: {count}")

        lines.append("")
        lines.append("Finale: 🔔 Bell → ⚑ Flag raised!")
        return "\n".join(lines)

    # ── Rendering ──────────────────────────────────────────────────

    def render(self) -> str:
        """Render the current state as a string for terminal display.

        Draws the canvas with structural elements (ramps, rails, columns),
        components with state indicators, projectile trails, sparkle effects,
        a title bar, status line, and any active messages.
        """
        # Create canvas
        canvas = [[' ' for _ in range(self.width)] for _ in range(self.height)]

        # Draw structural lines (ramps, rails, pipes)
        self._draw_structure(canvas)

        # Draw components
        for comp in self.components:
            cx, cy = comp.x, comp.y
            if 0 <= cy < self.height:
                ch = comp.char
                for i, c in enumerate(ch):
                    px = cx + i
                    if 0 <= px < self.width:
                        canvas[cy][px] = c

                # State indicators
                if comp.state == ACTIVE:
                    if 0 <= cy - 1 < self.height and 0 <= cx < self.width:
                        canvas[cy - 1][cx] = "✧" if cx < self.width - 1 else " "
                elif comp.state == TRIGGERED:
                    if 0 <= cy - 1 < self.height and 0 <= cx < self.width:
                        canvas[cy - 1][cx] = "✶" if cx < self.width - 1 else " "

        # Draw projectiles
        for proj in self.projectiles:
            px, py = int(proj.x), int(proj.y)
            if 0 <= py < self.height and 0 <= px < self.width:
                canvas[py][px] = proj.char
            # Draw trail
            for i, (tx, ty) in enumerate(proj.trail):
                itx, ity = int(tx), int(ty)
                if 0 <= ity < self.height and 0 <= itx < self.width:
                    alpha_chars = "·.:"
                    ch = alpha_chars[min(i, 2)] if i < 3 else "·"
                    if canvas[ity][itx] == ' ':
                        canvas[ity][itx] = ch

        # Draw sparkles
        for sx, sy, ttl in self.sparkles:
            if 0 <= sy < self.height and 0 <= sx < self.width:
                sparkle_chars = "✦✧✶✴*·"
                idx = min(ttl, len(sparkle_chars) - 1)
                canvas[sy][sx] = sparkle_chars[idx]

        # Build the final display lines
        lines = []

        # Title bar
        title = "⚙️  RUBE GOLDBERG MACHINE SIMULATOR  ⚙️"
        title_line = "║" + title.center(self.width - 2) + "║"
        lines.append("╔" + "═" * (self.width - 2) + "╗")
        lines.append(title_line)

        # Status bar
        status = f"  Frame: {self.frame:04d}  │  Components: {len(self.components)}  │  Projectiles: {len(self.projectiles)}"
        if self.complete:
            status += "  │  ✅ COMPLETE!"
        else:
            status += "  │  ⏳ Running..."
        status_line = "║" + status.ljust(self.width - 2) + "║"
        lines.append(status_line)

        # Message line
        if self.message:
            msg_line = "║" + f"  {self.message}".center(self.width - 2) + "║"
            lines.append(msg_line)

        # Canvas rows
        for row in canvas:
            line = "║" + "".join(row) + "║"
            lines.append(line)

        # Bottom border
        lines.append("╚" + "═" * (self.width - 2) + "╝")

        # Apply colors if enabled
        if self.color:
            lines = self._apply_colors(lines)

        return "\n".join(lines)

    def _apply_colors(self, lines: List[str]) -> List[str]:
        """Apply ANSI color codes to the rendered lines.

        Colors are applied based on component types, projectile types,
        and special elements like the border, title, and status bar.
        """
        colored_lines = []
        for i, line in enumerate(lines):
            if i == 0 or i == len(lines) - 1:
                # Border lines — dim
                colored_lines.append(ANSI_DIM + line + ANSI_RESET)
            elif i == 1:
                # Title line — bold yellow
                colored_lines.append(ANSI_BOLD + ANSI_YELLOW + line + ANSI_RESET)
            elif i == 2:
                # Status line — cyan
                colored_lines.append(ANSI_CYAN + line + ANSI_RESET)
            else:
                # Canvas rows — apply per-component coloring
                new_line = ""
                for ch in line:
                    colored = False
                    # Check each component type's character
                    if ch == "●":
                        new_line += ANSI_CYAN + ch + ANSI_RESET
                        colored = True
                    elif ch == "▌" or ch == "▀":
                        new_line += ANSI_YELLOW + ch + ANSI_RESET
                        colored = True
                    elif ch in ("/", "\\", "—"):
                        new_line += ANSI_GREEN + ch + ANSI_RESET
                        colored = True
                    elif ch in ("╘", "╤", "╛", "═"):
                        new_line += ANSI_BLUE + ch + ANSI_RESET
                        colored = True
                    elif ch == "⊙":
                        new_line += ANSI_MAGENTA + ch + ANSI_RESET
                        colored = True
                    elif ch == "✦":
                        new_line += ANSI_WHITE + ch + ANSI_RESET
                        colored = True
                    elif ch == "⌐":
                        new_line += ANSI_YELLOW + ch + ANSI_RESET
                        colored = True
                    elif ch == "▽":
                        new_line += ANSI_GREEN + ch + ANSI_RESET
                        colored = True
                    elif ch == "⌇":
                        new_line += ANSI_CYAN + ch + ANSI_RESET
                        colored = True
                    elif ch == "♫":
                        new_line += ANSI_BOLD + ANSI_YELLOW + ch + ANSI_RESET
                        colored = True
                    elif ch == "⚑" or ch == "⚐":
                        new_line += ANSI_BOLD + ANSI_GREEN + ch + ANSI_RESET
                        colored = True
                    elif ch == "≈":
                        new_line += ANSI_BLUE + ch + ANSI_RESET
                        colored = True
                    elif ch == "~":
                        new_line += ANSI_DIM + ANSI_WHITE + ch + ANSI_RESET
                        colored = True
                    elif ch in ("✧", "✶", "✴", "*"):
                        new_line += ANSI_YELLOW + ch + ANSI_RESET
                        colored = True
                    elif ch == "·":
                        new_line += ANSI_DIM + ch + ANSI_RESET
                        colored = True
                    else:
                        new_line += ch
                colored_lines.append(new_line)
        return colored_lines

    def _draw_structure(self, canvas):
        """Draw ramps, rails, and structural elements on the canvas.

        Connects adjacent components with diagonal ramps, draws horizontal
        rails under certain component types, and adds support columns
        under heavy components.
        """
        # Draw diagonal ramps connecting stages
        for i in range(len(self.components) - 1):
            c1 = self.components[i]
            c2 = self.components[i + 1]
            if c2.x > c1.x and c2.y > c1.y:
                # Draw ramp going down-right
                steps = max(abs(c2.x - c1.x), abs(c2.y - c1.y))
                for s in range(steps):
                    t = s / max(steps, 1)
                    rx = int(c1.x + t * (c2.x - c1.x))
                    ry = int(c1.y + t * (c2.y - c1.y))
                    if 0 <= ry < self.height and 0 <= rx < self.width:
                        canvas[ry][rx] = "╲"

        # Draw some horizontal rails
        for comp in self.components:
            if comp.kind in (DOMINO, SEESAW, SPRING, FUNNEL):
                for rx in range(max(0, comp.x - 2), min(self.width, comp.x + 4)):
                    if 0 <= comp.y + 1 < self.height:
                        if canvas[comp.y + 1][rx] == ' ':
                            canvas[comp.y + 1][rx] = "─"

        # Draw support columns
        for comp in self.components:
            if comp.kind in (BUCKET, PULLEY, BELL, FLAG):
                col_x = min(comp.x + 1, self.width - 1)
                for ry in range(comp.y + 1, min(self.height, comp.y + 4)):
                    if 0 <= col_x < self.width and canvas[ry][col_x] == ' ':
                        canvas[ry][col_x] = "│"


def create_preset_machine(width, height, color=False) -> RubeGoldbergMachine:
    """Create a hand-designed preset machine for a guaranteed good show.

    The preset machine features 10 carefully placed stages with known
    timing that reliably produces a satisfying chain reaction from
    start to finish.

    Args:
        width: Canvas width in characters
        height: Canvas height in characters
        color: Whether to enable ANSI color output

    Returns:
        A configured RubeGoldbergMachine ready to run.
    """
    machine = RubeGoldbergMachine(width, height, color=color)
    machine._stage_log = [
        "Starting Ball", "Domino Chain", "Seesaw Launch", "Spring Launch",
        "Bucket Dump", "Hammer Smash", "Fan Blow", "Pulley Lift",
        "Funnel Redirect", "Final Ball"
    ]

    # Stage 1: Ball rolls down
    machine.components.append(Component(BALL, 5, 5, state=ACTIVE, timer=2,
                                        extra={"fall_to": 9},
                                        stage_name="Starting Ball"))

    # Stage 2: Domino chain
    for i in range(5):
        machine.components.append(Component(DOMINO, 12 + i * 3, 9,
                                             state=IDLE, timer=3 + i * 3,
                                             stage_name="Domino Chain"))

    # Stage 3: Seesaw
    machine.components.append(Component(SEESAW, 30, 9, state=IDLE, timer=18,
                                        stage_name="Seesaw Launch"))

    # Stage 4: Spring launch
    machine.components.append(Component(SPRING, 38, 9, state=IDLE, timer=22,
                                         stage_name="Spring Launch"))

    # Stage 5: Ball flies to bucket
    machine.components.append(Component(BUCKET, 45, 12, state=IDLE, timer=28,
                                        stage_name="Bucket Dump"))

    # Stage 6: Hammer
    machine.components.append(Component(HAMMER, 50, 12, state=IDLE, timer=34,
                                         stage_name="Hammer Smash"))

    # Stage 7: Fan blows ball
    machine.components.append(Component(FAN, 55, 12, state=IDLE, timer=38,
                                         stage_name="Fan Blow"))

    # Stage 8: Ball rolls to pulley
    machine.components.append(Component(PULLEY, 62, 10, state=IDLE, timer=42,
                                         stage_name="Pulley Lift"))

    # Stage 9: Funnel redirect
    machine.components.append(Component(FUNNEL, 68, 14, state=IDLE, timer=48,
                                         stage_name="Funnel Redirect"))

    # Stage 10: Final ball
    machine.components.append(Component(BALL, 73, 14, state=IDLE, timer=52,
                                        extra={"fall_to": 14},
                                        stage_name="Final Ball"))

    # Finale: Bell + Flag
    machine.components.append(Component(BELL, 78, 14, state=IDLE, timer=58,
                                        stage_name="Grand Finale Bell"))
    machine.components.append(Component(FLAG, 82, 13, state=IDLE, timer=62,
                                         stage_name="Victory Flag"))

    return machine


def create_random_machine(width, height, color=False, seed=0) -> RubeGoldbergMachine:
    """Create a randomly generated machine.

    Args:
        width: Canvas width in characters
        height: Canvas height in characters
        color: Whether to enable ANSI color output
        seed: Random seed for reproducibility (0 = random)

    Returns:
        A configured RubeGoldbergMachine ready to run.
    """
    machine = RubeGoldbergMachine(width, height, color=color, seed=seed)
    machine.generate_machine()
    return machine


def clear_screen():
    """Clear the terminal screen using ANSI escape codes."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def hide_cursor():
    """Hide the terminal cursor using ANSI escape codes."""
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    """Show the terminal cursor using ANSI escape codes."""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def get_terminal_size():
    """Get terminal size with sensible defaults.

    Returns:
        Tuple of (width, height) in characters, clamped to
        reasonable minimum and maximum values.
    """
    try:
        size = shutil.get_terminal_size()
        width = min(size.columns - 2, 100)
        height = min(size.lines - 4, 35)
    except Exception:
        width, height = 80, 28

    width = max(width, 50)
    height = max(height, 20)
    return width, height


def run_machine(machine: RubeGoldbergMachine, speed: float = FRAME_DELAY):
    """Run the animation loop for a single machine.

    Args:
        machine: The machine to animate
        speed: Delay between frames in seconds (lower = faster)

    Returns:
        True if the machine completed successfully, False if it ran out of frames
    """
    max_frames = MAX_FRAMES

    for _ in range(max_frames):
        machine.step()
        clear_screen()
        print(machine.render())
        print("\n  [Ctrl+C to exit]")

        if machine.complete:
            # Let the completion message linger
            for _ in range(40):
                time.sleep(speed)
                machine.step()
                clear_screen()
                print(machine.render())
                print("\n  ✅ Machine complete!")
            return True

        time.sleep(speed)

    # Machine didn't complete within the frame limit
    print("\n  ⏰ Machine ran out of frames (some parts didn't connect)")
    return False


def run_interactive(speed: float = FRAME_DELAY, color: bool = False, seed: int = 0):
    """Run the interactive menu mode.

    Presents the user with options to choose a preset, random, or marathon
    machine, then runs the animation.

    Args:
        speed: Animation speed (seconds per frame)
        color: Whether to enable ANSI colors
        seed: Random seed (0 = random each time)
    """
    print("\n⚙️  RUBE GOLDBERG MACHINE SIMULATOR ⚙️")
    print("=" * 40)
    print()
    print("Watch an absurdly complex chain-reaction machine")
    print("accomplish a trivially simple task!")
    print()
    print("Options:")
    print("  [1] Preset machine (guaranteed good show)")
    print("  [2] Random machine (every time is different)")
    print("  [3] Generate 3 random machines (marathon!)")
    print("  [q] Quit")
    print()

    try:
        choice = input("Choose [1/2/3/q]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nBye! Remember: the hard way is the best way.")
        return

    if choice == 'q':
        print("Bye! Remember: the hard way is the best way.")
        return

    width, height = get_terminal_size()

    if choice == '1':
        machines = [create_preset_machine(width, height, color=color)]
    elif choice == '3':
        machines = []
        for i in range(3):
            s = seed + i if seed else 0
            machines.append(create_random_machine(width, height, color=color, seed=s))
    else:
        machines = [create_random_machine(width, height, color=color, seed=seed)]

    hide_cursor()
    try:
        for mi, machine in enumerate(machines):
            if len(machines) > 1:
                clear_screen()
                print(f"\n  🎬 Machine {mi + 1}/{len(machines)} 🎬\n")
                time.sleep(2)

            # Reset state for replay
            machine.complete = False
            run_machine(machine, speed=speed)

            if mi < len(machines) - 1:
                time.sleep(3)

    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        clear_screen()
        print("\n⚙️  Thanks for watching the Rube Goldberg Machine! ⚙️\n")
        print("Remember: any sufficiently complicated task")
        print("can be accomplished by an even more complicated machine.\n")


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for CLI options.

    Returns:
        Configured ArgumentParser with all supported options.
    """
    parser = argparse.ArgumentParser(
        prog="rube_goldberg",
        description="⚙️  Rube Goldberg Machine Simulator — watch absurdly complex "
                    "chain-reaction machines accomplish trivially simple tasks!",
        epilog="Examples:\n"
               "  python3 rube_goldberg.py                  # Interactive menu\n"
               "  python3 rube_goldberg.py --preset           # Run preset machine\n"
               "  python3 rube_goldberg.py --random --seed 42 # Reproducible random\n"
               "  python3 rube_goldberg.py --marathon --color # Colorful marathon\n"
               "  python3 rube_goldberg.py --describe --random # Print description only",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
        help="Show version number and exit"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--preset", action="store_true",
        help="Run the hand-designed preset machine (guaranteed good show)"
    )
    mode.add_argument(
        "--random", action="store_true",
        help="Run a randomly generated machine"
    )
    mode.add_argument(
        "--marathon", action="store_true",
        help="Run 3 random machines back-to-back"
    )
    parser.add_argument(
        "--seed", type=int, default=0,
        help="Random seed for reproducible machines (default: random each run)"
    )
    parser.add_argument(
        "--speed", type=float, default=FRAME_DELAY,
        help=f"Animation delay in seconds (default: {FRAME_DELAY}; lower = faster)"
    )
    parser.add_argument(
        "--color", action="store_true",
        help="Enable ANSI color output"
    )
    parser.add_argument(
        "--describe", action="store_true",
        help="Print a text description of the machine instead of animating"
    )
    parser.add_argument(
        "--width", type=int, default=0,
        help="Canvas width (default: auto-detect from terminal)"
    )
    parser.add_argument(
        "--height", type=int, default=0,
        help="Canvas height (default: auto-detect from terminal)"
    )
    return parser


def main():
    """Main entry point — parse CLI args and run the simulator."""
    parser = build_parser()
    args = parser.parse_args()

    # Determine canvas dimensions
    if args.width > 0 and args.height > 0:
        width = max(args.width, 50)
        height = max(args.height, 20)
    else:
        width, height = get_terminal_size()

    # Clamp speed to reasonable range
    speed = max(0.01, min(args.speed, 1.0))

    # Build the machine(s)
    seed = args.seed

    if args.preset:
        machines = [create_preset_machine(width, height, color=args.color)]
    elif args.marathon:
        machines = []
        for i in range(3):
            s = seed + i if seed else 0
            machines.append(create_random_machine(width, height, color=args.color, seed=s))
    elif args.random:
        machines = [create_random_machine(width, height, color=args.color, seed=seed)]
    else:
        # No mode specified — go interactive
        if args.describe:
            # Describe mode without a specific machine type: default to random
            machines = [create_random_machine(width, height, color=args.color, seed=seed)]
        else:
            return run_interactive(speed=speed, color=args.color, seed=seed)

    # Describe mode: just print description and exit
    if args.describe:
        for i, machine in enumerate(machines):
            if len(machines) > 1:
                print(f"\n{'=' * 50}")
                print(f"Machine {i + 1} of {len(machines)}")
                print(f"{'=' * 50}")
            print(machine.describe())
        return

    # Run animation
    hide_cursor()
    try:
        for mi, machine in enumerate(machines):
            if len(machines) > 1:
                clear_screen()
                print(f"\n  🎬 Machine {mi + 1}/{len(machines)} 🎬\n")
                time.sleep(2)

            machine.complete = False
            run_machine(machine, speed=speed)

            if mi < len(machines) - 1:
                time.sleep(3)

    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        clear_screen()
        print("\n⚙️  Thanks for watching the Rube Goldberg Machine! ⚙️\n")
        print("Remember: any sufficiently complicated task")
        print("can be accomplished by an even more complicated machine.\n")


if __name__ == "__main__":
    main()