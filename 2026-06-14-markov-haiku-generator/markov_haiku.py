#!/usr/bin/env python3
"""
Markov Chain Haiku Generator
Reads text, builds Markov chains, and generates 5-7-5 syllable haikus.
"""

import random
import re
import sys
import os
from collections import defaultdict


# ─── Syllable counting ───────────────────────────────────────────────────────

# Common exceptions: words where simple vowel counting fails
SYLLABLE_EXCEPTIONS = {
    # Silent e
    "the": 1, "be": 1, "he": 1, "me": 1, "she": 1, "we": 1, "ye": 1,
    "are": 1, "were": 1, "gone": 1, "some": 1, "come": 1, "one": 1,
    "done": 1, "none": 1, "have": 1, "give": 1, "live": 1, "love": 1,
    "move": 1, "prove": 1, "lose": 1, "whose": 1, "choose": 1,
    # Two-syllable
    "fire": 1, "poem": 2, "poet": 2, "quiet": 2, "science": 2,
    "every": 3, "different": 3, "beautiful": 4,
    # Common words that trip up vowel counting
    "nature": 2, "water": 2, "winter": 2, "summer": 2, "autumn": 2,
    "spring": 1, "morning": 2, "evening": 3, "flower": 2,
    "butterfly": 4, "mountain": 2, "river": 2, "forest": 2,
    "garden": 2, "shadow": 2, "whisper": 2, "silence": 2,
    "temple": 2, "mirror": 2, "ancient": 2, "golden": 2,
    "silver": 2, "crimson": 2, "violet": 3, "amber": 2,
    "twilight": 2, "moonlight": 2, "starlight": 2, "sunlight": 2,
    "daylight": 2, "firelight": 2, "candle": 2, "cherry": 2,
    "blossom": 2, "petals": 2, "falling": 2, "drifting": 2,
    "floating": 2, "singing": 2, "dancing": 2, "dreaming": 2,
    "waking": 2, "sleeping": 2, "weeping": 2, "laughing": 2,
    "breathing": 2, "wander": 2, "linger": 2, "flutter": 2,
    "shimmer": 2, "glimmer": 2, "glowing": 2, "fading": 2,
    "rising": 2, "falling": 2, "melting": 2, "freezing": 2,
    "gentle": 2, "solitary": 4, "tranquil": 2, "serene": 2,
    "peaceful": 2, "endless": 2, "eternal": 3, "infinite": 3,
    "moment": 2, "breathe": 1, "rhythm": 2, "harmony": 3,
    "through": 1, "though": 1, "thought": 1, "enough": 2,
    "against": 2, "between": 2, "within": 2, "without": 2,
    "upon": 2, "among": 2, "around": 2, "beneath": 2,
    "beyond": 2, "before": 2, "behind": 2,
    "fireflies": 3, "dragonfly": 3, "hummingbird": 3,
    "raindrop": 2, "snowfall": 2, "rainfall": 2, "windfall": 2,
    "nightfall": 2, "daybreak": 2, "daybreak": 2,
    "haiku": 2, "haikus": 2,
}


def count_syllables(word):
    """Count syllables in a word using heuristic rules + exception table."""
    word = word.lower().strip()
    word = re.sub(r"[^a-z]", "", word)

    if not word:
        return 0

    if word in SYLLABLE_EXCEPTIONS:
        return SYLLABLE_EXCEPTIONS[word]

    # Handle -le at end (e.g., "little" = 2, "sparkle" = 2)
    # But "able" = 2 not 3

    # Count vowel groups
    vowels = "aeiouy"
    count = 0
    prev_was_vowel = False

    for i, ch in enumerate(word):
        is_vowel = ch in vowels
        if is_vowel and not prev_was_vowel:
            count += 1
        prev_was_vowel = is_vowel

    # Adjustments
    # Silent 'e' at end (but not -le patterns like "little")
    if word.endswith("e") and not word.endswith("le") and len(word) > 2:
        if word[-2] not in vowels:
            count = max(1, count - 1)

    # -y at end adds a syllable usually (already counted by vowel group)

    # Words ending in -ed: if preceded by t or d, it's a syllable
    if word.endswith("ed") and len(word) > 3:
        if word[-3] in ("t", "d"):
            pass  # keep the count
        else:
            count = max(1, count - 1)

    # -es at end: if preceded by s, z, ch, sh, x, ge — adds syllable
    # Already handled by vowel group counting

    # ia, io, ea etc. — usually 2 syllables, already handled

    return max(1, count)


