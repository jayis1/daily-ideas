#!/usr/bin/env python3
"""
Procedural Treasure Map Generator
===================================
Generates elaborate ASCII treasure maps with coastlines, terrain features,
dotted trails, compass roses, sea monsters, pirate riddles, and X-marks-the-spot.
Each map is unique — seeded or random.

Version: 1.1.0
"""

import random
import math
import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


# ── Version ──────────────────────────────────────────────────────────────────

__version__ = "1.1.0"

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
    return a + (b - a) * t


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def noise_2d(x, y, seed=0):
    """Simple deterministic hash-based pseudo-noise."""
    n = int(x * 374761393 + y * 668265263 + seed * 1013904223)
    n = ((n >> 13) ^ n)
    n = (n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff
    return (n & 0xffff) / 0xffff


def smooth_noise(x, y, seed=0, scale=0.08):
    """Bilinearly interpolated smooth noise."""
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
    """Fractal Brownian Motion — layered noise for terrain generation."""
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
    width: int = 72
    height: int = 34
    seed: Optional[int] = None
    water_level: float = 0.38
    sand_level: float = 0.44
    grass_level: float = 0.56
    forest_level: float = 0.68
    mountain_level: float = 0.82
    unicode: bool = True


class TreasureMap:
    def __init__(self, config: MapConfig):
        self.cfg = config
        if config.seed is not None:
            random.seed(config.seed)
        self.seed = config.seed if config.seed is not None else random.randint(0, 999999)
        random.seed(self.seed)
        self.sym = SYMBOLS if config.unicode else SIMPLE_SYMBOLS
        self.grid: List[List[str]] = []
        self.terrain: List[List[str]] = []  # terrain type per cell
        self.annotations: List[Tuple[int, int, str]] = []  # overlaid labels
        self.treasure_x: Optional[int] = None
        self.treasure_y: Optional[int] = None
        self.landing_x: Optional[int] = None
        self.landing_y: Optional[int] = None
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
                # Try shifting right first
                new_x = tx + 2
                if new_x + len(text) <= W:
                    x = new_x
                else:
                    # Try shifting left so the label ends before the treasure
                    new_x = tx - len(text) - 1
                    if new_x >= 0:
                        x = new_x
                    # If neither works, keep original clamped position (best effort)

        self.annotations.append((x, y, text))

    def _generate(self):
        W, H = self.cfg.width, self.cfg.height
        # 1. Generate heightmap
        heightmap = [[0.0] * W for _ in range(H)]
        # Use two noise layers — one for continent shape, one for detail
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
        self._place_treasure(heightmap)
        self._draw_trail(heightmap)
        self._add_landmarks(heightmap)
        self._add_sea_creatures()
        self._add_compass_rose()
        self._add_ship()

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
                                # Use shallow water symbol (not hardcoded "~")
                                self.grid[y][x] = self.sym["water"]
                                break

    def _add_lake_if_possible(self, heightmap):
        """Sometimes add an inland lake."""
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
                    # Use the symbol dict, not hardcoded "~"
                    self.grid[y][x] = self.sym["water"]

    def _place_treasure(self, heightmap):
        """Place the treasure X on land, preferably inland."""
        W, H = self.cfg.width, self.cfg.height
        land_cells = []
        for y in range(3, H - 3):
            for x in range(3, W - 3):
                if self.terrain[y][x] in ("grass", "forest", "dense_forest", "sand"):
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
        # Pick from top candidates with some randomness
        top = land_cells[:max(1, len(land_cells) // 5)]
        chosen = random.choice(top)
        self.treasure_x, self.treasure_y = chosen[0], chosen[1]
        self.grid[self.treasure_y][self.treasure_x] = self.sym["x_mark"]

        # Add "Here be treasure!" annotation near the X
        # Bug fix: label is 17 chars long, not 15; use proper bounds check
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
        # so the landing point is always distinct from the treasure
        tx, ty = self.treasure_x, self.treasure_y
        valid_beach = [(x, y) for x, y in beach_cells if (x, y) != (tx, ty)]
        if not valid_beach:
            # All beach cells overlap with treasure — expand search to any
            # non-water cell adjacent to water that isn't the treasure
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
            # Still no valid landing — skip trail drawing
            self.landing_x, self.landing_y = None, None
            return

        start = random.choice(valid_beach)
        self.landing_x, self.landing_y = start[0], start[1]

        # Mark the landing with an anchor symbol
        # Find the water cell adjacent to landing
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = self.landing_y + dy, self.landing_x + dx
            if 0 <= ny < H and 0 <= nx < W and self.terrain[ny][nx] in ("water", "deep_water"):
                self.grid[ny][nx] = self.sym["anchor"]
                break

        # Walk from landing to treasure using a simple path
        # Use a randomized walk that prefers the direction toward the treasure
        path = self._find_path(start, (self.treasure_x, self.treasure_y))
        for i, (px, py) in enumerate(path):
            if self.terrain[py][px] not in ("water", "deep_water") and self.grid[py][px] != self.sym["x_mark"]:
                # Dotted trail — use symbol dict, not hardcoded "·"
                if i % 2 == 0:
                    self.grid[py][px] = self.sym["trail_dot"]
                else:
                    self.grid[py][px] = self.sym["trail_dot"]

    def _find_path(self, start, end):
        """Simple greedy path with randomness for a winding trail."""
        W, H = self.cfg.width, self.cfg.height
        x, y = start
        path = []
        visited = set()
        max_steps = 500
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
                # Stuck — just break
                break
            scored.sort(key=lambda s: s[0])
            # Pick best with some randomness
            pick = random.choice(scored[:3]) if len(scored) > 2 else scored[0]
            x, y = pick[1], pick[2]
            visited.add((x, y))
            path.append((x, y))
        return path

    def _add_landmarks(self, heightmap):
        """Add named landmarks: mountains, forests, bays, coves, etc."""
        W, H = self.cfg.width, self.cfg.height
        landmark_names = {
            "peak": ["Dragon's Peak", "Skull Mountain", "The Spire", "Witch's Needle", "Giant's Thumb", "Old Thunder"],
            "forest": ["Darkwood", "Whispering Forest", "Goblin Hollow", "Spider's Glen", "Deadman's Copse", "Hangman's Grove"],
            "dense_forest": ["Blackwood Deep", "Demon's Thicket", "Serpent Jungle", "The Bramble", "Cursed Tangle"],
            "sand": ["Dead Man's Beach", "Serpent's Cove", "Smuggler's Bay", "Boneshore", "Wreck Beach"],
            "swamp": ["Mire of Souls", "Bogwater", "Dead Marsh"],
            "mountain": ["Iron Hills", "Stoneback Ridge", "Cragmoor"],
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
                        self._add_annotation(x + 1, max(y - 1, 0), name)
                        placed += 1

        # Try to label a forest area
        forest_cells = [(x, y) for y in range(H) for x in range(W) if self.terrain[y][x] in ("forest", "dense_forest")]
        if forest_cells and placed < 5:
            fx, fy = random.choice(forest_cells)
            ftype = "forest" if self.terrain[fy][fx] == "forest" else "dense_forest"
            name = random.choice(landmark_names.get(ftype, ["Woods"]))
            while name in used_names:
                name = random.choice(landmark_names.get(ftype, ["Woods"]))
            used_names.add(name)
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
            self._add_annotation(bx + 1, max(by - 1, 0), name)
            placed += 1

    def _add_sea_creatures(self):
        """Add sea monsters and waves in open water."""
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
            # Place 1-2 sea creatures
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
        # Try top-left corner area
        cx, cy = 6, 3
        # Check if area is water
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
        """Add a ship on the water."""
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
            # Label the ship — use _add_annotation for bounds checking
            ship_names = ["The Black Pearl", "Sea Viper", "Widow Maker", "Iron Tide", "Ghost Galleon"]
            name = random.choice(ship_names)
            lx = max(0, sx - len(name) - 1)
            self._add_annotation(lx, sy, name)

    def render(self) -> str:
        """Render the final map as a string."""
        W, H = self.cfg.width, self.cfg.height
        # Create a copy of the grid for rendering
        display = [row[:] for row in self.grid]

        # Resolve annotation collisions: detect overlapping label rows and nudge them
        # Sort annotations by row, then by start x
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
            # Try original position
            end_x = ax + label_len
            current_y = ay

            # Try placing on this row, then shift down/up if collision
            placed = False
            for dy_offset in range(0, 5):  # Try original row, then shift down
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
                # If we can't resolve collision, just place it anyway
                resolved.append((ax, ay, text))

        return resolved

    def generate_riddle(self) -> str:
        """Generate a pirate riddle clue for the treasure."""
        riddles = [
            "Where the bones of sailors sleep,\nAnd salty tears the shore doth keep,\nWalk the path of whispered dread,\nPast the markers of the dead.",
            "Through the wood where ravens cry,\nUnderneath the darkened sky,\nSeek the stone that weeps with rain,\nThere to dig and break the chain.",
            "Count thy paces from the shore,\nThree score steps and then ten more,\nTurn thy face toward the peak,\nDig where roots and shadows speak.",
            "Past the cove where ships have bled,\nThrough the vale of pirate dead,\nWhere the mountain meets the sea,\nThere the gold awaits for thee.",
            "When the moonlight strikes the hill,\nAnd the waves are calm and still,\nMark the spot where shadows cross,\nDig beneath the bed of moss.",
            "From the anchor follow west,\nWhere the forest meets its rest,\nTwenty paces past the tree,\nGold and glory wait for thee.",
            "Beneath the peak where ravens nest,\nPast the shore of endless rest,\nWhere the trail of dots doth end,\nLie the bones of my old friend.",
            "Seek the isle where serpents dwell,\nPast the waters dark as hell,\nWhere the compass points to shore,\nDig beneath the sandy floor.",
        ]
        return random.choice(riddles)

    def generate_legend(self) -> str:
        """Generate a map legend."""
        sym = self.sym
        lines = [
            f"  {sym['deep_water']} Deep Water   {sym['water']} Shallow Water   {sym['sand']} Beach/Sand",
            f"  {sym['grass']} Grassland     {sym['forest']} Forest          {sym['mountain']} Mountain",
            f"  {sym['peak']} Peak          {sym['x_mark']} Treasure         {sym['trail_dot']} Trail",
            f"  {sym['anchor']} Landing      {sym['ship']} Ship             {sym['skull']} Danger",
        ]
        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="🗺️  Procedural Treasure Map Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python treasure_map.py                    # Random map
  python treasure_map.py --seed 42          # Reproducible map
  python treasure_map.py --width 90 --height 40   # Larger map
  python treasure_map.py --no-unicode       # ASCII-only output
  python treasure_map.py --riddle           # Include a pirate riddle
  python treasure_map.py --count 3          # Generate 3 maps
        """
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--width", type=int, default=72, help="Map width (default: 72)")
    parser.add_argument("--height", type=int, default=34, help="Map height (default: 34)")
    parser.add_argument("--no-unicode", action="store_true", help="Use ASCII-only symbols")
    parser.add_argument("--riddle", action="store_true", help="Include a pirate riddle")
    parser.add_argument("--legend", action="store_true", help="Include a map legend")
    parser.add_argument("--count", type=int, default=1, help="Number of maps to generate")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    args = parser.parse_args()

    for i in range(args.count):
        seed = args.seed + i if args.seed is not None else None
        config = MapConfig(
            width=args.width,
            height=args.height,
            seed=seed,
            unicode=not args.no_unicode,
        )
        tmap = TreasureMap(config)
        sym = tmap.sym

        print()
        if not args.no_unicode:
            print("  ╔══════════════════════════════════════╗")
            print("  ║   TREASURE MAP — Seed {:>6d}        ║".format(tmap.seed))
            print("  ╚══════════════════════════════════════╝")
        else:
            print("  +======================================+")
            print("  |   TREASURE MAP - Seed {:>6d}        |".format(tmap.seed))
            print("  +======================================+")
        print()
        print(tmap.render())
        print()

        if args.riddle:
            if not args.no_unicode:
                print("  ┌──────────────────────────────────────┐")
                print("  │          PIRATE'S RIDDLE               │")
                print("  └──────────────────────────────────────┘")
            else:
                print("  +--------------------------------------+")
                print("  |          PIRATE'S RIDDLE             |")
                print("  +--------------------------------------+")
            print()
            for line in tmap.generate_riddle().split("\n"):
                print(f"      {line}")
            print()

        if args.legend:
            print()
            if not args.no_unicode:
                print("  ┌──────── LEGEND ────────┐")
                print(tmap.generate_legend())
                print("  └─────────────────────────┘")
            else:
                print("  +-------- LEGEND ----------+")
                print(tmap.generate_legend())
                print("  +---------------------------+")
            print()

        if args.count > 1:
            print("=" * (args.width + 2))
            print()


if __name__ == "__main__":
    main()