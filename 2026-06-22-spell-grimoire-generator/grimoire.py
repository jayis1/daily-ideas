#!/usr/bin/env python3
"""
Procedural Spell Grimoire Generator
=====================================
Generates beautifully formatted grimoire pages for fantasy RPG spells
with procedural names, ASCII art, incantations, reagents, and metadata.

Version: 2.0.0
"""

import random
import math
import argparse
import json
import sys
import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict

__version__ = "2.0.0"

# ──────────────────────────────────────────────
# Data pools for procedural generation
# ──────────────────────────────────────────────

SCHOOL_COLORS = {
    "Evocation": "\033[38;5;196m",
    "Necromancy": "\033[38;5;99m",
    "Enchantment": "\033[38;5;213m",
    "Illusion": "\033[38;5;81m",
    "Conjuration": "\033[38;5;220m",
    "Abjuration": "\033[38;5;156m",
    "Divination": "\033[38;5;183m",
    "Transmutation": "\033[38;5;208m",
}

SCHOOLS = list(SCHOOL_COLORS.keys())

SCHOOL_DESCRIPTIONS = {
    "Evocation": "Spells that channel raw magical energy into destructive or protective force.",
    "Necromancy": "Spells that manipulate the forces of life, death, and undeath.",
    "Enchantment": "Spells that affect the minds of others, influencing or controlling them.",
    "Illusion": "Spells that deceive the senses or create false perceptions.",
    "Conjuration": "Spells that transport creatures or objects from elsewhere.",
    "Abjuration": "Spells that protect, ward, or dispel other magical effects.",
    "Divination": "Spells that reveal hidden knowledge or foretell the future.",
    "Transmutation": "Spells that change the physical properties of creatures or objects.",
}

# Rarity system: name, display color, and weight for random selection
RARITIES = {
    "Common":    {"color": "\033[37m",    "weight": 40},
    "Uncommon":  {"color": "\033[32m",    "weight": 30},
    "Rare":      {"color": "\033[34m",    "weight": 18},
    "Very Rare": {"color": "\033[35m",    "weight": 9},
    "Legendary": {"color": "\033[38;5;220m", "weight": 3},
}

RARITY_LEVEL_MODIFIERS = {
    "Common":    (-1, 3),    # levels 0-2 bias
    "Uncommon":  (1, 4),     # levels 1-3 bias
    "Rare":      (3, 6),     # levels 3-5 bias
    "Very Rare": (5, 8),     # levels 5-7 bias
    "Legendary": (7, 9),    # levels 7-9 bias
}

PREFIXES = [
    "Abyssal", "Arcane", "Astral", "Azura's", "Baleful", "Blazing", "Cerulean",
    "Chrono-", "Crystalline", "Cursed", "Dark", "Dawn's", "Death's", "Dire",
    "Ebon", "Echoing", "Elder", "Ember", "Ethereal", "Fey", "Frost",
    "Galactic", "Gloom", "Golden", "Hallowed", "Harmonic", "Hollow",
    "Ignis", "Iron", "Ivory", "Lunar", "Magma", "Midnight", "Nether",
    "Obsidian", "Omniscient", "Phantom", "Primal", "Radiant", "Runic",
    "Sacred", "Shadow", "Silver", "Solar", "Spectral", "Storm",
    "Tempest", "Twilight", "Umbral", "Vengeful", "Void", "Wailing",
    "Whispering", "Wicked", "Wild", "Winter's", "Withering", "Zealous",
]

ROOTS = {
    "Evocation": [
        "Bolt", "Burst", "Cascade", "Cascade", "Eruption", "Fireball",
        "Fury", "Inferno", "Lance", "Nova", "Pyre", "Ray", "Scorch",
        "Strike", "Torrent", "Wrath",
    ],
    "Necromancy": [
        "Blight", "Chill", "Command", "Curse", "Drain", "Grasp", "Grave",
        "Howl", "Plague", "Raise", "Reap", "Shroud", "Wail", "Wither",
        "Wraith", "Crypt",
    ],
    "Enchantment": [
        "Befuddle", "Berserk", "Bewitch", "Bind", "Charm", "Command",
        "Compel", "Dominate", "Entrance", "Fascinate", "Geas", "Hold",
        "Inspire", "Lull", "Mesmerize", "Soothe",
    ],
    "Illusion": [
        "Blur", "Cloak", "Disguise", "Dream", "Figment", "Guise",
        "Hallucination", "Haze", "Mirage", "Phantasm", "Phantom",
        "Shadow", "Shimmer", "Veil", "Vision", "Whisper",
    ],
    "Conjuration": [
        "Beckon", "Call", "Conjure", "Evoke", "Gate", "Invoke",
        "Manifest", "Planar", "Portal", "Raise", "Summon", "Teleport",
        "Warp", "Call", "Evoke", "Gate",
    ],
    "Abjuration": [
        "Aegis", "Banish", "Bar", "Circle", "Cleanse", "Counterspell",
        "Dispel", "Glyph", "Guard", "Purge", "Sanctuary", "Seal",
        "Shield", "Ward", "Dismiss", "Nullify",
    ],
    "Divination": [
        "Augury", "Clairvoyance", "Commune", "Divine", "Foresight",
        "Glimpse", "Ken", "Locate", "Oracle", "Precognize", "Scry",
        "See", "Sight", "Tongues", "Truesight", "Visions",
    ],
    "Transmutation": [
        "Alter", "Animate", "Change", "Disintegrate", "Enhance",
        "Flesh", "Growth", "Mutate", "Polymorph", "Reduce", "Shape",
        "Shift", "Shrink", "Stone", "Transform", "Resize",
    ],
}

CASTING_TIMES = [
    "1 action", "1 bonus action", "1 reaction", "1 minute",
    "10 minutes", "1 hour", "8 hours", "24 hours",
]

RANGES = [
    "Self", "Touch", "5 feet", "10 feet", "30 feet", "60 feet",
    "90 feet", "120 feet", "300 feet", "1 mile", "Sight",
]

DURATIONS = [
    "Instantaneous", "1 round", "1 minute", "10 minutes",
    "1 hour", "8 hours", "24 hours", "Concentration, up to 1 minute",
    "Concentration, up to 10 minutes", "Concentration, up to 1 hour",
    "Until dispelled", "Until the next dawn",
]

