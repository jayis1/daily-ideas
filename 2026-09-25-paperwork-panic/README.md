# Paperwork Panic

Paperwork Panic is a small, offline Python terminal game by jayis1. Route absurd government forms to their required offices, then spend a rubber stamp on each one before the deadline.

## Features

- Six absurd form types selected deterministically with `--seed`.
- One to six forms per game with `--forms`.
- A board showing every form's current office and destination.
- Turn-limited play with `--turns`.
- Validated commands for moving, stamping, quitting, form numbers, and office names.
- `--demo` mode for printing a board without starting an interactive game.
- `--help` and `--version` CLI options.
- Deterministic, standard-library-only implementation with no network access or external services.

## Install

Requirements:

- Python 3.8 or newer.
- No third-party packages.

From the repository root:

```bash
cd 2026-09-25-paperwork-panic
```

There is nothing else to install.

## Run

Start the default three-form game:

```bash
python3 paperwork_panic.py
```

Run a small, repeatable puzzle:

```bash
python3 paperwork_panic.py --seed 25 --forms 2 --turns 8
```

Print a board without entering interactive play:

```bash
python3 paperwork_panic.py --seed 25 --forms 4 --turns 10 --demo
```

Show all command-line options or the current version:

```bash
python3 paperwork_panic.py --help
python3 paperwork_panic.py --version
```

## Usage

Each form displays its current office and the destination it needs. Move a form to its destination, then stamp it. For example:

```text
1. Application for Emergency Biscuits: CAFETERIA -> STAMP

> move 1 stamp
Moved form 1 to STAMP.

> stamp 1
Stamped form 1. A tiny choir sings.
```

Commands:

- `move <form> <office>` moves a form to its required destination. The office name is case-insensitive.
- `stamp <form>` approves a form that has reached its destination and uses one stamp.
- `quit` leaves the desk and concedes defeat.

The game ends when all forms are approved, the turn limit is reached, or you quit. A seed makes the selected forms repeatable for sharing a particular puzzle.

## Tests

Run the unit tests from this directory:

```bash
python3 -m unittest -v
```

The tests cover deterministic selection, form-count validation, version output, valid moves and stamps, invalid offices, board rendering, scripted wins, winning on the final allowed turn, and invalid turn limits.

## Known issues

None known. Interactive play requires a terminal that can provide input; an unexpected end-of-file is treated as a loss without corrupting files or other state.

## Changelog

### 1.1.1

- Fixed games that completed on the final allowed turn being reported as deadline failures.
- Added validation for non-positive turn limits when `play` is called directly.
- Added regression tests for both fixes.
- Rewrote this README with current installation, usage, testing, and known-issue guidance.

### 1.1.0

- Added configurable form counts with `--forms`.
- Added `--version`.
- Added CLI validation for form counts and turn limits.
- Added demo mode and expanded tests.
