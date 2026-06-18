#!/usr/bin/env python3
"""
Crystal Growth Simulator — Diffusion-Limited Aggregation (DLA) in the Terminal

Simulates particles undergoing random walks that aggregate upon contact,
producing beautiful, branching, fractal-like crystalline structures.
Rendered in real-time ASCII art in the terminal.

Enhanced with symmetry modes, JSON export, snapshot saving, and growth analytics.
"""

import random
import sys
import os
import time
import math
import argparse
import json
import re
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

VERSION = "2.0.0"


# ─── Core DLA Engine ─────────────────────────────────────────────────────────

class DLASimulator:
    """Diffusion-Limited Aggregation simulator with ASCII rendering.

    Simulates random walkers that stick to an aggregate on contact,
    growing fractal-like crystal structures. Supports multiple seed
    configurations, symmetry modes, and real-time animation.

    Attributes:
        width: Grid width in characters.
        height: Grid height in characters.
        particle_count: Number of aggregated particles.
        step_count: Total simulation steps taken.
        max_radius: Maximum distance from center of any aggregate particle.
    """

    def __init__(self, width=80, height=40, seed_pos="center",
                 num_walkers=3, stickiness=1.0, charset="fancy",
                 diagonal=True, color=True, seed=None, animate=True,
                 max_particles=0, speed=1, symmetry="none"):
        """Initialize the DLA simulator.

        Args:
            width: Grid width (minimum 3).
            height: Grid height (minimum 3).
            seed_pos: Seed configuration - 'center', 'line', 'corners', or 'ring'.
            num_walkers: Number of simultaneous random walkers.
            stickiness: Probability of sticking on contact (0.0, 1.0].
            charset: Character set - 'fancy', 'minimal', or 'bw'.
            diagonal: Allow diagonal movement if True.
            color: Use ANSI color output if True.
            seed: Random seed for reproducibility.
            animate: Whether to animate the simulation.
            max_particles: Stop after this many particles (0 = unlimited).
            speed: Simulation steps per frame.
            symmetry: Symmetry mode - 'none', 'horizontal', 'vertical', or 'both'.
        """
        # Validate inputs
        if width < 3 or height < 3:
            raise ValueError(f"Grid must be at least 3x3, got {width}x{height}")
        if num_walkers < 1:
            raise ValueError(f"Need at least 1 walker, got {num_walkers}")
        if not (0.0 < stickiness <= 1.0):
            raise ValueError(f"Stickiness must be in (0.0, 1.0], got {stickiness}")
        if symmetry not in ("none", "horizontal", "vertical", "both"):
            raise ValueError(f"Symmetry must be none/horizontal/vertical/both, got '{symmetry}'")

        self.width = width
        self.height = height
        self.num_walkers = num_walkers
        self.stickiness = stickiness
        self.diagonal = diagonal
        self.use_color = color
        self.animate = animate
        self.max_particles = max_particles
        self.speed = speed
        self.symmetry = symmetry

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

        # Growth analytics tracking
        self.growth_history = []  # List of (step, particle_count) tuples
        self.start_time = time.time()

        # Seed positions
        self._place_seeds(seed_pos)

        # Update max_radius based on initial seed positions
        for r in range(self.height):
            for c in range(self.width):
                if self.grid[r][c] > 0:
                    dist = math.sqrt((r - self.center[0])**2 + (c - self.center[1])**2)
                    if dist > self.max_radius:
                        self.max_radius = dist

        # Active walkers
        self.walkers = []
        for _ in range(num_walkers):
            self.walkers.append(self._new_walker())

        if seed is not None:
            random.seed(seed)

    def _place_seeds(self, seed_pos):
        """Place seed particles according to the selected configuration."""
        if seed_pos == "center":
            self._add_seed(self.center[0], self.center[1])
        elif seed_pos == "line":
            mid = self.width // 2
            for r in range(self.height // 4, 3 * self.height // 4):
                self._add_seed(r, mid)
        elif seed_pos == "corners":
            margin = min(3, self.height // 10, self.width // 10)
            corners = [
                (0, 0),
                (0, self.width - 1),
                (self.height - 1, 0),
                (self.height - 1, self.width - 1),
            ]
            for cr, cc in corners:
                for ddr in range(margin):
                    for ddc in range(margin):
                        self._add_seed(cr + ddr, cc + ddc)
        elif seed_pos == "ring":
            cr, cc = self.center
            radius = min(self.height, self.width) // 4
            for angle in range(0, 360, 8):
                rad = math.radians(angle)
                r = int(cr + radius * math.sin(rad))
                c = int(cc + radius * math.cos(rad))
                if 0 <= r < self.height and 0 <= c < self.width:
                    self._add_seed(r, c)

    def _add_seed(self, r, c):
        """Place a seed particle. Only adds if position is in bounds and empty."""
        if 0 <= r < self.height and 0 <= c < self.width and self.grid[r][c] == 0:
            self.grid[r][c] = 1
            self.particle_count += 1

    def _mirror_positions(self, r, c):
        """Generate symmetry-mirrored positions for a given coordinate.

        Returns all positions that should be set simultaneously based on
        the current symmetry mode.
        """
        positions = [(r, c)]
        if self.symmetry == "horizontal" or self.symmetry == "both":
            # Mirror across vertical center line
            mc = self.width - 1 - c
            if mc != c:
                positions.append((r, mc))
        if self.symmetry == "vertical" or self.symmetry == "both":
            # Mirror across horizontal center line
            mr = self.height - 1 - r
            if mr != r:
                positions.append((mr, c))
        if self.symmetry == "both":
            # Corner mirror
            mr = self.height - 1 - r
            mc = self.width - 1 - c
            if mr != r or mc != c:
                positions.append((mr, mc))
        return positions

    def _new_walker(self):
        """Spawn a walker at a random position on the perimeter of a circle
        around the aggregate, far enough to not immediately stick.
        Ensures the walker doesn't spawn on an occupied cell."""
        r, c = self.center
        spawn_radius = max(self.max_radius + 5, min(self.height, self.width) // 3)

        # Try up to 50 times to find an empty cell for spawning
        for _ in range(50):
            angle = random.uniform(0, 2 * math.pi)
            wr = int(r + spawn_radius * math.sin(angle))
            wc = int(c + spawn_radius * math.cos(angle))
            # Clamp to grid bounds
            wr = max(0, min(self.height - 1, wr))
            wc = max(0, min(self.width - 1, wc))
            # Only use this position if it's empty
            if self.grid[wr][wc] == 0:
                return [wr, wc]

        # Fallback: find any empty cell near the spawn radius
        for attempt_radius in range(int(spawn_radius), max(int(spawn_radius) - 10, 0), -1):
            for angle_deg in range(0, 360, 15):
                rad = math.radians(angle_deg)
                wr = int(r + attempt_radius * math.sin(rad))
                wc = int(c + attempt_radius * math.cos(rad))
                wr = max(0, min(self.height - 1, wr))
                wc = max(0, min(self.width - 1, wc))
                if self.grid[wr][wc] == 0:
                    return [wr, wc]

        # Ultimate fallback: scan the entire grid for an empty cell
        for r2 in range(self.height):
            for c2 in range(self.width):
                if self.grid[r2][c2] == 0:
                    return [r2, c2]

        # Grid is completely full (shouldn't happen normally)
        return None

    def _has_neighbor(self, r, c):
        """Check if position has an adjacent aggregate particle."""
        for dr, dc in self.directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                if self.grid[nr][nc] > 0:
                    return True
        return False

    def step(self, count=1):
        """Advance the simulation by `count` steps.

        Each step moves all active walkers one position. When a walker
        touches the aggregate, it sticks (with probability = stickiness)
        and a new walker is spawned.
        """
        for _ in range(count):
            self.step_count += 1
            for i, walker in enumerate(self.walkers):
                if walker is None:
                    # Respawn dead walkers
                    self.walkers[i] = self._new_walker()
                    if self.walkers[i] is None:
                        # Grid is full, nothing to do
                        continue
                    walker = self.walkers[i]

                wr, wc = walker

                # If walker is on an occupied cell, respawn it
                if self.grid[wr][wc] > 0:
                    self.walkers[i] = self._new_walker()
                    continue

                # Check if walker should stick
                if self._has_neighbor(wr, wc):
                    if random.random() < self.stickiness:
                        # Place the particle (and its symmetry mirrors)
                        self.particle_count += 1
                        mirrored = self._mirror_positions(wr, wc)
                        for mr, mc in mirrored:
                            if (0 <= mr < self.height and 0 <= mc < self.width
                                    and self.grid[mr][mc] == 0):
                                self.grid[mr][mc] = self.particle_count
                                # Update max radius
                                dist = math.sqrt(
                                    (mr - self.center[0])**2 + (mc - self.center[1])**2
                                )
                                if dist > self.max_radius:
                                    self.max_radius = dist

                        # Record growth history for analytics
                        self.growth_history.append(
                            (self.step_count, self.particle_count)
                        )

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
                max_dist = max(self.height, self.width) * 0.7

                if (0 <= nr < self.height and 0 <= nc < self.width
                        and dist_from_center < max_dist):
                    if self.grid[nr][nc] == 0:
                        self.walkers[i] = [nr, nc]
                    else:
                        # Target cell is occupied; try a different random direction
                        moved = False
                        directions_copy = list(self.directions)
                        random.shuffle(directions_copy)
                        for dr2, dc2 in directions_copy:
                            nr2, nc2 = wr + dr2, wc + dc2
                            dist2 = math.sqrt(
                                (nr2 - self.center[0])**2 + (nc2 - self.center[1])**2
                            )
                            if (0 <= nr2 < self.height and 0 <= nc2 < self.width
                                    and dist2 < max_dist
                                    and self.grid[nr2][nc2] == 0):
                                self.walkers[i] = [nr2, nc2]
                                moved = True
                                break
                        if not moved:
                            # Surrounded — respawn
                            self.walkers[i] = self._new_walker()
                else:
                    self.walkers[i] = self._new_walker()

    def render(self):
        """Render the grid to an ASCII string with ANSI color codes.

        Returns a list of strings, one per row, with 24-bit color escapes
        for particle coloring based on age.
        """
        lines = []

        # Build walker position set for O(1) lookup
        walker_positions = set()
        for w in self.walkers:
            if w is not None:
                walker_positions.add((w[0], w[1]))

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
                elif (r, c) in walker_positions:
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

    def render_plain(self):
        """Render the grid as plain text without ANSI escapes.

        Useful for file output and non-terminal contexts.
        """
        lines = self.render()
        return [re.sub(r'\033\[[0-9;]*m', '', line).rstrip() for line in lines]

    def render_stats(self):
        """Return stats string with particle count, steps, radius, and density."""
        elapsed = time.time() - self.start_time
        # Calculate grid density (% of cells occupied)
        total_cells = self.width * self.height
        density = (self.particle_count / total_cells * 100) if total_cells > 0 else 0

        # Calculate growth rate (particles per 1000 steps)
        growth_rate = 0.0
        if len(self.growth_history) >= 2:
            recent = self.growth_history[-min(100, len(self.growth_history)):]
            if len(recent) >= 2:
                step_diff = recent[-1][0] - recent[0][0]
                particle_diff = recent[-1][1] - recent[0][1]
                if step_diff > 0:
                    growth_rate = (particle_diff / step_diff) * 1000

        return (
            f" Particles: {self.particle_count:5d} │"
            f" Steps: {self.step_count:8d} │"
            f" Radius: {self.max_radius:5.1f} │"
            f" Density: {density:4.1f}% │"
            f" Rate: {growth_rate:.1f}/1k "
        )

    def get_stats_dict(self):
        """Return statistics as a dictionary for JSON export.

        Returns:
            Dictionary containing simulation statistics and metadata.
        """
        elapsed = time.time() - self.start_time
        total_cells = self.width * self.height
        density = (self.particle_count / total_cells * 100) if total_cells > 0 else 0

        return {
            "version": VERSION,
            "width": self.width,
            "height": self.height,
            "particle_count": self.particle_count,
            "step_count": self.step_count,
            "max_radius": round(self.max_radius, 2),
            "density_percent": round(density, 2),
            "stickiness": self.stickiness,
            "num_walkers": self.num_walkers,
            "diagonal": self.diagonal,
            "symmetry": self.symmetry,
            "elapsed_seconds": round(elapsed, 2),
            "grid": self.grid,
        }

    def to_json(self):
        """Serialize the simulation state to a JSON string.

        The JSON contains the full grid state, parameters, and statistics,
        enabling later reconstruction or analysis.
        """
        return json.dumps(self.get_stats_dict(), indent=2)


# ─── Display Utilities ───────────────────────────────────────────────────────

def clear_screen():
    """Clear the terminal screen and move cursor to top-left."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def move_cursor(row, col):
    """Move the terminal cursor to the specified row and column."""
    sys.stdout.write(f"\033[{row};{col}H")
    sys.stdout.flush()

def hide_cursor():
    """Hide the terminal cursor for cleaner animation."""
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def show_cursor():
    """Show the terminal cursor (restore after hiding)."""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


# ─── Validation ─────────────────────────────────────────────────────────────

def validate_output_path(path):
    """Validate that an output path is safe to write to.

    Blocks writing to system directories and requires the parent
    directory to exist. Returns the resolved absolute path.
    """
    abs_path = os.path.abspath(os.path.expanduser(path))
    blocked_prefixes = [
        "/etc", "/usr", "/bin", "/sbin", "/lib",
        "/boot", "/dev", "/proc", "/sys", "/var",
    ]
    for prefix in blocked_prefixes:
        if abs_path.startswith(prefix + "/") or abs_path == prefix:
            raise ValueError(f"Cannot write to system directory: {abs_path}")
    parent = os.path.dirname(abs_path)
    if parent and not os.path.exists(parent):
        raise ValueError(f"Parent directory does not exist: {parent}")
    return abs_path


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Crystal Growth Simulator — Diffusion-Limited Aggregation in the terminal"
    )
    parser.add_argument("-W", "--width", type=int, default=80,
                        help="Grid width (default: 80, auto-detected)")
    parser.add_argument("-H", "--height", type=int, default=35,
                        help="Grid height (default: 35, auto-detected)")
    parser.add_argument("-w", "--walkers", type=int, default=5,
                        help="Number of simultaneous walkers (default: 5)")
    parser.add_argument("-s", "--stickiness", type=float, default=1.0,
                        help="Probability of sticking on contact, 0.0-1.0 (default: 1.0)")
    parser.add_argument("-S", "--seed-pos", choices=["center", "line", "corners", "ring"],
                        default="center", help="Seed configuration (default: center)")
    parser.add_argument("-c", "--charset", choices=["fancy", "minimal", "bw"],
                        default="fancy", help="Character set style (default: fancy)")
    parser.add_argument("--symmetry", choices=["none", "horizontal", "vertical", "both"],
                        default="none",
                        help="Mirror symmetry mode (default: none)")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--no-diagonal", action="store_true",
                        help="Only 4-directional walking (no diagonals)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--no-animate", action="store_true",
                        help="Don't animate, just output final result")
    parser.add_argument("-m", "--max-particles", type=int, default=0,
                        help="Stop after this many particles (0=unlimited)")
    parser.add_argument("--speed", type=int, default=5,
                        help="Simulation steps per frame (default: 5)")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Save final result to file and exit")
    parser.add_argument("--export-json", type=str, default=None,
                        help="Export simulation state as JSON file")
    parser.add_argument("--snapshot", type=int, default=0,
                        help="Auto-save a snapshot every N particles (0=disabled)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args()

    # Validate inputs
    if args.width < 3:
        parser.error(f"Width must be at least 3, got {args.width}")
    if args.height < 3:
        parser.error(f"Height must be at least 3, got {args.height}")
    if args.walkers < 1:
        parser.error(f"Need at least 1 walker, got {args.walkers}")
    if not (0.0 < args.stickiness <= 1.0):
        parser.error(f"Stickiness must be in (0.0, 1.0], got {args.stickiness}")
    if args.max_particles < 0:
        parser.error(f"Max particles must be non-negative, got {args.max_particles}")
    if args.speed < 1:
        parser.error(f"Speed must be at least 1, got {args.speed}")
    if args.snapshot < 0:
        parser.error(f"Snapshot interval must be non-negative, got {args.snapshot}")

    # Validate output paths
    if args.output:
        try:
            args.output = validate_output_path(args.output)
        except ValueError as e:
            parser.error(str(e))

    if args.export_json:
        try:
            args.export_json = validate_output_path(args.export_json)
        except ValueError as e:
            parser.error(str(e))

    # Auto-detect terminal size if not explicitly specified
    try:
        term_size = os.get_terminal_size()
        if args.width == 80:
            args.width = min(args.width, term_size.columns - 2)
        if args.height == 35:
            args.height = min(args.height, term_size.lines - 4)
    except OSError:
        pass

    # Ensure minimum dimensions after auto-detect
    args.width = max(args.width, 3)
    args.height = max(args.height, 3)

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
        symmetry=args.symmetry,
    )

    # Track last snapshot particle count for auto-snapshots
    last_snapshot_count = 0

    def check_snapshot(sim_state):
        """Check if we should auto-save a snapshot based on particle count."""
        nonlocal last_snapshot_count
        if args.snapshot > 0 and sim_state.particle_count >= last_snapshot_count + args.snapshot:
            ts = int(time.time())
            fname = f"crystal_snapshot_{sim_state.particle_count}p_{ts}.txt"
            try:
                lines = sim_state.render_plain()
                with open(fname, "w") as f:
                    for line in lines:
                        f.write(line + "\n")
                last_snapshot_count = sim_state.particle_count
            except OSError:
                pass  # Silently skip if snapshot fails (e.g., disk full)

    # ─── Batch mode: save to file ────────────────────────────────────────
    if args.output:
        target = args.max_particles if args.max_particles > 0 else 500
        print(f"Growing crystal to {target} particles...")
        while sim.particle_count < target:
            sim.step(count=args.speed)
            check_snapshot(sim)
            if sim.particle_count % 50 == 0:
                print(f"  {sim.particle_count}/{target} particles grown...", end="\r")
        lines = sim.render_plain()
        with open(args.output, "w") as f:
            for line in lines:
                f.write(line + "\n")
        print(f"\nSaved to {args.output}")

        # Also export JSON if requested
        if args.export_json:
            with open(args.export_json, "w") as f:
                f.write(sim.to_json())
            print(f"State exported to {args.export_json}")
        return

    # ─── Non-animated mode: print to terminal ────────────────────────────
    if args.no_animate:
        target = args.max_particles if args.max_particles > 0 else 300
        while sim.particle_count < target:
            sim.step(count=args.speed)
            check_snapshot(sim)
        lines = sim.render_plain()
        for line in lines:
            print(line)
        print(sim.render_stats())
        if args.export_json:
            with open(args.export_json, "w") as f:
                f.write(sim.to_json())
            print(f"State exported to {args.export_json}")
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
                check_snapshot(sim)

            # Render
            lines = sim.render()
            stats = sim.render_stats()

            move_cursor(1, 1)
            # Title bar
            title = f" ══ Crystal Growth Simulator v{VERSION} ══ {stats} "
            if sim.use_color and not args.no_color:
                title = f"\033[48;5;17m\033[38;5;220m{title}\033[0m"

            sys.stdout.write(title + "\n")
            for line in lines:
                sys.stdout.write(line + "\n")

            # Help bar
            help_text = " [Q]uit  [P]ause  [+/−]Speed  [R]eset  [S]ave  [J]SON"
            sys.stdout.write(f"\033[38;5;244m{help_text}\033[0m\n")

            # Status bar (paused/running indicator)
            status = " PAUSED " if paused else " RUNNING "
            if sim.use_color and not args.no_color:
                color = "\033[48;5;136m\033[38;5;16m" if paused else "\033[48;5;28m\033[38;5;16m"
                sys.stdout.write(f"{color}{status}\033[0m\n")
            else:
                sys.stdout.write(f"{status}\n")

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
                            speed=args.speed, symmetry=args.symmetry,
                        )
                        paused = False
                        last_snapshot_count = 0
                    elif key == "s" or key == "S":
                        # Quick save
                        ts = int(time.time())
                        fname = f"crystal_{ts}.txt"
                        with open(fname, "w") as f:
                            for line in sim.render_plain():
                                f.write(line + "\n")
                        sys.stdout.write(
                            f"\033[s\033[{args.height + 5};1H"
                            f"\033[38;5;2m Saved to {fname}! \033[0m\033[u"
                        )
                        sys.stdout.flush()
                    elif key == "j" or key == "J":
                        # Save JSON state
                        ts = int(time.time())
                        fname = f"crystal_{ts}.json"
                        with open(fname, "w") as f:
                            f.write(sim.to_json())
                        sys.stdout.write(
                            f"\033[s\033[{args.height + 5};1H"
                            f"\033[38;5;2m Exported to {fname}! \033[0m\033[u"
                        )
                        sys.stdout.flush()
            else:
                time.sleep(0.02)

    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        move_cursor(args.height + 5, 1)
        elapsed = time.time() - sim.start_time
        print(f"\nCrystal complete! {sim.particle_count} particles in "
              f"{sim.step_count} steps ({elapsed:.1f}s)")
        print(f"Final density: {sim.particle_count / (args.width * args.height) * 100:.1f}%")
        print("Goodbye! ✦")


if __name__ == "__main__":
    main()