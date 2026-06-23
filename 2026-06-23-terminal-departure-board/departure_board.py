#!/usr/bin/env python3
"""
Terminal Airport Departure Board
=================================
A real-time animated flip-board style flight information display system (FIDS)
with procedurally generated flights, delays, gate changes, and mechanical
character-cycling animation — all in the terminal.

Features:
  - Authentic flip-board character cycling animation
  - Procedurally generated flights with realistic airlines, cities, statuses
  - Live updates: delays, gate changes, cancellations, boarding calls
  - Color-coded status rows (green=on time, yellow=delayed, red=canceled, etc.)
  - Configurable update speed and board size
  - Flight search/filter by destination, airline, or flight number
  - Arrival board mode (--arrivals)
  - Random airport announcements for immersion
  - Weather display on the board header
  - ASCII art airport sign header
  - Sound-bell on boarding announcements (terminal bell)

Usage:
  python departure_board.py              # full board, default refresh
  python departure_board.py --compact    # fewer rows
  python departure_board.py --fast       # faster animation & updates
  python departure_board.py --filter BA  # show only British Airways flights
  python departure_board.py --destination Tokyo  # filter by destination
  python departure_board.py --arrivals   # show arrivals board instead
  python departure_board.py --flight BA117  # search for a specific flight
  python departure_board.py --no-animate # skip flip animation (instant)
  python departure_board.py --help       # full options
  python departure_board.py --version    # show version

Author: Daily Ideas Generator
Version: 1.1.0
"""

import random
import time
import sys
import argparse
import shutil
import itertools
import signal
from datetime import datetime, timedelta

__version__ = "1.1.0"

# ── ANSI helpers ────────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
BLINK = "\033[5m"
BELL = "\a"

FG = {
    "black":   "\033[30m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
}

BG = {
    "black":   "\033[40m",
    "red":     "\033[41m",
    "green":   "\033[42m",
    "yellow":  "\033[43m",
    "blue":    "\033[44m",
    "magenta": "\033[45m",
    "cyan":    "\033[46m",
    "white":   "\033[47m",
}

STATUS_COLORS = {
    "ON TIME":      (FG["green"],  BG["black"]),
    "BOARDING":     (FG["yellow"], BG["black"]),
    "DELAYED":      (FG["red"],    BG["black"]),
    "CANCELLED":    (FG["white"],  BG["red"]),
    "GATE CHANGE":  (FG["cyan"],   BG["black"]),
    "FINAL CALL":   (FG["yellow"], BG["red"]),
    "DEPARTED":     (FG["white"],  BG["black"]),
    "GATE OPEN":    (FG["green"],  BG["black"]),
    "ARRIVED":      (FG["green"],  BG["black"]),
    "LANDED":       (FG["cyan"],   BG["black"]),
    "EXPECTED":     (FG["yellow"], BG["black"]),
    "DIVERTED":     (FG["magenta"],BG["black"]),
}

# ── Flight data pools ────────────────────────────────────────────────────────

AIRLINES = [
    ("BA", "BRITISH AIRWAYS",   "🇬🇧"),
    ("AA", "AMERICAN AIRLINES",  "🇺🇸"),
    ("UA", "UNITED AIRLINES",   "🇺🇸"),
    ("DL", "DELTA AIR LINES",   "🇺🇸"),
    ("LH", "LUFTHANSA",         "🇩🇪"),
    ("AF", "AIR FRANCE",        "🇫🇷"),
    ("EK", "EMIRATES",          "🇦🇪"),
    ("SQ", "SINGAPORE AIRLINES","🇸🇬"),
    ("QF", "QANTAS",            "🇦🇺"),
    ("JL", "JAPAN AIRLINES",   "🇯🇵"),
    ("CX", "CATHAY PACIFIC",   "🇭🇰"),
    ("TK", "TURKISH AIRLINES",  "🇹🇷"),
    ("NH", "ALL NIPPON AIRWAYS","🇯🇵"),
    ("SK", "SAS SCANDINAVIAN",  "🇸🇪"),
    ("IB", "IBERIA",            "🇪🇸"),
    ("KL", "KLM ROYAL DUTCH",  "🇳🇱"),
    ("ET", "ETHIOPIAN AIRLINES","🇪🇹"),
    ("QR", "QATAR AIRWAYS",    "🇶🇦"),
    ("EY", "ETIHAD AIRWAYS",   "🇦🇪"),
    ("VS", "VIRGIN ATLANTIC",  "🇬🇧"),
]

