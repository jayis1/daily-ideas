# Glyph Press

**A portable, battery-operated Braille embossing device that takes text from a phone (BLE), an SD card, or a hardware keyboard, translates it into Braille (Grade 1 / Grade 2 / 8-dot Unicode), and embosses physical tactile dots onto standard paper or adhesive label tape using an 8-cell piezo-bender actuator head — built around an RP2040 dual-core MCU with a TMC2209-fed stepper paper-feed and BLE via an HC-05-compatible UART bridge.**

---

## What It Does

The Glyph Press is a **pocket-sized personal Braille embosser**. You feed it a strip of paper or adhesive label tape, send text from your phone (via a simple BLE terminal app or the companion Python script), and it embosses physical raised Braille dots onto the media — one line at a time, at ~3 cells/sec, in a format compatible with standard Braille conventions (6-dot and 8-dot). Unlike commercial Braille embossers ($1,800–$15,000, desk-sized, requiring tractor-feed paper), the Glyph Press costs under $70 and fits in a jacket pocket. It lets blind and low-vision users independently produce Braille labels for household items, file folders, medication, books, and personal notes — without depending on a sighted assistant or a specialized resource center.

### Why affordable personal Braille embossing matters

There are an estimated 43 million blind people worldwide and over 250 million with significant visual impairment. Access to Braille — the tactile writing system that remains the most reliable, private, and fast reading medium for blind people — is gated by the cost of Braille embossers and Braille books. Commercial Braille embossers are expensive precision machines found in schools, libraries, and rehabilitation centers, not in homes. Meanwhile, cheap "DIY Braille" solutions like slate-and-stylus require significant manual skill and patience, and can only produce one dot at a time. The Glyph Press bridges this gap: a portable, battery-powered embosser that takes text from the smartphone already in the user's pocket and produces real, physically raised Braille on demand, at home, in the office, or in the field. It democratizes Braille production for personal use, independent living skills, education, and emergency labeling.

### How it works

1. **Text input** — The user sends text to the Glyph Press via one of three channels:
   - **BLE from phone** — The companion Python script `glyph_send.py` (or any BLE terminal app) connects to the device and streams UTF-8 text. The firmware buffers up to 4096 characters.
   - **SD card** — A plain `.txt` file on a microSD card (FAT32) is read and embossed sequentially.
   - **Hardware UART** — A 433 MHz radio module or a wired keyboard terminal can send text for field deployments with no smartphone.

2. **Braille translation** — The firmware includes a Braille translation engine that converts Unicode text to dot patterns:
   - **Grade 1 (uncontracted)** — letter-by-letter mapping with support for 60+ languages (English, French, Spanish, German, Portuguese, Arabic, Hindi, Chinese pinyin).
   - **Grade 2 (contracted English)** — a compact rule-based contraction engine implementing ~180 common English Braille contractions (ch, sh, th, the, and, for, of, etc.) following the UEB (Unified English Braille) standard.
   - **8-dot mode** — supports 8-dot Braille Unicode (U+2800–U+28FF) for technical / scientific notation and line-number annotations.
   - The translation table is stored in flash as a compressed 8 KB lookup, with multi-character contraction rules in a 4 KB trie structure.

3. **Embosser head** — The physical embossing mechanism uses an **8-cell solenoid-bender actuator head**: each Braille cell is 2 wide × 4 high dots (one column of 8 cells = 16 dots for 8-dot mode, or 8 cells of 2×3 for 6-dot). Each dot is formed by a miniature 5V push-pull solenoid (5 mm stroke, 3 N force) that drives a hardened steel pin into the paper against a soft rubber anvil, forming a raised dot on the front of the paper. The solenoids fire in parallel for all dots in a single cell, then the paper advances by one cell width (6 mm). This produces standard-dimension Braille (dot diameter 1.5 mm, cell spacing 6 × 4 mm).
   - The head has 16 solenoids arranged in two columns of 8 (one column = 8 vertical dots for a single 8-dot cell; in 6-dot mode only the upper 6 are used).
   - A DRV8833 dual H-bridge drives each pair of solenoids with flyback protection, under the RP2040's PWM control.
   - Embossing force is software-adjustable (light for thin label tape, firm for cardstock).

4. **Paper feed** — A NEMA8 stepper motor (200 steps/rev, microstepped to 3200 steps/rev via TMC2209) drives a knurled rubber feed roller that advances the media by one cell width (6 mm) per step group. A spring-loaded idler roller keeps media flat against the feed roller. An optical paper-present sensor (TCRT5000 reflective IR) detects media presence and out-of-media conditions.

