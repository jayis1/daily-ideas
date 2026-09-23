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
    assert "provide TEXT, --file PATH, or --stdin" in result.stdout


def test_width_is_validated():
    result = run("Hi!", "--width", "10")
    assert result.returncode == 2
    assert "width must be at least 20" in result.stdout


def test_version_is_available_without_input():
    result = run("--version")
    assert result.returncode == 0
    assert result.stdout.strip().endswith("1.3.0")


def test_stdin_input_can_be_piped():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--stdin", "--json"],
        cwd=ROOT,
        input="pipe?!",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["text"] == "pipe?!"
    assert [hit["symbol"] for hit in payload["hits"]] == ["?", "!"]


def test_max_hits_keeps_original_positions():
    result = run("a,b;c!", "--json", "--max-hits", "1")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert len(payload["hits"]) == 1
    assert payload["hits"][0]["position"] == 1


def test_zero_max_hits_returns_no_hits():
    result = run("a,b!", "--json", "--max-hits", "0")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["hits"] == []


def test_title_removes_terminal_control_characters():
    result = run("safe\x1b[31m title\r\n")
    assert result.returncode == 0
    assert "\x1b" not in result.stdout
    assert "safe [31m title" in result.stdout


def test_file_and_text_inputs_cannot_be_combined(tmp_path):
    source = tmp_path / "phrase.txt"
    source.write_text("hello!", encoding="utf-8")
    result = run("also", "--file", str(source))
    assert result.returncode == 2
    assert "not allowed with argument" in result.stderr


def test_invalid_utf8_file_is_a_friendly_error(tmp_path):
    source = tmp_path / "not-utf8.txt"
    source.write_bytes(b"hello!\xff")
    result = run("--file", str(source))
    assert result.returncode == 2
    assert "utf-8" in result.stdout.lower()
    assert "traceback" not in result.stderr.lower()