DESTINATIONS = [
    ("New York JFK",      "JFK"),
    ("Los Angeles",       "LAX"),
    ("Tokyo Narita",      "NRT"),
    ("Tokyo Haneda",      "HND"),
    ("London Heathrow",   "LHR"),
    ("Paris CDG",         "CDG"),
    ("Dubai",             "DXB"),
    ("Singapore",         "SIN"),
    ("Hong Kong",         "HKG"),
    ("Sydney",            "SYD"),
    ("Frankfurt",         "FRA"),
    ("Istanbul",          "IST"),
    ("Seoul Incheon",     "ICN"),
    ("Bangkok",            "BKK"),
    ("Mumbai",             "BOM"),
    ("Cairo",              "CAI"),
    ("São Paulo",          "GRU"),
    ("Mexico City",        "MEX"),
    ("Toronto",            "YYZ"),
    ("Cape Town",          "CPT"),
    ("Amsterdam",          "AMS"),
    ("Madrid",             "MAD"),
    ("Rome Fiumicino",     "FCO"),
    ("Berlin Brandenburg", "BER"),
    ("Stockholm Arlanda",  "ARN"),
    ("Moscow Sheremetyevo","SVO"),
    ("Beijing Capital",   "PEK"),
    ("Shanghai Pudong",   "PVG"),
    ("Taipei Taoyuan",    "TPE"),
    ("Melbourne",          "MEL"),
]

# Origins used for arrival board (flights arriving *from* these cities)
ORIGINS = DESTINATIONS  # reuse same pool for origins

GATES = [f"{letter}{num}" for letter in "ABCDEF" for num in range(1, 16)]

TERMINALS = ["T1", "T2", "T3", "T4", "T5"]

# Characters used in flip animation (sorted for visual sweep)
FLIP_CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:-/."

# ── Weather simulation data ─────────────────────────────────────────────────

WEATHER_CONDITIONS = [
    ("☀ Clear skies",       0.3),
    ("⛅ Partly cloudy",    0.2),
    ("🌤 Mostly sunny",     0.15),
    ("🌥 Overcast",         0.1),
    ("🌧 Light rain",       0.08),
    ("🌧 Heavy rain",       0.04),
    ("🌨 Snow",             0.03),
    ("🌫 Fog",              0.05),
    ("🌬 Strong winds",     0.05),
]

WEATHER_TEMPS = {
    "☀ Clear skies": (18, 32),
    "⛅ Partly cloudy": (15, 28),
    "🌤 Mostly sunny": (16, 30),
    "🌥 Overcast": (10, 22),
    "🌧 Light rain": (8, 20),
    "🌧 Heavy rain": (5, 18),
    "🌨 Snow": (-5, 5),
    "🌫 Fog": (5, 15),
    "🌬 Strong winds": (8, 20),
}

# ── Random airport announcements ─────────────────────────────────────────────

ANNOUNCEMENTS = [
    "Remember: liquids over 100ml are not permitted through security.",
    "Free WiFi available throughout all terminals. Network: AIRPORT_FREE",
    "Duty-free shops in Terminal 3 now open until 22:00.",
    "Ground transportation: taxis available at Arrivals level.",
    "Currency exchange available at Gate B near Terminal 2.",
    "Smoking is permitted only in designated outdoor areas.",
    "For lost luggage, please contact your airline's baggage desk.",
    "Lounge access available for eligible passengers in Terminal 1 & 3.",
    "Flight information displays are located throughout all terminals.",
    "Please do not leave baggage unattended. Report suspicious items.",
    "Charging stations available near every gate seating area.",
    "Medical assistance: first aid station near Gate A1.",
    "Children's play area located in Terminal 5, Level 2.",
    "Shower facilities available in Terminal 3 transit hotel.",
    "Airport shuttle runs between terminals every 8 minutes.",
    "Self-service check-in kiosks available at all terminals.",
    "Priority boarding available for families with small children.",
    "Weather advisory: expect turbulence on northern routes today.",
    "ATM services available 24/7 in all terminal concourses.",
    "Thank you for choosing our airport. Safe travels!",
]

# ── Flight class ─────────────────────────────────────────────────────────────

