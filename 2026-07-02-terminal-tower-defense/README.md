# Terminal Tower Defense v2.3

A fully playable tower defense game rendered entirely in the terminal using ASCII art and `curses`. Strategically place and upgrade towers, deploy power-ups, and defend against waves of increasingly tough enemies — including stealth phantoms that dodge your attacks!

## Features

### Towers (7 Types)
- **Arrow** (50g) — Cheap, fast-firing. Great for early waves.
- **Cannon** (100g) — Splash damage (1 tile). Best near path bends.
- **Ice** (75g) — Slows enemies 50%. Synergizes with Snipers.
- **Sniper** (120g) — Long range, high damage, slow fire rate.
- **Mortar** (150g) — Area bombardment (2 tile splash). Devastating at chokepoints.
- **Lightning** (130g) — Chains to up to 3 nearby enemies at 70% damage per bounce.
- **Poison** (90g) — Applies damage-over-time (poison). Stacks with level upgrades.

### Enemies (7 Types)
- **Grunt** — Standard fodder.
- **Scout** — Fast but fragile.
- **Swarm** — Weak but spawns in packs from wave 3+.
- **Brute** — Tanky, slow, high HP.
- **Medic** — Heals nearby allies within 2 tiles.
- **Overlord** — Boss every 5th wave. Massive HP.
- **Phantom** — Stealth enemy from wave 7+. Phases in/out of visibility and has 30% dodge chance!

### Power-Up System
Earn 1 charge of each power-up per wave cleared:
- **Bomb** (`b` key) — Deals 80 damage to ALL enemies on the map. Great for emergencies!
- **Freeze** (`e` key) — Freezes all enemies in place for 3 seconds. Perfect for boss waves!
- **Gold Rush** (`d` key) — Doubles gold from kills for 5 seconds. Maximize your income!

### Economy
- **Gold Interest** — Earn 5% interest on unspent gold between waves (capped at 500g earned). Rewards strategic saving!
- **Wave Clear Bonus** — Gold bonus for completing each wave.
- **Sell Towers** — Get 50% refund of total invested gold.

### Gameplay
- **Upgrade System**: Upgrade towers up to level 5, increasing damage, range, and special effects.
- **Progressive Difficulty**: Enemies scale with wave number. Boss waves every 5th wave. Stealth enemies from wave 7+.
- **3 Difficulty Modes**: Easy (300g/30 lives), Normal (200g/20 lives), Hard (150g/10 lives).
- **Auto-Wave**: Press `a` to automatically start the next wave after clearing.
- **Fast-Forward**: Press `f` to double game speed.
- **Wave Preview**: See what enemies are coming next in the sidebar.
- **Kill Tracking**: Each tower tracks its own kill count, shown in the sidebar.
- **Hit Flash**: Enemies briefly show `!` when damaged. Poisoned enemies show `p`.
- **Freeze Visual**: Frozen enemies change color during freeze effect.
- **Stealth Mechanic**: Phantom enemies become invisible periodically — towers can't target them while hidden (but splash/chain still hits them!).
- **Poison DOT**: Poison tower applies damage-over-time that ticks each frame.
- **Splash Damage Falloff**: Cannon/Mortar damage decreases with distance from center.
- **Statistics Tracking**: Towers placed, upgrades, sells, total gold earned, and interest earned — all shown on game over.
- **Persistent High Scores**: Top 10 scores saved to `highscores.json` with stats.
- **Game Over Screen**: Shows final score, waves survived, kills, difficulty, and detailed stats.
- **Restart**: Press `r` after game over to play again without restarting the program.
- **Pathfinding**: Enemies follow a winding path with smooth interpolation.
- **Visual Range Indicator**: See tower range before placement.
- **Colorful ASCII Display**: Full color rendering with health bars and projectile animations.
- **In-Game Log**: Real-time feedback on placement, kills, wave status, and power-up usage.

## How to Install

No external dependencies required! Just Python 3.7+ with the standard `curses` module (included on macOS/Linux).

