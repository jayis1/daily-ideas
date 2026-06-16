#!/usr/bin/env python3
"""
ASCII Circuit Simulator — A digital logic circuit simulator with ASCII rendering.

Define circuits using a simple DSL, simulate them, and watch signals propagate
through gates in real-time rendered as ASCII art. Supports truth table generation,
step-by-step simulation, interactive mode, circuit validation, and export.

Usage:
    python3 circuit_sim.py --example half_adder --truth-table
    python3 circuit_sim.py --example full_adder --interactive
    python3 circuit_sim.py --example mux --step --inputs A=1 B=0 SEL=1
    python3 circuit_sim.py --file my_circuit.txt --truth-table
    python3 circuit_sim.py --example decoder --export circuit.txt
    python3 circuit_sim.py --version
"""

import sys
import time
import argparse
from dataclasses import dataclass, field
from typing import Optional
from collections import deque


__version__ = "1.1.0"

# ─── Gate Definitions ───────────────────────────────────────────────────────

@dataclass
class Gate:
    """Base class for all logic gates.

    Attributes:
        name: A human-readable identifier for this gate instance.
        inputs: List of signal names that feed into this gate.
        output: The signal name this gate produces.
        x: Horizontal grid position for ASCII rendering.
        y: Vertical grid position for ASCII rendering.
    """
    name: str
    inputs: list[str]  # names of input signals
    output: str        # name of output signal
    x: int = 0         # grid position
    y: int = 0         # grid position

    def evaluate(self, signals: dict[str, bool]) -> bool:
        """Evaluate this gate's output given the current signal state."""
        raise NotImplementedError

    def symbol(self) -> str:
        """Return a 3-character symbol for ASCII rendering."""
        raise NotImplementedError


class AndGate(Gate):
    """AND gate: output is 1 only when ALL inputs are 1."""
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return all(vals)
    def symbol(self): return "AND"


class OrGate(Gate):
    """OR gate: output is 1 when ANY input is 1."""
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return any(vals)
    def symbol(self): return "OR "


class NotGate(Gate):
    """NOT gate: inverts a single input."""
    def evaluate(self, signals):
        val = signals.get(self.inputs[0], False)
        return not val
    def symbol(self): return "NOT"


class NandGate(Gate):
    """NAND gate: NOT of AND. Output is 0 only when ALL inputs are 1."""
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return not all(vals)
    def symbol(self): return "NND"


class NorGate(Gate):
    """NOR gate: NOT of OR. Output is 1 only when ALL inputs are 0."""
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return not any(vals)
    def symbol(self): return "NOR"


class XorGate(Gate):
    """XOR gate: output is 1 when inputs differ (exactly 2 inputs)."""
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return vals[0] != vals[1] if len(vals) == 2 else False
    def symbol(self): return "XOR"


class XnorGate(Gate):
    """XNOR gate: output is 1 when inputs are the same (exactly 2 inputs)."""
    def evaluate(self, signals):
        vals = [signals.get(inp, False) for inp in self.inputs]
        return vals[0] == vals[1] if len(vals) == 2 else True
    def symbol(self): return "XNR"


