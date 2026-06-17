# 🛡️ Procedural Heraldry Generator

A command-line tool that generates random medieval-style coats of arms following authentic heraldic rules, rendered as colorful ASCII art in the terminal. Each coat of arms includes a proper blazon (formal heraldic description), a colored shield with charges and divisions, decorative mantling, and a random Latin motto.

## Features

- **Heraldically correct**: Follows the Rule of Tincture — metals (Or, Argent) are never placed on metals, and colours (Gules, Azure, Sable, Vert, Purpure) are never placed on colours. Every generated coat of arms has proper contrast.
- **8 shield divisions**: Per Pale, Per Fess, Per Bend, Per Bend Sinister, Per Saltire, Quarterly, Per Chevron, and Gyronny
- **12 charges/ordinaries**: Cross, Saltire, Roundel, Lozenge, Star (mullet), Crescent, Fleur-de-lis, Escallop, Bend, Chevron, Pale, and Fess
- **7 tinctures** with distinct ANSI 256-color rendering: Or (gold), Argent (white), Gules (red), Azure (blue), Sable (black), Vert (green), Purpure (purple)
- **Heater-style shield shape** that tapers at top and bottom, just like real heraldic shields
- **Decorative mantling** in the field colours
- **Random Latin mottos** from historical sources
- **Historical presets**: View real coats of arms (England, France, Scotland, Switzerland)
- **Reproducible output** via seed values
- **Blazon-only mode** for quick text generation
- **Plain ASCII mode** (`--plain`) for terminals that don't support Unicode
- **No color mode** (`--no-color`) for piping or monochrome terminals
- **Version flag** (`--version`)
- **Input validation**: Rejects invalid values for `--number`
- **No dependencies** — pure Python 3.6+ standard library

## Installation

No installation needed — just download and run:

```bash
# Clone the repository
git clone <repo-url>
cd heraldry-generator

# Make executable (optional)
chmod +x heraldry.py

# Run directly
python3 heraldry.py
```

Requires only Python 3.6+ with no external packages.

## Usage

### Generate a random coat of arms

```bash
python3 heraldry.py
```

### Generate multiple coats of arms

```bash
python3 heraldry.py -n 5
```

### Reproducible generation with a seed

```bash
python3 heraldry.py -s 42
```

### View a historical coat of arms

```bash
python3 heraldry.py --historical england
python3 heraldry.py --historical france
python3 heraldry.py --historical scotland
python3 heraldry.py --historical switzerland
```

### List available historical coats of arms

```bash
python3 heraldry.py --list-historical
```

### Blazon text only (no visual output)

```bash
python3 heraldry.py --blazon-only
python3 heraldry.py --blazon-only -n 10
```

### Disable colors

```bash
python3 heraldry.py --no-color
```

### Plain ASCII mode (no Unicode characters)

```bash
python3 heraldry.py --plain
python3 heraldry.py --plain --no-color
```

### Show version

```bash
python3 heraldry.py --version
```

## How It Works

### Blazon Generation

A **blazon** is the formal language of heraldry that describes a coat of arms. The generator creates blazons like:

- *"Gules, charged with a Cross Argent"* — red field with a white cross
- *"Per Pale Azure and Or"* — blue/gold split field with no charge
- *"Quarterly Sable and Argent, charged with a Crescent Purpure"* — black/white quartered field with a purple crescent

### Rule of Tincture

The generator enforces the medieval Rule of Tincture: a colour must not be placed on a colour, nor a metal on a metal. This ensures all generated arms have proper contrast and look authentic. The seven tinctures split into:

- **Metals**: Or (gold/yellow), Argent (silver/white)
- **Colours**: Gules (red), Azure (blue), Sable (black), Vert (green), Purpure (purple)

When the shield is divided into a metal and a colour, a single central charge cannot simultaneously contrast with both halves. In this case, the generator omits the charge — producing a clean divided field, which is perfectly valid heraldry.

### Shield Rendering

The shield is rendered on a 30×28 character grid shaped as a classic heater shield. Each pixel is filled with the appropriate tincture's ANSI color code, with a dark border outline. The result is a surprisingly detailed and colorful terminal display.

## Command-Line Options

| Option | Description |
|--------|-------------|
| `-n`, `--number` | Number of coats of arms to generate (default: 1, must be ≥ 1) |
| `-s`, `--seed` | Random seed for reproducibility |
| `--historical` | Display a specific historical coat of arms (england, france, scotland, switzerland) |
| `--list-historical` | List available historical coats of arms |
| `--blazon-only` | Output only the blazon text, no visual art |
| `--no-color` | Disable colored output |
| `--plain` | Use plain ASCII characters instead of Unicode |
| `--version` | Print version number and exit |

## Running Tests

```bash
python3 test_heraldry.py
```

The test suite includes 26 tests covering:
- Rule of tincture compliance (2000 random blazons)
- All 8 divisions and 12 charges render correctly
- Plain ASCII and no-color modes
- CLI flag validation
- Seed reproducibility
- State restoration after `--no-color`
- Historical coats of arms render without errors

## Changelog

### v1.1.0 — Bug fixes

- **Fixed: Rule of Tincture violations** — When a divided field contained one metal and one colour, the charge selection would fall back to a tincture that violated the rule against one half. Now the charge is correctly omitted in this case, producing heraldically valid divided fields.
- **Fixed: `--plain` flag not implemented** — The `--plain` argument was accepted but had no effect. Now it properly replaces all Unicode box-drawing characters with ASCII equivalents (`╔`→`+`, `║`→`|`, `█`→`#`, etc.) for terminals without Unicode support.
- **Fixed: `--no-color` permanently mutated global state** — Using `--no-color` would set the module's `RESET`, `BOLD`, `TINCTURES` etc. to empty strings, breaking any subsequent calls in the same process. Colors are now properly restored after each run via `restore_colors()`.
- **Added: `--version` flag** — Shows version number (v1.1.0).
- **Added: Input validation on `--number`** — Negative numbers and zero are now rejected with a clear error message.
- **Added: Unit test suite** — 26 tests covering rule compliance, rendering, CLI flags, and edge cases.
- **Fixed: README download URL** — Removed placeholder `wget` URL that pointed to a non-existent file.

## License

MIT