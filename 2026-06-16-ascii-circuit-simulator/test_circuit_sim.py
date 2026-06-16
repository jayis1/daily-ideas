"""Tests for the ASCII Circuit Simulator."""
import pytest
from circuit_sim import (
    Circuit, AndGate, OrGate, NotGate, NandGate, NorGate, XorGate, XnorGate,
    BufferGate, GATE_MAP, parse_circuit, generate_truth_table,
    half_adder, full_adder, mux_2to1, decoder_2to4, majority_gate,
    EXAMPLE_CIRCUITS,
)


class TestGateEvaluation:
    """Test individual gate logic."""

    def test_and_gate(self):
        gate = AndGate("test", ["a", "b"], "out")
        assert gate.evaluate({"a": True, "b": True}) is True
        assert gate.evaluate({"a": True, "b": False}) is False
        assert gate.evaluate({"a": False, "b": True}) is False
        assert gate.evaluate({"a": False, "b": False}) is False

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

    def test_gate_symbols(self):
        assert AndGate("t", [], "o").symbol() == "AND"
        assert OrGate("t", [], "o").symbol() == "OR "
        assert NotGate("t", [], "o").symbol() == "NOT"
        assert NandGate("t", [], "o").symbol() == "NND"
        assert NorGate("t", [], "o").symbol() == "NOR"
        assert XorGate("t", [], "o").symbol() == "XOR"
        assert XnorGate("t", [], "o").symbol() == "XNR"
        assert BufferGate("t", [], "o").symbol() == "BUF"


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

    def test_all_example_circuits_load(self):
        for name, func in EXAMPLE_CIRCUITS.items():
            circuit = func()
            assert len(circuit.gates) > 0
            assert len(circuit.inputs) > 0
            assert len(circuit.outputs) > 0


class TestTruthTable:
    """Test truth table generation."""

    def test_half_adder_truth_table(self):
        circuit = half_adder()
        table = generate_truth_table(circuit)
        # Should contain 4 data rows + header + separator
        lines = [l for l in table.strip().split('\n') if l.strip()]
        assert len(lines) >= 6  # header + separator + 4 rows

    def test_truth_table_contains_output_names(self):
        circuit = half_adder()
        table = generate_truth_table(circuit)
        assert "sum" in table
        assert "carry" in table

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
        # XOR gates should come before OR gate in x position
        xor_gates = [g for g in circuit.gates if isinstance(g, XorGate)]
        or_gate = [g for g in circuit.gates if isinstance(g, OrGate)][0]
        # OR gate should be further right (higher x) than its inputs
        assert or_gate.x >= xor_gates[0].x


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