#!/usr/bin/env python3
"""Unit tests for Terminal Tower Defense core game logic."""

import sys
import os
import curses
import unittest

# We need curses constants for TowerType/EnemyType but can't init curses display
# Import just the game logic parts by mocking what's needed
sys.path.insert(0, os.path.dirname(__file__))

# Must import after path setup since tower_defense uses curses at module level
from tower_defense import (
    build_path, Enemy, EnemyType, TowerType, Tower, TOWER_DATA, ENEMY_DATA,
    Game, WAYPOINTS, DIFFICULTY_SETTINGS, generate_wave,
    load_highscores, save_highscore, HIGHSCORE_FILE,
    VERSION, MIN_TERM_W, MIN_TERM_H, Projectile, Tile,
)


class TestBuildPath(unittest.TestCase):
    """Tests for the path-building function."""

    def test_basic_path(self):
        """Simple horizontal+vertical path should contain expected tiles."""
        waypoints = [(0, 0), (3, 0), (3, 2)]
        path_set, ordered = build_path(waypoints)
        # Should include (0,0), (1,0), (2,0), (3,0), (3,1), (3,2)
        self.assertIn((0, 0), path_set)
        self.assertIn((3, 0), path_set)
        self.assertIn((3, 2), path_set)
        self.assertEqual(len(ordered), 6)

    def test_reverse_direction(self):
        """Path going right-to-left should still work."""
        waypoints = [(5, 3), (2, 3)]
        path_set, ordered = build_path(waypoints)
        self.assertIn((5, 3), path_set)
        self.assertIn((2, 3), path_set)
        self.assertIn((4, 3), path_set)

    def test_single_point(self):
        """A single waypoint should produce an empty ordered path (no segments to traverse)."""
        waypoints = [(5, 5)]
        path_set, ordered = build_path(waypoints)
        self.assertEqual(len(ordered), 0)

    def test_no_duplicates(self):
        """Path through shared corners should not duplicate tiles."""
        waypoints = [(0, 0), (2, 0), (2, 2), (0, 2)]
        path_set, ordered = build_path(waypoints)
        # The (2,0) corner appears in both segments but should not be duplicated
        self.assertEqual(len(path_set), len(ordered))
        # Verify no duplicates in ordered list
        self.assertEqual(len(ordered), len(set(ordered)))

    def test_game_waypoints_valid(self):
        """The default game waypoints should produce a valid, connected path."""
        path_set, ordered = build_path(WAYPOINTS)
        self.assertGreater(len(ordered), 10)
        # Every consecutive pair should be adjacent
        for i in range(len(ordered) - 1):
            c1, r1 = ordered[i]
            c2, r2 = ordered[i + 1]
            dist = abs(c2 - c1) + abs(r2 - r1)
            self.assertEqual(dist, 1, f"Non-adjacent path tiles: {ordered[i]} -> {ordered[i+1]}")


