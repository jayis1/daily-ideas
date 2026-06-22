#!/usr/bin/env python3
"""Bug hunt test script for Terminal Stock Exchange."""

import sys
sys.path.insert(0, '/root/daily-ideas/2026-06-20-terminal-stock-exchange')

from exchange import *
import os

bugs_found = []

def report_bug(bug_id, description):
    bugs_found.append((bug_id, description))
    print(f"BUG {bug_id}: {description}")

def test_bug_1():
    """sell with negative shares should raise ValueError"""
    ex = StockExchange(num_companies=5, seed=42, starting_cash=100000)
    ticker = list(ex.companies.keys())[0]
    ex.buy(ticker, 10)
    try:
        ex.sell(ticker, -1)
        report_bug(1, "sell with negative shares did not raise ValueError")
    except ValueError:
        print("OK: sell with negative shares raises ValueError")

def test_bug_2():
    """sell with 0 shares should raise ValueError"""
    ex = StockExchange(num_companies=5, seed=42, starting_cash=100000)
    ticker = list(ex.companies.keys())[0]
    ex.buy(ticker, 10)
    try:
        ex.sell(ticker, 0)
        report_bug(2, "sell with 0 shares did not raise ValueError")
    except ValueError:
        print("OK: sell with 0 shares raises ValueError")

def test_bug_3():
    """prev_close = 0 in _recalculate_index should not crash"""
    ex = StockExchange(num_companies=3, seed=10)
    for c in ex.companies.values():
        c.prev_close = 0
    try:
        ex._recalculate_index()
        print(f"OK: Index with zero prev_close: {ex.index_value}")
    except Exception as e:
        report_bug(3, f"_recalculate_index crashes with zero prev_close: {e}")

def test_bug_4():
    """News with 1 company (partner selection)"""
    ex = StockExchange(num_companies=1, seed=5)
    ticker = list(ex.companies.keys())[0]
    ex._generate_news(ex.companies[ticker])
    print(f"OK: News with 1 company: {ex.news[-1].headline[:50]}")

def test_bug_5():
    """Save/load watchlist"""
    ex = StockExchange(num_companies=3, seed=20)
    ticker = list(ex.companies.keys())[0]
    ex.toggle_watchlist(ticker)
    ex.save()
    loaded = StockExchange.load()
    if ticker in loaded.watchlist:
        print(f"OK: Watchlist preserved: {loaded.watchlist}")
    else:
        report_bug(5, f"Watchlist not preserved after save/load: expected [{ticker}], got {loaded.watchlist}")

def test_bug_6():
    """Save/load positions"""
    ex = StockExchange(num_companies=3, seed=30)
    ticker = list(ex.companies.keys())[0]
    ex.buy(ticker, 15)
    ex.save()
    loaded = StockExchange.load()
    if loaded.positions[ticker].shares == 15:
        print(f"OK: Position shares preserved: {loaded.positions[ticker].shares}")
    else:
        report_bug(6, f"Position shares not preserved: expected 15, got {loaded.positions[ticker].shares}")

def test_bug_7():
    """_process_orders is dead code - all orders are FILLED"""
    ex = StockExchange(num_companies=3, seed=40)
    print(f"Note: _process_orders only processes PENDING orders, but buy/sell creates FILLED orders")

def test_bug_8():
    """Index after save/load then step"""
    ex = StockExchange(num_companies=3, seed=50)
    for _ in range(100):
        ex.step()
    idx_before = ex.index_value
    ex.save()
    loaded = StockExchange.load()
    loaded.step()
    print(f"OK: Index before save: {idx_before:.2f}, after load+step: {loaded.index_value:.2f}")

