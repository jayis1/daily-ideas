#!/usr/bin/env python3
"""
Procedural Micro-Nation Generator
===================================
Generates complete fictional micro-nations with flags, government,
culture, economy, diplomatic relations, national anthems, and more.

Usage:
  python3 micro_nation.py [OPTIONS]

Options:
  -n, --nations NUM    Number of nations to generate (default: 5)
  -s, --seed SEED      Random seed for reproducibility
  --no-color           Disable ANSI color output
  --json               Output as JSON
  --diplomacy           Always show diplomatic relations
  --compact             One-line summary per nation
  --compare             Compare all generated nations side-by-side
  -o, --output FILE    Save output to a file
  --list-TRAIT         List available options (e.g., --list-governments)
  --version            Show version and exit
  -h, --help           Show this help message and exit
"""

import random
import hashlib
import time
import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional

__version__ = "1.2.0"

# ── Data pools ──────────────────────────────────────────────────────────

PREFIXES = [
    "Nov", "Al", "San", "Cor", "Val", "Eld", "Mor", "Bel", "Cas", "Tor",
    "Fen", "Gal", "Ild", "Kyr", "Lyn", "Myr", "Nev", "Ost", "Por", "Rav",
    "Sel", "Thal", "Uld", "Ves", "Wyr", "Xan", "Yrl", "Zeph", "Ash", "Bor",
    "Cal", "Dun", "Esk", "Fal", "Gor", "Hav", "Ir", "Jol", "Kol", "Lor",
]

SUFFIXES = [
    "ia", "land", "burg", "heim", "dor", "ton", "vale", "mar", "grad", "stad",
    "os", "us", "is", "ax", "en", "ar", "on", "ul", "ix", "gard",
    "fell", "mere", "wick", "ford", "more", "dale", "crest", "keep", "holm", "bury",
]

GOVERNMENTS = [
    ("Constitutional Monarchy", "🏛️"),
    ("Democratic Republic", "🗳️"),
    ("Technocratic Directorate", "⚙️"),
    ("Oligarchic Council", "👥"),
    ("Theocratic Dominion", "🕯️"),
    ("Military Junta", "⚔️"),
    ("Anarcho-Syndicalist Commune", "✊"),
    ("Mage-ocracy", "🔮"),
    ("Pirate Republic", "🏴‍☠️"),
    ("Cybernetic Meritocracy", "💻"),
    ("Benevolent Dictatorship", "👑"),
    ("Gerontocracy", "📜"),
    ("Stratocracy", "🛡️"),
    ("Timocracy", "🏆"),
    ("Noocracy", "🧠"),
]

TERRAINS = [
    "volcanic archipelago", "mountainous highlands", "coastal peninsula",
    "river delta", "floating sky-islands", "underground cavern network",
    "dense jungle basin", "frozen tundra plateau", "desert oasis cluster",
    "coral atoll chain", "floating sea platform", "crater caldera",
    "subterranean mushroom forest", "glacial fjord region",
    "sinkhole cavern system", "mangrove swamp islands",
]

CURRENCIES = [
    "Crown", "Sovereign", "Mark", "Guilder", "Ducat", "Krone", "Florin",
    "Taler", "Piece", "Shard", "Lumen", "Drift", "Slate", "Chip",
    "Token", "Credit", "Pulse", "Thread", "Grain", "Spark",
]

CURRENCY_ADJECTIVES = [
    "Golden", "Silver", "Iron", "Crystal", "Shadow", "Ruby", "Storm",
    "Ember", "Frost", "Copper", "Obsidian", "Star", "Jade", "Mist",
]

NATIONAL_ANIMALS = [
    "Phoenix", "Griffin", "Sea Serpent", "Thunder Eagle", "Crystal Fox",
    "Shadow Wolf", "Iron Boar", "Storm Whale", "Ember Salamander",
    "Frost Bear", "Jade Cobra", "Cave Lion", "Sky Ray", "Moss Elk",
    "Obsidian Hawk", "Coral Mantis", "Glacier Owl", "Lava Beetle",
    "Wind Stag", "Tide Dragon",
]

MOTTOS = [
    "From Ashes, We Rise", "Unity Through Diversity", "Strength in Silence",
    "Eternal Vigilance, Enduring Peace", "By Wind and Wave", "Forward Always",
    "Light in Darkness", "Rooted in Stone", "The Tide Returns",
    "Where Thunder Walks", "Forged in Fire", "Beneath the Stars We Stand",
    "Wisdom Over Wealth", "Through Storm, Through Stillness",
    "The Mountain Remembers", "Currents Never Cease", "Iron Will, Gentle Heart",
    "Shadows Reveal Truth", "Tides Shape the Shore", "Echoes Become Legends",
]

