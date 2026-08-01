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

__version__ = "1.2.0"

# Shorthand character-class predicates -------------------------------------- #
# Each lowercase shorthand maps to the list of (lo, hi) ranges that define
# the characters it matches.  Uppercase variants (\D \W \S) match the
# *negation* of these sets and are handled by combining the same ranges with
# the `negated` flag of a CharClass (standalone) or a `shorthand_negations`
# entry (inside a character class).
SHORTHAND_RANGES = {
    "d": [("0", "9")],
    "w": [("a", "z"), ("A", "Z"), ("0", "9"), ("_", "_")],
    "s": [(" ", " "), ("\t", "\t"), ("\n", "\n"), ("\r", "\r"),
          ("\f", "\f"), ("\v", "\v")],
}


def _is_word_char(ch: str) -> bool:
    """Match Python's `\\w` semantics: alphanumeric or underscore."""
    return ch.isalnum() or ch == "_"

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
    # Ranges whose *complement* also matches (for `[\D \w]`-style unions).
    # Each entry is the set of ranges that must NOT contain the char.
    shorthand_negations: List[List[Tuple[str, str]]] = field(default_factory=list)
    name: str = "Class"

    def label(self) -> str:
        parts = []
        for a, b in self.ranges:
            parts.append(a if a == b else f"{a}-{b}")
        body = "".join(parts)
        for neg in self.shorthand_negations:
            nparts = []
            for a, b in neg:
                nparts.append(a if a == b else f"{a}-{b}")
            body += "(^" + "".join(nparts) + ")"
        return f"[{'^' if self.negated else ''}{body}]"

    def _in(self, ch: str) -> bool:
        r"""True if `ch` is a member of this class's *positive* definition.

        A character is a member if it falls inside any explicit range OR it
        satisfies any negated shorthand (a `\D`-style member means "any char
        NOT in the digit set", so a non-digit char is a member).
        """
        for a, b in self.ranges:
            if a <= ch <= b:
                return True
        for neg in self.shorthand_negations:
            inside_neg = any(a <= ch <= b for a, b in neg)
            if not inside_neg:
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
class WordBoundary(Node):
    """Matches `\\b` -- a zero-width assertion at a word/non-word boundary.

    A boundary exists at position `pos` when exactly one of the characters
    on either side is a "word character" (`\\w`).
    """
    negate: bool = False  # True for `\B`
    name: str = "Boundary"

    def label(self) -> str:
        return r"\B" if self.negate else r"\b"

    @staticmethod
    def _word_at(text: str, i: int) -> bool:
        return 0 <= i < len(text) and _is_word_char(text[i])

    def _is_boundary(self, text: str, pos: int) -> bool:
        before = self._word_at(text, pos - 1)
        after = self._word_at(text, pos)
        return before != after

    def match(self, ctx, pos):
        # Match Python's `re` semantics: on an empty input string neither
        # \b nor \B matches at all (CPython's SRE returns 0 for both
        # AT_BOUNDARY and AT_NON_BOUNDARY when beginning == end).
        if len(ctx.input) == 0:
            ctx.step(pos, self, "FAIL",
                     f"{self.label()} on empty input (never matches)")
            return
        boundary = self._is_boundary(ctx.input, pos)
        ok = (not boundary) if self.negate else boundary
        ctx.step(pos, self, "MATCH" if ok else "FAIL",
                 f"{self.label()} at pos {pos}")
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
        return f"{self.child.label() if self.child else ''}*{'?' if not self.greedy else ''}"

    def match(self, ctx, pos):
        """Backtracking star.

        Greedy  : consume as many as possible, then yield from longest to
                  shortest so the rest of the pattern can backtrack into the
                  captured text.
        Lazy    : yield the current (zero-match) position first, then try to
                  consume one more and recurse -- yielding progressively longer
                  matches only if a shorter one fails downstream.
        """
        if self.greedy:
            # Collect all reachable positions by repeatedly consuming one child.
            positions = [pos]
            cur = pos
            while True:
                advanced = False
                for nxt in self.child.match(ctx, cur):
                    if nxt == cur:
                        # Zero-width match would loop forever; stop here.
                        ctx.step(cur, self, "STOP", "zero-width match in *")
                        break
                    cur = nxt
                    positions.append(cur)
                    advanced = True
                    break
                if not advanced:
                    break
            # Yield greediest-first so the engine can backtrack into it.
            for p in reversed(positions):
                ctx.step(p, self, "YIELD",
                         f"* matched {len(positions)-1} times -> pos {p}")
                yield p
        else:  # lazy: try zero first, then progressively more
            yield from self._lazy_chain(ctx, pos)

    def _lazy_chain(self, ctx, pos):
        """Lazy `*`: yield `pos` first, then try one more match and recurse."""
        ctx.step(pos, self, "YIELD", f"*? -> pos {pos}")
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
        return f"{self.child.label() if self.child else ''}+{'?' if not self.greedy else ''}"

    def match(self, ctx, pos):
        """Backtracking plus (one or more).

        Greedy  : require one match, then consume as many more as possible,
                  yielding from longest to shortest.
        Lazy    : require one match, then yield that position first and only
                  consume more if the rest of the pattern fails downstream.

        A zero-width first match (e.g. ``()+`` or ``(a*)+`` at end of input)
        still satisfies the "one or more" requirement -- it yields `pos` once
        and stops, since further iterations would loop forever without
        advancing.  This mirrors Python's ``re`` (``re.search('()+', 'abc')``
        matches the empty string at pos 0).
        """
        # First match is mandatory in both modes.
        got = False
        first_pos = pos
        zero_width = False
        for nxt in self.child.match(ctx, pos):
            if nxt == pos:
                # Zero-width: counts as the mandatory one match, but no
                # further progress is possible.
                zero_width = True
                got = True
                ctx.step(pos, self, "STOP",
                         "zero-width first match in + (counts as the one)")
                break
            first_pos = nxt
            got = True
            break
        if not got:
            ctx.step(pos, self, "FAIL", "+ needs at least one match")
            return

        if zero_width:
            ctx.step(pos, self, "YIELD", "+ matched once (zero-width) -> pos")
            yield pos
            return

        if self.greedy:
            # Keep consuming greedily, then backtrack from longest to shortest.
            positions = [first_pos]
            cur = first_pos
            while True:
                advanced = False
                for nxt in self.child.match(ctx, cur):
                    if nxt == cur:
                        break
                    cur = nxt
                    positions.append(cur)
                    advanced = True
                    break
                if not advanced:
                    break
            for p in reversed(positions):
                ctx.step(p, self, "YIELD",
                         f"+ matched {len(positions)} times -> pos {p}")
                yield p
        else:
            # Lazy: yield the minimum (one match) first, then try more.
            yield from self._lazy_plus_chain(ctx, first_pos)

    def _lazy_plus_chain(self, ctx, pos):
        """Lazy `+`: yield `pos`, then try one more match and recurse."""
        ctx.step(pos, self, "YIELD", f"+? -> pos {pos}")
        yield pos
        for nxt in self.child.match(ctx, pos):
            if nxt == pos:
                return
            yield from self._lazy_plus_chain(ctx, nxt)


