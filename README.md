# 🧠 Daily Ideas

AI-generated coding projects — a new idea every 3 hours, each one enhanced and bug-hunted by an autonomous pipeline.

Every idea is conceived by an AI generator, improved by an enhancer, and debugged by a bug hunter — all running on autopilot. The result is a growing collection of working, tested projects you can actually run and learn from.

## 🤖 How It Works

Three AI agents work in a continuous cycle:

| Agent | Job | Frequency |
|---|---|---|
| **Generator** | Dreams up a novel project idea and builds it from scratch | Every 3h |
| **Enhancer** | Reads the latest project, adds features, improves code quality, upgrades docs | Every 3h |
| **Bug Hunter** | Runs the code, finds bugs, fixes them, verifies everything works | Every 3h |

Each agent rewrites the project's `README.md` when done, so documentation stays fresh and accurate.

## 📂 Project Index

| # | Date | Project | Description |
|---|---|---|---|
| 1 | 2026-06-12 | [ascii-dungeon-generator](./2026-06-12-ascii-dungeon-generator/) | Procedural ASCII dungeon maps with rooms, corridors, monsters, treasures, traps, NPCs, and fog of war |
| 2 | 2026-06-12 | [rune-cipher](./2026-06-12-rune-cipher/) | Terminal cryptography playground — Caesar, Vigenère, Affine, XOR ciphers with runic Unicode rendering and frequency analysis cracking |
| 3 | 2026-06-12 | [terminal-roguelike](./2026-06-12-terminal-roguelike/) | Full ASCII dungeon crawler — 5 floors, 10 enemy types, 3 bosses, inventory, fog of war, save/load |

> *New projects are added every 3 hours. This table is updated manually — check the repo for the latest.*

## 🗂️ Repo Structure

```
daily-ideas/
├── README.md                          ← You are here
├── 2026-06-12-ascii-dungeon-generator/
│   ├── README.md
│   ├── dungeon_generator.py
│   └── test_dungeon_generator.py
├── 2026-06-12-rune-cipher/
│   ├── README.md
│   └── rune_cipher.py
├── 2026-06-12-terminal-roguelike/
│   ├── README.md
│   └── roguelike.py
└── ...more every 3 hours
```

Each project folder is self-contained — just `cd` into it and run the Python file. No dependencies needed beyond Python 3.8+.

## ⚡ Quick Start

Pick any project and run it:

```bash
cd daily-ideas/2026-06-12-terminal-roguelike
python3 roguelike.py
```

```bash
cd daily-ideas/2026-06-12-rune-cipher
python3 rune_cipher.py --help
```

```bash
cd daily-ideas/2026-06-12-ascii-dungeon-generator
python3 dungeon_generator.py
```

## 🔄 Pipeline Details

### Generator
- Picks a project type at random (CLI tool, game, visualizer, utility, puzzle, etc.)
- Writes complete, runnable code from scratch
- Includes a full README with features, usage, and examples
- Checks existing folders to avoid duplicating ideas

### Enhancer
- Reads the most recent project's full source code
- Adds meaningful features (new functionality, error handling, CLI flags)
- Improves code quality (comments, edge cases, refactoring)
- Adds tests where missing
- Rewrites README.md to document all changes

### Bug Hunter
- Actually **runs** the code — doesn't just read it
- Tests edge cases (empty input, large input, weird characters)
- Checks for crashes, unhandled exceptions, resource leaks
- Verifies README instructions work end-to-end
- Fixes every bug found and re-tests after fixing
- Rewrites README.md with bug-fix notes

## 🛠️ Tech Stack

All projects are built with:
- **Python 3** (no external dependencies)
- Standard library only (`curses`, `json`, `random`, `math`, `os`, etc.)
- Each project is a single file or small set of files
- Designed to be immediately runnable — just `python3 <file>`

## 📊 Stats

| Metric | Value |
|---|---|
| Total projects | 3 |
| Total lines of code | ~3,000+ |
| Pipeline cycles completed | 3 |
| Bugs found & fixed | 7+ |
| Tests added | 21+ |

---

*Powered by [Hermes Agent](https://hermes-agent.nousresearch.com/) autonomous cron jobs.*