#!/usr/bin/env python3
"""
Procedural Constellation Map Generator
=======================================
Generates a rich, navigable ASCII star map with procedurally created
constellations, mythical names, lore, and celestial objects.

Features:
  - 6 distinct constellation shapes (chain, triangle, cross, arc, cluster, spiral)
  - Greek letter star designations
  - Colored ASCII nebulae
  - Deep sky objects (galaxies, pulsars, quasars, black holes, clusters)
  - Procedural meteor showers
  - Rich lore engine with template-based mythology
  - Coordinate grid overlay
  - Interactive navigation mode
  - Constellation search
  - Map statistics
  - JSON export
  - Reproducible maps via --seed
  - ANSI color support
"""

import random
import math
import argparse
import sys
import json
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from collections import defaultdict

__version__ = "1.1.0"

# ─── Data Sources ──────────────────────────────────────────────────────────────

GREEK_LETTERS = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta",
    "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi",
    "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega"
]

GREEK_SYMS = [
    "α", "β", "γ", "δ", "ε", "ζ", "η", "θ", "ι", "κ", "λ", "μ",
    "ν", "ξ", "ο", "π", "ρ", "σ", "τ", "υ", "φ", "χ", "ψ", "ω"
]

CONSTELLATION_PREFIXES = [
    "Aeth", "Bel", "Cor", "Dra", "Eld", "Fen", "Gal", "Har", "Ith", "Jor",
    "Kal", "Lyr", "Mor", "Nyx", "Oru", "Pha", "Que", "Rho", "Sel", "Thr",
    "Uld", "Vex", "Wy", "Xan", "Yso", "Zep", "Aur", "Bor", "Cel", "Dum",
    "Eri", "Flu", "Gor", "Hes", "Ian", "Jun", "Kry", "Lum", "Myr", "Nar",
    "Osa", "Pyr", "Qui", "Rav", "Som", "Tel", "Umi", "Vel", "Wyn", "Zar"
]

CONSTELLATION_SUFFIXES = [
    "ara", "ius", "ion", "ath", "eon", "iel", "oth", "ura", "yx", "is",
    "ax", "os", "ia", "on", "um", "us", "a", "en", "or", "ix",
    "iel", "oth", "yne", "ath", "ora"
]

CONSTELLATION_TYPES = [
    "The Guardian", "The Wanderer", "The Phoenix", "The Serpent", "The Crown",
    "The Scepter", "The Shield", "The Dragon", "The Oracle",
    "The Sentinel", "The Harbinger", "The Flame", "The Frost",
    "The Tempest", "The Void", "The Gate", "The Key", "The Spiral",
    "The Bridge", "The Forge", "The Loom", "The Well", "The Beacon",
    "The Compass", "The Anchor", "The Prism", "The Chalice", "The Mantle",
    "The Eye", "The Wing", "The Claw", "The Horn", "The Shard",
    "The Ember", "The Tide", "The Gale", "The Stone", "The Root",
]

LORE_TEMPLATES = [
    "Ancient mariners used {name} to navigate the {sea} Sea, believing its {part} pointed toward the mythical shores of {realm}.",
    "The {people} tell of {name} — a {creature} that {action} across the heavens each {season}, leaving a trail of {trail}.",
    "In the age of {age}, {name} was said to be the {role} of the {deity}, placed among the stars as a {reason}.",
    "Scholars of the {school} believe {name} marks the {event} — when the {thing} first {past_verb} from the {origin}.",
    "{name} is brightest during {season}, when legend says the {creature} {action} once more and the {object} {appears}.",
    "The oracle of {place} once prophesied that when {name} aligns with {other}, the {gate} shall {open_verb} and {consequence}.",
    "Nomadic tribes of the {region} call {name} the '{title}' and refuse to look upon it during {time}, fearing {fear}.",
    "According to the {book}, {name} was forged by {smith} from {material}, and its stars still burn with {property}.",
]

LORE_FILLINGS = {
    "sea": ["Whispering", "Eternal", "Crystal", "Shadowed", "Starlit", "Silver", "Abyssal"],
    "part": ["brightest star", "northern edge", "central triangle", "lowest point", "curving arm"],
    "realm": ["Aethon", "Elysara", "Mythralis", "Celestia", "The Forgotten Isle", "Valthor"],
    "people": ["Arathi", "Silvani", "Keldori", "Nyssians", "Thalassans", "Duskweavers"],
    "creature": ["phoenix", "wyrm", "titan", "spirit", "elemental", "serpent", "griffin"],
    "action": ["soars", "crawls", "dances", "races", "wakes", "emerges", "spirals"],
    "season": ["autumn equinox", "winter solstice", "spring dawn", "summer zenith", "harvest moon"],
    "trail": ["stardust", "cosmic fire", "frozen light", "ethereal mist", "silver threads"],
    "age": ["the First Age", "Starfall", "the Sundering", "the Convergence", "the Twilight Epoch"],
    "role": ["crown", "shield", "eye", "heart", "beacon", "compass", "key"],
    "deity": ["Aethon the Eternal", "Nyx the Unseen", "Solaris the Radiant", "Thalor the Deep"],
    "reason": ["warning to mortals", "beacon for the lost", "test of worthiness", "pact with the stars"],
    "school": ["Obsidian Tower", "Starlight Academy", "Arcane College", "Celestium"],
    "event": ["First Awakening", "Great Convergence", "Shattering", "Breaking of Bonds"],
    "thing": ["void serpent", "star fire", "cosmic seed", "primal essence"],
    "past_verb": ["erupted", "descended", "shattered", "awoke", "converged"],
    "origin": ["void between worlds", "heart of creation", "depths of time", "edge of reality"],
    "other": ["the Pillar of Dawn", "the Eye of Night", "the Silver Gate", "the Hollow Crown"],
    "gate": ["Gate of Echoes", "Door of Whispers", "Portal of Stars", "Veil of Becoming"],
    "open_verb": ["shatter", "dissolve", "ignite", "awaken", "unfold"],
    "consequence": ["time itself shall rewind", "the stars will remember their names", "lost souls shall return home"],
    "place": ["Aethermoor", "Starhollow", "Duskfall", "Celestia's Rest", "Thornspire"],
    "title": ["Omen of Endings", "Weeper of Stars", "Silent Watcher", "Herald of Change"],
    "time": ["the new moon", "the hour of wolves", "eclipse season", "the darkest night"],
    "fear": ["it might blink out of existence", "its gaze will find them", "the stars may fall"],
    "book": ["Chronicles of Aether", "Starbound Codex", "Tome of Celestial Lore", "Grimoire of Night"],
    "smith": ["the star-keeper Aethon", "the celestial forge-maiden", "the cosmic architect Nyxar"],
    "material": ["shards of dead stars", "the first light of creation", "crystallized time"],
    "property": ["the memory of their making", "an undying radiance", "the echo of forgotten songs"],
    # Additional fillings for expanded lore templates
    "object": ["celestial harp", "star-forged blade", "crystal scepter", "ancient compass"],
    "appears": ["shines with renewed brilliance", "emerges from shadow", "sings across the void"],
    "region": ["Northern Reaches", "Amber Wastes", "Silver Coast", "Twilight Marches"],
}

