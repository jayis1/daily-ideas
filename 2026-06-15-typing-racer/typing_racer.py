#!/usr/bin/env python3
"""
Terminal Typing Racer — a fast-paced typing game in your terminal.
Type the falling words before they reach the bottom of the screen!

Usage:
    python3 typing_racer.py              # Start the game
    python3 typing_racer.py --help       # Show help
    python3 typing_racer.py --version    # Show version
    python3 typing_racer.py --scores     # Show high scores
    python3 typing_racer.py --reset      # Reset high scores
"""

import argparse
import curses
import json
import os
import random
import time
import locale
import sys

__version__ = "2.2.0"

# ── High score file ─────────────────────────────────────────────────────
HIGHSCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".typing_racer_scores.json")
MIN_TERM_WIDTH = 60
MIN_TERM_HEIGHT = 20

# ── Word pools ──────────────────────────────────────────────────────────

EASY_WORDS = [
    "cat", "dog", "sun", "run", "big", "red", "hot", "cup", "box", "top",
    "key", "map", "fly", "ice", "fox", "gem", "oak", "bay", "dew", "fog",
    "hat", "jar", "kit", "log", "mud", "net", "owl", "pen", "rug", "van",
]

MEDIUM_WORDS = [
    "flame", "storm", "dream", "river", "swift", "ghost", "blaze", "frost",
    "tiger", "ocean", "eagle", "light", "stone", "crown", "spark", "quest",
    "forge", "bloom", "crane", "drift", "ember", "globe", "haste", "ivory",
    "jewel", "knot", "lunar", "marsh", "noble", "orbit",
]

HARD_WORDS = [
    "phoenix", "cascade", "crystal", "whisper", "eclipse", "harmony",
    "phantom", "venture", "zenith", "alchemy", "paradox", "catalyst",
    "spectrum", "inferno", "labyrinth", "silhouette", "nocturnal",
    "celestial", "obsidian", "synthesis", "enigmatic", "mystique",
    "turbulent", "sovereign", "reverence", "fortitude", "eloquent",
    "luminous", "fragment", "saffron",
]

EXPERT_WORDS = [
    "magnificent", "constellation", "kaleidoscope", "serendipity",
    "chrysalis", "effervescent", "juxtapose", "labyrinthine",
    "quintessence", "surreptitious", "mellifluous", "phosphorescent",
    "cataclysmic", "idiosyncratic", "discombobulate", "sesquipedalian",
    "conflagration", "archipelago", "pulchritudinous", "verisimilitude",
    "extraterrestrial", "photosynthesis", "encyclopedia", "bureaucracy",
    "metamorphosis", "philanthropy", "reconnaissance", "chromatography",
    "electromagnetic", "unprecedented",
]

# ── Power-up types ──────────────────────────────────────────────────────

POWERUP_FREEZE = "freeze"    # Freezes all words for 3 seconds
POWERUP_BOMB = "bomb"        # Destroys all words on screen
POWERUP_HEART = "heart"      # Restores 1 life (max 5)


# ── Game Objects ────────────────────────────────────────────────────────

class FallingWord:
    """A word that falls down the screen."""

    def __init__(self, word: str, x: int, speed: float, difficulty: str):
        self.word = word
        self.x = x
        self.y = 0.0
        self.speed = speed  # rows per second
        self.typed_count = 0  # how many chars correctly typed so far
        self.alive = True
        self.difficulty = difficulty
        self.flash_timer = 0  # brief flash on destruction
        self.frozen = False   # frozen by freeze power-up

    @property
    def remaining(self) -> str:
        return self.word[self.typed_count:]

    @property
    def typed(self) -> str:
        return self.word[: self.typed_count]

    @property
    def fraction_typed(self) -> float:
        return self.typed_count / len(self.word) if self.word else 0.0

    def advance(self, dt: float):
        """Move the word downward; skip if frozen."""
        if not self.frozen:
            self.y += self.speed * dt
        if self.flash_timer > 0:
            self.flash_timer -= dt

    def try_char(self, ch: str) -> bool:
        """Attempt to type the next character. Returns True if correct."""
        if self.typed_count < len(self.word) and self.word[self.typed_count] == ch:
            self.typed_count += 1
            return True
        return False

    def is_complete(self) -> bool:
        return self.typed_count >= len(self.word)


