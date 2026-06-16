#!/usr/bin/env python3
"""
ASCII Circuit Simulator — A digital logic circuit simulator with ASCII rendering.

Define circuits using a simple DSL, simulate them, and watch signals propagate
through gates in real-time rendered as ASCII art.
"""

import sys
import time
import argparse
from dataclasses import dataclass, field
from typing import Optional
from collections import deque


# ─── Gate Definitions ───────────────────────────────────────────────────────

@dataclass
class Gate:
    """Base class for all logic gates."""
    name: str
    inputs: list[str]  # names of input signals
    output: str        # name of output signal
    x: int = 0         # grid position
    y: int = 0         # grid position

    def evaluate(self, signals: dict[str, bool]) -> bool:
        raise NotImplementedError

    def symbol(self) -> str:
        raise NotImplementedError


class AndGate(Gate):
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return all(vals)
    def symbol(self): return "AND"

class OrGate(Gate):
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return any(vals)
    def symbol(self): return "OR "

class NotGate(Gate):
    def evaluate(self, signals):
        val = signals.get(self.inputs[0], False)
        return not val
    def symbol(self): return "NOT"

class NandGate(Gate):
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return not all(vals)
    def symbol(self): return "NND"

class NorGate(Gate):
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return not any(vals)
    def symbol(self): return "NOR"

class XorGate(Gate):
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return vals[0] != vals[1] if len(vals) == 2 else False
    def symbol(self): return "XOR"

class XnorGate(Gate):
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return vals[0] == vals[1] if len(vals) == 2 else True
    def symbol(self): return "XNR"

class BufferGate(Gate):
    """Pass-through buffer, useful for visualization."""
    def evaluate(self, signals):
        return signals.get(self.inputs[0], False)
    def symbol(self): return "BUF"


GATE_MAP = {
    "AND": AndGate, "OR": OrGate, "NOT": NotGate,
    "NAND": NandGate, "NOR": NorGate, "XOR": XorGate,
    "XNOR": XnorGate, "BUF": BufferGate,
}


# ─── Circuit ─────────────────────────────────────────────────────────────────

