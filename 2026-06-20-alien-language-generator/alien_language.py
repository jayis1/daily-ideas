#!/usr/bin/env python3
"""
Procedural Alien Language Generator
=====================================
Generates complete constructed (con)langs with unique phonology, morphology,
grammar rules, vocabulary, and a visual writing system rendered as ASCII art.

Each run produces a self-consistent language with:
- A named language with cultural flavor
- Phoneme inventory and syllable structure
- Grammar rules (word order, case system, tense, plurality)
- A lexicon of ~200 words
- A glyph-based writing system with procedural ASCII symbols
- The ability to translate English sentences into the alien language
- Written text rendered in the alien script
- Language evolution across generations (sound changes)
- Reverse translation (alien → English)
- Poetry generation in structured verse forms
"""

import random
import hashlib
import json
import sys
import copy
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

VERSION = "2.1.0"

# ─── Phoneme Pools ───────────────────────────────────────────────────────────

CONSONANTS_BY_MANNER = {
    "stops": ["p", "b", "t", "d", "k", "g", "q", "ʔ"],
    "fricatives": ["f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ", "h", "x"],
    "nasals": ["m", "n", "ŋ", "ɲ"],
    "approximants": ["l", "r", "ʎ", "w", "j"],
    "affricates": ["tʃ", "dʒ", "ts", "dz"],
}

VOWELS = {
    "close": ["i", "y", "ɨ", "u"],
    "close_mid": ["e", "ø", "ə", "o"],
    "open_mid": ["ɛ", "œ", "ʌ", "ɔ"],
    "open": ["a", "æ", "ɑ"],
}

WORD_ORDERS = ["SVO", "SOV", "VSO", "VOS", "OVS", "OSV"]

CASE_SYSTEMS = {
    "none": [],
    "nominative_accusative": ["NOM", "ACC"],
    "ergative_absolutive": ["ERG", "ABS"],
    "tripartite": ["NOM", "ACC", "ERG"],
}

TENSE_SYSTEMS = {
    "binary": ["PRES", "PAST"],
    "ternary": ["PRES", "PAST", "FUT"],
    "quaternary": ["PRES", "PAST", "FUT", "HAB"],
}

NUMBER_SYSTEMS = {
    "singular_only": [],
    "dual": ["SG", "DU"],
    "plural": ["SG", "PL"],
    "trial": ["SG", "DU", "PL"],
}

CULTURAL_FLAVORS = [
    ("aquatic", "ocean, water, deep, tide, wave, current, shore, coral, pearl, abyss"),
    ("desert", "sand, sun, heat, wind, dune, oasis, storm, dust, mirage, stone"),
    ("forest", "tree, root, leaf, moss, shadow, canopy, grove, bark, fern, spore"),
    ("mountain", "peak, stone, ice, echo, cliff, summit, frost, ridge, vale, thunder"),
    ("cosmic", "star, void, light, orbit, dust, nebula, pulse, flare, drift, abyss"),
    ("volcanic", "fire, ash, lava, heat, eruption, magma, obsidian, steam, crack, glow"),
    ("arctic", "ice, snow, frost, aurora, white, crystal, cold, wind, freeze, glitter"),
    ("swamp", "mud, fog, rot, vine, mist, decay, bloom, stalk, murk, crawl"),
]

GLYPH_STROKES = [
    "╱", "╲", "─", "│", "╮", "╭", "╯", "╰", "┼", "┤", "├", "┬", "┴",
    "╔", "╗", "╚", "╝", "║", "═", "░", "▒", "▓", "●", "○", "◆", "◇",
    "▲", "△", "▼", "▽", "■", "□", "⬡", "⬢", "⊛", "⊙", "⊘", "⊕",
]

GLYPH_FILL = ["░", "▒", "▓", "·", "∘", "×"]

# ─── Sound Change Rules ──────────────────────────────────────────────────────

SOUND_CHANGE_TYPES = [
    "lenition",       # consonant weakening (p→b, t→d, k→g)
    "fortition",      # consonant strengthening (b→p, d→t, g→k)
    "assimilation",   # consonant becomes more like neighbor
    "vowel_shift",    # vowels shift up/down the height chart
    "diphthongize",   # monophthong → diphthong
    "merge",          # two phonemes merge into one
    "insertion",      # insert a default vowel between consonants
]

# Lenition pairs: voiceless → voiced
LENITION_MAP = {
    "p": "b", "t": "d", "k": "g", "q": "ɢ", "f": "v", "θ": "ð",
    "s": "z", "ʃ": "ʒ", "tʃ": "dʒ", "ts": "dz",
}

# Fortition pairs: voiced → voiceless
FORTITION_MAP = {v: k for k, v in LENITION_MAP.items() if len(v) == 1}

# Vowel shift chains
VOWEL_SHIFT_UP = {"a": "æ", "æ": "ɛ", "ɛ": "e", "e": "i", "ʌ": "ɨ", "ɔ": "o", "o": "u", "ə": "ɨ"}
VOWEL_SHIFT_DOWN = {v: k for k, v in VOWEL_SHIFT_UP.items()}


def weighted_choice(options, weights=None):
    """Choose from options with optional weights."""
    if weights:
        total = sum(weights)
        r = random.random() * total
        cumulative = 0
        for opt, w in zip(options, weights):
            cumulative += w
            if r <= cumulative:
                return opt
        return options[-1]
    return random.choice(options)


def make_seed(s: str) -> int:
    """Convert a string seed to an integer hash."""
    return int(hashlib.md5(s.encode()).hexdigest(), 16) % (2**32)


# ─── Glyph Generator ─────────────────────────────────────────────────────────

