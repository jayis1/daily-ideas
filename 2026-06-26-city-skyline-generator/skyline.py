#!/usr/bin/env python3
"""
Procedural City Skyline Generator
Generates detailed ASCII city skylines with buildings, weather, time-of-day, and more.

Features:
  - 6 architectural styles (modern, art deco, gothic, industrial, brutalist, residential)
  - 4 times of day (dawn, day, dusk, night) with distinct color palettes
  - 6 weather conditions (clear, cloudy, rain, snow, fog, storm)
  - Waterfront mode with building reflections
  - Neon signs on buildings (night/dusk)
  - Birds and airplanes in the sky
  - SVG export for sharing
  - Save output to file
  - Seeded RNG for reproducible output
"""

import random
import argparse
import sys
import os

VERSION = "1.1.0"

# ─── Character Sets ────────────────────────────────────────────────────────────

STARS = "✦·.*+⋆✧"
MOON_PHASES = {"new": "●", "crescent": "☽", "quarter": "◑", "gibbous": "◕", "full": "○"}
WINDOW_CHARS = {"lit": "▣", "dim": "░", "dark": "·", "bright": "✦"}
GROUND_TOP = "▓"
GROUND_BOT = "░"
WATER_CHARS = "≈∽～˜"
WAVE_CHARS = "∿〜～"
NEON_CHARS = ["♠", "♥", "♦", "♣", "★", "☆", "◆", "◇", "○", "●", "■", "□", "▲", "▼", "♪", "♫", "☎", "⌂", "✿", "❖"]
BIRD_CHARS = ["⌇", "〜", "∿"]
PLANE_CHAR = "✈"

TIME_THEMES = {
    "night": {
        "sky":       ["\033[48;5;16m",  "\033[48;5;17m",  "\033[48;5;18m"],
        "bldg":      "\033[38;5;236m",
        "bldg_edge": "\033[38;5;244m",
        "win_lit":   "\033[38;5;214m",
        "win_bright":"\033[38;5;229m",
        "win_dim":    "\033[38;5;239m",
        "win_dark":   "\033[38;5;236m",
        "ground":    "\033[48;5;232m",
        "star":      "\033[38;5;147m",
        "moon":      "\033[38;5;255m",
        "sun":       "",
        "weather_rain": "\033[38;5;117m",
        "weather_snow": "\033[38;5;255m",
        "weather_fog":  "\033[38;5;245m",
        "weather_cloud":"\033[38;5;244m",
        "weather_storm":"\033[38;5;220m",
        "water":     "\033[38;5;25m",
        "neon":      "\033[38;5;196m",
        "bird":      "",
        "plane":     "\033[38;5;248m",
        "reset":     "\033[0m",
    },
    "dawn": {
        "sky":       ["\033[48;5;17m",  "\033[48;5;55m",  "\033[48;5;202m"],
        "bldg":      "\033[38;5;239m",
        "bldg_edge": "\033[38;5;248m",
        "win_lit":   "\033[38;5;228m",
        "win_bright":"\033[38;5;229m",
        "win_dim":    "\033[38;5;243m",
        "win_dark":   "\033[38;5;239m",
        "ground":    "\033[48;5;232m",
        "star":      "\033[38;5;147m",
        "moon":      "\033[38;5;228m",
        "sun":       "\033[38;5;220m",
        "weather_rain": "\033[38;5;117m",
        "weather_snow": "\033[38;5;255m",
        "weather_fog":  "\033[38;5;180m",
        "weather_cloud":"\033[38;5;248m",
        "weather_storm":"\033[38;5;220m",
        "water":     "\033[38;5;66m",
        "neon":      "\033[38;5;202m",
        "bird":      "\033[38;5;239m",
        "plane":     "",
        "reset":     "\033[0m",
    },
    "day": {
        "sky":       ["\033[48;5;33m",  "\033[48;5;39m",  "\033[48;5;117m"],
        "bldg":      "\033[38;5;250m",
        "bldg_edge": "\033[38;5;252m",
        "win_lit":   "\033[38;5;117m",
        "win_bright":"\033[38;5;195m",
        "win_dim":   "\033[38;5;247m",
        "win_dark":  "\033[38;5;244m",
        "ground":    "\033[48;5;239m",
        "star":      "",
        "moon":      "",
        "sun":       "\033[38;5;226m",
        "weather_rain": "\033[38;5;117m",
        "weather_snow": "\033[38;5;255m",
        "weather_fog":  "\033[38;5;252m",
        "weather_cloud":"\033[38;5;252m",
        "weather_storm":"\033[38;5;226m",
        "water":     "\033[38;5;39m",
        "neon":      "",
        "bird":      "\033[38;5;236m",
        "plane":     "\033[38;5;244m",
        "reset":     "\033[0m",
    },
    "dusk": {
        "sky":       ["\033[48;5;17m",  "\033[48;5;53m",  "\033[48;5;131m"],
        "bldg":      "\033[38;5;242m",
        "bldg_edge": "\033[38;5;248m",
        "win_lit":   "\033[38;5;214m",
        "win_bright":"\033[38;5;220m",
        "win_dim":    "\033[38;5;241m",
        "win_dark":   "\033[38;5;238m",
        "ground":    "\033[48;5;232m",
        "star":      "\033[38;5;147m",
        "moon":      "\033[38;5;222m",
        "sun":       "\033[38;5;202m",
        "weather_rain": "\033[38;5;117m",
        "weather_snow": "\033[38;5;255m",
        "weather_fog":  "\033[38;5;180m",
        "weather_cloud":"\033[38;5;244m",
        "weather_storm":"\033[38;5;202m",
        "water":     "\033[38;5;55m",
        "neon":      "\033[38;5;206m",
        "bird":      "\033[38;5;242m",
        "plane":     "\033[38;5;248m",
        "reset":     "\033[0m",
    },
}

