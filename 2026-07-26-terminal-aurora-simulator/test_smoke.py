"""Smoke + regression tests for the Terminal Aurora Simulator.

Run with: ``python3 test_smoke.py``
No external dependencies; imports the sibling ``aurora`` module.
"""
import aurora


# ---------------------------------------------------------------------------
# Original smoke tests: every palette renders, resize works, keys work.
# ---------------------------------------------------------------------------
for name in aurora.PALETTE_ORDER:
    s = aurora.init_state(80, 24, 42, name)
    s.time = 3.0
    frame = aurora.build_frame(s)
    assert len(frame) > 0
    # verify palette lookup works across the range
    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        c = aurora.palette_color(name, t)
        assert len(c) == 3 and all(0 <= x <= 255 for x in c)
    # advance time and render a few more frames to exercise the loop
    for _ in range(5):
        s.time += 0.1
        f2 = aurora.build_frame(s)
        assert len(f2) > 0

# Verify resize reinit
s = aurora.init_state(80, 24, 42, "green")
aurora.reinit_for_size(s, 100, 30)
assert s.width == 100 and s.height == 30

# Verify handle_key
assert aurora.handle_key("q", s) is True
assert aurora.handle_key("esc", s) is True
assert aurora.handle_key(None, s) is False
assert aurora.handle_key("c", s) is False
assert s.palette_name in aurora.PALETTE_ORDER


# ---------------------------------------------------------------------------
# Regression: degenerate / empty noise grids must not raise.
# ---------------------------------------------------------------------------
assert aurora.value_noise_1d([], 5.0) == 0.0
assert aurora.value_noise_2d([], 1.0, 1.0) == 0.0
assert aurora.value_noise_2d([[]], 1.0, 1.0) == 0.0
assert aurora.fractal_noise_1d([], 1.0) == 0.0
assert aurora.fractal_noise_1d([0.5], 1.0, octaves=0) == 0.0


# ---------------------------------------------------------------------------
# Regression: speed must never get stuck at 0 or go negative.
# ---------------------------------------------------------------------------
s = aurora.init_state(80, 24, 1, "green")
s.speed = 0.0
aurora.handle_key("+", s)
assert s.speed > 0.0, "speed stuck at 0 after '+'"
s.speed = -1.0
aurora.handle_key("+", s)
assert s.speed > 0.0, "speed still negative after '+'"
aurora.handle_key("-", s)
assert 0.05 <= s.speed <= 8.0


# ---------------------------------------------------------------------------
# New feature toggles (m, s, l, t) flip State booleans.
# ---------------------------------------------------------------------------
s = aurora.init_state(80, 24, 1, "green")
assert s.show_moon and s.show_stars and s.show_lake and s.show_mountains
aurora.handle_key("m", s); assert s.show_moon is False
aurora.handle_key("m", s); assert s.show_moon is True
aurora.handle_key("s", s); assert s.show_stars is False
aurora.handle_key("l", s); assert s.show_lake is False
aurora.handle_key("t", s); assert s.show_mountains is False
# toggling them back on
aurora.handle_key("s", s); assert s.show_stars is True
aurora.handle_key("l", s); assert s.show_lake is True
aurora.handle_key("t", s); assert s.show_mountains is True


# ---------------------------------------------------------------------------
# Palette cycling now visits 6 palettes (incl. magnetic).
# ---------------------------------------------------------------------------
assert "magnetic" in aurora.PALETTE_ORDER
assert len(aurora.PALETTE_ORDER) >= 6
s = aurora.init_state(80, 24, 1, "green")
seen = set()
for _ in range(len(aurora.PALETTE_ORDER)):
    seen.add(s.palette_name)
    aurora.handle_key("c", s)
assert seen == set(aurora.PALETTE_ORDER)
c = aurora.palette_color("magnetic", 0.5)
assert len(c) == 3 and all(0 <= x <= 255 for x in c)


# ---------------------------------------------------------------------------
# init_state accepts feature-toggle kwargs.
# ---------------------------------------------------------------------------
s = aurora.init_state(80, 24, 1, "green",
                     show_moon=False, show_stars=False,
                     show_mountains=False, show_lake=False)
assert not s.show_moon and not s.show_stars
assert not s.show_mountains and not s.show_lake
# rendering with everything off still works (just sky + aurora)
assert len(aurora.build_frame(s)) > 0


