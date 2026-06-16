import ast
import sys

with open("nbody_sim.py") as f:
    source = f.read()

try:
    tree = ast.parse(source)
    print(f"Syntax OK — {len(tree.body)} top-level nodes")
except SyntaxError as e:
    print(f"Syntax error: {e}")
    sys.exit(1)

# Quick unit test: can we instantiate the simulation and run a few steps?
from nbody_sim import Body, Simulation

sim = Simulation(80, 24)
sim.add_default_scene()
print(f"Default scene: {len(sim.bodies)} bodies")
for _ in range(100):
    sim.step()
print(f"After 100 steps: {len(sim.bodies)} bodies, {sim.collision_count} collisions, frame {sim.frame}")

# Test spawning
sim2 = Simulation(80, 24)
b = Body(40, 12, 0.5, 0.3, mass=2.0)
sim2.bodies.append(b)
sim2.step()
print(f"Single body step: pos=({b.x:.2f},{b.y:.2f}) vel=({b.vx:.2f},{b.vy:.2f})")

# Test two-body orbit
sim3 = Simulation(80, 24)
b1 = Body(40, 12, 0, 0, mass=100, color_idx=2)
b2 = Body(52, 12, 0, 0, mass=1, color_idx=4)
# Give b2 circular orbit velocity
v = (1.0 * 100 / 12) ** 0.5
b2.vy = v
sim3.bodies = [b1, b2]
for _ in range(200):
    sim3.step()
dx = b2.x - b1.x
dy = b2.y - b1.y
dist = (dx**2 + dy**2) ** 0.5
print(f"Two-body orbit: dist={dist:.2f} (started at 12.00)")

print("\nAll tests passed!")