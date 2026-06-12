#!/usr/bin/env python3
"""Bug hunting tests - systematically looking for bugs in both projects."""

import sys
import os

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '2026-06-12-ascii-dungeon-generator'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '2026-06-12-rune-cipher'))

from dungeon_generator import *
from rune_cipher import *

print("=" * 60)
print("BUG HUNT: DUNGEON GENERATOR")
print("=" * 60)

# --- Bug: Small rooms (min_room_size=2) cause entity placement crash ---
# In _add_monsters, _add_treasures, _add_npcs: randint(room.x+1, room.x+room.w-2)
# When room.w=2, this becomes randint(room.x+1, room.x), which raises ValueError
print("\n[BUG 1] Small room size (w=2 or h=2) - randint bounds error")
try:
    config = DungeonConfig(seed=42, min_room_size=2, max_room_size=2, width=30, height=15, min_rooms=2, max_rooms=3)
    gen = DungeonGenerator(config)
    gen.generate()
    print("  No crash with min_room_size=2 - checking if entities were placed...")
    # Check for rooms with w=2 or h=2
    for room in gen.rooms:
        if room.w <= 2 or room.h <= 2:
            print(f"  Room {room.room_id}: w={room.w}, h={room.h} - could cause randint error in entity placement")
except ValueError as e:
    print(f"  BUG CONFIRMED: ValueError with small rooms: {e}")
except Exception as e:
    print(f"  Other error: {type(e).__name__}: {e}")

# --- Bug: Entities on non-walkable tiles ---
print("\n[BUG 2] Entities placed on non-walkable tiles (water/pillar/door)")
config = DungeonConfig(seed=123, width=60, height=30)
gen = DungeonGenerator(config)
gen.generate()
bad_entities = 0
for e in gen.entities:
    tile = gen.grid[e.y][e.x]
    if tile not in (FLOOR, CORRIDOR):
        bad_entities += 1
        print(f"  BUG: {e.kind} '{e.description}' at ({e.x},{e.y}) on {TILE_NAMES.get(tile, str(tile))} tile")
if bad_entities == 0:
    print("  No entities on bad tiles (seed 123)")

# Check with more seeds
for seed in range(50):
    config = DungeonConfig(seed=seed, width=60, height=30)
    gen = DungeonGenerator(config)
    gen.generate()
    for e in gen.entities:
        tile = gen.grid[e.y][e.x]
        if tile not in (FLOOR, CORRIDOR):
            bad_entities += 1

if bad_entities == 0:
    print("  No entities on bad tiles across 51 seeds")
else:
    print(f"  Found {bad_entities} entities on non-walkable tiles across 51 seeds!")

# --- Bug: difficulty=5 with short monster list - tier out of range ---
print("\n[BUG 3] Monster tier selection with high difficulty")
config = DungeonConfig(seed=42, difficulty=5, width=60, height=30)
gen = DungeonGenerator(config)
gen.generate()
print(f"  Generated {len([e for e in gen.entities if e.kind == 'monster'])} monsters at difficulty 5")

# Check tier logic: tier = min(rng.randint(0, difficulty), len(monsters)-1)
# With difficulty=5, randint(0,5) can produce 5, but len(monsters)=6 (indices 0-5) - OK
# But what about difficulty > len(monsters)?
monsters = MONSTER_CHARS.get("standard", [])
print(f"  Monster chars for 'standard': {monsters} (length {len(monsters)})")
print(f"  With difficulty=5: tier = min(randint(0,5), 5) = 0-5, valid indices 0-5")
print(f"  This is fine since len(monsters)=6")

# --- Bug: _add_npcs with only 2 or 3 rooms ---
print("\n[BUG 4] NPC placement with few rooms")
for n_rooms in [2, 3, 4]:
    config = DungeonConfig(seed=42, min_rooms=n_rooms, max_rooms=n_rooms, width=60, height=30)
    gen = DungeonGenerator(config)
    gen.generate()
    npcs = [e for e in gen.entities if e.kind == "npc"]
    print(f"  {n_rooms} rooms -> {len(npcs)} NPCs")

# --- Bug: Room center property ---
print("\n[BUG 5] Room center calculation")
room = Room(x=3, y=3, w=4, h=4)
print(f"  Room(3,3,4,4).center = {room.center}")
# center = (3 + 4//2, 3 + 4//2) = (5, 5) - this is the center of a 4x4 room?
# A room at (3,3) with w=4,h=4 occupies x=3..6, y=3..6
# Center should be (4.5, 4.5), but integer center is (5, 5)
# That's actually outside or on edge. Let me check.
# Floor tiles are at x=3..6, y=3..6 (inclusive)
# Center (5,5) is within. Seems ok.

