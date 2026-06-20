#!/usr/bin/env python3
"""
Terminal Stock Exchange — A terminal-based stock market simulator with
procedurally generated companies, realistic price dynamics, portfolio
management, and ASCII candlestick charts.

No external dependencies — uses only the Python standard library.
"""

import argparse
import curses
import json
import math
import os
import random
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

SAVE_FILE = os.path.expanduser("~/.terminal-stock-exchange-save.json")

# ─── Procedural Company Generation ──────────────────────────────────────────

INDUSTRIES = [
    "Tech", "Energy", "Finance", "Health", "Materials", "Consumer",
    "Industrial", "Utilities", "Real Estate", "Telecom",
]

COMPANY_NAMES_PREFIX = [
    "Nova", "Apex", "Zephyr", "Quantum", "Helix", "Atlas", "Nexus",
    "Prism", "Forge", "Vortex", "Ember", "Crest", "Pulse", "Stellar",
    "Aegis", "Drift", "Arc", "Flux", "Onyx", "Crux", "Sable", "Vanguard",
    "Tidal", "Cobalt", "Iron", "Solar", "Lunar", "Boreal", "Meridian",
    "Aether", "Titan", "Phoenix", "Obsidian", "Glacier", "Crimson",
    "Azure", "Verdant", "Aurum", "Ferrum", "Silver", "Carbon",
]

COMPANY_NAMES_SUFFIX = [
    "Corp", "Inc", "Labs", "Systems", "Group", "Dynamics", "Tech",
    "Holdings", "Global", "Industries", "Networks", "Works", "Partners",
    "Solutions", "Digital", "Energy", "Capital", "Sciences", "Mech",
    "Fusion", "Core", "Link", "Byte", "Cloud", "Data", "Logic", "Net",
]

TICKER_PREFIXES = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
]

TICKER_MIDDLES = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
    "", "", "", "",  # Bias toward 2-letter tickers
]

NEWS_TEMPLATES_POSITIVE = [
    "{company} announces breakthrough in {field}!",
    "{company} beats quarterly earnings by {pct}%",
    "{company} secures ${amt}B government contract",
    "Analysts upgrade {company} to 'Strong Buy'",
    "{company} expands into {region} market",
    "{company} CEO named 'Executive of the Year'",
    "{company} launches revolutionary {product}",
    "{company} reports record revenue growth",
    "Major partnership: {company} × {partner}",
    "{company} achieves carbon neutrality target",
]

NEWS_TEMPLATES_NEGATIVE = [
    "{company} faces regulatory investigation",
    "{company} misses quarterly earnings by {pct}%",
    "{company} announces layoffs affecting {count} employees",
    "Analysts downgrade {company} to 'Sell'",
    "{company} recalls {product} over safety concerns",
    "{company} CEO resigns amid scandal",
    "{company} loses ${amt}B lawsuit",
    "Supply chain disruption hits {company} hard",
    "{company} warns of slowing growth ahead",
    "Insider selling detected at {company}",
]

NEWS_FIELDS = [
    "AI", "quantum computing", "biotech", "renewable energy", "robotics",
    "cybersecurity", "cloud computing", "blockchain", "genomics", "5G",
]

NEWS_REGIONS = [
    "European", "Asian-Pacific", "Latin American", "African", "Middle Eastern",
]

NEWS_PRODUCTS = [
    "platform", "device", "software suite", "chip", "vehicle", "drug",
    "sensor", "battery", "satellite", "robot",
]


class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


@dataclass
class Order:
    id: int
    ticker: str
    order_type: OrderType
    shares: int
    price: float
    timestamp: int
    status: OrderStatus = OrderStatus.PENDING


@dataclass
class Position:
    ticker: str
    shares: int
    avg_cost: float  # average cost basis per share


@dataclass
class Company:
    ticker: str
    name: str
    industry: str
    price: float
    prev_close: float
    open_price: float
    day_high: float
    day_low: float
    volume: int
    market_cap: float  # in billions
    beta: float  # volatility coefficient
    dividend_yield: float  # annual dividend yield %
    history: list = field(default_factory=list)  # list of (open, high, low, close, volume)
    sentiment: float = 0.0  # -1 to 1


@dataclass
class NewsEvent:
    tick: int
    headline: str
    ticker: str
    impact: float  # price impact multiplier


