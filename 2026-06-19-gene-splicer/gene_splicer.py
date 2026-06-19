#!/usr/bin/env python3
"""
Terminal Gene Splicer — breed ASCII creatures through genetic algorithms!

A genetic algorithm playground where you breed populations of ASCII creatures,
selecting for traits, cross-breeding, mutating, and evolving them over generations.

Enhancements from v1.1:
- Added --help, --version, --target, --generations, --population CLI flags
- Added creature export/import (JSON) via --export and --import
- Added lineage tracking: each creature records its ancestors
- Added evolve-to-threshold mode in interactive menu (evolve until fitness reaches target)
- Added extinction protection: population never drops below 3
- Added genome summary method for more detailed stats
- Improved crossover to preserve part-type diversity
- Added fitness_hybrid target that blends multiple objectives
- Better error handling in interactive input loops
- Proper argparse-based CLI with all flags
"""

import argparse
import json
import random
import copy
import math
import os
import sys
import time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

__version__ = "1.1.0"

# ─── Creature Genome ───────────────────────────────────────────────────────

GENE_COLORS = [
    "\033[38;5;196m", "\033[38;5;202m", "\033[38;5;208m", "\033[38;5;214m",
    "\033[38;5;220m", "\033[38;5;226m", "\033[38;5;190m", "\033[38;5;154m",
    "\033[38;5;118m", "\033[38;5;82m", "\033[38;5;46m", "\033[38;5;47m",
    "\033[38;5;48m", "\033[38;5;49m", "\033[38;5;51m", "\033[38;5;87m",
    "\033[38;5;123m", "\033[38;5;159m", "\033[38;5;195m", "\033[38;5;231m",
    "\033[38;5;213m", "\033[38;5;219m", "\033[38;5;225m", "\033[38;5;189m",
    "\033[38;5;183m", "\033[38;5;177m", "\033[38;5;171m", "\033[38;5;165m",
    "\033[38;5;129m", "\033[38;5;93m", "\033[38;5;99m", "\033[38;5;135m",
    "\033[38;5;171m", "\033[38;5;207m", "\033[38;5;203m", "\033[38;5;199m",
]

BODY_PARTS = ["head", "torso", "arms", "legs", "tail", "wings", "horns", "antennae"]

SYMBOL_POOLS = {
    "head":    ["◉", "○", "◎", "⊙", "۞", "✿", "❋", "⊕", "⊗", "☉", "Θ", "☺", "☻", "☣", "☮", "♛"],
    "torso":   ["║", "▓", "█", "▒", "╬", "╪", "◈", "◆", "♦", "▣", "▮", "▯", "▧", "▨", "◧", "◩"],
    "arms":    ["╱", "╲", "╳", "┃", "┋", "┊", "┆", "╟", "╢", "├", "┤", "╠", "╣", "╫", "╋", "╂"],
    "legs":    ["╲", "╱", "╳", "┃", "┋", "┊", "┆", "┘", "└", "┐", "┌", "╝", "╚", "╗", "╔", "║"],
    "tail":    ["~", "≈", "∿", "〜", "〰", "°", "˜", "§", "¶", "¤", "⁂", "✦", "✧", "⊹", "⊱", "◟"],
    "wings":   ["≦", "≧", "⊿", "△", "▽", "◁", "▷", "♤", "♧", "♡", "♢", "✧", "✦", "⟡", "◈", "◇"],
    "horns":   ["^", "△", "⌃", "⌅", "⌈", "⌉", "╱", "╲", "⍋", "⍙", "⌂", "↟", "↱", "↲", "⌇", "⌇"],
    "antennae": ["⌇", "⌇", "¨", "ˋˋ", "¯", "‾", "⌒", "⌢", "⏋", "⏌", "⌈", "⌉", "⌐", "⌑", "⍋", "⍢"],
}

TEMPLATE_FRAMES = [
    # Frame 0: basic humanoid
    {
        "head":    (1, 0),
        "horns":   (0, -1), "horns2": (2, -1),
        "antennae":(0, -1), "antennae2":(2, -1),
        "torso":   (1, 1),
        "arms":    (0, 1), "arms2": (2, 1),
        "legs":    (0, 2), "legs2": (2, 2),
        "tail":    (3, 2),
        "wings":   (-1, 1), "wings2": (3, 1),
    },
    # Frame 1: bug-like
    {
        "head":    (2, 0),
        "antennae":(1, -1), "antennae2":(3, -1),
        "torso":   (2, 1),
        "arms":    (1, 1), "arms2": (3, 1),
        "horns":   (1, 0), "horns2": (3, 0),
        "legs":    (0, 2), "legs2": (1, 2), "legs3": (3, 2), "legs4": (4, 2),
        "tail":   (4, 1),
        "wings":  (0, 0), "wings2": (4, 0),
    },
    # Frame 2: beast
    {
        "head":    (0, 1),
        "horns":   (0, 0), "horns2": (1, 0),
        "torso":   (2, 1),
        "legs":    (3, 2), "legs2": (4, 2), "legs3": (1, 2),
        "tail":    (4, 0),
        "arms":    (1, 1),
        "wings":   (2, 0),
        "antennae":(0, -1),
    },
]

FITNESS_TARGETS = {
    "size":      "How large the creature is (genome length)",
    "symmetry":  "How symmetric the creature appears",
    "complexity":"Number of unique body parts used",
    "harmony":   "Color harmony of the creature's palette",
    "speed":     "Fewer genes = faster creature",
    "hybrid":    "Blend of complexity + harmony + symmetry",
}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CLEAR = "\033[2J\033[H"


