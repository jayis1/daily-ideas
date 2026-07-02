#!/usr/bin/env python3
"""
🚂 ASCII Train Simulator

A terminal-based side-scrolling train driving game.
Manage your steam locomotive's speed, coal, and water while navigating
procedurally generated terrain with stations, signals, and obstacles.

Controls:
  ↑/W     - Increase throttle
  ↓/S     - Decrease throttle
  ←/A     - Apply brakes
  →/D     - Release brakes
  C       - Stoke coal (adds fuel)
  F       - Fill water (when near water tower)
  SPACE   - Horn
  Q/ESC   - Quit
"""

import curses
import random
import math
import time
import json
import os

# ─── World Generation ────────────────────────────────────────────────────────

TERRAIN_FLAT = 0
TERRAIN_HILL_UP = 1
TERRAIN_HILL_DOWN = 2
TERRAIN_BRIDGE = 3
TERRAIN_TUNNEL = 4
TERRAIN_STATION = 5
TERRAIN_WATER = 6

SIGNAL_GREEN = 0
SIGNAL_YELLOW = 1
SIGNAL_RED = 2

class World:
    """Procedurally generated side-scrolling world."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.chunks = {}
        self.total_distance = 0

    def get_elevation(self, x):
        """Get terrain elevation at position x."""
        base = math.sin(x * 0.003) * 4 + math.sin(x * 0.007) * 2
        detail = math.sin(x * 0.02) * 1 + math.sin(x * 0.05) * 0.5
        return int(base + detail)

    def get_terrain_type(self, x):
        """Get terrain type at position x."""
        rng = random.Random(x * 7919 + 104729)
        val = rng.random()

        # Every ~200 units, place a station
        if x % 200 < 8 and x > 20:
            return TERRAIN_STATION

        # Bridges over water
        if x % 150 < 12 and x > 30:
            return TERRAIN_WATER

        # Tunnels through hills
        elev = abs(self.get_elevation(x))
        if elev > 5 and x % 80 < 10 and x > 15:
            return TERRAIN_TUNNEL

        # Hill sections
        slope = self.get_elevation(x) - self.get_elevation(x - 1)
        if slope > 0.5:
            return TERRAIN_HILL_UP
        elif slope < -0.5:
            return TERRAIN_HILL_DOWN

        return TERRAIN_FLAT

    def get_signal(self, x):
        """Get signal state at position x."""
        rng = random.Random(x * 13007 + 51439)
        # Signals every ~60-100 units
        if x % 70 < 3 and x > 15:
            val = rng.random()
            if val < 0.6:
                return SIGNAL_GREEN
            elif val < 0.85:
                return SIGNAL_YELLOW
            else:
                return SIGNAL_RED
        return None

    def get_station_name(self, x):
        """Generate a station name."""
        prefixes = ["North", "South", "East", "West", "Upper", "Lower", "Old", "New",
                     "Great", "Little", "St.", "Fort", "Port", "Kings", "Queens"]
        roots = ["bridge", "ford", "ham", "bury", "field", "wood", "stone", "haven",
                 "dale", "worth", "ton", "gate", "wick", "leigh", "mouth", "bury",
                 "ford", "cross", "mill", "brook", "thorpe", "minster", "caster"]
        suffixes = ["", "ton", "ville", "burg", "town", "shire", "ford", "field"]
        rng = random.Random(x * 42017 + 7381)
        name = rng.choice(prefixes) + rng.choice(roots) + rng.choice(suffixes)
        return name


class Train:
    """The player's steam locomotive."""

    def __init__(self):
        self.x = 10.0         # Position in the world
        self.speed = 0.0      # Current speed (units/sec)
        self.throttle = 0     # Throttle level 0-8
        self.brake = 0.0      # Brake pressure 0.0-1.0
        self.coal = 80.0      # Coal level 0-100
        self.water = 70.0     # Water level 0-100
        self.pressure = 50.0  # Steam pressure 0-100
        self.whistle = 0.0    # Whistle animation timer
        self.distance = 0.0   # Total distance traveled
        self.score = 0
        self.stations_visited = 0
        self.running = True
        self.derailment = False
        self.at_station = False
        self.station_name = ""
        self.near_water_tower = False
        self.signal_violation = False
        self.signal_warning = ""
        self.fuel_warning = ""
        self.passengers = 0
        self.max_passengers = 50
        self.delivered = 0

    def update(self, dt, world):
        """Update train physics."""
        if not self.running or self.derailment:
            return

        # Coal consumption
        if self.throttle > 0 and self.coal > 0:
            self.coal -= self.throttle * 0.08 * dt
            if self.coal < 0:
                self.coal = 0

        # Pressure builds with coal and throttle
        if self.coal > 0 and self.throttle > 0:
            target_pressure = self.throttle * 12.5
            self.pressure += (target_pressure - self.pressure) * 0.5 * dt
        else:
            self.pressure -= self.pressure * 0.3 * dt

        # Water consumption (steam)
        if self.pressure > 10:
            self.water -= self.pressure * 0.003 * dt
            if self.water < 0:
                self.water = 0
                self.pressure *= 0.5  # Low water = low pressure

        # Force from throttle
        if self.coal > 0 and self.water > 0 and self.throttle > 0:
            force = self.pressure * 0.015
        else:
            force = 0

        # Brake force
        brake_force = self.brake * self.speed * 0.8

        # Friction
        friction = self.speed * 0.02

        # Gravity (terrain slope)
        terrain = world.get_terrain_type(int(self.x))
        gravity = 0
        if terrain == TERRAIN_HILL_UP:
            gravity = -0.3
        elif terrain == TERRAIN_HILL_DOWN:
            gravity = 0.2

        # Net acceleration
        accel = (force - brake_force - friction + gravity) * dt

        self.speed += accel
        if self.speed < 0:
            self.speed = 0
        if self.speed > 25:
            self.speed = 25

        # Check for derailment on sharp curves or excessive speed
        if self.speed > 22 and self.brake > 0.5:
            self.derailment = True
            self.running = False

        # Check signals
        signal = world.get_signal(int(self.x))
        if signal == SIGNAL_RED and self.speed > 2:
            self.signal_violation = True
            self.score -= 50
            self.signal_warning = "⚠ SIGNAL VIOLATION! -50 points"
        elif signal == SIGNAL_YELLOW and self.speed > 10:
            self.signal_warning = "⚠ Caution: slow down!"
        elif signal is not None:
            self.signal_warning = ""

        # Update position
        self.x += self.speed * dt * 3
        self.distance += abs(self.speed * dt * 3)

        # Check station
        self.at_station = False
        self.near_water_tower = False
        current_terrain = world.get_terrain_type(int(self.x))
        if current_terrain == TERRAIN_STATION:
            self.at_station = True
            self.station_name = world.get_station_name(int(self.x))
            self.near_water_tower = True
            if self.speed < 1:
                # Board passengers
                if self.passengers < self.max_passengers:
                    boarding = min(5, self.max_passengers - self.passengers)
                    self.passengers += boarding
                self.stations_visited += 1
                self.score += 10

        # Fuel warnings
        self.fuel_warning = ""
        if self.coal < 15:
            self.fuel_warning = "🔥 Low coal! Press C to stoke!"
        if self.water < 15:
            self.fuel_warning = "💧 Low water! Find a water tower!"

        # Whistle decay
        if self.whistle > 0:
            self.whistle -= dt * 3

        # Score for distance
        self.score = int(self.distance * 0.5) + self.stations_visited * 10 + self.delivered * 5

    def stoke_coal(self):
        """Add coal to the firebox."""
        self.coal = min(100, self.coal + 15)

    def fill_water(self):
        """Fill water tank (only at stations)."""
        if self.near_water_tower:
            self.water = min(100, self.water + 25)

    def sound_whistle(self):
        """Blow the whistle!"""
        self.whistle = 1.0


