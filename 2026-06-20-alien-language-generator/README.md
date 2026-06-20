# 🛸 Alien Language Generator

A procedural conlang (constructed language) generator that creates fully-formed alien languages with unique phonology, grammar, vocabulary, and a custom glyph-based writing system — all rendered as ASCII art in your terminal.

Every language is different. Each one is seeded, reproducible, and internally consistent, with cultural flavor that influences the vocabulary.

## Features

- **Procedural Phonology** — Random consonant and vowel inventories drawn from real-world phonetic categories, with configurable syllable structures
- **Grammar Systems** — Six possible word orders (SVO, SOV, VSO, VOS, OVS, OSV), case systems (nominative-accusative, ergative-absolutive, tripartite, or none), tense systems, and number systems
- **Morphology** — Prefix or suffix affixes for case, tense, and number, plus derivational morphology (nominalizer, verbalizer, adjectivizer)
- **Cultural Flavor** — Each language is themed around a culture (aquatic, desert, forest, mountain, cosmic, volcanic, arctic, swamp) that shapes vocabulary
- **200+ Word Vocabulary** — Pronouns, nouns, verbs, adjectives, adverbs, prepositions, conjunctions, and cultural words
- **Sentence Translation** — Translate English sentences into the alien language with basic grammar application
- **Glyph Writing System** — Each phoneme gets a unique procedurally-generated ASCII glyph; words are rendered in the alien script
- **Interactive Mode** — Explore the language, translate text, generate proverbs, and browse the glyph chart interactively
- **Save & Load** — Export languages as JSON and reload them later

## Installation

```bash
# No external dependencies — uses only Python 3 standard library
cd 2026-06-20-alien-language-generator
chmod +x alien_language.py
```

Requires Python 3.7+ (uses `dataclasses`, `argparse`, `hashlib`, `json`, `random`).

## Usage

### Generate and explore a random language (interactive mode)

```bash
python3 alien_language.py
```

This opens an interactive prompt where you can:
- Type any English text to translate it
- Use `/dict` to see the full dictionary
- Use `/info` to see language grammar overview
- Use `/chart` to see the glyph chart
- Use `/proverb` to generate an alien proverb
- Use `/glyph <word>` to render a word in glyphs
- Use `/new` to generate a new random language

### Use a specific seed for reproducibility

```bash
python3 alien_language.py --seed 42 --info
```

### Translate a sentence

```bash
python3 alien_language.py --seed 42 --translate "the water flows"
```

### Generate a proverb

```bash
python3 alien_language.py --seed 42 --proverb
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

## Examples

### Language Overview (Seed 42 — "Thuro", Desert Culture)

```
╔════════════════════════════════════════════════════════════╗
║  Language: Thuro                                          ║
║  Culture: desert                                           ║
╠════════════════════════════════════════════════════════════╣
║  PHONOLOGY                                                   ║
║  Consonants: b, dz, dʒ, k, p, q, ts, tʃ, ʔ                   ║
║  Vowels:     æ, ɛ                                             ║
║  Syllables:  CV, CVC                                          ║
║                                                              ║
║  GRAMMAR                                                     ║
║  Word order:   OSV                                            ║
║  Case system:  tripartite (NOM, ACC, ERG)                      ║
║  Tense system: ternary (PRES, PAST, FUT)                      ║
║  Number:       plural (SG, PL)                                ║
║  Affix type:   prefixes                                        ║
║  Question:     particle 'tsæ'                                  ║
```

### Proverb Generation

```
A hot stone always loses.
→ [a] dzɛdzk pæ tʃɛbɛqpæ pɛdʒædʒtsɛ
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

4. **Vocabulary** — Creates a ~200-word lexicon organized by category (pronouns, basic nouns, cultural nouns, verbs, adjectives, etc.), with each word generated as a random sequence of valid syllables

5. **Writing System** — Each phoneme gets a procedurally generated 3×3 ASCII glyph using box-drawing characters, geometric shapes, and fill patterns. The glyphs are arranged horizontally to spell words, making each language visually distinct

6. **Translation** — Simple word-by-word translation with basic grammar application (affix insertion, question particles), handling English morphological variants (plurals, past tense, progressives)

## License

MIT