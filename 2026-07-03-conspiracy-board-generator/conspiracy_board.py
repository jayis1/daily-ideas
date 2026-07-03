#!/usr/bin/env python3
"""
Procedural Conspiracy Board Generator
=======================================
Generates an ASCII conspiracy investigation board with random entities,
connections (red strings!), cryptic notes, evidence pins, timelines,
suspicion scores, and redacted text.  Each run produces a unique,
paranoid masterpiece.

Usage:
    python3 conspiracy_board.py [options]

Examples:
    python3 conspiracy_board.py                    # default board
    python3 conspiracy_board.py --narrative       # board + briefing
    python3 conspiracy_board.py --seed 42          # reproducible board
    python3 conspiracy_board.py --no-color         # plain text
    python3 conspiracy_board.py --timeline         # add timeline
    python3 conspiracy_board.py --json             # JSON output
    python3 conspiracy_board.py --version           # show version
"""

import json
import math
import random
import argparse
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Optional, Dict, Set

# ─── Version ────────────────────────────────────────────────────────────────
VERSION = "2.1.0"

# ─── Data pools ──────────────────────────────────────────────────────────────

PEOPLE = [
    "Dr. Vance", "Agent K", "The Architect", "Mr. Nyx", "Prof. Chen",
    "operative_7", "M. Dupont", "The Librarian", "Yuki Tanaka", "Oleg Petrov",
    "Senator Blake", "The Curator", "Dr. Okafor", "Ghost_0x", "The Witness",
    "Cpt. Reyes", "The Baroness", "J. Crawley", "Zara Ahmed", "The Informant",
    "Hans Mueller", "The Whisperer", "Dr. Morales", "Agent Phoenix", "The Exile",
]

ORGANIZATIONS = [
    "The Circle", "Project AURORA", "The Syndicate", "Division 6",
    "The Collective", "OBSIDIAN Group", "The Foundation", "Cell 9",
    "The Institute", "CIPHER Corps", "The Assembly", "Directive Omega",
    "The Panopticon", "THRESHOLD", "The Vault",
]

EVENTS = [
    "The Blackout", "Incident 73", "The Vanishing", "Signal Delta",
    "The Collapse", "Protocol Zero", "The Breach", "Event Horizon",
    "The Recall", "Black Friday", "The Awakening", "Operation Mirage",
    "The Rending", "Silence Protocol", "The Exchange",
]

LOCATIONS = [
    "Site Alpha", "The Bunker", "Warehouse 9", "The Spire",
    "Sector 7-G", "The Archive", "Facility X", "The Catacombs",
    "Station Echo", "Obsidian Room", "Point Nemo", "The Hollow",
    "Vault 12", "The Meridian", "Deep Array",
]

EVIDENCE_TYPES = [
    "PHOTO", "DOCUMENT", "RECORDING", "SAMPLE", "TRANSMISSION",
    "ARTIFACT", "JOURNAL", "BLUEPRINT", "CIPHER", "WITNESS",
    "SURVEILLANCE", "BLOOD", "FINGERPRINT", "FINANCIAL", "EMAIL",
]

CONNECTION_LABELS = [
    "KNOWS", "FEARS", "OWES", "HUNTS", "PROTECTS",
    "SEES", "OWNS", "WORKS FOR", "BETRAYED", "CONTACTED",
    "WATCHES", "RECRUITED", "SILENCED", "FUNDED", "LEAKED TO",
]

CRYPTIC_NOTES = [
    "WHO IS THE ARCHITECT?",
    "FOLLOW THE MONEY",
    "THEY'RE LISTENING",
    "IT'S ALL CONNECTED",
    "TRUST NO ONE",
    "NOT A COINCIDENCE",
    "WAKE UP",
    "LOOK CLOSER",
    "THE CODE IS THE KEY",
    "EVERYTHING IS A MESSAGE",
    "THEY ERASED THE RECORDS",
    "WHO BENEFITS?",
    "DON'T TRUST THE TIMELINE",
    "THE SIGNAL IS REAL",
    "THIS GOES ALL THE WAY UP",
    "IT WAS NEVER A THEORY",
    "THE PATTERN NEVER LIES",
    "CHECK THE DATES",
    "WHAT ARE THEY HIDING?",
    "REMEMBER THE VANISHING",
    "THEY KNOW YOU KNOW",
    "WHO PULLED THE STRINGS?",
    "FOLLOW THE WHITE RABBIT",
    "THE TRUTH IS BURIED",
    "NOTHING IS RANDOM",
]

