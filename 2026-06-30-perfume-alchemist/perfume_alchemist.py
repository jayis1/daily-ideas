#!/usr/bin/env python3
"""
Perfume Alchemist — Procedural Perfume Generator
Generates unique perfume compositions with note pyramids, scent profiles,
and evocative descriptions using procedural generation.

Features:
  - Random or guided perfume generation (by family, mood, season)
  - Collections of varied perfumes
  - Side-by-side comparison of two fragrances
  - Note search across the ingredient database
  - JSON export for saving/sharing perfume compositions
  - Reproducible generation with --seed
  - Concentration-longevity consistency (EDC < EDT < EDP < Extrait)
  - Interactive menu-driven exploration

Version: 1.1.0
"""

import json
import random
import sys
import argparse
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Tuple

__version__ = "1.1.0"

# ─── Data: Fragrance notes ───────────────────────────────────────────────────

TOP_NOTES = [
    ("bergamot", "citrus", "bright, sparkling citrus that dances on first spray"),
    ("lemon zest", "citrus", "zippy, sun-drenched lemon peel"),
    ("pink pepper", "spicy", "rosy warmth with a playful bite"),
    ("lavender", "herbal", "cool, calming purple fields"),
    ("mint", "herbal", "crisp and invigorating, morning garden fresh"),
    ("grapefruit", "citrus", "tangy pink sunrise in a bottle"),
    ("cardamom", "spicy", "warm, aromatic, slightly sweet intrigue"),
    ("juniper berry", "herbal", "gin-like clarity with forest edge"),
    ("blackcurrant", "fruity", "dark, tart, jewel-toned berry burst"),
    ("neroli", "floral", "bitter orange blossom, Mediterranean twilight"),
    ("galbanum", "green", "sharp, bitter green, freshly snapped stem"),
    ("ylang-ylang extra", "floral", "tropical, banana-like creaminess"),
    ("petitgrain", "citrus", "bitter orange leaf, green and luminous"),
    ("saffron", "spicy", "liquid gold, hay-like, ancient luxury"),
    ("apple blossom", "floral", "orchard innocence with honeyed edge"),
    ("cucumber", "green", "cool, watery, spa-day freshness"),
    ("coriander seed", "spicy", "citrusy, warm, quietly complex"),
    ("mastic", "green", "resinous, pine-like Aegean island breeze"),
    ("yuzu", "citrus", "Japanese citrus, effervescent and refined"),
    ("tarragon", "herbal", "anise-tinged, French kitchen garden"),
]

HEART_NOTES = [
    ("rose de mai", "floral", "the queen of flowers, honeyed and luminous"),
    ("oud", "woody", "dark, sacred wood, smoke and mystery"),
    ("jasmine sambac", "floral", "intoxicating night-blooming seduction"),
    ("iris butter", "floral", "powdery elegance, suede-like violet grace"),
    ("violet leaf", "green", "crushed green leaves with metallic whisper"),
    ("cinnamon bark", "spicy", "warm, baking, skin-like comfort"),
    ("cypress", "woody", "Mediterranean hills, incense-laced evergreen"),
    ("geranium", "floral", "rosy-minty, old-world gentleman's garden"),
    ("clove bud", "spicy", "arid heat, dental sharp, ancient spice route"),
    ("mimosa", "floral", "fuzzy yellow clouds, powdery tenderness"),
    ("davana", "herbal", "apricot-tinged, absinthe-green complexity"),
    ("fig leaf", "green", "milky, sun-warm, Mediterranean orchard"),
    ("black tea", "herbal", "tannic depth, smoky, contemplative cup"),
    ("cistus labdanum", "resinous", "ambergris warmth, sticky ambered leather"),
    ("tuberose", "floral", "carnal cream, opulent, dangerous beauty"),
    ("nutmeg", "spicy", "warm, slightly psychedelic kitchen spice"),
    ("honeysuckle", "floral", "nectar-sweet, twining vine memory"),
    ("sage", "herbal", "earthy wisdom, smudge-purified air"),
    ("magnolia", "floral", "Southern nights, lemon-cream petals"),
    ("elemi resin", "resinous", "peppery, lemony, incense precursor"),
]

