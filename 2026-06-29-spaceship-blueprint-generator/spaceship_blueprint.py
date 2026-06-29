#!/usr/bin/env python3
"""
Procedural Spaceship Blueprint Generator
==========================================
Generates detailed ASCII spaceship cross-sections with labeled rooms,
ship specifications, crew manifests, and system diagrams.

Each run produces a unique spaceship with different class, configuration,
and crew. Multiple output modes: blueprint, schematic, and stats.
"""

import random
import math
import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum


class ShipClass(Enum):
    CORVETTE = ("Corvette", (12, 20), (4, 7), (3, 8), 1)
    FRIGATE = ("Frigate", (20, 30), (7, 12), (8, 20), 2)
    DESTROYER = ("Destroyer", (30, 45), (10, 18), (20, 50), 3)
    CRUISER = ("Cruiser", (45, 60), (15, 22), (50, 120), 4)
    BATTLESHIP = ("Battleship", (55, 75), (18, 28), (120, 300), 5)
    CARRIER = ("Carrier", (60, 80), (20, 30), (100, 500), 6)
    DREADNOUGHT = ("Dreadnought", (75, 100), (25, 40), (300, 800), 7)
    STATION = ("Station", (40, 60), (40, 60), (500, 5000), 8)

    def __init__(self, label, length_range, width_range, crew_range, tier):
        self.label = label
        self.length_range = length_range
        self.width_range = width_range
        self.crew_range = crew_range
        self.tier = tier


SHIP_CLASSES = list(ShipClass)

HULL_NAMES = {
    ShipClass.CORVETTE: [
        "Stinger", "Wasp", "Mantis", "Viper", "Needle", "Dart",
        "Shiv", "Thorn", "Scorpion", "Adder"
    ],
    ShipClass.FRIGATE: [
        "Sentinel", "Vigilant", "Warden", "Watchman", "Guardian",
        "Defender", "Protector", "Aegis", "Bulwark", "Shield"
    ],
    ShipClass.DESTROYER: [
        "Reaper", "Scythe", "Annihilator", "Devastator", "Ravager",
        "Obliterator", "Eraser", "Vortex", "Tempest", "Maelstrom"
    ],
    ShipClass.CRUISER: [
        "Endeavour", "Voyager", "Odyssey", "Peregrine", "Nomad",
        "Wanderer", "Pioneer", "Meridian", "Zenith", "Apex"
    ],
    ShipClass.BATTLESHIP: [
        "Dominator", "Sovereign", "Titan", "Leviathan", "Colossus",
        "Behemoth", "Monolith", "Juggernaut", "Ironheart", "Doomhammer"
    ],
    ShipClass.CARRIER: [
        "Nest", "Hive", "Crèche", "Ark", "Haven",
        "Sanctuary", "Roost", "Aerie", "Refuge", "Vessel"
    ],
    ShipClass.DREADNOUGHT: [
        "Abyssal", "Calamity", "Cataclysm", "Extinction", "Apocalypse",
        "Oblivion", "Entropy", "Omega", "Terminus", "Infinity"
    ],
    ShipClass.STATION: [
        "Outpost", "Beacon", "Citadel", "Anchor", "Hearth",
        "Nexus", "Crossroads", "Harbor", "Lighthouse", "Sanctum"
    ],
}

REGISTRY_PREFIXES = [
    "ISS", "USS", "HMS", "ICS", "ESS", "CVS", "DSV", "KSS",
    "RTS", "TFS", "ANS", "VSS", "NRS", "JMC", "WGS"
]

