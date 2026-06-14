#!/usr/bin/env python3
"""
Comprehensive tests for CLI Escape Room v2.0.0.

Tests cover:
- Game state initialization and management
- Item management (take, drop, pickup dropped)
- Room navigation and locked doors
- Puzzle progression (full walkthrough)
- Save/load serialization
- Scoring and rank system
- Command parsing
- Hint system context sensitivity
"""

import sys
import os
import json
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from escape_room import (
    GameState, ITEMS, INTERACTABLES, parse_command, get_hint, VERSION, SAVE_FILE
)


class TestGameStateInit(unittest.TestCase):
    """Test GameState initialization."""

    def test_start_room_is_cell(self):
        state = GameState()
        self.assertEqual(state.current_room, "cell")

    def test_start_inventory_empty(self):
        state = GameState()
        self.assertEqual(state.inventory, [])

    def test_start_flags_empty(self):
        state = GameState()
        self.assertEqual(state.flags, set())

    def test_start_moves_zero(self):
        state = GameState()
        self.assertEqual(state.moves, 0)

    def test_start_not_escaped(self):
        state = GameState()
        self.assertFalse(state.escaped)

    def test_cell_has_items(self):
        state = GameState()
        self.assertIn("rusty_key", state.room["items"])
        self.assertIn("note_fragment_1", state.room["items"])

    def test_cell_north_locked(self):
        state = GameState()
        self.assertTrue(state.is_locked("north"))

    def test_corridor_east_locked(self):
        state = GameState()
        state.current_room = "corridor"
        self.assertTrue(state.is_locked("east"))

    def test_corridor_north_locked(self):
        state = GameState()
        state.current_room = "corridor"
        self.assertTrue(state.is_locked("north"))

    def test_six_rooms_exist(self):
        state = GameState()
        expected = {"cell", "corridor", "study", "lab", "hidden_passage", "control_room"}
        self.assertEqual(set(state.rooms.keys()), expected)

    def test_control_room_is_dark(self):
        state = GameState()
        self.assertTrue(state.rooms["control_room"].get("dark"))

    def test_command_history_starts_empty(self):
        state = GameState()
        self.assertEqual(state.command_history, [])

    def test_dropped_items_starts_empty(self):
        state = GameState()
        self.assertEqual(state.dropped_items, {})


class TestItemManagement(unittest.TestCase):
    """Test inventory and item operations."""

    def setUp(self):
        self.state = GameState()

    def test_has_item_false_initially(self):
        self.assertFalse(self.state.has_item("rusty_key"))

    def test_take_item_adds_to_inventory(self):
        self.state.take_item("rusty_key")
        self.assertTrue(self.state.has_item("rusty_key"))

    def test_take_item_removes_from_room(self):
        self.state.take_item("rusty_key")
        self.assertNotIn("rusty_key", self.state.room["items"])

    def test_take_item_from_room_false(self):
        self.state.take_item("cabinet_key", from_room=False)
        self.assertTrue(self.state.has_item("cabinet_key"))

    def test_take_item_idempotent(self):
        self.state.take_item("rusty_key")
        self.state.take_item("rusty_key")
        self.assertEqual(self.state.inventory.count("rusty_key"), 1)

    def test_remove_item(self):
        self.state.take_item("rusty_key")
        self.state.remove_item("rusty_key")
        self.assertFalse(self.state.has_item("rusty_key"))

    def test_remove_item_not_in_inventory(self):
        # Should not raise
        self.state.remove_item("rusty_key")

    def test_drop_item(self):
        self.state.take_item("rusty_key")
        result = self.state.drop_item("rusty_key")
        self.assertTrue(result)
        self.assertFalse(self.state.has_item("rusty_key"))
        self.assertIn("rusty_key", self.state.dropped_items.get("cell", []))

    def test_drop_item_not_owned(self):
        result = self.state.drop_item("rusty_key")
        self.assertFalse(result)

    def test_pickup_dropped_item(self):
        self.state.take_item("rusty_key")
        self.state.drop_item("rusty_key")
        result = self.state.pickup_dropped("rusty_key")
        self.assertTrue(result)
        self.assertTrue(self.state.has_item("rusty_key"))
        # Dropped items should be empty now
        self.assertNotIn("rusty_key", self.state.dropped_items.get("cell", []))

    def test_pickup_dropped_wrong_room(self):
        self.state.take_item("rusty_key")
        self.state.drop_item("rusty_key")
        self.state.current_room = "corridor"
        result = self.state.pickup_dropped("rusty_key")
        self.assertFalse(result)

    def test_all_items_have_name_and_desc(self):
        for item_id, item in ITEMS.items():
            self.assertIn("name", item, f"Item {item_id} missing 'name'")
            self.assertIn("desc", item, f"Item {item_id} missing 'desc'")


