# Punctuation Orchestra

Punctuation Orchestra is a tiny, offline Python CLI that turns ordinary text into a deterministic ASCII orchestra score. Letters become a simple melody, while punctuation marks conduct percussion: commas whisper on the hi-hat, question marks ring bells, and exclamation marks crash the cymbals.

## Features

- Converts letters into a compact, repeatable melody.
- Converts seven punctuation marks into named instruments and sounds.
- Accepts a phrase or a UTF-8 text file.
- Supports human-readable scores and stable JSON output.
- Validates input and width errors with friendly messages.
- Uses only the Python standard library.

## Why keep it?

It makes punctuation feel alive: paste in a message, a poem, or a commit description and discover the tiny band hiding inside it.

## Installation

Requirements: Python 3.8 or newer. No third-party packages are needed.

From the project directory:

```bash
python3 -m py_compile punctuation_orchestra.py
```

## How to run

From this directory:

```bash
python3 punctuation_orchestra.py "Hello, world!"
```

From the repository root:

```bash
python3 2026-09-22-punctuation-orchestra/punctuation_orchestra.py "Hello, world!"
```

Use a file as input:

```bash
python3 punctuation_orchestra.py --file ../README.md
```

Ask for machine-readable output:

```bash
python3 punctuation_orchestra.py "Hi?!" --json
```

## Usage examples

The command below was executed during verification:

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

JSON output records the exact character positions, so another program can remix the score:

```text
$ python3 punctuation_orchestra.py "Hi?!" --json
{
  "hits": [
    {
      "instrument": "bell",
      "position": 2,
      "sound": "ding",
      "symbol": "?"
    },
    {
      "instrument": "crash",
      "position": 3,
      "sound": "KRAK",
      "symbol": "!"
    }
  ],
  "melody": "(no melody)",
  "text": "Hi?!"
}
```

## What it does

The program scans input from left to right. The first sixteen letters in the set `A`–`G` become notes. Each supported punctuation mark becomes a percussion hit with its original zero-based character position. Unsupported punctuation and whitespace are left alone.

Supported percussion: `.` kick, `,` hi-hat, `!` crash, `?` bell, `:` rim, `;` tom, and `-` shaker.

## Testing

Run the four unit tests:

```bash
python3 -m pytest -q test_punctuation_orchestra.py
```

The tests cover normal rendering, JSON positions, missing input, and invalid widths.

## Limitations

This is intentionally a text-only score, not an audio synthesizer. It does not make network requests, require an account, or modify the input file.

## Author

Authored by jayis1.
