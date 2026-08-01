# Regex Engine Visualizer

A tiny **backtracking regex engine** that *records every step* of the matching
process and then renders a readable, colorized trace of how a pattern is
applied to an input string — showing the cursor position, the active pattern
node, and every **match / fail / backtrack** decision.

This is an **educational tool**: it does **not** use Python's `re` module for
matching. It implements its own recursive-descent parser and generator-based
backtracking matcher, so you can see exactly how a regex engine "thinks" as it
walks the input.

## Features

- **Hand-written regex engine** — no `re` module involved in matching.
- **Step-by-step trace** — every `TRY`, `MATCH`, `FAIL`, `YIELD` (backtrack
  candidate), `STOP`, and `LEAVE` is logged with the cursor position and the
  active AST node.
- **Colorized cursor view** — the input string is re-rendered at every step
  with the current position highlighted.
- **Unanchored search** — like `re.search`, tries the pattern at every start
  position until it matches.
- **Supported syntax:**

  | Feature | Syntax | Example |
  |---|---|---|
  | Literals | `abc` | `hello` |
  | Any char | `.` | `a.c` |
  | Star (greedy/lazy) | `a*`, `a*?` | `a*b` |
  | Plus (greedy/lazy) | `a+`, `a+?` | `a+b` |
  | Optional (greedy/lazy) | `a?`, `a??` | `colou?r` |
  | Char class | `[abc]`, `[a-z]`, `[^0-9]` | `[0-9]+` |
  | Anchors | `^`, `$` | `^foo$` |
  | Groups | `(...)` | `(ab)+` |
  | Alternation | `a\|b` | `cat\|dog` |
  | Escapes | `\d \w \s \D \W \S \. \\ \n \t` | `\d+` |

- **Step-limit safety** — guards against catastrophic backtracking with a
  configurable step cap.
- **Built-in demo mode** with curated examples.

## Install

No dependencies beyond the Python standard library.

```bash
# Python 3.8+ required
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

# Run the built-in demo examples
python3 regex_viz.py --demo

# Adjust how many steps are shown per example in demo mode
python3 regex_viz.py --demo --max-steps 20

# Run the test suite
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

## What It Does

Under the hood, `regex_viz.py`:

1. **Parses** the regex pattern into an AST of `Node` subclasses (`Literal`,
   `AnyChar`, `CharClass`, `Anchor`, `Group`, `Alternation`, `Star`, `Plus`,
   `OptionalNode`) using a recursive-descent parser.
2. **Matches** the AST against the input using generator-based backtracking.
   Each node's `match()` method is a generator that *yields* successful end
   positions; when a later node fails, control returns to the generator and it
   produces the next candidate — this is exactly backtracking.
3. **Records** every decision as a `Step` (position, node, action, note) on the
   `MatchContext`.
4. **Renders** the recorded steps as a colorized trace with a cursor-highlighted
   view of the input at each point, plus a final summary showing the match span
   and matched substring.

This makes the otherwise-invisible mechanics of regex backtracking — greedy
consumption, lazy matching, alternation branching, anchor checks, and the
"try / fail / backtrack" loop — fully visible and easy to follow.

## Files

| File | Description |
|---|---|
| `regex_viz.py` | The engine, parser, matcher, and CLI. |
| `test_regex_viz.py` | Correctness + smoke tests (30 cases). |

## Limitations

- No backreferences, lookaround, or named captures.
- No possessive quantifiers (the engine treats `a*+` as `a*` followed by a `+`
  quantifier on the star node, which is benign).
- The step cap prevents runaway backtracking but very pathological patterns
  will hit it and stop early.

## License

MIT — do whatever you like.