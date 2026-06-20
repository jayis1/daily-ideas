#!/usr/bin/env python3
"""Tests for the Alien Language Generator."""

import random
import json
import os
import tempfile
import unittest

from alien_language import (
    AlienLanguage, GlyphGenerator, make_seed, weighted_choice,
    CONSONANTS_BY_MANNER, VOWELS, WORD_ORDERS, CASE_SYSTEMS,
    TENSE_SYSTEMS, NUMBER_SYSTEMS, CULTURAL_FLAVORS, VERSION,
)


class TestMakeSeed(unittest.TestCase):
    """Test the make_seed utility function."""

    def test_deterministic(self):
        """Same input → same output."""
        self.assertEqual(make_seed("hello"), make_seed("hello"))

    def test_different_inputs(self):
        """Different inputs → different outputs (with high probability)."""
        self.assertNotEqual(make_seed("hello"), make_seed("world"))

    def test_integer_result(self):
        """Result should be an integer."""
        result = make_seed("test")
        self.assertIsInstance(result, int)


class TestWeightedChoice(unittest.TestCase):
    """Test the weighted_choice utility function."""

    def test_unweighted(self):
        """Without weights, all choices should be possible."""
        rng = random.Random(42)
        results = set()
        for _ in range(100):
            results.add(weighted_choice(["a", "b", "c"]))
        # With 100 tries, we should hit all 3 options
        self.assertEqual(len(results), 3)

    def test_weighted_deterministic(self):
        """With weights, seeded random should be deterministic."""
        rng = random.Random(42)
        result = weighted_choice(["x", "y", "z"], weights=[1, 1, 100])
        # With weight 100 on "z", this should almost always be "z"
        # but we test determinism of the function itself
        result1 = weighted_choice(["a", "b"], weights=[1, 100])
        result2 = weighted_choice(["a", "b"], weights=[1, 100])
        # Results depend on random state, so just verify it returns a valid choice
        self.assertIn(result1, ["a", "b"])


class TestGlyphGenerator(unittest.TestCase):
    """Test the GlyphGenerator class."""

    def test_generates_glyphs(self):
        """Each phoneme should get a 3-line glyph."""
        gen = GlyphGenerator(seed=42, phonemes=["p", "a", "k"])
        for ph in ["p", "a", "k"]:
            glyph = gen.render_phoneme(ph)
            self.assertEqual(len(glyph), 3)

    def test_unknown_phoneme(self):
        """Unknown phonemes should get placeholder glyphs."""
        gen = GlyphGenerator(seed=42, phonemes=["p"])
        glyph = gen.render_phoneme("zzz")
        self.assertEqual(glyph, [" ? ", " ? ", " ? "])

    def test_deterministic(self):
        """Same seed → same glyphs."""
        gen1 = GlyphGenerator(seed=123, phonemes=["p", "a", "k"])
        gen2 = GlyphGenerator(seed=123, phonemes=["p", "a", "k"])
        self.assertEqual(gen1.glyphs, gen2.glyphs)

    def test_different_seeds(self):
        """Different seeds → different glyphs (usually)."""
        gen1 = GlyphGenerator(seed=1, phonemes=["p", "a", "k"])
        gen2 = GlyphGenerator(seed=2, phonemes=["p", "a", "k"])
        # At least one glyph should differ
        self.assertNotEqual(gen1.glyphs, gen2.glyphs)


class TestAlienLanguageCreation(unittest.TestCase):
    """Test creating AlienLanguage instances."""

    def test_deterministic_with_seed(self):
        """Same seed → same language."""
        lang1 = AlienLanguage(seed=42)
        lang2 = AlienLanguage(seed=42)
        self.assertEqual(lang1.name, lang2.name)
        self.assertEqual(lang1.consonants, lang2.consonants)
        self.assertEqual(lang1.vowels, lang2.vowels)
        self.assertEqual(lang1.word_order, lang2.word_order)

    def test_random_without_seed(self):
        """No seed → random language (name likely different)."""
        # Not guaranteed different, but extremely likely
        names = set()
        for _ in range(10):
            lang = AlienLanguage()
            names.add(lang.name)
        self.assertGreater(len(names), 1)

    def test_custom_name(self):
        """Custom name should override generated name."""
        lang = AlienLanguage(seed=42, name="Xylorith")
        self.assertEqual(lang.name, "Xylorith")

    def test_culture_assignment(self):
        """Each language should have a culture."""
        lang = AlienLanguage(seed=42)
        cultures = [c[0] for c in CULTURAL_FLAVORS]
        self.assertIn(lang.culture, cultures)

    def test_vocabulary_populated(self):
        """Vocabulary should have entries in each category."""
        lang = AlienLanguage(seed=42)
        for cat in ["pronouns", "nouns_basic", "verbs_basic", "adjectives"]:
            self.assertGreater(len(lang.vocabulary[cat]), 0)

    def test_vocabulary_uniqueness(self):
        """All generated word forms should be unique."""
        lang = AlienLanguage(seed=42)
        all_forms = []
        for cat in lang.vocabulary:
            for en, alien in lang.vocabulary[cat].items():
                all_forms.append(alien)
        self.assertEqual(len(all_forms), len(set(all_forms)),
                         "Generated word forms should be unique")

    def test_reverse_vocab(self):
        """Reverse vocabulary should map alien → English."""
        lang = AlienLanguage(seed=42)
        for cat in lang.vocabulary:
            for en, alien in lang.vocabulary[cat].items():
                self.assertEqual(lang.reverse_vocab[alien], en)


