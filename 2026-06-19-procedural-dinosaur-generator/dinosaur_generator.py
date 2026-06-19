#!/usr/bin/env python3
"""
Procedural Dinosaur Generator
==============================
Generate random dinosaurs with scientifically-informed features,
ASCII art silhouettes, and collectible trading cards.

Each dinosaur gets:
  - A procedurally generated binomial name
  - An era, period, and habitat
  - Body type, diet, size, weight
  - Attack, defense, speed, intelligence stats
  - Special abilities
  - An ASCII art silhouette
  - A formatted "trading card" display

Features:
  - Interactive REPL with generation, battle, and collection tracking
  - Battle system with weighted stat calculation and randomness
  - DinoDex collection tracker with summaries and Wall of Fame
  - Tournament mode: bracket-style elimination
  - Side-by-side comparison of two dinosaurs
  - JSON export for each dinosaur
  - Seeded generation for reproducibility
  - --version and --help CLI flags

Version: 2.0.0
"""

import random
import math
import sys
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List

__version__ = "2.0.0"


# === Name Generation ==========================================================

GENUS_PREFIXES = [
    "Aero", "Allo", "Ankylo", "Apato", "Aralo", "Baryo", "Brachio", "Camaro",
    "Carcharo", "Carno", "Cerato", "Coelo", "Deino", "Diplo", "Draco",
    "Eoceno", "Erio", "Gigan", "Hadro", "Iguano", "Kentro", "Lystro",
    "Macro", "Megalo", "Micro", "Mono", "Neo", "Ornitho", "Ovi", "Pachy",
    "Para", "Pelo", "Philo", "Platy", "Pro", "Ptero", "Raptor", "Sauro",
    "Scolo", "Spino", "Stego", "Styraco", "Sucho", "Tani", "Theri", "Tita",
    "Tyranno", "Veloci", "Xeno", "Zephyro",
]

GENUS_SUFFIXES = [
    "saurus", "raptor", "don", "ceratops", "mimus", "phus", "teryx",
    "dactylus", "dus", "pelta", "pelis", "suchus", "titan", "dromeus",
    "ops", "chus", "pus", "rinx", "tholus", "gryphus", "venator",
    "morphus", "docus", "lophus", "nax", "pes", "dons", "gigas",
]

DESCRIPTIVE_EPITHETS = [
    "ferox", "magnus", "parvus", "velox", "robustus", "gracilis",
    "giganteus", "nanus", "crassus", "tenuis", "rudis", "nobilis",
    "atrox", "agilis", "armatus", "cornutus", "dens", "longus",
    "brevis", "latus", "striatus", "maculatus", "punctatus", "cristatus",
    "imperator", "rex", "augustus", "triumphans", "terribilis",
    "mirificus", "spectabilis", "elegans", "pulcher",
]

HABITAT_ADJECTIVES = {
    "forest": "silvanus",
    "desert": "arenosus",
    "swamp": "paluster",
    "mountain": "montanus",
    "plains": "campestris",
    "coastal": "littoralis",
    "arctic": "glacialis",
    "volcanic": "ignivomus",
    "river": "fluvialis",
    "cave": "spelaeus",
}


def generate_name(habitat: str) -> tuple:
    """Generate a random binomial dinosaur name.

    Combines Greek/Latin genus prefixes with taxonomic suffixes, and picks
    a species epithet that may reference the habitat, be purely descriptive,
    or form a compound name.

    Args:
        habitat: The dinosaur's habitat type (used to influence species name).

    Returns:
        A tuple of (genus, species) strings.
    """
    genus = random.choice(GENUS_PREFIXES) + random.choice(GENUS_SUFFIXES)
    style = random.random()
    if style < 0.4:
        species = random.choice(DESCRIPTIVE_EPITHETS)
    elif style < 0.7:
        species = HABITAT_ADJECTIVES.get(habitat, random.choice(DESCRIPTIVE_EPITHETS))
    else:
        species = random.choice(GENUS_PREFIXES).lower() + random.choice(GENUS_SUFFIXES)
    return genus, species


# === Dinosaur Data ============================================================

ERAS = [
    ("Triassic", (252, 201)),
    ("Jurassic", (201, 145)),
    ("Cretaceous", (145, 66)),
]

PERIODS_BY_ERA = {
    "Triassic": ["Early Triassic", "Middle Triassic", "Late Triassic"],
    "Jurassic": ["Early Jurassic", "Middle Jurassic", "Late Jurassic"],
    "Cretaceous": ["Early Cretaceous", "Late Cretaceous"],
}

HABITATS = ["forest", "desert", "swamp", "mountain", "plains", "coastal", "arctic", "volcanic", "river", "cave"]

BODY_TYPES = {
    "theropod": {
        "diet": "carnivore",
        "posture": "bipedal",
        "size_range": (1.5, 14),
        "weight_range": (10, 8000),
        "desc": "bipedal predator with sharp teeth and clawed hands",
    },
    "sauropod": {
        "diet": "herbivore",
        "posture": "quadrupedal",
        "size_range": (10, 40),
        "weight_range": (5000, 80000),
        "desc": "massive long-necked giant with pillar-like legs",
    },
    "ceratopsian": {
        "diet": "herbivore",
        "posture": "quadrupedal",
        "size_range": (2, 9),
        "weight_range": (100, 8000),
        "desc": "horned face with a bony frill and beak",
    },
    "ankylosaur": {
        "diet": "herbivore",
        "posture": "quadrupedal",
        "size_range": (3, 11),
        "weight_range": (500, 8000),
        "desc": "heavily armored body with a clubbed tail",
    },
    "stegosaur": {
        "diet": "herbivore",
        "posture": "quadrupedal",
        "size_range": (4, 9),
        "weight_range": (1000, 7000),
        "desc": "plates along the back and spiked tail",
    },
    "ornithopod": {
        "diet": "herbivore",
        "posture": "bipedal",
        "size_range": (1.5, 15),
        "weight_range": (20, 5000),
        "desc": "beaked herbivore capable of both bipedal and quadrupedal locomotion",
    },
    "pterosaur": {
        "diet": "carnivore",
        "posture": "quadrupedal (flying)",
        "size_range": (0.5, 10),
        "weight_range": (1, 250),
        "desc": "winged reptile with a membranous flight surface",
    },
    "therizinosaur": {
        "diet": "herbivore",
        "posture": "bipedal",
        "size_range": (3, 10),
        "weight_range": (500, 6000),
        "desc": "long-clawed theropod that convergently evolved herbivory",
    },
}

