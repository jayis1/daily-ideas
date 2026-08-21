# Hive Mind

**Solar-powered beehive health monitor with weight, temperature gradient, acoustic analysis, and bee traffic counting — reporting via LoRaWAN.**

---

## What It Does

The Hive Mind is a rugged, weatherproof PCB that sits under a beehive (or inside, depending on configuration) and continuously monitors colony health through four complementary sensing modalities:

- **Hive weight** — 50 kg load cell + HX711 24-bit ADC detects honey production trends, nectar flow events, and swarm preparation (sudden weight drop = swarm departed). Resolution: ±5 g.
- **Internal temperature gradient** — 3× DS18B20 1-Wire probes at different heights (floor, mid-hive, crown board) reveal brood thermoregulation health, clustering behavior, and winter survival.
- **Acoustic spectrum** — I2S MEMS microphone captures hive hum at 8 kHz, runs on-device 256-point FFT every 30 seconds, and classifies colony state: **normal**, **queenless**, **swarming**, **starving**, **fanning** (ventilation), or **dead**. Bee acoustic signatures occupy 200–500 Hz.
- **Bee traffic** — dual IR break-beam sensors at the entrance count incoming and outgoing foragers, producing an activity index (departures vs arrivals ratio signals orientation flights or mass eviction).

All data is fused into a **hive health score** (0–100) reported every 15 minutes via **LoRaWAN** (EU868 / US915 / AU915) to The Things Network or a private LoRa gateway. A local **SSD1306 OLED** shows real-time status during apiary visits. BLE is omitted in favor of long-range LoRa — the beekeeper configures the device via USB-C serial.

Battery life: **12+ months** on a single 18650 LiFePO₄ cell with the 5 W solar panel providing trickle charge. In winter with no sun, the 3.2 V 1500 mAh LiFePO₄ sustains operation for ~90 days at ultra-low duty cycle.

---

## Block Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        HIVE MIND                                  │
│                                                                   │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │  50 kg Load  │   │  DS18B20 x3  │   │  ICS-43434 MEMS Mic  │ │
│  │  Cell        │   │  1-Wire chain│   │  I2S digital output  │ │
│  │  (Wheatstone)│   │  (floor/mid/ │   │  (bee acoustics)     │ │
│  │      │       │   │   crown)     │   │         │            │ │
│  │  ┌──▼──┐    │   │      │       │   │   ┌─────▼─────┐      │ │
│  │  │HX711│    │   │      │       │   │   │ I2S + DMA │      │ │
│  │  │24bit│    │   │      │       │   │   │ 8kHz/16bit │      │ │
│  │  │ ADC │    │   │      │       │   │   └─────┬─────┘      │ │
│  │  └──┬──┘    │   │      │       │   │         │            │ │
│  └─────┼───────┘   └──────┼───────┘   └─────────┼────────────┘ │
│        │ GPIO             │ GPIO               │ I2S           │
│        │                  │                    │                │
│  ┌─────▼──────────────────▼────────────────────▼──────────────┐│
│  │                    STM32WL55JC                               ││
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────────────┐ ││
│  │  │ Cortex-  │ │ Cortex-  │ │ Sub-GHz   │ │ DMA + I2S +   │ ││
│  │  │ M4 48MHz │ │ M0+ 48MHz│ │ LoRa radio│ │ ADC + 1-Wire  │ ││
│  │  │ (app +   │ │ (LoRa    │ │ (EU868/   │ │ (sensors)     │ ││
│  │  │ FFT)     │ │ MAC)     │ │  US915)   │ │               │ ││
│  │  └──────────┘ └──────────┘ └───────────┘ └───────────────┘ ││
│  └─────────┬─────────────┬──────────────┬─────────────────────┘│
│            │             │              │                       │
│  ┌─────────▼──┐  ┌───────▼──────┐  ┌───▼──────────────────────┐│
│  │  SSD1306   │  │  IR TX/RX   │  │   LoRaWAN antenna       ││
│  │  128×64    │  │  break-beam  │  │   (868/915 MHz wire)    ││
│  │  OLED I²C  │  │  x2 (in/out)│  └──────────────────────────┘│
│  └────────────┘  └─────────────┘                               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  BME280 (ambient T/H/P)  ── I²C  ── weather context     │   │
│  │  Power: 5W solar → TP4056 → 18650 LiFePO₄ → ME6211 3.3V│   │
│  │  USB-C: charging + UART config (CH340E bridge)          │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Pin Assignment (STM32WL55JC UFQFPN48)

