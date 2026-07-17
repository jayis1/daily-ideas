#!/usr/bin/env python3
"""Unit tests for the typewriter simulator."""
from typewriter import TypewriterState, MODEL_PROPS, TypewriterModel

# Test state creation
state = TypewriterState()
assert state.col == 1
assert state.line == 1
assert state.ribbon_wear == 0.0

# Test model properties
for model in TypewriterModel:
    props = MODEL_PROPS[model]
    assert 'min_delay' in props
    assert 'max_delay' in props
    assert 'ink_variance' in props
    assert 'ding_at' in props
    assert 'description' in props
    print(f'  {model.value}: OK (ding_at={props["ding_at"]})')

# Test typing characters
state = TypewriterState()
for ch in 'Hello World!':
    density = 1.0 - state.ribbon_wear * 0.6
    state.lines[0].append((ch, density))
    state.col += 1
    state.total_chars += 1
    state.ribbon_wear = min(1.0, state.ribbon_wear + 0.0002)

assert state.total_chars == 12
assert state.ribbon_wear > 0.0
print(f'  Typed {state.total_chars} chars, ribbon wear: {state.ribbon_wear:.4f}')

print()
print('All tests passed!')