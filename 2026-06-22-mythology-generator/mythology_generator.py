#!/usr/bin/env python3
"""
Procedural Mythology Generator
===============================
Generates complete fictional pantheons with gods, relationships,
creation myths, sacred narratives, and cosmological structures.
"""

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ──────────────────────────────────────────────
# Data pools
# ──────────────────────────────────────────────

SUFFIXES = [
    "ion", "ath", "el", "os", "is", "us", "ar", "en", "ir", "on",
    "ia", "yne", "oth", "ul", "an", "yx", "ae", "or", "um", "ix",
    "ith", "orn", "aes", "uth", "alm", "ek", "yr", "oth", "inn", "ash",
]

PREFIXES = [
    "Aeth", "Bal", "Cor", "Dra", "Elu", "Fal", "Gor", "Hel", "Ith", "Jar",
    "Kar", "Lun", "Mar", "Nyx", "Ori", "Pel", "Quor", "Rav", "Sol", "Thr",
    "Uth", "Val", "Wil", "Xan", "Yrm", "Zel", "Ath", "Bor", "Cry", "Dor",
    "Eph", "Fyr", "Gal", "Hes", "Ion", "Kal", "Lor", "Mor", "Nar", "Oth",
]

TITLES = [
    "the Eternal", "the Undying", "the Shaper", "the Weaver", "the Keeper",
    "the Wanderer", "the Silent", "the First", "the Last", "the Hidden",
    "the Unseen", "the Stormborn", "the Deep", "the Swift", "the Patient",
    "the Watchful", "the Fierce", "the Gentle", "the Ancient", "the Bright",
    "the Shadow", "the Flame", "the Frost", "the Dawn", "the Dusk",
    "the Iron", "the Silver", "the Golden", "the Hollow", "the Crowned",
    "the Forgotten", "the Unnamed", "the Boundless", "the Still", "the Roaring",
]

PRIMARY_DOMAINS = [
    "Sky", "Sea", "Earth", "Fire", "War", "Love", "Death", "Wisdom",
    "Hunting", "Harvest", "Storms", "Light", "Darkness", "Music",
    "Healing", "Trickery", "Forge", "Travel", "Dreams", "Time",
    "Fate", "Justice", "Nature", "Moon", "Sun", "Stars",
    "Thunder", "Winter", "Summer", "Spring", "Autumn",
]

SECONDARY_DOMAINS = [
    "Prophecy", "Ritual", "Sacrifice", "Oaths", "Thresholds", "Boundaries",
    "Secrets", "Revelation", "Change", "Memory", "Forgiveness",
    "Vengeance", "Mercy", "Birth", "Rebirth", "Silence", "Echoes",
    "Tides", "Roots", "Ash", "Mist", "Mirrors", "Shadows", "Wells",
    "Crossroads", "Flights", "Depths", "Heights", "Gates", "Ruins",
]

SYMBOLS = [
    "a broken crown", "a three-pronged spear", "an unblinking eye",
    "a spiral shell", "a black flame", "a silver crescent", "a thunderbolt",
    "a woven tapestry", "a barren tree", "a drinking horn", "a closed book",
    "an open hand", "a clenched fist", "a feather", "a skull crowned with flowers",
    "a mirror", "a key", "a raven", "a serpent eating its tail", "a ladder",
    "a compass rose", "an hourglass", "a harp with broken strings", "a brazier",
    "a mask with no face", "a pair of scales", "a fountain", "an anvil",
    "a lantern in darkness", "a knot with no end",
]

