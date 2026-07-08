#!/usr/bin/env python3
"""Quick test to verify game logic works."""
import sys
sys.path.insert(0, '/root/daily-ideas/2026-07-08-terminal-lighthouse-keeper')
from lighthouse import Lighthouse, tick

s = Lighthouse()
print('State created OK')
print(f'Hour: {s.hour}, Fuel: {s.fuel}, Beam: {s.beam_on}')

for i in range(100):
    tick(s, 0.1)

print(f'After 100 ticks: Hour: {s.hour}:{s.minutes:02d}, Fuel: {s.fuel:.1f}')
print(f'Ships saved: {s.ships_saved}, Lost: {s.ships_lost}')
print('Game logic OK')