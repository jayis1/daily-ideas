# Soil Whisper — API Reference

## Serial Console (UART)

**Interface:** USART2 (PA2=TX, PA3=RX)  
**Baud rate:** 115200  
**Data bits:** 8, Parity: None, Stop bits: 1  
**Flow control:** None

All commands are terminated with `\r\n`. The prompt is `SOIL>`.

---

## Commands

### `status`

Display current sensor readings and system status.

```
SOIL> status
  VCAP: 3.42V
  MOIST10: 34.2% (21834 Hz)
  MOIST20: 28.7% (31256 Hz)
  MOIST40: 22.1% (25678 Hz)
  TEMP10: 18.3°C
  TEMP20: 16.9°C
  TEMP40: 15.4°C
  NO3: 45.2 ppm
  PO4: 12.8 ppm
  K: 187.3 ppm
  PH: 6.4
  RH: 62.1%
  LAST_TX: 1420s ago
  UPTIME: 86400s
  SLEEP_INT: 1800s
```

---

### `sample [now]`

Force an immediate sensor sampling cycle.

```
SOIL> sample now
  Sampling...
    Moisture: 10cm=31.5% 20cm=26.1% 40cm=19.8%
    Temp: 10cm=17.2°C 20cm=15.8°C 40cm=14.3°C
    NO3: 42.1 ppm  PO4: 11.5 ppm  K: 178.9 ppm
    pH: 6.3
    Humidity: 58%
    VBAT: 3.38V
  done
```

---

### `cal <sensor> <channel> <reference>`

Calibrate a sensor channel against a known reference value.

#### Moisture Calibration

```
SOIL> cal moisture 0 air      # Record dry reference (0% VWC)
SOIL> cal moisture 0 water     # Record wet reference (100% VWC)
SOIL> cal moisture 1 air
SOIL> cal moisture 1 water
SOIL> cal moisture 2 air
SOIL> cal moisture 2 water
```

#### pH Calibration (2-point)

```
SOIL> cal ph 4.0               # pH 4.0 buffer solution
SOIL> cal ph 7.0               # pH 7.0 buffer solution
```

#### NPK Calibration (single-point per ion)

```
SOIL> cal npk no3 100           # 100 ppm NO₃⁻ standard
SOIL> cal npk po4 50            # 50 ppm PO₄³⁻ standard
SOIL> cal npk k 200             # 200 ppm K⁺ standard
```

---

### `lora join`

Initiate a LoRaWAN join procedure (OTAA or ABP).

```
SOIL> lora join
  Joining... accepted (DevAddr: 260BFFA1)
```

---

### `lora tx [port]`

Transmit the latest sensor data on the specified port (default: 2).

```
SOIL> lora tx 2
  TX on port 2, 21 bytes... done (RSSI: -45, SNR: 8.2)
```

---

### `lora config <param> <value>`

Configure LoRaWAN parameters.

| Parameter | Values | Default |
|-----------|--------|---------|
| `region` | `EU868`, `US915`, `AS923`, `AU915` | `EU868` |
| `sf` | `7`–`12` | `7` |
| `power` | `2`–`14` (dBm) | `14` |
| `devaddr` | hex | `260BFFA1` |
| `appeui` | hex | — |
| `appkey` | hex | — |

```
SOIL> lora config region US915
  Region set to US915
SOIL> lora config sf 10
  Spreading factor set to SF10
```

---

### `sleep <seconds>`

Set the sleep interval between automatic sampling cycles.

```
SOIL> sleep 300        # 5 minutes
SOIL> sleep 1800       # 30 minutes (default)
SOIL> sleep 3600       # 1 hour
SOIL> sleep 86400      # 24 hours
```

---

### `reset`

Reset all calibration data to factory defaults.

```
SOIL> reset
  WARNING: This will erase all calibration data. Continue? (y/n): y
  Calibration reset to defaults.
```

---

### `info`

Display firmware version, build date, and hardware info.

```
SOIL> info
  Soil Whisper v1.0
  Built: 2026-06-16
  MCU: STM32WL55JC (Cortex-M4 @ 48 MHz)
  Flash: 256 KB | RAM: 64 KB
  LoRa: 868 MHz SF7
  Uptime: 86400s
```

---

### `vbat`

Display current supercapacitor voltage.

```
SOIL> vbat
  VCAP: 3.42V (charge: 78%)
```

---

## LoRaWAN Payload Format

Port 2, 21 bytes, little-endian.

See the main README for the full payload specification.

### Decoding Example (Python)

