# Schematic — Frost Point Chilled-Mirror Dew Point Hygrometer

KiCad 7 project. Schematic organized as hierarchical sheets:

```
frost-point.kicad_sch (root)
├── soc.sch            — STM32L476RGT6 + decoupling + crystal
├── power.sch          — USB-C PD (CH224K), LiPo charger (MCP73831), 3.3 V LDO (TPS7A4700), 5 V boost (TPS61023)
├── tec-drive.sch      — DRV8871 H-bridge, AD8418 current sense, TEC1-12706 connector, heater FET
├── mirror.sch         — ADS122U04 24-bit ADC, NTC thermistor bridge, calibration header
├── optics.sch         — VSLY5850 IR LED + TEMD6200 phototransistor + DAC bias + 38 kHz chopper
├── sensors.sch        — BME280, SCD41, SHT45, MS5837-02BA on I2C3
├── flash.sch          — W25Q128 SPI flash + level shift
├── ble.sch            — ANNA-B112 BLE module + reset/mode GPIO + UART
├── ui.sch             — SH1106 OLED, status LEDs, user button, buzzer
└── fan.sch            — Sunon blower + fan-fail thermistor on hot-side
```

## Net list (key nets)

| Net | From | To |
|-----|------|----|
| TEC_V_SENSE  | TEC+ → 10:1 div   | PA0 |
| TEC_I_SENSE  | 20 mΩ shunt → AD8418 | PA1 |
| TEC_PWM      | TIM2_CH1           | DRV8871 IN1 |
| TEC_DIR      | PA3               | DRV8871 IN2 |
| TEC_HEAT_EN  | PB13              | reverse-polarity P-FET gate |
| I2C1_SCL/SDA | PB8/PB9           | ADS122U04 |
| I2C3_SCL/SDA | PA8/PA9           | OLED, BME280, SCD41, SHT45 |
| SPI1_*       | PB3/PB4/PB5       | W25Q128 |
| LPUART1      | PA10/PA11         | ANNA-B112 |
| IR_LED_EN    | PB1               | VSLY5850 cathode driver |
| IR_LED_BIAS  | PA4 (DAC1)        | IR LED anode bias |
| IR_PHOTOTX   | PB0               | TEMD6200 emitter |
| MIRROR_FAULT | PB14              | thermistor open-detect comparator |

## Mirror/TEC assembly mechanical note

The mirror thermistors are surface-mounted to the gold-coated glass disc with a 2 mm PTFE mask isolating the reference thermistor from the condensing zone. Assembly is documented in `docs/assembly.md`.