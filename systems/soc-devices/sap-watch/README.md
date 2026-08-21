# Sap Watch

**A solar-powered, trunk-mounted sap-flow sensor that measures real-time xylem water transport in trees using the heat-pulse method — a precision heater probe and two matched thermistors compute sap flux velocity, daily transpiration, and drought-stress anomalies, reporting over LoRaWAN for forestry research, orchard irrigation scheduling, and climate-ecology monitoring.**

---

## What It Does

The Sap Watch is a scientific instrument that clamps onto a tree trunk and continuously measures how fast sap is flowing upward through the xylem — the direct physiological signal of transpiration. It uses the **heat-ratio method (HRM)**: a short, precisely-timed heat pulse is released from a central needle, and two thermistors located 5 mm upstream and 10 mm downstream of the heater record the temperature rise. The ratio of upstream-to-downstream temperature maxima directly yields the **sap flux velocity** (cm h⁻¹), which — combined with sapwood area — gives whole-tree water use (litres per hour).

This replaces expensive lab dataloggers (a single Campbell Scientific setup with TDP probes costs $2,500+) with a sub-$120 autonomous node that streams data over LoRaWAN. A researcher can deploy a mesh of 20+ Sap Watch units across a forest stand, orchard, or vineyard and build a real-time transpiration map.

- **3-needle heat-pulse probe** — 30 mm stainless-steel needles: a central constantan heater coil (~40 Ω, 2 s pulse at 6 V → ~1.8 J) flanked by two matched 10 kΩ NTC thermistors embedded 5 mm above and 10 mm below the heater in the xylem
- **Precision analog front-end** — 24-bit delta-sigma ADC (ADS122U04) multiplexed across the two thermistors, ratiometric measurement with 1,000× gain stage, 0.001 °C resolution — enough to resolve the 0.05–2.0 °C heat-pulse signal
- **On-device sap-flux computation** — heat-ratio algorithm (Marshall/Clearwater correction for wounding), 5 min measurement cycle, daily transpiration integration
- **Drought-stress detection** — compares predawn sap flow (potential evapotranspiration proxy) and midday flux to historical baselines; flags stomatal-closure anomalies (early water stress, days before visible wilting)
- **Environmental sensors** — SHT45 trunk-air temperature/humidity, DS18B20 sapwood temperature reference, TSL2591 light (for PAR proxy / canopy shading context)
- **LoRaWAN uplink** — STM32WL55JC's integrated sub-GHz radio, 868 MHz (EU) / 915 MHz (US), +14 dBm, adaptive data rate; reports every 15 min (or on anomaly), downlink for config
- **Solar-powered** — 1 W panel + MCP73831 charger + 18650 (3500 mAh) → 1–3 weeks autonomy even under dense canopy
- **IP68 weatherproof** — tree-mounted enclosure with cable-glanded probe, UV-stabilized ASA, heavy-duty strap mount

### Use Cases

