# Aero Reed — Breath-Controlled Electronic Wind Instrument

> A pocket-sized electronic wind instrument (EWI / wind MIDI controller) with
> capacitive-touch fingering, dual pressure sensing (breath + lip), IMU
> expression, on-board wavetable synthesis, I2S audio output, and BLE / USB MIDI.
> Built around the **ESP32-S3-WROOM-1**.

```
                   ┌─────────────────────────────┐
   mouthpiece  ──▶ │  breath pressure sensor       │
   (lip FSR)  ──▶  │  lip/bite force sensor        │
                   │                               │
  touch pads  ──▶  │  14× capacitive touch (C3-C0) │
                   │  ESP32-S3  ────────────────  │
  IMU (I2C)  ──▶   │   wavetable synth + bore      │
                   │   resonator model              │
                   │                               │
                   │  I2S ──▶ PCM5102A DAC ──▶ amp  │
                   │  BLE MIDI + USB MIDI            │
                   │  OLED (patch display)           │
                   └─────────────────────────────┘
```

---

## 1. What It Is

**Aero Reed** is a fully self-contained electronic wind instrument. You blow
into a mouthpiece; the instrument measures your breath pressure and lip/bite
force, reads which capacitive touch keys you're holding, senses tilt with an
IMU, and synthesises sound in real time — either through the on-board I2S DAC /
headphone amplifier or wirelessly over BLE / USB MIDI to an external synth or
DAW.

It is inspired by the Akai EWI and the Roland Aerophone, but is entirely
open-source and costs ~$60 in parts. It is:

- **Self-contained** — plays sound through headphones or a small on-board
  speaker without any external gear.
- **A real MIDI controller** — sends Breath Control (CC2), Lip/bite (pitch
  bend + CC74), touch keypads as note on/off, and IMU tilt as modulation
  (CC1), over both BLE MIDI and USB MIDI simultaneously.
- **Multi-timbral** — 16-voice wavetable synth with a physically-informed bore
  resonator, breath noise injection, and per-patch envelopes.

### What makes it different from Melody Sprite (#11)

| | Melody Sprite | Aero Reed |
|---|---|---|
| Instrument family | Keyboard synth | Wind controller |
| Primary input | Capacitive touch keyboard + pots | Breath pressure + lip FSR + touch keypads + IMU |
| Synthesis | 8-voice FM | 16-voice wavetable + bore resonator |
| Audio path | I2S mono | I2S stereo + headphone amp + speaker |
| Expression model | Pot CC maps | Breath→amp, Lip→pitch, Tilt→mod |
| Connectivity | BLE MIDI | BLE MIDI **and** USB MIDI |
| SoC | RP2040 | ESP32-S3 |

---

## 2. Key Features

- **14 capacitive touch keypads** mapped to a sax/flute fingering system
  (12 front + 2 thumb/octave), using the ESP32-S3's native touch peripheral.
- **Dual pressure sensing:**
  - **Breath**: NXP MP3V5004G differential pressure sensor → breath velocity,
    dynamics, and over-blow / harmonic switching.
  - **Lip/bite**: Interlink FSR 402 force-sensitive resistor → pitch bend and
    timbral "growl" (CC74 / polyphonic aftertouch).
- **9-axis IMU** (ICM-42688-P over SPI) — tilt angle drives modulation (CC1)
  and a tilt-octave-shift gesture; gyro detects "vibrato shake".
- **16-voice wavetable synth** with:
  - 8 built-in wavetables (sine, triangle, saw, square, 2-formant, bright-pulse,
    breath-noise, warm-pad).
  - One-pole bore-resonance filter tuned to the note frequency (models the
    acoustic bore of a flute/clarinet/sax).
  - ADSR envelope per voice (breath-gated: attack/release follow breath).
  - Per-patch transpose, breath curve, and MIDI CC routing.
- **I2S stereo audio** via PCM5102A DAC → MAX98357A class-D amp (mono
  speaker) + direct headphone jack (stereo).
- **BLE MIDI** (Apple MIDI over BLE) and **USB MIDI** (class-compliant) — both
  active simultaneously.
- **OLED display** (SSD1306, 128×64) — patch name, octave, breath bar,
  battery %, connection status.
- **Rechargeable LiPo** (3.7 V 800 mAh) with USB-C charging (TP4056) and
  fuel-gauge (MAX17048).
- **On-board patch editor** — 8 patches stored in NVS; editable via BLE
  sysex or the Python `patch_editor.py` script over USB serial.

---

## 3. Block Diagram

