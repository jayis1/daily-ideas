#!/usr/bin/env python3
"""
Terminal Hacker Simulator — A cinematic hacking simulation game.
Break into procedurally generated networks, crack passwords, bypass firewalls,
exfiltrate data, and race against the clock before you're traced.
"""

import random
import time
import sys
import os
import shutil
import string
import textwrap
from collections import OrderedDict

# ── ANSI helpers ──────────────────────────────────────────────────────────────

ESC = "\033["
BOLD = f"{ESC}1m"
DIM = f"{ESC}2m"
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
    w = width or TERMINAL_W
    return text.center(w)


def slow_print(text, delay=0.02, end=""):
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
    lines = []
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
    "net", "grid", "node", "core", "vault", "gate", "vault", "mainframe",
    "sector", "daemon", "spider", "wolf", "fox", "raven", "viper",
    "matrix", "archive", "tower", "vault", "fortress", "engine",
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
        count = 3 + self.difficulty
        node_types = ["gateway", "proxy", "database", "workstation", "server", "firewall"]
        for i in range(count):
            node = {
                "type": random.choice(node_types),
                "ip": f"{random.choice(IP_PREFIXES)}.{random.randint(1,254)}.{random.randint(1,254)}",
                "name": f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}-{random.randint(10,99)}",
                "difficulty": random.randint(1, self.difficulty + 1),
                "cracked": False,
                "files": random.sample(FILE_NAMES, k=random.randint(1, 3)),
            }
            self.nodes.append(node)

    @property
    def total_difficulty(self):
        return sum(n["difficulty"] for n in self.nodes)


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

    def clear(self):
        sys.stdout.write(CLEAR)
        sys.stdout.flush()

    def banner(self):
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
            f"{GREEN}{BOLD}  ║           T E R M I N A L   H A C K E R   v2.6          ║",
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
        trace_pct = int(self.trace_level)
        trace_bar_filled = int(trace_pct / 4)
        trace_bar = "█" * trace_bar_filled + "░" * (25 - trace_bar_filled)

        trace_color = GREEN if trace_pct < 40 else (YELLOW if trace_pct < 70 else RED)

        print(f"\n{CYAN}{'─' * 60}")
        print(f"  TARGET: {BOLD}{net.corp}{RESET}  ({net.handle})")
        print(f"  IP: {net.ip}  |  Nodes: {len(net.nodes)}  |  Difficulty: {'█' * net.difficulty}{'░' * (5 - net.difficulty)}")
        print(f"  TRACE: [{trace_color}{trace_bar}{RESET}] {trace_color}{trace_pct}%{RESET}")
        print(f"  SCORE: {BOLD}{self.score}{RESET}  |  Networks: {self.networks_cracked}  |  Files: {self.files_stolen}")
        print(f"{CYAN}{'─' * 60}{RESET}\n")

    def show_nodes(self):
        """Display network nodes with their status."""
        net = self.current_network
        print(f"\n{CYAN}{'═' * 60}")
        print(f"  NETWORK MAP: {net.corp}")
        print(f"{'═' * 60}{RESET}\n")

        for i, node in enumerate(net.nodes):
            status_icon = f"{GREEN}✓{RESET}" if node["cracked"] else f"{RED}✗{RESET}"
            diff_bar = "█" * node["difficulty"] + "░" * (6 - node["difficulty"])
            print(f"  [{i+1}] {status_icon} {BOLD}{node['name']:<25}{RESET} {DIM}({node['type']}){RESET}")
            print(f"      IP: {node['ip']}  |  Security: {diff_bar}  |  Files: {len(node['files'])}")
            if node["cracked"]:
                print(f"      {DIM}Files: {', '.join(node['files'])}{RESET}")
            print()

    def crack_node(self, node_idx):
        """Attempt to crack a node with a mini-game."""
        if node_idx < 1 or node_idx > len(self.current_network.nodes):
            print(f"{RED}Invalid node number.{RESET}")
            return

        node = self.current_network.nodes[node_idx - 1]

        if node["cracked"]:
            print(f"{YELLOW}Node '{node['name']}' already compromised.{RESET}")
            return

        difficulty = node["difficulty"]
        self.trace_level += difficulty * 3

        print(f"\n{YELLOW}▶ Targeting: {BOLD}{node['name']}{RESET}")
        print(f"{YELLOW}▶ Type: {node['type']}  |  Security Level: {difficulty}{RESET}\n")

        # Phase 1: Scan
        verb = random.choice(HACK_VERBS)
        noun = random.choice(HACK_NOUNS)
        print(f"  {CYAN}{verb.lower()} {noun}...{RESET}")
        progress_bar(f"  Scanning {node['ip']}", length=25 + difficulty * 5, speed=0.015)

        # Phase 2: Crack password mini-game
        print(f"\n  {MAGENTA}⚡ CRACKING ACCESS CODE{RESET}\n")

        # Generate a code the player must type
        code_length = 4 + difficulty
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=code_length))
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
            print(f"\n  {GREEN}{BOLD}★ PERFECT CRACK! ★{RESET}")
            print(f"  {GREEN}Node '{node['name']}' compromised! +{points} pts{RESET}")
            glitch_text(f"  ACCESS GRANTED — {node['ip']}")
        elif match_count >= total * 0.5:
            # Partial crack
            node["cracked"] = True
            points = difficulty * 80
            self.score += points
            self.trace_level += difficulty * 5
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
        if node_idx < 1 or node_idx > len(self.current_network.nodes):
            print(f"{RED}Invalid node number.{RESET}")
            return

        node = self.current_network.nodes[node_idx - 1]

        if not node["cracked"]:
            print(f"{RED}Node not compromised. Crack it first.{RESET}")
            return

        files = node["files"]
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
        if tool_name == "tracecut":
            print(f"\n  {MAGENTA}⚡ DEPLOYING TRACE CUTTER{RESET}")
            progress_bar("  Neutralizing trace", length=20, speed=0.025)
            reduction = min(self.trace_level, random.randint(15, 35))
            self.trace_level -= reduction
            print(f"  {GREEN}Trace reduced by {reduction}%!{RESET}")
            self.tools_unlocked.discard("tracecut")

        elif tool_name == "nuke":
            print(f"\n  {RED}{BOLD}⚡ DEPLOYING NETWORK NUKE{RESET}")
            for node in self.current_network.nodes:
                if not node["cracked"]:
                    node["cracked"] = True
                    self.score += 50
            self.trace_level += 20
            print(f"  {RED}All nodes cracked! But trace increased by 20%{RESET}")
            self.tools_unlocked.discard("nuke")

        elif tool_name == "stealth":
            print(f"\n  {CYAN}⚡ DEPLOYING STEALTH MODULE{RESET}")
            progress_bar("  Cloaking", length=15, speed=0.02)
            self.trace_level = max(0, self.trace_level - 25)
            print(f"  {GREEN}Stealth active! Trace reduced by 25%{RESET}")
            self.tools_unlocked.discard("stealth")
        else:
            print(f"{RED}Unknown tool: {tool_name}{RESET}")

    def generate_network(self, difficulty=None):
        """Generate a new network to hack."""
        if difficulty is None:
            difficulty = min(1 + self.networks_cracked, 5)
        self.current_network = Network(difficulty=difficulty)
        self.trace_level = 0

        # Chance to unlock tools
        if random.random() < 0.4:
            tool = random.choice(["tracecut", "nuke", "stealth"])
            if tool not in self.tools_unlocked:
                self.tools_unlocked.add(tool)
                print(f"\n  {MAGENTA}★ NEW TOOL UNLOCKED: {BOLD}{tool.upper()}{RESET}")
                print(f"  {DIM}Use 'deploy {tool}' to activate it.{RESET}")

        print(f"\n{GREEN}{BOLD}  ▶ NEW TARGET ACQUIRED{RESET}")
        print(f"  {CYAN}Corporation: {BOLD}{self.current_network.corp}{RESET}")
        print(f"  {CYAN}Network: {self.current_network.handle}{RESET}")
        print(f"  {CYAN}IP Range: {self.current_network.ip}.0/24{RESET}")
        print(f"  {CYAN}Nodes: {len(self.current_network.nodes)}  |  Difficulty: {'█' * difficulty}{'░' * (5 - difficulty)}{RESET}")
        print()

    def check_trace(self):
        """Check if we've been traced out."""
        if self.trace_level >= self.max_trace:
            return True
        return False

    def mission_complete(self):
        """Check if all nodes in the network are cracked."""
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
  {GREEN}quit{RESET}            Disconnect and exit

