#!/usr/bin/env python3
"""Tests for the Procedural Conspiracy Board Generator."""

import sys
import os

# Add the project directory to path
sys.path.insert(0, os.path.dirname(__file__))

from conspiracy_board import (
    Entity, Connection, Note,
    pick, generate_board, render_board, generate_narrative,
    PEOPLE, ORGANIZATIONS, EVENTS, LOCATIONS,
    EVIDENCE_TYPES, CONNECTION_LABELS, CRYPTIC_NOTES,
    bresenham,
)


def test_pick():
    """Test that pick returns correct number of unique items."""
    result = pick(PEOPLE, 3)
    assert len(result) == 3
    assert len(set(result)) == 3  # All unique
    for item in result:
        assert item in PEOPLE


def test_pick_more_than_pool():
    """Test that pick handles requesting more than available."""
    result = pick(PEOPLE, 100)
    assert len(result) == len(PEOPLE)
    assert len(set(result)) == len(PEOPLE)


def test_bresenham_horizontal():
    """Test Bresenham with horizontal line."""
    points = bresenham(0, 0, 5, 0)
    assert len(points) == 6
    assert points[0] == (0, 0)
    assert points[-1] == (5, 0)


def test_bresenham_vertical():
    """Test Bresenham with vertical line."""
    points = bresenham(3, 0, 3, 4)
    assert len(points) == 5
    for x, y in points:
        assert x == 3


def test_bresenham_diagonal():
    """Test Bresenham with diagonal line."""
    points = bresenham(0, 0, 3, 3)
    assert len(points) == 4
    assert points[0] == (0, 0)
    assert points[-1] == (3, 3)


def test_bresenham_same_point():
    """Test Bresenham with start == end."""
    points = bresenham(5, 5, 5, 5)
    assert len(points) == 1
    assert points[0] == (5, 5)


def test_generate_board_defaults():
    """Test board generation with default parameters."""
    entities, connections, notes = generate_board(seed=12345)

    assert len(entities) == 13  # 5 people + 3 orgs + 3 events + 2 locations
    assert len(connections) == 9
    assert len(notes) == 4

    # Check entity types
    kinds = [e.kind for e in entities]
    assert kinds.count("person") == 5
    assert kinds.count("org") == 3
    assert kinds.count("event") == 3
    assert kinds.count("location") == 2


def test_generate_board_custom():
    """Test board generation with custom parameters."""
    entities, connections, notes = generate_board(
        width=60, height=30,
        num_people=2, num_orgs=2, num_events=2, num_locations=1,
        num_connections=4, num_notes=2,
        seed=42,
    )

    assert len(entities) == 7
    assert len(connections) == 4
    assert len(notes) == 2

    # Check positions are within bounds
    for e in entities:
        assert 0 <= e.x < 60
        assert 0 <= e.y < 30


def test_generate_board_reproducible():
    """Test that same seed produces same board."""
    e1, c1, n1 = generate_board(seed=42)
    e2, c2, n2 = generate_board(seed=42)

    for a, b in zip(e1, e2):
        assert a.name == b.name
        assert a.kind == b.kind
        assert a.x == b.x
        assert a.y == b.y


def test_generate_board_different_seeds():
    """Test that different seeds produce different boards."""
    e1, c1, n1 = generate_board(seed=1)
    e2, c2, n2 = generate_board(seed=2)

    names1 = [e.name for e in e1]
    names2 = [e.name for e in e2]
    # Very unlikely to be identical
    assert names1 != names2 or len(set(names1)) < len(names1)


def test_entities_have_evidence():
    """Test that some entities get evidence assigned."""
    entities, _, _ = generate_board(num_people=10, num_orgs=10, seed=99)
    has_evidence = sum(1 for e in entities if e.evidence)
    # With 20 entities, at least some should have evidence
    assert has_evidence > 0


def test_connections_reference_valid_entities():
    """Test that all connections reference valid entity indices."""
    entities, connections, _ = generate_board(seed=55)
    n = len(entities)
    for conn in connections:
        assert 0 <= conn.from_idx < n
        assert 0 <= conn.to_idx < n
        assert conn.from_idx != conn.to_idx
        assert conn.strength in (1, 2, 3)


def test_render_board_no_color():
    """Test that rendering without color works and produces output."""
    entities, connections, notes = generate_board(
        width=60, height=25, seed=42
    )
    output = render_board(entities, connections, notes,
                         width=60, height=25, color=False)
    assert len(output) > 0
    assert "CONSPIRACY BOARD" in output
    assert "LEGEND" in output


def test_render_board_with_color():
    """Test that rendering with color produces ANSI escape codes."""
    entities, connections, notes = generate_board(
        width=60, height=25, seed=42
    )
    output = render_board(entities, connections, notes,
                         width=60, height=25, color=True)
    assert "\033[" in output  # Contains ANSI codes


def test_render_board_contains_entities():
    """Test that rendered board contains all entity names."""
    entities, connections, notes = generate_board(
        width=80, height=35, seed=42
    )
    output = render_board(entities, connections, notes,
                         width=80, height=35, color=False)
    for e in entities:
        assert e.name in output, f"Entity '{e.name}' not found in output"


def test_render_board_contains_connections():
    """Test that legend contains all connections."""
    entities, connections, notes = generate_board(
        width=80, height=35, seed=42
    )
    output = render_board(entities, connections, notes,
                         width=80, height=35, color=False)
    for conn in connections:
        e1 = entities[conn.from_idx]
        e2 = entities[conn.to_idx]
        assert e1.name in output
        assert e2.name in output


def test_generate_narrative():
    """Test narrative generation."""
    entities, connections, notes = generate_board(seed=42)
    narrative = generate_narrative(entities, connections, notes)
    assert "CLASSIFIED" in narrative
    assert "BURN AFTER READING" in narrative
    for conn in connections:
        assert entities[conn.from_idx].name in narrative
        assert entities[conn.to_idx].name in narrative


def test_note_texts_in_output():
    """Test that cryptic notes appear in rendered output."""
    entities, connections, notes = generate_board(seed=77)
    output = render_board(entities, connections, notes,
                         width=80, height=35, color=False)
    for note in notes:
        assert note.text in output


def test_kind_symbols():
    """Test that entity kind symbols are correct."""
    from conspiracy_board import KIND_SYM
    assert KIND_SYM["person"] == "☻"
    assert KIND_SYM["org"] == "◆"
    assert KIND_SYM["event"] == "◈"
    assert KIND_SYM["location"] == "▲"


def test_data_pools_not_empty():
    """Test that all data pools are populated."""
    assert len(PEOPLE) > 5
    assert len(ORGANIZATIONS) > 5
    assert len(EVENTS) > 5
    assert len(LOCATIONS) > 5
    assert len(EVIDENCE_TYPES) > 5
    assert len(CONNECTION_LABELS) > 5
    assert len(CRYPTIC_NOTES) > 5


def test_no_duplicate_names_in_board():
    """Test that no two entities share the same name."""
    entities, _, _ = generate_board(seed=123)
    names = [e.name for e in entities]
    assert len(names) == len(set(names))


if __name__ == "__main__":
    # Run all tests
    test_functions = [
        obj for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    passed = 0
    failed = 0
    for test_fn in test_functions:
        try:
            test_fn()
            print(f"  ✓ {test_fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {test_fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)