class Circuit:
    """A collection of gates, inputs, and outputs."""

    def __init__(self):
        self.gates: list[Gate] = []
        self.inputs: dict[str, bool] = {}   # name -> default value
        self.outputs: list[str] = []         # output signal names
        self.labels: dict[str, str] = {}     # signal -> display label

    def add_input(self, name: str, default: bool = False, label: str = ""):
        self.inputs[name] = default
        if label:
            self.labels[name] = label

    def add_output(self, name: str, label: str = ""):
        self.outputs.append(name)
        if label:
            self.labels[name] = label

    def add_gate(self, gate: Gate):
        self.gates.append(gate)

    def simulate(self, input_values: Optional[dict[str, bool]] = None) -> dict[str, bool]:
        """Simulate the circuit with given inputs. Returns all signal values."""
        signals: dict[str, bool] = {}
        # Set inputs
        for name, default in self.inputs.items():
            signals[name] = default
        if input_values:
            signals.update(input_values)

        # Topological sort of gates
        order = self._topological_sort()

        # Evaluate gates in order
        for gate in order:
            signals[gate.output] = gate.evaluate(signals)

        return signals

    def _topological_sort(self) -> list[Gate]:
        """Sort gates so dependencies are evaluated first."""
        # Build dependency graph
        output_to_gate = {g.output: g for g in self.gates}
        gate_deps = {}
        for g in self.gates:
            deps = []
            for inp in g.inputs:
                if inp in output_to_gate:
                    deps.append(output_to_gate[inp])
            gate_deps[id(g)] = deps

        # Kahn's algorithm
        in_degree = {id(g): 0 for g in self.gates}
        for g in self.gates:
            for dep in gate_deps[id(g)]:
                in_degree[id(g)] = in_degree.get(id(g), 0) + 1
                # Actually we need reverse — count how many gates depend on each gate
        # Redo: in_degree[g] = number of gates whose output is an input to g
        in_degree = {id(g): 0 for g in self.gates}
        for g in self.gates:
            for inp in g.inputs:
                dep_gate = output_to_gate.get(inp)
                if dep_gate:
                    # g depends on dep_gate, so dep_gate must come first
                    pass
        # Let me just use a simpler approach
        visited = set()
        order = []

        def visit(gate):
            if id(gate) in visited:
                return
            visited.add(id(gate))
            for inp in gate.inputs:
                dep = output_to_gate.get(inp)
                if dep:
                    visit(dep)
            order.append(gate)

        for g in self.gates:
            visit(g)

        return order

    def auto_layout(self):
        """Automatically assign grid positions to gates based on depth."""
        output_to_gate = {g.output: g for g in self.gates}

        # Calculate depth for each gate
        depth_cache = {}
        def get_depth(gate):
            if id(gate) in depth_cache:
                return depth_cache[id(gate)]
            max_input_depth = -1
            for inp in gate.inputs:
                dep = output_to_gate.get(inp)
                if dep:
                    max_input_depth = max(max_input_depth, get_depth(dep))
                else:
                    max_input_depth = max(max_input_depth, 0)  # circuit input
            depth_cache[id(gate)] = max_input_depth + 1
            return depth_cache[id(gate)]

        for g in self.gates:
            get_depth(g)

        # Group by depth
        depth_groups: dict[int, list[Gate]] = {}
        for g in self.gates:
            d = depth_cache[id(g)]
            depth_groups.setdefault(d, []).append(g)

        # Assign positions
        max_depth = max(depth_cache.values()) if depth_cache else 0
        x = 2  # start after input column
        for d in range(max_depth + 1):
            gates_at_depth = depth_groups.get(d, [])
            for i, g in enumerate(gates_at_depth):
                g.x = x + d * 12
                g.y = 2 + i * 4

    def render_ascii(self, signals: dict[str, bool], show_signals: bool = True) -> str:
        """Render the circuit as ASCII art with current signal values."""
        # Build grid
        width = 80
        height = max((g.y + 4 for g in self.gates), default=10) + 4
        height = max(height, 10)
        if self.gates:
            max_x = max(g.x for g in self.gates) + 16
            width = max(width, max_x)

        grid = [[' ' for _ in range(width)] for _ in range(height)]

        # Draw title
        title = "╔═══ Digital Logic Circuit ═══╗"
        for i, ch in enumerate(title):
            if i < width:
                grid[0][i + 2] = ch

        # Draw input labels on the left
        for i, (name, val) in enumerate(list(self.inputs.items())):
            y = 2 + i * 2
            if y < height:
                label = self.labels.get(name, name)
                val_char = "1" if signals.get(name, val) else "0"
                text = f" {label:>4} ──{val_char}"
                for j, ch in enumerate(text):
                    if j < width:
                        grid[y][j] = ch

        # Draw gates
        output_to_gate = {g.output: g for g in self.gates}
        for gate in self.gates:
            self._draw_gate(grid, gate, signals, width, height)

        # Draw output labels on the right
        for i, name in enumerate(self.outputs):
            y = 2 + i * 2
            if y < height:
                val_char = "1" if signals.get(name, False) else "0"
                label = self.labels.get(name, name)
                text = f"{val_char}── {label}"
                start_x = width - len(text) - 2
                if start_x > 0:
                    for j, ch in enumerate(text):
                        if start_x + j < width:
                            grid[y][start_x + j] = ch

        # Convert grid to string
        lines = [''.join(row).rstrip() for row in grid]
        return '\n'.join(line for line in lines if line.strip())

    def _draw_gate(self, grid, gate, signals, width, height):
        """Draw a single gate on the grid."""
        x, y = gate.x, gate.y
        sym = gate.symbol()
        out_val = signals.get(gate.output, False)
        val_char = "1" if out_val else "0"

        # Gate body: ┌─────┐
        #            │ AND │─1─→
        #            └─────┘
        gate_lines = [
            f"┌─────┐",
            f"│ {sym} │─{val_char}─→",
            f"└─────┘",
        ]

        for i, line in enumerate(gate_lines):
            gy = y + i
            if 0 <= gy < height:
                for j, ch in enumerate(line):
                    gx = x + j
                    if 0 <= gx < width:
                        grid[gy][gx] = ch

        # Draw input wires
        input_y_positions = []
        if len(gate.inputs) == 1:
            input_y_positions.append(y + 1)  # single input at center
        else:
            for idx in range(len(gate.inputs)):
                input_y_positions.append(y + idx * 2)

        for idx, inp_name in enumerate(gate.inputs):
            if idx < len(input_y_positions):
                iy = input_y_positions[idx]
                # Draw wire from left to gate
                if 0 <= iy < height:
                    inp_val = signals.get(inp_name, False)
                    wire_char = "━" if inp_val else "─"
                    # Connect to gate left edge
                    wire_len = min(6, x)  # wire length
                    for wx in range(max(0, x - wire_len), x):
                        if wx < width:
                            grid[iy][wx] = wire_char