def syllable_count_phrase(phrase):
    """Count total syllables in a space-separated phrase."""
    words = phrase.split()
    return sum(count_syllables(w) for w in words)


# ─── Markov Chain ────────────────────────────────────────────────────────────

class MarkovChain:
    """Builds a Markov chain from text and generates sequences."""

    def __init__(self, order=2):
        self.order = order
        self.chain = defaultdict(list)  # (prefix) -> [next_words]
        self.starters = []  # sentence/line starters
        self.all_words = set()

    def train(self, text):
        """Train the chain on input text."""
        # Split into sentences/lines
        sentences = re.split(r'[.!?\n]+', text)
        for sentence in sentences:
            words = self._tokenize(sentence)
            if len(words) < self.order + 1:
                continue

            self.starters.append(tuple(words[:self.order]))

            for i in range(len(words) - self.order):
                prefix = tuple(words[i:i + self.order])
                next_word = words[i + self.order]
                self.chain[prefix].append(next_word)
                self.all_words.add(next_word)
                for w in prefix:
                    self.all_words.add(w)

        # Also build single-word chain for fallback
        if not hasattr(self, '_single_chain'):
            self._single_chain = defaultdict(list)
        for sentence in sentences:
            words = self._tokenize(sentence)
            if len(words) < 2:
                continue
            for i in range(len(words) - 1):
                self._single_chain[words[i]].append(words[i + 1])
                self.all_words.add(words[i])
                self.all_words.add(words[i + 1])

    def _tokenize(self, text):
        """Tokenize text into words, preserving contractions."""
        words = re.findall(r"[a-zA-Z']+", text.lower())
        return [w for w in words if w and not all(c == "'" for c in w)]

    def generate(self, max_words=20, start=None):
        """Generate a sequence of words."""
        if start is None:
            if self.starters:
                start = random.choice(self.starters)
            else:
                # fallback
                word_list = list(self.all_words)
                if not word_list:
                    return []
                start = tuple(random.sample(word_list, min(self.order, len(word_list))))

        result = list(start)
        prefix = tuple(start)

        for _ in range(max_words - len(start)):
            if prefix in self.chain and self.chain[prefix]:
                next_word = random.choice(self.chain[prefix])
            else:
                # Try single-word fallback
                if prefix[-1] in self._single_chain and self._single_chain[prefix[-1]]:
                    next_word = random.choice(self._single_chain[prefix[-1]])
                else:
                    break
            result.append(next_word)
            prefix = tuple(result[-self.order:])

        return result

    def generate_with_syllable_target(self, target_syllables, max_attempts=200):
        """Generate a phrase that matches the target syllable count."""
        for _ in range(max_attempts):
            words = self.generate(max_words=target_syllables + 5)
            # Try all prefixes
            for end in range(1, len(words) + 1):
                phrase_words = words[:end]
                phrase = " ".join(phrase_words)
                sc = syllable_count_phrase(phrase)
                if sc == target_syllables:
                    return phrase
                if sc > target_syllables:
                    break

        # Fallback: construct word by word
        return self._construct_by_syllables(target_syllables)

    def _construct_by_syllables(self, target):
        """Build a phrase word-by-word to hit exact syllable count."""
        words_so_far = []
        syllables_so_far = 0

        # Pick a starting word
        word_list = sorted(self.all_words)
        if not word_list:
            return None

        # Try random words until we find a starting point
        attempts = 0
        while attempts < 50:
            start_word = random.choice(word_list)
            sc = count_syllables(start_word)
            if sc <= target:
                words_so_far.append(start_word)
                syllables_so_far = sc
                break
            attempts += 1

        if not words_so_far:
            return None

        # Build from there
        for _ in range(target * 2):
            remaining = target - syllables_so_far
            if remaining == 0:
                break
            if remaining < 0:
                # backtrack
                removed = words_so_far.pop()
                syllables_so_far -= count_syllables(removed)
                continue

            # Find candidate next words
            last = words_so_far[-1]
            candidates = self._single_chain.get(last, [])
            if not candidates:
                candidates = word_list

            # Filter by syllable fit
            valid = [w for w in candidates if count_syllables(w) <= remaining]
            if not valid:
                # Try any word that fits
                valid = [w for w in word_list if count_syllables(w) <= remaining]
            if not valid:
                # Backtrack
                removed = words_so_far.pop()
                syllables_so_far -= count_syllables(removed)
                continue

            next_word = random.choice(valid)
            words_so_far.append(next_word)
            syllables_so_far += count_syllables(next_word)

        if syllables_so_far == target:
            return " ".join(words_so_far)
        return None


