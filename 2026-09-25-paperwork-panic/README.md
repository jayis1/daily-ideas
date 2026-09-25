# Paperwork Panic

A tiny, offline terminal game about routing ridiculous government forms through the correct offices before the deadline. You have one rubber stamp per form, and every form must visit its destination office before it can be approved.

## Why this is interesting

The game turns a simple two-step workflow into a miniature logistics puzzle: moving a form to the wrong place wastes a turn, while the silly form names make the bureaucracy feel oddly alive.

## Features

- Deterministic form decks with `--seed`, so puzzles can be replayed.
- Three randomly selected absurd forms per game.
- A compact terminal board showing every form's current office and destination.
- Input validation for invalid forms, offices, and premature stamps.
- A `--demo` mode for inspecting a board without entering the game.
- Python standard library only.

## Install

Python 3.8 or newer is required. No third-party packages are needed.

```bash
cd 2026-09-25-paperwork-panic
```

## Run

Start a game:

```bash
python3 paperwork_panic.py
```

Print a deterministic board without starting an interactive session:

```bash
python3 paperwork_panic.py --seed 25 --demo
```

Use `--turns` to make the deadline tighter or more forgiving:

```bash
python3 paperwork_panic.py --seed 7 --turns 8
```

## Usage examples

A typical turn looks like this:

```text
1. Application for Emergency Biscuits: CAFETERIA -> STAMP
2. Temporary Moonlight Permit: ARCHIVE -> APPEALS
3. Request to Rename a Pigeon: STAMP -> ARCHIVE

> move 1 stamp
Moved form 1 to STAMP.

> stamp 1
Stamped form 1. A tiny choir sings.
```

The commands are:

- `move <form> <office>` — move a form from its current office to its destination.
- `stamp <form>` — approve a form that has reached its destination.
- `quit` — leave the desk and concede defeat.

## What it does

`make_forms()` selects a repeatable set of forms from a small catalogue. Each form has a current office and a destination office. A successful `move` advances the form to its destination; a successful `stamp` marks it `DONE` and consumes one stamp. The game ends when all forms are approved or the turn limit is reached.

## Tests

Run the included unit tests from this directory:

```bash
python3 -m unittest -v
```

## Author

Created by jayis1 as part of the Daily Ideas collection.
