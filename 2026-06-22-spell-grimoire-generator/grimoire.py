#!/usr/bin/env python3
"""
Procedural Spell Grimoire Generator
=====================================
Generates beautifully formatted grimoire pages for fantasy RPG spells
with procedural names, ASCII art, incantations, reagents, and metadata.

Version: 4.0.0

Features:
  - 8 schools of magic with school-specific content
  - 5 rarity tiers with weighted selection
  - Arcane sigils and spell diagrams (procedural ASCII art)
  - Spell tags for thematic categorization
  - Mana cost calculation
  - Scroll GP value calculation (D&D-style gold piece pricing)
  - Spell synergy detection
  - Spell conflict detection (incompatible school pairings)
  - Markdown, JSON, HTML, and plaintext export
  - Statistical analysis mode (--stats)
  - Interactive browser mode
  - Save/load spells to JSON files
  - Seed support for reproducible generation
"""

import random
import math
import argparse
import json
import sys
import os
import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Tuple
from pathlib import Path

__version__ = "4.0.1"

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

# Mana cost base values per spell level (0-9)
MANA_COSTS = {
    0: 0,    # Cantrip
    1: 5,    # 1st level
    2: 10,   # 2nd level
    3: 15,   # 3rd level
    4: 20,   # 4th level
    5: 30,   # 5th level
    6: 40,   # 6th level
    7: 50,   # 7th level
    8: 60,   # 8th level
    9: 75,   # 9th level
}

# School mana cost multipliers (some schools are costlier)
MANA_MULTIPLIERS = {
    "Evocation": 1.0,
    "Necromancy": 1.1,
    "Enchantment": 1.05,
    "Illusion": 0.9,
    "Conjuration": 1.15,
    "Abjuration": 1.05,
    "Divination": 0.85,
    "Transmutation": 1.1,
}

# Tag pools for spell categorization
TAG_POOLS = {
    "Evocation":    ["fire", "lightning", "cold", "force", "damage", "area", "burst", "beam", "destructive", "offensive"],
    "Necromancy":   ["death", "undead", "drain", "curse", "dark", "shadow", "fear", "decay", "life", "restoration"],
    "Enchantment":  ["mind", "charm", "control", "compulsion", "emotion", "sleep", "calm", "rage", "influence", "bond"],
    "Illusion":     ["deception", "shadow", "mirror", "phantom", "invisibility", "disguise", "hallucination", "dream", "mirage", "veil"],
    "Conjuration":  ["summoning", "portal", "teleportation", "gate", "planar", "calling", "creation", "extradimensional", "beast", "elemental"],
    "Abjuration":   ["protection", "ward", "shield", "barrier", "dispel", "counterspell", "sanctuary", "seal", "banish", "resistance"],
    "Divination":   ["vision", "sight", "knowledge", "foresight", "truth", "scrying", "oracle", "sense", "reveal", "secret"],
    "Transmutation": ["change", "transform", "shape", "enhance", "reduce", "grow", "shrink", "polymorph", "alter", "transmute"],
}

# Synergy matrix: which schools synergize well together
SYNERGY_PAIRS = {
    ("Evocation", "Abjuration"): "Offensive spells pair with protective wards for battle mages.",
    ("Necromancy", "Evocation"): "Dark energy amplifies destructive force for devastating attacks.",
    ("Enchantment", "Illusion"): "Mind-altering magic and sensory deception create irresistible effects.",
    ("Conjuration", "Abjuration"): "Summoned allies reinforced by protective barriers are formidable.",
    ("Divination", "Enchantment"): "Knowledge of thoughts makes enchantment spells far more effective.",
    ("Transmutation", "Evocation"): "Altered forms can channel elemental energy with greater efficiency.",
    ("Necromancy", "Illusion"): "Fear-based illusions and death magic create overwhelming dread.",
    ("Conjuration", "Transmutation"): "Summoned creatures can be reshaped for specific tasks.",
    ("Divination", "Abjuration"): "Foreknowledge allows precise placement of protective wards.",
    ("Illusion", "Conjuration"): "Illusory disguises enhance summoned creatures' effectiveness.",
    ("Necromancy", "Divination"): "Communing with the dead reveals hidden knowledge of the past.",
    ("Enchantment", "Transmutation"): "Altering both mind and body creates complete transformations.",
}

# Conflict matrix: schools that clash or interfere with each other
CONFLICT_PAIRS = {
    ("Evocation", "Illusion"): "Raw destructive force shatters delicate illusory constructs.",
    ("Necromancy", "Abjuration"): "Death magic undermines protective wards meant to preserve life.",
    ("Necromancy", "Enchantment"): "Undeath's cold void dampens the warmth needed for enchantment.",
    ("Evocation", "Divination"): "Chaotic elemental energy disrupts the calm focus needed for scrying.",
    ("Conjuration", "Necromancy"): "Planar portals can be contaminated by necrotic energy, causing miscasts.",
    ("Illusion", "Divination"): "False visions and true sight are inherently at odds.",
    ("Transmutation", "Necromancy"): "Changing living forms conflicts with the stasis of undeath.",
    ("Enchantment", "Abjuration"): "Mental domination clashes with wards designed to resist influence.",
}

# Scroll GP values by spell level (D&D 5e-style pricing)
# Based on: level × base_price, with rarity multiplier
SCROLL_BASE_PRICES = {
    0: 50,     # Cantrip scroll
    1: 100,    # 1st level
    2: 200,    # 2nd level
    3: 300,    # 3rd level
    4: 500,    # 4th level
    5: 1000,   # 5th level
    6: 2500,   # 6th level
    7: 5000,   # 7th level
    8: 10000,  # 8th level
    9: 25000,  # 9th level
}

