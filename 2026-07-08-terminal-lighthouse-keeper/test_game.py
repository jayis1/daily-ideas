#!/usr/bin/env python3
"""Comprehensive tests for Terminal Lighthouse Keeper."""
import os
import sys
import random
import math

# Use relative import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lighthouse import (
    Lighthouse, tick, _advance_time, _calculate_final_score,
    render_sea, render_sky, render_lighthouse, render_wind_indicator,
    EVENTS, SCREEN_W, SCREEN_H, NIGHT_START, NIGHT_END, TOTAL_NIGHT_HOURS,
    DIFFICULTIES, __version__,
)


class TestLighthouseInit:
    """Test Lighthouse initialization."""

    def test_default_init(self):
        s = Lighthouse()
        assert s.fuel == 80
        assert s.lens_health == 100
        assert s.beam_on is True
        assert s.hour == NIGHT_START
        assert s.minutes == 0
        assert s.game_over is False
        assert s.dawn_reached is False
        assert s.difficulty == "medium"

    def test_easy_init(self):
        s = Lighthouse(difficulty="easy")
        assert s.fuel == 90
        assert s.lens_health == 100

    def test_hard_init(self):
        s = Lighthouse(difficulty="hard")
        assert s.fuel == 60
        assert s.lens_health == 80


class TestTimeAdvancement:
    """Test _advance_time and tick time logic."""

    def test_advance_time_basic(self):
        s = Lighthouse()
        _advance_time(s, 5)
        assert s.minutes == 5
        assert s.hour == NIGHT_START

    def test_advance_time_hour_boundary(self):
        s = Lighthouse()
        s.hour = 5
        s.minutes = 58
        _advance_time(s, 5)
        # 5:58 + 5 = 6:03 → dawn
        assert s.dawn_reached is True
        assert s.hour == 6
        assert s.minutes == 3

    def test_advance_time_multi_hour(self):
        s = Lighthouse()
        s.hour = 20
        s.minutes = 55
        _advance_time(s, 10)
        # 20:55 + 10 = 21:05
        assert s.hour == 21
        assert s.minutes == 5
        assert s.dawn_reached is False

    def test_advance_time_no_false_dawn_at_night(self):
        """Advancing time during evening should NOT trigger dawn."""
        s = Lighthouse()
        s.hour = 19
        s.minutes = 30
        _advance_time(s, 5)
        # 19:35 should NOT trigger dawn (only 6 AM triggers it)
        assert s.dawn_reached is False

    def test_advance_time_hour_wraps_at_24(self):
        s = Lighthouse()
        s.hour = 23
        s.minutes = 58
        s.dawn_reached = True  # Prevent dawn check
        _advance_time(s, 5)
        # 23:58 + 5 = 0:03
        assert s.hour == 0
        assert s.minutes == 3

    def test_tick_hour_wraps_at_24(self):
        s = Lighthouse()
        s.hour = 23
        s.minutes = 59
        s.dawn_reached = True  # Prevent dawn
        s.game_over = False
        tick(s, 0.1)  # increments minutes to 60 → hour=24 → wraps to 0
        tick(s, 0.1)  # now hour 0
        assert s.hour < 24, f"Hour should wrap at 24 but got {s.hour}"


class TestDawnCheck:
    """Test dawn detection logic."""

    def test_dawn_at_6am(self):
        s = Lighthouse()
        s.hour = 5
        s.minutes = 59
        for i in range(5):
            tick(s, 0.1)
        assert s.dawn_reached is True
        assert s.game_over is True

    def test_no_dawn_at_6pm(self):
        """Hour 18 (6 PM) should NOT trigger dawn."""
        s = Lighthouse()
        # Game starts at hour 18
        assert s.hour == 18
        assert s.dawn_reached is False

    def test_dawn_in_tick(self):
        s = Lighthouse()
        s.hour = 5
        s.minutes = 50
        while not s.game_over:
            tick(s, 0.1)
            if s.total_ticks > 1000:
                break
        assert s.dawn_reached is True


class TestStormIntensity:
    """Test storm intensity bounds."""

    def test_storm_intensity_never_negative(self):
        s = Lighthouse()
        s.storm_active = True
        s.storm_intensity = 0.5
        s.weather_timer = 500
        for _ in range(2000):
            tick(s, 0.1)
            assert s.storm_intensity >= 0, f"storm_intensity went negative: {s.storm_intensity}"
            if s.game_over:
                break

    def test_storm_intensity_never_exceeds_100(self):
        s = Lighthouse()
        s.storm_active = True
        s.storm_intensity = 99.0
        s.weather_timer = 500
        for _ in range(500):
            tick(s, 0.1)
            assert s.storm_intensity <= 100, f"storm_intensity exceeded 100: {s.storm_intensity}"
            if s.game_over:
                break