# Month names for timeline generation
MONTHS = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]

# ─── ANSI colors ────────────────────────────────────────────────────────────

class C:
    RED = "\033[91m"
    YEL = "\033[93m"
    CYN = "\033[96m"
    GRN = "\033[92m"
    MAG = "\033[95m"
    WHT = "\033[97m"
    DIM = "\033[2m"
    BLD = "\033[1m"
    RST = "\033[0m"


# ─── Data structures ────────────────────────────────────────────────────────

@dataclass
class Entity:
    name: str
    kind: str  # "person", "org", "event", "location"
    x: int = 0
    y: int = 0
    evidence: List[str] = field(default_factory=list)
    suspicion: float = 0.0  # 0.0–1.0, how suspicious/central this entity is


@dataclass
class Connection:
    from_idx: int
    to_idx: int
    label: str = ""
    strength: int = 1  # 1=weak, 2=medium, 3=strong


@dataclass
class Note:
    text: str
    x: int = 0
    y: int = 0


@dataclass
class TimelineEvent:
    """An event in the conspiracy timeline."""
    month: int    # 1-12
    year: int     # year
    description: str
    entity_idx: int  # index into entities list
    classification: str = "TOP SECRET"  # classification level


# ─── Board generation ────────────────────────────────────────────────────────

def pick(pool: list, n: int) -> list:
    """Pick n unique items from a pool. Returns at most len(pool) items.

    Handles n <= 0 by returning an empty list.
    """
    if n <= 0:
        return []
    return random.sample(pool, min(n, len(pool)))


def compute_suspicion(entities: List[Entity], connections: List[Connection]) -> None:
    """Compute a suspicion score for each entity based on how central it is.

    Entities with more connections, stronger connections, and connections to
    multiple entity types are scored higher.
    """
    if not entities:
        return

    # Count connections per entity
    conn_count: Dict[int, int] = {i: 0 for i in range(len(entities))}
    conn_strength: Dict[int, int] = {i: 0 for i in range(len(entities))}
    conn_types: Dict[int, Set[str]] = {i: set() for i in range(len(entities))}

    for conn in connections:
        conn_count[conn.from_idx] = conn_count.get(conn.from_idx, 0) + 1
        conn_count[conn.to_idx] = conn_count.get(conn.to_idx, 0) + 1
        conn_strength[conn.from_idx] += conn.strength
        conn_strength[conn.to_idx] += conn.strength
        conn_types[conn.from_idx].add(entities[conn.to_idx].kind)
        conn_types[conn.to_idx].add(entities[conn.from_idx].kind)

    # Evidence adds suspicion
    for i, ent in enumerate(entities):
        evidence_factor = len(ent.evidence) * 0.1
        conn_factor = conn_count.get(i, 0) * 0.15
        strength_factor = conn_strength.get(i, 0) * 0.05
        diversity_factor = len(conn_types.get(i, set())) * 0.1
        ent.suspicion = min(1.0, evidence_factor + conn_factor + strength_factor + diversity_factor)


def detect_cycles(entities: List[Entity], connections: List[Connection]) -> List[List[int]]:
    """Detect simple cycles of length 3 in the connection graph.

    Returns a list of cycles, where each cycle is a list of entity indices
    forming a triangle (A→B, B→C, C→A).
    """
    # Build adjacency set
    adj: Dict[int, Set[int]] = {i: set() for i in range(len(entities))}
    for conn in connections:
        adj[conn.from_idx].add(conn.to_idx)

    cycles = []
    for a in range(len(entities)):
        for b in adj.get(a, set()):
            for c in adj.get(b, set()):
                if c != a and a in adj.get(c, set()):
                    # Found cycle a → b → c → a
                    cycle = sorted([a, b, c])
                    if cycle not in cycles:
                        cycles.append(cycle)

    return cycles[:5]  # Return at most 5 cycles to avoid clutter


