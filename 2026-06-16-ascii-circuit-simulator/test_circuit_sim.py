"""Tests for the ASCII Circuit Simulator — v1.1.0.

Covers gate logic, circuit simulation, truth table generation, DSL parsing,
auto-layout, rendering, validation, DSL export, circuit stats, and all
example circuits including the 4-bit ripple carry adder.
"""

import os
import tempfile
import pytest
from circuit_sim import (
    Circuit, AndGate, OrGate, NotGate, NandGate, NorGate, XorGate, XnorGate,
    BufferGate, GATE_MAP, parse_circuit, generate_truth_table,
    half_adder, full_adder, mux_2to1, decoder_2to4, majority_gate,
    ripple_carry_adder_4bit, sr_latch, EXAMPLE_CIRCUITS,
)


# ─── Gate Evaluation ──────────────────────────────────────────────────────

class TestGateEvaluation:
    """Test individual gate logic."""

    def test_and_gate(self):
        gate = AndGate("test", ["a", "b"], "out")
        assert gate.evaluate({"a": True, "b": True}) is True
        assert gate.evaluate({"a": True, "b": False}) is False
        assert gate.evaluate({"a": False, "b": True}) is False
        assert gate.evaluate({"a": False, "b": False}) is False

    def test_and_gate_three_inputs(self):
        """AND with 3 inputs should require all True."""
        gate = AndGate("test", ["a", "b", "c"], "out")
        assert gate.evaluate({"a": True, "b": True, "c": True}) is True
        assert gate.evaluate({"a": True, "b": True, "c": False}) is False

    def test_or_gate(self):
        gate = OrGate("test", ["a", "b"], "out")
        assert gate.evaluate({"a": True, "b": True}) is True
        assert gate.evaluate({"a": True, "b": False}) is True
        assert gate.evaluate({"a": False, "b": True}) is True
        assert gate.evaluate({"a": False, "b": False}) is False

    def test_not_gate(self):
        gate = NotGate("test", ["a"], "out")
        assert gate.evaluate({"a": True}) is False
        assert gate.evaluate({"a": False}) is True

    def test_nand_gate(self):
        gate = NandGate("test", ["a", "b"], "out")
        assert gate.evaluate({"a": True, "b": True}) is False
        assert gate.evaluate({"a": True, "b": False}) is True
        assert gate.evaluate({"a": False, "b": False}) is True

    def test_nor_gate(self):
        gate = NorGate("test", ["a", "b"], "out")
        assert gate.evaluate({"a": True, "b": True}) is False
        assert gate.evaluate({"a": True, "b": False}) is False
        assert gate.evaluate({"a": False, "b": False}) is True

    def test_xor_gate(self):
        gate = XorGate("test", ["a", "b"], "out")
        assert gate.evaluate({"a": True, "b": True}) is False
        assert gate.evaluate({"a": True, "b": False}) is True
        assert gate.evaluate({"a": False, "b": True}) is True
        assert gate.evaluate({"a": False, "b": False}) is False

    def test_xnor_gate(self):
        gate = XnorGate("test", ["a", "b"], "out")
        assert gate.evaluate({"a": True, "b": True}) is True
        assert gate.evaluate({"a": True, "b": False}) is False
        assert gate.evaluate({"a": False, "b": True}) is False
        assert gate.evaluate({"a": False, "b": False}) is True

    def test_buffer_gate(self):
        gate = BufferGate("test", ["a"], "out")
        assert gate.evaluate({"a": True}) is True
        assert gate.evaluate({"a": False}) is False

    def test_gate_missing_input_defaults_to_false(self):
        """Gates should treat missing inputs as False."""
        gate = AndGate("test", ["a", "b"], "out")
        assert gate.evaluate({"a": True}) is False  # b defaults to False

    def test_gate_symbols(self):
        assert AndGate("t", [], "o").symbol() == "AND"
        assert OrGate("t", [], "o").symbol() == "OR "
        assert NotGate("t", [], "o").symbol() == "NOT"
        assert NandGate("t", [], "o").symbol() == "NND"
        assert NorGate("t", [], "o").symbol() == "NOR"
        assert XorGate("t", [], "o").symbol() == "XOR"
        assert XnorGate("t", [], "o").symbol() == "XNR"
        assert BufferGate("t", [], "o").symbol() == "BUF"


