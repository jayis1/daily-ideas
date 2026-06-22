#!/usr/bin/env python3
"""Test index growth over 5000 steps."""
import sys
sys.path.insert(0, '/root/daily-ideas/2026-06-20-terminal-stock-exchange')
from exchange import *

ex = StockExchange(num_companies=20, seed=55)
for i in range(5000):
    ex.step()
print(f"Index after 5000 steps: {ex.index_value:.2f}")
print(f"Number of days: {ex.day}")
print(f"Index history entries: {len(ex.index_history)}")
if ex.index_history:
    print(f"First index history: {ex.index_history[0]:.2f}")
    print(f"Last index history: {ex.index_history[-1]:.2f}")