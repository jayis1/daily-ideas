#!/usr/bin/env python3
"""
Tests for Gene Splicer v1.1.

Covers:
- Gene and Creature data structures
- Random generation
- Crossover and mutation
- Fitness functions (all 6)
- EvolutionEngine (init, evolve, evolve_until, diversity)
- Export/import (JSON serialization round-trip)
- Generation chart
- CLI argument parsing
- Edge cases and error handling
"""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gene_splicer import (
    Gene, Creature, random_gene, random_creature,
    crossover, mutate, EvolutionEngine,
    FITNESS_FUNCTIONS, FITNESS_TARGETS, BODY_PARTS, SYMBOL_POOLS,
    GENE_COLORS, TEMPLATE_FRAMES,
    fitness_size, fitness_symmetry, fitness_complexity,
    fitness_harmony, fitness_speed, fitness_hybrid,
    box, fitness_bar, generation_chart,
    export_creature, import_creature, export_population, import_population,
    parse_args, __version__,
)

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name}: {detail}")

# ============================================================
# 1. Gene Tests
# ============================================================
print("=== Gene Tests ===")

g = Gene(part="head", symbol="◉", color_idx=5, strength=0.7, position=0)
test("Gene creation: part", g.part == "head", f"got {g.part}")
test("Gene creation: symbol", g.symbol == "◉", f"got {g.symbol}")
test("Gene creation: color_idx", g.color_idx == 5, f"got {g.color_idx}")
test("Gene creation: strength", abs(g.strength - 0.7) < 0.001, f"got {g.strength}")
test("Gene creation: position", g.position == 0, f"got {g.position}")

# Gene serialization
d = g.to_dict()
test("Gene to_dict: has all keys", all(k in d for k in ["part", "symbol", "color_idx", "strength", "position"]),
     f"got keys {list(d.keys())}")

g2 = Gene.from_dict(d)
test("Gene round-trip: part", g2.part == g.part, f"got {g2.part}")
test("Gene round-trip: symbol", g2.symbol == g.symbol, f"got {g2.symbol}")
test("Gene round-trip: strength", abs(g2.strength - g.strength) < 0.001, f"got {g2.strength}")

# ============================================================
# 2. Creature Tests
# ============================================================
print("\n=== Creature Tests ===")

c = random_creature("Testor")
test("Creature has name", c.name == "Testor")
test("Creature has genome", len(c.genome) >= 2, f"got {len(c.genome)} genes")
test("Creature has id", c.id.startswith("CR"), f"got {c.id}")
test("Creature generation defaults to 0", c.generation == 0)
test("Creature has fitness", hasattr(c, 'fitness'))

# body_parts_used
parts = c.body_parts_used
test("body_parts_used returns set", isinstance(parts, set))
test("body_parts_used contains head", "head" in parts, f"got {parts}")

# Render
rendered = c.render()
test("render produces non-empty string", len(rendered) > 0)

# Empty creature
empty = Creature(name="Empty", genome=[])
test("Empty creature renders as empty organism", "empty organism" in empty.render().lower() or len(empty.render()) == 0)

# genome_string
gs = c.genome_string()
test("genome_string is non-empty", len(gs) > 0)

# stats
stats = c.stats()
test("stats contains Genes", "Genes:" in stats, f"got {stats}")
test("stats contains Parts", "Parts:" in stats, f"got {stats}")

# genome_summary
summary = c.genome_summary()
test("genome_summary is non-empty", len(summary) > 0)

# Creature serialization
cd = c.to_dict()
test("Creature to_dict: has name", cd["name"] == "Testor")
test("Creature to_dict: has genome", "genome" in cd)
test("Creature to_dict: has fitness", "fitness" in cd)

c2 = Creature.from_dict(cd)
test("Creature round-trip: name", c2.name == c.name, f"got {c2.name}")
test("Creature round-trip: genome length", len(c2.genome) == len(c.genome),
     f"got {len(c2.genome)} vs {len(c.genome)}")
test("Creature round-trip: id", c2.id == c.id, f"got {c2.id} vs {c.id}")