@dataclass
class OptionalNode(Node):
    child: Optional["Node"] = None
    greedy: bool = True
    name: str = "Opt"

    def label(self) -> str:
        return f"{self.child.label() if self.child else ''}?{'?' if not self.greedy else ''}"

    def match(self, ctx, pos):
        """Backtracking optional (zero or one).

        Greedy  : try to match once first, then fall back to skipping.
        Lazy    : skip first, then try to match once as a fallback.
        """
        if self.greedy:
            matched = False
            for nxt in self.child.match(ctx, pos):
                matched = True
                ctx.step(nxt, self, "YIELD", f"? matched once -> pos {nxt}")
                yield nxt
            if not matched:
                ctx.step(pos, self, "YIELD", "? matched zero times")
            # Always allow skipping as the final fallback.
            ctx.step(pos, self, "YIELD", f"? skipping -> pos {pos}")
            yield pos
        else:  # lazy: skip first, then try matching once
            ctx.step(pos, self, "YIELD", f"?? skipping -> pos {pos}")
            yield pos
            for nxt in self.child.match(ctx, pos):
                ctx.step(nxt, self, "YIELD", f"?? matched once -> pos {nxt}")
                yield nxt


@dataclass
class Repeat(Node):
    """Bounded repetition: `{n}`, `{n,}`, `{n,m}` (greedy or lazy).

    Implemented as "at least `lo` matches, at most `hi` extra matches" where
    `hi=None` means unbounded.  Greedy mode consumes extra matches first and
    backtracks; lazy mode yields the minimum first.
    """
    child: Optional["Node"] = None
    lo: int = 0
    hi: Optional[int] = None  # None == infinity
    greedy: bool = True
    name: str = "Repeat"

    def label(self) -> str:
        child = self.child.label() if self.child else ""
        if self.hi is None:
            rep = f"{{{self.lo},}}"
        else:
            rep = f"{{{self.lo},{self.hi}}}" if self.lo != self.hi else f"{{{self.lo}}}"
        return f"{child}{rep}{'?' if not self.greedy else ''}"

    def match(self, ctx, pos):
        """Bounded backtracking repetition.

        Mandatory minimum matches: we need exactly `lo` child matches.  We
        take the first success of each iteration.  A zero-width child match
        (e.g. ``(a*)`` matching the empty tail of the input) still *counts*
        toward the minimum -- further iterations at the same position would
        also be zero-width, so we fast-forward the remaining count instead of
        looping forever (this mirrors Python's ``re`` semantics, where
        ``(a*){2}`` matches ``'aaa'``: the first ``a*`` consumes ``aaa``, the
        second matches empty at pos 3).
        """
        cur = pos
        done = 0
        zero_width = False
        while done < self.lo:
            got = False
            for nxt in self.child.match(ctx, cur):
                if nxt == cur:
                    # Zero-width: counts as one iteration; all remaining
                    # minimum iterations would also be zero-width here, so
                    # satisfy the rest of the minimum at once.
                    done = self.lo
                    zero_width = True
                    got = True
                    ctx.step(cur, self, "STOP",
                             f"zero-width match in {{{self.lo}}} minimum "
                             f"(satisfied {self.lo} min)")
                    break
                cur = nxt
                done += 1
                got = True
                break
            if not got:
                ctx.step(pos, self, "FAIL",
                         f"{{{self.lo}}} needs {self.lo} matches")
                return
        mandatory_pos = cur

        extra_cap = None if self.hi is None else max(self.hi - self.lo, 0)

        if self.greedy:
            # Consume as many extra as possible (up to cap), then backtrack.
            # A zero-width extra match would loop forever, so we stop.
            positions = [mandatory_pos]
            c = mandatory_pos
            count = 0
            while extra_cap is None or count < extra_cap:
                if zero_width:
                    break  # child matched zero-width in minimum; no progress
                advanced = False
                for nxt in self.child.match(ctx, c):
                    if nxt == c:
                        break
                    c = nxt
                    positions.append(c)
                    count += 1
                    advanced = True
                    break
                if not advanced:
                    break
            for p in reversed(positions):
                ctx.step(p, self, "YIELD",
                         f"{self.label()} -> pos {p}")
                yield p
        else:
            # Lazy: yield minimum first, then progressively more.
            yield from self._lazy_repeat(ctx, mandatory_pos, extra_cap, 0,
                                         zero_width)

    def _lazy_repeat(self, ctx, pos, cap, used, zero_width=False):
        ctx.step(pos, self, "YIELD", f"{self.label()} -> pos {pos}")
        yield pos
        if zero_width:
            return  # no further progress possible
        if cap is not None and used >= cap:
            return
        for nxt in self.child.match(ctx, pos):
            if nxt == pos:
                return
            yield from self._lazy_repeat(ctx, nxt, cap, used + 1)


