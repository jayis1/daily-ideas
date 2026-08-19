#!/usr/bin/env python3
"""
ASCII Morse Broadcasting Station
================================
A terminal-based simulation of a vintage shortwave radio station
broadcasting Morse code. Run it, and it continuously cycles through:
  1. Station ID call sign in Morse code
  2. Random news headlines from a built-in generator
  3. Weather reports
  4. Emergency alerts (occasionally)
  5. Dead air / static between segments

Audio is generated using the sine wave tone from the 'math' module
combined with the 'ossaudiodev' or 'wave' write. However, since this
is a terminal tool, we use the PC speaker/beep via 'os.system("tput bel")'
and also generate a WAV file that can be played optionally.

Morse code timing (PARIS standard):
  - Dot duration = 1 unit
  - Dash duration = 3 units
  - Intra-character gap = 1 unit
  - Inter-character gap = 3 units
  - Inter-word gap = 7 units
  - PARIS = 50 units, so at 20 WPM, 1 unit = 60ms / (20*50/60) = ...

We use a default 20 WPM. Each dot is 60ms.
"""

import os
import sys
import time
import random
import threading
import argparse
import math
import wave
import struct
import textwrap
from datetime import datetime

# Morse code lookup table
MORSE_CODE = {
    'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.',
    'F': '..-.', 'G': '--.', 'H': '....', 'I': '..', 'J': '.---',
    'K': '-.-', 'L': '.-..', 'M': '--', 'N': '-.', 'O': '---',
    'P': '.--.', 'Q': '--.-', 'R': '.-.', 'S': '...', 'T': '-',
    'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-', 'Y': '-.--',
    'Z': '--..',
    '0': '-----', '1': '.----', '2': '..---', '3': '...--',
    '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..', '9': '----.',
    '.': '.-.-.-', ',': '--..--', '?': '..--..', "'": '.----.',
    '!': '-.-.--', '/': '-..-.', '(': '-.--.', ')': '-.--.-',
    '&': '.-...', ':': '---...', ';': '-.-.-.', '=': '-...-',
    '+': '.-.-.', '-': '-....-', '_': '..--.-', '"': '.-..-.',
    '$': '...-..-', '@': '.--.-.',
    ' ': '/'
}

REVERSE_MORSE = {v: k for k, v in MORSE_CODE.items()}

# Call signs
CALL_SIGNS = [
    "WBSQ", "KXRT", "WNOR", "KVQX", "WABC", "KQED", "WBZR", "KLOS",
    "WCBS", "KPFA", "WINS", "KGO", "WQXR", "KCBS", "WGY", "KFI",
    "WOR", "KNX", "WNYC", "KCRW"
]