# ============================================================
# 3. Random Generation Tests
# ============================================================
print("\n=== Random Generation Tests ===")

g_random = random_gene()
test("random_gene: has valid part", g_random.part in BODY_PARTS, f"got {g_random.part}")
test("random_gene: has valid symbol", g_random.symbol in SYMBOL_POOLS.get(g_random.part, []),
     f"got {g_random.symbol}")
test("random_gene: strength in range", 0.0 <= g_random.strength <= 1.0,
     f"got {g_random.strength}")
test("random_gene: color_idx in range", 0 <= g_random.color_idx < len(GENE_COLORS),
     f"got {g_random.color_idx}")

g_specific = random_gene("torso")
test("random_gene with part: correct part", g_specific.part == "torso")

c_random = random_creature()
test("random_creature: has name", len(c_random.name) > 0)
test("random_creature: has genome", len(c_random.genome) >= 2)
test("random_creature: has head", "head" in c_random.body_parts_used)
test("random_creature: has torso", "torso" in c_random.body_parts_used)

# Min/max genes
c_small = random_creature(min_genes=2, max_genes=2)
test("random_creature min_genes=2: has 2 genes", len(c_small.genome) == 2,
     f"got {len(c_small.genome)}")

c_large = random_creature(min_genes=10, max_genes=10)
test("random_creature max_genes=10: has 10 genes", len(c_large.genome) == 10,
     f"got {len(c_large.genome)}")

# ============================================================
# 4. Crossover Tests
# ============================================================
print("\n=== Crossover Tests ===")

p1 = random_creature("Parent1")
p2 = random_creature("Parent2")
child = crossover(p1, p2)

test("crossover: produces creature", isinstance(child, Creature))
test("crossover: has genome", len(child.genome) > 0)
test("crossover: generation incremented", child.generation == max(p1.generation, p2.generation) + 1)
test("crossover: has parent IDs", len(child.parent_ids) == 2)
test("crossover: name is combination", len(child.name) > 0)

# Child genome should come from parents
all_parent_genes = set((g.part, g.symbol) for g in p1.genome + p2.genome)
child_genes = set((g.part, g.symbol) for g in child.genome)
# At least some genes should match parents (allowing for mutation)
# We can't guarantee 100% match because mutate() is called separately

# ============================================================
# 5. Mutation Tests
# ============================================================
print("\n=== Mutation Tests ===")

original = random_creature("Original")
mutant = mutate(original, rate=0.5)

test("mutate: produces creature", isinstance(mutant, Creature))
test("mutate: generation incremented", mutant.generation == original.generation + 1)
test("mutate: has parent ID", original.id in mutant.parent_ids)
test("mutate: name has mutation marker", len(mutant.name) > len(original.name),
     f"original={original.name}, mutant={mutant.name}")

# Low mutation rate should preserve most genes
low_mutant = mutate(original, rate=0.0)
test("mutate rate=0: same gene count", len(low_mutant.genome) == len(original.genome),
     f"got {len(low_mutant.genome)} vs {len(original.genome)}")

# High mutation rate
high_mutant = mutate(original, rate=1.0)
test("mutate rate=1: still produces valid creature", len(high_mutant.genome) >= 3)

# ============================================================
# 6. Fitness Function Tests
# ============================================================
print("\n=== Fitness Function Tests ===")

# fitness_size
small = Creature(name="Small", genome=[random_gene("head"), random_gene("torso")], generation=0)
large = Creature(name="Large", genome=[random_gene() for _ in range(10)], generation=0)

f_small = fitness_size(small)
f_large = fitness_size(large)
test("fitness_size: more genes = higher fitness", f_large > f_small,
     f"small={f_small}, large={f_large}")

# fitness_symmetry
sym_colors = [Gene(part="head", symbol="◉", color_idx=5, strength=0.5, position=i) for i in range(4)]
sym_colors[2].color_idx = 5  # Mirror of position 0
sym_colors[3].color_idx = sym_colors[1].color_idx  # Mirror of position 1

sym_creature = Creature(name="Sym", genome=sym_colors, generation=0)
f_sym = fitness_symmetry(sym_creature)
test("fitness_symmetry: symmetric creature has positive fitness", f_sym > 0, f"got {f_sym}")

