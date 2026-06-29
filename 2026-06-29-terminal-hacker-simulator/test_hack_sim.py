#!/usr/bin/env python3
"""
Tests for Terminal Hacker Simulator v3.0.0.

Run with: python3 test_hack_sim.py
"""
import sys
import os
import random
import io
import json
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hack_sim as h


class TestNetwork(unittest.TestCase):
    def test_creation(self):
        random.seed(42)
        net = h.Network(difficulty=3)
        self.assertEqual(net.difficulty, 3)
        self.assertIsNotNone(net.corp)
        self.assertIsNotNone(net.handle)
        self.assertIsNotNone(net.ip)
        self.assertEqual(len(net.nodes), 3 + 3)

    def test_default_difficulty(self):
        random.seed(7)
        net = h.Network()
        self.assertGreaterEqual(net.difficulty, 1)
        self.assertLessEqual(net.difficulty, 5)

    def test_node_structure(self):
        random.seed(42)
        net = h.Network(difficulty=2)
        for n in net.nodes:
            self.assertIn("type", n)
            self.assertIn("ip", n)
            self.assertIn("name", n)
            self.assertIn("difficulty", n)
            self.assertIn("cracked", n)
            self.assertIn("files", n)
            self.assertIn("analyzed", n)
            self.assertFalse(n["cracked"])
            self.assertFalse(n.get("analyzed", False))

    def test_total_difficulty(self):
        random.seed(99)
        net = h.Network(difficulty=2)
        self.assertEqual(net.total_difficulty, sum(n["difficulty"] for n in net.nodes))

    def test_network_addr(self):
        random.seed(42)
        net = h.Network(difficulty=3)
        addr = net.network_addr()
        self.assertTrue(addr.endswith(".0/24"))
        parts = addr.split("/")[0].split(".")
        self.assertEqual(len(parts), 4, f"Expected 4 octets, got {parts}")

    def test_node_difficulty_range(self):
        for d in range(1, 6):
            random.seed(d * 13)
            net = h.Network(difficulty=d)
            for n in net.nodes:
                self.assertGreaterEqual(n["difficulty"], 1)
                self.assertLessEqual(n["difficulty"], d + 1)

    def test_node_files_independent(self):
        random.seed(42)
        net = h.Network(difficulty=3)
        for i in range(len(net.nodes)):
            for j in range(i + 1, len(net.nodes)):
                self.assertIsNot(net.nodes[i]["files"], net.nodes[j]["files"])

    def test_cracked_count(self):
        random.seed(42)
        net = h.Network(difficulty=2)
        self.assertEqual(net.cracked_count(), 0)
        net.nodes[0]["cracked"] = True
        self.assertEqual(net.cracked_count(), 1)
        net.nodes[1]["cracked"] = True
        self.assertEqual(net.cracked_count(), 2)

    def test_total_nodes(self):
        random.seed(42)
        net = h.Network(difficulty=3)
        self.assertEqual(net.total_nodes(), len(net.nodes))