# Neon color palette for signs (ANSI 256-color codes)
NEON_COLORS = [
    "\033[38;5;196m",  # red
    "\033[38;5;206m",  # hot pink
    "\033[38;5;214m",  # orange
    "\033[38;5;226m",  # yellow
    "\033[38;5;82m",   # green
    "\033[38;5;45m",   # cyan
    "\033[38;5;129m",  # purple
    "\033[38;5;213m",  # pink
    "\033[38;5;51m",   # bright cyan
    "\033[38;5;220m",  # gold
]

# ─── Building Class ─────────────────────────────────────────────────────────────

class Building:
    """A single building with height, width, windows, optional antenna/spire, and neon signs."""

    def __init__(self, rng, style="mixed", min_height=3, max_height=18):
        if style == "mixed":
            style = rng.choice(["modern", "art_deco", "gothic", "industrial", "brutalist", "residential"])
        self.style = style
        self.height = rng.randint(min_height, max_height)
        self.width = rng.randint(2, 7)
        self.has_antenna = rng.random() < 0.25
        self.antenna_height = rng.randint(1, 3) if self.has_antenna else 0
        self.has_spire = style in ("gothic", "art_deco") and rng.random() < 0.3
        self.windows = self._gen_windows(rng)
        # Neon sign: only for night/dusk, wider buildings, not residential
        self.has_neon = (
            self.width >= 3
            and self.height >= 5
            and style not in ("residential",)
            and rng.random() < 0.35
        )
        self.neon_char = rng.choice(NEON_CHARS) if self.has_neon else ""
        self.neon_color_idx = rng.randint(0, len(NEON_COLORS) - 1) if self.has_neon else 0
        # Body character varies by style
        if style == "brutalist":
            self.body_char = "▓"
        elif style == "modern":
            self.body_char = "█"
        elif style == "industrial":
            self.body_char = "▒"
        else:
            self.body_char = rng.choice(["█", "▓", "▒"])
        # Edge character
        self.edge_char = "┃" if style in ("modern", "industrial") else "│"

    def _gen_windows(self, rng):
        """Generate the window grid for this building."""
        windows = []
        for _ in range(self.height):
            row = []
            for _ in range(self.width):
                r = rng.random()
                if r < 0.35:
                    row.append("lit")
                elif r < 0.55:
                    row.append("dim")
                elif r < 0.80:
                    row.append("dark")
                else:
                    row.append("bright")
            windows.append(row)
        return windows

    @property
    def total_height(self):
        """Total height including antenna and spire."""
        extra = self.antenna_height + (1 if self.has_spire else 0)
        return self.height + extra


# ─── City Generator ────────────────────────────────────────────────────────────

