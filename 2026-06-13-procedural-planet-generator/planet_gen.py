#!/usr/bin/env python3
"""
Procedural Planet Generator
Generates fictional planets with detailed properties, atmosphere, life forms,
and ASCII art globe renderings. Each planet is seeded for reproducibility.
"""

import hashlib
import math
import random
import sys
import argparse
from dataclasses import dataclass, field
from typing import List, Optional


# ─── Data tables ──────────────────────────────────────────────────────────────

STAR_TYPES = {
    "O": {"color": "Blue", "temp_range": (30000, 60000), "mass_range": (16, 150), "freq": 0.00003},
    "B": {"color": "Blue-white", "temp_range": (10000, 30000), "mass_range": (2.1, 16), "freq": 0.13},
    "A": {"color": "White", "temp_range": (7500, 10000), "mass_range": (1.4, 2.1), "freq": 0.6},
    "F": {"color": "Yellow-white", "temp_range": (6000, 7500), "mass_range": (1.04, 1.4), "freq": 3.0},
    "G": {"color": "Yellow", "temp_range": (5200, 6000), "mass_range": (0.8, 1.04), "freq": 7.6},
    "K": {"color": "Orange", "temp_range": (3700, 5200), "mass_range": (0.45, 0.8), "freq": 12.1},
    "M": {"color": "Red", "temp_range": (2400, 3700), "mass_range": (0.08, 0.45), "freq": 76.5},
}

PLANET_TYPES = [
    ("Lava World", 0.05),
    ("Desert World", 0.10),
    ("Ice World", 0.08),
    ("Ocean World", 0.12),
    ("Terran World", 0.10),
    ("Gas Giant", 0.20),
    ("Ice Giant", 0.10),
    ("Toxic World", 0.07),
    ("Crystalline World", 0.04),
    ("Storm World", 0.06),
    ("Megastructure", 0.02),
    ("Rogue Planet", 0.06),
]

ATMOSPHERES = {
    "Lava World": ["Sulfur Dioxide", "Carbon Dioxide", "Volcanic Ash Clouds", "None - Escaped to Space"],
    "Desert World": ["Thin Carbon Dioxide", "Nitrogen/Argon", "Dust-laden Nitrogen", "None"],
    "Ice World": ["Thin Nitrogen", "Methane/Nitrogen", "Carbon Dioxide", "Trace Oxygen"],
    "Ocean World": ["Nitrogen/Oxygen", "Water Vapor Rich", "Carbon Dioxide/Nitrogen", "Dense Hydrogen"],
    "Terran World": ["Nitrogen/Oxygen", "Nitrogen/Oxygen/Argon", "Dense Nitrogen/Oxygen", "Thin Nitrogen/Oxygen"],
    "Gas Giant": ["Hydrogen/Helium", "Hydrogen/Helium/Methane", "Ammonia Clouds", "Water Vapor Deeps"],
    "Ice Giant": ["Hydrogen/Helium/Methane", "Hydrogen/Helium/Ammonia", "Methane-rich", "Neon/Argon traces"],
    "Toxic World": ["Chlorine", "Hydrogen Sulfide", "Ammonia/Carbon Monoxide", "Acid Vapor"],
    "Crystalline World": ["Thin Silicate", "Quartz Dust", "Trace Gases", "None"],
    "Storm World": ["Supercritical Water", "Dense Hydrogen/Helium", "Ammonia/Thunderclouds", "Ionized Plasma"],
    "Megastructure": ["Artificial Nitrogen/Oxygen", "Engineered Mix", "Pressurized Dome Atmosphere", "Recycled Air"],
    "Rogue Planet": ["Thin Nitrogen/Methane", "Condensed CO2", "None - Stripped", "Ice-shielded Trace"],
}

