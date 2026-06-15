#!/usr/bin/env python3
"""Quick test for morse_wave module."""
from morse_wave import *

# Test encode/decode roundtrip
text = "HELLO WORLD"
morse = text_to_morse(text)
decoded = morse_to_text(morse)
assert decoded == text, f"Roundtrip failed: {decoded} != {text}"
print(f"✓ Roundtrip: '{text}' -> '{morse}' -> '{decoded}'")

# Test decode
morse_in = "... --- ..."
decoded2 = morse_to_text(morse_in)
assert decoded2 == "SOS", f"Decode failed: {decoded2}"
print(f"✓ Decode: '{morse_in}' -> '{decoded2}'")

# Test compact waveform
compact = render_compact_waveform(morse)
assert len(compact) > 0
print(f"✓ Compact waveform renders ({len(compact)} chars)")

# Test full waveform
full = render_waveform(morse, amplitude=1)
assert len(full) > 0
lines = full.strip().split("\n")
print(f"✓ Full waveform renders ({len(lines)} rows)")
print()
print("--- Compact SOS ---")
morse_sos = text_to_morse("SOS")
print(render_compact_waveform(morse_sos))
print()
print("--- Waveform SOS (amplitude=1) ---")
print(render_waveform(morse_sos, amplitude=1))
print()
print("--- Special chars ---")
morse_special = text_to_morse("CQ CQ DE W1AW")
print(f"Morse: {morse_special}")
print(render_compact_waveform(morse_special))
print()
print("All tests passed! ✓")