| Application | How Sap Watch Helps |
|------------|---------------------|
| Orchard irrigation scheduling | Real-time tree water-use data replaces soil-moisture guessing — irrigate only when sap flux drops below a crop-specific threshold, saving 20–40% water |
| Forest drought-stress early warning | Network of nodes detects stomatal closure days before canopy browning; informs fire-risk models and emergency watering of high-value urban trees |
| Vineyard precision viticulture | Track vine water stress to time deficit irrigation for optimal grape quality (mild stress concentrates flavour compounds) |
| Climate-change ecology | Long-term transpiration records from natural stands quantify how species shift water use under warming and drying climates |
| Plantation forestry | Compare clone water-use efficiency; select drought-resilient genotypes for future planting |
| Urban tree management | Monitor street-tree water stress during heatwaves; prioritize watering by data, not guesswork |
| Sap-flow research | Affordable, replicable nodes enable dense spatial sampling (20+ trees) where a single datalogger was previously unaffordable |
| Coffee / agroforestry | Shade-tree vs. crop-tree water partitioning studies for sustainable agroforestry system design |

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              SAP WATCH                                        │
│                                                                               │
│   ┌──────────────────────────────────────────┐                               │
│   │        STM32WL55JC                        │                               │
│   │   (M4 48 MHz + M0+ 32 MHz,              │                               │
│   │    256 KB flash, 64 KB SRAM,             │                               │
│   │    sub-GHz LoRa radio built in)          │                               │
│   │                                          │                               │
│   │   ┌──────────────────────────────────┐   │      ┌──────────────┐         │
│   │   │ sap-flow measurement task         │   │ UART │ ADS122U04    │         │
│   │   │ (heat-pulse → ratio → velocity)   │◄──┼──────┤ 24-bit ADC   │         │
│   │   ├──────────────────────────────────┤   │      │ (4-ch mux)   │         │
│   │   │ thermal / wound-area correction   │   │      └──────┬───────┘         │
│   │   ├──────────────────────────────────┤   │             │  4-wire         │
│   │   │ daily transpiration integration   │   │      ┌──────┴───────┐         │
│   │   ├──────────────────────────────────┤   │      │ Probe needles │         │
│   │   │ drought-stress anomaly detector   │   │      │  • Heater     │ GPIO  │
│   │   ├──────────────────────────────────┤   │      │    (40 Ω)    │──► DRV │
│   │   │ LoRaWAN MAC + uplink packer       │   │      │  • NTC up     │ ADC   │
│   │   ├──────────────────────────────────┤   │      │    (5 mm)    │       │
│   │   │ power mgmt / sleep scheduler      │   │      │  • NTC dn     │ ADC   │
│   │   └──────────────────────────────────┘   │      │    (10 mm)   │       │
│   │                                          │      └──────────────┘         │
│   │   ┌────────────┐  ┌────────────┐         │                               │
│   │   │ Sub-GHz    │  │ STM32WL    │         │    ┌──────────────┐            │
│   │   │ LoRa radio │  │ flash +    │         │ I²C │ SHT45       │            │
│   │   │ (internal) │  │ NVRAM      │         ├────►│ T/RH sensor │            │
│   │   └─────┬──────┘  └────────────┘         │    └──────────────┘            │
│   └─────────┼──────────────────────────────────┘    ┌──────────────┐            │
│             │  868/915 MHz                           │ TSL2591      │ I²C        │
│             ▼          ┌──────────────┐              │ light sensor │            │
│   ┌──────────────┐     │  Gateway /   │              └──────────────┘            │
│   │ Whip antenna │────►│  Dashboard   │     ┌──────────────┐                     │
│   └──────────────┘     └──────────────┘     │ DS18B20      │ 1-W                  │
│                                               │ sapwood temp │                     │
│   ┌──────────────┐  GPIO                     └──────────────┘                     │
│   │ Heater       │◄──── MOSFET (AO3400A)                                          │
│   │ driver       │                                                              │
│   └──────────────┘                                                              │
│                                                                                  │
│   ┌──────────────┐  ┌──────────────────────┐   ┌──────────────────────┐          │
│   │ Solar panel  │─►│ MCP73831 charger     │──►│ 18650 Li-ion         │          │
│   │ 1 W, 6 V     │  │ + TPS63020 buck-boost│   │ 3500 mAh protected  │          │
│   └──────────────┘  │ → 3.3 V              │   └──────────┬───────────┘          │
│                      └──────────────────────┘              │                      │
│   ┌──────────────┐  ┌──────────────────────┐               │                      │
│   │ Status LEDs  │  │ MAX17048 fuel gauge  │ I²C           │                      │
│   │ (red/grn/amb)│  │ + voltage divider    │◄──────────────┘                      │
│   └──────────────┘  └──────────────────────┘                                     │
│                                                                                    │
│   ┌──────────────────────────────────────────────────────────┐                     │
│   │ IP68 ENCLOSURE (tree-mounted)                             │◄──────────────────┘
│   │  • UV-stabilized ASA, gasket-sealed                       │
│   │  • Cable gland for 3-needle probe (1 m cable)            │
│   │  • Heavy-duty strap / ratchet clamp mount                 │
│   │  • Solar panel on sun-facing side                         │
│   └──────────────────────────────────────────────────────────┘
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## The Heat-Ratio Method — How It Works

The **heat-ratio method (HRM)**, developed by Marshall (1958) and refined by Burgess et al. (2001), measures sap flux by tracking the movement of a short heat pulse injected into the xylem.

### Probe Geometry