```
                ┌───────────┐   SPI    ┌──────────────┐
   ICM-42688-P  │ 9-axis IMU │◀────────▶│              │
   └───────────┘            │          │  ESP32-S3    │
                           │          │  WROOM-1-N8  │
   MP3V5004G ──ADC1_CH0────▶│ breath   │              │
   FSR-402  ──ADC1_CH3─────▶│ lip      │              │
   VBAT div ──ADC1_CH4─────▶│ battery  │              │   I2S   ┌──────────┐
                           │          │─────────▶ PCM5102A │ headphone
  14 touch pads ──T0..T13─▶│ touch    │              │  DAC  └──────────┘
                           │          │              │
  SS D1306 ──I2C───────────▶│ OLED     │              │   I2S   ┌──────────┐
  MAX17048 ──I2C───────────▶│ fuelgauge│              │────────▶│MAX98357A │ speaker
                           │          │              │  mono  └──────────┘
                           │          │── UART ──▶ status LED
                           │          │── USB ──▶ USB MIDI + power
                           │          │── BLE ──▶ BLE MIDI
                           └──────────┘
```

---

## 4. Bill of Materials

See [`hardware/BOM.csv`](hardware/BOM.csv) for the full priced BOM. Summary:

| Ref | Part | Qty | Price (USD) | Role |
|-----|------|-----|-----------|------|
| U1 | ESP32-S3-WROOM-1-N8 | 1 | 3.20 | SoC |
| U2 | MP3V5004G | 1 | 5.50 | Breath differential pressure |
| U3 | ICM-42688-P | 1 | 4.10 | 6-axis IMU (gyro+accel) |
| U4 | PCM5102A | 1 | 2.80 | I2S stereo DAC |
| U5 | MAX98357A | 1 | 1.60 | Class-D mono amplifier |
| U6 | SSD1306 OLED 128×64 I2C | 1 | 2.20 | Display |
| U7 | MAX17048 | 1 | 2.30 | LiPo fuel gauge |
| U8 | TP4056 | 1 | 0.35 | LiPo USB-C charger |
| FSR | Interlink FSR-402 | 1 | 1.80 | Lip/bite force |
| SPK | 28 mm 8 Ω mylar speaker | 1 | 1.20 | On-board speaker |
| J1 | 3.5 mm TRS headphone jack | 1 | 0.40 | headphone out |
| J2 | USB-C 2.0 receptacle | 1 | 0.30 | USB MIDI + charging |
| BAT | 3.7 V 800 mAh LiPo | 1 | 3.50 | Battery |
| Misc | passives, buttons, PCB | — | ~8.00 | — |
| | **Total** | | **~$38** | |

---

## 5. Pin Assignments

### ESP32-S3-WROOM-1-N8 pin map

| GPIO | Function | Net | Notes |
|------|----------|-----|-------|
| 0 | BOOT / pad | BOOT_BTN | pull-up, active-low button |
| 1 | Touch T1 | PAD_OCT_DOWN | octave-down thumb pad |
| 2 | Touch T2 | PAD_LH1 | left-hand key 1 |
| 3 | Touch T3 | PAD_LH2 | left-hand key 2 |
| 4 | Touch T4 | PAD_LH3 | left-hand key 3 |
| 5 | Touch T5 | PAD_LH4 | left-hand key 4 (C key) |
| 6 | Touch T6 | PAD_LH5 | left-hand key 5 |
| 7 | Touch T7 | PAD_RH1 | right-hand key 1 |
| 8 | Touch T8 | PAD_RH2 | right-hand key 2 |
| 9 | Touch T9 | PAD_RH3 | right-hand key 3 |
| 10 | Touch T10 | PAD_RH4 | right-hand key 4 |
| 11 | Touch T11 | PAD_RH5 | right-hand key 5 |
| 12 | Touch T12 | PAD_OCT_UP | octave-up thumb pad |
| 13 | Touch T13 | PAD_BEND | pitch-bend / bite-aux pad |
| 14 | Touch T14 | PAD_ALT | alt-fingering / trill pad |
| 15 | ADC1_CH4 | VBAT_DIV | battery voltage divider |
| 16 | ADC1_CH3 | LIP_FSR | lip force divider |
| 17 | ADC1_CH0 (ADC1_CH1) | BREATH | MP3V5004G Vout |
| 18 | SPI MISO | IMU_MISO | ICM-42688-P |
| 19 | SPI MOSI | IMU_MOSI | |
| 20 | SPI SCK | IMU_SCK | |
| 21 | GPIO | IMU_CS | chip select |
| 38 | GPIO | IMU_INT | data-ready interrupt |
| 35 | I2S BCK | DAC_BCK | PCM5102A bit clock |
| 36 | I2S WS | DAC_WS | word select (LRCLK) |
| 37 | I2S DOUT | DAC_DIN | serial data |
| 33 | GPIO | AMP_SD | MAX98357A shutdown |
| 8 (alt) | I2C SDA | I2C_SDA | OLED + fuel gauge |
| 9 (alt) | I2C SCL | I2C_SCL | |
| 43 | UART TX | — | debug |
| 44 | UART RX | — | debug |
| 19/20 | USB D-/D+ | USB_DM/DP | USB MIDI |