LIFE_LEVELS = {
    "Lava World": ["None", "Extremophile Microbes", "Silicon-based Crystals"],
    "Desert World": ["None", "Extremophile Microbes", "Hardy Insectoids", "Subterranean Fungi Networks"],
    "Ice World": ["None", "Psychrophilic Microbes", "Ice-dwelling Organisms", "Subsurface Ocean Life"],
    "Ocean World": ["None", "Microbial", "Aquatic Multicellular", "Intelligent Aquatic", "Bioluminescent Ecosystem"],
    "Terran World": ["None", "Microbial", "Simple Multicellular", "Complex Ecosystem", "Intelligent Civilization", "Post-Singularity"],
    "Gas Giant": ["None", "Floating Gas Organisms", "Airborne Ecosystems", "Intelligent Floaters"],
    "Ice Giant": ["None", "Deep-hot Biosphere", "Ammonia-based Life"],
    "Toxic World": ["None", "Acid-resistant Microbes", "Non-carbon Biochemistry", "Corrosive Ecosystem"],
    "Crystalline World": ["None", "Mineral Life", "Resonating Crystal Networks", "Silicon-based Intelligence"],
    "Storm World": ["None", "Electrotrophic Organisms", "Storm-riding Predators"],
    "Megastructure": ["None", "Automated Drones", "Uploaded Consciousness", "Builder Race Remnants"],
    "Rogue Planet": ["None", "Subsurface Chemotrophs", "Deep Thermal Life", "Hibernating Ecosystem"],
}

FEATURES = {
    "Lava World": ["Tidal Heating", "Supervolcano Network", "Magma Oceans", "Obsidian Plains", "Core Breach Chasms"],
    "Desert World": ["Ancient Riverbeds", "Sandstone Monoliths", "Underground Aquifers", "Glass Deserts", "Dust Cyclones"],
    "Ice World": ["Cryovolcanoes", "Subsurface Oceans", "Diamond Rain", "Ice Caverns", "Frost Quakes"],
    "Ocean World": ["Floating Kelp Continents", "Deep Trench Cities", "Coral Megastructures", "Whirlpool Gates", "Bioluminescent Zones"],
    "Terran World": ["Continental Plates", "Megaflora Forests", "Spiral Mountain Ranges", "Crystal Lakes", "Aurora Belts"],
    "Gas Giant": ["Great Storm Vortex", "Metallic Hydrogen Core", "Ring System", "Floating Refineries", "Hexagonal Pole Storm"],
    "Ice Giant": ["Diamond Mantle", "Supersonic Winds", "Axial Tilt Extremes", "Ring Systems", "Magnetic Anomalies"],
    "Toxic World": ["Acid Seas", "Corrosive Rain", "Chemical Gardens", "Geyser Fields", "Poison Crystals"],
    "Crystalline World": ["Singing Crystals", "Prismatic Canyons", "Geode Caverns", "Resonating Valleys", "Fractal Formations"],
    "Storm World": ["Perpetual Hurricanes", "Lightning Networks", "Floating Debris Islands", "Pressure Zones", "Electromagnetic Vortex"],
    "Megastructure": ["Dyson Fragments", "Orbital Rings", "Planet-sized Computer", "Ancient Terraforming Engines", "Gravity Anchors"],
    "Rogue Planet": ["Geothermal Vents", "Ice Shell Protection", "Drifting Moons", "Dark Matter Accumulation", "Starless Orbit"],
}

NAME_PREFIXES = [
    "Zor", "Kla", "Xen", "Phi", "Vel", "Neb", "Ori", "Thal", "Myr", "Cryn",
    "Aeth", "Vex", "Lum", "Sol", "Nov", "Arc", "Eld", "Zyn", "Pho", "Rix",
    "Qel", "Dra", "Syn", "Axi", "Var", "Nyx", "Hex", "Tor", "Bel", "Ash",
]

NAME_SUFFIXES = [
    "ion", "ara", "os", "ith", "ax", "ul", "eon", "is", "yx", "en",
    "ius", "oth", "ium", "ala", "ora", "ith", "ux", "oth", "ine", "ar",
    "oth", "ium", "el", "yx", "os", "ar", "um", "ix", "an", "us",
]

DESCRIPTORS = [
    "Ancient", "Forgotten", "Radiant", "Cursed", "Blessed", "Silent",
    "Roaring", "Crystalline", "Drifting", "Burning", "Frozen", "Singing",
    "Shadowed", "Prismatic", "Echoing", "Pulsing", "Wandering", "Hidden",
    "Shattered", "Dreaming", "Hollow", "Screaming", "Gilded", "Twilight",
]


# ─── Seeded RNG helper ────────────────────────────────────────────────────────

