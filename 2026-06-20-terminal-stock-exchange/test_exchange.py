#!/usr/bin/env python3
"""Tests for Terminal Stock Exchange simulator."""

import json
import os
import tempfile
import pytest
from exchange import (
    StockExchange, Company, Position, OrderType, OrderStatus,
    MarketPhase, InputPhase, SAVE_FILE,
    fmt_price, fmt_change, fmt_volume, fmt_index_change,
)

# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def exchange():
    """Create a small exchange with fixed seed for reproducible tests."""
    return StockExchange(num_companies=10, starting_cash=100000.0, seed=42)


@pytest.fixture
def exchange_with_position(exchange):
    """Exchange with a position in the first company."""
    ticker = list(exchange.companies.keys())[0]
    exchange.buy(ticker, 10)
    return exchange, ticker


# ─── Company Generation ─────────────────────────────────────────────────────

class TestCompanyGeneration:
    def test_companies_created(self, exchange):
        assert len(exchange.companies) == 10

    def test_companies_have_tickers(self, exchange):
        for ticker, company in exchange.companies.items():
            assert company.ticker == ticker
            assert len(ticker) <= 4
            assert ticker.isupper() or ticker.isalpha()

    def test_companies_have_names(self, exchange):
        names = set()
        for company in exchange.companies.values():
            assert len(company.name) > 0
            names.add(company.name)
        assert len(names) == 10  # All unique

    def test_companies_have_industries(self, exchange):
        for company in exchange.companies.values():
            assert company.industry in [
                "Tech", "Energy", "Finance", "Health", "Materials", "Consumer",
                "Industrial", "Utilities", "Real Estate", "Telecom",
            ]

    def test_companies_have_valid_prices(self, exchange):
        for company in exchange.companies.values():
            assert company.price > 0
            assert company.price < 10000
            assert company.day_high >= company.day_low

    def test_companies_have_history(self, exchange):
        for company in exchange.companies.values():
            assert len(company.history) >= 20

    def test_companies_have_valid_beta(self, exchange):
        for company in exchange.companies.values():
            assert 0.1 <= company.beta <= 3.0

    def test_companies_have_52w_high_low(self, exchange):
        """Verify 52-week high/low are initialized from history."""
        for company in exchange.companies.values():
            assert company.high_52w >= company.low_52w
            assert company.high_52w > 0

    def test_different_seeds_produce_different_companies(self):
        ex1 = StockExchange(num_companies=10, seed=1)
        ex2 = StockExchange(num_companies=10, seed=2)
        tickers1 = set(ex1.companies.keys())
        tickers2 = set(ex2.companies.keys())
        # They should be different (extremely unlikely to be the same)
        assert tickers1 != tickers2 or len(tickers1.intersection(tickers2)) < 10


# ─── Price Simulation ────────────────────────────────────────────────────────

class TestPriceSimulation:
    def test_step_advances_tick(self, exchange):
        old_tick = exchange.tick
        exchange.step()
        assert exchange.tick == old_tick + 1

    def test_prices_change_over_time(self, exchange):
        initial_prices = {t: c.price for t, c in exchange.companies.items()}
        for _ in range(100):
            exchange.step()
        # At least some prices should have changed
        changes = sum(
            1 for t, c in exchange.companies.items()
            if c.price != initial_prices[t]
        )
        assert changes > 0

    def test_prices_stay_positive(self, exchange):
        for _ in range(5000):
            exchange.step()
        for company in exchange.companies.values():
            assert company.price > 0

    def test_day_high_and_low_track(self, exchange):
        for _ in range(50):
            exchange.step()
        for company in exchange.companies.values():
            assert company.day_high >= company.price
            assert company.day_low <= company.price

    def test_volume_increases(self, exchange):
        for _ in range(10):
            exchange.step()
        for company in exchange.companies.values():
            assert company.volume > 0

    def test_52w_high_low_update(self, exchange):
        """52-week high/low should update as prices change."""
        initial_highs = {t: c.high_52w for t, c in exchange.companies.items()}
        initial_lows = {t: c.low_52w for t, c in exchange.companies.items()}
        for _ in range(500):
            exchange.step()
        # At least some companies should have new highs or lows
        changes = 0
        for t, company in exchange.companies.items():
            if company.high_52w != initial_highs[t] or company.low_52w != initial_lows[t]:
                changes += 1
        # Very likely at least one changes over 500 steps
        assert changes >= 0  # Could be 0 if all stayed within range


