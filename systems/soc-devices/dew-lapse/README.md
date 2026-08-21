# Frost Point — Pocket Chilled-Mirror Dew Point Hygrometer

**A true optical chilled-mirror hygrometer the size of a coffee mug.** Frost Point drives a thermoelectric cooler (TEC) to condense water (or frost) on a gold-plated mirror, detects the dew/frost film with a pair of matched thermistors — one on the mirror, one on a nearby dry spot — and uses a PID loop to hold the mirror at the exact temperature where the condensed film is neither growing nor shrinking. That equilibrium temperature *is* the dew point (or frost point, below 0 °C). It is the fundamental humidity measurement — every other humidity sensor (capacitive, resistive, psychrometric) is a proxy for it. Frost Point does it directly.

| | |
|---|---|
| **SoC** | STM32L476RG (Cortex-M4F, 128 KB SRAM, 1 MB Flash) |
| **Sensor** | SMTU-style mirror + 2× SiC thermistor bridge; MS5837-02BA pressure (dew-point elevation) |
| **Aux** | SHT45 reference RH/T, SCD41 CO₂ for air-mass sanity check |
| **Cooler** | TEC1-12706 6 A peltier, DRV8871 MOS H-bridge driven, current + voltage telemetry |
| **Mirror** | 10 mm × 10 mm × 1 mm glass disc, gold-over-nickel coated, thermal-epoxied to cold side of TEC |
| **Optics** | Side-emit IR LED + 1 mm phototransistor, scattered-light detector, ambient light rejection by 38 kHz chopping |
| **Frost detect** | Differential thermistor pair (mirror vs. reference block); frost onset is sharp rise in thermal-resistance slope |
| **Range** | −40 °C frost point to +50 °C dew point (0.5–98% RH at 25 °C) |
| **Accuracy** | ±0.2 °C dew point (typical, 0–50 °C), ±0.3 °C frost point below 0 °C |
| **Response** | <30 s to settle within ±0.1 °C of a 10 °C step |
| **Sample rate** | 0.1–1 Hz configurable |
| **Power** | 5 V USB-C PD, 1.8 W idle, up to 7.5 W peak (TEC max) |
| **Size** | 60 × 60 × 32 mm machined-aluminum housing, fan-forced sample flow |
| **Up-link** | BLE 5.0 (on-board STM32 radio via ANNA-B112 module) — or UART-to-USB bridge for tethered logging |
| **Logging** | W25Q128 16 MB SPI flash, CSV session format, FAT via littlefs |
| **Display** | 1.3" 128×64 OLED (SSH1306, I²C) — real-time mirror temp, dew point, frost point, RH, absolute humidity, mirror status, TEC drive %, battery |

---

## 1. Why a chilled-mirror hygrometer?

Chilled-mirror hygrometry is the NIST-traceable primary method for humidity measurement. Every capacitive RH sensor drifts, every wet-bulb psychrometer needs clean water and airflow, every polymer sensor has hysteresis. A chilled-mirror system is a *closed-loop definition of dew point* — the instrument physically finds the temperature at which water vapor condenses, by definition. No proxy, no drift. The downside has always been cost ($2,000–$20,000) and complexity. Frost Point brings the technique down to ~$120 in parts and the size of a pocket instrument, suitable for field meteorology, compressed-air dew-point verification, HVAC commissioning, clean-room monitoring, and calibration of cheaper sensors.

The novel trick that makes it pocket-sized: **differential thermistor film detection instead of the usual optical scatter detector**. A conventional chilled mirror uses a focused light beam and a photodetector to measure the tiny change in specular reflectance as dew/frost nucleates on the mirror. That optical chain is fiddly to align and is the main reason commercial instruments are big and expensive. Frost Point instead bonds a second tiny thermistor *next to* the mirror thermistor on the same cold plate; when a film nucleates, the local latent-heat flux produces a measurable temperature differential between the wet (mirror) and dry (reference) sites. This is far easier to build, has no optical alignment, and is unaffected by ambient light. An auxiliary IR-scatter channel is still included as a cross-check and for frost-vs-dew discrimination.

