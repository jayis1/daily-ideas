# 🛸 Alien Language Generator

A procedural conlang (constructed language) generator that creates fully-formed alien languages with unique phonology, grammar, vocabulary, and a custom glyph-based writing system — all rendered as ASCII art in your terminal.

Every language is seeded, reproducible, and internally consistent, with cultural flavor that shapes the vocabulary. Languages can be evolved over generations with historically-inspired sound changes.

## Features

- **Procedural Phonology** — Random consonant and vowel inventories drawn from real-world phonetic categories, with configurable syllable structures
- **Grammar Systems** — Six possible word orders (SVO, SOV, VSO, VOS, OVS, OSV), case systems (nominative-accusative, ergative-absolutive, tripartite, or none), tense systems, and number systems
- **Morphology** — Prefix or suffix affixes for case, tense, and number, plus derivational morphology (nominalizer, verbalizer, adjectivizer)
- **Cultural Flavor** — Each language is themed around a culture (aquatic, desert, forest, mountain, cosmic, volcanic, arctic, swamp) that shapes vocabulary
- **200+ Word Vocabulary** — Pronouns, nouns, verbs, adjectives, adverbs, prepositions, conjunctions, and cultural words
- **Sentence Translation** — Translate English sentences into the alien language with grammar rules (articles skipped, plurals, past tense, progressives, negation, question particles)
- **Reverse Translation** — Translate alien text back to English, with affix stripping for approximate lookups
- **Glyph Writing System** — Each phoneme gets a unique procedurally-generated ASCII glyph; words are rendered in the alien script
- **Poetry Generation** — Generate structured poems with thematic coherence across stanzas
- **Language Evolution** — Evolve languages across generations with historically-inspired sound changes (lenition, fortition, vowel shifts, diphthongization, mergers, epenthesis, degemination)
- **Interactive Mode** — Explore the language, translate text, generate proverbs and poems, browse the glyph chart, and evolve languages interactively
- **Save & Load** — Export languages as JSON and reload them later
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
║ Vowels:     æ, ɛ                                          ║
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
║   NOM: prefix 'qɛb'                                       ║
║   ACC: prefix 'dzɛdz'                                     ║
║   ERG: prefix 'qædz'                                      ║
║   ...                                                      ║
║                                                           ║
║ Vocabulary: 109 words                                     ║
╚════════════════════════════════════════════════════════════╝
```

### Translation with Reverse Lookup

```
$ python3 alien_language.py --seed 42 --translate "the water flows"

English: the water flows
Thuro: bɛbqɛk pɛqɛbɛ
Back to English: water flow

Glyphs:
─⬢▽ ─░─ ─⬢▽ ┴   ─░─ ╲─━
○ ┃ ▲ │ ○ ┃ ╔⬡  ▲ │ │╲╚
──■ ━── ──■  ┴╝ ━── ┴─▒
```

### Proverb Generation

```
A hot stone always loses.
→ dzɛdzɛk pæ tʃɛbɛqpæ pɛdʒædʒtsɛ
```

### Poem Generation

```
══ The Mystical Prayer of Thuro ══

say the stone, say the stone
In the sun, sun says
...
```

### Language Evolution

```
$ python3 alien_language.py --seed 42 --evolve 3 --info
Evolved language 3 generation(s). New name: Thuro'
  • Gen 1: Degemination /tsts/ → /ts/
  • Gen 2: Merger /ʔ/ → /q/
  • Gen 3: Degemination /tʃtʃ/ → /tʃ/
```

### Glyph Rendering

Words are rendered as columns of 3×3 glyph blocks — each phoneme maps to a unique symbol:

```
━⬢━ ━─⊙ ━⬢━ ▓⬡─ ━─⊙ ─━━
│∘┃ ⬡  ┃  │∘┃ │∘│ ⬡  ┃  │◆│
──├ ─━─ ──├ ─░─ ─━─ ━━─
```

## How It Works

1. **Phonology** — Randomly selects consonants from phonetic manner categories (stops, fricatives, nasals, etc.) and vowels from height categories, then picks a syllable structure pattern (CV, CVC, etc.)

2. **Grammar** — Randomly assigns word order, case alignment, tense system, and number system, creating typologically plausible combinations

3. **Morphology** — Generates affix morphemes using the language's own phoneme inventory, applying them as prefixes or suffixes consistently

4. **Vocabulary** — Creates a ~200-word lexicon organized by category (pronouns, basic nouns, cultural nouns, verbs, adjectives, etc.), with each word generated as a random sequence of valid syllables. Uniqueness of all word forms is enforced.

5. **Writing System** — Each phoneme gets a procedurally generated 3×3 ASCII glyph using box-drawing characters, geometric shapes, and fill patterns. The glyphs are arranged horizontally to spell words, making each language visually distinct

6. **Translation** — Word-by-word translation with grammar application (article skipping, affix insertion, question particles, negation handling, plural/past-tense/progressive detection), plus reverse translation with affix stripping

7. **Evolution** — Applies historically-inspired sound changes (lenition, fortition, vowel shifts, diphthongization, mergers, epenthesis, degemination) to evolve vocabulary across generations while preserving grammar structure

8. **Poetry** — Generates structured verse with 2–4 stanzas, each 2–4 lines, using thematic templates to create coherence within and across stanzas

## Running Tests

```bash
python3 -m pytest test_alien_language.py -v
```

The test suite covers:
- Seed determinism and reproducibility
- Vocabulary generation and uniqueness
- Translation and reverse translation
- Morphological inflection
- Language evolution and change logging
- Save/load round-tripping
- Glyph generation and rendering
- Proverb and poem generation
- CLI version and help flags
- Error handling (missing files, invalid JSON)

## License

MIT