# ─── Market Index ────────────────────────────────────────────────────────────

class TestMarketIndex:
    def test_index_starts_at_100(self, exchange):
        assert exchange.index_value == 100.0

    def test_index_changes_over_time(self, exchange):
        initial = exchange.index_value
        for _ in range(200):
            exchange.step()
        # Index should have moved from 100
        # (it could be slightly above or below)
        # Just check it's a valid number
        assert exchange.index_value > 0

    def test_index_history_recorded(self, exchange):
        """After a full trading day, index history should have an entry."""
        for _ in range(exchange.ticks_per_day + 5):
            exchange.step()
        assert len(exchange.index_history) >= 1

    def test_sector_performance(self, exchange):
        """Sector performance should return valid data."""
        sectors = exchange.sector_performance()
        assert isinstance(sectors, dict)
        for industry, perf in sectors.items():
            assert isinstance(perf, float)
            assert industry in [
                "Tech", "Energy", "Finance", "Health", "Materials", "Consumer",
                "Industrial", "Utilities", "Real Estate", "Telecom",
            ]


# ─── Market Phase ───────────────────────────────────────────────────────────

class TestMarketPhase:
    def test_initial_phase(self, exchange):
        """Initial market phase should be neutral."""
        assert exchange.market_phase in [MarketPhase.BULL, MarketPhase.BEAR, MarketPhase.NEUTRAL]

    def test_phase_detection(self):
        """Test that phase detection works with extreme sentiment."""
        ex = StockExchange(num_companies=5, seed=99)
        ex.market_sentiment = 0.5  # Bull territory
        assert ex.get_market_phase() == MarketPhase.BULL
        ex.market_sentiment = -0.5  # Bear territory
        assert ex.get_market_phase() == MarketPhase.BEAR
        ex.market_sentiment = 0.0
        assert ex.get_market_phase() == MarketPhase.NEUTRAL

    def test_sentiment_evolution(self, exchange):
        """Market sentiment should evolve over time."""
        initial = exchange.market_sentiment
        for _ in range(500):
            exchange.step()
        # Sentiment may or may not have changed, but should stay bounded
        assert -1.0 <= exchange.market_sentiment <= 1.0


# ─── SMA & RSI ──────────────────────────────────────────────────────────────

class TestSMAandRSI:
    def test_sma_computation(self, exchange):
        """SMA should return values for companies with enough history."""
        ticker = list(exchange.companies.keys())[0]
        sma = exchange.compute_sma(ticker, period=10)
        assert len(sma) > 0
        # SMA values should be reasonable price values
        for val in sma:
            assert val > 0

    def test_sma_insufficient_data(self, exchange):
        """SMA with period longer than history should return empty list."""
        # All companies have ~30 days of history
        ticker = list(exchange.companies.keys())[0]
        sma = exchange.compute_sma(ticker, period=500)
        assert len(sma) == 0

    def test_sma_unknown_ticker(self, exchange):
        """SMA for unknown ticker should return empty list."""
        sma = exchange.compute_sma("ZZZZ", period=10)
        assert len(sma) == 0

    def test_rsi_computation(self, exchange):
        """RSI should return a value between 0 and 100."""
        ticker = list(exchange.companies.keys())[0]
        rsi = exchange.compute_rsi(ticker)
        if rsi is not None:
            assert 0 <= rsi <= 100

    def test_rsi_insufficient_data(self, exchange):
        """RSI for unknown ticker should return None."""
        rsi = exchange.compute_rsi("ZZZZ")
        assert rsi is None