Three needles are drilled into the sapwood, spaced 6 mm apart vertically:

```
         ↑  sap flow direction
         │
   ┌─────┴─────┐  Needle 1: NTC thermistor (upstream, 5 mm above heater)
   │  10 kΩ NTC │
   └─────┬─────┘
         │  5 mm
   ┌─────┴─────┐  Needle 2: Constantan heater coil (~40 Ω, 30 mm active length)
   │  Heater   │
   └─────┬─────┘
         │  10 mm
   ┌─────┴─────┐  Needle 3: NTC thermistor (downstream, 10 mm below heater)
   │  10 kΩ NTC │
   └─────┬─────┘
         │
         ▼
```

### Measurement Cycle (every 5 min)

1. **Pre-pulse baseline** (10 s): sample both thermistors at 10 Hz to establish T₀ (zero-flow reference)
2. **Heat pulse** (2 s): drive the heater with ~1.8 J (6 V × 0.15 A × 2 s). The pulse heats a small xylem volume.
3. **Post-pulse sampling** (60 s): sample both thermistors at 4 Hz, record T₁ (upstream max) and T₂ (downstream max)
4. **Compute heat ratio**: `V_h = ln(T₁ / T₂) / x` where x is the probe spacing
5. **Correct for wounding**: the drill hole damages xylem around the needle, creating a "wound" correction factor (Green et al. 2003), applied as `V_sap = V_h × k_wound / (0.44 × ρ_w × c_w)` where the denominator converts heat-pulse velocity to sap-flux velocity using the thermal properties of water (ρ_w = 998 kg m⁻³, c_w = 4186 J kg⁻¹ K⁻¹)
6. **Zero-flow calibration**: at predawn (when transpiration ≈ 0), the heat ratio should be 1.0 (symmetric heat spread); any offset is stored as a per-probe zero and subtracted from all subsequent readings — this corrects for imperfect probe installation and natural thermal gradients

### From Sap-Flux Velocity to Whole-Tree Water Use

- `V_sap` (cm h⁻¹) × `A_sapwood` (cm²) = `Q` (cm³ h⁻¹) = whole-tree water uptake
- Sapwood area is measured once per tree (from increment cores or species-specific allometry) and stored in the device's configuration
- Daily transpiration `E_daily` (L day⁻¹) = ∫ Q dt over the daylight period

---

## Pin Assignment (STM32WL55JC)

The STM32WL55JC is in a QFN-48 package. The following pin assignments use the STM32Cube ecosystem naming. The sub-GHz radio is internal — no external SPI radio is needed, unlike SX1262-based designs.

