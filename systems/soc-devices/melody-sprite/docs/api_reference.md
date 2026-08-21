# Melody Sprite — API Reference

## Serial Console (UART, 115200 baud, 8N1)

The Melody Sprite exposes a text-based command interface over USB serial (CDC) for debugging, live control, and firmware updates.

### Command Format

```
MODULE:COMMAND [arguments]
```

Commands are case-insensitive. Arguments are space-separated. Responses are prefixed with `OK` or `ERR`.

---

## Synth Commands

### `SYNTH:NOTE_ON <voice> <note> <velocity>`

Trigger a note on a specific voice.

| Param | Range | Description |
|-------|-------|-------------|
| voice | 0–7 | Voice number |
| note | 12–95 | MIDI note number (C0–B7) |
| velocity | 0–127 | Note velocity |

Example: `SYNTH:NOTE_ON 0 60 100` — Play middle C on voice 0, velocity 100

Response: `OK NOTE_ON voice=0 note=60 vel=100`

### `SYNTH:NOTE_OFF <voice>`

Release a specific voice.

Example: `SYNTH:NOTE_OFF 0`

Response: `OK NOTE_OFF voice=0`

### `SYNTH:NOTE_ALL_OFF`

Release all active voices (panic button).

Response: `OK ALL_NOTES_OFF`

### `SYNTH:SET_PARAM <voice> <param> <value>`

Set a synthesis parameter on a voice.

| Param | Type | Range | Unit |
|-------|------|-------|------|
| mod_ratio | float | 0.25–8.0 | × (frequency multiplier) |
| mod_index | float | 0–1023 | modulation depth |
| feedback | float | 0–15 | self-feedback amount |
| attack | float | 1–5000 | ms |
| decay | float | 1–5000 | ms |
| sustain | float | 0–1.0 | level (0–100%) |
| release | float | 1–5000 | ms |
| volume | float | 0–1.0 | voice volume |

Example: `SYNTH:SET_PARAM 0 mod_index 500`

Response: `OK PARAM_SET voice=0 param=mod_index value=500.0`

### `SYNTH:LIST_VOICES`

Print the status of all 8 voices.

Response:
```
OK VOICES:
  V0: note=60 state=ATTACK freq=261.63Hz
  V1: note=-- state=IDLE
  V2: note=67 state=SUSTAIN freq=392.00Hz
  ...
```

### `SYNTH:MASTER_VOLUME <level>`

Set the master output volume.

| Param | Range | Description |
|-------|-------|-------------|
| level | 0–100 | Volume percentage |

Example: `SYNTH:MASTER_VOLUME 75`

---

## Sequencer Commands

### `SEQ:PLAY`

Start sequencer playback from the beginning.

Response: `OK SEQ_PLAY step=0`

### `SEQ:STOP`

Stop sequencer playback.

Response: `OK SEQ_STOP`

### `SEQ:RECORD`

Start live recording mode. Notes played on the keyboard are captured into the current pattern.

Response: `OK SEQ_RECORD`

### `SEQ:SET_TEMPO <bpm>`

Set sequencer tempo.

| Param | Range | Description |
|-------|-------|-------------|
| bpm | 40–300 | Beats per minute |

Example: `SEQ:SET_TEMPO 140`

### `SEQ:SET_SWING <percent>`

Set swing amount.

| Param | Range | Description |
|-------|-------|-------------|
| percent | 0–100 | Swing percentage (0 = straight, 100 = maximum swing) |

### `SEQ:SET_STEP <step> <note> <velocity> <gate>`

Program a specific step in the current pattern.

| Param | Range | Description |
|-------|-------|-------------|
| step | 0–63 | Step number |
| note | 0–127 or -- | MIDI note, or `--` for rest |
| velocity | 0–127 | Note velocity |
| gate | 0–100 | Gate length percentage |

Example: `SEQ:SET_STEP 0 60 100 80` — Step 0: C4, velocity 100, 80% gate

### `SEQ:CLEAR_STEP <step>`

Clear a step (make it a rest).

### `SEQ:CLEAR_PATTERN`

Clear all steps in the current pattern.

### `SEQ:LOAD <pattern_num>`

Load a pattern from flash storage.

| Param | Range | Description |
|-------|-------|-------------|
| pattern_num | 0–127 | Pattern slot number |

### `SEQ:SAVE <pattern_num>`

Save the current pattern to flash storage.

---

## Effects Commands

### `FX:SET <effect> <param> <value>`

Set an effect parameter.

**Delay:**
- `FX:SET delay time <10–1000>` — Delay time in ms
- `FX:SET delay feedback <0–90>` — Feedback percentage
- `FX:SET delay mix <0–100>` — Wet/dry mix percentage

**Bit-crusher:**
- `FX:SET crush bits <1–16>` — Bit depth
- `FX:SET crush downsample <1–64>` — Downsample factor

**Low-pass filter:**
- `FX:SET lpf cutoff <100–20000>` — Cutoff frequency in Hz
- `FX:SET lpf resonance <0.1–8.0>` — Resonance (Q)

Examples:
```
FX:SET delay time 350
FX:SET delay feedback 50
FX:SET crush bits 8
FX:SET lpf cutoff 2000
FX:SET lpf resonance 2.5
```