ROOM_TYPES = {
    "bridge": {"sym": "⬡", "priority": 10, "min_tier": 1, "label": "Bridge"},
    "engineering": {"sym": "⚙", "priority": 9, "min_tier": 1, "label": "Engineering"},
    "reactor": {"sym": "☢", "priority": 9, "min_tier": 1, "label": "Reactor Core"},
    "medbay": {"sym": "✚", "priority": 7, "min_tier": 1, "label": "Medical Bay"},
    "quarters": {"sym": "⚐", "priority": 6, "min_tier": 1, "label": "Crew Quarters"},
    "cargo": {"sym": "▣", "priority": 5, "min_tier": 1, "label": "Cargo Hold"},
    "armory": {"sym": "⚔", "priority": 5, "min_tier": 2, "label": "Armory"},
    "science": {"sym": "⚗", "priority": 4, "min_tier": 2, "label": "Science Lab"},
    "hangar": {"sym": "▽", "priority": 6, "min_tier": 2, "label": "Hangar Bay"},
    "shields": {"sym": "◈", "priority": 7, "min_tier": 2, "label": "Shield Generator"},
    "comms": {"sym": "◎", "priority": 7, "min_tier": 1, "label": "Comms Array"},
    "life_support": {"sym": "♣", "priority": 8, "min_tier": 1, "label": "Life Support"},
    "nav": {"sym": "⊛", "priority": 8, "min_tier": 1, "label": "Navigation"},
    "lounge": {"sym": "♦", "priority": 3, "min_tier": 3, "label": "Crew Lounge"},
    "hydroponics": {"sym": "❋", "priority": 3, "min_tier": 4, "label": "Hydroponics"},
    "brig": {"sym": "▦", "priority": 4, "min_tier": 3, "label": "Brig"},
    "war_room": {"sym": "⊞", "priority": 5, "min_tier": 4, "label": "War Room"},
    "officer_quarters": {"sym": "♕", "priority": 4, "min_tier": 3, "label": "Officer Quarters"},
    "shuttle_bay": {"sym": "◁", "priority": 5, "min_tier": 3, "label": "Shuttle Bay"},
    "fabricator": {"sym": "⚙", "priority": 3, "min_tier": 4, "label": "Fabricator"},
    "engine_room": {"sym": "⊳", "priority": 9, "min_tier": 1, "label": "Engine Room"},
}

RANK_TITLES = {
    ShipClass.CORVETTE: ["Captain", "First Mate", "Helmsman", "Engineer", "Gunner"],
    ShipClass.FRIGATE: ["Captain", "Commander", "Lieutenant", "Chief Engineer", "Gunnery Officer", "Comms Officer"],
    ShipClass.DESTROYER: ["Captain", "Commander", "Lieutenant Commander", "Lieutenant", "Chief Engineer", "Tactical Officer", "Comms Officer"],
    ShipClass.CRUISER: ["Captain", "Commander", "Lieutenant Commander", "Lieutenant", "Ensign", "Chief Engineer", "Tactical Officer", "Science Officer", "Comms Officer", "Chief Medical Officer"],
    ShipClass.BATTLESHIP: ["Admiral", "Captain", "Commander", "Lieutenant Commander", "Lieutenant", "Ensign", "Chief Engineer", "Tactical Officer", "Science Officer", "Comms Officer", "Chief Medical Officer", "Security Chief"],
    ShipClass.CARRIER: ["Admiral", "Captain", "Commander", "Wing Commander", "Lieutenant Commander", "Lieutenant", "Chief Engineer", "Flight Controller", "Deck Officer", "Comms Officer", "Chief Medical Officer"],
    ShipClass.DREADNOUGHT: ["Fleet Admiral", "Vice Admiral", "Rear Admiral", "Captain", "Commander", "Lieutenant Commander", "Lieutenant", "Chief Engineer", "Tactical Officer", "Science Officer", "Security Chief", "Chief Medical Officer", "Comms Officer"],
    ShipClass.STATION: ["Station Commander", "Deputy Commander", "Operations Chief", "Chief Engineer", "Security Chief", "Chief Medical Officer", "Dock Master", "Comms Director", "Science Director", "Quartermaster"],
}

FIRST_NAMES = [
    "James", "Elena", "Viktor", "Amara", "Chen", "Fatima", "Hiroshi", "Sofia",
    "Marcus", "Zara", "Ivan", "Priya", "Liam", "Nadia", "Dmitri", "Yuki",
    "Olga", "Rashid", "Kira", "Anders", "Mei", "Tariq", "Fiona", "Kwame",
    "Ingrid", "Carlos", "Aisha", "Nikolai", "Sato", "Mariana", "Oleg", "Leila",
    "Rafael", "Sigrid", "Omari", "Helena", "Jin", "Valentina", "Erik", "Nneka",
    "Arjun", "Svetlana", "Hassan", "Freya", "Ravi", "Isolde", "Kenji", "Astrid"
]

