#!/usr/bin/env python3
"""Quick test for the kaleidoscope engine."""
from kaleidoscope import Kaleidoscope, PATTERNS

# Test all patterns
for p in PATTERNS:
    k = Kaleidoscope(pattern=p, segments=8)
    frame = k.render_frame(40, 12)
    assert len(frame) == 12, f"Expected 12 rows, got {len(frame)}"
    assert len(frame[0]) == 40, f"Expected 40 cols, got {len(frame[0])}"
    print(f"Pattern {p}: {len(frame)} rows x {len(frame[0])} cols - OK")

# Test different segment counts
for s in [4, 6, 8, 10, 12, 16]:
    k = Kaleidoscope(segments=s, pattern="spiral")
    frame = k.render_frame(40, 12)
    print(f"Segments {s}: OK")

# Test multiple frames (animation continuity)
k = Kaleidoscope(pattern="spiral", segments=8)
for i in range(5):
    frame = k.render_frame(20, 10)
    assert len(frame) == 10
print("5 sequential frames: OK")

print("\nAll tests passed!")