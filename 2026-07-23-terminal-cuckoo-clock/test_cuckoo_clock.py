"""Smoke tests for cuckoo_clock — pure-logic (no curses required)."""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from cuckoo_clock import (
    ClockState,
    ChimeState,
    hours_minutes_seconds,
    start_cuckoo,
    start_chime,
    note_interval,
    NOTE_FREQ,
    format_time,
    parse_start_time,
    WESTMINSTER,
    gear,
    pendulum_bob,
    overlay,
)


def test_quarter_labels():
    assert hours_minutes_seconds(0) == (12, 0, 0, 0)
    assert hours_minutes_seconds(900) == (12, 15, 0, 15)
    assert hours_minutes_seconds(1800) == (12, 30, 0, 30)
    assert hours_minutes_seconds(2700) == (12, 45, 0, 45)
    assert hours_minutes_seconds(3600) == (1, 0, 0, 0)
    assert hours_minutes_seconds(13 * 3600) == (1, 0, 0, 0)
    assert hours_minutes_seconds(12 * 3600) == (12, 0, 0, 0)
    assert hours_minutes_seconds(11 * 3600 + 59 * 60) == (11, 59, 0, 45)


def test_westminster_keys():
    assert set(WESTMINSTER.keys()) == {15, 30, 45, 60}
    assert WESTMINSTER[60] == []


def test_start_cuckoo_sets_state():
    s = ClockState()
    assert not s.cuckoo_active
    start_cuckoo(s, 3)
    assert s.cuckoo_active
    assert s.cuckoo_count == 3
    assert s.cuckoo_step == 0
    assert any("Cuckoo" in entry for entry in s.log)


def test_start_cuckoo_clamps_count():
    """Count must be clamped to [1, 12] to avoid runaway strikes."""
    s = ClockState()
    start_cuckoo(s, 99)
    assert s.cuckoo_count == 12
    start_cuckoo(s, -5)
    assert s.cuckoo_count == 1
    assert "×1" in s.log[-1]


def test_gear_dimensions():
    rows = gear(teeth=10, radius=4, rotation=0.0)
    assert rows
    assert all(isinstance(r, str) for r in rows)
    assert len(rows) == len(rows[0])  # square
    assert len(rows) == 11  # 2*4+3


def test_pendulum_renders():
    rows = pendulum_bob(0.2)
    assert rows
    assert any("(" in r for r in rows)


def test_overlay_clips():
    screen = [[" "] * 5 for _ in range(5)]
    # fully out of bounds vertically and horizontally
    overlay(screen, ["###", "###"], top=-5, left=-5)
    assert screen == [[" "] * 5 for _ in range(5)]
    overlay(screen, ["AB", "CD"], top=2, left=2)
    assert screen[2][2] == "A"
    assert screen[3][3] == "D"


def test_hour12_rollover():
    # midnight = 12 cuckoos
    assert hours_minutes_seconds(0)[0] == 12
    # 1 AM = 1
    assert hours_minutes_seconds(3600)[0] == 1
    # noon = 12
    assert hours_minutes_seconds(12 * 3600)[0] == 12
    # 13:00 -> 1
    assert hours_minutes_seconds(13 * 3600)[0] == 1


# ---------------------------------------------------------------------------
# New tests for v1.1.0 features
# ---------------------------------------------------------------------------

def test_parse_start_time():
    assert parse_start_time("00:00:00") == 0
    assert parse_start_time("11:00") == 11 * 3600
    assert parse_start_time("23:59:30") == 23 * 3600 + 59 * 60 + 30
    assert parse_start_time("0:0:0") == 0


def test_parse_start_time_rejects_bad():
    for bad in ["bad", "1", "1:2:3:4", "25:00", "12:60", "12:00:61", "-1:00"]:
        try:
            parse_start_time(bad)
            raise AssertionError(f"expected ValueError for {bad!r}")
        except ValueError:
            pass


def test_note_interval_bounds():
    for note in NOTE_FREQ:
        iv = note_interval(note)
        assert 0.22 <= iv <= 0.65, f"{note}: {iv}"


def test_note_interval_lower_is_longer():
    # B3 (low) should ring longer than C5 (high)
    assert note_interval("B3") > note_interval("C5")


def test_chime_state_defaults():
    c = ChimeState()
    assert not c.active
    assert c.notes == []
    assert c.index == 0
    assert c.timer == 0.0


def test_start_chime_quarter():
    s = ClockState()
    start_chime(s, 15)
    assert s.chime.active
    assert s.chime.notes == WESTMINSTER[15]
    assert s.chime.index == 0
    assert any("Chime" in e for e in s.log)


def test_start_chime_hour_is_noop():
    """Quarter 60 is the full hour; chime is a no-op (cuckoo handles it)."""
    s = ClockState()
    start_chime(s, 60)
    assert not s.chime.active
    assert s.chime.notes == []


def test_start_chime_unknown_quarter():
    s = ClockState()
    start_chime(s, 7)
    assert not s.chime.active
    assert s.chime.notes == []


def test_format_time_12h():
    assert format_time(1, 0, 0, False, 13 * 3600) == "⏰  01:00:00"
    assert format_time(12, 0, 0, False, 0) == "⏰  12:00:00"


def test_format_time_24h():
    assert format_time(1, 0, 0, True, 13 * 3600) == "⏰  13:00:00"
    assert format_time(12, 0, 0, True, 0) == "⏰  00:00:00"
    assert format_time(1, 0, 0, True, 3600) == "⏰  01:00:00"


def test_clock_state_has_new_fields():
    s = ClockState()
    assert hasattr(s, "chime")
    assert hasattr(s, "use_24h")
    assert s.use_24h is False
    assert isinstance(s.chime, ChimeState)


def test_use_24h_toggle():
    s = ClockState()
    assert s.use_24h is False
    s.use_24h = True
    assert s.use_24h is True


def test_gear_rotation_changes_output():
    """A non-zero rotation should produce a different glyph grid."""
    a = gear(teeth=10, radius=4, rotation=0.0)
    b = gear(teeth=10, radius=4, rotation=0.5)
    assert a != b


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failed += 1
            except Exception as e:
                print(f"ERROR {name}: {type(e).__name__}: {e}")
                failed += 1
    print(f"\n{'All passed' if failed == 0 else f'{failed} failed'}")
    sys.exit(failed)