class BufferGate(Gate):
    """Pass-through buffer, useful for visualization and signal routing."""
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
    """A collection of gates, inputs, and outputs forming a digital logic circuit.

    Supports simulation, truth table generation, ASCII rendering, and validation.
    """

    def __init__(self):
        self.gates: list[Gate] = []
        self.inputs: dict[str, bool] = {}   # name -> default value
        self.outputs: list[str] = []         # output signal names
        self.labels: dict[str, str] = {}     # signal -> display label

    def add_input(self, name: str, default: bool = False, label: str = ""):
        """Add an input signal with an optional default value and label."""
        self.inputs[name] = default
        if label:
            self.labels[name] = label

    def add_output(self, name: str, label: str = ""):
        """Add an output signal with an optional display label."""
        self.outputs.append(name)
        if label:
            self.labels[name] = label

    def add_gate(self, gate: Gate):
        """Add a logic gate to the circuit."""
        self.gates.append(gate)

    def validate(self) -> list[str]:
        """Check the circuit for common issues and return a list of warnings.

        Checks for:
        - Dangling inputs (gate inputs that are neither circuit inputs nor gate outputs)
        - Disconnected outputs (declared outputs that are not produced by any gate)
        - Cycles in the combinational logic (feedback loops)
        - Gate input count mismatches (e.g., NOT with 2 inputs)
        - Empty circuits

        Returns:
            A list of warning/error strings. Empty list means no issues found.
        """
        warnings = []

        if not self.gates and not self.inputs:
            warnings.append("Circuit is empty — no gates or inputs defined.")
            return warnings

        # Set of all signal names that are produced somewhere
        produced_signals = set(self.inputs.keys())
        for gate in self.gates:
            produced_signals.add(gate.output)

        # Check for dangling gate inputs
        for gate in self.gates:
            for inp in gate.inputs:
                if inp not in produced_signals:
                    warnings.append(
                        f"Gate '{gate.name}' input '{inp}' is not connected to "
                        f"any circuit input or gate output (dangling input)."
                    )

        # Check for disconnected outputs
        output_set = set(self.outputs)
        gate_output_set = {g.output for g in self.gates}
        for out_name in self.outputs:
            if out_name not in self.inputs and out_name not in gate_output_set:
                warnings.append(
                    f"Output '{out_name}' is declared but not produced by any gate."
                )

        # Check for gate input count issues
        for gate in self.gates:
            if isinstance(gate, NotGate) and len(gate.inputs) != 1:
                warnings.append(
                    f"NOT gate '{gate.name}' has {len(gate.inputs)} inputs "
                    f"(expected 1)."
                )
            elif isinstance(gate, BufferGate) and len(gate.inputs) != 1:
                warnings.append(
                    f"BUF gate '{gate.name}' has {len(gate.inputs)} inputs "
                    f"(expected 1)."
                )
            elif isinstance(gate, (XorGate, XnorGate)) and len(gate.inputs) != 2:
                warnings.append(
                    f"{gate.symbol().strip()} gate '{gate.name}' has "
                    f"{len(gate.inputs)} inputs (expected 2)."
                )

        # Check for cycles (combinational circuits should be acyclic)
        output_to_gate = {g.output: g for g in self.gates}
        visited = set()
        rec_stack = set()

        def has_cycle(gate):
            """DFS-based cycle detection."""
            visited.add(id(gate))
            rec_stack.add(id(gate))
            for inp in gate.inputs:
                dep = output_to_gate.get(inp)
                if dep:
                    if id(dep) not in visited:
                        if has_cycle(dep):
                            return True
                    elif id(dep) in rec_stack:
                        return True
            rec_stack.discard(id(gate))
            return False

        for gate in self.gates:
            if id(gate) not in visited:
                if has_cycle(gate):
                    warnings.append(
                        "Cycle detected in combinational logic (feedback loop). "
                        "Simulation results may be unreliable for the first iteration."
                    )
                    break  # Only report once

        # Check for duplicate gate output names
        seen_outputs = {}
        for gate in self.gates:
            if gate.output in seen_outputs:
                warnings.append(
                    f"Gate output '{gate.output}' is defined by both "
                    f"'{seen_outputs[gate.output]}' and '{gate.name}'."
                )
            seen_outputs[gate.output] = gate.name

        # Check for duplicate input names
        # (Already handled by dict — inputs with same name are overwritten,
        #  but this could be unintentional, so we don't warn here)

        return warnings

    def simulate(self, input_values: Optional[dict[str, bool]] = None) -> dict[str, bool]:
        """Simulate the circuit with given inputs. Returns all signal values.

        Args:
            input_values: Override specific input signals. Any inputs not
                specified will use their default values.

        Returns:
            A dictionary mapping every signal name to its computed Boolean value.
        """
        signals: dict[str, bool] = {}
        # Set inputs to defaults first
        for name, default in self.inputs.items():
            signals[name] = default
        # Then override with provided values
        if input_values:
            signals.update(input_values)

        # Topological sort of gates ensures correct evaluation order
        order = self._topological_sort()

        # Evaluate each gate in dependency order
        for gate in order:
            signals[gate.output] = gate.evaluate(signals)

        return signals

    def _topological_sort(self) -> list[Gate]:
        """Sort gates so dependencies are evaluated first.

        Uses DFS-based topological sort to ensure that every gate's inputs
        are computed before the gate itself is evaluated.
        """
        output_to_gate = {g.output: g for g in self.gates}
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
        """Automatically assign grid positions to gates based on signal depth.

        Gates closer to the inputs are placed on the left; gates further
        from the inputs (deeper in the dependency chain) are placed further right.
        Handles cycles gracefully by assigning a default depth.
        """
        output_to_gate = {g.output: g for g in self.gates}

        # Calculate depth for each gate (distance from inputs)
        # Protect against cycles with a visited set during recursion
        depth_cache = {}
        in_progress = set()  # Track gates currently being computed (cycle detection)

        def get_depth(gate):
            if id(gate) in depth_cache:
                return depth_cache[id(gate)]
            if id(gate) in in_progress:
                # Cycle detected — assign depth 0 to break the loop
                depth_cache[id(gate)] = 0
                return 0
            in_progress.add(id(gate))
            max_input_depth = 0
            for inp in gate.inputs:
                dep = output_to_gate.get(inp)
                if dep:
                    max_input_depth = max(max_input_depth, get_depth(dep) + 1)
            in_progress.discard(id(gate))
            depth_cache[id(gate)] = max_input_depth
            return max_input_depth

        for g in self.gates:
            get_depth(g)

        # Group gates by depth level
        depth_groups: dict[int, list[Gate]] = {}
        for g in self.gates:
            d = depth_cache[id(g)]
            depth_groups.setdefault(d, []).append(g)

        # Assign grid positions: depth → x, index within depth → y
        max_depth = max(depth_cache.values()) if depth_cache else 0
        x = 2  # start after input column
        for d in range(max_depth + 1):
            gates_at_depth = depth_groups.get(d, [])
            for i, g in enumerate(gates_at_depth):
                g.x = x + d * 12
                g.y = 2 + i * 4

    def render_ascii(self, signals: dict[str, bool], show_signals: bool = True) -> str:
        """Render the circuit as ASCII art with current signal values.

        Args:
            signals: Current signal state dictionary.
            show_signals: If True, include signal values in the drawing.

        Returns:
            A string containing the ASCII art representation of the circuit.
        """
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
        """Draw a single gate on the grid with signal state."""
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
                    wire_len = min(6, x)
                    for wx in range(max(0, x - wire_len), x):
                        if wx < width:
                            grid[iy][wx] = wire_char

    def render_signal_map(self, signals: dict[str, bool]) -> str:
        """Render a compact signal map showing all intermediate and final values.

        Args:
            signals: Current signal state dictionary.

        Returns:
            A formatted string showing every signal name and its value.
        """
        lines = []
        lines.append("  ┌─────────────────────────────────────────┐")
        lines.append("  │ Signal Map                               │")
        lines.append("  ├───────────────────────────────────────────┤")

        # Show inputs first
        for name in self.inputs:
            val = signals.get(name, False)
            label = self.labels.get(name, name)
            indicator = "█ ON " if val else "  OFF"
            lines.append(f"  │  IN  {name:>8} ({label:>10}) = {indicator} │")

        # Show intermediate signals
        gate_outputs = {g.output for g in self.gates}
        final_outputs = set(self.outputs)
        intermediates = gate_outputs - final_outputs - set(self.inputs.keys())
        for name in sorted(intermediates):
            val = signals.get(name, False)
            indicator = "1" if val else "0"
            lines.append(f"  │  INT {name:>8}               = {indicator}     │")

        # Show outputs
        for name in self.outputs:
            val = signals.get(name, False)
            label = self.labels.get(name, name)
            indicator = "█HIGH" if val else " LOW"
            lines.append(f"  │  OUT {name:>8} ({label:>10}) = {indicator} │")

        lines.append("  └─────────────────────────────────────────┘")
        return '\n'.join(lines)

    def to_dsl(self) -> str:
        """Export the circuit back to DSL format.

        This is useful for saving a circuit (including built-in examples)
        to a file for later modification.

        Returns:
            A string in the circuit DSL format.
        """
        lines = []
        for name, default in self.inputs.items():
            label = self.labels.get(name, "")
            default_str = " 1" if default else ""
            label_str = f" {label}" if label else ""
            lines.append(f"INPUT {name}{label_str}{default_str}")

        for gate in self.gates:
            inputs_str = " ".join(gate.inputs)
            lines.append(f"GATE {gate.symbol().strip()} {gate.output} {inputs_str}")

        for name in self.outputs:
            label = self.labels.get(name, "")
            label_str = f" {label}" if label else ""
            lines.append(f"OUTPUT {name}{label_str}")

        return '\n'.join(lines)

    def gate_count(self) -> int:
        """Return the total number of gates in the circuit."""
        return len(self.gates)

    def depth(self) -> int:
        """Return the maximum depth (longest path from input to output)."""
        if not self.gates:
            return 0
        output_to_gate = {g.output: g for g in self.gates}
        depth_cache = {}

        def get_depth(gate):
            if id(gate) in depth_cache:
                return depth_cache[id(gate)]
            max_input_depth = 0
            for inp in gate.inputs:
                dep = output_to_gate.get(inp)
                if dep:
                    max_input_depth = max(max_input_depth, get_depth(dep) + 1)
            depth_cache[id(gate)] = max_input_depth
            return max_input_depth

        return max(get_depth(g) for g in self.gates)

    def input_count(self) -> int:
        """Return the number of inputs in the circuit."""
        return len(self.inputs)

    def output_count(self) -> int:
        """Return the number of outputs in the circuit."""
        return len(self.outputs)


