#!/usr/bin/env python3
"""
Terminal Cocktail Mixologist — Procedural cocktail recipe generator.

Generates unique, plausible cocktail recipes using spirit/liqueur/mixer/garnish
combinations, names them with creative procedural names, and renders beautiful
ASCII art menus and drink visualizations.
"""

import random
import argparse
import sys
import os
from dataclasses import dataclass, field
from typing import Optional

# ─── Ingredient Databases ───────────────────────────────────────────────────

SPIRITS = [
    ("gin", "London Dry Gin", 40, "herbal, juniper, citrus"),
    ("vodka", "Premium Vodka", 40, "neutral, clean"),
    ("rum_light", "Light Rum", 35, "sweet, sugarcane"),
    ("rum_dark", "Dark Rum", 40, "molasses, caramel, oak"),
    ("whiskey_bourbon", "Bourbon Whiskey", 40, "vanilla, caramel, corn"),
    ("whiskey_rye", "Rye Whiskey", 40, "spicy, peppery, grain"),
    ("whiskey_scotch", "Scotch Whisky", 43, "smoky, peat, malt"),
    ("tequila_blanco", "Blanco Tequila", 38, "agave, pepper, citrus"),
    ("tequila_reposado", "Reposado Tequila", 38, "oak, agave, vanilla"),
    ("mezcal", "Mezcal", 45, "smoky, earthy, roasted agave"),
    ("brandy", "Cognac", 40, "grape, oak, dried fruit"),
    ("cachaca", "Cachaça", 38, "sugarcane, grassy, tropical"),
]

LIQUEURS = [
    ("triple_sec", "Triple Sec", 30, "orange, sweet"),
    ("campari", "Campari", 25, "bitter, herbal, red"),
    ("vermouth_sweet", "Sweet Vermouth", 16, "botanical, sweet wine"),
    ("vermouth_dry", "Dry Vermouth", 16, "herbal, dry wine"),
    ("amaretto", "Amaretto", 28, "almond, sweet"),
    ("kahlua", "Kahlúa", 20, "coffee, vanilla"),
    ("chartreuse_green", "Green Chartreuse", 55, "herbal, mint, anise"),
    ("chartreuse_yellow", "Yellow Chartreuse", 40, "honey, saffron, herbal"),
    ("cointreau", "Cointreau", 40, "orange, balanced"),
    ("drambuie", "Drambuie", 40, "honey, whisky, herbs"),
    ("chambord", "Chambord", 16, "blackberry, raspberry"),
    ("aperol", "Aperol", 11, "bitter orange, rhubarb"),
    ("blue_curacao", "Blue Curaçao", 21, "orange, sweet, blue"),
    ("crème_de_cassis", "Crème de Cassis", 15, "blackcurrant"),
    ("maraschino", "Maraschino Liqueur", 32, "cherry, almond"),
    ("elderflower", "St-Germain", 20, "elderflower, lychee, pear"),
    ("green_chartreuse", "Green Chartreuse", 55, "mint, anise, herbal"),
    ("grand_marnier", "Grand Marnier", 40, "orange, cognac"),
]

MIXERS = [
    ("lime_juice", "Fresh Lime Juice", 0, "tart, citrus"),
    ("lemon_juice", "Fresh Lemon Juice", 0, "tart, bright"),
    ("orange_juice", "Fresh Orange Juice", 0, "sweet, citrus"),
    ("grapefruit_juice", "Fresh Grapefruit Juice", 0, "bitter, tart"),
    ("cranberry_juice", "Cranberry Juice", 0, "tart, berry"),
    ("pineapple_juice", "Pineapple Juice", 0, "sweet, tropical"),
    ("simple_syrup", "Simple Syrup", 0, "sweet, neutral"),
    ("grenadine", "Grenadine", 0, "sweet, pomegranate, red"),
    ("honey_syrup", "Honey Syrup", 0, "sweet, floral"),
    ("agave_syrup", "Agave Syrup", 0, "sweet, mild"),
    ("club_soda", "Club Soda", 0, "carbonated, neutral"),
    ("tonic_water", "Tonic Water", 0, "bitter, carbonated"),
    ("ginger_beer", "Ginger Beer", 0, "spicy, ginger, carbonated"),
    ("cola", "Cola", 0, "sweet, caramel, carbonated"),
    ("cream", "Heavy Cream", 0, "rich, dairy"),
    ("coconut_cream", "Coconut Cream", 0, "rich, coconut"),
    ("egg_white", "Egg White", 0, "frothy, protein"),
    ("hot_sauce", "Hot Sauce", 0, "spicy, vinegar"),
    ("bitters_aromatic", "Aromatic Bitters", 0, "complex, spice"),
    ("bitters_orange", "Orange Bitters", 0, "citrus, aromatic"),
    ("bitters_peach", "Peach Bitters", 0, "stone fruit, aromatic"),
    ("soda_water", "Soda Water", 0, "carbonated, neutral"),
    ("tomato_juice", "Tomato Juice", 0, "savory, umami"),
    (" Worcestershire", "Worcestershire Sauce", 0, "umami, savory"),
    ("celery_salt", "Celery Salt", 0, "savory, celery"),
    ("sugar_rim", "Sugar Rim", 0, "sweet, decorative"),
    ("salt_rim", "Salt Rim", 0, "salty, savory"),
]

