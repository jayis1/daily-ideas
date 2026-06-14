#!/usr/bin/env python3
"""
CLI Tamagotchi — A terminal virtual pet with ASCII art, decaying needs,
and interactive commands. Your pet lives in the terminal and needs your care!

Features:
  - 5 species with unique art, personality, and dialogue
  - Real-time stat decay between sessions
  - Life stages (egg → baby → child → adult → elder)
  - Teach tricks, explore adventures, earn achievements
  - Persistent save with automatic backup
  - --help and --version CLI flags

Usage:
  python3 tamagotchi.py          # Interactive mode
  python3 tamagotchi.py --help   # Show CLI help
  python3 tamagotchi.py --version # Show version
"""

import json
import os
import random
import shutil
import sys
import time
import signal
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path

# ─── Version ─────────────────────────────────────────────────────────────────
VERSION = "2.1.0"

# ─── Save file ───────────────────────────────────────────────────────────────
SAVE_DIR = Path.home() / ".tamagotchi"
SAVE_FILE = SAVE_DIR / "pet.json"
BACKUP_FILE = SAVE_DIR / "pet.json.bak"

# ─── Constants ────────────────────────────────────────────────────────────────
SPECIES_LIST = ["cat", "dog", "dragon", "slime", "robot"]
MAX_STAT = 100
DECAY_RATE = 1  # per real-world minute
AGE_MILESTONE_HOURS = 1  # age milestone every hour alive
SICK_THRESHOLD = 20
DYING_THRESHOLD = 10
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

# ─── Teach tricks (species-specific) ────────────────────────────────────────
TRICKS = {
    "cat": [
        ("High Five", "🐾 *raises paw and high-fives!*"),
        ("Roll Over", "🌀 *rolls over elegantly... then naps*"),
        ("Fetch", "🎾 *chases toy... then sits on it*"),
        ("Purr on Command", "🎵 *purrs so hard the room vibrates*"),
        ("Keyboard Walk", "⌨️ *walks across your keyboard: asdfghjkl*"),
    ],
    "dog": [
        ("Sit", "🦮 *sits promptly, tail still wagging*"),
        ("Shake", "🤝 *offers paw with enthusiasm*"),
        ("Roll Over", "🌀 *rolls over and over and over*"),
        ("Speak", "🗣️ WOOFWOOFWOOF!"),
        ("Play Dead", "💀 *dramatically flops... peeks with one eye*"),
    ],
    "dragon": [
        ("Fire Breath", "🔥 *breathes a controlled flame torch*"),
        ("Hover", "🪽 *hovers a few inches off the ground*"),
        ("Treasure Guard", "💎 *stands guard over a shiny pebble*"),
        ("Smoke Rings", "💨 *blows perfect smoke rings*"),
        ("Wing Spread", "🦖 *spreads wings majestically*"),
    ],
    "slime": [
        ("Shape Shift", "🟢 *becomes a cube... then a sphere... then a star*"),
        ("Bounce High", "🏀 *bounces incredibly high!*"),
        ("Absorb Object", "🧽 *absorbs a small pebble... then spits it out*"),
        ("Split", "🔄 *wobbles... almost splits in two!*"),
        ("Glow", "✨ *glows with bioluminescence!*"),
    ],
    "robot": [
        ("Calculate Pi", "🧮 *recites: 3.14159265358979...*"),
        ("Dance Mode", "🕺 *performs the robot dance*"),
        ("Translate", "🌍 *beeps in 47 languages*"),
        ("Scan", "📡 *scans surroundings: all clear*"),
        ("Self Diagnose", "🔧 *runs full diagnostic: 99.7% operational*"),
    ],
}

