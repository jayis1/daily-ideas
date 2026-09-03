# Memory Palace

Turn any plain-text notes into a small navigable knowledge graph. **Memory Palace** treats each paragraph (or sentence in a single-paragraph file) as a room, extracts distinctive keywords, and creates doors between rooms that share concepts. It is a dependency-free way to discover hidden threads in a journal, story outline, meeting notes, or research dump.

## Features

- Splits text into rooms using blank lines, with sentence fallback for prose pasted as one block.
- Extracts the five most useful repeated words per room while ignoring common stopwords.
- Builds weighted, bidirectional doors from shared keywords.
- Shows a readable terminal map and the connecting threads.
- Offers an interactive room browser with random jumps.
- Exports the complete graph as machine-readable JSON.
- Uses only the Python standard library and works with UTF-8 text files.

## Install

No package installation is required. Python 3.9+ is recommended.

```bash
git clone https://github.com/jayis1/daily-ideas.git
cd daily-ideas/2026-09-03-memory-palace
python3 memory_palace.py --help
```

## Run

Run the built-in miniature example as an interactive palace:

```bash
python3 memory_palace.py
```

Give it your own notes. Separate rooms with blank lines for the most useful result:

```bash
python3 memory_palace.py notes.txt
```

Print only the map, which is convenient for scripts and screenshots:

```bash
python3 memory_palace.py notes.txt --map
```

Require two shared keywords before connecting rooms, reducing noisy doors in a large document:

```bash
python3 memory_palace.py research.txt --map --min-shared 2
```

Export the graph for another tool:

```bash
python3 memory_palace.py notes.txt --json > palace.json
```

## Usage example

For this `notes.txt`:

```text
The baker keeps a notebook of sourdough experiments.

The notebook mentions a warm oven and a blue ceramic bowl.

A blue bowl sits beside the garden seeds.
```

`python3 memory_palace.py notes.txt --map` prints rooms and doors similar to:

```text
MEMORY PALACE
============================================================
#01 The Baker Keeps A Notebook [baker, keeps, notebook, sourdough, experiments]
     doors: #2
#02 The Notebook Mentions A [blue, bowl, mentions, notebook, oven]
     doors: #1, #3
#03 A Blue Bowl Sits [blue, bowl, beside, garden, seeds]
     doors: #2

SHARED THREADS
------------------------------------------------------------
#1 <-> #2: notebook
#2 <-> #3: blue, bowl
```

In interactive mode, enter a room number to read it, `random` to jump to a room, or `q` to leave.

## What it does

The program is intentionally transparent rather than AI-powered: it tokenizes words, counts each room's terms, removes a small built-in stopword list, and keeps the most frequent remaining words (ties are alphabetical). A door is created when two rooms share at least `--min-shared` keywords. This makes the same input produce the same map every time, while still exposing surprising connections in material you already wrote.

The JSON format contains two arrays:

- `rooms`: room number, generated title, original text, and extracted keywords.
- `links`: room endpoints, shared keywords, and link weight.

## Limitations

The keyword extractor is English-oriented and deliberately lightweight. It does not understand synonyms, spelling variants, or meaning; “ship” and “boat” will not connect unless the source text uses the same word. Very short notes may have no doors, which is a useful signal that they do not share vocabulary.

## License

Use, modify, and learn from it freely.