class CityGenerator:
    """Generates a complete city skyline on a canvas."""

    def __init__(self, width=80, time="night", weather="clear", style="mixed",
                 density=0.7, seed=None, water=False):
        # Validate inputs
        if not isinstance(width, int) or width < 20:
            raise ValueError(f"Width must be an integer >= 20, got {width}")
        if width > 300:
            raise ValueError(f"Width must be <= 300, got {width}")
        if time not in TIME_THEMES:
            raise ValueError(f"Time must be one of {list(TIME_THEMES.keys())}, got '{time}'")
        valid_weather = ["clear", "cloudy", "rain", "snow", "fog", "storm"]
        if weather not in valid_weather:
            raise ValueError(f"Weather must be one of {valid_weather}, got '{weather}'")
        valid_styles = ["modern", "art_deco", "gothic", "industrial", "brutalist", "residential", "mixed"]
        if style not in valid_styles:
            raise ValueError(f"Style must be one of {valid_styles}, got '{style}'")

        self.width = width
        self.time = time
        self.weather = weather
        self.style = style
        self.density = max(0.1, min(1.0, density))
        self.rng = random.Random(seed)
        self.seed = seed
        self.water = water
        self.sky_height = 14
        self.ground_height = 2
        self.water_height = 4 if water else 0
        self.total_height = self.sky_height + self.ground_height + self.water_height

        self.buildings = []
        self._place_buildings()

    def _place_buildings(self):
        """Place buildings across the skyline width with density control."""
        x = 0
        while x < self.width:
            if self.rng.random() < self.density:
                center_dist = abs(x - self.width / 2) / (self.width / 2)
                max_h = int(14 * (1 - center_dist * 0.5)) + 2
                max_h = max(5, min(14, max_h))
                b = Building(self.rng, style=self.style, min_height=3, max_height=max_h)
                self.buildings.append((x, b))
                x += b.width + self.rng.randint(0, 1)
            else:
                x += self.rng.randint(1, 2)

    def render(self, color=True):
        """Render the city skyline as a string, optionally with ANSI color codes."""
        R = self.rng
        W = self.width
        SH = self.sky_height
        theme = TIME_THEMES[self.time] if color else None
        RESET = theme["reset"] if theme else ""

        # Canvas: each cell is (char, color_prefix)
        canvas = [[" " for _ in range(W)] for _ in range(self.total_height)]
        ccolor = [["" for _ in range(W)] for _ in range(self.total_height)]

        # ── Sky background ───────────────────────────────────────────────
        for row in range(SH):
            frac = row / max(SH - 1, 1)
            if frac < 0.33:
                bg = theme["sky"][0] if theme else ""
            elif frac < 0.66:
                bg = theme["sky"][1] if theme else ""
            else:
                bg = theme["sky"][2] if theme else ""
            for col in range(W):
                canvas[row][col] = " "
                ccolor[row][col] = bg

        # ── Stars ─────────────────────────────────────────────────────────
        if self.time in ("night", "dusk", "dawn"):
            star_count = W * SH // 10
            # More stars at night
            if self.time == "night":
                star_count = int(star_count * 1.5)
            for _ in range(star_count):
                sr = R.randint(0, SH - 4)
                sc = R.randint(0, W - 1)
                canvas[sr][sc] = R.choice(STARS)
                ccolor[sr][sc] = theme["star"] if theme else ""

        # ── Moon ──────────────────────────────────────────────────────────
        if self.time in ("night", "dusk"):
            moon_phase = R.choice(list(MOON_PHASES.keys()))
            moon_char = MOON_PHASES[moon_phase]
            mr = R.randint(1, 3)
            mc = R.randint(W // 5, 4 * W // 5)
            canvas[mr][mc] = moon_char
            ccolor[mr][mc] = theme["moon"] if theme else ""

        # ── Sun ───────────────────────────────────────────────────────────
        if self.time == "day":
            sr = R.randint(1, 3)
            sc = R.randint(W // 3, 2 * W // 3)
            self._place_sun(canvas, ccolor, theme, sr, sc, SH, W)
        elif self.time == "dawn":
            sr = SH - 3
            sc = R.randint(W // 6, W // 3)
            self._place_sun(canvas, ccolor, theme, sr, sc, SH, W)
        elif self.time == "dusk":
            sr = SH - 3
            sc = R.randint(2 * W // 3, 5 * W // 6)
            self._place_sun(canvas, ccolor, theme, sr, sc, SH, W)

        # ── Birds and planes ──────────────────────────────────────────────
        self._place_sky_life(canvas, ccolor, theme, R, SH, W)

        # ── Weather particles ─────────────────────────────────────────────
        self._place_weather(canvas, ccolor, theme, R, SH, W)

        # ── Buildings ─────────────────────────────────────────────────────
        for bx, b in self.buildings:
            self._render_building(canvas, ccolor, theme, bx, b, SH, W)

        # ── Ground ────────────────────────────────────────────────────────
        ground_colors = theme["ground"] if theme else ""
        for col in range(W):
            canvas[SH][col] = GROUND_TOP
            ccolor[SH][col] = ground_colors
            canvas[SH + 1][col] = GROUND_BOT
            ccolor[SH + 1][col] = ground_colors

        # ── Water reflections ────────────────────────────────────────────
        if self.water:
            self._render_water(canvas, ccolor, theme, R, SH, W)

        # ── Render canvas to string ───────────────────────────────────────
        lines = []
        for row in range(self.total_height):
            line = []
            for col in range(W):
                ch = canvas[row][col]
                cc = ccolor[row][col]
                if color and cc:
                    line.append(f"{cc}{ch}{RESET}")
                else:
                    line.append(ch)
            lines.append("".join(line))

        # ── Stats line ────────────────────────────────────────────────────
        stats = self._generate_stats(R)
        if color:
            stats = f"\033[1m\033[36m{stats}{RESET}"
        lines.append(stats)

        return "\n".join(lines)

    def _place_sun(self, canvas, ccolor, theme, sr, sc, SH, W):
        """Place the sun with glow halo."""
        if not theme or not theme.get("sun"):
            return
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                rr, cc = sr + dr, sc + dc
                if 0 <= rr < SH and 0 <= cc < W:
                    canvas[rr][cc] = "·" if (dr, dc) != (0, 0) else "☀"
                    ccolor[rr][cc] = theme["sun"] if theme else ""

    def _place_sky_life(self, canvas, ccolor, theme, R, SH, W):
        """Place birds (day/dawn) or airplanes (night/dusk) in the sky."""
        # Birds: small V-shaped flocks during day and dawn
        if self.time in ("day", "dawn") and theme and theme.get("bird"):
            # 1-3 bird flocks
            num_flocks = R.randint(1, 3)
            for _ in range(num_flocks):
                br = R.randint(1, SH // 2)
                bc = R.randint(2, W - 3)
                bird = R.choice(BIRD_CHARS)
                # Each flock is 2-5 birds in a loose formation
                for j in range(R.randint(2, 5)):
                    offset_r = R.randint(-1, 1)
                    offset_c = R.randint(-2, 2)
                    r, c = br + offset_r, bc + j * 2 + offset_c
                    if 0 <= r < SH and 0 <= c < W:
                        canvas[r][c] = bird
                        ccolor[r][c] = theme["bird"] if theme else ""

        # Airplanes: at night and dusk
        if self.time in ("night", "dusk") and theme and theme.get("plane"):
            if R.random() < 0.4:
                pr = R.randint(0, SH // 3)
                pc = R.randint(W // 4, 3 * W // 4)
                if 0 <= pr < SH and 0 <= pc < W:
                    canvas[pr][pc] = PLANE_CHAR
                    ccolor[pr][pc] = theme["plane"] if theme else ""
                    # Contrail
                    for k in range(1, R.randint(3, 8)):
                        cc = pc - k
                        if 0 <= cc < W and canvas[pr][cc] == " ":
                            canvas[pr][cc] = "·"
                            ccolor[pr][cc] = theme["plane"] if theme else ""

    def _place_weather(self, canvas, ccolor, theme, R, SH, W):
        """Place weather particles (rain, snow, fog, clouds, storm)."""
        if self.weather not in ("rain", "snow", "fog", "cloudy", "storm"):
            return

        densities = {"rain": 12, "snow": 8, "fog": 20, "cloudy": 8, "storm": 15}
        chars_map = {
            "rain": ["·", "˙", "."],
            "snow": ["✻", "❄", "✼", "·"],
            "fog": ["░", "▒", " "],
            "cloudy": ["░", "▒"],
            "storm": ["·", "˙", ".", "⚡"],
        }
        color_key = {
            "rain": "weather_rain",
            "snow": "weather_snow",
            "fog": "weather_fog",
            "cloudy": "weather_cloud",
            "storm": "weather_storm",
        }

        count = W * SH * densities[self.weather] // 100
        for _ in range(count):
            wr = R.randint(0, SH - 1)
            wc = R.randint(0, W - 1)
            ch = R.choice(chars_map[self.weather])
            if ch != " ":
                canvas[wr][wc] = ch
                ccolor[wr][wc] = theme[color_key[self.weather]] if theme else ""

    def _render_building(self, canvas, ccolor, theme, bx, b, SH, W):
        """Render a single building onto the canvas."""
        total_h = b.total_height
        btop = SH - total_h   # top row of building (antenna/spire)
        bbot = SH              # bottom row (ground level)

        for abs_row in range(btop, bbot):
            row = abs_row  # canvas row
            rel = abs_row - btop  # relative row within building

            for cx in range(bx, min(bx + b.width, W)):
                # Antenna rows
                if rel < b.antenna_height:
                    mid = bx + b.width // 2
                    if cx == mid:
                        canvas[row][cx] = "┃"
                        ccolor[row][cx] = theme["bldg_edge"] if theme else ""
                    # else leave sky
                # Spire row
                elif rel == b.antenna_height and b.has_spire:
                    mid = bx + b.width // 2
                    if cx == mid:
                        canvas[row][cx] = "▲"
                        ccolor[row][cx] = theme["bldg"] if theme else ""
                    # else leave sky
                else:
                    # Main body
                    body_row = rel - b.antenna_height - (1 if b.has_spire else 0)

                    # Top row of main body: roof line
                    if body_row == 0:
                        canvas[row][cx] = "▀"
                        ccolor[row][cx] = theme["bldg"] if theme else ""
                    # Bottom row: ground floor
                    elif body_row == b.height - 1:
                        right_edge = min(bx + b.width - 1, W - 1)
                        if cx == bx or cx == right_edge:
                            canvas[row][cx] = b.edge_char
                            ccolor[row][cx] = theme["bldg_edge"] if theme else ""
                        else:
                            canvas[row][cx] = "▄"
                            ccolor[row][cx] = theme["bldg"] if theme else ""
                    # Interior: edges and windows
                    else:
                        right_edge = min(bx + b.width - 1, W - 1)
                        if cx == bx or cx == right_edge:
                            canvas[row][cx] = b.edge_char
                            ccolor[row][cx] = theme["bldg_edge"] if theme else ""
                        else:
                            win_row = body_row
                            win_col = cx - bx - 1
                            wrows = b.windows
                            if 0 <= win_row < len(wrows) and 0 <= win_col < len(wrows[win_row]):
                                wtype = wrows[win_row][win_col]
                                canvas[row][cx] = WINDOW_CHARS[wtype]
                                key = "win_" + wtype
                                ccolor[row][cx] = theme[key] if theme else ""
                            else:
                                canvas[row][cx] = b.body_char
                                ccolor[row][cx] = theme["bldg"] if theme else ""

        # ── Neon sign ──────────────────────────────────────────────────
        if b.has_neon and self.time in ("night", "dusk") and theme and theme.get("neon"):
            neon_row_idx = SH - b.height + 1  # second visible row of building
            if neon_row_idx >= 0 and neon_row_idx < SH:
                # Place neon sign characters across the building width (skip edges)
                neon_color = NEON_COLORS[b.neon_color_idx]
                for cx in range(bx + 1, min(bx + b.width - 1, W - 1)):
                    canvas[neon_row_idx][cx] = b.neon_char
                    ccolor[neon_row_idx][cx] = neon_color

    def _render_water(self, canvas, ccolor, theme, R, SH, W):
        """Render water with building reflections below the ground line."""
        water_start = SH + self.ground_height
        water_color = theme["water"] if theme else ""
        reset = theme["reset"] if theme else ""

        for water_row in range(self.water_height):
            actual_row = water_start + water_row
            if actual_row >= self.total_height:
                break

            # Reflection fading: closer to surface = clearer
            fade = 1.0 - (water_row / max(self.water_height, 1))

            for col in range(W):
                # Source row in sky/building area for reflection
                source_row = SH - 1 - water_row
                if source_row < 0:
                    source_row = 0

                source_char = canvas[source_row][col]
                source_cc = ccolor[source_row][col]

                # Add water ripple effect
                ripple = R.choice(WATER_CHARS) if R.random() < 0.3 else ""

                # Decide whether to show reflection or water
                if source_char not in (" ", "") and R.random() < fade:
                    # Show reflected character with possible ripple overlay
                    if ripple and R.random() < 0.2:
                        canvas[actual_row][col] = ripple
                    else:
                        # Flip some characters for reflection feel
                        canvas[actual_row][col] = source_char
                    ccolor[actual_row][col] = source_cc
                else:
                    # Pure water
                    if R.random() < 0.15:
                        canvas[actual_row][col] = R.choice(WAVE_CHARS)
                    else:
                        canvas[actual_row][col] = R.choice(WATER_CHARS)
                    ccolor[actual_row][col] = water_color

    def _generate_stats(self, R):
        """Generate the stats footer line."""
        city_names = [
            "Novapolis", "Arcadia Heights", "Duskholm", "Aether City",
            "Steelhaven", "Neon Ridge", "Crescent Valley", "Iron Peak",
            "Starfall Metro", "Obsidian Reach", "Lumen Bay", "Thunder Basin",
            "Copper Spire", "Frost Gate", "Solaris Prime", "Echo Mesa",
            "Midnight Citadel", "Chrome District", "Ember Falls", "Skyline Crossing",
            "Vertigo City", "Prism Harbor", "Cobalt Ridge", "Amber District",
            "Obsidian Terrace", "Zenith Park", "Mirage Flats", "Voltage Row",
        ]
        city_name = R.choice(city_names)
        pop = R.randint(80_000, 12_000_000)

        time_emoji = {"dawn": "🌅", "day": "☀️", "dusk": "🌇", "night": "🌙"}
        weather_emoji = {"clear": "✨", "cloudy": "☁️", "rain": "🌧️",
                         "snow": "❄️", "fog": "🌫️", "storm": "⛈️"}

        stats = (
            f"  {city_name}  │  "
            f"{time_emoji.get(self.time, '')} {self.time.title()}  │  "
            f"{weather_emoji.get(self.weather, '')} {self.weather.title()}  │  "
            f"🏢 {len(self.buildings)} buildings  │  "
            f"👥 Pop: {pop:,}"
        )
        if self.water:
            stats += "  │  🌊 Waterfront"
        return stats

    def render_svg(self, filepath):
        """Render the skyline as an SVG file."""
        R = self.rng
        W = self.width
        SH = self.sky_height
        total_h = self.sky_height + self.ground_height + self.water_height

        # SVG dimensions (each char cell = 10x14 pixels)
        cell_w = 10
        cell_h = 14
        svg_w = W * cell_w
        svg_h = (total_h + 1) * cell_h  # +1 for stats

        # Color definitions for time themes (hex colors)
        sky_colors = {
            "night": ["#00005f", "#000087", "#0000af"],
            "dawn":  ["#00005f", "#5f0087", "#ff5f00"],
            "day":   ["#005faf", "#00afff", "#87d7ff"],
            "dusk":  ["#00005f","#5f005f", "#af5f5f"],
        }
        ground_colors_hex = {
            "night": "#080808", "dawn": "#080808",
            "day": "#4e4e4e", "dusk": "#080808",
        }
        water_colors_hex = {
            "night": "#00005f", "dawn": "#5f87af",
            "day": "#00afff", "dusk": "#5f005f",
        }

        sky_hex = sky_colors.get(self.time, ["#00005f", "#000087", "#0000af"])
        ground_hex = ground_colors_hex.get(self.time, "#080808")
        water_hex = water_colors_hex.get(self.time, "#00005f")

        # Build SVG
        lines = []
        lines.append(f'<?xml version="1.0" encoding="UTF-8"?>')
        lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">')

        # Sky gradient
        lines.append(f'<defs>')
        lines.append(f'  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">')
        lines.append(f'    <stop offset="0%" stop-color="{sky_hex[0]}"/>')
        lines.append(f'    <stop offset="50%" stop-color="{sky_hex[1]}"/>')
        lines.append(f'    <stop offset="100%" stop-color="{sky_hex[2]}"/>')
        lines.append(f'  </linearGradient>')
        lines.append(f'</defs>')

        # Sky background
        sky_h_px = SH * cell_h
        lines.append(f'<rect x="0" y="0" width="{svg_w}" height="{sky_h_px}" fill="url(#sky)"/>')

        # Ground
        ground_y = SH * cell_h
        ground_h_px = self.ground_height * cell_h
        lines.append(f'<rect x="0" y="{ground_y}" width="{svg_w}" height="{ground_h_px}" fill="{ground_hex}"/>')

        # Water
        if self.water:
            water_y = (SH + self.ground_height) * cell_h
            water_h_px = self.water_height * cell_h
            lines.append(f'<rect x="0" y="{water_y}" width="{svg_w}" height="{water_h_px}" fill="{water_hex}"/>')

        # Buildings
        building_colors = {
            "night": ("#303030", "#585858"),
            "dawn":  ("#585858", "#8a8a8a"),
            "day":   ("#bcbcbc", "#d0d0d0"),
            "dusk":  ("#585858", "#8a8a8a"),
        }
        bldg_fill, bldg_stroke = building_colors.get(self.time, ("#303030", "#585858"))
        window_lit_color = "#ffaf00" if self.time in ("night", "dusk") else "#87d7ff"

        for bx, b in self.buildings:
            bx_px = bx * cell_w
            bw_px = b.width * cell_w
            # Building body starts at sky_height - b.height
            by_px = (SH - b.height) * cell_h
            bh_px = b.height * cell_h

            lines.append(f'<rect x="{bx_px}" y="{by_px}" width="{bw_px}" height="{bh_px}" '
                        f'fill="{bldg_fill}" stroke="{bldg_stroke}" stroke-width="1"/>')

            # Windows
            win_w = max(cell_w - 4, 3)
            win_h = max(cell_h - 6, 4)
            for wrow in range(b.height - 2):  # skip roof and ground floor
                for wcol in range(b.width - 2):  # skip edges
                    if wrow < len(b.windows) and wcol < len(b.windows[wrow]):
                        wtype = b.windows[wrow][wcol]
                        wx = bx_px + (wcol + 1) * cell_w + 2
                        wy = by_px + (wrow + 1) * cell_h + 3
                        if wtype in ("lit", "bright"):
                            lines.append(f'<rect x="{wx}" y="{wy}" width="{win_w}" height="{win_h}" '
                                        f'fill="{window_lit_color}" opacity="{0.9 if wtype == "lit" else 1.0}"/>')
                        elif wtype == "dim":
                            lines.append(f'<rect x="{wx}" y="{wy}" width="{win_w}" height="{win_h}" '
                                        f'fill="{bldg_fill}" opacity="0.6"/>')

            # Antenna
            if b.has_antenna:
                mid_x = bx_px + (b.width // 2) * cell_w + cell_w // 2
                ant_top = (SH - b.total_height) * cell_h
                lines.append(f'<line x1="{mid_x}" y1="{ant_top}" x2="{mid_x}" y2="{by_px}" '
                            f'stroke="{bldg_stroke}" stroke-width="1"/>')

            # Spire
            if b.has_spire:
                mid_x = bx_px + (b.width // 2) * cell_w + cell_w // 2
                spire_top = (SH - b.antenna_height - 1) * cell_h
                spire_w = max(b.width // 2, 1) * cell_w
                lines.append(f'<polygon points="{mid_x},{spire_top} '
                            f'{mid_x - spire_w//2},{spire_top + cell_h} '
                            f'{mid_x + spire_w//2},{spire_top + cell_h}" '
                            f'fill="{bldg_fill}" stroke="{bldg_stroke}"/>')

        # Stats text
        stats_y = total_h * cell_h + cell_h
        city_names = ["Novapolis", "Arcadia Heights", "Duskholm", "Aether City"]
        city_name = R.choice(city_names)
        stats_text = f"{city_name} | {self.time.title()} | {self.weather.title()} | {len(self.buildings)} buildings"
        lines.append(f'<text x="{svg_w // 2}" y="{stats_y}" text-anchor="middle" '
                    f'font-family="monospace" font-size="12" fill="#87d7ff">{stats_text}</text>')

        lines.append('</svg>')

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            return filepath
        except OSError as e:
            print(f"Error writing SVG file: {e}", file=sys.stderr)
            return None


def list_styles():
    """Return the list of available architectural styles."""
    return ["modern", "art_deco", "gothic", "industrial", "brutalist", "residential", "mixed"]


def main():
    parser = argparse.ArgumentParser(
        description="Procedural City Skyline Generator — creates detailed ASCII city skylines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python skyline.py                          Night skyline, 80 chars wide
  python skyline.py --time day               Sunny daytime cityscape
  python skyline.py --time dawn --weather rain   Dawn with rain
  python skyline.py --style gothic            Gothic architecture city
  python skyline.py --no-color                No ANSI colors
  python skyline.py --width 120               Wide panoramic view
  python skyline.py --seed 42                 Reproducible skyline
  python skyline.py --water                   Waterfront with reflections
  python skyline.py --svg city.svg            Export as SVG
  python skyline.py --save output.txt         Save to file
  python skyline.py --list                    List available styles
        """
    )
    parser.add_argument("-w", "--width", type=int, default=80,
                        help="Width of the skyline (default: 80, range: 20-300)")
    parser.add_argument("-t", "--time", default="night",
                        choices=["dawn", "day", "dusk", "night"],
                        help="Time of day (default: night)")
    parser.add_argument("--weather", default="clear",
                        choices=["clear", "cloudy", "rain", "snow", "fog", "storm"],
                        help="Weather condition (default: clear)")
    parser.add_argument("-s", "--style", default="mixed",
                        choices=list_styles(),
                        help="Architectural style (default: mixed)")
    parser.add_argument("-d", "--density", type=float, default=0.7,
                        help="Building density 0.1-1.0 (default: 0.7)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors")
    parser.add_argument("--water", action="store_true",
                        help="Add waterfront with building reflections")
    parser.add_argument("--svg", metavar="FILE",
                        help="Export skyline as SVG file")
    parser.add_argument("--save", metavar="FILE",
                        help="Save text output to file")
    parser.add_argument("--list", action="store_true",
                        help="List available styles and options")
    parser.add_argument("--version", action="version", version=f"skyline {VERSION}")

    args = parser.parse_args()

    if args.list:
        print("Available architectural styles:")
        descriptions = {
            "modern": "Glass and steel skyscrapers with clean lines",
            "art_deco": "Ornate towers with decorative spires",
            "gothic": "Pointed spires and dramatic architecture",
            "industrial": "Functional blocks and warehouse structures",
            "brutalist": "Heavy concrete slabs and imposing forms",
            "residential": "Small homes with varied rooflines",
            "mixed": "Random mix of all styles (default)",
        }
        for s in list_styles():
            desc = descriptions.get(s, "")
            print(f"  • {s:15s}  {desc}")
        print("\nAvailable times: dawn, day, dusk, night")
        print("Available weather: clear, cloudy, rain, snow, fog, storm")
        print("\nSpecial options:")
        print("  --water    Add waterfront with building reflections")
        print("  --svg FILE Export skyline as SVG")
        print("  --save FILE Save text output to file")
        return

    # Validate width
    if args.width < 20 or args.width > 300:
        parser.error(f"Width must be between 20 and 300, got {args.width}")

    color = not args.no_color

    try:
        city = CityGenerator(
            width=args.width,
            time=args.time,
            weather=args.weather,
            style=args.style,
            density=args.density,
            seed=args.seed,
            water=args.water,
        )
    except ValueError as e:
        parser.error(str(e))
        return

    output = city.render(color=color)

    # Print to stdout
    print()
    print(output)
    print()

    # Save to file if requested
    if args.save:
        try:
            with open(args.save, 'w', encoding='utf-8') as f:
                f.write(output)
                f.write('\n')
            print(f"Saved to {args.save}")
        except OSError as e:
            print(f"Error saving to {args.save}: {e}", file=sys.stderr)

    # Export SVG if requested
    if args.svg:
        result = city.render_svg(args.svg)
        if result:
            print(f"SVG exported to {result}")
        else:
            print("Failed to export SVG", file=sys.stderr)


if __name__ == "__main__":
    main()