```python
#!/usr/bin/env python3
"""Decode Soil Whisper LoRaWAN payload."""

import struct
from dataclasses import dataclass

@dataclass
class SoilData:
    moisture_10: float  # % VWC
    moisture_20: float  # % VWC
    moisture_40: float  # % VWC
    temp_10: float      # °C
    temp_20: float      # °C
    temp_40: float      # °C
    no3: float          # ppm
    po4: float          # ppm
    k: float            # ppm
    ph: float           # pH
    humidity: float      # %RH
    vbat: float         # V

    @classmethod
    def decode(cls, data: bytes) -> "SoilData":
        """Decode 21-byte LoRaWAN payload."""
        assert len(data) == 21, f"Expected 21 bytes, got {len(data)}"

        flags = data[0]
        m10 = int.from_bytes(data[1:3], "little") * 0.01
        m20 = int.from_bytes(data[3:5], "little") * 0.01
        m40 = int.from_bytes(data[5:7], "little") * 0.01

        t10 = int.from_bytes(data[7:9], "little", signed=True) * 0.01 - 40.0
        t20 = int.from_bytes(data[9:11], "little", signed=True) * 0.01 - 40.0
        t40 = int.from_bytes(data[11:13], "little", signed=True) * 0.01 - 40.0

        no3 = int.from_bytes(data[13:15], "little") * 0.1
        po4 = data[15] * 2.0
        k   = int.from_bytes(data[16:18], "little") * 0.1

        ph  = data[18] * 0.1
        rh  = data[19] * 0.4
        vbat = data[20] * 0.02

        return cls(m10, m20, m40, t10, t20, t40, no3, po4, k, ph, rh, vbat)

    def __str__(self) -> str:
        return (
            f"Moisture: 10cm={self.moisture_10:.1f}% "
            f"20cm={self.moisture_20:.1f}% "
            f"40cm={self.moisture_40:.1f}%\n"
            f"Temp: 10cm={self.temp_10:.1f}°C "
            f"20cm={self.temp_20:.1f}°C "
            f"40cm={self.temp_40:.1f}°C\n"
            f"NO₃⁻: {self.no3:.1f} ppm | "
            f"PO₄³⁻: {self.po4:.1f} ppm | "
            f"K⁺: {self.k:.1f} ppm\n"
            f"pH: {self.ph:.1f} | RH: {self.humidity:.0f}% | "
            f"VBat: {self.vbat:.2f}V"
        )


if __name__ == "__main__":
    # Example payload
    example = bytes([
        0xF8,                          # flags
        0x56, 0x0D,                    # moisture 10cm (34.14%)
        0x34, 0x0B,                    # moisture 20cm (28.68%)
        0xAD, 0x08,                    # moisture 40cm (22.21%)
        0xE8, 0x13,                    # temp 10cm (18.32°C)
        0xC4, 0x10,                    # temp 20cm (16.84°C)
        0x9C, 0x0E,                    # temp 40cm (15.48°C)
        0xC4, 0x01,                    # NO3 (45.2 ppm)
        0x06,                          # PO4 (12.8 ppm * 2 ≈ 6)
        0xB1, 0x07,                    # K (18.73 ppm * 10)
        0x40,                          # pH (6.4)
        0x9B,                          # RH (62.0%)
        0xAA,                          # VBat (3.4V)
    ])

    data = SoilData.decode(example)
    print(data)
```

---

## MQTT Integration (via LoRaWAN Server)

When integrated with The Things Network (TTN) or ChirpStack:

1. **Uplink topic:** `application/<appID>/device/<devEUI>/up`
2. **Payload:** Base64-encoded binary (21 bytes)
3. **Decoding:** Use the Python script above as a TTN payload formatter

### TTN Payload Formatter (JavaScript)

```javascript
function decodeUplink(input) {
    var data = input.bytes;
    var flags = data[0];
    
    var m10 = ((data[2] << 8) | data[1]) * 0.01;
    var m20 = ((data[4] << 8) | data[3]) * 0.01;
    var m40 = ((data[6] << 8) | data[5]) * 0.01;
    
    var t10 = (((data[8] << 8) | data[7]) << 16 >> 16) * 0.01 - 40.0;
    var t20 = (((data[10] << 8) | data[9]) << 16 >> 16) * 0.01 - 40.0;
    var t40 = (((data[12] << 8) | data[11]) << 16 >> 16) * 0.01 - 40.0;
    
    var no3 = ((data[14] << 8) | data[13]) * 0.1;
    var po4 = data[15] * 2.0;
    var k   = ((data[17] << 8) | data[16]) * 0.1;
    
    var ph = data[18] * 0.1;
    var rh = data[19] * 0.4;
    var vbat = data[20] * 0.02;
    
    return {
        data: {
            moisture: { depth10cm: m10, depth20cm: m20, depth40cm: m40 },
            temperature: { depth10cm: t10, depth20cm: t20, depth40cm: t40 },
            nitrogen_NO3: no3,
            phosphorus_PO4: po4,
            potassium: k,
            pH: ph,
            humidity: rh,
            batteryVoltage: vbat,
            flags: {
                moistureValid: !!(flags & 0x80),
                temperatureValid: !!(flags & 0x40),
                npkValid: !!(flags & 0x20),
                phValid: !!(flags & 0x10),
                humidityValid: !!(flags & 0x08),
            }
        },
        warnings: [],
        errors: []
    };
}
```

---

## Downlink Commands (Port 3)

The Soil Whisper accepts downlink commands on LoRaWAN port 3:

| Byte 0 | Command | Bytes 1+ | Description |
|--------|---------|----------|-------------|
| 0x01 | Set sleep interval | uint32 (seconds, LE) | Change sampling interval |
| 0x02 | Force sample | — | Trigger immediate sampling + TX |
| 0x03 | Reset calibration | — | Reset all calibration to defaults |
| 0x04 | Set LoRa SF | uint8 (7–12) | Change spreading factor |
| 0xFF | Reboot | — | Reboot the device |