NEBULA_NAMES = [
    "Veil of Shadows", "Crimson Drift", "Emerald Mists", "Ghost Nebula",
    "Sapphire Haze", "The Wound", "Silver Tendrils", "Void Heart",
    "Ashen Cloud", "The Breach", "Amber Expanse", "Twilight Veil"
]

CELESTIAL_OBJECTS = [
    ("galaxy", "spiral"), ("galaxy", "elliptical"), ("galaxy", "irregular"),
    ("nebula", "emission"), ("nebula", "planetary"), ("nebula", "reflection"),
    ("cluster", "globular"), ("cluster", "open"),
    ("pulsar", None), ("quasar", None), ("black hole", None),
]

METEOR_SHOWER_NAMES = [
    "Perseid", "Leonid", "Geminid", "Orionid", "Lyrid",
    "Eta Aquariid", "Draconid", "Taurid", "Quadrantid", "Delta Aquariid",
    "Aethonid", "Nyxariid", "Starfall", "Celestiid",
]

BRIGHT_STARS = "✦✧⋆✶★☆*·°•∘"

# Deterministic brightness characters based on magnitude (no random.choice)
# This ensures reproducibility across runs with the same seed
_BRIGHTNESS_TABLE = {
    # mag < 1.0: very bright
    0: "★",
    # mag 1.0-2.0: bright
    1: "✦",
    2: "✧",
    # mag 2.0-3.0: medium
    3: "⋆",
    # mag 3.0-4.5: dim
    4: "·",
    # mag >= 4.5: very dim
    5: "∘",
}


# ─── Star ──────────────────────────────────────────────────────────────────────

@dataclass
class Star:
    x: float
    y: float
    magnitude: float  # 0 = brightest, 6 = dimmest
    name: Optional[str] = None
    greek_letter: Optional[str] = None
    constellation_id: Optional[int] = None

    @property
    def brightness_char(self) -> str:
        """Return a deterministic display character based on magnitude."""
        if self.magnitude < 1.0:
            return _BRIGHTNESS_TABLE[0]
        elif self.magnitude < 2.0:
            # Use a secondary bright symbol for variety based on magnitude precision
            sub = int((self.magnitude - 1.0) * 10) % 2
            return _BRIGHTNESS_TABLE[1 + sub]
        elif self.magnitude < 3.0:
            return _BRIGHTNESS_TABLE[3]
        elif self.magnitude < 4.5:
            return _BRIGHTNESS_TABLE[4]
        else:
            return _BRIGHTNESS_TABLE[5]

    @property
    def display_char(self) -> str:
        return self.brightness_char


# ─── Constellation ─────────────────────────────────────────────────────────────

@dataclass
class Constellation:
    id: int
    name: str
    title: str  # e.g., "The Guardian"
    full_name: str  # e.g., "Aethara, The Guardian"
    stars: List[Star] = field(default_factory=list)
    connections: List[Tuple[int, int]] = field(default_factory=list)  # indices into self.stars
    lore: str = ""
    center: Tuple[float, float] = (0, 0)

    def assign_greek_letters(self):
        """Assign Greek letter designations to stars, brightest first."""
        sorted_stars = sorted(self.stars, key=lambda s: s.magnitude)
        for i, star in enumerate(sorted_stars):
            if i < len(GREEK_LETTERS):
                star.greek_letter = f"{GREEK_SYMS[i]} ({GREEK_LETTERS[i]})"
                star.name = f"{GREEK_SYMS[i]} {self.name}"


# ─── Celestial Object ──────────────────────────────────────────────────────────

@dataclass
class CelestialObject:
    x: float
    y: float
    obj_type: str
    sub_type: Optional[str]
    name: str
    symbol: str
    description: str


# ─── Nebula ─────────────────────────────────────────────────────────────────────

@dataclass
class Nebula:
    x: float
    y: float
    radius: float
    name: str
    density: float  # 0.0 - 1.0
    color: str  # ANSI color name


# ─── Meteor ────────────────────────────────────────────────────────────────────

@dataclass
class MeteorShower:
    """A procedurally generated meteor shower streaking across the sky."""
    name: str
    radiant_x: float
    radiant_y: float
    angle: float       # Direction of streak (radians)
    length: int         # Number of characters in the streak
    intensity: int       # Number of individual meteors
    peak_phrase: str    # Flavor text for peak activity


# ─── Star Map Generator ────────────────────────────────────────────────────────