> **Touch pins T1–T14** map to GPIO1–GPIO14 on the ESP32-S3 (the touch
> peripheral covers GPIO1-14). ADC channels are on GPIO1-20; to avoid
> conflict we route breath/lip/battery to ADC1 channels that are **not**
> shared with touch (ADC1_CH0 = GPIO1 is touch T1, so we use the internal
> ADC1_CH1 via an analog MUX or route breath to GPIO17 = ADC1_CH0... see the
> note below).

> **ADC conflict note:** The ESP32-S3 ADC1 overlaps touch-capable pins.
> In production we recommend using an **ADS1115** 4-channel I2C ADC for the
> three analog sensors (breath, lip, battery) to free the touch pins entirely.
> The schematic and firmware support both modes (direct-ADC and ADS1115).
> The BOM includes an optional ADS1115 breakout; see
> [`docs/build-notes.md`](docs/build-notes.md).

### Touch keypad layout (saxophone-style fingering)

```
           ┌────────────────────────────────┐
   octave  │  OCT↑   (T12)   OCT↓  (T1)      │  thumb row (back)
           ├────────────────────────────────┤
  left     │  L1(T2) L2(T3) L3(T4) L4(T5) L5(T6) │
  hand     ├────────────────────────────────┤
  right    │  R1(T7) R2(T8) R3(T9) R4(T10) R5(T11) │
  hand     ├────────────────────────────────┤
  aux      │  BEND(T13)      ALT(T14)            │
           └────────────────────────────────┘
```

---

## 6. Power Architecture

```
                USB-C
                  │
        ┌─────────▼──────────┐
        │      TP4056         │   LiPo charging @ 280 mA,
        │  (USB power in)     │   CV/CC, thermal limit
        └─────────┬──────────┘
                  │  VBAT (4.0–4.2 V)
        ┌─────────▼──────────┐
        │  3.7 V 800 mAh LiPo │
        └─────────┬──────────┘
                  │
        ┌─────────▼──────────┐
        │  MAX17048 fuel gauge│── I2C ── ESP32
        └─────────┬──────────┘
                  │
        ┌─────────▼──────────┐
        │  ME6211 LDO 3.3 V   │   500 mA
        └─────────┬──────────┘
                  │  3V3
                  ├──▶ ESP32-S3
                  ├──▶ PCM5102A (3.3 V)
                  ├──▶ MAX98357A (3.3 V logic / 3.7 V speaker power from VBAT)
                  ├──▶ SSD1306 OLED
                  └──▶ ICM-42688-P

```

- The MAX98357A speaker amp is powered directly from VBAT (louder) and
  shut down via `AMP_SD` when headphones are plugged in (jack detect).
- Typical play current ≈ 95 mA → ~8 h battery life.
- USB-C provides both charging (via TP4056) and USB MIDI (via the
  ESP32-S3 native USB peripheral on the same connector — the TP4056 VBUS
  and the ESP32-S3 USB D+/D- share the connector; see schematic).

---

## 7. Firmware

The firmware is written in C using the **ESP-IDF v5.2** framework.

```
firmware/
├── CMakeLists.txt          # top-level build
├── main/
│   ├── CMakeLists.txt
│   ├── main.c              # app entry, task orchestration
│   ├── touch.c / .h        # capacitive touch scanning + fingering decode
│   ├── breath.c / .h       # pressure sensor read + breath curve + gate
│   ├── lip.c / .h          # lip FSR read + pitch bend + growl
│   ├── imu.c / .h          # ICM-42688-P driver + tilt / vibrato
│   ├── synth.c / .h        # wavetable synth + bore resonator + envelope
│   ├── audio.c / .h        # I2S driver + DMA to PCM5102A
│   ├── midi.c / .h         # BLE MIDI + USB MIDI send/receive
│   ├── display.c / .h      # SSD1306 OLED rendering
│   ├── patch.c / .h        # patch storage in NVS
│   ├── power.c / .h        # battery / fuel gauge / charging
│   ├── port_sim.c          # host simulation shim (for `make sim`)
│   └── sdkconfig.defaults
├── sim/
│   └── CMakeLists.txt      # native simulation build (no ESP-IDF)
└── build/                  # (generated)
```

### Building

