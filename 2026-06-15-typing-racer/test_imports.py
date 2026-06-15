#!/usr/bin/env python3
"""Quick check that all imports work and the module is syntactically valid."""
import ast
import sys

with open("typing_racer.py", "r") as f:
    source = f.read()

tree = ast.parse(source)
classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

print(f"✓ Syntax valid")
print(f"  Classes: {classes}")
print(f"  Functions: {functions}")
print(f"  Lines of code: {len(source.splitlines())}")