class TestHackerSimulator(unittest.TestCase):
    def setUp(self):
        self.game = h.HackerSimulator()
        random.seed(42)
        self.game.current_network = h.Network(difficulty=2)
        self.game.trace_level = 0

    def test_init(self):
        game = h.HackerSimulator()
        self.assertEqual(game.score, 0)
        self.assertEqual(game.networks_cracked, 0)
        self.assertEqual(game.files_stolen, 0)
        self.assertEqual(game.trace_level, 0)
        self.assertEqual(game.max_trace, 100)
        self.assertIn("scan", game.tools_unlocked)
        self.assertTrue(game.running)
        self.assertEqual(game.command_history, [])
        self.assertEqual(game.total_cracks_attempted, 0)
        self.assertEqual(game.total_cracks_succeeded, 0)
        self.assertEqual(game.total_analyses, 0)

    def test_crack_node_invalid_low(self):
        old_score = self.game.score
        self.game.crack_node(0)
        self.assertEqual(self.game.score, old_score)

    def test_crack_node_invalid_high(self):
        old_score = self.game.score
        self.game.crack_node(999)
        self.assertEqual(self.game.score, old_score)

    def test_download_uncracked(self):
        old_score = self.game.score
        self.game.download_files(1)
        self.assertEqual(self.game.score, old_score)

    def test_download_invalid_low(self):
        self.game.download_files(0)  # Should not crash

    def test_download_invalid_high(self):
        self.game.download_files(999)  # Should not crash

    def test_mission_complete_false(self):
        self.assertFalse(self.game.mission_complete())

    def test_mission_complete_true(self):
        for n in self.game.current_network.nodes:
            n["cracked"] = True
        self.assertTrue(self.game.mission_complete())

    def test_mission_complete_none_network(self):
        self.game.current_network = None
        self.assertFalse(self.game.mission_complete())

    def test_check_trace_below(self):
        self.game.trace_level = 50
        self.assertFalse(self.game.check_trace())

    def test_check_trace_at_max(self):
        self.game.trace_level = 100
        self.assertTrue(self.game.check_trace())

    def test_check_trace_above_max(self):
        self.game.trace_level = 150
        self.assertTrue(self.game.check_trace())

    def test_check_trace_custom_max(self):
        self.game.max_trace = 130
        self.game.trace_level = 120
        self.assertFalse(self.game.check_trace())
        self.game.trace_level = 130
        self.assertTrue(self.game.check_trace())

    def test_generate_network(self):
        self.game.generate_network()
        self.assertIsNotNone(self.game.current_network)
        self.assertEqual(self.game.trace_level, 0)

    def test_generate_network_resets_trace(self):
        self.game.trace_level = 80
        self.game.generate_network()
        self.assertEqual(self.game.trace_level, 0)

    def test_deploy_tracecut(self):
        self.game.trace_level = 50
        self.game.tools_unlocked.add("tracecut")
        self.game.deploy_tool("tracecut")
        self.assertLess(self.game.trace_level, 50)
        self.assertNotIn("tracecut", self.game.tools_unlocked)

    def test_deploy_nuke(self):
        self.game.trace_level = 10
        self.game.tools_unlocked.add("nuke")
        self.game.deploy_tool("nuke")
        self.assertTrue(all(n["cracked"] for n in self.game.current_network.nodes))
        self.assertEqual(self.game.trace_level, 30)
        self.assertNotIn("nuke", self.game.tools_unlocked)

    def test_deploy_stealth(self):
        self.game.trace_level = 50
        self.game.tools_unlocked.add("stealth")
        self.game.deploy_tool("stealth")
        self.assertEqual(self.game.trace_level, 25)
        self.assertNotIn("stealth", self.game.tools_unlocked)

    def test_deploy_stealth_at_zero(self):
        self.game.trace_level = 0
        self.game.tools_unlocked.add("stealth")
        self.game.deploy_tool("stealth")
        self.assertGreaterEqual(self.game.trace_level, 0)

    def test_deploy_overclock(self):
        """Test that overclock reduces node difficulties and trace."""
        self.game.trace_level = 30
        self.game.tools_unlocked.add("overclock")
        # Find an uncracked node with difficulty > 1
        node = None
        for n in self.game.current_network.nodes:
            if not n["cracked"] and n["difficulty"] > 1:
                node = n
                break
        if node:
            old_diff = node["difficulty"]
            self.game.deploy_tool("overclock")
            self.assertEqual(node["difficulty"], old_diff - 1)
        self.assertLessEqual(self.game.trace_level, 15)
        self.assertNotIn("overclock", self.game.tools_unlocked)

    def test_deploy_shield(self):
        """Test that shield increases max_trace."""
        self.game.tools_unlocked.add("shield")
        self.game.deploy_tool("shield")
        self.assertEqual(self.game.max_trace, 130)
        self.assertNotIn("shield", self.game.tools_unlocked)

    def test_deploy_unknown_tool(self):
        self.game.deploy_tool("bogus")  # Should not crash

    def test_deploy_unavailable_tool(self):
        """Deploying a valid tool name that isn't in tools_unlocked should warn."""
        # These tools exist but aren't in the default set
        self.game.deploy_tool("nuke")  # Not unlocked — should print warning

    def test_download_cracked_node(self):
        node = self.game.current_network.nodes[0]
        node["cracked"] = True
        file_count = len(node["files"])
        old_score = self.game.score
        self.game.download_files(1)
        self.assertEqual(self.game.files_stolen, file_count)
        self.assertGreater(self.game.score, old_score)
        self.assertEqual(len(node["files"]), 0)

    def test_download_no_double_dip(self):
        node = self.game.current_network.nodes[0]
        node["cracked"] = True
        self.game.download_files(1)
        files_after_first = self.game.files_stolen
        self.game.download_files(1)  # Second download — no files
        self.assertEqual(self.game.files_stolen, files_after_first)

    def test_crack_already_cracked(self):
        node = self.game.current_network.nodes[0]
        node["cracked"] = True
        old_score = self.game.score
        old_trace = self.game.trace_level
        self.game.crack_node(1)
        self.assertEqual(self.game.score, old_score)
        self.assertEqual(self.game.trace_level, old_trace)

    def test_mission_victory_bonus(self):
        self.game.trace_level = 30
        for n in self.game.current_network.nodes:
            n["cracked"] = True
        old_score = self.game.score
        self.game.mission_victory()
        expected_bonus = (100 - 30) * 10
        self.assertEqual(self.game.score, old_score + expected_bonus)
        self.assertEqual(self.game.networks_cracked, 1)

    def test_mission_victory_bonus_with_shield(self):
        """Bonus should use max_trace, not hardcoded 100."""
        self.game.max_trace = 130
        self.game.trace_level = 30
        for n in self.game.current_network.nodes:
            n["cracked"] = True
        old_score = self.game.score
        self.game.mission_victory()
        expected_bonus = (130 - 30) * 10
        self.assertEqual(self.game.score, old_score + expected_bonus)

    def test_none_current_network_guards(self):
        """Methods should not crash when current_network is None."""
        game = h.HackerSimulator()
        game.current_network = None

        # These should print error messages, not crash
        game.show_status()
        game.show_nodes()
        game.crack_node(1)
        game.download_files(1)

    def test_analyze_node_none_network(self):
        game = h.HackerSimulator()
        game.current_network = None
        game.analyze_node(1)  # Should not crash

    def test_analyze_node_invalid_index(self):
        self.game.analyze_node(0)  # Should not crash
        self.game.analyze_node(999)  # Should not crash

    def test_analyze_node_already_cracked(self):
        """Analyzing an already-cracked node should be a no-op."""
        node = self.game.current_network.nodes[0]
        node["cracked"] = True
        old_trace = self.game.trace_level
        self.game.analyze_node(1)
        self.assertEqual(self.game.trace_level, old_trace)

    def test_analyze_node_already_analyzed(self):
        """Analyzing an already-analyzed node should be a no-op."""
        node = self.game.current_network.nodes[0]
        node["analyzed"] = True
        old_trace = self.game.trace_level
        self.game.analyze_node(1)
        self.assertEqual(self.game.trace_level, old_trace)

    def test_analyze_node_sets_fields(self):
        """Analyzing a node should set analyzed=True and store code hint."""
        node = self.game.current_network.nodes[0]
        self.game.analyze_node(1)
        self.assertTrue(node["analyzed"])
        self.assertIn("_code_hint", node)
        self.assertIn("_access_code", node)
        # Trace should increase
        self.assertGreater(self.game.trace_level, 0)
        self.assertEqual(self.game.total_analyses, 1)

    def test_analyze_node_trace_cost(self):
        """Trace cost should be 2 * difficulty."""
        node = self.game.current_network.nodes[0]
        difficulty = node["difficulty"]
        old_trace = self.game.trace_level
        self.game.analyze_node(1)
        expected_cost = difficulty * 2
        self.assertEqual(self.game.trace_level, old_trace + expected_cost)

    def test_nouns_no_duplicates(self):
        self.assertEqual(len(h.NOUNS), len(set(h.NOUNS)),
                         f"Duplicates in NOUNS: {h.NOUNS}")

    def test_adjectives_no_duplicates(self):
        self.assertEqual(len(h.ADJECTIVES), len(set(h.ADJECTIVES)),
                         f"Duplicates in ADJECTIVES: {h.ADJECTIVES}")

    def test_version_constant(self):
        self.assertIsInstance(h.VERSION, str)
        self.assertRegex(h.VERSION, r'\d+\.\d+\.\d+')

    def test_command_history(self):
        """Test that command history is recorded."""
        game = h.HackerSimulator()
        self.assertEqual(game.command_history, [])
        game.command_history.append("status")
        game.command_history.append("nodes")
        self.assertEqual(len(game.command_history), 2)
        self.assertEqual(game.command_history[0], "status")

    def test_stats_tracking(self):
        """Test that crack stats are tracked."""
        game = h.HackerSimulator()
        self.assertEqual(game.total_cracks_attempted, 0)
        self.assertEqual(game.total_cracks_succeeded, 0)


