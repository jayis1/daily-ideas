# Befunge-93 Esoteric Language Interpreter

**v1.1.0** — A complete, fully-featured interpreter for **Befunge-93**, one of the most fascinating esoteric programming languages ever created. In Befunge-93, code lives on a **2D grid** and the instruction pointer can move in **all four cardinal directions**, making programs behave like winding mazes rather than linear scripts.

## What is Befunge-93?

Befunge-93 was created by Chris Pressey in 1993 and is one of the original **esoteric programming languages** (esolangs). Its defining features:

- **2D code space**: Programs are laid out on an 80×25 character grid
- **Multi-directional execution**: The instruction pointer (IP) moves left, right, up, or down
- **Self-modifying code**: The `p` (put) and `g` (get) instructions allow a program to read and write its own source code at runtime
- **Stack-based**: Computation uses a push-down stack, similar to Forth

This makes Befunge-93 **Turing-complete** while being deliberately difficult to compile (since code can modify itself at any time).

## Features

### Core Interpreter
- ✅ **Complete Befunge-93 specification** — all 37 instructions implemented faithfully
- ✅ **C-style integer division** — division and modulo truncate toward zero, matching the reference implementation
- ✅ **Toroidal grid** — the 80×25 grid wraps in all directions
- ✅ **Output capture** — program output is captured to a string and returned by `run()`
- ✅ **Configurable step limit** — prevent infinite loops from hanging (`--max-steps`)
- ✅ **Step delay** — slow down execution for visualization (`--delay`)

### Built-in Examples (13 programs)
- ✅ **13 example programs** — Hello World, arithmetic, string mode, division, modulo, character output, and more
- ✅ **Run examples directly** — `--example <name>` to run any built-in program
- ✅ **List and inspect examples** — `--list` and `--show` flags

### Debugging & Inspection
- ✅ **Interactive mode** — step through programs visually with a grid display (press Enter to step, type numbers to multi-step)
- ✅ **Debug mode** — trace every instruction with stack dumps to stderr
- ✅ **Program grid viewer** — display any `.bf` file as a grid with `--cat`
- ✅ **Program validation** — `--validate` checks for missing terminators, unknown characters, and input instructions

### CLI
- ✅ **`--help` / `-h`** — Show usage information
- ✅ **`--version`** — Show version number
- ✅ **`--validate` / `-V`** — Check program for common issues
- ✅ **`--cat` / `-c`** — Display program grid without running
- ✅ **`--interactive` / `-i`** — Step-by-step visual execution mode
- ✅ **`--debug` / `-d`** — Enable instruction tracing
- ✅ **`--delay`** — Millisecond delay between steps
- ✅ **`--max-steps`** — Override the default 1,000,000 step limit

### Testing
- ✅ **77 unit tests** — comprehensive coverage of all instruction types, grid wrapping, examples, validation, and edge cases
- ✅ **Tests run with pytest** — `python3 -m pytest test_befunge93.py -v`

## Befunge-93 Instruction Reference

### Stack Manipulation
| Instruction | Description |
|-------------|-------------|
| `0`–`9` | Push digit onto stack |
| `+` | Addition: pop a,b; push a+b |
| `-` | Subtraction: pop a,b; push a−b |
| `*` | Multiplication: pop a,b; push a×b |
| `/` | Integer division: pop a,b; push a÷b (0 if b=0) |
| `%` | Modulo: pop a,b; push a%b (0 if b=0) |
| `!` | Logical NOT: pop val; push 1 if 0, else 0 |
| `` ` `` | Greater than: pop a,b; push 1 if a>b, else 0 |

### Direction / Flow Control
| Instruction | Description |
|-------------|-------------|
| `>` | Move right |
| `<` | Move left |
| `^` | Move up |
| `v` | Move down |
| `?` | Random direction |
| `_` | Horizontal IF: pop val; right if 0, left otherwise |
| `\|` | Vertical IF: pop val; down if 0, up otherwise |
| `#` | Bridge: skip next cell |

