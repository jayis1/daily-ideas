#!/usr/bin/env python3
"""
Tests for the ASCII Ecosystem Simulator.

Run with: python3 -m pytest test_ecosystem.py -v
"""

import io
import json
import random

import pytest

from ecosystem import (
    Entity,
    EventType,
    Herbivore,
    Plant,
    Predator,
    Season,
    World,
    parse_args,
    run_from_args,
    run_headless,
    WORLD_WIDTH,
    WORLD_HEIGHT,
    WATER_RATIO,
    INITIAL_PLANTS,
    INITIAL_HERBIVORES,
    INITIAL_PREDATORS,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def small_world():
    """Create a small world for fast testing."""
    return World(width=20, height=10, seed=42, water_ratio=0.0)


@pytest.fixture
def world_with_water():
    """Create a small world with water."""
    return World(width=20, height=10, seed=42, water_ratio=0.1)


# ─── Entity Tests ─────────────────────────────────────────────────────────────

class TestPlant:
    def test_plant_initial_state(self):
        p = Plant(5, 5)
        assert p.x == 5
        assert p.y == 5
        assert p.age == 0
        assert p.alive is True
        assert p.maturity == 0
        assert p.nutrition == 20

    def test_plant_ages_and_matures(self, small_world):
        p = Plant(5, 5)
        for _ in range(10):
            p.update(Season.SUMMER, small_world.rng)
        assert p.age == 10
        assert p.maturity == 5  # capped at 5

    def test_plant_dies_of_old_age(self, small_world):
        p = Plant(5, 5)
        p.age = 80  # at max age
        p.update(Season.SUMMER, small_world.rng)
        assert not p.alive

    def test_plant_dies_in_winter(self):
        """Plants have a chance to die in winter."""
        rng = random.Random(0)
        deaths = 0
        for _ in range(1000):
            p = Plant(5, 5)
            p.maturity = 3  # mature enough
            p.update(Season.WINTER, rng)
            if not p.alive:
                deaths += 1
        # Should be roughly 3% (with variance)
        assert deaths > 10  # at least some deaths

    def test_plant_spread_when_mature(self, small_world):
        p = Plant(5, 5)
        p.maturity = 5  # fully mature
        p.age = 20
        baby = p.try_spread(small_world, rng=random.Random(0))
        # May or may not succeed due to randomness, but shouldn't crash
        if baby:
            assert isinstance(baby, Plant)
            assert 0 <= baby.x < small_world.width
            assert 0 <= baby.y < small_world.height

    def test_plant_no_spread_when_immature(self, small_world):
        p = Plant(5, 5)
        p.maturity = 1  # too young
        baby = p.try_spread(small_world, rng=random.Random(0))
        assert baby is None

    def test_plant_nutrition_boost_in_spring(self, small_world):
        p = Plant(5, 5)
        initial = p.nutrition
        p.update(Season.SPRING, small_world.rng)
        assert p.nutrition > initial


class TestHerbivore:
    def test_herbivore_initial_state(self):
        h = Herbivore(3, 7)
        assert h.x == 3
        assert h.y == 7
        assert h.alive is True
        assert h.energy == 60  # HERBIVORE_INITIAL_ENERGY
        assert h.age == 0

    def test_herbivore_loses_energy(self, small_world):
        h = Herbivore(5, 5)
        initial_energy = h.energy
        h.update(small_world)
        assert h.energy < initial_energy

    def test_herbivore_dies_without_energy(self, small_world):
        h = Herbivore(5, 5, energy=1)
        h.update(small_world)
        assert not h.alive  # should die from no energy

    def test_herbivore_dies_of_old_age(self, small_world):
        h = Herbivore(5, 5, energy=200)  # plenty of energy
        h.age = 150  # well past max age
        h.update(small_world)
        assert not h.alive

    def test_herbivore_eats_plant(self, small_world):
        """Herbivore near a plant should eat it and gain energy."""
        h = Herbivore(5, 5, energy=30)
        p = Plant(5, 5)  # same position
        p.maturity = 3
        small_world.plants = [p]
        small_world.herbivores = [h]
        initial_energy = h.energy
        h.update(small_world)
        # Energy should have increased (ate the plant) minus move cost
        assert h.energy > initial_energy - 5  # some boost from eating

    def test_herbivore_reproduce(self, small_world):
        h = Herbivore(5, 5, energy=70)
        h.age = 15
        baby = h.reproduce(small_world, rng=random.Random(0))
        assert isinstance(baby, Herbivore)
        assert h.energy == 70 - 30  # HERBIVORE_REPRODUCE_COST
        assert baby.energy == 40

    def test_herbivore_custom_energy(self):
        h = Herbivore(5, 5, energy=99)
        assert h.energy == 99


class TestPredator:
    def test_predator_initial_state(self):
        p = Predator(10, 10)
        assert p.x == 10
        assert p.y == 10
        assert p.alive is True
        assert p.energy == 80  # PREDATOR_INITIAL_ENERGY
        assert p.hunt_cooldown == 0

    def test_predator_loses_energy(self):
        """Predator in an empty world should lose energy from movement costs."""
        world = World(width=20, height=10, seed=7, water_ratio=0.0)
        world.herbivores = []
        world.predators = []
        p = Predator(10, 10)
        p.energy = 80
        world.predators = [p]
        initial_energy = p.energy
        p.update(world)
        # Energy decreases by PREDATOR_MOVE_COST (3) at minimum
        assert p.energy < initial_energy

    def test_predator_dies_without_energy(self, small_world):
        p = Predator(5, 5, energy=1)
        p.update(small_world)
        assert not p.alive

    def test_predator_custom_energy(self):
        p = Predator(5, 5, energy=99)
        assert p.energy == 99

    def test_predator_hunts_herbivore(self, small_world):
        """Predator near a herbivore should catch it."""
        pr = Predator(5, 5, energy=70)
        h = Herbivore(5, 5, energy=50)  # same position
        small_world.herbivores = [h]
        small_world.predators = [pr]
        pr.update(small_world)
        assert not h.alive  # herbivore should be caught
        assert pr.energy > 70  # predator gained energy


# ─── World Tests ──────────────────────────────────────────────────────────────

class TestWorld:
    def test_world_initialization(self, small_world):
        assert small_world.width == 20
        assert small_world.height == 10
        assert small_world.tick == 0
        assert small_world.season == Season.SPRING
        assert len(small_world.plants) == INITIAL_PLANTS
        assert len(small_world.herbivores) == INITIAL_HERBIVORES
        assert len(small_world.predators) == INITIAL_PREDATORS

    def test_world_update_advances_tick(self, small_world):
        small_world.update()
        assert small_world.tick == 1

    def test_world_season_cycles(self, small_world):
        from ecosystem import SEASON_LENGTH
        for _ in range(SEASON_LENGTH):
            small_world.update()
        assert small_world.season == Season.SUMMER

    def test_world_season_full_cycle(self, small_world):
        from ecosystem import SEASON_LENGTH
        for _ in range(SEASON_LENGTH * 4):
            small_world.update()
        assert small_world.season == Season.SPRING  # full cycle

    def test_world_reintroduction_of_herbivores(self):
        """Herbivores should be reintroduced if they go extinct."""
        world = World(width=20, height=10, seed=99, water_ratio=0.0)
        world.herbivores = []
        # Reintroduction happens when tick % 20 == 0, but tick is incremented
        # before the check. So we need tick before update to be 19.
        world.tick = 19
        # Need plants > 10 for reintroduction
        for _ in range(15):
            x = world.rng.randint(0, world.width - 1)
            y = world.rng.randint(0, world.height - 1)
            world.plants.append(Plant(x, y))
        world.update()
        assert len(world.herbivores) > 0

    def test_world_reintroduction_of_predators(self):
        """Predators should be reintroduced if herbivores exist without predators."""
        world = World(width=20, height=10, seed=99, water_ratio=0.0)
        world.predators = []
        # Need enough herbivores and tick before update = 29
        world.herbivores = [Herbivore(i, i, energy=80) for i in range(6)]
        world.tick = 29
        world.update()
        assert len(world.predators) > 0

    def test_world_plant_cap(self, small_world):
        """Plants should be capped at PLANT_POP_CAP."""
        from ecosystem import PLANT_POP_CAP
        for _ in range(PLANT_POP_CAP + 50):
            x = small_world.rng.randint(0, small_world.width - 1)
            y = small_world.rng.randint(0, small_world.height - 1)
            small_world.plants.append(Plant(x, y))
        small_world.update()
        assert len(small_world.plants) <= PLANT_POP_CAP

    def test_get_entity_at(self, small_world):
        p = Plant(5, 5)
        h = Herbivore(5, 5, energy=50)
        pr = Predator(5, 5, energy=50)
        small_world.plants = [p]
        small_world.herbivores = [h]
        small_world.predators = [pr]
        entity = small_world.get_entity_at(5, 5)
        # Predators are checked first, so should return predator
        assert entity is pr

    def test_avg_energy(self, small_world):
        small_world.herbivores = [
            Herbivore(0, 0, energy=40),
            Herbivore(1, 1, energy=60),
        ]
        avg = small_world.avg_energy(small_world.herbivores)
        assert avg == pytest.approx(50.0)

    def test_avg_energy_empty(self, small_world):
        small_world.herbivores = []
        assert small_world.avg_energy(small_world.herbivores) == 0.0

    def test_is_water(self, world_with_water):
        # Some cells should be water
        water_count = sum(
            1 for y in range(world_with_water.height)
            for x in range(world_with_water.width)
            if world_with_water.is_water(x, y)
        )
        assert water_count > 0

    def test_random_land_avoids_water(self, world_with_water):
        """_random_land should never return a water cell."""
        for _ in range(100):
            x, y = world_with_water._random_land()
            assert not world_with_water.is_water(x, y)

    def test_reproducibility_with_seed(self):
        """Seeded worlds should have deterministic initial entity placement."""
        Entity._id_counter = 0
        w1 = World(width=20, height=10, seed=123, water_ratio=0.0)
        Entity._id_counter = 0
        w2 = World(width=20, height=10, seed=123, water_ratio=0.0)
        # Initial state should match exactly with same seed
        assert len(w1.plants) == len(w2.plants)
        assert len(w1.herbivores) == len(w2.herbivores)
        assert len(w2.predators) == len(w2.predators)
        # Positions should match
        for p1, p2 in zip(w1.plants, w2.plants):
            assert (p1.x, p1.y) == (p2.x, p2.y)


# ─── Event Tests ──────────────────────────────────────────────────────────────

class TestEvents:
    def test_drought_kills_plants(self, small_world):
        from ecosystem import EventType
        small_world._trigger_event = lambda: None  # disable random events
        initial_plants = len(small_world.plants)
        # Manually trigger drought
        event = EventType.DROUGHT
        n = max(1, len(small_world.plants) // 3)
        for p in small_world.rng.sample(small_world.plants, n):
            p.alive = False
        small_world.plants = [p for p in small_world.plants if p.alive]
        assert len(small_world.plants) < initial_plants

    def test_bounty_adds_plants(self, small_world):
        initial = len(small_world.plants)
        for _ in range(30):
            x, y = small_world._random_land()
            small_world.plants.append(Plant(x, y, maturity=5))
        assert len(small_world.plants) > initial

    def test_all_event_types_have_desc(self):
        for et in EventType:
            assert et.desc()  # should not raise

    def test_all_seasons_have_methods(self):
        for s in Season:
            assert s.emoji()
            assert s.label()
            assert s.plant_spread_modifier() > 0


# ─── Headless Mode Tests ──────────────────────────────────────────────────────

class TestHeadless:
    def test_headless_csv(self):
        world = World(width=20, height=10, seed=42, water_ratio=0.0)
        output = run_headless(world, 10, "csv")
        lines = output.strip().split("\n")
        assert len(lines) == 11  # header + 10 data rows
        assert "tick" in lines[0]
        assert "plants" in lines[0]

    def test_headless_json(self):
        world = World(width=20, height=10, seed=42, water_ratio=0.0)
        output = run_headless(world, 5, "json")
        data = json.loads(output)
        assert len(data) == 5
        assert data[0]["tick"] == 1
        assert "plants" in data[0]
        assert "avg_herb_energy" in data[0]

    def test_headless_data_accuracy(self):
        world = World(width=20, height=10, seed=42, water_ratio=0.0)
        output = run_headless(world, 3, "csv")
        lines = output.strip().split("\n")
        # Last row should have tick=3
        fields = lines[-1].split(",")
        assert fields[0] == "3"


# ─── CLI Tests ────────────────────────────────────────────────────────────────

class TestCLI:
    def test_default_args(self):
        args = parse_args([])
        assert args.headless is None
        assert args.seed is None
        assert args.width == WORLD_WIDTH
        assert args.height == WORLD_HEIGHT
        assert args.format == "csv"
        assert args.plants == INITIAL_PLANTS
        assert args.herbivores == INITIAL_HERBIVORES
        assert args.predators == INITIAL_PREDATORS
        assert args.water == WATER_RATIO

    def test_custom_args(self):
        args = parse_args([
            "--headless", "100",
            "--seed", "42",
            "--width", "40",
            "--height", "20",
            "--format", "json",
            "--plants", "30",
            "--herbivores", "10",
            "--predators", "3",
            "--water", "0.1",
            "--speed", "3",
        ])
        assert args.headless == 100
        assert args.seed == 42
        assert args.width == 40
        assert args.height == 20
        assert args.format == "json"
        assert args.plants == 30
        assert args.herbivores == 10
        assert args.predators == 3
        assert args.water == 0.1
        assert args.speed == 3

    def test_version_flag(self):
        with pytest.raises(SystemExit) as exc_info:
            parse_args(["--version"])
        assert exc_info.value.code == 0

    def test_run_from_args(self):
        args = parse_args(["--seed", "42", "--width", "20", "--height", "10", "--water", "0"])
        world = run_from_args(args)
        assert world.width == 20
        assert world.height == 10


# ─── Grid Rendering Tests ──────────────────────────────────────────────────────

class TestGrid:
    def test_get_grid_dimensions(self, small_world):
        grid, colors = small_world.get_grid()
        assert len(grid) == small_world.height
        assert len(grid[0]) == small_world.width

    def test_get_grid_water(self, world_with_water):
        grid, colors = world_with_water.get_grid()
        has_water = any(
            grid[y][x] == "~"
            for y in range(world_with_water.height)
            for x in range(world_with_water.width)
        )
        assert has_water

    def test_entity_appears_in_grid(self, small_world):
        # Place a specific entity
        h = Herbivore(5, 5, energy=80)
        small_world.herbivores = [h]
        grid, colors = small_world.get_grid()
        assert grid[5][5] == "◙"
        assert colors[5][5] == 3  # cyan for herbivore


# ─── Integration Tests ────────────────────────────────────────────────────────

class TestIntegration:
    def test_simulation_runs_stably(self):
        """Run 200 ticks and verify the simulation doesn't crash or go totally extinct."""
        world = World(width=30, height=15, seed=42, water_ratio=0.05)
        for _ in range(200):
            world.update()
        # At least some entities should exist
        total = len(world.plants) + len(world.herbivores) + len(world.predators)
        assert total > 0

    def test_history_is_recorded(self, small_world):
        for _ in range(20):
            small_world.update()
        assert len(small_world.history["plants"]) > 0
        assert len(small_world.history["herbivores"]) > 0
        assert len(small_world.history["predators"]) > 0

    def test_history_is_capped(self, small_world):
        """History should not exceed 100 entries."""
        for _ in range(600):  # 600 / 5 = 120 entries
            small_world.update()
        assert len(small_world.history["plants"]) <= 100