5. **Line handling** — When the end of a line is reached (configurable 20–40 cells per line), the firmware:
   - Feeds forward by one line height (10 mm) to move the next row of dots into position under the head.
   - Returns the carriage to the left margin by reversing the feed roller.
   - For sheet media, a microservo (SG90) actuates a paper-tray release for manual page change; for continuous label tape, feeding continues.

6. **Modes**:
   - **Label mode** — emboss a single short line (≤ 25 cells) centered on a label tape strip, with auto-cut.
   - **Page mode** — emboss a full page of text (configurable rows × columns) onto cardstock.
   - **Continuous mode** — emboss an arbitrary-length stream from SD card, automatically advancing label tape.
   - **Demo mode** — emboss a pre-stored sample text (the Braille alphabet) on power-up for self-test.

7. **User interface**:
   - **OLED display** (SH1106, 128×64) shows the current text line in both visual characters and Braille dot pattern (a sighted helper can verify what will be embossed).
   - **3 buttons** — START (emboss), MODE (cycle Grade1/Grade2/8-dot/Label/Page), and FEED (manual paper advance).
   - **Rotary encoder** — adjusts embossing force / cell spacing on the fly.
   - **Buzzer** — audible feedback for emboss start/complete, out-of-paper, error.

8. **Output** — Embossed Braille on paper or label tape, physically raised, readable by touch. Standard Braille dimensions: dot height ~0.5 mm, dot diameter ~1.5 mm, cell spacing 6 mm horizontal × 4 mm vertical, line spacing 10 mm.

### Use Cases

