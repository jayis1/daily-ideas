# Terminal Spreadsheet

A fully interactive, curses-based mini spreadsheet that runs right in your terminal. Edit cells, write formulas, reference other cells, and use built-in functions — all with a keyboard-driven interface inspired by Vim and traditional spreadsheet apps.

## Features

### Core
- **Interactive TUI** — Full-screen curses interface with cell grid, status bar, and help line
- **Cell navigation** — Arrow keys or hjkl to move between cells
- **Formula engine** — Write expressions starting with `=` (e.g., `=A1+B2*3`)
- **Cell references** — Refer to any cell by its coordinate (A1 through Z100)
- **Live recalculation** — Changing a cell instantly updates all dependents

### Arithmetic & Operators
- `+`, `-`, `*`, `/` — basic math
- `^` — exponentiation (right-associative)
- `%` — modulo
- `==`, `!=`, `<`, `<=`, `>`, `>=` — comparison operators (return 1 or 0)

### Built-in Functions
| Function | Description |
|----------|-------------|
| `SUM(range)` | Sum of values in range |
| `AVG(range)` | Average of values in range |
| `MEDIAN(range)` | Median of values in range |
| `STDEV(range)` | Sample standard deviation |
| `MIN(range)` | Minimum value in range |
| `MAX(range)` | Maximum value in range |
| `COUNT(range)` | Count of numeric values in range |
| `ABS(val)` | Absolute value |
| `INT(val)` | Integer part |
| `ROUND(val)` / `ROUND(val, digits)` | Round to nearest integer or N digits |
| `SQRT(val)` | Square root |
| `IF(cond, true_val, false_val)` | Conditional |
| `CONCAT(val1, val2, ...)` | Concatenate values as strings |

### Editing
- **Yank/Paste** — Copy cell contents with `y`, paste with `p`
- **Undo/Redo** — Press `u` to undo, `Ctrl+R` to redo (up to 50 levels)
- **Search** — Press `/` to search cell contents, `n` to find next match
- **Command mode** — Press `:` for commands

### Data I/O
- **CSV Export** — `:save filename.csv` writes the sheet to a CSV file
- **CSV Import** — `:load filename.csv` reads a CSV file into the sheet
- **CLI flag** — `--load file.csv` starts with a pre-loaded CSV

### Extras
- **`--help` and `--version`** flags on the command line
- **Transitive circular reference detection** — catches A1→B1→A1 cycles
- **String literals** — use `"hello"` in formulas for text concatenation
- **Sample data** — Ships with a pre-loaded budget spreadsheet so you can explore immediately
- **Zero dependencies** — Uses only the Python standard library (curses)

## How to Install

No installation required beyond Python 3.6+. Just clone and run:

```bash
git clone <repo-url>
cd terminal-spreadsheet
python3 spreadsheet.py
```

> **Note:** On some Linux systems, you may need the curses library:
> ```bash
> sudo apt-get install libncurses5-dev  # Debian/Ubuntu
> ```

## How to Run

```bash
# Start the interactive spreadsheet
python3 spreadsheet.py

# Start with a pre-loaded CSV file
python3 spreadsheet.py --load my_data.csv

# Show version
python3 spreadsheet.py --version

# Show help
python3 spreadsheet.py --help
```

## Key Bindings

| Key | Mode | Action |
|-----|------|--------|
| `↑↓←→` / `hjkl` | NAV | Move cursor |
| `e` / `Enter` | NAV | Edit current cell (with content) |
| `i` | NAV | Insert (edit with empty buffer) |
| `x` / `Del` / `Backspace` | NAV | Delete current cell |
| `y` | NAV | Yank (copy) current cell |
| `p` | NAV | Paste yanked cell |
| `u` | NAV | Undo last change |
| `/` | NAV | Search cells |
| `n` | NAV | Find next search match |
| `:` | NAV | Enter command mode |
| `q` | NAV | Quit |
| `?` / `H` | NAV | Show help |
| `Enter` | EDIT | Confirm and move down |
| `Tab` | EDIT | Confirm and move right |
| `Escape` | EDIT | Cancel edit |
| `Backspace` | EDIT | Delete last character |
| `Enter` | CMD | Execute command |
| `Escape` | CMD | Cancel command |

## Commands

| Command | Description |
|---------|-------------|
| `:q` / `:quit` | Quit the spreadsheet |
| `:h` / `:help` | Show help |
| `:clear` | Clear the entire sheet |
| `:goto C5` | Jump cursor to cell C5 |
| `:width 14` | Set column display width (4–30) |
| `:save data.csv` | Save sheet to a CSV file |
| `:load data.csv` | Load a CSV file into the sheet |
| `:version` | Show version number |

## Usage Examples

### Simple arithmetic
Type into a cell:
```
=2+3*4
```
Result: `14`

### Cell references
Set A1 to `10`, A2 to `20`, then in A3:
```
=A1+A2
```
Result: `30`

### Range functions
Fill B1–B5 with numbers, then in B6:
```
=SUM(B1:B5)
```
Result: sum of all five cells.

### Comparison operators
```
=A1>100
```
Returns `1` (true) if A1 is greater than 100, otherwise `0`.

### Conditional IF
```
=IF(A1>100, A1, 0)
```
Returns A1 if it's greater than 100, otherwise 0.

### MEDIAN and STDEV
```
=MEDIAN(B1:B10)
=STDEV(B1:B10)
```
Returns the median / sample standard deviation of the range.

### String concatenation
```
=CONCAT("Hello", " ", A1)
```
Joins strings and cell values together.

### Nested expressions
```
=(A1+A2)*2
```

### Square root
```
=SQRT(144)
```
Result: `12`

### Saving and loading
```
:save budget.csv
:load budget.csv
```

## Sample Data

The spreadsheet launches with a pre-loaded budget tracker:

| | A | B | C | D | E |
|---|---|---|---|---|---|
| **1** | Item | Jan | Feb | Mar | Total |
| **2** | Rent | 1200 | 1200 | 1200 | `=SUM(B2:D2)` |
| **3** | Food | 450 | 520 | 380 | `=SUM(B3:D3)` |
| **4** | Transport | 200 | 180 | 220 | `=SUM(B4:D4)` |
| **5** | Fun | 150 | 200 | 170 | `=SUM(B5:D5)` |
| **6** | Total | `=SUM(B2:B5)` | ... | ... | `=SUM(E2:E5)` |
| **8** | Average | `=AVG(B2:B5)` | ... | ... | |
| **9** | Median | `=MEDIAN(B2:B5)` | ... | ... | |

You can modify any cell and see the formulas recalculate live.

## Architecture

- **`Spreadsheet` class** — Stores raw cell contents, evaluates formulas on demand, caches results, invalidates caches when cells change. Supports undo/redo, CSV I/O, and search.
- **Formula parser** — A recursive descent parser that handles operator precedence (comparison → add/sub → mul/div/mod → power → unary → primary), parenthesized expressions, cell references, string literals, and function calls with range or expression arguments.
- **`SpreadsheetUI` class** — Curses-based rendering engine that manages the grid viewport, cursor position, scrolling, and four input modes (NAV, EDIT, COMMAND, SEARCH).

## Running Tests

```bash
python3 test_spreadsheet.py
```

Runs 30+ unit tests covering cell helpers, arithmetic formulas, cell references, SUM/AVG/MIN/MAX/COUNT/MEDIAN/STDEV functions, multi-column ranges, nested formulas, deletion, circular references (direct and transitive), division by zero, live recalculation, comparison operators, IF function, CONCAT function, undo/redo, CSV save/load, search, modulo, and tokenization.