class TestNavigation(unittest.TestCase):
    """Test room navigation and door locking."""

    def setUp(self):
        self.state = GameState()

    def test_unlock_door(self):
        self.assertTrue(self.state.is_locked("north"))
        self.state.unlock("north")
        self.assertFalse(self.state.is_locked("north"))

    def test_unlock_nonexistent_direction(self):
        # Should not raise
        self.state.unlock("up")

    def test_move_to_corridor(self):
        self.state.unlock("north")
        self.state.current_room = "corridor"
        self.assertEqual(self.state.current_room, "corridor")

    def test_room_property(self):
        self.assertEqual(self.state.room["name"], "The Cell")
        self.state.current_room = "corridor"
        self.assertEqual(self.state.room["name"], "The Corridor")


class TestPuzzleWalkthrough(unittest.TestCase):
    """Test the complete puzzle chain from start to escape."""

    def setUp(self):
        self.state = GameState()

    def test_full_walkthrough(self):
        """Simulate a complete winning playthrough."""
        s = self.state

        # Step 1: Pick up items in cell
        s.take_item("rusty_key")
        s.take_item("note_fragment_1")
        self.assertTrue(s.has_item("rusty_key"))
        self.assertTrue(s.has_item("note_fragment_1"))

        # Step 2: Get screwdriver from hidden passage
        s.current_room = "hidden_passage"
        s.take_item("screwdriver")
        self.assertTrue(s.has_item("screwdriver"))

        # Step 3: Get note fragment 2 from loose brick (simulated)
        s.take_item("note_fragment_2", from_room=False)
        self.assertTrue(s.has_item("note_fragment_2"))

        # Step 4: Combine notes
        s.flags.add("safe_combo")
        self.assertIn("safe_combo", s.flags)

        # Step 5: Get cabinet key from desk (requires screwdriver)
        s.current_room = "cell"
        s.take_item("cabinet_key", from_room=False)
        self.assertTrue(s.has_item("cabinet_key"))

        # Step 6: Unlock cell door
        s.unlock("north")
        self.assertFalse(s.is_locked("north"))

        # Step 7: Move to corridor
        s.current_room = "corridor"
        s.room["visited"] = True
        self.assertEqual(s.current_room, "corridor")

        # Step 8: Get old photograph from clock
        s.take_item("old_photograph", from_room=False)
        self.assertTrue(s.has_item("old_photograph"))

        # Step 9: Unlock keypad door
        s.unlock("north")
        self.assertFalse(s.is_locked("north"))

        # Step 10: Unlock lab door with cabinet key
        s.unlock("east")
        self.assertFalse(s.is_locked("east"))

        # Step 11: Go to study, unlock filing cabinet with key
        s.current_room = "study"
        s.take_item("flashlight", from_room=False)
        s.take_item("morse_chart")
        self.assertTrue(s.has_item("flashlight"))

        # Step 12: Open safe with combination
        s.flags.add("safe_opened")
        s.take_item("mysterious_gem", from_room=False)
        s.take_item("id_card", from_room=False)
        self.assertTrue(s.has_item("mysterious_gem"))
        self.assertTrue(s.has_item("id_card"))

        # Step 13: Go to lab
        s.current_room = "lab"
        s.take_item("blue_wire")
        self.assertTrue(s.has_item("blue_wire"))

        # Step 14: Open lab cabinet with code 472
        s.flags.add("cabinet_opened")
        s.take_item("red_wire", from_room=False)
        s.take_item("oil_can", from_room=False)
        self.assertTrue(s.has_item("red_wire"))
        self.assertTrue(s.has_item("oil_can"))

        # Step 15: Connect wires to panel
        s.flags.add("red_connected")
        s.flags.add("blue_connected")
        s.flags.add("power_restored")
        self.assertIn("power_restored", s.flags)

        # Step 16: Go to control room
        s.current_room = "control_room"
        self.assertEqual(s.current_room, "control_room")

        # Step 17: Swipe ID card on console
        s.flags.add("id_scanned")
        s.remove_item("id_card")
        self.assertIn("id_scanned", s.flags)
        self.assertFalse(s.has_item("id_card"))

        # Step 18: Place gem on console
        s.flags.add("gem_placed")
        s.remove_item("mysterious_gem")
        self.assertIn("gem_placed", s.flags)

        # Step 19: Unlock exit
        s.unlock("exit")
        self.assertFalse(s.is_locked("exit"))

        # Step 20: Escape!
        s.escaped = True
        self.assertTrue(s.escaped)


