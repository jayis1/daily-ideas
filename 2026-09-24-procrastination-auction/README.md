# Procrastination Auction

Author: jayis1

A tiny terminal game where your tasks compete in an auction for a limited supply of focus. Each task arrives with urgency and dread; the most persuasive task usually wins, while a little randomness lets an underdog steal a round.

## Features

- Play immediately with a funny built-in set of tasks.
- Add tasks with a name, urgency, dread, and estimated minutes.
- Spend focus in configurable auction rounds (five minutes by default).
- Reject malformed values and duplicate task names with readable CLI errors.
- Use `--seed` for repeatable auctions.
- Use `--json` for machine-readable allocations and round results.
- Use `--help` and `--version` to discover the command-line interface.
- Uses only the Python standard library and makes no network requests.

## Installation

Python 3.9 or newer is required. No third-party packages are needed.

From this directory, verify the installation with:

```bash
python3 auction.py --help
```

## Run the Auction

Run the default auction:

```bash
python3 auction.py --minutes 20 --seed 7
```

Provide tasks as `name,urgency,dread,minutes`. Repeat `--task` for multiple tasks. Urgency and dread must be 1–10, and requested minutes must be positive:

```bash
python3 auction.py \
  --minutes 12 \
  --round-minutes 2 \
  --seed 4 \
  --task "reply to Sam,9,3,10" \
  --task "water the office fern,3,8,5" \
  --task "rename the downloads folder,2,2,5"
```

For machine-readable output:

```bash
python3 auction.py --json --minutes 10 --seed 1
```

Inspect the version:

```bash
python3 auction.py --version
```

## How It Works

A task's base bid is calculated from urgency and dread. Each round awards up to the configured number of minutes to the highest-scoring active task, with a random bonus from 0–12 points. A task stops bidding after its requested minutes have been awarded, or when the focus budget is empty.

The program reports each task's allocation, unused focus, and the winner of the final round. Supplying `--seed` makes the chaos bonus repeatable; leaving it out gives each auction a fresh roll.

## Development

Run the test suite from this directory:

```bash
python3 -m unittest -v test_auction.py
```

The tests cover parsing and validation, budget limits, non-mutating auctions, deterministic seeds, custom round sizes, duplicate-name protection, and report-bar formatting.

## Known Issues

None known for the documented command-line use.

## Changelog

### 2026-09-24

- Fixed the text report's allocation bar, which previously displayed too many unallocated dots after minutes were awarded.
- Added a regression test for report-bar width and updated the usage documentation.
