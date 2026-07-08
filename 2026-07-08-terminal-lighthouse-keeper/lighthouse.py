#!/usr/bin/env python3
"""
Terminal Lighthouse Keeper — A meditative ASCII resource management game.
Maintain your lighthouse through the night. Keep the light burning, watch the sea,
respond to ships, and survive until dawn.
"""

import curses
import random
import time
import math
import sys

# ─── Constants ────────────────────────────────────────────────────────
SCREEN_W = 80
SCREEN_H = 24

HOUR_LENGTH = 15  # seconds per game hour
NIGHT_START = 18  # 6 PM
NIGHT_END = 6      # 6 AM
TOTAL_NIGHT_HOURS = 12

# ─── Game State ───────────────────────────────────────────────────────
class Lighthouse:
    def __init__(self):
        self.fuel = 80          # 0-100
        self.lens_health = 100   # 0-100
        self.beam_on = True
        self.beam_intensity = 80 # 0-100
        self.engine_temp = 50    # 0-100, overheats above 90
        self.ship_signals = 0
        self.ships_saved = 0
        self.ships_lost = 0
        self.hour = NIGHT_START
        self.minutes = 0
        self.weather = "clear"
        self.weather_timer = 0
        self.storm_active = False
        self.storm_intensity = 0  # 0-100
        self.log = []
        self.current_event = None
        self.event_timer = 0
        self.wave_offset = 0
        self.seagull_timer = 0
        self.seagulls = []
        self.ships = []
        self.ship_spawn_timer = 0
        self.crack_events = 0
        self.total_ticks = 0
        self.fuel_low_warned = False
        self.engine_overheated = False
        self.flash_timer = 0
        self.flash_message = ""
        self.score = 0
        self.game_over = False
        self.game_over_reason = ""
        self.dawn_reached = False
        self.actions_taken = 0


# ─── Wave / Sea Rendering ────────────────────────────────────────────
WAVE_CHARS = "~≈∼∿≋"

def render_sea(state, width):
    """Generate an animated sea line."""
    line = []
    t = state.total_ticks * 0.05
    storm_factor = state.storm_intensity / 100.0
    for i in range(width):
        wave = math.sin(i * 0.15 + t) * (1 + storm_factor * 2)
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


def render_sky(state, width):
    """Render sky with stars and moon."""
    hour = state.hour + state.minutes / 60.0
    # Moon phase based on position
    moon_progress = (hour - NIGHT_START) / TOTAL_NIGHT_HOURS
    moon_x = int(width * 0.2 + width * 0.6 * moon_progress)
    
    line = [" "] * width
    
    # Stars
    random.seed(42)  # deterministic stars
    for _ in range(30):
        sx = random.randint(0, width - 1)
        twinkle = random.random()
        if (state.total_ticks + int(twinkle * 100)) % 3 < 2:
            line[sx] = random.choice("·✦⋆")
    random.seed()  # restore randomness
    
    # Clouds in storm
    if state.storm_active:
        for i in range(width):
            if random.random() < state.storm_intensity / 150:
                line[i] = random.choice("▒░▓")
    
    # Moon
    if 0 <= moon_x < width:
        line[moon_x] = "☽"
        if moon_x > 0: line[moon_x-1] = "░"
        if moon_x < width-1: line[moon_x+1] = "░"
    
    # Dawn glow near end
    if state.hour >= 5:
        progress = (state.hour - 5 + state.minutes / 60.0) / 1.0
        if progress > 0:
            for i in range(width):
                if random.random() < progress * 0.1:
                    line[i] = random.choice("░▒")
    
    return "".join(line)


def render_lighthouse(state):
    """Return the lighthouse ASCII art with beam."""
    lines = []
    
    beam_char = "◈" if state.beam_on and state.fuel > 0 else "·"
    intensity = state.beam_intensity / 100.0
    
    # Light room
    light_state = beam_char if state.beam_on and state.fuel > 0 else "○"
    light_color_indicator = "◆" if state.beam_on and state.fuel > 0 else "◇"
    
    lines.append(f"         {light_color_indicator}          ")
    lines.append(f"        ╔╩╗          ")
    
    if state.beam_on and state.fuel > 0:
        beam_width = max(1, int(intensity * 5))
        beam = "═" * beam_width
        lines.append(f"    {beam}╔╬╗{beam}      ")
        # Right beam extends further
        r_beam = "━" * min(20, int(intensity * 20))
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