CREATION_MYTHS = [
    (
        "In the beginning, there was only {void}. From its depths, "
        "{first_god} arose \u2014 not born, but simply *becoming*. With a single "
        "word that shattered the silence, {first_god} spoke the world into "
        "being. Each syllable became a law of nature, each breath a wind "
        "that still blows today. The other gods formed from the echoes "
        "of that first word, each carrying a fragment of its power.",
        ["void", "first_god"],
    ),
    (
        "Before all things, two primeval forces \u2014 {force_a} and {force_b} \u2014 "
        "swirled in endless opposition. When they finally collided, the "
        "impact birthed {first_god}, who was neither {force_a} nor {force_b} "
        "but something entirely new. {first_god} gathered the residue of "
        "the collision and shaped it into mountains, seas, and sky. The "
        "other gods emerged from the places where residue pooled thickest.",
        ["force_a", "force_b", "first_god"],
    ),
    (
        "The cosmos began as a dream in the mind of {first_god}, who slept "
        "in the space between spaces. When {first_god} stirred, the dream "
        "cracked open and became real. But the dream had its own inhabitants "
        "\u2014 the other gods \u2014 who did not wish to be merely figments. They "
        "seized the cracks in reality and pulled themselves through into "
        "true existence, each claiming a domain of the dream as their own.",
        ["first_god"],
    ),
    (
        "A great cosmic egg floated in {void} for an age beyond counting. "
        "When it could contain itself no longer, it split \u2014 its shell became "
        "the sky and earth, its yolk became the sun, and its white became "
        "the moon. {first_god} emerged from the embryo, already ancient, "
        "already wise. The other gods were the egg's memories, given form.",
        ["void", "first_god"],
    ),
    (
        "In the age before ages, {first_god} was a mortal who discovered "
        "the secret of immortality hidden in {void}. By speaking the secret "
        "backward, {first_god} unmade death itself and ascended to godhood. "
        "But immortality demanded a price: {first_god} could no longer "
        "create alone. So {first_god} bled, and from each drop, another "
        "god was born, each inheriting a piece of {first_god}'s mortal longing.",
        ["void", "first_god"],
    ),
    (
        "There was no beginning. The world has always existed, cycling "
        "through ages of creation and destruction. But in this cycle, "
        "{first_god} was the first to awaken from the ashes of the last "
        "world. Remembering everything that had been, {first_god} wept \u2014 "
        "and each tear became a god, each sob a sacred law. This is why "
        "the gods weep when mortals die: they remember what it was to "
        "be the last of something.",
        ["first_god"],
    ),
]

VOID_NAMES = [
    "the Void", "the Abyss", "the Nothing", "Chaos", "the Formless Dark",
    "the Primal Mist", "the Before", "the Nameless", "the Deep Quiet",
    "the Unmaking", "the Hollow", "the Endless Night",
]

PRIMEVAL_FORCES = [
    "Light and Dark", "Flame and Frost", "Sound and Silence",
    "Order and Chaos", "Motion and Stillness", "Thought and Feeling",
    "Growth and Decay", "Expansion and Contraction", "Creation and Destruction",
    "Dreaming and Waking",
]

RELATIONSHIP_TYPES = [
    ("sibling", "sibling"),
    ("parent", "child"),
    ("spouse", "spouse"),
    ("rival", "rival"),
    ("ally", "ally"),
    ("creator", "creation"),
    ("beloved", "beloved"),
    ("fear", "fear"),
    ("deceiver", "deceived"),
    ("guardian", "ward"),
]

SACRED_NARRATIVE_TEMPLATES = [
    (
        "The Theft of {artifact}",
        (
            "Long ago, {thief} coveted {artifact}, a sacred relic belonging to "
            "{owner}. Under cover of {cover}, {thief} stole into {owner}'s "
            "domain and seized it. But {artifact} could not be owned by one "
            "who was unworthy. It burned {thief}'s hands, and the screams "
            "echoed across the heavens. {owner} reclaimed {artifact}, but "
            "the scars remain \u2014 which is why {explanation}."
        ),
        ["thief", "owner", "artifact", "cover", "explanation"],
    ),
    (
        "The War of {war_name}",
        (
            "When {god_a} declared that {domain} belonged to them alone, "
            "{god_b} rose in fury. The war lasted {duration}, and the mortal "
            "world trembled. Mountains shattered. Seas boiled. In the end, "
            "neither could claim total victory. They forged a pact: "
            "{domain} would be shared, but the border between their "
            "spheres would be marked by {marker} \u2014 a reminder that even "
            "gods must sometimes yield."
        ),
        ["war_name", "god_a", "god_b", "domain", "duration", "marker"],
    ),
    (
        "The Binding of {bound_one}",
        (
            "{bound_one} grew arrogant and threatened to unmake {domain}. "
            "The other gods, in desperation, called upon {binder} to craft "
            "{chains}. With these, {binder} bound {bound_one} in {prison}, "
            "where they remain to this day. But it is said that when "
            "{sign}, the chains weaken, and {bound_one} stirs \u2014 "
            "which is why mortals fear {fear}."
        ),
        ["bound_one", "domain", "binder", "chains", "prison", "sign", "fear"],
    ),
    (
        "The Descent of {descender}",
        (
            "{descender} walked among mortals disguised as a {disguise}, "
            "seeking to understand why {domain} called to them so. For "
            "{duration}, they lived as mortals do \u2014 suffering, rejoicing, "
            "grieving. When they returned to the divine realm, they carried "
            "with them {gift}, which they gave to mortals out of compassion. "
            "This is why {explanation}."
        ),
        ["descender", "disguise", "domain", "duration", "gift", "explanation"],
    ),
    (
        "The Betrayal at {place}",
        (
            "{betrayer} invited {betrayed} to {place} under the guise of "
            "friendship, but had laid a trap. {betrayed}, trusting in the "
            "oaths between their houses, came unguarded. The betrayal "
            "shattered the old covenant, and ever since, {consequence}. "
            "Mortals still invoke {betrayed}'s name when an oath is broken, "
            "for {betrayed} knows the cost of broken trust better than any."
        ),
        ["betrayer", "betrayed", "place", "consequence"],
    ),
]

