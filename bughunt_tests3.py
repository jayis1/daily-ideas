#!/usr/bin/env python3
"""More dungeon generator bug tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '2026-06-12-ascii-dungeon-generator'))
from dungeon_generator import *

# Bug: validate_config doesn't check max_room_size vs map size
config = DungeonConfig(width=10, height=10, min_room_size=3, max_room_size=15, min_rooms=5, max_rooms=10)
errors = validate_config(config)
print(f'Validation for 10x10 map with room_size 3-15: {errors}')

# Test: What happens when dungeon can't generate enough rooms?
config2 = DungeonConfig(width=10, height=10, min_rooms=5, max_rooms=10, min_room_size=3, max_room_size=5)
gen = DungeonGenerator(config2)
result = gen.generate()
print(f'Small map with many rooms: {len(gen.rooms)} rooms generated')
print(f'Grid populated: {any(gen.grid[y][x] != WALL for y in range(10) for x in range(10))}')

# Test: What happens when _add_monsters tries to place monsters in a tiny room?
config3 = DungeonConfig(seed=42, min_room_size=2, max_room_size=2, width=40, height=20, min_rooms=3, max_rooms=5)
gen3 = DungeonGenerator(config3)
try:
    gen3.generate()
    print(f'Tiny rooms: {len(gen3.rooms)} rooms generated')
    for room in gen3.rooms:
        print(f'  Room {room.room_id}: ({room.x},{room.y}) {room.w}x{room.h}')
        # For w=2: randint(room.x+1, room.x+room.w-2) = randint(room.x+1, room.x)
        # This is INVALID (max < min)
except ValueError as e:
    print(f'ValueError: {e}')

# Bug: min_room_size=2 causes crash specifically in _add_monsters, _add_treasures, _add_npcs
# randint(room.x + 1, room.x + room.w - 2) -> when w=2: randint(x+1, x+0)
# This raises ValueError
# The fix should ensure that when room.w <= 2 or room.h <= 2, we skip or handle this
print("\n=== Direct test of the bug ===")
room = type('Room', (), {'x': 5, 'y': 5, 'w': 2, 'h': 2})()
try:
    import random
    rng = random.Random(42)
    # This is what _add_monsters does:
    mx = rng.randint(room.x + 1, room.x + room.w - 2)  # randint(6, 5) -> CRASH
    print(f"  randint({room.x+1}, {room.x+room.w-2}) = {mx}")
except ValueError as e:
    print(f"  BUG CONFIRMED: randint({room.x+1}, {room.x+room.w-2}) raises ValueError: {e}")

# Test: generate() silently returns incomplete dungeons
print("\n=== generate() returning incomplete dungeons ===")
config4 = DungeonConfig(seed=9999, width=12, height=10, min_rooms=8, max_rooms=15, min_room_size=3, max_room_size=6)
gen4 = DungeonGenerator(config4)
gen4.generate()
print(f'Rooms generated: {len(gen4.rooms)}')
if len(gen4.rooms) < 2:
    print(f'  BUG: generate() returned with only {len(gen4.rooms)} rooms (< 2 minimum)')

# Bug: validate_config doesn't validate theme
config5 = DungeonConfig(theme="invalid_theme")
errors5 = validate_config(config5)
print(f'\nValidation for invalid theme: {errors5}')
# No error for invalid theme! This is a bug.