def make_rng(seed_string: str) -> random.Random:
    """Create a deterministic RNG from a seed string."""
    h = hashlib.sha256(seed_string.encode()).hexdigest()
    return random.Random(int(h, 16))


# ─── Planet dataclass ─────────────────────────────────────────────────────────

@dataclass
class Planet:
    name: str
    seed: str
    planet_type: str
    star_type: str
    star_color: str
    star_temp: int
    star_mass: float
    distance_au: float
    radius_km: float
    gravity_g: float
    day_length_hours: float
    year_length_days: float
    axial_tilt_deg: float
    mean_temp_c: float
    atmosphere: str
    life_level: str
    features: List[str]
    moons: int
    ring_system: bool
    magnetic_field: str
    surface_water_pct: float
    description: str


# ─── Generator ────────────────────────────────────────────────────────────────

def weighted_choice(rng: random.Random, choices: list) -> str:
    items, weights = zip(*choices)
    total = sum(weights)
    r = rng.random() * total
    cumulative = 0
    for item, w in zip(items, weights):
        cumulative += w
        if r <= cumulative:
            return item
    return items[-1]


def generate_planet(seed: Optional[str] = None) -> Planet:
    if seed is None:
        seed = str(random.Random().randint(0, 0xFFFFFFFFFFFF))
    seed_str = str(seed)
    rng = make_rng(seed_str)

    # Name
    name = rng.choice(NAME_PREFIXES) + rng.choice(NAME_SUFFIXES)
    if rng.random() < 0.3:
        name = rng.choice(DESCRIPTORS) + " " + name
    name_id = rng.randint(1, 999)
    full_name = f"{name}-{name_id}"

    # Star
    star_type = weighted_choice(rng, [(k, v["freq"]) for k, v in STAR_TYPES.items()])
    star_data = STAR_TYPES[star_type]
    star_color = star_data["color"]
    star_temp = rng.randint(*star_data["temp_range"])
    star_mass = round(rng.uniform(*star_data["mass_range"]), 2)

    # Planet type
    planet_type = weighted_choice(rng, PLANET_TYPES)

    # Distance from star (habitable zone depends on star)
    if planet_type == "Rogue Planet":
        distance_au = round(rng.uniform(100, 10000), 1)
    else:
        # Rough habitable zone
        base_dist = math.sqrt(star_mass) * 1.0  # AU, simplified
        distance_au = round(rng.uniform(max(0.1, base_dist * 0.3), base_dist * 4.0), 2)

    # Radius
    if planet_type in ("Gas Giant",):
        radius_km = round(rng.uniform(25000, 80000), 0)
    elif planet_type in ("Ice Giant",):
        radius_km = round(rng.uniform(15000, 30000), 0)
    elif planet_type == "Megastructure":
        radius_km = round(rng.uniform(5000, 50000), 0)
    else:
        radius_km = round(rng.uniform(2000, 12000), 0)

    # Gravity (roughly proportional to mass/radius^2)
    density_factor = rng.uniform(0.5, 2.0)
    if planet_type in ("Gas Giant",):
        density_factor = rng.uniform(0.3, 0.8)
    gravity_g = round(density_factor * (radius_km / 6371), 2)

    # Orbital period (Kepler's 3rd law approximation)
    year_length_days = round(365.25 * (distance_au ** 1.5) / math.sqrt(star_mass), 1) if star_mass > 0 else 0

    # Day length
    day_length_hours = round(rng.uniform(4, 200), 1)
    if planet_type == "Rogue Planet":
        day_length_hours = round(rng.uniform(4, 48), 1)

    # Axial tilt
    axial_tilt_deg = round(rng.uniform(0, 90), 1)
    if rng.random() < 0.1:  # Some extreme tilts
        axial_tilt_deg = round(rng.uniform(90, 180), 1)

    # Temperature
    if planet_type == "Lava World":
        mean_temp_c = rng.randint(200, 1500)
    elif planet_type == "Ice World":
        mean_temp_c = rng.randint(-220, -40)
    elif planet_type == "Desert World":
        mean_temp_c = rng.randint(20, 120)
    elif planet_type == "Ocean World":
        mean_temp_c = rng.randint(-10, 60)
    elif planet_type == "Terran World":
        mean_temp_c = rng.randint(-30, 50)
    elif planet_type == "Gas Giant":
        mean_temp_c = rng.randint(-200, 200)
    elif planet_type == "Ice Giant":
        mean_temp_c = rng.randint(-220, -100)
    elif planet_type == "Toxic World":
        mean_temp_c = rng.randint(50, 400)
    elif planet_type == "Storm World":
        mean_temp_c = rng.randint(-50, 300)
    elif planet_type == "Crystalline World":
        mean_temp_c = rng.randint(-100, 100)
    elif planet_type == "Megastructure":
        mean_temp_c = rng.randint(15, 25)  # Engineered!
    elif planet_type == "Rogue Planet":
        mean_temp_c = rng.randint(-270, -50)
    else:
        mean_temp_c = rng.randint(-100, 100)

    # Adjust for distance
    if planet_type not in ("Lava World", "Megastructure", "Gas Giant", "Ice Giant"):
        temp_modifier = int(50 / max(0.1, math.sqrt(distance_au)))
        mean_temp_c += temp_modifier

    # Atmosphere
    atmo_choices = ATMOSPHERES.get(planet_type, ["Unknown"])
    atmosphere = rng.choice(atmo_choices)

    # Life
    life_choices = LIFE_LEVELS.get(planet_type, ["None"])
    life_weights = [max(1, 10 - i) for i in range(len(life_choices))]
    life_level = rng.choices(life_choices, weights=life_weights, k=1)[0]

    # Features
    feature_choices = FEATURES.get(planet_type, ["Unknown"])
    num_features = rng.randint(1, min(3, len(feature_choices)))
    features = rng.sample(feature_choices, num_features)

    # Moons
    if planet_type in ("Gas Giant", "Ice Giant"):
        moons = rng.randint(10, 80)
    elif planet_type == "Rogue Planet":
        moons = rng.randint(0, 3)
    else:
        moons = rng.randint(0, 8)

    # Rings
    ring_system = rng.random() < 0.3
    if planet_type in ("Gas Giant", "Ice Giant"):
        ring_system = rng.random() < 0.7

    # Magnetic field
    mag_options = ["None", "Weak", "Moderate", "Strong", "Extreme"]
    mag_weights = [1, 3, 5, 3, 1]
    magnetic_field = rng.choices(mag_options, weights=mag_weights, k=1)[0]

    # Surface water
    if planet_type == "Ocean World":
        surface_water_pct = round(rng.uniform(80, 100), 1)
    elif planet_type == "Ice World":
        surface_water_pct = round(rng.uniform(5, 40), 1)
    elif planet_type == "Terran World":
        surface_water_pct = round(rng.uniform(20, 80), 1)
    elif planet_type in ("Gas Giant", "Ice Giant", "Lava World", "Toxic World", "Crystalline World", "Storm World", "Megastructure", "Rogue Planet"):
        surface_water_pct = 0.0
    else:
        surface_water_pct = round(rng.uniform(0, 10), 1)

    # Description
    descriptions = _generate_description(full_name, planet_type, star_color, atmosphere, life_level, features, rng)

    return Planet(
        name=full_name,
        seed=seed_str,
        planet_type=planet_type,
        star_type=star_type,
        star_color=star_color,
        star_temp=star_temp,
        star_mass=star_mass,
        distance_au=distance_au,
        radius_km=radius_km,
        gravity_g=gravity_g,
        day_length_hours=day_length_hours,
        year_length_days=year_length_days,
        axial_tilt_deg=axial_tilt_deg,
        mean_temp_c=mean_temp_c,
        atmosphere=atmosphere,
        life_level=life_level,
        features=features,
        moons=moons,
        ring_system=ring_system,
        magnetic_field=magnetic_field,
        surface_water_pct=surface_water_pct,
        description=descriptions,
    )