ARTIFACT_NAMES = [
    "the Sunstone", "the Moonveil", "the Evercup", "the Horn of Awakening",
    "the Shadowcloak", "the First Flame", "the Iron Heart", "the Living Compass",
    "the Whispering Harp", "the Worldseed", "the Still Bell",
    "the Unbreakable Chain", "the Crown of Eyes", "the Mirror of Truth",
    "the Knife That Cuts Fate", "the Ladder of Stars",
]

PLACE_NAMES = [
    "the Edge of the World", "the Bridge of Stars", "the Ashen Plain",
    "the Glass Mountain", "the Bottomless Well", "the Garden of Thorns",
    "the Hall of Echoes", "the Frozen Gate", "the Hollow Throne",
    "the Crimson Shore", "the Pillar of Winds", "the Obsidian Peak",
]

WAR_NAMES = [
    "the Broken Sky", "Sundering", "the Long Night", "Tears",
    "the Iron Seasons", "the Shattered Crown", "the Falling Stars",
    "the Twin Fires", "the Hollow War", "the Silent Battle",
]

DURATIONS = [
    "seven days", "a hundred years", "three ages", "a mortal lifetime",
    "a single night", "forty seasons", "an epoch", "nine months",
    "twice the span of mortal memory", "the time it takes a star to die",
]

EXPLANATIONS = [
    "the sky turns red at dusk",
    "wolves howl at the moon",
    "the sea refuses to be still",
    "some mortals are born with silver eyes",
    "iron rusts even in dry air",
    "children are afraid of the dark",
    "dreams feel more real than waking",
    "certain songs make people weep without knowing why",
    "storms always come from the same direction",
    "no flower blooms forever",
    "echoes never quite match the original sound",
]

SIGNS = [
    "the red star rises", "the last wolf howls", "the sea recedes beyond sight",
    "an unending winter begins", "the moon bleeds", "thunder comes from clear sky",
    "the old trees walk", "time itself shudders", "the names of the dead are spoken",
]

FEARS = [
    "eclipses", "still water", "the number thirteen", "mirrors in the dark",
    "sudden silence", "unchanging seasons", "the sound of weeping from underground",
]

DISGUISES = [
    "beggar", "shepherd", "wandering poet", "nameless soldier",
    "old woman", "child",
]

GIFTS = [
    "the knowledge of writing", "the gift of music", "the secret of fire-making",
    "the art of healing", "the understanding of seasons", "the language of animals",
    "the ability to dream", "the craft of building", "the power of forgiveness",
    "the wisdom of knowing when to let go",
]

PRISONS = [
    "the heart of a dead star", "a mountain of frozen fire",
    "the space between heartbeats",
    "a cage of living iron", "the bottom of the world-sea",
    "the far side of the moon",
    "an unbroken circle of names", "the hollow of an ancient tree",
]

CHAINS = [
    "chains woven from oaths", "a net of starlight", "a rope made of silence",
    "the weight of a thousand regrets", "a song that cannot be forgotten",
    "chains forged from the tears of the betrayed",
]

MARKERS = [
    "a line of salt", "a perpetual storm", "a river that flows both ways",
    "a shadow that falls the wrong direction",
    "a crack in the earth that never heals",
    "a constellation that appears only at the border",
]

COVERS = [
    "eternal night", "a storm of her own making",
    "the longest night of the year",
    "a thick fog", "the chaos of a great battle",
    "the silence of a lunar eclipse",
]

COSMOLOGY_TEMPLATES = [
    (
        "The world rests upon the back of {support}, floating through "
        "{medium}. Above, {sky_god} holds up the heavens. Below, "
        "{underworld_god} guards the roots of all things. Between them, "
        "mortals live their brief, bright lives."
    ),
    (
        "The cosmos is a great tree, its roots in {underworld}, its "
        "canopy in {sky}. Mortals live upon its trunk, and the gods "
        "nest in its branches. When the wind blows, it is the breath "
        "of {ancient}, who was here before the tree grew."
    ),
    (
        "The world is a song sung by {singer}. Mountains are the low "
        "notes, rivers the runs and trills. The gods are the refrains \u2014 "
        "repeating patterns that give the song structure. When {singer} "
        "stops singing, the world will simply end, mid-note."
    ),
    (
        "Three realms overlap like lenses: {realm_a}, {realm_b}, and "
        "{realm_c}. Where they intersect, the mortal world exists. "
        "The gods dwell in the pure zones of their respective realms, "
        "reaching through the intersections to touch mortal lives."
    ),
    (
        "The world is a wheel turned by {turner}. Each spoke is an age, "
        "and mortals cling to the rim, believing they move forward. The "
        "gods sit at the hub, watching the same stories repeat. Only "
        "{turner} knows what lies beyond the wheel."
    ),
]