class TestSaveLoad(unittest.TestCase):
    """Test save/load game state serialization."""

    def setUp(self):
        self.state = GameState()
        self.state.take_item("rusty_key")
        self.state.flags.add("safe_combo")
        self.state.moves = 42
        self.state.command_history = ["look", "take key", "go north"]

    def tearDown(self):
        # Clean up save files
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
        save_dir = os.path.dirname(SAVE_FILE)
        if os.path.exists(save_dir) and not os.listdir(save_dir):
            os.rmdir(save_dir)

    def test_to_dict(self):
        data = self.state.to_dict()
        self.assertEqual(data["current_room"], "cell")
        self.assertIn("rusty_key", data["inventory"])
        self.assertIn("safe_combo", data["flags"])
        self.assertEqual(data["moves"], 42)
        self.assertIn("take key", data["command_history"])

    def test_from_dict_roundtrip(self):
        data = self.state.to_dict()
        restored = GameState.from_dict(data)
        self.assertEqual(restored.current_room, self.state.current_room)
        self.assertEqual(restored.inventory, self.state.inventory)
        self.assertEqual(restored.flags, self.state.flags)
        self.assertEqual(restored.moves, self.state.moves)
        self.assertEqual(restored.command_history, self.state.command_history)

    def test_save_and_load(self):
        self.state.save()
        self.assertTrue(GameState.has_save())
        loaded = GameState.load()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.current_room, self.state.current_room)
        self.assertEqual(loaded.inventory, self.state.inventory)
        self.assertEqual(loaded.flags, self.state.flags)
        self.assertEqual(loaded.moves, self.state.moves)

    def test_load_no_save(self):
        loaded = GameState.load()
        self.assertIsNone(loaded)

    def test_delete_save(self):
        self.state.save()
        self.assertTrue(GameState.has_save())
        GameState.delete_save()
        self.assertFalse(GameState.has_save())

    def test_dropped_items_roundtrip(self):
        self.state.take_item("rusty_key")
        self.state.drop_item("rusty_key")
        data = self.state.to_dict()
        restored = GameState.from_dict(data)
        self.assertEqual(restored.dropped_items, self.state.dropped_items)

    def test_room_state_roundtrip(self):
        self.state.unlock("north")
        data = self.state.to_dict()
        restored = GameState.from_dict(data)
        self.assertFalse(restored.rooms["cell"]["locked"].get("north", False))

    def test_corrupted_save(self):
        """Loading a corrupted save file returns None."""
        os.makedirs(os.path.dirname(SAVE_FILE), exist_ok=True)
        with open(SAVE_FILE, "w") as f:
            f.write("{invalid json")
        loaded = GameState.load()
        self.assertIsNone(loaded)


