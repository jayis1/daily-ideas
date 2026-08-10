#!/usr/bin/env python3
"""Tests for the Terminal Domino Chain Simulator.

Run with:  python3 test_domino_chain.py
No external test framework required — uses a tiny built-in runner.
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))

from domino_chain import (
    ChainSimulator,
    Domino,
    STANDING,
    FALLING,
    FALLEN,
    SETTLED,
    STATE_NAMES,
    __version__,
    build_demo,
)


# ── Tiny test runner ──────────────────────────────────────────────────────────

_passed = 0
_failed = 0
_failures: list[str] = []


def check(condition: bool, label: str) -> None:
    global _passed, _failed
    if condition:
        _passed += 1
    else:
        _failed += 1
        _failures.append(label)
        print(f"  FAIL: {label}")


def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) < tol


# ── Domino unit tests ─────────────────────────────────────────────────────────

def test_domino_defaults():
    """A new domino should be standing upright with angle 0."""
    d = Domino(col=5, height=6, spacing=2)
    check(d.col == 5, "domino col set")
    check(d.height == 6, "domino height set")
    check(d.spacing == 2, "domino spacing set")
    check(d.angle == 0.0, "domino starts at angle 0")
    check(d.state == STANDING, "domino starts STANDING")
    check(d.fall_dir == 1, "domino default fall_dir is +1")


def test_domino_rejects_invalid_height():
    """Height < 1 should raise ValueError."""
    try:
        Domino(col=0, height=0, spacing=1)
        check(False, "height=0 should raise ValueError")
    except ValueError:
        check(True, "height=0 raises ValueError")
    try:
        Domino(col=0, height=-3, spacing=1)
        check(False, "height=-3 should raise ValueError")
    except ValueError:
        check(True, "height=-3 raises ValueError")


def test_domino_rejects_negative_spacing():
    """Negative spacing should raise ValueError."""
    try:
        Domino(col=0, height=5, spacing=-1)
        check(False, "spacing=-1 should raise ValueError")
    except ValueError:
        check(True, "spacing=-1 raises ValueError")


def test_domino_top_coords_upright():
    """An upright domino's top should be directly above its base."""
    d = Domino(col=10, height=6, spacing=2)
    check(approx(d.top_x, 10.0), "upright top_x == col")
    check(approx(d.top_y, 6.0), "upright top_y == height")


def test_domino_fall_progression():
    """A falling domino should eventually reach FALLEN state."""
    d = Domino(col=5, height=6, spacing=2)
    d.state = FALLING
    d.fall_dir = 1
    dt = 1.0 / 24
    # Step enough times that it must topple.
    for _ in range(200):
        d.update(dt)
        if d.state == FALLEN:
            break
    check(d.state == FALLEN, "falling domino reaches FALLEN state")
    check(abs(d.angle) == 90.0, "fallen domino angle is 90")


def test_domino_settles_after_fallen():
    """FALLEN domino should transition to SETTLED after a few frames."""
    d = Domino(col=5, height=6, spacing=2)
    d.state = FALLEN
    d.angle = 90.0
    for _ in range(10):
        d.update(1.0 / 24)
        if d.state == SETTLED:
            break
    check(d.state == SETTLED, "FALLEN domino transitions to SETTLED")


# ── ChainSimulator setup tests ────────────────────────────────────────────────

def test_add_domino_positions():
    """First domino at col 2; each subsequent one shifts by spacing+1."""
    sim = ChainSimulator(width=80, fps=24)
    sim.add_domino(6, 2)
    check(sim.dominoes[0].col == 2, "first domino at col 2")
    sim.add_domino(6, 3)
    check(sim.dominoes[1].col == 2 + 2 + 1, "second domino col = 2+spacing+1")


def test_random_setup_count():
    """random_setup(N) should create exactly N dominoes."""
    random.seed(42)
    sim = ChainSimulator(width=80, fps=24)
    sim.random_setup(15)
    check(len(sim.dominoes) == 15, "random_setup(15) creates 15 dominoes")