LAST_NAMES = [
    "Volkov", "Chen", "Okafor", "Petrov", "Singh", "Mueller", "Tanaka", "Santos",
    "Kim", "Fischer", "Abadi", "Johansson", "Nakamura", "Silva", "Patel", "Andersen",
    "Morales", "Weber", "Park", "Fernandez", "Lindqvist", "Yamamoto", "Diallo",
    "Kowalski", "Ibrahim", "Berg", "Reyes", "Novak", "Chang", "Okonkwo", "Ström",
    "Vasquez", "Larsen", "Mensah", "Kozlov", "Hoffman", "Matsuda", "Torres", "Aliyev"
]

SPECIES = [
    "Human", "Human", "Human", "Human", "Human",  # Humans more common
    "Theraxian", "Zel'vori", "Krythian", "Aurelian", "Myr-dhala",
    "Veskari", "Olonqi", "Synth-7", "Tennari"
]

SHIP_FACTIONS = [
    "Terran Alliance", "Mars Consortium", "Outer Rim Coalition",
    "Veskari Dominion", "Independent Traders Guild", "Aurelian Empire",
    "Free Systems Alliance", "Deep Space Authority", "Krythian Republic",
    "Corporate Sector Authority"
]

WEAPON_SYSTEMS = {
    ShipClass.CORVETTE: ["Twin Pulse Lasers", "Point Defense Turret", "Micro-Missile Pod"],
    ShipClass.FRIGATE: ["Quad Pulse Lasers", "Missile Battery", "Railgun Turret", "Flak Cannon"],
    ShipClass.DESTROYER: ["Heavy Railgun", "Missile Salvo Launcher", "Plasma Lance", "Torpedo Tubes"],
    ShipClass.CRUISER: ["Dual Plasma Cannons", "Guided Missile Array", "Particle Beam", "Defensive Flak Grid"],
    ShipClass.BATTLESHIP: ["Mega Plasma Cannon", "Siege Missile Array", "Quad Heavy Railguns", "Flak Curtain", "Nova Torpedo"],
    ShipClass.CARRIER: ["Point Defense Grid", "Flak Battery", "Intercept Drone Bay", "Guided Missiles"],
    ShipClass.DREADNOUGHT: ["Siege Plasma Array", "Super-Heavy Railguns", "Nova Torpedo Bay", "Orbital Bombardment Laser", "Flak Fortress"],
    ShipClass.STATION: ["Defense Grid", "Orbital Cannons", "Interceptor Missiles", "Point Defense Array"],
}

SHIELD_TYPES = {
    ShipClass.CORVETTE: ["Deflector Screen", "Micro-Shield"],
    ShipClass.FRIGATE: ["Standard Deflector", "Reinforced Screen"],
    ShipClass.DESTROYER: ["Military-Grade Deflector", "Tactical Shield"],
    ShipClass.CRUISER: ["Multi-Layer Deflector", "Regenerative Shield"],
    ShipClass.BATTLESHIP: ["Heavy Fortress Shield", "Layered Barrier"],
    ShipClass.CARRIER: ["Fleet Deflector Array", "Hangar Shield Dome"],
    ShipClass.DREADNOUGHT: ["Dreadnought Barrier", "Multi-Phase Fortress Shield"],
    ShipClass.STATION: ["Station-Scale Barrier", "Orbital Defense Shield"],
}

DRIVE_TYPES = {
    ShipClass.CORVETTE: ["Ion Thruster", "Chemical Drive"],
    ShipClass.FRIGATE: ["Ion Drive", "Pulse Thruster"],
    ShipClass.DESTROYER: ["Fusion Drive", "Ion Array"],
    ShipClass.CRUISER: ["Fusion Array", "Warp Coil Drive"],
    ShipClass.BATTLESHIP: ["Warp Core Drive", "Heavy Fusion Array"],
    ShipClass.CARRIER: ["Warp Core", "Fusion Array"],
    ShipClass.DREADNOUGHT: ["Dual Warp Core", "Quantum Drive"],
    ShipClass.STATION: ["Station-Keeping Thrusters", "Micro-Warp Stabilizer"],
}


