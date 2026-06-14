#!/usr/bin/env python3
"""
CLI Escape Room v2.0.0 — A text-based escape room game for your terminal.
Explore rooms, find items, solve puzzles, and escape!

Usage:
    python3 escape_room.py           # Start the game
    python3 escape_room.py --help    # Show help
    python3 escape_room.py --version # Show version

Features:
    - 6 interconnected rooms with atmospheric descriptions
    - 12+ collectible items with interconnected puzzle chains
    - Save/load game state to resume later
    - Contextual hint system for when you're stuck
    - Scoring system with rank tiers
    - Drop items in rooms and pick them up later
    - Command history review
    - Dark rooms, locked doors, combination locks, keypads
    - Typewriter-style narrative output
"""

import sys
import os
import time
import textwrap
import json
import random
import argparse

# ─── Version ────────────────────────────────────────────────────────

VERSION = "2.0.0"

# ─── Save file location ───────────────────────────────────────────

SAVE_DIR = os.path.expanduser("~/.cli-escape-room")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")

# ─── Display helpers ────────────────────────────────────────────────

WIDTH = 70

def clear():
    """Clear the terminal screen."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def narrate(text, delay=0.015):
    """Print text with typewriter effect, word-wrapped to WIDTH."""
    for line in textwrap.wrap(text, width=WIDTH):
        for ch in line:
            sys.stdout.write(ch)
            sys.stdout.flush()
            time.sleep(delay)
        print()
    print()

def narrate_fast(text):
    """Print text instantly (no typewriter delay), word-wrapped to WIDTH."""
    for line in textwrap.wrap(text, width=WIDTH):
        print(line)
    print()

def divider():
    """Print a horizontal divider line."""
    print("─" * WIDTH)

def box(text):
    """Print text inside a box."""
    w = WIDTH
    lines = textwrap.wrap(text, width=w - 4)
    print(f"┌{'─' * (w-2)}┐")
    for line in lines:
        print(f"│ {line:<{w-4}} │")
    print(f"└{'─' * (w-2)}┘")

def prompt():
    """Display the game prompt and return user input."""
    return input("\n\033[1;36m▸ What do you do?\033[0m ").strip().lower()

# ─── Ambient messages ───────────────────────────────────────────────

AMBIENT = {
    "cell": [
        "A drop of water falls from the ceiling with a soft plink.",
        "The fluorescent light buzzes and flickers momentarily.",
        "Somewhere deep in the walls, pipes groan.",
        "A faint draft tickles your neck.",
    ],
    "corridor": [
        "The grandfather clock's pendulum swings silently.",
        "A distant rumble vibrates through the floor.",
        "The keypad beeps once, as if reminding you it's there.",
        "Dust motes drift through the dim light.",
    ],
    "study": [
        "A page in a book turns on its own — must be the draft.",
        "The fireplace crackles faintly, though there's no fire.",
        "You hear the ticking of a clock through the wall.",
        "The leather chair creaks as if someone just stood up.",
    ],
    "lab": [
        "The terminal flickers with a brief burst of static.",
        "A faint smell of ozone drifts from the panels.",
        "A relay clicks somewhere inside the wall.",
        "The device on the bench hums for a moment, then falls silent.",
    ],
    "hidden_passage": [
        "Water drips steadily from an unseen pipe above.",
        "You hear your own heartbeat echoing off the concrete.",
        "The air feels heavier here, thick and damp.",
        "A rat scurries across the far end of the passage.",
    ],
    "control_room": [
        "A monitor briefly shows a face — then static.",
        "The emergency lights pulse faster for a moment.",
        "The console emits a soft electronic chime.",
        "You hear a mechanical whirring behind the exit door.",
    ],
}

def maybe_ambient(room_id, chance=0.2):
    """Randomly display an atmospheric message for the current room."""
    if room_id in AMBIENT and random.random() < chance:
        msg = random.choice(AMBIENT[room_id])
        print(f"\033[2;3m  {msg}\033[0m")

# ─── Item definitions ───────────────────────────────────────────────

ITEMS = {
    "rusty_key": {
        "name": "Rusty Key",
        "desc": "A small, corroded key. The teeth are still distinct enough to work a lock.",
    },
    "flashlight": {
        "name": "Flashlight",
        "desc": "A heavy-duty flashlight. It flickers a bit but works.",
    },
    "note_fragment_1": {
        "name": "Torn Note (Left Half)",
        "desc": "A scrap of paper reading: '...the safe combination begins with...'",
    },
    "note_fragment_2": {
        "name": "Torn Note (Right Half)",
        "desc": "A scrap of paper reading: '...7 turns right, then 3 left, and 9 right to open.'",
    },
    "screwdriver": {
        "name": "Screwdriver",
        "desc": "A Phillips-head screwdriver with a worn grip.",
    },
    "mysterious_gem": {
        "name": "Mysterious Gem",
        "desc": "A deep violet gemstone that pulses with faint inner light.",
    },
    "cabinet_key": {
        "name": "Cabinet Key",
        "desc": "A brass key with an ornate handle shaped like a leaf.",
    },
    "oil_can": {
        "name": "Oil Can",
        "desc": "A small can of machine oil. Still half full.",
    },
    "old_photograph": {
        "name": "Old Photograph",
        "desc": "A faded photo of two people in front of this house. On the back: 'Remember: the clock holds the truth.'",
    },
    "morse_chart": {
        "name": "Morse Code Chart",
        "desc": "A laminated card showing Morse code letters.",
    },
    "blue_wire": {
        "name": "Blue Wire",
        "desc": "A short segment of blue electrical wire with stripped ends.",
    },
    "red_wire": {
        "name": "Red Wire",
        "desc": "A short segment of red electrical wire with stripped ends.",
    },
    "id_card": {
        "name": "ID Card",
        "desc": "An ID badge for 'Dr. Elara Voss — Project Mnemosyne'. Has a magnetic stripe.",
    },
    "combined_note": {
        "name": "Combined Note",
        "desc": "The two note halves, pieced together: '...the safe combination begins with...7 turns right, then 3 left, and 9 right to open.'",
    },
}

# ─── Game State ─────────────────────────────────────────────────────

class GameState:
    """Manages all game state: rooms, inventory, flags, moves, timing."""

    def __init__(self):
        self.current_room = "cell"
        self.inventory = []
        self.flags = set()  # tracks puzzle states
        self.moves = 0
        self.start_time = time.time()
        self.escaped = False
        self.command_history = []
        self.dropped_items = {}  # room_id -> [item_ids dropped in that room]

        # Room descriptions
        self.rooms = {
            "cell": {
                "name": "The Cell",
                "first_desc": (
                    "You wake up on a cold metal bed, head pounding. The room spins as you sit up. "
                    "Fluorescent light flickers overhead, casting long shadows. Concrete walls surround you "
                    "on three sides. To the north, a heavy steel door with a rusty padlock. To the east, "
                    "a curtain conceals a narrow passage. A battered desk sits against the wall, and "
                    "there's a loose brick near the floor."
                ),
                "desc": (
                    "A small, windowless room with concrete walls. A thin mattress lies on a metal frame. "
                    "The only light comes from a flickering fluorescent tube. The air smells of dust."
                ),
                "items": ["rusty_key", "note_fragment_1"],
                "exits": {"north": "corridor", "east": "hidden_passage"},
                "locked": {},  # populated dynamically
                "visited": False,
            },
            "corridor": {
                "name": "The Corridor",
                "first_desc": (
                    "The steel door groans open. A long corridor stretches ahead, dimly lit by wall sconces. "
                    "Faded wallpaper peels in long strips. Three doors are visible: one to the west "
                    "(labeled 'STUDY'), one to the east (labeled 'LAB'), and a sturdy iron door to the "
                    "north with an electronic keypad. A grandfather clock stands against the wall, its "
                    "hands frozen at 3:33. A faint beeping comes from the keypad."
                ),
                "desc": (
                    "A long corridor with peeling wallpaper. Doors to the west (study), east (lab), "
                    "and north (keypad-locked iron door). A grandfather clock reads 3:33."
                ),
                "items": [],
                "exits": {"south": "cell", "west": "study", "east": "lab", "north": "control_room"},
                "locked": {},
                "visited": False,
            },
            "study": {
                "name": "The Study",
                "first_desc": (
                    "You push open the study door. Bookshelves line every wall, filled with dusty tomes. "
                    "A large oak desk sits in the center, covered in papers. An oil painting of a stern "
                    "woman hangs crookedly above the fireplace. A filing cabinet sits in the corner. "
                    "The room smells of old books and pipe tobacco."
                ),
                "desc": (
                    "A well-appointed study with bookshelves, an oak desk, an oil painting above the "
                    "fireplace, and a filing cabinet."
                ),
                "items": ["morse_chart"],
                "exits": {"east": "corridor"},
                "locked": {},
                "visited": False,
            },
            "lab": {
                "name": "The Laboratory",
                "first_desc": (
                    "The lab door clicks open. A sterile laboratory — white walls, stainless steel benches, "
                    "the faint smell of ozone. Electrical panels line the east wall with exposed wiring. "
                    "A glass-fronted cabinet sits in the corner. On a bench, a half-assembled device. "
                    "A terminal on the wall reads: 'POWER OFFLINE — MANUAL REWIRE REQUIRED'."
                ),
                "desc": (
                    "A sterile lab with electrical panels, a glass cabinet, a device on the bench, "
                    "and a wall terminal."
                ),
                "items": ["blue_wire"],
                "exits": {"west": "corridor"},
                "locked": {},
                "visited": False,
            },
            "hidden_passage": {
                "name": "Hidden Passage",
                "first_desc": (
                    "You push aside the curtain. A narrow passage stretches into darkness. The walls are "
                    "bare concrete, slick with condensation. Your footsteps echo. At the end, a small "
                    "alcove with a shelf carved into the wall, and a vent grate near the ceiling."
                ),
                "desc": (
                    "A narrow, damp concrete passage with a shelf and a vent grate near the ceiling."
                ),
                "items": ["screwdriver"],
                "exits": {"west": "cell"},
                "locked": {},
                "visited": False,
            },
            "control_room": {
                "name": "The Control Room",
                "first_desc": (
                    "The iron door swings open. A control room — banks of monitors, a central console "
                    "with flashing lights, and a massive steel exit door on the far wall marked 'EXIT'. "
                    "Red emergency lighting pulses ominously. A screen reads: 'SECURITY PROTOCOL ACTIVE — "
                    "INSERT AUTHORIZED ID AND KEY GEM TO UNLOCK EXIT'. You can almost taste freedom."
                ),
                "desc": (
                    "A high-tech control room with monitors, a central console, and an exit door "
                    "requiring ID card + gem."
                ),
                "items": [],
                "exits": {"south": "corridor", "exit": "freedom"},
                "locked": {},
                "visited": False,
                "dark": True,
                "dark_desc": "It's pitch black. You hear the faint hum of electronics. You need light.",
            },
        }

        # Set initial locked doors
        self.rooms["cell"]["locked"]["north"] = "A rusty padlock secures the steel door."
        self.rooms["corridor"]["locked"]["east"] = "The lab door has a brass lock shaped like a leaf."
        self.rooms["corridor"]["locked"]["north"] = "An electronic keypad glows red on the iron door."

    @property
    def room(self):
        """Return the current room dict."""
        return self.rooms[self.current_room]

    def has_item(self, item_id):
        """Check if an item is in the player's inventory."""
        return item_id in self.inventory

    def take_item(self, item_id, from_room=True):
        """Add an item to inventory. Optionally remove it from the current room."""
        if item_id not in self.inventory:
            self.inventory.append(item_id)
            if from_room:
                room_items = self.room["items"]
                if item_id in room_items:
                    room_items.remove(item_id)

    def remove_item(self, item_id):
        """Remove an item from inventory."""
        if item_id in self.inventory:
            self.inventory.remove(item_id)

    def drop_item(self, item_id):
        """Drop an item from inventory into the current room."""
        if item_id in self.inventory:
            self.inventory.remove(item_id)
            if self.current_room not in self.dropped_items:
                self.dropped_items[self.current_room] = []
            self.dropped_items[self.current_room].append(item_id)
            return True
        return False

    def pickup_dropped(self, item_id):
        """Pick up an item that was previously dropped in the current room."""
        if self.current_room in self.dropped_items:
            room_drops = self.dropped_items[self.current_room]
            if item_id in room_drops:
                room_drops.remove(item_id)
                if not room_drops:
                    del self.dropped_items[self.current_room]
                self.inventory.append(item_id)
                return True
        return False

    def unlock(self, direction):
        """Remove a locked direction from the current room."""
        if direction in self.room["locked"]:
            del self.room["locked"][direction]

    def is_locked(self, direction):
        """Check if a direction is locked in the current room."""
        return direction in self.room["locked"]

    def elapsed_seconds(self):
        """Return seconds elapsed since game start."""
        return int(time.time() - self.start_time)

    def score(self):
        """Calculate escape score based on time, moves, and items.

        Scoring:
            Base: 1000 points
            -5 per move
            -2 per second elapsed
            +50 per item found (max +650 for 13 items)
            +200 bonus for finding all items
            +100 bonus for completing in under 5 minutes
            +50 bonus for completing in under 10 moves
        """
        base = 1000
        move_penalty = self.moves * 5
        time_penalty = self.elapsed_seconds() * 2

        items_found = len([i for i in self.inventory if i in ITEMS])
        item_bonus = items_found * 50
        all_items_bonus = 200 if items_found >= 13 else 0
        speed_bonus = 100 if self.elapsed_seconds() < 300 else 0
        efficient_bonus = 50 if self.moves < 10 else 0

        total = base - move_penalty - time_penalty + item_bonus + all_items_bonus + speed_bonus + efficient_bonus
        return max(total, 0)  # Floor at 0

    @staticmethod
    def rank_for_score(score):
        """Return a rank tier string for a given score."""
        if score >= 1500:
            return "S — Master Escapist"
        elif score >= 1200:
            return "A — Expert Puzzler"
        elif score >= 900:
            return "B — Skilled Explorer"
        elif score >= 600:
            return "C — Capable Survivor"
        elif score >= 300:
            return "D — Lucky Escapee"
        else:
            return "F — Barely Made It"

    def to_dict(self):
        """Serialize game state to a dict for saving."""
        return {
            "current_room": self.current_room,
            "inventory": self.inventory,
            "flags": list(self.flags),
            "moves": self.moves,
            "start_time": self.start_time,
            "escaped": self.escaped,
            "command_history": self.command_history[-50:],  # last 50 commands
            "dropped_items": self.dropped_items,
            "rooms": {
                room_id: {
                    "items": room["items"],
                    "locked": room["locked"],
                    "visited": room["visited"],
                }
                for room_id, room in self.rooms.items()
            },
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialize game state from a dict (loaded from save file)."""
        state = cls.__new__(cls)
        state.current_room = data["current_room"]
        state.inventory = data["inventory"]
        state.flags = set(data["flags"])
        state.moves = data["moves"]
        state.start_time = data["start_time"]
        state.escaped = data["escaped"]
        state.command_history = data.get("command_history", [])
        state.dropped_items = data.get("dropped_items", {})

        # Reconstruct rooms — re-init to get full descriptions, then overlay saved state
        base = cls()
        state.rooms = base.rooms
        for room_id, saved_room in data.get("rooms", {}).items():
            if room_id in state.rooms:
                state.rooms[room_id]["items"] = saved_room["items"]
                state.rooms[room_id]["locked"] = saved_room["locked"]
                state.rooms[room_id]["visited"] = saved_room["visited"]

        return state

    def save(self):
        """Save game state to disk."""
        os.makedirs(SAVE_DIR, exist_ok=True)
        with open(SAVE_FILE, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls):
        """Load game state from disk. Returns None if no save exists."""
        if not os.path.exists(SAVE_FILE):
            return None
        try:
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    @classmethod
    def has_save(cls):
        """Check if a save file exists."""
        return os.path.exists(SAVE_FILE)

    @classmethod
    def delete_save(cls):
        """Delete the save file."""
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)


# ─── Interactables (examined via "look at X" or "use X on Y") ──────

INTERACTABLES = {
    "cell": {
        "desk": {
            "name": "metal desk",
            "short": "A battered metal desk with one drawer.",
            "inspect": "The desk is scarred with scratches. The drawer is stuck — something's wedged inside. Maybe a tool could open it.",
            "requires": "screwdriver",
            "result": "You pry the drawer open with the screwdriver. Inside: a cabinet key!",
            "gives": "cabinet_key",
        },
        "loose brick": {
            "name": "loose brick",
            "short": "A brick near the floor that sticks out slightly.",
            "inspect": "You pull the brick out. Behind it, a small cavity — inside is a torn note!",
            "gives": "note_fragment_2",
            "onetime": True,
        },
        "mattress": {
            "name": "mattress",
            "short": "A thin, stained mattress on a metal frame.",
            "inspect": "You lift the mattress. Nothing but springs and stains. Disappointing.",
        },
        "padlock": {
            "name": "padlock",
            "short": "A rusty padlock on the steel door.",
            "inspect": "The padlock is old and corroded. Maybe a key would fit...",
            "requires": "rusty_key",
            "result": "The rusty key fits! The padlock clatters to the floor.",
            "unlocks": "north",
        },
    },
    "corridor": {
        "clock": {
            "name": "grandfather clock",
            "short": "A tall grandfather clock, hands frozen at 3:33.",
            "inspect": "The clock is ornate, with carved mahogany. The face reads 3:33. You notice '3333' etched into the back panel. On the inside of the door, a label: 'Access Code: 3333'. Someone wanted to remember it. Behind the clock, an old photograph is wedged.",
            "gives": "old_photograph",
        },
        "keypad": {
            "name": "electronic keypad",
            "short": "An electronic keypad with a 4-digit display, glowing red.",
            "inspect": "The keypad requires a 4-digit code. The keys 3, 7, and 9 are most worn.",
            "is_keypad": True,
        },
        "wallpaper": {
            "name": "wallpaper",
            "short": "Faded, peeling wallpaper with a floral pattern.",
            "inspect": "Behind a strip of wallpaper, someone scratched: 'TIME = KEY'. The clock must be important.",
        },
    },
    "study": {
        "painting": {
            "name": "oil painting",
            "short": "An oil painting of a stern woman in Victorian dress.",
            "inspect": "You tilt the painting aside. Behind it, a wall safe with a combination dial! The dial has numbers 0-99.",
            "is_safe": True,
        },
        "filing cabinet": {
            "name": "filing cabinet",
            "short": "A metal filing cabinet with a single drawer.",
            "inspect": "The drawer requires a key. The lock has a leaf-shaped escutcheon.",
            "requires": "cabinet_key",
            "result": "The brass key turns smoothly. Inside: a flashlight!",
            "gives": "flashlight",
        },
        "bookshelf": {
            "name": "bookshelf",
            "short": "Floor-to-ceiling bookshelves filled with dusty tomes.",
            "inspect": "Most books are unremarkable. One stands out: 'Signals & Codes: A Practical Guide', bookmarked at the Morse code section.",
        },
        "desk": {
            "name": "oak desk",
            "short": "A large oak desk covered in papers.",
            "inspect": "You shuffle through the papers. Most are scientific reports about 'Project Mnemosyne'. One memo reads: 'Safe combination protocol: begin R, then L, then R. The numbers are in the note.'",
        },
        "fireplace": {
            "name": "fireplace",
            "short": "A stone fireplace, cold and unused.",
            "inspect": "The fireplace is cold. A few ashes remain. Nothing hidden here.",
        },
    },
    "lab": {
        "electrical panel": {
            "name": "electrical panel",
            "short": "A wall-mounted panel with exposed wiring and terminals.",
            "inspect": "The panel has two terminals labeled RED and BLUE. Wires are disconnected. You need to connect the right wires.",
        },
        "cabinet": {
            "name": "glass cabinet",
            "short": "A glass-fronted cabinet with a combination lock.",
            "inspect": "The cabinet contains a red wire and an oil can, but it's locked. The label reads: 'Code: 4-7-2'.",
            "is_cabinet_lock": True,
        },
        "device": {
            "name": "device",
            "short": "A half-assembled electronic device on the bench.",
            "inspect": "Label: 'Mnemosyne Memory Scanner — Prototype'. It's not functional.",
        },
        "terminal": {
            "name": "terminal",
            "short": "A wall-mounted terminal with a dim screen.",
            "inspect": "The screen reads: 'POWER OFFLINE — MANUAL REWIRE REQUIRED'. Fix the electrical panel to restore power.",
        },
    },
    "hidden_passage": {
        "shelf": {
            "name": "alcove shelf",
            "short": "A crude shelf carved into the concrete wall.",
            "inspect": "On the shelf: a screwdriver. Someone left it here deliberately.",
            "gives": "screwdriver",
            "onetime": True,
        },
        "vent": {
            "name": "vent grate",
            "short": "A small ventilation grate near the ceiling.",
            "inspect": "The grate is rusted shut. Maybe some oil would loosen it...",
            "requires": "oil_can",
            "result": "The oil loosens the rust. The grate creaks open, revealing an ID card!",
            "gives": "id_card",
        },
        "wall markings": {
            "name": "wall markings",
            "short": "Faint scratches on the concrete wall.",
            "inspect": "Someone scratched: '4-7-2 opens what's locked. Remember the sequence.'",
        },
    },
    "control_room": {
        "console": {
            "name": "central console",
            "short": "The main control console with a screen and card reader.",
            "inspect": "The console reads: 'SECURITY PROTOCOL ACTIVE'. There's a card reader slot and a circular gem-shaped indentation. Insert both to unlock the exit.",
        },
        "monitors": {
            "name": "monitors",
            "short": "Banks of monitors showing security feeds — all static.",
            "inspect": "The monitors flicker with static. One briefly shows the house from outside. Then it's gone. You're definitely underground.",
        },
        "exit door": {
            "name": "exit door",
            "short": "A massive steel door marked 'EXIT' with a gem-shaped lock and card reader.",
            "inspect": "The exit has two locks: a magnetic card reader and a gem-shaped indentation. Both must be activated.",
        },
    },
}

# Track one-time interactables
used_interactables = set()

# ─── Hint system ────────────────────────────────────────────────────

def get_hint(state):
    """Return a contextual hint based on the current room and game state.

    Walks through a priority-ordered checklist of puzzle progress
    and returns the most relevant next step.
    """
    room = state.current_room
    flags = state.flags
    inv = state.inventory

    # --- Cell phase ---
    if room == "cell":
        if not state.has_item("rusty_key"):
            return "Look around carefully. There might be something useful on the ground."
        if state.is_locked("north"):
            if state.has_item("rusty_key"):
                return "You have a key and there's a padlock on the door. Try 'use rusty key on padlock'."
        if not state.has_item("note_fragment_2"):
            return "That loose brick looks suspicious. Try 'look at loose brick'."
        if not state.has_item("cabinet_key"):
            if not state.has_item("screwdriver"):
                return "The desk drawer is stuck. You need a tool to pry it open. Explore other rooms."
            else:
                return "Try using the screwdriver on the desk drawer."

    # --- Hidden passage ---
    if room == "hidden_passage":
        if not state.has_item("screwdriver"):
            return "Check the shelf — someone may have left something useful there."
        if not state.has_item("id_card"):
            if not state.has_item("oil_can"):
                return "The vent grate is rusted shut. You'll need something to loosen it. Try the laboratory."
            else:
                return "You have oil! Try 'use oil can on vent'."
        return "You've found everything here. Time to explore other rooms."

    # --- Corridor ---
    if room == "corridor":
        if state.is_locked("north"):
            return "The keypad needs a 4-digit code. Examine things that show numbers — the clock seems important."
        if state.is_locked("east"):
            if state.has_item("cabinet_key"):
                return "The lab door has a leaf-shaped lock. Your cabinet key might work."
            return "The lab door is locked with a leaf-shaped brass lock. Look for a matching key."
        if not state.has_item("old_photograph"):
            return "Have you examined the grandfather clock closely? There might be something behind it."

    # --- Study ---
    if room == "study":
        if "safe_opened" not in flags:
            if "safe_combo" not in flags:
                if not (state.has_item("note_fragment_1") and state.has_item("note_fragment_2")):
                    return "You need to find clue fragments. Search other rooms for torn notes."
                else:
                    return "You have both note halves! Try 'combine notes' to read the safe combination."
            else:
                return "You know the combination! Examine the painting to find the safe, then use the combination."
        if not state.has_item("flashlight"):
            if state.has_item("cabinet_key"):
                return "The filing cabinet needs a key. Try 'use cabinet key on filing cabinet'."
            return "The filing cabinet is locked. You need a key with a leaf-shaped handle."

    # --- Lab ---
    if room == "lab":
        if "cabinet_opened" not in flags:
            return "The glass cabinet has a 3-digit code lock. Check the hidden passage for clues."
        if "power_restored" not in flags:
            has_red = "red_connected" in flags or state.has_item("red_wire")
            has_blue = "blue_connected" in flags or state.has_item("blue_wire")
            if not has_blue:
                return "The blue wire is on the bench. Pick it up and connect it to the electrical panel."
            if not has_red:
                return "You need a red wire. The glass cabinet might have one."
            return "You have wires! Use 'use red wire on panel' and 'use blue wire on panel'."
        return "Power is restored. Keep exploring!"

    # --- Control room ---
    if room == "control_room":
        if not state.has_item("flashlight"):
            return "It's dark in here! You need a flashlight. Check the study."
        if "id_scanned" not in flags:
            if not state.has_item("id_card"):
                return "The console needs an ID card. Check the hidden passage vent grate."
            return "You have the ID card! Try 'use id card on console'."
        if "gem_placed" not in flags:
            if not state.has_item("mysterious_gem"):
                return "The console needs a gem. Maybe the study safe has one?"
            return "Place the gem in the console indentation! Try 'use gem on console'."
        if state.is_locked("exit"):
            return "The exit should be unlocked now. Try 'go exit'!"
        return "Almost free! Head through the exit."

    # --- Generic fallback ---
    if not state.has_item("rusty_key"):
        return "Search the cell for useful items."
    if state.is_locked("north") and state.current_room == "cell":
        return "Use the key on the padlock to leave the cell."
    if "safe_combo" not in flags:
        return "Look for torn note fragments and combine them."
    if "safe_opened" not in flags:
        return "Use the safe combination on the safe behind the painting in the study."
    if "power_restored" not in flags:
        return "The lab needs power. Connect wires to the electrical panel."
    if not state.has_item("flashlight"):
        return "Find a flashlight before entering dark rooms."
    return "Keep exploring and examining things. Every clue has a purpose."

# ─── Command Parser ─────────────────────────────────────────────────

def parse_command(cmd):
    """Parse raw user input into a (verb, args) tuple.

    Supports aliases, multi-word commands like 'pick up' and 'look at',
    and direction shortcuts (n/s/e/w).
    """
    cmd = cmd.strip().lower()
    if not cmd:
        return None, ""

    aliases = {
        "look": ["l", "examine", "x", "inspect", "check"],
        "go": ["move", "walk", "enter", "head"],
        "take": ["get", "grab", "pick", "pickup"],
        "use": ["apply", "insert", "put", "place", "connect", "swipe", "open"],
        "inventory": ["i", "inv", "bag", "items"],
        "help": ["h", "?"],
        "combine": ["join", "merge"],
        "read": ["view"],
        "quit": ["exit", "q"],
        "save": [],
        "load": [],
        "hint": [],
        "status": [],
        "drop": ["leave", "discard"],
        "history": ["log"],
    }

    # Direction shortcuts
    direction_shortcuts = {"n": "north", "s": "south", "e": "east", "w": "west"}

    verb_map = {}
    for main, alts in aliases.items():
        verb_map[main] = main
        for a in alts:
            verb_map[a] = main

    words = cmd.split()
    verb = words[0]
    args = " ".join(words[1:]) if len(words) > 1 else ""

    # Multi-word command handling
    if cmd.startswith("pick up"):
        verb = "take"
        args = cmd[7:].strip()
    elif cmd.startswith("look at"):
        verb = "look"
        args = cmd[7:].strip()

    # Direction shortcuts: "n" → go north
    # Must check before verb resolution since 'n'/'s'/'e'/'w' aren't in aliases
    if verb in direction_shortcuts:
        args = direction_shortcuts[verb]
        verb = "go"

    resolved = verb_map.get(verb, verb)
    # Ensure args is always a string
    if isinstance(args, list):
        args = " ".join(args)
    return resolved, str(args)

# ─── Game Actions ───────────────────────────────────────────────────

def get_interactable(state, target):
    """Find an interactable matching the target string in the current room."""
    room_id = state.current_room
    if room_id not in INTERACTABLES:
        return None, None
    for key, obj in INTERACTABLES[room_id].items():
        if target in key or target in obj["name"].lower():
            return key, obj
    return None, None

def get_all_visible_items(state):
    """Return a list of (item_id, item_data) for all items visible in the room.

    Includes room items, interactable-given items, and dropped items.
    """
    room = state.room
    visible = []
    # Room floor items
    for item_id in room["items"]:
        if item_id in ITEMS:
            visible.append((item_id, ITEMS[item_id], "floor"))
    # Dropped items
    if state.current_room in state.dropped_items:
        for item_id in state.dropped_items[state.current_room]:
            if item_id in ITEMS:
                visible.append((item_id, ITEMS[item_id], "dropped"))
    return visible

def do_look(state, target=""):
    """Handle the 'look' command: describe the room or examine a specific thing."""
    room = state.room

    # Dark room check
    if room.get("dark") and not state.has_item("flashlight"):
        narrate(room.get("dark_desc", "It's too dark to see."))
        return

    if not target:
        desc = room["first_desc"] if not room["visited"] else room["desc"]
        narrate(desc)

        # Show items on the floor
        if room["items"]:
            item_names = [ITEMS[i]["name"] for i in room["items"] if i in ITEMS]
            if item_names:
                narrate("You notice: " + ", ".join(item_names))

        # Show dropped items
        if state.current_room in state.dropped_items and state.dropped_items[state.current_room]:
            dropped_names = [ITEMS[i]["name"] for i in state.dropped_items[state.current_room] if i in ITEMS]
            if dropped_names:
                narrate("On the ground (dropped): " + ", ".join(dropped_names))

        # Show interactables
        room_id = state.current_room
        if room_id in INTERACTABLES:
            for key, obj in INTERACTABLES[room_id].items():
                if key not in used_interactables or not obj.get("onetime"):
                    narrate(f"There's {obj['short']}")

        # Show exits
        exits_info = []
        for direction, room_id in room["exits"].items():
            target_room = state.rooms[room_id]
            info = f"{direction} → {target_room['name']}"
            if direction in room["locked"]:
                info += " [LOCKED]"
            exits_info.append(info)
        narrate("Exits: " + ", ".join(exits_info))
        return

    # Look at specific thing
    # Check room items
    for item_id in room["items"]:
        if item_id in ITEMS and target in ITEMS[item_id]["name"].lower():
            narrate(ITEMS[item_id]["desc"])
            return

    # Check dropped items in room
    if state.current_room in state.dropped_items:
        for item_id in state.dropped_items[state.current_room]:
            if item_id in ITEMS and target in ITEMS[item_id]["name"].lower():
                narrate(ITEMS[item_id]["desc"])
                return

    # Check inventory items
    for item_id in state.inventory:
        if item_id in ITEMS and target in ITEMS[item_id]["name"].lower():
            narrate(ITEMS[item_id]["desc"])
            return

    # Check interactables
    key, obj = get_interactable(state, target)
    if obj:
        if key in used_interactables and obj.get("onetime"):
            narrate(f"The {obj['name']} has already been thoroughly searched.")
        else:
            narrate(obj["inspect"])
            # Auto-give items on inspect for certain interactables
            if "gives" in obj and "requires" not in obj and not obj.get("is_safe") and not obj.get("is_cabinet_lock"):
                if not state.has_item(obj["gives"]):
                    state.take_item(obj["gives"], from_room=False)
                    narrate(f"You take: {ITEMS[obj['gives']]['name']}")
                    if obj.get("onetime"):
                        used_interactables.add(key)
        return

    narrate("You don't see that here.")

def do_go(state, direction):
    """Handle the 'go' command: move to another room."""
    room = state.room

    if room.get("dark") and not state.has_item("flashlight"):
        narrate("It's too dark to navigate safely. Find a light source first.")
        return

    if not direction:
        narrate("Go where? Exits: " + ", ".join(room["exits"].keys()))
        return

    # Fuzzy match direction
    matched_dir = None
    for d in room["exits"]:
        if d.startswith(direction) or direction == d:
            matched_dir = d
            break
    if not matched_dir:
        narrate(f"You can't go '{direction}'. Exits: {', '.join(room['exits'].keys())}")
        return

    # Check locked
    if matched_dir in room["locked"]:
        lock_msg = room["locked"][matched_dir]
        narrate(lock_msg)
        return

    # Move
    new_room_id = room["exits"][matched_dir]
    if new_room_id == "freedom":
        state.escaped = True
        return

    state.current_room = new_room_id
    state.moves += 1
    state.room["visited"] = True
    narrate(f"You head {matched_dir}...")
    do_look(state)
    maybe_ambient(state.current_room, chance=0.25)

def do_take(state, target):
    """Handle the 'take' command: pick up an item."""
    room = state.room
    if not target:
        narrate("Take what?")
        return

    # Check room items first
    for item_id in room["items"]:
        if item_id in ITEMS and target in ITEMS[item_id]["name"].lower():
            state.take_item(item_id)
            narrate(f"You pick up the {ITEMS[item_id]['name']}.")
            return

    # Check dropped items in this room
    if state.current_room in state.dropped_items:
        for item_id in state.dropped_items[state.current_room]:
            if item_id in ITEMS and target in ITEMS[item_id]["name"].lower():
                state.pickup_dropped(item_id)
                narrate(f"You pick up the {ITEMS[item_id]['name']}.")
                return

    # Check interactables that auto-give on inspect (already handled in do_look)
    key, obj = get_interactable(state, target)
    if obj and "gives" in obj and "requires" not in obj:
        if not state.has_item(obj["gives"]):
            state.take_item(obj["gives"], from_room=False)
            narrate(f"You take: {ITEMS[obj['gives']]['name']}")
            if obj.get("onetime"):
                used_interactables.add(key)
        else:
            narrate("You already have that.")
        return

    narrate("There's nothing like that to take here.")

def do_drop(state, target):
    """Handle the 'drop' command: leave an item in the current room."""
    if not target:
        narrate("Drop what?")
        return

    # Find the item in inventory
    item_id = None
    for iid in state.inventory:
        if iid in ITEMS and target in ITEMS[iid]["name"].lower():
            item_id = iid
            break

    if not item_id:
        narrate("You don't have that item.")
        return

    name = ITEMS[item_id]["name"]
    state.drop_item(item_id)
    narrate(f"You drop the {name} on the ground.")

def do_use(state, target):
    """Handle the 'use' command: use an item on something."""
    room = state.room
    if not target:
        narrate("Use what on what? Try: use <item> on <thing>")
        return

    # Parse "use X on Y"
    on_split = target.split(" on ")
    if len(on_split) == 2:
        item_name = on_split[0].strip()
        target_name = on_split[1].strip()
    else:
        item_name = target
        target_name = ""

    # Special: combine note fragments via 'use'
    if "note" in item_name or "fragment" in item_name:
        if state.has_item("note_fragment_1") and state.has_item("note_fragment_2"):
            if "safe_combo" not in state.flags:
                state.flags.add("safe_combo")
                narrate("You piece the torn notes together. They read: "
                        "'...the safe combination begins with...7 turns right, then 3 left, "
                        "and 9 right to open.' → Combination: Right 7, Left 3, Right 9")
            else:
                narrate("You've already combined the notes. Combination: R7, L3, R9.")
            return
        else:
            narrate("You need both note fragments to combine them.")
            return

    # Find the item in inventory
    item_id = None
    for iid in state.inventory:
        if iid in ITEMS and item_name in ITEMS[iid]["name"].lower():
            item_id = iid
            break

    if not item_id:
        narrate("You don't have that item.")
        return

    # If no target specified, give hint
    if not target_name:
        narrate(f"Use the {ITEMS[item_id]['name']} on what? Try: use {ITEMS[item_id]['name'].lower()} on <something>")
        return

    # Find the interactable target
    key, obj = get_interactable(state, target_name)
    if not obj:
        # Check if it's a direction/door
        for d in room["locked"]:
            if target_name in d or "door" in target_name or "lock" in target_name:
                narrate(room["locked"][d])
                return
        narrate(f"You don't see '{target_name}' to use that on.")
        return

    # Check if item is required for this interactable
    if "requires" in obj:
        if item_id != obj["requires"]:
            narrate(f"The {ITEMS[item_id]['name']} doesn't help with the {obj['name']}.")
            return
        # Use item on interactable
        narrate(obj["result"])
        if "gives" in obj and not state.has_item(obj["gives"]):
            state.take_item(obj["gives"], from_room=False)
            narrate(f"You obtain: {ITEMS[obj['gives']]['name']}")
        if "unlocks" in obj:
            state.unlock(obj["unlocks"])
            state.remove_item(item_id)
        if obj.get("onetime"):
            used_interactables.add(key)
        return

    # Special cases
    if obj.get("is_keypad"):
        if item_id == "rusty_key":
            narrate("A key won't work on an electronic keypad. It needs a code.")
            return
        narrate(f"The {ITEMS[item_id]['name']} doesn't fit in a keypad. It needs a numeric code.")

    elif obj.get("is_safe"):
        if "safe_combo" not in state.flags:
            narrate("You don't know the combination. Maybe you can find a clue...")
        else:
            if "safe_opened" not in state.flags:
                state.flags.add("safe_opened")
                narrate("You dial: Right 7... Left 3... Right 9... Click-click-click!")
                narrate("The safe swings open! Inside: a mysterious violet gem and an ID card!")
                state.take_item("mysterious_gem", from_room=False)
                state.take_item("id_card", from_room=False)
            else:
                narrate("The safe is already open and empty.")

    elif obj.get("is_cabinet_lock"):
        narrate("The cabinet needs a 3-digit code, not an item.")

    elif item_id == "red_wire" and "panel" in target_name:
        if "red_connected" not in state.flags:
            state.flags.add("red_connected")
            state.remove_item("red_wire")
            narrate("You connect the red wire to the RED terminal. One down, one to go.")
            if "blue_connected" in state.flags:
                state.flags.add("power_restored")
                narrate("Both wires connected! The panel hums to life! POWER RESTORED!")
        else:
            narrate("Red wire already connected.")

    elif item_id == "blue_wire" and "panel" in target_name:
        if "blue_connected" not in state.flags:
            state.flags.add("blue_connected")
            state.remove_item("blue_wire")
            narrate("You connect the blue wire to the BLUE terminal. One down, one to go.")
            if "red_connected" in state.flags:
                state.flags.add("power_restored")
                narrate("Both wires connected! The panel hums to life! POWER RESTORED!")
        else:
            narrate("Blue wire already connected.")

    elif item_id == "id_card" and ("console" in target_name or "exit" in target_name):
        if "id_scanned" not in state.flags:
            state.flags.add("id_scanned")
            state.remove_item("id_card")
            narrate("You swipe the ID card. Console reads: 'DR. VOSS AUTHORIZED — INSERT KEY GEM'")
        else:
            narrate("ID already scanned.")

    elif item_id == "mysterious_gem" and ("console" in target_name or "exit" in target_name):
        if "id_scanned" not in state.flags:
            narrate("The gem indentation is inert. The card reader must be activated first.")
        elif "gem_placed" not in state.flags:
            state.flags.add("gem_placed")
            state.remove_item("mysterious_gem")
            narrate("You place the gem in the indentation. It pulses with light!")
            narrate("SECURITY PROTOCOL DEACTIVATED. EXIT UNLOCKED.")
            state.unlock("exit")
        else:
            narrate("The gem is already in place.")

    else:
        narrate(f"Using the {ITEMS[item_id]['name']} on the {obj['name']} doesn't seem to help.")

def do_combine(state, target):
    """Handle the 'combine' command: merge two items."""
    if "note" in target or "fragment" in target:
        if state.has_item("note_fragment_1") and state.has_item("note_fragment_2"):
            if "safe_combo" not in state.flags:
                state.flags.add("safe_combo")
                narrate("You piece the torn notes together. They read: "
                        "'...the safe combination begins with...7 turns right, then 3 left, "
                        "and 9 right to open.' → Combination: Right 7, Left 3, Right 9")
            else:
                narrate("You've already combined the notes. Combination: R7, L3, R9.")
        else:
            narrate("You need both note fragments to combine them.")
    elif "wire" in target:
        narrate("Wires need to be connected to the electrical panel individually. Try: use wire on panel")
    else:
        narrate("You can't combine those items.")

def do_inventory(state):
    """Display the player's inventory."""
    if not state.inventory:
        narrate("Your pockets are empty.")
        return
    print("\n┌─ INVENTORY ────────────────────────────────────────────────────┐")
    for item_id in state.inventory:
        if item_id in ITEMS:
            print(f"│  • {ITEMS[item_id]['name']:<60} │")
    print("└────────────────────────────────────────────────────────────────┘\n")

def do_help(state):
    """Display command help."""
    box(
        "COMMANDS: look [thing] | go <direction> | take <item> | "
        "use <item> on <thing> | combine <things> | drop <item> | "
        "inventory | hint | status | save | load | history | help | quit. "
        "Directions: n/north, s/south, e/east, w/west. Tip: examine everything!"
    )

def do_status(state):
    """Show current game status: room, moves, time."""
    elapsed = state.elapsed_seconds()
    mins, secs = divmod(elapsed, 60)
    room_name = state.room["name"]

    print(f"\n┌─ STATUS ──────────────────────────────────────────────────────┐")
    print(f"│  Room:  {room_name:<56} │")
    print(f"│  Moves: {state.moves:<56} │")
    print(f"│  Time:  {mins}m {secs}s{' ' * (54 - len(f'{mins}m {secs}s'))} │")
    items_count = len([i for i in state.inventory if i in ITEMS])
    print(f"│  Items: {items_count:<56} │")
    if GameState.has_save():
        print(f"│  Save:  Available{' ' * 45} │")
    print(f"└────────────────────────────────────────────────────────────────┘\n")

def do_hint(state):
    """Display a contextual hint."""
    hint = get_hint(state)
    print(f"\n\033[1;33m💡 Hint: {hint}\033[0m\n")

def do_save(state):
    """Save the current game to disk."""
    try:
        state.save()
        narrate("Game saved! You can resume later with 'load'.")
    except OSError as e:
        narrate(f"Could not save game: {e}")

def do_load(state):
    """Load a saved game from disk, replacing current state."""
    loaded = GameState.load()
    if loaded is None:
        narrate("No saved game found.")
        return None
    narrate("Game loaded! You pick up where you left off...")
    return loaded

def do_history(state):
    """Show recent command history."""
    if not state.command_history:
        narrate("No commands in history yet.")
        return
    print("\n┌─ COMMAND HISTORY ─────────────────────────────────────────────┐")
    # Show last 20 commands
    recent = state.command_history[-20:]
    for i, cmd in enumerate(recent, 1):
        print(f"│  {i:>2}. {cmd:<55} │")
    print("└────────────────────────────────────────────────────────────────┘\n")

def do_enter_code(state, target):
    """Handle entering codes at various places."""
    room = state.room

    # Keypad in corridor
    if state.current_room == "corridor" and "north" in room["locked"]:
        if "3333" in target or target == "3333":
            narrate("✓ ACCESS GRANTED! The keypad turns green and the iron door clicks open.")
            state.unlock("north")
            return
        else:
            narrate("✗ INVALID CODE. The keypad resets.")
            return

    # Lab cabinet
    if state.current_room == "lab":
        key, obj = get_interactable(state, "cabinet")
        if obj and obj.get("is_cabinet_lock"):
            if "cabinet_opened" not in state.flags:
                if "472" in target.replace("-", "").replace(" ", "") or target == "4-7-2":
                    state.flags.add("cabinet_opened")
                    narrate("Click-click-click! The cabinet opens! Inside: a red wire and an oil can!")
                    state.take_item("red_wire", from_room=False)
                    state.take_item("oil_can", from_room=False)
                    return
                else:
                    narrate("✗ Wrong code. The cabinet stays locked.")
                    return

    # Study safe
    if state.current_room == "study":
        key, obj = get_interactable(state, "painting")
        if obj and obj.get("is_safe"):
            if "safe_opened" not in state.flags:
                if "safe_combo" in state.flags:
                    narrate("You dial: Right 7... Left 3... Right 9... Click-click-click!")
                    narrate("The safe swings open! Inside: a mysterious violet gem and an ID card!")
                    state.flags.add("safe_opened")
                    state.take_item("mysterious_gem", from_room=False)
                    state.take_item("id_card", from_room=False)
                    return
                else:
                    narrate("You don't know the combination. Maybe find some clues first.")
                    return

    narrate("There's nothing here to enter a code into.")

def handle_keypad(state):
    """Interactive keypad entry with limited attempts."""
    narrate("The keypad display blinks, waiting for a 4-digit code.")
    attempts = 3
    while attempts > 0:
        try:
            code = input("\033[1;33m    ▸ Enter 4-digit code: \033[0m").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if code == "3333":
            narrate("✓ ACCESS GRANTED! The keypad turns green and the iron door clicks open.")
            state.unlock("north")
            return
        else:
            attempts -= 1
            if attempts > 0:
                narrate(f"✗ INVALID CODE. {attempts} attempt(s) remaining.")
            else:
                narrate("✗ INVALID CODE. The keypad resets. You can try again later.")

def handle_cabinet_code(state):
    """Interactive cabinet code entry with limited attempts."""
    narrate("The cabinet lock requires a 3-digit code.")
    attempts = 3
    while attempts > 0:
        try:
            code = input("\033[1;33m    ▸ Enter 3-digit code: \033[0m").strip().replace("-", "").replace(" ", "")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if code == "472":
            state.flags.add("cabinet_opened")
            narrate("Click-click-click! The cabinet opens! Inside: a red wire and an oil can!")
            state.take_item("red_wire", from_room=False)
            state.take_item("oil_can", from_room=False)
            return
        else:
            attempts -= 1
            if attempts > 0:
                narrate(f"✗ Wrong code. {attempts} attempt(s) remaining.")
            else:
                narrate("✗ Wrong code. The cabinet stays locked. Try again later.")

def handle_safe_combination(state):
    """Interactive safe combination entry."""
    narrate("The safe requires a combination: direction + number, direction + number, direction + number.")
    narrate("Example: right 7, left 3, right 9")
    try:
        combo = input("\033[1;33m    ▸ Enter combination: \033[0m").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return
    # Accept various formats
    combo_clean = combo.replace(",", "").replace(" ", "").replace(".", "")
    if "right7" in combo_clean and "left3" in combo_clean and "right9" in combo_clean:
        state.flags.add("safe_opened")
        narrate("Click-click-click! The safe swings open! Inside: a mysterious violet gem and an ID card!")
        state.take_item("mysterious_gem", from_room=False)
        state.take_item("id_card", from_room=False)
    elif "safe_combo" in state.flags:
        # Player knows the combo but typed it wrong
        narrate("Hmm, that doesn't work. The note said: 7 turns right, 3 left, 9 right. Try: right 7 left 3 right 9")
    else:
        narrate("The dial doesn't move. You need the right combination.")

# ─── Title and Victory screens ──────────────────────────────────────

def show_title():
    """Display the ASCII art title screen."""
    clear()
    title = r"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║       ██████╗ ██████╗ ███████╗ ██████╗ ████████╗███████╗          ║
    ║      ██╔═══██╗██╔══██╗██╔════╝██╔═══██╗╚══██╔══╝██╔════╝          ║
    ║      ██║   ██║██████╔╝███████╗██║   ██║   ██║   █████╗            ║
    ║      ██║   ██║██╔══██╗╚════██║██║   ██║   ██║   ██╔══╝            ║
    ║      ╚██████╔╝██║  ██║███████║╚██████╔╝   ██║   ███████╗          ║
    ║       ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═════╝    ╚═╝   ╚══════╝          ║
    ║                                                                   ║
    ║              ███╗   ██╗███████╗███████╗ ██████╗                  ║
    ║              ████╗  ██║██╔════╝██╔════╝██╔═══██╗                  ║
    ║              ██╔██╗ ██║█████╗  ███████╗██║   ██║                  ║
    ║              ██║╚██╗██║██╔══╝  ╚════██║██║   ██║                  ║
    ║              ██║ ╚████║███████╗███████║╚██████╔╝                  ║
    ║              ╚═╝  ╚═══╝╚══════╝╚══════╝ ╚═════╝                   ║
    ║                                                                   ║
    ║   ── A Text-Based Puzzle Adventure ── v""" + VERSION + r"""                    ║
    ║                                                                   ║
    ║   You wake up in a locked cell. No memory of how you got here.    ║
    ║   Find items. Solve puzzles. Escape.                            ║
    ║                                                                   ║
    ║   Type 'help' for commands. Press ENTER to begin...               ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(title)
    try:
        input()
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)

