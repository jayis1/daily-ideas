# ♟ Chess Puzzle Generator

A terminal-based chess puzzle generator that creates forced-mate puzzles and lets you solve them interactively. Uses a minimax search engine to verify that each puzzle has a guaranteed checkmate sequence.

## Features

- **Procedural puzzle generation** — creates unique mate-in-1, mate-in-2, and mate-in-3 puzzles every time using random piece placement with verification
- **Interactive solving** — play as White and find the forced mate
- **Minimax verification** — every generated puzzle is verified by search to have a forced checkmate
- **Three difficulty levels** — Mate in 1 (Easy), Mate in 2 (Medium), Mate in 3 (Hard)
- **Hint system** — get piece-specific hints when you're stuck
- **Solution viewer** — see the full solution step by step
- **FEN support** — import/export positions in FEN notation
- **Position analysis** — analyze any position for forced mates
- **JSON output** — programmatically access puzzle data via `--json` flag
- **Score tracking** — session statistics for solved/failed puzzles
- **Board display** — Unicode chess piece rendering with move highlighting and check indicators
- **Move formats** — accepts `e2e4`, `e2 e4`, `e2-e4`, and `e2xe4` notation
- **Promotion support** — pawn promotion via `e7e8q` format
- **CLI mode** — generate, analyze, and solve puzzles from the command line
- **Generation timeout** — puzzle generation has a 30-second timeout and falls back to a verified position if needed

## How to Install

No dependencies required — just Python 3.6+ with standard library:

```bash
# Clone or download, then run directly
python3 chess_puzzle.py
```

## How to Run

### Interactive Mode

```bash
# Start the interactive menu
python3 chess_puzzle.py
```

This opens a menu where you can:
1. Generate a mate-in-1 puzzle (Easy)
2. Generate a mate-in-2 puzzle (Medium)
3. Generate a mate-in-3 puzzle (Hard)
4. Enter a FEN position
5. Read the how-to-play guide
6. View your session statistics

### Command-Line Mode

```bash
# Generate a mate-in-1 puzzle and print it
python3 chess_puzzle.py --generate 1

# Generate a mate-in-2 puzzle (may take a few seconds)
python3 chess_puzzle.py --generate 2

# Generate a mate-in-3 puzzle (may take up to 30 seconds)
python3 chess_puzzle.py --generate 3

# Generate puzzle with JSON metadata output
python3 chess_puzzle.py --generate 1 --json

# Analyze a position from FEN
python3 chess_puzzle.py --fen "5r1k/6pp/7N/3Q4/8/8/8/6K1 w"

# Find the forced mate for a position
python3 chess_puzzle.py --solve "5r1k/6pp/7N/3Q4/8/8/8/6K1 w"

# Show version
python3 chess_puzzle.py --version

# Show help
python3 chess_puzzle.py --help
```

### Interactive Commands

During puzzle solving, you can type:

| Command | Description |
|---------|-------------|
| `e2e4` | Make a move (from-square + to-square) |
| `e7e8q` | Move with pawn promotion to Queen |
| `hint` | Get a hint (shows which piece to move and where) |
| `solve` | See the full solution step by step |
| `show` | Redisplay the current board position |
| `reset` | Start the puzzle over from the beginning |
| `fen` | Show the current position as a FEN string |
| `quit` | Return to the menu |

## JSON Output

When using `--generate N --json`, the output is structured JSON:

```json
{
  "puzzle_id": "M1-9589",
  "mate_depth": 1,
  "fen": "1k6/ppp4R/8/8/8/8/3K4/8 w",
  "turn": "w",
  "generation_time_s": 0.01,
  "piece_count": 6,
  "verified_mate_half_moves": 2,
  "verified_mate_full_moves": 1,
  "mate_in_1_solutions": 1,
  "solutions": ["Rh8#"]
}
```

## How It Works

### Puzzle Generation

1. **Mate-in-1**: Randomly places a black king in a corner, adds restricting pawns, a white king at safe distance, and a queen or rook. Verifies the position has at least one mate-in-1 solution.

2. **Mate-in-2**: Uses random piece placement (white king, queen/rook, and restricting pawns around the black king). Verifies the position has a forced mate-in-2 (4 half-moves) but NOT mate-in-1. Falls back to a verified smothered mate position (Qg8+! Rxg8 Nf7#) if generation times out.

3. **Mate-in-3**: Uses similar random generation with more pieces. Verifies forced mate-in-3 (5 half-moves) but not shorter. Falls back to a mate-in-2 if generation times out (30 second limit).

### Search Engine

The mate search uses a minimax algorithm with:
- **Alpha-beta-style pruning**: checking moves are searched first for the attacker
- **Node limit**: aborts after 20,000 nodes to prevent infinite search
- **Move ordering**: checks first, non-checks second for better pruning
- **Defender optimization**: early exit when any escape is found

### Verified Fallback Position

The mate-in-2 fallback is a classic smothered mate:
```
5r1k/6pp/7N/3Q4/8/8/8/6K1 w
```
- Kh8, Rf8, pg7, ph7 vs Kg1, Qd5, Nh6
- 1.Qg8+! Rxg8 2.Nf7# (smothered mate)

## Bug Fixes (v1.1.0 → v1.1.1)

- **Fixed pawn attack direction** — White pawns now correctly attack upward (from higher row to lower) and black pawns attack downward. The previous implementation had the directions inverted, causing incorrect check and checkmate detection in any position involving pawn attacks.
- **Fixed broken puzzle patterns** — All curated mate-in-2 and mate-in-3 patterns were invalid after the pawn fix (some were actually mate-in-1, others had no forced mate). Replaced with random generation + verification approach with a verified smothered mate fallback.
- **Fixed mate-in-3 generation** — The `generate_mate_in_3` function previously returned a mate-in-2 (depth=2) when falling back, now correctly falls back to `generate_mate_in_2()` and reports its actual depth.
- **Fixed hint/search depth** — Hints and move-correctness checking for mate-in-3 puzzles now use `max_half_moves=7` (matching the puzzle depth) instead of `max_half_moves=5`, so they can actually find the correct solution.
- **Added generation timeouts** — Both `generate_mate_in_2` and `generate_mate_in_3` now have 30-second timeouts to prevent excessive computation, falling back to verified positions.

## Testing

Run the comprehensive test suite:

```bash
python3 test_chess_puzzle.py
```

Tests cover: Board operations, FEN serialization, move parsing, algebraic notation, check/checkmate/stalemate detection, forced mate search, puzzle generation, board display, score tracking, CLI flags, and edge cases.

## Piece Notation

| Symbol | White | Black |
|--------|-------|-------|
| King   | ♔ | ♚ |
| Queen  | ♕ | ♛ |
| Rook   | ♖ | ♜ |
| Bishop | ♗ | ♝ |
| Knight | ♘ | ♞ |
| Pawn   | ♙ | ♟ |

## Known Limitations

- No castling or en passant support (simplification for puzzle positions)
- Move disambiguation in algebraic notation (e.g., Nbd2 vs Nfd2) is not implemented — uses coordinate notation internally
- Mate-in-3 generation can be slow (up to 30 seconds) and may fall back to a mate-in-2 position
- The search node limit (20,000) may cause some positions to report "no forced mate" when one exists deeper in the tree

## License

MIT