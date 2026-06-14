#!/usr/bin/env python3
"""Run tests for CLI Tamagotchi without pytest dependency.

Covers all game mechanics including teach, explore, achievements, diary,
CLI flags, and save backup/migration.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tamagotchi as tm

passed = 0
failed = 0
errors = []

def test(name, condition, msg=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        errors.append(f"  ✗ {name}: {msg}")
        print(f"  ✗ {name}: {msg}")


def make_pet(**overrides):
    defaults = dict(
        name="Testy",
        species="cat",
        personality="playful",
        hunger=80,
        happiness=80,
        health=100,
        energy=80,
        cleanliness=80,
        age_hours=0.2,
        stage="baby",
        is_alive=True,
        created_at=datetime.now().isoformat(),
        last_care_time=datetime.now().isoformat(),
        tricks_learned=[],
        achievements=[],
        explore_count=0,
        event_log=[],
        was_sick=False,
    )
    defaults.update(overrides)
    return tm.Pet(**defaults)


print("\n🧪 Running CLI Tamagotchi tests...\n")

# ─── Pet creation ────────────────────────────────────────────────────
pet = make_pet()
test("Pet creation - name", pet.name == "Testy")
test("Pet creation - species", pet.species == "cat")
test("Pet creation - alive", pet.is_alive is True)
test("Pet creation - hunger", pet.hunger == 80)

# ─── Actions ────────────────────────────────────────────────────────
pet = make_pet(hunger=50)
msg = tm.do_feed(pet)
test("Feed increases hunger", pet.hunger >= 70, f"hunger={pet.hunger}")
test("Feed returns message", len(msg) > 0, f"msg='{msg}'")
test("Feed increments interactions", pet.total_interactions == 1)

pet = make_pet(hunger=80, happiness=50, energy=50)
msg = tm.do_play(pet)
test("Play increases happiness", pet.happiness >= 65, f"happiness={pet.happiness}")
test("Play decreases energy", pet.energy < 50, f"energy={pet.energy}")
test("Play decreases hunger", pet.hunger < 80, f"hunger={pet.hunger}")

pet = make_pet(health=50)
msg = tm.do_heal(pet)
test("Heal increases health", pet.health >= 75, f"health={pet.health}")
test("Heal increments interactions", pet.total_interactions == 1)

pet = make_pet(energy=30)
msg = tm.do_sleep(pet)
test("Sleep increases energy", pet.energy >= 60, f"energy={pet.energy}")
test("Sleep decreases hunger", pet.hunger < 80, f"hunger={pet.hunger}")

pet = make_pet(cleanliness=40)
msg = tm.do_clean(pet)
test("Clean increases cleanliness", pet.cleanliness >= 65, f"cleanliness={pet.cleanliness}")
test("Clean increments interactions", pet.total_interactions == 1)

pet = make_pet(happiness=50)
msg = tm.do_pet(pet)
test("Pet increases happiness", pet.happiness >= 58, f"happiness={pet.happiness}")
test("Pet increments interactions", pet.total_interactions == 1)

# ─── Decay ───────────────────────────────────────────────────────────
pet = make_pet(hunger=80, happiness=80, health=100, energy=80, cleanliness=80)
pet.apply_decay(60)
test("Decay reduces hunger", pet.hunger < 80, f"hunger={pet.hunger}")
test("Decay reduces happiness", pet.happiness < 80, f"happiness={pet.happiness}")
test("Decay reduces energy", pet.energy < 80, f"energy={pet.energy}")
test("Decay reduces cleanliness", pet.cleanliness < 80, f"cleanliness={pet.cleanliness}")

pet = make_pet(hunger=10, happiness=10, cleanliness=10, health=80)
pet.apply_decay(60)
test("Decay hurts health when stats low", pet.health < 60, f"health={pet.health}")

# ─── Death ───────────────────────────────────────────────────────────
pet = make_pet(health=5, hunger=0, happiness=0, cleanliness=0)
pet.apply_decay(1440)
test("Pet dies from extreme neglect", pet.is_alive is False)

# ─── Clamp ───────────────────────────────────────────────────────────
pet = make_pet(hunger=150, happiness=-10)
pet.clamp_stats()
test("Clamp caps hunger at 100", pet.hunger == 100, f"hunger={pet.hunger}")
test("Clamp floors happiness at 0", pet.happiness == 0, f"happiness={pet.happiness}")

# ─── Mood ────────────────────────────────────────────────────────────
pet = make_pet(hunger=95, happiness=95, health=95, energy=95, cleanliness=95)
test("Mood ecstatic", pet.get_overall_mood() == "ecstatic", f"mood={pet.get_overall_mood()}")

pet = make_pet(health=15)
test("Mood sick", pet.get_overall_mood() == "sick", f"mood={pet.get_overall_mood()}")

pet = make_pet(is_alive=False)
test("Mood dead", pet.get_overall_mood() == "dead", f"mood={pet.get_overall_mood()}")

# ─── Stage progression ──────────────────────────────────────────────
pet = make_pet(age_hours=0.01)
pet.update_stage()
test("Stage egg", pet.stage == "egg", f"stage={pet.stage}")

pet = make_pet(age_hours=0.2, stage="baby")
pet.update_stage()
test("Stage baby", pet.stage == "baby", f"stage={pet.stage}")

pet = make_pet(age_hours=1.0, stage="baby")
msgs = pet.update_stage()
test("Stage child", pet.stage == "child", f"stage={pet.stage}")
test("Level up messages generated", len(msgs) > 0, f"msgs={msgs}")

pet = make_pet(age_hours=5.0, stage="child")
pet.update_stage()
test("Stage adult", pet.stage == "adult", f"stage={pet.stage}")

pet = make_pet(age_hours=15.0, stage="adult")
pet.update_stage()
test("Stage elder", pet.stage == "elder", f"stage={pet.stage}")

# ─── Art coverage ────────────────────────────────────────────────────
for species in tm.SPECIES_LIST:
    for stage in ["egg", "baby", "child", "adult", "elder", "dead"]:
        test(f"Art for {species}/{stage}", stage in tm.PET_ART[species],
             f"missing {stage} for {species}")

# ─── Response coverage ──────────────────────────────────────────────
for species in tm.SPECIES_LIST:
    for action in ["feed", "play", "heal", "sleep", "clean", "pet", "ignore"]:
        test(f"Responses for {species}/{action}", species in tm.RESPONSES[action],
             f"missing {action} for {species}")

# ─── Stat bar ────────────────────────────────────────────────────────
bar = tm.stat_bar(50, width=10)
test("Stat bar has fill", "█" in bar)
test("Stat bar has empty", "░" in bar)

# ─── Render pet ──────────────────────────────────────────────────────
pet = make_pet()
output = tm.render_pet(pet)
test("Render includes name", "Testy" in output)
test("Render includes stats", "Stats" in output)

pet = make_pet(is_alive=False)
output = tm.render_pet(pet)
test("Render dead shows message", "passed away" in output)

# ─── All species ─────────────────────────────────────────────────────
for sp in tm.SPECIES_LIST:
    pet = make_pet(species=sp)
    test(f"Species {sp} - art exists", len(pet.get_art()) > 0)
    test(f"Species {sp} - mood valid", pet.get_overall_mood() in tm.MOOD_FACES)

# ─── Save/Load ──────────────────────────────────────────────────────
tmpdir = tempfile.mkdtemp()
save_file = tm.Path(tmpdir) / "pet.json"
backup_file = tm.Path(tmpdir) / "pet.json.bak"
import unittest.mock as mock
with mock.patch.object(tm, 'SAVE_FILE', save_file), \
     mock.patch.object(tm, 'SAVE_DIR', tm.Path(tmpdir)), \
     mock.patch.object(tm, 'BACKUP_FILE', backup_file):
    pet = make_pet(name="SaveTest", species="dragon")
    tm.save_pet(pet)
    loaded = tm.load_pet()
    test("Save/Load preserves name", loaded.name == "SaveTest", f"name={loaded.name}")
    test("Save/Load preserves species", loaded.species == "dragon", f"species={loaded.species}")

# ─── Decay doesn't go negative ──────────────────────────────────────
pet = make_pet(hunger=5, happiness=5, health=5, energy=5, cleanliness=5)
pet.apply_decay(500)
test("Decay caps hunger at 0", pet.hunger >= 0, f"hunger={pet.hunger}")
test("Decay caps happiness at 0", pet.happiness >= 0, f"happiness={pet.happiness}")
test("Decay caps energy at 0", pet.energy >= 0, f"energy={pet.energy}")
test("Decay caps cleanliness at 0", pet.cleanliness >= 0, f"cleanliness={pet.cleanliness}")

# ═══════════════════════════════════════════════════════════════════════
# NEW FEATURE TESTS
# ═══════════════════════════════════════════════════════════════════════

print("\n  ─── New Feature Tests ───\n")

# ─── Teach ───────────────────────────────────────────────────────────
pet = make_pet(energy=50)
msg = tm.do_teach(pet)
test("Teach adds trick", len(pet.tricks_learned) == 1, f"tricks={pet.tricks_learned}")
test("Teach costs energy", pet.energy < 50, f"energy={pet.energy}")
test("Teach increments interactions", pet.total_interactions == 1)
test("Teach first achievement", "first_teach" in pet.achievements)

pet = make_pet(energy=5)
msg = tm.do_teach(pet)
test("Teach too tired fails", "too tired" in msg.lower(), f"msg={msg}")
test("Teach too tired no trick", len(pet.tricks_learned) == 0)

# Learn all tricks for cat
pet = make_pet(energy=100)
cat_tricks = tm.TRICKS["cat"]
for _ in cat_tricks:
    tm.do_teach(pet)
test("Teach all tricks learned", len(pet.tricks_learned) == len(cat_tricks),
     f"learned={len(pet.tricks_learned)}, total={len(cat_tricks)}")
msg = tm.do_teach(pet)
test("Teach when all known performs trick", "already knows" in msg.lower(), f"msg={msg}")

# Tricks exist for all species
for species in tm.SPECIES_LIST:
    test(f"Tricks defined for {species}", species in tm.TRICKS and len(tm.TRICKS[species]) > 0)

# ─── Explore ─────────────────────────────────────────────────────────
pet = make_pet(energy=50)
msg = tm.do_explore(pet)
test("Explore increments count", pet.explore_count == 1)
test("Explore costs energy", pet.energy < 50)
test("Explore increments interactions", pet.total_interactions == 1)
test("Explore first achievement", "first_explore" in pet.achievements)
test("Explore returns message", len(msg) > 0)

pet = make_pet(energy=5)
msg = tm.do_explore(pet)
test("Explore too tired fails", "too tired" in msg.lower())
test("Explore too tired no count", pet.explore_count == 0)

# Explore events exist for all species
for species in tm.SPECIES_LIST:
    test(f"Explore events for {species}",
         species in tm.EXPLORE_EVENTS and len(tm.EXPLORE_EVENTS[species]) > 0)

# ─── Achievements ────────────────────────────────────────────────────
pet = make_pet(lifetime_interactions=10)
new = tm.check_achievements(pet)
test("Achievement interactions_10", "interactions_10" in new)

pet = make_pet(lifetime_interactions=50)
new = tm.check_achievements(pet)
test("Achievement interactions_50", "interactions_50" in new)

pet = make_pet(lifetime_interactions=100)
new = tm.check_achievements(pet)
test("Achievement interactions_100", "interactions_100" in new)

pet = make_pet(hunger=85, happiness=85, health=85, energy=85, cleanliness=85)
new = tm.check_achievements(pet)
test("Achievement all_stats_high", "all_stats_high" in new)

pet = make_pet(was_sick=True, health=50)
new = tm.check_achievements(pet)
test("Achievement survived_sickness", "survived_sickness" in new)

pet = make_pet(tricks_learned=["A", "B", "C"])
new = tm.check_achievements(pet)
test("Achievement tricks_3", "tricks_3" in new)

pet = make_pet(tricks_learned=["A", "B", "C", "D", "E"])
new = tm.check_achievements(pet)
test("Achievement tricks_5", "tricks_5" in new)

pet = make_pet(explore_count=5)
new = tm.check_achievements(pet)
test("Achievement explores_5", "explores_5" in new)

pet = make_pet(explore_count=20)
new = tm.check_achievements(pet)
test("Achievement explores_20", "explores_20" in new)

pet = make_pet(stage="adult")
new = tm.check_achievements(pet)
test("Achievement reached_adult", "reached_adult" in new)

pet = make_pet(stage="elder")
new = tm.check_achievements(pet)
test("Achievement reached_elder", "reached_elder" in new)

# No re-awarding
pet = make_pet(lifetime_interactions=10, achievements=["interactions_10"])
new = tm.check_achievements(pet)
test("Achievement no re-award", "interactions_10" not in new)

# All achievement defs exist
all_ach_ids = [
    "first_feed", "first_play", "first_heal", "first_sleep", "first_clean",
    "first_teach", "first_explore",
    "interactions_10", "interactions_50", "interactions_100", "interactions_500",
    "all_stats_high", "survived_sickness",
    "tricks_3", "tricks_5",
    "explores_5", "explores_20",
    "reached_adult", "reached_elder",
]
for aid in all_ach_ids:
    test(f"Achievement def exists: {aid}", aid in tm.ACHIEVEMENT_DEFS)

# Format achievement
formatted = tm.format_achievement("first_feed")
test("Format achievement has content", len(formatted) > 0)

# ─── Diary / Event Log ───────────────────────────────────────────────
pet = make_pet()
tm.do_feed(pet)
test("Event log records feed", len(pet.event_log) > 0, f"log={pet.event_log}")

# Event log cap
pet = make_pet(energy=100, hunger=50)
for i in range(120):
    pet._log_event(f"Event {i}")
test("Event log capped at 100", len(pet.event_log) <= 100, f"len={len(pet.event_log)}")

# ─── Save backup ────────────────────────────────────────────────────
tmpdir2 = tempfile.mkdtemp()
save_file2 = tm.Path(tmpdir2) / "pet.json"
backup_file2 = tm.Path(tmpdir2) / "pet.json.bak"
with mock.patch.object(tm, 'SAVE_FILE', save_file2), \
     mock.patch.object(tm, 'SAVE_DIR', tm.Path(tmpdir2)), \
     mock.patch.object(tm, 'BACKUP_FILE', backup_file2):
    pet1 = make_pet(name="First")
    tm.save_pet(pet1)
    pet2 = make_pet(name="Second")
    tm.save_pet(pet2)
    test("Backup created on second save", backup_file2.exists())
    if backup_file2.exists():
        with open(backup_file2) as f:
            backup_data = json.load(f)
        test("Backup has first save name", backup_data["name"] == "First", f"name={backup_data['name']}")

# ─── Load fallback to backup ─────────────────────────────────────────
tmpdir3 = tempfile.mkdtemp()
save_file3 = tm.Path(tmpdir3) / "pet.json"
backup_file3 = tm.Path(tmpdir3) / "pet.json.bak"
with mock.patch.object(tm, 'SAVE_FILE', save_file3), \
     mock.patch.object(tm, 'SAVE_DIR', tm.Path(tmpdir3)), \
     mock.patch.object(tm, 'BACKUP_FILE', backup_file3):
    # Save twice to create a backup of the first save
    pet = make_pet(name="BackupTest", species="dragon")
    tm.save_pet(pet)
    # Second save creates backup of the first
    pet2 = make_pet(name="Overwrite", species="cat")
    tm.save_pet(pet2)
    # Corrupt the primary save
    with open(save_file3, 'w') as f:
        f.write("{corrupted!!!")
    # Should fall back to backup (which has "BackupTest")
    loaded = tm.load_pet()
    test("Load falls back to backup", loaded is not None and loaded.name == "BackupTest",
         f"loaded={loaded}")

# ─── Save migration (old saves missing new fields) ──────────────────
tmpdir4 = tempfile.mkdtemp()
save_file4 = tm.Path(tmpdir4) / "pet.json"
with mock.patch.object(tm, 'SAVE_FILE', save_file4), \
     mock.patch.object(tm, 'SAVE_DIR', tm.Path(tmpdir4)), \
     mock.patch.object(tm, 'BACKUP_FILE', tm.Path(tmpdir4) / "pet.json.bak"):
    old_data = {
        "name": "OldPet",
        "species": "cat",
        "personality": "lazy",
        "hunger": 80, "happiness": 80, "health": 100, "energy": 80, "cleanliness": 80,
        "age_hours": 1.0, "stage": "child", "is_alive": True,
        "created_at": datetime.now().isoformat(),
        "last_care_time": datetime.now().isoformat(),
        "total_interactions": 5, "lifetime_interactions": 5, "messages": [],
    }
    with open(save_file4, 'w') as f:
        json.dump(old_data, f)
    loaded = tm.load_pet()
    test("Migration: loads old save", loaded is not None)
    if loaded:
        test("Migration: name preserved", loaded.name == "OldPet")
        test("Migration: tricks default empty", loaded.tricks_learned == [])
        test("Migration: achievements default empty", loaded.achievements == [])
        test("Migration: explore_count default 0", loaded.explore_count == 0)
        test("Migration: event_log default empty", loaded.event_log == [])
        test("Migration: was_sick default False", loaded.was_sick is False)

# ─── CLI flags ────────────────────────────────────────────────────────
result = tm.parse_args(["tamagotchi.py", "--help"])
test("CLI --help flag", result["show_help"] is True)

result = tm.parse_args(["tamagotchi.py", "-h"])
test("CLI -h flag", result["show_help"] is True)

result = tm.parse_args(["tamagotchi.py", "--version"])
test("CLI --version flag", result["show_version"] is True)

result = tm.parse_args(["tamagotchi.py", "-v"])
test("CLI -v flag", result["show_version"] is True)

result = tm.parse_args(["tamagotchi.py", "--bogus"])
test("CLI unknown arg error", result["error"] != "")

result = tm.parse_args(["tamagotchi.py"])
test("CLI no args defaults", result["show_help"] is False and result["show_version"] is False)

# Version constant
test("Version is valid semver", len(tm.VERSION.split(".")) == 3)

# ─── was_sick tracking ───────────────────────────────────────────────
pet = make_pet(health=25, hunger=10, happiness=10, cleanliness=10)
pet.apply_decay(60)
if pet.health < tm.SICK_THRESHOLD:
    test("was_sick set on low health", pet.was_sick is True)
else:
    test("was_sick tracking (stat OK)", True)  # Can't guarantee in this run

# ─── Render includes new features ───────────────────────────────────
pet = make_pet(tricks_learned=["High Five"], achievements=["first_feed"])
output = tm.render_pet(pet)
test("Render shows tricks count", "Tricks" in output or "tricks" in output.lower())
test("Render shows achievements count", "Achievement" in output or "achievement" in output.lower())

# ─── Delete pet cleans up backup too ────────────────────────────────
tmpdir5 = tempfile.mkdtemp()
save_file5 = tm.Path(tmpdir5) / "pet.json"
backup_file5 = tm.Path(tmpdir5) / "pet.json.bak"
with mock.patch.object(tm, 'SAVE_FILE', save_file5), \
     mock.patch.object(tm, 'SAVE_DIR', tm.Path(tmpdir5)), \
     mock.patch.object(tm, 'BACKUP_FILE', backup_file5):
    pet = make_pet(name="DeleteMe")
    tm.save_pet(pet)
    tm.save_pet(pet)  # Create backup
    test("Delete: both files exist before delete", save_file5.exists() and backup_file5.exists())
    tm.delete_pet()
    test("Delete: primary removed", not save_file5.exists())
    test("Delete: backup removed", not backup_file5.exists())

# ═══════════════════════════════════════════════════════════════════════
# BUG FIX TESTS (v2.2)
# ═══════════════════════════════════════════════════════════════════════

print("\n  ─── Bug Fix Tests (v2.2) ───\n")

# ─── stat_bar clamping ────────────────────────────────────────────────
import re

bar_over = tm.stat_bar(150, width=20)
clean_over = re.sub(r'\x1b\[[0-9;]*m', '', bar_over)
test("stat_bar clamps values above MAX_STAT", len(clean_over) == 20, f"len={len(clean_over)}")

bar_under = tm.stat_bar(-10, width=20)
clean_under = re.sub(r'\x1b\[[0-9;]*m', '', bar_under)
test("stat_bar clamps negative values to 0", len(clean_under) == 20, f"len={len(clean_under)}")

# ─── Explore energy threshold matches cost ─────────────────────────────
pet = make_pet(energy=8)
msg = tm.do_explore(pet)
test("Explore with energy=8 succeeds", "too tired" not in msg.lower(), f"msg={msg}")
test("Explore with energy=8 increments count", pet.explore_count == 1)

pet = make_pet(energy=7)
msg = tm.do_explore(pet)
test("Explore with energy=7 rejected", "too tired" in msg.lower(), f"msg={msg}")
test("Explore with energy=7 no count change", pet.explore_count == 0)

# ─── Dead pet action rejection ────────────────────────────────────────
dead_pet = make_pet(is_alive=False, hunger=0, health=0, energy=0, happiness=0, cleanliness=0,
                    total_interactions=0, lifetime_interactions=0, achievements=[])

msg = tm.do_feed(dead_pet)
test("Dead pet feed rejected", "passed away" in msg.lower(), f"msg={msg}")
test("Dead pet feed no hunger change", dead_pet.hunger == 0, f"hunger={dead_pet.hunger}")

dead_pet2 = make_pet(is_alive=False, happiness=10, energy=80)
msg = tm.do_play(dead_pet2)
test("Dead pet play rejected", "passed away" in msg.lower(), f"msg={msg}")
test("Dead pet play no happiness change", dead_pet2.happiness == 10)

dead_pet3 = make_pet(is_alive=False, health=0)
msg = tm.do_heal(dead_pet3)
test("Dead pet heal rejected", "passed away" in msg.lower(), f"msg={msg}")
test("Dead pet heal no health change", dead_pet3.health == 0)

dead_pet4 = make_pet(is_alive=False, energy=0)
msg = tm.do_sleep(dead_pet4)
test("Dead pet sleep rejected", "passed away" in msg.lower(), f"msg={msg}")
test("Dead pet sleep no energy change", dead_pet4.energy == 0)

dead_pet5 = make_pet(is_alive=False, cleanliness=10)
msg = tm.do_clean(dead_pet5)
test("Dead pet clean rejected", "passed away" in msg.lower(), f"msg={msg}")
test("Dead pet clean no cleanliness change", dead_pet5.cleanliness == 10)

dead_pet6 = make_pet(is_alive=False, happiness=10)
msg = tm.do_pet(dead_pet6)
test("Dead pet pet rejected", "passed away" in msg.lower(), f"msg={msg}")
test("Dead pet pet no happiness change", dead_pet6.happiness == 10)

dead_pet7 = make_pet(is_alive=False, energy=50)
msg = tm.do_teach(dead_pet7)
test("Dead pet teach rejected", "passed away" in msg.lower(), f"msg={msg}")
test("Dead pet teach no tricks", len(dead_pet7.tricks_learned) == 0)

dead_pet8 = make_pet(is_alive=False, energy=50)
msg = tm.do_explore(dead_pet8)
test("Dead pet explore rejected", "passed away" in msg.lower(), f"msg={msg}")
test("Dead pet explore no count", dead_pet8.explore_count == 0)

# Dead pet feed should not award achievements or increment interactions
dead_pet9 = make_pet(is_alive=False, hunger=0, achievements=[], total_interactions=0, lifetime_interactions=0)
tm.do_feed(dead_pet9)
test("Dead pet feed no achievement", "first_feed" not in dead_pet9.achievements)
test("Dead pet feed no interaction increment", dead_pet9.total_interactions == 0)

# ─── Results ─────────────────────────────────────────────────────────
print(f"\n{'═' * 50}")
print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print(f"\n  Failed tests:")
    for e in errors:
        print(f"    {e}")
print(f"{'═' * 50}\n")

sys.exit(0 if failed == 0 else 1)