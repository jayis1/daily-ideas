# 🛡️ Procedural Heraldry Generator

A command-line tool that generates random medieval-style coats of arms following authentic heraldic rules, rendered as colorful ASCII art in the terminal. Each coat of arms includes a proper blazon (formal heraldic description), a colored shield with charges and divisions, decorative mantling, and a random Latin motto.

## Features

- **Heraldically correct**: Follows the Rule of Tincture — metals (Or, Argent) are never placed on metals, and colours (Gules, Azure, Sable, Vert, Purpure) are never placed on colours. This ensures every generated coat of arms has proper contrast.
- **7 shield divisions**: Per Pale, Per Fess, Per Bend, Per Bend Sinister, Per Saltire, Quarterly, Per Chevron, and Gyronny
- **12 charges/ordinaries**: Cross, Saltire, Roundel, Lozenge, Star (mullet), Crescent, Fleur-de-lis, Escallop, Bend, Chevron, Pale, and Fess
- **7 tinctures** with distinct ANSI 256-color rendering: Or (gold), Argent (white), Gules (red), Azure (blue), Sable (black), Vert (green), Purpure (purple)
- **Heater-style shield shape** that tapers at top and bottom, just like real heraldic shields
- **Decorative mantling** in the field colours
- **Random Latin mottos** from historical sources
- **Historical presets**: View real coats of arms (England, France, Scotland, Switzerland)
- **Reproducible output** via seed values
- **Blazon-only mode** for quick text generation
- **No dependencies** — pure Python 3 standard library

## Installation

No installation needed — just download and run:

```bash
# Clone or download the script
wget https://raw.githubusercontent.com/.../heraldry.py
chmod +x heraldry.py
```

Or simply copy `heraldry.py` to your machine. It requires only Python 3.6+ with no external packages.

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

## How It Works

### Blazon Generation

A **blazon** is the formal language of heraldry that describes a coat of arms. The generator creates blazons like:

- *"Gules, charged with a Cross Argent"* — red field with a white cross
- *"Per Pale Azure and Or, charged with a Lozenge Gules"* — blue/gold split field with a red diamond
- *"Quarterly Sable and Argent, charged with a Crescent Purpure"* — black/white quartered field with a purple crescent

### Rule of Tincture

The generator enforces the medieval Rule of Tincture: a colour must not be placed on a colour, nor a metal on a metal. This ensures all generated arms have proper contrast and look authentic. The seven tinctures split into:

- **Metals**: Or (gold/yellow), Argent (silver/white)
- **Colours**: Gules (red), Azure (blue), Sable (black), Vert (green), Purpure (purple)

### Shield Rendering

The shield is rendered on a 30×28 character grid shaped as a classic heater shield. Each pixel is filled with the appropriate tincture's ANSI color code, with a dark border outline. The result is a surprisingly detailed and colorful terminal display.

## Examples

```
$ python3 heraldry.py -s 100

╔══════════════════════════════════════════════╗
║                 COAT OF ARMS                 ║
╟──────────────────────────────────────────────╢
║ "Per Bend Sinister Argent and Sable,        ║
║ charged with a Roundel Gules"               ║

╟──────────────────────────────────────────────╢

        ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
        ███████████████████████
        █████████████████████████
        ...

       ╱╲    ╱╲    ╱╲    ╱╲    ╱╲    ╱╲
 ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲  ╱  ╲
╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲╱    ╲

╭──────────────────────────────────────────────╮
│           « Per Aspera Ad Astra »            │
╰──────────────────────────────────────────────╯
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `-n`, `--number` | Number of coats of arms to generate (default: 1) |
| `-s`, `--seed` | Random seed for reproducibility |
| `--historical` | Display a specific historical coat of arms (england, france, scotland, switzerland) |
| `--list-historical` | List available historical coats of arms |
| `--blazon-only` | Output only the blazon text, no visual art |
| `--no-color` | Disable colored output |
| `--plain` | Use plain ASCII characters instead of Unicode |

## License

MIT