### Stack Operations
| Instruction | Description |
|-------------|-------------|
| `:` | Duplicate top of stack |
| `\` | Swap top two values |
| `$` | Pop and discard |

### I/O
| Instruction | Description |
|-------------|-------------|
| `.` | Pop and print as integer (followed by space) |
| `,` | Pop and print as ASCII character |
| `&` | Read integer from input |
| `~` | Read character from input |

### Special
| Instruction | Description |
|-------------|-------------|
| `"` | Toggle string mode (push ASCII values of characters) |
| `g` | Get: pop y,x; push ASCII value of grid cell (y,x) |
| `p` | Put: pop y,x,v; write character v to grid cell (y,x) |
| `@` | End program |
| `<space>` | No-op |

## Installation

No external dependencies required — just Python 3.6+:

```bash
cd ~/daily-ideas/2026-06-14-befunge93-interpreter
python3 befunge93.py --list
```

Or make it executable:

```bash
chmod +x befunge93.py
./befunge93.py --list
```

## Usage

### Run a Befunge program from a file

```bash
python3 befunge93.py examples/hello.bf
python3 befunge93.py examples/add.bf
python3 befunge93.py examples/multiply.bf
python3 befunge93.py examples/reverse.bf
```

### Run a built-in example

```bash
python3 befunge93.py --example hello
python3 befununge93.py --example add
python3 befunge93.py --example multiply
python3 befunge93.py --example factorial
python3 befunge93.py --example divider
python3 befunge93.py --example modulo
python3 befunge93.py --example charprint
```

### List available examples

```bash
python3 befunge93.py --list
```

### Show example source code

```bash
python3 befunge93.py --show hello
python3 befunge93.py --show factorial
```

### Validate a program for issues

```bash
python3 befunge93.py examples/hello.bf --validate
```

This checks for:
- Missing `@` (end) instruction
- Unknown characters (treated as no-ops)
- Input instructions that require stdin

### Debug mode (trace every step)

```bash
python3 befunge93.py examples/hello.bf --debug
```

### Interactive mode (step-by-step visual execution)

```bash
python3 befunge93.py --example hello --interactive
```

In interactive mode:
- Press **Enter** to step one instruction
- Type a **number** to step that many times
- Type **r** to run to completion
- Type **q** to quit
- Type **d** to toggle debug output

### View the program grid

```bash
python3 befunge93.py examples/hello.bf --cat
```

### Slow down execution

```bash
# 50ms delay between each step
python3 befunge93.py --example hello --delay 50
```

### Limit maximum steps

```bash
python3 befunge93.py examples/hello.bf --max-steps 10000
```

### Show version

```bash
python3 befunge93.py --version
```

## Example Programs

### Built-in Examples

| Name | Description | Output |
|------|-------------|--------|
| `hello` | Hello World using string mode | `Hello, World!` |
| `add` | Adds 3+4 | `7` |
| `multiply` | Multiplies 6×7 | `42` |
| `echo_digits` | Prints digits 1-5 | `1 2 3 4 5` |
| `double` | Prints 2×1², 2×2², 2×3², 2×4² | `2 8 18 32` |
| `reverse` | Reverses a string | `World!` |
| `truth` | The answer to everything | `42` |
| `countdown` | Counts down from 25 | `24 23 22 21 20` |
| `factorial` | Computes 5! = 120 | `120` |
| `divider` | Divides 14 by 3 | `4` |
| `modulo` | Computes 14 mod 3 | `2` |
| `charprint` | Prints 'H' via char output | `H` |
| `cat` | Echoes stdin to stdout (requires input) | — |

### File Examples

| File | Description |
|------|-------------|
| `examples/hello.bf` | Classic Hello, World! |
| `examples/add.bf` | Add two numbers |
| `examples/multiply.bf` | Multiply two numbers |
| `examples/echo_digits.bf` | Echo digits 1-5 |
| `examples/reverse.bf` | Reverse a string |
| `examples/factorial.bf` | Compute 5! |
| `examples/divider.bf` | Division example |
| `examples/cat.bf` | Cat program (echo stdin) |

