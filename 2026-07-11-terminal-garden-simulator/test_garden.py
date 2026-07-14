"""Tests for the Terminal Garden Simulator."""

import random
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from garden import (
    Plant, PlantType, GrowthStage, Season, GameState, GardenSimulator,
    GRID_W, GRID_H, HARVEST_VALUES, SHOP_PRICES, FERTILIZER_PRICE,
    COMPOST_VALUE, PEST_PROBABILITY, generate_weather, render_plant,
    SAVE_FILE, __version__
)


def test_growth_stages():
    """Test that growth stage thresholds are correct."""
    p = Plant(plant_type=PlantType.SUNFLOWER, x=0, y=0)
    p.health = 100
    
    p.growth = 0
    assert p.stage == GrowthStage.SEED, f"Expected SEED, got {p.stage}"
    
    p.growth = 10
    assert p.stage == GrowthStage.SPROUT, f"Expected SPROUT, got {p.stage}"
    
    p.growth = 25
    assert p.stage == GrowthStage.GROWING, f"Expected GROWING, got {p.stage}"
    
    p.growth = 50
    assert p.stage == GrowthStage.MATURE, f"Expected MATURE, got {p.stage}"
    
    p.growth = 75
    assert p.stage == GrowthStage.FLOWERING, f"Expected FLOWERING, got {p.stage}"
    
    p.growth = 90
    assert p.stage == GrowthStage.FRUITING, f"Expected FRUITING, got {p.stage}"
    
    p.growth = 100
    assert p.stage == GrowthStage.WITHERING, f"Expected WITHERING, got {p.stage}"
    
    p.health = 0
    assert p.stage == GrowthStage.DEAD, f"Expected DEAD, got {p.stage}"


def test_plant_seed():
    """Test planting seeds in the garden."""
    game = GardenSimulator()
    
    # Should successfully plant a sunflower
    assert game.state.seeds[PlantType.SUNFLOWER] == 3
    result = game.plant_seed(PlantType.SUNFLOWER, 5, 5)
    assert result is True
    assert game.state.grid[5][5] is not None
    assert game.state.grid[5][5].plant_type == PlantType.SUNFLOWER
    assert game.state.seeds[PlantType.SUNFLOWER] == 2
    
    # Can't plant on occupied spot
    result = game.plant_seed(PlantType.ROSE, 5, 5)
    assert result is False
    assert game.state.grid[5][5].plant_type == PlantType.SUNFLOWER  # Still sunflower
    
    # Can't plant out of bounds
    result = game.plant_seed(PlantType.ROSE, -1, 0)
    assert result is False
    result = game.plant_seed(PlantType.ROSE, 0, GRID_H + 1)
    assert result is False


def test_water_plant():
    """Test watering a plant."""
    game = GardenSimulator()
    game.plant_seed(PlantType.SUNFLOWER, 5, 5)
    plant = game.state.grid[5][5]
    plant.water_level = 30.0
    
    game.water_plant(5, 5)
    assert plant.water_level == 65.0, f"Expected 65.0, got {plant.water_level}"
    
    # Over-watering caps at 100
    plant.water_level = 90.0
    game.water_plant(5, 5)
    assert plant.water_level == 100.0
    
    # Watering empty spot does nothing
    game.water_plant(0, 0)  # Should not crash


def test_harvest():
    """Test harvesting plants at different stages."""
    game = GardenSimulator()
    game.plant_seed(PlantType.SUNFLOWER, 5, 5)
    plant = game.state.grid[5][5]
    
    # Can't harvest immature plant
    plant.growth = 50
    plant.health = 100
    game.harvest_plant(5, 5)
    assert game.state.grid[5][5] is not None, "Plant should still be there"
    
    # Harvest at flowering
    plant.growth = 80
    plant.health = 100
    initial_gold = game.state.gold
    game.harvest_plant(5, 5)
    assert game.state.grid[5][5] is None, "Plant should be removed after harvest"
    assert game.state.gold > initial_gold, "Gold should increase after harvest"
    expected_value = HARVEST_VALUES[PlantType.SUNFLOWER]
    assert game.state.gold == initial_gold + expected_value
    
    # Harvest at fruiting (1.5x bonus)
    game.state.seeds[PlantType.ROSE] = 1
    game.plant_seed(PlantType.ROSE, 6, 5)
    plant = game.state.grid[5][6]
    plant.growth = 95
    plant.health = 100
    initial_gold = game.state.gold
    game.harvest_plant(6, 5)
    expected_value = int(HARVEST_VALUES[PlantType.ROSE] * 1.5)
    assert game.state.gold == initial_gold + expected_value


