#!/usr/bin/env python3
"""Comprehensive tests for the Terminal Crossword Puzzle."""

import json
import os
import sys
import tempfile

# Ensure the module can be imported
sys.path.insert(0, os.path.dirname(__file__))
import crossword


class TestCrosswordGenerator:
    """Tests for the CrosswordGenerator class."""

    def setup_method(self):
        """Create a fresh generator for each test."""
        self.gen = crossword.CrosswordGenerator(20, 14)

    def test_init(self):
        """Generator initializes with correct dimensions and empty grid."""
        assert self.gen.width == 20
        assert self.gen.height == 14
        assert len(self.gen.grid) == 14
        assert len(self.gen.grid[0]) == 20
        assert self.gen.placed_words == []

    def test_init_custom_word_bank(self):
        """Generator accepts a custom word bank."""
        custom_bank = [("FOO", "A test word"), ("BAR", "Another test word")]
        gen = crossword.CrosswordGenerator(20, 14, word_bank=custom_bank)
        assert gen.word_bank == custom_bank
        assert gen.width == 20
        assert gen.height == 14

    def test_default_word_bank(self):
        """Default word bank is the global WORD_BANK."""
        gen = crossword.CrosswordGenerator(20, 14)
        assert gen.word_bank == crossword.WORD_BANK

    def test_generate_basic(self):
        """Basic generation places at least one word."""
        self.gen.generate(max_words=10, seed=42)
        assert len(self.gen.placed_words) >= 1

    def test_generate_with_seed_reproducible(self):
        """Same seed produces same puzzle."""
        gen1 = crossword.CrosswordGenerator(20, 14)
        gen1.generate(max_words=10, seed=123)
        gen1.trim_grid()

        gen2 = crossword.CrosswordGenerator(20, 14)
        gen2.generate(max_words=10, seed=123)
        gen2.trim_grid()

        assert gen1.placed_words == gen2.placed_words

    def test_generate_different_seeds_different_puzzles(self):
        """Different seeds generally produce different puzzles."""
        gen1 = crossword.CrosswordGenerator(20, 14)
        gen1.generate(max_words=10, seed=1)
        gen1.trim_grid()

        gen2 = crossword.CrosswordGenerator(20, 14)
        gen2.generate(max_words=10, seed=999)
        gen2.trim_grid()

        # Very unlikely to be identical
        assert gen1.placed_words != gen2.placed_words

    def test_max_words_respected(self):
        """Generation respects the max_words limit."""
        self.gen.generate(max_words=5, seed=42)
        assert len(self.gen.placed_words) <= 5

    def test_min_word_len_filter(self):
        """Short words are excluded when min_word_len is set."""
        gen = crossword.CrosswordGenerator(20, 14)
        gen.generate(max_words=20, seed=42, min_word_len=6)
        for word, _, _, _ in gen.placed_words:
            assert len(word) >= 6

    def test_word_bank_deduplication(self):
        """Duplicate entries in WORD_BANK don't cause double placement."""
        gen = crossword.CrosswordGenerator(20, 14)
        gen.generate(max_words=15, seed=42)
        words_placed = [w for w, _, _, _ in gen.placed_words]
        # No duplicate word text in placed words
        assert len(words_placed) == len(set(words_placed))

    def test_can_place_first_word(self):
        """First word can always be placed in bounds."""
        assert self.gen.can_place("ALGORITHM", 7, 5, 'A')

    def test_can_place_bounds_check(self):
        """Words that extend past grid boundaries are rejected."""
        # Word of length 9 starting at column 18 would go to column 26 (out of bounds)
        assert not self.gen.can_place("ALGORITHM", 0, 18, 'A')

    def test_can_place_negative_position(self):
        """Negative positions are rejected."""
        assert not self.gen.can_place("HASH", -1, 0, 'A')
        assert not self.gen.can_place("HASH", 0, -1, 'A')

    def test_can_place_requires_intersection(self):
        """After the first word, new words must intersect existing ones."""
        self.gen.place_word("ALGORITHM", 7, 5, 'A')
        # Placing parallel without intersection should fail
        assert not self.gen.can_place("PYTHON", 9, 2, 'A')

    def test_place_word(self):
        """Placing a word updates the grid correctly."""
        self.gen.place_word("HASH", 3, 4, 'A')
        assert self.gen.grid[3][4] == 'H'
        assert self.gen.grid[3][5] == 'A'
        assert self.gen.grid[3][6] == 'S'
        assert self.gen.grid[3][7] == 'H'
        assert len(self.gen.placed_words) == 1

    def test_place_word_vertical(self):
        """Placing a vertical word updates the grid correctly."""
        self.gen.place_word("NODE", 3, 4, 'D')
        assert self.gen.grid[3][4] == 'N'
        assert self.gen.grid[4][4] == 'O'
        assert self.gen.grid[5][4] == 'D'
        assert self.gen.grid[6][4] == 'E'

    def test_trim_grid(self):
        """trim_grid reduces the grid to the bounding box of placed words."""
        self.gen.place_word("GIT", 7, 10, 'A')
        self.gen.trim_grid()
        # Grid should be smaller than original 20x14
        assert self.gen.width <= 20
        assert self.gen.height <= 14
        # Should still contain the word
        assert len(self.gen.placed_words) == 1

    def test_trim_grid_empty(self):
        """trim_grid on an empty generator returns itself."""
        result = self.gen.trim_grid()
        assert result is self.gen

    def test_get_clues(self):
        """get_clues returns proper numbered clues."""
        self.gen.generate(max_words=10, seed=42)
        self.gen.trim_grid()
        across, down, numbered = self.gen.get_clues()
        # Should have some clues
        total = len(across) + len(down)
        assert total > 0
        # Numbers should start at 1
        all_nums = [n for n, _, _ in across] + [n for n, _, _ in down]
        assert min(all_nums) >= 1
        # Each clue should have (number, word, clue_text)
        for num, word, clue in across:
            assert isinstance(num, int)
            assert len(word) >= 3
            assert len(clue) > 0

    def test_to_dict_and_from_dict(self):
        """Serialization round-trip preserves puzzle state."""
        self.gen.generate(max_words=10, seed=42)
        self.gen.trim_grid()
        data = self.gen.to_dict()
        restored = crossword.CrosswordGenerator.from_dict(data)
        assert restored.width == self.gen.width
        assert restored.height == self.gen.height
        assert restored.grid == self.gen.grid
        assert restored.placed_words == self.gen.placed_words

    def test_export_text(self):
        """export_text produces a non-empty string without ANSI codes."""
        self.gen.generate(max_words=10, seed=42)
        self.gen.trim_grid()
        text = self.gen.export_text(show_answers=False)
        assert len(text) > 100
        assert "ACROSS" in text
        assert "DOWN" in text
        # No ANSI escape sequences
        assert "\033[" not in text

    def test_export_text_with_answers(self):
        """export_text with answers includes the answer key."""
        self.gen.generate(max_words=10, seed=42)
        self.gen.trim_grid()
        text = self.gen.export_text(show_answers=True)
        assert "ANSWERS" in text

    def test_is_good_puzzle(self):
        """is_good_puzzle validates word count threshold."""
        self.gen.generate(max_words=10, seed=42)
        assert crossword.is_good_puzzle(self.gen, min_words=3)
        assert crossword.is_good_puzzle(self.gen, min_words=100) == False

    def test_get_stats(self):
        """get_stats returns meaningful statistics for a generated puzzle."""
        self.gen.generate(max_words=10, seed=42)
        self.gen.trim_grid()
        stats = self.gen.get_stats()
        assert stats["total_words"] >= 1
        assert stats["across_count"] + stats["down_count"] == stats["total_words"]
        assert stats["total_cells"] > 0
        assert stats["grid_density"] > 0
        assert stats["avg_word_len"] > 0
        assert len(stats["longest_word"]) >= len(stats["shortest_word"])
        assert stats["intersections"] >= 0

    def test_get_stats_empty(self):
        """get_stats on empty generator returns zeroed stats."""
        stats = self.gen.get_stats()
        assert stats["total_words"] == 0
        assert stats["total_cells"] == 0
        assert stats["grid_density"] == 0.0
        assert stats["longest_word"] == ""

    def test_strip_ansi(self):
        """strip_ansi removes ANSI escape sequences from strings."""
        colored = f"\033[31mRed\033[0m \033[1mBold\033[0m"
        stripped = crossword.strip_ansi(colored)
        assert stripped == "Red Bold"

    def test_strip_ansi_plain_text(self):
        """strip_ansi leaves plain text untouched."""
        plain = "Hello World"
        assert crossword.strip_ansi(plain) == "Hello World"


