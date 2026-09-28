#!/usr/bin/env python3
"""Preview path collisions before files are copied or renamed."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Literal, Optional, Sequence

VERSION = "1.0.0"
Normalization = Literal["NFC", "NFKC"]


def path_parts(value: str) -> List[str]:
    """Split a relative path using either slash style and reject traversal."""
    value = value.strip().replace("\\", "/")
    parts = [part for part in value.split("/") if part]
    if not parts or any(part in (".", "..") for part in parts):
        raise ValueError("paths must be non-empty and cannot contain '.' or '..': {!r}".format(value))
    return parts


def collision_key(
    value: str,
    *,
    flatten: bool = False,
    case_sensitive: bool = False,
    normalization: Normalization = "NFC",
    portable: bool = False,
) -> str:
    """Return the destination identity produced by the selected rules."""
    parts = path_parts(value)
    if flatten:
        parts = parts[-1:]

    transformed = []
    for part in parts:
        part = unicodedata.normalize(normalization, part)
        if portable:
            part = part.rstrip(" .")
            if not part:
                raise ValueError("portable trimming leaves an empty path component in {!r}".format(value))
        if not case_sensitive:
            part = part.casefold()
        transformed.append(part)
    return "/".join(transformed)


def find_collisions(
    paths: Iterable[str],
    *,
    flatten: bool = False,
    case_sensitive: bool = False,
    normalization: Normalization = "NFC",
    portable: bool = False,
) -> Dict[str, List[str]]:
    """Group distinct source entries that resolve to the same destination key."""
    grouped: DefaultDict[str, List[str]] = defaultdict(list)
    for source in paths:
        key = collision_key(
            source,
            flatten=flatten,
            case_sensitive=case_sensitive,
            normalization=normalization,
            portable=portable,
        )
        grouped[key].append(source)
    return {key: sources for key, sources in sorted(grouped.items()) if len(sources) > 1}


def read_path_file(path: Path) -> List[str]:
    """Read one path per line, ignoring blanks and comment lines."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValueError("cannot read {}: {}".format(path, error))
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", metavar="PATH", help="relative source path to inspect")
    parser.add_argument("--file", type=Path, help="read additional paths, one per line")
    parser.add_argument("--flatten", action="store_true", help="compare basenames as if all files enter one directory")
    parser.add_argument("--case-sensitive", action="store_true", help="preserve case when comparing paths")
    parser.add_argument("--normalization", choices=("NFC", "NFKC"), default="NFC", help="Unicode normalization form (default: NFC)")
    parser.add_argument("--portable", action="store_true", help="trim component-ending spaces and periods")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--version", action="version", version="path-collision-scout {}".format(VERSION))
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    paths = list(args.paths)
    try:
        if args.file:
            paths.extend(read_path_file(args.file))
        if not paths:
            raise ValueError("provide at least one path or use --file")
        collisions = find_collisions(
            paths,
            flatten=args.flatten,
            case_sensitive=args.case_sensitive,
            normalization=args.normalization,
            portable=args.portable,
        )
    except ValueError as error:
        parser.error(str(error))

    if args.json:
        print(json.dumps({
            "paths_checked": len(paths),
            "collision_count": len(collisions),
            "collisions": [
                {"destination_key": key, "sources": sources}
                for key, sources in collisions.items()
            ],
        }, indent=2, ensure_ascii=False))
    elif not collisions:
        print("No collisions found across {} paths.".format(len(paths)))
    else:
        print("Found {} collision{} across {} paths:".format(
            len(collisions), "" if len(collisions) == 1 else "s", len(paths)
        ))
        for key, sources in collisions.items():
            print("- {}".format(key))
            for source in sources:
                print("  <- {}".format(source))
    return 1 if collisions else 0


if __name__ == "__main__":
    sys.exit(main())
