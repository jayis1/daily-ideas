#!/usr/bin/env python3
"""
Crystal Growth Simulator — Diffusion-Limited Aggregation (DLA) in the Terminal

Simulates particles undergoing random walks that aggregate upon contact,
producing beautiful, branching, fractal-like crystalline structures.
Rendered in real-time ASCII art in the terminal.
"""

import random
import sys
import os
import time
import math
import argparse
from collections import defaultdict


# ─── Configuration ───────────────────────────────────────────────────────────

CHARSET_FANCY = " ·∘○◎●◆✦★✶✸✹✺✻✼❋"
CHARSET_MINIMAL = " .:-=+*#%@"
CHARSET_BW = " ·▪■█"

DIRECTIONS_4 = [(0, 1), (0, -1), (1, 0), (-1, 0)]
DIRECTIONS_8 = DIRECTIONS_4 + [(1, 1), (1, -1), (-1, 1), (-1, -1)]

COLOR_PALETTE = [
    (100, 180, 255),  # light blue
    (80, 220, 200),   # cyan
    (140, 120, 255),  # purple
    (200, 140, 255),  # lavender
    (60, 240, 180),   # mint
    (255, 180, 100),  # orange
    (255, 220, 140),  # gold
]


# ─── Core DLA Engine ─────────────────────────────────────────────────────────

