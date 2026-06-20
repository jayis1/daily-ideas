#!/usr/bin/env python3
"""Manually test the smothered mate position"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chess_puzzle
chess_puzzle._MAX_SEARCH_NODES = 500000

from chess_puzzle import Board, find_mate_in_1_moves, move_to_algebraic

b = Board.from_fen("6rk/6pp/5N2/8/8/Q7/8/6K1 w")
print("Starting position:", b.to_fen())
print(b.display())

# 1. Qg8+ (queen takes rook on g8? No, queen goes to g8 which is check)
# Wait, queen is on a3 (row 2, col 0). Can queen reach g8?
# Queen on a3 -> can go to g8 via diagonal a3-b4-c5-d6-e7-f8... no, that's the wrong diagonal
# Queen on a3 -> a3 to g8: that's not a valid queen move. Let me check diagonals.
# a3 (2,0) -> diagonals: (1,1), (0,2) upward; (3,1), (4,2), (5,3), (6,4), (7,5) downward
# Ranks: a3 -> a-file (0,0), (1,0), ... (7,0); rank 3 -> (2,0), (2,1), ... (2,7)
# Hmm, queen on (2,0) = a3 can reach (5,3) = d6 via (3,1) (4,2) (5,3)
# But can it reach g8 = (0,6)?
# From (2,0) to (0,6): row diff = -2, col diff = +6. Not same row/col/diagonal.
# So the queen CANNOT go to g8 from a3!

# The original smothered mate had queen on d4 (row 4, col 3).
# d4 to g8: (4,3) to (0,6): row diff = -4, col diff = +3. Not diagonal (4 ≠ 3). Not same row/col.
# So Qd4 also can't reach g8.

# Classic smothered mate requires: Qg8+! Rxg8 Nf7#
# Queen must be on a square that can reach g8.
# Squares that can reach g8: g-file, 8th rank, or diagonals through g8.
# From g8: g-file (g7, g6, g5, g4, g3, g2, g1), 8th rank (a8-h8), 
# diagonals (h7, f7, e6, d5, c4, b3, a2) and (h9 invalid, f9 invalid)
# So queen needs to be on g1-g7, a8-f8, h8, or on the a2-g8 diagonal, or on the diagonal f7, e6, etc.

# Wait, queen needs to sacrifice on g8. So queen needs a clear path to g8.
# a2-g8 diagonal: a2(6,0), b3(5,1), c4(4,2), d5(3,3), e6(2,4), f7(1,5), g8(0,6)
# But f7 might be blocked by a pawn!

# The position I set up has queen on Qa3 which is (2,0), not on the a2-g8 diagonal.

# Let me set up the correct position:
# Kh8, Rg8, pg7, ph7 vs Kg1, Qd5, Nf6
# Qd5 = (3,3), which is on the diagonal d5-e6-f7-g8? 
# d5 to g8: (3,3) to (0,6). Row diff = -3, col diff = +3. YES! Same diagonal!
# But is f7 blocked? f7 = (1,5). In our position, f7 is empty (pawns are on g7 and h7).
# So Qd5 can reach g8 via e6, f7.

b2 = Board()
b2.turn = 'w'
b2.set(7, 6, 'K')   # Kg1
b2.set(3, 3, 'Q')    # Qd5
b2.set(2, 5, 'N')    # Nf6
b2.set(0, 7, 'k')    # Kh8
b2.set(0, 6, 'r')    # Rg8
b2.set(1, 6, 'p')    # pg7
b2.set(1, 7, 'p')    # ph7

print("\nCorrected smothered mate position:", b2.to_fen())
print(b2.display())

# Check if Qg8+ is a legal move
moves = b2.generate_legal_moves('w')
for m in moves:
    piece = b2.grid[m[0]][m[1]]
    if piece and piece.upper() == 'Q':
        alg = move_to_algebraic(b2, m)
        if 'g8' in alg.lower():
            print(f"Queen can go to g8: {alg}")

# Try Qg8+ manually
# Qd5 to g8: (3,3) -> (0,6)
# Check if path is clear
print("\nPath check d5 to g8:")
for r, c in [(2, 4), (1, 5)]:
    piece = b2.grid[r][c]
    print(f"  ({r},{c}) = {piece}")

# The path goes through e6 (2,4) and f7 (1,5). 
# Both should be empty for the queen to pass.
# e6 is empty, f7 is... let me check.

forced = chess_puzzle.find_forced_mate(b2, 'w', 5)
print(f"\nForced mate depth: {forced}")

# Also try with even higher limit
chess_puzzle._MAX_SEARCH_NODES = 1000000
forced = chess_puzzle.find_forced_mate(b2, 'w', 5)
print(f"Forced mate depth (1M nodes): {forced}")

# Let's also manually verify by playing Qg8+
# Move: (3,3) -> (0,6), capturing rook on (0,6)
print("\nPlaying Qxg8+...")
b3 = b2.make_move((3, 3, 0, 6, None))
print(b3.display())
# After Qxg8+, it should be check to the king on h8
# Wait, queen captures rook on g8, so queen is now on g8.
# Is king on h8 in check from queen on g8? Yes! (adjacent on 8th rank)
# King must respond. Can king take queen on g8? h8-g8 = one square. 
# But is that check? After Kxg8, Nf7 would check... wait, Nf6 can go to f7 only if f7 is empty
# Wait, the classic smothered mate goes: 1.Qg8+!? Rxg8 (forced, as king can't move) 
# Wait, can king go somewhere? h8 to g8? That's where the queen just went. h8 to h7? h7 has pawn.
# What about Kh7? Wait, h7 has pawn. So king can't go to h7.
# Actually let me check - after Qg8+, where can the king go?
# h8 -> g8: occupied by queen (and rook was there, now captured)
# h8 -> h7: pawn on h7 blocks... wait, is it own pawn? Yes, black pawn on h7.
# So king has NO moves. But wait, rook on g8 is captured by the queen.
# After Qxg8+, position has: queen on g8, no rook.
# King on h8 can't go to g8 (queen), h7 (own pawn). What about g7? Own pawn on g7.
# So it's CHECKMATE? But that would be mate-in-1!
# Unless... wait, I'm confused. Let me check: after Qxg8+, is it checkmate?
# King on h8, queen on g8. King can't go to g8 (queen), g7 (own pawn), h7 (own pawn).
# No escape squares! So it IS checkmate in 1!

# That means the position is actually mate-in-1 with Qxg8#!
# The smothered mate pattern requires a DIFFERENT setup where Qg8+ is NOT checkmate
# but forces Rxg8, and then Nf7# is mate.

# For Qg8+ NOT to be mate, the king needs an escape square.
# The classic pattern: Kh8, Rg8, pg7, ph7 with queen coming to g8.
# But after Qxg8+, king has no escape (g7 and h7 blocked by pawns).
# So it IS checkmate in 1!

# The smothered mate pattern actually works when the king CAN capture the queen.
# After Rxg8, then Nf7# is mate because the rook on g8 blocks the king's escape
# and the knight delivers check.

# But wait, in this position after Qg8+, can the rook capture? Rg8 is the piece being captured.
# So after Qxg8+, there's NO rook to take back. The queen just captured it.
# King has no escape = checkmate.

# For a true smothered mate-in-2, we need: Qg8+ (queen sacrifice, NOT capturing anything)
# The queen goes to g8 as a sacrifice. Then Rxg8 takes the queen.
# Then Nf7# is mate because the rook on g8 (which just captured) blocks escape.

# So the queen needs a clear path to g8 WITHOUT capturing anything on g8.
# That means g8 must be EMPTY, and the rook must be elsewhere.
# Classic: Kh8, Rf8, pg7, ph7 vs Kg1, Qd5, Nf6
# 1.Qg8+!? But wait, g8 is empty so queen goes there.
# After Qg8+, king can't take on g8 (queen is there, not a rook).
# Actually king CAN take the queen on g8! But then the pattern doesn't work.
# The pattern requires that the ROOK takes the queen, not the king.
# So we need: Kh8, Rf8, pg7, ph7 and queen can reach g8.
# After Qg8+, king can go to h7? No, pawn there. King can't go to g7 (pawn there).
# King can take queen on g8? Kxg8... but then Nf7+ doesn't work well.

# Actually the REAL smothered mate pattern is:
# 1.Nf7+ Kg8 2.Nh6+ (double check) Kh8 3.Qg8+! Rxg8 4.Nf7# 
# That's mate in 4, not 2.

# For a simple mate-in-2 smothered mate, we need:
# 1.Qg8+ Rxg8 2.Nf7#
# Where queen is sacrificed on g8, rook MUST take, then knight mates.
# For this, queen must give check from g8, and the only response must be Rxg8.

# Position: Kh8, Rg8, pg7, ph7 vs Kg1, Qd5, Nf6
# Wait, queen on d5 going to g8 IS check (queen attacks h8 via rank 8 after reaching g8? No...
# Queen on g8 attacks h8 (one square away on same rank). YES, it's check.
# Can king take on g8? King on h8 can go to g8 one square. 
# But queen is on g8 after the move. Can king capture queen on g8?
# Is g8 a legal move for the king? The king on h8 can move to g8, g7, or h7.
# g7 has a pawn (own), h7 has a pawn (own). So only g8 is available.
# But after Kxg8, is that legal? The king captures the queen on g8.
# But wait, we also have Nf6 which attacks g8 and h7. 
# So if Kxg8, the king would be on g8, attacked by Nf6 (which attacks g8? Let me check).
# Knight on f6 attacks: d5, d7, e4, e8, g4, g8, h5, h7.
# Yes! Nf6 attacks g8! So Kxg8 is ILLEGAL because g8 is attacked by the knight.
# Therefore after 1.Qg8+, the only response is Rxg8 (rook captures queen).
# Then 2.Nf7# is checkmate because:
# - Nf7 attacks h8 (check!)
# - King can't go to g8 (rook there), g7 (own pawn), h7 (own pawn)
# 
# THIS IS THE CORRECT SMOTHERED MATE PATTERN!

# But the position I set up had Rg8 (rook on g8), so queen can't go to g8 without capturing.
# I need Rook on f8 (not g8) so g8 is empty for the queen sacrifice.

b4 = Board()
b4.turn = 'w'
b4.set(7, 6, 'K')   # Kg1
b4.set(3, 3, 'Q')    # Qd5
b4.set(2, 5, 'N')    # Nf6
b4.set(0, 7, 'k')    # Kh8
b4.set(0, 5, 'r')    # Rf8
b4.set(1, 6, 'p')    # pg7
b4.set(1, 7, 'p')    # ph7

print("\n\nCORRECTED: Smothered mate with Rf8:")
print(f"FEN: {b4.to_fen()}")
print(b4.display())

m1_4 = find_mate_in_1_moves(b4, 'w')
print(f"Mate-in-1: {len(m1_4)}")

forced_4 = chess_puzzle.find_forced_mate(b4, 'w', 5)
print(f"Forced mate depth: {forced_4}")

if forced_4 == 4:
    best, depth = chess_puzzle.find_best_move(b4, 'w', 5)
    if best:
        print(f"Best first move: {move_to_algebraic(b4, best)}")