# ─── Circuit DSL Parser ──────────────────────────────────────────────────────

def parse_circuit(text: str) -> Circuit:
    """Parse a circuit from DSL text.

    DSL format:
        INPUT name [label] [0|1]      — Define an input signal
        OUTPUT name [label]           — Define an output signal
        GATE type output input1 [...] — Define a logic gate
        # comment                     — Comment line (ignored)

    Raises:
        ValueError: If the DSL contains unknown commands, gate types, or
            other syntax errors.
    """
    circuit = Circuit()
    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        cmd = parts[0].upper()

        if cmd == "INPUT":
            if len(parts) < 2:
                raise ValueError(f"Line {line_num}: INPUT requires a name")
            name = parts[1]
            label = ""
            default = False
            # Parse optional label and default value
            for p in parts[2:]:
                if p in ('0', '1'):
                    default = (p == '1')
                elif not label:
                    label = p
            circuit.add_input(name, default, label)

        elif cmd == "OUTPUT":
            if len(parts) < 2:
                raise ValueError(f"Line {line_num}: OUTPUT requires a name")
            name = parts[1]
            label = parts[2] if len(parts) > 2 else ""
            circuit.add_output(name, label)

        elif cmd == "GATE":
            if len(parts) < 4:
                raise ValueError(
                    f"Line {line_num}: GATE requires type, output, and at least one input"
                )
            gate_type = parts[1].upper()
            output_name = parts[2]
            input_names = parts[3:]
            if gate_type not in GATE_MAP:
                raise ValueError(f"Line {line_num}: Unknown gate type '{gate_type}'")
            gate = GATE_MAP[gate_type](
                name=f"{gate_type}_{output_name}",
                inputs=input_names,
                output=output_name
            )
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