class StockExchange:
    """Core simulation engine for the terminal stock exchange."""

    def __init__(self, num_companies=20, starting_cash=100000.0, seed=None):
        self.rng = random.Random(seed)
        self.tick = 0
        self.cash = starting_cash
        self.starting_cash = starting_cash
        self.companies: OrderedDict[str, Company] = OrderedDict()
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.news: List[NewsEvent] = []
        self.next_order_id = 1
        self.day = 1
        self.market_open = True
        self.ticks_per_day = 78  # ~6.5 hours of trading at ~5min intervals
        self.daily_ticks = 0
        self.total_dividends = 0.0
        self.trade_log: List[str] = []

        self._generate_companies(num_companies)

    def _generate_companies(self, n: int):
        used_tickers = set()
        used_names = set()
        for _ in range(n):
            # Generate unique ticker
            while True:
                mid = self.rng.choice(TICKER_MIDDLES)
                sfx = self.rng.choice(["", "", "", ""])  # bias toward shorter
                ticker = self.rng.choice(TICKER_PREFIXES) + mid + sfx
                if ticker not in used_tickers and len(ticker) <= 4:
                    used_tickers.add(ticker)
                    break

            # Generate unique name
            while True:
                name = f"{self.rng.choice(COMPANY_NAMES_PREFIX)} {self.rng.choice(COMPANY_NAMES_SUFFIX)}"
                if name not in used_names:
                    used_names.add(name)
                    break

            industry = self.rng.choice(INDUSTRIES)
            price = round(self.rng.uniform(5, 500), 2)
            market_cap = round(self.rng.uniform(0.5, 500), 1)
            beta = round(self.rng.uniform(0.3, 2.5), 2)
            div_yield = round(self.rng.uniform(0, 5), 2) if self.rng.random() < 0.6 else 0.0

            company = Company(
                ticker=ticker,
                name=name,
                industry=industry,
                price=price,
                prev_close=price * (1 + self.rng.uniform(-0.02, 0.02)),
                open_price=price,
                day_high=price,
                day_low=price,
                volume=0,
                market_cap=market_cap,
                beta=beta,
                dividend_yield=div_yield,
                sentiment=self.rng.uniform(-0.3, 0.3),
            )
            # Generate some initial history
            for _ in range(30):
                o = company.price
                change = self.rng.gauss(0, 0.02) * company.beta
                h = o * (1 + abs(self.rng.gauss(0, 0.01)) * company.beta)
                l = o * (1 - abs(self.rng.gauss(0, 0.01)) * company.beta)
                c = o * (1 + change)
                c = max(0.5, c)
                company.history.append((
                    round(o, 2), round(max(o, c, h), 2),
                    round(min(o, c, l), 2), round(c, 2),
                    self.rng.randint(100000, 5000000)
                ))
                company.price = c

            company.prev_close = company.price
            company.open_price = company.price
            company.day_high = company.price
            company.day_low = company.price
            self.companies[ticker] = company

    def step(self):
        """Advance the simulation by one tick."""
        self.tick += 1
        self.daily_ticks += 1

        # Check for new day
        if self.daily_ticks >= self.ticks_per_day:
            self._end_trading_day()
            self._start_trading_day()
            return

        # Price simulation for each company
        for ticker, company in self.companies.items():
            # Geometric Brownian Motion-inspired price update
            drift = 0.00002  # slight upward drift
            volatility = 0.002 * company.beta

            # Sentiment influence
            sentiment_drift = company.sentiment * 0.001
            company.sentiment *= 0.98  # sentiment decays

            # Market-wide factor
            market_factor = self.rng.gauss(0, 0.001)

            # Random event (rare)
            if self.rng.random() < 0.003:
                self._generate_news(company)

            # Apply pending news impact
            for ne in self.news:
                if ne.ticker == ticker and abs(self.tick - ne.tick) < 5:
                    company.sentiment += ne.impact * 0.1

            change_pct = drift + sentiment_drift + market_factor + self.rng.gauss(0, volatility)
            new_price = company.price * (1 + change_pct)
            new_price = max(0.01, round(new_price, 2))

            company.day_high = max(company.day_high, new_price)
            company.day_low = min(company.day_low, new_price)
            company.price = new_price
            company.volume += self.rng.randint(100, 50000)

        # Process orders
        self._process_orders()

    def _generate_news(self, company: Company):
        impact = self.rng.uniform(-0.15, 0.15)
        if impact > 0:
            template = self.rng.choice(NEWS_TEMPLATES_POSITIVE)
        else:
            template = self.rng.choice(NEWS_TEMPLATES_NEGATIVE)

        headline = template.format(
            company=company.name,
            field=self.rng.choice(NEWS_FIELDS),
            pct=round(abs(impact) * 100, 1),
            amt=round(abs(impact) * 10, 1),
            count=self.rng.randint(100, 5000),
            region=self.rng.choice(NEWS_REGIONS),
            product=self.rng.choice(NEWS_PRODUCTS),
            partner=self.rng.choice([c.name for c in list(self.companies.values())[:5]]),
        )

        ne = NewsEvent(
            tick=self.tick,
            headline=headline,
            ticker=company.ticker,
            impact=impact,
        )
        self.news.append(ne)
        company.sentiment += impact * 0.5
        if len(self.news) > 50:
            self.news = self.news[-50:]

    def _start_trading_day(self):
        self.day += 1
        self.daily_ticks = 0
        self.market_open = True

        # Overnight gap
        for company in self.companies.values():
            gap = self.rng.gauss(0, 0.005) * company.beta
            company.prev_close = company.price
            company.open_price = round(company.price * (1 + gap), 2)
            company.price = company.open_price
            company.day_high = company.price
            company.day_low = company.price
            company.volume = 0

    def _end_trading_day(self):
        self.market_open = False
        # Record daily candle
        for company in self.companies.values():
            company.history.append((
                round(company.open_price, 2),
                round(company.day_high, 2),
                round(company.day_low, 2),
                round(company.price, 2),
                company.volume,
            ))
            # Keep history manageable
            if len(company.history) > 365:
                company.history = company.history[-365:]

            # Pay dividends
            if company.dividend_yield > 0:
                pos = self.positions.get(company.ticker)
                if pos and pos.shares > 0:
                    # Quarterly dividend (every ~20 trading days)
                    if self.day % 20 == 0:
                        div_amount = pos.shares * company.price * (company.dividend_yield / 100) / 4
                        div_amount = round(div_amount, 2)
                        self.cash += div_amount
                        self.total_dividends += div_amount
                        self.trade_log.append(
                            f"Day {self.day}: Dividend ${div_amount:.2f} from {company.ticker}"
                        )

    def buy(self, ticker: str, shares: int, limit_price: Optional[float] = None) -> Order:
        if ticker not in self.companies:
            raise ValueError(f"Unknown ticker: {ticker}")
        price = limit_price or self.companies[ticker].price
        cost = shares * price
        if cost > self.cash:
            # Buy as many as we can afford
            shares = int(self.cash / price)
            if shares <= 0:
                raise ValueError(f"Insufficient funds. Need ${cost:.2f}, have ${self.cash:.2f}")
            cost = shares * price

        self.cash -= cost

        order = Order(
            id=self.next_order_id,
            ticker=ticker,
            order_type=OrderType.BUY,
            shares=shares,
            price=price,
            timestamp=self.tick,
            status=OrderStatus.FILLED,
        )
        self.next_order_id += 1
        self.orders.append(order)

        # Update position
        if ticker not in self.positions:
            self.positions[ticker] = Position(ticker=ticker, shares=shares, avg_cost=price)
        else:
            pos = self.positions[ticker]
            total_cost = pos.avg_cost * pos.shares + price * shares
            pos.shares += shares
            pos.avg_cost = total_cost / pos.shares if pos.shares > 0 else 0

        self.trade_log.append(
            f"Day {self.day}: BUY {shares} {ticker} @ ${price:.2f} = ${cost:.2f}"
        )
        return order

    def sell(self, ticker: str, shares: int, limit_price: Optional[float] = None) -> Order:
        if ticker not in self.positions:
            raise ValueError(f"No position in {ticker}")
        pos = self.positions[ticker]
        if shares > pos.shares:
            shares = pos.shares
        if shares <= 0:
            raise ValueError(f"No shares to sell")

        price = limit_price or self.companies[ticker].price
        proceeds = shares * price
        self.cash += proceeds

        order = Order(
            id=self.next_order_id,
            ticker=ticker,
            order_type=OrderType.SELL,
            shares=shares,
            price=price,
            timestamp=self.tick,
            status=OrderStatus.FILLED,
        )
        self.next_order_id += 1
        self.orders.append(order)

        pos.shares -= shares
        if pos.shares <= 0:
            del self.positions[ticker]

        self.trade_log.append(
            f"Day {self.day}: SELL {shares} {ticker} @ ${price:.2f} = ${proceeds:.2f}"
        )
        return order

    def _process_orders(self):
        # Market orders are filled immediately, limit orders check price
        for order in self.orders:
            if order.status != OrderStatus.PENDING:
                continue
            company = self.companies.get(order.ticker)
            if not company:
                continue
            if order.order_type == OrderType.BUY and company.price <= order.price:
                order.status = OrderStatus.FILLED
            elif order.order_type == OrderType.SELL and company.price >= order.price:
                order.status = OrderStatus.FILLED

    def portfolio_value(self) -> float:
        total = self.cash
        for ticker, pos in self.positions.items():
            total += pos.shares * self.companies[ticker].price
        return total

    def portfolio_pnl(self) -> float:
        return self.portfolio_value() - self.starting_cash

    def portfolio_pnl_pct(self) -> float:
        return (self.portfolio_value() / self.starting_cash - 1) * 100

    def save(self):
        data = {
            "tick": self.tick,
            "day": self.day,
            "cash": self.cash,
            "starting_cash": self.starting_cash,
            "total_dividends": self.total_dividends,
            "daily_ticks": self.daily_ticks,
            "companies": {},
            "positions": {},
            "news": [],
            "trade_log": self.trade_log[-100:],  # Keep last 100
        }
        for ticker, c in self.companies.items():
            data["companies"][ticker] = {
                "ticker": c.ticker, "name": c.name, "industry": c.industry,
                "price": c.price, "prev_close": c.prev_close,
                "open_price": c.open_price, "day_high": c.day_high,
                "day_low": c.day_low, "volume": c.volume,
                "market_cap": c.market_cap, "beta": c.beta,
                "dividend_yield": c.dividend_yield,
                "history": c.history, "sentiment": c.sentiment,
            }
        for ticker, pos in self.positions.items():
            data["positions"][ticker] = {
                "ticker": pos.ticker, "shares": pos.shares, "avg_cost": pos.avg_cost,
            }
        for ne in self.news[-30:]:
            data["news"].append({
                "tick": ne.tick, "headline": ne.headline,
                "ticker": ne.ticker, "impact": ne.impact,
            })
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f)

    @classmethod
    def load(cls) -> Optional["StockExchange"]:
        if not os.path.exists(SAVE_FILE):
            return None
        try:
            with open(SAVE_FILE) as f:
                data = json.load(f)
            ex = cls.__new__(cls)
            ex.tick = data["tick"]
            ex.day = data["day"]
            ex.cash = data["cash"]
            ex.starting_cash = data["starting_cash"]
            ex.total_dividends = data.get("total_dividends", 0)
            ex.daily_ticks = data.get("daily_ticks", 0)
            ex.companies = OrderedDict()
            ex.positions = {}
            ex.orders = []
            ex.news = []
            ex.next_order_id = 1
            ex.market_open = True
            ex.ticks_per_day = 78
            ex.trade_log = data.get("trade_log", [])
            ex.rng = random.Random()

            for ticker, cd in data["companies"].items():
                ex.companies[ticker] = Company(
                    ticker=cd["ticker"], name=cd["name"], industry=cd["industry"],
                    price=cd["price"], prev_close=cd["prev_close"],
                    open_price=cd["open_price"], day_high=cd["day_high"],
                    day_low=cd["day_low"], volume=cd["volume"],
                    market_cap=cd["market_cap"], beta=cd["beta"],
                    dividend_yield=cd["dividend_yield"],
                    history=[tuple(h) for h in cd["history"]],
                    sentiment=cd["sentiment"],
                )
            for ticker, pd in data["positions"].items():
                ex.positions[ticker] = Position(
                    ticker=pd["ticker"], shares=pd["shares"], avg_cost=pd["avg_cost"],
                )
            for nd in data.get("news", []):
                ex.news.append(NewsEvent(
                    tick=nd["tick"], headline=nd["headline"],
                    ticker=nd["ticker"], impact=nd["impact"],
                ))
            return ex
        except Exception:
            return None