class StarMapGenerator:
    def __init__(self, width=80, height=40, seed=None, num_constellations=12,
                 num_background_stars=200, num_nebulae=3, num_deep_objects=8,
                 num_meteor_showers=2):
        self.width = width
        self.height = height
        self.seed = seed or random.randint(0, 999999)
        self.rng = random.Random(self.seed)
        self.num_constellations = num_constellations
        self.num_background_stars = num_background_stars
        self.num_nebulae = num_nebulae
        self.num_deep_objects = num_deep_objects
        self.num_meteor_showers = num_meteor_showers

        self.constellations: List[Constellation] = []
        self.background_stars: List[Star] = []
        self.nebulae: List[Nebula] = []
        self.deep_objects: List[CelestialObject] = []
        self.meteor_showers: List[MeteorShower] = []

    def generate(self):
        """Generate the complete star map."""
        self._generate_nebulae()
        self._generate_constellations()
        self._generate_background_stars()
        self._generate_deep_objects()
        self._generate_meteor_showers()
        return self

    def _generate_name(self) -> str:
        prefix = self.rng.choice(CONSTELLATION_PREFIXES)
        suffix = self.rng.choice(CONSTELLATION_SUFFIXES)
        return prefix + suffix

    def _generate_lore(self, constellation: Constellation) -> str:
        template = self.rng.choice(LORE_TEMPLATES)
        fillings = {}
        for key, values in LORE_FILLINGS.items():
            fillings[key] = self.rng.choice(values)
        fillings["name"] = constellation.full_name
        try:
            return template.format(**fillings)
        except KeyError:
            return f"Little is known of {constellation.full_name}, save that it has shone since before memory."

    def _is_too_close(self, x, y, min_dist=8.0, existing_points=None):
        points = existing_points or []
        for px, py in points:
            if math.hypot(x - px, y - py) < min_dist:
                return True
        return False

    def _generate_nebulae(self):
        nebula_colors = ["crimson", "emerald", "sapphire", "amber", "violet", "silver", "ashen"]
        centers = []
        for _ in range(self.num_nebulae):
            for attempt in range(50):
                x = self.rng.uniform(5, self.width - 5)
                y = self.rng.uniform(5, self.height - 5)
                if not self._is_too_close(x, y, 12.0, centers):
                    break
            centers.append((x, y))
            radius = self.rng.uniform(4, 10)
            density = self.rng.uniform(0.3, 0.8)
            color = self.rng.choice(nebula_colors)
            name = self.rng.choice(NEBULA_NAMES)
            self.nebulae.append(Nebula(x, y, radius, name, density, color))

    def _generate_constellations(self):
        centers = []
        for i in range(self.num_constellations):
            name = self._generate_name()
            title = self.rng.choice(CONSTELLATION_TYPES)
            full_name = f"{name}, {title}"

            # Find a good center point
            for attempt in range(100):
                cx = self.rng.uniform(6, self.width - 6)
                cy = self.rng.uniform(4, self.height - 4)
                if not self._is_too_close(cx, cy, 10.0, centers):
                    break
            centers.append((cx, cy))

            constellation = Constellation(
                id=i,
                name=name,
                title=title,
                full_name=full_name,
                center=(cx, cy)
            )

            # Generate constellation stars
            num_stars = self.rng.randint(3, 9)
            constellation_shape = self.rng.choice(["chain", "triangle", "cross", "arc", "cluster", "spiral"])
            stars = self._generate_constellation_shape(cx, cy, num_stars, constellation_shape)
            constellation.stars = stars

            # Generate connections based on shape
            constellation.connections = self._generate_connections(len(stars), constellation_shape)

            # Assign names to bright stars
            constellation.assign_greek_letters()

            # Generate lore
            constellation.lore = self._generate_lore(constellation)

            self.constellations.append(constellation)

    def _generate_constellation_shape(self, cx, cy, num_stars, shape) -> List[Star]:
        stars = []
        spread = self.rng.uniform(1.5, 3.5)

        if shape == "chain":
            # Stars in a roughly linear chain
            angle = self.rng.uniform(0, math.pi)
            for i in range(num_stars):
                t = (i / max(1, num_stars - 1)) - 0.5
                x = cx + t * spread * 2 * math.cos(angle) + self.rng.gauss(0, 0.3)
                y = cy + t * spread * 2 * math.sin(angle) + self.rng.gauss(0, 0.3)
                mag = self.rng.uniform(0.5, 3.5)
                if i == 0 or i == num_stars - 1:
                    mag = min(mag, 2.0)
                stars.append(Star(x, y, mag))

        elif shape == "triangle":
            # Core triangle + extras
            for i in range(min(3, num_stars)):
                angle = i * 2 * math.pi / 3 + self.rng.uniform(-0.2, 0.2)
                x = cx + spread * math.cos(angle) + self.rng.gauss(0, 0.2)
                y = cy + spread * math.sin(angle) + self.rng.gauss(0, 0.2)
                mag = self.rng.uniform(0.5, 2.5)
                stars.append(Star(x, y, mag))
            for i in range(3, num_stars):
                x = cx + self.rng.uniform(-spread, spread)
                y = cy + self.rng.uniform(-spread, spread)
                mag = self.rng.uniform(1.5, 4.0)
                stars.append(Star(x, y, mag))

        elif shape == "cross":
            # Cross pattern
            for i in range(num_stars):
                if i < 2:
                    x = cx + (i - 0.5) * spread * 1.5 + self.rng.gauss(0, 0.2)
                    y = cy + self.rng.gauss(0, 0.2)
                elif i < 4:
                    x = cx + self.rng.gauss(0, 0.2)
                    y = cy + (i - 2.5) * spread * 1.0 + self.rng.gauss(0, 0.2)
                else:
                    x = cx + self.rng.uniform(-spread, spread)
                    y = cy + self.rng.uniform(-spread, spread)
                mag = self.rng.uniform(0.5, 3.5)
                stars.append(Star(x, y, mag))

        elif shape == "arc":
            # Curved arc
            arc_angle = self.rng.uniform(math.pi * 0.5, math.pi * 1.2)
            start_angle = self.rng.uniform(0, math.pi)
            for i in range(num_stars):
                t = i / max(1, num_stars - 1)
                angle = start_angle + t * arc_angle
                r = spread + self.rng.gauss(0, 0.3)
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                mag = self.rng.uniform(0.5, 3.5)
                if i == num_stars // 2:
                    mag = min(mag, 1.5)
                stars.append(Star(x, y, mag))

        elif shape == "cluster":
            # Tight cluster
            for i in range(num_stars):
                angle = self.rng.uniform(0, 2 * math.pi)
                r = self.rng.uniform(0, spread * 0.8)
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                mag = self.rng.uniform(0.5, 3.5)
                if r < spread * 0.3:
                    mag = min(mag, 2.0)
                stars.append(Star(x, y, mag))

        elif shape == "spiral":
            # Loose spiral
            turns = self.rng.uniform(1.0, 2.5)
            for i in range(num_stars):
                t = i / max(1, num_stars - 1)
                angle = t * turns * 2 * math.pi
                r = t * spread * 1.2
                x = cx + r * math.cos(angle) + self.rng.gauss(0, 0.2)
                y = cy + r * math.sin(angle) + self.rng.gauss(0, 0.2)
                mag = self.rng.uniform(0.5, 3.5)
                stars.append(Star(x, y, mag))

        # Clamp to bounds
        for star in stars:
            star.x = max(0.5, min(self.width - 0.5, star.x))
            star.y = max(0.5, min(self.height - 0.5, star.y))

        return stars

    def _generate_connections(self, num_stars, shape) -> List[Tuple[int, int]]:
        connections = []
        if shape == "chain" or shape == "arc" or shape == "spiral":
            for i in range(num_stars - 1):
                connections.append((i, i + 1))
        elif shape == "triangle":
            connections = [(0, 1), (1, 2), (2, 0)]
            for i in range(3, num_stars):
                # Connect to nearest existing star
                connections.append((i, i - 1))
        elif shape == "cross":
            if num_stars >= 2:
                connections.append((0, 1))
            if num_stars >= 4:
                connections.append((2, 3))
            if num_stars >= 4:
                connections.append((0, 2))
            for i in range(4, num_stars):
                connections.append((i, 0))
        elif shape == "cluster":
            # Connect each star to the closest one (minimum spanning tree approach)
            connected = {0}
            unconnected = set(range(1, num_stars))
            while unconnected:
                best = None
                best_dist = float('inf')
                for c in connected:
                    for u in unconnected:
                        d = abs(c - u)
                        if d < best_dist:
                            best_dist = d
                            best = (c, u)
                if best:
                    connections.append(best)
                    connected.add(best[1])
                    unconnected.discard(best[1])
        return connections

    def _generate_background_stars(self):
        for _ in range(self.num_background_stars):
            x = self.rng.uniform(0, self.width)
            y = self.rng.uniform(0, self.height)
            # Magnitude distribution: most stars are dim
            mag = self.rng.gauss(4.5, 1.5)
            mag = max(1.0, min(6.5, mag))
            self.background_stars.append(Star(x, y, mag))

    def _generate_deep_objects(self):
        symbols = {
            "galaxy": "ꙮ",
            "nebula": "⊛",
            "cluster": "✺",
            "pulsar": "⚡",
            "quasar": "✧",
            "black hole": "◎",
        }
        for _ in range(self.num_deep_objects):
            x = self.rng.uniform(2, self.width - 2)
            y = self.rng.uniform(2, self.height - 2)
            obj_type, sub_type = self.rng.choice(CELESTIAL_OBJECTS)
            symbol = symbols.get(obj_type, "∘")

            if obj_type == "galaxy":
                name = f"{self.rng.choice(GREEK_LETTERS)} Galaxy"
                desc = f"A {sub_type} galaxy, millions of light-years distant."
            elif obj_type == "nebula":
                name = f"{self._generate_name()} Nebula"
                desc = f"An {sub_type} nebula, birthplace of stars."
            elif obj_type == "cluster":
                name = f"{self._generate_name()} Cluster"
                desc = f"A {sub_type} star cluster."
            elif obj_type == "pulsar":
                name = f"PSR {self.rng.randint(1000, 9999)}"
                desc = "A rapidly rotating neutron star."
            elif obj_type == "quasar":
                name = f"QSO {self.rng.randint(1000, 9999)}"
                desc = "An extraordinarily luminous active galactic nucleus."
            elif obj_type == "black hole":
                name = f"BH-{self.rng.randint(100, 999)}"
                desc = "A region of spacetime from which nothing can escape."
            else:
                name = f"OBJ-{self.rng.randint(1000, 9999)}"
                desc = "An unidentified celestial object."

            self.deep_objects.append(CelestialObject(x, y, obj_type, sub_type, name, symbol, desc))

    def _generate_meteor_showers(self):
        """Generate procedural meteor showers that streak across the sky."""
        peak_phrases = [
            "peak activity expected tonight",
            "best viewed after midnight",
            "expect up to 100 meteors per hour",
            "faint but persistent trails",
            "bright fireballs possible",
            "notable for slow-moving meteors",
            "dust from an ancient comet",
            "remnants of a shattered asteroid",
        ]
        for _ in range(self.num_meteor_showers):
            name = self.rng.choice(METEOR_SHOWER_NAMES)
            radiant_x = self.rng.uniform(5, self.width - 5)
            radiant_y = self.rng.uniform(3, self.height - 3)
            angle = self.rng.uniform(0, 2 * math.pi)
            length = self.rng.randint(4, 12)
            intensity = self.rng.randint(3, 15)
            peak_phrase = self.rng.choice(peak_phrases)
            self.meteor_showers.append(MeteorShower(
                name=name,
                radiant_x=radiant_x,
                radiant_y=radiant_y,
                angle=angle,
                length=length,
                intensity=intensity,
                peak_phrase=peak_phrase,
            ))

    def get_statistics(self) -> Dict:
        """Compute and return statistics about the generated star map."""
        total_constellation_stars = sum(len(c.stars) for c in self.constellations)
        brightest_star = None
        brightest_mag = float('inf')
        for c in self.constellations:
            for s in c.stars:
                if s.magnitude < brightest_mag:
                    brightest_mag = s.magnitude
                    brightest_star = s
        for s in self.background_stars:
            if s.magnitude < brightest_mag:
                brightest_mag = s.magnitude
                brightest_star = s

        shape_counts = defaultdict(int)
        # We don't store shape per constellation, but we can count connection patterns
        avg_conn = 0
        if self.constellations:
            avg_conn = sum(len(c.connections) for c in self.constellations) / len(self.constellations)

        return {
            "total_stars": total_constellation_stars + len(self.background_stars),
            "constellation_stars": total_constellation_stars,
            "background_stars": len(self.background_stars),
            "num_constellations": len(self.constellations),
            "num_nebulae": len(self.nebulae),
            "num_deep_objects": len(self.deep_objects),
            "num_meteor_showers": len(self.meteor_showers),
            "brightest_magnitude": round(brightest_mag, 2) if brightest_star else None,
            "avg_constellation_connections": round(avg_conn, 2),
            "avg_stars_per_constellation": round(total_constellation_stars / max(1, len(self.constellations)), 2),
            "map_area": self.width * self.height,
            "star_density": round((total_constellation_stars + len(self.background_stars)) / max(1, self.width * self.height), 4),
        }

    def find_constellation(self, query: str) -> List[Constellation]:
        """Search for constellations matching the query string (case-insensitive)."""
        query_lower = query.lower()
        results = []
        for c in self.constellations:
            if (query_lower in c.name.lower() or
                query_lower in c.title.lower() or
                query_lower in c.full_name.lower()):
                results.append(c)
        return results