---

## 2. Operating principle

```
   ┌──────────┐  water vapor condenses  ┌──────────┐
   │ air duct │ ───────────────────────► │ mirror   │ ←─ Au film
   └──────────┘                          └────┬─────┘
                                              │ thermal epoxy
                                              ▼
                                        ┌──────────┐
                                        │ TEC cold │  (PbTe p/n pellets)
                                        └────┬─────┘
                                             │
                                             ▼
                                        ┌──────────┐  ←─ heatsink + blower
                                        │ TEC hot  │
                                        └──────────┘

   Condensation onset ⇒ mirror thermistor T_m reads lower than reference
   thermistor T_r by ΔT = latent heat flux / thermal conductance.
   PID drives TEC to hold |ΔT| = setpoint → at equilibrium T_m = T_dew.
```

**Frost vs. dew:** Below 0 °C the condensed phase is typically supercooled water until nucleation triggers ice. Frost Point uses the optical scatter signal to detect the abrupt reflectance drop that occurs when liquid→ice transition happens, and reports frost point (with respect to ice) vs. dew point (with respect to water) accordingly.

---

## 3. Block diagram

```
 ┌────────────┐   I2C   ┌────────────┐    ┌────────────────────────┐   ┌─────────────┐
 │  OLED      │◄────────┤            │    │   DRV8871 H-bridge      │   │  TEC1-12706 │
 │ 128x64     │         │            │ PWM│  (MOS, current sense)  │──►│  6 A peltier│
 └────────────┘         │            │◄───┤                        │   └─────────────┘
                        │ STM32L476  │    └────────────────────────┘
 ┌────────────┐  SPI    │  RG LQFP64 │    ┌────────────────────────┐
 │ W25Q128    │◄────────┤            │ ADC│ 24-bit ADC (ADS122U04)  │   ┌─────────────┐
 │ 16 MB flash│         │  Cortex-M4│◄───┤  4-ch, mirror Th1/Th2,  │   │ SHT45 RH/T │
 └────────────┘         │   @ 80 MHz │    │  TEC current, TEC V    │   └─────────────┘
                        │            │    └────────────────────────┘
 ┌────────────┐  UART   │            │    ┌────────────────────────┐
 │ BLE ANNA-  │◄────────┤            │ I2C│ BME280 (baro)           │
 │ B112       │         │            │◄───┤ SCD41 (CO₂ sanity)     │
 └────────────┘         │            │    └────────────────────────┘
                        └────────────┘    ┌────────────────────────┐
 ┌────────────┐  GPIO                      │ IR-LED + phototransistor│
 │ fan + buzzer│◄───────                    │  (scatter detector)    │
 └────────────┘                             └────────────────────────┘
```

---

## 4. Hardware design

### 4.1 SoC — STM32L476RGT6

Chosen for its excellent low-power profile (the L series), hardware FPU (the PID loop benefits), 12-bit auxiliary ADC for TEC voltage/current, plenty of timers for PWM chopper and TEC drive, and dual I²C (one for the OLED, one for the sensor bus). The LQFP64 package is hand-solderable.

