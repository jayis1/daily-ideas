#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from treasure_map import MapConfig, TreasureMap

# Check for mountain/peak cells across seeds on default 72x34
for s in range(1, 20):
    cfg = MapConfig(width=72, height=34, seed=s)
    tmap = TreasureMap(cfg)
    counts = {}
    for y in range(34):
        for x in range(72):
            t_type = tmap.terrain[y][x]
            counts[t_type] = counts.get(t_type, 0) + 1
    mt = counts.get('mountain', 0)
    pk = counts.get('peak', 0)
    if mt > 0 or pk > 0:
        print(f"Seed {s}: mountain={mt}, peak={pk}, terrain={counts}")