class Flight:
    """Represents a single flight on the departure or arrival board.

    Attributes:
        flight_id: Unique integer ID for the flight.
        airline_code: IATA airline code (e.g. 'BA').
        airline_name: Full airline name.
        destination_name: Destination city name (or origin for arrivals).
        destination_code: IATA airport code for destination/origin.
        flight_no: Full flight number string (e.g. 'BA117').
        terminal: Terminal identifier (T1–T5).
        gate: Gate identifier (e.g. 'A12').
        status: Current flight status string.
        scheduled: Scheduled departure/arrival datetime.
        estimated: Estimated actual departure/arrival datetime.
        belt: Baggage belt number (arrivals only).
        is_arrival: Whether this is an arriving flight.
    """

    _counter = itertools.count(100)

    def __init__(self, now=None, is_arrival=False):
        """Initialize a procedurally generated flight.

        Args:
            now: Current simulated time (defaults to real current time).
            is_arrival: If True, generate as an arrival flight.
        """
        self.flight_id = next(Flight._counter)
        airline_code, airline_name, _ = random.choice(AIRLINES)
        self.airline_code = airline_code
        self.airline_name = airline_name
        self.is_arrival = is_arrival

        if is_arrival:
            # For arrivals, the "from" city is the origin
            dest_name, dest_code = random.choice(ORIGINS)
            self.destination_name = f"From {dest_name}"
            self.destination_code = dest_code
            self.belt = f"B{random.randint(1, 12)}"
        else:
            dest_name, dest_code = random.choice(DESTINATIONS)
            self.destination_name = dest_name
            self.destination_code = dest_code
            self.belt = None

        self.flight_no = f"{airline_code}{random.randint(100, 9999)}"
        self.terminal = random.choice(TERMINALS)
        self.gate = random.choice(GATES)
        self.status = "EXPECTED" if is_arrival else "ON TIME"

        # Scheduled time sometime in the next few hours
        offset = random.randint(10, 360)
        self.scheduled = (now or datetime.now()) + timedelta(minutes=offset)
        self.estimated = self.scheduled
        self._next_event_time = self.scheduled - timedelta(minutes=random.randint(5, 45))
        self._cancelled = False

    def tick(self, now):
        """Advance the flight state based on current simulated time.

        For departures, progresses through: ON TIME → GATE OPEN → BOARDING →
        FINAL CALL → DEPARTED, with random DELAYED, GATE CHANGE, CANCELLED events.
        For arrivals, progresses through: EXPECTED → LANDED → ARRIVED, with
        random DELAYED, DIVERTED events.

        Args:
            now: Current simulated datetime.

        Returns:
            True if the status changed this tick, False otherwise.
        """
        old_status = self.status
        mins_to_arrival = (self.scheduled - now).total_seconds() / 60

        if self._cancelled:
            return False

        # Only process events when it's time
        if now < self._next_event_time:
            return False

        event_roll = random.random()

        if self.is_arrival:
            self._tick_arrival(mins_to_arrival, event_roll)
        else:
            self._tick_departure(mins_to_arrival, event_roll, now)

        # Schedule next event check
        if not self._cancelled:
            self._next_event_time = now + timedelta(minutes=random.randint(3, 15))

        return self.status != old_status

    def _tick_arrival(self, mins, roll):
        """Update status for arrival flights."""
        if mins < -5:
            self.status = "ARRIVED"
        elif mins < 0:
            self.status = "LANDED"
        elif mins < 10:
            if roll < 0.6:
                self.status = "LANDED"
            elif roll < 0.85:
                self.status = "EXPECTED"
        elif mins < 30:
            if roll < 0.3 and self.status == "EXPECTED":
                self.status = "DELAYED"
                self.estimated = self.scheduled + timedelta(minutes=random.randint(10, 45))
        elif mins < 60:
            if roll < 0.12 and self.status == "EXPECTED":
                self.status = "DELAYED"
                self.estimated = self.scheduled + timedelta(minutes=random.randint(15, 60))
            elif roll < 0.03:
                self.status = "DIVERTED"
                self._cancelled = True

    def _tick_departure(self, mins, roll, now):
        """Update status for departure flights."""
        if mins < 0:
            self.status = "DEPARTED"
        elif mins < 10 and self.status == "BOARDING":
            if roll < 0.3:
                self.status = "FINAL CALL"
            else:
                self._next_event_time = now + timedelta(minutes=random.randint(3, 8))
        elif mins < 20 and self.status in ("ON TIME", "GATE OPEN"):
            if roll < 0.6:
                self.status = "BOARDING"
            elif roll < 0.8:
                self.status = "GATE OPEN"
            self._next_event_time = now + timedelta(minutes=random.randint(3, 10))
        elif mins < 40:
            if roll < 0.15 and self.status == "ON TIME":
                self.status = "DELAYED"
                delay = random.randint(15, 90)
                self.estimated = self.scheduled + timedelta(minutes=delay)
            elif roll < 0.05:
                self.status = "CANCELLED"
                self._cancelled = True
            elif roll < 0.08 and self.status != "CANCELLED":
                self.gate = random.choice(GATES)
                self.status = "GATE CHANGE"
            self._next_event_time = now + timedelta(minutes=random.randint(5, 20))
        else:
            # Far out — occasional delay
            if roll < 0.08 and self.status == "ON TIME":
                self.status = "DELAYED"
                delay = random.randint(20, 120)
                self.estimated = self.scheduled + timedelta(minutes=delay)
            self._next_event_time = now + timedelta(minutes=random.randint(10, 30))


# ── Flip-board display engine ────────────────────────────────────────────────

