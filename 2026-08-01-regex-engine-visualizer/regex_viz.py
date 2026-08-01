#!/usr/bin/env python3
r"""
Regex Engine Visualizer
========================

A tiny backtracking regex engine that *records every step* of the matching
process and then renders a readable, colorized trace of how the pattern was
applied to the input string -- showing the cursor position, the active pattern
node, and every match / fail / backtrack decision.

This is an educational tool: it does NOT use Python's `re` module for matching.
It implements its own recursive backtracking matcher over a hand-written
parser that supports a useful subset of regex syntax:

    literals          abc
    any char          .
    star              a*       (greedy, backtracking)
    plus               a+
    optional           a?
    char class        [abc]  [a-z]  [^0-9]
    anchors            ^       $
    groups             (...)
    alternation        a|b
    escapes            \d  \w  \s  \D \W \S  \.  \\  \n  \t

Usage
-----
    python3 regex_viz.py '<pattern>' '<input>'
    python3 regex_viz.py --demo
    python3 regex_viz.py --demo --no-color   # plain text trace
    python3 regex_viz.py '(a|b)+c' 'abac' --steps   # show every step

The trace highlights:
    cursor  ->  the current position in the input
    node    ->  which part of the pattern is being tried
    action  ->  TRY / MATCH / FAIL / BACKTRACK / ACCEPT

Exit codes: 0 if the pattern matched, 1 if it did not, 2 on a parse error.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Callable

# --------------------------------------------------------------------------- #
# ANSI color helpers
# --------------------------------------------------------------------------- #

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
GRAY = "\033[90m"
BG_YELLOW = "\033[43m"
BG_CYAN = "\033[46m"


def supports_color(stream) -> bool:
    if not hasattr(stream, "isatty"):
        return False
    try:
        return bool(stream.isatty())
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# AST node types
# --------------------------------------------------------------------------- #

@dataclass
class Node:
    """Base class for pattern AST nodes."""
    name: str = "Node"

    def label(self) -> str:
        return self.name

    def match(self, ctx: "MatchContext", pos: int):
        """Try to match this node at position `pos`.

        A generator yielding successful end positions.  The matcher is a
        generator-style backtracking engine: each node yields possible next
        positions.  We record steps as a side effect via `ctx`.
        """
        raise NotImplementedError
        yield  # pragma: no cover  (make this a generator)


@dataclass
class Literal(Node):
    char: str = ""
    name: str = "Literal"

    def label(self) -> str:
        return f"Lit({self.char!r})"

    def match(self, ctx, pos):
        if pos < len(ctx.input) and ctx.input[pos] == self.char:
            ctx.step(pos, self, "MATCH", f"input[{pos}] == {self.char!r}")
            yield pos + 1
        else:
            ctx.step(pos, self, "FAIL", f"input[{pos}] != {self.char!r}")


@dataclass
class AnyChar(Node):
    name: str = "Dot"

    def label(self) -> str:
        return "Dot(.)"

    def match(self, ctx, pos):
        if pos < len(ctx.input) and ctx.input[pos] != "\n":
            ctx.step(pos, self, "MATCH", f". matches {ctx.input[pos]!r}")
            yield pos + 1
        else:
            ctx.step(pos, self, "FAIL", ". at end of input (or newline)")


@dataclass
class CharClass(Node):
    ranges: List[Tuple[str, str]] = field(default_factory=list)
    negated: bool = False
    name: str = "Class"

    def label(self) -> str:
        parts = []
        for a, b in self.ranges:
            parts.append(a if a == b else f"{a}-{b}")
        body = "".join(parts)
        return f"[{'^' if self.negated else ''}{body}]"

    def _in(self, ch: str) -> bool:
        for a, b in self.ranges:
            if a <= ch <= b:
                return True
        return False

    def match(self, ctx, pos):
        if pos < len(ctx.input):
            ch = ctx.input[pos]
            inside = self._in(ch)
            ok = (not inside) if self.negated else inside
            if ok:
                ctx.step(pos, self, "MATCH", f"{ch!r} in {self.label()}")
                yield pos + 1
            else:
                ctx.step(pos, self, "FAIL", f"{ch!r} not in {self.label()}")
        else:
            ctx.step(pos, self, "FAIL", f"{self.label()} at end of input")


@dataclass
class Anchor(Node):
    kind: str = "^"   # '^' or '$'
    name: str = "Anchor"

    def label(self) -> str:
        return f"Anchor({self.kind})"

    def match(self, ctx, pos):
        if self.kind == "^":
            ok = (pos == 0)
            ctx.step(pos, self, "MATCH" if ok else "FAIL",
                     f"^ at pos {pos} (start={ok})")
        else:
            ok = (pos == len(ctx.input))
            ctx.step(pos, self, "MATCH" if ok else "FAIL",
                     f"$ at pos {pos} (end={ok})")
        if ok:
            yield pos


@dataclass
class Group(Node):
    children: List[Node] = field(default_factory=list)
    index: int = 0
    name: str = "Group"

    def label(self) -> str:
        return f"Group#{self.index}"

    def match(self, ctx, pos):
        ctx.step(pos, self, "TRY", f"enter group {self.index}")
        yield from ctx.match_sequence(self.children, pos, self)
        ctx.step(pos, self, "LEAVE", f"leave group {self.index}")


@dataclass
class Alternation(Node):
    options: List[List[Node]] = field(default_factory=list)
    name: str = "Alt"

    def label(self) -> str:
        return f"Alt({len(self.options)} branches)"

    def match(self, ctx, pos):
        ctx.step(pos, self, "TRY", f"alternation with {len(self.options)} branches")
        for i, branch in enumerate(self.options):
            ctx.step(pos, self, "TRY", f"branch {i + 1}/{len(self.options)}")
            yield from ctx.match_sequence(branch, pos, self)


@dataclass
class Star(Node):
    child: Optional["Node"] = None
    greedy: bool = True
    name: str = "Star"

    def label(self) -> str:
        return f"{self.child.label() if self.child else ''}*"

    def match(self, ctx, pos):
        # Greedy: try to consume as many as possible, then backtrack.
        # We implement as recursive generator.
        if self.greedy:
            # try one more, then zero more (backtrack)
            count = 0
            cur = pos
            positions = [pos]
            # Collect all possible forward positions greedily
            while True:
                found = False
                for nxt in self.child.match(ctx, cur):
                    if nxt == cur:
                        # zero-width match would loop forever; stop
                        ctx.step(cur, self, "STOP", "zero-width match in *")
                        break
                    cur = nxt
                    count += 1
                    positions.append(cur)
                    found = True
                    break
                if not found:
                    break
            # Yield positions from greediest to least
            for p in reversed(positions):
                ctx.step(p, self, "YIELD", f"* matched {len(positions)-1} times -> pos {p}")
                yield p
        else:  # lazy
            yield pos
            for nxt in self.child.match(ctx, pos):
                if nxt == pos:
                    return
                yield from self._lazy_chain(ctx, nxt)


    def _lazy_chain(self, ctx, pos):
        """Lazy `*`: yield `pos`, then try one more match and recurse."""
        yield pos
        for nxt in self.child.match(ctx, pos):
            if nxt == pos:
                return
            yield from self._lazy_chain(ctx, nxt)


@dataclass
class Plus(Node):
    child: Optional["Node"] = None
    greedy: bool = True
    name: str = "Plus"

    def label(self) -> str:
        return f"{self.child.label() if self.child else ''}+"

    def match(self, ctx, pos):
        # one required, then star
        count = 0
        positions: List[int] = []
        cur = pos
        # first match (required)
        got = False
        for nxt in self.child.match(ctx, cur):
            if nxt == cur:
                ctx.step(cur, self, "STOP", "zero-width match in +")
                return
            cur = nxt
            count = 1
            positions.append(cur)
            got = True
            break
        if not got:
            ctx.step(pos, self, "FAIL", "+ needs at least one match")
            return
        # subsequent matches (greedy)
        while True:
            found = False
            for nxt in self.child.match(ctx, cur):
                if nxt == cur:
                    break
                cur = nxt
                count += 1
                positions.append(cur)
                found = True
                break
            if not found:
                break
        for p in reversed(positions):
            ctx.step(p, self, "YIELD", f"+ matched {len(positions)} times -> pos {p}")
            yield p


@dataclass
class OptionalNode(Node):
    child: Optional["Node"] = None
    greedy: bool = True
    name: str = "Opt"

    def label(self) -> str:
        return f"{self.child.label() if self.child else ''}?"

    def match(self, ctx, pos):
        matched = False
        for nxt in self.child.match(ctx, pos):
            matched = True
            ctx.step(nxt, self, "YIELD", f"? matched once -> pos {nxt}")
            yield nxt
        if not matched:
            ctx.step(pos, self, "YIELD", "? matched zero times")
        # always allow skipping
        ctx.step(pos, self, "YIELD", f"? skipping -> pos {pos}")
        yield pos


# --------------------------------------------------------------------------- #
# Match context -- records the trace
# --------------------------------------------------------------------------- #


@dataclass
class MatchContext:
    input: str
    steps: List["Step"] = field(default_factory=list)
    max_steps: int = 100000
    group_spans: dict = field(default_factory=dict)
    matched: bool = False
    match_start: int = -1
    match_end: int = -1

    def step(self, pos: int, node: Node, action: str, note: str = ""):
        if len(self.steps) >= self.max_steps:
            raise RuntimeError("step limit exceeded (possible catastrophic backtracking)")
        self.steps.append(Step(pos=pos, node=node, action=action, note=note,
                               depth=len(self.steps)))

    def match_sequence(self, nodes: List[Node], pos: int, parent: Node):
        """Backtracking match of a sequence of nodes starting at `pos`.

        Yields successful end positions after the whole sequence matches.
        """
        if not nodes:
            yield pos
            return

        def helper(i: int, p: int):
            if i == len(nodes):
                yield p
                return
            for nxt in nodes[i].match(self, p):
                yield from helper(i + 1, nxt)

        yield from helper(0, pos)


@dataclass
class Step:
    pos: int
    node: Node
    action: str
    note: str
    depth: int


# --------------------------------------------------------------------------- #
# Parser -- recursive descent
# --------------------------------------------------------------------------- #

class ParseError(Exception):
    pass


class Parser:
    def __init__(self, pattern: str):
        self.p = pattern
        self.i = 0
        self.group_count = 0

    def peek(self) -> Optional[str]:
        return self.p[self.i] if self.i < len(self.p) else None

    def next(self) -> str:
        ch = self.p[self.i]
        self.i += 1
        return ch

    def eof(self) -> bool:
        return self.i >= len(self.p)

    def parse(self) -> List[Node]:
        nodes = self.parse_alt()
        if not self.eof():
            raise ParseError(f"unexpected character {self.peek()!r} at {self.i}")
        return nodes

    def parse_alt(self) -> List[Node]:
        """alternation: seq ('|' seq)*"""
        branches = [self.parse_seq()]
        while self.peek() == "|":
            self.next()
            branches.append(self.parse_seq())
        if len(branches) == 1:
            return branches[0]
        return [Alternation(options=branches)]

    def parse_seq(self) -> List[Node]:
        """sequence: atom*"""
        nodes: List[Node] = []
        while not self.eof() and self.peek() not in ("|", ")"):
            nodes.append(self.parse_atom_quant())
        return nodes

    def parse_atom_quant(self) -> Node:
        """atom followed by optional quantifier"""
        atom = self.parse_atom()
        if self.eof():
            return atom
        ch = self.peek()
        if ch == "*":
            self.next()
            greedy = self._consume_lazy()
            return Star(child=atom, greedy=greedy)
        elif ch == "+":
            self.next()
            greedy = self._consume_lazy()
            return Plus(child=atom, greedy=greedy)
        elif ch == "?":
            self.next()
            greedy = self._consume_lazy()
            return OptionalNode(child=atom, greedy=greedy)
        return atom

    def _consume_lazy(self) -> bool:
        # support lazy '?'
        if self.peek() == "?":
            self.next()
            return False
        return True

    def parse_atom(self) -> Node:
        ch = self.peek()
        if ch is None:
            raise ParseError("unexpected end of pattern")
        if ch == "(":
            return self.parse_group()
        if ch == "[":
            return self.parse_class()
        if ch == ".":
            self.next()
            return AnyChar()
        if ch == "^":
            self.next()
            return Anchor(kind="^")
        if ch == "$":
            self.next()
            return Anchor(kind="$")
        if ch == "\\":
            return self.parse_escape()
        # default literal
        self.next()
        return Literal(char=ch)

    def parse_group(self) -> Node:
        assert self.next() == "("
        self.group_count += 1
        idx = self.group_count
        children = self.parse_alt()
        if self.peek() != ")":
            raise ParseError("missing closing )")
        self.next()
        return Group(children=children, index=idx)

    def parse_class(self) -> Node:
        assert self.next() == "["
        negated = False
        if self.peek() == "^":
            negated = True
            self.next()
        ranges: List[Tuple[str, str]] = []
        # ] as first char is a literal
        first = True
        while True:
            ch = self.peek()
            if ch is None:
                raise ParseError("unterminated character class")
            if ch == "]" and not first:
                self.next()
                break
            first = False
            # handle escape inside class
            if ch == "\\":
                self.next()
                esc = self.next()
                resolved = self._resolve_escape(esc)
                # escapes like \d \w \s expand to ranges
                if isinstance(resolved, list):
                    ranges.extend(resolved)
                    continue
                lo = resolved
            else:
                lo = self.next()
            # range?
            if self.peek() == "-" and self.i + 1 < len(self.p) and self.p[self.i + 1] != "]":
                self.next()  # consume -
                hi = self.peek()
                if hi == "\\":
                    self.next()
                    hi = self._resolve_escape(self.next())
                    if isinstance(hi, list):
                        # unusual; treat each as separate
                        for h in hi:
                            ranges.append((lo, h))
                        continue
                else:
                    hi = self.next()
                ranges.append((lo, hi))
            else:
                ranges.append((lo, lo))
        return CharClass(ranges=ranges, negated=negated)

    def parse_escape(self) -> Node:
        assert self.next() == "\\"
        esc = self.next()
        resolved = self._resolve_escape(esc)
        if isinstance(resolved, list):
            # \d \w \s -> char class
            return CharClass(ranges=resolved, negated=False)
        if esc in "dwsDWS":
            # shouldn't reach because resolved is a list for those
            return Literal(char=resolved)
        return Literal(char=resolved)

    def _resolve_escape(self, esc: str):
        """Return a literal char, or a list of (a,b) ranges for classes."""
        classes = {
            "d": [("0", "9")],
            "w": [("a", "z"), ("A", "Z"), ("0", "9"), ("_", "_")],
            "s": [(" ", " "), ("\t", "\t"), ("\n", "\n")],
        }
        if esc in classes:
            return classes[esc]
        if esc in "DWS":
            base = esc.lower()
            # we represent negated class escapes as a CharClass with negated
            ranges = classes[base]
            # We need to return a Node, but _resolve_escape is shared with
            # class parsing. Handle uppercase escapes specially here.
            return CharClass(ranges=ranges, negated=True)
        mapping = {
            "n": "\n", "t": "\t", "r": "\r",
            ".": ".", "\\": "\\", "[": "[", "]": "]",
            "(": "(", ")": ")", "|": "|", "*": "*", "+": "+",
            "?": "?", "^": "^", "$": "$", "/": "/",
            "0": "\0",
        }
        return mapping.get(esc, esc)


# --------------------------------------------------------------------------- #
# Matching entry point
# --------------------------------------------------------------------------- #

def run_match(pattern: str, text: str, max_steps: int = 100000) -> Tuple[bool, MatchContext]:
    """Compile `pattern` and try to match it against `text`.

    The match is unanchored (like re.search): it succeeds if the pattern
    matches starting at any position.
    """
    parser = Parser(pattern)
    try:
        ast = parser.parse()
    except ParseError as e:
        return False, None  # type: ignore

    ctx = MatchContext(input=text, max_steps=max_steps)
    for start in range(len(text) + 1):
        ctx.step(start, Anchor(kind="^"), "TRY", f"search from pos {start}")
        found = False
        try:
            for end in ctx.match_sequence(ast, start, Anchor()):
                ctx.matched = True
                ctx.match_start = start
                ctx.match_end = end
                found = True
                break
        except RuntimeError:
            break
        if found:
            return True, ctx
    # one final attempt at the empty string / end
    return ctx.matched, ctx


def run_match_full(pattern: str, text: str, max_steps: int = 100000) -> Tuple[bool, MatchContext]:
    """Like run_match but only reports a match found anywhere."""
    ok, ctx = run_match(pattern, text, max_steps)
    return ok, ctx


# --------------------------------------------------------------------------- #
# Rendering the trace
# --------------------------------------------------------------------------- #

ACTION_COLORS = {
    "TRY": CYAN,
    "MATCH": GREEN,
    "FAIL": RED,
    "BACKTRACK": YELLOW,
    "YIELD": MAGENTA,
    "LEAVE": GRAY,
    "STOP": YELLOW,
    "ACCEPT": BOLD + GREEN,
}


def render_cursor_line(text: str, pos: int, color: bool = True) -> str:
    """Render the input string with a highlighted cursor at `pos`."""
    if pos > len(text):
        pos = len(text)
    before = text[:pos]
    at = text[pos:pos + 1] if pos < len(text) else "<end>"
    after = text[pos + 1:]
    if color:
        return (
            GRAY + before.replace("\n", "\\n") +
            BG_YELLOW + BOLD + (at.replace("\n", "\\n")) + RESET +
            GRAY + after.replace("\n", "\\n") + RESET
        )
    else:
        before = before.replace("\n", "\\n")
        at = at.replace("\n", "\\n")
        after = after.replace("\n", "\\n")
        return f"{before}[{at}]{after}"


def render_trace(steps: List[Step], text: str, pattern: str, color: bool,
                 max_steps: Optional[int] = None, show_all: bool = False) -> str:
    lines: List[str] = []
    lines.append(_c(f"Pattern : {pattern}", BOLD, color))
    lines.append(_c(f"Input   : {text!r} (len={len(text)})", BOLD, color))
    lines.append(_c(f"Steps   : {len(steps)}", DIM, color))
    lines.append("")

    shown = steps if (show_all or max_steps is None) else steps[:max_steps]
    truncated = (max_steps is not None and not show_all and len(steps) > max_steps)

    for idx, s in enumerate(shown):
        cursor = render_cursor_line(text, s.pos, color)
        action_c = ACTION_COLORS.get(s.action, "")
        action_str = _c(f"{s.action:9}", action_c, color)
        node_str = _c(f"{s.node.label():18}", BLUE, color)
        note = s.note
        lines.append(f"{idx:4}  pos={s.pos:3}  {action_str} {node_str}  {note}")
        lines.append(f"      {cursor}")

    if truncated:
        lines.append(_c(f"... {len(steps) - max_steps} more steps omitted "
                       f"(use --steps to show all)", DIM, color))
    return "\n".join(lines)


def _c(text: str, code: str, color: bool) -> str:
    if not color or not code:
        return text
    return f"{code}{text}{RESET}"


def render_summary(ctx: MatchContext, pattern: str, text: str, color: bool) -> str:
    lines: List[str] = []
    lines.append("")
    lines.append(_c("=" * 60, DIM, color))
    if ctx.matched:
        s, e = ctx.match_start, ctx.match_end
        lines.append(_c("RESULT  : MATCH", BOLD + GREEN, color))
        lines.append(_c(f"span     : [{s}, {e})", DIM, color))
        matched_text = text[s:e]
        lines.append(_c(f"matched  : {matched_text!r}", BOLD, color))
    else:
        lines.append(_c("RESULT  : NO MATCH", BOLD + RED, color))
    lines.append(_c(f"total steps examined: {len(ctx.steps)}", DIM, color))
    lines.append(_c("=" * 60, DIM, color))
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_demo() -> List[Tuple[str, str, str]]:
    return [
        ("hello", "hello world", "literal match at start"),
        ("a*b", "aaaab", "greedy star then literal"),
        ("a+b", "b", "plus needs at least one (fails)"),
        ("(ab)+", "ababab", "group repetition"),
        ("[0-9]+", "year 2026", "char class for digits"),
        ("a.*z", "abc...xyz", "greedy dot-star"),
        ("^foo$", "foo", "anchored full match"),
        ("cat|dog", "I have a dog", "alternation"),
        ("colou?r", "color", "optional letter"),
    ]


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    color = supports_color(sys.stdout)

    parser = argparse.ArgumentParser(
        prog="regex_viz",
        description="A mini backtracking regex engine that visualizes the match.",
    )
    parser.add_argument("pattern", nargs="?", help="regex pattern")
    parser.add_argument("input", nargs="?", help="input string to match against")
    parser.add_argument("--demo", action="store_true", help="run built-in demo examples")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    parser.add_argument("--steps", action="store_true", help="show every step (not truncated)")
    parser.add_argument("--max-steps", type=int, default=40,
                        help="max steps to display per example (default 40)")
    args = parser.parse_args(argv)

    if args.no_color:
        color = False

    if args.demo:
        print(_c("Regex Engine Visualizer — Demo", BOLD, color))
        print(_c("Each example shows the step-by-step backtracking trace.\n", DIM, color))
        for pat, text, desc in build_demo():
            print(_c("─" * 60, GRAY, color))
            print(_c(f"DEMO: {desc}", BOLD + CYAN, color))
            print(_c(f"  regex_viz '{pat}' '{text}'", DIM, color))
            ok, ctx = run_match(pat, text)
            if ctx is None:
                print(_c("  [parse error]", RED, color))
                continue
            print(render_trace(ctx.steps, text, pat, color,
                               max_steps=args.max_steps, show_all=args.steps))
            print(render_summary(ctx, pat, text, color))
            print()
        return 0

    if args.pattern is None or args.input is None:
        parser.error("pattern and input are required (or use --demo)")

    pat = args.pattern
    text = args.input
    try:
        Parser(pat).parse()
    except ParseError as e:
        print(_c(f"Parse error: {e}", RED, color), file=sys.stderr)
        return 2

    ok, ctx = run_match(pat, text)
    if ctx is None:
        print(_c("Parse error", RED, color), file=sys.stderr)
        return 2

    print(render_trace(ctx.steps, text, pat, color,
                       max_steps=None if args.steps else args.max_steps,
                       show_all=args.steps))
    print(render_summary(ctx, pat, text, color))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())