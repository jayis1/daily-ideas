# 🔮 Spell Grimoire Generator

**Procedural fantasy RPG spell generator** — create unique, detailed spells with ASCII art sigils, incantations, casting recipes, power ratings, and more.

## Features

### Core Spell Generation
- **8 magic schools**: Abjuration, Conjuration, Divination, Enchantment, Evocation, Illusion, Necromancy, Transmutation
- **10 spell levels**: Cantrip through 9th level, each with appropriate power scaling
- **5 rarity tiers**: Common, Uncommon, Rare, Very Rare, Legendary
- **Procedural names**: Unique spell names generated from school-specific prefix/suffix pools
- **Rich descriptions**: Grammar-based procedural descriptions with damage, effects, and durations

### Visual Output
- **ASCII art sigils**: Deterministic geometric patterns unique to each spell
- **Spell diagrams**: Visual casting diagrams with range, area, and orientation
- **Colorful terminal rendering**: School-colored headers, dim lore text, bold key info
- **Box-drawing character pages**: Beautiful framed grimoire pages
- **`--no-color` support**: Clean plaintext output free of ANSI escape sequences

### Detailed Spell Components
- **Casting time, range, duration**: All procedurally generated and internally consistent
- **Verbal & somatic components**: Detailed descriptions of gestures and chant patterns
- **Material components**: School-specific materials from curated flavor pools
- **Incantations**: Latin-infused magical phrases
- **Lore / backstory**: Procedural flavor text with wizard names and arcane history
- **Higher-level scaling**: Auto-generated "At Higher Levels" descriptions for levels 2–8
- **Tags**: Auto-generated keywords (school, rarity, damage type, cantrip/epic)

### Power & Value Systems
- **Mana cost calculation**: Weighted formula based on level, school, rarity, casting time, and duration
- **Scroll value**: Gold piece price scaled by level and rarity
- **Power rating**: 0–100 composite score based on level, rarity, mana cost, range, and components
- **Casting recipe**: Step-by-step ritual instructions themed by magic school
- **Compatibility scoring**: How well two spells work together based on school alignment and rarity

### Output Formats
- **Terminal** (default): Colorful boxed grimoire pages
- **JSON**: Structured data export with all fields
- **Markdown**: GitHub-flavored markdown with headers and tables
- **HTML**: Standalone styled HTML document
- **LaTeX**: Full standalone `.tex` document ready for PDF compilation
- **Plain text**: Stripped of ANSI codes for piping/logging

### Comparison & Analysis Modes
- **Side-by-side comparison**: Two spells rendered adjacently
- **Synergy detection**: Find complementary spell pairs
- **Conflict detection**: Identify opposing school combinations
- **Statistics**: Aggregate stats across multiple spells
- **Power ranking**: Rank spells by power rating with visual bars
- **All-schools overview**: Generate one spell per school in a summary table
- **Compatibility check**: Score and describe how two spells interact

### Interactive Mode
- Full menu-driven interface with 15+ options
- Spell history tracking within session
- Save/load spells to JSON files

### CLI Flags

| Flag | Description |
|------|-------------|
| `--school <school>` | Generate spell from a specific school |
| `--level <1-9>` | Generate spell at a specific level (0 = cantrip) |
| `--rarity <tier>` | Set rarity: Common, Uncommon, Rare, Very Rare, Legendary |
| `--count <n>` | Generate multiple spells |
| `--json` | Output as JSON |
| `--markdown` | Output as Markdown |
| `--html` | Output as HTML |
| `--latex` | Output as LaTeX |
| `--no-color` | Disable ANSI colors |
| `--output <file>` | Write output to file |
| `--save <file>` | Save spells to JSON file |
| `--load <file>` | Load spells from JSON file |
| `--compare` | Compare two spells side by side |
| `--synergies <n>` | Find synergies among n spells |
| `--conflicts <n>` | Find conflicts among n spells |
| `--stats <n>` | Show statistics for n spells |
| `--power-ranking <n>` | Generate n spells and rank by power |
| `--all-schools` | One spell per school overview |
| `--compatibility` | Score compatibility of two spells |
| `--seed <int>` | Set random seed for reproducibility |
| `--interactive` | Launch interactive menu mode |
| `--version` | Show version |

## Installation

```bash
# No dependencies needed — uses only Python 3.8+ standard library
git clone <repo-url>
cd spell-grimoire-generator
python3 grimoire.py
```

## Quick Start

```bash
# Generate a random spell
python3 grimoire.py

# Generate a 5th-level Evocation spell
python3 grimoire.py --school Evocation --level 5

# Generate 3 spells and rank by power
python3 grimoire.py --power-ranking 3 --seed 42

# See all schools at a glance
python3 grimoire.py --all-schools

# Check compatibility between two spells
python3 grimoire.py --compatibility --seed 7

# Export to LaTeX
python3 grimoire.py --school Necromancy --latex --output spell.tex

# Export to HTML file
python3 grimoire.py --html --output spell.html

# Save spells to JSON
python3 grimoire.py --count 5 --save spells.json

# Load and re-display saved spells
python3 grimoire.py --load spells.json

# Interactive mode
python3 grimoire.py --interactive
```

## Running Tests

```bash
python3 -m pytest test_grimoire.py -v
# Or: python3 test_grimoire.py
```

165 tests covering spell generation, rendering, exports, CLI flags, LaTeX escaping, ANSI handling, and all features.

## Changelog

### v5.0.1 — Bug Fixes
- **Fixed LaTeX `_latex_escape` double-encoding bug**: The `\`, `^`, and `~` characters were being double-encoded. A backslash `\` would become `\textbackslash\{\}` instead of `\textbackslash{}` because the `{` and `}` from the textbackslash replacement were being re-escaped by the subsequent `{`/`}` replacement steps. Fixed by using placeholder tokens to protect the braces in `\textbackslash{}`, `\^{}`, and `\~{}` from re-escaping.
- **Fixed ANSI codes leaking into `--no-color` output**: Five rendering lines in `render_grimoire_page` used `DIM`, `ITALIC`, `BOLD`, and `rst` ANSI escape sequences without checking the `color` flag. This caused ANSI codes (`\x1b[2m` dim, `\x1b[3m` italic, `\x1b[1m` bold) to appear in plaintext/no-color output, affecting material details, tags, incantations, lore text, and power rating display. All five lines now properly gate ANSI codes behind the `color` parameter.
- **Added regression tests**: `test_render_page_no_ansi_with_color_false` and `test_latex_escape_no_double_encoding` to prevent these bugs from recurring.

## What It Does

The Spell Grimoire Generator creates unique, flavorful RPG spells on demand. Each spell includes:

1. **Name & School** — Procedurally generated from thematic word pools
2. **Level & Rarity** — Controlled via CLI flags or randomized
3. **Casting Time, Range, Duration** — Consistent with spell level
4. **Components** — Verbal, somatic, and material with flavor descriptions
5. **Description** — Grammar-based procedural effect text
6. **Sigil** — Deterministic ASCII art pattern unique to the spell
7. **Spell Diagram** — Visual representation of casting geometry
8. **Incantation** — Latin-inspired magical phrase
9. **Lore** — Procedural backstory featuring wizard names and arcane history
10. **Higher Levels** — Scaling description for spells levels 2–8
11. **Tags** — Auto-generated keywords for filtering
12. **Mana Cost** — Calculated from level, school, rarity, casting time, duration
13. **Scroll Value** — Gold piece price for scribing
14. **Power Rating** — 0–100 composite score
15. **Casting Recipe** — Step-by-step ritual instructions

## License

MIT