class FlipBoard:
    """Handles the character-cycling flip animation for a row of text.

    Mimics real mechanical split-flap displays by sweeping characters through
    the FLIP_CHARS alphabet before settling on the target character. Characters
    that don't need to change stay fixed, creating the signature wave effect.
    """

    def __init__(self, animate=True):
        """Args:
            animate: If False, skip animation and show target text immediately.
        """
        self.animate = animate

    @staticmethod
    def flip_distance(current, target):
        """Compute the number of flip steps between current and target characters.

        Args:
            current: The current character being displayed.
            target: The desired target character.

        Returns:
            Integer number of steps through FLIP_CHARS to reach target.
        """
        if current == target:
            return 0
        ci = FLIP_CHARS.find(current)
        ti = FLIP_CHARS.find(target)
        if ci < 0:
            ci = 0
        if ti < 0:
            ti = 0
        dist = (ti - ci) % len(FLIP_CHARS)
        return dist

    def animate_line(self, old_text, new_text, width, fg_color="", bg_color=""):
        """Yield intermediate frames for flip animation.

        Each frame represents one step of the character cycling. Characters
        with longer flip distances take more steps, creating a cascade effect.

        Args:
            old_text: Previous line content.
            new_text: Target line content.
            width: Display width for padding/truncation.
            fg_color: Optional ANSI foreground color (unused in frames).
            bg_color: Optional ANSI background color (unused in frames).

        Yields:
            String frames, one per animation step.
        """
        old_padded = old_text.ljust(width)[:width]
        new_padded = new_text.ljust(width)[:width]

        # Determine per-column flip distances
        distances = []
        for i in range(width):
            d = self.flip_distance(old_padded[i], new_padded[i])
            distances.append(d)

        max_dist = max(distances) if distances else 0
        if not self.animate:
            max_dist = 0

        for step in range(max_dist + 1):
            frame_chars = []
            for i in range(width):
                if distances[i] == 0:
                    frame_chars.append(new_padded[i])
                else:
                    progress = step / distances[i]
                    if progress >= 1.0:
                        frame_chars.append(new_padded[i])
                    else:
                        ci = FLIP_CHARS.find(old_padded[i]) if old_padded[i] in FLIP_CHARS else 0
                        ti = FLIP_CHARS.find(new_padded[i]) if new_padded[i] in FLIP_CHARS else 0
                        current_idx = ci + int(progress * ((ti - ci) % len(FLIP_CHARS)))
                        current_idx = current_idx % len(FLIP_CHARS)
                        frame_chars.append(FLIP_CHARS[current_idx])
            yield "".join(frame_chars)


# ── Weather generator ────────────────────────────────────────────────────────

def generate_weather():
    """Generate a random weather string for the board header.

    Returns:
        A string like '☀ Clear skies 24°C' suitable for display.
    """
    # Weighted random selection
    conditions = [c for c, _ in WEATHER_CONDITIONS]
    weights = [w for _, w in WEATHER_CONDITIONS]
    condition = random.choices(conditions, weights=weights, k=1)[0]
    low, high = WEATHER_TEMPS.get(condition, (10, 25))
    temp = random.randint(low, high)
    wind = random.randint(0, 30)
    visibility = random.choice(["Good", "Good", "Good", "Moderate", "Poor"])
    return f"{condition}  {temp}°C  Wind {wind}km/h  Vis: {visibility}"


# ── Departure Board ─────────────────────────────────────────────────────────

