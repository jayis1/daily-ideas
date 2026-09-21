import json
import subprocess
import sys
from pathlib import Path

import pytest

from assumption_switchboard import analyze, json_report, load_decision, ranking


def sample():
    return {"criteria": {"cost": 5, "comfort": 3, "adventure": 2}, "options": [
        {"name": "Night train", "scores": {"cost": 8, "comfort": 6, "adventure": 4}},
        {"name": "Budget flight", "scores": {"cost": 4, "comfort": 5, "adventure": 7}},
        {"name": "Road trip", "scores": {"cost": 3, "comfort": 8, "adventure": 10}},
    ]}


def test_baseline_and_sensitivity_report():
    report = analyze(sample())
    assert report["winner"] == "Night train"
    assert any(change["criterion"] == "adventure" for change in report["changes"])


def test_ranking_normalizes_weights():
    assert ranking(sample(), {"cost": 50, "comfort": 30, "adventure": 20}) == ranking(sample(), sample()["criteria"])


def test_rejects_missing_score(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"criteria": {"speed": 1}, "options": [{"name": "x", "scores": {}}]}))
    with pytest.raises(ValueError, match="score"):
        load_decision(path)


def test_rejects_huge_integer_without_traceback(tmp_path: Path):
    path = tmp_path / "huge.json"
    path.write_text(json.dumps({
        "criteria": {"speed": 10**1000},
        "options": [{"name": "x", "scores": {"speed": 1}}],
    }))
    with pytest.raises(ValueError, match="weight"):
        load_decision(path)


def test_rejects_duplicate_option_names(tmp_path: Path):
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps({
        "criteria": {"speed": 1},
        "options": [
            {"name": "Same", "scores": {"speed": 1}},
            {"name": " same ", "scores": {"speed": 2}},
        ],
    }))
    with pytest.raises(ValueError, match="duplicate"):
        load_decision(path)


def test_custom_multipliers_are_reported():
    report = analyze(sample(), (0.1, 10.0))
    assert report["steps"] == (0.1, 10.0)
    assert report["tested"] == 6


def test_cli_version():
    result = subprocess.run(
        [sys.executable, "assumption_switchboard.py", "--version"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip().endswith("1.1.1")


def test_json_report_is_machine_readable():
    report = json.loads(json_report(analyze(sample(), (2.0,))))
    assert report["winner"] == "Night train"
    assert report["baseline"][0]["name"] == "Night train"
