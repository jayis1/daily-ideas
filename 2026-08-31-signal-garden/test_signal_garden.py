import json
import pytest
from signal_garden import analyze, render

def test_analysis_is_deterministic_and_deduplicates():
    a = analyze("Moon moon, river", seed=4)
    b = analyze("Moon moon, river", seed=4)
    assert [s.word for s in a] == ["moon", "river"]
    assert a == b

def test_render_has_requested_canvas():
    output = render(analyze("one two", seed=1), 30, 8)
    assert len(output.splitlines()) == 10
    assert "one" in output and "two" in output

def test_small_canvas_rejected():
    with pytest.raises(ValueError): render([], 10, 5)

def test_json_shape_from_dataclass():
    data = [s.__dict__ for s in analyze("a b", seed=1)]
    assert set(data[0]) == {"word", "strength", "phase", "symbol"}