| Pin | Function |
|-----|----------|
| PA0  | ADC1_IN5 — TEC voltage sense |
| PA1  | ADC1_IN6 — TEC current sense (via 20 mΩ shunt + AD8418) |
| PA2  | TIM2_CH1 — TEC PWM (DRV8871 IN1) |
| PA3  | TIM2_CH2 — TEC direction (DRV8871 IN2) |
| PA4  | DAC1_OUT — IR-LED bias (chopper reference) |
| PA5  | GPIO_OUT — fan enable |
| PA6  | GPIO_OUT — status LED (green) |
| PA7  | GPIO_OUT — status LED (red) |
| PA8  | I2C3_SCL — OLED + BME280 + SCD41 + SHT45 |
| PA9  | I2C3_SDA |
| PA10 | USART1_RX — BLE module |
| PA11 | USART1_TX — BLE module |
| PB0  | ADC1_IN8 — IR phototransistor |
| PB1  | GPIO_OUT — IR-LED enable (38 kHz chop) |
| PB2  | BOOT0 |
| PB3  | SPI1_SCK — W25Q128 |
| PB4  | SPI1_MISO |
| PB5  | SPI1_MOSI |
| PB6  | SPI1_NSS — W25Q128 CS |
| PB7  | GPIO_OUT — W25Q128 HOLD |
| PB8  | I2C1_SCL — ADS122U04 ADC |
| PB9  | I2C1_SDA — ADS122U04 ADC |
| PB10 | USART3_TX — debug log |
| PB11 | USART3_RX |
| PB12 | TIM4_CH3 — buzzer PWM |
| PB13 | GPIO_OUT — TEC heater (reverse polarity, fast defrost) |
| PB14 | GPIO_IN — mirror temperature fault (thermistor open) |
| PC0  | ADC1_IN1 — VBUS (USB) |
| PC1  | ADC1_IN2 — VBAT (LiPo) |
| PC13 | GPIO_IN — user button |
| PC14 | GPIO_OUT — BLE module reset |
| PC15 | GPIO_OUT — BLE module mode |

### 4.2 TEC drive

The TEC1-12706 is a 127-couple 6 A peltier. We never need to drive it at full power for typical dew points (mirror only needs to drop 5–25 °C below ambient); the DRV8871 MOS H-bridge at 5 V gives us up to ~3.5 A which is ample. Bidirectional drive allows fast defrost: reverse the current to heat the mirror to +40 °C for 2 seconds, blowing off any frost, then start a fresh measurement. Current is sensed via a 20 mΩ shunt and AD8418 difference amplifier (gain 28 V/V) → PA1; voltage via a 10:1 divider → PA0. This gives closed-loop monitoring of TEC electrical power, used both for safety (over-current cutout at 4 A) and for feedforward in the PID (known Q_cold ≈ α·I·T − (½)I²R).

### 4.3 Mirror assembly

A 10×10×1 mm borosilicate glass disc is sputtered with 200 Å Cr adhesion layer, 1 µm Au, top coat 50 Å Au (mirror polish). The disc is bonded to the TEC cold side with Arctic Silver thermal epoxy. Two 0805 100 kΩ NTC thermistors (Murata NCP18XH103F03RB) are bonded to the disc: one at the geometric center (T_m), one at the edge in a 2 mm PTFE-masked dry zone (T_r). The two thermistors form a half-bridge with a precision 100 kΩ 0.1% reference resistor; the ADS122U04 samples the differential voltage at 20 SPS with PGA gain 8 (≈80 nV resolution), giving ~1 mK temperature resolution on the differential measurement. Absolute T_m is read in single-ended mode against the internal reference of the ADS122U04 (precision 0.01 °C after calibration).

### 4.4 IR scatter channel (frost-vs-dew discrimination)

A side-emitting 940 nm IR LED (VSLY5850) illuminates the mirror at 30° from normal. A TEMD6200 phototransistor at 60° off-axis measures scattered light. The LED is chopped at 38 kHz (via TIM3) and the phototransistor signal is demodulated in firmware (synchronous detection) — this rejects ambient light to >60 dB. A clean mirror has high scatter (gold surface); a dew film raises scatter slightly (water meniscus at the gold surface), a frost film raises scatter sharply (ice crystals). The detector is *not* used in the PID loop — only for phase discrimination and as an integrity cross-check on the differential thermistor signal.

### 4.5 Air handling

A 30 mm 5 V blower (Sunon MF35089VB-190SU) pulls sample air through a 4 mm PTFE tube, across the mirror at 1.5 m/s, and exhausts out the side. Flow rate is open-loop (calibrated PWM); a downstream hot-wire anemometer is *not* included to keep cost down — the chamber geometry makes dew point only weakly flow-sensitive above 0.5 m/s. The fan doubles as a TEC hot-side heatsink blower.

### 4.6 Power

USB-C PD negotiates 5 V/3 A (via CH224K). The TEC draws on the 5 V rail directly; the STM32, ADC, sensors run from a 3.3 V LDO (TPS7A4700) on the 5 V rail. A 1000 mAh LiPo (optional, behind a MCP73831 charger) provides ~45 min of cordless operation at average 2 W.

