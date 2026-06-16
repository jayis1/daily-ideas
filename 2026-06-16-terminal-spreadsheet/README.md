# Terminal Spreadsheet

A fully interactive, curses-based mini spreadsheet that runs right in your terminal. Edit cells, write formulas, reference other cells, and use built-in functions — all with a keyboard-driven interface inspired by Vim and traditional spreadsheet apps.

## Features

- **Interactive TUI** — Full-screen curses interface with cell grid, status bar, and help line
- **Cell navigation** — Arrow keys or hjkl to move between cells
- **Formula engine** — Write expressions starting with `=` (e.g., `=A1+B2*3`)
- **Cell references** — Refer to any cell by its coordinate (A1 through Z100)
- **Arithmetic** — `+`, `-`, `*`, `/`, `^` (power), `%` (modulo), unary minus
- **Built-in functions** — `SUM`, `AVG`, `MIN`, `MAX`, `COUNT` over ranges; `ABS`, `INT`, `ROUND`, `SQRT`, `IF`
- **Range notation** — `A1:B3` selects a rectangular region for aggregate functions
- **Live recalculation** — Changing a cell instantly updates all dependents
- **Yank/Paste** — Copy cell contents with `y`, paste with `p`
- **Command mode** — Press `:` for commands: `:goto C5`, `:clear`, `:width 14`, `:quit`
- **Sample data** — Ships with a pre-loaded budget spreadsheet so you can explore immediately
- **Zero dependencies** — Uses only the Python standard library (curses)

## How to Install

No installation required beyond Python 3.6+. Just clone and run:

```bash
git clone <repo-url>
cd terminal-spreadsheet
python3 spreadsheet.py
```

> **Note:** On some Linux systems, you may need to install the curses library:
> ```bash
> sudo apt-get install libncurses5-dev  # Debian/Ubuntu
> ```

## How to Run

```bash
python3 spreadsheet.py
```

## Key Bindings

| Key            | Mode  | Action                         |
|----------------|-------|--------------------------------|
| `↑↓←→` / `hjkl` | NAV   | Move cursor                    |
| `e` / `Enter`  | NAV   | Edit current cell              |
| `i`            | NAV   | Insert (edit with empty buffer)|
| `x` / `Del`   | NAV   | Delete current cell            |
| `y`            | NAV   | Yank (copy) current cell       |
| `p`            | NAV   | Paste yanked cell              |
| `:`            | NAV   | Enter command mode             |
| `q`            | NAV   | Quit                           |
| `?` / `H`     | NAV   | Show help                      |
| `Enter`        | EDIT  | Confirm and move down          |
| `Tab`          | EDIT  | Confirm and move right         |
| `Escape`       | EDIT  | Cancel edit                    |
| `Backspace`    | EDIT  | Delete last character          |
| `Enter`        | CMD   | Execute command                |
| `Escape`       | CMD   | Cancel command                 |

## Commands

| Command       | Description                    |
|---------------|--------------------------------|
| `:q` / `:quit`| Quit the spreadsheet           |
| `:h` / `:help`| Show help                     |
| `:clear`      | Clear the entire sheet         |
| `:goto C5`   | Jump cursor to cell C5         |
| `:width 14`  | Set column display width       |

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

### Nested expressions
```
=(A1+A2)*2
```

### IF function
```
=IF(A1>100,A1,0)
```
Returns A1 if it's greater than 100, otherwise 0.

### Square root
```
=SQRT(144)
```
Result: `12`

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

You can modify any cell and see the formulas recalculate live.

## Architecture

- **`Spreadsheet` class** — Stores raw cell contents, evaluates formulas on demand, caches results, and invalidates caches when cells change.
- **Formula parser** — A recursive descent parser that handles operator precedence (unary → power → mul/div → add/sub), parenthesized expressions, cell references, and function calls with range arguments.
- **`SpreadsheetUI` class** — Curses-based rendering engine that manages the grid viewport, cursor position, scrolling, and three input modes (NAV, EDIT, COMMAND).

## Running Tests

```bash
python3 test_spreadsheet.py
```

Runs 18 unit tests covering cell helpers, arithmetic formulas, cell references, SUM/AVG/MIN/MAX/COUNT functions, multi-column ranges, nested formulas, deletion, circular references, division by zero, live recalculation, and tokenization.