# --- Bug: Dungeon generation can fail silently ---
print("\n[BUG 6] Dungeon generation returns incomplete result after retries")
config = DungeonConfig(seed=9999, width=10, height=10, min_rooms=8, max_rooms=12)
gen = DungeonGenerator(config)
result = gen.generate()
print(f"  Tiny grid with many rooms: {len(gen.rooms)} rooms generated")

# --- Bug: Rune cipher - XOR with unicode characters ---
print("\n" + "=" * 60)
print("BUG HUNT: RUNE CIPHER")
print("=" * 60)

# --- Bug: XOR round-trip with unicode characters ---
print("\n[BUG R1] XOR round-trip with multi-byte characters")
try:
    text = "café"
    key = "test"
    enc = xor_encrypt(text, key)
    dec = xor_decrypt(enc, key)
    if dec == text:
        print(f"  XOR round-trip with 'café': OK (dec={repr(dec)})")
    else:
        print(f"  BUG: XOR round-trip failed! orig={repr(text)}, dec={repr(dec)}")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")

# --- Bug: XOR with key shorter than text - key wrapping ---
print("\n[BUG R2] XOR key wrapping")
text = "hello"
key = "a"
enc = xor_encrypt(text, key)
dec = xor_decrypt(enc, key)
print(f"  XOR round-trip (key='a'): orig={repr(text)}, dec={repr(dec)}, match={text==dec}")

# --- Bug: crack_vigenere with short text returns ("<short>", original) which isn't decrypted ---
print("\n[BUG R3] crack_vigenere with short text returns original ciphertext")
result = crack_vigenere("ab")
print(f"  crack_vigenere('ab') = {result}")
# Returns [("<short>", "ab")] - the second element is the ORIGINAL ciphertext, not decrypted

# --- Bug: crack_vigenere key length detection with single-letter groups ---
print("\n[BUG R4] crack_vigenere IC calculation with tiny groups")

# --- Bug: frequency_score with empty string ---
print("\n[BUG R5] frequency_score with empty/whitespace string")
score_empty = frequency_score("")
print(f"  frequency_score('') = {score_empty}")
score_space = frequency_score("   ")
print(f"  frequency_score('   ') = {score_space}")

# --- Bug: combined_score with empty string ---
score_cs = combined_score("")
print(f"  combined_score('') = {score_cs}")

# --- Bug: analyze_frequency with single character ---
result = analyze_frequency("a")
print(f"\n[BUG R6] analyze_frequency('a')")
print(f"  total_letters: {result.get('total_letters')}")
print(f"  IoC: {result.get('index_of_coincidence')}")
# IoC = c*(c-1) / (n*(n-1)) = 1*0/(1*0) = ZeroDivisionError!

# --- Bug: crack_substitution randomness (uses random module, not seeded) ---
print("\n[BUG R7] crack_substitution uses global random (not seeded)")
import random as rng_module
rng_module.seed(42)
result1 = crack_substitution("hello world this is a test of the emergency broadcast system")
rng_module.seed(42)
result2 = crack_substitution("hello world this is a test of the emergency broadcast system")
print(f"  Seeded crack_substitution results match: {result1 == result2}")

# --- Bug: substitution_decrypt with lowercase key containing non-alpha ---
print("\n[BUG R8] substitution key validation edge cases")

# --- Bug: Dungeon generator - corridor not carved when x1==x2 and y1==y2 ---
print("\n[BUG 7] Corridor with same start/end point")
gen = DungeonGenerator(DungeonConfig(seed=42))
gen._init_grid()
# Manually carve a room and test corridor
gen.grid[10][10] = FLOOR  # Mark start as walkable
gen._carve_corridor(10, 10, 10, 10)
print(f"  Same-point corridor: tile at (10,10) = {gen.grid[10][10]} (expected {FLOOR})")

# --- Bug: corridor that goes through already-floor tiles ---
print("\n[BUG 8] Corridor carving only changes WALL tiles to CORRIDOR")
gen = DungeonGenerator(DungeonConfig(seed=42))
gen._init_grid()
# Carve a floor tile
gen.grid[10][10] = FLOOR
# Carve a corridor that includes this floor tile
gen._carve_corridor(5, 10, 15, 10)
# Check if the floor tile was overwritten to CORRIDOR
print(f"  Floor tile after corridor: {gen.grid[10][10]} (FLOOR={FLOOR}, CORRIDOR={CORRIDOR})")
print(f"  This means corridor tiles replace floor tiles - could break room identification")

