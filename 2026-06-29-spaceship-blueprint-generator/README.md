# 🚀 Procedural Spaceship Blueprint Generator

A command-line tool that generates unique, detailed ASCII spaceship blueprints every time you run it. Each ship has a randomized class, name, crew manifest, room layout, weapons systems, and more — producing a full registration dossier complete with top-down blueprints, side-view schematics, power distribution diagrams, and system status dashboards.

## Features

- **8 Ship Classes**: Corvette, Frigate, Destroyer, Cruiser, Battleship, Carrier, Dreadnought, and Station — each with appropriate scale, crew size, weapons, and room layouts
- **Top-Down Blueprint**: ASCII art hull outline with procedurally placed rooms using Unicode symbols
- **Side-View Schematic**: Cross-section profile showing the ship's silhouette with engine glow indicators
- **Registration Dossier**: Complete specs including length, beam, displacement, speed, shields, drive type, and weapons loadout
- **Crew Manifest**: Named officers with ranks, species (including alien races), and roles
- **Power Distribution Diagram**: Visual bar chart showing system power allocation
- **System Status Dashboard**: Real-time-style readouts for reactor, hull, shields, navigation, comms, life support, and weapons
- **Seeded Generation**: Use `--seed` for reproducible ships
- **Batch Mode**: Generate multiple ships with `--number`
- **Stats-Only Mode**: Skip blueprints and just show the dossier with `--stats-only`

## Ship Classes

| Class | Length | Crew | Flavor |
|-------|--------|------|--------|
| Corvette | 12–20m | 3–8 | Light scout, patrol |
| Frigate | 20–30m | 8–20 | Escort, patrol |
| Destroyer | 30–45m | 20–50 | Combat escort |
| Cruiser | 45–60m | 50–120 | Multi-role warship |
| Battleship | 55–75m | 120–300 | Heavy combat |
| Carrier | 60–80m | 100–500 | Fighter transport |
| Dreadnought | 75–100m | 300–800 | Fleet flagship |
| Station | 40–60m | 500–5000 | Orbital facility |

## Installation

No external dependencies needed — just Python 3.7+:

```bash
# Clone or download the script
chmod +x spaceship_blueprint.py
```

## Usage

```bash
# Generate a random ship
python3 spaceship_blueprint.py

# Generate a specific class
python3 spaceship_blueprint.py --class cruiser

# Generate with a seed for reproducible results
python3 spaceship_blueprint.py --seed 42

# Generate 3 random ships
python3 spaceship_blueprint.py --number 3

# Stats only (no diagrams)
python3 spaceship_blueprint.py --stats-only

# Combine options
python3 spaceship_blueprint.py --class dreadnought --seed 77
```

### Available Classes

`corvette`, `frigate`, `destroyer`, `cruiser`, `battleship`, `carrier`, `dreadnought`, `station`

## Example Output

```
╔════════════════════════════════════════════════════════════╗
║                        ISS Guardian                        ║
║                          ICS-4657                          ║
╚════════════════════════════════════════════════════════════╝

  ┌─── TOP-DOWN BLUEPRINT ───────────────────────────────────┐
  │                                │                          │
  │     ▓                          │                          │
  │   ▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   │                      │
  │   ▒▒▒▒☢▒▒▒░░░░░░░░░░░░░░░░░░▓▓ │                      │
  │  ▓░░░░░░░░░░░░▒▒▒▒▒▒▒▒░░░░░░░▓ │                      │
  │ ▓░░▒▒▒▒░░▒▒▒░░▒▒▒▒⚙▒▒▒░░░░░░░▓ │                      │
  │  ▓░▒▒⬡▒░░▒♣▒░░░░░░░░░░░░░░░░░▓ │                      │
  │   ▓░░░░░░░░░░░░░░░░░░░░░░░░▓▓ │                        │
  └───────────────────────────────────────────────────────────┘

  ROOM LEGEND:
    ⬡  Bridge               (4×2)
    ⚙  Engineering          (8×2)
    ☢  Reactor Core         (8×2)
    ♣  Life Support         (3×2)

  ╔════════════════════════════════════════════════════════════╗
  ║              STARSHIP REGISTRATION DOSSIER                ║
  ╠════════════════════════════════════════════════════════════╣
  ║  Name:       ISS Guardian                                ║
  ║  Registry:   ICS-4657                                    ║
  ║  Class:      Frigate                                     ║
  ║  Faction:    Outer Rim Coalition                         ║
  ...
```

## How It Works

1. **Ship Class Selection**: Each class defines size ranges, crew capacity, and tier level
2. **Hull Generation**: A parametric hull shape is generated based on the class — pointed nose for speed, wide beam for capital ships
3. **Room Placement**: Essential rooms (bridge, engineering, reactor, etc.) are placed with priority, then optional rooms are added based on ship tier. Room placement uses collision avoidance and positional preferences (e.g., bridge near the nose, reactor near the stern)
4. **Crew Manifest**: Officers are generated with names drawn from a multi-cultural pool, alien species, and rank-appropriate titles
5. **Systems**: Weapons, shields, and drives are selected from class-appropriate pools
6. **Rendering**: The blueprint, side view, dossier, power diagram, and status dashboard are all rendered as formatted ASCII art

## License

MIT