# Terminal Hacker Simulator

A cinematic hacking simulation game played entirely in the terminal. Break into procedurally generated corporate networks, crack access codes, analyze nodes for intel, deploy special tools, exfiltrate data, and race against an ever-rising trace meter before you're caught. Save your progress between sessions and compete for the top spot on the high score board.

## Features

- **Cinematic boot sequence** — Animated startup with glitch effects, matrix rain, and progress bars
- **Procedural networks** — Every mission generates a unique corporate network with randomized names, IPs, node types, and difficulty levels (1–5)
- **Code-cracking mini-game** — Crack nodes by typing access codes; partial matches (≥50%) still work but increase your trace
- **Node analysis** — Use `analyze <n>` to recon nodes before cracking — reveals code hints at a trace cost
- **Trace system** — Every action increases your trace level; hit the max and you're caught. The status bar shows trace as a percentage of your max (affected by shield)
- **5 special tools** — Earn unlockable tools: `tracecut`, `nuke`, `stealth`, `overclock`, and `shield`
- **Escalating difficulty** — Each successive network gets harder with more nodes and tougher security
- **Score tracking** — Earn points for cracking nodes, downloading files, and low-trace completion bonuses
- **Detailed stats** — View your crack success rate, networks cracked, and more with the `score` command
- **Save & Load** — Auto-saves after every mission victory; manually save anytime with `save`. Persists score, stats, trace level, tools, network state, crack success rate, and command history
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

        T E R M I N A L   H A C K E R   v3.1.0

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
| `tracecut` | Reduce trace level by 15–35 points (one-time use) |
| `nuke` | Crack all remaining nodes instantly (trace +20 points) |
| `stealth` | Reduce trace by 25 points (one-time use) |
| `overclock` | Reduce all node difficulties by 1 + trace −15 points |
| `shield` | Increase max trace by 30 points, giving more headroom |

### Gameplay Flow

1. A new corporate network is generated automatically
2. Use `nodes` or `scan` to see available targets
3. Use `analyze <n>` to get code hints before cracking (costs trace points)
4. Use `crack <n>` to attempt breaching a node — type the access code
5. Use `download <n>` to exfiltrate files from cracked nodes for points
6. Watch your trace level — if it reaches the max (default 100, boosted by shield), it's game over
7. Deploy tools strategically to manage trace and crack tough nodes
8. Crack all nodes to complete the mission and earn a bonus
9. Move on to the next, harder network
10. Your progress auto-saves after each victory; use `scores` to check the leaderboard

### Example Session