BASE_NOTES = [
    ("sandalwood mysore", "woody", "creamy, meditative, temple incense"),
    ("vetiver haiti", "earthy", "dark roots, smoke, rain-soaked earth"),
    ("ambergris", "animalic", "oceanic, saline, warm skin after the sea"),
    ("patchouli dark", "earthy", "damp cellar, counterculture, depth"),
    ("musk ketone", "animalic", "clean skin, intimate, barely-there warmth"),
    ("vanilla tahitensis", "sweet", "gourmet, rum-soaked, gourmand embrace"),
    ("tonka bean", "sweet", "almond-vanilla, hay, twilight sweetness"),
    ("benzoin siam", "resinous", "vanillic resin, warm balsamic comfort"),
    ("oakmoss", "earthy", "forest floor, chypre soul, lichen-damp bark"),
    ("cedar atlas", "woody", "pencil-shavings, Moroccan mountain air"),
    ("castoreum", "animalic", "leathery, primal, fur and firelight"),
    ("opopanax", "resinous", "sweet myrrh, balsamic, ancient temple"),
    ("cashmeran", "musky", "soft gray wool, musky, comforting skin"),
    ("balsam peru", "resinous", "cinnamon-vanilla balsam, healing warmth"),
    ("civet", "animalic", "raw, primal, the edge of propriety"),
    ("leather accord", "leather", "saddle, smoking jacket, tannery romance"),
    ("immortelle", "earthy", "curry flower, burnt sugar, eternal straw"),
    ("guaiacwood", "woody", "smoky, rose-tinged, quiet strength"),
    ("amber fossil", "resinous", "prehistoric resin, golden time capsule"),
    ("honeycomb absolute", "sweet", "beeswax, golden syrup, sunlit hive"),
]

FAMILIES = [
    ("Chypre", "The sophisticated rebel — bergamot on oakmoss, earthy elegance."),
    ("Oriental / Amber", "Warm, resinous, addictive — vanilla, oud, and spice bazaars."),
    ("Floral", "The garden distilled — roses, jasmines, bouquets in bloom."),
    ("Fresh / Aquatic", "Sea spray and ozone — clean, breezy, open horizons."),
    ("Woody / Aromatic", "Forest temple — cedar, vetiver, incense smoke."),
    ("Gourmand", "Edible seduction — vanilla, coffee, dark chocolate temptation."),
    ("Fougère", "Barbershop soul — lavender, coumarin, fern-green sophistication."),
    ("Leather / Tobacco", "By the fire — saddle leather, pipe smoke, vintage study."),
    ("Green / Herbaceous", "Morning dew on leaves — crushed stems, fresh-cut grass."),
    ("Fruity / Tropical", "Island escape — mango, coconut, sun-drenched abandon."),
]

MOODS = [
    "enigmatic", "opulent", "serene", "feral", "nostalgic", "intimate",
    "regal", "melancholic", "exuberant", "hypnotic", "austere", "sensual",
    "dreamlike", "untamed", "tender", "imperious", "whimsical", "primordial",
    "celestial", "decadent", "wistful", "thunderous", "ethereal", "visceral",
]

SEASONS = [
    "eternal spring", "high summer", "autumn twilight", "winter solstice",
    "monsoon dusk", "perpetual golden hour", "frost-dawn", "midnight bloom",
]

ORIGINS = [
    "a Parisian attic where old letters yellow",
    "a Carpathian monastery lost in mist",
    "a Marrakech souk at closing time",
    "a seaside cliff in Cinque Terre",
    "a Kyoto temple garden in November",
    "a speakeasy beneath Buenos Aires",
    "a lighthouse on the Outer Hebrides",
    "a Venetian palazzo at Carnival",
    "a Bombay spice warehouse at dawn",
    "a Savannah veranda in August",
    "a Fjord village under the aurora",
    "a Damascus courtyard with orange trees",
    "a Copenhagen bookshop in the rain",
    "a Tasmanian lavender field at dusk",
    "a Himalayan monastery at sunrise",
]

NAME_PREFIXES = [
    "Noir", "Velours", "Lumière", "Ombre", "Éclat", "Brume", "Silence",
    "Aube", "Cendres", "Rêve", "Fugace", "Immortelle", "Braise", "Absinthe",
    "Spectre", "Éther", "Nacre", "Soupir", "Oubli", "Mirage", "Velours",
    "Somnium", "Crépuscule", "Vérité", "Chimère", "Obscura", "Solstice",
    "Hérésie", "Alchimie", "Mystère",
]

NAME_SUFFIXES = [
    "de Minuit", "Sauvage", "Profond", "Éternel", "Secret", "Maudit",
    "Céleste", "Interdit", "Perdu", "Précieux", "Ancien", "Divin",
    "Dissimulé", "Merveilleux", "Sans Nom", "Abscons", "Empoisonné",
    "Enfumé", "Galant", "Oublié", "Sans Façon", "Ardent", "Velouté",
]

