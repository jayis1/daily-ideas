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
    g      toggle GC-content gauge
    q      quit

CLI modes:
    (default)          interactive animated helix
    --snapshot         render N frames then exit (non-interactive)
    --protein          print translated protein for a sequence and exit
    --stats            print sequence statistics (GC content, base counts,
                       molecular weight, melting temperature) and exit
    --revcomp          print the reverse complement of a sequence and exit
    --complement       print the complement of a sequence and exit
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field

__version__ = "1.2.0"

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

COMPLEMENT = {"A": "T", "T": "A", "G": "C", "C": "G", "U": "A"}
VALID_BASES = set("ATGCU")

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

# Average molecular weight of a DNA nucleotide (Da, per monophosphate in a strand)
# Values are approximate, used for a rough ssDNA molecular weight estimate.
NT_WEIGHT = {"A": 313.21, "T": 304.2, "G": 329.21, "C": 289.18, "U": 290.17}


# --------------------------------------------------------------------------- #
#  Genome model
# --------------------------------------------------------------------------- #
@dataclass
class Genome:
    """A double-stranded DNA sequence.

    Stores only the 5'->3' coding (sense) strand; the template strand is
    derived on demand via the ``template`` property.  Any ``U`` bases in the
    input are normalised to ``T`` so the genome always holds DNA bases.
    """
    coding: list[str] = field(default_factory=list)  # 5'->3' coding strand

    def __post_init__(self) -> None:
        """Normalise bases: uppercase and convert U -> T (DNA-only genome)."""
        self.coding = ["T" if b == "u" or b == "U" else b.upper()
                       for b in self.coding]
        # validate that every base is a known DNA/RNA nucleotide
        bad = sorted(set(self.coding) - VALID_BASES)
        if bad:
            raise ValueError(
                f"invalid bases {bad!r} in genome — only A, T, G, C, U allowed"
            )

    @property
    def template(self) -> list[str]:
        """The 3'->5' template (antisense) strand, base-paired to coding."""
        return [COMPLEMENT[b] for b in self.coding]

    @property
    def length(self) -> int:
        return len(self.coding)

    def mutate(self, index: int | None = None) -> str:
        """Mutate a single base and return a human-readable description.

        If *index* is ``None`` a random position is chosen.  The new base is
        guaranteed to differ from the original (a true substitution, not a
        silent no-op).
        """
        if not self.coding:
            return "no bases to mutate"
        if index is None:
            index = random.randrange(self.length)
        elif not (0 <= index < self.length):
            raise IndexError(
                f"mutation index {index} out of range for length {self.length}"
            )
        old = self.coding[index]
        choices = [b for b in "ATGC" if b != old]
        new = random.choice(choices)
        self.coding[index] = new
        return f"pos {index}: {old}->{new}"

    def to_mrna(self) -> str:
        """Transcribe coding strand to mRNA (T -> U)."""
        # The coding (sense) strand has the same sequence as mRNA, with T->U.
        # (The template/antisense strand is what gets complemented in vivo.)
        return "".join("U" if b == "T" else b for b in self.coding)

    def to_protein(self, frame: int = 0) -> str:
        """Translate the coding strand into a single-letter protein string.

        *frame* is the offset (0, 1, or 2) at which to begin reading codons.
        Translation starts from the first ``AUG`` start codon found at/after
        the frame offset; if none exists it starts at the offset itself.
        Stops at the first stop codon (``*``).
        """
        if frame not in (0, 1, 2):
            raise ValueError(f"frame must be 0, 1, or 2, got {frame}")
        rna = self.to_mrna()
        if len(rna) < 3:
            return ""
        start = rna.find("AUG", frame)
        if start == -1:
            start = frame
        protein = []
        # CODON_TABLE is keyed by DNA bases, so convert U->T for lookup
        _u2t = str.maketrans("U", "T")
        for i in range(start, len(rna) - 2, 3):
            codon = rna[i:i + 3]
            aa = CODON_TABLE.get(codon.translate(_u2t), "?")
            protein.append(aa)
            if aa == "*":
                break
        return "".join(protein)

    def complement(self) -> str:
        """Return the complement strand (not reversed) as a string."""
        return "".join(COMPLEMENT[b] for b in self.coding)

    def reverse_complement(self) -> str:
        """Return the reverse complement (standard bioinformatics operation)."""
        return "".join(COMPLEMENT[b] for b in reversed(self.coding))

    def gc_content(self) -> float:
        """Fraction of bases that are G or C, in [0.0, 1.0]."""
        if not self.coding:
            return 0.0
        gc = sum(1 for b in self.coding if b in "GC")
        return gc / self.length

    def base_counts(self) -> dict[str, int]:
        """Return a dict of per-base counts for A, T, G, C."""
        counts = {"A": 0, "T": 0, "G": 0, "C": 0}
        for b in self.coding:
            if b in counts:
                counts[b] += 1
        return counts

    def molecular_weight(self) -> float:
        """Approximate molecular weight of the ssDNA strand in Daltons.

        Uses average monophosphate nucleotide weights and subtracts water for
        each phosphodiester bond (n-1 * 61.96 Da).  This is a rough estimate.
        """
        if not self.coding:
            return 0.0
        total = sum(NT_WEIGHT.get(b, 300.0) for b in self.coding)
        # subtract water lost per phosphodiester bond
        total -= (self.length - 1) * 61.96
        return round(total, 2)

    def melting_temp(self) -> float:
        """Rough melting temperature (Tm) in Celsius using the Wallace rule.

        For short oligos (< 14 nt):  Tm = 2*(A+T) + 4*(G+C)
        For longer sequences: uses a simple GC%-based approximation.
        """
        n = self.length
        if n == 0:
            return 0.0
        counts = self.base_counts()
        at = counts["A"] + counts["T"]
        gc = counts["G"] + counts["C"]
        if n < 14:
            return 2 * at + 4 * gc
        # simple approximation: 64.9 + 41*(GC-16.4)/n
        return round(64.9 + 41.0 * (gc - 16.4) / n, 1)