# ---------------------------------------------------------------------------
# Shooting stars: spawn over time and decay.
# ---------------------------------------------------------------------------
s = aurora.init_state(100, 30, 42, "magnetic")
s.time = 0.0
any_active = False
for _ in range(500):
    dt = 1 / 24
    s.time += dt
    aurora.maybe_spawn_shooting_star(s, s.meteor_rng)
    aurora.update_shooting_stars(s, dt)
    if s.shooting_stars:
        any_active = True
assert any_active, "shooting stars never spawned"
# after a long pause with no spawning, the list drains
s.shooting_stars[:] = []
aurora.update_shooting_stars(s, 10.0)
assert s.shooting_stars == []


# ---------------------------------------------------------------------------
# Moon: present by default and renders something in the frame.
# ---------------------------------------------------------------------------
s = aurora.init_state(80, 24, 100, "green")
assert s.moon is not None
assert 0.0 <= s.moon.phase < 1.0
frame = aurora.build_frame(s)
assert "O" in frame or "." in frame


# ---------------------------------------------------------------------------
# Lake reflection: with show_lake, the frame should include water ripple
# characters or reflection colors when the aurora is bright near the horizon.
# ---------------------------------------------------------------------------
s = aurora.init_state(80, 24, 7, "green")
s.show_lake = True
s.time = 3.0
frame = aurora.build_frame(s)
assert "38;2;" in frame  # truecolor sequences present


# ---------------------------------------------------------------------------
# Edge cases: tiny terminal, huge time, negative seed.
# ---------------------------------------------------------------------------
s = aurora.init_state(20, 8, 1, "green")
assert len(aurora.build_frame(s)) > 0
s = aurora.init_state(80, 24, 1, "green")
s.time = 1e9
assert len(aurora.build_frame(s)) > 0
s = aurora.init_state(80, 24, -5, "ice")
assert s.seed == -5
assert len(aurora.build_frame(s)) > 0


# ---------------------------------------------------------------------------
# Empty/degenerate canvas returns "".
# ---------------------------------------------------------------------------
s = aurora.State(width=0, height=0, seed=1, palette_name="green")
assert aurora.build_frame(s) == ""


# ---------------------------------------------------------------------------
# make_mountains handles width 0 and 1 without crashing.
# ---------------------------------------------------------------------------
assert aurora.make_mountains(0, 20, 1) == []
assert aurora.make_mountains(1, 20, 1) == [19]


# ---------------------------------------------------------------------------
# Regression: build_frame must not crash on very short terminals (h < 4).
# Previously sky_h was forced to max(4, ...) which overflowed the row buffer.
# ---------------------------------------------------------------------------
for h in [1, 2, 3]:
    s = aurora.init_state(80, h, 42, "green")
    s.time = 1.0
    f = aurora.build_frame(s)
    assert isinstance(f, str) and f != ""
    # frame should have at most h content rows (plus control lines)
    assert f.count("\n") <= 2 * h + 2


# ---------------------------------------------------------------------------
# Regression: noise functions must not raise on non-finite inputs (inf/nan).
# Previously int(math.floor(inf)) raised OverflowError.
# ---------------------------------------------------------------------------
import math
assert aurora.value_noise_1d([0.5, 0.7], float("inf")) == 0.0
assert aurora.value_noise_1d([0.5, 0.7], float("nan")) == 0.0
assert aurora.value_noise_2d([[0.5]], float("inf"), 1.0) == 0.0
assert aurora.value_noise_2d([[0.5]], 1.0, float("nan")) == 0.0
assert aurora.value_noise_2d([[0.5]], float("inf"), float("inf")) == 0.0


# ---------------------------------------------------------------------------
# Regression: make_screenshot.parse_ansi_frame correctly skips control lines.
# Previously it treated HOME/CLEAR_LINE/RESET escape lines as screen rows,
# misaligning the entire screenshot.
# ---------------------------------------------------------------------------
import make_screenshot
s = aurora.init_state(30, 6, 42, "magnetic")
s.time = 3.0
frame = aurora.build_frame(s)
colors, chars = make_screenshot.parse_ansi_frame(frame, 30, 6)
# Row 0 (top sky) should have content, not be empty as before the fix.
content_in_row0 = any(c != " " for c in chars[0])
content_in_row3 = any(c != " " for c in chars[3])  # mountain row
assert content_in_row0, "screenshot row 0 was empty (control-line misparse bug)"
assert content_in_row3, "screenshot row 3 was empty (control-line misparse bug)"


print("OK: all palettes render, resize + keys work, "
      "new features (moon, shooting stars, lake, toggles) verified, "
      "empty-grid + speed-clamp + short-terminal + inf-noise + "
      "screenshot-parse regressions pass")