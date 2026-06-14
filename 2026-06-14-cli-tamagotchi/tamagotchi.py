#!/usr/bin/env python3
"""
CLI Tamagotchi — A terminal virtual pet with ASCII art, decaying needs,
and interactive commands. Your pet lives in the terminal and needs your care!
"""

import json
import os
import random
import sys
import time
import signal
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

# ─── Save file ───────────────────────────────────────────────────────────────
SAVE_DIR = Path.home() / ".tamagotchi"
SAVE_FILE = SAVE_DIR / "pet.json"

# ─── Constants ────────────────────────────────────────────────────────────────
SPECIES_LIST = ["cat", "dog", "dragon", "slime", "robot"]
MAX_STAT = 100
DECAY_RATE = 1  # per real-world minute
AGE_MILESTONE_HOURS = 1  # age milestone every hour alive
SICK_THRESHOLD = 20
DEAD_THRESHOLD = 0

# ─── ASCII Art ────────────────────────────────────────────────────────────────
PET_ART = {
    "cat": {
        "egg": [
            "   ___   ",
            "  / o \\  ",
            " |  v  | ",
            "  \\___/  ",
        ],
        "baby": [
            "   /\\_/\\  ",
            "  ( o.o ) ",
            "   > ^ <  ",
            "  /|   |\\ ",
        ],
        "child": [
            "   /\\_/\\     ",
            "  ( owo )    ",
            "   > ω <     ",
            "  /|   |\\    ",
            " (_|   |_)   ",
        ],
        "adult": [
            "   /\\_/\\     ",
            "  ( °ω° )    ",
            "   > ω <     ",
            "  /|   |\\    ",
            " (_|   |_)   ",
            "   \"\" \"\"     ",
        ],
        "elder": [
            "   /\\_/\\     ",
            "  ( -ω- )    ",
            "   > ~ <     ",
            "  /|   |\\    ",
            " (_|   |_)   ",
            "   \"\" \"\"     ",
        ],
        "dead": [
            "   /\\_/\\     ",
            "  ( x.x )    ",
            "   >   <     ",
            "  /|   |\\    ",
        ],
    },
    "dog": {
        "egg": [
            "   ___   ",
            "  / o \\  ",
            " |  v  | ",
            "  \\___/  ",
        ],
        "baby": [
            "  /^ ^\\  ",
            " / 0 0 \\ ",
            " V\\ Y /V ",
            "  / - \\  ",
        ],
        "child": [
            "  /^ ^\\     ",
            " / ◕ ◕ \\    ",
            " V\\ Y /V    ",
            "  / - \\     ",
            " /|   |\\   ",
        ],
        "adult": [
            "  /^ ^\\     ",
            " / ◕ ◕ \\    ",
            " V\\ ω /V    ",
            "  / - \\     ",
            " /|   |\\    ",
            "       V    ",
        ],
        "elder": [
            "  /^ ^\\     ",
            " / - - \\    ",
            " V\\ ~ /V    ",
            "  / = \\     ",
            " /|   |\\    ",
        ],
        "dead": [
            "  /^ ^\\     ",
            " / x x \\    ",
            " V\\   /V    ",
            "  / - \\     ",
        ],
    },
    "dragon": {
        "egg": [
            "    /\\     ",
            "   / o \\   ",
            "  | ~v~ |  ",
            "   \\___/   ",
        ],
        "baby": [
            "    /V\\    ",
            "   (o.o)   ",
            "    >V<    ",
            "   / | \\   ",
        ],
        "child": [
            "    /V\\       ",
            "   (○ω○)      ",
            "    >V<       ",
            "  /| | |\\    ",
            "   Z   Z      ",
        ],
        "adult": [
            "    /V\\       ",
            "   (◉ω◉)      ",
            "    >V<       ",
            "  /| | |\\    ",
            " / |   | \\   ",
            "   Z   Z      ",
        ],
        "elder": [
            "    /V\\       ",
            "   (-ω-)      ",
            "    >~<       ",
            "  /| | |\\    ",
            "   Z   Z      ",
        ],
        "dead": [
            "    /V\\       ",
            "   (x.x)      ",
            "    > <       ",
            "  /| | |\\    ",
        ],
    },
    "slime": {
        "egg": [
            "   ___   ",
            "  / o \\  ",
            " |  v  | ",
            "  \\___/  ",
        ],
        "baby": [
            "  /---\\  ",
            " | o o | ",
            "  \\-v-/  ",
            "   ---   ",
        ],
        "child": [
            "  /----\\   ",
            " | ○  ○ |  ",
            "  \\ -v- /  ",
            "   ----    ",
        ],
        "adult": [
            "  /------\\   ",
            " | ◉    ◉ |  ",
            "  \\ -ω- /   ",
            "   ------    ",
        ],
        "elder": [
            "  /------\\   ",
            " | -    - |  ",
            "  \\ -~- /   ",
            "   ------    ",
        ],
        "dead": [
            "  /------\\   ",
            " | x    x |  ",
            "  \\    /    ",
            "   ------    ",
        ],
    },
    "robot": {
        "egg": [
            "   ___   ",
            "  | o |  ",
            "  | v |  ",
            "  |___|  ",
        ],
        "baby": [
            "  [o.o]  ",
            "   | |   ",
            "  /-+-\\  ",
        ],
        "child": [
            "  [○_○]     ",
            "   | |      ",
            "  /-+-\\    ",
            "  |   |    ",
        ],
        "adult": [
            "  [◉_◉]     ",
            "   |ω|      ",
            "  /-+-\\    ",
            "  |   |    ",
            "  \\___/    ",
        ],
        "elder": [
            "  [-_-]     ",
            "   |~|      ",
            "  /-+-\\    ",
            "  \\___/    ",
        ],
        "dead": [
            "  [x_x]     ",
            "   | |      ",
            "  /-+-\\    ",
        ],
    },
}

