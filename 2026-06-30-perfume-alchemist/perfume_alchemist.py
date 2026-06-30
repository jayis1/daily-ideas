#!/usr/bin/env python3
"""
Perfume Alchemist — Procedural Perfume Generator
Generates unique perfume compositions with note pyramids, scent profiles,
and evocative descriptions using procedural generation.
"""

import random
import sys
import argparse
from dataclasses import dataclass, field
from typing import List, Optional

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

SEASONS = ["eternal spring", "high summer", "autumn twilight", "winter solstice",
           "monsoon dusk", "perpetual golden hour", "frost-dawn", "midnight bloom"]

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
    "a Copenhaven bookshop in the rain",
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


@dataclass
class Note:
    name: str
    category: str
    description: str


@dataclass
class Perfume:
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

        w_top = max(len(top_str), 20)
        w_heart = max(len(heart_str), w_top + 8)
        w_base = max(len(base_str), w_heart + 8)

        lines = []
        lines.append("╭" + "─" * (w_base + 2) + "╮")
        lines.append("│" + " TOP ".center(w_base + 2) + "│")
        lines.append("│" + f"  {top_str}".ljust(w_base + 1) + "│")
        lines.append("├" + "─" * (w_base + 2) + "┤")
        lines.append("│" + " HEART ".center(w_base + 2) + "│")
        lines.append("│" + f"  {heart_str}".ljust(w_base + 1) + "│")
        lines.append("├" + "─" * (w_base + 2) + "┤")
        lines.append("│" + " BASE ".center(w_base + 2) + "│")
        lines.append("│" + f"  {base_str}".ljust(w_base + 1) + "│")
        lines.append("╰" + "─" * (w_base + 2) + "╯")
        return "\n".join(lines)

    def scent_profile_bar(self) -> str:
        """Generate a visual scent profile bar chart."""
        categories = {}
        for note_list in [self.top_notes, self.heart_notes, self.base_notes]:
            for note in note_list:
                categories[note.category] = categories.get(note.category, 0) + 1

        total = sum(categories.values())
        max_label = max(len(k) for k in categories)
        bar_width = 30

        lines = []
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            pct = count / total
            filled = int(pct * bar_width)
            bar = "█" * filled + "░" * (bar_width - filled)
            lines.append(f"  {cat.capitalize():<{max_label + 2}} {bar} {pct:.0%}")
        return "\n".join(lines)

    def full_report(self) -> str:
        """Generate a complete, beautiful report."""
        lines = []
        lines.append("")
        lines.append(f"  ✦ {self.name} ✦".center(60))
        lines.append(f"  \"{self.family}\" — {self.family_description}".center(60))
        lines.append("")
        lines.append(f"  Mood: {self.mood.capitalize()}")
        lines.append(f"  Season: {self.season.capitalize()}")
        lines.append(f"  Origin: {self.origin.capitalize()}")
        lines.append(f"  Concentration: {self.concentration}")
        lines.append(f"  Longevity: {self.longevity}")
        lines.append(f"  Sillage: {self.sillage}")
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
        # Wrap description
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
    ]
    return random.choice(templates)


def generate_perfume(family: Optional[str] = None, mood: Optional[str] = None) -> Perfume:
    """Generate a complete procedural perfume."""
    # Pick family
    if family:
        fam_data = next((f for f in FAMILIES if f[0].lower() == family.lower()), random.choice(FAMILIES))
    else:
        fam_data = random.choice(FAMILIES)

    # Pick mood
    chosen_mood = mood if mood else random.choice(MOODS)

    # Select notes
    n_top = random.randint(2, 3)
    n_heart = random.randint(2, 4)
    n_base = random.randint(2, 4)

    top = [Note(*random.choice(TOP_NOTES)) for _ in range(n_top)]
    heart = [Note(*random.choice(HEART_NOTES)) for _ in range(n_heart)]
    base = [Note(*random.choice(BASE_NOTES)) for _ in range(n_base)]

    # Ensure no duplicate note names — resample any duplicates
    def dedupe(notes, pool, seen):
        result = []
        for note in notes:
            attempts = 0
            while note.name in seen and attempts < 50:
                note = Note(*random.choice(pool))
                attempts += 1
            seen.add(note.name)
            result.append(note)
        return result

    seen = set()
    top = dedupe(top, TOP_NOTES, seen)
    heart = dedupe(heart, HEART_NOTES, seen)
    base = dedupe(base, BASE_NOTES, seen)

    concentration = random.choice(["Eau de Cologne", "Eau de Toilette",
                                    "Eau de Parfum", "Parfum / Extrait"])
    longevity = random.choice(["2–4 hours", "4–6 hours", "6–8 hours",
                                "8–12 hours", "12+ hours"])
    sillage = random.choice(["Intimate", "Moderate", "Strong", "Room-filling"])

    name = generate_name()
    season = random.choice(SEASONS)
    origin = random.choice(ORIGINS)

    perfume = Perfume(
        name=name,
        family=fam_data[0],
        family_description=fam_data[1],
        mood=chosen_mood,
        season=season,
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
    """Generate a collection of perfumes, ensuring variety in families and moods."""
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


def interactive_menu():
    """Run an interactive perfume generation session."""
    print("\n" + "═" * 60)
    print("  ✦ P E R F U M E   A L C H E M I S T ✦".center(60))
    print("  Procedural Fragrance Generator".center(60))
    print("═" * 60)

    while True:
        print("\n  What would you like to create?")
        print("  1. Generate a single perfume")
        print("  2. Generate a collection (5 perfumes)")
        print("  3. Generate by mood")
        print("  4. Generate by family")
        print("  5. Quick random perfume")
        print("  q. Quit")
        print()

        choice = input("  Choose [1-5/q]: ").strip().lower()

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
  python perfume_alchemist.py --generate          # Generate one perfume
  python perfume_alchemist.py --generate 3         # Generate 3 perfumes
  python perfume_alchemist.py --family Chypre     # Generate Chypre fragrance
  python perfume_alchemist.py --mood hypnotic      # Generate hypnotic fragrance
  python perfume_alchemist.py --collection         # Generate a 5-perfume collection
  python perfume_alchemist.py --list-families      # Show fragrance families
  python perfume_alchemist.py --list-moods         # Show available moods
        """
    )
    parser.add_argument("--generate", "-g", nargs="?", const=1, type=int,
                        help="Generate N perfumes (default 1)")
    parser.add_argument("--family", "-f", type=str,
                        help="Specify fragrance family")
    parser.add_argument("--mood", "-m", type=str,
                        help="Specify mood")
    parser.add_argument("--collection", "-c", action="store_true",
                        help="Generate a 5-perfume collection")
    parser.add_argument("--list-families", action="store_true",
                        help="List fragrance families")
    parser.add_argument("--list-moods", action="store_true",
                        help="List available moods")
    parser.add_argument("--seed", "-s", type=int,
                        help="Random seed for reproducibility")

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
        return

    if args.generate is not None:
        n = args.generate
        for i in range(n):
            p = generate_perfume(family=args.family, mood=args.mood)
            print(p.full_report())
            if i < n - 1:
                print("─" * 62)
        return

    # Default: interactive mode
    interactive_menu()


if __name__ == "__main__":
    main()