WORSHIP_PRACTICES = [
    "burning offerings of {offering} at dawn",
    "walking barefoot on sacred paths during the full moon",
    "weaving prayers into cloth that is never worn",
    "singing {god}'s true name only in whispers",
    "leaving the first portion of every meal at a crossroads",
    "inscribing {god}'s symbol on doorframes with ash",
    "fasting from sunrise to sunset on holy days",
    "lighting a flame that must never be allowed to go out",
    "pouring offerings of water into running streams",
    "telling {god}'s stories aloud at every gathering",
    "carrying a small token of {god}'s symbol at all times",
    "building small shrines at the borders of fields",
    "reciting {god}'s epithets upon waking and sleeping",
    "burying precious objects at the roots of ancient trees for {god}",
]

OFFERINGS = [
    "honey", "grain", "wine", "olive oil", "incense",
    "milk", "bread", "flowers", "river stones", "ash",
]


# ──────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────

@dataclass
class God:
    name: str
    title: str
    primary_domain: str
    secondary_domains: list
    symbol: str
    description: str
    personality: str
    worship_practice: str
    taboos: str = ""

    @property
    def full_title(self) -> str:
        return f"{self.name} {self.title}"


@dataclass
class Relationship:
    god_a: str
    god_b: str
    type_a: str
    type_b: str
    story: str


@dataclass
class Mythology:
    pantheon_name: str
    gods: list
    relationships: list
    creation_myth: str
    cosmology: str
    sacred_narratives: list
    great_taboo: str

    def to_dict(self) -> dict:
        return {
            "pantheon_name": self.pantheon_name,
            "gods": [
                {
                    "name": g.name,
                    "title": g.title,
                    "full_title": g.full_title,
                    "primary_domain": g.primary_domain,
                    "secondary_domains": g.secondary_domains,
                    "symbol": g.symbol,
                    "description": g.description,
                    "personality": g.personality,
                    "worship_practice": g.worship_practice,
                    "taboos": g.taboos,
                }
                for g in self.gods
            ],
            "relationships": [
                {
                    "god_a": r.god_a,
                    "god_b": r.god_b,
                    "type_a": r.type_a,
                    "type_b": r.type_b,
                    "story": r.story,
                }
                for r in self.relationships
            ],
            "creation_myth": self.creation_myth,
            "cosmology": self.cosmology,
            "sacred_narratives": self.sacred_narratives,
            "great_taboo": self.great_taboo,
        }


# ──────────────────────────────────────────────
# Generator
# ──────────────────────────────────────────────

