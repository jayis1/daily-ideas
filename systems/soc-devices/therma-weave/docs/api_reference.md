# Therma Weave — API Reference

## Serial Console (UART, 115200 baud, 8N1)

The Therma Weave firmware exposes a text-based serial console for debugging and manual control.

### Zone Control Commands

```
ZONE:ENABLE <0-3>          Enable a specific zone
ZONE:DISABLE <0-3>         Disable a specific zone
ZONE:ENABLE_ALL             Enable all zones
ZONE:DISABLE_ALL            Disable all zones
ZONE:TARGET <0-3> <30-55>   Set target temperature (°C) for a zone
ZONE:STATUS                  Print status of all zones
ZONE:PID <0-3> <Kp> <Ki> <Kd>  Set PID parameters for a zone
ZONE:RESET_FAULTS <0-3>     Clear fault flags for a zone
```

### Safety Commands

```
SAFETY:SHUTDOWN              Emergency shutdown — all heaters OFF
SAFETY:RESET                  Reset all faults and re-enable
SAFETY:STATUS                 Print safety watchdog status
```

### Sensor Commands

```
SENSOR:TEMP <0-3>             Read zone temperature (°C)
SENSOR:TEMP_ALL                Read all zone temperatures
SENSOR:AMBIENT                 Read BME280 ambient T/H/P
SENSOR:CURRENT <0-3>           Read zone current (mA)
SENSOR:CURRENT_ALL             Read all zone currents
SENSOR:ACTIVITY                 Read activity level (STILL/WALK/RUN/FALL)
SENSOR:BATTERY                  Read battery voltage (V)
```

### System Commands

```
SYSTEM:INFO                    Print device info (version, uptime, free heap)
SYSTEM:REBOOT                  Reboot the ESP32-C3
SYSTEM:FACTORY_RESET           Erase NVS and reset all settings
SYSTEM:SAVE                    Save current settings to NVS
SYSTEM:LOAD                    Load settings from NVS
```

### PID Auto-Tune

```
PID:AUTOTUNE <0-3>             Start Ziegler-Nichols auto-tune for a zone
PID:AUTOTUNE_STATUS            Check auto-tune progress
```

## I²C Register Map

The firmware also exposes an I²C slave interface on address `0x42` for external MCU control.

| Register | Size | R/W | Description |
|----------|------|-----|-------------|
| 0x00 | 1 | R | System status (bit0=running, bit1=BLE_connected, bit2=fault_active) |
| 0x01 | 1 | R | Number of active zones |
| 0x02 | 1 | R/W | Global enable bitmask (bit0=Z0, bit1=Z1, bit2=Z2, bit3=Z3) |
| 0x10 | 4 | R | Zone 0 current temp (float32, °C) |
| 0x14 | 4 | R | Zone 1 current temp (float32, °C) |
| 0x18 | 4 | R | Zone 2 current temp (float32, °C) |
| 0x1C | 4 | R | Zone 3 current temp (float32, °C) |
| 0x20 | 1 | R/W | Zone 0 target temp (uint8, °C, 30-55) |
| 0x21 | 1 | R/W | Zone 1 target temp (uint8, °C) |
| 0x22 | 1 | R/W | Zone 2 target temp (uint8, °C) |
| 0x23 | 1 | R/W | Zone 3 target temp (uint8, °C) |
| 0x30 | 1 | R | Zone 0 duty cycle (uint8, 0-100%) |
| 0x31 | 1 | R | Zone 1 duty cycle (uint8, %) |
| 0x32 | 1 | R | Zone 2 duty cycle (uint8, %) |
| 0x33 | 1 | R | Zone 3 duty cycle (uint8, %) |
| 0x40 | 2 | R | Zone 0 current (uint16, mA) |
| 0x42 | 2 | R | Zone 1 current (uint16, mA) |
| 0x44 | 2 | R | Zone 2 current (uint16, mA) |
| 0x46 | 2 | R | Zone 3 current (uint16, mA) |
| 0x50 | 4 | R | BME280 temperature (float32, °C) |
| 0x54 | 4 | R | BME280 humidity (float32, %RH) |
| 0x58 | 4 | R | BME280 pressure (float32, hPa) |
| 0x60 | 1 | R | Activity level (0=still, 1=walk, 2=run, 3=fall) |
| 0x70 | 2 | R | Battery voltage (uint16, mV) |
| 0x80 | 1 | R | Fault bitmap (see fault_type_t) |
| 0x81 | 1 | R | Zone 0 fault flags |
| 0x82 | 1 | R | Zone 1 fault flags |
| 0x83 | 1 | R | Zone 2 fault flags |
| 0x84 | 1 | R | Zone 3 fault flags |
| 0x90 | 4 | R/W | Zone 0 PID Kp (float32) |
| 0x94 | 4 | R/W | Zone 0 PID Ki (float32) |
| 0x98 | 4 | R/W | Zone 0 PID Kd (float32) |
| 0xFE | 1 | W | Command register (0x01=shutdown, 0x02=reset_faults, 0x03=reboot) |
| 0xFF | 1 | R | Firmware version (0x10 = v1.0) |

