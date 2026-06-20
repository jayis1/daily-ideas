# 🏛️ Procedural Cathedral Generator

Generate unique ASCII art gothic cathedrals every time! Each run produces a different cathedral with randomized spires, rose windows, stained glass, flying buttresses, arched doors, gargoyles, and atmospheric details.

## Features

- **Procedural generation** — every cathedral is unique, controlled by a seed for reproducibility
- **Gothic architecture elements**:
  - Twin towers with tapered spires and crosses
  - Pointed gothic arches for doors and windows
  - Ornate rose windows with petal patterns and radial spokes
  - Stained glass windows with colorful Unicode characters
  - Flying buttresses with pinnacles
  - Gargoyles perched on the façade
  - Battlements/crenellations (sometimes)
  - Central spire (sometimes)
  - Double or single arched doors
  - Stone wall textures with course lines
  - Pitched roofs with ridge lines
- **Atmospheric scene**: twinkling stars and textured ground
- **Configurable**: set seed, canvas size, and generate multiple cathedrals at once
- **Reproducible**: use the same seed to recreate any cathedral

## How to Run

No dependencies required — just Python 3.6+ with standard library:

```bash
python3 cathedral.py
```

### Options

```
--seed SEED        Random seed for reproducibility (default: random)
--width WIDTH      Canvas width in characters (default: 100)
--height HEIGHT    Canvas height in characters (default: 50)
--no-atmosphere    Skip stars and ground texture
--multi N          Generate N cathedrals with sequential seeds
```

### Examples

```bash
# Random cathedral
python3 cathedral.py

# Reproducible cathedral with seed 42
python3 cathedral.py --seed 42

# Larger cathedral
python3 cathedral.py --width 140 --height 60

# Generate 3 different cathedrals
python3 cathedral.py --multi 3

# Pure architecture, no atmosphere
python3 cathedral.py --no-atmosphere --seed 999
```

## How It Works

The generator uses a layered construction approach:

1. **Foundation**: Stone steps at the base
2. **Main body**: Rectangular nave with textured walls and horizontal course lines
3. **Roof**: Pointed/pitched roof filled with shading
4. **Towers**: Two flanking towers with windows and spires
5. **Central spire** (optional): Taller spire rising from the roof peak
6. **Rose window** (optional): Circular stained glass window on the façade
7. **Side windows**: Pointed-arch stained glass windows arranged along the nave
8. **Door(s)**: Gothic arched entrance, optionally double doors
9. **Flying buttresses** (optional): Arched supports extending from the walls
10. **Gargoyles** (optional): Decorative creatures on the façade
11. **Atmosphere**: Random stars and ground texture

Each architectural element uses Unicode block characters (█▓▒░), box drawing characters (╔╗╚╝├┤┬┼), and decorative symbols (✝✿◆◇●○✦✧) to create rich visual detail.

## Sample Output

Running `python3 cathedral.py --seed 42` produces a unique gothic cathedral with twin spired towers, a central rose window, stained glass side windows, flying buttresses, and an arched doorway — all rendered in ASCII art.

## License

MIT