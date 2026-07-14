#!/usr/bin/env python3
"""
Terminal Procedural Garden Simulator
Plant, grow, water, and harvest procedural ASCII plants through changing seasons.

Features:
  - 8 plant types with unique growth patterns, water needs, and season preferences
  - 4 seasons with dynamic weather (Clear, Cloudy, Rainy, Stormy, Hot, Windy)
  - Economy system: plant → grow → harvest → buy seeds → repeat
  - Fertilizer mechanic: boost plant growth with purchased fertilizer
  - Weather forecast: peek at upcoming days' weather
  - Pest events: random insects can damage your plants
  - Composting: clear dead plants to recover some gold
  - Save/Load: game state persists between sessions

Usage:
  python3 garden.py              # Interactive mode
  python3 garden.py --demo       # Demo/preview mode
  python3 garden.py --stats      # Show saved game statistics
  python3 garden.py --version    # Show version info
"""

import random
import time
import sys
import os
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple

__version__ = "1.1.0"

# --- Constants ---
GRID_W = 40
GRID_H = 16
SAVE_FILE = os.path.expanduser("~/.garden_save.json")

# --- Enums ---
class Season(Enum):
    SPRING = "Spring"
    SUMMER = "Summer"
    AUTUMN = "Autumn"
    WINTER = "Winter"

class PlantType(Enum):
    SUNFLOWER = "Sunflower"
    ROSE = "Rose"
    CACTUS = "Cactus"
    MUSHROOM = "Mushroom"
    FERN = "Fern"
    TREE = "Oak Tree"
    TULIP = "Tulip"
    VINE = "Vine"

class GrowthStage(Enum):
    SEED = 0
    SPROUT = 1
    GROWING = 2
    MATURE = 3
    FLOWERING = 4
    FRUITING = 5
    WITHERING = 6
    DEAD = 7

# --- Plant Data ---
PLANT_DATA = {
    PlantType.SUNFLOWER: {
        "grow_rate": 1.2,
        "water_need": 3,
        "season_bonus": {Season.SUMMER: 1.5, Season.SPRING: 1.1},
        "season_penalty": {Season.WINTER: 0.3, Season.AUTUMN: 0.6},
        "colors": ["\033[93m", "\033[33m"],  # yellow
        "flower_color": "\033[93m",
        "max_height": 6,
    },
    PlantType.ROSE: {
        "grow_rate": 0.9,
        "water_need": 4,
        "season_bonus": {Season.SPRING: 1.4, Season.SUMMER: 1.2},
        "season_penalty": {Season.WINTER: 0.2},
        "colors": ["\033[91m", "\033[31m"],  # red
        "flower_color": "\033[91m",
        "max_height": 4,
    },
    PlantType.CACTUS: {
        "grow_rate": 0.5,
        "water_need": 1,
        "season_bonus": {Season.SUMMER: 1.3},
        "season_penalty": {Season.WINTER: 0.5},
        "colors": ["\033[92m", "\033[32m"],  # green
        "flower_color": "\033[95m",
        "max_height": 5,
    },
    PlantType.MUSHROOM: {
        "grow_rate": 1.5,
        "water_need": 5,
        "season_bonus": {Season.AUTUMN: 1.6, Season.SPRING: 1.2},
        "season_penalty": {Season.SUMMER: 0.5, Season.WINTER: 0.3},
        "colors": ["\033[97m", "\033[37m"],  # white
        "flower_color": "\033[91m",
        "max_height": 3,
    },
    PlantType.FERN: {
        "grow_rate": 1.0,
        "water_need": 3,
        "season_bonus": {Season.SPRING: 1.3, Season.SUMMER: 1.1},
        "season_penalty": {Season.WINTER: 0.4, Season.AUTUMN: 0.7},
        "colors": ["\033[92m", "\033[32m"],
        "flower_color": "\033[92m",
        "max_height": 5,
    },
    PlantType.TREE: {
        "grow_rate": 0.4,
        "water_need": 2,
        "season_bonus": {Season.SPRING: 1.3, Season.SUMMER: 1.1},
        "season_penalty": {Season.WINTER: 0.3, Season.AUTUMN: 0.6},
        "colors": ["\033[33m", "\033[92m"],  # brown trunk, green canopy
        "flower_color": "\033[92m",
        "max_height": 8,
    },
    PlantType.TULIP: {
        "grow_rate": 1.1,
        "water_need": 3,
        "season_bonus": {Season.SPRING: 1.5},
        "season_penalty": {Season.WINTER: 0.2, Season.AUTUMN: 0.5},
        "colors": ["\033[95m", "\033[35m"],  # purple/pink
        "flower_color": "\033[95m",
        "max_height": 3,
    },
    PlantType.VINE: {
        "grow_rate": 1.3,
        "water_need": 3,
        "season_bonus": {Season.SUMMER: 1.4, Season.SPRING: 1.2},
        "season_penalty": {Season.WINTER: 0.2},
        "colors": ["\033[92m", "\033[32m"],
        "flower_color": "\033[95m",
        "max_height": 7,
    },
}

# --- ASCII Art for plants ---
SEED_ART = ["·"]
SPROUT_ART = {
    PlantType.SUNFLOWER: [",,", ",ₒ"],
    PlantType.ROSE: ["..", ",,"],
    PlantType.CACTUS: ["..", ",|"],
    PlantType.MUSHROOM: ["..", ",,"],
    PlantType.FERN: ["~", "ƒ"],
    PlantType.TREE: ["..", ",,"],
    PlantType.TULIP: ["..", ",,"],
    PlantType.VINE: ["~", ",/"],
}

