#!/usr/bin/env python3
"""
Terminal Hacker Simulator — A cinematic hacking simulation game.
Break into procedurally generated networks, crack passwords, bypass firewalls,
exfiltrate data, and race against the clock before you're traced.

v3.0.0 — Enhanced with save/load, analyze, history, high scores, and more.
"""

import random
import time
import sys
import os
import json
import shutil
import string
import textwrap
import argparse
from collections import OrderedDict
from datetime import datetime

VERSION = "3.1.0"

# ── Save file path ────────────────────────────────────────────────────────────

SAVE_DIR = os.path.join(os.path.expanduser("~"), ".config", "hack_sim")
SAVE_FILE = os.path.join(SAVE_DIR, "save.json")
HIGH_SCORES_FILE = os.path.join(SAVE_DIR, "highscores.json")
MAX_HIGH_SCORES = 10

# ── ANSI helpers ──────────────────────────────────────────────────────────────

ESC = "\033["
BOLD = f"{ESC}1m"
DIM = f"{ESC}2m"
ITALIC = f"{ESC}3m"
UNDERLINE = f"{ESC}4m"
RED = f"{ESC}91m"
GREEN = f"{ESC}92m"
YELLOW = f"{ESC}93m"
BLUE = f"{ESC}94m"
MAGENTA = f"{ESC}95m"
CYAN = f"{ESC}96m"
WHITE = f"{ESC}97m"
RESET = f"{ESC}0m"
CLEAR = f"{ESC}2J{ESC}H"
HIDE_CURSOR = f"{ESC}?25l"
SHOW_CURSOR = f"{ESC}?25h"

TERMINAL_W = shutil.get_terminal_size((80, 24)).columns
TERMINAL_H = shutil.get_terminal_size((80, 24)).lines


def center(text, width=None):
    """Center text within a given width."""
    w = width or TERMINAL_W
    return text.center(w)


def slow_print(text, delay=0.02, end=""):
    """Print text character by character with a delay."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    if end:
        sys.stdout.write(end)
        sys.stdout.flush()


def type_line(text, delay=0.012, color=""):
    """Simulate typing a line with optional color."""
    if color:
        sys.stdout.write(color)
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(RESET + "\n")
    sys.stdout.flush()


def glitch_text(text, iterations=6, delay=0.04):
    """Display text with a glitch effect."""
    charset = string.ascii_letters + string.digits + "!@#$%^&*"
    for i in range(iterations):
        display = "".join(random.choice(charset) if random.random() < 0.7 else ch for ch in text)
        sys.stdout.write(f"\r{GREEN}{display}{RESET}")
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(f"\r{GREEN}{BOLD}{text}{RESET}\n")
    sys.stdout.flush()


def progress_bar(label, length=40, speed=0.02):
    """Animated progress bar."""
    sys.stdout.write(f"{CYAN}{label} [{RESET}")
    for i in range(length):
        sys.stdout.write(f"{GREEN}█{RESET}")
        sys.stdout.flush()
        time.sleep(speed * random.uniform(0.5, 1.5))
    sys.stdout.write(f"{CYAN}]{RESET}\n")


def matrix_rain(duration=2.0, density=0.08):
    """Brief matrix rain effect."""
    charset = "01ｱｲｳｴｵｶｷｸｹｺ"
    cols = TERMINAL_W
    start = time.time()
    while time.time() - start < duration:
        line = "".join(random.choice(charset) if random.random() < density else " " for _ in range(cols))
        sys.stdout.write(f"{GREEN}{DIM}{line}{RESET}\n")
        sys.stdout.flush()
        time.sleep(0.06)
    sys.stdout.write(f"{ESC}{1}A" * 30 + CLEAR)


# ── Word lists ────────────────────────────────────────────────────────────────

ADJECTIVES = [
    "shadow", "dark", "neon", "cipher", "ghost", "phantom", "void", "null",
    "binary", "quantum", "frozen", "iron", "steel", "chrome", "stealth",
    "toxic", "silent", "frost", "crimson", "obsidian", "azure", "cobalt",
]

NOUNS = [
    "net", "grid", "node", "core", "vault", "gate", "mainframe",
    "sector", "daemon", "spider", "wolf", "fox", "raven", "viper",
    "matrix", "archive", "tower", "fortress", "engine", "sentinel",
]

CORP_NAMES = [
    "OmniCorp", "Nexus Dynamics", "Zeta Holdings", "Helix Industries",
    "Vaultec Solutions", "Axiom Global", "Polaris Systems", "Cobalt Group",
    "Titan Enterprises", "Synapse Labs", "Vortex Corp", "Onyx Financial",
    "Meridian Tech", "Cipher Networks", "Eclipse Data",
]

FILE_NAMES = [
    "payroll_enc.db", "employee_records.sql", "financial_q4.xlsx",
    "exec_emails.mbox", "blueprint_v3.dwg", "source_main.tar.gz",
    "client_list.csv", "password_vault.kdbx", "audit_log_2026.bin",
    "merger_docs.zip", "patent_pending.pdf", "hr_internal.db",
    "research_notes.md", "security_keys.pem", "board_minutes.docx",
]

HACK_VERBS = [
    "Initializing", "Establishing", "Bypassing", "Decrypting", "Injecting",
    "Compiling", "Uploading", "Cracking", "Scanning", "Enumerating",
    "Intercepting", "Spoofing", "Tunneling", "Escalating", "Exfiltrating",
]

HACK_NOUNS = [
    "crypto layer", "firewall", "packet filter", "handshake", "session token",
    "hash table", "root certificate", "DNS resolver", "proxy chain",
    "kernel module", "memory page", "access token", "boot sector",
    "I/O scheduler", "port scanner", "SSH key", "OTP seed",
]

IP_PREFIXES = ["10.0", "172.16", "192.168", "203.0", "198.51", "233.252"]

# ── Hacker handles for whoami flavor ───────────────────────────────────────────

HACKER_ALIASES = [
    "ZeroCool", "AcidBurn", "CrashOverride", "Neo", "Morpheus",
    "Trinity", "ThePlague", "Razor", "Blade", "Ghost in the Wire",
    "CipherPunk", "NullSet", "DarkPhoenix", "BitRot", "ShadowByte",
]


# ── Save/Load helpers ─────────────────────────────────────────────────────────

def ensure_save_dir():
    """Create the save directory if it doesn't exist."""
    os.makedirs(SAVE_DIR, exist_ok=True)


