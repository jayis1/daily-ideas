# 🥚 CLI Tamagotchi v2.1

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

### Learning & Adventure
- 🎓 **Teach tricks** — Teach species-specific tricks to your pet (5 unique tricks per species). Costs energy, boosts happiness.
- 🔍 **Explore adventures** — Send your pet on random adventures. Each species has unique events that can boost or reduce stats. Costs energy. Health can't drop below 1 from exploring (safety net).

### Achievements & Diary
- 🏅 **19 achievements** — Earn milestones for care (including petting!), interactions, tricks, exploration, and life stages. Track progress with `achievements` command.
- 📔 **Event diary** — Every action is timestamped in your pet's diary. Review the last 15 entries with `diary` command.

### Persistence & Safety
- 💾 **Automatic backup** — Save file is backed up to `pet.json.bak` on every save. If the primary save is corrupted, the game falls back to the backup automatically.
- 🔄 **Save migration** — Old save files missing new fields are automatically populated with sensible defaults.
- 🔄 **Forward compatibility** — Save files with unknown fields from future versions are loaded safely (extra fields are ignored).

### CLI
- 🏴 **CLI flags** — `--help` / `-h` and `--version` / `-v` / `-V` flags for quick reference without launching the game.

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

> **Note**: `play` requires at least 15 energy. `teach` requires at least 10 energy. `explore` requires at least 8 energy. If your pet is too tired, these actions will be rejected with a helpful message.

### Information commands

- `status` — Show detailed pet info (species, personality, age, mood, tricks, achievements). Works even for deceased pets.
- `achievements` — Show all earned achievements and preview locked ones
- `diary` — Show your pet's timestamped event diary
- `help` — Display in-game command reference
- `release` — Release current pet and create a new one
- `quit` — Save and exit

### Teaching tricks

Each species has 5 unique tricks to learn:

| Species | Sample Tricks |
|---------|---------------|
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

Exploring costs 8 energy. Health-reducing events cannot drop health below 1 (safety net).

### Achievements

19 achievements to unlock through care, milestones, and persistence:

| Achievement    | Icon | Requirement                              |
|---------------|------|------------------------------------------|
| First Bite    | 🍎  | Feed your pet for the first time          |
| Playtime      | 🎮  | Play with your pet for the first time     |
| Nurse         | 💊  | Heal your pet for the first time          |
| Sweet Dreams  | 💤  | Put your pet to sleep for the first time  |
| Sparkling     | 🧼  | Clean your pet for the first time         |
| Best Pal      | 🤗  | Pet your pet for the first time           |
| Teacher       | 🎓  | Teach your pet a trick for the first time |
| Adventurer   | 🧭  | Let your pet explore for the first time   |
| Devoted       | ❤️  | Reach 10 lifetime interactions            |
| Super Devoted| 💜  | Reach 50 lifetime interactions            |
| Best Friend  | 🏆  | Reach 100 lifetime interactions           |
| Soulmate     | ✨  | Reach 500 lifetime interactions           |
| Perfect Care | 👑  | All stats above 80 at once                |
| Survivor     | 🛡️ | Recover from being sick                    |
| Trickster    | 🎪  | Teach 3 different tricks                  |
| Grand Performer | 🎭 | Teach all 5 tricks                     |
| Wanderer     | 🗺️ | Explore 5 times                           |
| Explorer     | 🌍  | Explore 20 times                          |
| All Grown Up | 🌟  | Reach the adult stage                     |
| Wisdom       | 📖  | Reach the elder stage                     |

### Mood system

Your pet's mood depends on their stats:

| Mood      | Condition                                    |
|-----------|----------------------------------------------|
| Ecstatic  | Average of all stats ≥ 90                    |
| Happy     | Average ≥ 75                                |
| Content   | Average ≥ 60                                |
| Neutral   | Average ≥ 40                                |
| Sad       | Average ≥ 20                                |
| Sick      | Health < 20 (but ≥ 10)                      |
| Dying     | Health < 10                                  |
| Dead      | Pet has passed away (health reached 0)       |

