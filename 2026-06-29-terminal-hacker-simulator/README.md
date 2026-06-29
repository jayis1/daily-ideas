# Terminal Hacker Simulator

A cinematic hacking simulation game played entirely in the terminal. Break into procedurally generated corporate networks, crack access codes, analyze nodes for intel, deploy special tools, exfiltrate data, and race against an ever-rising trace meter before you're caught. Save your progress between sessions and compete for the top spot on the high score board.

## Features

- **Cinematic boot sequence** — Animated startup with glitch effects, matrix rain, and progress bars that make you feel like a movie hacker
- **Procedural networks** — Every mission generates a unique corporate network with randomized names, IPs, node types, and difficulty levels
- **Code-cracking mini-game** — Crack nodes by typing access codes; partial matches (≥50%) still work but increase your trace
- **Node analysis** — Use `analyze <n>` to recon nodes before cracking — reveals code hints at a trace cost
- **Trace system** — Every action increases your trace level; hit the max and you're caught. Play strategically!
- **5 special tools** — Earn unlockable tools through gameplay: `tracecut`, `nuke`, `stealth`, `overclock`, and `shield`
- **Escalating difficulty** — Each successive network gets harder with more nodes and tougher security
- **Score tracking** — Earn points for cracking nodes, downloading files, and low-trace completion bonuses
- **Detailed stats** — View your crack success rate, networks cracked, and more with the `score` command
- **Save & Load** — Auto-saves after every mission victory; manually save anytime with `save`
- **High score table** — Compete across sessions with persistent high scores (`scores` command)
- **Command history** — Review your recent commands with `history`
- **Hacker identity** — Run `whoami` for a fun flavor display of your hacker profile
- **Full ANSI art** — Colorful terminal UI with ASCII art banner, status bars, and visual effects
- **CLI flags** — `--version`, `--help`, `--skip-boot`, and `--difficulty` for quick starts
- **Robust error handling** — Graceful handling of missing networks, empty file lists, invalid inputs, and corrupted saves

## How to Install

```bash
# No dependencies required — uses only Python 3 standard library
git clone <repo-url>
cd terminal-hacker-simulator
```

No packages to install. Just Python 3.6+.

## How to Run

```bash
# Normal start (with cinematic boot sequence)
python3 hack_sim.py

# Quick start (skip boot animation)
python3 hack_sim.py --skip-boot

# Set starting difficulty (1-5)
python3 hack_sim.py --difficulty 3

# Show version
python3 hack_sim.py --version

# Show help
python3 hack_sim.py --help
```

Make sure your terminal supports ANSI colors for the full experience. A terminal size of at least 80×24 is recommended.

## Usage Examples

```
  ██╗  ██╗ █████╗  ██████╗██╗  ██╗
  ██║  ██║██╔══██╗██╔════╝██║ ██╔╝
  ███████║███████║██║     █████╔╝
  ██╔══██║██╔══██║██║     ██╔═██╗
  ██║  ██║██║  ██║╚██████╗██║  ██╗
  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝

        T E R M I N A L   H A C K E R   v3.0.0

[BIOS] POST check... OK
[BIOS] Memory test... 32768K OK
[KERNEL] Loading shadow kernel v4.2.1...
[NET] Establishing TOR circuit... 3 relays found
>> CONNECTION ESTABLISHED <<
```

### Commands

| Command | Description |
|---------|-------------|
| `status` | Show current mission status, trace level, and score |
| `nodes` | List all nodes in the current network |
| `scan` | Alias for `nodes` |
| `analyze <n>` | Recon node #n — reveals access code hints (costs trace) |
| `crack <n>` | Attempt to crack node #n (interactive code-cracking) |
| `download <n>` | Download files from a cracked node |
| `deploy <tool>` | Use a special tool (tracecut, nuke, stealth, overclock, shield) |
| `score` | Show detailed score breakdown and stats |
| `history` | Show recent command history |
| `whoami` | Display your hacker identity |
| `save` | Save current progress to disk |
| `scores` | Show the high score leaderboard |
| `clear` | Clear the terminal screen |
| `help` | Show full command reference |
| `quit` | Disconnect and exit |

### Tools

| Tool | Effect |
|------|--------|
| `tracecut` | Reduce trace level by 15–35% (one-time use) |
| `nuke` | Crack all remaining nodes instantly (big trace hit) |
| `stealth` | Reduce trace by 25% (one-time use) |
| `overclock` | Reduce all node difficulties by 1 + trace -15% |
| `shield` | Increase max trace by 30%, giving more headroom |

### Gameplay Flow

1. A new corporate network is generated automatically
2. Use `nodes` or `scan` to see available targets
3. Use `analyze <n>` to get code hints before cracking (costs trace)
4. Use `crack <n>` to attempt breaching a node — type the access code
5. Use `download <n>` to exfiltrate files from cracked nodes for points
6. Watch your trace level — if it hits 100% (or your shield-boosted max), it's game over
7. Deploy tools strategically to manage trace and crack tough nodes
8. Crack all nodes to complete the mission and earn a bonus
9. Move on to the next, harder network
10. Your progress auto-saves after each victory; use `scores` to check the leaderboard

