# 🥚 CLI Tamagotchi v2.0

A fully-featured virtual pet that lives in your terminal! Choose from 5 species (cat, dog, dragon, slime, robot), each with unique ASCII art, personality traits, and response text. Your pet's needs decay in real-time between sessions, so remember to come back and care for them!

## Features

### Core Gameplay
- **5 unique species** — Cat, Dog, Dragon, Slime, and Robot, each with distinct ASCII art across 6 life stages (egg → baby → child → adult → elder → dead)
- **5 decaying stats** — Hunger, Happiness, Health, Energy, and Cleanliness all decay over real-world time
- **6 care actions** — `feed`, `play`, `heal`, `sleep`, `clean`, and `pet`
- **Life stages** — Pets grow through egg → baby → child → adult → elder based on age
- **Personality system** — Each species has personality traits that flavor their responses
- **Species-specific dialogue** — Every species has unique response text for all actions
- **Health consequences** — Low hunger/happiness/cleanliness accelerates health decay; health at 0 means death
- **Mood system** — Pet mood changes based on overall stat levels (ecstatic → happy → content → neutral → sad → sick → dying → dead)
- **Random ignore events** — 10% chance per interaction that your pet reacts to being neglected

### New in v2.0
- 🎓 **Teach tricks** — Teach species-specific tricks to your pet (5 unique tricks per species). Costs energy, boosts happiness.
- 🔍 **Explore adventures** — Send your pet on random adventures. Each species has unique events that can boost or reduce stats. Costs energy.
- 🏅 **18 achievements** — Earn milestones for care, interactions, tricks, exploration, and life stages. Track progress with `achievements` command.
- 📔 **Event diary** — Every action is timestamped in your pet's diary. Review the last 15 entries with `diary` command.
- 💾 **Automatic backup** — Save file is backed up to `pet.json.bak` on every save. If the primary save is corrupted, the game falls back to the backup automatically.
- 🔄 **Save migration** — Old save files missing new fields are automatically populated with sensible defaults.
- 🏴 **CLI flags** — `--help` / `-h` and `--version` / `-v` flags for quick reference without launching the game.
- 🧪 **203 tests** — Comprehensive test coverage for all game mechanics including new features.

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
# Start or continue your pet
python3 tamagotchi.py

# Show CLI help
python3 tamagotchi.py --help

# Show version
python3 tamagotchi.py --version
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

      /\_/\
     ( °ω° )
      > ω <
     /|   |\
    (_|   |_)
      "" ""

  Stats:
  🍖 Hunger        ██████████████████░░  80.0/100
  💖 Happiness     ██████████████████░░  80.0/100
  ❤️ Health        ████████████████████ 100.0/100
  ⚡ Energy        ██████████████████░░  80.0/100
  ✨ Cleanliness   ██████████████████░░  80.0/100

  🕐 Age: 0.2h  |  📊 Stage: Baby  |  🎭 Playful  |  🎪 Tricks: 2  |  🏅 Achievements: 5
  🔢 Interactions: 12

══════════════════════════════════════════════════

  Commands: feed | play | heal | sleep | clean | pet | teach | explore | status | achievements | diary | help | quit

  Nibbles > teach
