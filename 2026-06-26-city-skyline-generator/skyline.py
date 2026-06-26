#!/usr/bin/env python3
"""
Procedural City Skyline Generator
Generates detailed ASCII city skylines with buildings, weather, time-of-day, and more.
"""

import random
import argparse
import sys

# ─── Character Sets ────────────────────────────────────────────────────────────

STARS = "✦·.*+⋆✧"
MOON_PHASES = {"new": "●", "crescent": "☽", "quarter": "◑", "gibbous": "◕", "full": "○"}
WINDOW_CHARS = {"lit": "▣", "dim": "░", "dark": "·", "bright": "✦"}
GROUND_TOP = "▓"
GROUND_BOT = "░"

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
        "reset":     "\033[0m",
    },
}

# ─── Building Class ─────────────────────────────────────────────────────────────

class Building:
    """A single building with height, width, windows, and optional antenna/spire."""

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
        extra = self.antenna_height + (1 if self.has_spire else 0)
        return self.height + extra


# ─── City Generator ────────────────────────────────────────────────────────────

class CityGenerator:
    """Generates a complete city skyline on a canvas."""

    def __init__(self, width=80, time="night", weather="clear", style="mixed",
                 density=0.7, seed=None):
        self.width = width
        self.time = time
        self.weather = weather
        self.style = style
        self.density = max(0.1, min(1.0, density))
        self.rng = random.Random(seed)
        self.seed = seed
        self.sky_height = 14
        self.ground_height = 2
        self.total_height = self.sky_height + self.ground_height

        self.buildings = []
        self._place_buildings()

    def _place_buildings(self):
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
            for _ in range(W * SH // 10):
                sr = R.randint(0, SH - 4)
                sc = R.randint(0, W - 1)
                canvas[sr][sc] = R.choice(STARS)
                ccolor[sr][sc] = theme["star"] if theme else ""

        # ── Moon ──────────────────────────────────────────────────────────
        moon_char = None
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
            # Glow around sun
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    rr, cc = sr + dr, sc + dc
                    if 0 <= rr < SH and 0 <= cc < W:
                        canvas[rr][cc] = "·" if (dr, dc) != (0, 0) else "☀"
                        ccolor[rr][cc] = theme["sun"] if theme else ""
        elif self.time == "dawn":
            sr = SH - 3
            sc = R.randint(W // 6, W // 3)
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    rr, cc = sr + dr, sc + dc
                    if 0 <= rr < SH and 0 <= cc < W:
                        canvas[rr][cc] = "·" if (dr, dc) != (0, 0) else "☀"
                        ccolor[rr][cc] = theme["sun"] if theme else ""
        elif self.time == "dusk":
            sr = SH - 3
            sc = R.randint(2 * W // 3, 5 * W // 6)
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    rr, cc = sr + dr, sc + dc
                    if 0 <= rr < SH and 0 <= cc < W:
                        canvas[rr][cc] = "·" if (dr, dc) != (0, 0) else "☀"
                        ccolor[rr][cc] = theme["sun"] if theme else ""

        # ── Weather particles ─────────────────────────────────────────────
        if self.weather in ("rain", "snow", "fog", "cloudy", "storm"):
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
            for _ in range(W * SH * densities[self.weather] // 100):
                wr = R.randint(0, SH - 1)
                wc = R.randint(0, W - 1)
                ch = R.choice(chars_map[self.weather])
                if ch != " ":
                    canvas[wr][wc] = ch
                    ccolor[wr][wc] = theme[color_key[self.weather]] if theme else ""

        # ── Buildings ─────────────────────────────────────────────────────
        for bx, b in self.buildings:
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
                            if cx == bx or cx == min(bx + b.width - 1, W - 1):
                                canvas[row][cx] = b.edge_char
                                ccolor[row][cx] = theme["bldg_edge"] if theme else ""
                            else:
                                canvas[row][cx] = "▄"
                                ccolor[row][cx] = theme["bldg"] if theme else ""
                        # Interior: edges and windows
                        else:
                            if cx == bx or cx == min(bx + b.width - 1, W - 1):
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

        # ── Ground ────────────────────────────────────────────────────────
        ground_colors = theme["ground"] if theme else ""
        for col in range(W):
            canvas[SH][col] = GROUND_TOP
            ccolor[SH][col] = ground_colors
            canvas[SH + 1][col] = GROUND_BOT
            ccolor[SH + 1][col] = ground_colors

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
        city_names = [
            "Novapolis", "Arcadia Heights", "Duskholm", "Aether City",
            "Steelhaven", "Neon Ridge", "Crescent Valley", "Iron Peak",
            "Starfall Metro", "Obsidian Reach", "Lumen Bay", "Thunder Basin",
            "Copper Spire", "Frost Gate", "Solaris Prime", "Echo Mesa",
            "Midnight Citadel", "Chrome District", "Ember Falls", "Skyline Crossing",
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
        if color:
            stats = f"\033[1m\033[36m{stats}{RESET}"
        lines.append(stats)

        return "\n".join(lines)


def list_styles():
    return ["modern", "art_deco", "gothic", "industrial", "brutalist", "residential", "mixed"]


def main():
    parser = argparse.ArgumentParser(
        description="Procedural City Skyline Generator",
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
  python skyline.py --list                    List available styles
        """
    )
    parser.add_argument("-w", "--width", type=int, default=80,
                        help="Width of the skyline (default: 80)")
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
                        help="Building density 0.0-1.0 (default: 0.7)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors")
    parser.add_argument("--list", action="store_true",
                        help="List available styles and options")
    parser.add_argument("--version", action="version", version="skyline 1.0.0")

    args = parser.parse_args()

    if args.list:
        print("Available architectural styles:")
        for s in list_styles():
            print(f"  • {s}")
        print("\nAvailable times: dawn, day, dusk, night")
        print("Available weather: clear, cloudy, rain, snow, fog, storm")
        return

    color = not args.no_color

    city = CityGenerator(
        width=args.width,
        time=args.time,
        weather=args.weather,
        style=args.style,
        density=max(0.1, min(1.0, args.density)),
        seed=args.seed,
    )

    print()
    print(city.render(color=color))
    print()


if __name__ == "__main__":
    main()