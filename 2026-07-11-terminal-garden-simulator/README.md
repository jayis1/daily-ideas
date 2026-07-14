# 🌻 Terminal Garden Simulator

A procedural ASCII garden simulator where you plant, grow, water, fertilize, and harvest procedural plants through changing seasons and weather. Manage your garden across Spring, Summer, Autumn, and Winter — each with unique weather patterns, growth modifiers, and random pest events.

## Features

- **8 Plant Types**: Sunflower, Rose, Cactus, Mushroom, Fern, Oak Tree, Tulip, and Vine — each with unique growth rates, water needs, and season preferences
- **7 Growth Stages**: Seed → Sprout → Growing → Mature → Flowering → Fruiting → Withering → Dead
- **4 Seasons**: Spring (rainy), Summer (hot), Autumn (mushroom-friendly), Winter (harsh) — each lasting 28 days
- **Dynamic Weather**: Clear, Cloudy, Rainy, Stormy, Hot, and Windy conditions affect plant growth and water levels
- **Weather Forecast**: Press T to see upcoming weather and plan your garden strategy
- **Fertilizer System**: Apply fertilizer (F key) to boost growth by 1.5× for 3 days; buy more at the shop
- **Pest Events**: Random insect attacks can damage your plants — watch out for aphids, caterpillars, slugs, beetles, and mites
- **Composting**: Clear dead plants with H to recover 3g each instead of just removing them
- **Procedural ASCII Art**: Each plant renders differently based on type, stage, and growth — with slight randomization each day
- **Economy System**: Earn gold by harvesting mature plants, spend it at the seed shop
- **Overwatering & Storm Damage**: Plants can suffer from too much water or stormy weather
- **Seed Shop**: Buy new seed types and fertilizer with earned gold
- **Save/Load**: Game state persists between sessions (V to save, auto-loads on start)
- **Statistics**: View game stats with `--stats`
- **Demo Mode**: Preview the garden with `--demo`

## How to Install

No external dependencies required — uses only Python's standard library:

```bash
# Just clone and run
git clone <repo-url>
cd terminal-garden-simulator
```

Requires Python 3.7+ (uses `dataclasses`, `enum`, `random`, `json`, `termios`).

## How to Run

### Interactive Mode
```bash
python3 garden.py
```

### Demo Mode (non-interactive preview)
```bash
python3 garden.py --demo
```

### View Saved Game Statistics
```bash
python3 garden.py --stats
```

### Show Version
```bash
python3 garden.py --version
```

## Controls

| Key | Action |
|-----|--------|
| ↑ ↓ ← → | Move cursor |
| P | Plant a seed at cursor position |
| W | Water plant at cursor |
| F | Apply fertilizer at cursor |
| H | Harvest mature plant / Compost dead plant |
| X | Remove plant (no gold reward) |
| S | Open seed & fertilizer shop |
| T | View weather forecast |
| N | Advance one day |
| M | Advance one week (7 days) |
| V | Save game |
| ? | Show help |
| Q | Quit game |

## Gameplay

1. **Plant seeds** — Move cursor to an empty plot and press P to select a seed to plant
2. **Water regularly** — Press W to water the plant under the cursor. Rainy weather also waters plants automatically
3. **Fertilize for growth** — Press F to apply fertilizer (1.5× growth boost for 3 days). Buy more at the shop
4. **Watch seasons change** — Every 28 days the season shifts, affecting growth rates. Spring is great for Tulips, Summer for Sunflowers, Autumn for Mushrooms
5. **Harvest for gold** — When a plant reaches Flowering or Fruiting stage, press H to harvest it. Fruiting gives 1.5× value! Fertilized plants give +20% bonus gold
6. **Compost dead plants** — Press H on a dead plant to compost it for 3g
7. **Buy new seeds & fertilizer** — Press S to open the shop and expand your garden variety
8. **Check the forecast** — Press T to see the next 3 days of weather and plan accordingly
9. **Beware storms & pests** — Stormy weather and random pest attacks can damage plants

## Season Effects

| Season | Best Plants | Weather Trend |
|--------|------------|---------------|
| Spring | Tulip, Rose, Fern, Mushroom | Frequent rain |
| Summer | Sunflower, Cactus, Vine | Hot spells |
| Autumn | Mushroom, Rose | Rain and clouds |
| Winter | (All plants struggle) | Frequent clouds, storms |

## Plant Stats

| Plant | Growth Rate | Water Need | Max Height | Harvest Value | Shop Price |
|-------|-------------|------------|------------|---------------|------------|
| Sunflower | 1.2× | 3 | 6 | 25g | 10g |
| Rose | 0.9× | 4 | 4 | 35g | 15g |
| Cactus | 0.5× | 1 | 5 | 30g | 20g |
| Mushroom | 1.5× | 5 | 3 | 20g | 12g |
| Fern | 1.0× | 3 | 5 | 15g | 10g |
| Oak Tree | 0.4× | 2 | 8 | 50g | 25g |
| Tulip | 1.1× | 3 | 3 | 25g | 12g |
| Vine | 1.3× | 3 | 7 | 30g | 15g |

Fertilizer costs 8g per unit.

## What It Does

The Terminal Garden Simulator creates a 40×16 ASCII garden grid. You navigate with arrow keys and interact with plants through a keyboard interface. Plants grow procedurally based on their type, season, weather, water levels, and fertilizer. Each plant type has unique ASCII art that changes through growth stages. The game features a full economic loop: plant → grow → harvest → buy new seeds/fertilizer → repeat. Seasons cycle every 28 days, random weather events and pest attacks add strategic depth — do you risk planting before a storm, or wait for clear skies? The forecast (T key) helps you plan ahead.

## Running Tests

```bash
python3 -m pytest test_garden.py -v
```

The test suite covers growth stages, planting, watering, harvesting, composting, fertilizing, season cycling, weather generation, plant growth, overwatering, drought, rendering, save/load, shop mechanics, and version validation.