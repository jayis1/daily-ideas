#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from treasure_map import MapConfig, TreasureMap

# Check larger maps for peaks
for s in range(1, 20):
    cfg = MapConfig(width=72, height=34, seed=s)
    tmap = TreasureMap(cfg)
    terrain_counts = {}
    for y in range(34):
        for x in range(72):
            t = tmap.terrain[y][x]
            terrain_counts[t] = terrain_counts.get(t, 0) + 1
    if 'peak' in terrain_counts or 'mountain' in terrain_counts:
        print(f"Seed {s}: {terrain_counts}")
        break
    
# Try easy difficulty which should have more land
for s in range(1, 10):
    cfg = MapConfig(width=72, height=34, seed=s, difficulty="easy")
    tmap = TreasureMap(cfg)
    terrain_counts = {}
    for y in range(34):
        for x in range(72):
            t = tmap.terrain[y][x]
            terrain_counts[t] = terrain_counts.get(t, 0) + 1
    print(f"Easy seed {s}: {terrain_counts}")