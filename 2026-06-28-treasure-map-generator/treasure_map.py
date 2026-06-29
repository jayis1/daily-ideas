#!/usr/bin/env python3
"""
Procedural Treasure Map Generator
===================================
Generates elaborate ASCII treasure maps with coastlines, terrain features,
dotted trails, compass roses, sea monsters, pirate riddles, and X-marks-the-spot.
Each map is unique — seeded or random.

Features:
  - Procedural terrain via fractal Brownian motion
  - Inland lakes, swamps, and volcanoes
  - Context-aware pirate riddles referencing actual map features
  - Difficulty presets affecting terrain generation
  - Terrain statistics (--stats)
  - Save to file (--save)
  - Distance estimation from landing to treasure

Version: 1.2.0
"""

import random
import math
import argparse
import sys
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

# ── Version ──────────────────────────────────────────────────────────────────

__version__ = "1.2.0"

# ── Difficulty Presets ───────────────────────────────────────────────────────

DIFFICULTY_PRESETS = {
    "easy": {
        "water_level": 0.30,
        "sand_level": 0.36,
        "grass_level": 0.50,
        "forest_level": 0.62,
        "mountain_level": 0.78,
        "description": "Larger islands, more land to explore",
    },
    "normal": {
        "water_level": 0.38,
        "sand_level": 0.44,
        "grass_level": 0.56,
        "forest_level": 0.68,
        "mountain_level": 0.82,
        "description": "Balanced island with mixed terrain",
    },
    "hard": {
        "water_level": 0.48,
        "sand_level": 0.53,
        "grass_level": 0.60,
        "forest_level": 0.72,
        "mountain_level": 0.85,
        "description": "Tiny atoll, mostly water — hard to find land!",
    },
}

# ── Map Symbols ──────────────────────────────────────────────────────────────

SYMBOLS = {
    "water":      "~",
    "deep_water": "≈",
    "sand":       ".",
    "grass":      ",",
    "forest":     "♣",
    "dense_forest":"♣",
    "mountain":   "▲",
    "peak":       "△",
    "swamp":      "%",
    "volcano":    "V",
    "lava":       "◙",
    "trail_dot":  "·",
    "trail_dash": "─",
    "x_mark":     "✕",
    "skull":      "☠",
    "cross":      "†",
    "anchor":     "⎋",
    "ship":       "⛵",
    "chest":      "📦",
    "compass_N":  "N",
    "compass_S":  "S",
    "compass_E":  "E",
    "compass_W":  "W",
    "border_h":   "═",
    "border_v":   "║",
    "corner_tl":  "╔",
    "corner_tr":  "╗",
    "corner_bl":  "╚",
    "corner_br":  "╝",
}

# Simplified ASCII fallback for terminals without unicode
SIMPLE_SYMBOLS = {
    "water":      "~",
    "deep_water": "~",
    "sand":       ".",
    "grass":      "\"",
    "forest":     "T",
    "dense_forest":"T",
    "mountain":   "^",
    "peak":       "A",
    "swamp":      "&",
    "volcano":    "V",
    "lava":       "o",
    "trail_dot":  ".",
    "trail_dash": "-",
    "x_mark":     "X",
    "skull":      "!",
    "cross":      "+",
    "anchor":     "A",
    "ship":       "S",
    "chest":      "C",
    "compass_N":  "N",
    "compass_S":  "S",
    "compass_E":  "E",
    "compass_W":  "W",
    "border_h":   "=",
    "border_v":   "|",
    "corner_tl":  "+",
    "corner_tr":  "+",
    "corner_bl":  "+",
    "corner_br":  "+",
}


# ── Helper functions ──────────────────────────────────────────────────────────

def lerp(a, b, t):
    """Linear interpolation between a and b by factor t."""
    return a + (b - a) * t


def clamp(v, lo, hi):
    """Clamp value v to the range [lo, hi]."""
    return max(lo, min(hi, v))


