# 🛸 Alien Language Generator v2.1.0

A procedural conlang (constructed language) generator that creates fully-formed alien languages with unique phonology, grammar, vocabulary, and a custom glyph-based writing system — all rendered as ASCII art in your terminal.

Every language is seeded, reproducible, and internally consistent, with cultural flavor that shapes the vocabulary. Languages can be evolved over generations with historically-inspired sound changes.

## Features

- **Procedural Phonology** — Random consonant and vowel inventories drawn from real-world phonetic categories, with configurable syllable structures (CV, CVC, CCV, VC)
- **Grammar Systems** — Six possible word orders (SVO, SOV, VSO, VOS, OVS, OSV), case systems (nominative-accusative, ergative-absolutive, tripartite, or none), tense systems, and number systems
- **Morphology** — Prefix or suffix affixes for case, tense, and number, plus derivational morphology (nominalizer, verbalizer, adjectivizer) and a possessive marker
- **Cultural Flavor** — Each language is themed around a culture (aquatic, desert, forest, mountain, cosmic, volcanic, arctic, swamp) that shapes vocabulary
- **~110 Word Vocabulary** — Pronouns, nouns, verbs, adjectives, adverbs, prepositions, conjunctions, and cultural words, all with guaranteed unique forms
- **Sentence Translation** — Translate English sentences into the alien language with grammar rules (article skipping, plurals, past tense, progressives, negation, possessives, question particles)
- **Reverse Translation** — Translate alien text back to English, with affix stripping for approximate lookups
- **Glyph Writing System** — Each phoneme gets a unique procedurally-generated ASCII glyph; words are rendered in the alien script with proper multi-char phoneme handling
- **Poetry Generation** — Generate structured poems with thematic coherence across stanzas
- **Language Evolution** — Evolve languages across generations with historically-inspired sound changes (lenition, fortition, vowel shifts, diphthongization, mergers, epenthesis, degemination) — applied to vocabulary, morphological affixes, and question particles
- **Duplicate Resolution** — When sound changes cause word-form collisions, duplicates are automatically disambiguated with phonologically appropriate suffixes
- **Interactive Mode** — Explore the language, translate text, generate proverbs and poems, browse the glyph chart, and evolve languages interactively
- **Save & Load** — Export languages as JSON (including all morphology, question particles, possession settings, and derivation markers) and reload them later
- **`--version` and `--help` flags** — Standard CLI interface with usage examples

## Installation

```bash
# No external dependencies — uses only Python 3 standard library
cd 2026-06-20-alien-language-generator
chmod +x alien_language.py
```

Requires Python 3.7+ (uses `dataclasses`, `argparse`, `hashlib`, `json`, `random`, `copy`).

## Usage

### Generate and explore a random language (interactive mode)

```bash
python3 alien_language.py
```

This opens an interactive prompt where you can:
- Type any English text to translate it (and see reverse translation)
- Use `/dict` to see the full dictionary
- Use `/info` to see language grammar overview
- Use `/chart` to see the glyph chart
- Use `/proverb` to generate an alien proverb
- Use `/poem` to generate a structured poem
- Use `/glyph <word>` to render a word in glyphs
- Use `/reverse <text>` to translate alien text back to English
- Use `/evolve <N>` to evolve the language N generations
- Use `/count` to see vocabulary statistics
- Use `/new` to generate a new random language
- Use `/save <file>` to save the language to JSON

### Use a specific seed for reproducibility

```bash
python3 alien_language.py --seed 42 --info
```

### Translate a sentence (with reverse translation and glyph rendering)

```bash
python3 alien_language.py --seed 42 --translate "the water flows"
```

### Reverse-translate alien text to English

```bash
python3 alien_language.py --seed 42 --reverse "bɛbqɛk pɛqɛbɛ"
```

### Generate a proverb

```bash
python3 alien_language.py --seed 42 --proverb
```

### Generate a poem

```bash
python3 alien_language.py --seed 42 --poem
```

### Evolve a language 5 generations with sound changes

```bash
python3 alien_language.py --seed 42 --evolve 5 --info
```

### Show vocabulary statistics

```bash
python3 alien_language.py --seed 42 --count
```

### Show the full dictionary

```bash
python3 alien_language.py --seed 42 --dict
```

### Show the glyph chart

```bash
python3 alien_language.py --seed 42 --chart
```

### Save a language to file

```bash
python3 alien_language.py --seed 42 -o my_language.json
```

### Load a saved language

```bash
python3 alien_language.py --load my_language.json --info
```

### Name your language

```bash
python3 alien_language.py --seed 42 --name "Xylorith" --info
```

### Show version

```bash
python3 alien_language.py --version
```

## Examples

### Language Overview (Seed 42 — "Thuro", Desert Culture)

```
╔════════════════════════════════════════════════════════════╗
║ Language: Thuro                                           ║
║ Culture: desert                                           ║
╠════════════════════════════════════════════════════════════╣
║ PHONOLOGY                                                 ║
║ Consonants: b, dz, dʒ, k, p, q, ts, tʃ, ʔ                 ║
║ Vowels:     ɛ, æ                                          ║
║ Syllables:  CV, CVC                                       ║
║                                                           ║
║ GRAMMAR                                                   ║
║ Word order:   OSV                                         ║
║ Case system:  tripartite (NOM, ACC, ERG)                  ║
║ Tense system: ternary (PRES, PAST, FUT)                   ║
║ Number:       plural (SG, PL)                             ║
║ Adj position: before noun                                 ║
║ Affix type:   prefixes                                    ║
║ Question:     particle 'tsæ'                              ║
║                                                           ║
║ MORPHOLOGY                                                ║
║   NOM: prefix 'qæb'                                       ║
║   ACC: prefix 'dzædz'                                     ║
║   ERG: prefix 'qɛdz'                                      ║
║   PRES: prefix 'kæ'                                       ║
║   PAST: prefix 'kɛ'                                       ║
║   FUT: prefix 'pæq'                                       ║
║   SG: prefix 'qæ'                                         ║
║   PL: prefix 'pæ'                                        ║
║   Nominalizer: 'kɛ'                                       ║
║   Verbalizer:  'kæb'                                      ║
║   Adjectivizer: 'qæ'                                      ║
║   Possessive:   prefix 'qɛ'                               ║
║                                                           ║
║ Vocabulary: 109 words                                     ║
╚════════════════════════════════════════════════════════════╝
```

