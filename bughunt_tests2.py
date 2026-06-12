#!/usr/bin/env python3
"""More targeted bug tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '2026-06-12-rune-cipher'))
from rune_cipher import *

print('=== Vigenere crack testing ===')

# Simple test
text = 'hello world'
key = 'abc'
ct = vigenere_encrypt(text, key)
candidates = crack_vigenere(ct)
print(f'Encrypting "{text}" with key "{key}"')
print(f'Ciphertext: {ct}')
for k, d in candidates[:3]:
    print(f'  Key="{k}": {d}')

# Longer text
text2 = 'the quick brown fox jumps over the lazy dog'
key2 = 'key'
ct2 = vigenere_encrypt(text2, key2)
candidates2 = crack_vigenere(ct2)
print(f'\nEncrypting with key="{key2}"')
for k, d in candidates2[:3]:
    print(f'  Key="{k}": {d[:50]}')

# Test XOR with unicode
print('\n=== XOR unicode test ===')
for text in ['hello', 'café', 'naïve']:
    try:
        enc = xor_encrypt(text, 'key')
        dec = xor_decrypt(enc, 'key')
        status = 'OK' if dec == text else f'FAIL: got {repr(dec)}'
        print(f'  "{text}": {status}')
    except Exception as e:
        print(f'  "{text}": ERROR: {e}')

# Test XOR round-trip with newline
enc = xor_encrypt('hello\nworld', 'key')
dec = xor_decrypt(enc, 'key')
print(f'XOR round-trip with newline: {repr(dec)}')

# Test substitution case handling
print('\n=== Substitution case handling ===')
key = 'qwertyuiopasdfghjklzxcvbnm'
ct = substitution_encrypt('Hello World', key)
print(f'Encrypt "Hello World": {ct}')
pt = substitution_decrypt(ct, key)
print(f'Decrypt back: {pt}')
# Note: both encrypt and decrypt lowercase everything - this is by design

# Test frequency_score edge cases
print('\n=== frequency_score edge cases ===')
print(f'frequency_score("a"): {frequency_score("a")}')
print(f'frequency_score("zzzzzzzz"): {frequency_score("zzzzzzzz")}')

# Test crack_vigenere with known simple text
print('\n=== crack_vigenere longer text ===')
text3 = 'attack at dawn the general said to his troops'
key3 = 'secret'
ct3 = vigenere_encrypt(text3, key3)
candidates3 = crack_vigenere(ct3)
print(f'Key="{key3}", ciphertext length={len(ct3.replace(" ", ""))}')
for k, d in candidates3[:3]:
    print(f'  Key="{k}": {d[:60]}')

# Test for BUG: crack_vigenere returns wrong key format
# The function returns (key, decrypted_text) but sometimes key is "<short>"
# This is not really a bug, it's documented behavior for short texts

# Test combined_score with short text
print('\n=== combined_score behavior ===')
for text in ['a', 'ab', 'the', 'hello', 'the quick brown fox']:
    score = combined_score(text)
    print(f'  combined_score("{text}"): {score:.2f}')

# Check if crack_vigenere IC calculation has a bug
# The IC for English should be ~0.0667
print('\n=== Index of Coincidence calculation ===')
analysis = analyze_frequency("the quick brown fox jumps over the lazy dog")
print(f"IoC for pangram: {analysis['index_of_coincidence']}")

# Longer text
analysis2 = analyze_frequency("it was the best of times it was the worst of times it was the age of wisdom it was the age of foolishness")
print(f"IoC for longer text: {analysis2['index_of_coincidence']}")

# Test: Does crack_vigenere correctly identify key length?
# For key "abc" (length 3), the IC should be high for groups of 3
ct_test = vigenere_encrypt("the quick brown fox jumps over the lazy dog the quick brown fox jumps over the lazy dog the quick brown fox", "abc")
clean = ''.join(ch for ch in ct_test.lower() if ch.isalpha())
print(f'\n=== Key length detection for "abc" (length 3) ===')
for kl in range(2, 8):
    groups = ['' for _ in range(kl)]
    for i, ch in enumerate(clean):
        groups[i % kl] += ch
    total_ic = 0
    for g in groups:
        n = len(g)
        if n < 2:
            continue
        from collections import Counter
        counts = Counter(g)
        ic = sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))
        total_ic += ic
    avg_ic = total_ic / kl
    print(f'  kl={kl}: avg_ic={avg_ic:.4f} (English ~0.0667)')