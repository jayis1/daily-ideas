# ⣿ Terminal Stock Exchange

A fully interactive terminal-based stock market simulator with procedurally generated companies, realistic price dynamics (Geometric Brownian Motion-inspired), portfolio management, ASCII candlestick charts with SMA overlays, RSI indicators, market index tracking, watchlists, sector analysis, and more.

## Features

### Core Trading
- **Procedural Companies** — 20 unique companies generated each game with names, tickers, industries, beta coefficients, dividend yields, and 30-day price history
- **Buy & Sell** — Two-step trade input: enter ticker, then specify share count (defaults to 10)
- **Portfolio Tracking** — Real-time portfolio value, cash balance, P&L (absolute and percentage), dividend income, cost basis per position

### Market Simulation
- **Realistic Price Dynamics** — GBM-inspired simulation with drift, volatility (beta-weighted), sentiment decay, and market-wide correlation
- **Market Phase Detection** — Automatically detects bull/bear/neutral market phases based on aggregate sentiment, displayed in the header
- **TSE Index** — Market-cap-weighted composite index tracking overall market performance, displayed in the header
- **Breaking News** — Random market events (breakthroughs, scandals, lawsuits, upgrades) that shift sentiment and move prices
- **Dividend Payments** — Quarterly dividends paid automatically for dividend-yielding stocks
- **Day/Night Cycle** — Trading days with 78 ticks, overnight gaps influenced by market phase, and daily candle recording

### Technical Analysis
- **ASCII Candlestick Charts** — OHLC candlestick charts with volume bars for any stock
- **SMA Overlay** — 20-day Simple Moving Average line overlaid on candlestick charts (toggle with `m`)
- **RSI Indicator** — 14-day Relative Strength Index displayed on chart view
- **52-Week High/Low** — Tracked per stock and displayed in the market board

### Views & Navigation
- **7 Views** — Market board, Portfolio, Chart, News feed, Trade log, Watchlist, Sector performance
- **Watchlist** — Mark stocks with `w` to track them on a dedicated watchlist view (view 6)
- **Sector Analysis** — View average performance by industry sector with visual bars (view 7)
- **Sorting** — Sort stocks by ticker, change %, volume, or price (`S` to cycle, `D` to flip order)
- **Speed Control** — 1x to 20x simulation speed, or pause with Space

### Persistence & CLI
- **Save/Load** — Game state (including watchlist, index history) persisted to `~/.terminal-stock-exchange-save.json`
- **--version flag** — Show version (`1.1.0`)
- **--help flag** — Full CLI usage info

## How to Install

No external dependencies — uses only the Python standard library (including `curses`).

```bash
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

# Show version
python3 exchange.py --version

# Show help
python3 exchange.py --help
```

## Controls

| Key | Action |
|-----|--------|
| `1` | Market board view |
| `2` | Portfolio view |
| `3` | Candlestick chart view |
| `4` | News feed |
| `5` | Trade log |
| `6` | Watchlist view |
| `7` | Sector performance view |
| `↑` / `↓` | Select stock / navigate |
| `Enter` | View chart for selected stock |
| `b` | Buy (two-step: ticker → shares) |
| `s` | Sell (two-step: ticker → shares) |
| `w` | Toggle selected stock on watchlist |
| `m` | Toggle SMA overlay on chart |
| `S` | Cycle sort mode (ticker → change → volume → price) |
| `D` | Toggle sort ascending/descending |
| `Space` | Pause/resume simulation |
| `+` / `-` | Increase/decrease simulation speed (1x–20x) |
| `q` | Quit and save |
| `Esc` | Cancel current input |

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
- **Drift**: Small upward bias (0.002% per tick), adjusted by market phase (+0.005% in bull, −0.008% in bear)
- **Sentiment**: Company-specific momentum that decays by 2% per tick
- **Market factor**: Correlated Gaussian noise across all stocks
- **Volatility**: Scaled by each company's beta coefficient

### Market Phase Detection
The aggregate market sentiment evolves with mean-reversion:
- **BULL** (sentiment > +0.15): Higher drift, positive overnight gaps
- **BEAR** (sentiment < −0.15): Lower drift, negative overnight gaps
- **NEUTRAL** (between): Standard dynamics

### TSE Index
A market-cap-weighted composite index starting at 100, tracking the weighted average price change across all stocks.

### News Events
With ~0.3% probability per tick, a random company generates a news event with impact ranging from −15% to +15%. News also shifts aggregate market sentiment slightly.

### Dividends
Companies with dividend yield > 0% pay quarterly dividends (every 20 trading days):
```
dividend = shares × price × (yield / 100) / 4
```

### Technical Indicators
- **SMA (20-day)**: Simple Moving Average shown as yellow dots on the chart
- **RSI (14-day)**: Relative Strength Index shown in the chart header (above 70 = overbought, below 30 = oversold)

### 52-Week High/Low
Tracked per stock, updated in real-time, displayed in the market board columns.

## Project Structure

```
2026-06-20-terminal-stock-exchange/
├── exchange.py          # Main application (simulation engine + curses UI)
├── test_exchange.py     # 74 pytest tests
└── README.md            # This file
```

## New in v1.1.0

- **TSE Index** — Market-cap-weighted composite index shown in the header
- **Market Phase Detection** — Bull/bear/neutral phases affecting price dynamics
- **SMA Overlay** — 20-day Simple Moving Average on candlestick charts (toggle `m`)
- **RSI Indicator** — 14-day RSI displayed on chart view
- **52-Week High/Low** — Tracked per stock, shown in market board
- **Watchlist** — Mark stocks with `w`, view them in view 6
- **Sector Performance** — View 7 shows average change by industry with visual bars
- **Two-Step Trade Input** — Enter ticker first, then share count (ESC to cancel)
- **--version and --help** — Proper CLI flags
- **Validation** — Buy with 0/negative shares raises ValueError
- **74 tests** — Up from 48, covering all new features

## License

MIT