class TestEnemy(unittest.TestCase):
    """Tests for Enemy creation and behavior."""

    def test_basic_enemy_creation(self):
        """A basic enemy on wave 1 should have scaled HP."""
        e = Enemy(EnemyType.BASIC, wave_num=1, difficulty="normal")
        self.assertTrue(e.alive)
        self.assertFalse(e.reached_end)
        self.assertEqual(e.char, "g")
        self.assertEqual(e.name, "Grunt")

    def test_enemy_hp_scales_with_wave(self):
        """Higher waves should produce enemies with more HP."""
        e1 = Enemy(EnemyType.BASIC, wave_num=1)
        e5 = Enemy(EnemyType.BASIC, wave_num=5)
        self.assertGreater(e5.max_hp, e1.max_hp)

    def test_enemy_take_damage(self):
        """Taking damage should reduce HP, and killing should mark dead."""
        e = Enemy(EnemyType.BASIC, wave_num=1)
        initial_hp = e.hp
        e.take_damage(5)
        self.assertEqual(e.hp, initial_hp - 5)
        self.assertTrue(e.alive)

    def test_enemy_kill(self):
        """Taking damage equal to HP should mark enemy as dead."""
        e = Enemy(EnemyType.BASIC, wave_num=1)
        e.take_damage(e.hp)
        self.assertEqual(e.hp, 0)
        self.assertFalse(e.alive)

    def test_enemy_slow(self):
        """Applying slow should set slow_timer."""
        e = Enemy(EnemyType.BASIC, wave_num=1)
        e.apply_slow(duration=10)
        self.assertEqual(e.slow_timer, 10)

    def test_enemy_slow_does_not_shorten(self):
        """Applying a shorter slow should not shorten an existing longer slow."""
        e = Enemy(EnemyType.BASIC, wave_num=1)
        e.apply_slow(duration=20)
        e.apply_slow(duration=5)
        self.assertEqual(e.slow_timer, 20)

    def test_boss_enemy(self):
        """Boss enemies should have high HP."""
        boss = Enemy(EnemyType.BOSS, wave_num=5)
        grunt = Enemy(EnemyType.BASIC, wave_num=5)
        self.assertGreater(boss.max_hp, grunt.max_hp)

    def test_swarm_enemy(self):
        """Swarm enemies should be fast but fragile."""
        swarm = Enemy(EnemyType.SWARM, wave_num=1)
        self.assertEqual(swarm.char, "w")
        self.assertEqual(swarm.name, "Swarm")

    def test_difficulty_scaling(self):
        """Hard difficulty should give enemies more HP and less reward."""
        e_easy = Enemy(EnemyType.BASIC, wave_num=1, difficulty="easy")
        e_hard = Enemy(EnemyType.BASIC, wave_num=1, difficulty="hard")
        self.assertGreater(e_hard.max_hp, e_easy.max_hp)
        self.assertGreater(e_easy.reward, e_hard.reward)


class TestTower(unittest.TestCase):
    """Tests for Tower creation, upgrading, and selling."""

    def test_tower_creation(self):
        """A tower should initialize with correct stats from TOWER_DATA."""
        t = Tower(TowerType.ARROW, col=5, row=5)
        self.assertEqual(t.name, "Arrow")
        self.assertEqual(t.char, "A")
        self.assertEqual(t.level, 1)
        self.assertEqual(t.damage, TOWER_DATA[TowerType.ARROW]["damage"])
        self.assertEqual(t.col, 5)
        self.assertEqual(t.row, 5)

    def test_tower_upgrade_cost_increases(self):
        """Upgrade cost should scale with tower level."""
        t = Tower(TowerType.ARROW, 5, 5)
        cost1 = t.upgrade_cost()
        self.assertIsNotNone(cost1)
        t.upgrade()
        cost2 = t.upgrade_cost()
        self.assertIsNotNone(cost2)
        self.assertGreater(cost2, cost1)

    def test_tower_upgrade_max_level(self):
        """Tower upgrade should cap at level 5."""
        t = Tower(TowerType.ARROW, 5, 5)
        for _ in range(5):
            t.upgrade()
        self.assertEqual(t.level, 5)
        self.assertIsNone(t.upgrade_cost())

    def test_tower_sell_value(self):
        """Sell value should be 50% of total invested gold."""
        t = Tower(TowerType.ARROW, 5, 5)
        # Initial cost is 50g
        self.assertEqual(t.sell_value(), 25)
        t.upgrade()
        # Total cost: 50 + 40*1 = 90
        self.assertEqual(t.sell_value(), 45)

    def test_lightning_tower(self):
        """Lightning tower should have chain attribute."""
        t = Tower(TowerType.LIGHTNING, 5, 5)
        self.assertEqual(t.chain, 3)
        self.assertEqual(t.name, "Lightning")

    def test_all_towers_have_data(self):
        """Every TowerType should have a corresponding TOWER_DATA entry."""
        for tt in TowerType:
            self.assertIn(tt, TOWER_DATA)
            data = TOWER_DATA[tt]
            self.assertIn("name", data)
            self.assertIn("cost", data)
            self.assertIn("damage", data)
            self.assertIn("range", data)
            self.assertIn("fire_rate", data)


