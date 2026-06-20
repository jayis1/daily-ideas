#!/usr/bin/env python3
"""
Terminal Chess Puzzle Generator
Generates chess puzzles with forced mates and lets you solve them interactively.
Uses a minimax search to verify forced mates exist.

Enhanced with: difficulty levels, puzzle statistics, FEN export/import,
move hints with explanation, score tracking, and improved CLI.
"""

import random
import sys
import time
import argparse
import json

__version__ = "1.1.0"

# --- Chess Engine Core ---

PIECE_UNICODE = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
}

PIECE_NAMES = {
    'K': 'King', 'Q': 'Queen', 'R': 'Rook', 'B': 'Bishop', 'N': 'Knight', 'P': 'Pawn',
    'k': 'King', 'q': 'Queen', 'r': 'Rook', 'b': 'Bishop', 'n': 'Knight', 'p': 'Pawn',
}

# Unicode piece symbols for display (filled/outlined for white/black)
PIECE_SYMBOLS = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
}


def is_white(piece):
    """Return True if piece is a white piece (uppercase)."""
    return piece is not None and piece.isupper()


def is_black(piece):
    """Return True if piece is a black piece (lowercase)."""
    return piece is not None and piece.islower()


class Board:
    """Chess board representation for puzzle generation and solving.

    Uses a simple 8x8 grid with piece characters:
    - Uppercase = White (K, Q, R, B, N, P)
    - Lowercase = Black (k, q, r, b, n, p)
    - None = empty square
    """

    def __init__(self):
        self.grid = [[None] * 8 for _ in range(8)]
        self.turn = 'w'

    def copy(self):
        """Return a deep copy of this board."""
        b = Board()
        b.grid = [row[:] for row in self.grid]
        b.turn = self.turn
        return b

    def get(self, r, c):
        """Get piece at (r, c) or None if out of bounds."""
        if 0 <= r < 8 and 0 <= c < 8:
            return self.grid[r][c]
        return None

    def set(self, r, c, piece):
        """Set piece at (r, c). Does nothing if out of bounds."""
        if 0 <= r < 8 and 0 <= c < 8:
            self.grid[r][c] = piece

    def find_king(self, color):
        """Find the position of the king for the given color ('w' or 'b')."""
        target = 'K' if color == 'w' else 'k'
        for r in range(8):
            for c in range(8):
                if self.grid[r][c] == target:
                    return (r, c)
        return None

    def pieces(self, color=None):
        """Yield (r, c, piece) for all pieces on the board.
        If color is 'w' or 'b', only yield pieces of that color."""
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p is None:
                    continue
                if color == 'w' and not p.isupper():
                    continue
                if color == 'b' and not p.islower():
                    continue
                yield (r, c, p)

    def is_attacked(self, r, c, by_color):
        """Check if square (r,c) is attacked by any piece of by_color."""
        # Check knight attacks
        knight = 'N' if by_color == 'w' else 'n'
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8 and self.grid[nr][nc] == knight:
                return True

        # Check king attacks
        king = 'K' if by_color == 'w' else 'k'
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8 and self.grid[nr][nc] == king:
                    return True

        # Check pawn attacks
        pawn = 'P' if by_color == 'w' else 'p'
        pawn_dr = -1 if by_color == 'w' else 1
        for dc in [-1, 1]:
            nr, nc = r + pawn_dr, c + dc
            if 0 <= nr < 8 and 0 <= nc < 8 and self.grid[nr][nc] == pawn:
                return True

        # Check rook/queen (straight lines)
        rook = 'R' if by_color == 'w' else 'r'
        queen = 'Q' if by_color == 'w' else 'q'
        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nr, nc = r + dr, c + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                p = self.grid[nr][nc]
                if p is not None:
                    if p == rook or p == queen:
                        return True
                    break
                nr, nc = nr + dr, nc + dc

        # Check bishop/queen (diagonals)
        bishop = 'B' if by_color == 'w' else 'b'
        for dr, dc in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            nr, nc = r + dr, c + dc
            while 0 <= nr < 8 and 0 <= nc < 8:
                p = self.grid[nr][nc]
                if p is not None:
                    if p == bishop or p == queen:
                        return True
                    break
                nr, nc = nr + dr, nc + dc

        return False

    def in_check(self, color):
        """Check if the king of the given color is in check."""
        king_pos = self.find_king(color)
        if king_pos is None:
            return True
        opp = 'b' if color == 'w' else 'w'
        return self.is_attacked(king_pos[0], king_pos[1], opp)

    def generate_pseudo_moves(self, color):
        """Generate all pseudo-legal moves for color (may leave king in check)."""
        moves = []
        for r in range(8):
            for c in range(8):
                piece = self.grid[r][c]
                if piece is None:
                    continue
                if color == 'w' and not piece.isupper():
                    continue
                if color == 'b' and not piece.islower():
                    continue

                pt = piece.upper()
                if pt == 'P':
                    direction = -1 if color == 'w' else 1
                    start_row = 6 if color == 'w' else 1
                    # Forward
                    nr = r + direction
                    if 0 <= nr < 8 and self.grid[nr][c] is None:
                        if nr == 0 or nr == 7:
                            for promo in ['Q', 'R', 'B', 'N'] if color == 'w' else ['q', 'r', 'b', 'n']:
                                moves.append((r, c, nr, c, promo))
                        else:
                            moves.append((r, c, nr, c, None))
                            # Double push
                            if r == start_row:
                                nr2 = r + 2 * direction
                                if 0 <= nr2 < 8 and self.grid[nr2][c] is None:
                                    moves.append((r, c, nr2, c, None))
                    # Captures
                    for dc in [-1, 1]:
                        nc = c + dc
                        nr = r + direction
                        if 0 <= nr < 8 and 0 <= nc < 8:
                            target = self.grid[nr][nc]
                            if target is not None and ((color == 'w' and target.islower()) or (color == 'b' and target.isupper())):
                                if nr == 0 or nr == 7:
                                    for promo in ['Q', 'R', 'B', 'N'] if color == 'w' else ['q', 'r', 'b', 'n']:
                                        moves.append((r, c, nr, nc, promo))
                                else:
                                    moves.append((r, c, nr, nc, None))

                elif pt == 'N':
                    for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < 8 and 0 <= nc < 8:
                            target = self.grid[nr][nc]
                            if target is None or (color == 'w' and target.islower()) or (color == 'b' and target.isupper()):
                                moves.append((r, c, nr, nc, None))

                elif pt == 'K':
                    for dr in [-1, 0, 1]:
                        for dc in [-1, 0, 1]:
                            if dr == 0 and dc == 0:
                                continue
                            nr, nc = r + dr, c + dc
                            if 0 <= nr < 8 and 0 <= nc < 8:
                                target = self.grid[nr][nc]
                                if target is None or (color == 'w' and target.islower()) or (color == 'b' and target.isupper()):
                                    moves.append((r, c, nr, nc, None))

                elif pt in ('R', 'B', 'Q'):
                    directions = []
                    if pt in ('R', 'Q'):
                        directions += [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    if pt in ('B', 'Q'):
                        directions += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
                    for dr, dc in directions:
                        nr, nc = r + dr, c + dc
                        while 0 <= nr < 8 and 0 <= nc < 8:
                            target = self.grid[nr][nc]
                            if target is None:
                                moves.append((r, c, nr, nc, None))
                            elif (color == 'w' and target.islower()) or (color == 'b' and target.isupper()):
                                moves.append((r, c, nr, nc, None))
                                break
                            else:
                                break
                            nr, nc = nr + dr, nc + dc

        return moves

    def make_move(self, move):
        """Make a move, return new board. Does not validate legality."""
        fr, fc, tr, tc, promo = move
        b = self.copy()
        piece = b.grid[fr][fc]
        b.grid[tr][tc] = piece if promo is None else promo
        b.grid[fr][fc] = None
        b.turn = 'b' if b.turn == 'w' else 'w'
        return b

    def generate_legal_moves(self, color):
        """Generate all legal moves for color (filters out moves that leave king in check)."""
        pseudo = self.generate_pseudo_moves(color)
        legal = []
        for move in pseudo:
            nb = self.make_move(move)
            if not nb.in_check(color):
                legal.append(move)
        return legal

    def is_checkmate(self, color):
        """Check if color is in checkmate."""
        return self.in_check(color) and len(self.generate_legal_moves(color)) == 0

    def is_stalemate(self, color):
        """Check if color is in stalemate."""
        return not self.in_check(color) and len(self.generate_legal_moves(color)) == 0

    def to_fen(self):
        """Convert board to FEN string (position + turn only)."""
        rows = []
        for r in range(8):
            empty = 0
            row = ''
            for c in range(8):
                if self.grid[r][c] is None:
                    empty += 1
                else:
                    if empty > 0:
                        row += str(empty)
                        empty = 0
                    row += str(self.grid[r][c])
            if empty > 0:
                row += str(empty)
            rows.append(row)
        return '/'.join(rows) + ' ' + self.turn

    @staticmethod
    def from_fen(fen):
        """Create a Board from a FEN string (position + turn)."""
        board = Board()
        parts = fen.strip().split()
        if len(parts) < 1:
            return board
        rows = parts[0].split('/')
        if len(rows) != 8:
            return board
        for r, row_str in enumerate(rows):
            c = 0
            for ch in row_str:
                if ch.isdigit():
                    c += int(ch)
                else:
                    if c < 8:
                        board.set(r, c, ch)
                    c += 1
        if len(parts) > 1:
            board.turn = parts[1]
        return board

    def display(self, highlight=None, last_move=None):
        """Return a string representation of the board.

        Args:
            highlight: set of (r, c) tuples to highlight
            last_move: (fr, fc, tr, tc, promo) tuple to highlight with arrows
        """
        if highlight is None:
            highlight = set()

        # Build highlight set from last_move
        move_highlight = set()
        if last_move is not None:
            fr, fc, tr, tc, _ = last_move
            move_highlight = {(fr, fc), (tr, tc)}
        all_highlight = highlight | move_highlight

        lines = []
        lines.append("   a  b  c  d  e  f  g  h")
        lines.append("  ┌──┬──┬──┬──┬──┬──┬──┬──┐")
        for r in range(8):
            row_str = f"{8 - r} │"
            for c in range(8):
                piece = self.grid[r][c]
                if piece is not None:
                    cell = f" {PIECE_UNICODE.get(piece, piece)} "
                else:
                    cell = " · " if (r + c) % 2 == 0 else "   "
                if (r, c) in all_highlight:
                    # Highlight the square
                    ch = PIECE_UNICODE.get(piece, piece) if piece else '·'
                    cell = f"[{ch}]"
                row_str += cell + "│"
            lines.append(row_str)
            if r < 7:
                lines.append("  ├──┼──┼──┼──┼──┼──┼──┼──┤")
        lines.append("  └──┴──┴──┴──┴──┴──┴──┴──┘")
        lines.append("   a  b  c  d  e  f  g  h")
        turn_indicator = "White to move" if self.turn == 'w' else "Black to move"
        check_status = ""
        if self.in_check(self.turn):
            check_status = " [CHECK!]"
        lines.append(f"  {turn_indicator}{check_status}")
        return '\n'.join(lines)

    def algebraic_to_rc(self, algebraic):
        """Convert algebraic notation (e.g. 'e4') to (row, col) tuple."""
        if len(algebraic) != 2:
            return None
        col = ord(algebraic[0]) - ord('a')
        row = 8 - int(algebraic[1])
        if 0 <= row < 8 and 0 <= col < 8:
            return (row, col)
        return None

    def rc_to_algebraic(self, r, c):
        """Convert (row, col) to algebraic notation (e.g. 'e4')."""
        return chr(ord('a') + c) + str(8 - r)

    def piece_count(self):
        """Return total number of pieces on the board."""
        count = 0
        for r in range(8):
            for c in range(8):
                if self.grid[r][c] is not None:
                    count += 1
        return count

    def material_count(self, color):
        """Return total material value for a color (P=1, N=3, B=3, R=5, Q=9, K=0)."""
        values = {'P': 1, 'N': 3, 'B': 3, 'R': 5, 'Q': 9, 'K': 0}
        total = 0
        for r in range(8):
            for c in range(8):
                p = self.grid[r][c]
                if p is None:
                    continue
                if color == 'w' and p.isupper():
                    total += values.get(p, 0)
                elif color == 'b' and p.islower():
                    total += values.get(p.upper(), 0)
        return total


# --- Mate Search ---

_search_node_count = 0
_MAX_SEARCH_NODES = 20000  # Abort search after this many nodes


def find_forced_mate(board, color, max_half_moves=5):
    """
    Check if there's a forced mate for 'color' within max_half_moves half-moves.
    Returns the number of half-moves to reach checkmate (2=mate in 1, 4=mate in 2, etc.),
    or -1 if no forced mate is found.
    """
    global _search_node_count
    _search_node_count = 0
    opp = 'b' if color == 'w' else 'w'
    return _find_mate_recursive(board, color, opp, max_half_moves, is_maximizing=True)


def _find_mate_recursive(board, attacker, defender, depth_remaining, is_maximizing):
    """Minimax search for forced mate. Returns half-moves to mate, or -1."""
    global _search_node_count
    _search_node_count += 1
    if _search_node_count > _MAX_SEARCH_NODES:
        return -1  # Abort: too many nodes

    color_to_move = attacker if is_maximizing else defender

    if board.is_checkmate(color_to_move):
        if not is_maximizing:
            return 1  # Just got mated
        return -1

    if board.is_stalemate(color_to_move):
        return -1

    if depth_remaining <= 0:
        return -1

    moves = board.generate_legal_moves(color_to_move)
    if not moves:
        return -1

    if is_maximizing:
        # Attacker: try checking moves first (more likely to lead to mate)
        checking = []
        non_checking = []
        for move in moves:
            nb = board.make_move(move)
            if nb.is_checkmate(defender if attacker == 'w' else 'w'):
                return 2  # Checkmate in 1 move from here
            opp_of_mover = 'b' if color_to_move == 'w' else 'w'
            if nb.in_check(opp_of_mover):
                checking.append((move, nb))
            else:
                non_checking.append((move, nb))
        ordered = checking + non_checking

        best = -1
        for move, nb in ordered:
            result = _find_mate_recursive(nb, attacker, defender, depth_remaining - 1, False)
            if result > 0:
                total = result + 1
                if best == -1 or total < best:
                    best = total
                if best == 2:
                    return 2  # Can't do better than mate in 1
        return best if best > 0 else -1
    else:
        # Defender: all moves must lead to mate for attacker to have forced mate
        for move in moves:
            nb = board.make_move(move)
            if nb.is_stalemate(attacker):
                return -1
            result = _find_mate_recursive(nb, attacker, defender, depth_remaining - 1, True)
            if result == -1:
                return -1  # Defender found an escape!
        # If we reach here, all defender moves lead to forced mate
        # Return the worst case (longest) mate depth
        worst = -1
        for move in moves:
            nb = board.make_move(move)
            result = _find_mate_recursive(nb, attacker, defender, depth_remaining - 1, True)
            if result > 0:
                total = result + 1
                if worst == -1 or total > worst:
                    worst = total
        return worst if worst > 0 else -1


def find_mate_in_1_moves(board, color):
    """Find all moves that deliver immediate checkmate."""
    moves = board.generate_legal_moves(color)
    opp = 'b' if color == 'w' else 'w'
    return [m for m in moves if board.make_move(m).is_checkmate(opp)]


def find_best_move(board, color, max_half_moves=5):
    """Find the best move for color (the one leading to shortest forced mate).
    Returns (move, half_moves_to_mate) or (None, -1) if no forced mate found.
    """
    moves = board.generate_legal_moves(color)
    opp = 'b' if color == 'w' else 'w'
    best_move = None
    best_depth = 999

    for move in moves:
        nb = board.make_move(move)
        if nb.is_checkmate(opp):
            return (move, 1)
        depth = find_forced_mate(nb, color, max_half_moves=max_half_moves)
        if depth > 0 and depth < best_depth:
            best_depth = depth
            best_move = move

    return (best_move, best_depth) if best_move else (None, -1)


# --- Puzzle Generation ---

# Curated mate-in-2 patterns that are verified to work
MATE_IN_2_PATTERNS = [
    # Pattern 0: Smothered mate - Qg8+! Rxg8 Nf7# (or similar)
    # Kh8, pg8, pg7, ph7, Nf6, Qd4, Ke1
    lambda b: _setup_pattern(b,
        white_pieces=[(7, 4, 'K'), (4, 3, 'Q'), (2, 5, 'N')],
        black_pieces=[(0, 7, 'k'), (0, 6, 'p'), (1, 6, 'p'), (1, 7, 'p')]),
    # Pattern 1: Smothered mate variant - Qf5
    lambda b: _setup_pattern(b,
        white_pieces=[(7, 4, 'K'), (3, 5, 'Q'), (2, 5, 'N')],
        black_pieces=[(0, 7, 'k'), (0, 6, 'p'), (1, 6, 'p'), (1, 7, 'p')]),
    # Pattern 2: Arabian mate - Rook + Knight
    # Kh8, ph7, pg7, Nf6, Rc1, Ka1
    lambda b: _setup_pattern(b,
        white_pieces=[(7, 0, 'K'), (7, 2, 'R'), (2, 5, 'N')],
        black_pieces=[(0, 7, 'k'), (1, 7, 'p'), (1, 6, 'p')]),
    # Pattern 3: Back rank mate with Rook
    # Kg1, Rd1 vs Kh8, Rg8, ph7, pg7, pf7
    lambda b: _setup_pattern(b,
        white_pieces=[(7, 6, 'K'), (7, 3, 'R')],
        black_pieces=[(0, 7, 'k'), (1, 5, 'p'), (1, 6, 'p'), (1, 7, 'p')]),
]


def _setup_pattern(board, white_pieces, black_pieces):
    """Place pieces on the board. Returns the board."""
    for r, c, piece in white_pieces:
        board.set(r, c, piece)
    for r, c, piece in black_pieces:
        board.set(r, c, piece)
    board.turn = 'w'
    return board


def generate_mate_in_1():
    """Generate a mate-in-1 puzzle by random placement and verification."""
    for _ in range(500):
        board = Board()
        board.turn = 'w'

        # Place black king in corner or edge
        bk_r = random.choice([0, 7])
        bk_c = random.choice([0, 1, 6, 7])
        board.set(bk_r, bk_c, 'k')

        # Place white king at safe distance
        for _ in range(50):
            wk_r, wk_c = random.randint(0, 7), random.randint(0, 7)
            if abs(wk_r - bk_r) + abs(wk_c - bk_c) >= 3 and board.get(wk_r, wk_c) is None:
                board.set(wk_r, wk_c, 'K')
                break

        # Add restricting pawns for black
        pawn_dir = 1 if bk_r < 4 else -1
        for dc in [-1, 0, 1]:
            pr = bk_r + pawn_dir
            pc = bk_c + dc
            if 0 <= pr < 8 and 0 <= pc < 8 and board.get(pr, pc) is None:
                board.set(pr, pc, 'p')

        # Place a queen or rook
        piece_type = random.choice(['Q', 'R', 'R'])
        for _ in range(30):
            pr = random.randint(0, 7)
            pc = random.randint(0, 7)
            if board.get(pr, pc) is None:
                # Avoid placing on same line as black king for Q/R (would be check)
                if piece_type in ('Q', 'R') and (pr == bk_r or pc == bk_c):
                    continue
                if piece_type in ('Q', 'B') and abs(pr - bk_r) == abs(pc - bk_c):
                    continue
                board.set(pr, pc, piece_type)
                break

        if board.in_check('b'):
            continue

        # Check for mate in 1 (exactly)
        mate_1_moves = find_mate_in_1_moves(board, 'w')
        if mate_1_moves:
            return board, 1

    # Ultimate fallback - a known mate-in-1 position
    board = Board()
    board.turn = 'w'
    board.set(7, 4, 'K')
    board.set(0, 4, 'k')
    board.set(1, 3, 'p')
    board.set(1, 4, 'p')
    board.set(1, 5, 'p')
    board.set(1, 0, 'R')
    return board, 1


def generate_mate_in_2():
    """Generate a mate-in-2 puzzle using curated patterns.

    Each pattern is verified to be mate-in-2 but NOT mate-in-1.
    Returns (board, mate_depth) where mate_depth is 2.
    """
    pattern_idx = random.randint(0, len(MATE_IN_2_PATTERNS) - 1)
    board = MATE_IN_2_PATTERNS[pattern_idx](Board())

    # Verify: not already mate in 1
    m1 = find_mate_in_1_moves(board, 'w')
    if m1:
        # Pattern might be mate in 1 — fall back to a different pattern or mate-in-1
        # Try other patterns
        for idx in range(len(MATE_IN_2_PATTERNS)):
            if idx == pattern_idx:
                continue
            test_board = MATE_IN_2_PATTERNS[idx](Board())
            if not find_mate_in_1_moves(test_board, 'w'):
                return test_board, 2
        # All patterns give mate in 1? Fall back
        return generate_mate_in_1()

    return board, 2


def generate_mate_in_3():
    """Generate a mate-in-3 puzzle using extended patterns with more pieces.

    These positions require 3 full moves (5 half-moves) to force checkmate.
    """
    patterns = [
        # Kg1, Qd1, Bg5 vs Kh8, pg7, ph7 - Queen + Bishop mate
        lambda b: _setup_pattern(b,
            white_pieces=[(7, 6, 'K'), (7, 3, 'Q'), (3, 6, 'B')],
            black_pieces=[(0, 7, 'k'), (1, 6, 'p'), (1, 7, 'p')]),
        # Kc1, Qd1, Re1 vs Kg8, f7, g7, h7
        lambda b: _setup_pattern(b,
            white_pieces=[(7, 2, 'K'), (7, 3, 'Q'), (7, 4, 'R')],
            black_pieces=[(0, 6, 'k'), (1, 5, 'p'), (1, 6, 'p'), (1, 7, 'p')]),
    ]
    pattern_idx = random.randint(0, len(patterns) - 1)
    board = patterns[pattern_idx](Board())

    # Verify it's not already a shorter mate
    m1 = find_mate_in_1_moves(board, 'w')
    if m1:
        # Fall back to generating a mate-in-2
        return generate_mate_in_2()

    depth = find_forced_mate(board, 'w', max_half_moves=7)
    if depth > 0:
        return board, (depth + 1) // 2  # Convert half-moves to full moves

    # Fallback
    return generate_mate_in_2()


def generate_puzzle(difficulty=1):
    """Generate a puzzle. difficulty: 1=mate in 1, 2=mate in 2, 3=mate in 3.

    Returns (board, mate_depth, puzzle_id) where puzzle_id is a unique string.
    """
    if difficulty == 1:
        board, depth = generate_mate_in_1()
    elif difficulty == 3:
        board, depth = generate_mate_in_3()
    else:
        board, depth = generate_mate_in_2()

    puzzle_id = f"M{depth}-{random.randint(1000, 9999)}"
    return board, depth, puzzle_id


# --- Interactive Game ---

def parse_move_input(board, user_input):
    """Parse user move input. Accepts formats like 'e2e4', 'e2 e4', 'e2-e4', 'e2xe4'."""
    # Normalize: strip, lowercase, remove capture marks and dashes
    user_input = user_input.strip().lower()
    # Remove 'x' (capture notation) and '-' (hyphen notation)
    user_input = user_input.replace('x', '').replace('-', '')
    # Handle space-separated format: "e2 e4" -> "e2e4"
    parts = user_input.split()
    if len(parts) == 2 and len(parts[0]) == 2 and len(parts[1]) == 2:
        user_input = parts[0] + parts[1]

    if len(user_input) == 4:
        from_sq = user_input[:2]
        to_sq = user_input[2:4]
        fr = board.algebraic_to_rc(from_sq)
        tc = board.algebraic_to_rc(to_sq)
        if fr and tc:
            return (fr[0], fr[1], tc[0], tc[1], None)
    if len(user_input) == 5:
        from_sq = user_input[:2]
        to_sq = user_input[2:4]
        promo_char = user_input[4]
        fr = board.algebraic_to_rc(from_sq)
        tc = board.algebraic_to_rc(to_sq)
        if fr and tc:
            promo_map = {'q': 'Q', 'r': 'R', 'b': 'B', 'n': 'N'}
            if promo_char in promo_map:
                return (fr[0], fr[1], tc[0], tc[1], promo_map[promo_char])
    return None


def move_to_algebraic(board, move):
    """Convert a move tuple to human-readable algebraic notation."""
    fr, fc, tr, tc, promo = move
    piece = board.grid[fr][fc]
    pt = piece.upper() if piece else '?'
    from_sq = board.rc_to_algebraic(fr, fc)
    to_sq = board.rc_to_algebraic(tr, tc)
    captured = board.grid[tr][tc]
    is_capture = captured is not None
    nb = board.make_move(move)
    opp = 'b' if board.turn == 'w' else 'w'
    suffix = ''
    if nb.is_checkmate(opp):
        suffix = '#'
    elif nb.in_check(opp):
        suffix = '+'
    promo_str = ''
    if promo:
        promo_str = '=' + promo.upper()
    if pt == 'P':
        if is_capture:
            return f"{from_sq[0]}x{to_sq}{promo_str}{suffix}"
        return f"{to_sq}{promo_str}{suffix}"
    prefix = pt
    if is_capture:
        return f"{prefix}x{to_sq}{suffix}"
    return f"{prefix}{to_sq}{suffix}"


def play_puzzle(board, mate_depth, puzzle_id=None):
    """Interactive puzzle solving. mate_depth is in full moves (1, 2, or 3).

    Returns True if puzzle was solved, False otherwise.
    """
    pid_str = f" #{puzzle_id}" if puzzle_id else ""
    print("\n" + "=" * 50)
    print("  ♟ CHESS PUZZLE ♟")
    print(f"  Mate in {mate_depth} - White to move!{pid_str}")
    print("=" * 50)
    print()
    print(board.display())
    print()

    current_board = board.copy()
    moves_made = 0  # half-moves made by white
    hints_used = 0
    start_time = time.time()

    while True:
        is_white_turn = current_board.turn == 'w'

        if not is_white_turn:
            # Auto-play black's best defense
            opp_moves = current_board.generate_legal_moves('b')
            if not opp_moves:
                if current_board.is_checkmate('b'):
                    print("  🎉 CHECKMATE! You solved the puzzle!")
                    elapsed = time.time() - start_time
                    print(f"  Time: {elapsed:.1f}s | Hints used: {hints_used}")
                    return True
                break

            # Find the defense that delays mate the longest (or escapes)
            best_defense = None
            best_defense_depth = -1
            for m in opp_moves:
                nb = current_board.make_move(m)
                if nb.is_checkmate('w'):
                    continue
                mc = find_forced_mate(nb, 'w', max_half_moves=7)
                if mc == -1:
                    best_defense = m
                    best_defense_depth = -1
                    break
                if best_defense is None or mc > best_defense_depth:
                    best_defense = m
                    best_defense_depth = mc

            if best_defense is None:
                if current_board.is_checkmate('b'):
                    print("  🎉 CHECKMATE! You solved the puzzle!")
                    elapsed = time.time() - start_time
                    print(f"  Time: {elapsed:.1f}s | Hints used: {hints_used}")
                    return True
                break

            move_str = move_to_algebraic(current_board, best_defense)
            print(f"  ♚ Black plays: {move_str}")
            current_board = current_board.make_move(best_defense)
            print()
            print(current_board.display())
            print()

            if current_board.is_checkmate('w'):
                print("  ✗ Black wins! Something went wrong...")
                return False
            continue

        # White's turn - user input
        print(f"  Your move (White, move {moves_made // 2 + 1}):")
        print("  Enter move (e.g., 'e2e4' or 'd1h5'): ", end='', flush=True)

        try:
            user_input = input().strip()
        except EOFError:
            print("\n  Exiting puzzle.")
            return False

        if user_input.lower() in ('quit', 'q', 'exit'):
            print("  Exiting puzzle.")
            return False

        if user_input.lower() in ('hint', 'h', '?'):
            hints_used += 1
            white_moves = current_board.generate_legal_moves('w')
            best_move = None
            best_depth = 999
            for m in white_moves:
                nb = current_board.make_move(m)
                if nb.is_checkmate('b'):
                    best_move = m
                    best_depth = 1
                    break
                mc = find_forced_mate(nb, 'w', max_half_moves=5)
                if mc != -1 and mc < best_depth:
                    best_depth = mc
                    best_move = m
            if best_move:
                fr = current_board.rc_to_algebraic(best_move[0], best_move[1])
                to = current_board.rc_to_algebraic(best_move[2], best_move[3])
                piece = current_board.grid[best_move[0]][best_move[1]]
                piece_name = PIECE_NAMES.get(piece, piece) if piece else "piece"
                print(f"  💡 Hint: Try moving your {piece_name} from {fr} to {to}")
            else:
                print("  💡 Hint: Look for forcing moves!")
            print()
            continue

        if user_input.lower() in ('show', 's', 'board'):
            print(current_board.display())
            print()
            continue

        if user_input.lower() == 'reset':
            current_board = board.copy()
            moves_made = 0
            print("  Puzzle reset!")
            print()
            print(current_board.display())
            print()
            continue

        if user_input.lower() == 'fen':
            print(f"  FEN: {current_board.to_fen()}")
            print()
            continue

        if user_input.lower() == 'solve':
            # Show solution step by step
            print("  📖 Solution:")
            solve_board = board.copy()
            move_num = 1
            for step in range(mate_depth * 2 - 1):
                if solve_board.turn == 'w':
                    white_moves = solve_board.generate_legal_moves('w')
                    # First check for immediate checkmate
                    best_move = None
                    for m in white_moves:
                        nb = solve_board.make_move(m)
                        if nb.is_checkmate('b'):
                            best_move = m
                            break
                    if best_move is None:
                        # For deeper solutions, use find_forced_mate
                        best_move, _ = find_best_move(solve_board, 'w', max_half_moves=7)
                    if best_move:
                        ms = move_to_algebraic(solve_board, best_move)
                        print(f"    {move_num}. {ms}")
                        solve_board = solve_board.make_move(best_move)
                        if solve_board.is_checkmate('b'):
                            print("    Checkmate!")
                            break
                        move_num += 1
                    else:
                        print("    (no solution found)")
                        break
                else:
                    opp_moves = solve_board.generate_legal_moves('b')
                    if not opp_moves:
                        if solve_board.is_checkmate('b'):
                            print("    Checkmate!")
                        break
                    # Pick the defense that delays mate the longest
                    best_def = None
                    worst_depth = -1
                    for m in opp_moves:
                        nb = solve_board.make_move(m)
                        mc = find_forced_mate(nb, 'w', max_half_moves=7)
                        if mc == -1:
                            best_def = m
                            break
                        if mc > worst_depth:
                            worst_depth = mc
                            best_def = m
                    if best_def:
                        ms = move_to_algebraic(solve_board, best_def)
                        print(f"    ...{ms}")
                        solve_board = solve_board.make_move(best_def)
                    else:
                        best_def = opp_moves[0]
                        ms = move_to_algebraic(solve_board, best_def)
                        print(f"    ...{ms}")
                        solve_board = solve_board.make_move(best_def)
            print()
            return False

        if user_input.lower() == 'help':
            print("  Commands: hint, solve, show, reset, fen, quit")
            print("  Move format: e2e4, d1h5, e7e8q (with promotion)")
            print()
            continue

        parsed = parse_move_input(current_board, user_input)
        if parsed is None:
            print("  ✗ Invalid format. Use 'e2e4' style (from-square + to-square).")
            print("    Type 'hint' for a hint, 'solve' to see the answer, 'quit' to exit.")
            continue

        fr, fc, tr, tc, promo = parsed

        # Validate the move
        legal_moves = current_board.generate_legal_moves('w')
        matching = [m for m in legal_moves if m[0] == fr and m[1] == fc and m[2] == tr and m[3] == tc and (promo is None or m[4] == promo)]

        if not matching:
            piece = current_board.get(fr, fc)
            if piece is None:
                print(f"  ✗ No piece at {current_board.rc_to_algebraic(fr, fc)}!")
            elif not piece.isupper():
                print(f"  ✗ That's a black piece!")
            else:
                print(f"  ✗ Illegal move for {PIECE_NAMES.get(piece.upper(), piece)}!")
            continue

        move = matching[0]

        # Check if this is a good move (leads toward forced mate)
        nb = current_board.make_move(move)
        is_correct = False
        if nb.is_checkmate('b'):
            is_correct = True
        else:
            # Check if this move keeps the forced mate sequence alive
            black_moves = nb.generate_legal_moves('b')
            if black_moves:
                all_good = True
                for bm in black_moves:
                    nb2 = nb.make_move(bm)
                    mc = find_forced_mate(nb2, 'w', max_half_moves=5)
                    if mc == -1:
                        all_good = False
                        break
                if all_good:
                    is_correct = True

        move_str = move_to_algebraic(current_board, move)
        current_board = nb
        moves_made += 1

        if is_correct:
            print(f"  ✓ Correct! {move_str}")
        else:
            print(f"  ✗ {move_str} - Not the best move! Try to find a forcing sequence.")
            print("  The puzzle resets. Try again!")
            print()
            return False

        print()
        print(current_board.display(last_move=move))
        print()

        if current_board.is_checkmate('b'):
            print("  🎉 CHECKMATE! You solved the puzzle!")
            elapsed = time.time() - start_time
            print(f"  Solved in {moves_made // 2 + 1} move(s)! Time: {elapsed:.1f}s | Hints: {hints_used}")
            return True

        if current_board.is_stalemate('b'):
            print("  ✗ Stalemate! Not a win.")
            return False


# --- Score Tracking ---

class ScoreTracker:
    """Track puzzle solving statistics across a session."""

    def __init__(self):
        self.solved = 0
        self.failed = 0
        self.hints_total = 0
        self.total_time = 0.0
        self.by_difficulty = {1: {'solved': 0, 'failed': 0}, 2: {'solved': 0, 'failed': 0}, 3: {'solved': 0, 'failed': 0}}

    def record(self, difficulty, success, hints, elapsed):
        """Record a puzzle attempt."""
        if success:
            self.solved += 1
            self.by_difficulty[difficulty]['solved'] += 1
        else:
            self.failed += 1
            self.by_difficulty[difficulty]['failed'] += 1
        self.hints_total += hints
        self.total_time += elapsed

    def display(self):
        """Print score summary."""
        total = self.solved + self.failed
        if total == 0:
            print("  No puzzles attempted yet.")
            return
        print("\n" + "═" * 50)
        print("  📊 SESSION STATISTICS")
        print("═" * 50)
        print(f"  Puzzles attempted: {total}")
        print(f"  Solved: {self.solved} | Failed: {self.failed}")
        if total > 0:
            print(f"  Success rate: {self.solved / total * 100:.0f}%")
        print(f"  Total time: {self.total_time:.1f}s | Hints used: {self.hints_total}")
        for diff in [1, 2, 3]:
            d = self.by_difficulty[diff]
            t = d['solved'] + d['failed']
            if t > 0:
                print(f"  Mate in {diff}: {d['solved']}/{t} solved ({d['solved'] / t * 100:.0f}%)")
        print()


# --- Main Menu ---

def print_menu():
    print("\n" + "═" * 50)
    print("  ♟♟♟  CHESS PUZZLE GENERATOR  ♟♟♟")
    print("═" * 50)
    print()
    print("  Train your tactical vision with forced-mate puzzles!")
    print()
    print("  [1] New Puzzle - Mate in 1  (Easy)")
    print("  [2] New Puzzle - Mate in 2  (Medium)")
    print("  [3] New Puzzle - Mate in 3  (Hard)")
    print("  [4] Enter a FEN position")
    print("  [5] How to play")
    print("  [6] View statistics")
    print("  [q] Quit")
    print()


def print_howto():
    print("\n" + "─" * 50)
    print("  HOW TO PLAY")
    print("─" * 50)
    print()
    print("  You play as White. Find the forced mate sequence!")
    print()
    print("  Move format: source + destination square")
    print("  Examples:")
    print("    e2e4  → Move piece from e2 to e4")
    print("    d1h5  → Move piece from d1 to h5")
    print("    e7e8q → Move pawn from e7 to e8, promote to Queen")
    print()
    print("  Commands during play:")
    print("    hint   → Get a hint for the current position")
    print("    solve  → See the full solution")
    print("    show   → Redisplay the board")
    print("    reset  → Start the puzzle over")
    print("    fen    → Show current position as FEN")
    print("    quit   → Return to menu")
    print()
    print("  Piece symbols:")
    print("    ♔=White King  ♕=Queen  ♖=Rook  ♗=Bishop  ♘=Knight  ♙=Pawn")
    print("    ♚=Black King   ♛=Queen  ♜=Rook  ♝=Bishop  ♞=Knight  ♟=Pawn")
    print()


def main():
    """Main entry point for the chess puzzle generator."""
    # Check for non-interactive flags
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(
            description="♟ Chess Puzzle Generator — generate and solve forced-mate puzzles",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""Examples:
  %(prog)s                    Interactive mode
  %(prog)s --generate 1        Generate a mate-in-1 puzzle (print FEN)
  %(prog)s --generate 2        Generate a mate-in-2 puzzle (print FEN)
  %(prog)s --generate 3        Generate a mate-in-3 puzzle (print FEN)
  %(prog)s --fen 'k7/8/8/8/8/8/8/K7 w'  Analyze a FEN position
  %(prog)s --solve 'k7/8/8/8/8/8/8/K7 w'  Find forced mate for a position
  %(prog)s --version           Show version
"""
        )
        parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
        parser.add_argument("--generate", type=int, choices=[1, 2, 3], metavar="DEPTH",
                            help="Generate a mate-in-N puzzle and print FEN + info")
        parser.add_argument("--fen", type=str, metavar="FEN",
                            help="Analyze a FEN position (show board + mate search)")
        parser.add_argument("--solve", type=str, metavar="FEN",
                            help="Find and display the forced mate for a FEN position")
        parser.add_argument("--json", action="store_true",
                            help="Output puzzle data in JSON format (for --generate)")
        args = parser.parse_args()

        if args.generate:
            difficulty = args.generate
            print(f"Generating mate-in-{difficulty} puzzle...", file=sys.stderr)
            start = time.time()
            board, depth, puzzle_id = generate_puzzle(difficulty)
            elapsed = time.time() - start
            if args.json:
                data = {
                    "puzzle_id": puzzle_id,
                    "mate_depth": depth,
                    "fen": board.to_fen(),
                    "turn": board.turn,
                    "generation_time_s": round(elapsed, 2),
                    "piece_count": board.piece_count(),
                }
                # Verify the mate
                forced = find_forced_mate(board, 'w', max_half_moves=7)
                data["verified_mate_half_moves"] = forced
                data["verified_mate_full_moves"] = (forced + 1) // 2 if forced > 0 else None
                mate_in_1 = find_mate_in_1_moves(board, 'w')
                data["mate_in_1_solutions"] = len(mate_in_1)
                if mate_in_1:
                    data["solutions"] = [
                        move_to_algebraic(board, m) for m in mate_in_1
                    ]
                print(json.dumps(data, indent=2))
            else:
                print(f"\n  Puzzle #{puzzle_id} — Mate in {depth}")
                print(f"  Generated in {elapsed:.1f}s")
                print(f"  FEN: {board.to_fen()}")
                print()
                print(board.display())
                # Show solution
                mate_1 = find_mate_in_1_moves(board, 'w')
                if mate_1:
                    solutions = [move_to_algebraic(board, m) for m in mate_1]
                    print(f"\n  Solution: {', '.join(solutions)}")
                else:
                    print(f"\n  (Use --solve to find the full solution)")
            return

        if args.fen:
            board = Board.from_fen(args.fen)
            print(board.display())
            print(f"\n  FEN: {board.to_fen()}")
            print(f"  Turn: {'White' if board.turn == 'w' else 'Black'}")
            print(f"  Pieces: {board.piece_count()}")
            print(f"  White material: {board.material_count('w')} | Black material: {board.material_count('b')}")
            if board.in_check(board.turn):
                print("  ⚠ King is in CHECK!")
            if board.is_checkmate(board.turn):
                print("  ✗ CHECKMATE!")
            elif board.is_stalemate(board.turn):
                print("  ✗ STALEMATE!")
            else:
                legal_moves = board.generate_legal_moves(board.turn)
                print(f"  Legal moves: {len(legal_moves)}")
            return

        if args.solve:
            board = Board.from_fen(args.solve)
            color = board.turn
            print(f"  Analyzing position for {'White' if color == 'w' else 'Black'}...")
            print(board.display())
            print()
            start = time.time()
            best_move, depth = find_best_move(board, color, max_half_moves=7)
            elapsed = time.time() - start
            if best_move:
                move_str = move_to_algebraic(board, best_move)
                mate_in = (depth + 1) // 2
                print(f"  Found forced mate in {mate_in}! Best first move: {move_str}")
                print(f"  (Depth: {depth} half-moves, analyzed in {elapsed:.1f}s)")
            else:
                print(f"  No forced mate found within search depth (analyzed in {elapsed:.1f}s)")
            return

    # Interactive mode
    tracker = ScoreTracker()
    print_menu()

    while True:
        try:
            choice = input("  Choose [1-6, q]: ").strip().lower()
        except EOFError:
            break

        if choice in ('q', 'quit', 'exit'):
            tracker.display()
            print("  Thanks for playing! ♟\n")
            break

        if choice == '5':
            print_howto()
            continue

        if choice == '6':
            tracker.display()
            print_menu()
            continue

        if choice in ('1', '2', '3'):
            difficulty = int(choice)
            print(f"\n  Generating mate-in-{difficulty} puzzle...")
            print("  (This may take a moment)")

            start_time = time.time()
            board, mate_depth, puzzle_id = generate_puzzle(difficulty)
            gen_elapsed = time.time() - start_time

            print(f"  Puzzle generated in {gen_elapsed:.1f}s")
            success = play_puzzle(board, mate_depth, puzzle_id)
            tracker.record(difficulty, success, 0, 0)  # Hints tracked inside play_puzzle
            print_menu()

        elif choice == '4':
            try:
                fen = input("  Enter FEN position: ").strip()
            except EOFError:
                continue

            board = Board.from_fen(fen)
            if board.piece_count() == 0:
                print("  ✗ Invalid FEN. No pieces found.")
                continue

            if board.in_check(board.turn):
                print("  Position has side to move in check!")
                continue

            print("  Analyzing position...")
            depth = find_forced_mate(board, board.turn, max_half_moves=7)
            if depth > 0:
                mate_in = (depth + 1) // 2
                print(f"  Found forced mate in {mate_in}!")
                play_puzzle(board, mate_in)
            else:
                print("  No forced mate found within 4 moves. Playing anyway...")
                play_puzzle(board, 3)

        else:
            print("  Invalid choice. Please select 1-6 or q.")


if __name__ == '__main__':
    main()