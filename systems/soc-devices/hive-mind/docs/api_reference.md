# Hive Mind — API Reference

## USB-C Console Commands

The Hive Mind exposes a serial console over USB-C (via CH340E UART bridge) at **115200 baud, 8N1**. All commands are newline-terminated and case-insensitive.

---

## General Commands

### `help`
Print available commands.

### `version`
Print firmware version and build date.

### `reset`
Software reset the MCU.

### `uptime`
Print uptime in hours.

---

## Weight Sensor Commands

### `weight read`
Read current hive weight in grams.

**Response:**
```
Weight: 23456 g (23.5 kg)
```

### `weight tare`
Tare the load cell (set current reading as zero point).

**Response:**
```
Tare offset: -12345
```

### `weight calibrate <grams>`
Calibrate with a known weight. Place the weight on the platform before calling this.

**Example:**
```
> weight calibrate 10000
Calibrated. Scale factor: 35.24 counts/g
```

### `weight raw`
Read raw HX711 ADC value (24-bit signed).

**Response:**
```
Raw: -12345
```

### `weight offset`
Read current tare offset value.

---

## Temperature Commands

### `temp scan`
Scan for DS18B20 probes on the 1-Wire bus and list their ROM IDs.

**Response:**
```
Found 3 probes:
[0] 28:FF:A1:B2:C3:D4:E5:01 -> floor
[1] 28:FF:11:22:33:44:55:66 -> mid
[2] 28:FF:AA:BB:CC:DD:EE:FF -> crown
```

### `temp read`
Read all temperature probes.

**Response:**
```
Floor: 22.5°C  Mid: 34.8°C  Crown: 32.1°C
```

### `temp assign <ROM_ID> <location>`
Assign a specific probe ROM ID to a location (floor, mid, or crown).

**Example:**
```
> temp assign 28:FF:A1:B2:C3:D4:E5:01 floor
Assigned 28:FF:A1:B2:C3:D4:E5:01 to floor
```

### `temp resolution <bits>`
Set DS18B20 resolution (9, 10, 11, or 12 bits). Default: 12 bits.

**Trade-off:** Lower resolution = faster conversion (9-bit: 93.75 ms vs 12-bit: 750 ms).

---

## Acoustic Commands

### `acoustic test`
Capture 2 seconds of audio, run FFT, and classify.

**Response:**
```
Dominant freq: 245 Hz
Class: QUEENRIGHT
Confidence: high (hum energy ratio: 0.32)
```

### `acoustic spectrum`
Print the FFT magnitude spectrum (first 32 bins).

**Response:**
```
Bin   Freq(Hz)   Magnitude
0     0           15234
1     31          876
2     62          456
...
31    968         123
```

### `acoustic raw`
Capture and stream raw I2S audio samples (2 seconds, 8 kHz, 16-bit).

**Warning:** Large output (~32 KB). Use with logging disabled.

### `acoustic classify`
Same as `acoustic test` but outputs the classification enum value only.

**Response:**
```
0
```
(0 = QUEENRIGHT, 1 = QUEENLESS, etc.)

---

## Bee Counter Commands

### `bee test [duration_s]`
Count bee traffic for the specified duration (default: 10 seconds).

**Response:**
```
Counting for 10s...
In: 23  Out: 18  Ratio: 1.28
```

### `bee calibrate`
Interactive calibration: wave a pencil through each gate to verify operation.

**Response:**
```
Calibrating OUT gate... Break detected! ✓
Calibrating IN gate... Break detected! ✓
```

---

## Ambient Sensor Commands

### `bme read`
Read BME280 ambient temperature, humidity, and pressure.

**Response:**
```
T: 22.5°C  H: 65.2%  P: 1013.4 hPa
```

---

## OLED Display Commands

### `oled on`
Turn on the OLED display.

### `oled off`
Turn off the OLED display (saves ~10 mA).

### `oled text <message>`
Display a custom text message on the OLED (max 21 characters per line).

**Example:**
```
> oled text Hello Beekeeper
```

### `oled status`
Show the default status screen (weight, temps, class, health).

---

## LoRaWAN Commands

### `lora status`
Show LoRaWAN connection status.

**Response:**
```
Status: JOINED
DevEUI: 70:B3:D5:7E:D0:00:00:01
AppEUI: 70:B3:D5:7E:D0:00:00:00
DR: 3 (SF7/125kHz)
TX Power: 14 dBm
Last TX: 15s ago
Uplinks: 42
```

### `lora join [otaa|abp]`
Join a LoRaWAN network. Default: OTAA.

### `lora set_deveui <hex16>`
Set the Device EUI (8 bytes, hex).

### `lora set_appeui <hex16>`
Set the Application EUI (8 bytes, hex).

### `lora set_appkey <hex32>`
Set the Application Key (16 bytes, hex).

### `lora test_tx`
Send a test uplink packet.

### `lora dr <0-5>`
Set data rate (0=SF12/125kHz through 5=SF7/250kHz).

### `lora port <1-223>`
Set application port for uplinks.

---

## Power Commands

### `power status`
Show battery and solar voltages, charge state.

**Response:**
```
Battery: 3.28V (86%)
Solar: 5.12V (charging)
Uptime: 120h
State: CHARGING
```

### `power sleep`
Enter STOP mode immediately (wakes on RTC alarm or user button).

### `power deepsleep`
Enter STANDBY mode (wakes on user button only, loses RAM state).

---

## System Commands

### `health`
Compute and display the hive health score.

**Response:**
```
Health Score: 82/100 (GOOD)
  Weight trend: 85/100
  Temperature: 78/100
  Acoustic: 100/100 (QUEENRIGHT)
  Bee traffic: 72/100
  Ambient: 80/100
  Battery: 86/100
```

### `factory_reset`
Erase all stored configuration (calibration, ROM assignments, LoRaWAN keys) and reset to defaults.

### `save`
Save current configuration to flash (NVM).

### `load`
Load configuration from flash (happens automatically on boot).

---

## Console Output Format

All responses are plain text, newline-terminated. Error responses start with `ERR:`. Example:

```
> weight calibrate
ERR: No weight on platform (raw value too low)
```

---

## Boot Messages

On power-up, the console prints:

```
=== Hive Mind v1.0 ===
STM32WL55JC @ 48 MHz
Free heap: 8192 bytes
Sensors: OK
BME280: OK (0x76)
DS18B20: 3 probes found
HX711: OK
OLED: OK (0x3C)
LoRaWAN: Joining...
LoRaWAN: Joined!
Ready.
```

---

*SoC Device Inventions — jayis1*