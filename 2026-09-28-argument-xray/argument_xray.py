#!/usr/bin/env python3
"""Reveal exactly what a command-line program receives in each argument."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from typing import Dict, List, Optional, Sequence, cast

VERSION = "1.0.0"
_SAFE_SHELL_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-"
)


def shell_quote(value: str) -> str:
    """Quote one string so a POSIX shell reads it back as one argument."""
    if value and all(character in _SAFE_SHELL_CHARS for character in value):
        return value
    return "'{}'".format(value.replace("'", "'\"'\"'"))


def classify(value: str) -> List[str]:
    """Return notable properties in a stable order."""
    flags: List[str] = []
    if not value:
        flags.append("empty")
    if any(character.isspace() for character in value):
        flags.append("whitespace")
    if any(unicodedata.category(character).startswith("C") for character in value):
        flags.append("control")
    if any(ord(character) > 127 for character in value):
        flags.append("non-ascii")
    if value.startswith("-"):
        flags.append("option-like")
    if any(character in "*?[]{}$`\\\"'|&;<>!()" for character in value):
        flags.append("shell-sensitive")
    return flags or ["plain"]


def inspect_argument(index: int, value: str) -> Dict[str, object]:
    """Build a JSON-safe description of one argument."""
    return {
        "index": index,
        "text": value,
        "characters": len(value),
        "utf8_bytes": len(value.encode("utf-8")),
        "flags": classify(value),
        "codepoints": ["U+{:04X}".format(ord(character)) for character in value],
    }


def build_report(arguments: Sequence[str], command: Optional[str] = None) -> Dict[str, object]:
    """Describe arguments and optionally construct a replay command."""
    inspected = [inspect_argument(index, value) for index, value in enumerate(arguments)]
    report: Dict[str, object] = {
        "argument_count": len(arguments),
        "arguments": inspected,
    }
    if command is not None:
        report["replay"] = " ".join(shell_quote(value) for value in [command, *arguments])
    return report


def escaped_text(value: str) -> str:
    """Return an ASCII-only representation that keeps invisible characters visible."""
    return ascii(value)


def render_text(report: Dict[str, object], show_codepoints: bool = False) -> str:
    """Render a report for terminal reading."""
    count = report["argument_count"]
    lines = ["Argument X-Ray: {} argument{}".format(count, "" if count == 1 else "s")]
    for item in cast(List[Dict[str, object]], report["arguments"]):
        lines.append("[{}] {}".format(item["index"], escaped_text(cast(str, item["text"]))))
        lines.append(
            "    characters: {}; UTF-8 bytes: {}; flags: {}".format(
                item["characters"],
                item["utf8_bytes"],
                ", ".join(cast(List[str], item["flags"])),
            )
        )
        if show_codepoints:
            lines.append(
                "    code points: {}".format(
                    " ".join(cast(List[str], item["codepoints"])) or "(none)"
                )
            )
    if "replay" in report:
        lines.extend(["Replay (POSIX shell):", str(report["replay"])])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Use -- before values that begin with a hyphen.",
    )
    parser.add_argument("arguments", nargs="*", metavar="ARG", help="argument to inspect")
    parser.add_argument("--command", metavar="NAME", help="include NAME in a safely quoted replay command")
    parser.add_argument("--codepoints", action="store_true", help="show every Unicode code point")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--version", action="version", version="argument-xray {}".format(VERSION))
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(args.arguments, args.command)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_text(report, args.codepoints))
    return 0


if __name__ == "__main__":
    sys.exit(main())
