# Terminal DNA Double-Helix Animator 🧬

A rotating, coloured **ASCII DNA double-helix** that lives in your terminal.
Watch base pairs connect across the strands, mutate sequences on the fly,
transcribe DNA into mRNA and proteins, and inspect sequence statistics —
all in real time, with zero dependencies.

![DNA Helix](https://img.shields.io/badge/genre-visualization-green) ![Python](https://img.shields.io/badge/python-3.8+-blue) ![No deps](https://img.shields.io/badge/dependencies-zero-orange) ![Tests](https://img.shields.io/badge/tests-29%20passing-brightgreen)

---

## ✨ Features

### Animation
- **Animated 3D-style helix** — two sinusoidal backbones twist around each
  other with depth shading (front strand bright, rear strand dimmed).
- **Colour-coded nucleotides** — A (green), T (red), G (yellow), C (blue).
- **Live mutation** — press `m` to randomly mutate a base and watch the helix
  change instantly, with a running mutation counter.
- **GC-content gauge** — toggle `g` to see a live GC/AT bar gauge in the
  status bar.
- **Transcription overlay** — toggle `t` to see the mRNA strand and the
  resulting amino-acid protein chain, with full codon → amino-acid translation.

### CLI tools
- **Custom sequences** — pass any DNA string with `-s` to render your own gene
  (accepts `U` as well as `T`).
- **Protein-only mode** — `--protein` prints the translated protein for a
  sequence without animation, with reading-frame selection (`--frame 0/1/2`).
- **Sequence statistics** — `--stats` prints base composition with ASCII bars,
  GC/AT content, approximate molecular weight, and melting temperature (Tm).
- **Reverse complement** — `--revcomp` prints the reverse complement
  (standard bioinformatics operation).
- **Complement strand** — `--complement` prints the Watson–Crick complement.
- **Snapshot mode** — `--snapshot` renders a fixed number of frames for
  non-interactive use (pipes, recordings).
- **Reproducible mode** — `--seed N` makes random genomes reproducible.
- **No-colour mode** — `--no-color` disables ANSI codes for piping / logs.
- **`--help` and `--version`** flags for standard CLI discoverability.

### Quality
- **Input validation** — invalid DNA characters are rejected with a clear
  error message.
- **Zero dependencies** — pure Python standard library, no `pip install` needed.
- **Test suite** — 29 tests / 110 assertions covering biology, edge cases,
  and CLI helpers.

---

## 🚀 Installation

No installation required — just run it with Python 3.8+.

```bash
git clone https://github.com/jayis1/daily-ideas.git
cd daily-ideas/2026-08-07-terminal-dna-helix
chmod +x dna_helix.py
```

Or simply copy `dna_helix.py` anywhere and run it.

---

## ▶️ How to Run

### Interactive animation

```bash
python3 dna_helix.py
```

### With a specific DNA sequence

```bash
python3 dna_helix.py -s ATGGCATGAACCTTTGGCCCAATAG
```

### Show transcription overlay from the start

```bash
python3 dna_helix.py -t
```

### Show GC-content gauge from the start

```bash
python3 dna_helix.py -g
```

### Reproducible random genome

```bash
python3 dna_helix.py --seed 42 -l 60
```

### Just translate a sequence to protein

```bash
python3 dna_helix.py -s ATGAAACCCTTTGGGCATTAA --protein
```

Output:
```
DNA    : ATGAAACCCTTTGGGCATTAA
mRNA   : AUGAAACCCUUUGGGCAUUAA
Protein: MKPFGH*
        (Met, Lys, Pro, Phe, Gly, His, STOP)
```

### Translate using a different reading frame

```bash
python3 dna_helix.py -s CATGAAACCCTTTGGGCATTAA --protein --frame 1
```

### Sequence statistics

```bash
python3 dna_helix.py -s ATGAAACCCTTTGGGCATTAA --stats
```

Output:
```
═══ DNA Sequence Statistics ═══

  Sequence         : ATGAAACCCTTTGGGCATTAA
  Length           : 21 bp

  Base composition:
    A     7 ( 33.3%)  ███████
    T     6 ( 28.6%)  ██████
    G     4 ( 19.0%)  ████
    C     4 ( 19.0%)  ████

  GC content       : 38.1%
  AT content       : 61.9%
  Mol. weight (ss) : ~5,252.03 Da
  Melting temp (Tm): ~48.5 °C

  mRNA             : AUGAAACCCUUUGGGCAUUAA
  Protein          : MKPFGH*
  Amino acids      : Met, Lys, Pro, Phe, Gly, His, STOP
```

### Reverse complement

```bash
python3 dna_helix.py -s ATGC --revcomp
# Output: GCAT
```

### Complement strand

```bash
python3 dna_helix.py -s ATGC --complement
# Output: TACG
```

### Snapshot (non-interactive) mode

```bash
python3 dna_helix.py --snapshot --frames 40 --delay 0.08
```

### Disable colour (for piping)

```bash
python3 dna_helix.py -s ATGAAACCCTTTGGGCATTAA --stats --no-color
```

### Run the test suite

```bash
python3 test_dna_helix.py
```

---

## 🎮 Controls (interactive mode)

| Key     | Action                          |
|---------|---------------------------------|
| `SPACE` | Pause / resume rotation         |
| `+`/`-` | Speed up / slow down            |
| `m`     | Mutate a random base            |
| `t`     | Toggle transcription overlay    |
| `g`     | Toggle GC-content gauge         |
| `r`     | Generate a new random genome    |
| `q`     | Quit                            |

---

## 🧪 What It Does

1. **Generates a genome** — a random (or user-supplied) DNA coding strand.
2. **Computes the complementary template strand** using standard base-pairing
   rules (A↔T, G↔C).
3. **Animates the helix** by plotting each base pair at a sinusoidal x-offset
   that rotates over time, creating the illusion of a spinning 3D double helix.
4. **Transcribes** the coding strand to mRNA (T→U) and **translates** it into
   a protein using the standard genetic codon table, starting from the first
   `AUG` start codon (with configurable reading frame).
5. **Mutates** individual bases on demand and immediately reflects the change
   in both the helix and (if visible) the protein.
6. **Analyses** the sequence — base composition, GC content, approximate
   molecular weight, and melting temperature.

---

## 🧬 Biology reference

- **DNA structure** — [Wikipedia](https://en.wikipedia.org/wiki/DNA)
- **Central dogma (transcription & translation)** — [Wikipedia](https://en.wikipedia.org/wiki/Central_dogma_of_molecular_biology)
- **Codon table** — [Wikipedia](https://en.wikipedia.org/wiki/DNA_codon_table)
- **Reverse complement** — [Wikipedia](https://en.wikipedia.org/wiki/Complementarity_(molecular_biology))
- **Melting temperature** — [Wikipedia](https://en.wikipedia.org/wiki/Melting_temperature)

---

## 📁 Project Structure

```
2026-08-07-terminal-dna-helix/
├── dna_helix.py       # the entire program (single file, no deps)
├── test_dna_helix.py  # test suite (29 tests, no framework needed)
└── README.md
```

---

## 📝 Version History

- **v1.1.0** — Added `--stats`, `--revcomp`, `--complement`, `--frame`,
  `--seed`, `--no-color`, `--version` flags; GC-content gauge; mutation
  counter; input validation; `g` keyboard toggle; 29-test suite; refactored
  renderer with colour abstraction.
- **v1.0.0** — Initial release: animated helix, mutation, transcription
  overlay, `--protein`, `--snapshot`.

---

Made with 💚 by a creative coding bot, one helix at a time.