# ─── Renderer ──────────────────────────────────────────────────────────────────

class StarMapRenderer:
    """Renders the star map to ASCII with optional ANSI colors."""

    NEBULA_CHARS = "░▒▓"
    CONSTELLATION_LINE = "─│╲╱╳·"

    # ANSI color codes
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "crimson": "\033[38;5;167m",
        "emerald": "\033[38;5;114m",
        "sapphire": "\033[38;5;117m",
        "amber": "\033[38;5;214m",
        "violet": "\033[38;5;177m",
        "silver": "\033[38;5;251m",
        "ashen": "\033[38;5;245m",
        "star_bright": "\033[38;5;229m",
        "star_medium": "\033[38;5;253m",
        "star_dim": "\033[38;5;244m",
        "star_faint": "\033[38;5;240m",
        "constellation_line": "\033[38;5;60m",
        "constellation_label": "\033[38;5;153m",
        "deep_object": "\033[38;5;213m",
        "border": "\033[38;5;240m",
        "title": "\033[38;5;229m\033[1m",
        "coordinate": "\033[38;5;245m",
        "info": "\033[38;5;253m",
        "lore": "\033[38;5;180m",
        "meteor": "\033[38;5;220m",
        "grid": "\033[38;5;236m",
        "stat_label": "\033[38;5;153m",
        "stat_value": "\033[38;5;229m",
    }

    def __init__(self, star_map: StarMapGenerator, use_color=True, show_lines=True,
                 show_labels=True, show_grid=False, show_meteors=True,
                 viewport_x=0, viewport_y=0,
                 viewport_w=None, viewport_h=None):
        self.star_map = star_map
        self.use_color = use_color
        self.show_lines = show_lines
        self.show_labels = show_labels
        self.show_grid = show_grid
        self.show_meteors = show_meteors
        self.vx = viewport_x
        self.vy = viewport_y
        self.vw = viewport_w or star_map.width
        self.vh = viewport_h or star_map.height

    def _c(self, color_name: str, text: str) -> str:
        if not self.use_color:
            return text
        return f"{self.COLORS.get(color_name, '')}{text}{self.COLORS['reset']}"

    def render(self) -> str:
        """Render the full star map as a string."""
        lines = []

        # Title
        seed_str = f"Seed: {self.star_map.seed:06d}"
        title = f"✦ Celestial Atlas — Procedural Constellation Map ✦"
        lines.append(self._c("title", title.center(self.vw + 20)))
        lines.append(self._c("coordinate", seed_str.center(self.vw + 20)))
        lines.append("")

        # Build the canvas
        canvas, color_map = self._build_canvas()

        # Render the canvas with border
        lines.append(self._render_canvas_with_border(canvas, color_map))

        # Legend
        lines.append("")
        lines.append(self._render_legend())

        # Constellation catalog
        lines.append("")
        lines.append(self._render_catalog())

        return "\n".join(lines)

    def render_compact(self) -> str:
        """Render only the visual map (no catalog/legend)."""
        canvas, color_map = self._build_canvas()
        return self._render_canvas_with_border(canvas, color_map)

    def _build_canvas(self) -> Tuple[List[List[str]], List[List[str]]]:
        """Build a 2D character canvas of the star map. Returns (canvas, color_map)."""
        w = self.vw
        h = self.vh
        canvas = [[" " for _ in range(w)] for _ in range(h)]
        color_map = [["" for _ in range(w)] for _ in range(h)]  # track colors

        # Draw grid first (lowest layer)
        if self.show_grid:
            self._draw_grid(canvas, color_map)

        # Draw nebulae (background)
        for nebula in self.star_map.nebulae:
            self._draw_nebula(canvas, color_map, nebula)

        # Draw meteor shower streaks
        if self.show_meteors:
            for shower in self.star_map.meteor_showers:
                self._draw_meteor_shower(canvas, color_map, shower)

        # Draw constellation lines
        if self.show_lines:
            for constellation in self.star_map.constellations:
                self._draw_constellation_lines(canvas, color_map, constellation)

        # Draw background stars
        for star in self.star_map.background_stars:
            sx, sy = int(round(star.x)), int(round(star.y))
            if 0 <= sx < w and 0 <= sy < h:
                ch = star.display_char
                canvas[sy][sx] = ch
                if star.magnitude < 3.0:
                    color_map[sy][sx] = "star_medium"
                else:
                    color_map[sy][sx] = "star_dim"

        # Draw constellation stars (on top)
        for constellation in self.star_map.constellations:
            for star in constellation.stars:
                sx, sy = int(round(star.x)), int(round(star.y))
                if 0 <= sx < w and 0 <= sy < h:
                    ch = star.display_char
                    canvas[sy][sx] = ch
                    color_map[sy][sx] = "star_bright"

        # Draw deep sky objects
        for obj in self.star_map.deep_objects:
            ox, oy = int(round(obj.x)), int(round(obj.y))
            if 0 <= ox < w and 0 <= oy < h:
                canvas[oy][ox] = obj.symbol
                color_map[oy][ox] = "deep_object"

        # Draw constellation labels
        if self.show_labels:
            for constellation in self.star_map.constellations:
                cx, cy = constellation.center
                label = constellation.name
                lx = int(round(cx - len(label) / 2))
                ly = int(round(cy))
                for i, ch in enumerate(label):
                    px = lx + i
                    if 0 <= px < w and 0 <= ly < h:
                        canvas[ly][px] = ch.lower() if ch.isupper() and i > 0 else ch
                        color_map[ly][px] = "constellation_label"

        return canvas, color_map

    def _draw_grid(self, canvas, color_map):
        """Draw a subtle coordinate grid on the canvas."""
        w, h = self.vw, self.vh
        # Vertical lines every 10 chars
        for x in range(10, w, 10):
            for y in range(h):
                if canvas[y][x] == " ":
                    canvas[y][x] = "┊"
                    color_map[y][x] = "grid"
        # Horizontal lines every 10 chars
        for y in range(10, h, 10):
            for x in range(w):
                if canvas[y][x] == " ":
                    canvas[y][x] = "┄"
                    color_map[y][x] = "grid"

    def _draw_nebula(self, canvas, color_map, nebula: Nebula):
        w, h = self.vw, self.vh
        rng = random.Random(int(nebula.x * 1000 + nebula.y * 1000))
        r_int = int(nebula.radius)
        for dy in range(-r_int, r_int + 1):
            for dx in range(-r_int, r_int + 1):
                dist = math.hypot(dx, dy)
                if dist < nebula.radius:
                    prob = nebula.density * (1 - dist / nebula.radius)
                    if rng.random() < prob:
                        px = int(round(nebula.x)) + dx
                        py = int(round(nebula.y)) + dy
                        if 0 <= px < w and 0 <= py < h:
                            if canvas[py][px] == " ":
                                if prob > 0.5:
                                    canvas[py][px] = "▓"
                                elif prob > 0.3:
                                    canvas[py][px] = "▒"
                                else:
                                    canvas[py][px] = "░"
                                color_map[py][px] = nebula.color

    def _draw_meteor_shower(self, canvas, color_map, shower: MeteorShower):
        """Draw a meteor shower as a streak of bright characters."""
        w, h = self.vw, self.vh
        # Draw the main streak line from the radiant point
        for i in range(shower.length):
            x = shower.radiant_x + i * math.cos(shower.angle) * 1.5
            y = shower.radiant_y + i * math.sin(shower.angle) * 0.8
            ix, iy = int(round(x)), int(round(y))
            if 0 <= ix < w and 0 <= iy < h:
                # Meteor characters fade from bright to dim
                if i == 0:
                    ch = "★"
                elif i < shower.length // 3:
                    ch = "✦"
                elif i < 2 * shower.length // 3:
                    ch = "·"
                else:
                    ch = "∘"
                # Only draw if the cell is empty or has a dim background
                if canvas[iy][ix] in (" ", "∘", "·", "░", "▒", "▓", "┊", "┄"):
                    canvas[iy][ix] = ch
                    color_map[iy][ix] = "meteor"
        # Scatter some individual meteor dots around the radiant
        scatter_rng = random.Random(int(shower.radiant_x * 100 + shower.radiant_y * 100))
        for _ in range(shower.intensity):
            offset_dist = scatter_rng.uniform(0, shower.length * 1.2)
            offset_angle = shower.angle + scatter_rng.gauss(0, 0.3)
            mx = shower.radiant_x + offset_dist * math.cos(offset_angle) * 1.5
            my = shower.radiant_y + offset_dist * math.sin(offset_angle) * 0.8
            mix, miy = int(round(mx)), int(round(my))
            if 0 <= mix < w and 0 <= miy < h:
                if canvas[miy][mix] in (" ", "∘", "░", "┊", "┄"):
                    canvas[miy][mix] = scatter_rng.choice("·∘")
                    color_map[miy][mix] = "meteor"

    def _draw_constellation_lines(self, canvas, color_map, constellation: Constellation):
        for i, j in constellation.connections:
            if i < len(constellation.stars) and j < len(constellation.stars):
                s1 = constellation.stars[i]
                s2 = constellation.stars[j]
                self._draw_line(canvas, color_map, s1.x, s1.y, s2.x, s2.y)

    def _draw_line(self, canvas, color_map, x1, y1, x2, y2):
        """Draw a line between two points using Bresenham's algorithm."""
        w, h = self.vw, self.vh
        ix1, iy1, ix2, iy2 = int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))

        dx = abs(ix2 - ix1)
        dy = abs(iy2 - iy1)
        sx = 1 if ix1 < ix2 else -1
        sy = 1 if iy1 < iy2 else -1
        err = dx - dy

        x, y = ix1, iy1
        while True:
            if 0 <= x < w and 0 <= y < h:
                if canvas[y][x] == " " or canvas[y][x] in "░▒▓┊┄":
                    canvas[y][x] = "·"
                    color_map[y][x] = "constellation_line"
            if x == ix2 and y == iy2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def _render_canvas_with_border(self, canvas, color_map) -> str:
        """Render the canvas with border and per-character color support."""
        w = self.vw
        lines = []

        # Top border with coordinate markers every 10 chars
        top_border = "┌"
        for x in range(w):
            if self.show_grid and x > 0 and x % 10 == 0:
                top_border += "┬"
            else:
                top_border += "─"
        top_border += "┐"
        lines.append(self._c("border", top_border))

        for y, row in enumerate(canvas):
            line = self._c("border", "│")
            for x, ch in enumerate(row):
                if self.use_color and color_map[y][x]:
                    # Apply per-character color from the color map
                    color_code = self.COLORS.get(color_map[y][x], "")
                    if color_code:
                        line += f"{color_code}{ch}{self.COLORS['reset']}"
                    else:
                        line += ch
                else:
                    line += ch
            line += self._c("border", "│")
            lines.append(line)

        # Bottom border with coordinate markers
        bot_border = "└"
        for x in range(w):
            if self.show_grid and x > 0 and x % 10 == 0:
                bot_border += "┴"
            else:
                bot_border += "─"
        bot_border += "┘"
        lines.append(self._c("border", bot_border))

        # Coordinate labels along the bottom if grid is shown
        if self.show_grid:
            coord_line = " "
            for x in range(w):
                if x % 10 == 0 and x > 0:
                    label = str(x)
                    for ci, cch in enumerate(label):
                        if x - len(label) + 1 + ci >= 0:
                            coord_line += cch if ci == len(label) - 1 else " "
                    # Pad remaining positions
                    remaining = 10 - len(label)
                    coord_line += " " * remaining
                else:
                    coord_line += " "
            lines.append(self._c("coordinate", coord_line))

        return "\n".join(lines)

    def _render_legend(self) -> str:
        lines = []
        lines.append(self._c("title", "── Legend ──"))

        legend_items = [
            ("★", "Bright star (mag < 1)"),
            ("✦✧", "Medium star (mag 1-2)"),
            ("⋆", "Faint star (mag 2-3)"),
            ("·", "Dim star / constellation line"),
            ("∘", "Very dim star (mag > 4.5)"),
            ("·", "Constellation connection"),
            ("░▒▓", "Nebula"),
            ("·∘★", "Meteor shower"),
        ]

        for sym, desc in legend_items:
            lines.append(f"  {sym}  {desc}")

        # Deep objects
        lines.append("")
        deep_items = [
            ("ꙮ", "Galaxy"),
            ("⊛", "Nebula"),
            ("✺", "Star cluster"),
            ("⚡", "Pulsar"),
            ("✧", "Quasar"),
            ("◎", "Black hole"),
        ]
        for sym, desc in deep_items:
            lines.append(f"  {sym}  {desc}")

        if self.show_grid:
            lines.append("")
            lines.append(f"  ┊┄  Coordinate grid")

        return "\n".join(lines)

    def _render_catalog(self) -> str:
        lines = []
        lines.append(self._c("title", "── Constellation Catalog ──"))
        lines.append("")

        for c in sorted(self.star_map.constellations, key=lambda c: c.id):
            star_count = len(c.stars)
            brightest = min(s.magnitude for s in c.stars) if c.stars else 0
            lines.append(self._c("constellation_label", f"  {c.id+1:2d}. {c.full_name}"))
            lines.append(self._c("info", f"      Stars: {star_count}  |  Brightest: mag {brightest:.1f}"))
            # Star names
            named_stars = [s for s in c.stars if s.greek_letter]
            if named_stars:
                star_names = ", ".join(s.greek_letter for s in named_stars[:6])
                lines.append(self._c("coordinate", f"      Notable stars: {star_names}"))
            lines.append(self._c("lore", f"      {c.lore}"))
            lines.append("")

        # Deep sky objects
        if self.star_map.deep_objects:
            lines.append(self._c("title", "── Deep Sky Objects ──"))
            lines.append("")
            for obj in self.star_map.deep_objects:
                type_label = obj.sub_type or obj.obj_type
                lines.append(self._c("deep_object", f"  {obj.symbol} {obj.name}"))
                lines.append(self._c("info", f"      {obj.description}"))
                lines.append("")

        # Nebulae
        if self.star_map.nebulae:
            lines.append(self._c("title", "── Nebulae ──"))
            lines.append("")
            for neb in self.star_map.nebulae:
                lines.append(self._c(neb.color, f"  {neb.name}"))
                lines.append(self._c("info", f"      Radius: {neb.radius:.1f} ly  |  Density: {neb.density:.0%}"))
                lines.append("")

        # Meteor showers
        if self.star_map.meteor_showers:
            lines.append(self._c("title", "── Meteor Showers ──"))
            lines.append("")
            for shower in self.star_map.meteor_showers:
                lines.append(self._c("meteor", f"  ✦ {shower.name}"))
                angle_deg = math.degrees(shower.angle) % 360
                lines.append(self._c("info", f"      Radiant: ({shower.radiant_x:.1f}, {shower.radiant_y:.1f})  |  "
                                             f"Angle: {angle_deg:.0f}°  |  {shower.peak_phrase}"))
                lines.append("")

        return "\n".join(lines)

    def render_statistics(self) -> str:
        """Render a formatted statistics summary."""
        stats = self.star_map.get_statistics()
        lines = []
        lines.append(self._c("title", "── Map Statistics ──"))
        lines.append("")
        lines.append(self._c("stat_label", f"  Total stars:           ") + self._c("stat_value", f"{stats['total_stars']}"))
        lines.append(self._c("stat_label", f"  Constellation stars:   ") + self._c("stat_value", f"{stats['constellation_stars']}"))
        lines.append(self._c("stat_label", f"  Background stars:      ") + self._c("stat_value", f"{stats['background_stars']}"))
        lines.append(self._c("stat_label", f"  Constellations:        ") + self._c("stat_value", f"{stats['num_constellations']}"))
        lines.append(self._c("stat_label", f"  Nebulae:               ") + self._c("stat_value", f"{stats['num_nebulae']}"))
        lines.append(self._c("stat_label", f"  Deep sky objects:      ") + self._c("stat_value", f"{stats['num_deep_objects']}"))
        lines.append(self._c("stat_label", f"  Meteor showers:        ") + self._c("stat_value", f"{stats['num_meteor_showers']}"))
        lines.append(self._c("stat_label", f"  Brightest magnitude:   ") + self._c("stat_value", f"{stats['brightest_magnitude']:.2f}" if stats['brightest_magnitude'] is not None else "N/A"))
        lines.append(self._c("stat_label", f"  Avg connections:       ") + self._c("stat_value", f"{stats['avg_constellation_connections']}"))
        lines.append(self._c("stat_label", f"  Avg stars/constellation: ") + self._c("stat_value", f"{stats['avg_stars_per_constellation']}"))
        lines.append(self._c("stat_label", f"  Map area:             ") + self._c("stat_value", f"{stats['map_area']} chars²"))
        lines.append(self._c("stat_label", f"  Star density:         ") + self._c("stat_value", f"{stats['star_density']:.4f} stars/char²"))
        return "\n".join(lines)

    def render_search_results(self, results: List[Constellation]) -> str:
        """Render search results for constellations."""
        if not results:
            return self._c("info", "No constellations found matching your query.")

        lines = []
        lines.append(self._c("title", f"── Search Results ({len(results)} found) ──"))
        lines.append("")
        for c in results:
            star_count = len(c.stars)
            brightest = min(s.magnitude for s in c.stars) if c.stars else 0
            lines.append(self._c("constellation_label", f"  {c.full_name}"))
            lines.append(self._c("info", f"      Stars: {star_count}  |  Brightest: mag {brightest:.1f}"))
            lines.append(self._c("coordinate", f"      Center: ({c.center[0]:.1f}, {c.center[1]:.1f})"))
            lines.append(self._c("lore", f"      {c.lore}"))
            lines.append("")
        return "\n".join(lines)