def random_genome(length: int = 42) -> Genome:
    """Generate a random Genome of the requested length."""
    if length < 0:
        raise ValueError(f"genome length must be non-negative, got {length}")
    return Genome(coding=list(random.choice("ATGC") for _ in range(length)))


def validate_sequence(seq: str) -> str:
    """Validate and normalise a user-supplied DNA/RNA sequence.

    - Uppercases the string
    - Converts U -> T (accept RNA input too)
    - Strips *all* whitespace (including internal newlines/spaces, so that
      multi-line sequences pasted from files work correctly)
    - Raises ValueError on invalid characters
    """
    seq = "".join(seq.upper().split()).replace("U", "T")
    invalid = set(seq) - VALID_BASES
    if invalid:
        raise ValueError(
            f"invalid bases {sorted(invalid)!r} in sequence — "
            f"only A, T, G, C (or U) are allowed"
        )
    return seq


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
                show_transcription: bool, show_gc: bool,
                use_color: bool = True) -> list[str]:
    """Build a single frame of the helix as a list of string lines.

    Parameters
    ----------
    genome : Genome
        The genome to render.
    phase : float
        Current rotation phase (radians).
    cols, rows : int
        Terminal dimensions.
    show_transcription : bool
        Whether to include the mRNA/protein overlay.
    show_gc : bool
        Whether to show a GC-content gauge.
    use_color : bool
        If False, emit plain text without ANSI codes (for piping / logging).
    """
    # When colour is disabled we use a no-op decorator
    if not use_color:
        def c(code: str, text: str) -> str:
            return text
    else:
        def c(code: str, text: str) -> str:
            return f"{code}{text}{ANSI['reset']}"

    # guard against absurd terminal sizes (must happen before half_w is used)
    if cols < 1:
        cols = 1
    if rows < 1:
        rows = 1

    half_w = cols // 2
    overlay_lines = 8 if show_transcription else 4
    if show_gc:
        overlay_lines += 1
    visible = min(genome.length, rows - overlay_lines)
    # never render more bases than the genome actually has, and never claim a
    # minimum of 4 when the genome is shorter than that (avoids IndexError).
    visible = max(0, min(visible, genome.length))

    lines: list[str] = []

    # ---- Title bar -------------------------------------------------------- #
    title = f"  {c(ANSI['bold'] + ANSI['cyan'], '╔══ DNA DOUBLE HELIX ══╗')}"
    lines.append(title)
    info = (f"  length={genome.length}  "
            f"phase={phase % 6.283:.2f}  bases shown={visible}")
    if show_gc:
        gc = genome.gc_content()
        bar_len = 20
        filled = int(round(gc * bar_len))
        bar = "█" * filled + "░" * (bar_len - filled)
        info += f"  GC={c(ANSI['yellow'], bar)} {gc:.1%}"
    lines.append(c(ANSI['dim'], info))

    # ---- Helix body ------------------------------------------------------- #
    for i in range(visible):
        base = genome.coding[i]
        comp = COMPLEMENT[base]

        # sinusoidal horizontal offset for the two backbones
        angle = phase + i * 0.45
        left_x = int(round(half_w + math.sin(angle) * (half_w - 6)))
        right_x = int(round(half_w + math.sin(angle + math.pi) * (half_w - 6)))

        # clamp backbone positions to the terminal width
        left_x = max(0, min(cols - 1, left_x))
        right_x = max(0, min(cols - 1, right_x))

        # depth: which strand is in front?
        depth_l = math.cos(angle)
        front_is_left = depth_l >= 0

        # build the line as a list of chars, then colourise
        line = [" "] * cols
        line[left_x] = "║"
        line[right_x] = "║"

        # connect base pairs between the two strands
        lo, hi = sorted((left_x, right_x))
        mid = (lo + hi) // 2
        if hi - lo > 2:
            for x in range(lo + 1, hi):
                line[x] = "·"
        # place the letters near the midpoint (guard against running off the row)
        if hi - lo >= 4:
            if 0 <= mid - 1 < cols:
                line[mid - 1] = base
            if 0 <= mid + 1 < cols:
                line[mid + 1] = comp

        # colourise
        coloured = []
        for x, ch in enumerate(line):
            if ch == "║":
                if (x == left_x and front_is_left) or (x == right_x and not front_is_left):
                    coloured.append(c(ANSI['white'] + ANSI['bold'], "║"))
                else:
                    coloured.append(c(ANSI['dim'], "║"))
            elif ch in BASE_COLOR:
                coloured.append(c(BASE_COLOR[ch], ch))
            elif ch == "·":
                coloured.append(c(ANSI['dim'], "·"))
            else:
                coloured.append(ch)
        lines.append("".join(coloured))

    # ---- Legend / transcription ------------------------------------------ #
    legend = (f"  {c(ANSI['dim'], 'A')}{c(ANSI['green'], '█')} "
              f"{c(ANSI['dim'], 'T')}{c(ANSI['red'], '█')} "
              f"{c(ANSI['dim'], 'G')}{c(ANSI['yellow'], '█')} "
              f"{c(ANSI['dim'], 'C')}{c(ANSI['blue'], '█')}   "
              + c(ANSI['dim'], 'SPACE pause · +/- speed · m mutate · '
                  't transcription · g GC gauge · r regen · q quit'))
    lines.append(legend)

    if show_transcription:
        rna = genome.to_mrna()
        protein = genome.to_protein()
        lines.append("")
        mrna_label = "mRNA (5'->3'):"
        lines.append(f"  {c(ANSI['magenta'], mrna_label)} {rna[:60]}"
                     f"{'…' if len(rna) > 60 else ''}")
        prot_display = " ".join(
            c(ANSI['cyan'], aa) for aa in protein[:30]
        )
        lines.append(f"  {c(ANSI['cyan'], 'Protein:      ')} {prot_display}"
                     f"{' …' if len(protein) > 30 else ''}")
        full_names = ", ".join(AMINO_NAME.get(a, "?") for a in protein[:12])
        lines.append(f"  {c(ANSI['dim'], '(' + full_names + '…)')}")

    return lines


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
    """Run the interactive animation loop until the user quits."""
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
        show_gc = args.gc
        last_mut = ""
        mut_count = 0

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
                    mut_count += 1
                elif key == "t":
                    show_transcription = not show_transcription
                elif key == "g":
                    show_gc = not show_gc
                elif key == "r":
                    genome = random_genome(args.length)
                    last_mut = "regenerated"
                    mut_count = 0

                frame = helix_frame(genome, phase, cols, rows,
                                    show_transcription, show_gc, args.color)
                if last_mut:
                    frame.append(f"  {c_if(args.color, ANSI['yellow'], '')}⟳ mutation: {last_mut}  (total: {mut_count}){c_if(args.color, ANSI['reset'], '')}")
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