class GlyphGenerator:
    """Generates unique ASCII-art glyphs for each phoneme."""

    def __init__(self, seed: int, phonemes: List[str]):
        self.rng = random.Random(seed)
        self.glyphs: Dict[str, List[str]] = {}
        self._generate_all(phonemes)

    def _generate_all(self, phonemes: List[str]):
        for ph in phonemes:
            self.glyphs[ph] = self._make_glyph(ph)

    def _make_glyph(self, phoneme: str) -> List[str]:
        rng = random.Random(hash(phoneme) + self.rng.randint(0, 99999))
        h, w = 3, 3
        grid = [[" " for _ in range(w)] for _ in range(h)]
        # Choose 2-5 strokes
        n_strokes = rng.randint(2, 5)
        positions = rng.sample([(r, c) for r in range(h) for c in range(w)], min(n_strokes, 9))
        for r, c in positions:
            grid[r][c] = rng.choice(GLYPH_STROKES)
        # Maybe add a fill character in center
        if rng.random() < 0.4:
            grid[1][1] = rng.choice(GLYPH_FILL)

        # Add border with some probability
        if rng.random() < 0.5:
            for c in range(w):
                if grid[0][c] == " ":
                    grid[0][c] = "━" if rng.random() < 0.5 else "─"
                if grid[h - 1][c] == " ":
                    grid[h - 1][c] = "━" if rng.random() < 0.5 else "─"
            for r in range(h):
                if grid[r][0] == " ":
                    grid[r][0] = "┃" if rng.random() < 0.5 else "│"
                if grid[r][w - 1] == " ":
                    grid[r][w - 1] = "┃" if rng.random() < 0.5 else "│"

        lines = ["".join(row) for row in grid]
        return lines

    def render_phoneme(self, phoneme: str) -> List[str]:
        """Render a single phoneme glyph, returning 3 lines."""
        return self.glyphs.get(phoneme, [" ? ", " ? ", " ? "])

    def render_syllable(self, syllable: str, phoneme_map: Dict[str, str]) -> List[str]:
        """Render a syllable by placing glyph columns side by side."""
        glyphs = []
        for ch in syllable:
            ph = phoneme_map.get(ch)
            if ph and ph in self.glyphs:
                glyphs.append(self.glyphs[ph])
            else:
                glyphs.append([" · ", " · ", " · "])
        if not glyphs:
            return ["   ", "   ", "   "]
        # Combine horizontally with 1-char gap
        result = []
        for row_idx in range(3):
            line = ""
            for g in glyphs:
                line += g[row_idx] + " "
            result.append(line.rstrip())
        return result

    def render_word(self, word: str, syllables: List[str], phoneme_map: Dict[str, str]) -> List[str]:
        """Render a full word as stacked syllable blocks."""
        rows = []
        for syl in syllables:
            syl_render = self.render_syllable(syl, phoneme_map)
            rows.extend(syl_render)
            rows.append(" " * max(len(r) for r in syl_render))  # blank line between syllables
        return rows


# ─── Language Generator ──────────────────────────────────────────────────────

