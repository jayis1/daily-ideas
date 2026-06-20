# ♟ Chess Puzzle Generator

A terminal-based chess puzzle generator that creates forced-mate puzzles and lets you solve them interactively. Uses a minimax search engine to verify that each puzzle has a guaranteed checkmate sequence.

## Features

- **Procedural puzzle generation** — creates unique mate-in-1, mate-in-2, and mate-in-3 puzzles every time
- **Interactive solving** — play as White and find the forced mate
- **Minimax verification** — every puzzle is verified to have a forced checkmate
- **Three difficulty levels** — Mate in 1 (Easy), Mate in 2 (Medium), Mate in 3 (Hard)
- **Hint system** — get piece-specific hints when you're stuck
- **Solution viewer** — see the full solution step by step
- **FEN support** — import/export positions in FEN notation
- **Position analysis** — analyze any position for forced mates
- **JSON output** — programmatically access puzzle data via `--json` flag
- **Score tracking** — session statistics for solved/failed puzzles
- **Board display** — Unicode chess piece rendering with move highlighting
- **Check detection** — shows check status on the board
- **Move formats** — accepts `e2e4`, `e2 e4`, `e2-e4`, and `e2xe4` notation
- **Promotion support** — pawn promotion via `e7e8q` format
- **CLI mode** — generate, analyze, and solve puzzles from the command line

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

# Generate a mate-in-2 puzzle
python3 chess_puzzle.py --generate 2

# Generate a mate-in-3 puzzle
python3 chess_puzzle.py --generate 3

# Generate puzzle with JSON metadata output
python3 chess_puzzle.py --generate 1 --json

# Analyze a position from FEN
python3 chess_puzzle.py --fen "k7/pp6/6R1/2K5/8/8/8/8 w"

# Find the forced mate for a position
python3 chess_puzzle.py --solve "6pk/6pp/5N2/8/3Q4/8/8/4K3 w"

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
  "puzzle_id": "M2-6364",
  "mate_depth": 2,
  "fen": "6pk/6pp/5N2/8/3Q4/8/8/4K3 w",
  "turn": "w",
  "generation_time_s": 0.02,
  "piece_count": 7,
  "verified_mate_half_moves": 4,
  "verified_mate_full_moves": 2,
  "mate_in_1_solutions": 0
}
```

## How It Works

### Puzzle Generation

1. **Mate-in-1**: Randomly places a black king in a corner, adds restricting pawns, a white king at safe distance, and a queen or rook. Verifies the position has exactly one or more mate-in-1 solutions.

2. **Mate-in-2**: Uses curated tactical patterns (smothered mate, Arabian mate, back-rank mate) that are pre-verified to be mate-in-2 but NOT mate-in-1.

3. **Mate-in-3**: Extends patterns with additional pieces for deeper forced mates.

### Search Engine

The mate search uses a minimax algorithm with:
- **Alpha-beta-style pruning**: checking moves are searched first for the attacker
- **Node limit**: aborts after 20,000 nodes to prevent infinite search
- **Move ordering**: checks first, non-checks second for better pruning
- **Defender optimization**: early exit when any escape is found

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

## License

MIT