def render_ships(state, sea_y, width):
    """Place ship sprites on the sea."""
    result = {}
    for ship in state.ships:
        x = ship["x"]
        y = ship.get("sea_y", sea_y)
        if ship["distress"]:
            sprite = "SOS!⛵"
        elif ship["saved"]:
            sprite = "⛵✓"
        else:
            sprite = "⛵"
        
        if 0 <= x < width - len(sprite):
            key = (y, x)
            result[key] = sprite
    return result


# ─── Events ───────────────────────────────────────────────────────────
EVENTS = [
    {
        "name": "lens_crack",
        "message": "⚠ A crack appears in the lens!",
        "duration": 0,
        "effect": lambda s: setattr(s, 'lens_health', max(0, s.lens_health - random.randint(10, 25))),
    },
    {
        "name": "fuel_leak",
        "message": "⚠ Fuel leak detected!",
        "duration": 0,
        "effect": lambda s: setattr(s, 'fuel', max(0, s.fuel - random.randint(5, 15))),
    },
    {
        "name": "supply_crate",
        "message": "📦 A supply crate washes ashore!",
        "duration": 0,
        "effect": lambda s: (setattr(s, 'fuel', min(100, s.fuel + random.randint(10, 25))),
                              setattr(s, 'lens_health', min(100, s.lens_health + random.randint(5, 15)))),
    },
    {
        "name": "engine_surge",
        "message": "⚠ Engine temperature surge!",
        "duration": 0,
        "effect": lambda s: setattr(s, 'engine_temp', min(100, s.engine_temp + random.randint(15, 30))),
    },
    {
        "name": "seagull_visit",
        "message": "🐦 A seagull lands on the railing.",
        "duration": 3,
        "effect": lambda s: None,
    },
    {
        "name": "ship_distress",
        "message": "🚨 A ship is signaling distress!",
        "duration": 5,
        "effect": lambda s: _spawn_distress_ship(s),
    },
]

def _spawn_distress_ship(s):
    for ship in s.ships:
        if ship["distress"]:
            return
    s.ships.append({
        "x": random.choice([5, 10, 15]),
        "distress": True,
        "saved": False,
        "timer": 20,
        "sea_y": 0,
    })