```bash
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
python3 tower_defense.py --help              # Show usage info and power-up guide
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
| `7` | Place Poison tower (90g) |
| `Tab` | Cycle tower selection |
| `u` | Upgrade tower under cursor |
| `s` | Sell tower under cursor (50% refund) |
| `SPACE` | Start next wave |
| `a` | Toggle auto-wave mode |
| `f` | Toggle fast-forward (2x speed) |
| `b` | Use Bomb power-up |
| `e` | Use Freeze power-up |
| `d` | Use Gold Rush power-up |
| `p` | Pause/unpause |
| `r` | Restart (after game over) |
| `q` / `Esc` | Quit |

## Gameplay Guide

1. **Start**: Choose a difficulty at the title screen (or use `--difficulty` to skip it). You begin with gold and lives based on difficulty.
2. **Place Towers**: Move the cursor to an empty tile (`·`) and press `1`-`7` to place a tower.
3. **Start a Wave**: Press `SPACE` to send the next wave. Enemies follow the brown path (`█`).
4. **Use Power-Ups**: You earn 1 charge of each power-up per wave cleared. Use them strategically!
5. **Upgrade & Sell**: Press `u` to upgrade or `s` to sell a tower under the cursor.
6. **Save Gold for Interest**: You earn 5% interest on unspent gold between waves. Save up for big investments!
7. **Survive**: Each enemy that reaches the end costs 1+ lives. If lives reach 0, game over!
8. **Boss Waves**: Every 5th wave features a powerful Overlord enemy.
9. **Stealth Enemies**: From wave 7+, Phantoms appear. They turn invisible periodically and dodge 30% of attacks!

## Strategy Tips

- **Arrow towers** are cheap and great for early waves. Place them along straight path sections.
- **Ice towers** slow enemies, making them take more hits from other towers. Combine with Snipers!
- **Cannon and Mortar** towers deal splash damage — place them near path bends where enemies cluster.
- **Sniper towers** have long range but slow fire rate — place them in central positions.
- **Lightning towers** chain damage to groups — devastating against Swarm packs.
- **Poison towers** deal damage over time — great for tanky Brutes and Overlords. Stack multiple!
- **Medic enemies** heal nearby foes — prioritize them!
- **Phantom enemies** dodge 30% of attacks — use splash damage (Cannon/Mortar) which can't be dodged!
- **Bomb power-up** is great for boss waves when you're overwhelmed.
- **Freeze power-up** buys you time to let towers deal damage.
- **Gold Rush** + finishing a wave = double bonus gold!
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
| Poison | 90g | 3 | 4 | Medium (10) | 3 poison dmg/tick for 5 ticks |

## Running Tests

```bash
python3 -m pytest test_tower_defense.py -v
```

The test suite covers path building, enemy mechanics, tower upgrades/selling, game state, wave generation, power-ups, stealth/dodge, poison, interest, statistics, high scores (including corrupted JSON handling), version formatting, and regression tests for all fixed bugs — 81 tests total.

## Changelog

### v2.3 — Bug Fixes
- **Fixed freeze off-by-one**: Freeze power-up was losing its effect 1 frame early. Enemies could move on what should have been the last frozen frame. Now `freeze_timer` is checked before being decremented, so the full `FREEZE_DURATION` (3 seconds) of freeze is applied correctly.
- **Fixed gold rush off-by-one**: Gold Rush power-up was losing its doubling effect 1 frame early. Kill rewards on the last frame of Gold Rush were not being doubled. Now `gold_rush_timer` is checked before being decremented, so the full `GOLD_RUSH_DURATION` (5 seconds) of double gold is applied correctly.
- **Fixed slow timer ticking during freeze**: When enemies were frozen, their slow timer was still counting down. This meant slow effects would expire while the enemy was frozen, so after freeze ended the enemy would move at full speed instead of slowed. Now slow timers are paused during freeze.
- **Fixed dead enemies still moving after poison kill**: When an enemy was killed by poison damage mid-update, it continued advancing along the path. This could cause a killed enemy to "reach the end" and trigger unexpected path completion logic. Now enemies that die from poison immediately stop moving.
- **Fixed sell refund inflating `total_gold_earned`**: Selling a tower was adding the 50% refund to the `total_gold_earned` statistic, making it appear that more gold was earned than actually was. Sell refunds are now correctly excluded from the earned gold counter.
- **Added 6 new regression tests** covering all five bugs plus a freeze duration exactness test.

### v2.2 — New Features & Improvements
- **Poison Tower** (7th tower type): Applies damage-over-time. Upgradeable poison damage. Visual indicator (`p`) on poisoned enemies.
- **Stealth Enemy (Phantom)**: New enemy type from wave 7+. Phases in/out of visibility and has 30% dodge chance. Towers can't target invisible Phantoms directly, but splash/chain damage still hits them.
- **Power-Up System**: Earn 1 Bomb, 1 Freeze, and 1 Gold Rush charge per wave cleared. Bomb deals 80 AoE damage, Freeze stops all enemies for 3s, Gold Rush doubles kill gold for 5s.
- **Gold Interest**: Earn 5% interest on unspent gold between waves (capped at 500g earned). Rewards strategic saving!
- **Wave Preview**: The sidebar now shows the composition of the next wave before you start it.
- **Game Statistics**: Tracks towers placed, upgrades, sells, total gold earned, and interest earned. Shown on game over and saved with high scores.
- **Enhanced Game Over Screen**: Now shows detailed stats including towers placed, upgrades, gold earned, and interest.
- **`__repr__` methods**: Added informative repr to Enemy and Tower classes for easier debugging.
- **Improved `load_highscores()`**: Now validates that the loaded data is actually a list, handles corrupted JSON gracefully.
- **`describe_wave()` function**: Generates a human-readable wave composition preview.
- **Version bump**: v2.1 → v2.2

### v2.1 — Bug Fixes
- **Fixed double-counting of kills from Lightning chain damage**: Chain kills were incrementing `total_kills` in both `_apply_projectile_hit()` and `update()`, causing chain kills to be counted twice. Now kills are only counted once in `update()`.
- **Fixed tower kill tracking**: `Tower.kills` was initialized to 0 but never incremented. Now each tower correctly tracks its own kills via the `killed_by` field on enemies, and kill counts are displayed in the sidebar.
- **Fixed `--difficulty` CLI flag being ignored**: The `--difficulty` command-line flag was setting a global variable but `main()` always called `select_difficulty()` which overwrote it. Now the menu is skipped when a valid difficulty is pre-selected via CLI.
- **Fixed `start_wave()` allowing wave start after game over**: After game over, pressing Space would still increment `wave_num` and set `wave_active`. Now `start_wave()` checks for `game_over` and refuses to start a new wave.
- **Fixed potential double high score save**: If multiple enemies reached the end in the same frame while lives dropped to 0 or below, `save_highscore()` could be called multiple times. Now a `not self.game_over` guard prevents this.
- **Fixed negative lives display**: Lives could go negative when multiple enemies reached the end in the same frame. The display now shows `max(0, lives)` to avoid showing negative numbers.
- **Added `source_tower` to Projectile**: Projectiles now track which tower fired them, enabling per-tower kill counting.
- **Added `killed_by` to Enemy**: Enemies now track which tower dealt the killing blow (first to kill), enabling kill attribution.