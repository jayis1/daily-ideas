# ⚡ ASCII Circuit Simulator

A digital logic circuit simulator with ASCII art rendering, truth table generation, circuit validation, DSL export, and interactive mode. Define circuits using a simple text DSL, simulate them step-by-step, toggle inputs interactively, validate designs, export to files, and watch signals propagate through logic gates.

## Features

- **8 gate types**: AND, OR, NOT, NAND, NOR, XOR, XNOR, BUF
- **7 built-in examples**: Half adder, full adder, SR latch, 2-to-1 multiplexer, 2-to-4 decoder, majority gate, 4-bit ripple carry adder
- **Circuit DSL**: Define circuits in a clean text format with comments, labels, and default values
- **Truth table generation**: Automatically enumerate all input combinations (with safety limit for >8 inputs)
- **Step-by-step simulation**: Watch signal propagation gate by gate with configurable delay
- **Interactive mode**: Toggle inputs in real-time and see outputs update, with truth table and step-through access
- **Circuit validation**: Detect dangling inputs, disconnected outputs, cycles, and gate input count mismatches
- **DSL export**: Save any circuit (including built-in examples) back to a DSL file for later editing
- **Circuit statistics**: Gate count, input/output count, circuit depth at a glance
- **Signal map visualization**: See every intermediate signal with ON/OFF indicators
- **ASCII art rendering**: Visual circuit diagram with signal state overlays
- **`--version` and `--help`** flags with comprehensive usage documentation
- **Custom circuits**: Load your own circuit definitions from files
- **Topological sort**: Correct gate evaluation order computed automatically with cycle protection
- **Auto-layout**: Gates positioned based on signal depth
- **Smart truth table formatting**: Column widths adapt to label names; large tables (>8 inputs) show a warning instead of flooding your terminal
- **76 unit tests** covering all gate types, simulation, parsing, validation, export, stats, and all example circuits

## Installation

No external dependencies needed — pure Python 3.6+:

```bash
# Just run it directly
python3 circuit_sim.py --help

# Or clone and run
cd daily-ideas/2026-06-16-ascii-circuit-simulator
python3 circuit_sim.py --example half_adder --truth-table
```

To run the test suite:

```bash
# Standalone runner (no dependencies)
python3 run_tests.py

# Or with pytest
python3 -m pytest test_circuit_sim.py -v
```

## Usage

### Quick Start

```bash
# Show available example circuits
python3 circuit_sim.py --list

# Generate a truth table
python3 circuit_sim.py --example half_adder --truth-table

# Simulate with specific inputs
python3 circuit_sim.py --example full_adder --inputs A=1 B=1 Cin=0

# Step-by-step simulation
python3 circuit_sim.py --example decoder --step --inputs A=1 B=0

# Interactive mode (toggle inputs live)
python3 circuit_sim.py --example full_adder --interactive

# Validate a circuit for common issues
python3 circuit_sim.py --example sr_latch --validate

# Export a built-in example to a DSL file
python3 circuit_sim.py --example 4bit_adder --export adder.txt

# Show version
python3 circuit_sim.py --version
```

### Command-Line Options

| Flag | Description |
|------|-------------|
| `--version` | Show version number and exit |
| `--example`, `-e` | Load a built-in example circuit |
| `--file`, `-f` | Load circuit from a DSL file |
| `--truth-table`, `-t` | Generate and display truth table |
| `--interactive`, `-i` | Run in interactive mode (toggle inputs) |
| `--step`, `-s` | Simulate step by step |
| `--inputs` | Set input values as NAME=0/1 pairs |
| `--validate`, `-v` | Validate circuit for common issues |
| `--export` | Export circuit to a DSL file |
| `--list` | List available example circuits |

### Available Examples

| Name | Description |
|------|-------------|
| `half_adder` | Adds two single-bit numbers |
| `full_adder` | Adds two bits with carry input |
| `sr_latch` | Set-reset memory element using NOR gates (feedback loop) |
| `mux` | 2-to-1 multiplexer |
| `decoder` | 2-to-4 decoder |
| `majority` | Output is 1 when majority of 3 inputs are 1 |
| `4bit_adder` | 4-bit ripple carry adder (20 gates, 9 inputs, 5 outputs) |

### Interactive Mode Controls

| Key | Action |
|-----|--------|
| `1`–`N` | Toggle input #N |
| `a` | Set all inputs ON |
| `n` | Set all inputs OFF |
| `t` | Show truth table |
| `s` | Step-through simulation |
| `q` | Quit |

### Circuit DSL Reference

```
# This is a comment
INPUT name [label] [0|1]            # Define an input (optional label and default)
OUTPUT name [label]                  # Define an output (optional label)
GATE type output input1 [input2 ...] # Define a logic gate
```

**Gate types**: `AND`, `OR`, `NOT`, `NAND`, `NOR`, `XOR`, `XNOR`, `BUF`