# News headline templates
NEWS_TEMPLATES = [
    "MARKETS RALLY AS DOW HITS RECORD HIGH",
    "STORM WARNINGS ISSUED FOR COASTAL AREAS",
    "SCIENTISTS DISCOVER NEW COMET APPROACHING EARTH",
    "LOCAL TEAM WINS CHAMPIONSHIP IN OVERTIME THRILLER",
    "CITY COUNCIL APPROVES NEW BRIDGE CONSTRUCTION",
    "RARE ECLIPSE VISIBLE ACROSS NORTHERN HEMISPHERE",
    "TEMPERATURES PLUMMET AS COLD FRONT MOVES IN",
    "NEW RAIL LINE OPENS CONNECTING TWO MAJOR CITIES",
    "ANCIENT RUINS DISCOVERED NEAR DESERT OASIS",
    "SHIPS ARRIVE IN PORT CARRYING EXOTIC CARGO",
    "FARMERS REPORT BUMPER CROP THIS SEASON",
    "RADIO AMATEURS SET NEW DISTANCE COMMUNICATION RECORD",
    "EXPLORERS RETURN FROM ARCTIC EXPEDITION SAFELY",
    "LIBRARY UNVEILS RARE MANUSCRIPT COLLECTION",
    "CLOCK TOWER RESTORATION PROJECT COMPLETED",
    "MIGRATING BIRDS SPOTTED OVER SOUTHERN FIELDS",
    "POWER RESTORED AFTER STORM OUTAGE",
    "NEW VACCINE SHOWS PROMISING RESULTS",
    "CONGRESS PASSES TARIFF BILL AFTER DEBATE",
    "STEAMSHIP DEPARTS ON MAIDEN VOYAGE TODAY",
    "MINERS RESCUED AFTER CAVE IN",
    "TROOPS RETURN HOME TO TICKER TAPE PARADE",
    "INVENTOR DEMONSTRATES WIRELESS TELEGRAPHY",
    "METEOR SHOWER EXPECTED TONIGHT AFTER MIDNIGHT",
    "DIPLOMATIC TALKS YIELD SURPRISE AGREEMENT",
    "HARVEST FESTIVAL DRAWS THOUSANDS TO TOWN SQUARE",
    "BALLOONIST CROSSES CHANNEL IN RECORD TIME",
    "POSTAL SERVICE ANNOUNCES NEW AIRMAIL ROUTE",
    "UNIVERSITY AWARDS HONORARY DEGREES",
    "HOT SPELL CONTINUES ACROSS PLAINS STATES",
    "FISHING FLEET RETURNS WITH FULL HOLD",
    "OBSTACLE COURSE RECORD BROKEN AT GAMES",
    "PILOT LANDS SAFELY AFTER GEAR FAILURE",
    "SUBMARINE COMPLETES ARCTIC TRANSIT",
    "RARE ORCHID BLOOMS AT BOTANICAL GARDENS",
    "BRIDGE TOLL REDUCED BY POPULAR DEMAND",
    "COMET STREAKS ACROSS NORTHERN SKY TONIGHT",
    "TROLLEY SERVICE RESUMES ON MAIN LINE",
    "BANK ROBBER CAUGHT AFTER CITY CHASE",
    "AIRSHIP DOCKS AT MAST AFTER SMOOTH FLIGHT",
    "FORTUNE TELLER PREDICTS EARLY SPRING"
]

WEATHER_TEMPLATES = [
    "CLEAR SKIES PREVAIL TEMPERATURE 72",
    "PARTLY CLOUDY LIGHT BREEZE TEMP 68",
    "OVERCAST RAIN EXPECTED BY NOON TEMP 55",
    "FOGY VISIBILITY LOW TEMP 48",
    "HEAT WAVE CONTINUES HIGH OF 95",
    "COOL FRONT APPROACHING WINDS 15 KNOTS",
    "FAIR WEATHER BAROMETER 30 POINT 02 INCHES",
    "SCATTERED THUNDERSTORMS AFTERNOON TEMP 78",
    "SNOW FLURRIES EXPECTED OVERNIGHT LOW 32",
    "HUMID CONDITIONS DEW POINT 70",
    "NORTHERLY WINDS 20 KNOTS TEMP 45",
    "CLEAR AND MILD TONIGHTS LOW 50",
    "TROPICAL STORM WATCH EFFECTIVE",
    "FROST WARNING ISSUED FOR INLAND AREAS",
    "SUNNY WITH LIGHT CLOUDS TEMP 75",
    "WINDS VEERING SOUTHWEST BAROMETER FALLING"
]

EMERGENCY_TEMPLATES = [
    "ATTENTION ALL STATIONS SEVERE WEATHER WARNING",
    "EMERGENCY ALERT FLOOD WARNING IN EFFECT",
    "URGENT NOTICE HURRICANE APPROACHING COAST",
    "WARNING TORNADO SIGHTED MOVE TO SHELTER",
    "ALERT FOREST FIRE SPREADING EVACUATE NOW",
    "ATTENTION AIR RAID PRECAUTION STAND BY",
    "EMERGENCY SHIP IN DISTRESS REQUESTING ASSISTANCE",
    "URGENT MEDICAL SUPPLIES NEEDED URGENTLY"
]

STATIC_PHRASES = [
    "QSL QSL",
    "QTH?",
    "QRX",
    "QRM",
    "QSB",
    "CQ CQ CQ",
    "DE",
    "K",
    "AR",
    "SK",
]

