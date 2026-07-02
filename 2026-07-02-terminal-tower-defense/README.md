# Terminal Tower Defense

A fully playable tower defense game rendered entirely in the terminal using ASCII art and `curses`. Strategically place and upgrade towers to defend against waves of increasingly tough enemies!

## Features

- **5 Tower Types**: Arrow (cheap, fast), Cannon (splash damage), Ice (slows enemies), Sniper (long range, high damage), Mortar (area bombardment)
- **5 Enemy Types**: Grunts, Scouts (fast), Brutes (tanky), Medics (heal nearby), Overlords (bosses)
- **Upgrade System**: Upgrade towers up to level 5, increasing damage and range
- **Sell Towers**: Get 50% refund when selling placed towers
- **Progressive Difficulty**: Enemies scale with wave number; every 5th wave features a boss
- **Pathfinding**: Enemies follow a winding path through the map
- **Visual Range Indicator**: See tower range before placement
- **Colorful ASCII Display**: Full color rendering with health indicators and projectile animations
- **In-Game Log**: Real-time feedback on tower placement, kills, and wave status

## How to Install

No external dependencies required! Just Python 3.7+ with the standard `curses` module (included on macOS/Linux).

```bash
# Clone or download the project
cd terminal-tower-defense
```

That's it — no pip install needed.

## How to Run

```bash
python3 tower_defense.py
```

> **Note**: Must be run in a real terminal (not an IDE output panel). The game requires a terminal that supports color and at least 80×30 characters.

## Controls

| Key | Action |
|-----|--------|
| `←`/`→`/`↑`/`↓` or `h`/`l`/`k`/`j` | Move cursor |
| `1` | Place Arrow tower (50g) |
| `2` | Place Cannon tower (100g) |
| `3` | Place Ice tower (75g) |
| `4` | Place Sniper tower (120g) |
| `5` | Place Mortar tower (150g) |
| `Tab` | Cycle tower selection |
| `u` | Upgrade tower under cursor |
| `s` | Sell tower under cursor (50% refund) |
| `Space` | Start next wave |
| `p` | Pause/unpause |
| `q` / `Esc` | Quit |

## Gameplay

1. **Start**: You begin with 200 gold and 20 lives.
2. **Place Towers**: Move the cursor to an empty tile (marked with `·`) and press `1`-`5` to place a tower.
3. **Start a Wave**: Press `Space` to send the next wave of enemies. Enemies follow the brown path (`█`).
4. **Upgrade & Sell**: Press `u` to upgrade or `s` to sell a tower under the cursor.
5. **Survive**: Each enemy that reaches the end costs 1 life. If lives reach 0, game over!
6. **Boss Waves**: Every 5th wave features a powerful Overlord enemy.

## Strategy Tips

- **Arrow towers** are cheap and great for early waves. Place them along straight path sections.
- **Ice towers** slow enemies, making them take more hits from other towers. Combine with Snipers!
- **Cannon and Mortar** towers deal splash damage — place them near path bends where enemies cluster.
- **Sniper towers** have long range but slow fire rate — place them in central positions.
- **Medic enemies** heal nearby foes — prioritize them!
- Upgrade key towers rather than placing many cheap ones.

## Tower Stats

| Tower | Cost | Damage | Range | Fire Rate | Special |
|-------|------|--------|-------|-----------|---------|
| Arrow | 50g | 8 | 4 | Fast | — |
| Cannon | 100g | 25 | 3 | Medium | Splash (1 tile) |
| Ice | 75g | 4 | 4 | Medium | 50% Slow |
| Sniper | 120g | 50 | 8 | Slow | — |
| Mortar | 150g | 40 | 5 | Slow | Splash (2 tiles) |

## What It Does

The game renders a 50×20 character map in your terminal showing a winding enemy path (brown `█` tiles) through a field of empty tiles (`·`). Towers appear as colored letters (A/C/I/S/M) at their placement positions. Enemies appear as colored characters moving along the path. Projectiles animate from towers to their targets.

The sidebar shows tower selection, selected tower stats, controls, and a list of current enemies with health bars. The bottom log area shows game events in real time.

Each wave spawns progressively more and tougher enemies. Enemy HP scales with wave number. Gold is earned by defeating enemies and completing waves. Strategic tower placement, upgrading, and selling is key to surviving all waves!