class DepartureBoard:
    """The main interactive departure/arrival board that runs in the terminal.

    Manages a list of Flight objects, advances simulated time, and renders
    the full board display including header, flight rows, announcements,
    and weather info.
    """

    COL_DEFS_DEPARTURES = [
        ("FLIGHT",       10),
        ("AIRLINE",      20),
        ("DESTINATION",  20),
        ("SCHED",         6),
        ("EST",           6),
        ("GATE",           5),
        ("TERM",           5),
        ("STATUS",        14),
    ]

    COL_DEFS_ARRIVALS = [
        ("FLIGHT",       10),
        ("AIRLINE",      20),
        ("ORIGIN",       20),
        ("SCHED",         6),
        ("EST",           6),
        ("BELT",           5),
        ("TERM",           5),
        ("STATUS",        14),
    ]

    SEPARATOR = "─"

    def __init__(self, num_flights=14, speed=1.0, animate=True,
                 filter_airline=None, filter_dest=None, no_color=False,
                 is_arrival=False, search_flight=None):
        """Initialize the departure board.

        Args:
            num_flights: Number of flights to display on the board.
            speed: Animation/progression speed multiplier (1.0 = normal).
            animate: Whether to use flip animation.
            filter_airline: Optional IATA airline code to filter by.
            filter_dest: Optional destination city name substring to filter by.
            no_color: If True, strip all ANSI color codes.
            is_arrival: If True, show arrivals instead of departures.
            search_flight: Optional flight number to search for (e.g. 'BA117').
        """
        self.num_flights = num_flights
        self.speed = speed
        self.animate = animate
        self.filter_airline = filter_airline.upper() if filter_airline else None
        self.filter_dest = filter_dest.lower() if filter_dest else None
        self.no_color = no_color
        self.is_arrival = is_arrival
        self.search_flight = search_flight.upper() if search_flight else None
        self.flip = FlipBoard(animate=animate)
        self.flights = []
        self.display_state = {}  # flight_id -> last displayed line
        self.now = datetime.now().replace(second=0, microsecond=0)
        self.weather = generate_weather()
        self.weather_change_counter = 0
        self.announcement_counter = 0
        self.announcement = random.choice(ANNOUNCEMENTS)
        self._generate_flights()

    @property
    def COL_DEFS(self):
        """Return column definitions based on board type (departure or arrival)."""
        return self.COL_DEFS_ARRIVALS if self.is_arrival else self.COL_DEFS_DEPARTURES

    def _generate_flights(self):
        """Generate initial flight set, respecting any active filters."""
        attempts = 0
        max_attempts = self.num_flights * 20  # be generous to find filter matches
        while len(self.flights) < self.num_flights * 3 and attempts < max_attempts:
            f = Flight(now=self.now, is_arrival=self.is_arrival)
            if self.filter_airline and f.airline_code != self.filter_airline:
                attempts += 1
                continue
            if self.filter_dest and self.filter_dest not in f.destination_name.lower():
                attempts += 1
                continue
            if self.search_flight and f.flight_no != self.search_flight:
                attempts += 1
                continue
            self.flights.append(f)
            attempts += 1

        if not self.flights and (self.filter_airline or self.filter_dest or self.search_flight):
            # If filters yielded no results, warn the user
            print(f"  ⚠ No flights found matching your filter criteria.")

        # Sort by scheduled time
        self.flights.sort(key=lambda f: f.scheduled)
        # Keep only the needed number
        self.flights = self.flights[:self.num_flights]

    def _fmt_time(self, dt):
        """Format a datetime as HH:MM.

        Args:
            dt: The datetime to format.

        Returns:
            String in HH:MM format.
        """
        return dt.strftime("%H:%M")

    def _format_flight_row(self, flight):
        """Format a flight into a list of fixed-width column strings.

        Args:
            flight: The Flight object to format.

        Returns:
            List of formatted column strings.
        """
        cols = [
            flight.flight_no[:10].ljust(10),
            flight.airline_name[:20].ljust(20),
            flight.destination_name[:20].ljust(20),
            self._fmt_time(flight.scheduled).ljust(6),
            self._fmt_time(flight.estimated).ljust(6),
        ]

        if flight.is_arrival:
            cols.append(flight.belt.ljust(5) if flight.belt else "  -- ".ljust(5))
        else:
            cols.append(flight.gate.ljust(5))

        cols.append(flight.terminal.ljust(5))
        cols.append(flight.status.ljust(14))
        return cols

    def _color_status(self, status, text):
        """Apply ANSI color codes to a status string based on its category.

        Args:
            status: The flight status string (e.g. 'BOARDING', 'CANCELLED').
            text: The text to colorize.

        Returns:
            The text wrapped in appropriate ANSI color codes.
        """
        if self.no_color:
            return text
        fg, bg = STATUS_COLORS.get(status, (FG["white"], BG["black"]))
        if status == "FINAL CALL":
            return f"{BOLD}{BLINK}{fg}{bg}{text}{RESET}"
        if status in ("CANCELLED", "DIVERTED"):
            return f"{BOLD}{fg}{bg}{text}{RESET}"
        if status in ("BOARDING", "DELAYED", "GATE CHANGE"):
            return f"{BOLD}{fg}{text}{RESET}"
        return f"{fg}{text}{RESET}"

    def _render_row(self, flight, frame_text=None):
        """Render a full row with color.

        Args:
            flight: The Flight object to render.
            frame_text: Optional animated frame text (unused currently).

        Returns:
            Formatted row string with ANSI colors.
        """
        cols = self._format_flight_row(flight)
        # Apply color to status
        cols[7] = self._color_status(flight.status, cols[7])
        return " │ ".join(cols) + " │"

    def _render_static_row(self, flight):
        """Render a flight row for static/non-animated display.

        Args:
            flight: The Flight object to render.

        Returns:
            Formatted row string with ANSI colors.
        """
        cols = self._format_flight_row(flight)
        cols[7] = self._color_status(flight.status, cols[7])
        return " │ ".join(cols)

    def _render_header(self, width):
        """Render the board header with column names and separators.

        Args:
            width: Total width of the display area.

        Returns:
            Multi-line string with the formatted header.
        """
        total_w = sum(w for _, w in self.COL_DEFS) + len(self.COL_DEFS) * 3 - 1
        header_cols = [name.ljust(w) for name, w in self.COL_DEFS]
        header_line = " │ ".join(header_cols)
        sep_line = self.SEPARATOR * total_w

        board_title = "  ✈  ARRIVALS" if self.is_arrival else "  ✈  DEPARTURES"

        lines = []
        if not self.no_color:
            lines.append(f"{BG['blue']}{FG['white']}{BOLD}{board_title}{' ' * max(0, total_w - len(board_title))}{RESET}")
        else:
            title_text = "ARRIVATIONS" if self.is_arrival else "DEPARTURES"
            lines.append(f"  ** {title_text} {' ' * max(0, total_w - len(title_text) - 6)}**")
        lines.append(sep_line)
        if not self.no_color:
            lines.append(f"{BOLD}{FG['cyan']}{header_line}{RESET}")
        else:
            lines.append(header_line)
        lines.append(sep_line)
        return "\n".join(lines)

    def _clear_screen(self):
        """Clear the terminal screen."""
        if not self.no_color:
            sys.stdout.write("\033[2J\033[H")
        else:
            sys.stdout.write("\n" * 2)

    def _move_cursor_top(self):
        """Move the terminal cursor to the top-left corner."""
        sys.stdout.write("\033[H")

    def run(self):
        """Main loop: render and update the board.

        Advances simulated time, updates flight statuses, replaces departed
        flights with new ones, and redraws the entire board. Runs until
        interrupted with Ctrl+C.
        """
        try:
            # Initial render
            self._clear_screen()
            sys.stdout.flush()

            frame_count = 0
            while True:
                # Advance simulation time
                self.now += timedelta(minutes=2 * self.speed)
                frame_count += 1

                # Update weather every 30 ticks (~1 hour of simulated time)
                self.weather_change_counter += 1
                if self.weather_change_counter >= 30:
                    self.weather = generate_weather()
                    self.weather_change_counter = 0

                # Rotate announcements every 10 ticks
                self.announcement_counter += 1
                if self.announcement_counter >= 10:
                    self.announcement = random.choice(ANNOUNCEMENTS)
                    self.announcement_counter = 0

                # Remove departed flights that have been shown for a while
                terminal_status = "DEPARTED" if not self.is_arrival else "ARRIVED"
                self.flights = [f for f in self.flights if f.status != terminal_status or
                                (self.now - f.scheduled).total_seconds() < 1800]
                # Add new flights if we're short
                refill_attempts = 0
                while len(self.flights) < self.num_flights and refill_attempts < 200:
                    f = Flight(now=self.now, is_arrival=self.is_arrival)
                    if self.filter_airline and f.airline_code != self.filter_airline:
                        refill_attempts += 1
                        continue
                    if self.filter_dest and self.filter_dest not in f.destination_name.lower():
                        refill_attempts += 1
                        continue
                    if self.search_flight and f.flight_no != self.search_flight:
                        refill_attempts += 1
                        continue
                    self.flights.append(f)
                    refill_attempts += 1
                self.flights.sort(key=lambda f: f.scheduled)
                self.flights = self.flights[:self.num_flights]

                # Tick all flights
                status_changed = []
                for f in self.flights:
                    if f.tick(self.now):
                        status_changed.append(f)

                # Build output
                self._clear_screen()

                # Clock and weather
                clock_str = self.now.strftime("%H:%M   %A, %d %b %Y")
                if not self.no_color:
                    print(f"{BOLD}{FG['white']}{BG['blue']}  {clock_str}{' ' * 20}{RESET}")
                    print(f"{FG['cyan']}  {self.weather}{RESET}")
                else:
                    print(f"  {clock_str}")
                    print(f"  {self.weather}")
                print()

                # Header
                print(self._render_header(sum(w for _, w in self.COL_DEFS)))
                print()

                # Flight rows
                for flight in self.flights:
                    row = self._render_static_row(flight)
                    print(f"  {row}")
                    if self.animate and flight in status_changed:
                        time.sleep(0.02 / self.speed)

                print()
                total_w = sum(w for _, w in self.COL_DEFS) + len(self.COL_DEFS) * 3 - 1
                sep = self.SEPARATOR * total_w
                print(sep)

                # Announcements (contextual per board type)
                # Collect contextual announcements based on board type
                boarding = [f for f in self.flights if f.status == "BOARDING"] if not self.is_arrival else []
                final = [f for f in self.flights if f.status == "FINAL CALL"] if not self.is_arrival else []
                cancelled = [f for f in self.flights if f.status == "CANCELLED"]
                landed = [f for f in self.flights if f.status == "LANDED"] if self.is_arrival else []

                if not self.no_color:
                    for f in boarding:
                        print(f"  {BOLD}{FG['yellow']}▶ NOW BOARDING: {f.flight_no} to {f.destination_name} — Gate {f.gate}{RESET}")
                    for f in final:
                        print(f"  {BOLD}{BLINK}{FG['red']}⚠ FINAL CALL: {f.flight_no} to {f.destination_name} — Gate {f.gate} ⚠{RESET}")
                    for f in landed:
                        print(f"  {BOLD}{FG['green']}● LANDED: {f.flight_no} from {f.destination_name} — Belt {f.belt}{RESET}")
                    for f in cancelled:
                        if self.is_arrival:
                            print(f"  {BOLD}{FG['white']}{BG['red']}✗ CANCELLED: {f.flight_no} from {f.destination_name}{RESET}")
                        else:
                            print(f"  {BOLD}{FG['white']}{BG['red']}✗ CANCELLED: {f.flight_no} to {f.destination_name} — Please contact airline{RESET}")
                else:
                    for f in boarding:
                        print(f"  >> BOARDING: {f.flight_no} to {f.destination_name} - Gate {f.gate}")
                    for f in final:
                        print(f"  !! FINAL CALL: {f.flight_no} to {f.destination_name} - Gate {f.gate}")
                    for f in landed:
                        print(f"  >> LANDED: {f.flight_no} from {f.destination_name} - Belt {f.belt}")
                    for f in cancelled:
                        if self.is_arrival:
                            print(f"  XX CANCELLED: {f.flight_no} from {f.destination_name}")
                        else:
                            print(f"  XX CANCELLED: {f.flight_no} to {f.destination_name}")

                # General airport announcement
                if not self.no_color:
                    print(f"{DIM}  📢 {self.announcement}{RESET}")
                else:
                    print(f"  [*] {self.announcement}")

                print()
                mode_label = "ARRIVALS" if self.is_arrival else "DEPARTURES"
                print(f"  {mode_label} board | Simulated time +{2*self.speed:.0f} min/tick | Press Ctrl+C to exit")

                sys.stdout.flush()
                time.sleep(2.0 / self.speed)

        except KeyboardInterrupt:
            print(f"\n\n{RESET}  Board closed. Safe travels! ✈\n")
            sys.exit(0)


