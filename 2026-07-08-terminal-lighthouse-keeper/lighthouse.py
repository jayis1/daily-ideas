#!/usr/bin/env python3
"""
Terminal Lighthouse Keeper — A meditative ASCII resource management game.

Maintain your lighthouse through the night. Keep the light burning, watch the
sea, respond to ships, and survive until dawn.

Usage:
    python3 lighthouse.py              # Start game (normal difficulty)
    python3 lighthouse.py --difficulty hard   # Hard mode
    python3 lighthouse.py --version
    python3 lighthouse.py --help
"""

import argparse
import curses
import json
import os
import random
import sys
import time
import math
from pathlib import Path
from typing import Dict, List, Optional

# ─── Version ──────────────────────────────────────────────────────────
__version__ = "1.1.0"

# ─── Constants ────────────────────────────────────────────────────────
SCREEN_W = 80
SCREEN_H = 24

HOUR_LENGTH = 15  # seconds per game hour (affects overall game speed)
NIGHT_START = 18  # 6 PM
NIGHT_END = 6      # 6 AM
TOTAL_NIGHT_HOURS = 12

# Difficulty presets: (fuel_start, lens_start, storm_freq_mult, event_freq_mult, fuel_rate_mult, label)
DIFFICULTIES = {
    "easy":   {"fuel": 90, "lens": 100, "storm_freq": 0.6, "event_freq": 0.6,
               "fuel_rate": 0.8, "engine_heat": 0.8, "label": "Easy"},
    "medium": {"fuel": 80, "lens": 100, "storm_freq": 1.0, "event_freq": 1.0,
               "fuel_rate": 1.0, "engine_heat": 1.0, "label": "Normal"},
    "hard":   {"fuel": 60, "lens": 80,  "storm_freq": 1.5, "event_freq": 1.5,
               "fuel_rate": 1.4, "engine_heat": 1.3, "label": "Hard"},
}

# High score file
SCORES_FILE = Path.home() / ".lighthouse_scores.json"

# ─── Game State ────────────────────────────────────────────────────────
class Lighthouse:
    """Core game state for the lighthouse keeper simulation."""

    def __init__(self, difficulty: str = "medium"):
        diff = DIFFICULTIES.get(difficulty, DIFFICULTIES["medium"])
        self.difficulty = difficulty
        self.diff_config = diff

        # Resources (0–100 scale)
        self.fuel = diff["fuel"]
        self.lens_health = diff["lens"]
        self.beam_on = True
        self.beam_intensity = self.fuel * 0.8
        self.engine_temp = 50          # 0–100; overheats above 90, shuts down at 100

        # Efficiency mode: reduces fuel consumption by 40% but caps beam at 60%
        self.efficiency_mode = False

        # Wind system: affects ship speed and direction
        self.wind_direction = random.uniform(-1, 1)  # -1=left, 1=right
        self.wind_strength = random.uniform(0.3, 0.8)
        self.wind_change_timer = random.randint(100, 300)

        # Scoring and ship tracking
        self.ship_signals = 0
        self.ships_saved = 0
        self.ships_lost = 0
        self.score = 0

        # Time: starts at 6 PM (hour 18)
        self.hour = NIGHT_START
        self.minutes = 0

        # Weather state
        self.weather = "clear"
        self.weather_timer = random.randint(80, 200)
        self.storm_active = False
        self.storm_intensity = 0.0  # 0–100

        # Event and message system
        self.log: List[str] = []
        self.current_event = None
        self.event_timer = 0
        self.flash_timer = 0
        self.flash_message = ""

        # Warnings and flags
        self.fuel_low_warned = False
        self.engine_overheated = False

        # Rendering state
        self.wave_offset = 0.0
        self.total_ticks = 0

        # Ship management
        self.ships: List[Dict] = []
        self.ship_spawn_timer = random.randint(30, 80)

        # Game flow
        self.game_over = False
        self.game_over_reason = ""
        self.dawn_reached = False
        self.paused = False
        self.actions_taken = 0

        # Statistics for end-game summary
        self.stats = {
            "times_refueled": 0,
            "times_lens_fixed": 0,
            "times_cooled": 0,
            "times_beam_toggled": 0,
            "times_efficiency_toggled": 0,
            "storms_weathered": 0,
            "crates_collected": 0,
            "longest_low_fuel_streak": 0,
            "current_low_fuel_streak": 0,
        }


# ─── Wave / Sea Rendering ─────────────────────────────────────────────
WAVE_CHARS = "≈∿≋~"