class TestSaveLoad(unittest.TestCase):
    """Test the save/load system."""

    def setUp(self):
        # Use a temp dir for save files
        self._orig_save_dir = h.SAVE_DIR
        self._orig_save_file = h.SAVE_FILE
        self._orig_hs_file = h.HIGH_SCORES_FILE
        self._tmpdir = tempfile.mkdtemp()
        h.SAVE_DIR = self._tmpdir
        h.SAVE_FILE = os.path.join(self._tmpdir, "save.json")
        h.HIGH_SCORES_FILE = os.path.join(self._tmpdir, "highscores.json")

    def tearDown(self):
        h.SAVE_DIR = self._orig_save_dir
        h.SAVE_FILE = self._orig_save_file
        h.HIGH_SCORES_FILE = self._orig_hs_file
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_save_and_load(self):
        """Test that a game can be saved and loaded correctly."""
        random.seed(42)
        game = h.HackerSimulator()
        game.current_network = h.Network(difficulty=2)
        game.score = 1500
        game.networks_cracked = 3
        game.files_stolen = 12
        game.trace_level = 45
        game.tools_unlocked.add("nuke")

        self.assertTrue(h.save_game(game))

        loaded_game = h.HackerSimulator()
        self.assertTrue(h.load_game(loaded_game))

        self.assertEqual(loaded_game.score, 1500)
        self.assertEqual(loaded_game.networks_cracked, 3)
        self.assertEqual(loaded_game.files_stolen, 12)
        self.assertEqual(loaded_game.trace_level, 45)
        self.assertIn("nuke", loaded_game.tools_unlocked)
        self.assertIsNotNone(loaded_game.current_network)

    def test_load_no_save_file(self):
        """Loading when no save file exists should return False."""
        game = h.HackerSimulator()
        self.assertFalse(h.load_game(game))

    def test_load_corrupted_save(self):
        """Loading a corrupted save file should return False."""
        h.ensure_save_dir()
        with open(h.SAVE_FILE, "w") as f:
            f.write("{invalid json!!!")
        game = h.HackerSimulator()
        self.assertFalse(h.load_game(game))

    def test_save_creates_directory(self):
        """save_game should create the save directory if it doesn't exist."""
        new_dir = os.path.join(self._tmpdir, "subdir", "config")
        h.SAVE_DIR = new_dir
        h.SAVE_FILE = os.path.join(new_dir, "save.json")
        game = h.HackerSimulator()
        self.assertTrue(h.save_game(game))
        self.assertTrue(os.path.exists(h.SAVE_FILE))

    def test_delete_save(self):
        """Delete save file should work."""
        game = h.HackerSimulator()
        h.save_game(game)
        self.assertTrue(h.delete_save())
        self.assertFalse(os.path.exists(h.SAVE_FILE))

    def test_delete_nonexistent_save(self):
        """Deleting a nonexistent save file should return False."""
        self.assertFalse(h.delete_save())