EXPORTS = [
    "enchanted timber", "crystal glassware", "spiced salt", "moonsteel",
    "sky-woven silk", "glow-fungus extract", "volcanic ceramics",
    "deep-sea pearls", "thunderstone", "mist-fermented tea", "ironwood",
    "wind-spun wool", "cave-aged cheese", "ember wine", "coral ink",
    "frost fruit preserves", "shadow pepper", "star-ash fertilizer",
    "tidal mechanical parts", "echo-stone tiles",
]

INDUSTRIES = [
    "arcane engineering", "deep-sea mining", "sky farming",
    "crystal cutting", "wind-powered shipping", "underwater viticulture",
    "steam-powered printing", "gravity research", "bioluminescent lighting",
    "cloud harvesting", "geothermal baking", "magnetic levitation transit",
    "resonance music production", "phase-shifting architecture",
    "mycelial construction", "tide-mill milling",
]

CULTURES = [
    "Festival of Floating Lanterns", "Whisper Court debates",
    "Storm Dance ceremony", "Crystal Carving season",
    "Night of the Open Doors", "Tide Singer competitions",
    "Iron Pour ritual", "Sky Market grand bazaar",
    "Echo Chamber meditation", "Root Binding ceremony",
    "Flame Walk initiation", "Deep Song gatherings",
    "Wind Reading festivals", "Stone Balancing contests",
    "Star Mapping expeditions",
]

FLAG_PATTERNS = [
    "horiz_tricolor", "vert_tricolor", "diagonal", "cross",
    "canton", "chevron", "saltire", "barrulets", "quarterly", "bend",
]