PHONETIC_ALPHABET = {
    'A': 'ALFA', 'B': 'BRAVO', 'C': 'CHARLIE', 'D': 'DELTA',
    'E': 'ECHO', 'F': 'FOXTROT', 'G': 'GOLF', 'H': 'HOTEL',
    'I': 'INDIA', 'J': 'JULIET', 'K': 'KILO', 'L': 'LIMA',
    'M': 'MIKE', 'N': 'NOVEMBER', 'O': 'OSCAR', 'P': 'PAPA',
    'Q': 'QUEBEC', 'R': 'ROMEO', 'S': 'SIERRA', 'T': 'TANGO',
    'U': 'UNIFORM', 'V': 'VICTOR', 'W': 'WHISKEY', 'X': 'XRAY',
    'Y': 'YANKEE', 'Z': 'ZULU', '0': 'ZERO', '1': 'ONE',
    '2': 'TWO', '3': 'THREE', '4': 'FOUR', '5': 'FIVE',
    '6': 'SIX', '7': 'SEVEN', '8': 'EIGHT', '9': 'NINE'
}


# ============================================================
# ANSI Color helpers
# ============================================================
class Color:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BG_BLACK = '\033[40m'
    BG_BLUE = '\033[44m'
    BG_CYAN = '\033[46m'
    BG_GREEN = '\033[42m'
    BG_RED = '\033[41m'
    BG_YELLOW = '\033[43m'
    BG_WHITE = '\033[47m'
    BG_MAGENTA = '\033[45m'
    BG_BLACK_BRIGHT = '\033[100m'
    BG_RED_BRIGHT = '\033[101m'
    BG_GREEN_BRIGHT = '\033[102m'
    BG_YELLOW_BRIGHT = '\033[103m'
    BG_BLUE_BRIGHT = '\033[104m'
    BG_MAGENTA_BRIGHT = '\033[105m'
    BG_CYAN_BRIGHT = '\033[106m'
    BG_WHITE_BRIGHT = '\033[107m'


# ============================================================
# Terminal control helpers
# ============================================================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def hide_cursor():
    sys.stdout.write('\033[?25l')
    sys.stdout.flush()


def show_cursor():
    sys.stdout.write('\033[?25h')
    sys.stdout.flush()


def move_to(row, col):
    sys.stdout.write(f'\033[{row};{col}H')
    sys.stdout.flush()


def save_cursor():
    sys.stdout.write('\033[s')
    sys.stdout.flush()


def restore_cursor():
    sys.stdout.write('\033[u')
    sys.stdout.flush()


# ============================================================
# Morse Code Engine
# ============================================================
class MorseEngine:
    """Handles Morse code encoding/decoding and timing."""

    def __init__(self, wpm=20, freq=600):
        self.wpm = wpm
        self.freq = freq
        # Dot duration in ms: 1200/WPM (PARIS standard)
        self.dot_ms = 1200.0 / wpm
        self.dash_ms = self.dot_ms * 3
        self.intra_char_gap_ms = self.dot_ms
        self.inter_char_gap_ms = self.dot_ms * 3
        self.inter_word_gap_ms = self.dot_ms * 7

    def text_to_morse(self, text):
        """Convert text to Morse code string. Returns list of (char, morse) tuples."""
        result = []
        for char in text.upper():
            if char in MORSE_CODE:
                result.append((char, MORSE_CODE[char]))
            elif char == ' ':
                result.append((' ', '/'))
            # Ignore unknown characters
        return result

    def morse_to_text(self, morse_str):
        """Convert Morse code back to text."""
        words = morse_str.split(' / ')
        result = []
        for word in words:
            chars = word.strip().split(' ')
            for c in chars:
                if c in REVERSE_MORSE:
                    result.append(REVERSE_MORSE[c])
            result.append(' ')
        return ''.join(result).strip()