| Application | How Glyph Press Helps |
|------------|------------------------|
| Household labeling | Emboss labels for kitchen, pantry, clothing, medication, appliances |
| File & folder labeling | Label file folders, binders, shelves for home/office organization |
| Medication identification | Emboss drug name, dosage, frequency on pill bottles or label tape |
| Book chapter marks | Emboss tab labels for Braille book chapter markers |
| Greeting cards | Add Braille personal messages to cards for blind recipients |
| Education | Teachers produce Braille worksheets, flashcards, labels on demand |
| Public signage | Libraries, offices, transit — emboss short Braille signage on demand |
| Emergency preparedness | Produce Braille evacuation/exit labels during disaster response |
| Field research | Anthropologists / aid workers produce Braille labels without specialized equipment |
| Independent living | Blind users self-label without relying on a sighted person |
| Braille literacy | Practice reading embossed Braille at home — improves literacy rates |
| Accessibility compliance | Small businesses produce Braille signage for ADA/local compliance cheaply |
| Maker projects | Emboss Braille on 3D-printed parts, PCB labels, enclosures |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              GLYPH PRESS                                          │
│                                                                                   │
│   ┌──────────────────────────────────────────────────────────────┐                │
│   │        RP2040 (Dual Cortex-M0+ @ 133 MHz)                     │                │
│   │        264 KB SRAM, 2 MB external QSPI flash                  │                │
│   │        30 GPIO, 2 × PIO state machines                        │                │
│   │                                                              │                │
│   │  ┌────────────────────────────────────────────────────────┐ │                │
│   │  │ Core 0: emboss_fsm — idle → translate → advance → fire │ │   I2C0 (GP4/GP5)│
│   │  │   line_done → next_line → idle                          │◄┼──────────────┐ │
│   │  ├────────────────────────────────────────────────────────┤ │              │ │
│   │  │ Core 0: braille_task — Grade1/Grade2/8-dot translation  │ │  ┌────────┐ │ │
│   │  │   UEB contraction trie, 60+ language tables            │ │  │SH1106  │ │ │
│   │  ├────────────────────────────────────────────────────────┤ │  │OLED    │ │ │
│   │  │ Core 0: feed_task — TMC2209 stepper → NEMA8 paper feed  │ │  │128×64  │ │ │
│   │  │   6 mm per cell, 10 mm per line                        │ │  │I2C 0x3C│ │ │
│   │  ├────────────────────────────────────────────────────────┤ │  └────────┘ │ │
│   │  │ Core 1: solenoid_task — 16× solenoid PWM via 8× DRV8833│ │              │ │
│   │  │   parallel dot firing, force control via duty cycle     │ │  ┌────────┐ │ │
│   │  ├────────────────────────────────────────────────────────┤ │  │TCRT5000│ │ │
│   │  │ Core 1: ui_task — buttons, encoder, buzzer, OLED render│◄┼──│IR paper│ │ │
│   │  ├────────────────────────────────────────────────────────┤ │  │sensor  │ │ │
│   │  │ Core 1: ble_task — UART → HC-05 BLE bridge (SPP)        │ │  └────────┘ │ │
│   │  │ Core 1: sd_task — microSD FAT32 text file read         │ │              │ │
│   │  └────────────────────────────────────────────────────────┘ │  ┌────────┐ │ │
│   │                                                              │  │microSD │ │ │
│   └──┬───────┬──────────┬──────────┬──────────┬─────────┬────────┘  │FAT32   │ │ │
│      │SPI0    │UART0     │PIO0      │I2C0      │GP/ADC   │GP/SPI     │socket  │ │ │
│      │QSPI    │BLE       │solenoids │OLED/sens │buttons  │SD card    └────────┘ │ │
│      ▼       ▼          ▼          ▼          ▼         ▼                      │ │
│  ┌────────┐┌────────┐┌──────────┐┌────────┐┌────────┐┌────────┐                │ │
│  │W25Q16  ││HC-05   ││8× DRV8833││SH1106  ││3 btns  ││microSD ││                │ │
│  │2MB ext ││BLE     ││dual H-   ││OLED    ││+ rotary││FAT32   ││                │ │
│  │flash   ││SPP     ││bridge    ││128x64  ││encoder ││text    ││                │ │
│  └────────┘└────────┘└────┬─────┘└────────┘└────────┘└────────┘                │ │
│                           │                                                       │ │
│                           ▼ 16 solenoid channels                                  │ │
│                   ┌─────────────────┐                                             │ │
│                   │  Embosser Head   │                                             │ │
│                   │  16× 5V push-    │                                             │ │
│                   │  pull solenoids  │                                             │ │
│                   │  (2 col × 8 dot)│                                              │ │
│                   │  hardened pins   │                                             │ │
│                   └────────┬─────────┘                                             │ │
│                            │                                                       │ │
│  Paper/label tape ─────────►    ◄──── NEMA8 stepper (TMC2209) paper feed roller   │ │
│                            │                                                       │ │
│  ┌────────────┐   ┌────────┐│┌────────────┐┌────────────┐                         │ │
│  │ TPS63020   │   │LiPo    │││ MCP73831  │││ DW01A/     │                         │ │
│  │ 3.3V       │◄──│2000mAh │││ charger   │││ FS8205A    │                         │ │
│  │ buck-boost │   │3.7V    │││ USB-C     │││ protection │                         │ │
│  └────────────┘   └────────┘└────────────┘└────────────┘                         │ │
│                                                                                   │
│   Mechanical: 3D-printed frame, embosser head mount, paper feed slot, rubber anvil│
│   Power:      LiPo 2000mAh → DW01A/FS8205A → TPS63020 3.3V → TLV70033 (sensors)  │
│   Charging:   USB-C → MCP73831 → LiPo                                             │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## Bill of Materials (BOM)

