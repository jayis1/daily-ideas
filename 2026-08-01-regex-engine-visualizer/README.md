# Regex Engine Visualizer

A tiny **backtracking regex engine** that *records every step* of the matching
process and then renders a readable, colorized trace of how a pattern is
applied to an input string — showing the cursor position, the active pattern
node, and every **match / fail / backtrack** decision.

This is an **educational tool**: it does **not** use Python's `re` module for
matching. It implements its own recursive-descent parser and generator-based
backtracking matcher, so you can see exactly how a regex engine "thinks" as
it walks the input.

## Features

### Engine

- **Hand-written regex engine** — no `re` module involved in matching.
- **Step-by-step trace** — every `TRY`, `MATCH`, `FAIL`, `YIELD` (backtrack
  candidate), `STOP`, and `LEAVE` is logged with the cursor position and the
  active AST node.
- **Colorized cursor view** — the input string is re-rendered at every step
  with the current position highlighted.
- **Unanchored search** — like `re.search`, tries the pattern at every start
  position until it matches.
- **Step-limit safety** — guards against catastrophic backtracking with a
  configurable step cap.
- **Verified against `re`** — the engine's match spans agree with Python's
  `re` module on a battery of cross-check cases.

### Supported syntax

| Feature | Syntax | Example |
|---|---|---|
| Literals | `abc` | `hello` |
| Any char | `.` | `a.c` |
| Star (greedy/lazy) | `a*`, `a*?` | `a*b` |
| Plus (greedy/lazy) | `a+`, `a+?` | `a+b` |
| Optional (greedy/lazy) | `a?`, `a??` | `colou?r` |
| **Bounded repetition** (greedy/lazy) | `a{n}`, `a{n,}`, `a{n,m}`, `a{3,5}?` | `a{2,4}` |
| Char class | `[abc]`, `[a-z]`, `[^0-9]` | `[0-9]+` |
| **Shorthands in classes** | `[\d]`, `[\s]`, `[\D]`, `[a-z\d]` | `[\d\s]+` |
| Anchors | `^`, `$` | `^foo$` |
| **Word boundary** | `\b`, `\B` | `\bfoo\b` |
| Groups | `(...)` | `(ab)+` |
| Alternation | `a\|b` | `cat\|dog` |
| Escapes | `\d \w \s \D \W \S \b \B \. \\ \n \t \r \f \v \0 \a` | `\d+` |