# ─── UI Rendering ───────────────────────────────────────────────────────────

COLOR_PAIRS = {
    "green": 1,
    "red": 2,
    "yellow": 3,
    "cyan": 4,
    "white": 5,
    "blue": 6,
    "magenta": 7,
    "dim_green": 8,
    "dim_red": 9,
}


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_CYAN, -1)
    curses.init_pair(5, curses.COLOR_WHITE, -1)
    curses.init_pair(6, curses.COLOR_BLUE, -1)
    curses.init_pair(7, curses.COLOR_MAGENTA, -1)
    curses.init_pair(8, 108, -1)  # dim green
    curses.init_pair(9, 131, -1)  # dim red


def color(name):
    return curses.color_pair(COLOR_PAIRS.get(name, 5))


def fmt_price(p: float) -> str:
    if p >= 1000:
        return f"${p:,.0f}"
    return f"${p:,.2f}"


def fmt_change(current: float, prev: float) -> Tuple[str, str]:
    if prev == 0:
        return "+0.00", "0.00%"
    chg = current - prev
    pct = (current / prev - 1) * 100
    sign = "+" if chg >= 0 else ""
    return f"{sign}{chg:.2f}", f"{sign}{pct:.2f}%"


def fmt_volume(v: int) -> str:
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.0f}K"
    return str(v)