| Ref | Qty | Part | Manufacturer | MPN | Package | Unit USD | Source | Notes |
|-----|-----|------|-------------|-----|---------|----------|--------|-------|
| U1 | 1 | RP2040 | Raspberry Pi | RP2040 | QFN-56 | 1.00 | Mouser | Dual Cortex-M0+ 133MHz 264KB SRAM |
| U2 | 1 | W25Q16JVSN | Winbond | W25Q16JVSN | SOIC-8 | 0.30 | Digi-Key | 2MB external QSPI flash for Braille tables |
| U3 | 1 | HC-05 Bluetooth module | Generic | HC-05 | module | 2.50 | AliExpress | Classic Bluetooth SPP bridge (UART) |
| U4 | 1 | SH1106 OLED 1.3" | Generic | SH1106-1.3-128x64 | PCB | 3.50 | AliExpress | 128×64 monochrome OLED I2C display |
| U5 | 1 | TMC2209 v1.2 | Trinamic | TMC2209-Q1 | module | 3.50 | AliExpress | Stepper driver 2A stealthChop 256 microstep |
| U6 | 1 | TPS63020DSJR | Texas Instruments | TPS63020 | SON-14 | 3.90 | Digi-Key | 3.3V buck-boost 2A |
| U7 | 1 | TLV70033DDCR | Texas Instruments | TLV70033 | SOT-23-5 | 0.50 | Digi-Key | 3.3V LDO for sensor low-noise rail |
| U8 | 1 | MCP73831T-2ACI/MC | Microchip | MCP73831 | DFN-8 | 0.60 | Digi-Key | USB-C LiPo charger 4.2V 500mA |
| U9 | 1 | DW01A | Sileic | DW01A | SOT-23-6 | 0.10 | Digi-Key | Battery protection IC |
| U10 | 1 | FS8205A | Fairchild | FS8205A | SOT-23-6 | 0.20 | Digi-Key | Dual MOSFET for DW01A |
| U11 | 1 | DRV8833 | TI | DRV8833PW | TSSOP-16 | 1.80 | Digi-Key | Dual H-bridge for solenoid pairs |
| U12 | 1 | TCRT5000 | Vishay | TCRT5000 | module | 0.50 | AliExpress | Reflective IR sensor for paper-present detection |
| U13 | 1 | TP4056 | NanJing Top | TP4056 | SOP-8 | 0.20 | AliExpress | Alternative USB charger (backup option) |
| SOL1-16 | 16 | 5V push-pull solenoid | Generic | ZYE1-0530Z | 5V mini | 0.60 | AliExpress | 5mm stroke 3N force micro solenoid for embossing |
| MOT1 | 1 | NEMA8 stepper 20mm | Generic | NEMA8-20mm | NEMA8 | 8.00 | AliExpress | 200 step/rev 0.28A bipolar stepper for paper feed |
| SERVO1 | 1 | SG90 servo | TowerPro | SG90 | mini | 3.00 | AliExpress | Paper-tray release / cutter |
| LED1 | 1 | WS2812B | Worldsemi | WS2812B | 5050 | 0.20 | AliExpress | RGB LED status indicator |
| J1 | 1 | USB-C 2.0 receptacle | Amphenol | 12401610E4#2A | USB-C | 0.50 | Digi-Key | USB-C charging + USB-CDC |
| J2 | 1 | JST-PH 2-pin | JST | S2B-PH-K | 2mm | 0.20 | Digi-Key | Battery connector |
| J3 | 1 | 6-pin SWD header | Generic | SWD-6 | 1.27mm | 0.15 | Digi-Key | SWD programming header |
| J4 | 1 | microSD socket | Amphenol | 101-00559-82 | push-push | 0.80 | Digi-Key | microSD card slot (SPI mode) |
| SW1-3 | 3 | Tactile 6×6mm | Generic | TS-6x6 | 6x6mm | 0.15 | AliExpress | START / MODE / FEED buttons |
| ENC1 | 1 | Rotary encoder EC11 | ALPS | EC11E-S | panel | 1.20 | AliExpress | Embossing force / spacing adjust |
| BUZ1 | 1 | Piezo buzzer 5V | CUI | PS1240P02BT | 12mm | 0.40 | Digi-Key | Audible feedback |
| L1 | 1 | 2.2µH inductor 3A | Coilcraft | XAL4040-222MEB | 4x4mm | 0.80 | Digi-Key | Inductor for TPS63020 |
| Y1 | 1 | 12MHz crystal | Abracon | ABM3-12.000MHZ | 3.2x2.5mm | 0.30 | Digi-Key | RP2040 system crystal |
| MECH1 | 1 | Embosser head frame | custom | custom | 3D printed | 4.00 | 3D printed | Mount for 16 solenoids + pin guide |
| MECH2 | 1 | Paper feed assembly | custom | custom | 3D printed | 3.00 | 3D printed | Roller mount, idler, paper slot |
| MECH3 | 1 | Rubber anvil strip | custom | custom | silicone | 1.00 | hardware | Soft anvil for dot formation |
| BAT1 | 1 | LiPo 2000mAh 603048 | Generic | LP603048 | 60x34x8mm | 5.50 | BatteryJunction | 3.7V 2000mAh |
| MISC | 1 | Passives kit | Various | | mixed | 5.00 | Digi-Key | R/C/L 0402/0603 pull-ups, decoupling |
| MISC2 | 1 | Solenoid driver PCB | custom | custom | PCB | 4.00 | JLCPCB | Custom PCB for 8× DRV8833 + solenoid headers |
| SD1 | 1 | microSD 2GB | SanDisk | SD-2GB | card | 2.00 | Amazon | FAT32 text storage |
| | | | | | **Total** | **~$58** | | |

