import time
from chess_puzzle import Board, find_forced_mate, find_mate_in_1_moves

# Test curated positions for mate-in-2

# Position 1: Kg1, Qd1, Bg5, Rf1. Kg8, f7, g7, h7
board1 = Board()
board1.turn = 'w'
board1.set(7, 6, 'K')
board1.set(7, 3, 'Q')
board1.set(3, 6, 'B')
board1.set(7, 5, 'R')
board1.set(0, 6, 'k')
board1.set(1, 5, 'p')
board1.set(1, 6, 'p')
board1.set(1, 7, 'p')

print("Position 1: Kg1, Qd1, Bg5, Rf1 vs Kg8, f7, g7, h7")
start = time.time()
d = find_forced_mate(board1, 'w', max_half_moves=5)
elapsed = time.time() - start
print(f"Forced mate: {d} half-moves ({elapsed:.2f}s)")

# Position 2: Kc1, Qd1, Re1. Kg8, f7, g7, h7
board2 = Board()
board2.turn = 'w'
board2.set(7, 2, 'K')
board2.set(7, 3, 'Q')
board2.set(7, 4, 'R')
board2.set(0, 6, 'k')
board2.set(1, 5, 'p')
board2.set(1, 6, 'p')
board2.set(1, 7, 'p')

print("\nPosition 2: Kc1, Qd1, Re1 vs Kg8, f7, g7, h7")
start = time.time()
d2 = find_forced_mate(board2, 'w', max_half_moves=5)
elapsed2 = time.time() - start
print(f"Forced mate: {d2} half-moves ({elapsed2:.2f}s)")

# Position 3: Back rank mate setup
board3 = Board()
board3.turn = 'w'
board3.set(7, 6, 'K')
board3.set(7, 3, 'Q')
board3.set(7, 0, 'R')
board3.set(0, 6, 'k')
board3.set(1, 5, 'p')
board3.set(1, 6, 'p')
board3.set(1, 7, 'p')

print("\nPosition 3: Kg1, Qd1, Ra1 vs Kg8, f7, g7, h7")
start = time.time()
d3 = find_forced_mate(board3, 'w', max_half_moves=5)
elapsed3 = time.time() - start
print(f"Forced mate: {d3} half-moves ({elapsed3:.2f}s)")