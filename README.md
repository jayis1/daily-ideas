# Daily Ideas

> A growing arcade, laboratory, and physical-computing workshop: 105 standalone terminal projects plus 57 open SoC device designs, brought together by one launcher and a four-node system architecture.

Daily Ideas is an autonomously grown collection of terminal games, simulations, generators, puzzles, audio experiments, science visualizations, and utilities. Every project begins as a new idea, then passes through enhancement and bug-hunting stages before joining the collection.

The projects remain deliberately independent: open any dated directory, read one approachable Python program, and run it directly. The shared `daily-ideas` command makes the whole collection feel like one product without tightly coupling the applications.

## Highlights

- **105 runnable projects** grouped into seven searchable categories.
- **One launcher** for browsing, inspecting, selecting, and running every app.
- **Full-screen Command Center** with search, filters, random picks, app details, and one-key launching.
- **No framework lock-in**: most apps use only the Python standard library.
- **Terminal-native experiences** including curses interfaces, ANSI animation, audio generation, interactive games, and scriptable CLI tools.
- **Safe process isolation** so apps can control the terminal and signals without affecting the launcher.
- **Deterministic metadata** generated from the source tree and committed to Git.
- **Automated quality gates** for catalog validity, compilation, tests, and bounded smoke checks.
- **Learning-friendly layout** where every project retains its own source, tests, and documentation.
- **Four-node physical platform** that composes novel SoC designs into Observe, Reason, Act, and Coordinate systems.

## Beyond standalone ideas

