#!/usr/bin/env python3
"""Run tests for the circuit simulator without pytest dependency.

This is a standalone test runner that verifies all core functionality:
gate logic, circuit simulation, parsing, truth tables, validation,
DSL export, and circuit statistics.
"""
import sys
sys.path.insert(0, '.')

from circuit_sim import (
    Circuit, AndGate, OrGate, NotGate, NandGate, NorGate, XorGate, XnorGate,
    BufferGate, GATE_MAP, parse_circuit, generate_truth_table,
    half_adder, full_adder, mux_2to1, decoder_2to4, majority_gate,
    ripple_carry_adder_4bit, EXAMPLE_CIRCUITS,
)

passed = 0
failed = 0

def test(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name}")

# ─── Gate Logic ───
print("Gate Logic:")
g = AndGate("t", ["a", "b"], "o")
test("AND TT", g.evaluate({"a": True, "b": True}) is True)
test("AND TF", g.evaluate({"a": True, "b": False}) is False)
test("AND FF", g.evaluate({"a": False, "b": False}) is False)
test("AND 3-input", AndGate("t", ["a", "b", "c"], "o").evaluate({"a": True, "b": True, "c": True}) is True)

g = OrGate("t", ["a", "b"], "o")
test("OR TT", g.evaluate({"a": True, "b": True}) is True)
test("OR TF", g.evaluate({"a": True, "b": False}) is True)
test("OR FF", g.evaluate({"a": False, "b": False}) is False)

g = NotGate("t", ["a"], "o")
test("NOT T", g.evaluate({"a": True}) is False)
test("NOT F", g.evaluate({"a": False}) is True)

g = NandGate("t", ["a", "b"], "o")
test("NAND TT", g.evaluate({"a": True, "b": True}) is False)
test("NAND FF", g.evaluate({"a": False, "b": False}) is True)

g = NorGate("t", ["a", "b"], "o")
test("NOR FF", g.evaluate({"a": False, "b": False}) is True)
test("NOR TF", g.evaluate({"a": True, "b": False}) is False)

g = XorGate("t", ["a", "b"], "o")
test("XOR TF", g.evaluate({"a": True, "b": False}) is True)
test("XOR TT", g.evaluate({"a": True, "b": True}) is False)

g = XnorGate("t", ["a", "b"], "o")
test("XNOR TT", g.evaluate({"a": True, "b": True}) is True)
test("XNOR TF", g.evaluate({"a": True, "b": False}) is False)

g = BufferGate("t", ["a"], "o")
test("BUF T", g.evaluate({"a": True}) is True)
test("BUF F", g.evaluate({"a": False}) is False)

# ─── Half Adder ───
print("\nHalf Adder:")
c = half_adder()
s = c.simulate({"A": False, "B": False})
test("HA 0+0 sum=0", s["sum"] is False)
test("HA 0+0 carry=0", s["carry"] is False)
s = c.simulate({"A": True, "B": False})
test("HA 1+0 sum=1", s["sum"] is True)
test("HA 1+0 carry=0", s["carry"] is False)
s = c.simulate({"A": True, "B": True})
test("HA 1+1 sum=0", s["sum"] is False)
test("HA 1+1 carry=1", s["carry"] is True)

# ─── Full Adder ───
print("\nFull Adder:")
c = full_adder()
s = c.simulate({"A": True, "B": True, "Cin": True})
test("FA 1+1+1 sum=1", s["sum"] is True)
test("FA 1+1+1 cout=1", s["Cout"] is True)
s = c.simulate({"A": True, "B": True, "Cin": False})
test("FA 1+1+0 sum=0", s["sum"] is False)
test("FA 1+1+0 cout=1", s["Cout"] is True)

# ─── 4-bit Adder ───
print("\n4-bit Ripple Carry Adder:")
c = ripple_carry_adder_4bit()
test("4bit has 20 gates", c.gate_count() == 20)
inputs = {"A0": True, "A1": False, "A2": False, "A3": False,
          "B0": True, "B1": False, "B2": False, "B3": False, "Cin": False}
s = c.simulate(inputs)
test("4bit: 1+1=2 (S0=0)", s["S0"] is False)
test("4bit: 1+1=2 (S1=1)", s["S1"] is True)
test("4bit: no carry out", s["Cout"] is False)

# ─── Mux ───
print("\nMultiplexer:")
c = mux_2to1()
s = c.simulate({"A": True, "B": False, "SEL": False})
test("MUX sel=A, Y=1", s["Y"] is True)
s = c.simulate({"A": True, "B": False, "SEL": True})
test("MUX sel=B, Y=0", s["Y"] is False)

# ─── Decoder ───
print("\nDecoder:")
c = decoder_2to4()
s = c.simulate({"A": True, "B": False})
test("DEC 10 → Y1=1", s["Y1"] is True)
test("DEC 10 → Y0=0", s["Y0"] is False)