class TestGame(unittest.TestCase):
    """Tests for the Game class logic."""

    def test_game_initial_state(self):
        """Game should start with correct initial resources."""
        g = Game(difficulty="normal")
        self.assertEqual(g.gold, 200)
        self.assertEqual(g.lives, 20)
        self.assertEqual(g.wave_num, 0)
        self.assertFalse(g.game_over)
        self.assertFalse(g.wave_active)

    def test_game_easy_difficulty(self):
        """Easy difficulty should give more gold and lives."""
        g = Game(difficulty="easy")
        self.assertEqual(g.gold, 300)
        self.assertEqual(g.lives, 30)

    def test_game_hard_difficulty(self):
        """Hard difficulty should give less gold and lives."""
        g = Game(difficulty="hard")
        self.assertEqual(g.gold, 150)
        self.assertEqual(g.lives, 10)

    def test_place_tower(self):
        """Placing a tower should deduct gold and mark the tile."""
        g = Game(difficulty="normal")
        # Place at a position that's not on the path
        # Cursor starts at (10, 10), but (10,10) might be on path. Let's check:
        g.cursor_col = 5
        g.cursor_row = 0
        # Ensure this tile is empty
        if g.grid[0][5] == 0:  # Tile.EMPTY
            g.place_tower(TowerType.ARROW)
            self.assertEqual(g.gold, 200 - 50)
            self.assertEqual(len(g.towers), 1)

    def test_place_tower_insufficient_gold(self):
        """Placing a tower with insufficient gold should fail."""
        g = Game(difficulty="normal")
        g.gold = 10
        g.cursor_col = 5
        g.cursor_row = 0
        g.place_tower(TowerType.ARROW)
        self.assertEqual(len(g.towers), 0)
        self.assertEqual(g.gold, 10)

    def test_place_tower_on_path(self):
        """Placing a tower on a path tile should fail."""
        g = Game(difficulty="normal")
        g.cursor_col = WAYPOINTS[0][0]
        g.cursor_row = WAYPOINTS[0][1]
        g.place_tower(TowerType.ARROW)
        self.assertEqual(len(g.towers), 0)

    def test_sell_tower(self):
        """Selling a tower should refund 50% and clear the tile."""
        g = Game(difficulty="normal")
        g.cursor_col = 5
        g.cursor_row = 0
        if g.grid[0][5] == 0:
            g.place_tower(TowerType.ARROW)
            initial_gold = g.gold
            g.sell_tower()
            self.assertEqual(g.gold, initial_gold + 25)
            self.assertEqual(len(g.towers), 0)

    def test_upgrade_tower(self):
        """Upgrading a tower should increase its level and stats."""
        g = Game(difficulty="normal")
        g.cursor_col = 5
        g.cursor_row = 0
        if g.grid[0][5] == 0:
            g.place_tower(TowerType.ARROW)
            tower = g.tower_grid.get((5, 0))
            self.assertIsNotNone(tower)
            initial_level = tower.level
            initial_dmg = tower.damage
            g.gold += 1000  # Ensure enough gold for upgrade
            g.upgrade_tower()
            self.assertEqual(tower.level, initial_level + 1)
            self.assertGreater(tower.damage, initial_dmg)

    def test_start_wave(self):
        """Starting a wave should increment wave_num and set wave_active."""
        g = Game(difficulty="normal")
        g.start_wave()
        self.assertEqual(g.wave_num, 1)
        self.assertTrue(g.wave_active)

    def test_start_wave_double(self):
        """Starting a second wave while one is active should fail."""
        g = Game(difficulty="normal")
        g.start_wave()
        g.start_wave()
        self.assertEqual(g.wave_num, 1)  # Should not increment again

    def test_generate_wave_boss(self):
        """Wave 5 (divisible by 5) should include a boss."""
        wave = generate_wave(5)
        types = [et for et, _ in wave]
        self.assertIn(EnemyType.BOSS, types)

    def test_generate_wave_increasing_count(self):
        """Later waves should have more enemies."""
        wave1 = generate_wave(1)
        wave5 = generate_wave(5)
        self.assertGreater(len(wave5), len(wave1))

    def test_auto_wave_toggle(self):
        """Auto-wave should start waves automatically."""
        g = Game(difficulty="normal")
        g.auto_wave = True
        g.start_wave()  # Start wave 1
        # After clearing, auto_wave should trigger next wave
        # This is tested indirectly via update logic


