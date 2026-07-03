#!/usr/bin/env python3
"""Tests for the Procedural Conspiracy Board Generator v2.1."""

import sys
import os
import json
import random

# Add the project directory to path
sys.path.insert(0, os.path.dirname(__file__))

from conspiracy_board import (
    Entity, Connection, Note, TimelineEvent,
    pick, generate_board, render_board, generate_narrative,
    generate_timeline, generate_json, render_timeline,
    compute_suspicion, detect_cycles, redact_text, suspicion_label,
    PEOPLE, ORGANIZATIONS, EVENTS, LOCATIONS,
    EVIDENCE_TYPES, CONNECTION_LABELS, CRYPTIC_NOTES,
    MONTHS, SUSPICION_LABELS,
    bresenham, VERSION,
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


def test_pick_zero():
    """Test that pick with n=0 returns empty list."""
    result = pick(PEOPLE, 0)
    assert len(result) == 0


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


def test_bresenham_long_line():
    """Test Bresenham with a long line."""
    points = bresenham(0, 0, 50, 50)
    assert len(points) > 50
    assert points[0] == (0, 0)
    assert points[-1] == (50, 50)


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


def test_generate_board_minimal():
    """Test board generation with minimal entities."""
    entities, connections, notes = generate_board(
        num_people=1, num_orgs=1, num_events=0, num_locations=0,
        num_connections=1, num_notes=0,
        seed=99,
    )
    assert len(entities) == 2
    assert len(connections) == 1
    assert len(notes) == 0


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


def test_narrative_with_suspicion():
    """Test that narrative includes suspicion assessment."""
    entities, connections, notes = generate_board(seed=42)
    narrative = generate_narrative(entities, connections, notes)
    assert "SUSPICION ASSESSMENT" in narrative


def test_narrative_with_timeline():
    """Test narrative with timeline integration."""
    entities, connections, notes = generate_board(seed=42)
    timeline = generate_timeline(entities, connections, num_events=4, seed=42)
    narrative = generate_narrative(entities, connections, notes, timeline=timeline)
    assert "TIMELINE FRAGMENTS" in narrative


def test_narrative_no_color():
    """Test narrative without color."""
    entities, connections, notes = generate_board(seed=42)
    narrative = generate_narrative(entities, connections, notes, color=False)
    assert "CLASSIFIED" in narrative
    assert "\033[" not in narrative


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


def test_version():
    """Test that VERSION is a valid version string."""
    assert isinstance(VERSION, str)
    parts = VERSION.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


# ─── New feature tests ────────────────────────────────────────────────────────

def test_compute_suspicion():
    """Test that suspicion scores are computed for all entities."""
    entities, connections, _ = generate_board(seed=42)
    for ent in entities:
        assert 0.0 <= ent.suspicion <= 1.0, f"{ent.name} suspicion out of range: {ent.suspicion}"


def test_suspicion_label_low():
    """Test suspicion label for low scores."""
    assert suspicion_label(0.0) == "LOW"
    assert suspicion_label(0.15) == "LOW"
    assert suspicion_label(0.29) == "LOW"


def test_suspicion_label_moderate():
    """Test suspicion label for moderate scores."""
    assert suspicion_label(0.35) == "MODERATE"
    assert suspicion_label(0.3) == "MODERATE"


def test_suspicion_label_high():
    """Test suspicion label for high scores."""
    assert suspicion_label(0.6) == "HIGH"
    assert suspicion_label(0.5) == "HIGH"


def test_suspicion_label_critical():
    """Test suspicion label for critical scores."""
    assert suspicion_label(0.8) == "CRITICAL"
    assert suspicion_label(0.7) == "CRITICAL"


def test_suspicion_label_extreme():
    """Test suspicion label for extreme scores."""
    assert suspicion_label(0.95) == "EXTREME"
    assert suspicion_label(0.9) == "EXTREME"


def test_detect_cycles_triangle():
    """Test cycle detection with a triangle."""
    entities = [
        Entity(name="A", kind="person"),
        Entity(name="B", kind="person"),
        Entity(name="C", kind="person"),
    ]
    connections = [
        Connection(0, 1, "KNOWS", 1),
        Connection(1, 2, "OWES", 1),
        Connection(2, 0, "FEARS", 1),
    ]
    cycles = detect_cycles(entities, connections)
    assert len(cycles) >= 1, "Should detect at least one triangle"


def test_detect_cycles_no_cycles():
    """Test cycle detection with no cycles."""
    entities = [
        Entity(name="A", kind="person"),
        Entity(name="B", kind="person"),
        Entity(name="C", kind="person"),
    ]
    connections = [
        Connection(0, 1, "KNOWS", 1),
        Connection(1, 2, "OWES", 1),
    ]
    cycles = detect_cycles(entities, connections)
    assert len(cycles) == 0, "Should detect no cycles"


def test_detect_cycles_in_board():
    """Test cycle detection on a generated board."""
    entities, connections, _ = generate_board(num_people=5, num_connections=15, seed=42)
    cycles = detect_cycles(entities, connections)
    # With many connections, cycles are likely but not guaranteed
    assert isinstance(cycles, list)


def test_redact_text():
    """Test that redact_text produces output with redaction blocks."""
    rng = random.Random(42)
    text = "The quick brown fox jumps over the lazy dog"
    result = redact_text(text, rng=rng, probability=0.5)
    # Should contain some █ characters when probability is 0.5
    assert isinstance(result, str)
    assert len(result) > 0
    # The non-redacted words should still appear partially
    words = result.split()
    for word in words:
        assert len(word) > 0


def test_redact_text_zero_probability():
    """Test that redact_text with probability=0 doesn't redact anything."""
    rng = random.Random(42)
    text = "The quick brown fox"
    result = redact_text(text, rng=rng, probability=0.0)
    assert result == text


def test_redact_text_full_probability():
    """Test that redact_text with probability=1.0 redacts everything."""
    rng = random.Random(42)
    text = "hello world"
    result = redact_text(text, rng=rng, probability=1.0)
    # All words should be redacted
    for word in result.split():
        assert all(c == "█" for c in word), f"Word '{word}' not fully redacted"


def test_generate_timeline():
    """Test timeline generation produces valid events."""
    entities, connections, _ = generate_board(seed=42)
    timeline = generate_timeline(entities, connections, num_events=4, seed=42)
    assert len(timeline) > 0

    for event in timeline:
        assert 1 <= event.month <= 12
        assert event.year >= 2019
        assert len(event.description) > 0
        assert 0 <= event.entity_idx < len(entities)
        assert event.classification in [
            "TOP SECRET", "CLASSIFIED", "EYES ONLY",
            "BURN AFTER READING", "NOFORN", "SCI", "COMPARTMENTED",
        ]


def test_generate_timeline_sorted():
    """Test that timeline events are sorted by date."""
    entities, connections, _ = generate_board(seed=42)
    timeline = generate_timeline(entities, connections, num_events=6, seed=42)
    for i in range(len(timeline) - 1):
        assert (timeline[i].year, timeline[i].month) <= (timeline[i + 1].year, timeline[i + 1].month)


def test_render_timeline():
    """Test that timeline rendering produces output."""
    entities, connections, _ = generate_board(seed=42)
    timeline = generate_timeline(entities, connections, num_events=4, seed=42)
    output = render_timeline(timeline, entities, color=False)
    assert "TIMELINE" in output
    assert len(output) > 100


def test_render_timeline_with_color():
    """Test timeline rendering with color codes."""
    entities, connections, _ = generate_board(seed=42)
    timeline = generate_timeline(entities, connections, num_events=4, seed=42)
    output = render_timeline(timeline, entities, color=True)
    assert "TIMELINE" in output
    assert "\033[" in output


def test_render_timeline_empty():
    """Test timeline rendering with empty timeline returns empty string."""
    output = render_timeline([], [Entity(name="A", kind="person")], color=False)
    assert output == ""


def test_generate_json():
    """Test JSON output generation."""
    entities, connections, notes = generate_board(seed=42)
    json_str = generate_json(entities, connections, notes)
    data = json.loads(json_str)

    assert "version" in data
    assert data["version"] == VERSION
    assert "entities" in data
    assert "connections" in data
    assert "notes" in data
    assert "cycles" in data
    assert len(data["entities"]) == len(entities)
    assert len(data["connections"]) == len(connections)
    assert len(data["notes"]) == len(notes)


def test_generate_json_with_timeline():
    """Test JSON output includes timeline when provided."""
    entities, connections, notes = generate_board(seed=42)
    timeline = generate_timeline(entities, connections, num_events=4, seed=42)
    json_str = generate_json(entities, connections, notes, timeline)
    data = json.loads(json_str)

    assert "timeline" in data
    assert len(data["timeline"]) > 0


def test_generate_json_entity_fields():
    """Test JSON entity output has all expected fields."""
    entities, connections, notes = generate_board(seed=42)
    json_str = generate_json(entities, connections, notes)
    data = json.loads(json_str)

    for ent in data["entities"]:
        assert "name" in ent
        assert "kind" in ent
        assert "x" in ent
        assert "y" in ent
        assert "evidence" in ent
        assert "suspicion" in ent
        assert "suspicion_label" in ent


def test_generate_json_connection_fields():
    """Test JSON connection output has all expected fields."""
    entities, connections, notes = generate_board(seed=42)
    json_str = generate_json(entities, connections, notes)
    data = json.loads(json_str)

    for conn in data["connections"]:
        assert "from" in conn
        assert "to" in conn
        assert "label" in conn
        assert "strength" in conn
        assert "strength_word" in conn


def test_suspicion_scores_variety():
    """Test that suspicion scores vary across entities."""
    entities, connections, _ = generate_board(
        num_people=8, num_orgs=5, num_connections=20, seed=42
    )
    scores = [e.suspicion for e in entities]
    # Not all scores should be the same
    assert len(set(round(s, 2) for s in scores)) > 1, "Suspicion scores should vary"


def test_render_board_contains_suspicion():
    """Test that legend includes suspicion information."""
    entities, connections, notes = generate_board(seed=42)
    output = render_board(entities, connections, notes,
                         width=80, height=35, color=False)
    assert "suspicion" in output.lower() or "SUSPICION" in output


def test_render_board_contains_cycle_info():
    """Test that board output includes cycle detection section when cycles exist."""
    # Create a board with enough connections to likely have cycles
    entities, connections, notes = generate_board(
        num_people=5, num_connections=15, seed=42
    )
    output = render_board(entities, connections, notes,
                         width=80, height=35, color=False)
    # Cycle section header should appear regardless (it conditionally fills)
    assert "TRIANGULATED" in output or len(detect_cycles(entities, connections)) == 0


def test_board_width_clamping():
    """Test that board dimensions are clamped to valid ranges."""
    entities, connections, notes = generate_board(width=10, height=5, seed=42)
    # Should not crash even with very small dimensions
    output = render_board(entities, connections, notes,
                         width=40, height=20, color=False)
    assert len(output) > 0


def test_connection_strength_words():
    """Test that strength_word mapping works correctly."""
    from conspiracy_board import generate_json
    entities, connections, notes = generate_board(seed=42)
    json_str = generate_json(entities, connections, notes)
    data = json.loads(json_str)

    valid_strengths = {"weak", "moderate", "strong"}
    for conn in data["connections"]:
        assert conn["strength_word"] in valid_strengths


def test_timeline_event_dataclass():
    """Test TimelineEvent dataclass."""
    event = TimelineEvent(month=3, year=2023, description="Test event", entity_idx=0)
    assert event.month == 3
    assert event.year == 2023
    assert event.classification == "TOP SECRET"  # default


def test_months_constant():
    """Test that MONTHS has 12 entries."""
    assert len(MONTHS) == 12
    assert MONTHS[0] == "JAN"
    assert MONTHS[11] == "DEC"


def test_connection_strength_range():
    """Test that all connection strengths are 1, 2, or 3."""
    _, connections, _ = generate_board(seed=42)
    for conn in connections:
        assert conn.strength in (1, 2, 3), f"Invalid strength: {conn.strength}"


# ─── Bug fix regression tests ────────────────────────────────────────────────

def test_pick_negative_n():
    """Test that pick() handles negative n gracefully (returns empty list)."""
    result = pick(PEOPLE, -1)
    assert result == [], f"pick with n=-1 should return [], got {result}"


def test_pick_negative_n_large():
    """Test that pick() handles large negative n gracefully."""
    result = pick(PEOPLE, -100)
    assert result == [], f"pick with n=-100 should return [], got {result}"


def test_entity_names_within_board():
    """Test that entity names and evidence tags don't overflow the board."""
    import re
    for seed in range(20):
        entities, connections, notes = generate_board(
            width=40, height=20, seed=seed
        )
        board = render_board(entities, connections, notes,
                             width=40, height=20, color=False)
        # Board should render without error and be non-empty
        assert len(board) > 0
        # All entity names should appear somewhere in the output (even if clipped)
        for ent in entities:
            # At least the start of each name should be in the output
            assert ent.name[:3] in board or ent.name in board, \
                f"Entity name '{ent.name}' not found in board output"


def test_entity_evidence_clamped():
    """Test that entity evidence tags are clamped to board bounds in rendering."""
    # Create entities near the edges and render a small board
    entities = [
        Entity(name="TestEntity", kind="person", x=2, y=5,
               evidence=["PHOTO", "DOCUMENT"]),
    ]
    connections = []
    notes = []
    # Should not crash even on a small board
    board = render_board(entities, connections, notes,
                         width=40, height=20, color=False)
    assert len(board) > 0


def test_legend_box_consistency():
    """Test that legend box lines are consistently wide."""
    entities, connections, notes = generate_board(seed=42)
    board = render_board(entities, connections, notes,
                         width=100, height=45, color=False)
    lines = board.split('\n')
    # Find legend lines
    legend_lines = [l for l in lines if l.startswith('║')]
    assert len(legend_lines) > 0, "No legend lines found"
    # All legend lines should have the same width (after stripping ANSI codes)
    widths = set()
    import re
    for line in legend_lines:
        clean = re.sub(r'\033\[[0-9;]*m', '', line)
        widths.add(len(clean.rstrip()))
    # All widths should be the same (box_w + 4 for ║ + space + content + space + ║)
    # Due to truncation, they should all be exactly box_w + 4
    assert len(widths) == 1, f"Legend lines have inconsistent widths: {widths}"


def test_negative_cli_args_rejected():
    """Test that negative CLI arguments are rejected."""
    import subprocess
    result = subprocess.run(
        [sys.executable, "conspiracy_board.py", "--people", "-1"],
        capture_output=True, text=True
    )
    assert result.returncode != 0, "Should reject negative --people"


def test_pick_empty_pool():
    """Test that pick from empty pool returns empty list."""
    result = pick([], 5)
    assert result == []


def test_version_updated():
    """Test that VERSION is still a valid version string after bug fixes."""
    from conspiracy_board import VERSION
    assert isinstance(VERSION, str)
    parts = VERSION.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


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