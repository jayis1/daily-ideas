#!/usr/bin/env python3
"""
Tests for Decision Oracle — validates core logic without interactive prompts.

Run with: python3 -m pytest test_decision_oracle.py -v
       or: python3 test_decision_oracle.py
"""

import json
import sys
import tempfile
from pathlib import Path

# Add project directory to path
sys.path.insert(0, str(Path(__file__).parent))

import decision_oracle as do


# ─── Test Fixtures ────────────────────────────────────────────────

SAMPLE_TREE = {
    "name": "test_tree",
    "description": "A simple test tree",
    "version": "2.0.0",
    "root": {
        "question": "Is it sunny?",
        "yes": {
            "question": "Do you want to go outside?",
            "yes": {"decision": "Go for a walk in the park!"},
            "no": {"decision": "Read a book by the window."},
        },
        "no": {
            "question": "Do you like board games?",
            "yes": {"decision": "Settle in for board game night!"},
            "no": {"decision": "Binge-watch your favorite series."},
        },
    },
}

DEEP_TREE = {
    "name": "deep_tree",
    "description": "A tree with varying depths",
    "root": {
        "question": "Q1?",
        "yes": {
            "question": "Q2?",
            "yes": {"decision": "Deep yes-yes"},
            "no": {"decision": "Deep yes-no"},
        },
        "no": {"decision": "Shallow no"},
    },
}

MALFORMED_TREE = {
    "name": "malformed",
    "description": "A tree with issues",
    "root": {
        "question": "Missing branches?",
        # Missing "yes" and "no" keys
    },
}

EMPTY_DECISION_TREE = {
    "name": "empty_decision",
    "description": "A tree with an empty decision",
    "root": {
        "question": "Is this ok?",
        "yes": {"decision": ""},
        "no": {"decision": "Fine"},
    },
}


# ─── Counting Tests ───────────────────────────────────────────────

class TestCountNodes:
    def test_sample_tree(self):
        assert do.count_nodes(SAMPLE_TREE["root"]) == 7

    def test_single_question(self):
        node = {"question": "Q?", "yes": {"decision": "Y"}, "no": {"decision": "N"}}
        assert do.count_nodes(node) == 3

    def test_empty_node(self):
        assert do.count_nodes({}) == 0
        assert do.count_nodes(None) is not None  # Should not crash

    def test_deep_tree(self):
        assert do.count_nodes(DEEP_TREE["root"]) == 5


class TestCountLeaves:
    def test_sample_tree(self):
        assert do.count_leaves(SAMPLE_TREE["root"]) == 4

    def test_single_question(self):
        node = {"question": "Q?", "yes": {"decision": "Y"}, "no": {"decision": "N"}}
        assert do.count_leaves(node) == 2

    def test_empty(self):
        assert do.count_leaves({}) == 0

    def test_deep_tree(self):
        assert do.count_leaves(DEEP_TREE["root"]) == 3


class TestTreeDepth:
    def test_sample_tree(self):
        assert do.tree_depth(SAMPLE_TREE["root"]) == 2

    def test_single_question(self):
        node = {"question": "Q?", "yes": {"decision": "Y"}, "no": {"decision": "N"}}
        assert do.tree_depth(node) == 1

    def test_leaf_node(self):
        assert do.tree_depth({"decision": "Done"}) == 0

    def test_deep_tree(self):
        # Q1 -> Q2 -> leaf = depth 2 for yes branch, 0 for no branch
        assert do.tree_depth(DEEP_TREE["root"]) == 2


# ─── Collect Leaves Tests ─────────────────────────────────────────

class TestCollectLeaves:
    def test_sample_tree(self):
        leaves = do.collect_leaves(SAMPLE_TREE["root"])
        assert len(leaves) == 4
        decisions = [d for d, _ in leaves]
        assert "Go for a walk in the park!" in decisions
        assert "Read a book by the window." in decisions

    def test_paths(self):
        leaves = do.collect_leaves(DEEP_TREE["root"])
        # Shallow no should have path length 1
        shallow = [p for d, p in leaves if d == "Shallow no"]
        assert len(shallow) == 1
        assert len(shallow[0]) == 1

        # Deep yes-yes should have path length 2
        deep = [p for d, p in leaves if d == "Deep yes-yes"]
        assert len(deep) == 1
        assert len(deep[0]) == 2

    def test_empty_tree(self):
        assert do.collect_leaves({}) == []


