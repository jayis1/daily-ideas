import json
import subprocess
import sys

import pytest

from signal_garden import VERSION, analyze, render, summarize


def test_analysis_is_deterministic_and_deduplicates():
    a = analyze("Moon moon, river", seed=4)
    b = analyze("Moon moon, river", seed=4)
    assert [s.word for s in a] == ["moon", "river"]
    assert a == b


def test_unicode_and_inner_punctuation_are_tokenized():
    assert [s.word for s in analyze("Café, don't stop—café!")] == ["café", "don't", "stop", "café"][:3]


def test_render_has_requested_canvas():
    output = render(analyze("one two", seed=1), 30, 8)
    assert len(output.splitlines()) == 10
    assert "one" in output and "two" in output


def test_small_canvas_rejected():
    with pytest.raises(ValueError):
        render([], 10, 5)


def test_empty_summary_is_safe():
    assert summarize([]) == {
        "unique_signals": 0,
        "total_strength": 0,
        "average_strength": 0.0,
        "strongest": None,
    }


def test_cli_version_and_json_export(tmp_path):
    output_file = tmp_path / "nested" / "garden.json"
    command = [sys.executable, "signal_garden.py", "rain", "rain", "glass", "--seed", "2", "--stats", "--json", str(output_file)]
    completed = subprocess.run(command, text=True, capture_output=True, check=True)
    assert "2 unique signals" in completed.stdout
    assert "Total strength:" in completed.stdout
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["version"] == VERSION
    assert payload["summary"]["unique_signals"] == 2

    version = subprocess.run([sys.executable, "signal_garden.py", "--version"], text=True, capture_output=True, check=True)
    assert version.stdout.strip() == f"Signal Garden {VERSION}"