{BOLD}Hacking:{RESET}
  {GREEN}crack <n>{RESET}       Attempt to crack node #n
  {GREEN}download <n>{RESET}    Download files from cracked node #n
  {GREEN}deploy <tool>{RESET}   Deploy a special tool

{BOLD}Tools (earned through gameplay):{RESET}
  {MAGENTA}tracecut{RESET}      Reduce trace level by 15-35%
  {MAGENTA}nuke{RESET}          Crack all remaining nodes (big trace hit)
  {MAGENTA}stealth{RESET}       Reduce trace by 25%

{BOLD}Tips:{RESET}
  • Each crack attempt increases trace — be strategic!
  • Partial code matches (≥50%) still crack the node but increase trace.
  • If trace reaches 100%, you're caught — game over!
  • Crack all nodes to complete the mission and score a bonus.
"""
        print(help_text)

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
        print(f"\n  {DIM}Final Score: {BOLD}{self.score}{RESET}")
        print(f"  {DIM}Networks Cracked: {self.networks_cracked}{RESET}")
        print(f"  {DIM}Files Exfiltrated: {self.files_stolen}{RESET}")
        print()

    def mission_victory(self):
        """All nodes cracked — mission success."""
        bonus = max(0, (100 - int(self.trace_level)) * 10)
        self.score += bonus
        self.networks_cracked += 1

        print(f"\n\n{GREEN}{BOLD}")
        glitch_text("  ★★★ MISSION COMPLETE ★★★", iterations=6, delay=0.03)
        print(f"{RESET}")

        print(f"  {GREEN}All nodes in {self.current_network.corp} compromised!{RESET}")
        print(f"  {GREEN}Low-trace bonus: +{bonus} pts{RESET}")
        print(f"  {GREEN}Total Score: {BOLD}{self.score}{RESET}")
        print()

    def run(self):
        """Main game loop."""
        try:
            self.boot_sequence()
            self.generate_network()

            while self.running:
                try:
                    self.show_status()

                    if self.check_trace():
                        self.game_over()
                        break

                    if self.mission_complete():
                        self.mission_victory()
                        print(f"\n  {CYAN}Connect to next target? [Y/n]{RESET} ", end="")
                        try:
                            cont = input().strip().lower()
                        except EOFError:
                            cont = "y"
                        if cont in ("n", "no", "q", "quit"):
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

                    parts = cmd.split()
                    action = parts[0]

                    if action in ("quit", "exit", "q"):
                        print(f"\n  {DIM}Disconnecting...{RESET}")
                        break
                    elif action == "help" or action == "?":
                        self.show_help()
                    elif action == "status":
                        pass  # status shown every loop
                    elif action == "nodes":
                        self.show_nodes()
                    elif action == "crack":
                        if len(parts) > 1 and parts[1].isdigit():
                            self.crack_node(int(parts[1]))
                        else:
                            print(f"{RED}Usage: crack <node_number>{RESET}")
                    elif action == "download" or action == "dl":
                        if len(parts) > 1 and parts[1].isdigit():
                            self.download_files(int(parts[1]))
                        else:
                            print(f"{RED}Usage: download <node_number>{RESET}")
                    elif action == "deploy":
                        if len(parts) > 1:
                            self.deploy_tool(parts[1])
                        else:
                            avail = ", ".join(self.tools_unlocked - {"scan", "crack", "download"}) or "none"
                            print(f"{YELLOW}Available tools: {avail}{RESET}")
                    elif action == "scan":
                        self.show_nodes()
                    else:
                        print(f"{RED}Unknown command: {action}. Type 'help' for commands.{RESET}")

                except KeyboardInterrupt:
                    print(f"\n\n  {YELLOW}Connection interrupted by user.{RESET}")
                    break

            # Final score display
            print(f"\n{CYAN}{'═' * 60}")
            print(f"  SESSION ENDED")
            print(f"{'═' * 60}{RESET}")
            print(f"  Final Score: {BOLD}{self.score}{RESET}")
            print(f"  Networks Cracked: {self.networks_cracked}")
            print(f"  Files Exfiltrated: {self.files_stolen}")
            print(f"{CYAN}{'═' * 60}{RESET}\n")

        except Exception as e:
            print(f"\n{RED}FATAL ERROR: {e}{RESET}")
            raise


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(HIDE_CURSOR)
    try:
        game = HackerSimulator()
        game.run()
    finally:
        print(SHOW_CURSOR)