**Hardware (ESP-IDF):**
```bash
cd firmware
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

**Simulation (host):**
```bash
cd firmware
cmake -B build -S sim
cmake --build build
./build/aero_reed_sim
```

The simulation build links `port_sim.c` (stubbed peripherals) and exercises
the synth, fingering, and MIDI encoding logic, printing a "breath sweep"
trace so you can verify the signal chain without hardware.

### Configuration

`sdkconfig.defaults` sets:
- 240 MHz CPU, 240 MHz flash (QIO)
- I2S 44100 Hz stereo 16-bit
- FreeRTOS tick 1 ms
- BLE MIDI (GATT MIDI service)
- USB CDC + TinyUSB MIDI class
- `CONFIG_BT_NIMBLE_MAX_CONNECTIONS=1`

---

## 8. Patch System

Eight patches live in NVS. Each patch is 32 bytes:

| Offset | Field | Scale |
|--------|-------|-------|
| 0 | wavetable index | 0–7 |
| 1 | transpose (semitones) | -24..+24 |
| 2 | breath curve exponent | 1–8 (x^exp/4.0) |
| 3 | breath CC curve exponent | 1–8 |
| 4 | bore Q | 1–20 (×0.1) |
| 5 | breath-to-noise mix | 0–127 |
| 6 | lip pitch bend range | 0–12 semitones |
| 7 | lip growl depth | 0–127 |
| 8 | tilt mod depth | 0–127 |
| 9 | vibrato rate Hz | 0–20 (÷2) |
| 10 | vibrato depth cents | 0–100 |
| 11–14 | ADSR attack/decay/sustain/release (0–127 each) | — |
| 15 | octave base | -3..+3 |
| 16–31 | name (16 ASCII chars) | — |

Patches are editable via the Python `patch_editor.py` script (USB serial) or
BLE sysex. The on-device UI cycles patches with the BOOT button.

---

## 9. MIDI Implementation

| Control | MIDI message | Default CC |
|---------|--------------|-----------|
| Breath (aftertouch-like) | CC 2 (Breath Controller) + channel pressure | CC2 |
| Lip pitch bend | Pitch bend (14-bit) + CC74 (sound brightness) | CC74 |
| IMU tilt | CC1 (Modulation) | CC1 |
| Vibrato (gyro-detected) | CC76 (vibrato rate) + CC77 (vibrato depth) | CC76/77 |
| Touch keypads | Note On / Note Off (velocity = breath) | — |
| Patch change (BOOT btn) | Program Change | — |

USB MIDI is class-compliant (shows up in any DAW / GarageBand / Camelot).
BLE MIDI uses the Apple BLE MIDI spec (works with iOS / macOS / Windows).

---

## 10. Assembly

See [`docs/assembly-guide.md`](docs/assembly-guide.md) for the full
step-by-step build. In brief:

1. Solder the ESP32-S3-WROOM-1 module onto the PCB (hot-air or reflow).
2. Populate the power section (TP4056, MAX17048, LDO).
3. Populate the touch pad electrodes (large copper pads on the front PCB
   face — these are the "keys"; you can cover them with a thin acrylic panel).
4. Populate the audio section (PCM5102A, MAX98357A, headphone jack, speaker).
5. Wire the mouthpiece assembly: MP3V5004G + FSR-402 in a 3D-printed
   mouthpiece (STL provided in `docs/`).
6. Mount the OLED on the top face.
7. Flash firmware over USB-C.

---

## 11. Usage

1. Charge via USB-C (LED: red=charging, green=full).
2. Power on: press BOOT for 1 s → OLED shows patch name.
3. Select patch: tap BOOT to cycle through 8 patches.
4. Play: blow into the mouthpiece; hold touch pads for notes; bite for
   pitch bend; tilt for modulation.
5. Connect to a DAW: plug USB-C → it appears as "Aero Reed MIDI". Or pair
   via Bluetooth → "Aero Reed BLE MIDI".
6. Edit patches: `python3 scripts/patch_editor.py --port /dev/ttyACM0`

---

## 12. API Reference

See [`docs/api-reference.md`](docs/api-reference.md) for full firmware API
docs. Key modules:

- **`touch_get_fingering()`** → returns decoded MIDI note number or -1.
- **`breath_get_velocity()`** → 0–127 MIDI velocity from pressure.
- **`breath_get_gate()`** → bool, true above breath threshold.
- **`lip_get_bend_cents()`** → pitch bend in cents from FSR.
- **`imu_get_modulation()`** → 0–127 modulation from tilt.
- **`synth_note_on(note, vel, patch)`** / `synth_note_off(note)`.
- **`midi_send_ble(msg, len)`** / `midi_send_usb(msg, len)`.

---

## 13. License

MIT — build it, play it, improve it. See repo root LICENSE.