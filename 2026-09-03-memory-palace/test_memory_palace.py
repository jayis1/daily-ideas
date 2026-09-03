import json
import subprocess
import sys
from pathlib import Path

import memory_palace as mp


def test_builds_rooms_and_shared_keyword_links():
    rooms, links = mp.build_palace(
        "A red boat crosses the river.\n\nThe river carries a red lantern.\n\nA quiet hill watches the moon.",
        min_shared=1,
    )
    assert len(rooms) == 3
    assert any(link.left == 1 and link.right == 2 and "river" in link.shared for link in links)
    assert not any(link.left == 1 and link.right == 3 for link in links)


def test_min_shared_filters_doors():
    _, links = mp.build_palace("alpha beta gamma\n\nalpha beta delta", min_shared=3)
    assert links == []


def test_json_cli_is_parseable(tmp_path: Path):
    source = tmp_path / "notes.txt"
    source.write_text("The red fox sleeps.\n\nThe red fox wakes.", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "memory_palace.py", str(source), "--json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert len(payload["rooms"]) == 2
    assert payload["links"][0]["shared"] == ["fox", "red"]