def _generate_description(name, ptype, star_color, atmo, life, features, rng):
    """Generate a short lore paragraph."""
    templates = [
        f"{name} orbits a {star_color.lower()} star, veiled in {atmo.lower()}. "
        f"Known for its {', '.join(features).lower()}, this {ptype.lower()} hosts {life.lower()}.",

        f"Deep in the cosmos, {name} spins silently — a {ptype.lower()} wrapped in {atmo.lower()}. "
        f"Explorers report {', '.join(features).lower()}, and life here is classified as {life.lower()}.",

        f"The {ptype.lower()} {name} endures under the glow of a {star_color.lower()} sun. "
        f"Under skies of {atmo.lower()}, {', '.join(features).lower()} define its character. "
        f"Life assessment: {life.lower()}.",

        f"Catalogued as a {ptype.lower()}, {name} breathes {atmo.lower()}. "
        f"Its most notable features include {', '.join(features).lower()}. "
        f"The biosphere reads: {life.lower()}.",

        f"A {star_color.lower()} star illuminates the {ptype.lower()} {name}, where {atmo.lower()} "
        f"fills the atmosphere. Beneath, {', '.join(features).lower()} await discovery. "
        f"Life status: {life.lower()}.",
    ]
    return rng.choice(templates)


# ─── ASCII Globe Renderer ─────────────────────────────────────────────────────