| Pin | Function | Connected To | Notes |
|-----|----------|-------------|-------|
| PA0 | ADC_IN5 | Battery voltage divider | 1:2 divider, full-scale 6.6 V |
| PA1 | GPIO_IN | HX711 DOUT | Active-low data ready |
| PA2 | GPIO_OUT | HX711 PD_SCK | Clock to HX711, 25 pulses = channel A ×128 |
| PA3 | LPUART1_TX | CH340E RX → USB-C | Debug/console + configuration |
| PA4 | LPUART1_RX | CH340E TX → USB-C | Debug/console + configuration |
| PA9 | I2C1_SCL | BME280 + SSD1306 | 4.7 kΩ pullups |
| PA10 | I2C1_SDA | BME280 + SSD1306 | 4.7 kΩ pullups |
| PB3 | GPIO_OD | DS18B20 1-Wire bus | Open-drain, 4.7 kΩ pullup |
| PB4 | I2S_CK | ICS-43434 SCK | I2S bit clock, 256 kHz for 8 kHz sample |
| PB5 | I2S_WS | ICS-43434 WS | I2S word select (L/R select) |
| PB6 | I2S_SD | ICS-43434 SD | I2S serial data in |
| PB7 | GPIO_OUT | HX711 power enable | Active-high LDO enable for load cell |
| PB8 | GPIO_OUT | IR LED 1 (entrance out) | 940 nm LED, 50 mA peak |
| PB9 | GPIO_IN | IR phototransistor 1 | TCRT1000 reflective sensor |
| PB10 | GPIO_OUT | IR LED 2 (entrance in) | 940 nm LED, 50 mA peak |
| PB11 | GPIO_IN | IR phototransistor 2 | TCRT1000 reflective sensor |
| PB12 | SPI2_NSS | Sub-GHz radio NSS | Internal to RF subsystem |
| PB13 | SPI2_SCK | Sub-GHz radio SCK | Internal to RF subsystem |
| PB14 | SPI2_MISO | Sub-GHz radio MISO | Internal to RF subsystem |
| PB15 | SPI2_MOSI | Sub-GHz radio MOSI | Internal to RF subsystem |
| PC0 | GPIO_OUT | RF switch CTRL1 | Skyworks SKY13330 antenna switch |
| PC1 | GPIO_OUT | RF switch CTRL2 | Skyworks SKY13330 antenna switch |
| PC6 | GPIO_OUT | Status LED green | Active-low, 1 kΩ series |
| PC7 | GPIO_OUT | Status LED red | Active-low, 1 kΩ series |
| PC13 | GPIO_IN | User button | Active-low, internal pullup |
| PH3 | BOOT0 | Boot configuration | 10 kΩ pullup, 100 nF cap |
| VDD | 3.3V | Power rail | ME6211 LDO output |
| VSS | GND | Ground | Common ground plane |

---

## Power Architecture

```
Solar (5W, 6V OC) ──► TP4056 CC/CV ──► 18650 LiFePO₄ (3.2V, 1500mAh) ──► ME6211-3.3V LDO ──► VDD

USB-C (5V) ──► CH340E (UART bridge) ──► PA3/PA4
         └──► TP4056 (charge path) ──► battery

Quiescent: ~8 µA (STOP mode, RTC on, HX711 off)
Active (LoRa TX burst): ~45 mA for 200 ms every 15 min
Active (acoustic FFT): ~12 mA for 100 ms every 30 s
Average (full duty cycle): ~0.8 mA → ~78 days on battery alone
Solar supplement: ~15 mA avg in daylight → indefinite outdoor operation
```

