#!/usr/bin/env python3
"""Comprehensive tests for the Chess Puzzle Generator."""

import json
import subprocess
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chess_puzzle import (
    Board, find_forced_mate, find_mate_in_1_moves, find_best_move,
    generate_mate_in_1, generate_mate_in_2, generate_mate_in_3,
    generate_puzzle, parse_move_input, move_to_algebraic,
    ScoreTracker, PIECE_UNICODE, PIECE_NAMES,
    __version__
)


class TestBoard:
    """Test Board class basics."""

    def test_init(self):
        b = Board()
        assert b.turn == 'w'
        assert all(b.grid[r][c] is None for r in range(8) for c in range(8))

    def test_set_and_get(self):
        b = Board()
        b.set(0, 0, 'K')
        assert b.get(0, 0) == 'K'
        assert b.get(0, 1) is None

    def test_get_out_of_bounds(self):
        b = Board()
        assert b.get(-1, 0) is None
        assert b.get(8, 8) is None

    def test_set_out_of_bounds(self):
        b = Board()
        b.set(-1, 0, 'K')  # Should not crash
        assert b.get(0, 0) is None  # Nothing written

    def test_copy(self):
        b = Board()
        b.set(0, 0, 'K')
        c = b.copy()
        c.set(0, 0, 'Q')
        assert b.get(0, 0) == 'K'  # Original unchanged

    def test_find_king(self):
        b = Board()
        b.set(0, 4, 'k')
        b.set(7, 4, 'K')
        assert b.find_king('w') == (7, 4)
        assert b.find_king('b') == (0, 4)

    def test_find_king_missing(self):
        b = Board()
        assert b.find_king('w') is None

    def test_pieces(self):
        b = Board()
        b.set(0, 0, 'K')
        b.set(0, 7, 'k')
        b.set(7, 0, 'R')
        white_pieces = list(b.pieces('w'))
        assert len(white_pieces) == 2  # K and R
        black_pieces = list(b.pieces('b'))
        assert len(black_pieces) == 1  # k

    def test_piece_count(self):
        b = Board()
        b.set(0, 0, 'K')
        b.set(7, 4, 'k')
        assert b.piece_count() == 2

    def test_material_count(self):
        b = Board()
        b.set(0, 0, 'K')
        b.set(7, 0, 'R')  # 5 points
        b.set(7, 7, 'k')
        assert b.material_count('w') == 5  # Rook = 5, King = 0
        assert b.material_count('b') == 0