def generate_timeline(
    entities: List[Entity],
    connections: List[Connection],
    num_events: int = 6,
    seed: Optional[int] = None,
) -> List[TimelineEvent]:
    """Generate a conspiracy timeline linking entities to dated events.

    Each timeline entry references an entity and places it in a plausible
    date range, creating a narrative of when things happened.
    """
    rng = random.Random(seed)

    timeline: List[TimelineEvent] = []
    base_year = rng.randint(2019, 2024)

    classifications = [
        "TOP SECRET", "CLASSIFIED", "EYES ONLY", "BURN AFTER READING",
        "NOFORN", "SCI", "COMPARTMENTED",
    ]

    # Timeline templates — each references a connection
    templates_single = [
        "First known contact with {entity}",
        "{entity} observed at off-site facility",
        "Secure phone call traced to {entity}",
        "{entity} filed anomalous expense report",
        "Surveillance photo of {entity} confirmed",
        "{entity} deleted records from server",
        "Encrypted message decoded: references {entity}",
        "{entity} visited restricted site after hours",
        "Wire transfer linked to {entity}",
        "{entity} failed polygraph examination",
    ]

    templates_connection = [
        "{from_ent} established contact with {to_ent}",
        "Meeting between {from_ent} and {to_ent} intercepted",
        "{from_ent} transferred funds to {to_ent}",
        "{from_ent} leaked documents to {to_ent}",
        "Shared safe house: {from_ent} and {to_ent}",
        "{from_ent} provided cover for {to_ent}",
    ]

    # Generate single-entity events
    for _ in range(num_events):
        month = rng.randint(1, 12)
        year = base_year + rng.randint(0, 4)
        idx = rng.randint(0, len(entities) - 1)
        template = rng.choice(templates_single)
        desc = template.format(entity=entities[idx].name)
        classification = rng.choice(classifications)
        timeline.append(TimelineEvent(
            month=month, year=year,
            description=desc,
            entity_idx=idx,
            classification=classification,
        ))

    # Generate connection events (if we have connections)
    for conn in connections[:3]:
        month = rng.randint(1, 12)
        year = base_year + rng.randint(0, 4)
        template = rng.choice(templates_connection)
        desc = template.format(
            from_ent=entities[conn.from_idx].name,
            to_ent=entities[conn.to_idx].name,
        )
        classification = rng.choice(classifications)
        # Use the from_idx as reference entity
        timeline.append(TimelineEvent(
            month=month, year=year,
            description=desc,
            entity_idx=conn.from_idx,
            classification=classification,
        ))

    # Sort by date
    timeline.sort(key=lambda e: (e.year, e.month))
    return timeline


def redact_text(text: str, rng: Optional[random.Random] = None, probability: float = 0.3) -> str:
    """Redact portions of text with █████ blocks.

    Args:
        text: The text to redact.
        rng: Random state (uses module random if None).
        probability: Chance each word gets redacted.

    Returns:
        Text with some words replaced by '█████' blocks.
    """
    if rng is None:
        rng = random.Random()

    words = text.split()
    result = []
    for word in words:
        if rng.random() < probability:
            result.append("█" * max(4, len(word)))
        else:
            result.append(word)
    return " ".join(result)