NAME_STANDALONES = [
    "Murmure", "Ténèbres", "L'Air Rien", "Demi-Jour", "Fleur de Feu",
    "Peau d'Âme", "Cœur de Cendre", "Sang de Lune", "Larme d'Or",
    "Souffle Noir", "Main de Glace", "L'Heure Bleue", "Feu Follet",
    "Pierre de Lune", "Voile de Brume", "Cendres et Roses", "Nuit Blanche",
    "Sillages", "Lisière", "Point de Fuite", "Loin", "Jusqu'aux Os",
    "Les Yeux Fermés", "Sous la Peau", "À Fleur de Peau", "Bain de Minuit",
]

# Concentration-to-longevity mapping for realistic perfume generation.
# Higher concentrations naturally last longer on skin.
CONCENTRATION_LONGEVITY = {
    "Eau de Cologne": ["2–4 hours", "2–4 hours", "3–5 hours"],
    "Eau de Toilette": ["3–5 hours", "4–6 hours", "4–6 hours"],
    "Eau de Parfum": ["6–8 hours", "6–8 hours", "8–12 hours"],
    "Parfum / Extrait": ["8–12 hours", "12+ hours", "12+ hours"],
}

CONCENTRATION_SILLAGE = {
    "Eau de Cologne": ["Intimate", "Moderate"],
    "Eau de Toilette": ["Intimate", "Moderate", "Moderate"],
    "Eau de Parfum": ["Moderate", "Strong", "Strong"],
    "Parfum / Extrait": ["Strong", "Room-filling"],
}

# Pairing compatibility: note categories that harmonize well together.
# Used to suggest pairings and calculate a harmony score.
HARMONY_PAIRS = {
    ("citrus", "floral"), ("citrus", "herbal"), ("citrus", "green"),
    ("floral", "woody"), ("floral", "spicy"), ("floral", "sweet"),
    ("woody", "resinous"), ("woody", "earthy"), ("woody", "spicy"),
    ("spicy", "sweet"), ("spicy", "resinous"), ("spicy", "leather"),
    ("sweet", "resinous"), ("sweet", "musky"),
    ("earthy", "resinous"), ("earthy", "green"),
    ("green", "herbal"), ("green", "citrus"),
    ("animalic", "leather"), ("animalic", "woody"),
    ("musky", "sweet"), ("musky", "floral"),
    ("leather", "tobacco"), ("leather", "smoky"),
    ("herbal", "woody"), ("herbal", "green"),
    ("fruity", "floral"), ("fruity", "sweet"),
}


@dataclass
class Note:
    """A single fragrance note with name, category, and description."""
    name: str
    category: str
    description: str

    def to_dict(self) -> dict:
        """Convert to a plain dictionary for JSON serialization."""
        return {"name": self.name, "category": self.category, "description": self.description}