GARNISHES = [
    ("lime_wheel", "Lime Wheel"),
    ("lemon_twist", "Lemon Twist"),
    ("orange_peel", "Orange Peel"),
    ("cherry", "Luxardo Cherry"),
    ("olive", "Green Olive"),
    ("mint_sprig", "Fresh Mint Sprig"),
    ("rosemary", "Rosemary Sprig"),
    ("basil", "Fresh Basil Leaf"),
    ("cucumber_ribbon", "Cucumber Ribbon"),
    ("berry_skewer", "Berry Skewer"),
    ("pineapple_wedge", "Pineapple Wedge"),
    ("grapefruit_slice", "Grapefruit Slice"),
    ("cinnamon_stick", "Cinnamon Stick"),
    ("nutmeg", "Fresh Grated Nutmeg"),
    ("coffee_beans", "Three Coffee Beans"),
    ("star_anise", "Star Anise"),
    ("edible_flower", "Edible Flower"),
    ("celery_stalk", "Celery Stalk"),
    ("jalapeno_slice", "Jalapeño Slice"),
    ("candied_ginger", "Candied Ginger"),
    ("pepper", "Cracked Black Pepper"),
]

GLASSWARE = [
    ("coupe", "Coupe Glass", "elegant V-shaped bowl"),
    ("rocks", "Rocks Glass", "short, wide tumbler"),
    ("highball", "Highball Glass", "tall, slim tumbler"),
    ("martini", "Martini Glass", "iconic stemmed cone"),
    ("collins", "Collins Glass", "tall, narrow tumbler"),
    ("snifter", "Snifter Glass", "round bowl, short stem"),
    ("hurricane", "Hurricane Glass", "curvy, tall bowl"),
    ("nick_nora", "Nick & Nora Glass", "small stemmed coupe"),
    ("copper_mug", "Copper Mug", "metallic Moscow Mule mug"),
    ("tiki_mug", "Tiki Mug", "ceramic tropical vessel"),
    ("flute", "Champagne Flute", "tall, narrow, stemmed"),
    ("wine", "Wine Glass", "standard stemmed glass"),
    ("mason_jar", "Mason Jar", "rustic glass jar"),
    ("punch_cup", "Punch Cup", "small, handled cup"),
]

ICE_TYPES = [
    ("none", "No Ice (Neat)"),
    ("cube", "Standard Cubes"),
    ("crushed", "Crushed Ice"),
    ("large_cube", "Single Large Cube"),
    ("sphere", "Ice Sphere"),
    ("shaved", "Shaved Ice"),
]

METHODS = [
    ("shaken", "Shaken", "Vigorously shake with ice, strain"),
    ("stirred", "Stirred", "Gently stir with ice, strain"),
    ("built", "Built", "Assemble directly in serving glass"),
    ("blended", "Blended", "Blend ingredients with ice"),
    ("muddled", "Muddled", "Muddle ingredients, then shake"),
    ("layered", "Layered", "Carefully float layers on top"),
    ("poured", "Poured", "Simply pour over ice"),
]

# ─── Naming Components ──────────────────────────────────────────────────────

ADJECTIVES = [
    "Crimson", "Velvet", "Golden", "Silver", "Ebon", "Opal",
    "Midnight", "Twilight", "Dawn", "Aurora", "Ember", "Frost",
    "Phantom", "Celestial", "Mystic", "Wandering", "Lost", "Secret",
    "Silent", "Electric", "Wicked", "Humble", "Grand", "Royal",
    "Rustic", "Cosmic", "Atomic", "Wild", "Gentle", "Fierce",
    "Lunar", "Solar", "Stellar", "Forgotten", "Ancient", "Neon",
    "Dusky", "Amber", "Ivory", "Copper", "Iron", "Jade",
    "Scarlet", "Indigo", "Violet", "Saffron", "Cobalt", "Obsidian",
]

NOUNS = [
    "Fox", "Sparrow", "Serpent", "Lotus", "Orchid", "Compass",
    "Lantern", "Tempest", "Mirage", "Eclipse", "Phoenix", "Dragon",
    "Rose", "Thistle", "Dagger", "Crown", "Labyrinth", "Oracle",
    "Nightingale", "Raven", "Falcon", "Tiger", "Panther", "Viper",
    "Jasmine", "Sage", "Cedar", "Coral", "Amber", "Opal",
    "Nebula", "Comet", "Prism", "Hourglass", "Meridian", "Zenith",
    "Siren", "Valkyrie", "Muse", "Whisper", "Shadow", "Flame",
    "Honeybee", "Monarch", "Alchemist", "Pilot", "Captain", "Wanderer",
]

