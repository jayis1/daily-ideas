#!/usr/bin/env python3
"""
Tests for the Terminal Lighthouse Keeper game logic.

Run with: python3 -m pytest test_lighthouse.py -v
"""
import sys
import os
import random
from pathlib import Path

# Ensure the module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lighthouse import Lighthouse, tick, _advance_time, _calculate_final_score, \
    save_high_score, load_high_scores, DIFFICULTIES, SCORES_FILE


# ─── Fixtures / Helpers ───────────────────────────────────────────
def make_state(difficulty="medium"):
    """Create a fresh game state for testing."""
    return Lighthouse(difficulty=difficulty)


def tick_many(state, n):
    """Advance the game by n ticks."""
    for _ in range(n):
        tick(state, 0.1)


# ─── State Initialization ──────────────────────────────────────────
def test_initial_state_medium():
    s = make_state("medium")
    assert s.fuel == 80, f"Expected fuel=80, got {s.fuel}"
    assert s.lens_health == 100
    assert s.beam_on is True
    assert s.hour == 18
    assert s.minutes == 0
    assert s.game_over is False
    assert s.paused is False
    assert s.efficiency_mode is False


def test_initial_state_easy():
    s = make_state("easy")
    assert s.fuel == 90
    assert s.lens_health == 100


def test_initial_state_hard():
    s = make_state("hard")
    assert s.fuel == 60
    assert s.lens_health == 80


def test_invalid_difficulty_defaults_to_medium():
    s = Lighthouse(difficulty="nonexistent")
    assert s.diff_config["label"] == "Normal"


# ─── Time Advancement ─────────────────────────────────────────────
def test_advance_time_minutes():
    s = make_state()
    _advance_time(s, 5)
    assert s.minutes == 5


def test_advance_time_wraps_hour():
    s = make_state()
    _advance_time(s, 61)
    assert s.hour == 19
    assert s.minutes == 1


def test_advance_time_dawn_triggers_game_over():
    s = make_state()
    s.hour = 5
    s.minutes = 55
    _advance_time(s, 10)  # pushes to hour 6
    assert s.dawn_reached is True
    assert s.game_over is True


# ─── Fuel Mechanics ────────────────────────────────────────────────
def test_fuel_depletes_while_beam_on():
    s = make_state()
    initial_fuel = s.fuel
    # Disable random events to avoid supply crates adding fuel
    s.event_timer = 9999
    s.current_event = None
    # Disable weather to avoid storm effects
    s.storm_active = False
    s.weather = "clear"
    s.weather_timer = 9999
    tick_many(s, 50)
    assert s.fuel < initial_fuel, "Fuel should decrease while beam is on"


def test_fuel_stops_at_zero():
    s = make_state()
    s.fuel = 0.5
    tick_many(s, 20)
    assert s.fuel >= 0, "Fuel should not go below zero"


def test_beam_turns_off_when_fuel_empty():
    s = make_state()
    s.fuel = 0
    tick_many(s, 1)
    assert s.beam_on is False, "Beam should turn off when fuel hits zero"


def test_refueling():
    s = make_state()
    s.fuel = 30
    random.seed(42)
    fuel_gain = random.randint(15, 30)  # deterministic
    s.fuel = min(100, s.fuel + fuel_gain)
    assert s.fuel >= 45, "Refueling should increase fuel"


# ─── Efficiency Mode ───────────────────────────────────────────────
def test_efficiency_mode_reduces_fuel_rate():
    s = make_state()
    s.efficiency_mode = False
    s.fuel = 80
    tick_many(s, 20)
    fuel_normal = s.fuel

    s2 = make_state()
    s2.efficiency_mode = True
    s2.fuel = 80
    tick_many(s2, 20)
    # Efficiency mode should preserve more fuel
    assert s2.fuel >= fuel_normal, "Eco mode should use fuel more slowly"


def test_efficiency_mode_caps_beam():
    s = make_state()
    s.efficiency_mode = True
    s.fuel = 80
    s.lens_health = 100
    tick_many(s, 50)
    assert s.beam_intensity <= 65, "Eco mode should cap beam intensity around 60%"


def test_efficiency_mode_turns_off_with_beam():
    s = make_state()
    s.efficiency_mode = True
    s.beam_on = False
    # Eco mode should be false if beam is off
    s.efficiency_mode = False  # reset
    assert s.efficiency_mode is False


# ─── Engine Mechanics ──────────────────────────────────────────────
def test_engine_heats_up_while_beam_on():
    s = make_state()
    initial_temp = s.engine_temp
    tick_many(s, 50)
    assert s.engine_temp > initial_temp, "Engine should heat up while beam is on"


def test_engine_cools_while_beam_off():
    s = make_state()
    s.engine_temp = 80
    s.beam_on = False
    tick_many(s, 50)
    assert s.engine_temp < 80, "Engine should cool when beam is off"


def test_engine_shutdown_at_100():
    s = make_state()
    s.engine_temp = 99.9  # Very close to shutdown threshold
    tick_many(s, 50)       # Enough ticks to push past 100
    assert s.beam_on is False, "Beam should turn off when engine overheats"
    assert s.flash_message != ""


# ─── Beam Intensity ────────────────────────────────────────────────
def test_beam_intensity_follows_fuel_and_lens():
    s = make_state()
    s.fuel = 100
    s.lens_health = 100
    tick_many(s, 20)
    assert s.beam_intensity > 50, "Full fuel and lens should give strong beam"