# ─── Circuit DSL Parser ──────────────────────────────────────────────────────

def parse_circuit(text: str) -> Circuit:
    """Parse a circuit from DSL text.

    DSL format:
        INPUT name [label] [0|1]
        OUTPUT name [label]
        GATE type output input1 [input2 ...]
    """
    circuit = Circuit()
    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        cmd = parts[0].upper()

        if cmd == "INPUT":
            name = parts[1]
            label = parts[2] if len(parts) > 2 and not parts[2].startswith('0') and not parts[2].startswith('1') else ""
            default = False
            # Check for default value
            for p in parts[2:]:
                if p == '1':
                    default = True
                elif p == '0':
                    default = False
            circuit.add_input(name, default, label)

        elif cmd == "OUTPUT":
            name = parts[1]
            label = parts[2] if len(parts) > 2 else ""
            circuit.add_output(name, label)

        elif cmd == "GATE":
            gate_type = parts[1].upper()
            output_name = parts[2]
            input_names = parts[3:]
            if gate_type not in GATE_MAP:
                raise ValueError(f"Line {line_num}: Unknown gate type '{gate_type}'")
            gate = GATE_MAP[gate_type](name=f"{gate_type}_{output_name}", inputs=input_names, output=output_name)
            circuit.add_gate(gate)

        else:
            raise ValueError(f"Line {line_num}: Unknown command '{cmd}'")

    circuit.auto_layout()
    return circuit


# ─── Example Circuits ────────────────────────────────────────────────────────

def half_adder() -> Circuit:
    """A half adder: adds two single-bit numbers."""
    text = """
    INPUT A A
    INPUT B B
    GATE XOR sum A B
    GATE AND carry A B
    OUTPUT sum Sum
    OUTPUT carry Carry
    """
    return parse_circuit(text)


def full_adder() -> Circuit:
    """A full adder: adds two bits with carry input."""
    text = """
    INPUT A A
    INPUT B B
    INPUT Cin CarryIn
    GATE XOR s1 A B
    GATE XOR sum s1 Cin
    GATE AND c1 A B
    GATE AND c2 s1 Cin
    GATE OR Cout c1 c2
    OUTPUT sum Sum
    OUTPUT Cout CarryOut
    """
    return parse_circuit(text)


def sr_latch() -> Circuit:
    """An SR latch (using NOR gates) — demonstrates feedback."""
    text = """
    INPUT S Set
    INPUT R Reset
    GATE NOR Q S qbar
    GATE NOR Qbar R Q
    OUTPUT Q Q
    OUTPUT Qbar Q_bar
    """
    return parse_circuit(text)


def mux_2to1() -> Circuit:
    """A 2-to-1 multiplexer."""
    text = """
    INPUT A InputA
    INPUT B InputB
    INPUT SEL Select
    GATE NOT nsel SEL
    GATE AND o1 A nsel
    GATE AND o2 B SEL
    GATE OR Y o1 o2
    OUTPUT Y Output
    """
    return parse_circuit(text)


def decoder_2to4() -> Circuit:
    """A 2-to-4 decoder."""
    text = """
    INPUT A Addr0
    INPUT B Addr1
    GATE NOT nA A
    GATE NOT nB B
    GATE AND Y0 nA nB
    GATE AND Y1 A nB
    GATE AND Y2 nA B
    GATE AND Y3 A B
    OUTPUT Y0 Out0
    OUTPUT Y1 Out1
    OUTPUT Y2 Out2
    OUTPUT Y3 Out3
    """
    return parse_circuit(text)


def majority_gate() -> Circuit:
    """A majority gate: output is 1 if majority of 3 inputs are 1."""
    text = """
    INPUT A A
    INPUT B B
    INPUT C C
    GATE AND ab A B
    GATE AND bc B C
    GATE AND ac A C
    GATE OR m1 ab bc
    GATE OR M m1 ac
    OUTPUT M Majority
    """
    return parse_circuit(text)