@dataclass
class Room:
    room_type: str
    label: str
    x: int
    y: int
    w: int
    h: int
    sym: str


@dataclass
class CrewMember:
    name: str
    rank: str
    species: str
    role: str


@dataclass
class ShipSpec:
    name: str
    registry: str
    ship_class: ShipClass
    faction: str
    length_m: int
    width_m: int
    crew_count: int
    deck_count: int
    rooms: List[Room]
    weapons: List[str]
    shield: str
    drive: str
    crew_manifest: List[CrewMember]


def rand_range(r: Tuple[int, int]) -> int:
    return random.randint(r[0], r[1])


def generate_ship(specified_class: Optional[ShipClass] = None) -> ShipSpec:
    ship_class = specified_class or random.choice(SHIP_CLASSES)

    name = f"{random.choice(REGISTRY_PREFIXES)} {random.choice(HULL_NAMES[ship_class])}"
    registry = f"{random.choice(REGISTRY_PREFIXES)}-{random.randint(1000, 9999)}"
    faction = random.choice(SHIP_FACTIONS)

    length = rand_range(ship_class.length_range)
    width = rand_range(ship_class.width_range)
    crew = rand_range(ship_class.crew_range)
    deck_count = min(ship_class.tier + random.randint(0, 2), 10)

    # Generate rooms
    rooms = _generate_rooms(ship_class, length, width)
    weapons = random.sample(
        WEAPON_SYSTEMS[ship_class],
        k=min(random.randint(1, 3), len(WEAPON_SYSTEMS[ship_class]))
    )
    shield = random.choice(SHIELD_TYPES[ship_class])
    drive = random.choice(DRIVE_TYPES[ship_class])

    # Generate crew manifest
    manifest = _generate_crew(ship_class, crew)

    return ShipSpec(
        name=name, registry=registry, ship_class=ship_class,
        faction=faction, length_m=length, width_m=width,
        crew_count=crew, deck_count=deck_count, rooms=rooms,
        weapons=weapons, shield=shield, drive=drive,
        crew_manifest=manifest
    )