# --------------------------------------------------------------------------- #
# Match context -- records the trace
# --------------------------------------------------------------------------- #


class StepLimitExceeded(Exception):
    """Raised internally when the recorded-step budget is exhausted.

    This is a safety guard against catastrophic backtracking.  It is caught
    by `run_match` so the limit never escapes to the caller -- the match
    simply stops early and the partial result (if any) is returned.
    """


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
            raise StepLimitExceeded(
                "step limit exceeded (possible catastrophic backtracking)")
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
        """atom followed by an optional quantifier (*, +, ?, {n}, {n,}, {n,m}).

        Each quantifier may be followed by a `?` to make it lazy.  A second
        quantifier immediately after the first (e.g. `a**`, `a++`, `a*+`,
        `a?{2}`) is a "multiple repeat" error -- Python's `re` rejects it and
        we do too, rather than silently treating the stray `*`/`+`/`?` as a
        literal.
        """
        atom = self.parse_atom()
        if self.eof():
            return atom
        ch = self.peek()
        quantified = False
        if ch == "*":
            self.next()
            greedy = self._consume_lazy()
            atom = Star(child=atom, greedy=greedy)
            quantified = True
        elif ch == "+":
            self.next()
            greedy = self._consume_lazy()
            atom = Plus(child=atom, greedy=greedy)
            quantified = True
        elif ch == "?":
            self.next()
            greedy = self._consume_lazy()
            atom = OptionalNode(child=atom, greedy=greedy)
            quantified = True
        elif ch == "{":
            rep = self._try_parse_brace_quant()
            if rep is not None:
                lo, hi = rep
                greedy = self._consume_lazy()
                atom = Repeat(child=atom, lo=lo, hi=hi, greedy=greedy)
                quantified = True
            # Not a valid quantifier -- treat '{' as a literal (already
            # consumed by parse_atom if it reached here, so just return atom).
        if quantified and not self.eof() and self.peek() in ("*", "+", "?", "{"):
            raise ParseError(
                f"multiple repeat at position {self.i}: nothing to repeat "
                f"after a quantifier ({self.peek()!r})")
        return atom

    def _try_parse_brace_quant(self) -> Optional[Tuple[int, Optional[int]]]:
        """Attempt to parse `{n}`, `{n,}`, `{n,m}`, `{,m}`, or `{,}` starting
        at the `{`.

        Returns `(lo, hi)` on success (hi is None for `{n,}` / `{,}`), or `None`
        if the text starting at the cursor is not a valid brace quantifier (in
        which case the cursor is left untouched so `{` is treated as a literal).

        Per Python's `re`, `{,m}` is equivalent to `{0,m}` and `{,}` to `{0,}`.
        """
        assert self.peek() == "{"
        start = self.i  # remember position of '{' for rollback
        self.next()  # consume '{'
        digits = ""
        while self.peek() is not None and self.peek().isdigit():
            digits += self.next()
        if self.peek() == ",":
            # `{,m}` or `{,}` -- empty lower bound means 0 (matches `re`).
            if not digits:
                lo = 0
            else:
                lo = int(digits)
            self.next()  # consume ','
            digits2 = ""
            while self.peek() is not None and self.peek().isdigit():
                digits2 += self.next()
            hi = int(digits2) if digits2 else None  # None == infinity
        elif not digits:
            # Not a quantifier (e.g. `{` or `{abc`); roll back.
            self.i = start
            return None
        else:
            lo = int(digits)
            hi = lo  # `{n}` exact count
        if self.peek() != "}":
            # Malformed -- roll back and treat as literal text.
            self.i = start
            return None
        self.next()  # consume '}'
        if hi is not None and hi < lo:
            raise ParseError(f"{{{lo},{hi}}}: min > max")
        return lo, hi

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
        # Detect `(?...)` extension syntax.  These are not supported by this
        # educational engine (no lookaround, named groups, or inline flags),
        # but we must NOT silently parse the `?` as a literal inside a normal
        # group -- that would mislead users into thinking the pattern worked.
        # Raise a clear ParseError instead.
        if self.peek() == "?":
            nxt = self.p[self.i + 1] if self.i + 1 < len(self.p) else ""
            kind = {
                ":": "non-capturing group (?:...)",
                "=": "lookahead (?=...)",
                "!": "negative lookahead (?!...)",
                "<": "lookbehind (?<=... / (?<!...)",
                "P": "named group (?P<name>...) / backreference (?P=name)",
            }.get(nxt, f"unknown (?{nxt} extension")
            raise ParseError(
                f"unsupported group syntax '(?{nxt}': {kind} is not supported "
                f"by this engine")
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
        shorthand_negations: List[List[Tuple[str, str]]] = []
        # `]` as the very first char is treated as a literal member.
        first = True
        while True:
            ch = self.peek()
            if ch is None:
                raise ParseError("unterminated character class")
            if ch == "]" and not first:
                self.next()
                break
            first = False
            # Handle escape inside class.
            if ch == "\\":
                self.next()
                if self.eof():
                    raise ParseError("trailing backslash in character class")
                esc = self.next()
                resolved = self._resolve_escape(esc)
                if isinstance(resolved, list):
                    # Positive shorthand (\d \w \s) -- add its ranges.
                    ranges.extend(resolved)
                    continue
                if isinstance(resolved, tuple) and resolved[0] == "__negate__":
                    # Negated shorthand (\D \W \S) inside a class -- the char
                    # matches if it is NOT in the listed ranges.
                    shorthand_negations.append(resolved[1])
                    continue
                lo = resolved
            else:
                lo = self.next()
            # Range?  e.g. a-z, 0-9
            if (self.peek() == "-" and self.i + 1 < len(self.p)
                    and self.p[self.i + 1] != "]"):
                self.next()  # consume '-'
                hi = self.peek()
                if hi == "\\":
                    self.next()
                    hi = self._resolve_escape(self.next())
                    if isinstance(hi, list) or isinstance(hi, tuple):
                        # A shorthand as the *end* of a range doesn't make
                        # sense; treat each element as a separate singleton.
                        ranges.append((lo, lo))
                        if isinstance(hi, list):
                            for h in hi:
                                ranges.append((h, h))
                        continue
                else:
                    hi = self.next()
                if lo > hi:
                    raise ParseError(f"invalid range {lo!r}-{hi!r} in class")
                ranges.append((lo, hi))
            else:
                ranges.append((lo, lo))
        return CharClass(ranges=ranges, negated=negated,
                        shorthand_negations=shorthand_negations)

    def parse_escape(self) -> Node:
        """Parse a `\\X` escape sequence and return the matching AST node.

        Lowercase shorthands (`\\d \\w \\s`) become positive CharClass nodes.
        Uppercase shorthands (`\\D \\W \\S`) become *negated* CharClass nodes
        matching the complement of the corresponding lowercase set.
        `\\b` / `\\B` become word-boundary assertions; everything else resolves
        to a single literal character.
        """
        assert self.next() == "\\"
        if self.eof():
            raise ParseError("trailing backslash at end of pattern")
        esc = self.next()
        if esc == "b":
            return WordBoundary(negate=False)
        if esc == "B":
            return WordBoundary(negate=True)
        if esc in SHORTHAND_RANGES:
            return CharClass(ranges=list(SHORTHAND_RANGES[esc]), negated=False)
        if esc in ("D", "W", "S"):
            return CharClass(ranges=list(SHORTHAND_RANGES[esc.lower()]),
                             negated=True)
        # Literal escape -- resolve to a single character.
        mapping = {
            "n": "\n", "t": "\t", "r": "\r", "f": "\f", "v": "\v",
            "0": "\0", "a": "\a",
            ".": ".", "\\": "\\", "[": "[", "]": "]",
            "(": "(", ")": ")", "|": "|", "*": "*", "+": "+",
            "?": "?", "^": "^", "$": "$", "/": "/",
            "{": "{", "}": "}", "-": "-", " ": " ",
        }
        return Literal(char=mapping.get(esc, esc))

    def _resolve_escape(self, esc: str):
        """Resolve an escape for use *inside a character class*.

        Returns either a list of `(lo, hi)` ranges (for shorthands like `\\d`,
        `\\w`, `\\s` -- including negated uppercase forms which contribute a
        `shorthand_negations` entry to the surrounding CharClass) or a single
        literal character string.

        Note: `\\b` inside a class means backspace (U+0008), not a boundary.
        """
        if esc in SHORTHAND_RANGES:
            return list(SHORTHAND_RANGES[esc])
        if esc in ("D", "W", "S"):
            # Negated shorthand inside a class.  We signal this by returning a
            # tuple tagged with the ranges to negate; parse_class turns that
            # into a shorthand_negations entry.  We use a distinct marker type.
            return ("__negate__", list(SHORTHAND_RANGES[esc.lower()]))
        if esc == "b":
            return "\b"  # backspace inside a character class
        mapping = {
            "n": "\n", "t": "\t", "r": "\r", "f": "\f", "v": "\v",
            "0": "\0", "a": "\a",
            ".": ".", "\\": "\\", "[": "[", "]": "]",
            "(": "(", ")": ")", "|": "|", "*": "*", "+": "+",
            "?": "?", "^": "^", "$": "$", "/": "/",
            "{": "{", "}": "}", "-": "-",
        }
        return mapping.get(esc, esc)


