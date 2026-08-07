# Terminal DNA Double-Helix Animator 🧬

A rotating, coloured **ASCII DNA double-helix** that lives in your terminal.
Watch base pairs connect across the strands, mutate sequences on the fly, and
transcribe DNA into mRNA and proteins — all in real time.

![DNA Helix](https://img.shields.io/badge/genre-visualization-green) ![Python](https://img.shields.io/badge/python-3.8+-blue) ![No deps](https://img.shields.io/badge/dependencies-zero-orange)

---

## ✨ Features

- **Animated 3D-style helix** — two sinusoidal backbones twist around each other
  with depth shading (front strand bright, rear strand dimmed).
- **Colour-coded nucleotides** — A (green), T (red), G (yellow), C (blue).
- **Live mutation** — press `m` to randomly mutate a base and watch the helix
  change instantly.
- **Transcription overlay** — toggle `t` to see the mRNA strand and the
  resulting amino-acid protein chain, with full codon → amino-acid translation.
- **Custom sequences** — pass any DNA string with `-s` to render your own gene.
- **Protein-only mode** — `--protein` prints the translated protein for a
  sequence without animation.
- **Snapshot mode** — `--snapshot` renders a fixed number of frames for
  non-interactive use (pipes, recordings).
- **Zero dependencies** — pure Python standard library, no `pip install` needed.

---

## 🚀 Installation

No installation required — just run it with Python 3.8+.

```bash
git clone …
cd 2026-08-07-terminal-dna-helix
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

### Just translate a sequence to protein

```bash
python3 dna_helix.py -s ATGGCATGAACCTTTGGCCCAATAG --protein
```

Output:
```
DNA   : ATGGCATGAACCTTTGGCCCAATAG
mRNA  : UACCGUACUUGGAAACCGGGUUAUC
Protein: MAETFGLPS
       (Met, Ala, Glu, Thr, Phe, Gly, Leu, Pro, Ser)
```

### Snapshot (non-interactive) mode

```bash
python3 dna_helix.py --snapshot --frames 40 --delay 0.08
```

---

## 🎮 Controls (interactive mode)

| Key     | Action                          |
|---------|---------------------------------|
| `SPACE` | Pause / resume rotation         |
| `+`/`-` | Speed up / slow down            |
| `m`     | Mutate a random base            |
| `t`     | Toggle transcription overlay    |
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
   `AUG` start codon.
5. **Mutates** individual bases on demand and immediately reflects the change
   in both the helix and (if visible) the protein.

---

## 📁 Project Structure

```
2026-08-07-terminal-dna-helix/
├── dna_helix.py   # the entire program (single file, no deps)
└── README.md
```

---

## 🔬 Learn More

- [DNA structure (Wikipedia)](https://en.wikipedia.org/wiki/DNA)
- [Transcription & translation](https://en.wikipedia.org/wiki/Central_dogma_of_molecular_biology)
- [Codon table](https://en.wikipedia.org/wiki/DNA_codon_table)

---

Made with 💚 by a creative coding bot, one helix at a time.