# ─── Game Logic ───────────────────────────────────────────────────────
def tick(state, dt):
    """Advance game state by dt seconds."""
    if state.game_over:
        return
    
    state.total_ticks += 1
    state.wave_offset += dt
    
    # Advance time
    state.minutes += 1
    if state.minutes >= 60:
        state.minutes = 0
        state.hour += 1
        if state.hour >= 24:
            state.hour = 0
        
        # Hourly log
        state.log.append(f"Hour {state.hour:02d}:00")
        if len(state.log) > 50:
            state.log = state.log[-30:]
        
        # Dawn check
        if state.hour >= NIGHT_END:
            state.dawn_reached = True
            state.game_over = True
            state.game_over_reason = "Dawn has broken! You survived the night."
            state.score += state.ships_saved * 100
            state.score += state.fuel * 5
            state.score += state.lens_health * 3
            state.score += max(0, (100 - state.engine_temp)) * 2
            return
    
    # Fuel consumption
    if state.beam_on:
        fuel_rate = 0.08 * (state.beam_intensity / 80.0)
        if state.storm_active:
            fuel_rate *= 1.3
        state.fuel = max(0, state.fuel - fuel_rate)
    
    if state.fuel <= 0 and state.beam_on:
        state.beam_on = False
        state.flash_message = "THE LIGHT HAS GONE OUT!"
        state.flash_timer = 10
    
    if state.fuel < 15 and not state.fuel_low_warned:
        state.fuel_low_warned = True
        state.flash_message = "⚠ Fuel running low!"
        state.flash_timer = 8
    
    if state.fuel > 30:
        state.fuel_low_warned = False
    
    # Engine temperature
    if state.beam_on:
        state.engine_temp += 0.03
        if state.storm_active:
            state.engine_temp += 0.02
    else:
        state.engine_temp = max(30, state.engine_temp - 0.08)
    
    if state.engine_temp > 90 and not state.engine_overheated:
        state.engine_overheated = True
        state.flash_message = "⚠ ENGINE OVERHEATING!"
        state.flash_timer = 8
    elif state.engine_temp <= 80:
        state.engine_overheated = False
    
    if state.engine_temp >= 100:
        state.beam_on = False
        state.engine_temp = 95
        state.flash_message = "ENGINE SHUTDOWN - OVERHEATED"
        state.flash_timer = 12
    
    # Beam intensity
    if state.beam_on and state.fuel > 0:
        target = min(100, state.fuel * 1.2) * (state.lens_health / 100.0)
        state.beam_intensity += (target - state.beam_intensity) * 0.05
    else:
        state.beam_intensity *= 0.9
    
    # Weather changes
    state.weather_timer -= 1
    if state.weather_timer <= 0:
        r = random.random()
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
    
    # Storm intensity
    if state.storm_active:
        state.storm_intensity = min(100, state.storm_intensity + random.uniform(-0.5, 1.0))
        state.lens_health = max(0, state.lens_health - 0.01 * (state.storm_intensity / 100))
    
    # Ship spawning
    state.ship_spawn_timer -= 1
    if state.ship_spawn_timer <= 0:
        state.ship_spawn_timer = random.randint(60, 180)
        if random.random() < 0.4:
            state.ships.append({
                "x": -5 if random.random() < 0.5 else SCREEN_W + 5,
                "distress": False,
                "saved": False,
                "timer": random.randint(60, 150),
                "direction": 1 if random.random() < 0.5 else -1,
            })
    
    # Update ships
    ships_to_remove = []
    for i, ship in enumerate(state.ships):
        if not ship.get("distress", False):
            ship["x"] += ship.get("direction", 1) * (0.5 if state.storm_active else 1)
            ship["timer"] -= 1
            if ship["timer"] <= 0 or ship["x"] < -20 or ship["x"] > SCREEN_W + 20:
                # Ship passed safely (or left)
                if state.beam_on and state.beam_intensity > 30:
                    state.ships_saved += 1
                    state.score += 50
                else:
                    if random.random() < 0.5:
                        state.ships_lost += 1
                        state.log.append("A ship was lost in the darkness...")
                ships_to_remove.append(i)
        else:
            # Distress ship
            ship["timer"] -= 1
            if ship["timer"] <= 0:
                state.ships_lost += 1
                state.log.append("A distressed ship could not reach safety...")
                state.flash_message = "A ship has been lost!"
                state.flash_timer = 10
                ships_to_remove.append(i)
    
    for i in sorted(ships_to_remove, reverse=True):
        state.ships.pop(i)
    
    # Random events
    state.event_timer -= 1
    if state.event_timer <= 0 and state.current_event:
        state.current_event = None
    
    if state.event_timer <= 0 and random.random() < 0.008:
        event = random.choice(EVENTS)
        state.current_event = event
        state.event_timer = event.get("duration", 0) * 10
        event["effect"](state)
        state.log.append(event["message"])
    
    # Flash timer
    if state.flash_timer > 0:
        state.flash_timer -= 1
    
    # Game over: no fuel and no way to continue
    if state.fuel <= 0 and state.hour < NIGHT_END and state.hour >= NIGHT_START:
        if random.random() < 0.005:  # small chance each tick
            lost = True
            state.ships_lost += 1
            state.log.append("A ship was lost - no light to guide it!")