def generate_board(
    width=90, height=45,
    num_people=5, num_orgs=3, num_events=3, num_locations=2,
    num_connections=9, num_notes=4, seed=None,
) -> Tuple[List[Entity], List[Connection], List[Note]]:
    """Generate the board data: entities, connections, and notes.

    Args:
        width: Board width in characters.
        height: Board height in characters.
        num_people: Number of people entities.
        num_orgs: Number of organization entities.
        num_events: Number of event entities.
        num_locations: Number of location entities.
        num_connections: Number of connections between entities.
        num_notes: Number of cryptic notes.
        seed: Random seed for reproducibility.

    Returns:
        Tuple of (entities, connections, notes).
    """
    if seed is not None:
        random.seed(seed)

    # Validate inputs
    width = max(40, min(200, width))
    height = max(20, min(100, height))
    num_connections = max(0, num_connections)
    num_notes = max(0, num_notes)

    entities: List[Entity] = []
    margin = 5

    for name in pick(PEOPLE, num_people):
        entities.append(Entity(name=name, kind="person"))
    for name in pick(ORGANIZATIONS, num_orgs):
        entities.append(Entity(name=name, kind="org"))
    for name in pick(EVENTS, num_events):
        entities.append(Entity(name=name, kind="event"))
    for name in pick(LOCATIONS, num_locations):
        entities.append(Entity(name=name, kind="location"))

    # Spread entities across a grid to reduce overlaps
    cols = max(1, int(math.sqrt(len(entities)) * 1.5))
    rows = (len(entities) + cols - 1) // cols
    cell_w = (width - 2 * margin) / max(cols, 1)
    cell_h = (height - 2 * margin - 3) / max(rows, 1)

    # Track occupied positions to avoid overlaps
    occupied: Set[Tuple[int, int]] = set()

    for i, ent in enumerate(entities):
        col = i % cols
        row = i // cols
        cx = margin + col * cell_w + cell_w / 2
        cy = margin + 1 + row * cell_h + cell_h / 2
        # Add randomness within the cell, avoiding overlaps
        px = int(cx)
        py = int(cy)
        for _ in range(50):  # Try up to 50 times to find a free spot
            candidate_px = int(cx + random.uniform(-cell_w * 0.25, cell_w * 0.25))
            candidate_py = int(cy + random.uniform(-cell_h * 0.15, cell_h * 0.15))
            candidate_px = max(margin, min(width - margin - 1, candidate_px))
            candidate_py = max(margin, min(height - margin - 2, candidate_py))
            if (candidate_px, candidate_py) not in occupied:
                px, py = candidate_px, candidate_py
                break
        ent.x = px
        ent.y = py
        occupied.add((px, py))

    # Add evidence
    for ent in entities:
        n_ev = random.randint(0, 2)
        ent.evidence = pick(EVIDENCE_TYPES, n_ev)

    # Generate connections — prefer connecting different kinds
    connections: List[Connection] = []
    if len(entities) >= 2:
        # Build a pool of potential connection pairs, weighting different-kinds higher
        pairs = []
        for i in range(len(entities)):
            for j in range(len(entities)):
                if i != j:
                    weight = 3 if entities[i].kind != entities[j].kind else 1
                    pairs.extend([(i, j)] * weight)

        used_pairs: Set[Tuple[int, int]] = set()
        for _ in range(min(num_connections, len(pairs))):
            # Try to pick a pair we haven't used yet
            for attempt in range(100):
                a, b = random.choice(pairs)
                if (a, b) not in used_pairs:
                    used_pairs.add((a, b))
                    label = random.choice(CONNECTION_LABELS)
                    strength = random.randint(1, 3)
                    connections.append(Connection(a, b, label, strength))
                    break

    # Generate notes
    note_texts = pick(CRYPTIC_NOTES, num_notes)
    notes: List[Note] = []
    for text in note_texts:
        # Try to place note avoiding entity positions
        # Note box requires: left ┌ at nx-1, right ┐ at nx+len(text)
        # So nx must be >= 1 and nx + len(text) must be <= width - 1
        max_nx = max(margin + 1, width - margin - len(text) - 2)
        nx = random.randint(margin, max_nx)
        ny = random.randint(margin + 2, max(margin + 3, height - margin - 2))
        for _ in range(30):
            candidate_nx = random.randint(margin, max(margin + 1, width - margin - len(text) - 2))
            candidate_ny = random.randint(margin + 2, max(margin + 3, height - margin - 2))
            # Check if this overlaps with any entity
            overlap = any(abs(ent.x - candidate_nx) < len(text) // 2 + 2 and abs(ent.y - candidate_ny) < 2
                         for ent in entities)
            if not overlap:
                nx, ny = candidate_nx, candidate_ny
                break
        notes.append(Note(text=text, x=nx, y=ny))

    # Compute suspicion scores
    compute_suspicion(entities, connections)

    return entities, connections, notes


# ─── Rendering ───────────────────────────────────────────────────────────────

KIND_SYM = {"person": "☻", "org": "◆", "event": "◈", "location": "▲"}
KIND_COL = {"person": C.CYN, "org": C.MAG, "event": C.YEL, "location": C.WHT}

# Suspicion level labels and thresholds
SUSPICION_LABELS = [
    (0.3, "LOW"),
    (0.5, "MODERATE"),
    (0.7, "HIGH"),
    (0.9, "CRITICAL"),
]


