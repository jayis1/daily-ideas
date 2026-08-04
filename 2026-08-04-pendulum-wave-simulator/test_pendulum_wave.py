#!/usr/bin/env python3
"""Tests for the Pendulum Wave Simulator.

Run with:  python3 test_pendulum_wave.py
No external test framework required — uses a tiny built-in runner.
"""

import math
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from pendulum_wave import (
    build_pendulums,
    Pendulum,
    Renderer,
    render_static,
    print_info,
    G,
    __version__,
)


# ── Existing physics tests ────────────────────────────────────────────────────

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
    cycle = swings * pens[0].period
    angles = [p.angle(cycle) for p in pens]
    first = angles[0]
    for a in angles:
        assert abs(a - first) < 1e-6, f"Resync failed: {a} vs {first}"


def test_resync_at_quarter():
    """At quarter cycle, all pendulums that have integer-swing /4 should align."""
    # With 4 pendulums and base_swings=4, at quarter cycle each has
    # completed (base_swings+i) * 0.25 swings.  We just check the longest
    # pendulum is at zero displacement (cos(π/2)=0).
    pens = build_pendulums(4, 60.0, 4, 0.5, 12.0)
    cycle = 4 * pens[0].period
    quarter = cycle / 4.0
    # Longest completes exactly 1 full swing in the quarter → cos(2π)=1,
    # so it should be back at amplitude.
    assert abs(pens[0].angle(quarter) - pens[0].amplitude) < 1e-9


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


# ── New tests for enhanced features ───────────────────────────────────────────

def test_version_string():
    """The module exposes a __version__ string."""
    assert isinstance(__version__, str)
    assert len(__version__) > 0
    parts = __version__.split(".")
    assert len(parts) >= 2, "version should have at least major.minor"


def test_energy_constant():
    """Total mechanical energy should be time-invariant (undamped)."""
    p = Pendulum(index=0, length=0.5, amplitude=0.2, n_swing=10)
    e0 = p.energy(0.0)
    e_quarter = p.energy(p.period / 4.0)
    e_half = p.energy(p.period / 2.0)
    # Energy should be conserved to within floating-point tolerance
    assert abs(e0 - e_quarter) < 1e-9, f"energy drift: {e0} vs {e_quarter}"
    assert abs(e0 - e_half) < 1e-9, f"energy drift: {e0} vs {e_half}"


def test_energy_formula():
    """Energy equals ½ m g L A² for the harmonic pendulum."""
    L, A, m = 0.5, 0.2, 1.0
    p = Pendulum(index=0, length=L, amplitude=A, n_swing=10)
    expected = 0.5 * m * G * L * A ** 2
    assert abs(p.energy(0.0, mass=m) - expected) < 1e-12


def test_angular_velocity():
    """Angular velocity is zero at the extremes (t=0, t=T/2)."""
    p = Pendulum(index=0, length=0.5, amplitude=0.2, n_swing=10)
    assert abs(p.angular_velocity(0.0)) < 1e-12
    assert abs(p.angular_velocity(p.period / 2.0)) < 1e-12
    # At quarter period, |θ̇| should be maximal = A·ω
    omega = 2 * math.pi / p.period
    expected_max = p.amplitude * omega
    assert abs(abs(p.angular_velocity(p.period / 4.0)) - expected_max) < 1e-9


def test_no_color_render():
    """Monochrome rendering should contain no ANSI colour escapes."""
    pens = build_pendulums(6, 60.0, 51, 0.5, 12.0)
    out = render_static(pens, 5.0, 80, 24, 0.2, 0.6, mode=1, use_color=False)
    assert "\033[38;2;" not in out, "colour escape found in monochrome output"
    # Bobs should still be present
    assert "●" in out


def test_ascii_render():
    """ASCII mode uses 'O' for bobs instead of '●'."""
    pens = build_pendulums(6, 60.0, 51, 0.5, 12.0)
    out = render_static(pens, 5.0, 80, 24, 0.2, 0.6, mode=1,
                        use_color=False, charset="ascii")
    assert "O" in out, "ASCII bob 'O' not found"
    assert "●" not in out, "Unicode bob leaked into ASCII mode"
    assert "│" not in out, "Unicode string char leaked into ASCII mode"


def test_renderer_color_toggle():
    """Renderer can toggle colour on and off after construction."""
    pens = build_pendulums(4, 60.0, 51, 0.5, 12.0)
    r = Renderer(80, 24, pens, 0.2, 0.6, mode=1, use_color=True)
    assert r.use_color is True
    r.use_color = False
    out = r.render(5.0)
    assert "\033[38;2;" not in out


