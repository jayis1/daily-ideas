# 🍹 Terminal Cocktail Mixologist

**Procedural cocktail recipe generator** — creates unique, plausible cocktail recipes with creative names, flavor balance scoring, ingredient substitutions, ASCII art glassware, pairing compatibility, and atmospheric backstory. Never make the same drink twice.

## Features

### Core Generation
- **7 style profiles**: Classic, Tropical, Strong, Fizzy, Dessert, Bitter, Sour — each with weighted method, glass, and ingredient distributions
- **12 base spirits**: Gin, vodka, rums, whiskeys, tequilas, mezcal, brandy, cachaça
- **18 liqueurs** and **27 mixers** (including 3 bitters varieties) with flavor harmony rules for balanced combinations
- **12 naming templates** + 48 adjectives + 48 nouns = thousands of unique cocktail names
- **Atmospheric origin stories** procedurally generated from template pools

### Flavor Intelligence
- **Flavor balance scoring** (0–100): Rates how well-balanced a cocktail's flavor profile is across sweet/sour/bitter/herbal/fruity/spicy/strong/creamy dimensions
- **Verbose mode** (`--verbose`): Shows detailed flavor breakdown with bar charts and ingredient substitution suggestions
- **Ingredient substitution system**: Suggests alternatives for base spirits, liqueurs, and mixers with flavor reasoning

### Cocktail Pairing
- **`--pairing` mode**: Generates a complementary cocktail pair with a compatibility score (0–100), star rating, and explanation
- **Pairing algorithm**: Considers style compatibility, ABV progression, flavor overlap, and base spirit diversity
- **13 style compatibility rules** with flavor-based explanations

### Visual Output
- **ASCII art glassware**: 14 different glass types rendered in ASCII art
- **Visual ABV strength bars**: LIGHT/MEDIUM/STRONG/POTENT ratings with block character bars
- **Flavor balance visualization**: Bar charts showing relative intensity of each flavor category (verbose mode)
- **Box-drawing character cards**: Beautiful framed recipe cards
- **Pairing comparison cards**: Side-by-side compatibility display

### Export & Persistence
- **Terminal** (default): Colorful ASCII recipe cards
- **JSON export** (`--json`): Machine-readable output including balance scores and pairing data
- **Save/Load** (`--save`/`--load`): Persist cocktails to JSON files for later display

### Interactive Mode
- Full menu-driven interface with 5 options
- Random generation, style selection, full menus, themed menus, pairings

## Installation

No external dependencies required — uses only Python 3.6+ standard library.

```bash
# Clone and run
git clone <repo-url>
cd cocktail-mixologist
python3 cocktail_mixologist.py
```

## Usage

### Basic Generation
```bash
# Generate a random cocktail
python3 cocktail_mixologist.py

# Generate a specific style
python3 cocktail_mixologist.py -s tropical
python3 cocktail_mixologist.py -s classic
python3 cocktail_mixologist.py -s strong

# Generate multiple cocktails
python3 cocktail_mixologist.py -n 5
python3 cocktail_mixologist.py -n 3 -s bitter

# Reproducible output
python3 cocktail_mixologist.py --seed 42
```

### Verbose Mode
```bash
# Show flavor balance breakdown and substitution suggestions
python3 cocktail_mixologist.py --verbose
python3 cocktail_mixologist.py -n 2 -s dessert --verbose
```

Verbose mode adds:
- **Flavor balance bars**: Visual breakdown of sweet/sour/bitter/herbal/etc. intensity
- **Substitution suggestions**: Alternative ingredients with flavor reasoning (e.g., "↻ London Dry Gin → Premium Vodka (Neutral spirit, less botanical)")

### Pairing Mode
```bash
# Generate a complementary cocktail pair
python3 cocktail_mixologist.py --pairing

# Pair with a specific starting style
python3 cocktail_mixologist.py --pairing -s classic

# Pair with verbose details
python3 cocktail_mixologist.py --pairing --verbose --seed 42
```

