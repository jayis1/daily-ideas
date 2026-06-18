# Turing Machine Simulator

A visual, interactive Turing machine simulator with 10 built-in programs, curses-based visualization, text-mode stepping, batch execution, execution tracing, machine validation, execution statistics, and JSON import/export. Explore the fundamentals of computation through animated tape heads and state transitions.

## Features

- **10 Built-in Programs**: Binary increment, unary addition, palindrome checker, 3-state Busy Beaver, binary NOT, 1-counter, binary decrement, unary doubler, binary AND, and string reverser
- **Curses Visualization**: Real-time animated tape display with state highlighting, transition rules, and keyboard controls
- **Text-Mode Stepping**: Step-by-step execution with colored terminal output (no curses dependency)
- **Batch Execution**: Run all programs at once and compare results with execution statistics
- **Execution Trace**: Detailed step-by-step trace showing state, head position, symbols read/written, direction, and tape snapshots (`--trace`)
- **Custom Machines**: Interactive creator for defining your own Turing machines
- **Machine Validation**: Detects unused states, undefined transitions, and orphan states
- **JSON Persistence**: Save and load machine definitions as JSON files
- **Execution Statistics**: Track steps, cells written, tape span, and unique cells visited
- **CLI Flags**: `--version`, `--tape`, `--export`, `--list`, `--create`, `--visual`, `--text`, `--run`, `--trace`

## Built-in Programs

| Program | Description | Input | Output |
|---------|-------------|-------|--------|
| `binary_increment` | Increment a binary number by 1 | `1011` (11) | `1100` (12) |
| `unary_addition` | Add two unary numbers with `+` | `111+11` | `11111` (5 ones) |
| `palindrome_checker` | Check if a binary string is a palindrome | `10101` | ACCEPTED |
| `busy_beaver_3` | The champion 3-state Busy Beaver | (blank) | 6 ones in 13 steps |
| `binary_not` | Flip all bits (NOT operation) | `10110011` | `01001100` |
| `count_ones` | Count 1s in binary, write unary tally after `=` | `10110=` | `10110=\|\|\|` |
| `binary_decrement` | Decrement a binary number by 1 | `1100` (12) | `1011` (11) |
| `unary_doubler` | Double a unary number | `111` (3) | `111111` (6) |
| `binary_and` | Bitwise AND of two equal-length binary strings separated by `&` | `1100&1010` | `1100&1000` |
| `string_reverser` | Reverse a binary string | `110` | `011` |

## How to Install

No external dependencies needed — uses only Python 3 standard library:

```bash
cd ~/daily-ideas/2026-06-18-turing-machine-simulator
```

Requires Python 3.6+ (tested with 3.11+). The curses module is part of the standard library on most systems.

## How to Run

### Show Version

```bash
python3 turing.py --version
```

### Visual Mode (Interactive, requires a terminal)

```bash
python3 turing.py                    # Show menu, pick a program
python3 turing.py --visual           # Same as above
python3 turing.py --run busy_beaver_3  # Run specific program visually
```

### Text Mode (Step-by-step output, no curses)

```bash
python3 turing.py --text                       # Default program (binary_increment)
python3 turing.py --text --run palindrome_checker
python3 turing.py --text --speed 0.1           # Faster stepping
```

### Batch Mode (Run all programs, show results with statistics)

```bash
python3 turing.py --run all
python3 turing.py --run all --max-steps 500
```

### Execution Trace (Detailed step-by-step trace)

```bash
python3 turing.py --trace                       # Default program (binary_increment)
python3 turing.py --trace --run binary_not      # Trace binary NOT
python3 turing.py --trace --run busy_beaver_3   # Trace Busy Beaver
```

The `--trace` flag produces a detailed execution log showing each step with the current state, head position, symbol read, symbol written, movement direction, next state, and a tape snapshot. Each step is numbered so you can follow the exact execution path.

### Override Tape Input

```bash
python3 turing.py --tape 1010 --run binary_increment   # Custom input
python3 turing.py --tape 1111 --run unary_doubler       # Double four ones
python3 turing.py --tape 1100 --run string_reverser     # Reverse 1100
python3 turing.py --tape 1111&0101 --run binary_and     # AND two numbers
```

### Export a Machine to JSON

```bash
python3 turing.py --export busy_beaver_3    # Saves to machines/busy_beaver_3.json
python3 turing.py --export unary_doubler    # Saves to machines/unary_doubler.json
```

### List Available Programs

```bash
python3 turing.py --list
```

### Custom Machine (Interactive Creator)

```bash
python3 turing.py --create
```

### Load Machine from JSON

```bash
python3 turing.py --load machines/my_machine.json
python3 turing.py --load machines/my_machine.json --visual
python3 turing.py --load machines/my_machine.json --text
```

## Usage Examples

### Visual Mode Controls

When running in visual (curses) mode:

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume |
| `S` | Execute one step (when paused) |
| `R` | Reset to initial state |
| `+` | Speed up (decrease delay) |
| `-` | Slow down (increase delay) |
| `Q` | Quit |

### Example: Binary Increment

```
$ python3 turing.py --text --run binary_increment

============================================================
  Machine: Binary Increment
  Increment a binary number by 1
  Input: 1011
============================================================

  Step    0  State: q0
  ..._______________[1]011________...

  Step    1  State: q0
  ...______________0[0]11_________...

  ✓ ACCEPTED after 9 steps
  Final tape: 1100
  Stats: Steps: 9  Cells written: 9  Tape span: [0, 4]  Unique cells: 5
```

### Example: Binary AND