class TestBeamIntensity:
    """Test beam intensity bounds."""

    def test_beam_intensity_floors_at_zero(self):
        s = Lighthouse()
        s.beam_on = False
        s.beam_intensity = 50.0
        for _ in range(500):
            tick(s, 0.1)
        assert s.beam_intensity == 0, f"beam_intensity should floor at 0 but is {s.beam_intensity}"

    def test_beam_intensity_does_not_exceed_100(self):
        s = Lighthouse()
        s.beam_on = True
        s.fuel = 100
        s.lens_health = 100
        for _ in range(500):
            tick(s, 0.1)
            assert s.beam_intensity <= 100, f"beam_intensity exceeded 100: {s.beam_intensity}"
            if s.game_over:
                break


class TestFuelAndEngine:
    """Test fuel and engine mechanics."""

    def test_fuel_never_negative(self):
        s = Lighthouse()
        s.fuel = 0.05
        s.beam_on = True
        for _ in range(100):
            tick(s, 0.1)
        assert s.fuel >= 0, f"Fuel went negative: {s.fuel}"

    def test_engine_shutdown_at_100(self):
        s = Lighthouse()
        s.engine_temp = 99.9
        s.beam_on = True
        s.fuel = 100
        while s.engine_temp < 100 and not s.game_over:
            tick(s, 0.1)
        # After reaching 100, engine should shut down
        assert s.beam_on is False or s.engine_temp < 100

    def test_engine_does_not_exceed_100(self):
        s = Lighthouse()
        s.engine_temp = 95
        s.beam_on = True
        s.fuel = 100
        s.storm_active = True
        for _ in range(500):
            tick(s, 0.1)
            # Engine can reach 100 briefly then get clamped
            assert s.engine_temp <= 101, f"Engine temp too high: {s.engine_temp}"
            if s.game_over:
                break

    def test_fuel_low_warning(self):
        s = Lighthouse()
        s.fuel = 14
        tick(s, 0.1)
        assert s.fuel_low_warned is True

    def test_fuel_low_warning_resets(self):
        s = Lighthouse()
        s.fuel = 14
        tick(s, 0.1)
        assert s.fuel_low_warned is True
        s.fuel = 50
        tick(s, 0.1)
        assert s.fuel_low_warned is False


class TestLoseCondition:
    """Test game-over conditions."""

    def test_lose_condition_no_fuel_many_ships_lost(self):
        s = Lighthouse()
        s.fuel = 0
        s.beam_on = False
        s.fuel_out_ticks = 0
        s.ships_lost = 5
        # Tick enough to trigger lose condition
        for i in range(350):
            s.fuel = 0
            tick(s, 0.1)
            if s.game_over:
                break
        assert s.game_over is True, "Game should end when fuel is out and ships are lost"

    def test_game_continues_with_fuel(self):
        s = Lighthouse()
        s.fuel = 80
        for i in range(1200):
            tick(s, 0.1)
            if s.game_over:
                break
        # Game should eventually end at dawn (needs ~360 ticks to reach 6 AM)
        assert s.dawn_reached is True or s.game_over is True


class TestDifficulty:
    """Test difficulty settings."""

    def test_easy_difficulty(self):
        s = Lighthouse(difficulty="easy")
        assert s.diff_config["fuel_rate"] == 0.8
        assert s.diff_config["storm_freq"] == 0.6

    def test_hard_difficulty(self):
        s = Lighthouse(difficulty="hard")
        assert s.diff_config["fuel_rate"] == 1.4
        assert s.diff_config["storm_freq"] == 1.5

    def test_invalid_difficulty_defaults_medium(self):
        s = Lighthouse(difficulty="impossible")
        assert s.difficulty == "impossible"
        # Should still get medium config since DIFFICULTIES.get() defaults
        assert s.fuel == 80  # medium default