```

### Care actions

| Command  | Effect                     | Side Effects                              |
|----------|----------------------------|-------------------------------------------|
| `feed`   | 🍖 +25 hunger              | ⚡ +5 energy, ✨ -3 cleanliness            |
| `play`   | 💖 +20 happiness            | ⚡ -15 energy, 🍖 -10 hunger, ✨ -5        |
| `heal`   | ❤️ +30 health              | 💖 -5 happiness (yucky medicine)          |
| `sleep`  | ⚡ +35 energy              | 🍖 -8 hunger                              |
| `clean`  | ✨ +30 cleanliness          | 💖 +5 happiness                           |
| `pet`    | 💖 +10 happiness            | —                                         |
| `teach`  | 🎓 Learn a new trick        | ⚡ -10 energy, 💖 +8 happiness            |
| `explore`| 🔍 Random adventure         | ⚡ -8 energy, stat effects vary           |

### Information commands

- `status` — Show detailed pet info (species, personality, age, mood, tricks, achievements)
- `achievements` — Show all earned achievements and preview locked ones
- `diary` — Show your pet's timestamped event diary
- `help` — Display in-game command reference
- `release` — Release current pet and create a new one
- `quit` — Save and exit

### Teaching tricks

Each species has 5 unique tricks to learn:

| Species | Sample Tricks |
|---------|--------------|
| Cat     | High Five, Roll Over, Fetch, Purr on Command, Keyboard Walk |
| Dog     | Sit, Shake, Roll Over, Speak, Play Dead |
| Dragon  | Fire Breath, Hover, Treasure Guard, Smoke Rings, Wing Spread |
| Slime   | Shape Shift, Bounce High, Absorb Object, Split, Glow |
| Robot   | Calculate Pi, Dance Mode, Translate, Scan, Self Diagnose |

Teaching costs 10 energy. If your pet already knows all tricks, they'll perform a random one instead!

### Exploring adventures

Each species has 8 unique exploration events that can raise or lower stats:

- **Cat**: "found a warm sunbeam" (💖 +8), "knocked a glass off the table" (✨ -8)
- **Dog**: "found a stick" (💖 +10), "rolled in something smelly" (✨ -15)
- **Dragon**: "discovered a hidden cave" (💖 +15), "accidentally set something on fire" (✨ -12)
- **Slime**: "absorbed a puddle" (🍖 +6), "left a slime trail" (✨ -8)
- **Robot**: "got a firmware update" (💖 +10), "overheated slightly" (❤️ -5)

Exploring costs 8 energy.

### Achievements

18 achievements to unlock through care, milestones, and persistence:

| Achievement | Icon | Requirement |
|------------|------|-------------|
| First Bite | 🍎 | Feed your pet for the first time |
| Playtime | 🎮 | Play with your pet for the first time |
| Nurse | 💊 | Heal your pet for the first time |
| Sweet Dreams | 💤 | Put your pet to sleep for the first time |
| Sparkling | 🧼 | Clean your pet for the first time |
| Teacher | 🎓 | Teach your pet a trick for the first time |
| Adventurer | 🧭 | Let your pet explore for the first time |
| Devoted | ❤️ | Reach 10 lifetime interactions |
| Super Devoted | 💜 | Reach 50 lifetime interactions |
| Best Friend | 🏆 | Reach 100 lifetime interactions |
| Soulmate | ✨ | Reach 500 lifetime interactions |
| Perfect Care | 👑 | All stats above 80 at once |
| Survivor | 🛡️ | Recover from being sick |
| Trickster | 🎪 | Teach 3 different tricks |
| Grand Performer | 🎭 | Teach all 5 tricks |
| Wanderer | 🗺️ | Explore 5 times |
| Explorer | 🌍 | Explore 20 times |
| All Grown Up | 🌟 | Reach the adult stage |
| Wisdom | 📖 | Reach the elder stage |

### If your pet passes away

```
  💀 Nibbles has passed away... 💀
  Use 'release' to let go and start fresh.
```

### Returning after absence

Stats decay over real time. If you leave for hours, your pet will be hungry, tired, and dirty. If you leave for too long (24+ hours of neglect), they may pass away. The game caps decay at 24 hours to prevent instant death on return.

## Save Files

- **Primary**: `~/.tamagotchi/pet.json`
- **Backup**: `~/.tamagotchi/pet.json.bak` (created automatically on each save)
- If the primary save is corrupted, the game falls back to the backup
- Old saves missing new fields are automatically migrated with sensible defaults

## Running Tests

```bash
# Run all 203 tests (no pytest needed)
python3 run_tests.py

# Or with pytest (if installed)
python3 -m pytest test_tamagotchi.py -v
```

## How It Works

- **Decay**: Each minute of real time, all stats decrease by a small amount. Health decays faster when other stats are critically low.
- **Life stages**: Pets progress through egg (0–3 min) → baby (3–30 min) → child (30 min–2h) → adult (2–10h) → elder (10h+)
- **Mood**: Calculated from the average of all stats, with special handling for low health (sick) and death (dead)
- **Random events**: 10% chance per interaction that your pet reacts to being ignored
- **Achievements**: Checked after every action; new achievements are announced immediately
- **Event diary**: All actions and events are logged with timestamps, capped at 100 entries
- **Save format**: JSON file with all pet state including tricks, achievements, and diary