# Daily Ideas

A growing collection of small, runnable coding projects by jayis1. Each dated directory is an independent experiment with its own source code, README, and (when practical) tests. The collection favors local-first programs that can be explored from a terminal without accounts or network services.

## Latest project

### Argument X-Ray — `2026-09-28-argument-xray/`

A dependency-free Python CLI that exposes exact argument boundaries, byte lengths, invisible characters, and a safely quoted POSIX replay command.

```bash
cd 2026-09-28-argument-xray
python3 argument_xray.py --command demo '' 'two words' '*.txt' "can't"
```

Previous project: [Path Collision Scout](2026-09-28-path-collision-scout/), a preflight checker for filename collisions during migrations.

## Running projects

Browse the dated directories to find terminal games, generators, simulations, puzzles, visualizations, and utilities. Each project README documents its exact requirements and launch command. Most Python projects run directly with Python 3.8+; check the local README for exceptions.

## Repository layout

```text
daily-ideas/
├── README.md                         # Collection index
├── YYYY-MM-DD-project-name/          # Independent project
│   ├── README.md
│   ├── program files
│   └── tests (where included)
└── .github/workflows/                # Repository validation
```

## Principles

- Keep each idea small enough to understand and run in one sitting.
- Prefer deterministic, dependency-light, offline demos.
- Document real commands and observed behavior rather than placeholders.
- Keep projects independent so an experiment can be reused without a shared framework.

## Requirements

Python 3.8+ covers most projects. Individual READMEs are authoritative for additional runtimes or optional dependencies.

## License

Projects are authored by jayis1 and inherit the licensing terms established by the repository.
