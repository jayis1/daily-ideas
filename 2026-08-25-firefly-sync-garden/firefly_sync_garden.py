#!/usr/bin/env python3
"""Firefly Sync Garden.

A terminal animation that simulates pulse-coupled fireflies drifting through a
night garden and gradually synchronizing their flashes.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

VERSION = "1.1.0"
RESET = "\033[0m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_HOME = "\033[H"
CLEAR_SCREEN = "\033[2J\033[H"
PALETTES: dict[str, list[str]] = {
    "amber": ["\033[38;5;94m", "\033[38;5;136m", "\033[38;5;214m", "\033[38;5;229m"],
    "mint": ["\033[38;5;29m", "\033[38;5;42m", "\033[38;5;84m", "\033[38;5;194m"],
    "violet": ["\033[38;5;54m", "\033[38;5;99m", "\033[38;5;141m", "\033[38;5;225m"],
    "ocean": ["\033[38;5;24m", "\033[38;5;39m", "\033[38;5;81m", "\033[38;5;159m"],
}
BACKGROUND_STARS = ("·", "˙", "•", "✦")
GLOW_CHARS = [" ", "·", "•", "o", "O", "@"]
ASCII_GLOW_CHARS = [" ", ".", ":", "o", "O", "*"]
DEFAULTS: dict[str, Any] = {
    "width": 72,
    "height": 22,
    "count": 36,
    "steps": 180,
    "fps": 18,
    "coupling": 0.18,
    "radius": 7.0,
    "speed": 0.65,
    "jitter": 0.06,
    "phase_step": 0.04,
    "warmup": 100,
    "palette": "amber",
}
PRESETS: dict[str, dict[str, Any]] = {
    "classic": {},
    "calm": {"count": 24, "coupling": 0.26, "radius": 9.0, "speed": 0.45, "jitter": 0.03, "palette": "mint", "fps": 14},
    "swarm": {"count": 60, "coupling": 0.14, "radius": 6.0, "speed": 0.9, "jitter": 0.10, "palette": "ocean", "fps": 22},
    "storm": {"count": 48, "coupling": 0.32, "radius": 10.0, "speed": 0.8, "jitter": 0.08, "palette": "violet", "fps": 20},
}


@dataclass
class Firefly:
    x: float
    y: float
    vx: float
    vy: float
    phase: float
    period: float
    flash_timer: int = 0


@dataclass
class StepStats:
    flashes: int
    order: float
    synced_ratio: float
    mean_phase: float


@dataclass
class GardenState:
    width: int
    height: int
    fireflies: list[Firefly]
    frame: int = 0


@dataclass
class RenderConfig:
    palette: str = "amber"
    use_color: bool = True
    unicode: bool = True
    trails: int = 4
    show_status: bool = True


@dataclass
class SimConfig:
    coupling: float = 0.18
    radius: float = 7.0
    jitter: float = 0.06
    speed: float = 0.65
    flash_length: int = 2
    phase_step: float = 0.04


@dataclass
class AnalysisSummary:
    steps: int
    total_flashes: int
    peak_flashes: int
    average_order: float
    max_order: float
    average_synced_ratio: float
    max_synced_ratio: float
    final_order: float
    final_synced_ratio: float
    final_mean_phase: float
    first_sync_frame: int | None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def wrap_position(value: float, limit: int) -> float:
    if limit <= 0:
        return 0.0
    while value < 0:
        value += limit
    while value >= limit:
        value -= limit
    return value


def create_state(width: int, height: int, count: int, rng: random.Random, speed: float) -> GardenState:
    """Create a randomized garden with drifting fireflies."""
    fireflies: list[Firefly] = []
    for _ in range(count):
        angle = rng.uniform(0.0, math.tau)
        velocity = rng.uniform(speed * 0.2, speed)
        period = rng.uniform(18.0, 42.0)
        fireflies.append(
            Firefly(
                x=rng.uniform(0, max(width - 1, 1)),
                y=rng.uniform(0, max(height - 1, 1)),
                vx=math.cos(angle) * velocity,
                vy=math.sin(angle) * velocity,
                phase=rng.random(),
                period=period,
            )
        )
    return GardenState(width=width, height=height, fireflies=fireflies)


def phase_order(phases: Sequence[float]) -> float:
    if not phases:
        return 0.0
    real = sum(math.cos(math.tau * phase) for phase in phases) / len(phases)
    imag = sum(math.sin(math.tau * phase) for phase in phases) / len(phases)
    return math.hypot(real, imag)


def circular_mean(phases: Sequence[float]) -> float:
    if not phases:
        return 0.0
    real = sum(math.cos(math.tau * phase) for phase in phases)
    imag = sum(math.sin(math.tau * phase) for phase in phases)
    angle = math.atan2(imag, real)
    return (angle / math.tau) % 1.0


def phase_distance(a: float, b: float) -> float:
    return min((a - b) % 1.0, (b - a) % 1.0)


def count_synced(phases: Sequence[float], tolerance: float = 0.08) -> float:
    if not phases:
        return 0.0
    center = circular_mean(phases)
    close = sum(1 for phase in phases if phase_distance(phase, center) <= tolerance)
    return close / len(phases)


def toroidal_distance(a: Firefly, b: Firefly, width: int, height: int) -> float:
    """Measure distance with screen wrapping so edge neighbors still interact."""
    dx = abs(a.x - b.x)
    dy = abs(a.y - b.y)
    if width > 0:
        dx = min(dx, width - dx)
    if height > 0:
        dy = min(dy, height - dy)
    return math.hypot(dx, dy)


def apply_flash_coupling(
    state: GardenState,
    flash_indices: Iterable[int],
    coupling: float,
    radius: float,
) -> None:
    """Nudge nearby oscillators forward when fireflies flash."""
    if coupling <= 0 or radius <= 0:
        return
    flashers = list(flash_indices)
    if not flashers:
        return
    for index, firefly in enumerate(state.fireflies):
        boost = 0.0
        for flasher_index in flashers:
            if flasher_index == index:
                continue
            flasher = state.fireflies[flasher_index]
            gap = toroidal_distance(firefly, flasher, state.width, state.height)
            if gap > radius:
                continue
            influence = 1.0 - (gap / radius)
            boost += coupling * influence * (1.0 - firefly.phase)
        if boost:
            firefly.phase = min(0.999999, firefly.phase + boost)


def advance_firefly(firefly: Firefly, width: int, height: int, rng: random.Random, config: SimConfig) -> bool:
    """Move a firefly one step and report whether it flashed."""
    firefly.vx += rng.uniform(-config.jitter, config.jitter)
    firefly.vy += rng.uniform(-config.jitter, config.jitter)
    speed = math.hypot(firefly.vx, firefly.vy)
    if speed > config.speed and speed > 0:
        scale = config.speed / speed
        firefly.vx *= scale
        firefly.vy *= scale
    elif speed < config.speed * 0.15:
        angle = rng.uniform(0.0, math.tau)
        nudge = config.speed * 0.25
        firefly.vx += math.cos(angle) * nudge
        firefly.vy += math.sin(angle) * nudge
    firefly.x = wrap_position(firefly.x + firefly.vx, width)
    firefly.y = wrap_position(firefly.y + firefly.vy, height)
    firefly.phase += config.phase_step / max(firefly.period / 30.0, 0.1)
    flashed = False
    if firefly.phase >= 1.0:
        firefly.phase %= 1.0
        firefly.flash_timer = config.flash_length
        flashed = True
    elif firefly.flash_timer > 0:
        firefly.flash_timer -= 1
    return flashed


def step_state(state: GardenState, rng: random.Random, config: SimConfig) -> StepStats:
    """Advance the garden by one frame and compute synchronization metrics."""
    flash_indices: list[int] = []
    for index, firefly in enumerate(state.fireflies):
        if advance_firefly(firefly, state.width, state.height, rng, config):
            flash_indices.append(index)

    apply_flash_coupling(state, flash_indices, config.coupling, config.radius)

    flashed_set = set(flash_indices)
    secondary_flashes: list[int] = []
    for index, firefly in enumerate(state.fireflies):
        if index in flashed_set:
            continue
        if firefly.phase >= 0.995:
            firefly.phase = 0.0
            firefly.flash_timer = config.flash_length
            secondary_flashes.append(index)

    all_flashes = flash_indices + secondary_flashes
    phases = [firefly.phase for firefly in state.fireflies]
    state.frame += 1
    return StepStats(
        flashes=len(all_flashes),
        order=phase_order(phases),
        synced_ratio=count_synced(phases),
        mean_phase=circular_mean(phases),
    )


def background_field(width: int, height: int, frame: int, unicode: bool) -> list[list[str]]:
    chars = BACKGROUND_STARS if unicode else (".", ".", ".", "+")
    field = [[" " for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            value = (x * 17 + y * 31 + frame * 7) % 97
            if value == 0:
                field[y][x] = chars[3]
            elif value in (1, 2):
                field[y][x] = chars[2]
            elif value in (3, 4, 5):
                field[y][x] = chars[1]
    return field


def render_frame(state: GardenState, stats: StepStats, config: RenderConfig) -> str:
    width = state.width
    height = state.height
    grid = background_field(width, height, state.frame, config.unicode)
    intensities = [[0 for _ in range(width)] for _ in range(height)]
    glyphs = GLOW_CHARS if config.unicode else ASCII_GLOW_CHARS
    phases = [firefly.phase for firefly in state.fireflies]
    mean_phase = circular_mean(phases)

    for firefly in state.fireflies:
        x = int(round(firefly.x)) % width
        y = int(round(firefly.y)) % height
        pulse = 1.0 - phase_distance(firefly.phase, mean_phase)
        brightness = int(round(1 + pulse * config.trails))
        if firefly.flash_timer > 0:
            brightness = len(glyphs) - 1
        intensities[y][x] = max(intensities[y][x], brightness)
        if firefly.flash_timer > 0:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx = (x + dx) % width
                    ny = (y + dy) % height
                    if dx == 0 and dy == 0:
                        continue
                    splash = max(len(glyphs) - 3, 1)
                    intensities[ny][nx] = max(intensities[ny][nx], splash)

    palette = PALETTES[config.palette]
    lines: list[str] = []
    for y in range(height):
        parts: list[str] = []
        for x in range(width):
            intensity = intensities[y][x]
            if intensity <= 0:
                parts.append(grid[y][x])
                continue
            glyph = glyphs[min(intensity, len(glyphs) - 1)]
            if config.use_color:
                color_index = min(len(palette) - 1, max(0, intensity - 1))
                parts.append(f"{palette[color_index]}{glyph}{RESET}")
            else:
                parts.append(glyph)
        lines.append("".join(parts))

    if config.show_status:
        status = (
            f"frame={state.frame:03d}  flashes={stats.flashes:02d}  "
            f"order={stats.order:0.2f}  synced={stats.synced_ratio * 100:4.1f}%  "
            f"palette={config.palette}"
        )
        lines.append(status[:width])
    return "\n".join(lines)


def simulate_snapshot(state: GardenState, rng: random.Random, sim_config: SimConfig, warmup: int) -> StepStats:
    """Advance the simulation a few frames and return a still snapshot state."""
    stats = StepStats(
        flashes=0,
        order=phase_order([fly.phase for fly in state.fireflies]),
        synced_ratio=count_synced([fly.phase for fly in state.fireflies]),
        mean_phase=circular_mean([fly.phase for fly in state.fireflies]),
    )
    for _ in range(max(warmup, 0)):
        stats = step_state(state, rng, sim_config)
    return stats


def run_analysis(
    state: GardenState,
    rng: random.Random,
    sim_config: SimConfig,
    steps: int,
) -> tuple[list[dict[str, float]], AnalysisSummary]:
    """Run a headless analysis and collect per-frame metrics."""
    history: list[dict[str, float]] = []
    total_flashes = 0
    peak_flashes = 0
    order_sum = 0.0
    synced_sum = 0.0
    max_order = 0.0
    max_synced_ratio = 0.0
    first_sync_frame: int | None = None
    final_stats = StepStats(flashes=0, order=0.0, synced_ratio=0.0, mean_phase=0.0)

    for _ in range(steps):
        final_stats = step_state(state, rng, sim_config)
        row = {
            "frame": float(state.frame),
            "flashes": float(final_stats.flashes),
            "order": final_stats.order,
            "synced_ratio": final_stats.synced_ratio,
            "mean_phase": final_stats.mean_phase,
        }
        history.append(row)
        total_flashes += final_stats.flashes
        peak_flashes = max(peak_flashes, final_stats.flashes)
        order_sum += final_stats.order
        synced_sum += final_stats.synced_ratio
        max_order = max(max_order, final_stats.order)
        max_synced_ratio = max(max_synced_ratio, final_stats.synced_ratio)
        if first_sync_frame is None and final_stats.synced_ratio >= 0.9:
            first_sync_frame = state.frame

    divisor = max(steps, 1)
    summary = AnalysisSummary(
        steps=steps,
        total_flashes=total_flashes,
        peak_flashes=peak_flashes,
        average_order=order_sum / divisor,
        max_order=max_order,
        average_synced_ratio=synced_sum / divisor,
        max_synced_ratio=max_synced_ratio,
        final_order=final_stats.order,
        final_synced_ratio=final_stats.synced_ratio,
        final_mean_phase=final_stats.mean_phase,
        first_sync_frame=first_sync_frame,
    )
    return history, summary


def save_analysis_csv(path: str, history: Sequence[Mapping[str, float]]) -> Path:
    destination = Path(path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["frame", "flashes", "order", "synced_ratio", "mean_phase"])
        writer.writeheader()
        writer.writerows(history)
    return destination


def format_summary(summary: AnalysisSummary) -> str:
    sync_frame = "not reached" if summary.first_sync_frame is None else str(summary.first_sync_frame)
    return "\n".join(
        [
            "Firefly Sync Garden analysis",
            f"steps: {summary.steps}",
            f"total flashes: {summary.total_flashes}",
            f"peak flashes/frame: {summary.peak_flashes}",
            f"average order: {summary.average_order:.3f}",
            f"max order: {summary.max_order:.3f}",
            f"average synced ratio: {summary.average_synced_ratio:.3f}",
            f"max synced ratio: {summary.max_synced_ratio:.3f}",
            f"final order: {summary.final_order:.3f}",
            f"final synced ratio: {summary.final_synced_ratio:.3f}",
            f"final mean phase: {summary.final_mean_phase:.3f}",
            f"first 90% sync frame: {sync_frame}",
        ]
    )


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be non-negative")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Animate drifting fireflies that gradually synchronize their flashes in your terminal.",
    )
    parser.add_argument("--width", type=positive_int, default=DEFAULTS["width"], help="garden width in characters")
    parser.add_argument("--height", type=positive_int, default=DEFAULTS["height"], help="garden height in rows")
    parser.add_argument("--count", type=positive_int, default=None, help="number of fireflies")
    parser.add_argument("--steps", type=positive_int, default=None, help="frames to animate or analyze")
    parser.add_argument("--fps", type=positive_int, default=None, help="frames per second")
    parser.add_argument("--seed", type=int, default=None, help="random seed for reproducible gardens")
    parser.add_argument("--coupling", type=nonnegative_float, default=None, help="flash influence on nearby fireflies")
    parser.add_argument("--radius", type=nonnegative_float, default=None, help="flash influence radius")
    parser.add_argument("--speed", type=positive_float, default=None, help="maximum drift speed")
    parser.add_argument("--jitter", type=nonnegative_float, default=None, help="random steering jitter")
    parser.add_argument("--phase-step", type=positive_float, default=None, help="base oscillator advancement per frame")
    parser.add_argument("--warmup", type=nonnegative_int, default=DEFAULTS["warmup"], help="simulation steps before snapshot output")
    parser.add_argument("--snapshot", action="store_true", help="print one still frame instead of animating")
    parser.add_argument("--analyze", action="store_true", help="run headless analysis and print synchronization metrics")
    parser.add_argument("--csv", help="write analysis metrics to a CSV file (use with --analyze)")
    parser.add_argument("--summary-only", action="store_true", help="omit the snapshot frame in analysis mode")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="classic", help="apply a curated simulation preset")
    parser.add_argument("--palette", choices=sorted(PALETTES), default=None, help="color palette")
    parser.add_argument("--ascii", action="store_true", help="use ASCII-only glow characters")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    parser.add_argument("--no-status", action="store_true", help="hide the status line")
    parser.add_argument("--version", action="version", version=f"Firefly Sync Garden {VERSION}")
    return parser


def resolve_options(args: argparse.Namespace) -> dict[str, Any]:
    resolved = dict(DEFAULTS)
    resolved.update(PRESETS[args.preset])
    for key in ("count", "steps", "fps", "coupling", "radius", "speed", "jitter", "phase_step", "palette"):
        value = getattr(args, key)
        if value is not None:
            resolved[key] = value
    return resolved


def animate(state: GardenState, rng: random.Random, sim_config: SimConfig, render_config: RenderConfig, steps: int, fps: int) -> int:
    delay = 1.0 / max(fps, 1)
    sys.stdout.write(CLEAR_SCREEN + HIDE_CURSOR)
    sys.stdout.flush()
    try:
        for _ in range(steps):
            started = time.perf_counter()
            stats = step_state(state, rng, sim_config)
            sys.stdout.write(CLEAR_HOME)
            sys.stdout.write(render_frame(state, stats, render_config))
            sys.stdout.write("\n")
            sys.stdout.flush()
            elapsed = time.perf_counter() - started
            if elapsed < delay:
                time.sleep(delay - elapsed)
    except KeyboardInterrupt:
        return 130
    finally:
        sys.stdout.write(SHOW_CURSOR + RESET + "\n")
        sys.stdout.flush()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.snapshot and args.analyze:
        parser.error("--snapshot and --analyze are mutually exclusive")
    if args.csv and not args.analyze:
        parser.error("--csv requires --analyze")
    if args.width < 10 or args.height < 5:
        parser.error("width must be at least 10 and height at least 5")

    options = resolve_options(args)
    rng = random.Random(args.seed)
    sim_config = SimConfig(
        coupling=clamp(options["coupling"], 0.0, 1.0),
        radius=max(options["radius"], 0.0),
        jitter=max(options["jitter"], 0.0),
        speed=max(options["speed"], 0.05),
        phase_step=max(options["phase_step"], 0.001),
    )
    render_config = RenderConfig(
        palette=options["palette"],
        use_color=not args.no_color,
        unicode=not args.ascii,
        show_status=not args.no_status,
    )
    state = create_state(args.width, args.height, options["count"], rng, sim_config.speed)

    if args.snapshot:
        stats = simulate_snapshot(state, rng, sim_config, args.warmup)
        print(render_frame(state, stats, render_config))
        return 0

    if args.analyze:
        history, summary = run_analysis(state, rng, sim_config, options["steps"])
        if not args.summary_only:
            last_stats = StepStats(
                flashes=int(history[-1]["flashes"]) if history else 0,
                order=summary.final_order,
                synced_ratio=summary.final_synced_ratio,
                mean_phase=summary.final_mean_phase,
            )
            print(render_frame(state, last_stats, render_config))
            print()
        print(format_summary(summary))
        if args.csv:
            destination = save_analysis_csv(args.csv, history)
            print(f"csv: {destination}")
        return 0

    return animate(state, rng, sim_config, render_config, options["steps"], options["fps"])


if __name__ == "__main__":
    raise SystemExit(main())