GLOBE_CHARS = {
    "Lava World": [("≈", "red"), ("~", "yellow"), (".", "red"), (",", "orange")],
    "Desert World": [(".", "yellow"), (":", "sandy"), ("~", "brown"), ("_", "sandy")],
    "Ice World": [(".", "cyan"), ("*", "white"), ("+", "lightcyan"), ("~", "blue")],
    "Ocean World": [("≈", "blue"), ("~", "cyan"), (".", "teal"), ("_", "navy")],
    "Terran World": [("~", "blue"), ("^", "green"), (".", "green"), (",", "brown")],
    "Gas Giant": [("≡", "orange"), ("≈", "yellow"), ("~", "brown"), ("-", "red")],
    "Ice Giant": [(".", "lightblue"), ("≈", "cyan"), ("~", "blue"), ("-", "white")],
    "Toxic World": [("≈", "green"), (".", "yellow"), (":", "lime"), ("~", "olive")],
    "Crystalline World": [("*", "magenta"), (".", "purple"), ("+", "pink"), (":", "violet")],
    "Storm World": [("#", "yellow"), ("≡", "white"), ("~", "gray"), (".", "darkgray")],
    "Megastructure": [("□", "cyan"), ("▪", "blue"), ("╗", "gray"), ("═", "white")],
    "Rogue Planet": [(".", "darkgray"), (":", "gray"), ("~", "dim"), ("*", "blue")],
}

ANSI_COLORS = {
    "red": "\033[31m", "yellow": "\033[33m", "orange": "\033[38;5;208m",
    "cyan": "\033[36m", "white": "\033[37m", "lightcyan": "\033[96m",
    "blue": "\033[34m", "green": "\033[32m", "brown": "\033[38;5;130m",
    "sandy": "\033[38;5;180m", "teal": "\033[38;5;30m", "navy": "\033[38;5;17m",
    "magenta": "\033[35m", "purple": "\033[38;5;93m", "pink": "\033[38;5;213m",
    "violet": "\033[38;5;99m", "gray": "\033[90m", "darkgray": "\033[38;5;240m",
    "dim": "\033[38;5;242m", "lime": "\033[38;5;118m", "olive": "\033[38;5;100m",
    "lightblue": "\033[94m",
}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def render_globe(planet: Planet, width: int = 40, height: int = 20, use_color: bool = True) -> str:
    """Render an ASCII art globe for the planet."""
    rng = make_rng(planet.seed + "_globe")
    chars_config = GLOBE_CHARS.get(planet.planet_type, [(".", "white"), (":", "gray"), ("~", "blue")])

    # Add surface detail based on features
    if planet.ring_system:
        chars_config = chars_config + [("-", "white"), ("=", "gray")]

    lines = []
    cx, cy = width // 2, height // 2
    rx, ry = width // 2 - 1, height // 2 - 1

    # Generate continent/pattern map using noise-like approach
    pattern = {}
    for y in range(height):
        for x in range(width):
            dx = (x - cx) / rx if rx > 0 else 0
            dy = (y - cy) / ry if ry > 0 else 0
            dist2 = dx * dx + dy * dy
            if dist2 <= 1.0:
                # Simple value noise
                val = math.sin(x * 0.4 + planet.mean_temp_c * 0.01) * \
                      math.cos(y * 0.3 + planet.axial_tilt_deg * 0.02) + \
                      math.sin((x + y) * 0.2) * 0.5 + \
                      rng.uniform(-0.2, 0.2)
                pattern[(x, y)] = val

    # Latitude bands (for gas giants, add horizontal bands)
    for y in range(height):
        row = ""
        for x in range(width):
            dx = (x - cx) / rx if rx > 0 else 0
            dy = (y - cy) / ry if ry > 0 else 0
            dist2 = dx * dx + dy * dy

            if dist2 > 1.0:
                # Check for ring system
                if planet.ring_system and abs(dy) < 0.15 and dist2 > 1.0 and dist2 < 1.8:
                    ring_char = rng.choice(["-", "=", "≈", "~"])
                    if use_color:
                        row += f"\033[38;5;250m{ring_char}{RESET}"
                    else:
                        row += ring_char
                else:
                    row += " "
                continue

            # On the globe surface
            val = pattern.get((x, y), 0)

            # Atmosphere edge darkening
            edge_factor = 1.0 - dist2

            # For gas giants, add banding
            if planet.planet_type in ("Gas Giant", "Ice Giant"):
                band = math.sin(y * 0.8 + rng.uniform(-1, 1))
                val += band * 0.5

            # Map val to character
            char_idx = int((val + 2) / 4 * len(chars_config)) % len(chars_config)
            char, color = chars_config[char_idx]

            # Ocean worlds: surface is mostly water
            if planet.planet_type == "Ocean World" and val < 0.3:
                char, color = "≈", "blue"
            elif planet.planet_type == "Terran World":
                if val < -0.2:
                    char, color = "~", "blue"
                elif val < 0.1:
                    char, color = ".", "green"
                elif val < 0.4:
                    char, color = "^", "green"
                else:
                    char, color = ",", "brown"

            if use_color:
                ansi = ANSI_COLORS.get(color, "\033[37m")
                row += f"{ansi}{char}{RESET}"
            else:
                row += char

        lines.append(row)

    return "\n".join(lines)


