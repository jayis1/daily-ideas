# Terminal Tower Defense v2.1

A fully playable tower defense game rendered entirely in the terminal using ASCII art and `curses`. Strategically place and upgrade towers to defend against waves of increasingly tough enemies — with 6 tower types, 6 enemy types, 3 difficulty modes, auto-wave, fast-forward, per-tower kill tracking, and persistent high scores!

## Features

### Towers (6 Types)
- **Arrow** (50g) — Cheap, fast-firing. Great for early waves.
- **Cannon** (100g) — Splash damage (1 tile). Best near path bends.
- **Ice** (75g) — Slows enemies 50%. Synergizes with Snipers.
- **Sniper** (120g) — Long range, high damage, slow fire rate.
- **Mortar** (150g) — Area bombardment (2 tile splash). Devastating at chokepoints.
- **Lightning** (130g) — Chains to up to 3 nearby enemies at 70% damage per bounce.

### Enemies (6 Types)
- **Grunt** — Standard fodder.
- **Scout** — Fast but fragile.
- **Swarm** — Weak but spawns in packs from wave 3+.
- **Brute** — Tanky, slow, high HP.
- **Medic** — Heals nearby allies within 2 tiles.
- **Overlord** — Boss every 5th wave. Massive HP.

### Gameplay
- **Upgrade System**: Upgrade towers up to level 5, increasing damage, range, and chain count (Lightning).
- **Sell Towers**: Get 50% refund of total invested gold when selling.
- **Progressive Difficulty**: Enemies scale with wave number. Boss waves every 5th wave.
- **3 Difficulty Modes**: Easy (300g/30 lives), Normal (200g/20 lives), Hard (150g/10 lives).
- **Auto-Wave**: Press `a` to automatically start the next wave after clearing.
- **Fast-Forward**: Press `f` to double game speed.
- **Kill Tracking**: Each tower tracks its own kill count, shown in the sidebar.
- **Hit Flash**: Enemies briefly show `!` when damaged.
- **Splash Damage Falloff**: Cannon/Mortar damage decreases with distance from center.
- **Persistent High Scores**: Top 10 scores saved to `highscores.json`.
- **Game Over Screen**: Shows final score, waves survived, kills, and difficulty.
- **Restart**: Press `r` after game over to play again without restarting the program.
- **Pathfinding**: Enemies follow a winding path with smooth interpolation.
- **Visual Range Indicator**: See tower range before placement.
- **Colorful ASCII Display**: Full color rendering with health bars and projectile animations.
- **In-Game Log**: Real-time feedback on placement, kills, and wave status.

## How to Install

No external dependencies required! Just Python 3.7+ with the standard `curses` module (included on macOS/Linux).

```bash
# Clone or download the project
cd 2026-07-02-terminal-tower-defense
```

That's it — no pip install needed.

## How to Run

```bash
python3 tower_defense.py
```

Optional flags:

```bash
python3 tower_defense.py --difficulty hard    # Skip difficulty menu, start on hard
python3 tower_defense.py --difficulty easy    # Skip menu, start on easy
python3 tower_defense.py --version            # Show version and exit
python3 tower_defense.py --help               # Show usage info
```

> **Note**: Must be run in a real terminal (not an IDE output panel). Requires a terminal that supports color and at least 84×28 characters.

## Controls

| Key | Action |
|-----|--------|
| `←`/`→`/`↑`/`↓` or `h`/`l`/`k`/`j` | Move cursor |
| `1` | Place Arrow tower (50g) |
| `2` | Place Cannon tower (100g) |
| `3` | Place Ice tower (75g) |
| `4` | Place Sniper tower (120g) |
| `5` | Place Mortar tower (150g) |
| `6` | Place Lightning tower (130g) |
| `Tab` | Cycle tower selection |
| `u` | Upgrade tower under cursor |
| `s` | Sell tower under cursor (50% refund) |
| `Space` | Start next wave |
| `a` | Toggle auto-wave mode |
| `f` | Toggle fast-forward (2x speed) |
| `p` | Pause/unpause |
| `r` | Restart (after game over) |
| `q` / `Esc` | Quit |