def show_victory(state):
    """Display the victory screen with score and rank."""
    elapsed = state.elapsed_seconds()
    mins, secs = divmod(elapsed, 60)
    final_score = state.score()
    rank = GameState.rank_for_score(final_score)
    items_found = len([i for i in state.inventory if i in ITEMS])

    clear()
    print(r"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║     ███████╗ ██████╗ ██╗   ██╗ █████╗ ██████╗ ███████╗           ║
    ║     ██╔════╝██╔═══██╗██║   ██║██╔══██╗██╔══██╗██╔════╝           ║
    ║     ███████╗██║   ██║██║   ██║███████║██████╔╝█████╗             ║
    ║     ╚════██║██║▄▄ ██║██║   ██║██╔══██║██╔═══╝ ██╔══╝             ║
    ║     ███████║╚██████╔╝╚██████╔╝██║  ██║██║     ███████╗           ║
    ║     ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚══════╝           ║
    ║                                                                   ║
    ║   ── YOU ESCAPED! ──                                              ║
    ║                                                                   ║
    ║   The exit door opens to blinding daylight. You stumble out        ║
    ║   into fresh air, gasping. Behind you, the facility door           ║
    ║   seals shut with a final, decisive clang.                        ║
    ║                                                                   ║
    ║   You're free. But questions remain:                              ║
    ║   Who is Dr. Elara Voss? What was Project Mnemosyne?              ║
    ║   And why were you locked inside...                              ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """)
    print(f"    Time:   {mins}m {secs}s")
    print(f"    Moves:  {state.moves}")
    print(f"    Items:  {items_found}")
    print(f"    Score:  {final_score}")
    print(f"    Rank:   {rank}")
    print()

    # Clean up save file on successful escape
    GameState.delete_save()

# ─── Main game loop ─────────────────────────────────────────────────

def run_game():
    """Main game loop: initialize state, handle commands, manage game flow."""
    state = GameState()
    show_title()

    clear()
    narrate("═════════════════════════════════════════════════════════════")
    narrate("You wake up. Cold concrete. Flickering light. Pounding head.")
    narrate("You're in a cell. The door is locked. You need to get out.")
    narrate("═════════════════════════════════════════════════════════════")
    print()
    do_look(state)

    while not state.escaped:
        try:
            cmd = prompt()
        except (EOFError, KeyboardInterrupt):
            print()
            narrate("You give up and sit down. The walls close in slowly...")
            break

        if not cmd:
            continue

        # Record command history
        state.command_history.append(cmd)

        verb, args = parse_command(cmd)

        if verb is None:
            continue
        elif verb == "quit":
            # Offer to save before quitting
            if not state.escaped:
                narrate("Save before quitting? (y/n)")
                try:
                    answer = input("\033[1;36m▸ \033[0m").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    answer = "n"
                if answer.startswith("y"):
                    do_save(state)
            narrate("You give up and sit down. The walls close in slowly...")
            break
        elif verb == "help":
            do_help(state)
        elif verb == "look":
            do_look(state, args)
        elif verb == "go":
            do_go(state, args)
        elif verb == "take":
            do_take(state, args)
        elif verb == "drop":
            do_drop(state, args)
        elif verb == "use":
            do_use(state, args)
        elif verb == "combine":
            do_combine(state, args)
        elif verb == "inventory":
            do_inventory(state)
        elif verb == "read":
            do_look(state, args)
        elif verb == "hint":
            do_hint(state)
        elif verb == "status":
            do_status(state)
        elif verb == "save":
            do_save(state)
        elif verb == "load":
            loaded = do_load(state)
            if loaded is not None:
                state = loaded
                # Show current room after loading
                do_look(state)
        elif verb == "history":
            do_history(state)
        elif args and any(kw in cmd for kw in ["3333", "472", "4-7-2"]):
            do_enter_code(state, cmd)
        else:
            # Check if they're trying to interact with something specific
            key, obj = get_interactable(state, cmd)
            if obj:
                if obj.get("is_keypad") and "north" in state.room["locked"]:
                    handle_keypad(state)
                elif obj.get("is_cabinet_lock") and "cabinet_opened" not in state.flags:
                    handle_cabinet_code(state)
                elif obj.get("is_safe") and "safe_opened" not in state.flags:
                    handle_safe_combination(state)
                else:
                    narrate(obj["inspect"])
            else:
                narrate(f"You can't '{cmd}'. Type 'help' for commands.")

        state.moves += 1

        # Random ambient message after some commands
        maybe_ambient(state.current_room, chance=0.12)

    if state.escaped:
        show_victory(state)

# ─── CLI entry point ─────────────────────────────────────────────────

def main():
    """Parse CLI arguments and start the game."""
    parser = argparse.ArgumentParser(
        prog="escape_room",
        description="CLI Escape Room — A text-based puzzle adventure for your terminal. "
                     "Explore rooms, find items, solve puzzles, and escape!",
        epilog="Type 'help' inside the game for command reference.",
    )
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"%(prog)s {VERSION}",
        help="Show version number and exit",
    )

    # If there's a save file, offer to resume
    if GameState.has_save():
        print("A saved game was found!")
        print("  [1] Resume saved game")
        print("  [2] Start new game")
        print("  [3] Delete save and start new")
        try:
            choice = input("Choose (1/2/3): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        if choice == "1":
            state = GameState.load()
            if state is None:
                print("Error loading save. Starting new game.")
                run_game()
            else:
                clear()
                narrate("Game loaded! You pick up where you left off...")
                do_look(state)
                while not state.escaped:
                    try:
                        cmd = prompt()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        narrate("You give up and sit down. The walls close in slowly...")
                        break

                    if not cmd:
                        continue
                    state.command_history.append(cmd)
                    verb, args = parse_command(cmd)

                    if verb is None:
                        continue
                    elif verb == "quit":
                        narrate("Save before quitting? (y/n)")
                        try:
                            answer = input("\033[1;36m▸ \033[0m").strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            answer = "n"
                        if answer.startswith("y"):
                            do_save(state)
                        narrate("You give up and sit down. The walls close in slowly...")
                        break
                    elif verb == "help":
                        do_help(state)
                    elif verb == "look":
                        do_look(state, args)
                    elif verb == "go":
                        do_go(state, args)
                    elif verb == "take":
                        do_take(state, args)
                    elif verb == "drop":
                        do_drop(state, args)
                    elif verb == "use":
                        do_use(state, args)
                    elif verb == "combine":
                        do_combine(state, args)
                    elif verb == "inventory":
                        do_inventory(state)
                    elif verb == "read":
                        do_look(state, args)
                    elif verb == "hint":
                        do_hint(state)
                    elif verb == "status":
                        do_status(state)
                    elif verb == "save":
                        do_save(state)
                    elif verb == "load":
                        loaded = do_load(state)
                        if loaded is not None:
                            state = loaded
                            do_look(state)
                    elif verb == "history":
                        do_history(state)
                    elif args and any(kw in cmd for kw in ["3333", "472", "4-7-2"]):
                        do_enter_code(state, cmd)
                    else:
                        key, obj = get_interactable(state, cmd)
                        if obj:
                            if obj.get("is_keypad") and "north" in state.room["locked"]:
                                handle_keypad(state)
                            elif obj.get("is_cabinet_lock") and "cabinet_opened" not in state.flags:
                                handle_cabinet_code(state)
                            elif obj.get("is_safe") and "safe_opened" not in state.flags:
                                handle_safe_combination(state)
                            else:
                                narrate(obj["inspect"])
                        else:
                            narrate(f"You can't '{cmd}'. Type 'help' for commands.")

                    state.moves += 1
                    maybe_ambient(state.current_room, chance=0.12)

                if state.escaped:
                    show_victory(state)
        elif choice == "3":
            GameState.delete_save()
            print("Save deleted. Starting new game...\n")
            run_game()
        else:
            run_game()
    else:
        # No save file — just start normally
        # Parse args first to handle --help/--version
        parser.parse_args()
        run_game()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. The walls remain closed...")
        sys.exit(0)