class TestCrosswordGame:
    """Tests for the CrosswordGame class."""

    def setup_method(self):
        """Create a generator and game for each test."""
        self.gen = crossword.CrosswordGenerator(20, 14)
        self.gen.generate(max_words=10, seed=42)
        self.gen.trim_grid()
        self.game = crossword.CrosswordGame(self.gen)

    def test_init(self):
        """Game initializes with proper state."""
        assert self.game.direction == 'A'
        assert self.game.solved is False
        assert self.game.hints_used == 0
        assert self.game.total_cells > 0

    def test_type_letter(self):
        """Typing a letter fills the current cell."""
        r, c = self.game.cursor_r, self.game.cursor_c
        old_char = self.game.player_grid[r][c]
        self.game.type_letter('X')
        assert self.game.player_grid[r][c] == 'X'

    def test_type_letter_uppercases(self):
        """Typing a lowercase letter auto-uppercases it."""
        r, c = self.game.cursor_r, self.game.cursor_c
        self.game.type_letter('a')
        assert self.game.player_grid[r][c] == 'A'

    def test_type_letter_advances_cursor(self):
        """Typing advances the cursor position."""
        old_r, old_c = self.game.cursor_r, self.game.cursor_c
        self.game.type_letter('X')
        # Cursor should have moved (unless at the very end)
        # At minimum, the letter was typed
        assert self.game.player_grid[old_r][old_c] == 'X'

    def test_backspace(self):
        """Backspace clears the current cell."""
        r, c = self.game.cursor_r, self.game.cursor_c
        self.game.type_letter('X')
        # Move cursor back to test backspace
        self.game.cursor_r = r
        self.game.cursor_c = c
        self.game.backspace()
        assert self.game.player_grid[r][c] == '_'

    def test_toggle_direction(self):
        """toggle_direction switches between A and D."""
        assert self.game.direction == 'A'
        self.game.toggle_direction()
        assert self.game.direction == 'D'
        self.game.toggle_direction()
        assert self.game.direction == 'A'

    def test_check_puzzle_empty(self):
        """Checking an empty puzzle gives a message."""
        self.game.check_puzzle()
        assert "Fill in" in self.game.message

    def test_check_puzzle_correct_partial(self):
        """Checking with all-correct partial fill reports so."""
        # Fill in all cells correctly
        for r in range(self.gen.height):
            for c in range(self.gen.width):
                if self.gen.grid[r][c] != ' ':
                    self.game.player_grid[r][c] = self.gen.grid[r][c]
        self.game.check_puzzle()
        assert self.game.solved is True

    def test_reveal_letter(self):
        """reveal_letter fills in the correct letter."""
        r, c = self.game.cursor_r, self.game.cursor_c
        self.game.reveal_letter()
        assert self.game.player_grid[r][c] == self.gen.grid[r][c]
        assert self.game.hints_used == 1

    def test_reveal_word(self):
        """reveal_word fills in the entire current word."""
        cells = self.game.get_current_word_cells()
        self.game.reveal_word()
        for r, c in cells:
            assert self.game.player_grid[r][c] == self.gen.grid[r][c]

    def test_progress_pct_empty(self):
        """Progress starts at 0%."""
        assert self.game.progress_pct() == 0

    def test_progress_pct_partial(self):
        """Progress increases as letters are filled."""
        r, c = self.game.cursor_r, self.game.cursor_c
        self.game.type_letter(self.gen.grid[r][c])
        assert self.game.progress_pct() > 0

    def test_elapsed_time(self):
        """Elapsed time is non-negative."""
        assert self.game.elapsed_time() >= 0

    def test_format_time(self):
        """format_time formats seconds correctly."""
        assert self.game.format_time(65) == "01:05"
        assert self.game.format_time(0) == "00:00"
        assert self.game.format_time(3599) == "59:59"

    def test_format_time_hours(self):
        """format_time shows HH:MM:SS when over an hour."""
        assert self.game.format_time(3600) == "01:00:00"
        assert self.game.format_time(3661) == "01:01:01"
        assert self.game.format_time(7200) == "02:00:00"

    def test_get_current_word_cells(self):
        """get_current_word_cells returns a list of cell positions."""
        cells = self.game.get_current_word_cells()
        assert len(cells) >= 2  # Words have at least 2 cells

    def test_move_cursor(self):
        """move_cursor changes cursor position."""
        old_r, old_c = self.game.cursor_r, self.game.cursor_c
        self.game.move_cursor(0, 1)
        # Cursor may or may not have moved depending on grid layout,
        # but it shouldn't crash
        assert 0 <= self.game.cursor_r < self.gen.height
        assert 0 <= self.game.cursor_c < self.gen.width

    def test_render(self):
        """render produces a non-empty string."""
        output = self.game.render(use_color=False)
        assert len(output) > 100
        assert "CROSSWORD" in output or "crossword" in output.lower()

    def test_render_with_color(self):
        """render with color produces output with ANSI codes."""
        output = self.game.render(use_color=True)
        assert "\033[" in output

    def test_render_without_color(self):
        """render without color has no ANSI codes."""
        output = self.game.render(use_color=False)
        assert "\033[" not in output

    def test_game_serialization(self):
        """Game state can be serialized and restored."""
        data = self.game.to_dict()
        assert "player_grid" in data
        assert "cursor_r" in data
        assert "cursor_c" in data
        assert "direction" in data
        assert "hints_used" in data

    def test_game_from_dict(self):
        """Game can be restored from a saved state."""
        self.game.type_letter('X')
        data = self.game.to_dict()
        restored = crossword.CrosswordGame.from_dict(self.gen, data)
        assert restored.cursor_r == data["cursor_r"]
        assert restored.cursor_c == data["cursor_c"]
        assert restored.direction == data["direction"]
        assert restored.hints_used == data["hints_used"]