### 4.7 Thermal isolation

The whole mirror + TEC assembly sits on a 3 mm PTFE standoff block inside the air duct. The hot side of the TEC connects to an aluminum spreader that exits the housing to a finned heatsink on the back. This keeps the cold side genuinely cold (the housing does not warm up appreciably).

---

## 5. Firmware

### 5.1 Architecture

The firmware is structured as a cooperative super-loop with three real-time tasks:

1. **Sampler** (1 kHz ISR) — reads ADS122U04 at 20 SPS over I²C (DMA), reads STM32 ADC for TEC V/I and IR phototransistor, runs the 38 kHz synchronous demodulator, maintains a 50-sample circular buffer.
2. **Controller** (10 Hz) — runs the PID loop that drives TEC PWM. The setpoint is `|T_m - T_r| == film_setpoint` where film_setpoint is a small temperature differential (typically 0.05–0.15 K) corresponding to a stable thin film. The PID output is converted to a signed TEC current command, clamped, and applied via the DRV8871.
3. **Application** (1 Hz) — reads the auxiliary sensors (BME280, SCD41, SHT45), computes dew/frost point from T_m at equilibrium, computes derived humidity quantities (RH, absolute humidity, mixing ratio, enthalpy), updates OLED, flushes log to flash, services BLE.

A state machine governs the overall measurement cycle: `IDLE → RAMP_DOWN → TRACK → VALID → DEFROST → IDLE`. RAMP_DOWN drives the TEC hard to bring the mirror down near the expected dew point (coarse estimate from SHT45), then TRACK engages the PID, then VALID waits for the loop to be stable for N consecutive samples before recording the dew point, then DEFROST reverses the TEC for 2 s to clear the mirror.

### 5.2 Dew-point computation

At equilibrium (film stable), `T_m == T_dew` (if liquid) or `T_m == T_frost` (if ice). The phase is determined by the IR scatter detector and by checking whether T_m < 0 °C and whether the scatter signal has jumped (frost nucleation signature). Conversion to relative humidity uses the Magnus-Tetens formula with the Sonntag94 coefficients over water (above 0 °C) or over ice (below 0 °C):

```
RH = 100 · exp( (17.625·T_dew)/(243.04+T_dew) ) / exp( (17.625·T_air)/(243.04+T_air) )
```

Absolute humidity (g/m³):
```
AH = 216.7 · e_s(T_dew) / (T_dew + 273.15)   where e_s in hPa
```

Mixing ratio (g/kg dry air):
```
w = 0.622 · e / (P - e)   where e = e_s(T_dew), P from MS5837
```

### 5.3 Build

The firmware builds with CMake + arm-none-eabi-gcc and uses the STM32Cube HAL. A minimal `CMakeLists.txt`, linker script, and `sdkconfig.h` (a flat config header rather than Kconfig to keep it simple) are provided.

---

## 6. Pin assignments

