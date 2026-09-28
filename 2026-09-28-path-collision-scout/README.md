# Path Collision Scout

Path Collision Scout is a dependency-free Python CLI that predicts filename collisions before paths are copied, flattened, or moved to a case-insensitive filesystem. It compares paths locally without touching the files they name.

## Why

A folder merge can silently overwrite `Logo.svg` with `logo.svg`, while visually identical Unicode names can be stored as different byte sequences. This tool exposes those conflicts before a migration begins.

## Requirements

- Python 3.8 or newer
- No third-party packages or network access

## Run

From the repository root:

```bash
cd 2026-09-28-path-collision-scout
python3 path_collision_scout.py --flatten \
  'draft/Logo.svg' 'final/logo.svg' 'final/banner.svg'
```

Verified output and exit status (`1` means collisions were found):

```text
Found 1 collision across 3 paths:
- logo.svg
  <- draft/Logo.svg
  <- final/logo.svg
```

Without `--flatten`, directory components remain part of each destination key. Comparisons are case-insensitive and NFC-normalized by default. Optional rules model other migrations:

```bash
python3 path_collision_scout.py --portable 'notes/report.txt' 'notes/report.txt. '
python3 path_collision_scout.py --normalization NFKC 'prices/1.txt' 'prices/１.txt'
python3 path_collision_scout.py --case-sensitive 'Logo.svg' 'logo.svg'
```

Read larger inventories from a UTF-8 file containing one path per line. Blank lines and lines beginning with `#` are ignored:

```bash
python3 path_collision_scout.py --file paths.txt --flatten --json
```

A clean scan exits with status `0`; a scan containing collisions exits with status `1`. Invalid input exits with status `2`. Use `--help` to see every option.

## Comparison rules

- `/` and `\\` are both accepted as separators.
- Empty paths and `.` or `..` components are rejected.
- NFC normalization combines canonically equivalent Unicode spellings.
- NFKC additionally combines compatibility variants such as full-width characters.
- `--portable` trims spaces and periods from component endings to reveal names that collide on stricter destinations.
- Duplicate source entries are reported because they still target the same destination identity.

## Tests

Run the focused suite from this directory:

```bash
python3 -m unittest -v
```

The tests cover separator handling, traversal rejection, Unicode normalization, case sensitivity, flattening, portable trimming, path files, text output, JSON output, and exit statuses.