def render_sea(state: Lighthouse, width: int) -> str:
    """Generate an animated sea line influenced by wind and weather."""
    line = []
    t = state.total_ticks * 0.05
    storm_factor = state.storm_intensity / 100.0
    wind_bias = state.wind_direction * state.wind_strength * 0.3

    for i in range(width):
        wave = math.sin(i * 0.15 + t + wind_bias * i * 0.01) * (1 + storm_factor * 2)
        wave += math.sin(i * 0.07 - t * 0.7) * 0.5
        wave += math.cos(i * 0.22 + t * 1.3) * 0.3 * (1 + storm_factor)

        if storm_factor > 0.3 and random.random() < storm_factor * 0.1:
            line.append("▓" if storm_factor > 0.6 else "▒")
        elif wave > 1.2 + storm_factor:
            line.append("≈")
        elif wave < -0.8 - storm_factor * 0.5:
            line.append("∿")
        elif abs(wave) < 0.3:
            line.append("≋")
        else:
            line.append(random.choice("~∼"))
    return "".join(line)


def render_sky(state: Lighthouse, width: int) -> str:
    """Render sky with stars, moon, clouds, and dawn glow."""
    hour = state.hour + state.minutes / 60.0

    # Moon moves from left to right across the sky during the night
    moon_progress = (hour - NIGHT_START) / TOTAL_NIGHT_HOURS
    moon_x = int(width * 0.2 + width * 0.6 * moon_progress)

    line = [" "] * width

    # Deterministic star field (same stars every frame, some twinkle)
    random.seed(42)
    for _ in range(30):
        sx = random.randint(0, width - 1)
        twinkle = random.random()
        if (state.total_ticks + int(twinkle * 100)) % 3 < 2:
            line[sx] = random.choice("·✦⋆")
    random.seed()  # restore randomness

    # Storm clouds obscure the sky
    if state.storm_active:
        for i in range(width):
            if random.random() < state.storm_intensity / 150:
                line[i] = random.choice("▒░▓")

    # Moon with halo
    if 0 <= moon_x < width:
        line[moon_x] = "☽"
        if moon_x > 0:
            line[moon_x - 1] = "░"
        if moon_x < width - 1:
            line[moon_x + 1] = "░"

    # Dawn glow in the final hour
    if state.hour >= 5:
        progress = (state.hour - 5 + state.minutes / 60.0) / 1.0
        if progress > 0:
            for i in range(width):
                if random.random() < progress * 0.1:
                    line[i] = random.choice("░▒")

    return "".join(line)


def render_lighthouse(state: Lighthouse) -> List[str]:
    """Return the lighthouse ASCII art, beam state depends on fuel and mode."""
    lines = []

    beam_char = "◈" if state.beam_on and state.fuel > 0 else "·"
    intensity = state.beam_intensity / 100.0

    # Efficiency mode indicator
    mode_tag = " (eco)" if state.efficiency_mode and state.beam_on and state.fuel > 0 else ""

    light_state = beam_char if state.beam_on and state.fuel > 0 else "○"
    light_color_indicator = "◆" if state.beam_on and state.fuel > 0 else "◇"

    lines.append(f"         {light_color_indicator}          ")
    lines.append(f"        ╔╩╗          ")

    if state.beam_on and state.fuel > 0:
        beam_width = max(1, int(intensity * 5))
        beam = "═" * beam_width
        lines.append(f"    {beam}╔╬╗{beam}      ")
        # Right beam extends further — longer when efficiency mode is off
        max_reach = 12 if state.efficiency_mode else 20
        r_beam = "━" * min(max_reach, int(intensity * max_reach))
        lines.append(f"      ╔╬╝ {r_beam}")
    else:
        lines.append(f"        ╠╣╗          ")
        lines.append(f"        ╚╬╝          ")

    lines.append(f"        ╔╩╗          ")
    lines.append(f"        ║{light_state}║          ")
    lines.append(f"        ╔╩╗          ")
    lines.append(f"        ║▓║          ")
    lines.append(f"       ╔╬╬╬╗         ")
    lines.append(f"       ║▓▓▓║         ")
    lines.append(f"       ║▓▓▓║         ")
    lines.append(f"      ╔╬╬╬╬╬╗        ")
    lines.append(f"      ║▓▓▓▓▓║        ")

    # Door
    lines.append(f"      ║▓▓▓▓▓║        ")
    lines.append(f"     ╔╬╬╬╬╬╬╬╗       ")
    lines.append(f"     ║▓▓█▓▓▓▓║       ")
    lines.append(f"     ╚╬╬╬╬╬╬╬╝       ")
    lines.append(f"    ▓▓▓▓▓▓▓▓▓▓▓      ")

    return lines