# ─── Majority ───
print("\nMajority Gate:")
c = majority_gate()
s = c.simulate({"A": True, "B": True, "C": False})
test("MAJ 1,1,0 → 1", s["M"] is True)
s = c.simulate({"A": True, "B": False, "C": False})
test("MAJ 1,0,0 → 0", s["M"] is False)

# ─── XOR from NAND ───
print("\nXOR from NAND:")
text = """INPUT A
INPUT B
GATE NAND n1 A B
GATE NAND n2 A n1
GATE NAND n3 B n1
GATE NAND Q n2 n3
OUTPUT Q"""
c = parse_circuit(text)
test("NAND-XOR 00=0", c.simulate({"A": False, "B": False})["Q"] is False)
test("NAND-XOR 10=1", c.simulate({"A": True, "B": False})["Q"] is True)
test("NAND-XOR 01=1", c.simulate({"A": False, "B": True})["Q"] is True)
test("NAND-XOR 11=0", c.simulate({"A": True, "B": True})["Q"] is False)

# ─── Parser ───
print("\nParser:")
try:
    parse_circuit("BADCMD something")
    test("Parser rejects bad command", False)
except ValueError:
    test("Parser rejects bad command", True)

try:
    parse_circuit("INPUT A\nGATE BADTYPE out A")
    test("Parser rejects bad gate type", False)
except ValueError:
    test("Parser rejects bad gate type", True)

try:
    parse_circuit("GATE AND out")
    test("Parser rejects too few GATE args", False)
except ValueError:
    test("Parser rejects too few GATE args", True)

# ─── Truth Table ───
print("\nTruth Table:")
c = half_adder()
table = generate_truth_table(c)
test("Table has 'Sum'", "Sum" in table)
test("Table has 'Carry'", "Carry" in table)
lines = [l for l in table.strip().split('\n') if l.strip()]
test("Table has 6+ lines", len(lines) >= 6)

# Test large truth table warning
big_text = "\n".join(f"INPUT A{i}" for i in range(9)) + "\nGATE AND out " + " ".join(f"A{i}" for i in range(9)) + "\nOUTPUT out"
big_circuit = parse_circuit(big_text)
big_table = generate_truth_table(big_circuit)
test("Large truth table shows warning", "too large" in big_table or "2^" in big_table)

# ─── Auto Layout ───
print("\nAuto Layout:")
c = full_adder()
c.auto_layout()
all_positioned = all(g.x >= 0 and g.y >= 0 for g in c.gates)
test("All gates positioned", all_positioned)

# ─── Render ───
print("\nRender:")
c = half_adder()
s = c.simulate({"A": True, "B": False})
output = c.render_ascii(s)
test("Render produces output", len(output) > 0)

c2 = ripple_carry_adder_4bit()
s2 = c2.simulate({"A0": True, "A1": False, "A2": True, "A3": False,
                   "B0": False, "B1": True, "B2": False, "B3": True, "Cin": False})
output2 = c2.render_ascii(s2)
test("4-bit adder renders", len(output2) > 0)

# ─── Gate Map ───
print("\nGate Map:")
test("All 8 gates in map", set(GATE_MAP.keys()) == {"AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR", "BUF"})

# ─── Validation ───
print("\nValidation:")
c = half_adder()
warnings = c.validate()
test("Valid circuit has no warnings", len(warnings) == 0)

empty = Circuit()
warnings = empty.validate()
test("Empty circuit has warnings", len(warnings) > 0)

dangling_text = """INPUT A
GATE AND out A B
OUTPUT out"""
dangling = parse_circuit(dangling_text)
warnings = dangling.validate()
test("Dangling input detected", any("dangling" in w.lower() for w in warnings))

# ─── DSL Export ───
print("\nDSL Export:")
c = half_adder()
dsl = c.to_dsl()
test("Export contains INPUT", "INPUT" in dsl)
test("Export contains GATE", "GATE" in dsl)
test("Export contains OUTPUT", "OUTPUT" in dsl)

# Re-import and verify
c2 = parse_circuit(dsl)
test("Re-import has same gate count", len(c2.gates) == len(c.gates))
test("Re-import has same input count", len(c2.inputs) == len(c.inputs))
test("Re-import produces same results",
     c.simulate({"A": True, "B": True}) == c2.simulate({"A": True, "B": True}))

# ─── Circuit Stats ───
print("\nCircuit Stats:")
c = full_adder()
test("Gate count", c.gate_count() == 5)
test("Input count", c.input_count() == 3)
test("Output count", c.output_count() == 2)
test("Depth > 0", c.depth() >= 1)

# ─── Signal Map ───
print("\nSignal Map:")
c = half_adder()
s = c.simulate({"A": True, "B": False})
smap = c.render_signal_map(s)
test("Signal map has content", len(smap) > 0)
test("Signal map has header", "Signal Map" in smap)

# ─── All examples load ───
print("\nExample Circuits:")
for name, func in EXAMPLE_CIRCUITS.items():
    c = func()
    test(f"{name} loads", len(c.gates) > 0 and len(c.inputs) > 0)

# ─── Summary ───
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
if failed > 0:
    sys.exit(1)
else:
    print("✅ All tests passed!")