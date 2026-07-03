# Conspiracy Board Generator v2.1

A procedurally generated conspiracy theory board — complete with red-string connections, classified documents, suspicion scores, cycle detection, and timeline events. Generates a unique, visually rich ASCII-art conspiracy board every time.

## Features

- **Procedural board generation** — Randomly places people, organizations, events, and locations on a red-string conspiracy board
- **Connection types** — Entities are linked with labeled connections (CONTACTED, LEAKED TO, WORKS FOR, etc.) with visual strength indicators (━━ strong, ── medium, ·· weak)
- **Suspicion scores** — Each entity gets a computed suspicion level (LOW → MODERATE → HIGH → CRITICAL → EXTREME) based on connections, evidence, and entity type diversity, displayed with progress bars in the legend
- **Cycle detection** — Automatically detects triangular connection patterns (A→B→C→A) and highlights them in the legend with a "⚠ TRIANGULATED CONNECTIONS" section
- **Conspiracy timeline** — Generates dated, classified timeline events linking entities to key moments across 2019–2028, with classification levels like TOP SECRET, SCI, NOFORN
- **Narrative mode** — Produces a classified briefing document with suspicion assessment, connection strength labels, and optional timeline fragments
- **JSON output** — Exports all board data (entities with suspicion scores, connections with strength labels, notes, cycles, timeline) as structured JSON
- **Evidence tags** — Entities can have evidence markers (PHOTO, DOCUMENT, WITNESS, etc.) displayed on the board
- **Cryptic notes** — Redacted sticky notes scattered across the board with conspiracy-themed messages
- **Reproducible seeds** — Use `--seed` for deterministic output; same seed always produces the same board
- **Color and monochrome** — Full ANSI color support with `--no-color` for terminals without color

## Installation

No external dependencies needed — uses only the Python standard library.

```bash
# Just run it directly
python3 conspiracy_board.py

# Or clone the repo
cd ~/daily-ideas
git pull
cd 2026-07-03-conspiracy-board-generator
python3 conspiracy_board.py
```

Requires Python 3.7+ (uses dataclasses).

## Usage

```bash
# Generate a random conspiracy board
python3 conspiracy_board.py

# With a specific seed for reproducibility
python3 conspiracy_board.py --seed 42

# Include narrative briefing
python3 conspiracy_board.py --seed 42 --narrative

# Include classified timeline
python3 conspiracy_board.py --seed 42 --timeline

# Both narrative and timeline
python3 conspiracy_board.py --seed 42 --narrative --timeline

# JSON output (machine-readable)
python3 conspiracy_board.py --seed 42 --json

# No ANSI colors
python3 conspiracy_board.py --no-color

# Custom board dimensions and entity counts
python3 conspiracy_board.py --width 120 --height 50 --people 8 --orgs 4 --connections 15

# Show version
python3 conspiracy_board.py --version
```

### Command-Line Options

| Flag | Default | Description |
|------|---------|-------------|
| `--width` | 90 | Board width in characters |
| `--height` | 45 | Board height in characters |
| `--people` | 5 | Number of person entities |
| `--orgs` | 3 | Number of organization entities |
| `--events` | 3 | Number of event entities |
| `--locations` | 2 | Number of location entities |
| `--connections` | 9 | Number of connections to generate |
| `--notes` | 4 | Number of cryptic notes |
| `--seed` | random | Random seed for reproducibility |
| `--narrative` | off | Print classified narrative briefing |
| `--timeline` | off | Print conspiracy timeline |
| `--json` | off | Output board data as JSON |
| `--no-color` | off | Disable ANSI color codes |
| `--version` | — | Print version and exit |

All entity count arguments must be non-negative integers. Board dimensions are clamped to 40–200 (width) and 20–100 (height). At least 2 entities total are required.

## Testing

```bash
# Run the full test suite (65 tests)
python3 test_conspiracy_board.py
```

Tests cover all major features: board generation, rendering, narrative, timeline, JSON output, suspicion scoring, cycle detection, redaction, and regression tests for all bug fixes.

## Changelog

### v2.1.0 — Bug Fix Release

**Bugs Fixed:**
- **`pick()` crash on negative `n`** — Calling `pick(pool, n)` with a negative `n` would crash with `ValueError` from `random.sample()`. Now returns an empty list for any `n ≤ 0`.
- **Entity name overflow** — Entity names and evidence tags placed near board edges could extend beyond the board boundaries, causing visual corruption. Now clamped to board width with proper truncation.
- **Legend box width inconsistency** — Legend border lines (╔═╗, ╠═╣, ╚═╝) were 2 characters narrower than content lines (║ ... ║), causing misalignment. All lines are now consistently `box_w + 4` characters.
- **Legend entity line overflow** — Entity lines with evidence could exceed the 78-character `box_w`, truncating important info. `box_w` increased from 78 to 100, and evidence display shortened from `"Evidence:"` to `"Ev:"` with max 2 items.
- **Negative CLI arguments** — Passing negative values for `--people`, `--orgs`, `--events`, `--locations`, `--connections`, or `--notes` would cause undefined behavior. Now properly rejected with a helpful error message.
- **Note position overflow** — Cryptic notes placed near board edges could overflow. Note positions are now properly clamped within board margins.

**Tests Added:** 8 new regression tests (57 → 65 total):
- `test_pick_negative_n` — Verifies `pick()` returns `[]` for negative `n`
- `test_pick_negative_n_large` — Verifies `pick()` returns `[]` for large negative `n`
- `test_pick_empty_pool` — Verifies `pick()` returns `[]` from an empty pool
- `test_entity_names_within_board` — Verifies entity names render within board bounds
- `test_entity_evidence_clamped` — Verifies evidence tags don't crash on small boards
- `test_legend_box_consistency` — Verifies all legend lines have the same width
- `test_negative_cli_args_rejected` — Verifies negative CLI arguments are rejected
- `test_version_updated` — Verifies version string format after changes

## License

MIT