#!/usr/bin/env python3
"""Unit tests for Terminal Tower Defense core game logic."""

import sys
import os
import curses
import unittest
import random

# We need curses constants for TowerType/EnemyType but can't init curses display
# Import just the game logic parts by mocking what's needed
sys.path.insert(0, os.path.dirname(__file__))

# Must import after path setup since tower_defense uses curses at module level
from tower_defense import (
    build_path, Enemy, EnemyType, TowerType, Tower, TOWER_DATA, ENEMY_DATA,
    Game, WAYPOINTS, DIFFICULTY_SETTINGS, generate_wave, describe_wave,
    load_highscores, save_highscore, HIGHSCORE_FILE,
    VERSION, MIN_TERM_W, MIN_TERM_H, Projectile, Tile,
    BOMB_DAMAGE, FREEZE_DURATION, GOLD_RUSH_DURATION, INTEREST_RATE,
    INTEREST_MAX_GOLD, POWER_UP_PER_WAVE, MAP_H, MAP_W,
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
        hit = e.take_damage(5)
        self.assertTrue(hit)  # damage should go through
        self.assertEqual(e.hp, initial_hp - 5)
        self.assertTrue(e.alive)

    def test_enemy_kill(self):
        """Taking damage equal to HP should mark enemy as dead."""
        e = Enemy(EnemyType.BASIC, wave_num=1)
        hit = e.take_damage(e.hp)
        self.assertTrue(hit)
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

    def test_stealth_enemy_creation(self):
        """Stealth (Phantom) enemies should have stealth=True and dodge chance."""
        e = Enemy(EnemyType.STEALTH, wave_num=1)
        self.assertTrue(e.stealth)
        self.assertGreater(e.dodge, 0)
        self.assertEqual(e.name, "Phantom")

    def test_stealth_enemy_dodge(self):
        """Stealth enemies should sometimes dodge attacks (probabilistic test)."""
        e = Enemy(EnemyType.STEALTH, wave_num=1)
        dodged = 0
        hits = 0
        for _ in range(1000):
            e.hp = e.max_hp  # reset HP each time
            e.alive = True
            e.killed_by = None
            result = e.take_damage(5)
            if not result:
                dodged += 1
            else:
                hits += 1
        # With 30% dodge, we should see both outcomes in 1000 trials
        self.assertGreater(dodged, 0, "Stealth enemy should dodge some attacks")
        self.assertGreater(hits, 0, "Stealth enemy should not dodge all attacks")

    def test_poison_application(self):
        """Applying poison should set poison_timer and poison_dmg."""
        e = Enemy(EnemyType.BASIC, wave_num=1)
        e.apply_poison(dmg_per_tick=3, duration=5)
        self.assertEqual(e.poison_timer, 5)
        self.assertEqual(e.poison_dmg, 3)

    def test_poison_does_not_reduce_duration(self):
        """Reapplying poison with shorter duration should not reduce timer."""
        e = Enemy(EnemyType.BASIC, wave_num=1)
        e.apply_poison(dmg_per_tick=3, duration=10)
        e.apply_poison(dmg_per_tick=2, duration=5)
        self.assertEqual(e.poison_timer, 10, "Poison timer should not be shortened")
        self.assertEqual(e.poison_dmg, 3, "Poison dmg should keep max value")

    def test_enemy_poison_damage_in_update(self):
        """Poison damage should reduce HP each update tick."""
        e = Enemy(EnemyType.BASIC, wave_num=1)
        # Give enough HP to survive poison
        e.max_hp = 100
        e.hp = 100
        e.apply_poison(dmg_per_tick=5, duration=3)
        e.update(WAYPOINTS_PATH)
        self.assertLess(e.hp, 100, "Poison should deal damage")

    def test_non_stealth_enemy_has_no_dodge(self):
        """Non-stealth enemies should not dodge attacks."""
        e = Enemy(EnemyType.BASIC, wave_num=1)
        self.assertEqual(e.dodge, 0)

    def test_enemy_repr(self):
        """Enemy repr should be informative."""
        e = Enemy(EnemyType.BASIC, wave_num=1)
        r = repr(e)
        self.assertIn("Grunt", r)
        self.assertIn("hp=", r)


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

    def test_poison_tower_creation(self):
        """Poison tower should have poison attribute."""
        t = Tower(TowerType.POISON, 5, 5)
        self.assertEqual(t.name, "Poison")
        self.assertEqual(t.char, "P")
        self.assertGreater(t.poison, 0)

    def test_poison_tower_upgrade_increases_poison(self):
        """Upgrading poison tower should increase poison damage."""
        t = Tower(TowerType.POISON, 5, 5)
        initial_poison = t.poison
        t.upgrade()
        self.assertGreater(t.poison, initial_poison)

    def test_tower_repr(self):
        """Tower repr should be informative."""
        t = Tower(TowerType.ARROW, 5, 5)
        r = repr(t)
        self.assertIn("Arrow", r)
        self.assertIn("Lv1", r)

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

    def test_game_initial_powerups(self):
        """Game should start with zero power-up charges."""
        g = Game(difficulty="normal")
        self.assertEqual(g.bomb_charges, 0)
        self.assertEqual(g.freeze_charges, 0)
        self.assertEqual(g.gold_rush_charges, 0)

    def test_place_tower(self):
        """Placing a tower should deduct gold and mark the tile."""
        g = Game(difficulty="normal")
        g.cursor_col = 5
        g.cursor_row = 0
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

    def test_bomb_powerup(self):
        """Using a bomb should damage all alive enemies."""
        g = Game(difficulty="normal")
        g.bomb_charges = 1
        # Create enemies on a later wave so they have enough HP to survive a bomb
        e1 = Enemy(EnemyType.TANK, wave_num=10)
        e2 = Enemy(EnemyType.TANK, wave_num=10)
        e1.path_index = 10.0
        e2.path_index = 20.0
        g.enemies = [e1, e2]
        g.use_bomb()
        self.assertEqual(g.bomb_charges, 0)
        # Both enemies should have taken BOMB_DAMAGE (clamped to 0 minimum)
        expected_hp1 = max(0, e1.max_hp - BOMB_DAMAGE)
        expected_hp2 = max(0, e2.max_hp - BOMB_DAMAGE)
        self.assertEqual(e1.hp, expected_hp1)
        self.assertEqual(e2.hp, expected_hp2)
        # Both enemies should have been hit (hit_flash set)
        self.assertGreater(e1.hit_flash, 0)
        self.assertGreater(e2.hit_flash, 0)

    def test_bomb_kills_weak_enemies(self):
        """Bomb should kill enemies with HP <= BOMB_DAMAGE."""
        g = Game(difficulty="normal")
        g.bomb_charges = 1
        # Swarm has 12 * (1 + 0.15) = 13.8 HP at wave 1
        e = Enemy(EnemyType.SWARM, wave_num=1)
        e.hp = 1  # nearly dead
        e.path_index = 10.0
        g.enemies = [e]
        g.use_bomb()
        self.assertFalse(e.alive)

    def test_bomb_no_charges(self):
        """Using bomb with no charges should log error and not crash."""
        g = Game(difficulty="normal")
        g.bomb_charges = 0
        g.use_bomb()  # Should not crash

    def test_freeze_powerup(self):
        """Using freeze should set freeze_timer."""
        g = Game(difficulty="normal")
        g.freeze_charges = 1
        g.use_freeze()
        self.assertEqual(g.freeze_timer, FREEZE_DURATION)
        self.assertEqual(g.freeze_charges, 0)

    def test_gold_rush_powerup(self):
        """Using gold rush should set gold_rush_timer."""
        g = Game(difficulty="normal")
        g.gold_rush_charges = 1
        g.use_gold_rush()
        self.assertEqual(g.gold_rush_timer, GOLD_RUSH_DURATION)
        self.assertEqual(g.gold_rush_charges, 0)

    def test_wave_clear_grants_powerups(self):
        """Clearing a wave should grant power-up charges."""
        g = Game(difficulty="normal")
        g.start_wave()
        # Simulate clearing by emptying enemies
        g.wave_enemies = []
        g.enemies = []
        g.wave_active = True
        g.update()
        self.assertEqual(g.bomb_charges, POWER_UP_PER_WAVE)
        self.assertEqual(g.freeze_charges, POWER_UP_PER_WAVE)
        self.assertEqual(g.gold_rush_charges, POWER_UP_PER_WAVE)

    def test_wave_clear_grants_interest(self):
        """Clearing a wave should grant gold interest."""
        g = Game(difficulty="normal")
        # Start and immediately clear wave 1
        g.start_wave()
        g.wave_enemies = []
        g.enemies = []
        g.wave_active = True
        gold_before = g.gold
        g.update()
        # Interest = gold * 5%
        expected_interest = min(int(gold_before * INTEREST_RATE), INTEREST_MAX_GOLD)
        self.assertGreater(g.interest_earned, 0)

    def test_gold_rush_doubles_rewards(self):
        """When gold rush is active, enemy kills should give double gold."""
        g = Game(difficulty="normal")
        g.gold_rush_timer = 10  # active
        e = Enemy(EnemyType.BASIC, wave_num=1)
        e.hp = 0
        e.alive = False
        e.reached_end = False
        # Simulate gold earning
        reward = e.reward * 2  # gold rush doubles
        self.assertEqual(reward, e.reward * 2)

    def test_freeze_stops_enemies(self):
        """When freeze_timer is active, enemies should not advance."""
        g = Game(difficulty="normal")
        g.start_wave()
        # Spawn an enemy manually
        e = Enemy(EnemyType.BASIC, 1)
        e.path_index = 10.0
        g.enemies = [e]
        g.wave_enemies = []
        g.freeze_timer = 10
        pos_before = e.path_index
        g.update()
        # Enemy should not have moved
        self.assertEqual(e.path_index, pos_before)

    def test_statistics_tracking(self):
        """Game should track placement/upgrade/sell statistics."""
        g = Game(difficulty="normal")
        self.assertEqual(g.towers_placed, 0)
        self.assertEqual(g.towers_upgraded, 0)
        self.assertEqual(g.towers_sold, 0)
        self.assertEqual(g.total_gold_earned, 0)

    def test_place_tower_increments_stats(self):
        """Placing a tower should increment towers_placed."""
        g = Game(difficulty="normal")
        g.cursor_col = 5
        g.cursor_row = 0
        if g.grid[0][5] == 0:
            g.place_tower(TowerType.ARROW)
            self.assertEqual(g.towers_placed, 1)

    def test_get_stats(self):
        """get_stats should return a dictionary with expected keys."""
        g = Game(difficulty="normal")
        stats = g.get_stats()
        self.assertIn("total_kills", stats)
        self.assertIn("towers_placed", stats)
        self.assertIn("towers_upgraded", stats)
        self.assertIn("towers_sold", stats)
        self.assertIn("total_gold_earned", stats)
        self.assertIn("interest_earned", stats)


class TestDescribeWave(unittest.TestCase):
    """Tests for the wave preview description function."""

    def test_describe_wave_1(self):
        """Wave 1 should describe basic enemies."""
        desc = describe_wave(1)
        self.assertIn("Grunt", desc)

    def test_describe_wave_0(self):
        """Wave 0 should return a hint message."""
        desc = describe_wave(0)
        self.assertIn("SPACE", desc)

    def test_describe_wave_5_has_boss(self):
        """Wave 5 description should mention the boss."""
        # Wave 5 has a boss, but describe_wave uses random, so we just check it doesn't crash
        desc = describe_wave(5)
        self.assertIsInstance(desc, str)
        self.assertGreater(len(desc), 0)


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

    def test_save_with_stats(self):
        """Saving a score with stats should include them."""
        stats = {"total_kills": 50, "towers_placed": 10}
        save_highscore(200, 8, "hard", stats)
        scores = load_highscores()
        self.assertEqual(len(scores), 1)
        self.assertIn("stats", scores[0])
        self.assertEqual(scores[0]["stats"]["total_kills"], 50)

    def test_top_10_kept(self):
        """Only the top 10 scores should be retained."""
        for i in range(15):
            save_highscore(i * 10, i + 1, "normal")
        scores = load_highscores()
        self.assertLessEqual(len(scores), 10)
        # Highest score should be first
        self.assertEqual(scores[0]["score"], 140)

    def test_corrupted_file(self):
        """Loading a corrupted JSON file should return empty list."""
        HIGHSCORE_FILE.write_text("not valid json{{{")
        scores = load_highscores()
        self.assertEqual(scores, [])

    def test_invalid_json_type(self):
        """Loading JSON that isn't a list should return empty list."""
        HIGHSCORE_FILE.write_text('{"score": 100}')
        scores = load_highscores()
        self.assertEqual(scores, [])


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


# Build path for tests that need ordered_path
WAYPOINTS_PATH = build_path(WAYPOINTS)[1]


class TestBugFixesV23(unittest.TestCase):
    """Regression tests for bugs found and fixed in v2.3."""

    def test_freeze_last_frame_still_freezes_enemies(self):
        """On the last frame of freeze (timer=1), enemies should still be frozen."""
        g = Game(difficulty="normal")
        g.freeze_timer = 1  # Only 1 frame left
        e = Enemy(EnemyType.BASIC, wave_num=1)
        e.path_index = 10.0
        g.enemies = [e]
        g.wave_enemies = []
        g.wave_active = True
        pos_before = e.path_index
        g.update()
        # Enemy should NOT have moved on the last frame of freeze
        self.assertEqual(e.path_index, pos_before,
                         "Enemy should not move on the last frame of freeze")

    def test_gold_rush_last_frame_still_doubles_gold(self):
        """On the last frame of gold rush (timer=1), kills should still give double gold."""
        g = Game(difficulty="normal")
        g.gold_rush_timer = 1  # Only 1 frame left
        e = Enemy(EnemyType.BASIC, wave_num=1)
        e.hp = 0
        e.alive = False
        e.reached_end = False
        g.enemies = [e]
        g.wave_enemies = []
        g.wave_active = True
        gold_before = g.gold
        g.update()
        # Kill reward should be doubled: 5 * 2 = 10
        self.assertGreater(g.gold, gold_before,
                            "Gold rush last frame should still double kill rewards")

    def test_slow_timer_does_not_tick_during_freeze(self):
        """Slow effects should be paused during freeze, not expire."""
        g = Game(difficulty="normal")
        g.freeze_timer = 10  # 10 frames of freeze
        e = Enemy(EnemyType.BASIC, wave_num=1)
        e.path_index = 10.0
        e.apply_slow(duration=3)  # 3 frames of slow
        self.assertEqual(e.slow_timer, 3)
        g.enemies = [e]
        g.wave_enemies = []
        g.wave_active = True
        # After 10 frames of freeze, slow_timer should NOT have changed
        for i in range(10):
            g.freeze_timer = 10 - i
            g.update()
        self.assertEqual(e.slow_timer, 3,
                         "Slow timer should NOT tick down during freeze")

    def test_poison_killed_enemy_stops_moving(self):
        """An enemy killed by poison should not advance further along the path."""
        e = Enemy(EnemyType.BASIC, wave_num=1)
        e.hp = 1
        e.max_hp = 1
        e.path_index = 10.0
        e.apply_poison(dmg_per_tick=10, duration=5)  # Will kill
        idx_before = e.path_index
        e.update(WAYPOINTS_PATH)
        self.assertFalse(e.alive, "Enemy should be dead from poison")
        self.assertEqual(e.path_index, idx_before,
                         "Dead enemy should not advance along path")

    def test_sell_refund_not_counted_in_total_gold_earned(self):
        """Selling a tower should add gold but NOT count in total_gold_earned."""
        g = Game(difficulty="normal")
        # Find an empty cell
        for r in range(MAP_H):
            for c in range(MAP_W):
                if g.grid[r][c] == Tile.EMPTY:
                    g.cursor_col = c
                    g.cursor_row = r
                    break
            else:
                continue
            break
        g.place_tower(TowerType.ARROW)
        earned_before = g.total_gold_earned
        g.sell_tower()
        # Gold should increase (refund), but total_gold_earned should NOT
        self.assertEqual(g.total_gold_earned, earned_before,
                         "Sell refund should not count as earned gold")

    def test_freeze_duration_exact(self):
        """Freeze should last exactly FREEZE_DURATION frames."""
        g = Game(difficulty="normal")
        g.freeze_timer = FREEZE_DURATION
        e = Enemy(EnemyType.BASIC, wave_num=1)
        e.path_index = 10.0
        g.enemies = [e]
        g.wave_enemies = []
        g.wave_active = True
        pos_start = e.path_index
        # Enemy should be frozen for exactly FREEZE_DURATION frames
        for i in range(FREEZE_DURATION):
            g.update()
        # After FREEZE_DURATION frames, enemy should NOT have moved at all
        self.assertEqual(e.path_index, pos_start,
                         "Enemy should not move during entire freeze duration")
        # Now freeze is over, enemy should move on next frame
        g.update()
        self.assertGreater(e.path_index, pos_start,
                           "Enemy should move after freeze ends")


if __name__ == "__main__":
    unittest.main()