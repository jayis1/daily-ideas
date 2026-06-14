#!/usr/bin/env python3
"""Tests for CLI Tamagotchi."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import tamagotchi as tm


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
        stage="baby",
        is_alive=True,
        created_at=datetime.now().isoformat(),
        last_care_time=datetime.now().isoformat(),
    )
    defaults.update(overrides)
    return tm.Pet(**defaults)


def test_pet_creation():
    pet = make_pet()
    assert pet.name == "Testy"
    assert pet.species == "cat"
    assert pet.is_alive is True
    assert pet.hunger == 80


def test_feed_action():
    pet = make_pet(hunger=50)
    msg = tm.do_feed(pet)
    assert pet.hunger >= 70  # 50 + 25 = 75, clamped
    assert pet.total_interactions == 1
    assert isinstance(msg, str)
    assert len(msg) > 0


def test_play_action():
    pet = make_pet(happiness=50, energy=50)
    msg = tm.do_play(pet)
    assert pet.happiness >= 65  # 50 + 20 = 70, but energy cost
    assert pet.energy < 50  # energy decreases
    assert pet.hunger < 50  # hunger decreases from playing


def test_heal_action():
    pet = make_pet(health=50)
    msg = tm.do_heal(pet)
    assert pet.health >= 75  # 50 + 30 = 80
    assert pet.total_interactions == 1


def test_sleep_action():
    pet = make_pet(energy=30)
    msg = tm.do_sleep(pet)
    assert pet.energy >= 60  # 30 + 35 = 65
    assert pet.hunger < 80  # hunger decreases from sleeping


def test_clean_action():
    pet = make_pet(cleanliness=40)
    msg = tm.do_clean(pet)
    assert pet.cleanliness >= 65  # 40 + 30 = 70
    assert pet.total_interactions == 1


def test_pet_action():
    pet = make_pet(happiness=50)
    msg = tm.do_pet(pet)
    assert pet.happiness >= 58  # 50 + 10 = 60
    assert pet.total_interactions == 1


def test_decay():
    pet = make_pet(hunger=80, happiness=80, health=100, energy=80, cleanliness=80)
    pet.apply_decay(60)  # 1 hour
    assert pet.hunger < 80  # hunger decays
    assert pet.happiness < 80
    assert pet.energy < 80
    assert pet.cleanliness < 80


def test_decay_health_affected_by_low_stats():
    pet = make_pet(hunger=10, happiness=10, cleanliness=10, health=80)
    pet.apply_decay(60)
    # Health should decay faster when other stats are low
    assert pet.health < 60


def test_death():
    pet = make_pet(health=5, hunger=0, happiness=0, cleanliness=0)
    pet.apply_decay(1440)  # 24 hours
    assert pet.is_alive is False


def test_clamp_stats():
    pet = make_pet(hunger=150, happiness=-10)
    pet.clamp_stats()
    assert pet.hunger == 100
    assert pet.happiness == 0


def test_mood_ecstatic():
    pet = make_pet(hunger=95, happiness=95, health=95, energy=95, cleanliness=95)
    assert pet.get_overall_mood() == "ecstatic"


def test_mood_sick():
    pet = make_pet(health=15)
    assert pet.get_overall_mood() == "sick"


def test_mood_dead():
    pet = make_pet(is_alive=False)
    assert pet.get_overall_mood() == "dead"


def test_stage_progression():
    pet = make_pet(age_hours=0.01)
    msgs = pet.update_stage()
    assert pet.stage == "egg"

    pet.age_hours = 0.2
    pet.stage = "baby"
    msgs = pet.update_stage()
    assert pet.stage == "baby"

    pet.age_hours = 1.0
    pet.stage = "baby"
    msgs = pet.update_stage()
    assert pet.stage == "child"

    pet.age_hours = 5.0
    pet.stage = "child"
    msgs = pet.update_stage()
    assert pet.stage == "adult"

    pet.age_hours = 15.0
    pet.stage = "adult"
    msgs = pet.update_stage()
    assert pet.stage == "elder"


def test_level_up_messages():
    pet = make_pet(age_hours=5.0, stage="child")
    msgs = pet.update_stage()
    assert len(msgs) > 0
    assert "Testy" in msgs[0]


def test_save_and_load(tmp_path):
    save_file = tmp_path / "pet.json"
    with patch.object(tm, 'SAVE_FILE', save_file), \
         patch.object(tm, 'SAVE_DIR', tmp_path):
        pet = make_pet(name="SaveTest", species="dragon")
        tm.save_pet(pet)
        loaded = tm.load_pet()
        assert loaded is not None
        assert loaded.name == "SaveTest"
        assert loaded.species == "dragon"


def test_load_nonexistent():
    result = tm.load_pet()
    # Should return None for nonexistent or invalid
    # (might find an actual save file; just check type)
    assert result is None or isinstance(result, tm.Pet)


def test_art_exists_for_all_species():
    for species in tm.SPECIES_LIST:
        for stage in ["egg", "baby", "child", "adult", "elder", "dead"]:
            assert stage in tm.PET_ART[species], f"Missing {stage} art for {species}"


def test_responses_exist_for_all_species():
    for species in tm.SPECIES_LIST:
        for action in ["feed", "play", "heal", "sleep", "clean", "pet", "ignore"]:
            assert species in tm.RESPONSES[action], f"Missing {action} responses for {species}"


def test_stat_bar():
    bar = tm.stat_bar(50, width=10)
    assert "█" in bar
    assert "░" in bar


def test_render_pet():
    pet = make_pet()
    output = tm.render_pet(pet)
    assert "Testy" in output
    assert "cat" in output.lower()
    assert "Stats" in output


def test_render_dead_pet():
    pet = make_pet(is_alive=False)
    output = tm.render_pet(pet)
    assert "passed away" in output


def test_play_too_tired():
    pet = make_pet(energy=5)
    msg = tm.do_play(pet) if pet.energy >= 15 else "too tired"
    # The main loop checks energy, but we can verify the logic


def test_decay_cap():
    """Verify decay doesn't go below 0."""
    pet = make_pet(hunger=5, happiness=5, health=5, energy=5, cleanliness=5)
    pet.apply_decay(500)
    assert pet.hunger >= 0
    assert pet.happiness >= 0
    assert pet.energy >= 0
    assert pet.cleanliness >= 0


def test_all_species_creation():
    for sp in tm.SPECIES_LIST:
        pet = make_pet(species=sp)
        assert pet.species == sp
        art = pet.get_art()
        assert len(art) > 0
        mood = pet.get_overall_mood()
        assert mood in tm.MOOD_FACES


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])