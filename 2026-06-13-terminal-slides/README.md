# Terminal Slides 🎤🖥️

A presentation tool that runs entirely in your terminal. Write your slides in Markdown, present them with beautiful ANSI colors and keyboard navigation — no GUI required.

## Features

- **Markdown-based slides** — Separate slides with `---`, use standard Markdown syntax
- **Rich formatting** — Headers, bold, italic, inline code, code blocks, blockquotes, ordered/unordered lists
- **3 built-in themes** — Dark, Light, and Monochrome
- **Interactive navigation** — Arrow keys, vim keys (j/k), space bar, jump to first/last
- **Auto-play mode** — Timed slide advancement for unattended presentations
- **Progress bar** — Visual slide progress at the bottom of each slide
- **Code blocks** — Language-labeled with box-drawing borders
- **Alternate screen buffer** — Your terminal history is preserved after exiting
- **Export to text** — Dump slides to plain text (strips ANSI codes)
- **Zero dependencies** — Pure Python 3, no external packages needed
- **SSH-friendly** — Present remotely over any terminal connection

## Installation

No installation needed beyond Python 3.6+:

```bash
# Just download and run
chmod +x slides.py
./slides.py demo
```

Or clone this repo:

```bash
git clone <repo-url>
cd terminal-slides
python3 slides.py demo
```

## How to Run

### Built-in Demo

```bash
python3 slides.py --demo
```

### Your Own Presentation

```bash
python3 slides.py presentation.md
```

### With a Specific Theme

```bash
python3 slides.py presentation.md --theme light
python3 slides.py presentation.md --theme monochrome
```

### Auto-play Mode

Advance slides automatically every 5 seconds:

```bash
python3 slides.py presentation.md --auto 5
```

### Export to Plain Text

```bash
python3 slides.py presentation.md --export output.txt
```

## Usage Examples

### Writing Slides

Create a Markdown file with slides separated by `---`:

```markdown
# My Presentation

A subtitle goes here

---

## Slide Two

* Point one
* Point two
* **Bold text** and *italic text*

---

## Code Example

```python
def hello():
    print("Hello, World!")
```

> A wise quote goes here

---

# Thank You!

Questions?
```

### Supported Markdown Syntax

| Syntax | Result |
|--------|--------|
| `# Heading` | Centered title slide |
| `## Heading` | Section heading |
| `### Heading` | Sub-section heading |
| `**bold**` | Bold colored text |
| `*italic*` | Italic colored text |
| `` `code` `` | Inline code highlight |
| ` ```lang ` code blocks | Boxed code with language label |
| `> quote` | Blockquote with side bar |
| `- item` | Unordered list |
| `1. item` | Ordered list |
| `---` | Slide separator |

### Keyboard Controls

| Key | Action |
|-----|--------|
| `→` / `Space` / `Enter` / `j` | Next slide |
| `←` / `h` | Previous slide |
| `g` | First slide |
| `G` | Last slide |
| `q` / `Ctrl+C` | Quit |

## How It Works

1. **Parsing**: The `SlideParser` reads Markdown text, splits on `---` separators, and converts each slide into a list of semantic elements (headings, lists, code blocks, etc.)

2. **Theming**: Three built-in color themes map each element type (title, body, code, quote, etc.) to ANSI color + style combinations

3. **Rendering**: The `Renderer` converts each slide's element list into ANSI-decorated strings, centering title slides and drawing box-drawing characters around code blocks

4. **Presentation**: The `Presenter` uses the alternate screen buffer and raw terminal input to create an interactive slide-show experience without any curses dependency

## File Structure

```
terminal-slides/
├── slides.py    # The complete presentation tool (single file)
├── sample.md    # Example presentation
└── README.md    # This file
```

## License

MIT