# Terminal Hacker Simulator

A cinematic hacking simulation game played entirely in the terminal. Break into procedurally generated corporate networks, crack access codes, bypass firewalls, exfiltrate data, and race against an ever-rising trace meter before you're caught.

## Features

- **Cinematic boot sequence** — Animated startup with glitch effects, matrix rain, and progress bars that make you feel like a movie hacker
- **Procedural networks** — Every mission generates a unique corporate network with randomized names, IPs, node types, and difficulty levels
- **Code-cracking mini-game** — Crack nodes by typing access codes; partial matches still work but increase your trace
- **Trace system** — Every action increases your trace level; hit 100% and you're caught. Play strategically!
- **Special tools** — Earn unlockable tools like `tracecut`, `nuke`, and `stealth` through gameplay
- **Escalating difficulty** — Each successive network gets harder with more nodes and tougher security
- **Score tracking** — Earn points for cracking nodes, downloading files, and low-trace completion bonuses
- **Full ANSI art** — Colorful terminal UI with ASCII art banner, status bars, and visual effects

## How to Install

```bash
# No dependencies required — uses only Python 3 standard library
git clone <repo-url>
cd terminal-hacker-simulator
```

No packages to install. Just Python 3.6+.

## How to Run

```bash
python3 hack_sim.py
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

        T E R M I N A L   H A C K E R   v2.6

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
| `crack <n>` | Attempt to crack node #n (interactive code-cracking) |
| `download <n>` | Download files from a cracked node |
| `deploy <tool>` | Use a special tool (tracecut, nuke, stealth) |
| `help` | Show full command reference |
| `quit` | Disconnect and exit |

### Gameplay Flow

1. A new corporate network is generated automatically
2. Use `nodes` to scan and see available targets
3. Use `crack <n>` to attempt breaching a node — you'll need to type an access code
4. Use `download <n>` to exfiltrate files from cracked nodes for points
5. Watch your trace level — if it hits 100%, it's game over
6. Crack all nodes to complete the mission and earn a bonus
7. Move on to the next, harder network

### Example Session

```
hack> nodes

  NETWORK MAP: OmniCorp
════════════════════════════════════════════════════════════

  [1] ✗ shadow-vault-42          (gateway)
      IP: 10.0.47.23  |  Security: ██░░░░  |  Files: 3

  [2] ✗ chrome-engine-15         (database)
      IP: 172.16.208.7  |  Security: ████░░  |  Files: 2

hack> crack 1

▶ Targeting: shadow-vault-42
▶ Type: gateway  |  Security Level: 2

  Scanning 10.0.47.23 [████████████████████████████]

  ⚡ CRACKING ACCESS CODE

  Access code pattern: K3••••

  CODE> K3M7R
  ★ PERFECT CRACK! ★
  Node 'shadow-vault-42' compromised! +300 pts
```

## What It Does

Terminal Hacker Simulator is a single-player terminal game that simulates the Hollywood-style hacking experience. Each run generates a unique corporate network with multiple nodes of varying difficulty. Players must strategically choose which nodes to attack, type access codes under pressure, manage their trace level (which increases with every action), and use earned tools to stay ahead of detection. The game features a full cinematic boot sequence with ANSI animations, glitch effects, and a progress-bar driven cracking system that makes you feel like you're actually breaking into a mainframe — all from the comfort of your terminal.