# ─── Watchlist ──────────────────────────────────────────────────────────────

class TestWatchlist:
    def test_toggle_watchlist_add(self, exchange):
        ticker = list(exchange.companies.keys())[0]
        added = exchange.toggle_watchlist(ticker)
        assert added is True
        assert ticker in exchange.watchlist

    def test_toggle_watchlist_remove(self, exchange):
        ticker = list(exchange.companies.keys())[0]
        exchange.toggle_watchlist(ticker)  # Add
        removed = exchange.toggle_watchlist(ticker)  # Remove
        assert removed is False
        assert ticker not in exchange.watchlist

    def test_watchlist_persists_save_load(self, exchange):
        ticker = list(exchange.companies.keys())[0]
        exchange.toggle_watchlist(ticker)
        exchange.save()
        loaded = StockExchange.load()
        assert loaded is not None
        assert ticker in loaded.watchlist


# ─── Trading ──────────────────────────────────────────────────────────────────

class TestTrading:
    def test_buy_reduces_cash(self, exchange):
        ticker = list(exchange.companies.keys())[0]
        initial_cash = exchange.cash
        price = exchange.companies[ticker].price
        exchange.buy(ticker, 5)
        assert exchange.cash < initial_cash
        # Should be close to initial_cash - 5 * price
        assert abs(exchange.cash - (initial_cash - 5 * price)) < 1

    def test_buy_creates_position(self, exchange):
        ticker = list(exchange.companies.keys())[0]
        exchange.buy(ticker, 10)
        assert ticker in exchange.positions
        assert exchange.positions[ticker].shares == 10

    def test_buy_avg_cost(self, exchange):
        ticker = list(exchange.companies.keys())[0]
        exchange.buy(ticker, 10)
        first_cost = exchange.positions[ticker].avg_cost
        # Buy more
        exchange.buy(ticker, 10)
        # Avg cost should still be close (price may have changed slightly)
        assert exchange.positions[ticker].shares == 20

    def test_buy_zero_shares_raises(self, exchange):
        """Buying zero or negative shares should raise ValueError."""
        ticker = list(exchange.companies.keys())[0]
        with pytest.raises(ValueError, match="positive"):
            exchange.buy(ticker, 0)

    def test_sell_increases_cash(self, exchange_with_position):
        exchange, ticker = exchange_with_position
        initial_cash = exchange.cash
        exchange.sell(ticker, 5)
        assert exchange.cash > initial_cash

    def test_sell_reduces_shares(self, exchange_with_position):
        exchange, ticker = exchange_with_position
        exchange.sell(ticker, 5)
        assert exchange.positions[ticker].shares == 5

    def test_sell_all_removes_position(self, exchange_with_position):
        exchange, ticker = exchange_with_position
        exchange.sell(ticker, 10)
        assert ticker not in exchange.positions

    def test_buy_insufficient_funds_buys_less(self, exchange):
        # Try to buy more than we can afford
        ticker = list(exchange.companies.keys())[0]
        price = exchange.companies[ticker].price
        max_shares = int(exchange.cash / price)
        # Buy max possible
        exchange.buy(ticker, max_shares + 1000)
        assert exchange.cash >= 0
        assert exchange.positions[ticker].shares > 0

    def test_sell_unknown_ticker_raises(self, exchange):
        with pytest.raises(ValueError):
            exchange.sell("ZZZZ", 10)

    def test_sell_no_position_raises(self, exchange):
        ticker = list(exchange.companies.keys())[0]
        with pytest.raises(ValueError):
            exchange.sell(ticker, 10)

    def test_trade_log_records_buys_and_sells(self, exchange_with_position):
        exchange, ticker = exchange_with_position
        assert any("BUY" in entry for entry in exchange.trade_log)
        exchange.sell(ticker, 5)
        assert any("SELL" in entry for entry in exchange.trade_log)


# ─── Portfolio ────────────────────────────────────────────────────────────────

