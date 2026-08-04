#!/usr/bin/env python3
"""Tests for the Pendulum Wave Simulator."""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from pendulum_wave import (
    build_pendulums,
    Pendulum,
    render_static,
    G,
)


def test_pendulum_count():
    pens = build_pendulums(10, 60.0, 51, 0.5, 12.0)
    assert len(pens) == 10


def test_periods_decrease():
    """Longer pendulum → longer period."""
    pens = build_pendulums(8, 60.0, 51, 0.5, 12.0)
    for a, b in zip(pens, pens[1:]):
        assert a.period > b.period, f"{a.period} should exceed {b.period}"


def test_lengths_decrease():
    """First pendulum is the longest."""
    pens = build_pendulums(8, 60.0, 51, 0.5, 12.0)
    for a, b in zip(pens, pens[1:]):
        assert a.length > b.length


def test_resync():
    """At t = derived cycle time all pendulums realign (angle ≈ amplitude)."""
    max_length = 0.5
    swings = 51
    pens = build_pendulums(12, 60.0, swings, max_length, 12.0)
    # true cycle = swings × period of longest pendulum
    cycle = swings * pens[0].period
    angles = [p.angle(cycle) for p in pens]
    first = angles[0]
    for a in angles:
        assert abs(a - first) < 1e-6, f"Resync failed: {a} vs {first}"


def test_angle_bounds():
    """Angle never exceeds amplitude."""
    pens = build_pendulums(6, 60.0, 51, 0.5, 12.0)
    amp = pens[0].amplitude
    for t in range(0, 600, 7):
        for p in pens:
            assert abs(p.angle(t * 0.1)) <= amp + 1e-9


def test_period_formula():
    """T = 2π√(L/g)."""
    p = Pendulum(index=0, length=0.5, amplitude=0.2, n_swing=10)
    expected = 2 * math.pi * math.sqrt(0.5 / G)
    assert abs(p.period - expected) < 1e-12


def test_static_render():
    """render_static produces a non-empty string with expected content."""
    pens = build_pendulums(8, 60.0, 51, 0.5, 12.0)
    out = render_static(pens, 5.0, 80, 24, 0.2, 0.6, mode=1)
    assert isinstance(out, str)
    assert len(out) > 100
    assert "t = " in out  # label present
    assert "●" in out      # at least one bob


def test_static_render_modes():
    """All four modes produce output."""
    pens = build_pendulums(6, 60.0, 51, 0.5, 12.0)
    for mode in (1, 2, 3, 4):
        out = render_static(pens, 10.0, 80, 24, 0.2, 0.6, mode=mode)
        assert len(out) > 50, f"mode {mode} produced too little output"


def test_bob_positions():
    """At t=0 all bobs should be at maximum displacement (angle = amplitude)."""
    pens = build_pendulums(5, 60.0, 51, 0.5, 12.0)
    for p in pens:
        assert abs(p.angle(0.0) - p.amplitude) < 1e-12


def test_half_period():
    """At half period the bob should be at the opposite extreme."""
    p = Pendulum(index=0, length=0.5, amplitude=0.2, n_swing=10)
    assert abs(p.angle(p.period / 2) - (-0.2)) < 1e-9


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)