def noise_2d(x, y, seed=0):
    """Simple deterministic hash-based pseudo-noise for terrain generation."""
    n = int(x * 374761393 + y * 668265263 + seed * 1013904223)
    n = ((n >> 13) ^ n)
    n = (n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff
    return (n & 0xffff) / 0xffff


def smooth_noise(x, y, seed=0, scale=0.08):
    """Bilinearly interpolated smooth noise using smoothstep."""
    sx, sy = x * scale, y * scale
    ix, iy = int(math.floor(sx)), int(math.floor(sy))
    fx, fy = sx - ix, sy - iy
    fx = fx * fx * (3 - 2 * fx)  # smoothstep
    fy = fy * fy * (3 - 2 * fy)
    n00 = noise_2d(ix, iy, seed)
    n10 = noise_2d(ix + 1, iy, seed)
    n01 = noise_2d(ix, iy + 1, seed)
    n11 = noise_2d(ix + 1, iy + 1, seed)
    nx0 = lerp(n00, n10, fx)
    nx1 = lerp(n01, n11, fx)
    return lerp(nx0, nx1, fy)


def fbm(x, y, seed=0, octaves=4, scale=0.08, lacunarity=2.0, gain=0.5):
    """Fractal Brownian Motion — layered noise for terrain generation.

    Multiple octaves of smooth noise are summed with decreasing amplitude
    to produce natural-looking terrain height fields.
    """
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_amp = 0.0
    for _ in range(octaves):
        value += amplitude * smooth_noise(x * frequency, y * frequency, seed, scale)
        max_amp += amplitude
        amplitude *= gain
        frequency *= lacunarity
    return value / max_amp


# ── Map Generation ────────────────────────────────────────────────────────────

@dataclass
class MapConfig:
    """Configuration for a treasure map generation run."""
    width: int = 72
    height: int = 34
    seed: Optional[int] = None
    water_level: float = 0.38
    sand_level: float = 0.44
    grass_level: float = 0.56
    forest_level: float = 0.68
    mountain_level: float = 0.82
    unicode: bool = True
    difficulty: str = "normal"


class TreasureMap:
    """Procedural treasure map generator.

    Creates a unique island map each time, with terrain features, trails,
    landmarks, sea creatures, and more. Maps can be seeded for reproducibility.
    """

    def __init__(self, config: MapConfig):
        self.cfg = config
        # Apply difficulty preset if specified (and not overridden by explicit levels)
        if config.difficulty != "normal":
            preset = DIFFICULTY_PRESETS.get(config.difficulty, DIFFICULTY_PRESETS["normal"])
            # Only apply preset levels if the config still has defaults
            # (We detect this by checking if levels match 'normal' defaults)
            normal = DIFFICULTY_PRESETS["normal"]
            if abs(config.water_level - normal["water_level"]) < 0.001:
                self.cfg = MapConfig(
                    width=config.width,
                    height=config.height,
                    seed=config.seed,
                    water_level=preset["water_level"],
                    sand_level=preset["sand_level"],
                    grass_level=preset["grass_level"],
                    forest_level=preset["forest_level"],
                    mountain_level=preset["mountain_level"],
                    unicode=config.unicode,
                    difficulty=config.difficulty,
                )
        if config.seed is not None:
            random.seed(config.seed)
        self.seed = config.seed if config.seed is not None else random.randint(0, 999999)
        random.seed(self.seed)
        self.sym = SYMBOLS if self.cfg.unicode else SIMPLE_SYMBOLS
        self.grid: List[List[str]] = []
        self.terrain: List[List[str]] = []  # terrain type per cell
        self.annotations: List[Tuple[int, int, str]] = []  # overlaid labels
        self.treasure_x: Optional[int] = None
        self.treasure_y: Optional[int] = None
        self.landing_x: Optional[int] = None
        self.landing_y: Optional[int] = None
        self.landmark_names_placed: List[str] = []  # Track placed landmark names for riddle context
        self._generate()

    def _add_annotation(self, x: int, y: int, text: str):
        """Add an annotation label, clamping position so it stays within grid bounds.

        Also checks for overlap with the treasure X position and shifts the label
        if it would overwrite the treasure marker.
        """
        W, H = self.cfg.width, self.cfg.height
        # Clamp x so the entire label fits within the grid
        x = max(0, min(x, W - len(text)))
        # Clamp y within grid bounds
        y = max(0, min(y, H - 1))

        # Avoid overwriting the treasure X marker with this label
        if self.treasure_x is not None and self.treasure_y is not None:
            tx, ty = self.treasure_x, self.treasure_y
            if ty == y and x <= tx < x + len(text):
                # Shift the label to the right past the treasure, or left before it
                new_x = tx + 2
                if new_x + len(text) <= W:
                    x = new_x
                else:
                    new_x = tx - len(text) - 1
                    if new_x >= 0:
                        x = new_x
                    # If neither works, keep original clamped position (best effort)

        self.annotations.append((x, y, text))

    def _generate(self):
        """Main generation pipeline: heightmap → terrain → features → render."""
        W, H = self.cfg.width, self.cfg.height

        # 1. Generate heightmap
        heightmap = [[0.0] * W for _ in range(H)]
        seed1 = self.seed
        seed2 = self.seed + 7919
        for y in range(H):
            for x in range(W):
                # Distance from center for island-like shape
                dx = (x - W / 2) / (W / 2)
                dy = (y - H / 2) / (H / 2)
                dist = math.sqrt(dx * dx + dy * dy)
                # Falloff to create island edges
                falloff = max(0, 1.0 - dist * 0.9)
                # Combine noise layers
                n1 = fbm(x, y, seed1, octaves=5, scale=0.06)
                n2 = fbm(x, y, seed2, octaves=3, scale=0.12)
                h = (n1 * 0.7 + n2 * 0.3) * falloff
                # Add slight randomness to coast
                h += random.uniform(-0.02, 0.02)
                heightmap[y][x] = clamp(h, 0.0, 1.0)

        # 2. Convert heightmap to terrain
        self.terrain = [["water"] * W for _ in range(H)]
        self.grid = [[self.sym["water"]] * W for _ in range(H)]
        wl = self.cfg.water_level
        sl = self.cfg.sand_level
        gl = self.cfg.grass_level
        fl = self.cfg.forest_level
        ml = self.cfg.mountain_level

        for y in range(H):
            for x in range(W):
                h = heightmap[y][x]
                if h < wl - 0.1:
                    t = "deep_water"
                elif h < wl:
                    t = "water"
                elif h < sl:
                    t = "sand"
                elif h < gl:
                    t = "grass"
                elif h < fl:
                    # Decide between grass and forest based on local noise
                    if fbm(x, y, self.seed + 1234, octaves=2, scale=0.15) > 0.45:
                        t = "forest"
                    else:
                        t = "grass"
                elif h < ml:
                    t = "dense_forest" if fbm(x, y, self.seed + 5678, octaves=2, scale=0.2) > 0.5 else "mountain"
                else:
                    t = "peak"

                self.terrain[y][x] = t
                self.grid[y][x] = self.sym.get(t, self.sym["water"])

        # 3. Add special features
        self._add_coast_foam()
        self._add_lake_if_possible(heightmap)
        self._add_swamp_if_possible(heightmap)
        self._add_volcano_if_possible()
        self._place_treasure(heightmap)
        self._draw_trail(heightmap)
        self._add_landmarks(heightmap)
        self._add_sea_creatures()
        self._add_compass_rose()
        self._add_ship()
        self._add_danger_markers()

    def _add_coast_foam(self):
        """Add a thin line of different characters at water/land boundaries."""
        W, H = self.cfg.width, self.cfg.height
        for y in range(H):
            for x in range(W):
                if self.terrain[y][x] in ("water", "deep_water"):
                    # Check if adjacent to land
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W:
                            if self.terrain[ny][nx] not in ("water", "deep_water"):
                                self.grid[y][x] = self.sym["water"]
                                break

    def _add_lake_if_possible(self, heightmap):
        """Sometimes add an inland lake by flooding a grass/forest area."""
        if random.random() > 0.6:
            return
        W, H = self.cfg.width, self.cfg.height
        # Find a grass/forest area away from edges
        candidates = []
        for y in range(4, H - 4):
            for x in range(4, W - 4):
                if self.terrain[y][x] in ("grass", "forest"):
                    candidates.append((x, y))
        if len(candidates) < 20:
            return
        cx, cy = random.choice(candidates)
        lake_r = random.randint(2, 4)
        for y in range(H):
            for x in range(W):
                d = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if d < lake_r:
                    self.terrain[y][x] = "water"
                    self.grid[y][x] = self.sym["water"]

    def _add_swamp_if_possible(self, heightmap):
        """Add swampy areas near water at low elevation.

        Swamps form on grass or forest cells that are close to water,
        creating marshy transition zones that make maps more interesting.
        """
        W, H = self.cfg.width, self.cfg.height
        if random.random() > 0.45:
            return
        # Find grass cells adjacent to water/soft terrain
        candidates = []
        for y in range(2, H - 2):
            for x in range(2, W - 2):
                if self.terrain[y][x] in ("grass", "forest"):
                    # Count adjacent water cells
                    water_neighbors = 0
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W:
                            if self.terrain[ny][nx] in ("water", "deep_water", "sand"):
                                water_neighbors += 1
                    if water_neighbors >= 2:
                        candidates.append((x, y))

        if not candidates:
            return

        # Pick a cluster center and create a swamp area
        random.shuffle(candidates)
        num_swamp = min(len(candidates), random.randint(3, 8))
        for i in range(num_swamp):
            sx, sy = candidates[i]
            self.terrain[sy][sx] = "swamp"
            self.grid[sy][sx] = self.sym["swamp"]

    def _add_volcano_if_possible(self):
        """Occasionally place a volcano on peak or mountain terrain.

        Volcanoes are dramatic features that add character to maps.
        They display a V symbol with an optional label and lava flow.
        """
        W, H = self.cfg.width, self.cfg.height
        if random.random() > 0.45:  # 45% chance
            return
        # Find peak cells first, then mountain cells, then dense_forest as last resort
        peak_cells = []
        mountain_cells = []
        forest_cells = []
        for y in range(3, H - 3):
            for x in range(3, W - 3):
                if self.terrain[y][x] == "peak":
                    peak_cells.append((x, y))
                elif self.terrain[y][x] == "mountain":
                    mountain_cells.append((x, y))
                elif self.terrain[y][x] == "dense_forest":
                    forest_cells.append((x, y))

        # Prefer peaks for volcanoes, fall back to mountains, then dense forest
        candidate_cells = peak_cells if peak_cells else (mountain_cells if mountain_cells else forest_cells)
        if not candidate_cells:
            return

        vx, vy = random.choice(candidate_cells)
        # Mark the volcano
        self.terrain[vy][vx] = "volcano"
        self.grid[vy][vx] = self.sym["volcano"]

        # Add lava flow — a short line of lava going downhill from the volcano
        lava_directions = [(0, 1), (1, 1), (-1, 1), (1, 0), (-1, 0)]
        dx, dy = random.choice(lava_directions)
        lava_len = random.randint(2, 4)
        for step in range(1, lava_len + 1):
            lx, ly = vx + dx * step, vy + dy * step
            if 0 <= lx < W and 0 <= ly < H:
                if self.terrain[ly][lx] in ("mountain", "grass", "forest", "peak", "sand"):
                    self.terrain[ly][lx] = "lava"
                    self.grid[ly][lx] = self.sym["lava"]

        # Label it
        volcano_names = ["Mount Doom", "Fire Mountain", "Volcano Inferno",
                         "The Cauldron", "Smoldering Peak", "Dragon's Breath",
                         "Burning Hill", "Ashen Mound"]
        name = random.choice(volcano_names)
        self.landmark_names_placed.append(name)
        label_x = min(vx + 2, W - len(name))
        label_y = max(vy - 1, 0)
        self._add_annotation(label_x, label_y, name)

    def _place_treasure(self, heightmap):
        """Place the treasure X on land, preferably inland away from water."""
        W, H = self.cfg.width, self.cfg.height
        land_cells = []
        for y in range(3, H - 3):
            for x in range(3, W - 3):
                if self.terrain[y][x] in ("grass", "forest", "dense_forest", "sand", "swamp"):
                    # Prefer cells farther from water
                    water_dist = 0
                    for dy in range(-3, 4):
                        for dx in range(-3, 4):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < H and 0 <= nx < W:
                                if self.terrain[ny][nx] in ("water", "deep_water"):
                                    water_dist += 1
                    land_cells.append((x, y, water_dist))

        if not land_cells:
            return

        # Prefer cells far from water (more inland)
        land_cells.sort(key=lambda c: -c[2])
        top = land_cells[:max(1, len(land_cells) // 5)]
        chosen = random.choice(top)
        self.treasure_x, self.treasure_y = chosen[0], chosen[1]
        self.grid[self.treasure_y][self.treasure_x] = self.sym["x_mark"]

        # Add "Here be treasure!" annotation near the X
        label = "Here be treasure!"
        label_x = min(self.treasure_x + 2, W - len(label))
        label_y = max(self.treasure_y - 1, 0)
        self._add_annotation(label_x, label_y, label)

    def _draw_trail(self, heightmap):
        """Draw a dotted trail from a landing point to the treasure."""
        W, H = self.cfg.width, self.cfg.height
        # Find a beach cell on the coast for the landing
        beach_cells = []
        for y in range(H):
            for x in range(W):
                if self.terrain[y][x] == "sand":
                    # Must be adjacent to water
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W:
                            if self.terrain[ny][nx] in ("water", "deep_water"):
                                beach_cells.append((x, y))
                                break

        if not beach_cells or self.treasure_x is None:
            return

        # Filter out beach cells that are the same as the treasure location
        tx, ty = self.treasure_x, self.treasure_y
        valid_beach = [(x, y) for x, y in beach_cells if (x, y) != (tx, ty)]
        if not valid_beach:
            # All beach cells overlap with treasure — expand search
            for y in range(H):
                for x in range(W):
                    if (x, y) != (tx, ty) and self.terrain[y][x] not in ("water", "deep_water"):
                        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < H and 0 <= nx < W:
                                if self.terrain[ny][nx] in ("water", "deep_water"):
                                    valid_beach.append((x, y))
                                    break
        if not valid_beach:
            self.landing_x, self.landing_y = None, None
            return

        start = random.choice(valid_beach)
        self.landing_x, self.landing_y = start[0], start[1]

        # Mark the landing with an anchor symbol in adjacent water
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = self.landing_y + dy, self.landing_x + dx
            if 0 <= ny < H and 0 <= nx < W and self.terrain[ny][nx] in ("water", "deep_water"):
                self.grid[ny][nx] = self.sym["anchor"]
                break

        # Walk from landing to treasure
        path = self._find_path(start, (self.treasure_x, self.treasure_y))
        for i, (px, py) in enumerate(path):
            if self.terrain[py][px] not in ("water", "deep_water") and self.grid[py][px] != self.sym["x_mark"]:
                # Alternating trail symbols for visual variety
                if i % 3 == 0:
                    self.grid[py][px] = self.sym["trail_dash"]
                else:
                    self.grid[py][px] = self.sym["trail_dot"]

    def _find_path(self, start, end):
        """Greedy pathfinding with randomness for a winding trail effect.

        Uses 8-directional movement, preferring moves toward the treasure
        but with random perturbation to avoid straight-line paths.
        """
        W, H = self.cfg.width, self.cfg.height
        x, y = start
        path = []
        visited = set()
        max_steps = max(500, W * H // 2)
        for _ in range(max_steps):
            if (x, y) == end:
                break
            dx = end[0] - x
            dy = end[1] - y
            # Possible moves (8-directional)
            moves = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
            # Score each move
            scored = []
            for mx, my in moves:
                nx, ny = x + mx, y + my
                if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in visited:
                    if self.terrain[ny][nx] not in ("water", "deep_water") or (nx, ny) == end:
                        dist = math.sqrt((nx - end[0]) ** 2 + (ny - end[1]) ** 2)
                        # Add randomness for winding paths
                        dist += random.uniform(-2, 2)
                        scored.append((dist, nx, ny))
            if not scored:
                break
            scored.sort(key=lambda s: s[0])
            # Pick best with some randomness
            pick = random.choice(scored[:3]) if len(scored) > 2 else scored[0]
            x, y = pick[1], pick[2]
            visited.add((x, y))
            path.append((x, y))
        return path

    def _add_landmarks(self, heightmap):
        """Add named landmarks: mountains, forests, bays, swamps, volcanoes, etc."""
        W, H = self.cfg.width, self.cfg.height
        landmark_names = {
            "peak": ["Dragon's Peak", "Skull Mountain", "The Spire", "Witch's Needle", "Giant's Thumb", "Old Thunder"],
            "forest": ["Darkwood", "Whispering Forest", "Goblin Hollow", "Spider's Glen", "Deadman's Copse", "Hangman's Grove"],
            "dense_forest": ["Blackwood Deep", "Demon's Thicket", "Serpent Jungle", "The Bramble", "Cursed Tangle"],
            "sand": ["Dead Man's Beach", "Serpent's Cove", "Smuggler's Bay", "Boneshore", "Wreck Beach"],
            "swamp": ["Mire of Souls", "Bogwater", "Dead Marsh", "Fen of Shadows"],
            "mountain": ["Iron Hills", "Stoneback Ridge", "Cragmoor"],
            "volcano": ["Mount Doom", "Fire Mountain", "The Cauldron"],
        }

        used_names = set()
        placed = 0

        # Try to label peaks
        for y in range(2, H - 2):
            for x in range(2, W - 2):
                if self.terrain[y][x] == "peak" and placed < 5:
                    if random.random() < 0.4:
                        name = random.choice(landmark_names.get("peak", ["Peak"]))
                        while name in used_names:
                            name = random.choice(landmark_names.get("peak", ["Peak"]))
                        used_names.add(name)
                        self.landmark_names_placed.append(name)
                        self._add_annotation(x + 1, max(y - 1, 0), name)
                        placed += 1

        # Try to label a forest area
        forest_cells = [(x, y) for y in range(H) for x in range(W)
                        if self.terrain[y][x] in ("forest", "dense_forest")]
        if forest_cells and placed < 5:
            fx, fy = random.choice(forest_cells)
            ftype = "forest" if self.terrain[fy][fx] == "forest" else "dense_forest"
            name = random.choice(landmark_names.get(ftype, ["Woods"]))
            while name in used_names:
                name = random.choice(landmark_names.get(ftype, ["Woods"]))
            used_names.add(name)
            self.landmark_names_placed.append(name)
            self._add_annotation(fx + 1, max(fy - 1, 0), name)
            placed += 1

        # Try to label a beach area
        beach_cells = [(x, y) for y in range(H) for x in range(W) if self.terrain[y][x] == "sand"]
        if beach_cells and placed < 5:
            bx, by = random.choice(beach_cells)
            name = random.choice(landmark_names.get("sand", ["Beach"]))
            while name in used_names:
                name = random.choice(landmark_names.get("sand", ["Beach"]))
            used_names.add(name)
            self.landmark_names_placed.append(name)
            self._add_annotation(bx + 1, max(by - 1, 0), name)
            placed += 1

        # Try to label a swamp area
        swamp_cells = [(x, y) for y in range(H) for x in range(W) if self.terrain[y][x] == "swamp"]
        if swamp_cells and placed < 5:
            sx, sy = random.choice(swamp_cells)
            name = random.choice(landmark_names.get("swamp", ["Swamp"]))
            while name in used_names:
                name = random.choice(landmark_names.get("swamp", ["Swamp"]))
            used_names.add(name)
            self.landmark_names_placed.append(name)
            self._add_annotation(sx + 1, max(sy - 1, 0), name)
            placed += 1

    def _add_sea_creatures(self):
        """Add sea monsters and labels in open water areas."""
        W, H = self.cfg.width, self.cfg.height
        creatures = ["🐙", "🐋", "🦑"] if self.cfg.unicode else ["~", "~"]
        creature_labels = ["Kraken", "Leviathan", "Sea Serpent"]

        # Find large water areas
        water_cells = []
        for y in range(2, H - 2):
            for x in range(2, W - 2):
                if self.terrain[y][x] in ("water", "deep_water"):
                    # Check it's surrounded by water
                    all_water = True
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W:
                            if self.terrain[ny][nx] not in ("water", "deep_water"):
                                all_water = False
                    if all_water:
                        water_cells.append((x, y))

        if water_cells:
            num = min(len(water_cells), random.randint(1, 2))
            random.shuffle(water_cells)
            for i in range(num):
                cx, cy = water_cells[i]
                if self.cfg.unicode:
                    self.grid[cy][cx] = random.choice(creatures)
                # Label — use _add_annotation for proper bounds checking
                label = creature_labels[i % len(creature_labels)]
                lx = min(cx + 1, W - len(label) - 1)
                self._add_annotation(lx, cy, label)

        # Add "Here be dragons" text in a far water area
        if water_cells:
            far_cells = sorted(water_cells, key=lambda c: -(c[0] + c[1]))
            if far_cells:
                fx, fy = far_cells[0]
                label = "Here be dragons"
                lx = max(0, min(fx - 2, W - len(label) - 1))
                self._add_annotation(lx, fy, label)

    def _add_compass_rose(self):
        """Add a compass rose in a corner water area."""
        W, H = self.cfg.width, self.cfg.height
        cx, cy = 6, 3
        if not (0 <= cy < H and 0 <= cx < W):
            return
        # Draw a small compass rose
        compass = [
            (0, -2, "N"),
            (0, 2, "S"),
            (2, 0, "E"),
            (-2, 0, "W"),
            (-1, -1, "\\"),  # diagonal
            (1, -1, "/"),
            (-1, 1, "/"),
            (1, 1, "\\"),
        ]
        for dx, dy, ch in compass:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < W and 0 <= ny < H and self.terrain[ny][nx] in ("water", "deep_water"):
                if ch in ("N", "S", "E", "W"):
                    self.grid[ny][nx] = ch
                else:
                    self.grid[ny][nx] = ch if self.cfg.unicode else ch
        # Center dot
        if 0 <= cy < H and 0 <= cx < W:
            self.grid[cy][cx] = "+" if not self.cfg.unicode else "✦"

    def _add_ship(self):
        """Add a ship on the water with a name label."""
        W, H = self.cfg.width, self.cfg.height
        # Find water on right or bottom side
        candidates = []
        for y in range(H // 2, H):
            for x in range(W // 2, W):
                if self.terrain[y][x] in ("water", "deep_water"):
                    candidates.append((x, y))
        if candidates:
            sx, sy = random.choice(candidates)
            self.grid[sy][sx] = self.sym["ship"]
            # Label the ship
            ship_names = ["The Black Pearl", "Sea Viper", "Widow Maker", "Iron Tide", "Ghost Galleon"]
            name = random.choice(ship_names)
            lx = max(0, sx - len(name) - 1)
            self._add_annotation(lx, sy, name)

    def _add_danger_markers(self):
        """Add skull/cross danger markers near treacherous areas."""
        W, H = self.cfg.width, self.cfg.height
        # Place skull markers near volcano or swamp
        danger_count = 0
        for y in range(2, H - 2):
            for x in range(2, W - 2):
                if danger_count >= 2:
                    break
                if self.terrain[y][x] in ("volcano", "lava") and random.random() < 0.15:
                    # Place a skull near the volcano
                    for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and self.terrain[ny][nx] in ("mountain", "grass", "sand"):
                            self.grid[ny][nx] = self.sym["skull"]
                            danger_count += 1
                            break
                elif self.terrain[y][x] == "swamp" and random.random() < 0.03:
                    for dy, dx in [(0, 1), (1, 0)]:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and self.terrain[ny][nx] == "swamp":
                            self.grid[ny][nx] = self.sym["skull"]
                            danger_count += 1
                            break

    def get_terrain_stats(self) -> Dict[str, int]:
        """Calculate terrain statistics for the generated map."""
        W, H = self.cfg.width, self.cfg.height
        counts: Dict[str, int] = {}
        total = W * H
        for y in range(H):
            for x in range(W):
                t = self.terrain[y][x]
                counts[t] = counts.get(t, 0) + 1
        # Convert to percentages, ensuring they sum to exactly 100
        stats: Dict[str, int] = {}
        remaining_pct = 100
        sorted_types = sorted(counts.keys())
        for i, t in enumerate(sorted_types):
            if i == len(sorted_types) - 1:
                # Last type gets the remaining percentage to avoid rounding drift
                stats[t] = remaining_pct
            else:
                pct = round(counts[t] / total * 100)
                stats[t] = pct
                remaining_pct -= pct
        return stats

    def get_trail_distance(self) -> Optional[int]:
        """Return the approximate Manhattan distance from landing to treasure."""
        if self.landing_x is None or self.treasure_x is None:
            return None
        if self.landing_y is None or self.treasure_y is None:
            return None
        return abs(self.treasure_x - self.landing_x) + abs(self.treasure_y - self.landing_y)

    def generate_riddle(self) -> str:
        """Generate a pirate riddle clue, context-aware when possible.

        If landmarks were placed on the map, the riddle will reference them.
        """
        # Context-aware riddle templates that reference actual map features
        peak_names = [n for n in self.landmark_names_placed if "Peak" in n or "Mountain" in n
                      or "Spire" in n or "Thumb" in n or "Thunder" in n or "Doom" in n
                      or "Cauldron" in n or "Fire" in n or "Breath" in n]
        forest_names = [n for n in self.landmark_names_placed if "wood" in n.lower() or "Forest" in n
                        or "Hollow" in n or "Glen" in n or "Copse" in n or "Grove" in n
                        or "Thicket" in n or "Jungle" in n or "Bramble" in n or "Tangle" in n]
        beach_names = [n for n in self.landmark_names_placed if "Beach" in n or "Cove" in n
                       or "Bay" in n or "shore" in n.lower()]
        swamp_names = [n for n in self.landmark_names_placed if "Mire" in n or "Bog" in n
                       or "Marsh" in n or "Swamp" in n or "Fen" in n]

        # Distance hint
        dist = self.get_trail_distance()
        dist_hint = ""
        if dist is not None:
            # Convert to "paces" — rough pirate measurement
            paces = dist * 5
            if paces < 50:
                dist_hint = f"\nNo more than {paces} paces from shore to gold,"
            else:
                dist_hint = f"\n{paces} paces walk from where the anchor's laid,"

        # Context-aware riddles
        context_riddles = []

        if peak_names:
            peak = peak_names[0]
            context_riddles.append(
                f"Seek the shadow of {peak},\n"
                f"Where the earth meets the sky,\n"
                f"Dig beneath the ancient stone,{dist_hint[1:] if dist_hint else ''}\n"
                f"And the treasure shall not lie."
            )

        if forest_names:
            forest = forest_names[0]
            riddle = (
                f"Beneath the boughs of {forest},\n"
                f"Where shadows dance and play,"
            )
            if dist_hint:
                riddle += dist_hint + "\n"
            riddle += "The treasure waits for those who dare\nTo find it on this day."
            context_riddles.append(riddle)

        if beach_names:
            beach = beach_names[0]
            context_riddles.append(
                f"From the sands of {beach},\n"
                f"Walk inland brave and true,{dist_hint[1:] if dist_hint else ''}\n"
                f"Past the markers of the dead,\n"
                f"The gold awaits for you."
            )

        if swamp_names:
            swamp = swamp_names[0]
            context_riddles.append(
                f"Through the mists of {swamp},\n"
                f"Where the living dare not tread,{dist_hint[1:] if dist_hint else ''}\n"
                f"Past the bones and through the fog,\n"
                f"Lies the treasure of the dead."
            )

        # Generic fallback riddles (original)
        generic_riddles = [
            "Where the bones of sailors sleep,\nAnd salty tears the shore doth keep,\nWalk the path of whispered dread,\nPast the markers of the dead.",
            "Through the wood where ravens cry,\nUnderneath the darkened sky,\nSeek the stone that weeps with rain,\nThere to dig and break the chain.",
            "Count thy paces from the shore,\nThree score steps and then ten more,\nTurn thy face toward the peak,\nDig where roots and shadows speak.",
            "Past the cove where ships have bled,\nThrough the vale of pirate dead,\nWhere the mountain meets the sea,\nThere the gold awaits for thee.",
            "When the moonlight strikes the hill,\nAnd the waves are calm and still,\nMark the spot where shadows cross,\nDig beneath the bed of moss.",
            "From the anchor follow west,\nWhere the forest meets its rest,\nTwenty paces past the tree,\nGold and glory wait for thee.",
            "Beneath the peak where ravens nest,\nPast the shore of endless rest,\nWhere the trail of dots doth end,\nLie the bones of my old friend.",
            "Seek the isle where serpents dwell,\nPast the waters dark as hell,\nWhere the compass points to shore,\nDig beneath the sandy floor.",
        ]

        # Prefer context-aware riddle, fall back to generic
        all_riddles = context_riddles + generic_riddles
        return random.choice(all_riddles)

    def generate_legend(self) -> str:
        """Generate a map legend showing all terrain symbols."""
        sym = self.sym
        lines = [
            f"  {sym['deep_water']} Deep Water   {sym['water']} Shallow Water   {sym['sand']} Beach/Sand",
            f"  {sym['grass']} Grassland     {sym['forest']} Forest          {sym['mountain']} Mountain",
            f"  {sym['peak']} Peak          {sym['x_mark']} Treasure         {sym['trail_dot']} Trail",
            f"  {sym['anchor']} Landing      {sym['ship']} Ship             {sym['skull']} Danger",
            f"  {sym['swamp']} Swamp        {sym['volcano']} Volcano          {sym['lava']} Lava Flow",
        ]
        return "\n".join(lines)

    def render(self) -> str:
        """Render the final map as a bordered string."""
        W, H = self.cfg.width, self.cfg.height
        # Create a copy of the grid for rendering
        display = [row[:] for row in self.grid]

        # Resolve annotation collisions
        resolved = self._resolve_annotation_collisions(self.annotations, W, H)

        # Overlay annotations (labels on top of terrain)
        # But protect the treasure X marker from being overwritten
        for ax, ay, text in resolved:
            for i, ch in enumerate(text):
                tx = ax + i
                if 0 <= tx < W and 0 <= ay < H:
                    # Protect treasure X from being overwritten by labels
                    if self.treasure_x is not None and self.treasure_y is not None:
                        if tx == self.treasure_x and ay == self.treasure_y:
                            continue
                    display[ay][tx] = ch

        # Ensure treasure X is still visible
        if self.treasure_x is not None and self.treasure_y is not None:
            if 0 <= self.treasure_x < W and 0 <= self.treasure_y < H:
                display[self.treasure_y][self.treasure_x] = self.sym["x_mark"]

        # Build the lines
        lines = []
        # Top border
        lines.append(self.sym["corner_tl"] + self.sym["border_h"] * W + self.sym["corner_tr"])

        for y in range(H):
            row = self.sym["border_v"] + "".join(display[y]) + self.sym["border_v"]
            lines.append(row)

        # Bottom border
        lines.append(self.sym["corner_bl"] + self.sym["border_h"] * W + self.sym["corner_br"])

        return "\n".join(lines)

    def _resolve_annotation_collisions(self, annotations, W, H):
        """Resolve overlapping annotations by nudging labels to different rows."""
        if not annotations:
            return annotations

        # Sort by y, then by x
        sorted_annots = sorted(annotations, key=lambda a: (a[1], a[0]))
        resolved = []

        # Track occupied intervals per row: row -> list of (start_x, end_x)
        row_intervals = {}

        for ax, ay, text in sorted_annots:
            label_len = len(text)
            end_x = ax + label_len
            current_y = ay

            # Try placing on this row, then shift down/up if collision
            placed = False
            for dy_offset in range(0, 5):
                for try_y in [current_y + dy_offset, current_y - dy_offset]:
                    if try_y < 0 or try_y >= H:
                        continue
                    if try_y not in row_intervals:
                        row_intervals[try_y] = []
                    # Check for overlap with existing labels on this row
                    overlaps = False
                    for (sx, ex) in row_intervals[try_y]:
                        if ax < ex and end_x > sx:
                            overlaps = True
                            break
                    if not overlaps:
                        row_intervals.setdefault(try_y, []).append((ax, end_x))
                        resolved.append((ax, try_y, text))
                        placed = True
                        break
                if placed:
                    break

            if not placed:
                resolved.append((ax, ay, text))

        return resolved


def main():
    parser = argparse.ArgumentParser(
        description="🗺️  Procedural Treasure Map Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python treasure_map.py                          # Random map
  python treasure_map.py --seed 42                 # Reproducible map
  python treasure_map.py --width 90 --height 40    # Larger map
  python treasure_map.py --no-unicode              # ASCII-only output
  python treasure_map.py --riddle                  # Include a pirate riddle
  python treasure_map.py --legend                  # Include a map legend
  python treasure_map.py --stats                   # Show terrain statistics
  python treasure_map.py --difficulty hard         # Harder (smaller islands)
  python treasure_map.py --count 3                 # Generate 3 maps
  python treasure_map.py --save map.txt            # Save output to file
        """
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--width", type=int, default=72, help="Map width (default: 72)")
    parser.add_argument("--height", type=int, default=34, help="Map height (default: 34)")
    parser.add_argument("--no-unicode", action="store_true", help="Use ASCII-only symbols")
    parser.add_argument("--riddle", action="store_true", help="Include a pirate riddle")
    parser.add_argument("--legend", action="store_true", help="Include a map legend")
    parser.add_argument("--stats", action="store_true", help="Show terrain statistics")
    parser.add_argument("--count", type=int, default=1, help="Number of maps to generate")
    parser.add_argument("--difficulty", choices=["easy", "normal", "hard"], default="normal",
                        help="Difficulty preset: easy (big islands), normal, hard (tiny atolls)")
    parser.add_argument("--save", type=str, default=None,
                        help="Save output to a file instead of stdout")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    # Validate dimensions
    if args.width < 5 or args.height < 3:
        print(f"Error: Map dimensions too small (minimum 5x3), got {args.width}x{args.height}", file=sys.stderr)
        sys.exit(1)
    if args.width > 200 or args.height > 100:
        print(f"Warning: Large map dimensions ({args.width}x{args.height}) may produce cluttered output", file=sys.stderr)

    output_lines = []

    for i in range(args.count):
        seed = args.seed + i if args.seed is not None else None
        config = MapConfig(
            width=args.width,
            height=args.height,
            seed=seed,
            unicode=not args.no_unicode,
            difficulty=args.difficulty,
        )
        tmap = TreasureMap(config)
        sym = tmap.sym

        output_lines.append("")
        if not args.no_unicode:
            output_lines.append("  ╔══════════════════════════════════════╗")
            output_lines.append("  ║   TREASURE MAP — Seed {:>6d}        ║".format(tmap.seed))
            output_lines.append("  ╚══════════════════════════════════════╝")
        else:
            output_lines.append("  +======================================+")
            output_lines.append("  |   TREASURE MAP - Seed {:>6d}        |".format(tmap.seed))
            output_lines.append("  +======================================+")
        output_lines.append("")

        # Show difficulty label if not normal
        if args.difficulty != "normal":
            diff_label = args.difficulty.upper()
            preset = DIFFICULTY_PRESETS[args.difficulty]
            output_lines.append(f"  Difficulty: {diff_label} — {preset['description']}")
            output_lines.append("")

        output_lines.append(tmap.render())
        output_lines.append("")

        # Show distance from landing to treasure
        dist = tmap.get_trail_distance()
        if dist is not None:
            paces = dist * 5
            output_lines.append(f"  📏 Estimated distance: ~{paces} paces from landing to treasure")
            output_lines.append("")

        if args.stats:
            stats = tmap.get_terrain_stats()
            output_lines.append("  ── Terrain Statistics ──")
            terrain_display = {
                "deep_water": "Deep Water",
                "water": "Shallow Water",
                "sand": "Beach/Sand",
                "grass": "Grassland",
                "forest": "Forest",
                "dense_forest": "Dense Forest",
                "mountain": "Mountain",
                "peak": "Peak",
                "swamp": "Swamp",
                "volcano": "Volcano",
                "lava": "Lava Flow",
            }
            for terrain_type, pct in sorted(stats.items(), key=lambda x: -x[1]):
                display_name = terrain_display.get(terrain_type, terrain_type)
                symbol = tmap.sym.get(terrain_type, "?")
                bar = "█" * pct
                output_lines.append(f"    {symbol} {display_name:<14s} {pct:>3d}% {bar}")
            output_lines.append("")

        if args.riddle:
            if not args.no_unicode:
                output_lines.append("  ┌──────────────────────────────────────┐")
                output_lines.append("  │          PIRATE'S RIDDLE               │")
                output_lines.append("  └──────────────────────────────────────┘")
            else:
                output_lines.append("  +--------------------------------------+")
                output_lines.append("  |          PIRATE'S RIDDLE             |")
                output_lines.append("  +--------------------------------------+")
            output_lines.append("")
            for line in tmap.generate_riddle().split("\n"):
                output_lines.append(f"      {line}")
            output_lines.append("")

        if args.legend:
            output_lines.append("")
            if not args.no_unicode:
                output_lines.append("  ┌──────── LEGEND ────────┐")
                output_lines.append(tmap.generate_legend())
                output_lines.append("  └─────────────────────────┘")
            else:
                output_lines.append("  +-------- LEGEND ----------+")
                output_lines.append(tmap.generate_legend())
                output_lines.append("  +---------------------------+")
            output_lines.append("")

        if args.count > 1:
            output_lines.append("=" * (args.width + 2))
            output_lines.append("")

    full_output = "\n".join(output_lines)

    if args.save:
        # Save to file
        try:
            with open(args.save, "w", encoding="utf-8") as f:
                f.write(full_output)
            print(f"Map saved to {args.save}")
        except OSError as e:
            print(f"Error saving to {args.save}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(full_output)


if __name__ == "__main__":
    main()