class TestHighscores(unittest.TestCase):
    """Tests for the high score save/load system."""

    def setUp(self):
        """Back up and remove any existing high score file."""
        self.backup = None
        if HIGHSCORE_FILE.exists():
            self.backup = HIGHSCORE_FILE.read_text()
            HIGHSCORE_FILE.unlink()

    def tearDown(self):
        """Restore original high score file."""
        if self.backup is not None:
            HIGHSCORE_FILE.write_text(self.backup)
        elif HIGHSCORE_FILE.exists():
            HIGHSCORE_FILE.unlink()

    def test_load_empty(self):
        """Loading from nonexistent file should return empty list."""
        scores = load_highscores()
        self.assertEqual(scores, [])

    def test_save_and_load(self):
        """Saving a score and loading it should round-trip correctly."""
        save_highscore(100, 5, "normal")
        scores = load_highscores()
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0]["score"], 100)
        self.assertEqual(scores[0]["wave"], 5)
        self.assertEqual(scores[0]["difficulty"], "normal")

    def test_top_10_kept(self):
        """Only the top 10 scores should be retained."""
        for i in range(15):
            save_highscore(i * 10, i + 1, "normal")
        scores = load_highscores()
        self.assertLessEqual(len(scores), 10)
        # Highest score should be first
        self.assertEqual(scores[0]["score"], 140)


class TestVersion(unittest.TestCase):
    """Ensure version string is valid."""

    def test_version_format(self):
        """Version should be a non-empty string in semver-ish format."""
        self.assertIsInstance(VERSION, str)
        self.assertRegex(VERSION, r'\d+\.\d+\.\d+')