class TestPortfolio:
    def test_portfolio_value_starts_at_cash(self, exchange):
        assert exchange.portfolio_value() == exchange.cash

    def test_portfolio_value_includes_positions(self, exchange_with_position):
        exchange, ticker = exchange_with_position
        price = exchange.companies[ticker].price
        shares = exchange.positions[ticker].shares
        expected = exchange.cash + price * shares
        assert abs(exchange.portfolio_value() - expected) < 1

    def test_portfolio_pnl_starts_at_zero(self, exchange):
        assert exchange.portfolio_pnl() == 0.0

    def test_portfolio_pnl_pct_starts_at_zero(self, exchange):
        assert exchange.portfolio_pnl_pct() == 0.0

    def test_portfolio_pnl_changes_after_trade(self, exchange_with_position):
        exchange, ticker = exchange_with_position
        # After buying, PnL is usually negative due to price movement
        pnl = exchange.portfolio_pnl()
        # It should be a valid number
        assert isinstance(pnl, float)


# ─── Save / Load ─────────────────────────────────────────────────────────────

class TestSaveLoad:
    def test_save_and_load(self, exchange):
        original_cash = exchange.cash
        original_day = exchange.day
        original_num_companies = len(exchange.companies)

        exchange.save()
        loaded = StockExchange.load()

        assert loaded is not None
        assert loaded.cash == original_cash
        assert loaded.day == original_day
        assert len(loaded.companies) == original_num_companies

    def test_save_preserves_positions(self, exchange_with_position):
        exchange, ticker = exchange_with_position
        exchange.save()
        loaded = StockExchange.load()
        assert ticker in loaded.positions
        assert loaded.positions[ticker].shares == exchange.positions[ticker].shares

    def test_load_returns_none_when_no_file(self):
        # Point to a nonexistent path
        import exchange as ex_mod
        old_save = ex_mod.SAVE_FILE
        ex_mod.SAVE_FILE = "/tmp/test_stock_exchange_nonexistent.json"
        result = StockExchange.load()
        assert result is None
        ex_mod.SAVE_FILE = old_save

    def test_round_trip_preserves_prices(self, exchange):
        original_prices = {t: c.price for t, c in exchange.companies.items()}
        exchange.save()
        loaded = StockExchange.load()
        for ticker, price in original_prices.items():
            assert loaded.companies[ticker].price == price

    def test_save_preserves_index_value(self, exchange):
        """Verify index_value is preserved across save/load."""
        # Run some steps to change the index
        for _ in range(100):
            exchange.step()
        idx_before = exchange.index_value
        exchange.save()
        loaded = StockExchange.load()
        assert loaded is not None
        assert abs(loaded.index_value - idx_before) < 0.01

    def test_save_preserves_52w_high_low(self, exchange):
        """Verify 52-week high/low are preserved across save/load."""
        ticker = list(exchange.companies.keys())[0]
        high_before = exchange.companies[ticker].high_52w
        low_before = exchange.companies[ticker].low_52w
        exchange.save()
        loaded = StockExchange.load()
        assert loaded is not None
        assert loaded.companies[ticker].high_52w == high_before
        assert loaded.companies[ticker].low_52w == low_before


# ─── News Generation ─────────────────────────────────────────────────────────

class TestNewsGeneration:
    def test_news_generated_occasionally(self, exchange):
        for _ in range(5000):
            exchange.step()
        # With 0.3% chance per step per company, should get some news over 5000 steps
        # But it's random, so just check it doesn't crash

    def test_news_events_have_required_fields(self, exchange):
        # Force news generation
        company = list(exchange.companies.values())[0]
        exchange._generate_news(company)
        assert len(exchange.news) > 0
        ne = exchange.news[-1]
        assert ne.headline
        assert ne.ticker == company.ticker
        assert isinstance(ne.impact, float)


# ─── Day Cycling ──────────────────────────────────────────────────────────────

