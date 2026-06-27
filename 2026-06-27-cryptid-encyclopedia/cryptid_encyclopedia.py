#!/usr/bin/env python3
"""
Cryptid Encyclopedia — Procedurally generated cryptid bestiary.
Each cryptid is deterministically generated from a seed, so the same name
always yields the same creature. Browse, search, or discover random cryptids
with detailed lore, ASCII art, and sighting reports.
"""

import hashlib
import random
import sys
import textwrap
import os

# ── Deterministic RNG from string seed ──────────────────────────────────

def seed_rng(name: str) -> random.Random:
    """Create a deterministic RNG from a string."""
    h = hashlib.sha256(name.lower().strip().encode()).hexdigest()
    return random.Random(int(h, 16))


# ── Data pools ──────────────────────────────────────────────────────────

BODY_TYPES = [
    "bipedal", "quadrupedal", "serpentine", "amorphous", "insectoid",
    "arachnid", "cephalopodic", "chiropteran", "piscine", "aves",
    "draconic", "ursine", "cancrine", "vermiform", "crustacean",
]

SKIN_TEXTURES = [
    "scaly", "slimy", "furry", "feathered", "chitinous", "leathery",
    "gelatinous", "bark-like", "crystalline", "translucent", "mossy",
    "bone-plated", "corroded", "smoldering", "iridescent",
]

COLORS = [
    "ashen gray", "mossy green", "blood crimson", "void black",
    "bioluminescent blue", "sickly yellow", "bruised purple", "rust orange",
    "corpse white", "algae teal", "fungus magenta", "petrified brown",
    "ozone silver", "bile chartreuse", "aurora iridescent",
]

HEAD_SHAPES = [
    "humanoid but eyeless", "cervine with antlers of bone",
    "squid-like with many feelers", "owl-like with a beak of teeth",
    "canine with too many jaws", "featureless save for a single eye",
    "reptilian with a third eye socket", "fish-like with human eyes",
    "skull-like with membrane stretched tight", "insectoid with compound eyes",
    "serpentine with a cowl of skin", "boar-like with tusks of iron",
    "avian with a crown of quills", "amorphous and constantly shifting",
    "primate with a sagittal crest", "moth-like with feathery antennae",
]

ABILITIES = [
    "mimics human voices to lure prey", "can become invisible in fog",
    "emits a paralysis-inducing drone", "phases through solid matter",
    "induces vivid hallucinations", "controls local weather within 1km",
    "absorbs memories through touch", "creates zones of absolute silence",
    "regenerates from any wound within minutes", "manipulates shadows into decoys",
    "causes electronics to malfunction", "exudes an odor that causes amnesia",
    "can appear in multiple places simultaneously", "bends light to appear as someone you know",
    "hibernates for decades then emerges ravenous", "vomits a corrosive mist",
]

HABITATS = [
    "abandoned coal mines in Appalachia", "submerged Mayan temples",
    "the thermal vents beneath Lake Baikal", "glacial crevasses in the Himalayas",
    "mangrove swamps of the Mekong Delta", "collapsed subway tunnels under Moscow",
    "the Mariana Trench's hadal zone", "petrified forests in Patagonia",
    "lava tubes of Kīlauea", "boreal peat bogs of Scandinavia",
    "catacombs beneath Paris", "the Sargasso Sea's floating debris",
    "sinkholes in the Yucatán", "cloud forests of Papua New Guinea",
    "abandoned nuclear testing sites in Kazakhstan",
]

WEAKNESSES = [
    "cannot cross running water", "is repelled by iron filings",
    "falls dormant in direct moonlight", "cannot tolerate the sound of a child's laugh",
    "is harmed by its own reflection", "fears the smell of burnt sage",
    "loses power during the new moon", "is disoriented by recorded birdsong",
    "can be trapped within a circle of salt", "withers when called by its true name",
    "is paralyzed by ultraviolet light", "flees from the sound of church bells",
    "cannot enter any structure with a threshold offering", "melts in purified water",
    "is weakened by the scent of cedar",
]

