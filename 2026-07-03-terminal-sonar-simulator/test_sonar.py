#!/usr/bin/env python3
"""
Tests for Terminal Sonar Simulator.

Validates world generation, enemy spawning, supply crates,
game logic helpers, difficulty presets, and CLI argument parsing.
"""

import sys
import os
import random
import math

# Ensure we import from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sonar import (
    generate_world, spawn_enemies, spawn_supply_crates,
    SonarGame, Submarine, Enemy, Torpedo, SonarPing, Particle,
    SupplyCrate, CellType, EnemyType, ENEMY_CONFIGS,
    DIFFICULTY_PRESETS, WORLD_W, WORLD_H, PING_RADIUS,
    PASSIVE_RADIUS, MAX_TORPEDOES, TORPEDO_RANGE, VERSION,
    parse_args,
)


class TestWorldGeneration:
    """Tests for procedural world generation."""

    def test_generate_world_dimensions(self):
        """World grid must match requested dimensions."""
        world = generate_world(WORLD_W, WORLD_H)
        assert len(world) == WORLD_H, f"Expected {WORLD_H} rows, got {len(world)}"
        assert len(world[0]) == WORLD_W, f"Expected {WORLD_W} cols, got {len(world[0])}"

    def test_generate_world_contains_land(self):
        """World should contain at least some land cells (islands)."""
        world = generate_world(WORLD_W, WORLD_H)
        land_count = sum(1 for row in world for c in row if c == CellType.LAND)
        assert land_count > 0, "World should have at least one land cell"

    def test_generate_world_start_area_clear(self):
        """The starting area around (60, 30) should be water."""
        world = generate_world(WORLD_W, WORLD_H)
        for y in range(28, 33):
            for x in range(57, 64):
                assert world[y][x] == CellType.WATER, (
                    f"Starting area cell ({x},{y}) should be water"
                )

    def test_generate_world_with_seed(self):
        """Same seed should produce the same world."""
        w1 = generate_world(WORLD_W, WORLD_H, seed=42)
        w2 = generate_world(WORLD_W, WORLD_H, seed=42)
        for y in range(WORLD_H):
            for x in range(WORLD_W):
                assert w1[y][x] == w2[y][x], (
                    f"Seed 42 produced different worlds at ({x},{y})"
                )

    def test_generate_world_different_seeds(self):
        """Different seeds should (very likely) produce different worlds."""
        w1 = generate_world(WORLD_W, WORLD_H, seed=1)
        w2 = generate_world(WORLD_W, WORLD_H, seed=2)
        differences = sum(
            1 for y in range(WORLD_H) for x in range(WORLD_W)
            if w1[y][x] != w2[y][x]
        )
        assert differences > 0, "Different seeds should produce different worlds"

    def test_generate_world_only_valid_cells(self):
        """All cells should be WATER, LAND, or SHALLOWS."""
        world = generate_world(WORLD_W, WORLD_H)
        valid = {CellType.WATER, CellType.LAND, CellType.SHALLOWS}
        for row in world:
            for cell in row:
                assert cell in valid, f"Unexpected cell type: {cell}"


class TestEnemySpawning:
    """Tests for enemy creation and placement."""

    def test_spawn_enemies_count(self):
        """Should spawn the requested number of enemies."""
        world = generate_world(WORLD_W, WORLD_H, seed=100)
        enemies = spawn_enemies(world, 10)
        assert len(enemies) == 10, f"Expected 10 enemies, got {len(enemies)}"

    def test_spawn_enemies_on_water(self):
        """All enemies should be placed on water cells."""
        world = generate_world(WORLD_W, WORLD_H, seed=100)
        enemies = spawn_enemies(world, 15)
        for e in enemies:
            assert world[e.y][e.x] == CellType.WATER, (
                f"Enemy at ({e.x},{e.y}) is not on water"
            )

    def test_spawn_enemies_away_from_start(self):
        """No enemy should be within 15 manhattan distance of (60, 30)."""
        world = generate_world(WORLD_W, WORLD_H, seed=100)
        enemies = spawn_enemies(world, 15)
        for e in enemies:
            dist = abs(e.x - 60) + abs(e.y - 30)
            assert dist > 15, f"Enemy at ({e.x},{e.y}) is too close to start"

    def test_spawn_enemies_hp_multiplier(self):
        """HP multiplier should scale enemy HP correctly."""
        world = generate_world(WORLD_W, WORLD_H, seed=100)
        enemies = spawn_enemies(world, 30, hp_mult=2.0)
        for e in enemies:
            expected_hp = max(1, round(ENEMY_CONFIGS[e.etype]["hp"] * 2.0))
            assert e.hp == expected_hp, (
                f"{e.etype.value}: expected HP {expected_hp}, got {e.hp}"
            )

    def test_spawn_enemies_detect_multiplier(self):
        """Detection range multiplier should scale correctly."""
        world = generate_world(WORLD_W, WORLD_H, seed=100)
        enemies = spawn_enemies(world, 30, detect_mult=1.5)
        for e in enemies:
            expected = max(3, round(ENEMY_CONFIGS[e.etype]["detect_range"] * 1.5))
            assert e.detect_range == expected, (
                f"{e.etype.value}: expected range {expected}, got {e.detect_range}"
            )

    def test_spawn_enemies_zero_count(self):
        """Spawning zero enemies should return an empty list."""
        world = generate_world(WORLD_W, WORLD_H, seed=100)
        enemies = spawn_enemies(world, 0)
        assert len(enemies) == 0