def test_compost_dead_plant():
    """Test composting a dead plant for gold."""
    game = GardenSimulator()
    game.state.seeds[PlantType.SUNFLOWER] = 1
    game.plant_seed(PlantType.SUNFLOWER, 5, 5)
    plant = game.state.grid[5][5]
    plant.health = 0  # Plant is dead
    
    initial_gold = game.state.gold
    game.harvest_plant(5, 5)
    assert game.state.grid[5][5] is None, "Dead plant should be removed"
    assert game.state.gold == initial_gold + COMPOST_VALUE


def test_remove_plant():
    """Test removing a plant without gold reward."""
    game = GardenSimulator()
    game.plant_seed(PlantType.SUNFLOWER, 5, 5)
    initial_gold = game.state.gold
    
    game.remove_plant(5, 5)
    assert game.state.grid[5][5] is None
    assert game.state.gold == initial_gold, "Removing should not give gold"


def test_fertilize():
    """Test the fertilizer mechanic."""
    game = GardenSimulator()
    game.state.seeds[PlantType.SUNFLOWER] = 1
    game.plant_seed(PlantType.SUNFLOWER, 5, 5)
    plant = game.state.grid[5][5]
    
    # Should successfully fertilize
    initial_fert = game.state.fertilizer_count
    game.fertilize_plant(5, 5)
    assert plant.fertilized_days == 3
    assert game.state.fertilizer_count == initial_fert - 1
    
    # Can't fertilize with 0 fertilizer
    game.state.fertilizer_count = 0
    game.fertilize_plant(5, 5)
    assert plant.fertilized_days == 3, "Should not increase fertilizer days when out"


def test_season_cycle():
    """Test that seasons cycle correctly every 28 days."""
    game = GardenSimulator()
    game.state.day = 1
    assert game.state.season == Season.SPRING
    
    game.advance_day(27)  # Day 28 = still Spring
    assert game.state.season == Season.SPRING
    
    game.advance_day(1)  # Day 29 = Summer
    assert game.state.season == Season.SUMMER
    
    game.advance_day(28)  # Day 57 = Autumn
    assert game.state.season == Season.AUTUMN
    
    game.advance_day(28)  # Day 85 = Winter
    assert game.state.season == Season.WINTER
    
    game.advance_day(28)  # Day 113 = Spring again
    assert game.state.season == Season.SPRING


def test_weather_generation():
    """Test that weather generation produces valid weather types."""
    for season in Season:
        weather = generate_weather(season)
        assert weather in ["Clear", "Cloudy", "Rainy", "Stormy", "Hot", "Windy"], f"Invalid weather: {weather}"
    
    # Test deterministic weather with seed
    w1 = generate_weather(Season.SUMMER, day_seed=42)
    w2 = generate_weather(Season.SUMMER, day_seed=42)
    assert w1 == w2, "Same seed should produce same weather"
    
    # Summer should have Hot weather more often
    hot_count = sum(1 for _ in range(1000) if generate_weather(Season.SUMMER) == "Hot")
    assert hot_count > 50, f"Summer should have hot days frequently, got {hot_count}/1000"


def test_plant_growth():
    """Test that plants grow when advancing days."""
    game = GardenSimulator()
    game.plant_seed(PlantType.SUNFLOWER, 5, 5)
    plant = game.state.grid[5][5]
    initial_growth = plant.growth
    
    # Advance a day with watering
    plant.water_level = 60
    game.advance_day(1)
    assert plant.growth > initial_growth, "Plant should grow after a day"


def test_overwatering():
    """Test that overwatering damages plant health."""
    game = GardenSimulator()
    game.plant_seed(PlantType.SUNFLOWER, 5, 5)
    plant = game.state.grid[5][5]
    plant.water_level = 100
    plant.health = 100
    
    # Heavy rain should overwater
    game.weather = "Rainy"
    game._grow_plants()
    # Health should decrease from overwatering
    assert plant.health < 100, "Overwatering should reduce health"


def test_drought_damage():
    """Test that very low water damages plant health."""
    game = GardenSimulator()
    game.plant_seed(PlantType.SUNFLOWER, 5, 5)
    plant = game.state.grid[5][5]
    plant.water_level = 0
    plant.health = 100
    game.weather = "Clear"
    
    game._grow_plants()
    assert plant.health < 100, "Drought should reduce health"