def test_bug_9():
    """52w high/low should match history"""
    ex = StockExchange(num_companies=5, seed=80)
    for ticker, c in ex.companies.items():
        if c.history:
            actual_high = max(h[1] for h in c.history)
            actual_low = min(h[2] for h in c.history)
            diff_h = abs(c.high_52w - actual_high)
            diff_l = abs(c.low_52w - actual_low)
            if diff_h > 0.02 or diff_l > 0.02:
                report_bug(9, f"{ticker}: 52w high diff={diff_h:.4f}, low diff={diff_l:.4f}")
            else:
                print(f"OK: {ticker} 52w high/low match history (diffs: {diff_h:.4f}, {diff_l:.4f})")

def test_bug_10():
    """Market phase at exact thresholds"""
    ex = StockExchange(num_companies=3, seed=90)
    ex.market_sentiment = 0.15  # exactly at BULL_THRESHOLD
    phase = ex.get_market_phase()
    print(f"Phase at exactly 0.15: {phase}")
    
    ex.market_sentiment = -0.15  # exactly at BEAR_THRESHOLD
    phase = ex.get_market_phase()
    print(f"Phase at exactly -0.15: {phase}")

def test_bug_11():
    """Save preserves sentiment"""
    ex = StockExchange(num_companies=3, seed=100)
    ex.market_sentiment = 0.5
    ex.save()
    loaded = StockExchange.load()
    if loaded.market_sentiment == 0.5:
        print(f"OK: Sentiment preserved: {loaded.market_sentiment}")
    else:
        report_bug(11, f"Sentiment not preserved: expected 0.5, got {loaded.market_sentiment}")

def test_bug_12():
    """Index doesn't cause runaway growth"""
    ex = StockExchange(num_companies=10, seed=55)
    for i in range(5000):
        ex.step()
    print(f"Index after 5000 steps: {ex.index_value:.2f}")
    if ex.index_value <= 0:
        report_bug(12, f"Index went to zero or negative: {ex.index_value}")

def test_bug_13():
    """0 companies doesn't crash"""
    ex = StockExchange(num_companies=0, seed=1)
    for _ in range(100):
        ex.step()
    print(f"OK: 0-company exchange works, tick={ex.tick}, index={ex.index_value}")

def test_bug_14():
    """sell() - negative shares doesn't validate properly"""
    ex = StockExchange(num_companies=5, seed=42)
    ticker = list(ex.companies.keys())[0]
    ex.buy(ticker, 10)
    # The sell() method: if shares > pos.shares, shares = pos.shares
    # If shares <= 0 after that, raises ValueError
    # But what about shares < 0? It would pass the first check (shares > pos.shares is False for negative)
    # Then shares would be negative, and "if shares <= 0" catches it. OK.
    try:
        ex.sell(ticker, -5)
        report_bug(14, "sell with negative shares did not raise ValueError")
    except ValueError:
        print("OK: sell with negative shares raises ValueError")

def test_bug_15():
    """RSI computation correctness"""
    ex = StockExchange(num_companies=3, seed=42)
    ticker = list(ex.companies.keys())[0]
    # Run enough steps to accumulate history
    for _ in range(50):
        ex.step()
    rsi = ex.compute_rsi(ticker)
    print(f"RSI for {ticker}: {rsi}")
    if rsi is not None and (rsi < 0 or rsi > 100):
        report_bug(15, f"RSI out of range: {rsi}")

def test_bug_16():
    """SMA computation correctness"""
    ex = StockExchange(num_companies=3, seed=42)
    ticker = list(ex.companies.keys())[0]
    for _ in range(50):
        ex.step()
    sma = ex.compute_sma(ticker, period=10)
    print(f"SMA for {ticker}: len={len(sma)}, first={sma[0]:.2f}" if sma else "SMA empty")
    if sma:
        for v in sma:
            if v <= 0:
                report_bug(16, f"SMA value is non-positive: {v}")
                break

def test_bug_17():
    """Sector performance doesn't crash with zero companies in a sector"""
    ex = StockExchange(num_companies=3, seed=42)
    sectors = ex.sector_performance()
    print(f"OK: Sector performance works: {sectors}")