# ============================================================
# WAV Audio Generator
# ============================================================
def generate_morse_wav(text, wpm=20, freq=600, filename='broadcast.wav'):
    """Generate a WAV file containing Morse code audio."""
    engine = MorseEngine(wpm=wpm, freq=freq)
    morse_pairs = engine.text_to_morse(text)

    sample_rate = 8000
    samples = []

    def add_tone(duration_ms):
        n_samples = int(sample_rate * duration_ms / 1000)
        for i in range(n_samples):
            # Apply fade in/out envelope to avoid clicks
            t = i / sample_rate
            envelope = 1.0
            fade_samples = min(int(sample_rate * 0.005), n_samples // 4)
            if i < fade_samples:
                envelope = i / fade_samples
            elif i > n_samples - fade_samples:
                envelope = (n_samples - i) / fade_samples
            val = int(32767 * 0.3 * envelope * math.sin(2 * math.pi * freq * t))
            samples.append(struct.pack('<h', val))

    def add_silence(duration_ms):
        n_samples = int(sample_rate * duration_ms / 1000)
        for i in range(n_samples):
            samples.append(struct.pack('<h', 0))

    for char, morse in morse_pairs:
        if morse == '/':
            add_silence(engine.inter_word_gap_ms)
            continue
        for symbol in morse:
            if symbol == '.':
                add_tone(engine.dot_ms)
            elif symbol == '-':
                add_tone(engine.dash_ms)
            add_silence(engine.intra_char_gap_ms)
        add_silence(engine.inter_char_gap_ms - engine.intra_char_gap_ms)

    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(samples))

    return filename


