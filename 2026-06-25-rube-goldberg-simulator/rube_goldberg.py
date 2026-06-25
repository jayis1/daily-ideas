#!/usr/bin/env python3
"""
Rube Goldberg Machine Simulator
================================
A terminal-based ASCII animation of absurdly complex chain-reaction machines.
Watch as balls, dominoes, seesaws, buckets, pulleys, and more interact in
a hilariously over-engineered contraption to accomplish a trivial task.
"""

import random
import time
import sys
import shutil
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

# ── Display constants ──────────────────────────────────────────────
FRAME_DELAY = 0.06  # seconds between frames

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

# ── State tracking ─────────────────────────────────────────────────
IDLE = "idle"
ACTIVE = "active"
TRIGGERED = "triggered"
DONE = "done"


@dataclass
class Component:
    kind: str
    x: int
    y: int
    state: str = IDLE
    timer: int = 0
    direction: int = 1        # 1=right, -1=left
    extra: dict = field(default_factory=dict)

    @property
    def char(self):
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
        return self.state in (TRIGGERED, DONE)


@dataclass
class Projectile:
    """A moving object (ball, water, air) that travels between components."""
    kind: str
    x: float
    y: float
    dx: float
    dy: float
    life: int = 100
    trail: list = field(default_factory=list)

    @property
    def char(self):
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
    """Manages and simulates a complete Rube Goldberg machine."""

    def __init__(self, width=90, height=35):
        self.width = width
        self.height = height
        self.components: List[Component] = []
        self.projectiles: List[Projectile] = []
        self.frame = 0
        self.complete = False
        self.message = ""
        self.message_timer = 0
        self.sparkles: List[Tuple[int, int, int]] = []  # x, y, ttl

    # ── Machine generation ─────────────────────────────────────────

    def generate_machine(self):
        """Generate a random Rube Goldberg machine layout."""
        self.components.clear()
        self.projectiles.clear()

        machine_parts = self._design_machine()
        for part in machine_parts:
            self.components.append(part)

        # Sort by x for visual flow (left to right generally)
        self.components.sort(key=lambda c: (c.y, c.x))

    def _design_machine(self) -> List[Component]:
        """Design a complete multi-stage machine."""
        parts = []
        y_levels = [4, 8, 12, 16, 20, 24]
        num_stages = random.randint(4, 6)

        # Start with a ball at the top-left
        start_x = 4
        start_y = y_levels[0]
        parts.append(Component(BALL, start_x, start_y, state=ACTIVE, timer=1,
                               extra={"fall_to": y_levels[1]}))

        current_x = start_x
        current_y = y_levels[0]

        stage_types = [
            self._stage_domino_chain,
            self._stage_seesaw_launch,
            self._stage_bucket_dump,
            self._stage_hammer_smash,
            self._stage_fan_blow,
            self._stage_spring_launch,
            self._stage_funnel_redirect,
            self._stage_pulley_lift,
        ]

        random.shuffle(stage_types)
        stage_funcs = stage_types[:num_stages]

        for i, stage_func in enumerate(stage_funcs):
            next_y = y_levels[min(i + 1, len(y_levels) - 1)]
            new_parts, current_x, current_y = stage_func(
                current_x, current_y, next_y
            )
            parts.extend(new_parts)

        # End with a bell + flag
        parts.append(Component(BELL, current_x + 3, current_y,
                                state=IDLE, timer=random.randint(8, 15)))
        parts.append(Component(FLAG, current_x + 6, current_y - 1,
                                state=IDLE, timer=random.randint(3, 6)))

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
        """Advance one frame of simulation."""
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
        """Handle component activation effects."""
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

    # ── Rendering ──────────────────────────────────────────────────

    def render(self) -> str:
        """Render the current state as a string for terminal display."""
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

        # Draw border
        lines = []
        lines.append("╔" + "═" * (self.width - 2) + "╗")
        for row in canvas:
            line = "║" + "".join(row) + "║"
            lines.append(line)
        lines.append("╚" + "═" * (self.width - 2) + "╝")

        # Add title
        title = "⚙️  RUBE GOLDBERG MACHINE SIMULATOR  ⚙️"
        title_line = "║" + title.center(self.width - 2) + "║"
        lines[0] = "╔" + "═" * (self.width - 2) + "╗"
        lines[1] = title_line

        # Add status bar
        status = f"  Frame: {self.frame:04d}  │  Components: {len(self.components)}  │  Projectiles: {len(self.projectiles)}"
        if self.complete:
            status += "  │  ✅ COMPLETE!"
        else:
            status += "  │  ⏳ Running..."
        status_line = "║" + status.ljust(self.width - 2) + "║"
        lines.insert(2, status_line)

        # Add message if any
        if self.message:
            msg_line = "║" + f"  {self.message}".center(self.width - 2) + "║"
            lines.insert(3, msg_line)

        return "\n".join(lines)

    def _draw_structure(self, canvas):
        """Draw ramps, rails, and structural elements."""
        # Draw diagonal ramps connecting stages
        for i in range(len(self.components) - 1):
            c1 = self.components[i]
            c2 = self.components[i + 1]
            if c2.x > c1.x and c2.y > c1.y:
                # Draw ramp going down-right
                steps = max(abs(c2.x - c1.x), abs(c2.y - c1.y))
                for s in range(steps):
                    t = s / steps
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


