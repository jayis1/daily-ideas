# 🧬 Gene Splicer v1.1 — Terminal Genetic Algorithm Playground

Breed, mutate, and evolve ASCII creatures through the power of genetic algorithms. Each creature has a unique genome that determines its appearance, body parts, colors, and traits. Guide their evolution by choosing fitness targets, cross-breeding champions, and injecting mutations.

## Features

### Core Evolution
- **Genetic Algorithm Engine** — Full population-based evolution with tournament selection, crossover, and mutation
- **5 Fitness Targets** — Evolve for complexity, color harmony, size, symmetry, or speed
- **Hybrid Fitness Target** — New blended objective combining complexity, harmony, and symmetry (40/35/25 weighting)
- **Evolve-to-Threshold** — Set a fitness target and evolve until it's reached (with safety max generation limit)

### Creature System
- **ASCII Creature Rendering** — Creatures are rendered as colorful ASCII art based on their genome across 3 body templates
- **8 Body Part Types** — Head, torso, arms, legs, tail, wings, horns, and antennae
- **Genome Summary** — Detailed part breakdown showing composition and average strength
- **Mutation Rate Control** — Choose how aggressively to mutate your creatures

### Interactive Controls
- **[N]** Create a new population with custom size and fitness target
- **[E]** Evolve one generation and see results
- **[A]** Auto-evolve N generations with progress bar
- **[G]** Evolve until a fitness threshold is reached (new!)
- **[T]** Change the fitness target mid-evolution
- **[V]** View the top 10 creatures
- **[B]** View the current champion in detail
- **[S]** Splice (crossover) two creatures of your choice
- **[M]** Mutate a creature at a custom rate
- **[H]** View evolution history as an ASCII chart
- **[D]** Diversity report showing gene pool richness
- **[X]** Create a custom creature gene-by-gene
- **[W]** Export champion or population to JSON (new!)
- **[L]** Load a creature or population from JSON (new!)
- **[R]** Reset the population and start over

### Data & Persistence
- **Creature Export/Import** — Save and load individual creatures as JSON files
- **Population Export/Import** — Save and restore entire populations including evolution history
- **Evolution History** — ASCII chart tracking best and average fitness across generations

### CLI Flags
- `--version` — Show version number
- `--help` — Show usage and examples
- `-i, --interactive` — Run in interactive mode
- `-t, --target {size,symmetry,complexity,harmony,speed,hybrid}` — Set fitness target
- `-g, --generations N` — Number of generations for demo mode (default: 25)
- `-p, --population N` — Population size for demo mode (default: 30)
- `--export FILE` — Export best creature from demo run to JSON
- `--import FILE` — Import a creature from JSON (interactive mode)

## How It Works

Each creature has a **genome** — a list of **genes**, where each gene specifies:

| Field | Description |
|-------|-------------|
| `part` | Body part type (head, torso, arms, legs, tail, wings, horns, antennae) |
| `symbol` | The Unicode character used to render that part |
| `color_idx` | Index into a 256-color palette |
| `strength` | Expression strength (0.0–1.0), affects bold/dim rendering |
| `position` | Position in the genome sequence |

Evolution uses **tournament selection** (k=3) to pick parents, then performs **crossover** (uniform recombination) and **mutation** (symbol, color, strength, or part changes, plus gene insertion/deletion). The top 2 performers survive unchanged into the next generation (elitism).

### Fitness Targets

| Target | Selects For |
|--------|-------------|
| `complexity` | More unique body parts (head + torso + arms + legs + tail + wings + horns + antennae) |
| `harmony` | Analogous color palettes (neighboring colors on the wheel) |
| `size` | Longer genomes (more genes = more body) |
| `symmetry` | Color symmetry between left/right halves of the genome |
| `speed` | Shorter genomes (fewer genes = faster creature) |
| `hybrid` | Balanced blend of complexity (40%), harmony (35%), and symmetry (25%) |

## Installation

No external dependencies — uses only Python's standard library:

```bash
# Just clone and run!
git clone <repo-url>
cd 2026-06-19-gene-splicer
```

Requires Python 3.7+ (for dataclasses and f-strings).

## How to Run

### Interactive Mode

```bash
python3 gene_splicer.py --interactive
# or
python3 gene_splicer.py -i
```

### Demo Mode (default)