# ─── Haiku Generator ─────────────────────────────────────────────────────────

# Default corpus with poetic/nature language for when no input is provided
DEFAULT_CORPUS = """
Cherry blossoms fall softly on the quiet mountain temple
Ancient trees whisper secrets to the wandering wind
Moonlight paints the garden in silver shadows
A single raindrop falls into the still pond
Autumn leaves drift down the slow river
Winter snow covers the sleeping forest
Spring flowers open their petals to the morning sun
Summer cicadas sing their endless song
The heron stands still in the shallow water
Fog rises from the deep valley at dawn
Stars shine above the silent monastery
Pine needles carpet the forgotten path
A butterfly rests on the wildflower
The old stone bridge crosses the narrow stream
Crimson maple leaves reflect in the lake
Geese fly south through the cooling evening sky
Frost crystals form on the window pane
The bamboo sways gently in the breeze
Night falls over the peaceful mountain village
Dewdrops glisten on the morning grass
The wooden boat drifts across the misty harbor
Cherry petals floating down the gentle stream
The ancient bell rings across the silent valley
White clouds drift above the endless green meadow
Fireflies dance along the dark forest edge
The moon rises slowly over the eastern hills
Snow melts quietly beneath the warming sun
A cricket chirps in the temple garden
The koi swims slowly through the lily pond
Golden sunlight filters through the cedar trees
The path winds upward through the ancient forest
Rain taps softly on the paper umbrella
Bamboo shadows stretch across the stone courtyard
The temple bell echoes through the autumn evening
Wild geese call from far across the twilight sky
Morning mist clings to the mountain ridge
The old poet writes by candlelight
A single pine stands on the rocky cliff
Petals scatter when the wind blows through the orchard
The frozen river shines beneath the winter moon
Soft rain falls on the mossy temple steps
Cherry branches heavy with pink blossoms
The dragonfly hovers above the water lily
Stone lanterns glow along the garden path
Distant thunder rolls across the summer hills
The fishing boat returns to the quiet harbor
Maple shadows dance upon the temple wall
A white crane takes flight from the shallow marsh
The evening breeze carries the scent of jasmine
Dawn breaks over the sleeping fishing village
Autumn moonlight shines deep in the mountain water
A caterpillar crawls along the fallen leaf
The old well reflects the stars above
Spring rain nourishes the waiting earth
Sunset paints the clouds in amber and gold
The nightingale sings from the highest branch
Silver fish leap from the moonlit lake
The garden gate opens to the inner courtyard
Bonsai trees stand patient in the morning light
A gentle stream flows beneath the wooden bridge
The monk walks slowly along the stone path
Cranes fly home across the purple evening sky
A leaf falls gently into the still water
The temple roof gleams in the autumn sunlight
Winter branches reach toward the gray sky
Spring returns again to the mountain village
The wooden flute plays a melody of longing
Stars reflected in the mountain lake
The cicada shell clings to the cherry trunk
Rain washes the dust from the temple steps
The heron waits patiently by the river bend
Moon shadows fall across the garden stones
A wild deer drinks from the forest stream
The ancient pine survives another winter
Golden chrysanthemums bloom in the temple garden
The wind carries the sound of distant bells
Snowflakes melt on the warm stone steps
The owl watches from the cedar tree
Fishing boats rest on the quiet shore
Bamboo groves rustle in the evening wind
The mountain path disappears into the clouds
A frog jumps into the old pond with a splash
The autumn moon is bright above the ancient pagoda
Cherry blossoms cover the quiet road
The river carries fallen leaves to the sea
A white cloud passes over the mountain peak
The temple garden sleeps beneath the winter snow
Morning dew sparkles on the spider web
The old turtle suns itself on the river rock
Crimson leaves fall softly through the morning air
The distant mountain floats in the evening haze
A thousand stars reflected in the dark lake
The bamboo flute echoes through the forest
Gentle waves lap against the mossy shore
The garden pond reflects the willow tree
Spring flowers push through the melting snow
The crane stands tall in the morning mist
An ancient path leads through the bamboo forest
The setting sun paints the sky in fire
A single star appears in the twilight
The temple incense drifts through the evening air
Petals fall like snow upon the garden path
The mountain stream sings its ancient song
"""