ORIGINS = [
    "the vengeful spirit of a wronged naturalist",
    "a Cold War experiment in biological weapons that escaped containment",
    "an ancient guardian placed by a forgotten civilization to protect a sacred site",
    "the hybrid offspring of two species that should never have met",
    "a creature that has existed since before the Permian extinction, merely sleeping",
    "the physical manifestation of a region's collective grief",
    "a dimensional refugee that slipped through a thin spot in reality",
    "the result of a curse laid by an indigenous shaman over 500 years ago",
    "a symbiotic organism that merged with a human host long ago",
    "an AI experiment from a defunct research lab that achieved organic self-replication",
    "the degenerated descendant of livestock abandoned by early settlers",
    "a creature born from an underground nuclear test's radiation mutating local fauna",
]

THREAT_LEVELS = [
    ("Harmless — observed but never known to attack", 1),
    ("Unsettling — causes psychological distress", 2),
    ("Caution — will defend territory aggressively", 3),
    ("Dangerous — known to have injured humans", 4),
    ("Lethal — confirmed fatalities on record", 5),
    ("Apocalyptic — entire regions rendered uninhabitable", 6),
    ("Existential — classified threat by 3+ governments", 7),
]

SIGHTING_TYPES = [
    "A lone hiker reported",
    "A team of researchers documented",
    "Multiple witnesses at a rural diner observed",
    "A park ranger's dashcam recorded",
    "Fishermen on a remote lake spotted",
    "A spelunking group encountered",
    "A wildlife photographer captured (film was destroyed)",
    "A search-and-rescue team found evidence of",
    "Local children described to their disbelieving parents",
    "A truck driver on a desolate highway swerved to avoid",
    "An elderly resident who has lived alone for decades finally reported",
    "A group of urban explorers livestreamed (connection lost)",
    "Coast guard radar anomalously detected",
    "A mining crew 2km underground radioed about",
]

SIGHTING_DETAILS = [
    "It stood motionless for 45 seconds before dissolving into mist.",
    "It emitted a sound like reverse laughter and retreated into a cave.",
    "It left three-toed prints in the mud for 200 meters before they simply stopped.",
    "It stared with what appeared to be hundreds of eyes before the observer blacked out.",
    "It circled their campsite for six hours, always just beyond the firelight.",
    "It was seen dragging what appeared to be a deer carcass into a crevasse.",
    "It responded to the witness's name being spoken aloud.",
    "It was wearing what appeared to be a decayed parka.",
    "It had clearly been watching them for some time before it was noticed.",
    "It left a residue on nearby trees that glowed faintly under UV light.",
    "All electronic devices within 50m simultaneously died for ten minutes after the sighting.",
    "The observer's hair turned white. They have not spoken since.",
]

CRYPTID_NAME_PREFIXES = [
    "The", "", "", "", "",
]

CRYPTID_NAME_FORMATS = [
    "{prefix} {adj} {noun}",
    "{prefix} {noun} of {place}",
    "{prefix} {adj} {creature} of {place}",
    "{prefix} {creature} of the {place_adj} {place_noun}",
    "{prefix} {place_adj} {creature}",
    "{prefix} {noun}",
]

ADJECTIVES = [
    "Rutting", "Moldering", "Whispering", "Creeping", "Hollow",
    "Gristle", "Pale", "Lurid", "Shuddering", "Fen",
    "Dank", "Rime", "Sable", "Brimstone", "Wither",
    "Thorn", "Slake", "Vermillion", "Ashen", "Dusk",
]

NOUNS = [
    "Wendigo", "Mantis", "Shuck", "Crawler", "Wraith",
    "Maw", "Watcher", "Stalker", "Howler", "Drifter",
    "Grub", "Fiend", "Hag", "Thing", "Horror",
    "Beast", "Specter", "Ghoul", "Lurker", "Devil",
]

CREATURES = [
    "Mothman", "Jersey Devil", "Skinwalker", "Doppelgänger",
    "Basilisk", "Bunyip", "Chupacabra", "Kraken",
    "Manticore", "Wendigo", "Thunderbird", "Nuckelavee",
    "Barghest", "Dullahan", "Fleshgait", "Rake",
    "Bogeyman", "Nightingale", "Mimic", "Revenant",
]

PLACES = [
    "Blackwood", "Hollow Creek", "the Barrows", "the Meres", "Dunwich",
    "Grimstone", "Briar Hollow", "the Fens", "Witchmoor", "Coldmarsh",
    "Iron Lake", "Slaughter Hill", "the Undercroft", "Stygia", "Harrow",
]

PLACE_ADJS = [
    "Black", "Gray", "Blind", "Silent", "Still",
    "Lost", "Forgotten", "Frozen", "Sunken", "Burning",
    "Bleeding", "Screaming", "Hollow", "Twisted", "Cursed",
]

