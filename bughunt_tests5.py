#!/usr/bin/env python3
"""More rune cipher bug tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '2026-06-12-rune-cipher'))
from rune_cipher import *

# Bug: XOR output has inconsistent hex width for multi-byte chars
enc = xor_encrypt('café', 'key')
print(f'XOR café: {repr(enc)}')

# Test with emoji - this creates multi-digit hex values
try:
    enc_emoji = xor_encrypt('hi🎉', 'key')
    dec_emoji = xor_decrypt(enc_emoji, 'key')
    print(f'XOR emoji round-trip: {repr(dec_emoji)}')
    print(f'Emoji XOR output: {repr(enc_emoji)}')
except Exception as e:
    print(f'Emoji XOR error: {e}')

# Bug: combined_score doesn't handle punctuation in word matching
print()
print('=== combined_score punctuation bug ===')
plain = 'the cat sat on the mat'
shifted = caesar_encrypt(plain, 3)
candidates = crack_caesar(shifted)
print(f'crack_caesar no punct: key={candidates[0][0]}, text={candidates[0][1]}')

# With punctuation - period attached to 'mat' prevents word matching
plain_punct = 'the cat sat on the mat.'
shifted_punct = caesar_encrypt(plain_punct, 3)
candidates_punct = crack_caesar(shifted_punct)
print(f'crack_caesar with period: key={candidates_punct[0][0]}, text={candidates_punct[0][1]}')

# Test crack_vigenere with longer text
print("\n=== crack_vigenere accuracy ===")
text = "attack at dawn the general said to his troops today we march on the enemy fortress"
key = "secret"
ct = vigenere_encrypt(text, key)
candidates = crack_vigenere(ct)
for k, d in candidates[:3]:
    match = "CORRECT" if k == key else "wrong"
    print(f'  Key="{k}": {d[:50]}... ({match})')

# Bug: validate_config doesn't check for invalid theme
print("\n=== validate_config doesn't check theme ===")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '2026-06-12-ascii-dungeon-generator'))
from dungeon_generator import validate_config, DungeonConfig
errors = validate_config(DungeonConfig(theme="invalid"))
print(f"Errors for invalid theme: {errors}")

# Bug: XOR hex format is inconsistent for values > 255
print("\n=== XOR hex format consistency ===")
# For regular ASCII, values are always 2 hex digits
enc_ascii = xor_encrypt("hello", "k")
print(f"XOR 'hello' with 'k': {enc_ascii}")
# All values should be 2-digit hex pairs separated by spaces

# For unicode chars > 255, values can be 3+ hex digits
enc_unicode = xor_encrypt("é", "k")
print(f"XOR 'é' with 'k': {enc_unicode}")
# ord('é') = 233, ord('k') = 107, 233 ^ 107 = 138 = '8a' (still 2 digits - OK)

# For emoji, values can be much larger
enc_emoji2 = xor_encrypt("🎉", "k")
print(f"XOR '🎉' with 'k': {enc_emoji2}")
# ord('🎉') = 127882, 127882 ^ 107 = 127849 -> hex '1f389' (5 digits!)
# This breaks the "space-separated hex pairs" format assumption in README