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


def test_find_ranks_rooms_by_matching_terms():
    rooms, _ = mp.build_palace("red boat sleeps\n\nred fox wakes near a red door")

    matches = mp.find_rooms(rooms, "red fox")

    assert [room.number for room, _ in matches] == [2, 1]
    assert matches[0][1] == ["fox", "red"]


def test_cli_supports_version_and_custom_keyword_limit():
    version = subprocess.run(
        [sys.executable, "memory_palace.py", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert version.stdout.strip() == f"memory-palace {mp.__version__}"

    result = subprocess.run(
        [sys.executable, "memory_palace.py", "--json", "--keywords", "2"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert all(len(room["keywords"]) <= 2 for room in payload["rooms"])
    assert payload["stats"]["room_count"] == len(payload["rooms"])


def test_unicode_words_and_titles_are_preserved():
    rooms, _ = mp.build_palace("Café naïve résumé")

    assert rooms[0].title == "Café Naïve Résumé"
    assert rooms[0].keywords == ["café", "naïve", "résumé"]