def render_plant(plant_type: PlantType, stage: GrowthStage, height: float, rng: random.Random) -> List[str]:
    """Render a plant as a list of strings (bottom to top)."""
    data = PLANT_DATA[plant_type]
    c = data["flower_color"]
    g = data["colors"][0]
    brown = "\033[33m"
    reset = "\033[0m"
    
    if stage == GrowthStage.SEED:
        return [f"{g}·{reset}"]
    
    if stage == GrowthStage.SPROUT:
        arts = SPROUT_ART.get(plant_type, [",,", ",,"])
        return [f"{g}{arts[1]}{reset}", f"{g}{arts[0]}{reset}"]
    
    h = max(2, int(height))
    lines = []
    
    if plant_type == PlantType.SUNFLOWER:
        # Stem
        for i in range(h - 1):
            sway = rng.choice(["|", "/", "\\"])
            lines.append(f"{g}{sway}{reset}")
        # Flower head
        lines.append(f"{c}⊛{reset}")
        
    elif plant_type == PlantType.ROSE:
        for i in range(h - 1):
            lines.append(f"{g}|{reset}")
        if stage in (GrowthStage.FLOWERING, GrowthStage.FRUITING):
            lines.append(f"{c}@{reset}")
        else:
            lines.append(f"{g}*{reset}")
            
    elif plant_type == PlantType.CACTUS:
        for i in range(h):
            if i == h // 2:
                lines.append(f"{g}╠╣{reset}")
            elif i == h // 2 + 1:
                lines.append(f"{g}╠╣{reset}")
            else:
                lines.append(f"{g}║{reset}")
        if stage in (GrowthStage.FLOWERING, GrowthStage.FRUITING):
            lines[-1] = f"{c}✿{reset}"
            
    elif plant_type == PlantType.MUSHROOM:
        # Stem
        for i in range(h - 1):
            lines.append(f"{g}║{reset}")
        # Cap
        if stage in (GrowthStage.FLOWERING, GrowthStage.FRUITING):
            cap_w = min(h + 2, 7)
            cap = f"{c}{'~' * cap_w}{reset}"
            cap_inner = f"{c}{' ' * cap_w}{reset}"
            lines = [cap, cap_inner] + lines
        else:
            lines.append(f"{g}☂{reset}")
            
    elif plant_type == PlantType.FERN:
        for i in range(h):
            frond = rng.choice(["⌿", "∤", "∥", "蕨"])
            if stage in (GrowthStage.FLOWERING, GrowthStage.FRUITING):
                frond = f"{c}{frond}{reset}"
            else:
                frond = f"{g}{frond}{reset}"
            lines.append(frond)
            
    elif plant_type == PlantType.TREE:
        # Trunk
        trunk_h = max(2, h // 3)
        canopy_h = h - trunk_h
        for i in range(trunk_h):
            lines.append(f"{brown}║{reset}")
        # Canopy
        for i in range(canopy_h):
            width = canopy_h - i
            if stage in (GrowthStage.FLOWERING,):
                line = f"{c}{'*' * width}{reset}"
            elif stage == GrowthStage.FRUITING:
                line = f"{g}{'*' * width}{reset}"
                # Add some fruits
                chars = list(line)
                for j in range(1, len(chars) - 1):
                    if rng.random() < 0.3 and chars[j] == '*':
                        chars[j] = f"{c}●{reset}"
                line = ''.join(chars)
            else:
                line = f"{g}{'*' * width}{reset}"
            lines.append(line)
            
    elif plant_type == PlantType.TULIP:
        for i in range(h - 1):
            lines.append(f"{g}|{reset}")
        if stage in (GrowthStage.FLOWERING, GrowthStage.FRUITING):
            lines.append(f"{c}❀{reset}")
        else:
            lines.append(f"{g}↑{reset}")
            
    elif plant_type == PlantType.VINE:
        for i in range(h):
            v = rng.choice(["/", "\\", "|", "⌇"])
            lines.append(f"{g}{v}{reset}")
        if stage in (GrowthStage.FLOWERING, GrowthStage.FRUITING):
            lines[-1] = f"{c}✿{reset}"
    
    # Withering overlay
    if stage == GrowthStage.WITHERING:
        withered = []
        for line in lines:
            w = line.replace("\033[92m", "\033[33m").replace("\033[93m", "\033[33m").replace("\033[91m", "\033[2;31m")
            withered.append(w)
        return withered
    
    if stage == GrowthStage.DEAD:
        return [f"\033[2;37m✗{reset}" for _ in range(1)]
    
    return lines


@dataclass
class Plant:
    """Represents a single plant in the garden grid."""
    plant_type: PlantType
    x: int
    y: int
    growth: float = 0.0  # 0-100
    water_level: float = 50.0  # 0-100
    health: float = 100.0  # 0-100
    age_days: int = 0
    rng_seed: int = field(default_factory=lambda: random.randint(0, 999999))
    fertilized_days: int = 0  # Days of fertilizer boost remaining
    
    @property
    def stage(self) -> GrowthStage:
        if self.health <= 0:
            return GrowthStage.DEAD
        if self.growth < 10:
            return GrowthStage.SEED
        if self.growth < 25:
            return GrowthStage.SPROUT
        if self.growth < 50:
            return GrowthStage.GROWING
        if self.growth < 75:
            return GrowthStage.MATURE
        if self.growth < 90:
            return GrowthStage.FLOWERING
        if self.growth < 100:
            return GrowthStage.FRUITING
        return GrowthStage.WITHERING
    
    @property
    def height(self) -> float:
        data = PLANT_DATA[self.plant_type]
        return max(1, (self.growth / 100.0) * data["max_height"])
    
    @property
    def rng(self) -> random.Random:
        return random.Random(self.rng_seed + self.age_days)


@dataclass
class GameState:
    """Complete game state including grid, inventory, and position."""
    grid: List[List[Optional[Plant]]] = field(default_factory=lambda: [[None]*GRID_W for _ in range(GRID_H)])
    season: Season = Season.SPRING
    day: int = 1
    gold: int = 50
    seeds: Dict[PlantType, int] = field(default_factory=lambda: {
        PlantType.SUNFLOWER: 3,
        PlantType.ROSE: 2,
        PlantType.TULIP: 2,
    })
    total_harvested: int = 0
    total_planted: int = 0
    cursor_x: int = 5
    cursor_y: int = 5
    message: str = ""
    message_timer: int = 0
    fertilizer_count: int = 3  # Starting fertilizer


SEASON_ORDER = [Season.SPRING, Season.SUMMER, Season.AUTUMN, Season.WINTER]
SEASON_COLORS = {
    Season.SPRING: "\033[92m",   # green
    Season.SUMMER: "\033[93m",   # yellow
    Season.AUTUMN: "\033[33m",   # orange/brown
    Season.WINTER: "\033[96m",   # cyan
}
SEASON_EMOJI = {
    Season.SPRING: "🌱",
    Season.SUMMER: "☀️",
    Season.AUTUMN: "🍂",
    Season.WINTER: "❄️",
}

WEATHER_TYPES = ["Clear", "Cloudy", "Rainy", "Stormy", "Hot", "Windy"]
WEATHER_RAIN = {"Rainy": 1.0, "Stormy": 0.8, "Cloudy": 0.2}
WEATHER_EMOJI = {
    "Clear": "☀️",
    "Cloudy": "☁️",
    "Rainy": "🌧️",
    "Stormy": "⛈️",
    "Hot": "🔥",
    "Windy": "💨",
}

SHOP_PRICES = {
    PlantType.SUNFLOWER: 10,
    PlantType.ROSE: 15,
    PlantType.CACTUS: 20,
    PlantType.MUSHROOM: 12,
    PlantType.FERN: 10,
    PlantType.TREE: 25,
    PlantType.TULIP: 12,
    PlantType.VINE: 15,
}

FERTILIZER_PRICE = 8  # Cost per fertilizer unit in shop

HARVEST_VALUES = {
    PlantType.SUNFLOWER: 25,
    PlantType.ROSE: 35,
    PlantType.CACTUS: 30,
    PlantType.MUSHROOM: 20,
    PlantType.FERN: 15,
    PlantType.TREE: 50,
    PlantType.TULIP: 25,
    PlantType.VINE: 30,
}

# Compost value: gold recovered when clearing a dead plant
COMPOST_VALUE = 3

# Pest event probability per day
PEST_PROBABILITY = 0.12  # 12% chance of a pest event each day


def generate_weather(season: Season, day_seed: int = None) -> str:
    """Generate a random weather type based on the current season."""
    weights = [4, 3, 2, 1, 1, 1]  # Clear, Cloudy, Rainy, Stormy, Hot, Windy
    if season == Season.SUMMER:
        weights[4] = 3  # more hot days
    elif season == Season.WINTER:
        weights = [2, 3, 3, 2, 0, 2]
    elif season == Season.SPRING:
        weights[2] = 4  # more rain
    elif season == Season.AUTUMN:
        weights[1] = 4  # more cloudy
        weights[2] = 3  # more rain (mushroom season)
    
    if day_seed is not None:
        rng = random.Random(day_seed)
        return rng.choices(WEATHER_TYPES, weights=weights, k=1)[0]
    return random.choices(WEATHER_TYPES, weights=weights, k=1)[0]


class GardenSimulator:
    """Main garden simulator class handling game logic and rendering."""
    
    def __init__(self):
        self.state = GameState()
        self.weather = "Clear"
        self.forecast: List[str] = []  # Weather forecast for upcoming days
        self.running = True
        self.mode = "normal"  # normal, plant_select, shop, forecast
        self.selected_plant_idx = 0
        self.available_seeds_list: List[Tuple[PlantType, int]] = []
        self.shop_page = 0
        self.pest_alert = ""  # Message about current pest event
        self.pest_alert_timer = 0
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def get_season_day(self) -> int:
        """Get the current day within the season (1-28)."""
        return ((self.state.day - 1) % 28) + 1
    
    def compute_forecast(self, days: int = 3) -> List[str]:
        """Compute weather forecast for the next `days` days."""
        forecast = []
        for i in range(1, days + 1):
            future_day = self.state.day + i
            future_season_idx = ((future_day - 1) // 28) % 4
            future_season = SEASON_ORDER[future_season_idx]
            future_weather = generate_weather(future_season, day_seed=future_day * 7919)
            forecast.append(future_weather)
        return forecast
    
    def advance_day(self, days=1):
        """Advance the game by the specified number of days."""
        for _ in range(days):
            self.state.day += 1
            # Determine season
            season_idx = ((self.state.day - 1) // 28) % 4
            self.state.season = SEASON_ORDER[season_idx]
            # Random weather
            self.weather = generate_weather(self.state.season)
            # Check for pest event
            self._check_pest_event()
            # Grow plants
            self._grow_plants()
        # Update forecast
        self.forecast = self.compute_forecast(3)
    
    def _check_pest_event(self):
        """Randomly trigger a pest event that can damage plants."""
        self.pest_alert = ""
        self.pest_alert_timer = 0
        if random.random() < PEST_PROBABILITY:
            # Pest event! Determine severity
            pest_types = ["aphids", "caterpillars", "slugs", "beetles", "mites"]
            pest = random.choice(pest_types)
            affected = []
            for row in self.state.grid:
                for plant in row:
                    if plant and plant.stage not in (GrowthStage.DEAD,):
                        # Some plants resist pests better
                        resistance = 1.0
                        if plant.plant_type == PlantType.CACTUS:
                            resistance = 0.3  # Cacti are tough
                        elif plant.plant_type == PlantType.FERN:
                            resistance = 0.7
                        if random.random() < (0.4 * resistance):
                            damage = random.randint(3, 12)
                            plant.health -= damage
                            plant.health = max(0, plant.health)
                            affected.append(plant.plant_type.value)
            if affected:
                self.pest_alert = f"🐛 {pest.title()} attacked {len(affected)} plant(s)!"
                self.pest_alert_timer = 40
    
    def _grow_plants(self):
        """Process growth for all plants for one day."""
        rain_factor = WEATHER_RAIN.get(self.weather, 0.0)
        for row in self.state.grid:
            for plant in row:
                if plant is None or plant.stage == GrowthStage.DEAD:
                    continue
                data = PLANT_DATA[plant.plant_type]
                plant.age_days += 1
                # Water from rain
                plant.water_level += rain_factor * 30
                plant.water_level = min(100, plant.water_level)
                # Natural water loss
                plant.water_level -= 2
                plant.water_level = max(0, plant.water_level)
                # Growth calculation
                grow_rate = data["grow_rate"]
                # Determine seasonal multiplier
                if self.state.season in data["season_bonus"]:
                    effective = data["season_bonus"][self.state.season]
                elif self.state.season in data["season_penalty"]:
                    effective = data["season_penalty"][self.state.season]
                else:
                    effective = 1.0
                # Water factor
                water_need = data["water_need"]
                if plant.water_level >= water_need * 10:
                    water_mult = 1.0
                elif plant.water_level >= water_need * 5:
                    water_mult = 0.6
                else:
                    water_mult = 0.2
                # Fertilizer boost
                fert_mult = 1.0
                if plant.fertilized_days > 0:
                    fert_mult = 1.5
                    plant.fertilized_days -= 1
                # Health effects
                if plant.water_level <= 5:
                    plant.health -= 8
                elif plant.water_level >= 95:
                    plant.health -= 2  # overwatering
                else:
                    plant.health = min(100, plant.health + 1)
                # Storm damage
                if self.weather == "Stormy":
                    if random.random() < 0.15:
                        plant.health -= random.randint(5, 20)
                # Hot weather increases water loss
                if self.weather == "Hot":
                    plant.water_level -= 5
                plant.water_level = max(0, plant.water_level)
                # Apply growth
                plant.growth += grow_rate * effective * water_mult * fert_mult
                plant.growth = min(110, plant.growth)  # Can go slightly past 100
                if plant.growth >= 100:
                    plant.growth -= 0.3  # Slow withering
                plant.health = max(0, min(100, plant.health))
                if plant.health <= 0:
                    plant.growth = max(plant.growth, 0)
    
    def plant_seed(self, plant_type: PlantType, x: int, y: int) -> bool:
        """Plant a seed at the given position. Returns True on success."""
        if x < 0 or x >= GRID_W or y < 0 or y >= GRID_H:
            return False
        if self.state.grid[y][x] is not None:
            self.state.message = "That spot is occupied!"
            self.state.message_timer = 30
            return False
        if self.state.seeds.get(plant_type, 0) <= 0:
            self.state.message = f"No {plant_type.value} seeds left!"
            self.state.message_timer = 30
            return False
        self.state.seeds[plant_type] -= 1
        self.state.grid[y][x] = Plant(plant_type=plant_type, x=x, y=y)
        self.state.total_planted += 1
        self.state.message = f"Planted {plant_type.value}!"
        self.state.message_timer = 30
        return True
    
    def water_plant(self, x: int, y: int):
        """Water the plant at the given position."""
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            plant = self.state.grid[y][x]
            if plant and plant.stage not in (GrowthStage.DEAD,):
                plant.water_level = min(100, plant.water_level + 35)
                self.state.message = f"Watered {plant.plant_type.value}! 💧"
                self.state.message_timer = 20
    
    def fertilize_plant(self, x: int, y: int):
        """Apply fertilizer to the plant at the given position."""
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            return
        plant = self.state.grid[y][x]
        if plant is None:
            self.state.message = "Nothing here to fertilize!"
            self.state.message_timer = 20
            return
        if plant.stage == GrowthStage.DEAD:
            self.state.message = "Dead plants can't be fertilized!"
            self.state.message_timer = 20
            return
        if self.state.fertilizer_count <= 0:
            self.state.message = "No fertilizer! Buy some at the shop (F key)."
            self.state.message_timer = 30
            return
        self.state.fertilizer_count -= 1
        plant.fertilized_days = 3  # Boost for 3 days
        self.state.message = f"Fertilized {plant.plant_type.value}! (3 days boost) ✨"
        self.state.message_timer = 25
    
    def harvest_plant(self, x: int, y: int):
        """Harvest or compost the plant at the given position."""
        if not (0 <= x < GRID_W and 0 <= y < GRID_H):
            return
        plant = self.state.grid[y][x]
        if plant is None:
            return
        if plant.stage in (GrowthStage.FLOWERING, GrowthStage.FRUITING):
            value = HARVEST_VALUES.get(plant.plant_type, 15)
            # Bonus for fruiting stage
            if plant.stage == GrowthStage.FRUITING:
                value = int(value * 1.5)
            # Fertilized plants give bonus gold
            if plant.fertilized_days > 0:
                value = int(value * 1.2)
            self.state.gold += value
            self.state.total_harvested += 1
            # Chance to get seeds back
            if random.random() < 0.6:
                self.state.seeds[plant.plant_type] = self.state.seeds.get(plant.plant_type, 0) + 1
                self.state.message = f"Harvested {plant.plant_type.value}! +{value}g (+1 seed) 🪙"
            else:
                self.state.message = f"Harvested {plant.plant_type.value}! +{value}g 🪙"
            self.state.message_timer = 30
            self.state.grid[y][x] = None
        elif plant.stage == GrowthStage.DEAD:
            # Composting: recover some gold from dead plants
            self.state.gold += COMPOST_VALUE
            self.state.grid[y][x] = None
            self.state.message = f"Composted {plant.plant_type.value}. +{COMPOST_VALUE}g ♻️"
            self.state.message_timer = 20
        else:
            self.state.message = f"{plant.plant_type.value} not ready to harvest yet!"
            self.state.message_timer = 30
    
    def remove_plant(self, x: int, y: int):
        """Remove a plant at the given position (no gold reward)."""
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            plant = self.state.grid[y][x]
            if plant:
                self.state.grid[y][x] = None
                self.state.message = f"Removed {plant.plant_type.value}."
                self.state.message_timer = 20
    
    def buy_seed(self, plant_type: PlantType):
        """Buy 3 seeds of the given plant type."""
        price = SHOP_PRICES.get(plant_type, 15)
        if self.state.gold >= price:
            self.state.gold -= price
            self.state.seeds[plant_type] = self.state.seeds.get(plant_type, 0) + 3
            self.state.message = f"Bought 3 {plant_type.value} seeds! -{price}g"
            self.state.message_timer = 30
        else:
            self.state.message = f"Not enough gold! Need {price}g."
            self.state.message_timer = 30
    
    def buy_fertilizer(self):
        """Buy one unit of fertilizer."""
        if self.state.gold >= FERTILIZER_PRICE:
            self.state.gold -= FERTILIZER_PRICE
            self.state.fertilizer_count += 1
            self.state.message = f"Bought fertilizer! -{FERTILIZER_PRICE}g"
            self.state.message_timer = 30
        else:
            self.state.message = f"Not enough gold! Need {FERTILIZER_PRICE}g."
            self.state.message_timer = 30
    
    def render_garden(self) -> str:
        """Render the main garden view as a string."""
        lines = []
        sc = SEASON_COLORS[self.state.season]
        reset = "\033[0m"
        
        # Header
        season_day = self.get_season_day()
        emoji = SEASON_EMOJI[self.state.season]
        weather_emoji = WEATHER_EMOJI.get(self.weather, "")
        header = f"{sc}{emoji} {self.state.season.value} Day {season_day}{reset}  |  Day {self.state.day}  |  {weather_emoji} {self.weather}  |  💰 {self.state.gold}g  |  ✨ Fert: {self.state.fertilizer_count}"
        lines.append(header)
        
        # Seed inventory
        seed_strs = []
        for pt, count in self.state.seeds.items():
            if count > 0:
                seed_strs.append(f"{pt.value}:{count}")
        seed_line = "Seeds: " + ", ".join(seed_strs) if seed_strs else "Seeds: none"
        lines.append(seed_line)
        lines.append("")
        
        # Garden grid
        # Top border
        lines.append("  " + "─" * GRID_W)
        
        for y in range(GRID_H):
            row_str = " │"
            for x in range(GRID_W):
                plant = self.state.grid[y][x]
                if x == self.state.cursor_x and y == self.state.cursor_y:
                    # Cursor position
                    if plant:
                        stage = plant.stage
                        art = render_plant(plant.plant_type, stage, plant.height, plant.rng)
                        cell = art[-1] if art else "?"
                        # Highlight with inverse for cursor
                        cell = f"\033[7m{cell}{reset}"
                        row_str += cell
                    else:
                        row_str += "\033[7m·\033[0m"
                else:
                    if plant:
                        art = render_plant(plant.plant_type, plant.stage, plant.height, plant.rng)
                        cell = art[-1] if art else " "
                        row_str += cell
                    else:
                        # Empty ground
                        ground_chars = [".", ",", ".", " ", ".", ".", " "]
                        rng_ground = random.Random(x * 100 + y)
                        row_str += rng_ground.choice(ground_chars)
            row_str += "│"
            lines.append(row_str)
        
        lines.append("  " + "─" * GRID_W)
        
        # Plant detail at cursor
        cx, cy = self.state.cursor_x, self.state.cursor_y
        plant = self.state.grid[cy][cx] if 0 <= cy < GRID_H and 0 <= cx < GRID_W else None
        if plant:
            fert_str = f" \033[93m✨ Fert:{plant.fertilized_days}d\033[0m" if plant.fertilized_days > 0 else ""
            detail = f"  {plant.plant_type.value} | Stage: {plant.stage.name} | Growth: {plant.growth:.0f}% | Water: {plant.water_level:.0f}% | Health: {plant.health:.0f}%{fert_str}"
        else:
            detail = f"  Empty plot ({cx},{cy})"
        lines.append(detail)
        
        # Pest alert
        if self.pest_alert_timer > 0:
            lines.append(f"\033[91m  {self.pest_alert}\033[0m")
            self.pest_alert_timer -= 1
        
        # Message
        if self.state.message_timer > 0:
            lines.append(f"\033[93m  {self.state.message}{reset}")
            self.state.message_timer -= 1
        
        return "\n".join(lines)
    
    def render_plant_detail(self, plant: Plant) -> str:
        """Render a larger view of a single plant."""
        art = render_plant(plant.plant_type, plant.stage, plant.height, plant.rng)
        result_lines = []
        for line in art:
            result_lines.append(f"  {line}")
        return "\n".join(result_lines)
    
    def render_shop(self) -> str:
        """Render the seed shop overlay."""
        lines = []
        lines.append("\033[93m╔══════════════════════════════════════╗")
        lines.append("║        🏪 SEED SHOP 🏪               ║")
        lines.append(f"║        Gold: {self.state.gold}g  Fertilizer: {self.state.fertilizer_count}    ║")
        lines.append("╠══════════════════════════════════════╣")
        
        plant_types = list(PlantType)
        start = self.shop_page * 4
        end = min(start + 4, len(plant_types))
        
        for i, pt in enumerate(plant_types[start:end]):
            idx = start + i
            price = SHOP_PRICES.get(pt, 15)
            marker = "→" if idx == self.selected_plant_idx else " "
            owned = self.state.seeds.get(pt, 0)
            data = PLANT_DATA[pt]
            lines.append(f"║ {marker} {pt.value:12s} {price:3d}g (3 seeds) own:{owned:2d} ║")
            lines.append(f"║   Water need:{data['water_need']} Grow:{data['grow_rate']}x              ║")
        
        # Fertilizer option
        fert_marker = "→" if self.selected_plant_idx == len(plant_types) else " "
        lines.append("╠══════════════════════════════════════╣")
        lines.append(f"║ {fert_marker} Fertilizer    {FERTILIZER_PRICE:3d}g (1 unit)  own:{self.state.fertilizer_count:2d} ║")
        lines.append("╠══════════════════════════════════════╣")
        lines.append("║ ↑↓ Select  Enter:Buy  Esc:Back      ║")
        lines.append("║ ←/→: Page                             ║")
        lines.append("╚══════════════════════════════════════╝\033[0m")
        return "\n".join(lines)
    
    def render_plant_select(self) -> str:
        """Render the seed selection overlay."""
        lines = []
        lines.append("\033[92m╔══════════════════════════════════════╗")
        lines.append("║      🌱 SELECT SEED TO PLANT       ║")
        lines.append("╠══════════════════════════════════════╣")
        
        self.available_seeds_list = [(pt, c) for pt, c in self.state.seeds.items() if c > 0]
        
        if not self.available_seeds_list:
            lines.append("║  No seeds available!                ║")
            lines.append("║  Press S to visit the shop.         ║")
        else:
            for i, (pt, count) in enumerate(self.available_seeds_list):
                marker = "→" if i == self.selected_plant_idx else " "
                data = PLANT_DATA[pt]
                lines.append(f"║ {marker} {pt.value:12s} x{count}               ║")
                lines.append(f"║   Water:{data['water_need']} Grow:{data['grow_rate']}x H:{data['max_height']}          ║")
        
        lines.append("╠══════════════════════════════════════╣")
        lines.append("║ ↑↓ Select  Enter:Plant  Esc:Cancel  ║")
        lines.append("╚══════════════════════════════════════╝\033[0m")
        return "\n".join(lines)
    
    def render_forecast(self) -> str:
        """Render the weather forecast overlay."""
        lines = []
        lines.append("\033[96m╔══════════════════════════════════════╗")
        lines.append("║        🌤️  WEATHER FORECAST 🌤️       ║")
        lines.append("╠══════════════════════════════════════╣")
        
        forecast = self.forecast if self.forecast else self.compute_forecast(3)
        for i, weather in enumerate(forecast):
            future_day = self.state.day + i + 1
            future_season_idx = ((future_day - 1) // 28) % 4
            future_season = SEASON_ORDER[future_season_idx]
            future_season_day = ((future_day - 1) % 28) + 1
            emoji = WEATHER_EMOJI.get(weather, "")
            sc = SEASON_COLORS[future_season]
            lines.append(f"║  Day {future_day:3d} ({sc}{future_season.value} D{future_season_day}\033[0m)  {emoji} {weather:8s} ║")
        
        lines.append("╠══════════════════════════════════════╣")
        lines.append("║  Press any key to close             ║")
        lines.append("╚══════════════════════════════════════╝\033[0m")
        return "\n".join(lines)
    
    def render_help(self) -> str:
        """Render the help screen."""
        return """
\033[93m═══════════════════════════════════════
        🌻 GARDEN SIMULATOR HELP 🌻
═══════════════════════════════════════\033[0m

  \033[1mMovement:\033[0m     Arrow keys (↑↓←→)
  \033[1mPlant:\033[0m        P - Plant a seed at cursor
  \033[1mWater:\033[0m        W - Water plant at cursor
  \033[1mFertilize:\033[0m    F - Apply fertilizer (growth boost)
  \033[1mHarvest:\033[0m      H - Harvest mature / compost dead
  \033[1mRemove:\033[0m        X - Remove plant at cursor
  \033[1mShop:\033[0m         S - Buy seeds & fertilizer
  \033[1mForecast:\033[0m     T - View weather forecast
  \033[1mNext Day:\033[0m     N - Advance one day
  \033[1mNext Week:\033[0m    M - Advance 7 days
  \033[1mSave:\033[0m         V - Save game
  \033[1mHelp:\033[0m         ? - Show this help
  \033[1mQuit:\033[0m         Q - Exit game

\033[1mPlant Stages:\033[0m
  Seed → Sprout → Growing → Mature →
  Flowering → Fruiting → Withering → Dead

\033[1mTips:\033[0m
  • Different plants thrive in different seasons
  • Water your plants! But don't overwater.
  • Harvest at Flowering or Fruiting stage for gold.
  • Fruiting stage gives 1.5x harvest value.
  • Fertilized plants grow 1.5x faster for 3 days.
  • Fertilized harvests give +20% gold bonus.
  • Compost dead plants for 3g each (H key).
  • Storms and pests can damage your plants!
  • Press T to check upcoming weather.
  • Buy seeds & fertilizer at the shop (S key).
\033[93m═══════════════════════════════════════\033[0m
"""
    
    def save_game(self):
        """Save game state to disk."""
        data = {
            "version": __version__,
            "day": self.state.day,
            "gold": self.state.gold,
            "seeds": {pt.value: count for pt, count in self.state.seeds.items()},
            "total_harvested": self.state.total_harvested,
            "total_planted": self.state.total_planted,
            "fertilizer_count": self.state.fertilizer_count,
            "plants": [],
        }
        for row in self.state.grid:
            for plant in row:
                if plant:
                    data["plants"].append({
                        "type": plant.plant_type.value,
                        "x": plant.x,
                        "y": plant.y,
                        "growth": plant.growth,
                        "water_level": plant.water_level,
                        "health": plant.health,
                        "age_days": plant.age_days,
                        "rng_seed": plant.rng_seed,
                        "fertilized_days": plant.fertilized_days,
                    })
        try:
            with open(SAVE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            self.state.message = "Game saved! 💾"
            self.state.message_timer = 20
        except Exception as e:
            self.state.message = f"Save failed: {e}"
            self.state.message_timer = 30
    
    def load_game(self) -> bool:
        """Load game state from disk. Returns True on success."""
        if not os.path.exists(SAVE_FILE):
            return False
        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
            self.state.day = data["day"]
            self.state.gold = data["gold"]
            self.state.seeds = {PlantType(name): count for name, count in data["seeds"].items()}
            self.state.total_harvested = data.get("total_harvested", 0)
            self.state.total_planted = data.get("total_planted", 0)
            self.state.fertilizer_count = data.get("fertilizer_count", 3)
            self.state.grid = [[None]*GRID_W for _ in range(GRID_H)]
            for pd in data["plants"]:
                plant = Plant(
                    plant_type=PlantType(pd["type"]),
                    x=pd["x"], y=pd["y"],
                    growth=pd["growth"],
                    water_level=pd["water_level"],
                    health=pd["health"],
                    age_days=pd["age_days"],
                    rng_seed=pd["rng_seed"],
                    fertilized_days=pd.get("fertilized_days", 0),
                )
                self.state.grid[pd["y"]][pd["x"]] = plant
            # Set season
            season_idx = ((self.state.day - 1) // 28) % 4
            self.state.season = SEASON_ORDER[season_idx]
            # Generate initial weather and forecast
            self.weather = generate_weather(self.state.season)
            self.forecast = self.compute_forecast(3)
            return True
        except Exception:
            return False
    
    def get_stats(self) -> str:
        """Return a string with game statistics."""
        plant_count = 0
        total_growth = 0.0
        total_health = 0.0
        stage_counts = {}
        for row in self.state.grid:
            for plant in row:
                if plant and plant.stage != GrowthStage.DEAD:
                    plant_count += 1
                    total_growth += plant.growth
                    total_health += plant.health
                    stage_name = plant.stage.name
                    stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1
        
        avg_growth = total_growth / plant_count if plant_count > 0 else 0
        avg_health = total_health / plant_count if plant_count > 0 else 0
        
        lines = [
            f"\033[93m{'='*40}\033[0m",
            f"\033[1m  🌻 Garden Statistics 🌻\033[0m",
            f"\033[93m{'='*40}\033[0m",
            f"  Day: {self.state.day}  Season: {self.state.season.value}",
            f"  Gold: {self.state.gold}g",
            f"  Plants alive: {plant_count}",
            f"  Plants planted (all time): {self.state.total_planted}",
            f"  Plants harvested (all time): {self.state.total_harvested}",
            f"  Avg growth: {avg_growth:.1f}%",
            f"  Avg health: {avg_health:.1f}%",
            f"  Fertilizer: {self.state.fertilizer_count}",
            f"  Seeds: {sum(self.state.seeds.values())}",
            "",
        ]
        if stage_counts:
            lines.append("  Growth stages:")
            for stage in GrowthStage:
                if stage.name in stage_counts:
                    lines.append(f"    {stage.name}: {stage_counts[stage.name]}")
        return "\n".join(lines)
    
    def run(self):
        """Main game loop with interactive terminal input."""
        # Try to load saved game
        if os.path.exists(SAVE_FILE):
            self.load_game()
        
        # Generate initial weather and forecast
        self.weather = generate_weather(self.state.season)
        self.forecast = self.compute_forecast(3)
        
        # Set up terminal for raw input
        try:
            import tty
            import termios
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
        except (ImportError, termios.error):
            old_settings = None
            fd = None
        
        def read_key():
            """Read a single keypress from terminal."""
            try:
                ch = sys.stdin.read(1)
                if ch == '\x1b':  # ESC sequence
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        ch3 = sys.stdin.read(1)
                        if ch3 == 'A':
                            return 'UP'
                        elif ch3 == 'B':
                            return 'DOWN'
                        elif ch3 == 'C':
                            return 'RIGHT'
                        elif ch3 == 'D':
                            return 'LEFT'
                    return 'ESC'
                elif ch == '\r' or ch == '\n':
                    return 'ENTER'
                elif ch == ' ':
                    return 'SPACE'
                elif ch == '\x03':  # Ctrl+C
                    return 'QUIT'
                elif ch == '\x7f' or ch == '\x08':  # Backspace
                    return 'BACKSPACE'
                return ch.upper()
            except:
                return 'QUIT'
        
        try:
            while self.running:
                self.clear_screen()
                
                if self.mode == "shop":
                    print(self.render_shop())
                elif self.mode == "plant_select":
                    print(self.render_plant_select())
                elif self.mode == "forecast":
                    print(self.render_forecast())
                else:
                    print(self.render_garden())
                
                key = read_key()
                
                if key == 'QUIT':
                    self.running = False
                    break
                
                # Forecast mode — any key dismisses
                if self.mode == "forecast":
                    self.mode = "normal"
                    continue
                
                # Mode-specific handling
                if self.mode == "shop":
                    total_items = len(PlantType) + 1  # +1 for fertilizer
                    if key == 'ESC' or key == 'S':
                        self.mode = "normal"
                    elif key == 'UP':
                        self.selected_plant_idx = max(0, self.selected_plant_idx - 1)
                    elif key == 'DOWN':
                        max_idx = total_items - 1
                        self.selected_plant_idx = min(max_idx, self.selected_plant_idx + 1)
                    elif key == 'LEFT':
                        self.shop_page = max(0, self.shop_page - 1)
                        self.selected_plant_idx = self.shop_page * 4
                    elif key == 'RIGHT':
                        max_page = (len(PlantType)) // 4
                        self.shop_page = min(max_page, self.shop_page + 1)
                        self.selected_plant_idx = self.shop_page * 4
                    elif key == 'ENTER':
                        if self.selected_plant_idx < len(PlantType):
                            self.buy_seed(list(PlantType)[self.selected_plant_idx])
                        elif self.selected_plant_idx == len(PlantType):
                            # Fertilizer
                            self.buy_fertilizer()
                    continue
                
                elif self.mode == "plant_select":
                    if key == 'ESC':
                        self.mode = "normal"
                    elif key == 'UP':
                        self.selected_plant_idx = max(0, self.selected_plant_idx - 1)
                    elif key == 'DOWN':
                        max_idx = len(self.available_seeds_list) - 1
                        self.selected_plant_idx = min(max_idx, self.selected_plant_idx + 1)
                    elif key == 'ENTER':
                        if self.available_seeds_list:
                            if self.selected_plant_idx < len(self.available_seeds_list):
                                pt, count = self.available_seeds_list[self.selected_plant_idx]
                                self.plant_seed(pt, self.state.cursor_x, self.state.cursor_y)
                        self.mode = "normal"
                    continue
                
                # Normal mode controls
                if key == 'UP':
                    self.state.cursor_y = max(0, self.state.cursor_y - 1)
                elif key == 'DOWN':
                    self.state.cursor_y = min(GRID_H - 1, self.state.cursor_y + 1)
                elif key == 'LEFT':
                    self.state.cursor_x = max(0, self.state.cursor_x - 1)
                elif key == 'RIGHT':
                    self.state.cursor_x = min(GRID_W - 1, self.state.cursor_x + 1)
                elif key == 'P':
                    # Enter plant select mode
                    self.available_seeds_list = [(pt, c) for pt, c in self.state.seeds.items() if c > 0]
                    if self.available_seeds_list:
                        self.selected_plant_idx = 0
                        self.mode = "plant_select"
                    else:
                        self.state.message = "No seeds! Press S to visit shop."
                        self.state.message_timer = 30
                elif key == 'W':
                    # Water plant
                    self.water_plant(self.state.cursor_x, self.state.cursor_y)
                elif key == 'F':
                    # Fertilize plant
                    self.fertilize_plant(self.state.cursor_x, self.state.cursor_y)
                elif key == 'H':
                    # Harvest / compost
                    self.harvest_plant(self.state.cursor_x, self.state.cursor_y)
                elif key == 'X':
                    # Remove plant
                    self.remove_plant(self.state.cursor_x, self.state.cursor_y)
                elif key == 'S':
                    # Open shop
                    self.mode = "shop"
                    self.selected_plant_idx = 0
                    self.shop_page = 0
                elif key == 'T':
                    # Weather forecast
                    self.forecast = self.compute_forecast(3)
                    self.mode = "forecast"
                elif key == 'N':
                    # Next day
                    self.advance_day(1)
                elif key == 'M':
                    # Next week
                    self.advance_day(7)
                elif key == '?' or key == '/':
                    self.clear_screen()
                    print(self.render_help())
                    input("\nPress Enter to continue...")
                elif key == 'V':
                    # Save game
                    self.save_game()
                elif key == 'Q':
                    self.running = False
        
        finally:
            if old_settings and fd is not None:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            self.clear_screen()
            print(f"\n\033[93m🌻 Thanks for gardening! 🌻\033[0m")
            print(f"  Days survived: {self.state.day}")
            print(f"  Gold earned: {self.state.gold}")
            print(f"  Plants harvested: {self.state.total_harvested}")
            print(f"  Plants planted: {self.state.total_planted}\n")


def show_stats():
    """Load a saved game and display statistics, then exit."""
    game = GardenSimulator()
    if os.path.exists(SAVE_FILE):
        game.load_game()
        print(game.get_stats())
    else:
        print("No saved game found at", SAVE_FILE)


def main():
    """Entry point: parse arguments and run the game or display info."""
    import argparse
    parser = argparse.ArgumentParser(
        description="Terminal Procedural Garden Simulator — plant, grow, and harvest ASCII plants through the seasons!",
        epilog="Run without arguments for interactive mode."
    )
    parser.add_argument('--demo', action='store_true', help='Run in demo mode (non-interactive preview)')
    parser.add_argument('--stats', action='store_true', help='Show statistics from a saved game')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
        return
    
    game = GardenSimulator()
    
    if args.demo:
        # Auto-populate and show garden
        plants_demo = [
            (PlantType.SUNFLOWER, 5, 10),
            (PlantType.ROSE, 10, 8),
            (PlantType.CACTUS, 15, 12),
            (PlantType.TULIP, 20, 6),
            (PlantType.TREE, 25, 5),
            (PlantType.FERN, 8, 14),
            (PlantType.VINE, 30, 11),
            (PlantType.MUSHROOM, 12, 13),
        ]
        for pt, x, y in plants_demo:
            game.state.grid[y][x] = Plant(plant_type=pt, x=x, y=y)
            game.state.grid[y][x].growth = random.uniform(30, 95)
            game.state.grid[y][x].water_level = random.uniform(20, 80)
            game.state.grid[y][x].health = random.uniform(60, 100)
            game.state.grid[y][x].age_days = random.randint(5, 50)
        
        game.state.day = 15
        game.state.gold = 120
        game.state.seeds = {
            PlantType.SUNFLOWER: 5,
            PlantType.ROSE: 3,
            PlantType.TULIP: 2,
            PlantType.CACTUS: 1,
            PlantType.MUSHROOM: 2,
        }
        
        # Simulate a few days of weather
        game.advance_day(0)
        game.weather = "Clear"
        game.forecast = game.compute_forecast(3)
        
        print(game.render_garden())
        print()
        print("\033[93m" + "=" * 50 + "\033[0m")
        print("\033[92m  🌻 GARDEN DEMO MODE 🌻\033[0m")
        print("\033[93m" + "=" * 50 + "\033[0m")
        print()
        print("This is a preview of your garden!")
        print("Run without --demo for interactive mode.")
        print()
        print("Controls:")
        print("  Arrow keys     - Move cursor")
        print("  P - Plant seed    W - Water")
        print("  F - Fertilize     H - Harvest/Compost")
        print("  X - Remove        S - Shop")
        print("  T - Forecast      N - Next day")
        print("  M - Next week     V - Save")
        print("  Q - Quit")
        print()
        
        # Show some plants in detail
        for pt, x, y in plants_demo[:4]:
            p = game.state.grid[y][x]
            if p is not None:
                art = render_plant(p.plant_type, p.stage, p.height, p.rng)
                print(f"  {p.plant_type.value} ({p.stage.name}):")
                for line in art:
                    print(f"    {line}")
                print(f"    Growth: {p.growth:.0f}%  Water: {p.water_level:.0f}%  Health: {p.health:.0f}%")
                print()
    else:
        game.run()


if __name__ == "__main__":
    main()