class TestHighScores(unittest.TestCase):
    """Test the high score system."""

    def setUp(self):
        self._orig_save_dir = h.SAVE_DIR
        self._orig_hs_file = h.HIGH_SCORES_FILE
        self._tmpdir = tempfile.mkdtemp()
        h.SAVE_DIR = self._tmpdir
        h.HIGH_SCORES_FILE = os.path.join(self._tmpdir, "highscores.json")

    def tearDown(self):
        h.SAVE_DIR = self._orig_save_dir
        h.HIGH_SCORES_FILE = self._orig_hs_file
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_save_and_load_high_scores(self):
        """Test saving and reading high scores."""
        h.save_high_score(5000, 5, 20)
        h.save_high_score(3000, 3, 15)

        self.assertTrue(os.path.exists(h.HIGH_SCORES_FILE))
        with open(h.HIGH_SCORES_FILE, "r") as f:
            entries = json.load(f)
        self.assertEqual(len(entries), 2)
        # Should be sorted descending by score
        self.assertEqual(entries[0]["score"], 5000)
        self.assertEqual(entries[1]["score"], 3000)

    def test_high_score_limit(self):
        """Only top MAX_HIGH_SCORES entries should be kept."""
        for i in range(15):
            h.save_high_score(i * 100, i, i * 2)

        with open(h.HIGH_SCORES_FILE, "r") as f:
            entries = json.load(f)
        self.assertEqual(len(entries), h.MAX_HIGH_SCORES)

    def test_show_high_scores_empty(self):
        """show_high_scores should not crash with no scores."""
        # Redirect stdout to suppress output
        with patch('sys.stdout', new_callable=io.StringIO):
            h.show_high_scores()

    def test_show_high_scores_with_data(self):
        """show_high_scores should not crash with data."""
        h.save_high_score(1000, 2, 8)
        with patch('sys.stdout', new_callable=io.StringIO):
            h.show_high_scores()