# --------------------------------------------------------------------------- #
# Matching entry point
# --------------------------------------------------------------------------- #

def run_match(pattern: str, text: str, max_steps: int = 100000) -> Tuple[bool, MatchContext]:
    """Compile `pattern` and try to match it against `text`.

    The match is unanchored (like re.search): it succeeds if the pattern
    matches starting at any position.

    If the step budget (`max_steps`) is exhausted, matching stops early and
    whatever partial result (if any) is returned without raising -- the step
    limit is a safety guard against catastrophic backtracking, not a crash.
    """
    parser = Parser(pattern)
    try:
        ast = parser.parse()
    except ParseError as e:
        return False, None  # type: ignore

    ctx = MatchContext(input=text, max_steps=max_steps)
    for start in range(len(text) + 1):
        # The "search from pos N" bookkeeping step is itself recorded via
        # ctx.step, which can raise StepLimitExceeded if the budget was
        # exhausted during the previous position's attempt.  Guard it so the
        # limit never escapes to the caller.
        try:
            ctx.step(start, Anchor(kind="^"), "TRY", f"search from pos {start}")
        except StepLimitExceeded:
            break
        found = False
        try:
            for end in ctx.match_sequence(ast, start, Anchor()):
                ctx.matched = True
                ctx.match_start = start
                ctx.match_end = end
                found = True
                break
        except StepLimitExceeded:
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
    """Curated demo examples that showcase each engine feature."""
    return [
        ("hello", "hello world", "literal match at start"),
        ("a*b", "aaaab", "greedy star then literal"),
        ("a+b", "b", "plus needs at least one (fails)"),
        ("(ab)+", "ababab", "group repetition"),
        ("[0-9]+", "year 2026", "char class for digits"),
        ("a.*z", "abc...xyz", "greedy dot-star"),
        ("a.*?z", "abczxyz", "lazy dot-star (stops early)"),
        ("^foo$", "foo", "anchored full match"),
        ("cat|dog", "I have a dog", "alternation"),
        ("colou?r", "color", "optional letter"),
        ("a{3}", "aaaa", "exact repetition {n}"),
        ("a{2,4}", "aaaaa", "bounded repetition {n,m}"),
        (r"\bfoo\b", "a foo b", "word boundary \\b"),
        (r"\d{3}-\d{4}", "call 555-1234", "phone-number pattern"),
        (r"\D+", "abc123", "negated shorthand \\D"),
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
    parser.add_argument("--demo", action="store_true",
                        help="run built-in demo examples")
    parser.add_argument("--no-color", action="store_true",
                        help="disable ANSI colors (for piping / logs)")
    parser.add_argument("--steps", action="store_true",
                        help="show every step (not truncated)")
    parser.add_argument("--max-steps", type=int, default=40,
                        help="max steps to display per example (default 40)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="suppress the trace; print only the result line")
    parser.add_argument("--version", action="version",
                        version=f"regex_viz {__version__}")
    args = parser.parse_args(argv)

    if args.no_color:
        color = False

    if args.demo:
        print(_c("Regex Engine Visualizer — Demo", BOLD, color))
        print(_c("Each example shows the step-by-step backtracking trace.\n",
                 DIM, color))
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

    if args.quiet:
        # Scripting mode: a single machine-friendly line.
        if ok:
            print(f"MATCH {ctx.match_start} {ctx.match_end} "
                  f"{text[ctx.match_start:ctx.match_end]!r}")
        else:
            print("NOMATCH")
        return 0 if ok else 1

    print(render_trace(ctx.steps, text, pat, color,
                       max_steps=None if args.steps else args.max_steps,
                       show_all=args.steps))
    print(render_summary(ctx, pat, text, color))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())