"""Smoke tests for cuckoo_clock — pure-logic (no curses required)."""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from cuckoo_clock import (
    ClockState,
    hours_minutes_seconds,
    start_cuckoo,
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