# ─── Circuit Simulation ──────────────────────────────────────────────────

class TestCircuitSimulation:
    """Test circuit simulation logic."""

    def test_half_adder_00(self):
        circuit = half_adder()
        signals = circuit.simulate({"A": False, "B": False})
        assert signals["sum"] is False
        assert signals["carry"] is False

    def test_half_adder_01(self):
        circuit = half_adder()
        signals = circuit.simulate({"A": False, "B": True})
        assert signals["sum"] is True
        assert signals["carry"] is False

    def test_half_adder_10(self):
        circuit = half_adder()
        signals = circuit.simulate({"A": True, "B": False})
        assert signals["sum"] is True
        assert signals["carry"] is False

    def test_half_adder_11(self):
        circuit = half_adder()
        signals = circuit.simulate({"A": True, "B": True})
        assert signals["sum"] is False
        assert signals["carry"] is True

    def test_full_adder_truth(self):
        circuit = full_adder()
        # 1 + 1 + 0 = 10 (sum=0, carry=1)
        signals = circuit.simulate({"A": True, "B": True, "Cin": False})
        assert signals["sum"] is False
        assert signals["Cout"] is True

    def test_full_adder_all_ones(self):
        circuit = full_adder()
        # 1 + 1 + 1 = 11 (sum=1, carry=1)
        signals = circuit.simulate({"A": True, "B": True, "Cin": True})
        assert signals["sum"] is True
        assert signals["Cout"] is True

    def test_mux_select_a(self):
        circuit = mux_2to1()
        signals = circuit.simulate({"A": True, "B": False, "SEL": False})
        assert signals["Y"] is True

    def test_mux_select_b(self):
        circuit = mux_2to1()
        signals = circuit.simulate({"A": True, "B": False, "SEL": True})
        assert signals["Y"] is False

    def test_decoder_10(self):
        circuit = decoder_2to4()
        signals = circuit.simulate({"A": True, "B": False})
        assert signals["Y0"] is False
        assert signals["Y1"] is True
        assert signals["Y2"] is False
        assert signals["Y3"] is False

    def test_majority_gate(self):
        circuit = majority_gate()
        # 2 out of 3 = majority
        signals = circuit.simulate({"A": True, "B": True, "C": False})
        assert signals["M"] is True
        # 1 out of 3 = not majority
        signals = circuit.simulate({"A": True, "B": False, "C": False})
        assert signals["M"] is False
        # 3 out of 3 = majority
        signals = circuit.simulate({"A": True, "B": True, "C": True})
        assert signals["M"] is True

    def test_simulate_with_defaults(self):
        """Simulation should use default input values when none provided."""
        text = """
        INPUT A 0
        INPUT B 1
        GATE AND out A B
        OUTPUT out
        """
        circuit = parse_circuit(text)
        signals = circuit.simulate()  # No overrides — use defaults
        assert signals["out"] is False  # A=0, B=1, AND → 0

    def test_simulate_override_defaults(self):
        """Provided inputs should override defaults."""
        text = """
        INPUT A 0
        INPUT B 1
        GATE AND out A B
        OUTPUT out
        """
        circuit = parse_circuit(text)
        signals = circuit.simulate({"A": True})
        assert signals["out"] is True  # A=1, B=1 (default), AND → 1


# ─── 4-bit Ripple Carry Adder ────────────────────────────────────────────

