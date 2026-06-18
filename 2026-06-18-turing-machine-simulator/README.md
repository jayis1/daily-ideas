# Turing Machine Simulator

A fully-featured Turing machine simulator with 12 built-in programs, visual (curses) and batch execution modes, state diagram export, and comprehensive testing.

## Features

- **12 built-in programs** covering binary arithmetic, unary operations, string manipulation, and more
- **Visual mode** — interactive curses-based step-by-step visualization
- **Text mode** — terminal-friendly step display with configurable delay
- **Batch mode** — run machines programmatically and capture results
- **Trace mode** — detailed execution traces showing every step
- **Machine info** — inspect state count, transitions, alphabet, and more
- **State diagram export** — generate Graphviz DOT format for any built-in machine
- **Tape comparison** — programmatically compare tape contents for verification
- **JSON save/load** — export and import machine definitions
- **Validation** — check machine definitions for unreachable states and other issues
- **Interactive creator** — build custom machines from the command line
- **Custom tape input** — override initial tape for any built-in program via `--tape`

## Built-in Programs

| Name | Input | Output | Description |
|------|-------|--------|-------------|
| `binary_increment` | `1011` | `1100` | Increment a binary number by 1 |
| `unary_addition` | `111+11` | `11111` | Add two unary numbers separated by `+` |
| `palindrome_checker` | `10101` | `XX10X` | Check if input is a palindrome (accepts if yes) |
| `busy_beaver_3` | (blank) | `1111101` | Busy Beaver 3-state champion (writes 6 ones, halts in 13 steps) |
| `binary_not` | `10110011` | `01001100` | Bitwise NOT of a binary string |
| `count_ones` | `10110=` | `10110=\|\|\|` | Count the 1s in a binary string (tally marks after `=`) |
| `binary_decrement` | `1100` | `1011` | Decrement a binary number by 1 |
| `unary_doubler` | `111` | `111111` | Double a unary number |
| `binary_and` | `1100&1010` | `1100&1000` | Bitwise AND of two binary numbers separated by `&` |
| `string_reverser` | `110` | `011` | Reverse a binary string |
| `unary_subtract` | `11111-11` | `111` | Subtract two unary numbers separated by `-` |
| `unary_multiplier` | `11x111` | `11x111=111111` | Multiply two unary numbers separated by `x` |

## Installation

No external dependencies required — uses only the Python standard library (including `curses` for visual mode).

```bash
# Clone or copy the project
cd turing-machine-simulator

# Run directly
python3 turing.py --help
```

## Usage

### Command-Line Interface

```bash
# Show help and version
python3 turing.py --help
python3 turing.py --version

# List all built-in programs
python3 turing.py --list

# Run a specific program in batch mode
python3 turing.py --run binary_increment

# Run with custom tape input
python3 turing.py --run binary_increment --tape 1111

# Run all programs in batch
python3 turing.py --run all

# Text-mode step display
python3 turing.py --text --run busy_beaver_3

# Detailed execution trace
python3 turing.py --trace --run palindrome_checker --tape 1001

# Validate a machine before running
python3 turing.py --validate --run binary_decrement

# Show detailed machine info
python3 turing.py --info unary_subtract

# Export state diagram as Graphviz DOT
python3 turing.py --dot busy_beaver_3 > busy_beaver.dot

# Export machine to JSON
python3 turing.py --export binary_increment

# Load and run a custom machine from JSON
python3 turing.py --load machines/my_machine.json

# Interactive visual mode (default if no --run)
python3 turing.py --visual

# Create a custom machine interactively
python3 turing.py --create

# Adjust step speed (in seconds)
python3 turing.py --text --run busy_beaver_3 --speed 0.1

# Set maximum steps for batch mode
python3 turing.py --run binary_increment --max-steps 5000
```

### Python API

```python
from turing import (
    TuringMachine, Tape, Transition, BUILTIN_PROGRAMS,
    run_batch, run_trace, run_text,
    export_dot, compare_tapes, machine_info,
    save_machine, load_machine,
)

# Run a built-in program
result = run_batch(BUILTIN_PROGRAMS["unary_addition"])
print(f"Output: {result['output']}")  # Output: 11111
print(f"Accepted: {result['accepted']}")  # Accepted: True
print(f"Steps: {result['steps']}")  # Steps: 8

# Run with custom tape
from turing import TuringMachine
base = BUILTIN_PROGRAMS["unary_subtract"]
machine = TuringMachine(
    name=base.name, description=base.description,
    states=base.states, alphabet=base.alphabet,
    blank_symbol=base.blank_symbol, initial_state=base.initial_state,
    accept_states=base.accept_states, reject_states=base.reject_states,
    transitions=base.transitions, initial_tape="111-1",
)
result = run_batch(machine)

# Get detailed machine info
info = machine_info(BUILTIN_PROGRAMS["busy_beaver_3"])
print(f"States: {info['num_states']}, Transitions: {info['num_transitions']}")

# Export state diagram
dot = export_dot(BUILTIN_PROGRAMS["binary_increment"], "binary_increment.dot")

# Compare tapes
t1, t2 = Tape(), Tape()
t1.write(0, "1"); t1.write(1, "0")
t2.write(0, "0"); t2.write(1, "1")
comparison = compare_tapes(t1, t2)
print(f"Match: {comparison['match']}")  # False
print(f"Differences: {comparison['diff_positions']}")

# Save and load machines
save_machine(BUILTIN_PROGRAMS["busy_beaver_3"], "my_machine.json")
loaded = load_machine("my_machine.json")
```

## Architecture

- **`Tape`** — Infinite tape using a sparse dictionary representation (only non-blank cells are stored)
- **`TuringMachine`** — Machine definition with states, alphabet, transitions, and validation
- **`Transition`** — Named tuple for `(next_state, write_symbol, direction)` transition rules
- **`ExecutionStats`** — Tracks step count, cells written, tape span, and unique cells visited
- **`ExecutionStep`** — Captures full state at each step for tracing
- **`BUILTIN_PROGRAMS`** — Dictionary of 12 pre-defined machines

### Key Design Decisions

- Transitions use `(state, symbol)` tuples as keys for O(1) lookup
- Tape positions can be negative (machine starts at position 0)
- Blank symbol is configurable per machine
- Direction codes: `L` (left), `R` (right), `S` (stay)
- Reaching an undefined transition causes the machine to halt (not reject)

## Testing

64 tests covering all core functionality:

```bash
python3 test_turing.py
```

Test categories:
- **Tape operations** — read, write, blank handling, non-blank segment
- **Machine construction** — transitions, validation
- **Built-in programs** — all 12 programs produce correct output
- **New built-ins** — unary_subtract and unary_multiplier with multiple test cases
- **Export functions** — DOT export, tape comparison, machine info
- **Trace & batch** — execution tracing and result formatting
- **Save/Load** — JSON round-trip and error handling

## File Structure

```
turing.py           — Main simulator (single file, ~1800 lines)
test_turing.py      — Test suite (64 tests)
machines/           — Exported machine JSON files
README.md           — This file
```

## License

MIT