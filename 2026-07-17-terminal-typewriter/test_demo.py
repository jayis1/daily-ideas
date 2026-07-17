#!/usr/bin/env python3
"""Quick demo script showing all 5 typewriter models with sample text."""

from typewriter import demo_typewriter

print("=" * 72)
print("  Terminal Typewriter Simulator — Demo of All Models")
print("=" * 72)

demo_typewriter('The Royal Quiet De Luxe: elegant but temperamental.', 'royal')
demo_typewriter('The IBM Selectric II: fast, consistent, electric.', 'ibm')
demo_typewriter('The Olivetti Lettera 32: Italian precision and beauty.', 'olivetti')
demo_typewriter('The Remington Portable: light and quick.', 'remington')
demo_typewriter('The Underwood No. 5: the classic workhorse.', 'underwood')

print("Done! Run 'python3 typewriter.py' for the interactive experience.")