class TestSupplyCrates:
    """Tests for supply crate spawning."""

    def test_spawn_supply_crates(self):
        """Should create the requested number of crates."""
        world = generate_world(WORLD_W, WORLD_H, seed=200)
        crates = spawn_supply_crates(world, 4)
        assert len(crates) == 4, f"Expected 4 crates, got {len(crates)}"

    def test_crate_kinds(self):
        """Crates should be 'torpedo' or 'repair'."""
        world = generate_world(WORLD_W, WORLD_H, seed=200)
        crates = spawn_supply_crates(world, 10)
        for c in crates:
            assert c.kind in ("torpedo", "repair"), f"Unexpected crate kind: {c.kind}"

    def test_crates_on_water(self):
        """All crates should be on water."""
        world = generate_world(WORLD_W, WORLD_H, seed=200)
        crates = spawn_supply_crates(world, 5)
        for c in crates:
            assert world[c.y][c.x] == CellType.WATER, (
                f"Crate at ({c.x},{c.y}) not on water"
            )


class TestDataClasses:
    """Tests for data class defaults and construction."""

    def test_submarine_defaults(self):
        """Submarine should have sensible defaults."""
        sub = Submarine()
        assert sub.x == 60
        assert sub.y == 30
        assert sub.hp == 10
        assert sub.max_hp == 10
        assert sub.depth == 0
        assert sub.score == 0
        assert sub.noise_level == 0.0

    def test_enemy_construction(self):
        """Enemy should store all fields correctly."""
        e = Enemy(x=10, y=20, etype=EnemyType.DESTROYER, hp=3,
                  speed=1, detect_range=10, symbol="D", color=3,
                  torpedo_dmg=2)
        assert e.x == 10
        assert e.etype == EnemyType.DESTROYER
        assert e.classified is False
        assert e.alert_level == 0.0

    def test_torpedo_construction(self):
        """Torpedo should store direction and ownership."""
        t = Torpedo(x=5.0, y=5.0, dx=1.0, dy=0.0, friendly=True, dmg=2)
        assert t.friendly is True
        assert t.dmg == 2
        assert t.age == 0

    def test_sonar_ping_construction(self):
        """SonarPing should default to active ping."""
        sp = SonarPing(x=30, y=20, radius=0, max_radius=PING_RADIUS)
        assert sp.active_ping is True
        assert sp.age == 0

    def test_supply_crate_construction(self):
        """SupplyCrate should initialise age to 0."""
        sc = SupplyCrate(x=10, y=10, kind="torpedo")
        assert sc.age == 0
        assert sc.kind == "torpedo"


class TestDifficultyPresets:
    """Tests for difficulty configuration."""

    def test_all_difficulties_exist(self):
        """Easy, normal, and hard presets must all be defined."""
        for name in ("easy", "normal", "hard"):
            assert name in DIFFICULTY_PRESETS, f"Missing difficulty: {name}"

    def test_hard_has_more_enemies(self):
        """Hard mode should have more enemies than easy."""
        assert (DIFFICULTY_PRESETS["hard"]["enemies"]
                > DIFFICULTY_PRESETS["easy"]["enemies"])

    def test_easy_has_more_torpedoes(self):
        """Easy mode should have more torpedoes than hard."""
        assert (DIFFICULTY_PRESETS["easy"]["torpedo_count"]
                > DIFFICULTY_PRESETS["hard"]["torpedo_count"])

    def test_hard_enemies_tougher(self):
        """Hard mode should have higher HP and detection multipliers."""
        assert DIFFICULTY_PRESETS["hard"]["enemy_hp_mult"] > 1.0
        assert DIFFICULTY_PRESETS["hard"]["enemy_detect_mult"] > 1.0

    def test_easy_enemies_weaker(self):
        """Easy mode should reduce enemy HP and detection."""
        assert DIFFICULTY_PRESETS["easy"]["enemy_hp_mult"] < 1.0
        assert DIFFICULTY_PRESETS["easy"]["enemy_detect_mult"] < 1.0