def _generate_rooms(ship_class: ShipClass, length: int, width: int) -> List[Room]:
    """Place rooms on the ship blueprint grid."""
    rooms = []
    tier = ship_class.tier

    # Determine which rooms are available at this tier
    available = {
        k: v for k, v in ROOM_TYPES.items()
        if v["min_tier"] <= tier
    }

    # Always include essential rooms
    essential = ["bridge", "engineering", "reactor", "life_support", "quarters", "cargo", "comms"]
    if ship_class.tier >= 2:
        essential.append("nav")
        essential.append("medbay")

    # Add random rooms based on ship size
    max_rooms = min(tier + random.randint(2, 5), len(available))
    all_types = list(available.keys())
    optional = [r for r in all_types if r not in essential]
    num_optional = max(0, min(max_rooms - len(essential), len(optional)))
    chosen_optional = random.sample(optional, k=num_optional) if num_optional > 0 else []
    chosen = essential + chosen_optional

    # Grid dimensions (scaled for ASCII display)
    grid_w = max(24, min(70, length // 2))
    grid_h = max(8, min(22, width // 2))

    # Create a grid to track occupied spaces
    grid = [[False] * grid_w for _ in range(grid_h)]

    # Ship shape: create an outline — pointed nose, wider middle
    def is_in_hull(gx, gy):
        # Nose is pointed, body widens, tail narrows slightly
        progress = gx / max(1, grid_w - 1)  # 0=nose, 1=tail
        # Width profile: starts narrow, expands, stays wide
        if progress < 0.15:
            half_width = (progress / 0.15) * (grid_h / 2 - 1) + 1
        elif progress < 0.7:
            half_width = grid_h / 2 - 1
        else:
            taper = (progress - 0.7) / 0.3
            half_width = (grid_h / 2 - 1) * (1 - 0.3 * taper)
        center = grid_h / 2
        return abs(gy - center) < half_width

    # Place rooms one by one
    placed = []
    # Sort chosen by priority (highest first for placement)
    chosen_sorted = sorted(chosen, key=lambda r: ROOM_TYPES[r]["priority"], reverse=True)

    for room_type in chosen_sorted:
        info = ROOM_TYPES[room_type]
        # Room size based on type
        rw = random.randint(3, min(7, grid_w // 3))
        rh = random.randint(2, min(4, grid_h // 3))
        if room_type == "bridge":
            rw = min(4, grid_w // 4)
            rh = min(2, grid_h // 4)
        elif room_type in ("reactor", "engineering", "hangar", "cargo"):
            rw = max(4, min(8, grid_w // 3))
            rh = max(2, min(4, grid_h // 3))

        # Try to place room
        best_pos = None
        best_score = -1

        for attempt in range(100):
            x = random.randint(0, grid_w - rw)
            y = random.randint(0, grid_h - rh)

            # Check all cells in the room are in hull
            all_in_hull = True
            for dx in range(rw):
                for dy in range(rh):
                    if not is_in_hull(x + dx, y + dy):
                        all_in_hull = False
                        break
                if not all_in_hull:
                    break

            if not all_in_hull:
                continue

            # Check no overlap with existing rooms (with 1 cell gap)
            overlaps = False
            for dx in range(-1, rw + 1):
                for dy in range(-1, rh + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < grid_w and 0 <= ny < grid_h:
                        if grid[ny][nx]:
                            overlaps = True
                            break
                if overlaps:
                    break

            if overlaps:
                continue

            # Score: prefer certain positions
            score = random.random()
            if room_type == "bridge" and x < grid_w * 0.2:
                score += 10
            if room_type == "reactor" and x > grid_w * 0.5:
                score += 10
            if room_type == "engineering" and x > grid_w * 0.4:
                score += 10
            if room_type == "hangar" and x > grid_w * 0.6:
                score += 10

            if score > best_score:
                best_score = score
                best_pos = (x, y)

        if best_pos:
            x, y = best_pos
            for dx in range(rw):
                for dy in range(rh):
                    if 0 <= x + dx < grid_w and 0 <= y + dy < grid_h:
                        grid[y + dy][x + dx] = True
            placed.append(Room(
                room_type=room_type, label=info["label"],
                x=x, y=y, w=rw, h=rh, sym=info["sym"]
            ))

    return placed


def _generate_crew(ship_class: ShipClass, crew_count: int) -> List[CrewMember]:
    """Generate a crew manifest with names, ranks, and species."""
    ranks = RANK_TITLES[ship_class]
    manifest = []

    # Generate officers (one per rank)
    for i, rank in enumerate(ranks):
        species = random.choice(SPECIES)
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        manifest.append(CrewMember(
            name=f"{first} {last}", rank=rank, species=species, role=rank
        ))

    # Fill out crew
    remaining = max(0, crew_count - len(ranks))
    if remaining > 0:
        # Just list a count of remaining crew
        pass

    return manifest


def render_blueprint(ship: ShipSpec) -> str:
    """Render a top-down ASCII blueprint of the ship."""
    lines = []

    # Determine grid size from rooms
    if not ship.rooms:
        return "No rooms to display."

    max_x = max(r.x + r.w for r in ship.rooms)
    max_y = max(r.y + r.h for r in ship.rooms)
    grid_w = max(max_x + 2, 30)
    grid_h = max(max_y + 2, 10)

    # Create blank canvas
    canvas = [[' '] * grid_w for _ in range(grid_h)]

    # Ship hull outline
    def is_in_hull(gx, gy):
        progress = gx / max(1, grid_w - 1)
        if progress < 0.15:
            half_width = (progress / 0.15) * (grid_h / 2 - 1) + 1
        elif progress < 0.7:
            half_width = grid_h / 2 - 1
        else:
            taper = (progress - 0.7) / 0.3
            half_width = (grid_h / 2 - 1) * (1 - 0.3 * taper)
        center = grid_h / 2
        return abs(gy - center) < half_width

    # Draw hull boundary
    for y in range(grid_h):
        for x in range(grid_w):
            if is_in_hull(x, y):
                # Check if it's on the boundary
                is_boundary = False
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if nx < 0 or nx >= grid_w or ny < 0 or ny >= grid_h or not is_in_hull(nx, ny):
                        is_boundary = True
                        break
                if is_boundary:
                    canvas[y][x] = '▓'
                else:
                    if canvas[y][x] == ' ':
                        canvas[y][x] = '░'

    # Draw rooms
    for room in ship.rooms:
        # Room border
        for dx in range(room.w):
            for dy in range(room.h):
                rx, ry = room.x + dx, room.y + dy
                if 0 <= rx < grid_w and 0 <= ry < grid_h:
                    is_edge = (dx == 0 or dx == room.w - 1 or dy == 0 or dy == room.h - 1)
                    if is_edge:
                        canvas[ry][rx] = '▒'
                    else:
                        canvas[ry][rx] = '·'

        # Room symbol in center
        cx = room.x + room.w // 2
        cy = room.y + room.h // 2
        if 0 <= cx < grid_w and 0 <= cy < grid_h:
            canvas[cy][cx] = room.sym

    # Convert canvas to string
    grid_lines = [''.join(row) for row in canvas]

    lines.append("")
    lines.append(f"  ╔{'═' * 60}╗")
    lines.append(f"  ║  {ship.name:^56}  ║")
    lines.append(f"  ║  {ship.registry:^56}  ║")
    lines.append(f"  ╚{'═' * 60}╝")
    lines.append("")
    lines.append("  ┌─── TOP-DOWN BLUEPRINT ───────────────────────────────────┐")

    for row in grid_lines:
        lines.append(f"  │ {row:<{grid_w}} │")

    lines.append("  └───────────────────────────────────────────────────────────┘")
    lines.append("")
    lines.append("  ROOM LEGEND:")
    for room in ship.rooms:
        lines.append(f"    {room.sym}  {room.label:<20} ({room.w}×{room.h})")

    return '\n'.join(lines)


def render_side_view(ship: ShipSpec) -> str:
    """Render a side-view schematic of the ship."""
    lines = []

    length = max(40, min(70, ship.length_m // 2))
    height = max(6, min(14, ship.width_m // 4))

    canvas = [[' '] * length for _ in range(height)]

    # Ship profile — side view
    for y in range(height):
        for x in range(length):
            progress = x / max(1, length - 1)
            # Side profile: rises to a maximum height in the middle
            if progress < 0.1:
                max_h = (progress / 0.1) * (height * 0.6)
            elif progress < 0.3:
                max_h = height * 0.6 + (progress - 0.1) / 0.2 * (height * 0.4)
            elif progress < 0.7:
                max_h = height
            elif progress < 0.9:
                max_h = height * 1.0 - (progress - 0.7) / 0.2 * (height * 0.3)
            else:
                max_h = height * 0.7 - (progress - 0.9) / 0.1 * (height * 0.3)

            # Center vertically
            bottom = height // 2 + int(max_h / 2)
            top = height // 2 - int(max_h / 2)

            if top <= y <= bottom:
                is_boundary = (y == top or y == bottom or
                               (y > top and y < bottom and
                                (not (top <= y <= bottom) if False else False)))
                # Check boundary
                is_bnd = False
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    nx_prog = nx / max(1, length - 1)
                    if nx < 0 or nx >= length or ny < 0 or ny >= height:
                        is_bnd = True
                        break
                    # Recalculate for neighbor
                    p2 = nx / max(1, length - 1)
                    if p2 < 0.1:
                        m2 = (p2 / 0.1) * (height * 0.6)
                    elif p2 < 0.3:
                        m2 = height * 0.6 + (p2 - 0.1) / 0.2 * (height * 0.4)
                    elif p2 < 0.7:
                        m2 = height
                    elif p2 < 0.9:
                        m2 = height - (p2 - 0.7) / 0.2 * (height * 0.3)
                    else:
                        m2 = height * 0.7 - (p2 - 0.9) / 0.1 * (height * 0.3)
                    b2 = height // 2 + int(m2 / 2)
                    t2 = height // 2 - int(m2 / 2)
                    if not (t2 <= ny <= b2):
                        is_bnd = True
                        break

                if is_bnd or y == top or y == bottom:
                    canvas[y][x] = '▄' if y == bottom else ('▀' if y == top else '█')
                else:
                    canvas[y][x] = '░'

    # Add engine glow at the back
    for y in range(height // 2 - 1, height // 2 + 2):
        if 0 <= y < height:
            canvas[y][0] = '◈'

    lines.append("")
    lines.append("  ┌─── SIDE VIEW SCHEMATIC ──────────────────────────────────┐")

    for row in canvas:
        row_str = ''.join(row)
        lines.append(f"  │ {row_str:<{length}} │")

    lines.append("  └───────────────────────────────────────────────────────────┘")

    return '\n'.join(lines)


def render_stats(ship: ShipSpec) -> str:
    """Render ship statistics and details."""
    lines = []

    lines.append("")
    lines.append("  ╔════════════════════════════════════════════════════════════╗")
    lines.append("  ║              STARSHIP REGISTRATION DOSSIER                ║")
    lines.append("  ╠════════════════════════════════════════════════════════════╣")
    lines.append(f"  ║  Name:       {ship.name:<43} ║")
    lines.append(f"  ║  Registry:   {ship.registry:<43} ║")
    lines.append(f"  ║  Class:      {ship.ship_class.label:<43} ║")
    lines.append(f"  ║  Faction:    {ship.faction:<43} ║")
    lines.append("  ╠════════════════════════════════════════════════════════════╣")
    lines.append("  ║  SPECIFICATIONS                                            ║")
    lines.append("  ╠════════════════════════════════════════════════════════════╣")
    lines.append(f"  ║  Length:      {ship.length_m:>6} m{'':<35} ║")
    lines.append(f"  ║  Beam:        {ship.width_m:>6} m{'':<35} ║")
    displacement = ship.length_m * ship.width_m * random.randint(3, 8)
    lines.append(f"  ║  Displacement:{displacement:>7} tonnes{'':<30} ║")
    lines.append(f"  ║  Decks:       {ship.deck_count:>6}{'':<36} ║")
    lines.append(f"  ║  Crew:        {ship.crew_count:>6}{'':<36} ║")
    speed = random.randint(3, 12)
    lines.append(f"  ║  Max Speed:   {speed:>6} ly/h{'':<33} ║")
    lines.append("  ╠════════════════════════════════════════════════════════════╣")
    lines.append("  ║  SYSTEMS                                                   ║")
    lines.append("  ╠════════════════════════════════════════════════════════════╣")
    lines.append(f"  ║  Drive:      {ship.drive:<43} ║")
    lines.append(f"  ║  Shields:    {ship.shield:<43} ║")
    lines.append("  ║  Weapons:                                                  ║")
    for w in ship.weapons:
        lines.append(f"  ║    - {w:<44} ║")
    lines.append("  ╠════════════════════════════════════════════════════════════╣")
    lines.append("  ║  ACCOMMODATIONS                                            ║")
    lines.append("  ╠════════════════════════════════════════════════════════════╣")
    for room in ship.rooms:
        area = room.w * room.h * random.randint(8, 25)
        lines.append(f"  ║    {room.sym} {room.label:<20} ({area:>4} m²){'':<10} ║")
    lines.append("  ╠════════════════════════════════════════════════════════════╣")
    lines.append("  ║  KEY OFFICERS                                              ║")
    lines.append("  ╠════════════════════════════════════════════════════════════╣")
    for crew in ship.crew_manifest[:8]:
        lines.append(f"  ║  {crew.rank:<22} {crew.name:<20} {crew.species:<8} ║")
    if ship.crew_count > len(ship.crew_manifest):
        remaining = ship.crew_count - len(ship.crew_manifest)
        lines.append(f"  ║  {'... plus ' + str(remaining) + ' crew members':^52} ║")
    lines.append("  ╚════════════════════════════════════════════════════════════╝")

    return '\n'.join(lines)


def render_power_diagram(ship: ShipSpec) -> str:
    """Render a power/system distribution diagram."""
    lines = []
    lines.append("")
    lines.append("  ┌─── POWER DISTRIBUTION ──────────────────────────────────┐")
    lines.append("  │                                                          │")

    systems = [
        ("Engines", random.randint(15, 40)),
        ("Shields", random.randint(10, 30)),
        ("Weapons", random.randint(10, 35)),
        ("Life Sup.", random.randint(10, 20)),
        ("Comms", random.randint(5, 15)),
        ("Sensors", random.randint(5, 20)),
    ]

    total = sum(p for _, p in systems)
    bar_width = 40

    for name, power in systems:
        pct = power / total
        filled = int(pct * bar_width)
        bar = '█' * filled + '░' * (bar_width - filled)
        lines.append(f"  │  {name:<10} {bar} {power:>3}% │")

    lines.append("  │                                                          │")
    lines.append("  └───────────────────────────────────────────────────────────┘")

    return '\n'.join(lines)


def render_system_status(ship: ShipSpec) -> str:
    """Render a system status dashboard."""
    lines = []
    lines.append("")
    lines.append("  ┌─── SYSTEM STATUS ───────────────────────────────────────┐")

    status_items = [
        ("Reactor", random.choice(["NOMINAL", "NOMINAL", "OPTIMAL", "HIGH EFFICIENCY"])),
        ("Hull", f"{random.randint(85, 100)}%"),
        ("Shields", random.choice(["STANDBY", "ACTIVE", "CHARGING", "READY"])),
        ("Navigation", random.choice(["LOCKED", "CALCULATING", "LOCKED", "DRIFT COMPENSATION"])),
        ("Comms", random.choice(["ONLINE", "ONLINE", "ONLINE", "ENCRYPTED MODE"])),
        ("Life Support", random.choice(["NOMINAL", "NOMINAL", "BOOSTED", "RECYCLING"])),
        ("Weapons", random.choice(["SAFE", "READY", "STANDBY", "ARMED"])),
    ]

    for name, status in status_items:
        color_indicator = "●" if "NOMINAL" in status or "ONLINE" in status or "LOCKED" in status else "◐"
        if status in ["ARMED", "HIGH EFFICIENCY"]:
            color_indicator = "◉"
        lines.append(f"  │  {color_indicator} {name:<14} {status:<38} │")

    lines.append("  └───────────────────────────────────────────────────────────┘")

    return '\n'.join(lines)


def generate_full_report(ship: ShipSpec) -> str:
    """Generate the complete ship blueprint report."""
    parts = [
        render_blueprint(ship),
        render_side_view(ship),
        render_stats(ship),
        render_power_diagram(ship),
        render_system_status(ship),
    ]
    return '\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Procedural Spaceship Blueprint Generator"
    )
    parser.add_argument(
        '-c', '--class', dest='ship_class',
        choices=[sc.name.lower() for sc in ShipClass],
        help='Ship class to generate (default: random)'
    )
    parser.add_argument(
        '-s', '--seed', type=int, default=None,
        help='Random seed for reproducible results'
    )
    parser.add_argument(
        '-n', '--number', type=int, default=1,
        help='Number of ships to generate (default: 1)'
    )
    parser.add_argument(
        '--stats-only', action='store_true',
        help='Only show stats, no blueprint diagrams'
    )

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    specified_class = None
    if args.ship_class:
        for sc in ShipClass:
            if sc.name.lower() == args.ship_class:
                specified_class = sc
                break

    for i in range(args.number):
        if i > 0:
            print("\n" + "=" * 65 + "\n")
        ship = generate_ship(specified_class)
        if args.stats_only:
            print(render_stats(ship))
        else:
            print(generate_full_report(ship))


if __name__ == "__main__":
    main()