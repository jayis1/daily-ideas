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
  - Flight search/filter by destination or airline
  - ASCII art airport sign header
  - Sound-bell on boarding announcements (optional)

Usage:
  python departure_board.py              # full board, default refresh
  python departure_board.py --compact     # fewer rows
  python departure_board.py --fast        # faster animation & updates
  python departure_board.py --filter BA   # show only British Airways flights
  python departure_board.py --destination Tokyo  # filter by destination
  python departure_board.py --no-animate  # skip flip animation (instant)
  python departure_board.py --help        # full options
"""

import random
import time
import sys
import argparse
import shutil
import itertools
from datetime import datetime, timedelta

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
}

# ── Flight data pools ────────────────────────────────────────────────────────

AIRLINES = [
    ("BA", "BRITISH AIRWAYS",   "🇬🇧"),
    ("AA", "AMERICAN AIRLINES",  "🇺🇸"),
    ("UA", "UNITED AIRLINES",    "🇺🇸"),
    ("DL", "DELTA AIR LINES",    "🇺🇸"),
    ("LH", "LUFTHANSA",          "🇩🇪"),
    ("AF", "AIR FRANCE",         "🇫🇷"),
    ("EK", "EMIRATES",           "🇦🇪"),
    ("SQ", "SINGAPORE AIRLINES", "🇸🇬"),
    ("QF", "QANTAS",             "🇦🇺"),
    ("JL", "JAPAN AIRLINES",     "🇯🇵"),
    ("CX", "CATHAY PACIFIC",    "🇭🇰"),
    ("TK", "TURKISH AIRLINES",  "🇹🇷"),
    ("NH", "ALL NIPPON AIRWAYS", "🇯🇵"),
    ("SK", "SAS SCANDINAVIAN",  "🇸🇪"),
    ("IB", "IBERIA",            "🇪🇸"),
    ("KL", "KLM ROYAL DUTCH",   "🇳🇱"),
    ("ET", "ETHIOPIAN AIRLINES", "🇪🇹"),
    ("QR", "QATAR AIRWAYS",     "🇶🇦"),
    ("EY", "ETIHAD AIRWAYS",    "🇦🇪"),
    ("VS", "VIRGIN ATLANTIC",   "🇬🇧"),
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
    ("Bangkok",           "BKK"),
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
    ("Beijing Capital",    "PEK"),
    ("Shanghai Pudong",    "PVG"),
    ("Taipei Taoyuan",     "TPE"),
    ("Melbourne",          "MEL"),
]

GATES = [f"{letter}{num}" for letter in "ABCDEF" for num in range(1, 16)]

TERMINALS = ["T1", "T2", "T3", "T4", "T5"]

# Characters used in flip animation (sorted for visual sweep)
FLIP_CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:-/."

# ── Flight class ─────────────────────────────────────────────────────────────

class Flight:
    _counter = itertools.count(100)

    def __init__(self, now=None):
        self.flight_id = next(Flight._counter)
        airline_code, airline_name, _ = random.choice(AIRLINES)
        self.airline_code = airline_code
        self.airline_name = airline_name
        dest_name, dest_code = random.choice(DESTINATIONS)
        self.destination_name = dest_name
        self.destination_code = dest_code
        self.flight_no = f"{airline_code}{random.randint(100, 9999)}"
        self.terminal = random.choice(TERMINALS)
        self.gate = random.choice(GATES)
        self.status = "ON TIME"
        # Scheduled time sometime in the next few hours
        offset = random.randint(10, 360)
        self.scheduled = (now or datetime.now()) + timedelta(minutes=offset)
        self.estimated = self.scheduled
        self._next_event_time = self.scheduled - timedelta(minutes=random.randint(5, 45))
        self._cancelled = False

    def tick(self, now):
        """Advance the flight state based on current time. Returns True if status changed."""
        old_status = self.status
        mins_to_departure = (self.scheduled - now).total_seconds() / 60

        if self._cancelled:
            return False

        # Decide random events
        if now >= self._next_event_time:
            event_roll = random.random()
            if mins_to_departure < 0:
                self.status = "DEPARTED"
            elif mins_to_departure < 10 and self.status == "BOARDING":
                if event_roll < 0.3:
                    self.status = "FINAL CALL"
                else:
                    self._next_event_time = now + timedelta(minutes=random.randint(3, 8))
            elif mins_to_departure < 20 and self.status in ("ON TIME", "GATE OPEN"):
                if event_roll < 0.6:
                    self.status = "BOARDING"
                elif event_roll < 0.8:
                    self.status = "GATE OPEN"
                self._next_event_time = now + timedelta(minutes=random.randint(3, 10))
            elif mins_to_departure < 40:
                if event_roll < 0.15 and self.status == "ON TIME":
                    self.status = "DELAYED"
                    delay = random.randint(15, 90)
                    self.estimated = self.scheduled + timedelta(minutes=delay)
                elif event_roll < 0.05:
                    self.status = "CANCELLED"
                    self._cancelled = True
                elif event_roll < 0.08 and self.status != "CANCELLED":
                    self.gate = random.choice(GATES)
                    self.status = "GATE CHANGE"
                self._next_event_time = now + timedelta(minutes=random.randint(5, 20))
            else:
                # Far out — occasional delay
                if event_roll < 0.08 and self.status == "ON TIME":
                    self.status = "DELAYED"
                    delay = random.randint(20, 120)
                    self.estimated = self.scheduled + timedelta(minutes=delay)
                self._next_event_time = now + timedelta(minutes=random.randint(10, 30))

        return self.status != old_status


# ── Flip-board display engine ────────────────────────────────────────────────

class FlipBoard:
    """Handles the character-cycling flip animation for a row of text."""

    def __init__(self, animate=True):
        self.animate = animate

    @staticmethod
    def flip_distance(current, target):
        """Number of flip steps between current and target char."""
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
        """Yield intermediate frames for flip animation."""
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


# ── Departure Board ─────────────────────────────────────────────────────────

class DepartureBoard:
    HEADER = r"""
  ╔══════════════════════════════════════════════════════════════════════════════╗
  ║                                                                              ║
  ║     ✈  D E P A R T U R E S   B O A R D   ✈                                  ║
  ║                                                                              ║
  ╚══════════════════════════════════════════════════════════════════════════════╝