@dataclass
class Perfume:
    """A complete procedural perfume composition."""
    name: str
    family: str
    family_description: str
    mood: str
    season: str
    origin: str
    top_notes: List[Note]
    heart_notes: List[Note]
    base_notes: List[Note]
    concentration: str
    longevity: str
    sillage: str
    description: str

    def note_pyramid(self) -> str:
        """Render the fragrance note pyramid as ASCII art."""
        all_top = [n.name for n in self.top_notes]
        all_heart = [n.name for n in self.heart_notes]
        all_base = [n.name for n in self.base_notes]

        top_str = "  ·  ".join(all_top)
        heart_str = " · ".join(all_heart)
        base_str = " · ".join(all_base)

        # Calculate widths — pyramid narrows at top
        w_base = max(len(base_str), 20)
        w_heart = max(len(heart_str), 20)
        w_top = max(len(top_str), 20)
        w = max(w_base, w_heart + 8, w_top + 4)

        lines = []
        lines.append("╭" + "─" * (w + 2) + "╮")
        lines.append("│" + " TOP ".center(w + 2) + "│")
        lines.append("│" + f"  {top_str}".ljust(w + 1) + "│")
        lines.append("├" + "─" * (w + 2) + "┤")
        lines.append("│" + " HEART ".center(w + 2) + "│")
        lines.append("│" + f"  {heart_str}".ljust(w + 1) + "│")
        lines.append("├" + "─" * (w + 2) + "┤")
        lines.append("│" + " BASE ".center(w + 2) + "│")
        lines.append("│" + f"  {base_str}".ljust(w + 1) + "│")
        lines.append("╰" + "─" * (w + 2) + "╯")
        return "\n".join(lines)

    def scent_profile_bar(self) -> str:
        """Generate a visual scent profile bar chart."""
        categories: Dict[str, int] = {}
        # Weight base notes more (they anchor the fragrance longer)
        for note in self.top_notes:
            categories[note.category] = categories.get(note.category, 0) + 1
        for note in self.heart_notes:
            categories[note.category] = categories.get(note.category, 0) + 2
        for note in self.base_notes:
            categories[note.category] = categories.get(note.category, 0) + 3

        total = sum(categories.values())
        max_label = max(len(k) for k in categories) if categories else 1
        bar_width = 30

        lines = []
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            pct = count / total
            filled = int(pct * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            lines.append(f"  {cat.capitalize():<{max_label + 2}} {bar} {pct:.0%}")
        return "\n".join(lines)

    def harmony_score(self) -> str:
        """Calculate a harmony/compatibility score based on note category pairings."""
        all_notes = self.top_notes + self.heart_notes + self.base_notes
        categories = [n.category for n in all_notes]
        harmonious = 0
        total_pairs = 0
        for i, cat_a in enumerate(categories):
            for cat_b in categories[i + 1:]:
                total_pairs += 1
                pair = tuple(sorted([cat_a, cat_b]))
                if pair in HARMONY_PAIRS or cat_a == cat_b:
                    harmonious += 1

        if total_pairs == 0:
            return "N/A"

        ratio = harmonious / total_pairs
        if ratio >= 0.7:
            label = "★★★ Harmonious"
        elif ratio >= 0.45:
            label = "★★· Balanced"
        elif ratio >= 0.25:
            label = "★·· Distinctive"
        else:
            label = "···· Contrarian"
        return f"{label} ({ratio:.0%})"

    def full_report(self) -> str:
        """Generate a complete, beautiful report."""
        lines = []
        lines.append("")
        lines.append(f"  ✦ {self.name} ✦".center(60))
        lines.append(f'  "{self.family}" — {self.family_description}'.center(60))
        lines.append("")
        lines.append(f"  Mood: {self.mood.capitalize()}")
        lines.append(f"  Season: {self.season.capitalize()}")
        lines.append(f"  Origin: {self.origin.capitalize()}")
        lines.append(f"  Concentration: {self.concentration}")
        lines.append(f"  Longevity: {self.longevity}")
        lines.append(f"  Sillage: {self.sillage}")
        lines.append(f"  Harmony: {self.harmony_score()}")
        lines.append("")
        lines.append("  ── Note Pyramid ──".center(60))
        lines.append(self.note_pyramid())
        lines.append("")
        lines.append("  ── Scent Profile ──".center(60))
        lines.append(self.scent_profile_bar())
        lines.append("")
        lines.append("  ── Tasting Notes ──".center(60))
        lines.append("")
        lines.append("  ▸ TOP:")
        for n in self.top_notes:
            lines.append(f"    {n.name} — {n.description}")
        lines.append("")
        lines.append("  ▸ HEART:")
        for n in self.heart_notes:
            lines.append(f"    {n.name} — {n.description}")
        lines.append("")
        lines.append("  ▸ BASE:")
        for n in self.base_notes:
            lines.append(f"    {n.name} — {n.description}")
        lines.append("")
        lines.append("  ── Impressions ──".center(60))
        lines.append("")
        # Wrap description to ~60 chars
        words = self.description.split()
        line = "  "
        for word in words:
            if len(line) + len(word) + 1 > 62:
                lines.append(line)
                line = "  " + word
            else:
                line += " " + word if line != "  " else word
        if line.strip():
            lines.append(line)
        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert perfume to a JSON-serializable dictionary."""
        return {
            "name": self.name,
            "family": self.family,
            "family_description": self.family_description,
            "mood": self.mood,
            "season": self.season,
            "origin": self.origin,
            "concentration": self.concentration,
            "longevity": self.longevity,
            "sillage": self.sillage,
            "harmony": self.harmony_score(),
            "top_notes": [n.to_dict() for n in self.top_notes],
            "heart_notes": [n.to_dict() for n in self.heart_notes],
            "base_notes": [n.to_dict() for n in self.base_notes],
            "description": self.description,
        }


def generate_name() -> str:
    """Generate a perfume name with French flair."""
    style = random.random()
    if style < 0.35:
        return f"{random.choice(NAME_PREFIXES)} {random.choice(NAME_SUFFIXES)}"
    elif style < 0.65:
        return random.choice(NAME_STANDALONES)
    else:
        prefix = random.choice(NAME_PREFIXES)
        suffix = random.choice(NAME_SUFFIXES)
        return f"{prefix} {suffix}"


def generate_description(perfume: Perfume) -> str:
    """Generate an evocative perfume description."""
    templates = [
        f"{perfume.name} opens with a {perfume.mood} whisper of {perfume.top_notes[0].name}, "
        f"unfurling into {perfume.heart_notes[0].name} at its pulsing heart. "
        f"The dry-down reveals {perfume.base_notes[0].name}, leaving a {perfume.mood} "
        f"trail that lingers like {perfume.origin}. This {perfume.family.lower()} fragrance "
        f"is a meditation on {perfume.season} — {perfume.family_description.lower()}",

        f"Born from {perfume.origin}, {perfume.name} is a {perfume.mood} "
        f"{perfume.family.lower()} that traces the arc of {perfume.season}. "
        f"From the {perfume.top_notes[0].description} of {perfume.top_notes[0].name} "
        f"through the {perfume.heart_notes[0].name}'s {perfume.heart_notes[0].description}, "
        f"it resolves into the {perfume.base_notes[0].name} depths of "
        f"{perfume.base_notes[0].description}. {perfume.family_description}",

        f"Imagine {perfume.origin}. Now inhale: {perfume.top_notes[0].name} "
        f"bursts forth with its {perfume.top_notes[0].description}, before "
        f"surrendering to the {perfume.mood} embrace of {perfume.heart_notes[0].name}. "
        f"Hours later, {perfume.base_notes[0].name} remains — "
        f"{perfume.base_notes[0].description} — a ghost of {perfume.season}. "
        f"{perfume.family_description}",

        f"A {perfume.mood} apparition, {perfume.name} drifts in from {perfume.origin}. "
        f"Its opening of {perfume.top_notes[0].name} gives way to the {perfume.heart_notes[0].name} "
        f"heart — {perfume.heart_notes[0].description} — before settling into the deep "
        f"embrace of {perfume.base_notes[0].name}. A {perfume.family.lower()} for "
        f"{perfume.season}.",

        f"Close your eyes: {perfume.season}, {perfume.origin}. {perfume.name} is a "
        f"{perfume.mood} {perfume.family.lower()} that begins with {perfume.top_notes[0].name} — "
        f"{perfume.top_notes[0].description} — and spirals through "
        f"{perfume.heart_notes[0].name} before finding its resolution in "
        f"{perfume.base_notes[0].name}, {perfume.base_notes[0].description}.",
    ]
    return random.choice(templates)


def _dedupe_notes(notes: List[Note], pool: List[tuple], seen: set) -> List[Note]:
    """Remove duplicate note names by resampling from the pool.

    Args:
        notes: List of Note objects that may contain duplicates.
        pool: The source pool of (name, category, description) tuples to resample from.
        seen: Set of note names already used; updated in place.

    Returns:
        List of Note objects with unique names.
    """
    result = []
    for note in notes:
        attempts = 0
        while note.name in seen and attempts < 50:
            note = Note(*random.choice(pool))
            attempts += 1
        # If we still have a duplicate after 50 attempts, accept it
        # (extremely unlikely with 20+ note pools)
        seen.add(note.name)
        result.append(note)
    return result


def generate_perfume(
    family: Optional[str] = None,
    mood: Optional[str] = None,
    season: Optional[str] = None,
) -> Perfume:
    """Generate a complete procedural perfume.

    Args:
        family: Fragrance family name (case-insensitive partial match).
        mood: Desired mood for the perfume.
        season: Desired season context.

    Returns:
        A complete Perfume object with all fields populated.
    """
    # Pick family — support partial/case-insensitive matching
    if family:
        fam_data = next(
            (f for f in FAMILIES if family.lower() in f[0].lower()),
            random.choice(FAMILIES),
        )
    else:
        fam_data = random.choice(FAMILIES)

    # Pick mood
    chosen_mood = mood if mood else random.choice(MOODS)

    # Pick season
    chosen_season = season if season else random.choice(SEASONS)

    # Select notes
    n_top = random.randint(2, 3)
    n_heart = random.randint(2, 4)
    n_base = random.randint(2, 4)

    top = [Note(*random.choice(TOP_NOTES)) for _ in range(n_top)]
    heart = [Note(*random.choice(HEART_NOTES)) for _ in range(n_heart)]
    base = [Note(*random.choice(BASE_NOTES)) for _ in range(n_base)]

    # Ensure no duplicate note names
    seen: set = set()
    top = _dedupe_notes(top, TOP_NOTES, seen)
    heart = _dedupe_notes(heart, HEART_NOTES, seen)
    base = _dedupe_notes(base, BASE_NOTES, seen)

    # Pick concentration and derive realistic longevity/sillage
    concentration = random.choice(
        ["Eau de Cologne", "Eau de Toilette", "Eau de Parfum", "Parfum / Extrait"]
    )
    longevity = random.choice(CONCENTRATION_LONGEVITY[concentration])
    sillage = random.choice(CONCENTRATION_SILLAGE[concentration])

    name = generate_name()
    origin = random.choice(ORIGINS)

    perfume = Perfume(
        name=name,
        family=fam_data[0],
        family_description=fam_data[1],
        mood=chosen_mood,
        season=chosen_season,
        origin=origin,
        top_notes=top,
        heart_notes=heart,
        base_notes=base,
        concentration=concentration,
        longevity=longevity,
        sillage=sillage,
        description="",
    )
    perfume.description = generate_description(perfume)
    return perfume


def generate_collection(n: int = 5) -> List[Perfume]:
    """Generate a collection of perfumes, ensuring variety in families and moods.

    Args:
        n: Number of perfumes to generate (default 5).

    Returns:
        List of Perfume objects with varied families and moods.
    """
    families = list(FAMILIES)
    random.shuffle(families)
    moods = list(MOODS)
    random.shuffle(moods)

    perfumes = []
    for i in range(n):
        fam = families[i % len(families)]
        mood = moods[i % len(moods)]
        perfumes.append(generate_perfume(family=fam[0], mood=mood))

    return perfumes


def compare_perfumes(p1: Perfume, p2: Perfume) -> str:
    """Generate a side-by-side comparison of two perfumes.

    Args:
        p1: First perfume to compare.
        p2: Second perfume to compare.

    Returns:
        Formatted comparison string.
    """
    lines = []
    lines.append("")
    lines.append("  ══════════════════ FRAGRANCE DUEL ══════════════════")
    lines.append("")

    # Side by side basic info
    max_name = max(len(p1.name), len(p2.name))
    lines.append(f"  ✦ {p1.name:<{max_name + 4}} ✦ {p2.name}")
    lines.append(f"  {p1.family:<{max_name + 6}} {p2.family}")
    lines.append(f"  Mood: {p1.mood:<{max_name}} Mood: {p2.mood}")
    lines.append(f"  Season: {p1.season:<{max_name - 3}} Season: {p2.season}")
    lines.append(f"  Conc: {p1.concentration:<{max_name - 1}} Conc: {p2.concentration}")
    lines.append(f"  Longevity: {p1.longevity:<{max_name - 5}} Longevity: {p2.longevity}")
    lines.append(f"  Sillage: {p1.sillage:<{max_name - 2}} Sillage: {p2.sillage}")
    lines.append(f"  Harmony: {p1.harmony_score():<{max_name}} Harmony: {p2.harmony_score()}")
    lines.append("")

    # Note comparison
    lines.append("  ── Top Notes ──")
    lines.append(f"    {', '.join(n.name for n in p1.top_notes):<{max_name + 6}} {', '.join(n.name for n in p2.top_notes)}")
    lines.append("  ── Heart Notes ──")
    lines.append(f"    {', '.join(n.name for n in p1.heart_notes):<{max_name + 6}} {', '.join(n.name for n in p2.heart_notes)}")
    lines.append("  ── Base Notes ──")
    lines.append(f"    {', '.join(n.name for n in p1.base_notes):<{max_name + 6}} {', '.join(n.name for n in p2.base_notes)}")
    lines.append("")

    # Shared notes
    names1 = {n.name for n in p1.top_notes + p1.heart_notes + p1.base_notes}
    names2 = {n.name for n in p2.top_notes + p2.heart_notes + p2.base_notes}
    shared = names1 & names2
    if shared:
        lines.append(f"  Shared notes: {', '.join(sorted(shared))}")
    else:
        lines.append("  No shared notes — truly distinct compositions.")

    # Shared categories
    cats1 = {n.category for n in p1.top_notes + p1.heart_notes + p1.base_notes}
    cats2 = {n.category for n in p2.top_notes + p2.heart_notes + p2.base_notes}
    shared_cats = cats1 & cats2
    if shared_cats:
        lines.append(f"  Shared categories: {', '.join(sorted(c.capitalize() for c in shared_cats))}")
    lines.append("")
    return "\n".join(lines)


def search_notes(query: str) -> str:
    """Search for fragrance notes matching a query string.

    Args:
        query: Search term (matches note name or category, case-insensitive).

    Returns:
        Formatted results string.
    """
    q = query.lower().strip()
    results: List[Tuple[str, str, str, str]] = []

    for tier, pool in [("Top", TOP_NOTES), ("Heart", HEART_NOTES), ("Base", BASE_NOTES)]:
        for name, category, desc in pool:
            if q in name.lower() or q in category.lower():
                results.append((tier, name, category, desc))

    if not results:
        return f"\n  No notes found matching '{query}'. Try a note name or category (e.g., 'citrus', 'oud', 'floral').\n"

    lines = [f"\n  ── Notes matching '{query}' ({len(results)} found) ──\n"]
    for tier, name, category, desc in results:
        lines.append(f"  [{tier:>4}] {name} ({category}) — {desc}")
    lines.append("")
    return "\n".join(lines)


def interactive_menu():
    """Run an interactive perfume generation session."""
    print("\n" + "═" * 60)
    print("  ✦ P E R F U M E   A L C H E M I S T ✦".center(60))
    print("  Procedural Fragrance Generator v{}".format(__version__).center(60))
    print("═" * 60)

    while True:
        print("\n  What would you like to create?")
        print("  1. Generate a single perfume")
        print("  2. Generate a collection (5 perfumes)")
        print("  3. Generate by mood")
        print("  4. Generate by family")
        print("  5. Generate by season")
        print("  6. Compare two fragrances (duel)")
        print("  7. Search notes")
        print("  8. Quick random perfume")
        print("  q. Quit")
        print()

        try:
            choice = input("  Choose [1-8/q]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\n  Until next scent... 👃\n")
            break

        if choice == "q":
            print("\n  Until next scent... 👃\n")
            break
        elif choice == "1":
            p = generate_perfume()
            print(p.full_report())
        elif choice == "2":
            perfumes = generate_collection(5)
            print("\n  ── Your Collection ──\n")
            for p in perfumes:
                print(f"  ✦ {p.name}")
                print(f"    {p.family} · {p.mood} · {p.season}")
                print(f"    Top: {', '.join(n.name for n in p.top_notes)}")
                print(f"    Heart: {', '.join(n.name for n in p.heart_notes)}")
                print(f"    Base: {', '.join(n.name for n in p.base_notes)}")
                print()
            input("  Press Enter to see full details of a random perfume...")
            print(random.choice(perfumes).full_report())
        elif choice == "3":
            print("\n  Available moods:")
            for i, m in enumerate(MOODS, 1):
                print(f"    {i:2d}. {m}")
            idx = input("\n  Pick mood number: ").strip()
            try:
                mood = MOODS[int(idx) - 1]
                p = generate_perfume(mood=mood)
                print(p.full_report())
            except (ValueError, IndexError):
                print("  Invalid selection. Try again.")
        elif choice == "4":
            print("\n  Available families:")
            for i, (name, desc) in enumerate(FAMILIES, 1):
                print(f"    {i:2d}. {name} — {desc}")
            idx = input("\n  Pick family number: ").strip()
            try:
                fam = FAMILIES[int(idx) - 1][0]
                p = generate_perfume(family=fam)
                print(p.full_report())
            except (ValueError, IndexError):
                print("  Invalid selection. Try again.")
        elif choice == "5":
            print("\n  Available seasons:")
            for i, s in enumerate(SEASONS, 1):
                print(f"    {i:2d}. {s.capitalize()}")
            idx = input("\n  Pick season number: ").strip()
            try:
                season = SEASONS[int(idx) - 1]
                p = generate_perfume(season=season)
                print(p.full_report())
            except (ValueError, IndexError):
                print("  Invalid selection. Try again.")
        elif choice == "6":
            p1 = generate_perfume()
            p2 = generate_perfume()
            print(compare_perfumes(p1, p2))
        elif choice == "7":
            query = input("  Search for: ").strip()
            if query:
                print(search_notes(query))
            else:
                print("  Please enter a search term.")
        elif choice == "8":
            p = generate_perfume()
            print(p.full_report())
        else:
            print("  Unknown option. Try again.")


def main():
    parser = argparse.ArgumentParser(
        description="Perfume Alchemist — Procedural Perfume Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python perfume_alchemist.py                     # Interactive mode
  python perfume_alchemist.py --generate           # Generate one perfume
  python perfume_alchemist.py --generate 3         # Generate 3 perfumes
  python perfume_alchemist.py --family Chypre      # Generate Chypre fragrance
  python perfume_alchemist.py --mood hypnotic      # Generate hypnotic fragrance
  python perfume_alchemist.py --season "high summer"  # Generate summer fragrance
  python perfume_alchemist.py --collection         # Generate a 5-perfume collection
  python perfume_alchemist.py --compare            # Compare two random fragrances
  python perfume_alchemist.py --search oud         # Search for notes containing 'oud'
  python perfume_alchemist.py --export perfume.json --generate  # Export to JSON
  python perfume_alchemist.py --list-families      # Show fragrance families
  python perfume_alchemist.py --list-moods         # Show available moods
  python perfume_alchemist.py --seed 42            # Reproducible output
        """,
    )
    parser.add_argument(
        "--version", "-v", action="version",
        version=f"Perfume Alchemist v{__version__}",
    )
    parser.add_argument(
        "--generate", "-g", nargs="?", const=1, type=int,
        help="Generate N perfumes (default 1)",
    )
    parser.add_argument(
        "--family", "-f", type=str,
        help="Specify fragrance family (partial/case-insensitive match)",
    )
    parser.add_argument(
        "--mood", "-m", type=str,
        help="Specify mood",
    )
    parser.add_argument(
        "--season", type=str,
        help="Specify season (e.g., 'high summer', 'monsoon dusk')",
    )
    parser.add_argument(
        "--collection", "-c", action="store_true",
        help="Generate a 5-perfume collection",
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="Generate and compare two random fragrances (duel mode)",
    )
    parser.add_argument(
        "--search", type=str, metavar="QUERY",
        help="Search notes by name or category",
    )
    parser.add_argument(
        "--export", "-e", type=str, metavar="FILE",
        help="Export generated perfume(s) to JSON file",
    )
    parser.add_argument(
        "--list-families", action="store_true",
        help="List fragrance families",
    )
    parser.add_argument(
        "--list-moods", action="store_true",
        help="List available moods",
    )
    parser.add_argument(
        "--list-seasons", action="store_true",
        help="List available seasons",
    )
    parser.add_argument(
        "--seed", "-s", type=int,
        help="Random seed for reproducibility",
    )

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if args.list_families:
        print("\nFragrance Families:")
        for name, desc in FAMILIES:
            print(f"  • {name}: {desc}")
        print()
        return

    if args.list_moods:
        print("\nAvailable Moods:")
        for m in MOODS:
            print(f"  • {m}")
        print()
        return

    if args.list_seasons:
        print("\nAvailable Seasons:")
        for s in SEASONS:
            print(f"  • {s.capitalize()}")
        print()
        return

    if args.search:
        print(search_notes(args.search))
        return

    if args.compare:
        p1 = generate_perfume(family=args.family, mood=args.mood)
        p2 = generate_perfume(family=args.family, mood=args.mood)
        output = compare_perfumes(p1, p2)
        print(output)
        if args.export:
            data = {
                "perfume_1": p1.to_dict(),
                "perfume_2": p2.to_dict(),
            }
            try:
                with open(args.export, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  Exported comparison to {args.export}")
            except OSError as exc:
                print(f"  Error writing to {args.export}: {exc}", file=sys.stderr)
        return

    if args.collection:
        perfumes = generate_collection(5)
        print("\n  ── Your Collection ──\n")
        for p in perfumes:
            print(f"  ✦ {p.name}")
            print(f"    {p.family} · {p.mood} · {p.season}")
            print()
        print("─" * 62)
        for p in perfumes:
            print(p.full_report())
            print("─" * 62)
        if args.export:
            data = [p.to_dict() for p in perfumes]
            try:
                with open(args.export, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  Exported collection to {args.export}")
            except OSError as exc:
                print(f"  Error writing to {args.export}: {exc}", file=sys.stderr)
        return

    if args.generate is not None:
        n = args.generate
        perfumes = [
            generate_perfume(family=args.family, mood=args.mood, season=args.season)
            for _ in range(n)
        ]
        for i, p in enumerate(perfumes):
            print(p.full_report())
            if i < n - 1:
                print("─" * 62)
        if args.export:
            data = [p.to_dict() for p in perfumes]
            try:
                with open(args.export, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"  Exported {n} perfume(s) to {args.export}")
            except OSError as exc:
                print(f"  Error writing to {args.export}: {exc}", file=sys.stderr)
        return

    # Default: interactive mode
    interactive_menu()


if __name__ == "__main__":
    main()