# ── Flip animation demo mode ─────────────────────────────────────────────────

def run_flip_demo():
    """Standalone demo: show the flip-board character cycling effect."""
    print("Flip-Board Character Animation Demo")
    print("=" * 40)
    print()

    messages = [
        "FLIGHT BA117  LONDON HEATHROW  GATE A12",
        "NOW BOARDING  GATE C09  ON TIME",
        "DELAYED  EST 16:45  NEW GATE D04",
        "CANCELLED  PLEASE CONTACT AIRLINE",
        "FINAL CALL  GATE B07  ALL PASSENGERS",
    ]

    flip = FlipBoard(animate=True)
    old_line = " " * len(messages[0])

    for msg in messages:
        # Truncate/pad to same width
        msg = msg.ljust(len(messages[0]))[:len(messages[0])]
        for frame in flip.animate_line(old_line, msg, len(msg)):
            sys.stdout.write(f"\r  {frame}")
            sys.stdout.flush()
            time.sleep(0.008)
        old_line = msg
        time.sleep(0.5)

    print("\n")


# ── One-shot static display (for non-TTY / piped output) ────────────────────

def run_static_board(num_flights=14, filter_airline=None, filter_dest=None,
                     no_color=False, is_arrival=False, search_flight=None):
    """Print a single static snapshot of the departure/arrival board.

    Args:
        num_flights: Number of flights to show.
        filter_airline: Optional airline code filter.
        filter_dest: Optional destination city filter.
        no_color: Whether to suppress ANSI colors.
        is_arrival: Whether to show arrivals instead of departures.
        search_flight: Optional flight number to search for.
    """
    now = datetime.now().replace(second=0, microsecond=0)
    flights = []
    attempts = 0
    max_attempts = num_flights * 20
    while len(flights) < num_flights and attempts < max_attempts:
        f = Flight(now=now, is_arrival=is_arrival)
        if filter_airline and f.airline_code != filter_airline.upper():
            attempts += 1
            continue
        if filter_dest and filter_dest.lower() not in f.destination_name.lower():
            attempts += 1
            continue
        if search_flight and f.flight_no != search_flight.upper():
            attempts += 1
            continue
        # Tick to generate some variety
        for _ in range(random.randint(0, 5)):
            f.tick(now - timedelta(minutes=random.randint(1, 30)))
        flights.append(f)
        attempts += 1

    if not flights:
        print("No flights found matching your criteria.")
        return

    flights.sort(key=lambda f: f.scheduled)
    flights = flights[:num_flights]

    COL_DEFS = DepartureBoard.COL_DEFS_ARRIVALS if is_arrival else DepartureBoard.COL_DEFS_DEPARTURES
    total_w = sum(w for _, w in COL_DEFS) + len(COL_DEFS) * 3 - 1

    clock_str = now.strftime("%H:%M   %A, %d %b %Y")
    title = "ARRIVALS" if is_arrival else "DEPARTURES"
    if not no_color:
        print(f"{BOLD}{FG['white']}{BG['blue']}  ✈  {title}  —  {clock_str}{' ' * 10}✈  {RESET}")
    else:
        print(f"  ** {title} — {clock_str} **")

    print("─" * total_w)
    header_cols = [name.ljust(w) for name, w in COL_DEFS]
    print(" │ ".join(header_cols))
    print("─" * total_w)

    for f in flights:
        cols = [
            f.flight_no[:10].ljust(10),
            f.airline_name[:20].ljust(20),
            f.destination_name[:20].ljust(20),
            f.scheduled.strftime("%H:%M").ljust(6),
            f.estimated.strftime("%H:%M").ljust(6),
        ]
        if f.is_arrival:
            cols.append(f.belt.ljust(5) if f.belt else "  -- ".ljust(5))
        else:
            cols.append(f.gate.ljust(5))
        cols.append(f.terminal.ljust(5))
        cols.append(f.status.ljust(14))
        if not no_color:
            fg, bg = STATUS_COLORS.get(f.status, (FG["white"], BG["black"]))
            cols[7] = f"{BOLD}{fg}{bg}{cols[7]}{RESET}"
        print(" │ ".join(cols))

    print("─" * total_w)
    print()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    """Entry point: parse arguments and launch the board."""
    parser = argparse.ArgumentParser(
        description="✈ Terminal Airport Departure Board — animated flip-board style FIDS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python departure_board.py                     # live animated board
  python departure_board.py --compact           # fewer rows
  python departure_board.py --fast              # faster updates & animation
  python departure_board.py --arrivals          # show arrivals board
  python departure_board.py --filter BA         # British Airways only
  python departure_board.py --destination Tokyo  # Tokyo flights only
  python departure_board.py --flight BA117      # search for specific flight
  python departure_board.py --static            # one-shot print (no animation)
  python departure_board.py --demo              # flip animation demo only
  python departure_board.py --no-color          # no ANSI colors
        """,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--compact", action="store_true", help="Show fewer flights (8)")
    parser.add_argument("--fast", action="store_true", help="Faster animation and time progression")
    parser.add_argument("--slow", action="store_true", help="Slower animation and time progression")
    parser.add_argument("--no-animate", action="store_true", help="Disable flip animation")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    parser.add_argument("--arrivals", action="store_true", help="Show arrivals board instead of departures")
    parser.add_argument("--filter", metavar="AIRLINE_CODE", help="Filter by airline code (e.g. BA, UA)")
    parser.add_argument("--destination", metavar="CITY", help="Filter by destination city")
    parser.add_argument("--flight", metavar="FLIGHT_NO", help="Search for a specific flight number (e.g. BA117)")
    parser.add_argument("--static", action="store_true", help="Print a single snapshot and exit")
    parser.add_argument("--demo", action="store_true", help="Run flip animation demo")
    parser.add_argument("--flights", type=int, default=14, help="Number of flights to display")

    args = parser.parse_args()

    num_flights = 8 if args.compact else args.flights
    speed = 2.0 if args.fast else (0.5 if args.slow else 1.0)

    if args.demo:
        run_flip_demo()
        return

    if args.static:
        no_color = args.no_color
        if not sys.stdout.isatty():
            no_color = True
        run_static_board(
            num_flights=num_flights,
            filter_airline=args.filter,
            filter_dest=args.destination,
            no_color=no_color,
            is_arrival=args.arrivals,
            search_flight=args.flight,
        )
        return

    # Live board — requires a TTY
    if not sys.stdout.isatty():
        # Fall back to static mode for non-interactive terminals
        run_static_board(
            num_flights=num_flights,
            filter_airline=args.filter,
            filter_dest=args.destination,
            no_color=True,
            is_arrival=args.arrivals,
            search_flight=args.flight,
        )
        return

    board = DepartureBoard(
        num_flights=num_flights,
        speed=speed,
        animate=not args.no_animate,
        filter_airline=args.filter,
        filter_dest=args.destination,
        no_color=args.no_color,
        is_arrival=args.arrivals,
        search_flight=args.flight,
    )
    board.run()


if __name__ == "__main__":
    main()