# ─── Interactive Navigator ─────────────────────────────────────────────────────

class StarMapNavigator:
    """Interactive navigator for exploring the star map in the terminal."""

    def __init__(self, star_map: StarMapGenerator):
        self.star_map = star_map
        self.cursor_x = star_map.width // 2
        self.cursor_y = star_map.height // 2
        self.selected_constellation = None
        self.renderer = StarMapRenderer(star_map, use_color=True, show_lines=True,
                                        show_labels=True)

    def find_nearest_constellation(self, x, y) -> Optional[Constellation]:
        """Find the constellation whose center is closest to the given coordinates."""
        best = None
        best_dist = float('inf')
        for c in self.star_map.constellations:
            dist = math.hypot(c.center[0] - x, c.center[1] - y)
            if dist < best_dist:
                best_dist = dist
                best = c
        return best

    def find_nearest_star(self, x, y) -> Optional[Star]:
        """Find the nearest constellation star to the given coordinates."""
        best = None
        best_dist = float('inf')
        for c in self.star_map.constellations:
            for s in c.stars:
                dist = math.hypot(s.x - x, s.y - y)
                if dist < best_dist:
                    best_dist = dist
                    best = s
        return best

    def find_object_at(self, x, y, radius=2.0) -> Optional[CelestialObject]:
        """Find a deep sky object near the given coordinates."""
        for obj in self.star_map.deep_objects:
            if math.hypot(obj.x - x, obj.y - y) < radius:
                return obj
        return None

    def get_info_at(self, x, y) -> str:
        """Get a formatted string describing what's at or near the given map coordinates."""
        lines = []
        lines.append(f"Position: ({x}, {y})")

        # Check for constellation
        const = self.find_nearest_constellation(x, y)
        if const:
            dist = math.hypot(const.center[0] - x, const.center[1] - y)
            if dist < 6:
                lines.append(f"Nearest constellation: {const.full_name} (dist: {dist:.1f})")
                lines.append(f"  Lore: {const.lore}")

        # Check for star
        star = self.find_nearest_star(x, y)
        if star:
            dist = math.hypot(star.x - x, star.y - y)
            if dist < 3:
                name = star.name or "unnamed"
                lines.append(f"Nearest star: {name} (mag {star.magnitude:.2f}, dist: {dist:.1f})")

        # Check for deep object
        obj = self.find_object_at(x, y)
        if obj:
            lines.append(f"Deep sky object: {obj.name} — {obj.description}")

        if len(lines) == 1:
            lines.append("Empty sky at this position.")

        return "\n".join(lines)

    def run(self):
        """Run the interactive navigation loop (requires a terminal with tty support)."""
        import tty
        import termios

        print("✦ Interactive Constellation Navigator ✦")
        print("Use arrow keys to move, 'i' for info, 'q' to quit")
        print()

        # Save original terminal settings
        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
        except termios.error:
            # Not a real terminal — fall back to line mode
            self._run_line_mode()
            return

        try:
            tty.setraw(fd)
            while True:
                # Render current view
                self._render_view()
                # Read key
                ch = sys.stdin.read(1)
                if ch == 'q' or ch == '\x03':  # q or Ctrl-C
                    break
                elif ch == '\x1b':  # escape sequence (arrow keys)
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        if ch3 == 'A':    # up
                            self.cursor_y = max(0, self.cursor_y - 1)
                        elif ch3 == 'B':  # down
                            self.cursor_y = min(self.star_map.height - 1, self.cursor_y + 1)
                        elif ch3 == 'C':  # right
                            self.cursor_x = min(self.star_map.width - 1, self.cursor_x + 1)
                        elif ch3 == 'D':  # left
                            self.cursor_x = max(0, self.cursor_x - 1)
                elif ch == 'i':
                    # Show info at cursor position
                    sys.stdout.write("\r\n" + self.get_info_at(self.cursor_x, self.cursor_y) + "\r\n")
                    sys.stdout.write("Press any key to continue...\r\n")
                    sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            print()  # Clean exit newline

    def _run_line_mode(self):
        """Fallback navigation mode for non-tty environments."""
        print("Running in line mode (no tty detected). Type 'help' for commands.")
        while True:
            try:
                cmd = input(f"({self.cursor_x},{self.cursor_y})> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if cmd in ('q', 'quit', 'exit'):
                break
            elif cmd == 'help':
                print("Commands: w/up  s/down  a/left  d/right  i/info  q/quit")
            elif cmd in ('w', 'up'):
                self.cursor_y = max(0, self.cursor_y - 1)
            elif cmd in ('s', 'down'):
                self.cursor_y = min(self.star_map.height - 1, self.cursor_y + 1)
            elif cmd in ('a', 'left'):
                self.cursor_x = max(0, self.cursor_x - 1)
            elif cmd in ('d', 'right'):
                self.cursor_x = min(self.star_map.width - 1, self.cursor_x + 1)
            elif cmd in ('i', 'info'):
                print(self.get_info_at(self.cursor_x, self.cursor_y))
            else:
                print("Unknown command. Type 'help' for commands.")

    def _render_view(self):
        """Render the current view with cursor indicator to stdout."""
        # Clear screen and move to top
        sys.stdout.write("\033[2J\033[H")
        # Render compact map
        output = self.renderer.render_compact()
        sys.stdout.write(output + "\r\n")
        # Show cursor position and info
        sys.stdout.write(f"\r\nCursor: ({self.cursor_x}, {self.cursor_y})  [arrows=move, i=info, q=quit]\r\n")
        sys.stdout.flush()


# ─── JSON Export ────────────────────────────────────────────────────────────────

def export_json(star_map: StarMapGenerator, filepath: str):
    """Export the star map data as JSON."""
    data = {
        "seed": star_map.seed,
        "width": star_map.width,
        "height": star_map.height,
        "constellations": [],
        "deep_objects": [],
        "nebulae": [],
        "meteor_showers": [],
        "statistics": star_map.get_statistics(),
    }

    for c in star_map.constellations:
        c_data = {
            "id": c.id,
            "name": c.name,
            "title": c.title,
            "full_name": c.full_name,
            "center": list(c.center),
            "lore": c.lore,
            "stars": [
                {
                    "x": round(s.x, 2),
                    "y": round(s.y, 2),
                    "magnitude": round(s.magnitude, 2),
                    "name": s.name,
                    "greek_letter": s.greek_letter,
                }
                for s in c.stars
            ],
            "connections": c.connections,
        }
        data["constellations"].append(c_data)

    for obj in star_map.deep_objects:
        data["deep_objects"].append({
            "x": round(obj.x, 2),
            "y": round(obj.y, 2),
            "type": obj.obj_type,
            "subtype": obj.sub_type,
            "name": obj.name,
            "description": obj.description,
        })

    for neb in star_map.nebulae:
        data["nebulae"].append({
            "x": round(neb.x, 2),
            "y": round(neb.y, 2),
            "radius": round(neb.radius, 2),
            "name": neb.name,
            "density": round(neb.density, 2),
        })

    for shower in star_map.meteor_showers:
        data["meteor_showers"].append({
            "name": shower.name,
            "radiant_x": round(shower.radiant_x, 2),
            "radiant_y": round(shower.radiant_y, 2),
            "angle": round(math.degrees(shower.angle), 2),
            "length": shower.length,
            "intensity": shower.intensity,
            "peak_phrase": shower.peak_phrase,
        })

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="✦ Procedural Constellation Map Generator ✦",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  constellation_map                        # Random map, 80x40
  constellation_map --seed 42               # Reproducible map
  constellation_map --width 120 --height 50 # Larger map
  constellation_map --no-color              # No ANSI colors
  constellation_map --no-lines              # Hide constellation lines
  constellation_map --export map.json       # Export as JSON
  constellation_map --constellations 20     # More constellations
  constellation_map --find Phoenix          # Search for constellations
  constellation_map --stats                 # Show map statistics
  constellation_map --grid                  # Show coordinate grid
  constellation_map --interactive           # Interactive navigation mode
  constellation_map --no-meteors            # Hide meteor showers
        """
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible maps")
    parser.add_argument("--width", type=int, default=80,
                        help="Map width in characters (default: 80)")
    parser.add_argument("--height", type=int, default=40,
                        help="Map height in characters (default: 40)")
    parser.add_argument("--constellations", type=int, default=12,
                        help="Number of constellations (default: 12)")
    parser.add_argument("--stars", type=int, default=200,
                        help="Number of background stars (default: 200)")
    parser.add_argument("--nebulae", type=int, default=3,
                        help="Number of nebulae (default: 3)")
    parser.add_argument("--deep-objects", type=int, default=8,
                        help="Number of deep sky objects (default: 8)")
    parser.add_argument("--meteor-showers", type=int, default=2,
                        help="Number of meteor showers (default: 2)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors")
    parser.add_argument("--no-lines", action="store_true",
                        help="Hide constellation connection lines")
    parser.add_argument("--no-labels", action="store_true",
                        help="Hide constellation labels")
    parser.add_argument("--no-meteors", action="store_true",
                        help="Hide meteor shower streaks")
    parser.add_argument("--grid", action="store_true",
                        help="Show coordinate grid overlay")
    parser.add_argument("--compact", action="store_true",
                        help="Compact output: no catalog, just the map")
    parser.add_argument("--export", type=str, default=None,
                        help="Export star map data as JSON to file")
    parser.add_argument("--catalog-only", action="store_true",
                        help="Only show the constellation catalog")
    parser.add_argument("--find", type=str, default=None,
                        help="Search for constellations by name or title")
    parser.add_argument("--stats", action="store_true",
                        help="Show map statistics")
    parser.add_argument("--interactive", action="store_true",
                        help="Launch interactive navigation mode")

    args = parser.parse_args()

    # Generate
    gen = StarMapGenerator(
        width=args.width,
        height=args.height,
        seed=args.seed,
        num_constellations=args.constellations,
        num_background_stars=args.stars,
        num_nebulae=args.nebulae,
        num_deep_objects=args.deep_objects,
        num_meteor_showers=args.meteor_showers,
    )
    gen.generate()

    # Export JSON if requested
    if args.export:
        export_json(gen, args.export)
        print(f"Star map exported to {args.export}")
        return

    # Create renderer
    renderer = StarMapRenderer(
        gen,
        use_color=not args.no_color,
        show_lines=not args.no_lines,
        show_labels=not args.no_labels,
        show_grid=args.grid,
        show_meteors=not args.no_meteors,
    )

    # Search mode
    if args.find:
        results = gen.find_constellation(args.find)
        print(renderer.render_search_results(results))
        return

    # Statistics mode
    if args.stats:
        print(renderer.render_statistics())
        return

    # Interactive mode
    if args.interactive:
        navigator = StarMapNavigator(gen)
        navigator.run()
        return

    # Catalog-only mode
    if args.catalog_only:
        print(renderer._render_catalog())
        return

    # Compact mode
    if args.compact:
        print(renderer.render_compact())
        return

    # Full render
    print(renderer.render())


if __name__ == "__main__":
    main()