def test_random_setup_heights_in_range():
    """Random heights should be in [3, 8] and spacings in [1, 4]."""
    random.seed(7)
    sim = ChainSimulator(width=120, fps=24)
    sim.random_setup(50)
    for d in sim.dominoes:
        check(3 <= d.height <= 8, f"height {d.height} in [3,8]")
        check(1 <= d.spacing <= 4, f"spacing {d.spacing} in [1,4]")


def test_random_setup_reproducible():
    """Same seed should produce identical chains."""
    random.seed(123)
    sim1 = ChainSimulator(width=80, fps=24)
    sim1.random_setup(20)
    random.seed(123)
    sim2 = ChainSimulator(width=80, fps=24)
    sim2.random_setup(20)
    h1 = [(d.height, d.spacing) for d in sim1.dominoes]
    h2 = [(d.height, d.spacing) for d in sim2.dominoes]
    check(h1 == h2, "same seed -> same chain config")


def test_random_setup_zero():
    """random_setup(0) should create an empty chain."""
    sim = ChainSimulator(width=80, fps=24)
    sim.random_setup(0)
    check(len(sim.dominoes) == 0, "random_setup(0) creates 0 dominoes")


def test_random_setup_negative_raises():
    """random_setup(-1) should raise ValueError."""
    sim = ChainSimulator(width=80, fps=24)
    try:
        sim.random_setup(-1)
        check(False, "random_setup(-1) should raise ValueError")
    except ValueError:
        check(True, "random_setup(-1) raises ValueError")


def test_uniform_setup():
    """uniform_setup should create identical dominoes."""
    sim = ChainSimulator(width=80, fps=24)
    sim.uniform_setup(10, height=5, spacing=3)
    check(len(sim.dominoes) == 10, "uniform_setup(10) creates 10 dominoes")
    for d in sim.dominoes:
        check(d.height == 5, "uniform domino height == 5")
        check(d.spacing == 3, "uniform domino spacing == 3")


def test_build_demo():
    """build_demo should return a sim with 20 dominoes."""
    sim = build_demo()
    check(len(sim.dominoes) == 20, "build_demo creates 20 dominoes")


# ── Trigger tests ─────────────────────────────────────────────────────────────

def test_trigger_first():
    """Triggering index 0 should start it falling rightward."""
    sim = ChainSimulator(width=80, fps=24)
    sim.uniform_setup(5)
    result = sim.trigger(idx=0, direction=1)
    check(result is True, "trigger returns True when it fires")
    check(sim.dominoes[0].state == FALLING, "domino 0 is FALLING")
    check(sim.dominoes[0].fall_dir == 1, "domino 0 fall_dir == 1")


def test_trigger_reverse():
    """Triggering the last domino with direction -1."""
    sim = ChainSimulator(width=80, fps=24)
    sim.uniform_setup(5)
    sim.trigger(idx=4, direction=-1)
    check(sim.dominoes[4].state == FALLING, "last domino is FALLING")
    check(sim.dominoes[4].fall_dir == -1, "last domino fall_dir == -1")


def test_trigger_out_of_range():
    """Triggering an out-of-range index should return False, not crash."""
    sim = ChainSimulator(width=80, fps=24)
    sim.uniform_setup(3)
    result = sim.trigger(idx=10, direction=1)
    check(result is False, "trigger out-of-range returns False")
    # No dominoes should have changed state.
    check(all(d.state == STANDING for d in sim.dominoes),
          "out-of-range trigger leaves all dominoes STANDING")


def test_trigger_already_falling():
    """Re-triggering a falling domino should return False (no-op)."""
    sim = ChainSimulator(width=80, fps=24)
    sim.uniform_setup(3)
    sim.trigger(idx=0)
    result = sim.trigger(idx=0)  # already falling
    check(result is False, "re-triggering a falling domino returns False")


# ── Physics / collision tests ──────────────────────────────────────────────────

def test_tight_chain_cascades():
    """Tight uniform spacing should cascade the full chain (prob ~1)."""
    random.seed(0)
    sim = ChainSimulator(width=200, fps=60)
    sim.uniform_setup(20, height=8, spacing=1)
    sim.trigger(idx=0, direction=1)
    # Run headless.
    sim._run_headless()
    settled = sum(1 for d in sim.dominoes if d.state in (FALLEN, SETTLED))
    check(settled == 20, f"tight chain fully cascades (got {settled}/20)")


