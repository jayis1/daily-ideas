#!/usr/bin/env python3
"""Run tests for CLI Tamagotchi without pytest dependency."""

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
import unittest.mock as mock
with mock.patch.object(tm, 'SAVE_FILE', save_file), \
     mock.patch.object(tm, 'SAVE_DIR', tm.Path(tmpdir)):
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

# ─── Results ─────────────────────────────────────────────────────────
print(f"\n{'═' * 50}")
print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print(f"\n  Failed tests:")
    for e in errors:
        print(f"    {e}")
print(f"{'═' * 50}\n")

sys.exit(0 if failed == 0 else 1)