PLACE_NOUNS = [
    "Woods", "Depths", "Marshes", "Tunnels", "Ruins",
    "Caverns", "Peaks", "Shores", "Fields", "Valleys",
    "Catacombs", "Wastes", "Chasm", "Hollows", "Towers",
]

# ── ASCII Art Templates ──────────────────────────────────────────────────

# Each template is a list of lines with {eye}, {mouth}, {wing}, {tail} markers
# that get replaced based on the creature's features.

CRYPTID_ART_TEMPLATES = [
    # Template 0: Quadruped beast
    [
        "           {eye}     {eye}",
        "          /  \\   /  \\",
        "    ____ /    \\_/    \\",
        "   /    \\  {mouth}  /    \\",
        "  |  {wing}  |  \\_/  |  {wing}  |",
        "   \\____/    |    \\____/",
        "    /   \\    |    /   \\",
        "   /     \\   |   /     \\",
        "  |   {tail}   |  |   {tail}   |",
        "  |       |  |       |",
        "  /   /|  |  |  |\\   \\",
        " /___/ |  |  |  | \\___\\",
        "       /  /  \\  \\",
        "      /__/    \\__\\",
    ],
    # Template 1: Serpentine
    [
        "              {eye}",
        "             /  \\",
        "            / {mouth}\\",
        "     ____  /    |",
        "    /    \\/_____|",
        "   /  {wing}    \\",
        "  |   {wing}     |",
        "   \\         /____",
        "    \\       /     \\",
        "     \\  {tail}/  {tail}  \\",
        "      \\    /       \\",
        "       \\  /    {tail}   \\",
        "        \\/             \\",
        "         \\_____  {tail}   \\",
        "               \\______\\",
    ],
    # Template 2: Bipedal humanoid
    [
        "         _______",
        "        /       \\",
        "       /  {eye}  {eye}  \\",
        "      |  {mouth}      |",
        "      |   \\____/   |",
        "       \\__________/",
        "        |  {wing}  |",
        "       /|  {wing}  |\\",
        "      / |      | \\",
        "     /  |      |  \\",
        "    /   |      |   \\",
        "        |  {tail}  |",
        "        |      |",
        "       / \\    / \\",
        "      /   \\  /   \\",
    ],
    # Template 3: Insectoid/arachnid
    [
        "            {eye}{eye}{eye}",
        "           / \\ / \\",
        "          |  {mouth}  |",
        "           \\_/\\_/",
        "     {wing}/       \\{wing}",
        "    /  |         |  \\",
        "   /   |    O    |   \\",
        "  |  {tail}|         |{tail}  |",
        "   \\   |         |   /",
        "    \\  |         |  /",
        "     {wing}\\|         |/{wing}",
        "       /|         |\\",
        "      / |         | \\",
        "     /  |         |  \\",
        "    /   |    {tail}   |   \\",
        "         |         |",
    ],
    # Template 4: Amorphous blob
    [
        "          {eye}  {eye}  {eye}",
        "        /   \\  {mouth} /   \\",
        "       /     \\____/     \\",
        "      /   {wing}         {wing}   \\",
        "     |     /     \\     |",
        "      \\  {tail}/  {tail}  \\  /",
        "       \\_/        \\_/",
        "      /    {tail}         \\",
        "     /                \\",
        "    |  {wing}    {tail}   {wing}  |",
        "     \\    _       _    /",
        "      \\  / \\     / \\  /",
        "       \\/   \\   /   \\/",
        "        \\    \\_/    /",
        "         \\_________/",
    ],
    # Template 5: Winged creature
    [
        "                    {eye}",
        "                   /\\/",
        "                  /  \\",
        "            _____/ {mouth}\\_____",
        "    {wing}___/     \\__/      \\___{wing}",
        "   /   /       ||        \\   \\",
        "  /  /         ||         \\  \\",
        " / /           ||          \\ \\",
        "||             ||            ||",
        " \\\\            ||           //",
        "  \\\\     {tail}   ||   {tail}    //",
        "   \\\\          ||          //",
        "    \\\\_________||_________//",
        "         |    ||    |",
        "         |    ||    |",
    ],
]

