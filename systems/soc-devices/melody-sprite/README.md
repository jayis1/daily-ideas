# Melody Sprite

**A handheld 8-voice FM synthesizer, step sequencer, and effects processor built on the RP2040.**

---

## What It Does

Melody Sprite is a pocket-sized music creation instrument that fits in the palm of your hand. It combines an 8-voice FM synthesis engine with a 16-pad capacitive touch keyboard, 4 real-time potentiometers, a crisp OLED display, and a built-in step sequencer — all running on a dual-core RP2040.

Core capabilities:

- **8-voice FM synthesis** — each voice has 2 operators (carrier + modulator) with configurable ratio, feedback, and ADSR envelope
- **16-pad capacitive touch keyboard** — two octaves of chromatic notes, velocity-sensitive via touch duration
- **4 analog potentiometers** — map to any synthesis parameter in real time (mod index, feedback, attack, release, etc.)
- **16-step sequencer** — program patterns with per-step note and velocity; up to 64 steps via 4 banks
- **3 built-in effects** — delay, bit-crusher, and resonant low-pass filter, cascaded in the audio pipeline
- **I2S audio output** — 16-bit, 44.1 kHz stereo via PCM5102A DAC to built-in speaker amp or headphone jack
- **128×64 OLED display** — waveform visualizer, parameter readouts, sequencer grid, and menu navigation
- **BLE MIDI** — wireless MIDI input/output; use Melody Sprite as a BLE MIDI controller or receive MIDI from a DAW
- **USB-C** — power + USB MIDI (appears as a standard MIDI device to any host)
- **Battery powered** — 800 mAh LiPo gives ~6 hours of play; USB-C charging

Whether you're a musician sketching ideas on the bus, a maker learning audio DSP, or a live performer who wants a tiny backup synth, Melody Sprite is designed to be played, not just programmed.

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        MELODY SPRITE                              │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐  │
│  │  MPR121         │  │ 4× Potentiometers│  │  MPR121         │  │
│  │  Cap Touch      │  │ 10kΩ linear      │  │  Cap Touch      │  │
│  │  Controller #1  │  │ (Mod/Atk/Rel/FB) │  │  Controller #2 │  │
│  │  16-pad keyboard│  │ ADC0-3 → RP2040  │  │  8 func buttons │  │
│  │  I²C 0x5A      │  └──────────────────┘  │  I²C 0x5B      │  │
│  └───────┬─────────┘                        └───────┬────────┘  │
│          │ I²C                                       │ I²C      │
│  ┌───────┴──────────────────────────────────────────┴────────┐  │
│  │                      RP2040                                 │  │
│  │  ┌──────────────────┐  ┌───────────────────────────────┐  │  │
│  │  │  Core 0:          │  │  Core 1:                      │  │  │
│  │  │  • UI / OLED      │  │  • FM Synthesis Engine        │  │  │
│  │  │  • Sequencer      │  │  • Effects Pipeline           │  │  │
│  │  │  • Touch scan     │  │  • I2S audio output           │  │  │
│  │  │  • BLE / USB MIDI │  │  • Audio buffer management    │  │  │
│  │  └──────────────────┘  └───────────────────────────────┘  │  │
│  │                                                             │  │
│  │  GPIO0-3  → ADC for potentiometers                        │  │
│  │  GPIO4-5  → I2S BCLK, LRCK                                │  │
│  │  GPIO6   → I2S DOUT                                       │  │
│  │  GPIO7   → UART TX (debug)                                │  │
│  │  GPIO8-9 → I²C SDA/SCL (all I²C devices)                  │  │
│  │  GPIO10  → Encoder A (rotary knob)                        │  │
│  │  GPIO11  → Encoder B (rotary knob)                        │  │
│  │  GPIO12  → Encoder push                                   │  │
│  │  GPIO13  → Power hold (keeps regulator on)                │  │
│  │  GPIO14  → MPR121 IRQ1                                   │  │
│  │  GPIO15  → MPR121 IRQ2                                   │  │
│  │  GPIO16-23 → Direct GPIO for status LEDs                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│          │ I2S                    │ I²C        │ SPI             │
│  ┌───────▼────────┐  ┌──────────▼─────┐  ┌──▼──────────────┐  │
│  │  PCM5102A      │  │  SSD1306       │  │  W25Q16         │  │
│  │  I2S DAC       │  │  128×64 OLED   │  │  16Mbit Flash   │  │
│  │  16-bit 44.1k  │  │  Display       │  │  (patch storage)│  │
│  └───────┬────────┘  └────────────────┘  └─────────────────┘  │
│          │                                                      │
│  ┌───────▼────────┐                                             │
│  │  MAX98357A     │  ┌────────────────┐  ┌──────────────────┐  │
│  │  3W Class-D    │  │ MCP73831       │  │ AP2112-3.3       │  │
│  │  Speaker Amp   │  │ LiPo Charger   │  │ LDO (3.3V/600mA)│  │
│  │  + Headphone   │  │ USB-C → 4.2V  │  │ 5V → 3.3V       │  │
│  │  jack switch   │  └────────────────┘  └──────────────────┘  │
│  └────────────────┘                                            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Power: 800mAh LiPo (3.7V) │ USB-C 5V input & charging    │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (RP2040)