REAGENTS = [
    "a pinch of sulfur", "crushed moonstone", "a drop of blood", "a feather from an owl",
    "a sliver of obsidian", "melted candle wax", "a sprig of wolfsbane",
    "powdered amethyst", "a vial of seawater", "a shard of mirror",
    "dried nightshade", "a copper coin", "a length of silver thread",
    "a piece of parchment with a name", "crushed pearl", "a drop of mercury",
    "a tiny hourglass", "a magnetized needle", "a bell without a clapper",
    "a bone from a black cat", "hemlock extract", "a cobweb from a crypt",
    "frost from the first frost", "a whisper trapped in amber",
    "petrified dragon scale", "a lock of elven hair",
    "ground stardust", "tears of a will-o'-wisp",
    "a splinter from a gallows", "ash from a funeral pyre",
]

VERBAL_COMPONENTS = [
    "the caster must shout the name of a forgotten god",
    "the incantation must be whispered backwards",
    "the caster must speak in an ancient tongue",
    "the words must be sung in a minor key",
    "the caster must chant rhythmically for the full duration",
    "the spell requires a spoken confession of a secret",
    "the caster must recite the lineage of a celestial being",
    "the words must be spoken with absolute conviction",
]

SOMATIC_COMPONENTS = [
    "a precise five-fingered gesture ending in a snap",
    "tracing a sigil in the air with one finger",
    "both hands must weave in counterpoint patterns",
    "the caster must draw a circle upon the ground",
    "the gesture requires perfectly steady hands",
    "the caster makes a beckoning motion with their off-hand",
    "both palms must face the target simultaneously",
    "the sign must be drawn with a finger dipped in ink",
]

EFFECT_TEMPLATES = {
    "Evocation": [
        "Deals {dice}d{sides} {damage_type} damage in a {area} radius.",
        "A beam of {damage_type} energy strikes the target for {dice}d{sides} damage.",
        "Releases a {area}-foot cone of {damage_type} dealing {dice}d{sides} damage.",
        "{dice}d{sides} {damage_type} damage in a {area}-foot sphere centered on self.",
    ],
    "Necromancy": [
        "Drains {dice}d{sides} hit points from the target, healing the caster by half.",
        "Animates {count_undead_servant} for {duration}, each with {hp} HP.",
        "Target must make a WIS save or take {dice}d{sides} necrotic damage and be frightened.",
        "Creates a {area}-foot zone of negative energy. Living creatures take {dice}d{sides} damage.",
    ],
    "Enchantment": [
        "Target must make a WIS save or become {condition} for {duration}.",
        "Up to {count_creature_become} {condition} for {duration}.",
        "Target creature regards the caster as a trusted ally for {duration}.",
        "The caster can issue a {count}-word command that the target must follow.",
    ],
    "Illusion": [
        "Creates a {area}-foot illusory {illusion} that lasts for {duration}.",
        "The caster becomes invisible for {duration} or until they attack.",
        "Creates a {area}-foot zone where all sounds are muffled for {duration}.",
        "Target sees a terrifying phantasm; WIS save or take {dice}d{sides} psychic damage.",
    ],
    "Conjuration": [
        "Summons {count_creature_summoned} for {duration}.",
        "Opens a portal to {plane} lasting {duration}.",
        "Teleports the caster and up to {count_ally} to a location within {area} miles.",
        "Conjures a {area}-foot dome of {material_to} lasting {duration_short}.",
    ],
    "Abjuration": [
        "Creates a {area}-foot radius anti-magic field for {duration}.",
        "Grants {count_creature_resistance} resistance to {damage_type} for {duration}.",
        "Dispels all magical effects of level {level} or lower in a {area}-foot radius.",
        "Creates a magical barrier with {hp} HP that lasts for {duration} or until destroyed.",
    ],
    "Divination": [
        "Reveals the location of {count_hidden_object} within {area} feet.",
        "The caster receives a vision of events up to {count_day} in the future.",
        "For {duration}, the caster can see through walls and illusions within {area} feet.",
        "Answers {count_question} about the future with 90% accuracy.",
    ],
    "Transmutation": [
        "Transforms {area} cubic feet of {material_from} into {material_to} for {duration}.",
        "Target creature grows to {size}x their size for {duration}.",
        "Target creature shrinks to 1/{size} their size for {duration}.",
        "For {duration}, the caster gains the ability to {ability}.",
    ],
}

DAMAGE_TYPES = [
    "acid", "bludgeoning", "cold", "fire", "force", "lightning",
    "necrotic", "piercing", "poison", "psychic", "radiant", "slashing", "thunder",
]

CONDITIONS = [
    "charmed", "frightened", "paralyzed", "stunned", "confused",
    "incapacitated", "restrained", "blinded", "deafened",
]

ILLUSION_THINGS = [
    "castle", "dragon", "army", "forest", "wall", "pit",
    "bridge", "treasury", "portal", "monster",
]

CREATURE_TYPES = [
    "elemental", "fiend", "celestial", "fey", "construct", "beast",
]

PLANES = [
    "the Elemental Plane of Fire", "the Shadowfell", "the Feywild",
    "the Astral Plane", "the Abyss", "Mount Celestia",
    "Limbo", "Mechanus", "the Far Realm",
]

MATERIALS_FROM = ["stone", "wood", "water", "earth", "air", "flesh", "iron"]
MATERIALS_TO = ["gold", "glass", "wine", "crystal", "mist", "marble", "silver"]

SIZES = [2, 3, 4, 5, 8, 10, 16]

ABILITIES = [
    "fly at 60 feet per round", "breathe underwater",
    "climb walls like a spider", "phase through solid matter",
    "see in complete darkness", "communicate telepathically within 60 feet",
]