# ============================================================
# Radio Receiver UI
# ============================================================
class RadioDisplay:
    """Renders the radio receiver interface."""

    def __init__(self, call_sign):
        self.call_sign = call_sign
        self.signal_strength = 0
        self.frequency = random.choice([
            "5.850", "7.250", "14.020", "21.150", "28.500",
            "3.750", "10.100", "18.100", "24.890", "1.825"
        ])
        self.mode = "CW"
        self.band = "SHORTWAVE"
        self.s_meter = 0
        self.tuned = True
        self.static_phase = 0
        self.broadcast_log = []
        self.morse_display = []
        self.decoded_text = ""
        self.current_segment = "IDLE"
        self.signal_bar_width = 40
        self.last_update = time.time()

    def _box(self, row, col, width, height, title=""):
        """Draw a box border."""
        top = '┌' + '─' * (width - 2) + '┐'
        bot = '└' + '─' * (width - 2) + '┘'
        move_to(row, col)
        sys.stdout.write(top)
        move_to(row + height - 1, col)
        sys.stdout.write(bot)
        for r in range(1, height - 1):
            move_to(row + r, col)
            sys.stdout.write('│')
            move_to(row + r, col + width - 1)
            sys.stdout.write('│')
        if title:
            move_to(row, col + 3)
            sys.stdout.write(f' {title} ')

    def _rssi_bars(self):
        """Generate signal strength bars."""
        bars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
        filled = int(self.s_meter / 100 * self.signal_bar_width)
        bar_str = '█' * min(filled, self.signal_bar_width)
        bar_str += '░' * (self.signal_bar_width - len(bar_str))
        return bar_str

    def _static_line(self, width):
        """Generate a line of radio static noise."""
        noise_chars = '·∙•◦°*+-~^`\'" '
        return ''.join(random.choice(noise_chars) for _ in range(width))

    def _vfo_display(self):
        """Build the VFO (digital frequency display) string."""
        return f"{self.frequency} MHz  {self.mode}  {self.band}"

    def _s_meter_display(self):
        """Build the S-meter display."""
        s_level = min(9, max(0, int(self.s_meter / 11)))
        if self.s_meter > 99:
            s_str = f"S{s_level}+{min(20, self.s_meter - 99)}dB"
        else:
            s_str = f"S{s_level}"
        return s_str.ljust(8)

    def update(self, segment_name, morse_char, decoded_char, signal):
        """Update display state."""
        self.current_segment = segment_name
        self.s_meter = signal
        self.signal_strength = signal
        self.static_phase += 1

        if morse_char and morse_char != '/':
            self.morse_display.append(morse_char)
            if len(self.morse_display) > 200:
                self.morse_display = self.morse_display[-200:]

        if decoded_char:
            self.decoded_text += decoded_char
            if len(self.decoded_text) > 80:
                self.decoded_text = self.decoded_text[-80:]

    def add_log(self, entry):
        """Add an entry to the broadcast log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.broadcast_log.append(f"[{timestamp}] {entry}")
        if len(self.broadcast_log) > 12:
            self.broadcast_log = self.broadcast_log[-12:]

    def render(self):
        """Full screen render."""
        clear_screen()
        W = 76

        # Title bar
        move_to(1, 1)
        title = f"  ╔═══ {Color.CYAN}{Color.BOLD}SHORTWAVE BROADCASTING STATION{Color.RESET} ═══╗"
        subtitle = f"  ╚═══ {' ' * 27}═══╝"
        sys.stdout.write(f"{Color.CYAN}{Color.BOLD}{'═' * W}{Color.RESET}\n")
        sys.stdout.write(f"{Color.CYAN}{Color.BOLD}  ░█▀▀ █░░ █▀▀ █▀█ █▀█ █▀▀ █▀▀ ░{Color.RESET}\n")
        sys.stdout.write(f"{Color.CYAN}{Color.BOLD}  ░█▀▀ █░░ █▀▀ █▀█ █▀█ █▀▀ █▀▀ ░{Color.RESET}\n")
        sys.stdout.write(f"{Color.CYAN}{Color.BOLD}  ░▀▀▀ ▀▀▀ ▀▀▀ ▀░▀ ▀░▀ ▀▀▀ ▀▀▀ ░{Color.RESET}\n")
        sys.stdout.write(f"{Color.CYAN}{Color.BOLD}{'═' * W}{Color.RESET}\n")

        # VFO Display
        move_to(6, 2)
        vfo = self._vfo_display()
        sys.stdout.write(f"{Color.GREEN}{Color.BOLD}  ┌{'─' * 44}┐{Color.RESET}")
        move_to(7, 2)
        sys.stdout.write(f"{Color.GREEN}{Color.BOLD}  │  ◉  {vfo.ljust(36)}│{Color.RESET}")
        move_to(8, 2)
        sys.stdout.write(f"{Color.GREEN}{Color.BOLD}  └{'─' * 44}┘{Color.RESET}")

        # S-Meter
        move_to(10, 2)
        s_str = self._s_meter_display()
        bars = self._rssi_bars()
        sys.stdout.write(f"{Color.YELLOW}  SIGNAL: [{Color.GREEN}{bars}{Color.YELLOW}] {Color.WHITE}{s_str}{Color.RESET}")

        # Tuning indicator
        move_to(12, 2)
        indicator = "◉" if self.tuned else "○"
        ind_color = Color.GREEN if self.tuned else Color.RED
        sys.stdout.write(f"  {ind_color}{indicator} TUNED{Color.RESET}   ")
        sys.stdout.write(f"{Color.DIM}STATION: {Color.WHITE}{self.call_sign}{Color.RESET}")
        sys.stdout.write(f"  {Color.DIM}SEGMENT: {Color.WHITE}{self.current_segment}{Color.RESET}")

        # Morse code visual display
        move_to(14, 2)
        sys.stdout.write(f"{Color.MAGENTA}{Color.BOLD}  MORSE TRANSMISSION:{Color.RESET}")
        move_to(15, 2)
        sys.stdout.write(f"  {Color.DIM}{'─' * 70}{Color.RESET}")

        # Render morse in a scrolling area
        morse_str = ''.join(self.morse_display[-70:])
        move_to(16, 2)
        sys.stdout.write(f"  {Color.GREEN}{morse_str.ljust(70)}{Color.RESET}")

        # Decoded text
        move_to(18, 2)
        sys.stdout.write(f"{Color.CYAN}{Color.BOLD}  DECODED MESSAGE:{Color.RESET}")
        move_to(19, 2)
        sys.stdout.write(f"  {Color.DIM}{'─' * 70}{Color.RESET}")
        move_to(20, 2)
        decoded_display = self.decoded_text[-70:]
        sys.stdout.write(f"  {Color.WHITE}{Color.BOLD}>{decoded_display.ljust(70)}{Color.RESET}")

        # Waveform area
        move_to(22, 2)
        sys.stdout.write(f"{Color.YELLOW}  WAVEFORM:{Color.RESET}")
        move_to(23, 2)
        sys.stdout.write(f"  {Color.DIM}{'─' * 70}{Color.RESET}")

        for i in range(4):
            move_to(24 + i, 2)
            wave_line = self._render_waveform(70, offset=i * 10)
            sys.stdout.write(f"  {wave_line}")

        # Broadcast log
        move_to(29, 2)
        sys.stdout.write(f"{Color.BLUE}{Color.BOLD}  BROADCAST LOG:{Color.RESET}")
        move_to(30, 2)
        sys.stdout.write(f"  {Color.DIM}{'─' * 70}{Color.RESET}")

        for i, log_entry in enumerate(self.broadcast_log[-10:]):
            move_to(31 + i, 2)
            sys.stdout.write(f"  {Color.DIM}{log_entry[:70]}{Color.RESET}")

        # Static noise line
        move_to(42, 2)
        static = self._static_line(70)
        sys.stdout.write(f"  {Color.DIM}{static}{Color.RESET}")

        # Status bar
        move_to(44, 2)
        sys.stdout.write(f"{Color.CYAN}{'═' * W}{Color.RESET}")
        move_to(45, 2)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        sys.stdout.write(f"  {Color.DIM}📡 ON AIR{Color.RESET}  │  {Color.DIM}{now}{Color.RESET}  │  {Color.DIM}Press Ctrl+C to stop{Color.RESET}")

        sys.stdout.flush()

    def _render_waveform(self, width, offset=0):
        """Render an ASCII waveform."""
        waveform_chars = ' ▁▂▃▄▅▆▇█'
        line = []
        t = time.time() * 5 + offset * 0.3
        signal = self.signal_strength / 100.0
        for i in range(width):
            x = (i + offset) * 0.3
            # Combine sine waves for realistic look
            wave_val = (math.sin(x * 2 + t) * 0.4 +
                        math.sin(x * 5 + t * 1.3) * 0.3 +
                        math.sin(x * 1.5 + t * 0.7) * 0.3) * signal
            wave_val = (wave_val + 1) / 2  # normalize 0-1
            idx = int(wave_val * (len(waveform_chars) - 1))
            idx = max(0, min(len(waveform_chars) - 1, idx))
            line.append(waveform_chars[idx])
        return f"{Color.CYAN}{''.join(line)}{Color.RESET}"


# ============================================================
# Broadcast Manager
# ============================================================
class BroadcastManager:
    """Manages the broadcast schedule and segments."""

    SEGMENT_TYPES = ["STATION_ID", "NEWS", "WEATHER", "STATIC", "EMERGENCY", "IDLE"]

    def __init__(self, call_sign, wpm=20, speed_mult=1.0, audio=False, save_wav=False):
        self.call_sign = call_sign
        self.wpm = wpm
        self.speed_mult = speed_mult
        self.audio_enabled = audio
        self.save_wav = save_wav
        self.engine = MorseEngine(wpm=wpm)
        self.display = RadioDisplay(call_sign)
        self.running = True
        self.cycle_count = 0
        self.current_segment_type = "IDLE"
        self.current_segment_text = ""
        self.segment_queue = self._build_segment_queue()

    def _build_segment_queue(self):
        """Build a cycle of broadcast segments."""
        queue = ["STATION_ID", "NEWS", "WEATHER"]
        # Occasionally add emergency
        if random.random() < 0.3:
            queue.append("EMERGENCY")
        else:
            queue.append("STATIC")
        queue.append("STATION_ID")
        queue.append("NEWS")
        queue.append("WEATHER")
        return queue

    def _get_segment_content(self, segment_type):
        """Get content for a broadcast segment."""
        if segment_type == "STATION_ID":
            phonetic = ' '.join(phonetic for c, phonetic in [
                (c, PHONETIC_ALPHABET.get(c, c)) for c in self.call_sign
            ])
            return f"CQ CQ CQ DE {self.call_sign} {self.call_sign} {self.call_sign} AR", "STATION IDENTIFICATION"
        elif segment_type == "NEWS":
            headline = random.choice(NEWS_TEMPLATES)
            return f"{headline} AR", "NEWS BULLETIN"
        elif segment_type == "WEATHER":
            report = random.choice(WEATHER_TEMPLATES)
            return f"WX {report} AR", "WEATHER REPORT"
        elif segment_type == "EMERGENCY":
            alert = random.choice(EMERGENCY_TEMPLATES)
            return f"URGENT {alert} AR", "EMERGENCY ALERT"
        elif segment_type == "STATIC":
            return "QSL QSL DE " + self.call_sign + " AR", "DEAD AIR / STATIC"
        else:
            return "QRT DE " + self.call_sign + " SK", "SIGN OFF"

    def _transmit_morse(self, text, segment_name):
        """Transmit Morse code character by character with visual + optional audio."""
        morse_pairs = self.engine.text_to_morse(text)
        signal = random.randint(75, 95)
        self.display.current_segment = segment_name

        for char, morse in morse_pairs:
            if not self.running:
                return

            if morse == '/':
                # Word gap
                gap = self.engine.inter_word_gap_ms / 1000.0 * self.speed_mult
                time.sleep(gap)
                self.display.update(segment_name, ' ', ' ', max(10, signal - 20))
                continue

            # Show the morse symbol being transmitted
            self.display.update(segment_name, morse + ' ', char, signal)

            # Transmit each dot/dash
            for symbol in morse:
                if not self.running:
                    return
                if symbol == '.':
                    duration = self.engine.dot_ms / 1000.0 * self.speed_mult
                elif symbol == '-':
                    duration = self.engine.dash_ms / 1000.0 * self.speed_mult
                else:
                    continue

                # Audio beep
                if self.audio_enabled:
                    self._beep(duration, self.engine.freq)
                else:
                    time.sleep(duration)

                # Intra-character gap
                gap = self.engine.intra_char_gap_ms / 1000.0 * self.speed_mult
                time.sleep(gap)

            # Inter-character gap (subtract intra gap already waited)
            char_gap = (self.engine.inter_char_gap_ms - self.engine.intra_char_gap_ms) / 1000.0 * self.speed_mult
            time.sleep(max(0.01, char_gap))

            # Render periodically
            self.display.render()

    def _beep(self, duration, freq):
        """Play a beep using the terminal bell or system beep."""
        # Try to use system beep via ANSI escape
        if sys.platform == 'linux':
            try:
                # Try ALSA or pulseaudio
                os.system(
                    f'play -nq -t alsa synth {duration:.3f} sine {freq} 2>/dev/null &'
                )
            except Exception:
                sys.stdout.write('\a')
                sys.stdout.flush()
        else:
            sys.stdout.write('\a')
            sys.stdout.flush()

    def _transmit_static(self, duration_s):
        """Simulate static/dead air for a duration."""
        end_time = time.time() + duration_s
        while time.time() < end_time and self.running:
            # Randomly fluctuate signal
            signal = random.randint(5, 25)
            self.display.update("STATIC", random.choice(['·', '∙', '•', '◦', '*']), '', signal)
            self.display.render()
            time.sleep(0.15)

    def run(self):
        """Main broadcast loop."""
        try:
            hide_cursor()
            self.running = True
            self.cycle_count = 0

            # Initial display
            self.display.render()

            while self.running:
                if not self.segment_queue:
                    self.segment_queue = self._build_segment_queue()
                    self.cycle_count += 1

                segment_type = self.segment_queue.pop(0)
                text, segment_name = self._get_segment_content(segment_type)
                self.current_segment_type = segment_type
                self.current_segment_text = text

                self.display.add_log(f"▶ {segment_name}: {text[:50]}...")

                if segment_type == "STATIC":
                    static_dur = random.uniform(3, 6)
                    self._transmit_static(static_dur)
                else:
                    self._transmit_morse(text, segment_name)

                # Brief pause between segments
                self.display.add_log(f"✔ {segment_name} complete")
                time.sleep(0.5 * self.speed_mult)

                # Occasionally save WAV
                if self.save_wav and self.cycle_count == 0 and segment_type == "STATION_ID":
                    wav_file = generate_morse_wav(
                        text, wpm=self.wpm,
                        freq=self.engine.freq,
                        filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'broadcast.wav')
                    )
                    self.display.add_log(f"💾 WAV saved: {wav_file}")

                self.cycle_count += 1

        except KeyboardInterrupt:
            pass
        finally:
            self.display.add_log("■ BROADCAST TERMINATED")
            self.display.render()
            show_cursor()
            print()
            print(f"  {Color.YELLOW}📡 {self.call_sign} signing off. 73!{Color.RESET}")
            print()


# ============================================================
# Main
# ============================================================
def print_help():
    print(f"{Color.CYAN}{Color.BOLD}")
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║        SHORTWAVE MORSE BROADCASTING STATION          ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print(f"{Color.RESET}")
    print(f"  {Color.DIM}A vintage shortwave radio station simulator that broadcasts")
    print(f"  Morse code news, weather, and station IDs in real time.{Color.RESET}")
    print()
    print(f"  {Color.YELLOW}Usage:{Color.RESET}")
    print(f"    python main.py [options]")
    print()
    print(f"  {Color.YELLOW}Options:{Color.RESET}")
    print(f"    -c, --callsign    Set custom call sign (default: random)")
    print(f"    -w, --wpm         Morse code speed in WPM (default: 20)")
    print(f"    -f, --freq        Audio frequency in Hz (default: 600)")
    print(f"    -s, --speed       Broadcast speed multiplier (default: 1.0)")
    print(f"    -a, --audio       Enable audio beeps (requires SoX/play)")
    print(f"    -v, --wav         Save broadcast as WAV file")
    print(f"    -l, --log         Print decoded messages to stdout log")
    print(f"    -h, --help        Show this help message")
    print()
    print(f"  {Color.YELLOW}Examples:{Color.RESET}")
    print(f"    python main.py --callsign WBSQ --wpm 25")
    print(f"    python main.py -c KXRT -w 15 -s 0.5  # Slow Morse, easy to follow")
    print(f"    python main.py --audio               # With sound")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Shortwave Morse Broadcasting Station Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-c', '--callsign', type=str, default=None,
                        help='Custom call sign (default: random)')
    parser.add_argument('-w', '--wpm', type=int, default=20,
                        help='Morse code speed in WPM (default: 20)')
    parser.add_argument('-f', '--freq', type=int, default=600,
                        help='Audio frequency in Hz (default: 600)')
    parser.add_argument('-s', '--speed', type=float, default=1.0,
                        help='Broadcast speed multiplier (default: 1.0)')
    parser.add_argument('-a', '--audio', action='store_true',
                        help='Enable audio beeps (requires SoX/play installed)')
    parser.add_argument('-v', '--wav', action='store_true',
                        help='Save first broadcast segment as WAV file')
    parser.add_argument('-l', '--log', action='store_true',
                        help='Print decoded messages to stdout')
    parser.add_argument('--callsign-list', action='store_true',
                        help='List available call signs and exit')
    args = parser.parse_args()

    if args.callsign_list:
        print(f"{Color.CYAN}Available call signs:{Color.RESET}")
        for cs in CALL_SIGNS:
            phonetic = ' '.join(PHONETIC_ALPHABET.get(c, c) for c in cs)
            print(f"  {Color.GREEN}{cs}{Color.RESET} - {phonetic}")
        return

    call_sign = args.callsign.upper() if args.callsign else random.choice(CALL_SIGNS)

    # Validate call sign
    if not all(c.isalnum() for c in call_sign):
        print(f"{Color.RED}Error: Call sign must be alphanumeric{Color.RESET}")
        return

    # Set frequency
    freq = max(200, min(2000, args.freq))

    # Print startup message
    clear_screen()
    print(f"\n  {Color.CYAN} Initializing broadcasting station...{Color.RESET}")
    print(f"  {Color.DIM}Call Sign : {call_sign}{Color.RESET}")
    print(f"  {Color.DIM}Frequency : {freq} Hz{Color.RESET}")
    print(f"  {Color.DIM}Speed     : {args.wpm} WPM{Color.RESET}")
    print(f"  {Color.DIM}Audio     : {'ON' if args.audio else 'OFF'}{Color.RESET}")
    time.sleep(1.5)

    # Start broadcasting
    manager = BroadcastManager(
        call_sign=call_sign,
        wpm=args.wpm,
        speed_mult=args.speed,
        audio=args.audio,
        save_wav=args.wav
    )
    manager.engine.freq = freq
    manager.run()


if __name__ == '__main__':
    main()