def save_game(game):
    """Save the current game state to disk."""
    ensure_save_dir()
    state = {
        "version": VERSION,
        "score": game.score,
        "networks_cracked": game.networks_cracked,
        "files_stolen": game.files_stolen,
        "trace_level": game.trace_level,
        "max_trace": game.max_trace,
        "tools_unlocked": list(game.tools_unlocked),
        "total_cracks_attempted": game.total_cracks_attempted,
        "total_cracks_succeeded": game.total_cracks_succeeded,
        "total_analyses": game.total_analyses,
        "command_history": game.command_history[-50:],
        "saved_at": datetime.now().isoformat(),
    }
    if game.current_network:
        net = game.current_network
        state["network"] = {
            "difficulty": net.difficulty,
            "corp": net.corp,
            "handle": net.handle,
            "ip": net.ip,
            "nodes": net.nodes,
        }
    else:
        state["network"] = None

    with open(SAVE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    return True


def load_game(game):
    """Load a saved game state from disk. Returns True if successful."""
    if not os.path.exists(SAVE_FILE):
        return False
    try:
        with open(SAVE_FILE, "r") as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError):
        return False

    game.score = state.get("score", 0)
    game.networks_cracked = state.get("networks_cracked", 0)
    game.files_stolen = state.get("files_stolen", 0)
    game.trace_level = state.get("trace_level", 0)
    game.max_trace = state.get("max_trace", 100)
    game.tools_unlocked = set(state.get("tools_unlocked", ["scan", "crack", "download"]))
    game.total_cracks_attempted = state.get("total_cracks_attempted", 0)
    game.total_cracks_succeeded = state.get("total_cracks_succeeded", 0)
    game.total_analyses = state.get("total_analyses", 0)
    game.command_history = state.get("command_history", [])

    net_data = state.get("network")
    if net_data:
        net = Network(difficulty=net_data["difficulty"])
        net.corp = net_data["corp"]
        net.handle = net_data["handle"]
        net.ip = net_data["ip"]
        net.nodes = net_data["nodes"]
        game.current_network = net
    else:
        game.current_network = None

    return True


