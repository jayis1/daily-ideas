#!/usr/bin/env python3
"""Tests for Terminal Mandala Generator."""

import sys
import os

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mandala import (
    MandalaGenerator, make_canvas, make_color_canvas,
    render_canvas, pick_palette, PALETTES, ELEMENT_TYPES,
    ansi_fg, ansi_bg, RESET
)


def test_canvas_creation():
    """Test that canvases are created with correct dimensions."""
    canvas = make_canvas(40, 20)
    assert len(canvas) == 20
    assert len(canvas[0]) == 40
    assert canvas[0][0] == ' '


def test_color_canvas_creation():
    """Test that color canvases are created with None values."""
    canvas = make_color_canvas(40, 20)
    assert len(canvas) == 20
    assert len(canvas[0]) == 40
    assert canvas[0][0] is None


def test_pick_palette():
    """Test palette selection."""
    warm = pick_palette('warm')
    assert warm == PALETTES['warm']
    cool = pick_palette('cool')
    assert cool == PALETTES['cool']
    # Random palette should return something valid
    rand = pick_palette()
    assert isinstance(rand, list)
    assert len(rand) > 0


def test_ansi_escapes():
    """Test ANSI escape code generation."""
    fg = ansi_fg(196)
    assert '38;5;196' in fg
    bg = ansi_bg(16)
    assert '48;5;16' in bg
    assert RESET == '\033[0m'


def test_generator_creation():
    """Test basic generator creation."""
    gen = MandalaGenerator(width=60, height=31, seed=42)
    assert gen.width == 60
    assert gen.height == 31
    assert gen.cx == 30
    assert gen.cy == 15


def test_generator_seed_reproducibility():
    """Test that same seed produces same mandala."""
    gen1 = MandalaGenerator(width=60, height=31, seed=12345)
    gen1.generate_random(complexity=4)
    output1 = gen1.render_no_color()

    gen2 = MandalaGenerator(width=60, height=31, seed=12345)
    gen2.generate_random(complexity=4)
    output2 = gen2.render_no_color()

    assert output1 == output2


def test_center_dot():
    """Test adding center dot."""
    gen = MandalaGenerator(width=40, height=21, seed=42)
    gen.add_center_dot()
    # Center should have a character
    assert gen.canvas[gen.cy][gen.cx] != ' '


def test_circle():
    """Test adding a circle."""
    gen = MandalaGenerator(width=60, height=31, seed=42)
    gen.add_circle(radius=10, ch='●', color=196)
    # Should have non-space characters
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


def test_dotted_circle():
    """Test adding a dotted circle."""
    gen = MandalaGenerator(width=60, height=31, seed=42)
    gen.add_dotted_circle(radius=12, dots=16)
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0  # Some dots rendered (may overlap)


def test_petals():
    """Test adding petals."""
    gen = MandalaGenerator(width=60, height=31, seed=42)
    gen.add_petals(radius=12, count=8)
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


def test_star():
    """Test adding a star."""
    gen = MandalaGenerator(width=60, height=31, seed=42)
    gen.add_star(radius=10, points=6)
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


def test_spiral_arms():
    """Test adding spiral arms."""
    gen = MandalaGenerator(width=60, height=31, seed=42)
    gen.add_spiral_arms(arms=5, radius=12)
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


def test_diamonds():
    """Test adding diamonds."""
    gen = MandalaGenerator(width=80, height=41, seed=42)
    gen.add_diamonds(radius=15, count=6)
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


def test_wave_ring():
    """Test adding wave ring."""
    gen = MandalaGenerator(width=60, height=31, seed=42)
    gen.add_wave_ring(radius=10, waves=8)
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


def test_wheel():
    """Test adding wheel spokes."""
    gen = MandalaGenerator(width=60, height=31, seed=42)
    gen.add_wheel(radius=10, spokes=8)
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


def test_fractal_ring():
    """Test adding fractal ring."""
    gen = MandalaGenerator(width=80, height=41, seed=42)
    gen.add_fractal_ring(radius=15, depth=2)
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


def test_filled_ring():
    """Test adding filled ring."""
    gen = MandalaGenerator(width=60, height=31, seed=42)
    gen.add_filled_ring(radius_outer=12, radius_inner=8)
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


def test_ornamental_border():
    """Test adding ornamental border."""
    gen = MandalaGenerator(width=60, height=31, seed=42)
    gen.add_ornamental_border()
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


def test_generate_random():
    """Test random generation with various complexities."""
    for complexity in range(3, 9):
        gen = MandalaGenerator(width=60, height=31, seed=42)
        gen.generate_random(complexity=complexity)
        non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
        assert non_space > 0, f"No content generated for complexity {complexity}"


def test_render_no_color():
    """Test no-color rendering."""
    gen = MandalaGenerator(width=40, height=21, seed=42)
    gen.generate_random(complexity=4)
    output = gen.render_no_color()
    # Should have 21 lines
    lines = output.split('\n')
    assert len(lines) == 21
    # Each line should be 40 chars
    for line in lines:
        assert len(line) == 40


def test_render_with_color():
    """Test colored rendering contains ANSI codes."""
    gen = MandalaGenerator(width=40, height=21, seed=42)
    gen.generate_random(complexity=4)
    output = gen.render(bg_color=16)
    # Should contain ANSI escape sequences
    assert '\033[' in output


def test_palette_options():
    """Test all palette options work."""
    for name in PALETTES:
        gen = MandalaGenerator(width=40, height=21, seed=42, palette_name=name)
        gen.generate_random(complexity=4)
        non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
        assert non_space > 0, f"Palette {name} produced no content"


def test_elements_tracking():
    """Test that elements are tracked properly."""
    gen = MandalaGenerator(width=60, height=31, seed=42)
    gen.add_center_dot()
    gen.add_circle(radius=10)
    gen.add_dotted_circle(radius=15)
    assert len(gen.elements) == 3


def test_polar_plot():
    """Test polar coordinate plotting."""
    gen = MandalaGenerator(width=40, height=21, seed=42)
    gen._plot_polar(5, 0, '●', 196)
    # Something should be plotted
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


def test_radial_draw():
    """Test radial symmetry drawing."""
    gen = MandalaGenerator(width=40, height=21, seed=42)
    gen._radial_draw(10, 0, '●', 196, symmetry=6)
    # Should have some rendered points (positions may overlap at small sizes)
    non_space = sum(1 for row in gen.canvas for ch in row if ch != ' ')
    assert non_space > 0


if __name__ == '__main__':
    test_canvas_creation()
    test_color_canvas_creation()
    test_pick_palette()
    test_ansi_escapes()
    test_generator_creation()
    test_generator_seed_reproducibility()
    test_center_dot()
    test_circle()
    test_dotted_circle()
    test_petals()
    test_star()
    test_spiral_arms()
    test_diamonds()
    test_wave_ring()
    test_wheel()
    test_fractal_ring()
    test_filled_ring()
    test_ornamental_border()
    test_generate_random()
    test_render_no_color()
    test_render_with_color()
    test_palette_options()
    test_elements_tracking()
    test_polar_plot()
    test_radial_draw()
    print("✅ All tests passed!")