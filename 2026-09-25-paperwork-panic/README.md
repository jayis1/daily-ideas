# Paperwork Panic

Paperwork Panic is a tiny, offline terminal game about routing ridiculous government forms through the correct offices before the deadline. Move each form to its destination, then spend one rubber stamp to approve it before bureaucracy wins.

## Features

- Six absurd form types, with a deterministic deck selected by `--seed`.
- One to six forms per game via `--forms`, so a quick puzzle can stay quick.
- A compact board showing each form's current office and destination.
- Strict input validation for unknown commands, form numbers, offices, and premature stamps.
- A configurable deadline via `--turns`.
- `--demo` mode for inspecting a board without entering the game.
- `--help` and `--version` flags for discoverable CLI usage.
- Python standard library only; no network access or external services.

## Install

Python 3.8 or newer is required. No package installation is needed.

```bash
cd 2026-09-25-paperwork-panic
```

## Run

Start the default three-form game:

```bash
python3 paperwork_panic.py
```

Play a smaller, repeatable puzzle:

```bash
python3 paperwork_panic.py --seed 25 --forms 2 --turns 8
```

Print a board without starting an interactive session:

```bash
python3 paperwork_panic.py --seed 25 --forms 4 --demo
```

Inspect all command-line options or the current version:

```bash
python3 paperwork_panic.py --help
python3 paperwork_panic.py --version
```

## How to play

Each form starts at an office and names the office it needs to visit. A successful move uses one turn; once the form reaches its destination, stamp it to approve it.

```text
1. Application for Emergency Biscuits: CAFETERIA -> STAMP
2. Temporary Moonlight Permit: ARCHIVE -> APPEALS

> move 1 stamp
Moved form 1 to STAMP.

> stamp 1
Stamped form 1. A tiny choir sings.
```

Commands:

- `move <form> <office>` — move a form to its destination.
- `stamp <form>` — approve a form that has reached its destination.
- `quit` — leave the desk and concede defeat.

The game ends when every form is approved, the turn limit is reached, or you quit. A seed makes the selected forms repeatable, which is useful for sharing a particularly cursed desk with a friend.

## Tests

Run the standard-library unit tests from this directory:

```bash
python3 -m unittest -v
```

The tests cover repeatable decks, configurable form counts, CLI version output, valid moves and stamps, invalid offices, board rendering, and a scripted win.

## Author

Created by jayis1 as part of the Daily Ideas collection.