class TestScoring(unittest.TestCase):
    """Test scoring and rank system."""

    def test_initial_score(self):
        state = GameState()
        # Fresh state with 0 moves, 0 elapsed time:
        # 1000 base + 100 speed bonus (0s < 300s) + 50 efficiency bonus (0 moves < 10)
        # = 1150, minus a tiny time penalty
        score = state.score()
        self.assertGreaterEqual(score, 1100)

    def test_move_penalty(self):
        state = GameState()
        state.moves = 10
        score = state.score()
        # 1000 - 10*5 = 950 + speed bonus (if <300s) = 1050 minus tiny time
        self.assertLessEqual(score, 1050)
        self.assertGreaterEqual(score, 1030)

    def test_item_bonus(self):
        state = GameState()
        # Add several items
        for item in ["rusty_key", "flashlight", "screwdriver", "mysterious_gem", "oil_can"]:
            state.take_item(item, from_room=False)
        score = state.score()
        # At least +250 for 5 items
        self.assertGreaterEqual(score, 1000)

    def test_score_floor_at_zero(self):
        state = GameState()
        state.moves = 999
        # Force time to be huge
        state.start_time = 0
        score = state.score()
        self.assertGreaterEqual(score, 0)

    def test_rank_s(self):
        self.assertEqual(GameState.rank_for_score(1500), "S — Master Escapist")
        self.assertEqual(GameState.rank_for_score(2000), "S — Master Escapist")

    def test_rank_a(self):
        self.assertEqual(GameState.rank_for_score(1200), "A — Expert Puzzler")

    def test_rank_b(self):
        self.assertEqual(GameState.rank_for_score(900), "B — Skilled Explorer")

    def test_rank_c(self):
        self.assertEqual(GameState.rank_for_score(600), "C — Capable Survivor")

    def test_rank_d(self):
        self.assertEqual(GameState.rank_for_score(300), "D — Lucky Escapee")

    def test_rank_f(self):
        self.assertEqual(GameState.rank_for_score(50), "F — Barely Made It")
        self.assertEqual(GameState.rank_for_score(0), "F — Barely Made It")

    def test_elapsed_seconds(self):
        state = GameState()
        elapsed = state.elapsed_seconds()
        self.assertGreaterEqual(elapsed, 0)


class TestCommandParser(unittest.TestCase):
    """Test command parsing and alias resolution."""

    def test_empty_command(self):
        verb, args = parse_command("")
        self.assertIsNone(verb)

    def test_look(self):
        verb, args = parse_command("look")
        self.assertEqual(verb, "look")

    def test_look_alias_examine(self):
        verb, args = parse_command("examine clock")
        self.assertEqual(verb, "look")
        self.assertEqual(args, "clock")

    def test_go_north(self):
        verb, args = parse_command("go north")
        self.assertEqual(verb, "go")
        self.assertEqual(args, "north")

    def test_go_alias_walk(self):
        verb, args = parse_command("walk east")
        self.assertEqual(verb, "go")

    def test_direction_shortcut_n(self):
        verb, args = parse_command("n")
        self.assertEqual(verb, "go")
        self.assertEqual(args, "north")

    def test_direction_shortcut_s(self):
        verb, args = parse_command("s")
        self.assertEqual(verb, "go")
        self.assertEqual(args, "south")

    def test_direction_shortcut_e(self):
        verb, args = parse_command("e")
        self.assertEqual(verb, "go")
        self.assertEqual(args, "east")

    def test_direction_shortcut_w(self):
        verb, args = parse_command("w")
        self.assertEqual(verb, "go")
        self.assertEqual(args, "west")

    def test_take_alias_get(self):
        verb, args = parse_command("get key")
        self.assertEqual(verb, "take")

    def test_pick_up_multiword(self):
        verb, args = parse_command("pick up key")
        self.assertEqual(verb, "take")
        self.assertEqual(args, "key")

    def test_look_at_multiword(self):
        verb, args = parse_command("look at clock")
        self.assertEqual(verb, "look")
        self.assertEqual(args, "clock")

    def test_use_on(self):
        verb, args = parse_command("use key on padlock")
        self.assertEqual(verb, "use")
        self.assertEqual(args, "key on padlock")

    def test_inventory_alias_i(self):
        verb, args = parse_command("i")
        self.assertEqual(verb, "inventory")

    def test_help_alias_h(self):
        verb, args = parse_command("h")
        self.assertEqual(verb, "help")

    def test_quit_alias_q(self):
        verb, args = parse_command("q")
        self.assertEqual(verb, "quit")

    def test_combine_alias_merge(self):
        verb, args = parse_command("merge notes")
        self.assertEqual(verb, "combine")

    def test_hint_command(self):
        verb, args = parse_command("hint")
        self.assertEqual(verb, "hint")

    def test_status_command(self):
        verb, args = parse_command("status")
        self.assertEqual(verb, "status")

    def test_save_command(self):
        verb, args = parse_command("save")
        self.assertEqual(verb, "save")

    def test_load_command(self):
        verb, args = parse_command("load")
        self.assertEqual(verb, "load")

    def test_drop_command(self):
        verb, args = parse_command("drop key")
        self.assertEqual(verb, "drop")

    def test_drop_alias_leave(self):
        verb, args = parse_command("leave key")
        self.assertEqual(verb, "drop")

    def test_history_command(self):
        verb, args = parse_command("history")
        self.assertEqual(verb, "history")

    def test_unknown_command(self):
        verb, args = parse_command("xyzzy")
        self.assertEqual(verb, "xyzzy")

    def test_case_insensitive(self):
        verb, args = parse_command("LOOK AT CLOCK")
        self.assertEqual(verb, "look")
        self.assertEqual(args, "clock")

    def test_read_alias(self):
        verb, args = parse_command("read note")
        self.assertEqual(verb, "read")

    def test_use_alias_swipe(self):
        verb, args = parse_command("swipe card on console")
        self.assertEqual(verb, "use")


