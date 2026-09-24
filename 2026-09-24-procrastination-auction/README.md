# Procrastination Auction

A tiny terminal game where your tasks compete in an auction for a limited supply of focus. Each task arrives with urgency and dread; the most persuasive task usually wins, but a little randomness lets the underdog steal a round.

## Features

- Play immediately with a funny built-in set of tasks.
- Add your own tasks with urgency, dread, and estimated minutes.
- Spend focus in five-minute auction rounds until the time runs out.
- Use `--seed` for repeatable auctions.
- Use `--json` when you want to pipe the ruling into another tool.
- Uses only the Python standard library and makes no network requests.

## Installation

Python 3.9 or newer is the only requirement. From this directory:

```bash
python3 auction.py --help
```

No virtual environment or third-party packages are needed.

## How to Run

Try the default auction in ten seconds:

```bash
python3 auction.py --minutes 20 --seed 7
```

Provide tasks as `name,urgency,dread,minutes`, repeating `--task` as needed:

```bash
python3 auction.py \
  --minutes 12 \
  --seed 4 \
  --task "reply to Sam,9,3,10" \
  --task "water the office fern,3,8,5" \
  --task "rename the downloads folder,2,2,5"
```

For scripts, request JSON:

```bash
python3 auction.py --json --minutes 10 --seed 1
```

## Usage Examples

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

The exact winner can change without `--seed`, because every auction contains a small chaos bonus.

## What It Does

The bid for a task is calculated from its urgency and dread. The auction then awards up to five minutes per round to the highest-scoring active task, with a random bonus of 0–12 points. A task stops bidding when its requested minutes have been awarded or the focus budget is empty. The program reports each task's allocation and the final round winner.

Urgency and dread are both rated from 1 (mild) to 10 (catastrophic). Minutes must be positive. Invalid task specifications produce a clear command-line error instead of a traceback.

## Development

Run the built-in tests from this directory:

```bash
python3 -m unittest -v test_auction.py
```