EYES = ["@", "◉", "⊘", "⊙", "⊗", "¤", "⊘", "◎", "✺", "✪", "⊙", "⊛"]
MOUTHS = ["—", "∧", "▽", "~", "=", "ϖ", "⌐", "◘", "ω", "∩", "∑", "▫"]
WINGS = ["≋", "≈", "~", "∿", "♒", "◇", "△", "⌇", "§", "¶", "∆", "∞"]
TAILS = ["§", "¤", "※", "†", "‡", "⊹", "∘", "○", "•", "◦", "⊘", "⊕"]


# ── Generator functions ────────────────────────────────────────────────

def pick(rng, lst):
    return rng.choice(lst)


def pick_n(rng, lst, n):
    return rng.sample(lst, min(n, len(lst)))


def generate_name(rng):
    fmt = pick(rng, CRYPTID_NAME_FORMATS)
    prefix = pick(rng, CRYPTID_NAME_PREFIXES)
    adj = pick(rng, ADJECTIVES)
    noun = pick(rng, NOUNS)
    creature = pick(rng, CREATURES)
    place = pick(rng, PLACES)
    place_adj = pick(rng, PLACE_ADJS)
    place_noun = pick(rng, PLACE_NOUNS)
    name = fmt.format(
        prefix=prefix, adj=adj, noun=noun, creature=creature,
        place=place, place_adj=place_adj, place_noun=place_noun,
    ).strip()
    # Clean up double spaces
    name = " ".join(name.split())
    return name


def generate_art(rng):
    template_idx = rng.randint(0, len(CRYPTID_ART_TEMPLATES) - 1)
    template = CRYPTID_ART_TEMPLATES[template_idx]
    eye = pick(rng, EYES)
    mouth = pick(rng, MOUTHS)
    wing = pick(rng, WINGS)
    tail = pick(rng, TAILS)
    art = []
    for line in template:
        art.append(line.format(eye=eye, mouth=mouth, wing=wing, tail=tail))
    return "\n".join(art)


def generate_sightings(rng, name):
    """Generate 2-4 sighting reports."""
    count = rng.randint(2, 4)
    years = sorted(rng.sample(range(1950, 2026), count), reverse=True)
    sightings = []
    for i, year in enumerate(years):
        stype = pick(rng, SIGHTING_TYPES)
        detail = pick(rng, SIGHTING_DETAILS)
        article = "an" if name[0].lower() in "aeiou" else "a"
        # Avoid "the The" duplication
        display_name = name
        if display_name.startswith("The "):
            s = f"{stype} {display_name} in {year}. {detail}"
        else:
            s = f"{stype} {article} {display_name} in {year}. {detail}"
        sightings.append(s)
    return sightings


def generate_cryptid(name: str) -> dict:
    """Generate a complete cryptid entry from a name seed."""
    rng = seed_rng(name)

    body = pick(rng, BODY_TYPES)
    skin = pick(rng, SKIN_TEXTURES)
    color = pick(rng, COLORS)
    head = pick(rng, HEAD_SHAPES)
    ability = pick(rng, ABILITIES)
    habitat = pick(rng, HABITATS)
    weakness = pick(rng, WEAKNESSES)
    origin = pick(rng, ORIGINS)
    threat_name, threat_level = pick(rng, THREAT_LEVELS)
    height = rng.choice([
        "0.3m", "0.5m", "0.8m", "1.2m", "1.5m", "1.8m", "2.1m",
        "2.4m", "3m", "4m", "5m", "8m", "12m", "variable",
    ])
    weight = rng.choice([
        "2kg", "5kg", "10kg", "25kg", "50kg", "80kg", "120kg",
        "200kg", "350kg", "500kg", "1 tonne", "3 tonnes", "unknown",
    ])
    diet = rng.choice([
        "carnivorous", "herbivorous", "omnivorous", "hematophagic",
        "lithovorous", "fungivorous", "piscivorous", "unknown",
    ])
    activity = rng.choice([
        "nocturnal", "crepuscular", "diurnal", "cathemeral",
        "hibernates for 11 months", "active only during eclipses",
    ])
    sightings = generate_sightings(rng, name)
    art = generate_art(rng)

    return {
        "name": name,
        "body_type": body,
        "skin": skin,
        "color": color,
        "head": head,
        "ability": ability,
        "habitat": habitat,
        "weakness": weakness,
        "origin": origin,
        "threat_level": threat_level,
        "threat_name": threat_name,
        "height": height,
        "weight": weight,
        "diet": diet,
        "activity": activity,
        "sightings": sightings,
        "art": art,
    }