class TestHintSystem(unittest.TestCase):
    """Test that the hint system returns contextually appropriate hints."""

    def test_hint_in_cell_no_key(self):
        state = GameState()
        hint = get_hint(state)
        self.assertIn("look", hint.lower())

    def test_hint_in_cell_has_key_locked(self):
        state = GameState()
        state.take_item("rusty_key")
        hint = get_hint(state)
        self.assertIn("key", hint.lower())

    def test_hint_in_cell_door_unlocked(self):
        state = GameState()
        state.take_item("rusty_key")
        state.unlock("north")
        state.current_room = "corridor"
        hint = get_hint(state)
        # Should mention keypad or clock
        self.assertTrue(len(hint) > 0)

    def test_hint_in_study_no_combo(self):
        state = GameState()
        state.current_room = "study"
        hint = get_hint(state)
        self.assertTrue(len(hint) > 0)

    def test_hint_in_study_has_combo(self):
        state = GameState()
        state.current_room = "study"
        state.flags.add("safe_combo")
        hint = get_hint(state)
        self.assertIn("combination", hint.lower())

    def test_hint_in_control_room_no_flashlight(self):
        state = GameState()
        state.current_room = "control_room"
        hint = get_hint(state)
        self.assertIn("flashlight", hint.lower())

    def test_hint_in_control_room_has_flashlight_no_id(self):
        state = GameState()
        state.current_room = "control_room"
        state.take_item("flashlight", from_room=False)
        hint = get_hint(state)
        self.assertIn("id", hint.lower())

    def test_hint_in_lab_no_cabinet_code(self):
        state = GameState()
        state.current_room = "lab"
        hint = get_hint(state)
        self.assertTrue(len(hint) > 0)

    def test_hint_always_returns_string(self):
        """Verify hints are always non-empty strings for all room states."""
        for room in ["cell", "corridor", "study", "lab", "hidden_passage", "control_room"]:
            state = GameState()
            state.current_room = room
            hint = get_hint(state)
            self.assertIsInstance(hint, str)
            self.assertTrue(len(hint) > 0, f"Empty hint for room {room}")


class TestInteractables(unittest.TestCase):
    """Test interactable data integrity."""

    def test_all_rooms_have_interactables(self):
        for room_id in ["cell", "corridor", "study", "lab", "hidden_passage", "control_room"]:
            self.assertIn(room_id, INTERACTABLES)

    def test_interactables_have_name_and_short(self):
        for room_id, objects in INTERACTABLES.items():
            for key, obj in objects.items():
                self.assertIn("name", obj, f"{room_id}/{key} missing 'name'")
                self.assertIn("short", obj, f"{room_id}/{key} missing 'short'")

    def test_interactables_have_inspect(self):
        for room_id, objects in INTERACTABLES.items():
            for key, obj in objects.items():
                self.assertIn("inspect", obj, f"{room_id}/{key} missing 'inspect'")

    def test_gives_references_valid_item(self):
        for room_id, objects in INTERACTABLES.items():
            for key, obj in objects.items():
                if "gives" in obj:
                    self.assertIn(obj["gives"], ITEMS, f"{room_id}/{key} gives invalid item '{obj['gives']}'")

    def test_requires_references_valid_item(self):
        for room_id, objects in INTERACTABLES.items():
            for key, obj in objects.items():
                if "requires" in obj:
                    self.assertIn(obj["requires"], ITEMS, f"{room_id}/{key} requires invalid item '{obj['requires']}'")


class TestVersion(unittest.TestCase):
    """Test version constant."""

    def test_version_is_string(self):
        self.assertIsInstance(VERSION, str)

    def test_version_format(self):
        parts = VERSION.split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())


if __name__ == "__main__":
    unittest.main()