def create_preset_machine(width, height) -> RubeGoldbergMachine:
    """Create a hand-designed preset machine for a guaranteed good show."""
    machine = RubeGoldbergMachine(width, height)

    # Stage 1: Ball rolls down
    machine.components.append(Component(BALL, 5, 5, state=ACTIVE, timer=2,
                                        extra={"fall_to": 9}))

    # Stage 2: Domino chain
    for i in range(5):
        machine.components.append(Component(DOMINO, 12 + i * 3, 9,
                                             state=IDLE, timer=3 + i * 3))

    # Stage 3: Seesaw
    machine.components.append(Component(SEESAW, 30, 9, state=IDLE, timer=18))

    # Stage 4: Spring launch
    machine.components.append(Component(SPRING, 38, 9, state=IDLE, timer=22))

    # Stage 5: Ball flies to bucket
    machine.components.append(Component(BUCKET, 45, 12, state=IDLE, timer=28))

    # Stage 6: Hammer
    machine.components.append(Component(HAMMER, 50, 12, state=IDLE, timer=34))

    # Stage 7: Fan blows ball
    machine.components.append(Component(FAN, 55, 12, state=IDLE, timer=38))

    # Stage 8: Ball rolls to pulley
    machine.components.append(Component(PULLEY, 62, 10, state=IDLE, timer=42))

    # Stage 9: Funnel redirect
    machine.components.append(Component(FUNNEL, 68, 14, state=IDLE, timer=48))

    # Stage 10: Final ball
    machine.components.append(Component(BALL, 73, 14, state=IDLE, timer=52,
                                        extra={"fall_to": 14}))

    # Finale: Bell + Flag
    machine.components.append(Component(BELL, 78, 14, state=IDLE, timer=58))
    machine.components.append(Component(FLAG, 82, 13, state=IDLE, timer=62))

    return machine


def create_random_machine(width, height) -> RubeGoldbergMachine:
    """Create a randomly generated machine."""
    machine = RubeGoldbergMachine(width, height)
    machine.generate_machine()
    return machine


def clear_screen():
    """Clear the terminal screen."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def main():
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

    choice = input("Choose [1/2/3/q]: ").strip()

    if choice == 'q':
        print("Bye! Remember: the hard way is the best way.")
        return

    # Get terminal size
    try:
        size = shutil.get_terminal_size()
        width = min(size.columns - 2, 100)
        height = min(size.lines - 4, 35)
    except:
        width, height = 80, 28

    width = max(width, 50)
    height = max(height, 20)

    if choice == '1':
        machines = [create_preset_machine(width, height)]
    elif choice == '3':
        machines = [create_random_machine(width, height) for _ in range(3)]
    else:
        machines = [create_random_machine(width, height)]

    hide_cursor()
    try:
        for mi, machine in enumerate(machines):
            if len(machines) > 1:
                clear_screen()
                print(f"\n  🎬 Machine {mi + 1}/{len(machines)} 🎬\n")
                time.sleep(2)

            # Reset state for replay
            machine.complete = False
            max_frames = 400  # safety limit

            for _ in range(max_frames):
                machine.step()
                clear_screen()
                print(machine.render())
                print("\n  [Ctrl+C to exit]")

                if machine.complete:
                    # Let the completion message linger
                    for _ in range(40):
                        time.sleep(FRAME_DELAY)
                        machine.step()
                        clear_screen()
                        print(machine.render())
                        print("\n  ✅ Machine complete! ")
                    break

                time.sleep(FRAME_DELAY)

            if not machine.complete:
                print("\n  ⏰ Machine ran out of frames (some parts didn't connect)")

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