# ─── Explore events (adventures) ─────────────────────────────────────────────
EXPLORE_EVENTS = {
    "cat": [
        ("found a warm sunbeam", "happiness", 8),
        ("discovered a cardboard box", "happiness", 12),
        ("chased a moth", "happiness", 5),
        ("knocked a glass off the table", "cleanliness", -8),
        ("found a cozy blanket", "energy", 5),
        ("stared at a wall mysteriously", "happiness", 2),
        ("caught a toy mouse", "happiness", 10),
        ("got fur everywhere", "cleanliness", -5),
    ],
    "dog": [
        ("found a stick", "happiness", 10),
        ("dug a hole in the garden", "cleanliness", -10),
        ("chased their own tail", "happiness", 5),
        ("met a new friend", "happiness", 12),
        ("rolled in something smelly", "cleanliness", -15),
        ("found a hidden treat", "hunger", 8),
        ("barked at the mailman", "happiness", 3),
        ("brought back a soggy ball", "happiness", 6),
    ],
    "dragon": [
        ("found a shiny coin", "happiness", 10),
        ("roasted a marshmallow", "happiness", 8),
        ("accidentally set something on fire", "cleanliness", -12),
        ("discovered a hidden cave", "happiness", 15),
        ("hoarded some treasure", "happiness", 12),
        ("flew through some clouds", "energy", -5),
        ("breathed frost instead of fire", "happiness", 5),
        ("found a gemstone", "happiness", 14),
    ],
    "slime": [
        ("absorbed a puddle", "hunger", 6),
        ("bounced off a wall", "happiness", 8),
        ("got stuck in a jar temporarily", "energy", -5),
        ("found some delicious algae", "hunger", 10),
        ("jiggled through a keyhole", "happiness", 7),
        ("left a slime trail", "cleanliness", -8),
        ("merged with a raindrop", "happiness", 5),
        ("discovered a secret passage", "happiness", 12),
    ],
    "robot": [
        ("intercepted a wifi signal", "happiness", 8),
        ("found a charging port", "energy", 10),
        ("got a firmware update", "happiness", 10),
        ("crashed and rebooted", "energy", -8),
        ("scanned a QR code", "happiness", 5),
        ("collected some data", "happiness", 6),
        ("overheated slightly", "health", -5),
        ("optimized a process", "happiness", 12),
    ],
}

# ─── Event messages ───────────────────────────────────────────────────────────
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