NAME_STYLES = [
    # "The Adjective Noun"
    lambda adj, noun: f"The {adj} {noun}",
    # "Noun's Adjective"
    lambda adj, noun: f"{noun}'s {adj}",
    # "Adjective Noun"
    lambda adj, noun: f"{adj} {noun}",
    # "Noun & Noun" (second noun)
    lambda adj, noun: f"{noun} & {random.choice(NOUNS)}",
    # "The Noun of Adjective"
    lambda adj, noun: f"The {noun} of {adj}",
    # "Noun's Kiss"
    lambda adj, noun: f"{noun}'s Kiss",
    # "Adjective Noun No. X"
    lambda adj, noun: f"{adj} {noun} No. {random.randint(2, 9)}",
    # "Noun on Fire"
    lambda adj, noun: f"{noun} on Fire",
    # "Last of the Noun"
    lambda adj, noun: f"Last of the {noun}",
    # "Adjective Noun Spritz"
    lambda adj, noun: f"{adj} {noun} Spritz",
    # "Noun's Revenge"
    lambda adj, noun: f"{noun}'s Revenge",
    # "Dear Adjective Noun"
    lambda adj, noun: f"Dear {adj} {noun}",
]

# ─── Recipe Compatibility Rules ──────────────────────────────────────────────

# Flavor profiles that work well together
HARMONIOUS_PAIRS = {
    "herbal": ["citrus", "sweet", "bitter"],
    "sweet": ["bitter", "tart", "spicy"],
    "tart": ["sweet", "herbal", "tropical"],
    "bitter": ["sweet", "herbal", "citrus"],
    "smoky": ["sweet", "tropical", "spicy"],
    "tropical": ["sweet", "tart", "spicy"],
    "spicy": ["sweet", "citrus", "tropical"],
    "citrus": ["herbal", "sweet", "bitter"],
    "vanilla": ["sweet", "coffee", "fruit"],
    "coffee": ["sweet", "vanilla", "cream"],
}

FLAVOR_MAP = {
    "herbal": "herbal", "juniper": "herbal", "mint": "herbal", "anise": "herbal", "botanical": "herbal",
    "sweet": "sweet", "honey": "sweet", "sugar": "sweet", "agave": "sweet", "vanilla": "sweet",
    "tart": "tart", "sour": "tart", "lime": "tart", "lemon": "tart", "grapefruit": "tart",
    "bitter": "bitter", "campari": "bitter", "tonic": "bitter",
    "smoky": "smoky", "peat": "smoky", "roasted": "smoky",
    "tropical": "tropical", "pineapple": "tropical", "coconut": "tropical", "passion": "tropical",
    "spicy": "spicy", "ginger": "spicy", "pepper": "spicy", "hot": "spicy",
    "citrus": "citrus", "orange": "citrus",
    "vanilla": "vanilla", "caramel": "vanilla",
    "coffee": "coffee",
    "cream": "cream", "dairy": "cream",
    "fruit": "fruit", "berry": "fruit", "cherry": "fruit", "raspberry": "fruit",
    "oak": "oak", "aged": "oak",
}


def extract_flavors(desc: str) -> set:
    """Extract flavor categories from an ingredient description."""
    flavors = set()
    desc_lower = desc.lower()
    for keyword, category in FLAVOR_MAP.items():
        if keyword in desc_lower:
            flavors.add(category)
    return flavors


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class Ingredient:
    key: str
    name: str
    abv: float  # Alcohol by volume
    flavor_desc: str
    amount_oz: float  # Amount in ounces
    role: str  # "base", "liqueur", "mixer", "bitters", "garnish"

    @property
    def flavors(self) -> set:
        return extract_flavors(self.flavor_desc)


@dataclass
class Cocktail:
    name: str
    ingredients: list
    method: tuple  # (key, name, description)
    glass: tuple   # (key, name, description)
    ice: tuple     # (key, name)
    garnish: tuple  # (garnish_key, garnish_name)
    story: str = ""
    flavor_profile: str = ""
    difficulty: str = ""
    abv: float = 0.0
    total_oz: float = 0.0

    def compute_stats(self):
        """Compute ABV and total volume."""
        total_alcohol_oz = 0.0
        total_volume = 0.0
        for ing in self.ingredients:
            total_alcohol_oz += ing.amount_oz * (ing.abv / 100.0)
            total_volume += ing.amount_oz
        self.total_oz = total_volume
        self.abv = round((total_alcohol_oz / total_volume * 100), 1) if total_volume > 0 else 0


# ─── Generator Logic ────────────────────────────────────────────────────────

