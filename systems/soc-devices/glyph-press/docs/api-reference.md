# Glyph Press — API Reference

## BLE Serial Protocol

The Glyph Press communicates via a Bluetooth Classic SPP serial port (HC-05 module, 9600 baud, 8N1). Connect from any Bluetooth serial terminal app.

### Command Set

All commands are ASCII text terminated with `\n`. Responses are ASCII prefixed with `OK ` or `ERR `.

### TEXT — Queue Text

```
TEXT <string>
```

Queues text for embossing. Maximum 4096 characters. Newlines in the text are treated as spaces (the firmware handles line wrapping based on cells-per-line setting).

**Response:** `OK Text queued`

**Example:**
```
TEXT MORNING MEDS
OK Text queued
```

### MODE — Set Braille Mode

```
MODE G1|G2|G8|LABEL|PAGE
```

| Mode | Description |
|------|-------------|
| G1 | Grade 1 (uncontracted, letter-by-letter) |
| G2 | Grade 2 (UEB contracted English) |
| G8 | 8-dot Unicode Braille pass-through |
| LABEL | Single-line centered label |
| PAGE | Multi-line page mode |

**Response:** `OK Mode set`

### LANG — Set Language

```
LANG en|fr|es|de|pt|ar|hi|zh
```

Selects the Grade 1 translation table. Grade 2 contractions are English-only.

**Response:** `OK Lang set` or `ERR Unknown lang`

### FORCE — Set Embossing Force

```
FORCE 0-9
```

Sets the solenoid dwell time (force level). 0 = lightest (thin label tape), 9 = firmest (cardstock). Default: 5.

**Response:** `OK Force set`

### CPL — Set Cells Per Line

```
CPL <20-40>
```

Sets the number of Braille cells per line. Standard Braille paper is 28-40 cells per line. Default: 28.

**Response:** `OK CPL set`

### FEED — Manual Paper Feed

```
FEED <mm>
```

Advances the paper by the specified distance in millimeters. Useful for positioning media before embossing.

**Response:** `OK Fed`

### START — Begin Embossing

```
START
```

Begins embossing the queued text. The device must be in IDLE state with text already queued.

**Response:** `OK Embossing` or `ERR No text or busy`

### STOP — Cancel Embossing

```
STOP
```

Cancels the current emboss job and returns to IDLE.

**Response:** `OK Stopped`

### STATUS — Query Device Status

```
STATUS
```

**Response:** `OK <state> mode:<mode> cells:<done>/<total>`

State is `idle` or `busy`. Mode is one of `G1`, `G2`, `8dot`, `Label`, `Page`.

**Example:**
```
STATUS
OK busy mode:G2 cells:14/28
```

### TEST — Self-Test

```
TEST
```

Embosses the Braille alphabet (A-Z) as a self-test. Useful for verifying the embosser head is working.

**Response:** `OK Test embossing alphabet`

### HELP — List Commands

```
HELP
```

Returns a list of all available commands.

## SD Card File Format

Place a `.txt` file (UTF-8, plain text) on a FAT32-formatted microSD card. The firmware reads the first `.txt` file found (alphabetical order by filename) and embosses it. Maximum file size: 32 KB.

## USB-CDC Interface

When connected via USB-C, the RP2040 exposes a USB-CDC serial port (115200 baud) that accepts the same command set. This is used for:
- Firmware flashing (via UF2 drag-and-drop in BOOTSEL mode)
- Braille table loading (`scripts/load_tables.py`)
- Direct text sending from a PC

## Python API

```python
import serial

ser = serial.Serial("/dev/tty.GlyphPress", 9600)

# Queue text
ser.write(b"TEXT HELLO WORLD\n")

# Set mode
ser.write(b"MODE G2\n")

# Start embossing
ser.write(b"START\n")

# Read response
print(ser.readline().decode())
```