def ripple_carry_adder_4bit() -> Circuit:
    """A 4-bit ripple carry adder built from full adders."""
    text = """
    # 4-bit ripple carry adder
    INPUT A0 A0
    INPUT A1 A1
    INPUT A2 A2
    INPUT A3 A3
    INPUT B0 B0
    INPUT B1 B1
    INPUT B2 B2
    INPUT B3 B3
    INPUT Cin Cin
    # Bit 0
    GATE XOR s1_0 A0 B0
    GATE XOR S0 s1_0 Cin
    GATE AND c1_0 A0 B0
    GATE AND c2_0 s1_0 Cin
    GATE OR C0 c1_0 c2_0
    # Bit 1
    GATE XOR s1_1 A1 B1
    GATE XOR S1 s1_1 C0
    GATE AND c1_1 A1 B1
    GATE AND c2_1 s1_1 C0
    GATE OR C1 c1_1 c2_1
    # Bit 2
    GATE XOR s1_2 A2 B2
    GATE XOR S2 s1_2 C1
    GATE AND c1_2 A2 B2
    GATE AND c2_2 s1_2 C1
    GATE OR C2 c1_2 c2_2
    # Bit 3
    GATE XOR s1_3 A3 B3
    GATE XOR S3 s1_3 C2
    GATE AND c1_3 A3 B3
    GATE AND c2_3 s1_3 C2
    GATE OR Cout c1_3 c2_3
    # Outputs
    OUTPUT S0 S0
    OUTPUT S1 S1
    OUTPUT S2 S2
    OUTPUT S3 S3
    OUTPUT Cout Cout
    """
    return parse_circuit(text)