COLORS = {
    "red":     "\033[31m",
    "blue":    "\033[34m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "white":   "\033[37m",
    "black":   "\033[30m",
    "cyan":    "\033[36m",
    "magenta": "\033[35m",
    "orange":  "\033[38;5;208m",
    "purple":  "\033[38;5;129m",
}

NO_COLOR_CHARS = {
    "red":     "█",
    "blue":    "▓",
    "green":   "░",
    "yellow":  "▒",
    "white":   "□",
    "black":   "■",
    "cyan":    "◇",
    "magenta": "◆",
    "orange":  "▧",
    "purple":  "▨",
}

FLAG_COLORS = list(COLORS.keys())

RELATION_TYPES = [
    ("Allied", "🤝"),
    ("Friendly", "😊"),
    ("Neutral", "😐"),
    ("Tense", "😤"),
    ("Hostile", "⚔️"),
    ("Trade Partner", "📈"),
    ("Cultural Exchange", "🎭"),
    ("Frozen Relations", "🧊"),
]

PERSONALITIES = [
    "stoic", "warm", "mysterious", "boisterous", "meticulous",
    "whimsical", "pragmatic", "idealistic", "cunning", "serene",
]

# National anthem opening lines (paired with personality)
ANTHEM_OPENINGS = {
    "stoic": [
        "O mountains that guard our eternal rest,",
        "Beneath iron skies we make our stand,",
        "The stone remembers what flesh forgets,",
    ],
    "warm": [
        "Beneath the golden sun we share our bread,",
        "Come, gather near the hearth of home,",
        "Our open doors shall never close,",
    ],
    "mysterious": [
        "In twilight's shadow, secrets bloom,",
        "The mists conceal what eyes can't find,",
        "Whisper the words the wind has carried,",
    ],
    "boisterous": [
        "Raise high the cup, the feast goes on!",
        "Let thunder ring and voices soar,",
        "No quiet night shall claim our spirits,",
    ],
    "meticulous": [
        "By measure true and balance kept,",
        "Each grain of sand is counted here,",
        "The architect of order stands,",
    ],
    "whimsical": [
        "Where dreams dance on the morning dew,",
        "A twist of fate, a turn of chance,",
        "The stars spell out our strangest plans,",
    ],
    "pragmatic": [
        "We build with what the land provides,",
        "No need for crowns when work is done,",
        "The harvest speaks what kings cannot,",
    ],
    "idealistic": [
        "A brighter dawn forever calls,",
        "We dream the world that yet could be,",
        "Beyond the horizon, hope still shines,",
    ],
    "cunning": [
        "The fox knows well which paths are blind,",
        "What shadows hide, we navigate,",
        "Between the lines, our fortune waits,",
    ],
    "serene": [
        "Like water still, we find our peace,",
        "The evening breeze carries no weight,",
        "In silence, truth and beauty meet,",
    ],
}

# Area ranges (sq km) by terrain
TERRAIN_AREAS = {
    "volcanic archipelago": (50, 500),
    "mountainous highlands": (2000, 15000),
    "coastal peninsula": (500, 8000),
    "river delta": (100, 2000),
    "floating sky-islands": (10, 200),
    "underground cavern network": (5, 50),
    "dense jungle basin": (3000, 25000),
    "frozen tundra plateau": (5000, 40000),
    "desert oasis cluster": (50, 500),
    "coral atoll chain": (5, 100),
    "floating sea platform": (1, 20),
    "crater caldera": (100, 800),
    "subterranean mushroom forest": (20, 200),
    "glacial fjord region": (2000, 12000),
    "sinkhole cavern system": (10, 100),
    "mangrove swamp islands": (100, 3000),
}

# Leaders by government type
LEADER_TITLES = {
    "Constitutional Monarchy": ("King", "Queen"),
    "Democratic Republic": ("President", "President"),
    "Technocratic Directorate": ("Director", "Director"),
    "Oligarchic Council": ("Councilor", "Councilor"),
    "Theocratic Dominion": ("High Priest", "High Priestess"),
    "Military Junta": ("General", "General"),
    "Anarcho-Syndicalist Commune": ("Coordinator", "Coordinator"),
    "Mage-ocracy": ("Archmage", "Archmage"),
    "Pirate Republic": ("Captain", "Captain"),
    "Cybernetic Meritocracy": ("Admin", "Admin"),
    "Benevolent Dictatorship": ("Dictator", "Dictator"),
    "Gerontocracy": ("Elder", "Elder"),
    "Stratocracy": ("Marshal", "Marshal"),
    "Timocracy": ("Champion", "Champion"),
    "Noocracy": ("Sage", "Sage"),
}

LEADER_FIRST_NAMES = [
    "Aldric", "Brenna", "Cassius", "Delia", "Elias", "Freya",
    "Gareth", "Helena", "Ivan", "Jasmina", "Kael", "Liora",
    "Magnus", "Nadia", "Orion", "Petra", "Quinn", "Rowena",
    "Soren", "Thalia", "Ulric", "Vera", "Wolfram", "Xena",
    "Yuri", "Zara",
]

LEADER_EPITHETS = [
    "the Bold", "the Wise", "the Steadfast", "the Iron-willed",
    "the Merciful", "the Unyielding", "the Visionary", "the Just",
    "the Wanderer", "the Silent", "the Radiant", "the Swift",
    "the Patient", "the Fierce", "the Enlightened", "the Resolute",
]

NATIONAL_HOLIDAYS = [
    "Founding Day", "Harvest Moon Festival", "Liberation Day",
    "Storm's End Remembrance", "New Dawn Celebration", "Ancestral Vigil",
    "Tide Festival", "Crystal Night", "Iron Week", "Sky Market Opening",
    "Frost's Departure", "Unity Day", "The Great Kindling",
    "Remembrance of Tides", "Starfall Night",
]

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"


def make_rng(seed=None):
    """Create a deterministic random number generator from a seed."""
    if seed is None:
        seed = str(time.time())
    seed = str(seed)
    return random.Random(hashlib.sha256(seed.encode()).hexdigest())


def pick(rng, lst, n=1):
    """Pick n items from a list. If n=1, return a single item."""
    if n == 1:
        return rng.choice(lst)
    return rng.sample(lst, min(n, len(lst)))


# ── Flag Renderer ───────────────────────────────────────────────────────

class FlagRenderer:
    WIDTH = 30
    HEIGHT = 12

    def __init__(self, rng):
        self.rng = rng

    def render(self, pattern=None, flag_colors=None, emblem=None, use_color=True):
        pattern = pattern or pick(self.rng, FLAG_PATTERNS)
        flag_colors = flag_colors or pick(self.rng, FLAG_COLORS, 3)
        while len(flag_colors) < 3:
            flag_colors.append(pick(self.rng, FLAG_COLORS))
        if emblem is None:
            emblem = pick(self.rng, ["star", "diamond", "circle", "crescent", "cross", "triangle"])

        grid = []
        for y in range(self.HEIGHT):
            row = []
            for x in range(self.WIDTH):
                row.append(self._pick_color(pattern, x, y, flag_colors))
            grid.append(row)

        if emblem:
            grid = self._add_emblem(grid, emblem, flag_colors[-1])

        lines = []
        for row in grid:
            line = ""
            for c in row:
                if use_color:
                    line += f"{COLORS[c]}█{RESET}"
                else:
                    line += NO_COLOR_CHARS.get(c, "#")
            lines.append(line)
        return lines

    def _pick_color(self, pattern, x, y, c):
        W, H = self.WIDTH, self.HEIGHT
        if pattern == "horiz_tricolor":
            if y < H // 3: return c[0]
            elif y < 2 * H // 3: return c[1]
            else: return c[2]
        elif pattern == "vert_tricolor":
            if x < W // 3: return c[0]
            elif x < 2 * W // 3: return c[1]
            else: return c[2]
        elif pattern == "diagonal":
            if x + y < (W + H) // 3: return c[0]
            elif x + y < 2 * (W + H) // 3: return c[1]
            else: return c[2]
        elif pattern == "cross":
            if abs(x - W // 2) <= 2 or abs(y - H // 2) <= 1:
                return c[1]
            return c[0] if y < H // 2 else c[2]
        elif pattern == "canton":
            if x < W // 3 and y < H // 2:
                return c[1]
            return c[0] if y < H // 2 else c[2]
        elif pattern == "chevron":
            mid = H // 2
            chev = abs(y - mid) * 2
            if x < W // 4 and x > chev // 2:
                return c[1]
            elif x <= chev // 2:
                return c[0] if y < mid else c[2]
            return c[0] if y < mid else c[2]
        elif pattern == "saltire":
            cx, cy = W // 2, H // 2
            dx, dy = abs(x - cx), abs(y - cy)
            if dx * H <= dy * W + W * 0.15 and dx * H >= dy * W - W * 0.15:
                return c[1]
            return c[0] if (x + y) % 2 == 0 else c[2]
        elif pattern == "barrulets":
            stripe = y % 4
            if stripe < 2: return c[0]
            elif stripe == 2: return c[1]
            else: return c[2]
        elif pattern == "quarterly":
            if x < W // 2 and y < H // 2: return c[0]
            elif x >= W // 2 and y < H // 2: return c[1]
            elif x < W // 2 and y >= H // 2: return c[2]
            else: return c[0]
        elif pattern == "bend":
            if abs(x - y * W // H) <= 3:
                return c[1]
            return c[0] if x > y * W // H else c[2]
        return c[0]

    def _add_emblem(self, grid, emblem, color):
        emblems = {
            "star": [
                "          **          ",
                "         ****         ",
                "        ******        ",
                "   ****************   ",
                "    **************    ",
                "     ************     ",
                "      **********      ",
                "    **************    ",
                "   ****  **  ****   ",
                "  ****    **    ****  ",
                " ***      **      *** ",
                "**        **        **",
            ],
            "diamond": [
                "          **          ",
                "         ****         ",
                "        ******        ",
                "       ********       ",
                "      **********      ",
                "     ************     ",
                "      **********      ",
                "       ********       ",
                "        ******        ",
                "         ****         ",
                "          **          ",
                "                       ",
            ],
            "circle": [
                "        ******        ",
                "      **********     ",
                "     ************    ",
                "    **************   ",
                "    **************   ",
                "    **************   ",
                "    **************   ",
                "    **************   ",
                "     ************    ",
                "      **********     ",
                "        ******        ",
                "                       ",
            ],
            "crescent": [
                "      ********       ",
                "    ************     ",
                "   **************    ",
                "  ***************    ",
                "  ******              ",
                "  ******               ",
                "  ******              ",
                "  ***************    ",
                "   **************    ",
                "    ************     ",
                "      ********       ",
                "                       ",
            ],
            "cross": [
                "         **          ",
                "         **          ",
                "         **          ",
                "         **          ",
                "    **************    ",
                "    **************    ",
                "         **          ",
                "         **          ",
                "         **          ",
                "         **          ",
                "         **          ",
                "                       ",
            ],
            "triangle": [
                "          **          ",
                "         ****         ",
                "        ******        ",
                "       ********       ",
                "      **********      ",
                "     ************     ",
                "    **************    ",
                "   ****************   ",
                "  ******************  ",
                " ********************* ",
                " ********************* ",
                "                       ",
            ],
        }
        overlay = emblems.get(emblem, emblems["star"])
        start_x = (self.WIDTH - 21) // 2
        for i, row in enumerate(overlay):
            if i >= len(grid):
                break
            for j, ch in enumerate(row):
                if ch == '*' and start_x + j < self.WIDTH:
                    grid[i][start_x + j] = color
        return grid


# ── Nation Generator ────────────────────────────────────────────────────

@dataclass
class MicroNation:
    name: str
    motto: str
    government: str
    gov_icon: str
    population: int
    terrain: str
    area_sq_km: float
    capital: str
    currency: str
    national_animal: str
    exports: List[str]
    industries: List[str]
    cultural_events: List[str]
    personality: str
    founding_year: int
    flag_pattern: str
    flag_colors: List[str]
    emblem: str
    seed: str
    leader_name: str = ""
    leader_title: str = ""
    national_holiday: str = ""
    anthem_opening: str = ""
    relations: List[dict] = field(default_factory=list)

    @property
    def population_density(self) -> float:
        """People per sq km."""
        if self.area_sq_km > 0:
            return self.population / self.area_sq_km
        return 0.0


class NationGenerator:
    def __init__(self, seed=None):
        self.seed = seed or str(time.time())
        self.rng = make_rng(self.seed)
        self.flag_renderer = FlagRenderer(self.rng)
        self.generated_nations: List[MicroNation] = []

    def generate(self, seed_override=None):
        rng = make_rng(seed_override or self.seed)

        prefix = pick(rng, PREFIXES)
        suffix = pick(rng, SUFFIXES)
        name = f"{prefix}{suffix}"

        gov, gov_icon = pick(rng, GOVERNMENTS)
        terrain = pick(rng, TERRAINS)
        motto = pick(rng, MOTTOS)
        animal = pick(rng, NATIONAL_ANIMALS)
        personality = pick(rng, PERSONALITIES)
        currency_adj = pick(rng, CURRENCY_ADJECTIVES)
        currency_name = pick(rng, CURRENCIES)
        currency = f"{currency_adj} {currency_name}"
        # Area based on terrain
        area_range = TERRAIN_AREAS.get(terrain, (100, 10000))
        area_sq_km = round(rng.uniform(area_range[0], area_range[1]), 1)

        # Population scaled by area to keep density realistic (max ~5000/km² for city-states)
        max_density = rng.randint(50, 5000)
        min_pop = max(127, int(area_sq_km * 10))
        max_pop = int(area_sq_km * max_density)
        population = rng.randint(min_pop, max(min_pop + 1, max_pop))
        founding_year = rng.randint(1800, 2024)

        capital_prefix = pick(rng, ["New", "Fort", "Old", "Port", "North", "South", "East", "West", "Mount", "Lake", "Grand", "Little", "Upper", "Lower", ""])
        capital_root = pick(rng, PREFIXES[:20] + ["haven", "holm", "bury", "wick", "ford", "bridge", "castle", "keep", "gate"])
        capital = f"{capital_prefix} {capital_root}" if capital_prefix else capital_root.capitalize()

        exports = pick(rng, EXPORTS, 3)
        industries = pick(rng, INDUSTRIES, 3)
        cultural_events = pick(rng, CULTURES, 3)
        flag_pattern = pick(rng, FLAG_PATTERNS)
        flag_colors = pick(rng, FLAG_COLORS, 3)
        emblem = pick(rng, ["star", "diamond", "circle", "crescent", "cross", "triangle"])

        # Leader
        titles = LEADER_TITLES.get(gov, ("Leader", "Leader"))
        leader_title = pick(rng, titles)
        leader_first = pick(rng, LEADER_FIRST_NAMES)
        leader_epithet = pick(rng, LEADER_EPITHETS)
        leader_name = f"{leader_title} {leader_first} {leader_epithet}"

        # National holiday
        national_holiday = pick(rng, NATIONAL_HOLIDAYS)

        # Anthem opening
        anthem_pool = ANTHEM_OPENINGS.get(personality, ANTHEM_OPENINGS["stoic"])
        anthem_opening = pick(rng, anthem_pool)

        nation = MicroNation(
            name=name, motto=motto, government=gov, gov_icon=gov_icon,
            population=population, terrain=terrain, area_sq_km=area_sq_km,
            capital=capital, currency=currency, national_animal=animal,
            exports=exports, industries=industries, cultural_events=cultural_events,
            personality=personality, founding_year=founding_year,
            flag_pattern=flag_pattern, flag_colors=flag_colors,
            emblem=emblem, seed=seed_override or self.seed,
            leader_name=leader_name, leader_title=leader_title,
            national_holiday=national_holiday, anthem_opening=anthem_opening,
        )
        self.generated_nations.append(nation)
        return nation

    def generate_relations(self, nations=None):
        """Generate diplomatic relations between nations."""
        if nations is None:
            nations = self.generated_nations
        for i, nation in enumerate(nations):
            nation.relations = []
            for j, other in enumerate(nations):
                if i == j:
                    continue
                rel_type, rel_icon = pick(self.rng, RELATION_TYPES)
                strength = self.rng.randint(1, 100)
                nation.relations.append({
                    "nation": other.name,
                    "type": rel_type,
                    "icon": rel_icon,
                    "strength": strength,
                })

    def format_population(self, pop):
        """Format population with K/M suffixes."""
        if pop >= 1_000_000:
            return f"{pop / 1_000_000:.1f}M"
        elif pop >= 1_000:
            val = pop / 1_000
            formatted = f"{val:.1f}K"
            # If formatting rounds up to 1000.0K, show as 1.0M instead
            if val >= 999.95:
                return f"{pop / 1_000_000:.1f}M"
            return formatted
        return str(pop)

    def format_area(self, area):
        """Format area with appropriate units."""
        if area >= 1_000_000:
            return f"{area / 1_000_000:.1f}M km²"
        elif area >= 1_000:
            val = area / 1_000
            formatted = f"{val:.1f}K km²"
            # If formatting rounds up to 1000.0K, show as 1.0M instead
            if val >= 999.95:
                return f"{area / 1_000_000:.1f}M km²"
            return formatted
        return f"{area:,.1f} km²"

    def display_nation(self, nation, use_color=True, compact=False):
        """Format a nation for display. If compact=True, output a one-line summary."""
        if compact:
            density = f"{nation.population_density:.0f}/km²" if nation.area_sq_km > 0 else "N/A"
            return (f"{nation.gov_icon} {nation.name} | {nation.government} | "
                    f"Pop: {self.format_population(nation.population)} | "
                    f"Area: {self.format_area(nation.area_sq_km)} | "
                    f"Terrain: {nation.terrain.title()} | "
                    f"Founded: {nation.founding_year}")

        R = RESET if use_color else ""
        B = BOLD if use_color else ""
        D = DIM if use_color else ""
        C = CYAN if use_color else ""
        G = GREEN if use_color else ""
        Y = YELLOW if use_color else ""

        # Render flag as plain lines
        flag_lines = self.flag_renderer.render(
            nation.flag_pattern, nation.flag_colors, nation.emblem, use_color
        )

        # Build sections
        lines = []

        # Header
        title = f"  {nation.gov_icon}  {nation.name.upper()}  {nation.gov_icon}  "
        lines.append(f"  {B}{title:^56}{R}")
        lines.append(f"  {D}\"{nation.motto}\"{R}")
        lines.append("")

        # Flag
        lines.append("  ┌" + "─" * 32 + "┐")
        for fl in flag_lines:
            if use_color:
                visible_len = len(re.sub(r'\033\[[0-9;]*m', '', fl))
                pad = 30 - visible_len
                lines.append(f"  │ {fl}{' ' * max(0, pad)} │")
            else:
                lines.append(f"  │ {fl.ljust(30)} │")
        lines.append("  └" + "─" * 32 + "┘")
        lines.append("")

        # Info block
        density_str = f"{nation.population_density:.0f}/km²" if nation.area_sq_km > 0 else "N/A"
        info = [
            (f"{nation.gov_icon} Government", nation.government),
            ("Population", self.format_population(nation.population)),
            ("Area", self.format_area(nation.area_sq_km)),
            ("Density", density_str),
            ("Terrain", nation.terrain.capitalize()),
            ("Capital", nation.capital),
            ("Leader", nation.leader_name),
            ("Currency", nation.currency),
            ("National Animal", nation.national_animal),
            ("Personality", nation.personality.capitalize()),
            ("Founded", str(nation.founding_year)),
            ("National Holiday", nation.national_holiday),
        ]
        for label, value in info:
            lines.append(f"  {C}{label}:{R} {G}{value}{R}")

        lines.append("")
        lines.append(f"  {B}Anthem:{R} {D}\"{nation.anthem_opening}\"{R}")
        lines.append("")

        # Exports
        lines.append(f"  {B}Exports:{R} {Y}{', '.join(nation.exports)}{R}")
        lines.append(f"  {B}Industries:{R} {Y}{', '.join(nation.industries)}{R}")
        lines.append(f"  {B}Cultural Events:{R}")
        for evt in nation.cultural_events:
            lines.append(f"    {G}• {evt}{R}")

        # Diplomatic relations
        if nation.relations:
            lines.append("")
            lines.append(f"  {B}Diplomatic Relations:{R}")
            for rel in nation.relations:
                bar_len = rel['strength'] // 10
                bar = "█" * bar_len + "░" * (10 - bar_len)
                lines.append(f"    {rel['icon']} {rel['nation']}: {rel['type']} [{bar}] {rel['strength']}/100")

        lines.append("")
        lines.append(f"  {D}Seed: {nation.seed}{R}")

        return "\n".join(lines)

    def display_comparison(self, nations, use_color=True):
        """Display nations side-by-side in a comparison table."""
        if not nations:
            return "No nations to compare."

        R = RESET if use_color else ""
        B = BOLD if use_color else ""
        C = CYAN if use_color else ""
        G = GREEN if use_color else ""
        Y = YELLOW if use_color else ""

        lines = []
        lines.append(f"\n  {B}═══ NATION COMPARISON ═══{R}\n")

        attrs = [
            ("Government", lambda n: f"{n.gov_icon} {n.government}"),
            ("Population", lambda n: n.format_population(n.population) if hasattr(n, 'format_population') else f"{n.population:,}"),
            ("Area", lambda n: f"{n.area_sq_km:,.1f} km²"),
            ("Density", lambda n: f"{n.population_density:.0f}/km²" if n.area_sq_km > 0 else "N/A"),
            ("Terrain", lambda n: n.terrain.title()),
            ("Capital", lambda n: n.capital),
            ("Founded", lambda n: str(n.founding_year)),
            ("Currency", lambda n: n.currency),
            ("Animal", lambda n: n.national_animal),
            ("Personality", lambda n: n.personality.title()),
            ("Holiday", lambda n: n.national_holiday),
        ]

        # Calculate column widths
        name_widths = [len(n.name) for n in nations]
        max_name = max(name_widths) + 2
        attr_width = 14

        # Header
        header = f"  {C}{'Attribute':<14}{R} │ "
        for i, n in enumerate(nations):
            header += f"{B}{n.name:^{max_name}}{R} │ "
        lines.append(header)
        lines.append("  " + "─" * (attr_width + 3 + len(nations) * (max_name + 3)))

        for attr_name, getter in attrs:
            row = f"  {C}{attr_name:<14}{R} │ "
            for n in nations:
                val = getter(n)
                row += f"{G}{val:^{max_name}}{R} │ "
            lines.append(row)

        # Diplomatic relations summary
        if len(nations) > 1:
            lines.append("")
            lines.append(f"  {B}Diplomacy:{R}")
            for i, n in enumerate(nations):
                for rel in n.relations:
                    for j, other in enumerate(nations):
                        if rel['nation'] == other.name:
                            strength_bar = "█" * (rel['strength'] // 10) + "░" * (10 - rel['strength'] // 10)
                            lines.append(f"    {n.name} → {other.name}: {rel['icon']} {rel['type']} [{strength_bar}] {rel['strength']}")

        return "\n".join(lines)

    def to_dict(self, nation):
        """Convert a MicroNation to a dictionary for JSON output."""
        return {
            "name": nation.name,
            "motto": nation.motto,
            "government": nation.government,
            "gov_icon": nation.gov_icon,
            "population": nation.population,
            "area_sq_km": nation.area_sq_km,
            "population_density": round(nation.population_density, 1),
            "terrain": nation.terrain,
            "capital": nation.capital,
            "leader": nation.leader_name,
            "leader_title": nation.leader_title,
            "currency": nation.currency,
            "national_animal": nation.national_animal,
            "exports": nation.exports,
            "industries": nation.industries,
            "cultural_events": nation.cultural_events,
            "personality": nation.personality,
            "founding_year": nation.founding_year,
            "national_holiday": nation.national_holiday,
            "anthem_opening": nation.anthem_opening,
            "flag_pattern": nation.flag_pattern,
            "flag_colors": nation.flag_colors,
            "emblem": nation.emblem,
            "seed": nation.seed,
            "relations": nation.relations,
        }


def list_trait(trait_name):
    """Print available options for a given trait category."""
    trait_map = {
        "governments": ("Governments", [f"{icon} {name}" for name, icon in GOVERNMENTS]),
        "terrains": ("Terrains", TERRAINS),
        "currencies": ("Currencies (adjective + name, randomly combined)",
            [f"Adjectives: {', '.join(CURRENCY_ADJECTIVES)}",
             f"Names: {', '.join(CURRENCIES)}"]),
        "animals": ("National Animals", NATIONAL_ANIMALS),
        "mottos": ("Mottos", MOTTOS),
        "exports": ("Exports", EXPORTS),
        "industries": ("Industries", INDUSTRIES),
        "cultures": ("Cultural Events", CULTURES),
        "personalities": ("Personalities", PERSONALITIES),
        "patterns": ("Flag Patterns", FLAG_PATTERNS),
        "colors": ("Flag Colors", FLAG_COLORS),
        "emblems": ("Flag Emblems", ["star", "diamond", "circle", "crescent", "cross", "triangle"]),
    }

    key = trait_name.lower().replace("--", "").replace("_", "").replace("-", "")
    if key in trait_map:
        title, items = trait_map[key]
        print(f"\n{BOLD}{title}:{RESET}")
        for item in items:
            print(f"  • {item}")
        print(f"\n  ({len(items)} options)")
    else:
        print(f"Unknown trait: {trait_name}")
        print(f"Available: {', '.join(trait_map.keys())}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Procedural Micro-Nation Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("-n", "--nations", type=int, default=5,
                        help="Number of nations to generate (default: 5)")
    parser.add_argument("-s", "--seed", type=str, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--diplomacy", action="store_true",
                        help="Always show diplomatic relations between nations")
    parser.add_argument("--compact", action="store_true",
                        help="One-line summary per nation")
    parser.add_argument("--compare", action="store_true",
                        help="Compare all generated nations side-by-side")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Save output to a file")
    parser.add_argument("--version", action="version",
                        version=f"micro-nation-generator {__version__}")

    # List trait options
    for trait in ["governments", "terrains", "currencies", "animals", "mottos",
                   "exports", "industries", "cultures", "personalities",
                   "patterns", "colors", "emblems"]:
        parser.add_argument(f"--list-{trait}", action="store_true",
                            help=f"List available {trait} and exit")

    args = parser.parse_args()

    # Handle --list flags
    for trait in ["governments", "terrains", "currencies", "animals", "mottos",
                   "exports", "industries", "cultures", "personalities",
                   "patterns", "colors", "emblems"]:
        attr = f"list_{trait}"
        if hasattr(args, attr.replace("-", "_")):
            flag_val = getattr(args, attr.replace("-", "_"))
        else:
            flag_val = getattr(args, f"list_{trait.replace('-', '_')}", False)
        if flag_val:
            list_trait(trait)
            return

    # Validate --nations
    if args.nations < 1:
        print("Error: --nations must be at least 1.", file=sys.stderr)
        sys.exit(1)
    if args.nations > 50:
        print("Warning: Generating more than 50 nations may produce a lot of output.", file=sys.stderr)

    use_color = not args.no_color
    gen = NationGenerator(seed=args.seed)

    nations = []
    for i in range(args.nations):
        if args.seed:
            seed = f"{args.seed}-{i}"
        else:
            seed = f"nation-{i}-{time.time()}"
        nation = gen.generate(seed_override=seed)
        nations.append(nation)

    # Always generate relations if more than 1 nation or --diplomacy flag
    if args.diplomacy or args.nations > 1:
        gen.generate_relations(nations)

    # JSON output
    if args.json:
        data = [gen.to_dict(n) for n in nations]
        output = json.dumps(data, indent=2, ensure_ascii=False)
        print(output)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"\n📄 Output saved to {args.output}", file=sys.stderr)
        return

    # Compact output
    if args.compact:
        for nation in nations:
            print(gen.display_nation(nation, use_color=use_color, compact=True))
        if args.seed:
            print(f"\n🌱 Seed: {args.seed}")
        if args.output:
            lines = [gen.display_nation(n, use_color=False, compact=True) for n in nations]
            if args.seed:
                lines.append(f"\nSeed: {args.seed}")
            with open(args.output, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"\n📄 Output saved to {args.output}", file=sys.stderr)
        return

    # Comparison output
    if args.compare:
        text = gen.display_comparison(nations, use_color=use_color)
        print(text)
        if args.output:
            text_nocolor = gen.display_comparison(nations, use_color=False)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text_nocolor)
            print(f"\n📄 Output saved to {args.output}", file=sys.stderr)
        return

    # Full display output
    for nation in nations:
        print()
        print(gen.display_nation(nation, use_color=use_color))

    print(f"\n🎲 Generated {len(nations)} micro-nation(s)")
    if args.seed:
        print(f"🌱 Seed: {args.seed}")

    if args.output:
        output_lines = []
        for nation in nations:
            output_lines.append(gen.display_nation(nation, use_color=False))
            output_lines.append("")
        with open(args.output, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
        print(f"📄 Output saved to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()