EXAMPLE_CIRCUITS = {
    "half_adder": half_adder,
    "full_adder": full_adder,
    "sr_latch": sr_latch,
    "mux": mux_2to1,
    "decoder": decoder_2to4,
    "majority": majority_gate,
}


# ─── Truth Table Generator ───────────────────────────────────────────────────

def generate_truth_table(circuit: Circuit) -> str:
    """Generate and display the truth table for a circuit."""
    input_names = list(circuit.inputs.keys())
    output_names = circuit.outputs

    if not input_names:
        return "No inputs to generate truth table."

    n = len(input_names)
    header = " │ ".join(input_names) + " │ " + " │ ".join(output_names)
    separator = "─┼─".join("─" * max(len(n), 3) for n in input_names + output_names)

    lines = [header, separator]

    for i in range(2 ** n):
        input_vals = {}
        bits = []
        for j, name in enumerate(input_names):
            val = bool((i >> (n - 1 - j)) & 1)
            input_vals[name] = val
            bits.append("1" if val else "0")

        signals = circuit.simulate(input_vals)
        out_bits = ["1" if signals.get(o, False) else "0" for o in output_names]

        row = " │ ".join(bits) + " │ " + " │ ".join(out_bits)
        lines.append(row)

    return "\n".join(lines)


# ─── Interactive Mode ────────────────────────────────────────────────────────