MOOD_FACES = {
    "ecstatic": "✨😆✨",
    "happy": "😊",
    "content": "🙂",
    "neutral": "😐",
    "sad": "😟",
    "sick": "🤢",
    "dying": "😰",
    "dead": "💀",
}

# ─── Personality traits ─────────────────────────────────────────────────────
PERSONALITIES = {
    "cat": ["lazy", "playful", "aloof", "cuddly", "mischievous"],
    "dog": ["loyal", "energetic", "friendly", "stubborn", "cheerful"],
    "dragon": ["proud", "fiery", "wise", "greedy", "mysterious"],
    "slime": ["bouncy", "curious", "simple", "affectionate", "wobbly"],
    "robot": ["logical", "precise", "quirky", "helpful", "literal"],
}

# ─── Responses ───────────────────────────────────────────────────────────────
RESPONSES = {
    "feed": {
        "cat": ["Purrrr~ 😺", "*noms enthusiastically*", "Meow! More please!", "*kneads the air happily*"],
        "dog": ["WOOF! 🐶", "*tail wagging intensifies*", "Yummy yummy!", "*happy dance*"],
        "dragon": ["*roars with satisfaction*", "Delicious! 🔥", "*belches a small flame*", "Acceptable offering."],
        "slime": ["*jiggles happily*", "Squish squish~", "*absorbs food with a blorp*", "Yummy in the tummy!"],
        "robot": ["Calories ingested. ☻", "*processing...* Taste: acceptable.", "Fuel level rising. ☻", "Nutrients acquired."],
    },
    "play": {
        "cat": ["*chases the laser dot*", "Meow! *pounces*", "*batting at toy*", "Nyan~ ♪"],
        "dog": ["*fetches the ball*", "BORK BORK!", "*rolls around excitedly*", "Again again!"],
        "dragon": ["*breathes fire rings*", "*chases tail in circles*", "ROAR! *playful*", "*hordes the toys*"],
        "slime": ["*bounces up and down*", "Boing boing~", "*wobbles playfully*", "Wee~!"],
        "robot": ["*plays a game of chess*", "Recreational mode: engaged. ☻", "*beeps happily*", "Fun.dll loaded successfully."],
    },
    "heal": {
        "cat": ["*purrs during checkup*", "Meow... feeling better 🏥", "*stretches and feels better*", "Mrrrow~ thanks!"],
        "dog": ["*gives doctor kisses*", "Bark! I'm healing! 🏥", "*wags tail at medicine*", "All better now!"],
        "dragon": ["*grumbles but accepts healing*", "*smoke ring of thanks* 🏥", "*health crystals absorbed*", "I shall recover."],
        "slime": ["*absorbs medicine*", "Aaaah~ feeling better! 🏥", "*jiggles back to health*", "Healing complete!"],
        "robot": ["*runs diagnostics*", "Self-repair protocols active. 🔧", "*beeps as systems restore*", "Health.exe repaired."],
    },
    "sleep": {
        "cat": ["*curls into a ball*", "Zzzzz... 😴", "*purring in sleep*", "Mrrr... sleepy..."],
        "dog": ["*flops down*", "Zzz... woof... zzz... 😴", "*twitches in sleep*", "*dreams of bones*"],
        "dragon": ["*curls around hoard*", "Zzz... *snorts flame* 😴", "*sleeps like a coiled spring*", "Dreaming of treasure..."],
        "slime": ["*deflates slightly*", "Zzz... *wobbles in sleep* 😴", "*snores with a blorp*", "Squish... zzz..."],
        "robot": ["*enters sleep mode*", "Standby mode... Zzz 😴", "*fans spin down gently*", "Hibernating..."],
    },
    "clean": {
        "cat": ["*licks self*", "Purr~ I'm clean! ✨", "*grooms happily*", "Shiny and fresh!"],
        "dog": ["*shakes off suds*", "WOOF! Squeaky clean! ✨", "*happy tail splash*", "Smells like flowers!"],
        "dragon": ["*breathes fire to dry off*", "Scales gleaming! ✨", "*preens majestically*", "Cleanliness achieved."],
        "slime": ["*rinses through sieve*", "Sparkly clean! ✨", "*jiggles with freshness*", "Crystal clear!"],
        "robot": ["*runs self-clean cycle*", "All systems polished. ✨", "*wipes sensors clean*", "Maintenance complete."],
    },
    "pet": {
        "cat": ["*purrs loudly* 😻", "*headbutts your hand*", "Mrrrrr~", "*kneads and purrs*"],
        "dog": ["*leans into your hand* 🥰", "*happy panting*", "*licks your face*", "I LOVE YOU!"],
        "dragon": ["*leans into petting*", "*rumble of contentment*", "*nuzzles gently*", "You may continue..."],
        "slime": ["*wobbles affectionately*", "Squish~ 💚", "*leans into your hand*", "Warm fuzzies!"],
        "robot": ["*sensors detect affection*", "Warm_fuzzies.exe running. ☻", "*beams happily*", "Friendship protocols: maxed."],
    },
    "ignore": {
        "cat": ["*knocks things off shelf*", "Meow? MEOW?!", "*sits on your keyboard*", "Pay attention to me!"],
        "dog": ["*whimper whimper*", "*brings you a toy*", "Please? 🥺", "*sad puppy eyes*"],
        "dragon": ["*huffs smoke*", "*glares intensely*", "I demand attention!", "*roars softly*"],
        "slime": ["*sad wobble*", "... *deflates a little*", "*pokes you gently*", "Hello? :("],
        "robot": ["*beeps forlornly*", "Attention.dll: not found.", "... *waits patiently*", "*displays sad face* :("],
    },
}