# ─── Rendering ────────────────────────────────────────────────────────
def render(stdscr, state):
    """Full screen render."""
    stdscr.clear()
    h, w = stdscr.getmaxyx()
    
    # Create buffer
    buffer = [[" "] * SCREEN_W for _ in range(SCREEN_H)]
    colors = [[0] * SCREEN_W for _ in range(SCREEN_H)]
    
    # Sky (rows 0-3)
    sky_line = render_sky(state, SCREEN_W)
    for i, ch in enumerate(sky_line[:SCREEN_W]):
        buffer[0][i] = ch
        colors[0][i] = 2  # cyan for sky
    
    # Sea (rows 4-5)
    for row in range(4, 7):
        sea = render_sea(state, SCREEN_W)
        for i, ch in enumerate(sea[:SCREEN_W]):
            buffer[row][i] = ch
            colors[row][i] = 4  # blue for sea
    
    # Lighthouse (rows 7-22) - right side
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
        sy = 5 if ship["distress"] else 4 + random.randint(0, 1) if state.total_ticks % 10 == 0 else 5
        sprite = "SOS!⛵" if ship["distress"] else "⛵"
        if ship.get("saved"):
            sprite = "⛵✓"
        for i, ch in enumerate(sprite):
            if 0 <= sx + i < SCREEN_W and 0 <= sy < SCREEN_H:
                buffer[sy][sx + i] = ch
                colors[sy][sx + i] = 1 if ship["distress"] else 6  # red for distress, white otherwise
    
    # Rain/storm effects
    if state.storm_active:
        for y in range(SCREEN_H):
            for x in range(SCREEN_W):
                if random.random() < state.storm_intensity / 300:
                    buffer[y][x] = random.choice("·⁘⁖")
                    colors[y][x] = 4
    
    # Draw buffer to screen
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
    
    # ─── HUD Panel ───────────────────────────────────────────────────
    panel_y = 8
    panel_x = 2
    
    hour_display = state.hour if state.hour > 12 else state.hour if state.hour != 0 else 12
    ampm = "PM" if state.hour >= 12 else "AM"
    if state.hour > 12:
        hour_display = state.hour - 12
    elif state.hour == 0:
        hour_display = 12
    
    time_str = f"{hour_display}:{state.minutes:02d} {ampm}"
    
    # Night progress
    night_progress = 0
    if state.hour >= NIGHT_START:
        night_progress = (state.hour - NIGHT_START + state.minutes / 60.0) / TOTAL_NIGHT_HOURS
    elif state.hour < NIGHT_END:
        night_progress = (state.hour + 24 - NIGHT_START + state.minutes / 60.0) / TOTAL_NIGHT_HOURS
    
    progress_bar_len = 20
    filled = int(night_progress * progress_bar_len)
    progress_bar = "█" * filled + "░" * (progress_bar_len - filled)
    
    # Status indicators
    beam_status = "ON " if state.beam_on else "OFF"
    beam_color = 2 if state.beam_on and state.fuel > 0 else 1
    
    weather_icon = {"clear": "☀", "rain": "🌧", "storm": "⛈"}.get(state.weather, "?")
    
    # Fuel bar
    fuel_bar_len = 20
    fuel_filled = int((state.fuel / 100) * fuel_bar_len)
    fuel_bar = "█" * fuel_filled + "░" * (fuel_bar_len - fuel_filled)
    
    # Lens bar
    lens_filled = int((state.lens_health / 100) * fuel_bar_len)
    lens_bar = "█" * lens_filled + "░" * (fuel_bar_len - lens_filled)
    
    # Engine temp bar
    temp_filled = int((state.engine_temp / 100) * fuel_bar_len)
    temp_bar = "█" * temp_filled + "░" * (fuel_bar_len - temp_filled)
    
    # Intensity bar
    int_filled = int((state.beam_intensity / 100) * fuel_bar_len)
    int_bar = "█" * int_filled + "░" * (fuel_bar_len - int_filled)
    
    hud_lines = [
        f"╔══════════════════════════════╗",
        f"║  🏠 THE LIGHTHOUSE KEEPER   ║",
        f"║  Time: {time_str:>8s}              ║",
        f"║  Night: [{progress_bar}]   ║",
        f"╠══════════════════════════════╣",
        f"║  🔦 Beam: {beam_status}                ║",
        f"║  ⛽ Fuel:  [{fuel_bar}]   ║",
        f"║  🔍 Lens:  [{lens_bar}]   ║",
        f"║  🌡 Temp:  [{temp_bar}]   ║",
        f"║  ☆ Intensity: [{int_bar}]  ║",
        f"╠══════════════════════════════╣",
        f"║  Weather: {weather_icon} {state.weather:<6s}           ║",
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
    
    # ─── Action Help ──────────────────────────────────────────────────
    help_y = SCREEN_H - 5
    help_lines = [
        "[B] Toggle Beam  [R] Refuel  [F] Fix Lens",
        "[C] Cool Engine  [S] Signal Ship  [Q] Quit",
        f"{'[SPACE] Pause' if not state.game_over else '[R] Restart  [Q] Quit'}",
    ]
    
    for i, line in enumerate(help_lines):
        if help_y + i < h:
            try:
                stdscr.addstr(help_y + i, 2, line, curses.color_pair(6) | curses.A_BOLD)
            except curses.error:
                pass
    
    # ─── Event Message ────────────────────────────────────────────────
    if state.current_event and state.event_timer > 0:
        msg = state.current_event["message"]
        msg_y = 7
        try:
            stdscr.addstr(msg_y, (w - len(msg)) // 2, msg, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
    
    # ─── Flash Message ────────────────────────────────────────────────
    if state.flash_timer > 0:
        msg = state.flash_message
        flash_y = 3
        try:
            stdscr.addstr(flash_y, (w - len(msg)) // 2, msg, 
                         curses.color_pair(1) | curses.A_BOLD | curses.A_BLINK)
        except curses.error:
            pass
    
    # ─── Game Over Overlay ────────────────────────────────────────────
    if state.game_over:
        overlay_lines = [
            "╔═══════════════════════════════════╗",
            f"║  {'DAWN BREAKS!' if state.dawn_reached else 'GAME OVER':^33s}║",
            "╠═══════════════════════════════════╣",
            f"║  Ships saved:  {state.ships_saved:>3d}              ║",
            f"║  Ships lost:   {state.ships_lost:>3d}              ║",
            f"║  Final score:  {state.score:>6d}          ║",
            "║                                   ║",
            "║  Press [R] to restart or [Q] quit ║",
            "╚═══════════════════════════════════╝",
        ]
        oy = (h - len(overlay_lines)) // 2
        for i, line in enumerate(overlay_lines):
            ox = (w - len(line)) // 2
            if oy + i < h:
                try:
                    color = curses.color_pair(2) | curses.A_BOLD if state.dawn_reached else curses.color_pair(1) | curses.A_BOLD
                    stdscr.addstr(oy + i, ox, line, color)
                except curses.error:
                    pass
    
    # ─── Log (bottom area) ────────────────────────────────────────────
    log_y = SCREEN_H - 2
    recent_logs = state.log[-1:] if state.log else []
    if recent_logs and not state.game_over:
        try:
            stdscr.addstr(log_y, 2, recent_logs[-1][:60], curses.color_pair(3))
        except curses.error:
            pass
    
    stdscr.refresh()


# ─── Main Game Loop ───────────────────────────────────────────────────
def main(stdscr):
    # Setup colors
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
    stdscr.timeout(100) # refresh every 100ms
    
    state = Lighthouse()
    last_time = time.time()
    
    while True:
        # Handle input
        key = stdscr.getch()
        
        if state.game_over:
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('r') or key == ord('R'):
                state = Lighthouse()
                last_time = time.time()
                continue
        else:
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('b') or key == ord('B'):
                if state.fuel > 0 and state.engine_temp < 100:
                    state.beam_on = not state.beam_on
                    state.actions_taken += 1
            elif key == ord('r') or key == ord('R'):
                # Refuel - costs time but restores fuel
                fuel_gain = random.randint(15, 30)
                state.fuel = min(100, state.fuel + fuel_gain)
                state.log.append(f"Refueled +{fuel_gain}%")
                state.actions_taken += 1
                # Advance time slightly
                state.minutes += 5
                if state.minutes >= 60:
                    state.minutes = 0
                    state.hour += 1
            elif key == ord('f') or key == ord('F'):
                # Fix lens
                lens_fix = random.randint(10, 25)
                state.lens_health = min(100, state.lens_health + lens_fix)
                state.log.append(f"Repaired lens +{lens_fix}%")
                state.actions_taken += 1
                state.minutes += 3
                if state.minutes >= 60:
                    state.minutes = 0
                    state.hour += 1
            elif key == ord('c') or key == ord('C'):
                # Cool engine
                cool_amount = random.randint(15, 30)
                state.engine_temp = max(30, state.engine_temp - cool_amount)
                state.log.append(f"Cooled engine -{cool_amount}°")
                state.actions_taken += 1
                state.minutes += 2
                if state.minutes >= 60:
                    state.minutes = 0
                    state.hour += 1
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
        
        # Update game
        if not state.game_over:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            tick(state, dt)
        
        # Render
        render(stdscr, state)


def run():
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()