The collection now has a second scale. Every design from the [SoC Device Inventions repository](https://github.com/jayis1/SoC-Device-Inventions) remains independently buildable, while the [Unified Four-Node System](./systems/) connects the full collection into larger working systems:

```text
Observe ──telemetry──► Reason ──commands──► Act
   ▲                     ▲                  │
   └──────feedback───────┘                  │
                         └── Coordinate ◄───┘
```

All 57 hardware designs are connected through a [unified registry](./systems/devices.json) and [shared device protocol](./systems/protocol/). The [complete unification guide](./systems/README.md) explains repository ownership, device roles, message contracts, deployment composition, and how every design participates. Use `daily-ideas system list` to see the roles, `daily-ideas system devices` to browse the complete fleet, and `daily-ideas system doctor` to prove that no imported design is missing.

## Requirements

- Python 3.8 or newer.
- Linux, macOS, or Windows for ordinary CLI applications.
- A real, Unicode-capable terminal for curses and full-screen applications.
- Optional dependencies are app-specific; `daily-ideas doctor` reports detected support.

Windows users may need `windows-curses` for full-screen apps. Audio playback support varies by platform, although audio-generating projects can generally export files without live playback.

## Installation and quick start

Clone the repository and install its launcher in editable mode:

```bash
git clone https://github.com/jayis1/daily-ideas.git
cd daily-ideas
python3 -m pip install -e .
daily-ideas doctor
daily-ideas system list
daily-ideas system doctor
daily-ideas browse
daily-ideas list
daily-ideas search dungeon
daily-ideas info terminal-roguelike
daily-ideas run ascii-dungeon-generator -- --help
daily-ideas random --category puzzle
daily-ideas doctor
```

Apps run as isolated child processes from their own directories, so interactive input, curses, signals, and relative assets continue to work. Arguments after `--` are passed directly to the selected app.

Installation is optional. From a checkout, the equivalent command is:

```bash
PYTHONPATH=src python3 -m daily_ideas.cli list
```

## Commands

| Command | Purpose |
|---|---|
| `browse` | Open the full-screen Terminal Command Center |
| `list` | Browse apps, optionally filtered by category or interface |
| `search` | Search IDs, titles, descriptions, categories, and tags |
| `info` | Show an app's entrypoint, requirements, and metadata |
| `run` | Launch an app in an isolated subprocess |
| `random` | Choose an app, optionally launching it with `--run` |
| `doctor` | Validate the catalog and report terminal/dependency support |
| `system list/info/doctor` | Inspect and validate the four-node hardware platform |

Set `DAILY_IDEAS_ROOT` when invoking an installed launcher outside the source checkout. App-specific writable data locations are exposed through `DAILY_IDEAS_APP_DATA`.

## Usage examples

Open the interactive Command Center:

```bash
daily-ideas browse
```

| Key | Action |
|---|---|
| `↑` / `↓` or `j` / `k` | Move through apps |
| `Page Up` / `Page Down` | Move ten entries |
| `Enter` | Launch the selected app and return afterward |
| `/` | Search the catalog |
| `c` / `C` | Cycle categories forward/backward |
| `r` | Select a random matching app |
| `Esc` | Clear all filters |
| `q` | Leave the Command Center |

Browse by category or interaction style:

```bash
daily-ideas list --category puzzle
daily-ideas list --category science
daily-ideas list --interface curses
```

Search across app IDs, titles, descriptions, categories, and tags:

```bash
daily-ideas search dungeon
daily-ideas search terminal puzzle
daily-ideas search music
```

Inspect an app before launching it, then forward app-specific options after `--`:

```bash
daily-ideas info ascii-dungeon-generator
daily-ideas run ascii-dungeon-generator -- --help
daily-ideas run ascii-dungeon-generator -- --seed 42 --width 80 --height 30
```

Choose an app at random, with optional reproducibility and filtering:

```bash
daily-ideas random
daily-ideas random --category creative --seed 42
daily-ideas random --category puzzle --run
```

Every project remains directly runnable:

```bash
cd 2026-06-12-terminal-roguelike
python3 roguelike.py
```

## How the integration works

The launcher is a control plane, not a shared application runtime:

```text
src/daily_ideas/apps.json
          │
          ▼
 searchable catalog ──► capability report
          │
          ▼
     safe runner ──► isolated Python subprocess
                          │
                          ├── app working directory
                          ├── original stdin/stdout/TTY
                          ├── forwarded arguments
                          └── app-specific data location
```

This boundary matters because the collection contains programs that manage curses state, ANSI rendering, keyboard input, timers, signals, audio, saves, and generated files. Child processes preserve that behavior and prevent global state from leaking between applications.

### Runtime environment

| Variable | Meaning |
|---|---|
| `DAILY_IDEAS_APP_ID` | Stable catalog ID of the running application |
| `DAILY_IDEAS_APP_DATA` | App-specific writable data directory |
| `DAILY_IDEAS_DATA_HOME` | Optional override for the launcher's data root |
| `DAILY_IDEAS_ROOT` | Optional source-checkout path when running outside the repository |

Existing apps need not use these variables. New apps can use `DAILY_IDEAS_APP_DATA` to keep saves and generated state outside the Git checkout.

## Repository layout

```text
daily-ideas/
├── README.md                     # Landing page and generated app index
├── pyproject.toml                # Installable launcher package
├── src/daily_ideas/
│   ├── apps.json                 # Committed canonical catalog
│   ├── catalog.py                # Loading, validation, and search
│   ├── cli.py                    # User-facing commands
│   ├── runner.py                 # Isolated app execution
│   └── tui.py                    # Full-screen Command Center
├── tools/                        # Discovery, docs, validation, smoke checks
├── tests/                        # Shared integration tests
├── systems/
│   ├── platform.json             # Four-node topology and contracts
│   └── soc-devices/              # Imported open hardware design library
├── .github/workflows/            # Collection-wide CI
└── YYYY-MM-DD-project-name/      # Independent app, README, and tests
```

## Interface types

| Interface | What to expect |
|---|---|
| `cli` | Bounded, script-friendly output and command-line options |
| `interactive` | Prompts and ordinary line-oriented keyboard input |
| `curses` | Full-screen terminal control; requires a real TTY |
| `animation` | ANSI rendering, timed frames, or direct keyboard interaction |
| `audio` | Audio synthesis, playback, or export behavior |

## Application catalog

<!-- APP_INDEX_START -->
**105 apps** across 7 categories. This section is generated.

<details><summary>Audio (4)</summary>

| App | Interface | Description |
|---|---|---|
| [Wave Synth  Terminal Audio Waveform Synthesizer](./2026-06-13-wave-synth/) | interactive | Version 1.2.2 — A command-line tool for generating, visualizing, mixing, and exporting audio waveforms entirely from your terminal. |
| [Morse Wave Translator](./2026-06-15-morse-wave-translator/) | animation | Encode and decode text as visual Morse code waveforms — dots and dashes rendered as animated ASCII sine waves, compact block-element oscilloscope traces, and optional real audio... |
| [Procedural Music Box](./2026-06-16-procedural-music-box/) | interactive | Algorithmic melody generator, visualizer, MIDI exporter, and WAV exporter. |
| [Terminal Drum Machine](./2026-06-17-terminal-drum-machine/) | animation | A feature-rich, Python-based drum machine that runs entirely in your terminal. Synthesize 8 drum sounds, build patterns with a step sequencer, add accents and flams for expressi... |

</details>

<details><summary>Creative (50)</summary>

| App | Interface | Description |
|---|---|---|
| [Procedural ASCII Dungeon Map Generator](./2026-06-12-ascii-dungeon-generator/) | animation | Generate random dungeon maps with rooms, corridors, monsters, treasures, traps, NPCs, and stairs — all rendered in beautiful ASCII art. |
| [ASCII Fractal Explorer](./2026-06-13-fractal-explorer/) | curses | Explore Mandelbrot, Julia, Burning Ship, and Tricorn sets directly in your terminal — with interactive zoom, pan, palette switching, smooth coloring, bookmarks, and mouse suppor... |
| [LOOM  Terminal Generative Art Weaver](./2026-06-13-loom/) | animation | Version 1.1.1 |
| [Procedural Planet Generator](./2026-06-13-procedural-planet-generator/) | animation | Generate infinite fictional worlds with detailed properties, habitability scores, hazard assessments, resource ratings, named moons, and ASCII art globe renderings. Each planet... |
| [CLI Tarot Reader](./2026-06-13-tarot-reader/) | animation | A beautifully rendered terminal tarot card reader with ASCII art cards, multiple spreads, full interpretations, and dramatic reveal animations. Pull cards from a complete 78-car... |
| [ASCII Kaleidoscope](./2026-06-14-ascii-kaleidoscope/) | animation | A mesmerizing terminal-based kaleidoscope that generates real-time, animated, symmetric patterns using Unicode block characters and ANSI 256-color mode. The engine computes patt... |
| [Befunge-93 Esoteric Language Interpreter](./2026-06-14-befunge93-interpreter/) | animation | v1.1.0 — A complete, fully-featured interpreter for Befunge-93, one of the most fascinating esoteric programming languages ever created. In Befunge-93, code lives on a 2D grid a... |
| [Constellation Map  Procedural Star Atlas Generator](./2026-06-14-constellation-map/) | animation | A command-line tool that generates rich, navigable ASCII star maps with procedurally created constellations, mythical names, deep sky objects, nebulae, meteor showers, and lore.... |
| [Markov Chain Haiku Generator](./2026-06-14-markov-haiku-generator/) | animation | A CLI tool that builds Markov chains from text input and generates 5-7-5 syllable haikus (or 5-7-5-7-7 tanka poems) with automatic season detection, syllable stats, colored term... |
| [Terminal ASCII Fireworks Simulator](./2026-06-15-ascii-fireworks/) | curses | A real-time fireworks display in your terminal with particle physics, multiple explosion patterns, and choreographed shows. Watch rockets launch, explode into dazzling patterns,... |
| [Terminal Mondrian Art Generator v3.0.1](./2026-06-15-mondrian-generator/) | animation | Generate Piet Mondrian-style De Stijl compositions directly in your terminal using Unicode box-drawing characters and ANSI 24-bit true colors. |
| [Sorting Algorithm Race v2.1](./2026-06-15-sorting-algorithm-race/) | animation | A real-time terminal visualization that pits multiple sorting algorithms against each other in a head-to-head race. Watch Bubble Sort struggle, Quick Sort fly, and Tim Sort hold... |
| [Terminal Typing Racer](./2026-06-15-typing-racer/) | curses | A fast-paced typing game that runs entirely in your terminal. Words fall from the top of the screen — type them before they hit the danger zone! Features progressive difficulty,... |
| [ASCII Topography Map Generator](./2026-06-16-ascii-topography/) | animation | Generate beautiful, detailed topographic maps in your terminal using Perlin noise. Features contour lines, rivers, lakes, named peaks, terrain shading with ANSI colors, elevatio... |
| [Barchart Race  Animated ASCII Bar Chart Race Visualizer](./2026-06-16-barchart-race/) | animation | Watch values compete and rankings shift over time with smooth ASCII animations. Supports multiple data sources, transformation modes, HTML export, and more. |
| [Decision Oracle](./2026-06-16-decision-oracle/) | interactive | An interactive CLI tool for building, consulting, and visualizing binary decision trees. Grow your own knowledge trees by answering yes/no questions, then consult the Oracle whe... |
| [Procedural Heraldry Generator](./2026-06-17-heraldry-generator/) | animation | A command-line tool that generates random medieval-style coats of arms following authentic heraldic rules, rendered as colorful ASCII art in the terminal. Each coat of arms incl... |
| [Procedural Inkblot Generator](./2026-06-17-inkblot-generator/) | animation | Version 2.0.0 |
| [Maze Generator & Pathfinder Visualizer](./2026-06-17-maze-pathfinder-visualizer/) | animation | v1.3.1 — Generate mazes with five algorithms and watch five pathfinding solvers explore them in real-time ASCII animation, right in your terminal. |
| [Terminal Alchemy](./2026-06-17-terminal-alchemy/) | animation | A Little Alchemy-inspired element-combining game that runs entirely in your terminal. Start with four base elements — water, fire, earth, and air — and combine them to discover... |
| [Voronoi Generator v2.0.0](./2026-06-17-voronoi-generator/) | animation | A terminal-based Voronoi diagram generator that produces beautiful, colorful tessellations using Unicode block characters and ANSI 256-color mode. A Voronoi diagram partitions a... |
| [Terminal Lava Lamp v3.1.0](./2026-06-18-terminal-lava-lamp/) | animation | A mesmerizing ASCII lava lamp simulation that runs in your terminal, featuring colored wax blobs that rise and fall inside a lamp-shaped container with real-time physics, rising... |
| [Procedural Dinosaur Generator](./2026-06-19-procedural-dinosaur-generator/) | animation | Version 2.0.0 |
| [Procedural Flag Generator](./2026-06-19-procedural-flag-generator/) | animation | A creative CLI tool that generates random fictional country flags with various geometric patterns and renders them as colorful Unicode block art directly in your terminal. Every... |
| [Terminal Mandala Generator](./2026-06-19-terminal-mandala-generator/) | animation | A Python CLI tool that generates beautiful, radially symmetric mandala patterns in your terminal using Unicode block characters and ANSI 256-color palette. |
| [Alien Language Generator v2.1.0](./2026-06-20-alien-language-generator/) | interactive | A procedural conlang (constructed language) generator that creates fully-formed alien languages with unique phonology, grammar, vocabulary, and a custom glyph-based writing syst... |
| [Procedural Cathedral Generator](./2026-06-20-procedural-cathedral-generator/) | animation | Generate unique ASCII art gothic cathedrals every time! Each run produces a different cathedral with randomized spires, rose windows, stained glass, flying buttresses, arched do... |
| [Terminal Cocktail Mixologist](./2026-06-22-cocktail-mixologist/) | interactive | Procedural cocktail recipe generator — creates unique, plausible cocktail recipes with creative names, flavor balance scoring, ingredient substitutions, ASCII art glassware, pai... |
| [Dice Notation Roller & Probability Analyzer](./2026-06-22-dice-notation-probability/) | cli | A command-line tool that parses standard and advanced dice notation, rolls dice, computes exact probability distributions, and renders beautiful ASCII histograms. Perfect for TT... |
| [Procedural Mythology Generator](./2026-06-22-mythology-generator/) | animation | Generate complete, original fictional mythologies — pantheons of gods with domains, relationships, creation myths, sacred narratives, cosmologies, and taboos. Every run produces... |
| [Spell Grimoire Generator](./2026-06-22-spell-grimoire-generator/) | animation | Procedural fantasy RPG spell generator — create unique, detailed spells with ASCII art sigils, incantations, casting recipes, power ratings, and more. |
| [Procedural Micro-Nation Generator](./2026-06-24-micro-nation-generator/) | animation | A command-line tool that generates complete fictional micro-nations — each with a unique ASCII flag, leader, national anthem, government, economy, culture, and diplomatic relati... |
| [Procedural City Skyline Generator](./2026-06-26-city-skyline-generator/) | animation | A CLI tool that generates detailed, atmospheric ASCII city skylines with buildings, weather effects, time-of-day lighting, varied architectural styles, neon signs, waterfront re... |
| [Terminal Spirograph](./2026-06-26-terminal-spirograph/) | animation | Generate beautiful hypotrochoid, epitrochoid, rose, and Lissajous curve patterns directly in your terminal using Unicode characters and ANSI colors. |
| [Cryptid Encyclopedia](./2026-06-27-cryptid-encyclopedia/) | interactive | A procedurally-generated bestiary of creatures that may or may not exist. Each cryptid is deterministically generated from its name — the same name always produces the same crea... |
| [Procedural Treasure Map Generator](./2026-06-28-treasure-map-generator/) | animation | Generate unique, elaborate ASCII treasure maps with coastlines, terrain features, dotted trails, compass roses, sea monsters, pirate riddles, and X-marks-the-spot. Every map is... |
| [Procedural Spaceship Blueprint Generator](./2026-06-29-spaceship-blueprint-generator/) | cli | A command-line tool that generates unique, detailed ASCII spaceship blueprints every time you run it. Each ship has a randomized class, name, crew manifest, room layout, weapons... |
| [ASCII Terrain Flyover](./2026-06-30-ascii-terrain-flyover/) | animation | A procedurally generated 3D-like terrain flyover rendered entirely in your terminal using ANSI 256-color codes and Unicode characters. Soar over mountains, oceans, forests, and... |
| [Perfume Alchemist](./2026-06-30-perfume-alchemist/) | interactive | A procedural perfume generator that creates unique, evocative fragrance compositions with note pyramids, scent profile visualizations, harmony scores, side-by-side comparisons,... |
| [Procedural Fingerprint Generator](./2026-07-01-procedural-fingerprint-generator/) | animation | Version 1.1.1 |
| [Conspiracy Board Generator v2.1](./2026-07-03-conspiracy-board-generator/) | animation | A procedurally generated conspiracy theory board — complete with red-string connections, classified documents, suspicion scores, cycle detection, and timeline events. Generates... |
| [Procedural Snowflake Generator](./2026-07-04-procedural-snowflake-generator/) | animation | Version 2.1.0 — Generate unique, mathematically-derived snowflake crystal patterns using fractal branching algorithms. No two are alike — just like real snowflakes! |
| [Terminal Lighthouse Keeper](./2026-07-08-terminal-lighthouse-keeper/) | curses | A meditative ASCII resource management game where you keep a lighthouse burning through the night. Manage your fuel, maintain the lens, cool the engine, rescue ships in distress... |
| [Terminal Stained Glass Generator](./2026-07-14-terminal-stained-glass/) | animation | Procedurally generate beautiful stained glass window patterns directly in your terminal! Each window features colored Unicode characters arranged in authentic architectural styl... |
| [Terminal Cuckoo Clock Simulator](./2026-07-23-terminal-cuckoo-clock/) | curses | A self-contained, zero-dependency ASCII-art cuckoo clock for your terminal. It |
| [Terminal Séance  Ouija Board Simulator](./2026-07-29-terminal-seance/) | animation | 🕯️ Conduct a séance right in your terminal. Place your fingers on the planchette, ask the spirits a question, and watch as the planchette glides across an ANSI-rendered Ouija bo... |
| [Terminal DNA Double-Helix Animator](./2026-08-07-terminal-dna-helix/) | animation | A rotating, coloured ASCII DNA double-helix that lives in your terminal. |
| [Terminal Semaphore Flag Signaler](./2026-08-13-terminal-semaphore-signaler/) | animation | A CLI tool that translates text into maritime flag semaphore positions and visualizes them as animated ASCII stick figures holding flags. Each letter of the alphabet is represen... |
| [ASCII Stereogram Generator SIRDS](./2026-08-16-ascii-stereogram-generator/) | cli | > Generate single-image random dot stereograms in the terminal using ASCII characters. Hidden 3D shapes pop out when you relax or cross your eyes. |
| [ASCII Morse Broadcasting Station](./2026-08-19-ascii-morse-broadcasting/) | animation | A terminal-based vintage shortwave radio station simulator that broadcasts Morse code in real time — doubled as a practical Morse code utility toolkit. Watch as it cycles throug... |

</details>

<details><summary>Game (9)</summary>

| App | Interface | Description |
|---|---|---|
| [Terminal Roguelike Engine](./2026-06-12-terminal-roguelike/) | interactive | A full-featured ASCII dungeon crawler built entirely in Python — no external dependencies required. Descend through 5 floors of procedurally generated dungeons, fight 10 enemy t... |
| [CLI Escape Room](./2026-06-14-cli-escape-room/) | animation | v2.0.0 — A fully interactive text-based escape room game for your terminal. Wake up in a locked cell with no memory. Explore rooms, collect items, solve interconnected puzzles,... |
| [CLI Tamagotchi v2.2](./2026-06-14-cli-tamagotchi/) | animation | A fully-featured virtual pet that lives in your terminal! Choose from 5 species (cat, dog, dragon, slime, robot), each with unique ASCII art, personality traits, and response te... |
| [Terminal Slot Machine](./2026-06-16-terminal-slot-machine/) | curses | A fully-featured animated casino slot machine right in your terminal! Spin the reels, place bets, and chase the jackpot — all with colorful ANSI graphics and smooth animations.... |
| [ASCII Sokoban](./2026-06-17-ascii-sokoban/) | animation | A feature-rich terminal-based implementation of the classic Sokoban box-pushing puzzle game, rendered with Unicode box-drawing characters and colored ANSI output. |
| [Terminal Mastermind](./2026-06-22-terminal-mastermind/) | animation | A beautiful, fully-featured Mastermind code-breaking game for the terminal — with colored pegs, multiple difficulty levels, an AI auto-solver using Knuth's minimax algorithm, a... |
| [Terminal Lunar Lander](./2026-06-23-terminal-lunar-lander/) | curses | A classic physics-based lunar landing game rendered entirely in ASCII art. Pilot your lunar module safely to the surface by managing thrust, fuel, and descent angle across proce... |
| [Terminal Tower Defense v2.3](./2026-07-02-terminal-tower-defense/) | curses | A fully playable tower defense game rendered entirely in the terminal using ASCII art and curses. Strategically place and upgrade towers, deploy power-ups, and defend against wa... |
| [Terminal Lock Picker](./2026-07-05-terminal-lock-picker/) | curses | An interactive terminal-based simulation of picking pin tumbler locks. Feel the tension, find the binding pins, lift them to the shear line, and experience the satisfying click... |

</details>

<details><summary>Puzzle (6)</summary>

| App | Interface | Description |
|---|---|---|
| [Regex Crossword Generator & Solver](./2026-06-14-regex-crossword/) | cli | v1.3.0 — A CLI tool for generating and solving regex crossword puzzles — a mind-bending puzzle type where each cell must satisfy both a row regex constraint and a column regex c... |
| [Pipes Puzzle](./2026-06-15-pipes-puzzle/) | curses | A terminal-based pipe rotation puzzle game built with Python and curses. Rotate pipe segments on a grid to connect water flow from the source (▶ left side) to the drain (▶ right... |
| [Terminal Rubik's Cube](./2026-06-18-terminal-rubiks-cube/) | animation | A fully interactive 3×3 Rubik's Cube simulator rendered entirely in the terminal with ANSI colors. Supports all 18 standard moves, scramble, undo, solve detection, and multiple... |
| [Nonogram Picross](./2026-06-19-nonogram-picross/) | animation | A terminal-based Nonogram (Picross) puzzle game and solver written in Python. |
| [Chess Puzzle Generator](./2026-06-20-chess-puzzle-generator/) | interactive | A terminal-based chess puzzle generator that creates forced-mate puzzles and lets you solve them interactively. Uses a minimax search engine to verify that each puzzle has a gua... |
| [Terminal Crossword Puzzle](./2026-06-27-terminal-crossword/) | animation | A feature-rich interactive crossword puzzle generator and game for your terminal. Creates random tech-themed crossword puzzles you can play right in the command line — with colo... |

</details>

<details><summary>Science (10)</summary>

| App | Interface | Description |
|---|---|---|
| [CellLab  Interactive Cellular Automata Laboratory](./2026-06-13-cellular-automata-lab/) | curses | Explore the emergent beauty of cellular automata right in your terminal. CellLab supports both 1D elementary automata (Wolfram rules 0–255) and 2D Life-like automata (10 presets... |
| [Collatz Explorer](./2026-06-14-collatz-explorer/) | animation | v1.2.0 — A terminal-based visualization tool for exploring the Collatz Conjecture — one of mathematics' most famous unsolved problems. |
| [ASCII Circuit Simulator](./2026-06-16-ascii-circuit-simulator/) | animation | A digital logic circuit simulator with ASCII art rendering, truth table generation, circuit validation, DSL export, and interactive mode. Define circuits using a simple text DSL... |
| [N-Body Gravity Simulator](./2026-06-16-nbody-gravity-simulator/) | curses | A real-time terminal-based gravitational N-body simulation. Spawn celestial bodies, watch orbits form, witness collisions and mergers, and observe chaotic gravitational dynamics... |
| [Periodic Table Explorer](./2026-06-17-periodic-table-explorer/) | curses | An interactive terminal-based periodic table of the elements built with Python curses. Browse all 118 elements, navigate the full periodic table layout, search by name or symbol... |
| [ASCII Reaction-Diffusion Lab](./2026-06-18-reaction-diffusion-lab/) | animation | A terminal-based simulator for the Gray-Scott reaction-diffusion model — the mathematical system that produces stunning organic patterns like coral growth, cell mitosis, spots,... |
| [Gene Splicer v1.1  Terminal Genetic Algorithm Playground](./2026-06-19-gene-splicer/) | animation | Breed, mutate, and evolve ASCII creatures through the power of genetic algorithms. Each creature has a unique genome that determines its appearance, body parts, colors, and trai... |
| [Terminal Seismograph Simulator](./2026-06-19-seismograph-simulator/) | animation | A real-time terminal-based seismograph simulator that visualizes earthquake seismic waves propagating through a network of monitoring stations. Watch P-waves, S-waves, and surfa... |
| [Solar System Orrery v3.1](./2026-06-19-solar-system-orrery/) | curses | An animated terminal-based orrery that displays all eight planets orbiting the Sun using real orbital mechanics — with opposition detection, transit alerts, find-next-conjunctio... |
| [Volcano Eruption Simulator](./2026-06-20-volcano-eruption-simulator/) | animation | A terminal-based ASCII simulation of a volcanic eruption with procedurally generated terrain, lava fountains, flowing lava, pyroclastic flows, ash clouds, seismic tremors, a day... |

</details>

<details><summary>Simulation (18)</summary>

| App | Interface | Description |
|---|---|---|
| [Terminal Aquarium](./2026-06-13-terminal-aquarium/) | curses | A beautiful animated aquarium that lives in your terminal. Watch procedurally generated fish swim, plants sway, and bubbles rise — all rendered in glorious curses-based ASCII ar... |
| [Boids Flocking Simulator](./2026-06-15-boids-flocking/) | curses | A real-time terminal simulation of Craig Reynolds' classic Boids algorithm — watch emergent flocking behavior arise from just three simple rules: separation, alignment, and cohe... |
| [ASCII Ecosystem Simulator](./2026-06-15-ecosystem-simulator/) | curses | A terminal-based ecosystem simulation that models the dynamics of a living world — plants grow and spread, herbivores graze and flee, predators hunt and reproduce. Watch populat... |
| [Crystal Growth Simulator v2.1](./2026-06-18-crystal-growth-simulator/) | animation | A real-time terminal visualization of Diffusion-Limited Aggregation (DLA) — watch particles randomly walk and stick together, forming beautiful branching, fractal-like crystalli... |
| [Turing Machine Simulator](./2026-06-18-turing-machine-simulator/) | curses | A fully-featured Turing machine simulator with 12 built-in programs, visual (curses) and batch execution modes, state diagram export, and comprehensive testing. |
| [Terminal Polygraph Simulator v2.1.0](./2026-06-19-polygraph-simulator/) | animation | An interactive lie detector simulation that analyzes your keystroke dynamics — typing speed, rhythm consistency, hesitations, and corrections — to estimate whether you're being... |
| [Terminal Stock Exchange](./2026-06-20-terminal-stock-exchange/) | curses | A fully interactive terminal-based stock market simulator with procedurally generated companies, realistic price dynamics (Geometric Brownian Motion-inspired), portfolio managem... |
| [Water Ripple Simulator](./2026-06-20-water-ripple-simulator/) | animation | A real-time 2D wave equation simulator rendered in the terminal using Unicode block characters and 24-bit ANSI colors. Drop stones, place wave sources, build walls, save/load st... |
| [Terminal Ant Colony Simulator](./2026-06-25-ant-colony-simulator/) | curses | A real-time emergent behavior simulation where ants forage for food, leave pheromone trails, and collectively discover optimal paths — all rendered as colorful ASCII art in your... |
| [Rube Goldberg Machine Simulator](./2026-06-25-rube-goldberg-simulator/) | animation | A terminal-based ASCII animation of absurdly complex chain-reaction machines. Watch as balls, dominoes, seesaws, buckets, pulleys, fans, springs, hammers, and more interact in h... |
| [Terminal Hacker Simulator](./2026-06-29-terminal-hacker-simulator/) | animation | A cinematic hacking simulation game played entirely in the terminal. Break into procedurally generated corporate networks, crack access codes, analyze nodes for intel, deploy sp... |
| [ASCII Train Simulator](./2026-07-02-ascii-train-simulator/) | curses | A terminal-based side-scrolling steam locomotive simulator. Drive your train through procedurally generated terrain, managing speed, coal, water, and steam pressure while stoppi... |
| [Terminal Sonar Simulator](./2026-07-03-terminal-sonar-simulator/) | curses | A submarine combat game played entirely in the terminal. Navigate a fog-of-war ocean using sonar pings to detect, classify, and destroy hidden enemy vessels — while trying not t... |
| [Terminal Garden Simulator](./2026-07-11-terminal-garden-simulator/) | interactive | A procedural ASCII garden simulator where you plant, grow, water, fertilize, and harvest procedural plants through changing seasons and weather. Manage your garden across Spring... |
| [Galton Board Simulator](./2026-07-20-galton-board-simulator/) | animation | A live, interactive terminal simulation of a Galton board (also called a |
| [Terminal Aurora Borealis Simulator](./2026-07-26-terminal-aurora-simulator/) | animation | A self-contained Python program that paints a procedurally-animated aurora |
| [Terminal Pendulum Wave Simulator](./2026-08-04-pendulum-wave-simulator/) | animation | A physics-based ASCII animation of the pendulum wave — one of the most |
| [Domino Chain Simulator](./2026-08-10-domino-chain-simulator/) | animation | A terminal-based domino chain reaction simulator written in pure Python. Set up dominoes with varied heights and spacings, trigger any domino, and watch the cascade ripple acros... |

</details>

<details><summary>Utility (8)</summary>

| App | Interface | Description |
|---|---|---|
| [Rune Cipher ᚱᚢᚾᛖ](./2026-06-12-rune-cipher/) | interactive | A terminal cryptography playground that encodes messages with historical ciphers, renders output in Elder Futhark runic Unicode, cracks ciphertext using frequency analysis and h... |
| [Terminal Slides](./2026-06-13-terminal-slides/) | animation | A presentation tool that runs entirely in your terminal. Write your slides in Markdown, present them with beautiful ANSI colors and keyboard navigation — no GUI required. |
| [Terminal Spreadsheet](./2026-06-16-terminal-spreadsheet/) | curses | A fully interactive, curses-based mini spreadsheet that runs right in your terminal. Edit cells, write formulas, reference other cells, and use built-in functions — all with a k... |
| [Curta Type II  Mechanical Calculator Simulator](./2026-06-18-mechanical-calculator/) | animation | A faithful terminal simulation of the Curta Type II mechanical calculator, the remarkable hand-cranked calculating machine invented by Curt Herzstark in a Buchenwald concentrati... |
| [Terminal Enigma Machine](./2026-06-18-terminal-enigma-machine/) | interactive | A complete simulation of the WWII Enigma cipher machine with 8 historical rotors, 3 reflectors, configurable plugboard, visual encryption path tracing, random configuration gene... |
| [Terminal Departure Board](./2026-06-23-terminal-departure-board/) | animation | A real-time animated flip-board style airport departure/arrival display (FIDS) running entirely in the terminal. Watch flights get procedurally generated, scheduled, delayed, ca... |
| [Terminal Typewriter Simulator](./2026-07-17-terminal-typewriter/) | curses | v1.3.0 |
| [Regex Engine Visualizer](./2026-08-01-regex-engine-visualizer/) | animation | A tiny backtracking regex engine that records every step of the matching |

</details>

<!-- APP_INDEX_END -->

## Maintaining the collection

The catalog is committed so launching is fast and deterministic. After adding or changing an app:

```bash
python3 tools/discover_apps.py
python3 tools/update_readme.py
python3 tools/discover_apps.py --check
PYTHONPATH=src python3 tools/validate_catalog.py
python3 -m unittest discover -s tests -v
python3 tools/smoke_apps.py
```

A canonical app directory must:

- Be named `YYYY-MM-DD-lowercase-slug`.
- Contain at least one runnable Python entrypoint.
- Include a project-level `README.md` with usage examples.
- Keep tests and assets inside its own directory.
- Avoid assuming the repository root is its working directory.
- Prefer a bounded `--help` or other non-interactive smoke path.

The discovery tool finds the likely entrypoint, extracts documentation, classifies the interface, assigns search tags, and records safe smoke arguments. Review the generated metadata whenever an app has multiple executables or unusual runtime requirements.

## Pipeline model

The autonomous generator, enhancer, and bug hunter can continue producing independent apps. A final integration gate turns those projects into a coherent collection:

| Stage | Responsibility |
|---|---|
| Generator | Conceive a distinct idea and build a complete runnable first version |
| Enhancer | Add meaningful features, improve usability and documentation, and extend tests |
| Bug hunter | Execute real workflows, probe edge cases, fix failures, and verify behavior |
| Integration gate | Regenerate metadata, validate structure, compile sources, run tests and smoke checks, and update this page |

Apps do not depend on launcher internals. Their shared contract is discoverable structure and executable behavior, allowing every project to remain understandable and portable.

## Testing and quality

Collection-wide verification uses several layers:

1. Python compilation catches syntax errors across shared tooling and app sources.
2. Catalog validation ensures IDs are unique and every entrypoint exists.
3. Shared tests cover search, command dispatch, argument forwarding, and subprocess safety.
4. Smoke checks invoke safe `--help` paths with timeouts and disabled stdin.
5. Individual project test suites exercise each application's domain logic.

GitHub Actions runs the shared checks on pushes and pull requests. Full-screen apps are not blindly launched in non-interactive CI; they use bounded CLI paths or project-specific unit tests.

## Troubleshooting

### The launcher cannot find the app sources

Run it from the checkout or point it at the repository:

```bash
export DAILY_IDEAS_ROOT=/path/to/daily-ideas
daily-ideas run terminal-roguelike
```

### A curses app fails or renders incorrectly

Use a real terminal, enlarge the window, and ensure `TERM` is configured correctly. On Windows, install `windows-curses` if your Python distribution does not provide curses.

### An optional dependency is missing

Run `daily-ideas doctor` to inspect detected packages. Install only what the desired app requires instead of adding every optional dependency globally.

### Generated files appear in the checkout

New applications should write persistent state beneath `DAILY_IDEAS_APP_DATA`. Some older self-contained apps may continue writing relative to their own directories until migrated.

### The catalog or README index is stale

```bash
python3 tools/discover_apps.py
python3 tools/update_readme.py
python3 tools/discover_apps.py --check
```

## Contributing

Contributions can improve an existing app, add a new idea, or strengthen the shared launcher. Keep changes scoped and preserve the independence of unrelated projects.

For new apps, favor deterministic options such as `--seed` where appropriate, clear terminal requirements, safe output paths, a bounded non-interactive mode, and tests that do not require manual input. Before opening a pull request, run the maintenance commands above and confirm `daily-ideas doctor` reports a valid catalog.

## Status and scope

Daily Ideas is an experimental, continuously evolving collection. Projects favor creativity, readability, and terminal-native fun over a uniform internal API. The launcher unifies discovery and execution while leaving room for each idea to have its own personality.

Unless an individual project says otherwise, treat generated outputs and simulations as entertainment or educational material—not professional, scientific, financial, or safety-critical advice.