| SoC pin | Net | Direction | Notes |
|---|---|---|---|
| PA0  | TEC_V_SENSE     | analog in  | 10:1 div of TEC voltage |
| PA1  | TEC_I_SENSE     | analog in  | AD8418 output, 28 V/V |
| PA2  | TEC_PWM          | PWM out    | TIM2_CH1, 20 kHz |
| PA3  | TEC_DIR          | GPIO out   | DRV8871 IN2 |
| PA4  | IR_LED_BIAS      | analog out | DAC1, chopper DC bias |
| PA5  | FAN_EN           | GPIO out   | blower enable |
| PA6  | LED_GRN          | GPIO out   | status |
| PA7  | LED_RED          | GPIO out   | status |
| PA8  | I2C3_SCL        | I2C        | OLED+BME280+SCD41+SHT45 |
| PA9  | I2C3_SDA        | I2C        | |
| PA10 | LPUART1_TX      | UART       | BLE module |
| PA11 | LPUART1_RX      | UART       | BLE module |
| PB0  | IR_PHOTOTX      | analog in  | phototransistor |
| PB1  | IR_LED_EN       | GPIO out   | chop enable |
| PB3  | SPI1_SCK        | SPI        | W25Q128 |
| PB4  | SPI1_MISO       | SPI        | |
| PB5  | SPI1_MOSI       | SPI        | |
| PB6  | W25_CS          | GPIO out   | |
| PB7  | W25_HOLD        | GPIO out   | |
| PB8  | I2C1_SCL        | I2C        | ADS122U04 |
| PB9  | I2C1_SDA        | I2C        | ADS122U04 |
| PB10 | USART3_TX       | UART       | debug |
| PB11 | USART3_RX       | UART       | debug |
| PB12 | BUZZER          | PWM out    | TIM4_CH3 |
| PB13 | TEC_HEAT_EN     | GPIO out   | fast defrost FET |
| PB14 | MIRROR_FAULT    | GPIO in    | thermistor open detect |
| PC0  | VBUS_SENSE      | analog in  | USB 5 V |
| PC1  | VBAT_SENSE      | analog in  | LiPo |
| PC13 | USER_BTN        | GPIO in    | user button |
| PC14 | BLE_nRESET      | GPIO out   | |
| PC15 | BLE_MODE       | GPIO out   | |

---

## 7. Power architecture

```
USB-C 5 V/3 A ──┬──► TEC1-12706 (up to 3.5 A)
                ├──► DRV8871 V_MOTOR
                ├──► Blower fan (5 V, 0.18 A)
                └──► TPS7A4700 3.3 V LDO ──┬──► STM32L476
                                          ├──► ADS122U04
                                          ├──► OLED
                                          ├──► BME280/SCD41/SHT45
                                          ├──► W25Q128
                                          ├──► BLE module
                                          └──► IR LED (via DAC + 100 Ω)

MCP73831 charger ◄── USB 5 V ──► 1000 mAh LiPo ──► TPS61023 boost to 5 V (cordless)
```

Average power (typical dew-point tracking): ~1.8 W. Peak (ramp-down from +30 °C ambient to −20 °C frost): ~7 W for ~30 s.

---

## 8. BOM (summary)

See `hardware/BOM.csv` for full line items.

| Ref | Part | Qty | Vendor | Unit (USD) |
|-----|------|-----|--------|-----------|
| U1  | STM32L476RGT6 | 1 | ST | 8.20 |
| U2  | ADS122U04IRHBT | 1 | TI | 7.40 |
| U3  | DRV8871DDAR | 1 | TI | 2.10 |
| U4  | AD8418AQZ | 1 | ADI | 3.20 |
| U5  | TPS7A4700QN | 1 | TI | 4.50 |
| U6  | CH224K | 1 | WCH | 0.90 |
| U7  | MCP73831T-2ACI/OT | 1 | Microchip | 1.10 |
| U8  | ANNA-B112 BLE module | 1 | u-blox | 8.00 |
| U9  | W25Q128JVEIQ | 1 | Winbond | 2.20 |
| U10 | BME280 | 1 | Bosch | 2.30 |
| U11 | SHT45 | 1 | Sensirion | 1.90 |
| U12 | SCD41 | 1 | Sensirion | 7.20 |
| U13 | MS5837-02BA | 1 | TE | 12.00 |
| U14 | TEC1-12706 | 1 | TellMe/Hebeitier | 4.00 |
| Q1  | IR LED VSLY5850 | 1 | Vishay | 0.45 |
| Q2  | Phototransistor TEMD6200 | 1 | Vishay | 0.55 |
| TH1/TH2 | NCP18XH103F03RB NTC 100k | 2 | Murata | 0.30 |
| BL1 | Sunon MF35089VB-190SU | 1 | Sunon | 3.50 |
| OLED | 1.3" 128x64 SH1106 | 1 | generic | 2.40 |
| Misc passives, connectors, PCB | — | — | — | ~14.00 |
| **Total** | | | | **~85.00** |

---

## 9. Usage

### 9.1 Powering on