# ─── Wind Rendering ───────────────────────────────────────────────────
def render_wind_indicator(state: Lighthouse) -> str:
    """Return a short wind direction string for the HUD."""
    direction = "→" if state.wind_direction > 0.2 else "←" if state.wind_direction < -0.2 else "·"
    strength = "strong" if state.wind_strength > 0.6 else "light" if state.wind_strength < 0.4 else "moderate"
    return f"{direction} {strength}"


# ─── Events ───────────────────────────────────────────────────────────
def _spawn_distress_ship(s: Lighthouse) -> None:
    """Spawn a new distress ship if no other distress ship exists."""
    for ship in s.ships:
        if ship["distress"]:
            return  # Only one distress ship at a time
    s.ships.append({
        "x": random.choice([5, 10, 15]),
        "distress": True,
        "saved": False,
        "timer": 20,
        "sea_y": 0,
        "direction": random.choice([-1, 1]),
    })


def _apply_lens_crack(s: Lighthouse) -> None:
    """Damage the lens by a random amount."""
    setattr(s, 'lens_health', max(0, s.lens_health - random.randint(10, 25)))


def _apply_fuel_leak(s: Lighthouse) -> None:
    """Lose some fuel to a leak."""
    setattr(s, 'fuel', max(0, s.fuel - random.randint(5, 15)))


def _apply_supply_crate(s: Lighthouse) -> None:
    """A supply crate washes ashore, restoring fuel and lens."""
    setattr(s, 'fuel', min(100, s.fuel + random.randint(10, 25)))
    setattr(s, 'lens_health', min(100, s.lens_health + random.randint(5, 15)))
    s.stats["crates_collected"] += 1


def _apply_engine_surge(s: Lighthouse) -> None:
    """Spike the engine temperature."""
    setattr(s, 'engine_temp', min(100, s.engine_temp + random.randint(15, 30)))


def _apply_noop(s: Lighthouse) -> None:
    """No-op event effect (cosmetic events like seagulls)."""
    pass


EVENTS = [
    {
        "name": "lens_crack",
        "message": "⚠ A crack appears in the lens!",
        "duration": 0,
        "effect": _apply_lens_crack,
    },
    {
        "name": "fuel_leak",
        "message": "⚠ Fuel leak detected!",
        "duration": 0,
        "effect": _apply_fuel_leak,
    },
    {
        "name": "supply_crate",
        "message": "📦 A supply crate washes ashore!",
        "duration": 0,
        "effect": _apply_supply_crate,
    },
    {
        "name": "engine_surge",
        "message": "⚠ Engine temperature surge!",
        "duration": 0,
        "effect": _apply_engine_surge,
    },
    {
        "name": "seagull_visit",
        "message": "🐦 A seagull lands on the railing.",
        "duration": 3,
        "effect": _apply_noop,
    },
    {
        "name": "ship_distress",
        "message": "🚨 A ship is signaling distress!",
        "duration": 5,
        "effect": _spawn_distress_ship,
    },
]


# ─── Game Logic ───────────────────────────────────────────────────────
def _advance_time(state: Lighthouse, minutes: int) -> None:
    """Advance game time by a number of minutes, checking for dawn."""
    state.minutes += minutes
    while state.minutes >= 60:
        state.minutes -= 60
        state.hour += 1

        # Wrap hour past midnight
        if state.hour >= 24:
            state.hour -= 24

        # Hourly log entry
        state.log.append(f"Hour {state.hour:02d}:00")
        if len(state.log) > 50:
            state.log = state.log[-30:]

    # Dawn check — only trigger between NIGHT_END (6 AM) and NIGHT_START (6 PM)
    if state.hour >= NIGHT_END and state.hour < NIGHT_START and not state.dawn_reached:
        state.dawn_reached = True
        state.game_over = True
        state.game_over_reason = "Dawn has broken! You survived the night."
        _calculate_final_score(state)


def _calculate_final_score(state: Lighthouse) -> None:
    """Tally up the final score at game end."""
    state.score += state.ships_saved * 100
    state.score += int(state.fuel * 5)
    state.score += int(state.lens_health * 3)
    state.score += max(0, int((100 - state.engine_temp) * 2))
    # Bonus for efficiency mode usage
    if state.stats["times_efficiency_toggled"] > 0:
        state.score += 50  # small bonus for using a harder mechanic
    # Difficulty multiplier
    diff_mult = {"easy": 0.8, "medium": 1.0, "hard": 1.5}
    state.score = int(state.score * diff_mult.get(state.difficulty, 1.0))