def draw_candlestick_chart(company: Company, win, y: int, x: int, w: int, h: int):
    """Draw an ASCII candlestick chart in the given window area."""
    history = company.history[-w:]
    if len(history) < 2:
        return

    # Determine price range
    all_prices = []
    for o, hi, lo, c, v in history:
        all_prices.extend([hi, lo])
    pmin = min(all_prices)
    pmax = max(all_prices)
    if pmax == pmin:
        pmax = pmin + 1

    price_range = pmax - pmin

    # Draw each candle
    chart_lines = []
    for row in range(h):
        chart_lines.append([" "] * len(history))

    for i, (o, hi, lo, c, v) in enumerate(history):
        if c >= o:
            bull = True
        else:
            bull = False

        # Map prices to rows
        def price_to_row(p):
            return int((pmax - p) / price_range * (h - 1))

        wick_top = price_to_row(hi)
        wick_bot = price_to_row(lo)
        body_top = price_to_row(max(o, c))
        body_bot = price_to_row(min(o, c))

        # Draw wick
        for row in range(max(0, wick_top), min(h, wick_bot + 1)):
            if row < 0 or row >= h:
                continue
            if body_top <= row <= body_bot:
                if bull:
                    chart_lines[row][i] = "█"
                else:
                    chart_lines[row][i] = "░"
            else:
                chart_lines[row][i] = "│"

    # Render
    for row in range(h):
        try:
            line = "".join(chart_lines[row])
            if bull := any(ch in line for ch in ["█", "│"]):
                # Determine color per line
                has_bull = "█" in line
                has_bear = "░" in line
                if has_bull and not has_bear:
                    win.addstr(y + row, x, line, color("green"))
                elif has_bear and not has_bull:
                    win.addstr(y + row, x, line, color("red"))
                else:
                    win.addstr(y + row, x, line, color("white"))
            else:
                win.addstr(y + row, x, line)
        except curses.error:
            pass