def save_high_score(score, networks, files):
    """Save a high score entry."""
    ensure_save_dir()
    entries = []
    if os.path.exists(HIGH_SCORES_FILE):
        try:
            with open(HIGH_SCORES_FILE, "r") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, OSError):
            entries = []

    entries.append({
        "score": score,
        "networks": networks,
        "files": files,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    # Sort descending by score, keep top N
    entries.sort(key=lambda e: e["score"], reverse=True)
    entries = entries[:MAX_HIGH_SCORES]

    with open(HIGH_SCORES_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def show_high_scores():
    """Display the high score table."""
    if not os.path.exists(HIGH_SCORES_FILE):
        print(f"\n  {YELLOW}No high scores yet. Complete a mission to set one!{RESET}\n")
        return
    try:
        with open(HIGH_SCORES_FILE, "r") as f:
            entries = json.load(f)
    except (json.JSONDecodeError, OSError):
        print(f"\n  {RED}Error reading high scores.{RESET}\n")
        return

    if not entries:
        print(f"\n  {YELLOW}No high scores yet.{RESET}\n")
        return

    print(f"\n{CYAN}{'═' * 60}")
    print(f"  ★ HIGH SCORES ★")
    print(f"{'═' * 60}{RESET}\n")

    for i, entry in enumerate(entries, 1):
        medal = f"{YELLOW}★{RESET}" if i == 1 else (f"{WHITE}★{RESET}" if i == 2 else (f"{RED}★{RESET}" if i == 3 else " "))
        print(f"  {medal} {BOLD}{i:>2}.{RESET}  {entry['score']:>8} pts  "
              f"{DIM}│{RESET}  Networks: {entry['networks']}  "
              f"{DIM}│{RESET}  Files: {entry['files']}  "
              f"{DIM}│{RESET}  {entry['date']}")

    print(f"\n{CYAN}{'═' * 60}{RESET}\n")


def delete_save():
    """Delete the save file."""
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
        return True
    return False


# ── Game classes ──────────────────────────────────────────────────────────────

class Network:
    """A procedurally generated network to hack into."""

    def __init__(self, difficulty=None):
        self.difficulty = difficulty or random.randint(1, 5)
        self.corp = random.choice(CORP_NAMES)
        self.handle = f"{random.choice(ADJECTIVES)}_{random.choice(NOUNS)}"
        self.ip = f"{random.choice(IP_PREFIXES)}.{random.randint(1,254)}.{random.randint(1,254)}"
        self.nodes = []
        self._generate_nodes()

    def _generate_nodes(self):
        """Generate the nodes in this network based on difficulty."""
        count = 3 + self.difficulty
        node_types = ["gateway", "proxy", "database", "workstation", "server", "firewall"]
        for i in range(count):
            node = {
                "type": random.choice(node_types),
                "ip": f"{random.choice(IP_PREFIXES)}.{random.randint(1,254)}.{random.randint(1,254)}",
                "name": f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}-{random.randint(10,99)}",
                "difficulty": min(random.randint(1, self.difficulty + 1), 5),
                "cracked": False,
                "analyzed": False,
                "files": random.sample(FILE_NAMES, k=random.randint(1, 3)),
            }
            self.nodes.append(node)

    @property
    def total_difficulty(self):
        """Sum of all node difficulties."""
        return sum(n["difficulty"] for n in self.nodes)

    def network_addr(self):
        """Return the network address in CIDR notation (first 3 octets + .0/24)."""
        first_three = ".".join(self.ip.split(".")[:3])
        return f"{first_three}.0/24"

    def cracked_count(self):
        """Number of nodes that have been cracked."""
        return sum(1 for n in self.nodes if n["cracked"])

    def total_nodes(self):
        """Total number of nodes."""
        return len(self.nodes)


class HackerSimulator:
    """Main game engine."""

    def __init__(self):
        self.score = 0
        self.networks_cracked = 0
        self.files_stolen = 0
        self.current_network = None
        self.trace_level = 0
        self.max_trace = 100
        self.tools_unlocked = set(["scan", "crack", "download"])
        self.running = True
        self.command_history = []
        self.total_cracks_attempted = 0
        self.total_cracks_succeeded = 0
        self.total_analyses = 0

    def clear(self):
        """Clear the terminal screen."""
        sys.stdout.write(CLEAR)
        sys.stdout.flush()

    def banner(self):
        """Display the game banner."""
        self.clear()
        banner_lines = [
            "",
            f"{GREEN}{BOLD}  ╔══════════════════════════════════════════════════════════╗",
            f"{GREEN}{BOLD}  ║                                                          ║",
            f"{GREEN}{BOLD}  ║     ██╗  ██╗ █████╗  ██████╗██╗  ██╗                    ║",
            f"{GREEN}{BOLD}  ║     ██║  ██║██╔══██╗██╔════╝██║ ██╔╝                    ║",
            f"{GREEN}{BOLD}  ║     ███████║███████║██║     █████╔╝                     ║",
            f"{GREEN}{BOLD}  ║     ██╔══██║██╔══██║██║     ██╔═██╗                     ║",
            f"{GREEN}{BOLD}  ║     ██║  ██║██║  ██║╚██████╗██║  ██╗                    ║",
            f"{GREEN}{BOLD}  ║     ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝                    ║",
            f"{GREEN}{BOLD}  ║                                                          ║",
            f"{GREEN}{BOLD}  ║     ███╗   ██╗███████╗████████╗ █████╗  ██████╗ ██╗   ██╗   ║",
            f"{GREEN}{BOLD}  ║     ████╗  ██║██╔════╝╚══██╔══╝██╔══██╗██╔═══██╗╚██╗ ██╔╝   ║",
            f"{GREEN}{BOLD}  ║     ██╔██╗ ██║█████╗     ██║   ███████║██║   ██║ ╚████╔╝    ║",
            f"{GREEN}{BOLD}  ║     ██║╚██╗██║██╔══╝     ██║   ██╔══██║██║   ██║  ╚██╔╝     ║",
            f"{GREEN}{BOLD}  ║     ██║ ╚████║███████╗   ██║   ██║  ██║╚██████╔╝   ██║      ║",
            f"{GREEN}{BOLD}  ║     ╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝    ╚═╝      ║",
            f"{GREEN}{BOLD}  ║                                                          ║",
            f"{GREEN}{BOLD}  ║{f'T E R M I N A L   H A C K E R   v{VERSION}'.center(58)}║",
            f"{GREEN}{BOLD}  ║                                                          ║",
            f"{GREEN}{BOLD}  ╚══════════════════════════════════════════════════════════╝",
            f"{RESET}",
        ]
        for line in banner_lines:
            print(line)
            time.sleep(0.01)

    def boot_sequence(self):
        """Cinematic boot sequence."""
        self.banner()
        time.sleep(0.5)

        boot_lines = [
            (f"{DIM}[BIOS]", "POST check... OK"),
            (f"{DIM}[BIOS]", "Memory test... 32768K OK"),
            (f"{DIM}[KERNEL]", "Loading shadow kernel v4.2.1..."),
            (f"{DIM}[KERNEL]", "Initializing crypto engine..."),
            (f"{DIM}[KERNEL]", "Mounting encrypted filesystem..."),
            (f"{DIM}[NET]", "Establishing TOR circuit... 3 relays found"),
            (f"{DIM}[NET]", "VPN tunnel active. External IP masked."),
            (f"{DIM}[SEC]", "Stealth mode: ENABLED"),
            (f"{DIM}[SEC]", "Trace countermeasures: LOADED"),
            (f"{DIM}[SAVE]", f"Save directory: {SAVE_DIR}"),
            (f"{YELLOW}[WARN]", f"Operating at risk level: {RED}MODERATE{RESET}"),
        ]

        for tag, msg in boot_lines:
            sys.stdout.write(f"  {tag} {msg}{RESET}\n")
            sys.stdout.flush()
            time.sleep(random.uniform(0.15, 0.35))

        print()
        progress_bar("  System ready", length=30, speed=0.02)
        print()
        time.sleep(0.3)
        glitch_text("  >> CONNECTION ESTABLISHED <<", iterations=8, delay=0.03)
        print()
        time.sleep(0.5)

    def show_status(self):
        """Display current mission status."""
        net = self.current_network
        if net is None:
            print(f"{YELLOW}No active mission. Type 'scan' or wait for a network to be assigned.{RESET}")
            return

        # Calculate trace percentage relative to max_trace
        trace_pct = int(min(self.trace_level / self.max_trace * 100, 999))
        trace_bar_filled = min(int(trace_pct / 4), 25)
        trace_bar = "█" * trace_bar_filled + "░" * (25 - trace_bar_filled)

        trace_color = GREEN if trace_pct < 40 else (YELLOW if trace_pct < 70 else RED)

        # Progress indicator
        cracked = net.cracked_count()
        total = net.total_nodes()
        progress = f"{cracked}/{total}"

        print(f"\n{CYAN}{'─' * 60}")
        print(f"  TARGET: {BOLD}{net.corp}{RESET}  ({net.handle})")
        print(f"  IP: {net.ip}  |  Nodes: {total}  |  Difficulty: {'█' * net.difficulty}{'░' * (5 - net.difficulty)}")
        print(f"  PROGRESS: {GREEN}{cracked}{RESET}/{total} nodes cracked")
        print(f"  TRACE: [{trace_color}{trace_bar}{RESET}] {trace_color}{trace_pct}%{RESET}  ({int(self.trace_level)}/{self.max_trace})")
        print(f"  SCORE: {BOLD}{self.score}{RESET}  |  Networks: {self.networks_cracked}  |  Files: {self.files_stolen}")
        print(f"{CYAN}{'─' * 60}{RESET}\n")

    def show_nodes(self):
        """Display network nodes with their status."""
        net = self.current_network
        if net is None:
            print(f"{YELLOW}No active mission. Use 'scan' to find a network.{RESET}")
            return
        print(f"\n{CYAN}{'═' * 60}")
        print(f"  NETWORK MAP: {net.corp}")
        print(f"{'═' * 60}{RESET}\n")

        for i, node in enumerate(net.nodes):
            status_icon = f"{GREEN}✓{RESET}" if node["cracked"] else (f"{BLUE}◎{RESET}" if node.get("analyzed") else f"{RED}✗{RESET}")
            diff_bar = "█" * node["difficulty"] + "░" * (5 - node["difficulty"])
            analyzed_tag = f" {DIM}[ANALYZED]{RESET}" if node.get("analyzed") and not node["cracked"] else ""
            print(f"  [{i+1}] {status_icon} {BOLD}{node['name']:<25}{RESET} {DIM}({node['type']}){RESET}{analyzed_tag}")
            print(f"      IP: {node['ip']}  |  Security: {diff_bar}  |  Files: {len(node['files'])}")
            if node["cracked"]:
                print(f"      {DIM}Files: {', '.join(node['files']) if node['files'] else '(downloaded)'}{RESET}")
            elif node.get("analyzed"):
                # Show partial hint from analyzed node
                hint_chars = node.get("_code_hint", "??")
                print(f"      {BLUE}Code hint: {hint_chars}{RESET}")
            print()

    def analyze_node(self, node_idx):
        """Recon a node — reveals the first 3 characters of its access code.

        Costs a small amount of trace (2 * difficulty).
        """
        if self.current_network is None:
            print(f"{YELLOW}No active mission. Use 'scan' to find a network.{RESET}")
            return

        if node_idx < 1 or node_idx > len(self.current_network.nodes):
            print(f"{RED}Invalid node number.{RESET}")
            return

        node = self.current_network.nodes[node_idx - 1]

        if node["cracked"]:
            print(f"{YELLOW}Node '{node['name']}' already compromised. No need to analyze.{RESET}")
            return

        if node.get("analyzed"):
            print(f"{YELLOW}Node '{node['name']}' already analyzed. Use the hint from 'nodes'.{RESET}")
            return

        difficulty = node["difficulty"]
        trace_cost = difficulty * 2
        self.trace_level += trace_cost
        self.total_analyses += 1

        print(f"\n{BLUE}▶ Analyzing: {BOLD}{node['name']}{RESET}")
        print(f"{BLUE}▶ Type: {node['type']}  |  Security Level: {difficulty}{RESET}")
        print(f"{DIM}  Trace cost: +{trace_cost} points{RESET}\n")

        # Run a brief scan animation
        verb = random.choice(HACK_VERBS)
        noun = random.choice(HACK_NOUNS)
        print(f"  {CYAN}{verb.lower()} {noun}...{RESET}")
        progress_bar(f"  Analyzing {node['ip']}", length=15 + difficulty * 3, speed=0.015)

        # Generate the access code (same logic as crack_node)
        code_length = 4 + difficulty
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=code_length))

        # Store for later use in crack_node — we'll use a seed-based approach
        # Instead, store the actual code on the node so crack_node can reuse it
        reveal_count = min(3, len(code))
        hint = code[:reveal_count] + "•" * (len(code) - reveal_count)

        node["analyzed"] = True
        node["_code_hint"] = hint
        node["_access_code"] = code

        print(f"\n  {BLUE}{BOLD}◈ ANALYSIS COMPLETE{RESET}")
        print(f"  {BLUE}Node type: {node['type']}  |  Security level: {difficulty}{RESET}")
        print(f"  {BLUE}Access code pattern: {BOLD}{hint}{RESET}")
        print(f"  {DIM}Use 'crack {node_idx}' to attempt access.{RESET}\n")

    def crack_node(self, node_idx):
        """Attempt to crack a node with a mini-game."""
        if self.current_network is None:
            print(f"{YELLOW}No active mission. Use 'scan' to find a network.{RESET}")
            return

        if node_idx < 1 or node_idx > len(self.current_network.nodes):
            print(f"{RED}Invalid node number.{RESET}")
            return

        node = self.current_network.nodes[node_idx - 1]

        if node["cracked"]:
            print(f"{YELLOW}Node '{node['name']}' already compromised.{RESET}")
            return

        difficulty = node["difficulty"]
        self.trace_level += difficulty * 3
        self.total_cracks_attempted += 1

        print(f"\n{YELLOW}▶ Targeting: {BOLD}{node['name']}{RESET}")
        print(f"{YELLOW}▶ Type: {node['type']}  |  Security Level: {difficulty}{RESET}\n")

        # Phase 1: Scan
        verb = random.choice(HACK_VERBS)
        noun = random.choice(HACK_NOUNS)
        print(f"  {CYAN}{verb.lower()} {noun}...{RESET}")
        progress_bar(f"  Scanning {node['ip']}", length=25 + difficulty * 5, speed=0.015)

        # Phase 2: Crack password mini-game
        print(f"\n  {MAGENTA}⚡ CRACKING ACCESS CODE{RESET}\n")

        # Use the pre-generated code if the node was analyzed, else generate fresh
        if node.get("_access_code"):
            code = node["_access_code"]
            # Clean up stored code after use
            del node["_access_code"]
        else:
            code_length = 4 + difficulty
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=code_length))

        code_length = len(code)
        # If analyzed, show the analyzed hint; otherwise show first 2 chars
        if node.get("analyzed"):
            hint = node.get("_code_hint", code[:2] + "•" * (code_length - 2))
        else:
            hint = code[:2] + "•" * (code_length - 2)

        print(f"  {BOLD}Access code pattern: {GREEN}{hint}{RESET}")
        print(f"  {DIM}(Type the full code to crack the node. Partial matches reduce trace.){RESET}\n")

        try:
            attempt = input(f"  {BOLD}{CYAN}CODE>{RESET} ").strip().upper()
        except EOFError:
            attempt = ""

        # Calculate match
        match_count = sum(1 for a, b in zip(attempt, code) if a == b)
        total = len(code)

        if attempt == code:
            # Perfect crack!
            node["cracked"] = True
            points = difficulty * 150
            self.score += points
            self.total_cracks_succeeded += 1
            print(f"\n  {GREEN}{BOLD}★ PERFECT CRACK! ★{RESET}")
            print(f"  {GREEN}Node '{node['name']}' compromised! +{points} pts{RESET}")
            glitch_text(f"  ACCESS GRANTED — {node['ip']}")
        elif match_count >= total * 0.5:
            # Partial crack
            node["cracked"] = True
            points = difficulty * 80
            self.score += points
            self.trace_level += difficulty * 5
            self.total_cracks_succeeded += 1
            print(f"\n  {YELLOW}⚠ PARTIAL CRACK{RESET}")
            print(f"  {YELLOW}Brute-forcing remaining bytes...{RESET}")
            progress_bar("  Forcing", length=20, speed=0.03)
            print(f"  {GREEN}Node '{node['name']}' compromised! +{points} pts{RESET}")
        else:
            # Failed
            self.trace_level += difficulty * 8
            print(f"\n  {RED}✗ CRACK FAILED{RESET}")
            print(f"  {RED}Access code was: {code}{RESET}")
            print(f"  {RED}Trace level increased significantly!{RESET}")

        time.sleep(0.5)

    def download_files(self, node_idx):
        """Download files from a cracked node."""
        if self.current_network is None:
            print(f"{YELLOW}No active mission. Use 'scan' to find a network.{RESET}")
            return

        if node_idx < 1 or node_idx > len(self.current_network.nodes):
            print(f"{RED}Invalid node number.{RESET}")
            return

        node = self.current_network.nodes[node_idx - 1]

        if not node["cracked"]:
            print(f"{RED}Node not compromised. Crack it first.{RESET}")
            return

        files = node["files"]
        if not files:
            print(f"  {YELLOW}No files remaining on this node.{RESET}")
            return

        print(f"\n  {CYAN}▼ Downloading from {node['name']}...{RESET}\n")

        for f in files:
            progress_bar(f"  {f}", length=20, speed=0.02)
            self.files_stolen += 1
            points = random.randint(50, 200)
            self.score += points
            print(f"    {GREEN}✓ {f} ({points} pts){RESET}\n")

        # Remove downloaded files to avoid double-dipping
        node["files"] = []

    def deploy_tool(self, tool_name):
        """Use a special hacking tool."""
        if self.current_network is None and tool_name in ("nuke", "overclock"):
            print(f"{YELLOW}No active mission. Connect to a network first.{RESET}")
            return

        if tool_name not in self.tools_unlocked:
            print(f"{RED}Tool '{tool_name}' not available. Earn it through gameplay.{RESET}")
            return

        if tool_name == "tracecut":
            print(f"\n  {MAGENTA}⚡ DEPLOYING TRACE CUTTER{RESET}")
            progress_bar("  Neutralizing trace", length=20, speed=0.025)
            reduction = min(self.trace_level, random.randint(15, 35))
            self.trace_level -= reduction
            print(f"  {GREEN}Trace reduced by {reduction} points!{RESET}")
            self.tools_unlocked.discard("tracecut")

        elif tool_name == "nuke":
            print(f"\n  {RED}{BOLD}⚡ DEPLOYING NETWORK NUKE{RESET}")
            for node in self.current_network.nodes:
                if not node["cracked"]:
                    node["cracked"] = True
                    self.score += 50
                    self.total_cracks_succeeded += 1
                    self.total_cracks_attempted += 1
            self.trace_level += 20
            print(f"  {RED}All nodes cracked! But trace increased by 20 points!{RESET}")
            self.tools_unlocked.discard("nuke")

        elif tool_name == "stealth":
            print(f"\n  {CYAN}⚡ DEPLOYING STEALTH MODULE{RESET}")
            progress_bar("  Cloaking", length=15, speed=0.02)
            self.trace_level = max(0, self.trace_level - 25)
            print(f"  {GREEN}Stealth active! Trace reduced by 25 points!{RESET}")
            self.tools_unlocked.discard("stealth")

        elif tool_name == "overclock":
            print(f"\n  {YELLOW}⚡ DEPLOYING OVERCLOCK MODULE{RESET}")
            progress_bar("  Overclocking CPU", length=10, speed=0.01)
            self.trace_level = max(0, self.trace_level - 15)
            # Also boost next crack attempt by making all uncracked nodes easier
            for node in self.current_network.nodes:
                if not node["cracked"] and node["difficulty"] > 1:
                    node["difficulty"] -= 1
            print(f"  {GREEN}CPU overclocked! Node difficulties reduced. Trace -15 points.{RESET}")
            self.tools_unlocked.discard("overclock")

        elif tool_name == "shield":
            print(f"\n  {BLUE}⚡ DEPLOYING SHIELD GENERATOR{RESET}")
            progress_bar("  Raising shields", length=15, speed=0.02)
            # Shield increases max trace by 30, giving more headroom
            self.max_trace += 30
            print(f"  {GREEN}Shield active! Max trace increased to {self.max_trace}%.{RESET}")
            self.tools_unlocked.discard("shield")

        else:
            print(f"{RED}Unknown tool: {tool_name}{RESET}")

    def generate_network(self, difficulty=None):
        """Generate a new network to hack."""
        if difficulty is None:
            difficulty = min(1 + self.networks_cracked, 5)
        self.current_network = Network(difficulty=difficulty)
        self.trace_level = 0

        # Chance to unlock tools
        available_tools = ["tracecut", "nuke", "stealth", "overclock", "shield"]
        unlock_chance = 0.35 + (self.networks_cracked * 0.05)  # Increases with progress
        if random.random() < unlock_chance:
            # Prefer tools not yet unlocked
            candidates = [t for t in available_tools if t not in self.tools_unlocked]
            if candidates:
                tool = random.choice(candidates)
                self.tools_unlocked.add(tool)
                print(f"\n  {MAGENTA}★ NEW TOOL UNLOCKED: {BOLD}{tool.upper()}{RESET}")
                print(f"  {DIM}Use 'deploy {tool}' to activate it.{RESET}")

        print(f"\n{GREEN}{BOLD}  ▶ NEW TARGET ACQUIRED{RESET}")
        print(f"  {CYAN}Corporation: {BOLD}{self.current_network.corp}{RESET}")
        print(f"  {CYAN}Network: {self.current_network.handle}{RESET}")
        print(f"  {CYAN}IP Range: {self.current_network.network_addr()}{RESET}")
        print(f"  {CYAN}Nodes: {len(self.current_network.nodes)}  |  Difficulty: {'█' * difficulty}{'░' * (5 - difficulty)}{RESET}")
        print()

    def check_trace(self):
        """Check if we've been traced out."""
        return self.trace_level >= self.max_trace

    def mission_complete(self):
        """Check if all nodes in the network are cracked."""
        if self.current_network is None:
            return False
        return all(n["cracked"] for n in self.current_network.nodes)

    def show_help(self):
        """Display help."""
        help_text = f"""
{CYAN}{'═' * 60}
  COMMAND REFERENCE
{'═' * 60}{RESET}

{BOLD}Navigation & Info:{RESET}
  {GREEN}status{RESET}          Show current mission status
  {GREEN}nodes{RESET}           List network nodes
  {GREEN}help{RESET}            Show this help
  {GREEN}history{RESET}         Show recent command history
  {GREEN}clear{RESET}           Clear the terminal screen
  {GREEN}whoami{RESET}          Display your hacker identity
  {GREEN}score{RESET}           Show detailed score breakdown
  {GREEN}quit{RESET}            Disconnect and exit

{BOLD}Hacking:{RESET}
  {GREEN}crack <n>{RESET}       Attempt to crack node #n
  {GREEN}analyze <n>{RESET}     Recon node #n — reveals code hints (costs trace)
  {GREEN}download <n>{RESET}    Download files from cracked node #n
  {GREEN}deploy <tool>{RESET}   Deploy a special tool

{BOLD}Tools (earned through gameplay):{RESET}
  {MAGENTA}tracecut{RESET}      Reduce trace level by 15-35%
  {MAGENTA}nuke{RESET}          Crack all remaining nodes (big trace hit)
  {MAGENTA}stealth{RESET}       Reduce trace by 25%
  {MAGENTA}overclock{RESET}     Reduce all node difficulties by 1 (trace -15%)
  {MAGENTA}shield{RESET}        Increase max trace by 30%

{BOLD}Save/Load:{RESET}
  {GREEN}save{RESET}            Save current progress
  {GREEN}scores{RESET}          Show high score table

{BOLD}Tips:{RESET}
  • Use {GREEN}analyze <n>{RESET} before cracking — it reveals code hints!
  • Each crack attempt increases trace — be strategic!
  • Partial code matches (≥50%) still crack the node but increase trace.
  • If trace reaches {RED}max{RESET}, you're caught — game over!
  • Your game auto-saves after each mission victory.
"""
        print(help_text)

    def show_score_breakdown(self):
        """Show detailed score and stats."""
        crack_pct = (self.total_cracks_succeeded / self.total_cracks_attempted * 100
                     ) if self.total_cracks_attempted > 0 else 0

        print(f"\n{CYAN}{'═' * 60}")
        print(f"  SCORE BREAKDOWN")
        print(f"{'═' * 60}{RESET}\n")
        print(f"  {BOLD}Total Score:{RESET}       {self.score}")
        print(f"  {BOLD}Networks Cracked:{RESET}  {self.networks_cracked}")
        print(f"  {BOLD}Files Stolen:{RESET}      {self.files_stolen}")
        print(f"  {BOLD}Crack Success Rate:{RESET} {crack_pct:.0f}% "
              f"({self.total_cracks_succeeded}/{self.total_cracks_attempted})")
        print(f"  {BOLD}Nodes Analyzed:{RESET}    {self.total_analyses}")

        if self.current_network:
            net = self.current_network
            cracked = net.cracked_count()
            total = net.total_nodes()
            print(f"\n  {DIM}Current Network:{RESET}")
            print(f"    {DIM}Target: {net.corp}  |  Progress: {cracked}/{total} nodes{RESET}")
            print(f"    {DIM}Trace: {int(self.trace_level)}/{self.max_trace}{RESET}")

        # Tools available
        special_tools = self.tools_unlocked - {"scan", "crack", "download"}
        if special_tools:
            tools_str = ", ".join(f"{MAGENTA}{t}{RESET}" for t in special_tools)
            print(f"\n  {DIM}Available tools: {tools_str}{RESET}")

        print(f"\n{CYAN}{'═' * 60}{RESET}\n")

    def show_history(self):
        """Show command history."""
        if not self.command_history:
            print(f"\n  {YELLOW}No commands in history yet.{RESET}\n")
            return

        print(f"\n{CYAN}{'─' * 40}")
        print(f"  COMMAND HISTORY (last 20)")
        print(f"{'─' * 40}{RESET}\n")

        for i, cmd in enumerate(self.command_history[-20:], 1):
            print(f"  {DIM}{i:>3}.{RESET} {cmd}")

        print()

    def show_whoami(self):
        """Fun flavor command — display a hacker identity."""
        random.seed(hash(str(self.score) + str(self.networks_cracked)))
        alias = random.choice(HACKER_ALIASES)
        codename = f"{random.choice(ADJECTIVES).title()}{random.choice(NOUNS).title()}"
        random.seed()  # Reset seed

        print(f"\n  {GREEN}{BOLD}{alias}{RESET} {DIM}aka{RESET} {GREEN}{codename}{RESET}")
        print(f"  {DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
        print(f"  {DIM}Networks compromised:{RESET}  {BOLD}{self.networks_cracked}{RESET}")
        print(f"  {DIM}Files exfiltrated:{RESET}     {BOLD}{self.files_stolen}{RESET}")
        print(f"  {DIM}Reputation score:{RESET}     {BOLD}{self.score}{RESET}")
        print(f"  {DIM}Trust level:{RESET}           {RED if self.trace_level > 50 else YELLOW if self.trace_level > 25 else GREEN}{100 - int(self.trace_level)}%{RESET}")
        print(f"  {DIM}Active since:{RESET}          {DIM}session start{RESET}")
        print(f"  {DIM}Status:{RESET}                {GREEN}ONLINE{RESET} {DIM}│{RESET} {GREEN}MASKED{RESET} {DIM}│{RESET} {GREEN}STEALTH{RESET}")
        print()

    def game_over(self):
        """Trace detected — game over."""
        self.clear()
        print(f"\n\n{RED}{BOLD}")
        glitch_text("  ██╗   ██╗ █████╗ ███╗   ██╗██████╗  ██████╗ ███╗   ███╗███████╗", iterations=4, delay=0.02)
        glitch_text("  ╚██╗ ██╔╝██╔══██╗████╗  ██║██╔══██╗██╔═══██╗████╗ ████║██╔════╝", iterations=4, delay=0.02)
        glitch_text("   ╚████╔╝ ███████║██╔██╗ ██║██║  ██║██║   ██║██╔████╔██║█████╗  ", iterations=4, delay=0.02)
        glitch_text("    ╚██╔╝  ██╔══██║██║╚██╗██║██║  ██║██║   ██║██║╚██╔╝██║██╔══╝  ", iterations=4, delay=0.02)
        glitch_text("     ██║   ██║  ██║██║ ╚████║██████╔╝╚██████╔╝██║ ╚═╝ ██║███████╗", iterations=4, delay=0.02)
        glitch_text("     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚══════╝", iterations=4, delay=0.02)
        print(f"{RESET}")
        time.sleep(0.5)
        print(f"\n  {RED}Trace detected. Your location has been triangulated.{RESET}")
        print(f"  {RED}Connection terminated by remote host.{RESET}")
        print()

    def mission_victory(self):
        """All nodes cracked — mission success."""
        bonus = max(0, (self.max_trace - int(self.trace_level)) * 10)
        self.score += bonus
        self.networks_cracked += 1

        print(f"\n\n{GREEN}{BOLD}")
        glitch_text("  ★★★ MISSION COMPLETE ★★★", iterations=6, delay=0.03)
        print(f"{RESET}")

        print(f"  {GREEN}All nodes in {self.current_network.corp} compromised!{RESET}")
        print(f"  {GREEN}Low-trace bonus: +{bonus} pts{RESET}")
        print(f"  {GREEN}Total Score: {BOLD}{self.score}{RESET}")
        print()

        # Auto-save after mission victory
        save_game(self)

    def run(self, skip_boot=False, start_difficulty=None):
        """Main game loop."""
        try:
            if not skip_boot:
                self.boot_sequence()
            else:
                self.clear()
                print(f"  {GREEN}{BOLD}Terminal Hacker v{VERSION} — Quick Start{RESET}")
                print(f"  {DIM}Boot sequence skipped.{RESET}\n")
            self.generate_network(difficulty=start_difficulty)

            while self.running:
                try:
                    self.show_status()

                    if self.check_trace():
                        self.game_over()
                        # Save high score on game over
                        save_high_score(self.score, self.networks_cracked, self.files_stolen)
                        break

                    if self.mission_complete():
                        self.mission_victory()
                        print(f"\n  {CYAN}Connect to next target? [Y/n]{RESET} ", end="")
                        try:
                            cont = input().strip().lower()
                        except EOFError:
                            cont = "y"
                        if cont in ("n", "no", "q", "quit"):
                            # Save high score on voluntary exit after victory
                            save_high_score(self.score, self.networks_cracked, self.files_stolen)
                            break
                        self.generate_network()
                        continue

                    print(f"  {BOLD}{GREEN}hack>{RESET} ", end="")
                    sys.stdout.flush()

                    try:
                        cmd = input().strip().lower()
                    except EOFError:
                        print()
                        break

                    if not cmd:
                        continue

                    # Record command in history
                    self.command_history.append(cmd)

                    parts = cmd.split()
                    action = parts[0]

                    if action in ("quit", "exit", "q"):
                        print(f"\n  {DIM}Disconnecting...{RESET}")
                        save_high_score(self.score, self.networks_cracked, self.files_stolen)
                        break
                    elif action == "help" or action == "?":
                        self.show_help()
                    elif action == "status":
                        self.show_status()
                        continue  # Don't re-show status below
                    elif action == "nodes":
                        self.show_nodes()
                    elif action == "crack":
                        if len(parts) > 1 and parts[1].isdigit():
                            self.crack_node(int(parts[1]))
                        else:
                            print(f"{RED}Usage: crack <node_number>{RESET}")
                    elif action == "analyze" or action == "recon":
                        if len(parts) > 1 and parts[1].isdigit():
                            self.analyze_node(int(parts[1]))
                        else:
                            print(f"{RED}Usage: analyze <node_number>{RESET}")
                    elif action == "download" or action == "dl":
                        if len(parts) > 1 and parts[1].isdigit():
                            self.download_files(int(parts[1]))
                        else:
                            print(f"{RED}Usage: download <node_number>{RESET}")
                    elif action == "deploy":
                        if len(parts) > 1:
                            self.deploy_tool(parts[1])
                        else:
                            avail = self.tools_unlocked - {"scan", "crack", "download"} or {"none"}
                            avail_str = ", ".join(avail)
                            print(f"{YELLOW}Available tools: {avail_str}{RESET}")
                    elif action == "scan":
                        self.show_nodes()
                    elif action == "save":
                        if save_game(self):
                            print(f"\n  {GREEN}✓ Game saved successfully.{RESET}")
                            print(f"  {DIM}Save location: {SAVE_FILE}{RESET}\n")
                        else:
                            print(f"\n  {RED}✗ Failed to save game.{RESET}\n")
                    elif action == "scores" or action == "highscores" or action == "leaderboard":
                        show_high_scores()
                    elif action == "history" or action == "h":
                        self.show_history()
                    elif action == "clear" or action == "cls":
                        self.clear()
                    elif action == "whoami":
                        self.show_whoami()
                    elif action == "score" or action == "stats":
                        self.show_score_breakdown()
                    else:
                        print(f"{RED}Unknown command: {action}. Type 'help' for commands.{RESET}")

                except KeyboardInterrupt:
                    print(f"\n\n  {YELLOW}Connection interrupted by user.{RESET}")
                    save_high_score(self.score, self.networks_cracked, self.files_stolen)
                    break

            # Final score display
            print(f"\n{CYAN}{'═' * 60}")
            print(f"  SESSION ENDED")
            print(f"{'═' * 60}{RESET}")
            print(f"  Final Score: {BOLD}{self.score}{RESET}")
            print(f"  Networks Cracked: {self.networks_cracked}")
            print(f"  Files Exfiltrated: {self.files_stolen}")
            crack_pct = (self.total_cracks_succeeded / self.total_cracks_attempted * 100
                        ) if self.total_cracks_attempted > 0 else 0
            print(f"  Crack Success Rate: {crack_pct:.0f}%")
            print(f"{CYAN}{'═' * 60}{RESET}\n")

        except Exception as e:
            print(f"\n{RED}FATAL ERROR: {e}{RESET}")
            raise


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="hack_sim",
        description="Terminal Hacker Simulator — A cinematic hacking simulation game.",
    )
    parser.add_argument("--version", "-v", action="version", version=f"Terminal Hacker Simulator v{VERSION}")
    parser.add_argument("--skip-boot", "-s", action="store_true", help="Skip the cinematic boot sequence")
    parser.add_argument("--difficulty", "-d", type=int, choices=range(1, 6), metavar="1-5",
                        help="Starting difficulty (1-5, default scales with missions)")
    args = parser.parse_args()

    print(HIDE_CURSOR)
    try:
        game = HackerSimulator()
        game.run(skip_boot=args.skip_boot, start_difficulty=args.difficulty)
    finally:
        print(SHOW_CURSOR)


if __name__ == "__main__":
    main()