def tick(state: Lighthouse, dt: float) -> None:
    """Advance game state by one tick (~100ms)."""
    if state.game_over or state.paused:
        return

    state.total_ticks += 1
    state.wave_offset += dt

    # ── Time advancement ──────────────────────────────────────────
    state.minutes += 1
    if state.minutes >= 60:
        state.minutes = 0
        state.hour += 1

        # Wrap hour past midnight
        if state.hour >= 24:
            state.hour -= 24

        # Hourly log
        state.log.append(f"Hour {state.hour:02d}:00")
        if len(state.log) > 50:
            state.log = state.log[-30:]

    # Dawn check — game ends at 6 AM
    if state.hour >= NIGHT_END and state.hour < NIGHT_START and not state.dawn_reached:
        state.dawn_reached = True
        state.game_over = True
        state.game_over_reason = "Dawn has broken! You survived the night."
        _calculate_final_score(state)
        return

    # ── Fuel consumption ──────────────────────────────────────────
    if state.beam_on:
        fuel_rate = 0.08 * (state.beam_intensity / 80.0) * state.diff_config["fuel_rate"]
        if state.efficiency_mode:
            fuel_rate *= 0.6  # 40% less fuel in efficiency mode
        if state.storm_active:
            fuel_rate *= 1.3
        state.fuel = max(0, state.fuel - fuel_rate)

    # Fuel ran out → beam goes dark
    if state.fuel <= 0 and state.beam_on:
        state.beam_on = False
        state.efficiency_mode = False
        state.flash_message = "THE LIGHT HAS GONE OUT!"
        state.flash_timer = 10

    # Low fuel warning
    if state.fuel < 15 and not state.fuel_low_warned:
        state.fuel_low_warned = True
        state.flash_message = "⚠ Fuel running low!"
        state.flash_timer = 8
        state.stats["current_low_fuel_streak"] = 0

    if state.fuel < 15:
        state.stats["current_low_fuel_streak"] += 1
        state.stats["longest_low_fuel_streak"] = max(
            state.stats["longest_low_fuel_streak"],
            state.stats["current_low_fuel_streak"],
        )
    else:
        state.fuel_low_warned = False
        state.stats["current_low_fuel_streak"] = 0

    # ── Engine temperature ────────────────────────────────────────
    heat_rate = state.diff_config["engine_heat"]
    if state.beam_on:
        state.engine_temp += 0.03 * heat_rate
        if state.storm_active:
            state.engine_temp += 0.02 * heat_rate
    else:
        state.engine_temp = max(30, state.engine_temp - 0.08)

    if state.engine_temp > 90 and not state.engine_overheated:
        state.engine_overheated = True
        state.flash_message = "⚠ ENGINE OVERHEATING!"
        state.flash_timer = 8
    elif state.engine_temp <= 80:
        state.engine_overheated = False

    # Engine shutdown on overheat
    if state.engine_temp >= 100:
        state.beam_on = False
        state.efficiency_mode = False
        state.engine_temp = 95
        state.flash_message = "ENGINE SHUTDOWN - OVERHEATED"
        state.flash_timer = 12

    # ── Beam intensity ────────────────────────────────────────────
    if state.beam_on and state.fuel > 0:
        max_intensity = 60 if state.efficiency_mode else 100
        target = min(max_intensity, state.fuel * 1.2) * (state.lens_health / 100.0)
        state.beam_intensity += (target - state.beam_intensity) * 0.05
    else:
        state.beam_intensity *= 0.9
        if state.beam_intensity < 0.1:
            state.beam_intensity = 0

    # ── Weather system ────────────────────────────────────────────
    state.weather_timer -= 1
    if state.weather_timer <= 0:
        r = random.random()
        storm_freq = state.diff_config["storm_freq"]
        if state.storm_active:
            if r < 0.3:
                state.weather = "clear"
                state.storm_active = False
                state.storm_intensity = max(0, state.storm_intensity - 20)
                state.weather_timer = random.randint(80, 200)
            elif r < 0.7:
                state.weather = "rain"
                state.storm_intensity = max(0, state.storm_intensity - 5)
                state.weather_timer = random.randint(40, 100)
            else:
                state.weather = "storm"
                state.storm_intensity = min(100, state.storm_intensity + random.randint(5, 15))
                state.weather_timer = random.randint(60, 150)
        else:
            if r < 0.5:
                state.weather = "clear"
                state.weather_timer = random.randint(80, 250)
            elif r < 0.8:
                state.weather = "rain"
                state.weather_timer = random.randint(40, 120)
            else:
                state.weather = "storm"
                state.storm_active = True
                state.storm_intensity = random.randint(20, 50)
                state.weather_timer = random.randint(50, 150)
                state.flash_message = "⛈ A storm approaches!"
                state.flash_timer = 10
                state.stats["storms_weathered"] += 1

    # Storm effects on lens
    if state.storm_active:
        state.storm_intensity = max(0, min(100, state.storm_intensity + random.uniform(-0.5, 1.0)))
        state.lens_health = max(0, state.lens_health - 0.01 * (state.storm_intensity / 100))

    # ── Wind system ───────────────────────────────────────────────
    state.wind_change_timer -= 1
    if state.wind_change_timer <= 0:
        state.wind_direction = random.uniform(-1, 1)
        state.wind_strength = random.uniform(0.2, 0.9)
        state.wind_change_timer = random.randint(100, 300)

    # ── Ship spawning ────────────────────────────────────────────
    state.ship_spawn_timer -= 1
    if state.ship_spawn_timer <= 0:
        state.ship_spawn_timer = random.randint(60, 180)
        if random.random() < 0.4:
            direction = 1 if random.random() < 0.5 else -1
            state.ships.append({
                "x": -5 if direction > 0 else SCREEN_W + 5,
                "distress": False,
                "saved": False,
                "timer": random.randint(60, 150),
                "direction": direction,
            })

    # ── Update ships ─────────────────────────────────────────────
    ships_to_remove = []
    for i, ship in enumerate(state.ships):
        if not ship.get("distress", False):
            # Wind affects ship speed
            wind_boost = state.wind_direction * state.wind_strength * 0.3
            speed = (0.5 if state.storm_active else 1.0) + wind_boost * ship.get("direction", 1)
            ship["x"] += ship.get("direction", 1) * max(0.2, speed)
            ship["timer"] -= 1
            if ship["timer"] <= 0 or ship["x"] < -20 or ship["x"] > SCREEN_W + 20:
                # Ship passed — was it guided?
                if state.beam_on and state.beam_intensity > 30:
                    state.ships_saved += 1
                    state.score += 50
                else:
                    if random.random() < 0.5:
                        state.ships_lost += 1
                        state.log.append("A ship was lost in the darkness...")
                ships_to_remove.append(i)
        else:
            # Distress ship countdown
            ship["timer"] -= 1
            if ship["timer"] <= 0:
                state.ships_lost += 1
                state.log.append("A distressed ship could not reach safety...")
                state.flash_message = "A ship has been lost!"
                state.flash_timer = 10
                ships_to_remove.append(i)

    for i in sorted(ships_to_remove, reverse=True):
        if i < len(state.ships):
            state.ships.pop(i)

    # ── Random events ─────────────────────────────────────────────
    state.event_timer -= 1
    if state.event_timer <= 0 and state.current_event:
        state.current_event = None

    event_freq = state.diff_config["event_freq"]
    if state.event_timer <= 0 and random.random() < 0.008 * event_freq:
        event = random.choice(EVENTS)
        state.current_event = event
        state.event_timer = event.get("duration", 0) * 10
        event["effect"](state)
        state.log.append(event["message"])

    # ── Flash timer ───────────────────────────────────────────────
    if state.flash_timer > 0:
        state.flash_timer -= 1

    # ── Extra ship losses when the light is out ───────────────────
    if state.fuel <= 0 and not state.beam_on:
        if random.random() < 0.005:
            state.ships_lost += 1
            state.log.append("A ship was lost — no light to guide it!")