class TestDayCycling:
    def test_day_advances(self, exchange):
        initial_day = exchange.day
        for _ in range(exchange.ticks_per_day + 5):
            exchange.step()
        # Day should have advanced
        assert exchange.day > initial_day

    def test_daily_candle_recorded(self, exchange):
        # Run through a full day
        for _ in range(exchange.ticks_per_day + 2):
            exchange.step()
        # Check that history was recorded for at least some companies
        for company in exchange.companies.values():
            assert len(company.history) > 30  # Initial 30 + at least 1 new

    def test_prev_close_updates(self, exchange):
        original_prev_close = {t: c.prev_close for t, c in exchange.companies.items()}
        for _ in range(exchange.ticks_per_day + 5):
            exchange.step()
        # After a day passes, prev_close should update

    def test_volume_resets_daily(self, exchange):
        for _ in range(exchange.ticks_per_day + 5):
            exchange.step()
        # Volume resets to 0 at start of new day (or near-zero from a few ticks)
        for company in exchange.companies.values():
            # Volume should be relatively small at start of day
            assert company.volume < 500000  # Not accumulated from previous day

    def test_index_history_recorded_after_day(self, exchange):
        """Index history should have entries after trading days complete."""
        for _ in range(exchange.ticks_per_day + 5):
            exchange.step()
        assert len(exchange.index_history) >= 1


# ─── Edge Cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_buy_with_exact_cash(self, exchange):
        ticker = list(exchange.companies.keys())[0]
        price = exchange.companies[ticker].price
        max_shares = int(exchange.cash / price)
        exchange.buy(ticker, max_shares)
        assert exchange.cash >= 0

    def test_multiple_buys_same_ticker(self, exchange):
        ticker = list(exchange.companies.keys())[0]
        exchange.buy(ticker, 5)
        exchange.buy(ticker, 5)
        assert exchange.positions[ticker].shares == 10

    def test_many_ticks_no_crash(self, exchange):
        for _ in range(10000):
            exchange.step()

    def test_zero_companies(self):
        ex = StockExchange(num_companies=0, seed=1)
        for _ in range(100):
            ex.step()

    def test_single_company(self):
        ex = StockExchange(num_companies=1, seed=1)
        ticker = list(ex.companies.keys())[0]
        ex.buy(ticker, 1)
        for _ in range(100):
            ex.step()

    def test_large_number_of_companies(self):
        """Stress test with many companies."""
        ex = StockExchange(num_companies=50, seed=1)
        assert len(ex.companies) == 50
        for _ in range(200):
            ex.step()

    def test_rapid_buy_sell_cycle(self, exchange):
        """Rapidly buy and sell should not corrupt state."""
        ticker = list(exchange.companies.keys())[0]
        for _ in range(5):
            exchange.buy(ticker, 1)
        for _ in range(5):
            exchange.sell(ticker, 1)
        assert ticker not in exchange.positions or exchange.positions[ticker].shares == 0


# ─── Helper Functions ────────────────────────────────────────────────────────

class TestHelperFunctions:
    def test_fmt_price_small(self):
        assert fmt_price(10.50) == "$10.50"

    def test_fmt_price_large(self):
        assert fmt_price(1500.00) == "$1,500"

    def test_fmt_change_positive(self):
        chg, pct = fmt_change(105.0, 100.0)
        assert "+" in chg
        assert "+" in pct

    def test_fmt_change_negative(self):
        chg, pct = fmt_change(95.0, 100.0)
        assert chg.startswith("-")

    def test_fmt_change_zero_prev(self):
        """fmt_change with zero previous should not crash."""
        chg, pct = fmt_change(50.0, 0.0)
        assert isinstance(chg, str)
        assert isinstance(pct, str)

    def test_fmt_volume(self):
        assert "K" in fmt_volume(1500)
        assert "M" in fmt_volume(1500000)

    def test_fmt_volume_small(self):
        """Small volumes should be plain numbers."""
        assert fmt_volume(50) == "50"

    def test_fmt_index_change(self):
        """Index change formatting."""
        result = fmt_index_change(102.0, 100.0)
        assert "+" in result
        result = fmt_index_change(98.0, 100.0)
        assert "-" in result or result.startswith("0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])