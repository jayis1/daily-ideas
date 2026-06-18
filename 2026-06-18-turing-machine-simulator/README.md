# Turing Machine Simulator

A visual, interactive Turing machine simulator with 6 built-in programs, curses-based visualization, text-mode stepping, and batch execution. Explore the fundamentals of computation through beautifully animated tape heads and state transitions.

## Features

- **6 Built-in Programs**: Binary increment, unary addition, palindrome checker, 3-state Busy Beaver, binary NOT, and 1-counter
- **Curses Visualization**: Real-time animated tape display with state highlighting, transition rules, and keyboard controls
- **Text-Mode Stepping**: Step-by-step execution with colored terminal output (no curses dependency)
- **Batch Execution**: Run all programs at once and compare results
- **Custom Machines**: Interactive creator for defining your own Turing machines
- **JSON Persistence**: Save and load machine definitions as JSON files
- **Keyboard Controls**: Pause (Space), Step (S), Reset (R), Speed (±), Quit (Q)

## Built-in Programs

| Program | Description | Input | Output |
|---------|-------------|-------|--------|
| `binary_increment` | Increment a binary number by 1 | `1011` (11) | `1100` (12) |
| `unary_addition` | Add two unary numbers with '+' | `111+11` | `11111` (5 ones) |
| `palindrome_checker` | Check if a binary string is a palindrome | `10101` | ACCEPTED |
| `busy_beaver_3` | The champion 3-state Busy Beaver | (blank) | 6 ones in 13 steps |
| `binary_not` | Flip all bits (NOT operation) | `10110011` | `01001100` |
| `count_ones` | Count 1s in binary, write unary after '=' | `10110=` | `10110=\|\|\|` |

## How to Install

No external dependencies needed — uses only Python 3 standard library:

```bash
# Just clone and run
cd ~/daily-ideas
git clone <repo-url>  # or it's already here
cd 2026-06-18-turing-machine-simulator
```

## How to Run

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

### Batch Mode (Run all programs, show results)

```bash
python3 turing.py --run all
python3 turing.py --run all --max-steps 500
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
  ...

  ✓ ACCEPTED after 9 steps

  Final tape: 1100
```

### Example: Busy Beaver 3-State

The 3-state Busy Beaver is a famous problem in computability theory. This particular machine (the champion) writes 6 ones on an initially blank tape before halting in exactly 13 steps:

```
$ python3 turing.py --run busy_beaver_3

  busy_beaver_3              Input: (blank)          Output: 1111101          Steps:    13  ✓ ACCEPTED
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

The simulator supports multiple running modes (visual, text, batch), allows creating custom machines interactively or via JSON files, and includes six carefully verified built-in programs that demonstrate different computational tasks from simple bit-flipping to the famous Busy Beaver problem.