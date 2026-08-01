#!/usr/bin/env python3
"""Investigate remaining food bug and other edge cases."""
import sys
sys.path.insert(0, '.')
from ant_colony import AntColonySimulation, Ant, run_headless
import random

print("=== Investigating Remaining Food Bug ===")

# Bug: food_sources have remaining amount but food_grid is empty
# This means food was picked up from grid but food_sources weren't updated
sim = AntColonySimulation(80, 24, num_ants=200, num_walls=0, seed=42)
for i in range(10000):
    sim.step()
    if sim.food_collected >= sim.total_food:
        break

remaining_grid = sum(sum(row) for row in sim.food_grid)
remaining_sources = sum(f.amount for f in sim.food_sources)
print(f'food_collected={sim.food_collected}, total_food={sim.total_food}')
print(f'Remaining in food_grid: {remaining_grid}')
print(f'Remaining in food_sources: {remaining_sources}')
print(f'Food sources still active: {len(sim.food_sources)}')

# The food_sources are only removed when f.amount <= 0
# But the _update_ant code decrements food_grid, not food_source.amount
# So food_source.amount never gets decremented!
# This is a BUG: food_source.amount should be decremented when food is picked up

# Let me verify
sim2 = AntColonySimulation(80, 24, num_ants=60, seed=42)
print(f'\nInitial food_source amounts: {[f.amount for f in sim2.food_sources]}')
print(f'Initial total_food: {sim2.total_food}')

# Run a few steps
for _ in range(100):
    sim2.step()

print(f'After 100 ticks:')
print(f'  food_source amounts: {[f.amount for f in sim2.food_sources]}')
print(f'  food_collected: {sim2.food_collected}')

# food_source.amount never changes! It's always the initial amount
# This means food_sources never get removed, and the "sources_remaining" stat is always wrong

# Bug: In _update_ant, when food is picked up:
#   self.food_grid[ant.y][ant.x] -= 1
# But food_source.amount is never decremented!
# And food_sources are filtered by amount > 0:
#   self.food_sources = [f for f in self.food_sources if f.amount > 0]
# So food_sources are NEVER removed because their amount never goes to 0

print("\n=== Checking food_source.amount tracking ===")
sim3 = AntColonySimulation(80, 24, num_ants=200, seed=42)
initial_amounts = [f.amount for f in sim3.food_sources]
print(f'Initial amounts: {initial_amounts}')

for _ in range(5000):
    sim3.step()

final_amounts = [f.amount for f in sim3.food_sources]
print(f'After 5000 ticks amounts: {final_amounts}')
print(f'food_collected: {sim3.food_collected}')
# If amounts haven't changed, it confirms the bug

# Also check: the stat 'sources_remaining' should decrease over time
stats_early = None
for i in range(1000):
    sim3.step()
    if i == 100:
        stats_early = sim3.get_stats()

stats_late = sim3.get_stats()
print(f'\nSources remaining at tick 100: {stats_early["sources_remaining"]}')
print(f'Sources remaining at tick {sim3.tick}: {stats_late["sources_remaining"]}')
print(f'Sources remaining should decrease as food is collected')

print("\n=== Investigation Complete ===")