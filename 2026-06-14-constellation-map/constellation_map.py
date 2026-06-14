#!/usr/bin/env python3
"""
Procedural Constellation Map Generator
=======================================
Generates a rich, navigable ASCII star map with procedurally created
constellations, mythical names, lore, and celestial objects.
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
    "Osa", "Pyr", "Qui", "Rav", "Som", "Tel", "Umi", "Vel", "Wy", "Zar"
]

CONSTELLATION_SUFFIXES = [
    "ara", "ius", "ion", "ath", "eon", "iel", "oth", "ura", "yx", "is",
    "ax", "os", "ia", "on", "um", "us", "a", "en", "or", "ix",
    "iel", "oth", "yne", "ath", "ora"
]

CONSTELLATION_TYPES = [
    "The Guardian", "The Wanderer", "The Phoenix", "The Serpent", "The Crown",
    "The Scepter", "The Shield", "The Dragon", "The Phoenix", "The Oracle",
    "The Sentinel", "The Harbinger", "The Wanderer", "The Flame", "The Frost",
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

BRIGHT_STARS = "✦✧⋆✶★☆*·°•∘"

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
        if self.magnitude < 1.0:
            return random.choice("★✦")
        elif self.magnitude < 2.0:
            return random.choice("✧✶")
        elif self.magnitude < 3.0:
            return "⋆"
        elif self.magnitude < 4.5:
            return "·"
        else:
            return "∘"
    
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


# ─── Star Map Generator ────────────────────────────────────────────────────────

class StarMapGenerator:
    def __init__(self, width=80, height=40, seed=None, num_constellations=12,
                 num_background_stars=200, num_nebulae=3, num_deep_objects=8):
        self.width = width
        self.height = height
        self.seed = seed or random.randint(0, 999999)
        self.rng = random.Random(self.seed)
        self.num_constellations = num_constellations
        self.num_background_stars = num_background_stars
        self.num_nebulae = num_nebulae
        self.num_deep_objects = num_deep_objects
        
        self.constellations: List[Constellation] = []
        self.background_stars: List[Star] = []
        self.nebulae: List[Nebula] = []
        self.deep_objects: List[CelestialObject] = []
        
    def generate(self):
        """Generate the complete star map."""
        self._generate_nebulae()
        self._generate_constellations()
        self._generate_background_stars()
        self._generate_deep_objects()
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
            # Connect each star to the closest one
            connected = {0}
            unconnected = set(range(1, num_stars))
            while unconnected:
                # Find closest pair
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
    }
    
    def __init__(self, star_map: StarMapGenerator, use_color=True, show_lines=True,
                 show_labels=True, show_grid=False, viewport_x=0, viewport_y=0,
                 viewport_w=None, viewport_h=None):
        self.star_map = star_map
        self.use_color = use_color
        self.show_lines = show_lines
        self.show_labels = show_labels
        self.show_grid = show_grid
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
        canvas = self._build_canvas()
        
        # Render the canvas with border
        lines.append(self._render_canvas_with_border(canvas))
        
        # Legend
        lines.append("")
        lines.append(self._render_legend())
        
        # Constellation catalog
        lines.append("")
        lines.append(self._render_catalog())
        
        return "\n".join(lines)
    
    def _build_canvas(self) -> List[List[str]]:
        """Build a 2D character canvas of the star map."""
        w = self.vw
        h = self.vh
        canvas = [[" " for _ in range(w)] for _ in range(h)]
        color_map = [["" for _ in range(w)] for _ in range(h)]  # track colors
        
        # Draw nebulae first (background)
        for nebula in self.star_map.nebulae:
            self._draw_nebula(canvas, color_map, nebula)
        
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
        
        return canvas
    
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
                if canvas[y][x] == " " or canvas[y][x] in "░▒▓":
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
    
    def _render_canvas_with_border(self, canvas) -> str:
        w = self.vw
        lines = []
        
        # Top border with coordinate markers
        border_top = self._c("border", "┌" + "─" * w + "┐")
        lines.append(border_top)
        
        for y, row in enumerate(canvas):
            line = self._c("border", "│")
            for x, ch in enumerate(row):
                # Check if there's a color for this cell
                # We'll just apply the character; colors applied per-char would be too complex
                line += ch
            line += self._c("border", "│")
            lines.append(line)
        
        border_bottom = self._c("border", "└" + "─" * w + "┘")
        lines.append(border_bottom)
        
        return "\n".join(lines)
    
    def _render_legend(self) -> str:
        lines = []
        lines.append(self._c("title", "── Legend ──"))
        
        legend_items = [
            ("★✦", "Bright star (mag < 1)"),
            ("✧✶", "Medium star (mag 1-2)"),
            ("⋆", "Faint star (mag 2-3)"),
            ("·", "Dim star / constellation line"),
            ("∘", "Very dim star (mag > 4.5)"),
            ("·", "Constellation connection"),
            ("░▒▓", "Nebula"),
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
        
        return "\n".join(lines)


# ─── Interactive Navigator ─────────────────────────────────────────────────────

class StarMapNavigator:
    """Simple interactive navigator for exploring the star map."""
    
    def __init__(self, star_map: StarMapGenerator):
        self.star_map = star_map
        self.cursor_x = star_map.width // 2
        self.cursor_y = star_map.height // 2
        self.selected_constellation = None
        self.info_mode = False
    
    def find_nearest_constellation(self, x, y) -> Optional[Constellation]:
        best = None
        best_dist = float('inf')
        for c in self.star_map.constellations:
            dist = math.hypot(c.center[0] - x, c.center[1] - y)
            if dist < best_dist:
                best_dist = dist
                best = c
        return best
    
    def find_nearest_star(self, x, y) -> Optional[Star]:
        best = None
        best_dist = float('inf')
        for c in self.star_map.constellations:
            for s in c.stars:
                dist = math.hypot(s.x - x, s.y - y)
                if dist < best_dist:
                    best_dist = dist
                    best = s
        return best


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
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="✦ Procedural Constellation Map Generator ✦",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  constellation-map                    # Random map, 80x40
  constellation-map --seed 42          # Reproducible map
  constellation-map --width 120 --height 50  # Larger map
  constellation-map --no-color         # No ANSI colors
  constellation-map --no-lines         # Hide constellation lines
  constellation-map --export map.json  # Export as JSON
  constellation-map --constellations 20  # More constellations
        """
    )
    
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
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors")
    parser.add_argument("--no-lines", action="store_true",
                        help="Hide constellation connection lines")
    parser.add_argument("--no-labels", action="store_true",
                        help="Hide constellation labels")
    parser.add_argument("--compact", action="store_true",
                        help="Compact output: no catalog, just the map")
    parser.add_argument("--export", type=str, default=None,
                        help="Export star map data as JSON to file")
    parser.add_argument("--catalog-only", action="store_true",
                        help="Only show the constellation catalog")
    
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
    )
    gen.generate()
    
    # Export JSON if requested
    if args.export:
        export_json(gen, args.export)
        print(f"Star map exported to {args.export}")
        return
    
    # Render
    renderer = StarMapRenderer(
        gen,
        use_color=not args.no_color,
        show_lines=not args.no_lines,
        show_labels=not args.no_labels,
    )
    
    if args.catalog_only:
        print(renderer._render_catalog())
    else:
        output = renderer.render()
        if args.compact:
            # Only show the visual map portion
            lines = output.split("\n")
            map_lines = []
            in_map = False
            for line in lines:
                if line.startswith("┌"):
                    in_map = True
                if in_map:
                    map_lines.append(line)
                if line.startswith("└"):
                    in_map = False
                    break
            print("\n".join(map_lines))
        else:
            print(output)


if __name__ == "__main__":
    main()