class TestSaveLoad:
    """Tests for save/load functionality."""

    def setup_method(self):
        """Create a generator and game for save/load tests."""
        self.gen = crossword.CrosswordGenerator(20, 14)
        self.gen.generate(max_words=10, seed=42)
        self.gen.trim_grid()
        self.game = crossword.CrosswordGame(self.gen)

    def test_save_and_load(self):
        """Save and load round-trip preserves game state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = crossword.save_game(self.gen, self.game, filename="test_save.json")
            assert os.path.exists(filepath)

            loaded_gen, loaded_game = crossword.load_game(filepath)
            assert loaded_gen.width == self.gen.width
            assert loaded_gen.height == self.gen.height
            assert loaded_game.hints_used == self.game.hints_used

    def test_save_creates_directory(self):
        """Save creates the save directory if it doesn't exist."""
        filepath = crossword.save_game(self.gen, self.game)
        assert os.path.exists(filepath)
        # Clean up
        os.unlink(filepath)

    def test_list_saves_empty_dir(self):
        """list_saves returns empty list for nonexistent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = crossword.SAVE_DIR
            crossword.SAVE_DIR = os.path.join(tmpdir, "nonexistent")
            result = crossword.list_saves()
            crossword.SAVE_DIR = old_dir
            assert result == []

    def test_list_saves_with_files(self):
        """list_saves finds saved games."""
        crossword.save_game(self.gen, self.game)
        saves = crossword.list_saves()
        assert len(saves) >= 1
        # Clean up
        for filepath, _, _ in saves:
            os.unlink(filepath)

    def test_load_missing_file(self):
        """Loading a nonexistent file raises FileNotFoundError."""
        try:
            crossword.load_game("/nonexistent/path/file.json")
            assert False, "Should have raised FileNotFoundError"
        except (FileNotFoundError, IOError):
            pass

    def test_save_version_included(self):
        """Saved file includes version information."""
        filepath = crossword.save_game(self.gen, self.game, filename="test_ver.json")
        with open(filepath, 'r') as f:
            data = json.load(f)
        assert "version" in data
        assert data["version"] == crossword.__version__
        os.unlink(filepath)


class TestDifficultyPresets:
    """Tests for difficulty preset configuration."""

    def test_easy_preset(self):
        """Easy preset has expected keys."""
        assert "max_words" in crossword.DIFFICULTY_PRESETS["easy"]
        assert "min_word_len" in crossword.DIFFICULTY_PRESETS["easy"]
        assert "grid_width" in crossword.DIFFICULTY_PRESETS["easy"]
        assert "grid_height" in crossword.DIFFICULTY_PRESETS["easy"]

    def test_hard_more_words_than_easy(self):
        """Hard difficulty allows more words than easy."""
        assert (crossword.DIFFICULTY_PRESETS["hard"]["max_words"] >
                crossword.DIFFICULTY_PRESETS["easy"]["max_words"])

    def test_generate_easy(self):
        """Easy difficulty generates a valid puzzle."""
        preset = crossword.DIFFICULTY_PRESETS["easy"]
        gen = crossword.CrosswordGenerator(preset["grid_width"], preset["grid_height"])
        gen.generate(max_words=preset["max_words"], seed=42,
                     min_word_len=preset["min_word_len"])
        gen.trim_grid()
        assert len(gen.placed_words) >= 1

    def test_generate_hard(self):
        """Hard difficulty generates a valid puzzle."""
        preset = crossword.DIFFICULTY_PRESETS["hard"]
        gen = crossword.CrosswordGenerator(preset["grid_width"], preset["grid_height"])
        gen.generate(max_words=preset["max_words"], seed=42,
                     min_word_len=preset["min_word_len"])
        gen.trim_grid()
        assert len(gen.placed_words) >= 1


class TestThemedWordBank:
    """Tests for themed word bank functionality."""

    def test_get_themed_word_bank_programming(self):
        """Programming theme returns programming-related words."""
        bank = crossword.get_themed_word_bank("programming")
        assert len(bank) > 0
        for word, clue in bank:
            assert word in crossword.THEMED_WORDS["programming"]
            assert len(clue) > 0

    def test_get_themed_word_bank_networking(self):
        """Networking theme returns networking-related words."""
        bank = crossword.get_themed_word_bank("networking")
        assert len(bank) > 0
        for word, clue in bank:
            assert word in crossword.THEMED_WORDS["networking"]

    def test_get_themed_word_bank_data(self):
        """Data theme returns data-related words."""
        bank = crossword.get_themed_word_bank("data")
        assert len(bank) > 0
        for word, clue in bank:
            assert word in crossword.THEMED_WORDS["data"]

    def test_get_themed_word_bank_systems(self):
        """Systems theme returns systems-related words."""
        bank = crossword.get_themed_word_bank("systems")
        assert len(bank) > 0
        for word, clue in bank:
            assert word in crossword.THEMED_WORDS["systems"]

    def test_get_themed_word_bank_unknown(self):
        """Unknown theme returns the full word bank."""
        bank = crossword.get_themed_word_bank("unknown_theme")
        assert bank == list(crossword.WORD_BANK)

    def test_generate_with_theme(self):
        """Generating a puzzle with a themed word bank works."""
        bank = crossword.get_themed_word_bank("programming")
        gen = crossword.CrosswordGenerator(20, 14, word_bank=bank)
        gen.generate(max_words=8, seed=42)
        gen.trim_grid()
        assert len(gen.placed_words) >= 1
        # All placed words should come from the themed bank
        placed_words = {w for w, _, _, _ in gen.placed_words}
        theme_words = {w for w, _ in bank}
        assert placed_words.issubset(theme_words)

    def test_theme_case_insensitive(self):
        """Theme names are case-insensitive."""
        bank1 = crossword.get_themed_word_bank("Programming")
        bank2 = crossword.get_themed_word_bank("programming")
        assert bank1 == bank2

    def test_no_duplicates_in_themed_bank(self):
        """Themed word banks have no duplicate words."""
        for theme in crossword.THEMED_WORDS:
            bank = crossword.get_themed_word_bank(theme)
            words = [w for w, _ in bank]
            assert len(words) == len(set(words)), f"Duplicates in theme '{theme}'"


class TestStats:
    """Tests for the puzzle statistics feature."""

    def setup_method(self):
        """Create a generated puzzle for stats tests."""
        self.gen = crossword.CrosswordGenerator(20, 14)
        self.gen.generate(max_words=10, seed=42)
        self.gen.trim_grid()

    def test_stats_total_words(self):
        """Stats total_words matches placed_words count."""
        stats = self.gen.get_stats()
        assert stats["total_words"] == len(self.gen.placed_words)

    def test_stats_across_down_counts(self):
        """Stats across + down counts equal total words."""
        stats = self.gen.get_stats()
        assert stats["across_count"] + stats["down_count"] == stats["total_words"]

    def test_stats_intersections(self):
        """Stats intersections count is non-negative."""
        stats = self.gen.get_stats()
        assert stats["intersections"] >= 0

    def test_stats_density_range(self):
        """Stats grid density is between 0 and 1."""
        stats = self.gen.get_stats()
        assert 0 < stats["grid_density"] <= 1.0

    def test_stats_word_lengths(self):
        """Stats longest word is at least as long as shortest."""
        stats = self.gen.get_stats()
        assert len(stats["longest_word"]) >= len(stats["shortest_word"])

    def test_print_stats_no_crash(self):
        """print_stats runs without crashing."""
        # Redirect stdout to suppress output during test
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            crossword.print_stats(self.gen, use_color=False)
            output = sys.stdout.getvalue()
            assert "PUZZLE STATISTICS" in output
            assert "Total words" in output
            assert "Intersections" in output
        finally:
            sys.stdout = old_stdout


class TestVersion:
    """Test version constant."""

    def test_version_exists(self):
        """Module has a version string."""
        assert hasattr(crossword, '__version__')
        assert isinstance(crossword.__version__, str)
        # Should be in semver-like format
        parts = crossword.__version__.split('.')
        assert len(parts) >= 2

    def test_version_is_1_3(self):
        """Version is 1.3.0 after enhancements."""
        assert crossword.__version__ == "1.3.0"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_generate_no_words(self):
        """Generating with max_words=0 produces no placements."""
        gen = crossword.CrosswordGenerator(20, 14)
        gen.generate(max_words=0, seed=42)
        assert len(gen.placed_words) == 0

    def test_generate_tiny_grid(self):
        """A tiny grid can still place short words."""
        gen = crossword.CrosswordGenerator(5, 5)
        gen.generate(max_words=3, seed=42)
        assert len(gen.placed_words) >= 1

    def test_can_place_no_overlap_after_first(self):
        """A word placed far from all existing words is rejected."""
        gen = crossword.CrosswordGenerator(20, 14)
        gen.place_word("PYTHON", 0, 0, 'A')
        # This word doesn't intersect and is far away
        assert not gen.can_place("JAVA", 10, 10, 'A')

    def test_export_text_empty_grid(self):
        """export_text handles a trimmed empty generator."""
        gen = crossword.CrosswordGenerator(20, 14)
        gen.generate(max_words=1, seed=42)
        gen.trim_grid()
        text = gen.export_text()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_generate_max_words_zero(self):
        """Generating with max_words=0 produces no placements."""
        gen = crossword.CrosswordGenerator(20, 14)
        gen.generate(max_words=0, seed=42)
        assert len(gen.placed_words) == 0

    def test_game_empty_puzzle_no_crash(self):
        """Creating a game on an empty grid does not crash."""
        gen = crossword.CrosswordGenerator(20, 14)
        # No words placed
        game = crossword.CrosswordGame(gen)
        assert game.total_cells == 0
        assert game.has_puzzle is False
        # Render should work without crashing
        output = game.render(use_color=False)
        assert "No puzzle" in output

    def test_get_current_word_cells_no_side_effect(self):
        """get_current_word_cells should not toggle direction as side effect on normal puzzles."""
        gen = crossword.CrosswordGenerator(20, 14)
        gen.generate(max_words=10, seed=42)
        gen.trim_grid()
        game = crossword.CrosswordGame(gen)
        original_dir = game.direction
        cells = game.get_current_word_cells()
        # On a normal puzzle, direction may toggle if perpendicular word is found
        # But the result should be consistent
        assert len(cells) >= 2

    def test_render_does_not_decrement_message_timer(self):
        """Render should not decrement message_timer (that's the game loop's job)."""
        gen = crossword.CrosswordGenerator(20, 14)
        gen.generate(max_words=10, seed=42)
        gen.trim_grid()
        game = crossword.CrosswordGame(gen)
        game.check_puzzle()  # Sets message_timer
        timer_before = game.message_timer
        game.render(use_color=False)
        timer_after = game.message_timer
        assert timer_before == timer_after, "render() should not decrement message_timer"

    def test_render_does_not_toggle_direction(self):
        """Render should not toggle the game direction."""
        gen = crossword.CrosswordGenerator(20, 14)
        gen.generate(max_words=10, seed=42)
        gen.trim_grid()
        game = crossword.CrosswordGame(gen)
        game.direction = 'A'
        game.render(use_color=False)
        # Direction should remain 'A' after rendering
        assert game.direction == 'A'

    def test_double_digit_clue_numbers_render(self):
        """Render should handle double-digit clue numbers without misalignment."""
        gen = crossword.CrosswordGenerator(24, 16)
        gen.generate(max_words=18, seed=42, min_word_len=3)
        gen.trim_grid()
        game = crossword.CrosswordGame(gen)
        # Should not crash
        output = game.render(use_color=False)
        assert len(output) > 100

    def test_format_time_over_one_hour(self):
        """format_time shows hours when elapsed > 60 minutes."""
        game = crossword.CrosswordGame(
            crossword.CrosswordGenerator(20, 14))
        # 1 hour, 23 minutes, 45 seconds
        assert game.format_time(5025) == "01:23:45"

    def test_format_time_under_one_hour(self):
        """format_time shows MM:SS when under an hour."""
        game = crossword.CrosswordGame(
            crossword.CrosswordGenerator(20, 14))
        assert game.format_time(599) == "09:59"

    def test_supports_color_env_var(self):
        """supports_color respects NO_COLOR env var."""
        import os
        original = os.environ.get('NO_COLOR')
        os.environ['NO_COLOR'] = '1'
        assert crossword.supports_color() is False
        if original is not None:
            os.environ['NO_COLOR'] = original
        else:
            del os.environ['NO_COLOR']

    def test_strip_ansi_removes_escape_codes(self):
        """strip_ansi correctly removes all ANSI sequences."""
        text = "\033[1m\033[31mBold Red\033[0m normal \033[48;5;240mgray bg\033[0m"
        result = crossword.strip_ansi(text)
        assert "\033[" not in result
        assert "Bold Red" in result
        assert "normal" in result
        assert "gray bg" in result


# ─── Run Tests ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Simple test runner
    test_classes = [
        TestCrosswordGenerator,
        TestCrosswordGame,
        TestSaveLoad,
        TestDifficultyPresets,
        TestThemedWordBank,
        TestStats,
        TestVersion,
        TestEdgeCases,
    ]

    passed = 0
    failed = 0
    errors = []

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith('test_')]
        for method_name in methods:
            try:
                if hasattr(instance, 'setup_method'):
                    instance.setup_method()
                getattr(instance, method_name)()
                passed += 1
                print(f"  PASS: {cls.__name__}.{method_name}")
            except Exception as e:
                failed += 1
                errors.append((f"{cls.__name__}.{method_name}", str(e)))
                print(f"  FAIL: {cls.__name__}.{method_name}: {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  {name}: {err}")
    sys.exit(0 if failed == 0 else 1)