---

## Pin Assignments (RP2040 QFN-56)

| Pin | GPIO | Function | Direction | Notes |
|-----|------|----------|-----------|-------|
| 1 | GP0 | UART0 TX | out | → HC-05 RX (BLE bridge) |
| 2 | GP1 | UART0 RX | in | ← HC-05 TX |
| 3 | GP2 | SPI0 SCK | out | → W25Q16 flash + microSD clock |
| 4 | GP3 | SPI0 MOSI | out | → W25Q16 MOSI + microSD MOSI |
| 5 | GP4 | SPI0 MISO | in | ← W25Q16 MISO + microSD MISO |
| 6 | GP5 | SPI0 CS0 (flash) | out | W25Q16 CS (active low) |
| 7 | GP6 | SPI0 CS1 (SD) | out | microSD CS (active low) |
| 8 | GP7 | I2C0 SDA | bidir | SH1106 OLED + (future sensors) |
| 9 | GP8 | I2C0 SCL | out | SH1106 OLED |
| 10 | GP9 | STEPPER STEP | out | → TMC2209 STEP (PIO-driven) |
| 11 | GP10 | STEPPER DIR | out | → TMC2209 DIR |
| 12 | GP11 | STEPPER EN | out | → TMC2209 EN (active low) |
| 13 | GP12 | SERVO PWM | out | → SG90 servo (paper release/cut) |
| 14 | GP13 | PAPER SENSOR | in | TCRT5000 paper-present (ADC) |
| 15 | GP14 | BTN_START | in | START button (active low, pull-up) |
| 16 | GP15 | BTN_MODE | in | MODE button (active low, pull-up) |
| 17 | GP16 | BTN_FEED | in | FEED button (active low, pull-up) |
| 18 | GP17 | ENC_A | in | Rotary encoder A |
| 19 | GP18 | ENC_B | in | Rotary encoder B |
| 20 | GP19 | ENC_BTN | in | Rotary encoder push |
| 21 | GP20 | BUZZER | out | Piezo buzzer drive |
| 22 | GP21 | WS2812 | out | Status LED (PIO-driven) |
| 23 | GP22 | LED_STATUS | out | Green status LED |
| 24 | GP26 | ADC0 | in | Battery voltage divider |
| 25 | GP27 | SOLENoid_FORCE_ADC | in | Force feedback (optional) |
| 26 | GP28 | SPARE_ADC | in | Spare analog input |
| 27 | GP23-25 | QSPI flash | — | Internal boot flash (W25Q16 on same bus) |

### Solenoid Drive Matrix (8× DRV8833 → 16 solenoids)

Each DRV8833 drives 2 solenoids. 16 solenoids = 8 DRV8833 chips. Each solenoid is driven by a PWM pulse (20 ms ON, then OFF with flyback). The RP2040 drives the 16 enable/phase lines via a combination of GPIO and a 74HC595 shift register chain (to save GPIO):

| Shift Register | Output | DRV8833 # | Solenoid Dot | Description |
|----------------|--------|-----------|-------------|-------------|
| 74HC595 #1 | Q0-Q7 | DRV8833 1-4 | Dots 1-8 (col A) | Column A dots 1-8 |
| 74HC595 #2 | Q0-Q7 | DRV8833 5-8 | Dots 1-8 (col B) | Column B dots 1-8 |

The RP2040 clocks the shift registers via SPI1 (GP10/GP11/GP12 reconfigured or a second PIO SM), then latches and fires all solenoids simultaneously for one cell.

**Shift register pins:**
- GP19 → 74HC595 SER (data)
- GP20 → 74HC595 SRCLK (shift clock)
- GP21 → 74HC595 RCLK (latch)

*(These override the encoder/buzzer pins above when embossing — handled by task scheduling, not simultaneous use.)*

---

## Power Architecture

```
USB-C 5V ────► MCP73831 ────► LiPo 3.7V 2000mAh ────► DW01A/FS8205A protection
                  │                                      │
                  └─────── ► (charging)                   │
                                                         ▼
                                                    TPS63020
                                                    buck-boost
                                                    3.3V / 2A
                                                         │
                                    ┌────────────────────┼────────────────────┐
                                    │                    │                    │
                                    ▼                    ▼                    ▼
                              RP2040 + flash       DRV8833 bank           TLV70033
                              (3.3V, ~80mA)       (3.3V logic, 5V sol)   3.3V LDO
                                                    │                 (sensors, OLED)
                                                    ▼                    │
                                              Solenoid 5V rail            ▼
                                              (from LiPo direct,       I2C bus
                                               via DRV8833 VMOT)         (OLED, IR sensor)
```

