#!/usr/bin/env python3
"""Generate the committed application catalog from a Daily Ideas checkout."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

APP_DIR = re.compile(r"^(\d{4}-\d{2}-\d{2})-([a-z0-9-]+)$")
EXCLUDED_STEMS = {"debug", "verify", "run_tests"}

CATEGORIES = {
    "game": ("game", "roguelike", "tamagotchi", "sokoban", "mastermind", "tower-defense", "lunar-lander", "lock-picker", "escape-room", "slot-machine"),
    "puzzle": ("puzzle", "crossword", "nonogram", "rubiks", "pipes"),
    "science": ("nbody", "solar", "seismograph", "volcano", "gene", "periodic", "cellular", "reaction", "collatz", "circuit"),
    "simulation": ("simulator", "ecosystem", "boids", "exchange", "aquarium", "garden", "galton"),
    "audio": ("music", "wave-synth", "morse-wave", "drum"),
    "utility": ("cipher", "enigma", "spreadsheet", "slides", "calculator", "regex-engine", "departure-board", "typewriter"),
}


def title_and_description(readme: Path, slug: str) -> tuple[str, str]:
    title = slug.replace("-", " ").title()
    description = title
    if not readme.is_file():
        return title, description
    lines = readme.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines:
        if line.startswith("# "):
            title = re.sub(r"[^\w\s&:+./'-]", "", line[2:]).strip() or title
            break
    after_heading = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            after_heading = True
            continue
        if (after_heading and stripped and not stripped.lower().startswith("version ")
                and not stripped.startswith(("#", "!", "[", "<", "```", "---"))):
            description = re.sub(r"[*_`]", "", stripped)
            description = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", description)
            if len(description) > 180:
                description = description[:177].rstrip() + "..."
            break
    return title, description


def entrypoint(directory: Path, slug: str) -> Path:
    files = [p for p in directory.glob("*.py") if not p.name.startswith("test")]
    preferred = slug.replace("-", "_")
    ranked = sorted(files, key=lambda p: (
        p.stem in EXCLUDED_STEMS or p.stem.startswith(("debug", "bug_hunt", "find_")),
        p.stem != preferred,
        -p.stat().st_size,
        p.name,
    ))
    if not ranked:
        raise ValueError(f"no application entrypoint in {directory.name}")
    return ranked[0]


def category(slug: str) -> str:
    for name, terms in CATEGORIES.items():
        if any(re.search(rf"(?:^|-){re.escape(term)}(?:-|$)", slug) for term in terms):
            return name
    return "creative"


def inspect(directory: Path) -> dict:
    match = APP_DIR.fullmatch(directory.name)
    if not match:
        raise ValueError(directory.name)
    date, slug = match.groups()
    script = entrypoint(directory, slug)
    source = script.read_text(encoding="utf-8", errors="replace")
    lowered = source.lower()
    if "import curses" in source:
        interface = "curses"
    elif any(token in lowered for token in ("time.sleep", "\x1b[", "ansi")):
        interface = "animation"
    elif any(token in lowered for token in ("winsound", "pyaudio", "simpleaudio", "subprocess.run([\"aplay\"")):
        interface = "audio"
    elif "input(" in source:
        interface = "interactive"
    else:
        interface = "cli"
    dependencies = ["numpy"] if re.search(r"^\s*(?:import|from)\s+numpy\b", source, re.M) else []
    title, description = title_and_description(directory / "README.md", slug)
    tags = sorted(set(slug.split("-") + [category(slug)]))
    smoke_args = ["--help"] if "argparse" in source else []
    return {
        "id": slug,
        "title": title,
        "description": description,
        "date": date,
        "path": directory.name,
        "entrypoint": script.name,
        "category": category(slug),
        "interface": interface,
        "dependencies": dependencies,
        "tags": tags,
        "smoke_args": smoke_args,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    apps = [inspect(path) for path in sorted(args.root.iterdir()) if APP_DIR.fullmatch(path.name)]
    payload = json.dumps({"schema_version": 1, "apps": apps}, indent=2, ensure_ascii=False) + "\n"
    output = args.output or args.root / "src/daily_ideas/apps.json"
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != payload:
            print(f"catalog is stale; run {Path(__file__).name}")
            return 1
        print(f"catalog is current ({len(apps)} apps)")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    print(f"wrote {len(apps)} apps to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