STYLE_PROFILES = {
    "classic": {
        "bases_per": 1, "liqueurs_per": (0, 1), "mixers_per": (1, 2),
        "bitters_per": (0, 1), "garnish_per": 1,
        "method_weights": {"stirred": 3, "shaken": 3, "built": 2, "muddled": 1, "layered": 0, "blended": 0, "poured": 1},
        "glass_weights": {"coupe": 3, "rocks": 3, "martini": 2, "nick_nora": 2, "highball": 1, "collins": 1},
    },
    "tropical": {
        "bases_per": 1, "liqueurs_per": (0, 1), "mixers_per": (2, 3),
        "bitters_per": (0, 0), "garnish_per": 1,
        "method_weights": {"shaken": 4, "blended": 3, "built": 1, "muddled": 1, "stirred": 0, "layered": 0, "poured": 1},
        "glass_weights": {"tiki_mug": 4, "hurricane": 3, "highball": 2, "mason_jar": 1, "collins": 1},
    },
    "strong": {
        "bases_per": 1, "liqueurs_per": (0, 1), "mixers_per": (0, 1),
        "bitters_per": (1, 2), "garnish_per": 1,
        "method_weights": {"stirred": 4, "built": 2, "poured": 1, "shaken": 0, "blended": 0, "muddled": 0, "layered": 0},
        "glass_weights": {"rocks": 4, "snifter": 3, "coupe": 1, "martini": 1},
    },
    "fizzy": {
        "bases_per": 1, "liqueurs_per": (0, 1), "mixers_per": (2, 3),
        "bitters_per": (0, 1), "garnish_per": 1,
        "method_weights": {"built": 4, "poured": 3, "shaken": 1, "stirred": 0, "blended": 0, "muddled": 1, "layered": 0},
        "glass_weights": {"highball": 4, "collins": 3, "copper_mug": 2, "hurricane": 1},
    },
    "dessert": {
        "bases_per": 1, "liqueurs_per": (1, 2), "mixers_per": (1, 2),
        "bitters_per": (0, 0), "garnish_per": 1,
        "method_weights": {"shaken": 3, "blended": 3, "built": 1, "muddled": 0, "stirred": 0, "layered": 1, "poured": 1},
        "glass_weights": {"coupe": 3, "martini": 2, "hurricane": 1, "mason_jar": 1},
    },
    "bitter": {
        "bases_per": 1, "liqueurs_per": (1, 2), "mixers_per": (0, 1),
        "bitters_per": (1, 2), "garnish_per": 1,
        "method_weights": {"stirred": 3, "built": 2, "shaken": 1, "poured": 1, "blended": 0, "muddled": 0, "layered": 0},
        "glass_weights": {"rocks": 3, "coupe": 2, "nick_nora": 2, "martini": 1},
    },
    "sour": {
        "bases_per": 1, "liqueurs_per": (0, 1), "mixers_per": (2, 3),
        "bitters_per": (0, 1), "garnish_per": 1,
        "method_weights": {"shaken": 5, "muddled": 2, "built": 0, "stirred": 0, "blended": 0, "layered": 0, "poured": 0},
        "glass_weights": {"coupe": 3, "rocks": 2, "nick_nora": 2, "martini": 1},
    },
}


def weighted_choice(items, weights):
    """Choose an item based on weight dict."""
    keys = list(items)
    w = [weights.get(k, 1) for k in keys]
    return random.choices(keys, weights=w, k=1)[0]