class Renderer:
    """ASCII art renderer for the train simulator."""

    # Sky patterns based on "time of day" cycling
    SKY_CHARS = [' ', '.', '·', '°', '*', '✦', '✧']

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.frame = 0
        self.smoke_particles = []

    def get_colors(self):
        """Initialize color pairs."""
        try:
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)    # Default
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)    # Ground
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # Train
            curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)      # Danger
            curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)     # Sky/water
            curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)     # Station
            curses.init_pair(7, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Whistle
            curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_WHITE)    # Tunnel
            return True
        except:
            return False

    def draw(self, train, world, height, width):
        """Draw the full game screen."""
        self.frame += 1
        screen_x = int(train.x)

        has_colors = self.get_colors()

        # Clear screen
        self.stdscr.clear()

        # ─── Draw sky ────────────────────────────────────────────────
        sky_height = 6
        for y in range(sky_height):
            for x in range(width):
                wx = screen_x + x - 10
                # Stars
                rng = random.Random(wx * 31 + y * 97 + int(self.frame * 0.01))
                if rng.random() < 0.05:
                    ch = rng.choice(['.', '·', '*', '✦'])
                    self.stdscr.addch(y, x, ch)
                else:
                    # Clouds
                    cloud_val = math.sin(wx * 0.05) * math.cos(wx * 0.03 + y * 0.5)
                    if cloud_val > 0.6:
                        self.stdscr.addch(y, x, '░')
                    elif cloud_val > 0.4:
                        self.stdscr.addch(y, x, '·')

        # ─── Draw terrain ────────────────────────────────────────────
        ground_y = sky_height + 4  # Base ground level

        for x in range(width):
            wx = screen_x + x - 10
            elev = world.get_elevation(wx)
            terrain = world.get_terrain_type(wx)
            track_y = ground_y + max(0, min(5, -elev + 3))

            # Draw sky between sky area and ground
            for y in range(sky_height, track_y - 1):
                # Distant scenery
                rng = random.Random(wx * 13 + y * 7)
                dist_elev = world.get_elevation(wx)
                dist_y = ground_y + max(0, min(5, -dist_elev + 3))
                if y >= dist_y - 1:
                    pass  # Will be drawn as terrain

            if terrain == TERRAIN_TUNNEL:
                # Tunnel entrance
                for y in range(track_y - 4, track_y + 2):
                    if 0 <= y < height - 2:
                        self.stdscr.addch(y, x, '█')
                if 0 <= track_y - 2 < height - 2:
                    self.stdscr.addch(track_y - 2, x, '▓')

            elif terrain == TERRAIN_WATER:
                # Bridge over water
                if 0 <= track_y < height - 2:
                    self.stdscr.addch(track_y, x, '═')
                for y in range(track_y + 1, min(track_y + 4, height - 2)):
                    wave_ch = '≈' if (wx + self.frame // 4) % 3 == 0 else '~'
                    self.stdscr.addch(y, x, wave_ch)

            elif terrain == TERRAIN_STATION:
                # Station platform
                if 0 <= track_y < height - 2:
                    self.stdscr.addch(track_y, x, '═')
                # Platform
                if 0 <= track_y + 1 < height - 2:
                    self.stdscr.addch(track_y + 1, x, '▓')
                # Building above
                if x == width // 2 - 2:
                    for y in range(max(0, track_y - 5), track_y):
                        self.stdscr.addch(y, x, '║')
                elif x == width // 2 + 2:
                    for y in range(max(0, track_y - 5), track_y):
                        self.stdscr.addch(y, x, '║')
                elif abs(x - width // 2) <= 2:
                    for y in range(max(0, track_y - 5), track_y):
                        self.stdscr.addch(y, x, '─')

            else:
                # Normal terrain
                if 0 <= track_y < height - 2:
                    self.stdscr.addch(track_y, x, '─')

                # Ground below track
                for y in range(track_y + 1, min(track_y + 6, height - 2)):
                    if 0 <= y < height - 2:
                        depth = y - track_y
                        ch = '▓' if depth == 1 else ('░' if depth < 4 else ' ')
                        self.stdscr.addch(y, x, ch)

                # Hills
                if terrain == TERRAIN_HILL_UP:
                    for y in range(track_y - 1, track_y):
                        if 0 <= y < height - 2:
                            self.stdscr.addch(y, x, '/' if (x + self.frame // 8) % 4 == 0 else '│')

            # Signal
            signal = world.get_signal(wx)
            if signal is not None:
                sig_y = track_y - 3
                if 0 <= sig_y < height - 2:
                    self.stdscr.addch(sig_y, x, '║')
                sig_y2 = track_y - 4
                if 0 <= sig_y2 < height - 2:
                    sig_char = '●'
                    if signal == SIGNAL_RED:
                        sig_char = '⬤' if self.frame % 10 < 5 else '●'
                    elif signal == SIGNAL_YELLOW:
                        sig_char = '◆'
                    else:
                        sig_char = '○'
                    self.stdscr.addch(sig_y2, x, sig_char)

            # Trees and scenery
            rng = random.Random(wx * 41 + 1)
            if rng.random() < 0.03 and terrain == TERRAIN_FLAT:
                tree_y = track_y - 1
                if 0 <= tree_y < height - 2:
                    tree_ch = rng.choice(['🌲', '🌳', '♣', '♠'])
                    try:
                        self.stdscr.addch(tree_y, x, ord(tree_ch[0]))
                    except:
                        self.stdscr.addch(tree_y, x, '♣')

        # ─── Draw the train ──────────────────────────────────────────
        train_screen_x = 10
        train_y = ground_y + max(0, min(5, -world.get_elevation(int(train.x)) + 3)) - 1

        # Smoke particles
        if train.throttle > 0 and train.coal > 0:
            if self.frame % 2 == 0:
                self.smoke_particles.append({
                    'x': train_screen_x + 2,
                    'y': train_y - 2,
                    'life': 1.0,
                    'dx': random.uniform(-0.3, 0.1),
                    'dy': random.uniform(-0.5, -0.2),
                    'ch': random.choice(['·', '°', '○', '○', '◌'])
                })

        # Update and draw smoke
        new_particles = []
        for p in self.smoke_particles:
            p['x'] += p['dx']
            p['y'] += p['dy']
            p['life'] -= 0.05
            p['dx'] += random.uniform(-0.1, 0.1)
            if p['life'] > 0 and 0 <= int(p['y']) < height and 0 <= int(p['x']) < width:
                new_particles.append(p)
                try:
                    self.stdscr.addch(int(p['y']), int(p['x']), '·' if p['life'] < 0.5 else '○')
                except:
                    pass
        self.smoke_particles = new_particles[-50:]  # Limit particles

        # Draw locomotive body
        engine_art = [
            "  ┌─╥─┐  ",
            " ┌┘ ║ └┐ ",
            "┌╩══╩═╩═╗",
            "║ ◢███◣ ║",
            "╟──╥──╥──╢",
            "╚═╧══╧═══╝",
        ]

        # Simplified locomotive for better rendering
        loco_lines = [
            "    ┌─╖─┐    ",
            "   ┌┘ ┣ └┐   ",
            " ┌──╥═╥──╗  ",
            " │ ◈████◈ │ ",
            " ├─╥─╥─╥─┤ ",
            " ╘╧═╧═╧═╧╛ ",
        ]

        # Wheel animation
        wheel_phase = int(self.frame * train.speed * 0.5) % 4
        wheel_chars = ['○', '◎', '◉', '◎']

        for i, line in enumerate(loco_lines):
            y = train_y - 4 + i
            if 0 <= y < height - 2:
                # Add wheel spin characters
                modified = line.replace('╧', wheel_chars[wheel_phase] if i == 5 else '╧')
                try:
                    self.stdscr.addstr(y, train_screen_x, modified)
                except:
                    pass

        # Tender (coal car)
        tender_lines = [
            " ┌────────┐",
            " │ ████░░ │",
            " ├────────┤",
            " ╘══○══○══╛",
        ]
        for i, line in enumerate(tender_lines):
            y = train_y - 4 + i
            x = train_screen_x + 12
            if 0 <= y < height - 2:
                try:
                    self.stdscr.addstr(y, x, line)
                except:
                    pass

        # Passenger car
        car_lines = [
            " ┌──────┐",
            " │▪▪▪▪▪▪│",
            " ├──────┤",
            " ╘═○══○═╛",
        ]
        for i, line in enumerate(car_lines):
            y = train_y - 4 + i
            x = train_screen_x + 22
            if 0 <= y < height - 2:
                try:
                    self.stdscr.addstr(y, x, line)
                except:
                    pass

        # ─── Draw HUD ────────────────────────────────────────────────
        hud_y = height - 8

        # Speed gauge
        speed_pct = min(1.0, train.speed / 25.0)
        speed_bar_len = 20
        speed_bar = '█' * int(speed_pct * speed_bar_len) + '░' * (speed_bar_len - int(speed_pct * speed_bar_len))

        self.stdscr.addstr(hud_y, 2, f"Speed: [{speed_bar}] {train.speed:.1f} mph")

        # Pressure gauge
        press_pct = min(1.0, train.pressure / 100.0)
        press_bar = '█' * int(press_pct * 15) + '░' * (15 - int(press_pct * 15))
        self.stdscr.addstr(hud_y + 1, 2, f"Steam: [{press_bar}] {train.pressure:.0f} PSI")

        # Throttle
        throttle_str = '▓' * train.throttle + '░' * (8 - train.throttle)
        self.stdscr.addstr(hud_y + 2, 2, f"Throt: [{throttle_str}] {train.throttle}/8")

        # Brake
        brake_str = '▓' * int(train.brake * 10) + '░' * (10 - int(train.brake * 10))
        self.stdscr.addstr(hud_y + 3, 2, f"Brake: [{brake_str}] {train.brake:.0%}")

        # Coal
        coal_pct = train.coal / 100.0
        coal_bar = '█' * int(coal_pct * 15) + '░' * (15 - int(coal_pct * 15))
        self.stdscr.addstr(hud_y, 45, f"Coal:  [{coal_bar}] {train.coal:.0f}%")

        # Water
        water_pct = train.water / 100.0
        water_bar = '█' * int(water_pct * 15) + '░' * (15 - int(water_pct * 15))
        self.stdscr.addstr(hud_y + 1, 45, f"Water: [{water_bar}] {train.water:.0f}%")

        # Score and distance
        self.stdscr.addstr(hud_y + 2, 45, f"Score: {train.score}  Dist: {train.distance:.0f}m")

        # Passengers
        self.stdscr.addstr(hud_y + 3, 45, f"Passengers: {train.passengers}/{train.max_passengers}")

        # Controls hint
        self.stdscr.addstr(hud_y + 4, 2, "↑/↓ Throttle  ← Brake  C Coal  F Water  SPACE Horn  Q Quit")

        # Status messages
        if train.at_station and train.speed < 1:
            self.stdscr.addstr(hud_y + 5, 2, f"🚉 Station: {train.station_name}  [Boarding passengers]")
        elif train.at_station:
            self.stdscr.addstr(hud_y + 5, 2, f"🚉 Approaching {train.station_name} — Slow down!")

        if train.fuel_warning:
            self.stdscr.addstr(hud_y + 6, 2, train.fuel_warning)

        if train.signal_warning:
            self.stdscr.addstr(hud_y + 6, 45, train.signal_warning)

        # Whistle animation
        if train.whistle > 0:
            whistle_text = "CHOO CHOO!" if int(train.whistle * 5) % 2 == 0 else "🎶 CHOO! 🎶"
            self.stdscr.addstr(2, width // 2 - 5, whistle_text)

        # Derailment
        if train.derailment:
            self.stdscr.addstr(height // 2, width // 2 - 10, "💥 DERAILED! 💥")
            self.stdscr.addstr(height // 2 + 1, width // 2 - 15, "Press R to restart or Q to quit")

        self.stdscr.refresh()


def game_loop(stdscr):
    """Main game loop using curses."""
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(50)

    height, width = stdscr.getmaxyx()

    world = World(seed=random.randint(0, 999999))
    train = Train()
    renderer = Renderer(stdscr)

    last_time = time.time()

    while True:
        current_time = time.time()
        dt = min(current_time - last_time, 0.1)
        last_time = current_time

        # Handle input
        try:
            key = stdscr.getch()
        except:
            key = -1

        if key == ord('q') or key == 27:  # Q or ESC
            break
        elif key in (ord('w'), ord('W'), curses.KEY_UP):
            train.throttle = min(8, train.throttle + 1)
        elif key in (ord('s'), ord('S'), curses.KEY_DOWN):
            train.throttle = max(0, train.throttle - 1)
        elif key in (ord('a'), ord('A'), curses.KEY_LEFT):
            train.brake = min(1.0, train.brake + 0.1)
        elif key in (ord('d'), ord('D'), curses.KEY_RIGHT):
            train.brake = max(0.0, train.brake - 0.1)
        elif key == ord('c') or key == ord('C'):
            train.stoke_coal()
        elif key == ord('f') or key == ord('F'):
            train.fill_water()
        elif key == ord(' '):
            train.sound_whistle()
        elif key == ord('r') or key == ord('R'):
            if train.derailment:
                train = Train()
        elif key == ord('b') or key == ord('B'):
            # Emergency brake
            train.brake = 1.0
            train.throttle = 0

        # Update physics
        train.update(dt, world)

        # Render
        try:
            renderer.draw(train, world, height, width)
        except curses.error:
            pass

        # Check if train is completely stopped and out of fuel
        if train.speed < 0.01 and train.coal <= 0 and train.pressure < 5:
            stdscr.addstr(height // 2, width // 2 - 15, "Out of coal! Game Over!")
            stdscr.addstr(height // 2 + 1, width // 2 - 12, "Press Q to quit")
            stdscr.refresh()
            time.sleep(0.1)

    return train.score


def main():
    """Entry point."""
    print("🚂 ASCII Train Simulator")
    print("=" * 40)
    print()
    print("Controls:")
    print("  ↑/W     Increase throttle")
    print("  ↓/S     Decrease throttle")
    print("  ←/A     Apply brakes")
    print("→/D     Release brakes")
    print("  C       Stoke coal")
    print("  F       Fill water (at stations)")
    print("  SPACE   Sound whistle")
    print("  B       Emergency brake")
    print("  Q/ESC   Quit")
    print()
    print("Starting simulation...")
    time.sleep(1)

    try:
        score = curses.wrapper(game_loop)
        print(f"\n🎮 Final Score: {score}")
        print("Thanks for riding! 🚂")
    except KeyboardInterrupt:
        print("\nSimulation ended.")


if __name__ == "__main__":
    main()