```bash
# Default: evolve for complexity, harmony, and size (25 gens each)
python3 gene_splicer.py

# Custom target and generations
python3 gene_splicer.py --target hybrid --generations 50

# Export the best creature after demo
python3 gene_splicer.py --target complexity --generations 30 --export champion.json
```

### Import a Creature

```bash
# Load a previously exported creature into interactive mode
python3 gene_splicer.py -i --import champion.json
```

## Usage Examples

### Start with hybrid fitness target

```
Command> n
Population size [20]: 30
Fitness target [complexity]: hybrid

✓ Population of 30 creatures created!
Fitness target: hybrid
```

### Evolve to a fitness target

```
Command> g
  Evolve to Fitness Target
  Current best fitness: 85.0
  Target fitness [105.0]: 120
  Max generations (safety limit) [500]: 200

  Evolving until fitness ≥ 120.0 (max 200 gens)...

  ✓ Reached fitness 121.3 at generation 47!
```

### Export and import creatures

```
Command> w
  Export
  [1] Export best creature
  [2] Export entire population
  Choice: 1
  File path [creature.json]: my_best.json

  ✓ Champion exported to my_best.json
```

### Splice two creatures

```
Command> s
Select two creatures to splice:

  [1] Zorblix       fitness=120.0
  [2] Krimon        fitness=115.5
  ...

First parent #: 1
Second parent #: 2

  Offspring: Zorion — fitness=118.7
  Add to population? [Y/n]: y
```

### View the champion

```
Command> b

  ═══ Current Champion ═══

       ⊿  ☉  △
      ├     ◟

  Lux*^~*  (ID:CR4821)
  Genes: 11  |  Parts: 4  |  Avg Strength: 0.45  |  Colors: 3  |  Gen: 48  |  Fitness: 98.9
  Parts: [arms:3, head:2, legs:2, torso:2, wings:1, horns:1]  AvgStr: 0.45  Colors: 3
  Genome: ≧███░ ├████ △███░ ⊿██░░ ⊿██░░ ✧░░░░ ◟░░░░ ⊕░░░░ ☉░░░░ ☣░░░░ ☉░░░░
```

## Testing

```bash
python3 test_gene_splicer.py
```

Runs 151 tests covering:
- Gene and Creature data structures (creation, serialization, round-trip)
- Random generation (valid parts, symbols, strengths, sizes)
- Crossover (offspring properties, parent tracking)
- Mutation (rate effects, generation tracking)
- All 6 fitness functions (edge cases, empty genomes, relative ordering)
- EvolutionEngine (init, evolve, evolve_until, diversity, history)
- Export/import (JSON serialization round-trip for creatures and populations)
- Display helpers (box, fitness_bar, generation_chart)
- CLI argument parsing (defaults, all flags)
- Edge cases (empty genomes, duplicate genes, tiny populations)

## What's New in v1.1

- **`--help` and `--version` CLI flags** — Proper argparse-based CLI with usage examples
- **`--target`, `--generations`, `--population` flags** — Configure demo mode from the command line
- **`--export` and `--import` flags** — Save and load creatures/populations as JSON
- **Hybrid fitness target** — New blended objective combining complexity + harmony + symmetry
- **Evolve-to-threshold** — New interactive command `[G]` to evolve until a fitness goal is reached
- **Export/Import in interactive mode** — `[W]` and `[L]` commands for JSON persistence
- **Genome summary** — Detailed part breakdown showing composition and average strength
- **Minimum population of 3** — Extinction protection prevents population from becoming too small
- **Mutation rate clamping** — Interactive mutation rate is clamped to [0.0, 1.0]
- **Better input handling** — Helper methods for integer and float prompts with defaults
- **151 tests** — Comprehensive test suite for all modules and features

## Concepts

- **Crossover**: Two parent genomes are combined by randomly selecting each gene position from either parent
- **Mutation**: Each gene has a chance to change its symbol, color, strength, or body part type; genes can also be inserted or deleted
- **Elitism**: The top 2 performers survive unchanged into the next generation
- **Tournament Selection**: k=3 random contestants compete; the fittest becomes a parent
- **Hybrid Fitness**: Weighted blend of 0.40 × complexity + 0.35 × harmony + 0.25 × symmetry, normalized to ≈0–150

## License

MIT