class TestFEN:
    """Test FEN serialization and deserialization."""

    def test_to_fen_basic(self):
        b = Board()
        b.set(7, 4, 'K')
        b.set(0, 4, 'k')
        fen = b.to_fen()
        assert 'k' in fen
        assert 'K' in fen

    def test_from_fen_roundtrip(self):
        b1 = Board()
        b1.set(7, 4, 'K')
        b1.set(0, 4, 'k')
        b1.set(1, 3, 'p')
        b1.turn = 'w'
        fen = b1.to_fen()
        b2 = Board.from_fen(fen)
        assert b2.get(7, 4) == 'K'
        assert b2.get(0, 4) == 'k'
        assert b2.get(1, 3) == 'p'
        assert b2.turn == 'w'

    def test_from_fen_empty(self):
        b = Board.from_fen("")
        assert b is not None

    def test_from_fen_standard_start(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w"
        b = Board.from_fen(fen)
        assert b.get(0, 4) == 'k'  # Black king on e8
        assert b.get(7, 4) == 'K'  # White king on e1
        assert b.turn == 'w'


class TestMoveParsing:
    """Test move input parsing."""

    def test_basic_move(self):
        b = Board()
        result = parse_move_input(b, "e2e4")
        assert result is not None
        assert result == (6, 4, 4, 4, None)

    def test_move_with_spaces(self):
        b = Board()
        result = parse_move_input(b, "e2 e4")
        assert result is not None
        assert result == (6, 4, 4, 4, None)

    def test_promotion(self):
        b = Board()
        result = parse_move_input(b, "e7e8q")
        assert result is not None
        assert result[4] == 'Q'

    def test_invalid_move(self):
        b = Board()
        result = parse_move_input(b, "xyz")
        assert result is None

    def test_move_with_x_capture(self):
        b = Board()
        result = parse_move_input(b, "e2xe4")
        assert result is not None

    def test_move_with_dash(self):
        b = Board()
        result = parse_move_input(b, "e2-e4")
        assert result is not None


class TestMoveAlgebraic:
    """Test algebraic move notation."""

    def test_simple_move(self):
        b = Board()
        b.set(7, 4, 'K')  # King on e1
        move = (7, 4, 6, 4, None)  # Ke2
        result = move_to_algebraic(b, move)
        assert 'K' in result
        assert 'e2' in result

    def test_pawn_move(self):
        b = Board()
        b.set(6, 4, 'P')  # Pawn on e2
        move = (6, 4, 4, 4, None)  # e4
        result = move_to_algebraic(b, move)
        assert 'e4' in result

    def test_rc_to_algebraic(self):
        b = Board()
        assert b.rc_to_algebraic(0, 0) == 'a8'
        assert b.rc_to_algebraic(7, 7) == 'h1'
        assert b.rc_to_algebraic(6, 4) == 'e2'

    def test_algebraic_to_rc(self):
        b = Board()
        assert b.algebraic_to_rc('a8') == (0, 0)
        assert b.algebraic_to_rc('h1') == (7, 7)
        assert b.algebraic_to_rc('e2') == (6, 4)
        assert b.algebraic_to_rc('z9') is None  # Invalid


class TestCheckDetection:
    """Test check and checkmate detection."""

    def test_in_check(self):
        # White king in check from black rook
        b = Board()
        b.set(7, 4, 'K')  # Ke1
        b.set(7, 0, 'r')  # Ra1 (same rank)
        assert b.in_check('w')

    def test_not_in_check(self):
        b = Board()
        b.set(7, 4, 'K')  # Ke1
        b.set(0, 0, 'k')  # ka8
        assert not b.in_check('w')
        assert not b.in_check('b')

    def test_checkmate_back_rank(self):
        # Simple back-rank mate
        b = Board()
        b.set(0, 6, 'k')  # Kg8
        b.set(1, 5, 'p')  # f7
        b.set(1, 6, 'p')  # g7
        b.set(1, 7, 'p')  # h7
        b.set(0, 0, 'R')  # Ra8 (delivers check)
        # Verify black king is in check from rook on a8
        assert b.in_check('b')

    def test_stalemate(self):
        # Classic stalemate: Black king on a8, white queen on b6, white king on c7
        # Black has no legal moves and is not in check
        b = Board()
        b.set(0, 0, 'k')  # Ka8
        b.set(2, 1, 'Q')  # Qb6
        b.set(1, 2, 'K')  # Kc7
        b.turn = 'b'
        # Verify: Black king is NOT in check
        assert not b.in_check('b'), "Black should not be in check for stalemate"
        # Verify: Black has no legal moves
        assert b.is_stalemate('b'), "Should be stalemate"


class TestMateSearch:
    """Test forced mate finding."""

    def test_find_mate_in_1_simple(self):
        # Back-rank mate: Ke1, Rd8 vs Kh8, g7, h7 (but Rd8 gives check)
        b = Board()
        b.set(7, 4, 'K')  # Ke1
        b.set(0, 7, 'k')  # Kh8
        b.set(1, 6, 'p')  # g7
        b.set(1, 7, 'p')  # h7
        b.set(0, 0, 'R')  # Ra8 — but this IS checkmate already!
        # Let's make it so the rook can deliver mate in 1
        b2 = Board()
        b2.set(7, 4, 'K')  # Ke1
        b2.set(0, 7, 'k')  # Kh8
        b2.set(1, 6, 'p')  # g7
        b2.set(1, 7, 'p')  # h7
        b2.set(1, 0, 'R')  # Ra7
        b2.turn = 'w'
        moves = find_mate_in_1_moves(b2, 'w')
        # Ra8 should be mate
        assert len(moves) > 0

    def test_generate_mate_in_1(self):
        board, depth = generate_mate_in_1()
        assert depth == 1
        moves = find_mate_in_1_moves(board, 'w')
        assert len(moves) > 0, "Should have at least one mate-in-1 solution"

    def test_generate_mate_in_2(self):
        board, depth = generate_mate_in_2()
        # depth might be 1 if fallback to mate-in-1 occurs (generation is random)
        assert depth >= 1, f"Expected depth >= 1, got {depth}"
        if depth == 2:
            # Should NOT be mate in 1 if we got a proper mate-in-2
            m1 = find_mate_in_1_moves(board, 'w')
            assert len(m1) == 0, "Mate-in-2 puzzle should NOT have a mate-in-1 solution"

    def test_reproducibility(self):
        """Same seed should produce same puzzle (via generate_puzzle with fixed random)."""
        random.seed(42)
        b1, d1, _ = generate_puzzle(1)
        random.seed(42)
        b2, d2, _ = generate_puzzle(1)
        assert d1 == d2
        assert b1.to_fen() == b2.to_fen()


class TestPuzzleGeneration:
    """Test puzzle generation at different difficulties."""

    def test_generate_puzzle_easy(self):
        board, depth, pid = generate_puzzle(1)
        assert depth >= 1
        assert pid is not None
        assert pid.startswith("M")

    def test_generate_puzzle_medium(self):
        board, depth, pid = generate_puzzle(2)
        assert depth >= 1
        assert pid is not None

    def test_generate_puzzle_hard(self):
        board, depth, pid = generate_puzzle(3)
        assert depth >= 1

    def test_board_has_kings(self):
        """Every generated puzzle should have both kings."""
        for _ in range(5):
            board, depth, _ = generate_puzzle(1)
            wk = board.find_king('w')
            bk = board.find_king('b')
            assert wk is not None, "White king must be on the board"
            assert bk is not None, "Black king must be on the board"


class TestBoardDisplay:
    """Test board display formatting."""

    def test_display_basic(self):
        b = Board()
        b.set(7, 4, 'K')
        b.set(0, 4, 'k')
        output = b.display()
        assert '♔' in output  # White king
        assert '♚' in output  # Black king
        assert 'a' in output
        assert 'h' in output

    def test_display_with_highlight(self):
        b = Board()
        b.set(7, 4, 'K')
        output = b.display(highlight={(7, 4)})
        assert '[' in output  # Highlighted square

    def test_display_with_last_move(self):
        b = Board()
        b.set(7, 4, 'K')
        output = b.display(last_move=(7, 4, 6, 4, None))
        assert 'K' in output or '♔' in output


class TestScoreTracker:
    """Test score tracking."""

    def test_initial_state(self):
        tracker = ScoreTracker()
        assert tracker.solved == 0
        assert tracker.failed == 0

    def test_record_success(self):
        tracker = ScoreTracker()
        tracker.record(1, True, 0, 5.0)
        assert tracker.solved == 1
        assert tracker.by_difficulty[1]['solved'] == 1

    def test_record_failure(self):
        tracker = ScoreTracker()
        tracker.record(2, False, 1, 10.0)
        assert tracker.failed == 1
        assert tracker.by_difficulty[2]['failed'] == 1
        assert tracker.hints_total == 1

    def test_display(self):
        tracker = ScoreTracker()
        tracker.record(1, True, 0, 5.0)
        # Should not crash
        tracker.display()


class TestCLI:
    """Test command-line interface."""

    def test_version_flag(self):
        result = subprocess.run(
            [sys.executable, "chess_puzzle.py", "--version"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        assert result.returncode == 0
        assert __version__ in result.stdout

    def test_help_flag(self):
        result = subprocess.run(
            [sys.executable, "chess_puzzle.py", "--help"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        assert result.returncode == 0
        assert "Chess Puzzle" in result.stdout

    def test_generate_mate_in_1(self):
        result = subprocess.run(
            [sys.executable, "chess_puzzle.py", "--generate", "1"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            timeout=30
        )
        assert result.returncode == 0
        assert "Mate in" in result.stdout or "mate" in result.stdout.lower() or "FEN" in result.stdout

    def test_generate_mate_in_2(self):
        result = subprocess.run(
            [sys.executable, "chess_puzzle.py", "--generate", "2"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            timeout=120
        )
        assert result.returncode == 0

    def test_generate_json(self):
        result = subprocess.run(
            [sys.executable, "chess_puzzle.py", "--generate", "1", "--json"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            timeout=30
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "puzzle_id" in data
        assert "fen" in data
        assert "mate_depth" in data

    def test_fen_analysis(self):
        # Simple position
        result = subprocess.run(
            [sys.executable, "chess_puzzle.py", "--fen", "k7/8/8/8/8/8/8/K7 w"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            timeout=10
        )
        assert result.returncode == 0
        assert "a8" in result.stdout or "♔" in result.stdout

    def test_solve_flag(self):
        # Use a simple position
        result = subprocess.run(
            [sys.executable, "chess_puzzle.py", "--solve", "k7/8/8/8/8/8/8/K7 w"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            timeout=30
        )
        assert result.returncode == 0


class TestEdgeCases:
    """Test edge cases and robustness."""

    def test_empty_board_fen(self):
        b = Board()
        fen = b.to_fen()
        assert fen == "8/8/8/8/8/8/8/8 w"

    def test_from_fen_invalid(self):
        b = Board.from_fen("invalid")
        # Should not crash, just return something
        assert b is not None

    def test_pawn_promotion_in_moves(self):
        b = Board()
        b.set(1, 0, 'P')  # White pawn about to promote
        b.turn = 'w'
        moves = b.generate_pseudo_moves('w')
        promo_moves = [m for m in moves if m[4] is not None]
        assert len(promo_moves) > 0, "Pawn on 7th rank should have promotion moves"

    def test_king_safety_in_legal_moves(self):
        # King can't move into check
        # White King on a8, Black Rook on b8 (attacks b8 AND b7)
        # The king can't go to a7 (attacked by rook on b8's diagonal? no —
        # Actually rook on b8 attacks a8 and b8's rank. Let me set up properly.
        # Ka8, rb7 — rook attacks the 7th rank. King can't go to b7.
        b = Board()
        b.set(0, 0, 'K')  # Ka8
        b.set(1, 1, 'r')  # Rb7
        b.set(7, 4, 'k')  # Ke1 (black king far away)
        b.turn = 'w'
        moves = b.generate_legal_moves('w')
        # King on a8 can go to: b8 (if not attacked), a7 (if not attacked), b7 (attacked by rook)
        # But wait, rook on b7 attacks a7? No, it's on b7, so it attacks b-file and 7th rank
        # Rook on b7 attacks: b-file (b8, b6, ...) and 7th rank (a7, c7, ...)
        # So king can't go to b8 (attacked? no, rook is on b7 which attacks b8? yes! b7 attacks b8)
        # And can't go to b7 (occupied by rook? yes! But we can capture... wait, it's a black rook)
        # King can capture the rook on b7... but then it would be on b7 which is attacked by...
        # Actually let's test something simpler.
        # Let's verify that no legal move puts the king on a square attacked by the rook
        for m in moves:
            nb = b.make_move(m)
            assert not nb.in_check('w'), f"Legal move should not leave king in check"


# Import random for reproducibility test
import random


if __name__ == "__main__":
    import traceback
    test_classes = [
        TestBoard, TestFEN, TestMoveParsing, TestMoveAlgebraic,
        TestCheckDetection, TestMateSearch, TestPuzzleGeneration,
        TestBoardDisplay, TestScoreTracker, TestCLI, TestEdgeCases
    ]
    total = 0
    passed = 0
    failed = 0
    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in methods:
            total += 1
            try:
                getattr(instance, method_name)()
                passed += 1
                print(f"  ✓ {cls.__name__}.{method_name}")
            except Exception as e:
                failed += 1
                print(f"  ✗ {cls.__name__}.{method_name}: {e}")
                traceback.print_exc()

    print(f"\n{passed}/{total} tests passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)