| Pin | Function | Connected To |
|-----|----------|-------------|
| PA0 / ADC1_IN1 | Analog | ADS122U04 ADC ready interrupt (EXTI) — optional, polled |
| PA1 / ADC1_IN2 | Analog | Battery voltage divider (1:3) — backup for MAX17048 |
| PA2 / USART2_TX | UART TX | ADS122U04 UART (9600 baud, ADC config + data) |
| PA3 / USART2_RX | UART RX | ADS122U04 UART (ADC data response) |
| PA4 / GPIO_OUT | GPIO output | Heater MOSFET gate (AO3400A, 2 s pulse drive) |
| PA5 / SPI1_SCK | SPI SCK | External flash (W25Q16, optional log buffer) — shared SPI1 |
| PA6 / SPI1_MISO | SPI MISO | External flash MISO |
| PA7 / SPI1_MOSI | SPI MOSI | External flash MOSI |
| PA8 / GPIO_OUT | GPIO output | External flash CS (W25Q16) |
| PA9 / I2C1_SCL | I2C SCL | SHT45 + TSL2591 + MAX17048 (4.7 kΩ pull-ups) |
| PA10 / I2C1_SDA | I2C SDA | SHT45 + TSL2591 + MAX17048 |
| PA11 / TIM4_CH1 | PWM | Status LED green (LoRa joined / reporting OK) |
| PA12 / TIM4_CH2 | PWM | Status LED red (drought-stress anomaly) |
| PA13 / TIM4_CH3 | PWM | Status LED amber (solar charging) |
| PA14 / GPIO_IN | GPIO input | Program / provisioning button (active low, pull-up) |
| PA15 / GPIO_IN | GPIO input | Mode / cycle button (triggers immediate measurement) |
| PB0 / ADC1_IN15 | Analog | Solar panel voltage sense (1:4 divider) |
| PB1 / GPIO_OUT | GPIO output | 1-Wire bus power (strong pull-up for DS18B20) |
| PB2 / SYS | — | BOOT0 (tied to GND via 10 kΩ for normal boot) |
| PB3 / GPIO_OUT | GPIO output | 1-Wire data line (DS18B20 sapwood temperature) |
| PB4 / GPIO_OUT | GPIO output | ADC ADS122U04 CS (chip select, active low) |
| PB5 / TIM3_CH1 | PWM | ADC excitation/current-source enable (optional) |
| PB6 / GPIO_OUT | GPIO output | Heater enable (high-side switch, redundant safety) |
| PB7 / GPIO_IN | GPIO input | Heater overcurrent fault (from current-sense amp) |
| PB8 / GPIO_IN | GPIO input | TSL2591 INT (optional light threshold interrupt) |
| PB9 / GPIO_OUT | GPIO output | LDO enable for analog front-end (power-gate ADC between cycles) |
| PB10 / USART3_TX | UART TX | Debug log (115200 baud, USB-serial bridge) |
| PB11 / USART3_RX | UART RX | Debug log input |
| PB12 / GPIO_OUT | GPIO output | LoRa radio TCXO enable (sub-GHz radio control) |
| PB13 / RF_SUBGHZ | RF | Sub-GHz antenna matching network → whip antenna |
| PC0 / GPIO_OUT | GPIO output | Analog front-end reset |
| PC1 / GPIO_IN | GPIO input | Heater current-sense ADC (overcurrent monitor) |
| PC13 / GPIO_IN | GPIO input | MAX17048 ALRT (low-battery interrupt) |
| PC14 / OSC32_IN | — | 32.768 kHz LSE crystal (for RTC + low-power timing) |
| PC15 / OSC32_OUT | — | 32.768 kHz LSE crystal |
| VDD | Power | +3.3 V from TPS63020 |
| VSS | Power | Ground |
| VDDRF | Power | +3.3 V (radio domain, ferrite-isolated) |
| VDDSMPS | Power | SMPS supply (internal buck, 1.2 V core) |

---

## Schematic Overview

### 1. Heat-Pulse Probe & Analog Front-End

The heart of the Sap Watch is a 3-needle probe that is drilled into the tree's sapwood. Each needle is 30 mm long, 1.2 mm diameter, stainless-steel sheath.