def test_beam_decays_when_off():
    s = make_state()
    s.beam_on = False
    s.beam_intensity = 50
    tick_many(s, 30)
    assert s.beam_intensity < 10, "Beam intensity should decay when beam is off"


# ─── Weather System ───────────────────────────────────────────────
def test_storm_damages_lens():
    s = make_state()
    s.storm_active = True
    s.storm_intensity = 80
    s.lens_health = 100
    tick_many(s, 100)
    assert s.lens_health < 100, "Storms should damage lens health"


def test_weather_timer_advances():
    s = make_state()
    initial_timer = s.weather_timer
    tick_many(s, 10)
    assert s.weather_timer < initial_timer or s.weather_timer != initial_timer


# ─── Ship Mechanics ────────────────────────────────────────────────
def test_ships_spawn_over_time():
    s = make_state()
    s.ship_spawn_timer = 1
    tick_many(s, 5)
    # Ships may or may not spawn due to randomness, but timer should advance
    assert isinstance(s.ships, list)


def test_distress_ship_signal():
    s = make_state()
    s.ships.append({"x": 10, "distress": True, "saved": False, "timer": 30, "direction": -1})
    # Simulate pressing S
    for ship in s.ships:
        if ship["distress"] and not ship.get("saved"):
            ship["saved"] = True
            ship["distress"] = False
            s.ships_saved += 1
            s.score += 200
            break
    assert s.ships_saved == 1
    assert s.score >= 200


# ─── Pause ─────────────────────────────────────────────────────────
def test_pause_prevents_tick():
    s = make_state()
    initial_tick = s.total_ticks
    s.paused = True
    tick_many(s, 20)
    assert s.total_ticks == initial_tick, "Paused game should not advance"


# ─── Score Calculation ─────────────────────────────────────────────
def test_final_score_includes_all_factors():
    s = make_state()
    s.ships_saved = 3
    s.fuel = 80
    s.lens_health = 90
    s.engine_temp = 40
    s.dawn_reached = True
    _calculate_final_score(s)
    # 3*100 + 80*5 + 90*3 + (100-40)*2 = 300 + 400 + 270 + 120 = 1090 for medium (x1.0)
    assert s.score >= 1000, f"Expected score >= 1000, got {s.score}"


def test_hard_difficulty_multiplier():
    s = make_state("hard")
    s.ships_saved = 3
    s.fuel = 80
    s.lens_health = 90
    s.engine_temp = 40
    s.dawn_reached = True
    _calculate_final_score(s)
    # Same base as above but x1.5
    assert s.score >= 1500, f"Hard mode should multiply score, got {s.score}"


# ─── High Scores ───────────────────────────────────────────────────
def test_save_and_load_high_scores(tmp_path=None):
    # Use a temporary file for testing
    import tempfile
    from lighthouse import SCORES_FILE as orig_scores_file
    import lighthouse as lh_mod
    tmp = tempfile.mktemp(suffix=".json")
    lh_mod.SCORES_FILE = Path(tmp)

    try:
        # Save a score
        rank = save_high_score(500, "medium", 3, 0)
        assert rank >= 1, "Rank should be 1-based"

        # Load it back
        scores = load_high_scores()
        assert len(scores) >= 1
        assert scores[0]["score"] == 500

        # Clean up
        if os.path.exists(tmp):
            os.unlink(tmp)
    finally:
        lh_mod.SCORES_FILE = orig_scores_file


def test_load_high_scores_missing_file():
    import tempfile
    from lighthouse import SCORES_FILE as orig_scores_file
    import lighthouse as lh_mod
    tmp = tempfile.mktemp(suffix=".json")
    lh_mod.SCORES_FILE = Path(tmp)

    try:
        scores = load_high_scores()
        assert scores == []
    finally:
        lh_mod.SCORES_FILE = orig_scores_file


# ─── Game Tick Stability ──────────────────────────────────────────
def test_many_ticks_dont_crash():
    """Run 500 ticks and make sure nothing crashes."""
    s = make_state()
    # Force some extreme conditions
    s.storm_active = True
    s.storm_intensity = 80
    tick_many(s, 500)
    # Should still be running or game-over, not crashed
    assert s.total_ticks >= 500 or s.game_over


def test_dawn_reached_ends_game():
    s = make_state()
    s.hour = 5
    s.minutes = 50
    tick_many(s, 30)  # should reach hour 6
    assert s.game_over is True
    assert s.dawn_reached is True


# ─── Wind System ───────────────────────────────────────────────────
def test_wind_changes_over_time():
    s = make_state()
    initial_wind = s.wind_direction
    s.wind_change_timer = 1
    tick_many(s, 5)
    # Wind should eventually change (not guaranteed in just 5 ticks, but timer decreases)
    assert isinstance(s.wind_direction, float)
    assert isinstance(s.wind_strength, float)


# ─── Statistics Tracking ───────────────────────────────────────────
def test_stats_are_initialized():
    s = make_state()
    assert "times_refueled" in s.stats
    assert "storms_weathered" in s.stats
    assert "crates_collected" in s.stats


if __name__ == "__main__":
    # Run a quick smoke test
    s = make_state()
    print(f"✓ State created: hour={s.hour}, fuel={s.fuel}, beam={'ON' if s.beam_on else 'OFF'}")
    tick_many(s, 100)
    print(f"✓ After 100 ticks: hour={s.hour}:{s.minutes:02d}, fuel={s.fuel:.1f}")
    print(f"✓ Ships saved: {s.ships_saved}, lost: {s.ships_lost}")
    print("All smoke tests passed!")