def interactive_mode(circuit: Circuit):
    """Run the circuit in interactive mode. Toggle inputs and see outputs."""
    input_names = list(circuit.inputs.keys())
    current_inputs = {name: False for name in input_names}

    while True:
        # Simulate
        signals = circuit.simulate(current_inputs)

        # Clear screen
        print("\033[2J\033[H")  # ANSI clear screen + cursor home

        print("╔══════════════════════════════════════════════════════════════╗")
        print("║          ⚡ ASCII Circuit Simulator — Interactive ⚡         ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print()

        # Show inputs
        print("  INPUTS:")
        for i, name in enumerate(input_names):
            label = circuit.labels.get(name, name)
            val = current_inputs[name]
            indicator = "█ ON " if val else "  OFF"
            print(f"    [{i+1}] {label:>10} : {indicator}")
        print()

        # Show outputs
        print("  OUTPUTS:")
        for name in circuit.outputs:
            label = circuit.labels.get(name, name)
            val = signals.get(name, False)
            indicator = "█ HIGH" if val else "  LOW "
            print(f"    {label:>10} : {indicator}")
        print()

        # Show truth table
        print("  TRUTH TABLE:")
        print("  " + generate_truth_table(circuit).replace("\n", "\n  "))
        print()

        # Show signal map
        print("  SIGNAL MAP:")
        for name in sorted(signals.keys()):
            val = "1" if signals[name] else "0"
            label = circuit.labels.get(name, name)
            print(f"    {name:>8} ({label:>10}) = {val}")

        print()
        print("  Commands: [1-{}] toggle input | 'a' all on | 'n' all off | 'q' quit".format(len(input_names)))

        try:
            cmd = input("\n  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Bye!")
            break

        if cmd == 'q':
            print("  Bye!")
            break
        elif cmd == 'a':
            current_inputs = {name: True for name in input_names}
        elif cmd == 'n':
            current_inputs = {name: False for name in input_names}
        elif cmd.isdigit() and 1 <= int(cmd) <= len(input_names):
            idx = int(cmd) - 1
            name = input_names[idx]
            current_inputs[name] = not current_inputs[name]


# ─── Simulation Step-by-Step ────────────────────────────────────────────────

def simulate_steps(circuit: Circuit, input_values: dict[str, bool], delay: float = 0.5):
    """Simulate the circuit step by step, showing signal propagation."""
    signals = {}
    for name, default in circuit.inputs.items():
        signals[name] = default
    signals.update(input_values)

    output_to_gate = {g.output: g for g in circuit.gates}
    order = circuit._topological_sort()

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║          ⚡ ASCII Circuit Simulator — Step Mode ⚡           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    print(f"  Initial inputs:")
    for name in circuit.inputs:
        val = signals.get(name, False)
        label = circuit.labels.get(name, name)
        print(f"    {label:>10} = {'1' if val else '0'}")
    print()

    for step, gate in enumerate(order, 1):
        inp_vals = [signals.get(inp, False) for inp in gate.inputs]
        result = gate.evaluate(signals)
        signals[gate.output] = result

        inp_str = ", ".join(f"{inp}={'1' if v else '0'}" for inp, v in zip(gate.inputs, inp_vals))
        print(f"  Step {step}: {gate.symbol().strip()} gate → {gate.output} = {'1' if result else '0'}  ({inp_str})")
        time.sleep(delay)

    print()
    print("  Final outputs:")
    for name in circuit.outputs:
        val = signals.get(name, False)
        label = circuit.labels.get(name, name)
        print(f"    {label:>10} = {'1' if val else '0'}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ASCII Circuit Simulator — simulate digital logic circuits with ASCII art",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --example half_adder --truth-table
  %(prog)s --example full_adder --interactive
  %(prog)s --example mux --step
  %(prog)s --file my_circuit.txt --truth-table
  %(prog)s --example decoder --inputs A=1 B=0

Available examples: half_adder, full_adder, sr_latch, mux, decoder, majority

Circuit DSL:
  INPUT name [label] [0|1]    — Define an input signal
  OUTPUT name [label]          — Define an output signal
  GATE type output input1 [input2 ...]  — Define a logic gate
  # comment lines are supported

Gate types: AND, OR, NOT, NAND, NOR, XOR, XNOR, BUF
        """)

    parser.add_argument('--example', '-e', choices=list(EXAMPLE_CIRCUITS.keys()),
                        help='Load an example circuit')
    parser.add_argument('--file', '-f', type=str,
                        help='Load circuit from a DSL file')
    parser.add_argument('--truth-table', '-t', action='store_true',
                        help='Generate and display truth table')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Run in interactive mode (toggle inputs)')
    parser.add_argument('--step', '-s', action='store_true',
                        help='Simulate step by step')
    parser.add_argument('--inputs', type=str, nargs='*',
                        help='Set input values as NAME=0/1 pairs')
    parser.add_argument('--list', action='store_true',
                        help='List available example circuits')

    args = parser.parse_args()

    if args.list:
        print("Available example circuits:")
        for name, func in EXAMPLE_CIRCUITS.items():
            print(f"  {name:15s} — {func.__doc__.strip()}")
        return

    # Load circuit
    if args.file:
        with open(args.file) as f:
            text = f.read()
        circuit = parse_circuit(text)
    elif args.example:
        circuit = EXAMPLE_CIRCUITS[args.example]()
    else:
        # Default: show half adder truth table
        print("No circuit specified. Use --example or --file. Showing half_adder:\n")
        circuit = half_adder()

    # Parse input overrides
    input_values = {}
    if args.inputs:
        for pair in args.inputs:
            if '=' in pair:
                name, val = pair.split('=', 1)
                input_values[name] = bool(int(val))

    # Run
    if args.interactive:
        interactive_mode(circuit)
    elif args.step:
        simulate_steps(circuit, input_values)
    elif args.truth_table:
        print()
        print(f"  Truth Table for: {circuit.gates[0].name.split('_')[-1] if circuit.gates else 'Circuit'}")
        print()
        print(generate_truth_table(circuit))
        print()
        if input_values:
            print("  With specified inputs:")
            signals = circuit.simulate(input_values)
            for name in circuit.outputs:
                label = circuit.labels.get(name, name)
                print(f"    {label} = {'1' if signals[name] else '0'}")
    else:
        # Default: simulate and show results
        signals = circuit.simulate(input_values)
        print()
        print("  Circuit Simulation Results")
        print("  " + "─" * 40)
        if input_values:
            print("  Inputs:")
            for name, val in input_values.items():
                label = circuit.labels.get(name, name)
                print(f"    {label:>10} = {'1' if val else '0'}")
        print()
        print("  Outputs:")
        for name in circuit.outputs:
            label = circuit.labels.get(name, name)
            val = signals.get(name, False)
            print(f"    {label:>10} = {'1' if val else '0'}")
        print()
        print("  All signals:")
        for name in sorted(signals.keys()):
            label = circuit.labels.get(name, name)
            val = signals[name]
            bar = "█" * (4 if val else 0) + "░" * (4 if not val else 0)
            print(f"    {name:>8} ({label:>8}) = {'1' if val else '0'} {bar}")
        print()
        print("  Use --truth-table, --interactive, or --step for more!")


if __name__ == "__main__":
    main()