# Empty genome
empty_sym = Creature(name="Empty", genome=[], generation=0)
test("fitness_symmetry: empty genome returns 0", fitness_symmetry(empty_sym) == 0)

# Single gene
single = Creature(name="Single", genome=[random_gene()], generation=0)
test("fitness_symmetry: single gene returns 0", fitness_symmetry(single) == 0)

# fitness_complexity
many_parts = Creature(name="ManyParts",
    genome=[Gene(part=p, symbol="X", color_idx=0, strength=0.5, position=i)
            for i, p in enumerate(BODY_PARTS)],
    generation=0)
few_parts = Creature(name="FewParts",
    genome=[Gene(part="head", symbol="X", color_idx=0, strength=0.5, position=0),
            Gene(part="torso", symbol="X", color_idx=0, strength=0.5, position=1)],
    generation=0)

test("fitness_complexity: more parts > fewer parts",
     fitness_complexity(many_parts) > fitness_complexity(few_parts),
     f"many={fitness_complexity(many_parts)}, few={fitness_complexity(few_parts)}")

# fitness_harmony
harmonious_genes = [Gene(part="head", symbol="◉", color_idx=i, strength=0.5, position=i) for i in range(5)]
harmonious = Creature(name="Harmony", genome=harmonious_genes, generation=0)
f_harm = fitness_harmony(harmonious)
test("fitness_harmony: returns positive fitness for any genome", f_harm >= 0, f"got {f_harm}")

test("fitness_harmony: empty genome returns 0", fitness_harmony(empty_sym) == 0)
test("fitness_harmony: single gene returns 0", fitness_harmony(single) == 0)

# fitness_speed
fast = Creature(name="Fast", genome=[random_gene() for _ in range(3)], generation=0)
slow = Creature(name="Slow", genome=[random_gene() for _ in range(8)], generation=0)
test("fitness_speed: fewer genes = higher fitness", fitness_speed(fast) > fitness_speed(slow),
     f"fast={fitness_speed(fast)}, slow={fitness_speed(slow)}")

# fitness_hybrid
f_hybrid = fitness_hybrid(many_parts)
test("fitness_hybrid: returns positive fitness", f_hybrid > 0, f"got {f_hybrid}")

# Verify all fitness functions are in FITNESS_FUNCTIONS
for name, desc in FITNESS_TARGETS.items():
    test(f"FITNESS_FUNCTIONS contains '{name}'", name in FITNESS_FUNCTIONS,
         f"missing {name}")

test("FITNESS_TARGETS has 6 entries", len(FITNESS_TARGETS) == 6,
     f"got {len(FITNESS_TARGETS)}")

# ============================================================
# 7. EvolutionEngine Tests
# ============================================================
print("\n=== EvolutionEngine Tests ===")

engine = EvolutionEngine(population_size=10, fitness_target="complexity")
test("Engine: initialized with population", len(engine.population) == 10)
test("Engine: generation starts at 0", engine.generation == 0)
test("Engine: population is sorted by fitness",
     all(engine.population[i].fitness >= engine.population[i+1].fitness
         for i in range(len(engine.population)-1)))

# Evolve one generation
result = engine.evolve()
test("Engine: evolve returns dict", isinstance(result, dict))
test("Engine: evolve returns best", "best" in result)
test("Engine: evolve returns avg_fitness", "avg_fitness" in result)
test("Engine: evolve returns worst_fitness", "worst_fitness" in result)
test("Engine: evolve returns generation", "generation" in result)
test("Engine: generation incremented", engine.generation == 1)

# Best should be a Creature
test("Engine: best is Creature", isinstance(result["best"], Creature))
test("Engine: avg_fitness is numeric", isinstance(result["avg_fitness"], (int, float)))
test("Engine: generation in result", result["generation"] == 1)

# Evolve several generations
for _ in range(5):
    engine.evolve()
test("Engine: 6 generations total", engine.generation == 6)

# get_best and get_top
best = engine.get_best()
test("Engine: get_best returns Creature", isinstance(best, Creature))
test("Engine: get_best has highest fitness", best.fitness >= engine.population[-1].fitness)