### Loading Custom Circuits

Create `my_circuit.txt`:

```
# Custom XOR from NAND gates
INPUT A
INPUT B
GATE NAND n1 A B
GATE NAND n2 A n1
GATE NAND n3 B n1
GATE NAND Q n2 n3
OUTPUT Q XOR_result
```

Then run:

```bash
python3 circuit_sim.py --file my_circuit.txt --truth-table
python3 circuit_sim.py --file my_circuit.txt --validate
python3 circuit_sim.py --file my_circuit.txt --interactive
```

### Exporting Circuits

```bash
# Export any example to a DSL file for editing
python3 circuit_sim.py --example full_adder --export full_adder.txt

# Export a custom circuit loaded from file
python3 circuit_sim.py --file my_circuit.txt --export modified_circuit.txt
```

### Validating Circuits

```bash
python3 circuit_sim.py --example half_adder --validate
# ✓ Circuit validation passed — no issues found.

python3 circuit_sim.py --example sr_latch --validate
# ⚠ Circuit validation found issues:
#   • Gate 'NOR_Q' input 'qbar' is not connected...
```

Validation checks for:
- **Dangling inputs**: Gate inputs that aren't connected to any circuit input or gate output
- **Disconnected outputs**: Declared outputs not produced by any gate
- **Cycles**: Feedback loops in combinational logic
- **Gate input count**: NOT with ≠1 input, XOR/XNOR with ≠2 inputs
- **Duplicate gate outputs**: Two gates driving the same signal
- **Empty circuits**: No gates or inputs defined

### 4-bit Adder Example

The `4bit_adder` example chains four full adders to add two 4-bit binary numbers with a carry input:

```bash
# 1 + 1 = 2 (binary: 0001 + 0001 = 0010)
python3 circuit_sim.py --example 4bit_adder --inputs A0=1 B0=1

# 7 + 3 = 10 (binary: 0111 + 0011 = 1010)
python3 circuit_sim.py --example 4bit_adder --inputs A0=1 A1=1 A2=1 B0=1 B1=1
```

Note: Truth tables for the 4-bit adder are suppressed (2^9 = 512 rows) — use `--inputs` to test specific combinations.

## How It Works

1. **Parsing**: The DSL is parsed into a `Circuit` object containing `Gate` objects with input/output connections
2. **Validation**: Optional validation checks for common design issues
3. **Topological sort**: Gates are ordered by dependencies so inputs are computed before outputs (with cycle protection)
4. **Simulation**: Each gate evaluates its inputs using Boolean logic, producing output signals
5. **Truth table**: All 2^n input combinations are enumerated and simulated
6. **Interactive mode**: A terminal loop reads user commands, toggles inputs, and re-simulates
7. **Step-by-step**: Gates evaluate one at a time with visual delay, showing intermediate values

## File Structure

```
2026-06-16-ascii-circuit-simulator/
├── circuit_sim.py        # Complete implementation (single file, ~730 lines)
├── test_circuit_sim.py   # 76 unit tests (pytest)
├── run_tests.py           # Standalone test runner (no dependencies)
└── README.md             # This file
```

## Changelog

### v1.1.0
- **Added** `--version` flag
- **Added** `--validate` flag for circuit validation (dangling inputs, disconnected outputs, cycles, gate input count)
- **Added** `--export` flag to save circuits back to DSL files
- **Added** 4-bit ripple carry adder example (`4bit_adder`)
- **Added** `Circuit.validate()` method for programmatic validation
- **Added** `Circuit.to_dsl()` method for exporting circuits to DSL format
- **Added** `Circuit.render_signal_map()` for structured signal display
- **Added** `Circuit.gate_count()`, `Circuit.input_count()`, `Circuit.output_count()`, `Circuit.depth()` stats methods
- **Added** Interactive mode now shows circuit stats and supports truth table (`t`) and step-through (`s`) sub-commands
- **Added** Smart truth table formatting with column widths based on label names
- **Added** Truth table safety limit for circuits with >8 inputs (shows warning instead of 256+ rows)
- **Added** Cycle protection in `auto_layout()` to prevent infinite recursion on feedback circuits
- **Added** Better parser error messages for missing INPUT/OUTPUT names and insufficient GATE arguments
- **Added** Better error handling for `--file` (file not found) and `--inputs` (invalid values)
- **Improved** Truth table header now uses display labels instead of raw signal names
- **Improved** Default simulation output now shows circuit info (gates, depth, inputs, outputs)
- **Improved** Interactive mode shows signal map alongside inputs/outputs
- **Improved** Code documentation (docstrings on all classes and public methods)
- **Improved** 76 unit tests covering all features including validation, export, stats, 4-bit adder, and cycle detection
- **Improved** Standalone test runner (`run_tests.py`) updated with new test cases
- **Fixed** `auto_layout()` recursion error on circuits with feedback loops (SR latch, etc.)

## License

CC0 — use it however you like.