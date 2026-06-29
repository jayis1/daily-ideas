#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from treasure_map import MapConfig, TreasureMap

# Try easy difficulty which has more land
for s in range(1, 100):
    cfg = MapConfig(width=72, height=34, seed=s, difficulty="easy")
    tmap = TreasureMap(cfg)
    for y in range(34):
        for x in range(72):
            if tmap.terrain[y][x] in ("volcano", "lava", "peak", "mountain", "dense_forest"):
                print(f"Easy seed {s}: found elevated terrain")
                print(f"  volcano={sum(1 for y2 in range(34) for x2 in range(72) if tmap.terrain[y2][x2]=='volcano')}")
                print(f"  lava={sum(1 for y2 in range(34) for x2 in range(72) if tmap.terrain[y2][x2]=='lava')}")
                import sys; sys.exit(0)
print("No elevated terrain found in 99 easy seeds")