Duty cycle in normal mode:
1. STOP mode (RTC wake every 30 s)
2. Read DS18B20 chain (~750 ms, parasitic power)
3. Read BME280 (~5 ms)
4. Read HX711 (~100 ms)
5. Every 4th cycle (2 min): capture I2S audio (2 s window) → 256-point FFT → classify
6. Every 8th cycle (4 min): count IR break-beam events over 30 s window
7. Every 30th cycle (15 min): LoRaWAN uplink (hive weight, temperatures, acoustic class, bee traffic, battery)
8. OLED wakes on user button press (shows data for 10 s then sleeps)
9. Return to STOP mode

---

## Acoustic Classification

The FFT pipeline runs on the Cortex-M4 at 48 MHz:

| Frequency Band | Meaning |
|----------------|---------|
| 200–250 Hz | Normal colony hum (queenright, healthy) |
| 250–300 Hz | Elevated activity (foraging boom, nectar flow) |
| 300–400 Hz | Queen piping (toot/quack pattern at ~350 Hz) |
| 400–500 Hz | Fanning / ventilation (cooling the hive) |
| Absence of hum | Dead colony or extreme cold cluster |
| Wideband noise | Disturbance / robbing / alarm pheromone |

Classification is a simple rule-based system on FFT bin magnitudes (no ML model needed — 8 rules cover 95% of hive states). The classifier outputs one of 8 states:

```
QUEENRIGHT, QUEENLESS, SWARMING, FANNING, PIPING, ROBBING, CLUSTERING, DEAD
```

---

## LoRaWAN Uplink Payload

Each uplink is 21 bytes, SF7, on EU868 (or US915/AU915):

| Byte | Field | Scale | Range |
|------|-------|-------|-------|
| 0–1 | Hive weight (g) | 1 g | 0–65535 g |
| 2 | Temperature floor (°C) | ×0.5, offset -20 | -20 to +83 °C |
| 3 | Temperature mid | ×0.5, offset -20 | -20 to +83 °C |
| 4 | Temperature crown | ×0.5, offset -20 | -20 to +83 °C |
| 5 | Ambient temperature | ×0.5, offset -20 | -20 to +83 °C |
| 6–7 | Ambient humidity | 0.01% | 0–100% |
| 8–9 | Ambient pressure | 0.1 hPa | 300–1100 hPa |
| 10 | Acoustic class | enum 0–7 | See classification table |
| 11 | Dominant freq (×10 Hz) | 10 Hz | 0–2550 Hz |
| 12–13 | Bee traffic in (count) | 1 | 0–65535 per window |
| 14–15 | Bee traffic out (count) | 1 | 0–65535 per window |
| 16 | Battery voltage | ×0.02 V | 0–5.1 V |
| 17 | Solar voltage | ×0.02 V | 0–5.1 V |
| 18 | Uptime hours | 1 h | 0–65535 h |
| 19–20 | Hive health score | 0.01 | 0–100 |

---

## LoRaWAN Downlink (Configuration)

Downlink payloads allow remote configuration:

| Port | Length | Meaning |
|------|--------|---------|
| 2 | 1 | Set sampling interval (seconds × 2) |
| 3 | 4 | Set LoRaWAN ABP keys (NwkSKey + AppSKey) |
| 4 | 1 | Force immediate uplink (0 = trigger) |
| 5 | 2 | Set FFT interval (seconds, big-endian) |
| 6 | 2 | Set IR counting window (seconds, big-endian) |

---

## Mechanical

- PCB: 100 × 70 mm, 1.6 mm FR4, 4-layer
- Mounts under hive via 4× M5 standoffs (load cell is the rear support point)
- Load cell: 50 kg beam type, mounted on aluminum bracket
- DS18B20 probes: 3 × 1 m silicone cable, inserted at floor/mid/crown
- IR break-beam: custom 3D-printed entrance gate with IR gate pair, 30 mm aperture
- Enclosure: IP65 rated ABS box (120 × 80 × 40 mm) with cable glands
- Antenna: 868/915 MHz wire antenna (86 mm / 82 mm quarter-wave) exits via cable gland
- Solar panel: 5 W rigid panel on angled bracket, cable gland entry
- Weight: 180 g (PCB + enclosure), 280 g total with battery and load cell

