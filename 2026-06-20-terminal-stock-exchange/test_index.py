#!/usr/bin/env python3
"""Test index growth over time."""

import sys
sys.path.insert(0, '/root/daily-ideas/2026-06-20-terminal-stock-exchange')

from exchange import *

# Test index growth
ex = StockExchange(num_companies=20, seed=42)
print(f"Initial index: {ex.index_value:.2f}")
for i in range(500):
    ex.step()
    if i % 50 == 0:
        prices = [c.price for c in ex.companies.values()]
        print(f"Tick {ex.tick}: index={ex.index_value:.2f}, day={ex.day}, "
              f"min_price={min(prices):.2f}, max_price={max(prices):.2f}")
print(f"Final index after 500 ticks: {ex.index_value:.2f}")

# What should the index be? Let's calculate directly
total_weight = sum(c.market_cap for c in ex.companies.values())
direct_change = 0.0
for c in ex.companies.values():
    if c.prev_close > 0:
        weight = c.market_cap / total_weight
        direct_change += weight * (c.price / c.prev_close - 1)
print(f"Direct weighted change from prev_close: {direct_change:.6f}")
print(f"If we computed index just once: {100 * (1 + direct_change):.2f}")