def generate_cocktail(style: str = None) -> Cocktail:
    """Generate a complete cocktail recipe."""
    if style is None:
        style = random.choice(list(STYLE_PROFILES.keys()))
    profile = STYLE_PROFILES[style]

    # Choose base spirit
    base = random.choice(SPIRITS)
    base_ing = Ingredient(base[0], base[1], base[2], base[3],
                          round(random.uniform(1.5, 2.5), 1), "base")
    base_flavors = base_ing.flavors

    # Choose liqueurs
    num_liqueurs = random.randint(*profile["liqueurs_per"])
    liqueur_ings = []
    used_keys = {base[0]}
    for _ in range(num_liqueurs):
        available = [l for l in LIQUEURS if l[0] not in used_keys]
        if not available:
            break
        liq = random.choice(available)
        used_keys.add(liq[0])
        amount = round(random.uniform(0.25, 1.0), 2)
        liqueur_ings.append(Ingredient(liq[0], liq[1], liq[2], liq[3], amount, "liqueur"))

    # Choose mixers
    num_mixers = random.randint(*profile["mixers_per"])
    mixer_ings = []
    # Prefer harmonious mixers
    for _ in range(num_mixers):
        available = [m for m in MIXERS if m[0] not in used_keys]
        if not available:
            break
        # Try to find harmonious mixers
        preferred = []
        for m in available:
            m_flavors = extract_flavors(m[3])
            for bf in base_flavors:
                if bf in HARMONIOUS_PAIRS:
                    for mf in m_flavors:
                        if mf in HARMONIOUS_PAIRS.get(bf, []):
                            preferred.append(m)
                            break
        if preferred and random.random() < 0.7:
            mixer = random.choice(preferred)
        else:
            mixer = random.choice(available)
        used_keys.add(mixer[0])
        amount = round(random.uniform(0.25, 1.5), 2)
        mixer_ings.append(Ingredient(mixer[0], mixer[1], mixer[2], mixer[3], amount, "mixer"))

    # Choose bitters
    num_bitters = random.randint(*profile["bitters_per"])
    bitter_ings = []
    bitters_pool = [m for m in MIXERS if m[0].startswith("bitters_")]
    for _ in range(num_bitters):
        available = [b for b in bitters_pool if b[0] not in used_keys]
        if not available:
            break
        bit = random.choice(available)
        used_keys.add(bit[0])
        bitter_ings.append(Ingredient(bit[0], bit[1], bit[2], bit[3], 1, "bitters"))

    # Choose garnish
    garnish = random.choice(GARNISHES)

    # Choose method, glass, ice
    method_key = weighted_choice([m[0] for m in METHODS], profile["method_weights"])
    method_data = next(m for m in METHODS if m[0] == method_key)

    glass_key = weighted_choice([g[0] for g in GLASSWARE], profile["glass_weights"])
    glass_data = next(g for g in GLASSWARE if g[0] == glass_key)

    # Ice depends on method and glass
    if method_key in ("stirred", "shaken", "muddled"):
        ice_options = ["cube", "large_cube", "sphere"]
    elif method_key == "blended":
        ice_options = ["crushed", "shaved"]
    elif method_key == "built":
        ice_options = ["cube", "crushed", "large_cube"]
    else:
        ice_options = ["none", "cube"]
    ice_key = random.choice(ice_options)
    ice_data = next(i for i in ICE_TYPES if i[0] == ice_key)

    # Combine all ingredients
    all_ingredients = [base_ing] + liqueur_ings + mixer_ings + bitter_ings

    # Generate name
    name = random.choice(NAME_STYLES)(
        random.choice(ADJECTIVES), random.choice(NOUNS)
    )

    # Build cocktail
    cocktail = Cocktail(
        name=name,
        ingredients=all_ingredients,
        method=method_data,
        glass=glass_data,
        ice=ice_data,
        garnish=garnish,
    )
    cocktail.compute_stats()

    # Generate flavor profile description
    all_flavors = set()
    for ing in all_ingredients:
        all_flavors |= ing.flavors
    flavor_words = list(all_flavors)
    random.shuffle(flavor_words)
    if len(flavor_words) >= 3:
        cocktail.flavor_profile = f"{', '.join(flavor_words[:2])} and {flavor_words[2]}"
    elif len(flavor_words) == 2:
        cocktail.flavor_profile = f"{flavor_words[0]} and {flavor_words[1]}"
    elif flavor_words:
        cocktail.flavor_profile = flavor_words[0]

    # Generate story
    cocktail.story = generate_story(cocktail, style)

    # Difficulty
    if method_key in ("layered", "blended") or len(all_ingredients) > 5:
        cocktail.difficulty = "Advanced"
    elif method_key in ("muddled", "shaken") or len(all_ingredients) > 3:
        cocktail.difficulty = "Intermediate"
    else:
        cocktail.difficulty = "Easy"

    return cocktail


STORY_TEMPLATES = [
    "Legend has it this drink was first mixed at {venue} by a {bartender} who believed that {belief}.",
    "Born in the {era} at {venue}, this cocktail carries the spirit of {vibe} — {trait}.",
    "A {bartender} at {venue} created this in a moment of {mood}, combining {trait} with {trait2}.",
    "This cocktail emerged from the {era} speakeasy scene, where {bartender} would serve it to {patrons}.",
    "Inspired by {inspiration}, this drink captures the essence of {vibe} in every sip.",
    "The story goes that {bartender} invented this at {venue} when {event}, and it's been a {adj} favorite ever since.",
]


def generate_story(cocktail: Cocktail, style: str) -> str:
    venues = ["The Midnight Lounge", "The Velvet Curtain", "a Havana cantina", "a Parisian café",
              "The Copper Lantern", "a Tokyo cocktail den", "a New York speakeasy",
              "The Wandering Albatross", "a rooftop bar in Barcelona", "The Green Parrot"]
    bartenders = ["an enigmatic bartender", "a retired sailor", "a world-weary mixologist",
                   "a poet turned barkeep", "a mysterious stranger", "a jazz pianist",
                   "a traveling merchant", "a reclusive alchemist"]
    beliefs = ["every drink tells a story", "spirits speak to those who listen",
                "the perfect balance is found, not made", "ice has memory",
                "garnish is destiny", "shaking is dancing with the drink"]
    eras = ["1920s", "1950s", "1970s", "1990s", "post-war", "golden age of cocktails"]
    vibes = ["rebellion", "elegance", "adventure", "nostalgia", "celebration", "intrigue"]
    moods = ["inspiration", "desperation", "quiet contemplation", "joyful experimentation", "serendipity"]
    traits = ["boldness", "subtlety", "complexity", "warmth", "surprise", "depth"]
    patrons = ["wanderers and dreamers", "artists and writers", "diplomats and spies",
               "star-crossed lovers", "midnight philosophers"]
    inspirations = ["a sunset over the Mediterranean", "jazz echoing through rain-soaked streets",
                    "a garden in full bloom", "the Northern Lights", "a forgotten recipe found in an old book"]
    events = ["the clock struck midnight", "the last bottle was nearly empty",
              "a patron challenged them to create something new", "the power went out and only candles lit the bar"]
    adjs = ["cult", "beloved", "legendary", "cherished", "secret"]

    template = random.choice(STORY_TEMPLATES)
    return template.format(
        venue=random.choice(venues),
        bartender=random.choice(bartenders),
        belief=random.choice(beliefs),
        era=random.choice(eras),
        vibe=random.choice(vibes),
        trait=random.choice(traits),
        trait2=random.choice([t for t in traits if t != random.choice(traits)]),
        mood=random.choice(moods),
        patrons=random.choice(patrons),
        inspiration=random.choice(inspirations),
        event=random.choice(events),
        adj=random.choice(adjs),
    )