```
$ python3 turing.py --text --run binary_and --tape 1100&1010

  Machine: Binary AND
  Bitwise AND of two binary numbers separated by &
  Input: 1100&1010

  ✓ ACCEPTED after 80 steps
  Final tape: 1100&1000
```

The `binary_and` program processes two equal-length binary numbers separated by `&`, computing the bitwise AND column by column. It marks left-side bits as X (for 0) or Y (for 1) to track position correspondence, then converts markers back and cleans up to produce the final result.

### Example: String Reverser

```
$ python3 turing.py --text --run string_reverser --tape 110

  Machine: String Reverser
  Reverse a binary string (e.g., 110 → 011)
  Input: 110

  ✓ ACCEPTED after 54 steps
  Final tape: 011
```

The `string_reverser` works by placing a `=` separator at the end of the input, then repeatedly taking the rightmost input character, erasing it (marking with X), and appending it past the separator. This naturally builds the reversed string. Finally, X markers and the separator are cleaned up.

### Example: Execution Trace

```
$ python3 turing.py --trace --run binary_not

Step   0 | State: q0 | Head: 0 | Read: 1 → Write: 0 | Move: R → q0
  ..._[0]0110011_...
Step   1 | State: q0 | Head: 1 | Read: 0 → Write: 1 | Move: R → q0
  ..._01[1]110011_...
...
```

### Example: Unary Doubler

```
$ python3 turing.py --text --run unary_doubler --tape 111

  Machine: Unary Doubler
  Double a unary number (e.g., 111 → 111111)
  Input: 111

  ✓ ACCEPTED after 58 steps
  Final tape: 111111
```

### Example: Count Ones

```
$ python3 turing.py --text --run count_ones

  Machine: Count Ones
  Count the 1s in a binary string and write unary result after '='
  Input: 10110=

  ✓ ACCEPTED after 42 steps
  Final tape: 10110=|||
```

### Example: Machine Validation

```python
from turing import TuringMachine, BUILTIN_PROGRAMS

# Validate any machine
warnings = machine.validate()
for w in warnings:
    print(f"  ⚠ {w}")
```

### Creating a Custom Machine

```bash
$ python3 turing.py --create

╔══════════════════════════════════════════╗
║     Custom Turing Machine Creator       ║
╚══════════════════════════════════════════╝

Machine name (snake_case): doubler
Description: Doubles the input by replacing each 1 with 11
Initial tape contents: 101
States (comma-separated): q0,q1,q_accept
Alphabet (comma-separated): 0,1,_
Blank symbol [default='_']: _
Initial state [default='q0']: q0
Accept states: q_accept
Reject states:
Now enter transitions. Format: state,read -> next_state,write,direction
Enter empty line to finish.

  Rule: q0,0 -> q0,0,R
  Rule: q0,1 -> q1,1,R
  Rule: q0,_ -> q_accept,_,S
  Rule: q1,0 -> q0,0,R
  Rule: q1,_ -> q_accept,_,S
```

## What It Does

This simulator implements a complete Turing machine — the mathematical model of computation that Alan Turing described in 1936. Each machine consists of:

1. **Tape**: An infinite sequence of cells, each holding one symbol from the alphabet
2. **Head**: A read/write cursor that moves left or right along the tape
3. **State Register**: Tracks the machine's current state
4. **Transition Table**: Rules that determine what to write, which direction to move, and what state to enter next, based on the current state and symbol under the head

The simulator supports multiple execution modes (visual, text, batch, trace), machine validation with helpful warnings, execution statistics tracking, custom machine creation interactively or via JSON files, and ten carefully verified built-in programs that demonstrate different computational tasks — from simple bit-flipping and arithmetic to the famous Busy Beaver problem, bitwise AND operations, and string reversal.

## Running Tests

```bash
python3 test_turing.py
```

The test suite (51 tests) covers tape operations, transitions, machine validation, all 10 built-in programs (including edge cases), batch execution, execution trace, save/load functionality, and the version string.

## Changelog

### v1.2.1 — Bug Fixes

- **Fixed palindrome checker** for single-character and two-character palindromes: inputs like `0`, `1`, `00`, and `11` were incorrectly rejected because the machine lacked transitions for `q0` reading `X` (all chars marked) and `q_left0`/`q_left1` reading `X` (single remaining character). Added three transitions:
  - `(q0, X)` → accept (all characters processed → palindrome)
  - `(q_left0, X)` → accept (single character matches itself)
  - `(q_left1, X)` → accept (single character matches itself)

- **Fixed binary decrement** leaving `Z` markers in output: the `q_strip` state wrote `Z` to mark stripped leading zeros, but these markers were never cleaned up. Changed to write `_` (blank) instead, which is automatically erased from the sparse tape representation. Also removed `Z` from the alphabet since it's no longer needed.

- **Fixed string reverser** for empty input: an empty tape caused the machine to get stuck because `q0` had no transition for `_` after the `=` separator was placed. Added `(q0, _)` → cleanup to handle empty and degenerate inputs gracefully.

- **Added 7 new tests** for edge cases:
  - `test_palindrome_single_char`: single-character palindromes (`0`, `1`)
  - `test_palindrome_two_same_chars`: two-character palindromes (`00`, `11`)
  - `test_palindrome_two_diff_chars`: two-character non-palindromes (`01`, `10`)
  - `test_binary_decrement_no_z_markers`: verifies no `Z` in output for power-of-two decrements
  - `test_binary_decrement_underflow`: verifies `0` is correctly rejected
  - `test_string_reverser_empty_input`: empty string reverses to empty string
  - `test_string_reverser_single_char`: single characters reverse to themselves