| Pin | Function | Connected To | Notes |
|-----|----------|-------------|-------|
| GPIO0 | ADC0 | Pot 1 (Mod Index) | 10kΩ linear pot, wiper to ADC |
| GPIO1 | ADC1 | Pot 2 (Attack) | 10kΩ linear pot, wiper to ADC |
| GPIO2 | ADC2 | Pot 3 (Release) | 10kΩ linear pot, wiper to ADC |
| GPIO3 | ADC3 | Pot 4 (Feedback) | 10kΩ linear pot, wiper to ADC |
| GPIO4 | I2S BCLK | PCM5102A BCK | Audio bit clock (44.1 kHz × 32) |
| GPIO5 | I2S LRCK | PCM5102A LRCK | Left/right clock (44.1 kHz) |
| GPIO6 | I2S DOUT | PCM5102A DIN | Serial audio data out |
| GPIO7 | UART0 TX | Debug header | 115200 baud, 8N1 |
| GPIO8 | I²C SDA | All I²C devices | 4.7kΩ pull-up to 3.3V |
| GPIO9 | I²C SCL | All I²C devices | 4.7kΩ pull-up to 3.3V |
| GPIO10 | Encoder A | Rotary encoder | Quadrature decode, pull-up |
| GPIO11 | Encoder B | Rotary encoder | Quadrature decode, pull-up |
| GPIO12 | Encoder SW | Rotary encoder | Push button, pull-up |
| GPIO13 | Power hold | AP2112 EN pin | Drive HIGH to keep power on |
| GPIO14 | MPR121 IRQ1 | MPR121 #1 (keyboard) | Active-low interrupt |
| GPIO15 | MPR121 IRQ2 | MPR121 #2 (func buttons) | Active-low interrupt |
| GPIO16 | SPI0 TX | W25Q16 MOSI | External flash data out |
| GPIO17 | SPI0 RX | W25Q16 MISO | External flash data in |
| GPIO18 | SPI0 SCK | W25Q16 CLK | External flash clock |
| GPIO19 | SPI0 CSn | W25Q16 CS | External flash chip select |
| GPIO20 | OLED DC | SSD1306 DC | Data/command select |
| GPIO21 | OLED CS | SSD1306 CS | Chip select (active low) |
| GPIO22 | OLED RST | SSD1306 RES | Reset (active low) |
| GPIO23 | LED | Status LED (blue) | Power/audio activity |
| GPIO24 | VSYS_MONITOR | Voltage divider | Battery voltage monitor via ADC |
| GPIO25 | LED | Status LED (green) | Sequencer step indicator |
| GPIO26 | ADC4 | Ext pedal 1 input | Expression pedal 1 (optional) |
| GPIO27 | ADC5 | Ext pedal 2 input | Expression pedal 2 (optional) |
| GPIO28 | ADC6 | Audio level sense | Peak detector from speaker amp |

---

## Power Architecture

```
                    ┌─────────┐
USB-C 5V ──────────┤ VBUS    │
                    │         │          ┌──────────┐
                    │ MCP     ├──────────┤ LiPo     │ 800 mAh
                    │ 73831   │          │ 3.7V     │
                    │         │          └────┬─────┘
                    └─────────┘               │
                                              │ VSYS (3.0–4.2V)
                    ┌──────────┐               │
                    │ AP2112   ├───────────────┘
                    │ 3.3V LDO│
                    │ 600mA   ├───→ 3.3V Rail (RP2040, all ICs)
                    └──────────┘
                                              │
                    ┌──────────┐               │
                    │ PCM5102A │◄──────────────┘
                    │ 3.3V     │
                    │ + FILT   ├───→ Headphone out
                    └─────┬────┘
                          │
                    ┌─────▼─────┐
                    │ MAX98357A │
                    │ 3W Class-D├───→ Built-in speaker (8Ω)
                    └───────────┘
```

- **Charge current**: 200 mA (PROG resistor = 5kΩ) — full charge in ~4 hours
- **Power hold**: GPIO13 drives AP2112 EN pin; device stays on while HIGH, auto-powers off after 30 min idle
- **Battery life**: ~6 hours typical (synthesis active, moderate volume)
- **Deep sleep current**: <50 µA (RP2040 dormant, only RTC running)

