# 🔮 Decision Oracle

An interactive CLI tool for building, consulting, and visualizing binary decision trees. Grow your own knowledge trees by answering yes/no questions, then consult the Oracle whenever you're stuck on a decision.

## Features

- **🌱 Build** — Interactively grow decision trees by defining yes/no questions and leaf outcomes
- **🔮 Consult** — Walk through a tree with the Oracle to get a decision based on your answers
- **🌳 Visualize** — Render any tree as ASCII art directly in the terminal
- **📋 List** — See all saved trees with node counts and descriptions
- **📊 Export** — Generate Mermaid diagrams for rendering in Markdown or documentation
- **💾 Persistent** — Trees are saved as JSON files, so they persist between sessions
- **🎭 Personality** — The Oracle speaks with flavor, dispensing wisdom and mysterious sayings

## How to Install

No external dependencies needed — just Python 3.10+:

```bash
# Clone or download this directory
cd decision-oracle
```

## How to Run

```bash
# Interactive menu (default)
python3 decision_oracle.py

# Or use a specific command directly:
python3 decision_oracle.py build       # Build a new decision tree
python3 decision_oracle.py consult     # Consult the Oracle
python3 decision_oracle.py visualize   # Show tree as ASCII art
python3 decision_oracle.py list        # List all saved trees
python3 decision_oracle.py export      # Export as Mermaid diagram
```

## Usage Examples

### Building a Tree

Run `python3 decision_oracle.py build` and answer the prompts:

```
🌳  Name your decision tree: what_to_cook
📝  Brief description: Deciding what to cook for dinner

══════════════════════════════════════════════
🌱  Let's grow your decision tree!
══════════════════════════════════════════════

🌿 Enter a yes/no question: Do you have more than 30 minutes?
  ── YES branch ──
  Does YES lead to a final decision? [y/n]: n
  ❓ Enter a yes/no question: Are you comfortable with complex recipes?
    ── YES branch ──
    Does YES lead to a final decision? [y/n]: y
    ✅ Final decision/outcome for YES: Make beef bourguignon!
    ── NO branch ──
    Does NO lead to a final decision? [y/n]: y
    ❌ Final decision/outcome for NO: Simple pasta with jarred sauce.
  ── NO branch ──
  Does NO lead to a final decision? [y/n]: y
  ❌ Final decision/outcome for NO: Order pizza.
```

### Consulting the Oracle

Run `python3 decision_oracle.py consult`, pick a tree, and answer questions:

```
🔮 Consulting the Oracle of 'lunch_decider'...
"The leaves of knowledge rustle with insight..."

❓ Do you want something hot? [y/n]: y
❓ Are you craving something spicy? [y/n]: y
❓ Do you have more than 30 minutes? [y/n]: n

══════════════════════════════════════════════
🔮 The Oracle decrees:

   "Grab spicy ramen — quick, hot, and packs a punch."

Path taken: YES: Do you want something hot? → YES: Are you craving something spicy? → NO: Do you have more than 30 minutes?
══════════════════════════════════════════════
```

### Visualizing a Tree

Run `python3 decision_oracle.py visualize` to see the tree structure:

```
🌳 Tree: lunch_decider

  ──────────────────────────────────────────────────────
  🌳 Do you want something hot?
  ├── YES
    │ ❓ Are you craving something spicy?
    │ ├── YES
    │ │ ❓ Do you have more than 30 minutes?
    │ │ ├── YES
    │ │ │ 🔵 Make a big pot of chili — you've got time, make it count!
    │ │ └── NO
          🔵 Grab spicy ramen — quick, hot, and packs a punch.
    │ └── NO
        ❓ Are you in the mood for soup?
        ├── YES
        │ 🔵 Tomato soup with grilled cheese — comfort in a bowl.
        └── NO
          🔵 Warm panini or toasted sandwich — hot, crispy, satisfying.
  └── NO
    ❓ Are you looking for something healthy?
    ...
```

### Exporting a Mermaid Diagram

Run `python3 decision_oracle.py export` to generate a Mermaid flowchart that you can embed in Markdown or render online:

```mermaid
graph TD
    N1{{"Do you want something hot?"}}
    N2{{"Are you craving something spicy?"}}
    N1 -->|"Yes"| N2
    N3["Make a big pot of chili"]
    N2 -->|"Yes"| N3
```

## Included Sample Trees

The `trees/` directory includes two sample trees to get you started:

| Tree | Description | Nodes | Leaves |
|------|-------------|-------|--------|
| `lunch_decider` | Can't decide what to eat? Let the Oracle guide your lunch decisions. | 15 | 8 |
| `weekend_planner` | Not sure what to do this weekend? The Oracle knows. | 15 | 8 |

## How It Works

Decision Oracle uses a binary tree structure where each internal node contains a yes/no question and each leaf node contains a final decision. The tree is stored as a nested JSON object:

```json
{
  "question": "Do you want something hot?",
  "yes": {
    "question": "Are you craving something spicy?",
    "yes": { "decision": "Spicy ramen!" },
    "no": { "decision": "Tomato soup with grilled cheese." }
  },
  "no": {
    "question": "Are you looking for something healthy?",
    "yes": { "decision": "Big salad." },
    "no": { "decision": "Charcuterie board." }
  }
}
```

Trees of any depth are supported — keep branching until you've captured all the nuances of a decision.