class DLASimulator:
    """Diffusion-Limited Aggregation simulator with ASCII rendering."""

    def __init__(self, width=80, height=40, seed_pos="center",
                 num_walkers=3, stickiness=1.0, charset="fancy",
                 diagonal=True, color=True, seed=None, animate=True,
                 max_particles=0, speed=1):

        self.width = width
        self.height = height
        self.num_walkers = num_walkers
        self.stickiness = stickiness
        self.diagonal = diagonal
        self.use_color = color
        self.animate = animate
        self.max_particles = max_particles
        self.speed = speed

        if charset == "fancy":
            self.charset = CHARSET_FANCY
        elif charset == "minimal":
            self.charset = CHARSET_MINIMAL
        else:
            self.charset = CHARSET_BW

        self.directions = DIRECTIONS_8 if diagonal else DIRECTIONS_4

        # Grid: 0 = empty, >0 = age when particle attached (for coloring)
        self.grid = [[0] * width for _ in range(height)]
        self.particle_count = 0
        self.step_count = 0
        self.max_radius = 0
        self.center = (height // 2, width // 2)

        # Seed positions
        if seed_pos == "center":
            self._add_seed(self.center[0], self.center[1])
        elif seed_pos == "line":
            mid = width // 2
            for r in range(height // 4, 3 * height // 4):
                self._add_seed(r, mid)
        elif seed_pos == "corners":
            margin = min(3, height // 10, width // 10)
            for dr, dc in [(0, 0), (0, width - 1), (height - 1, 0), (height - 1, width - 1)]:
                for ddr in range(margin):
                    for ddc in range(margin):
                        self._add_seed(self.center[0] + dr - self.center[0] + ddr,
                                       self.center[1] + dc - self.center[1] + ddc)
        elif seed_pos == "ring":
            cr, cc = self.center
            radius = min(height, width) // 4
            for angle in range(0, 360, 8):
                rad = math.radians(angle)
                r = int(cr + radius * math.sin(rad))
                c = int(cc + radius * math.cos(rad))
                if 0 <= r < height and 0 <= c < width:
                    self._add_seed(r, c)

        # Active walkers
        self.walkers = []
        for _ in range(num_walkers):
            self.walkers.append(self._new_walker())

        if seed is not None:
            random.seed(seed)

    def _add_seed(self, r, c):
        if 0 <= r < self.height and 0 <= c < self.width and self.grid[r][c] == 0:
            self.grid[r][c] = 1
            self.particle_count += 1

    def _new_walker(self):
        """Spawn a walker at a random position on the perimeter of a circle
        around the aggregate, far enough to not immediately stick."""
        r, c = self.center
        spawn_radius = max(self.max_radius + 5, min(self.height, self.width) // 3)
        angle = random.uniform(0, 2 * math.pi)
        wr = int(r + spawn_radius * math.sin(angle))
        wc = int(c + spawn_radius * math.cos(angle))
        # Clamp to grid bounds
        wr = max(0, min(self.height - 1, wr))
        wc = max(0, min(self.width - 1, wc))
        return [wr, wc]

    def _has_neighbor(self, r, c):
        """Check if position has an adjacent aggregate particle."""
        for dr, dc in self.directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                if self.grid[nr][nc] > 0:
                    return True
        return False

    def step(self, count=1):
        """Advance the simulation by `count` steps."""
        for _ in range(count):
            self.step_count += 1
            for i, walker in enumerate(self.walkers):
                if walker is None:
                    continue

                wr, wc = walker

                # Check if walker should stick
                if self._has_neighbor(wr, wc):
                    if random.random() < self.stickiness:
                        self.grid[wr][wc] = self.particle_count + 1
                        self.particle_count += 1
                        # Update max radius
                        dist = math.sqrt((wr - self.center[0])**2 + (wc - self.center[1])**2)
                        if dist > self.max_radius:
                            self.max_radius = dist
                        # Respawn
                        self.walkers[i] = self._new_walker()
                        continue

                # Random walk
                dr, dc = random.choice(self.directions)
                nr, nc = wr + dr, wc + dc

                # Kill walker if it wanders too far, respawn
                dist_from_center = math.sqrt(
                    (nr - self.center[0])**2 + (nc - self.center[1])**2
                )
                max_dist = min(self.height, self.width) * 0.6

                if 0 <= nr < self.height and 0 <= nc < self.width and dist_from_center < max_dist:
                    if self.grid[nr][nc] == 0:
                        self.walkers[i] = [nr, nc]
                else:
                    self.walkers[i] = self._new_walker()

    def render(self):
        """Render the grid to an ASCII string."""
        lines = []

        # Find age range for gradient mapping
        max_age = max(1, self.particle_count)

        # Build the render buffer with character + color info
        buffer = []
        for r in range(self.height):
            row = []
            for c in range(self.width):
                age = self.grid[r][c]
                if age > 0:
                    # Map age to charset index
                    char_idx = min(len(self.charset) - 1,
                                  int((age / max_age) * (len(self.charset) - 1)))
                    ch = self.charset[char_idx]
                    # Color based on age
                    color_idx = int((age / max_age) * (len(COLOR_PALETTE) - 1))
                    color = COLOR_PALETTE[min(color_idx, len(COLOR_PALETTE) - 1)]
                    row.append((ch, color))
                else:
                    # Check if this is an active walker
                    is_walker = False
                    for w in self.walkers:
                        if w is not None and w[0] == r and w[1] == c:
                            is_walker = True
                            break
                    if is_walker:
                        row.append((self.charset[-1], (255, 255, 255)))
                    else:
                        row.append((" ", (0, 0, 0)))
            buffer.append(row)

        # Convert buffer to string with ANSI colors
        for row in buffer:
            line = ""
            prev_fg = None
            for ch, (fr, fg, fb) in row:
                if ch == " ":
                    if prev_fg is not None:
                        line += "\033[0m"
                        prev_fg = None
                    line += ch
                else:
                    if self.use_color:
                        new_fg = (fr, fg, fb)
                        if new_fg != prev_fg:
                            line += f"\033[38;2;{fr};{fg};{fb}m"
                            prev_fg = new_fg
                    line += ch
            if prev_fg is not None:
                line += "\033[0m"
            lines.append(line)

        return lines

    def render_stats(self):
        """Return stats string."""
        return (
            f" Particles: {self.particle_count:5d} │"
            f" Steps: {self.step_count:8d} │"
            f" Radius: {self.max_radius:5.1f} │"
            f" Walkers: {self.num_walkers} "
        )


# ─── Display Utilities ───────────────────────────────────────────────────────

def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def move_cursor(row, col):
    sys.stdout.write(f"\033[{row};{col}H")
    sys.stdout.flush()

def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Crystal Growth Simulator — Diffusion-Limited Aggregation in the terminal"
    )
    parser.add_argument("-W", "--width", type=int, default=80, help="Grid width (default: 80)")
    parser.add_argument("-H", "--height", type=int, default=35, help="Grid height (default: 35)")
    parser.add_argument("-w", "--walkers", type=int, default=5, help="Number of simultaneous walkers (default: 5)")
    parser.add_argument("-s", "--stickiness", type=float, default=1.0,
                       help="Probability of sticking on contact, 0.0-1.0 (default: 1.0)")
    parser.add_argument("-S", "--seed-pos", choices=["center", "line", "corners", "ring"],
                       default="center", help="Seed configuration (default: center)")
    parser.add_argument("-c", "--charset", choices=["fancy", "minimal", "bw"],
                       default="fancy", help="Character set style (default: fancy)")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--no-diagonal", action="store_true", help="Only 4-directional walking")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--no-animate", action="store_true",
                       help="Don't animate, just output final result")
    parser.add_argument("-m", "--max-particles", type=int, default=0,
                       help="Stop after this many particles (0=unlimited)")
    parser.add_argument("--speed", type=int, default=5,
                       help="Simulation steps per frame (default: 5)")
    parser.add_argument("-o", "--output", type=str, default=None,
                       help="Save final result to file instead of displaying")
    args = parser.parse_args()

    # Auto-detect terminal size if not specified
    try:
        term_size = os.get_terminal_size()
        if args.width == 80:
            args.width = min(args.width, term_size.columns - 2)
        if args.height == 35:
            args.height = min(args.height, term_size.lines - 4)
    except OSError:
        pass

    sim = DLASimulator(
        width=args.width,
        height=args.height,
        seed_pos=args.seed_pos,
        num_walkers=args.walkers,
        stickiness=args.stickiness,
        charset=args.charset,
        diagonal=not args.no_diagonal,
        color=not args.no_color,
        seed=args.seed,
        animate=not args.no_animate,
        max_particles=args.max_particles,
        speed=args.speed,
    )

    if args.output:
        # Batch mode — run simulation and save to file
        target = args.max_particles if args.max_particles > 0 else 500
        print(f"Growing crystal to {target} particles...")
        while sim.particle_count < target:
            sim.step(count=args.speed)
            if sim.particle_count % 50 == 0:
                print(f"  {sim.particle_count}/{target} particles grown...", end="\r")
        lines = sim.render()
        with open(args.output, "w") as f:
            # Strip ANSI codes for file output
            import re
            for line in lines:
                clean = re.sub(r'\033\[[0-9;]*m', '', line)
                f.write(clean.rstrip() + "\n")
        print(f"\nSaved to {args.output}")
        return

    if args.no_animate:
        # Non-animated mode — run to target and print
        target = args.max_particles if args.max_particles > 0 else 300
        while sim.particle_count < target:
            sim.step(count=args.speed)
        lines = sim.render()
        import re
        for line in lines:
            clean = re.sub(r'\033\[[0-9;]*m', '', line)
            print(clean.rstrip())
        print(sim.render_stats())
        return

    # ─── Animated mode ───────────────────────────────────────────────────
    clear_screen()
    hide_cursor()

    try:
        frame = 0
        paused = False
        running = True

        while running:
            if not paused:
                # Check if we've hit particle limit
                if args.max_particles > 0 and sim.particle_count >= args.max_particles:
                    paused = True

                sim.step(count=args.speed)

            # Render
            lines = sim.render()
            stats = sim.render_stats()

            move_cursor(1, 1)
            # Title bar
            title = f" ══ Crystal Growth Simulator ══ {stats} "
            if sim.use_color and not args.no_color:
                title = f"\033[48;5;17m\033[38;5;220m{title}\033[0m"

            sys.stdout.write(title + "\n")
            for line in lines:
                sys.stdout.write(line + "\n")

            # Help bar
            help_text = " [Q]uit  [P]ause  [+/−]Speed  [R]eset  [S]ave"
            sys.stdout.write(f"\033[38;5;244m{help_text}\033[0m\n")

            sys.stdout.flush()

            frame += 1

            # Non-blocking key input
            if sys.stdin.isatty():
                import select
                if select.select([sys.stdin], [], [], 0.02)[0]:
                    key = sys.stdin.read(1)
                    if key == "q" or key == "Q":
                        running = False
                    elif key == "p" or key == "P":
                        paused = not paused
                    elif key == "+" or key == "=":
                        args.speed = min(args.speed + 1, 50)
                    elif key == "-" or key == "_":
                        args.speed = max(args.speed - 1, 1)
                    elif key == "r" or key == "R":
                        sim = DLASimulator(
                            width=args.width, height=args.height,
                            seed_pos=args.seed_pos, num_walkers=args.walkers,
                            stickiness=args.stickiness, charset=args.charset,
                            diagonal=not args.no_diagonal,
                            color=not args.no_color, seed=args.seed,
                            animate=True, max_particles=args.max_particles,
                            speed=args.speed,
                        )
                        paused = False
                    elif key == "s" or key == "S":
                        # Quick save
                        import re
                        ts = int(time.time())
                        fname = f"crystal_{ts}.txt"
                        with open(fname, "w") as f:
                            for line in lines:
                                clean = re.sub(r'\033\[[0-9;]*m', '', line)
                                f.write(clean.rstrip() + "\n")
                        # Flash save notification
                        sys.stdout.write(f"\033[s\033[{args.height + 3};1H\033[38;5;2m Saved to {fname}! \033[0m\033[u")
                        sys.stdout.flush()
            else:
                time.sleep(0.02)

    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        move_cursor(args.height + 4, 1)
        print(f"\nCrystal complete! {sim.particle_count} particles grown in {sim.step_count} steps.")
        print("Goodbye! ✦")


if __name__ == "__main__":
    main()