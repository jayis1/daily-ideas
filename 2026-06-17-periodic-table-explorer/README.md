# Periodic Table Explorer

An interactive terminal-based periodic table of the elements built with Python curses. Browse all 118 elements, navigate the full periodic table layout, search by name or symbol, filter by element category, and view detailed element information — all from your terminal.

![Periodic Table Explorer](https://img.shields.io/badge/118-elements-blue)

## Features

- **Full Periodic Table Layout** — All 118 elements displayed in the standard periodic table arrangement, including properly placed lanthanide and actinide rows
- **Interactive Navigation** — Arrow key navigation across the periodic table grid with intelligent neighbor-finding
- **Element Detail View** — Press Enter on any element to see a rich detail screen with big ASCII art symbol, atomic mass, category, phase, discovery year, period/group, mass rank, and neighbor elements
- **Search** — Press `/` to search elements by name, symbol, or atomic number
- **Category Filtering** — Press `F` to filter the table to show only elements of a specific category (alkali metals, noble gases, halogens, etc.)
- **Color-Coded Categories** — Each element category gets its own distinctive color, making patterns in the table instantly visible
- **ASCII Art Symbols** — Detail view shows the element symbol rendered in large block-letter ASCII art
- **Discovery Year Formatting** — Ancient elements show BCE dates, modern ones show the actual discovery year
- **Phase Information** — See whether each element is solid, liquid, or gas at STP

## Installation

No external dependencies needed — uses only Python's built-in `curses` library.

```bash
# Clone the repo
git clone <repo-url>
cd 2026-06-17-periodic-table-explorer

# Make it executable (optional)
chmod +x periodic_table.py
```

**Requirements:** Python 3.6+ with curses support (included by default on Linux/macOS; on Windows, install `windows-curses`).

## How to Run

```bash
python3 periodic_table.py
```

## Controls

| Key | Action |
|-----|--------|
| ↑↓←→ | Navigate elements on the table |
| Enter | View detailed element info |
| `/` | Open search mode |
| `F` | Open category filter |
| `q` / ESC | Quit (from table view) |
| ESC | Cancel (from search/filter) |

### Detail View Controls

| Key | Action |
|-----|--------|
| ← → | Browse previous/next element |
| ESC / Enter | Return to table view |

### Search Mode

Type an element name (e.g., `gold`), symbol (e.g., `Au`), or atomic number (e.g., `79`) to find elements. Use arrow keys to navigate results, Enter to select.

### Filter Mode

Select a category to highlight only those elements on the table. Selecting an already-active category clears the filter.

## Usage Examples

### Quick Lookup
```bash
# Start the explorer
python3 periodic_table.py

# Navigate to Iron (Fe, #26) using arrow keys, then press Enter to see:
#   ___
#  | # |  Detailed view with:
#  |Fe |  - Atomic number, symbol, name
#  |___|  - Atomic mass (55.845 u)
#         - Category: Transition Metal
#         - Phase: Solid
#         - Discovered: 5000 BCE
#         - Period 4, Group 8
```

### Search for an Element
```bash
# Press / to enter search mode
# Type "oxygen" or "O" or "8"
# Arrow down to select, Enter to view details
```

### Filter by Category
```bash
# Press F to open filter
# Arrow down to "Noble Gas", press Enter
# Only noble gas elements (He, Ne, Ar, Kr, Xe, Rn) will be highlighted
# on the periodic table
```

## Data Coverage

All **118 confirmed elements** are included with:
- Atomic number, symbol, and name
- Atomic mass (standard atomic weight)
- Element category (11 categories)
- Phase at standard temperature and pressure
- Discovery year (including BCE for ancient elements)

## How It Works

The app uses Python's `curses` library to render the periodic table directly in the terminal. Each element is drawn as a small cell at its correct position on the standard periodic table grid. Lanthanides (57-71) and actinides (89-103) are displayed in separate rows below the main table, matching the conventional layout.

Navigation uses a position-aware algorithm that finds the nearest element in the specified direction by matching group/period coordinates, with intelligent handling of the gaps in the table and transitions to/from the lanthanide and actinide rows.

## License

MIT