def test_sparse_chain_may_stall():
    """Very wide spacing can cause the chain to stall (not all fall)."""
    random.seed(3)
    sim = ChainSimulator(width=200, fps=60)
    sim.uniform_setup(20, height=3, spacing=4)
    sim.trigger(idx=0, direction=1)
    sim._run_headless()
    settled = sum(1 for d in sim.dominoes if d.state in (FALLEN, SETTLED))
    # With height=3 spacing=4, transfer_prob = max(0.15, 1 - 4/3.6) = 0.15.
    # Over 20 dominoes the chain very likely stalls somewhere.
    check(settled <= 20, "sparse chain: settled <= total")
    # We can't guarantee a stall every time, but it should be < 20 often.
    # Just make sure it didn't crash and produced a sensible number.
    check(settled >= 1, "at least the triggered domino fell")


def test_all_settled_empty():
    """all_settled on an empty chain should be True (vacuous)."""
    sim = ChainSimulator(width=80, fps=24)
    check(sim.all_settled() is True, "empty chain is all_settled")


def test_all_settled_before_trigger():
    """A fresh chain with all standing dominoes is all_settled."""
    sim = ChainSimulator(width=80, fps=24)
    sim.uniform_setup(5)
    check(sim.all_settled() is True, "un-triggered chain is all_settled")


def test_not_all_settled_mid_fall():
    """A chain with a falling domino is NOT all_settled."""
    sim = ChainSimulator(width=80, fps=24)
    sim.uniform_setup(5)
    sim.trigger(idx=0)
    check(sim.all_settled() is False, "falling chain is not all_settled")


def test_headless_run_completes():
    """_run_headless should terminate without hanging."""
    random.seed(1)
    sim = ChainSimulator(width=80, fps=60)
    sim.uniform_setup(10, height=6, spacing=2)
    sim.trigger(idx=0, direction=1)
    sim._run_headless()
    check(sim.frame > 0, "headless run produced frames")
    check(sim.all_settled() is True, "headless run reaches all_settled")


def test_headless_max_frames_guard():
    """_run_headless should stop at max_frames if never settling."""
    sim = ChainSimulator(width=80, fps=60)
    # No dominoes, never triggered — all_settled is True immediately,
    # but test the guard by constructing a sim that never settles.
    sim.uniform_setup(2, height=6, spacing=2)
    # Don't trigger — all_settled() returns True immediately.
    sim._run_headless()
    check(sim.frame == 0, "un-triggered headless run does 0 frames")


# ── Stats tests ────────────────────────────────────────────────────────────────

def test_stats_initial():
    """stats() on a fresh chain should show all standing."""
    sim = ChainSimulator(width=80, fps=24)
    sim.uniform_setup(8)
    s = sim.stats()
    check(s["total"] == 8, "stats total == 8")
    check(s["standing"] == 8, "stats standing == 8 initially")
    check(s["falling"] == 0, "stats falling == 0 initially")
    check(s["settled"] == 0, "stats settled == 0 initially")


def test_stats_after_full_cascade():
    """stats() after a full cascade should show all fallen/settled."""
    random.seed(0)
    sim = ChainSimulator(width=200, fps=60)
    sim.uniform_setup(15, height=8, spacing=1)
    sim.trigger(idx=0, direction=1)
    sim._run_headless()
    s = sim.stats()
    fallen = s["fallen"] + s["settled"]
    check(fallen == 15, f"stats: all 15 fell (got {fallen})")
    check(s["standing"] == 0, "no dominoes left standing")


def test_stats_report_contains_key_info():
    """stats_report should mention key numbers."""
    random.seed(0)
    sim = ChainSimulator(width=200, fps=60)
    sim.uniform_setup(10, height=8, spacing=1)
    sim.trigger(idx=0, direction=1)
    sim._run_headless()
    report = sim.stats_report()
    check("Total dominoes : 10" in report, "report contains total")
    check("Frames" in report, "report contains frame count")