### Example Session

```
hack> analyze 1

  ▶ Analyzing: shadow-vault-42
  ▶ Type: gateway  |  Security Level: 2
    Trace cost: +4%

  Scanning shadow-vault-42 [████████████████████]
  ◈ ANALYSIS COMPLETE
  Node type: gateway  |  Security level: 2
  Access code pattern: K3M••••
  Use 'crack 1' to attempt access.

hack> crack 1

  ▶ Targeting: shadow-vault-42
  ▶ Type: gateway  |  Security Level: 2

  Scanning 10.0.47.0 [████████████████████████████]
  ⚡ CRACKING ACCESS CODE

  Access code pattern: K3M••••

  CODE> K3M7R
  ★ PERFECT CRACK! ★
  Node 'shadow-vault-42' compromised! +300 pts

hack> download 1

  ▼ Downloading from shadow-vault-42...

  payroll_enc.db [████████████████████] ✓
  ✓ payroll_enc.db (150 pts)

hack> score

  ══════════════════════════════════════════════════════════════
  SCORE BREAKDOWN
  ══════════════════════════════════════════════════════════════

  Total Score:       450
  Networks Cracked:  0
  Files Stolen:      1
  Crack Success Rate: 100% (1/1)
  Nodes Analyzed:    1
```

## What It Does

Terminal Hacker Simulator is a single-player terminal game that simulates the Hollywood-style hacking experience. Each run generates a unique corporate network with multiple nodes of varying difficulty. Players can analyze nodes for intel before cracking, strategically manage their trace level, deploy earned tools like overclock and shield, and compete for high scores across sessions. The game features a full cinematic boot sequence with ANSI animations, glitch effects, a progress-bar driven cracking system, persistent save/load, and a high score leaderboard — all from the comfort of your terminal.

## Save Data

Save files are stored in `~/.config/hack_sim/`:
- `save.json` — Current game state (auto-saved after each mission)
- `highscores.json` — Top 10 high scores across all sessions

## Testing

```bash
python3 -m pytest test_hack_sim.py -v
```

The test suite includes **70 tests** covering:
- Network generation and structure validation
- IP address format validation
- Node difficulty ranges
- HackerSimulator initialization
- Crack, download, analyze, and deploy operations
- Trace level tracking with custom max_trace (shield)
- Overclock tool — difficulty reduction with floor of 1
- Shield tool — stacking max_trace increases
- Mission completion, victory bonuses, and shield-aware bonuses
- Save/load system — save, load, corrupt files, missing files, directory creation
- High score system — save, sort, limit, display
- Command history tracking
- Stats tracking (crack success rate, analysis count)
- Edge cases (empty files, invalid inputs, None network guards, duplicate data)
- Display bar formatting
- Version constant format

## Changelog

### v3.0.0 — Feature Release

**Added:**
- `analyze <n>` command — recon a node to reveal access code hints before cracking (costs 2× difficulty trace)
- `overclock` tool — reduces all node difficulties by 1 and trace by 15%
- `shield` tool — increases max trace by 30%, giving more headroom before game over
- `score` / `stats` command — shows detailed score breakdown, crack success rate, and stats
- `history` command — shows the last 20 commands entered
- `whoami` command — displays a fun hacker identity based on your progress
- `clear` command — clears the terminal screen
- `save` command — manually save game progress to disk
- `scores` / `highscores` / `leaderboard` command — persistent high score table (top 10)
- Auto-save after every mission victory
- High score tracking across sessions (stored in `~/.config/hack_sim/highscores.json`)
- Save/load system with JSON persistence (`~/.config/hack_sim/save.json`)
- Progress indicator in status showing cracked/total nodes
- Analyzed node indicators (◎ icon) and code hints in `nodes` display
- `command_history` tracking on HackerSimulator
- Stats tracking: `total_cracks_attempted`, `total_cracks_succeeded`, `total_analyses`
- Tool unlock chance now scales with networks cracked (0.35 + 0.05 per network)
- `deploy` now rejects unavailable tools with a clear message
- High score saved on game over and voluntary quit after victory
- Final session summary includes crack success rate
- `HACKER_ALIASES` list for `whoami` flavor
- 36 new tests (70 total, up from 34)

**Fixed:**
- `mission_victory` bonus now uses `max_trace` instead of hardcoded 100, so shield tool works correctly
- `mission_complete()` now returns `False` when `current_network` is `None` instead of crashing
- `deploy` now checks `tools_unlocked` before allowing tool use
- Boot sequence now shows save directory path

### v2.7.0 — Bug Fix Release

**Fixed:**
- IP range display bug (5 octets → correct CIDR notation)
- Duplicate entries in NOUNS
- Double final score on game over
- Empty file download confusion
- `status` command was a no-op
- NoneType crashes on multiple methods
- Banner version alignment
- Version hardcoded in banner