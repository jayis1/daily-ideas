#!/usr/bin/env python3
"""
Non-interactive demo of the slot machine that runs a series of spins
and prints results to stdout. Useful for testing without a terminal.
"""

import random
import slots

def run_demo(num_spins=20, seed=42):
    random.seed(seed)
    print("🎰 LUCKY TERMINAL SLOTS — Demo Mode 🎰")
    print("=" * 50)
    print()

    credits = 100
    bet = 1
    total_won = 0
    total_bet = 0

    print(f"Starting credits: {credits}")
    print(f"Bet per spin: {bet}")
    print()

    for spin_num in range(1, num_spins + 1):
        # Deduct bet
        credits -= bet
        total_bet += bet

        # Spin each reel
        results = [random.choice(slots.WEIGHTED_REEL) for _ in range(slots.NUM_REELS)]
        emojis = [slots.SYMBOL_EMOJIS[slots.SYMBOL_NAMES.index(r)] for r in results]

        # Check for wins (3-of-a-kind on payline)
        win = 0
        win_desc = ""
        if results[0] == results[1] == results[2]:
            mult = slots.SYMBOL_PAYOUTS[results[0]]
            win = mult * bet
            win_desc = f"3× {emojis[0]} → ×{mult}"

        # Check 2-of-a-kind
        if win == 0 and (results[0] == results[1] or results[1] == results[2]):
            sym = results[1]
            small_mult = max(1, slots.SYMBOL_PAYOUTS[sym] // 5)
            win = small_mult * bet
            win_desc = f"2× {slots.SYMBOL_EMOJIS[slots.SYMBOL_NAMES.index(sym)]} → ×{small_mult}"

        credits += win
        total_won += win

        result_str = " ".join(emojis)
        spin_line = f"Spin {spin_num:>3}: {result_str}"
        if win > 0:
            spin_line += f"  ✨ WIN {win_desc} (+{win})"
        else:
            spin_line += f"  —"

        print(spin_line)

    print()
    print("=" * 50)
    print(f"Final credits: {credits}")
    print(f"Total bet:     {total_bet}")
    print(f"Total won:     {total_won}")
    payback = (total_won / total_bet * 100) if total_bet > 0 else 0
    print(f"Payback rate: {payback:.1f}%")
    print()

if __name__ == "__main__":
    run_demo()