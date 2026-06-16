#!/usr/bin/env python3
"""
Decision Oracle — An interactive CLI decision tree builder and consultant.

Build knowledge trees by answering yes/no questions, then consult the oracle
for decisions. Trees are persisted as JSON and visualized as ASCII art.

Usage:
    python3 decision_oracle.py build     — Build a new decision tree interactively
    python3 decision_oracle.py consult   — Consult an existing tree for a decision
    python3 decision_oracle.py visualize — Render a tree as ASCII art
    python3 decision_oracle.py list       — List all saved trees
    python3 decision_oracle.py export     — Export a tree as a Mermaid diagram
"""

import json
import os
import sys
import textwrap
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent / "trees"

ORACLE_SAYINGS = [
    "The Oracle peers into the mist...",
    "Ancient wisdom flows through the branches...",
    "The leaves of knowledge rustle with insight...",
    "The Oracle contemplates your question...",
    "The tree of decision stretches before you...",
    "Wisdom awaits at the terminal nodes...",
    "The roots of knowledge run deep...",
    "The Oracle whispers from the canopy...",
    "Branches fork, decisions crystallize...",
    "The path reveals itself...",
]

BANNER = r"""
╔══════════════════════════════════════════════════════╗
║                   DECISION ORACLE                    ║
║         Build & Consult Decision Trees               ║
║                                                      ║
║   "All knowledge is a tree; every decision a branch" ║
╚══════════════════════════════════════════════════════╝
"""

TREE_BANNER = r"""
     🌳
    /    \
   🍃     🍃
  /  \   /  \
 🍃   🍃🍃   🍃
"""


