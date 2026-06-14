#!/usr/bin/env python3
"""Tests for the Procedural Constellation Map Generator."""

import json
import os
import tempfile
import sys

sys.path.insert(0, os.path.dirname(__file__))

from constellation_map import (
    StarMapGenerator, StarMapRenderer, Constellation, Star,
    export_json, GREEK_LETTERS, GREEK_SYMS, Nebula, CelestialObject
)


def test_basic_generation():
    """Test that a star map generates without errors."""
    gen = StarMapGenerator(width=40, height=20, seed=42, num_constellations=5,
                          num_background_stars=50, num_nebulae=1, num_deep_objects=3)
    gen.generate()
    assert len(gen.constellations) == 5
    assert len(gen.background_stars) == 50
    assert len(gen.nebulae) == 1
    assert len(gen.deep_objects) == 3


def test_reproducibility():
    """Test that the same seed produces the same map."""
    gen1 = StarMapGenerator(seed=12345)
    gen1.generate()
    gen2 = StarMapGenerator(seed=12345)
    gen2.generate()
    
    # Same constellation names
    for c1, c2 in zip(gen1.constellations, gen2.constellations):
        assert c1.name == c2.name
        assert c1.full_name == c2.full_name
        assert c1.lore == c2.lore
    
    # Same star positions
    for c1, c2 in zip(gen1.constellations, gen2.constellations):
        for s1, s2 in zip(c1.stars, c2.stars):
            assert abs(s1.x - s2.x) < 0.01
            assert abs(s1.y - s2.y) < 0.01
            assert abs(s1.magnitude - s2.magnitude) < 0.01


def test_different_seeds_different_maps():
    """Test that different seeds produce different maps."""
    gen1 = StarMapGenerator(seed=100)
    gen1.generate()
    gen2 = StarMapGenerator(seed=200)
    gen2.generate()
    
    # At least some constellation names should differ
    names1 = {c.name for c in gen1.constellations}
    names2 = {c.name for c in gen2.constellations}
    # Very unlikely all names match with different seeds
    assert names1 != names2


def test_constellation_has_stars():
    """Each constellation should have at least 3 stars."""
    gen = StarMapGenerator(seed=42, num_constellations=10)
    gen.generate()
    for c in gen.constellations:
        assert len(c.stars) >= 3, f"Constellation {c.name} has only {len(c.stars)} stars"


def test_constellation_has_connections():
    """Each constellation should have connection lines."""
    gen = StarMapGenerator(seed=42, num_constellations=10)
    gen.generate()
    for c in gen.constellations:
        assert len(c.connections) >= 1, f"Constellation {c.name} has no connections"


def test_constellation_greek_letters():
    """Stars in constellations should get Greek letter designations."""
    gen = StarMapGenerator(seed=42, num_constellations=5)
    gen.generate()
    for c in gen.constellations:
        named_stars = [s for s in c.stars if s.greek_letter is not None]
        assert len(named_stars) >= 1, f"Constellation {c.name} has no named stars"
        # Check format includes Greek symbol
        first_named = named_stars[0]
        assert "α" in first_named.greek_letter or "β" in first_named.greek_letter or first_named.greek_letter.startswith(tuple(GREEK_SYMS))


def test_star_magnitude_range():
    """Star magnitudes should be reasonable (0-7)."""
    gen = StarMapGenerator(seed=42)
    gen.generate()
    for c in gen.constellations:
        for s in c.stars:
            assert 0 <= s.magnitude <= 7, f"Star magnitude {s.magnitude} out of range"
    for s in gen.background_stars:
        assert 0 <= s.magnitude <= 7, f"Background star magnitude {s.magnitude} out of range"


def test_star_positions_in_bounds():
    """All stars should be within the map boundaries."""
    gen = StarMapGenerator(width=80, height=40, seed=42)
    gen.generate()
    for c in gen.constellations:
        for s in c.stars:
            assert 0 <= s.x <= 80, f"Star x={s.x} out of bounds"
            assert 0 <= s.y <= 40, f"Star y={s.y} out of bounds"
    for s in gen.background_stars:
        assert 0 <= s.x <= 80, f"Background star x={s.x} out of bounds"
        assert 0 <= s.y <= 40, f"Background star y={s.y} out of bounds"


def test_constellation_names_unique():
    """All constellation names should be unique."""
    gen = StarMapGenerator(seed=42, num_constellations=20)
    gen.generate()
    names = [c.name for c in gen.constellations]
    assert len(names) == len(set(names)), "Duplicate constellation names found"


def test_constellation_lore():
    """Each constellation should have lore text."""
    gen = StarMapGenerator(seed=42)
    gen.generate()
    for c in gen.constellations:
        assert len(c.lore) > 20, f"Constellation {c.name} has insufficient lore"
        assert c.name in c.lore or c.full_name in c.lore, "Lore should mention the constellation name"


def test_nebulae():
    """Nebulae should have required properties."""
    gen = StarMapGenerator(seed=42, num_nebulae=3)
    gen.generate()
    assert len(gen.nebulae) == 3
    for neb in gen.nebulae:
        assert 0 <= neb.x <= gen.width
        assert 0 <= neb.y <= gen.height
        assert neb.radius > 0
        assert 0 < neb.density <= 1
        assert len(neb.name) > 0


