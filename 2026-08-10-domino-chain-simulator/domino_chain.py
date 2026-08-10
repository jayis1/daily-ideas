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

Features
--------
- Simplified rotational physics (gravity-driven angular acceleration)
- Probabilistic momentum transfer (gap-to-height ratio)
- Bidirectional triggering (--reverse) or trigger any domino (--trigger N)
- Reproducible runs via --seed
- Adjustable frame rate (--fps)
- Color-blind-friendly no-color mode (--no-color)
- Optional terminal bell on each fall (--sound)
- Headless stats mode for scripts/CI (--no-anim)
- Post-run statistics report (--stats)
- Zero external dependencies — Python 3.10+ only

Run:  python3 domino_chain.py
"""

from __future__ import annotations

import argparse
import math
import random
import sys
import time

__version__ = "1.1.0"

# ── ANSI helpers ──────────────────────────────────────────────────────
CLEAR = "\033[2J"
HOME = "\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
RESET = "\033[0m"
BELL = "\a"

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

# When --no-color is requested, every color code maps to "" so the rest of
# the rendering logic stays unchanged.
_FG_NO_COLOR = {k: "" for k in FG}

# ── Physics model (heavily simplified) ────────────────────────────────
# Domino states:
#   STANDING   — upright, waiting to be hit
#   FALLING    — rotating, angle increases each tick
#   FALLEN     — fully horizontal (or past 90°)
#   SETTLED    — collapsed and inert
STANDING, FALLING, FALLEN, SETTLED = 0, 1, 2, 3

# Human-readable state names for the stats report.
STATE_NAMES = {
    STANDING: "standing",
    FALLING: "falling",
    FALLEN: "fallen",
    SETTLED: "settled",
}

# Domino rendering height in terminal rows (visual only)
DOMINO_HEIGHT = 6
# Width of a standing domino on the grid
DOMINO_WIDTH = 1

# Angle (degrees) at which a falling domino can reach its neighbour.
CONTACT_ANGLE = 25.0
# Frames a domino stays in the FALLEN (red) state before settling.
FALLEN_LINGER = 3


class Domino:
    """A single domino tile.

    Parameters
    ----------
    col : int
        Horizontal grid position (left edge of the base).
    height : int
        Visual height of the domino in terminal rows.
    spacing : int
        Gap (in columns) between this domino's right edge and the next
        domino's left edge.
    """

    __slots__ = ("col", "height", "spacing", "angle", "state", "fall_dir", "_fallen_frames")

    def __init__(self, col: int, height: int = DOMINO_HEIGHT, spacing: int = 2):
        if height < 1:
            raise ValueError(f"domino height must be >= 1, got {height}")
        if spacing < 0:
            raise ValueError(f"domino spacing must be >= 0, got {spacing}")
        self.col = col            # horizontal grid position (left edge)
        self.height = height      # pixel-ish height
        self.spacing = spacing    # gap to next domino's base
        self.angle = 0.0          # 0 = upright, 90 = flat
        self.state = STANDING
        self.fall_dir = 1         # +1 = right, -1 = left
        self._fallen_frames = 0  # frames spent in FALLEN state (for linger)

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
        """Advance one physics step by ``dt`` seconds."""
        if self.state == FALLING:
            # Angular acceleration grows with sin(angle) — gravity-like.
            # The *80 scaling factor makes the sim look good at ~24 fps;
            # it is purely visual, not a real physical constant.
            g = 9.8
            alpha = g * math.sin(math.radians(abs(self.angle))) / self.height * 80.0
            # Constant kick so the domino starts moving immediately rather
            # than sitting at unstable equilibrium.
            self.angle += (alpha * dt + 30.0 * dt) * self.fall_dir
            # Clamp angle magnitude — once at 90° the domino is flat.
            if abs(self.angle) >= 90.0:
                self.angle = 90.0 * self.fall_dir
                self.state = FALLEN
                self._fallen_frames = 0
        elif self.state == FALLEN:
            # Linger briefly in the red FALLEN state for visual feedback,
            # then transition to inert SETTLED.
            self._fallen_frames += 1
            if self._fallen_frames >= FALLEN_LINGER:
                self.state = SETTLED


class ChainSimulator:
    """The full domino chain simulation.

    Parameters
    ----------
    width : int
        Width of the render grid in terminal columns.
    fps : int
        Animation frames per second (also used as physics tick rate).
    use_color : bool
        If False, render without ANSI colour codes (accessible / pipeable).
    sound : bool
        If True, emit a terminal bell each time a domino topples.
    """

    def __init__(self, width: int = 70, fps: int = 24,
                 use_color: bool = True, sound: bool = False):
        self.width = max(10, width)
        self.fps = max(1, fps)
        self.use_color = use_color
        self.sound = sound
        self.dominoes: list[Domino] = []
        self.frame = 0
        self.ground_row = 14   # the floor; below this is the base
        self._falls_this_step = 0  # bell bookkeeping

    # Colour helper: respects --no-color.
    @property
    def fg(self) -> dict[str, str]:
        return FG if self.use_color else _FG_NO_COLOR

    @property
    def reset(self) -> str:
        """RESET code, or empty when --no-color is active."""
        return RESET if self.use_color else ""

    # ── setup ──────────────────────────────────────────────────────────
    def add_domino(self, height: int, spacing: int) -> None:
        """Append a domino with the given height and spacing to the chain."""
        if not self.dominoes:
            col = 2
        else:
            prev = self.dominoes[-1]
            col = prev.col + prev.spacing + 1
        self.dominoes.append(Domino(col=col, height=height, spacing=spacing))

    def random_setup(self, count: int) -> None:
        """Randomly generate a chain with varied heights & spacings."""
        if count < 0:
            raise ValueError(f"domino count must be >= 0, got {count}")
        self.dominoes.clear()
        for _ in range(count):
            h = random.randint(3, 8)
            s = random.randint(1, 4)
            self.add_domino(h, s)

    def uniform_setup(self, count: int, height: int = 6, spacing: int = 2) -> None:
        """Generate ``count`` identical dominoes."""
        if count < 0:
            raise ValueError(f"domino count must be >= 0, got {count}")
        self.dominoes.clear()
        for _ in range(count):
            self.add_domino(height, spacing)

    # ── triggering ─────────────────────────────────────────────────────
    def trigger(self, idx: int = 0, direction: int = 1) -> bool:
        """Push over the domino at index ``idx``.

        Returns True if a domino was actually triggered, False otherwise
        (e.g. index out of range or domino already falling).
        """
        if 0 <= idx < len(self.dominoes) and self.dominoes[idx].state == STANDING:
            self.dominoes[idx].state = FALLING
            self.dominoes[idx].fall_dir = direction
            return True
        return False

    # ── collision detection ─────────────────────────────────────────────
    def check_collisions(self) -> None:
        """A falling domino that leans far enough hits its neighbor."""
        for i, d in enumerate(self.dominoes):
            if d.state != FALLING:
                continue
            # domino reached enough lean to reach its neighbor's base
            if d.fall_dir > 0 and i + 1 < len(self.dominoes):
                nxt = self.dominoes[i + 1]
                if nxt.state == STANDING and abs(d.angle) > CONTACT_ANGLE:
                    # transfer momentum — smaller spacing = more reliable
                    gap = (nxt.col - d.col) - 1
                    transfer_prob = max(0.15, 1.0 - gap / (d.height * 1.2))
                    if random.random() < transfer_prob:
                        nxt.state = FALLING
                        nxt.fall_dir = d.fall_dir
                        self._falls_this_step += 1
            elif d.fall_dir < 0 and i - 1 >= 0:
                prv = self.dominoes[i - 1]
                if prv.state == STANDING and abs(d.angle) > CONTACT_ANGLE:
                    gap = (d.col - prv.col) - 1
                    transfer_prob = max(0.15, 1.0 - gap / (d.height * 1.2))
                    if random.random() < transfer_prob:
                        prv.state = FALLING
                        prv.fall_dir = d.fall_dir
                        self._falls_this_step += 1

    # ── step physics ───────────────────────────────────────────────────
    def step(self, dt: float) -> None:
        self._falls_this_step = 0
        for d in self.dominoes:
            d.update(dt)
        self.check_collisions()
        if self.sound and self._falls_this_step > 0:
            sys.stdout.write(BELL)
            sys.stdout.flush()

    def all_settled(self) -> bool:
        """True when the cascade has fully stopped (no falling dominoes)."""
        return all(d.state in (SETTLED, STANDING) for d in self.dominoes)

    # ── statistics ──────────────────────────────────────────────────────
    def stats(self) -> dict[str, int]:
        """Return a dict of per-state counts plus the total."""
        counts = {name: 0 for name in STATE_NAMES.values()}
        for d in self.dominoes:
            counts[STATE_NAMES[d.state]] += 1
        counts["total"] = len(self.dominoes)
        return counts

    def stats_report(self) -> str:
        """Human-readable post-run statistics summary."""
        s = self.stats()
        fallen = s["fallen"] + s["settled"]
        total = s["total"]
        pct = (fallen / total * 100) if total else 0.0
        stalled = total - fallen - s["falling"]
        lines = [
            f"Total dominoes : {total}",
            f"Fell           : {fallen} ({pct:.1f}%)",
            f"Still standing : {s['standing']} (chain stalled at {stalled})",
            f"Frames         : {self.frame}",
        ]
        return "\n".join(lines)

    # ── rendering ──────────────────────────────────────────────────────
    def render(self) -> str:
        """Render the current scene as an ANSI string."""
        rows = 16
        cols = self.width
        grid: list[list[str]] = [[" "] * cols for _ in range(rows)]

        fg = self.fg
        rst = self.reset
        # draw ground
        gr = self.ground_row
        if gr < rows:
            for c in range(cols):
                grid[gr][c] = fg["gray"] + "▔" + rst

        # draw base/support line below ground
        base_row = gr + 1
        if base_row < rows:
            for c in range(cols):
                grid[base_row][c] = fg["dim"] + "▔" + rst

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
        fg = self.fg
        rst = self.reset

        # color by state
        if d.state == STANDING:
            color = fg["white"]
        elif d.state == FALLING:
            # gradient from cyan to yellow based on angle
            t = abs(d.angle) / 90.0
            color = fg["cyan"] if t < 0.5 else fg["yellow"]
        elif d.state == FALLEN:
            color = fg["red"]
        else:
            color = fg["gray"]

        # standing: vertical bar
        if d.state == STANDING:
            for h in range(d.height):
                y = gr - 1 - h
                x = d.col
                if 0 <= y < rows and 0 <= x < cols:
                    grid[y][x] = color + "█" + rst
            # base
            if 0 <= gr < rows and 0 <= d.col < cols:
                grid[gr][d.col] = color + "▁" + rst
            return

        # fallen/settled: horizontal bar
        if d.state in (FALLEN, SETTLED):
            length = d.height
            start = d.col if d.fall_dir > 0 else d.col - length + 1
            end = start + length
            for x in range(max(0, start), min(cols, end)):
                if 0 <= gr - 1 < rows:
                    grid[gr - 1][x] = color + "█" + rst
                if 0 <= gr < rows:
                    grid[gr][x] = color + "▁" + rst
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
                    grid[y][x] = color + "█" + rst
        # pivot base
        if 0 <= gr < rows and 0 <= d.col < cols:
            grid[gr][d.col] = color + "▁" + rst

    # ── HUD overlay ─────────────────────────────────────────────────────
    def render_hud(self, total_fallen: int, total: int) -> str:
        fg = self.fg
        rst = self.reset
        status_line = (
            f"{fg['gray']}Dominoes: {total_fallen}/{total} fallen  "
            f"Frame: {self.frame}{rst}"
        )
        bar_width = 30
        pct = total_fallen / max(1, total)
        filled = int(bar_width * pct)
        bar = fg["green"] + "█" * filled + fg["dim"] + "░" * (bar_width - filled) + rst
        return f"{status_line}\n{bar}"

    # ── main animation loop ────────────────────────────────────────────
    def run(self, animate: bool = True) -> None:
        """Run the simulation.

        If ``animate`` is False, skip all rendering and just step the
        physics until the chain settles — useful for scripts/CI.
        """
        if not animate:
            self._run_headless()
            return

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
                    f"{self.fg['magenta']}╔══ Domino Chain Simulator v{__version__} ══╗{RESET}\n"
                    f"{self.fg['magenta']}╚═════════════════════════════════════╝{RESET}\n\n"
                )
                sys.stdout.write(header)
                sys.stdout.write(scene + "\n")
                sys.stdout.write("\n" + hud + "\n")
                sys.stdout.flush()

                if self.all_settled() and self.frame > 10:
                    time.sleep(1.0)
                    # final summary
                    sys.stdout.write(
                        f"\n{self.fg['green']}Chain complete! "
                        f"{fallen}/{total} dominoes fell.{RESET}\n"
                    )
                    sys.stdout.write(
                        f"{self.fg['gray']}Press Ctrl+C to exit.{RESET}\n"
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

    def _run_headless(self) -> None:
        """Step physics without any rendering, until the chain settles."""
        dt = 1.0 / self.fps
        max_frames = 10_000  # safety guard against infinite loops
        while not self.all_settled() and self.frame < max_frames:
            self.step(dt)
            self.frame += 1


# ── entry point ─────────────────────────────────────────────────────────
def build_demo() -> ChainSimulator:
    """Construct the default hand-crafted demo chain."""
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


def _validate_args(args: argparse.Namespace) -> None:
    """Sanity-check parsed CLI arguments, raising SystemExit on error."""
    if args.fps < 1:
        raise SystemExit(f"error: --fps must be >= 1, got {args.fps}")
    if args.height < 1:
        raise SystemExit(f"error: --height must be >= 1, got {args.height}")
    if args.spacing < 0:
        raise SystemExit(f"error: --spacing must be >= 0, got {args.spacing}")
    if args.random is not None and args.random < 0:
        raise SystemExit(f"error: --random count must be >= 0, got {args.random}")
    if args.uniform is not None and args.uniform < 0:
        raise SystemExit(f"error: --uniform count must be >= 0, got {args.uniform}")
    if args.trigger is not None and args.trigger < 0:
        raise SystemExit(f"error: --trigger index must be >= 0, got {args.trigger}")
    # Mutually exclusive setup modes
    setup_modes = sum(1 for x in (args.random, args.uniform is not None) if x)
    if setup_modes > 1:
        raise SystemExit("error: --random and --uniform are mutually exclusive")


def main():
    parser = argparse.ArgumentParser(
        prog="domino_chain.py",
        description=f"Terminal Domino Chain Simulator v{__version__}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 domino_chain.py                  # default demo chain\n"
            "  python3 domino_chain.py --random 25      # 25 random dominoes\n"
            "  python3 domino_chain.py --uniform 30     # 30 identical dominoes\n"
            "  python3 domino_chain.py --reverse        # push from the right\n"
            "  python3 domino_chain.py --trigger 5      # push domino #5\n"
            "  python3 domino_chain.py --fps 30         # faster animation\n"
            "  python3 domino_chain.py --no-anim --stats # headless stats\n"
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
        "--trigger", type=int, metavar="IDX", default=None,
        help="Trigger domino at index IDX (0-based) instead of an end. "
             "Use --trigger 0 to explicitly push the leftmost.",
    )
    parser.add_argument(
        "--fps", type=int, default=24,
        help="Frames per second for the animation (default 24).",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducible runs.",
    )
    parser.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI colour codes (accessible / pipeable output).",
    )
    parser.add_argument(
        "--sound", action="store_true",
        help="Emit a terminal bell (\\a) each time a domino topples.",
    )
    parser.add_argument(
        "--no-anim", action="store_true",
        help="Skip animation; just step physics and exit (for scripts/CI).",
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print a statistics report after the simulation finishes.",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"%(prog)s v{__version__}",
    )
    args = parser.parse_args()

    _validate_args(args)

    if args.seed is not None:
        random.seed(args.seed)

    sim = ChainSimulator(
        width=70,
        fps=args.fps,
        use_color=not args.no_color,
        sound=args.sound,
    )

    if args.random is not None:
        sim.random_setup(args.random)
    elif args.uniform is not None:
        sim.uniform_setup(args.uniform, height=args.height, spacing=args.spacing)
    else:
        demo = build_demo()
        sim.dominoes = demo.dominoes
        sim.fps = args.fps

    # Determine trigger index/direction.
    # --trigger overrides --reverse; both default to the leftmost domino.
    if args.trigger is not None:
        trigger_idx = args.trigger
        direction = 1
    elif args.reverse:
        trigger_idx = len(sim.dominoes) - 1
        direction = -1
    else:
        trigger_idx = 0
        direction = 1

    if not sim.trigger(idx=trigger_idx, direction=direction):
        # Be helpful if the user asked for an out-of-range trigger.
        n = len(sim.dominoes)
        print(f"warning: trigger index {trigger_idx} is out of range "
              f"(chain has {n} dominoes, valid 0..{n-1}); nothing was pushed.",
              file=sys.stderr)

    sim.run(animate=not args.no_anim)

    if args.stats:
        print("\nDomino Chain Statistics")
        print("=" * 40)
        print(sim.stats_report())
        print("=" * 40)


if __name__ == "__main__":
    main()