@dataclass
class Gene:
    part: str           # body part type
    symbol: str         # the character/symbol
    color_idx: int      # index into GENE_COLORS
    strength: float     # 0.0-1.0 expression strength
    position: int       # positional offset in genome

    def to_dict(self) -> dict:
        """Serialize gene to a dictionary for JSON export."""
        return {
            "part": self.part,
            "symbol": self.symbol,
            "color_idx": self.color_idx,
            "strength": round(self.strength, 4),
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Gene":
        """Deserialize gene from a dictionary."""
        return cls(
            part=d["part"],
            symbol=d["symbol"],
            color_idx=d["color_idx"],
            strength=d["strength"],
            position=d["position"],
        )


@dataclass
class Creature:
    name: str
    genome: List[Gene]
    generation: int = 0
    fitness: float = 0.0
    parent_ids: List[str] = field(default_factory=list)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"CR{random.randint(1000,9999)}"

    @property
    def body_parts_used(self) -> set:
        return {g.part for g in self.genome}

    def render(self, width: int = 40, compact: bool = False) -> str:
        """Render creature as ASCII art based on its genome."""
        if not self.genome:
            return "  (empty organism)"

        # Pick a template based on genome hash
        template_idx = sum(g.position for g in self.genome) % len(TEMPLATE_FRAMES)
        template = TEMPLATE_FRAMES[template_idx]

        # Build a grid
        lines = {}
        for gene in self.genome:
            part = gene.part
            # Map gene to template position
            key = part
            count = sum(1 for g in self.genome[:self.genome.index(gene)] if g.part == part)
            if count > 0:
                key = f"{part}{count+1}"

            if key in template:
                x, y = template[key]
            elif part in template:
                x, y = template[part]
            else:
                continue

            if y not in lines:
                lines[y] = {}
            color = GENE_COLORS[gene.color_idx % len(GENE_COLORS)]
            symbol = gene.symbol
            if gene.strength < 0.3:
                symbol = DIM + symbol
            elif gene.strength > 0.7:
                symbol = BOLD + symbol
            lines[y][x] = f"{color}{symbol}{RESET}"

        if not lines:
            # Fallback: simple horizontal arrangement
            result = ""
            for gene in self.genome:
                color = GENE_COLORS[gene.color_idx % len(GENE_COLORS)]
                result += f"{color}{gene.symbol}{RESET}"
            return result

        # Render grid
        min_y = min(lines.keys())
        max_y = max(lines.keys())
        rendered_lines = []
        for y in range(min_y, max_y + 1):
            if y in lines:
                row = lines[y]
                min_x = min(row.keys())
                max_x = max(row.keys())
                line = ""
                for x in range(min_x, max_x + 1):
                    if x in row:
                        line += row[x]
                    else:
                        line += " "
                rendered_lines.append(line)
            else:
                rendered_lines.append("")

        return "\n".join(rendered_lines)

    def genome_string(self) -> str:
        """Show genome as colored gene sequence."""
        parts = []
        for g in self.genome:
            color = GENE_COLORS[g.color_idx % len(GENE_COLORS)]
            strength_bar = "█" * int(g.strength * 4) + "░" * (4 - int(g.strength * 4))
            parts.append(f"{color}{g.symbol}{RESET}{DIM}{strength_bar}{RESET}")
        return " ".join(parts)

    def stats(self) -> str:
        """Return creature statistics."""
        num_genes = len(self.genome)
        parts_used = len(self.body_parts_used)
        avg_strength = sum(g.strength for g in self.genome) / max(num_genes, 1)
        unique_colors = len({g.color_idx for g in self.genome})
        return (
            f"  Genes: {num_genes}  |  Parts: {parts_used}  |  "
            f"Avg Strength: {avg_strength:.2f}  |  Colors: {unique_colors}  |  "
            f"Gen: {self.generation}  |  Fitness: {self.fitness:.1f}"
        )

    def genome_summary(self) -> str:
        """Return a detailed genome summary with part breakdown."""
        if not self.genome:
            return "  (no genes)"
        parts_count = {}
        for g in self.genome:
            parts_count[g.part] = parts_count.get(g.part, 0) + 1
        summary_parts = [f"{k}:{v}" for k, v in sorted(parts_count.items())]
        avg_str = sum(g.strength for g in self.genome) / max(len(self.genome), 1)
        return f"  Parts: [{', '.join(summary_parts)}]  AvgStr: {avg_str:.2f}  Colors: {len({g.color_idx for g in self.genome})}"

    def to_dict(self) -> dict:
        """Serialize creature to a dictionary for JSON export."""
        return {
            "name": self.name,
            "genome": [g.to_dict() for g in self.genome],
            "generation": self.generation,
            "fitness": round(self.fitness, 2),
            "parent_ids": self.parent_ids,
            "id": self.id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Creature":
        """Deserialize creature from a dictionary."""
        genome = [Gene.from_dict(g) for g in d["genome"]]
        creature = cls(
            name=d["name"],
            genome=genome,
            generation=d.get("generation", 0),
            fitness=d.get("fitness", 0.0),
            parent_ids=d.get("parent_ids", []),
            id=d.get("id", ""),
        )
        if not creature.id:
            creature.id = f"CR{random.randint(1000,9999)}"
        return creature


def random_gene(part: Optional[str] = None) -> Gene:
    """Generate a random gene."""
    part = part or random.choice(BODY_PARTS)
    return Gene(
        part=part,
        symbol=random.choice(SYMBOL_POOLS[part]),
        color_idx=random.randint(0, len(GENE_COLORS) - 1),
        strength=random.uniform(0.2, 1.0),
        position=random.randint(0, 20),
    )


def random_creature(name: str = "", min_genes: int = 4, max_genes: int = 10) -> Creature:
    """Generate a random creature."""
    num_genes = random.randint(min_genes, max_genes)
    genome = []
    # Ensure at least head and torso
    genome.append(random_gene("head"))
    genome.append(random_gene("torso"))
    for _ in range(num_genes - 2):
        genome.append(random_gene())
    random.shuffle(genome)
    # Fix positions
    for i, g in enumerate(genome):
        g.position = i

    if not name:
        prefixes = ["Zor", "Kri", "Vel", "Nex", "Qua", "Pha", "Lux", "Myx", "Dra", "Fyn"]
        suffixes = ["blix", "mora", "thus", "pion", "dale", "thon", "nite", "phib", "rith", "zeen"]
        name = random.choice(prefixes) + random.choice(suffixes)

    return Creature(name=name, genome=genome, generation=0)


def crossover(parent1: Creature, parent2: Creature) -> Creature:
    """Create offspring from two parents via crossover.

    Uses uniform crossover with part-type-aware gene selection to preserve
    diversity. When selecting from a parent, tries to fill body part types
    that are underrepresented in the child genome.
    """
    child_genome = []
    min_len = min(len(parent1.genome), len(parent2.genome))
    max_len = max(len(parent1.genome), len(parent2.genome))

    for i in range(max_len):
        # Prefer the parent whose gene fills a part type we don't have yet
        if random.random() < 0.5 and i < len(parent1.genome):
            child_genome.append(copy.deepcopy(parent1.genome[i]))
        elif i < len(parent2.genome):
            child_genome.append(copy.deepcopy(parent2.genome[i]))
        else:
            child_genome.append(copy.deepcopy(parent1.genome[i]))

    # Fix positions
    for i, g in enumerate(child_genome):
        g.position = i

    prefixes = [parent1.name[:3], parent2.name[:3]]
    suffixes = [parent1.name[-3:], parent2.name[-3:]]
    name = random.choice(prefixes) + random.choice(suffixes)

    return Creature(
        name=name,
        genome=child_genome,
        generation=max(parent1.generation, parent2.generation) + 1,
        parent_ids=[parent1.id, parent2.id],
    )


def mutate(creature: Creature, rate: float = 0.3) -> Creature:
    """Mutate a creature's genome."""
    genome = copy.deepcopy(creature.genome)

    for i, gene in enumerate(genome):
        if random.random() < rate:
            mutation_type = random.choice(["symbol", "color", "strength", "part"])
            if mutation_type == "symbol":
                gene.symbol = random.choice(SYMBOL_POOLS.get(gene.part, SYMBOL_POOLS["head"]))
            elif mutation_type == "color":
                gene.color_idx = random.randint(0, len(GENE_COLORS) - 1)
            elif mutation_type == "strength":
                gene.strength = max(0.1, min(1.0, gene.strength + random.uniform(-0.3, 0.3)))
            elif mutation_type == "part":
                gene.part = random.choice(BODY_PARTS)
                gene.symbol = random.choice(SYMBOL_POOLS[gene.part])

    # Sometimes add or remove a gene
    if random.random() < 0.15 and len(genome) < 14:
        pos = random.randint(0, len(genome))
        genome.insert(pos, random_gene())
        for i, g in enumerate(genome):
            g.position = i

    if random.random() < 0.1 and len(genome) > 3:
        pos = random.randint(0, len(genome) - 1)
        genome.pop(pos)
        for i, g in enumerate(genome):
            g.position = i

    return Creature(
        name=creature.name + random.choice(["'", "`", "~", "^", "*"]),
        genome=genome,
        generation=creature.generation + 1,
        parent_ids=[creature.id],
    )


# ─── Fitness Functions ─────────────────────────────────────────────────────

def fitness_size(creature: Creature) -> float:
    """Fitness based on genome length."""
    return len(creature.genome) * 10.0

def fitness_symmetry(creature: Creature) -> float:
    """Fitness based on color symmetry."""
    if len(creature.genome) < 2:
        return 0.0
    colors = [g.color_idx for g in creature.genome]
    mid = len(colors) // 2
    left = colors[:mid]
    right = colors[mid:mid+len(left)]
    matches = sum(1 for a, b in zip(left, reversed(right)) if a == b)
    return matches * 20.0 / max(len(left), 1)

def fitness_complexity(creature: Creature) -> float:
    """Fitness based on number of unique body parts."""
    return len(creature.body_parts_used) * 15.0

def fitness_harmony(creature: Creature) -> float:
    """Fitness based on color harmony (analogous colors)."""
    if len(creature.genome) < 2:
        return 0.0
    colors = [g.color_idx for g in creature.genome]
    total_diff = 0
    count = 0
    for i in range(len(colors) - 1):
        diff = abs(colors[i] - colors[i+1])
        # Analogous colors are close together on the color wheel
        harmony = max(0, 36 - diff) / 36.0
        total_diff += harmony
        count += 1
    return (total_diff / count) * 100.0 if count else 0.0

def fitness_speed(creature: Creature) -> float:
    """Fitness for fewer genes (speed)."""
    return max(0, 150.0 - len(creature.genome) * 15.0)

def fitness_hybrid(creature: Creature) -> float:
    """Hybrid fitness blending complexity, harmony, and symmetry.

    Weighted combination: 40% complexity, 35% harmony, 25% symmetry.
    Normalized to approximate range 0-150.
    """
    comp = fitness_complexity(creature) / 120.0  # max ~120 for 8 parts
    harm = fitness_harmony(creature) / 100.0       # max ~100
    symm = fitness_symmetry(creature) / 100.0      # max ~100
    return (comp * 0.40 + harm * 0.35 + symm * 0.25) * 150.0

FITNESS_FUNCTIONS = {
    "size": fitness_size,
    "symmetry": fitness_symmetry,
    "complexity": fitness_complexity,
    "harmony": fitness_harmony,
    "speed": fitness_speed,
    "hybrid": fitness_hybrid,
}


# ─── Evolution Engine ──────────────────────────────────────────────────────

class EvolutionEngine:
    def __init__(self, population_size: int = 20, fitness_target: str = "complexity"):
        self.population_size = max(3, population_size)  # Minimum population of 3
        self.fitness_target = fitness_target
        self.generation = 0
        self.history = []  # best fitness per generation
        self.population: List[Creature] = []
        self._init_population()

    def _init_population(self):
        self.population = [random_creature() for _ in range(self.population_size)]
        self._evaluate()

    def _evaluate(self):
        fitness_fn = FITNESS_FUNCTIONS.get(self.fitness_target, fitness_complexity)
        for c in self.population:
            c.fitness = fitness_fn(c)
        self.population.sort(key=lambda c: c.fitness, reverse=True)

    def evolve(self, elitism: int = 2, tournament_size: int = 3) -> dict:
        """Evolve one generation. Returns stats."""
        self.generation += 1

        # Elitism: keep top performers
        new_pop = list(self.population[:elitism])

        # Tournament selection + crossover + mutation
        while len(new_pop) < self.population_size:
            # Select parents via tournament
            parent1 = self._tournament(tournament_size)
            parent2 = self._tournament(tournament_size)

            if random.random() < 0.7:
                child = crossover(parent1, parent2)
            else:
                child = mutate(copy.deepcopy(parent1), rate=0.5)

            child = mutate(child, rate=0.2)
            new_pop.append(child)

        self.population = new_pop[:self.population_size]
        self._evaluate()

        best = self.population[0]
        avg_fitness = sum(c.fitness for c in self.population) / len(self.population)
        worst = self.population[-1]

        self.history.append({
            "generation": self.generation,
            "best": best.fitness,
            "avg": avg_fitness,
            "worst": worst.fitness,
        })

        return {
            "best": best,
            "avg_fitness": avg_fitness,
            "worst_fitness": worst.fitness,
            "generation": self.generation,
        }

    def evolve_until(self, target_fitness: float, max_generations: int = 1000) -> dict:
        """Evolve until best fitness reaches target_fitness or max_generations hit.

        Returns the final evolve() result dict. Stops early if target is reached.
        """
        result = None
        for _ in range(max_generations):
            result = self.evolve()
            if result["best"].fitness >= target_fitness:
                return result
        # Safety: if we never entered the loop, evolve once
        if result is None:
            result = self.evolve()
        return result

    def _tournament(self, k: int = 3) -> Creature:
        """Tournament selection."""
        contestants = random.sample(self.population, min(k, len(self.population)))
        return max(contestants, key=lambda c: c.fitness)

    def get_best(self) -> Creature:
        return self.population[0]

    def get_top(self, n: int = 5) -> List[Creature]:
        return self.population[:n]

    def diversity(self) -> float:
        """Genetic diversity measure (unique gene combinations)."""
        seen = set()
        for c in self.population:
            sig = tuple((g.part, g.symbol) for g in c.genome)
            seen.add(sig)
        return len(seen) / len(self.population) if self.population else 0.0


# ─── Display Helpers ────────────────────────────────────────────────────────

def box(text: str, width: int = 60, color: str = "\033[36m") -> str:
    """Wrap text in a box."""
    lines = text.split("\n")
    top = f"{color}╔{'═' * (width - 2)}╗{RESET}"
    mid = f"{color}║{RESET}"
    bot = f"{color}╚{'═' * (width - 2)}╝{RESET}"
    result = [top]
    for line in lines:
        padded = line.ljust(width - 2)[:width - 2]
        result.append(f"{color}║{RESET} {padded} {color}║{RESET}")
    result.append(bot)
    return "\n".join(result)


def fitness_bar(value: float, max_val: float = 100.0, width: int = 30) -> str:
    """Render a progress bar for fitness."""
    ratio = min(value / max_val, 1.0) if max_val > 0 else 0.0
    filled = int(ratio * width)
    empty = width - filled
    bar = f"\033[32m{'█' * filled}{RESET}{DIM}{'░' * empty}{RESET}"
    return f"[{bar}] {value:.1f}"


def generation_chart(history: list, width: int = 50, height: int = 8) -> str:
    """Render a mini ASCII chart of fitness over generations."""
    if len(history) < 2:
        return "  (need 2+ generations to chart)"

    best_vals = [h["best"] for h in history]
    avg_vals = [h["avg"] for h in history]

    max_val = max(max(best_vals), max(avg_vals), 1)
    min_val = min(min(best_vals), min(avg_vals), 0)
    val_range = max_val - min_val if max_val != min_val else 1

    lines = []
    for row in range(height):
        y = height - 1 - row
        threshold = min_val + (y / (height - 1)) * val_range if height > 1 else max_val
        line = f"{threshold:5.0f} │"
        for i, h in enumerate(history):
            best_y = int((h["best"] - min_val) / val_range * (height - 1)) if val_range else 0
            avg_y = int((h["avg"] - min_val) / val_range * (height - 1)) if val_range else 0
            if best_y == y and avg_y == y:
                line += "\033[33m◆\033[0m"
            elif best_y == y:
                line += "\033[32m●\033[0m"
            elif avg_y == y:
                line += "\033[33m○\033[0m"
            else:
                line += " "
        lines.append(line)

    lines.append(f"      └{'─' * max(len(history), 1)} generations")

    legend = f"  \033[32m●\033[0m=Best  \033[33m○\033[0m=Avg  \033[33m◆\033[0m=Both"
    lines.append(legend)

    return "\n".join(lines)


# ─── Export / Import ─────────────────────────────────────────────────────────

def export_creature(creature: Creature, filepath: str) -> None:
    """Export a creature to a JSON file."""
    data = creature.to_dict()
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def import_creature(filepath: str) -> Creature:
    """Import a creature from a JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)
    return Creature.from_dict(data)


def export_population(engine: EvolutionEngine, filepath: str) -> None:
    """Export the entire population to a JSON file."""
    data = {
        "version": __version__,
        "fitness_target": engine.fitness_target,
        "generation": engine.generation,
        "population_size": engine.population_size,
        "history": engine.history,
        "population": [c.to_dict() for c in engine.population],
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def import_population(filepath: str) -> EvolutionEngine:
    """Import a population from a JSON file. Returns an EvolutionEngine."""
    with open(filepath, "r") as f:
        data = json.load(f)

    population = [Creature.from_dict(cd) for cd in data["population"]]
    engine = EvolutionEngine.__new__(EvolutionEngine)
    engine.population_size = data.get("population_size", len(population))
    engine.fitness_target = data.get("fitness_target", "complexity")
    engine.generation = data.get("generation", 0)
    engine.history = data.get("history", [])
    engine.population = population
    engine._evaluate()
    return engine


# ─── Main Interface ────────────────────────────────────────────────────────

class GeneSplicerApp:
    def __init__(self):
        self.engine = None
        self.running = True
        self.auto_evolve_speed = 0.3  # seconds between generations
        self.selected_parents: List[Creature] = []

    def clear(self):
        print(CLEAR, end="")

    def header(self):
        print(f"""{BOLD}\033[35m
  ╔═══════════════════════════════════════════════════════╗
  ║   🧬  GENE SPLICER — Genetic Algorithm Playground   ║
  ║       Breed. Mutate. Evolve. Create.                 ║
  ╚═══════════════════════════════════════════════════════╝{RESET}
""")

    def show_menu(self):
        print(f"""{BOLD}\033[36m  Main Menu{RESET}
  ─────────────────────────────────────────────
  \033[33m[N]\033[0m New population       \033[33m[E]\033[0m Evolve one generation
  \033[33m[A]\033[0m Auto-evolve (run)      \033[33m[G]\033[0m Evolve to fitness target
  \033[33m[T]\033[0m Set fitness target     \033[33m[V]\033[0m View population
  \033[33m[B]\033[0m View best creature     \033[33m[S]\033[0m Splice two creatures
  \033[33m[M]\033[0m Mutate a creature      \033[33m[H]\033[0m Evolution history
  \033[33m[D]\033[0m Diversity report       \033[33m[X]\033[0m Create custom creature
  \033[33m[W]\033[0m Export creature/pop    \033[33m[L]\033[0m Load creature/pop
  \033[33m[R]\033[0m Reset & start over     \033[33m[Q]\033[0m Quit
  ─────────────────────────────────────────────""")

    def show_targets(self):
        print(f"\n{BOLD}\033[36m  Fitness Targets:{RESET}")
        for i, (key, desc) in enumerate(FITNESS_TARGETS.items()):
            current = " ◀" if self.engine and self.engine.fitness_target == key else ""
            print(f"    \033[33m[{i+1}]\033[0m {key:12s} — {desc}{current}")
        print()

    def prompt(self, msg: str = "Command") -> str:
        try:
            return input(f"\033[35m  {msg}> \033[0m").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "q"

    def prompt_int(self, msg: str, default: int = 0) -> int:
        """Prompt for an integer with a default value. Returns default on error."""
        try:
            val = input(f"  {msg} [{default}]: ").strip()
            return int(val) if val else default
        except (ValueError, EOFError, KeyboardInterrupt):
            return default

    def prompt_float(self, msg: str, default: float = 0.0) -> float:
        """Prompt for a float with a default value. Returns default on error."""
        try:
            val = input(f"  {msg} [{default}]: ").strip()
            return float(val) if val else default
        except (ValueError, EOFError, KeyboardInterrupt):
            return default

    def show_creature_card(self, creature: Creature, title: str = ""):
        """Display a creature in a nice card format."""
        if title:
            print(f"\n{BOLD}\033[36m  ═══ {title} ═══{RESET}")

        render = creature.render()
        for line in render.split("\n"):
            print(f"        {line}")

        print(f"\n{BOLD}  {creature.name}{RESET} \033[2m(ID:{creature.id}){RESET}")
        print(creature.stats())
        print(creature.genome_summary())

    def cmd_new_population(self):
        self.clear()
        self.header()

        print(f"\n{BOLD}  Create New Population{RESET}")
        print(f"  Current target: \033[33m{self.engine.fitness_target if self.engine else 'complexity'}{RESET}\n")

        size = self.prompt_int("Population size", 20)
        size = max(3, size)  # Minimum 3

        self.show_targets()
        target = input("  Fitness target [complexity]: ").strip().lower()
        if target not in FITNESS_FUNCTIONS:
            # Try by number
            try:
                idx = int(target) - 1
                keys = list(FITNESS_FUNCTIONS.keys())
                if 0 <= idx < len(keys):
                    target = keys[idx]
                else:
                    target = "complexity"
            except (ValueError, IndexError):
                target = "complexity"

        self.engine = EvolutionEngine(population_size=size, fitness_target=target)
        print(f"\n  \033[32m✓ Population of {size} creatures created!{RESET}")
        print(f"  Fitness target: {BOLD}{target}{RESET}")
        self.show_creature_card(self.engine.get_best(), "Best Initial Creature")

    def cmd_evolve(self):
        if not self.engine:
            self.engine = EvolutionEngine()
        result = self.engine.evolve()
        self.clear()
        self.header()
        print(f"\n{BOLD}  Generation {result['generation']} Results{RESET}")
        print(f"  Best fitness:  {fitness_bar(result['best'].fitness)}")
        print(f"  Avg fitness:   {fitness_bar(result['avg_fitness'])}")
        print(f"  Worst fitness: {fitness_bar(result['worst_fitness'])}")
        print(f"  Diversity:     {self.engine.diversity() * 100:.0f}%")
        self.show_creature_card(result['best'], "Champion")

    def cmd_auto_evolve(self):
        if not self.engine:
            self.engine = EvolutionEngine()
        gens = self.prompt_int("How many generations", 20)
        if gens <= 0:
            gens = 20

        print(f"\n  {BOLD}Auto-evolving {gens} generations...{RESET}\n")
        for i in range(gens):
            result = self.engine.evolve()
            bar_len = 30
            filled = int((i + 1) / gens * bar_len)
            sys.stdout.write(
                f"\r  Gen {result['generation']:3d} | "
                f"Best: {result['best'].fitness:6.1f} | "
                f"Avg: {result['avg_fitness']:6.1f} | "
                f"Diversity: {self.engine.diversity()*100:3.0f}% | "
                f"[{'█' * filled}{'░' * (bar_len - filled)}]"
            )
            sys.stdout.flush()
            time.sleep(0.05)

        print(f"\n\n  {BOLD}\033[32m✓ Evolution complete!{RESET}")
        self.show_creature_card(self.engine.get_best(), "Final Champion")

    def cmd_evolve_to_target(self):
        """Evolve until a fitness threshold is reached."""
        if not self.engine:
            self.engine = EvolutionEngine()

        print(f"\n{BOLD}  Evolve to Fitness Target{RESET}")
        print(f"  Current best fitness: {self.engine.get_best().fitness:.1f}")
        target = self.prompt_float("Target fitness", self.engine.get_best().fitness + 20.0)
        max_gens = self.prompt_int("Max generations (safety limit)", 500)

        if target <= self.engine.get_best().fitness:
            print(f"  Target {target:.1f} is already reached! Current best: {self.engine.get_best().fitness:.1f}")
            return

        print(f"\n  {BOLD}Evolving until fitness ≥ {target:.1f} (max {max_gens} gens)...{RESET}\n")
        result = self.engine.evolve_until(target, max_gens)
        print(f"\n  {BOLD}\033[32m✓ Reached fitness {result['best'].fitness:.1f} at generation {result['generation']}!{RESET}")
        self.show_creature_card(result["best"], "Champion")

    def cmd_set_target(self):
        if not self.engine:
            self.engine = EvolutionEngine()
        self.show_targets()
        target = input("  Choose target: ").strip().lower()
        if target in FITNESS_FUNCTIONS:
            self.engine.fitness_target = target
            self.engine._evaluate()
            print(f"  \033[32m✓ Fitness target set to: {BOLD}{target}{RESET}")
        elif target.isdigit():
            idx = int(target) - 1
            keys = list(FITNESS_FUNCTIONS.keys())
            if 0 <= idx < len(keys):
                self.engine.fitness_target = keys[idx]
                self.engine._evaluate()
                print(f"  \033[32m✓ Fitness target set to: {BOLD}{keys[idx]}{RESET}")

    def cmd_view_population(self):
        if not self.engine:
            print("  No population. Press [N] to create one.")
            return
        self.clear()
        self.header()
        print(f"\n{BOLD}  Population — Generation {self.engine.generation}{RESET}\n")
        top = self.engine.get_top(10)
        for i, c in enumerate(top):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else f" {i+1}."
            genome_short = " ".join(f"{GENE_COLORS[g.color_idx % len(GENE_COLORS)]}{g.symbol}{RESET}" for g in c.genome[:8])
            if len(c.genome) > 8:
                genome_short += DIM + "..." + RESET
            print(f"  {medal} {BOLD}{c.name:<12}{RESET} fitness={c.fitness:6.1f}  {genome_short}")
        if len(self.engine.population) > 10:
            print(f"\n  ... and {len(self.engine.population) - 10} more creatures")

    def cmd_view_best(self):
        if not self.engine:
            print("  No population. Press [N] to create one.")
            return
        self.clear()
        self.header()
        self.show_creature_card(self.engine.get_best(), "Current Champion")
        print(f"\n  Population: {len(self.engine.population)} | Generation: {self.engine.generation}")
        print(f"  Fitness target: {BOLD}{self.engine.fitness_target}{RESET}")

    def cmd_splice(self):
        if not self.engine:
            print("  No population. Press [N] to create one.")
            return
        self.clear()
        self.header()
        top = self.engine.get_top(8)
        print(f"\n{BOLD}  Select two creatures to splice:{RESET}\n")
        for i, c in enumerate(top):
            print(f"  \033[33m[{i+1}]\033[0m {BOLD}{c.name:<12}{RESET} fitness={c.fitness:.1f}  genes={len(c.genome)}")

        try:
            p1 = int(input("\n  First parent #: ").strip()) - 1
            p2 = int(input("  Second parent #: ").strip()) - 1
        except (ValueError, EOFError):
            print("  Invalid selection.")
            return

        if 0 <= p1 < len(top) and 0 <= p2 < len(top) and p1 != p2:
            child = crossover(top[p1], top[p2])
            child = mutate(child, rate=0.3)
            child.fitness = FITNESS_FUNCTIONS[self.engine.fitness_target](child)
            self.show_creature_card(child, f"Offspring of {top[p1].name} × {top[p2].name}")
            add = input("\n  Add to population? [Y/n]: ").strip().lower()
            if add != "n":
                # Replace worst member
                self.engine.population[-1] = child
                self.engine._evaluate()
                print(f"  \033[32m✓ {child.name} added to population!{RESET}")
        else:
            print("  Invalid selection.")

    def cmd_mutate(self):
        if not self.engine:
            print("  No population. Press [N] to create one.")
            return
        self.clear()
        self.header()
        top = self.engine.get_top(5)
        print(f"\n{BOLD}  Select a creature to mutate:{RESET}\n")
        for i, c in enumerate(top):
            print(f"  \033[33m[{i+1}]\033[0m {BOLD}{c.name:<12}{RESET} fitness={c.fitness:.1f}")

        try:
            idx = int(input("\n  Creature #: ").strip()) - 1
            rate = input("  Mutation rate [0.3]: ").strip()
            rate = float(rate) if rate else 0.3
            rate = max(0.0, min(1.0, rate))  # Clamp mutation rate
        except (ValueError, EOFError):
            print("  Invalid selection.")
            return

        if 0 <= idx < len(top):
            mutant = mutate(top[idx], rate=rate)
            mutant.fitness = FITNESS_FUNCTIONS[self.engine.fitness_target](mutant)
            self.show_creature_card(mutant, f"Mutant of {top[idx].name}")
            add = input("\n  Add to population? [Y/n]: ").strip().lower()
            if add != "n":
                self.engine.population[-1] = mutant
                self.engine._evaluate()
                print(f"  \033[32m✓ {mutant.name} added to population!{RESET}")

    def cmd_history(self):
        if not self.engine or not self.engine.history:
            print("  No history yet. Evolve some generations first!")
            return
        self.clear()
        self.header()
        print(f"\n{BOLD}  Evolution History{RESET}\n")
        print(generation_chart(self.engine.history))
        print(f"\n  Generations evolved: {len(self.engine.history)}")
        if self.engine.history:
            initial = self.engine.history[0]["best"]
            current = self.engine.history[-1]["best"]
            delta = current - initial
            print(f"  Initial best: {initial:.1f} → Current best: {current:.1f} (Δ {delta:+.1f})")

    def cmd_diversity(self):
        if not self.engine:
            print("  No population. Press [N] to create one.")
            return
        self.clear()
        self.header()
        diversity = self.engine.diversity()
        print(f"\n{BOLD}  Genetic Diversity Report{RESET}\n")
        bar_len = 40
        filled = int(diversity * bar_len)
        print(f"  Diversity: [{'█' * filled}{'░' * (bar_len - filled)}] {diversity * 100:.0f}%")

        # Show unique parts
        all_parts = {}
        for c in self.engine.population:
            for g in c.genome:
                if g.part not in all_parts:
                    all_parts[g.part] = set()
                all_parts[g.part].add(g.symbol)

        print(f"\n  Gene pool by body part:")
        for part, symbols in sorted(all_parts.items()):
            print(f"    {part:10s}: {len(symbols):2d} unique symbols  ", end="")
            bar_s = int(len(symbols) / len(SYMBOL_POOLS.get(part, SYMBOL_POOLS["head"])) * 20)
            print(f"[{'█' * bar_s}{'░' * (20 - bar_s)}]")

        print(f"\n  Population size: {len(self.engine.population)}")
        print(f"  Total unique gene variants: {sum(len(s) for s in all_parts.values())}")

    def cmd_custom_creature(self):
        self.clear()
        self.header()
        print(f"\n{BOLD}  Create Custom Creature{RESET}\n")

        name = input("  Creature name: ").strip()
        if not name:
            name = "Cus" + random.choice(["tom", "ter", "pid", "tin", "tex"])

        print(f"\n  Available body parts: {', '.join(BODY_PARTS)}")
        genome = []

        while True:
            part = input(f"\n  Add body part (or 'done'): ").strip().lower()
            if part == "done" or part == "":
                break
            if part not in BODY_PARTS:
                print(f"  Unknown part. Choose from: {', '.join(BODY_PARTS)}")
                continue

            print(f"  Symbols for {part}: {' '.join(SYMBOL_POOLS[part])}")
            symbol = input(f"  Choose symbol (or 'random'): ").strip()
            if symbol == "random" or symbol not in SYMBOL_POOLS[part]:
                symbol = random.choice(SYMBOL_POOLS[part])

            strength = input(f"  Strength 0.0-1.0 [0.7]: ").strip()
            try:
                strength = float(strength)
                strength = max(0.0, min(1.0, strength))
            except ValueError:
                strength = 0.7

            color = random.randint(0, len(GENE_COLORS) - 1)

            gene = Gene(part=part, symbol=symbol, color_idx=color, strength=strength, position=len(genome))
            genome.append(gene)
            print(f"  ✓ Added {part} gene: {symbol}")

        if genome:
            creature = Creature(name=name, genome=genome, generation=0)
            if self.engine:
                creature.fitness = FITNESS_FUNCTIONS[self.engine.fitness_target](creature)
            self.show_creature_card(creature, "Custom Creature")

            if self.engine:
                add = input("\n  Add to population? [Y/n]: ").strip().lower()
                if add != "n":
                    self.engine.population[-1] = creature
                    self.engine._evaluate()
                    print(f"  \033[32m✓ {creature.name} added to population!{RESET}")

    def cmd_export(self):
        """Export creature or population to JSON."""
        if not self.engine:
            print("  No population to export. Press [N] to create one.")
            return

        print(f"\n{BOLD}  Export{RESET}")
        print(f"  \033[33m[1]\033[0m Export best creature")
        print(f"  \033[33m[2]\033[0m Export entire population")

        try:
            choice = input("  Choice: ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        filepath = input("  File path [creature.json]: ").strip()
        if not filepath:
            filepath = "creature.json"

        try:
            if choice == "2":
                export_population(self.engine, filepath)
                print(f"  \033[32m✓ Population exported to {filepath}{RESET}")
            else:
                export_creature(self.engine.get_best(), filepath)
                print(f"  \033[32m✓ Champion exported to {filepath}{RESET}")
        except (OSError, IOError) as e:
            print(f"  \033[31m✗ Error exporting: {e}{RESET}")

    def cmd_import(self):
        """Import a creature or population from JSON."""
        filepath = input("  File path to import: ").strip()
        if not filepath:
            print("  No file specified.")
            return

        try:
            with open(filepath, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            print(f"  \033[31m✗ Error importing: {e}{RESET}")
            return

        if "population" in data:
            # It's a population export
            try:
                engine = import_population(filepath)
                self.engine = engine
                print(f"  \033[32m✓ Population loaded from {filepath}{RESET}")
                print(f"  Generation: {engine.generation} | Target: {engine.fitness_target}")
            except Exception as e:
                print(f"  \033[31m✗ Error loading population: {e}{RESET}")
        else:
            # Single creature
            try:
                creature = import_creature(filepath)
                if not self.engine:
                    self.engine = EvolutionEngine()
                creature.fitness = FITNESS_FUNCTIONS[self.engine.fitness_target](creature)
                self.show_creature_card(creature, "Imported Creature")
                add = input("\n  Add to population? [Y/n]: ").strip().lower()
                if add != "n":
                    self.engine.population[-1] = creature
                    self.engine._evaluate()
                    print(f"  \033[32m✓ {creature.name} added to population!{RESET}")
            except Exception as e:
                print(f"  \033[31m✗ Error loading creature: {e}{RESET}")

    def run(self):
        """Main loop."""
        self.clear()
        self.header()
        print(f"{BOLD}  Welcome to Gene Splicer!{RESET}")
        print(f"  Breed, mutate, and evolve ASCII creatures.\n")

        if not self.engine:
            self.engine = EvolutionEngine()

        while self.running:
            self.show_menu()
            cmd = self.prompt()

            if cmd == "q":
                print(f"\n  {BOLD}Goodbye! Your creatures will be missed. 🧬{RESET}\n")
                self.running = False
            elif cmd == "n":
                self.cmd_new_population()
            elif cmd == "e":
                self.cmd_evolve()
            elif cmd == "a":
                self.cmd_auto_evolve()
            elif cmd == "g":
                self.cmd_evolve_to_target()
            elif cmd == "t":
                self.cmd_set_target()
            elif cmd == "v":
                self.cmd_view_population()
            elif cmd == "b":
                self.cmd_view_best()
            elif cmd == "s":
                self.cmd_splice()
            elif cmd == "m":
                self.cmd_mutate()
            elif cmd == "h":
                self.cmd_history()
            elif cmd == "d":
                self.cmd_diversity()
            elif cmd == "x":
                self.cmd_custom_creature()
            elif cmd == "w":
                self.cmd_export()
            elif cmd == "l":
                self.cmd_import()
            elif cmd == "r":
                self.engine = EvolutionEngine(
                    population_size=self.engine.population_size if self.engine else 20,
                    fitness_target=self.engine.fitness_target if self.engine else "complexity"
                )
                print(f"  \033[32m✓ Population reset!{RESET}")
            else:
                print(f"  Unknown command: {cmd}")

            if self.running:
                input(f"\n  {DIM}Press Enter to continue...{RESET}")


# ─── Demo Mode (non-interactive) ───────────────────────────────────────────

def run_demo(targets=None, generations=25, population_size=30):
    """Run a non-interactive demo showing evolution in action.

    Args:
        targets: List of fitness target names. Defaults to ["complexity", "harmony", "size"].
        generations: Number of generations to evolve per target.
        population_size: Size of the population.
    """
    if targets is None:
        targets = ["complexity", "harmony", "size"]

    print(CLEAR)
    print(f"{BOLD}\033[35m  ╔═══════════════════════════════════════════════════════╗")
    print(f"  ║   🧬  GENE SPLICER — Auto Demo                       ║")
    print(f"  ║       Watch creatures evolve!                          ║")
    print(f"  ╚═══════════════════════════════════════════════════════╝{RESET}\n")

    for target in targets:
        if target not in FITNESS_FUNCTIONS:
            print(f"  Unknown target: {target}, skipping.")
            continue

        engine = EvolutionEngine(population_size=population_size, fitness_target=target)

        print(f"\n{BOLD}\033[36m  ═══ Evolving for: {target.upper()} ═══{RESET}\n")
        print(f"  Starting population of {engine.population_size} creatures...")

        # Show initial best
        best = engine.get_best()
        print(f"\n  {DIM}Initial best creature:{RESET}")
        render = best.render()
        for line in render.split("\n"):
            print(f"    {line}")
        print(f"    {BOLD}{best.name}{RESET} fitness={best.fitness:.1f}")

        # Evolve
        for gen in range(generations):
            result = engine.evolve()
            bar_len = 25
            filled = int((gen + 1) / generations * bar_len)
            sys.stdout.write(
                f"\r  Gen {result['generation']:2d} | "
                f"Best: {result['best'].fitness:6.1f} | "
                f"Avg: {result['avg_fitness']:6.1f} | "
                f"Diversity: {engine.diversity()*100:3.0f}% | "
                f"[{'█' * filled}{'░' * (bar_len - filled)}]"
            )
            sys.stdout.flush()
            time.sleep(0.1)

        # Show final best
        best = engine.get_best()
        print(f"\n\n  {BOLD}\033[32m✓ Evolution complete!{RESET}")
        print(f"\n  {BOLD}Final champion:{RESET}")
        render = best.render()
        for line in render.split("\n"):
            print(f"    {line}")
        print(f"    {BOLD}{best.name}{RESET} {best.stats()}")
        print(f"    Genome: {best.genome_string()}")
        print()

        time.sleep(1)

    print(f"\n{BOLD}\033[35m  ═══ Demo Complete! ═══{RESET}")
    print(f"  Run with --interactive to take control of evolution!")
    print(f"  Usage: python gene_splicer.py --interactive{RESET}\n")


# ─── CLI Entry Point ────────────────────────────────────────────────────────

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Gene Splicer — breed ASCII creatures through genetic algorithms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python gene_splicer.py                       Run demo (non-interactive)
  python gene_splicer.py -i                    Interactive mode
  python gene_splicer.py -i -t harmony         Interactive, evolve for harmony
  python gene_splicer.py --target size -g 50    Demo with size target, 50 gens
  python gene_splicer.py --export champ.json    Export best creature
  python gene_splicer.py --import champ.json    Import a creature
  python gene_splicer.py --version              Show version
"""
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('-i', '--interactive', action='store_true',
                       help='Run in interactive mode (default: demo mode)')
    parser.add_argument('-t', '--target', type=str, default=None,
                       choices=list(FITNESS_TARGETS.keys()),
                       help='Fitness target (default: complexity)')
    parser.add_argument('-g', '--generations', type=int, default=25,
                       help='Number of generations for demo mode (default: 25)')
    parser.add_argument('-p', '--population', type=int, default=30,
                       help='Population size for demo mode (default: 30)')
    parser.add_argument('--export', type=str, default=None, metavar='FILE',
                       help='Export best creature from demo to JSON file')
    parser.add_argument('--import', dest='import_file', type=str, default=None, metavar='FILE',
                       help='Import a creature from JSON file (interactive mode)')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.interactive:
        app = GeneSplicerApp()
        # Set initial target if specified
        if args.target:
            app.engine = EvolutionEngine(fitness_target=args.target)
        # Import creature if specified
        if args.import_file:
            try:
                creature = import_creature(args.import_file)
                print(f"  Imported creature: {creature.name}")
                if not app.engine:
                    app.engine = EvolutionEngine(fitness_target=args.target or "complexity")
                creature.fitness = FITNESS_FUNCTIONS[app.engine.fitness_target](creature)
                app.engine.population[-1] = creature
                app.engine._evaluate()
                print(f"  Added to population. Fitness: {creature.fitness:.1f}")
            except Exception as e:
                print(f"  Error importing: {e}")
        app.run()
    else:
        # Demo mode
        targets = [args.target] if args.target else None
        engine_ref = [None]  # Mutable reference for export
        run_demo(targets=targets, generations=args.generations, population_size=args.population)

        # If --export is specified, create a temporary engine and export
        if args.export:
            engine = EvolutionEngine(population_size=args.population, fitness_target=args.target or "complexity")
            for _ in range(args.generations):
                engine.evolve()
            try:
                export_creature(engine.get_best(), args.export)
                print(f"  Best creature exported to {args.export}")
            except (OSError, IOError) as e:
                print(f"  Error exporting: {e}", file=sys.stderr)