class Particle:
    """Simple explosion particle for visual feedback."""

    def __init__(self, x: int, y: int, char: str, vx: float, vy: float, life: float, color: int):
        self.x = float(x)
        self.y = float(y)
        self.char = char
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color

    def advance(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 30 * dt  # gravity
        self.life -= dt

    @property
    def alive(self) -> bool:
        return self.life > 0


class PowerUp:
    """A collectible power-up that appears on screen."""

    SYMBOLS = {
        POWERUP_FREEZE: "❄",
        POWERUP_BOMB: "💥",
        POWERUP_HEART: "♥",
    }

    LABELS = {
        POWERUP_FREEZE: "FREEZE",
        POWERUP_BOMB: "BOMB",
        POWERUP_HEART: "+1 LIFE",
    }

    def __init__(self, ptype: str, x: int, y: int):
        self.ptype = ptype
        self.x = x
        self.y = y
        self.speed = 0.6  # slow fall
        self.alive = True
        self.age = 0.0
        self.max_age = 8.0  # disappears after 8 seconds

    @property
    def symbol(self) -> str:
        return self.SYMBOLS.get(self.ptype, "?")

    @property
    def label(self) -> str:
        return self.LABELS.get(self.ptype, "?")

    def advance(self, dt: float):
        self.y += self.speed * dt
        self.age += dt
        if self.age >= self.max_age:
            self.alive = False


# ── High Score Management ───────────────────────────────────────────────

class HighScoreManager:
    """Persist and retrieve high scores to a JSON file."""

    MAX_ENTRIES = 10

    def __init__(self, path: str = HIGHSCORE_FILE):
        self.path = path
        self.scores: list[dict] = []

    def load(self):
        """Load scores from disk. Silently handle corrupt/missing files."""
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Validate each entry is a dict with required keys
                    required = {"score", "wpm", "accuracy", "level", "words", "max_combo", "date"}
                    self.scores = [
                        e for e in data
                        if isinstance(e, dict) and required.issubset(e.keys())
                    ]
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self.scores = []

    def save(self):
        """Persist scores to disk."""
        try:
            with open(self.path, "w") as f:
                json.dump(self.scores, f, indent=2)
        except OSError:
            pass  # silently ignore write failures (e.g. read-only FS)

    def add(self, score: int, wpm: float, accuracy: float,
            level: int, words: int, max_combo: int) -> int:
        """Add a score entry. Returns the rank (1-based) or 0 if not in top."""
        entry = {
            "score": score,
            "wpm": round(wpm, 1),
            "accuracy": round(accuracy, 1),
            "level": level,
            "words": words,
            "max_combo": max_combo,
            "date": time.strftime("%Y-%m-%d %H:%M"),
        }
        self.scores.append(entry)
        self.scores.sort(key=lambda e: e["score"], reverse=True)
        self.scores = self.scores[: self.MAX_ENTRIES]
        self.save()
        # Find rank
        for i, s in enumerate(self.scores):
            if s is entry:
                return i + 1
        return 0

    def is_high_score(self, score: int) -> bool:
        """Check if a score would make the leaderboard."""
        if len(self.scores) < self.MAX_ENTRIES:
            return True
        return score > self.scores[-1]["score"]

    def clear(self):
        """Delete all scores."""
        self.scores = []
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass


# ── Main Game ──────────────────────────────────────────────────────────

class TypingRacer:
    DIFFICULTY_MAP = {
        "easy": (EASY_WORDS, 0.8, 2.5),
        "medium": (MEDIUM_WORDS, 1.1, 2.0),
        "hard": (HARD_WORDS, 1.5, 1.5),
        "expert": (EXPERT_WORDS, 2.0, 1.0),
    }

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        curses.curs_set(0)
        curses.noecho()
        stdscr.nodelay(True)
        stdscr.timeout(50)  # ms between getch

        # Colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)       # typed portion
        curses.init_pair(2, curses.COLOR_WHITE, -1)       # untyped portion
        curses.init_pair(3, curses.COLOR_GREEN, -1)       # completed word
        curses.init_pair(4, curses.COLOR_RED, -1)         # danger zone
        curses.init_pair(5, curses.COLOR_YELLOW, -1)       # score / UI accent
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)      # particles
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_RED)    # game over bg
        curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_GREEN)  # level up flash
        curses.init_pair(9, curses.COLOR_BLUE, -1)        # freeze tint
        curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_BLUE)  # power-up highlight
        curses.init_pair(11, curses.COLOR_GREEN, -1)      # power-up heart color
        curses.init_pair(12, curses.COLOR_CYAN, -1)       # combo milestone color

        # State
        self.words: list[FallingWord] = []
        self.particles: list[Particle] = []
        self.powerups: list[PowerUp] = []
        self.score = 0
        self.level = 1
        self.combo = 0
        self.max_combo = 0
        self.words_completed = 0
        self.lives = 5
        self.game_over = False
        self.paused = False
        self.started = False
        self.countdown = 3.0  # 3-second countdown before game starts
        self.current_target: FallingWord | None = None
        self.total_chars_typed = 0
        self.correct_chars = 0
        self.elapsed_time = 0.0
        self.spawn_timer = 0.0
        self.difficulty_level = "easy"  # current word difficulty tier
        self.level_flash = 0.0
        self.speed_multiplier = 1.0
        self.spawn_interval = 2.5

        # Freeze power-up state
        self.freeze_timer = 0.0
        self.freeze_active = False

        # Combo milestone notifications
        self.combo_milestone = 0.0  # timer for displaying milestone text
        self.combo_milestone_text = ""

        # Power-up spawn tracking
        self.powerup_spawn_counter = 0  # words completed since last power-up

        # Track what difficulty tiers are unlocked
        self.unlocked = {"easy"}
        self.difficulty_thresholds = {
            "medium": 3,
            "hard": 10,
            "expert": 20,
        }

        # High scores
        self.high_scores = HighScoreManager()
        self.high_scores.load()
        self.rank = 0  # rank of the last game

        # Resize handling
        self._last_size = (self.height, self.width)

    # ── Spawning ────────────────────────────────────────────────────────

    def pick_word(self) -> tuple[str, str]:
        """Pick a random word from available difficulty tiers."""
        tiers = list(self.unlocked)
        # Weight toward harder tiers as level increases
        # Unlocked tiers always get a minimum weight of 1 so they actually appear
        weights = []
        for tier in tiers:
            if tier == "easy":
                weights.append(max(1, 5 - self.level))
            elif tier == "medium":
                weights.append(max(1, min(self.level, 5)))
            elif tier == "hard":
                weights.append(max(1, min(self.level - 1, 4)) if self.level > 2 else 1)
            elif tier == "expert":
                weights.append(max(1, min(self.level - 3, 3)) if self.level > 4 else 1)
            else:
                weights.append(1)

        if sum(weights) == 0:
            weights = [1] * len(tiers)

        tier = random.choices(tiers, weights=weights, k=1)[0]
        word_list, _, _ = self.DIFFICULTY_MAP[tier]
        return random.choice(word_list), tier

    def spawn_word(self):
        word, tier = self.pick_word()
        _, base_speed, _ = self.DIFFICULTY_MAP[tier]
        speed = base_speed * self.speed_multiplier
        # Ensure word fits on screen
        max_x = max(0, self.width - len(word) - 2)
        x = random.randint(1, max(1, max_x))
        fw = FallingWord(word, x, speed, tier)
        if self.freeze_active:
            fw.frozen = True
        self.words.append(fw)

    def spawn_particles(self, word: FallingWord):
        """Explosion of characters when a word is completed."""
        chars = list(word.word)
        for i, ch in enumerate(chars):
            angle = (i / len(chars)) * 6.2832 + random.uniform(-0.3, 0.3)
            speed = random.uniform(15, 40)
            vx = speed * (1 if i % 2 == 0 else -1) + random.uniform(-5, 5)
            vy = random.uniform(-30, -10)
            color = random.choice([1, 3, 5, 6])
            life = random.uniform(0.4, 1.0)
            self.particles.append(
                Particle(int(word.x) + i, int(word.y), ch, vx, vy, life, color)
            )

    def maybe_spawn_powerup(self):
        """Possibly spawn a power-up after completing a word."""
        self.powerup_spawn_counter += 1
        # Spawn a power-up roughly every 6-12 words completed
        interval = random.randint(6, 12)
        if self.powerup_spawn_counter >= interval:
            self.powerup_spawn_counter = 0
            ptype = random.choice([POWERUP_FREEZE, POWERUP_BOMB, POWERUP_HEART])
            max_x = max(0, self.width - 10)
            x = random.randint(2, max(2, max_x))
            self.powerups.append(PowerUp(ptype, x, 2))

    # ── Game Logic ──────────────────────────────────────────────────────

    def update(self, dt: float):
        if self.game_over or self.paused or not self.started:
            return

        self.elapsed_time += dt

        # Freeze power-up
        if self.freeze_active:
            self.freeze_timer -= dt
            if self.freeze_timer <= 0:
                self.freeze_active = False
                self.freeze_timer = 0
                for w in self.words:
                    w.frozen = False

        # Spawn new words
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self.spawn_word()
            self.spawn_timer = self.spawn_interval + random.uniform(-0.5, 0.5)

        # Check difficulty unlocks
        for tier, threshold in self.difficulty_thresholds.items():
            if self.words_completed >= threshold and tier not in self.unlocked:
                self.unlocked.add(tier)
                self.level_flash = 1.0
                self.combo_milestone_text = f"UNLOCKED: {tier.upper()}"
                self.combo_milestone = 2.0

        # Move words down
        for word in self.words:
            word.advance(dt)
            # Check if word hit bottom
            if word.y >= self.height - 3 and word.alive:
                word.alive = False
                self.lives -= 1
                self.combo = 0
                if self.current_target is word:
                    self.current_target = None
                if self.lives <= 0:
                    self.game_over = True

        # Move power-ups down and check collection
        for pu in self.powerups:
            pu.advance(dt)
            # Collect power-up when it reaches the bottom area
            # (simulates the player catching it as it falls)
            if pu.y >= self.height - 5 and pu.alive:
                self.collect_powerup(pu)
            # Check if power-up fell past bottom — it disappears
            elif pu.y >= self.height - 3:
                pu.alive = False

        # Move particles
        for p in self.particles:
            p.advance(dt)

        # Clean up dead objects
        self.words = [w for w in self.words if w.alive or w.flash_timer > 0]
        self.powerups = [p for p in self.powerups if p.alive]
        self.particles = [p for p in self.particles if p.alive]

        # Level flash decay
        if self.level_flash > 0:
            self.level_flash -= dt

        # Combo milestone decay
        if self.combo_milestone > 0:
            self.combo_milestone -= dt

        # Level up every 8 completed words
        new_level = self.words_completed // 8 + 1
        if new_level > self.level:
            self.level = new_level
            self.level_flash = 1.0
            self.speed_multiplier = 1.0 + (self.level - 1) * 0.1
            self.spawn_interval = max(0.8, 2.5 - (self.level - 1) * 0.15)

    def handle_input(self, ch: int):
        # Countdown phase — skip countdown on any key EXCEPT ESC and Q
        if not self.started:
            if ch == ord("\x1b") or ch == 27:
                return  # ignore ESC during countdown
            if ch == ord("q") or ch == ord("Q"):
                return  # ignore Q during countdown
            self.started = True
            return

        if self.game_over:
            if ch == ord("r") or ch == ord("R"):
                self.reset()
            return

        if ch == ord("\x1b") or ch == 27:  # ESC
            self.paused = not self.paused
            return

        if self.paused:
            # Allow Q to quit from pause screen
            if ch == ord("q") or ch == ord("Q"):
                self.game_over = True  # trigger game over to save score
            return

        if ch < 0 or ch > 255:
            return

        char = chr(ch)

        # Ignore non-alpha keys (space, digits, punctuation, etc.)
        # These should not affect gameplay or reset the combo.
        if not char.isalpha():
            return

        # Convert to lowercase so Caps Lock doesn't break gameplay
        char = char.lower()

        self.total_chars_typed += 1

        # If we have an active target, try typing into it
        if self.current_target and self.current_target.alive:
            if self.current_target.try_char(char):
                self.correct_chars += 1
                if self.current_target.is_complete():
                    self._complete_word(self.current_target)
                    self.current_target = None
            else:
                # Wrong character — break combo
                self.combo = 0
                # Don't abandon target, let player try again
            return

        # No active target — find a word whose next char matches
        # Prioritize words closest to the bottom
        candidates = [
            w for w in self.words
            if w.alive and w.typed_count == 0 and w.word[0] == char
        ]
        if candidates:
            # Pick the one closest to the bottom (most urgent)
            candidates.sort(key=lambda w: w.y, reverse=True)
            target = candidates[0]
            target.try_char(char)
            self.correct_chars += 1
            self.current_target = target
            if target.is_complete():
                self._complete_word(target)
                self.current_target = None
        else:
            # No matching word — miss
            self.combo = 0

    def _complete_word(self, word: FallingWord):
        word.alive = False
        word.flash_timer = 0.5
        self.words_completed += 1
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)

        # Score: base + length bonus + combo multiplier
        length_bonus = len(word.word)
        combo_mult = 1.0 + (self.combo - 1) * 0.25
        difficulty_bonus = {"easy": 1, "medium": 2, "hard": 3, "expert": 5}.get(
            word.difficulty, 1
        )
        points = int((10 + length_bonus) * combo_mult * difficulty_bonus)
        self.score += points

        # Combo milestones — show a notification at 5, 10, 15, 20...
        if self.combo > 0 and self.combo % 5 == 0:
            self.combo_milestone_text = f"🔥 {self.combo}x COMBO!"
            self.combo_milestone = 2.0

        self.spawn_particles(word)
        self.maybe_spawn_powerup()

    def collect_powerup(self, pu: PowerUp):
        """Apply a power-up effect."""
        if pu.ptype == POWERUP_FREEZE:
            self.freeze_active = True
            self.freeze_timer = 3.0
            for w in self.words:
                w.frozen = True
        elif pu.ptype == POWERUP_BOMB:
            # Destroy all words on screen with particles
            # Note: bombed words do NOT count toward words_completed —
            # only manually typed words advance difficulty progression
            for w in self.words:
                if w.alive:
                    w.alive = False
                    self.score += 5  # small bonus for bombed words
                    self.spawn_particles(w)
            if self.current_target:
                self.current_target = None
            self.combo = 0  # bomb resets combo
        elif pu.ptype == POWERUP_HEART:
            self.lives = min(self.lives + 1, 5)

        pu.alive = False

    def reset(self):
        self.words.clear()
        self.particles.clear()
        self.powerups.clear()
        self.score = 0
        self.level = 1
        self.combo = 0
        self.max_combo = 0
        self.words_completed = 0
        self.lives = 5
        self.game_over = False
        self.paused = False
        self.started = False
        self.countdown = 3.0
        self.current_target = None
        self.total_chars_typed = 0
        self.correct_chars = 0
        self.elapsed_time = 0.0
        self.spawn_timer = 0.0
        self.speed_multiplier = 1.0
        self.spawn_interval = 2.5
        self.unlocked = {"easy"}
        self.level_flash = 0.0
        self.freeze_active = False
        self.freeze_timer = 0.0
        self.combo_milestone = 0.0
        self.combo_milestone_text = ""
        self.powerup_spawn_counter = 0
        self.rank = 0

    # ── Rendering ────────────────────────────────────────────────────────

    def draw(self):
        self.stdscr.clear()

        # Handle terminal resize
        new_h, new_w = self.stdscr.getmaxyx()
        if (new_h, new_w) != self._last_size:
            self.height, self.width = new_h, new_w
            self._last_size = (new_h, new_w)
            if self.height < MIN_TERM_HEIGHT or self.width < MIN_TERM_WIDTH:
                self._draw_too_small()
                self.stdscr.refresh()
                return

        h, w = self.height, self.width

        if not self.started and not self.game_over:
            self._draw_countdown()
            self.stdscr.refresh()
            return

        if self.paused:
            self._draw_pause()
            return

        if self.game_over:
            self._draw_game_over()
            return

        # ── Freeze overlay tint ────────────────────────────────────────
        if self.freeze_active:
            for y in range(2, h - 3):
                for x in range(0, w, 4):
                    try:
                        self.stdscr.addch(y, x, "·", curses.color_pair(9) | curses.A_DIM)
                    except curses.error:
                        pass

        # ── Danger zone line ────────────────────────────────────────────
        danger_y = h - 3
        for x in range(w):
            try:
                if x % 2 == 0:
                    self.stdscr.addch(danger_y, x, "─", curses.color_pair(4))
                else:
                    self.stdscr.addch(danger_y, x, "·", curses.color_pair(4) | curses.A_DIM)
            except curses.error:
                pass

        # ── Words ────────────────────────────────────────────────────────
        for word in self.words:
            if not word.alive and word.flash_timer <= 0:
                continue
            y = int(word.y)
            if y < 0 or y >= h:
                continue

            if word.flash_timer > 0 and not word.alive:
                # Completed flash
                x = word.x
                for i, ch in enumerate(word.word):
                    try:
                        self.stdscr.addch(y, int(x + i), ch, curses.color_pair(3) | curses.A_BOLD)
                    except curses.error:
                        pass
                continue

            x = word.x
            # Draw typed portion in cyan (or blue if frozen)
            for i in range(word.typed_count):
                color = curses.color_pair(9 if word.frozen else 1) | curses.A_BOLD
                try:
                    self.stdscr.addch(y, int(x + i), word.word[i], color)
                except curses.error:
                    pass
            # Draw remaining portion
            for i in range(word.typed_count, len(word.word)):
                # Red if in danger zone
                if y >= danger_y - 2:
                    color = curses.color_pair(4) | curses.A_BOLD
                elif word.frozen:
                    color = curses.color_pair(9)
                else:
                    color = curses.color_pair(2)
                try:
                    self.stdscr.addch(y, int(x + i), word.word[i], color)
                except curses.error:
                    pass

            # Target indicator: show a small arrow above the target word
            if word is self.current_target and word.alive and y > 2:
                mid = int(x + len(word.word) / 2)
                try:
                    self.stdscr.addch(y - 1, mid, "▼", curses.color_pair(5) | curses.A_BOLD)
                except curses.error:
                    pass

        # ── Power-ups ──────────────────────────────────────────────────
        for pu in self.powerups:
            y = int(pu.y)
            x = int(pu.x)
            if 0 <= y < h and 0 <= x < w:
                # Draw the symbol with a colored background
                # Use simple ASCII fallback since Unicode symbols may not render
                if pu.ptype == POWERUP_FREEZE:
                    sym = "F"
                    color = curses.color_pair(9) | curses.A_BOLD
                elif pu.ptype == POWERUP_BOMB:
                    sym = "B"
                    color = curses.color_pair(4) | curses.A_BOLD
                else:  # HEART
                    sym = "+"
                    color = curses.color_pair(3) | curses.A_BOLD

                try:
                    self.stdscr.addch(y, x, sym, color)
                except curses.error:
                    pass

                # Draw label below
                if y + 1 < h:
                    try:
                        self.stdscr.addstr(y + 1, max(0, x - 1), f"[{pu.label}]", color)
                    except curses.error:
                        pass

        # ── Particles ────────────────────────────────────────────────────
        for p in self.particles:
            x, y = int(p.x), int(p.y)
            if 0 <= x < w and 0 <= y < h:
                try:
                    alpha = max(0, min(1, p.life / p.max_life))
                    attr = curses.color_pair(p.color)
                    if alpha < 0.5:
                        attr |= curses.A_DIM
                    else:
                        attr |= curses.A_BOLD
                    self.stdscr.addch(y, x, p.char, attr)
                except curses.error:
                    pass

        # ── HUD ─────────────────────────────────────────────────────────
        self._draw_hud()

        # ── Level flash ─────────────────────────────────────────────────
        if self.level_flash > 0:
            flash_text = f"⚡ LEVEL {self.level} ⚡"
            fx = w // 2 - len(flash_text) // 2
            fy = h // 2 - 1
            try:
                self.stdscr.addstr(fy, fx, flash_text, curses.color_pair(5) | curses.A_BOLD)
            except curses.error:
                pass

        # ── Combo milestone ──────────────────────────────────────────────
        if self.combo_milestone > 0 and self.combo_milestone_text:
            cm_x = w // 2 - len(self.combo_milestone_text) // 2
            cm_y = h // 2 + 1
            try:
                self.stdscr.addstr(cm_y, cm_x, self.combo_milestone_text,
                                   curses.color_pair(12) | curses.A_BOLD)
            except curses.error:
                pass

        # ── Freeze indicator ────────────────────────────────────────────
        if self.freeze_active:
            freeze_text = f"❄ FREEZE {self.freeze_timer:.1f}s ❄"
            fx = w - len(freeze_text) - 2
            try:
                self.stdscr.addstr(2, fx, freeze_text, curses.color_pair(9) | curses.A_BOLD)
            except curses.error:
                pass

        # ── Available first-letters hint ────────────────────────────────
        self._draw_hints()

        # ── Current target display ───────────────────────────────────────
        if self.current_target and self.current_target.alive:
            target_text = f">> {self.current_target.typed}{self.current_target.remaining}"
            tx = max(0, w // 2 - len(target_text) // 2)
            ty = h - 1
            try:
                self.stdscr.addstr(ty, tx, target_text[:w - 1], curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

        self.stdscr.refresh()

    def _draw_hints(self):
        """Show available first letters for untargeted words."""
        h, w = self.height, self.width
        # Collect unique first letters of alive, untyped words
        first_letters = set()
        for word in self.words:
            if word.alive and word.typed_count == 0:
                first_letters.add(word.word[0].upper())

        if first_letters:
            hint_str = "Keys: " + " ".join(sorted(first_letters))
            hint_x = 2
            hint_y = h - 2
            try:
                self.stdscr.addstr(hint_y, hint_x, hint_str[:w - 2],
                                   curses.color_pair(5) | curses.A_DIM)
            except curses.error:
                pass

    def _draw_hud(self):
        h, w = self.height, self.width
        # Top bar
        lives_str = "♥ " * self.lives + "♡ " * (5 - self.lives)
        combo_str = f"Combo: {self.combo}x" if self.combo > 0 else ""
        unlocked_str = " ".join(f"[{t}]" for t in sorted(self.unlocked))
        score_str = f"Score: {self.score}"
        level_str = f"Lv{self.level}"

        # WPM
        if self.elapsed_time > 0:
            wpm = (self.correct_chars / 5) / (self.elapsed_time / 60)
        else:
            wpm = 0
        wpm_str = f"WPM: {wpm:.0f}"

        # Accuracy
        if self.total_chars_typed > 0:
            acc = (self.correct_chars / self.total_chars_typed) * 100
        else:
            acc = 100.0
        acc_str = f"Acc: {acc:.0f}%"

        hud_parts = [lives_str, score_str, combo_str, wpm_str, acc_str, level_str, unlocked_str]
        hud_text = "  |  ".join(p for p in hud_parts if p)

        # Truncate to screen width
        hud_text = hud_text[:w - 1]

        try:
            self.stdscr.addstr(0, 0, hud_text, curses.color_pair(5) | curses.A_BOLD)
        except curses.error:
            pass

        # Separator
        for x in range(w):
            try:
                self.stdscr.addch(1, x, "─", curses.A_DIM)
            except curses.error:
                pass

    def _draw_countdown(self):
        """Draw the countdown/start screen."""
        h, w = self.height, self.width

        title_lines = [
            "",
            "  ███████╗████████╗██╗   ██╗██████╗ ███████╗ █████╗ ██████╗ ███████╗",
            "  ██╔════╝╚══██╔══╝╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔════╝",
            "  ███████╗   ██║    ╚████╔╝ ██████╔╝█████╗  ███████║██████╔╝█████╗  ",
            "  ╚════██║   ██║     ╚██╔╝  ██╔══██╗██╔══╝  ██╔══██║██╔═══╝ ██╔══╝  ",
            "  ███████║   ██║      ██║   ██║  ██╗███████╗██║  ██║██║     ███████╗",
            "  ╚══════╝   ╚═╝      ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚══════╝",
            "",
            "  Type falling words before they hit the danger zone!",
            "",
        ]

        start_y = max(0, h // 2 - len(title_lines) // 2 - 4)
        for i, line in enumerate(title_lines):
            x = max(0, w // 2 - len(line) // 2)
            try:
                self.stdscr.addstr(start_y + i, x, line, curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

        # Countdown number
        count_num = max(1, int(self.countdown) + 1)
        if count_num > 3:
            count_num = 3
        count_str = f"[ {count_num} ]"
        cx = max(0, w // 2 - len(count_str) // 2)
        cy = start_y + len(title_lines) + 1
        try:
            self.stdscr.addstr(cy, cx, count_str, curses.color_pair(5) | curses.A_BOLD)
        except curses.error:
            pass

        hint_str = "Press any key to skip..."
        try:
            self.stdscr.addstr(cy + 2, max(0, w // 2 - len(hint_str) // 2), hint_str, curses.A_DIM)
        except curses.error:
            pass

        # Show high scores if any
        if self.high_scores.scores:
            hs_y = cy + 5
            try:
                self.stdscr.addstr(hs_y, max(0, w // 2 - 10), "── HIGH SCORES ──",
                                   curses.color_pair(5) | curses.A_BOLD)
                for i, entry in enumerate(self.high_scores.scores[:5]):
                    line = f"  {i+1}. {entry['score']:>6}  WPM:{entry['wpm']:>5.1f}  " \
                           f"Acc:{entry['accuracy']:>5.1f}%  Lv{entry['level']}"
                    try:
                        self.stdscr.addstr(hs_y + 1 + i, max(0, w // 2 - 20), line,
                                           curses.color_pair(2))
                    except curses.error:
                        pass
            except curses.error:
                pass

        self.stdscr.refresh()

    def _draw_game_over(self):
        h, w = self.height, self.width

        # Dim background effect
        for y in range(h):
            for x in range(w):
                try:
                    self.stdscr.addch(y, x, " ", curses.color_pair(7))
                except curses.error:
                    pass

        # Game over text
        lines = [
            "",
            "  ██████╗  █████╗ ███╗   ███╗███████╗     ██████╗  █████╗ ███╗   ███╗███████╗",
            "  ██╔════╝ ██╔══██╗████╗ ████║██╔════╝    ██╔════╝ ██╔══██╗████╗ ████║██╔════╝",
            "  ██║  ███╗███████║██╔████╔██║█████╗      ██║  ███╗███████║██╔████╔██║█████╗  ",
            "  ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝      ██║   ██║██╔══██║██║╚██╔╝██║██╔══╝  ",
            "  ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗    ╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗",
            "  ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝     ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝",
            "",
        ]

        start_y = max(0, h // 2 - len(lines) // 2 - 4)
        for i, line in enumerate(lines):
            x = max(0, w // 2 - len(line) // 2)
            try:
                self.stdscr.addstr(start_y + i, x, line, curses.color_pair(4) | curses.A_BOLD)
            except curses.error:
                pass

        # Stats
        if self.elapsed_time > 0:
            wpm = (self.correct_chars / 5) / (self.elapsed_time / 60)
        else:
            wpm = 0

        if self.total_chars_typed > 0:
            acc = (self.correct_chars / self.total_chars_typed) * 100
        else:
            acc = 100.0

        stats_lines = [
            f"Final Score:   {self.score}",
            f"Words Typed:   {self.words_completed}",
            f"Max Combo:     {self.max_combo}x",
            f"WPM:           {wpm:.1f}",
            f"Accuracy:       {acc:.1f}%",
            f"Level Reached:  {self.level}",
        ]

        # Show rank if applicable
        if self.rank > 0:
            stats_lines.append(f"High Score Rank: #{self.rank}")

        stats_lines.append("")
        stats_lines.append("  [R] Restart    [Q] Quit")

        stats_y = start_y + len(lines) + 1
        for i, line in enumerate(stats_lines):
            x = max(0, w // 2 - len(line) // 2)
            try:
                color = curses.color_pair(5) | curses.A_BOLD if i == 0 else curses.color_pair(2)
                self.stdscr.addstr(stats_y + i, x, line, color)
            except curses.error:
                pass

        self.stdscr.refresh()

    def _draw_pause(self):
        h, w = self.height, self.width

        # Show stats during pause
        if self.elapsed_time > 0:
            wpm = (self.correct_chars / 5) / (self.elapsed_time / 60)
        else:
            wpm = 0

        if self.total_chars_typed > 0:
            acc = (self.correct_chars / self.total_chars_typed) * 100
        else:
            acc = 100.0

        lines = [
            "╔══════════════════════════════╗",
            "║        PAUSED                ║",
            "║  Press ESC to resume        ║",
            "║  Press Q to quit             ║",
            "╠══════════════════════════════╣",
            f"║  Score:    {self.score:>6}            ║",
            f"║  WPM:      {wpm:>6.1f}            ║",
            f"║  Accuracy: {acc:>5.1f}%           ║",
            f"║  Level:    {self.level:>6}            ║",
            f"║  Combo:    {self.combo:>6}x           ║",
            f"║  Lives:    {'♥ ' * self.lives + '♡ ' * (5 - self.lives):>12}  ║",
            "╚══════════════════════════════╝",
        ]

        start_y = max(0, h // 2 - len(lines) // 2)
        for i, line in enumerate(lines):
            x = max(0, w // 2 - len(line) // 2)
            try:
                self.stdscr.addstr(start_y + i, x, line, curses.color_pair(5) | curses.A_BOLD)
            except curses.error:
                pass

        self.stdscr.refresh()

    def _draw_too_small(self):
        """Notify the user their terminal is too small."""
        self.stdscr.clear()
        msg = f"Terminal too small! Need >= {MIN_TERM_WIDTH}x{MIN_TERM_HEIGHT}"
        try:
            self.stdscr.addstr(0, 0, msg, curses.color_pair(4) | curses.A_BOLD)
        except curses.error:
            pass
        self.stdscr.refresh()

    # ── Main Loop ───────────────────────────────────────────────────────

    def run(self):
        last_time = time.time()

        while True:
            now = time.time()
            dt = min(now - last_time, 0.1)  # cap delta to avoid jumps
            last_time = now

            # Handle countdown
            if not self.started:
                self.countdown -= dt
                if self.countdown <= 0:
                    self.started = True
                    self.spawn_timer = 0.5  # first word appears quickly

            # Handle all pending input
            while True:
                try:
                    ch = self.stdscr.getch()
                except Exception:
                    ch = -1
                if ch == -1:
                    break
                if ch == ord("q") or ch == ord("Q"):
                    if self.game_over:
                        return
                self.handle_input(ch)

            self.update(dt)
            self.draw()


def show_scores():
    """Print high scores and exit."""
    hs = HighScoreManager()
    hs.load()
    if not hs.scores:
        print("No high scores yet. Play a game first!")
        return
    print("\n  ══════ TYPING RACER HIGH SCORES ══════\n")
    print(f"  {'Rank':>4}  {'Score':>8}  {'WPM':>6}  {'Acc':>7}  {'Level':>5}  {'Words':>5}  {'Combo':>5}  {'Date':<16}")
    print("  " + "─" * 70)
    for i, e in enumerate(hs.scores):
        print(f"  {i+1:>4}  {e['score']:>8}  {e['wpm']:>6.1f}  {e['accuracy']:>6.1f}%  {e['level']:>5}  "
              f"{e['words']:>5}  {e['max_combo']:>5}x  {e['date']:<16}")
    print()


def reset_scores():
    """Clear high scores and exit."""
    hs = HighScoreManager()
    hs.clear()
    print("High scores cleared.")


def main(stdscr):
    locale.setlocale(locale.LC_ALL, "")

    # Check terminal size
    h, w = stdscr.getmaxyx()
    if h < MIN_TERM_HEIGHT or w < MIN_TERM_WIDTH:
        stdscr.clear()
        msg = f"Terminal too small! Need >= {MIN_TERM_WIDTH}x{MIN_TERM_HEIGHT}, got {w}x{h}"
        try:
            stdscr.addstr(0, 0, msg, curses.color_pair(4) | curses.A_BOLD)
            stdscr.addstr(2, 0, "Press any key to exit...")
            stdscr.refresh()
            stdscr.getch()
        except curses.error:
            pass
        return

    game = TypingRacer(stdscr)

    # If we have previous high scores, show a brief title screen
    game.run()

    # On game over, save score
    if game.game_over and game.words_completed > 0:
        if game.elapsed_time > 0:
            wpm = (game.correct_chars / 5) / (game.elapsed_time / 60)
        else:
            wpm = 0
        if game.total_chars_typed > 0:
            acc = (game.correct_chars / game.total_chars_typed) * 100
        else:
            acc = 100.0

        game.rank = game.high_scores.add(
            game.score, wpm, acc, game.level, game.words_completed, game.max_combo
        )


def cli_main():
    """Entry point with argument parsing for --help, --version, --scores, --reset."""
    parser = argparse.ArgumentParser(
        description="Terminal Typing Racer — a fast-paced typing game in your terminal!",
        epilog="Type the falling words before they reach the danger zone!",
    )
    parser.add_argument("--version", action="version", version=f"typing-racer {__version__}")
    parser.add_argument("--scores", action="store_true", help="Show high scores and exit")
    parser.add_argument("--reset", action="store_true", help="Reset high scores and exit")

    args = parser.parse_args()

    if args.scores:
        show_scores()
        return

    if args.reset:
        reset_scores()
        return

    # Launch the game
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli_main()