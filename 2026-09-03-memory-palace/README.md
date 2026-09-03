# Memory Palace

Memory Palace is a dependency-free Python CLI that turns UTF-8 plain-text notes into a small, navigable knowledge graph. Each paragraph becomes a room; a single paragraph is split into sentences. Frequent content words label rooms, and shared keywords create weighted links between them.

It is useful for finding recurring threads in journals, research notes, meeting dumps, story outlines, and other text without an AI service or external runtime package.

## Features

- Splits notes on blank lines, with sentence fallback for a single paragraph.
- Preserves Unicode words such as `café`, `naïve`, and `résumé`.
- Extracts frequent non-stopword keywords with deterministic alphabetical tie-breaking.
- Controls the number of retained keywords with `--keywords`.
- Builds weighted, bidirectional links from shared keywords.
- Filters links with `--min-shared`.
- Prints a readable terminal map with rooms, doors, and shared threads.
- Provides an interactive browser with room lookup and seeded random jumps.
- Searches original room text with `--find`, including terms omitted from keyword lists.
- Exports rooms, links, and graph statistics as JSON.
- Handles missing files, invalid options, empty input, EOF, and Ctrl-C cleanly.
- Includes automated tests using pytest.

## Requirements and installation

Python 3.9 or newer is recommended. There are no runtime dependencies.

```bash
git clone https://github.com/jayis1/daily-ideas.git
cd daily-ideas/2026-09-03-memory-palace
python3 memory_palace.py --help
```

Run the test suite:

```bash
python3 -m pytest -q
```

## Usage

Use the built-in example interactively:

```bash
python3 memory_palace.py
```

Read a UTF-8 notes file (blank lines define room boundaries):

```bash
python3 memory_palace.py notes.txt
```

Print a non-interactive map:

```bash
python3 memory_palace.py notes.txt --map
```

Require two shared keywords and retain seven keywords per room:

```bash
python3 memory_palace.py research.txt --map --min-shared 2 --keywords 7
```

Search for rooms containing one or more query terms. Results are ranked by the number of matching terms:

```bash
python3 memory_palace.py notes.txt --find "harbor storm"
```

Export the graph for another program:

```bash
python3 memory_palace.py notes.txt --json > palace.json
```

Make random interactive jumps reproducible and inspect the version:

```bash
python3 memory_palace.py --seed 42
python3 memory_palace.py --version
```

`--json`, `--find`, and `--map` are non-interactive output modes. If more than one is supplied, JSON takes precedence, followed by search, then map.

## Example

Given:

```text
The baker keeps a notebook of sourdough experiments.

The notebook mentions a warm oven and a blue ceramic bowl.

A blue bowl sits beside the garden seeds.
```

`python3 memory_palace.py notes.txt --map` produces output like:

```text
MEMORY PALACE
============================================================
#01 The Baker Keeps A Notebook [baker, experiments, keeps, notebook, sourdough]
     doors: #2
#02 The Notebook Mentions A [blue, bowl, ceramic, mentions, notebook]
     doors: #1, #3
#03 A Blue Bowl Sits [beside, blue, bowl, garden, seeds]
     doors: #2

SHARED THREADS
------------------------------------------------------------
#1 <-> #2: notebook
#2 <-> #3: blue, bowl
```

In interactive mode, enter a room number to read its original text, `random` to jump to a room, or `q` to exit. Piped input and Ctrl-C exit without a traceback.

## JSON format

The JSON export contains:

- `version`: export schema version (`1`).
- `rooms`: room number, generated title, original text, and extracted keywords.
- `links`: room endpoints, sorted shared keywords, and link weight.
- `stats`: `room_count` and `link_count`.

Room numbers follow source order, so exports can be referenced consistently by other tools.

## How it works

Words are lowercased and extracted with a Unicode-aware regular expression. Letters may contain internal apostrophes or hyphens; digits and underscores are not treated as keywords. A built-in English stopword list removes common connective words. The most frequent remaining words are retained per room, with alphabetical tie-breaking. Two rooms receive a link when their retained keyword sets share at least `--min-shared` terms; link weight is the number of shared terms.

Search scans original room text rather than only retained keywords, so `--find` can locate a term that did not make a room's keyword shortlist.

## Known limitations

This is deliberately lightweight: it does not understand synonyms, spelling variants, stemming, or semantics. “Ship” and “boat” will not connect unless the source repeats a word they share. The stopword list is English-oriented, and very short notes may have no keywords or doors.

## Changelog

### 1.1.1

- Fixed loss of accented and other Unicode letters in keywords and generated titles.
- Added regression coverage for Unicode parsing and title rendering.
- Documented output-mode precedence and current limitations.

### 1.1.0

- Added ranked `--find` search, configurable keyword limits, `--version`, JSON statistics, validation, and safer interactive behavior.

## License

Use, modify, and learn from it freely.
