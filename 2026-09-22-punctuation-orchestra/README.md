# Punctuation Orchestra

Punctuation Orchestra is a tiny, offline Python CLI that turns text into a deterministic ASCII orchestra score: letters become a melody, while punctuation conducts the percussion.

It is for curious terminal users, writers, and developers who want to paste a phrase, poem, or commit message and discover the tiny band hiding inside it.

## Features

- Maps letters `A` through `G` (case-insensitive) to a compact melody.
- Maps `.`, `,`, `!`, `?`, `:`, `;`, and `-` to named percussion instruments.
- Preserves each punctuation hit's zero-based character position in JSON output.
- Accepts either a phrase on the command line or a UTF-8 text file.
- Produces readable ASCII scores or stable, indented JSON.
- Limits long scores with `--max-hits` without changing reported source positions.
- Rejects ambiguous input when both text and `--file` are supplied.
- Provides `--help` and `--version` flags.
- Uses only the Python standard library and never makes network requests.

## Requirements and installation

Python 3.10 or newer is required. There are no third-party packages to install.

Clone the repository, then run the script directly from this directory. An optional syntax check is:

```bash
python3 -m py_compile punctuation_orchestra.py
```

## Basic usage

Arrange a phrase in the terminal:

```bash
python3 punctuation_orchestra.py "Hello, world!"
```

Read a UTF-8 file instead:

```bash
python3 punctuation_orchestra.py --file ../README.md
```

Emit JSON for another program to remix:

```bash
python3 punctuation_orchestra.py "Hi?!" --json
```

Keep a busy message to its first two percussion hits:

```bash
python3 punctuation_orchestra.py "Wait... really?!" --max-hits 2
```

Inspect the available flags or the current version:

```bash
python3 punctuation_orchestra.py --help
python3 punctuation_orchestra.py --version
```

## Example output

```text
$ python3 punctuation_orchestra.py "Hello, world!"
PUNCTUATION ORCHESTRA
"Hello, world!"

Melody : G-F
Rhythm : , tss | ! KRAK

Conductor's notes:
  beat  6: hat     tss
  beat 13: crash   KRAK
```

With JSON output, `python3 punctuation_orchestra.py "Hi?!" --json` reports the text, melody, and hit objects. Each hit contains `position`, `symbol`, `instrument`, and `sound`.

## What it does

The program scans characters from left to right. The first sixteen supported melody letters become notes. Each supported punctuation mark becomes one percussion hit unless `--max-hits N` stops collection after `N` hits. Whitespace, unsupported punctuation, and other characters are ignored for both instruments.

Percussion mapping:

| Symbol | Instrument | Sound |
| --- | --- | --- |
| `.` | kick | `boom` |
| `,` | hat | `tss` |
| `!` | crash | `KRAK` |
| `?` | bell | `ding` |
| `:` | rim | `tik` |
| `;` | tom | `tok` |
| `-` | shaker | `sha` |

A phrase with no letters or punctuation is still rendered as a silent manuscript. An empty command, unreadable file, invalid width, or negative hit limit exits with status `2` and a friendly error. `--help` and `--version` exit with status `0` without requiring input.

## Testing and development

Run the focused test suite:

```bash
python3 -m pytest -q test_punctuation_orchestra.py
```

The tests cover human-readable rendering, JSON positions, missing input, width validation, version output, hit limiting, and conflicting input sources.

## Limitations and privacy

This is a text-only score, not an audio synthesizer. It is deterministic and offline: it does not contact a service, require credentials, or modify input files. File input is read as UTF-8, and very large text can still produce large output unless `--max-hits` is used.

## Author

Authored by jayis1.