---

## Audio Pipeline

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  FM Synthesis   │    │  Effects Chain   │    │  I2S Output     │
│  Engine         │───►│                  │───►│  PCM5102A       │
│                 │    │  1. Delay (2×)   │    │  16-bit 44.1kHz │
│  8 voices ×    │    │  2. Bit-crusher  │    │  Stereo L/R     │
│  2 operators   │    │  3. LPF (SVF)    │    │                 │
│  each           │    │                  │    │  ──────┐        │
│                 │    │  Mix wet/dry     │    │        │        │
│  ADSR envelope │    │  per effect      │    │  ┌─────▼─────┐  │
│  Per-operator  │    │                  │    │  │MAX98357A  │  │
│  Feedback      │    │                  │    │  │3W Speaker │  │
│  Ratio control │    │                  │    │  └───────────┘  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### FM Synthesis Details

Each of the 8 voices consists of:

| Parameter | Range | Description |
|-----------|-------|-------------|
| Note | C0–B7 (MIDI 12–95) | Chromatic pitch |
| Ratio | 0.25–8.0 (×0.25 steps) | Modulator:carrier frequency ratio |
| Mod Index | 0–1023 | Modulation depth (0 = sine, max = complex) |
| Feedback | 0–15 | Modulator self-modulation |
| Attack | 1–5000 ms | Envelope attack time |
| Decay | 1–5000 ms | Envelope decay time |
| Sustain | 0–1.0 | Sustain level (0–100%) |
| Release | 1–5000 ms | Envelope release time |
| Volume | 0–127 | Per-voice volume |

### Effect Parameters

| Effect | Parameters | Range |
|--------|-----------|-------|
| Delay | Time, Feedback, Mix | 10–1000 ms, 0–90%, 0–100% |
| Bit-crusher | Bits, Downsample | 1–16 bits, 1–64× |
| LPF | Cutoff, Resonance | 100–20000 Hz, 0–8.0 Q |

---

## Capacitive Touch Layout

### Keyboard (MPR121 #1, I²C 0x5A)

```
┌──────────────────────────────────┐
│  C4  C#4 D4  D#4 E4  F4  F#4 G4 │  ← Touch pads 0–7
│  G#4 A4  A#4 B4  C5  C#5 D5 D#5│  ← Touch pads 8–15
└──────────────────────────────────┘
         16 pads = 2 octaves
```

### Function Buttons (MPR121 #2, I²C 0x5B)

| Pad | Function | Description |
|-----|----------|-------------|
| 0 | SEQ | Toggle sequencer record/play |
| 1 | OCT↓ | Octave down |
| 2 | OCT↑ | Octave up |
| 3 | WAVE | Cycle waveform preset |
| 4 | FX1 | Toggle delay effect |
| 5 | FX2 | Toggle bit-crusher |
| 6 | FX3 | Toggle filter |
| 7 | HOLD | Sustain hold (notes sustain until re-pressed) |

---

## Step Sequencer

The built-in 16-step sequencer operates in 3 modes:

1. **Live Record** — play notes on the keyboard; they're captured into the current pattern
2. **Step Edit** — use the rotary encoder to place notes on each step with configurable velocity
3. **Play** — the pattern loops, driving the synthesis engine

Each pattern stores:
- 16 steps × 4 banks = 64 total steps
- Per-step: note (0–127), velocity (0–127), gate (0–100%), accent (yes/no)
- Tempo: 40–300 BPM
- Swing: 0–100%

Patterns are stored in the external W25Q16 SPI flash (up to 128 patterns, each 256 bytes = 32 KB total).

---

## Enclosure

The PCB is designed as a **handheld wand** form factor:

```
              ┌──────────────────────────────────────────┐
              │  ┌────────────────────────────────────┐  │
              │  │         SSD1306 OLED 128×64        │  │
              │  └────────────────────────────────────┘  │
              │                                          │
              │  ┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐        │
              │  │C4││C#││D4││D#││E4││F4││F#││G4│  ...  │
              │  └──┘└──┘└──┘└──┘└──┘└──┘└──┘└──┘        │
              │  ┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐        │
              │  │G#││A4││A#││B4││C5││C#││D5││D#│  ...  │
              │  └──┘└──┘└──┘└──┘└──┘└──┘└──┘└──┘        │
              │                                          │
              │    ◉  ◉  ◉  ◉    ◉  ◉  ◉  ◉             │
              │   Pot1 Pot2 Pot3 Pot4  Func buttons       │
              │                                          │
              │         ◎ Rotary Encoder                  │
              │                                          │
              │  ┌──────┐                        ┌───┐   │
              │  │Speaker│                       │USB│   │
              │  └──────┘                        └───┘   │
              └──────────────────────────────────────────┘
                120mm × 80mm PCB (4-layer)
```