def test_deep_objects():
    """Deep sky objects should have types and descriptions."""
    gen = StarMapGenerator(seed=42, num_deep_objects=5)
    gen.generate()
    assert len(gen.deep_objects) == 5
    for obj in gen.deep_objects:
        assert obj.obj_type in ["galaxy", "nebula", "cluster", "pulsar", "quasar", "black hole"]
        assert len(obj.name) > 0
        assert len(obj.description) > 0
        assert len(obj.symbol) > 0


def test_renderer_basic():
    """Renderer should produce output without errors."""
    gen = StarMapGenerator(width=40, height=20, seed=42, num_constellations=3,
                          num_background_stars=30)
    gen.generate()
    renderer = StarMapRenderer(gen, use_color=False)
    output = renderer.render()
    assert len(output) > 100
    assert "Constellation Catalog" in output


def test_renderer_no_color():
    """No-color mode should not contain ANSI escape sequences."""
    gen = StarMapGenerator(width=40, height=20, seed=42)
    gen.generate()
    renderer = StarMapRenderer(gen, use_color=False)
    output = renderer.render()
    assert "\033[" not in output


def test_renderer_with_color():
    """Color mode should contain ANSI escape sequences."""
    gen = StarMapGenerator(width=40, height=20, seed=42)
    gen.generate()
    renderer = StarMapRenderer(gen, use_color=True)
    output = renderer.render()
    assert "\033[" in output


def test_renderer_no_lines():
    """No-lines mode should still produce output."""
    gen = StarMapGenerator(width=40, height=20, seed=42)
    gen.generate()
    renderer = StarMapRenderer(gen, use_color=False, show_lines=False)
    output = renderer.render()
    assert len(output) > 100


def test_renderer_no_labels():
    """No-labels mode should still produce output."""
    gen = StarMapGenerator(width=40, height=20, seed=42)
    gen.generate()
    renderer = StarMapRenderer(gen, use_color=False, show_labels=False)
    output = renderer.render()
    assert len(output) > 100


def test_json_export():
    """JSON export should produce valid JSON with all data."""
    gen = StarMapGenerator(seed=42, num_constellations=3, num_nebulae=1, num_deep_objects=2)
    gen.generate()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name
    
    try:
        export_json(gen, filepath)
        
        with open(filepath) as f:
            data = json.load(f)
        
        assert data["seed"] == 42
        assert len(data["constellations"]) == 3
        assert len(data["nebulae"]) == 1
        assert len(data["deep_objects"]) == 2
        
        for c in data["constellations"]:
            assert "name" in c
            assert "title" in c
            assert "full_name" in c
            assert "lore" in c
            assert "stars" in c
            assert "connections" in c
            assert len(c["stars"]) >= 3
            for s in c["stars"]:
                assert "x" in s
                assert "y" in s
                assert "magnitude" in s
    finally:
        os.unlink(filepath)


def test_star_display_chars():
    """Star brightness characters should vary by magnitude."""
    bright = Star(0, 0, 0.5)
    medium = Star(0, 0, 2.5)
    dim = Star(0, 0, 5.0)
    
    assert bright.display_char in "★✦"
    assert medium.display_char == "⋆"
    assert dim.display_char == "∘"


def test_constellation_shapes():
    """All constellation shapes should generate valid stars."""
    for shape in ["chain", "triangle", "cross", "arc", "cluster", "spiral"]:
        gen = StarMapGenerator(seed=42, num_constellations=1)
        # Force shape
        c = gen._generate_constellation_shape(20, 10, 5, shape)
        assert len(c) == 5, f"Shape {shape} produced {len(c)} stars instead of 5"
        for s in c:
            assert 0 <= s.magnitude <= 7


def test_connections_valid():
    """All connection indices should reference valid stars."""
    gen = StarMapGenerator(seed=42, num_constellations=10)
    gen.generate()
    for c in gen.constellations:
        for i, j in c.connections:
            assert 0 <= i < len(c.stars), f"Connection index {i} out of range"
            assert 0 <= j < len(c.stars), f"Connection index {j} out of range"
            assert i != j, "Self-connection found"


def test_small_map():
    """Very small maps should still generate."""
    gen = StarMapGenerator(width=20, height=10, seed=42, num_constellations=2,
                          num_background_stars=10, num_nebulae=0)
    gen.generate()
    renderer = StarMapRenderer(gen, use_color=False)
    output = renderer.render()
    assert len(output) > 0


def test_large_map():
    """Large maps should generate without performance issues."""
    gen = StarMapGenerator(width=120, height=60, seed=42, num_constellations=20,
                          num_background_stars=500)
    gen.generate()
    assert len(gen.constellations) == 20
    assert len(gen.background_stars) == 500


def test_constellation_full_name():
    """Constellation full name should include name and title."""
    gen = StarMapGenerator(seed=42)
    gen.generate()
    for c in gen.constellations:
        assert ", " in c.full_name
        parts = c.full_name.split(", ")
        assert len(parts) == 2
        assert parts[0] == c.name
        assert parts[1] == c.title


if __name__ == "__main__":
    test_count = 0
    failures = 0
    
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            test_count += 1
            try:
                obj()
                print(f"  ✓ {name}")
            except Exception as e:
                failures += 1
                print(f"  ✗ {name}: {e}")
    
    print(f"\n{test_count - failures}/{test_count} tests passed")
    if failures > 0:
        sys.exit(1)