- **Solenoid power**: 16 solenoids at 5V, ~300mA each = up to 4.8A peak. But only one cell fires at a time (2-8 solenoids active), so peak is ~2.4A. Sourced directly from LiPo (3.0-4.2V) via DRV8833 VMOT pin. The LiPo can deliver 2C = 4A burst, sufficient.
- **MCU + logic**: 3.3V from TPS63020, ~150mA total.
- **Battery life**: 2000mAh at ~300mA average embossing draw = ~5 hours of continuous embossing, or ~2000 cells (practically weeks of intermittent use).
- **Charging**: USB-C 5V → MCP73831 → LiPo. ~4 hours full charge.

---

## Firmware Architecture

The firmware uses the RP2040's dual-core architecture:
- **Core 0**: Emboss state machine, Braille translation, stepper paper feed, BLE/SD text input
- **Core 1**: Solenoid driver, UI (OLED, buttons, encoder, buzzer), BLE UART protocol handler

### State Machine (Core 0)

```
IDLE ──(text received)──► TRANSLATE ──► EMBOSS_CELL ──► ADVANCE ──► EMBOSS_CELL ...
                                                        │
                                                        └──(line end)──► LINE_FEED ──► EMBOSS_CELL
                                                        │
                                                        └──(text end)──► DONE ──► IDLE
```

### Braille Translation Engine

The `braille.c` module implements:
- **Grade 1**: Direct character→dot-pattern lookup from a 256-byte table (one byte per character, bits 0-7 = dots 1-8).
- **Grade 2 (UEB)**: A trie-based contraction matcher. Input text is scanned left-to-right; the longest matching contraction at each position is applied. ~180 contractions covering common English words and letter groups. The trie is stored in flash as a flat array of nodes (4 KB).
- **8-dot**: Passes through Unicode Braille patterns (U+2800-U+28FF) directly to the embosser without translation.
- **Language selection**: 6 language tables stored in external W25Q16 flash (each ~1 KB), selectable via MODE button.

### Embossing Physics

- **Dot formation**: The solenoid drives a 1.5mm hardened steel pin into the paper (80-160 gsm) against a silicone rubber anvil (Shore 40A). The pin displaces the paper fibers, creating a raised dome ~0.5mm high on the front face.
- **Dwell time**: 20 ms per dot (solenoid fully extended, then released). A cell of up to 8 dots fires in parallel (all solenoids active simultaneously), so one cell takes ~25 ms.
- **Feed**: 6mm per cell at 3200 steps/rev = ~53 steps per cell. At 1000 steps/sec, that's ~53 ms per cell.
- **Throughput**: ~25ms emboss + ~53ms feed = ~78ms/cell = ~13 cells/sec theoretical. Practical: ~8-10 cells/sec with acceleration/deceleration.

---

## Assembly Guide

### What you need

1. Custom PCB (see `schematic/` for KiCad files — order from JLCPCB ~$4 for 5 boards)
2. 3D-printed embosser head and frame (see `docs/` for STL files)
3. Soldering iron, solder, flux
4. Small screwdriver set, M2/M3 hardware
5. PC with Python 3 for the companion script
6. ST-Link or Picoprobe for flashing firmware

### Step-by-step

1. **PCB assembly**: Solder the RP2040, W25Q16 flash, TPS63020, MCP73831, DW01A, FS8205A, and passives. Use a stencil + hot plate for the QFN packages.
2. **Solenoid driver board**: Solder 8× DRV8833 on the solenoid driver PCB. Connect 16 solenoid connectors.
3. **Mechanical assembly**:
   - Mount the 16 solenoids in the 3D-printed embosser head (2 columns of 8).
   - Insert hardened steel pins (1.5mm diameter, 15mm long) into each solenoid plunger.
   - Mount the NEMA8 stepper with the feed roller in the paper feed assembly.
   - Install the silicone rubber anvil strip below the embosser head.
   - Mount the SG90 servo for paper release.
   - Install the TCRT5000 paper-present sensor in the paper slot.
