#!/usr/bin/env python3
"""Render a single static frame of the board for screenshot purposes."""
import ouija

board, planchette = ouija.render_board(ouija.SPIRITS[0]["color"], ouija.PLANCHETTE_HOME)
print(board)
print()
print("  Planchette overlay chars:", [s[2] for s in planchette])