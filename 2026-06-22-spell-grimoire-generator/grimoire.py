#!/usr/bin/env python3
"""
Procedural Spell Grimoire Generator
=====================================
Generates beautifully formatted grimoire pages for fantasy RPG spells
with procedural names, ASCII art, incantations, reagents, and metadata.
"""

import random
import math
import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Optional

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
        "Animates {count} undead servants for {duration}, each with {hp} HP.",
        "Target must make a WIS save or take {dice}d{sides} necrotic damage and be frightened.",
        "Creates a {area}-foot zone of negative energy. Living creatures take {dice}d{sides} damage.",
    ],
    "Enchantment": [
        "Target must make a WIS save or become {condition} for {duration}.",
        "Up to {count} creatures become {condition} for {duration}.",
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
        "Summons {count} {creature_type} for {duration}.",
        "Opens a portal to {plane} lasting {duration}.",
        "Teleports the caster and up to {count} allies to a location within {area} miles.",
        "Conjures a {area}-foot dome of {material_to} lasting {duration_short}.",
    ],
    "Abjuration": [
        "Creates a {area}-foot radius anti-magic field for {duration}.",
        "Grants {count} creatures resistance to {damage_type} for {duration}.",
        "Dispels all magical effects of level {level} or lower in a {area}-foot radius.",
        "Creates a magical barrier with {hp} HP that lasts for {duration} or until destroyed.",
    ],
    "Divination": [
        "Reveals the location of {count} hidden objects within {area} feet.",
        "The caster receives a vision of events up to {count} days in the future.",
        "For {duration}, the caster can see through walls and illusions within {area} feet.",
        "Answers {count} yes/no questions about the future with 90% accuracy.",
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
    """Generate a procedural arcane sigil based on school and level."""
    lines = []
    random.seed(hash(school) + level * 137)  # Deterministic per school+level

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

    random.seed()  # Reset random seed
    return lines


def generate_border(width: int, school: str) -> str:
    """Generate a decorative border line."""
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
    random.seed()
    return pattern


def generate_spell_diagram(school: str, level: int) -> List[str]:
    """Generate a procedural geometric spell diagram."""
    lines = []
    width = 35
    height = 13
    center_x = width // 2
    center_y = height // 2

    grid = [[" " for _ in range(width)] for _ in range(height)]

    random.seed(hash(school) * 1000 + level * 7 + 999)

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

    random.seed()
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


# ──────────────────────────────────────────────
# Generation
# ──────────────────────────────────────────────

def generate_spell(school: Optional[str] = None, level: Optional[int] = None) -> Spell:
    """Generate a complete procedural spell."""
    if school is None:
        school = random.choice(SCHOOLS)
    if level is None:
        level = random.randint(0, 9)

    # Generate name
    if random.random() < 0.6 or level == 0:
        name = f"{random.choice(PREFIXES)} {random.choice(ROOTS[school])}"
    else:
        name = f"{random.choice(PREFIXES)} {random.choice(ROOTS[school])} of {random.choice(PREFIXES)} {random.choice(ROOTS[school])}"

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

    description = template.format(
        dice=dice, sides=sides, damage_type=damage_type, area=area,
        condition=condition, duration=duration_short, duration_short=duration_short, count=count,
        hp=hp, illusion=illusion, creature_type=creature_type,
        plane=plane, material_from=material_from, material_to=material_to,
        size=size, ability=ability, level=level,
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

    # Higher levels
    if level > 0 and level < 9:
        higher_levels = (
            f"When cast using a spell slot of {level + 1}th level or higher, "
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
    )

    return Spell(
        name=name, school=school, level=level,
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

def wrap_text(text: str, width: int = 58) -> List[str]:
    """Word-wrap text to a given width."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}" if current else word
    if current:
        lines.append(current)
    return lines


def render_grimoire_page(spell: Spell, color: bool = True) -> str:
    """Render a full grimoire page for a spell."""
    page_width = 64

    sc = SCHOOL_COLORS.get(spell.school, "") if color else ""
    rst = RST if color else ""

    lines = []

    # Top border
    top_border = f"  ╔{'═' * (page_width - 4)}╗"
    lines.append(top_border)

    # School and level header
    level_str = SPELL_LEVELS[spell.level]
    header = f"{spell.school} — {level_str} Level"
    if len(spell.school) > 0:
        pad = page_width - 6 - len(header)
        # account for ANSI codes
        header_display = f"{sc}{header}{rst}" if color else header
        lines.append(f"  ║ {header_display}{' ' * (pad)} ║")

    lines.append(f"  ╠{'═' * (page_width - 4)}╣")

    # Spell name (centered)
    name_display = f"{BOLD}{sc}{spell.name}{rst}" if color else spell.name
    name_pad = page_width - 6 - len(spell.name)
    lines.append(f"  ║ {name_display}{' ' * name_pad} ║")

    # Decorative line
    lines.append(f"  ╠{'─' * (page_width - 4)}╣")

    # Metadata
    def meta_line(label: str, value: str) -> str:
        lbl = f"{BOLD}{label}:{rst}" if color else f"{label}:"
        content = f"{lbl} {value}"
        content_pad = page_width - 6 - len(label) - 2 - len(value)
        # We need to handle ANSI codes length
        actual_content = f"{BOLD}{label}:{rst} {value}" if color else f"{label}: {value}"
        # Calculate padding based on visible width
        visible_len = len(label) + 2 + len(value) + 1
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
            ml_pad = page_width - 6 - len(ml)
            lines.append(f"  ║   {DIM}{ml}{rst}{' ' * max(ml_pad - 3, 0)} ║")

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
    for i, dl in enumerate(desc_lines):
        prefix = f"  ║ {ITALIC}" if color else "  ║ "
        suffix = f"{rst}" if color else ""
        dl_pad = page_width - 6 - len(dl)
        lines.append(f"{prefix}{dl}{suffix}{' ' * max(dl_pad, 0)} ║")

    if spell.higher_levels:
        lines.append(f"  ║{' ' * (page_width - 4)}║")
        hl_lines = wrap_text(spell.higher_levels, width=page_width - 8)
        for hl in hl_lines:
            prefix = f"  ║ {BOLD}At Higher Levels.{rst} " if hl == hl_lines[0] and color else f"  ║ "
            hl_pad = page_width - 6 - len(hl)
            lines.append(f"{prefix}{hl}{' ' * max(hl_pad - len(prefix) + 6, 0)} ║")

    lines.append(f"  ║{' ' * (page_width - 4)}║")

    # Component details
    lines.append(f"  ╠{'─' * (page_width - 4)}╣")
    lines.append(f"  ║{' ' * (page_width - 4)}║")

    if spell.verbal:
        v_label = f"{BOLD}Verbal:{rst} " if color else "Verbal: "
        v_text = spell.verbal_detail
        v_all = v_label + v_text
        v_lines = wrap_text(v_all, width=page_width - 8)
        # Remove ANSI from wrap calculation
        v_lines_plain = wrap_text(f"Verbal: {v_text}", width=page_width - 8)
        for vl in v_lines_plain:
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
        il_pad = page_width - 6 - len(il) - 2
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
    """Render a grimoire page without ANSI color codes."""
    return render_grimoire_page(spell, color=False)


# ──────────────────────────────────────────────
# Grimoire (collection of spells)
# ──────────────────────────────────────────────

def generate_grimoire(num_spells: int = 5, school: Optional[str] = None, color: bool = True) -> str:
    """Generate a full grimoire with multiple spells."""
    pages = []
    title = "═══════════════════════════════════════════"
    subtitle = "        G R I M O I R E        "

    sc = ""
    rst = ""
    if color and school and school in SCHOOL_COLORS:
        sc = SCHOOL_COLORS[school]
        rst = RESET

    header = f"""
  {sc}╔════════════════════════════════════════════════════════════╗{rst}
  {sc}║                                                          ║{rst}
  {sc}║           G R I M O I R E   O F   S P E L L S            ║{rst}
  {sc}║                                                          ║{rst}
  {sc}║     {'─' * 50}     ║{rst}
  {sc}║                                                          ║{rst}"""

    if school:
        header += f"""
  {sc}║     {BOLD}School of {school}{rst}{sc}                                       ║{rst}"""

    header += f"""
  {sc}║                                                          ║{rst}
  {sc}╚════════════════════════════════════════════════════════════╝{rst}
"""

    pages.append(header)

    for i in range(num_spells):
        spell = generate_spell(school=school)
        page = render_grimoire_page(spell, color=color)
        pages.append(page)
        if i < num_spells - 1:
            pages.append("\n")

    return "\n".join(pages)


# ──────────────────────────────────────────────
# Spell list mode (compact table)
# ──────────────────────────────────────────────

def generate_spell_list(num_spells: int = 10, school: Optional[str] = None, color: bool = True) -> str:
    """Generate a compact spell list."""
    lines = []
    lines.append(f"  {'Level':<8} {'School':<14} {'Spell Name':<30}")
    lines.append(f"  {'─' * 8} {'─' * 14} {'─' * 30}")

    for _ in range(num_spells):
        spell = generate_spell(school=school)
        sc = SCHOOL_COLORS.get(spell.school, "") if color else ""
        rst = RESET if color else ""
        level_str = SPELL_LEVELS[spell.level]
        lines.append(f"  {level_str:<8} {sc}{spell.school:<14}{rst} {sc}{BOLD}{spell.name:<30}{rst}")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# Interactive mode
# ──────────────────────────────────────────────

def interactive_mode():
    """Run an interactive grimoire browser."""
    print(f"\n{BOLD}{UNDERLINE}📜 Procedural Spell Grimoire Generator{rst}")
    print(f"{DIM}Generate unique spells for your fantasy RPG campaigns{rst}\n")

    while True:
        print(f"\n{BOLD}Options:{rst}")
        print("  1. Generate a random spell")
        print("  2. Generate a spell from a specific school")
        print("  3. Generate a grimoire (5 spells)")
        print("  4. Generate a spell list (10 spells)")
        print("  5. Browse spells by level")
        print("  q. Quit")
        print()

        choice = input(f"{BOLD}Choose [1-5/q]:{rst} ").strip().lower()

        if choice == "q":
            print(f"\n{DIM}May your spells always find their mark!{rst}\n")
            break
        elif choice == "1":
            spell = generate_spell()
            print("\n" + render_grimoire_page(spell))
        elif choice == "2":
            print(f"\n{BOLD}Schools:{rst}")
            for i, school in enumerate(SCHOOLS, 1):
                sc = SCHOOL_COLORS.get(school, "")
                print(f"  {i}. {sc}{school}{rst}")
            try:
                s_choice = int(input(f"\n{BOLD}Choose school [1-8]:{rst} ").strip())
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
                level = int(input(f"{BOLD}Spell level [0-9]:{rst} ").strip())
                if 0 <= level <= 9:
                    spell = generate_spell(level=level)
                    print("\n" + render_grimoire_page(spell))
                else:
                    print("Level must be 0-9.")
            except (ValueError, EOFError):
                print("Invalid input.")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Procedural Spell Grimoire Generator — Create unique fantasy RPG spells",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           Generate a random spell
  %(prog)s --grimoire                Generate a full 5-spell grimoire
  %(prog)s --school Necromancy       Generate a Necromancy spell
  %(prog)s --level 5                 Generate a 5th-level spell
  %(prog)s --list 20                 Show a list of 20 spells
  %(prog)s --no-color                Disable colored output
  %(prog)s --interactive             Enter interactive mode
  %(prog)s --grimoire --school Evocation --output grimoire.txt
        """,
    )
    parser.add_argument("--school", "-s", choices=SCHOOLS,
                        help="School of magic for the spell(s)")
    parser.add_argument("--level", "-l", type=int, choices=range(10),
                        help="Spell level (0-9)")
    parser.add_argument("--grimoire", "-g", action="store_true",
                        help="Generate a full grimoire (5 spells)")
    parser.add_argument("--list", "-n", type=int, metavar="COUNT",
                        help="Generate a compact list of COUNT spells")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output")
    parser.add_argument("--output", "-o", type=str,
                        help="Write output to file instead of stdout")
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

    if args.grimoire:
        output = generate_grimoire(num_spells=5, school=args.school, color=color)
    elif args.list:
        output = generate_spell_list(num_spells=args.list, school=args.school, color=color)
    else:
        spell = generate_spell(school=args.school, level=args.level)
        output = render_grimoire_page(spell, color=color)

    if args.output:
        # Strip ANSI for file output
        import re
        clean_output = re.sub(r'\033\[[0-9;]*m', '', output)
        with open(args.output, "w") as f:
            f.write(clean_output)
        print(f"Grimoire written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()