### If your pet passes away

```
  💀 Nibbles has passed away... 💀
  Use 'release' to let go and start fresh.
```

Dead pets can still use `status`, `achievements`, `diary`, and `release` commands.

### Returning after absence

Stats decay over real time. If you leave for hours, your pet will be hungry, tired, and dirty. If you leave for too long (24+ hours of neglect), they may pass away. The game caps decay at 24 hours to prevent instant death on return.

## Save Files

- **Primary**: `~/.tamagotchi/pet.json`
- **Backup**: `~/.tamagotchi/pet.json.bak` (created automatically on each save)
- If the primary save is corrupted, the game falls back to the backup
- Old saves missing new fields are automatically migrated with sensible defaults
- Save files with unknown fields from future versions are loaded safely (extra fields are ignored)

## Running Tests

```bash
# Run all 203 tests (no pytest needed)
python3 run_tests.py

# Or with pytest (if installed)
python3 -m pytest test_tamagotchi.py -v
```

## Changelog

### v2.1 — Bug Fixes
- **Fixed 'dying' mood unreachable** — The `dying` mood (😰) was unreachable because health was checked against `SICK_THRESHOLD` before `DEAD_THRESHOLD` (0). Added `DYING_THRESHOLD = 10` so health below 10 shows "dying" and below 20 shows "sick".
- **Fixed egg → baby transition** — Level-up messages were suppressed for egg-to-baby transitions due to `old_stage != "egg"` check. Your pet's very first growth milestone now properly announces!
- **Fixed `do_play()` missing energy check** — Unlike `teach` and `explore`, `play` had no internal energy check. Calling `do_play()` with energy below 15 now returns a "too tired" message instead of executing and driving energy negative.
- **Fixed dead pet `status` command** — The `status` command was missing from the dead-pet command allowlist, causing dead pets to show "can't do that" instead of their status. Now dead pets can check `status`, `achievements`, `diary`, and `release`.
- **Fixed missing `pet` achievement** — The `pet` command didn't award any achievement, unlike every other care action. Added `first_pet_stroke` ("Best Pal" 🤗) achievement.
- **Fixed save file forward compatibility** — Loading a save file with unknown fields (from a future version) caused a `TypeError` crash. `load_pet()` now filters out unknown fields so saves are forward-compatible.
- **Fixed explore health safety** — Robot's "overheated slightly" event reduced health by 5, which could drop health to 0 (potentially killing the pet from an adventure). Health-reducing explore events now floor at 1, preventing unfair death.
- **Fixed unknown command decay** — Typos and unrecognized commands triggered stat decay (`apply_decay(0.5)`), punishing players for mistakes. Unknown and invalid commands now skip the decay phase.
- **Fixed test `test_play_action`** — The test created a pet with default `hunger=80` but asserted `hunger < 50` after `do_play`. Fixed by explicitly setting `hunger=50`.
- **Updated test `test_play_too_tired`** — Now properly tests that `do_play()` rejects low-energy play internally, verifying stats don't change.
- **Added 11 new bug-fix tests** — Covering dying mood, egg transition, energy check, dead pet commands, pet achievement, forward compatibility, explore health safety, and more.

## How It Works

- **Decay**: Each minute of real time, all stats decrease by a small amount. Health decays faster when other stats are critically low.
- **Life stages**: Pets progress through egg (0–3 min) → baby (3–30 min) → child (30 min–2h) → adult (2–10h) → elder (10h+)
- **Mood**: Calculated from the average of all stats, with special handling for low health (dying < 10, sick < 20) and death
- **Random events**: 10% chance per interaction that your pet reacts to being ignored
- **Achievements**: Checked after every action; new achievements are announced immediately
- **Event diary**: All actions and events are logged with timestamps, capped at 100 entries
- **Save format**: JSON file with all pet state including tricks, achievements, and diary