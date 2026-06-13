# 🪐 Procedural Planet Generator

Generate infinite fictional worlds with detailed properties, lore, and ASCII art globe renderings. Each planet is procedurally generated from a seed — use the same seed and get the same world every time.

## Features

- **12 planet types**: Lava World, Desert World, Ice World, Ocean World, Terran World, Gas Giant, Ice Giant, Toxic World, Crystalline World, Storm World, Megastructure, Rogue Planet
- **Stellar classification**: Generates parent stars (O/B/A/F/G/K/M class) with realistic temperature and mass
- **Detailed properties**: Gravity, atmosphere, surface water, magnetic field, moons, ring systems, axial tilt, temperature, day/year length
- **Life detection**: Procedural life level appropriate to planet type — from "None" to "Post-Singularity"
- **Notable features**: Each planet gets 1–3 unique features like "Cryovolcanoes", "Great Storm Vortex", "Dyson Fragments"
- **ASCII globe rendering**: Colored (ANSI) or plain-text globe visualization with per-planet-type character sets, ring systems, and terrain patterns
- **Seeded generation**: Same seed = same planet, every time. Share seeds with friends!
- **Batch generation**: Generate multiple planets at once
- **Export**: Save planet catalogs to text files
- **Procedural names**: Evocative names like "Gilded Vexion-879", "Ashul-468", "Dreaming Phoros-112"

## Installation

No external dependencies — uses only the Python standard library.

```bash
# Just clone and run
git clone <repo-url>
cd procedural-planet-generator
python3 planet_gen.py
```

## Usage

```bash
# Generate a random planet
python3 planet_gen.py

# Generate with a specific seed (reproducible)
python3 planet_gen.py --seed 42
python3 planet_gen.py --seed "my-world"

# Generate multiple planets
python3 planet_gen.py --count 5

# Generate multiple planets from a seed (each gets a derived seed)
python3 planet_gen.py --seed "exploration" --count 3

# Disable the ASCII globe
python3 planet_gen.py --no-globe

# Disable ANSI colors (for piping or light terminals)
python3 planet_gen.py --no-color

# Save to a file
python3 planet_gen.py --seed "catalog-1" --save planets.txt

# Custom globe size (wider globe)
python3 planet_gen.py --size 60
```

## Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🪐 Ashul-468
  Seed: 42
──────────────────────────────────────────
  Type:            Gas Giant
  Star:            M-class (Red, 2,721 K, 0.23 M☉)
  Distance:        0.94 AU
  Radius:          31,533 km
  Gravity:         2.31g
  Day Length:      192.4 hours
  Year Length:     694.1 days
  Axial Tilt:      88.4°
  Mean Temp:       200°C
  Atmosphere:      Hydrogen/Helium/Methane
  Surface Water:   0.0%
  Magnetic Field:  Moderate
  Moons:           71
  Ring System:     Yes
  Life Level:      None
  Features:        Ring System
──────────────────────────────────────────
  Globe View:

                      ~
              -~~~~~~~--------~
           ---~~≈≈≈~~--------~~≈~~
        -=---~~≈≡≈≈≈~~~-~---~-~~≈≈~--
       ------~≈≡≡≡≡≈≈≈~~--~-~~~≈≈~~~~-
     -------~~≈≡≈≡≡≡≈≈~~~--~~~≈≈≈≈≈~----
     ~------~≈≡≈≡≡≈≈≈~------~~~~~~~~----
    -------~~~~≈≈≈≈≈~~--------~----------
  ≈≈--------~-~~~~~----------------------~
  -------------~-~--~---------------------
  -------~~~~-~--~~~--~-~--------------~~~
    -~~≈≈≡~≡≈≈~~--~-~-~~≈~-~----------≈≈≈
     ≈≈≈≡≡≡≡≈≈≈~--~~~~~≈≈~≈~~-------~≈≈≡
     ~≈≡≡≡≡≡≈≈~------~~≈≈≈≈~~-------~≈≡≡
       ≡≡≡≡≡≈≈~-------≈≈≈~~~--------~≈
        ≡≈≈≈≈~---------~~~-~--------~
           ~-----=--------------=-

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## How It Works

1. **Seeding**: A SHA-256 hash of the seed string initializes a deterministic `random.Random` instance, ensuring reproducibility.
2. **Star generation**: A star type (O through M) is chosen using realistic frequency weights, then temperature and mass are randomly sampled within that class's ranges.
3. **Planet type**: Selected via weighted random choice from 12 types.
4. **Property derivation**: Each property (distance, radius, gravity, temperature, atmosphere, life, features) is generated contextually based on the planet type — gas giants get many moons, lava worlds get extreme temperatures, megastructures get engineered climates.
5. **Globe rendering**: A 2D projection maps (x, y) coordinates onto a sphere. Values are modulated by sinusoidal "terrain" functions seeded by the planet's properties. Each planet type has its own character/color palette. Gas giants show horizontal banding. Rings are rendered as horizontal lines beyond the sphere's edge.
6. **Naming**: A random prefix + suffix creates names like "Vexion", "Zoroth", "Klaara". A 30% chance adds an evocative descriptor prefix ("Gilded", "Ancient", "Dreaming").

## Extending

- Add new planet types by adding to `PLANET_TYPES`, `ATMOSPHERES`, `LIFE_LEVELS`, `FEATURES`, and `GLOBE_CHARS`
- Add new star types in `STAR_TYPES`
- Add naming flavors in `NAME_PREFIXES`, `NAME_SUFFIXES`, `DESCRIPTORS`

## License

MIT