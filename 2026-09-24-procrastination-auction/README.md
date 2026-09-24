# Procrastination Auction

A tiny terminal game where your tasks compete in an auction for a limited supply of focus. Each task arrives with urgency and dread; the most persuasive task usually wins, but a little randomness lets the underdog steal a round.

## Features

- Play immediately with a funny built-in set of tasks.
- Add your own tasks with urgency, dread, and estimated minutes.
- Spend focus in configurable auction rounds (five minutes by default).
- Reject invalid values and duplicate task names with readable command-line errors.
- Use `--seed` for repeatable auctions.
- Use `--json` for machine-readable allocations and round results.
- Use `--help` and `--version` to discover the command-line interface.
- Uses only the Python standard library and makes no network requests.

## Installation

Python 3.9 or newer is the only requirement. From this directory:

```bash
python3 auction.py --help
```

No virtual environment or third-party packages are needed.

## How to Run

Try the default auction:

```bash
python3 auction.py --minutes 20 --seed 7
```

Provide tasks as `name,urgency,dread,minutes`, repeating `--task` as needed. Urgency and dread must be 1–10, and requested minutes must be positive:

```bash
python3 auction.py \
  --minutes 12 \
  --round-minutes 2 \
  --seed 4 \
  --task "reply to Sam,9,3,10" \
  --task "water the office fern,3,8,5" \
  --task "rename the downloads folder,2,2,5"
```

For scripts, request JSON:

```bash
python3 auction.py --json --minutes 10 --seed 1
```

Inspect the installed version:

```bash
python3 auction.py --version
```

## What It Does

The bid for a task is calculated from its urgency and dread. The auction awards up to the configured number of minutes per round to the highest-scoring active task, with a random bonus of 0–12 points. A task stops bidding when its requested minutes have been awarded or the focus budget is empty. Task names must be unique so every allocation remains unambiguous.

The program reports each task's allocation, unused focus, and the task that won the final round. Supplying `--seed` makes the chaos bonus repeatable; leaving it out gives each auction a fresh roll.

A normal run prints a compact ruling:

```text
PROCRASTINATION AUCTION
========================
The tasks have made their case.

answer the email         bid  76  ███████████████··············· 15 min
organize the cables      bid  49  ·········· 0 min
learn one magic trick    bid  38  ·········· 0 min
wash the suspicious mug  bid  87  █████····· 5 min

Unused focus: 0 min
Final ruling: answer the email got the last word.
```

## Development

Run the tests from this directory:

```bash
python3 -m unittest -v test_auction.py
```

The tests cover parsing and validation, budget limits, non-mutating auctions, deterministic seeds, custom round sizes, and duplicate-name protection.
