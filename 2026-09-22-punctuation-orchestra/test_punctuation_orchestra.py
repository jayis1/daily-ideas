import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent
SCRIPT = ROOT / "punctuation_orchestra.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_render_has_rhythm_and_melody():
    result = run("Hello, world!")
    assert result.returncode == 0
    assert "Melody :" in result.stdout
    assert "hat     tss" in result.stdout
    assert "crash   KRAK" in result.stdout


def test_json_preserves_positions():
    result = run("Hi?!", "--json")
    payload = json.loads(result.stdout)
    assert [hit["position"] for hit in payload["hits"]] == [2, 3]
    assert payload["hits"][0]["instrument"] == "bell"


def test_missing_input_is_a_friendly_error():
    result = run()
    assert result.returncode == 2
    assert "provide TEXT or --file PATH" in result.stdout


def test_width_is_validated():
    result = run("Hi!", "--width", "10")
    assert result.returncode == 2
    assert "width must be at least 20" in result.stdout