# ── Display functions ───────────────────────────────────────────────────

BOX_WIDTH = 68

def hr(char="─"):
    return f"╔{char * BOX_WIDTH}╗"

def hr_mid(char="─"):
    return f"╟{char * BOX_WIDTH}╢"

def hr_bot(char="─"):
    return f"╚{char * BOX_WIDTH}╝"

def wrapped_line(text, width=BOX_WIDTH):
    lines = textwrap.wrap(text, width=width)
    return lines

def center_line(text, width=BOX_WIDTH):
    return text.center(width)

def display_cryptid(c: dict):
    """Print a beautifully formatted cryptid entry."""
    W = BOX_WIDTH
    print()
    print(hr())
    # Title
    title = f"  {c['name'].upper()}  "
    print(f"║{title.center(W)}║")
    print(hr())
    
    # ASCII art
    art_lines = c["art"].split("\n")
    for line in art_lines:
        print(f"║{line.center(W)}║")
    print(hr_mid())
    
    # Classification
    threat_stars = "★" * c["threat_level"] + "☆" * (7 - c["threat_level"])
    print(f"║  THREAT LEVEL: {threat_stars}  ║")
    print(f"║  {c['threat_name']}{' ' * (W - 4 - len(c['threat_name']))}║")
    print(hr_mid())
    
    # Stats
    stats = [
        ("Body Type", c["body_type"]),
        ("Height", c["height"]),
        ("Weight", c["weight"]),
        ("Diet", c["diet"]),
        ("Activity", c["activity"]),
    ]
    for label, val in stats:
        line = f"  {label}: {val}"
        print(f"║{line:<{W}}║")
    print(hr_mid())
    
    # Description
    desc = (
        f"A {c['color']}, {c['skin']} {c['body_type']} creature "
        f"with a {c['head']} head. "
        f"It {c['ability']}. "
        f"Origin: {c['origin']}."
    )
    desc_lines = wrapped_line(desc, W - 2)
    for dl in desc_lines:
        print(f"║ {dl:<{W-1}}║")
    print(hr_mid())
    
    # Habitat
    hab = f"HABITAT: {c['habitat']}"
    for hl in wrapped_line(hab, W - 2):
        print(f"║ {hl:<{W-1}}║")
    print(hr_mid())
    
    # Weakness
    weak = f"WEAKNESS: {c['weakness']}"
    for wl in wrapped_line(weak, W - 2):
        print(f"║ {wl:<{W-1}}║")
    print(hr_mid())
    
    # Sightings
    print(f"║{'  SIGHTING REPORTS':<{W}}║")
    print(f"║{'─' * W}║")
    for i, s in enumerate(c["sightings"], 1):
        slines = wrapped_line(f"  {i}. {s}", W - 2)
        for sl in slines:
            print(f"║ {sl:<{W-1}}║")
    print(hr_bot())
    print()


# ── Interactive browser ────────────────────────────────────────────────

KNOWN_CRYPTIDS = [
    "The Ashen Wendigo", "The Hollow Stalker of Blackwood",
    "The Rime Fiend", "The Creeping Horror of the Meres",
    "The Lurid Drifter", "The Moldering Beast of Grimstone",
    "The Whispering Wraith of Dunwich", "The Gristle Maw",
    "The Pale Watcher of Iron Lake", "The Dusk Howler",
    "The Slake Crawler of the Barrows", "The Sable Shuck",
    "The Brimstone Specter", "The Wither Hag",
    "The Thorn Devil of Slaughter Hill", "The Vermillion Thing",
]

BANNER = r"""
 ╔════════════════════════════════════════════════════════════════╗
 ║               🦑 CRYPTID ENCYCLOPEDIA 🦑                     ║
 ║                                                               ║
 ║    A procedurally-generated bestiary of creatures              ║
 ║    that may or may not exist.                                  ║
 ║                                                               ║
 ║    Commands:                                                  ║
 ║      <name>   Look up a cryptid by name                       ║
 ║      random   Discover a random cryptid                        ║
 ║      list     List known cryptid names                        ║
 ║      search   Search for cryptids by keyword                  ║
 ║      help     Show this help message                           ║
 ║      quit     Exit the encyclopedia                            ║
 ╚════════════════════════════════════════════════════════════════╝
"""