- **Needle 1 (upstream thermistor)**: a 10 kΩ NTC thermistor (Murata NCP18XH103F03RB, ±1 %, B25/85 = 3380 K) potted at 5 mm from the tip, connected via 4-wire Kelvin leads to the ADC
- **Needle 2 (heater)**: a constantan wire coil (~40 Ω, wound on a PTFE core) runs the full 30 mm active length; driven by a 6 V pulse from a low-side MOSFET (AO3400A) with a 2 s on-time → ~1.8 J per pulse
- **Needle 3 (downstream thermistor)**: identical 10 kΩ NTC, potted at 10 mm from the tip (asymmetric spacing corrects for the heat-pulse method's known downstream bias)

**Analog front-end**: An **ADS122U04** (TI, 24-bit delta-sigma, 4-channel mux, UART interface) reads both thermistors ratiometrically. Each thermistor is in a voltage divider with a precision 10 kΩ reference resistor (0.1 %, 25 ppm/°C). The ADC's internal PGA provides gain up to 128×. The 24-bit resolution over a 3.3 V span gives ~0.2 µV per LSB; with the 10 kΩ divider, this resolves ~0.001 °C — more than enough to measure the 0.05–2.0 °C heat-pulse signal.

The ADS122U04 is power-gated via a P-channel MOSFET (controlled by PB9) so it draws <1 µA between measurement cycles — critical for the 5-minute duty cycle.

### 2. Heater Driver & Safety

The heater needle is driven by a low-side N-channel MOSFET (AO3400A, 30 V, 1.7 A, low R_DS(on)). The heater current flows from the battery (through a 100 mΩ sense resistor) through the 40 Ω coil to GND.

**Triple-redundant safety** (a heater stuck-on would burn the tree and drain the battery):
1. **Firmware watchdog**: the heater is enabled by a hardware timer (TIM2) in one-pulse mode — it self-disables after 2 s regardless of firmware state
2. **Discrete overcurrent**: a current-sense amplifier (INA180) feeds a comparator; if heater current exceeds 0.5 A, a hardware latch trips and cuts the heater enable line (PB6)
3. **Thermal fuse**: a 72 °C one-shot thermal fuse is potted into the heater needle as a last-resort mechanical cutoff

A separate GPIO (PB7) reads the comparator's fault flag so the firmware can report heater faults over LoRaWAN.

### 3. Environmental Sensors

- **SHT45** (Sensirion, I²C 0x44): ±0.1 °C, ±1.5 %RH — measures trunk-surface air temperature and humidity for vapor-pressure-deficit (VPD) calculation (a key driver of transpiration)
- **TSL2591** (AMS, I²C 0x29): 0.1–40,000 lux — measures incident light at the canopy level as a photosynthetically-active-radiation (PAR) proxy, useful for interpreting sap-flow patterns
- **DS18B20** (Maxim, 1-Wire, parasitic power): inserted into a fourth small hole in the sapwood 20 mm from the probe cluster — measures sapwood temperature for the thermal-properties correction in the heat-ratio equation (c_w and ρ_w are temperature-dependent)

### 4. LoRaWAN Uplink (Internal STM32WL55 Radio)

The STM32WL55JC has an integrated Semtech SX1262-equivalent sub-GHz LoRa radio — no external SPI radio chip is needed. The radio connects to the MCU core via an internal SPI bus.

- **Frequency**: 868 MHz (EU) / 915 MHz (US/AU), configured via firmware region setting
- **Antenna**: 86 mm whip antenna (¼-wave at 868 MHz) on the enclosure exterior, connected via a U.FL connector on the PCB
- **LoRaWAN 1.0.4** MAC layer (implemented in firmware using STM32WL LoRaWAN stack)
- **Uplink messages (port 1)**: sap-flux velocity (cm h⁻¹), cumulative daily transpiration (L), sapwood temp, air T/RH, light, battery %, probe health — every 15 min
- **Uplink messages (port 2 — alert)**: drought-stress anomaly flag, predawn/midday flux ratio, heater-fault flag — sent immediately on detection
- **Downlink (port 3)**: measurement interval, sapwood area, zero-flow calibration command, species correction factor
- **Join**: OTAA (AppEUI/AppKey provisioned via the program button during setup)

### 5. Power Architecture

- **Solar panel**: 1 W, 6 V monocrystalline panel (70 × 50 mm) — smaller than Echo Trap because canopy shade limits available light; the panel is mounted on the sun-facing side of the enclosure and angled outward from the trunk
- **Charge controller**: **MCP73831** (simple linear Li-ion charger, 100 mA, low external part count) — adequate for the low power budget; a load-sharing MOSFET lets the panel power the system while charging
- **Battery**: 1× 18650 Li-ion, 3500 mAh, protected (3.0–4.2 V) — mounted inside the enclosure
- **3.3 V rail**: **TPS63020** buck-boost (1.8–5.5 V → 3.3 V, up to 2 A) — stable across the full battery voltage range
- **Fuel gauge**: **MAX17048** (I²C) for accurate state-of-charge; the device enters deep sleep when SoC < 10 % and wakes only every hour for a single measurement
- **Power budget**:
  - Measurement cycle (every 5 min): ADC + heater pulse = ~180 mA for 2 s (heater) + 5 mA for 60 s (ADC) → ~6 mA average
  - LoRaWAN TX (14 dBm): ~40 mA for ~0.2 s every 15 min = ~0.01 mA average
  - Environmental sensors + MCU: ~2 mA standby
  - **Total average**: ~8 mA → ~440 h (18 days) on a 3500 mAh battery with no sun; with 1 W solar (~3 h effective under canopy × 100 mA charge) the device is self-sustaining in most conditions; in deep shade a larger 2 W panel or weekly battery swap is needed

### 6. Enclosure & Probe Mounting

- **IP68** UV-stabilized ASA enclosure (~100 × 65 × 40 mm)
- **Cable gland**: PG7 waterproof gland for the 4-needle probe cable (1 m, shielded, 6-conductor)
- **Tree mount**: heavy-duty ratchet strap (25 mm, 1 m) wraps the trunk; enclosure hangs from a bracket on the strap
- **Probe installation**: a drill guide jig (included) ensures parallel needle insertion at the correct 5/10 mm spacing; needles are tapped into pre-drilled 1.0 mm holes to a depth of 20 mm into the sapwood
- **Solar panel**: mounted on a small bracket angled 45° outward from the trunk toward the sun-facing side

---

## Firmware Architecture (STM32WL55JC, STM32CubeIDE / CMake)

Bare-metal C with a lightweight cooperative scheduler (no FreeRTOS needed — the duty cycle is dominated by sleep). The firmware uses the STM32WL HAL and the STM32 LoRaWAN stack.

| Task / Module | Trigger | Job |
|---------------|---------|-----|
| `measure` | Timer, every 5 min | Run heat-pulse cycle: baseline → pulse → sample → compute sap flux |
| `sensors` | Timer, every 60 s | Read SHT45, TSL2591, DS18B20, MAX17048 |
| `lorawan` | Event-driven | Radio IRQ handler, MAC state machine, uplink queue, downlink parser |
| `power` | Timer, every 60 s | Fuel gauge poll, solar voltage check, deep-sleep entry/exit |
| `anomaly` | After each measurement | Drought-stress detector: predawn vs. midday flux, historical baseline comparison |
| `main` | Boot | Init peripherals, load config from flash, start scheduler |

Key modules:

- `main.c` — peripheral init, scheduler loop, sleep/wake management
- `config.h` — all constants, pin map, LoRaWAN region, measurement intervals
- `probe.c` — heater pulse driver (TIM2 one-pulse mode), ADS122U04 UART driver, thermistor-to-temperature conversion (Steinhart-Hart), 4-wire Kelvin readout
- `heat_ratio.c` — heat-ratio algorithm: baseline subtraction, T₁/T₂ max tracking, wounding correction, zero-flow calibration, sap-flux velocity computation
- `transpiration.c` — daily transpiration integration (trapezoidal), sapwood area scaling, VPD calculation
- `anomaly.c` — drought-stress detection: predawn baseline, midday ratio, rolling 7-day comparison, stomatal-closure flag
- `sensors.c` — SHT45, TSL2591, DS18B20, MAX17048 drivers
- `lorawan.c` — STM32WL sub-GHz radio driver, LoRaWAN MAC, OTAA join, uplink packet assembly, downlink config parsing
- `power.c` — battery management, deep-sleep, solar charge status, low-power mode selection
- `storage.c` — flash-backed config storage (NVRAM emulation in STM32WL flash), measurement log ring buffer
- `heater_safety.c` — TIM2 one-pulse watchdog, overcurrent comparator monitoring, fault reporting

---

## Sap-Flow Computation Detail

### Thermistor-to-Temperature (Steinhart-Hart)

The 10 kΩ NTC thermistors are read via a voltage divider (V_ref = 3.3 V, R_ref = 10 kΩ 0.1 %):

```
R_therm = R_ref × (V_ref / V_measured - 1)

T (Kelvin) = 1 / (A + B·ln(R) + C·ln(R)³)

where (for NCP18XH103F03RB, 10 kΩ @ 25 °C):
  A = 0.790389e-3
  B = 2.273577e-4
  C = 1.6089e-7
```

This gives temperature to ±0.01 °C over 0–50 °C.

### Heat-Ratio Velocity

After a 2 s heat pulse, the upstream (T₁) and downstream (T₂) thermistors each reach a temperature maximum within 60 s. The heat-pulse velocity is:

```
V_h = (k_xylem / (x_up + x_dn)) × ln(T₂ / T₁)    [cm s⁻¹]
```

where `k_xylem` is the thermal diffusivity of wet sapwood (~0.0025 cm² s⁻¹) and x_up, x_dn are the probe spacings (5 mm, 10 mm). This is then corrected:

```
V_sap = (V_h - V_0) × F_wound × (ρ_w × c_w) / (ρ_s × c_s)
```

- `V_0` = zero-flow offset (measured at predawn each day)
- `F_wound` = wound correction factor (1.0–1.8, species-dependent, stored in config)
- `ρ_s × c_s` = thermal capacity of sapwood (measured or estimated from sapwood density + moisture content)

### Sap-Flux Velocity to Whole-Tree Water Use

```
Q (L h⁻¹) = V_sap (cm h⁻¹) × A_sapwood (cm²) × 0.001
```

The sapwood area `A_sapwood` is set per-tree via LoRaWAN downlink during installation. For a 30 cm DBH oak with 20 mm sapwood depth, `A_sapwood ≈ 180 cm²`, and a typical midday `V_sap ≈ 20 cm h⁻¹` gives `Q ≈ 3.6 L h⁻¹`.

---

## LoRaWAN Payload Format

### Port 1 — Periodic Report (every 15 min)

| Byte | Field | Type | Notes |
|------|-------|------|-------|
| 0–1 | sap_flux_velocity | int16 | cm h⁻¹ × 100 (e.g., 2050 = 20.50 cm h⁻¹) |
| 2–3 | daily_transpiration | uint16 | L × 100 (e.g., 1250 = 12.50 L since midnight) |
| 4–5 | sapwood_temp | int16 | °C × 100 (DS18B20) |
| 6–7 | air_temp | int16 | °C × 100 (SHT45) |
| 8–9 | humidity | uint16 | %RH × 100 |
| 10–11 | light_lux | uint16 | lux (TSL2591, capped at 65535) |
| 12–13 | vpd | uint16 | kPa × 100 (vapor pressure deficit) |
| 14 | battery_pct | uint8 | % (MAX17048) |
| 15 | probe_health | uint8 | bitfield: bit0=heater_ok, bit1=adc_ok, bit2=therm1_ok, bit3=therm2_ok, bit4=zero_cal_valid |
| 16–17 | measurement_count | uint16 | total measurements since boot |
| 18 | flags | uint8 | bit0=drought_stress, bit1=heater_fault, bit2=low_battery |

### Port 2 — Anomaly Alert (sent immediately on detection)

| Byte | Field | Type | Notes |
|------|-------|------|-------|
| 0 | alert_type | uint8 | 1=drought_stress, 2=heater_fault, 3=probe_disconnect, 4=low_battery |
| 1–2 | sap_flux_velocity | int16 | cm h⁻¹ × 100 |
| 3–4 | predawn_flux | int16 | cm h⁻¹ × 100 (predawn baseline) |
| 5–6 | midday_flux | int16 | cm h⁻¹ × 100 (current midday) |
| 7 | ratio_pct | uint8 | midday/predawn × 100 (e.g., 40 = 40% of predawn → stress) |

### Port 3 — Downlink (config from gateway)

| Byte | Field | Type | Notes |
|------|-------|------|-------|
| 0 | command | uint8 | 1=set_interval, 2=set_sapwood_area, 3=trigger_zero_cal, 4=set_wound_factor, 5=force_measurement |
| 1–2 | value | uint16 | command-specific (e.g., interval in minutes, sapwood area in cm², wound factor × 100) |

---

## Bill of Materials

See `hardware/BOM.csv`.

---

## Building It

See `docs/assembly_guide.md` for the full assembly, probe installation, and tree-mounting procedure. See `docs/api_reference.md` for the LoRaWAN payload format and downlink protocol. See `docs/calibration_guide.md` for the zero-flow calibration and wounding-factor determination procedure.

---

## Companion Scripts

`scripts/` contains Python helpers:

- `decode_uplink.py` — decode LoRaWAN uplink payloads (port 1/2) into human-readable JSON
- `plot_transpiration.py` — connect to a Chirpstack/TTN HTTP integration, plot daily transpiration curves and drought-stress flags (matplotlib)
- `field_test.py` — automated field test: trigger a measurement over UART debug, verify heater/ADC/radio response, report pass/fail
- `calibration.py` — run the zero-flow calibration procedure: connect over UART, collect predawn data, compute offset, send to device
- `deploy_mesh.py` — batch-provision LoRaWAN keys (AppEUI/AppKey/DevEUI) for a fleet of Sap Watch nodes via serial console

---

## License

MIT — build it, measure trees with it, understand forests with it.