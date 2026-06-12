#!/usr/bin/env python3
"""Final bug verification tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '2026-06-12-rune-cipher'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '2026-06-12-ascii-dungeon-generator'))

from rune_cipher import *
from dungeon_generator import *

# Verify XOR round-trip with emoji
enc = xor_encrypt('hi🎉', 'key')
dec = xor_decrypt(enc, 'key')
print(f'Emoji XOR round-trip: {repr(dec)} == "hi🎉": {dec == "hi🎉"}')

# Check stairs placement
config = DungeonConfig(seed=42, width=60, height=30, add_water=True, add_pillars=True)
gen = DungeonGenerator(config)
gen.generate()

stairs_up = None
stairs_down = None
for y in range(config.height):
    for x in range(config.width):
        if gen.grid[y][x] == STAIRS_UP:
            stairs_up = (x, y)
        elif gen.grid[y][x] == STAIRS_DOWN:
            stairs_down = (x, y)
print(f'Stairs up at: {stairs_up}')
print(f'Stairs down at: {stairs_down}')

# Check if stairs could fail to be placed when all floor tiles in a room are water/pillar
# This is unlikely but possible in theory
config2 = DungeonConfig(seed=42, width=60, height=30, add_water=True, add_pillars=True, add_doors=False)
gen2 = DungeonGenerator(config2)
gen2.generate()
# Count stairs
up_count = sum(1 for y in range(config2.height) for x in range(config2.width) if gen2.grid[y][x] == STAIRS_UP)
down_count = sum(1 for y in range(config2.height) for x in range(config2.width) if gen2.grid[y][x] == STAIRS_DOWN)
print(f'Stairs up: {up_count}, Stairs down: {down_count}')

# Now check: does _add_stairs handle the case where room center has no FLOOR tile?
# Room center could be WATER or PILLAR
# _add_stairs searches for FLOOR tiles near center and picks the closest one
# If ALL floor tiles in a room are covered by water/pillar, no stairs can be placed
# This is a real bug scenario for small rooms with lots of water

# Check if crack_vigenere can find "secret" key
print("\n=== crack_vigenere accuracy test ===")
text = "the quick brown fox jumps over the lazy dog and the cat sat on the mat while the dog ran in the park"
key = "secret"
ct = vigenere_encrypt(text, key)
candidates = crack_vigenere(ct)
for k, d in candidates[:3]:
    match = "CORRECT" if k == key else "wrong"
    print(f'  Key="{k}": {d[:60]} ({match})')

# Verify the IoC zero-division edge case in analyze_frequency
print("\n=== IoC edge case ===")
# n=1: Counter has 1 element with count 1
# ic = 1*(1-1) / (1*(1-1)) = 0/0 -> ZeroDivisionError?
try:
    result = analyze_frequency("a")
    print(f"analyze_frequency('a'): IoC = {result.get('index_of_coincidence')}")
except ZeroDivisionError as e:
    print(f"BUG: ZeroDivisionError in analyze_frequency('a'): {e}")

# n=2 same letter: Counter has 1 element with count 2
# ic = 2*(2-1) / (2*(2-1)) = 2/2 = 1.0
result2 = analyze_frequency("aa")
print(f"analyze_frequency('aa'): IoC = {result2.get('index_of_coincidence')}")

# Verify the critical dungeon generator bug: min_room_size=2 crash
print("\n=== Critical dungeon bug: min_room_size=2 ===")
config3 = DungeonConfig(seed=42, min_room_size=2, max_room_size=2, width=40, height=20, min_rooms=3, max_rooms=5)
gen3 = DungeonGenerator(config3)
try:
    gen3.generate()
    print(f"Generated with min_room_size=2: {len(gen3.rooms)} rooms")
except ValueError as e:
    print(f"CRASH: ValueError: {e}")

# Verify that larger room sizes work fine
config4 = DungeonConfig(seed=42, min_room_size=4, max_room_size=8, width=60, height=30)
gen4 = DungeonGenerator(config4)
gen4.generate()
print(f"Generated with min_room_size=4: {len(gen4.rooms)} rooms")

# Check the specific line that crashes
# In _add_monsters: mx = self.rng.randint(room.x + 1, room.x + room.w - 2)
# When room.w = 2: randint(room.x + 1, room.x + 0) -> CRASH
room = Room(x=5, y=5, w=2, h=3)
print(f"\nRoom w=2: randint({room.x + 1}, {room.x + room.w - 2}) -> randint({room.x + 1}, {room.x + room.w - 2})")
# This is randint(6, 5) which is invalid

# Same issue with room.h = 2 in _add_monsters:
# my = self.rng.randint(room.y + 1, room.y + room.h - 2)
# When room.h = 2: randint(room.y + 1, room.y + 0) -> CRASH
print(f"Room h=2: randint({room.y + 1}, {room.y + room.h - 2}) -> randint({room.y + 1}, {room.y + room.h - 2})")

# Also affects _add_treasures, _add_npcs with same pattern