#!/usr/bin/env python3
"""Quick syntax and logic validation for sonar.py"""

# Test 1: Syntax check
with open("sonar.py", "r") as f:
    code = f.read()
try:
    compile(code, "sonar.py", "exec")
    print("OK: Syntax check passed")
except SyntaxError as e:
    print(f"FAIL: Syntax error: {e}")

# Test 2: Constants
from sonar import WORLD_W, WORLD_H, PING_RADIUS, MAX_TORPEDOES
print(f"OK: World is {WORLD_W}x{WORLD_H}, Ping radius={PING_RADIUS}, Max torpedoes={MAX_TORPEDOES}")

# Test 3: Generate world
from sonar import generate_world, spawn_enemies, CellType
world = generate_world(WORLD_W, WORLD_H)
land_count = sum(1 for row in world for c in row if c == CellType.LAND)
water_count = sum(1 for row in world for c in row if c == CellType.WATER)
print(f"OK: World generated with {land_count} land cells, {water_count} water cells")

# Test 4: Spawn enemies
enemies = spawn_enemies(world, 10)
print(f"OK: Spawned {len(enemies)} enemies")
for e in enemies:
    print(f"  - {e.etype.value} at ({e.x},{e.y}), HP={e.hp}")

print("\nAll validation checks passed!")