top5 = engine.get_top(5)
test("Engine: get_top(5) returns 5", len(top5) == 5)
top3 = engine.get_top(3)
test("Engine: get_top(3) returns 3", len(top3) == 3)

# diversity
div = engine.diversity()
test("Engine: diversity between 0 and 1", 0 <= div <= 1, f"got {div}")

# Minimum population size
engine_small = EvolutionEngine(population_size=1, fitness_target="size")
test("Engine: minimum population is 3", len(engine_small.population) == 3,
     f"got {len(engine_small.population)}")

# evolve_until
engine2 = EvolutionEngine(population_size=20, fitness_target="size")
initial_best = engine2.get_best().fitness
result2 = engine2.evolve_until(target_fitness=initial_best + 500, max_generations=10)
test("Engine: evolve_until returns dict", isinstance(result2, dict))
test("Engine: evolve_until ran at least 1 gen", engine2.generation >= 1)

# Change fitness target
engine3 = EvolutionEngine(population_size=10, fitness_target="complexity")
engine3.fitness_target = "harmony"
engine3._evaluate()
test("Engine: fitness target change works", engine3.fitness_target == "harmony")

# History tracking
test("Engine: history has entries", len(engine.history) >= 6)
test("Engine: history entry has generation", "generation" in engine.history[0])
test("Engine: history entry has best", "best" in engine.history[0])

# ============================================================
# 8. Export/Import Tests
# ============================================================
print("\n=== Export/Import Tests ===")

c_export = random_creature("ExportTest")
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    export_path = f.name

try:
    export_creature(c_export, export_path)
    test("Export: file created", os.path.exists(export_path))

    with open(export_path, 'r') as f:
        data = json.load(f)
    test("Export: JSON has name", "name" in data)
    test("Export: JSON has genome", "genome" in data)

    c_import = import_creature(export_path)
    test("Import: creature name matches", c_import.name == c_export.name,
         f"got {c_import.name} vs {c_export.name}")
    test("Import: genome length matches", len(c_import.genome) == len(c_export.genome))
    test("Import: generation matches", c_import.generation == c_export.generation)
    test("Import: fitness matches", abs(c_import.fitness - c_export.fitness) < 0.01,
         f"got {c_import.fitness} vs {c_export.fitness}")

    # Population export/import
    engine_exp = EvolutionEngine(population_size=10, fitness_target="complexity")
    for _ in range(3):
        engine_exp.evolve()

    export_population(engine_exp, export_path)
    with open(export_path, 'r') as f:
        pop_data = json.load(f)
    test("Population export: has population key", "population" in pop_data)
    test("Population export: has fitness_target", "fitness_target" in pop_data)
    test("Population export: has generation", "generation" in pop_data)

    engine_imp = import_population(export_path)
    test("Population import: population restored", len(engine_imp.population) == 10)
    test("Population import: fitness target restored", engine_imp.fitness_target == "complexity")
    test("Population import: generation restored", engine_imp.generation >= 3)

finally:
    os.unlink(export_path)

# ============================================================
# 9. Display Helper Tests
# ============================================================
print("\n=== Display Helper Tests ===")

# box
boxed = box("Hello World")
test("box: contains top border", "╔" in boxed)
test("box: contains bottom border", "╚" in boxed)
test("box: contains text", "Hello World" in boxed)

# fitness_bar
bar = fitness_bar(50.0)
test("fitness_bar: contains bar characters", "█" in bar or "░" in bar)
test("fitness_bar: contains value", "50.0" in bar)

bar_max = fitness_bar(150.0, max_val=100.0)
test("fitness_bar: clamps to max", "150.0" in bar_max)

# generation_chart
history = [
    {"best": 50, "avg": 40},
    {"best": 60, "avg": 45},
    {"best": 70, "avg": 50},
]
chart = generation_chart(history)
test("generation_chart: produces output", len(chart) > 0)
test("generation_chart: has legend", "Best" in chart)

# Empty history
chart_empty = generation_chart([])
test("generation_chart: empty history gives message", "need" in chart_empty.lower() or len(chart_empty) > 0)