def c_if(use_color: bool, code: str, text: str) -> str:
    """Wrap *text* in *code* only if colour is enabled."""
    if use_color:
        return f"{code}{text}{ANSI['reset']}"
    return text


def shutil_termsize() -> tuple[int, int]:
    import shutil
    size = shutil.get_terminal_size((80, 24))
    return size.columns, size.lines


# --------------------------------------------------------------------------- #
#  Static (non-interactive) render — for --snapshot or piped output
# --------------------------------------------------------------------------- #
def static_render(genome: Genome, args) -> None:
    """Render *args.frames* static frames without keyboard interaction."""
    cols, rows = shutil_termsize()
    for step in range(args.frames):
        phase = step * 0.25
        frame = helix_frame(genome, phase, cols, rows, args.transcribe,
                            args.gc, args.color)
        move_home()
        sys.stdout.write("\n".join(frame))
        sys.stdout.flush()
        time.sleep(args.delay)
    print()


# --------------------------------------------------------------------------- #
#  Stats mode
# --------------------------------------------------------------------------- #
def print_stats(genome: Genome, use_color: bool = True) -> None:
    """Print a detailed statistics report for the genome."""
    n = genome.length
    counts = genome.base_counts()
    gc = genome.gc_content()

    def w(code: str, text: str) -> str:
        return c_if(use_color, code, text)

    print(w(ANSI['bold'] + ANSI['cyan'], "═══ DNA Sequence Statistics ═══"))
    print()
    print(f"  Sequence         : {''.join(genome.coding[:50])}"
          f"{'…' if n > 50 else ''}")
    print(f"  Length           : {n} bp")
    print()
    print(w(ANSI['bold'], "  Base composition:"))
    for b in "ATGC":
        cnt = counts[b]
        pct = (cnt / n * 100) if n else 0.0
        bar = "█" * int(round(pct / 5))  # each block = 5%
        print(f"    {w(BASE_COLOR[b], b)} "
              f"{cnt:>5} ({pct:5.1f}%)  {w(ANSI['dim'], bar)}")
    print()
    print(f"  GC content       : {w(ANSI['yellow'], f'{gc:.1%}')}")
    print(f"  AT content       : {w(ANSI['green'], f'{1 - gc:.1%}')}")
    print(f"  Mol. weight (ss) : ~{genome.molecular_weight():,.2f} Da")
    print(f"  Melting temp (Tm): ~{genome.melting_temp()} °C")
    print()
    mrna = genome.to_mrna()
    protein = genome.to_protein()
    print(f"  mRNA             : {mrna[:50]}{'…' if len(mrna) > 50 else ''}")
    print(f"  Protein          : {protein[:50]}{'…' if len(protein) > 50 else ''}")
    if protein:
        names = ", ".join(AMINO_NAME.get(a, "?") for a in protein)
        print(f"  Amino acids      : {names}")
    print()


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def build_genome(args) -> Genome:
    """Construct a Genome from CLI arguments (sequence or random)."""
    if args.sequence is not None:
        seq = validate_sequence(args.sequence)
        if not seq:
            raise ValueError("sequence is empty after normalisation")
        return Genome(coding=list(seq))
    return random_genome(args.length)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="A rotating ASCII DNA double-helix for your terminal."
    )
    parser.add_argument("--version", action="version",
                        version=f"dna-helix {__version__}")
    parser.add_argument("-l", "--length", type=int, default=42,
                        help="length of the random genome (default 42)")
    parser.add_argument("-s", "--sequence", type=str, default=None,
                        help="use a specific DNA sequence instead of random "
                             "(accepts A, T, G, C, U)")
    parser.add_argument("-S", "--speed", type=float, default=1.0,
                        help="rotation speed multiplier (default 1.0)")
    parser.add_argument("-t", "--transcribe", action="store_true",
                        help="show mRNA + protein transcription overlay")
    parser.add_argument("-g", "--gc", action="store_true",
                        help="show GC-content gauge")
    parser.add_argument("--snapshot", action="store_true",
                        help="render N static frames then exit (no keyboard)")
    parser.add_argument("--frames", type=int, default=30,
                        help="number of frames for --snapshot (default 30)")
    parser.add_argument("--delay", type=float, default=0.1,
                        help="delay between snapshot frames (default 0.1s)")
    parser.add_argument("--protein", action="store_true",
                        help="just print the protein for the sequence and exit")
    parser.add_argument("--frame", type=int, default=0, choices=[0, 1, 2],
                        help="reading frame for translation (0, 1, or 2; "
                             "default 0)")
    parser.add_argument("--stats", action="store_true",
                        help="print sequence statistics and exit")
    parser.add_argument("--revcomp", action="store_true",
                        help="print the reverse complement and exit")
    parser.add_argument("--complement", action="store_true",
                        help="print the complement strand and exit")
    parser.add_argument("--seed", type=int, default=None,
                        help="random seed for reproducible genomes")
    parser.add_argument("--no-color", dest="color", action="store_false",
                        help="disable ANSI colour codes (for piping / logs)")
    parser.set_defaults(color=True)
    args = parser.parse_args()

    # ---- Validate numeric arguments -------------------------------------- #
    if args.frames < 0:
        print("error: --frames must be >= 0", file=sys.stderr)
        sys.exit(2)
    if args.delay < 0:
        print("error: --delay must be >= 0", file=sys.stderr)
        sys.exit(2)
    if args.speed < 0:
        print("error: --speed must be >= 0", file=sys.stderr)
        sys.exit(2)
    if args.length < 0:
        print("error: --length must be >= 0", file=sys.stderr)
        sys.exit(2)

    # ---- Warn about mutually-exclusive modes ----------------------------- #
    exclusive = [("--revcomp", args.revcomp),
                 ("--complement", args.complement),
                 ("--stats", args.stats),
                 ("--protein", args.protein)]
    chosen = [name for name, flag in exclusive if flag]
    if len(chosen) > 1:
        print(f"warning: multiple output modes specified ({', '.join(chosen)}); "
              f"only the first ({chosen[0]}) will be used.", file=sys.stderr)

    # Seed early so random_genome is reproducible
    if args.seed is not None:
        random.seed(args.seed)

    try:
        genome = build_genome(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)

    # ---- Subcommand: reverse complement ---------------------------------- #
    if args.revcomp:
        print(genome.reverse_complement())
        return

    # ---- Subcommand: complement ------------------------------------------ #
    if args.complement:
        print(genome.complement())
        return

    # ---- Subcommand: stats ----------------------------------------------- #
    if args.stats:
        print_stats(genome, use_color=args.color)
        return

    # ---- Subcommand: protein --------------------------------------------- #
    if args.protein:
        protein = genome.to_protein(frame=args.frame)
        print(f"DNA    : {''.join(genome.coding)}")
        print(f"mRNA   : {genome.to_mrna()}")
        print(f"Protein: {protein}")
        if protein:
            print(f"        ({', '.join(AMINO_NAME.get(a, '?') for a in protein)})")
        else:
            print("        (no start codon found; empty translation)")
        return

    # ---- Subcommand: snapshot -------------------------------------------- #
    if args.snapshot:
        static_render(genome, args)
        return

    # ---- Interactive (or fallback) --------------------------------------- #
    if not sys.stdin.isatty():
        # fall back to snapshot if not a tty
        static_render(genome, args)
        return

    try:
        animate(genome, args)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n{c_if(args.color, ANSI['cyan'], '')}"
              f"Thanks for watching the helix spin!{c_if(args.color, ANSI['reset'], '')}")


if __name__ == "__main__":
    main()