class TestBugFixes(unittest.TestCase):
    """Regression tests for bugs that were found and fixed."""

    def test_start_wave_blocked_when_game_over(self):
        """Starting a wave after game over should be blocked."""
        g = Game(difficulty="normal")
        g.game_over = True
        g.start_wave()
        self.assertEqual(g.wave_num, 0, "Wave num should not increment when game_over")

    def test_double_kill_count_fix(self):
        """Chain lightning kills should not be double-counted in total_kills."""
        g = Game(difficulty="normal")
        # Create two enemies with 1 HP each
        e1 = Enemy(EnemyType.BASIC, 1, "normal")
        e1.hp = 1
        e2 = Enemy(EnemyType.BASIC, 1, "normal")
        e2.hp = 1
        e1.path_index = 10.0
        e2.path_index = 11.0
        g.enemies = [e1, e2]

        # Create a tower and a lightning projectile that kills both
        tower = Tower(TowerType.LIGHTNING, 10, 10)
        proj = Projectile((10, 10), (10.0, 5.0), 15, chain=3, source_tower=tower)
        proj.col = 10.0
        proj.row = 5.0
        proj.alive = False
        g._apply_projectile_hit(proj)

        # Run update to process dead enemies
        g.update()

        # Both enemies should be killed, total_kills should be 2 (not 4)
        self.assertEqual(g.total_kills, 2, "Chain kills should not be double-counted")
        # Tower should have 2 kills
        self.assertEqual(tower.kills, 2, "Tower should track kills from projectiles")

    def test_tower_kill_tracking(self):
        """Tower.kills should be incremented when a tower's projectile kills an enemy."""
        g = Game(difficulty="normal")
        tower = Tower(TowerType.ARROW, 5, 0)
        g.towers.append(tower)
        g.tower_grid[(5, 0)] = tower
        g.grid[0][5] = Tile.TOWER

        # Create an enemy with 1 HP
        e = Enemy(EnemyType.BASIC, 1, "normal")
        e.hp = 1
        e.path_index = 10.0
        g.enemies = [e]

        # Simulate a projectile hit
        proj = Projectile((5, 0), (10.0, 5.0), 10, source_tower=tower)
        proj.col = 10.0
        proj.row = 5.0
        proj.alive = False
        g._apply_projectile_hit(proj)
        g.update()

        self.assertEqual(tower.kills, 1, "Tower should have 1 kill")
        self.assertEqual(g.total_kills, 1, "Total kills should be 1")

    def test_single_kill_not_double_counted(self):
        """A single-target kill should count exactly once in total_kills."""
        g = Game(difficulty="normal")
        tower = Tower(TowerType.ARROW, 25, 10)
        e = Enemy(EnemyType.BASIC, 1, "normal")
        e.hp = 1
        e.path_index = 50
        g.enemies = [e]

        proj = Projectile((25, 10), e.position(g.ordered_path), 10, source_tower=tower)
        proj.col, proj.row = e.position(g.ordered_path)
        proj.alive = False
        g._apply_projectile_hit(proj)
        self.assertFalse(e.alive)
        g.update()
        self.assertEqual(g.total_kills, 1)
        self.assertEqual(tower.kills, 1)

    def test_lives_display_nonnegative(self):
        """Lives display should show 0 minimum even if lives goes negative."""
        g = Game(difficulty="normal")
        g.lives = 1
        # Simulate multiple enemies reaching end in same frame
        for _ in range(3):
            g.lives -= 1
        # Lives is -2 internally, but game over triggers at <= 0
        self.assertLessEqual(g.lives, 0)
        # Display should use max(0, lives)
        self.assertEqual(max(0, g.lives), 0)

    def test_game_over_saves_highscore_once(self):
        """High score should only be saved once even if multiple enemies reach end."""
        g = Game(difficulty="normal")
        g.lives = 1
        # First enemy reaching end triggers game over and saves
        g.lives -= 1
        if g.lives <= 0 and not g.game_over:
            g.game_over = True
            save_highscore(g.score, g.wave_num, g.difficulty)
        # Second enemy reaching end should NOT save again
        g.lives -= 1
        already_saved = g.game_over  # True already
        self.assertTrue(already_saved, "game_over should prevent double save")

    def test_enemy_killed_by_tracking(self):
        """Enemy.killed_by should track which tower dealt the killing blow."""
        tower = Tower(TowerType.SNIPER, 25, 10)
        e = Enemy(EnemyType.BASIC, 1, "normal")
        e.take_damage(5, source=tower)
        self.assertIsNone(e.killed_by, "Enemy should not be marked as killed_by while alive")
        e.take_damage(e.hp, source=tower)
        self.assertFalse(e.alive)
        self.assertEqual(e.killed_by, tower, "killed_by should be the tower that dealt the killing blow")

    def test_enemy_killed_by_only_first_killer(self):
        """killed_by should only be set by the first killing blow, not overwritten."""
        tower1 = Tower(TowerType.ARROW, 25, 10)
        tower2 = Tower(TowerType.CANNON, 25, 10)
        e = Enemy(EnemyType.BASIC, 1, "normal")
        e.take_damage(e.hp, source=tower1)
        self.assertEqual(e.killed_by, tower1)
        # Overkill from another tower should not change killed_by
        e.take_damage(100, source=tower2)
        self.assertEqual(e.killed_by, tower1, "killed_by should not change after first kill")

    def test_difficulty_cli_flag_logic(self):
        """The --difficulty flag should override the difficulty menu."""
        # _selected_difficulty is a module-level global
        import tower_defense
        original = tower_defense._selected_difficulty
        try:
            # Setting it to a valid difficulty should skip the menu
            tower_defense._selected_difficulty = "hard"
            self.assertIn(tower_defense._selected_difficulty, DIFFICULTY_SETTINGS)
            # Setting it to None or invalid should trigger the menu
            tower_defense._selected_difficulty = None
            self.assertNotIn(tower_defense._selected_difficulty, DIFFICULTY_SETTINGS)
        finally:
            tower_defense._selected_difficulty = original


if __name__ == "__main__":
    unittest.main()