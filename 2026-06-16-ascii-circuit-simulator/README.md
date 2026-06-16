# ⚡ ASCII Circuit Simulator

A digital logic circuit simulator with ASCII art rendering, truth table generation, and interactive mode. Define circuits using a simple DSL, simulate them step-by-step, toggle inputs interactively, and watch signals propagate through logic gates.

## Features

- **8 gate types**: AND, OR, NOT, NAND, NOR, XOR, XNOR, BUF
- **Circuit DSL**: Define circuits in a clean text format with comments
- **Truth table generation**: Automatically enumerate all input combinations
- **Step-by-step simulation**: Watch signal propagation gate by gate
- **Interactive mode**: Toggle inputs in real-time and see outputs update
- **6 built-in examples**: Half adder, full adder, SR latch, multiplexer, decoder, majority gate
- **Custom circuits**: Load your own circuit definitions from files
- **Topological sort**: Correct gate evaluation order computed automatically
- **Auto-layout**: Gates are positioned based on signal depth
- **Signal map visualization**: See every intermediate signal with ON/OFF indicators

## Installation

No external dependencies needed — pure Python 3.6+.

```bash
# Clone or download, then run directly:
python3 circuit_sim.py --help
```

## Usage

### List available example circuits

```bash
python3 circuit_sim.py --list
```

Output:
```
Available example circuits:
  half_adder       — A half adder: adds two single-bit numbers.
  full_adder       — A full adder: adds two bits with carry input.
  sr_latch         — An SR latch (using NOR gates) — demonstrates feedback.
  mux              — A 2-to-1 multiplexer.
  decoder          — A 2-to-4 decoder.
  majority         — A majority gate: output is 1 if majority of 3 inputs are 1.
```

### Generate a truth table

```bash
python3 circuit_sim.py --example half_adder --truth-table
```

Output:
```
  A │ B │ sum │ carry
  ───┼─────┼─────┼──────
  0 │ 0 │ 0 │ 0
  0 │ 1 │ 1 │ 0
  1 │ 0 │ 1 │ 0
  1 │ 1 │ 0 │ 1
```

### Simulate with specific inputs

```bash
python3 circuit_sim.py --example full_adder --inputs A=1 B=1 Cin=0
```

### Step-by-step simulation

```bash
python3 circuit_sim.py --example decoder --step --inputs A=1 B=0
```

Output:
```
  Step 1: NOT gate → nA = 0  (A=1)
  Step 2: NOT gate → nB = 1  (B=0)
  Step 3: AND gate → Y0 = 0  (nA=0, nB=1)
  Step 4: AND gate → Y1 = 1  (A=1, nB=1)
  Step 5: AND gate → Y2 = 0  (nA=0, B=0)
  Step 6: AND gate → Y3 = 0  (A=1, B=0)
```

### Interactive mode

```bash
python3 circuit_sim.py --example full_adder --interactive
```

Toggle inputs by number, type `a` to set all on, `n` for all off, `q` to quit.

### Load a custom circuit from file

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
```

## Circuit DSL Reference

| Command | Description |
|---------|-------------|
| `INPUT name [label] [0\|1]` | Define an input signal with optional label and default value |
| `OUTPUT name [label]` | Define an output signal with optional label |
| `GATE type output input1 [input2 ...]` | Define a logic gate |
| `# comment` | Comment line (ignored) |

**Gate types**: `AND`, `OR`, `NOT`, `NAND`, `NOR`, `XOR`, `XNOR`, `BUF`

## Example Circuits

- **Half adder** — Adds two single-bit numbers, produces sum and carry
- **Full adder** — Adds two bits with carry input, produces sum and carry-out
- **SR latch** — Set-reset memory element using NOR gates (feedback loop)
- **MUX (2-to-1)** — Selects between two inputs based on a selector bit
- **Decoder (2-to-4)** — Decodes a 2-bit address into one of 4 output lines
- **Majority gate** — Output is 1 when the majority of 3 inputs are 1

## Running Tests

```bash
python3 run_tests.py
```

52 tests covering all gate types, circuit simulation, truth table generation, parsing, auto-layout, and rendering.

## How It Works

1. **Parsing**: The DSL is parsed into a `Circuit` object containing `Gate` objects
2. **Topological sort**: Gates are ordered by dependencies so inputs are computed before outputs
3. **Simulation**: Each gate evaluates its inputs using Boolean logic, producing output signals
4. **Truth table**: All 2^n input combinations are enumerated and simulated
5. **Interactive mode**: A terminal loop reads user commands, toggles inputs, and re-simulates