# ⚙️ Rube Goldberg Machine Simulator

A terminal-based ASCII animation of absurdly complex chain-reaction machines. Watch as balls, dominoes, seesaws, buckets, pulleys, fans, springs, hammers, and more interact in hilariously over-engineered contraptions — all to accomplish a trivially simple task.

Inspired by the real-world [Rube Goldberg machines](https://en.wikipedia.org/wiki/Rube_Goldberg_machine) that use convoluted, indirect mechanisms to perform simple tasks in wildly complicated ways.

## Features

- **Preset Machine** — A hand-designed 10-stage machine with guaranteed good visuals
- **Random Machine** — Every run generates a unique layout from randomized stage combinations
- **Marathon Mode** — 3 random machines back-to-back
- **Animated Chain Reactions** — Balls roll, dominoes fall, seesaws tip, buckets dump, springs bounce, fans blow, pulleys lift, hammers smash
- **Particle Effects** — Sparkles, trails, and water drops for visual flair
- **Real-time Status** — Frame counter, component count, projectile tracking
- **No Dependencies** — Pure Python standard library, no pip installs needed

## How It Works

The simulator uses a component-based architecture:

1. **Components** are placed on a 2D canvas — balls, dominoes, seesaws, buckets, etc.
2. Each component has a timer that counts down; when it reaches zero, the component activates
3. Activating a component spawns **projectiles** (balls, water, air, sparks) that fly through the scene with physics (gravity, velocity)
4. Components progress through states: `idle → active → triggered → done`, changing their appearance
5. The finale features a bell (🔔 DING!) and a flag (⚑) to signal completion

Stage types include:
- **Domino Chain** — Rows of dominoes falling in sequence
- **Seesaw Launch** — A seesaw that flings a ball
- **Bucket Dump** — A bucket that tips and spills
- **Hammer Smash** — A hammer that whacks and triggers
- **Fan Blow** — A fan that pushes a ball with air
- **Spring Launch** — A spring that bounces a ball upward
- **Funnel Redirect** — A funnel that redirects a ball
- **Pulley Lift** — A pulley that lifts a ball

## Installation

No installation required! Just clone and run with Python 3.

```bash
git clone <repo-url>
cd rube-goldberg-simulator
```

## How to Run

```bash
python3 rube_goldberg.py
```

Then choose an option:
- `[1]` Preset machine (hand-designed, reliable)
- `[2]` Random machine (different every time)
- `[3]` Marathon mode (3 random machines)

Press `Ctrl+C` to exit at any time.

## Usage Examples

```
$ python3 rube_goldberg.py

⚙️  RUBE GOLDBERG MACHINE SIMULATOR ⚙️
========================================

Watch an absurdly complex chain-reaction machine
accomplish a trivially simple task!

Options:
  [1] Preset machine (guaranteed good show)
  [2] Random machine (every time is different)
  [3] Generate 3 random machines (marathon!)
  [q] Quit

Choose [1/2/3/q]: 2
```

You'll see an animated ASCII display showing the machine running in real-time, with components activating in sequence, projectiles flying with trails and sparkles, and a completion message when the flag is finally raised.

## What It Does

The simulator generates a multi-stage chain-reaction machine using the Rube Goldberg principle: a ball starts rolling, knocks over dominoes, which trigger a seesaw, which launches another ball into a bucket, which tips and activates a fan, and so on — all rendered in real-time ASCII art in your terminal. Each machine is a unique experience, with the random generator creating different combinations of mechanical stages every time.