EXAMPLE_CIRCUITS = {
    "half_adder": half_adder,
    "full_adder": full_adder,
    "sr_latch": sr_latch,
    "mux": mux_2to1,
    "decoder": decoder_2to4,
    "majority": majority_gate,
    "4bit_adder": ripple_carry_adder_4bit,
}


# ─── Truth Table Generator ───────────────────────────────────────────────────

def generate_truth_table(circuit: Circuit) -> str:
    """Generate and display the truth table for a circuit.

    For circuits with more than 8 inputs, a warning is issued since
    the truth table would have 2^n rows.

    Args:
        circuit: The circuit to analyze.

    Returns:
        A formatted string containing the truth table.
    """
    input_names = list(circuit.inputs.keys())
    output_names = circuit.outputs

    if not input_names:
        return "No inputs to generate truth table."

    n = len(input_names)
    if n > 8:
        return (
            f"Truth table has 2^{n} = {2**n} rows — too large to display.\n"
            f"Use --inputs to test specific input combinations."
        )

    # Calculate column widths
    col_widths = {}
    for name in input_names:
        col_widths[name] = max(len(name), 3)
    for name in output_names:
        label = circuit.labels.get(name, name)
        col_widths[name] = max(len(label), 3)

    # Build header
    header_parts = []
    for name in input_names:
        header_parts.append(f" {name:>{col_widths[name]}} ")
    header_parts.append("│")
    for name in output_names:
        label = circuit.labels.get(name, name)
        header_parts.append(f" {label:>{col_widths[name]}} ")

    header = " ".join(header_parts)

    # Build separator
    sep_parts = []
    for name in input_names:
        sep_parts.append("─" * (col_widths[name] + 2))
    sep_parts.append("┼")
    for name in output_names:
        sep_parts.append("─" * (col_widths[name] + 2))
    separator = "─".join(sep_parts)

    lines = [header, separator]

    # Generate all input combinations
    for i in range(2 ** n):
        input_vals = {}
        bits = []
        for j, name in enumerate(input_names):
            val = bool((i >> (n - 1 - j)) & 1)
            input_vals[name] = val
            bits.append(f" {'1' if val else '0':>{col_widths[name]}} ")

        signals = circuit.simulate(input_vals)
        out_bits = []
        for name in output_names:
            label = circuit.labels.get(name, name)
            val = signals.get(name, False)
            out_bits.append(f" {'1' if val else '0':>{col_widths[name]}} ")

        row = " ".join(bits) + " │" + " ".join(out_bits)
        lines.append(row)

    return "\n".join(lines)


# ─── Interactive Mode ────────────────────────────────────────────────────────

def interactive_mode(circuit: Circuit):
    """Run the circuit in interactive mode. Toggle inputs and see outputs.

    Controls:
        [1-N] — Toggle a specific input
        a     — Set all inputs to 1 (ON)
        n     — Set all inputs to 0 (OFF)
        t     — Show truth table
        s     — Show signal map
        q     — Quit
    """
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

        # Show signal map
        print(circuit.render_signal_map(signals))
        print()

        # Show circuit info
        print(f"  Gates: {circuit.gate_count()}  |  Depth: {circuit.depth()}  |  "
              f"Inputs: {circuit.input_count()}  |  Outputs: {circuit.output_count()}")
        print()

        print(f"  Commands: [1-{len(input_names)}] toggle  |  'a' all on  |  "
              f"'n' all off  |  't' truth table  |  's' step  |  'q' quit")

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
        elif cmd == 't':
            print("\n  Truth Table:")
            print("  " + generate_truth_table(circuit).replace("\n", "\n  "))
            input("\n  Press Enter to continue...")
        elif cmd == 's':
            simulate_steps(circuit, current_inputs, delay=0.3)
            input("\n  Press Enter to continue...")
        elif cmd.isdigit() and 1 <= int(cmd) <= len(input_names):
            idx = int(cmd) - 1
            name = input_names[idx]
            current_inputs[name] = not current_inputs[name]


