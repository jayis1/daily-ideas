#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from treasure_map import MapConfig, TreasureMap

# Check peak and volcano generation
for s in range(1, 50):
    cfg = MapConfig(width=50, height=25, seed=s)
    tmap = TreasureMap(cfg)
    peak_cells = sum(1 for y in range(25) for x in range(50) if tmap.terrain[y][x] == 'peak')
    volc_cells = sum(1 for y in range(25) for x in range(50) if tmap.terrain[y][x] in ('volcano', 'lava'))
    if peak_cells > 0 or volc_cells > 0:
        print(f"Seed {s}: {peak_cells} peaks, {volc_cells} volcano/lava")
    if s <= 5:
        print(f"  Seed {s} check: peaks={peak_cells}, volc={volc_cells}")

# Check stats rounding
cfg = MapConfig(width=40, height=18, seed=42)
tmap = TreasureMap(cfg)
stats = tmap.get_terrain_stats()
total = sum(stats.values())
print(f"\nStats total: {total}%")
print(f"Stats: {stats}")