def interactive_mode():
    """Run the interactive encyclopedia browser."""
    print(BANNER)
    history = []
    
    while True:
        try:
            user_input = input("cryptid> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  The encyclopedia slams shut.")
            break
        
        if not user_input:
            continue
        
        cmd = user_input.lower()
        
        if cmd in ("quit", "exit", "q"):
            print("  The encyclopedia slams shut.")
            break
        
        elif cmd == "help":
            print(BANNER)
        
        elif cmd == "random":
            rng = random.Random()
            name = generate_name(rng)
            c = generate_cryptid(name)
            display_cryptid(c)
            history.append(name)
        
        elif cmd == "list":
            print("\n  Known Cryptids:")
            print("  " + "─" * 50)
            for i, name in enumerate(KNOWN_CRYPTIDS, 1):
                print(f"  {i:2d}. {name}")
            print("  " + "─" * 50)
            print(f"  ({len(KNOWN_CRYPTIDS)} entries)")
            print()
        
        elif cmd == "search":
            keyword = input("  Search keyword: ").strip().lower()
            if not keyword:
                continue
            results = [n for n in KNOWN_CRYPTIDS if keyword in n.lower()]
            if not results:
                # Generate a cryptid with that keyword
                rng_name = seed_rng(keyword)
                name = generate_name(rng_name)
                results = [name]
                print(f"  No known cryptids match '{keyword}'. However...")
            for name in results:
                c = generate_cryptid(name)
                display_cryptid(c)
        
        elif cmd.startswith("search "):
            keyword = cmd[7:].strip()
            results = [n for n in KNOWN_CRYPTIDS if keyword in n.lower()]
            if not results:
                rng_name = seed_rng(keyword)
                name = generate_name(rng_name)
                results = [name]
                print(f"  No known cryptids match '{keyword}'. However...")
            for name in results:
                c = generate_cryptid(name)
                display_cryptid(c)
        
        else:
            # Treat as a cryptid name
            name = user_input
            c = generate_cryptid(name)
            display_cryptid(c)
            history.append(name)
            if name not in KNOWN_CRYPTIDS:
                print(f"  ℹ New cryptid '{name}' added to your discoveries!")
                KNOWN_CRYPTIDS.append(name)


# ── CLI entry point ────────────────────────────────────────────────────

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Cryptid Encyclopedia — Procedurally generated cryptid bestiary"
    )
    parser.add_argument(
        "name", nargs="*", default=None,
        help="Cryptid name to look up (use quotes for multi-word names)"
    )
    parser.add_argument(
        "-r", "--random", action="store_true",
        help="Generate a random cryptid"
    )
    parser.add_argument(
        "-n", "--number", type=int, default=1,
        help="Number of random cryptids to generate (use with --random)"
    )
    parser.add_argument(
        "-l", "--list", action="store_true",
        help="List known cryptid names"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true",
        help="Launch interactive browsing mode"
    )
    parser.add_argument(
        "--export", type=str, default=None,
        help="Export cryptid entry to a text file"
    )
    
    args = parser.parse_args()
    
    # Interactive mode
    if args.interactive:
        interactive_mode()
        return
    
    # List mode
    if args.list:
        print("\nKnown Cryptids:")
        print("─" * 50)
        for i, name in enumerate(KNOWN_CRYPTIDS, 1):
            print(f"  {i:2d}. {name}")
        print("─" * 50)
        print(f"({len(KNOWN_CRYPTIDS)} entries)\n")
        return
    
    # Random mode
    if args.random:
        for _ in range(args.number):
            rng = random.Random()
            name = generate_name(rng)
            c = generate_cryptid(name)
            display_cryptid(c)
            if args.export:
                export_to_file(c, args.export)
        return
    
    # Name lookup
    if args.name:
        name = " ".join(args.name)
        c = generate_cryptid(name)
        display_cryptid(c)
        if args.export:
            export_to_file(c, args.export)
        return
    
    # Default: show help
    parser.print_help()


def export_to_file(c: dict, filepath: str):
    """Export a cryptid entry to a text file."""
    import io
    buf = io.StringIO()
    # Redirect print to buffer
    import contextlib
    with contextlib.redirect_stdout(buf):
        display_cryptid(c)
    with open(filepath, "a") as f:
        f.write(buf.getvalue())
    print(f"  📄 Entry exported to {filepath}")


if __name__ == "__main__":
    main()