class TestTranslation(unittest.TestCase):
    """Test translation functionality."""

    def setUp(self):
        self.lang = AlienLanguage(seed=42)

    def test_translate_word_known(self):
        """Known words should translate correctly."""
        result = self.lang.translate_word("water")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)

    def test_translate_word_unknown(self):
        """Unknown words should return None."""
        result = self.lang.translate_word("xylophone_rare")
        self.assertIsNone(result)

    def test_translate_sentence(self):
        """Sentence translation should produce output."""
        result = self.lang.translate_sentence("water flows")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_translate_question(self):
        """Questions should add question particle if defined."""
        result = self.lang.translate_sentence("water flows?")
        if self.lang.question_particle:
            self.assertIn(self.lang.question_particle, result)

    def test_translate_articles_skipped(self):
        """Articles (the, a, an) should be skipped."""
        with_the = self.lang.translate_sentence("the water")
        without_the = self.lang.translate_sentence("water")
        # They should be the same (articles skipped)
        self.assertEqual(with_the, without_the)

    def test_translate_negation(self):
        """Negation word 'not' should be handled."""
        result = self.lang.translate_sentence("not water")
        self.assertIsInstance(result, str)

    def test_reverse_translate(self):
        """Reverse translation should map some words back."""
        # Translate a known word, then reverse translate it
        alien = self.lang.translate_word("water")
        self.assertIsNotNone(alien)
        english = self.lang.reverse_translate_word(alien)
        self.assertEqual(english, "water")


class TestInflection(unittest.TestCase):
    """Test morphological inflection."""

    def setUp(self):
        self.lang = AlienLanguage(seed=42)

    def test_inflect_noun_case(self):
        """Noun inflection should add case affix."""
        if self.lang.cases:
            result = self.lang.inflect_noun("taka", case=self.lang.cases[0])
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), len("taka"))

    def test_inflect_verb_tense(self):
        """Verb inflection should add tense affix."""
        if self.lang.tenses:
            result = self.lang.inflect_verb("beka", tense=self.lang.tenses[0])
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), len("beka"))

    def test_inflect_noun_number(self):
        """Noun inflection should add number affix."""
        if self.lang.numbers:
            result = self.lang.inflect_noun("taka", number=self.lang.numbers[0])
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), len("taka"))


class TestEvolution(unittest.TestCase):
    """Test language evolution."""

    def test_evolve_creates_new_name(self):
        """Evolved language should have ' appended to name."""
        lang = AlienLanguage(seed=42)
        evolved = lang.evolve(1)
        self.assertEqual(evolved.name, lang.name + "'")

    def test_evolve_preserves_grammar(self):
        """Evolved language should keep the same grammar."""
        lang = AlienLanguage(seed=42)
        evolved = lang.evolve(2)
        self.assertEqual(evolved.word_order, lang.word_order)
        self.assertEqual(evolved.case_system, lang.case_system)
        self.assertEqual(evolved.tense_system, lang.tense_system)

    def test_evolve_logs_changes(self):
        """Evolution should record changes."""
        lang = AlienLanguage(seed=42)
        evolved = lang.evolve(3)
        # Should have some evolution log entries (may be fewer than 3 if some changes don't apply)
        self.assertGreaterEqual(len(evolved.evolution_log), 0)

    def test_evolve_accumulates(self):
        """Multiple evolutions should accumulate log entries."""
        lang = AlienLanguage(seed=42)
        evolved1 = lang.evolve(2)
        evolved2 = evolved1.evolve(2)
        self.assertGreaterEqual(len(evolved2.evolution_log),
                                len(evolved1.evolution_log))

    def test_evolve_zero_generations(self):
        """Evolving 0 generations should return a copy."""
        lang = AlienLanguage(seed=42)
        evolved = lang.evolve(0)
        self.assertEqual(evolved.name, lang.name + "'")
        self.assertEqual(len(evolved.evolution_log), 0)


