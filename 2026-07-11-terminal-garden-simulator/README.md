# 🌻 Terminal Garden Simulator

A procedural ASCII garden simulator where you plant, grow, water, and harvest procedural plants through changing seasons and weather. Manage your garden across Spring, Summer, Autumn, and Winter — each with unique weather patterns and growth modifiers.

## Features

- **8 Plant Types**: Sunflower, Rose, Cactus, Mushroom, Fern, Oak Tree, Tulip, and Vine — each with unique growth rates, water needs, and season preferences
- **7 Growth Stages**: Seed → Sprout → Growing → Mature → Flowering → Fruiting → Withering → Dead
- **4 Seasons**: Spring (rainy), Summer (hot), Autumn (mushroom-friendly), Winter (harsh) — each lasting 28 days
- **Dynamic Weather**: Clear, Cloudy, Rainy, Stormy, Hot, and Windy conditions affect plant growth and water levels
- **Procedural ASCII Art**: Each plant renders differently based on type, stage, and growth — with slight randomization each day
- **Economy System**: Earn gold by harvesting mature plants, spend it at the seed shop
- **Overwatering & Storm Damage**: Plants can suffer from too much water or stormy weather
- **Seed Shop**: Buy new seed types with earned gold
- **Save/Load**: Game state persists between sessions

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

## Controls

| Key | Action |
|-----|--------|
| Arrow Keys / WASD | Move cursor |
| P | Plant a seed at cursor position |
| SPACE | Water plant at cursor |
| H | Harvest mature plant |
| X | Remove plant |
| S | Open seed shop |
| N | Advance one day |
| M | Advance one week (7 days) |
| ? | Show help |
| Q | Quit game |

## Gameplay

1. **Plant seeds** — Move cursor to an empty plot and press P to select a seed to plant
2. **Water regularly** — Press SPACE to water the plant under the cursor. Rainy weather also waters plants automatically
3. **Watch seasons change** — Every 28 days the season shifts, affecting growth rates. Spring is great for Tulips, Summer for Sunflowers, Autumn for Mushrooms
4. **Harvest for gold** — When a plant reaches Flowering or Fruiting stage, press H to harvest it. Fruiting gives 1.5x value!
5. **Buy new seeds** — Press S to open the shop and expand your garden variety
6. **Beware storms** — Stormy weather can damage plants. Hot days increase water loss

## Season Effects

| Season | Best Plants | Weather Trend |
|--------|------------|---------------|
| Spring | Tulip, Rose, Fern, Mushroom | Frequent rain |
| Summer | Sunflower, Cactus, Vine | Hot spells |
| Autumn | Mushroom, Rose | Moderate rain |
| Winter | (All plants struggle) | Frequent clouds |

## Plant Stats

| Plant | Growth Rate | Water Need | Max Height | Harvest Value |
|-------|-------------|------------|------------|---------------|
| Sunflower | 1.2x | 3 | 6 | 25g |
| Rose | 0.9x | 4 | 4 | 35g |
| Cactus | 0.5x | 1 | 5 | 30g |
| Mushroom | 1.5x | 5 | 3 | 20g |
| Fern | 1.0x | 3 | 5 | 15g |
| Oak Tree | 0.4x | 2 | 8 | 50g |
| Tulip | 1.1x | 3 | 3 | 25g |
| Vine | 1.3x | 3 | 7 | 30g |

## What It Does

The Terminal Garden Simulator creates a 40×16 ASCII garden grid. You navigate with arrow keys and interact with plants through a simple keyboard interface. Plants grow procedurally based on their type, season, weather, and water levels. Each plant type has unique ASCII art that changes through growth stages. The game features a full economic loop: plant → grow → harvest → buy new seeds → repeat. Seasons cycle every 28 days, and random weather events add strategic depth — do you risk planting before a storm, or wait for clear skies?