### Translation with Possessives

```
$ python3 alien_language.py --seed 42 --translate "water's fire"

English: water's fire
Thuro: qɛ bɛbqɛk dʒædʒ
Back to English: possessive water fire
```

Possessives now use the language's own possessive marker instead of the English `'s`.

### Language Evolution (with affix evolution)

```
$ python3 alien_language.py --seed 42 --evolve 3 --info

Evolved language 3 generation(s). New name: Thuro'
  • Gen 1: Merger /tʃ/ → /b/
  • Gen 2: Epenthesis /kʔ/ → /kɛʔ/
  • Gen 3: Lenition /ts/ → /dz/

Question particle: tsæ → dzɛ (evolved by sound changes!)
Affixes also evolve: the question particle, case/tense/number affixes,
and derivational morphemes all undergo the same sound changes as vocabulary.
```

## How It Works

1. **Phonology** — Randomly selects consonants from phonetic manner categories (stops, fricatives, nasals, etc.) and vowels from height categories, then picks a syllable structure pattern (CV, CVC, CCV, etc.). Bare vowel (V-only) syllables are excluded to prevent degenerate single-character words.

2. **Grammar** — Randomly assigns word order, case alignment, tense system, and number system, creating typologically plausible combinations.

3. **Morphology** — Generates affix morphemes using the language's own phoneme inventory, applying them as prefixes or suffixes consistently. Includes a possessive marker for translation of English possessives.

4. **Vocabulary** — Creates a ~110-word lexicon organized by category, with each word generated as a random sequence of valid syllables. Uniqueness of all word forms is enforced with retry logic.

5. **Writing System** — Each phoneme gets a procedurally generated 3×3 ASCII glyph. Multi-char phonemes (like `ts`, `dʒ`) are properly parsed and rendered as single glyphs using longest-match-first tokenization.

6. **Translation** — Word-by-word translation with grammar rules: articles (the/a/an) are skipped, negation (`not`/`don't`/`doesn't`) uses a dedicated particle, possessives use the language's own marker, plurals and past tenses are detected, and question particles are appended to questions.

7. **Evolution** — Applies historically-inspired sound changes to vocabulary AND morphological affixes/question particles. When sound changes create duplicate word forms, they are automatically disambiguated with phonologically appropriate suffixes.

8. **Poetry** — Generates structured verse with 2–4 stanzas, each 2–4 lines, using thematic templates for coherence.

9. **Save/Load** — Full round-trip serialization preserves all language data: morphology, question particles, possessive settings, adjective placement, derivation markers, and evolution history.

## Running Tests

```bash
python3 -m pytest test_alien_language.py -v
```

The test suite (51 tests) covers:
- Seed determinism and reproducibility
- Vocabulary generation and uniqueness
- Translation and reverse translation
- Morphological inflection
- Language evolution (no duplicate forms, affixes evolve)
- Save/load round-tripping (including all morphology fields)
- Glyph generation and rendering (including multi-char phonemes)
- Proverb and poem generation
- Possessive translation (no English `'s` in output)
- No single-character word forms
- Negation not duplicated
- CLI version and help flags
- Error handling (missing files, invalid JSON)

## Changelog

### v2.1.0 — Bug Fix Release

**Bugs Fixed:**
- **Evolve creates duplicate word forms** — Sound changes (mergers, assimilation) could map two different English words to the same alien form, breaking `reverse_vocab`. Now duplicates are automatically disambiguated with phonologically appropriate suffixes. (55% of seeds were affected)
- **Dead code in negation handling** — `don't`/`doesn't` were caught by both line 496 and the unreachable line 504. Removed the dead code path.
- **Possessive handling was identical in both branches** — Both prefix and suffix branches just appended English `'s`. Now uses the language's own possessive affix marker (prefix or suffix based on `prefix_mode`).
- **Evolve didn't update morphological affixes** — Case affixes, tense affixes, number affixes, nominalizer, verbalizer, adjectivizer, possessive marker, and question particle were all left unchanged by evolution. Sound changes are now applied to all morphological elements.
- **Save/load was incomplete** — `cultural_words`, `adj_before_noun`, `possession_suffix`, `question_particle`, `nominalizer`, `verbalizer`, `adjectivizer`, and `possessive_affix` were missing from serialization. Full round-trip now preserves all fields.
- **Single-character vowel words** — Syllable patterns including bare `V` could produce single-character words (e.g., just `a` or `ɨ`), which are fragile and collision-prone. Removed bare `V` from syllable pattern choices.
- **Glyph rendering didn't handle multi-char phonemes** — The `render_word_glyphs` method used `phoneme_to_char.values()` lookup which failed for multi-char phonemes like `ts`, `dʒ`. Replaced with proper longest-match-first phoneme tokenization.
- **`RuntimeError` during evolve duplicate resolution** — Dictionary was modified during iteration. Fixed by collecting duplicates first, then resolving them separately.

**New Features:**
- Possessive affix is now displayed in the `--info` output
- Added 8 new regression tests covering all fixed bugs
- Version bumped to 2.1.0

## License

MIT