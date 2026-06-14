# 🥚 CLI Tamagotchi

A fully-featured virtual pet that lives in your terminal! Choose from 5 species (cat, dog, dragon, slime, robot), each with unique ASCII art, personality traits, and response text. Your pet's needs decay in real-time between sessions, so remember to come back and care for them!

## Features

- **5 unique species** — Cat, Dog, Dragon, Slime, and Robot, each with distinct ASCII art across 6 life stages (egg → baby → child → adult → elder → dead)
- **5 decaying stats** — Hunger, Happiness, Health, Energy, and Cleanliness all decay over real-world time
- **6 care actions** — `feed`, `play`, `heal`, `sleep`, `clean`, and `pet`
- **Life stages** — Pets grow through egg → baby → child → adult → elder based on age
- **Personality system** — Each species has personality traits that flavor their responses
- **Species-specific dialogue** — Every species has unique response text for all actions
- **Persistent saves** — Pet state is saved to `~/.tamagotchi/pet.json` and loads automatically
- **Real-time decay** — Stats decay based on real elapsed time between sessions (capped at 24h)
- **Health consequences** — Low hunger/happiness/cleanliness accelerates health decay; health at 0 means death
- **Colored stat bars** — Visual progress bars with color-coded warnings
- **Mood system** — Pet mood changes based on overall stat levels (ecstatic → happy → content → neutral → sad → sick → dying → dead)
- **Random ignore events** — Neglecting your pet triggers sad reactions
- **121 passing tests** — Comprehensive test coverage for all game mechanics

## How to Install

No external dependencies needed — just Python 3.7+:

```bash
# Clone or download the project
cd ~/daily-ideas/2026-06-14-cli-tamagotchi

# Run directly
python3 tamagotchi.py
```

## How to Run

```bash
python3 tamagotchi.py
```

On first launch, you'll be prompted to name your pet and choose a species. After that, your pet loads automatically on each run.

## Usage Examples

### Starting a new pet

```
🥚 Welcome to CLI Tamagotchi! 🥚

Choose a name for your pet:
  Name: Nibbles

Choose a species:
  1. Cat
  2. Dog
  3. Dragon
  4. Slime
  5. Robot
  Species (1-5): 1
```

### Main game screen

```
══════════════════════════════════════════════════
  🥚 CLI Tamagotchi — Nibbles the cat 😊
══════════════════════════════════════════════════

      /\\_/\\    
     ( °ω° )   
      > ω <    
     /|   |\\   
    (_|   |_)   
      "" ""    

  Stats:
  🍖 Hunger        ██████████████████░░  80.0/100
  💖 Happiness     ██████████████████░░  80.0/100
  ❤️ Health        ████████████████████ 100.0/100
  ⚡ Energy        ██████████████████░░  80.0/100
  ✨ Cleanliness   ██████████████████░░  80.0/100

  🕐 Age: 0.2h  |  📊 Stage: Baby  |  🎭 Playful
  🔢 Interactions: 0

══════════════════════════════════════════════════

  Commands: feed | play | heal | sleep | clean | pet | status | help | quit

  Nibbles > feed
```

### Care actions

| Command | Effect | Side Effects |
|---------|--------|-------------|
| `feed`  | 🍖 +25 hunger | ⚡ +5 energy, ✨ -3 cleanliness |
| `play`  | 💖 +20 happiness | ⚡ -15 energy, 🍖 -10 hunger, ✨ -5 |
| `heal`  | ❤️ +30 health | 💖 -5 happiness (yucky medicine) |
| `sleep` | ⚡ +35 energy | 🍖 -8 hunger |
| `clean` | ✨ +30 cleanliness | 💖 +5 happiness |
| `pet`   | 💖 +10 happiness | — |

### Other commands

- `status` — Show detailed pet info (species, personality, age, mood)
- `help` — Display command reference
- `release` — Release current pet and create a new one
- `quit` — Save and exit

### If your pet passes away

```
  💀 Nibbles has passed away... 💀
  Use 'release' to let go and start fresh.
```

### Returning after absence

Stats decay over real time. If you leave for hours, your pet will be hungry, tired, and dirty. If you leave for too long (24+ hours of neglect), they may pass away. The game caps decay at 24 hours to prevent instant death on return.

## Running Tests

```bash
python3 run_tests.py
```

This runs 121 tests covering all game mechanics without requiring pytest.

## How It Works

- **Decay**: Each minute of real time, all stats decrease by a small amount. Health decays faster when other stats are critically low.
- **Life stages**: Pets progress through egg (0-3min) → baby (3-30min) → child (30min-2h) → adult (2-10h) → elder (10h+)
- **Mood**: Calculated from the average of all stats, with special handling for low health (sick) and death (dead)
- **Random events**: 10% chance per interaction that your pet reacts to being ignored
- **Save format**: JSON file at `~/.tamagotchi/pet.json` with all pet state