# Opti Rot — API Reference

## BLE GATT Protocol

The ESP32-C3 companion exposes a BLE 5.0 GATT server with the following service:

### Service: `0000FF30-0000-1000-8000-00805F9B34FB` (Opti Rot Service)

#### Characteristics

| UUID | Name | Properties | Description |
|------|------|------------|-------------|
| `FF31` | Command | Write | Send command to device |
| `FF32` | Result | Notify | Measurement results (notification) |
| `FF33` | Status | Notify | Device status updates |
| `FF34` | Library | Read/Write | Compound library access |
| `FF35` | Config | Read/Write | Device configuration |

### Command Format (Write to `FF31`)

Commands are sent as binary frames:
```
[CMD] [LEN] [PAYLOAD...]
```

| CMD | Name | Payload | Response |
|-----|------|---------|----------|
| 0x01 | Measure | — | Result on `FF32` |
| 0x02 | Identify | — | Multi-result on `FF32` |
| 0x03 | Auto-Zero | — | Status on `FF33` |
| 0x04 | Monitor Start | [interval_ms: u16] | Periodic results on `FF32` |
| 0x05 | Monitor Stop | — | Status on `FF33` |
| 0x06 | Set Wavelength | [wl_nm: u16] | Status on `FF33` |
| 0x07 | List Library | — | Multiple entries on `FF34` |
| 0x08 | Add Compound | [name:24B][α:f32][tc:f32][K:f32][λ0:f32] | Status on `FF33` |
| 0x09 | Remove Compound | [index: u8] | Status on `FF33` |
| 0x0A | Get Config | — | Config on `FF35` |
| 0x0B | Set Config | [key:16B][value:16B] | Status on `FF33` |

### Result Format (Notify from `FF32`)

#### Single-Wavelength Result (CMD 0x01)

```
Byte  0:  Result type (0x01 = single)
Bytes 1-4:  Angle (float32, little-endian) — analyzer null angle
Bytes 5-8:  Rotation (float32) — optical rotation in degrees
Bytes 9-12: Concentration (float32) — g/100mL (if compound known)
Bytes 13-16: Confidence (float32) — 0-100%
Bytes 17-20: Wavelength (float32) — nm
Bytes 21-24: Temperature (float32) — °C
Bytes 25-48: Compound name (24 bytes, null-padded ASCII)
```

#### Multi-Wavelength Result (CMD 0x02)

```
Byte  0:  Result type (0x02 = multi)
Bytes 1-4:  Rotation @ 405nm (float32)
Bytes 5-8:  Rotation @ 520nm (float32)
Bytes 9-12: Rotation @ 589nm (float32)
Bytes 13-16: Drude K (float32)
Bytes 17-20: Drude λ₀ (float32, nm)
Bytes 21-24: Drude residual (float32)
Byte  25:  Match index (uint8) — library entry
Bytes 26-29: Match confidence (float32)
Bytes 30-33: Match distance (float32)
Bytes 34-57: Match name (24 bytes, null-padded)
```

### Library Entry Format (Read/Write `FF34`)

```
Bytes 0-23:  Name (24 bytes, null-padded ASCII)
Bytes 24-27: Specific rotation [α]_D (float32)
Bytes 28-31: Temperature coefficient (float32)
Bytes 32-35: Drude K (float32)
Bytes 36-39: Drude λ₀ (float32)
Byte  40:    Is custom (0=builtin, 1=user-added)
```

## Wi-Fi SoftAP

When enabled via Config, the ESP32-C3 creates a Wi-Fi softAP:

- **SSID**: `OptiRot-XXXX` (last 4 of MAC)
- **Password**: `optirot123`
- **IP**: `192.168.4.1`

### HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard (measurement display, library browser) |
| `/api/measure` | POST | Trigger single measurement |
| `/api/identify` | POST | Trigger 3-wavelength identification |
| `/api/zero` | POST | Auto-zero |
| `/api/monitor/start` | POST | Start monitoring (body: `{"interval": 10000}`) |
| `/api/monitor/stop` | POST | Stop monitoring |
| `/api/library` | GET | List all library entries (JSON) |
| `/api/library/add` | POST | Add compound (body: `{"name":"...","alpha":66.5,"tc":-0.01}`) |
| `/api/library/remove` | POST | Remove compound (body: `{"index": 41}`) |
| `/api/config` | GET | Get configuration |
| `/api/config` | POST | Set configuration |
| `/api/log` | GET | Download SD card log as CSV |
| `/api/log/download` | GET | Download full log file |

### JSON Response Format

```json
{
  "type": "single",
  "angle": 45.123,
  "rotation": 34.600,
  "concentration": 26.000,
  "confidence": 0.0,
  "wavelength": 589.0,
  "temperature": 21.3,
  "compound": "",
  "timestamp": 1688256000000
}
```

Multi-wavelength response:
```json
{
  "type": "multi",
  "rotations": {"405": 72.3, "520": 48.1, "589": 34.6},
  "drude": {"K": 2100000, "lambda0": 190, "residual": 0.002},
  "match": {"index": 0, "name": "Sucrose", "confidence": 94.2, "distance": 0.08},
  "temperature": 21.3,
  "timestamp": 1688256000000
}
```

## UART Binary Protocol (STM32 ↔ ESP32-C3)

The STM32 and ESP32-C3 communicate over UART2 at 1 Mbps using a framed binary protocol.

### Frame Format

```
[SYNC: 0xA5] [VERSION: 0x01] [LEN_LO] [LEN_HI] [CMD] [PAYLOAD...] [CHECKSUM]
```
- SYNC: 0xA5 (always)
- VERSION: 0x01 (protocol version)
- LEN: 16-bit little-endian payload length
- CMD: command opcode (see ble_bridge.h)
- CHECKSUM: XOR of all bytes from VERSION through last PAYLOAD byte

### STM32 → ESP32 Commands

| Opcode | Name | Payload |
|--------|------|---------|
| 0x01 | Result Single | 48 bytes (see ble_bridge.c) |
| 0x02 | Result Multi | 61 bytes (see ble_bridge.c) |
| 0x03 | Library Entry | 41 bytes per entry |
| 0x04 | Status | variable length string |
| 0x05 | Log Entry | CSV line |

### ESP32 → STM32 Commands

| Opcode | Name | Payload |
|--------|------|---------|
| 0x81 | Measure | — |
| 0x82 | Identify | — |
| 0x83 | Zero | — |
| 0x84 | Monitor Start | [interval_ms: u16] |
| 0x85 | Monitor Stop | — |
| 0x86 | Library List | — |
| 0x87 | Library Add | [name:24B][α:f32][tc:f32][K:f32][λ0:f32] |
| 0x88 | Library Remove | [index: u8] |
| 0x89 | Set Wavelength | [wl_nm: u16] |
| 0x8A | Get Status | — |

## SD Card Log Format

Measurements are logged to `/opti_rot/log.csv` in the following format:

```csv
timestamp_ms,rotation_deg,concentration,compound,confidence,temp_c,wavelength_nm
1688256000000,34.6000,26.000,Sucrose,94.2,21.3,589
1688256010000,34.5980,25.998,Sucrose,94.1,21.3,589
```

The custom library is persisted to `/opti_rot/library.bin` as:
```
[count: u8] [entry × count: 41 bytes each]
```