Pairing output includes:
- ★★★ Perfect Pairing / ★★☆ Great Match / ★☆☆ Good Together / ☆☆☆ Different Vibes
- Compatibility score (0–100)
- Explanation of why the pair works (or doesn't)

### JSON Export
```bash
# Export cocktails as JSON
python3 cocktail_mixologist.py -n 3 --json

# Export pairing as JSON (includes pairing score)
python3 cocktail_mixologist.py --pairing --json --seed 42
```

### Save & Load
```bash
# Save cocktails to a JSON file
python3 cocktail_mixologist.py -n 5 --save cocktails.json

# Load and display saved cocktails
python3 cocktail_mixologist.py --load cocktails.json

# Load with verbose display
python3 cocktail_mixologist.py --load cocktails.json --verbose
```

### Interactive Mode
```bash
python3 cocktail_mixologist.py --interactive
```

Options:
1. Generate a random cocktail
2. Generate by style
3. Generate a full 5-drink menu
4. Generate a themed menu (tiki night, speakeasy, dive bar, brunch, etc.)
5. Generate a cocktail pairing (2 complementary drinks)

### All CLI Flags

| Flag | Description |
|------|-------------|
| `-n, --number <N>` | Number of cocktails to generate (default: 1) |
| `-s, --style <style>` | Cocktail style: classic, tropical, strong, fizzy, dessert, bitter, sour |
| `--pairing` | Generate a complementary cocktail pair with compatibility score |
| `--verbose, -v` | Show flavor balance breakdown and substitution suggestions |
| `--json` | Output as JSON (includes balance scores, pairing data) |
| `--save <file>` | Save generated cocktails to a JSON file |
| `--load <file>` | Load and display cocktails from a JSON file |
| `--seed <int>` | Random seed for reproducible generation |
| `--interactive, -i` | Launch interactive menu mode |
| `--version` | Show version (v2.0.0) |

## How It Works

1. **Style Selection**: A style profile determines weighted probabilities for preparation methods, glassware, and ingredient counts
2. **Base Spirit**: Randomly selected from 12 spirits (gin, vodka, rums, whiskeys, tequilas, mezcal, brandy, cachaça)
3. **Liqueur Selection**: 0–2 liqueurs chosen based on style profile
4. **Mixer Selection**: 0–3 mixers selected with a 70% bias toward harmonious flavor pairings
5. **Bitters**: 0–2 dashes of bitters for depth (each dash = 0.03 oz of 35–44% ABV spirit)
6. **Garnish**: Randomly paired from 20 garnish options
7. **Naming**: A random naming template combines adjectives and nouns
8. **Story**: Procedural backstory fills in venue, bartender, era, and mood
9. **Stats**: ABV and total volume calculated from ingredient data (including bitters alcohol content)
10. **Balance Score**: Flavor harmony scored across 8 flavor dimensions
11. **Pairing**: Style compatibility, ABV progression, and flavor overlap analyzed

Flavor harmony rules ensure that ingredients complement each other (e.g., smoky spirits pair with sweet/tropical mixers, herbal bases pair with citrus/bitter additions).

## Running Tests

```bash
python3 -m pytest test_cocktail_mixologist.py -v
# Or: python3 test_cocktail_mixologist.py
```

48 tests covering cocktail generation, flavor balance, pairing, substitutions, save/load, rendering, CLI flags, bug fixes, and all features.

## Changelog

### v2.0.1 — Bug Fixes
- **Fixed `score_cocktail_pairing` crash on empty ingredient lists** — accessing `c.ingredients[0].key` without bounds check caused `IndexError` on empty cocktails
- **Fixed invalid substitution target keys** — `"white_rum"` was referenced in substitutions but doesn't exist in any ingredient pool; changed to `"rum_light"` (the actual key)
- **Fixed story generation `trait2` bug** — `random.choice(traits)` was evaluated per-iteration in the list comprehension, causing `trait2` to equal `trait` ~17% of the time; now correctly ensures they're always different
- **Fixed story double-article bug** — Templates "by a {bartender}" and "A {bartender}" produced "by a a retired sailor" since bartender strings already include articles; removed redundant articles
- **Fixed bitters ABV** — Bitters (Aromatic, Orange, Peach) had ABV=0% but real bitters are 35–44% ABV concentrated spirits; now correctly set to 44%, 40%, 35% respectively, producing accurate cocktail ABV calculations
- **Fixed bitters amount** — Bitters were assigned amount_oz=1 (1 oz!) instead of 0.03 oz (a proper dash); this inflated total volume and understated cocktail ABV significantly
- **Fixed bitters display** — Recipe cards now show "1 dash" / "2 dashes" for bitters instead of fractional ounces
- **Fixed shopping list entry parsing** — Removed dead code that used `split('(')` to parse cocktail names from entries, which would break on names containing parentheses; now stores names directly
- **Fixed shopping list category alignment** — Category labels now dynamically padded instead of using a hardcoded 37-char pad that could misalign

### v2.0.0 — Initial Enhanced Release
- Flavor balance scoring (0–100)
- Cocktail pairing mode with compatibility analysis
- Ingredient substitution suggestions
- Save/load support for JSON persistence
- Verbose mode with flavor breakdown bars
- 40 comprehensive tests

## License

MIT