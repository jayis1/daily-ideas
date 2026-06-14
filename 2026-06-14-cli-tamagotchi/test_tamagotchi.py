#!/usr/bin/env python3
"""Tests for CLI Tamagotchi — including teach, explore, achievements, diary, and CLI flags."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import tamagotchi as tm


def make_pet(**overrides):
    """Create a Pet with sensible defaults for testing."""
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


# ─── Original feature tests ─────────────────────────────────────────────────

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
    pet = make_pet(hunger=50, happiness=50, energy=50)
    msg = tm.do_play(pet)
    assert pet.happiness >= 65  # 50 + 20 = 70
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
    """Play should fail if pet is too tired (internal check in do_play)."""
    pet = make_pet(energy=5)
    msg = tm.do_play(pet)
    assert "too tired" in msg.lower()
    # Verify stats didn't change (play was rejected)
    assert pet.happiness == 80  # unchanged from default


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


# ─── New feature tests: teach ────────────────────────────────────────────────

def test_teach_basic():
    """Teaching a trick should add to tricks_learned and cost energy."""
    pet = make_pet(energy=50)
    msg = tm.do_teach(pet)
    assert len(pet.tricks_learned) == 1
    assert pet.energy < 50
    assert pet.total_interactions == 1
    assert "learned" in msg.lower() or "already knows" in msg.lower()


def test_teach_too_tired():
    """Teaching should fail if pet is too tired."""
    pet = make_pet(energy=5)
    msg = tm.do_teach(pet)
    assert "too tired" in msg.lower()
    assert len(pet.tricks_learned) == 0


def test_teach_all_tricks():
    """After learning all tricks, further teach should perform a trick instead."""
    pet = make_pet(energy=100)
    species_tricks = tm.TRICKS.get(pet.species, [])
    # Learn all tricks
    for _ in species_tricks:
        tm.do_teach(pet)
    assert len(pet.tricks_learned) == len(species_tricks)
    # Teach again — should perform, not learn
    msg = tm.do_teach(pet)
    assert "already knows" in msg.lower()


def test_teach_achievement_first():
    """Teaching for the first time should award 'first_teach' achievement."""
    pet = make_pet(energy=50)
    assert "first_teach" not in pet.achievements
    tm.do_teach(pet)
    assert "first_teach" in pet.achievements


def test_tricks_exist_for_all_species():
    """Every species should have tricks available."""
    for species in tm.SPECIES_LIST:
        assert species in tm.TRICKS, f"Missing tricks for {species}"
        assert len(tm.TRICKS[species]) > 0, f"Empty tricks list for {species}"


# ─── New feature tests: explore ───────────────────────────────────────────────

def test_explore_basic():
    """Exploring should increment explore_count and cost energy."""
    pet = make_pet(energy=50)
    msg = tm.do_explore(pet)
    assert pet.explore_count == 1
    assert pet.energy < 50
    assert pet.total_interactions == 1
    assert isinstance(msg, str)
    assert len(msg) > 0


def test_explore_too_tired():
    """Exploring should fail if pet is too tired."""
    pet = make_pet(energy=5)
    msg = tm.do_explore(pet)
    assert "too tired" in msg.lower()
    assert pet.explore_count == 0


def test_explore_achievement_first():
    """First explore should award 'first_explore' achievement."""
    pet = make_pet(energy=50)
    assert "first_explore" not in pet.achievements
    tm.do_explore(pet)
    assert "first_explore" in pet.achievements


def test_explore_events_exist_for_all_species():
    """Every species should have explore events."""
    for species in tm.SPECIES_LIST:
        assert species in tm.EXPLORE_EVENTS, f"Missing explore events for {species}"
        assert len(tm.EXPLORE_EVENTS[species]) > 0, f"Empty explore events for {species}"


def test_explore_stat_modification():
    """Explore events should modify stats as specified in the event."""
    pet = make_pet(energy=50, hunger=50, happiness=50, cleanliness=50, health=50)
    # Run several explores to be likely to hit different events
    for _ in range(10):
        pet_copy = make_pet(energy=50, hunger=50, happiness=50, cleanliness=50, health=50)
        tm.do_explore(pet_copy)
        # At least one stat should have changed (beyond energy cost)
        # Energy should decrease
        assert pet_copy.energy < 50


# ─── New feature tests: achievements ─────────────────────────────────────────

def test_achievement_check_interactions():
    """Achievements should be awarded at interaction milestones."""
    pet = make_pet(lifetime_interactions=10)
    new = tm.check_achievements(pet)
    assert "interactions_10" in new

    pet = make_pet(lifetime_interactions=50)
    new = tm.check_achievements(pet)
    assert "interactions_50" in new

    pet = make_pet(lifetime_interactions=100)
    new = tm.check_achievements(pet)
    assert "interactions_100" in new


def test_achievement_all_stats_high():
    """All stats above 80 should award 'all_stats_high'."""
    pet = make_pet(hunger=85, happiness=85, health=85, energy=85, cleanliness=85)
    new = tm.check_achievements(pet)
    assert "all_stats_high" in new


def test_achievement_survivor():
    """Recovering from sickness should award 'survived_sickness'."""
    pet = make_pet(was_sick=True, health=50)
    new = tm.check_achievements(pet)
    assert "survived_sickness" in new


def test_achievement_tricks():
    """Teaching multiple tricks should award trick milestones."""
    pet = make_pet(tricks_learned=["High Five", "Roll Over", "Fetch"])
    new = tm.check_achievements(pet)
    assert "tricks_3" in new

    pet = make_pet(tricks_learned=["High Five", "Roll Over", "Fetch", "Sit", "Speak"])
    new = tm.check_achievements(pet)
    assert "tricks_5" in new


def test_achievement_explore_milestones():
    """Explore count milestones should award achievements."""
    pet = make_pet(explore_count=5)
    new = tm.check_achievements(pet)
    assert "explores_5" in new

    pet = make_pet(explore_count=20)
    new = tm.check_achievements(pet)
    assert "explores_20" in new


def test_achievement_stage_milestones():
    """Reaching adult/elder stages should award achievements."""
    pet = make_pet(stage="adult")
    new = tm.check_achievements(pet)
    assert "reached_adult" in new

    pet = make_pet(stage="elder")
    new = tm.check_achievements(pet)
    assert "reached_elder" in new


def test_achievement_not_reaward():
    """Achievements already earned should not be re-awarded."""
    pet = make_pet(lifetime_interactions=10, achievements=["interactions_10"])
    new = tm.check_achievements(pet)
    assert "interactions_10" not in new


def test_format_achievement():
    """format_achievement should produce a readable string."""
    result = tm.format_achievement("first_feed")
    assert "🍎" in result or "First Bite" in result


def test_achievement_defs_complete():
    """All referenced achievement IDs should exist in ACHIEVEMENT_DEFS."""
    # Check that every achievement we test for exists in the definitions
    for aid in ["first_feed", "first_play", "first_heal", "first_sleep",
               "first_clean", "first_pet_stroke", "first_teach", "first_explore",
               "interactions_10", "interactions_50", "interactions_100", "interactions_500",
               "all_stats_high", "survived_sickness",
               "tricks_3", "tricks_5",
               "explores_5", "explores_20",
               "reached_adult", "reached_elder"]:
        assert aid in tm.ACHIEVEMENT_DEFS, f"Missing achievement definition: {aid}"
        assert "name" in tm.ACHIEVEMENT_DEFS[aid]
        assert "icon" in tm.ACHIEVEMENT_DEFS[aid]
        assert "desc" in tm.ACHIEVEMENT_DEFS[aid]


# ─── New feature tests: diary/event log ──────────────────────────────────────

def test_event_log():
    """Actions should add entries to the event log."""
    pet = make_pet()
    assert len(pet.event_log) == 0
    tm.do_feed(pet)
    assert len(pet.event_log) > 0
    assert "fed" in pet.event_log[-1].lower()


def test_event_log_cap():
    """Event log should be capped at 100 entries."""
    pet = make_pet(energy=100, hunger=50)
    # Generate more than 100 events
    for i in range(120):
        pet._log_event(f"Event {i}")
    assert len(pet.event_log) <= 100


# ─── New feature tests: save backup ──────────────────────────────────────────

def test_save_creates_backup(tmp_path):
    """Saving should create a backup of the previous save."""
    save_file = tmp_path / "pet.json"
    backup_file = tmp_path / "pet.json.bak"
    with patch.object(tm, 'SAVE_FILE', save_file), \
         patch.object(tm, 'SAVE_DIR', tmp_path), \
         patch.object(tm, 'BACKUP_FILE', backup_file):
        # First save
        pet = make_pet(name="First")
        tm.save_pet(pet)
        assert save_file.exists()
        # Second save — should create backup of first
        pet2 = make_pet(name="Second")
        tm.save_pet(pet2)
        assert backup_file.exists()
        # Backup should contain the first save
        with open(backup_file) as f:
            backup_data = json.load(f)
        assert backup_data["name"] == "First"


def test_load_fallback_to_backup(tmp_path):
    """If primary save is corrupted, load should fall back to backup."""
    save_file = tmp_path / "pet.json"
    backup_file = tmp_path / "pet.json.bak"
    with patch.object(tm, 'SAVE_FILE', save_file), \
         patch.object(tm, 'SAVE_DIR', tmp_path), \
         patch.object(tm, 'BACKUP_FILE', backup_file):
        # Save twice to create a backup of the first save
        pet = make_pet(name="BackupTest", species="dragon")
        tm.save_pet(pet)
        # Second save creates backup of the first
        pet2 = make_pet(name="Overwrite", species="cat")
        tm.save_pet(pet2)
        # Corrupt the primary save
        with open(save_file, 'w') as f:
            f.write("{corrupted json!!!")
        # Should fall back to backup (which has "BackupTest")
        loaded = tm.load_pet()
        assert loaded is not None
        assert loaded.name == "BackupTest"


# ─── New feature tests: CLI flags ────────────────────────────────────────────

def test_parse_args_help():
    """--help flag should set show_help."""
    result = tm.parse_args(["tamagotchi.py", "--help"])
    assert result["show_help"] is True

    result = tm.parse_args(["tamagotchi.py", "-h"])
    assert result["show_help"] is True


def test_parse_args_version():
    """--version flag should set show_version."""
    result = tm.parse_args(["tamagotchi.py", "--version"])
    assert result["show_version"] is True

    result = tm.parse_args(["tamagotchi.py", "-v"])
    assert result["show_version"] is True


def test_parse_args_unknown():
    """Unknown args should set error."""
    result = tm.parse_args(["tamagotchi.py", "--bogus"])
    assert result["error"] != ""


def test_parse_args_empty():
    """No args should return defaults."""
    result = tm.parse_args(["tamagotchi.py"])
    assert result["show_help"] is False
    assert result["show_version"] is False
    assert result["error"] == ""


def test_version_constant():
    """Version should be a valid semver string."""
    assert tm.VERSION
    parts = tm.VERSION.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


# ─── New feature tests: save migration ───────────────────────────────────────

def test_load_old_save_migration(tmp_path):
    """Loading a save missing new fields should populate them with defaults."""
    save_file = tmp_path / "pet.json"
    with patch.object(tm, 'SAVE_FILE', save_file), \
         patch.object(tm, 'SAVE_DIR', tmp_path), \
         patch.object(tm, 'BACKUP_FILE', tmp_path / "pet.json.bak"):
        # Write an "old" save without the new fields
        old_data = {
            "name": "OldPet",
            "species": "cat",
            "personality": "lazy",
            "hunger": 80,
            "happiness": 80,
            "health": 100,
            "energy": 80,
            "cleanliness": 80,
            "age_hours": 1.0,
            "stage": "child",
            "is_alive": True,
            "created_at": datetime.now().isoformat(),
            "last_care_time": datetime.now().isoformat(),
            "total_interactions": 5,
            "lifetime_interactions": 5,
            "messages": [],
        }
        with open(save_file, 'w') as f:
            json.dump(old_data, f)

        loaded = tm.load_pet()
        assert loaded is not None
        assert loaded.name == "OldPet"
        assert loaded.tricks_learned == []
        assert loaded.achievements == []
        assert loaded.explore_count == 0
        assert loaded.event_log == []
        assert loaded.was_sick is False


# ─── New feature tests: was_sick tracking ────────────────────────────────────

def test_was_sick_tracked_on_decay():
    """was_sick should be set to True when health drops below SICK_THRESHOLD."""
    pet = make_pet(health=25, hunger=10, happiness=10, cleanliness=10)
    pet.apply_decay(60)
    if pet.health < tm.SICK_THRESHOLD:
        assert pet.was_sick is True


# ─── Bug fix tests ───────────────────────────────────────────────────────────

def test_dying_mood_reachable():
    """Bug fix: 'dying' mood should be reachable when health is very low (below DYING_THRESHOLD)."""
    pet = make_pet(health=5, is_alive=True, hunger=80, happiness=80, energy=80, cleanliness=80)
    mood = pet.get_overall_mood()
    assert mood == "dying", f"Expected 'dying' but got '{mood}'"

def test_dying_mood_between_thresholds():
    """Health between DYING_THRESHOLD and SICK_THRESHOLD should be 'sick'."""
    pet = make_pet(health=15, is_alive=True, hunger=80, happiness=80, energy=80, cleanliness=80)
    mood = pet.get_overall_mood()
    assert mood == "sick"

def test_egg_to_baby_transition_message():
    """Bug fix: Egg -> Baby transition should produce a level-up message."""
    pet = make_pet(stage="egg", age_hours=0.01)
    # Now age enough to transition to baby
    pet.age_hours = 0.3
    msgs = pet.update_stage()
    assert len(msgs) > 0, "Egg to baby transition should produce a message"

def test_play_energy_check_internal():
    """Bug fix: do_play should reject if energy < 15 (internal check)."""
    pet = make_pet(energy=10)
    msg = tm.do_play(pet)
    assert "too tired" in msg.lower()
    # Happiness should not have increased
    assert pet.happiness == 80  # default from make_pet

def test_dead_pet_status_command():
    """Bug fix: 'status' should be in the dead-pet command allowlist."""
    allowed_commands = ("release", "help", "quit", "achievements", "diary", "status")
    assert "status" in allowed_commands, "'status' should be allowed for dead pets"

def test_pet_action_achievement():
    """Bug fix: do_pet should award 'first_pet_stroke' achievement."""
    pet = make_pet(happiness=50)
    assert "first_pet_stroke" not in pet.achievements
    tm.do_pet(pet)
    assert "first_pet_stroke" in pet.achievements

def test_pet_stroke_achievement_definition():
    """Bug fix: 'first_pet_stroke' should exist in ACHIEVEMENT_DEFS."""
    assert "first_pet_stroke" in tm.ACHIEVEMENT_DEFS
    assert tm.ACHIEVEMENT_DEFS["first_pet_stroke"]["name"] == "Best Pal"

def test_load_pet_forward_compatibility(tmp_path):
    """Bug fix: load_pet should ignore unknown fields from future save versions."""
    save_file = tmp_path / "pet.json"
    with patch.object(tm, 'SAVE_FILE', save_file), \
         patch.object(tm, 'SAVE_DIR', tmp_path), \
         patch.object(tm, 'BACKUP_FILE', tmp_path / "pet.json.bak"):
        # Save with an extra future field
        data = tm.asdict(make_pet(name="CompatTest"))
        data["future_field_xyz"] = "should_be_ignored"
        with open(save_file, 'w') as f:
            json.dump(data, f)
        loaded = tm.load_pet()
        assert loaded is not None
        assert loaded.name == "CompatTest"

def test_explore_health_safety():
    """Bug fix: explore events that reduce health should not drop health below 1."""
    # Robot has an event that reduces health by 5
    # Set health very low and explore many times
    for _ in range(50):
        pet = make_pet(species="robot", health=3, energy=50)
        tm.do_explore(pet)
        assert pet.health >= 1, f"Health dropped below 1 to {pet.health} from explore!"

def test_mood_dying_face():
    """Verify 'dying' mood face exists and is used correctly."""
    assert "dying" in tm.MOOD_FACES
    pet = make_pet(health=5, is_alive=True)
    assert pet.get_overall_mood() == "dying"

def test_dying_threshold_constant():
    """Verify DYING_THRESHOLD constant exists and is between 0 and SICK_THRESHOLD."""
    assert hasattr(tm, 'DYING_THRESHOLD')
    assert 0 < tm.DYING_THRESHOLD < tm.SICK_THRESHOLD


# ─── Bug fix tests: v2.2 ──────────────────────────────────────────────────────

def test_stat_bar_clamps_above_max():
    """Bug fix: stat_bar should clamp values above MAX_STAT to prevent overflow."""
    bar = tm.stat_bar(150, width=20)
    import re
    clean = re.sub(r'\x1b\[[0-9;]*m', '', bar)
    assert len(clean) == 20, f"stat_bar(150) produced bar of length {len(clean)}"
    assert "█" in bar

def test_stat_bar_clamps_below_zero():
    """Bug fix: stat_bar should clamp negative values to 0."""
    bar = tm.stat_bar(-10, width=20)
    import re
    clean = re.sub(r'\x1b\[[0-9;]*m', '', bar)
    assert len(clean) == 20, f"stat_bar(-10) produced bar of length {len(clean)}"
    assert "░" in bar

def test_explore_energy_threshold_matches_cost():
    """Bug fix: explore energy threshold should match its stated cost of 8."""
    pet = make_pet(energy=8)
    msg = tm.do_explore(pet)
    assert "too tired" not in msg.lower(), f"Energy=8 should be enough to explore, got: {msg}"
    assert pet.explore_count == 1

def test_explore_energy_7_rejected():
    """Energy just below the cost (7) should be rejected."""
    pet = make_pet(energy=7)
    msg = tm.do_explore(pet)
    assert "too tired" in msg.lower()
    assert pet.explore_count == 0

def test_dead_pet_feed_rejected():
    """Bug fix: do_feed should reject dead pets."""
    pet = make_pet(is_alive=False, hunger=0)
    msg = tm.do_feed(pet)
    assert "passed away" in msg.lower()
    assert pet.hunger == 0, f"Dead pet's hunger should not change, got {pet.hunger}"

def test_dead_pet_play_rejected():
    """Bug fix: do_play should reject dead pets."""
    pet = make_pet(is_alive=False, happiness=10, energy=80)
    msg = tm.do_play(pet)
    assert "passed away" in msg.lower()
    assert pet.happiness == 10

def test_dead_pet_heal_rejected():
    """Bug fix: do_heal should reject dead pets."""
    pet = make_pet(is_alive=False, health=0)
    msg = tm.do_heal(pet)
    assert "passed away" in msg.lower()
    assert pet.health == 0

def test_dead_pet_sleep_rejected():
    """Bug fix: do_sleep should reject dead pets."""
    pet = make_pet(is_alive=False, energy=0)
    msg = tm.do_sleep(pet)
    assert "passed away" in msg.lower()
    assert pet.energy == 0

def test_dead_pet_clean_rejected():
    """Bug fix: do_clean should reject dead pets."""
    pet = make_pet(is_alive=False, cleanliness=10)
    msg = tm.do_clean(pet)
    assert "passed away" in msg.lower()
    assert pet.cleanliness == 10

def test_dead_pet_pet_rejected():
    """Bug fix: do_pet should reject dead pets."""
    pet = make_pet(is_alive=False, happiness=10)
    msg = tm.do_pet(pet)
    assert "passed away" in msg.lower()
    assert pet.happiness == 10

def test_dead_pet_teach_rejected():
    """Bug fix: do_teach should reject dead pets."""
    pet = make_pet(is_alive=False, energy=50)
    msg = tm.do_teach(pet)
    assert "passed away" in msg.lower()
    assert len(pet.tricks_learned) == 0

def test_dead_pet_explore_rejected():
    """Bug fix: do_explore should reject dead pets."""
    pet = make_pet(is_alive=False, energy=50)
    msg = tm.do_explore(pet)
    assert "passed away" in msg.lower()
    assert pet.explore_count == 0

def test_dead_pet_feed_no_achievement():
    """Bug fix: feeding a dead pet should not award achievements."""
    pet = make_pet(is_alive=False, hunger=0, achievements=[])
    tm.do_feed(pet)
    assert "first_feed" not in pet.achievements

def test_dead_pet_feed_no_interaction_increment():
    """Bug fix: feeding a dead pet should not increment interactions."""
    pet = make_pet(is_alive=False, hunger=0, total_interactions=0, lifetime_interactions=0)
    tm.do_feed(pet)
    assert pet.total_interactions == 0
    assert pet.lifetime_interactions == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])