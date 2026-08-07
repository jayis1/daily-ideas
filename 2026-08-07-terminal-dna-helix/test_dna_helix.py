#!/usr/bin/env python3
"""Tests for the Terminal DNA Double-Helix Animator.

Run with:  python3 test_dna_helix.py
No external test framework required — uses a tiny built-in runner.
"""

import os
import sys
import random

sys.path.insert(0, os.path.dirname(__file__))

from dna_helix import (
    Genome,
    random_genome,
    validate_sequence,
    COMPLEMENT,
    CODON_TABLE,
    AMINO_NAME,
    __version__,
)


# ── Tiny test runner ──────────────────────────────────────────────────────────

_passed = 0
_failed = 0
_failures: list[str] = []


def check(condition: bool, label: str) -> None:
    global _passed, _failed
    if condition:
        _passed += 1
    else:
        _failed += 1
        _failures.append(label)
        print(f"  FAIL: {label}")


def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) < tol


# ── Genome / biology tests ────────────────────────────────────────────────────

def test_complement():
    """Complement strand should follow A<->T, G<->C pairing."""
    g = Genome(coding=list("ATGCATGC"))
    check(g.complement() == "TACGTACG", "complement of ATGCATGC == TACGTACG")
    check(g.template == list("TACGTACG"), "template property matches complement")


def test_reverse_complement():
    """Reverse complement: reverse then complement (standard bioinformatics)."""
    g = Genome(coding=list("ATGC"))
    check(g.reverse_complement() == "GCAT", "revcomp of ATGC == GCAT")
    g2 = Genome(coding=list("AAAACCCCC"))
    check(g2.reverse_complement() == "GGGGGTTTT", "revcomp of AAAACCCCC")


def test_mrna_transcription():
    """mRNA should be coding strand with T replaced by U."""
    g = Genome(coding=list("ATGCATGC"))
    check(g.to_mrna() == "AUGCAUGC", "mRNA transcription T->U")


def test_protein_translation():
    """Full translation: ATG start, stop at stop codon."""
    # ATG AAA CCC TTT GGG CAT TAA -> M K P F G H *
    g = Genome(coding=list("ATGAAACCCTTTGGGCATTAA"))
    check(g.to_protein() == "MKPFGH*", "protein translation with stop")


def test_protein_no_start_codon():
    """If no AUG start codon, translation starts at frame offset."""
    # Ccc Ccc -> P P (no AUG, starts at offset 0)
    g = Genome(coding=list("CCCCCC"))
    check(g.to_protein() == "PP", "no start codon -> translate from offset")


def test_reading_frame():
    """Different reading frames should yield different proteins."""
    # Frame 0: CAT GAA ACC ... -> H E T ...
    # Frame 1: A TGA AAC ... -> start at AUG found later
    seq = "CATGAAACCCTTTGGGCATTAA"
    g = Genome(coding=list(seq))
    p0 = g.to_protein(frame=0)
    # With frame=1 the first AUG is at index 2 (0-based from mRNA), but
    # to_protein searches for AUG starting at *frame* offset in the mRNA.
    # mRNA = CAUGAAACCCUUUGGGCAUUAA
    # frame=1 -> search "AUG" from index 1 -> found at index 2
    # so translation still starts at AUG -> MKPFGH*
    p1 = g.to_protein(frame=1)
    check(p0 == "MKPFGH*", f"frame 0 protein is MKPFGH*, got {p0}")
    check(p1 == "MKPFGH*", f"frame 1 finds same AUG -> MKPFGH*, got {p1}")


def test_empty_genome():
    """Edge case: empty genome should not crash."""
    g = Genome(coding=[])
    check(g.length == 0, "empty genome length 0")
    check(g.to_mrna() == "", "empty genome mRNA empty")
    check(g.to_protein() == "", "empty genome protein empty")
    check(g.gc_content() == 0.0, "empty genome GC content 0.0")
    check(g.complement() == "", "empty genome complement empty")
    check(g.reverse_complement() == "", "empty genome revcomp empty")
    check(g.molecular_weight() == 0.0, "empty genome MW 0.0")
    check(g.melting_temp() == 0.0, "empty genome Tm 0.0")
    check(g.mutate() == "no bases to mutate", "empty genome mutate message")


def test_mutate_changes_base():
    """Mutation must change the base to a different nucleotide."""
    random.seed(123)
    g = Genome(coding=list("AAAAAAAAAA"))
    original = "".join(g.coding)
    desc = g.mutate(index=0)
    check(g.coding[0] != "A", "mutated base differs from original")
    check("pos 0:" in desc, "mutation description includes position")


def test_mutate_index_out_of_range():
    """Mutating an out-of-range index should raise IndexError."""
    g = Genome(coding=list("ATGC"))
    try:
        g.mutate(index=10)
        check(False, "mutate out of range should raise IndexError")
    except IndexError:
        check(True, "mutate out of range raises IndexError")


def test_mutate_all_positions():
    """Every base in a long genome should be mutable without error."""
    random.seed(42)
    g = random_genome(100)
    for i in range(100):
        g.mutate(index=i)
    check(g.length == 100, "genome length unchanged after mutations")


def test_gc_content():
    """GC content is the fraction of G and C bases."""
    g = Genome(coding=list("GGCC"))  # 100% GC
    check(approx(g.gc_content(), 1.0), "GGCC GC content == 1.0")
    g2 = Genome(coding=list("AATT"))  # 0% GC
    check(approx(g2.gc_content(), 0.0), "AATT GC content == 0.0")
    g3 = Genome(coding=list("ATGC"))  # 50% GC
    check(approx(g3.gc_content(), 0.5), "ATGC GC content == 0.5")