RARITY_GOLD_MULTIPLIERS = {
    "Common": 1.0,
    "Uncommon": 1.5,
    "Rare": 2.5,
    "Very Rare": 5.0,
    "Legendary": 10.0,
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
        "Animates {count_undead_servant}{duration_phrase}{hp_phrase}.",
        "Target must make a WIS save or take {dice}d{sides} necrotic damage and be frightened.",
        "Creates a {area}-foot zone of negative energy. Living creatures take {dice}d{sides} damage.",
    ],
    "Enchantment": [
        "Target must make a WIS save or become {condition}{duration_phrase}.",
        "Up to {count_creature_become} become {condition}{duration_phrase}.",
        "Target creature regards the caster as a trusted ally{duration_phrase}.",
        "The caster can issue a {count}-word command that the target must follow.",
    ],
    "Illusion": [
        "Creates a {area}-foot illusory {illusion}{duration_phrase}.",
        "The caster becomes invisible{duration_phrase} or until they attack.",
        "Creates a {area}-foot zone where all sounds are muffled{duration_phrase}.",
        "Target sees a terrifying phantasm; WIS save or take {dice}d{sides} psychic damage.",
    ],
    "Conjuration": [
        "Summons {count_creature_summoned}{duration_phrase}.",
        "Opens a portal to {plane}{duration_phrase}.",
        "Teleports the caster and up to {count_ally} to a location within {area} miles.",
        "Conjures a {area}-foot dome of {material_to}{duration_phrase}.",
    ],
    "Abjuration": [
        "Creates a {area}-foot radius anti-magic field{duration_phrase}.",
        "Grants {count_creature_resistance} resistance to {damage_type}{duration_phrase}.",
        "Dispels all magical effects of level {level} or lower in a {area}-foot radius.",
        "Creates a magical barrier with {hp} HP{duration_phrase} or until destroyed.",
    ],
    "Divination": [
        "Reveals the location of {count_hidden_object} within {area} feet.",
        "The caster receives a vision of events up to {count_day} in the future.",
        "The caster can see through walls and illusions within {area} feet{duration_phrase}.",
        "Answers {count_question} about the future with 90% accuracy.",
    ],
    "Transmutation": [
        "Transforms {area} cubic feet of {material_from} into {material_to}{duration_phrase}.",
        "Target creature grows to {size}x their size{duration_phrase}.",
        "Target creature shrinks to 1/{size} their size{duration_phrase}.",
        "{duration_phrase_cap}the caster gains the ability to {ability}.",
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
    tags: List[str] = field(default_factory=list)
    mana_cost: int = 0
    scroll_value: int = 0

    def to_dict(self) -> Dict:
        """Convert spell to a JSON-serializable dictionary."""
        d = asdict(self)
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialize spell to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_markdown(self) -> str:
        """Render the spell as a Markdown document."""
        level_str = SPELL_LEVELS[self.level]
        components = []
        if self.verbal:
            components.append("V")
        if self.somatic:
            components.append("S")
        if self.material != "None":
            components.append(f"M ({self.material})")
        comp_str = ", ".join(components)

        md_lines = [
            f"# {self.name}",
            f"",
            f"**{self.school} — {level_str} Level** | **[{self.rarity}]** | **Mana Cost: {self.mana_cost}** | **Scroll: {self.scroll_value:,} gp**",
            f"",
            f"- **Casting Time:** {self.casting_time}",
            f"- **Range:** {self.rng}",
            f"- **Duration:** {self.duration}",
            f"- **Components:** {comp_str}",
            f"",
            f"## Description",
            f"",
            f"{self.description}",
        ]

        if self.higher_levels:
            md_lines.extend([
                f"",
                f"## At Higher Levels",
                f"",
                f"{self.higher_levels}",
            ])

        md_lines.extend([
            f"",
            f"## Incantation",
            f"",
            f"*{self.incantation}*",
            f"",
            f"## Lore",
            f"",
            f"{self.backstory}",
        ])

        if self.tags:
            md_lines.extend([
                f"",
                f"## Tags",
                f"",
                f"{', '.join(self.tags)}",
            ])

        return "\n".join(md_lines)

    def to_html(self) -> str:
        """Render the spell as a standalone HTML document."""
        level_str = SPELL_LEVELS[self.level]
        components = []
        if self.verbal:
            components.append("V")
        if self.somatic:
            components.append("S")
        if self.material != "None":
            components.append(f"M ({html_escape(self.material)})")
        comp_str = ", ".join(components)

        sigil_html = "<pre>\n" + "\n".join(html_escape(line) for line in self.sigil) + "\n</pre>"
        diagram_html = "<pre>\n" + "\n".join(html_escape(line) for line in self.diagram) + "\n</pre>"

        higher_levels_html = ""
        if self.higher_levels:
            higher_levels_html = f"""
      <div class="section">
        <h3>At Higher Levels</h3>
        <p>{html_escape(self.higher_levels)}</p>
      </div>"""

        tags_html = ""
        if self.tags:
            tag_items = "\n".join(f'          <li>{html_escape(t)}</li>' for t in self.tags)
            tags_html = f"""
      <div class="section">
        <h3>Tags</h3>
        <ul class="tags">
{tag_items}
        </ul>
      </div>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_escape(self.name)}</title>
  <style>
    body {{
      font-family: 'Georgia', 'Times New Roman', serif;
      max-width: 700px;
      margin: 2rem auto;
      padding: 0 1rem;
      background: #1a1a2e;
      color: #e0e0e0;
    }}
    h1 {{
      color: #f0c040;
      border-bottom: 2px solid #f0c040;
      padding-bottom: 0.5rem;
    }}
    h2 {{
      color: #a0a0ff;
      margin-top: 1.5rem;
    }}
    h3 {{
      color: #c0c0c0;
    }}
    .meta {{
      background: #252540;
      border-radius: 8px;
      padding: 1rem;
      margin: 1rem 0;
    }}
    .meta dt {{
      font-weight: bold;
      color: #f0c040;
    }}
    .meta dd {{
      margin-left: 1rem;
      margin-bottom: 0.3rem;
    }}
    .badge {{
      display: inline-block;
      background: #404080;
      color: #ffffff;
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
      font-size: 0.9rem;
    }}
    .badge.legendary {{ background: #f0c040; color: #1a1a2e; }}
    .badge.very-rare {{ background: #a020f0; color: #ffffff; }}
    .badge.rare {{ background: #4060e0; color: #ffffff; }}
    .badge.uncommon {{ background: #20a020; color: #ffffff; }}
    .badge.common {{ background: #808080; color: #ffffff; }}
    .section {{
      margin: 1rem 0;
    }}
    pre {{
      background: #101020;
      padding: 1rem;
      border-radius: 4px;
      overflow-x: auto;
      color: #c0ffc0;
      font-size: 0.85rem;
    }}
    .tags li {{
      display: inline-block;
      background: #303060;
      padding: 0.15rem 0.5rem;
      border-radius: 12px;
      margin: 0.2rem;
      font-size: 0.85rem;
    }}
    .incantation {{
      font-style: italic;
      color: #d0a0ff;
      border-left: 3px solid #d0a0ff;
      padding-left: 1rem;
      margin: 1rem 0;
    }}
    .lore {{
      color: #a0a0a0;
      font-style: italic;
    }}
    .gold {{ color: #f0c040; }}
    .mana {{ color: #40c0ff; }}
  </style>
</head>
<body>
  <h1>{html_escape(self.name)}</h1>
  <p>
    <strong>{html_escape(self.school)}</strong> — {html_escape(level_str)} Level
    <span class="badge {self.rarity.lower().replace(' ', '-')}">{html_escape(self.rarity)}</span>
    <span class="mana">Mana: {self.mana_cost}</span>
    <span class="gold">Scroll: {self.scroll_value:,} gp</span>
  </p>
  <dl class="meta">
    <dt>Casting Time</dt><dd>{html_escape(self.casting_time)}</dd>
    <dt>Range</dt><dd>{html_escape(self.rng)}</dd>
    <dt>Duration</dt><dd>{html_escape(self.duration)}</dd>
    <dt>Components</dt><dd>{html_escape(comp_str)}</dd>
  </dl>
  <div class="section">
    <h2>Sigil</h2>
    {sigil_html}
  </div>
  <div class="section">
    <h2>Spell Diagram</h2>
    {diagram_html}
  </div>
  <div class="section">
    <h2>Description</h2>
    <p>{html_escape(self.description)}</p>
  </div>{higher_levels_html}
  <div class="section">
    <h2>Incantation</h2>
    <p class="incantation">{html_escape(self.incantation)}</p>
  </div>
  <div class="section">
    <h2>Lore</h2>
    <p class="lore">{html_escape(self.backstory)}</p>
  </div>{tags_html}
</body>
</html>"""


# ──────────────────────────────────────────────
# Helper: ordinal suffix for level strings
# ──────────────────────────────────────────────

def format_duration_phrase(duration: str) -> str:
    """Format a duration string for embedding in a description.

    Returns a phrase like ' for 1 minute', ' for up to 10 minutes', etc.
    For 'Instantaneous', returns an empty string (duration doesn't apply).
    For durations starting with 'Concentration', returns ' for up to X'.
    For 'Until dispelled' / 'Until the next dawn', returns ' until dispelled' / ' until the next dawn'.
    """
    if duration == "Instantaneous":
        return ""
    if duration.startswith("Until "):
        return " " + duration[0].lower() + duration[1:]
    if duration.startswith("Concentration, up to "):
        return " for " + duration[len("Concentration, "):]  # "up to X"
    return f" for {duration}"


def format_duration_phrase_cap(duration: str) -> str:
    """Like format_duration_phrase but with the first letter capitalized for sentence start."""
    phrase = format_duration_phrase(duration)
    if not phrase:
        return ""
    # Find the first letter and capitalize it
    for i, ch in enumerate(phrase):
        if ch.isalpha():
            return phrase[:i] + ch.upper() + phrase[i+1:]
    return phrase


def format_hp_phrase(count: int, hp: int) -> str:
    """Format the HP phrase for undead servant descriptions.

    Returns ', each with X HP' for plural, or ' with X HP' for singular.
    """
    if count == 1:
        return f" with {hp} HP"
    return f", each with {hp} HP"


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
# Mana cost calculation
# ──────────────────────────────────────────────

def calculate_mana_cost(level: int, school: str, rarity: str, casting_time: str, duration: str) -> int:
    """Calculate a mana cost for the spell based on its properties.

    The base cost comes from the spell level, then modifiers are applied
    for school difficulty, rarity, casting time, and duration.
    """
    base = MANA_COSTS.get(level, 0)

    # School multiplier
    multiplier = MANA_MULTIPLIERS.get(school, 1.0)
    cost = int(base * multiplier)

    # Rarity modifier
    rarity_mods = {
        "Common": 0, "Uncommon": 2, "Rare": 5,
        "Very Rare": 10, "Legendary": 20,
    }
    cost += rarity_mods.get(rarity, 0)

    # Casting time modifier (quicker = more costly)
    quick_cast = {"1 action", "1 bonus action", "1 reaction"}
    if casting_time in quick_cast:
        cost += 3

    # Duration modifier (longer = more costly)
    long_dur = {"8 hours", "24 hours", "Until dispelled"}
    if duration in long_dur:
        cost += 5

    # Concentration costs extra
    if "Concentration" in duration:
        cost += 2

    return max(cost, 0)


# ──────────────────────────────────────────────
# Scroll GP value calculation
# ──────────────────────────────────────────────

def calculate_scroll_value(level: int, rarity: str) -> int:
    """Calculate the gold piece value of a spell scroll.

    Uses D&D 5e-style pricing: base price from level, multiplied
    by the rarity multiplier.  The result is rounded to the nearest
    standard denomination (5 gp for values under 100, 25 gp for
    values under 1,000, and 100 gp otherwise).

    Args:
        level: Spell level (0-9).
        rarity: Rarity tier (Common through Legendary).

    Returns:
        Gold piece value as an integer.
    """
    base = SCROLL_BASE_PRICES.get(level, 50)
    mult = RARITY_GOLD_MULTIPLIERS.get(rarity, 1.0)
    value = int(base * mult)
    # Round to a sensible denomination
    if value < 100:
        value = max(5, round(value / 5) * 5)
    elif value < 1000:
        value = round(value / 25) * 25
    else:
        value = round(value / 100) * 100
    return value


# ──────────────────────────────────────────────
# Conflict detection
# ──────────────────────────────────────────────

def find_conflicts(spells: List[Spell]) -> List[Tuple[Spell, Spell, str]]:
    """Find pairs of spells whose schools conflict with each other.

    Returns a list of (spell1, spell2, description) tuples.
    """
    conflicts = []
    for i in range(len(spells)):
        for j in range(i + 1, len(spells)):
            s1, s2 = spells[i], spells[j]
            key1 = (s1.school, s2.school)
            key2 = (s2.school, s1.school)
            desc = CONFLICT_PAIRS.get(key1) or CONFLICT_PAIRS.get(key2)
            if desc:
                conflicts.append((s1, s2, desc))
    return conflicts


def render_conflicts(spells: List[Spell], color: bool = True) -> str:
    """Render a conflict report for a list of spells."""
    conflicts = find_conflicts(spells)
    if not conflicts:
        return f"  No conflicts found between these spells."

    lines = [f"  {BOLD}⚠ Spell Conflicts{RST if color else ''}", ""]
    for s1, s2, desc in conflicts:
        sc1 = SCHOOL_COLORS.get(s1.school, "") if color else ""
        sc2 = SCHOOL_COLORS.get(s2.school, "") if color else ""
        rst = RST if color else ""
        lines.append(f"  {sc1}{BOLD if color else ''}{s1.name}{rst} × {sc2}{BOLD if color else ''}{s2.name}{rst}")
        lines.append(f"    {DIM if color else ''}{desc}{rst}")
        lines.append("")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# HTML export helper
# ──────────────────────────────────────────────

def html_escape(text: str) -> str:
    """Escape special HTML characters in a string."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


# ──────────────────────────────────────────────
# Spell tag generation
# ──────────────────────────────────────────────

def generate_tags(school: str, level: int, damage_type: Optional[str] = None,
                  rarity: str = "Common") -> List[str]:
    """Generate thematic tags for a spell based on its properties."""
    tags = []

    # Always include the school as a tag
    tags.append(school.lower())

    # Add 1-3 school-specific tags
    school_tags = TAG_POOLS.get(school, [])
    if school_tags:
        num_tags = random.randint(1, min(3, len(school_tags)))
        for tag in random.sample(school_tags, num_tags):
            if tag not in tags:
                tags.append(tag)

    # Add level-based tags
    if level == 0:
        tags.append("cantrip")
    elif level >= 7:
        tags.append("epic")
    elif level >= 5:
        tags.append("powerful")

    # Add rarity tag if not Common
    if rarity != "Common":
        tags.append(rarity.lower().replace(" ", "-"))

    # Add damage type tag if applicable
    if damage_type and damage_type not in tags:
        tags.append(damage_type)

    return tags


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

def _reset_generated_names():
    """Clear the set of generated names. Called when a seed is set to ensure
    deterministic output across runs."""
    global _generated_names
    _generated_names = set()

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

    # Computed phrases for description templates
    duration_phrase = format_duration_phrase(duration)
    duration_phrase_cap = format_duration_phrase_cap(duration)
    hp_phrase = format_hp_phrase(count, hp)

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
        duration_phrase=duration_phrase,
        duration_phrase_cap=duration_phrase_cap,
        hp_phrase=hp_phrase,
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

    # Tags
    tags = generate_tags(school, level, damage_type if school == "Evocation" else None, rarity)

    # Mana cost
    mana_cost = calculate_mana_cost(level, school, rarity, casting_time, duration)

    # Scroll value (gold piece price)
    scroll_value = calculate_scroll_value(level, rarity)

    return Spell(
        name=name, school=school, level=level, rarity=rarity,
        casting_time=casting_time, rng=rng, duration=duration,
        verbal=verbal, somatic=somatic, material=material,
        description=description, incantation=incantation,
        verbal_detail=verbal_detail, somatic_detail=somatic_detail,
        backstory=backstory, sigil=sigil, diagram=diagram,
        higher_levels=higher_levels, tags=tags, mana_cost=mana_cost,
        scroll_value=scroll_value,
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

    # Rarity badge and mana cost on next line
    rarity_label = f"[{spell.rarity}]"
    mana_label = f"Mana: {spell.mana_cost}"
    gold_label = f"Scroll: {spell.scroll_value:,} gp"
    rarity_mana = f"{rarity_label}  {mana_label}  {gold_label}"
    rarity_display = f"{rc}{BOLD}{rarity_label}{rst}  {BOLD}Mana:{rst} {spell.mana_cost}  {BOLD}Scroll:{rst} {spell.scroll_value:,} gp" if color else rarity_mana
    rarity_pad = page_width - 6 - len(rarity_mana)
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
        hl_prefix = "At Higher Levels. "
        hl_lines = wrap_text(spell.higher_levels, width=page_width - 8,
                              first_line_width=page_width - 8 - len(hl_prefix))
        for idx, hl in enumerate(hl_lines):
            if idx == 0:
                prefix = f"  ║ {BOLD}At Higher Levels.{rst} " if color else "  ║ At Higher Levels. "
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

    # Tags
    if spell.tags:
        tags_str = ", ".join(spell.tags)
        lines.append(f"  ║{' ' * (page_width - 4)}║")
        tag_lines = wrap_text(tags_str, width=page_width - 8)
        for tl in tag_lines:
            t_pad = page_width - 6 - len(tl)
            lines.append(f"  ║ {DIM}{tl}{rst}{' ' * max(t_pad, 0)} ║")

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


def render_side_by_side(spell1: Spell, spell2: Spell, color: bool = True) -> str:
    """Render two spells side by side for comparison."""
    page1 = render_grimoire_page(spell1, color=color)
    page2 = render_grimoire_page(spell2, color=color)

    lines1 = page1.split("\n")
    lines2 = page2.split("\n")

    max_lines = max(len(lines1), len(lines2))
    # Pad shorter page
    while len(lines1) < max_lines:
        lines1.append("")
    while len(lines2) < max_lines:
        lines2.append("")

    separator = " │ "
    result_lines = []
    for l1, l2 in zip(lines1, lines2):
        # Ensure each side is the same visible width for alignment
        l1_clean = strip_ansi(l1) if color else l1
        l2_clean = strip_ansi(l2) if color else l2
        # Pad to visible width of 64 (standard page width)
        l1_padded = l1 + " " * max(0, 64 - len(l1_clean))
        l2_padded = l2 + " " * max(0, 64 - len(l2_clean))
        result_lines.append(f"{l1_padded}{separator}{l2_padded}")

    return "\n".join(result_lines)


# ──────────────────────────────────────────────
# Grimoire (collection of spells)
# ──────────────────────────────────────────────

def generate_grimoire(num_spells: int = 5, school: Optional[str] = None,
                      level: Optional[int] = None, rarity: Optional[str] = None,
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
    title = "G R I M O I R E   O F   S P E L L S"
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
        spell = generate_spell(school=school, level=level, rarity=rarity)
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
                        level: Optional[int] = None, rarity: Optional[str] = None,
                        color: bool = True) -> str:
    """Generate a compact spell list."""
    lines = []
    # Updated header to include Scroll Value column
    lines.append(f"  {'Rarity':<12} {'Level':<8} {'Mana':<6} {'Scroll':<10} {'School':<14} {'Spell Name':<30}")
    lines.append(f"  {'─' * 12} {'─' * 8} {'─' * 6} {'─' * 10} {'─' * 14} {'─' * 30}")

    for _ in range(num_spells):
        spell = generate_spell(school=school, level=level, rarity=rarity)
        sc = SCHOOL_COLORS.get(spell.school, "") if color else ""
        rc = RARITIES.get(spell.rarity, {}).get("color", "") if color else ""
        rst = RESET if color else ""
        level_str = SPELL_LEVELS[spell.level]
        rarity_str = spell.rarity
        mana_str = str(spell.mana_cost)
        lines.append(
            f"  {rc}{rarity_str:<12}{rst} {level_str:<8} {mana_str:<6} {f'{spell.scroll_value:,} gp':<10} "
            f"{sc}{spell.school:<14}{rst} {sc}{BOLD}{spell.name:<30}{rst}"
        )

    result = "\n".join(lines)
    if not color:
        result = strip_ansi(result)
    return result


# ──────────────────────────────────────────────
# Spell synergy detection
# ──────────────────────────────────────────────

def find_synergies(spells: List[Spell]) -> List[Tuple[Spell, Spell, str]]:
    """Find pairs of spells that synergize well together.

    Returns a list of (spell1, spell2, description) tuples.
    """
    synergies = []
    for i in range(len(spells)):
        for j in range(i + 1, len(spells)):
            s1, s2 = spells[i], spells[j]
            # Check both orderings
            key1 = (s1.school, s2.school)
            key2 = (s2.school, s1.school)
            desc = SYNERGY_PAIRS.get(key1) or SYNERGY_PAIRS.get(key2)
            if desc:
                synergies.append((s1, s2, desc))
    return synergies


def render_synergies(spells: List[Spell], color: bool = True) -> str:
    """Render synergy report for a list of spells."""
    synergies = find_synergies(spells)
    if not synergies:
        return f"  {'No synergies found between these spells.'}"

    lines = [f"  {BOLD}⚡ Spell Synergies{RST if color else ''}", ""]
    for s1, s2, desc in synergies:
        sc1 = SCHOOL_COLORS.get(s1.school, "") if color else ""
        sc2 = SCHOOL_COLORS.get(s2.school, "") if color else ""
        rst = RST if color else ""
        lines.append(f"  {sc1}{BOLD if color else ''}{s1.name}{rst} × {sc2}{BOLD if color else ''}{s2.name}{rst}")
        lines.append(f"    {DIM if color else ''}{desc}{rst}")
        lines.append("")
    return "\n".join(lines)


# ──────────────────────────────────────────────
# Statistical analysis
# ──────────────────────────────────────────────

def render_stats(spells: List[Spell], color: bool = True) -> str:
    """Render a statistical summary of a list of spells.

    Shows breakdown by school, level, rarity; average mana cost,
    total scroll value, and other aggregate metrics.
    """
    if not spells:
        return "  No spells to analyze."

    rst = RST if color else ""
    bold = BOLD if color else ""
    dim = DIM if color else ""
    sc_cache = SCHOOL_COLORS if color else {s: "" for s in SCHOOLS}

    total = len(spells)

    # School breakdown
    school_counts: Dict[str, int] = {}
    for s in spells:
        school_counts[s.school] = school_counts.get(s.school, 0) + 1

    # Level breakdown
    level_counts: Dict[int, int] = {}
    for s in spells:
        level_counts[s.level] = level_counts.get(s.level, 0) + 1

    # Rarity breakdown
    rarity_counts: Dict[str, int] = {}
    for s in spells:
        rarity_counts[s.rarity] = rarity_counts.get(s.rarity, 0) + 1

    # Mana cost stats
    mana_costs = [s.mana_cost for s in spells]
    avg_mana = sum(mana_costs) / len(mana_costs)
    min_mana = min(mana_costs)
    max_mana = max(mana_costs)

    # Scroll value stats
    scroll_values = [s.scroll_value for s in spells]
    total_scroll = sum(scroll_values)
    avg_scroll = total_scroll / len(scroll_values)

    lines = [
        f"  {bold}📊 Spell Statistics{rst}",
        f"  {dim}{'─' * 50}{rst}",
        "",
        f"  {bold}Total Spells:{rst}      {total}",
        "",
        f"  {bold}By School:{rst}",
    ]
    for school in SCHOOLS:
        cnt = school_counts.get(school, 0)
        if cnt > 0:
            bar = "█" * cnt + "░" * (max(school_counts.values()) - cnt)
            lines.append(f"    {sc_cache.get(school, '')}{school:<14}{rst} {cnt:>2}  {bar}")

    lines.extend([
        "",
        f"  {bold}By Level:{rst}",
    ])
    for lvl in range(10):
        cnt = level_counts.get(lvl, 0)
        if cnt > 0:
            bar = "█" * cnt + "░" * (max(level_counts.values()) - cnt)
            lines.append(f"    {SPELL_LEVELS[lvl]:<8} {cnt:>2}  {bar}")

    lines.extend([
        "",
        f"  {bold}By Rarity:{rst}",
    ])
    for rarity in RARITIES:
        cnt = rarity_counts.get(rarity, 0)
        if cnt > 0:
            rc = RARITIES[rarity]["color"] if color else ""
            lines.append(f"    {rc}{rarity:<12}{rst} {cnt:>2}")

    lines.extend([
        "",
        f"  {bold}Mana Cost:{rst}       avg {avg_mana:.1f}  (min {min_mana}, max {max_mana})",
        f"  {bold}Scroll Value:{rst}     total {total_scroll:,} gp  (avg {avg_scroll:,.0f} gp)",
    ])

    return "\n".join(lines)


# ──────────────────────────────────────────────
# Save/Load spells
# ──────────────────────────────────────────────

def save_spells(spells: List[Spell], filepath: str) -> None:
    """Save a list of spells to a JSON file."""
    data = [spell.to_dict() for spell in spells]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_spells(filepath: str) -> List[Spell]:
    """Load spells from a JSON file.

    Returns a list of Spell objects reconstructed from the file.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    spells = []
    for d in data:
        # Remove computed fields that aren't constructor params
        # (tags and mana_cost might be missing in old files)
        spell = Spell(
            name=d["name"],
            school=d["school"],
            level=d["level"],
            casting_time=d["casting_time"],
            rng=d["rng"],
            duration=d["duration"],
            verbal=d["verbal"],
            somatic=d["somatic"],
            material=d["material"],
            description=d["description"],
            incantation=d["incantation"],
            verbal_detail=d["verbal_detail"],
            somatic_detail=d["somatic_detail"],
            backstory=d["backstory"],
            sigil=d["sigil"],
            diagram=d["diagram"],
            higher_levels=d.get("higher_levels", ""),
            rarity=d.get("rarity", "Common"),
            tags=d.get("tags", []),
            mana_cost=d.get("mana_cost", 0),
            scroll_value=d.get("scroll_value", calculate_scroll_value(d.get("level", 0), d.get("rarity", "Common"))),
        )
        spells.append(spell)
    return spells


# ──────────────────────────────────────────────
# Interactive mode
# ──────────────────────────────────────────────

def interactive_mode():
    """Run an interactive grimoire browser."""
    print(f"\n{BOLD}{UNDERLINE}📜 Procedural Spell Grimoire Generator v{__version__}{RST}")
    print(f"{DIM}Generate unique spells for your fantasy RPG campaigns{RST}\n")

    history: List[Spell] = []

    while True:
        print(f"\n{BOLD}Options:{RST}")
        print("  1. Generate a random spell")
        print("  2. Generate a spell from a specific school")
        print("  3. Generate a grimoire (5 spells)")
        print("  4. Generate a spell list (10 spells)")
        print("  5. Browse spells by level")
        print("  6. Browse spells by rarity")
        print("  7. Compare two spells side-by-side")
        print("  8. Find synergies in recent spells")
        print("  9. View spell history")
        print("  c. Find conflicts in recent spells")
        print("  t. View statistics")
        print("  s. Save spells to file")
        print("  l. Load spells from file")
        print("  q. Quit")
        print()

        choice = input(f"{BOLD}Choose [1-9/c/t/s/l/q]:{RST} ").strip().lower()

        if choice == "q":
            print(f"\n{DIM}May your spells always find their mark!{RST}\n")
            break
        elif choice == "1":
            spell = generate_spell()
            history.append(spell)
            print("\n" + render_grimoire_page(spell))
            print(f"\n{DIM}Tags: {', '.join(spell.tags)} | Mana: {spell.mana_cost} | Scroll: {spell.scroll_value:,} gp{RST}")
        elif choice == "2":
            print(f"\n{BOLD}Schools:{RST}")
            for i, school in enumerate(SCHOOLS, 1):
                sc = SCHOOL_COLORS.get(school, "")
                print(f"  {i}. {sc}{school}{RST}")
            try:
                s_choice = int(input(f"\n{BOLD}Choose school [1-8]:{RST} ").strip())
                if 1 <= s_choice <= 8:
                    spell = generate_spell(school=SCHOOLS[s_choice - 1])
                    history.append(spell)
                    print("\n" + render_grimoire_page(spell))
                    print(f"\n{DIM}Tags: {', '.join(spell.tags)} | Mana: {spell.mana_cost} | Scroll: {spell.scroll_value:,} gp{RST}")
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
                    history.append(spell)
                    print("\n" + render_grimoire_page(spell))
                    print(f"\n{DIM}Tags: {', '.join(spell.tags)} | Mana: {spell.mana_cost} | Scroll: {spell.scroll_value:,} gp{RST}")
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
                    history.append(spell)
                    print("\n" + render_grimoire_page(spell))
                    print(f"\n{DIM}Tags: {', '.join(spell.tags)} | Mana: {spell.mana_cost} | Scroll: {spell.scroll_value:,} gp{RST}")
                else:
                    print("Invalid choice.")
            except (ValueError, EOFError):
                print("Invalid choice.")
        elif choice == "7":
            # Compare two spells side-by-side
            if len(history) < 2:
                print("Generate at least 2 spells first (using options 1, 2, 5, or 6).")
                continue
            print(f"\n{BOLD}Recent spells:{RST}")
            for i, spell in enumerate(history[-10:], 1):
                sc = SCHOOL_COLORS.get(spell.school, "")
                print(f"  {i}. {sc}{spell.name}{RST} ({spell.school}, {SPELL_LEVELS[spell.level]})")
            try:
                idx1 = int(input(f"\n{BOLD}First spell #:{RST} ").strip()) - 1
                idx2 = int(input(f"{BOLD}Second spell #:{RST} ").strip()) - 1
                recent = history[-10:]
                if 0 <= idx1 < len(recent) and 0 <= idx2 < len(recent) and idx1 != idx2:
                    print("\n" + render_side_by_side(recent[idx1], recent[idx2]))
                else:
                    print("Invalid selection.")
            except (ValueError, EOFError):
                print("Invalid input.")
        elif choice == "8":
            # Find synergies
            if len(history) < 2:
                print("Generate at least 2 spells first to find synergies.")
                continue
            print("\n" + render_synergies(history[-10:]))
        elif choice == "9":
            # View history
            if not history:
                print("No spells generated yet in this session.")
                continue
            print(f"\n{BOLD}📜 Spell History ({len(history)} spells):{RST}")
            for i, spell in enumerate(history, 1):
                sc = SCHOOL_COLORS.get(spell.school, "")
                rc = RARITIES.get(spell.rarity, {}).get("color", "")
                print(f"  {i}. {sc}{BOLD}{spell.name}{RST} — "
                      f"{rc}[{spell.rarity}]{RST} {SPELL_LEVELS[spell.level]} "
                      f"{spell.school} (Mana: {spell.mana_cost}, Scroll: {spell.scroll_value:,} gp)")
        elif choice == "c":
            # Find conflicts
            if len(history) < 2:
                print("Generate at least 2 spells first to find conflicts.")
                continue
            print("\n" + render_conflicts(history[-10:]))
        elif choice == "t":
            # View statistics
            if not history:
                print("No spells to analyze. Generate some first!")
                continue
            print("\n" + render_stats(history))
        elif choice == "s":
            # Save spells
            if not history:
                print("No spells to save. Generate some first!")
                continue
            filepath = input(f"{BOLD}File path:{RST} ").strip()
            if not filepath:
                print("No path specified.")
                continue
            try:
                save_spells(history, filepath)
                print(f"{BOLD}Saved {len(history)} spells to {filepath}{RST}")
            except OSError as e:
                print(f"Error saving: {e}")
        elif choice == "l":
            # Load spells
            filepath = input(f"{BOLD}File path:{RST} ").strip()
            if not filepath:
                print("No path specified.")
                continue
            try:
                loaded = load_spells(filepath)
                history.extend(loaded)
                print(f"{BOLD}Loaded {len(loaded)} spells from {filepath}{RST}")
                for spell in loaded:
                    print(f"  - {spell.name} ({SPELL_LEVELS[spell.level]} {spell.school})")
            except (OSError, json.JSONDecodeError, KeyError) as e:
                print(f"Error loading: {e}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=f"Procedural Spell Grimoire Generator v{__version__} — Create unique fantasy RPG spells",
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
  %(prog)s --markdown                Output spell as Markdown
  %(prog)s --html                    Output spell as a standalone HTML page
  %(prog)s --compare                 Compare two random spells
  %(prog)s --synergies 5             Find synergies among 5 random spells
  %(prog)s --conflicts 5             Find conflicts among 5 random spells
  %(prog)s --stats 20               Show statistics for 20 random spells
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
    parser.add_argument("--markdown", "-m", action="store_true",
                        help="Output spell as Markdown")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Enter interactive mode")
    parser.add_argument("--compare", action="store_true",
                        help="Compare two random spells side by side")
    parser.add_argument("--synergies", type=int, metavar="N",
                        help="Find synergies among N random spells")
    parser.add_argument("--conflicts", type=int, metavar="N",
                        help="Find conflicts among N random spells")
    parser.add_argument("--stats", type=int, metavar="N",
                        help="Show statistics for N random spells")
    parser.add_argument("--html", action="store_true",
                        help="Output spell as a standalone HTML document")
    parser.add_argument("--save", type=str, metavar="FILE",
                        help="Save generated spells to a JSON file")
    parser.add_argument("--load", type=str, metavar="FILE",
                        help="Load and display spells from a JSON file")
    parser.add_argument("--seed", type=int,
                        help="Random seed for reproducible spells")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        _reset_generated_names()

    color = not args.no_color

    if args.interactive:
        interactive_mode()
        return

    # Load and display saved spells
    if args.load:
        try:
            loaded = load_spells(args.load)
            if args.json:
                data = [s.to_dict() for s in loaded]
                print(json.dumps(data, indent=2, ensure_ascii=False))
            elif args.markdown:
                for spell in loaded:
                    print(spell.to_markdown())
                    print()
            elif args.html:
                for spell in loaded:
                    print(spell.to_html())
            else:
                for spell in loaded:
                    print(render_grimoire_page(spell, color=color))
                    print()
        except (OSError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading spells from {args.load}: {e}", file=sys.stderr)
            sys.exit(1)
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

    if args.markdown:
        # Markdown output mode
        num = max(args.count, 1)
        md_parts = []
        spells_list = []
        for _ in range(num):
            spell = generate_spell(school=args.school, level=args.level, rarity=args.rarity)
            spells_list.append(spell)
            md_parts.append(spell.to_markdown())
        output = "\n\n---\n\n".join(md_parts)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"Markdown written to {args.output}")
            except OSError as e:
                print(f"Error writing to {args.output}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(output)

        # Save if requested
        if args.save:
            save_spells(spells_list, args.save)
            print(f"Saved {len(spells_list)} spells to {args.save}")
        return

    # HTML output mode
    if args.html:
        num = max(args.count, 1)
        html_parts = []
        spells_list = []
        for i in range(num):
            spell = generate_spell(school=args.school, level=args.level, rarity=args.rarity)
            spells_list.append(spell)
            html_parts.append(spell.to_html())
        if num == 1:
            output = html_parts[0]
        else:
            # Multiple spells: combine into a single HTML document
            level_str = SPELL_LEVELS[args.level] if args.level is not None else "Various"
            school_str = args.school or "All Schools"
            combined = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Grimoire — {html_escape(school_str)} Spells</title>
  <style>
    body {{
      font-family: 'Georgia', 'Times New Roman', serif;
      max-width: 700px;
      margin: 2rem auto;
      padding: 0 1rem;
      background: #1a1a2e;
      color: #e0e0e0;
    }}
    h1 {{ color: #f0c040; border-bottom: 2px solid #f0c040; padding-bottom: 0.5rem; }}
    h2 {{ color: #a0a0ff; margin-top: 1.5rem; }}
    h3 {{ color: #c0c0c0; }}
    hr {{ border: 1px solid #404060; margin: 2rem 0; }}
    .meta {{ background: #252540; border-radius: 8px; padding: 1rem; margin: 1rem 0; }}
    .meta dt {{ font-weight: bold; color: #f0c040; }}
    .meta dd {{ margin-left: 1rem; margin-bottom: 0.3rem; }}
    .badge {{ display: inline-block; background: #404080; color: #ffffff; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.9rem; }}
    .badge.legendary {{ background: #f0c040; color: #1a1a2e; }}
    .badge.very-rare {{ background: #a020f0; color: #ffffff; }}
    .badge.rare {{ background: #4060e0; color: #ffffff; }}
    .badge.uncommon {{ background: #20a020; color: #ffffff; }}
    .badge.common {{ background: #808080; color: #ffffff; }}
    .section {{ margin: 1rem 0; }}
    pre {{ background: #101020; padding: 1rem; border-radius: 4px; overflow-x: auto; color: #c0ffc0; font-size: 0.85rem; }}
    .tags li {{ display: inline-block; background: #303060; padding: 0.15rem 0.5rem; border-radius: 12px; margin: 0.2rem; font-size: 0.85rem; }}
    .incantation {{ font-style: italic; color: #d0a0ff; border-left: 3px solid #d0a0ff; padding-left: 1rem; margin: 1rem 0; }}
    .lore {{ color: #a0a0a0; font-style: italic; }}
    .gold {{ color: #f0c040; }}
    .mana {{ color: #40c0ff; }}
  </style>
</head>
<body>
  <h1>Grimoire — {html_escape(school_str)} Spells</h1>
"""
            for i, (spell, html) in enumerate(zip(spells_list, html_parts)):
                # Extract just the <body> content from each spell's HTML
                import re as _re
                body_match = _re.search(r'<body>(.*)</body>', html, _re.DOTALL)
                body_content = body_match.group(1) if body_match else html
                if i > 0:
                    combined += "\n  <hr>\n"
                combined += f"\n{body_content}\n"
            combined += "\n</body>\n</html>"
            output = combined

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"HTML written to {args.output}")
            except OSError as e:
                print(f"Error writing to {args.output}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(output)

        # Save if requested
        if args.save:
            save_spells(spells_list, args.save)
            print(f"Saved {len(spells_list)} spells to {args.save}")
        return

    # Compare mode
    if args.compare:
        spell1 = generate_spell(school=args.school, level=args.level, rarity=args.rarity)
        spell2 = generate_spell(school=args.school, level=args.level, rarity=args.rarity)
        output = render_side_by_side(spell1, spell2, color=color)
        print(output)

        if args.save:
            save_spells([spell1, spell2], args.save)
            print(f"Saved 2 spells to {args.save}")
        return

    # Synergy mode
    if args.synergies:
        num = args.synergies
        spells_list = []
        for _ in range(num):
            spell = generate_spell(school=args.school, level=args.level, rarity=args.rarity)
            spells_list.append(spell)

        # Show each spell
        for spell in spells_list:
            print(render_grimoire_page(spell, color=color))
            print()

        # Show synergies
        print(render_synergies(spells_list, color=color))

        if args.save:
            save_spells(spells_list, args.save)
            print(f"Saved {len(spells_list)} spells to {args.save}")
        return

    # Conflict mode
    if args.conflicts:
        num = args.conflicts
        spells_list = []
        for _ in range(num):
            spell = generate_spell(school=args.school, level=args.level, rarity=args.rarity)
            spells_list.append(spell)

        # Show each spell
        for spell in spells_list:
            print(render_grimoire_page(spell, color=color))
            print()

        # Show conflicts
        print(render_conflicts(spells_list, color=color))

        if args.save:
            save_spells(spells_list, args.save)
            print(f"Saved {len(spells_list)} spells to {args.save}")
        return

    # Stats mode
    if args.stats:
        num = args.stats
        spells_list = []
        for _ in range(num):
            spell = generate_spell(school=args.school, level=args.level, rarity=args.rarity)
            spells_list.append(spell)

        print(render_stats(spells_list, color=color))

        if args.save:
            save_spells(spells_list, args.save)
            print(f"Saved {len(spells_list)} spells to {args.save}")
        return

    if args.grimoire:
        # Generate spells for grimoire mode and collect them for saving
        num_spells = 5
        spells_list = []
        pages = []
        grimoire_school = args.school
        if color and grimoire_school and grimoire_school in SCHOOL_COLORS:
            sc = SCHOOL_COLORS[grimoire_school]
        else:
            sc = ""
        rst = RESET if color else ""
        pw = 64
        title = "G R I M O I R E   O F   S P E L L S"
        content_width = pw - 4
        title_pad_left = (content_width - len(title)) // 2
        title_pad_right = content_width - len(title) - title_pad_left
        lines = []
        lines.append(f"  {sc}╔{'═' * (pw - 4)}╗{rst}")
        lines.append(f"  {sc}║{' ' * (pw - 4)}║{rst}")
        lines.append(f"  {sc}║{' ' * title_pad_left}{title}{' ' * title_pad_right}║{rst}")
        lines.append(f"  {sc}║{' ' * (pw - 4)}║{rst}")
        sep = f"{'─' * 50}"
        sep_pad = pw - 6 - len(sep)
        lines.append(f"  {sc}║ {sep}{' ' * max(sep_pad, 0)} ║{rst}")
        if grimoire_school:
            school_line = f"School of {grimoire_school}"
            school_pad = pw - 6 - len(school_line)
            lines.append(f"  {sc}║ {BOLD}{school_line}{rst}{sc}{' ' * max(school_pad, 0)} ║{rst}")
        lines.append(f"  {sc}║{' ' * (pw - 4)}║{rst}")
        lines.append(f"  {sc}╚{'═' * (pw - 4)}╝{rst}")
        header = "\n".join(lines)
        pages.append(header)

        for i in range(num_spells):
            spell = generate_spell(school=grimoire_school, level=args.level, rarity=args.rarity)
            spells_list.append(spell)
            page = render_grimoire_page(spell, color=color)
            pages.append(page)
            if i < num_spells - 1:
                pages.append("\n")

        output = "\n".join(pages)
        if not color:
            output = strip_ansi(output)

    elif args.list:
        # Generate spells for list mode and collect them for saving
        num_spells = args.list
        spells_list = []
        list_lines = []
        list_lines.append(f"  {'Rarity':<12} {'Level':<8} {'Mana':<6} {'Scroll':<10} {'School':<14} {'Spell Name':<30}")
        list_lines.append(f"  {'─' * 12} {'─' * 8} {'─' * 6} {'─' * 10} {'─' * 14} {'─' * 30}")

        for _ in range(num_spells):
            spell = generate_spell(school=args.school, level=args.level, rarity=args.rarity)
            spells_list.append(spell)
            sc = SCHOOL_COLORS.get(spell.school, "") if color else ""
            rc = RARITIES.get(spell.rarity, {}).get("color", "") if color else ""
            rst = RESET if color else ""
            level_str = SPELL_LEVELS[spell.level]
            rarity_str = spell.rarity
            mana_str = str(spell.mana_cost)
            scroll_str = f"{spell.scroll_value:,} gp"
            list_lines.append(
                f"  {rc}{rarity_str:<12}{rst} {level_str:<8} {mana_str:<6} {scroll_str:<10} "
                f"{sc}{spell.school:<14}{rst} {sc}{BOLD}{spell.name:<30}{rst}"
            )

        output = "\n".join(list_lines)
        if not color:
            output = strip_ansi(output)
    else:
        # Generate one or more individual spells
        num = max(args.count, 1)
        pages = []
        spells_list = []
        for _ in range(num):
            spell = generate_spell(school=args.school, level=args.level, rarity=args.rarity)
            spells_list.append(spell)
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

    # Save spells if requested
    if args.save and not args.synergies and not args.compare:
        save_spells(spells_list, args.save)
        print(f"Saved {len(spells_list)} spells to {args.save}")


if __name__ == "__main__":
    main()