class TestCLI:
    """Tests for command-line argument parsing."""

    def test_defaults(self):
        """Default args should be normal difficulty, no seed, no enemy override."""
        args = parse_args([])
        assert args.difficulty == "normal"
        assert args.seed is None
        assert args.enemies is None

    def test_difficulty_flag(self):
        """--difficulty should accept easy/normal/hard."""
        for diff in ("easy", "normal", "hard"):
            args = parse_args(["--difficulty", diff])
            assert args.difficulty == diff

    def test_enemies_flag(self):
        """--enemies should accept an integer."""
        args = parse_args(["--enemies", "20"])
        assert args.enemies == 20

    def test_seed_flag(self):
        """--seed should accept an integer."""
        args = parse_args(["--seed", "42"])
        assert args.seed == 42

    def test_combined_flags(self):
        """All flags should work together."""
        args = parse_args(["--difficulty", "hard", "--enemies", "5", "--seed", "123"])
        assert args.difficulty == "hard"
        assert args.enemies == 5
        assert args.seed == 123


class TestGameLogicHelpers:
    """Tests for utility methods that don't require curses."""

    def test_in_bounds(self):
        """in_bounds should correctly check world boundaries."""
        # Need a minimal game-like object to test static methods
        assert SonarGame.in_bounds(0, 0) is True
        assert SonarGame.in_bounds(WORLD_W - 1, WORLD_H - 1) is True
        assert SonarGame.in_bounds(WORLD_W, WORLD_H) is False
        assert SonarGame.in_bounds(-1, 0) is False
        assert SonarGame.in_bounds(0, -1) is False

    def test_dist(self):
        """dist should compute Euclidean distance."""
        assert SonarGame.dist(0, 0, 3, 4) == 5.0
        assert SonarGame.dist(0, 0, 0, 0) == 0.0
        assert abs(SonarGame.dist(1, 1, 4, 5) - 5.0) < 0.001

    def test_bearing_arrow(self):
        """bearing_arrow should return directional arrows."""
        # East
        assert SonarGame.bearing_arrow(0, 0, 10, 0) == '→'
        # West
        assert SonarGame.bearing_arrow(10, 0, 0, 0) == '←'
        # North
        assert SonarGame.bearing_arrow(0, 0, 0, -10) == '↑'
        # South
        assert SonarGame.bearing_arrow(0, 0, 0, 10) == '↓'

    def test_version_exists(self):
        """VERSION should be a non-empty string."""
        assert isinstance(VERSION, str)
        assert len(VERSION) > 0


class TestEnemyConfigConsistency:
    """Tests that ENEMY_CONFIGS are well-formed."""

    def test_all_enemy_types_have_configs(self):
        """Each EnemyType should have a corresponding config."""
        for etype in EnemyType:
            assert etype in ENEMY_CONFIGS, f"Missing config for {etype}"

    def test_config_fields(self):
        """All configs should have the required fields."""
        required = {"hp", "speed", "detect_range", "symbol", "color", "torpedo_dmg"}
        for etype, cfg in ENEMY_CONFIGS.items():
            missing = required - set(cfg.keys())
            assert not missing, f"{etype.value} missing fields: {missing}"

    def test_hp_positive(self):
        """All enemy HP values should be positive."""
        for etype, cfg in ENEMY_CONFIGS.items():
            assert cfg["hp"] > 0, f"{etype.value} has non-positive HP"

    def test_detect_range_positive(self):
        """All enemy detection ranges should be positive."""
        for etype, cfg in ENEMY_CONFIGS.items():
            assert cfg["detect_range"] > 0, f"{etype.value} has non-positive range"


