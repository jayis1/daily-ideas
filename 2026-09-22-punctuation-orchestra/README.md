# Punctuation Orchestra

Punctuation Orchestra is a small, offline Python command-line program that turns text into a deterministic ASCII orchestra score. Letters become melody notes, and selected punctuation marks conduct percussion hits. Authored by jayis1.

## Features

- Maps letters A through G, case-insensitively, to melody notes.
- Maps `.`, `,`, `!`, `?`, `:`, `;`, and `-` to named percussion instruments and sounds.
- Reports each punctuation hit's zero-based character position in JSON.
- Accepts text arguments, a UTF-8 file, or piped standard input.
- Renders a readable terminal score or stable, indented JSON.
- Limits output with `--max-hits` while preserving source positions; `0` produces no hits.
- Rejects simultaneous text and file/stdin input sources.
- Provides `--help` and `--version`.
- Uses only the Python standard library and makes no network requests.

## Requirements and installation

- Python 3.10 or newer
- No third-party packages

There is nothing to install. From this directory, verify the script with:

```bash
python3 -m py_compile punctuation_orchestra.py
```

## Usage

Arrange a phrase as a human-readable score:

```bash
python3 punctuation_orchestra.py "Hello, world!"
```

Read UTF-8 text from a file:

```bash
python3 punctuation_orchestra.py --file punctuation_orchestra.py
```

Read a phrase from a shell pipeline:

```bash
echo 'Pipe?!' | python3 punctuation_orchestra.py --stdin --json
```

Emit JSON from an argument:

```bash
python3 punctuation_orchestra.py "Hi?!" --json
```

Keep only the first two percussion hits:

```bash
python3 punctuation_orchestra.py "Wait... really?!" --max-hits 2
```

Inspect command-line options or the version:

```bash
python3 punctuation_orchestra.py --help
python3 punctuation_orchestra.py --version
```

## Output and behavior

The program scans characters from left to right. The first sixteen supported melody letters become notes. Each supported punctuation mark becomes a percussion hit unless `--max-hits N` limits collection. Positions in JSON are zero-based Python character positions. Whitespace, unsupported punctuation, and other characters do not produce instruments.

A phrase with no letters or punctuation renders as a silent manuscript. An empty text argument is valid in JSON mode. Missing input, unreadable files, invalid width, and negative hit limits exit with status `2`; successful output, `--help`, and `--version` exit with status `0`. Standard-input mode reads until EOF and is useful for composing the tool with other command-line programs.

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

Example human-readable output:

```text
PUNCTUATION ORCHESTRA
"Hello, world!"

Melody : G-F
Rhythm : , tss | ! KRAK

Conductor's notes:
  beat  6: hat     tss
  beat 13: crash   KRAK
```

JSON output contains `text`, `melody`, and a `hits` array. Each hit contains `position`, `symbol`, `instrument`, and `sound`.

## Testing

Run the focused test suite:

```bash
python3 -m pytest -q test_punctuation_orchestra.py
```

The tests cover rendering, JSON positions, missing input, width validation, version output, piped stdin, hit limits including zero, conflicting input sources, and UTF-8 file handling.

## Known limitations

- This is a text-only score generator, not an audio synthesizer.
- File input must be valid UTF-8.
- Very large input can require substantial memory and output space; use `--max-hits` to bound percussion output.
- Standard-input mode waits for the producer to close the pipe before rendering.
