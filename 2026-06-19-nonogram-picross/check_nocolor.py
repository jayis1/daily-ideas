#!/usr/bin/env python3
"""Check _NO_COLOR usage in source"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import nonogram as nm
import inspect

source = inspect.getsource(nm)
count = source.count('_NO_COLOR')
print(f'_NO_COLOR referenced {count} times in source')

draw_source = inspect.getsource(nm.NonogramGame.draw)
if '_NO_COLOR' in draw_source:
    print('  _NO_COLOR IS used in draw()')
else:
    print('  _NO_COLOR NOT used in draw() - BUG: --no-color has no effect!')

pp_source = inspect.getsource(nm.print_puzzle)
if '_NO_COLOR' in pp_source:
    print('  _NO_COLOR IS used in print_puzzle()')
else:
    print('  _NO_COLOR NOT used in print_puzzle() - BUG: --no-color has no effect!')

main_source = inspect.getsource(nm.main)
if '_NO_COLOR' in main_source:
    print('  _NO_COLOR IS set in main()')
else:
    print('  _NO_COLOR NOT set in main()')

# Also check if NO_COLOR env var is checked anywhere
if 'NO_COLOR' in source:
    lines_with_no_color = [line.strip() for line in source.split('\n') if 'NO_COLOR' in line]
    for line in lines_with_no_color:
        print(f'  Line: {line}')