# ─── Achievement definitions ─────────────────────────────────────────────────
ACHIEVEMENT_DEFS = {
    # Care milestones
    "first_feed": {"name": "First Bite", "desc": "Feed your pet for the first time", "icon": "🍎"},
    "first_play": {"name": "Playtime", "desc": "Play with your pet for the first time", "icon": "🎮"},
    "first_heal": {"name": "Nurse", "desc": "Heal your pet for the first time", "icon": "💊"},
    "first_sleep": {"name": "Sweet Dreams", "desc": "Put your pet to sleep for the first time", "icon": "💤"},
    "first_clean": {"name": "Sparkling", "desc": "Clean your pet for the first time", "icon": "🧼"},
    "first_pet_stroke": {"name": "Best Pal", "desc": "Pet your pet for the first time", "icon": "🤗"},
    "first_teach": {"name": "Teacher", "desc": "Teach your pet a trick for the first time", "icon": "🎓"},
    "first_explore": {"name": "Adventurer", "desc": "Let your pet explore for the first time", "icon": "🧭"},
    # Interaction milestones
    "interactions_10": {"name": "Devoted", "desc": "Reach 10 lifetime interactions", "icon": "❤️"},
    "interactions_50": {"name": "Super Devoted", "desc": "Reach 50 lifetime interactions", "icon": "💜"},
    "interactions_100": {"name": "Best Friend", "desc": "Reach 100 lifetime interactions", "icon": "🏆"},
    "interactions_500": {"name": "Soulmate", "desc": "Reach 500 lifetime interactions", "icon": "✨"},
    # Stat milestones
    "all_stats_high": {"name": "Perfect Care", "desc": "All stats above 80 at once", "icon": "👑"},
    "survived_sickness": {"name": "Survivor", "desc": "Recover from being sick", "icon": "🛡️"},
    # Trick milestones
    "tricks_3": {"name": "Trickster", "desc": "Teach your pet 3 different tricks", "icon": "🎪"},
    "tricks_5": {"name": "Grand Performer", "desc": "Teach your pet all 5 tricks", "icon": "🎭"},
    # Exploration milestones
    "explores_5": {"name": "Wanderer", "desc": "Explore 5 times", "icon": "🗺️"},
    "explores_20": {"name": "Explorer", "desc": "Explore 20 times", "icon": "🌍"},
    # Stage milestones
    "reached_adult": {"name": "All Grown Up", "desc": "Pet reaches the adult stage", "icon": "🌟"},
    "reached_elder": {"name": "Wisdom", "desc": "Pet reaches the elder stage", "icon": "📖"},
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
    # New fields — tricks, achievements, event log
    tricks_learned: list = field(default_factory=list)   # list of trick names
    achievements: list = field(default_factory=list)      # list of achievement IDs
    explore_count: int = 0
    event_log: list = field(default_factory=list)         # timestamped event history
    was_sick: bool = False                                 # track if pet has been sick (for survivor achievement)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_care_time:
            self.last_care_time = datetime.now().isoformat()
        if not self.personality:
            self.personality = random.choice(PERSONALITIES.get(self.species, ["friendly"]))

    def get_overall_mood(self) -> str:
        """Calculate mood based on average stats and health status."""
        if not self.is_alive:
            return "dead"
        avg = (self.hunger + self.happiness + self.health + self.energy + self.cleanliness) / 5
        if self.health < DYING_THRESHOLD:
            return "dying"
        if self.health < SICK_THRESHOLD:
            return "sick"
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
        """Return ASCII art lines for the pet's current stage."""
        if not self.is_alive:
            return PET_ART.get(self.species, PET_ART["cat"]).get("dead", ["  (x_x)  "])
        return PET_ART.get(self.species, PET_ART["cat"]).get(self.stage, ["  (o_o)  "])

    def apply_decay(self, minutes_elapsed: float):
        """Apply time-based decay to stats.

        Health decays faster when other stats are critically low.
        """
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
        # Track sickness for survivor achievement
        if self.health < SICK_THRESHOLD:
            self.was_sick = True
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

        if new_stage != old_stage:
            template = random.choice(EVENT_MESSAGES["level_up"])
            messages.append(template.format(name=self.name, stage=new_stage))
            # Log stage transition
            self._log_event(f"Grew from {old_stage} to {new_stage}")
        self.stage = new_stage
        return messages

    def clamp_stats(self):
        """Keep all stats within bounds [0, MAX_STAT]."""
        for attr in ['hunger', 'happiness', 'health', 'energy', 'cleanliness']:
            setattr(self, attr, max(0, min(MAX_STAT, getattr(self, attr))))

    def _log_event(self, event: str):
        """Add a timestamped event to the pet's diary."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.event_log.append(f"[{timestamp}] {event}")
        # Keep diary manageable — last 100 entries
        if len(self.event_log) > 100:
            self.event_log = self.event_log[-100:]


# ─── Achievement system ──────────────────────────────────────────────────────
def check_achievements(pet: Pet) -> list:
    """Check and award new achievements. Returns list of newly earned achievement IDs."""
    new_achievements = []

    def _award(aid: str):
        if aid not in pet.achievements and aid in ACHIEVEMENT_DEFS:
            pet.achievements.append(aid)
            new_achievements.append(aid)

    # Interaction milestones
    if pet.lifetime_interactions >= 1:
        # These are checked after specific actions, but we also check cumulative
        pass
    if pet.lifetime_interactions >= 10:
        _award("interactions_10")
    if pet.lifetime_interactions >= 50:
        _award("interactions_50")
    if pet.lifetime_interactions >= 100:
        _award("interactions_100")
    if pet.lifetime_interactions >= 500:
        _award("interactions_500")

    # All stats high
    if (pet.is_alive and
        pet.hunger >= 80 and pet.happiness >= 80 and
        pet.health >= 80 and pet.energy >= 80 and
        pet.cleanliness >= 80):
        _award("all_stats_high")

    # Survivor — was sick but now recovered
    if pet.was_sick and pet.health >= SICK_THRESHOLD and pet.is_alive:
        _award("survived_sickness")

    # Trick milestones
    if len(pet.tricks_learned) >= 3:
        _award("tricks_3")
    if len(pet.tricks_learned) >= 5:
        _award("tricks_5")

    # Explore milestones
    if pet.explore_count >= 5:
        _award("explores_5")
    if pet.explore_count >= 20:
        _award("explores_20")

    # Stage milestones
    if pet.stage == "adult":
        _award("reached_adult")
    if pet.stage == "elder":
        _award("reached_elder")

    return new_achievements


def format_achievement(aid: str) -> str:
    """Format an achievement for display."""
    a = ACHIEVEMENT_DEFS.get(aid, {"name": aid, "icon": "?", "desc": ""})
    return f"{a['icon']} {a['name']} — {a['desc']}"


# ─── Save/Load ────────────────────────────────────────────────────────────────
def save_pet(pet: Pet):
    """Save pet state to JSON with automatic backup."""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    data = asdict(pet)
    # Create backup of existing save before overwriting
    if SAVE_FILE.exists():
        try:
            shutil.copy2(SAVE_FILE, BACKUP_FILE)
        except (OSError, IOError):
            pass  # Non-critical: backup failure shouldn't block save
    with open(SAVE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_pet() -> Pet | None:
    """Load pet from save file. Falls back to backup if primary is corrupted."""
    for filepath in [SAVE_FILE, BACKUP_FILE]:
        if not filepath.exists():
            continue
        try:
            with open(filepath) as f:
                data = json.load(f)
            # Handle migration: ensure new fields have defaults for old saves
            defaults = {
                "tricks_learned": [],
                "achievements": [],
                "explore_count": 0,
                "event_log": [],
                "was_sick": False,
            }
            for key, default in defaults.items():
                data.setdefault(key, default)
            # Filter out unknown fields for forward compatibility
            valid_fields = {f.name for f in Pet.__dataclass_fields__.values()}
            data = {k: v for k, v in data.items() if k in valid_fields}
            return Pet(**data)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue  # Try backup
        except Exception:
            continue
    return None


def delete_pet():
    """Delete pet save file and backup."""
    for filepath in [SAVE_FILE, BACKUP_FILE]:
        if filepath.exists():
            try:
                filepath.unlink()
            except OSError:
                pass


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
    """Render a visual stat bar with optional color coding."""
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
    """Render the full pet display including stats, art, and messages."""
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

    # Info line
    trick_count = len(pet.tricks_learned)
    ach_count = len(pet.achievements)
    info_parts = [
        f"🕐 Age: {pet.age_hours:.1f}h",
        f"📊 Stage: {pet.stage.capitalize()}",
        f"🎭 {pet.personality.capitalize()}",
    ]
    if trick_count:
        info_parts.append(f"🎪 Tricks: {trick_count}")
    if ach_count:
        info_parts.append(f"🏅 Achievements: {ach_count}")
    lines.append(f"\n  {'  |  '.join(info_parts)}")
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
        lines.append(f"\n  {DIM}Commands: feed | play | heal | sleep | clean | pet | teach | explore | status | achievements | diary | help | quit{RESET}\n")

    return "\n".join(lines)


# ─── Actions ──────────────────────────────────────────────────────────────────
def do_feed(pet: Pet) -> str:
    """Feed the pet: increases hunger and energy, slightly decreases cleanliness."""
    responses = RESPONSES["feed"].get(pet.species, ["*eats happily*"])
    msg = random.choice(responses)
    pet.hunger = min(MAX_STAT, pet.hunger + 25)
    pet.energy = min(MAX_STAT, pet.energy + 5)
    pet.cleanliness = max(0, pet.cleanliness - 3)  # eating makes a mess
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    # Achievement check
    if "first_feed" not in pet.achievements:
        pet.achievements.append("first_feed")
    pet._log_event("Was fed")
    return msg


def do_play(pet: Pet) -> str:
    """Play with the pet: increases happiness, costs energy and hunger."""
    if pet.energy < 15:
        return f"😴 {pet.name} is too tired to play! Try letting them sleep."
    responses = RESPONSES["play"].get(pet.species, ["*plays happily*"])
    msg = random.choice(responses)
    pet.happiness = min(MAX_STAT, pet.happiness + 20)
    pet.energy = max(0, pet.energy - 15)
    pet.hunger = max(0, pet.hunger - 10)
    pet.cleanliness = max(0, pet.cleanliness - 5)
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    if "first_play" not in pet.achievements:
        pet.achievements.append("first_play")
    pet._log_event("Played")
    return msg


def do_heal(pet: Pet) -> str:
    """Heal the pet: increases health, slightly decreases happiness (yucky medicine)."""
    responses = RESPONSES["heal"].get(pet.species, ["*feels better*"])
    msg = random.choice(responses)
    pet.health = min(MAX_STAT, pet.health + 30)
    pet.happiness = max(0, pet.happiness - 5)  # medicine is yucky
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    # Check recovery
    if pet.was_sick and pet.health >= SICK_THRESHOLD:
        msg += " " + random.choice(EVENT_MESSAGES["recovered"])
    if "first_heal" not in pet.achievements:
        pet.achievements.append("first_heal")
    pet._log_event("Was healed")
    return msg


def do_sleep(pet: Pet) -> str:
    """Put the pet to sleep: restores energy, slightly decreases hunger."""
    responses = RESPONSES["sleep"].get(pet.species, ["*falls asleep*"])
    msg = random.choice(responses)
    pet.energy = min(MAX_STAT, pet.energy + 35)
    pet.hunger = max(0, pet.hunger - 8)
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    if "first_sleep" not in pet.achievements:
        pet.achievements.append("first_sleep")
    pet._log_event("Went to sleep")
    return msg


def do_clean(pet: Pet) -> str:
    """Clean the pet: increases cleanliness and slightly happiness."""
    responses = RESPONSES["clean"].get(pet.species, ["*sparkles*"])
    msg = random.choice(responses)
    pet.cleanliness = min(MAX_STAT, pet.cleanliness + 30)
    pet.happiness = min(MAX_STAT, pet.happiness + 5)
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    if "first_clean" not in pet.achievements:
        pet.achievements.append("first_clean")
    pet._log_event("Was cleaned")
    return msg


def do_pet(pet: Pet) -> str:
    """Pet the pet: increases happiness."""
    responses = RESPONSES["pet"].get(pet.species, ["*happy*"])
    msg = random.choice(responses)
    pet.happiness = min(MAX_STAT, pet.happiness + 10)
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    if "first_pet_stroke" not in pet.achievements:
        pet.achievements.append("first_pet_stroke")
    pet._log_event("Was petted")
    return msg


def do_teach(pet: Pet) -> str:
    """Teach the pet a new trick. Costs energy, gains happiness.

    If the pet already knows all available tricks, just performs a random one.
    Returns a descriptive message.
    """
    available_tricks = TRICKS.get(pet.species, [])

    if not available_tricks:
        return "❓ There are no tricks for this species yet..."

    # Find tricks not yet learned
    unlearned = [t for t in available_tricks if t[0] not in pet.tricks_learned]

    if not unlearned:
        # All tricks learned — perform a random one
        trick_name, trick_anim = random.choice(available_tricks)
        pet._log_event(f"Performed trick: {trick_name}")
        return f"🎭 {pet.name} already knows all tricks! {trick_anim}"

    # Check energy — teaching costs energy
    if pet.energy < 10:
        return f"😴 {pet.name} is too tired to learn! Try letting them sleep first."

    # Learn a random unlearned trick
    trick_name, trick_anim = random.choice(unlearned)
    pet.tricks_learned.append(trick_name)
    pet.energy = max(0, pet.energy - 10)
    pet.happiness = min(MAX_STAT, pet.happiness + 8)
    pet.total_interactions += 1
    pet.lifetime_interactions += 1

    if "first_teach" not in pet.achievements:
        pet.achievements.append("first_teach")

    pet._log_event(f"Learned trick: {trick_name}")
    return f"🎓 {pet.name} learned **{trick_name}**! {trick_anim}"


def do_explore(pet: Pet) -> str:
    """Let the pet explore and have a random adventure.

    Costs energy. May find items, trigger events, or encounter mishaps.
    Returns a descriptive message.
    """
    if pet.energy < 10:
        return f"😴 {pet.name} is too tired to explore! Try letting them sleep first."

    events = EXPLORE_EVENTS.get(pet.species, [])
    if not events:
        return "❓ There's nothing to explore here..."

    event_desc, stat_name, amount = random.choice(events)
    # Apply the stat change (health can't drop below 1 from exploring — that would be unfair)
    current = getattr(pet, stat_name)
    new_val = max(0, min(MAX_STAT, current + amount))
    if stat_name == "health" and new_val < 1:
        new_val = 1
    setattr(pet, stat_name, new_val)

    pet.energy = max(0, pet.energy - 8)
    pet.total_interactions += 1
    pet.lifetime_interactions += 1
    pet.explore_count += 1

    if "first_explore" not in pet.achievements:
        pet.achievements.append("first_explore")

    # Format message
    direction = "+" if amount > 0 else ""
    icon = "🔍" if amount > 0 else "⚡"
    msg = f"{icon} {pet.name} {event_desc}! ({stat_name.capitalize()} {direction}{amount})"
    pet._log_event(f"Explored and {event_desc}")
    return msg


def do_ignore(pet: Pet) -> str:
    """Handle the pet being ignored: decreases happiness."""
    responses = RESPONSES["ignore"].get(pet.species, ["*sad*"])
    msg = random.choice(responses)
    pet.happiness = max(0, pet.happiness - 5)
    return msg


# ─── New Pet Creation ─────────────────────────────────────────────────────────
def create_new_pet(name: str = "", species: str = "") -> Pet:
    """Interactive pet creation flow. Prompts for name and species if not provided."""
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
    pet._log_event(f"{name} the {species} was born!")
    save_pet(pet)
    return pet


# ─── CLI argument handling ────────────────────────────────────────────────────
def print_version():
    """Print version information."""
    print(f"CLI Tamagotchi v{VERSION}")
    print("A terminal virtual pet with ASCII art, decaying needs, and interactive commands.")


def print_help():
    """Print CLI help and exit."""
    print(f"""
{BOLD}{CYAN}🥚 CLI Tamagotchi v{VERSION}{RESET}

{BOLD}USAGE{RESET}
  python3 tamagotchi.py           Start or continue your virtual pet
  python3 tamagotchi.py --help    Show this help message
  python3 tamagotchi.py --version Show version

{BOLD}CARE COMMANDS{RESET}
  {YELLOW}feed{RESET}     Feed your pet (🍖 +25 hunger, ⚡ +5 energy, ✨ -3)
  {MAGENTA}play{RESET}     Play with your pet (💖 +20 happiness, ⚡ -15, 🍖 -10)
  {RED}heal{RESET}      Give medicine (❤️ +30 health, 💖 -5)
  {CYAN}sleep{RESET}     Put pet to bed (⚡ +35 energy, 🍖 -8)
  {GREEN}clean{RESET}     Clean your pet (✨ +30 cleanliness, 💖 +5)
  {YELLOW}pet{RESET}      Pet your pet (💖 +10 happiness)

{BOLD}LEARNING & ADVENTURE{RESET}
  {BLUE}teach{RESET}     Teach your pet a new trick (🎓 costs ⚡10 energy)
  {BLUE}explore{RESET}   Send pet on an adventure (🔍 costs ⚡8 energy)

{BOLD}INFORMATION{RESET}
  {BLUE}status{RESET}        Show detailed pet info
  {BLUE}achievements{RESET}  Show earned achievements
  {BLUE}diary{RESET}         Show pet's event diary
  {DIM}help{RESET}           Show in-game command reference
  {DIM}release{RESET}       Release your pet and start fresh
  {DIM}quit{RESET}           Save and exit

{BOLD}SPECIES{RESET}
  Cat, Dog, Dragon, Slime, Robot — each with unique art, personality, and dialogue

{BOLD}SAVE FILE{RESET}
  ~/.tamagotchi/pet.json  (with automatic backup at pet.json.bak)
""")


def parse_args(args: list) -> dict:
    """Parse command-line arguments. Returns dict with parsed options."""
    result = {"show_help": False, "show_version": False, "error": ""}
    for arg in args[1:]:  # Skip script name
        if arg in ("--help", "-h"):
            result["show_help"] = True
        elif arg in ("--version", "-v", "-V"):
            result["show_version"] = True
        else:
            result["error"] = f"Unknown option: {arg}"
    return result


# ─── Main Loop ────────────────────────────────────────────────────────────────
def main():
    # Parse CLI arguments
    cli_args = parse_args(sys.argv)
    if cli_args["error"]:
        print(f"Error: {cli_args['error']}")
        print("Try '--help' for usage information.")
        sys.exit(1)
    if cli_args["show_help"]:
        print_help()
        sys.exit(0)
    if cli_args["show_version"]:
        print_version()
        sys.exit(0)

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
                pet._log_event("Passed away from neglect")
    except (ValueError, TypeError) as e:
        # Corrupted timestamp — reset to now
        pet.messages.append(f"⚠️ Save time was corrupted. Resetting timers.")
    except Exception:
        pass

    pet.clamp_stats()
    pet.last_care_time = datetime.now().isoformat()
    save_pet(pet)

    # Interactive loop
    while True:
        # Check and award achievements before rendering
        new_ach = check_achievements(pet)
        if new_ach:
            for aid in new_ach:
                pet.messages.append(f"🏅 Achievement unlocked: {format_achievement(aid)}")
                pet._log_event(f"Achievement: {ACHIEVEMENT_DEFS[aid]['name']}")

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
            print(f"  {YELLOW}feed{RESET}    — Feed your pet (🍖 +25 hunger)")
            print(f"  {MAGENTA}play{RESET}    — Play with your pet (💖 +20 happiness, ⚡ -15 energy)")
            print(f"  {RED}heal{RESET}     — Give medicine (❤️ +30 health)")
            print(f"  {CYAN}sleep{RESET}    — Put pet to bed (⚡ +35 energy)")
            print(f"  {GREEN}clean{RESET}    — Clean your pet (✨ +30 cleanliness)")
            print(f"  {YELLOW}pet{RESET}     — Pet your pet (💖 +10 happiness)")
            print(f"  {BLUE}teach{RESET}    — Teach a trick (🎓 costs ⚡10 energy)")
            print(f"  {BLUE}explore{RESET}  — Go on an adventure (🔍 costs ⚡8 energy)")
            print(f"  {BLUE}status{RESET}   — Show detailed pet info")
            print(f"  {BLUE}achievements{RESET} — Show earned achievements")
            print(f"  {BLUE}diary{RESET}   — Show pet's event diary")
            print(f"  {DIM}release{RESET}  — Release your pet (start fresh)")
            print(f"  {DIM}quit{RESET}     — Save and exit")
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

        elif cmd == "teach" and pet.is_alive:
            result_msg = do_teach(pet)

        elif cmd == "explore" and pet.is_alive:
            result_msg = do_explore(pet)

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
            if pet.tricks_learned:
                print(f"  Tricks:       {', '.join(pet.tricks_learned)}")
            if pet.achievements:
                print(f"  Achievements: {len(pet.achievements)}")
            print(f"  Explores:     {pet.explore_count}")
            print(f"  Created:      {pet.created_at[:19]}")
            print(f"{'═' * 40}")
            input("\n  Press Enter to continue...")
            continue

        elif cmd == "achievements":
            print(f"\n{BOLD}{CYAN}  🏅 Achievements for {pet.name}{RESET}\n")
            if not pet.achievements:
                print(f"  {DIM}No achievements yet. Keep caring for your pet!{RESET}")
            else:
                for aid in pet.achievements:
                    print(f"  {format_achievement(aid)}")
            # Show locked achievements
            locked = [aid for aid in ACHIEVEMENT_DEFS if aid not in pet.achievements]
            if locked:
                print(f"\n  {DIM}Locked ({len(locked)} remaining):{RESET}")
                for aid in locked[:5]:
                    a = ACHIEVEMENT_DEFS[aid]
                    print(f"  {DIM}🔒 {a['name']} — {a['desc']}{RESET}")
                if len(locked) > 5:
                    print(f"  {DIM}... and {len(locked) - 5} more{RESET}")
            input("\n  Press Enter to continue...")
            continue

        elif cmd == "diary":
            print(f"\n{BOLD}{CYAN}  📔 {pet.name}'s Diary{RESET}\n")
            if not pet.event_log:
                print(f"  {DIM}No events recorded yet.{RESET}")
            else:
                # Show last 15 entries
                for entry in pet.event_log[-15:]:
                    print(f"  {DIM}{entry}{RESET}")
                if len(pet.event_log) > 15:
                    print(f"\n  {DIM}... and {len(pet.event_log) - 15} older entries{RESET}")
            input("\n  Press Enter to continue...")
            continue

        elif cmd == "release":
            if pet.is_alive:
                confirm = input(f"  {RED}Are you sure you want to release {pet.name}? (yes/no): {RESET}").strip().lower()
                if confirm == "yes":
                    print(f"  {DIM}Goodbye, {pet.name}... 🌈{RESET}")
                    pet._log_event("Was released")
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
            if not pet.is_alive and cmd not in ("release", "help", "quit", "achievements", "diary", "status"):
                result_msg = f"💀 {pet.name} can't do that... they've passed away."
            else:
                result_msg = f"❓ Unknown command: {cmd}. Type 'help' for options."
            # Don't apply decay for invalid/unrecognized commands
            pet.messages.append(result_msg)
            continue

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

        # Check achievements after every action
        new_ach = check_achievements(pet)
        if new_ach:
            for aid in new_ach:
                pet.messages.append(f"🏅 Achievement unlocked: {format_achievement(aid)}")

        pet.clamp_stats()
        pet.last_care_time = datetime.now().isoformat()
        save_pet(pet)


if __name__ == "__main__":
    main()