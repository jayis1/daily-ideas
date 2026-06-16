#!/usr/bin/env python3
"""
Decision Oracle — An interactive CLI decision tree builder and consultant.

Build knowledge trees by answering yes/no questions, then consult the oracle
for decisions. Trees are persisted as JSON and visualized as ASCII art.

Usage:
    python3 decision_oracle.py build      — Build a new decision tree interactively
    python3 decision_oracle.py consult    — Consult an existing tree for a decision
    python3 decision_oracle.py visualize   — Render a tree as ASCII art
    python3 decision_oracle.py list        — List all saved trees
    python3 decision_oracle.py export      — Export a tree as a Mermaid diagram
    python3 decision_oracle.py random      — Get a random oracle decision (skip the questions)
    python3 decision_oracle.py stats       — Show statistics about a tree
    python3 decision_oracle.py delete       — Delete a saved tree
    python3 decision_oracle.py validate    — Validate a tree's structure

Options:
    --help     Show this help message
    --version  Show version info
"""

import json
import os
import sys
import textwrap
import random
from pathlib import Path

__version__ = "2.0.0"

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

ORACLE_RANDOM_SAYINGS = [
    "The Oracle plucks a leaf at random — such is fate!",
    "The winds of chance blow through the canopy...",
    "The Oracle casts the runes and picks a path unseen...",
    "Destiny is shuffled — the Oracle draws a card...",
    "Without hesitation, the Oracle leaps to a conclusion...",
    "The Oracle closes its eyes and points — there!",
    "Fate spins the wheel of decisions...",
    "The Oracle tosses the sacred coin...",
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


# ─── Helpers ──────────────────────────────────────────────────────

def ensure_data_dir():
    """Create the data directory if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_tree_path(name: str) -> Path:
    """Get the file path for a named tree.

    Sanitizes the name to produce a safe filename while preserving
    readability. Handles edge cases like empty strings and special chars.
    """
    safe_name = name.lower().strip().replace(" ", "_").replace("/", "_")
    # Remove any remaining problematic characters
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-")
    if not safe_name:
        safe_name = "untitled"
    return DATA_DIR / f"{safe_name}.json"


def count_nodes(node: dict) -> int:
    """Count total nodes in a tree (questions + decisions)."""
    if not node:
        return 0
    count = 1
    if "yes" in node:
        count += count_nodes(node["yes"])
    if "no" in node:
        count += count_nodes(node["no"])
    return count


def count_leaves(node: dict) -> int:
    """Count leaf (decision) nodes in a tree."""
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


def tree_depth(node: dict) -> int:
    """Calculate the maximum depth of a tree."""
    if not node or "decision" in node:
        return 0
    yes_depth = tree_depth(node.get("yes", {})) + 1
    no_depth = tree_depth(node.get("no", {})) + 1
    return max(yes_depth, no_depth)


def collect_leaves(node: dict, path: list | None = None) -> list[tuple[str, list[str]]]:
    """Collect all leaf decisions along with the path taken to reach them.

    Returns a list of (decision_text, path_steps) tuples.
    """
    if path is None:
        path = []
    if not node:
        return []

    if "decision" in node:
        return [(node["decision"], path.copy())]

    results = []
    question = node.get("question", "?")
    if "yes" in node:
        results.extend(collect_leaves(node["yes"], path + [f"YES: {question}"]))
    if "no" in node:
        results.extend(collect_leaves(node["no"], path + [f"NO: {question}"]))
    return results


def validate_tree(node: dict, depth: int = 0, path: str = "root") -> list[str]:
    """Validate the structure of a decision tree, returning a list of issues.

    Checks for:
    - Missing 'question' key in internal nodes
    - Missing 'decision' key in leaf nodes
    - Missing 'yes' or 'no' branches
    - Excessive depth (>20)
    - Empty strings
    """
    issues = []

    if not node:
        issues.append(f"Empty node at {path}")
        return issues

    if "decision" in node:
        # Leaf node — should not have question/yes/no
        if not node["decision"] or not node["decision"].strip():
            issues.append(f"Empty decision text at {path}")
        if "yes" in node or "no" in node:
            issues.append(f"Leaf node at {path} has branches (should be terminal)")
        return issues

    # Internal node
    if "question" not in node:
        issues.append(f"Missing 'question' at {path}")
    elif not node["question"] or not node["question"].strip():
        issues.append(f"Empty question text at {path}")

    if "yes" not in node:
        issues.append(f"Missing 'yes' branch at {path}")
    else:
        issues.extend(validate_tree(node["yes"], depth + 1, f"{path} → YES"))

    if "no" not in node:
        issues.append(f"Missing 'no' branch at {path}")
    else:
        issues.extend(validate_tree(node["no"], depth + 1, f"{path} → NO"))

    if depth > 20:
        issues.append(f"Tree is very deep at {path} (depth={depth}), consider simplifying")

    return issues


# ─── User Input ───────────────────────────────────────────────────

def prompt_input(message: str) -> str:
    """Prompt for user input with a styled message.

    Handles EOF and keyboard interrupts gracefully.
    """
    try:
        return input(f"  {message}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def prompt_yes_no(message: str) -> bool:
    """Prompt for a yes/no answer with input validation."""
    while True:
        ans = prompt_input(f"{message} [y/n]").lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("  Please answer yes or no.")


# ─── Core Commands ────────────────────────────────────────────────

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

    root = _build_node(depth=0)

    tree_data = {
        "name": name,
        "description": description or f"A decision tree about {name}",
        "version": __version__,
        "root": root,
    }

    ensure_data_dir()
    tree_path = get_tree_path(name)
    tree_path.write_text(json.dumps(tree_data, indent=2, ensure_ascii=False))

    node_count = count_nodes(root)
    leaf_count = count_leaves(root)

    print()
    print("  ══════════════════════════════════════════════")
    print(f"  🌳  Tree '{name}' has grown!")
    print(f"      {node_count} total nodes, {leaf_count} leaf decisions")
    print(f"      Saved to: {tree_path.name}")
    print("  ══════════════════════════════════════════════")


def _build_node(depth: int) -> dict:
    """Recursively build a single node of the tree.

    Args:
        depth: Current nesting depth (used for indentation and depth limits).

    Returns:
        A dict representing a tree node (either a question node or a leaf).
    """
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
        node["yes"] = _build_node(depth + 1)

    # NO branch
    print(f"{indent}  ── NO branch ──")
    if prompt_yes_no(f"{indent}  Does NO lead to a final decision (leaf)?"):
        node["no"] = {
            "decision": prompt_input(f"{indent}  ❌ Final decision/outcome for NO")
        }
    else:
        node["no"] = _build_node(depth + 1)

    return node


def consult_tree():
    """Consult an existing tree for a decision by walking through questions."""
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
            desc = data.get("description", "")
            print(f"    {i}. {name} — {desc}")
        except Exception:
            print(f"    {i}. {tree_file.stem} (corrupted)")

    print()
    choice = prompt_input("Select a tree (number or name)")
    if not choice:
        return

    tree_data = _resolve_tree_choice(choice, trees)
    if not tree_data:
        return

    name = tree_data.get("name", "Unknown")
    print()
    print(f"  🔮 Consulting the Oracle of '{name}'...")
    print(f"  \"{random.choice(ORACLE_SAYINGS)}\"")
    print()

    # Walk the tree interactively
    node = tree_data["root"]
    path_taken = []

    while True:
        if "decision" in node:
            print()
            print("  ══════════════════════════════════════════════")
            print("  🔮 The Oracle decrees:")
            print()
            # Wrap long decisions for readability
            wrapped = textwrap.fill(node['decision'], width=60, initial_indent="     ", subsequent_indent="     ")
            print(wrapped)
            print()
            if path_taken:
                print(f"  Path taken: {' → '.join(path_taken)}")
            print("  ══════════════════════════════════════════════")
            return

        question = node.get("question", "???")
        if prompt_yes_no(f"  ❓ {question}"):
            path_taken.append(f"YES: {question}")
            node = node["yes"]
        else:
            path_taken.append(f"NO: {question}")
            node = node["no"]


def random_decision():
    """Get a random decision from a tree — no questions asked!"""
    print(BANNER)

    ensure_data_dir()
    tree_data = select_tree()
    if not tree_data:
        return

    name = tree_data.get("name", "Unknown")
    leaves = collect_leaves(tree_data["root"])

    if not leaves:
        print("\n  This tree has no decisions! Something is wrong.\n")
        return

    decision_text, path = random.choice(leaves)

    print()
    print(f"  🎲 The Oracle of '{name}' speaks without hesitation...")
    print(f"  \"{random.choice(ORACLE_RANDOM_SAYINGS)}\"")
    print()
    print("  ══════════════════════════════════════════════")
    print("  🔮 The Oracle randomly decrees:")
    print()
    wrapped = textwrap.fill(decision_text, width=60, initial_indent="     ", subsequent_indent="     ")
    print(wrapped)
    print()
    if path:
        print(f"  Hypothetical path: {' → '.join(path)}")
    print("  ══════════════════════════════════════════════")


def show_stats():
    """Show statistics about a decision tree."""
    print(BANNER)

    ensure_data_dir()
    tree_data = select_tree()
    if not tree_data:
        return

    name = tree_data.get("name", "Unknown")
    root = tree_data["root"]

    n_nodes = count_nodes(root)
    n_leaves = count_leaves(root)
    depth = tree_depth(root)
    n_questions = n_nodes - n_leaves

    # Collect all leaf decisions with their paths
    leaves = collect_leaves(root)
    longest_path = max(len(p) for _, p in leaves) if leaves else 0
    shortest_path = min(len(p) for _, p in leaves) if leaves else 0
    avg_decision_len = sum(len(d) for d, _ in leaves) / len(leaves) if leaves else 0

    # Balanced ratio (1.0 = perfectly balanced, lower = more unbalanced)
    if n_leaves > 1:
        balance = shortest_path / longest_path if longest_path > 0 else 0
    else:
        balance = 1.0

    print()
    print(f"  📊 Statistics for '{name}'")
    print()
    print(f"    Total nodes:        {n_nodes}")
    print(f"    Question nodes:     {n_questions}")
    print(f"    Decision (leaf) nodes: {n_leaves}")
    print(f"    Maximum depth:      {depth}")
    print(f"    Longest path:       {longest_path} questions")
    print(f"    Shortest path:      {shortest_path} questions")
    print(f"    Balance ratio:      {balance:.2f}  (1.0 = perfectly balanced)")
    print(f"    Avg decision length: {avg_decision_len:.1f} chars")
    print()

    # List all decisions
    if leaves:
        print("  🍃 All possible decisions:")
        for i, (decision, path) in enumerate(leaves, 1):
            path_str = " → ".join(path) if path else "(direct)"
            print(f"    {i}. {decision}")
            print(f"       via {path_str}")
        print()


def delete_tree():
    """Delete a saved decision tree."""
    print(BANNER)

    ensure_data_dir()
    trees = sorted(DATA_DIR.glob("*.json"))
    if not trees:
        print("\n  No decision trees found!\n")
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
    choice = prompt_input("Select a tree to DELETE (number or name)")
    if not choice:
        return

    # Resolve which file to delete
    tree_file = None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(trees):
            tree_file = trees[idx]
    except (ValueError, IndexError):
        tree_path = get_tree_path(choice)
        if tree_path.exists():
            tree_file = tree_path

    if not tree_file:
        print(f"  Tree '{choice}' not found.")
        return

    tree_data = json.loads(tree_file.read_text())
    tree_name = tree_data.get("name", tree_file.stem)

    if prompt_yes_no(f"  ⚠️  Permanently delete '{tree_name}'?"):
        tree_file.unlink()
        # Also remove .mmd if it exists
        mmd_file = tree_file.with_suffix(".mmd")
        if mmd_file.exists():
            mmd_file.unlink()
        print(f"  🗑️  Tree '{tree_name}' deleted.")
    else:
        print("  Deletion cancelled.")


def validate_tree_cmd():
    """Validate a tree's structure and report any issues."""
    print(BANNER)

    ensure_data_dir()
    tree_data = select_tree()
    if not tree_data:
        return

    name = tree_data.get("name", "Unknown")
    root = tree_data["root"]

    issues = validate_tree(root)

    print()
    if not issues:
        print(f"  ✅ Tree '{name}' is valid! No issues found.")
        n = count_nodes(root)
        l = count_leaves(root)
        d = tree_depth(root)
        print(f"     {n} nodes, {l} decisions, depth {d}")
    else:
        print(f"  ⚠️  Found {len(issues)} issue(s) in '{name}':")
        for issue in issues:
            print(f"     • {issue}")

    print()


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
            leaf_count = count_leaves(data.get("root", {}))
            depth = tree_depth(data.get("root", {}))
            desc = data.get("description", "No description")
            print(f"    • {name}")
            print(f"      {desc}")
            print(f"      ({node_count} nodes, {leaf_count} decisions, depth {depth})\n")
        except Exception as e:
            print(f"    • {tree_file.stem} (corrupted: {e})\n")


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
    _render_node(tree_data["root"], lines, "", is_root=True)
    for line in lines:
        print(line)

    print("  " + "─" * 56)
    n = count_nodes(tree_data["root"])
    l = count_leaves(tree_data["root"])
    d = tree_depth(tree_data["root"])
    print(f"  Nodes: {n} | Leaves: {l} | Depth: {d}")


def _render_node(node: dict, lines: list, prefix: str, is_root: bool = False):
    """Recursively render a node as an ASCII tree.

    Args:
        node: The tree node to render.
        lines: Accumulator list for output lines.
        prefix: Indentation prefix for the current branch.
        is_root: Whether this is the root node (special rendering).
    """
    if "decision" in node:
        lines.append(f"  {prefix}🔵 {node['decision']}")
        return

    question = node.get("question", "???")
    if is_root:
        lines.append(f"  🌳 {question}")
        child_prefix = "  │ "
    else:
        lines.append(f"  {prefix}❓ {question}")
        child_prefix = prefix + "│ "

    # YES branch
    lines.append(f"  {prefix}├── YES")
    if "yes" in node:
        _render_node(node["yes"], lines, child_prefix)

    # NO branch
    lines.append(f"  {prefix}└── NO")
    if "no" in node:
        # Compute the continuation prefix for the NO branch
        if is_root:
            no_child_prefix = "    "
        else:
            # Replace the │ prefix segment with spaces for the NO subtree
            no_child_prefix = prefix.replace("│ ", "  ") + "  "
        _render_node(node["no"], lines, no_child_prefix)


def select_tree() -> dict | None:
    """Let user select a tree from available ones.

    Returns the parsed tree data dict, or None if no selection was made.
    """
    trees = sorted(DATA_DIR.glob("*.json"))
    if not trees:
        print("\n  No decision trees found!\n")
        return None

    print("  Available trees:\n")
    for i, tree_file in enumerate(trees, 1):
        try:
            data = json.loads(tree_file.read_text())
            name = data.get("name", tree_file.stem)
            desc = data.get("description", "")
            print(f"    {i}. {name} — {desc}")
        except Exception:
            print(f"    {i}. {tree_file.stem} (corrupted)")

    print()
    choice = prompt_input("Select a tree (number or name)")
    if not choice:
        return None

    return _resolve_tree_choice(choice, trees)


def _resolve_tree_choice(choice: str, trees: list) -> dict | None:
    """Resolve a user's tree selection by number or name.

    Args:
        choice: The user's input — either a number or tree name.
        trees: List of Path objects for available tree files.

    Returns:
        Parsed tree data dict, or None if not found.
    """
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(trees):
            return json.loads(trees[idx].read_text())
    except (ValueError, IndexError):
        pass

    tree_path = get_tree_path(choice)
    if tree_path.exists():
        return json.loads(tree_path.read_text())

    print(f"  Tree '{choice}' not found.")
    return None


# ─── Export ───────────────────────────────────────────────────────

def export_mermaid_to_string(tree_data: dict) -> str:
    """Generate a Mermaid diagram string for a tree.

    Produces a graph TD flowchart with diamond nodes for questions
    and rounded-rect nodes for decisions.
    """
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


# ─── Interactive Menu ─────────────────────────────────────────────

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
        print("    6. 🎲 Random decision (skip questions!)")
        print("    7. 📊 Show tree statistics")
        print("    8. ✅ Validate a tree")
        print("    9. 🗑️  Delete a tree")
        print("    0. 🚪 Exit")
        print()

        choice = prompt_input("Choose [0-9]")
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
            random_decision()
        elif choice == "7":
            show_stats()
        elif choice == "8":
            validate_tree_cmd()
        elif choice == "9":
            delete_tree()
        elif choice in ("0", "q", "quit", "exit"):
            print("\n  May your decisions be wise! 🌳✨\n")
            break
        else:
            print("  Invalid choice. Try again.")


# ─── Entry Point ─────────────────────────────────────────────────

COMMANDS = {
    "build": build_tree,
    "consult": consult_tree,
    "visualize": visualize_tree,
    "list": list_trees,
    "export": export_mermaid,
    "random": random_decision,
    "stats": show_stats,
    "delete": delete_tree,
    "validate": validate_tree_cmd,
}


def main():
    """Main entry point — dispatch to commands or show help/version."""
    # Handle --version and --help flags
    if "--version" in sys.argv:
        print(f"Decision Oracle v{__version__}")
        return

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print(f"Version: {__version__}")
        print()
        print("Available commands:")
        for cmd in sorted(COMMANDS.keys()):
            print(f"  {cmd}")
        print()
        print("Run without arguments for interactive menu.")
        return

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command in COMMANDS:
            COMMANDS[command]()
        else:
            print(f"\n  Unknown command: {command}")
            print(f"  Available commands: {', '.join(sorted(COMMANDS.keys()))}")
            print("  Run with --help for more info.\n")
    else:
        interactive_menu()


if __name__ == "__main__":
    main()