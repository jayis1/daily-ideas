#!/usr/bin/env python3
"""Search for verified mate-in-2 and mate-in-3 patterns"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chess_puzzle import Board, find_forced_mate, find_mate_in_1_moves, move_to_algebraic, _setup_pattern

# Known good: Pattern 0 (smothered mate with Nf6 + Qd4)
# FEN: 6rk/6pp/5N2/8/3Q4/8/8/4K3 w - verified mate in 2

# Let me systematically try positions
print("=== Searching for mate-in-2 patterns ===")

# Smothered mate variants
positions_m2 = [
    # Pattern 0 (already verified): Smothered mate
    # Kh8, Rg8, pg7, ph7, Nf6, Qd4, Ke1
    ("Smothered Qd4", [(7, 4, 'K'), (4, 3, 'Q'), (2, 5, 'N')], [(0, 7, 'k'), (0, 6, 'r'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Try: Kh8, Rg8, pf7, pg7, ph7, Nf6, Qe5
    ("Qe5 smothered", [(7, 4, 'K'), (3, 4, 'Q'), (2, 5, 'N')], [(0, 7, 'k'), (0, 6, 'r'), (1, 5, 'p'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Back rank mate: Kh8, Rf8, pg7, ph7 vs Ke1, Rd1
    # Rd8+ Rxd8# - no, that's not forced because black can block
    # Let's try: Kh8, pg7, ph7, Ke1, Qd1 vs Kh8
    ("Qd1 back rank", [(7, 4, 'K'), (7, 3, 'Q')], [(0, 7, 'k'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Try Arabian mate with Rook + Knight
    # Kh8, pg7 vs Kh1, Ng5, Rg1
    # Actually, let me try a known Arabian: Nf6 + Rook on g-file
    # Kh8, pg7 vs Ke1, Nf6, Rg1
    # 1.Ng8+?? No. Let me think...
    # Arabian mate: 1.Rg8+ Kh7 2.Nf6+ Kh6 3.Rg6# -- that's mate in 3
    # Simpler: Kh8, pg7, Nf6, Rg1 -> 1.Ng8? No
    # Let's try: Nf6, Rh1 -> 1.Rh8#? That's mate in 1 if not blocked
    
    # Try: Kb1, Rg1 vs Kh8, pg7, ph7
    # 1.Rg8+... no, not forced
    
    # Simple ladder mate with Q+R
    # Kh8, pg7, ph7 vs Ke1, Qd4, Rd1
    ("Q+R ladder", [(7, 4, 'K'), (4, 3, 'Q'), (7, 3, 'R')], [(0, 7, 'k'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Q sacrifice on g8
    # Kh8, Rg8, pg7, ph7 vs Ke1, Qd4
    # Already tested - not forced mate!
    
    # Try: Kh8, pg7, ph7, Nf6 vs Ke1, Qa4
    ("Qa4+N", [(7, 4, 'K'), (4, 0, 'Q'), (2, 5, 'N')], [(0, 7, 'k'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Boden's mate: Bb5+ Ka8, Bxe8... no
    # Opera mate: Rook on back rank
    
    # Try: Kh8, pg7, ph7 vs Kf1, Qf3
    # 1.Qf8+ Kh7 -> what next?
    ("Qf3 approach", [(7, 5, 'K'), (5, 5, 'Q')], [(0, 7, 'k'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Try Greco's mate: Bg5 vs Kh8
    # Kb1, Bg5, Qh5 vs Kh8, Rf8, pg7, ph7
    ("Greco mate", [(7, 1, 'K'), (3, 6, 'B'), (3, 7, 'Q')], [(0, 7, 'k'), (0, 5, 'r'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Try: Kb1, Qh5 vs Kh8, pf7, pg7, ph7
    ("Qh5 mate", [(7, 1, 'K'), (3, 7, 'Q')], [(0, 7, 'k'), (1, 5, 'p'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Try: Kg1, Qd5 vs Kh8, pf7, pg7, ph7  
    ("Qd5", [(7, 6, 'K'), (3, 3, 'Q')], [(0, 7, 'k'), (1, 5, 'p'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Try: Kg1, Qg4 vs Kh8, pg7, ph7
    ("Qg4", [(7, 6, 'K'), (4, 6, 'Q')], [(0, 7, 'k'), (1, 6, 'p'), (1, 7, 'p')]),
]

for name, white, black in positions_m2:
    b = Board()
    _setup_pattern(b, white, black)
    m1 = find_mate_in_1_moves(b, 'w')
    forced = find_forced_mate(b, 'w', 7)
    if forced == 4 and len(m1) == 0:
        print(f"✓ {name}: FEN={b.to_fen()}")
        print(f"  Mate-in-2 (verified!)")
    else:
        print(f"  {name}: m1={len(m1)}, forced={forced}")

print()
print("=== Searching for mate-in-3 patterns ===")

positions_m3 = [
    # Extended smothered: more pieces to make it harder
    # Kh8, Rg8, pf7, pg7, ph7, Nf6, Qd4, Ke1
    ("Smothered extended", [(7, 4, 'K'), (4, 3, 'Q'), (2, 5, 'N')], [(0, 7, 'k'), (0, 6, 'r'), (1, 5, 'p'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Kh8, pg7, ph7 vs Ke1, Qd1, Bg5
    ("Q+B", [(7, 4, 'K'), (7, 3, 'Q'), (3, 6, 'B')], [(0, 7, 'k'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Kh8, pg7, ph7 vs Ke1, Qd1, Rf1
    ("Q+R", [(7, 4, 'K'), (7, 3, 'Q'), (7, 5, 'R')], [(0, 7, 'k'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Kg8, pf7, pg7, ph7 vs Ke1, Qd4, Rd1
    ("Q+R vs Kg8", [(7, 4, 'K'), (4, 3, 'Q'), (7, 3, 'R')], [(0, 6, 'k'), (1, 5, 'p'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Kh8, Rf8, pg7, ph7 vs Ke1, Qa4
    ("Qa4 vs Kh8 Rf8", [(7, 4, 'K'), (4, 0, 'Q')], [(0, 7, 'k'), (0, 5, 'r'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Kg8, pf7, pg6 vs Ke1, Qd4, Re1
    ("Q+R vs Kg8 minimal", [(7, 4, 'K'), (4, 3, 'Q'), (7, 4, 'R')], [(0, 6, 'k'), (1, 5, 'p')]),
    
    # Try some random positions with more pieces
    ("Rook staircase", [(7, 0, 'K'), (6, 0, 'R'), (6, 7, 'R')], [(0, 7, 'k'), (1, 6, 'p'), (1, 7, 'p')]),
    
    # Kg1, Rf1, Rf7 vs Kh8, pg7, ph7 - staircase mate
    ("Rook ladder", [(7, 6, 'K'), (1, 5, 'R'), (7, 5, 'R')], [(0, 7, 'k'), (1, 6, 'p'), (1, 7, 'p')]),
]

for name, white, black in positions_m3:
    b = Board()
    # Check for overlaps
    occupied = set()
    ok = True
    for r, c, p in white + black:
        if (r, c) in occupied:
            ok = False
        occupied.add((r, c))
    if not ok:
        print(f"  {name}: OVERLAP! Skipping")
        continue
    _setup_pattern(b, white, black)
    wk = b.find_king('w')
    bk = b.find_king('b')
    if not wk or not bk:
        print(f"  {name}: Missing king!")
        continue
    m1 = find_mate_in_1_moves(b, 'w')
    forced = find_forced_mate(b, 'w', 9)
    full_moves = (forced + 1) // 2 if forced > 0 else -1
    if forced == 5 and len(m1) == 0:
        print(f"✓ {name}: FEN={b.to_fen()}")
        print(f"  Mate-in-3 (verified!)")
    elif forced > 0:
        print(f"  {name}: m1={len(m1)}, forced={forced} half-moves ({full_moves} full moves)")
    else:
        print(f"  {name}: m1={len(m1)}, forced=-1")

print()
print("=== Exhaustive search for simple mate-in-2 patterns ===")
# Try many positions with Q/R+B+N combos vs corner king + pawns
import random
random.seed(42)
found = 0
attempts = 0
for _ in range(2000):
    b = Board()
    b.turn = 'w'
    # Place black king in corner
    bk_r = random.choice([0, 7])
    bk_c = random.choice([0, 1, 6, 7])
    b.set(bk_r, bk_c, 'k')
    
    # Add restricting pawns
    pawn_dir = 1 if bk_r < 4 else -1
    for dc in [-1, 0, 1]:
        pr = bk_r + pawn_dir
        pc = bk_c + dc
        if 0 <= pr < 8 and 0 <= pc < 8 and random.random() < 0.7:
            if b.get(pr, pc) is None:
                b.set(pr, pc, 'p')
    
    # Place white king at safe distance
    for _ in range(30):
        wk_r, wk_c = random.randint(0, 7), random.randint(0, 7)
        if b.get(wk_r, wk_c) is None and abs(wk_r - bk_r) + abs(wk_c - bk_c) >= 3:
            b.set(wk_r, wk_c, 'K')
            break
    
    # Add 2-3 white pieces
    pieces_pool = ['Q', 'R', 'B', 'N']
    num_pieces = random.randint(2, 3)
    for _ in range(num_pieces):
        pt = random.choice(pieces_pool)
        for _ in range(20):
            pr, pc = random.randint(0, 7), random.randint(0, 7)
            if b.get(pr, pc) is None:
                # Don't place on line with bk for Q/R (would be check)
                if pt in ('Q', 'R') and (pr == bk_r or pc == bk_c):
                    continue
                if pt in ('Q', 'B') and abs(pr - bk_r) == abs(pc - bk_c):
                    continue
                b.set(pr, pc, pt)
                break
    
    if b.in_check('b'):
        continue
    
    attempts += 1
    m1 = find_mate_in_1_moves(b, 'w')
    if m1:
        continue
    
    forced = find_forced_mate(b, 'w', 7)
    if forced == 4:
        found += 1
        print(f"  Found mate-in-2: {b.to_fen()}")
        # List pieces
        for r, c, p in b.pieces():
            sq = b.rc_to_algebraic(r, c)
            print(f"    {p} on {sq}")
        if found >= 3:
            break

print(f"Attempts: {attempts}, Found: {found}")