def test_renderer_zero_max_dimensions():
    """Renderer should not crash when max_x or max_y is zero."""
    pens = build_pendulums(4, 60.0, 51, 0.5, 12.0)
    r = Renderer(80, 24, pens, max_x=0.0, max_y=0.0, mode=1)
    out = r.render(5.0)
    assert isinstance(out, str)
    assert len(out) > 50


def test_info_output(capsys=None):
    """print_info produces a table with the expected columns."""
    pens = build_pendulums(6, 60.0, 51, 0.5, 12.0)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_info(pens, swings=51, num=6)
    text = buf.getvalue()
    assert "Pendulum Wave" in text
    assert "energy" in text.lower()
    assert "Resync cycle" in text
    assert "realign" in text


def test_validate_args_rejects_bad_input():
    """Invalid parameters produce a non-None error message."""
    from pendulum_wave import validate_args, parse_args
    # Too few pendulums
    args = parse_args(["-n", "1"])
    assert validate_args(args) is not None
    # Negative cycle
    args = parse_args(["-T", "-5"])
    assert validate_args(args) is not None
    # Amplitude out of range
    args = parse_args(["-a", "95"])
    assert validate_args(args) is not None
    # Valid args → None
    args = parse_args(["-n", "16"])
    assert validate_args(args) is None


def test_version_flag(capsys=None):
    """--version prints the version and exits."""
    from pendulum_wave import main
    import io
    import contextlib
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            main(["--version"])
    except SystemExit as e:
        assert e.code == 0
    assert __version__ in buf.getvalue()


def test_renderer_trail_accumulation():
    """Trails grow as more frames are rendered."""
    pens = build_pendulums(4, 60.0, 51, 0.5, 12.0)
    r = Renderer(80, 24, pens, 0.2, 0.6, mode=1)
    r.render(0.0)
    assert all(len(t) == 1 for t in r.trails)
    r.render(0.1)
    assert all(len(t) == 2 for t in r.trails)
    # Trail length capped
    for _ in range(100):
        r.render(0.2)
    assert all(len(t) <= r.trail_len for t in r.trails)


def test_renderer_tiny_dimensions():
    """Renderer must not crash with height=1 or width=1 (degenerate sizes)."""
    pens = build_pendulums(4, 60.0, 51, 0.5, 12.0)
    for w, h in [(1, 1), (1, 24), (80, 1), (0, 0), (-5, -5)]:
        r = Renderer(w, h, pens, 0.2, 0.6, mode=1, use_color=False)
        out = r.render(5.0)
        assert isinstance(out, str)
        assert len(out) > 0, f"empty output for dims ({w}, {h})"
        # Internal dimensions must be clamped to at least 2
        assert r.w >= 2 and r.h >= 2


def test_validate_args_rejects_bad_dimensions():
    """Negative or too-small --width / --height are rejected."""
    from pendulum_wave import validate_args, parse_args
    args = parse_args(["--frame", "0", "--width", "0"])
    assert validate_args(args) is not None
    args = parse_args(["--frame", "0", "--width", "-1"])
    assert validate_args(args) is not None
    args = parse_args(["--frame", "0", "--height", "1"])
    assert validate_args(args) is not None
    args = parse_args(["--frame", "0", "--height", "-5"])
    assert validate_args(args) is not None
    # Valid dimensions → None
    args = parse_args(["--frame", "0", "--width", "80", "--height", "24"])
    assert validate_args(args) is None


def test_render_static_tiny_dimensions():
    """render_static must not crash with degenerate dimensions."""
    pens = build_pendulums(4, 60.0, 51, 0.5, 12.0)
    for w, h in [(1, 1), (2, 2), (5, 3)]:
        out = render_static(pens, 1.0, w, h, 0.2, 0.6, mode=1, use_color=False)
        assert isinstance(out, str) and len(out) > 0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failures = []
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {t.__name__}: {e}")
            failures.append(t.__name__)
        except Exception as e:
            print(f"  ✗ {t.__name__}: {type(e).__name__}: {e}")
            failures.append(t.__name__)
    print(f"\n{passed}/{len(tests)} tests passed")
    if failures:
        print("Failed: " + ", ".join(failures))
    sys.exit(0 if passed == len(tests) else 1)