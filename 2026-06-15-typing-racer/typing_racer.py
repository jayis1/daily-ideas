#!/usr/bin/env python3
"""
Terminal Typing Racer — a fast-paced typing game in your terminal.
Type the falling words before they reach the bottom of the screen!
"""

import curses
import random
import time
import locale
import sys

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
        curses.init_pair(3, curses.COLOR_GREEN, -1)      # completed word
        curses.init_pair(4, curses.COLOR_RED, -1)        # danger zone
        curses.init_pair(5, curses.COLOR_YELLOW, -1)     # score / UI accent
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)    # particles
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_RED)    # game over bg
        curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_GREEN)  # level up flash

        # State
        self.words: list[FallingWord] = []
        self.particles: list[Particle] = []
        self.score = 0
        self.level = 1
        self.combo = 0
        self.max_combo = 0
        self.words_completed = 0
        self.lives = 5
        self.game_over = False
        self.paused = False
        self.current_target: FallingWord | None = None
        self.miss_buffer = ""
        self.total_chars_typed = 0
        self.correct_chars = 0
        self.elapsed_time = 0.0
        self.spawn_timer = 0.0
        self.difficulty_level = "easy"  # current word difficulty tier
        self.level_flash = 0.0
        self.speed_multiplier = 1.0
        self.spawn_interval = 2.5

        # Track what difficulty tiers are unlocked
        self.unlocked = {"easy"}
        self.difficulty_thresholds = {
            "medium": 3,
            "hard": 10,
            "expert": 20,
        }

    # ── Spawning ────────────────────────────────────────────────────────

    def pick_word(self) -> tuple[str, str]:
        """Pick a random word from available difficulty tiers."""
        tiers = list(self.unlocked)
        # Weight toward harder tiers as level increases
        weights = []
        for tier in tiers:
            if tier == "easy":
                weights.append(max(1, 5 - self.level))
            elif tier == "medium":
                weights.append(min(self.level, 5))
            elif tier == "hard":
                weights.append(min(self.level - 1, 4) if self.level > 2 else 0)
            elif tier == "expert":
                weights.append(min(self.level - 3, 3) if self.level > 4 else 0)
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
        self.words.append(FallingWord(word, x, speed, tier))

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

    # ── Game Logic ──────────────────────────────────────────────────────

    def update(self, dt: float):
        if self.game_over or self.paused:
            return

        self.elapsed_time += dt

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

        # Move words down
        for word in self.words:
            word.advance(dt)
            # Check if word hit bottom
            if word.y >= self.height - 3 and word.alive:
                word.alive = False
                self.lives -= 1
                self.combo = 0
                if self.lives <= 0:
                    self.game_over = True

        # Move particles
        for p in self.particles:
            p.advance(dt)

        # Clean up
        self.words = [w for w in self.words if w.alive or w.flash_timer > 0]
        self.particles = [p for p in self.particles if p.alive]

        # Level flash decay
        if self.level_flash > 0:
            self.level_flash -= dt

        # Level up every 8 completed words
        new_level = self.words_completed // 8 + 1
        if new_level > self.level:
            self.level = new_level
            self.level_flash = 1.0
            self.speed_multiplier = 1.0 + (self.level - 1) * 0.1
            self.spawn_interval = max(0.8, 2.5 - (self.level - 1) * 0.15)

    def handle_input(self, ch: int):
        if self.game_over:
            if ch == ord("r") or ch == ord("R"):
                self.reset()
            return

        if ch == ord("\x1b") or ch == 27:  # ESC
            self.paused = not self.paused
            return

        if self.paused:
            return

        if ch < 0 or ch > 255:
            return

        char = chr(ch)

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

        self.spawn_particles(word)

    def reset(self):
        self.words.clear()
        self.particles.clear()
        self.score = 0
        self.level = 1
        self.combo = 0
        self.max_combo = 0
        self.words_completed = 0
        self.lives = 5
        self.game_over = False
        self.paused = False
        self.current_target = None
        self.total_chars_typed = 0
        self.correct_chars = 0
        self.elapsed_time = 0.0
        self.spawn_timer = 0.0
        self.speed_multiplier = 1.0
        self.spawn_interval = 2.5
        self.unlocked = {"easy"}
        self.level_flash = 0.0

    # ── Rendering ────────────────────────────────────────────────────────

    def draw(self):
        self.stdscr.clear()
        h, w = self.height, self.width

        if self.paused:
            self._draw_pause()
            return

        if self.game_over:
            self._draw_game_over()
            return

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
            # Draw typed portion in cyan
            for i in range(word.typed_count):
                try:
                    self.stdscr.addch(y, int(x + i), word.word[i], curses.color_pair(1) | curses.A_BOLD)
                except curses.error:
                    pass
            # Draw remaining portion
            for i in range(word.typed_count, len(word.word)):
                # Red if in danger zone
                if y >= danger_y - 2:
                    color = curses.color_pair(4) | curses.A_BOLD
                else:
                    color = curses.color_pair(2)
                try:
                    self.stdscr.addch(y, int(x + i), word.word[i], color)
                except curses.error:
                    pass

            # Underline the target word
            if word is self.current_target:
                for i in range(len(word.word)):
                    try:
                        # We can't easily underline in all terminals, so use bold highlight
                        pass
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

        # ── Current target display ───────────────────────────────────────
        if self.current_target and self.current_target.alive:
            target_text = f"► {self.current_target.typed}{self.current_target.remaining}"
            tx = max(0, w // 2 - len(target_text) // 2)
            ty = h - 1
            try:
                self.stdscr.addstr(ty, tx, target_text[:w - 1], curses.color_pair(1) | curses.A_BOLD)
            except curses.error:
                pass

        self.stdscr.refresh()

    def _draw_hud(self):
        h, w = self.height, self.width
        # Top bar
        lives_str = "♥ " * self.lives + "♡ " * (5 - self.lives)
        combo_str = f"Combo: {self.combo}x" if self.combo > 0 else ""
        unlocked_str = " ".join(f"[{t}]" for t in sorted(self.unlocked))
        score_str = f"Score: {self.score}"

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

        hud_parts = [lives_str, score_str, combo_str, wpm_str, acc_str, unlocked_str]
        hud_text = "  │  ".join(p for p in hud_parts if p)

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
            "",
            "  [R] Restart    [Q] Quit",
        ]

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
        text = "║ PAUSED — Press ESC to resume ║"
        x = max(0, w // 2 - len(text) // 2)
        y = h // 2
        try:
            self.stdscr.addstr(y, x, text, curses.color_pair(5) | curses.A_BOLD)
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


def main(stdscr):
    locale.setlocale(locale.LC_ALL, "")
    game = TypingRacer(stdscr)
    game.run()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass