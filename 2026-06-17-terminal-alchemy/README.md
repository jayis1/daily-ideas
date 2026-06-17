# 🧪 Terminal Alchemy

A Little Alchemy-inspired element-combining game that runs entirely in your terminal. Start with four base elements — **water**, **fire**, **earth**, and **air** — and combine them to discover **271 unique elements** spanning nature, technology, civilization, mythology, and the cosmos.

## Features

- **271 discoverable elements** organized in deep dependency chains
- **423+ recipes** for combining elements
- **Interactive mode** with a colorful prompt, progress tracking, and hint system
- **Non-interactive / batch mode** for scripting and automation
- **Persistent progress** — your discoveries are saved between sessions
- **Progress bar** and statistics to track how far you've come
- **Search** through your discovered elements
- **Hint system** when you're stuck
- **Reset option** to start fresh

## Installation

No external dependencies — just Python 3.6+:

```bash
# Clone or download, then:
chmod +x alchemy.py
```

Or run directly:

```bash
python3 alchemy.py
```

## How to Play

### Interactive Mode (default)

```bash
python3 alchemy.py
```

You'll see the game banner and a prompt. Type combinations like:

```
⚗️ > water + fire
⚗️ > water fire
⚗️ > combine water fire
```

All three formats work. The game checks if both elements are in your discovered list and whether they produce a new element.

### Commands

| Command | Description |
|---------|-------------|
| `a + b` or `a b` | Combine two elements |
| `list` | Show all discovered elements |
| `hint` | Get a hint about possible combinations |
| `new` | Show elements discovered this session |
| `search <term>` | Search discovered elements |
| `stats` | Show progress bar and statistics |
| `reset` | Reset all progress (with confirmation) |
| `help` | Show all commands |
| `quit` / `exit` | Save and exit |

### Non-Interactive Mode

Combine elements from the command line:

```bash
python3 alchemy.py --combine water fire --combine steam air --combine cloud cloud
```

### Other CLI Options

```bash
python3 alchemy.py --list          # List discovered elements
python3 alchemy.py --stats         # Show progress statistics
python3 alchemy.py --hint          # Get a hint
python3 alchemy.py --all-elements  # List all possible elements (spoilers!)
python3 alchemy.py --reset         # Reset progress
python3 alchemy.py --version       # Show version
```

## Example Session

```
🧪 > water + fire
✨✨✨ NEW DISCOVERY! ✨✨✨
steam + fire = heat

🧪 > fire + fire
✨✨✨ NEW DISCOVERY! ✨✨✨
fire + fire = heat

🧪 > steam + air
✨✨✨ NEW DISCOVERY! ✨✨✨
steam + air = cloud

🧪 > cloud + cloud
✨✨✨ NEW DISCOVERY! ✨✨✨
cloud + cloud = storm

🧪 > storm + water
✨✨✨ NEW DISCOVERY! ✨✨✨
storm + water = hurricane
Progress: 10/271 (3.7%)
```

## Progression Tree (Spoilers!)

<details>
<summary>Click to reveal early-game combinations</summary>

### Tier 1 — Base + Base
| Combination | Result |
|---|---|
| water + fire | steam |
| water + earth | mud |
| water + air | mist |
| fire + earth | lava |
| fire + air | smoke |
| earth + air | dust |

### Tier 2 — Deeper Combinations
| Combination | Result |
|---|---|
| fire + fire | heat |
| steam + air | cloud |
| smoke + mist | darkness |
| cloud + cloud | storm |
| cloud + fire | lightning |
| lightning + water | life |
| air + energy | cold |
| air + darkness | night |
| energy + fire | light |

### Tier 3 — Life & Nature
| Combination | Result |
|---|---|
| life + earth | animal |
| life + air | bird |
| life + fire | phoenix |
| life + water | fish |
| rain + earth | plant |
| flower + heat | sugar |
| cloud + night | moon |
| light + light | star |

</details>

## Element Categories

The 271 elements span many categories:

- **Nature**: water, fire, earth, air, rain, snow, ice, mountain, river, ocean, desert, volcano
- **Life**: animal, bird, fish, plant, tree, flower, bacteria, human
- **Materials**: metal, glass, stone, clay, wood, paper, diamond, gold, carbon
- **Technology**: wheel, engine, computer, internet, robot, phone
- **Food**: bread, steak, sandwich, honey, mead, tea, soda, candy
- **Mythology**: dragon, phoenix, wizard, paladin, legend, overlord
- **Cosmos**: star, constellation, galaxy, universe, eclipse, meteor
- **Emotions**: love, fear, courage, harmony, wisdom
- **Civilization**: village, city, civilization, empire, kingdom

## Data Storage

Progress is saved to `~/.config/terminal-alchemy/save.json`. You can back up or share this file.

## License

MIT License — combine freely!