# --- Bug: render_fog_of_war doesn't reveal stairs up ---
print("\n[BUG 9] Fog of war reveals stairs")
config = DungeonConfig(seed=42)
gen = DungeonGenerator(config)
gen.generate()
fog_map = gen.render_fog_of_war(reveal_radius=100)
# With radius 100, everything should be revealed (or at least stairs)
has_stairs_up = STAIRS_UP not in [row.count('▲') for row in fog_map.split('\n')]
print(f"  Fog with r=100 - has stairs up visible: {'▲' in fog_map}")
print(f"  Fog with r=4 - has stairs up visible: {'▲' in gen.render_fog_of_war()}")

# --- Bug: Dungeon center property with room position 0 ---
print("\n[BUG 10] Room center with position 0")
room = Room(x=0, y=0, w=3, h=3)
print(f"  Room(0,0,3,3).center = {room.center}")

# --- Bug: validate_config doesn't check room_size vs map_size compatibility ---
print("\n[BUG 11] Config validation allows impossibly large rooms")
errors = validate_config(DungeonConfig(width=10, height=10, min_room_size=8, max_room_size=15))
print(f"  Validation errors for 10x10 map with room size 8-15: {errors}")
# Room of size 8+2 (with margin) needs 10 tiles, which is exactly the map width
# But rooms start at x=1, so max room at x=1 with w=8 = x+w-1 = 8, within 0-9 bounds

# --- Bug: generate() uses self.rng for room generation, but some methods
# use rng after consuming random numbers in different orders ---
print("\n[BUG 12] Seed reproducibility with different feature flags")
config1 = DungeonConfig(seed=42, add_water=True, add_pillars=True)
gen1 = DungeonGenerator(config1)
gen1.generate()

config2 = DungeonConfig(seed=42, add_water=False, add_pillars=False)
gen2 = DungeonGenerator(config2)
gen2.generate()
# Room layout should be the same because features are added after rooms
if len(gen1.rooms) == len(gen2.rooms):
    same_pos = all(r1.x == r2.x and r1.y == r2.y for r1, r2 in zip(gen1.rooms, gen2.rooms))
    print(f"  Same rooms with different features: {same_pos}")
else:
    print(f"  Different number of rooms: {len(gen1.rooms)} vs {len(gen2.rooms)}")

# --- Bug: _rooms_overlap uses margin=2 by default ---
# But a room at x=0 would overlap with margin check:
# room.x - margin < other.x + other.w -> 0 - 2 < other.x + other.w
# This is always true since other.x >= 1, so other.x + other.w >= 3 > -2
# So margin checking is fine for x=0
print("\n[BUG 13] Edge case: rooms at map boundary")
config = DungeonConfig(seed=1, width=20, height=15, min_rooms=2, max_rooms=4)
gen = DungeonGenerator(config)
gen.generate()
for room in gen.rooms:
    if room.x <= 0 or room.y <= 0:
        print(f"  Room at boundary: ({room.x}, {room.y}) w={room.w} h={room.h}")
print(f"  All rooms in bounds: {all(r.x >= 1 and r.y >= 1 for r in gen.rooms)}")

# Check rooms at far boundary
for room in gen.rooms:
    if room.x + room.w >= gen.config.width or room.y + room.h >= gen.config.height:
        print(f"  Room at far boundary: ({room.x}, {room.y}) w={room.w} h={room.h}")

print("\n" + "=" * 60)
print("ADDITIONAL TARGETED BUG TESTS")
print("=" * 60)

# --- Bug: _add_monsters randint with room.w=2 ---
# randint(room.x + 1, room.x + room.w - 2) = randint(room.x+1, room.x+0)
# when room.w=2, this is randint(room.x+1, room.x) which raises ValueError
print("\n[CRITICAL BUG] randint with room.w=2")
try:
    import random
    r = random.Random(42)
    # This should fail:
    result = r.randint(5, 4)  # room.x+1=5, room.x+room.w-2=4 when room.w=2
    print(f"  randint(5, 4) = {result} - SHOULD NOT HAPPEN")
except ValueError as e:
    print(f"  BUG CONFIRMED: randint(5, 4) raises ValueError: {e}")