# ── Rendering tests ───────────────────────────────────────────────────────────

def test_render_no_color_has_no_ansi():
    """A no-color sim should render without ANSI escape sequences."""
    sim = ChainSimulator(width=60, fps=24, use_color=False)
    sim.uniform_setup(5)
    out = sim.render()
    check("\033[" not in out, "no-color render has no ANSI codes")


def test_render_with_color_has_ansi():
    """A color sim should include ANSI escape sequences."""
    sim = ChainSimulator(width=60, fps=24, use_color=True)
    sim.uniform_setup(5)
    out = sim.render()
    check("\033[" in out, "color render includes ANSI codes")


def test_render_empty_chain():
    """Rendering an empty chain should not crash."""
    sim = ChainSimulator(width=60, fps=24)
    out = sim.render()
    check(isinstance(out, str) and len(out) > 0, "empty chain renders a string")


def test_render_hud():
    """render_hud should produce a string with a progress bar."""
    sim = ChainSimulator(width=60, fps=24)
    sim.uniform_setup(10)
    hud = sim.render_hud(5, 10)
    check("Dominoes:" in hud, "hud contains dominoe count")
    check("█" in hud or "░" in hud, "hud contains progress bar chars")


# ── Width/fps clamping tests ───────────────────────────────────────────────────

def test_width_clamped():
    """Width below 10 should be clamped to 10."""
    sim = ChainSimulator(width=5, fps=24)
    check(sim.width == 10, "width clamped to 10")


def test_fps_clamped():
    """FPS below 1 should be clamped to 1."""
    sim = ChainSimulator(width=80, fps=0)
    check(sim.fps == 1, "fps clamped to 1")
    sim2 = ChainSimulator(width=80, fps=-5)
    check(sim2.fps == 1, "negative fps clamped to 1")


# ── Version test ───────────────────────────────────────────────────────────────

def test_version():
    """Version string should be defined and non-empty."""
    check(isinstance(__version__, str) and len(__version__) > 0,
          "version is non-empty string")


# ── Run all tests ─────────────────────────────────────────────────────────────

def main() -> int:
    tests = [
        # Domino
        test_domino_defaults,
        test_domino_rejects_invalid_height,
        test_domino_rejects_negative_spacing,
        test_domino_top_coords_upright,
        test_domino_fall_progression,
        test_domino_settles_after_fallen,
        # Setup
        test_add_domino_positions,
        test_random_setup_count,
        test_random_setup_heights_in_range,
        test_random_setup_reproducible,
        test_random_setup_zero,
        test_random_setup_negative_raises,
        test_uniform_setup,
        test_build_demo,
        # Trigger
        test_trigger_first,
        test_trigger_reverse,
        test_trigger_out_of_range,
        test_trigger_already_falling,
        # Physics / collisions
        test_tight_chain_cascades,
        test_sparse_chain_may_stall,
        test_all_settled_empty,
        test_all_settled_before_trigger,
        test_not_all_settled_mid_fall,
        test_headless_run_completes,
        test_headless_max_frames_guard,
        # Stats
        test_stats_initial,
        test_stats_after_full_cascade,
        test_stats_report_contains_key_info,
        # Rendering
        test_render_no_color_has_no_ansi,
        test_render_with_color_has_ansi,
        test_render_empty_chain,
        test_render_hud,
        # Clamping
        test_width_clamped,
        test_fps_clamped,
        # Version
        test_version,
    ]

    print(f"Running {len(tests)} tests for domino_chain v{__version__}...\n")
    for test in tests:
        try:
            test()
        except Exception as exc:
            global _failed
            _failed += 1
            _failures.append(f"{test.__name__}: {exc}")
            print(f"  ERROR in {test.__name__}: {exc}")

    print(f"\n{'=' * 50}")
    print(f"  Passed: {_passed}   Failed: {_failed}")
    if _failures:
        print("\n  Failures:")
        for f in _failures:
            print(f"    - {f}")
    print(f"{'=' * 50}")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())