# ─── ASCII Art Rendering ────────────────────────────────────────────────────

def render_glass_ascii(glass_key: str) -> str:
    """Return ASCII art for each glass type."""
    glasses = {
        "coupe": r"""
        .──────.
       /        \
      /          \
     /            \
    │              │
     \            /
      `──.    .──'
          \  /
           \/
           ||
           ||
         ─────
""",
        "rocks": r"""
      ┌──────────┐
      │          │
      │          │
      │          │
      │          │
      └──────────┘
""",
        "highball": r"""
      ┌──────────┐
      │          │
      │          │
      │          │
      │          │
      │          │
      │          │
      │          │
      └──────────┘
""",
        "martini": r"""
          /\
         /  \
        /    \
       /      \
      /        \
     /          \
    │            │
     \          /
      \        /
       \──────/
         ||
         ||
       ─────
""",
        "collins": r"""
      ┌──────────┐
      │          │
      │          │
      │          │
      │          │
      │          │
      │          │
      │          │
      │          │
      │          │
      └──────────┘
""",
        "snifter": r"""
        .──────.
       /        \
      /          \
     │            │
      \          /
       │        │
       │        │
       └────────┘
""",
        "hurricane": r"""
        .──────.
       /        \
      /          \
     │            │
     │            │
      \          /
       │        │
       │        │
       │        │
       └────────┘
""",
        "nick_nora": r"""
        .──────.
       /        \
      /          \
     │            │
      \          /
       `──.  .──'
           \/
           ||
         ─────
""",
        "copper_mug": r"""
      ┌──────────┐ ╮
      │          │ │
      │          │ │
      │          │ │
      │          │ ╯
      └──────────┘
""",
        "tiki_mug": r"""
      ╭──────────╮
      │ ╭──────╮ │
      │ │ ○  ○ │ │
      │ │  ─   │ │
      │ ╰──────╯ │
      │          │
      └──────────┘
""",
        "flute": r"""
       ┌────┐
       │    │
       │    │
       │    │
       │    │
       │    │
       │    │
       │    │
       └────┘
         ||
         ||
       ─────
""",
        "wine": r"""
        .──────.
       /        \
      /          \
     │            │
      \          /
       │        │
       │        │
       └────────┘
""",
        "mason_jar": r"""
      ╭──────────╮
      │ ┌──────┐ │
      │ │      │ │
      │ │      │ │
      │ │      │ │
      │ └──────┘ │
      ╰──────────╯
""",
        "punch_cup": r"""
      ╭──────────╮
      │  ╮        │
      │  ╯        │
      │            │
      └──────────┘
""",
    }
    return glasses.get(glass_key, glasses["rocks"])


def render_strength_bar(abv: float) -> str:
    """Render a strength bar for the cocktail's ABV."""
    # Scale: 0-50% ABV
    normalized = min(abv / 50.0, 1.0)
    bar_len = 30
    filled = int(normalized * bar_len)
    empty = bar_len - filled

    if abv < 10:
        label = "LIGHT"
        color = "░"
    elif abv < 20:
        label = "MEDIUM"
        color = "▒"
    elif abv < 30:
        label = "STRONG"
        color = "▓"
    else:
        label = "POTENT"
        color = "█"

    bar = color * filled + "─" * empty
    return f"  Strength: [{bar}] {abv}% ABV ({label})"


def render_cocktail_menu(cocktails: list, title: str = "COCKTAIL MENU") -> str:
    """Render a beautiful ASCII menu card."""
    width = 62
    lines = []

    # Header
    lines.append("╔" + "═" * width + "╗")
    title_line = f"║  {title.center(width - 4)}  ║"
    lines.append(title_line)
    lines.append("╠" + "═" * width + "╣")
    lines.append("║" + " " * width + "║")

    for i, c in enumerate(cocktails, 1):
        # Name line
        name_str = f"  {i}. {c.name}"
        abv_str = f"{c.abv}% ABV  "
        padded_name = name_str.ljust(width - len(abv_str))
        lines.append(f"║{padded_name}{abv_str}║")

        # Description
        desc = f"     {c.flavor_profile} · {c.method[1].lower()} · {c.glass[1].lower()}"
        if len(desc) > width - 2:
            desc = desc[:width - 5] + "..."
        lines.append(f"║{desc.ljust(width)}║")

        if i < len(cocktails):
            lines.append("║" + " " * width + "║")

    lines.append("║" + " " * width + "║")
    lines.append("╚" + "═" * width + "╝")
    return "\n".join(lines)