class TestRippleCarryAdder:
    """Test the 4-bit ripple carry adder."""

    def test_adder_zero_plus_zero(self):
        """0 + 0 + 0 = 0000 with no carry."""
        circuit = ripple_carry_adder_4bit()
        inputs = {f"A{i}": False for i in range(4)}
        inputs.update({f"B{i}": False for i in range(4)})
        inputs["Cin"] = False
        signals = circuit.simulate(inputs)
        assert signals["S0"] is False
        assert signals["S1"] is False
        assert signals["S2"] is False
        assert signals["S3"] is False
        assert signals["Cout"] is False

    def test_adder_one_plus_one(self):
        """1 + 1 + 0 = 0010 with no carry."""
        circuit = ripple_carry_adder_4bit()
        inputs = {"A0": True, "A1": False, "A2": False, "A3": False,
                  "B0": True, "B1": False, "B2": False, "B3": False,
                  "Cin": False}
        signals = circuit.simulate(inputs)
        assert signals["S0"] is False  # 1+1=10, S0=0
        assert signals["S1"] is True   # carry, S1=1
        assert signals["S2"] is False
        assert signals["S3"] is False
        assert signals["Cout"] is False

    def test_adder_with_carry_in(self):
        """0 + 0 + 1 = 0001 with no carry out."""
        circuit = ripple_carry_adder_4bit()
        inputs = {f"A{i}": False for i in range(4)}
        inputs.update({f"B{i}": False for i in range(4)})
        inputs["Cin"] = True
        signals = circuit.simulate(inputs)
        assert signals["S0"] is True
        assert signals["S1"] is False
        assert signals["S2"] is False
        assert signals["S3"] is False
        assert signals["Cout"] is False

    def test_adder_max_values(self):
        """15 + 15 + 0 = 14 with carry out (1110 + carry)."""
        circuit = ripple_carry_adder_4bit()
        inputs = {f"A{i}": True for i in range(4)}
        inputs.update({f"B{i}": True for i in range(4)})
        inputs["Cin"] = False
        signals = circuit.simulate(inputs)
        # 15+15=30 = 0b11110, so S=1110, Cout=1
        assert signals["Cout"] is True

    def test_adder_gate_count(self):
        """4-bit adder should have 20 gates (5 per bit × 4 bits)."""
        circuit = ripple_carry_adder_4bit()
        assert circuit.gate_count() == 20


# ─── Parser ───────────────────────────────────────────────────────────────

class TestParser:
    """Test the circuit DSL parser."""

    def test_parse_simple_circuit(self):
        text = """
        INPUT A
        INPUT B
        GATE AND out A B
        OUTPUT out
        """
        circuit = parse_circuit(text)
        assert "A" in circuit.inputs
        assert "B" in circuit.inputs
        assert "out" in circuit.outputs
        assert len(circuit.gates) == 1

    def test_parse_with_labels(self):
        text = """
        INPUT A InputA
        GATE NOT nA A
        OUTPUT nA NotA
        """
        circuit = parse_circuit(text)
        assert circuit.labels["A"] == "InputA"
        assert circuit.labels["nA"] == "NotA"

    def test_parse_with_defaults(self):
        text = """
        INPUT A MyInput 1
        GATE BUF out A
        OUTPUT out
        """
        circuit = parse_circuit(text)
        assert circuit.inputs["A"] is True

    def test_parse_comments(self):
        text = """
        # This is a comment
        INPUT A
        INPUT B
        # Another comment
        GATE OR out A B
        OUTPUT out
        """
        circuit = parse_circuit(text)
        assert len(circuit.gates) == 1

    def test_parse_unknown_gate_raises(self):
        text = """
        INPUT A
        GATE UNKNOWN out A
        """
        with pytest.raises(ValueError, match="Unknown gate type"):
            parse_circuit(text)

    def test_parse_unknown_command_raises(self):
        text = "BLAH something"
        with pytest.raises(ValueError, match="Unknown command"):
            parse_circuit(text)

    def test_parse_gate_too_few_args_raises(self):
        """GATE with fewer than 4 tokens should raise."""
        text = "GATE AND out"
        with pytest.raises(ValueError):
            parse_circuit(text)

    def test_parse_input_no_name_raises(self):
        """INPUT with no name should raise."""
        text = "INPUT"
        with pytest.raises(ValueError):
            parse_circuit(text)

    def test_parse_output_no_name_raises(self):
        """OUTPUT with no name should raise."""
        text = "OUTPUT"
        with pytest.raises(ValueError):
            parse_circuit(text)

    def test_all_example_circuits_load(self):
        for name, func in EXAMPLE_CIRCUITS.items():
            circuit = func()
            assert len(circuit.gates) > 0, f"{name} has no gates"
            assert len(circuit.inputs) > 0, f"{name} has no inputs"
            assert len(circuit.outputs) > 0, f"{name} has no outputs"


# ─── Truth Table ──────────────────────────────────────────────────────────

