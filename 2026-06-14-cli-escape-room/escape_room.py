#!/usr/bin/env python3
"""
CLI Escape Room — A text-based escape room game for your terminal.
Explore rooms, find items, solve puzzles, and escape!
"""

import sys
import time
import textwrap

# ─── Display helpers ────────────────────────────────────────────────

WIDTH = 70

def clear():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def narrate(text, delay=0.015):
    for line in textwrap.wrap(text, width=WIDTH):
        for ch in line:
            sys.stdout.write(ch)
            sys.stdout.flush()
            time.sleep(delay)
        print()
    print()

def divider():
    print("─" * WIDTH)

def box(text):
    w = WIDTH
    lines = textwrap.wrap(text, width=w - 4)
    print(f"┌{'─' * (w-2)}┐")
    for line in lines:
        print(f"│ {line:<{w-4}} │")
    print(f"└{'─' * (w-2)}┘")

def prompt():
    return input("\n\033[1;36m▸ What do you do?\033[0m ").strip().lower()

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
}

# ─── Game State ─────────────────────────────────────────────────────

class GameState:
    def __init__(self):
        self.current_room = "cell"
        self.inventory = []
        self.flags = set()  # tracks puzzle states
        self.moves = 0
        self.start_time = time.time()
        self.escaped = False

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
        return self.rooms[self.current_room]

    def has_item(self, item_id):
        return item_id in self.inventory

    def take_item(self, item_id, from_room=True):
        if item_id not in self.inventory:
            self.inventory.append(item_id)
            if from_room:
                room_items = self.room["items"]
                if item_id in room_items:
                    room_items.remove(item_id)

    def remove_item(self, item_id):
        if item_id in self.inventory:
            self.inventory.remove(item_id)

    def unlock(self, direction):
        if direction in self.room["locked"]:
            del self.room["locked"][direction]

    def is_locked(self, direction):
        return direction in self.room["locked"]

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

# ─── Command Parser ─────────────────────────────────────────────────

def parse_command(cmd):
    cmd = cmd.strip().lower()
    if not cmd:
        return None, []

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
    }

    verb_map = {}
    for main, alts in aliases.items():
        verb_map[main] = main
        for a in alts:
            verb_map[a] = main

    words = cmd.split()
    verb = words[0]
    args = " ".join(words[1:]) if len(words) > 1 else ""

    if cmd.startswith("pick up"):
        verb = "take"
        args = cmd[7:].strip()
    elif cmd.startswith("look at"):
        verb = "look"
        args = cmd[7:].strip()

    resolved = verb_map.get(verb, verb)
    return resolved, args

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

def do_look(state, target=""):
    room = state.room

    # Dark room check
    if room.get("dark") and not state.has_item("flashlight"):
        narrate(room.get("dark_desc", "It's too dark to see."))
        return

    if not target:
        desc = room["first_desc"] if not room["visited"] else room["desc"]
        narrate(desc)

        # Show items
        if room["items"]:
            item_names = [ITEMS[i]["name"] for i in room["items"] if i in ITEMS]
            if item_names:
                narrate("You notice: " + ", ".join(item_names))

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

def do_take(state, target):
    room = state.room
    if not target:
        narrate("Take what?")
        return

    # Check room items
    for item_id in room["items"]:
        if item_id in ITEMS and target in ITEMS[item_id]["name"].lower():
            state.take_item(item_id)
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

def do_use(state, target):
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

    # Special: combine note fragments
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
    if not state.inventory:
        narrate("Your pockets are empty.")
        return
    print("\n┌─ INVENTORY ────────────────────────────────────────────────────┐")
    for item_id in state.inventory:
        if item_id in ITEMS:
            print(f"│  • {ITEMS[item_id]['name']:<60} │")
    print("└────────────────────────────────────────────────────────────────┘\n")

def do_help(state):
    box(
        "COMMANDS: look [thing] | go <direction> | take <item> | "
        "use <item> on <thing> | combine <things> | inventory | help | quit. "
        "Directions: north, south, east, west. Tip: examine everything, combine clues!"
    )

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
    """Interactive keypad entry."""
    narrate("The keypad display blinks, waiting for a 4-digit code.")
    attempts = 3
    while attempts > 0:
        code = input("\033[1;33m    ▸ Enter 4-digit code: \033[0m").strip()
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
    """Interactive cabinet code entry."""
    narrate("The cabinet lock requires a 3-digit code.")
    attempts = 3
    while attempts > 0:
        code = input("\033[1;33m    ▸ Enter 3-digit code: \033[0m").strip().replace("-", "").replace(" ", "")
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
    combo = input("\033[1;33m    ▸ Enter combination: \033[0m").strip().lower()
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

# ─── Main game loop ─────────────────────────────────────────────────

def show_title():
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
    ║   ── A Text-Based Puzzle Adventure ──                            ║
    ║                                                                   ║
    ║   You wake up in a locked cell. No memory of how you got here.    ║
    ║   Find items. Solve puzzles. Escape.                            ║
    ║                                                                   ║
    ║   Type 'help' for commands. Press ENTER to begin...               ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(title)
    input()

def show_victory(state):
    elapsed = int(time.time() - state.start_time)
    mins, secs = divmod(elapsed, 60)
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
    items_found = len([i for i in state.inventory if i in ITEMS])
    print(f"    Time: {mins}m {secs}s  |  Moves: {state.moves}  |  Items: {items_found}")
    print()

def run_game():
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
        cmd = prompt()
        verb, args = parse_command(cmd)

        if verb is None:
            continue
        elif verb == "quit":
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
        elif verb == "use":
            do_use(state, args)
        elif verb == "combine":
            do_combine(state, args)
        elif verb == "inventory":
            do_inventory(state)
        elif verb == "read":
            do_look(state, args)
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

    if state.escaped:
        show_victory(state)

if __name__ == "__main__":
    try:
        run_game()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. The walls remain closed...")
        sys.exit(0)