def ensure_data_dir():
    """Create the data directory if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_tree_path(name: str) -> Path:
    """Get the file path for a named tree."""
    safe_name = name.lower().replace(" ", "_").replace("/", "_")
    return DATA_DIR / f"{safe_name}.json"


def list_trees():
    """List all saved decision trees."""
    ensure_data_dir()
    trees = sorted(DATA_DIR.glob("*.json"))
    if not trees:
        print("\n  No decision trees found. Build one with: decision_oracle.py build\n")
        return
    print("\n  🌳 Saved Decision Trees:\n")
    for tree_file in trees:
        try:
            data = json.loads(tree_file.read_text())
            name = data.get("name", tree_file.stem)
            node_count = count_nodes(data.get("root", {}))
            desc = data.get("description", "No description")
            print(f"    • {name}")
            print(f"      {desc}")
            print(f"      ({node_count} nodes)\n")
        except Exception:
            print(f"    • {tree_file.stem} (corrupted)\n")


def count_nodes(node: dict) -> int:
    """Count total nodes in a tree."""
    if not node:
        return 0
    count = 1
    if "yes" in node:
        count += count_nodes(node["yes"])
    if "no" in node:
        count += count_nodes(node["no"])
    return count


def prompt_input(message: str) -> str:
    """Prompt for user input with a styled message."""
    try:
        return input(f"  {message}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def prompt_yes_no(message: str) -> bool:
    """Prompt for a yes/no answer."""
    while True:
        ans = prompt_input(f"{message} [y/n]").lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("  Please answer yes or no.")


def build_tree():
    """Interactively build a new decision tree."""
    print(BANNER)
    print(TREE_BANNER)

    name = prompt_input("🌳  Name your decision tree")
    if not name:
        print("  A tree needs a name! Aborting.")
        return

    existing = get_tree_path(name)
    if existing.exists():
        if not prompt_yes_no(f"  Tree '{name}' already exists. Overwrite?"):
            print("  Keeping existing tree. Goodbye!")
            return

    description = prompt_input("📝  Brief description")
    print()

    print("  ══════════════════════════════════════════════")
    print("  🌱  Let's grow your decision tree!")
    print("  ══════════════════════════════════════════════")
    print()
    print("  Start with a yes/no question. The Oracle will")
    print("  branch based on the answer, building a binary")
    print("  tree of knowledge. At each leaf, provide the")
    print("  final decision/outcome.")
    print()

    root = build_node(depth=0)

    tree_data = {
        "name": name,
        "description": description or f"A decision tree about {name}",
        "root": root,
    }

    ensure_data_dir()
    tree_path = get_tree_path(name)
    tree_path.write_text(json.dumps(tree_data, indent=2))

    node_count = count_nodes(root)
    leaf_count = count_leaves(root)

    print()
    print("  ══════════════════════════════════════════════")
    print(f"  🌳  Tree '{name}' has grown!")
    print(f"      {node_count} total nodes, {leaf_count} leaf decisions")
    print(f"      Saved to: {tree_path.name}")
    print("  ══════════════════════════════════════════════")


def build_node(depth: int) -> dict:
    """Recursively build a single node of the tree."""
    indent = "  " * (depth + 1)
    prefix = "🌿 " if depth == 0 else "🍃 " if depth < 3 else "  "

    if depth > 0:
        print(f"{indent}Now define the branch...")

    question = prompt_input(f"{indent}{prefix}Enter a yes/no question")
    if not question:
        question = "Is this what you seek?"

    node = {"question": question}

    # YES branch
    print(f"{indent}  ── YES branch ──")
    if prompt_yes_no(f"{indent}  Does YES lead to a final decision (leaf)?"):
        node["yes"] = {
            "decision": prompt_input(f"{indent}  ✅ Final decision/outcome for YES")
        }
    else:
        node["yes"] = build_node(depth + 1)

    # NO branch
    print(f"{indent}  ── NO branch ──")
    if prompt_yes_no(f"{indent}  Does NO lead to a final decision (leaf)?"):
        node["no"] = {
            "decision": prompt_input(f"{indent}  ❌ Final decision/outcome for NO")
        }
    else:
        node["no"] = build_node(depth + 1)

    return node


def count_leaves(node: dict) -> int:
    """Count leaf nodes in a tree."""
    if not node:
        return 0
    if "decision" in node:
        return 1
    count = 0
    if "yes" in node:
        count += count_leaves(node["yes"])
    if "no" in node:
        count += count_leaves(node["no"])
    return count


def consult_tree():
    """Consult an existing tree for a decision."""
    print(BANNER)

    ensure_data_dir()
    trees = sorted(DATA_DIR.glob("*.json"))
    if not trees:
        print("\n  No decision trees found! Build one first with: decision_oracle.py build\n")
        return

    print("  Available trees:\n")
    for i, tree_file in enumerate(trees, 1):
        try:
            data = json.loads(tree_file.read_text())
            name = data.get("name", tree_file.stem)
            print(f"    {i}. {name}")
        except Exception:
            print(f"    {i}. {tree_file.stem} (corrupted)")

    print()
    choice = prompt_input("Select a tree (number or name)")
    if not choice:
        return

    tree_data = None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(trees):
            tree_data = json.loads(trees[idx].read_text())
    except (ValueError, IndexError):
        tree_path = get_tree_path(choice)
        if tree_path.exists():
            tree_data = json.loads(tree_path.read_text())

    if not tree_data:
        print(f"  Tree '{choice}' not found.")
        return

    name = tree_data.get("name", "Unknown")
    print()
    print(f"  🔮 Consulting the Oracle of '{name}'...")
    print(f"  \"{random.choice(ORACLE_SAYINGS)}\"")
    print()

    # Walk the tree
    node = tree_data["root"]
    path_taken = []

    while True:
        if "decision" in node:
            print()
            print("  ══════════════════════════════════════════════")
            print(f"  🔮 The Oracle decrees:")
            print()
            print(f"     \"{node['decision']}\"")
            print()
            if path_taken:
                print(f"  Path taken: {' → '.join(path_taken)}")
            print("  ══════════════════════════════════════════════")
            return

        question = node["question"]
        if prompt_yes_no(f"  ❓ {question}"):
            path_taken.append(f"YES: {question}")
            node = node["yes"]
        else:
            path_taken.append(f"NO: {question}")
            node = node["no"]


def visualize_tree():
    """Render a decision tree as ASCII art."""
    print(BANNER)

    ensure_data_dir()
    tree_data = select_tree()
    if not tree_data:
        return

    name = tree_data.get("name", "Unknown")
    print(f"\n  🌳 Tree: {name}\n")
    print("  " + "─" * 56)

    lines = []
    render_node(tree_data["root"], lines, "", True)
    for line in lines:
        print(line)

    print("  " + "─" * 56)
    print(f"  Nodes: {count_nodes(tree_data['root'])} | Leaves: {count_leaves(tree_data['root'])}")


def render_node(node: dict, lines: list, prefix: str, is_root: bool = False):
    """Recursively render a node as ASCII tree."""
    if "decision" in node:
        lines.append(f"  {prefix}🔵 {node['decision']}")
        return

    question = node["question"]
    if is_root:
        lines.append(f"  🌳 {question}")
        child_prefix = "  │ "
    else:
        lines.append(f"  {prefix}❓ {question}")
        child_prefix = prefix + "│ "

    # YES branch
    lines.append(f"  {prefix}├── YES")
    if "yes" in node:
        render_node(node["yes"], lines, child_prefix)

    # NO branch
    lines.append(f"  {prefix}└── NO")
    if "no" in node:
        new_prefix = prefix.replace("│ ", "  ").replace("├", "│").replace("└", " ") + "  "
        if is_root:
            new_prefix = "  "
        render_node(node["no"], lines, new_prefix)


def select_tree() -> dict | None:
    """Let user select a tree from available ones."""
    trees = sorted(DATA_DIR.glob("*.json"))
    if not trees:
        print("\n  No decision trees found!\n")
        return None

    print("  Available trees:\n")
    for i, tree_file in enumerate(trees, 1):
        try:
            data = json.loads(tree_file.read_text())
            print(f"    {i}. {data.get('name', tree_file.stem)}")
        except Exception:
            print(f"    {i}. {tree_file.stem} (corrupted)")

    print()
    choice = prompt_input("Select a tree (number or name)")
    if not choice:
        return None

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(trees):
            return json.loads(trees[idx].read_text())
    except (ValueError, IndexError):
        tree_path = get_tree_path(choice)
        if tree_path.exists():
            return json.loads(tree_path.read_text())

    print(f"  Tree '{choice}' not found.")
    return None


def export_mermaid_to_string(tree_data: dict) -> str:
    """Generate a Mermaid diagram string for a tree."""
    lines = ["graph TD"]
    node_id = [0]

    def make_id():
        node_id[0] += 1
        return f"N{node_id[0]}"

    def escape(s):
        return s.replace('"', "'").replace("\n", " ")

    def _export_node(node: dict, parent_id: str | None, label: str):
        if "decision" in node:
            nid = make_id()
            lines.append(f'    {nid}["{escape(node["decision"])}"]')
            if parent_id:
                lines.append(f'    {parent_id} -->|"{label}"| {nid}')
            return nid

        nid = make_id()
        lines.append(f'    {nid}{{{{"{escape(node["question"])}"}}}}')
        if parent_id:
            lines.append(f'    {parent_id} -->|"{label}"| {nid}')

        if "yes" in node:
            _export_node(node["yes"], nid, "Yes")
        if "no" in node:
            _export_node(node["no"], nid, "No")
        return nid

    _export_node(tree_data["root"], None, "")
    return "\n".join(lines)


def export_mermaid():
    """Export a tree as a Mermaid diagram."""
    print(BANNER)

    ensure_data_dir()
    tree_data = select_tree()
    if not tree_data:
        return

    name = tree_data.get("name", "Unknown")
    output = export_mermaid_to_string(tree_data)

    out_file = get_tree_path(name).with_suffix(".mmd")
    out_file.write_text(output)

    print(f"\n  📊 Mermaid diagram exported to: {out_file.name}")
    print(f"\n  {output}\n")


def interactive_menu():
    """Show an interactive menu when no command is given."""
    print(BANNER)

    while True:
        print("\n  What would you like to do?\n")
        print("    1. 🌱 Build a new decision tree")
        print("    2. 🔮 Consult the Oracle")
        print("    3. 🌳 Visualize a tree")
        print("    4. 📋 List all trees")
        print("    5. 📊 Export as Mermaid diagram")
        print("    6. 🚪 Exit")
        print()

        choice = prompt_input("Choose [1-6]")
        if choice == "1":
            build_tree()
        elif choice == "2":
            consult_tree()
        elif choice == "3":
            visualize_tree()
        elif choice == "4":
            list_trees()
        elif choice == "5":
            export_mermaid()
        elif choice == "6":
            print("\n  May your decisions be wise! 🌳✨\n")
            break
        else:
            print("  Invalid choice. Try again.")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "build":
            build_tree()
        elif command == "consult":
            consult_tree()
        elif command == "visualize":
            visualize_tree()
        elif command == "list":
            list_trees()
        elif command == "export":
            export_mermaid()
        else:
            print(f"\n  Unknown command: {command}")
            print("  Usage: decision_oracle.py [build|consult|visualize|list|export]\n")
    else:
        interactive_menu()


if __name__ == "__main__":
    main()