---

## Firmware Architecture

```
Core 0 (UI / Control)                  Core 1 (Audio / DSP)
┌─────────────────────┐               ┌──────────────────────┐
│ main()               │               │ audio_main()          │
│  ├─ ui_task()        │               │  ├─ synth_tick()      │
│  │  ├─ oled_update() │               │  │  ├─ fm_voice() ×8  │
│  │  ├─ touch_scan()  │  (multicore   │  │  ├─ mixer()        │
│  │  └─ encoder_poll() │   FIFO)       │  │  └─ effects()      │
│  ├─ seq_task()        │◄────────────►│  ├─ i2s_output()      │
│  │  ├─ seq_record()  │               │  └─ midi_in()         │
│  │  ├─ seq_play()    │               └──────────────────────┘
│  │  └─ seq_edit()    │
│  ├─ midi_task()      │
│  │  ├─ ble_midi()    │
│  │  └─ usb_midi()    │
│  ├─ pot_task()       │
│  └─ power_task()     │
└─────────────────────┘
```

**Inter-core communication**: A 4-byte FIFO per voice (note, velocity, gate) plus a shared parameter block in RAM.

---

## Building the Firmware

### Prerequisites

```bash
# Install Pico SDK
git clone https://github.com/raspberrypi/pico-sdk.git /opt/pico-sdk
cd /opt/pico-sdk && git submodule update --init

# Install toolchain
sudo apt install gcc-arm-none-eabi libnewlib-arm-none-eabi cmake

# Set environment
export PICO_SDK_PATH=/opt/pico-sdk
```

### Build

```bash
cd firmware
mkdir build && cd build
cmake ..
make -j$(nproc)
# Output: melody_sprite.uf2
```

### Flash

Hold BOOTSEL, plug in USB-C. Copy `melody_sprite.uf2` to the RPI-RP2 drive.

---

## BLE MIDI

Melody Sprite advertises as **"Melody Sprite"** with the BLE MIDI service UUID `03B80E5A-EDE8-4B33-A751-23CE4A040CBE`.

- **Input**: Receive Note On/Off, CC, Program Change from any BLE MIDI controller
- **Output**: Transmit Note On/Off from keyboard touches, CC from pots, Clock from sequencer

Pairing: Hold SEQ + HOLD buttons for 3 seconds to enter BLE pairing mode. The OLED shows the pairing status.

---

## API Reference

### Serial Console (UART, 115200 baud)

```
SYNTH:NOTE_ON <voice> <note> <velocity>
SYNTH:NOTE_OFF <voice>
SYNTH:SET_PARAM <voice> <param> <value>
SYNTH:LIST_VOICES
SEQ:PLAY
SEQ:STOP
SEQ:RECORD
SEQ:SET_TEMPO <bpm>
SEQ:SET_SWING <percent>
SEQ:LOAD <pattern_num>
SEQ:SAVE <pattern_num>
FX:SET <effect> <param> <value>
FX:TOGGLE <effect>
MIDI:SEND_CC <cc> <value>
MIDI:SEND_PC <program>
SYSTEM:INFO
SYSTEM:RESET
```

### I²C Register Map (for external control)

The firmware exposes a simple I²C slave interface on address 0x42 for external MCU control:

| Register | Size | R/W | Description |
|----------|------|-----|-------------|
| 0x00 | 1 | R | Status byte (bit0=playing, bit1=recording, bit2=BLE) |
| 0x01 | 1 | R | Active voice count |
| 0x10-0x17 | 4 | R | Voice N: [note, velocity, gate, param_idx] |
| 0x20 | 2 | R/W | Tempo (BPM, little-endian) |
| 0x22 | 1 | R/W | Swing (0–100) |
| 0x23 | 1 | R/W | Current pattern (0–127) |
| 0x30-0x33 | 2 | R/W | Pot 1-4 raw ADC values |
| 0x40-0x4F | 2 | R/W | Effect parameters (see effects table) |
| 0xFE | 1 | W | Command register (0x01=play, 0x02=stop, 0x03=record) |
| 0xFF | 1 | R | Firmware version |

---

## Safety Notes

- **Hearing protection**: The MAX98357A can drive 3W into 8Ω. Always start with low volume.
- **Battery safety**: Use only protected LiPo cells with built-in PCM. Do not puncture or short.
- **ESD**: The capacitive touch pads are ESD-sensitive. Handle with care during assembly.
- **USB power**: The device can operate on USB power without a battery installed.

---

## License

MIT — build it, play it, mod it, sell it.

---

*Device #11 in the [SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions) collection.*