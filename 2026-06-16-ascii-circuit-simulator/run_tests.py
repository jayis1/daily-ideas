#!/usr/bin/env python3
"""Run tests for the circuit simulator without pytest dependency."""
import sys
sys.path.insert(0, '.')

from circuit_sim import (
    Circuit, AndGate, OrGate, NotGate, NandGate, NorGate, XorGate, XnorGate,
    BufferGate, GATE_MAP, parse_circuit, generate_truth_table,
    half_adder, full_adder, mux_2to1, decoder_2to4, majority_gate,
    EXAMPLE_CIRCUITS,
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

# ─── Truth Table ───
print("\nTruth Table:")
c = half_adder()
table = generate_truth_table(c)
test("Table has 'sum'", "sum" in table)
test("Table has 'carry'", "carry" in table)
lines = [l for l in table.strip().split('\n') if l.strip()]
test("Table has 6+ lines", len(lines) >= 6)

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

# ─── Gate Map ───
print("\nGate Map:")
test("All 8 gates in map", set(GATE_MAP.keys()) == {"AND", "OR", "NOT", "NAND", "NOR", "XOR", "XNOR", "BUF"})

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