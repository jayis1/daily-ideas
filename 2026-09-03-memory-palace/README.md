# Memory Palace

Memory Palace turns plain-text notes into a small, navigable knowledge graph. Each paragraph becomes a room (or, for a single paragraph, each sentence becomes a room), useful words become room labels, and shared words become weighted doors between rooms.

It is a transparent, deterministic command-line tool for finding threads in journals, research notes, meeting dumps, story outlines, and other text—without external packages or an AI service.

## Features

- Splits notes into rooms on blank lines, with sentence fallback for single-paragraph prose.
- Extracts frequent, non-stopword keywords with deterministic alphabetical tie-breaking.
- Configures how many keywords are retained per room with `--keywords`.
- Builds weighted, bidirectional links from shared keywords.
- Filters noisy links with `--min-shared`.
- Renders a readable terminal map showing rooms, doors, and shared threads.
- Provides an interactive browser with room-number lookup and seeded random jumps.
- Searches all room text with `--find`, ranking rooms by matching query terms and showing excerpts.
- Exports JSON containing rooms, links, and graph statistics.
- Handles missing files, invalid options, empty input, EOF, and Ctrl-C cleanly.
- Includes a standard-library test suite.

## Requirements and installation

Python 3.9 or newer is recommended. There are no runtime dependencies.

```bash
git clone https://github.com/jayis1/daily-ideas.git
cd daily-ideas/2026-09-03-memory-palace
python3 memory_palace.py --help
```

Run tests with `pytest` if it is available:

```bash
python3 -m pytest -q
```

## Quick start

Use the built-in example interactively:

```bash
python3 memory_palace.py
```

Use your own UTF-8 notes. Blank lines make room boundaries explicit:

```bash
python3 memory_palace.py notes.txt
```

Print a non-interactive map:

```bash
python3 memory_palace.py notes.txt --map
```

Require at least two shared keywords and retain seven keywords per room:

```bash
python3 memory_palace.py research.txt --map --min-shared 2 --keywords 7
```

Search for rooms related to several words:

```bash
python3 memory_palace.py notes.txt --find "harbor storm"
```

Export the complete graph for another program:

```bash
python3 memory_palace.py notes.txt --json > palace.json
```

Check the installed script version:

```bash
python3 memory_palace.py --version
```

## Example

Given this `notes.txt`:

```text
The baker keeps a notebook of sourdough experiments.

The notebook mentions a warm oven and a blue ceramic bowl.

A blue bowl sits beside the garden seeds.
```

`python3 memory_palace.py notes.txt --map` produces a map like:

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

In interactive mode, enter a room number to read its original text, `random` to jump to a room, or `q` to exit. Piping input or pressing Ctrl-C exits instead of leaving an exception on the terminal.

A search such as `--find "blue bowl"` lists matching rooms, their matched terms, and a short excerpt. Search terms are normalized with the same lightweight tokenizer used for keywords.

## JSON format

The JSON export has:

- `version`: export schema version.
- `rooms`: room number, generated title, original text, and extracted keywords.
- `links`: room endpoints, sorted shared keywords, and link weight.
- `stats`: `room_count` and `link_count`.

Room numbers follow source order, so exports can be referenced consistently by other tools.

## How it works

Words are lowercased and extracted with a small English-oriented regular expression. A built-in stopword list removes common connective words. The most frequent remaining words are retained per room; ties are alphabetical. Two rooms receive a link when their retained keyword sets share at least `--min-shared` terms. Link weight equals the number of shared terms.

Search scans the original room text rather than only retained keywords, so `--find` can locate a term that did not make a room's keyword shortlist.

## Limitations

This is deliberately lightweight: it does not understand synonyms, spelling variants, stemming, or semantics. “Ship” and “boat” will not connect unless the source repeats a word they share. The tokenizer is primarily English-oriented, and very short notes may have no keywords or doors.

## License

Use, modify, and learn from it freely.
