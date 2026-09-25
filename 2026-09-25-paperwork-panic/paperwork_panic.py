#!/usr/bin/env python3
"""Paperwork Panic: route absurd forms through offices before the clock runs out."""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass


OFFICES = ("STAMP", "ARCHIVE", "APPEALS", "CAFETERIA")
FORMS = (
    ("Request to Rename a Pigeon", "STAMP", "ARCHIVE"),
    ("Temporary Moonlight Permit", "ARCHIVE", "APPEALS"),
    ("Complaint About a Suspiciously Confident Chair", "APPEALS", "CAFETERIA"),
    ("Application for Emergency Biscuits", "CAFETERIA", "STAMP"),
    ("Declaration of Intent to Nod", "STAMP", "APPEALS"),
    ("Permit to Whisper at Tax Documents", "ARCHIVE", "CAFETERIA"),
)


@dataclass(frozen=True)
class Form:
    name: str
    current: str
    destination: str


def make_forms(seed: int, count: int = 3) -> list[Form]:
    rng = random.Random(seed)
    chosen = rng.sample(FORMS, k=min(count, len(FORMS)))
    return [Form(name, origin, destination) for name, origin, destination in chosen]


def render_board(forms: list[Form], stamps: int, turn: int, max_turns: int) -> str:
    lines = ["PAPERWORK PANIC", "=" * 16, f"Turn {turn}/{max_turns}   Rubber stamps left: {stamps}", ""]
    for number, form in enumerate(forms, 1):
        status = "DONE" if form.current == "DONE" else f"{form.current} -> {form.destination}"
        lines.append(f"{number}. {form.name}: {status}")
    lines.extend(["", "Offices: " + ", ".join(OFFICES), "Commands: move <form> <office> | stamp <form> | quit"])
    return "\n".join(lines)


def apply_command(forms: list[Form], command: str, stamps: int) -> tuple[str, int]:
    words = command.lower().split()
    if not words:
        return "Type a command.", stamps
    if words[0] == "quit":
        return "quit", stamps
    if len(words) < 2 or not words[1].isdigit():
        return "Use a form number, for example: move 1 archive", stamps
    index = int(words[1]) - 1
    if not 0 <= index < len(forms):
        return "That form number is not on the desk.", stamps
    form = forms[index]
    if form.current == "DONE":
        return "That form is already gloriously complete.", stamps
    if words[0] == "move" and len(words) == 3:
        office = words[2].upper()
        if office not in OFFICES:
            return "That office does not exist. The cafeteria is already enough.", stamps
        if office != form.destination:
            return f"Wrong destination: form {index + 1} needs {form.destination}.", stamps
        forms[index] = Form(form.name, form.destination, form.destination)
        return f"Moved form {index + 1} to {form.destination}.", stamps
    if words[0] == "stamp":
        if stamps <= 0:
            return "You are out of stamps. The bureaucracy wins.", stamps
        if form.current != form.destination:
            return f"Stamp denied: form {index + 1} is still in {form.current}.", stamps
        forms[index] = Form(form.name, "DONE", "DONE")
        return f"Stamped form {index + 1}. A tiny choir sings.", stamps - 1
    return "Try move <form> <office> or stamp <form>.", stamps


def play(seed: int, max_turns: int = 12, input_fn=input, output_fn=print) -> bool:
    forms = make_forms(seed)
    stamps = len(forms)
    output_fn(render_board(forms, stamps, 1, max_turns))
    for turn in range(1, max_turns + 1):
        if all(form.current == "DONE" for form in forms):
            output_fn("\nALL FORMS APPROVED. You are now Deputy Assistant to the Assistant.")
            return True
        if turn > 1:
            output_fn("\n" + render_board(forms, stamps, turn, max_turns))
        try:
            command = input_fn("\n> ")
        except EOFError:
            output_fn("\nThe paperwork remains pending.")
            return False
        message, stamps = apply_command(forms, command, stamps)
        if message == "quit":
            output_fn("You abandon the desk. The forms will remember this.")
            return False
        output_fn(message)
    output_fn("\nDEADLINE MISSED. The forms have unionized.")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=25, help="repeatable form selection (default: 25)")
    parser.add_argument("--turns", type=int, default=12, help="maximum turns (default: 12)")
    parser.add_argument("--demo", action="store_true", help="print a board without starting the game")
    args = parser.parse_args(argv)
    if args.turns < 1:
        parser.error("--turns must be positive")
    forms = make_forms(args.seed)
    if args.demo:
        print(render_board(forms, len(forms), 1, args.turns))
        return 0
    return 0 if play(args.seed, args.turns) else 1


if __name__ == "__main__":
    sys.exit(main())
