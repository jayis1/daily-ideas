# ⣿ Terminal Stock Exchange

A fully interactive terminal-based stock market simulator with procedurally generated companies, realistic price dynamics (Geometric Brownian Motion-inspired), portfolio management, ASCII candlestick charts, breaking news events, dividend payouts, and save/load persistence.

## Features

- **Procedural Companies** — 20 unique companies generated each game with names, tickers, industries, beta coefficients, dividend yields, and 30-day price history
- **Realistic Price Dynamics** — GBM-inspired simulation with drift, volatility (beta-weighted), sentiment decay, and market-wide correlation
- **Buy & Sell** — Purchase and sell shares with automatic cost-basis tracking; positions show unrealized P&L
- **ASCII Candlestick Charts** — View OHLC candlestick charts with volume bars for any stock
- **Breaking News** — Random market events (breakthroughs, scandals, lawsuits, upgrades) that shift sentiment and move prices
- **Dividend Payments** — Quarterly dividends paid automatically for dividend-yielding stocks
- **Portfolio Tracking** — Real-time portfolio value, cash balance, P&L (absolute and percentage), dividend income
- **Day/Night Cycle** — Trading days with 78 ticks (~5-minute intervals simulating a 6.5-hour session), overnight gaps, and daily candle recording
- **Save/Load** — Game state persisted to `~/.terminal-stock-exchange-save.json`; resume where you left off
- **5 Views** — Market board, Portfolio, Chart, News feed, Trade log
- **Sorting** — Sort stocks by ticker, change %, volume, or price
- **Speed Control** — 1x to 20x simulation speed, or pause

## How to Install

No external dependencies — uses only the Python standard library (including `curses`).

```bash
# Clone the repo
cd ~/daily-ideas/2026-06-20-terminal-stock-exchange

# That's it! Just run with Python 3.10+
```

## How to Run

```bash
# Start the exchange (loads save if exists)
python3 exchange.py

# Start fresh with new companies
python3 exchange.py --new

# Custom starting cash
python3 exchange.py --new --cash 500000

# Set number of companies
python3 exchange.py --new --companies 30

# Set random seed for reproducibility
python3 exchange.py --new --seed 12345
```

## Controls

| Key | Action |
|-----|--------|
| `1` | Market board view |
| `2` | Portfolio view |
| `3` | Candlestick chart view |
| `4` | News feed |
| `5` | Trade log |
| `↑` / `↓` | Select stock |
| `Enter` | View chart for selected stock |
| `b` | Buy (type ticker, Enter to confirm — buys 10 shares) |
| `s` | Sell (type ticker, Enter to confirm — sells 10 shares) |
| `S` | Cycle sort mode (ticker → change → volume → price) |
| `D` | Toggle sort ascending/descending |
| `Space` | Pause/resume simulation |
| `+` / `-` | Increase/decrease simulation speed (1x–20x) |
| `q` | Quit and save |

## Usage Examples

### Starting a New Game
```bash
python3 exchange.py --new --cash 250000 --companies 15
```

### Resuming a Saved Game
```bash
python3 exchange.py
```

### Running Tests
```bash
python3 -m pytest test_exchange.py -v
```

## How It Works

### Price Simulation
Each tick applies a GBM-inspired update:
```
ΔP/P = drift + sentiment_drift + market_factor + N(0, σ·β)
```
- **Drift**: Small upward bias (0.002% per tick)
- **Sentiment**: Company-specific momentum that decays by 2% per tick
- **Market factor**: Correlated Gaussian noise across all stocks
- **Volatility**: Scaled by each company's beta coefficient

### News Events
With ~0.3% probability per tick, a random company generates a news event with an impact factor ranging from -15% to +15%. This shifts the company's sentiment, causing gradual price drift over the next few ticks.

### Dividends
Companies with a dividend yield > 0% pay quarterly dividends (every 20 trading days). Dividends are calculated as:
```
dividend = shares × price × (yield / 100) / 4
```

### Day Cycling
Each trading day consists of 78 ticks. At day end:
- Daily candles (OHLC + volume) are recorded
- Dividends are paid (if applicable)
- An overnight gap is applied at market open

## Project Structure

```
2026-06-20-terminal-stock-exchange/
├── exchange.py          # Main application (simulation engine + curses UI)
├── test_exchange.py     # 48 pytest tests
└── README.md            # This file
```

## License

MIT