"""

    COL_DEFS = [
        ("FLIGHT",    10),
        ("AIRLINE",   20),
        ("DESTINATION", 20),
        ("SCHED",      6),
        ("EST",        6),
        ("GATE",        5),
        ("TERM",        5),
        ("STATUS",     14),
    ]

    SEPARATOR = "─"

    def __init__(self, num_flights=14, speed=1.0, animate=True,
                 filter_airline=None, filter_dest=None, no_color=False):
        self.num_flights = num_flights
        self.speed = speed
        self.animate = animate
        self.filter_airline = filter_airline.upper() if filter_airline else None
        self.filter_dest = filter_dest.lower() if filter_dest else None
        self.no_color = no_color
        self.flip = FlipBoard(animate=animate)
        self.flights = []
        self.display_state = {}  # flight_id -> last displayed line
        self.now = datetime.now().replace(second=0, microsecond=0)
        self._generate_flights()

    def _generate_flights(self):
        """Generate initial flight set."""
        attempts = 0
        while len(self.flights) < self.num_flights * 3 and attempts < 200:
            f = Flight(now=self.now)
            if self.filter_airline and f.airline_code != self.filter_airline:
                attempts += 1
                continue
            if self.filter_dest and self.filter_dest not in f.destination_name.lower():
                attempts += 1
                continue
            self.flights.append(f)
            attempts += 1
        # Sort by scheduled time
        self.flights.sort(key=lambda f: f.scheduled)
        # Keep only the needed number
        self.flights = self.flights[:self.num_flights]

    def _fmt_time(self, dt):
        return dt.strftime("%H:%M")

    def _format_flight_row(self, flight):
        """Format a flight into a fixed-width row string."""
        cols = [
            flight.flight_no[:10].ljust(10),
            flight.airline_name[:20].ljust(20),
            flight.destination_name[:20].ljust(20),
            self._fmt_time(flight.scheduled).ljust(6),
            self._fmt_time(flight.estimated).ljust(6),
            flight.gate.ljust(5),
            flight.terminal.ljust(5),
            flight.status.ljust(14),
        ]
        return cols

    def _color_status(self, status, text):
        if self.no_color:
            return text
        fg, bg = STATUS_COLORS.get(status, (FG["white"], BG["black"]))
        if status == "FINAL CALL":
            return f"{BOLD}{BLINK}{fg}{bg}{text}{RESET}"
        if status == "CANCELLED":
            return f"{BOLD}{fg}{bg}{text}{RESET}"
        if status in ("BOARDING", "DELAYED", "GATE CHANGE"):
            return f"{BOLD}{fg}{text}{RESET}"
        return f"{fg}{text}{RESET}"

    def _render_row(self, flight, frame_text=None):
        """Render a full row with color."""
        if frame_text:
            # During animation, we show the animated text monochrome
            # but color the status column separately at the end
            pass
        cols = self._format_flight_row(flight)
        # Apply color to status
        cols[7] = self._color_status(flight.status, cols[7])
        return " │ ".join(cols) + " │"

    def _render_static_row(self, flight):
        cols = self._format_flight_row(flight)
        cols[7] = self._color_status(flight.status, cols[7])
        return " │ ".join(cols)

    def _render_header(self, width):
        total_w = sum(w for _, w in self.COL_DEFS) + len(self.COL_DEFS) * 3 - 1
        header_cols = [name.ljust(w) for name, w in self.COL_DEFS]
        header_line = " │ ".join(header_cols)
        sep_line = self.SEPARATOR * total_w
        lines = []
        if not self.no_color:
            lines.append(f"{BG['blue']}{FG['white']}{BOLD}  ✈  DEPARTURES{' ' * (total_w - 14)}✈  {RESET}")
        else:
            lines.append(f"  ** DEPARTURES {' ' * (total_w - 18)}**")
        lines.append(sep_line)
        if not self.no_color:
            lines.append(f"{BOLD}{FG['cyan']}{header_line}{RESET}")
        else:
            lines.append(header_line)
        lines.append(sep_line)
        return "\n".join(lines)

    def _clear_screen(self):
        if not self.no_color:
            sys.stdout.write("\033[2J\033[H")
        else:
            sys.stdout.write("\n" * 2)

    def _move_cursor_top(self):
        sys.stdout.write("\033[H")

    def run(self):
        """Main loop: render and update the board."""
        try:
            # Initial render
            self._clear_screen()
            sys.stdout.flush()

            frame_count = 0
            while True:
                # Advance simulation time
                self.now += timedelta(minutes=2 * self.speed)
                frame_count += 1

                # Occasionally add a new flight to replace departed ones
                self.flights = [f for f in self.flights if f.status != "DEPARTED" or
                                (self.now - f.scheduled).total_seconds() < 1800]
                # Add new flights if we're short
                while len(self.flights) < self.num_flights:
                    f = Flight(now=self.now)
                    if self.filter_airline and f.airline_code != self.filter_airline:
                        continue
                    if self.filter_dest and self.filter_dest not in f.destination_name.lower():
                        continue
                    self.flights.append(f)
                self.flights.sort(key=lambda f: f.scheduled)
                self.flights = self.flights[:self.num_flights]

                # Tick all flights
                status_changed = []
                for f in self.flights:
                    if f.tick(self.now):
                        status_changed.append(f)

                # Build output
                self._clear_screen()

                # Clock
                clock_str = self.now.strftime("%H:%M   %A, %d %b %Y")
                if not self.no_color:
                    print(f"{BOLD}{FG['white']}{BG['blue']}  {clock_str}{' ' * 20}{RESET}")
                else:
                    print(f"  {clock_str}")
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

                # Announcements
                boarding = [f for f in self.flights if f.status == "BOARDING"]
                final = [f for f in self.flights if f.status == "FINAL CALL"]
                cancelled = [f for f in self.flights if f.status == "CANCELLED"]

                if not self.no_color:
                    for f in boarding:
                        print(f"  {BOLD}{FG['yellow']}▶ NOW BOARDING: {f.flight_no} to {f.destination_name} — Gate {f.gate}{RESET}")
                    for f in final:
                        print(f"  {BOLD}{BLINK}{FG['red']}⚠ FINAL CALL: {f.flight_no} to {f.destination_name} — Gate {f.gate} ⚠{RESET}")
                    for f in cancelled:
                        print(f"  {BOLD}{FG['white']}{BG['red']}✗ CANCELLED: {f.flight_no} to {f.destination_name} — Please contact airline{RESET}")
                else:
                    for f in boarding:
                        print(f"  >> BOARDING: {f.flight_no} to {f.destination_name} - Gate {f.gate}")
                    for f in final:
                        print(f"  !! FINAL CALL: {f.flight_no} to {f.destination_name} - Gate {f.gate}")
                    for f in cancelled:
                        print(f"  XX CANCELLED: {f.flight_no} to {f.destination_name}")

                print()
                print(f"  Simulated time advancing +{2*self.speed:.0f} min/tick | Press Ctrl+C to exit")

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

def run_static_board(num_flights=14, filter_airline=None, filter_dest=None, no_color=False):
    """Print a single static snapshot of the departure board."""
    now = datetime.now().replace(second=0, microsecond=0)
    flights = []
    attempts = 0
    while len(flights) < num_flights and attempts < 300:
        f = Flight(now=now)
        if filter_airline and f.airline_code != filter_airline.upper():
            attempts += 1
            continue
        if filter_dest and filter_dest.lower() not in f.destination_name.lower():
            attempts += 1
            continue
        # Tick to generate some variety
        for _ in range(random.randint(0, 5)):
            f.tick(now - timedelta(minutes=random.randint(1, 30)))
        flights.append(f)
        attempts += 1

    flights.sort(key=lambda f: f.scheduled)
    flights = flights[:num_flights]

    COL_DEFS = DepartureBoard.COL_DEFS
    total_w = sum(w for _, w in COL_DEFS) + len(COL_DEFS) * 3 - 1

    clock_str = now.strftime("%H:%M   %A, %d %b %Y")
    if not no_color:
        print(f"{BOLD}{FG['white']}{BG['blue']}  ✈  DEPARTURES  —  {clock_str}{' ' * 10}✈  {RESET}")
    else:
        print(f"  ** DEPARTURES — {clock_str} **")

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
            f.gate.ljust(5),
            f.terminal.ljust(5),
            f.status.ljust(14),
        ]
        if not no_color:
            fg, bg = STATUS_COLORS.get(f.status, (FG["white"], BG["black"]))
            cols[7] = f"{BOLD}{fg}{bg}{cols[7]}{RESET}"
        print(" │ ".join(cols))

    print("─" * total_w)
    print()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="✈ Terminal Airport Departure Board — animated flip-board style FIDS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python departure_board.py                     # live animated board
  python departure_board.py --compact           # fewer rows
  python departure_board.py --fast              # faster updates & animation
  python departure_board.py --filter BA         # British Airways only
  python departure_board.py --destination Tokyo  # Tokyo flights only
  python departure_board.py --static             # one-shot print (no animation)
  python departure_board.py --demo               # flip animation demo only
  python departure_board.py --no-color           # no ANSI colors
        """,
    )
    parser.add_argument("--compact", action="store_true", help="Show fewer flights (8)")
    parser.add_argument("--fast", action="store_true", help="Faster animation and time progression")
    parser.add_argument("--slow", action="store_true", help="Slower animation and time progression")
    parser.add_argument("--no-animate", action="store_true", help="Disable flip animation")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    parser.add_argument("--filter", metavar="AIRLINE_CODE", help="Filter by airline code (e.g. BA, UA)")
    parser.add_argument("--destination", metavar="CITY", help="Filter by destination city")
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
        )
        return

    # Live board — requires a TTY
    if not sys.stdout.isatty():
        # Fall back to static
        run_static_board(
            num_flights=num_flights,
            filter_airline=args.filter,
            filter_dest=args.destination,
            no_color=True,
        )
        return

    board = DepartureBoard(
        num_flights=num_flights,
        speed=speed,
        animate=not args.no_animate,
        filter_airline=args.filter,
        filter_dest=args.destination,
        no_color=args.no_color,
    )
    board.run()


if __name__ == "__main__":
    main()