#!/usr/bin/env python3
"""
Procedural Conspiracy Board Generator
=======================================
Generates an ASCII conspiracy investigation board with random entities,
connections (red strings!), cryptic notes, and evidence pins.
Each run produces a unique, paranoid masterpiece.

Usage:
    python3 conspiracy_board.py [options]

Examples:
    python3 conspiracy_board.py                    # default board
    python3 conspiracy_board.py --narrative       # board + briefing
    python3 conspiracy_board.py --seed 42          # reproducible board
    python3 conspiracy_board.py --no-color         # plain text
"""

import math
import random
import argparse
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


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


@dataclass
class Connection:
    from_idx: int
    to_idx: int
    label: str = ""
    strength: int = 1


@dataclass
class Note:
    text: str
    x: int = 0
    y: int = 0


# ─── Board generation ────────────────────────────────────────────────────────

def pick(pool: list, n: int) -> list:
    return random.sample(pool, min(n, len(pool)))


def generate_board(
    width=90, height=45,
    num_people=5, num_orgs=3, num_events=3, num_locations=2,
    num_connections=9, num_notes=4, seed=None,
) -> Tuple[List[Entity], List[Connection], List[Note]]:
    if seed is not None:
        random.seed(seed)

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
    cell_h = (height - 2 * margin - 3) / max(rows, 1)  # leave room for labels

    for i, ent in enumerate(entities):
        col = i % cols
        row = i // cols
        cx = margin + col * cell_w + cell_w / 2
        cy = margin + 1 + row * cell_h + cell_h / 2
        # Add some randomness within the cell
        ent.x = int(cx + random.uniform(-cell_w * 0.25, cell_w * 0.25))
        ent.y = int(cy + random.uniform(-cell_h * 0.15, cell_h * 0.15))
        ent.x = max(margin, min(width - margin - 1, ent.x))
        ent.y = max(margin, min(height - margin - 2, ent.y))

    # Add evidence
    for ent in entities:
        n_ev = random.randint(0, 2)
        ent.evidence = pick(EVIDENCE_TYPES, n_ev)

    # Generate connections — prefer connecting different kinds
    connections: List[Connection] = []
    if len(entities) >= 2:
        for _ in range(num_connections):
            a, b = random.sample(range(len(entities)), 2)
            label = random.choice(CONNECTION_LABELS)
            strength = random.randint(1, 3)
            connections.append(Connection(a, b, label, strength))

    # Generate notes
    note_texts = pick(CRYPTIC_NOTES, num_notes)
    notes: List[Note] = []
    for text in note_texts:
        nx = random.randint(margin, max(margin + 1, width - margin - len(text) - 2))
        ny = random.randint(margin + 2, max(margin + 3, height - margin - 1))
        notes.append(Note(text=text, x=nx, y=ny))

    return entities, connections, notes


# ─── Rendering ───────────────────────────────────────────────────────────────

KIND_SYM = {"person": "☻", "org": "◆", "event": "◈", "location": "▲"}
KIND_COL = {"person": C.CYN, "org": C.MAG, "event": C.YEL, "location": C.WHT}


def bresenham(x0, y0, x1, y1) -> List[Tuple[int, int]]:
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
            off = random.choice([-1, 0, 1])
            for i, ch in enumerate(lbl):
                put(lx - len(lbl) // 2 + i, ly + off, ch, C.YEL if color else "")

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

        # Name centered below
        name = ent.name
        sx = ent.x - len(name) // 2
        for i, ch in enumerate(name):
            put(sx + i, ent.y + 1, ch, col if color else "")

        # Evidence tag above
        if ent.evidence:
            ev = "[" + ",".join(ent.evidence[:2]) + "]"
            esx = ent.x - len(ev) // 2
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
    box_w = 78
    lines.append("")
    lines.append("╔" + "═" * box_w + "╗")
    lines.append("║" + " CONSPIRACY BOARD — LEGEND & INTEL ".center(box_w) + "║")
    lines.append("╠" + "═" * box_w + "╣")

    def legend(text, col=""):
        t = text[:box_w].ljust(box_w)
        if color and col:
            return f"║ {col}{t}{C.RST} ║"
        return f"║ {t} ║"

    lines.append(legend(f"☻ PERSON   ◆ ORGANIZATION   ◈ EVENT   ▲ LOCATION", C.WHT + C.BLD))
    lines.append(legend("━━ Strong link   ── Medium link   ·· Weak link", C.RED))
    lines.append(legend(""))

    lines.append(legend("  ENTITIES:", C.BLD))
    for ent in entities:
        sym = KIND_SYM.get(ent.kind, "?")
        ev = ""
        if ent.evidence:
            ev = f"  │ Evidence: {', '.join(ent.evidence)}"
        col = KIND_COL.get(ent.kind, "") if color else ""
        lines.append(legend(f"    {sym} {ent.name}{ev}", col))

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

    lines.append("╚" + "═" * box_w + "╝")

    return "\n".join(lines)


def generate_narrative(entities, connections, notes):
    lines = []
    lines.append("━━━ CLASSIFIED INTELLIGENCE BRIEFING ━━━")
    lines.append("")
    lines.append("The following connections have been identified through")
    lines.append("surveillance and intercepted communications:")
    lines.append("")

    for conn in connections:
        e1 = entities[conn.from_idx]
        e2 = entities[conn.to_idx]
        lines.append(f"  • {e1.name} ─[{conn.label}]→ {e2.name}")

    lines.append("")
    lines.append("KEY EVIDENCE:")
    for ent in entities:
        if ent.evidence:
            lines.append(f"  • {ent.name}: {', '.join(ent.evidence)}")

    lines.append("")
    lines.append("OPERATIVE NOTES:")
    for note in notes:
        lines.append(f"  >> {note.text}")

    lines.append("")
    lines.append("━━━ END OF BRIEFING — BURN AFTER READING ━━━")
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Procedural Conspiracy Board Generator — every run is a new conspiracy!"
    )
    parser.add_argument("--width", type=int, default=90, help="Board width (chars)")
    parser.add_argument("--height", type=int, default=45, help="Board height (chars)")
    parser.add_argument("--people", type=int, default=5, help="Number of people")
    parser.add_argument("--orgs", type=int, default=3, help="Number of organizations")
    parser.add_argument("--events", type=int, default=3, help="Number of events")
    parser.add_argument("--locations", type=int, default=2, help="Number of locations")
    parser.add_argument("--connections", type=int, default=9, help="Number of connections")
    parser.add_argument("--notes", type=int, default=4, help="Number of cryptic notes")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--narrative", action="store_true", help="Print narrative briefing")
    parser.add_argument("--no-color", action="store_true", help="Disable colors")

    args = parser.parse_args()

    entities, connections, notes = generate_board(
        width=args.width, height=args.height,
        num_people=args.people, num_orgs=args.orgs,
        num_events=args.events, num_locations=args.locations,
        num_connections=args.connections, num_notes=args.notes,
        seed=args.seed,
    )

    board = render_board(entities, connections, notes,
                         width=args.width, height=args.height,
                         color=not args.no_color)
    print(board)

    if args.narrative:
        print()
        nar = generate_narrative(entities, connections, notes)
        if not args.no_color:
            print(f"{C.RED}{C.BLD}{nar}{C.RST}")
        else:
            print(nar)


if __name__ == "__main__":
    main()