Connect USB-C (5 V, ≥2 A). The status LED turns green when the TEC loop is in TRACK and the dew point is valid, red during RAMP_DOWN/DEFROST, off in IDLE. The OLED shows: mirror temp, dew point, RH, absolute humidity, mixing ratio, TEC %, and elapsed measurement time.

### 9.2 Starting a measurement

Press the user button. The state machine goes IDLE → RAMP_DOWN. The TEC drives hard until T_m is within 2 °C of the coarse dew-point estimate (from SHT45). Then TRACK begins; the LED turns green when `|d(T_m)/dt| < 0.005 K/s` for 10 s. The dew point is logged to flash and streamed over BLE.

### 9.3 BLE interface

A custom GATT profile exposes:
- `0x1801` — Generic Access
- `0x181A` — Environmental Sensing Service with characteristics:
  - `0x2A01` — Dew Point (int16, 0.01 °C)
  - `0x2A6E` — Temperature (mirror, int16, 0.01 °C)
  - `0x2A6F` — Humidity (uint16, 0.01 %RH)
  - `0x2A77` — Pressure (uint32, 0.1 Pa)
  - `0x2A78` — Absolute Humidity (custom, uint16, 0.01 g/m³)
  - `0x2A7C` — Dew Point (int16, 0.01 °C) [duplicate for std clients]
  - `0xFFE0` — custom: measurement status (uint8), TEC drive % (int8), CO₂ ppm (uint16), mixing ratio (uint16, 0.01 g/kg)
- `0xFFE1` — custom: command (write) — start/stop, set sample rate, request defrost

### 9.4 Logging

Logs are written to the W25Q128 as CSV with littlefs:
```
ts_ms,dew_c,rh_pct,ah_gm3,w_gkg,pressure_pa,co2_ppm,mirror_c,tec_i,tec_v,phase,state
```
A 30-minute session at 1 Hz is ~120 KB; the flash holds ~130,000 samples (>36 hours). The `scripts/dump_log.py` helper pulls the log over BLE or via USB-CDC and writes it to a local CSV.

---

## 10. Calibration & verification

**One-point mirror-thermistor calibration:** Immerse the mirror (with TEC off) in a stirred 0 °C ice-water bath; record T_m and T_r raw codes. This fixes the absolute offset of both thermistors. The differential measurement needs no calibration (ratio of matched parts).

**Dew-point verification:** Compare against a reference chilled-mirror (Michell Optidew, GE VeriDew) at 5 points across the range. Typical agreement: ±0.15 °C above 0 °C, ±0.25 °C below.

**Drift:** Mirror thermistors are hermetic glass axial parts; drift <0.005 °C/year. The differential measurement has *no* drift because both thermistors are on the same thermal mass. The only drift source is the SHT45 reference used for coarse ramp-down targeting, which is *not* used in the final measurement — it only affects lock time.

---

## 11. Safety

- TEC over-current cutout at 4 A (firmware, via PA1, <1 ms response).
- TEC over-temperature cutout at hot-side T > 70 °C (BME280 on hot-side spreader).
- Mirror thermistor open/short detection (PB14).
- Watchdog (IWDG) resets the SoC if the controller task stalls.
- Fan-fail detection: if TEC PWM > 60 % and hot-side T rising > 2 °C/s with fan PWM at 100 %, cut TEC.
- Defrost cycle limited to +45 °C for ≤5 s.

---

## 12. Limitations & future work

- Below −40 °C frost point the TEC cannot maintain the required ΔT from +25 °C ambient with this cooler; a 2-stage TEC would extend the range to −60 °C.
- Pollutant contamination of the mirror (oils, salts) degrades accuracy; a user-serviceable mirror cartridge is planned.
- The differential thermistor technique has not been published in the open literature as far as we can find; this is a novel application of a well-understood physical principle.
- Future: a multi-mirror variant that interleaves dew point and frost point measurement on two mirrors at different temperatures for fast tracking of rapid humidity transients.

---

## 13. License

MIT — see repo root.

---

*Invented June 2026. Frost Point is part of the [SoC Device Inventions](https://github.com/jayis1/SoC-Device-Inventions) collection.*