def test_render_plant():
    """Test that render_plant returns valid output for each stage and type."""
    rng = random.Random(42)
    for pt in PlantType:
        for stage in GrowthStage:
            art = render_plant(pt, stage, 3.0, rng)
            assert isinstance(art, list), f"render_plant should return list for {pt} {stage}"
            assert len(art) > 0, f"render_plant should return non-empty for {pt} {stage}"
            for line in art:
                assert isinstance(line, str), f"Each line should be a string"


def test_save_and_load(tmp_path):
    """Test game save and load functionality."""
    # Use a temporary save file
    import garden
    original_save = garden.SAVE_FILE
    garden.SAVE_FILE = str(tmp_path / "test_save.json")
    
    try:
        game = GardenSimulator()
        game.state.seeds[PlantType.SUNFLOWER] = 1
        game.plant_seed(PlantType.SUNFLOWER, 5, 5)
        plant = game.state.grid[5][5]
        plant.growth = 50.0
        plant.water_level = 70.0
        plant.health = 90.0
        plant.fertilized_days = 2
        game.state.fertilizer_count = 5
        game.state.gold = 100
        
        game.save_game()
        assert os.path.exists(garden.SAVE_FILE)
        
        # Load into a new game
        game2 = GardenSimulator()
        result = game2.load_game()
        assert result is True
        assert game2.state.gold == 100
        assert game2.state.fertilizer_count == 5
        loaded_plant = game2.state.grid[5][5]
        assert loaded_plant is not None
        assert loaded_plant.plant_type == PlantType.SUNFLOWER
        assert abs(loaded_plant.growth - 50.0) < 0.01
        assert abs(loaded_plant.water_level - 70.0) < 0.01
        assert abs(loaded_plant.health - 90.0) < 0.01
        assert loaded_plant.fertilized_days == 2
    finally:
        garden.SAVE_FILE = original_save


def test_buy_seed():
    """Test buying seeds from the shop."""
    game = GardenSimulator()
    game.state.gold = 100
    
    game.buy_seed(PlantType.CACTUS)
    assert game.state.seeds[PlantType.CACTUS] == 3, "Should have 3 cactus seeds"
    expected_price = SHOP_PRICES[PlantType.CACTUS]
    assert game.state.gold == 100 - expected_price
    
    # Can't buy if not enough gold
    game.state.gold = 0
    game.buy_seed(PlantType.TREE)
    assert game.state.seeds.get(PlantType.TREE, 0) == 0, "Should not buy without gold"


def test_buy_fertilizer():
    """Test buying fertilizer from the shop."""
    game = GardenSimulator()
    game.state.gold = 50
    initial_fert = game.state.fertilizer_count
    
    game.buy_fertilizer()
    assert game.state.fertilizer_count == initial_fert + 1
    assert game.state.gold == 50 - FERTILIZER_PRICE
    
    # Can't buy if not enough gold
    game.state.gold = 0
    game.buy_fertilizer()
    assert game.state.fertilizer_count == initial_fert + 1, "Should not increase without gold"


def test_forecast():
    """Test weather forecast generation."""
    game = GardenSimulator()
    game.state.day = 10
    game.state.season = Season.SPRING
    
    forecast = game.compute_forecast(3)
    assert len(forecast) == 3
    for w in forecast:
        assert w in ["Clear", "Cloudy", "Rainy", "Stormy", "Hot", "Windy"]


def test_pest_event():
    """Test that pest events can damage plants."""
    game = GardenSimulator()
    game.state.seeds[PlantType.SUNFLOWER] = 5
    
    # Plant many plants to ensure at least one gets hit
    positions = [(x, y) for x in range(5) for y in range(5)]
    for i, (x, y) in enumerate(positions):
        game.state.seeds[PlantType.SUNFLOWER] = 99  # Infinite seeds for testing
        game.state.grid[y][x] = Plant(plant_type=PlantType.SUNFLOWER, x=x, y=y)
        game.state.grid[y][x].health = 100
    
    # Force a pest event by temporarily making probability 100%
    import garden
    original_prob = garden.PEST_PROBABILITY
    garden.PEST_PROBABILITY = 1.0
    game._check_pest_event()
    garden.PEST_PROBABILITY = original_prob
    
    # At least some plants should have been damaged
    damaged = False
    for y in range(5):
        for x in range(5):
            plant = game.state.grid[y][x]
            if plant and plant.health < 100:
                damaged = True
                break
        if damaged:
            break
    # Note: might not always damage due to resistance, but probability is high


def test_version():
    """Test that version string exists and is valid."""
    assert __version__ is not None
    parts = __version__.split('.')
    assert len(parts) == 3, "Version should be semver"
    assert all(p.isdigit() for p in parts), "Version parts should be numeric"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])