> Items in **bold** are new in this release (v1.1.0). See
> [Changelog](#changelog) below.

### CLI

- `--demo` — run curated built-in examples
- `--no-color` — plain-text trace (for piping / logs)
- `--steps` — show every step instead of truncating
- `--max-steps N` — cap steps displayed per example
- `--quiet` / `-q` — machine-friendly one-line result for scripting
- `--version` — print version and exit
- `--help` — full usage

## Install

No dependencies beyond the Python standard library. Requires Python 3.8+.

```bash
python3 regex_viz.py --demo
```

## How to Run

```bash
# Match a pattern against an input string
python3 regex_viz.py '<pattern>' '<input>'

# Show every step (don't truncate the trace)
python3 regex_viz.py 'a.*z' 'abczxyz' --steps

# Disable ANSI colors (for piping / logs)
python3 regex_viz.py 'a*b' 'aaaab' --no-color

# Scripting mode: a single parseable line
python3 regex_viz.py '\d{3}-\d{4}' 'call 555-1234' --quiet
# -> MATCH 5 13 '555-1234'

# Run the built-in demo examples
python3 regex_viz.py --demo

# Adjust how many steps are shown per example in demo mode
python3 regex_viz.py --demo --max-steps 20

# Print the version
python3 regex_viz.py --version

# Run the test suite (61 cases)
python3 test_regex_viz.py
```

## Usage Examples

### Greedy star + backtracking

```
$ python3 regex_viz.py 'a.*z' 'abczxyz' --no-color --steps
Pattern : a.*z
Input   : 'abczxyz' (len=7)
Steps   : 13

   0  pos=  0  TRY       Anchor(^)           search from pos 0
      [a]bczxyz
   1  pos=  0  MATCH     Lit('a')            input[0] == 'a'
      [a]bczxyz
   2  pos=  1  MATCH     Dot(.)              . matches 'b'
      a[b]czxyz
   ...
   8  pos=  7  FAIL      Dot(.)              . at end of input (or newline)
      abczxyz[<end>]
   9  pos=  7  YIELD     Dot(.)*             * matched 6 times -> pos 7
      abczxyz[<end>]
  10  pos=  7  FAIL      Lit('z')            input[7] != 'z'
      abczxyz[<end>]
  11  pos=  6  YIELD     Dot(.)*             * matched 6 times -> pos 6
      abczxy[z]
  12  pos=  6  MATCH     Lit('z')            input[6] == 'z'
      abczxy[z]

============================================================
RESULT  : MATCH
span     : [0, 7)
matched  : 'abczxyz'
total steps examined: 13
============================================================
```

Notice how the greedy `.*` consumes all the way to the end, fails to find the
final `z`, then **backtracks** one position at a time (the `YIELD` rows) until
`z` matches at position 6.

### Lazy quantifier

```
$ python3 regex_viz.py 'a.*?z' 'abczxyz' --no-color
...
RESULT  : MATCH
span     : [0, 4)
matched  : 'abcz'
```

The lazy `*?` matches as *few* characters as possible, stopping at the first
`z` (position 3) rather than the last.

### Bounded repetition `{n,m}`

```
$ python3 regex_viz.py 'a{3}' 'aaaa' --no-color --max-steps 6
Pattern : a{3}
Input   : 'aaaa' (len=4)
Steps   : 5

   0  pos=  0  TRY       Anchor(^)           search from pos 0
      [a]aaa
   1  pos=  0  MATCH     Lit('a')            input[0] == 'a'
      [a]aaa
   2  pos=  1  MATCH     Lit('a')            input[1] == 'a'
      a[a]aa
   3  pos=  2  MATCH     Lit('a')            input[2] == 'a'
      aa[a]a
   4  pos=  3  YIELD     Lit('a'){3}         Lit('a'){3} -> pos 3
      aaa[a]

============================================================
RESULT  : MATCH
span     : [0, 3)
matched  : 'aaa'
============================================================
```

### Word boundary `\b`

```
$ python3 regex_viz.py '\bfoo\b' 'a foo b' --no-color --quiet
MATCH 2 5 'foo'
```

### Negated shorthands

```
$ python3 regex_viz.py '\D+' 'abc123' --no-color --quiet
MATCH 0 3 'abc'
```

### Char class + unanchored search

```
$ python3 regex_viz.py '[0-9]+' 'year 2026' --no-color
...
RESULT  : MATCH
span     : [5, 9)
matched  : '2026'
```

### Alternation

```
$ python3 regex_viz.py 'cat|dog' 'I have a dog' --no-color
...
RESULT  : MATCH
span     : [9, 12)
matched  : 'dog'
```

### No match

```
$ python3 regex_viz.py '[0-9]+' 'no digits here' --no-color
...
RESULT  : NO MATCH
total steps examined: 45
```

### Built-in demo

```
$ python3 regex_viz.py --demo
Regex Engine Visualizer — Demo
Each example shows the step-by-step backtracking trace.

────────────────────────────────────────────────────────────
DEMO: greedy star then literal
  regex_viz 'a*b' 'aaaab'
...
```

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | The pattern matched. |
| `1` | The pattern did not match. |
| `2` | Parse error (invalid pattern). |

## Quiet / scripting mode

`--quiet` (`-q`) suppresses the full trace and prints exactly one line:

- On a match: `MATCH <start> <end> '<matched-text>'`
- On no match: `NOMATCH`

This makes the tool easy to drop into shell pipelines and scripts.

```
$ if python3 regex_viz.py '\d+' "$input" --quiet | grep -q MATCH; then
>   echo "found a number"
> fi
```

## What It Does

Under the hood, `regex_viz.py`:

1. **Parses** the regex pattern into an AST of `Node` subclasses (`Literal`,
   `AnyChar`, `CharClass`, `Anchor`, `WordBoundary`, `Group`, `Alternation`,
   `Star`, `Plus`, `OptionalNode`, `Repeat`) using a recursive-descent parser.
2. **Matches** the AST against the input using generator-based backtracking.
   Each node's `match()` method is a generator that *yields* successful end
   positions; when a later node fails, control returns to the generator and
   it produces the next candidate — this is exactly backtracking.
3. **Records** every decision as a `Step` (position, node, action, note) on the
   `MatchContext`.
4. **Renders** the recorded steps as a colorized trace with a
   cursor-highlighted view of the input at each point, plus a final summary
   showing the match span and matched substring.

This makes the otherwise-invisible mechanics of regex backtracking — greedy
consumption, lazy matching, alternation branching, anchor checks, bounded
repetition, and the "try / fail / backtrack" loop — fully visible and easy to
follow.

## Files

| File | Description |
|---|---|
| `regex_viz.py` | The engine, parser, matcher, and CLI. |
| `test_regex_viz.py` | Correctness + smoke tests (61 cases). |

## Changelog

### v1.1.0

**Bug fixes:**
- Fixed `\D`, `\W`, `\S` (uppercase shorthands) not matching standalone — they
  were incorrectly wrapped as `Literal(char=CharClass)` and never matched.
- Fixed `[\D]`, `[\W]`, `[\S]` (negated shorthands inside character classes)
  crashing with `TypeError: '<=' not supported between instances of
  'CharClass' and 'str'`.
- Fixed lazy `+?` and `??` quantifiers being **greedy** in practice — the
  `greedy` flag was parsed but ignored by `Plus` and `OptionalNode`.

**New features:**
- Added bounded repetition quantifiers: `{n}`, `{n,}`, `{n,m}` (greedy and
  lazy `{n,m}?`).
- Added `\b` and `\B` word-boundary assertions.
- Added `--version` flag.
- Added `--quiet` / `-q` scripting mode (one-line machine-friendly output).
- Added `\f`, `\v`, `\a` escape sequences.
- Negated shorthands (`\D \W \S`) now work correctly inside character classes
  as union members (`[a-z\D]`).
- `\b` inside a character class now means backspace (U+0008), matching `re`.
- Invalid ranges inside classes (e.g. `z-a`) now raise a `ParseError`.
- Trailing-backslash patterns now raise a `ParseError` instead of `IndexError`.
- `{n,m}` with `min > max` is now rejected at parse time.
- A literal `{` that is not a valid quantifier is treated as a literal char.

**Quality:**
- Expanded test suite from 30 to 61 cases, covering all new features and bug
  fixes, plus a version check.
- Added docstrings to all node `match` methods explaining greedy/lazy
  semantics.
- Verified engine output against Python's `re` module on 20 cross-check cases
  (all match).
- Expanded demo mode with 6 new examples showcasing the new features.

### v1.0.0

Initial release: hand-written backtracking regex engine with step-by-step
trace visualization.

## Limitations

- No backreferences, lookaround, or named captures.
- No possessive quantifiers (the engine treats `a*+` as `a*` followed by a `+`
  quantifier on the star node, which is benign).
- The step cap prevents runaway backtracking but very pathological patterns
  will hit it and stop early.
- Greedy mandatory-minimum matches in `{n}` take the first success of each
  child (standard greedy behavior); only the *extra* matches beyond the
  minimum are backtrackable.

## License

MIT — do whatever you like.