### Writing Your Own Programs

A Befunge-93 program is just text. The simplest program is:

```
34+.@
```

This pushes 3, pushes 4, adds them (7), prints as integer, and ends (`@`).

For string output, use the string mode (`"`):

```
0"!dlroW ,olleH">:#,_@
```

This pushes 0, then enters string mode and pushes the characters of `"Hello, World!"` in reverse, then loops printing each character until the 0 sentinel is hit, and ends.

For larger numbers (> 9), use arithmetic to compose them:

```
77+3/.@    # 14 / 3 = 4 (7+7=14, 14/3=4)
```

## How It Works

The interpreter maintains four key pieces of state:

1. **The grid** — An 80×25 character array holding the program. Programs that don't fill the entire grid have spaces (no-ops) in unused cells.

2. **The stack** — A push-down stack for computation. Most instructions pop values, operate on them, and push results. Popping from an empty stack returns 0.

3. **The instruction pointer (IP)** — Tracks the current position (x, y) and direction (dx, dy). After each instruction executes, the IP moves one cell in its current direction, wrapping around edges (toroidal topology).

4. **String mode** — When active (toggled by `"`), all characters (except another `"`) have their ASCII values pushed onto the stack. This is how Befunge embeds string data.

The most mind-bending feature is **self-modification** via `p` (put) and `g` (get). A Befunge program can rewrite its own code at runtime, making it possible (in principle) to write programs that evolve, self-repair, or generate entirely new behavior.

## Running Tests

```bash
# Run all 77 tests
python3 -m pytest test_befunge93.py -v

# Or with unittest
python3 -m unittest test_befunge93 -v
```

Tests cover:
- Stack operations (push, pop, peek)
- All arithmetic instructions
- Logical instructions (!, `)
- Direction changing and grid wrapping
- Conditional branching (_, |)
- String mode
- I/O instructions (., ,)
- Self-modification (g, p)
- Bridge instruction (#)
- Program termination (@)
- Output capture
- Program loading and validation
- All 13 built-in examples
- Edge cases (empty stack, division by zero, unknown characters)
- Version flag

## Changelog

### v1.1.0 — Enhanced Interpreter

- **Added `--version` flag** — Shows version number (`v1.1.0`)
- **Added `--validate` flag** — Checks programs for missing `@`, unknown characters, and input instructions
- **Added program validation API** — `Befunge93.validate()` returns a list of warnings
- **Added output capture** — `run()` now returns the captured output string; `Befunge93.output` stores it
- **Added step counter display** — Debug mode and interactive mode now show total steps on completion
- **Added `__version__` constant** — Programmatically accessible version string
- **Added 5 new example programs** — `factorial`, `divider`, `modulo`, `charprint`, `cat`
- **Added `VALID_INSTRUCTIONS` set** — Used for validation
- **Added `__doc__` to `Befunge93` class** — Comprehensive docstring with attributes
- **Improved C-style division** — Integer division and modulo now truncate toward zero (matching the Befunge-93 reference spec), with proper handling of negative operands
- **Improved error handling** — `load_file()` now raises `FileNotFoundError` with a clear message, and catches `UnicodeDecodeError`
- **Improved docstrings** — All public methods now have comprehensive docstrings with argument and return descriptions
- **Fixed interactive mode** — Now shows captured output at program end
- **Added debug end summary** — After program completion, debug mode reports total steps and output length
- **Added 77 unit tests** — Comprehensive test suite covering all instructions, examples, validation, and edge cases
- **Removed non-functional quine and sieve examples** — These did not terminate correctly in the interpreter
- **Updated example .bf files** — Added `factorial.bf`, `divider.bf`, `cat.bf` in examples/

## Why Befunge-93?

Befunge-93 is a masterclass in creative constraint. The 2D grid forces you to think about programs as **spaces** rather than sequences. The self-modification feature means the code you wrote isn't necessarily the code that runs. It's beautiful, infuriating, and endlessly fascinating — everything an esolang should be.

## License

MIT