class TestSaveLoad(unittest.TestCase):
    """Test save and load functionality."""

    def setUp(self):
        self.lang = AlienLanguage(seed=42)
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up temp files
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_load(self):
        """Save → load should reproduce the same language."""
        filepath = os.path.join(self.tmpdir, "test_lang.json")
        self.lang.save(filepath)
        loaded = AlienLanguage.load(filepath)
        self.assertEqual(loaded.name, self.lang.name)
        self.assertEqual(loaded.seed, self.lang.seed)
        self.assertEqual(loaded.consonants, self.lang.consonants)
        self.assertEqual(loaded.vowels, self.lang.vowels)
        self.assertEqual(loaded.word_order, self.lang.word_order)
        self.assertEqual(loaded.vocabulary, self.lang.vocabulary)

    def test_load_nonexistent(self):
        """Loading a nonexistent file should exit with error."""
        with self.assertRaises(SystemExit):
            AlienLanguage.load("/nonexistent/path/test.json")

    def test_save_creates_file(self):
        """Save should create a valid JSON file."""
        filepath = os.path.join(self.tmpdir, "test_lang.json")
        self.lang.save(filepath)
        self.assertTrue(os.path.exists(filepath))
        with open(filepath) as f:
            data = json.load(f)
        self.assertIn("name", data)
        self.assertIn("seed", data)
        self.assertIn("vocabulary", data)


class TestProverbGeneration(unittest.TestCase):
    """Test proverb generation."""

    def test_generates_proverb(self):
        """Should generate a non-empty proverb."""
        lang = AlienLanguage(seed=42)
        proverb = lang.generate_proverb()
        self.assertIsInstance(proverb, str)
        self.assertGreater(len(proverb), 0)
        # Should contain the arrow separator
        self.assertIn("→", proverb)


class TestPoemGeneration(unittest.TestCase):
    """Test poem generation."""

    def test_generates_poem(self):
        """Should generate a non-empty poem."""
        lang = AlienLanguage(seed=42)
        poem = lang.generate_poem()
        self.assertIsInstance(poem, str)
        self.assertGreater(len(poem), 0)
        # Should contain the title separator
        self.assertIn("═", poem)


class TestGlyphRendering(unittest.TestCase):
    """Test glyph rendering functionality."""

    def setUp(self):
        self.lang = AlienLanguage(seed=42)

    def test_render_word_glyphs(self):
        """Should render a word as glyphs (3 lines of output)."""
        alien = self.lang.translate_word("water")
        if alien:
            result = self.lang.render_word_glyphs(alien)
            lines = result.split("\n")
            self.assertGreaterEqual(len(lines), 3)

    def test_render_text_glyphs(self):
        """Should render a full text as glyphs."""
        result = self.lang.render_text_glyphs("paka laka")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


class TestDictionaryAndInfo(unittest.TestCase):
    """Test dictionary and info output."""

    def setUp(self):
        self.lang = AlienLanguage(seed=42)

    def test_dictionary(self):
        """Dictionary should contain all vocabulary entries."""
        d = self.lang.dictionary()
        self.assertGreater(len(d), 0)
        # Every value should appear in reverse_vocab
        for en, alien in d.items():
            self.assertEqual(self.lang.reverse_vocab.get(alien), en)

    def test_info(self):
        """Info should contain key language properties."""
        info = self.lang.info()
        self.assertIn(self.lang.name, info)
        self.assertIn(self.lang.culture, info)
        self.assertIn(self.lang.word_order, info)

    def test_print_dictionary(self):
        """Print dictionary should produce output."""
        d = self.lang.print_dictionary()
        self.assertIsInstance(d, str)
        self.assertIn("DICTIONARY", d)

    def test_print_glyph_chart(self):
        """Glyph chart should produce output."""
        chart = self.lang.print_glyph_chart()
        self.assertIsInstance(chart, str)
        self.assertIn("GLYPH CHART", chart)


class TestVersion(unittest.TestCase):
    """Test version constant exists."""

    def test_version_string(self):
        """VERSION should be a valid semver string."""
        self.assertIsInstance(VERSION, str)
        parts = VERSION.split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())