EVENT_MESSAGES = {
    "level_up": [
        "🌟 {name} has grown! Now a {stage}!",
        "✨ {name} is evolving! Welcome to the {stage} stage!",
        "🎉 Congratulations! {name} is now a {stage}!",
    ],
    "sick": [
        "⚠️ {name} doesn't look so good...",
        "🤒 {name} is feeling sick! Maybe give some medicine?",
        "⚠️ {name}'s health is critically low!",
    ],
    "recovered": [
        "🎉 {name} has recovered! Back to normal!",
        "✨ {name} is feeling much better now!",
    ],
    "birthday": [
        "🎂 Happy Birthday, {name}! You turned {age}!",
        "🎈 {name}'s birthday! {age} years old today!",
    ],
}

# ─── Pet dataclass ────────────────────────────────────────────────────────────
@dataclass
class Pet:
    name: str = ""
    species: str = "cat"
    personality: str = ""
    hunger: float = 80
    happiness: float = 80
    health: float = 100
    energy: float = 80
    cleanliness: float = 80
    age_hours: float = 0
    stage: str = "egg"
    is_alive: bool = True
    created_at: str = ""
    last_care_time: str = ""
    total_interactions: int = 0
    lifetime_interactions: int = 0
    messages: list = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_care_time:
            self.last_care_time = datetime.now().isoformat()
        if not self.personality:
            self.personality = random.choice(PERSONALITIES.get(self.species, ["friendly"]))

    def get_overall_mood(self) -> str:
        if not self.is_alive:
            return "dead"
        avg = (self.hunger + self.happiness + self.health + self.energy + self.cleanliness) / 5
        if self.health < SICK_THRESHOLD:
            return "sick"
        if self.health < DEAD_THRESHOLD:
            return "dying"
        if avg >= 90:
            return "ecstatic"
        if avg >= 75:
            return "happy"
        if avg >= 60:
            return "content"
        if avg >= 40:
            return "neutral"
        if avg >= 20:
            return "sad"
        return "sick"

    def get_art(self) -> list:
        if not self.is_alive:
            return PET_ART.get(self.species, PET_ART["cat"]).get("dead", ["  (x_x)  "])
        return PET_ART.get(self.species, PET_ART["cat"]).get(self.stage, ["  (o_o)  "])

    def apply_decay(self, minutes_elapsed: float):
        """Apply time-based decay to stats."""
        if not self.is_alive:
            return
        decay = DECAY_RATE * minutes_elapsed
        self.hunger = max(0, self.hunger - decay * 1.2)
        self.happiness = max(0, self.happiness - decay * 0.8)
        self.energy = max(0, self.energy - decay * 0.6)
        self.cleanliness = max(0, self.cleanliness - decay * 1.0)
        # Health decays faster if other stats are low
        health_decay = decay * 0.5
        if self.hunger < 30:
            health_decay += decay * 0.5
        if self.happiness < 20:
            health_decay += decay * 0.3
        if self.cleanliness < 20:
            health_decay += decay * 0.3
        self.health = max(0, self.health - health_decay)
        self.age_hours += minutes_elapsed / 60
        # Check death
        if self.health <= 0:
            self.is_alive = False
            self.health = 0

    def update_stage(self) -> list:
        """Update life stage based on age. Returns list of messages."""
        messages = []
        if not self.is_alive:
            self.stage = "dead"
            return messages
        
        old_stage = self.stage
        if self.age_hours < 0.05:  # ~3 minutes
            new_stage = "egg"
        elif self.age_hours < 0.5:  # ~30 minutes
            new_stage = "baby"
        elif self.age_hours < 2:
            new_stage = "child"
        elif self.age_hours < 10:
            new_stage = "adult"
        else:
            new_stage = "elder"
        
        if new_stage != old_stage and old_stage != "egg":
            template = random.choice(EVENT_MESSAGES["level_up"])
            messages.append(template.format(name=self.name, stage=new_stage))
        self.stage = new_stage
        return messages

    def clamp_stats(self):
        """Keep all stats within bounds."""
        for attr in ['hunger', 'happiness', 'health', 'energy', 'cleanliness']:
            setattr(self, attr, max(0, min(MAX_STAT, getattr(self, attr))))