# ─── Display ───────────────────────────────────────────────────────────────────

def display_planet(planet: Planet, show_globe: bool = True, use_color: bool = True, globe_size: int = 40):
    """Pretty-print a planet's info card."""
    R = RESET
    B = BOLD if use_color else ""
    D = DIM if use_color else ""

    # Color-code planet type
    type_colors = {
        "Lava World": "\033[38;5;202m",
        "Desert World": "\033[38;5;180m",
        "Ice World": "\033[36m",
        "Ocean World": "\033[34m",
        "Terran World": "\033[32m",
        "Gas Giant": "\033[38;5;208m",
        "Ice Giant": "\033[94m",
        "Toxic World": "\033[35m",
        "Crystalline World": "\033[95m",
        "Storm World": "\033[38;5;226m",
        "Megastructure": "\033[96m",
        "Rogue Planet": "\033[90m",
    }
    tc = type_colors.get(planet.planet_type, "\033[37m") if use_color else ""

    w = globe_size + 2  # Card width based on globe size

    output = []
    output.append(f"{tc}{'━' * w}{R}")
    output.append(f"{B}  🪐 {planet.name}{R}")
    output.append(f"{D}  Seed: {planet.seed}{R}")
    output.append(f"{tc}{'─' * w}{R}")
    output.append(f"  {B}Type:{R}            {tc}{planet.planet_type}{R}")
    output.append(f"  {B}Star:{R}            {planet.star_type}-class ({planet.star_color}, {planet.star_temp:,} K, {planet.star_mass} M☉)")
    output.append(f"  {B}Distance:{R}        {planet.distance_au} AU")
    output.append(f"  {B}Radius:{R}          {planet.radius_km:,.0f} km")
    output.append(f"  {B}Gravity:{R}         {planet.gravity_g}g")
    output.append(f"  {B}Day Length:{R}      {planet.day_length_hours} hours")
    output.append(f"  {B}Year Length:{R}     {planet.year_length_days:,.1f} days")
    output.append(f"  {B}Axial Tilt:{R}      {planet.axial_tilt_deg}°")
    output.append(f"  {B}Mean Temp:{R}       {planet.mean_temp_c}°C")
    output.append(f"  {B}Atmosphere:{R}      {planet.atmosphere}")
    output.append(f"  {B}Surface Water:{R}   {planet.surface_water_pct}%")
    output.append(f"  {B}Magnetic Field:{R}   {planet.magnetic_field}")
    output.append(f"  {B}Moons:{R}           {planet.moons}")
    ring_str = "Yes" if planet.ring_system else "No"
    output.append(f"  {B}Ring System:{R}     {ring_str}")
    output.append(f"  {B}Life Level:{R}      {planet.life_level}")
    output.append(f"  {B}Features:{R}        {', '.join(planet.features)}")
    output.append(f"{tc}{'─' * w}{R}")
    output.append(f"  {D}{planet.description}{R}")

    if show_globe:
        globe_height = max(12, globe_size // 2)
        output.append(f"{tc}{'─' * w}{R}")
        output.append(f"{B}  Globe View:{R}")
        output.append("")
        globe = render_globe(planet, width=globe_size, height=globe_height, use_color=use_color)
        for line in globe.split("\n"):
            output.append(f"  {line}")
        output.append("")

    output.append(f"{tc}{'━' * w}{R}")

    return "\n".join(output)


# ─── Catalog export ───────────────────────────────────────────────────────────

def export_text(planet: Planet) -> str:
    """Export planet as plain text (no ANSI codes)."""
    lines = [
        f"Planet: {planet.name}",
        f"Seed: {planet.seed}",
        f"Type: {planet.planet_type}",
        f"Star: {planet.star_type}-class ({planet.star_color}, {planet.star_temp} K, {planet.star_mass} M☉)",
        f"Distance: {planet.distance_au} AU",
        f"Radius: {planet.radius_km:,.0f} km",
        f"Gravity: {planet.gravity_g}g",
        f"Day Length: {planet.day_length_hours} hours",
        f"Year Length: {planet.year_length_days:,.1f} days",
        f"Axial Tilt: {planet.axial_tilt_deg}°",
        f"Mean Temp: {planet.mean_temp_c}°C",
        f"Atmosphere: {planet.atmosphere}",
        f"Surface Water: {planet.surface_water_pct}%",
        f"Magnetic Field: {planet.magnetic_field}",
        f"Moons: {planet.moons}",
        f"Ring System: {'Yes' if planet.ring_system else 'No'}",
        f"Life Level: {planet.life_level}",
        f"Features: {', '.join(planet.features)}",
        f"Description: {planet.description}",
    ]
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🌌 Procedural Planet Generator — create fictional worlds!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python planet_gen.py                    # Random planet
  python planet_gen.py --seed 42          # Reproducible planet
  python planet_gen.py --count 5           # Generate 5 planets
  python planet_gen.py --no-globe          # Skip the ASCII globe
  python planet_gen.py --no-color          # No ANSI colors
  python planet_gen.py --save catalog.txt  # Save to file
  python planet_gen.py --size 50           # Larger globe
        """
    )
    parser.add_argument("--seed", type=str, default=None, help="Seed for reproducible generation")
    parser.add_argument("--count", "-n", type=int, default=1, help="Number of planets to generate")
    parser.add_argument("--no-globe", action="store_true", help="Don't render the ASCII globe")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    parser.add_argument("--save", type=str, default=None, help="Save output to file")
    parser.add_argument("--size", type=int, default=40, help="Globe width (default: 40)")

    args = parser.parse_args()

    use_color = not args.no_color
    planets = []

    for i in range(args.count):
        if args.count == 1:
            seed = args.seed
        else:
            if args.seed:
                # Derive seeds for multiple planets
                seed = str(int(hashlib.sha256(f"{args.seed}_{i}".encode()).hexdigest(), 16))
            else:
                seed = None

        planet = generate_planet(seed)
        planets.append(planet)

        output = display_planet(planet, show_globe=not args.no_globe, use_color=use_color, globe_size=args.size)
        if args.count > 1:
            print(f"\n{'═' * 50}")
            print(f"  PLANET {i + 1} OF {args.count}")
            print(f"{'═' * 50}")
        print(output)

    if args.save:
        with open(args.save, "w") as f:
            for planet in planets:
                f.write(export_text(planet) + "\n")
                if not args.no_globe:
                    globe = render_globe(planet, width=args.size, height=max(12, args.size // 2), use_color=False)
                    f.write("\n" + globe + "\n")
                f.write("\n" + "=" * 50 + "\n\n")
        print(f"\n💾 Saved {len(planets)} planet(s) to {args.save}")


if __name__ == "__main__":
    main()