class HaikuGenerator:
    """Generate haikus using Markov chains and syllable counting."""

    SEASONS = {
        "spring": ["🌸", "🌱", "🌷"],
        "summer": ["☀️", "🌿", "🦋"],
        "autumn": ["🍂", "🍁", "🌾"],
        "winter": ["❄️", "🏔️", "🌑"],
    }

    SEASON_KEYWORDS = {
        "spring": ["spring", "blossom", "cherry", "flower", "petal", "bud",
                    "butterfly", "dawn", "morning", "rain", "fresh", "green",
                    "seed", "grow", "bloom", "nest", "bird", "warming"],
        "summer": ["summer", "sun", "heat", "cicada", "firefly", "warm",
                   "bright", "day", "golden", "sunset", "humid", "pond",
                   "cricket", "jasmine", "lily", "crane"],
        "autumn": ["autumn", "fall", "leaf", "maple", "crimson", "harvest",
                   "moon", "cool", "mist", "fog", "wind", "amber", "chrysanthemum",
                   "evening", "twilight"],
        "winter": ["winter", "snow", "frost", "ice", "cold", "frozen", "bare",
                   "night", "star", "dark", "silent", "sleep", "stone", "gray",
                   "white", "moonlight"],
    }

    def __init__(self, order=2):
        self.chain = MarkovChain(order=order)

    def train(self, text):
        """Train on provided text."""
        self.chain.train(text)

    def train_default(self):
        """Train on the built-in nature corpus."""
        self.chain.train(DEFAULT_CORPUS)

    def detect_season(self, haiku_text):
        """Detect the season of a haiku based on keywords."""
        text_lower = haiku_text.lower()
        scores = {s: 0 for s in self.SEASONS}
        for season, keywords in self.SEASON_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    scores[season] += 1
        best = max(scores, key=lambda k: scores[k])
        if scores[best] == 0:
            import datetime
            month = datetime.datetime.now().month
            if month in (3, 4, 5):
                best = "spring"
            elif month in (6, 7, 8):
                best = "summer"
            elif month in (9, 10, 11):
                best = "autumn"
            else:
                best = "winter"
        return best

    def generate_haiku(self, max_attempts=500):
        """Generate a single 5-7-5 haiku."""
        for _ in range(max_attempts):
            line1 = self.chain.generate_with_syllable_target(5)
            line2 = self.chain.generate_with_syllable_target(7)
            line3 = self.chain.generate_with_syllable_target(5)

            if line1 and line2 and line3:
                # Capitalize first letter of each line
                line1 = line1[0].upper() + line1[1:]
                line2 = line2[0].upper() + line2[1:]
                line3 = line3[0].upper() + line3[1:]
                return [line1, line2, line3]

        return None

    def format_haiku(self, lines, style="pretty"):
        """Format a haiku for display."""
        if not lines:
            return "  (could not generate haiku)"

        text = " ".join(lines)
        season = self.detect_season(text)
        emoji = random.choice(self.SEASONS[season])

        if style == "minimal":
            return "\n".join(lines)

        if style == "pretty":
            border = "─" * 40
            result = []
            result.append(f"  {emoji}  ┌{border}┐")
            for line in lines:
                padded = line.center(36)
                result.append(f"     │ {padded} │")
            result.append(f"  {emoji}  └{border}┘")
            result.append(f"      ── {season.capitalize()} ──")
            return "\n".join(result)

        if style == "cjk":
            # Japanese-inspired vertical-ish layout
            result = []
            result.append("  ╔══════════════════════════╗")
            for line in lines:
                padded = f"  {line}"
                padded = padded.ljust(24)
                result.append(f"  ║{padded}║")
            result.append("  ╚══════════════════════════╝")
            result.append(f"     {emoji} {season.capitalize()}")
            return "\n".join(result)

        return "\n".join(lines)

    def generate_and_format(self, count=1, style="pretty"):
        """Generate multiple haikus and format them."""
        results = []
        for _ in range(count):
            lines = self.generate_haiku()
            formatted = self.format_haiku(lines, style=style)
            results.append(formatted)
        return results