---

## Firmware Architecture

```
firmware/
├── Core/
│   ├── Inc/
│   │   ├── main.h
│   │   ├── weight_sensor.h
│   │   ├── temp_chain.h
│   │   ├── acoustic_analyzer.h
│   │   ├── bee_counter.h
│   │   ├── bme280_driver.h
│   │   ├── oled_display.h
│   │   ├── lorawan_uplink.h
│   │   ├── power_manager.h
│   │   └── hive_health.h
│   └── Src/
│       ├── main.c              # Entry point, FreeRTOS tasks, watchdog
│       ├── weight_sensor.c     # HX711 bit-bang, calibration, tare
│       ├── temp_chain.c        # DS18B20 1-Wire read, 3-probe chain
│       ├── acoustic_analyzer.c # I2S DMA capture, FFT, classification
│       ├── bee_counter.c       # IR break-beam, counting, activity index
│       ├── bme280_driver.c     # Ambient T/H/P via I2C
│       ├── oled_display.c      # SSD1306 status display
│       ├── lorawan_uplink.c    # LoRaWAN MAC, payload encode
│       ├── power_manager.c     # STOP mode, RTC wake, solar monitor
│       └── hive_health.c       # Health score computation
├── Drivers/
│   ├── STM32WLxx_HAL_Driver/
│   └── CMSIS/
├── Middlewares/
│   ├── FreeRTOS/
│   └── LoRaWAN/               (LoRaWAN MAC from STM32CubeWL)
├── Makefile
└── STM32WL55JC.ld
```

### Key Firmware Flow

```c
int main(void) {
    HAL_Init();
    SystemClock_Config();
    power_manager_init();
    i2c_bus_init();
    bme280_init();
    oled_display_init();
    weight_sensor_init();
    temp_chain_init();
    bee_counter_init();
    acoustic_analyzer_init();
    lorawan_init();   // LoRaWAN MAC on CM0+, joined to network

    xTaskCreate(sensor_task,    "Sensors",  512, NULL, 2, NULL);
    xTaskCreate(acoustic_task,  "Acoustic", 1024, NULL, 3, NULL);
    xTaskCreate(uplink_task,    "Uplink",   512, NULL, 1, NULL);
    xTaskCreate(display_task,  "Display",  256, NULL, 0, NULL);
    vTaskStartScheduler();
}

void sensor_task(void *pv) {
    while (1) {
        float weight = weight_sensor_read_grams();    // HX711
        float temps[3]; temp_chain_read_all(temps);   // DS18B20
        float ambient[3]; bme280_read(ambient);        // T/H/P
        float vbat = power_manager_read_battery();

        // Store in shared struct
        sensor_data_update(weight, temps, ambient, vbat);

        vTaskDelay(pdMS_TO_TICKS(30000));  // Every 30 s
    }
}

void acoustic_task(void *pv) {
    while (1) {
        acoustic_class_t cls = acoustic_analyzer_classify();
        sensor_data_set_class(cls);
        vTaskDelay(pdMS_TO_TICKS(120000));  // Every 2 min
    }
}

void uplink_task(void *pv) {
    while (1) {
        lorawan_send_payload(encode_payload());
        vTaskDelay(pdMS_TO_TICKS(900000));  // Every 15 min
    }
}
```

---

## Dual-Core Architecture

The STM32WL55JC uses both cores:

| Core | Role | Tasks |
|------|------|-------|
| Cortex-M4 | Application | Sensor reads, FFT, health score, OLED, RTOS |
| Cortex-M0+ | LoRaWAN MAC | Radio driver, LoRaWAN stack, IPCC mail to M4 |

The CM0+ runs the LoRaWAN MAC from STM32CubeWL. The CM4 sends uplink payloads via IPCC (Inter-Processor Communication Controller) mailbox. The CM0+ handles all radio IRQs, duty-cycle enforcement, and ADR.