DIETS = ["carnivore", "herbivore", "omnivore", "piscivore", "insectivore"]

SKIN_PATTERNS = [
    "mottled green and brown",
    "striped orange and black",
    "speckled grey",
    "iridescent blue-green",
    "dusty tan with white underbelly",
    "dark forest green with red crest",
    "pale yellow with brown bands",
    "deep purple-black with gold accents",
    "snow white with silver streaks",
    "fiery red-orange with black tips",
    "olive drab with copper sheen",
    "ash grey with volcanic red spots",
]

SPECIAL_ABILITIES = {
    "theropod": [
        "Bone-crushing bite force",
        "Lightning-fast pursuit speed",
        "Intelligent pack hunting",
        "Serrated teeth that never dull",
        "Powerful leaping ambush",
    ],
    "sauropod": [
        "Earth-shaking stomp",
        "Whip-tail sonic boom",
        "Impenetrable hide",
        "Neck reach of 15 meters",
        "Herd defensive formation",
    ],
    "ceratopsian": [
        "Impaling horn charge",
        "Shield frill deflection",
        "Beak shear through bone",
        "Intimidation display",
        "Formation charging",
    ],
    "ankylosaur": [
        "Tail club devastator",
        "Armor plating deflection",
        "Low-center charge",
        "Belly splash defensive roll",
        "Spiked shoulder counters",
    ],
    "stegosaur": [
        "Thagomizer tail spike",
        "Plate thermoregulation",
        "Intimidating plate display",
        "Swiping tail defense",
        "Herding alarm calls",
    ],
    "ornithopod": [
        "Herd stampede",
        "Burrowing escape",
        "Blazing sprint speed",
        "Warning vocalization",
        "Adaptive digestion",
    ],
    "pterosaur": [
        "Aerial dive-bomb",
        "Echolocation hunting",
        "Wind-current gliding",
        "Beak spear attack",
        "Crepuscular ambush",
    ],
    "therizinosaur": [
        "Slashing claw fury",
        "Intimidating arm spread",
        "Dual-mode digestion",
        "Feathered insulation",
        "Territory marking claws",
    ],
}

FEATHER_TYPES = [
    "none (scaly hide)",
    "protofeathers on back",
    "full plumage",
    "display feathers on arms and tail",
    "downy chick feathers that molt",
    "bristle-like filaments",
]

EGG_TYPES = [
    "oval, 15cm long, buried in sand",
    "elongated, 20cm, hidden in vegetation",
    "round, 10cm, in mud nest",
    "oblong, 25cm, in earthen mound",
    "tiny, 5cm, in tree hollow",
    "soft-shelled, 12cm, in communal pit",
]

# Personality adjectives that add flavor
PERSONALITY_TRAITS = [
    "territorial", "curious", "aggressive", "docile", "nocturnal",
    "migratory", "solitary", "social", "cautious", "fearless",
    "ambush-oriented", "opportunistic", "pack-hunting", "nest-protective",
]


# === ASCII Art Templates ======================================================

ART_THEROPOD_LARGE = r"""
                          .-^^^^^-.
                         /        \\
                        /          \\
                  __   /    _   _   \\
                 /  \_/    / \ / \   \\
                /    |     \_/ \_/    \\
          ____ |  O  |      _   _      |
         /    \|     /     / \ / \     |
        |   O  \____/      \_/ \_/     |
        |      /              |        /
         \____/               |       /
            |               __|__    /
            |              |    |  /
            |              | O  | /
            \              |    |/
             \_____________|    |
                          |    |
                         _|    |_
                        |________|
""".strip()

ART_THEROPOD_SMALL = r"""
                       /\____/\
                      /        \
                     |  O    O |
                      \   __   /
                       | /  \ |
                      /| \__/ |\
                     / |      | \
                       /      \
                      /        \
                     |  |    |  |
                     |  |    |  |
                     /  /    \  \
""".strip()

ART_SAUROPOD = r"""
                                 ____
                          _..--^v    ^v--.._
                       .-'                  '-.
                      /                        \
                     /        __         __      \
                    |       /    \     /    \     |
                    |      | O  O|   | O  O|     |
                     \      \____/     \____/    /
                      '-._                _.-'
                          '-..        ..-'
                              |      |
                             /|      |\
                            / |      | \
                              |      |
                              |      |
                             /        \
                            /          \
                           /|          |\
                          / |          | \
                            |          |
                            |          |
                           /            \
                          /              \
""".strip()