# ─── Simulation Step-by-Step ────────────────────────────────────────────────

def simulate_steps(circuit: Circuit, input_values: dict[str, bool], delay: float = 0.5):
    """Simulate the circuit step by step, showing signal propagation.

    Args:
        circuit: The circuit to simulate.
        input_values: Input signal values.
        delay: Seconds between steps for visual effect.
    """
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

        inp_str = ", ".join(
            f"{inp}={'1' if v else '0'}" for inp, v in zip(gate.inputs, inp_vals)
        )
        print(
            f"  Step {step}: {gate.symbol().strip()} gate → "
            f"{gate.output} = {'1' if result else '0'}  ({inp_str})"
        )
        if delay > 0:
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
  %(prog)s --example 4bit_adder --export adder.txt
  %(prog)s --validate --file my_circuit.txt

Available examples: half_adder, full_adder, sr_latch, mux, decoder, majority, 4bit_adder

Circuit DSL:
  INPUT name [label] [0|1]    — Define an input signal
  OUTPUT name [label]          — Define an output signal
  GATE type output input1 [input2 ...]  — Define a logic gate
  # comment lines are supported

Gate types: AND, OR, NOT, NAND, NOR, XOR, XNOR, BUF
        """)

    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

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
    parser.add_argument('--validate', '-v', action='store_true',
                        help='Validate the circuit for common issues')
    parser.add_argument('--export', type=str,
                        help='Export circuit to a DSL file')

    args = parser.parse_args()

    if args.list:
        print("Available example circuits:")
        for name, func in EXAMPLE_CIRCUITS.items():
            print(f"  {name:15s} — {func.__doc__.strip()}")
        return

    # Load circuit
    if args.file:
        try:
            with open(args.file) as f:
                text = f.read()
            circuit = parse_circuit(text)
        except FileNotFoundError:
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        except ValueError as e:
            print(f"Error parsing circuit: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.example:
        circuit = EXAMPLE_CIRCUITS[args.example]()
    else:
        # Default: show half adder truth table
        print("No circuit specified. Use --example or --file. Showing half_adder:\n")
        circuit = half_adder()

    # Validate if requested
    if args.validate:
        warnings = circuit.validate()
        if warnings:
            print("⚠ Circuit validation found issues:\n")
            for w in warnings:
                print(f"  • {w}")
            print()
        else:
            print("✓ Circuit validation passed — no issues found.\n")

    # Export if requested
    if args.export:
        with open(args.export, 'w') as f:
            f.write(circuit.to_dsl() + '\n')
        print(f"Circuit exported to '{args.export}'")
        print(f"  {circuit.gate_count()} gates, {circuit.input_count()} inputs, "
              f"{circuit.output_count()} outputs, depth {circuit.depth()}")
        return

    # Parse input overrides
    input_values = {}
    if args.inputs:
        for pair in args.inputs:
            if '=' in pair:
                name, val = pair.split('=', 1)
                try:
                    input_values[name] = bool(int(val))
                except ValueError:
                    print(f"Error: Invalid input value '{val}' for '{name}'. "
                          f"Use 0 or 1.", file=sys.stderr)
                    sys.exit(1)

    # Run
    if args.interactive:
        interactive_mode(circuit)
    elif args.step:
        simulate_steps(circuit, input_values)
    elif args.truth_table:
        print()
        # Get circuit name for display
        if args.example:
            name = args.example
        elif args.file:
            name = args.file
        else:
            name = "circuit"
        print(f"  Truth Table for: {name}")
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
        print(f"  Circuit info: {circuit.gate_count()} gates, "
              f"depth {circuit.depth()}, "
              f"{circuit.input_count()} inputs, {circuit.output_count()} outputs")
        print()
        print("  Use --truth-table, --interactive, --step, or --validate for more!")


if __name__ == "__main__":
    main()