4. **Wiring**: Connect the solenoid driver board to the main PCB via ribbon cable. Connect the stepper (TMC2209), servo, OLED, and battery.
5. **Flash firmware**: Connect a Picoprobe (or use a Pi Pico as Picoprobe) to the SWD header. Run `make flash` from the `firmware/` directory.
6. **Load Braille tables**: The Grade 2 contraction table and language tables are pre-flashed into W25Q16. Use `scripts/load_tables.py` to update them if needed.
7. **Test**: Power on, the OLED shows "Glyph Press Ready". Press MODE to cycle modes. Send text via `scripts/glyph_send.py`.

---

## API Reference

### BLE Serial Protocol (HC-05 SPP)

The HC-05 module presents a classic Bluetooth serial port (SPP). Connect from a phone (Android: "Serial Bluetooth Terminal" app; iOS: "Bluetooth Terminal" app) or PC. Baud rate: 9600, 8N1.

**Commands** (sent as ASCII lines, terminated with `\n`):

| Command | Description |
|---------|-------------|
| `TEXT <string>` | Queue text for embossing (max 4096 chars) |
| `MODE G1` | Set Grade 1 (uncontracted) mode |
| `MODE G2` | Set Grade 2 (UEB contracted) mode |
| `MODE G8` | Set 8-dot Unicode Braille mode |
| `MODE LABEL` | Set label mode (single line, centered) |
| `MODE PAGE` | Set page mode (multi-line) |
| `LANG <code>` | Set language (en, fr, es, de, pt, ar, hi, zh) |
| `FORCE <0-9>` | Set embossing force (0=lightest, 9=firmest) |
| `CPL <n>` | Set cells per line (20-40) |
| `FEED <mm>` | Feed paper by N mm |
| `START` | Begin embossing queued text |
| `STOP` | Cancel current emboss job |
| `STATUS` | Query device status (returns `OK <state> <mode> <cells_done> <cells_total>`) |
| `TEST` | Emboss the Braille alphabet (self-test) |
| `HELP` | List available commands |

### SD Card File Format

Place a `.txt` file (UTF-8) on a FAT32-formatted microSD card. The firmware reads the first file found (alphabetical order) and embosses it. The file must be plain text, max 32 KB. Lines are separated by `\n`. The firmware wraps long lines at the configured cells-per-line setting.

### Python Companion Script

```python
# scripts/glyph_send.py
# Usage: python glyph_send.py --port /dev/tty.GlyphPress --text "Hello World"
#        python glyph_send.py --port COM5 --file label.txt --mode G2
```

See `scripts/glyph_send.py` for full usage.

---

## Usage Example

```
$ python scripts/glyph_send.py --port /dev/tty.GlyphPress --text "MORNING MEDS" --mode LABEL

Connecting to Glyph Press on /dev/tty.GlyphPress ...
Connected. Mode: LABEL, Language: en, Force: 5
Sending: "MORNING MEDS"
Translating (Grade 2): MORNING→morn, MEDS→meds
Embossing 12 cells ...
████████████ 100%
Done. Please tear off label.
```

The embossed label tape reads (in Braille):
```
⠍⠕⠗⠝⠬⠍⠑⠙⠎
```
(MORNING in contracted UEB: m-o-r-n-ing; MEDS: m-e-d-s)

---

## Technical Specifications

| Parameter | Value |
|-----------|-------|
| MCU | RP2040 (dual Cortex-M0+ @ 133 MHz) |
| Flash | 2 MB external (W25Q16) + 16 MB internal boot flash |
| SRAM | 264 KB |
| Connectivity | Bluetooth Classic SPP (HC-05), USB-CDC, SD card |
| Embossing speed | ~8-10 cells/sec |
| Cell spacing | 6 mm horizontal, 4 mm vertical (standard Braille) |
| Line spacing | 10 mm |
| Dot height | ~0.5 mm (adjustable) |
| Dot diameter | 1.5 mm |
| Media width | 25-50 mm paper or label tape |
| Media thickness | 80-160 gsm paper / 0.15mm label tape |
| Cells per line | 20-40 (configurable) |
| Lines per page | 25-28 |
| Battery | 2000mAh LiPo, ~5h continuous emboss |
| Charging | USB-C 5V, ~4h full |
| Dimensions | 120 × 70 × 40 mm (pocket-sized) |
| Weight | ~180g (with battery) |
| Cost | ~$58 (parts only) |

---

## License

MIT — build it, sell it, improve it. Braille is a human right.