SPELL_LEVELS = ["Cantrip", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"]

BACKSTORY_TEMPLATES = [
    "This spell was first inscribed on the walls of the Sunken Temple of {temple}, "
    "discovered by the archmage {archmage} during the {era}. It is said that casting it "
    "under a full moon amplifies its power twofold.",

    "Legend holds that {archmage} devised this spell during the {era} to combat the "
    "invading {enemy} hordes. The original scroll, written in {language}, is preserved "
    "in the Grand Library of {city}.",

    "The origins of this spell are lost to time, but the mad sorcerer {archmage} is "
    "credited with its rediscovery during the {era}. It requires a clear mind and "
    "steady hand; even minor mispronunciations have been known to have catastrophic results.",

    "Found among the personal effects of the lich {archmage} after the Siege of "
    "{city}, this spell carries a faint curse. Those who learn it report hearing "
    "whispers from {plane} during the casting.",

    "This spell was a closely guarded secret of the Order of the {order}, passed "
    "down from master to apprentice during the {era}. {archmage} broke their oath "
    "by recording it in the Codex of {city}.",

    "A wandering sage named {archmage} is said to have received this spell in a vision "
    "during the {era}. It was later inscribed on a tablet of {material} in the ruins of "
    "{city}, where it lay hidden for centuries until the Order of the {order} unearthed it.",

    "The Council of {city} outlawed this spell during the {era} after {archmage} used it "
    "to devastating effect against the {enemy} invasion. Copies were ordered destroyed, "
    "but a single parchment survived in the archives of the Temple of {temple}.",
]

TEMPLES = [
    "Ashenmoor", "Blackspire", "Crystalfall", "Dawnfire", "Ebonhollow",
    "Frostveil", "Gloomreach", "Hollowgate", "Ironveil", "Shadowfen",
]

ARCHMAGES = [
    "Valdris the Unbroken", "Seraphina Moonshadow", "Thalric Ironweave",
    "Lysara of the Pale Court", "Kaelen Stormborn", "Morvaine Duskhollow",
    "Isolde the Ashen", "Ravendawn", "Zephriel the Blind", "Nimue Frostheart",
]

ERAS = [
    "Age of Ashes", "Second Dawn", "War of the Silver Throne",
    "Long Night", "Age of Wonders", "Iron Collapse",
    "Drakefall Era", "Reign of the Pale King", "Third Ascendancy",
]

ENEMIES = [
    "orc", "demonic", "undead", "fey", "aberrant", "draconic", "elemental",
]

LANGUAGES = [
    "Draconic", "Infernal", "Celestial", "Deep Speech", "Sylvan", "Primordial",
]

CITIES = [
    "Thornwall", "Everspire", "Goldhaven", "Mistral", "Ashenmere",
    "Silverreach", "Starfall", "Wraithkeep", "Emberford", "Duskholm",
]

ORDERS = [
    "Silver Flame", "Crimson Eye", "Ebon Star", "Golden Wand",
    "Twilight Watch", "Crystal Dawn",
]

MATERIALS_TABLET = ["obsidian", "granite", "crystal", "adamantine", "iron", "marble"]

# ──────────────────────────────────────────────
# Incantation generation
# ──────────────────────────────────────────────

INCANTATION_PREFIXES = [
    "O", "By", "In", "Through", "From", "With", "By the power of",
    "I call upon", "Hear me, O", "Awaken, O",
]

INCANTATION_SUBJECTS = {
    "Evocation": ["flame eternal", "storm unending", "light primordial", "fury of the heavens"],
    "Necromancy": ["veil of death", "shadow beyond", "cold grave", "dark beyond life"],
    "Enchantment": ["mind unbound", "will of the sovereign", "chain of thought", "dream unforgotten"],
    "Illusion": ["mirror of dreams", "veil of masks", "shimmer unmade", "phantom echo"],
    "Conjuration": ["gate unbarred", "bridge between worlds", "door unseen", "call across the void"],
    "Abjuration": ["shield unbroken", "ward of ages", "circle sealed", "light that guards"],
    "Divination": ["eye of truth", "sight beyond sight", "star that knows", "voice of the oracle"],
    "Transmutation": ["forge of change", "wheel of becoming", "thread re-woven", "shape unmade new"],
}

INCANTATION_VERBS = [
    "arise", "awaken", "become", "bend", "break", "burn", "come forth",
    "consuming", "darken", "descend", "endure", "forsake", "gather",
    "illuminate", "open", "rend", "reveal", "rise", "shatter", "shine",
    "speak", "stand", "sunder", "surge", "transform", "unmake", "waken",
]

INCANTATION_ENDINGS = [
    "so it is spoken, so it shall be!",
    "by my will, let it be done!",
    "as the stars have witnessed!",
    "by shadow and starlight!",
    "let the world tremble!",
    "now and unto the ending of days!",
    "I command thee!",
    "by the ancient compact!",
    "in the name of the forgotten!",
    "by the pact of the first mages!",
]


def generate_incantation(school: str) -> str:
    """Generate a ritual incantation for the spell."""
    prefix = random.choice(INCANTATION_PREFIXES)
    subject = random.choice(INCANTATION_SUBJECTS[school])
    verbs = random.sample(INCANTATION_VERBS, k=random.randint(2, 4))
    ending = random.choice(INCANTATION_ENDINGS)
    verb_str = ", ".join(verbs[:-1]) + " and " + verbs[-1]
    return f'"{prefix} {subject}, {verb_str} — {ending}"'


# ──────────────────────────────────────────────
# ASCII Art generation
# ──────────────────────────────────────────────

def generate_sigil(school: str, level: int, width: int = 21, height: int = 11) -> List[str]:
    """Generate a procedural arcane sigil based on school and level.

    Uses a deterministic seed derived from school and level so the same
    school+level always produces the same sigil. The global random state
    is saved and restored to avoid side effects.
    """
    # Save and restore random state so we don't disrupt other generation
    state = random.getstate()
    random.seed(hash(school) + level * 137)

    lines = []
    center_x = width // 2
    center_y = height // 2

    grid = [[" " for _ in range(width)] for _ in range(height)]

    # Draw concentric circles
    for radius in [3, 5]:
        for angle_deg in range(360):
            angle = math.radians(angle_deg)
            x = center_x + int(radius * math.cos(angle))
            y = center_y + int(radius * math.sin(angle) * 0.5)  # squish vertically
            if 0 <= x < width and 0 <= y < height:
                grid[y][x] = "·"

    # Draw school-specific symbols
    school_symbols = {
        "Evocation": [("*", (0, -4)), ("⚡", (0, 0)), ("*", (0, 4)),
                      ("|", (0, -3)), ("|", (0, 3)), ("+", (-2, -1)),
                      ("+", (2, -1)), ("+", (-2, 1)), ("+", (2, 1))],
        "Necromancy": [("☠", (0, 0)), ("○", (0, -3)), ("○", (0, 3)),
                       ("|", (0, -2)), ("|", (0, 2)),
                       ("◠", (-2, 0)), ("◡", (2, 0))],
        "Enchantment": [("♡", (0, 0)), ("~", (0, -3)), ("~", (0, 3)),
                        ("✧", (-3, 0)), ("✧", (3, 0))],
        "Illusion": [("◈", (0, 0)), ("░", (-2, -1)), ("░", (2, 1)),
                     ("▒", (-2, 1)), ("▒", (2, -1)),
                     ("~", (0, -3)), ("~", (0, 3))],
        "Conjuration": [("◇", (0, 0)), ("◇", (-3, -2)), ("◇", (3, -2)),
                        ("◇", (-3, 2)), ("◇", (3, 2)),
                        ("┼", (0, -3)), ("┼", (0, 3))],
        "Abjuration": [("◆", (0, 0)), ("◆", (-3, 0)), ("◆", (3, 0)),
                       ("◆", (0, -3)), ("◆", (0, 3)),
                       ("-", (-2, -1)), ("-", (2, -1)),
                       ("-", (-2, 1)), ("-", (2, 1))],
        "Divination": [("◉", (0, 0)), ("👁", (0, -3)), ("☽", (-3, 0)),
                       ("✦", (3, 0)), ("─", (0, 3))],
        "Transmutation": [("∞", (0, 0)), ("▲", (0, -3)), ("▼", (0, 3)),
                          ("◄", (-3, 0)), ("►", (3, 0)),
                          ("⟳", (0, -1))],
    }

    symbols = school_symbols.get(school, [("✦", (0, 0))])
    for char, (dx, dy) in symbols:
        sx = center_x + dx
        sy = center_y + dy
        if 0 <= sx < width and 0 <= sy < height:
            grid[sy][sx] = char

    # Add level-based runic marks
    for i in range(level):
        angle = math.radians(i * (360 // max(level, 1)) + 90)
        r = 7
        rx = center_x + int(r * math.cos(angle))
        ry = center_y + int(r * math.sin(angle) * 0.5)
        rune_chars = "ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛇᛈᛉᛊᛏᛒᛖᛗᛚᛝᛟ"
        if 0 <= rx < width and 0 <= ry < height:
            grid[ry][rx] = rune_chars[i % len(rune_chars)]

    for row in grid:
        lines.append("".join(row))

    random.setstate(state)  # Restore random state
    return lines


def generate_border(width: int, school: str) -> str:
    """Generate a decorative border line."""
    state = random.getstate()
    random.seed(hash(school) + 42)
    motifs = {
        "Evocation": ("═", "⚡", "◆"),
        "Necromancy": ("─", "☠", "◈"),
        "Enchantment": ("~", "♡", "✧"),
        "Illusion": ("┄", "◈", "░"),
        "Conjuration": ("═", "◇", "✦"),
        "Abjuration": ("═", "◆", "✚"),
        "Divination": ("─", "◉", "☽"),
        "Transmutation": ("─", "∞", "▲"),
    }
    fill, motif, corner = motifs.get(school, ("─", "✦", "✦"))
    mid = width - 4
    pattern = f"  {corner} "
    pattern += f" {fill}{motif}{fill} " * (mid // 4)
    pattern = pattern[:mid]
    pattern += f" {corner}"
    random.setstate(state)
    return pattern


def generate_spell_diagram(school: str, level: int) -> List[str]:
    """Generate a procedural geometric spell diagram.

    Saves and restores random state to avoid side effects.
    """
    state = random.getstate()
    random.seed(hash(school) * 1000 + level * 7 + 999)

    lines = []
    width = 35
    height = 13
    center_x = width // 2
    center_y = height // 2

    grid = [[" " for _ in range(width)] for _ in range(height)]

    # Base circle
    radius = 5
    for angle_deg in range(360):
        angle = math.radians(angle_deg)
        x = center_x + int(radius * math.cos(angle))
        y = center_y + int(radius * math.sin(angle) * 0.55)
        if 0 <= x < width and 0 <= y < height:
            grid[y][x] = "○" if angle_deg % 30 == 0 else "·"

    # Inner geometric pattern based on level
    sides = min(level + 2, 8)
    for i in range(sides):
        angle1 = math.radians(i * (360 // sides) - 90)
        angle2 = math.radians(((i + 1) % sides) * (360 // sides) - 90)
        r = radius - 2
        x1 = center_x + int(r * math.cos(angle1))
        y1 = center_y + int(r * math.sin(angle1) * 0.55)
        x2 = center_x + int(r * math.cos(angle2))
        y2 = center_y + int(r * math.sin(angle2) * 0.55)

        # Draw line between points (simple approach)
        steps = max(abs(x2 - x1), abs(y2 - y1), 1)
        for s in range(steps + 1):
            t = s / max(steps, 1)
            lx = int(x1 + t * (x2 - x1))
            ly = int(y1 + t * (y2 - y1))
            if 0 <= lx < width and 0 <= ly < height:
                if grid[ly][lx] == " ":
                    grid[ly][lx] = "─" if abs(y2 - y1) < abs(x2 - x1) else "│"

        # Mark vertices
        if 0 <= x1 < width and 0 <= y1 < height:
            grid[y1][x1] = "✦"

    # Add connection lines to center (star pattern for higher levels)
    if level >= 3:
        for i in range(sides):
            angle = math.radians(i * (360 // sides) - 90)
            r = radius - 2
            vx = center_x + int(r * math.cos(angle))
            vy = center_y + int(r * math.sin(angle) * 0.55)
            # Connect opposite vertex
            opp = (i + sides // 2) % sides
            angle_opp = math.radians(opp * (360 // sides) - 90)
            ox = center_x + int(r * math.cos(angle_opp))
            oy = center_y + int(r * math.sin(angle_opp) * 0.55)
            steps = max(abs(ox - vx), abs(oy - vy), 1)
            for s in range(steps + 1):
                t = s / max(steps, 1)
                lx = int(vx + t * (ox - vx))
                ly = int(vy + t * (oy - vy))
                if 0 <= lx < width and 0 <= ly < height:
                    if grid[ly][lx] == " ":
                        grid[ly][lx] = "┄"

    # Center symbol
    school_center = {
        "Evocation": "⚡", "Necromancy": "☠", "Enchantment": "✧",
        "Illusion": "◈", "Conjuration": "◇", "Abjuration": "✚",
        "Divination": "◉", "Transmutation": "∞",
    }
    grid[center_y][center_x] = school_center.get(school, "✦")

    for row in grid:
        lines.append("".join(row).rstrip())

    random.setstate(state)  # Restore random state
    return lines


# ──────────────────────────────────────────────
# Spell dataclass
# ──────────────────────────────────────────────

@dataclass
class Spell:
    name: str
    school: str
    level: int
    casting_time: str
    rng: str
    duration: str
    verbal: bool
    somatic: bool
    material: str
    description: str
    incantation: str
    verbal_detail: str
    somatic_detail: str
    backstory: str
    sigil: List[str]
    diagram: List[str]
    higher_levels: str = ""
    rarity: str = "Common"

    def to_dict(self) -> Dict:
        """Convert spell to a JSON-serializable dictionary."""
        d = asdict(self)
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialize spell to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# ──────────────────────────────────────────────
# Helper: ordinal suffix for level strings
# ──────────────────────────────────────────────

def ordinal(n: int) -> str:
    """Return the ordinal string for a number: 1 → '1st', 2 → '2nd', 3 → '3rd', etc."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def pluralize(count: int, singular: str, plural: str) -> str:
    """Return singular or plural form based on count.

    Examples: pluralize(1, "servant", "servants") → "1 servant"
              pluralize(3, "servant", "servants") → "3 servants"
    """
    word = singular if count == 1 else plural
    return f"{count} {word}"


# ──────────────────────────────────────────────
# Rarity selection
# ──────────────────────────────────────────────

def choose_rarity(level: Optional[int] = None) -> str:
    """Choose a rarity, optionally influenced by spell level."""
    names = list(RARITIES.keys())
    weights = [RARITIES[r]["weight"] for r in names]
    rarity = random.choices(names, weights=weights, k=1)[0]

    # If a level is given, sometimes bump rarity toward appropriate range
    if level is not None and random.random() < 0.5:
        low, high = RARITY_LEVEL_MODIFIERS[rarity]
        # If the chosen level falls outside the rarity's typical range,
        # 50% of the time re-pick from a more appropriate rarity
        if level < low or level > high:
            # Find a rarity whose range contains this level
            for r in ["Legendary", "Very Rare", "Rare", "Uncommon", "Common"]:
                lo, hi = RARITY_LEVEL_MODIFIERS[r]
                if lo <= level <= hi:
                    rarity = r
                    break
    return rarity


# ──────────────────────────────────────────────
# Generation
# ──────────────────────────────────────────────

# Track generated names to avoid duplicates within a session
_generated_names: set = set()


def generate_spell(school: Optional[str] = None, level: Optional[int] = None,
                   rarity: Optional[str] = None) -> Spell:
    """Generate a complete procedural spell.

    Args:
        school: School of magic. Random if None.
        level: Spell level 0-9. Random if None.
        rarity: Spell rarity. Auto-selected based on level if None.

    Returns:
        A fully populated Spell dataclass.
    """
    if school is None:
        school = random.choice(SCHOOLS)
    if level is None:
        level = random.randint(0, 9)
    if rarity is None:
        rarity = choose_rarity(level)

    # Generate name — ensure uniqueness
    max_attempts = 50
    name = f"{random.choice(PREFIXES)} {random.choice(ROOTS[school])}"  # fallback default
    for _ in range(max_attempts):
        if random.random() < 0.6 or level == 0:
            candidate = f"{random.choice(PREFIXES)} {random.choice(ROOTS[school])}"
        else:
            candidate = f"{random.choice(PREFIXES)} {random.choice(ROOTS[school])} of {random.choice(PREFIXES)} {random.choice(ROOTS[school])}"
        if candidate not in _generated_names:
            _generated_names.add(candidate)
            name = candidate
            break

    casting_time = random.choice(CASTING_TIMES)
    rng = random.choice(RANGES)

    if school in ("Evocation", "Necromancy", "Abjuration"):
        duration_weights = [3, 2, 1, 1, 1, 1, 1, 2, 2, 1, 1, 1]
    elif school in ("Enchantment", "Illusion", "Conjuration"):
        duration_weights = [1, 1, 2, 2, 2, 1, 1, 3, 3, 2, 1, 1]
    else:
        duration_weights = [2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2]

    duration = random.choices(DURATIONS, weights=duration_weights, k=1)[0]

    verbal = random.random() > 0.15
    somatic = random.random() > 0.2

    # Material component
    if random.random() > 0.2:
        num_reagents = random.randint(1, 2)
        material = " and ".join(random.sample(REAGENTS, num_reagents))
        if random.random() > 0.7:
            material += ", which the spell consumes"
    else:
        material = "None"

    # Effect description
    template = random.choice(EFFECT_TEMPLATES[school])
    dice = random.randint(1, min(level + 2, 10))
    sides = random.choice([4, 6, 8, 10, 12])
    damage_type = random.choice(DAMAGE_TYPES)
    area = random.choice([5, 10, 15, 20, 30, 60])
    condition = random.choice(CONDITIONS)
    count = random.randint(1, min(level + 1, 6))
    hp = random.randint(5, 30 + level * 10)
    illusion = random.choice(ILLUSION_THINGS)
    creature_type = random.choice(CREATURE_TYPES)
    plane = random.choice(PLANES)
    material_from = random.choice(MATERIALS_FROM)
    material_to = random.choice(MATERIALS_TO)
    size = random.choice(SIZES)
    ability = random.choice(ABILITIES)

    duration_short = duration.split(",")[-1].strip().rstrip(".") if "," in duration else duration
    level_word = SPELL_LEVELS[level]

    # Pluralized count+Noun strings for grammar-correct descriptions
    count_undead_servant = pluralize(count, "undead servant", "undead servants")
    count_creature_become = pluralize(count, "creature becomes", "creatures become")
    CREATURE_PLURALS = {
        "elemental": "elementals", "fiend": "fiends", "celestial": "celestials",
        "fey": "fey", "construct": "constructs", "beast": "beasts",
    }
    count_creature_summoned = pluralize(count, creature_type, CREATURE_PLURALS.get(creature_type, f"{creature_type}s"))
    count_ally = pluralize(count, "ally", "allies")
    count_creature_resistance = pluralize(count, "creature", "creatures")
    count_hidden_object = pluralize(count, "hidden object", "hidden objects")
    count_day = pluralize(count, "day", "days")
    count_question = pluralize(count, "yes/no question", "yes/no questions")

    description = template.format(
        dice=dice, sides=sides, damage_type=damage_type, area=area,
        condition=condition, duration=duration_short, duration_short=duration_short, count=count,
        hp=hp, illusion=illusion, creature_type=creature_type,
        plane=plane, material_from=material_from, material_to=material_to,
        size=size, ability=ability, level=level,
        count_undead_servant=count_undead_servant,
        count_creature_become=count_creature_become,
        count_creature_summoned=count_creature_summoned,
        count_ally=count_ally,
        count_creature_resistance=count_creature_resistance,
        count_hidden_object=count_hidden_object,
        count_day=count_day,
        count_question=count_question,
    )

    # Verbal detail
    if verbal:
        verbal_detail = random.choice(VERBAL_COMPONENTS)
    else:
        verbal_detail = "N/A"

    # Somatic detail
    if somatic:
        somatic_detail = random.choice(SOMATIC_COMPONENTS)
    else:
        somatic_detail = "N/A"

    # Higher levels — with correct ordinal suffix
    if 0 < level < 9:
        higher_levels = (
            f"When cast using a spell slot of {ordinal(level + 1)} level or higher, "
            f"the {random.choice(['damage increases', 'duration doubles', 'area of effect doubles', 'number of targets increases'])} "
            f"for each slot level above {level}."
        )
    else:
        higher_levels = ""

    incantation = generate_incantation(school)
    sigil = generate_sigil(school, level)
    diagram = generate_spell_diagram(school, level)

    # Backstory
    backstory = random.choice(BACKSTORY_TEMPLATES).format(
        temple=random.choice(TEMPLES),
        archmage=random.choice(ARCHMAGES),
        era=random.choice(ERAS),
        enemy=random.choice(ENEMIES),
        language=random.choice(LANGUAGES),
        city=random.choice(CITIES),
        plane=random.choice(PLANES),
        order=random.choice(ORDERS),
        material=random.choice(MATERIALS_TABLET),
    )

    return Spell(
        name=name, school=school, level=level, rarity=rarity,
        casting_time=casting_time, rng=rng, duration=duration,
        verbal=verbal, somatic=somatic, material=material,
        description=description, incantation=incantation,
        verbal_detail=verbal_detail, somatic_detail=somatic_detail,
        backstory=backstory, sigil=sigil, diagram=diagram,
        higher_levels=higher_levels,
    )


# ──────────────────────────────────────────────
# Rendering
# ──────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
RST = RESET


def wrap_text(text: str, width: int = 58, first_line_width: Optional[int] = None) -> List[str]:
    """Word-wrap text to a given width.

    Args:
        text: The text to wrap.
        width: Maximum line width for all lines.
        first_line_width: If given, the first line has a shorter max width
            (useful when a prefix will be added to the first line).
    """
    if first_line_width is None:
        first_line_width = width
    words = text.split()
    lines = []
    current = ""
    max_w = first_line_width
    for word in words:
        if current and len(current) + 1 + len(word) > max_w:
            lines.append(current)
            current = word
            max_w = width  # subsequent lines use full width
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r'\033\[[0-9;]*m', '', text)


def render_grimoire_page(spell: Spell, color: bool = True) -> str:
    """Render a full grimoire page for a spell."""
    page_width = 64

    sc = SCHOOL_COLORS.get(spell.school, "") if color else ""
    rst = RST if color else ""
    rc = RARITIES.get(spell.rarity, {}).get("color", "") if color else ""

    lines = []

    # Top border
    top_border = f"  ╔{'═' * (page_width - 4)}╗"
    lines.append(top_border)

    # School and level header
    level_str = SPELL_LEVELS[spell.level]
    header = f"{spell.school} — {level_str} Level"
    pad = page_width - 6 - len(header)
    header_display = f"{sc}{header}{rst}" if color else header
    lines.append(f"  ║ {header_display}{' ' * pad} ║")

    # Rarity badge on next line
    rarity_label = f"[{spell.rarity}]"
    rarity_display = f"{rc}{BOLD}{rarity_label}{rst}" if color else rarity_label
    rarity_pad = page_width - 6 - len(rarity_label)
    lines.append(f"  ║ {rarity_display}{' ' * rarity_pad} ║")

    lines.append(f"  ╠{'═' * (page_width - 4)}╣")

    # Spell name (centered)
    name_display = f"{BOLD}{sc}{spell.name}{rst}" if color else spell.name
    name_pad = page_width - 6 - len(spell.name)
    lines.append(f"  ║ {name_display}{' ' * name_pad} ║")

    # Decorative line
    lines.append(f"  ╠{'─' * (page_width - 4)}╣")

    # Metadata
    def meta_line(label: str, value: str) -> str:
        actual_content = f"{BOLD}{label}:{rst} {value}" if color else f"{label}: {value}"
        visible_len = len(label) + 2 + len(value)  # label + ": " + value
        pad = page_width - 6 - visible_len
        return f"  ║ {actual_content}{' ' * max(pad, 0)} ║"

    lines.append(meta_line("Casting Time", spell.casting_time))
    lines.append(meta_line("Range", spell.rng))
    lines.append(meta_line("Duration", spell.duration))

    # Components
    components = []
    if spell.verbal:
        components.append("V")
    if spell.somatic:
        components.append("S")
    if spell.material != "None":
        components.append("M")
    comp_str = ", ".join(components)

    lines.append(meta_line("Components", comp_str))

    # Material detail (if present)
    if spell.material != "None":
        mat_lines = wrap_text(f"({spell.material})", width=page_width - 8)
        for ml in mat_lines:
            ml_pad = page_width - 8 - len(ml)  # 8 = "  ║   " (6) + " ║" (2)
            lines.append(f"  ║   {DIM}{ml}{rst}{' ' * max(ml_pad, 0)} ║")

    lines.append(f"  ╠{'─' * (page_width - 4)}╣")

    # Sigil
    lines.append(f"  ║{' ' * (page_width - 4)}║")
    sigil_lines = spell.sigil
    for sl in sigil_lines:
        sigil_pad = page_width - 6 - len(sl)
        lines.append(f"  ║ {sc}{sl}{rst}{' ' * max(sigil_pad, 0)} ║")
    lines.append(f"  ║{' ' * (page_width - 4)}║")

    # Spell diagram
    lines.append(f"  ╠{'─' * (page_width - 4)}╣")
    lines.append(f"  ║{' ' * (page_width - 4)}║")
    for dl in spell.diagram:
        dl_pad = page_width - 6 - len(dl)
        lines.append(f"  ║ {sc}{dl}{rst}{' ' * max(dl_pad, 0)} ║")
    lines.append(f"  ║{' ' * (page_width - 4)}║")

    # Description
    lines.append(f"  ╠{'─' * (page_width - 4)}╣")
    lines.append(f"  ║{' ' * (page_width - 4)}║")

    desc_lines = wrap_text(spell.description, width=page_width - 8)
    for dl in desc_lines:
        prefix = f"  ║ {ITALIC}" if color else "  ║ "
        suffix = f"{rst}" if color else ""
        dl_pad = page_width - 6 - len(dl)
        lines.append(f"{prefix}{dl}{suffix}{' ' * max(dl_pad, 0)} ║")

    if spell.higher_levels:
        lines.append(f"  ║{' ' * (page_width - 4)}║")
        # The prefix "At Higher Levels. " is 20 visible chars.
        # First line has: "  ║ " (4) + prefix (20) + hl + padding + " ║" (2) = 64
        # So first line content (prefix + hl) must be ≤ 58 visible chars,
        # meaning hl ≤ 38. Subsequent lines wrap at 58.
        hl_prefix = "At Higher Levels. "
        hl_lines = wrap_text(spell.higher_levels, width=page_width - 8,
                              first_line_width=page_width - 8 - len(hl_prefix))
        for idx, hl in enumerate(hl_lines):
            if idx == 0:
                prefix = f"  ║ {BOLD}At Higher Levels.{rst} " if color else "  ║ At Higher Levels. "
                # visible content = "At Higher Levels. " + hl
                visible_len = len(hl_prefix) + len(hl)
                hl_pad = page_width - 6 - visible_len
                lines.append(f"{prefix}{hl}{' ' * max(hl_pad, 0)} ║")
            else:
                hl_pad = page_width - 6 - len(hl)
                lines.append(f"  ║ {hl}{' ' * max(hl_pad, 0)} ║")

    lines.append(f"  ║{' ' * (page_width - 4)}║")

    # Component details
    lines.append(f"  ╠{'─' * (page_width - 4)}╣")
    lines.append(f"  ║{' ' * (page_width - 4)}║")

    if spell.verbal:
        v_text = spell.verbal_detail
        v_lines = wrap_text(f"Verbal: {v_text}", width=page_width - 8)
        for vl in v_lines:
            v_pad = page_width - 6 - len(vl)
            lines.append(f"  ║ {vl}{' ' * max(v_pad, 0)} ║")

    if spell.somatic:
        s_text = spell.somatic_detail
        s_lines = wrap_text(f"Somatic: {s_text}", width=page_width - 8)
        for sl2 in s_lines:
            s_pad = page_width - 6 - len(sl2)
            lines.append(f"  ║ {sl2}{' ' * max(s_pad, 0)} ║")

    lines.append(f"  ║{' ' * (page_width - 4)}║")

    # Incantation
    lines.append(f"  ╠{'─' * (page_width - 4)}╣")
    lines.append(f"  ║{' ' * (page_width - 4)}║")

    inc_lines = wrap_text(spell.incantation, width=page_width - 10)
    for il in inc_lines:
        il_pad = page_width - 7 - len(il)  # 7 = "  ║  " (5) + " ║" (2)
        lines.append(f"  ║  {sc}{ITALIC}{il}{rst}{' ' * max(il_pad, 0)} ║")

    lines.append(f"  ║{' ' * (page_width - 4)}║")

    # Lore / backstory
    lines.append(f"  ╠{'─' * (page_width - 4)}╣")
    lines.append(f"  ║{' ' * (page_width - 4)}║")

    lore_lines = wrap_text(spell.backstory, width=page_width - 8)
    for ll in lore_lines:
        ll_pad = page_width - 6 - len(ll)
        lines.append(f"  ║ {DIM}{ll}{rst}{' ' * max(ll_pad, 0)} ║")

    lines.append(f"  ║{' ' * (page_width - 4)}║")

    # Bottom border
    lines.append(f"  ╚{'═' * (page_width - 4)}╝")

    return "\n".join(lines)


def render_plaintext_page(spell: Spell) -> str:
    """Render a grimoire page without any ANSI escape codes."""
    return strip_ansi(render_grimoire_page(spell, color=True))


# ──────────────────────────────────────────────
# Grimoire (collection of spells)
# ──────────────────────────────────────────────

def generate_grimoire(num_spells: int = 5, school: Optional[str] = None,
                      color: bool = True) -> str:
    """Generate a full grimoire with multiple spells."""
    pages = []

    sc = ""
    rst = ""
    if color and school and school in SCHOOL_COLORS:
        sc = SCHOOL_COLORS[school]
        rst = RESET

    # Build header programmatically to ensure consistent 64-char width
    pw = 64  # page_width
    # "  ║" (3) + content (60) + "║" (1) = 64
    title = "G R I M O I R E   O F   S P E L L S"
    # Center the title within the 60-char content area
    content_width = pw - 4  # 60 chars between ║ and ║
    title_pad_left = (content_width - len(title)) // 2
    title_pad_right = content_width - len(title) - title_pad_left

    lines = []
    lines.append(f"  {sc}╔{'═' * (pw - 4)}╗{rst}")
    lines.append(f"  {sc}║{' ' * (pw - 4)}║{rst}")
    lines.append(f"  {sc}║{' ' * title_pad_left}{title}{' ' * title_pad_right}║{rst}")
    lines.append(f"  {sc}║{' ' * (pw - 4)}║{rst}")

    # Separator line with dashes
    sep = f"{'─' * 50}"
    sep_pad = pw - 6 - len(sep)
    lines.append(f"  {sc}║ {sep}{' ' * max(sep_pad, 0)} ║{rst}")

    if school:
        school_line = f"School of {school}"
        school_pad = pw - 6 - len(school_line)
        lines.append(f"  {sc}║ {BOLD}{school_line}{rst}{sc}{' ' * max(school_pad, 0)} ║{rst}")

    lines.append(f"  {sc}║{' ' * (pw - 4)}║{rst}")
    lines.append(f"  {sc}╚{'═' * (pw - 4)}╝{rst}")

    header = "\n".join(lines)

    pages.append(header)

    for i in range(num_spells):
        spell = generate_spell(school=school)
        page = render_grimoire_page(spell, color=color)
        pages.append(page)
        if i < num_spells - 1:
            pages.append("\n")

    result = "\n".join(pages)
    if not color:
        result = strip_ansi(result)
    return result


# ──────────────────────────────────────────────
# Spell list mode (compact table)
# ──────────────────────────────────────────────

def generate_spell_list(num_spells: int = 10, school: Optional[str] = None,
                        color: bool = True) -> str:
    """Generate a compact spell list."""
    lines = []
    lines.append(f"  {'Rarity':<12} {'Level':<8} {'School':<14} {'Spell Name':<30}")
    lines.append(f"  {'─' * 12} {'─' * 8} {'─' * 14} {'─' * 30}")

    for _ in range(num_spells):
        spell = generate_spell(school=school)
        sc = SCHOOL_COLORS.get(spell.school, "") if color else ""
        rc = RARITIES.get(spell.rarity, {}).get("color", "") if color else ""
        rst = RESET if color else ""
        level_str = SPELL_LEVELS[spell.level]
        rarity_str = spell.rarity
        lines.append(
            f"  {rc}{rarity_str:<12}{rst} {level_str:<8} "
            f"{sc}{spell.school:<14}{rst} {sc}{BOLD}{spell.name:<30}{rst}"
        )

    result = "\n".join(lines)
    if not color:
        result = strip_ansi(result)
    return result


# ──────────────────────────────────────────────
# Interactive mode
# ──────────────────────────────────────────────

def interactive_mode():
    """Run an interactive grimoire browser."""
    print(f"\n{BOLD}{UNDERLINE}📜 Procedural Spell Grimoire Generator v{__version__}{RST}")
    print(f"{DIM}Generate unique spells for your fantasy RPG campaigns{RST}\n")

    while True:
        print(f"\n{BOLD}Options:{RST}")
        print("  1. Generate a random spell")
        print("  2. Generate a spell from a specific school")
        print("  3. Generate a grimoire (5 spells)")
        print("  4. Generate a spell list (10 spells)")
        print("  5. Browse spells by level")
        print("  6. Browse spells by rarity")
        print("  q. Quit")
        print()

        choice = input(f"{BOLD}Choose [1-6/q]:{RST} ").strip().lower()

        if choice == "q":
            print(f"\n{DIM}May your spells always find their mark!{RST}\n")
            break
        elif choice == "1":
            spell = generate_spell()
            print("\n" + render_grimoire_page(spell))
        elif choice == "2":
            print(f"\n{BOLD}Schools:{RST}")
            for i, school in enumerate(SCHOOLS, 1):
                sc = SCHOOL_COLORS.get(school, "")
                print(f"  {i}. {sc}{school}{RST}")
            try:
                s_choice = int(input(f"\n{BOLD}Choose school [1-8]:{RST} ").strip())
                if 1 <= s_choice <= 8:
                    spell = generate_spell(school=SCHOOLS[s_choice - 1])
                    print("\n" + render_grimoire_page(spell))
                else:
                    print("Invalid choice.")
            except (ValueError, EOFError):
                print("Invalid choice.")
        elif choice == "3":
            print("\n" + generate_grimoire(num_spells=5))
        elif choice == "4":
            print("\n" + generate_spell_list(num_spells=10))
        elif choice == "5":
            try:
                level = int(input(f"{BOLD}Spell level [0-9]:{RST} ").strip())
                if 0 <= level <= 9:
                    spell = generate_spell(level=level)
                    print("\n" + render_grimoire_page(spell))
                else:
                    print("Level must be 0-9.")
            except (ValueError, EOFError):
                print("Invalid input.")
        elif choice == "6":
            print(f"\n{BOLD}Rarities:{RST}")
            rarity_names = list(RARITIES.keys())
            for i, r in enumerate(rarity_names, 1):
                rc = RARITIES[r]["color"]
                print(f"  {i}. {rc}{BOLD}{r}{RST}")
            try:
                r_choice = int(input(f"\n{BOLD}Choose rarity [1-5]:{RST} ").strip())
                if 1 <= r_choice <= len(rarity_names):
                    rarity = rarity_names[r_choice - 1]
                    spell = generate_spell(rarity=rarity)
                    print("\n" + render_grimoire_page(spell))
                else:
                    print("Invalid choice.")
            except (ValueError, EOFError):
                print("Invalid choice.")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Procedural Spell Grimoire Generator — Create unique fantasy RPG spells",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s                           Generate a random spell
  %(prog)s --grimoire                Generate a full 5-spell grimoire
  %(prog)s --school Necromancy       Generate a Necromancy spell
  %(prog)s --level 5                 Generate a 5th-level spell
  %(prog)s --rarity Legendary        Generate a Legendary-rarity spell
  %(prog)s --list 20                 Show a list of 20 spells
  %(prog)s --json                    Output spell as JSON
  %(prog)s --no-color                Disable colored output
  %(prog)s --interactive             Enter interactive mode
  %(prog)s --grimoire --school Evocation --output grimoire.txt
  %(prog)s --version                 Show version number
""",
    )
    parser.add_argument("--version", "-v", action="version",
                        version=f"%(prog)s {__version__}")
    parser.add_argument("--school", "-s", choices=SCHOOLS,
                        help="School of magic for the spell(s)")
    parser.add_argument("--level", "-l", type=int, choices=range(10),
                        metavar="{0..9}", help="Spell level (0-9)")
    parser.add_argument("--rarity", "-r", choices=list(RARITIES.keys()),
                        help="Spell rarity (Common, Uncommon, Rare, Very Rare, Legendary)")
    parser.add_argument("--grimoire", "-g", action="store_true",
                        help="Generate a full grimoire (5 spells)")
    parser.add_argument("--count", "-c", type=int, default=1,
                        help="Number of individual spells to generate (default: 1)")
    parser.add_argument("--list", "-n", type=int, metavar="COUNT",
                        help="Generate a compact list of COUNT spells")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output")
    parser.add_argument("--output", "-o", type=str,
                        help="Write output to file instead of stdout")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Output spell data as JSON (for --count or single spell)")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Enter interactive mode")
    parser.add_argument("--seed", type=int,
                        help="Random seed for reproducible spells")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    color = not args.no_color

    if args.interactive:
        interactive_mode()
        return

    output = ""
    json_spells = []

    if args.json:
        # JSON output mode
        num = args.count if args.count > 1 or not args.grimoire else 1
        if args.grimoire:
            num = 5
        elif args.list:
            num = args.list
        else:
            num = max(args.count, 1)

        for _ in range(num):
            spell = generate_spell(school=args.school, level=args.level, rarity=args.rarity)
            json_spells.append(spell.to_dict())

        output = json.dumps(json_spells, indent=2, ensure_ascii=False)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"JSON written to {args.output}")
            except OSError as e:
                print(f"Error writing to {args.output}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(output)
        return

    if args.grimoire:
        output = generate_grimoire(num_spells=5, school=args.school, color=color)
    elif args.list:
        output = generate_spell_list(num_spells=args.list, school=args.school, color=color)
    else:
        # Generate one or more individual spells
        num = max(args.count, 1)
        pages = []
        for _ in range(num):
            spell = generate_spell(school=args.school, level=args.level, rarity=args.rarity)
            pages.append(render_grimoire_page(spell, color=color))
        output = "\n\n".join(pages)

    if args.output:
        # Strip ANSI for file output
        clean_output = strip_ansi(output)
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(clean_output)
            print(f"Grimoire written to {args.output}")
        except OSError as e:
            print(f"Error writing to {args.output}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)


if __name__ == "__main__":
    main()