"""Quick self-test for the water ripple simulator."""
from ripple import RippleSimulator

sim = RippleSimulator(cols=20, rows=10)
sim.drop_stone(10, 5, radius=2, amplitude=10)

# Run a few steps
for i in range(5):
    sim.step()

lines = sim.render()
assert len(lines) == 10, f"Expected 10 rows, got {len(lines)}"
assert sim.frame == 5, f"Expected frame 5, got {sim.frame}"
assert sim.drop_count == 1, f"Expected 1 drop, got {sim.drop_count}"

# Check waves propagated (non-zero cells exist)
nonzero = sum(1 for v in sim.current if abs(v) > 0.001)
assert nonzero > 0, "Expected non-zero wave values after drop"

# Test wall functionality
sim2 = RippleSimulator(cols=10, rows=5)
sim2.walls[sim2.idx(5, 2)] = True
sim2.drop_stone(2, 2, radius=1, amplitude=5)
for i in range(10):
    sim2.step()

# Wall cell should be 0
assert sim2.current[sim2.idx(5, 2)] == 0.0, "Wall cell should remain 0"

# Test clearing
sim2.clear_water()
assert all(v == 0.0 for v in sim2.current), "Water should be cleared"
assert sim2.frame == 0, "Frame should reset to 0"

# Test palette switching
sim2.palette_id = 2
lines2 = sim2.render()
assert len(lines2) == 5, "Render should work with different palette"

print("✅ All tests passed!")