```
hack> analyze 1

  ▶ Analyzing: shadow-vault-42
  ▶ Type: gateway  |  Security Level: 2
    Trace cost: +4 points

  Scanning shadow-vault-42 [████████████████████]
  ◈ ANALYSIS COMPLETE
  Node type: gateway  |  Security level: 2
  Access code pattern: K3M•••
  Use 'crack 1' to attempt access.

hack> crack 1

  ▶ Targeting: shadow-vault-42
  ▶ Type: gateway  |  Security Level: 2

  Scanning 10.0.47.0 [████████████████████████████]
  ⚡ CRACKING ACCESS CODE

  Access code pattern: K3M•••

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

Terminal Hacker Simulator is a single-player terminal game that simulates the Hollywood-style hacking experience. Each run generates a unique corporate network with multiple nodes of varying difficulty (1–5). Players can analyze nodes for intel before cracking, strategically manage their trace level, deploy earned tools like overclock and shield, and compete for high scores across sessions. The game features a full cinematic boot sequence with ANSI animations, glitch effects, a progress-bar driven cracking system, persistent save/load (including stats and command history), and a high score leaderboard — all from the comfort of your terminal.

## Save Data

Save files are stored in `~/.config/hack_sim/`:
- `save.json` — Current game state (auto-saved after each mission). Persists: score, networks cracked, files stolen, trace level, max trace, tools unlocked, crack stats, analysis count, and command history.
- `highscores.json` — Top 10 high scores across all sessions

## Testing

```bash
python3 -m pytest test_hack_sim.py -v
```

The test suite includes **77 tests** covering:
- Network generation and structure validation
- IP address format validation
- Node difficulty ranges (capped at 5)
- HackerSimulator initialization
- Crack, download, analyze, and deploy operations
- Trace level tracking with custom max_trace (shield)
- Trace bar display as percentage of max_trace (not absolute)
- Trace bar overflow protection (capped at 25 chars)
- Overclock tool — difficulty reduction with floor of 1, None network guard
- Shield tool — stacking max_trace increases
- Mission completion, victory bonuses, and shield-aware bonuses
- Save/load system — save, load, corrupt files, missing files, directory creation, stats persistence
- High score system — save, sort, limit, display
- Command history tracking and persistence
- Stats tracking (crack success rate, analysis count, save/load roundtrip)
- Edge cases (empty files, invalid inputs, None network guards, deploy overclock/nuke with None network, duplicate data)
- Display bar formatting (difficulty bars now consistently 5 chars wide)
- Version constant format

## Known Issues

None currently known. All identified bugs have been fixed.

## Changelog

### v3.1.0 — Bug Fix Release

**Fixed:**
- **Overclock crash with no network** — `deploy overclock` with `current_network=None` caused `AttributeError`. Added None check alongside nuke (both need a network)
- **Trace bar showed absolute percentage instead of relative** — The status bar showed `trace_level%` regardless of `max_trace`. With shield (max_trace=130), a trace of 65 was shown as "65%" instead of the correct "50%". Now calculated as `trace_level / max_trace * 100`
- **Trace bar overflow** — When `trace_level > max_trace`, the bar could exceed 25 chars producing garbled output. Now capped at 25 chars
- **Difficulty bar inconsistency** — Network difficulty bars were 5 chars wide, but node difficulty bars were 6 chars wide. Now both consistently use 5 chars
- **Node difficulty could exceed 5** — `random.randint(1, difficulty + 1)` for difficulty-5 networks could produce difficulty-6 nodes, breaking the bar display. Now capped at `min(randint(1, difficulty+1), 5)`
- **Save/load didn't persist stats** — `total_cracks_attempted`, `total_cracks_succeeded`, `total_analyses`, and `command_history` were not saved or restored, so they were lost on load. Now fully persisted
- **Misleading trace messages** — Tracecut said "reduced by X%" but used absolute values; stealth said "reduced by 25%" (actually 25 points); overclock said "trace -15%" (actually 15 points); nuke said "trace increased by 20%" (actually 20 points); analyze said "trace cost: +X%" (actually X points). All changed to say "points" instead of "%"
- **Status trace display now shows absolute values** — Added `(current/max)` after the percentage bar for clarity, e.g., `TRACE: [████████████░░░░░░░░░░░░] 50%  (65/130)`

**Added:**
- 7 new tests (77 total, up from 70): overclock None network guard, node difficulty cap at 5, trace bar relative percentage, trace bar overflow protection, save/load stats roundtrip, tracecut non-negative, stealth non-negative

### v3.0.0 — Feature Release

**Added:**
- `analyze <n>` command — recon a node to reveal access code hints before cracking (costs 2× difficulty trace)
- `overclock` tool — reduces all node difficulties by 1 and trace by 15 points
- `shield` tool — increases max trace by 30 points, giving more headroom before game over
- `score` / `stats` command — shows detailed score breakdown, crack success rate, and stats
- `history` command — shows the last 20 commands entered
- `whoami` command — displays a fun hacker identity based on your progress
- `clear` command — clears the terminal screen
- `save` command — manually save game progress to disk
- `scores` / `highscores` / `leaderboard` command — persistent high score table (top 10)
- Auto-save after every mission victory
- High score tracking across sessions
- Save/load system with JSON persistence
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
- `mission_victory` bonus now uses `max_trace` instead of hardcoded 100
- `mission_complete()` returns `False` when `current_network` is `None`
- `deploy` now checks `tools_unlocked` before allowing tool use
- Boot sequence now shows save directory path