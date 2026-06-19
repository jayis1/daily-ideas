# 🧬 Gene Splicer — Terminal Genetic Algorithm Playground

Breed, mutate, and evolve ASCII creatures through the power of genetic algorithms. Each creature has a unique genome that determines its appearance, body parts, colors, and traits. Guide their evolution by choosing fitness targets, cross-breeding champions, and injecting mutations.

## Features

- **Genetic Algorithm Engine** — Full population-based evolution with tournament selection, crossover, and mutation
- **ASCII Creature Rendering** — Creatures are rendered as colorful ASCII art based on their genome
- **5 Fitness Targets** — Evolve for complexity, color harmony, size, symmetry, or speed
- **Interactive Breeding** — Manually select two parents and splice their genomes together
- **Targeted Mutation** — Pick any creature and mutate it at a custom rate
- **Custom Creatures** — Design your own creature gene-by-gene
- **Diversity Tracking** — Monitor genetic diversity across your population
- **Evolution History** — ASCII chart showing fitness progression over generations
- **Auto-Evolve Mode** — Sit back and watch N generations unfold
- **Demo Mode** — Non-interactive showcase that evolves for three different fitness targets

## How It Works

Each creature has a **genome** — a list of **genes**, where each gene specifies:

| Field | Description |
|-------|-------------|
| `part` | Body part type (head, torso, arms, legs, tail, wings, horns, antennae) |
| `symbol` | The Unicode character used to render that part |
| `color_idx` | Index into a 256-color palette |
| `strength` | Expression strength (0.0–1.0), affects bold/dim rendering |
| `position` | Position in the genome sequence |

Evolution uses **tournament selection** (k=3) to pick parents, then performs **crossover** (uniform recombination) and **mutation** (symbol, color, strength, or part changes, plus gene insertion/deletion).

### Fitness Targets

| Target | Selects For |
|--------|-------------|
| `complexity` | More unique body parts (head + torso + arms + legs + tail + wings + horns + antennae) |
| `harmony` | Analogous color palettes (neighboring colors on the wheel) |
| `size` | Longer genomes (more genes = more body) |
| `symmetry` | Color symmetry between left/right halves of the genome |
| `speed` | Shorter genomes (fewer genes = faster creature) |

## Installation

No external dependencies — uses only Python's standard library:

```bash
# No pip install needed! Just clone and run:
git clone <repo-url>
cd 2026-06-19-gene-splicer
```

Requires Python 3.7+ for dataclasses and f-strings.

## How to Run

### Interactive Mode

```bash
python3 gene_splicer.py --interactive
# or
python3 gene_splicer.py -i
```

This opens the full interactive menu where you can:
- `[N]` Create a new population with custom size and fitness target
- `[E]` Evolve one generation and see the results
- `[A]` Auto-evolve N generations with a progress bar
- `[T]` Change the fitness target mid-evolution
- `[V]` View the top 10 creatures in the population
- `[B]` View the current champion in detail
- `[S]` Splice (crossover) two creatures of your choice
- `[M]` Mutate a creature at a custom rate
- `[H]` View evolution history as an ASCII chart
- `[D]` Diversity report showing gene pool richness
- `[X]` Create a custom creature gene-by-gene
- `[R]` Reset the population and start over

### Demo Mode (default)

```bash
python3 gene_splicer.py
```

Runs a non-interactive demo that evolves three populations (complexity, harmony, size) for 25 generations each, showing the initial and final champions.

## Usage Examples

### Start with complexity evolution

```
Command> n
Population size [20]: 30
Fitness target [complexity]: complexity

✓ Population of 30 creatures created!
Fitness target: complexity
```

### Auto-evolve 50 generations

```
Command> a
How many generations [20]? 50

Gen 50 | Best:  135.0 | Avg:  112.3 | Diversity:  97% | [█████████████████████████]
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
  Genome: ≧███░ ├████ △███░ ⊿██░░ ⊿██░░ ✧░░░░ ◟░░░░ ⊕░░░░ ☉░░░░ ☣░░░░ ☉░░░░
```

## Concepts

- **Crossover**: Two parent genomes are combined by randomly selecting each gene position from either parent
- **Mutation**: Each gene has a chance to change its symbol, color, strength, or body part type; genes can also be inserted or deleted
- **Elitism**: The top 2 performers survive unchanged into the next generation
- **Tournament Selection**: k=3 random contestants compete; the fittest becomes a parent

## License

MIT