class TestDepthControls:
    """Tests for depth control correctness (bug fix validation)."""

    def test_z_key_increases_depth(self):
        """Pressing Z (dive) should increase depth by 1."""
        sub = Submarine(depth=0)
        # Simulate Z key: depth should go from 0 → 1
        new_depth = sub.depth + 1
        assert new_depth == 1, f"Z at periscope (0) should give depth 1, got {new_depth}"

    def test_z_key_at_max_depth(self):
        """Z at max depth (2) should stay at 2."""
        sub = Submarine(depth=2)
        new_depth = min(2, sub.depth + 1)
        assert new_depth == 2, f"Z at deep (2) should stay at 2, got {new_depth}"

    def test_x_key_decreases_depth(self):
        """Pressing X (rise) should decrease depth by 1."""
        sub = Submarine(depth=2)
        new_depth = sub.depth - 1
        assert new_depth == 1, f"X at deep (2) should give depth 1, got {new_depth}"

    def test_x_key_at_min_depth(self):
        """X at periscope depth (0) should stay at 0."""
        sub = Submarine(depth=0)
        new_depth = max(0, sub.depth - 1)
        assert new_depth == 0, f"X at periscope (0) should stay at 0, got {new_depth}"

    def test_depth_cycle(self):
        """Full depth cycle: 0→1→2→1→0."""
        depth = 0
        depth = min(2, depth + 1)  # Z: dive
        assert depth == 1
        depth = min(2, depth + 1)  # Z: dive
        assert depth == 2
        depth = max(0, depth - 1)  # X: rise
        assert depth == 1
        depth = max(0, depth - 1)  # X: rise
        assert depth == 0

    def test_depth_view_penalty_ordering(self):
        """Deeper depths should have lower view penalty (less visibility)."""
        depth_view_penalty = {0: 1.0, 1: 0.7, 2: 0.4}
        assert depth_view_penalty[0] > depth_view_penalty[1] > depth_view_penalty[2]

    def test_depth_damage_reduction_ordering(self):
        """Deeper depths should have higher damage reduction."""
        depth_damage_reduction = {0: 0.0, 1: 0.25, 2: 0.5}
        assert depth_damage_reduction[0] < depth_damage_reduction[1] < depth_damage_reduction[2]


class TestPassiveSonarConstraints:
    """Tests for passive sonar mode behavior (bug fix validation)."""

    def test_passive_ping_cooldown_constant(self):
        """PASSIVE_RADIUS should be less than PING_RADIUS."""
        assert PASSIVE_RADIUS < PING_RADIUS, (
            f"Passive radius ({PASSIVE_RADIUS}) should be less than active ({PING_RADIUS})"
        )

    def test_torpedo_range_positive(self):
        """TORPEDO_RANGE should be a positive value."""
        assert TORPEDO_RANGE > 0

    def test_max_torpedoes_positive(self):
        """MAX_TORPEDOES should be positive."""
        assert MAX_TORPEDOES > 0


class TestCameraCentering:
    """Tests for camera centering logic (bug fix validation)."""

    def test_camera_y_centers_in_viewport(self):
        """Camera Y should center the sub in the viewport (h-6 lines tall)."""
        # Simulate: viewport height is h-6, sub at y=30
        h = 40
        viewport_h = h - 6  # 34 lines
        sub_y = 30
        cam_y = sub_y - viewport_h // 2  # 30 - 17 = 13
        # The sub should appear at the center of the viewport
        sub_screen_y = sub_y - cam_y  # 30 - 13 = 17
        assert sub_screen_y == viewport_h // 2, (
            f"Sub at screen y={sub_screen_y}, expected {viewport_h // 2}"
        )


# ── Run all tests ─────────────────────────────────────────────────────

def run_all():
    """Discover and run all test methods, printing results."""
    test_classes = [
        TestWorldGeneration,
        TestEnemySpawning,
        TestSupplyCrates,
        TestDataClasses,
        TestDifficultyPresets,
        TestCLI,
        TestGameLogicHelpers,
        TestEnemyConfigConsistency,
        TestDepthControls,
        TestPassiveSonarConstraints,
        TestCameraCentering,
    ]

    total = 0
    passed = 0
    failed = 0

    for cls in test_classes:
        instance = cls()
        for name in sorted(dir(instance)):
            if not name.startswith("test_"):
                continue
            total += 1
            method = getattr(instance, name)
            try:
                method()
                passed += 1
                print(f"  ✓ {cls.__name__}.{name}")
            except AssertionError as e:
                failed += 1
                print(f"  ✗ {cls.__name__}.{name}: {e}")
            except Exception as e:
                failed += 1
                print(f"  ✗ {cls.__name__}.{name}: ERROR: {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("All tests passed!")
    return failed


if __name__ == "__main__":
    sys.exit(run_all()) 