## BLE GATT Service Details

### Environmental Sensing Service (0x181A)

| Char UUID | Properties | Data Type | Description |
|-----------|-----------|-----------|-------------|
| 0x2A6E | Read, Notify | float32 (°C) | Zone 0 temperature |
| 0x2A6E+1 | Read, Notify | float32 (°C) | Zone 1 temperature |
| 0x2A6E+2 | Read, Notify | float32 (°C) | Zone 2 temperature |
| 0x2A6E+3 | Read, Notify | float32 (°C) | Zone 3 temperature |
| 0x2A1C | Read, Notify | float32 (°C) | Ambient temperature (BME280) |
| 0x2A6F | Read | uint16 (‰) | Ambient humidity (BME280) |
| 0x2A1C+1 | Read | uint16 (mV) | Battery voltage |

### ThermaWeave Control Service (0xFFB0)

| Char UUID | Properties | Data Type | Description |
|-----------|-----------|-----------|-------------|
| 0xFFB1 | Read, Write | uint8 (°C, 30-55) | Zone 0 target temp |
| 0xFFB2 | Read, Write | uint8 (°C) | Zone 1 target temp |
| 0xFFB3 | Read, Write | uint8 (°C) | Zone 2 target temp |
| 0xFFB4 | Read, Write | uint8 (°C) | Zone 3 target temp |
| 0xFFB5 | Read, Notify | uint8 (0-100%) | Zone 0 duty cycle |
| 0xFFB6 | Read, Notify | uint8 (%) | Zone 1 duty cycle |
| 0xFFB7 | Read, Notify | uint8 (%) | Zone 2 duty cycle |
| 0xFFB8 | Read, Notify | uint8 (%) | Zone 3 duty cycle |
| 0xFFB9 | Read, Notify | uint16 (mA) | Zone 0 current |
| 0xFFBA | Read, Notify | uint16 (mA) | Zone 1 current |
| 0xFFBB | Read, Notify | uint16 (mA) | Zone 2 current |
| 0xFFBC | Read, Notify | uint16 (mA) | Zone 3 current |
| 0xFFBD | Read, Notify | uint8 (enum) | Activity level |
| 0xFFBE | Write | uint8 (bitmask) | Zone enable bitmask |
| 0xFFBF | Write | uint8 (cmd) | Safety control |
| 0xFFC0 | Read, Notify | uint8 (bitmap) | Fault status |
| 0xFFC1 | Read, Write | float32 | Zone 0 PID Kp |
| 0xFFC2 | Read, Write | float32 | Zone 0 PID Ki |
| 0xFFC3 | Read, Write | float32 | Zone 0 PID Kd |
| 0xFFFF | Read | string | Device info ("Therma Weave v1.0") |

### BLE Advertising Format

```
Byte 0:   Flags (0x02, 0x01, 0x06)
Byte 3:   Complete 16-bit UUID list (0xFFB0, 0x181A)
Byte 7:   Manufacturer specific data:
            Byte 7:   Zone 0 temp (int8, °C offset from 0)
            Byte 8:   Zone 0 duty (uint8, %)
            Byte 9-10: Battery voltage (uint16, mV)
            Byte 11:  Fault flags (uint8)
            Byte 12:  Activity level (uint8)
```

## Error Codes

| Code | Name | Description |
|------|------|-------------|
| 0x00 | NONE | No fault |
| 0x01 | OVERCURRENT | Zone current exceeded 4A |
| 0x02 | OVERTEMP | Zone temperature exceeded 65°C |
| 0x04 | THERMISTOR_OPEN | Thermistor reading below -40°C (open circuit) |
| 0x08 | THERMISTOR_SHORT | Thermistor reading above 150°C (short circuit) |
| 0x10 | LOW_BATTERY | Battery voltage below 10.5V |
| 0x20 | WATCHDOG | Safety watchdog triggered |
| 0x40 | COMM_ERROR | I2C communication error |