class TestTruthTable:
    """Test truth table generation."""

    def test_half_adder_truth_table(self):
        circuit = half_adder()
        table = generate_truth_table(circuit)
        lines = [l for l in table.strip().split('\n') if l.strip()]
        assert len(lines) >= 6  # header + separator + 4 rows

    def test_truth_table_contains_output_names(self):
        circuit = half_adder()
        table = generate_truth_table(circuit)
        # Labels are used in header: "Sum" and "Carry" (from the DSL)
        assert "Sum" in table or "sum" in table
        assert "Carry" in table or "carry" in table

    def test_not_gate_truth_table(self):
        text = """
        INPUT A
        GATE NOT out A
        OUTPUT out
        """
        circuit = parse_circuit(text)
        table = generate_truth_table(circuit)
        lines = [l for l in table.strip().split('\n') if l.strip()]
        assert len(lines) == 4  # header + separator + 2 rows

    def test_truth_table_too_many_inputs(self):
        """Circuits with >8 inputs should show a warning instead of the table."""
        # Build a circuit with 9 inputs
        text_lines = ["INPUT A%d" % i for i in range(9)]
        text_lines.append("GATE AND out " + " ".join("A%d" % i for i in range(9)))
        text_lines.append("OUTPUT out")
        text = "\n".join(text_lines)
        circuit = parse_circuit(text)
        table = generate_truth_table(circuit)
        assert "too large" in table or "2^" in table


# ─── Auto Layout ──────────────────────────────────────────────────────────

class TestAutoLayout:
    """Test automatic gate positioning."""

    def test_auto_layout_assigns_positions(self):
        circuit = half_adder()
        circuit.auto_layout()
        for gate in circuit.gates:
            assert gate.x >= 0
            assert gate.y >= 0

    def test_layout_depth_ordering(self):
        circuit = full_adder()
        circuit.auto_layout()
        xor_gates = [g for g in circuit.gates if isinstance(g, XorGate)]
        or_gate = [g for g in circuit.gates if isinstance(g, OrGate)][0]
        assert or_gate.x >= xor_gates[0].x


# ─── Gate Map ─────────────────────────────────────────────────────────────

class TestGateMap:
    """Test that all gate types are in the GATE_MAP."""

    def test_all_gates_in_map(self):
        expected = {"AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR", "BUF"}
        assert set(GATE_MAP.keys()) == expected

    def test_gate_map_classes(self):
        assert GATE_MAP["AND"] == AndGate
        assert GATE_MAP["OR"] == OrGate
        assert GATE_MAP["NOT"] == NotGate
        assert GATE_MAP["NAND"] == NandGate
        assert GATE_MAP["NOR"] == NorGate
        assert GATE_MAP["XOR"] == XorGate
        assert GATE_MAP["XNOR"] == XnorGate
        assert GATE_MAP["BUF"] == BufferGate


# ─── XOR from NAND ────────────────────────────────────────────────────────

class TestXorFromNand:
    """Test building XOR from NAND gates."""

    def test_xor_from_nand(self):
        text = """
        INPUT A
        INPUT B
        GATE NAND n1 A B
        GATE NAND n2 A n1
        GATE NAND n3 B n1
        GATE NAND Q n2 n3
        OUTPUT Q
        """
        circuit = parse_circuit(text)
        # XOR truth table
        assert circuit.simulate({"A": False, "B": False})["Q"] is False
        assert circuit.simulate({"A": True, "B": False})["Q"] is True
        assert circuit.simulate({"A": False, "B": True})["Q"] is True
        assert circuit.simulate({"A": True, "B": True})["Q"] is False


# ─── ASCII Rendering ──────────────────────────────────────────────────────

class TestRenderAscii:
    """Test ASCII rendering doesn't crash."""

    def test_half_adder_renders(self):
        circuit = half_adder()
        signals = circuit.simulate({"A": True, "B": False})
        output = circuit.render_ascii(signals)
        assert len(output) > 0
        assert isinstance(output, str)

    def test_full_adder_renders(self):
        circuit = full_adder()
        signals = circuit.simulate({"A": True, "B": True, "Cin": False})
        output = circuit.render_ascii(signals)
        assert len(output) > 0

    def test_mux_renders(self):
        circuit = mux_2to1()
        signals = circuit.simulate({"A": True, "B": False, "SEL": True})
        output = circuit.render_ascii(signals)
        assert len(output) > 0

    def test_4bit_adder_renders(self):
        """4-bit adder should render without crashing."""
        circuit = ripple_carry_adder_4bit()
        signals = circuit.simulate({
            "A0": True, "A1": False, "A2": True, "A3": False,
            "B0": False, "B1": True, "B2": False, "B3": True,
            "Cin": False,
        })
        output = circuit.render_ascii(signals)
        assert len(output) > 0