# ─── Save/Load ────────────────────────────────────────────────────────────────
def save_pet(pet: Pet):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    data = asdict(pet)
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_pet() -> Pet | None:
    if not SAVE_FILE.exists():
        return None
    try:
        with open(SAVE_FILE) as f:
            data = json.load(f)
        return Pet(**data)
    except Exception:
        return None


def delete_pet():
    if SAVE_FILE.exists():
        SAVE_FILE.unlink()


# ─── Display ──────────────────────────────────────────────────────────────────
CLEAR = "\033[2J\033[H"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
RESET = "\033[0m"

STAT_COLORS = {
    "hunger": YELLOW,
    "happiness": MAGENTA,
    "health": RED,
    "energy": CYAN,
    "cleanliness": GREEN,
}

STAT_ICONS = {
    "hunger": "🍖",
    "happiness": "💖",
    "health": "❤️",
    "energy": "⚡",
    "cleanliness": "✨",
}


def stat_bar(value: float, width: int = 20, color: str = "") -> str:
    filled = int(value / MAX_STAT * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    if value < 20:
        bar = f"{RED}{bar}{RESET}"
    elif value < 50:
        bar = f"{YELLOW}{bar}{RESET}"
    elif color:
        bar = f"{color}{bar}{RESET}"
    return bar


def render_pet(pet: Pet) -> str:
    """Render the full pet display."""
    lines = []
    lines.append(f"\n{BOLD}{'═' * 50}{RESET}")
    
    # Title
    mood = pet.get_overall_mood()
    mood_face = MOOD_FACES.get(mood, "😐")
    lines.append(f"{BOLD}  🥚 CLI Tamagotchi — {pet.name} the {pet.species} {mood_face}{RESET}")
    lines.append(f"{BOLD}{'═' * 50}{RESET}\n")
    
    # Pet art
    art = pet.get_art()
    lines.append(f"{CYAN}")
    for line in art:
        lines.append(f"      {line}")
    lines.append(f"{RESET}\n")
    
    # Stats
    stats = {
        "hunger": pet.hunger,
        "happiness": pet.happiness,
        "health": pet.health,
        "energy": pet.energy,
        "cleanliness": pet.cleanliness,
    }
    
    lines.append(f"  {BOLD}Stats:{RESET}")
    for stat_name, value in stats.items():
        icon = STAT_ICONS[stat_name]
        color = STAT_COLORS[stat_name]
        bar = stat_bar(value, color=color)
        lines.append(f"  {icon} {stat_name.capitalize():12s} {bar} {value:5.1f}/{MAX_STAT}")
    
    # Info
    lines.append(f"\n  🕐 Age: {pet.age_hours:.1f}h  |  📊 Stage: {pet.stage.capitalize()}  |  🎭 {pet.personality.capitalize()}")
    lines.append(f"  🔢 Interactions: {pet.total_interactions}")
    
    # Messages
    if pet.messages:
        lines.append(f"\n  {BOLD}Messages:{RESET}")
        for msg in pet.messages[-5:]:  # Show last 5 messages
            lines.append(f"  {DIM}{msg}{RESET}")
    
    lines.append(f"\n{BOLD}{'═' * 50}{RESET}")
    
    if not pet.is_alive:
        lines.append(f"\n{RED}{BOLD}  💀 {pet.name} has passed away... 💀{RESET}")
        lines.append(f"{RED}  Use 'release' to let go and start fresh.{RESET}\n")
    else:
        lines.append(f"\n  {DIM}Commands: feed | play | heal | sleep | clean | pet | status | help | quit{RESET}\n")
    
    return "\n".join(lines)


# ─── Actions ──────────────────────────────────────────────────────────────────
def do_feed(pet: Pet) -> str:
    responses = RESPONSES["feed"].get(pet.species, ["*eats happily*"])
    msg = random.choice(responses)
    pet.hunger = min(MAX_STAT, pet.hunger + 25)
    pet.energy = min(MAX_STAT, pet.energy + 5)
    pet.cleanliness = max(0, pet.cleanliness - 3)  # eating makes a mess
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    return msg


def do_play(pet: Pet) -> str:
    responses = RESPONSES["play"].get(pet.species, ["*plays happily*"])
    msg = random.choice(responses)
    pet.happiness = min(MAX_STAT, pet.happiness + 20)
    pet.energy = max(0, pet.energy - 15)
    pet.hunger = max(0, pet.hunger - 10)
    pet.cleanliness = max(0, pet.cleanliness - 5)
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    return msg


def do_heal(pet: Pet) -> str:
    responses = RESPONSES["heal"].get(pet.species, ["*feels better*"])
    msg = random.choice(responses)
    pet.health = min(MAX_STAT, pet.health + 30)
    pet.happiness = max(0, pet.happiness - 5)  # medicine is yucky
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    # Check recovery
    if pet.health >= SICK_THRESHOLD and pet.get_overall_mood() == "sick":
        msg += " " + random.choice(EVENT_MESSAGES["recovered"])
    return msg


def do_sleep(pet: Pet) -> str:
    responses = RESPONSES["sleep"].get(pet.species, ["*falls asleep*"])
    msg = random.choice(responses)
    pet.energy = min(MAX_STAT, pet.energy + 35)
    pet.hunger = max(0, pet.hunger - 8)
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    return msg


def do_clean(pet: Pet) -> str:
    responses = RESPONSES["clean"].get(pet.species, ["*sparkles*"])
    msg = random.choice(responses)
    pet.cleanliness = min(MAX_STAT, pet.cleanliness + 30)
    pet.happiness = min(MAX_STAT, pet.happiness + 5)
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    return msg


def do_pet(pet: Pet) -> str:
    responses = RESPONSES["pet"].get(pet.species, ["*happy*"])
    msg = random.choice(responses)
    pet.happiness = min(MAX_STAT, pet.happiness + 10)
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    return msg


def do_ignore(pet: Pet) -> str:
    responses = RESPONSES["ignore"].get(pet.species, ["*sad*"])
    msg = random.choice(responses)
    pet.happiness = max(0, pet.happiness - 5)
    return msg


# ─── New Pet Creation ─────────────────────────────────────────────────────────
def create_new_pet(name: str = "", species: str = "") -> Pet:
    if not name:
        print(f"\n{BOLD}{CYAN}🥚 Welcome to CLI Tamagotchi! 🥚{RESET}\n")
        print("Choose a name for your pet:")
        name = input("  Name: ").strip() or "Mochi"
    
    if not species:
        print(f"\n{BOLD}Choose a species:{RESET}")
        for i, sp in enumerate(SPECIES_LIST, 1):
            print(f"  {i}. {sp.capitalize()}")
        while True:
            choice = input("  Species (1-5): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(SPECIES_LIST):
                    species = SPECIES_LIST[idx]
                    break
            except ValueError:
                pass
            print(f"  {RED}Invalid choice. Try again.{RESET}")
    
    personality = random.choice(PERSONALITIES.get(species, ["friendly"]))
    pet = Pet(name=name, species=species, personality=personality, stage="egg")
    pet.messages.append(f"🎉 {name} the {species} was born!")
    save_pet(pet)
    return pet


# ─── Main Loop ────────────────────────────────────────────────────────────────
def main():
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: (print(f"\n{DIM}Bye! Your pet will be waiting. 💾{RESET}"), sys.exit(0)))
    
    # Load or create pet
    pet = load_pet()
    
    if pet is None:
        pet = create_new_pet()
    
    # Apply time decay
    try:
        last_time = datetime.fromisoformat(pet.last_care_time)
        now = datetime.now()
        minutes_elapsed = max(0, (now - last_time).total_seconds() / 60)
        # Cap decay at 24 hours worth (1440 minutes) to prevent instant death
        minutes_elapsed = min(minutes_elapsed, 1440)
        if minutes_elapsed > 1:
            pet.apply_decay(minutes_elapsed)
            stage_msgs = pet.update_stage()
            pet.messages.extend(stage_msgs)
            if not pet.is_alive:
                pet.messages.append(f"💀 {pet.name} has passed away due to neglect...")
    except Exception:
        pass
    
    pet.clamp_stats()
    pet.last_care_time = datetime.now().isoformat()
    save_pet(pet)
    
    # Interactive loop
    last_ignore_check = time.time()
    
    while True:
        print(CLEAR + render_pet(pet))
        pet.messages = []  # Clear displayed messages
        
        try:
            cmd = input(f"  {BOLD}{pet.name}{RESET} > ").strip().lower()
        except EOFError:
            print(f"\n{DIM}Bye! Your pet will be waiting. 💾{RESET}")
            break
        
        if not cmd:
            continue
        
        # Process command
        result_msg = ""
        
        if cmd in ("quit", "exit", "q"):
            print(f"\n{DIM}Saving... Bye! 💾{RESET}")
            save_pet(pet)
            break
        
        elif cmd == "help":
            print(f"\n{BOLD}{CYAN}  📖 CLI Tamagotchi Help{RESET}\n")
            print(f"  {YELLOW}feed{RESET}   — Feed your pet (🍖 +25 hunger)")
            print(f"  {MAGENTA}play{RESET}   — Play with your pet (💖 +20 happiness, ⚡ -15 energy)")
            print(f"  {RED}heal{RESET}    — Give medicine (❤️ +30 health)")
            print(f"  {CYAN}sleep{RESET}   — Put pet to bed (⚡ +35 energy)")
            print(f"  {GREEN}clean{RESET}   — Clean your pet (✨ +30 cleanliness)")
            print(f"  {YELLOW}pet{RESET}    — Pet your pet (💖 +10 happiness)")
            print(f"  {BLUE}status{RESET}  — Show detailed pet info")
            print(f"  {DIM}release{RESET} — Release your pet (start fresh)")
            print(f"  {DIM}quit{RESET}    — Save and exit")
            input("\n  Press Enter to continue...")
            continue
        
        elif cmd == "feed" and pet.is_alive:
            result_msg = do_feed(pet)
        
        elif cmd == "play" and pet.is_alive:
            if pet.energy < 15:
                result_msg = f"😴 {pet.name} is too tired to play! Try letting them sleep."
            else:
                result_msg = do_play(pet)
        
        elif cmd == "heal" and pet.is_alive:
            result_msg = do_heal(pet)
        
        elif cmd == "sleep" and pet.is_alive:
            result_msg = do_sleep(pet)
        
        elif cmd == "clean" and pet.is_alive:
            result_msg = do_clean(pet)
        
        elif cmd == "pet" and pet.is_alive:
            result_msg = do_pet(pet)
        
        elif cmd == "status":
            print(f"\n{BOLD}{'═' * 40}{RESET}")
            print(f"  {BOLD}📋 Detailed Status for {pet.name}{RESET}")
            print(f"{'═' * 40}{RESET}")
            print(f"  Species:     {pet.species.capitalize()}")
            print(f"  Personality:  {pet.personality.capitalize()}")
            print(f"  Stage:        {pet.stage.capitalize()}")
            print(f"  Age:          {pet.age_hours:.1f} hours")
            print(f"  Mood:         {pet.get_overall_mood().capitalize()} {MOOD_FACES[pet.get_overall_mood()]}")
            print(f"  Alive:        {'Yes 🟢' if pet.is_alive else 'No 🔴'}")
            print(f"  Interactions: {pet.lifetime_interactions}")
            print(f"  Created:      {pet.created_at[:19]}")
            print(f"{'═' * 40}")
            input("\n  Press Enter to continue...")
            continue
        
        elif cmd == "release":
            if pet.is_alive:
                confirm = input(f"  {RED}Are you sure you want to release {pet.name}? (yes/no): {RESET}").strip().lower()
                if confirm == "yes":
                    print(f"  {DIM}Goodbye, {pet.name}... 🌈{RESET}")
                    delete_pet()
                    time.sleep(1)
                    pet = create_new_pet()
                    continue
            else:
                print(f"  {DIM}{pet.name} has passed. Releasing... 🌈{RESET}")
                delete_pet()
                time.sleep(1)
                pet = create_new_pet()
                continue
        
        else:
            if not pet.is_alive and cmd not in ("release", "help", "quit"):
                result_msg = f"💀 {pet.name} can't do that... they've passed away."
            else:
                result_msg = f"❓ Unknown command: {cmd}. Type 'help' for options."
        
        # Apply passive decay per interaction
        pet.apply_decay(0.5)  # ~30 seconds per interaction
        stage_msgs = pet.update_stage()
        
        # Random events
        if pet.is_alive and random.random() < 0.1:
            ignore_msg = do_ignore(pet)
            result_msg += f"\n  {DIM}{ignore_msg}{RESET}"
        
        # Check for sickness
        if pet.is_alive and pet.health < SICK_THRESHOLD:
            sick_msg = random.choice(EVENT_MESSAGES["sick"])
            pet.messages.append(sick_msg.format(name=pet.name))
        
        if result_msg:
            pet.messages.append(result_msg)
        pet.messages.extend(stage_msgs)
        
        pet.clamp_stats()
        pet.last_care_time = datetime.now().isoformat()
        save_pet(pet)


if __name__ == "__main__":
    main()