def render_recipe_card(cocktail: Cocktail) -> str:
    """Render a detailed recipe card for a single cocktail."""
    width = 58
    lines = []

    # Top border
    lines.append("┌" + "─" * width + "┐")

    # Title
    title = f"  🍸 {cocktail.name}  "
    lines.append(f"│{title.center(width)}│")
    lines.append("├" + "─" * width + "┤")

    # Flavor profile
    if cocktail.flavor_profile:
        fp = f"  Flavor: {cocktail.flavor_profile}"
        lines.append(f"│{fp.ljust(width)}│")

    # Difficulty
    diff = f"  Difficulty: {cocktail.difficulty}"
    lines.append(f"│{diff.ljust(width)}│")
    lines.append("│" + " " * width + "│")

    # Glass & ice
    glass_line = f"  Glass: {cocktail.glass[1]} ({cocktail.glass[2]})"
    lines.append(f"│{glass_line.ljust(width)}│")
    ice_line = f"  Ice: {cocktail.ice[1]}"
    lines.append(f"│{ice_line.ljust(width)}│")
    method_line = f"  Method: {cocktail.method[1]} — {cocktail.method[2]}"
    if len(method_line) > width:
        method_line = method_line[:width - 3] + "..."
    lines.append(f"│{method_line.ljust(width)}│")
    lines.append("│" + " " * width + "│")

    # Ingredients header
    lines.append(f"│{'  ── Ingredients ──'.ljust(width)}│")
    for ing in cocktail.ingredients:
        role_icon = {"base": "◎", "liqueur": "◇", "mixer": "○", "bitters": "✦"}.get(ing.role, "·")
        amount_str = f"{ing.amount_oz} oz" if ing.amount_oz != 1 else "1 dash"
        if ing.role == "bitters":
            amount_str = "1 dash"
        ing_line = f"  {role_icon} {ing.name} ({amount_str})"
        if ing.abv > 0:
            ing_line += f" — {ing.abv}%"
        lines.append(f"│{ing_line.ljust(width)}│")

    lines.append("│" + " " * width + "│")

    # Garnish
    garnish_line = f"  ✿ Garnish: {cocktail.garnish[1]}"
    lines.append(f"│{garnish_line.ljust(width)}│")

    # Strength bar
    lines.append("│" + " " * width + "│")
    strength = render_strength_bar(cocktail.abv)
    lines.append(f"│{strength.ljust(width)}│")

    # Story
    if cocktail.story:
        lines.append("│" + " " * width + "│")
        lines.append(f"│{'  ── Story ──'.ljust(width)}│")
        # Word wrap story
        words = cocktail.story.split()
        story_lines = []
        current = "  "
        for word in words:
            if len(current) + 1 + len(word) > width - 2:
                story_lines.append(current)
                current = "  " + word
            else:
                current += " " + word
        if current.strip():
            story_lines.append(current)
        for sl in story_lines:
            lines.append(f"│{sl.ljust(width)}│")

    lines.append("└" + "─" * width + "┘")

    # Glass ASCII art
    lines.append("")
    lines.append(render_glass_ascii(cocktail.glass[0]))

    return "\n".join(lines)


def render_ingredient_shopping_list(cocktails: list) -> str:
    """Render a consolidated shopping list for multiple cocktails."""
    all_ingredients = {}
    for c in cocktails:
        for ing in c.ingredients:
            key = ing.name
            if key not in all_ingredients:
                all_ingredients[key] = []
            all_ingredients[key].append(f"{ing.amount_oz} oz ({c.name})")

    lines = []
    lines.append("┌──────────────────────────────────────────────┐")
    lines.append("│         🛒  SHOPPING LIST                    │")
    lines.append("├──────────────────────────────────────────────┤")

    categories = {"Spirits": [], "Liqueurs": [], "Mixers": [], "Bitters": []}
    for c in cocktails:
        for ing in c.ingredients:
            if ing.role == "base":
                cat = "Spirits"
            elif ing.role == "liqueur":
                cat = "Liqueurs"
            elif ing.role == "bitters":
                cat = "Bitters"
            else:
                cat = "Mixers"
            entry = f"  • {ing.name} (for {', '.join(set(x.split('(')[1].rstrip(')') for x in all_ingredients[ing.name]))})"
            categories[cat].append(ing.name)

    for cat, items in categories.items():
        if items:
            lines.append(f"│  {cat}:                                     │")
            for item in sorted(set(items)):
                count = items.count(item)
                line = f"  • {item}"
                if count > 1:
                    line += f" (×{count})"
                lines.append(f"│{line.ljust(46)}│")
            lines.append("│" + " " * 46 + "│")

    lines.append("└──────────────────────────────────────────────┘")
    return "\n".join(lines)


