#!/usr/bin/env python3
"""
Procedural Micro-Nation Generator
===================================
Generates complete fictional micro-nations with flags, government,
culture, economy, and diplomatic relations.
"""

import random
import hashlib
import time
import argparse
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional

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

# Different ASCII chars for no-color mode so flag patterns are visible
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

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"


def make_rng(seed=None):
    if seed is None:
        seed = str(time.time())
    return random.Random(hashlib.sha256(seed.encode()).hexdigest())


def pick(rng, lst, n=1):
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
    relations: List[dict] = field(default_factory=list)


class NationGenerator:
    def __init__(self, seed=None):
        self.seed = seed or str(time.time())
        self.rng = make_rng(self.seed)
        self.flag_renderer = FlagRenderer(self.rng)
        self.generated_nations = []

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
        population = rng.randint(127, 8_500_000)
        founding_year = rng.randint(1800, 2024)

        capital_prefix = pick(rng, ["New", "Fort", "Old", "Port", "North", "South", "East", "West", "Mount", "Lake", "Grand", "Little", "Upper", "Lower", ""])
        capital_root = pick(rng, PREFIXES[:20] + ["haven", "holm", "bury", "wick", "ford", "bridge", "castle", "keep", "gate"])
        capital = f"{capital_prefix}{capital_root}" if capital_prefix else capital_root.capitalize()

        exports = pick(rng, EXPORTS, 3)
        industries = pick(rng, INDUSTRIES, 3)
        cultural_events = pick(rng, CULTURES, 3)
        flag_pattern = pick(rng, FLAG_PATTERNS)
        flag_colors = pick(rng, FLAG_COLORS, 3)
        emblem = pick(rng, ["star", "diamond", "circle", "crescent", "cross", "triangle"])

        nation = MicroNation(
            name=name, motto=motto, government=gov, gov_icon=gov_icon,
            population=population, terrain=terrain, capital=capital,
            currency=currency, national_animal=animal, exports=exports,
            industries=industries, cultural_events=cultural_events,
            personality=personality, founding_year=founding_year,
            flag_pattern=flag_pattern, flag_colors=flag_colors,
            emblem=emblem, seed=seed_override or self.seed,
        )
        self.generated_nations.append(nation)
        return nation

    def generate_relations(self, nations=None):
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
        if pop >= 1_000_000:
            return f"{pop / 1_000_000:.1f}M"
        elif pop >= 1_000:
            return f"{pop / 1_000:.1f}K"
        return str(pop)

    def display_nation(self, nation, use_color=True):
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
            # Strip ANSI for width calculation, pad visible chars to 30
            if use_color:
                visible_len = len(re.sub(r'\033\[[0-9;]*m', '', fl))
                pad = 30 - visible_len
                lines.append(f"  │ {fl}{' ' * max(0, pad)} │")
            else:
                lines.append(f"  │ {fl.ljust(30)} │")
        lines.append("  └" + "─" * 32 + "┘")
        lines.append("")

        # Info block
        info = [
            (f"{nation.gov_icon} Government", nation.government),
            ("Population", self.format_population(nation.population)),
            ("Terrain", nation.terrain.capitalize()),
            ("Capital", nation.capital),
            ("Currency", nation.currency),
            ("National Animal", nation.national_animal),
            ("Personality", nation.personality.capitalize()),
            ("Founded", str(nation.founding_year)),
        ]
        for label, value in info:
            lines.append(f"  {C}{label}:{R} {G}{value}{R}")

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

    def to_dict(self, nation):
        return {
            "name": nation.name,
            "motto": nation.motto,
            "government": nation.government,
            "population": nation.population,
            "terrain": nation.terrain,
            "capital": nation.capital,
            "currency": nation.currency,
            "national_animal": nation.national_animal,
            "exports": nation.exports,
            "industries": nation.industries,
            "cultural_events": nation.cultural_events,
            "personality": nation.personality,
            "founding_year": nation.founding_year,
            "flag_pattern": nation.flag_pattern,
            "flag_colors": nation.flag_colors,
            "emblem": nation.emblem,
            "seed": nation.seed,
            "relations": nation.relations,
        }


def main():
    parser = argparse.ArgumentParser(description="Procedural Micro-Nation Generator")
    parser.add_argument("-n", "--nations", type=int, default=5,
                        help="Number of nations to generate")
    parser.add_argument("-s", "--seed", type=str, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--diplomacy", action="store_true",
                        help="Show diplomatic relations between nations")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Save output to file")
    args = parser.parse_args()

    use_color = not args.no_color
    gen = NationGenerator(seed=args.seed)

    nations = []
    for i in range(args.nations):
        seed = f"{args.seed or 'nation'}-{i}" if args.seed else None
        nation = gen.generate(seed_override=seed)
        nations.append(nation)

    if args.diplomacy or args.nations > 1:
        gen.generate_relations(nations)

    if args.json:
        data = [gen.to_dict(n) for n in nations]
        output = json.dumps(data, indent=2)
        print(output)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
        return

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
        with open(args.output, "w") as f:
            f.write("\n".join(output_lines))
        print(f"📄 Output saved to {args.output}")


if __name__ == "__main__":
    main()