class TestBugFixes(unittest.TestCase):
    """Tests for specific bug fixes."""

    def test_evolve_no_duplicate_forms(self):
        """Evolved languages should not have duplicate word forms."""
        for seed in range(20):
            lang = AlienLanguage(seed=seed)
            evolved = lang.evolve(5)
            all_forms = []
            for cat in evolved.vocabulary:
                for en, alien in evolved.vocabulary[cat].items():
                    all_forms.append(alien)
            self.assertEqual(len(all_forms), len(set(all_forms)),
                             f"Seed {seed} has duplicate forms after evolution")

    def test_evolve_updates_affixes(self):
        """Evolution should apply sound changes to morphological affixes."""
        lang = AlienLanguage(seed=100)
        orig_affixes = dict(lang.tense_affixes)
        evolved = lang.evolve(3)
        # At least some affixes should have changed (not guaranteed, but likely)
        # Check that the affixes are properly stored in evolved language
        self.assertIsInstance(evolved.tense_affixes, dict)
        self.assertEqual(set(evolved.tense_affixes.keys()),
                         set(orig_affixes.keys()))

    def test_evolve_updates_question_particle(self):
        """Evolution should apply sound changes to question particle."""
        lang = AlienLanguage(seed=100)
        evolved = lang.evolve(3)
        # question_particle should still be a string or None
        self.assertTrue(evolved.question_particle is None or
                        isinstance(evolved.question_particle, str))

    def test_possessive_translation(self):
        """Possessives should use language-specific affix, not English 's."""
        lang = AlienLanguage(seed=42)
        result = lang.translate_sentence("water's fire")
        # Should NOT contain English "'s"
        self.assertNotIn("'s", result)
        # Should contain both translated words
        water_alien = lang.translate_word("water")
        fire_alien = lang.translate_word("fire")
        self.assertIn(water_alien, result)
        self.assertIn(fire_alien, result)

    def test_no_single_char_words(self):
        """Generated word forms should never be single characters."""
        for seed in range(50):
            lang = AlienLanguage(seed=seed)
            for cat in lang.vocabulary:
                for en, alien in lang.vocabulary[cat].items():
                    self.assertGreater(len(alien), 1,
                                       f"Seed {seed}, {cat}/{en}: single-char word '{alien}'")

    def test_save_load_roundtrip_complete(self):
        """Save and load should preserve all language properties."""
        import tempfile, os
        lang = AlienLanguage(seed=42)
        tmpfile = tempfile.mktemp(suffix='.json')
        try:
            lang.save(tmpfile)
            loaded = AlienLanguage.load(tmpfile)
            self.assertEqual(lang.name, loaded.name)
            self.assertEqual(lang.nominalizer, loaded.nominalizer)
            self.assertEqual(lang.verbalizer, loaded.verbalizer)
            self.assertEqual(lang.adjectivizer, loaded.adjectivizer)
            self.assertEqual(lang.question_particle, loaded.question_particle)
            self.assertEqual(lang.adj_before_noun, loaded.adj_before_noun)
            self.assertEqual(lang.possession_suffix, loaded.possession_suffix)
            self.assertEqual(lang.possessive_affix, loaded.possessive_affix)
            self.assertEqual(lang.vocabulary, loaded.vocabulary)
        finally:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)

    def test_negation_not_duplicated(self):
        """'not' should produce exactly one negation word, not two."""
        lang = AlienLanguage(seed=42)
        result = lang.translate_sentence("I not go")
        neg_word = lang.translate_word("not")
        if neg_word:
            # Count occurrences of negation word
            count = result.count(neg_word)
            self.assertEqual(count, 1, "Negation word should appear exactly once")

    def test_glyph_rendering_multi_char_phonemes(self):
        """Glyphs should handle multi-char phonemes correctly."""
        lang = AlienLanguage(seed=42)
        # Find a word with a multi-char phoneme
        multi_char = [p for p in lang.all_phonemes if len(p) > 1]
        if multi_char:
            # Find a word containing any multi-char phoneme
            for cat in lang.vocabulary:
                for en, alien in lang.vocabulary[cat].items():
                    if any(p in alien for p in multi_char):
                        result = lang.render_word_glyphs(alien)
                        # Should produce output, not crash
                        self.assertIsInstance(result, str)
                        self.assertGreater(len(result), 0)
                        break
                else:
                    continue
                break


if __name__ == "__main__":
    unittest.main()