# ─── Menu Builder Mode ──────────────────────────────────────────────────────

def interactive_menu():
    """Interactive menu building mode."""
    print("\n" + "═" * 50)
    print("  🍹 TERMINAL COCKTAIL MIXOLOGIST 🍹")
    print("  Procedural Cocktail Recipe Generator")
    print("═" * 50)

    while True:
        print("\nOptions:")
        print("  [1] Generate a random cocktail")
        print("  [2] Generate a cocktail by style")
        print("  [3] Generate a full menu (5 cocktails)")
        print("  [4] Generate a themed menu")
        print("  [5] Generate cocktail pairing (2 drinks)")
        print("  [q] Quit")

        choice = input("\n→ ").strip().lower()

        if choice == "q":
            print("\nCheers! 🥂")
            break
        elif choice == "1":
            c = generate_cocktail()
            print("\n" + render_recipe_card(c))
        elif choice == "2":
            print("\nStyles:", ", ".join(STYLE_PROFILES.keys()))
            style = input("Choose style → ").strip().lower()
            if style in STYLE_PROFILES:
                c = generate_cocktail(style)
                print("\n" + render_recipe_card(c))
            else:
                print("Unknown style. Generating random...")
                c = generate_cocktail()
                print("\n" + render_recipe_card(c))
        elif choice == "3":
            cocktails = [generate_cocktail() for _ in range(5)]
            print("\n" + render_cocktail_menu(cocktails))
            print("\n" + render_ingredient_shopping_list(cocktails))
            print("\n--- Full Recipes ---\n")
            for c in cocktails:
                print(render_recipe_card(c))
                print()
        elif choice == "4":
            themes = {
                "tiki": "tropical",
                "speakeasy": "classic",
                "dive bar": "strong",
                "brunch": "fizzy",
                "nightcap": "bitter",
                "summer": "tropical",
                "winter": "dessert",
                "sour hour": "sour",
            }
            print("\nThemes:", ", ".join(themes.keys()))
            theme = input("Choose theme → ").strip().lower()
            style = themes.get(theme, random.choice(list(STYLE_PROFILES.keys())))
            cocktails = [generate_cocktail(style) for _ in range(5)]
            print("\n" + render_cocktail_menu(cocktails, f"{theme.upper()} NIGHT MENU"))
            print("\n--- Full Recipes ---\n")
            for c in cocktails:
                print(render_recipe_card(c))
                print()
        elif choice == "5":
            c1 = generate_cocktail()
            # Second cocktail should complement
            complementary = {"classic": "sour", "tropical": "strong", "strong": "fizzy",
                           "fizzy": "bitter", "dessert": "classic", "bitter": "tropical", "sour": "dessert"}
            style2 = complementary.get(random.choice(list(STYLE_PROFILES.keys())),
                                        random.choice(list(STYLE_PROFILES.keys())))
            c2 = generate_cocktail(style2)
            print("\n" + render_cocktail_menu([c1, c2], "PERFECT PAIRING"))
            print("\n--- Full Recipes ---\n")
            print(render_recipe_card(c1))
            print()
            print(render_recipe_card(c2))


def batch_generate(num: int = 5, style: str = None, json_output: bool = False):
    """Generate cocktails in batch mode (non-interactive)."""
    cocktails = []
    for _ in range(num):
        c = generate_cocktail(style)
        cocktails.append(c)

    if json_output:
        import json
        data = []
        for c in cocktails:
            data.append({
                "name": c.name,
                "flavor_profile": c.flavor_profile,
                "difficulty": c.difficulty,
                "abv": c.abv,
                "total_oz": c.total_oz,
                "method": c.method[1],
                "glass": c.glass[1],
                "ice": c.ice[1],
                "garnish": c.garnish[1],
                "ingredients": [
                    {"name": i.name, "amount_oz": i.amount_oz, "abv": i.abv, "role": i.role}
                    for i in c.ingredients
                ],
                "story": c.story,
            })
        print(json.dumps(data, indent=2))
    else:
        print("\n" + render_cocktail_menu(cocktails))
        print("\n" + render_ingredient_shopping_list(cocktails))
        print("\n--- Full Recipes ---\n")
        for c in cocktails:
            print(render_recipe_card(c))
            print()


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🍹 Terminal Cocktail Mixologist — Procedural cocktail recipe generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Generate 1 random cocktail
  %(prog)s -n 5                     Generate 5 random cocktails
  %(prog)s -n 3 -s tropical        Generate 3 tropical cocktails
  %(prog)s -n 5 --json              Output as JSON
  %(prog)s --interactive            Interactive menu mode
        """
    )
    parser.add_argument("-n", "--number", type=int, default=1,
                        help="Number of cocktails to generate (default: 1)")
    parser.add_argument("-s", "--style", choices=list(STYLE_PROFILES.keys()),
                        help="Cocktail style/theme")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Run in interactive menu mode")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of ASCII")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if args.interactive:
        interactive_menu()
    else:
        batch_generate(args.number, args.style, args.json)


if __name__ == "__main__":
    main()