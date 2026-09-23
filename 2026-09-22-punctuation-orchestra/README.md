# Punctuation Orchestra

Punctuation Orchestra is a small, offline Python command-line program by jayis1 that turns text into a deterministic ASCII orchestra score. Letters become melody notes, and selected punctuation marks conduct percussion hits. It is a text toy, not an audio synthesizer.

## Features

- Maps letters A through G, case-insensitively, to melody notes (`C` through `B`), using the first sixteen supported letters.
- Maps `.`, `,`, `!`, `?`, `:`, `;`, and `-` to named instruments and sounds.
- Reports punctuation positions as zero-based character positions in JSON.
- Accepts positional text, a UTF-8 file, or piped standard input.
- Renders a readable terminal score or stable, indented JSON.
- Limits output with `--max-hits` while preserving source positions; `0` produces no hits.
- Rejects conflicting text, file, and standard-input sources.
- Keeps control characters out of the displayed title so pasted or piped text cannot emit terminal escape sequences.
- Reports missing files, invalid UTF-8, invalid widths, and negative hit limits as concise command-line errors.
- Provides `--help` and `--version` (currently version 1.3.0).
- Uses only the Python standard library and makes no network requests.

## Requirements and installation

- Python 3.10 or newer
- No third-party packages are required.

There is nothing to install. From this directory, verify the source compiles:

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

A human-readable score looks like this:

```text
PUNCTUATION ORCHESTRA
"Hello, world!"

Melody : G-F
Rhythm : , tss | ! KRAK

Conductor's notes:
  beat  6: hat     tss
  beat 13: crash   KRAK
```

The percussion mapping is:

| Symbol | Instrument | Sound |
| --- | --- | --- |
| `.` | kick | `boom` |
| `,` | hat | `tss` |
| `!` | crash | `KRAK` |
| `?` | bell | `ding` |
| `:` | rim | `tik` |
| `;` | tom | `tok` |
| `-` | shaker | `sha` |

JSON output contains `text`, `melody`, and a `hits` array. Each hit contains `position`, `symbol`, `instrument`, and `sound`. Positions are zero-based Python character positions. Whitespace, unsupported punctuation, and other characters do not produce instruments.

An empty phrase is valid and produces a silent manuscript. Missing input, unreadable files, invalid UTF-8, invalid width, and negative hit limits exit with status `2`; successful output, `--help`, and `--version` exit with status `0`. Standard-input mode reads until EOF, so it works with shell pipelines.

## Testing

Run the focused test suite:

```bash
python3 -m pytest -q test_punctuation_orchestra.py
```

The tests cover rendering, JSON positions, missing input, width validation, version output, piped stdin, hit limits including zero, conflicting input sources, invalid UTF-8 files, and terminal-control-character sanitization.

## Known issues and limitations

- This is a text-only score generator, not an audio synthesizer.
- File input must be valid UTF-8.
- Very large input can require substantial memory and output space; use `--max-hits` to bound percussion output.
- Standard-input mode waits for the producer to close the pipe before rendering.
- Non-printable characters are replaced with spaces in the human-readable title, while JSON preserves the original input text.

## Changelog

### 1.3.0 — 2026-09-23

- Fixed terminal escape/control characters leaking into human-readable titles.
- Added a regression test for control-character sanitization.
- Re-ran the full focused test suite and boundary-input checks.

### 1.3.0 — Previous fixes

- Added piped stdin input and explicit input-source validation.
- Added bounded percussion hits with `--max-hits`, including the zero-hit case.
- Added friendly handling for invalid UTF-8 files.
