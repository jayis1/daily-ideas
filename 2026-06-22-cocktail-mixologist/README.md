# 🍹 Terminal Cocktail Mixologist

A procedural cocktail recipe generator that creates unique, plausible cocktail recipes with creative names, balanced flavor profiles, ASCII art glassware, and atmospheric backstory. Never make the same drink twice.

## Features

- **Procedural Generation** — Combines base spirits, liqueurs, mixers, bitters, and garnishes using flavor harmony rules to create balanced, believable cocktails
- **7 Style Profiles** — Classic, Tropical, Strong, Fizzy, Dessert, Bitter, and Sour — each with weighted method, glass, and ingredient distributions
- **Creative Naming** — 12 naming templates + 48 adjectives + 48 nouns = thousands of unique cocktail names ("The Crimson Sparrow", "Nebula's Kiss", "Twilight Comet Spritz No. 7")
- **Atmospheric Stories** — Each cocktail gets a procedurally generated origin story (speakeasy legends, rooftop bar discoveries, poet-turned-barkeep inventions)
- **ASCII Art Glassware** — 14 different glass types rendered in ASCII art, matched to cocktail style
- **Strength Meters** — Visual ABV bars with LIGHT/MEDIUM/STRONG/POTENT ratings
- **Full Menu Mode** — Generate complete cocktail menus with formatted ASCII menu cards
- **Shopping Lists** — Consolidated ingredient lists across multiple cocktails
- **JSON Export** — Machine-readable output for integration with other tools
- **Reproducible** — Seed-based random generation for repeatable results

## How to Install

No external dependencies required — uses only Python standard library.

```bash
# Just make it executable
chmod +x cocktail_mixologist.py
```

Requires Python 3.6+.

## How to Run

### Single Cocktail
```bash
python3 cocktail_mixologist.py
```

### Multiple Cocktails
```bash
python3 cocktail_mixologist.py -n 5
```

### By Style
```bash
python3 cocktail_mixologist.py -s tropical
python3 cocktail_mixologist.py -n 3 -s classic
```

Available styles: `classic`, `tropical`, `strong`, `fizzy`, `dessert`, `bitter`, `sour`

### JSON Output
```bash
python3 cocktail_mixologist.py -n 3 --json
```

### Reproducible (Seeded)
```bash
python3 cocktail_mixologist.py --seed 42
```

### Interactive Mode
```bash
python3 cocktail_mixologist.py --interactive
```

Interactive mode lets you:
1. Generate a random cocktail
2. Generate by style
3. Generate a full 5-drink menu
4. Generate a themed menu (tiki night, speakeasy, dive bar, brunch, etc.)
5. Generate a cocktail pairing (2 complementary drinks)

## Usage Examples

```
$ python3 cocktail_mixologist.py --seed 7

╔══════════════════════════════════════════════════════════════╗
║                        COCKTAIL MENU                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. Shadow's Mystic                               21.2% ABV  ║
║     tart, spicy and sweet · shaken · hurricane glass         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

Each recipe card includes:
- Creative cocktail name
- Flavor profile summary
- Difficulty rating
- Glassware with ASCII art
- Ice type and preparation method
- Full ingredient list with measurements and ABV
- Garnish suggestion
- Visual strength meter
- Procedurally generated origin story

## How It Works

1. **Style Selection** — A style profile determines weighted probabilities for preparation methods, glassware, and ingredient counts
2. **Base Spirit** — Randomly selected from 12 spirits (gin, vodka, rums, whiskeys, tequilas, mezcal, brandy, cachaça)
3. **Liqueur Selection** — 0-2 liqueurs chosen based on style profile
4. **Mixer Selection** — 0-3 mixers selected with a 70% bias toward harmonious flavor pairings
5. **Bitters** — 0-2 dashes of bitters for depth
6. **Garnish** — Randomly paired from 20 garnish options
7. **Naming** — A random naming template combines adjectives and nouns
8. **Story** — Procedural backstory fills in venue, bartender, era, and mood
9. **Stats** — ABV and total volume calculated from ingredient data

Flavor harmony rules ensure that ingredients complement each other (e.g., smoky spirits pair with sweet/tropical mixers, herbal bases pair with citrus/bitter additions).

## License

MIT