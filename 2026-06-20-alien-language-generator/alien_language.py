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
"""

import random
import hashlib
import json
import sys
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


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


def weighted_choice(options, weights=None):
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

    def _generate_name(self) -> str:
        templates = [
            lambda: self._make_syllable().capitalize() + self._make_syllable(),
            lambda: self._make_syllable().capitalize() + "'" + self._make_syllable(),
            lambda: self._make_syllable().capitalize() + "i" + self._make_syllable(),
            lambda: self._make_syllable().capitalize() + "u" + self._make_syllable() + self._make_syllable(),
        ]
        return self.rng.choice(templates)()

    def _make_syllable(self) -> str:
        c = self.rng.choice(["b", "k", "l", "r", "t", "s", "m", "n", "z", "v", "zh", "th", "q"])
        v = self.rng.choice(["a", "e", "i", "o", "u", "ai", "ei", "ou"])
        return c + v

    def _build_phonology(self):
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

        # Syllable structure
        self.syllable_patterns = self.rng.choice([
            ["CV"],                          # Simple
            ["CV", "CVC"],                    # Medium
            ["CV", "CVC", "CCV", "V"],        # Complex
            ["V", "CV", "VC", "CVC"],         # Open
        ])

    def _build_grammar(self):
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
        # Affixes
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

    def _gen_morpheme(self) -> str:
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

    def _gen_word_form(self) -> str:
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
                while form in used_forms:
                    form = self._gen_word_form()
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

    def inflect_noun(self, base: str, case: Optional[str] = None, number: Optional[str] = None) -> str:
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
        word = base
        if tense and tense in self.tense_affixes:
            if self.prefix_mode:
                word = self.tense_affixes[tense] + word
            else:
                word = word + self.tense_affixes[tense]
        return word

    def translate_sentence(self, english: str) -> str:
        """Simple sentence translation with basic grammar application."""
        words = english.lower().strip().rstrip(".").split()

        # Very simple: try to translate each word
        # Determine subject/verb/object positions based on word order
        translated = []
        for w in words:
            alien_w = self.translate_word(w)
            if alien_w:
                translated.append(alien_w)
            else:
                # Try to handle possessives, plurals, etc. simply
                if w.endswith("s") and w[:-1]:
                    alien_w = self.translate_word(w[:-1])
                    if alien_w:
                        translated.append(self.inflect_noun(alien_w, number="PL"))
                        continue
                if w.endswith("ed") and w[:-2]:
                    alien_w = self.translate_word(w[:-2])
                    if alien_w:
                        translated.append(self.inflect_verb(alien_w, tense="PAST"))
                        continue
                if w.endswith("ing") and w[:-3]:
                    alien_w = self.translate_word(w[:-3])
                    if alien_w:
                        translated.append(self.inflect_verb(alien_w, tense="PRES"))
                        continue
                translated.append(f"[{w}]")

        # Reorder based on word order if we can identify S/V/O
        # For simplicity, just apply question particle
        result = " ".join(translated)
        if english.strip().endswith("?") and self.question_particle:
            result += " " + self.question_particle

        return result

    def render_word_glyphs(self, alien_word: str) -> str:
        """Render an alien word in the glyph writing system."""
        # Break word into grapheme-sized chunks for rendering
        chunks = []
        i = 0
        while i < len(alien_word):
            if i + 1 < len(alien_word) and alien_word[i:i+2] in self.phoneme_to_char.values():
                chunks.append(alien_word[i:i+2])
                i += 2
            else:
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
            block = self.render_word_glyphs(word)
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

    def dictionary(self) -> Dict[str, str]:
        """Return the full dictionary English → Alien."""
        d = {}
        for cat in self.vocabulary:
            for en, alien in self.vocabulary[cat].items():
                d[en] = alien
        return dict(sorted(d.items()))

    def info(self) -> str:
        """Print a comprehensive description of the language."""
        lines = []
        lines.append(f"╔{'═'*60}╗")
        lines.append(f"║  Language: {self.name:<47}║")
        lines.append(f"║  Culture: {self.culture:<49}║")
        lines.append(f"╠{'═'*60}╣")
        lines.append(f"║                                                              ║")
        lines.append(f"║  PHONOLOGY                                                   ║")
        lines.append(f"║  Consonants: {', '.join(self.consonants)}")
        lines.append(f"║  Vowels:     {', '.join(self.vowels)}")
        lines.append(f"║  Syllables:  {', '.join(self.syllable_patterns)}")
        lines.append(f"║                                                              ║")
        lines.append(f"║  GRAMMAR                                                     ║")
        lines.append(f"║  Word order:   {self.word_order}")
        lines.append(f"║  Case system:  {self.case_system} ({', '.join(self.cases) if self.cases else 'none'})")
        lines.append(f"║  Tense system: {self.tense_system} ({', '.join(self.tenses) if self.tenses else 'none'})")
        lines.append(f"║  Number:       {self.number_system} ({', '.join(self.numbers) if self.numbers else 'none'})")
        lines.append(f"║  Adj position: {'before noun' if self.adj_before_noun else 'after noun'}")
        lines.append(f"║  Affix type:   {'prefixes' if self.prefix_mode else 'suffixes'}")
        if self.question_particle:
            lines.append(f"║  Question:     particle '{self.question_particle}'")
        lines.append(f"║                                                              ║")
        lines.append(f"║  MORPHOLOGY                                                   ║")
        for case, affix in self.case_affixes.items():
            lines.append(f"║  {case:6s}: {self.prefix_mode * 'prefix' if self.prefix_mode else 'suffix'} '{affix}'")
        for tense, affix in self.tense_affixes.items():
            lines.append(f"║  {tense:6s}: {self.prefix_mode * 'prefix' if self.prefix_mode else 'suffix'} '{affix}'")
        for num, affix in self.number_affixes.items():
            lines.append(f"║  {num:6s}: {self.prefix_mode * 'prefix' if self.prefix_mode else 'suffix'} '{affix}'")
        lines.append(f"║                                                              ║")
        lines.append(f"╚{'═'*60}╝")
        return "\n".join(lines)

    def print_dictionary(self) -> str:
        """Format the full dictionary."""
        lines = []
        lines.append(f"{'─'*50}")
        lines.append(f"  DICTIONARY — {self.name}")
        lines.append(f"{'─'*50}")
        for cat in self.vocabulary:
            lines.append(f"")
            lines.append(f"  [{cat.upper()}]")
            for en, alien in sorted(self.vocabulary[cat].items()):
                lines.append(f"    {en:<15s} → {alien}")
        lines.append(f"{'─'*50}")
        return "\n".join(lines)

    def print_glyph_chart(self) -> str:
        """Print a chart of all phoneme glyphs."""
        lines = []
        lines.append(f"{'─'*60}")
        lines.append(f"  GLYPH CHART — {self.name}")
        lines.append(f"{'─'*60}")

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

        lines.append(f"{'─'*60}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize language to a dictionary."""
        data = {
            "name": self.name,
            "seed": self.seed,
            "culture": self.culture,
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
            "case_affixes": self.case_affixes,
            "tense_affixes": self.tense_affixes,
            "number_affixes": self.number_affixes,
            "vocabulary": self.vocabulary,
        }
        return data

    def save(self, filepath: str):
        """Save language to JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> "AlienLanguage":
        """Load language from JSON file."""
        with open(filepath) as f:
            data = json.load(f)

        lang = cls(seed=data["seed"])
        lang.name = data["name"]
        lang.culture = data["culture"]
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
        lang.case_affixes = data["case_affixes"]
        lang.tense_affixes = data["tense_affixes"]
        lang.number_affixes = data["number_affixes"]
        lang.vocabulary = data["vocabulary"]
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
    print(f"\n{'═'*60}")
    print(f"  Welcome to the {lang.name} Language Lab!")
    print(f"  Culture: {lang.culture} | Seed: {lang.seed}")
    print(f"{'═'*60}")
    print()
    print("  Commands:")
    print("    <text>        — Translate English text to alien language")
    print("    /glyph <word>  — Show glyph rendering of an alien word")
    print("    /dict         — Show full dictionary")
    print("    /info         — Show language info")
    print("    /chart        — Show glyph chart")
    print("    /proverb      — Generate a proverb")
    print("    /sample       — Generate sample text")
    print("    /new          — Generate a new random language")
    print("    /save <file>  — Save language to file")
    print("    /quit         — Exit")
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

            if cmd == "/quit" or cmd == "/exit":
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
            elif cmd == "/new":
                seed = random.randint(0, 2**32 - 1)
                lang = AlienLanguage(seed=seed)
                print(f"\n  Generated new language: {lang.name}")
                print(f"  Culture: {lang.culture}")
                print(f"  Seed: {lang.seed}")
                print()
            elif cmd == "/save":
                filename = arg if arg else f"{lang.name.lower().replace(' ', '_')}.json"
                lang.save(filename)
                print(f"  Saved to {filename}")
            else:
                print(f"  Unknown command: {cmd}")
        else:
            # Translate
            translated = lang.translate_sentence(user_input)
            print(f"\n  {lang.name}: {translated}")
            print(f"\n  Glyphs:")
            print(lang.render_text_glyphs(translated))
            print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Procedural Alien Language Generator — create fully-formed constructed languages!"
    )
    parser.add_argument("-s", "--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("-n", "--name", type=str, help="Name for the language")
    parser.add_argument("-i", "--info", action="store_true", help="Print language info and exit")
    parser.add_argument("-d", "--dict", action="store_true", help="Print dictionary and exit")
    parser.add_argument("-g", "--chart", action="store_true", help="Print glyph chart and exit")
    parser.add_argument("-p", "--proverb", action="store_true", help="Generate a proverb and exit")
    parser.add_argument("-t", "--translate", type=str, help="Translate an English sentence")
    parser.add_argument("-o", "--output", type=str, help="Save language to JSON file")
    parser.add_argument("-l", "--load", type=str, help="Load language from JSON file")
    parser.add_argument("--interactive", action="store_true", help="Start interactive mode")

    args = parser.parse_args()

    if args.load:
        lang = AlienLanguage.load(args.load)
        print(f"Loaded language: {lang.name}")
    else:
        lang = AlienLanguage(seed=args.seed, name=args.name)

    if args.output:
        lang.save(args.output)
        print(f"Saved language to {args.output}")

    if args.info:
        print(lang.info())

    if args.dict:
        print(lang.print_dictionary())

    if args.chart:
        print(lang.print_glyph_chart())

    if args.proverb:
        print(lang.generate_proverb())

    if args.translate:
        translated = lang.translate_sentence(args.translate)
        print(f"\nEnglish: {args.translate}")
        print(f"{lang.name}: {translated}")
        print(f"\nGlyphs:")
        print(lang.render_text_glyphs(translated))

    if args.interactive or not any([args.info, args.dict, args.chart, args.proverb, args.translate, args.output]):
        interactive_mode(lang)


if __name__ == "__main__":
    main()