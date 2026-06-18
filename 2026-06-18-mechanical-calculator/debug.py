#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mechanical_calculator import MechanicalCalculator

calc = MechanicalCalculator()
calc.set_number(123)
calc.set_carriage(0)
calc.crank(6)
print(f"After 123*6: result={calc.read_result()}")
calc.set_carriage(1)
calc.clear_counter()
calc.crank(5)
print(f"After +123*50: result={calc.read_result()}")
calc.set_carriage(2)
calc.clear_counter()
calc.crank(4)
print(f"After +123*400: result={calc.read_result()}")
print(f"Expected 56088 (123*456)")