class View(Enum):
    MARKET = 0
    PORTFOLIO = 1
    CHART = 2
    NEWS = 3
    TRADE_LOG = 4


def run_ui(stdscr, exchange: StockExchange):
    init_colors()
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(100)  # 100ms refresh

    current_view = View.MARKET
    selected_idx = 0
    scroll_offset = 0
    input_mode = None  # None, 'buy', 'sell'
    input_buffer = ""
    message = ""
    message_timer = 0
    speed = 1  # ticks per frame
    paused = False
    sort_by = "ticker"  # ticker, price, change, volume
    sort_ascending = True

    # Sort options cycle
    sort_cycle = ["ticker", "change", "volume", "price"]

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        # Header
        portfolio_val = exchange.portfolio_value()
        pnl = exchange.portfolio_pnl()
        pnl_pct = exchange.portfolio_pnl_pct()
        pnl_color = "green" if pnl >= 0 else "red"

        header = (
            f" ⣿ TERMINAL STOCK EXCHANGE │ Day {exchange.day} │ "
            f"Portfolio: {fmt_price(portfolio_val)} │ "
        )
        stdscr.addstr(0, 0, header, color("cyan") | curses.A_BOLD)
        pnl_str = f"P&L: {'+'if pnl>=0 else ''}{pnl:.2f} ({pnl_pct:+.2f}%) "
        stdscr.addstr(0, len(header), pnl_str, color(pnl_color) | curses.A_BOLD)

        # Status bar
        status_parts = [
            f"Cash: {fmt_price(exchange.cash)}",
            f"Speed: {speed}x",
            "PAUSED" if paused else "RUNNING",
            f"View: {current_view.name}",
        ]
        if exchange.total_dividends > 0:
            status_parts.append(f"Dividends: {fmt_price(exchange.total_dividends)}")
        status = " │ ".join(status_parts)
        stdscr.addstr(1, 0, f" {status}", color("yellow"))

        # Navigation hint
        nav = " [1]Market [2]Portfolio [3]Chart [4]News [5]Log  [+]Speed [-]Slow [Space]Pause [Q]uit"
        stdscr.addstr(2, 0, nav, color("dim_green"))

        if message_timer > 0:
            message_timer -= 1
            stdscr.addstr(2, w - len(message) - 2, message, color("yellow") | curses.A_BOLD)

        # Main content area starts at row 3
        content_y = 3
        content_h = h - content_y - 1  # leave bottom for input

        tickers = list(exchange.companies.keys())

        if current_view == View.MARKET:
            # Column headers
            headers = f" {'#':>2}  {'Ticker':<5} {'Company':<22} {'Industry':<12} {'Price':>8} {'Change':>9} {'Vol':>7} {'β':>5} {'Div':>5}"
            stdscr.addstr(content_y, 0, headers, color("cyan") | curses.A_BOLD)
            stdscr.addstr(content_y + 1, 0, " " + "─" * (w - 2), color("cyan"))

            # Sort companies
            if sort_by == "ticker":
                sorted_tickers = sorted(tickers)
            elif sort_by == "change":
                sorted_tickers = sorted(tickers,
                    key=lambda t: (exchange.companies[t].price / exchange.companies[t].prev_close - 1),
                    reverse=True)
            elif sort_by == "volume":
                sorted_tickers = sorted(tickers,
                    key=lambda t: exchange.companies[t].volume, reverse=True)
            elif sort_by == "price":
                sorted_tickers = sorted(tickers,
                    key=lambda t: exchange.companies[t].price, reverse=True)
            else:
                sorted_tickers = tickers

            if not sort_ascending:
                sorted_tickers = list(reversed(sorted_tickers))

            # Adjust scroll
            if selected_idx >= len(sorted_tickers):
                selected_idx = max(0, len(sorted_tickers) - 1)
            if selected_idx < scroll_offset:
                scroll_offset = selected_idx
            max_scroll = max(0, len(sorted_tickers) - content_h + 3)
            scroll_offset = min(scroll_offset, max_scroll)

            row = content_y + 2
            visible = sorted_tickers[scroll_offset:]
            for i, ticker in enumerate(visible):
                if row >= content_y + content_h:
                    break
                c = exchange.companies[ticker]
                chg_str, pct_str = fmt_change(c.price, c.prev_close)
                is_up = c.price >= c.prev_close
                chg_color = "green" if is_up else "red"
                arrow = "▲" if is_up else "▼"

                line = f" {i+scroll_offset+1:>2}  {c.ticker:<5} {c.name[:22]:<22} {c.industry:<12} {c.price:>8.2f} {arrow}{pct_str:>8} {fmt_volume(c.volume):>7} {c.beta:>5.2f} "
                if c.dividend_yield > 0:
                    line += f"{c.dividend_yield:>4.1f}%"
                else:
                    line += "    -"

                attr = color(chg_color)
                if i + scroll_offset == selected_idx:
                    attr |= curses.A_REVERSE
                stdscr.addstr(row, 0, line[:w-1], attr)
                row += 1

            # Bottom hint
            hint = f" [↑↓]Select [Enter]Chart [b]Buy [s]Sell [S]ort:{sort_by} [D]esc"
            stdscr.addstr(h - 1, 0, hint, color("dim_green"))

        elif current_view == View.PORTFOLIO:
            stdscr.addstr(content_y, 0, f" {'Ticker':<6} {'Shares':>7} {'Avg Cost':>10} {'Current':>10} {'Value':>12} {'P&L':>12} {'P&L%':>8}",
                         color("cyan") | curses.A_BOLD)
            stdscr.addstr(content_y + 1, 0, " " + "─" * (w - 2), color("cyan"))

            row = content_y + 2
            total_value = exchange.cash
            for ticker, pos in sorted(exchange.positions.items()):
                if row >= content_y + content_h:
                    break
                c = exchange.companies[ticker]
                value = pos.shares * c.price
                cost_basis = pos.shares * pos.avg_cost
                pl = value - cost_basis
                pl_pct = (value / cost_basis - 1) * 100 if cost_basis > 0 else 0
                is_up = pl >= 0

                line = f" {ticker:<6} {pos.shares:>7} {pos.avg_cost:>10.2f} {c.price:>10.2f} {fmt_price(value):>12} {'+'if is_up else ''}{pl:>10.2f} {'+'if is_up else ''}{pl_pct:>6.2f}%"
                stdscr.addstr(row, 0, line[:w-1], color("green" if is_up else "red"))
                row += 1
                total_value += value  # already counted cash

            # Actually compute properly
            total_value = exchange.portfolio_value()
            stdscr.addstr(row + 1, 0, f" Cash: {fmt_price(exchange.cash):>12}", color("yellow"))
            stdscr.addstr(row + 2, 0, f" Invested: {fmt_price(total_value - exchange.cash):>10}", color("yellow"))
            stdscr.addstr(row + 3, 0, f" Total: {fmt_price(total_value):>12}", color("yellow") | curses.A_BOLD)

            if exchange.total_dividends > 0:
                stdscr.addstr(row + 4, 0, f" Dividends earned: {fmt_price(exchange.total_dividends):>8}", color("green"))

            stdscr.addstr(h - 1, 0, " [b]Buy [s]Sell [Enter]Chart [1]Market", color("dim_green"))

        elif current_view == View.CHART:
            if tickers:
                if selected_idx >= len(tickers):
                    selected_idx = 0
                # Get ticker - use selected company
                sorted_tickers = sorted(tickers)
                ticker = sorted_tickers[selected_idx] if selected_idx < len(sorted_tickers) else tickers[0]
                c = exchange.companies[ticker]

                # Company info
                chg_str, pct_str = fmt_change(c.price, c.prev_close)
                is_up = c.price >= c.prev_close
                info_color = "green" if is_up else "red"
                info = f" {c.ticker} — {c.name} ({c.industry})"
                stdscr.addstr(content_y, 0, info, color("cyan") | curses.A_BOLD)

                price_line = f" Price: {c.price:.2f}  {chg_str} {pct_str}  H:{c.day_high:.2f} L:{c.day_low:.2f}  Vol:{fmt_volume(c.volume)}"
                stdscr.addstr(content_y + 1, 0, price_line, color(info_color))

                # Chart area
                chart_y = content_y + 3
                chart_h = content_h - 6
                chart_w = min(w - 2, len(c.history))
                chart_w = max(chart_w, 10)

                # Price labels on left
                if c.history:
                    all_hi = [h[1] for h in c.history[-chart_w:]]
                    all_lo = [h[2] for h in c.history[-chart_w:]]
                    pmax = max(all_hi) if all_hi else c.price * 1.05
                    pmin = min(all_lo) if all_lo else c.price * 0.95
                    if pmax == pmin:
                        pmax = pmin + 1

                    for row_i in range(chart_h):
                        price_at_row = pmax - (pmax - pmin) * row_i / max(chart_h - 1, 1)
                        label = f"{price_at_row:>8.1f} │"
                        stdscr.addstr(chart_y + row_i, 0, label, color("dim_green"))

                    draw_candlestick_chart(c, stdscr, chart_y, 10, chart_w, chart_h)

                # Volume bars at bottom
                vol_y = chart_y + chart_h + 1
                stdscr.addstr(vol_y, 0, f" {'Day':>5} │ Volume bars", color("dim_green"))

                vol_h = min(5, content_y + content_h - vol_y - 2)
                if vol_h > 0 and c.history:
                    recent = c.history[-(w-12):]
                    max_vol = max(v for _, _, _, _, v in recent) if recent else 1
                    for col_i, (o, hi, lo, cl, vol) in enumerate(recent):
                        if col_i >= w - 12:
                            break
                        bar_h = int(vol / max_vol * vol_h)
                        is_bull = cl >= o
                        for bar_row in range(bar_h):
                            try:
                                stdscr.addstr(
                                    vol_y + vol_h - bar_row, 12 + col_i,
                                    "▓" if is_bull else "▒",
                                    color("green" if is_bull else "red"),
                                )
                            except curses.error:
                                pass

                stdscr.addstr(h - 1, 0, " [↑↓]Change stock [1]Market [2]Portfolio [b]Buy [s]Sell", color("dim_green"))

        elif current_view == View.NEWS:
            stdscr.addstr(content_y, 0, " 📰 MARKET NEWS & EVENTS", color("cyan") | curses.A_BOLD)
            stdscr.addstr(content_y + 1, 0, " " + "─" * (w - 2), color("cyan"))

            row = content_y + 2
            for ne in reversed(exchange.news[-20:]):
                if row >= content_y + content_h:
                    break
                age = exchange.tick - ne.tick
                age_str = f"[{age}]" if age < 1000 else ""
                impact_sym = "▲" if ne.impact > 0 else "▼"
                impact_color = "green" if ne.impact > 0 else "red"
                line = f" {age_str:>5} {impact_sym} {ne.headline[:w-15]}"
                stdscr.addstr(row, 0, line[:w-1], color(impact_color))
                row += 1

            if not exchange.news:
                stdscr.addstr(row, 0, " No news yet. The market will generate events over time.", color("yellow"))

            stdscr.addstr(h - 1, 0, " [1]Market [2]Portfolio [3]Chart", color("dim_green"))

        elif current_view == View.TRADE_LOG:
            stdscr.addstr(content_y, 0, " 📋 TRADE LOG", color("cyan") | curses.A_BOLD)
            stdscr.addstr(content_y + 1, 0, " " + "─" * (w - 2), color("cyan"))

            row = content_y + 2
            for entry in reversed(exchange.trade_log[-30:]):
                if row >= content_y + content_h:
                    break
                is_buy = "BUY" in entry
                stdscr.addstr(row, 0, f" {entry[:w-2]}", color("green" if is_buy else "red"))
                row += 1

            if not exchange.trade_log:
                stdscr.addstr(row, 0, " No trades yet. Press [b] to buy or [s] to sell.", color("yellow"))

            stdscr.addstr(h - 1, 0, " [1]Market [2]Portfolio [3]Chart [4]News", color("dim_green"))

        # Input mode overlay
        if input_mode:
            prompt = f" {input_mode.upper()} — Enter ticker" if not input_buffer else f" {input_mode.upper()} {input_buffer}"
            stdscr.addstr(h - 2, 0, prompt[:w-1], color("yellow") | curses.A_BOLD)

        stdscr.refresh()

        # Handle input
        try:
            key = stdscr.getch()
        except:
            continue

        if key == -1:
            # No key pressed, advance simulation
            if not paused:
                for _ in range(speed):
                    exchange.step()
            continue

        if input_mode:
            if key == 27 or key == ord('q'):  # ESC
                input_mode = None
                input_buffer = ""
            elif key == curses.KEY_ENTER or key == 10 or key == 13:
                # Process input
                if input_mode in ('buy', 'sell'):
                    ticker = input_buffer.upper().strip()
                    if ticker in exchange.companies:
                        if input_mode == 'buy':
                            # Buy 10 shares by default
                            try:
                                c = exchange.companies[ticker]
                                max_shares = int(exchange.cash / c.price)
                                shares = min(10, max_shares)
                                if shares > 0:
                                    order = exchange.buy(ticker, shares)
                                    message = f"Bought {shares} {ticker} @ {c.price:.2f}"
                                else:
                                    message = "Can't afford any shares"
                            except ValueError as e:
                                message = str(e)
                        elif input_mode == 'sell':
                            if ticker in exchange.positions:
                                shares = min(10, exchange.positions[ticker].shares)
                                try:
                                    order = exchange.sell(ticker, shares)
                                    c = exchange.companies[ticker]
                                    message = f"Sold {shares} {ticker} @ {c.price:.2f}"
                                except ValueError as e:
                                    message = str(e)
                            else:
                                message = f"No position in {ticker}"
                    else:
                        message = f"Unknown ticker: {ticker}"
                input_mode = None
                input_buffer = ""
                message_timer = 30
            elif key == curses.KEY_BACKSPACE or key == 127:
                input_buffer = input_buffer[:-1]
            elif 32 <= key <= 126:
                input_buffer += chr(key)
            continue

        # Normal mode key handling
        if key == ord('q') or key == ord('Q'):
            exchange.save()
            break
        elif key == ord('1'):
            current_view = View.MARKET
        elif key == ord('2'):
            current_view = View.PORTFOLIO
        elif key == ord('3'):
            current_view = View.CHART
        elif key == ord('4'):
            current_view = View.NEWS
        elif key == ord('5'):
            current_view = View.TRADE_LOG
        elif key == ord('b') or key == ord('B'):
            input_mode = 'buy'
            input_buffer = ""
        elif key == ord('s') or key == ord('S'):
            if key == ord('S'):
                # Shift+S = sort
                idx = sort_cycle.index(sort_by) if sort_by in sort_cycle else 0
                sort_by = sort_cycle[(idx + 1) % len(sort_cycle)]
            else:
                input_mode = 'sell'
                input_buffer = ""
        elif key == ord('D'):
            sort_ascending = not sort_ascending
        elif key == ord(' '):
            paused = not paused
        elif key == ord('+') or key == ord('='):
            speed = min(speed + 1, 20)
        elif key == ord('-') or key == ord('_'):
            speed = max(speed - 1, 1)
        elif key == curses.KEY_UP:
            selected_idx = max(0, selected_idx - 1)
        elif key == curses.KEY_DOWN:
            selected_idx = min(len(tickers) - 1, selected_idx + 1)
        elif key == curses.KEY_NPAGE:
            selected_idx = min(len(tickers) - 1, selected_idx + 10)
        elif key == curses.KEY_PPAGE:
            selected_idx = max(0, selected_idx - 10)
        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            current_view = View.CHART
        # Number keys for buy amounts in buy mode handled above

        # Advance simulation
        if not paused:
            for _ in range(speed):
                exchange.step()


def main():
    parser = argparse.ArgumentParser(description="Terminal Stock Exchange Simulator")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--companies", type=int, default=20, help="Number of companies to generate")
    parser.add_argument("--cash", type=float, default=100000, help="Starting cash")
    parser.add_argument("--new", action="store_true", help="Start a new game (ignore save)")
    args = parser.parse_args()

    # Load existing game or create new
    exchange = None
    if not args.new:
        exchange = StockExchange.load()

    if exchange is None:
        exchange = StockExchange(
            num_companies=args.companies,
            starting_cash=args.cash,
            seed=args.seed,
        )

    curses.wrapper(run_ui, exchange)


if __name__ == "__main__":
    main()