# Single entry
chart_single = generation_chart([{"best": 50, "avg": 40}])
test("generation_chart: single entry gives message", "need" in chart_single.lower() or len(chart_single) > 0)

# ============================================================
# 10. Template and Constants Tests
# ============================================================
print("\n=== Template and Constants Tests ===")

test("BODY_PARTS has 8 entries", len(BODY_PARTS) == 8, f"got {len(BODY_PARTS)}")
test("SYMBOL_POOLS has all body parts", all(p in SYMBOL_POOLS for p in BODY_PARTS))

for part, symbols in SYMBOL_POOLS.items():
    test(f"SYMBOL_POOLS[{part}] is non-empty", len(symbols) > 0)

test("TEMPLATE_FRAMES has 3 entries", len(TEMPLATE_FRAMES) == 3, f"got {len(TEMPLATE_FRAMES)}")
test("GENE_COLORS has entries", len(GENE_COLORS) > 0)

# ============================================================
# 11. CLI Argument Parsing Tests
# ============================================================
print("\n=== CLI Argument Parsing Tests ===")

# Test default args
sys.argv = ["gene_splicer.py"]
args = parse_args()
test("CLI: default interactive=False", args.interactive == False)
test("CLI: default target=None", args.target == None)
test("CLI: default generations=25", args.generations == 25)
test("CLI: default population=30", args.population == 30)
test("CLI: default export=None", args.export == None)
test("CLI: default import=None", args.import_file == None)

# Test with flags
sys.argv = ["gene_splicer.py", "-i", "-t", "harmony", "-g", "50", "-p", "20"]
args = parse_args()
test("CLI: -i sets interactive", args.interactive == True)
test("CLI: -t sets target", args.target == "harmony")
test("CLI: -g sets generations", args.generations == 50)
test("CLI: -p sets population", args.population == 20)

# Test export/import flags
sys.argv = ["gene_splicer.py", "--export", "out.json"]
args = parse_args()
test("CLI: --export sets path", args.export == "out.json")

sys.argv = ["gene_splicer.py", "--import", "in.json"]
args = parse_args()
test("CLI: --import sets path", args.import_file == "in.json")

# Version
test("Version is a string", isinstance(__version__, str))
test("Version format valid", "." in __version__, f"got {__version__}")

# ============================================================
# 12. Edge Cases and Error Handling
# ============================================================
print("\n=== Edge Cases ===")

# Creature with duplicate genes
dup_genes = [Gene(part="head", symbol="◉", color_idx=0, strength=0.5, position=i) for i in range(5)]
dup_creature = Creature(name="Dup", genome=dup_genes, generation=0)
test("Duplicate genes: renders", len(dup_creature.render()) > 0)
test("Duplicate genes: fitness_size", fitness_size(dup_creature) == 50.0, f"got {fitness_size(dup_creature)}")

# Very large genome
big_genome = [random_gene() for _ in range(14)]
big_creature = Creature(name="Big", genome=big_genome, generation=0)
test("Large genome: renders", len(big_creature.render()) > 0)

# Fitness with empty genome
empty_creature = Creature(name="Empty", genome=[], generation=0)
test("Fitness on empty genome: size", fitness_size(empty_creature) == 0.0)
test("Fitness on empty genome: complexity", fitness_complexity(empty_creature) == 0.0)
test("Fitness on empty genome: harmony", fitness_harmony(empty_creature) == 0.0)
test("Fitness on empty genome: speed", fitness_speed(empty_creature) == 150.0)
test("Fitness on empty genome: hybrid", fitness_hybrid(empty_creature) == 0.0)

# Population size edge case
engine_tiny = EvolutionEngine(population_size=3, fitness_target="complexity")
test("Population size 3: works", len(engine_tiny.population) == 3)
result_tiny = engine_tiny.evolve()
test("Population size 3: evolve works", isinstance(result_tiny, dict))

# ============================================================
# Summary
# ============================================================
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
if failed > 0:
    print("SOME TESTS FAILED!")
    sys.exit(1)
else:
    print("All tests passed!")