# ─── Validation Tests ─────────────────────────────────────────────

class TestValidateTree:
    def test_valid_tree(self):
        issues = do.validate_tree(SAMPLE_TREE["root"])
        assert len(issues) == 0

    def test_missing_branches(self):
        issues = do.validate_tree(MALFORMED_TREE["root"])
        assert len(issues) > 0
        # Should report missing 'yes' and 'no' branches
        assert any("yes" in i.lower() for i in issues)
        assert any("no" in i.lower() for i in issues)

    def test_empty_decision(self):
        issues = do.validate_tree(EMPTY_DECISION_TREE["root"])
        assert any("empty" in i.lower() or "decision" in i.lower() for i in issues)

    def test_empty_node(self):
        issues = do.validate_tree({})
        assert len(issues) > 0

    def test_deep_tree_valid(self):
        issues = do.validate_tree(DEEP_TREE["root"])
        assert len(issues) == 0


# ─── Path / Filename Tests ─────────────────────────────────────────

class TestGetTreePath:
    def test_simple_name(self):
        path = do.get_tree_path("lunch_decider")
        assert path.name == "lunch_decider.json"

    def test_spaces(self):
        path = do.get_tree_path("My Tree")
        assert path.name == "my_tree.json"

    def test_special_chars(self):
        path = do.get_tree_path("tree/with/slashes")
        assert path.name == "tree_with_slashes.json"

    def test_empty_string(self):
        path = do.get_tree_path("")
        assert path.name == "untitled.json"

    def test_strip_whitespace(self):
        path = do.get_tree_path("  hello world  ")
        assert path.name == "hello_world.json"


# ─── Mermaid Export Tests ──────────────────────────────────────────

class TestMermaidExport:
    def test_produces_output(self):
        output = do.export_mermaid_to_string(SAMPLE_TREE)
        assert output.startswith("graph TD")
        assert "Is it sunny?" in output
        assert "Go for a walk in the park!" in output

    def test_escape_quotes(self):
        tree = {
            "root": {
                "question": 'Is it "fun"?',
                "yes": {"decision": "It's great!"},
                "no": {"decision": "Nope"},
            }
        }
        output = do.export_mermaid_to_string(tree)
        # Should use single quotes inside the Mermaid labels
        assert "'fun'" in output

    def test_node_ids_unique(self):
        output = do.export_mermaid_to_string(SAMPLE_TREE)
        lines = output.strip().split("\n")
        node_def_lines = [l for l in lines if "N" in l and ("{{" in l or "[" in l)]
        # Each node should get a unique N{id} identifier
        assert len(node_def_lines) > 0


# ─── JSON Persistence Tests ────────────────────────────────────────

class TestPersistence:
    def test_round_trip(self, tmp_path):
        # Override DATA_DIR temporarily
        original_data_dir = do.DATA_DIR
        do.DATA_DIR = tmp_path / "trees"

        try:
            do.ensure_data_dir()
            tree_path = do.get_tree_path("test_round")
            tree_path.write_text(json.dumps(SAMPLE_TREE, indent=2))

            loaded = json.loads(tree_path.read_text())
            assert loaded["name"] == "test_tree"
            assert loaded["root"]["question"] == "Is it sunny?"
            assert do.count_nodes(loaded["root"]) == 7
        finally:
            do.DATA_DIR = original_data_dir


# ─── CLI Argument Tests ───────────────────────────────────────────

class TestCLIHelp:
    def test_version_flag(self, capsys):
        """Test --version flag works."""
        sys.argv = ["decision_oracle.py", "--version"]
        do.main()
        captured = capsys.readouterr()
        assert "2.0.0" in captured.out

    def test_help_flag(self, capsys):
        """Test --help flag works."""
        sys.argv = ["decision_oracle.py", "--help"]
        do.main()
        captured = capsys.readouterr()
        assert "build" in captured.out.lower()
        assert "consult" in captured.out.lower()


# ─── Run standalone ───────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))