# ─── Interactive mode ─────────────────────────────────────────────────────────

def interactive_mode(generator):
    """Run an interactive haiku generation session."""
    print("\n  🎋 Markov Chain Haiku Generator 🎋")
    print("  ─────────────────────────────────")
    print("  Commands:")
    print("    [Enter]  Generate a new haiku")
    print("    s        Cycle display style")
    print("    c        Enter custom text to train on")
    print("    d        Reset to default corpus")
    print("    q        Quit")
    print()

    styles = ["pretty", "cjk", "minimal"]
    style_idx = 0

    while True:
        try:
            cmd = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Farewell! 🌸")
            break

        if cmd == "q" or cmd == "quit":
            print("  Farewell! 🌸")
            break
        elif cmd == "s":
            style_idx = (style_idx + 1) % len(styles)
            print(f"  Style: {styles[style_idx]}")
            continue
        elif cmd == "c":
            print("  Enter your text (end with an empty line):")
            lines = []
            while True:
                try:
                    line = input("  | ")
                except (EOFError, KeyboardInterrupt):
                    break
                if not line.strip():
                    break
                lines.append(line)
            if lines:
                text = " ".join(lines)
                generator.chain = MarkovChain(order=2)
                generator.train(text)
                generator.train_default()
                print(f"  Trained on {len(lines)} lines of text (+ default corpus)")
            continue
        elif cmd == "d":
            generator.chain = MarkovChain(order=2)
            generator.train_default()
            print("  Reset to default corpus")
            continue
        else:
            # Generate haiku
            lines = generator.generate_haiku()
            print()
            print(generator.format_haiku(lines, style=styles[style_idx]))
            print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="🎋 Markov Chain Haiku Generator — generates 5-7-5 haikus from text"
    )
    parser.add_argument(
        "input_file", nargs="?",
        help="Text file to train on (uses built-in nature corpus if omitted)"
    )
    parser.add_argument(
        "-n", "--count", type=int, default=1,
        help="Number of haikus to generate (default: 1)"
    )
    parser.add_argument(
        "-s", "--style", choices=["pretty", "cjk", "minimal"], default="pretty",
        help="Output style (default: pretty)"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true",
        help="Interactive mode"
    )
    parser.add_argument(
        "-o", "--order", type=int, default=2,
        help="Markov chain order (default: 2)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    gen = HaikuGenerator(order=args.order)

    # Train
    if args.input_file:
        try:
            with open(args.input_file, "r") as f:
                text = f.read()
            gen.train(text)
            print(f"  Trained on {args.input_file}", file=sys.stderr)
        except FileNotFoundError:
            print(f"  Error: file '{args.input_file}' not found", file=sys.stderr)
            sys.exit(1)
    else:
        gen.train_default()

    if args.interactive:
        interactive_mode(gen)
    else:
        haikus = gen.generate_and_format(count=args.count, style=args.style)
        for h in haikus:
            print(h)
            print()


if __name__ == "__main__":
    main()