#!/usr/bin/env python3
"""
Terminal Domino Chain Simulator
================================
Place dominoes on a grid, pick a trigger point, and watch the
chain reaction cascade across the screen in an animated ASCII sim.

Each domino has a height and spacing. When the first one is pushed,
it rotates and falls into its neighbor, transferring momentum with
some probability of continuing the chain. Tall tightly-packed dominoes
cascade further; short sparse ones may stop early.

Run:  python3 domino_chain.py
"""

import argparse
import random
import sys
import time
import math

# ── ANSI helpers ──────────────────────────────────────────────────────
CLEAR = "\033[2J"
HOME = "\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
RESET = "\033[0m"

FG = {
    "white": "\033[97m",
    "gray": "\033[90m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "red": "\033[91m",
    "green": "\033[92m",
    "magenta": "\033[95m",
    "dim": "\033[2m",
}

# ── Physics model (heavily simplified) ────────────────────────────────
# Domino states:
#   STANDING   — upright, waiting to be hit
#   FALLING    — rotating, angle increases each tick
#   FALLEN     — fully horizontal (or past 90°)
#   SETTLED    — collapsed and inert
STANDING, FALLING, FALLEN, SETTLED = 0, 1, 2, 3

# Domino rendering height in terminal rows (visual only)
DOMINO_HEIGHT = 6
# Width of a standing domino on the grid
DOMINO_WIDTH = 1


class Domino:
    """A single domino tile."""

    __slots__ = ("col", "height", "spacing", "angle", "state", "fall_dir")

    def __init__(self, col: int, height: int = DOMINO_HEIGHT, spacing: int = 2):
        self.col = col            # horizontal grid position (left edge)
        self.height = height      # pixel-ish height
        self.spacing = spacing    # gap to next domino's base
        self.angle = 0.0          # 0 = upright, 90 = flat
        self.state = STANDING
        self.fall_dir = 1         # +1 = right, -1 = left

    @property
    def top_x(self) -> float:
        """x-coord of the top of the domino, accounting for rotation."""
        rad = math.radians(self.angle)
        return self.col + self.height * math.sin(rad) * self.fall_dir

    @property
    def top_y(self) -> float:
        """y-coord of the top of the domino (0 = ground)."""
        rad = math.radians(self.angle)
        return self.height * math.cos(rad)

    def update(self, dt: float) -> None:
        if self.state == FALLING:
            # angular acceleration grows with sin(angle) — gravity-like
            g = 9.8
            alpha = g * math.sin(math.radians(abs(self.angle))) / self.height * 80.0
            # add a constant kick so it starts moving immediately
            self.angle += (alpha * dt + 30.0 * dt) * self.fall_dir
            # clamp angle magnitude
            if abs(self.angle) >= 90.0:
                self.angle = 90.0 * self.fall_dir
                self.state = FALLEN
        elif self.state == FALLEN:
            # brief pause then settled
            self.state = SETTLED


class ChainSimulator:
    """The full domino chain simulation."""

    def __init__(self, width: int = 70, fps: int = 20):
        self.width = width
        self.fps = fps
        self.dominoes: list[Domino] = []
        self.frame = 0
        self.ground_row = 14   # the floor; below this is the base

    # ── setup ──────────────────────────────────────────────────────────
    def add_domino(self, height: int, spacing: int) -> None:
        if not self.dominoes:
            col = 2
        else:
            prev = self.dominoes[-1]
            col = prev.col + prev.spacing + 1
        self.dominoes.append(Domino(col=col, height=height, spacing=spacing))

    def random_setup(self, count: int) -> None:
        """Randomly generate a chain with varied heights & spacings."""
        self.dominoes.clear()
        for _ in range(count):
            h = random.randint(3, 8)
            s = random.randint(1, 4)
            self.add_domino(h, s)

    def uniform_setup(self, count: int, height: int = 6, spacing: int = 2) -> None:
        self.dominoes.clear()
        for _ in range(count):
            self.add_domino(height, spacing)

    # ── triggering ─────────────────────────────────────────────────────
    def trigger(self, idx: int = 0, direction: int = 1) -> None:
        """Push over the domino at index `idx` in the given direction."""
        if 0 <= idx < len(self.dominoes) and self.dominoes[idx].state == STANDING:
            self.dominoes[idx].state = FALLING
            self.dominoes[idx].fall_dir = direction

    # ── collision detection ─────────────────────────────────────────────
    def check_collisions(self) -> None:
        """A falling domino that leans far enough hits its neighbor."""
        for i, d in enumerate(self.dominoes):
            if d.state != FALLING:
                continue
            # domino reached enough lean to reach its neighbor's base
            if d.fall_dir > 0 and i + 1 < len(self.dominoes):
                nxt = self.dominoes[i + 1]
                if nxt.state == STANDING and abs(d.angle) > 25.0:
                    # transfer momentum — smaller spacing = more reliable
                    gap = (nxt.col - d.col) - 1
                    transfer_prob = max(0.15, 1.0 - gap / (d.height * 1.2))
                    if random.random() < transfer_prob:
                        nxt.state = FALLING
                        nxt.fall_dir = d.fall_dir
            elif d.fall_dir < 0 and i - 1 >= 0:
                prv = self.dominoes[i - 1]
                if prv.state == STANDING and abs(d.angle) > 25.0:
                    gap = (d.col - prv.col) - 1
                    transfer_prob = max(0.15, 1.0 - gap / (d.height * 1.2))
                    if random.random() < transfer_prob:
                        prv.state = FALLING
                        prv.fall_dir = d.fall_dir

    # ── step physics ───────────────────────────────────────────────────
    def step(self, dt: float) -> None:
        for d in self.dominoes:
            d.update(dt)
        self.check_collisions()

    def all_settled(self) -> bool:
        return all(d.state in (SETTLED, STANDING) for d in self.dominoes)

    # ── rendering ──────────────────────────────────────────────────────
    def render(self) -> str:
        """Render the current scene as an ANSI string."""
        rows = 16
        cols = self.width
        grid: list[list[str]] = [[" "] * cols for _ in range(rows)]

        # draw ground
        ground = "▔" * cols
        # place it at row index `ground_row`
        gr = self.ground_row
        if gr < rows:
            for c in range(cols):
                grid[gr][c] = FG["gray"] + "▔" + RESET

        # draw base/support line below ground
        base_row = gr + 1
        if base_row < rows:
            for c in range(cols):
                grid[base_row][c] = FG["dim"] + "▔" + RESET

        # draw dominoes
        for d in self.dominoes:
            self._draw_domino(grid, d, rows, cols)

        # build string
        out = []
        for r in range(rows):
            line = ""
            for c in range(cols):
                line += grid[r][c]
            out.append(line)
        return "\n".join(out)

    def _draw_domino(self, grid, d: Domino, rows: int, cols: int) -> None:
        """Draw a single domino using a simple rotation approximation."""
        gr = self.ground_row
        rad = math.radians(abs(d.angle))

        # color by state
        if d.state == STANDING:
            color = FG["white"]
        elif d.state == FALLING:
            # gradient from cyan to yellow based on angle
            t = abs(d.angle) / 90.0
            color = FG["cyan"] if t < 0.5 else FG["yellow"]
        elif d.state == FALLEN:
            color = FG["red"]
        else:
            color = FG["gray"]

        # standing: vertical bar
        if d.state == STANDING:
            for h in range(d.height):
                y = gr - 1 - h
                x = d.col
                if 0 <= y < rows and 0 <= x < cols:
                    grid[y][x] = color + "█" + RESET
            # base
            if 0 <= gr < rows and 0 <= d.col < cols:
                grid[gr][d.col] = color + "▁" + RESET
            return

        # fallen/settled: horizontal bar
        if d.state in (FALLEN, SETTLED):
            length = d.height
            start = d.col if d.fall_dir > 0 else d.col - length + 1
            end = start + length
            for x in range(max(0, start), min(cols, end)):
                if 0 <= gr - 1 < rows:
                    grid[gr - 1][x] = color + "█" + RESET
                if 0 <= gr < rows:
                    grid[gr][x] = color + "▁" + RESET
            return

        # falling: interpolate between vertical and horizontal
        t = abs(d.angle) / 90.0  # 0 = vertical, 1 = horizontal
        # we'll draw the domino as a line of tiles from the pivot (base)
        # to the top, rotated by angle
        num_pts = max(2, d.height)
        for i in range(num_pts):
            frac = i / max(1, num_pts - 1)
            # distance along domino from base
            dist = frac * d.height
            # rotated offset
            dx = dist * math.sin(rad) * d.fall_dir
            dy = -dist * math.cos(rad)
            x = int(round(d.col + dx))
            y = int(round(gr + dy))
            if 0 <= y < rows and 0 <= x < cols:
                # overwrite only if empty or our own color
                if grid[y][x].strip() in ("", "▔"):
                    grid[y][x] = color + "█" + RESET
        # pivot base
        if 0 <= gr < rows and 0 <= d.col < cols:
            grid[gr][d.col] = color + "▁" + RESET

    # ── HUD overlay ─────────────────────────────────────────────────────
    def render_hud(self, total_fallen: int, total: int) -> str:
        status_line = (
            f"{FG['gray']}Dominoes: {total_fallen}/{total} fallen  "
            f"Frame: {self.frame}{RESET}"
        )
        bar_width = 30
        pct = total_fallen / max(1, total)
        filled = int(bar_width * pct)
        bar = FG["green"] + "█" * filled + FG["dim"] + "░" * (bar_width - filled) + RESET
        return f"{status_line}\n{bar}"

    # ── main animation loop ────────────────────────────────────────────
    def run(self) -> None:
        try:
            sys.stdout.write(HIDE_CURSOR)
            dt = 1.0 / self.fps
            total = len(self.dominoes)

            while True:
                self.step(dt)
                self.frame += 1

                # render frame
                scene = self.render()
                fallen = sum(1 for d in self.dominoes if d.state in (FALLEN, SETTLED))
                hud = self.render_hud(fallen, total)

                sys.stdout.write(HOME)
                sys.stdout.write(CLEAR)
                sys.stdout.write("\n")
                # header
                header = (
                    f"{FG['magenta']}╔══ Domino Chain Simulator ══╗{RESET}\n"
                    f"{FG['magenta']}╚════════════════════════════╝{RESET}\n\n"
                )
                sys.stdout.write(header)
                sys.stdout.write(scene + "\n")
                sys.stdout.write("\n" + hud + "\n")
                sys.stdout.flush()

                if self.all_settled() and self.frame > 10:
                    time.sleep(1.0)
                    # final summary
                    sys.stdout.write(
                        f"\n{FG['green']}Chain complete! "
                        f"{fallen}/{total} dominoes fell.{RESET}\n"
                    )
                    sys.stdout.write(
                        f"{FG['gray']}Press Ctrl+C to exit.{RESET}\n"
                    )
                    sys.stdout.flush()
                    break

                time.sleep(dt)
        except KeyboardInterrupt:
            pass
        finally:
            sys.stdout.write(SHOW_CURSOR)
            sys.stdout.write(CLEAR)
            sys.stdout.write(HOME)
            sys.stdout.flush()


# ── entry point ─────────────────────────────────────────────────────────
def build_demo() -> ChainSimulator:
    sim = ChainSimulator(width=70, fps=24)
    # Build an interesting chain with varied heights & spacings
    config = [
        (6, 2), (7, 2), (5, 1), (8, 3), (6, 1),
        (4, 2), (7, 1), (9, 2), (5, 3), (6, 1),
        (8, 2), (4, 1), (7, 2), (9, 1), (5, 2),
        (6, 3), (8, 1), (7, 2), (10, 2), (5, 1),
    ]
    for h, s in config:
        sim.add_domino(h, s)
    return sim


def main():
    parser = argparse.ArgumentParser(
        description="Terminal Domino Chain Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 domino_chain.py                  # default demo chain\n"
            "  python3 domino_chain.py --random 25      # 25 random dominoes\n"
            "  python3 domino_chain.py --uniform 30      # 30 identical dominoes\n"
            "  python3 domino_chain.py --reverse        # push from the right\n"
            "  python3 domino_chain.py --fps 30          # faster animation\n"
        ),
    )
    parser.add_argument(
        "--random", type=int, metavar="N",
        help="Generate N dominoes with random heights and spacings.",
    )
    parser.add_argument(
        "--uniform", type=int, nargs="?", const=20,
        help="Generate N uniform dominoes (default 20).",
    )
    parser.add_argument(
        "--height", type=int, default=6,
        help="Domino height for --uniform mode (default 6).",
    )
    parser.add_argument(
        "--spacing", type=int, default=2,
        help="Domino spacing for --uniform mode (default 2).",
    )
    parser.add_argument(
        "--reverse", action="store_true",
        help="Push the chain from the right end instead of the left.",
    )
    parser.add_argument(
        "--fps", type=int, default=24,
        help="Frames per second for the animation (default 24).",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducible runs.",
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    sim = ChainSimulator(width=70, fps=args.fps)

    if args.random:
        sim.random_setup(args.random)
    elif args.uniform is not None:
        sim.uniform_setup(args.uniform, height=args.height, spacing=args.spacing)
    else:
        sim = build_demo()
        sim.fps = args.fps

    # determine trigger index/direction
    if args.reverse:
        trigger_idx = len(sim.dominoes) - 1
        direction = -1
    else:
        trigger_idx = 0
        direction = 1

    sim.trigger(idx=trigger_idx, direction=direction)
    sim.run()


if __name__ == "__main__":
    main()