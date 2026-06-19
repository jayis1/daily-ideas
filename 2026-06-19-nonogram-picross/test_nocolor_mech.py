#!/usr/bin/env python3
"""Test _NO_COLOR mechanism"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import nonogram

print("Testing Style metaclass...")
print(f"Style.RED = {repr(nonogram.Style.RED)}")
print(f"Style.BOLD = {repr(nonogram.Style.BOLD)}")
print(f"Style.RESET = {repr(nonogram.Style.RESET)}")
print(f"_NO_COLOR = {nonogram._NO_COLOR}")
print()

nonogram._NO_COLOR = True
print(f"After setting _NO_COLOR = True:")
print(f"Style.RED = {repr(nonogram.Style.RED)}")
print(f"Style.BOLD = {repr(nonogram.Style.BOLD)}")
print(f"Style.RESET = {repr(nonogram.Style.RESET)}")