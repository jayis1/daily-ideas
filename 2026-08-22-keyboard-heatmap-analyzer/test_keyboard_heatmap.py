import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from keyboard_heatmap import analyze_text, normalize_char, render_heatmap, serialize_analysis

PROJECT_DIR = Path(__file__).resolve().parent
SCRIPT = PROJECT_DIR / "keyboard_heatmap.py"


def test_normalize_char_maps_shifted_symbols():
    assert normalize_char("A") == "a"
    assert normalize_char("!") == "1"
    assert normalize_char("?") == "/"


def test_analysis_counts_rows_hands_and_bigrams():
    analysis = analyze_text("Dad adds jazz.")
    assert analysis.counts["d"] == 4
    assert analysis.counts["a"] == 3
    assert analysis.row_usage["home row"] >= 5
    assert analysis.hand_usage["left"] > analysis.hand_usage["right"]
    assert analysis.bigrams["da"] >= 1
    assert analysis.effort_score > 0


def test_render_heatmap_mentions_space_cell():
    analysis = analyze_text("a a")
    rendered = render_heatmap(analysis, use_color=False)
    assert "space" in rendered
    assert "a" in rendered


def test_serialize_analysis_includes_summary_metrics():
    analysis = analyze_text("hello world")
    payload = serialize_analysis(analysis, top_n=3)
    summary = cast(dict[str, Any], payload["summary"])
    assert cast(float, summary["effort_per_100_keys"]) > 0
    assert cast(list[tuple[str, int]], summary["top_keys"])


def test_cli_json_output_is_valid():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", "hello"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["counts"]["h"] == 1
    assert payload["summary"]["top_keys"][0][0] == "l"


def test_cli_reads_stdin_when_requested():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--stdin", "--no-color"],
        cwd=PROJECT_DIR,
        input="type me maybe",
        capture_output=True,
        text=True,
        check=True,
    )
    assert "mapped keys:" in result.stdout
    assert "top keys:" in result.stdout


def test_cli_version_flag():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--version"],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "1.1.0" in result.stdout