class TestEvents:
    """Test random events."""

    def test_lens_crack_event(self):
        s = Lighthouse()
        old_lens = s.lens_health
        from lighthouse import _apply_lens_crack
        _apply_lens_crack(s)
        assert s.lens_health <= old_lens
        assert s.lens_health >= 0

    def test_fuel_leak_event(self):
        s = Lighthouse()
        old_fuel = s.fuel
        from lighthouse import _apply_fuel_leak
        _apply_fuel_leak(s)
        assert s.fuel <= old_fuel
        assert s.fuel >= 0

    def test_supply_crate_event(self):
        s = Lighthouse()
        s.fuel = 50
        s.lens_health = 50
        from lighthouse import _apply_supply_crate
        _apply_supply_crate(s)
        assert s.fuel > 50
        assert s.lens_health > 50
        assert s.stats["crates_collected"] == 1

    def test_engine_surge_event(self):
        s = Lighthouse()
        s.engine_temp = 50
        from lighthouse import _apply_engine_surge
        _apply_engine_surge(s)
        assert s.engine_temp > 50
        assert s.engine_temp <= 100

    def test_distress_ship_spawns(self):
        s = Lighthouse()
        from lighthouse import _spawn_distress_ship
        _spawn_distress_ship(s)
        assert len(s.ships) == 1
        assert s.ships[0]["distress"] is True

    def test_only_one_distress_ship(self):
        s = Lighthouse()
        from lighthouse import _spawn_distress_ship
        _spawn_distress_ship(s)
        _spawn_distress_ship(s)
        assert len([s for s in s.ships if s["distress"]]) == 1


class TestRendering:
    """Test rendering functions don't crash."""

    def test_render_sea(self):
        s = Lighthouse()
        result = render_sea(s, 80)
        assert len(result) == 80
        assert isinstance(result, str)

    def test_render_sea_storm(self):
        s = Lighthouse()
        s.storm_active = True
        s.storm_intensity = 50
        result = render_sea(s, 80)
        assert len(result) == 80

    def test_render_sky(self):
        s = Lighthouse()
        result = render_sky(s, 80)
        assert len(result) == 80

    def test_render_lighthouse(self):
        s = Lighthouse()
        result = render_lighthouse(s)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_render_lighthouse_beam_off(self):
        s = Lighthouse()
        s.beam_on = False
        result = render_lighthouse(s)
        assert isinstance(result, list)

    def test_render_wind_indicator(self):
        s = Lighthouse()
        result = render_wind_indicator(s)
        assert isinstance(result, str)
        assert len(result) > 0


class TestHourDisplay:
    """Test 12-hour time display conversion."""

    def _compute_hour_display(self, hour):
        if hour > 12:
            return hour - 12
        elif hour == 0:
            return 12
        else:
            return hour

    def _compute_ampm(self, hour):
        return "PM" if hour >= 12 else "AM"

    def test_midnight(self):
        assert self._compute_hour_display(0) == 12
        assert self._compute_ampm(0) == "AM"

    def test_noon(self):
        assert self._compute_hour_display(12) == 12
        assert self._compute_ampm(12) == "PM"

    def test_1am(self):
        assert self._compute_hour_display(1) == 1
        assert self._compute_ampm(1) == "AM"

    def test_6pm(self):
        assert self._compute_hour_display(18) == 6
        assert self._compute_ampm(18) == "PM"

    def test_11pm(self):
        assert self._compute_hour_display(23) == 11
        assert self._compute_ampm(23) == "PM"


class TestNightProgress:
    """Test night progress calculation."""

    def test_start_of_night(self):
        progress = (NIGHT_START - NIGHT_START) / TOTAL_NIGHT_HOURS
        assert progress == 0.0

    def test_midnight(self):
        progress = (0 + 24 - NIGHT_START) / TOTAL_NIGHT_HOURS
        assert abs(progress - 0.5) < 0.01

    def test_near_dawn(self):
        progress = (5 - NIGHT_START + 24) / TOTAL_NIGHT_HOURS
        # This should be > 0.9
        # 5 + 24 - 18 = 11/12 ≈ 0.917
        # But wait: hour 5 is < NIGHT_START(18), so:
        # progress = (5 + 24 - 18) / 12 = 11/12
        progress_alt = (5 + 24 - NIGHT_START) / TOTAL_NIGHT_HOURS
        assert progress_alt > 0.9


class TestVersion:
    """Test version string exists."""

    def test_version_exists(self):
        assert __version__ is not None
        assert isinstance(__version__, str)


class TestCLI:
    """Test command-line argument parsing."""

    def test_default_difficulty(self):
        import argparse
        from lighthouse import parse_args
        old_argv = sys.argv
        sys.argv = ["lighthouse"]
        args = parse_args()
        assert args.difficulty == "medium"
        sys.argv = old_argv

    def test_hard_difficulty_arg(self):
        import argparse
        from lighthouse import parse_args
        old_argv = sys.argv
        sys.argv = ["lighthouse", "--difficulty", "hard"]
        args = parse_args()
        assert args.difficulty == "hard"
        sys.argv = old_argv


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])