def suspicion_label(score: float) -> str:
    """Return a human-readable suspicion level label.

    Ranges:
        0.0–0.3:  LOW
        0.3–0.5:  MODERATE
        0.5–0.7:  HIGH
        0.7–0.9:  CRITICAL
        0.9–1.0:  EXTREME
    """
    for threshold, label in SUSPICION_LABELS:
        if score < threshold:
            return label
    return "EXTREME"


def bresenham(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
    """Draw a line between two points using Bresenham's algorithm.

    Args:
        x0, y0: Start point.
        x1, y1: End point.

    Returns:
        List of (x, y) integer points on the line.
    """
    pts = []
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx - dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return pts


def render_board(entities, connections, notes, width=90, height=45, color=True):
    """Render the conspiracy board as an ASCII string.

    Args:
        entities: List of Entity objects.
        connections: List of Connection objects.
        notes: List of Note objects.
        width: Board width in characters.
        height: Board height in characters.
        color: Whether to include ANSI color codes.

    Returns:
        A string containing the rendered ASCII board with legend.
    """
    # Double-buffer: character and its color tag
    canvas = [[" " for _ in range(width)] for _ in range(height)]
    tags = [["" for _ in range(width)] for _ in range(height)]

    def put(x, y, ch, tag=""):
        if 0 <= x < width and 0 <= y < height:
            canvas[y][x] = ch
            if tag:
                tags[y][x] = tag

    # Entity position lookup (for avoiding overwriting)
    ent_pos = {(e.x, e.y) for e in entities}

    # ── Draw connections (strings) ──
    for conn in connections:
        e1, e2 = entities[conn.from_idx], entities[conn.to_idx]
        pts = bresenham(e1.x, e1.y, e2.x, e2.y)
        if conn.strength >= 3:
            s_ch, s_tag = "━", C.RED
        elif conn.strength == 2:
            s_ch, s_tag = "─", C.RED
        else:
            s_ch, s_tag = "·", C.RED + C.DIM

        for px, py in pts:
            if (px, py) not in ent_pos:
                put(px, py, s_ch, s_tag)

        # Place label near midpoint
        if len(pts) > 8:
            mi = len(pts) // 2
            lx, ly = pts[mi]
            lbl = conn.label[:8]
            # Offset label slightly to avoid entity
            off_y = random.choice([-1, 0, 1])
            for i, ch in enumerate(lbl):
                put(lx - len(lbl) // 2 + i, ly + off_y, ch, C.YEL if color else "")

    # ── Draw cryptic notes (boxed) ──
    for note in notes:
        t = note.text
        tl = len(t)
        nx, ny = note.x, note.y
        # Top row ┌───┐
        put(nx - 1, ny - 1, "┌", C.GRN if color else "")
        for i in range(tl):
            put(nx + i, ny - 1, "─", C.GRN if color else "")
        put(nx + tl, ny - 1, "┐", C.GRN if color else "")
        # Middle row │text│
        put(nx - 1, ny, "│", C.GRN if color else "")
        for i, ch in enumerate(t):
            put(nx + i, ny, ch, C.GRN + C.BLD if color else "")
        put(nx + tl, ny, "│", C.GRN if color else "")
        # Bottom row └───┘
        put(nx - 1, ny + 1, "└", C.GRN if color else "")
        for i in range(tl):
            put(nx + i, ny + 1, "─", C.GRN if color else "")
        put(nx + tl, ny + 1, "┘", C.GRN if color else "")

    # ── Draw entities ──
    for ent in entities:
        sym = KIND_SYM.get(ent.kind, "?")
        col = KIND_COL.get(ent.kind, "") if color else ""
        put(ent.x, ent.y, sym, col + C.BLD if color else "")

        # Name centered below (clamp start position and truncate to fit board)
        name = ent.name
        sx = ent.x - len(name) // 2
        # Clamp start to at least 0 so name doesn't overflow left
        if sx < 0:
            name = name[-sx:]  # Trim left side of name
            sx = 0
        # Truncate name if it extends beyond board width
        if sx + len(name) > width:
            name = name[:width - sx]
        for i, ch in enumerate(name):
            put(sx + i, ent.y + 1, ch, col if color else "")

        # Evidence tag above (clamp start position and truncate to fit board)
        if ent.evidence:
            ev = "[" + ",".join(ent.evidence[:2]) + "]"
            esx = ent.x - len(ev) // 2
            # Clamp start to at least 0
            if esx < 0:
                ev = ev[-esx:]
                esx = 0
            # Truncate if extends beyond board width
            if esx + len(ev) > width:
                ev = ev[:width - esx]
            for i, ch in enumerate(ev):
                put(esx + i, ent.y - 1, ch, C.DIM if color else "")

    # ── Assemble output ──
    lines = []
    lines.append("┌" + "─" * width + "┐")

    for y in range(height):
        row = "│"
        for x in range(width):
            ch = canvas[y][x]
            tag = tags[y][x]
            if color and tag:
                row += f"{tag}{ch}{C.RST}"
            else:
                row += ch
        row += "│"
        lines.append(row)

    lines.append("└" + "─" * width + "┘")

    # ── Legend box ──
    box_w = 100
    lines.append("")
    lines.append("╔" + "═" * (box_w + 2) + "╗")
    lines.append("║" + " CONSPIRACY BOARD — LEGEND & INTEL ".center(box_w + 2) + "║")
    lines.append("╠" + "═" * (box_w + 2) + "╣")

    def legend(text, col=""):
        t = text[:box_w].ljust(box_w)
        if color and col:
            return f"║ {col}{t}{C.RST} ║"
        return f"║ {t} ║"

    lines.append(legend(f"☻ PERSON   ◆ ORGANIZATION   ◈ EVENT   ▲ LOCATION", C.WHT + C.BLD))
    lines.append(legend("━━ Strong link   ── Medium link   ·· Weak link", C.RED))
    lines.append(legend(""))

    # Suspicion scores
    lines.append(legend("  ENTITIES (sorted by suspicion):", C.BLD))
    sorted_ents = sorted(entities, key=lambda e: e.suspicion, reverse=True)
    for ent in sorted_ents:
        sym = KIND_SYM.get(ent.kind, "?")
        ev = ""
        if ent.evidence:
            # Show up to 2 evidence types, truncate if too long to fit legend
            ev_list = ", ".join(ent.evidence[:2])
            ev = f"  │ Ev: {ev_list}"
        sus_label = suspicion_label(ent.suspicion)
        sus_bar_len = 8
        sus_filled = int(ent.suspicion * sus_bar_len)
        sus_bar = "█" * sus_filled + "░" * (sus_bar_len - sus_filled)
        col = KIND_COL.get(ent.kind, "") if color else ""
        line = f"    {sym} {ent.name:<20} [{sus_bar}] {sus_label}{ev}"
        lines.append(legend(line, col))

    lines.append(legend(""))
    lines.append(legend("  CONNECTIONS:", C.RED + C.BLD))
    for conn in connections:
        e1 = entities[conn.from_idx]
        e2 = entities[conn.to_idx]
        bar = "━" * conn.strength
        lines.append(legend(f"    {bar} {e1.name} ─[{conn.label}]→ {e2.name}"))

    lines.append(legend(""))
    lines.append(legend("  CRYPTIC NOTES:", C.GRN + C.BLD))
    for note in notes:
        lines.append(legend(f"    >> {note.text}"))

    # Cycle detection
    cycles = detect_cycles(entities, connections)
    if cycles:
        lines.append(legend(""))
        lines.append(legend("  ⚠ TRIANGULATED CONNECTIONS (cycles):", C.RED + C.BLD))
        for cycle in cycles:
            names = " → ".join(entities[idx].name for idx in cycle)
            lines.append(legend(f"    ◯ {names} ◯", C.RED))

    lines.append("╚" + "═" * (box_w + 2) + "╝")

    return "\n".join(lines)


def render_timeline(timeline: List[TimelineEvent], entities: List[Entity], color: bool = True) -> str:
    """Render the conspiracy timeline as a formatted string.

    Args:
        timeline: List of TimelineEvent objects.
        entities: List of Entity objects for reference.
        color: Whether to include ANSI color codes.

    Returns:
        A formatted timeline string.
    """
    if not timeline:
        return ""

    lines = []
    lines.append("")
    lines.append("━━━ CONSPIRACY TIMELINE ━━━" if not color else f"{C.YEL}{C.BLD}━━━ CONSPIRACY TIMELINE ━━━{C.RST}")
    lines.append("")

    # Header
    if color:
        lines.append(f"  {C.DIM}{'DATE':<14} {'CLASSIFICATION':<20} EVENT{C.RST}")
    else:
        lines.append(f"  {'DATE':<14} {'CLASSIFICATION':<20} EVENT")
    lines.append("  " + "─" * 72)

    for i, event in enumerate(timeline):
        month_str = MONTHS[event.month - 1]
        date_str = f"{month_str} {event.year}"
        entity_name = entities[event.entity_idx].name
        entity_kind = entities[event.entity_idx].kind
        sym = KIND_SYM.get(entity_kind, "?")
        kind_col = KIND_COL.get(entity_kind, "") if color else ""

        # Draw timeline connector
        if i < len(timeline) - 1:
            connector = "  │"
        else:
            connector = "  └"

        if color:
            lines.append(
                f"  {kind_col}{sym}{C.RST} {C.BLD}{date_str:<14}{C.RST} "
                f"{C.RED}{event.classification:<20}{C.RST} "
                f"{event.description}"
            )
        else:
            lines.append(
                f"  {sym} {date_str:<14} "
                f"{event.classification:<20} "
                f"{event.description}"
            )
        if i < len(timeline) - 1:
            lines.append(f"  │")

    lines.append("")
    lines.append("━━━ END TIMELINE — DESTROY AFTER READING ━━━" if not color
                  else f"{C.YEL}{C.BLD}━━━ END TIMELINE — DESTROY AFTER READING ━━━{C.RST}")

    return "\n".join(lines)


def generate_narrative(entities, connections, notes, timeline=None, color=True):
    """Generate a classified intelligence briefing from board data.

    Args:
        entities: List of Entity objects.
        connections: List of Connection objects.
        notes: List of Note objects.
        timeline: Optional list of TimelineEvent objects.
        color: Whether to include ANSI color codes.

    Returns:
        A formatted narrative string.
    """
    lines = []
    lines.append("━━━ CLASSIFIED INTELLIGENCE BRIEFING ━━━")
    lines.append("")
    lines.append("The following connections have been identified through")
    lines.append("surveillance and intercepted communications:")
    lines.append("")

    for conn in connections:
        e1 = entities[conn.from_idx]
        e2 = entities[conn.to_idx]
        strength_word = {1: "weak", 2: "moderate", 3: "strong"}.get(conn.strength, "unknown")
        lines.append(f"  • {e1.name} ─[{conn.label}]→ {e2.name} ({strength_word})")

    lines.append("")
    lines.append("KEY EVIDENCE:")
    for ent in entities:
        if ent.evidence:
            lines.append(f"  • {ent.name}: {', '.join(ent.evidence)}")

    lines.append("")
    lines.append("SUSPICION ASSESSMENT:")
    for ent in sorted(entities, key=lambda e: e.suspicion, reverse=True)[:5]:
        sus_label = suspicion_label(ent.suspicion)
        lines.append(f"  • {ent.name}: {sus_label} ({ent.suspicion:.0%})")

    lines.append("")
    lines.append("OPERATIVE NOTES:")
    for note in notes:
        lines.append(f"  >> {note.text}")

    # Include timeline in narrative if available
    if timeline:
        # Redact some entries for flavor
        rng = random.Random(42)
        lines.append("")
        lines.append("INTERCEPTED TIMELINE FRAGMENTS:")
        for event in timeline[:4]:
            desc = redact_text(event.description, rng, probability=0.25)
            lines.append(f"  [{MONTHS[event.month - 1]} {event.year}] {desc}")

    lines.append("")
    lines.append("━━━ END OF BRIEFING — BURN AFTER READING ━━━")
    return "\n".join(lines)


def generate_json(entities, connections, notes, timeline=None):
    """Generate JSON output of the board data.

    Args:
        entities: List of Entity objects.
        connections: List of Connection objects.
        notes: List of Note objects.
        timeline: Optional list of TimelineEvent objects.

    Returns:
        A JSON string of the board data.
    """
    data = {
        "version": VERSION,
        "entities": [
            {
                "name": e.name,
                "kind": e.kind,
                "x": e.x,
                "y": e.y,
                "evidence": e.evidence,
                "suspicion": round(e.suspicion, 3),
                "suspicion_label": suspicion_label(e.suspicion),
            }
            for e in entities
        ],
        "connections": [
            {
                "from": entities[c.from_idx].name,
                "from_kind": entities[c.from_idx].kind,
                "to": entities[c.to_idx].name,
                "to_kind": entities[c.to_idx].kind,
                "label": c.label,
                "strength": c.strength,
                "strength_word": {1: "weak", 2: "moderate", 3: "strong"}.get(c.strength, "unknown"),
            }
            for c in connections
        ],
        "notes": [{"text": n.text, "x": n.x, "y": n.y} for n in notes],
        "cycles": [
            [entities[idx].name for idx in cycle]
            for cycle in detect_cycles(entities, connections)
        ],
    }
    if timeline:
        data["timeline"] = [
            {
                "month": t.month,
                "year": t.year,
                "description": t.description,
                "entity": entities[t.entity_idx].name,
                "classification": t.classification,
            }
            for t in timeline
        ]
    return json.dumps(data, indent=2, ensure_ascii=False)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Procedural Conspiracy Board Generator — every run is a new conspiracy!",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s                              # default board\n"
            "  %(prog)s --narrative                  # board + classified briefing\n"
            "  %(prog)s --timeline                   # board + conspiracy timeline\n"
            "  %(prog)s --seed 42                     # reproducible board\n"
            "  %(prog)s --json                        # output as JSON\n"
            "  %(prog)s --no-color > board.txt        # plain text to file\n"
            "  %(prog)s --width 120 --height 55       # larger board\n"
        ),
    )
    parser.add_argument("--width", type=int, default=90, help="Board width in characters (40–200, default: 90)")
    parser.add_argument("--height", type=int, default=45, help="Board height in characters (20–100, default: 45)")
    parser.add_argument("--people", type=int, default=5, help="Number of people on the board (default: 5)")
    parser.add_argument("--orgs", type=int, default=3, help="Number of organizations (default: 3)")
    parser.add_argument("--events", type=int, default=3, help="Number of events (default: 3)")
    parser.add_argument("--locations", type=int, default=2, help="Number of locations (default: 2)")
    parser.add_argument("--connections", type=int, default=9, help="Number of connections (default: 9)")
    parser.add_argument("--notes", type=int, default=4, help="Number of cryptic notes (default: 4)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--narrative", action="store_true", help="Print classified intelligence briefing")
    parser.add_argument("--timeline", action="store_true", help="Generate and display a conspiracy timeline")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output board data as JSON")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    args = parser.parse_args()

    # Validate entity counts make sense
    for name, val in [("people", args.people), ("orgs", args.orgs),
                      ("events", args.events), ("locations", args.locations),
                      ("connections", args.connections), ("notes", args.notes)]:
        if val < 0:
            parser.error(f"--{name} must be non-negative, got {val}")

    total_entities = args.people + args.orgs + args.events + args.locations
    if total_entities < 2:
        parser.error("Need at least 2 entities total to generate connections")
    if args.connections > total_entities * (total_entities - 1):
        parser.error(f"Cannot have more connections ({args.connections}) than possible pairs ({total_entities * (total_entities - 1)})")

    entities, connections, notes = generate_board(
        width=args.width, height=args.height,
        num_people=args.people, num_orgs=args.orgs,
        num_events=args.events, num_locations=args.locations,
        num_connections=args.connections, num_notes=args.notes,
        seed=args.seed,
    )

    # Generate timeline if requested
    timeline = None
    if args.timeline:
        timeline = generate_timeline(entities, connections, num_events=6, seed=args.seed)

    # JSON output mode
    if args.json_output:
        print(generate_json(entities, connections, notes, timeline))
        return

    # Render the board
    board = render_board(entities, connections, notes,
                         width=args.width, height=args.height,
                         color=not args.no_color)
    print(board)

    # Print timeline if requested
    if timeline:
        print(render_timeline(timeline, entities, color=not args.no_color))

    # Print narrative if requested
    if args.narrative:
        print()
        nar = generate_narrative(entities, connections, notes, timeline, color=not args.no_color)
        if not args.no_color:
            print(f"{C.RED}{C.BLD}{nar}{C.RST}")
        else:
            print(nar)


if __name__ == "__main__":
    main()