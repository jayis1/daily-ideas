#!/usr/bin/env python3
"""Quick functional test for orrery orbital mechanics."""
import sys
sys.path.insert(0, '.')
from orrery import planet_position, solve_kepler
import math

# Test Kepler solver
E = solve_kepler(0.0, 0.0)
assert abs(E) < 1e-10, f"E should be 0, got {E}"

# Test circular orbit
x, y = planet_position(1.0, 1.0, 0.0, 0.0)
assert abs(x - 1.0) < 0.01, f"Circular orbit at t=0 should be (1,0), got ({x},{y})"

# Test Earth at epoch
x, y = planet_position(1.000, 1.000, 0.017, 0.0)
print(f"Earth at epoch: ({x:.4f}, {y:.4f}) AU")

# Test Mercury
x, y = planet_position(0.387, 0.241, 0.206, 1.0)
print(f"Mercury after 1 year: ({x:.4f}, {y:.4f}) AU")

# Test Neptune  
x, y = planet_position(30.069, 164.800, 0.009, 1.0)
print(f"Neptune after 1 year: ({x:.4f}, {y:.4f}) AU")

print("\nAll orbital mechanics tests passed!")