# ─── High Scores ──────────────────────────────────────────────────────
def load_high_scores() -> List[Dict]:
    """Load high scores from disk, return empty list if file missing."""
    try:
        if SCORES_FILE.exists():
            with open(SCORES_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_high_score(score: int, difficulty: str, ships_saved: int, ships_lost: int) -> int:
    """Save a new high score entry. Returns the rank (1-based)."""
    scores = load_high_scores()
    entry = {
        "score": score,
        "difficulty": difficulty,
        "ships_saved": ships_saved,
        "ships_lost": ships_lost,
        "date": time.strftime("%Y-%m-%d %H:%M"),
    }
    scores.append(entry)
    scores.sort(key=lambda e: e["score"], reverse=True)
    scores = scores[:10]  # keep top 10
    try:
        with open(SCORES_FILE, "w") as f:
            json.dump(scores, f, indent=2)
    except OSError:
        pass
    # Find rank
    for i, s in enumerate(scores):
        if s is entry:
            return i + 1
    return len(scores)


# ─── Rendering ────────────────────────────────────────────────────────
def render(stdscr, state: Lighthouse) -> None:
    """Full screen render of the game."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()

    # Safety check for very small terminals
    if h < 10 or w < 30:
        try:
            stdscr.addstr(0, 0, "Terminal too small! Need >= 30x10", curses.color_pair(1))
            stdscr.refresh()
        except curses.error:
            pass
        return

    # Create buffer for the scene layer
    buffer = [[" "] * SCREEN_W for _ in range(SCREEN_H)]
    colors = [[0] * SCREEN_W for _ in range(SCREEN_H)]

    # Sky (rows 0–3)
    sky_line = render_sky(state, SCREEN_W)
    for i, ch in enumerate(sky_line[:SCREEN_W]):
        buffer[0][i] = ch
        colors[0][i] = 2  # green for sky elements

    # Sea (rows 4–6)
    for row in range(4, 7):
        sea = render_sea(state, SCREEN_W)
        for i, ch in enumerate(sea[:SCREEN_W]):
            buffer[row][i] = ch
            colors[row][i] = 4  # blue for sea

    # Lighthouse (right side of screen)
    lighthouse = render_lighthouse(state)
    lh_x = 55
    for row_offset, line in enumerate(lighthouse):
        y = 5 + row_offset
        if y < SCREEN_H:
            for i, ch in enumerate(line):
                x = lh_x + i
                if 0 <= x < SCREEN_W:
                    buffer[y][x] = ch
                    colors[y][x] = 3  # yellow for lighthouse

    # Place ships on sea
    for ship in state.ships:
        sx = int(ship["x"])
        sy = 5 if ship["distress"] else (4 + random.randint(0, 1) if state.total_ticks % 10 == 0 else 5)
        sprite = "SOS!⛵" if ship["distress"] else "⛵"
        if ship.get("saved"):
            sprite = "⛵✓"
        for i, ch in enumerate(sprite):
            if 0 <= sx + i < SCREEN_W and 0 <= sy < SCREEN_H:
                buffer[sy][sx + i] = ch
                colors[sy][sx + i] = 1 if ship["distress"] else 6

    # Rain / storm particles
    if state.storm_active:
        for y in range(SCREEN_H):
            for x in range(SCREEN_W):
                if random.random() < state.storm_intensity / 300:
                    buffer[y][x] = random.choice("·⁘⁖")
                    colors[y][x] = 4

    # Draw scene buffer to screen
    try:
        for y in range(min(SCREEN_H, h)):
            for x in range(min(SCREEN_W, w)):
                ch = buffer[y][x]
                if ch != " ":
                    color_pair = colors[y][x]
                    attr = curses.color_pair(color_pair) if curses.has_colors() else 0
                    try:
                        stdscr.addch(y, x, ord(ch), attr)
                    except curses.error:
                        pass
    except curses.error:
        pass

    # ── HUD Panel ─────────────────────────────────────────────────
    panel_y = 8
    panel_x = 2

    # 12-hour time display
    ampm = "PM" if state.hour >= 12 else "AM"
    if state.hour > 12:
        hour_display = state.hour - 12
    elif state.hour == 0:
        hour_display = 12
    else:
        hour_display = state.hour

    time_str = f"{hour_display}:{state.minutes:02d} {ampm}"

    # Night progress bar
    if state.hour >= NIGHT_START:
        night_progress = (state.hour - NIGHT_START + state.minutes / 60.0) / TOTAL_NIGHT_HOURS
    elif state.hour < NIGHT_END:
        night_progress = (state.hour + 24 - NIGHT_START + state.minutes / 60.0) / TOTAL_NIGHT_HOURS
    else:
        night_progress = 1.0

    progress_bar_len = 20
    filled = int(night_progress * progress_bar_len)
    progress_bar = "█" * filled + "░" * (progress_bar_len - filled)

    # Status indicators
    beam_status = "ON " if state.beam_on else "OFF"
    eco_status = " [eco]" if state.efficiency_mode else ""
    weather_icon = {"clear": "☀", "rain": "🌧", "storm": "⛈"}.get(state.weather, "?")
    wind_str = render_wind_indicator(state)

    # Resource bars
    bar_len = 20
    fuel_filled = int((state.fuel / 100) * bar_len)
    fuel_bar = "█" * fuel_filled + "░" * (bar_len - fuel_filled)

    lens_filled = int((state.lens_health / 100) * bar_len)
    lens_bar = "█" * lens_filled + "░" * (bar_len - lens_filled)

    temp_filled = int((state.engine_temp / 100) * bar_len)
    temp_bar = "█" * temp_filled + "░" * (bar_len - temp_filled)

    int_filled = int((state.beam_intensity / 100) * bar_len)
    int_bar = "█" * int_filled + "░" * (bar_len - int_filled)

    diff_label = state.diff_config["label"]

    hud_lines = [
        f"╔══════════════════════════════╗",
        f"║  🏠 THE LIGHTHOUSE KEEPER   ║",
        f"║  Time: {time_str:>8s}  [{diff_label:>6s}]  ║",
        f"║  Night: [{progress_bar}]   ║",
        f"╠══════════════════════════════╣",
        f"║  🔦 Beam: {beam_status}{eco_status:<6s}          ║",
        f"║  ⛽ Fuel:  [{fuel_bar}]   ║",
        f"║  🔍 Lens:  [{lens_bar}]   ║",
        f"║  🌡 Temp:  [{temp_bar}]   ║",
        f"║  ☆ Intens: [{int_bar}]   ║",
        f"╠══════════════════════════════╣",
        f"║  Weather: {weather_icon} {state.weather:<6s}           ║",
        f"║  Wind: {wind_str:<12s}          ║",
        f"║  Ships saved: {state.ships_saved:<3d}           ║",
        f"║  Ships lost:  {state.ships_lost:<3d}           ║",
        f"║  Score: {state.score:<6d}              ║",
        f"╚══════════════════════════════╝",
    ]

    for i, line in enumerate(hud_lines):
        if panel_y + i < h and panel_x + len(line) < w:
            try:
                stdscr.addstr(panel_y + i, panel_x, line, curses.color_pair(7))
            except curses.error:
                pass

    # ── Action Help ────────────────────────────────────────────────
    help_y = SCREEN_H - 5
    pause_tag = "PAUSED" if state.paused else ""
    help_lines = [
        f"[B] Toggle Beam  [R] Refuel  [F] Fix Lens  [E] Eco Mode",
        f"[C] Cool Engine  [S] Signal Ship  [SPACE] Pause  [Q] Quit",
        f"{'⏸ PAUSED — press SPACE to resume' if state.paused else ''}",
    ]

    for i, line in enumerate(help_lines):
        if help_y + i < h and line:
            try:
                attr = curses.color_pair(1) | curses.A_BOLD if state.paused and i == 2 else curses.color_pair(6) | curses.A_BOLD
                stdscr.addstr(help_y + i, 2, line, attr)
            except curses.error:
                pass

    # ── Event Message ─────────────────────────────────────────────
    if state.current_event and state.event_timer > 0:
        msg = state.current_event["message"]
        msg_y = 7
        try:
            stdscr.addstr(msg_y, (w - len(msg)) // 2, msg,
                          curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass

    # ── Flash Message ─────────────────────────────────────────────
    if state.flash_timer > 0:
        msg = state.flash_message
        flash_y = 3
        try:
            stdscr.addstr(flash_y, max(0, (w - len(msg)) // 2), msg,
                          curses.color_pair(1) | curses.A_BOLD | curses.A_BLINK)
        except curses.error:
            pass

    # ── Game Over Overlay ─────────────────────────────────────────
    if state.game_over:
        overlay_lines = [
            "╔══════════════════════════════════════╗",
            f"║  {'DAWN BREAKS!' if state.dawn_reached else 'GAME OVER':^38s}║",
            "╠══════════════════════════════════════╣",
            f"║  Ships saved:  {state.ships_saved:>3d}                    ║",
            f"║  Ships lost:   {state.ships_lost:>3d}                    ║",
            f"║  Final score:  {state.score:>6d}                  ║",
            "║                                      ║",
            "║  Press [R] to restart or [Q] quit    ║",
            "╚══════════════════════════════════════╝",
        ]
        oy = max(0, (h - len(overlay_lines)) // 2)
        for i, line in enumerate(overlay_lines):
            ox = max(0, (w - len(line)) // 2)
            if oy + i < h:
                try:
                    color = (curses.color_pair(2) | curses.A_BOLD
                             if state.dawn_reached
                             else curses.color_pair(1) | curses.A_BOLD)
                    stdscr.addstr(oy + i, ox, line, color)
                except curses.error:
                    pass

    # ── Log (bottom line) ─────────────────────────────────────────
    log_y = SCREEN_H - 2
    recent_logs = state.log[-1:] if state.log else []
    if recent_logs and not state.game_over:
        try:
            stdscr.addstr(log_y, 2, recent_logs[-1][:60], curses.color_pair(3))
        except curses.error:
            pass

    stdscr.refresh()


# ─── Main Game Loop ───────────────────────────────────────────────────
def main(stdscr, difficulty: str = "medium") -> None:
    """Main game loop: handle input, tick, render."""

    # ── Color setup ───────────────────────────────────────────────
    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLACK)

    curses.curs_set(0)  # hide cursor
    stdscr.nodelay(1)   # non-blocking input
    stdscr.timeout(100)  # refresh every 100ms

    state = Lighthouse(difficulty=difficulty)
    last_time = time.time()

    while True:
        # ── Handle input ──────────────────────────────────────
        key = stdscr.getch()

        if state.game_over:
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('r') or key == ord('R'):
                state = Lighthouse(difficulty=difficulty)
                last_time = time.time()
                continue
        else:
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord(' '):
                # Toggle pause
                state.paused = not state.paused
                if state.paused:
                    state.log.append("⏸ Game paused")
                else:
                    state.log.append("▶ Game resumed")
                    last_time = time.time()  # prevent time jump
            elif state.paused:
                pass  # ignore all other keys while paused
            elif key == ord('b') or key == ord('B'):
                if state.fuel > 0 and state.engine_temp < 100:
                    state.beam_on = not state.beam_on
                    if not state.beam_on:
                        state.efficiency_mode = False
                    state.actions_taken += 1
                    state.stats["times_beam_toggled"] += 1
            elif key == ord('e') or key == ord('E'):
                # Toggle efficiency mode (only when beam is on)
                if state.beam_on and state.fuel > 0:
                    state.efficiency_mode = not state.efficiency_mode
                    state.log.append(
                        f"Eco mode {'ON — 40% less fuel, beam capped at 60%' if state.efficiency_mode else 'OFF — full power'}"
                    )
                    state.stats["times_efficiency_toggled"] += 1
                else:
                    state.log.append("Can't toggle eco — beam is off!")
            elif key == ord('r') or key == ord('R'):
                # Refuel — costs 5 game-minutes, restores 15–30% fuel
                fuel_gain = random.randint(15, 30)
                state.fuel = min(100, state.fuel + fuel_gain)
                state.log.append(f"Refueled +{fuel_gain}%")
                state.actions_taken += 1
                state.stats["times_refueled"] += 1
                _advance_time(state, 5)
                if state.game_over:
                    continue
            elif key == ord('f') or key == ord('F'):
                # Fix lens — costs 3 game-minutes, restores 10–25% lens health
                lens_fix = random.randint(10, 25)
                state.lens_health = min(100, state.lens_health + lens_fix)
                state.log.append(f"Repaired lens +{lens_fix}%")
                state.actions_taken += 1
                state.stats["times_lens_fixed"] += 1
                _advance_time(state, 3)
                if state.game_over:
                    continue
            elif key == ord('c') or key == ord('C'):
                # Cool engine — costs 2 game-minutes, reduces temp by 15–30°
                cool_amount = random.randint(15, 30)
                state.engine_temp = max(30, state.engine_temp - cool_amount)
                state.log.append(f"Cooled engine -{cool_amount}°")
                state.actions_taken += 1
                state.stats["times_cooled"] += 1
                _advance_time(state, 2)
                if state.game_over:
                    continue
            elif key == ord('s') or key == ord('S'):
                # Signal a distress ship
                for ship in state.ships:
                    if ship["distress"] and not ship.get("saved"):
                        ship["saved"] = True
                        ship["distress"] = False
                        state.ships_saved += 1
                        state.score += 200
                        state.log.append("Ship rescued! +200 points")
                        state.flash_message = "🚢 Ship rescued!"
                        state.flash_timer = 8
                        state.actions_taken += 1
                        break
                else:
                    state.log.append("No ships to signal.")

        # ── Update game ───────────────────────────────────────
        if not state.game_over and not state.paused:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            tick(state, dt)
        elif state.paused:
            last_time = time.time()  # keep time fresh so no jump on unpause

        # ── Render ─────────────────────────────────────────────
        render(stdscr, state)

    # ── Save high score on exit ───────────────────────────────
    if state.dawn_reached or state.game_over:
        try:
            save_high_score(state.score, state.difficulty, state.ships_saved, state.ships_lost)
        except Exception:
            pass  # best-effort score saving


def run(difficulty: str = "medium") -> None:
    """Entry point: launch the curses game."""
    try:
        curses.wrapper(lambda stdscr: main(stdscr, difficulty))
    except KeyboardInterrupt:
        pass


# ─── CLI ──────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="lighthouse",
        description="Terminal Lighthouse Keeper — A meditative ASCII resource management game. "
                    "Keep the light burning through the night!",
        epilog="Guide ships to safety, manage your fuel and engine, and survive until dawn.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--difficulty", choices=["easy", "medium", "hard"], default="medium",
        help="Game difficulty: easy (more fuel, fewer storms), medium (default), hard (less fuel, more storms).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(difficulty=args.difficulty)