### `FX:TOGGLE <effect>`

Toggle an effect on/off.

| Effect | Name |
|--------|------|
| Delay | `delay` |
| Bit-crusher | `crush` |
| Low-pass filter | `lpf` |

Example: `FX:TOGGLE delay` — toggles delay on/off

### `FX:STATUS`

Print the current state of all effects.

Response:
```
OK FX_STATUS:
  Delay: ON time=250ms fb=0.4 mix=0.3
  Crush: OFF bits=16 ds=1
  LPF: OFF cutoff=8000Hz Q=0.7
```

---

## MIDI Commands

### `MIDI:SEND_CC <cc> <value>`

Send a MIDI Control Change message over BLE MIDI.

| Param | Range | Description |
|-------|-------|-------------|
| cc | 0–127 | Controller number |
| value | 0–127 | Controller value |

### `MIDI:SEND_PC <program>`

Send a MIDI Program Change message over BLE MIDI.

| Param | Range | Description |
|-------|-------|-------------|
| program | 0–127 | Program number |

### `MIDI:BLE_PAIR`

Enter BLE pairing mode. The device advertises as "Melody Sprite" for 60 seconds.

Response: `OK BLE_PAIRING`

### `MIDI:BLE_DISCONNECT`

Disconnect current BLE connection.

---

## System Commands

### `SYSTEM:INFO`

Print system information.

Response:
```
OK SYSTEM_INFO:
  Firmware: v1.0.0
  SoC: RP2040
  Flash: 16Mbit (W25Q16)
  Battery: 3.82V (72%)
  Uptime: 00:15:32
  Voices active: 3/8
  CPU0: 45% (UI)
  CPU1: 78% (Audio)
```

### `SYSTEM:RESET`

Soft reset the device. All state is lost.

Response: `OK RESETTING...`

### `SYSTEM:POWER_OFF`

Graceful shutdown. Cuts power via power-hold GPIO.

Response: `OK POWER_OFF`

### `SYSTEM:CALIBRATE_TOUCH`

Run capacitive touch baseline recalibration.

Response: `OK CALIBRATING... DONE`

---

## I²C Slave Register Map (Address 0x42)

For external MCU control via I²C. The device responds as an I²C slave on address 0x42.

| Register | Size | R/W | Description |
|----------|------|-----|-------------|
| 0x00 | 1 | R | Status byte |
| | | | Bit 0: Playing |
| | | | Bit 1: Recording |
| | | | Bit 2: BLE connected |
| | | | Bit 3: USB connected |
| | | | Bit 4: Hold active |
| | | | Bit 5–7: Reserved |
| 0x01 | 1 | R | Active voice count (0–8) |
| 0x02 | 1 | R | Current sequencer step (0–63) |
| 0x10–0x17 | 4 | R | Voice N: [note, velocity, gate, state] |
| 0x20 | 2 | R/W | Tempo (BPM, little-endian) |
| 0x22 | 1 | R/W | Swing (0–100) |
| 0x23 | 1 | R/W | Current pattern (0–127) |
| 0x30 | 2 | R | Pot 1 raw ADC (0–4095) |
| 0x32 | 2 | R | Pot 2 raw ADC (0–4095) |
| 0x34 | 2 | R | Pot 3 raw ADC (0–4095) |
| 0x36 | 2 | R | Pot 4 raw ADC (0–4095) |
| 0x40 | 2 | R/W | Delay time (10–1000 ms) |
| 0x42 | 1 | R/W | Delay feedback (0–90) |
| 0x43 | 1 | R/W | Delay mix (0–100) |
| 0x44 | 1 | R/W | Bit-crusher bits (1–16) |
| 0x45 | 1 | R/W | Bit-crusher downsample (1–64) |
| 0x46 | 2 | R/W | LPF cutoff (100–20000 Hz) |
| 0x48 | 2 | R/W | LPF resonance (×100, e.g. 070 = 0.70) |
| 0xFE | 1 | W | Command register (see below) |
| 0xFF | 1 | R | Firmware version (0x10 = v1.0) |

### Command Register (0xFE) Values

| Value | Action |
|-------|--------|
| 0x01 | Start playback |
| 0x02 | Stop playback |
| 0x03 | Start recording |
| 0x04 | Stop recording |
| 0x05 | All notes off (panic) |
| 0x06 | Calibrate touch |
| 0x07 | Reset device |
| 0x08 | Power off |
| 0x10–0x17 | Note on voice 0–7 (velocity = 100) |
| 0x20–0x27 | Note off voice 0–7 |
| 0x30 | Toggle delay |
| 0x31 | Toggle bit-crusher |
| 0x32 | Toggle LPF |
| 0x40 | Toggle hold mode |

### I²C Transaction Examples

**Read active voice count:**
```
Master: START → 0x84 (0x42 << 1 | R) → ACK
Slave: 0x03 (3 voices active) → STOP
```

**Set tempo to 140 BPM:**
```
Master: START → 0x84 (0x42 << 1 | W) → ACK → 0x20 → ACK → 0x8C (140 LSB) → ACK → 0x00 (0 MSB) → ACK → STOP
```

**Start playback:**
```
Master: START → 0x84 (0x42 << 1 | W) → ACK → 0xFE → ACK → 0x01 → ACK → STOP
```