## Gameplay Guide

1. **Start**: Choose a difficulty at the title screen (or use `--difficulty` to skip it). You begin with gold and lives based on difficulty.
2. **Place Towers**: Move the cursor to an empty tile (`·`) and press `1`-`6` to place a tower.
3. **Start a Wave**: Press `Space` to send the next wave. Enemies follow the brown path (`█`).
4. **Upgrade & Sell**: Press `u` to upgrade or `s` to sell a tower under the cursor.
5. **Survive**: Each enemy that reaches the end costs 1+ lives. If lives reach 0, game over!
6. **Boss Waves**: Every 5th wave features a powerful Overlord enemy.
7. **Auto-Wave**: Press `a` to automatically chain waves — great for experienced players.

## Strategy Tips

- **Arrow towers** are cheap and great for early waves. Place them along straight path sections.
- **Ice towers** slow enemies, making them take more hits from other towers. Combine with Snipers!
- **Cannon and Mortar** towers deal splash damage — place them near path bends where enemies cluster.
- **Sniper towers** have long range but slow fire rate — place them in central positions.
- **Lightning towers** chain damage to groups — devastating against Swarm packs.
- **Medic enemies** heal nearby foes — prioritize them!
- Upgrade key towers rather than placing many cheap ones.
- Use `f` for fast-forward during easier waves, and `a` to auto-advance.

## Tower Stats

| Tower | Cost | Damage | Range | Fire Rate | Special |
|-------|------|--------|-------|-----------|---------|
| Arrow | 50g | 8 | 4 | Fast (6) | — |
| Cannon | 100g | 25 | 3 | Medium (12) | Splash (1 tile) |
| Ice | 75g | 4 | 4 | Medium (8) | 50% Slow |
| Sniper | 120g | 50 | 8 | Slow (20) | — |
| Mortar | 150g | 40 | 5 | Slow (18) | Splash (2 tiles) |
| Lightning | 130g | 15 | 5 | Medium (14) | Chains to 3 targets |

## Changelog

### v2.1 — Bug Fixes
- **Fixed double-counting of kills from Lightning chain damage**: Chain kills were incrementing `total_kills` in both `_apply_projectile_hit()` and `update()`, causing chain kills to be counted twice. Now kills are only counted once in `update()`.
- **Fixed tower kill tracking**: `Tower.kills` was initialized to 0 but never incremented. Now each tower correctly tracks its own kills via the `killed_by` field on enemies, and kill counts are displayed in the sidebar.
- **Fixed `--difficulty` CLI flag being ignored**: The `--difficulty` command-line flag was setting a global variable but `main()` always called `select_difficulty()` which overwrote it. Now the menu is skipped when a valid difficulty is pre-selected via CLI.
- **Fixed `start_wave()` allowing wave start after game over**: After game over, pressing Space would still increment `wave_num` and set `wave_active`. Now `start_wave()` checks for `game_over` and refuses to start a new wave.
- **Fixed potential double high score save**: If multiple enemies reached the end in the same frame while lives dropped to 0 or below, `save_highscore()` could be called multiple times. Now a `not self.game_over` guard prevents this.
- **Fixed negative lives display**: Lives could go negative when multiple enemies reached the end in the same frame. The display now shows `max(0, lives)` to avoid showing negative numbers.
- **Added `source_tower` to Projectile**: Projectiles now track which tower fired them, enabling per-tower kill counting.
- **Added `killed_by` to Enemy**: Enemies now track which tower dealt the killing blow (first to kill), enabling kill attribution.

## Running Tests

```bash
python3 -m pytest test_tower_defense.py -v
```

The test suite covers path building, enemy mechanics, tower upgrades/selling, game state, wave generation, high scores, version formatting, and regression tests for all fixed bugs — 46 tests total.