class MythologyGenerator:
    def __init__(self, seed=None, num_gods=7):
        self.rng = random.Random(seed)
        self.num_gods = min(max(num_gods, 3), 12)
        self.used_names = set()
        self.used_domains = set()
        self.gods = []

    def _pick(self, seq):
        return self.rng.choice(seq)

    def _pick_n(self, seq, n):
        return self.rng.sample(seq, min(n, len(seq)))

    def _generate_name(self):
        for _ in range(100):
            name = self._pick(PREFIXES) + self._pick(SUFFIXES)
            if name not in self.used_names:
                self.used_names.add(name)
                return name
        name = self._pick(PREFIXES) + self._pick(SUFFIXES) + str(self.rng.randint(1, 99))
        self.used_names.add(name)
        return name

    def _generate_god(self, is_first=False):
        name = self._generate_name()
        title = self._pick(TITLES)

        # Primary domain
        if is_first:
            cosmic = ["Sky", "Sea", "Earth", "Fire", "Time", "Fate", "Light", "Darkness"]
            available = [d for d in cosmic if d not in self.used_domains]
            if not available:
                available = [d for d in PRIMARY_DOMAINS if d not in self.used_domains]
            primary = self.rng.choice(available) if available else self._pick(PRIMARY_DOMAINS)
        else:
            available = [d for d in PRIMARY_DOMAINS if d not in self.used_domains]
            primary = self.rng.choice(available) if available else self._pick(PRIMARY_DOMAINS)
        self.used_domains.add(primary)

        # Secondary domains
        secondary_available = [d for d in SECONDARY_DOMAINS if d not in self.used_domains]
        n_secondary = self.rng.randint(1, 3)
        secondaries = []
        for d in self._pick_n(secondary_available, n_secondary):
            self.used_domains.add(d)
            secondaries.append(d)

        symbol = self._pick(SYMBOLS)

        # Description
        wraths = ["flame", "shadow", "mist", "starlight", "storm clouds",
                   "silver light", "golden dust", "frost", "deep water", "autumn leaves"]
        eyes = ["burning", "closed", "shifting", "endless", "ancient", "sorrowful"]
        forms = ["an ageless child", "a towering silhouette",
                 "a shifting form of many faces", "a figure with too many hands",
                 "a being of pure light", "a shadow with eyes"]
        sounds = ["distant thunder", "running water", "a single note held forever",
                  "whispered prayers", "cracking stone", "falling leaves"]
        effects = ["flowers bloom", "time slows", "shadows deepen", "rivers reverse",
                   "birds fall silent", "stars flicker"]

        desc_choices = [
            (name + " appears as a figure wreathed in " + self._pick(wraths) +
             ", their eyes " + self._pick(eyes) + ". They carry " + symbol +
             " and are never seen without it."),
            (name + " manifests as " + self._pick(forms) +
             ", always accompanied by the sound of " + self._pick(sounds) +
             ". Their symbol, " + symbol + ", marks their presence."),
            ("When " + name + " walks the world, " + self._pick(effects) +
             ". They are known by " + symbol + ", and those who encounter them are forever changed."),
        ]
        description = self._pick(desc_choices)

        # Personality
        temperaments = [
            "Calm and implacable", "Fierce and quick-tempered",
            "Gentle but unyielding", "Cold and calculating",
            "Warm and generous", "Wild and unpredictable",
            "Patient and watchful", "Mirthful and dangerous",
        ]
        demands = [
            "demands absolute devotion", "cares little for worship",
            "rewards cleverness", "tests mortals endlessly",
            "answers only honest prayers", "enjoys chaos",
            "protects the forgotten", "speaks only in riddles",
        ]
        personality_traits = [
            "slow to anger but terrible in wrath",
            "quick to laugh and quicker to strike",
            "given to long silences and sudden pronouncements",
            "easily amused and dangerously unpredictable",
            "melancholic and wise",
            "joyful but unforgiving of betrayal",
        ]

        personality = self._pick(temperaments) + ", " + name + " " + self._pick(demands) + "."
        personality += " " + name + " is " + self._pick(personality_traits) + "."

        # Worship practice
        offering = self._pick(OFFERINGS)
        practice = self._pick(WORSHIP_PRACTICES).replace("{god}", name).replace("{offering}", offering)

        # Taboos
        animals = ["deer", "boar", "fish", "horse", "serpent", "raven", "wolf"]
        colors = ["red", "white", "black", "gold", "blue", "green"]
        taboo_conditions = [
            "during a storm", "while facing north", "after dark",
            "in the presence of the dead", "within sight of the sea",
            "on the longest day", "inside a closed room",
        ]
        taboo_actions = [
            ("eat the flesh of " + self._pick(animals)),
            ("wear the color " + self._pick(colors)),
            "sleep under an open sky", "look upon a mirror",
            "carry iron", "walk backward", "drink from a vessel of clay",
        ]
        taboo_curses = [
            "endless wanderlust", "the loss of one's name", "blindness",
            "deafness", "insomnia", "the inability to keep oaths",
            "an eternal thirst",
        ]

        taboo_options = [
            "It is forbidden to speak " + name + "'s name " + self._pick(taboo_conditions) + ".",
            "Those who serve " + name + " must never " + self._pick(taboo_actions) + ".",
            "To betray " + name + "'s trust is to invite " + self._pick(taboo_curses) + ".",
        ]
        taboo = self._pick(taboo_options)

        return God(
            name=name,
            title=title,
            primary_domain=primary,
            secondary_domains=secondaries,
            symbol=symbol,
            description=description,
            personality=personality,
            worship_practice=practice,
            taboos=taboo,
        )

    def _generate_relationships(self):
        relationships = []
        n_relationships = self.rng.randint(
            self.num_gods - 1,
            min(self.num_gods * 2, len(self.gods) * (len(self.gods) - 1) // 2)
        )
        pairs_used = set()

        for _ in range(n_relationships):
            a, b = self.rng.sample(range(len(self.gods)), 2)
            pair = tuple(sorted([self.gods[a].name, self.gods[b].name]))
            attempts = 0
            while pair in pairs_used and attempts < 50:
                a, b = self.rng.sample(range(len(self.gods)), 2)
                pair = tuple(sorted([self.gods[a].name, self.gods[b].name]))
                attempts += 1
            if pair in pairs_used:
                continue
            pairs_used.add(pair)

            type_a, type_b = self._pick(RELATIONSHIP_TYPES)
            god_a = self.gods[a]
            god_b = self.gods[b]

            # Build story without nested f-strings with backslashes
            story_parts = [
                ("When " + god_a.name + " first met " + god_b.name + ", " +
                 self._pick([
                     "they recognized something of themselves",
                     "the sky trembled",
                     "an unbreakable bond formed",
                     "they laughed at the same joke",
                     "neither would yield ground",
                     "they wept with recognition",
                 ]) + ". " + god_a.name + " became " + type_a + " to " +
                 god_b.name + ", and this bond has shaped the " +
                 self._pick(["world", "heavens", "seasons", "fates of mortals", "tides", "course of history"]) +
                 " ever since."),
                (god_a.name + " and " + god_b.name + " " +
                 self._pick(["have always been", "became", "were forged as"]) +
                 " " + type_a + " and " + type_b + ". " +
                 self._pick(["Their bond is", "This relationship is", "This connection remains"]) +
                 " " + self._pick(["unbreakable", "tenuous at best", "the source of endless conflict",
                                   "a mystery even to other gods", "the foundation of several myths",
                                   "tested regularly"]) + "."),
                ("The bond of " + type_a + "/" + type_b + " between " +
                 god_a.name + " and " + god_b.name + " began " +
                 self._pick([
                     "at the dawn of the world",
                     "during the War of " + self._pick(WAR_NAMES),
                     "when a mortal prayer went unanswered",
                     "in a moment of betrayal",
                     "through a shared secret",
                     "by accident",
                 ]) + ". " +
                 self._pick(["It endures.", "It has never fully healed.",
                             "It grows stronger with each age.",
                             "It is the reason the seasons turn."])),
            ]
            story = self._pick(story_parts)

            relationships.append(Relationship(
                god_a=god_a.name,
                god_b=god_b.name,
                type_a=type_a,
                type_b=type_b,
                story=story,
            ))

        return relationships

    def _generate_creation_myth(self):
        template, placeholders = self._pick(CREATION_MYTHS)
        kwargs = {}
        if "void" in placeholders:
            kwargs["void"] = self._pick(VOID_NAMES)
        if "first_god" in placeholders:
            kwargs["first_god"] = self.gods[0].full_title
        if "force_a" in placeholders:
            forces = self._pick(PRIMEVAL_FORCES).split(" and ")
            kwargs["force_a"] = forces[0]
            kwargs["force_b"] = forces[1]
        return template.format(**kwargs)

    def _generate_cosmology(self):
        template = self._pick(COSMOLOGY_TEMPLATES)
        gods_shuffled = list(self.gods)
        self.rng.shuffle(gods_shuffled)

        replacements = {}
        placeholders = [
            "support", "medium", "sky_god", "underworld_god",
            "underworld", "sky", "ancient", "singer",
            "realm_a", "realm_b", "realm_c", "turner",
        ]
        god_idx = 0
        for ph in placeholders:
            if "{" + ph + "}" in template:
                if ph in ("support", "medium", "underworld", "sky",
                          "realm_a", "realm_b", "realm_c"):
                    replacements[ph] = self._pick([
                        "a sleeping titan", "the Great Serpent",
                        "a pillar of unbroken ice", "the World Tree",
                        "an ocean of stars", "the Dreaming Stone",
                        "the Ashen King", "a chasm of forgotten names",
                        "the Endless Stair", "a mirror of all possibilities",
                        "the Frozen River", "the Mountain of Echoes",
                        "the Plain of Salt", "the Forest of Shadows",
                    ])
                elif ph in ("sky_god", "underworld_god", "ancient", "singer", "turner"):
                    if god_idx < len(gods_shuffled):
                        replacements[ph] = gods_shuffled[god_idx].full_title
                        god_idx += 1
                    else:
                        replacements[ph] = self.gods[0].full_title

        return template.format(**replacements)

    def _generate_sacred_narratives(self):
        import re
        narratives = []
        n_narratives = self.rng.randint(2, 4)
        chosen = self._pick_n(SACRED_NARRATIVE_TEMPLATES, n_narratives)

        for title_template, body_template, placeholders in chosen:
            kwargs = {}
            gods_shuffled = list(self.gods)
            self.rng.shuffle(gods_shuffled)
            god_idx = 0

            for ph in placeholders:
                if ph in ("thief", "owner", "god_a", "god_b", "binder",
                          "bound_one", "descender", "betrayer", "betrayed"):
                    if god_idx < len(gods_shuffled):
                        kwargs[ph] = gods_shuffled[god_idx].name
                        god_idx += 1
                    else:
                        kwargs[ph] = self.gods[0].name
                elif ph == "war_name":
                    kwargs[ph] = self._pick(WAR_NAMES)
                elif ph == "artifact":
                    kwargs[ph] = self._pick(ARTIFACT_NAMES)
                elif ph == "cover":
                    kwargs[ph] = self._pick(COVERS)
                elif ph == "explanation":
                    kwargs[ph] = self._pick(EXPLANATIONS)
                elif ph == "war_name":
                    kwargs[ph] = self._pick(WAR_NAMES)
                elif ph == "domain":
                    available = [g.primary_domain for g in self.gods]
                    kwargs[ph] = self._pick(available)
                elif ph == "duration":
                    kwargs[ph] = self._pick(DURATIONS)
                elif ph == "marker":
                    kwargs[ph] = self._pick(MARKERS)
                elif ph == "chains":
                    kwargs[ph] = self._pick(CHAINS)
                elif ph == "prison":
                    kwargs[ph] = self._pick(PRISONS)
                elif ph == "sign":
                    kwargs[ph] = self._pick(SIGNS)
                elif ph == "fear":
                    kwargs[ph] = self._pick(FEARS)
                elif ph == "place":
                    kwargs[ph] = self._pick(PLACE_NAMES)
                elif ph == "consequence":
                    kwargs[ph] = self._pick(EXPLANATIONS)
                elif ph == "disguise":
                    kwargs[ph] = self._pick(DISGUISES)
                elif ph == "gift":
                    kwargs[ph] = self._pick(GIFTS)

            title_names = re.findall(r'\{(\w+)\}', title_template)
            title_kwargs = {k: v for k, v in kwargs.items() if k in title_names}

            narratives.append({
                "title": title_template.format(**title_kwargs),
                "story": body_template.format(**kwargs),
            })

        return narratives

    def _generate_great_taboo(self):
        god = self.rng.choice(self.gods)
        offering = self._pick(OFFERINGS)
        season = self._pick(["the longest night", "the equinox", "the dark of the moon", "the first frost"])

        taboo_options = [
            ("Above all, mortals must never " +
             self._pick([
                 "speak the true name of " + god.name,
                 "enter the temple of " + god.name + " uninvited",
                 "offer " + offering + " to " + god.name,
                 "sleep at a crossroads during " + season,
             ]) + ". To do so invites " +
             self._pick([
                 "madness", "the dissolution of the self",
                 "an eternity of wandering",
                 "the direct wrath of " + god.name,
                 "the unraveling of fate",
             ]) + "."),
            ("The greatest taboo is " +
             self._pick([
                 "to question the order set by " + god.name,
                 "to attempt to raise the dead",
                 "to shed blood in a sacred grove",
                 "to break an oath sworn by " + god.name,
             ]) + ". Those who transgress find that " +
             self._pick([
                 "the sky no longer recognizes them",
                 "their shadow detaches and hunts them",
                 "they age a year for every day",
                 "no door will open for them again",
             ]) + "."),
            ("It is said that " +
             self._pick([
                 "the last god to be forgotten",
                 "the first lie ever told",
                 "the name of the world before it was made",
                 "the sound of the cosmos cracking",
             ]) + " must never be " +
             self._pick([
                 "spoken aloud", "written down",
                 "remembered", "sought after",
             ]) + ", for " +
             self._pick([
                 "the world itself would end",
                 "all the gods would turn their faces away",
                 "the boundary between realms would dissolve",
                 "time would begin to run backwards",
             ]) + "."),
        ]
        return self._pick(taboo_options)

    def generate(self):
        # Generate gods
        self.gods = []
        for i in range(self.num_gods):
            self.gods.append(self._generate_god(is_first=(i == 0)))

        # Generate pantheon name
        pantheon_names = [
            "The " + self._pick(["Eternal", "Shattered", "Hidden", "Iron", "Silver",
                                  "Golden", "Ancient", "Forgotten", "Burning", "Silent",
                                  "Wandering", "Crowned"]) + " Pantheon of " + self.gods[0].name,
            "The Court of " + self._pick(["Thorns", "Stars", "Ash", "Mirrors",
                                           "Flames", "Shadows", "Echoes", "Dreams",
                                           "Storms", "Silence"]),
            "The " + self._pick(["Divine", "Sacred", "Exalted", "Primordial", "Celestial"]) +
            " House of " + self.gods[self.rng.randint(0, len(self.gods) - 1)].name,
            "The " + self._pick(["Lords", "Sovereigns", "Keepers", "Makers", "Watchers", "Shapers"]) +
            " of " + self._pick(["the Heights", "the Deep", "All Things",
                                  "the Turning World", "the Boundless Realm", "the Eternal Cycle"]),
        ]
        pantheon_name = self._pick(pantheon_names)

        # Generate relationships
        relationships = self._generate_relationships()

        # Generate creation myth
        creation_myth = self._generate_creation_myth()

        # Generate cosmology
        cosmology = self._generate_cosmology()

        # Generate sacred narratives
        sacred_narratives = self._generate_sacred_narratives()

        # Generate great taboo
        great_taboo = self._generate_great_taboo()

        return Mythology(
            pantheon_name=pantheon_name,
            gods=self.gods,
            relationships=relationships,
            creation_myth=creation_myth,
            cosmology=cosmology,
            sacred_narratives=sacred_narratives,
            great_taboo=great_taboo,
        )


# ──────────────────────────────────────────────
# Rendering
# ──────────────────────────────────────────────

def render_markdown(myth):
    """Render a Mythology as a beautiful Markdown document."""
    lines = []

    # Header
    lines.append("# " + myth.pantheon_name)
    lines.append("")
    lines.append("---")
    lines.append("")

    # Creation myth
    lines.append("## The Creation")
    lines.append("")
    lines.append(myth.creation_myth)
    lines.append("")

    # Cosmology
    lines.append("## The Shape of the Cosmos")
    lines.append("")
    lines.append(myth.cosmology)
    lines.append("")

    # The Great Taboo
    lines.append("## The Great Taboo")
    lines.append("")
    lines.append(myth.great_taboo)
    lines.append("")

    # Gods
    lines.append("## The Gods")
    lines.append("")
    for god in myth.gods:
        lines.append("### " + god.full_title)
        lines.append("")
        lines.append("**Domain:** " + god.primary_domain)
        if god.secondary_domains:
            lines.append("**Also:** " + ", ".join(god.secondary_domains))
        lines.append("**Symbol:** " + god.symbol.capitalize())
        lines.append("")
        lines.append(god.description)
        lines.append("")
        lines.append(god.personality)
        lines.append("")
        lines.append("*Worship:* " + god.worship_practice + ".")
        lines.append("")
        lines.append("*Taboo:* " + god.taboos)
        lines.append("")

    # Relationships
    lines.append("## Divine Relationships")
    lines.append("")
    for rel in myth.relationships:
        lines.append("### " + rel.god_a + " \u2014 " + rel.god_b)
        lines.append("")
        lines.append("**" + rel.god_a + "** is *" + rel.type_a + "* to **" +
                     rel.god_b + "**; " +
                     "**" + rel.god_b + "** is *" + rel.type_b + "* to **" +
                     rel.god_a + "**.")
        lines.append("")
        lines.append(rel.story)
        lines.append("")

    # Sacred narratives
    lines.append("## Sacred Narratives")
    lines.append("")
    for nar in myth.sacred_narratives:
        lines.append("### " + nar["title"])
        lines.append("")
        lines.append(nar["story"])
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*This mythology was procedurally generated with " +
                 str(len(myth.gods)) + " gods, " +
                 str(len(myth.relationships)) + " divine relationships, and " +
                 str(len(myth.sacred_narratives)) + " sacred narratives.*")

    return "\n".join(lines)


def render_json(myth):
    """Render a Mythology as JSON."""
    return json.dumps(myth.to_dict(), indent=2, ensure_ascii=False)


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Procedural Mythology Generator \u2014 create complete fictional pantheons",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mythology_generator.py                    # Default: 7 gods, random seed
  python mythology_generator.py --gods 5           # Smaller pantheon
  python mythology_generator.py --gods 12 --seed 42  # Deterministic
  python mythology_generator.py --format json      # JSON output
  python mythology_generator.py --output myth.md   # Save to file
""",
    )
    parser.add_argument("--gods", "-g", type=int, default=7,
                        help="Number of gods to generate (3-12, default: 7)")
    parser.add_argument("--seed", "-s", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--format", "-f", choices=["markdown", "json"], default="markdown",
                        help="Output format (default: markdown)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output file path (default: stdout)")

    args = parser.parse_args()

    generator = MythologyGenerator(seed=args.seed, num_gods=args.gods)
    mythology = generator.generate()

    if args.format == "markdown":
        output = render_markdown(mythology)
    else:
        output = render_json(mythology)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print("Written to " + args.output)
    else:
        print(output)


if __name__ == "__main__":
    main()