class AlienLanguage:
    """A procedurally generated alien language."""

    def __init__(self, seed: Optional[int] = None, name: Optional[str] = None):
        if seed is not None:
            self.seed = seed
        else:
            self.seed = random.randint(0, 2**32 - 1)
        self.rng = random.Random(self.seed)

        # Cultural flavor
        flavor_name, flavor_words = self.rng.choice(CULTURAL_FLAVORS)
        self.culture = flavor_name
        self.cultural_words = [w.strip() for w in flavor_words.split(",")]

        # Language name
        if name:
            self.name = name
        else:
            self.name = self._generate_name()

        # Phonology
        self._build_phonology()

        # Grammar
        self._build_grammar()

        # Morphology
        self._build_morphology()

        # Vocabulary
        self._build_vocabulary()

        # Glyphs
        self.glyph_gen = GlyphGenerator(self.seed + 9999, self.all_phonemes)

        # Evolution history
        self.evolution_log: List[str] = []

    def _generate_name(self) -> str:
        """Generate a random language name."""
        templates = [
            lambda: self._make_syllable().capitalize() + self._make_syllable(),
            lambda: self._make_syllable().capitalize() + "'" + self._make_syllable(),
            lambda: self._make_syllable().capitalize() + "i" + self._make_syllable(),
            lambda: self._make_syllable().capitalize() + "u" + self._make_syllable() + self._make_syllable(),
        ]
        return self.rng.choice(templates)()

    def _make_syllable(self) -> str:
        """Generate a simple syllable for name generation."""
        c = self.rng.choice(["b", "k", "l", "r", "t", "s", "m", "n", "z", "v", "zh", "th", "q"])
        v = self.rng.choice(["a", "e", "i", "o", "u", "ai", "ei", "ou"])
        return c + v

    def _build_phonology(self):
        """Build the phoneme inventory and syllable structure."""
        # Pick consonant inventory
        n_manners = self.rng.randint(2, 4)
        chosen_manners = self.rng.sample(list(CONSONANTS_BY_MANNER.keys()), n_manners)
        self.consonants = []
        for manner in chosen_manners:
            pool = CONSONANTS_BY_MANNER[manner]
            n = self.rng.randint(2, min(5, len(pool)))
            self.consonants.extend(self.rng.sample(pool, n))
        self.consonants = sorted(set(self.consonants))

        # Pick vowel inventory
        n_vowel_classes = self.rng.randint(2, 4)
        chosen_classes = self.rng.sample(list(VOWELS.keys()), n_vowel_classes)
        self.vowels = []
        for vc in chosen_classes:
            self.vowels.append(self.rng.choice(VOWELS[vc]))
        self.vowels = list(set(self.vowels))

        # Simplified phoneme representation (single chars)
        self.char_to_phoneme: Dict[str, str] = {}
        self.phoneme_to_char: Dict[str, str] = {}
        idx = 0
        all_chars = list("bcdfghjklmnpqrstvwxyz") + list("aeiou")
        self.all_phonemes = self.consonants + self.vowels
        for ph in self.all_phonemes:
            if len(ph) == 1:
                self.char_to_phoneme[ph] = ph
                self.phoneme_to_char[ph] = ph
            else:
                # Map multi-char phonemes to a single display char
                ch = all_chars[idx % len(all_chars)]
                self.char_to_phoneme[ch] = ph
                self.phoneme_to_char[ph] = ch
                idx += 1

        # Syllable structure (avoid bare "V" patterns that produce single-char words)
        self.syllable_patterns = self.rng.choice([
            ["CV"],                              # Simple
            ["CV", "CVC"],                        # Medium
            ["CV", "CVC", "CCV"],                 # Complex (removed bare V)
            ["CV", "VC", "CVC"],                   # Open (removed bare V)
        ])

    def _build_grammar(self):
        """Build the grammar rules."""
        self.word_order = self.rng.choice(WORD_ORDERS)
        self.case_system = self.rng.choice(list(CASE_SYSTEMS.keys()))
        self.cases = CASE_SYSTEMS[self.case_system]
        self.tense_system = self.rng.choice(list(TENSE_SYSTEMS.keys()))
        self.tenses = TENSE_SYSTEMS[self.tense_system]
        self.number_system = self.rng.choice(list(NUMBER_SYSTEMS.keys()))
        self.numbers = NUMBER_SYSTEMS[self.number_system]
        # Adjective placement
        self.adj_before_noun = self.rng.random() < 0.5
        # Possession
        self.possession_suffix = self.rng.random() < 0.6
        # Question particle
        self.question_particle = self._gen_morpheme() if self.rng.random() < 0.5 else None

    def _build_morphology(self):
        """Build the morphological affixes."""
        self.case_affixes = {}
        for case in self.cases:
            self.case_affixes[case] = self._gen_morpheme()

        self.tense_affixes = {}
        for tense in self.tenses:
            self.tense_affixes[tense] = self._gen_morpheme()

        self.number_affixes = {}
        for num in self.numbers:
            self.number_affixes[num] = self._gen_morpheme()

        # Derivational morphology
        self.nominalizer = self._gen_morpheme() if self.rng.random() < 0.7 else None
        self.verbalizer = self._gen_morpheme() if self.rng.random() < 0.5 else None
        self.adjectivizer = self._gen_morpheme() if self.rng.random() < 0.6 else None

        self.prefix_mode = self.rng.random() < 0.5  # True=prefix, False=suffix
        # Possessive marker (used when translating English possessives like "water's")
        self.possessive_affix = self._gen_morpheme()

    def _gen_morpheme(self) -> str:
        """Generate a short morpheme for affixes."""
        pattern = self.rng.choice(self.syllable_patterns)
        morpheme = ""
        for slot in pattern:
            if slot == "C":
                morpheme += self.rng.choice(self.consonants[:8]) if len(self.consonants) > 8 else self.rng.choice(self.consonants)
            elif slot == "V":
                morpheme += self.rng.choice(self.vowels)
            elif slot == "CC":
                c1 = self.rng.choice(self.consonants[:6]) if len(self.consonants) > 6 else self.rng.choice(self.consonants)
                c2 = self.rng.choice(self.consonants[:6]) if len(self.consonants) > 6 else self.rng.choice(self.consonants)
                morpheme += c1 + c2
        return morpheme

    def _gen_possessive_marker(self) -> str:
        """Return the possessive affix for this language."""
        return self.possessive_affix

    def _gen_word_form(self) -> str:
        """Generate a random word form using the language's phonology."""
        n_syl = self.rng.choices([1, 2, 3], weights=[3, 5, 2])[0]
        syllables = []
        for _ in range(n_syl):
            pattern = self.rng.choice(self.syllable_patterns)
            syl = ""
            for slot in pattern:
                if slot == "C" or slot == "CC":
                    cs = self.consonants[:8] if len(self.consonants) > 8 else self.consonants
                    if slot == "CC":
                        syl += self.rng.choice(cs) + self.rng.choice(cs)
                    else:
                        syl += self.rng.choice(cs)
                elif slot == "V":
                    syl += self.rng.choice(self.vowels)
            syllables.append(syl)
        return "".join(syllables)

    def _build_vocabulary(self):
        """Build the full vocabulary from semantic categories."""
        # Core vocabulary categories
        categories = {
            "pronouns": ["I", "you", "he", "she", "it", "we", "they", "this", "that"],
            "nouns_basic": ["person", "hand", "eye", "head", "water", "fire", "earth", "sky",
                           "day", "night", "sun", "moon", "star", "tree", "stone", "food"],
            "nouns_cultural": self.cultural_words,
            "verbs_basic": ["be", "have", "do", "go", "come", "see", "hear", "say", "eat", "give",
                           "make", "know", "want", "love", "think", "take", "find", "lose"],
            "verbs_cultural": ["swim", "dive", "flow", "rise", "fall", "grow", "build", "break"],
            "adjectives": ["big", "small", "good", "bad", "hot", "cold", "old", "new",
                          "fast", "slow", "strong", "weak", "bright", "dark", "deep", "high"],
            "numbers_word": ["one", "two", "three", "four", "five", "many", "all", "none"],
            "adverbs": ["very", "not", "also", "here", "there", "now", "then", "always", "never"],
            "prepositions": ["in", "on", "at", "with", "from", "to", "of", "about"],
            "conjunctions": ["and", "or", "but", "if", "because", "when", "while"],
        }

        self.vocabulary: Dict[str, Dict[str, str]] = {}
        self.reverse_vocab: Dict[str, str] = {}

        used_forms = set()
        for cat, words in categories.items():
            self.vocabulary[cat] = {}
            for word in words:
                form = self._gen_word_form()
                # Ensure uniqueness
                attempts = 0
                while form in used_forms and attempts < 100:
                    form = self._gen_word_form()
                    attempts += 1
                used_forms.add(form)
                self.vocabulary[cat][word] = form
                self.reverse_vocab[form] = word

    def translate_word(self, english: str) -> Optional[str]:
        """Translate an English word to the alien language."""
        lower = english.lower()
        for cat in self.vocabulary:
            if lower in self.vocabulary[cat]:
                return self.vocabulary[cat][lower]
        return None

    def reverse_translate_word(self, alien: str) -> Optional[str]:
        """Translate an alien word back to English."""
        # Try exact match first
        if alien in self.reverse_vocab:
            return self.reverse_vocab[alien]
        # Try stripping affixes and looking up the stem
        # This is approximate — we try common affix positions
        for affix_dict in [self.case_affixes, self.tense_affixes, self.number_affixes]:
            for case, affix in affix_dict.items():
                if self.prefix_mode:
                    # Prefix: try removing it from the start
                    if alien.startswith(affix) and len(alien) > len(affix):
                        stem = alien[len(affix):]
                        if stem in self.reverse_vocab:
                            return self.reverse_vocab[stem]
                else:
                    # Suffix: try removing it from the end
                    if alien.endswith(affix) and len(alien) > len(affix):
                        stem = alien[:-len(affix)]
                        if stem in self.reverse_vocab:
                            return self.reverse_vocab[stem]
        return None

    def inflect_noun(self, base: str, case: Optional[str] = None, number: Optional[str] = None) -> str:
        """Apply case and number affixes to a noun."""
        word = base
        if number and number in self.number_affixes:
            if self.prefix_mode:
                word = self.number_affixes[number] + word
            else:
                word = word + self.number_affixes[number]
        if case and case in self.case_affixes:
            if self.prefix_mode:
                word = self.case_affixes[case] + word
            else:
                word = word + self.case_affixes[case]
        return word

    def inflect_verb(self, base: str, tense: Optional[str] = None) -> str:
        """Apply tense affix to a verb."""
        word = base
        if tense and tense in self.tense_affixes:
            if self.prefix_mode:
                word = self.tense_affixes[tense] + word
            else:
                word = word + self.tense_affixes[tense]
        return word

    def translate_sentence(self, english: str) -> str:
        """Translate an English sentence into the alien language.

        Handles articles, plurals, past tense, progressives, negation,
        and question particles.
        """
        raw = english.strip()
        # Detect question
        is_question = raw.endswith("?")
        # Strip punctuation for processing
        stripped = raw.rstrip(".!?").strip()

        words = stripped.lower().split()
        translated = []
        for w in words:
            # Skip English articles (the, a, an)
            if w in ("the", "a", "an"):
                continue
            # Handle negation: "not", "don't", "doesn't" → standalone negation word
            if w in ("not", "don't", "doesn't"):
                neg_word = self.translate_word("not")
                if neg_word:
                    translated.append(neg_word)
                else:
                    translated.append("[not]")
                continue

            alien_w = self.translate_word(w)
            if alien_w:
                translated.append(alien_w)
                continue
            # Handle possessives: "water's" → water + possessive marker
            if w.endswith("'s") and len(w) > 2:
                stem = w[:-2]
                alien_w = self.translate_word(stem)
                if alien_w:
                    if self.prefix_mode:
                        # Prefix possession marker
                        possessive_marker = self._gen_possessive_marker()
                        translated.append(possessive_marker + " " + alien_w)
                    else:
                        # Suffix possession marker
                        possessive_marker = self._gen_possessive_marker()
                        translated.append(alien_w + " " + possessive_marker)
                    continue
            # Handle plurals
            if w.endswith("es") and len(w) > 3:
                alien_w = self.translate_word(w[:-2])
                if alien_w:
                    translated.append(self.inflect_noun(alien_w, number="PL"))
                    continue
            if w.endswith("s") and len(w) > 2 and w not in ("is", "was", "has", "his", "as", "this"):
                alien_w = self.translate_word(w[:-1])
                if alien_w:
                    translated.append(self.inflect_noun(alien_w, number="PL"))
                    continue
            # Handle past tense
            if w.endswith("ed") and len(w) > 3:
                alien_w = self.translate_word(w[:-2])
                if alien_w:
                    translated.append(self.inflect_verb(alien_w, tense="PAST"))
                    continue
            # Handle progressive
            if w.endswith("ing") and len(w) > 4:
                alien_w = self.translate_word(w[:-3])
                if alien_w:
                    translated.append(self.inflect_verb(alien_w, tense="PRES"))
                    continue
            # Handle adverbs ending in -ly
            if w.endswith("ly") and len(w) > 3:
                adj = w[:-2]
                alien_w = self.translate_word(adj)
                if alien_w:
                    # Use the adverb form directly if we have it, else the adjective
                    translated.append(alien_w)
                    continue
            translated.append(f"[{w}]")

        result = " ".join(translated)
        if is_question and self.question_particle:
            result += " " + self.question_particle

        return result

    def reverse_translate(self, alien_text: str) -> str:
        """Attempt to translate alien language text back to English.

        This is approximate since the grammar is simplified.
        """
        words = alien_text.strip().split()
        translated = []
        for w in words:
            # Strip question particle
            if self.question_particle and w == self.question_particle:
                translated.append("?")
                continue
            en = self.reverse_translate_word(w)
            if en:
                translated.append(en)
            else:
                translated.append(f"[{w}]")
        return " ".join(translated)

    def render_word_glyphs(self, alien_word: str) -> str:
        """Render an alien word in the glyph writing system."""
        # Break word into phoneme-sized chunks for rendering.
        # Multi-char phonemes (like "ts", "dʒ") need to be matched as a unit.
        # Sort phonemes by length (longest first) to greedily match.
        sorted_phonemes = sorted(self.all_phonemes, key=len, reverse=True)

        chunks = []
        i = 0
        while i < len(alien_word):
            matched = False
            for ph in sorted_phonemes:
                if alien_word[i:i+len(ph)] == ph:
                    chunks.append(ph)
                    i += len(ph)
                    matched = True
                    break
            if not matched:
                # Unknown character, skip it
                chunks.append(alien_word[i])
                i += 1

        glyph_rows = []
        for chunk in chunks:
            ph = self.char_to_phoneme.get(chunk, chunk)
            g = self.glyph_gen.render_phoneme(ph)
            glyph_rows.append(g)

        if not glyph_rows:
            return alien_word

        # Combine horizontally
        lines = ["", "", ""]
        for g in glyph_rows:
            for row_idx in range(3):
                lines[row_idx] += g[row_idx] + " "

        return "\n".join(lines)

    def render_text_glyphs(self, text: str) -> str:
        """Render a full text in the glyph writing system."""
        words = text.split()
        all_blocks = []
        for word in words:
            # Skip punctuation and brackets for glyph rendering
            clean = word.strip(".,!?;:[]()\"'")
            if clean:
                block = self.render_word_glyphs(clean)
                all_blocks.append(block)

        return "\n\n".join(all_blocks)

    def generate_sample_text(self) -> str:
        """Generate a sample sentence in the alien language."""
        templates = [
            "{subj} {verb} {obj}.",
            "{subj} {verb}.",
            "The {adj} {noun} {verb} the {obj}.",
            "{subj} {verb} {adj} {obj}.",
            "{noun} and {noun} {verb} {obj}.",
        ]
        template = self.rng.choice(templates)

        nouns = list(self.vocabulary.get("nouns_basic", {}).values()) + \
                list(self.vocabulary.get("nouns_cultural", {}).values())
        verbs = list(self.vocabulary.get("verbs_basic", {}).values()) + \
                list(self.vocabulary.get("verbs_cultural", {}).values())
        adjs = list(self.vocabulary.get("adjectives", {}).values())

        if not nouns or not verbs:
            return "..."

        mapping = {
            "subj": self.rng.choice(nouns),
            "verb": self.rng.choice(verbs),
            "obj": self.rng.choice(nouns) if nouns else "",
            "adj": self.rng.choice(adjs) if adjs else "",
            "noun": self.rng.choice(nouns),
        }

        return template.format(**{k: v for k, v in mapping.items() if v})

    def generate_proverb(self) -> str:
        """Generate a proverb-like phrase."""
        noun_en = list(self.vocabulary.get("nouns_basic", {}).keys()) + \
                  list(self.vocabulary.get("nouns_cultural", {}).keys())
        verb_en = list(self.vocabulary.get("verbs_basic", {}).keys())
        adj_en = list(self.vocabulary.get("adjectives", {}).keys())

        templates = [
            "A {adj} {noun} always {verb}s.",
            "When the {noun} {verb}s, the {noun} {verb}s.",
            "The {adj} {noun} {verb}s, but the {adj} {noun} {verb}s.",
            "He who {verb}s a {noun} will {verb} a {noun}.",
            "Where there is {noun}, there is {noun}.",
        ]

        template = self.rng.choice(templates)
        mapping = {
            "noun": self.rng.choice(noun_en) if noun_en else "thing",
            "verb": self.rng.choice(verb_en) if verb_en else "be",
            "adj": self.rng.choice(adj_en) if adj_en else "good",
        }

        en_proverb = template.format(**mapping)
        alien_proverb = self.translate_sentence(en_proverb)
        return en_proverb + "\n→ " + alien_proverb

    def generate_poem(self) -> str:
        """Generate a structured poem in the alien language.

        Creates a verse with 2-4 stanzas, each with 2-4 lines,
        following a poetic template with rhyme-like alliteration.
        """
        noun_en = list(self.vocabulary.get("nouns_basic", {}).keys()) + \
                  list(self.vocabulary.get("nouns_cultural", {}).keys())
        verb_en = list(self.vocabulary.get("verbs_basic", {}).keys()) + \
                  list(self.vocabulary.get("verbs_cultural", {}).keys())
        adj_en = list(self.vocabulary.get("adjectives", {}).keys())

        if not noun_en or not verb_en:
            return "..."

        # Poetic templates per line
        line_templates = [
            "The {adj} {noun} {verb}s",
            "{noun} {verb}s {adj}",
            "In the {noun}, {noun} {verb}s",
            "{adj} {noun}, {adj} {noun}",
            "Where {noun} {verb}s",
            "{verb} the {noun}, {verb} the {noun}",
            "Through {adj} {noun}",
            "The {noun} {verb}s, the {noun} {verb}s",
        ]

        n_stanzas = self.rng.randint(2, 4)
        poem_en_lines = []
        poem_alien_lines = []

        for _ in range(n_stanzas):
            n_lines = self.rng.randint(2, 4)
            stanza_en = []
            stanza_alien = []
            # Pick a theme word for some coherence within a stanza
            theme_noun = self.rng.choice(noun_en)
            theme_adj = self.rng.choice(adj_en) if adj_en else "big"
            theme_verb = self.rng.choice(verb_en)

            for _ in range(n_lines):
                template = self.rng.choice(line_templates)
                # Use theme words with some probability
                noun = theme_noun if self.rng.random() < 0.4 else self.rng.choice(noun_en)
                adj = theme_adj if self.rng.random() < 0.3 else (self.rng.choice(adj_en) if adj_en else "big")
                verb = theme_verb if self.rng.random() < 0.3 else self.rng.choice(verb_en)

                # Format the verb (remove 's' for templates that don't need it)
                mapping = {"noun": noun, "adj": adj, "verb": verb}
                try:
                    en_line = template.format(**mapping)
                except (KeyError, IndexError):
                    en_line = f"The {adj} {noun} {verb}s"

                stanza_en.append(en_line)
                stanza_alien.append(self.translate_sentence(en_line))

            poem_en_lines.append("\n".join(stanza_en))
            poem_alien_lines.append("\n".join(stanza_alien))

        # Combine English and alien
        title_adjs = ["ancient", "sacred", "forgotten", "eternal", "mystical"]
        title_nouns = ["song", "chant", "verse", "hymn", "prayer"]
        title = f"The {self.rng.choice(title_adjs).capitalize()} {self.rng.choice(title_nouns).capitalize()} of {self.name}"

        result_lines = [f"══ {title} ══\n"]
        for i, (en_stanza, al_stanza) in enumerate(zip(poem_en_lines, poem_alien_lines)):
            result_lines.append(en_stanza)
            result_lines.append("")
            result_lines.append(al_stanza)
            if i < n_stanzas - 1:
                result_lines.append("\n---\n")

        return "\n".join(result_lines)

    def evolve(self, generations: int = 1, rng: Optional[random.Random] = None) -> "AlienLanguage":
        """Apply historical sound changes to evolve the language.

        Returns a new AlienLanguage derived from this one with accumulated
        sound changes. Each generation applies one change rule.
        Sound changes are also applied to morphological affixes and particles.
        """
        if rng is None:
            rng = random.Random()

        # Start from current vocabulary
        current_vocab = {}
        for cat, words in self.vocabulary.items():
            current_vocab[cat] = dict(words)

        # Also track morphological affixes for sound changes
        current_affixes = {}
        for name, affix in self.case_affixes.items():
            current_affixes[("case", name)] = affix
        for name, affix in self.tense_affixes.items():
            current_affixes[("tense", name)] = affix
        for name, affix in self.number_affixes.items():
            current_affixes[("number", name)] = affix
        if self.nominalizer:
            current_affixes[("deriv", "nominalizer")] = self.nominalizer
        if self.verbalizer:
            current_affixes[("deriv", "verbalizer")] = self.verbalizer
        if self.adjectivizer:
            current_affixes[("deriv", "adjectivizer")] = self.adjectivizer
        if self.possessive_affix:
            current_affixes[("deriv", "possessive")] = self.possessive_affix
        if self.question_particle:
            current_affixes[("particle", "question")] = self.question_particle

        # Helper to apply a replacement to both vocab and affixes
        def apply_replacement(target: str, replacement: str):
            """Apply a phoneme replacement to vocabulary and affixes."""
            for cat in current_vocab:
                for en, alien in list(current_vocab[cat].items()):
                    new_form = alien.replace(target, replacement)
                    if new_form != alien:
                        current_vocab[cat][en] = new_form
            for key in list(current_affixes.keys()):
                new_affix = current_affixes[key].replace(target, replacement)
                current_affixes[key] = new_affix

        # Helper to apply a replacement to first occurrence only
        def apply_first_replacement(target: str, replacement: str):
            """Apply a replacement to the first occurrence in each word/affix."""
            for cat in current_vocab:
                for en, alien in list(current_vocab[cat].items()):
                    if target in alien:
                        idx_pos = alien.index(target)
                        new_form = alien[:idx_pos] + replacement + alien[idx_pos + len(target):]
                        current_vocab[cat][en] = new_form
            for key in list(current_affixes.keys()):
                affix = current_affixes[key]
                if target in affix:
                    idx_pos = affix.index(target)
                    new_affix = affix[:idx_pos] + replacement + affix[idx_pos + len(target):]
                    current_affixes[key] = new_affix

        # Helper to apply insertion replacement
        def apply_insertion(old: str, new: str):
            """Apply an insertion replacement to vocabulary and affixes."""
            for cat in current_vocab:
                for en, alien in list(current_vocab[cat].items()):
                    if old in alien:
                        current_vocab[cat][en] = alien.replace(old, new)
            for key in list(current_affixes.keys()):
                if old in current_affixes[key]:
                    current_affixes[key] = current_affixes[key].replace(old, new)

        # Track changes
        changes_applied = []

        for gen in range(generations):
            # Pick a sound change type
            change_type = rng.choice(SOUND_CHANGE_TYPES)

            if change_type == "lenition":
                applicable = [c for c in self.consonants if c in LENITION_MAP]
                if not applicable:
                    continue
                target = rng.choice(applicable)
                replacement = LENITION_MAP[target]
                apply_replacement(target, replacement)
                changes_applied.append(f"Gen {gen+1}: Lenition /{target}/ → /{replacement}/")

            elif change_type == "fortition":
                applicable = [c for c in self.consonants if c in FORTITION_MAP]
                if not applicable:
                    continue
                target = rng.choice(applicable)
                replacement = FORTITION_MAP[target]
                apply_replacement(target, replacement)
                changes_applied.append(f"Gen {gen+1}: Fortition /{target}/ → /{replacement}/")

            elif change_type == "vowel_shift":
                direction = rng.choice(["up", "down"])
                shift_map = VOWEL_SHIFT_UP if direction == "up" else VOWEL_SHIFT_DOWN
                applicable = [v for v in self.vowels if v in shift_map]
                if not applicable:
                    continue
                target = rng.choice(applicable)
                replacement = shift_map[target]
                apply_replacement(target, replacement)
                changes_applied.append(f"Gen {gen+1}: Vowel shift /{target}/ → /{replacement}/ ({direction})")

            elif change_type == "merge":
                if len(self.consonants) < 3:
                    continue
                c1, c2 = rng.sample(self.consonants, 2)
                apply_replacement(c2, c1)
                changes_applied.append(f"Gen {gen+1}: Merger /{c2}/ → /{c1}/")

            elif change_type == "diphthongize":
                if not self.vowels:
                    continue
                target = rng.choice(self.vowels)
                diphthong = target + rng.choice(["i", "u", "a"])
                apply_first_replacement(target, diphthong)
                changes_applied.append(f"Gen {gen+1}: Diphthongization /{target}/ → /{diphthong}/")

            elif change_type == "insertion":
                if not self.vowels:
                    continue
                insert_vowel = rng.choice(self.vowels)
                if len(self.consonants) < 2:
                    continue
                c_pair = rng.choice(self.consonants) + rng.choice(self.consonants)
                apply_insertion(c_pair, c_pair[0] + insert_vowel + c_pair[1])
                changes_applied.append(f"Gen {gen+1}: Epenthesis /{c_pair}/ → /{c_pair[0]}{insert_vowel}{c_pair[1]}/")

            elif change_type == "assimilation":
                if len(self.consonants) < 2:
                    continue
                c_target = rng.choice(self.consonants)
                double = c_target + c_target
                apply_replacement(double, c_target)
                changes_applied.append(f"Gen {gen+1}: Degemination /{double}/ → /{c_target}/")

        # Create evolved language as a copy of self with evolved vocabulary
        evolved = copy.deepcopy(self)
        evolved.name = self.name + "'"
        # Override vocabulary with evolved forms
        evolved.vocabulary = current_vocab

        # Resolve duplicate word forms created by sound changes (mergers, etc.)
        # When two English words map to the same alien form, disambiguate
        # by appending a distinguishing suffix.
        all_forms: Dict[str, List[Tuple[str, str]]] = {}  # alien_form -> [(cat, en_word)]
        for cat in evolved.vocabulary:
            for en, alien in evolved.vocabulary[cat].items():
                if alien not in all_forms:
                    all_forms[alien] = []
                all_forms[alien].append((cat, en))

        # Collect duplicates and fix them (avoid modifying dict during iteration)
        disambig_vowels = evolved.vowels if evolved.vowels else ["a", "e", "i"]
        vi = 0
        duplicates_to_fix = []
        for alien_form, entries in all_forms.items():
            if len(entries) > 1:
                duplicates_to_fix.append((alien_form, entries))

        for alien_form, entries in duplicates_to_fix:
            for j, (cat, en) in enumerate(entries[1:]):
                # Try adding a consonant+vowel suffix to make the form unique
                # First try single vowels, then CV combos
                new_form = None
                for v in disambig_vowels:
                    candidate = alien_form + v
                    if candidate not in all_forms:
                        new_form = candidate
                        break
                if new_form is None:
                    # Try CV combos using available consonants
                    consonants_for_disambig = evolved.consonants[:5] if evolved.consonants else ["k", "t", "p"]
                    for c in consonants_for_disambig:
                        for v in disambig_vowels:
                            candidate = alien_form + c + v
                            if candidate not in all_forms:
                                new_form = candidate
                                break
                        if new_form:
                            break
                if new_form is None:
                    # Fallback: use a number suffix
                    new_form = alien_form + str(j + 2)
                evolved.vocabulary[cat][en] = new_form
                all_forms[new_form] = [(cat, en)]

        # Rebuild reverse vocabulary
        evolved.reverse_vocab = {}
        for cat in evolved.vocabulary:
            for en, alien in evolved.vocabulary[cat].items():
                evolved.reverse_vocab[alien] = en

        # Restore evolved morphological affixes
        evolved.case_affixes = {}
        evolved.tense_affixes = {}
        evolved.number_affixes = {}
        for key, affix in current_affixes.items():
            category, name = key
            if category == "case":
                evolved.case_affixes[name] = affix
            elif category == "tense":
                evolved.tense_affixes[name] = affix
            elif category == "number":
                evolved.number_affixes[name] = affix
            elif category == "deriv":
                if name == "nominalizer":
                    evolved.nominalizer = affix
                elif name == "verbalizer":
                    evolved.verbalizer = affix
                elif name == "adjectivizer":
                    evolved.adjectivizer = affix
                elif name == "possessive":
                    evolved.possessive_affix = affix
            elif category == "particle":
                if name == "question":
                    evolved.question_particle = affix

        evolved.evolution_log = self.evolution_log + changes_applied
        # Update seed for reproducibility of evolved language
        evolved.seed = self.seed + generations

        return evolved

    def dictionary(self) -> Dict[str, str]:
        """Return the full dictionary English → Alien."""
        d = {}
        for cat in self.vocabulary:
            for en, alien in self.vocabulary[cat].items():
                d[en] = alien
        return dict(sorted(d.items()))

    def info(self) -> str:
        """Print a comprehensive description of the language."""
        W = 60  # Box width
        lines = []

        def pad(text: str, width: int = W) -> str:
            """Pad text to fit inside box borders, truncating if too long."""
            inner = width - 2  # "║ " and " ║"
            if len(text) > inner:
                text = text[:inner - 1] + "…"
            return text.ljust(inner)

        sep = ", "
        affix_label = "prefix" if self.prefix_mode else "suffix"
        affix_type = "prefixes" if self.prefix_mode else "suffixes"
        adj_pos = "before noun" if self.adj_before_noun else "after noun"
        cases_str = sep.join(self.cases) if self.cases else "none"
        tenses_str = sep.join(self.tenses) if self.tenses else "none"
        numbers_str = sep.join(self.numbers) if self.numbers else "none"

        lines.append(f"╔{'═' * W}╗")
        lines.append(f"║ {pad('Language: ' + self.name)}║")
        lines.append(f"║ {pad('Culture: ' + self.culture)}║")
        if self.evolution_log:
            evo_str = str(len(self.evolution_log)) + ' change(s) applied'
            lines.append(f"║ {pad('Evolved: ' + evo_str)}║")
        lines.append(f"╠{'═' * W}╣")
        lines.append(f"║ {pad('PHONOLOGY')}║")
        lines.append(f"║ {pad('Consonants: ' + sep.join(self.consonants))}║")
        lines.append(f"║ {pad('Vowels:     ' + sep.join(self.vowels))}║")
        lines.append(f"║ {pad('Syllables:  ' + sep.join(self.syllable_patterns))}║")
        lines.append(f"║ {pad('')}║")
        lines.append(f"║ {pad('GRAMMAR')}║")
        lines.append(f"║ {pad('Word order:   ' + self.word_order)}║")
        lines.append(f"║ {pad('Case system:  ' + self.case_system + ' (' + cases_str + ')')}║")
        lines.append(f"║ {pad('Tense system: ' + self.tense_system + ' (' + tenses_str + ')')}║")
        lines.append(f"║ {pad('Number:       ' + self.number_system + ' (' + numbers_str + ')')}║")
        lines.append(f"║ {pad('Adj position: ' + adj_pos)}║")
        lines.append(f"║ {pad('Affix type:   ' + affix_type)}║")
        if self.question_particle:
            lines.append(f"║ {pad('Question:     particle ' + repr(self.question_particle))}║")
        lines.append(f"║ {pad('')}║")
        lines.append(f"║ {pad('MORPHOLOGY')}║")
        for case, affix in self.case_affixes.items():
            line_text = '  ' + case + ': ' + affix_label + " '" + affix + "'"
            lines.append('║ ' + pad(line_text) + '║')
        for tense, affix in self.tense_affixes.items():
            line_text = '  ' + tense + ': ' + affix_label + " '" + affix + "'"
            lines.append('║ ' + pad(line_text) + '║')
        for num, affix in self.number_affixes.items():
            line_text = '  ' + num + ': ' + affix_label + " '" + affix + "'"
            lines.append('║ ' + pad(line_text) + '║')
        if self.nominalizer:
            lines.append('║ ' + pad("  Nominalizer: '" + self.nominalizer + "'") + '║')
        if self.verbalizer:
            lines.append('║ ' + pad("  Verbalizer:  '" + self.verbalizer + "'") + '║')
        if self.adjectivizer:
            lines.append('║ ' + pad("  Adjectivizer: '" + self.adjectivizer + "'") + '║')
        if self.possessive_affix:
            pos_label = "prefix" if self.prefix_mode else "suffix"
            lines.append('║ ' + pad("  Possessive:   " + pos_label + " '" + self.possessive_affix + "'") + '║')
        lines.append(f"║ {pad('')}║")
        vocab_count = str(sum(len(v) for v in self.vocabulary.values()))
        lines.append(f"║ {pad('Vocabulary: ' + vocab_count + ' words')}║")
        lines.append(f"╚{'═' * W}╝")
        return "\n".join(lines)

    def print_dictionary(self) -> str:
        """Format the full dictionary."""
        lines = []
        lines.append(f"{'─' * 50}")
        lines.append(f"  DICTIONARY — {self.name}")
        lines.append(f"{'─' * 50}")
        for cat in self.vocabulary:
            lines.append(f"")
            lines.append(f"  [{cat.upper()}]")
            for en, alien in sorted(self.vocabulary[cat].items()):
                lines.append(f"    {en:<15s} → {alien}")
        lines.append(f"{'─' * 50}")
        return "\n".join(lines)

    def print_glyph_chart(self) -> str:
        """Print a chart of all phoneme glyphs."""
        lines = []
        lines.append(f"{'─' * 60}")
        lines.append(f"  GLYPH CHART — {self.name}")
        lines.append(f"{'─' * 60}")

        # Render consonants
        lines.append("")
        lines.append("  CONSONANTS:")
        lines.append("")
        # Show in rows of 5
        all_ph = self.consonants
        for i in range(0, len(all_ph), 5):
            chunk = all_ph[i:i+5]
            row1 = ""
            row2 = ""
            row3 = ""
            label = ""
            for ph in chunk:
                g = self.glyph_gen.render_phoneme(ph)
                row1 += g[0] + "  "
                row2 += g[1] + "  "
                row3 += g[2] + "  "
                label += f"/{ph}/".center(len(g[0]) + 2)
            lines.append(f"  {row1}")
            lines.append(f"  {row2}")
            lines.append(f"  {row3}")
            lines.append(f"  {label}")
            lines.append("")

        # Render vowels
        lines.append("  VOWELS:")
        lines.append("")
        for ph in self.vowels:
            g = self.glyph_gen.render_phoneme(ph)
            lines.append(f"  {g[0]}  ← /{ph}/")
            lines.append(f"  {g[1]}")
            lines.append(f"  {g[2]}")
            lines.append("")

        lines.append(f"{'─' * 60}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize language to a dictionary."""
        data = {
            "name": self.name,
            "seed": self.seed,
            "culture": self.culture,
            "cultural_words": self.cultural_words,
            "consonants": self.consonants,
            "vowels": self.vowels,
            "syllable_patterns": self.syllable_patterns,
            "word_order": self.word_order,
            "case_system": self.case_system,
            "tense_system": self.tense_system,
            "number_system": self.number_system,
            "cases": self.cases,
            "tenses": self.tenses,
            "numbers": self.numbers,
            "prefix_mode": self.prefix_mode,
            "adj_before_noun": self.adj_before_noun,
            "possession_suffix": self.possession_suffix,
            "question_particle": self.question_particle,
            "case_affixes": self.case_affixes,
            "tense_affixes": self.tense_affixes,
            "number_affixes": self.number_affixes,
            "nominalizer": self.nominalizer,
            "verbalizer": self.verbalizer,
            "adjectivizer": self.adjectivizer,
            "possessive_affix": self.possessive_affix,
            "vocabulary": self.vocabulary,
            "evolution_log": self.evolution_log,
        }
        return data

    def save(self, filepath: str):
        """Save language to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> "AlienLanguage":
        """Load language from JSON file."""
        try:
            with open(filepath) as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"Error: File '{filepath}' not found.", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in '{filepath}': {e}", file=sys.stderr)
            sys.exit(1)

        lang = cls(seed=data["seed"])
        lang.name = data["name"]
        lang.culture = data["culture"]
        lang.cultural_words = data.get("cultural_words", [])
        lang.consonants = data["consonants"]
        lang.vowels = data["vowels"]
        lang.syllable_patterns = data["syllable_patterns"]
        lang.word_order = data["word_order"]
        lang.case_system = data["case_system"]
        lang.tense_system = data["tense_system"]
        lang.number_system = data["number_system"]
        lang.cases = data["cases"]
        lang.tenses = data["tenses"]
        lang.numbers = data["numbers"]
        lang.prefix_mode = data["prefix_mode"]
        lang.adj_before_noun = data.get("adj_before_noun", True)
        lang.possession_suffix = data.get("possession_suffix", False)
        lang.question_particle = data.get("question_particle")
        lang.case_affixes = data["case_affixes"]
        lang.tense_affixes = data["tense_affixes"]
        lang.number_affixes = data["number_affixes"]
        lang.nominalizer = data.get("nominalizer")
        lang.verbalizer = data.get("verbalizer")
        lang.adjectivizer = data.get("adjectivizer")
        lang.possessive_affix = data.get("possessive_affix", "")
        lang.vocabulary = data["vocabulary"]
        lang.evolution_log = data.get("evolution_log", [])
        lang.reverse_vocab = {}
        for cat in lang.vocabulary:
            for en, alien in lang.vocabulary[cat].items():
                lang.reverse_vocab[alien] = en

        # Rebuild phoneme mappings
        lang.char_to_phoneme = {}
        lang.phoneme_to_char = {}
        lang.all_phonemes = lang.consonants + lang.vowels
        idx = 0
        all_chars = list("bcdfghjklmnpqrstvwxyz") + list("aeiou")
        for ph in lang.all_phonemes:
            if len(ph) == 1:
                lang.char_to_phoneme[ph] = ph
                lang.phoneme_to_char[ph] = ph
            else:
                ch = all_chars[idx % len(all_chars)]
                lang.char_to_phoneme[ch] = ph
                lang.phoneme_to_char[ph] = ch
                idx += 1

        lang.glyph_gen = GlyphGenerator(lang.seed + 9999, lang.all_phonemes)
        return lang


# ─── Interactive Mode ─────────────────────────────────────────────────────────

def interactive_mode(lang: AlienLanguage):
    """Interactive translation and exploration mode."""
    print(f"\n{'═' * 60}")
    print(f"  Welcome to the {lang.name} Language Lab!")
    print(f"  Culture: {lang.culture} | Seed: {lang.seed}")
    if lang.evolution_log:
        print(f"  Evolved: {len(lang.evolution_log)} change(s) applied")
    print(f"{'═' * 60}")
    print()
    print("  Commands:")
    print("    <text>         — Translate English text to alien language")
    print("    /glyph <word>  — Show glyph rendering of an alien word")
    print("    /dict          — Show full dictionary")
    print("    /info          — Show language info")
    print("    /chart         — Show glyph chart")
    print("    /proverb       — Generate a proverb")
    print("    /poem          — Generate a poem")
    print("    /sample        — Generate sample text")
    print("    /reverse <text> — Translate alien text to English")
    print("    /evolve <N>    — Evolve language N generations")
    print("    /new           — Generate a new random language")
    print("    /save <file>   — Save language to file")
    print("    /count         — Show vocabulary count")
    print("    /quit          — Exit")
    print()

    while True:
        try:
            user_input = input("🔤 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye! 👋")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            if cmd in ("/quit", "/exit", "/q"):
                print("  Goodbye! 👋")
                break
            elif cmd == "/info":
                print(lang.info())
            elif cmd == "/dict":
                print(lang.print_dictionary())
            elif cmd == "/chart":
                print(lang.print_glyph_chart())
            elif cmd == "/proverb":
                print()
                proverb = lang.generate_proverb()
                print(f"  {proverb}")
                print()
            elif cmd == "/poem":
                print()
                poem = lang.generate_poem()
                print(poem)
                print()
            elif cmd == "/sample":
                sample = lang.generate_sample_text()
                print(f"\n  {sample}")
                print(f"\n  In glyphs:")
                print(lang.render_text_glyphs(sample))
                print()
            elif cmd == "/glyph":
                if arg:
                    print()
                    print(lang.render_word_glyphs(arg))
                    print()
                else:
                    print("  Usage: /glyph <alien_word>")
            elif cmd == "/reverse":
                if arg:
                    en = lang.reverse_translate(arg)
                    print(f"\n  English: {en}")
                    print()
                else:
                    print("  Usage: /reverse <alien_text>")
            elif cmd == "/evolve":
                try:
                    n = int(arg) if arg else 1
                except ValueError:
                    n = 1
                lang = lang.evolve(n)
                print(f"\n  Language evolved {n} generation(s)!")
                print(f"  New name: {lang.name}")
                if lang.evolution_log:
                    print(f"  Changes:")
                    for change in lang.evolution_log:
                        print(f"    • {change}")
                print()
            elif cmd == "/new":
                seed = random.randint(0, 2**32 - 1)
                lang = AlienLanguage(seed=seed)
                print(f"\n  Generated new language: {lang.name}")
                print(f"  Culture: {lang.culture}")
                print(f"  Seed: {lang.seed}")
                print()
            elif cmd == "/save":
                filename = arg if arg else f"{lang.name.lower().replace(' ', '_')}.json"
                try:
                    lang.save(filename)
                    print(f"  Saved to {filename}")
                except OSError as e:
                    print(f"  Error saving: {e}")
            elif cmd == "/count":
                total = sum(len(v) for v in lang.vocabulary.values())
                print(f"  Vocabulary: {total} words")
                for cat, words in lang.vocabulary.items():
                    print(f"    {cat}: {len(words)}")
            else:
                print(f"  Unknown command: {cmd}. Type /quit to exit.")
        else:
            # Translate
            translated = lang.translate_sentence(user_input)
            print(f"\n  {lang.name}: {translated}")
            reverse = lang.reverse_translate(translated)
            print(f"  Back to English: {reverse}")
            print(f"\n  Glyphs:")
            print(lang.render_text_glyphs(translated))
            print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Procedural Alien Language Generator — create fully-formed constructed languages!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s                                    # Interactive mode
  %(prog)s --seed 42 --info                   # Show language info
  %(prog)s --seed 42 --translate "the water flows"  # Translate a sentence
  %(prog)s --seed 42 --proverb                # Generate a proverb
  %(prog)s --seed 42 --poem                   # Generate a poem
  %(prog)s --seed 42 --dict                   # Show dictionary
  %(prog)s --seed 42 --chart                  # Show glyph chart
  %(prog)s --seed 42 --evolve 5 --info        # Evolve 5 generations, then show info
  %(prog)s --seed 42 -o lang.json             # Save to file
  %(prog)s --load lang.json --info            # Load and show info
"""
    )
    parser.add_argument("-s", "--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("-n", "--name", type=str, help="Name for the language")
    parser.add_argument("-i", "--info", action="store_true", help="Print language info and exit")
    parser.add_argument("-d", "--dict", action="store_true", help="Print dictionary and exit")
    parser.add_argument("-g", "--chart", action="store_true", help="Print glyph chart and exit")
    parser.add_argument("-p", "--proverb", action="store_true", help="Generate a proverb and exit")
    parser.add_argument("-t", "--translate", type=str, help="Translate an English sentence")
    parser.add_argument("-r", "--reverse", type=str, help="Translate alien text back to English")
    parser.add_argument("--poem", action="store_true", help="Generate a poem and exit")
    parser.add_argument("--evolve", type=int, metavar="N", help="Evolve language N generations")
    parser.add_argument("--count", action="store_true", help="Show vocabulary word count")
    parser.add_argument("-o", "--output", type=str, help="Save language to JSON file")
    parser.add_argument("-l", "--load", type=str, help="Load language from JSON file")
    parser.add_argument("--interactive", action="store_true", help="Start interactive mode")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    if args.load:
        lang = AlienLanguage.load(args.load)
        print(f"Loaded language: {lang.name}")
    else:
        lang = AlienLanguage(seed=args.seed, name=args.name)

    # Apply evolution if requested
    if args.evolve:
        lang = lang.evolve(args.evolve)
        print(f"Evolved language {args.evolve} generation(s). New name: {lang.name}")
        if lang.evolution_log:
            for change in lang.evolution_log:
                print(f"  • {change}")

    if args.output:
        try:
            lang.save(args.output)
            print(f"Saved language to {args.output}")
        except OSError as e:
            print(f"Error saving: {e}", file=sys.stderr)

    if args.info:
        print(lang.info())

    if args.dict:
        print(lang.print_dictionary())

    if args.chart:
        print(lang.print_glyph_chart())

    if args.proverb:
        print(lang.generate_proverb())

    if args.poem:
        print(lang.generate_poem())

    if args.count:
        total = sum(len(v) for v in lang.vocabulary.values())
        print(f"Vocabulary: {total} words")
        for cat, words in lang.vocabulary.items():
            print(f"  {cat}: {len(words)}")

    if args.translate:
        translated = lang.translate_sentence(args.translate)
        print(f"\nEnglish: {args.translate}")
        print(f"{lang.name}: {translated}")
        reverse = lang.reverse_translate(translated)
        print(f"Back to English: {reverse}")
        print(f"\nGlyphs:")
        print(lang.render_text_glyphs(translated))

    if args.reverse:
        en = lang.reverse_translate(args.reverse)
        print(f"English: {en}")

    if args.interactive or not any([args.info, args.dict, args.chart, args.proverb, args.poem,
                                     args.translate, args.reverse, args.output, args.count, args.evolve]):
        interactive_mode(lang)


if __name__ == "__main__":
    main()