# Spectra Charm — API Reference

## UART Protocol (STM32G491 ↔ ESP32-C3)

### Packet Format

All packets follow this structure:

```
[0xA5] [0x5A] [LEN_H] [LEN_L] [CMD] [PAYLOAD...] [CRC8]
```

| Field | Size | Description |
|-------|------|-------------|
| SYNC1 | 1 | Fixed 0xA5 |
| SYNC2 | 1 | Fixed 0x5A |
| LEN_H | 1 | Payload length high byte |
| LEN_L | 1 | Payload length low byte |
| CMD | 1 | Command byte |
| PAYLOAD | 0-506 | Variable length data |
| CRC8 | 1 | CRC-8 over CMD + PAYLOAD |

### Commands (STM32 → ESP32)

| CMD | Name | Payload | Description |
|-----|------|---------|-------------|
| 0x81 | SCAN_RESULT | See below | Full scan result with peaks and match |
| 0x83 | BATTERY_RESP | SOC(1) + voltage(2) | Battery status response |
| 0x84 | STATUS_RESP | state(1) + uptime(4) + scans(2) | Device status |
| 0x85 | LIBRARY_RESP | count(2) + entries... | Library listing |
| 0x86 | ACK | orig_cmd(1) + status(1) | Acknowledge |

### Commands (ESP32 → STM32)

| CMD | Name | Payload | Description |
|-----|------|---------|-------------|
| 0x01 | SCAN_REQUEST | type(1) + gain(1) + integration(2) | Trigger scan |
| 0x02 | SET_GAIN | gain(1) | Change AS7343 gain |
| 0x03 | GET_BATTERY | (none) | Request battery status |
| 0x04 | GET_STATUS | (none) | Request device status |
| 0x05 | LIBRARY_LIST | (none) | List library compounds |
| 0x06 | ADD_COMPOUND | entry(512) | Add custom compound to flash |

### SCAN_RESULT Payload

```
Offset  Size  Field
0       1    Status (0=OK, 1=no_cuvette, 2=invalid, 3=timeout, 4=saturated)
1       2    Scan number (big-endian)
3       1    Number of peaks found
4       128  Peaks array (16 × {wavelength_f32, absorbance_f32})
132     1    Compound ID
133     4    Match confidence (float32)
137     4    Concentration in mol/L (float32)
141     32   Compound name (null-terminated)
Total: 173 bytes
```

## BLE GATT Service

### Service: Spectra Charm (0xFEA0)

| Characteristic | UUID | Properties | Format |
|----------------|------|------------|--------|
| Scan Trigger | 0xFEA1 | Write | uint8: 0=dark, 1=blank, 2=sample |
| Spectrum Data | 0xFEA2 | Notify | 128 × float32 (512 bytes, 20-byte chunks) |
| Compound ID | 0xFEA3 | Read | uint8 compound ID |
| Battery Level | 0xFEA4 | Read | uint8 percentage |
| Device Info | 0xFEA5 | Read | UTF-8 string |

### Spectrum Data Notification

The 512-byte spectrum payload is sent in 26 BLE notification packets:

```
Packet 0:  [SEQ(1)] [DATA(19)]
Packet 1:  [SEQ(1)] [DATA(20)]
...
Packet 25: [SEQ(1)] [DATA(13)]
```

SEQ is a rolling sequence number (0-25) for reassembly.

### Absorbance Spectrum Format

Each float32 value at index `i` represents:

```
wavelength(nm) = 340.0 + (360.0 × i / 127)
absorbance(AU) = spectrum[i]
```

Valid range: 340 nm to 700 nm, 0.0 to 2.0 AU.

## WiFi REST API

Base URL: `http://192.168.4.1` (AP mode, password: `spectra24`)

### Endpoints

#### POST /api/v1/scan
Trigger a new scan.

**Request body** (optional JSON):
```json
{"type": 2}
```

| type | Meaning |
|------|---------|
| 0 | Dark reference |
| 1 | Blank reference |
| 2 | Sample scan (default) |

**Response** (200):
```json
{"status": "scanning"}
```

#### GET /api/v1/spectrum
Get the last acquired spectrum.

**Response** (200):
```json
{
  "points": 128,
  "wl_start": 340.0,
  "wl_end": 700.0,
  "absorbance": [0.001, 0.002, ..., 0.015]
}
```

#### GET /api/v1/match
Get compound match results for last scan.

**Response** (200):
```json
{
  "compound": "Potassium Permanganate",
  "confidence": 0.94,
  "concentration_mol_L": 0.00125
}
```

#### GET /api/v1/library
List available reference spectra.

**Response** (200):
```json
{
  "count": 15,
  "compounds": [
    {"id": 1, "name": "Potassium Permanganate"},
    {"id": 2, "name": "Potassium Dichromate"},
    ...
  ]
}
```

#### POST /api/v1/library
Upload a new reference spectrum.

**Request body**:
```json
{
  "name": "My Compound",
  "num_key_points": 3,
  "molar_absorptivity": 5600.0,
  "key_wavelengths": [420.0, 520.0, 560.0],
  "key_absorbances": [0.3, 1.0, 0.8]
}
```

**Response** (201):
```json
{"id": 16, "status": "added"}
```

#### GET /api/v1/config
Get device configuration.

**Response** (200):
```json
{
  "name": "Spectra Charm",
  "version": "1.0.0",
  "wavelength_start_nm": 340,
  "wavelength_end_nm": 700,
  "points": 128,
  "path_length_cm": 1.0
}
```

#### GET /api/v1/battery
Get battery status.

**Response** (200):
```json
{
  "percent": 87,
  "voltage_mv": 3850,
  "current_ma": -45,
  "charging": true,
  "time_to_empty_min": 65535
}
```

#### POST /api/v1/ota
Upload firmware update (ESP32-C3 only).

**Request**: Binary firmware image as body
**Response** (200): `{"status": "rebooting"}`