def test_bug_18():
    """Day cycling test - verify volume resets, candle records"""
    ex = StockExchange(num_companies=3, seed=42)
    initial_history_len = len(list(ex.companies.values())[0].history)
    for _ in range(ex.ticks_per_day + 5):
        ex.step()
    final_history_len = len(list(ex.companies.values())[0].history)
    print(f"History grew from {initial_history_len} to {final_history_len} entries")
    if final_history_len <= initial_history_len:
        report_bug(18, f"History did not grow after a full trading day")

def test_bug_19():
    """Check if loaded exchange has proper ticks_per_day"""
    ex = StockExchange(num_companies=3, seed=42)
    ex.save()
    loaded = StockExchange.load()
    print(f"Loaded ticks_per_day: {loaded.ticks_per_day} (should be 78)")
    # Check market_phase is recalculated
    print(f"Loaded market_phase: {loaded.market_phase}")

def test_bug_20():
    """Check that fmt_change handles zero previous close"""
    chg, pct = fmt_change(50.0, 0.0)
    print(f"fmt_change(50, 0): chg={chg}, pct={pct}")

def test_bug_21():
    """Check sell with unknown ticker"""
    ex = StockExchange(num_companies=3, seed=42)
    try:
        ex.sell("ZZZZ", 10)
        report_bug(21, "sell with unknown ticker did not raise")
    except ValueError:
        print("OK: sell with unknown ticker raises ValueError")

def test_bug_22():
    """Check that portfolio_value handles missing companies in positions"""
    ex = StockExchange(num_companies=3, seed=42)
    ticker = list(ex.companies.keys())[0]
    ex.buy(ticker, 10)
    # Manually add a position for a non-existent company
    ex.positions["ZZZZ"] = Position(ticker="ZZZZ", shares=5, avg_cost=50.0)
    val = ex.portfolio_value()
    print(f"Portfolio value with missing company position: {val}")

def test_bug_23():
    """Verify that after _end_trading_day, volume resets properly"""
    ex = StockExchange(num_companies=3, seed=42)
    # Run exactly one day
    for _ in range(ex.ticks_per_day):
        ex.step()
    # After one full day, _end_trading_day is called, then _start_trading_day
    # Volume should have been reset to 0 (or close to 0 from a couple ticks)
    for ticker, c in ex.companies.items():
        # After _start_trading_day, volume resets to 0, then a few steps add volume
        print(f"  {ticker}: volume={c.volume}")

def test_bug_24():
    """Verify that after save/load, exchange.step() works correctly"""
    ex = StockExchange(num_companies=3, seed=42)
    for _ in range(50):
        ex.step()
    ex.save()
    loaded = StockExchange.load()
    # Step should work
    for _ in range(50):
        loaded.step()
    print(f"OK: Step after save/load works. tick={loaded.tick}, day={loaded.day}")

def test_bug_25():
    """Check if market_sentiment is bounded after many steps"""
    ex = StockExchange(num_companies=10, seed=99)
    for _ in range(10000):
        ex.step()
    if -1.0 <= ex.market_sentiment <= 1.0:
        print(f"OK: Sentiment bounded: {ex.market_sentiment:.4f}")
    else:
        report_bug(25, f"Sentiment out of bounds: {ex.market_sentiment}")

# Run all tests
test_bug_1()
test_bug_2()
test_bug_3()
test_bug_4()
test_bug_5()
test_bug_6()
test_bug_7()
test_bug_8()
test_bug_9()
test_bug_10()
test_bug_11()
test_bug_12()
test_bug_13()
test_bug_14()
test_bug_15()
test_bug_16()
test_bug_17()
test_bug_18()
test_bug_19()
test_bug_20()
test_bug_21()
test_bug_22()
test_bug_23()
test_bug_24()
test_bug_25()

# Cleanup
save_path = os.path.expanduser("~/.terminal-stock-exchange-save.json")
if os.path.exists(save_path):
    os.remove(save_path)

print(f"\n=== BUGS FOUND: {len(bugs_found)} ===")
for bug_id, desc in bugs_found:
    print(f"  BUG #{bug_id}: {desc}")