---

## Calibration

### Weight Sensor Calibration

```python
# scripts/calibrate_weight.py
# Place known weights on the hive platform:
# 1. Tare (empty platform) → records offset
# 2. Place 10 kg reference → records scale factor
# 3. Place 20 kg reference → verify linearity
# Store offset and scale_factor in STM32 flash (NVM)
```

### Temperature Probe Mapping

The three DS18B20 probes are on a single 1-Wire bus. On first boot, the firmware scans for ROM IDs and maps them by boot order (or the user can assign floor/mid/crown labels via USB-C console):

```
> temp assign <ROM_ID> floor
> temp assign <ROM_ID> mid
> temp assign <ROM_ID> crown
```

---

## Assembly Notes

1. **Load cell mounting**: Use M5 bolts through the load cell mounting holes. The cell must be the sole support point on one side of the hive. Use a rigid aluminum bracket to transfer weight from the hive floor to the load cell.
2. **DS18B20 probe insertion**: Drill 3 mm holes in hive frames at floor/mid/crown levels. Push silicone-sheathed probes into the holes and seal with beeswax.
3. **IR gate assembly**: 3D-print the entrance gate (STL files in `hardware/`). Install the two IR break-beam pairs 30 mm apart in the entrance tunnel, one for incoming bees and one for outgoing.
4. **Antenna**: Solder the 86 mm (868 MHz) or 82 mm (915 MHz) wire antenna to the RF output pad. Route through cable gland.
5. **Solar panel**: Mount on a south-facing bracket (Northern Hemisphere) at 45° angle. Connect via weatherproof cable gland.
6. **Conformal coating**: Apply acrylic conformal coating (except load cell, antenna, and sensor openings) for weather resistance.

---

## Cost Estimate

| Category | Cost (USD) |
|----------|-----------|
| STM32WL55JC | 4.50 |
| HX711 + 50 kg load cell | 3.80 |
| DS18B20 × 3 | 2.10 |
| ICS-43434 MEMS mic | 1.80 |
| BME280 | 1.20 |
| SSD1306 OLED | 0.90 |
| TCRT1000 × 2 (IR gate) | 0.60 |
| TP4056 + ME6211 (power) | 0.40 |
| CH340E (USB-UART) | 0.30 |
| SKY13330 (RF switch) | 0.80 |
| Passives + connectors | 1.50 |
| 18650 LiFePO₄ 1500 mAh | 3.00 |
| 5 W solar panel | 4.00 |
| PCB (4-layer, 100×70 mm) | 2.50 |
| Enclosure (ABS IP65) | 2.50 |
| **Total** | **~30.40** |

---

## LoRaWAN Provisioning

The Hive Mind supports both **OTAA** (recommended) and **ABP** activation:

### OTAA (Over-The-Air Activation)

1. Generate a Device EUI from the STM32WL55 unique ID (UID96 → EUI-64)
2. Generate an Application EUI and Application Key
3. Register device on The Things Network (TTN) console
4. The device auto-joins on first power-up
5. AppKey is stored in STM32 flash (NVM)

### ABP (Activation By Personalization)

1. Use USB-C console to program NwkSKey, AppSKey, and DevAddr
2. Device starts transmitting immediately

```bash
# USB-C console commands (115200 baud, 8N1)
> lora set_deveui <hex16>
> lora set_appeui <hex16>
> lora set_appkey <hex32>
> lora join otaa
> lora status
> lora test_tx   # Send test packet
```

---

## API Reference

See [`docs/api_reference.md`](docs/api_reference.md) for full USB-C console command reference.

## Assembly Guide

See [`docs/assembly_guide.md`](docs/assembly_guide.md) for step-by-step build instructions.

## Deployment Guide

See [`docs/deployment_guide.md`](docs/deployment_guide.md) for apiary installation and calibration.

---

## License

MIT — build it, sell it, improve it.

---

*Invented by [jayis1](https://github.com/jayis1) — SoC Device Inventions.*