ART_CERATOPSIA = r"""
                           __
                     _..--^  ^--.._
                  .-'    ____     '-.
                 /    .-'    '-.     \
                /    /   O  O  \     \
               |    |     __     |     |
               |     \   \/    /      |
                \     '.______.'      /
                 '._              _.'
                    '-..______..-'
                   /    |    |    \
                  |     |    |     |
                  |   O |    |  O  |
                  |     |____|     |
                   \    /    \    /
                    |  |      |  |
                    |  |      |  |
                   /   /      \   \
""".strip()

ART_ANKYLOSAUR = r"""
                        _..---^^---.._
                    .-'              '-.
                   /                    \
                  |  []  []  []  []  []  |
                  |   __    __    __    |
                   \ /  \ /  \ /  \  /
                   |____|____|____|____|
                  /                    \
                 |  O              O    |
                 |                      |
                  \                    /
                   '.              ,-'
                     '-..______..-'
                       |  |  |
                       |  |  |
                      /   /   \
                     /___/ \___\
""".strip()

ART_STEGOSAUR = r"""
                        ___
                      //||\\
                     // || \\
                    //  ||  \\
                   //   ||   \\
                  //    ||    \\
                 //_____||______\\
                 |______||_______|
                     |  ____  |
                     | /    \ |
                     |/ O  O \|
                      |\____/ |
                      |       |
                       \     /
                      __\   /__
                     /  |   |  \
                    /   |   |   \
                   /____|___|____\
                         |   |
                        /    \
                       /      \
""".strip()

ART_ORNITHOPOD = r"""
                       ___
                     /     \
                    |  O  O |
                     \  __  /
                     /|    |\
                    / |    | \
                   /  |____|  \
                  /            \
                 /    _    _    \
                |    / \  / \    |
                |    \_/  \_/    |
                 \              /
                  '.__        _.'
                     |        |
                     |   ||   |
                     |   ||   |
                     |   ||   |
                    /    ||    \
                   /_____||____\
""".strip()

ART_PTEROSAUR = r"""
                           _
                         /   \
                        / O   O\
                       /  ___   \
                      / /     \  \
                 ___/ /         \ \___
            ___/     /           \     \___
           /________/             \________\
                   /               \
                  /_________________\
                        |   |
                        |___|
                         / \
                        /   \
""".strip()

ART_THERIZINOSAUR = r"""
                          _..--^^--.._
                        /    ____    \
                       /    /    \    \
                      |    | O  O |    |
                      |     \____/     |
                       \    /    \    /
                        '--/      \--'
                     ___/ /|      |\ \___
                    /    / |      | \    \
                   /    /  |      |  \    \
                  |    |   |______|   |    |
                  |    |   /      \   |    |
                  |     \ /   __   \ /     |
                   \     |   /  \   |     /
                    \    |  /    \  |    /
                     \   |  \____/  |   /
                      \  |          |  /
                       \ |          | /
                        \|          |/
""".strip()

BODY_ART_MAP = {
    "theropod": [ART_THEROPOD_LARGE, ART_THEROPOD_SMALL],
    "sauropod": [ART_SAUROPOD],
    "ceratopsian": [ART_CERATOPSIA],
    "ankylosaur": [ART_ANKYLOSAUR],
    "stegosaur": [ART_STEGOSAUR],
    "ornithopod": [ART_ORNITHOPOD],
    "pterosaur": [ART_PTEROSAUR],
    "therizinosaur": [ART_THERIZINOSAUR],
}


# === Dinosaur Class ===========================================================