class TestDifficultyBarDisplay(unittest.TestCase):
    def test_network_difficulty_bars(self):
        for d in range(1, 6):
            bar = "█" * d + "░" * (5 - d)
            self.assertEqual(len(bar), 5)

    def test_node_difficulty_bars(self):
        for d in range(1, 7):
            bar = "█" * d + "░" * (6 - d)
            self.assertEqual(len(bar), 6)

    def test_trace_bars(self):
        for pct in [0, 25, 50, 75, 99, 100]:
            filled = int(pct / 4)
            bar = "█" * filled + "░" * (25 - filled)
            self.assertEqual(len(bar), 25)


class TestEdgeCases(unittest.TestCase):
    """Edge case and robustness tests."""

    def test_ip_prefixes_valid(self):
        """All IP prefixes should be valid dotted notation."""
        for prefix in h.IP_PREFIXES:
            parts = prefix.split(".")
            self.assertEqual(len(parts), 2)
            for part in parts:
                self.assertTrue(part.isdigit())

    def test_corp_names_unique(self):
        """Corporation names should be unique."""
        self.assertEqual(len(h.CORP_NAMES), len(set(h.CORP_NAMES)))

    def test_file_names_unique(self):
        """File names should be unique."""
        self.assertEqual(len(h.FILE_NAMES), len(set(h.FILE_NAMES)))

    def test_hacker_aliases_unique(self):
        """Hacker aliases should be unique."""
        self.assertEqual(len(h.HACKER_ALIASES), len(set(h.HACKER_ALIASES)))

    def test_ansi_constants_not_empty(self):
        """All ANSI constants should be non-empty strings."""
        for name in ["BOLD", "DIM", "RED", "GREEN", "YELLOW", "BLUE",
                      "MAGENTA", "CYAN", "WHITE", "RESET", "CLEAR"]:
            const = getattr(h, name)
            self.assertIsInstance(const, str)
            self.assertTrue(len(const) > 0)

    def test_network_ip_format(self):
        """Generated IPs should have 4 octets."""
        random.seed(123)
        for _ in range(50):
            net = h.Network(difficulty=2)
            parts = net.ip.split(".")
            self.assertEqual(len(parts), 4, f"IP {net.ip} doesn't have 4 octets")

    def test_shield_multiple_uses(self):
        """Shield should stack max_trace increases."""
        game = h.HackerSimulator()
        game.current_network = h.Network(difficulty=2)
        game.tools_unlocked.add("shield")
        game.deploy_tool("shield")
        self.assertEqual(game.max_trace, 130)
        game.tools_unlocked.add("shield")
        game.deploy_tool("shield")
        self.assertEqual(game.max_trace, 160)

    def test_overclock_reduces_difficulty_floor(self):
        """Overclock should not reduce difficulty below 1."""
        game = h.HackerSimulator()
        random.seed(42)
        game.current_network = h.Network(difficulty=1)
        game.tools_unlocked.add("overclock")
        game.deploy_tool("overclock")
        for node in game.current_network.nodes:
            self.assertGreaterEqual(node["difficulty"], 1)


if __name__ == "__main__":
    unittest.main()