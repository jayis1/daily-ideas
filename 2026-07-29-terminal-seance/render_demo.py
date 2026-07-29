#!/usr/bin/env python3
"""Render a single static frame of the board for screenshot purposes.

Also prints a quick legend so the screenshot is self-explanatory.

Usage:
    python3 render_demo.py [--no-color]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ouija


def main():
    parser = argparse.ArgumentParser(description="Static board screenshot renderer")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors")
    args = parser.parse_args()
    if args.no_color:
        ouija.set_no_color(True)

    board, planchette = ouija.render_board(ouija.SPIRITS[0]["color"], ouija.PLANCHETTE_HOME)
    print(board)
    print()
    print("  Planchette overlay chars:", [s[2] for s in planchette])
    print()
    print(f"  Board size: {ouija.BOARD_WIDTH} cols x {ouija.BOARD_HEIGHT} rows")
    print(f"  Spirits available: {len(ouija.SPIRITS)}")
    print(f"  Version: ouija v{ouija.__version__}")


if __name__ == "__main__":
    main()