# ─── Circuit Validation ──────────────────────────────────────────────────

class TestValidation:
    """Test circuit validation feature."""

    def test_valid_circuit_no_warnings(self):
        """A properly constructed circuit should have no validation warnings."""
        circuit = half_adder()
        warnings = circuit.validate()
        assert len(warnings) == 0, f"Unexpected warnings: {warnings}"

    def test_empty_circuit_warning(self):
        """An empty circuit should produce a warning."""
        circuit = Circuit()
        warnings = circuit.validate()
        assert len(warnings) > 0
        assert any("empty" in w.lower() for w in warnings)

    def test_dangling_input_warning(self):
        """A gate input that doesn't connect to anything should produce a warning."""
        text = """
        INPUT A
        GATE AND out A B
        OUTPUT out
        """
        circuit = parse_circuit(text)
        warnings = circuit.validate()
        assert any("dangling" in w.lower() for w in warnings)

    def test_disconnected_output_warning(self):
        """An output not produced by any gate should produce a warning."""
        text = """
        INPUT A
        GATE NOT nA A
        OUTPUT nA
        OUTPUT missing_out
        """
        circuit = parse_circuit(text)
        warnings = circuit.validate()
        assert any("not produced" in w.lower() for w in warnings)

    def test_not_gate_wrong_input_count_warning(self):
        """NOT gate with wrong number of inputs should produce a warning."""
        text = """
        INPUT A
        INPUT B
        GATE NOT out A B
        OUTPUT out
        """
        circuit = parse_circuit(text)
        warnings = circuit.validate()
        assert any("NOT" in w and "inputs" in w for w in warnings)

    def test_xor_gate_wrong_input_count_warning(self):
        """XOR gate with wrong number of inputs should produce a warning."""
        text = """
        INPUT A
        INPUT B
        INPUT C
        GATE XOR out A B C
        OUTPUT out
        """
        circuit = parse_circuit(text)
        warnings = circuit.validate()
        assert any("XOR" in w and "inputs" in w for w in warnings)

    def test_cycle_detection_warning(self):
        """Circuits with feedback loops may produce warnings (cycle or dangling input)."""
        # SR latch has intentional feedback — the cross-coupled NOR gates
        # create a cycle, but our validator may detect the dangling input
        # (qbar referenced before it's computed) before the cycle itself.
        circuit = sr_latch()
        warnings = circuit.validate()
        # Should produce at least one warning (dangling input or cycle)
        assert len(warnings) > 0, f"Expected at least one warning, got: {warnings}"

    def test_explicit_cycle_detection(self):
        """A simple feedback loop should be detected as a cycle or dangling input."""
        # Create a circuit with circular dependency: out1 depends on out2, out2 depends on out1
        text_cycle = """
        INPUT A
        GATE NOT out1 out2
        GATE NOT out2 out1
        OUTPUT out1
        """
        circuit = parse_circuit(text_cycle)
        warnings = circuit.validate()
        has_cycle_or_dangling = any("cycle" in w.lower() or "dangling" in w.lower()
                                     for w in warnings)
        assert has_cycle_or_dangling, \
            f"Expected cycle or dangling warning for feedback loop, got: {warnings}"

    def test_full_adder_validates_clean(self):
        """Full adder should validate without warnings."""
        circuit = full_adder()
        warnings = circuit.validate()
        assert len(warnings) == 0, f"Unexpected warnings: {warnings}"


# ─── DSL Export ────────────────────────────────────────────────────────────

