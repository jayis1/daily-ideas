#!/usr/bin/env python3
"""
Non-interactive demo of the slot machine that runs a series of spins
and prints results to stdout. Useful for testing without a terminal.

Usage:
    python3 demo.py                  # Default: 20 spins, seed=42
    python3 demo.py --spins 50       # Run 50 spins
    python3 demo.py --credits 500   # Start with 500 credits
    python3 demo.py --bet 5          # Use bet of 5 per spin
    python3 demo.py --seed 12345     # Use specific random seed
    python3 demo.py --version        # Show version info
    python3 demo.py --help           # Show help message
"""

import random
import argparse
import sys

import slots

__version__ = "1.1.0"


def run_demo(num_spins=20, starting_credits=100, bet=1, seed=42):
    """Run a non-interactive demo of the slot machine.

    Args:
        num_spins: Number of spins to simulate.
        starting_credits: Starting credit balance.
        bet: Bet amount per spin.
        seed: Random seed for reproducibility.
    """
    random.seed(seed)

    print("🎰 LUCKY TERMINAL SLOTS — Demo Mode 🎰")
    print("=" * 55)
    print()
    print(f"  Starting credits: {starting_credits}")
    print(f"  Bet per spin:     {bet}")
    print(f"  Number of spins:  {num_spins}")
    print(f"  Random seed:      {seed}")
    print()

    credits = starting_credits
    total_won = 0
    total_bet = 0
    biggest_win = 0
    win_count = 0
    loss_count = 0
    current_streak = 0
    best_streak = 0
    worst_streak = 0
    current_loss_streak = 0

    # Track symbol frequency for stats
    symbol_counts = {name: 0 for name in slots.SYMBOL_NAMES}

    # Check if player can go bankrupt mid-session
    went_bankrupt = False
    bankrupt_spin = 0

    print(f"  {'Spin':>4}  {'Reel 1':>8}  {'Reel 2':>8}  {'Reel 3':>8}  {'Result':<30}  {'Credits':>8}")
    print("  " + "-" * 75)

    completed_spins = 0

    for spin_num in range(1, num_spins + 1):
        # Check if player can afford to spin
        if credits < bet:
            went_bankrupt = True
            bankrupt_spin = spin_num
            print(f"\n  ⛔ BANKRUPT at spin {spin_num}! Not enough credits to continue.")
            print(f"     Final credits: {credits}")
            break

        # Deduct bet
        credits -= bet
        total_bet += bet

        # Spin each reel
        results = [random.choice(slots.WEIGHTED_REEL) for _ in range(slots.NUM_REELS)]
        emojis = [slots.SYMBOL_EMOJIS[slots.SYMBOL_NAMES.index(r)] for r in results]

        # Track symbol frequency
        for r in results:
            symbol_counts[r] = symbol_counts.get(r, 0) + 1

        # Check for wins (3-of-a-kind on payline)
        win = 0
        win_desc = ""
        if results[0] == results[1] == results[2]:
            mult = slots.SYMBOL_PAYOUTS[results[0]]
            win = mult * bet
            win_desc = f"3× {emojis[0]} → ×{mult} ({mult * bet})"
        # Check 2-of-a-kind
        elif results[0] == results[1] or results[1] == results[2]:
            sym = results[1]
            small_mult = max(1, slots.SYMBOL_PAYOUTS[sym] // 5)
            win = small_mult * bet
            emoji_idx = slots.SYMBOL_NAMES.index(sym)
            win_desc = f"2× {slots.SYMBOL_EMOJIS[emoji_idx]} → ×{small_mult} ({small_mult * bet})"

        credits += win
        total_won += win

        if win > 0:
            win_count += 1
            if win > biggest_win:
                biggest_win = win
            current_streak += 1
            current_loss_streak = 0
            if current_streak > best_streak:
                best_streak = current_streak
            result_str = f"✨ WIN {win_desc}"
        else:
            loss_count += 1
            current_loss_streak += 1
            current_streak = 0
            if current_loss_streak > worst_streak:
                worst_streak = current_loss_streak
            result_str = "—"

        completed_spins = spin_num
        print(f"  {spin_num:>4}  {emojis[0]:>8}  {emojis[1]:>8}  {emojis[2]:>8}  {result_str:<30}  {credits:>8}")

    print()
    print("=" * 55)
    print("  SESSION SUMMARY")
    print("=" * 55)
    print(f"  Final credits:     {credits}")
    print(f"  Total spins:       {completed_spins}")
    print(f"  Total bet:         {total_bet}")
    print(f"  Total won:         {total_won}")
    payback = (total_won / total_bet * 100) if total_bet > 0 else 0
    print(f"  Payback rate:      {payback:.1f}%")
    net = credits - starting_credits
    print(f"  Net profit/loss:   {net:+d}")
    print(f"  Wins:              {win_count}  |  Losses: {loss_count}")
    print(f"  Biggest win:       {biggest_win}")
    print(f"  Best win streak:   {best_streak}")
    print(f"  Worst loss streak: {worst_streak}")
    if went_bankrupt:
        print(f"  ⚠️  Went bankrupt at spin {bankrupt_spin}")
    print()
    print("  Symbol frequency:")
    for name in slots.SYMBOL_NAMES:
        count = symbol_counts.get(name, 0)
        pct = (count / (completed_spins * 3) * 100) if completed_spins > 0 else 0
        emoji_idx = slots.SYMBOL_NAMES.index(name)
        emoji = slots.SYMBOL_EMOJIS[emoji_idx]
        bar = "█" * min(30, int(pct / 2))
        print(f"    {emoji} {name:<8} {count:>4} ({pct:>5.1f}%) {bar}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="🎰 Terminal Slot Machine — Non-interactive demo mode",
        epilog="Example: python3 demo.py --spins 50 --credits 500 --bet 5"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--spins", type=int, default=20,
                        help="Number of spins to simulate (default: 20)")
    parser.add_argument("--credits", type=int, default=100,
                        help="Starting credits (default: 100)")
    parser.add_argument("--bet", type=int, default=1,
                        help="Bet amount per spin (default: 1)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")

    args = parser.parse_args()

    # Validate inputs
    if args.spins < 1:
        print("Error: --spins must be at least 1", file=sys.stderr)
        sys.exit(1)
    if args.credits < 1:
        print("Error: --credits must be at least 1", file=sys.stderr)
        sys.exit(1)
    if args.bet < 1:
        print("Error: --bet must be at least 1", file=sys.stderr)
        sys.exit(1)

    run_demo(
        num_spins=args.spins,
        starting_credits=args.credits,
        bet=args.bet,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()