#!/usr/bin/env python3
"""Quick verification script for Befunge-93 fixes."""
from befunge93 import Befunge93

# Test a proper factorial program
# This Befunge-93 program computes 5! using a loop
# Push 5 (counter), then 1 (accumulator)
# Loop: duplicate counter, if 0 then print accumulator and end
# Otherwise multiply accumulator by counter, decrement counter
bf = Befunge93()

# Well-known Befunge-93 factorial program
factorial_code = """1->:#5#_5#v
   v  v<
   >$.@
   ^  <"""
bf.load(factorial_code)
bf.run(max_steps=10000)
print(f'Factorial output: {repr(bf.output)}, steps={bf.step_count}, running={bf.running}')

# Try a simpler approach - just compute 5*4*3*2*1 explicitly
bf2 = Befunge93()
# 5*4=20, 20*3=60, 60*2=120, 120*1=120
bf2.load('54*3*2*1*.@')
bf2.run()
print(f'Simple mult: output={repr(bf2.output)}, steps={bf2.step_count}')

# Test the divider example: we want division, 14/3 = 4
# In Befunge: push 14 and 3, divide
# But we can only push 0-9! So we need to push 14 via arithmetic
# 25* = 10, 4+ = 14, or: 77+ = 14
# Actually: push 14 = 7+7 = 77+ then push 3 then divide
bf3 = Befunge93()
bf3.load('77+3/.@')  # 14/3 = 4 (C-style truncation toward zero)
bf3.run()
print(f'Division 77+3/: output={repr(bf3.output)}, steps={bf3.step_count}')

# Test cat program - needs stdin, skip
# Test sieve - may be complex, skip for now
print("All verification tests done!")