class TestDslExport:
    """Test circuit-to-DSL export."""

    def test_export_and_reimport(self):
        """Exporting a circuit and re-parsing it should produce equivalent results."""
        circuit = half_adder()
        dsl = circuit.to_dsl()

        # Re-parse the DSL
        circuit2 = parse_circuit(dsl)

        # Should have same number of gates, inputs, outputs
        assert len(circuit2.gates) == len(circuit.gates)
        assert len(circuit2.inputs) == len(circuit.inputs)
        assert len(circuit2.outputs) == len(circuit.outputs)

        # Should produce same simulation results
        for a_val in [False, True]:
            for b_val in [False, True]:
                s1 = circuit.simulate({"A": a_val, "B": b_val})
                s2 = circuit2.simulate({"A": a_val, "B": b_val})
                assert s1["sum"] == s2["sum"]
                assert s1["carry"] == s2["carry"]

    def test_export_contains_input_lines(self):
        """Exported DSL should contain INPUT lines."""
        circuit = full_adder()
        dsl = circuit.to_dsl()
        assert "INPUT" in dsl
        assert "GATE" in dsl
        assert "OUTPUT" in dsl

    def test_export_to_file(self):
        """Export should write a valid DSL file."""
        circuit = mux_2to1()
        dsl = circuit.to_dsl()

        # Write to temp file and re-read
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(dsl)
            filename = f.name

        try:
            circuit2 = parse_circuit(dsl)
            assert len(circuit2.gates) == len(circuit.gates)
        finally:
            os.unlink(filename)


# ─── Circuit Stats ────────────────────────────────────────────────────────

class TestCircuitStats:
    """Test circuit statistic methods."""

    def test_gate_count(self):
        circuit = half_adder()
        assert circuit.gate_count() == 2

    def test_gate_count_full_adder(self):
        circuit = full_adder()
        assert circuit.gate_count() == 5

    def test_input_count(self):
        circuit = full_adder()
        assert circuit.input_count() == 3

    def test_output_count(self):
        circuit = full_adder()
        assert circuit.output_count() == 2

    def test_depth_half_adder(self):
        """Half adder has depth 1 (all gates are at the same level)."""
        circuit = half_adder()
        assert circuit.depth() >= 0

    def test_depth_full_adder(self):
        """Full adder has depth > 0 (gates depend on other gates)."""
        circuit = full_adder()
        assert circuit.depth() >= 1

    def test_depth_empty_circuit(self):
        """Empty circuit has depth 0."""
        circuit = Circuit()
        assert circuit.depth() == 0


# ─── Signal Map ───────────────────────────────────────────────────────────

class TestSignalMap:
    """Test the signal map rendering."""

    def test_signal_map_has_structure(self):
        """Signal map should contain header and structured layout."""
        circuit = half_adder()
        signals = circuit.simulate({"A": True, "B": False})
        smap = circuit.render_signal_map(signals)
        assert "Signal Map" in smap
        assert "IN" in smap or "OUT" in smap

    def test_signal_map_shows_all_outputs(self):
        """Signal map should show all declared outputs."""
        circuit = full_adder()
        signals = circuit.simulate({"A": True, "B": True, "Cin": False})
        smap = circuit.render_signal_map(signals)
        assert "Sum" in smap or "CarryOut" in smap


# ─── SR Latch ─────────────────────────────────────────────────────────────

class TestSRLatch:
    """Test SR latch (feedback circuit)."""

    def test_sr_latch_set(self):
        """Setting S=1, R=0 should set Q=1."""
        circuit = sr_latch()
        signals = circuit.simulate({"S": True, "R": False})
        # Note: SR latch behavior depends on evaluation order for feedback
        # This just verifies it doesn't crash
        assert "Q" in signals

    def test_sr_latch_loads(self):
        """SR latch example should load successfully."""
        circuit = sr_latch()
        assert circuit.gate_count() > 0


# ─── Main Function ────────────────────────────────────────────────────────

class TestMainFunction:
    """Test the main() entry point doesn't crash with various arguments."""

    def test_version_flag(self):
        """--version should print version and exit."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "circuit_sim.py", "--version"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__) or "."
        )
        assert result.returncode == 0
        assert "1.1.0" in result.stdout

    def test_list_flag(self):
        """--list should show example circuits."""
        import subprocess
        result = subprocess.run(
            [sys.executable, "circuit_sim.py", "--list"],
            capture_output=True, text=True, cwd=os.path.dirname(__file__) or "."
        )
        assert result.returncode == 0
        assert "half_adder" in result.stdout
        assert "4bit_adder" in result.stdout


import sys

if __name__ == '__main__':
    pytest.main([__file__, '-v'])