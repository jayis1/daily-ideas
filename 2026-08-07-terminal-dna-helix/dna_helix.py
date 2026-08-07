#!/usr/bin/env python3
"""
Terminal DNA Double-Helix Animator
==================================
A rotating, colored ASCII DNA double-helix that lives in your terminal.
Watch base pairs connect, mutate sequences, and transcribe DNA into proteins.

Controls (when run interactively):
    SPACE  pause / resume rotation
    + / -  speed up / slow down
    m      mutate a random base
    t      toggle transcription overlay (show mRNA + protein)
    r      generate a new random genome
    q      quit
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
#  ANSI helpers
# --------------------------------------------------------------------------- #
ANSI = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "dim":     "\033[2m",
    "red":     "\033[31m",
    "green":   "\033[32m",
    "yellow":  "\033[33m",
    "blue":    "\033[34m",
    "magenta": "\033[35m",
    "cyan":    "\033[36m",
    "white":   "\033[37m",
    "bg_black": "\033[40m",
}

# Nucleotide colours
BASE_COLOR = {
    "A": ANSI["green"],
    "T": ANSI["red"],
    "G": ANSI["yellow"],
    "C": ANSI["blue"],
    "U": ANSI["magenta"],
}

COMPLEMENT = {"A": "T", "T": "A", "G": "C", "C": "G"}

# Codon table (standard genetic code) -> single-letter amino acid
CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

AMINO_NAME = {
    "A": "Ala", "R": "Arg", "N": "Asn", "D": "Asp", "C": "Cys",
    "E": "Glu", "Q": "Gln", "G": "Gly", "H": "His", "I": "Ile",
    "L": "Leu", "K": "Lys", "M": "Met", "F": "Phe", "P": "Pro",
    "S": "Ser", "T": "Thr", "W": "Trp", "Y": "Tyr", "V": "Val",
    "*": "STOP",
}


# --------------------------------------------------------------------------- #
#  Genome model
# --------------------------------------------------------------------------- #
@dataclass
class Genome:
    """A double-stranded DNA sequence."""
    coding: list[str] = field(default_factory=list)  # 5'->3' coding strand

    @property
    def template(self) -> list[str]:
        return [COMPLEMENT[b] for b in self.coding]

    @property
    def length(self) -> int:
        return len(self.coding)

    def mutate(self, index: int | None = None) -> str:
        """Mutate a single base and return a description."""
        if not self.coding:
            return "no bases to mutate"
        if index is None:
            index = random.randrange(self.length)
        old = self.coding[index]
        choices = [b for b in "ATGC" if b != old]
        new = random.choice(choices)
        self.coding[index] = new
        return f"pos {index}: {old}->{new}"

    def to_mrna(self) -> str:
        # The coding (sense) strand has the same sequence as mRNA, with T→U.
        # (The template/antisense strand is what gets complemented in vivo.)
        return "".join("U" if b == "T" else b for b in self.coding)

    def to_protein(self) -> str:
        """Translate from the first start codon (or from position 0)."""
        rna = self.to_mrna()
        start = rna.find("AUG")
        if start == -1:
            start = 0
        protein = []
        for i in range(start, len(rna) - 2, 3):
            codon = rna[i:i + 3]
            aa = CODON_TABLE.get("".join({"U": "T"}.get(c, c) for c in codon), "?")
            protein.append(aa)
            if aa == "*":
                break
        return "".join(protein)


def random_genome(length: int = 42) -> Genome:
    return Genome(coding=list(random.choice("ATGC") for _ in range(length)))


# --------------------------------------------------------------------------- #
#  Renderer
# --------------------------------------------------------------------------- #
def hide_cursor() -> None:
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor() -> None:
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def move_home() -> None:
    sys.stdout.write("\033[H")
    sys.stdout.flush()


def helix_frame(genome: Genome, phase: float, cols: int, rows: int,
                show_transcription: bool) -> list[str]:
    """Build a single frame of the helix as a list of string lines."""
    half_w = cols // 2
    visible = min(genome.length, rows - (8 if show_transcription else 4))
    if visible < 4:
        visible = 4

    lines: list[str] = []

    # ---- Title bar -------------------------------------------------------- #
    title = f"{ANSI['bold']}{ANSI['cyan']}  ╔══ DNA DOUBLE HELIX ══╗{ANSI['reset']}"
    lines.append(title)
    lines.append(f"{ANSI['dim']}  length={genome.length}  "
                 f"phase={phase % 6.283:.2f}  bases shown={visible}"
                 f"{ANSI['reset']}")

    # ---- Helix body ------------------------------------------------------- #
    for i in range(visible):
        base = genome.coding[i]
        comp = COMPLEMENT[base]

        # sinusoidal horizontal offset for the two backbones
        angle = phase + i * 0.45
        left_x = int(round(half_w + math_sin(angle) * (half_w - 6)))
        right_x = int(round(half_w + math_sin(angle + 3.14159) * (half_w - 6)))

        # depth: which strand is in front?
        depth_l = math_cos(angle)
        front_is_left = depth_l >= 0

        # build the line as a list of chars, then colourise
        line = [" "] * cols
        line[max(0, min(cols - 1, left_x))] = "║"
        line[max(0, min(cols - 1, right_x))] = "║"

        # connect base pairs between the two strands
        lo, hi = sorted((left_x, right_x))
        mid = (lo + hi) // 2
        if hi - lo > 2:
            for x in range(lo + 1, hi):
                line[x] = "·"
        # place the letters near the midpoint
        if hi - lo >= 4:
            line[mid - 1] = base
            line[mid + 1] = comp

        # colourise
        coloured = []
        for x, ch in enumerate(line):
            if ch == "║":
                if (x == left_x and front_is_left) or (x == right_x and not front_is_left):
                    coloured.append(f"{ANSI['white']}{ANSI['bold']}║{ANSI['reset']}")
                else:
                    coloured.append(f"{ANSI['dim']}║{ANSI['reset']}")
            elif ch in BASE_COLOR:
                coloured.append(f"{BASE_COLOR[ch]}{ch}{ANSI['reset']}")
            elif ch == "·":
                coloured.append(f"{ANSI['dim']}·{ANSI['reset']}")
            else:
                coloured.append(ch)
        lines.append("".join(coloured))

    # ---- Legend / transcription ------------------------------------------ #
    legend = (f"{ANSI['dim']}  A{ANSI['reset']}{ANSI['green']}█{ANSI['reset']} "
              f"{ANSI['dim']}T{ANSI['reset']}{ANSI['red']}█{ANSI['reset']} "
              f"{ANSI['dim']}G{ANSI['reset']}{ANSI['yellow']}█{ANSI['reset']} "
              f"{ANSI['dim']}C{ANSI['reset']}{ANSI['blue']}█{ANSI['reset']}   "
              f"{ANSI['dim']}SPACE pause · +/- speed · m mutate · "
              f"t transcription · r regen · q quit{ANSI['reset']}")
    lines.append(legend)

    if show_transcription:
        rna = genome.to_mrna()
        protein = genome.to_protein()
        lines.append("")
        lines.append(f"{ANSI['magenta']}  mRNA (5'->3'): {ANSI['reset']}{rna[:60]}"
                     f"{'…' if len(rna) > 60 else ''}")
        prot_display = " ".join(
            f"{ANSI['cyan']}{aa}{ANSI['reset']}" for aa in protein[:30]
        )
        lines.append(f"{ANSI['cyan']}  Protein:      {ANSI['reset']}{prot_display}"
                     f"{' …' if len(protein) > 30 else ''}")
        full_names = ", ".join(AMINO_NAME.get(a, "?") for a in protein[:12])
        lines.append(f"{ANSI['dim']}  ({full_names}…){ANSI['reset']}")

    return lines


# tiny local sine/cos so we don't even need math import overhead in tight loops
import math as _math


def math_sin(x: float) -> float:
    return _math.sin(x)


def math_cos(x: float) -> float:
    return _math.cos(x)


# --------------------------------------------------------------------------- #
#  Non-blocking input (Unix)
# --------------------------------------------------------------------------- #
def set_raw(fd: int) -> None:
    import termios
    import tty
    tty.setraw(fd)


def restore_terminal(fd: int, old_flags) -> None:
    import termios
    termios.tcsetattr(fd, termios.TCSADRAIN, old_flags)


def read_key_nonblocking() -> str | None:
    """Return a single key if available, else None. Unix-only."""
    import select
    rlist, _, _ = select.select([sys.stdin], [], [], 0)
    if rlist:
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            # escape sequence — swallow the rest
            ch2 = sys.stdin.read(1) if select.select([sys.stdin], [], [], 0.01)[0] else ""
            return ch + ch2
        return ch
    return None


# --------------------------------------------------------------------------- #
#  Main animation loop
# --------------------------------------------------------------------------- #
def animate(genome: Genome, args) -> None:
    import termios

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    try:
        set_raw(fd)
        hide_cursor()
        clear_screen()

        phase = 0.0
        speed = args.speed
        paused = False
        show_transcription = args.transcribe
        last_mut = ""

        try:
            while True:
                cols, rows = shutil_termsize()

                key = read_key_nonblocking()
                if key == "q" or key == "\x03":  # q or Ctrl-C
                    break
                elif key == " ":
                    paused = not paused
                elif key == "+" or key == "=":
                    speed = min(speed + 0.3, 5.0)
                elif key == "-":
                    speed = max(speed - 0.3, 0.05)
                elif key == "m":
                    last_mut = genome.mutate()
                elif key == "t":
                    show_transcription = not show_transcription
                elif key == "r":
                    genome = random_genome(args.length)
                    last_mut = "regenerated"

                frame = helix_frame(genome, phase, cols, rows, show_transcription)
                if last_mut:
                    frame.append(f"{ANSI['yellow']}  ⟳ mutation: {last_mut}{ANSI['reset']}")
                    last_mut = ""

                move_home()
                # pad to full height to avoid trailing artefacts
                while len(frame) < rows:
                    frame.append("")
                sys.stdout.write("\n".join(frame[:rows]))
                sys.stdout.flush()

                if not paused:
                    phase += speed * 0.15
                time.sleep(0.05)
        finally:
            clear_screen()
            show_cursor()
    finally:
        restore_terminal(fd, old)


def shutil_termsize() -> tuple[int, int]:
    import shutil
    size = shutil.get_terminal_size((80, 24))
    return size.columns, size.lines


# --------------------------------------------------------------------------- #
#  Static (non-interactive) render — for --snapshot or piped output
# --------------------------------------------------------------------------- #
def static_render(genome: Genome, args) -> None:
    cols, rows = shutil_termsize()
    for step in range(args.frames):
        phase = step * 0.25
        frame = helix_frame(genome, phase, cols, rows, args.transcribe)
        move_home()
        sys.stdout.write("\n".join(frame))
        sys.stdout.flush()
        time.sleep(args.delay)
    print()


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def build_genome(args) -> Genome:
    if args.sequence:
        seq = args.sequence.upper().replace("U", "T")
        return Genome(coding=list(seq))
    return random_genome(args.length)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A rotating ASCII DNA double-helix for your terminal."
    )
    parser.add_argument("-l", "--length", type=int, default=42,
                        help="length of the random genome (default 42)")
    parser.add_argument("-s", "--sequence", type=str, default=None,
                        help="use a specific DNA sequence instead of random")
    parser.add_argument("-S", "--speed", type=float, default=1.0,
                        help="rotation speed multiplier (default 1.0)")
    parser.add_argument("-t", "--transcribe", action="store_true",
                        help="show mRNA + protein transcription overlay")
    parser.add_argument("--snapshot", action="store_true",
                        help="render N static frames then exit (no keyboard)")
    parser.add_argument("--frames", type=int, default=30,
                        help="number of frames for --snapshot (default 30)")
    parser.add_argument("--delay", type=float, default=0.1,
                        help="delay between snapshot frames (default 0.1s)")
    parser.add_argument("--protein", action="store_true",
                        help="just print the protein for the sequence and exit")
    args = parser.parse_args()

    genome = build_genome(args)

    if args.protein:
        protein = genome.to_protein()
        print(f"DNA   : {''.join(genome.coding)}")
        print(f"mRNA  : {genome.to_mrna()}")
        print(f"Protein: {protein}")
        print(f"       ({', '.join(AMINO_NAME.get(a,'?') for a in protein)})")
        return

    if args.snapshot:
        static_render(genome, args)
        return

    # interactive
    if not sys.stdin.isatty():
        # fall back to snapshot if not a tty
        static_render(genome, args)
        return

    try:
        animate(genome, args)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n{ANSI['cyan']}Thanks for watching the helix spin!{ANSI['reset']}")


if __name__ == "__main__":
    main()