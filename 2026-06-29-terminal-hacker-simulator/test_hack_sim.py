#!/usr/bin/env python3
"""
Tests for Terminal Hacker Simulator.

Run with: python3 test_hack_sim.py
"""
import sys
import os
import random
import io
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
            self.assertFalse(n["cracked"])

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

    def test_check_trace_below(self):
        self.game.trace_level = 50
        self.assertFalse(self.game.check_trace())

    def test_check_trace_at_max(self):
        self.game.trace_level = 100
        self.assertTrue(self.game.check_trace())

    def test_check_trace_above_max(self):
        self.game.trace_level = 150
        self.assertTrue(self.game.check_trace())

    def test_generate_network(self):
        self.game.generate_network()
        self.assertIsNotNone(self.game.current_network)
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

    def test_deploy_unknown_tool(self):
        self.game.deploy_tool("bogus")  # Should not crash

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

    def test_none_current_network_guards(self):
        """Methods should not crash when current_network is None."""
        game = h.HackerSimulator()
        game.current_network = None

        # These should print error messages, not crash
        game.show_status()
        game.show_nodes()
        game.crack_node(1)
        game.download_files(1)

    def test_nouns_no_duplicates(self):
        self.assertEqual(len(h.NOUNS), len(set(h.NOUNS)),
                         f"Duplicates in NOUNS: {h.NOUNS}")

    def test_version_constant(self):
        self.assertIsInstance(h.VERSION, str)
        self.assertRegex(h.VERSION, r'\d+\.\d+\.\d+')


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


if __name__ == "__main__":
    unittest.main()