@dataclass
class Dinosaur:
    """A procedurally generated dinosaur with stats, appearance, and abilities."""
    genus: str
    species: str
    era: str
    period: str
    habitat: str
    body_type: str
    diet: str
    posture: str
    length_m: float
    height_m: float
    weight_kg: float
    skin_pattern: str
    feathers: str
    special_ability: str
    egg_type: str
    attack: int
    defense: int
    speed: int
    intelligence: int
    rarity: str
    personality: str = ""
    art: str = ""

    @property
    def full_name(self) -> str:
        """Return the binomial name of the dinosaur."""
        return f"{self.genus} {self.species}"

    @property
    def stat_total(self) -> int:
        """Return the sum of all combat stats."""
        return self.attack + self.defense + self.speed + self.intelligence

    def to_dict(self) -> dict:
        """Convert dinosaur to a JSON-serializable dictionary."""
        d = {}
        d["full_name"] = self.full_name
        d["stat_total"] = self.stat_total
        d.update(asdict(self))
        return d

    def to_json(self) -> str:
        """Serialize dinosaur to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=2)


def generate_dinosaur(seed=None, body_type=None) -> Dinosaur:
    """Generate a random dinosaur with procedurally determined attributes.

    Args:
        seed: Optional random seed for reproducible generation.
        body_type: Optional specific body type to generate. If provided,
                   the dinosaur will be of this type rather than random.

    Returns:
        A fully populated Dinosaur instance.
    """
    if seed is not None:
        random.seed(seed)

    era_name, (era_start, era_end) = random.choice(ERAS)
    period = random.choice(PERIODS_BY_ERA[era_name])

    habitat = random.choice(HABITATS)

    # Use specified body_type if provided, otherwise random
    if body_type is not None:
        if body_type not in BODY_TYPES:
            raise ValueError(f"Unknown body type: {body_type!r}. "
                             f"Valid types: {list(BODY_TYPES.keys())}")
        chosen_type = body_type
    else:
        chosen_type = random.choice(list(BODY_TYPES.keys()))

    bt_data = BODY_TYPES[chosen_type]

    genus, species = generate_name(habitat)

    min_s, max_s = bt_data["size_range"]
    mu = math.log(math.sqrt(min_s * max_s))
    sigma = 0.4
    length_m = max(min_s, min(max_s, random.lognormvariate(mu, sigma)))
    length_m = round(length_m, 1)

    if bt_data["posture"] == "bipedal":
        height_m = round(length_m * random.uniform(0.4, 0.7), 1)
    else:
        height_m = round(length_m * random.uniform(0.3, 0.5), 1)

    min_w, max_w = bt_data["weight_range"]
    weight_ratio = (length_m - min_s) / max(max_s - min_s, 0.1)
    weight_kg = min_w + (max_w - min_w) * (weight_ratio ** 2.5)
    weight_kg = round(max(min_w, min(max_w, weight_kg * random.uniform(0.8, 1.2))), 0)

    if chosen_type == "pterosaur":
        diet = random.choice(["carnivore", "piscivore"])
    elif chosen_type == "therizinosaur":
        diet = "herbivore"
    elif chosen_type == "theropod":
        diet = random.choice(["carnivore", "carnivore", "omnivore"])
    elif chosen_type == "ornithopod":
        diet = random.choice(["herbivore", "herbivore", "omnivore"])
    else:
        diet = bt_data["diet"]

    skin_pattern = random.choice(SKIN_PATTERNS)

    if chosen_type in ("theropod", "therizinosaur", "ornithopod"):
        feathers = random.choice(FEATHER_TYPES)
    elif chosen_type == "pterosaur":
        feathers = random.choice(["pycnofibers (hair-like filaments)", "dense pycnofiber coat"])
    else:
        feathers = random.choice(FEATHER_TYPES[:2])

    ability = random.choice(SPECIAL_ABILITIES.get(chosen_type, ["Tenacious survival instinct"]))
    egg = random.choice(EGG_TYPES)
    personality = random.choice(PERSONALITY_TRAITS)

    # Stats based on body type
    stat_ranges = {
        "theropod":       {"attack": (60, 98), "defense": (20, 60), "speed": (50, 95), "intelligence": (40, 85)},
        "sauropod":       {"attack": (30, 55), "defense": (70, 98), "speed": (10, 35), "intelligence": (20, 50)},
        "ceratopsian":   {"attack": (50, 85), "defense": (65, 95), "speed": (25, 55), "intelligence": (25, 55)},
        "ankylosaur":    {"attack": (40, 65), "defense": (80, 99), "speed": (10, 30), "intelligence": (15, 40)},
        "stegosaur":     {"attack": (35, 55), "defense": (55, 80), "speed": (15, 35), "intelligence": (10, 35)},
        "ornithopod":    {"attack": (20, 45), "defense": (25, 55), "speed": (55, 90), "intelligence": (40, 70)},
        "pterosaur":     {"attack": (30, 60), "defense": (10, 30), "speed": (75, 99), "intelligence": (35, 65)},
        "therizinosaur": {"attack": (55, 80), "defense": (40, 65), "speed": (20, 50), "intelligence": (45, 75)},
    }

    sr = stat_ranges.get(chosen_type, {"attack": (30, 70), "defense": (30, 70), "speed": (30, 70), "intelligence": (30, 70)})
    attack = random.randint(*sr["attack"])
    defense = random.randint(*sr["defense"])
    speed = random.randint(*sr["speed"])
    intelligence = random.randint(*sr["intelligence"])

    stat_total = attack + defense + speed + intelligence
    if stat_total >= 300:
        rarity = "legendary"
    elif stat_total >= 260:
        rarity = "rare"
    elif stat_total >= 200:
        rarity = "uncommon"
    else:
        rarity = "common"

    art_options = BODY_ART_MAP.get(chosen_type, [ART_THEROPOD_LARGE])
    art = random.choice(art_options)

    return Dinosaur(
        genus=genus, species=species, era=era_name, period=period,
        habitat=habitat, body_type=chosen_type, diet=diet, posture=bt_data["posture"],
        length_m=length_m, height_m=height_m, weight_kg=weight_kg,
        skin_pattern=skin_pattern, feathers=feathers,
        special_ability=ability, egg_type=egg,
        attack=attack, defense=defense, speed=speed, intelligence=intelligence,
        rarity=rarity, personality=personality, art=art,
    )


# === Card Rendering ===========================================================

RARITY_COLORS = {
    "common":    ("\033[37m", "\033[0m"),
    "uncommon":  ("\033[32m", "\033[0m"),
    "rare":      ("\033[34m", "\033[0m"),
    "legendary": ("\033[33m", "\033[0m"),
}

RARITY_STARS = {
    "common":    "*---",
    "uncommon":  "**--",
    "rare":      "***-",
    "legendary": "****",
}

DIET_ICONS = {
    "carnivore": "[MEAT]",
    "herbivore": "[LEAF]",
    "omnivore": "[OMNI]",
    "piscivore": "[FISH]",
    "insectivore": "[BUGS]",
}

HABITAT_ICONS = {
    "forest": "TREES", "desert": "SANDS", "swamp": "MARSH",
    "mountain": "PEAKS", "plains": "PLAINS", "coastal": "SHORE",
    "arctic": "ICE", "volcanic": "LAVA", "river": "RIVER", "cave": "CAVES",
}


def stat_bar(value: int, max_val: int = 100, width: int = 20) -> str:
    """Render a visual stat bar.

    Args:
        value: The stat value (0-100).
        max_val: The maximum value for the bar scale.
        width: The width in characters of the bar.

    Returns:
        A formatted string like '[########............]  42'
    """
    filled = int(round(value / max_val * width))
    empty = width - filled
    return f"[{'#' * filled}{'.' * empty}] {value:>3d}"


def render_card(dino: Dinosaur, use_color: bool = True) -> str:
    """Render a dinosaur's trading card as a formatted string.

    Args:
        dino: The Dinosaur instance to render.
        use_color: Whether to include ANSI color codes.

    Returns:
        A multi-line string containing the formatted card.
    """
    c_open, c_close = RARITY_COLORS.get(dino.rarity, ("", "")) if use_color else ("", "")
    stars = RARITY_STARS[dino.rarity]
    rarity_label = dino.rarity.upper()

    name_display = f"{dino.genus} {dino.species}"
    W = 58

    lines = []
    lines.append("+" + "=" * (W - 2) + "+")
    name_line = f" {c_open}{name_display}{c_close}"
    rarity_str = f"{c_open}{stars} {rarity_label}{c_close}"
    plain_name_len = len(name_display)
    plain_rarity_len = len(stars) + 1 + len(rarity_label)
    pad = W - 2 - plain_name_len - plain_rarity_len - 2
    lines.append(f"|{name_line}{' ' * max(1, pad)}{rarity_str} |")
    lines.append("+" + "-" * (W - 2) + "+")

    # Classification row
    diet_label = DIET_ICONS.get(dino.diet, dino.diet.upper())
    habitat_label = HABITAT_ICONS.get(dino.habitat, dino.habitat.upper())
    row2 = f" {dino.body_type.upper():<14s} | {diet_label} {dino.diet:<10s} | {dino.posture}"
    lines.append(f"|{row2}{' ' * max(0, W - 2 - len(row2))}|")

    # Era row
    row3 = f" {dino.period:<24s} | {habitat_label}: {dino.habitat}"
    lines.append(f"|{row3}{' ' * max(0, W - 2 - len(row3))}|")

    lines.append("+" + "-" * (W - 2) + "+")

    # Stats
    lines.append(f"|  ATK: {stat_bar(dino.attack, width=18)}       |")
    lines.append(f"|  DEF: {stat_bar(dino.defense, width=18)}       |")
    lines.append(f"|  SPD: {stat_bar(dino.speed, width=18)}       |")
    lines.append(f"|  INT: {stat_bar(dino.intelligence, width=18)}       |")

    lines.append("+" + "-" * (W - 2) + "+")

    # Physical
    phys = f"  L:{dino.length_m}m  H:{dino.height_m}m  W:{dino.weight_kg:,.0f}kg"
    lines.append(f"|{phys}{' ' * max(0, W - 2 - len(phys))}|")

    lines.append("+" + "-" * (W - 2) + "+")

    # Appearance
    skin_line = f"  Skin: {dino.skin_pattern}"
    lines.append(f"|{skin_line}{' ' * max(0, W - 2 - len(skin_line))}|")

    feather_line = f"  Feathers: {dino.feathers}"
    lines.append(f"|{feather_line}{' ' * max(0, W - 2 - len(feather_line))}|")

    # Personality trait (new field)
    pers_line = f"  Temper: {dino.personality}"
    lines.append(f"|{pers_line}{' ' * max(0, W - 2 - len(pers_line))}|")

    lines.append("+" + "-" * (W - 2) + "+")

    # Special ability
    ability_line = f"  >> {dino.special_ability}"
    lines.append(f"| {c_open}{ability_line}{c_close}{' ' * max(0, W - 2 - len(ability_line))}|")

    # Eggs
    egg_line = f"  Egg: {dino.egg_type}"
    lines.append(f"|{egg_line}{' ' * max(0, W - 2 - len(egg_line))}|")

    lines.append("+" + "=" * (W - 2) + "+")

    return "\n".join(lines)


def render_art(dino: Dinosaur) -> str:
    """Return the ASCII art for a dinosaur."""
    return dino.art


def render_full(dino: Dinosaur, use_color: bool = True) -> str:
    """Render the full display: ASCII art + trading card.

    Args:
        dino: The Dinosaur instance to render.
        use_color: Whether to include ANSI color codes.

    Returns:
        A multi-line string with art and card.
    """
    art = render_art(dino)
    card = render_card(dino, use_color=use_color)
    return f"{art}\n\n{card}"


# === Collection Tracker =======================================================

class DinoDex:
    """Tracks a collection of generated dinosaurs with summary statistics."""

    def __init__(self):
        self.collection: List[Dinosaur] = []

    def add(self, dino: Dinosaur):
        """Add a dinosaur to the collection."""
        self.collection.append(dino)

    def summary(self, use_color: bool = True) -> str:
        """Generate a summary of the collection grouped by rarity, type, and diet."""
        if not self.collection:
            return "Your DinoDex is empty! Generate some dinosaurs."

        total = len(self.collection)
        by_rarity = {}
        by_type = {}
        by_diet = {}
        for d in self.collection:
            by_rarity[d.rarity] = by_rarity.get(d.rarity, 0) + 1
            by_type[d.body_type] = by_type.get(d.body_type, 0) + 1
            by_diet[d.diet] = by_diet.get(d.diet, 0) + 1

        lines = [
            "",
            "  DINODEX COLLECTION SUMMARY",
            "  " + "=" * 38,
            f"  Total dinosaurs: {total}",
            "",
            "  By Rarity:",
        ]
        for r in ["common", "uncommon", "rare", "legendary"]:
            if r in by_rarity:
                stars = RARITY_STARS[r]
                lines.append(f"    {stars} {r.capitalize():12s} {by_rarity[r]}")

        lines.append("")
        lines.append("  By Body Type:")
        for bt, count in sorted(by_type.items(), key=lambda x: -x[1]):
            lines.append(f"    {bt.capitalize():16s} {count}")

        lines.append("")
        lines.append("  By Diet:")
        for diet, count in sorted(by_diet.items(), key=lambda x: -x[1]):
            icon = DIET_ICONS.get(diet, "")
            lines.append(f"    {icon} {diet.capitalize():14s} {count}")

        return "\n".join(lines)

    def wall_of_fame(self, use_color: bool = True) -> str:
        """Show the top 10 dinosaurs by total stat points."""
        if not self.collection:
            return "No dinosaurs in collection yet."

        by_stat = sorted(self.collection, key=lambda d: d.stat_total, reverse=True)
        lines = [
            "",
            "  WALL OF FAME -- Top Dinosaurs",
            "  " + "=" * 50,
        ]
        for i, d in enumerate(by_stat[:10]):
            c_open, c_close = RARITY_COLORS.get(d.rarity, ("", ""))
            lines.append(
                f"  {i+1:2d}. {c_open}{d.genus} {d.species}{c_close} "
                f"[{d.body_type}] Total: {d.stat_total} "
                f"(ATK:{d.attack} DEF:{d.defense} SPD:{d.speed} INT:{d.intelligence})"
            )
        return "\n".join(lines)


# === Battle System ============================================================

def battle(dino1: Dinosaur, dino2: Dinosaur) -> str:
    """Simulate a battle between two dinosaurs.

    Uses weighted stat calculation (ATK×0.35 + DEF×0.25 + SPD×0.25 + INT×0.15)
    with ±15% randomness for exciting upsets.

    Args:
        dino1: First combatant.
        dino2: Second combatant.

    Returns:
        A multi-line string describing the battle and outcome.
    """
    score1 = dino1.attack * 0.35 + dino1.defense * 0.25 + dino1.speed * 0.25 + dino1.intelligence * 0.15
    score2 = dino2.attack * 0.35 + dino2.defense * 0.25 + dino2.speed * 0.25 + dino2.intelligence * 0.15
    score1 *= random.uniform(0.85, 1.15)
    score2 *= random.uniform(0.85, 1.15)

    lines = [
        "",
        "  BATTLE: {} {} vs {} {}".format(dino1.genus, dino1.species, dino2.genus, dino2.species),
        "  " + "-" * 56,
        "  {}: ATK={} DEF={} SPD={} INT={}".format(
            dino1.genus + " " + dino1.species, dino1.attack, dino1.defense, dino1.speed, dino1.intelligence),
        "  {}: ATK={} DEF={} SPD={} INT={}".format(
            dino2.genus + " " + dino2.species, dino2.attack, dino2.defense, dino2.speed, dino2.intelligence),
        "",
    ]

    lines.append("  {} uses {}!".format(dino1.genus, dino1.special_ability.lower()))
    lines.append("  {} uses {}!".format(dino2.genus, dino2.special_ability.lower()))
    lines.append("")

    if score1 > score2:
        margin = (score1 - score2) / max(score2, 1) * 100
        lines.append("  >> {} {} WINS! (margin: {:.1f}%)".format(dino1.genus, dino1.species, margin))
    elif score2 > score1:
        margin = (score2 - score1) / max(score1, 1) * 100
        lines.append("  >> {} {} WINS! (margin: {:.1f}%)".format(dino2.genus, dino2.species, margin))
    else:
        lines.append("  >> It's a DRAW! Both dinosaurs retreat.")

    return "\n".join(lines)


def compare(dino1: Dinosaur, dino2: Dinosaur) -> str:
    """Compare two dinosaurs side by side.

    Args:
        dino1: First dinosaur.
        dino2: Second dinosaur.

    Returns:
        A formatted comparison string.
    """
    def advantage(val1, val2):
        if val1 > val2:
            return " <<<"
        elif val2 > val1:
            return ">>>"
        return ""

    lines = [
        "",
        "  COMPARISON",
        "  " + "=" * 60,
        f"  {'Attribute':<14s} | {'Dino 1':>30s} | {'Dino 2':>30s}",
        "  " + "-" * 60,
        f"  {'Name':<14s} | {dino1.full_name:>30s} | {dino2.full_name:>30s}",
        f"  {'Body Type':<14s} | {dino1.body_type:>30s} | {dino2.body_type:>30s}",
        f"  {'Rarity':<14s} | {dino1.rarity.upper():>30s} | {dino2.rarity.upper():>30s}",
        f"  {'Era':<14s} | {dino1.period:>30s} | {dino2.period:>30s}",
        f"  {'Habitat':<14s} | {dino1.habitat:>30s} | {dino2.habitat:>30s}",
        f"  {'Diet':<14s} | {dino1.diet:>30s} | {dino2.diet:>30s}",
        f"  {'Length':<14s} | {str(dino1.length_m) + 'm':>30s} | {str(dino2.length_m) + 'm':>30s}",
        f"  {'Weight':<14s} | {str(dino1.weight_kg) + 'kg':>30s} | {str(dino2.weight_kg) + 'kg':>30s}",
        "  " + "-" * 60,
        f"  {'ATK':<14s} | {dino1.attack:>27d}{advantage(dino1.attack, dino2.attack):4s} | {dino2.attack:>27d}{advantage(dino2.attack, dino1.attack):4s}",
        f"  {'DEF':<14s} | {dino1.defense:>27d}{advantage(dino1.defense, dino2.defense):4s} | {dino2.defense:>27d}{advantage(dino2.defense, dino1.defense):4s}",
        f"  {'SPD':<14s} | {dino1.speed:>27d}{advantage(dino1.speed, dino2.speed):4s} | {dino2.speed:>27d}{advantage(dino2.speed, dino1.speed):4s}",
        f"  {'INT':<14s} | {dino1.intelligence:>27d}{advantage(dino1.intelligence, dino2.intelligence):4s} | {dino2.intelligence:>27d}{advantage(dino2.intelligence, dino1.intelligence):4s}",
        "  " + "-" * 60,
        f"  {'TOTAL':<14s} | {dino1.stat_total:>27d}{advantage(dino1.stat_total, dino2.stat_total):4s} | {dino2.stat_total:>27d}{advantage(dino2.stat_total, dino1.stat_total):4s}",
        "  " + "=" * 60,
    ]
    return "\n".join(lines)


# === Tournament System ========================================================

def tournament(dinosaurs: List[Dinosaur], use_color: bool = True) -> Dinosaur:
    """Run a single-elimination tournament among dinosaurs.

    Dinosaurs are paired up, battles are fought, and winners advance
    to the next round. If the number is not a power of 2, some
    dinosaurs get byes in the first round.

    Args:
        dinosaurs: List of Dinosaur instances to compete.
        use_color: Whether to use ANSI colors in output.

    Returns:
        The champion Dinosaur.
    """
    if len(dinosaurs) < 2:
        raise ValueError("Need at least 2 dinosaurs for a tournament.")

    contestants = list(dinosaurs)
    round_num = 1

    print(f"\n  TOURNAMENT: {len(contestants)} dinosaurs enter!")
    print("  " + "=" * 50)

    while len(contestants) > 1:
        # Pad to power of 2 with byes
        next_power = 1
        while next_power < len(contestants):
            next_power *= 2

        winners = []
        i = 0
        while i < len(contestants):
            if i + 1 >= len(contestants):
                # Bye: this dinosaur advances automatically
                print(f"\n  Round {round_num}: {contestants[i].full_name} gets a bye")
                winners.append(contestants[i])
                break

            d1 = contestants[i]
            d2 = contestants[i + 1]

            # Battle
            score1 = d1.attack * 0.35 + d1.defense * 0.25 + d1.speed * 0.25 + d1.intelligence * 0.15
            score2 = d2.attack * 0.35 + d2.defense * 0.25 + d2.speed * 0.25 + d2.intelligence * 0.15
            score1 *= random.uniform(0.85, 1.15)
            score2 *= random.uniform(0.85, 1.15)

            if score1 > score2:
                winner, loser = d1, d2
                margin = (score1 - score2) / max(score2, 1) * 100
            elif score2 > score1:
                winner, loser = d2, d1
                margin = (score2 - score1) / max(score1, 1) * 100
            else:
                # Draw: pick random winner
                winner = random.choice([d1, d2])
                loser = d2 if winner is d1 else d1
                margin = 0.0

            result = "DRAW (random)" if margin == 0.0 else f"{margin:.1f}%"
            print(f"\n  Round {round_num}: {d1.full_name} vs {d2.full_name}")
            print(f"    >> {winner.full_name} advances! ({result})")

            winners.append(winner)
            i += 2

        contestants = winners
        round_num += 1

    champion = contestants[0]
    print(f"\n  {'*' * 50}")
    print(f"  CHAMPION: {champion.full_name} [{champion.body_type}] ({champion.rarity.upper()})")
    print(f"  Stats: ATK={champion.attack} DEF={champion.defense} SPD={champion.speed} INT={champion.intelligence}")
    print(f"  {'*' * 50}\n")

    return champion


# === Interactive Mode =========================================================

def interactive():
    """Run the interactive REPL for generating and managing dinosaurs."""
    print("")
    print("  +==========================================================+")
    print("  |          PROCEDURAL DINOSAUR GENERATOR  v{}           |".format(__version__))
    print("  |                                                          |")
    print("  |   Generate random dinosaurs with stats, ASCII art,      |")
    print("  |   and collectible trading cards!                          |")
    print("  +==========================================================+")
    print("")

    dex = DinoDex()

    while True:
        print("")
        print("Commands:")
        print("  [g] Generate a random dinosaur")
        print("  [b] Battle two dinosaurs from your collection")
        print("  [c] Compare two dinosaurs side-by-side")
        print("  [t] Tournament (all dinosaurs compete)")
        print("  [l] List your collection")
        print("  [w] Wall of Fame (top stats)")
        print("  [s] Generate with specific seed")
        print("  [j] Export last dinosaur as JSON")
        print("  [q] Quit")
        print("")

        try:
            cmd = input(">>> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("")
            break

        if cmd in ("q", "quit", "exit"):
            print("")
            print("  Thanks for using the Dinosaur Generator!")
            break

        elif cmd in ("g", "generate", ""):
            dino = generate_dinosaur()
            dex.add(dino)
            print("")
            print("=" * 60)
            print("  NEW DINOSAUR DISCOVERED!")
            print("=" * 60)
            print(render_full(dino))
            print("")
            print("  Collection size: {}".format(len(dex.collection)))

        elif cmd in ("b", "battle"):
            if len(dex.collection) < 2:
                print("")
                print("  You need at least 2 dinosaurs to battle! Generate more first.")
                continue

            print("")
            print("  Your collection:")
            for i, d in enumerate(dex.collection):
                print("    {:3d}. {} {} [{}] (Total: {})".format(
                    i + 1, d.genus, d.species, d.body_type, d.stat_total))

            try:
                idx1 = int(input("\n  Select first dinosaur (#): ")) - 1
                idx2 = int(input("  Select second dinosaur (#): ")) - 1
                if 0 <= idx1 < len(dex.collection) and 0 <= idx2 < len(dex.collection):
                    print(battle(dex.collection[idx1], dex.collection[idx2]))
                else:
                    print("  Invalid selection.")
            except (ValueError, EOFError):
                print("  Invalid input.")

        elif cmd in ("c", "compare"):
            if len(dex.collection) < 2:
                print("")
                print("  You need at least 2 dinosaurs to compare! Generate more first.")
                continue

            print("")
            print("  Your collection:")
            for i, d in enumerate(dex.collection):
                print("    {:3d}. {} {} [{}] (Total: {})".format(
                    i + 1, d.genus, d.species, d.body_type, d.stat_total))

            try:
                idx1 = int(input("\n  Select first dinosaur (#): ")) - 1
                idx2 = int(input("  Select second dinosaur (#): ")) - 1
                if 0 <= idx1 < len(dex.collection) and 0 <= idx2 < len(dex.collection):
                    print(compare(dex.collection[idx1], dex.collection[idx2]))
                else:
                    print("  Invalid selection.")
            except (ValueError, EOFError):
                print("  Invalid input.")

        elif cmd in ("t", "tournament"):
            if len(dex.collection) < 2:
                print("")
                print("  You need at least 2 dinosaurs for a tournament! Generate more first.")
                continue

            champion = tournament(dex.collection)
            print(render_card(champion))

        elif cmd in ("l", "list"):
            print(dex.summary())

        elif cmd in ("w", "wall", "fame"):
            print(dex.wall_of_fame())

        elif cmd in ("s", "seed"):
            try:
                seed = int(input("  Enter seed number: "))
                dino = generate_dinosaur(seed=seed)
                dex.add(dino)
                print("")
                print("=" * 60)
                print("  SEEDED DINOSAUR (seed={})".format(seed))
                print("=" * 60)
                print(render_full(dino))
            except (ValueError, EOFError):
                print("  Invalid seed.")

        elif cmd in ("j", "json"):
            if not dex.collection:
                print("")
                print("  No dinosaurs in collection yet! Generate one first.")
                continue
            print("")
            print(dex.collection[-1].to_json())

        else:
            print("  Unknown command: {}".format(cmd))


# === CLI Entry Point ==========================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Procedural Dinosaur Generator - generate random dinosaurs with stats, ASCII art, and trading cards!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dinosaur_generator.py                    # Interactive mode
  python dinosaur_generator.py --generate         # Generate one dinosaur
  python dinosaur_generator.py --generate 5       # Generate 5 dinosaurs
  python dinosaur_generator.py --seed 42          # Generate with seed 42
  python dinosaur_generator.py --battle           # Battle random dinosaurs
  python dinosaur_generator.py --type theropod   # Generate specific type
  python dinosaur_generator.py --tournament 8     # 8-dino tournament
  python dinosaur_generator.py --json             # Output as JSON
  python dinosaur_generator.py --compare           # Compare two random dinos
  python dinosaur_generator.py --no-color          # No ANSI colors
        """,
    )

    parser.add_argument("--version", "-v", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--generate", "-g", nargs="?", const=1, type=int, default=None,
                        help="Generate N dinosaurs (default: 1)")
    parser.add_argument("--seed", "-s", type=int, default=None,
                        help="Random seed for reproducible generation")
    parser.add_argument("--battle", "-b", action="store_true",
                        help="Battle two random dinosaurs")
    parser.add_argument("--compare", action="store_true",
                        help="Compare two random dinosaurs side-by-side")
    parser.add_argument("--tournament", "-t", nargs="?", const=8, type=int, default=None,
                        help="Run an N-dinosaur tournament (default: 8)")
    parser.add_argument("--type", choices=list(BODY_TYPES.keys()),
                        help="Generate a specific body type")
    parser.add_argument("--json", action="store_true",
                        help="Output dinosaur(s) as JSON instead of cards")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI color codes")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Run in interactive mode")

    args = parser.parse_args()

    use_color = not args.no_color

    if args.seed is not None:
        random.seed(args.seed)

    # If no specific command, go interactive
    if (args.generate is None and not args.battle and not args.compare
            and args.tournament is None and not args.interactive):
        interactive()
        return

    if args.interactive:
        interactive()
        return

    if args.generate is not None:
        n = args.generate
        dinos = []
        for i in range(n):
            dino = generate_dinosaur(body_type=args.type)
            dinos.append(dino)

        if args.json:
            if len(dinos) == 1:
                print(dinos[0].to_json())
            else:
                print(json.dumps([d.to_dict() for d in dinos], indent=2))
        else:
            for i, dino in enumerate(dinos):
                if n > 1:
                    print("")
                    print("--- Dinosaur {}/{} ---".format(i + 1, n))
                print(render_full(dino, use_color=use_color))
        return

    if args.battle:
        dino1 = generate_dinosaur()
        dino2 = generate_dinosaur()
        print("")
        print("  Combatants:")
        print("  1. {} {} ({}, {})".format(dino1.genus, dino1.species, dino1.body_type, dino1.rarity))
        print("  2. {} {} ({}, {})".format(dino2.genus, dino2.species, dino2.body_type, dino2.rarity))
        print(render_art(dino1))
        print("")
        print("VS")
        print("")
        print(render_art(dino2))
        print(battle(dino1, dino2))
        return

    if args.compare:
        dino1 = generate_dinosaur()
        dino2 = generate_dinosaur()
        print(render_art(dino1))
        print("")
        print(render_art(dino2))
        print(compare(dino1, dino2))
        return

    if args.tournament is not None:
        n = args.tournament
        if n < 2:
            print("Error: Need at least 2 dinosaurs for a tournament.", file=sys.stderr)
            sys.exit(1)
        dinos = [generate_dinosaur() for _ in range(n)]
        champion = tournament(dinos, use_color=use_color)
        if args.json:
            print(champion.to_json())
        return


if __name__ == "__main__":
    main()