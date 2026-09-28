# Argument X-Ray

Argument X-Ray is a dependency-free Python CLI that reveals exactly which strings survive shell parsing into a program's argument vector. It makes empty values, whitespace, control characters, Unicode byte lengths, and shell-sensitive characters visible, then can build a safely quoted POSIX replay command.

## Why

A command copied from a bug report may look right while passing the wrong boundaries: an empty value disappears, a wildcard expands, or two words become two arguments. Argument X-Ray provides a small local target for inspecting those boundaries without running the command being debugged.

## Requirements

- Python 3.8 or newer
- No third-party packages or network access

## Run

From the repository root:

```bash
cd 2026-09-28-argument-xray
python3 argument_xray.py --command demo '' 'two words' '*.txt' "can't"
```

Verified output:

```text
Argument X-Ray: 4 arguments
[0] ''
    characters: 0; UTF-8 bytes: 0; flags: empty
[1] 'two words'
    characters: 9; UTF-8 bytes: 9; flags: whitespace
[2] '*.txt'
    characters: 5; UTF-8 bytes: 5; flags: shell-sensitive
[3] "can't"
    characters: 5; UTF-8 bytes: 5; flags: shell-sensitive
Replay (POSIX shell):
demo '' 'two words' '*.txt' 'can'"'"'t'
```

The replay line uses POSIX shell quoting and reproduces the inspected arguments without executing them. `--command` is only a label placed at the start of that line.

## Inspect tricky values

Show each Unicode code point:

```bash
python3 argument_xray.py --codepoints $'line\nbreak' '☃'
```

Use `--` before argument values that look like this tool's own options:

```bash
python3 argument_xray.py --command my-tool -- --dry-run -n
```

Emit a JSON report for another program:

```bash
python3 argument_xray.py --json --command demo '' 'two words'
```

The operating system cannot place a NUL byte inside a command-line argument, so Argument X-Ray cannot inspect one. Its replay syntax targets POSIX shells; it is not PowerShell or `cmd.exe` syntax.

## Tests

Run the focused suite from this directory:

```bash
python3 -m unittest -v
```

The tests cover safe and sensitive shell quoting, apostrophes, empty values, POSIX replay round trips, Unicode character and byte counts, control characters, code-point output, JSON output, option-like arguments, and the zero-argument case.