# --- Bug: _carve_corridor doesn't carve the start tile if it's already FLOOR ---
# In _carve_corridor, the start tile at (x1, y1) is only carved if it's WALL
# But if a room already carved that tile as FLOOR, it stays FLOOR (not CORRIDOR)
# This is actually correct behavior - rooms should stay as FLOOR
print("\n[CORRIDOR BEHAVIOR] Corridors don't overwrite room floors")
gen = DungeonGenerator(DungeonConfig(seed=42))
gen._init_grid()
gen.grid[10][10] = FLOOR
gen._carve_corridor(10, 10, 15, 10)
print(f"  Room floor preserved as FLOOR: {gen.grid[10][10] == FLOOR}")
print(f"  Corridor tile is CORRIDOR: {gen.grid[10][11] == CORRIDOR}")

# --- Bug: Rune cipher - atbash/rot13 decrypt in interactive mode ---
# The code uses atbash_encrypt and rot13_encrypt for both encrypt and decrypt
# since they're self-inverse. But the README says "decrypt" command should work.
# Let's test that atbash is truly self-inverse:
print("\n[BUG R9] Atbash self-inverse property")
text = "hello world"
atbash_once = atbash_encrypt(text)
atbash_twice = atbash_encrypt(atbash_once)
print(f"  Original: {text}")
print(f"  Atbash once: {atbash_once}")
print(f"  Atbash twice: {atbash_twice}")
print(f"  Self-inverse: {atbash_twice == text}")

# --- Bug: Rune cipher - crack_vigenere returns wrong key ---
print("\n[BUG R10] crack_vigenere accuracy test")
text = "the quick brown fox jumps over the lazy dog"
key = "secret"
ct = vigenere_encrypt(text, key)
candidates = crack_vigenere(ct)
print(f"  Vigenere crack with key='{key}':")
for k, d in candidates[:3]:
    match = "CORRECT" if k == key else "wrong"
    print(f"    Key='{k}': {d[:50]}... ({match})")

# --- Bug: crack_caesar for single character ---
print("\n[BUG R11] crack_caesar with single character")
result = crack_caesar("d")
print(f"  crack_caesar('d') = {result[:3] if result else 'empty'}")

# --- Bug: combined_score division by zero protection ---
print("\n[BUG R12] combined_score edge cases")
print(f"  combined_score('a') = {combined_score('a')}")
print(f"  combined_score('ab') = {combined_score('ab')}")

# --- Bug: rune cipher - text_to_runes with uppercase ---
print("\n[BUG R13] text_to_runes with uppercase")
result = text_to_runes("Hello World")
print(f"  text_to_runes('Hello World') = {result}")
# Should lowercase first: 'hello world'
expected = text_to_runes("hello world")
print(f"  text_to_runes('hello world') = {expected}")
print(f"  Uppercase preserved: {result == expected}")

# --- Bug: rune cipher - runes_to_text with unknown rune ---
print("\n[BUG R14] runes_to_text with unknown characters")
result = runes_to_text("ᚨᛒᚲ123")
print(f"  runes_to_text('ᚨᛒᚲ123') = {result}")

# --- Bug: NPC placement when all rooms are entrance/exit ---
print("\n[BUG 15] NPC placement with only 2 rooms")
config = DungeonConfig(seed=42, min_rooms=2, max_rooms=2, width=40, height=20, add_npcs=True)
gen = DungeonGenerator(config)
gen.generate()
npcs = [e for e in gen.entities if e.kind == "npc"]
print(f"  NPCs with 2 rooms: {len(npcs)}")
# eligible_rooms = [r for r in self.rooms if r.room_id != 0 and r.room_id != len(self.rooms)-1]
# With 2 rooms: room_ids are 0 and 1, so eligible_rooms is empty
# num_npcs = min(3, len(self.rooms)-2) = min(3, 0) = 0
# So this should be 0 NPCs, which is correct behavior (code handles it)

# --- Bug: NPC placement when rooms > 3, eligible rooms should work ---
config = DungeonConfig(seed=42, min_rooms=5, max_rooms=8, width=60, height=30)
gen = DungeonGenerator(config)
gen.generate()
npcs = [e for e in gen.entities if e.kind == "npc"]
print(f"  NPCs with {len(gen.rooms)} rooms: {len(npcs)}")

print("\n" + "=" * 60)
print("BUG HUNT COMPLETE")
print("=" * 60)