def test_base_counts():
    """base_counts returns correct per-base tallies."""
    g = Genome(coding=list("AATTTGGGCCC"))
    counts = g.base_counts()
    check(counts == {"A": 2, "T": 3, "G": 3, "C": 3}, "base counts correct")


def test_molecular_weight():
    """Molecular weight should be positive for non-empty sequences."""
    g = Genome(coding=list("ATGC"))
    mw = g.molecular_weight()
    check(mw > 0, f"molecular weight positive, got {mw}")


def test_melting_temp_short():
    """Wallace rule for short sequences: Tm = 2*(A+T) + 4*(G+C)."""
    g = Genome(coding=list("ATGC"))  # 2*2 + 4*2 = 12
    check(g.melting_temp() == 12, "Wallace Tm for ATGC == 12")


def test_melting_temp_empty():
    """Empty sequence Tm should be 0."""
    g = Genome(coding=[])
    check(g.melting_temp() == 0.0, "empty sequence Tm == 0")


# ── Random genome tests ───────────────────────────────────────────────────────

def test_random_genome_length():
    """random_genome produces a genome of the requested length."""
    random.seed(7)
    g = random_genome(50)
    check(g.length == 50, "random_genome(50) length == 50")
    # all bases valid
    check(all(b in "ATGC" for b in g.coding), "random genome bases are ATGC")


def test_random_genome_reproducible():
    """Same seed produces same genome."""
    random.seed(99)
    g1 = random_genome(20)
    random.seed(99)
    g2 = random_genome(20)
    check(g1.coding == g2.coding, "same seed -> same genome")


def test_random_genome_zero():
    """random_genome(0) produces an empty genome."""
    g = random_genome(0)
    check(g.length == 0, "random_genome(0) is empty")


def test_random_genome_negative():
    """random_genome(-1) should raise ValueError."""
    try:
        random_genome(-1)
        check(False, "random_genome(-1) should raise ValueError")
    except ValueError:
        check(True, "random_genome(-1) raises ValueError")


# ── validate_sequence tests ───────────────────────────────────────────────────

def test_validate_normal():
    """Normal DNA sequence passes validation."""
    check(validate_sequence("ATGC") == "ATGC", "validate ATGC")


def test_validate_lowercase():
    """Lowercase input is uppercased."""
    check(validate_sequence("atgc") == "ATGC", "lowercase -> uppercase")


def test_validate_rna():
    """U is converted to T."""
    check(validate_sequence("AUGC") == "ATGC", "U -> T conversion")


def test_validate_whitespace():
    """Whitespace is stripped."""
    check(validate_sequence("  ATGC  ") == "ATGC", "whitespace stripped")


def test_validate_invalid():
    """Invalid characters raise ValueError."""
    try:
        validate_sequence("ATGCXYZ")
        check(False, "invalid bases should raise ValueError")
    except ValueError:
        check(True, "invalid bases raise ValueError")


def test_validate_empty():
    """Empty string validates to empty (genome build catches it)."""
    check(validate_sequence("") == "", "empty string validates to empty")


# ── Codon table integrity ─────────────────────────────────────────────────────

def test_codon_table_completeness():
    """All 64 codons should be present in the codon table."""
    check(len(CODON_TABLE) == 64, f"codon table has 64 entries, got {len(CODON_TABLE)}")
    for a in "ATGC":
        for b in "ATGC":
            for c in "ATGC":
                codon = a + b + c
                check(codon in CODON_TABLE, f"codon {codon} in table")


def test_stop_codons():
    """The three standard stop codons map to '*'."""
    check(CODON_TABLE["TAA"] == "*", "TAA -> *")
    check(CODON_TABLE["TAG"] == "*", "TAG -> *")
    check(CODON_TABLE["TGA"] == "*", "TGA -> *")


def test_start_codon():
    """ATG (Methionine) is the start codon."""
    check(CODON_TABLE["ATG"] == "M", "ATG -> M")


# ── Version ───────────────────────────────────────────────────────────────────

def test_version():
    """Version string should be defined and non-empty."""
    check(isinstance(__version__, str) and len(__version__) > 0, "version is non-empty string")


# ── Run all tests ─────────────────────────────────────────────────────────────

def main() -> int:
    tests = [
        test_complement,
        test_reverse_complement,
        test_mrna_transcription,
        test_protein_translation,
        test_protein_no_start_codon,
        test_reading_frame,
        test_empty_genome,
        test_mutate_changes_base,
        test_mutate_index_out_of_range,
        test_mutate_all_positions,
        test_gc_content,
        test_base_counts,
        test_molecular_weight,
        test_melting_temp_short,
        test_melting_temp_empty,
        test_random_genome_length,
        test_random_genome_reproducible,
        test_random_genome_zero,
        test_random_genome_negative,
        test_validate_normal,
        test_validate_lowercase,
        test_validate_rna,
        test_validate_whitespace,
        test_validate_invalid,
        test_validate_empty,
        test_codon_table_completeness,
        test_stop_codons,
        test_start_codon,
        test_version,
    ]

    print(f"Running {len(tests)} tests for dna_helix v{__version__}...\n")
    for test in tests:
        try:
            test()
        except Exception as exc:
            global _failed
            _failed += 1
            _failures.append(f"{test.__name__}: {exc}")
            print(f"  ERROR in {test.__name__}: {exc}")

    print(f"\n{'=' * 50}")
    print(f"  Passed: {_passed}   Failed: {_failed}")
    if _failures:
        print("\n  Failures:")
        for f in _failures:
            print(f"    - {f}")
    print(f"{'=' * 50}")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())